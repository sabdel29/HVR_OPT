#!/usr/bin/env python3
"""Phase-0M-R3B Section 1 --- current-state fixes applied from OUTSIDE prior builders.

Phase 0M-R3's repair_report.py writes the provenance rows once, guarded by a regex that
stops matching after the first run, so the table froze at "0M-R3, 2026-09-19" while the
report's own chapter said a later phase was authoritative. Same once-only-insert shape as
the Architecture Comparison note.

The rows are rewritten to whatever the CURRENT gate is, not matched against the old text:
pinning the old value is exactly how the row went stale.
"""
from __future__ import annotations
import re, sys
from pathlib import Path

import yaml

R = Path(__file__).resolve().parents[2]
HIST = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
STAND = R / "results" / "ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.md"
CONTRACT = R / "configs" / "phase0mr3" / "semantic_contract.yaml"
GEN_DATE = "2026-09-21"
BASELINE_DATE = "2026-09-08"


def gate() -> str:
    return yaml.safe_load(CONTRACT.read_text())["meta"]["gates"][-1]


def rewrite_gate_sentence(s: str, gates: list[str]) -> tuple[str, str]:
    """Single owner for the falsification-gate roll, in both reports.

    Two phase updaters previously each rewrote this sentence from their own hard-coded
    word and list, and they fought as soon as a third gate landed. It is derived here and
    nowhere else.
    """
    import importlib.util as _ilu
    _sp = _ilu.spec_from_file_location(
        "_sa", R / "scripts/phase0mr3/semantic_audit.py")
    _sa = _ilu.module_from_spec(_sp); _sp.loader.exec_module(_sa)
    want = f"{_sa.NUMWORD[len(gates)]} sequential falsification gates ({', '.join(gates)})"
    pat = re.compile(r"[\w-]+ sequential falsification gates\s*\([^)]*\)", re.S)
    m = pat.search(s)
    if not m:
        return s, "FAIL  no gate sentence"
    if re.sub(r"\s+", " ", m.group(0)) == want:
        return s, "ok    gate sentence (already current)"
    return pat.sub(lambda _m: want, s, count=1), \
        f"ok    gate sentence -> {_sa.NUMWORD[len(gates)]}, {len(gates)} gates"


def rewrite_row(s: str, label: str, value: str) -> tuple[str, str]:
    pat = re.compile(rf"(\|\s*{re.escape(label)}\s*\|)([^|]*)(\|)")
    m = pat.search(s)
    if not m:
        return s, f"FAIL  no '{label}' row"
    if m.group(2).strip() == value:
        return s, f"ok    {label} (already current)"
    was = m.group(2).strip()
    s = pat.sub(lambda _m: f"{_m.group(1)} {value} {_m.group(3)}", s, count=1)
    return s, f"ok    {label}: {was} -> {value}"


STAND_EDITS = [
    # DEFECT #60: the weight is dPEEQ * V, not a damage law.
    ("14. solder model: weighting named for what it is",
     "while the joint's damage-weighted median stress is about "
     "**82 MPa** and **99.8 % of the damage is generated outside the fitted window**.",
     "while the joint's inelastic-strain-weighted median stress is about "
     "**82 MPa** and **99.8 % of the accumulated inelastic strain is generated outside "
     "the fitted window**. The weight is the solver's own dPEEQ times element volume; "
     "no damage law is applied, so this is a RESPONSE weighting."),
]


def apply(path: Path, edits) -> int:
    s = path.read_text()
    for desc, old, new in edits:
        if new in s and old not in s:
            print(f"  ok    {desc} (already current)")
            continue
        n = s.count(old)
        if n != 1:
            print(f"  FAIL  {desc}: matched {n} times, expected 1")
            return 1
        s = s.replace(old, new, 1)
        print(f"  ok    {desc}")
    path.write_text(s)
    return 0


def main() -> int:
    g = gate()
    print(f"current gate {g}")
    s, bad = HIST.read_text(), 0
    for label, value in (("Phase completed", f"{g}, {GEN_DATE}"),
                         ("Report generated", GEN_DATE),
                         ("Repository baseline", BASELINE_DATE)):
        s, msg = rewrite_row(s, label, value)
        print("  " + msg)
        bad += msg.startswith("FAIL")
    gates = yaml.safe_load(CONTRACT.read_text())["meta"]["gates"]
    s, msg = rewrite_gate_sentence(s, gates)
    print("  " + msg); bad += msg.startswith("FAIL")
    HIST.write_text(s)
    t = STAND.read_text()
    t, msg = rewrite_gate_sentence(t, gates)
    print("  standalone " + msg); bad += msg.startswith("FAIL")
    STAND.write_text(t)
    return 1 if bad else apply(STAND, STAND_EDITS)


if __name__ == "__main__":
    sys.exit(main())
