"""Task 1 -- is the maximum-displacement joint the critical one?

For every case (production S0/S1, cooling tiers A and B) the candidates are
  * every ball site on the Pareto front in (du, T): a site is dropped only if another site
    has BOTH a larger du AND a larger T_joint (strict in both, as the reviewer response
    states it);
  * the four package corners;
  * the current critical site (maximum du).
Each candidate is solved with the production local model at L0 with the production
settings -- the call final_closure_sensitivity._local_task makes (split load step, the
time study's first increment, block-order extraction) -- at the candidate's own (du, T).

The Pareto argument needs the response to be non-decreasing in du and in T. That is
tested, not assumed:
  (a) a regular (du, T) grid spanning every candidate (du 0.2-4.5 um, T 75-120 C);
  (b) every pair of computed points (all cases + grid) that is ordered in both du and T
      must be ordered in the response the same way; violations are counted.

    python tcpmt_solder_critical.py --run         solve (restartable)
    python tcpmt_solder_critical.py --summarize   write the 'critical_joint' section
"""
from __future__ import annotations

import itertools
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcpmt_solder_common as C                                     # noqa: E402

STUDY = "critical"
CASE_ORDER = ["Z1_S0", "Z2_S0", "Z3_S0", "Z1_S1", "Z2_S1", "A_Z3", "B_Z1", "B_Z2", "B_Z3"]
GRID_DU = (0.2, 0.5, 1.0, 1.5, 2.0, 3.0, 4.5)
GRID_T = (75.0, 90.0, 105.0, 120.0)
#: the published Phase-0I control joint (harness acceptance, policy amendments 3-6)
CONTROL = dict(du_um=C.LR.CONTROL["du_um"], T_C=C.LR.CONTROL["T_hot_C"])
CONTROL_PASS5 = 0.00651488542578123          # local_mesh_study.json acceptance, same settings


def strict_front(sites):
    return [s for s in sites
            if not any(o["du_um"] > s["du_um"] and o["T_C"] > s["T_C"] for o in sites)]


def candidates(case):
    rk = C.ranked(case)
    xm = max(abs(s["x_mm"]) for s in rk)
    ym = max(abs(s["y_mm"]) for s in rk)
    crit = C.critical(case)
    out = {}

    def add(s, role):
        k = (round(s["x_mm"], 4), round(s["y_mm"], 4))
        out.setdefault(k, {"x_mm": s["x_mm"], "y_mm": s["y_mm"], "du_um": s["du_um"],
                           "T_C": s["T_C"], "rank_by_du": s["rank"], "roles": []})
        if role not in out[k]["roles"]:
            out[k]["roles"].append(role)

    for s in strict_front(rk):
        add(s, "pareto")
    for s in rk:
        if abs(abs(s["x_mm"]) - xm) < 1e-9 and abs(abs(s["y_mm"]) - ym) < 1e-9:
            add(s, "corner")
    add(dict(crit, rank=1), "max_du")
    return sorted(out.values(), key=lambda c: -c["du_um"]), len(rk)


def tag(case, c):
    return f"{case}_x{c['x_mm']:+06.2f}_y{c['y_mm']:+06.2f}"


def tasks():
    t = [dict(study=STUDY, tag="CONTROL", meta={"role": "harness control"}, **CONTROL)]
    for case in CASE_ORDER:                                   # critical sites first
        cands, _ = candidates(case)
        cands = sorted(cands, key=lambda c: "max_du" not in c["roles"])
        for c in cands:
            t.append(dict(study=STUDY, tag=tag(case, c), du_um=c["du_um"], T_C=c["T_C"],
                          meta={"case": case, "x_mm": c["x_mm"], "y_mm": c["y_mm"],
                                "roles": c["roles"]}))
    for du in GRID_DU:
        for T in GRID_T:
            t.append(dict(study=STUDY, tag=f"GRID_du{du:.2f}_T{T:.0f}", du_um=du, T_C=T,
                          meta={"role": "monotonicity grid"}))
    # critical sites of every case first, then the grid, then the rest of the fronts
    key = {"CONTROL": 0}
    for x in t:
        r = (x.get("meta") or {}).get("roles") or []
        key.setdefault(x["tag"], 1 if "max_du" in r else (2 if x["tag"].startswith("GRID")
                                                          else 3))
    return sorted(t, key=lambda x: key[x["tag"]])


def summarize():
    recs = C.load_records(STUDY)
    out = {"what": "critical-joint verification (task 1)",
           "settings": {"level": "L0", "first_increment_s": C.INC0, "split_steps": True,
                        "n_cycles": 4, "band_frac": C.BAND_PROD,
                        "procedure": "final_closure_local_mesh._solve, as "
                                     "final_closure_sensitivity._local_task"},
           "candidate_rule": "Pareto front in (du, T): a site is dropped only if another site "
                             "has both a strictly larger du and a strictly larger T_joint; "
                             "plus the four corners and the current critical (max-du) site",
           "cases": {}}
    ctl = recs.get("CONTROL")
    if ctl:
        v = ctl.get("d_peeq_per_cycle")
        out["harness_control"] = {"value": v, "pass5_value": CONTROL_PASS5,
                                  "dev_rel": (v - CONTROL_PASS5) / CONTROL_PASS5 if v else None,
                                  "published_phase0i": C.LR.CONTROL["d_eps_in_stab"]}
    pts = []
    for case in CASE_ORDER:
        cands, n_sites = candidates(case)
        rows = []
        for c in cands:
            r = recs.get(tag(case, c)) or {}
            rows.append(dict(c, d_eps=r.get("d_peeq_per_cycle"), error=r.get("error"),
                             per_cycle=r.get("per_cycle"), wall_s=r.get("wall_s")))
        done = [r for r in rows if r["d_eps"] is not None]
        crit = next(r for r in rows if "max_du" in r["roles"])
        best = max(done, key=lambda r: r["d_eps"]) if done else None
        others = [r for r in done if r is not crit]
        second = max(others, key=lambda r: r["d_eps"]) if others else None
        inner = [r for r in others if "corner" not in r["roles"]]
        best_inner = max(inner, key=lambda r: r["d_eps"]) if inner else None
        out["cases"][case] = {
            "case_file": C.rel(C.CASES[case]), "n_sites": n_sites,
            "n_candidates": len(rows), "n_solved": len(done),
            "n_pareto": sum("pareto" in r["roles"] for r in rows),
            "max_du_site": {k: crit[k] for k in ("x_mm", "y_mm", "du_um", "T_C", "d_eps")},
            "max_response_site": ({k: best[k] for k in ("x_mm", "y_mm", "du_um", "T_C",
                                                        "d_eps", "roles")} if best else None),
            "critical_is_max_du": (best is crit) if (best and crit["d_eps"] is not None)
                                  else None,
            "runner_up": ({k: second[k] for k in ("x_mm", "y_mm", "du_um", "T_C", "d_eps",
                                                  "roles")} if second else None),
            "margin_rel": ((crit["d_eps"] - second["d_eps"]) / crit["d_eps"]
                           if (second and crit["d_eps"]) else None),
            "best_non_corner_front_site": ({k: best_inner[k] for k in
                                            ("x_mm", "y_mm", "du_um", "T_C", "d_eps", "roles")}
                                           if best_inner else None),
            "margin_vs_non_corner_rel": ((crit["d_eps"] - best_inner["d_eps"]) / crit["d_eps"]
                                         if (best_inner and crit["d_eps"]) else None),
            "candidates": rows}
        pts += [dict(r, case=case) for r in done]
    grid = []
    for du in GRID_DU:
        for T in GRID_T:
            r = recs.get(f"GRID_du{du:.2f}_T{T:.0f}") or {}
            grid.append({"du_um": du, "T_C": T, "d_eps": r.get("d_peeq_per_cycle"),
                         "error": r.get("error")})
    out["grid"] = {"du_um": list(GRID_DU), "T_C": list(GRID_T), "points": grid}
    gv = {(g["du_um"], g["T_C"]): g["d_eps"] for g in grid}
    d_du = [gv[(b, T)] / gv[(a, T)] for T in GRID_T for a, b in zip(GRID_DU, GRID_DU[1:])
            if gv.get((a, T)) and gv.get((b, T))]
    d_T = [gv[(du, b)] / gv[(du, a)] for du in GRID_DU for a, b in zip(GRID_T, GRID_T[1:])
           if gv.get((du, a)) and gv.get((du, b))]
    # local log-sensitivities on the grid (central where possible)
    out["grid"]["min_ratio_along_du"] = min(d_du) if d_du else None
    out["grid"]["min_ratio_along_T"] = min(d_T) if d_T else None
    out["grid"]["monotone_in_du"] = bool(d_du) and min(d_du) > 1.0
    out["grid"]["monotone_in_T"] = bool(d_T) and min(d_T) > 1.0
    el_du, el_T = [], []
    for T in GRID_T:
        for a, b in zip(GRID_DU, GRID_DU[1:]):
            if gv.get((a, T)) and gv.get((b, T)):
                el_du.append(math.log(gv[(b, T)] / gv[(a, T)]) / math.log(b / a))
    for du in GRID_DU:
        for a, b in zip(GRID_T, GRID_T[1:]):
            if gv.get((du, a)) and gv.get((du, b)):
                el_T.append(math.log(gv[(du, b)] / gv[(du, a)]) / (b - a))
    out["grid"]["dlnf_dlndu_range"] = [min(el_du), max(el_du)] if el_du else None
    out["grid"]["dlnf_dT_per_K_range"] = [min(el_T), max(el_T)] if el_T else None
    allp = pts + [dict(g, case="GRID") for g in grid if g["d_eps"]]
    n_pair = n_bad = n_bad_big = 0
    worst = None
    for p, q in itertools.permutations(allp, 2):
        if p["du_um"] >= q["du_um"] and p["T_C"] >= q["T_C"] and \
                (p["du_um"] > q["du_um"] or p["T_C"] > q["T_C"]):
            n_pair += 1
            if p["d_eps"] < q["d_eps"]:
                n_bad += 1
                d = (q["d_eps"] - p["d_eps"]) / q["d_eps"]
                n_bad_big += d > 1e-3
                if worst is None or d > worst["rel"]:
                    worst = {"rel": d, "higher": {k: p[k] for k in ("case", "du_um", "T_C",
                                                                    "d_eps")},
                             "lower": {k: q[k] for k in ("case", "du_um", "T_C", "d_eps")}}
    out["monotonicity_pairs"] = {
        "test": "for every pair of computed points (all candidates of all cases and the grid) "
                "with du_p >= du_q and T_p >= T_q (one strict), d_eps_p >= d_eps_q",
        "n_points": len(allp), "n_ordered_pairs": n_pair, "n_violations": n_bad,
        "n_violations_above_0p1pct": n_bad_big, "worst_violation": worst}
    out["all_max_du"] = all(c["critical_is_max_du"] for c in out["cases"].values()
                            if c["critical_is_max_du"] is not None)
    return out


def main():
    if "--run" in sys.argv:
        C.run_tasks(tasks())
    if "--summarize" in sys.argv:
        from tcpmt_solder_collect import merge
        s = summarize()
        merge("critical_joint", s)
        for k, c in s["cases"].items():
            b = c["max_response_site"]
            print(f"{k}: {c['n_solved']}/{c['n_candidates']} solved; max d_eps at "
                  f"({b['x_mm']}, {b['y_mm']}) = {b['d_eps']:.4e}; is max-du: "
                  f"{c['critical_is_max_du']}; margin {c['margin_rel']}")
        print("pairs:", s["monotonicity_pairs"]["n_ordered_pairs"], "violations:",
              s["monotonicity_pairs"]["n_violations"])
    if "--list" in sys.argv:
        for case in CASE_ORDER:
            cands, n = candidates(case)
            print(case, n, len(cands), sum("pareto" in c["roles"] for c in cands))


if __name__ == "__main__":
    main()
