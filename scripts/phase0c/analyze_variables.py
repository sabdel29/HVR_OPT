#!/usr/bin/env python3
"""Phase-0C analysis: reduce the C01-C20 sweep to VARIABLE-LEVEL effects.

The deliverable is not 20 case results. It is an answer to: which design variable is the
dominant mechanical lever, and is it DVPD-specific or generic floorplanning?

Effect size for a matched pair/sweep:   S = (max - min) / |median|
Resolution rule (Phase-0B):             resolved iff S > 2 u,  u = mesh uncertainty
Bands (Phase-0B):                       weak 10-15%, moderate 15-25%, strong >=25%
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase0b"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from descriptors import descriptors                       # noqa: E402
from etm.config import load_doe, load_stack               # noqa: E402
from etm.placement import case_tiles                      # noqa: E402

R = Path(__file__).resolve().parents[2]
P0B = R / "results" / "phase0b"
P0C = R / "results" / "phase0c"

METRICS = ["T_max_C", "die_warpage_pv_um", "pkg_warpage_pv_um",
           "si_principal_p99_MPa", "tsv_vm_p99_MPa", "interface_shear_p99_MPa"]
LABEL = {"T_max_C": "T_max", "die_warpage_pv_um": "die warp",
         "pkg_warpage_pv_um": "pkg warp", "si_principal_p99_MPa": "Si s1 p99",
         "tsv_vm_p99_MPa": "TSV vM p99", "interface_shear_p99_MPa": "iface shear p99"}

# Matched comparisons available in the FROZEN DOE. Each entry is
#   (variable, dvpd_specific, [case list in sweep order], swept quantity)
COMPARISONS = [
    ("substrate thickness (N=2 compact)",  True,  ["C01", "C03"], "h_sub_mm"),
    ("substrate thickness (N=4 distrib.)", True,  ["C05", "C08"], "h_sub_mm"),
    ("substrate thickness (N=6 distrib.)", True,  ["C13", "C16"], "h_sub_mm"),
    ("HVR footprint (N=4 distrib.)",       True,  ["C11", "C05", "C12"], "a_vr_total_mm2"),
    ("HVR tile aspect ratio (N=4)",        True,  ["C10", "C05", "C09"], "aspect_ratio"),
    ("HVR heat (N=4 asymmetric)",          True,  ["C19", "C07", "C20"], "p_hvr_total_W"),
    ("VR count (symmetric distributed)",   True,  ["C05", "C13", "C17"], "n_vr"),
    ("VR count (compact family)",          True,  ["C01", "C04"], "n_vr"),
    ("placement (N=4 family)",             False, ["C04", "C05", "C06", "C07"], "placement"),
    ("placement (N=2 family)",             False, ["C01", "C02"], "placement"),
    ("placement (N=6 family)",             False, ["C13", "C14", "C15"], "placement"),
    ("placement asymmetry only (N=4)",     False, ["C05", "C07"], "placement"),
    ("placement asymmetry only (N=6)",     False, ["C13", "C15"], "placement"),
]


def band(s: float) -> str:
    a = abs(s)
    return "STRONG" if a >= .25 else "MODERATE" if a >= .15 else "WEAK" if a >= .10 else "BELOW-BAND"


def resolved(s: float, u: float) -> bool:
    return bool(abs(s) > 2 * abs(u))


def mesh_uncertainty() -> dict[str, float]:
    """Worst-case final-step convergence change across the thin (C05) and thick (C08)
    studies, per metric. Using the worse of the two is the conservative choice."""
    key = {"T_max_C": "d_T_max_C_pct", "die_warpage_pv_um": "d_die_warpage_pv_um_pct",
           "pkg_warpage_pv_um": "d_pkg_warpage_pv_um_pct",
           "si_principal_p99_MPa": "d_si_principal_p99_MPa_pct",
           "tsv_vm_p99_MPa": "d_tsv_vm_p99_MPa_pct",
           "interface_shear_p99_MPa": "d_interface_shear_p99_MPa_pct"}
    out = {m: 0.0 for m in METRICS}
    for f in (P0B / "mesh_convergence.csv", P0C / "convergence_thick.csv"):
        if not f.exists():
            continue
        last = list(csv.DictReader(f.open()))[-1]
        for m, k in key.items():
            try:
                out[m] = max(out[m], abs(float(last[k])) / 100.0)
            except (KeyError, TypeError, ValueError):
                pass
    return out


def main():
    stack, doe = load_stack(), load_doe()
    rows = {r["case"]: r for r in csv.DictReader((P0C / "full_doe_results.csv").open())}
    for r in rows.values():
        for k, v in r.items():
            if k not in ("case", "variant", "bc", "placement"):
                try:
                    r[k] = float(v)
                except (TypeError, ValueError):
                    pass
    u = mesh_uncertainty()

    # ---------- geometric descriptors -------------------------------------
    t_tile = stack["geometry"]["hvr_tile"]["thickness"]["value"]
    desc_rows = []
    for cid in sorted(doe["cases"]):
        d = {"case": cid}
        d.update(descriptors(case_tiles(doe["cases"][cid], stack, doe), t_tile))
        d["h_sub_mm"] = doe["cases"][cid]["h_sub"]
        for m in METRICS:
            d[m] = rows[cid][m]
        desc_rows.append(d)
    p = P0C / "geometric_descriptors.csv"
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(desc_rows[0].keys())); w.writeheader()
        w.writerows(desc_rows)

    # ---------- variable-level effects ------------------------------------
    eff_rows = []
    print(f"\n{'='*140}\nVARIABLE-LEVEL EFFECTS (BC-A, converged production mesh)\n{'='*140}")
    hdr = (f"{'variable':38s}{'cases':22s}" +
           "".join(f"{LABEL[m]:>15s}" for m in METRICS) + f"{'DVPD?':>8s}")
    print(hdr); print("-" * len(hdr))

    for name, dvpd, cases, swept in COMPARISONS:
        rec = {"variable": name, "dvpd_specific": dvpd, "cases": " ".join(cases),
               "swept_quantity": swept,
               "swept_values": " ".join(str(rows[c].get(swept, doe["cases"][c].get("placement")))
                                        for c in cases)}
        line = f"{name:38s}{' '.join(cases):22s}"
        for m in METRICS:
            vals = [rows[c][m] for c in cases]
            med = float(np.median(vals))
            S = (max(vals) - min(vals)) / abs(med) if med else float("nan")
            rec[f"{m}_min"] = round(min(vals), 4)
            rec[f"{m}_max"] = round(max(vals), 4)
            rec[f"{m}_S_pct"] = round(100 * S, 2)
            rec[f"{m}_resolved"] = resolved(S, u[m])
            rec[f"{m}_band"] = band(S)
            mark = "*" if resolved(S, u[m]) else " "
            line += f"{100*S:13.2f}%{mark}"
        line += f"{'YES' if dvpd else 'generic':>8s}"
        print(line)
        eff_rows.append(rec)

    print(f"\n  * = resolved (S > 2u).  Mesh uncertainty 2u per metric: " +
          ", ".join(f"{LABEL[m]} {200*u[m]:.2f}%" for m in METRICS))

    p = P0C / "variable_effects.csv"
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(eff_rows[0].keys())); w.writeheader()
        w.writerows(eff_rows)

    # ---------- ranking on die warpage ------------------------------------
    print(f"\n{'='*100}\nRANKING BY ROBUST DIE-WARPAGE EFFECT\n{'='*100}")
    rk = sorted(eff_rows, key=lambda r: -abs(r["die_warpage_pv_um_S_pct"]))
    print(f"{'rank':>4s}  {'variable':38s}{'S(die warp)':>13s}{'resolved':>10s}{'band':>11s}{'DVPD?':>9s}")
    for i, r in enumerate(rk, 1):
        print(f"{i:4d}  {r['variable']:38s}{r['die_warpage_pv_um_S_pct']:12.2f}%"
              f"{str(r['die_warpage_pv_um_resolved']):>10s}{r['die_warpage_pv_um_band']:>11s}"
              f"{'YES' if r['dvpd_specific'] else 'generic':>9s}")

    # ---------- descriptor correlation ------------------------------------
    print(f"\n{'='*100}\nMECHANISM: does die warpage follow the inclusion-field moments?\n{'='*100}")
    sub = [d for d in desc_rows if d["h_sub_mm"] == 0.200]
    y = np.array([d["die_warpage_pv_um"] for d in sub])
    print(f"  (restricted to the {len(sub)} cases at h_sub = 200 um so thickness does not confound)")
    corr = {}
    for k in ("centroid_area_offset_mm", "first_moment_area_mm3", "centroid_heat_offset_mm",
              "I_polar_mm4", "radius_gyration_mm", "A_total_mm2", "n_tiles",
              "anisotropy", "anisotropy_shape_only", "mean_tile_area_mm2"):
        x = np.array([d[k] for d in sub], float)
        if np.std(x) < 1e-12:
            continue
        r_ = float(np.corrcoef(x, y)[0, 1])
        corr[k] = r_
        print(f"    Pearson r(die warpage, {k:26s}) = {r_:+.4f}")
    # two-term physical model: bowl depth from spread + tilt from first moment
    X = np.column_stack([np.ones(len(sub)),
                         [d["I_polar_mm4"] for d in sub],
                         [d["first_moment_area_mm3"] for d in sub]])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ beta
    ss = 1 - np.sum((y - pred) ** 2) / np.sum((y - y.mean()) ** 2)
    print(f"\n    two-term physical fit  w_pv ~ b0 + b1*I_polar + b2*|first moment|")
    print(f"      b0={beta[0]:+.4f} um   b1={beta[1]:+.5e} um/mm^4   b2={beta[2]:+.5e} um/mm^3")
    print(f"      R^2 = {ss:.4f}  over {len(sub)} cases, 3 parameters "
          f"(interpretation aid only - not a surrogate)")

    json.dump({"correlations": corr, "two_term_fit": {"b0": beta[0], "b1": beta[1],
               "b2": beta[2], "r2": ss, "n": len(sub)}, "mesh_u_rel": u},
              (P0C / "mechanism_analysis.json").open("w"), indent=2)
    print(f"\nwrote {P0C/'variable_effects.csv'}\nwrote {P0C/'geometric_descriptors.csv'}")


if __name__ == "__main__":
    main()
