#!/usr/bin/env python3
"""Re-run the decision-relevant replay cells with DEFECT #46 fixed.

DEFECT #46 inflated the inelastic-ENERGY metric by ~18.5 % by pairing tensors from one side of
a step boundary with a temperature from the other. Every energy-derived quantity -- w/eps, D,
the energy life-law ratios and hence the experiment sample count -- inherited that error.
The strain metric did not, because PEEQ is read from the solver rather than reconstructed.
"""
from __future__ import annotations
import csv, sys, time
from pathlib import Path
R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0l"))
from replay import run_case, PROFILES, WD                                   # noqa: E402

JOBS = ([("M1", a, p) for a in ("Z1", "Z2")
         for p in ("OP_BASELINE", "EXP_45_125", "EXP_110_150")]
        + [("M0_COARSE", a, p) for a in ("Z1", "Z2")
           for p in ("OP_BASELINE", "EXP_45_125", "EXP_110_150")])
rows, out = [], R / "results/phase0lr/package_replay_defect46_fixed.csv"
t0 = time.time()
for i, (m, a, p) in enumerate(JOBS, 1):
    r = run_case(m, a, PROFILES[p], tight=True)
    r["profile_tag"] = p
    rows.append(r)
    print(f"[{i:2d}/{len(JOBS)}] {m:10s} {a} {p:12s} {r.get('status')} "
          f"dPEEQ={r.get('d_peeq_per_cycle', float('nan')):.6g} "
          f"W={r.get('inelastic_work_MJ_per_m3', float('nan')):.6g} "
          f"({time.time()-t0:.0f}s)", flush=True)
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=sorted({k for rr in rows for k in rr}))
        w.writeheader(); w.writerows(rows)
    tag = f"{m}_{a}_" + ("BASE" if PROFILES[p] is None
                         else f"{PROFILES[p][0]:g}_{PROFILES[p][1]:g}") + "_T"
    for ext in (".frd", ".dat", ".12d"):
        f = WD / f"{tag}{ext}"
        if f.is_file():
            f.unlink()
print(f"\nwrote {out}  ({len(rows)} runs, {time.time()-t0:.0f}s)")
