#!/usr/bin/env python3
"""Phase-0F Sec.7: the same decisive candidates under BOTH assembly states.

Package-level (BC-A, free warpage) and board-mounted (BC-B) are reported separately and never
combined. A tradeoff counts as robust across assembly states only if its interpretation
survives both; where the sign changes, that is the result.
"""
from __future__ import annotations
import csv, json, math, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0f"))
import kw1
from etm.config import load_doe, load_stack

OUT = R / "results" / "phase0f"

CASES = [("thickness", "ARCH_A", "uniform", 49, 3.5, 0.8),
         ("thickness", "ARCH_A", "uniform", 49, 3.5, 1.5),
         ("thickness", "ARCH_B", "uniform", 49, 3.5, 0.8),
         ("thickness", "ARCH_B", "uniform", 49, 3.5, 2.0),
         ("footprint", "ARCH_A", "uniform", 36, 3.0, 1.5),
         ("footprint", "ARCH_A", "uniform", 49, 3.0, 1.5),
         ("placement", "ARCH_A", "uniform", 49, 3.5, 1.5),
         ("placement", "ARCH_A", "compact", 49, 3.5, 1.5)]


def main():
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((OUT / "cooling_1kw_calibration.json").read_text())["h_top_W_m2K"]
    wd = OUT / "runs_bcbpairs"
    rows = []
    for grp, arch, fam, M, j, h in CASES:
        t0 = time.time()
        try:
            r = kw1.coupled_1kw(arch, fam, h, h_top, stack, doe, wd, m_vr=M, j=j,
                                bc="BC_B", h_xy=0.70)
        except Exception as e:
            print(f"  {grp:10s} {arch} {fam:10s} h={h:.2f}  FAILED: {str(e)[:80]}", flush=True)
            continue
        r.pop("history", None)
        r["group"] = grp
        rows.append(r)
        print(f"  {grp:10s} {arch} {fam:10s} M={M} j={j} h={h:.2f}  BC_B  "
              f"w={r['die_warpage_pv_um']:8.4f} kappa={r['curvature_um_per_mm2']:+.3e} "
              f"shear99={r['interface_shear_p99_MPa']:7.3f} P_el={r['P_elec_total_w']:7.2f} "
              f"({time.time()-t0:.0f}s)", flush=True)
    keys = sorted({k for r in rows for k in r})
    with open(OUT / "bcb_pairs_1kw.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
    print(f"\nwrote {OUT/'bcb_pairs_1kw.csv'} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
