#!/usr/bin/env python3
"""TCPMT round 3 -- the designs of the design record compared through the chain.

    python tcpmt_design_comparison.py            -> tcpmt_revision/design_comparison.json
    python tcpmt_design_comparison.py kcheck     -> tcpmt_revision/k_check.json
    python tcpmt_design_comparison.py commit-k   -> research/tcpmt_revision/decoupling_by_design.json

compare  the production state (implemented decoupling) of every design the campaign ran:
         the production m36 (campaign root), the 5-tier co-design comparison m36t5, the
         thin-capacitor sensitivity m36thin and the count neighbours m25 / m49 (design
         subroots <root>/designs/<key>). For each integration and cooling: package loss,
         peak and die temperature, convergence and energy residual; then the COUNT RANKING
         through the chain (Z1, both coolings) against the screen's ranking (the DSE's P_total
         at 25 C, design record entry `screen`).
kcheck   the k_eq the campaign's own decoupling chain derived (input_decoupling.json summary)
         against the committed production k the package network was closed at (the design
         record's `decoupling` block); |delta| above K_TOL flags a re-closure.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
for _p in ("scripts/phase0nw", "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))
import design_record as DR                                          # noqa: E402

ROOT = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research")
K_TOL = 0.02
ARCHS, TIERS = ("Z1", "Z2", "Z3"), ("A", "B")


def design_root(key):
    """The results root of a design: the campaign root for the production design, its
    subroot otherwise (a campaign subroot when ETM_RESULTS_ROOT is a design subroot)."""
    base = ROOT
    if base.parent.name == "designs":
        base = base.parent.parent
    return base if key == DR.production_key() else base / "designs" / key


def case_file(key, arch, tier):
    return (design_root(key) / "final_closure" / "sensitivity" /
            f"etm_{arch}_HV_SDEC__sdec_{tier}.json")


def summary(path):
    if not path.is_file():
        return None
    c = json.loads(path.read_text())
    th = c.get("thermal") or {}
    me = c.get("mechanics") or {}
    crit = (me.get("joint_search") or {}).get("critical") or {}
    return {"file": str(path), "P_loss_W": c.get("P_loss_w"), "T_max_C": th.get("T_max_C"),
            "die_T_max_C": c.get("die_T_max_C"), "et_converged": c.get("et_converged"),
            "energy_residual_rel": th.get("energy_residual_rel"),
            "die_warpage_pv_um": me.get("die_warpage_pv_um"), "du_c_um": crit.get("du_um"),
            "design": (c.get("design") or {}).get("design")}


def joint_band(key):
    """{'<tier>_<arch>': joint response of the design's own v2 law band} (the production law at
    its own maximum over the BGA lattice and every other law at its own; the band's file in
    the design's results root), or {} when the design has none."""
    f = design_root(key) / "tcpmt_revision" / "solder_law_band.json"
    if not f.is_file():
        return {}
    b = json.loads(f.read_text())
    out = {}
    for lab, r in (b.get("band") or {}).items():
        if not r.get("complete"):
            continue
        site = (b.get("joints") or {}).get(lab) or {}
        out[lab] = {"production": r["production"], "min": r["min"], "max": r["max"],
                    "values": r["values"], "same_site_all_laws": r.get("same_site_all_laws"),
                    "site_mm": [site.get("x_mm"), site.get("y_mm")], "T_C": site.get("T_C"),
                    "du_def_xy_um": site.get("du_def_xy_um"),
                    "all_verified": b.get("all_verified"),
                    "production_law": b.get("production_law")}
    return out


def count_joints(out):
    """The joint response of the count neighbours against the production count (Z1, each
    cooling) under THE rule: D = y_b - y_a resolved when |D| > U95(D) under EVERY law of the
    band (tcpmt_resolution.law_band); U95 from each joint's numerical U of the local model
    (the production joints' own L0 -> L3 and 4 -> 8 cycle changes, transferred to the
    neighbours' joints, which run the same local model)."""
    try:
        import tcpmt_resolution as RULE
        import tcpmt_uncertainty as TU
        _eps, u_t, _own, _basis, _band = TU.local_u()
    except Exception as e:                        # recorded, never silent
        return {"error": str(e)[-300:]}
    prod = DR.production_key()
    res = {}
    for t in TIERS:
        u = u_t.get((t, "Z1"))
        rows = {k: (d.get("joints") or {}).get(f"{t}_Z1") for k, d in out["designs"].items()
                if DR.get(k)["role"] in ("production", "count neighbour")}
        if None in rows.values() or u is None:
            res[t] = {"complete": False}
            continue
        laws = sorted(set.intersection(*(set(r["values"]) for r in rows.values())))
        pairs = {}
        for k, r in rows.items():
            if k == prod:
                continue
            p0 = rows[prod]
            per = {law: (r["values"][law] - p0["values"][law],
                         RULE.quad(u * p0["values"][law], u * r["values"][law]))
                   for law in laws}
            lb = RULE.law_band(per, p0["production_law"])
            pairs[k] = {"D_production": r["production"] - p0["production"],
                        "ratio_production": r["production"] / p0["production"],
                        "verdict": lb.get("verdict"),
                        "lower": prod if r["production"] > p0["production"] else k,
                        "sign_changes": lb.get("sign_changes")}
        order = {law: [k for k, _r in sorted(rows.items(), key=lambda kv: kv[1]["values"][law])]
                 for law in laws}
        res[t] = {"complete": True, "U_rel": u, "laws": laws, "order_by_law": order,
                  "same_order_all_laws": len({tuple(v) for v in order.values()}) == 1,
                  "pairs_vs_production": pairs}
    return res


def compare():
    out = {"what": __doc__.split("\n\n")[1].strip(), "designs": {}, "ranking": {}}
    for key in DR.keys():
        e = DR.get(key)
        rec = {"role": e["role"], "tag": e["tag"], "n_vr": e["n_vr"],
               "screen_P_total_W": e["screen"]["P_total_W"],
               "screen_conv_W": e["screen"]["conv_total_W"],
               "conversion_25C_W": e["conversion_25C_W"],
               "converter_stack_um": e.get("converter_stack_um"), "cases": {}}
        for a in ARCHS:
            for t in TIERS:
                s = summary(case_file(key, a, t))
                if s:
                    rec["cases"][f"{a}_{t}"] = s
        rec["joints"] = joint_band(key)
        out["designs"][key] = rec
    for t in TIERS:
        rows = [(k, d["n_vr"], d["screen_P_total_W"], (d["cases"].get(f"Z1_{t}") or {})
                 .get("P_loss_W")) for k, d in out["designs"].items()
                if DR.get(k)["role"] in ("production", "count neighbour")]
        have = [r for r in rows if r[3] is not None]
        screen_rank = [r[0] for r in sorted(rows, key=lambda r: r[2])]
        chain_rank = [r[0] for r in sorted(have, key=lambda r: r[3])]
        out["ranking"][f"Z1_{t}"] = {
            "screen_order_by_P_total": screen_rank, "chain_order_by_P_loss": chain_rank,
            "complete": len(have) == len(rows),
            "same_ranking": bool(len(have) == len(rows) and screen_rank == chain_rank),
            "rows": [{"design": k, "M": m, "screen_P_total_W": ps, "chain_P_loss_W": pc}
                     for k, m, ps, pc in rows]}
    out["count_joints"] = count_joints(out)
    f = ROOT / "tcpmt_revision" / "design_comparison.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(out, indent=1, default=float) + "\n")
    print(json.dumps({"ranking": out["ranking"], "count_joints": out["count_joints"]},
                     indent=1, default=float))
    return out


def kcheck():
    e = DR.get()
    committed = (e.get("decoupling") or {}).get("k_eq")
    f = ROOT / "tcpmt_revision" / "input_decoupling.json"
    derived = None
    if f.is_file():
        rec = (json.loads(f.read_text()).get("summary") or {}).get("recommended") or {}
        derived = rec.get("k_eq")
    out = {"design": DR.name(), "k_eq_committed": committed, "k_eq_derived": derived,
           "tolerance": K_TOL,
           "delta": (derived - committed) if (derived is not None and committed) else None}
    out["within_tolerance"] = (out["delta"] is not None and abs(out["delta"]) <= K_TOL)
    out["note"] = ("the package network was closed at k_eq_committed (configs/design_points."
                   "yaml decoupling); a delta beyond the tolerance means the BGA count must be "
                   "re-closed at the derived k (final_closure_pkg_network.py)")
    g = ROOT / "tcpmt_revision" / "k_check.json"
    g.parent.mkdir(parents=True, exist_ok=True)
    g.write_text(json.dumps(out, indent=1, default=float) + "\n")
    print(json.dumps(out, indent=1, default=float))
    return out


DECOUPLING_FILE = R / "research" / "tcpmt_revision" / "decoupling_by_design.json"


def commit_k():
    """Record the decoupling chain's result for the design in force (the results root's
    input_decoupling.json and package_network.json) in research/tcpmt_revision/
    decoupling_by_design.json, the generator's source of each design's committed production
    k (scripts/tcpmt_design_record.py `decoupling`). A development step outside the campaign
    (it writes the repository); the campaign re-derives k and kcheck compares."""
    import datetime
    dec = json.loads((ROOT / "tcpmt_revision" / "input_decoupling.json").read_text())
    pn = json.loads((ROOT / "final_closure" / "package_network.json").read_text())
    ci, pl, s = dec["circuit"], dec["placement"], dec["summary"]
    if (ci.get("design") or {}).get("n_cell") != DR.n_vr():
        raise SystemExit("input_decoupling.json is not of the design in force")
    if ((pn.get("meta") or {}).get("design") or {}).get("design") != DR.name():
        raise SystemExit("package_network.json is not of the design in force")
    rec = s["recommended"]
    s0 = ROOT / "final_closure" / ci["design"]["source"].split("I_in from ")[-1]
    ref = json.loads(s0.read_text()).get("refine") if s0.is_file() else None
    fb = pn.get("match_fallback")
    k_closed, n_closed = pn["meta"].get("production_k_eq"), pn["matched_count"]
    # the re-closure at this k (final_closure_pkg_network.py reclose), when it is of this
    # design and k: its closure supersedes the network's (which may be at an earlier k)
    bp = ROOT / "final_closure" / "bga_count_production.json"
    bc, adopted = None, None
    if bp.is_file():
        b = json.loads(bp.read_text())
        if ((b.get("design") or {}).get("design") == DR.name()
                and abs(float(b.get("k_eq") or 0.0) - float(rec["k_eq"])) < 1e-9):
            # review round 3: the network's count is the modelled arrangement (the network k
            # is derived on); the provisioned count is the re-closure's adopted one
            fb, k_closed = b.get("match_fallback"), b["k_eq"]
            n_closed = b.get("modelled_count", b.get("matched_count"))
            bc, adopted = b.get("ball_currents_at_count"), b.get("adopted_count")
    if n_closed != pn["matched_count"]:
        raise SystemExit(f"the re-closure at k = {k_closed:.3f} moves the count to {n_closed}: "
                         f"rebuild package_network.json (final_closure_pkg_network.py "
                         f"--reuse-screen) and rerun the decoupling chain first")
    entry = {
        "k_eq": rec["k_eq"], "k_eq_band": rec["k_eq_band"], "option": rec["option"],
        "phase_pattern": pl.get("recommended_phase"), "n_ring": rec["count"],
        "k_open": ci["waveform"]["ramp_deff"]["k_open"], "P_ring_esr_W": rec["P_ring_esr_W"],
        "rule": pl.get("recommend_rule"),
        "bga": {"n_per_rail": n_closed, "adopted_count": adopted,
                "status": (bc["status"] if bc else fb["status"] if fb else "CLOSED"),
                "closed_at_k_eq": k_closed,
                "verified_peak_A": (fb or {}).get("verified_peak_A"),
                "criterion_A": pn["meta"].get("criterion_A_per_ball"),
                "r_loop_mohm": {a: pn["loop"][a]["r_loop_ohm"] * 1e3 for a in pn["loop"]}},
        "ball_rms": s.get("ball_currents_recommended"),
        # review round 3: both per-ball currents at the closed count and the worse of them
        # (the closure criterion), from the re-closure at this k
        **({"bga_closure": {
            "rule": bc.get("rule"), "n_per_rail": bc["n_per_rail"], "status": bc["status"],
            "criterion_A": bc["criterion_A"],
            "I_ball_closure_rule_A": {a: v["I_ball_closure_rule_A"]
                                      for a, v in bc["per_arch"].items()},
            "I_ball_rms_max_A": {a: v["I_ball_rms_max_A"] for a, v in bc["per_arch"].items()
                                 if v["I_ball_rms_max_A"] is not None},
            "I_ball_A": {a: v["I_ball_A"] for a, v in bc["per_arch"].items()},
            "passes": {a: v["passes"] for a, v in bc["per_arch"].items()},
            "basis": {a: v["basis"] for a, v in bc["per_arch"].items()}}} if bc else {}),
        "source": (f"decoupling chain (tcpmt_decap_circuit/placement/framework) on the "
                   f"design's own package network and S0 case ({s0.name}, mesh rung "
                   f"r{''.join(str(x) for x in ref) if ref else '?'}), "
                   f"{datetime.date.today().isoformat()}")}
    doc = json.loads(DECOUPLING_FILE.read_text()) if DECOUPLING_FILE.is_file() else {
        "what": "committed production k of each design's implemented input decoupling (the "
                "package network is closed at it); written by tcpmt_design_comparison.py "
                "commit-k from a decoupling chain run, read by tcpmt_design_record.py",
        "designs": {}}
    doc["designs"][DR.name()] = entry
    DECOUPLING_FILE.write_text(json.dumps(doc, indent=1, default=float) + "\n")
    print(json.dumps(entry, indent=1, default=float))
    return entry


if __name__ == "__main__":
    if sys.argv[1:2] == ["kcheck"]:
        kcheck()
    elif sys.argv[1:2] == ["commit-k"]:
        commit_k()
    else:
        compare()
