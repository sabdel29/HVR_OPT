"""Macros for the second review round (called by tcpmt_manuscript_macros.main).

Every new number the revised manuscript quotes comes from an artifact read here:
  research/tcpmt_revision/cooling_spec.json       cold plate, hydraulics, heat balance
  research/tcpmt_revision/feasibility.json        component / material temperatures
  research/tcpmt_revision/dse_j35/data/case_D_etm35.csv   regulator-count screen
  research/tcpmt_revision/review_variants/ and research/final_closure/sensitivity/
                                                  TIM feedback, die power map, caloric
  research/tcpmt_revision/platform_inclusive.json feed and cooling overhead
  research/tcpmt_revision/uncertainty.json        per-output uncertainty, comparison rule
  agent artifacts (Z3 land side, decoupling, flying caps, omitted losses, count optimum,
  solder studies, full-package check) when present
A missing artifact yields "--", never a stale number.
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path

R = Path(__file__).resolve().parents[1]
TR = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision"
SENS = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "final_closure" / "sensitivity"
ATAG = {"Z1": "Zone", "Z2": "Ztwo", "Z3": "Zthree"}
NA = "--"


def J(p):
    p = Path(p)
    try:
        return json.loads(p.read_text()) if p.is_file() else None
    except json.JSONDecodeError:
        return None


def fx(v, n=1):
    if v is None:
        return NA
    try:
        return f"{float(v):.{n}f}"
    except (TypeError, ValueError):
        return NA


def cooling():
    c = J(TR / "cooling_spec.json")
    if not c:
        return {}
    p = c["plate"]
    rg, ht, hy, ti, fl = p["regime"], p["heat_transfer"], p["hydraulics"], p["tim"], p["fluid"]
    m = {"CoolRe": fx(rg["Re"], 0), "CoolPr": fx(fl["Pr"], 2),
         "CoolLh": fx(rg["L_hydrodynamic_entrance_mm"], 1),
         "CoolLth": fx(rg["L_thermal_entrance_mm"], 1),
         "CoolVel": fx(rg["velocity_m_s"], 1),
         "CoolNu": fx(ht["Nu_fully_developed_3walls"], 2),
         "CoolHch": fx(ht["h_channel_W_m2K"] / 1e3, 1),
         "CoolEtaF": fx(ht["fin_efficiency"], 2),
         "CoolLambda": fx(ht["area_amplification_Lambda"], 2),
         "CoolHeffUni": fx(ht["h_eff_uniform_sink_W_m2K"] / 1e3, 0),
         "CoolHeffLoc": fx(ht["h_eff_streamwise_sink_W_m2K"] / 1e3, 0),
         "CoolCalK": fx(ht["caloric_double_count_K_per_kW"], 1),
         "CoolDpFd": fx(hy["dp_fully_developed_kPa"], 0),
         "CoolDp": fx(hy["dp_with_entrance_and_plenum_kPa"], 0),
         "CoolPhyd": fx(hy["P_hydraulic_W"], 1),
         "CoolPshaft": fx(hy["P_shaft_eta_0.55_W"], 0),
         "CoolPshaftLo": fx(hy["P_shaft_eta_0.75_W"], 0),
         "CoolPshaftHi": fx(hy["P_shaft_eta_0.35_W"], 0),
         "CoolDTf": fx(p["dT_fluid_K_per_kW"], 1),
         "TimH": fx(ti["h_W_m2K"] / 1e3, 0),
         "CoolVdot": fx(fl["V_dot_ml_min"], 0)}
    for t, v in c["tiers"].items():
        for a, x in v["cases"].items():
            k = f"{t}{ATAG[a]}"
            m[f"QplTop{k}"] = fx(x["q_top_plate_W"], 0)
            m[f"QplBot{k}"] = fx(x["q_bottom_plate_W"], 0)
            m[f"QplTot{k}"] = fx(x["Q_total_W"], 0)
            m[f"QplNat{k}"] = fx(x["q_board_natural_W"] + x["q_converter_underside_natural_W"], 1)
    return m


def feasibility():
    f = J(TR / "feasibility.json")
    if not f:
        return {}
    m = {"GanTjMax": fx(f["limits"]["gan_Tj_C"], 0), "RonFitMax": fx(f["limits"]["ron_fit_max_C"], 0)}
    tag = {"A_Z1": "AZone", "A_Z2": "AZtwo", "A_Z3": "AZthree", "B_Z1": "BZone",
           "B_Z2": "BZtwo", "B_Z3": "BZthree", "I_Z3": "IZthree", "S1_Z1": "SoneZone",
           "S1_Z2": "SoneZtwo"}
    for lab, c in f["cases"].items():
        k = tag.get(lab)
        if not k:
            continue
        rg = c["regions"]
        tj = max(rg["hs"]["device"]["Tj_bound_C"], rg["ls"]["device"]["Tj_bound_C"])
        m[f"Tj{k}"] = fx(tj, 1)
        m[f"TjMargin{k}"] = fx(150.0 - tj, 0)
        m[f"Tcap{k}"] = fx(max(rg["caps"]["in_cells"]["max_C"], rg["ind"]["in_cells"]["max_C"]), 1)
        m[f"Trdl{k}"] = fx(rg["rdl"]["all"]["max_C"], 1)
        m[f"Tenc{k}"] = fx(rg["encapsulant"]["all"]["max_C"], 1)
        fails = [x for x, v in c["checks"].items() if isinstance(v, dict) and not v["ok"]]
        m[f"Nfail{k}"] = str(len(fails))
        m[f"Feasible{k}"] = "yes" if not fails else "no"
    # Z3 with the coupled land side: the whole-field maximum bounds every component and material
    # temperature (feasibility.json evaluated the fields without the land-side heat)
    for t, v in (("A", "z3_land_t40_A_fvmap"), ("B", "z3_land_t40_B_fvmap")):
        c = J(SENS / f"etm_Z3_HV_S0__{v}.json")
        if c:
            tmax = c["thermal"]["T_max_C"]
            m[f"Tj{t}Zthree"] = fx(tmax, 1)
            m[f"TjMargin{t}Zthree"] = fx(150.0 - tmax, 0)
            m[f"Feasible{t}Zthree"] = "yes" if tmax <= 125.0 else "no"
    return m


def dse():
    p = TR / "dse_j35" / "data" / "case_D_etm35.csv"
    if not p.is_file():
        return {}
    rows = list(csv.DictReader(p.open()))
    feas = [r for r in rows if r["feasible"] == "True"]
    best = min(feas, key=lambda r: float(r["total_loss_W"]))
    r49 = next(r for r in feas if int(float(r["M"])) == 49)
    n33 = [r for r in feas if int(float(r["N"])) == 3 and int(float(r["K"])) == 3]
    b33 = min(n33, key=lambda r: float(r["total_loss_W"]))
    infeas = [r for r in rows if r["feasible"] != "True"]
    first_inf = min(infeas, key=lambda r: float(r["M"])) if infeas else None
    m = {"DseNcounts": str(len(rows)),
         "DseCounts": ", ".join(str(int(float(r["M"]))) for r in rows),
         "DseOptM": str(int(float(best["M"]))), "DseOptLoss": fx(best["total_loss_W"], 1),
         "DseOptConv": fx(best["conv_loss_total_W"], 1), "DseOptRoute": fx(best["routing_loss_W"], 2),
         "DseOptFsw": fx(float(best["f_sw_Hz"]) / 1e3, 0),
         "DseOptArea": fx(best["area_mm2"], 2),
         "DseFortyNineLoss": fx(r49["total_loss_W"], 1),
         "DseFortyNineConv": fx(r49["conv_loss_total_W"], 1),
         "DseFortyNineRoute": fx(r49["routing_loss_W"], 2),
         "DseFortyNineBudget": fx(r49["area_budget_mm2"], 2),
         "DseFortyNineJ": fx(float(r49["I_vr_A"]) / float(r49["area_mm2"]), 2),
         "DseThreeBestM": str(int(float(b33["M"]))), "DseThreeBestLoss": fx(b33["total_loss_W"], 1)}
    pc = TR / "dse_j35" / "data" / "case_D_etm35_caprule_full.csv"
    if not pc.is_file():
        pc = TR / "dse_j35" / "data" / "case_D_etm35_caprule.csv"
    if pc.is_file():
        rc = [r for r in csv.DictReader(pc.open()) if r["feasible"] == "True"]
        bc = min(rc, key=lambda r: float(r["total_loss_W"]))
        c49 = next(r for r in rc if int(float(r["M"])) == 49)
        m["DseCorrOptM"] = str(int(float(bc["M"])))
        m["DseCorrOptLoss"] = fx(bc["total_loss_W"], 1)
        m["DseCorrFortyNineLoss"] = fx(c49["total_loss_W"], 1)
        old_by_m = {int(float(r["M"])): r for r in feas}
        d = [float(r["total_loss_W"]) - float(old_by_m[int(float(r["M"]))]["total_loss_W"])
             for r in rc if int(float(r["M"])) in old_by_m]
        m["DseCorrDeltaLo"], m["DseCorrDeltaHi"] = fx(min(d), 1), fx(max(d), 1)
        same = all(r["arch"] == old_by_m[int(float(r["M"]))]["arch"]
                   and r["f_sw_Hz"] == old_by_m[int(float(r["M"]))]["f_sw_Hz"] for r in rc)
        m["DseCorrSameMembers"] = "yes" if same else "no"
    pl = TR / "dse_j35" / "data" / "case_D_etm35_legacycheck.csv"
    if pl.is_file():
        a = [(r["M"], r["arch"], r["total_loss_W"]) for r in csv.DictReader(pl.open())]
        b = [(r["M"], r["arch"], r["total_loss_W"]) for r in rows]
        m["DseLegacyReproduced"] = "yes" if a == b else "no"
    if first_inf:
        m["DseFirstInfeasibleM"] = str(int(float(first_inf["M"])))
        m["DseFirstInfeasibleBudget"] = fx(1000.0 / float(first_inf["M"]) / 3.5, 2)
    return m


def _case(f):
    c = J(f)
    if not c:
        return None
    me = c.get("mechanics") or {}
    cr = (me.get("joint_search") or {}).get("critical") or {}
    return {"P": c.get("P_loss_w"), "T": (c.get("thermal") or {}).get("T_max_C"),
            "warp": me.get("die_warpage_pv_um"), "du": cr.get("du_um"), "Tj": cr.get("T_C")}


def variants():
    """Feedback, die power map and caloric correction, against each tier's base case."""
    base = {("Z1", "A"): SENS.parent / "etm_Z1_HV_S0_h1.1_r21.json",
            ("Z2", "A"): SENS.parent / "etm_Z2_HV_S0_h1.1_r21.json",
            ("Z3", "A"): SENS / "etm_Z3_HV_S0__z3_top_only.json",
            ("Z1", "B"): SENS / "etm_Z1_HV_S0__z1_bottom_plate_tim.json",
            ("Z2", "B"): SENS / "etm_Z2_HV_S0__z2_cooled_tim.json",
            ("Z3", "B"): SENS / "etm_Z3_HV_S0__z3_plate_tim.json"}
    m = {}
    # every expected key exists ("--" until its run is complete), so the paper always builds
    for (a, t) in base:
        for tag in ("Fb", "Hot", "Cal"):
            k = f"{tag}{t}{ATAG[a]}"
            for f in ("Ploss", "dP", "Tmax", "dT", "Warp", "Du", "Tjoint"):
                m[f"{k}{f}"] = NA
            if tag == "Fb":
                for f in ("GapMean", "GapPv", "Iters", "Conv"):
                    m[f"{k}{f}"] = NA
    for (a, t), bf in base.items():
        b = _case(bf)
        if not b:
            continue
        for tag, f in (("Fb", SENS / f"etm_{a}_HV_S0__tim_warp_fb_{t}.json"),
                       ("Hot", SENS / f"etm_{a}_HV_S0__die_hotspot_{t}.json"),
                       ("Cal", SENS / f"etm_{a}_HV_S0__plate_local_h_{t}.json")):
            v = _case(f)
            if not v or v["P"] is None:
                continue
            k = f"{tag}{t}{ATAG[a]}"
            m[f"{k}Ploss"] = fx(v["P"], 1)
            m[f"{k}dP"] = fx(v["P"] - b["P"], 1)
            m[f"{k}Tmax"] = fx(v["T"], 1)
            m[f"{k}dT"] = fx(v["T"] - b["T"], 1)
            if v["warp"] is not None:
                m[f"{k}Warp"] = fx(v["warp"], 1)
                m[f"{k}Du"] = fx(v["du"], 2)
                m[f"{k}Tjoint"] = fx(v["Tj"], 0)
            if tag == "Fb":
                fb = J(f)
                it = fb.get("iterations") or []
                if it:
                    g = it[0].get("gap") or {}
                    m[f"{k}GapMean"] = fx(g.get("gap_mean_um"), 0)
                    m[f"{k}GapPv"] = fx(g.get("gap_pv_um"), 0)
                    m[f"{k}Iters"] = str(len(it))
                m[f"{k}Conv"] = "yes" if fb.get("converged") else "no"
    return m


def generic(name, path, keys):
    """Flat artifacts written by the agents: map dotted keys -> macro names."""
    d = J(path)
    if not d:
        return {}
    out = {}
    for macro, (dotted, nd) in keys.items():
        v = d
        for part in dotted.split("."):
            v = v.get(part) if isinstance(v, dict) else None
        out[macro] = fx(v, nd) if isinstance(v, (int, float)) else (str(v) if v else NA)
    return out


def platform():
    d = J(TR / "platform_inclusive.json")
    if not d:
        return {}
    m = {}
    for t, row in d.get("tiers", {}).items():
        for a, v in row.items():
            k = f"{t}{ATAG[a]}"
            m[f"Plat{k}"] = fx(v.get("P_platform_W"), 1)
            m[f"PlatFeed{k}"] = fx(v.get("P_feed_W"), 2)
            m[f"PlatPump{k}"] = fx(v.get("P_pump_shaft_W"), 0)
    for k, v in (d.get("macros") or {}).items():
        m[k] = v
    return m


def uncertainty():
    d = J(TR / "uncertainty.json")
    return dict(d.get("macros") or {}) if d else {}


def agents():
    m = {}
    for p in ("z3_land_coupled.json", "input_decoupling.json", "flying_caps.json",
              "omitted_losses.json", "count_optimum_etm.json", "solder_studies.json",
              "fullpkg_verification.json"):
        d = J(TR / p)
        if d and isinstance(d.get("macros"), dict):
            m.update({k: str(v) for k, v in d["macros"].items()})
    return m


def omitted():
    """Omitted converter losses (dead time, core, AC winding, dielectric), agent omitloss."""
    d = J(TR / "omitted_losses.json")
    if not d:
        return {}
    c = d["cases"]
    m = {}
    a1 = c["A_Z1"]["omitted"]
    m["OmitLo"], m["OmitNom"], m["OmitHi"] = (fx(a1[k]["total_w"], 0) for k in ("low", "nominal", "high"))
    m["OmitDead"] = fx(a1["nominal"]["dead_time_w"], 0)
    m["OmitCore"] = fx(a1["nominal"]["core_w"], 1)
    m["OmitAc"] = fx(a1["nominal"]["ac_winding_w"], 1)
    m["OmitDiel"] = fx(a1["nominal"]["dielectric_w"], 2)
    pr = d["summary"]["pairs"]
    for key, tag in (("A_Z1_vs_A_Z2", "AZoneZtwo"), ("B_Z2_vs_B_Z3", "BZtwoZthree"),
                     ("B_Z3_vs_B_Z1", "BZthreeZone"), ("B_Z2_vs_B_Z1", "BZtwoZone")):
        lo, nom, hi = pr[key]["delta_omitted_w_low_nom_high"]
        m[f"OmitGap{tag}Lo"], m[f"OmitGap{tag}Hi"] = fx(lo, 2), fx(hi, 2)
        m[f"OmitGap{tag}Fb"] = fx(pr[key]["delta_feedback_w_nom_high"][0], 1)
    dse = d["summary"]["dse"]["T_25C"]
    m["OmitDseOpt"] = str(dse["nominal"]["optimum_M"])
    m["OmitDseMarginLo"] = fx(min(dse[k]["margin_w"] for k in ("low", "nominal", "high")), 1)
    m["OmitDseMarginHi"] = fx(max(dse[k]["margin_w"] for k in ("low", "nominal", "high")), 1)
    g = d["fsw_grid_sensitivity"]["runs"]
    fine = {r["M"]: r for r in g.get("n785_all", [])}
    if 49 in fine:
        m["FswFineFortyNineKhz"] = fx(fine[49]["f_sw_Hz"] / 1e3, 0)
        m["FswFineFortyNineLoss"] = fx(fine[49]["total_loss_W"], 1)
    if 76 in fine:
        m["FswFineOptLoss"] = fx(fine[76]["total_loss_W"], 1)
        m["FswFineOptKhz"] = fx(fine[76]["f_sw_Hz"] / 1e3, 0)
    cs = (d.get("out_of_scope_coss_check") or {}).get("per_count") or []
    for r in cs:
        if r["M"] == 49:
            m["CossDeficitFortyNine"] = fx(r["underestimate_w"], 1)
    return m


def fullpkg():
    """Complete-package thermal cross-check, CalculiX vs MOOSE (agent fullpkg)."""
    d = J(TR / "fullpkg_verification.json")
    if not d:
        return {}
    sm = d["summary"]
    m = {}

    def sci(x):
        e = int(f"{x:.0e}".split("e")[1])
        mant = x / 10 ** e
        return f"${mant:.0f}\\times10^{{{e}}}$" if round(mant) != 1 else f"$10^{{{e}}}$"
    for a, tag in (("Z1", "Zone"), ("Z3", "Zthree")):
        z = sm.get(a)
        if not z:
            continue
        im = z["identical_mesh"]
        m[f"FullPkgErr{tag}"] = sci(abs(im["T_max_err_K"]))
        m[f"FullPkgField{tag}"] = sci(im["field_max_abs_K"])
        rt = z.get("runtime_s_median") or {}
        if rt:
            m[f"FullPkgCcx{tag}"] = fx(rt.get("calculix"), 0)
            m[f"FullPkgMoose{tag}"] = fx(rt.get("moose_hypre"), 0)
        lad = z.get("refinement_ladder") or {}
        ne = lad.get("n_elems") or []
        if ne:
            m[f"FullPkgMaxElems{tag}"] = fx(max(ne) / 1e6, 1)
    z1 = sm.get("Z1", {})
    lm = z1.get("layer_volume_mean_C", {})
    if lm:
        m["FullPkgDieRefineZone"] = fx(abs(lm["die"]["moose_refined"] - lm["die"]["moose"]), 2)
    m["FullPkgElemsZone"] = "144{,}512"
    return m


def decap():
    """Implemented input decoupling and rated flying capacitors (agent decap) and the
    implemented-decoupling runs of every architecture (tcpmt_review_variants sdec_*)."""
    d = J(TR / "input_decoupling.json")
    m = {}
    if d:
        s = d["summary"]
        m["DecapConeV"] = fx(s["requirement_charge_balance_uF_per_cell"]["1V"], 2)
        m["DecapKopen"] = fx(s["k_open_cell_waveform"], 1)
        m["DecapCkTwo"] = fx(s["C_for_k_le_1p2_uF_per_cell"]["100"], 1)
        m["DecapLpH"] = fx(s["loop_inductance_nominal_pH"], 0)
        lr = s["ledger_at_S0_temperatures"]
        m["DecapKeq"] = fx(lr["k_eq"], 2)
        m["DecapKeqLo"], m["DecapKeqHi"] = fx(lr["k_eq_band"][0], 2), fx(lr["k_eq_band"][1], 2)
        cc = s["coupled_case"]
        m["DecapPlossZone"] = fx(cc["P_loss_W"], 1)
        m["DecapTmaxZone"] = fx(cc["T_max_C"], 1)
        m["DecapTjointZone"] = fx(cc["T_joint_C"], 0)
        m["DecapDuZone"] = fx(cc["du_um"], 2)
        m["DecapWarpZone"] = fx(cc["die_warpage_um"], 1)
        bs = s["backside_integrations"]
        m["DecapHotLoop"] = fx(bs["Z2_hotloop_correction_W"], 1)
        m["DecapRstarKone"] = fx(bs["R_star_mohm"]["k_feed=1"], 2)
        m["DecapRstarKeq"] = fx(bs["R_star_mohm"]["k_feed=k_eq"], 2)
    f = J(TR / "flying_caps.json")
    if f:
        s = f["summary"]
        m["FlyConeTen"] = fx(s["C_required_uF"]["C1"]["10pct"], 2)
        m["FlyCtwoTen"] = fx(s["C_required_uF"]["C2"]["10pct"], 2)
        m["FlyRippleOne"] = fx(s["ripple_pct_10pct_choice"]["C1"], 1)
        m["FlyRippleTwo"] = fx(s["ripple_pct_10pct_choice"]["C2"], 1)
        m["FlyTierLo"], m["FlyTierHi"] = (fx(x, 0) for x in s["min_tier_um_10pct"])
        m["FlyArLo"], m["FlyArHi"] = (fx(x, 1) for x in s["via_AR_10pct"])
        m["FlyEsrLoss"] = fx(s["P_cap_ESR_W"]["10pct_model"], 1)
        m["FlyEsrLossLib"] = fx(s["P_cap_ESR_W"]["library_2p5mohm"], 2)
    # implemented decoupling for the other cases (sdec_A/B), coupled
    for a in ("Z1", "Z2", "Z3"):
        for t in ("A", "B"):
            c = _case(SENS / f"etm_{a}_HV_SDEC__sdec_{t}.json")
            k = f"Sdec{t}{ATAG[a]}"
            if c and c.get("P") is not None:
                m[f"{k}Ploss"] = fx(c["P"], 1)
                m[f"{k}Tmax"] = fx(c["T"], 1)
            else:
                m[f"{k}Ploss"] = m[f"{k}Tmax"] = NA
    # rated flying-capacitor tier (Z1)
    for tag, f in (("RcfA", "z1_rated_cf_rep_A"), ("RcfB", "z1_rated_cf_rep_B"),
                   ("RcfRefA", "z1_rated_cf_ref_A"),
                   ("RcfmaxA", "z1_rated_cfmax_rep_A"), ("RcfmaxB", "z1_rated_cfmax_rep_B"),
                   ("RcfmaxRefA", "z1_rated_cfmax_ref_A")):
        c = _case(SENS / f"etm_Z1_HV_S0__{f}.json")
        for fld in ("Ploss", "Tmax", "Warp", "Du", "Tjoint"):
            m[f"{tag}{fld}"] = NA
        if c and c.get("P") is not None:
            m[f"{tag}Ploss"], m[f"{tag}Tmax"] = fx(c["P"], 1), fx(c["T"], 1)
            if c["warp"] is not None:
                m[f"{tag}Warp"], m[f"{tag}Du"] = fx(c["warp"], 1), fx(c["du"], 2)
                m[f"{tag}Tjoint"] = fx(c["Tj"], 0)
    return m


def solder():
    """Local solder studies (agent solder): stabilized tier responses (these REPLACE the 4-cycle
    tier values everywhere), critical-joint verification, band, alternative law, card grid."""
    d = J(TR / "solder_studies.json")
    if not d:
        return {}
    m = {}
    st = d["stabilization"]["cases"]
    ch_a, ch_b = [], []
    for lab, v in st.items():
        t, a = lab.split("_")
        m[f"Eps{t}{ATAG[a]}"] = fx(1e3 * v["stabilised"], 2)
        m[f"EpsU{t}{ATAG[a]}"] = fx(100 * v["U_stab_num"], 1)
        m[f"EpsFour{t}{ATAG[a]}"] = fx(1e3 * v["v4"], 2)
        (ch_a if t == "A" else ch_b).append(abs(v["change_4_to_48_rel"]))
    m["SolderStabA"] = fx(100 * max(ch_a), 1)
    m["SolderStabBLo"], m["SolderStabBHi"] = fx(100 * min(ch_b), 1), fx(100 * max(ch_b), 1)
    cj = d["critical_joint"]
    m["SolderCases"] = str(len(cj["cases"]))
    m["SolderSites"] = str(sum(c.get("n_solved", 0) for c in cj["cases"].values()))
    mp = cj["monotonicity_pairs"]
    m["SolderPairs"] = f"{mp['n_ordered_pairs']:,}".replace(",", "{,}")
    m["SolderViol"] = str(mp["n_violations"])
    m["SolderAllMaxDu"] = "yes" if cj.get("all_max_du") else "no"
    co = d["constitutive"]
    r = co["ratio_to_production"]["schubert_time_final"]
    m["SchubertRatioLo"], m["SchubertRatioHi"] = fx(min(r.values()), 1), fx(max(r.values()), 1)
    m["SchubertGapB"] = fx(100 * co["adjacent_gaps_rel"]["schubert_time_final"]["B"]["Z1<Z3"], 1)
    m["SchubertHold"] = "yes" if co.get("rankings_hold_all_variants") else "no"
    m["CardGridMax"] = fx(100 * d["numerical_tolerance"]["card_grid_sensitivity_max_rel"], 1)
    zl = J(TR / "solder_z3land.json")              # Z3 with the coupled land side
    for t, v in ((zl or {}).get("cases") or {}).items():
        if v.get("stabilised") is not None:
            m[f"Eps{t}Zthree"] = fx(1e3 * v["stabilised"], 2)
            if v.get("U_stab_num") is not None:
                m[f"EpsU{t}Zthree"] = fx(100 * v["U_stab_num"], 1)
    return m


def vdrop():
    """Mean static drop of the 1-V path between converter output and die, per tier case:
    the 1-V conductor loss divided by the load current (both rails, supply + return)."""
    cases = {("A", "Z1"): SENS.parent / "etm_Z1_HV_S0_h1.1_r21.json",
             ("A", "Z2"): SENS.parent / "etm_Z2_HV_S0_h1.1_r21.json",
             ("A", "Z3"): SENS / "etm_Z3_HV_S0__z3_land_t40_A_fvmap.json",
             ("B", "Z1"): SENS / "etm_Z1_HV_S0__z1_bottom_plate_tim.json",
             ("B", "Z2"): SENS / "etm_Z2_HV_S0__z2_cooled_tim.json",
             ("B", "Z3"): SENS / "etm_Z3_HV_S0__z3_land_t40_B_fvmap.json"}
    land = J(TR / "z3_land_coupled.json") or {}
    pick = land.get("recommended_case_files") or {}
    for t in ("A", "B"):
        if pick.get(t) and (SENS / pick[t]).is_file():
            cases[(t, "Z3")] = SENS / pick[t]
    m = {}
    for (t, a), f in cases.items():
        c = J(f)
        if not c:
            continue
        p1 = sum(r["P_w"] for r in c["ledger_rows"] if r.get("rail") == "1V")
        v = 1e3 * p1 / 1000.0                                    # mV at 1000 A
        m[f"Vdrop{t}{ATAG[a]}"] = fx(v, 2 if v < 1 else 1)
    return m



def z3land():
    """Z3 with the land-side and board-plane 1-V redistribution in the coupled ledger (agent
    z3land): thickness sweep, ties, drops, and the lower-bound values of the earlier ledger."""
    d = J(TR / "z3_land_coupled.json")
    if not d:
        return {}
    m = {}
    tab = {r["run"]: r for r in d["table"]}
    names = {10: "Ten", 20: "Twenty", 40: "Forty", 100: "Hundred"}
    for t_um, k in names.items():
        r = tab.get(f"z3_land_t{t_um}_B")
        if r:
            m[f"ZthreeLandB{k}Ploss"] = fx(r["P_loss_w"], 1)
            m[f"ZthreeLandB{k}Land"] = fx(r["P_land_w"], 1)
            m[f"ZthreeLandB{k}Drop"] = fx(r["dV_land_static_one_rail_mV"], 0)
    r = tab.get("z3_land_t40_B")
    if r:
        m["ZthreeLandPlane"] = fx(r["P_board_plane_w"], 1)
        m["ZthreeLandPlaneDrop"] = fx(r["dV_board_static_VDD_mV"], 0)
    r = tab.get("z3_land_t40_A")
    if r:
        m["ZthreeLandAFortyPloss"] = fx(r["P_loss_w"], 1)
    dv = d["derived"]
    m["ZthreeLandTie"] = fx(dv["tie_with_board_planes"]["t_um"], 0)
    m["ZthreeLandTieLandOnly"] = fx(dv["tie_land_only"]["t_um"], 0)
    for key, mac in (("drop_30mV_one_rail", "ZthreeLandThirtyMv"),
                     ("drop_30mV_VDD_plus_GND", "ZthreeLandThirtyMvLoop")):
        v = dv.get(key)
        if isinstance(v, dict):
            val = next((v[k] for k in ("t_um", "t_min_um", "t_um_min") if v.get(k) is not None),
                       None)
            m[mac] = fx(val, 0)
        elif isinstance(v, (int, float)):
            m[mac] = fx(v, 0)
    m["ZthreeLandNote"] = (r"Z3: land-side (40~\textmu m) and board-plane redistribution "
                           r"in the coupled solution.")
    iso = J(TR / "z3_land_isothermal.json") or {}
    if iso:
        m["PIsoLandZthree"] = fx(iso["25.0"]["P"], 1)
        m["PIsoHotLandZthree"] = fx(iso["100.0"]["P"], 1)
        m["IsoHotLandTermsZthree"] = fx(iso["100.0"]["land"] + iso["100.0"]["plane"], 1)
    lb = {"A": SENS / "etm_Z3_HV_S0__z3_top_only.json",
          "B": SENS / "etm_Z3_HV_S0__z3_plate_tim.json"}
    for t, f in lb.items():
        c = _case(f)
        if c:
            m[f"PlossLb{t}Zthree"] = fx(c["P"], 1)
    return m


def feedback_passes():
    """Interface feedback: per-pass values where a case does not converge (Z2 and Z3 under
    cooling A run away; their passes are reported instead of a converged value)."""
    m = {}
    rv = TR / "review_variants"
    for a in ("Z2", "Z3"):
        for it in (1, 2, 3, 4, 5):
            d = J(rv / f"etm_{a}_HV_S0__tim_warp_fb_A_it{it}.json")
            if not d or "mechanics" not in d:
                continue
            k = f"FbPass{['', 'One', 'Two', 'Three', 'Four', 'Five'][it]}A{ATAG[a]}"
            m[f"{k}Ploss"] = fx(d["P_loss_w"], 1)
            m[f"{k}Tmax"] = fx(d["thermal"]["T_max_C"], 1)
            m[f"{k}Warp"] = fx(d["mechanics"]["die_warpage_pv_um"], 1)
    return m



def countopt():
    """The strongest buildable square count (M = 64, N2K2K_A1) through the full Z1 chain
    (agent countopt): synthesized cell (3.74 mm2, five tiers) and the enlarged 4.0-mm2 cell."""
    m = {}
    d = TR / "countopt"
    for tag, f in (("Syn", "etm_Z1_M64N2K2KA1_HV_S0_h1.1_r21.json"),
                   ("Cell", "etm_Z1_M64N2K2KA1C4_HV_S0_h1.1_r21.json")):
        c = _case(d / f)
        if not c:
            continue
        m[f"Count{tag}Ploss"] = fx(c["P"], 1)
        m[f"Count{tag}Tmax"] = fx(c["T"], 1)
        if c["warp"] is not None:
            m[f"Count{tag}Warp"] = fx(c["warp"], 1)
            m[f"Count{tag}Du"] = fx(c["du"], 2)
            m[f"Count{tag}Tjoint"] = fx(c["Tj"], 0)
    r31 = _case(d / "etm_Z1_M64N2K2KA1_HV_S0_h1.1_r31.json")
    if r31:
        m["CountSynPlossFine"] = fx(r31["P"], 1)
    return m


def macros():
    m = {}
    for f in (cooling, feasibility, dse, variants, platform, uncertainty, omitted, fullpkg, decap, solder, vdrop, z3land, feedback_passes, countopt, agents):
        try:
            m.update(f())
        except Exception as e:          # a malformed artifact must not stop the paper build
            print(f"  WARNING review macros {f.__name__}: {e}")
    return m


if __name__ == "__main__":
    for k, v in macros().items():
        print(k, v)
