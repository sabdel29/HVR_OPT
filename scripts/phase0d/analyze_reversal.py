#!/usr/bin/env python3
"""Phase-0D ET vs ETM ranking and the G1 architecture-reversal test.

Ranking is by Pareto dominance on the tuples frozen in ET_OBJECTIVE_DEFINITION.md:
    ET  : (P_elec_total, T_max)
    ETM : (P_elec_total, T_max, die_warpage_pv)
No scalarisation carries a claim; a lambda sweep is reported for sensitivity only.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
P0D = R / "results" / "phase0d"

ET_COLS = ["cand", "n_vr", "j_target", "h_sub_mm", "placement", "design", "arch_N", "arch_K",
           "arch_KA", "f_sw_MHz", "tile_side_mm", "a_hvr_per_vr_mm2", "a_hvr_total_mm2",
           "p_conv_total_w", "p_lateral_w", "p_tsv_w", "p_pdn_w", "p_elec_total_w",
           "efficiency_pct", "r_tsv_field_uohm", "n_via_per_vr", "T_max_C",
           "ripple_ok", "thermal_ok", "et_rank"]


def pareto_front(points) -> list[int]:
    """Indices of non-dominated points (all objectives minimised)."""
    pts = [tuple(float(v) for v in p) for p in points]
    out = []
    for i, a in enumerate(pts):
        dominated = False
        for j, b in enumerate(pts):
            if i == j:
                continue
            if all(bv <= av for av, bv in zip(a, b)) and any(bv < av for av, bv in zip(a, b)):
                dominated = True
                break
        if not dominated:
            out.append(i)
    return out


def load_candidates():
    rows = []
    for r in csv.DictReader((P0D / "coupled_candidates.csv").open()):
        if r.get("converged") != "True":
            continue
        for k, v in r.items():
            if k not in ("cand", "placement", "design", "converged", "ripple_ok", "thermal_ok"):
                try:
                    r[k] = float(v)
                except (TypeError, ValueError):
                    pass
        r["ripple_ok"] = r["ripple_ok"] == "True"
        r["thermal_ok"] = r["thermal_ok"] == "True"
        rows.append(r)
    return rows


def main():
    rows = load_candidates()
    feas = [r for r in rows if r["ripple_ok"] and r["thermal_ok"]]
    print(f"{len(rows)} converged candidates, {len(feas)} pass the ET feasibility filter "
          f"(ripple + T_max <= 100 C)\n")

    # ---------------- ET ranking (mechanics not consulted) --------------------
    feas.sort(key=lambda r: r["p_elec_total_w"])
    for i, r in enumerate(feas, 1):
        r["et_rank"] = i
    et_idx = pareto_front([(r["p_elec_total_w"], r["T_max_C"]) for r in feas])
    for i, r in enumerate(feas):
        r["et_pareto"] = i in et_idx

    with (P0D / "et_ranking.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=ET_COLS, extrasaction="ignore")
        w.writeheader(); w.writerows(feas)
    with (P0D / "pareto_et.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=ET_COLS, extrasaction="ignore")
        w.writeheader(); w.writerows([feas[i] for i in et_idx])

    print("=" * 118)
    print("ET-ONLY RANKING  (frozen objective: minimise P_elec_total; Pareto on "
          "(P_elec, T_max)). Mechanics NOT consulted.")
    print("=" * 118)
    hdr = (f"{'rk':>3s} {'cand':>5s} {'N':>2s} {'J':>4s} {'h_sub':>6s} {'placement':20s}"
           f"{'A_tot':>8s}{'P_conv':>8s}{'P_pdn':>7s}{'P_elec':>8s}{'eta %':>8s}{'T_max':>8s}{'ETp':>5s}")
    print(hdr); print("-" * len(hdr))
    for r in feas:
        print(f"{r['et_rank']:3d} {r['cand']:>5s} {int(r['n_vr']):2d} {r['j_target']:4g} "
              f"{r['h_sub_mm']*1000:5.0f}u {r['placement']:20s}{r['a_hvr_total_mm2']:8.1f}"
              f"{r['p_conv_total_w']:8.2f}{r['p_pdn_w']:7.2f}{r['p_elec_total_w']:8.2f}"
              f"{r['efficiency_pct']:8.3f}{r['T_max_C']:8.2f}{'  *' if r['et_pareto'] else '   ':>5s}")

    # ---------------- ETM ranking --------------------------------------------
    etm_idx = pareto_front([(r["p_elec_total_w"], r["T_max_C"], r["die_warpage_pv_um"])
                            for r in feas])
    for i, r in enumerate(feas):
        r["etm_pareto"] = i in etm_idx
    by_w = sorted(feas, key=lambda r: (r["die_warpage_pv_um"], r["p_elec_total_w"]))
    for i, r in enumerate(by_w, 1):
        r["etm_rank_warp"] = i

    etm_cols = ET_COLS + ["die_warpage_pv_um", "pkg_warpage_pv_um",
                          "interface_shear_p99_MPa", "etm_pareto", "etm_rank_warp"]
    with (P0D / "etm_ranking.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=etm_cols, extrasaction="ignore")
        w.writeheader(); w.writerows(feas)
    with (P0D / "pareto_etm.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=etm_cols, extrasaction="ignore")
        w.writeheader(); w.writerows([feas[i] for i in etm_idx])

    print(f"\n{'='*118}\nETM PARETO  (adds die warpage as a third objective)\n{'='*118}")
    print(f"{'cand':>5s} {'N':>2s} {'J':>4s} {'h_sub':>6s} {'placement':20s}"
          f"{'P_elec':>8s}{'T_max':>8s}{'warp um':>9s}{'ET rk':>7s}{'in ET front':>12s}")
    print("-" * 100)
    for i in sorted(etm_idx, key=lambda k: feas[k]["p_elec_total_w"]):
        r = feas[i]
        print(f"{r['cand']:>5s} {int(r['n_vr']):2d} {r['j_target']:4g} {r['h_sub_mm']*1000:5.0f}u "
              f"{r['placement']:20s}{r['p_elec_total_w']:8.2f}{r['T_max_C']:8.2f}"
              f"{r['die_warpage_pv_um']:9.3f}{r['et_rank']:7d}{str(r['et_pareto']):>12s}")

    # ---------------- G1 test -------------------------------------------------
    et_best = feas[0]
    etm_only = [feas[i] for i in etm_idx if not feas[i]["et_pareto"]]
    et_best_in_etm = et_best["etm_pareto"]

    def levels(rs, key):
        return sorted({r[key] for r in rs})

    et_front = [feas[i] for i in et_idx]
    etm_front = [feas[i] for i in etm_idx]
    lever_shift = {}
    for key in ("h_sub_mm", "j_target", "a_hvr_total_mm2", "placement", "n_vr"):
        lever_shift[key] = {"et_front": levels(et_front, key),
                            "etm_front": levels(etm_front, key),
                            "changed": levels(et_front, key) != levels(etm_front, key)}

    print(f"\n{'='*118}\nG1 ARCHITECTURE-REVERSAL TEST\n{'='*118}")
    print(f"  ET-optimal candidate           : {et_best['cand']}  "
          f"(N={int(et_best['n_vr'])}, J={et_best['j_target']:g}, "
          f"h_sub={et_best['h_sub_mm']*1000:.0f} um, {et_best['placement']}, "
          f"A={et_best['a_hvr_total_mm2']:.1f} mm2)")
    print(f"    P_elec {et_best['p_elec_total_w']:.2f} W, eta {et_best['efficiency_pct']:.3f} %, "
          f"T_max {et_best['T_max_C']:.2f} C, warpage {et_best['die_warpage_pv_um']:.3f} um")
    print(f"  ET-optimal still on the ETM Pareto front? {et_best_in_etm}")
    print(f"  candidates that JOIN the front only when warpage is included: "
          f"{[r['cand'] for r in etm_only]}")
    print(f"\n  Design-variable levels on each front:")
    for k, v in lever_shift.items():
        print(f"    {k:20s} ET {str(v['et_front']):38s} ETM {str(v['etm_front']):38s} "
              f"{'CHANGED' if v['changed'] else 'same'}")

    # ---------------- lambda sweep (sensitivity only) -------------------------
    print(f"\n{'='*118}\nSCALARISATION SENSITIVITY (reported for completeness; no claim "
          f"rests on any single lambda)\n{'='*118}")
    lam_rows = []
    p_span = max(r["p_elec_total_w"] for r in feas) - min(r["p_elec_total_w"] for r in feas)
    w_span = max(r["die_warpage_pv_um"] for r in feas) - min(r["die_warpage_pv_um"] for r in feas)
    print(f"  P_elec span {p_span:.2f} W, warpage span {w_span:.2f} um  ->  "
          f"lambda that equalises them = {p_span/w_span:.4f} W/um")
    for lam in (0.0, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0):
        best = min(feas, key=lambda r: r["p_elec_total_w"] + lam * r["die_warpage_pv_um"])
        lam_rows.append({"lambda_W_per_um": lam, "winner": best["cand"],
                         "n_vr": int(best["n_vr"]), "j_target": best["j_target"],
                         "h_sub_mm": best["h_sub_mm"], "placement": best["placement"],
                         "p_elec_total_w": best["p_elec_total_w"],
                         "die_warpage_pv_um": best["die_warpage_pv_um"]})
        print(f"    lambda={lam:5.2f} W/um -> {best['cand']}  N={int(best['n_vr'])} "
              f"J={best['j_target']:g} h={best['h_sub_mm']*1000:.0f}u {best['placement']:20s} "
              f"P={best['p_elec_total_w']:6.2f}W w={best['die_warpage_pv_um']:6.3f}um")
    switch = len({r["winner"] for r in lam_rows}) > 1

    out = {
        "n_candidates": len(rows), "n_feasible": len(feas),
        "et_best": {k: et_best[k] for k in
                    ("cand", "n_vr", "j_target", "h_sub_mm", "placement", "a_hvr_total_mm2",
                     "p_elec_total_w", "efficiency_pct", "T_max_C", "die_warpage_pv_um")},
        "et_pareto": [feas[i]["cand"] for i in et_idx],
        "etm_pareto": [feas[i]["cand"] for i in etm_idx],
        "et_best_remains_on_etm_front": bool(et_best_in_etm),
        "candidates_added_by_mechanics": [r["cand"] for r in etm_only],
        "lever_levels": lever_shift,
        "lambda_sweep": lam_rows,
        "winner_changes_with_lambda": bool(switch),
    }
    (P0D / "reversal_analysis.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"\nwrote {P0D/'et_ranking.csv'}, {P0D/'etm_ranking.csv'}, "
          f"{P0D/'pareto_et.csv'}, {P0D/'pareto_etm.csv'}, {P0D/'reversal_analysis.json'}")


if __name__ == "__main__":
    main()
