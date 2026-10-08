#!/usr/bin/env python3
"""Phase-0L Part XI follow-up: the runs that need tighter solver control, plus the control
experiment that proves the tighter control does not itself move the answer.

M1_NHI (n + 2 SE) diverges on the FIRST increment with the default start. The remedy is solver
control, not a model change: a smaller starting increment (1e-8 s instead of 1e-5 s) and a lower
floor (1e-14 s instead of 1e-12 s). Tighter control is strictly more accurate, but using it for
one model and not the others would confound solver settings with constitutive model. So M1 and
M0_FINE are ALSO re-run under the tight settings at the baseline, and the difference is measured.
"""
from __future__ import annotations
import csv, sys, time
from pathlib import Path
R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0l"))
from replay import run_case, PROFILES, WD                                   # noqa: E402

JOBS = ([("M1_NHI", a, "OP_BASELINE") for a in ("Z1", "Z2", "Z4")]
        + [("M1_NHI", a, p) for a in ("Z1", "Z2")
           for p in ("EXP_45_125", "EXP_110_150")]
        # control: same settings, models that already ran under the default control
        + [(m, a, "OP_BASELINE") for m in ("M0_FINE", "M1") for a in ("Z1", "Z2")])

rows, out = [], R / "results" / "phase0l" / "package_model_replay_tight.csv"
t0 = time.time()
for i, (m, a, p) in enumerate(JOBS, 1):
    r = run_case(m, a, PROFILES[p], tight=True)
    r["profile_tag"] = p
    rows.append(r)
    print(f"[{i:2d}/{len(JOBS)}] {m:10s} {a} {p:12s} status={r.get('status')} "
          f"dPEEQ={r.get('d_peeq_per_cycle', float('nan')):.6g} "
          f"W={r.get('inelastic_work_MJ_per_m3', float('nan')):.6g} "
          f"({r.get('wall_s', 0):.0f}s, elapsed {time.time()-t0:.0f}s)", flush=True)
    keys = sorted({k for rr in rows for k in rr})
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
    # the .dat for a tight run is ~250 MB; keep the parsed numbers, drop the bulk
    tag = f"{m}_{a}_" + ("BASE" if PROFILES[p] is None
                         else f"{PROFILES[p][0]:g}_{PROFILES[p][1]:g}") + "_T"
    for ext in (".frd", ".dat", ".12d"):
        f = WD / f"{tag}{ext}"
        if f.is_file():
            f.unlink()
print(f"\nwrote {out}  ({len(rows)} runs, {time.time()-t0:.0f}s)")
