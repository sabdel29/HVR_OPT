#!/usr/bin/env python3
"""Phase-0M-R3A --- the canonical report rebuild chain.

Each phase's builder owns a sentinel block and hard-codes its own chapter heading,
including the "(current authoritative)" marker. A later phase demotes that heading from
OUTSIDE the block, so running an older builder on its own silently restores a superseded
chapter to current. That is not a defect in either builder; it is what makes the chain the
unit of rebuild rather than any single script.

Run this, not the individual builders.
"""
from __future__ import annotations
import subprocess, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]

CHAIN = [
    "scripts/phase0mr3/build_report_0mr3.py",     # Phase 0M-R3 chapter
    "scripts/phase0mr3a/build_report_0mr3a.py",   # demotes it, adds 0M-R3A, status block
    "scripts/phase0mr3a/update_standalone.py",    # standalone current-state audit
    "scripts/phase0dr/build_pdf.py",              # historical PDF + its verification
    "scripts/phase0l/build_audit_report.py",      # standalone PDF + its verification
]

# The PDF builders repair the Markdown in place (a table header on the line after text is
# not parsed as a table), so they must run AFTER the content builders and their repair is
# part of the delivered file. Running the chain again after a PDF build and diffing the
# Markdown is what makes that visible rather than a silent race between two writers.


def run(rel: str) -> int:
    p = subprocess.run([sys.executable, str(R / rel)], cwd=R,
                       capture_output=True, text=True)
    tag = "ok  " if p.returncode == 0 else "FAIL"
    print(f"[{tag}] {rel}")
    if p.returncode:
        print(p.stdout[-2500:]); print(p.stderr[-2500:])
    return p.returncode


def main() -> int:
    for rel in CHAIN:
        if run(rel):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
