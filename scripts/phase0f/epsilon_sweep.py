#!/usr/bin/env python3
"""Phase-0F Sec.10: PARAMETRIC CONSTRAINT SENSITIVITY (not feasibility).

No source-backed mechanical criterion was found (see PHASE0F_1KW_ETM_GATE.md Sec. 10 for the
search record), so none is invented. Instead the question is inverted: for a hypothetical
limit eps on the mechanical response, at what value of eps would the electrically optimal
1-kW candidate FIRST be excluded, and what would it cost to comply?

This is labelled PARAMETRIC CONSTRAINT SENSITIVITY throughout. It is not a feasibility result
and it does not license any reliability claim.
"""
from __future__ import annotations
import csv, json, sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0f"


def load_candidates():
    rows = []
    for r in csv.DictReader(open(OUT / "1kw_candidates.csv")):
        if str(r.get("feasible")).lower() not in ("true", "1"):
            continue
        try:
            rows.append({**r, "P_elec_total_w": float(r["P_elec_total_w"]),
                         "die_warpage_pv_um": float(r["die_warpage_pv_um"]),
                         "T_max_C": float(r["T_max_C"]),
                         "h_sub_mm": float(r["h_sub_mm"])})
        except (KeyError, ValueError):
            continue
    return rows


def main():
    cands = load_candidates()
    if not cands:
        print("no feasible candidates yet"); return
    metric = "die_warpage_pv_um"
    et_opt = min(cands, key=lambda r: r["P_elec_total_w"])
    print(f"{len(cands)} feasible 1-kW candidates")
    print(f"ET optimum: {et_opt['group']}/{et_opt['arch']}/{et_opt['fam']} "
          f"h={et_opt['h_sub_mm']} -> P_elec={et_opt['P_elec_total_w']:.3f} W, "
          f"warpage={et_opt[metric]:.3f} um")
    w = sorted(r[metric] for r in cands)
    print(f"warpage across candidates: {w[0]:.3f} .. {w[-1]:.3f} um")

    eps_grid = sorted(set([round(x, 4) for x in np.concatenate([
        np.linspace(w[0] * 0.5, w[-1] * 1.2, 60), np.array(w)])]))
    rows = []
    first_excl = None
    for eps in eps_grid:
        ok = [r for r in cands if r[metric] <= eps]
        et_ok = et_opt[metric] <= eps
        best = min(ok, key=lambda r: r["P_elec_total_w"]) if ok else None
        pen = (best["P_elec_total_w"] - et_opt["P_elec_total_w"]) if best else float("nan")
        rows.append({"epsilon_um": eps, "n_feasible": len(ok),
                     "et_optimum_admissible": et_ok,
                     "best_admissible_P_elec_w": best["P_elec_total_w"] if best else None,
                     "penalty_w": pen,
                     "penalty_pct": 100 * pen / et_opt["P_elec_total_w"] if best else None,
                     "best_admissible_case": (f"{best['group']}/{best['arch']}/{best['fam']}"
                                              f"/h{best['h_sub_mm']}") if best else None,
                     "best_admissible_warpage_um": best[metric] if best else None})
        if not et_ok and first_excl is None:
            first_excl = eps
    with open(OUT / "mechanical_epsilon_sweep.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)

    print(f"\nThe ET optimum is excluded once eps < {et_opt[metric]:.3f} um.")
    print(f"{'eps (um)':>10s} {'n_ok':>5s} {'ET opt ok?':>11s} {'penalty (W)':>12s} "
          f"{'penalty %':>10s}  best admissible")
    for eps in (w[-1], et_opt[metric] * 1.001, et_opt[metric] * 0.999,
                np.median(w), w[0] * 1.001, w[0] * 0.999):
        r = min(rows, key=lambda q: abs(q["epsilon_um"] - eps))
        print(f"{r['epsilon_um']:10.3f} {r['n_feasible']:5d} "
              f"{str(r['et_optimum_admissible']):>11s} "
              f"{(r['penalty_w'] if r['penalty_w'] == r['penalty_w'] else float('nan')):12.4f} "
              f"{(r['penalty_pct'] if r['penalty_pct'] is not None else float('nan')):10.4f}  "
              f"{r['best_admissible_case']}")
    print(f"\nwrote {OUT/'mechanical_epsilon_sweep.csv'}")


if __name__ == "__main__":
    main()
