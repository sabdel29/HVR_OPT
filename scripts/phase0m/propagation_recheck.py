#!/usr/bin/env python3
"""Phase-0M -- re-verify every surviving DEFECT-#44 scanner hit, one by one.

The Phase-0L-R scanner is a KEYWORD scanner with no exoneration logic, deliberately: DEFECT
#36 showed that an exoneration term can hide a real stale claim behind a green build. So it
fires on retractions, on definitions, and on a defect report quoting the defect it fixed.

Suppressing those would reintroduce exactly the risk the scanner exists to catch. Instead
every surviving hit is ADJUDICATED here, by excerpt, with its reason. The set is PINNED: a
hit that is not on this list fails the check, so a genuinely new stale claim cannot hide
among the known-benign ones.
"""
from __future__ import annotations
import csv, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
HITS = R / "results" / "phase0lr" / "defect44_hits.csv"
OUT = R / "results" / "phase0m"

# (report, claim_id, a distinctive fragment of the excerpt) -> why it is not a stale claim
ADJUDICATED = {
    ("HISTORICAL", "C02", "'validated relative life' is NOT earned"):
        "the sentence RETRACTS the phrase it contains. The scanner matches the phrase; the "
        "text forbids it.",
    ("HISTORICAL", "C03", "BLOCKED rather than ready to execute"):
        "likewise a retraction: it says the campaign is BLOCKED, and contains the words "
        "'ready to execute' only to deny them.",
    ("HISTORICAL", "C11", "C still cancels in a ratio"):
        "TRUE and complete in context. The life-law CONSTANT does cancel in a ratio; the "
        "very next sentence says 'That is necessary but NOT sufficient' and states the "
        "conditional 1.19 to 1.22 envelope. What does not cancel is the high-stress "
        "extrapolation, and the text says so.",
    ("HISTORICAL", "C11", "In the historical report they cluster in three GENERATED blocks"):
        "the Phase-0L-R defect report QUOTING the defect it repaired. A defect report must "
        "be allowed to quote the defect.",
    ("STANDALONE", "C06", "not SAC305) | **OPEN**"):
        "an open-items table row that RECORDS the alloy mismatch as OPEN. It is the "
        "disclosure, not the claim.",
    ("STANDALONE", "C08", "With no yield surface the integrated law is exactly"):
        "TRUE of the SELECTED model. M1 removes the yield surface, so the integrated law IS "
        "eps_dot = A sigma^n, confirmed to a median 3e-6 relative error. The pattern was "
        "written to catch that form being given as the law for the CARD WITH a yield "
        "surface, which is a different statement.",
    ("STANDALONE", "C08", "A power-law creep model"):
        "a GLOSSARY definition of the Norton law. A glossary must be allowed to define the "
        "term it names.",
    ("STANDALONE", "C11", "An error **cancels in a ratio** if it multiplies both"):
        "a DEFINITION of what cancellation means, immediately before the section that "
        "measures which errors do and do not cancel here.",
    ("STANDALONE", "C11", "preserved under every fatigue law admitted, because the law's"):
        "TRUE: the life-law CONSTANT cancels in a ratio, which is why the ORDERING is "
        "preserved. It is in the DEFENSIBLE TODAY column, and the NOT DEFENSIBLE column "
        "beside it denies the extrapolation cancelling.",
    ("STANDALONE", "C11", "stress extrapolation is common mode and cancels"):
        "in the **NOT DEFENSIBLE TODAY** column of the claims table, quoted in order to be "
        "refused. The scanner cannot see the column; a reader cannot miss it.",
}


def main() -> int:
    if not HITS.is_file():
        print("no scanner output -- run scripts/phase0lr/propagation_audit.py first")
        return 1
    rows = [r for r in csv.DictReader(HITS.open()) if r["status"] == "STALE-CURRENT"]
    used, unknown, out = set(), [], []
    for r in rows:
        key = next((k for k in ADJUDICATED
                    if k[0] == r["report"] and k[1] == r["claim_id"] and k[2] in r["excerpt"]),
                   None)
        if key is None:
            unknown.append(r)
            out.append({**r, "adjudication": "UNADJUDICATED -- NEW HIT"})
        else:
            used.add(key)
            out.append({**r, "adjudication": ADJUDICATED[key]})
    stale_keys = [k for k in ADJUDICATED if k not in used]
    with open(OUT / "propagation_recheck.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]) if out else ["report"])
        w.writeheader(); w.writerows(out)
    print(f"{len(rows)} STALE-CURRENT hits, {len(rows) - len(unknown)} adjudicated benign")
    for k in stale_keys:
        print(f"  NOTE: adjudication no longer needed (the text changed): {k[0]} {k[1]} "
              f"{k[2][:50]!r}")
    if unknown:
        print(f"\n{len(unknown)} UNADJUDICATED hit(s) -- these are NEW and must be repaired "
              f"or adjudicated:")
        for r in unknown:
            print(f"  {r['report']} {r['claim_id']} [{r['section'][:50]}] "
                  f"{r['excerpt'][:110]}")
        return 1
    print("every surviving hit is a verified keyword false positive; the set is pinned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
