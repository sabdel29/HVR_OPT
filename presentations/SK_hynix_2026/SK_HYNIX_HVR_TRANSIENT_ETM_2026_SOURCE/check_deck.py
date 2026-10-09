#!/usr/bin/env python3
"""Permanent guard on the built deck.

Scans every slide's visible text AND its presenter notes for claims that were
withdrawn or were never licensed, and asserts the frozen values are the current
ones. Run after every build. Exits non-zero on any violation.

Each pattern below is the REAL offending text, not a paraphrase, so the check
fails if that exact wrong claim ever reaches a slide.
"""
from __future__ import annotations
import re, sys
from pathlib import Path
from pptx import Presentation
import sources as S

DECK = Path(__file__).resolve().parent.parent / "SK_HYNIX_HVR_TRANSIENT_ETM_2026.pptx"

# (regex, why it is forbidden).  Case-insensitive.
FORBIDDEN = [
    (r"\b1\.3225\b",            "superseded D_u (pre-R3 ladder)"),
    (r"\b1\.2552\b",            "superseded D_u (pre-R3 ladder)"),
    (r"\b1\.1942\b",            "superseded D_u (pre-R3C)"),
    (r"\b1\.1943\b",            "superseded D_u (pre-R3C)"),
    (r"\b1\.558\b",             "withdrawn relative-life ratio"),
    (r"longer life",            "no life claim is licensed"),
    (r"less damage",            "d_eps is a response, not damage"),
    (r"more damage",            "d_eps is a response, not damage"),
    (r"mechanically safe",      "no mechanical pass/fail is licensed"),
    (r"fatigue life",           "no fatigue model was run"),
    (r"cycles to failure",      "no life model was run"),
    (r"same via geometry",      "h_sub and the TSV path differ between Z1 and Z2"),
    (r"identical via field",    "the via field is NOT identical"),
    (r"experimentally validated", "cross-solver verification only"),
    (r"validated against measurement", "no hardware was measured"),
    (r"SK hynix (currently )?uses", "no claim about what SK hynix does"),
    (r"you should (build|adopt|use)", "no product recommendation"),
]
# PROVEN_REALIZABLE may appear ONLY in its negated form.
PROVEN_OK = re.compile(r"PROVEN_REALIZABLE is not", re.I)

# values that must be present somewhere, so a stale rebuild is caught
REQUIRED = [f"{S.D_U:.4f}", f"{S.D_EPS:.4f}", f"{S.AR['repartition_C1']:.3f}",
            f"{S.TRANSIENT['ratio_400']:.1f}", f"{S.H_TSV_UM['Z1']:.0f}"]


# A forbidden phrase is allowed when it is being DENIED. Negation is detected in
# the sentence containing the match, so "no fatigue life" passes and
# "Z2 has 18.4 % longer life" does not.
NEG = re.compile(r"\b(no|not|never|cannot|can't|neither|nor|without|refus\w+|"
                 r"n't|Not claimed|is not|does not|do not|did not|am not|"
                 r"must not|would not|non-)\b", re.I)
SENT = re.compile(r"[^.;:!?\n]*")


def sentence(text, pos):
    """The clause containing offset `pos`."""
    lo = max(text.rfind(".", 0, pos), text.rfind(";", 0, pos),
             text.rfind("\n", 0, pos), text.rfind("?", 0, pos),
             text.rfind("!", 0, pos)) + 1
    m = SENT.match(text, pos)
    hi = m.end() if m else len(text)
    return text[lo:hi]


def harvest(path):
    prs = Presentation(path)
    out = []
    for i, s in enumerate(prs.slides, 1):
        txt = []
        for sh in s.shapes:
            if sh.has_text_frame:
                txt.append(sh.text_frame.text)
            if sh.has_table:
                tbl = sh.table
                hdr = [c.text.strip() for c in tbl.rows[0].cells]
                for ri, r in enumerate(tbl.rows):
                    for ci, c in enumerate(r.cells):
                        # prefix the column header so a "Not claimed" column
                        # reads as a denial rather than an assertion
                        pre = (hdr[ci] + ": ") if ri and ci < len(hdr) else ""
                        txt.append(pre + c.text)
        note = s.notes_slide.notes_text_frame.text if s.has_notes_slide else ""
        out.append((i, "\n".join(txt), note))
    return out


def run(path, verbose=True):
    bad = []
    slides = harvest(path)
    allslide = []
    for i, body, note in slides:
        allslide.append(body + "\n" + note)
        for where, text in (("slide", body), ("notes", note)):
            for pat, why in FORBIDDEN:
                for m in re.finditer(pat, text, re.I):
                    clause = sentence(text, m.start())
                    if NEG.search(clause):
                        continue                      # the claim is being denied
                    bad.append(f"slide {i} [{where}]: {m.group(0)!r} "
                               f"in {clause.strip()[:90]!r} — {why}")
            for m in re.finditer(r"PROVEN_REALIZABLE", text, re.I):
                seg = text[m.start():m.start() + 40]
                if not PROVEN_OK.match(seg):
                    bad.append(f"slide {i} [{where}]: bare PROVEN_REALIZABLE")
    whole = "\n".join(allslide)
    for v in REQUIRED:
        if v not in whole:
            bad.append(f"MISSING required current value {v!r} — stale build?")
    # every main slide carries a complete notes contract
    for i, _, note in slides[:33]:
        if not re.match(r"^\[~\d+ s\]", note):
            bad.append(f"slide {i}: notes missing [~N s]")
        if "If asked" not in note:
            bad.append(f"slide {i}: notes missing 'If asked:'")
        if i != 33 and "TRANSITION" not in note:
            bad.append(f"slide {i}: notes missing TRANSITION")
    if verbose:
        if bad:
            print(f"FAIL — {len(bad)} violation(s)")
            for b in bad:
                print("  " + b)
        else:
            print(f"PASS — {len(slides)} slides clean "
                  f"({len(FORBIDDEN)} forbidden patterns, "
                  f"{len(REQUIRED)} required values)")
    return bad


if __name__ == "__main__":
    sys.exit(1 if run(DECK) else 0)
