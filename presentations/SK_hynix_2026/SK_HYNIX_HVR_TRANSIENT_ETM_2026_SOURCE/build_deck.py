#!/usr/bin/env python3
"""Build SK_HYNIX_HVR_TRANSIENT_ETM_2026.pptx from deck_content.py."""
from __future__ import annotations
import re, sys
from pathlib import Path
import json
from deck_engine import deck, new, LOG, log_new
import deck_content as C

OUT = Path(__file__).resolve().parent.parent / "SK_HYNIX_HVR_TRANSIENT_ETM_2026.pptx"


def build():
    prs = deck()
    n = 0
    for f in C.MAIN:
        n += 1
        r = log_new("main"); r["page"] = n; r["fn"] = f.__name__
        f(new(prs), n)
    for i, f in enumerate(C.BACK, start=1):
        r = log_new("backup"); r["page"] = f"B{i}"; r["fn"] = f.__name__
        f(new(prs), i)
    prs.save(OUT)
    (Path(__file__).resolve().parent / "deck_manifest.json").write_text(
        json.dumps(LOG, indent=1))
    return prs, n


def timings():
    out = []
    for f in C.MAIN:
        src = f.__doc__ or ""
        out.append(f.__name__)
    return out


if __name__ == "__main__":
    prs, nmain = build()
    print(f"wrote {OUT.name}")
    print(f"  main slides   {nmain}")
    print(f"  backup slides {len(C.BACK)}")
    print(f"  total         {len(prs.slides.__iter__.__self__._sldIdLst)}")
