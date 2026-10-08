#!/usr/bin/env python3
"""Phase-0M-R3C --- bring the STANDALONE current-state audit to 0M-R3C."""
from __future__ import annotations
import csv, sys
from pathlib import Path
import yaml

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3c"
STAND = R / "results" / "ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.md"
CONTRACT = R / "configs" / "phase0mr3" / "semantic_contract.yaml"
DATE = "2026-09-21"
WORD = {22: "Twenty-two", 23: "Twenty-three"}


def main() -> int:
    gates = yaml.safe_load(CONTRACT.read_text())["meta"]["gates"]
    g = "0M-R3C"
    fp = {r["case"]: r for r in csv.DictReader((OUT / "final_pair_status.csv").open())}
    z1, z2 = fp["Z1"], fp["Z2"]
    d = float(z1["D_driver_final"])
    s = STAND.read_text()

    new_12 = "\n".join([
        f"## 1.2 What Phase {g} changed", "",
        "The last planned technical gate, and a paper-freeze decision.", "",
        "| question | answer |", "|---|---|",
        "| How many via levels does `ls_to_L` really need? | **One, not three (DEFECT "
        "#64).** Phase 0M-R3B counted three MATERIAL layers; `RDL_UM` is an interlayer "
        "REDISTRIBUTION layer, which is a conductor plane and therefore a capture land. "
        "Counting conductor planes gives one via level of 100 um |",
        "| Does that change the Phase-0M-R3B verdict? | **Yes.** Its finding that zero "
        "configurations satisfy both sourced bounds is WITHDRAWN. It also relocates the "
        "real problem: the binding net was `hs_to_cf`, crossing the whole 606 um low-side "
        "GaN tier at aspect ratio 5.05 |",
        "| Can the existing components be repartitioned? | **Yes, by a permutation.** "
        "`T1C_REORDERED` swaps gan_ls and cap_fly only. The 20.408 A switch node becomes "
        "an adjacent-tier RDL transition and the worst build-up aspect ratio falls from "
        "**5.05 to 0.83**, at identical component set, per-tier area and 1921 um stack |",
        "| Is it manufacturable? | **Not demonstrated.** Geometry closes at a "
        "source-bounded pitch; the microvia current allowable, the capture pad, a vendor "
        "design rule and two package clearances are OPEN. The verdict is "
        "**GEOMETRICALLY_REALIZABLE / PROCESS-CONDITIONAL**, never PROVEN_REALIZABLE |",
        f"| Does the ordering survive? | **Yes.** One ETM replay on a pair frozen before "
        f"solving: D_driver_final = **{d:.4f}** against the historical 1.1943, "
        f"**{100*(d-1.1943)/1.1943:+.2f} %**. ARCH_Z2 is "
        f"{float(z2['T_max_C'])-float(z1['T_max_C']):+.2f} K hotter and carries 16.3 % "
        f"less local fatigue-relevant inelastic response |",
        "", f"**Verdict B --- a process-conditional repartition exists and the final Z1/Z2 "
        f"response ordering survives.** No fundamental model contradiction was found, so "
        f"framework development stops here. The next action is manuscript freeze: see "
        f"`results/PAPER_FREEZE_DECISION.md`.",
    ])

    edits = [
        ("subtitle", 'as it exists after Phase 0M-R3B"', f'as it exists after Phase {g}"'),
        ("phase completed", f"| Phase completed | 0M-R3B, {DATE} |",
         f"| Phase completed | {g}, {DATE} |"),
        ("demote 0M-R3B summary", "## 1.2 What Phase 0M-R3B changed",
         new_12 + "\n\n\\newpage\n\n## 1.3 Superseded Phase-0M-R3B summary"),
        ("demote 0M-R3A summary", "## 1.3 Superseded Phase-0M-R3A summary",
         "## 1.4 Superseded Phase-0M-R3A summary"),
        ("demote 0M-R3 summary", "## 1.4 Superseded Phase-0M-R3 summary",
         "## 1.5 Superseded Phase-0M-R3 summary"),
        ("demote 0M-R2 summary", "## 1.5 Superseded Phase-0M-R2 summary",
         "## 1.6 Superseded Phase-0M-R2 summary"),
        ("precondition header", "| precondition | status after Phase 0M-R3B | evidence |",
         f"| precondition | status after Phase {g} | evidence |"),
    ]
    for desc, old, new in edits:
        if new in s and old not in s:
            print(f"  ok    {desc} (already current)"); continue
        n = s.count(old)
        if n != 1:
            print(f"  FAIL  {desc}: matched {n} times, expected 1"); return 1
        s = s.replace(old, new, 1); print(f"  ok    {desc}")
    STAND.write_text(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
