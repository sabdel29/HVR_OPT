#!/usr/bin/env python3
"""Phase-0M-R3B Sections 4 and 6 --- `ls_to_L` as a physical via chain.

Replaces the single abstract 673 um cylinder with what the stack actually is: a chain of
one microvia per build-up layer across the 120 um gap between the low-side GaN die and the
inductor, evaluated against the sourced pitch bound rather than the borrowed TSV range.

Every quantity is recomputed here from first principles; no production routine is called,
so agreement with the production numbers is a cross-check and not a tautology.
"""
from __future__ import annotations
import csv, math, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3b"
sys.path.insert(0, str(R / "scripts" / "phase0mr3b"))
from ls_to_l_topology import layer_stack                                 # noqa: E402

I_RMS = 1000.0 / 49.0            # A, one cell
J_DESIGN = 1.0e8                 # A/m2, framework design current density
T_LINER_UM = 0.5
S_MIN_UM = 30.0                  # SOURCE_BACKED minimum spacing
PACKING = 0.5
# The landing area is NOT the die footprint. The chain crosses the flying-capacitor power
# layer, and in that layer the cell is already occupied by (N-1) embedded MLCCs; only what
# is left is available for via columns. That free area, not the die footprint, is the
# binding constraint, and it is smaller (DEFECT #63).
A_LAND_MM2 = 1.61                # free area in the flying-capacitor layer: 5.61 - 2 x 2.00
A_LAND_MODEL_MM2 = 1.80          # what edge_loss() assumed: the gan_ls footprint
RHO_CU_85C = 1.72e-8 * (1 + 0.00393 * (85.0 - 20.0))

# pitch cases: the design point, and the two the sources actually demonstrate
PITCH_CASES = [
    (70.0,  "0M-R3 design point", "UNSOURCED -- below the finest pitch any reachable "
                                  "source demonstrates for this class"),
    (100.0, "Ostmann 2008 prototype", "SOURCE_BOUNDED -- 100 um I/O pad pitch demonstrated "
                                      "at prototype level"),
    (150.0, "Ostmann 2008 production", "SOURCE_BOUNDED -- min. 150 um I/O pad pitch in "
                                       "production"),
]
# the 3-layer gap needs 3 microvia levels. The sourced qualified configuration is
# 2 stacked + 1 staggered; a staggered level lands beside the level below, so its column
# occupies at least two lateral pitch cells instead of one.
STACK_CASES = [("fully_stacked", 1.0, "3 stacked levels -- OVER the sourced limit"),
               ("semi_stacked", 2.0, "2 stacked + 1 staggered -- the sourced configuration")]


def n_required(i_a: float, d_um: float) -> int:
    a_cu = math.pi * ((d_um / 2.0 - T_LINER_UM) * 1e-6) ** 2
    return max(1, math.ceil(i_a / (J_DESIGN * a_cu)))


def n_available(pitch_um: float, area_penalty: float) -> int:
    p = pitch_um * 1e-6
    return max(1, int(A_LAND_MM2 * 1e-6 * PACKING / (p ** 2 * area_penalty)))


def d_max_for_pitch(pitch_um: float) -> float:
    """Largest via that still respects the additive spacing rule at this pitch."""
    return pitch_um - S_MIN_UM


def chain_resistance(d_um: float, n: int) -> tuple[float, list[dict]]:
    a_cu = math.pi * ((d_um / 2.0 - T_LINER_UM) * 1e-6) ** 2
    segs, rtot = [], 0.0
    for s in layer_stack():
        r = RHO_CU_85C * (s["thickness_um"] * 1e-6) / (a_cu * n)
        rtot += r
        segs.append({"segment": s["layer"], "kind": s["kind"],
                     "thickness_um": s["thickness_um"], "d_um": d_um,
                     "aspect_ratio": round(s["thickness_um"] / d_um, 4),
                     "n_parallel": n, "R_ohm": r})
    return rtot, segs


def main() -> int:
    rows, res_rows = [], []
    for pitch, label, prov in PITCH_CASES:
        for stack, pen, snote in STACK_CASES:
            for d in (40.0, d_max_for_pitch(pitch)):
                nr = n_required(I_RMS, d)
                na = n_available(pitch, pen)
                ratio = nr / na
                rtot, segs = chain_resistance(d, min(nr, na) if na else nr)
                a_need = nr * (pitch * 1e-6) ** 2 * pen / PACKING
                rows.append({
                    "pitch_um": pitch, "pitch_case": label, "pitch_provenance": prov[:40],
                    "landing_area_mm2": A_LAND_MM2,
                    "area_needed_mm2": round(a_need * 1e6, 4),
                    "pct_of_binding_layer_free_area": round(100 * a_need * 1e6 / A_LAND_MM2, 1),
                    "stack": stack, "stack_note": snote, "area_penalty": pen,
                    "d_um": round(d, 1), "d_legal_at_pitch": d <= d_max_for_pitch(pitch),
                    "n_required": nr, "n_available": na,
                    "routing_ratio": round(ratio, 4), "feasible": nr <= na,
                    "R_chain_ohm": rtot, "P_chain_w": I_RMS ** 2 * rtot,
                    "AR_worst": max(s["aspect_ratio"] for s in segs),
                })
                if pitch == 100.0 and stack == "semi_stacked" and abs(d - d_max_for_pitch(pitch)) < 1e-9:
                    res_rows = segs
    with (OUT / "ls_to_L_feasibility.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    with (OUT / "ls_to_L_resistance_breakdown.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(res_rows[0])); w.writeheader(); w.writerows(res_rows)

    print(f"{'pitch':>6} {'stack':14s} {'d_um':>6} {'legal':>6} {'n_req':>6} {'n_av':>6} "
          f"{'ratio':>7} {'feas':>5} {'AR_max':>7}")
    for r in rows:
        print(f"{r['pitch_um']:6.0f} {r['stack']:14s} {r['d_um']:6.1f} "
              f"{str(r['d_legal_at_pitch']):>6} {r['n_required']:6d} {r['n_available']:6d} "
              f"{r['routing_ratio']:7.3f} {str(r['feasible']):>5} {r['AR_worst']:7.3f}")
    ok = [r for r in rows if r["feasible"] and r["d_legal_at_pitch"]
          and r["pitch_um"] >= 100.0 and r["stack"] == "semi_stacked"]
    print(f"\nconfigurations that are BOTH feasible AND inside the sourced pitch and "
          f"stacking bounds: {len(ok)}")
    for r in ok:
        print(f"   pitch {r['pitch_um']:.0f} um, d {r['d_um']:.0f} um, "
              f"n_req {r['n_required']} <= n_av {r['n_available']}, "
              f"R {r['R_chain_ohm']*1e6:.3f} uOhm, P {r['P_chain_w']*1000:.3f} mW")
    return 0


if __name__ == "__main__":
    sys.exit(main())
