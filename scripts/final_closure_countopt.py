#!/usr/bin/env python3
"""TCPMT REVISION --- a count-optimal candidate through the complete Z1 ETM chain.

The reviewer's point: the regulator-count optimum of the DSE is an electrical/routing optimum
only. This driver carries one count-optimal design (a non-default Z1 config, e.g.
configs/phase0nx/z1_physical_m64.yaml) through the SAME production chain as the 49-cell Z1:
E-T fixed point, thermoelastic solution, all-site joint search and the local solder response,
at production settings (h_xy 1.1, refine (2,1), ITERATIVE CHOLESKY, top cold plate, S0).

The config is an EXPLICIT parameter (--z1-config); it is exported as HVR_Z1_CONFIG before
any chain module is imported, so every module of the process sees one design
(scripts/phase0nw/z1_design.py). Without it the chain is the production one, unchanged.

    python final_closure_countopt.py --z1-config CFG net       # package 48 V network
    python final_closure_countopt.py --z1-config CFG etm  [--threads 2] [--refine 21]
    python final_closure_countopt.py --z1-config CFG remech [--timeout 43200]
    python final_closure_countopt.py --z1-config CFG local     # L0 local solder response
    python final_closure_countopt.py --z1-config CFG control   # the 49-cell L0, same harness
    python final_closure_countopt.py --z1-config CFG compare   # candidate vs 49-cell Z1
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
R = Path(__file__).resolve().parents[1]
SCEN = "HV_S0"
#: the 49-cell production case every candidate result is compared with
PRODUCTION_CASE = R / "research" / "final_closure" / "etm_Z1_HV_S0_h1.1_r21.json"
PRODUCTION_NETWORK = R / "research" / "final_closure" / "package_network.json"
PRODUCTION_LOCAL = R / "research" / "final_closure" / "local_mesh_study.json"
#: the structural solve's wall-clock limit (ccxio.run_ccx default 7200 s). A limit changes
#: nothing numerical; remech_long.py used 12 h for the r31 solves on the loaded host.
CCX_TIMEOUT_S = 43200


def _paths():
    for p in ("scripts", "scripts/phase0nw", "scripts/phase0mr", "scripts/phase0m",
              "scripts/phase0i", "scripts/phase0g", "scripts/phase0b"):
        if str(R / p) not in sys.path:
            sys.path.insert(0, str(R / p))


def _long_ccx(timeout):
    import production_et as PE
    orig = PE.ccxio.run_ccx
    if getattr(orig, "_long", False):
        return

    def run_ccx(job, threads=None, timeout=timeout):
        return orig(job, threads, timeout)
    run_ccx._long = True
    PE.ccxio.run_ccx = run_ccx


# ------------------------------------------------------------------ package 48 V network
def _net_job(args):
    import pkg_rdl_refined as RF
    rail, n, level, cells, tile = args
    r = RF.solve_rail("Z1", rail, n, level, mode="VIN_PAD", cells=cells, tile=tile)
    return {k: (v.tolist() if hasattr(v, "tolist") else v) for k, v in r.items()
            if k != "cell_drop_v"}


def cmd_net(a):
    """The Z1 48 V package network on the candidate's cell grid: the production model
    (pkg_rdl_refined, traced VIN pad, levels 1-3) at the production matched count, plus the
    per-ball peak fraction at every legal count (level 1) for the closure check."""
    from multiprocessing import Pool
    import numpy as np
    import physical_coords as PCO
    import pkg_rdl_network as K
    import pkg_rdl_refined as RF
    import z1_design as Z1D
    t0 = time.time()
    prod = json.loads(PRODUCTION_NETWORK.read_text())
    n = a.n_per_rail or int(prod["loop"]["Z1"]["n_per_rail"])
    cells, tile = Z1D.cell_coordinates(), Z1D.cell_side_mm()
    jobs = [(rail, n, lv, cells, tile) for rail in ("supply", "return") for lv in (1, 2, 3)]
    cand = PCO.bga_lattice_sites(K.architecture_cutout_mm("Z1"))
    legal = []
    for m in range(2, 251, 2):
        if 2 * m > len(cand):
            break
        try:
            s = PCO.select_power_sites(cand, cells, m, m, "nearest_symmetric")
        except Exception:
            continue
        if len(s["supply"]) == m and len(s["return"]) == m:
            legal.append(m)
    screen_jobs = [(rail, m, 1, cells, tile) for m in legal for rail in ("supply", "return")]
    with Pool(a.workers) as p:
        fin = p.map(_net_job, jobs, chunksize=1)
        scr = p.map(_net_job, screen_jobs, chunksize=1)
    conv = {}
    for rail in ("supply", "return"):
        rr = sorted([r for r in fin if r["rail"] == rail], key=lambda r: r["level"])
        fine, mid = rr[-1], rr[-2]
        d = {m: abs(fine[m] - mid[m]) / abs(fine[m]) for m in RF.CONV_METRICS}
        conv[f"Z1_{rail}"] = {
            "deltas": d, "worst_metric": max(d, key=d.get), "worst_delta": max(d.values()),
            "converged": max(d.values()) < RF.CONV_THRESH,
            "levels": [{k: v for k, v in r.items() if k not in ("i_ball_a", "ball_xy")}
                       for r in rr],
            "final": {k: fine[k] for k in ("r_eff_ohm", "max_cell_drop_v", "i_ball_max_a",
                                           "ball_imax_over_imean", "n_cv",
                                           "energy_residual_rel")},
            "i_ball_frac": fine["i_ball_a"], "ball_xy": fine["ball_xy"]}
    screen = {}
    for r in scr:
        screen.setdefault(r["n_per_rail"], {})[r["rail"]] = r["i_ball_max_a"]
    rs = conv["Z1_supply"]["final"]["r_eff_ohm"]
    rr_ = conv["Z1_return"]["final"]["r_eff_ohm"]
    res = {"meta": {"model": prod["meta"]["model"], "terminal_status":
                    prod["meta"]["terminal_status"], "levels_mm": prod["meta"]["levels_mm"],
                    "conv_threshold": RF.CONV_THRESH, "conv_metrics": list(RF.CONV_METRICS),
                    "criterion_A_per_ball": prod["meta"]["criterion_A_per_ball"],
                    "design": Z1D.summary(), "n_cells": len(cells), "tile_side_mm": tile,
                    "matched_count_source": "production package_network.json loop Z1",
                    "wall_s": round(time.time() - t0, 1)},
           "matched_count": n,
           "convergence": conv,
           "loop": {"Z1": {"n_per_rail": n, "r_supply_ohm": rs, "r_return_ohm": rr_,
                           "r_loop_ohm": rs + rr_,
                           "converged": conv["Z1_supply"]["converged"]
                           and conv["Z1_return"]["converged"]}},
           "screen_level1_peak_fraction": {
               str(m): max(v["supply"], v["return"]) for m, v in sorted(screen.items())
               if len(v) == 2},
           "production_Z1": {"loop": prod["loop"]["Z1"],
                             "closure_HV_S0": prod["closure"].get("Z1__HV_S0")}}
    out = Z1D.package_network_file()
    out.write_text(json.dumps(res, indent=1))
    print(f"Z1 {Z1D.tag()} network N={n}: R_supply {rs*1e3:.4f} mOhm, R_return "
          f"{rr_*1e3:.4f} mOhm, converged {res['loop']['Z1']['converged']} "
          f"(worst {max(conv['Z1_supply']['worst_delta'], conv['Z1_return']['worst_delta']):.2e})"
          f"; production {prod['loop']['Z1']['r_loop_ohm']*1e3:.4f} mOhm loop -> {out}")


# ------------------------------------------------------------------ the ETM case
def cmd_etm(a):
    import final_closure_physical_etm as E
    _long_ccx(a.timeout)
    refine = (int(a.refine[0]), int(a.refine[1]))
    t0 = time.time()
    solver = "NONE" if a.thermal_only else "ITERATIVE CHOLESKY"   # NONE: E-T fixed point only
    r = E.run_case("Z1", SCEN, 1.1, True, refine, solver, a.threads)
    f = Path(r["file"])
    c = json.loads(f.read_text())
    c["ccx_timeout_s"] = a.timeout
    c["driver"] = "scripts/final_closure_countopt.py etm"
    f.write_text(json.dumps(c, indent=1, default=float))
    print(f"{r} in {time.time() - t0:.0f} s", flush=True)


def cmd_remech(a):
    """Structural step only, on the converged field (final_closure_remech, longer limit)."""
    import numpy as np
    import final_closure_physical_etm as E
    import production_et as PE
    _long_ccx(a.timeout)
    refine = (int(a.refine[0]), int(a.refine[1]))
    f = E.case_path("Z1", SCEN, 1.1, refine)
    wd = E.work_dir("Z1", SCEN, 1.1, refine)
    E._raise_stack_limit()
    m, mats, st, tiles, _ = E.build("Z1", 1.1, refine)
    res = json.loads(f.read_text())
    last_it = sorted(wd.glob("et*"), key=lambda p: int(p.name[2:]))[-1]
    frd = sorted(last_it.glob("th_*.frd"), key=lambda p: int(p.stem.split("_")[1]))[-1]
    Tn = PE.ccxio.read_frd(frd)["NDTEMP"][1:m.n_nodes + 1, 0]
    assert abs(float(np.nanmax(Tn)) - res["thermal"]["T_max_C"]) < 1e-6, "not the converged field"
    res["mechanics"] = E.mechanics(m, mats, st, Tn, wd, "Z1", tiles, "ITERATIVE CHOLESKY",
                                   a.threads)
    res["mechanics"]["note"] = "structural step run separately on the converged field"
    res.pop("mechanics_error", None)
    res["ccx_timeout_s"] = a.timeout
    f.write_text(json.dumps(res, indent=1, default=float))
    print("re-mech", res["mechanics"]["die_warpage_pv_um"],
          res["mechanics"]["joint_search"]["critical"], flush=True)


# ------------------------------------------------------------------ local solder response
def _local(name, du, tj, sub):
    os.environ["JOINT_BAND_FRAC"] = repr(1.0 / 6.0)
    import final_closure_local_mesh as LM
    from hvr_scratch import path as scratch
    if os.environ["JOINT_BAND_FRAC"] != "0.16666666666666666":
        raise RuntimeError(f"averaging band {os.environ['JOINT_BAND_FRAC']} is not the "
                           f"production pass-5 band")
    inc0 = json.loads(LM.TIME_STUDY.read_text())["production_dt0_s"]
    return LM._solve(name, du, tj, scratch("fc_countopt_local", sub), "L0", inc0, True)


def cmd_local(a):
    """The candidate's critical joint at L0 exactly as final_closure_sensitivity._local_task."""
    import final_closure_physical_etm as E
    import z1_design as Z1D
    f = E.case_path("Z1", SCEN)
    c = json.loads(f.read_text())
    crit = c["mechanics"]["joint_search"]["critical"]
    r = _local(f"Z1_{Z1D.tag()}_{SCEN}", crit["du_um"], crit["T_C"], Z1D.tag())
    c["local"] = r
    f.write_text(json.dumps(c, indent=1, default=float))
    print("local", r["d_peeq_per_cycle"], r["error"], flush=True)


def cmd_control(a):
    """The 49-cell Z1 critical joint through the SAME call: must reproduce the published L0."""
    pub = json.loads(PRODUCTION_LOCAL.read_text())["cases"]["Z1_HV_S0"]["levels"]["L0"]
    r = _local("Z1_HV_S0_control49", pub["du_um"], pub["T_joint_C"], "control49")
    dev = abs(r["d_peeq_per_cycle"] - pub["d_peeq_per_cycle"]) / pub["d_peeq_per_cycle"]
    out = R / "research" / "tcpmt_revision" / "countopt" / "local_control_49.json"
    out.write_text(json.dumps({"published": pub, "rerun": r, "dev_rel": dev,
                               "accept_if_below": 1e-3}, indent=1, default=float))
    print("control", r["d_peeq_per_cycle"], pub["d_peeq_per_cycle"], dev, flush=True)


# ------------------------------------------------------------------ comparison
def cmd_compare(a):
    import final_closure_physical_etm as E
    import z1_design as Z1D
    c = json.loads(E.case_path("Z1", SCEN).read_text())
    p = json.loads(PRODUCTION_CASE.read_text())
    pl = json.loads(PRODUCTION_LOCAL.read_text())["cases"]["Z1_HV_S0"]["levels"]["L0"]
    net_c = json.loads(Z1D.package_network_file().read_text())
    net_p = json.loads(PRODUCTION_NETWORK.read_text())
    cell = json.loads((R / "research/tcpmt_revision/countopt/physical_cell.json").read_text())
    groups = {"conversion": ("P_conv_hs", "P_conv_ls", "P_conv_inductor_dcr",
                             "P_conv_cap_esr"),
              "intra_vr": ("P_intraVR_metal", "P_intraVR_vertical"),
              "package_48V": ("P_pkg_RDL_HV_supply", "P_pkg_RDL_HV_return", "P_BGA_supply",
                              "P_BGA_return"),
              "tsv_48V": ("P_TSV_VDD", "P_TSV_GND"), "pads_1V": ("P_pad_VDD", "P_pad_GND")}

    def split(case):
        t = {r["term"]: r["P_w"] for r in case["ledger_rows"]}
        out = {"terms": t, "groups": {g: sum(t.get(k, 0.0) for k in ks)
                                      for g, ks in groups.items()}}
        out["total"] = case["P_loss_w"]
        return out

    def temps(case):
        h = case["et_history"][-1]
        return {k: h[k] for k in h if k.startswith("T_")}

    def mech(case):
        m = case.get("mechanics") or {}
        js = m.get("joint_search") or {}
        return {"die_warpage_pv_um": m.get("die_warpage_pv_um"),
                "pkg_warpage_pv_um": m.get("pkg_warpage_pv_um"),
                "critical_joint": js.get("critical"), "n_sites": js.get("n_sites"),
                "n_evaluated": js.get("n_evaluated"),
                "structural_wall_s": m.get("wall_s")}

    def balls(net, i_hv):
        L = net["loop"]["Z1"]
        pk = max(net["convergence"]["Z1_supply"]["final"]["i_ball_max_a"],
                 net["convergence"]["Z1_return"]["final"]["i_ball_max_a"])
        return {"n_per_rail": L["n_per_rail"], "r_loop_mohm": L["r_loop_ohm"] * 1e3,
                "peak_ball_fraction": pk, "i_hv_S0_A": i_hv, "peak_ball_A": pk * i_hv,
                "criterion_A": 1.5, "passes_1p5A": pk * i_hv <= 1.5}

    def tsv(case, n_cells):
        rows = {r["term"]: r for r in case["ledger_rows"]}
        v = rows["P_TSV_VDD"]
        n_vdd = int(v["conductor"].split(",")[1].split("/")[0])
        g = rows["P_TSV_GND"]
        n_gnd = int(g["conductor"].split(",")[1].split("/")[0])
        i_cell = v["I_a"] / n_cells
        return {"per_cell": n_vdd + n_gnd, "vdd_per_cell": n_vdd, "gnd_per_cell": n_gnd,
                "total": (n_vdd + n_gnd) * n_cells, "i_cell_A": i_cell,
                "i_per_via_mA": 1e3 * i_cell / n_vdd,
                "loss_W": v["P_w"] + g["P_w"],
                "cu_fraction_in_tiles": case["materials"]["tsv_tile_cu_fraction"]}

    n_c = int(c["design"]["n_vr"])
    i_c, i_p = c["i_hv_avg_a"], p["i_hv_avg_a"]
    cmp_ = {
        "scenario": SCEN, "mesh": f"h_xy 1.1, refine {c['refine']}",
        "candidate": {"design": c["design"], "file": str(E.case_path("Z1", SCEN).relative_to(R)),
                      "loss": split(c), "temperatures_C": temps(c),
                      "thermal": {k: c["thermal"][k] for k in
                                  ("T_max_C", "T_mean_C", "q_top_W", "q_bot_W",
                                   "energy_residual_rel", "n_elems", "n_nodes")},
                      "et_converged": c["et_converged"], "et_iterations": len(c["et_history"]),
                      "mechanics": mech(c), "local_L0": (c.get("local") or {}),
                      "balls_48V": balls(net_c, i_c), "tsv_48V": tsv(c, n_c),
                      "via_ar_worst": cell["cells"]["64"]["chosen"]["worst_ar"],
                      "tier_order": cell["cells"]["64"]["chosen"]["partition"],
                      "stack_um": cell["cells"]["64"]["chosen"]["stack_um"]},
        "production_49": {"file": str(PRODUCTION_CASE.relative_to(R)), "loss": split(p),
                          "temperatures_C": temps(p),
                          "thermal": {k: p["thermal"][k] for k in
                                      ("T_max_C", "T_mean_C", "q_top_W", "q_bot_W",
                                       "energy_residual_rel", "n_elems", "n_nodes")},
                          "mechanics": mech(p),
                          "local_L0": {k: pl[k] for k in ("d_peeq_per_cycle", "du_um",
                                                          "T_joint_C", "error")},
                          "balls_48V": balls(net_p, i_p), "tsv_48V": tsv(p, 49),
                          "via_ar_worst": cell["cells"]["49"]["chosen"]["worst_ar"],
                          "tier_order": cell["cells"]["49"]["chosen"]["partition"],
                          "stack_um": cell["cells"]["49"]["chosen"]["stack_um"]},
    }
    cc, pp = cmp_["candidate"], cmp_["production_49"]
    d = {"P_loss_W": cc["loss"]["total"] - pp["loss"]["total"],
         "T_max_K": cc["thermal"]["T_max_C"] - pp["thermal"]["T_max_C"]}
    for g in groups:
        d[f"P_{g}_W"] = cc["loss"]["groups"][g] - pp["loss"]["groups"][g]
    if cc["mechanics"]["die_warpage_pv_um"] is not None:
        d["die_warpage_um"] = cc["mechanics"]["die_warpage_pv_um"] - pp["mechanics"]["die_warpage_pv_um"]
        d["du_um"] = (cc["mechanics"]["critical_joint"]["du_um"]
                      - pp["mechanics"]["critical_joint"]["du_um"])
        d["T_joint_K"] = (cc["mechanics"]["critical_joint"]["T_C"]
                          - pp["mechanics"]["critical_joint"]["T_C"])
    if cc["local_L0"].get("d_peeq_per_cycle"):
        d["local_L0_rel"] = (cc["local_L0"]["d_peeq_per_cycle"]
                             / pp["local_L0"]["d_peeq_per_cycle"] - 1.0)
    cmp_["delta_candidate_minus_49"] = d
    dse = json.loads((R / "research/tcpmt_revision/countopt/candidate_dse.json").read_text())
    cmp_["dse_electrical_only"] = {
        m: {k: dse["counts"][m][k] for k in ("conversion_total_W", "routing_W", "total_W")}
        for m in ("49", "64", "76")}
    # the electrical difference with the coupling removed: the candidate's ledger at the
    # 49-cell case's converged temperatures (each region key at the production value)
    import final_closure_ledger as FL
    hp = p["et_history"][-1]
    t49 = {k: hp[f"T_{k}_C"] for k in ("conv", "hs", "ls", "ind", "caps", "bga", "sub",
                                       "interface") if f"T_{k}_C" in hp}
    Lm = FL.self_consistent("Z1", SCEN, t49)
    tm = {r["term"]: r["P_w"] for r in Lm["rows"]}
    cmp_["candidate_at_49_temperatures"] = {
        "temperatures_C": t49, "P_loss_W": Lm["P_loss_w"],
        "groups": {g: sum(tm.get(k, 0.0) for k in ks) for g, ks in groups.items()},
        "delta_vs_49_W": Lm["P_loss_w"] - pp["loss"]["total"],
        "note": "same ledger, the production converged region temperatures: the electrical "
                "penalty of the design alone; the rest of delta P_loss is the coupling"}
    # 48 V BGA closure at the candidate's own converged current (1.5 A/ball criterion):
    # the level-1 screen over every legal count, and the converged count's level-3 peak
    scr = {int(k): v for k, v in net_c["screen_level1_peak_fraction"].items()}
    ok = sorted(n for n, f in scr.items() if f * i_c <= 1.5)
    cmp_["candidate"]["balls_48V"].update({
        "screen_min_passing_n_per_rail": ok[0] if ok else None,
        "screen_larger_counts_that_fail": [n for n, f in sorted(scr.items())
                                           if ok and n > ok[0] and f * i_c > 1.5],
        "production_closure_HV_S0": net_p["closure"].get("Z1__HV_S0")})
    # mesh: the candidate's tile is 1.93 mm, so r21 puts 4 elements across it where the
    # 49-cell tile gets 6; the r31 E-T level (thermal only) brackets that
    f31 = E.case_path("Z1", SCEN, 1.1, (3, 1))
    p31 = R / "research" / "final_closure" / "etm_Z1_HV_S0_h1.1_r31.json"
    if f31.exists():
        c31 = json.loads(f31.read_text())
        q31 = json.loads(p31.read_text()) if p31.exists() else None

        def rel(a_, b_):
            return (a_ - b_) / b_
        cmp_["mesh_r21_to_r31"] = {
            "candidate": {"T_max_rel": rel(c31["thermal"]["T_max_C"], c["thermal"]["T_max_C"]),
                          "P_loss_rel": rel(c31["P_loss_w"], c["P_loss_w"]),
                          "T_max_r31_C": c31["thermal"]["T_max_C"],
                          "P_loss_r31_W": c31["P_loss_w"],
                          "et_converged_r31": c31["et_converged"],
                          "n_elems_r31": c31["thermal"]["n_elems"]},
            "production_49": None if q31 is None else {
                "T_max_rel": rel(q31["thermal"]["T_max_C"], p["thermal"]["T_max_C"]),
                "P_loss_rel": rel(q31["P_loss_w"], p["P_loss_w"])},
            "declared_tolerance_rel": E.MESH_TOL_REL}
    out = R / "research" / "tcpmt_revision" / "countopt" / f"etm_compare_{Z1D.tag()}_vs_49.json"
    out.write_text(json.dumps(cmp_, indent=1, default=float))
    print(json.dumps(d, indent=1))
    print("wrote", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--z1-config", required=True,
                    help="the candidate's Z1 config (exported as HVR_Z1_CONFIG)")
    ap.add_argument("cmd", choices=("net", "etm", "remech", "local", "control", "compare"))
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--refine", default="21")
    ap.add_argument("--timeout", type=int, default=CCX_TIMEOUT_S)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--n-per-rail", type=int, default=0)
    ap.add_argument("--thermal-only", action="store_true",
                    help="etm: the E-T fixed point only (a mesh-sensitivity level)")
    a = ap.parse_args()
    os.environ["HVR_Z1_CONFIG"] = a.z1_config        # BEFORE any chain module is imported
    _paths()
    import z1_design as Z1D
    if Z1D.is_default():
        raise SystemExit("--z1-config names the production Z1 config; this driver is for "
                         "a non-default design")
    Z1D.declared()
    {"net": cmd_net, "etm": cmd_etm, "remech": cmd_remech, "local": cmd_local,
     "control": cmd_control, "compare": cmd_compare}[a.cmd](a)


if __name__ == "__main__":
    main()
