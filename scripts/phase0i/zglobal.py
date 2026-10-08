#!/usr/bin/env python3
"""Phase-0I Sec.6/7/16 -- architecture-specific GLOBAL package model.

Moving the converter in z changes three things at once, and all three have to move together:
  * the SUBSTRATE THICKNESS the architecture is allowed (Sec.5),
  * WHERE the converter heat is injected,
  * WHERE the converter's stiff, high-CTE material sits relative to the neutral plane.

Phases 0B-0H reused one mechanical stack for every architecture (DEFECT #33), so none of this
was visible.

The model supplies the two quantities the local joint submodel needs at the critical BGA:
    du(t)  relative in-plane displacement across the ball standoff
    T(t)   joint temperature
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
for p in ("phase0i", "phase0h", "phase0g", "phase0f", "phase0e", "phase0b"):
    sys.path.insert(0, str(R / "scripts" / p))

import board as BRD                                                    # noqa: E402
import kw1                                                             # noqa: E402
from etm import ccxio, metrics                                         # noqa: E402
from etm.config import build_materials, load_doe, load_stack           # noqa: E402
from etm.mesh import build                                             # noqa: E402
from etm.placement import Tile                                         # noqa: E402
from zarch import GAN_HS_UM, GAN_LS_UM, realizable                     # noqa: E402

DIE_MM = 22.36
CONV_CELL_MM = (500.0 + GAN_LS_UM + 100.0 + 20.0) / 1e3     # 1.226 mm converter stack

# Where the converter sits relative to the substrate, per architecture.
#   "in"    inside the substrate (a tile band), as Phases 0B-0H assumed
#   "below" between the BGA field and the substrate underside
#   "above" between the substrate top and the compute die
CONV_PLACE = {"ARCH_Z1_EMBEDDED": "in",
              "ARCH_Z2_BACKSIDE": "below",
              "ARCH_Z4_POWER_DIE": "above"}


def stack_for(arch: str, h_sub_mm: float, board_case: str = "fr4_1p6mm") -> tuple:
    """(stack dict, extra bottom layers, converter tile thickness) for this architecture."""
    st0 = load_stack()
    place = CONV_PLACE[arch]
    if place == "in":
        st = BRD.stack_with_board(st0, CONV_CELL_MM, board_case)
        extra = BRD.bottom_layers(board_case)
        return st, extra, CONV_CELL_MM
    # the converter is NOT in the substrate: the tile band collapses to a thin RDL band and
    # the converter becomes its own layer, above or below.
    st = BRD.stack_with_board(st0, 0.020, board_case)
    extra = BRD.bottom_layers(board_case)
    if place == "below":
        # board / bga / CONVERTER / substrate : insert the converter directly under z = 0
        extra = extra + [("conv", CONV_CELL_MM, "hvr_effective", 2)]
    return st, extra, 0.020


def mid_layers(arch: str, variant: str = "Z4_STACKED") -> list:
    """Layers between the substrate top and the compute die.

    PHASE 0M-R2. `stack_for` had branches for "in" and "below" and NONE for "above", so
    ARCH_Z4's power die was never built and its heat was deposited in the `interface`
    layer 0.355 mm below the cooler. `conv_above_layers` was written for this branch and
    was never called. Geometry and provenance: configs/phase0mr2/z4_stack.yaml.
    """
    if CONV_PLACE.get(arch) != "above":
        return []
    cfg = _z4_cfg()
    v = next(x for x in cfg["variants"] if x["id"] == variant)
    if variant == "Z4_PLANAR":
        # components side by side: one component band of the tallest part, plus the RDLs
        # and the bond, which are present in both constructions.
        names = {"power_die_rdl_lower", "power_die_rdl_upper", "hybrid_bond"}
        out = []
        for L in cfg["layers"]:
            if L["name"] in names:
                out.append((L["name"], L["thickness_um"] * 1e-3, _MAT[L["material"]], 1))
            elif L["name"] == "gan_hs":
                out.append(("pdie_components", (v["total_thickness_um"] - 30.0) * 1e-3,
                            "hvr_effective", 3))
        return out
    return [(L["name"] if L["name"].startswith("power_die") or L["name"] == "hybrid_bond"
             else "pdie_" + L["name"],
             L["thickness_um"] * 1e-3, _MAT[L["material"]],
             3 if L["thickness_um"] > 200 else 1)
            for L in cfg["layers"]]


# The Z4 stack names its own materials; they map onto the media the framework already has,
# so the architecture comparison stays a comparison of PLACEMENT and not of materials.
_MAT = {"rdl_effective": "hvr_effective",
        "gan_device": "hvr_effective",
        "inductor_effective": "hvr_effective",
        "mlcc_effective": "hvr_effective",
        "microbump_underfill_homog": "underfill_homog"}

_Z4_CFG = None


def _z4_cfg() -> dict:
    global _Z4_CFG
    if _Z4_CFG is None:
        import yaml
        _Z4_CFG = yaml.safe_load(
            (R / "configs" / "phase0mr2" / "z4_stack.yaml").read_text())
    return _Z4_CFG


def conv_above_layers(arch: str) -> float:
    """Thickness of a converter layer sitting ABOVE the substrate (ARCH_Z4)."""
    return CONV_CELL_MM if CONV_PLACE[arch] == "above" else 0.0


def corner_joint_response(arch: str, h_sub_mm: float, p_conv_w: float, p_die_w: float,
                          h_top: float, board_case: str = "fr4_1p6mm",
                          wd: Path | None = None, t_ref_c: float = 25.0,
                          h_xy: float = 0.80) -> dict:
    """Solve the global package and return the corner-BGA relative displacement and
    temperature. One thermal solve, one structural solve -- no ET iteration, because the
    converter loss is supplied by the Sec.4 electrical model."""
    wd = wd or (R / "results" / "phase0i" / "global")
    wd.mkdir(parents=True, exist_ok=True)
    doe = load_doe()
    st, extra, t_tile = stack_for(arch, h_sub_mm, board_case)
    n_vr = 49
    side = math.sqrt(274.89 / n_vr)
    xy = kw1.tiles_for("uniform", side, st, doe, n_vr)
    tiles = [Tile(cx, cy, side, side, p_conv_w / n_vr) for cx, cy in xy]
    m = build(tiles, st, h_sub_mm, h_xy=h_xy, z_scale=1.4, support_layer=False,
              extra_bottom_layers=extra)
    if len(m.elems) > 40000:
        raise RuntimeError(f"{len(m.elems)} elements over the ceiling")
    mats = build_materials(st)
    ti = wd / f"{arch}_th.inp"
    films = ccxio.write_thermal(m, mats, tiles, st, p_die_w, h_top, ti)
    ccxio.run_ccx(ti, threads=8)
    Tn = ccxio.read_frd(wd / f"{arch}_th.frd")["NDTEMP"]
    tm = metrics.thermal_metrics(m, Tn, films, st, p_die_w + p_conv_w, h_top)
    Tnode = Tn[1:m.n_nodes + 1, 0]
    si = wd / f"{arch}_st.inp"
    ccxio.write_structural(m, mats, Tnode, st, "BC_BOARD", si, solver="")
    ccxio.run_ccx(si, threads=8)
    s = ccxio.read_frd(wd / f"{arch}_st.frd")
    U = s["DISP"]
    sm = metrics.structural_metrics(m, U, s["STRESS"], st)

    # ---- corner-BGA relative displacement -------------------------------------------
    # The ball layer spans [z_bga0, z_bga1]. The joint shear is the in-plane displacement
    # difference between its top and bottom faces at the greatest distance from the neutral
    # point, which is where a BGA fails first.
    zl = {L.name: (L.z0, L.z1) for L in m.layers}
    z0, z1 = zl["bga"]
    nb = m.node_ids_at_z(z0)
    nt = m.node_ids_at_z(z1)
    pb, pt = m.nodes[nb - 1], m.nodes[nt - 1]
    rb = np.hypot(pb[:, 0], pb[:, 1])
    rmax = rb.max()
    sel_b = nb[rb > 0.92 * rmax]
    du_max, T_joint = 0.0, []
    for idb in sel_b:
        p = m.nodes[idb - 1]
        j = int(np.argmin((pt[:, 0] - p[0]) ** 2 + (pt[:, 1] - p[1]) ** 2))
        idt = nt[j]
        d = math.hypot(U[idt, 0] - U[idb, 0], U[idt, 1] - U[idb, 1])
        du_max = max(du_max, d)
        T_joint.append(0.5 * (Tnode[idb - 1] + Tnode[idt - 1]))
    return {"arch": arch, "h_sub_mm": h_sub_mm, "board_case": board_case,
            "n_elem": len(m.elems), "conv_placement": CONV_PLACE[arch],
            "T_max_C": tm["T_max_C"], "T_joint_C": float(np.mean(T_joint)),
            "T_joint_max_C": float(np.max(T_joint)),
            "du_corner_um": du_max * 1000.0,
            "bga_standoff_mm": z1 - z0,
            "shear_strain_pct": 100.0 * du_max / (z1 - z0),
            "die_warpage_pv_um": sm["die_warpage_pv_um"],
            "pkg_warpage_pv_um": sm["pkg_warpage_pv_um"],
            "energy_residual_pct": tm.get("energy_residual_pct", float("nan"))}
