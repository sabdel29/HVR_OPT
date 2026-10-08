#!/usr/bin/env python3
"""Regenerate the capability matrix in PRIOR_FRAMEWORK_COMPARISON.md from the manuscript.

The manuscript table is the single source. Keeping a second hand-written copy of the same
scores is how one of them goes stale, so the markdown section is derived, never edited.
"""
from __future__ import annotations
import re, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
TEX = R / "manuscript" / "ETM_DVPD_JOURNAL_MANUSCRIPT.tex"
MD = R / "manuscript" / "PRIOR_FRAMEWORK_COMPARISON.md"
KEY = {"Krishnakumar2026DVPD": "A", "Sriharini_ECTC_24": "B", "ISCAS2024DVPD": "C",
       "VPD2023Architectures": "E", "DVPD2026PowerMgmt": "F", "Wang2025TTSV": "D"}
SYM = {"\\checkmark": "✓", "$\\triangle$": "△", "---": "—"}


def main() -> int:
    t = TEX.read_text()
    i = t.index("\\label{tab:cmp}")
    tab = t[t.index("\\begin{tabular}", i):t.index("\\end{tabular}", i)]
    rows = [l.strip() for l in tab.split("\n")
            if "&" in l and not l.startswith("%")]
    hdr = rows[0]
    cols = [KEY.get(k, k) for k in re.findall(r"\\cite\{([^}]+)\}", hdr)] + ["G"]
    body, below = [], False
    for l in rows[1:]:
        if "\\midrule" in l:
            below = True
        cells = [c.strip() for c in l.replace("\\\\", "").split("&")]
        if len(cells) != len(cols) + 1:
            continue
        name = re.sub(r"\$([^$]*)\$", r"\1", cells[0])
        name = (name.replace("\\mathrm", "").replace("\\rho", "rho").replace("{", "")
                    .replace("}", "").replace("--", "–"))
        body.append((name, [SYM.get(c, c) for c in cells[1:]], below))

    sec = ["## Capability matrix", "",
           "Generated from the manuscript table by "
           "`scripts/phase0mr3c/sync_prior_comparison.py`. Do not edit by hand.", "",
           "Legend: **✓** modelled explicitly · **△** partial, assumed or reported as future "
           "work · **—** not included.", "",
           "| capability | " + " | ".join(f"[{c}]" for c in cols) + " |",
           "|---|" + ":--:|" * len(cols)]
    sec += [f"| {n} | " + " | ".join(v) + " |" for n, v, b in body if not b]
    if any(b for _, _, b in body):
        sec += ["", "Capabilities **[G] does not provide**:", "",
                "| capability | " + " | ".join(f"[{c}]" for c in cols) + " |",
                "|---|" + ":--:|" * len(cols)]
        sec += [f"| {n} | " + " | ".join(v) + " |" for n, v, b in body if b]

    md = MD.read_text()
    a = md.index("## Capability matrix")
    b = md.index("## Reproduction and testing")
    MD.write_text(md[:a] + "\n".join(sec) + "\n\n" + md[b:])
    print(f"synced {len(body)} capability rows over {len(cols)} columns -> "
          f"{MD.relative_to(R)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
