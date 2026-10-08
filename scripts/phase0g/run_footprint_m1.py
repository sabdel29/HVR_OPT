#!/usr/bin/env python3
"""Phase-0G Sec.14 (footprint under the calibrated assembly) and Sec.11 (M1 reference state).

Sec.14 -- footprint is the strongest DVPD-specific novelty, so its sign must be re-tested
under the explicit BGA + board assembly rather than the compact foundation that Phase 0G has
just shown to be non-physical.

Sec.11 -- every warpage number in this project is INCREMENTAL OPERATIONAL: the stress-free
reference is the 25 C operating ambient, so it excludes assembly/cure/cooldown residual
deformation. Raising the reference temperature to a cure temperature is a targeted M1
sensitivity. Its only purpose is to ask whether assembly pre-stress can change the THICKNESS
ORDERING; it is not a lifetime model.
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
P0F = R / "results" / "phase0f"


def main():
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((P0F / "cooling_1kw_calibration.json").read_text())["h_top_W_m2K"]
    wd = OUT / "runs_fpm1"
    rows = []

    # ---------------- Sec.14: footprint, free vs explicitly mounted -------------------
    print("Sec.14  FOOTPRINT under the explicit assembly (M = 36 vs 49 at j = 3.0)")
    for M, j in ((36, 3.0), (49, 3.0)):
        kw1.M_VR, kw1.J_TARGET = M, j
        for mode, case in (("BC_A", "-"), ("BC_B", "-"), ("BC_BOARD", "fr4_1p6mm")):
            t0 = time.time()
            try:
                r = run_case(1.50, mode, case, stack, doe, h_top, wd)
            except Exception as e:
                print(f"  M={M} {mode:9s} FAILED: {str(e)[:70]}", flush=True); continue
            r.update({"study": "footprint", "m_vr": M, "j": j, "t_ref_C": 25.0})
            rows.append(r)
            print(f"  M={M:3d} {mode:9s} {case:12s} w={r['die_warpage_pv_um']:9.4f} um "
                  f"({time.time()-t0:.0f}s)", flush=True)
    kw1.M_VR, kw1.J_TARGET = 49, 3.5

    # ---------------- Sec.11: M1 reference-state sensitivity ---------------------------
    print("\nSec.11  M1 REFERENCE-STATE sensitivity on the decisive thickness pair")
    for t_ref in (25.0, 150.0, 175.0):
        st = json.loads(json.dumps(stack))
        st["structural_bc"]["t_ref"]["value"] = t_ref
        for h in (0.80, 2.00):
            for mode, case in (("BC_A", "-"), ("BC_BOARD", "fr4_1p6mm")):
                t0 = time.time()
                try:
                    r = run_case(h, mode, case, st, doe, h_top, wd)
                except Exception as e:
                    print(f"  t_ref={t_ref} h={h} {mode} FAILED: {str(e)[:60]}", flush=True)
                    continue
                r.update({"study": "m1", "m_vr": 49, "j": 3.5, "t_ref_C": t_ref})
                rows.append(r)
                print(f"  t_ref={t_ref:6.1f} C  h={h:.2f} {mode:9s} "
                      f"w={r['die_warpage_pv_um']:10.4f} um ({time.time()-t0:.0f}s)", flush=True)

    with open(OUT / "footprint_m1_1kw.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for r in rows for k in r}))
        w.writeheader(); w.writerows(rows)

    print("\n=== Sec.14 footprint sign by assembly model ===")
    for mode, case in (("BC_A", "-"), ("BC_B", "-"), ("BC_BOARD", "fr4_1p6mm")):
        a = next((r for r in rows if r.get("study") == "footprint" and r["restraint"] == mode
                  and r["m_vr"] == 36), None)
        b = next((r for r in rows if r.get("study") == "footprint" and r["restraint"] == mode
                  and r["m_vr"] == 49), None)
        if not (a and b):
            continue
        S = 100 * (b["die_warpage_pv_um"] - a["die_warpage_pv_um"]) / a["die_warpage_pv_um"]
        print(f"  {mode:9s} {case:12s} W {a['die_warpage_pv_um']:8.4f} -> "
              f"{b['die_warpage_pv_um']:8.4f}  ({S:+.2f} %)  "
              f"{'larger footprint WORSE' if S > 0 else 'larger footprint BETTER'}")

    print("\n=== Sec.11 does assembly pre-stress change the thickness ordering? ===")
    for mode in ("BC_A", "BC_BOARD"):
        for t_ref in (25.0, 150.0, 175.0):
            a = next((r for r in rows if r.get("study") == "m1" and r["restraint"] == mode
                      and r["t_ref_C"] == t_ref and r["h_sub_mm"] == 0.80), None)
            b = next((r for r in rows if r.get("study") == "m1" and r["restraint"] == mode
                      and r["t_ref_C"] == t_ref and r["h_sub_mm"] == 2.00), None)
            if not (a and b):
                continue
            S = (b["die_warpage_pv_um"] - a["die_warpage_pv_um"]) / a["die_warpage_pv_um"]
            print(f"  {mode:9s} t_ref={t_ref:6.1f} C   W {a['die_warpage_pv_um']:9.4f} -> "
                  f"{b['die_warpage_pv_um']:9.4f}   S_h = {S:+8.4f}  "
                  f"{'thicker BETTER' if S < 0 else 'thicker WORSE'}")
    print(f"\nwrote {OUT/'footprint_m1_1kw.csv'}")


if __name__ == "__main__":
    main()
