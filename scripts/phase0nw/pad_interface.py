"""PHASE 0N-AE --- the die-side interface, from VERIFIED Table III of the DVPD source.

Table III of 10.1109/TCPMT.2026.3724907 (open version arXiv:2606.28837) was fetched and
read directly this phase. The RDL/Chiplet column is:

    Type Pads | Material Cu | d_c 10 um | h_c 10 um | p_c 20 um | A_c 100 um^2
    R_c 1.7 mOhm | 48V/1V # VICs 200,000 | Area 20 mm^2

and footnote b gives "Solder resistivity: 130 nOhm.m, Cu resistivity: 17 nOhm.m" --
which independently confirms the two resistivities this framework already used.

THE PAD IS NOT CIRCULAR. d_c = 10 um with A_c = 100 um^2 is a 10x10 um SQUARE:
pi*(5 um)^2 = 78.54 um^2, not 100. Using a circular reading would understate the area by
21% and overstate the resistance by the same factor. The source's own A_c is used.

THE SOURCE'S R_c IS PURE BULK. rho_Cu * h / A = 17e-9 * 10e-6 / 100e-12 = 1.700 mOhm,
matching Table III's 1.7 exactly. So the published pad resistance contains NO extra
contact, UBM or spreading term -- a Cu pad, not a solder microbump. Same check on the
other columns: BGA 130e-9*300e-6/125663e-12 = 0.3104 mOhm against 0.3, and TSV
17e-9*300e-6/707e-12 = 7.2136 against 7.1 (1.6% rounding). The table is internally
consistent with simple rho*L/A throughout.

TWO INTERFACE TECHNOLOGIES, KEPT APART:
  IF_PAD_SRC  the Table III Cu pad. PRIMARY. No solder, no IMC, no UBM term, because
              the source's own resistance is exactly bulk Cu and contains none.
  IF_MB_ALT   a Cu-pillar / solder-cap / UBM / IMC microbump. ALTERNATIVE TECHNOLOGY
              only, and the only place the solder-microbump literature applies.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for _p in ("scripts/phase0nw", "scripts/phase0m", "scripts/phase0mr", "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))
from interconnect import rho_cu                                        # noqa: E402

DOI = "10.1109/TCPMT.2026.3724907"
ARXIV = "arXiv:2606.28837"

# --- Table III, RDL/Chiplet column. VERIFIED by direct read this phase. ---------------
PAD_D_UM, PAD_H_UM, PAD_P_UM = 10.0, 10.0, 20.0
PAD_A_UM2 = 100.0                 # SOURCE value; NOT pi*(d/2)^2
PAD_R_SRC_MOHM = 1.7
PAD_SHAPE = "square_10x10_um"     # inferred from A_c = 100 = 10*10, not pi*25
PAD_SHAPE_STATUS = ("DERIVED -- A_c = 100 um^2 is exactly 10x10; a circular reading "
                    "gives 78.54 um^2 and contradicts the source's own A_c")
SRC_VIC_48V1V = 200_000
SRC_AREA_MM2 = 20.0
SRC_BGA_VIC_48V1V = 132
SRC_BGA_AREA_MM2 = 85.0

# The source states VIC count is sized from "the connection current and per-via current
# limit, with current assumed to be uniformly distributed". The LIMIT ITSELF IS NEVER
# PUBLISHED in the paper text, so no allowable is taken from it.
SRC_PER_VIA_LIMIT_A = None
SRC_PER_VIA_LIMIT_STATUS = ("OPEN -- the source references a per-via current limit but "
                            "never gives its value")
SRC_VIC_SEMANTICS = ("AMBIGUOUS -- the paper does not state whether a VIC count is one "
                     "rail, supply+return combined, or current-carrying only. Area = "
                     "count * pitch^2 holds (132*0.8^2 = 84.5 vs 85 mm^2), which fixes "
                     "the count as physical sites but not their rail assignment")


def pad_bulk_resistance_ohm(T_c: float = 20.0) -> float:
    """rho_Cu(T) * h / A using the SOURCE's area, not a circular approximation."""
    return rho_cu(T_c) * (PAD_H_UM * 1e-6) / (PAD_A_UM2 * 1e-12)


def pad_circular_misreading_ohm(T_c: float = 20.0) -> float:
    """What a circular d_c = 10 um reading would give. For the guard, never for use."""
    a = math.pi * (PAD_D_UM / 2 * 1e-6) ** 2
    return rho_cu(T_c) * (PAD_H_UM * 1e-6) / a


def source_cross_check() -> dict:
    """Does Table III's R_c follow from its own geometry and resistivity?"""
    bulk = pad_bulk_resistance_ohm(20.0)
    return {"source_R_mohm": PAD_R_SRC_MOHM, "bulk_R_mohm": bulk * 1e3,
            "rel_diff": abs(bulk * 1e3 - PAD_R_SRC_MOHM) / PAD_R_SRC_MOHM,
            "conclusion": ("Table III's pad resistance IS simple bulk Cu; it contains no "
                           "contact, UBM or IMC term, which is consistent with a Cu pad "
                           "and inconsistent with a solder microbump"),
            "circular_misreading_mohm": pad_circular_misreading_ohm(20.0) * 1e3}


def geometric_capacity(footprint_mm2: float, keepout_frac: float = 0.30) -> dict:
    """How many pads physically fit, at the source pitch, in a given footprint.

    keepout_frac is BOUNDED_ENGINEERING: the interface cannot use the whole cell
    footprint because components and other interconnect consume part of it. It is a
    declared fraction, not a sourced one, and is swept.
    """
    usable = footprint_mm2 * (1.0 - keepout_frac)
    per_pad_mm2 = (PAD_P_UM * 1e-3) ** 2
    n = int(usable / per_pad_mm2)
    return {"footprint_mm2": footprint_mm2, "keepout_frac": keepout_frac,
            "keepout_status": "BOUNDED_ENGINEERING -- declared, swept, not sourced",
            "usable_mm2": usable, "pitch_area_mm2": per_pad_mm2,
            "n_total": n, "n_vdd": n // 2, "n_gnd": n // 2}


def size_for_cell(i_cell_rms_a: float, footprint_mm2: float = 5.61,
                  drop_budget_frac: float = 0.01, v_rail: float = 1.0,
                  T_c: float = 20.0, keepout_frac: float = 0.30) -> dict:
    """PAD-DROP, PAD-GEOM and the adopted count for ONE cell.

    No EM allowable is used, because the source does not publish one.
    """
    r_one = pad_bulk_resistance_ohm(T_c)
    budget_v = drop_budget_frac * v_rail
    # one rail: n pads in parallel must keep I*R below the budget
    n_drop = max(1, math.ceil(i_cell_rms_a * r_one / budget_v))
    geom = geometric_capacity(footprint_mm2, keepout_frac)
    n_adopt = min(geom["n_vdd"], max(n_drop, geom["n_vdd"]))   # geometry-limited
    out = {}
    for tag, n in (("PAD_DROP", n_drop), ("PAD_GEOM", geom["n_vdd"]),
                   ("PAD_ADOPTED", n_adopt)):
        r_rail = r_one / n
        out[tag] = {"n_per_rail": n, "r_rail_ohm": r_rail,
                    "i_per_pad_a": i_cell_rms_a / n,
                    "j_per_pad_A_cm2": (i_cell_rms_a / n) / (PAD_A_UM2 * 1e-8),
                    "v_drop_v": i_cell_rms_a * r_rail,
                    "p_rail_w": i_cell_rms_a ** 2 * r_rail}
    out.update({"i_cell_rms_a": i_cell_rms_a, "r_one_pad_ohm": r_one,
                "budget_v": budget_v,
                "budget_status": "BOUNDED_ENGINEERING -- declared drop budget",
                "em_allowable": None,
                "em_status": SRC_PER_VIA_LIMIT_STATUS,
                "geometry": geom,
                "selection_criterion": ("adopted = geometry-limited count; the "
                                        "drop-limited count is far smaller, so geometry "
                                        "rather than voltage drop sets the field")})
    return out


def system(i_cell_rms_a: float, cells: int = 49, **kw) -> dict:
    c = size_for_cell(i_cell_rms_a, **kw)
    a = c["PAD_ADOPTED"]
    return {"interface": "IF_PAD_SRC", "source": f"{DOI} Table III ({ARXIV})",
            "cells": cells, "per_cell": c,
            "n_vdd_total": a["n_per_rail"] * cells,
            "n_gnd_total": a["n_per_rail"] * cells,
            "p_pad_vdd_w": a["p_rail_w"] * cells,
            "p_pad_gnd_w": a["p_rail_w"] * cells,
            "p_pad_total_w": 2 * a["p_rail_w"] * cells,
            "geometry_maturity": "CLOSED", "current_maturity": "CLOSED",
            "loss_maturity": "CLOSED",
            "note": ("the 1 V cell output RMS is known from the converter model, so this "
                     "interface's loss is genuinely closed at T_ref")}


def source_comparison(our_n_vdd: int, our_n_gnd: int) -> dict:
    """Our count against the source's, WITHOUT forcing agreement."""
    return {"source_vic_48v1v": SRC_VIC_48V1V, "source_area_mm2": SRC_AREA_MM2,
            "source_semantics": SRC_VIC_SEMANTICS,
            "our_n_vdd": our_n_vdd, "our_n_gnd": our_n_gnd,
            "our_total": our_n_vdd + our_n_gnd,
            "why_not_copied": ("the source optimized a 70-VR architecture; our design "
                               "has 49 cells and a different cell footprint, so its "
                               "total count is not transferable. The source's VALUES "
                               "(geometry, resistance, resistivity) are used; its "
                               "ALLOCATION is not")}


if __name__ == "__main__":
    import rms_currents as RMS
    cc = RMS.cell_currents()
    x = source_cross_check()
    print(f"Table III pad: {PAD_D_UM:.0f} um d_c, A_c {PAD_A_UM2:.0f} um^2, "
          f"{PAD_SHAPE}")
    print(f"  source R_c {x['source_R_mohm']} mOhm | bulk rho*h/A "
          f"{x['bulk_R_mohm']:.4f} mOhm | rel diff {x['rel_diff']*100:.2f} %")
    print(f"  a CIRCULAR misreading would give {x['circular_misreading_mohm']:.4f} mOhm "
          f"({x['circular_misreading_mohm']/x['bulk_R_mohm']:.3f}x too high)")
    s = system(cc["i_cell_out_rms_a"])
    c = s["per_cell"]
    print(f"\nper cell at I_rms {c['i_cell_rms_a']:.4f} A:")
    for t in ("PAD_DROP", "PAD_GEOM", "PAD_ADOPTED"):
        v = c[t]
        print(f"  {t:12s} n/rail {v['n_per_rail']:6d}  R {v['r_rail_ohm']*1e6:9.3f} uohm"
              f"  drop {v['v_drop_v']*1e3:7.4f} mV  P {v['p_rail_w']*1e3:8.3f} mW")
    print(f"\nsystem: {s['n_vdd_total']} VDD + {s['n_gnd_total']} GND pads, "
          f"P_pad total {s['p_pad_total_w']*1e3:.2f} mW")
    print(f"source 48V/1V VIC count {SRC_VIC_48V1V} -- {SRC_VIC_SEMANTICS[:60]}...")
    out = R / "research" / "phase0nae"
    out.mkdir(parents=True, exist_ok=True)
    (out / "pad_interface.json").write_text(json.dumps(
        {"cross_check": x, "system": s,
         "source_comparison": source_comparison(s["n_vdd_total"], s["n_gnd_total"])},
        indent=1, sort_keys=True))
