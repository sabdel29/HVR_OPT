#!/usr/bin/env python3
"""Phase-0M-R3B Section 8 --- is the ARCH_Z2 TSV margin process-qualified, or parametric?

Phase 0M-R3A found 32 um to be the smallest diameter on its grid that passes a -2 %
diameter / +2 % depth bound. That bound was never sourced. This phase searched for a real
tolerance and did not find one, so rather than assert a margin the question is INVERTED:
for each diameter, how much tolerance can it absorb before AR = 10 is violated? That is a
statement about the design, not about the process, and it is labelled as such.
"""
from __future__ import annotations
import csv, math, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3b"
SRC = R / "results" / "phase0mr3a" / "z2_tsv_diameter_sweep.csv"
AR_MAX = 10.0
L_UM = 300.0          # ARCH_Z2 TSV span, SOURCE_BACKED (0M-R2 architecture geometry)

SEARCH = [
 ("etched depth tolerance", "OPEN", "OpenAlex: 338 hits on DRIE depth control, none giving "
  "a process tolerance for a 300 um TSV; the two on-point reviews are MDPI and every "
  "route to their full text returns a block page from this host"),
 ("via diameter tolerance", "OPEN", "same searches; no numeric diameter tolerance found"),
 ("liner / plating tolerance", "OPEN", "7 hits, none giving a tolerance band"),
 ("taper / scallop", "OPEN", "DRIE taper papers found but for MEMS geometries at other "
  "scales; no transferable tolerance"),
 ("aspect-ratio process limit", "SOURCE_BACKED", "AR <= 10 is the framework's own "
  "source-backed hard rule and is unchanged"),
 ("overlay / alignment", "OPEN", "no source"),
 ("pitch / KOZ tolerance", "SOURCE_BACKED", "s_min = 30 um, framework SOURCE_BACKED"),
]


def max_tolerance_pct(d_um: float) -> float:
    """Symmetric tolerance t (%) on diameter AND depth that AR = 10 can still absorb.

    Worst case shrinks the diameter and deepens the via:
        AR_worst = L(1+t) / (d(1-t)) <= 10
    """
    ar = L_UM / d_um
    if ar >= AR_MAX:
        return 0.0
    # solve L(1+t) = 10 d (1-t)  ->  t = (10d - L) / (10d + L)
    return 100.0 * (AR_MAX * d_um - L_UM) / (AR_MAX * d_um + L_UM)


def main() -> int:
    src = {r["d_um"]: r for r in csv.DictReader(SRC.open())}
    rows = []
    for d_s in sorted(src, key=float):
        d = float(d_s)
        if d not in (30.0, 32.0, 34.0, 36.0):
            continue
        r = src[d_s]
        t = max_tolerance_pct(d)
        rows.append({
            "d_um": d, "L_um": L_UM, "AR_nominal": round(L_UM / d, 4),
            "M_AR_nominal": round(AR_MAX / (L_UM / d), 4),
            "n_required": r["n_required"], "n_available": r["n_available"],
            "phi_cu": r["phi_cu"],
            "max_absorbable_tolerance_pct": round(t, 3),
            "passes_parametric_2pct": t >= 2.0,
            "tolerance_provenance": "OPEN -- no manufacturing tolerance for this process "
                                    "was sourced from this host",
            "licensed_wording": ("PARAMETRICALLY MARGINED at the stated tolerance; "
                                 "NOT process-qualified"),
        })
    p = OUT / "z2_tsv_sourced_tolerance_sweep.csv"
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"{'d_um':>6} {'AR':>7} {'M_AR':>7} {'max tol it can absorb':>22} {'>=2%?':>7}")
    for r in rows:
        print(f"{r['d_um']:6.0f} {r['AR_nominal']:7.3f} {r['M_AR_nominal']:7.3f} "
              f"{r['max_absorbable_tolerance_pct']:20.2f} % {str(r['passes_parametric_2pct']):>7}")
    ps = OUT / "z2_tsv_tolerance_search.csv"
    with ps.open("w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["parameter", "provenance", "what the search found"])
        w.writerows(SEARCH)
    n_open = sum(1 for _, s, _ in SEARCH if s == "OPEN")
    print(f"\ntolerance parameters searched: {len(SEARCH)}, still OPEN: {n_open}")
    print("32 um: PARAMETRICALLY MARGINED, NOT process-qualified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
