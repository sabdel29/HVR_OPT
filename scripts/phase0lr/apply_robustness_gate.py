#!/usr/bin/env python3
"""Phase-0L-R Part 10 -- apply the predeclared model-form robustness gate.

The gate was frozen and hashed in results/phase0lr/PART10_PREDECLARED_ROBUSTNESS_GATE.md
(sha256 b508c3ed...) BEFORE any ratio under a second constitutive family existed. It is applied
here exactly as written, first-matching-row-wins.
"""
from __future__ import annotations
import csv, hashlib, math, statistics, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0lr"
E_MIN = 0.17
ROBUST_S, PARTIAL_S = 0.25 * E_MIN, 1.00 * E_MIN
F = lambda r, k: float(r[k])


def check_hash():
    doc = OUT / "PART10_PREDECLARED_ROBUSTNESS_GATE.md"
    want = (OUT / "PART10_PREDECLARED_ROBUSTNESS_GATE.sha256").read_text().split()[0]
    got = hashlib.sha256(doc.read_bytes()).hexdigest()
    if got != want:
        sys.exit("the predeclared gate has been edited after the fact -- refusing to apply it")
    return want


def main() -> int:
    h = check_hash()
    print(f"predeclared gate verified, sha256 {h[:16]}...")

    # ---- the model set, with its FAMILY label -------------------------------------------
    tight = {(r["model"], r["arch"]): r for r in
             csv.DictReader(open(R / "results/phase0l/package_model_replay_tight.csv"))
             if r["status"] == "OK" and r["profile_tag"] == "OP_BASELINE"}
    anand = {r["arch"]: r for r in
             csv.DictReader(open(OUT / "anand_family_replay.csv")) if r["status"] == "OK"}

    ENTRIES = [
        ("M1",      "NORTON", "Norton, SnAgCu surrogate, central exponent"),
        ("M1_NLO",  "NORTON", "Norton, n - 2 SE (parametric, same family)"),
        ("M1_NHI",  "NORTON", "Norton, n + 2 SE (parametric, same family)"),
    ]
    rows = []
    for model, fam, note in ENTRIES:
        z1, z2 = tight.get((model, "Z1")), tight.get((model, "Z2"))
        if not (z1 and z2):
            continue
        rows.append({"model": model, "family": fam, "note": note,
                     "r_strain": F(z1, "d_peeq_per_cycle") / F(z2, "d_peeq_per_cycle"),
                     "r_energy": (F(z1, "inelastic_work_MJ_per_m3")
                                  / F(z2, "inelastic_work_MJ_per_m3")),
                     "r_range": (F(z1, "range_eq_inelastic") / F(z2, "range_eq_inelastic"))})
    if "Z1" in anand and "Z2" in anand:
        a1, a2 = anand["Z1"], anand["Z2"]
        rows.append({"model": "M2_ANAND", "family": "ANAND",
                     "note": "Anand (Yamin/Motalab SAC305), reduced over 5-15 MPa (n=8.97), "
                             "the highest-stress reduction this solver can integrate",
                     "r_strain": F(a1, "d_peeq_per_cycle") / F(a2, "d_peeq_per_cycle"),
                     "r_energy": (F(a1, "inelastic_work_MJ_per_m3")
                                  / F(a2, "inelastic_work_MJ_per_m3")),
                     "r_range": F(a1, "range_eq_inelastic") / F(a2, "range_eq_inelastic")})

    print()
    print(f"{'model':>10} {'family':>8} {'r_strain':>9} {'r_energy':>9} {'r_range':>9}")
    for r in rows:
        print(f"{r['model']:>10} {r['family']:>8} {r['r_strain']:9.4f} {r['r_energy']:9.4f} "
              f"{r['r_range']:9.4f}")

    families = sorted({r["family"] for r in rows})
    allr = [r[k] for r in rows for k in ("r_strain", "r_energy", "r_range")]
    any_reversal = any(x <= 1.0 for x in allr)

    print()
    print(f"distinct model FAMILIES parameterised and replayed: {len(families)}  {families}")
    print(f"every ratio > 1 : {not any_reversal}  (min over all metrics/models "
          f"= {min(allr):.4f})")

    verdicts = []
    for key, lab in (("r_strain", "creep strain"), ("r_energy", "inelastic energy"),
                     ("r_range", "within-cycle range")):
        v = [r[key] for r in rows]
        med = statistics.median(v)
        S = (max(v) - min(v)) / med
        verdicts.append({"metric": lab, "n_models": len(v), "n_families": len(families),
                         "min": min(v), "median": med, "max": max(v), "spread_S": S,
                         "every_ratio_above_1": all(x > 1 for x in v)})
        print(f"  {lab:>20}: min {min(v):.4f} med {med:.4f} max {max(v):.4f}  S = {S:.4f}")

    # ---- the gate, first matching row wins ------------------------------------------------
    if any_reversal:
        cls = "MODEL-FORM DEPENDENT"
        why = "a defensible model gives an architecture ratio at or below 1"
    elif len(families) < 3:
        cls = "INSUFFICIENT EVIDENCE"
        why = (f"only {len(families)} distinct model FAMILIES could be parameterised AND "
               f"integrated over the package stress range; the gate requires three. "
               f"M1_NLO/M1_NHI are parametric perturbations of the Norton family, not a "
               f"second form, and the gate says so explicitly.")
    else:
        worst = max(v["spread_S"] for v in verdicts)
        if worst <= ROBUST_S:
            cls, why = "MAGNITUDE ROBUST", f"worst S = {worst:.4f} <= {ROBUST_S:.4f}"
        elif worst <= PARTIAL_S:
            cls, why = "ORDERING ONLY ROBUST", f"worst S = {worst:.4f} <= {PARTIAL_S:.4f}"
        else:
            cls, why = "ORDERING ROBUST, MAGNITUDE UNBOUNDED", f"worst S = {worst:.4f} > {PARTIAL_S:.4f}"

    print()
    print("=" * 92)
    print(f"GATE RESULT: {cls}")
    print(f"  reason: {why}")
    print("=" * 92)
    print("Observation recorded OUTSIDE the gate (it is evidence, not a gate result): the two")
    print("families that could both be integrated agree on the strain ratio to "
          f"{100*abs(rows[0]['r_strain']/rows[-1]['r_strain']-1):.1f} % "
          f"({rows[0]['r_strain']:.4f} vs {rows[-1]['r_strain']:.4f}).")

    p = OUT / "model_form_robustness.csv"
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    p2 = OUT / "model_form_gate_result.csv"
    for v in verdicts:
        v["gate_classification"] = cls; v["gate_reason"] = why
        v["threshold_magnitude_robust"] = ROBUST_S; v["threshold_ordering_only"] = PARTIAL_S
    with p2.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(verdicts[0].keys())); w.writeheader(); w.writerows(verdicts)
    print(f"\nwrote {p}\nwrote {p2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
