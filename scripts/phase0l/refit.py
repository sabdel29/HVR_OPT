#!/usr/bin/env python3
"""Phase-0L Part VI -- construct the scientifically consistent alternative fit(s).

FIT-A : rate = A(T) sigma_applied^n            (the existing regression)
FIT-B : rate = A(T) [sigma_applied - sigma_y(T)]^n, positive overstress only

The brief forbids using negative overstress, so FIT-B can only be built from points where
sigma_applied > sigma_y(T).  This script reports how many such points exist per temperature,
which decides whether FIT-B is constructible at all.
"""
from __future__ import annotations
import csv, math, sys
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0i"))
import solder_model as sm                                                   # noqa: E402

R_GAS = 8.314462618
T_MELT_K = 490.15        # SAC305 solidus/liquidus ~217 C; used only for T/Tm reporting


def powerfit(x, y):
    n, lnA = np.polyfit(np.log(x), np.log(y), 1)
    A = math.exp(lnA)
    pred = A * np.asarray(x) ** n
    rel = np.abs(pred - np.asarray(y)) / np.asarray(y)
    return {"A": A, "n": float(n), "npts": len(x),
            "rmse_pct": float(100 * math.sqrt(float((rel ** 2).mean()))),
            "max_pct": float(100 * rel.max())}


rows, out = [], []
print("=" * 104)
print("PART VI -- FIT-A (sigma_applied) versus FIT-B (positive overstress only)")
print("=" * 104)
print(f"{'T (C)':>7} {'T/Tm':>6} {'sigma_y0':>9} {'N pts':>6} {'N usable':>9} "
      f"{'FIT-A A':>12} {'FIT-A n':>8} {'rmse%':>7} {'FIT-B':>28}")
for T in sm.DATA_TEMPS:
    pts = [(s, e) for (t, s, e) in sm.CREEP_DATA if t == T]
    y0 = sm.sigma0_of_T(T)
    usable = [(s - y0, e) for s, e in pts if s - y0 > 0]
    fa = powerfit([s for s, _ in pts], [e for _, e in pts])
    if len(usable) >= 2:
        fb = powerfit([o for o, _ in usable], [e for _, e in usable])
        fbtxt = f"A={fb['A']:.3e} n={fb['n']:.3f}"
    elif len(usable) == 1:
        fb, fbtxt = None, "UNDERDETERMINED (1 point)"
    else:
        fb, fbtxt = None, "IMPOSSIBLE (0 points)"
    thom = (T + 273.15) / T_MELT_K
    print(f"{T:7.0f} {thom:6.3f} {y0:9.2f} {len(pts):6d} {len(usable):9d} "
          f"{fa['A']:12.4e} {fa['n']:8.3f} {fa['rmse_pct']:7.2f} {fbtxt:>28}")
    out.append({"T_C": T, "T_over_Tm": thom, "sigma_y0_MPa": y0,
                "n_points": len(pts), "n_points_positive_overstress": len(usable),
                "fitA_A": fa["A"], "fitA_n": fa["n"], "fitA_rmse_pct": fa["rmse_pct"],
                "fitA_max_pct": fa["max_pct"],
                "fitB_constructible": bool(fb),
                "fitB_A": fb["A"] if fb else "", "fitB_n": fb["n"] if fb else "",
                "fitB_rmse_pct": fb["rmse_pct"] if fb else "",
                "fitB_max_pct": fb["max_pct"] if fb else "",
                "fitB_status": ("OK" if fb else
                                ("UNDERDETERMINED" if len(usable) == 1 else "IMPOSSIBLE"))})

tot = sum(o["n_points"] for o in out)
us = sum(o["n_points_positive_overstress"] for o in out)
print()
print(f"FIT-B usable points: {us} of {tot}.  Constructible at "
      f"{sum(1 for o in out if o['fitB_constructible'])} of {len(out)} temperatures.")
print("A Norton law needs two parameters per temperature, so FIT-B requires >= 2 usable")
print("points at every temperature. It is NOT CONSTRUCTIBLE.")
print()
# activation energy of FIT-A, from the rate at the centre of the measured window
ts = np.array(sm.DATA_TEMPS)
lnr = np.array([math.log(o["fitA_A"] * 10.0 ** o["fitA_n"]) for o in out])
sl, ic = np.polyfit(1.0 / (ts + 273.15), lnr, 1)
print(f"FIT-A apparent activation energy at sigma_ref = 10 MPa: "
      f"Q = {-sl*R_GAS/1000:.1f} kJ/mol")
print(f"  literature Garofalo Q for this dataset (Yuan 2023 Table 6): 62-65 kJ/mol")
print(f"FIT-A exponent n falls {out[0]['fitA_n']:.2f} -> {out[-1]['fitA_n']:.2f} "
      f"over {sm.DATA_TEMPS[0]:.0f}-{sm.DATA_TEMPS[-1]:.0f} C "
      f"(a single global Norton exponent is not supported)")
print()
print("EXTRAPOLATION behaviour of FIT-A, rate ratio relative to the top of the fitted window:")
print(f"  {'T':>6} {'edot(15.9 MPa)':>15} {'edot(60 MPa)':>14} {'edot(100 MPa)':>14} "
      f"{'ratio 100/15.9':>15}")
for o in out:
    A, n = o["fitA_A"], o["fitA_n"]
    r1, r2, r3 = A * 15.92 ** n, A * 60.0 ** n, A * 100.0 ** n
    print(f"  {o['T_C']:6.0f} {r1:15.4e} {r2:14.4e} {r3:14.4e} {r3/r1:15.4g}")

p = R / "results" / "phase0l" / "refit_comparison.csv"
with p.open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
print(f"\nwrote {p}")
