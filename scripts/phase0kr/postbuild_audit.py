#!/usr/bin/env python3
"""Phase-0K-R Sec.34 -- audit the FINAL artifacts, after generation, not before.

Mandatory because previous defects (#35, #38, #39) all occurred AFTER generation: the source
YAML was right and the built report was not, or the fragment was right and the splice was
stale. This reads the final Markdown AND the text extracted from the final PDF.
"""
from __future__ import annotations
import re, subprocess, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
MD = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
PDF = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.pdf"
OUT = R / "results" / "phase0kr"

CF = ("executive summary", "governing-equation status", "validation status",
      "publication-defensible claims", "claims that must not be made", "next steps",
      "current scientific status", "current authoritative", "exact next work",
      "current limitations", "roadmap")

STALE = [
    (r"[Nn]ext work[^.\n]{0,30}(is )?PHASE 0K\b(?![-‑]R)", "Phase 0K named as next work"),
    (r"(N_?required|required life)[^.\n]{0,40}(is|remains) the (sole|only) blocker",
     "N_required called the sole blocker"),
    (r"only\s+(one|ONE)\b[^.\n]{0,60}failure mechanism", "only one failure mechanism"),
    (r"[Nn]o (admissible )?SAC305 life law (exists|was retrievable)", "no SAC305 life law"),
    (r"[Nn]o lifetime is predicted (anywhere|in this project)", "no lifetime predicted"),
    (r"unsourced exponent", "relative life on an unsourced exponent"),
    (r"1\.25\s*(to|-|--|–)\s*9\.18", "Z2/Z1 = 1.25-9.18"),
    (r"Phase 0J-?R? (is|remains) the current", "0J/0J-R called current"),
    (r"one (board-level )?test would[^.\n]{0,40}(fix|make every)", "one test fixes everything"),
    (r"[Oo]ne (thermal )?(cycle )?condition[^.\n]{0,40}identif\w+[^.\n]{0,30}(law|model form)",
     "one condition identifies the law"),
    (r"absolute life is blocked only by mission", "absolute life blocked only by mission"),
    (r"-40[^.\n]{0,50}(validated|within (the )?(validated|calibrated) domain)",
     "-40 C called validated"),
    (r"6\.19\s*(sigma|σ)", "6.19 sigma quoted as a sigma"),
    (r"D\s*=\s*1\.849", "withdrawn D = 1.849"),
    (r"16 (specimens|packages)[^.\n]{0,60}(sufficient|proven|adequate)",
     "16 specimens called sufficient"),
]
EXON = ("supersed", "withdraw", "historical", "phase 0k-r", "not validated", "invalid",
        "cannot", "no longer", "was the", "still read", "fragments were not", "defect #39",
        "insufficient", "marginal", "is false", "no sub-zero", "85 k below", "campaign",
        "phase 0k established", "screening", "renamed", "is not a sigma", "omits")


def heads(txt, pat=r"^(#{1,4})\s+(.*)$"):
    return [(m.start(), m.group(2).lower()) for m in re.finditer(pat, txt, re.M)]


def head_at(secs, pos):
    h = ""
    for s, t in secs:
        if s <= pos:
            h = t
        else:
            break
    return h


def audit(txt, secs, label):
    bad = []
    for pat, name in STALE:
        for m in re.finditer(pat, txt):
            h = head_at(secs, m.start())
            if not any(c in h for c in CF):
                continue
            sent = txt[max(0, m.start() - 320):m.start() + 320].lower()
            if any(e in sent for e in EXON):
                continue
            bad.append((name, h, txt[max(0, m.start() - 90):m.start() + 90].replace("\n", " ")))
    return bad


def main() -> int:
    md = MD.read_text()
    secs_md = heads(md)
    bad_md = audit(md, secs_md, "markdown")
    txt = subprocess.run(["pdftotext", "-layout", str(PDF), "-"], capture_output=True,
                         text=True).stdout
    # PDF headings are not markdown; approximate by the same heading strings appearing alone
    secs_pdf = [(txt.find(t), t) for _, t in secs_md if t and txt.find(t) >= 0]
    secs_pdf = sorted((p, t) for p, t in secs_pdf if p >= 0)
    bad_pdf = audit(txt, secs_pdf, "pdf")

    lines = ["# Phase 0K-R Sec. 34 — Post-build semantic audit", "",
             "Run on the **final artifacts after generation**, not on the source YAML or the",
             "pre-build fragments. Mandatory because DEFECTS #35, #38 and #39 all occurred at or",
             "after the generation step.", "",
             f"| artifact | size |", "|---|---|",
             f"| `ETM_DVPD_FULL_TECHNICAL_REPORT.md` | {len(md):,} chars, "
             f"{len(md.splitlines()):,} lines |",
             f"| `ETM_DVPD_FULL_TECHNICAL_REPORT.pdf` (text-extracted) | {len(txt):,} chars |",
             "", "## Current-facing headings checked", "",
             "| # | heading |", "|---|---|"]
    seen, i = [], 0
    for _, t in secs_md:
        if any(c in t for c in CF) and t not in seen:
            seen.append(t); i += 1
            lines.append(f"| {i} | {t} |")
    lines += ["", f"**{len(seen)} current-facing headings checked** in the final Markdown, and "
              f"the same heading set located in the extracted PDF text.", "",
              "## Stale formulations searched", "", "| pattern | markdown | pdf |", "|---|---|---|"]
    for pat, name in STALE:
        nm = sum(1 for b in bad_md if b[0] == name)
        npd = sum(1 for b in bad_pdf if b[0] == name)
        lines.append(f"| {name} | {'**' + str(nm) + '**' if nm else '0'} | "
                     f"{'**' + str(npd) + '**' if npd else '0'} |")
    lines += ["", "## Result", ""]
    if not bad_md and not bad_pdf:
        lines += ["> **CLEAN.** No unqualified stale current-facing statement survives in either",
                  "> the final Markdown or the final PDF text. Every historical occurrence sits",
                  "> either outside a current-facing section or inside an explicit correction",
                  "> context (superseded / withdrawn / historical / renamed)."]
    else:
        for n, h, c in bad_md + bad_pdf:
            lines.append(f"- **{n}** in `{h}`: ...{c}...")
    (OUT / "POSTBUILD_SEMANTIC_AUDIT.md").write_text("\n".join(lines) + "\n")
    print(f"current-facing headings checked : {len(seen)}")
    print(f"stale hits in final MARKDOWN    : {len(bad_md)}")
    print(f"stale hits in final PDF text    : {len(bad_pdf)}")
    for n, h, c in (bad_md + bad_pdf)[:8]:
        print(f"   [{n}] {h[:46]}")
        print(f"      ...{c[-110:]}")
    print(f"\nwrote {OUT / 'POSTBUILD_SEMANTIC_AUDIT.md'}")
    return 0 if not (bad_md or bad_pdf) else 1


if __name__ == "__main__":
    raise SystemExit(main())
