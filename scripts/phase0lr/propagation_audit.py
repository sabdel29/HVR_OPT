#!/usr/bin/env python3
"""Phase-0L-R Part 1 -- DEFECT #44 directed comparison.

Searches BOTH reports for the specific stale current-facing claims the Phase-0L-R brief names,
classifies each hit by the SCOPE of the section it sits in, and by whether the sentence itself
carries a retraction.

Scope rules:
  * HISTORICAL report -- chronological. A "# Phase 0X ... (superseded by|extended by|SUPERSEDED)"
    chapter is HISTORICAL; everything else at top level is CURRENT-FACING, and the Phase-0L
    chapter is explicitly "current authoritative".
  * STANDALONE report -- describes only TODAY, so EVERY section is CURRENT-FACING by definition
    (Phase-0L-R brief, Part 23). A stale claim anywhere in it is a defect.
"""
from __future__ import annotations
import csv, json, re, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
HIST = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
STAND = R / "results" / "ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.md"
OUT = R / "results" / "phase0lr"

# (id, human label, regex, the VERBATIM sentence the pattern must be able to catch)
CLAIMS: list[tuple[str, str, str, str]] = [
    ("C01", "Z2/Z1 = 1.21-1.38 presented as current",
     r"1\.21\s*(?:--|-|\u2013|\u2014|to)\s*1\.38",
     "Z2 backside has a robust relative solder-fatigue-life advantage of 1.21--1.38."),
    ("C02", "relative life called validated",
     r"relative[- ]life[^.\n]{0,40}\bVALIDATED\b|RELATIVE LIFE VALIDATED|"
     r"\bvalidated relative life\b",
     "status: RELATIVE LIFE VALIDATED; ABSOLUTE LIFE CONDITIONAL"),
    ("C03", "experiment called ready to execute",
     r"ready to execute",
     "the experiment is READY TO EXECUTE WITH A DECLARED LIMITATION"),
    ("C04", "34 specimens per cell as current",
     r"34\s*(?:specimens?\s*)?(?:per|/)\s*cell|34 specimens",
     "the specimen count rises from 16 to 34 per cell"),
    ("C05", "136 packages as current",
     r"\b136\s*(?:total\s*)?packages\b|\b136 packages\b",
     "4 cells, 136 packages, ready to execute"),
    ("C06", "creep data called SAC305",
     r"SAC305 (?:steady-state )?creep (?:data|points|dataset)|"
     r"measured (?:SAC305|data for the correct alloy)",
     "PRIMARY EXPERIMENTAL DATA -- SAC305 steady-state creep points"),
    ("C07", "creep model called valid over the operating regime",
     r"creep (?:model|card)[^.\n]{0,50}\bvalid\b[^.\n]{0,40}(?:operating|package)|"
     r"near its calibrated range",
     "the card is evaluated near its calibrated range"),
    ("C08", "eps_dot = A sigma^n given as the current CalculiX law",
     r"\\dot\{\\varepsilon\}\s*=\s*A\s*\(?T\)?\s*\\?,?\s*\\sigma\^?\{?n|"
     r"eps_dot\s*=\s*A\s*\(?T\)?\s*\*?\s*sigma\s*\^\s*n|"
     r"varepsilon\}\s*=\s*A\s*\\sigma\^\{n\}",
     "the implemented law is \\dot{\\varepsilon} = A(T) \\sigma^{n}"),
    ("C09", "Arrhenius attributed to CalculiX's own interpolation",
     r"CalculiX[^.\n]{0,80}Arrhenius|Arrhenius[^.\n]{0,60}(?:inside|within) CalculiX|"
     r"solver[^.\n]{0,40}interpolates[^.\n]{0,30}Arrhenius",
     "CalculiX interpolates A(T) with an Arrhenius law"),
    ("C10", "mechanics described as M0 only",
     r"M0 only|only a linear thermoelastic|no (?:plasticity, )?creep or fatigue",
     "Mechanics is M0 only -- no plasticity, creep or fatigue"),
    ("C11", "high-stress extrapolation said to cancel",
     r"common mode and cancels|cancels in (?:a|the) ratio|extrapolation[^.\n]{0,50}cancels",
     "the constitutive extrapolation applies identically to all three architectures, so it is "
     "common mode and cancels in a ratio"),
    ("C12", "N_required called the only blocker",
     r"only (?:remaining )?blocker|sole blocker|the remaining blocker is[^.\n]{0,30}"
     r"(?:REQUIRED LIFE|N_?\{?required)",
     "the remaining blocker is a REQUIRED LIFE"),
    ("C13", "Phase 0K-R said to have frozen or closed the matrix",
     r"(?:0K-R|Phase 0K-R)[^.\n]{0,60}(?:froze|frozen|closed)[^.\n]{0,30}"
     r"(?:matrix|experiment|design)|experiment design FROZEN",
     "Phase 0K-R froze the experiment design"),
]

# A sentence that is ITSELF a retraction is the record working, not a defect.
RETRACT = re.compile(
    r"WITHDRAWN|withdrawn|SUPERSEDED|superseded|no longer|is wrong|was wrong|not defensible|"
    r"NOT validated|not validated|corrected here|previously|before Phase 0L|is refuted|refuted|"
    r"does not hold|must not|never|rejected|stale|historical record|retained as|"
    r"WITHDRAW|does NOT|is FALSE|incorrect|overstat", re.I)


def chapter_scope(head: str, standalone: bool) -> str:
    if standalone:
        return "CURRENT-FACING"
    if re.match(r"^Phase 0[A-Z]", head, re.I) or head.startswith("PHASE 0"):
        return "CURRENT-FACING" if "current authoritative" in head.lower() else "HISTORICAL"
    if re.search(r"historical record", head, re.I):
        return "HISTORICAL"
    return "CURRENT-FACING"


def sections(md: str, standalone: bool):
    """-> list of (start, end, heading, scope).

    A '##' subsection INHERITS the scope of the '#' chapter it sits in. Without that, a
    subsection like 'Where the project stands' inside the superseded Phase-0K-R chapter reads
    as current-facing and every historical chapter looks full of live stale claims.
    """
    lines = md.split("\n")
    idx = [(i, l) for i, l in enumerate(lines) if re.match(r"^#{1,3} \S", l)]
    out, cur_chapter, cur_scope = [], "(front matter)", "CURRENT-FACING"
    for k, (i, l) in enumerate(idx):
        j = idx[k + 1][0] if k + 1 < len(idx) else len(lines)
        level = len(l) - len(l.lstrip("#"))
        head = l.lstrip("# ").strip()
        if level == 1:
            cur_chapter, cur_scope = head, chapter_scope(head, standalone)
            label = head
        else:
            label = f"{cur_chapter} :: {head}"
        out.append((i, j, label, cur_scope))
    return out, lines


def scan(path: Path, standalone: bool, tag: str):
    md = path.read_text()
    secs, lines = sections(md, standalone)
    rows = []
    for cid, label, pat, _canon in CLAIMS:
        rx = re.compile(pat, re.I)
        for si, (a, b, head, scope) in enumerate(secs):
            body = "\n".join(lines[a:b])
            for m in rx.finditer(body):
                # the sentence containing the hit
                lo = body.rfind(".", 0, m.start()) + 1
                hi = body.find(".", m.end())
                sent = body[lo:hi if hi > 0 else min(len(body), m.end() + 240)]
                sent = " ".join(sent.split())
                retracted = bool(RETRACT.search(sent))
                if scope == "CURRENT-FACING" and not retracted:
                    status = "STALE-CURRENT"
                elif scope == "CURRENT-FACING":
                    status = "CURRENT-RETRACTED"
                elif retracted:
                    status = "HISTORICAL-RETRACTED"
                else:
                    status = "HISTORICAL-UNMARKED"
                rows.append({"report": tag, "claim_id": cid, "claim": label,
                             "section": head[:70], "scope": scope,
                             "sentence_retracts": retracted, "status": status,
                             "excerpt": sent[:200]})
    return rows


def main() -> int:
    rows = scan(HIST, False, "HISTORICAL") + scan(STAND, True, "STANDALONE")
    p = OUT / "defect44_hits.csv"
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    print(f"{'report':>11} {'id':>4} {'status':>21}  section / excerpt")
    print("=" * 112)
    bad = [r for r in rows if r["status"] in ("STALE-CURRENT", "HISTORICAL-UNMARKED")]
    for r in sorted(bad, key=lambda r: (r["report"], r["claim_id"])):
        print(f"{r['report']:>11} {r['claim_id']:>4} {r['status']:>21}  [{r['section'][:44]}]")
        print(f"{'':>39}  {r['excerpt'][:104]}")
    print()
    from collections import Counter
    for tag in ("HISTORICAL", "STANDALONE"):
        c = Counter(r["status"] for r in rows if r["report"] == tag)
        print(f"{tag:>11}: " + ", ".join(f"{k}={v}" for k, v in sorted(c.items())))
    n_stale = sum(1 for r in rows if r["status"] == "STALE-CURRENT")
    n_unmarked = sum(1 for r in rows if r["status"] == "HISTORICAL-UNMARKED")
    print(f"\nSTALE-CURRENT hits: {n_stale};  HISTORICAL-UNMARKED hits: {n_unmarked}")
    print(f"DEFECT #44 is {'CONFIRMED' if (n_stale or n_unmarked) else 'NOT CONFIRMED'}")
    print(f"\nwrote {p}  ({len(rows)} hits)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
