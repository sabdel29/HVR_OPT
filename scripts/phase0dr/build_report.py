#!/usr/bin/env python3
"""Build results/ETM_DVPD_FULL_TECHNICAL_REPORT.{md,pdf}.

Tables are generated FROM the source artifacts, never retyped, so the document cannot drift
from the data. Every table carries its source filename.
"""
from __future__ import annotations

import csv, json, subprocess, sys, textwrap
from datetime import date
from pathlib import Path

R = Path(__file__).resolve().parents[2]
RES = R / "results"
OUT_MD = RES / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
OUT_PDF = RES / "ETM_DVPD_FULL_TECHNICAL_REPORT.pdf"
FIGS: list[tuple[str, str, str]] = []          # (path, caption, source phase)


def rows(p: Path) -> list[dict]:
    with p.open() as fh:
        return list(csv.DictReader(fh))


def js(p: Path):
    return json.loads(p.read_text())


def num(v, nd=3):
    try:
        f = float(v)
        return f"{f:.{nd}f}"
    except (TypeError, ValueError):
        return str(v)


def table(hdr: list[str], body: list[list], align: str | None = None,
          src: str | None = None) -> str:
    a = align or ("l" + "r" * (len(hdr) - 1))
    sep = "|" + "|".join({"l": ":--", "r": "--:", "c": ":-:"}[c] for c in a) + "|"
    out = ["| " + " | ".join(str(h) for h in hdr) + " |", sep]
    for r_ in body:
        out.append("| " + " | ".join(str(c) for c in r_) + " |")
    if src:
        out.append("")
        out.append(f"*Source: `{src}`*")
    return "\n".join(out)


def fig(path: Path, caption: str, phase: str, width: str = "95%") -> str:
    rel = path.relative_to(RES.parent) if path.is_relative_to(RES.parent) else path
    FIGS.append((str(path), caption, phase))
    n = len(FIGS)
    return (f"![**Figure {n}.** {caption} *(Produced in {phase}; data: "
            f"`{rel}`)*]({path}){{width={width}}}\n")


def sec_cover() -> str:
    ccx = subprocess.run(["ccx", "-v"], capture_output=True, text=True).stdout.strip() or "CalculiX 2.23"
    commit = subprocess.run(["git", "-C", str(R / "Scalable_Integrated_VR"), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True).stdout.strip() or "n/a"
    return textwrap.dedent(f"""\
    ---
    title: "Electrothermal--Mechanical Co-Design of Distributed Vertical Power Delivery: Model Development, Falsification Gates, and Coupled Architecture Results"
    author: "HVR_Journal_System_Level / ETM-DVPD project --- HiPerCAS Lab, University of Illinois Chicago"
    date: "{date.today().isoformat()}"
    geometry: margin=2.2cm
    fontsize: 10pt
    colorlinks: true
    linkcolor: NavyBlue
    urlcolor: NavyBlue
    toc: true
    toc-depth: 2
    numbersections: true
    ---

    \\newpage

    # Provenance

    | Item | Value |
    |:--|:--|
    | Project | HVR_Journal_System_Level / ETM-DVPD |
    | Repository root | `{R}` |
    | Converter-model repo commit | `{commit}` (`Scalable_Integrated_VR`) |
    | Report date | {date.today().isoformat()} |
    | Structural / thermal solver | {ccx.splitlines()[0] if ccx else 'CalculiX 2.23'} (C3D8I, direct SPOOLES) |
    | Independent FE cross-check | MOOSE `heat_transfer-opt`, build 09515f92aa |
    | Full-wave EM solver available | PALACE (build at `/home/beams0/LPOPRYHO/projects/palace`) |
    | Commercial EM/thermal | ANSYS AEDT v261 installed; **licence unavailable** (see S16) |
    | Mesh generation | gmsh 4.15.2 |
    | Python | {sys.version.split()[0]} |
    | Test suite | see S17 |

    **How to read this document.** Every table is generated programmatically from the source
    artifact named beneath it. No numerical result in this report was retyped by hand.
    Sections are ordered by project phase; **Section 8 (Phase 0D-R) supersedes Section 7
    (Phase 0D) wherever they disagree**, and every such disagreement is called out explicitly.

    \\newpage
    """)
