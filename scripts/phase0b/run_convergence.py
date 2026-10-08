#!/usr/bin/env python3
"""Phase-0B mandatory mesh-convergence study.

Spec acceptance targets (validation targets, NOT reliability thresholds):
    |w_M3 - w_M2| / w_M3  < 5%    for global warpage
    |s_M3 - s_M2| / s_M3  < 10%   for a REGULARIZED local stress metric (p99)
Raw nodal maxima are tracked for diagnosis but are never the acceptance quantity:
comparing the single highest nodal stress across meshes of different density is
exactly the error the spec forbids.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from etm.config import load_stack, load_doe
from etm.run_case import run_case

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0b"

# Graded meshes. h_xy is the element size AT MATERIAL BOUNDARIES; the far field
# coarsens to h_xy * h_max_factor. All four levels sit inside the measured
# C3D8I/SPOOLES element ceiling (see etm.run_case.SPOOLES_C3D8I_MAX).
LEVELS = [("M1", 0.60, 0.8), ("M2", 0.45, 1.0), ("M3", 0.38, 1.2), ("M4", 0.32, 1.4)]

TRACK = [
    ("T_max_C",              lambda r: r["thermal"]["T_max_C"]),
    ("energy_residual_pct",  lambda r: r["thermal"]["energy_residual_pct"]),
    ("die_warpage_pv_um",    lambda r: r["structural"]["die_warpage_pv_um"]),
    ("pkg_warpage_pv_um",    lambda r: r["structural"]["pkg_warpage_pv_um"]),
    ("si_principal_p99_MPa", lambda r: r["structural"]["si_principal_MPa"]["p99"]),
    ("si_principal_raw_MPa", lambda r: r["structural"]["si_principal_MPa"]["raw_max"]),
    ("tsv_vm_p99_MPa",       lambda r: r["structural"]["tsv_region_vm_MPa"]["p99"]),
    ("interface_shear_p99_MPa", lambda r: r["structural"]["interface_shear_MPa"]["p99"]),
    ("interface_peel_p99_MPa",  lambda r: r["structural"]["interface_peel_MPa"]["p99"]),
]


def main(case_id: str = "C05") -> None:
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((OUT / "cooling_calibration.json").read_text())["h_top_W_m2K"]

    rows = []
    for name, hxy, zs in LEVELS:
        wd = OUT / "convergence" / f"{case_id}_{name}"
        r = run_case(case_id, stack, doe, wd, h_top=h_top, h_xy=hxy, z_scale=zs,
                     bc="BC_A", threads=32, solver='')
        row = {"level": name, "h_xy_mm": hxy, "z_scale": zs,
               "n_nodes": r["mesh"]["n_nodes"], "n_elems": r["mesh"]["n_elems"],
               "el_through_substrate": r["mesh"]["elems_through_substrate"],
               "el_through_die": r["mesh"]["elems_through_die"],
               "runtime_s": r["runtime_s"]}
        for k, f in TRACK:
            row[k] = f(r)
        rows.append(row)
        print(f"  {name}: {row['n_elems']:7d} el  Tmax={row['T_max_C']:7.3f}  "
              f"die_w={row['die_warpage_pv_um']:7.3f}um  "
              f"si99={row['si_principal_p99_MPa']:7.3f}MPa  ({row['runtime_s']:.0f}s)")

    # successive relative changes
    for i in range(1, len(rows)):
        for k, _ in TRACK:
            a, b = rows[i - 1][k], rows[i][k]
            rows[i][f"d_{k}_pct"] = (abs(b - a) / abs(b) * 100.0) if b else float("nan")

    fields = list(rows[-1].keys())
    p = OUT / "mesh_convergence.csv"
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r_ in rows:
            w.writerow({k: r_.get(k, "") for k in fields})
    print(f"\nwrote {p}")

    last = rows[-1]
    verdict = {
        "case": case_id,
        "warpage_die_change_pct": last.get("d_die_warpage_pv_um_pct"),
        "warpage_pkg_change_pct": last.get("d_pkg_warpage_pv_um_pct"),
        "si_p99_change_pct": last.get("d_si_principal_p99_MPa_pct"),
        "si_raw_change_pct": last.get("d_si_principal_raw_MPa_pct"),
        "interface_shear_p99_change_pct": last.get("d_interface_shear_p99_MPa_pct"),
        "Tmax_change_pct": last.get("d_T_max_C_pct"),
        "target_warpage_pct": 5.0, "target_stress_pct": 10.0,
        "warpage_converged": (last.get("d_die_warpage_pv_um_pct", 1e9) < 5.0
                              and last.get("d_pkg_warpage_pv_um_pct", 1e9) < 5.0),
        "stress_converged": last.get("d_si_principal_p99_MPa_pct", 1e9) < 10.0,
    }
    (OUT / "convergence_verdict.json").write_text(json.dumps(verdict, indent=2))
    print(json.dumps(verdict, indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "C05")
