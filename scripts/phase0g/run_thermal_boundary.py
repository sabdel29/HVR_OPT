#!/usr/bin/env python3
"""Phase-0G Sec.8/10 -- does the THICKNESS ORDERING survive thermal-boundary uncertainty?

Phase 0F calibrated an equivalent Robin boundary on the TIM top surface (h = 166 kW/m2K,
T_max = 84.07 C, converged) while June-2026 places micro-channels INSIDE the substrate
adjacent to the GaN switch layer. Phase 0F also showed the substrate-side topology SATURATES:
at the h ceiling it reaches only 90.96 C, 6.96 K above the reference junction temperature.
The two topologies bracket a real model-form uncertainty, and the thickness ordering -- the
only mechanical ordering still standing after Sec.6/7 -- must be tested across it.

MODEL-FORM LIMIT, stated rather than hidden: the substrate-side film is applied to the
substrate UNDERSIDE, which is an external face only when no board is attached. With an
explicit BGA + board the same surface is internal, so CalculiX cannot carry a film there and
the substrate topology is run on BC_A / BC_B only. For the mounted assembly the thermal
boundary is instead perturbed over a wide h_top band, which changes both the temperature
level and the through-thickness gradient -- the two channels by which the thermal boundary
can reach the mechanics at all.
"""
from __future__ import annotations
import csv, json, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0g"))
sys.path.insert(0, str(R / "scripts" / "phase0f"))
from run_explicit_board import run_case
from etm.config import load_doe, load_stack

OUT = R / "results" / "phase0g"
H_NATURAL = 10.0          # W/m2K, still air on the surface that is no longer the cooled one


def sweep(stack, doe, rows, wd, tag, h_top, models, h_bottom=None):
    st = json.loads(json.dumps(stack))
    if h_bottom is not None:
        st["thermal_bc"]["h_bottom"]["value"] = h_bottom
    for h in (0.80, 2.00):
        for mode, case in models:
            t0 = time.time()
            try:
                r = run_case(h, mode, case, st, doe, h_top, wd)
            except Exception as e:
                print(f"    h={h} {mode:9s} FAILED: {str(e)[:60]}", flush=True); continue
            r["topology"] = tag
            rows.append(r)
            print(f"    h={h:.2f} {mode:9s} {case:12s} Tmax={r['T_max_C']:8.3f} C  "
                  f"w={r['die_warpage_pv_um']:9.4f} um ({time.time()-t0:.0f}s)", flush=True)


def main():
    stack, doe = load_stack(), load_doe()
    wd, rows = OUT / "runs_thermal", []
    cal_top = json.loads((R / "results/phase0f/cooling_1kw_calibration.json").read_text())
    cal_sub = json.loads((R / "results/phase0f/cooling_1kw_calibration_substrate.json").read_text())
    h_top, h_sub_side = cal_top["h_top_W_m2K"], cal_sub["h_top_W_m2K"]
    free = [("BC_A", "-"), ("BC_B", "-")]
    mounted = [("BC_BOARD", "fr4_1p6mm"), ("BC_BOARD", "compliant")]

    print("Sec.8/10  THICKNESS ORDERING vs THERMAL BOUNDARY  (h_sub 0.80 -> 2.00 mm)")
    print(f"\n  A. top-surface cooling, calibrated  h_top = {h_top:,.0f} W/m2K "
          f"(T_max {cal_top['achieved_T_max_C']:.2f} C, converged {cal_top['converged']})",
          flush=True)
    sweep(stack, doe, rows, wd, "top_calibrated", h_top, free + mounted)

    print(f"\n  B. substrate-side cooling, saturated  h_bottom = {h_sub_side:,.0f} W/m2K, "
          f"top natural (T_max {cal_sub['achieved_T_max_C']:.2f} C, "
          f"converged {cal_sub['converged']}) -- unmounted only", flush=True)
    sweep(stack, doe, rows, wd, "substrate_saturated", H_NATURAL, free, h_bottom=h_sub_side)

    for f in (0.5, 2.0):
        print(f"\n  C. mounted assembly, thermal-boundary perturbation h_top x {f}", flush=True)
        sweep(stack, doe, rows, wd, f"top_x{f:g}", h_top * f, mounted)

    with open(OUT / "cooling_topology_comparison.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for r in rows for k in r}))
        w.writeheader(); w.writerows(rows)

    print("\n=== S_h = [W(2.00) - W(0.80)] / W(0.80) by thermal boundary ===")
    signs = {}
    for topo in dict.fromkeys(r["topology"] for r in rows):
        for mode, case in free + mounted:
            sel = [r for r in rows if r["topology"] == topo and r["restraint"] == mode
                   and r.get("board_case", "-") == case]
            a = next((r for r in sel if r["h_sub_mm"] == 0.80), None)
            b = next((r for r in sel if r["h_sub_mm"] == 2.00), None)
            if not (a and b):
                continue
            S = (b["die_warpage_pv_um"] - a["die_warpage_pv_um"]) / a["die_warpage_pv_um"]
            signs.setdefault((mode, case), []).append((topo, S))
            print(f"  {topo:22s} {mode:9s} {case:12s} "
                  f"dT {a['T_max_C']:7.2f}/{b['T_max_C']:7.2f} C  "
                  f"W {a['die_warpage_pv_um']:8.4f} -> {b['die_warpage_pv_um']:8.4f}   "
                  f"S_h = {S:+7.4f}  {'thicker BETTER' if S < 0 else 'thicker WORSE'}")

    print("\n=== does any thermal boundary flip a SIGN? ===")
    for (mode, case), ss in signs.items():
        vals = [s for _, s in ss]
        stable = all(v < 0 for v in vals) or all(v > 0 for v in vals)
        print(f"  {mode:9s} {case:12s} " + "  ".join(f"{t}={s:+.4f}" for t, s in ss)
              + f"   -> {'SIGN STABLE' if stable else 'SIGN FLIPS'}")
    print(f"\nwrote {OUT/'cooling_topology_comparison.csv'}")


if __name__ == "__main__":
    main()
