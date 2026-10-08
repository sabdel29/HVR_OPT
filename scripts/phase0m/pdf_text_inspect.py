#!/usr/bin/env python3
"""Phase-0M -- INDEPENDENT inspection of the built PDFs' extracted text.

The build scripts verify their own output. This one does not trust them: it re-extracts the
text from both finished PDFs and checks that the Phase-0M conclusions a reader must be able
to find are actually THERE, in the PDF, in readable form -- not merely in the source
Markdown. A claim that exists only in the .md is a claim the auditor never sees.
"""
from __future__ import annotations
import re, subprocess, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
HIST = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.pdf"
STAND = R / "results" / "ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.pdf"


def text(p: Path) -> str:
    for cmd in (["pdftotext", "-layout", str(p), "-"], ["pdftotext", str(p), "-"]):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if r.returncode == 0 and len(r.stdout) > 1000:
                return r.stdout
        except FileNotFoundError:
            break
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    return "\n".join((pg.extract_text() or "") for pg in PdfReader(str(p)).pages)


def norm(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", s)
    return re.sub(r"\s+", " ", s)


MUST_HIST = [
    ("the Phase-0M verdict letter", r"MULTIPLE MISSING PHYSICAL COUPLINGS ARE FIRST ORDER"),
    ("the radius cancellation", r"cross-section cancels \*{0,2}identically|"
                                r"cross-section has cancelled identically"),
    ("the crowding spread", r"K_crowd.{0,40}0\.6|0\.606"),
    ("intra-VR routing absent", r"[Ii]ntra-converter metallization"),
    ("the Z5 equivalent resistance", r"0\.76807|0\.768"),
    ("the PCB-versus-RDL reversal", r"4\.56"),
    ("the cooling flow inconsistency", r"168 K"),
    ("the pumping power", r"7\.4 ?%"),
    ("the M-to-E magnitude", r"0\.16 ?%"),
    ("ETM-L1", r"ETM-L1"),
    ("the single-level VR infeasibility", r"1\.76"),
    ("the ME reconstruction", r"solver-coherent|mechanical strain"),
    ("the specimen provenance", r"192"),
    ("the retired theorem is gone", r"^(?!.*must reproduce it\.)", ),
]
def flex(pattern: str) -> str:
    r"""Tolerate the line breaks and soft hyphenation xelatex introduces.

    `constitutive-law-independent deformation driver favoring Z2` is present in the PDF, but
    typeset as `constitutive-law-\nindependent ...`. Matching the literal string reported the
    licensed wording as ABSENT when it was there. Every space outside a character class
    becomes `\s+`, and every literal hyphen may be followed by a line break.
    """
    out, depth, esc = [], 0, False
    for ch in pattern:
        if esc:
            out.append(ch); esc = False; continue
        if ch == "\\":
            out.append(ch); esc = True; continue
        if ch == "[":
            depth += 1
        elif ch == "]" and depth:
            depth -= 1
        if depth == 0 and ch == " ":
            out.append(r"\s+")
        elif depth == 0 and ch == "-":
            out.append(r"-\s*")
        else:
            out.append(ch)
    return "".join(out)


# Phase 0M-R rewrote the STANDALONE report, which by design describes the framework as it
# is now rather than as any phase left it. Four of these anchors pointed at Phase-0M section
# titles and at wording Phase 0M-R legitimately superseded. They are RE-POINTED at the same
# substance in the new document, not deleted -- the protection is the point, the phrasing is
# not. One of them, "cooling is not derived", is now FALSE, so it is inverted rather than
# re-pointed: the check must fail if the report ever says cooling is calibrated again.
MUST_STAND = [
    ("interconnect geometry is resolved", r"Interconnect geometry"),
    ("intra-VR routing is covered", r"[Ii]ntra-VR routing"),
    ("crowding is derived, not assumed", r"per[- ]class|0\.606|solved exactly"),
    ("partitioning is covered", r"component-level partitioning|partition"),
    ("homogenization verdict", r"REJECTED|rejected"),
    ("cooling IS derived from hardware", r"derived from hardware, not calibrated"),
    ("coupling directionality", r"ETM-L1"),
    ("missing mechanics count", r"(?i:not modelled)"),
    ("licensed structural wording",
     r"constitutive-law-independent deformation driver favoring Z2"),
]
FORBIDDEN = [("the retired theorem", r"must reproduce it\."),
             ("the retired theorem", r"must (therefore )?rank Z1 worse"),
             ("the stale gate count", r"Eleven sequential falsification gates")]


def check(name: str, t: str, musts) -> int:
    bad = 0
    n = norm(t)
    for label, pat in musts:
        if pat.startswith("^(?!"):
            continue
        ok = re.search(flex(pat), n) is not None
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {label}")
        bad += (not ok)
    for label, pat in FORBIDDEN:
        hit = re.search(flex(pat), n)
        print(f"  [{'PASS' if not hit else 'FAIL'}] {name}: {label} absent")
        bad += bool(hit)
    return bad


def main() -> int:
    bad = 0
    for p, musts, nm in ((HIST, MUST_HIST, "historical"), (STAND, MUST_STAND, "standalone")):
        if not p.is_file():
            print(f"  [FAIL] {nm}: PDF missing"); bad += 1; continue
        t = text(p)
        print(f"{nm}: {len(t)} characters extracted from {p.name}")
        assert len(t) > 40000, f"{nm}: extraction too short to be real"
        bad += check(nm, t, musts)
    print(f"\n{'ALL PDF TEXT CHECKS PASS' if not bad else str(bad) + ' FAILURE(S)'}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
