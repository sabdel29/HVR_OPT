"""Finding 2 -- the critical-joint check redone with the v2 local model.

With the full cut-boundary transfer the joint response is no longer a function of (|du_xy|,
T) alone: du_z, the relative tilt of the two faces and their in-plane stretch enter too, so
the Pareto argument of round 2 does not cover the candidates any more. Each case therefore
solves, with the production v2 model (production law at its converged window, global
kinematics, ramped loading):
  * the top N sites by |du_xy|, by |relative tilt| and by |eps_z|,
  * the strict Pareto front in (|du_xy|, T), and the four corners
(tcpmt_mech_kinematics.candidate_sites, stored with every case). The question answered per
case: is the maximum-|du_xy| joint the maximum-response joint, and by what margin?

    python tcpmt_mech_critical.py --run [--top N] [CASE ...]
    python tcpmt_mech_critical.py --summarize   -> research/tcpmt_revision/solder_critical_v2.json
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcpmt_mech_kinematics as KIN                                 # noqa: E402
import tcpmt_mech_submodel as SUB                                   # noqa: E402
import tcpmt_mech_laws as LAW                                       # noqa: E402

import tcpmt_mech_production as MP                                 # noqa: E402

#: TCPMT round 3 (campaign): the compared cases of the local model's state -- the production
#: state of the design in force by default (tcpmt_mech_production.LOCAL_STATE)
STATE = MP.LOCAL_STATE
_SFX = "" if STATE == "SDEC" else f"_{STATE}"
STUDY = "critical_v2" + _SFX
OUT = LAW.TR / f"solder_critical_v2{_SFX}.json"
ROUND2_ORDER = ["Z1_S0", "Z2_S0", "Z3_S0", "Z1_S1", "Z2_S1", "A_Z3", "B_Z1", "B_Z2", "B_Z3",
                "A_Z3land", "B_Z3land"]
CASE_ORDER = ROUND2_ORDER if STATE == "round2" else MP.labels(STATE)


def mirror_of(a, b, tol=1e-6):
    """Site a is a mirror image of site b (|x| and |y| swapped or reflected)."""
    sa = sorted((abs(a["x_mm"]), abs(a["y_mm"])))
    sb = sorted((abs(b["x_mm"]), abs(b["y_mm"])))
    return abs(sa[0] - sb[0]) < tol and abs(sa[1] - sb[1]) < tol


def pareto_front(rows):
    """Strict Pareto front in (|du_xy|, T): no other site is larger in both."""
    return [r for r in rows if not any(o["du_xy_um"] > r["du_xy_um"] and o["T_C"] > r["T_C"]
                                       for o in rows)]


def monotonicity(rows):
    """Finding 2, the round-2 argument tested under the new boundary conditions: if the
    response were monotone in (|du_xy|, T), the critical joint would lie on the Pareto front
    and a site dominated in both would never respond more. Over every ordered pair of solved
    sites where one dominates the other in both (>=, one strictly), count the pairs whose
    responses are ordered the other way, and the largest such excess."""
    done = [r for r in rows if r.get("d_eps") is not None]
    n = nv = nv1 = 0
    worst = None
    for a in done:
        for b in done:
            if a is b or mirror_of(a, b):         # mirror twins: one site
                continue
            if a["du_xy_um"] >= b["du_xy_um"] and a["T_C"] >= b["T_C"] and (
                    a["du_xy_um"] > b["du_xy_um"] or a["T_C"] > b["T_C"]):
                n += 1
                if b["d_eps"] > a["d_eps"]:
                    nv += 1
                    x = b["d_eps"] / a["d_eps"] - 1.0
                    nv1 += x > 0.01
                    if worst is None or x > worst["excess_rel"]:
                        worst = {"excess_rel": x, "dominating": [a["x_mm"], a["y_mm"]],
                                 "dominated": [b["x_mm"], b["y_mm"]]}
    front = pareto_front(done)
    best = max(done, key=lambda r: r["d_eps"]) if done else None
    return {"n_ordered_pairs": n, "n_violations": nv, "n_violations_over_1pct": nv1,
            "worst_violation": worst,
            "n_pareto_solved": len(front),
            "max_response_on_pareto_front": (best in front) if best else None,
            "rule": "a site at least as large in both |du_xy| and T must respond at least as "
                    "much (pairs over every solved candidate; mirror twins are one site)"}


def candidates(case, n_top):
    kin = KIN.load_kinematics(case)
    if not kin:
        return None
    allc = KIN.expand_sites(kin["interconnects"]["bga"]["candidates"])
    for k in allc:
        Gb, Gt = k["G_bot"], k["G_top"]
        k["tilt_rel"] = [Gt[2][0] - Gb[2][0], Gt[2][1] - Gb[2][1]]
    return KIN.candidate_sites(allc, n_top)


def tag(case, k):
    return f"{case}_x{k['x_mm']:+06.2f}_y{k['y_mm']:+06.2f}"


def tasks(cases, n_top):
    out = []
    for case in cases:
        cand = candidates(case, n_top)
        if not cand:
            continue
        top = max(cand, key=lambda k: k["du_xy_um"])
        for k in sorted(cand, key=lambda k: k is not top):
            out.append(dict(study=STUDY, tag=tag(case, k), kin=k,
                            meta={"case": case, "x_mm": k["x_mm"], "y_mm": k["y_mm"],
                                  "max_du": k is top}))
    return out


def summarize(n_top):
    recs = SUB.load_records(STUDY)
    prod = LAW.solder_cfg()["production_law"]
    out = {"what": "critical-joint check, v2 local model (finding 2)",
           "state": STATE,
           "model": {k: SUB.lcfg()[k] for k in ("bc_mode", "ramp_s", "dwell_s", "n_cycles",
                                                 "element", "level")},
           "law": prod,
           "window_status": LAW.stored_window(prod)[1],
           "window_MPa": LAW.stored_window(prod)[0],
           "card_sha": LAW.card_sha(LAW.card(prod, LAW.stored_window(prod)[0])[0]),
           "candidate_rule": f"top {n_top} by |du_xy|, by |relative tilt|, by |eps_z| and by "
                             "the deforming du, the strict Pareto front in (|du_xy|, T) and "
                             "the four corners, over every evaluated lattice site",
           "inputs_sha1": {}, "cases": {}}
    # the card it was solved with is recorded by its hash (card_sha): pass 2 of the law band
    # re-stores the window afterwards by design, which must not make this check stale
    n_tot = n_ok = 0
    for case in CASE_ORDER:
        cand = candidates(case, n_top)
        if not cand:
            continue
        rows = []
        for k in cand:
            r = recs.get(tag(case, k)) or {}
            # a record solved with another card or other kinematics is not this check's
            fresh = bool(r) and r.get("card_sha") == out["card_sha"] and abs(
                ((r.get("kin") or {}).get("du_xy_um") or -1.0) - k["du_xy_um"]) < 1e-9
            rows.append({"x_mm": k["x_mm"], "y_mm": k["y_mm"], "du_xy_um": k["du_xy_um"],
                         "du_z_um": k["du_z_um"], "T_C": SUB.site_temperature(k),
                         "du_def_xy_um": k.get("du_def_xy_um"),
                         "tilt_rel": k["tilt_rel"],
                         "d_eps": r.get("d_peeq_per_cycle") if fresh else None,
                         "error": (r.get("error") if fresh else
                                   ("stale record (other card or kinematics)" if r else
                                    "not solved"))})
        done = [r for r in rows if r["d_eps"] is not None]
        if not done:
            continue
        top = max(rows, key=lambda r: r["du_xy_um"])
        best = max(done, key=lambda r: r["d_eps"])
        # a mirror image of the maximum-du site (the package is mirror-symmetric: the same
        # site up to the solution's own asymmetry) is that site, not another critical joint
        twin = best is not top and mirror_of(best, top)
        if twin:
            best = top if top["d_eps"] is not None else best
        others = [r for r in done if r is not top and not mirror_of(r, top)]
        second = max(others, key=lambda r: r["d_eps"]) if others else None
        n_tot += 1
        is_max = top["d_eps"] is not None and best is top
        n_ok += bool(is_max)
        kin = KIN.load_kinematics(case) or {}
        out["inputs_sha1"].update(kin.get("inputs_sha1") or {})
        stale = [r["error"] for r in rows if r.get("error")]
        out["cases"][case] = {
            "case_file": kin.get("case_file"), "case_sha1": kin.get("case_sha1"),
            "site_coverage": kin.get("site_coverage"),
            "n_candidates": len(rows), "n_solved": len(done), "n_failed": len(stale),
            "monotonicity": monotonicity(rows),
            "max_du_site": top, "max_response_site": best,
            "mirror_twin_of_max_du_responded_more": bool(twin),
            "critical_is_max_du": is_max if top["d_eps"] is not None else None,
            "margin_rel": ((top["d_eps"] - second["d_eps"]) / top["d_eps"]
                           if (second and top["d_eps"]) else None),
            "max_response_over_max_du": (best["d_eps"] / top["d_eps"]
                                         if top["d_eps"] else None),
            "candidates": rows}
    out["all_max_du"] = (n_ok == n_tot) if n_tot else None
    out["n_cases"] = n_tot
    OUT.write_text(json.dumps(out, indent=1, default=float) + "\n")
    return out


def main():
    n_top = 30
    if "--top" in sys.argv:
        n_top = int(sys.argv[sys.argv.index("--top") + 1])
    cases = [a for a in sys.argv[1:] if a in KIN.CASES] or CASE_ORDER
    if "--run" in sys.argv:
        SUB.run_tasks(tasks(cases, n_top))
    if "--summarize" in sys.argv:
        s = summarize(n_top)
        for k, c in s["cases"].items():
            b = c["max_response_site"]
            print(f"{k}: {c['n_solved']}/{c['n_candidates']}; max d_eps at ({b['x_mm']}, "
                  f"{b['y_mm']}) = {b['d_eps']:.4e}; is max-du: {c['critical_is_max_du']}; "
                  f"ratio {c['max_response_over_max_du']}")
        print("all max-du:", s["all_max_du"])


if __name__ == "__main__":
    main()
