#!/usr/bin/env python3
"""Phase-0D step 1: verify the validated Phase-0C mechanical pipeline still reproduces
before any electrical coupling is added. A regression here invalidates everything downstream."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase0b"))
from etm.config import load_doe, load_stack          # noqa: E402
from etm.run_case import run_case                    # noqa: E402

R = Path(__file__).resolve().parents[2]
P0B, P0C, OUT = R / "results" / "phase0b", R / "results" / "phase0c", R / "results" / "phase0d"
CASES = ["C05", "C07", "C08", "C11", "C12", "C19", "C20"]
TOL = 0.5


def main() -> int:
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((P0B / "cooling_calibration.json").read_text())["h_top_W_m2K"]
    arch = {r["case"]: r for r in csv.DictReader((P0C / "full_doe_results.csv").open())}

    rows, ok = [], True
    for cid in CASES:
        r = run_case(cid, stack, doe, OUT / "repro" / cid, h_top=h_top, bc="BC_A",
                     threads=32, solver="", h_xy=0.32, z_scale=1.4)
        now = r["structural"]["die_warpage_pv_um"]
        was = float(arch[cid]["die_warpage_pv_um"])
        d = 100 * abs(now - was) / was
        p = d <= TOL
        ok &= p
        rows.append({"case": cid, "archived_um": was, "rerun_um": now, "delta_pct": d,
                     "T_max_C": r["thermal"]["T_max_C"],
                     "energy_residual_pct": r["thermal"]["energy_residual_pct"], "pass": p})
        print(f"  {cid}: archived {was:8.4f}  rerun {now:8.4f}  delta {d:6.3f}%  "
              f"Tmax {r['thermal']['T_max_C']:7.3f}  {'OK' if p else 'REGRESSION'}", flush=True)

    w = {x["case"]: x["rerun_um"] for x in rows}
    eff = {
        "thickness_C05_C08_pct": 100 * (w["C08"] - w["C05"]) / w["C05"],
        "footprint_C11_vs_C05_pct": 100 * (w["C11"] - w["C05"]) / w["C05"],
        "footprint_C12_vs_C05_pct": 100 * (w["C12"] - w["C05"]) / w["C05"],
        "hvr_heat_C19_vs_C07_pct": 100 * (w["C19"] - w["C07"]) / w["C07"],
        "hvr_heat_C20_vs_C07_pct": 100 * (w["C20"] - w["C07"]) / w["C07"],
    }
    exp = {"thickness_C05_C08_pct": -57.0, "footprint_C11_vs_C05_pct": -21.2,
           "footprint_C12_vs_C05_pct": 20.6, "hvr_heat_C19_vs_C07_pct": -10.8,
           "hvr_heat_C20_vs_C07_pct": 10.8}
    print("\n  Phase-0C effects:")
    for k, v in eff.items():
        e = exp[k]
        good = abs(v - e) < 0.5
        ok &= good
        print(f"    {k:32s} {v:+7.2f}%  (Phase-0C {e:+6.1f}%)  {'OK' if good else 'DRIFT'}")

    verdict = {"reproduced": bool(ok), "tolerance_pct": TOL, "cases": rows, "effects": eff,
               "phase0c_expected": exp}
    (OUT / "phase0c_reproduction.json").write_text(json.dumps(verdict, indent=2))
    print(f"\n{'REPRODUCTION VERIFIED' if ok else 'REGRESSION DETECTED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
