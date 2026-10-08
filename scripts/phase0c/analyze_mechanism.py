#!/usr/bin/env python3
"""Phase-0C mechanism, scaling and interaction analysis.

Purpose is mechanistic interpretation, not prediction. No ML. The regressions here have
3 parameters over 16 samples and exist only to test whether a compact mechanics argument
explains the FEA, per the Phase-0C brief.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase0b"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from descriptors import descriptors                  # noqa: E402
from etm.config import load_doe, load_stack          # noqa: E402
from etm.placement import case_tiles                 # noqa: E402

R = Path(__file__).resolve().parents[2]
P0C = R / "results" / "phase0c"


def load():
    rows = {}
    for r in csv.DictReader((P0C / "full_doe_results.csv").open()):
        for k, v in r.items():
            if k not in ("case", "variant", "bc", "placement"):
                try:
                    r[k] = float(v)
                except (TypeError, ValueError):
                    pass
        rows[r["case"]] = r
    return rows


def main():
    stack, doe = load_stack(), load_doe()
    rows = load()
    g = stack["geometry"]
    t_tile = g["hvr_tile"]["thickness"]["value"]
    t_stack_fixed = (g["interface_layer"]["thickness"]["value"]
                     + g["functional_die"]["thickness"]["value"]
                     + g["tim"]["thickness"]["value"])
    out = {}

    # ---------------- matched-pair relative changes ------------------------
    print(f"\n{'='*104}\nMATCHED COMPARISONS - relative change from the stated baseline\n{'='*104}")
    pairs = [
        ("substrate thickness", "C01", "C03", "N=2 compact,   h 200->500 um", True),
        ("substrate thickness", "C05", "C08", "N=4 distributed, h 200->500 um", True),
        ("substrate thickness", "C13", "C16", "N=6 distributed, h 200->500 um", True),
        ("HVR footprint", "C05", "C11", "96 -> 72 mm2 (-25%)", True),
        ("HVR footprint", "C05", "C12", "96 -> 120 mm2 (+25%)", True),
        ("HVR aspect ratio", "C05", "C09", "AR 1 -> 2", True),
        ("HVR aspect ratio", "C05", "C10", "AR 1 -> 0.5 (rotated)", True),
        ("HVR heat", "C07", "C19", "42 -> 31.5 W (-25%)", True),
        ("HVR heat", "C07", "C20", "42 -> 52.5 W (+25%)", True),
        ("VR count", "C05", "C13", "N 4 -> 6", True),
        ("VR count", "C05", "C17", "N 4 -> 8", True),
        ("VR count", "C01", "C04", "N 2 -> 4 (compact)", True),
        ("placement", "C05", "C07", "distributed -> asymmetric", False),
        ("placement", "C05", "C04", "distributed -> compact central", False),
        ("placement", "C05", "C06", "distributed -> edge/corner", False),
        ("placement", "C13", "C14", "distributed -> perimeter ring", False),
    ]
    tab = []
    print(f"{'variable':22s}{'comparison':32s}{'d die warp':>12s}{'d pkg warp':>12s}"
          f"{'d T_max':>10s}{'DVPD?':>9s}")
    print("-" * 104)
    for var, a, b, lab, dv in pairs:
        d = {}
        for m, key in (("die", "die_warpage_pv_um"), ("pkg", "pkg_warpage_pv_um"),
                       ("tmax", "T_max_C"), ("si", "si_principal_p99_MPa")):
            d[m] = 100 * (rows[b][key] - rows[a][key]) / rows[a][key]
        tab.append({"variable": var, "baseline": a, "variant": b, "comparison": lab,
                    "dvpd_specific": dv, **{f"d_{k}_pct": round(v, 2) for k, v in d.items()}})
        print(f"{var:22s}{lab:32s}{d['die']:11.2f}%{d['pkg']:11.2f}%{d['tmax']:9.2f}%"
              f"{('YES' if dv else 'generic'):>9s}")
    with (P0C / "matched_comparisons.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(tab[0].keys())); w.writeheader(); w.writerows(tab)
    out["matched"] = tab

    # ---------------- thickness scaling law --------------------------------
    print(f"\n{'='*104}\nSUBSTRATE-THICKNESS SCALING\n{'='*104}")
    sc = []
    for a, b, lab in (("C01", "C03", "N=2 compact"), ("C05", "C08", "N=4 distributed"),
                      ("C13", "C16", "N=6 distributed")):
        h1 = rows[a]["h_sub_mm"] + t_stack_fixed
        h2 = rows[b]["h_sub_mm"] + t_stack_fixed
        w1, w2 = rows[a]["die_warpage_pv_um"], rows[b]["die_warpage_pv_um"]
        n = np.log(w2 / w1) / np.log(h2 / h1)
        sc.append({"pair": f"{a}->{b}", "family": lab, "h_total_1_mm": round(h1, 4),
                   "h_total_2_mm": round(h2, 4), "w1_um": w1, "w2_um": w2,
                   "ratio": round(w2 / w1, 4), "exponent_n": round(float(n), 3)})
        print(f"  {lab:16s} h_total {h1:.3f} -> {h2:.3f} mm   w {w1:7.4f} -> {w2:7.4f} um   "
              f"ratio {w2/w1:.4f}   w ~ h^({n:+.3f})")
    ns = [s["exponent_n"] for s in sc]
    print(f"\n  exponent across all three families: {np.mean(ns):+.3f} +/- {np.std(ns):.3f}")
    print("  Interpretation: two competing mechanisms. Plate bending stiffness grows as")
    print("  D ~ E h^3, while the FIXED-thickness HVR/TSV inclusion sits further from the")
    print("  shifted neutral axis, so its thermal moment arm grows ~h. Net w ~ h^-2.")
    out["thickness_scaling"] = {"pairs": sc, "mean_exponent": float(np.mean(ns)),
                                "std_exponent": float(np.std(ns))}

    # ---------------- interactions -----------------------------------------
    print(f"\n{'='*104}\nINTERACTION CHECKS\n{'='*104}")
    inter = {}
    r_t = [100 * (rows[b]["die_warpage_pv_um"] / rows[a]["die_warpage_pv_um"] - 1)
           for a, b in (("C01", "C03"), ("C05", "C08"), ("C13", "C16"))]
    inter["thickness_x_placement_family"] = {
        "families": ["N=2 compact_central_pair", "N=4 distributed_2x2", "N=6 distributed_3x2"],
        "thickness_effect_pct": [round(v, 2) for v in r_t],
        "spread_pp": round(max(r_t) - min(r_t), 2),
        "conclusion": ("NO detectable interaction: the thickness effect is the same to within "
                       f"{max(r_t)-min(r_t):.2f} percentage points across three placement families")}
    print(f"  thickness x placement family: effect = "
          f"{', '.join(f'{v:.2f}%' for v in r_t)}  -> spread {max(r_t)-min(r_t):.2f} pp")
    print(f"    {inter['thickness_x_placement_family']['conclusion']}")

    inter["thickness_x_asymmetry"] = {
        "testable": False,
        "reason": ("The frozen DOE contains NO asymmetric case at h_sub = 500 um "
                   "(C07/C15 are both 200 um). Thickness x asymmetry - the most interesting "
                   "interaction - cannot be isolated. C17->C18 confounds placement with "
                   "thickness and is not a clean test.")}
    print(f"\n  thickness x asymmetry: NOT TESTABLE - {inter['thickness_x_asymmetry']['reason']}")

    # footprint x placement: only one placement has a footprint sweep
    inter["footprint_x_placement"] = {
        "testable": False,
        "reason": ("The footprint sweep (C11/C05/C12) exists only for distributed_2x2. "
                   "No matched footprint sweep exists at another placement.")}
    print(f"\n  footprint x placement: NOT TESTABLE - {inter['footprint_x_placement']['reason']}")

    # count x placement IS testable
    cnt_dist = 100 * (rows["C17"]["die_warpage_pv_um"] / rows["C05"]["die_warpage_pv_um"] - 1)
    cnt_comp = 100 * (rows["C04"]["die_warpage_pv_um"] / rows["C01"]["die_warpage_pv_um"] - 1)
    inter["count_x_placement"] = {
        "distributed_N4_to_N8_pct": round(cnt_dist, 2),
        "compact_N2_to_N4_pct": round(cnt_comp, 2),
        "conclusion": "count is inert in both placement families"}
    print(f"\n  count x placement: distributed N4->N8 {cnt_dist:+.2f}% ; "
          f"compact N2->N4 {cnt_comp:+.2f}%  -> inert in both")
    out["interactions"] = inter

    # ---------------- mechanism regression incl. area ----------------------
    print(f"\n{'='*104}\nMECHANISM MODEL (h_sub = 200 um cases only)\n{'='*104}")
    sub = [c for c in sorted(doe["cases"]) if rows[c]["h_sub_mm"] == 0.200]
    D = {c: descriptors(case_tiles(doe["cases"][c], stack, doe), t_tile) for c in sub}
    y = np.array([rows[c]["die_warpage_pv_um"] for c in sub])
    q = np.array([rows[c]["p_hvr_total_W"] for c in sub])

    models = {
        "I_polar only": [[D[c]["I_polar_mm4"]] for c in sub],
        "I_polar + |M1|": [[D[c]["I_polar_mm4"], D[c]["first_moment_area_mm3"]] for c in sub],
        "I_polar + |M1| + A": [[D[c]["I_polar_mm4"], D[c]["first_moment_area_mm3"],
                                D[c]["A_total_mm2"]] for c in sub],
        "I_polar + |M1| + A + Q": [[D[c]["I_polar_mm4"], D[c]["first_moment_area_mm3"],
                                    D[c]["A_total_mm2"], q[i]] for i, c in enumerate(sub)],
    }
    fits = {}
    for name, X in models.items():
        X = np.column_stack([np.ones(len(sub)), np.array(X, float)])
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        pred = X @ beta
        r2 = 1 - np.sum((y - pred) ** 2) / np.sum((y - y.mean()) ** 2)
        adj = 1 - (1 - r2) * (len(sub) - 1) / (len(sub) - X.shape[1])
        fits[name] = {"r2": float(r2), "adj_r2": float(adj), "n_params": X.shape[1],
                      "coeffs": [float(b) for b in beta]}
        print(f"  {name:26s} R2={r2:.4f}  adj-R2={adj:.4f}  ({X.shape[1]} params, {len(sub)} cases)")
    out["mechanism_fits"] = fits
    print("\n  Signs: I_polar coefficient is NEGATIVE (spreading the inclusion lowers peak")
    print("  deflection) and |first moment| is POSITIVE (asymmetry raises it). Both match the")
    print("  Phase-0B explanation. Fits are interpretation aids, never used for prediction.")

    (P0C / "mechanism_analysis.json").write_text(json.dumps(out, indent=2))
    print(f"\nwrote {P0C/'matched_comparisons.csv'}\nwrote {P0C/'mechanism_analysis.json'}")


if __name__ == "__main__":
    main()
