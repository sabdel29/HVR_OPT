#!/usr/bin/env python3
"""Phase-0M Part 0 -- close the residual Phase-0L-R report and numerics items.

Five text repairs (A, B, C, D, E of the Phase-0M brief) applied as ONE staged transaction
per file. Every edit is checked for presence and uniqueness BEFORE anything is written; a
failure aborts with no file touched. (Earlier phases lost a batch of edits twice by writing
after a sequence of asserts, one of which threw.)

  A  stale Phase-0H language in current-facing status
  B  obsolete next-step statement naming Phase 0L
  C  Anand wording: PARAMETERIZED in the regime vs INTEGRATED through the production solve
  D  authoritative specimen-count provenance table (written by provenance.py)
  E  theorem-like "any monotone law MUST rank Z1 worse" -> the licensed structural wording
"""
from __future__ import annotations
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
RES = R / "results"
OUT = RES / "phase0m"
OUT.mkdir(parents=True, exist_ok=True)

STRUCTURAL = ("the global package supplies a constitutive-law-independent deformation "
              "driver favoring Z2, and every presently testable constitutive/life-law "
              "combination preserves that ordering")

EDITS: dict[str, list[tuple[str, str, str]]] = {}


def edit(path: str, item: str, old: str, new: str) -> None:
    EDITS.setdefault(path, []).append((item, old, new))


# ---------------------------------------------------------------- E: theorem wording
edit("ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.md", "E1",
     "Z1 and contains no solder constitutive law at all, so any law monotone in imposed\n"
     "displacement must reproduce it.",
     "Z1 and contains no solder constitutive law at all, so " + STRUCTURAL + ".")

edit("ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.md", "E2",
     "Any constitutive law that is monotone in imposed cyclic displacement must therefore "
     "rank Z1 worse, which is a structural reason for the ordering rather than an empirical one.",
     "Stated without overreach: " + STRUCTURAL + " --- a structural reason for the ordering "
     "rather than an empirical one. It is not a theorem about all monotone laws, because the "
     "set of laws this solver can integrate is bounded (Norton exponent below about 9 to 10) "
     "and no proof covers laws outside it.")

edit("ETM_DVPD_FULL_TECHNICAL_REPORT.md", "E3",
     "so any law monotone in imposed displacement must reproduce it.",
     "so " + STRUCTURAL + ".")

edit("ETM_DVPD_FULL_TECHNICAL_REPORT.md", "E4",
     "Any law monotone in imposed cyclic displacement must rank Z1 worse.",
     "Stated without overreach: " + STRUCTURAL + ". That is a structural statement about the "
     "driver, not a theorem about every conceivable law.")

edit("phase0lr/PHASE0LR_CONSTITUTIVE_AND_REPORT_CLOSURE.md", "E5",
     "Any law monotone in imposed cyclic displacement must therefore rank Z1 worse.",
     "Stated without overreach (revised in Phase 0M Part 0-E): " + STRUCTURAL + ".")

edit("phase0lr/Z1_Z2_MECHANISM_AUDIT.md", "E6",
     "2. **Damage is monotone in imposed strain.** Every physically admissible viscoplastic "
     "law gives\n   more accumulated inelastic strain for a larger imposed cyclic displacement "
     "at the same\n   temperature and cycle shape. Reversing Z1 and Z2 would require a law that "
     "is *anti-monotone*\n   in imposed displacement, which is not a property any candidate in "
     "the literature has.",
     "2. **Damage rises with imposed strain in every law tested.** Every viscoplastic law "
     "replayed\n   here, and every candidate form retrieved from the literature, gives more "
     "accumulated\n   inelastic strain for a larger imposed cyclic displacement at the same "
     "temperature and cycle\n   shape. Reversing Z1 and Z2 would require a law that is "
     "*anti-monotone* in imposed\n   displacement. No such candidate was found --- which is an "
     "absence of counterexamples over the\n   laws this solver can integrate, not a proof over "
     "all laws.")

edit("phase0lr/Z1_Z2_MECHANISM_AUDIT.md", "E7",
     "answer — not for a monotone law, given a 32 % difference in the driver — and not "
     "merely the\nempirical answer \"the four models we ran all agreed\".",
     "answer: " + STRUCTURAL + ". That is stronger than the\nbare empirical answer \"the four "
     "models we ran all agreed\", and weaker than a theorem.")

edit("phase0lr/LIFE_LAW_STATUS_AFTER_PHASE0L.md", "E8",
     "cannot within this framework: the ordering originates in the global thermoelastic model, "
     "upstream\nof the solder law, and damage is monotone in imposed displacement.",
     "cannot within this framework: " + STRUCTURAL + ".")

# ---------------------------------------------------------------- C: Anand wording
edit("ETM_DVPD_FULL_TECHNICAL_REPORT.md", "C1",
     "> **Predeclared model-form gate: INSUFFICIENT EVIDENCE** --- only two model families "
     "could be parameterised AND integrated where the package operates, and the gate requires "
     "three.",
     "> **Predeclared model-form gate: INSUFFICIENT EVIDENCE** --- two constitutive families "
     "(Norton and Anand) can currently be PARAMETERIZED in the relevant regime, and only ONE "
     "of them can presently be INTEGRATED through the production package solve; the gate "
     "requires three families parameterised and integrated.")

edit("ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.md", "C2",
     "constitutive forms can ever be replayed here: the Anand family can only be run through a\n"
     "low-stress reduction, which is why the model-form question cannot be settled by replay alone.",
     "constitutive forms can ever be replayed here. Stated precisely: **two constitutive "
     "families can\ncurrently be PARAMETERIZED in the relevant regime, and only one of them "
     "can presently be\nINTEGRATED through the production package solve.** The Anand family "
     "runs only through a\nlow-stress reduction, which is why the model-form question cannot "
     "be settled by replay alone.")

# ---------------------------------------------------------------- A: stale Phase-0H language
_METHOD_OLD = ("**Method.** Eleven sequential falsification gates (0B-0I plus the 0D-R and "
               "0I-R audit gates),")
_METHOD_NEW = ("**Method.** Sixteen sequential falsification gates (0B, 0C, 0D, 0D-R, 0E, 0F, "
               "0G, 0H, 0I, 0I-R, 0J, 0J-R, 0K, 0K-R, 0L, 0L-R) plus the Phase-0M "
               "model-generalization audit,")
edit("ETM_DVPD_FULL_TECHNICAL_REPORT.md", "A1", _METHOD_OLD, _METHOD_NEW)


def stage() -> list[tuple[Path, str]]:
    """Validate every edit, then return the new content of every file. Nothing written."""
    staged, problems = [], []
    for rel, items in EDITS.items():
        p = RES / rel
        if not p.is_file():
            problems.append(f"{rel}: FILE MISSING")
            continue
        s0 = s = p.read_text()
        for item, old, new in items:
            n = s.count(old)
            if n == 0:
                if s.count(new):
                    print(f"  {rel} [{item}] already applied")
                    continue
                problems.append(f"{rel} [{item}]: pattern NOT FOUND -- {old[:70]!r}")
                continue
            if n > 1:
                problems.append(f"{rel} [{item}]: pattern occurs {n} times, not unique")
                continue
            s = s.replace(old, new)
            print(f"  {rel} [{item}] staged")
        if s != s0:
            staged.append((p, s))
    if problems:
        print("\nABORTED -- nothing written:")
        for q in problems:
            print("  " + q)
        raise SystemExit(1)
    return staged


def main() -> int:
    print("staging Phase-0M Part-0 closure edits")
    staged = stage()
    for p, s in staged:
        p.write_text(s)
    print(f"\napplied to {len(staged)} file(s)")
    # post-condition: the retired wording must be gone from both current-facing reports
    for rel in ("ETM_DVPD_FULL_TECHNICAL_REPORT.md",
                "ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.md"):
        t = (RES / rel).read_text()
        for bad in ("must reproduce it.", "must rank Z1 worse", "must therefore rank Z1 worse",
                    "Eleven sequential falsification gates"):
            assert bad not in t, f"{rel}: retired wording still present -- {bad!r}"
    print("post-conditions pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
