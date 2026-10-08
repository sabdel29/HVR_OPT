#!/usr/bin/env python3
"""Phase-0L Part XII -- is the high-stress constitutive extrapolation common mode?

Phase 0K-R asserted that the 3.4x-7.2x stress extrapolation "applies identically to all three
architectures, so it is common mode and cancels in a ratio". That was an assumption. This
script tests it against the tolerance frozen in results/phase0l/PART12_PREDECLARED_TOLERANCE.md
BEFORE any ratio under an alternative model existed.

Predeclared, sha256 fc19abf7eff93c17aec802b2c488d0e5c76c7e7929b77cd751595ed434365355:

    S = (max_m r_m - min_m r_m) / median_m r_m         over admitted models m
    E_min = 0.21                                        the smallest architecture effect

    ROBUST   : S <= 0.25 * E_min = 0.0525  AND every r_m > 1
    PARTIAL  : 0.0525 < S <= 0.21          AND every r_m > 1
    MODEL-FORM DEPENDENT : S > 0.21        OR  any r_m <= 1
"""
from __future__ import annotations
import csv, math, statistics, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0l"
E_MIN = 0.21
ROBUST_S, PARTIAL_S = 0.25 * E_MIN, 1.00 * E_MIN

# life-law exponents: N_f proportional to (metric)^(-k)
LAWS = [("Syed2004_Eq14_strain", "d_peeq_per_cycle", 1.0),
        ("Schubert2003_strain", "d_peeq_per_cycle", 1.3),
        ("Syed2004_Eq15_energy", "inelastic_work_MJ_per_m3", 1.0),
        ("Schubert2003_energy", "inelastic_work_MJ_per_m3", 1.0)]
METRICS = [("M1_creep_strain", "d_peeq_per_cycle"),
           ("M2_within_cycle_range", "range_eq_inelastic"),
           ("M3_inelastic_energy", "inelastic_work_MJ_per_m3")]


def load():
    rows = []
    for f in ("package_model_replay.csv", "package_model_replay_tight.csv"):
        p = OUT / f
        if p.is_file():
            rows += [r for r in csv.DictReader(open(p)) if r.get("status") == "OK"]
    # a TIGHT run supersedes a DEFAULT run of the same (model, arch, profile)
    best = {}
    for r in rows:
        k = (r["model"], r["arch"], r["profile_tag"])
        if k not in best or r.get("solver_control") == "TIGHT":
            best[k] = r
    # Solver settings must not vary across the models being compared. The control runs showed
    # the strain metric is insensitive to them (<= 0.41 %) but the inelastic ENERGY metric is
    # not (+11 to +24 % under tighter control), so a mixed set would inject a numerical
    # difference into the model-form spread and read as physics.
    ctrls = {v.get("solver_control", "DEFAULT") for v in best.values()}
    if len(ctrls) > 1:
        import sys as _s
        by = {}
        for k, v in best.items():
            by.setdefault(v.get("solver_control", "DEFAULT"), []).append(k)
        for c, ks in sorted(by.items()):
            print(f"  {c}: {len(ks)} runs", file=_s.stderr)
        _s.exit("REFUSING TO COMPARE: solver control is not uniform across the replay set. "
                "Complete the TIGHT matrix (scripts/phase0l/run_replay_tight_rest.py) first.")
    return best


def main() -> int:
    data = load()
    models = sorted({k[0] for k in data})
    profiles = sorted({k[2] for k in data})
    out, summary = [], []

    for prof in profiles:
        print("=" * 104)
        print(f"PROFILE {prof}")
        print("=" * 104)
        print(f"{'model':>11} {'ctrl':>8} " + " ".join(f"{n.split('_')[0]:>12}" for n, _ in METRICS)
              + "   " + " ".join(f"{n[:11]:>12}" for n, _, _ in LAWS))
        per_model = {}
        for m in models:
            z1, z2 = data.get((m, "Z1", prof)), data.get((m, "Z2", prof))
            if not (z1 and z2):
                continue
            row = {"profile": prof, "model": m,
                   "solver_control": z1.get("solver_control", "DEFAULT")}
            for name, key in METRICS:
                a, b = float(z1[key]), float(z2[key])
                row[f"ratio_{name}"] = a / b            # Z1 metric over Z2 metric
            for lname, key, k in LAWS:
                a, b = float(z1[key]), float(z2[key])
                row[f"life_{lname}"] = (a / b) ** k     # N_f,Z2 / N_f,Z1
            z4 = data.get((m, "Z4", prof))
            if z4:
                row["life_Z4_over_Z1_Syed14"] = (float(z1["d_peeq_per_cycle"])
                                                 / float(z4["d_peeq_per_cycle"]))
            per_model[m] = row
            out.append(row)
            print(f"{m:>11} {row['solver_control']:>8} "
                  + " ".join(f"{row[f'ratio_{n}']:12.4f}" for n, _ in METRICS)
                  + "   " + " ".join(f"{row[f'life_{n}']:12.4f}" for n, _, _ in LAWS))
        if len(per_model) < 2:
            print("  (fewer than two models -- no spread computable)\n"); continue

        print()
        print(f"  {'quantity':>26} {'min':>9} {'median':>9} {'max':>9} {'S':>8}  "
              f"{'sign?':>6}  classification")
        for lname, _, _ in LAWS:
            v = [r[f"life_{lname}"] for r in per_model.values()]
            med = statistics.median(v)
            S = (max(v) - min(v)) / med
            allpos = all(x > 1.0 for x in v)
            cls = ("ROBUST COMMON-MODE CANCELLATION" if (S <= ROBUST_S and allpos)
                   else "PARTIAL CANCELLATION" if (S <= PARTIAL_S and allpos)
                   else "RELATIVE-LIFE RESULT MODEL-FORM DEPENDENT")
            print(f"  {lname:>26} {min(v):9.4f} {med:9.4f} {max(v):9.4f} {S:8.4f}  "
                  f"{'all>1' if allpos else 'NO':>6}  {cls}")
            summary.append({"profile": prof, "quantity": lname, "n_models": len(v),
                            "min": min(v), "median": med, "max": max(v), "spread_S": S,
                            "all_ratios_above_1": allpos, "classification": cls,
                            "threshold_robust": ROBUST_S, "threshold_partial": PARTIAL_S})
        print()

    p1 = OUT / "common_mode_cancellation_test.csv"
    with p1.open("w", newline="") as fh:
        keys = sorted({k for r in out for k in r})
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(out)
    p2 = OUT / "common_mode_verdict.csv"
    with p2.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0].keys()))
        w.writeheader(); w.writerows(summary)
    print(f"wrote {p1}\nwrote {p2}")

    base = [s for s in summary if s["profile"] == "BASE"]
    if base:
        worst = max(base, key=lambda s: s["spread_S"])
        print()
        print("OPERATING-BASELINE HEADLINE")
        print(f"  worst quantity : {worst['quantity']}  S = {worst['spread_S']:.4f}")
        print(f"  classification : {worst['classification']}")
        lo = min(s["min"] for s in base); hi = max(s["max"] for s in base)
        print(f"  Z2/Z1 life ratio spans {lo:.3f} to {hi:.3f} across all models and all laws")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
