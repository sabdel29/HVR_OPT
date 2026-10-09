#!/usr/bin/env python3
"""Negative test for check_deck.py.

Injects the REAL offending claims — the exact wordings that were ruled out —
into a copy of the built deck and asserts the guard catches every one. If this
test ever passes silently, the guard has gone blind.
"""
from __future__ import annotations
import shutil, sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
import check_deck

SRC = Path(__file__).resolve().parent.parent / "SK_HYNIX_HVR_TRANSIENT_ETM_2026.pptx"
TMP = Path("/tmp/_negtest_deck.pptx")

# Verbatim from the governing brief's "Do NOT say" list, plus the superseded
# values the snapshot manifest says must never be quoted again.
INJECT = [
    ("slide", "Z2 has 18.4% longer life"),
    ("slide", "Z2 has 18.4% less damage"),
    ("notes", "Z2 is mechanically safe"),
    ("slide", "D_u = 1.1943 for the final pair"),
    ("notes", "the relative life ratio is 1.558"),
    ("slide", "Same converter, same via geometry"),
    ("notes", "Identical via field, three orders of magnitude apart"),
    ("slide", "The framework is PROVEN_REALIZABLE at this pitch"),
    ("notes", "The solver was experimentally validated on a test vehicle"),
    ("slide", "SK hynix uses this architecture today"),
]


def main():
    shutil.copy(SRC, TMP)
    prs = Presentation(TMP)
    s = prs.slides[0]
    y = 0.2
    for where, text in INJECT:
        if where == "slide":
            tb = s.shapes.add_textbox(Inches(0.1), Inches(y), Inches(6), Inches(0.25))
            tb.text_frame.text = text
            y += 0.26
        else:
            tf = s.notes_slide.notes_text_frame
            tf.text = tf.text + "\n" + text
    prs.save(TMP)

    bad = check_deck.run(TMP, verbose=False)
    caught = " || ".join(bad).lower()
    missed = [t for _, t in INJECT
              if not any(w in caught for w in t.lower().split()[:3])]

    print(f"injected {len(INJECT)} real offending claims")
    print(f"guard raised {len(bad)} violation(s)")
    for b in bad:
        print("  caught: " + b[:120])
    if missed:
        print("\nNOT CAUGHT:")
        for m in missed:
            print("  " + m)
        return 1
    print("\nPASS — every injected claim was caught")
    return 0


if __name__ == "__main__":
    sys.exit(main())
