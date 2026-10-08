#!/usr/bin/env python3
"""Phase-0M-R3B --- the canonical report rebuild chain.

Supersedes scripts/phase0mr3a/rebuild_reports.py. Same reasoning: each phase's builder
hard-codes its own headings and once-only inserts, later phases correct them from outside,
so the CHAIN is the unit of rebuild. Run this, not the individual builders.
"""
from __future__ import annotations
import subprocess, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]

CHAIN = [
    "scripts/phase0mr3/build_report_0mr3.py",       # Phase 0M-R3 chapter
    "scripts/phase0mr3a/build_report_0mr3a.py",     # demotes it, 0M-R3A chapter, status
    "scripts/phase0mr3a/update_standalone.py",      # standalone, 0M-R3A state
    "scripts/phase0mr3b/build_report_0mr3b.py",     # 0M-R3B chapter (skipped if absent)
    "scripts/phase0mr3b/update_standalone_0mr3b.py",
    "scripts/phase0mr3c/build_report_0mr3c.py",     # 0M-R3C chapter
    "scripts/phase0mr3c/update_standalone_0mr3c.py",
    "scripts/phase0mr3b/report_state_fix.py",       # provenance + terminology, from outside
    "scripts/phase0dr/build_pdf.py",                # historical PDF + verification
    "scripts/phase0l/build_audit_report.py",        # standalone PDF + verification
]


def main() -> int:
    for rel in CHAIN:
        if not (R / rel).is_file():
            print(f"[skip] {rel} (not present yet)")
            continue
        p = subprocess.run([sys.executable, str(R / rel)], cwd=R,
                           capture_output=True, text=True)
        print(f"[{'ok  ' if p.returncode == 0 else 'FAIL'}] {rel}")
        if p.returncode:
            print(p.stdout[-2500:]); print(p.stderr[-2500:])
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
