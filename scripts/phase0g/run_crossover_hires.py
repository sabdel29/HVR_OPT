#!/usr/bin/env python3
"""Phase-0G Sec.2/4: is the ARCH_B interior electrical optimum real?

Phase 0F reported an interior minimum near h_sub = 1.0 mm from five points whose decisive
step is +14.5 mW on a 125 W system. Decomposing that curve shows why it must be audited:

    P_total,B(h) = g(h) + P_TSV,B(h)

g(h) -- converter plus everything except the LV via field -- falls only because the package
gets cooler, and the temperature steps involved are 0.038-0.093 K. The Phase-0F ET loop
converged T_max to 0.05 K. With dP_conv/dT = 148 mW/K, that tolerance alone admits ~7.4 mW of
error, which is half the effect being claimed.

This script therefore re-runs the sweep at high thickness resolution and at a convergence
tolerance 25x tighter, so the fixed point is resolved far below the quantity in dispute.
"""
from __future__ import annotations
import argparse, csv, json, math, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0f"))
import kw1
from etm.config import load_doe, load_stack

OUT = R / "results" / "phase0g"
OUT.mkdir(parents=True, exist_ok=True)
P0F = R / "results" / "phase0f"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tol", type=float, default=0.002)
    ap.add_argument("--maxit", type=int, default=30)
    ap.add_argument("--arch", default="ARCH_B")
    ap.add_argument("--tag", default="tight")
    ap.add_argument("--grid", type=int, default=161)
    a = ap.parse_args()

    stack, doe = load_stack(), load_doe()
    h_top = json.loads((P0F / "cooling_1kw_calibration.json").read_text())["h_top_W_m2K"]
    wd = OUT / f"runs_{a.tag}"
    hs = [0.80, 0.90, 1.00, 1.10, 1.20, 1.30, 1.40, 1.50, 2.00]
    rows = []
    print(f"arch={a.arch}  tol={a.tol} K  max_it={a.maxit}  rdl_grid={a.grid}")
    print(f"{'h':>5s} {'P_total':>11s} {'P_conv':>10s} {'P_tsv(mW)':>10s} {'P_rdl':>8s} "
          f"{'T_max':>8s} {'T_hvr':>8s} {'its':>4s} {'dT_last':>9s} {'s':>5s}")
    for h in hs:
        t0 = time.time()
        r = kw1.coupled_1kw(a.arch, "uniform", h, h_top, stack, doe, wd,
                            bc="BC_A", tol=a.tol, max_it=a.maxit)
        if not r["feasible"]:
            print(f"{h:5.2f}  {r['reason']}"); continue
        hist = r["history"]
        dT_last = (abs(hist[-1]["T_max_C"] - hist[-2]["T_max_C"]) if len(hist) > 1
                   else float("nan"))
        rows.append({"arch": a.arch, "h_sub_mm": h, "tol_K": a.tol, "rdl_grid": a.grid,
                     "P_elec_total_w": r["P_elec_total_w"], "P_conv_w": r["P_conv_w"],
                     "P_tsv_w": r["P_tsv_w"], "P_rdl_w": r["P_rdl_w"],
                     "P_bga_w": r["P_bga_w"], "P_c4_w": r["P_c4_w"],
                     "P_microbump_w": r["P_microbump_w"], "P_pdn_w": r["P_pdn_w"],
                     "T_max_C": r["T_max_C"], "T_vr_min_C": r["T_vr_min_C"],
                     "T_vr_max_C": r["T_vr_max_C"],
                     "die_warpage_pv_um": r["die_warpage_pv_um"],
                     "energy_residual_pct": r["energy_residual_pct"],
                     "et_iters": r["et_iters"], "dT_last_K": dT_last,
                     "wall_s": time.time() - t0})
        print(f"{h:5.2f} {r['P_elec_total_w']:11.5f} {r['P_conv_w']:10.4f} "
              f"{r['P_tsv_w']*1e3:10.3f} {r['P_rdl_w']:8.4f} {r['T_max_C']:8.4f} "
              f"{r['T_vr_max_C']:8.4f} {r['et_iters']:4d} {dT_last:9.2e} "
              f"{time.time()-t0:5.0f}", flush=True)
    f = OUT / f"crossover_hires_{a.arch}_{a.tag}.csv"
    with open(f, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    p = [(r["h_sub_mm"], r["P_elec_total_w"]) for r in rows]
    imin = min(range(len(p)), key=lambda i: p[i][1])
    print(f"\nminimum at h = {p[imin][0]:.2f} mm, P = {p[imin][1]:.5f} W")
    print(f"interior = {0 < imin < len(p)-1}")
    print(f"wrote {f}")


if __name__ == "__main__":
    main()
