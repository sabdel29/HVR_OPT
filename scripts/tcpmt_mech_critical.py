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

STUDY = "critical_v2"
OUT = LAW.TR / "solder_critical_v2.json"
CASE_ORDER = ["Z1_S0", "Z2_S0", "Z3_S0", "Z1_S1", "Z2_S1", "A_Z3", "B_Z1", "B_Z2", "B_Z3",
              "A_Z3land", "B_Z3land"]


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
    out = {"what": "critical-joint check, v2 local model (finding 2)",
           "model": {k: SUB.lcfg()[k] for k in ("bc_mode", "ramp_s", "dwell_s", "n_cycles",
                                                 "element", "level")},
           "law": LAW.solder_cfg()["production_law"],
           "window_status": LAW.stored_window(LAW.solder_cfg()["production_law"])[1],
           "candidate_rule": f"top {n_top} by |du_xy|, by |relative tilt| and by |eps_z|, the "
                             "strict Pareto front in (|du_xy|, T) and the four corners",
           "cases": {}}
    n_tot = n_ok = 0
    for case in CASE_ORDER:
        cand = candidates(case, n_top)
        if not cand:
            continue
        rows = []
        for k in cand:
            r = recs.get(tag(case, k)) or {}
            rows.append({"x_mm": k["x_mm"], "y_mm": k["y_mm"], "du_xy_um": k["du_xy_um"],
                         "du_z_um": k["du_z_um"], "T_C": SUB.site_temperature(k),
                         "tilt_rel": k["tilt_rel"], "d_eps": r.get("d_peeq_per_cycle"),
                         "error": r.get("error")})
        done = [r for r in rows if r["d_eps"] is not None]
        if not done:
            continue
        top = max(rows, key=lambda r: r["du_xy_um"])
        best = max(done, key=lambda r: r["d_eps"])
        others = [r for r in done if r is not top]
        second = max(others, key=lambda r: r["d_eps"]) if others else None
        n_tot += 1
        is_max = top["d_eps"] is not None and best is top
        n_ok += bool(is_max)
        out["cases"][case] = {
            "n_candidates": len(rows), "n_solved": len(done),
            "max_du_site": top, "max_response_site": best,
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
