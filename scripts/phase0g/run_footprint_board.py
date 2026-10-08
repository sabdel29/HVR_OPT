#!/usr/bin/env python3
"""Phase-0G Sec.14b -- is the FOOTPRINT OPPOSITION sign itself assembly-state dependent?

Sec.14 found the footprint sign flipping between the free package (larger footprint worse)
and one explicit board (larger footprint better). Footprint opposition is the strongest
DVPD-specific claim in this project, so the flip must be resolved across the whole calibrated
board envelope before either sign is reported.
"""
from __future__ import annotations
import csv, json, math, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0g"))
sys.path.insert(0, str(R / "scripts" / "phase0f"))
import board as BRD
import kw1
from run_explicit_board import run_case
from etm.config import load_doe, load_stack

OUT = R / "results" / "phase0g"


def main():
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((R / "results/phase0f/cooling_1kw_calibration.json").read_text())["h_top_W_m2K"]
    wd, rows = OUT / "runs_fpboard", []
    models = [("BC_A", "-"), ("BC_B", "-")] + [("BC_BOARD", c) for c in BRD.BOARD_CASES]

    print("Sec.14b  FOOTPRINT 259.2 -> 329.3 mm2 (M = 36 -> 49 at j = 3.0), h_sub = 1.50 mm")
    for M in (36, 49):
        kw1.M_VR, kw1.J_TARGET = M, 3.0
        for mode, case in models:
            t0 = time.time()
            try:
                r = run_case(1.50, mode, case, stack, doe, h_top, wd)
            except Exception as e:
                print(f"  M={M} {mode} {case} FAILED: {str(e)[:60]}", flush=True); continue
            r.update({"m_vr": M, "j": 3.0, "hvr_area_mm2": 259.20 if M == 36 else 329.28})
            rows.append(r)
            print(f"  M={M:3d} {mode:9s} {case:20s} w={r['die_warpage_pv_um']:9.4f} um "
                  f"({time.time()-t0:.0f}s)", flush=True)
    kw1.M_VR, kw1.J_TARGET = 49, 3.5

    with open(OUT / "footprint_board_envelope.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for r in rows for k in r}))
        w.writeheader(); w.writerows(rows)

    print("\n=== S_A = [W(329.3 mm2) - W(259.2 mm2)] / W(259.2 mm2) ===")
    flips = []
    for mode, case in models:
        a = next((r for r in rows if r["restraint"] == mode and r.get("board_case", "-") == case
                  and r["m_vr"] == 36), None)
        b = next((r for r in rows if r["restraint"] == mode and r.get("board_case", "-") == case
                  and r["m_vr"] == 49), None)
        if not (a and b):
            continue
        S = (b["die_warpage_pv_um"] - a["die_warpage_pv_um"]) / a["die_warpage_pv_um"]
        flips.append(S)
        print(f"  {mode:9s} {case:20s} W {a['die_warpage_pv_um']:8.4f} -> "
              f"{b['die_warpage_pv_um']:8.4f}   S_A = {S:+7.4f}   "
              f"{'larger footprint WORSE  (opposition HOLDS)' if S > 0 else 'larger footprint BETTER (opposition ABSENT)'}")
    if flips and min(flips) < 0 < max(flips):
        print("\n  VERDICT: the footprint sign is NOT invariant -- it flips inside the calibrated")
        print("  board envelope. Footprint opposition is ASSEMBLY-STATE DEPENDENT.")
    elif flips and max(flips) < 0:
        print("\n  VERDICT: larger footprint is BETTER in every mounted model -- no opposition.")
    elif flips:
        print("\n  VERDICT: footprint opposition holds across the whole envelope.")
    print(f"\nwrote {OUT/'footprint_board_envelope.csv'}")


if __name__ == "__main__":
    main()
