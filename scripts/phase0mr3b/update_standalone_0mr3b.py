#!/usr/bin/env python3
"""Phase-0M-R3B --- bring the STANDALONE current-state audit to 0M-R3B.

Runs after scripts/phase0mr3a/update_standalone.py and applies this phase's delta as
asserted substitutions, so an upstream rewording fails the build rather than leaving stale
text in the document whose whole job is to be current.
"""
from __future__ import annotations
import csv, sys
from pathlib import Path

import yaml

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3b"
STAND = R / "results" / "ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.md"
CONTRACT = R / "configs" / "phase0mr3" / "semantic_contract.yaml"
DATE = "2026-09-21"


def rd(n):
    return list(csv.DictReader((OUT / n).open()))


def main() -> int:
    gates = yaml.safe_load(CONTRACT.read_text())["meta"]["gates"]
    # each phase's updater writes ITS OWN phase; the latest one in the chain
    # wins, and the gate sentence has a single owner in report_state_fix.py
    g = "0M-R3B"
    feas = rd("ls_to_L_feasibility.csv")
    dp = [r for r in feas if float(r["pitch_um"]) == 70.0
          and r["stack"] == "fully_stacked" and float(r["d_um"]) == 40.0][0]
    s = STAND.read_text()

    new_12 = "\n".join([
        f"## 1.2 What Phase {g} changed", "",
        "Four goals: find out what `ls_to_L` physically is, source the package clearances, "
        "source a real TSV tolerance, and clear the remaining report-state defects.", "",
        "| question | answer |", "|---|---|",
        "| What is `ls_to_L`? | **Not a 673 um structure.** That span was measured tier "
        "mid-plane to tier mid-plane, through 303 um of GaN die body and 250 um of "
        "inductor body. The build-up a via chain crosses is **120 um** in three layers: "
        "RDL 10 + flying-capacitor layer 100 + RDL 10 (DEFECT #62) |",
        "| Single via or a chain? | **A chain** --- one microvia per build-up layer, with "
        "a capture land between each pair. Three levels |",
        "| Is the technology sourced? | **The class is**: stacked build-up microvias "
        "through embedded-component substrate power layers. Two primary sources obtained "
        "in full text. Five of twelve geometric parameters are still OPEN |",
        "| Is r = 20 um at 70 um pitch legal? | **No.** Ostmann 2008 gives min. 150 um I/O "
        "pad pitch in production, 100 um at prototype level, and states that below 100 um "
        "vialess methods are used instead. Cauwe 2023 calls three stacked microvia levels "
        "a reliability risk; this gap needs three |",
        f"| Does routing still pass? | **No.** The vias available were counted over the "
        f"1.80 mm2 die footprint; the binding number is the 1.61 mm2 left free in the "
        f"flying-capacitor layer (DEFECT #63). At that area the design point gives "
        f"**{float(dp['routing_ratio']):.4f} > 1** |",
        "| Were the clearances sourced? | **One of three** moves to SOURCE_BOUNDED and "
        "lands inside its existing bound, so no corner moves. Two remain OPEN --- and they "
        "are no longer what blocks first |",
        "| Is the 32 um TSV margin process-qualified? | **No.** No manufacturing tolerance "
        "could be sourced. 32 um absorbs 3.23 % symmetric tolerance before AR = 10 is "
        "violated; it is **parametrically margined, not process-qualified** |",
        "", f"**Verdict D --- the physical `ls_to_L` topology, evaluated against sourced "
        f"substrate-via rules, makes the frozen Z1/Z2 pair NOT_REALIZABLE under the current "
        f"component topology.** Both architectures share one converter cell, so it applies "
        f"to both. The deciding mechanical ordering is untouched and is not what this gate "
        f"tested.",
    ])

    edits = [
        ("subtitle", 'as it exists after Phase 0M-R3A"', f'as it exists after Phase {g}"'),
        ("phase completed", f"| Phase completed | 0M-R3A, {DATE} |",
         f"| Phase completed | {g}, {DATE} |"),
        ("demote 0M-R3A summary",
         "## 1.2 What Phase 0M-R3A changed",
         new_12 + "\n\n\\newpage\n\n## 1.3 Superseded Phase-0M-R3A summary"),
        ("demote 0M-R3 summary", "## 1.3 Superseded Phase-0M-R3 summary",
         "## 1.4 Superseded Phase-0M-R3 summary"),
        ("demote 0M-R2 summary", "## 1.4 Superseded Phase-0M-R2 summary",
         "## 1.5 Superseded Phase-0M-R2 summary"),
        ("precondition header",
         "| precondition | status after Phase 0M-R3A | evidence |",
         f"| precondition | status after Phase {g} | evidence |"),
    ]
    for desc, old, new in edits:
        if new in s and old not in s:
            print(f"  ok    {desc} (already current)"); continue
        n = s.count(old)
        if n != 1:
            print(f"  FAIL  {desc}: matched {n} times, expected 1"); return 1
        s = s.replace(old, new, 1)
        print(f"  ok    {desc}")
    STAND.write_text(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
