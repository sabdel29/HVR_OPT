#!/usr/bin/env python3
"""Complete the TIGHT matrix so every model is compared on identical solver settings.

The control runs showed the strain metric is insensitive to the solver control (<= 0.41 %) but
the INELASTIC ENERGY metric is not: it rises 11-24 % under tighter control, because most of the
inelastic work is deposited in the fast transient at the start of each half-cycle and the
default start under-resolves it. Mixing settings across models would therefore inject a
numerical difference into the model-form spread. Everything is run tight.
"""
from __future__ import annotations
import csv, sys, time
from pathlib import Path
R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0l"))
from replay import run_case, PROFILES, WD                                   # noqa: E402

OUT = R / "results" / "phase0l"
CSV = OUT / "package_model_replay_tight.csv"
jobs = [l.split() for l in Path("/tmp/missing_tight.txt").read_text().split("\n") if l.strip()]
rows = list(csv.DictReader(open(CSV))) if CSV.is_file() else []
t0 = time.time()
for i, (m, a, p) in enumerate(jobs, 1):
    r = run_case(m, a, PROFILES[p], tight=True)
    r["profile_tag"] = p
    rows.append(r)
    print(f"[{i:2d}/{len(jobs)}] {m:10s} {a} {p:12s} status={r.get('status')} "
          f"dPEEQ={r.get('d_peeq_per_cycle', float('nan')):.6g} "
          f"W={r.get('inelastic_work_MJ_per_m3', float('nan')):.6g} "
          f"({r.get('wall_s',0):.0f}s, elapsed {time.time()-t0:.0f}s)", flush=True)
    keys = sorted({k for rr in rows for k in rr})
    with CSV.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
    tag = f"{m}_{a}_" + ("BASE" if PROFILES[p] is None
                         else f"{PROFILES[p][0]:g}_{PROFILES[p][1]:g}") + "_T"
    for ext in (".frd", ".dat", ".12d"):
        f = WD / f"{tag}{ext}"
        if f.is_file() and tag not in ("M1_Z1_BASE_T", "M1_Z2_BASE_T", "M0_FINE_Z1_BASE_T"):
            f.unlink()
print(f"\nwrote {CSV}  ({len(rows)} tight runs, {time.time()-t0:.0f}s)")
