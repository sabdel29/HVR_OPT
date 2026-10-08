#!/usr/bin/env python3
"""Phase-0C step 1: verify the current repository still reproduces the frozen
Phase-0B headline result before any scientific extension is attempted.

If this fails, the extension STOPS and the regression is diagnosed. A changed
baseline silently propagated into a 20-case sweep would invalidate everything.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase0b"))
from etm.config import load_doe, load_stack          # noqa: E402
from etm.run_case import run_case                    # noqa: E402

R = Path(__file__).resolve().parents[2]
P0B = R / "results" / "phase0b"
OUT = R / "results" / "phase0c" / "repro"

# archived Phase-0B headline (BC-A, production mesh)
ARCHIVE = {"C05": 7.7720, "C07": 12.4808, "C13": 7.7739}
TOL_PCT = 0.5          # numerical tolerance on an identical deterministic pipeline


def main() -> int:
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((P0B / "cooling_calibration.json").read_text())["h_top_W_m2K"]
    print(f"frozen h_top = {h_top:.4f} W/m2K\n")

    rows, ok = [], True
    for cid in ("C05", "C07", "C13"):
        arch_file = P0B / cid / "baseline_BC_A" / "metrics.json"
        archived = json.loads(arch_file.read_text())
        r = run_case(cid, stack, doe, OUT / cid, h_top=h_top, bc="BC_A", threads=32,
                     solver="", h_xy=0.32, z_scale=1.4)

        now = r["structural"]["die_warpage_pv_um"]
        was = archived["structural"]["die_warpage_pv_um"]
        d = 100 * abs(now - was) / was
        passed = d <= TOL_PCT and abs(now - ARCHIVE[cid]) / ARCHIVE[cid] * 100 <= TOL_PCT
        ok &= passed
        rows.append((cid, was, now, d, passed))
        print(f"  {cid}: archived {was:8.4f} um   rerun {now:8.4f} um   "
              f"delta {d:6.3f} %   {'OK' if passed else 'REGRESSION'}")
        # secondary quantities
        for k in ("pkg_warpage_pv_um",):
            a, b = archived["structural"][k], r["structural"][k]
            print(f"        {k:22s} {a:9.4f} -> {b:9.4f}  ({100*abs(b-a)/a:5.3f} %)")
        for k in ("T_max_C", "energy_residual_pct"):
            a, b = archived["thermal"][k], r["thermal"][k]
            print(f"        {k:22s} {a:9.4f} -> {b:9.4f}")

    w = {c: n for c, _, n, _, _ in rows}
    order_ok = (abs(w["C05"] - w["C13"]) / w["C05"] < 0.01) and (w["C07"] > 1.4 * w["C05"])
    print(f"\n  ordering C05 ~ C13 << C07 : {'PRESERVED' if order_ok else 'BROKEN'}")
    print(f"    C05={w['C05']:.4f}  C13={w['C13']:.4f}  C07={w['C07']:.4f}")

    verdict = {"reproduced": bool(ok and order_ok), "tolerance_pct": TOL_PCT,
               "h_top_W_m2K": h_top, "ordering_preserved": bool(order_ok),
               "cases": [{"case": c, "archived_um": a, "rerun_um": n,
                          "delta_pct": d, "pass": bool(p)} for c, a, n, d, p in rows]}
    (R / "results" / "phase0c" / "phase0b_reproduction.json").write_text(
        json.dumps(verdict, indent=2))
    print(f"\n{'REPRODUCTION VERIFIED' if verdict['reproduced'] else 'REGRESSION DETECTED'}")
    return 0 if verdict["reproduced"] else 1


if __name__ == "__main__":
    sys.exit(main())
