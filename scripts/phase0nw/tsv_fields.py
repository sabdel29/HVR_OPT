"""PHASE 0N-W --- explicit VDD and GND TSV fields, per cell (brief section 16).

The historical model had ONE homogenized `tsv_homog` block per tile. That cannot answer
the questions the brief asks, because supply and return are not distinguishable inside it:
you cannot report a VDD count, a GND count, or a loop resistance from a single smeared
medium.

This module builds the two fields explicitly as interleaved sub-lattices on the SOURCE_BACKED
30 um / 60 um TSV geometry, and reports each rail separately.

TWO THINGS THE BRIEF WARNS ABOUT, BOTH HANDLED HERE.

1. "Do not say one local cell field carries 1 kA." It does not. Each cell carries
   I_cell = I_total / 49. The kiloamp figure is the SYSTEM aggregate across all 49 cells,
   and appears here only as a sum.

2. "Do not rely solely on R_loop = 2 R_field." The loop is not two field resistances in
   series. Current must converge from the plane into the via mouths and spread back out
   at the far end, and that constriction resistance is not part of the parallel bundle.
   R_loop = R_vdd + R_gnd + 2 R_spread, with the spreading term computed, reported
   separately, and shown as a percentage of the total so it cannot be waved away.
"""
from __future__ import annotations

import math

# --- SOURCE_BACKED geometry (June-2026 Table III, via package_stack.yaml) --------------
D_TSV_MM = 0.030
P_TSV_MM = 0.060
RHO_CU_20C = 1.68e-8          # ohm.m, annealed copper
ALPHA_CU = 3.9e-3             # 1/K, temperature coefficient of resistivity


def _lattice(cell_side_mm: float, pitch_mm: float, keepout_mm: float = 0.05):
    """Interleaved VDD/GND sites on a square lattice, centred on the cell.

    Checkerboard interleaving: every VDD via has GND nearest neighbours in x and y. That
    minimises loop inductance and makes the two fields co-located, so neither rail sees a
    systematically different thermal or mechanical environment -- which a block-split
    (VDD on one half, GND on the other) would not give.
    """
    usable = cell_side_mm - 2 * keepout_mm
    n = int(usable // pitch_mm)
    if n < 2:
        raise ValueError(f"cell side {cell_side_mm} mm holds no TSV lattice at {pitch_mm} mm")
    off = (n - 1) * pitch_mm / 2.0          # centred, as in the BGA lattice fix
    vdd, gnd = [], []
    for i in range(n):
        for j in range(n):
            xy = (-off + i * pitch_mm, -off + j * pitch_mm)
            (vdd if (i + j) % 2 == 0 else gnd).append(xy)
    return n, vdd, gnd


def _first_moment(pts):
    if not pts:
        return (0.0, 0.0)
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def field_resistance(n_via: int, h_mm: float, d_mm: float, T_C: float = 20.0) -> float:
    """Parallel bundle resistance of n_via copper vias of length h."""
    rho = RHO_CU_20C * (1.0 + ALPHA_CU * (T_C - 20.0))
    a_m2 = math.pi * (d_mm / 2 * 1e-3) ** 2
    return rho * (h_mm * 1e-3) / a_m2 / max(n_via, 1)


def spreading_resistance(n_via: int, d_mm: float, pitch_mm: float, T_C: float = 20.0) -> float:
    """Constriction resistance converging from a plane into n_via mouths.

    Classical circular-contact constriction, R = rho / (2 d) per contact (Holm), with the
    contacts in parallel and a Nusselt-type correction for the finite cell the current
    arrives from. This is the term that makes R_loop != 2 R_field.
    """
    rho = RHO_CU_20C * (1.0 + ALPHA_CU * (T_C - 20.0))
    a = d_mm / 2 * 1e-3
    b = pitch_mm / 2 * 1e-3                      # half-pitch = equivalent cell radius
    xi = min(a / b, 0.999)
    # constriction with finite-domain correction (1 - xi)^1.5
    r_one = rho / (4 * a) * (1 - xi) ** 1.5
    return r_one / max(n_via, 1)


def cell_report(cell_side_mm: float, h_tsv_mm: float, i_cell_a: float,
                pitch_mm: float = P_TSV_MM, d_mm: float = D_TSV_MM,
                T_C: float = 20.0) -> dict:
    """Everything brief section 16 asks for, for ONE cell."""
    n, vdd, gnd = _lattice(cell_side_mm, pitch_mm)
    a_via_mm2 = math.pi * (d_mm / 2) ** 2
    a_cell_mm2 = cell_side_mm ** 2

    r_vdd = field_resistance(len(vdd), h_tsv_mm, d_mm, T_C)
    r_gnd = field_resistance(len(gnd), h_tsv_mm, d_mm, T_C)
    r_spread_v = spreading_resistance(len(vdd), d_mm, pitch_mm, T_C)
    r_spread_g = spreading_resistance(len(gnd), d_mm, pitch_mm, T_C)
    r_loop = r_vdd + r_gnd + r_spread_v + r_spread_g
    r_loop_naive = 2 * r_vdd

    j_vdd = i_cell_a / len(vdd) / (a_via_mm2 * 1e-2)      # A/cm^2
    j_gnd = i_cell_a / len(gnd) / (a_via_mm2 * 1e-2)

    return {
        "lattice_n": n,
        "n_vdd": len(vdd), "n_gnd": len(gnd), "n_total": len(vdd) + len(gnd),
        "diameter_um": d_mm * 1e3, "pitch_um": pitch_mm * 1e3,
        "h_tsv_um": h_tsv_mm * 1e3,
        "cu_area_fraction_vdd": len(vdd) * a_via_mm2 / a_cell_mm2,
        "cu_area_fraction_gnd": len(gnd) * a_via_mm2 / a_cell_mm2,
        "cu_area_fraction_total": (len(vdd) + len(gnd)) * a_via_mm2 / a_cell_mm2,
        "i_cell_a": i_cell_a,
        "i_per_via_vdd_ma": 1e3 * i_cell_a / len(vdd),
        "i_per_via_gnd_ma": 1e3 * i_cell_a / len(gnd),
        "j_vdd_A_cm2": j_vdd, "j_gnd_A_cm2": j_gnd,
        "r_vdd_ohm": r_vdd, "r_gnd_ohm": r_gnd,
        "r_spread_vdd_ohm": r_spread_v, "r_spread_gnd_ohm": r_spread_g,
        "r_loop_ohm": r_loop,
        "r_loop_naive_2rfield_ohm": r_loop_naive,
        "spreading_share_pct": 100.0 * (r_spread_v + r_spread_g) / r_loop,
        "naive_error_pct": 100.0 * (r_loop_naive - r_loop) / r_loop,
        "p_vdd_w": i_cell_a ** 2 * (r_vdd + r_spread_v),
        "p_gnd_w": i_cell_a ** 2 * (r_gnd + r_spread_g),
        "p_loop_w": i_cell_a ** 2 * r_loop,
        "first_moment_vdd_mm": _first_moment(vdd),
        "first_moment_gnd_mm": _first_moment(gnd),
    }


def system_report(cells: int, cell_side_mm: float, h_tsv_mm: float, i_total_a: float,
                  **kw) -> dict:
    """Aggregate across all cells. The kiloamp figure lives HERE, not in a cell."""
    i_cell = i_total_a / cells
    c = cell_report(cell_side_mm, h_tsv_mm, i_cell, **kw)
    return {
        "cells": cells,
        "i_total_a": i_total_a, "i_cell_a": i_cell,
        "per_cell": c,
        "n_vdd_total": c["n_vdd"] * cells, "n_gnd_total": c["n_gnd"] * cells,
        "p_vdd_total_w": c["p_vdd_w"] * cells,
        "p_gnd_total_w": c["p_gnd_w"] * cells,
        "p_tsv_total_w": c["p_loop_w"] * cells,
    }
