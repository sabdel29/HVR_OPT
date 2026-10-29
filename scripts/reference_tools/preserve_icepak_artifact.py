"""Preserve the executed Icepak cooling benchmark outside scratch (final-closure Part 30).

Copies, for every solved mesh level, the AEDT project file (about 50 kB; the solved
.aedtresults folders are tens to hundreds of MB of solver scratch and stay out) and the
boundary flow reports Icepak exported (fs_*.csv), plus the round-1 convergence-criteria
record. It writes research/final_closure/reference_artifacts/icepak/MANIFEST.json, which
holds each project's SHA256, its original scratch path, the mesh, boundary conditions and
reproduction command, and refuses to copy any file that names a licence server. The AEDT/
PyAEDT logs are never copied, because they carry licence-server details.

    python scripts/reference_tools/preserve_icepak_artifact.py
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

R = Path(__file__).resolve().parents[2]
SRC = Path.home() / "claude_scratch" / "aedt_work" / "icepak"
DST = R / "research" / "final_closure" / "reference_artifacts" / "icepak"
LEVELS = ("baseline", "baseline_x", "fine", "fine_x")
LICENCE = re.compile(rb"licen[cs]e.?server|lmgrd|ansyslmd|\b\d{4,5}@[A-Za-z0-9.-]+", re.I)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def safe_copy(src, dst):
    data = Path(src).read_bytes()
    if LICENCE.search(data):
        raise SystemExit(f"{src} names a licence server; not copied")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    return {"file": str(dst.relative_to(R)), "sha256": sha(dst), "bytes": len(data),
            "source": str(src)}


def main():
    ref = json.loads((R / "research/final_closure/reference_cooling_icepak.json").read_text())
    man = {"study": "matched conjugate-CFD benchmark of the production cold-plate correlation",
           "tool": "Ansys Electronics Desktop 2026 R1 Icepak (AnsProductVersion 26.1), PyAEDT",
           "result_json": "research/final_closure/reference_cooling_icepak.json",
           "generator": "scripts/reference_tools/icepak_cooling_benchmark.py",
           "reproduce": ("export PATH=/home/beams0/MGHARIB/envs/etm/bin:$PATH; python "
                         "scripts/reference_tools/icepak_cooling_benchmark.py driver baseline "
                         "fine baseline_x fine_x   (AEDT 2026 R1 with an Icepak licence; "
                         "writes under $AEDT_WORK, default ~/claude_scratch/aedt_work)"),
           "cfd_problem": ref.get("cfd_problem"), "inputs": ref.get("inputs"),
           "evidence": "presentation/prelim_hvr/tool_evidence/cooling_icepak/",
           "not_preserved": ("the solved .aedtresults folders (solver scratch, 22-151 MB each) "
                             "and the AEDT/PyAEDT logs (they carry licence-server details)"),
           "levels": {}}
    for lv in LEVELS:
        d = SRC / lv
        proj = d / f"cooling_{lv}.aedt"
        if not proj.exists():
            raise SystemExit(f"missing {proj}")
        rec = {"project": safe_copy(proj, DST / lv / proj.name),
               "flow_reports": [safe_copy(c, DST / lv / c.name)
                                for c in sorted(d.glob("fs_*.csv"))],
               "cells": (ref["levels"].get(lv) or {}).get("cells"),
               "solved": (ref["levels"].get(lv) or {}).get("solved"),
               "dT_base_mean_K": (ref["levels"].get(lv) or {}).get("dT_base_mean_K"),
               "solve_wall_s": (ref["levels"].get(lv) or {}).get("solve_wall_s")}
        man["levels"][lv] = rec
    r1 = SRC / "round1_crit1e-5" / "reference_cooling_icepak_round1.json"
    if r1.exists():
        man["round1_convergence_criteria"] = safe_copy(r1, DST / r1.name)
    (DST / "MANIFEST.json").write_text(json.dumps(man, indent=1) + "\n")
    (DST / "README.md").write_text(
        "# Icepak cooling benchmark: preserved project files\n\n"
        "These are the AEDT 2026 R1 Icepak projects behind "
        "`research/final_closure/reference_cooling_icepak.json`: one microchannel "
        "half-pitch, steady laminar conjugate CFD, four mesh levels. Each project's SHA256 "
        "and original path are in `MANIFEST.json`, together with the boundary conditions "
        "and the reproduction command.\n\n"
        "Kept here:\n"
        "- the `.aedt` project file of every level;\n"
        "- Icepak's own inlet/outlet flow reports (`fs_*.csv`);\n"
        "- the round-1 convergence-criteria record.\n\n"
        "Not kept:\n"
        "- the solved `.aedtresults` folders, which are solver scratch. Re-solving a "
        "project regenerates them.\n"
        "- the AEDT/PyAEDT logs, which carry licence-server details.\n\n"
        "Reproduce:\n\n    " + man["reproduce"] + "\n")
    print("preserved", len(man["levels"]), "levels into", DST.relative_to(R))


if __name__ == "__main__":
    main()
