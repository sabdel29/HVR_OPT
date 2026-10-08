"""Phase-0D-R: evaluate a full architecture power path, tier by tier, rail by rail."""
from __future__ import annotations

import math
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "phase0dr"))
sys.path.insert(0, str(REPO / "scripts" / "phase0d"))
import ppdn
from ppdn import (Infeasible, load_paths, n_available, n_required, rail_currents,
                  rdl_sheet_solve, vertical_segment)

_v = ppdn._v

DIE_MM = 22.36
N_POL_SIDE = 10


def pol_grid(die_mm: float = DIE_MM, n: int = N_POL_SIDE):
    q = (np.arange(n) + 0.5) / n * die_mm - die_mm / 2
    return [(x, y) for x in q for y in q]


def evaluate(arch_name: str, tiles_xy, tile_side_mm: float, h_sub_mm: float,
             i_total_a: float, p_conv_total_w: float, T_c: float,
             v_in: float = 48.0, v_out: float = 1.0, paths: dict | None = None,
             t_tile_mm: float = 0.150, rdl_n: int = 81,
             lateral_route_mm: float | None = None) -> dict:
    """Full rail-aware loss decomposition for one architecture at one thickness."""
    P = paths or load_paths()
    arch = P["architectures"][arch_name]
    tiers = P["tiers"]
    n_vr = len(tiles_xy)

    i_out = i_total_a / n_vr
    p_conv_vr = p_conv_total_w / n_vr
    rc = rail_currents(i_out, v_in, v_out, p_conv_vr)
    cur = {"HV": rc["I_in_a"], "LV": rc["I_out_a"]}

    tile_fp = tile_side_mm ** 2
    h_tsv_m = (h_sub_mm - t_tile_mm) * 1e-3
    if h_tsv_m <= 0:
        raise ValueError("h_sub must exceed the tile thickness")

    segs, infeas = [], []
    for s in arch["segments"]:
        tier_name = s["tier"]
        if tier_name in ("converter", "rdl"):
            continue
        rail = s["rail"]
        I = cur[rail]
        h_m = h_tsv_m if tier_name == "tsv" else None
        # BGA sits under the package, not under one tile: give it the package footprint share
        fp = tile_fp if tier_name in ("tsv", "microbump") else (30.0 * 30.0) / n_vr
        try:
            segs.append(vertical_segment(s["id"], tier_name, tiers[tier_name], rail, I,
                                         fp, T_c, h_m, heat_region=tier_name, n_vr=n_vr))
        except Infeasible as e:
            infeas.append(str(e))

    # ---- lateral RDL: solved as a 2-D resistive sheet ------------------------
    pol = pol_grid()
    i_per_pol = i_total_a / len(pol)
    rdl = rdl_sheet_solve([(x, y) for x, y in tiles_xy], [i_out] * n_vr,
                          pol, [i_per_pol] * len(pol), tiers["rdl"], T_c,
                          DIE_MM, n=rdl_n, src_size_mm=tile_side_mm,
                          load_size_mm=DIE_MM / N_POL_SIDE)
    p_rdl = rdl["p_loop_w"]

    # 2.5D: the VR sits outside the die, so the output additionally crosses a long
    # interposer route before it reaches the die edge.
    p_rdl_long = 0.0
    if lateral_route_mm:
        tier = tiers["rdl"]
        sigma_s = _v(tier["t_cu_m"]) * _v(tier["metal_occupancy"]) / ppdn.rho_at(tier, T_c)
        # a route of length L and width W_eff has L/W squares
        w_eff_mm = DIE_MM
        r_route = (1.0 / sigma_s) * (lateral_route_mm / w_eff_mm)
        p_rdl_long = 2.0 * i_total_a ** 2 * r_route
        p_rdl += p_rdl_long

    by_tier = {}
    for s in segs:
        by_tier[s.tier] = by_tier.get(s.tier, 0.0) + s.p_loss_w
    by_tier["rdl"] = p_rdl

    p_pdn = sum(by_tier.values())
    dv = {s.tier: s.dv_v for s in segs}
    dv["rdl"] = rdl["dv_span_v"]

    return {
        "architecture": arch_name, "tsv_rail": arch["tsv_rail"],
        "h_sub_mm": h_sub_mm, "n_vr": n_vr, "tile_side_mm": tile_side_mm,
        "I_out_per_vr_a": rc["I_out_a"], "I_in_per_vr_a": rc["I_in_a"],
        "I_tsv_a": cur[arch["tsv_rail"]], "stage_eta": rc["eta_stage"],
        "feasible": len(infeas) == 0, "infeasible_reasons": infeas,
        "segments": [asdict(s) for s in segs],
        "P_by_tier_w": by_tier, "P_pdn_w": p_pdn, "P_conv_w": p_conv_total_w,
        "P_elec_total_w": p_pdn + p_conv_total_w,
        "dV_by_tier_v": dv, "dV_total_v": sum(dv.values()),
        "rdl_solve": rdl, "p_rdl_long_route_w": p_rdl_long,
        "n_tsv_required": next((s.n_required for s in segs if s.tier == "tsv"), None),
        "n_tsv_available": next((s.n_available for s in segs if s.tier == "tsv"), None),
        "r_tsv_loop_ohm": next((s.r_loop_ohm for s in segs if s.tier == "tsv"), None),
    }
