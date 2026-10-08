#!/usr/bin/env python3
"""Phase-0C: full frozen C01-C20 sweep + a convergence check for the THICK substrate.

Case definitions come verbatim from configs/phase0b/doe_cases.yaml and are NOT altered.
Phase-0B outputs are never touched; everything lands under results/phase0c/.

Why the extra convergence study: the frozen mesh policy gives the h_sub = 500 um cases
3 elements across a 350 um sub_lower layer (117 um each) versus 16.7 um for the 200 um
cases. Substrate thickness is the highest-priority Phase-0C variable, so its discretisation
must be independently demonstrated converged rather than assumed from the C05 study.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase0b"))
from etm.config import load_doe, load_stack          # noqa: E402
from etm.run_case import run_case                    # noqa: E402

R = Path(__file__).resolve().parents[2]
P0B = R / "results" / "phase0b"
OUT = R / "results" / "phase0c"
PROD = dict(h_xy=0.32, z_scale=1.4)
LEVELS = [("M1", 0.60, 0.8), ("M2", 0.45, 1.0), ("M3", 0.38, 1.2), ("M4", 0.32, 1.4)]

FIELDS = {
    "T_max_C": lambda r: r["thermal"]["T_max_C"],
    "T_min_C": lambda r: r["thermal"]["T_min_C"],
    "energy_residual_pct": lambda r: r["thermal"]["energy_residual_pct"],
    "die_warpage_pv_um": lambda r: r["structural"]["die_warpage_pv_um"],
    "pkg_warpage_pv_um": lambda r: r["structural"]["pkg_warpage_pv_um"],
    "si_principal_p99_MPa": lambda r: r["structural"]["si_principal_MPa"]["p99"],
    "si_principal_p95_MPa": lambda r: r["structural"]["si_principal_MPa"]["p95"],
    "si_principal_raw_MPa": lambda r: r["structural"]["si_principal_MPa"]["raw_max"],
    "tsv_vm_p99_MPa": lambda r: (r["structural"].get("tsv_region_vm_MPa") or {}).get("p99", float("nan")),
    "hvr_vm_p99_MPa": lambda r: (r["structural"].get("hvr_tile_vm_MPa") or {}).get("p99", float("nan")),
    "interface_shear_p99_MPa": lambda r: r["structural"]["interface_shear_MPa"]["p99"],
    "interface_peel_p99_MPa": lambda r: r["structural"]["interface_peel_MPa"]["p99"],
    "uz_max_um": lambda r: r["structural"]["uz_max_um"],
    "uz_min_um": lambda r: r["structural"]["uz_min_um"],
}


def row_for(cid: str, case: dict, r: dict, variant: str = "nominal") -> dict:
    d = {"case": cid, "variant": variant, "bc": r["bc"]["bc"],
         "n_vr": case["n_vr"], "placement": case["placement"],
         "tile_ax": case["tile_ax"], "tile_ay": case["tile_ay"],
         "h_sub_mm": case["h_sub"],
         "a_vr_total_mm2": round(case["tile_ax"] * case["tile_ay"] * case["n_vr"], 4),
         "p_hvr_total_W": r["loads"]["p_hvr_total_W"],
         "aspect_ratio": round(case["tile_ax"] / case["tile_ay"], 4),
         "n_elems": r["mesh"]["n_elems"], "runtime_s": r["runtime_s"]}
    d.update({k: f(r) for k, f in FIELDS.items()})
    return d


def thick_convergence(stack, doe, h_top, threads=32):
    print("=== convergence check: C08 (h_sub = 500 um) ===", flush=True)
    rows = []
    for name, hxy, zs in LEVELS:
        r = run_case("C08", stack, doe, OUT / "convergence_thick" / f"C08_{name}",
                     h_top=h_top, h_xy=hxy, z_scale=zs, bc="BC_A", threads=threads, solver="")
        row = {"level": name, "h_xy_mm": hxy, "z_scale": zs,
               "n_elems": r["mesh"]["n_elems"],
               "sub_lower_nz": r["mesh"]["elems_through_substrate"]}
        row.update({k: f(r) for k, f in FIELDS.items()})
        rows.append(row)
        print(f"  {name}: {row['n_elems']:6d} el  Tmax={row['T_max_C']:7.3f}  "
              f"die_w={row['die_warpage_pv_um']:7.4f}um  "
              f"si99={row['si_principal_p99_MPa']:7.3f}MPa  ({r['runtime_s']:.0f}s)", flush=True)
    for i in range(1, len(rows)):
        for k in FIELDS:
            a, b = rows[i - 1][k], rows[i][k]
            rows[i][f"d_{k}_pct"] = (abs(b - a) / abs(b) * 100.0) if b else float("nan")
    p = OUT / "convergence_thick.csv"
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[-1].keys())); w.writeheader()
        for x in rows:
            w.writerow({k: x.get(k, "") for k in rows[-1]})
    last = rows[-1]
    v = {"case": "C08", "h_sub_mm": 0.5,
         "die_warpage_change_pct": last.get("d_die_warpage_pv_um_pct"),
         "pkg_warpage_change_pct": last.get("d_pkg_warpage_pv_um_pct"),
         "si_p99_change_pct": last.get("d_si_principal_p99_MPa_pct"),
         "Tmax_change_pct": last.get("d_T_max_C_pct"),
         "warpage_converged": last.get("d_die_warpage_pv_um_pct", 1e9) < 5.0,
         "stress_converged": last.get("d_si_principal_p99_MPa_pct", 1e9) < 10.0}
    (OUT / "convergence_thick_verdict.json").write_text(json.dumps(v, indent=2))
    print(json.dumps(v, indent=2), flush=True)
    return v


def main():
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((P0B / "cooling_calibration.json").read_text())["h_top_W_m2K"]
    OUT.mkdir(parents=True, exist_ok=True)

    thick_convergence(stack, doe, h_top)

    print("\n=== full frozen C01-C20 sweep, BC-A, production mesh ===", flush=True)
    order = ["C03", "C08", "C16", "C18",          # thickness first (highest priority)
             "C09", "C10", "C11", "C12",          # aspect ratio, footprint
             "C05", "C07", "C13",                 # Phase-0B anchors
             "C02", "C06", "C14", "C15", "C17",   # placement family
             "C19", "C20",                        # HVR heat
             "C01", "C04"]                        # count / compactness controls
    assert sorted(order) == sorted(doe["cases"]), "sweep must cover exactly C01-C20"

    rows, t0 = [], time.time()
    for cid in order:
        case = doe["cases"][cid]
        r = run_case(cid, stack, doe, OUT / "sweep" / cid, h_top=h_top, bc="BC_A",
                     threads=32, solver="", **PROD)
        rows.append(row_for(cid, case, r))
        print(f"  {cid} N={case['n_vr']} {case['placement']:20s} h={case['h_sub']*1000:3.0f}u "
              f"A={rows[-1]['a_vr_total_mm2']:6.1f} P={rows[-1]['p_hvr_total_W']:5.1f}W  "
              f"Tmax={rows[-1]['T_max_C']:7.3f}  die_w={rows[-1]['die_warpage_pv_um']:8.4f}um  "
              f"pkg_w={rows[-1]['pkg_warpage_pv_um']:8.4f}um  "
              f"si99={rows[-1]['si_principal_p99_MPa']:7.3f}  "
              f"Eb={rows[-1]['energy_residual_pct']:+.3f}%  ({r['runtime_s']:.0f}s)", flush=True)

    rows.sort(key=lambda x: x["case"])
    p = OUT / "full_doe_results.csv"
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"\nwrote {p}  ({len(rows)} cases, {time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
