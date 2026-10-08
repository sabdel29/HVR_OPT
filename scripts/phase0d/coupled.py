"""Phase-0D electrical-thermal fixed point, with the validated FEA thermal solver in the loop.

    T -> R_DS(on)(T), DCR(T), rho_Cu(T) -> P_conv, P_PDN -> heat sources -> FEA thermal -> T

Mechanics is deliberately OUTSIDE the loop: the M0 structural model has no back-action on
the electrical or thermal problem (linear thermoelasticity, no deformation-dependent contact),
so the correct sequence is ET fixed point -> converged temperature field -> structural solve.

A candidate that does not converge is REJECTED, never silently reported at its last iterate.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field as dcfield
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "phase0b"))
sys.path.insert(0, str(REPO / "scripts" / "phase0d"))

from etm import ccxio, metrics                                   # noqa: E402
from etm.config import build_materials                           # noqa: E402
from etm.mesh import build                                       # noqa: E402
from etm.placement import Tile                                   # noqa: E402
from electrical import (TSVField, HVRDesign, lateral_pdn,        # noqa: E402
                        vertical_tsv_loss, ALPHA_GAN_RDSON)

MM_PER_M = 1e-3


@dataclass
class ETResult:
    converged: bool
    iterations: int
    history: list = dcfield(default_factory=list)
    T_max_c: float = float("nan")
    T_tile_c: list = dcfield(default_factory=list)
    p_conv_total_w: float = float("nan")
    p_lateral_w: float = float("nan")
    p_tsv_w: float = float("nan")
    p_pdn_w: float = float("nan")
    p_elec_total_w: float = float("nan")
    efficiency_pct: float = float("nan")
    r_tsv_field_ohm: float = float("nan")
    n_via_per_vr: int = 0
    energy_residual_pct: float = float("nan")
    ripple_ok: bool = True


def tile_temperatures(m, T: np.ndarray, n_tiles: int) -> list[float]:
    """Volume-weighted mean temperature of each HVR tile (its own junction environment)."""
    out = []
    V = m.elem_volumes()
    for ti in range(n_tiles):
        ids = m.elem_set(layer="tile_band", tile=ti)
        if len(ids) == 0:
            out.append(float(np.nanmean(T[1:m.n_nodes + 1, 0])))
            continue
        w = V[ids - 1]
        tm = np.array([np.nanmean(T[m.elems[e - 1], 0]) for e in ids])
        out.append(float((tm * w).sum() / w.sum()))
    return out


def solve_et(design: HVRDesign, tiles_xy, stack, doe, workdir: Path, *,
             h_sub_mm: float, h_top: float, p_die_w: float, i_total_a: float,
             tile_ax: float, tile_ay: float, pol_xy: np.ndarray,
             rho_mohm_per_mm: float = 50.0, r_bump_ohm: float = 0.08e-3,
             tsv_path: str = "input", i_via_max_a: float = 0.033,
             alpha_gan: float = ALPHA_GAN_RDSON,
             h_xy: float = 0.45, z_scale: float = 1.0,
             tol_T: float = 0.05, tol_P: float = 1e-3, max_iter: int = 20,
             threads: int = 32) -> ETResult:
    """Run the ET fixed point for one candidate architecture."""
    workdir.mkdir(parents=True, exist_ok=True)
    n_vr = len(tiles_xy)
    field = TSVField(i_via_max_a=i_via_max_a)
    mats = build_materials(stack)

    T_tile = [25.0] * n_vr
    prev_Tmax, prev_P = None, None
    hist, res = [], ETResult(converged=False, iterations=0)

    for it in range(max_iter):
        # ---- electrical at the current temperature -------------------------
        conv = [design.loss_at(T_tile[j], alpha_gan) for j in range(n_vr)]
        p_conv = [c["p_conv_w"] for c in conv]
        T_bulk = float(np.mean(T_tile))

        lat = lateral_pdn(pol_xy, np.array([(t[0], t[1]) for t in tiles_xy]),
                          i_total_a, rho_mohm_per_mm, design.f_sw_hz,
                          r_bump_ohm=r_bump_ohm, T_c=T_bulk, temp_aware=True)
        ver = vertical_tsv_loss(lat["i_per_vr_a"], h_sub_mm * MM_PER_M, T_bulk, field,
                                tile_ax * tile_ay, path=tsv_path,
                                v_in=design.v_in, v_out=design.v_out)

        p_conv_tot = float(sum(p_conv))
        p_pdn = lat["p_lateral_w"] + ver["p_tsv_total_w"]
        p_elec = p_conv_tot + p_pdn

        # ---- thermal: HVR tiles dissipate converter loss; PDN loss is
        #      distributed into the die layer where the routing physically sits
        tiles = [Tile(cx, cy, tile_ax, tile_ay, p_conv[j])
                 for j, (cx, cy) in enumerate(tiles_xy)]
        m = build(tiles, stack, h_sub_mm, h_xy=h_xy, z_scale=z_scale)
        tinp = workdir / f"thermal_{it}.inp"
        films = ccxio.write_thermal(m, mats, tiles, stack, p_die_w + p_pdn, h_top, tinp)
        ccxio.run_ccx(tinp, threads=threads)
        Tfrd = ccxio.read_frd(workdir / f"thermal_{it}.frd")["NDTEMP"]
        tm = metrics.thermal_metrics(m, Tfrd, films, stack, p_die_w + p_elec, h_top)
        T_tile = tile_temperatures(m, Tfrd, n_vr)
        Tmax = tm["T_max_C"]

        dT = abs(Tmax - prev_Tmax) if prev_Tmax is not None else float("inf")
        dP = abs(p_elec - prev_P) / p_elec if prev_P is not None else float("inf")
        hist.append({"iter": it, "T_max_C": Tmax, "T_tile_mean_C": float(np.mean(T_tile)),
                     "p_conv_total_w": p_conv_tot, "p_lateral_w": lat["p_lateral_w"],
                     "p_tsv_w": ver["p_tsv_total_w"], "p_elec_total_w": p_elec,
                     "dT_max_K": dT if np.isfinite(dT) else None,
                     "dP_rel": dP if np.isfinite(dP) else None,
                     "energy_residual_pct": tm["energy_residual_pct"]})
        for f in workdir.glob(f"thermal_{it}.*"):
            if f.suffix not in (".inp",):
                f.unlink(missing_ok=True)

        if dT < tol_T and dP < tol_P:
            rl = design.loss_at(float(np.mean(T_tile)), alpha_gan)
            res = ETResult(
                converged=True, iterations=it + 1, history=hist, T_max_c=Tmax,
                T_tile_c=[round(x, 4) for x in T_tile], p_conv_total_w=p_conv_tot,
                p_lateral_w=lat["p_lateral_w"], p_tsv_w=ver["p_tsv_total_w"],
                p_pdn_w=p_pdn, p_elec_total_w=p_elec,
                efficiency_pct=100.0 * p_die_w / (p_die_w + p_elec),
                r_tsv_field_ohm=ver["per_vr"][0]["r_field_ohm"],
                n_via_per_vr=ver["per_vr"][0]["n_via"],
                energy_residual_pct=tm["energy_residual_pct"],
                ripple_ok=bool(abs(rl["delta_i_out_a"]) <= 0.5 * design.i_out_a))
            break
        prev_Tmax, prev_P = Tmax, p_elec

    res.history = hist
    (workdir / "fixed_point_history.json").write_text(json.dumps(hist, indent=2))
    if not res.converged:
        res.iterations = len(hist)
    return res
