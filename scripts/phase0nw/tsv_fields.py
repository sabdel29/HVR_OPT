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
from pathlib import Path

R = Path(__file__).resolve().parents[2]

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


def spreading_resistance(n_via: int, d_mm: float, pitch_mm: float, T_C: float = 20.0,
                         ends: int = 2) -> float:
    """Constriction resistance of a via bundle fed from a plane, counting BOTH ends.

    DERIVATION, AND WHY `ends` DEFAULTS TO 2.

    A circular contact of radius `a` delivering current into a semi-infinite conductor of
    resistivity rho has the classical spreading resistance

        R_1end = rho / (4 a)

    for ONE such interface. The physical path through a TSV rail has two of them: current
    converges out of the land-side plane into the via mouths at one end, and diverges back
    out of the via mouths into the receiving plane at the other. That is Holm's
    constriction resistance for a contact between two conductors,

        R_both = 2 * rho / (4 a) = rho / (2 a)

    The first version of this module returned the ONE-END value and the caller added it
    once per rail, so the loop was short by one constriction per rail. `ends` makes the
    count explicit and testable rather than buried in a caller's arithmetic.

    The finite-domain factor (1 - xi)^1.5, with xi = a / b and b the half-pitch, corrects
    the semi-infinite result for the fact that each via draws from a finite cell rather
    than an unbounded half-space. It is a standard Nusselt-type correction and is carried
    as an approximation, not a sourced constant.
    """
    if ends not in (1, 2):
        raise ValueError(f"ends must be 1 or 2, not {ends}")
    rho = RHO_CU_20C * (1.0 + ALPHA_CU * (T_C - 20.0))
    a = d_mm / 2 * 1e-3
    b = pitch_mm / 2 * 1e-3                      # half-pitch = equivalent cell radius
    xi = min(a / b, 0.999)
    r_one_end = rho / (4 * a) * (1 - xi) ** 1.5
    return ends * r_one_end / max(n_via, 1)


def cell_report(cell_side_mm: float, h_tsv_mm: float, i_cell_a: float,
                pitch_mm: float = P_TSV_MM, d_mm: float = D_TSV_MM,
                T_C: float = 20.0) -> dict:
    """Everything brief section 16 asks for, for ONE cell."""
    n, vdd, gnd = _lattice(cell_side_mm, pitch_mm)
    a_via_mm2 = math.pi * (d_mm / 2) ** 2
    a_cell_mm2 = cell_side_mm ** 2

    r_vdd = field_resistance(len(vdd), h_tsv_mm, d_mm, T_C)
    r_gnd = field_resistance(len(gnd), h_tsv_mm, d_mm, T_C)
    # both ends of each rail -- see spreading_resistance()
    r_spread_v = spreading_resistance(len(vdd), d_mm, pitch_mm, T_C, ends=2)
    r_spread_g = spreading_resistance(len(gnd), d_mm, pitch_mm, T_C, ends=2)
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
        "spreading_ends_per_rail": 2,
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
                  n_per_cell: int | None = None, **kw) -> dict:
    """Aggregate across all cells. The kiloamp figure lives HERE, not in a cell."""
    i_cell = i_total_a / cells
    if n_per_cell is not None:
        # select the coarsest lattice pitch whose site count does not exceed n_per_cell
        import math as _m
        kw = dict(kw)
        kw["pitch_mm"] = P_TSV_MM * max(1, int(_m.ceil(
            _m.sqrt(_lattice(cell_side_mm, P_TSV_MM)[0] ** 2 / max(n_per_cell, 1)))))
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


# =======================================================================================
# SECTION 4 --- Z1 AND Z2 HAVE DIFFERENT TSV ELECTRICAL NETWORKS
#
# This is a core physical distinction of the paper, and the first version of this module
# erased it by assuming 1000 A for everything.
#
#   Z1  the through-substrate field carries the 48 V INPUT at low current,
#       I = P_in / 48 V -- a few amps.
#   Z2  the through-substrate field carries the 1 V OUTPUT at ~kiloamp system current.
#
# Same geometry. The through-substrate rail CURRENT differs by more than 40x
# (1000 A against ~23.7 A), and because Joule loss goes as I^2 the TSV LOSS differs by
# roughly three orders of magnitude. Those two ratios are not the same number and must
# not be quoted interchangeably: 42.2^2 = 1781, which is the loss ratio the model
# produces. Any statement that the two architectures have "the same via field" is false
# in the only sense that matters electrically.
#
# P_in is NOT hard-coded. It must come from the physical electrical solution; until that
# exists the caller passes the historical Phase-0M-R3C value explicitly and the result is
# labelled a placeholder, so no one can mistake it for a physical result.
# =======================================================================================

V_IN_48 = 48.0
V_OUT_1 = 1.0


# ---------------------------------------------------------------------------------------
# POWER BOOKKEEPING. The three quantities below are NOT interchangeable, and conflating
# two of them is the defect this block exists to prevent.
#
#   p_load_w    the useful power delivered to the die            (1000 W)
#   p_loss_w    everything dissipated getting it there           (~137 W)
#   p_input_w   what the 48 V supply must deliver = load + loss  (~1137 W)
#
# The first version of this module stored the LOSS under the name P_IN_PLACEHOLDER_W and
# then divided it by 48 V. That is not an approximation of the input current, it is a
# different quantity: it gave 2.86 A where the correct historical-order figure is
# 23.69 A -- low by 8.3x in current and by 69x in any I^2 R derived from it.
#
# Nothing here is hard-coded. P_load comes from the architecture config and the
# historical losses are RE-SUMMED from the frozen replay's own L_P_* columns, which also
# demonstrates that P_total_electronics_w is a loss total rather than an input power.
# ---------------------------------------------------------------------------------------

_ARCH_YAML = R / "configs" / "phase0i" / "z_architectures.yaml"
_REPLAY_CSV = R / "results" / "phase0mr3c" / "final_etm_replay.csv"


def _load_power_w() -> float:
    import yaml
    c = yaml.safe_load(_ARCH_YAML.read_text())
    for node in (c, *(v for v in c.values() if isinstance(v, dict))):
        if isinstance(node, dict) and isinstance(node.get("load"), dict):
            return float(node["load"]["power_w"])
    raise KeyError(f"no load.power_w in {_ARCH_YAML}")


def _historical_losses_w() -> dict:
    """Phase-0M-R3C electronics LOSS per architecture, re-summed from the L_P_* columns.

    Deliberately recomputed rather than read from P_total_electronics_w: the sum IS the
    proof that the column is a loss total. If a future edit makes them disagree, that is
    a finding, not a rounding issue, so it raises.
    """
    import csv
    out = {}
    for r in csv.DictReader(_REPLAY_CSV.open()):
        terms = sum(float(v) for k, v in r.items() if k.startswith("L_P_"))
        stated = float(r["P_total_electronics_w"])
        if abs(terms - stated) > 1e-9:
            raise ValueError(
                f"{r['arch']}: sum(L_P_*) = {terms!r} but P_total_electronics_w = "
                f"{stated!r}; the column is no longer a pure loss total")
        out["Z1" if "Z1" in r["arch"] else "Z2"] = terms
    return out


P_LOAD_W = _load_power_w()
P_LOSS_PLACEHOLDER_W = _historical_losses_w()


def input_power_w(p_load_w: float, p_loss_w: float) -> float:
    """p_input = p_load + p_loss. The one place this sum is formed."""
    if p_loss_w > p_load_w:
        raise ValueError(
            f"p_loss_w = {p_loss_w} exceeds p_load_w = {p_load_w}. That is possible in "
            f"principle but is overwhelmingly likely to be the load/loss/input mix-up "
            f"this function exists to catch -- pass the LOSS, not the input power.")
    return p_load_w + p_loss_w


def rail_current_48v(p_load_w: float, p_loss_w: float) -> float:
    return input_power_w(p_load_w, p_loss_w) / V_IN_48


def z1_rail_report(cfg, p_loss_w: float | None = None, p_load_w: float | None = None,
                   h_tsv_mm: float = 0.300, T_C: float = 20.0,
                   n_per_cell: int | None = None) -> dict:
    """Z1's 48 V through-substrate rail.

    I = (P_load + P_loss) / 48 V. `p_loss_w` is the ELECTRICAL LOSS, not the input power;
    passing an input power here would be caught by input_power_w().
    """
    placeholder = p_loss_w is None
    p_load = P_LOAD_W if p_load_w is None else p_load_w
    p_loss = P_LOSS_PLACEHOLDER_W["Z1"] if placeholder else p_loss_w
    p_in = input_power_w(p_load, p_loss)
    i_total = p_in / V_IN_48
    r = system_report(cfg.cells, cfg.cell_side_mm, h_tsv_mm, i_total, T_C=T_C,
                      n_per_cell=n_per_cell)
    r.update({"architecture": "Z1", "rail_v": V_IN_48,
              "p_load_w": p_load, "p_loss_w": p_loss, "p_input_w": p_in,
              "placeholder": placeholder,
              "source": ("Phase-0M-R3C electronics LOSS + load (PLACEHOLDER)"
                         if placeholder else "physical electrical loss ledger")})
    return r


def z2_rail_report(cfg, i_load_a: float = 1000.0, h_tsv_mm: float = 0.300,
                   T_C: float = 20.0, n_per_cell: int | None = None) -> dict:
    """Z2's 1 V through-substrate rail, carrying the load current itself."""
    r = system_report(cfg.cells, cfg.cell_side_mm, h_tsv_mm, i_load_a, T_C=T_C,
                      n_per_cell=n_per_cell)
    r.update({"architecture": "Z2", "rail_v": V_OUT_1, "i_load_a": i_load_a,
              "p_load_w": P_LOAD_W, "placeholder": False,
              "source": "1 V load current; to be updated self-consistently with losses"})
    return r


# =======================================================================================
# SECTION 5 --- THE TSV COUNT IS A DESIGN CHOICE, NOT "whatever fits"
#
# 685 VDD + 684 GND is simply the densest lattice the cell will hold. That is a geometric
# upper bound, not a requirement, and it must not drift into being "the physical TSV
# count" by default.
#
# NO EM / CURRENT-DENSITY ALLOWABLE IS INVENTED HERE. None is available for this via
# geometry, so the field is bracketed instead: a minimum set by a declared voltage-drop
# budget, the geometric maximum, and a midpoint. The adopted point is named explicitly.
# =======================================================================================

# Declared design budget. BOUNDED: an engineering choice, not a sourced allowable.
V_DROP_BUDGET_FRAC = 0.01        # 1 % of the rail voltage across the TSV field


def _n_for_lattice(cell_side_mm, pitch_mm):
    n, vdd, gnd = _lattice(cell_side_mm, pitch_mm)
    return n, len(vdd), len(gnd)


def sizing_study(cfg, i_total_a: float = 1000.0, rail_v: float = V_OUT_1,
                 h_tsv_mm: float = 0.300, T_C: float = 20.0) -> dict:
    """Three-point TSV field bracket for one rail.

    min_drop     the coarsest lattice still meeting the declared voltage-drop budget
    max_density  the finest lattice the cell geometry permits
    mid          between them

    Each point reports the drop it actually achieves, so the budget is auditable.
    """
    i_cell = i_total_a / cfg.cells
    budget_v = V_DROP_BUDGET_FRAC * rail_v

    def point(pitch_mm):
        n, nv, ng = _n_for_lattice(cfg.cell_side_mm, pitch_mm)
        r_v = (field_resistance(nv, h_tsv_mm, D_TSV_MM, T_C)
               + spreading_resistance(nv, D_TSV_MM, pitch_mm, T_C, ends=2))
        r_g = (field_resistance(ng, h_tsv_mm, D_TSV_MM, T_C)
               + spreading_resistance(ng, D_TSV_MM, pitch_mm, T_C, ends=2))
        r_loop = r_v + r_g
        return {"pitch_um": pitch_mm * 1e3, "lattice_n": n, "n_vdd": nv, "n_gnd": ng,
                "n_total": nv + ng, "r_loop_ohm": r_loop,
                "v_drop_v": i_cell * r_loop,
                "v_drop_frac_of_rail": i_cell * r_loop / rail_v,
                "p_loop_w": i_cell ** 2 * r_loop,
                "meets_budget": i_cell * r_loop <= budget_v}

    # coarsest pitch (fewest vias) that still meets the budget
    candidates = [round(P_TSV_MM * k, 4) for k in (1, 2, 3, 4, 6, 8, 12, 16)]
    feasible = [p for p in candidates if point(p)["meets_budget"]]
    p_min = max(feasible) if feasible else P_TSV_MM
    p_max = P_TSV_MM
    p_mid = min(candidates, key=lambda p: abs(p - 0.5 * (p_min + p_max)))

    return {
        "rail_v": rail_v, "i_total_a": i_total_a, "i_cell_a": i_cell,
        "budget_frac": V_DROP_BUDGET_FRAC, "budget_v": budget_v,
        "budget_status": "BOUNDED -- declared engineering budget, not a sourced allowable",
        "current_density_allowable": None,
        "current_density_note": ("no validated EM/current-density allowable exists for "
                                 "this via geometry, so none is asserted; the field is "
                                 "bracketed by voltage drop and geometry instead"),
        "min_drop": point(p_min), "mid": point(p_mid), "max_density": point(p_max),
        "adopted": "max_density",
        "adopted_rationale": ("the mechanical and thermal models need the copper volume "
                              "fraction to be an upper bound on stiffening and spreading; "
                              "the ELECTRICAL bracket is reported alongside so the "
                              "sensitivity is visible. This is a MAXIMUM-DENSITY field, "
                              "explicitly not a minimum-required one."),
    }


# =======================================================================================
# SECTIONS 9 AND 10 --- PER-ARCHITECTURE SIZING, AND THE TWO DISTINCT COMPARISONS
#
# sizing_study() defaults to 1 V / 1000 A. That is a Z2 study, and reporting its
# 81 / 324 / 1369 bracket as if it applied to Z1 too would be wrong: Z1's rail is 48 V at
# ~23.7 A, so its drop budget is 480 mV against 10 mV and its current is 42x lower. The
# minimum field it needs is therefore dramatically smaller.
#
# TWO COMPARISONS, AND THEY MUST NOT BE MIXED:
#
#   Study A, SAME-FIELD (primary). Identical physical via fabric in both architectures.
#       Isolates the rail assignment itself -- what happens when the same fabric carries
#       48 V at low current versus 1 V at high current. Any difference is attributable to
#       the electrical architecture, not to one design having more copper.
#
#   Study B, AS-DESIGNED (sensitivity). Each field sized independently to its own
#       declared criterion. Answers what provisioned architectures would look like, but
#       confounds rail assignment with copper content, so it cannot be the primary
#       physics comparison.
# =======================================================================================

PRIMARY_TSV_COMPARISON = "A_same_field"


def z1_sizing_study(cfg, p_loss_w: float | None = None, p_load_w: float | None = None,
                    **kw) -> dict:
    """Z1's field sized against its own 48 V rail and its own drop budget."""
    p_load = P_LOAD_W if p_load_w is None else p_load_w
    p_loss = P_LOSS_PLACEHOLDER_W["Z1"] if p_loss_w is None else p_loss_w
    i = input_power_w(p_load, p_loss) / V_IN_48
    s = sizing_study(cfg, i_total_a=i, rail_v=V_IN_48, **kw)
    s.update({"architecture": "Z1", "placeholder": p_loss_w is None})
    return s


def z2_sizing_study(cfg, i_load_a: float = 1000.0, **kw) -> dict:
    """Z2's field sized against its own 1 V rail."""
    s = sizing_study(cfg, i_total_a=i_load_a, rail_v=V_OUT_1, **kw)
    s.update({"architecture": "Z2", "placeholder": False})
    return s


def comparison_studies(cfg, **kw) -> dict:
    """Study A (same field, primary) and Study B (independently sized, sensitivity)."""
    z1, z2 = z1_rail_report(cfg, **kw), z2_rail_report(cfg, **kw)
    s1, s2 = z1_sizing_study(cfg), z2_sizing_study(cfg)
    return {
        "primary": PRIMARY_TSV_COMPARISON,
        "A_same_field": {
            "rule": "identical maximum-density fabric in both; only the rail differs",
            "n_per_cell": z1["per_cell"]["n_total"],
            "z1": {"i_total_a": z1["i_total_a"], "p_tsv_w": z1["p_tsv_total_w"]},
            "z2": {"i_total_a": z2["i_total_a"], "p_tsv_w": z2["p_tsv_total_w"]},
            "current_ratio": z2["i_total_a"] / z1["i_total_a"],
            "loss_ratio": z2["p_tsv_total_w"] / z1["p_tsv_total_w"],
            "note": ("loss ratio ~= current ratio squared, as Joule scaling requires; "
                     "that it does is a check on the model, not a coincidence"),
        },
        "B_as_designed": {
            "rule": "each field sized to its own rail and drop budget",
            "z1_min_n": s1["min_drop"]["n_total"], "z2_min_n": s2["min_drop"]["n_total"],
            "z1_budget_v": s1["budget_v"], "z2_budget_v": s2["budget_v"],
            "caveat": ("confounds rail assignment with copper content; sensitivity "
                       "only, never the primary physics comparison"),
        },
    }
