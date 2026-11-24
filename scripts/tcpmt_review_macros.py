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
    # TCPMT round 3: the manifold plate (production) against the single pass (variant)
    con, sp = p.get("construction") or {}, p.get("single_pass") or {}
    if con:
        m.update({"CoolZones": str(con["n_zones"]),
                  "CoolPassMm": fx(con["pass_length_mm"], 2),
                  "CoolDpFdEnt": fx(hy.get("dp_fd_plus_entrance_kPa"), 0),
                  "CoolDpPlenum": fx(hy.get("dp_plenum_kPa"), 1),
                  "CoolDpHeader": fx((hy.get("dp_turns_kPa") or 0.0)
                                     + (hy.get("dp_header_kPa") or 0.0), 1)})
    if sp:
        m.update({"CoolDpSinglePass": fx(sp["dp_total_kPa"], 0),
                  "CoolPhydSinglePass": fx(sp["P_hydraulic_W"], 1),
                  "CoolDpRatio": fx(sp["dp_total_kPa"] / hy["dp_total_kPa"], 1)
                  if hy.get("dp_total_kPa") else NA})
    for t, v in c["tiers"].items():
        for a, x in v["cases"].items():
            if x.get("missing"):                # a compared case not run yet (tcpmt_cases)
                continue
            k = f"{t}{ATAG[a]}"
            m[f"QplTop{k}"] = fx(x["q_top_plate_W"], 0)
            m[f"QplBot{k}"] = fx(x["q_bottom_plate_W"], 0)
            m[f"QplTot{k}"] = fx(x["Q_total_W"], 0)
            m[f"QplNat{k}"] = fx(x["q_board_natural_W"] + x["q_converter_underside_natural_W"], 1)
    return m


#: feasibility-stage check names -> the short label the tables print
CHECK_LABEL = {"operating_point": "no operating point", "gan_Tj_hs": "GaN T_J (HS)",
               "gan_Tj_ls": "GaN T_J (LS)", "ron_fit": "R_DS(on) fit range",
               "mlcc": "MLCC 125 C", "inductor": "inductor 125 C", "buildup": "dielectric Tg",
               "encapsulant": "encapsulant Tg", "board": "board Tg", "die": "die 105 C",
               "solder_law": "solder law 125 C", "solder_solidus": "solder solidus",
               "bga_current": "BGA 2 A/ball", "bga_sites": "BGA sites",
               "ir_drop": "IR drop 30 mV"}
THERMAL_CHECKS = ("gan_Tj_hs", "gan_Tj_ls", "ron_fit", "mlcc", "inductor", "buildup",
                  "encapsulant", "board", "die")


def _feas_tag(key):
    """feasibility.json case key -> macro tag: production state '<t>_<a>' -> '<t><A>';
    references 'S0_<t>_<a>' -> '<t><A>Szero', 'S1_A_<a>' -> 'Sone<A>' (the earlier name) and
    'S1_B_<a>' -> 'B<A>Sone'."""
    p = key.split("_")
    if len(p) == 2:
        return f"{p[0]}{ATAG[p[1]]}"
    st, t, a = p
    if st == "S1" and t == "A":
        return f"Sone{ATAG[a]}"
    return f"{t}{ATAG[a]}{'Szero' if st == 'S0' else 'Sone'}"


def feasibility():
    """The feasibility stage (tcpmt_feasibility): per compared case the junction bound of the
    hotter device tier, component and material maxima, the die, the verdict and the failing
    limits; the ranking of each cooling tier counts only feasible candidates."""
    f = J(TR / "feasibility.json")
    if not f or "records" not in f:
        return {}
    lim = f["limits"]
    m = {"GanTjMax": fx(lim["gan_Tj_C"], 0), "RonFitMax": fx(lim["ron_fit_max_C"], 0),
         "DieTmax": fx(lim["die_C"], 0), "IrDropMax": fx(lim["ir_drop_mV_per_rail"], 0),
         "BgaPowerFracMax": fx(100 * lim["bga_power_site_fraction_max"], 0),
         "FeasNcases": str(f["summary"]["n_cases"]),
         "FeasNinfeasible": str(len(f["summary"]["infeasible"])),
         "FeasNunresolved": str(len(f["summary"]["unresolved"]))}
    for key, c in f["cases"].items():
        k = _feas_tag(key)
        ch = c["checks"]
        tj = [v for v in (c.get("junction_C") or {}).values() if v is not None]
        if tj:
            m[f"Tj{k}"] = fx(max(tj), 1)
            m[f"TjMargin{k}"] = fx(lim["gan_Tj_C"] - max(tj), 0)
        rg = c.get("regions") or {}
        cap = [rg.get("caps_in_cells"), rg.get("ind_in_cells")]
        if all(x is not None for x in cap):
            m[f"Tcap{k}"] = fx(max(cap), 1)
        for name, reg in (("Trdl", "rdl_all"), ("Tenc", "encapsulant"), ("Tboardmax", "board")):
            if rg.get(reg) is not None:
                m[f"{name}{k}"] = fx(rg[reg], 1)
        if c.get("die_T_max_C") is not None:
            m[f"Tdiemax{k}"] = fx(c["die_T_max_C"], 1)
        if (ch.get("ir_drop") or {}).get("value") is not None:
            m[f"VdropMax{k}"] = fx(ch["ir_drop"]["value"], 1)
            m[f"VdropLoop{k}"] = fx(ch["ir_drop"]["loop_mV"], 1)
        if (ch.get("bga_current") or {}).get("value") is not None:
            m[f"BgaPeak{k}"] = fx(ch["bga_current"]["value"], 2)
        th = [x for x in THERMAL_CHECKS if x in ch]
        thermal_fail = [x for x in th if ch[x]["ok"] is False]
        thermal_open = [x for x in th if ch[x]["ok"] is None]
        m[f"FeasThermal{k}"] = ("no" if thermal_fail else "open" if thermal_open else "yes")
        for grp, names in (("Solder", ("solder_law", "solder_solidus")),
                           ("Bga", ("bga_current", "bga_sites")), ("Drop", ("ir_drop",)),
                           ("Die", ("die",))):
            oks = [ch[x]["ok"] for x in names if x in ch]
            m[f"Feas{grp}{k}"] = ("n/a" if not oks else "no" if False in oks
                                  else "open" if None in oks else "yes")
        m[f"Nfail{k}"] = str(len(c["fails"]))
        m[f"Feasible{k}"] = {"feasible": "yes", "infeasible": "no"}.get(c["verdict"], "open")
        m[f"FeasFails{k}"] = ", ".join(CHECK_LABEL.get(x, x) for x in c["fails"]) or "none"
        hb = ((c.get("omitted_losses") or {}).get("bundles") or {}).get("high") or {}
        if hb:
            m[f"OmitHiFails{k}"] = (", ".join(CHECK_LABEL.get(x, x) for x in hb["fails"])
                                    or "none")
            m[f"OmitHiDp{k}"] = fx(hb["dP_w"], 0)
            for chk in ("mlcc", "ron_fit", "solder_law", "die"):
                if chk in hb["checks"]:
                    m[f"OmitHi{chk.title().replace('_', '')}{k}"] = fx(hb["checks"][chk]["value"], 1)
    for key, rk in (f.get("rankings") or {}).items():
        st, t = key.split("_")
        tag = t + ("" if st == f.get("production_state", "SDEC") else
                   {"S0": "Szero", "S1": "Sone"}.get(st, st))
        m[f"Rank{tag}"] = (" < ".join(rk["ranked"]) if rk["ranked"] else "none feasible")
        m[f"RankComplete{tag}"] = "yes" if rk["complete"] else "no"
        m[f"Excluded{tag}"] = "; ".join(
            f"{e['arch']} ({', '.join(CHECK_LABEL.get(x, x) for x in (e['fails'] or e['unresolved']))})"
            for e in rk["excluded"]) or "none"
    og = f.get("omitted_gap_shift") or {}
    for t, v in (og.get("by_tier") or {}).items():
        for b in ("nominal", "high"):
            bt = "Nom" if b == "nominal" else "Hi"
            m[f"OmitShiftDirect{t}{bt}"] = fx(v["direct_max_w"][b], 2)
            m[f"OmitShiftFb{t}{bt}"] = fx(v["feedback_max_w"][b], 1)
            m[f"OmitShiftTot{t}{bt}"] = fx(v["total_max_w"][b], 1)
        m[f"OmitSmallestGap{t}"] = fx(v["smallest_gap_w"], 1)
    return m


def bga_count():
    """The 48-V ball count re-closed at the production waveform (final_closure_pkg_network
    reclose -> research/final_closure/bga_count_production.json). Review round 3 (the authors'
    decision of 2026-11-22): the ADOPTED count of each architecture (the smallest legal count
    meeting the per-ball target by the DC peak x k rule, within the site budget), its per-ball
    current, site fraction, 48-V loop, the 1.5-A sensitivity, Z1's port-model RMS bound, the
    modelled arrangement it replaces and the change of each production case's BGA feed terms.
    BgaNmatch: the smallest common count meeting the target for both architectures."""
    d = J(SENS.parent / "bga_count_production.json")   # campaign hook (SENS: final_closure/sensitivity)
    if not d:
        return {}
    cl = d["closure"]
    ad0 = d.get("adopted_count") or {}
    m = {"BgaKeq": fx(d["k_eq"], 2),
         # the k the count rule closes each count at: the upper end of the k_eq band
         "BgaKeqCountRule": fx(d.get("k_eq_count_rule"), 2),
         # the smallest count both architectures meet: the larger adopted count (the screen-
         # first common count, matched_count_dc_rule, can sit one step above it)
         "BgaNmatch": str(max(int(v) for v in ad0.values()) if ad0 else
                          (d.get("matched_count_dc_rule") or d.get("matched_count") or NA)),
         "BgaNmatchSzero": str(d.get("matched_count_S0") or NA),
         "BgaIrmsZone": fx(d["currents_A"]["Z1"]["HV_SDEC"], 1),
         "BgaTarget": fx(d.get("criterion_A_per_ball"), 0),
         "BgaTargetSens": fx(d.get("criterion_sensitivity_A_per_ball"), 1)}
    ad = d.get("adopted_count") or {}
    bc = d.get("ball_currents_at_count") or {}
    if d.get("modelled_count"):
        m["BgaNmodel"] = str(d["modelled_count"])
    for a, tag in (("Z1", "Zone"), ("Z2", "Ztwo")):
        sb = (d.get("site_budget") or {}).get(a) or {}
        if sb:
            m[f"BgaSitesTotal{tag}"] = str(sb["sites"])
            m[f"BgaSiteCap{tag}"] = str(sb["cap_per_rail"])
        pa = (bc.get("per_arch") or {}).get(a) or {}
        if a in ad and pa:
            m[f"BgaNadopt{tag}"] = str(ad[a])
            m[f"BgaSitesAdopt{tag}"] = str(2 * int(ad[a]))
            m[f"BgaSiteFrac{tag}"] = fx(100.0 * pa["site_fraction"], 1)
            m[f"BgaIball{tag}"] = fx(pa["I_ball_closure_rule_A"], 2)
            m[f"BgaMargin{tag}"] = fx(pa.get("margin_A"), 4)
            # the count rule's view: the upper end of the k_eq band
            if pa.get("I_ball_at_band_A") is not None:
                m[f"BgaIballBand{tag}"] = fx(pa["I_ball_at_band_A"], 2)
                m[f"BgaMarginBand{tag}"] = fx(pa.get("margin_at_band_A"), 4)
            m[f"BgaPasses{tag}"] = "yes" if pa.get("passes") else "no"
            fe = pa.get("feed") or {}
            if fe.get("R_loop_20C_ohm"):
                m[f"BgaRloop{tag}"] = fx(1e3 * fe["R_loop_20C_ohm"], 2)
                m[f"BgaRloopModel{tag}"] = fx(1e3 * fe["R_loop_20C_modelled_ohm"], 2)
        mo = ((d.get("modelled_arrangement") or {}).get("per_arch") or {}).get(a) or {}
        if mo:
            m[f"BgaIballModel{tag}"] = fx(mo["I_ball_closure_rule_A"], 2)
            m[f"BgaSiteFracModel{tag}"] = fx(100.0 * mo["site_fraction"], 1)
        sc = (d.get("sensitivity_count") or {}).get(a) or {}
        if sc:
            m[f"BgaNsens{tag}"] = str(sc["n_per_rail"]) if sc.get("n_per_rail") else "none"
            if sc.get("n_per_rail"):
                m[f"BgaSensInBudget{tag}"] = "yes" if sc.get("within_site_budget") else "no"
    z1 = (bc.get("per_arch") or {}).get("Z1") or {}
    if z1.get("I_ball_rms_max_A") is not None:
        m["BgaRmsBoundZone"] = fx(z1["I_ball_rms_max_A"], 2)
    if bc.get("k_eq_port_model_at_count") is not None:
        m["BgaKeqAtCountZone"] = fx(bc["k_eq_port_model_at_count"], 2)
    m.update(_z3_1v_balls(d))
    ce = d.get("coupled_effect") or {}
    for key, r in (ce.get("per_case") or {}).items():
        t, a = key.split("_")
        if r.get("coupled"):
            m[f"BgaFeedDp{t}{ATAG[a]}"] = f"{r['dP_W']:+.2f}"
    if ce:
        m["BgaFeedDpMax"] = fx(ce.get("max_abs_dP_W"), 2)
        m["BgaFeedDpThreshold"] = fx(ce.get("threshold_W"), 1)
    for a, tag in (("Z1", "Zone"), ("Z2", "Ztwo")):
        for s, st in (("HV_S0", "Szero"), ("HV_SDEC", "")):
            v = cl.get(f"{a}__{s}") or {}
            if v.get("n_min"):
                m[f"BgaNmin{tag}{st}"] = str(v["n_min"])
                m[f"BgaPeakAtNmin{tag}{st}"] = fx(v.get("peak_at_n_min_A"), 2)
        # the production state: the adoption's verified minimum (the screen-first closure can
        # sit one step above it when the screen and the verification level straddle the target)
        ado = (d.get("adoption") or {}).get(a) or {}
        if ado.get("status") == "CLOSED" and ado.get("n_per_rail"):
            m[f"BgaNmin{tag}"] = str(ado["n_per_rail"])
            m[f"BgaPeakAtNmin{tag}"] = fx(ado.get("peak_A"), 2)
        hi = cl.get(f"{a}__HV_SDEC__k_hi") or {}
        if hi.get("n_min_screen"):
            m[f"BgaNminKhi{tag}"] = str(hi["n_min_screen"])
    pn = J(SENS.parent / "package_network.json") or {}   # campaign hook
    pa = J(SENS.parent / "package_network_adopted.json") or {}   # review round 3: adopted
    if pa.get("loop", {}).get("Z1"):
        conv = pa["convergence"]
        f1 = max(conv["Z1_supply"]["final"]["i_ball_max_a"],
                 conv["Z1_return"]["final"]["i_ball_max_a"])
        m["BgaNcurrent"] = str(pa["loop"]["Z1"]["n_per_rail"])
        m["BgaPeakCurrentCountProd"] = fx(f1 * d["currents_A"]["Z1"]["HV_SDEC"], 2)
    elif pn:
        conv = pn["convergence"]
        f1 = max(conv["Z1_supply"]["final"]["i_ball_max_a"],
                 conv["Z1_return"]["final"]["i_ball_max_a"])
        m["BgaNcurrent"] = str(pn["matched_count"])
        m["BgaPeakCurrentCountProd"] = fx(f1 * d["currents_A"]["Z1"]["HV_SDEC"], 2)
    m.update(bga_sites())
    return m


def _z3_1v_balls(d):
    """Z3's 1-V balls (review round 3: the same per-ball rule at DC with equal sharing, the Z3
    design record's count): the count the production case carries, its site fraction of the
    full lattice, the per-ball current, and the count the 1.5-A sensitivity would need."""
    import math
    import re
    import tcpmt_cases as TC
    p = TC.case_path(TC.PRODUCTION_STATE, "A", "Z3")
    c = J(p) if p else None
    rows = {r["term"]: r for r in (c or {}).get("ledger_rows") or []}
    if "P_BGA_1V_VDD" not in rows:
        return {}
    n = int(re.search(r"N=(\d+)", rows["P_BGA_1V_VDD"]["conductor"]).group(1))
    sites = int(((d.get("site_budget") or {}).get("Z1") or {}).get("sites") or 1369)
    fmax = float(((d.get("site_budget") or {}).get("Z1") or {}).get("fraction_max") or 0.75)
    i_rail = 1000.0                                  # the 1-V DC rail current, P_load / V_out
    sens = float(d.get("criterion_sensitivity_A_per_ball") or 1.5)
    n_s = math.ceil(i_rail / sens - 1e-12)
    return {"BgaNadoptZthree": str(n), "BgaSitesAdoptZthree": str(2 * n),
            "BgaSiteFracZthree": fx(100.0 * 2 * n / sites, 1),
            "BgaIballZthree": fx(i_rail / n, 2),
            "BgaNsensZthree": str(n_s),
            "BgaSensInBudgetZthree": "yes" if 2 * n_s / sites <= fmax else "no"}


def bga_sites():
    """Ball sites carrying power, per compared case (Table V): Z1 its 48-V balls (the case's
    own count, or the re-closure's adopted count when the case stands for it:
    final_closure_ledger.accepted_count, the count the feasibility stage checks), Z2 the
    BGA-ring feed of the platform accounting (outside its package-internal boundary, but power
    sites of the package), Z3 its 1-V balls."""
    import re
    import final_closure_ledger as FL
    import tcpmt_cases as TC
    pl = J(TR / "platform_inclusive.json") or {}
    ring = (pl.get("feed_design") or {}).get("Z2_bga_ring") or {}
    m = {}
    for st, suf in ((TC.PRODUCTION_STATE, ""), ("S0", "Szero")):
        for t in TC.TIERS:
            for a in TC.ARCHS:
                p = TC.case_path(st, t, a)
                c = J(p) if p else None
                if not c:
                    continue
                rows = {r["term"]: r for r in c["ledger_rows"]}
                n = None
                if "P_BGA_supply" in rows:
                    n_case = int(re.search(r"N=(\d+)", rows["P_BGA_supply"]["conductor"]).group(1))
                    n = 2 * (FL.accepted_count("Z1", n_case, SENS.parent)[0] or n_case)
                elif a == "Z2" and ring.get("n_per_rail"):
                    n = 2 * int(ring["n_per_rail"])
                elif "P_BGA_1V_VDD" in rows:
                    n = 2 * int(re.search(r"N=(\d+)", rows["P_BGA_1V_VDD"]["conductor"]).group(1))
                if n is not None:
                    m[f"BgaSites{t}{ATAG[a]}{suf}"] = str(n)
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
    """Feedback, die power map and caloric correction, against each tier's base case: the
    production state (implemented decoupling, HV_SDEC runs) under the plain names, the S0
    reference under '...Szero' names. A variant built on a superseded uncoupled Z3 case is never
    quoted (tcpmt_cases.SUPERSEDED)."""
    import tcpmt_cases as TC
    m = {}
    for st, suf in ((TC.PRODUCTION_STATE, ""), ("S0", "Szero")):
        scen = TC.SCEN[st]
        base = {(a, t): TC.case_path(st, t, a) for a in TC.ARCHS for t in TC.TIERS}
        # every expected key exists ("--" until its run is complete), so the paper always builds
        for (a, t) in base:
            for tag in ("Fb", "Hot", "Cal"):
                k = f"{tag}{t}{ATAG[a]}"
                for fld in ("Ploss", "dP", "Tmax", "dT", "Warp", "Du", "Tjoint"):
                    m[f"{k}{fld}{suf}"] = NA
                if tag == "Fb":
                    for fld in ("GapMean", "GapPv", "Iters", "Conv"):
                        m[f"{k}{fld}{suf}"] = NA
        m.update(_variant_rows(base, scen, suf, TC))
    return m


def _variant_rows(base, scen, suf, TC):
    m = {}
    for (a, t), bf in base.items():
        b = _case(bf) if bf else None
        if not b:
            continue
        for tag, f in (("Fb", SENS / f"etm_{a}_{scen}__tim_warp_fb_{t}.json"),
                       ("Hot", SENS / f"etm_{a}_{scen}__die_hotspot_{t}.json"),
                       ("Cal", SENS / f"etm_{a}_{scen}__plate_local_h_{t}.json")):
            if TC.is_superseded(f):
                continue
            v = _case(f)
            if not v or v["P"] is None:
                continue
            k = f"{tag}{t}{ATAG[a]}"
            m[f"{k}Ploss{suf}"] = fx(v["P"], 1)
            m[f"{k}dP{suf}"] = fx(v["P"] - b["P"], 1)
            m[f"{k}Tmax{suf}"] = fx(v["T"], 1)
            m[f"{k}dT{suf}"] = fx(v["T"] - b["T"], 1)
            if v["warp"] is not None:
                m[f"{k}Warp{suf}"] = fx(v["warp"], 1)
                m[f"{k}Du{suf}"] = fx(v["du"], 2)
                m[f"{k}Tjoint{suf}"] = fx(v["Tj"], 0)
            if tag == "Fb":
                fb = J(f)
                it = fb.get("iterations") or []
                if it:
                    g = it[0].get("gap") or {}
                    m[f"{k}GapMean{suf}"] = fx(g.get("gap_mean_um"), 0)
                    m[f"{k}GapPv{suf}"] = fx(g.get("gap_pv_um"), 0)
                    m[f"{k}Iters{suf}"] = str(len(it))
                m[f"{k}Conv{suf}"] = "yes" if fb.get("converged") else "no"
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
              "fullpkg_verification.json", "production_converter.json"):
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
    import tcpmt_cases as TC
    for a in ("Z1", "Z2", "Z3"):
        for t in ("A", "B"):
            pth = TC.case_path(TC.PRODUCTION_STATE, t, a)
            c = _case(pth) if pth else None
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


def pair_gap(adj, a, b):
    """Relative gap (hi - lo) / hi between integrations a and b from the adjacent gaps of one
    ordering ({"X<Y": g, ...} in ascending order, tcpmt_solder_constitutive adjacent_gaps_rel).
    The ratios lo / hi = 1 - g multiply along the chain between them, so the result is exact
    whichever of a and b is lower and whether or not they are adjacent; None when the ordering
    does not hold both."""
    keys = [k.split("<") for k in (adj or {})]
    if not keys or any(len(k) != 2 for k in keys):
        return None
    chain = [keys[0][0]] + [hi for _lo, hi in keys]
    if any(keys[i][0] != chain[i] for i in range(len(keys))) or a not in chain or b not in chain:
        return None
    i, j = sorted((chain.index(a), chain.index(b)))
    ratio = 1.0
    for lo, hi in keys[i:j]:
        ratio *= 1.0 - float(adj[f"{lo}<{hi}"])
    return 1.0 - ratio


def _scaled(v, key, f):
    """f x v[key], None when the study left it unresolved."""
    x = (v or {}).get(key)
    return None if x is None else f * x


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
        # the solder study solved the S0 tier cases: the S0 REFERENCE names (review round 2:
        # the production state is the implemented decoupling, solved by the campaign)
        m[f"Eps{t}{ATAG[a]}Szero"] = fx(_scaled(v, "stabilised", 1e3), 2)
        m[f"EpsU{t}{ATAG[a]}Szero"] = fx(_scaled(v, "U_stab_num", 100), 1)
        m[f"EpsFour{t}{ATAG[a]}Szero"] = fx(_scaled(v, "v4", 1e3), 2)
        if v.get("change_4_to_48_rel") is not None:
            (ch_a if t == "A" else ch_b).append(abs(v["change_4_to_48_rel"]))
    m["SolderStabA"] = fx(100 * max(ch_a), 1) if ch_a else NA
    m["SolderStabBLo"], m["SolderStabBHi"] = ((fx(100 * min(ch_b), 1), fx(100 * max(ch_b), 1))
                                              if ch_b else (NA, NA))
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
    # the cooling-B gap between Z1 and Z3 under the alternative law, whichever is lower and
    # whether or not Z2 sits between them (round 2: Z1 < Z3, adjacent)
    g = pair_gap(((co.get("adjacent_gaps_rel") or {}).get("schubert_time_final") or {}).get("B"),
                 "Z1", "Z3")
    m["SchubertGapB"] = fx(None if g is None else 100 * g, 1)
    m["SchubertHold"] = "yes" if co.get("rankings_hold_all_variants") else "no"
    m["CardGridMax"] = fx(100 * d["numerical_tolerance"]["card_grid_sensitivity_max_rel"], 1)
    zl = J(TR / "solder_z3land.json")              # Z3 with the coupled land side
    for t, v in ((zl or {}).get("cases") or {}).items():
        if v.get("stabilised") is not None:
            m[f"Eps{t}ZthreeSzero"] = fx(1e3 * v["stabilised"], 2)
            if v.get("U_stab_num") is not None:
                m[f"EpsU{t}ZthreeSzero"] = fx(100 * v["U_stab_num"], 1)
    return m


def vdrop():
    """Static 1-V drop per tier case (review round 2): the per-rail MAXIMUM drop between the
    converter output and the die (tcpmt_ir_drop: series maxima of the rail -- lumped rows, Z3's
    land side and board planes, the cell's output plane), for the production state under the
    plain names and the S0 reference under '...Szero'; the earlier loss/current mean is kept
    as VdropMean."""
    import tcpmt_cases as TC
    import tcpmt_ir_drop as IR
    m = {}
    for st, suf in ((TC.PRODUCTION_STATE, ""), ("S0", "Szero")):
        for t in TC.TIERS:
            for a in TC.ARCHS:
                p = TC.case_path(st, t, a)
                c = J(p) if p else None
                if not c:
                    continue
                d = IR.static_drop(c, n_vr=(c.get("design") or {}).get("n_vr"))
                k = f"{t}{ATAG[a]}{suf}"
                m[f"Vdrop{k}"] = fx(d["max_mV"], 1)
                m[f"VdropVdd{k}"] = fx(d["VDD_mV"], 1)
                m[f"VdropGnd{k}"] = fx(d["GND_mV"], 1)
                m[f"VdropLoop{k}"] = fx(d["loop_mV"], 1)
                v = d["mean_loss_over_I_mV"]
                m[f"VdropMean{k}"] = fx(v, 2 if v < 1 else 1)
                if a == "Z3":
                    tl = d["terms"]["VDD"]
                    m[f"VdropLand{k}"] = fx(tl.get("land_side_sheet"), 1)
                    m[f"VdropPlanes{k}"] = fx(tl.get("board_plane_sheet"), 1)
    m["VdropLimit"] = fx(IR.LIMIT_MV_PER_RAIL, 0)
    return m


def z3land():
    """Z3 with the land-side and board-plane 1-V redistribution in the coupled ledger (agent
    z3land): thickness sweep, ties, drops, and the lower-bound values of the earlier ledger.
    TCPMT round 3: the uncoupled lower bound is not produced (z3_land_coupled.json records
    `lower_bound.status` = skipped) and a tie may be absent: their macros print NA."""
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
    dv = d.get("derived") or {}
    m["ZthreeLandTie"] = fx((dv.get("tie_with_board_planes") or {}).get("t_um"), 0)
    m["ZthreeLandTieLandOnly"] = fx((dv.get("tie_land_only") or {}).get("t_um"), 0)
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
        # the superseded lower bound, when the root holds it; else NA (the text still compiles)
        m[f"PlossLb{t}Zthree"] = fx(c["P"], 1) if c else NA
    return m


def feedback_passes():
    """Interface feedback: per-pass values of the cooling-A Z2 and Z3 loops, which the paper
    reports where a case does not converge (round 2: both ran away; a runaway is recorded in
    the case's `non_convergence`)."""
    import tcpmt_cases as TC
    m = {}
    rv = TR / "review_variants"
    # TCPMT round 3: the campaign runs the feedback in the production state (HV_SDEC); the
    # round-2 S0 files are the fallback
    scens = (TC.SCEN[TC.PRODUCTION_STATE], "HV_S0")
    for a in ("Z2", "Z3"):
        for it in (1, 2, 3, 4, 5):
            d = next((x for x in (J(rv / f"etm_{a}_{s}__tim_warp_fb_A_it{it}.json")
                                  for s in scens) if x and "mechanics" in x), None)
            if not d:
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
    for f in (cooling, feasibility, bga_count, dse, variants, platform, uncertainty, omitted,
              fullpkg, decap, solder, vdrop, z3land, feedback_passes, countopt, agents):
        try:
            m.update(f())
        except Exception as e:          # a malformed artifact must not stop the paper build
            print(f"  WARNING review macros {f.__name__}: {e}")
    return m


if __name__ == "__main__":
    for k, v in macros().items():
        print(k, v)
