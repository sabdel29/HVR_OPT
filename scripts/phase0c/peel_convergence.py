#!/usr/bin/env python3
"""Targeted convergence retest of the interface metrics with an exclusion radius.

Phase 0B: interface peel p99 changed 19.24 % over the final refinement step and was
declared UNRESOLVED. The cause is a bimaterial free-edge singularity at the underfill
perimeter. This retests the same four meshes using peel/shear evaluated in the bonded
interior, and reports whether that converges. If it still does not, peel stays demoted.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase0b"))
from etm.config import load_doe, load_stack          # noqa: E402
from etm.run_case import run_case                    # noqa: E402

R = Path(__file__).resolve().parents[2]
P0B = R / "results" / "phase0b"
OUT = R / "results" / "phase0c"
LEVELS = [("M1", 0.60, 0.8), ("M2", 0.45, 1.0), ("M3", 0.38, 1.2), ("M4", 0.32, 1.4)]
KEYS = ["interface_peel_MPa", "interface_peel_excl025_MPa", "interface_peel_excl050_MPa",
        "interface_peel_excl100_MPa", "interface_shear_MPa", "interface_shear_excl050_MPa"]


def main():
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((P0B / "cooling_calibration.json").read_text())["h_top_W_m2K"]
    rows = []
    for name, hxy, zs in LEVELS:
        r = run_case("C05", stack, doe, OUT / "peel_convergence" / name, h_top=h_top,
                     h_xy=hxy, z_scale=zs, bc="BC_A", threads=32, solver="")
        d = {"level": name, "n_elems": r["mesh"]["n_elems"]}
        for k in KEYS:
            v = r["structural"].get(k)
            d[k + "_p99"] = v["p99"] if v else float("nan")
            d[k + "_raw"] = v["raw_max"] if v else float("nan")
        rows.append(d)
        print(f"  {name}: {d['n_elems']:6d} el  " +
              "  ".join(f"{k.replace('interface_','').replace('_MPa','')}={d[k+'_p99']:7.4f}"
                        for k in KEYS), flush=True)

    for i in range(1, len(rows)):
        for k in KEYS:
            a, b = rows[i-1][k+"_p99"], rows[i][k+"_p99"]
            rows[i][f"d_{k}_pct"] = abs(b - a) / abs(b) * 100 if b else float("nan")

    p = OUT / "peel_convergence.csv"
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[-1].keys())); w.writeheader()
        for x in rows:
            w.writerow({k: x.get(k, "") for k in rows[-1]})

    print(f"\n{'metric':34s}{'M3->M4 change':>16s}{'target':>9s}{'verdict':>14s}")
    print("-" * 74)
    verdict = {}
    for k in KEYS:
        d = rows[-1].get(f"d_{k}_pct", float("nan"))
        ok = d < 10.0
        verdict[k] = {"final_change_pct": d, "converged": bool(ok)}
        print(f"{k:34s}{d:15.2f}%{'<10%':>9s}{'CONVERGED' if ok else 'NOT CONVERGED':>14s}")
    (OUT / "peel_convergence_verdict.json").write_text(json.dumps(verdict, indent=2))
    print(f"\nwrote {p}")


if __name__ == "__main__":
    main()
