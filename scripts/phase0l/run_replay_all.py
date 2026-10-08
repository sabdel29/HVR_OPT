#!/usr/bin/env python3
"""Phase-0L Part XI driver: every admissible model x architecture x profile."""
from __future__ import annotations
import csv, sys, time
from pathlib import Path
R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0l"))
from replay import run_case, PROFILES                                       # noqa: E402

MODELS = ["M0_COARSE", "M0_FINE", "M1", "M1_NLO", "M1_NHI"]
JOBS = ([(m, a, "OP_BASELINE") for m in MODELS for a in ("Z1", "Z2", "Z4")]
        + [(m, a, p) for m in MODELS for a in ("Z1", "Z2")
           for p in ("EXP_45_125", "EXP_110_150")])

rows, out = [], R / "results" / "phase0l" / "package_model_replay.csv"
t0 = time.time()
for i, (m, a, p) in enumerate(JOBS, 1):
    r = run_case(m, a, PROFILES[p])
    r["profile_tag"] = p
    rows.append(r)
    print(f"[{i:2d}/{len(JOBS)}] {m:10s} {a} {p:12s} "
          f"status={r.get('status')} dPEEQ={r.get('d_peeq_per_cycle', float('nan')):.6g} "
          f"W={r.get('inelastic_work_MJ_per_m3', float('nan')):.6g} "
          f"({r.get('wall_s', 0):.0f}s, elapsed {time.time()-t0:.0f}s)", flush=True)
    keys = sorted({k for rr in rows for k in rr})
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
print(f"\nwrote {out}  ({len(rows)} runs, {time.time()-t0:.0f}s total)")
