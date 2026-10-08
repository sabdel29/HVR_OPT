#!/usr/bin/env python3
"""H1b: package-scale H0 (smeared) vs H1 (discrete Cu inclusions) comparison,
plus the CTE-bias correction implied by the unit-cell result.

Both models are run at IDENTICAL mesh settings and with EXACTLY equal Cu volume, so
any difference is attributable to resolving the phase rather than changing it.
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
OUT = R / "results" / "phase0c" / "homogenization"

# finest mesh at which BOTH the smeared and the discrete model fit the C3D8I ceiling
MESH = dict(h_xy=0.45, z_scale=1.0, h_max_factor=5.0)
CASES = ("C05", "C07")

M = {"die_warpage_pv_um": lambda r: r["structural"]["die_warpage_pv_um"],
     "pkg_warpage_pv_um": lambda r: r["structural"]["pkg_warpage_pv_um"],
     "T_max_C": lambda r: r["thermal"]["T_max_C"],
     "T_min_C": lambda r: r["thermal"]["T_min_C"],
     "si_principal_p99_MPa": lambda r: r["structural"]["si_principal_MPa"]["p99"],
     "uz_min_um": lambda r: r["structural"]["uz_min_um"],
     "uz_max_um": lambda r: r["structural"]["uz_max_um"],
     "energy_residual_pct": lambda r: r["thermal"]["energy_residual_pct"]}


def main():
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((P0B / "cooling_calibration.json").read_text())["h_top_W_m2K"]
    OUT.mkdir(parents=True, exist_ok=True)

    # CTE bias measured by the unit cell: numerical alpha_xy / analytic alpha
    uc = json.loads((OUT / "unit_cell_properties.json").read_text())
    cte_corr = uc["alpha_xy_eff_num"] / uc["analytic"]["cte"]

    variants = [
        ("H0_smeared",        dict()),
        ("H1_discrete_p1.2",  dict(tsv_discrete_pitch=1.2)),
        ("H1_discrete_p2.4",  dict(tsv_discrete_pitch=2.4)),
        ("H0_cte_corrected",  dict(overrides={"tsv_homog": {"cte": cte_corr}})),
    ]
    print(f"unit-cell CTE correction factor = {cte_corr:.5f} "
          f"({uc['analytic']['cte']:.4e} -> {uc['alpha_xy_eff_num']:.4e})\n")

    rows = []
    for tag, kw in variants:
        for cid in CASES:
            r = run_case(cid, stack, doe, OUT / f"{tag}_{cid}", h_top=h_top, bc="BC_A",
                         threads=32, solver="", **MESH, **kw)
            d = {"variant": tag, "case": cid, "n_elems": r["mesh"]["n_elems"],
                 "runtime_s": r["runtime_s"]}
            d.update({k: f(r) for k, f in M.items()})
            rows.append(d)
            print(f"  {tag:20s} {cid}  {d['n_elems']:6d} el  "
                  f"die_w={d['die_warpage_pv_um']:8.4f}um  pkg_w={d['pkg_warpage_pv_um']:8.4f}um  "
                  f"Tmax={d['T_max_C']:7.3f}  si99={d['si_principal_p99_MPa']:7.3f}  "
                  f"({r['runtime_s']:.0f}s)", flush=True)

    p = OUT / "h0_h1_runs.csv"
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    # architectural spread under each representation - the decision-relevant quantity
    print(f"\n{'variant':22s}{'C05':>11s}{'C07':>11s}{'spread %':>11s}{'vs H0 abs':>11s}{'vs H0 spread':>14s}")
    print("-" * 80)
    summary = {}
    base = None
    for tag, _ in variants:
        g = {r["case"]: r for r in rows if r["variant"] == tag}
        a, b = g["C05"]["die_warpage_pv_um"], g["C07"]["die_warpage_pv_um"]
        sp = 100 * (b - a) / a
        if base is None:
            base = (a, sp)
        d_abs = 100 * (a - base[0]) / base[0]
        d_sp = sp - base[1]
        summary[tag] = {"C05_um": a, "C07_um": b, "spread_pct": sp,
                        "abs_shift_vs_H0_pct": d_abs, "spread_shift_vs_H0_pp": d_sp}
        print(f"{tag:22s}{a:11.4f}{b:11.4f}{sp:11.2f}{d_abs:11.2f}{d_sp:14.2f}")

    (OUT / "h0_h1_summary.json").write_text(json.dumps(
        {"cte_correction_factor": cte_corr, "mesh": MESH, "summary": summary}, indent=2))
    print(f"\nwrote {p}")


if __name__ == "__main__":
    main()
