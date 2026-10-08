#!/usr/bin/env python3
"""Phase-0L Part X -- can each candidate reproduce its source data, and what does it do
at the stresses the package actually reaches?"""
from __future__ import annotations
import csv, math, sys
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0l"))
sys.path.insert(0, str(R / "scripts" / "phase0i"))
import solder_model as sm                                                   # noqa: E402
import candidate_laws as cl                                                 # noqa: E402

PKG_SIGMA = (20., 40., 60., 80., 100., 120.)
out = []

print("=" * 104)
print("TEST 1 -- reproduction of the 19 Xiao & Armstrong points (Yuan 2023 Table 5)")
print("=" * 104)
print(f"{'model':>16} {'N reproduced':>13} {'median meas/pred':>17} "
      f"{'max |log10|':>12} {'worst factor':>13}")
summ = {}
for name, f in cl.MODELS.items():
    rr = []
    for (T, s, e) in sm.CREEP_DATA:
        p = float(np.atleast_1d(f(s, T))[0])
        rr.append(e / p if (p == p and p > 0) else float("inf"))
        out.append({"test": "source_19pt", "model": name, "T_C": T, "sigma_MPa": s,
                    "measured": e, "predicted": p,
                    "ratio_meas_over_pred": rr[-1]})
    fin = [r for r in rr if 0 < r < float("inf")]
    nrep = sum(1 for r in rr if 0.2 < r < 5.0)
    if fin:
        lg = [abs(math.log10(r)) for r in fin]
        med = sorted(fin)[len(fin) // 2]
        print(f"{name:>16} {nrep:>8} / {len(rr):<4} {med:17.4g} {max(lg):12.4f} "
              f"{10**max(lg):13.4g}")
        summ[name] = (nrep, med, max(lg))
    else:
        print(f"{name:>16} {nrep:>8} / {len(rr):<4} {'all zero/nan':>17}")
        summ[name] = (nrep, float("nan"), float("nan"))

print()
print("=" * 104)
print("TEST 2 -- behaviour at package-relevant stresses (uniaxial steady-state rate, 1/s)")
print("=" * 104)
for T in (45., 80., 115., 150.):
    print(f"  T = {T:.0f} C")
    print(f"    {'sigma':>7} " + " ".join(f"{k:>15}" for k in cl.MODELS))
    for s in PKG_SIGMA:
        vals = []
        for name, f in cl.MODELS.items():
            v = float(np.atleast_1d(f(s, T))[0])
            vals.append(v)
            out.append({"test": "package_stress", "model": name, "T_C": T, "sigma_MPa": s,
                        "measured": "", "predicted": v, "ratio_meas_over_pred": ""})
        print(f"    {s:7.1f} " + " ".join(f"{v:15.4e}" for v in vals))

print()
print("=" * 104)
print("TEST 3 -- spread across models at package stresses (max/min of the finite rates)")
print("=" * 104)
print(f"  {'T':>6} {'sigma':>7} {'max/min':>12}   models in play")
for T in (45., 80., 115., 150.):
    for s in PKG_SIGMA:
        v = {k: float(np.atleast_1d(f(s, T))[0]) for k, f in cl.MODELS.items()}
        fin = {k: x for k, x in v.items() if x == x and x > 0}
        if len(fin) > 1:
            print(f"  {T:6.0f} {s:7.1f} {max(fin.values())/min(fin.values()):12.4g}   "
                  f"{len(fin)} of {len(v)}")

p = R / "results" / "phase0l" / "high_stress_model_comparison.csv"
with p.open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
print(f"\nwrote {p}  ({len(out)} rows)")
