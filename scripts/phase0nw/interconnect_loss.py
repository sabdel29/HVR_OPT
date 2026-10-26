"""PHASE 0N-AB --- RECOMPUTED physical interconnect resistance and loss.

The power-path graph said every segment existed. This computes R(T) and I^2 R for the
ones whose geometry is actually known, on the NEW physical package, and leaves the rest
OPEN rather than borrowing a Phase-0M-R3C number.

MATERIAL PROVENANCE. Resistivities come from the framework's own sourced card,
scripts/phase0m/interconnect.py:

    rho_Cu(20 C)     = 17.0 nOhm.m   SOURCE_BACKED to the June-2026 design source
    rho_solder(20 C) = 130.0 nOhm.m  SOURCE_BACKED to the same source
    alpha_Cu         = 3.93e-3 /K    ASSUMPTION (bulk Cu TCR)
    alpha_solder     = 4.0e-3 /K     ASSUMPTION

So the BGA solder RESISTIVITY is source-backed even though the ALLOY NAME is not: the
retrievable abstract of 10.1109/TCPMT.2026.3724907 does not state a solder alloy. The
model therefore uses `solder_bga` with a sourced resistivity and an OPEN alloy, rather
than asserting SAC305 and inheriting a name nothing in the source establishes. As a
cross-check, 130 nOhm.m is within a few percent of commonly reported SAC305 values, which
is consistent with -- but does not prove -- that choice.

WHAT IS STILL OPEN AND WHY:
  * microbump geometry (diameter, pitch, pillar/cap split, count) is not in the physical
    config, so microbump loss is bracketed by count rather than computed;
  * contact / UBM / IMC resistance has no transferable source, so it is a bracket whose
    lower bound is explicitly the IDEAL-CONTACT bound, never silently zero;
  * the package-level HV/LV distribution networks have no geometry yet, so their loss is
    OPEN -- a continuous conductor from the BGA ring to the 49 cells does not exist in
    the model, and inventing a plane to make a number appear would be worse than OPEN.
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

from interconnect import (ALPHA_CU, ALPHA_SOLDER, RHO_CU_20C,  # noqa: E402
                          RHO_SOLDER_20C, rho_cu, rho_solder)

T_REF_C = 20.0            # declared electrical reference temperature (brief 37)

# --- SOURCE_BACKED geometry, June-2026 Table III ---------------------------------------
D_BALL_MM, H_BALL_MM = 0.400, 0.300
D_TSV_MM, P_TSV_MM, H_TSV_MM = 0.030, 0.060, 0.300

BGA_ALLOY_STATUS = "OPEN -- the design source does not state the alloy"
BGA_RHO_STATUS = "SOURCE_BACKED -- June-2026 via scripts/phase0m/interconnect.py"


def _area_mm2(d_mm):
    return math.pi * (d_mm / 2) ** 2


# =======================================================================================
# BGA
# =======================================================================================
def bga_resistance(n_balls: int, T_c: float = T_REF_C) -> dict:
    """Parallel solder balls, R = rho(T) h / A per ball.

    Equal sharing is ASSUMED here and flagged: the package RDL network that would
    determine the true split does not exist yet (see module docstring). With a real
    network the outer balls would carry more, so this is a LOWER bound on BGA loss.
    """
    rho = rho_solder(T_c)
    a_m2 = _area_mm2(D_BALL_MM) * 1e-6
    r_one = rho * (H_BALL_MM * 1e-3) / a_m2
    return {"n_balls": n_balls, "T_c": T_c, "rho_ohm_m": rho,
            "r_one_ohm": r_one, "r_total_ohm": r_one / max(n_balls, 1),
            "sharing": "EQUAL (assumed)",
            "sharing_status": "BOUNDED -- lower bound; the RDL network that sets the "
                              "true split is not yet built"}


def bga_loss(i_a: float, n_supply: int, n_return: int, T_c: float = T_REF_C) -> dict:
    s = bga_resistance(n_supply, T_c)
    g = bga_resistance(n_return, T_c)
    i_ball = i_a / max(n_supply, 1)
    return {"i_a": i_a, "T_c": T_c,
            "r_supply_ohm": s["r_total_ohm"], "r_return_ohm": g["r_total_ohm"],
            "p_supply_w": i_a ** 2 * s["r_total_ohm"],
            "p_return_w": i_a ** 2 * g["r_total_ohm"],
            "p_total_w": i_a ** 2 * (s["r_total_ohm"] + g["r_total_ohm"]),
            "i_per_ball_a": i_ball,
            "j_nominal_A_cm2": i_ball / (_area_mm2(D_BALL_MM) * 1e-2),
            "j_local_A_cm2": None,
            "j_local_status": "OPEN -- needs this package's own pad/RDL solve; the 22x "
                              "in 10.1016/j.jmrt.2023.12.187 is that paper's geometry",
            "status": "RECOMPUTED (equal-sharing lower bound)"}


# =======================================================================================
# TSV  --  reuses the audited two-ended constriction model
# =======================================================================================
def tsv_loss(i_total_a: float, n_vdd: int, n_gnd: int, cells: int,
             T_c: float = T_REF_C) -> dict:
    import tsv_fields as TSV
    i_cell = i_total_a / cells
    r_v = (TSV.field_resistance(n_vdd, H_TSV_MM, D_TSV_MM, T_c)
           + TSV.spreading_resistance(n_vdd, D_TSV_MM, P_TSV_MM, T_c, ends=2))
    r_g = (TSV.field_resistance(n_gnd, H_TSV_MM, D_TSV_MM, T_c)
           + TSV.spreading_resistance(n_gnd, D_TSV_MM, P_TSV_MM, T_c, ends=2))
    return {"i_total_a": i_total_a, "i_cell_a": i_cell, "cells": cells, "T_c": T_c,
            "n_vdd": n_vdd, "n_gnd": n_gnd,
            "r_vdd_ohm": r_v, "r_gnd_ohm": r_g,
            "p_vdd_w": cells * i_cell ** 2 * r_v,
            "p_gnd_w": cells * i_cell ** 2 * r_g,
            "p_total_w": cells * i_cell ** 2 * (r_v + r_g),
            "transition_term": None,
            "transition_status": (
                "OPEN -- 10.1145/3698364.3705353 describes DC crowding where current "
                "TURNS between landing pad, via and TSV. The two-ended constriction "
                "already here is the plane-to-via-mouth convergence; a pad/via-ladder "
                "transition would be a DIFFERENT effect. Adding a second factor without "
                "establishing they are different would double-count."),
            "status": "RECOMPUTED"}


# =======================================================================================
# Microbump  --  geometry is OPEN, so this is a bracket, not a value
# =======================================================================================
# Bracket on microbump count per architecture. The physical config does not define a
# microbump field; the interface layer is 10 um of homogenized medium. These bounds are
# BOUNDED_ENGINEERING and exist to show the loss SCALE, not to claim a value.
N_UBUMP_BRACKET = (10_000, 100_000)
D_UBUMP_BRACKET_MM = (0.020, 0.050)      # 20-50 um, the scale in 10.1109/TCPMT.2026.3728725
H_UBUMP_MM = 0.010                        # the interface tier thickness


def microbump_loss(i_a: float, T_c: float = T_REF_C,
                   r_contact_ohm: float = 0.0) -> dict:
    """Series ladder with an explicit contact term.

    R_microbump = R_bulk + R_constriction + R_contact. r_contact_ohm = 0 is the
    IDEAL-CONTACT LOWER BOUND and is labelled as such -- never a claim that contact
    resistance is zero. 10.1109/EPTC.2015.7412351 shows microbump resistance RISING as
    solder converts to IMC, so the real value is above this bound by an unknown amount.
    """
    rho = rho_cu(T_c)
    out = {}
    for tag, (n, d) in (("MB_L", (N_UBUMP_BRACKET[1], D_UBUMP_BRACKET_MM[1])),
                        ("MB_H", (N_UBUMP_BRACKET[0], D_UBUMP_BRACKET_MM[0]))):
        a_m2 = _area_mm2(d) * 1e-6
        r_bulk = rho * (H_UBUMP_MM * 1e-3) / a_m2
        r_sp = 2 * rho / (4 * (d / 2 * 1e-3))          # two ends, same form as the TSVs
        r_one = r_bulk + r_sp + r_contact_ohm
        r_tot = r_one / n
        out[tag] = {"n": n, "d_mm": d, "r_bulk_one_ohm": r_bulk,
                    "r_spread_one_ohm": r_sp, "r_contact_one_ohm": r_contact_ohm,
                    "r_total_ohm": r_tot, "p_w": i_a ** 2 * r_tot}
    return {"i_a": i_a, "T_c": T_c, "cases": out,
            "p_low_w": out["MB_L"]["p_w"], "p_high_w": out["MB_H"]["p_w"],
            "geometry_status": "OPEN -- no microbump field in the physical config",
            "contact_status": ("r_contact = 0 is the IDEAL-CONTACT LOWER BOUND, not a "
                               "claim of zero; no transferable source was found"),
            "status": "BRACKETED (geometry OPEN)"}


# =======================================================================================
MAT_ = lambda g, c, l: {"geometry": g, "current": c, "loss": l}   # noqa: E731


def rms_scenarios(arch: str) -> dict:
    """RMS current per rail. The 48 V rail is a BRACKET, not a value."""
    import rms_currents as RMS
    import power_path as PP
    rc = PP.rail_currents(arch)
    hv = RMS.hv_input_scenarios(rc["hv_total_a"])
    c = RMS.cell_currents()
    # SECTION L: 49 electrically separate TSV fields -> no cross terms. Per-cell RMS.
    i_cell_rms = RMS.triangular_rms(c["i_cell_out_avg_a"], c["ripple_out_pp_a"])
    return {"hv_avg_a": rc["hv_total_a"],
            "hv_S0_a": hv["HV_S0"]["i_rms_a"], "hv_S1_a": hv["HV_S1"]["i_rms_a"],
            "hv_S2_a": hv["HV_S2"]["i_rms_a"],
            "hv_status": hv["status"], "hv_upper_bound": hv["upper_bound_status"],
            "lv_total_avg_a": rc["lv_total_a"],
            "i_cell_avg_a": c["i_cell_out_avg_a"], "i_cell_rms_a": i_cell_rms,
            "cell_rms_over_avg": i_cell_rms / c["i_cell_out_avg_a"]}


def ledger(arch: str, T_c: float = T_REF_C, n_tsv_side: int = 722) -> dict:
    import power_path as PP
    import tsv_fields as TSV
    rc = PP.rail_currents(arch)
    cfg_cells = rc["cells"]
    i_hv, i_lv = rc["hv_total_a"], rc["lv_total_a"]

    cap = TSV.bga_capacity(i_hv)
    bga = bga_loss(i_hv, cap["n_supply_required"], cap["n_return_required"], T_c)

    # which rail crosses the substrate is the architectural distinction
    i_tsv = i_hv if arch == "Z1" else i_lv
    tsv = tsv_loss(i_tsv, n_tsv_side, n_tsv_side, cfg_cells, T_c)
    mb = microbump_loss(i_lv, T_c)

    # --- RMS -------------------------------------------------------------------------
    # I^2 R needs RMS, not average. The 48 V rail has NO established waveform, so its
    # loss is reported across two SCENARIOS: HV-S0 continuous and HV-S1 constant square
    # pulse at the buck duty. S1 is the MINIMUM RMS for support D, not an upper bound,
    # and no finite upper bound exists from average current alone. The two scenarios
    # differ by 4x in RMS and 16x in I^2 R; that is a scenario separation, NOT an
    # uncertainty interval.
    rb = rms_scenarios(arch)
    # PRIMARY interface is the source Cu pad; the arbitrary microbump bracket moves to
    # legacy_sensitivity and no longer drives any ledger term.
    import pad_interface as PAD
    import rms_currents as _RMS
    pad = PAD.system(_RMS.cell_currents()["i_cell_out_rms_a"])
    MAT = MAT_
    f_S0 = (rb["hv_S0_a"] / rb["hv_avg_a"]) ** 2
    f_S1 = (rb["hv_S1_a"] / rb["hv_avg_a"]) ** 2
    f_S2 = (rb["hv_S2_a"] / rb["hv_avg_a"]) ** 2
    f_lv = rb["cell_rms_over_avg"] ** 2

    def hv_scen(p_base):
        return {"HV_S0": p_base * f_S0, "HV_S1": p_base * f_S1, "HV_S2": p_base * f_S2}

    def lv_val(p_base):
        return p_base * f_lv

    # --- PHASE 0N-AI: the package HV RDL is now a solved physical network -----
    # geometry CLOSED for both architectures (sheet, real BGA lattice sites,
    # finite source-backed contacts, separate return conductor). The LOSS axis
    # follows CONVERGENCE, not merely the existence of a number: Z2's two
    # networks pass the 1 % test on all five metrics and Z1's two do not, so
    # Z1's loss stays OPEN while its geometry is closed. That is exactly the
    # distinction the three-axis maturity model exists to express.
    import json as _jn
    _vf = _jn.loads((R / "research/phase0nai"
                     / "voltage_fed_network.json").read_text())
    _cv = _vf["convergence"]
    _rdl_ok = all(_cv[f"{arch}_{r}"]["converged"] for r in ("supply", "return"))
    _rdl = _vf["loop"][arch]
    _rdl_mat = MAT_("CLOSED", "SCENARIO", "SCENARIO" if _rdl_ok else "OPEN")
    _rdl_note = (
        "voltage-fed network, converged on all five metrics"
        if _rdl_ok else
        "voltage-fed network built and solved, but %s fail the 1 %% convergence "
        "test (worst %s), so the resistance is not yet a reportable value"
        % (", ".join(sorted(k for k in _cv if k.startswith(arch)
                            and not _cv[k]["converged"])),
           max((_cv[k]["worst_delta"] for k in _cv if k.startswith(arch)),
               default=0.0)))

    def _rdl_scen(r_ohm):
        return hv_scen(rb["hv_avg_a"] ** 2 * r_ohm) if _rdl_ok else None

    # THREE-AXIS MATURITY (brief 46): geometry, current and loss are tracked
    # separately, so a conductor whose resistance is closed is not called unresolved
    # merely because its waveform is open.
    terms = {
        "P_BGA_supply": {"w": None, "scenario_w": hv_scen(bga["p_supply_w"]),
                         "maturity": MAT("CLOSED", "OPEN", "SCENARIO")},
        "P_BGA_return": {"w": None, "scenario_w": hv_scen(bga["p_return_w"]),
                         "maturity": MAT("CLOSED", "OPEN", "SCENARIO")},
        "P_TSV_VDD": ({"w": None, "scenario_w": hv_scen(tsv["p_vdd_w"]),
                       "maturity": MAT("CLOSED", "OPEN", "SCENARIO")} if arch == "Z1"
                      else {"w": lv_val(tsv["p_vdd_w"]), "scenario_w": None,
                            "maturity": MAT("CLOSED", "CLOSED", "CLOSED")}),
        "P_TSV_GND": ({"w": None, "scenario_w": hv_scen(tsv["p_gnd_w"]),
                       "maturity": MAT("CLOSED", "OPEN", "SCENARIO")} if arch == "Z1"
                      else {"w": lv_val(tsv["p_gnd_w"]), "scenario_w": None,
                            "maturity": MAT("CLOSED", "CLOSED", "CLOSED")}),
        # One pad's area, resistance and the cell current are all closed. The FIELD
        # COUNT is not -- no physical criterion selects it -- so the field loss is a
        # count scenario spanning ~1227x, not a number.
        "P_pad_VDD": {"w": None,
                      "scenario_w": {k: v for k, v in
                                     pad["scenario_p_pad_rail_w"].items()},
                      "maturity": MAT("CLOSED", "CLOSED", "SCENARIO")},
        "P_pad_GND": {"w": None,
                      "scenario_w": {k: v for k, v in
                                     pad["scenario_p_pad_rail_w"].items()},
                      "maturity": MAT("CLOSED", "CLOSED", "SCENARIO")},
        "P_pkg_RDL_HV_supply": {"w": None,
                                "scenario_w": _rdl_scen(_rdl["r_supply_ohm"]),
                                "r_ohm": _rdl["r_supply_ohm"],
                                "converged": _rdl_ok, "note": _rdl_note,
                                "maturity": _rdl_mat},
        "P_pkg_RDL_HV_return": {"w": None,
                                "scenario_w": _rdl_scen(_rdl["r_return_ohm"]),
                                "r_ohm": _rdl["r_return_ohm"],
                                "converged": _rdl_ok, "note": _rdl_note,
                                "maturity": _rdl_mat},
        "P_pkg_RDL_LV_supply": {"w": None, "scenario_w": None,
                                "maturity": MAT("OPEN", "OPEN", "OPEN")},
        "P_pkg_RDL_LV_return": {"w": None, "scenario_w": None,
                                "maturity": MAT("OPEN", "OPEN", "OPEN")},
        "P_intraVR_metal": {"w": None, "scenario_w": None,
                            "maturity": MAT("OPEN", "OPEN", "OPEN")},
        "P_intraVR_vertical": {"w": None, "scenario_w": None,
                               "maturity": MAT("OPEN", "OPEN", "OPEN")},
    }
    done = sum(v["w"] for v in terms.values()
               if v["maturity"]["loss"] == "CLOSED" and v["w"] is not None)
    return {"arch": arch, "T_c": T_c, "i_hv_a": i_hv, "i_lv_a": i_lv,
            "tsv_rail_v": 48.0 if arch == "Z1" else 1.0,
            "bga": bga, "tsv": tsv, "pad": pad, "bga_capacity": cap,
            "legacy_sensitivity": {"microbump_arbitrary_bracket": mb},
            "terms": terms,
            "p_recomputed_total_w": done,
            "rms": rb,
            "n_loss_closed": sum(1 for v in terms.values()
                                 if v["maturity"]["loss"] == "CLOSED"),
            "n_loss_scenario": sum(1 for v in terms.values()
                                   if v["maturity"]["loss"] == "SCENARIO"),
            "n_loss_open": sum(1 for v in terms.values()
                               if v["maturity"]["loss"] == "OPEN"),
            "n_geometry_closed": sum(1 for v in terms.values()
                                     if v["maturity"]["geometry"] == "CLOSED")}


def main():
    out = {a: ledger(a) for a in ("Z1", "Z2")}
    d = R / "research" / "phase0nab"
    d.mkdir(parents=True, exist_ok=True)
    (d / "interconnect_loss.json").write_text(
        json.dumps(out, indent=1, sort_keys=True))
    for a, L in out.items():
        print(f"\n=== {a}  (T_ref {L['T_c']:.0f} C, substrate rail "
              f"{L['tsv_rail_v']:.0f} V) ===")
        print(f"  I_HV {L['i_hv_a']:.4f} A   I_LV {L['i_lv_a']:.0f} A")
        print(f"  loss CLOSED {L['n_loss_closed']}  SCENARIO {L['n_loss_scenario']}  "
              f"OPEN {L['n_loss_open']}  |  geometry CLOSED {L['n_geometry_closed']}/12")
        for k, v in L["terms"].items():
            m = v["maturity"]
            tag = f"{m['geometry']}/{m['current']}/{m['loss']}"
            if v["w"] is not None:
                print(f"    {k:22s} {v['w']*1e3:10.3f} mW   {tag}")
            elif v.get("scenario_w"):
                # PRE-EXISTING BUG: this printed sc['HV_S0'] unconditionally and
                # raised KeyError on the pad terms, whose scenarios are keyed
                # PAD_DROP / PAD_GEOM_MAX. main() could not run to completion.
                # Render whatever scenario keys the term actually carries.
                sc = v["scenario_w"]
                body = "  ".join(f"{n.replace('HV_', '')} {w*1e3:.2f}"
                                 for n, w in sc.items())
                print(f"    {k:22s} {body} mW   {tag}")
            else:
                print(f"    {k:22s} {'--':>10s}      {tag}")
        pd = L["pad"]
        print(f"  pad field: count OPEN, loss {pd['loss_maturity']} spanning "
              f"{pd['sensitivity']['loss_span_factor']:.0f}x "
              f"({pd['sensitivity']['n_drop']} to "
              f"{pd['sensitivity']['n_geom_max']} pads/rail/cell)")


if __name__ == "__main__":
    main()
