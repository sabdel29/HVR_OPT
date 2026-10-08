#!/usr/bin/env python3
"""Phase-0M-R3 Section 1 --- structural repairs to the historical report.

Every repair is IDEMPOTENT and is verified by re-running the semantic audit.
"""
from __future__ import annotations
import re, sys
from collections import Counter
from pathlib import Path

R = Path(__file__).resolve().parents[2]
REP = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
STAND = R / "results" / "ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.md"

GEN_DATE = "2026-09-19"
BASELINE_DATE = "2026-09-08"


def dedupe_paragraphs(s: str) -> tuple[str, int]:
    """Keep the FIRST occurrence of any paragraph of 200+ chars, drop later copies.

    Phase 0M-R2 shipped four identical copies of one paragraph because its builder
    inserted outside a sentinel block and its idempotency guard had a case mismatch.
    """
    parts = re.split(r"(\n\s*\n)", s)
    seen: set[str] = set()
    out, removed = [], 0
    for p in parts:
        key = " ".join(p.split())
        if len(key) >= 200 and not key.startswith("|") and not key.startswith("<!--"):
            if key in seen:
                removed += 1
                continue
            seen.add(key)
        out.append(p)
    res = "".join(out)
    return re.sub(r"\n{4,}", "\n\n\n", res), removed


def fix_provenance(s: str) -> tuple[str, list[str]]:
    done = []
    # one ambiguous "Report date" row -> three labelled rows
    m = re.search(r"\|\s*Report date\s*\|\s*[^|]+\|\n", s)
    if m:
        s = s.replace(m.group(0),
                      f"| Report generated | {GEN_DATE} |\n"
                      f"| Repository baseline | {BASELINE_DATE} |\n"
                      f"| Phase completed | 0M-R3, {GEN_DATE} |\n")
        done.append("provenance dates disambiguated")
    # Palace: measured NOT FOUND this phase
    m2 = re.search(r"\|\s*Full-wave EM available\s*\|\s*[^|]*\|\n", s)
    if m2 and "NOT FOUND" not in m2.group(0):
        s = s.replace(m2.group(0),
                      "| Full-wave EM available | **PALACE NOT FOUND on this system "
                      "(measured Phase 0M-R3).** Earlier phases recorded it as built and "
                      "functional; it is not present now and nothing current depends on it |\n")
        done.append("Palace availability corrected")
    m3 = re.search(r"\|\s*Commercial EM/thermal\s*\|\s*[^|]*\|\n", s)
    if m3 and "Fluent" not in m3.group(0):
        s = s.replace(m3.group(0), m3.group(0).rstrip("\n").rstrip("|")
                      + "; Fluent NOT INSTALLED |\n")
        done.append("Fluent availability recorded")
    return s, done


def fix_front_matter(s: str) -> tuple[str, list[str]]:
    s2 = re.sub(r'(?m)^date: "\d{4}-\d{2}-\d{2}"$', f'date: "{GEN_DATE}"', s, count=1)
    return s2, (["front-matter date"] if s2 != s else [])


def main() -> int:
    total = []
    for path, name in ((REP, "HISTORICAL"), (STAND, "STANDALONE")):
        if not path.is_file():
            continue
        s = orig = path.read_text()
        s, n = dedupe_paragraphs(s)
        if n:
            total.append(f"{name}: removed {n} duplicate paragraph(s)")
        s, d1 = fix_provenance(s)
        s, d2 = fix_front_matter(s)
        total += [f"{name}: {x}" for x in d1 + d2]
        if s != orig:
            path.write_text(s)
    for t in total:
        print("  " + t)
    if not total:
        print("  nothing to repair (idempotent)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
