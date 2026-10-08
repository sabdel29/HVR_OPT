#!/usr/bin/env python3
"""Phase-0M-R3B --- advance every representation of current state, together.

DEFECT #57 was five copies of current state advanced at different times. They are all
advanced here in one pass, and the gate list is advanced in the two configs that carry it.
"""
from __future__ import annotations
import re, sys
from pathlib import Path

import yaml

R = Path(__file__).resolve().parents[2]
ST = R / "results" / "CURRENT_SCIENTIFIC_STATUS.yaml"
SEM = R / "configs" / "phase0mr3" / "semantic_contract.yaml"
CLM = R / "configs" / "phase0mr2" / "current_state_claims.yaml"
GATE = "0M-R3B"
DATE = "2026-09-21"


def sub_once(s: str, old: str, new: str, what: str) -> str:
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"FAIL {what}: matched {n} times, expected 1")
    print(f"  ok  {what}")
    return s.replace(old, new, 1)


def main() -> int:
    # ---- gate lists ------------------------------------------------------------------
    for p, old_t, new_t in ((SEM, "0M-R3, 0M-R3A]", f"0M-R3, 0M-R3A, {GATE}]"),
                            (CLM, "    - 0M-R3A\n", f"    - 0M-R3A\n    - {GATE}\n")):
        s = p.read_text()
        if GATE in s:
            print(f"  ok  {p.name} gate list already advanced"); continue
        s = sub_once(s, old_t, new_t, f"{p.name} gate list")
        p.write_text(s)
    s = SEM.read_text()
    s = sub_once(s, 'current_authoritative_phase: "0M-R3A"',
                 f'current_authoritative_phase: "{GATE}"',
                 "semantic contract authoritative phase")
    SEM.write_text(s)
    s = CLM.read_text()
    s = sub_once(s, 'current_authoritative_phase: "0M-R3A"',
                 f'current_authoritative_phase: "{GATE}"', "0M-R2 claims authoritative phase")
    s = sub_once(s, '    current_wording: "Twenty-one sequential falsification gates"',
                 '    current_wording: "Twenty-two sequential falsification gates"',
                 "0M-R2 claims gate wording")
    s = sub_once(s, '    historical_wording: "Nineteen sequential falsification gates"',
                 '    historical_wording: "Twenty-one sequential falsification gates"',
                 "0M-R2 claims historical wording")
    s = sub_once(s, '      - "# Phase 0M-R3 --- Realizable-Template Repair, Cooling '
                 'Validation and Final Current-State Closure (current authoritative)"',
                 '      - "# Phase 0M-R3 --- Realizable-Template Repair, Cooling '
                 'Validation and Final Current-State Closure (current authoritative)"\n'
                 '      - "# Phase 0M-R3A --- Final State, Via-Technology and TSV-Margin '
                 'Closure (current authoritative)"',
                 "0M-R2 claims stale authority wording")
    CLM.write_text(s)

    # ---- the authoritative status ----------------------------------------------------
    s = ST.read_text()
    s = sub_once(s, 'current_phase: "0M-R3A"', f'current_phase: "{GATE}"',
                 "meta.current_phase")
    s = sub_once(s, '    state: "0M-R3A complete"', f'    state: "{GATE} complete"',
                 "contract current_phase")
    s = sub_once(s, '    evidence: "results/phase0mr3a/PHASE0MR3A_FINAL_CLOSURE.md"',
                 '    evidence: "results/phase0mr3b/'
                 'PHASE0MR3B_SUBSTRATE_VIA_AND_PACKAGE_RULE_CLOSURE.md"',
                 "contract current_phase evidence")
    ST.write_text(s)
    d = yaml.safe_load(ST.read_text())
    print("\nYAML parses. current_phase =", d["meta"]["current_phase"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
