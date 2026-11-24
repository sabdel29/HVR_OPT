"""Macros of the results sections (evaluate, compare, explore, discussion, conclusion) that
results_macros.tex does not carry -> manuscript_v2/macros_results.tex.

Every number is read from the campaign root ($ETM_RESULTS_ROOT, default research/campaign_v3)
or from the design record the campaign ran with (configs/design_points.yaml); a missing artifact
prints "--", never a stale number. All macro names start with "Wr" (no collision with
results_macros.tex or the other writers' files).

Two quantities are evaluated, not only read, with the campaign's own models:
  * the common-temperature ledger in the production state (implemented decoupling): the
    production scenario is registered exactly as the campaign registers it
    (tcpmt_decap_framework._register: package 48-V network at k_eq, cell-internal VIN runs at
    k_open, ring ESR as a row) and checked by reproducing the Z1 cooling-A case at its own
    temperatures; Z3 adds the input-state correction of its base ledger to the coupled
    land-side common-temperature loss (z3_land_isothermal.json);
  * the feasibility filter (tcpmt_feasibility.evaluate, in memory, no file written) of the
    interface-feedback, die-hot-spot and design-variant cases that feasibility.json does not
    hold.

Run:  ETM_RESULTS_ROOT=research/campaign_v3 $PY scripts/tcpmt_writer_macros_results.py
"""
from __future__ import annotations

import csv
import io
import json
import math
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

R = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research" / "campaign_v3").resolve()
os.environ["ETM_RESULTS_ROOT"] = str(ROOT)
FC, TR = ROOT / "final_closure", ROOT / "tcpmt_revision"
SENS = FC / "sensitivity"
OUT = R / "manuscript_v2" / "macros_results.tex"
for p in (R / "scripts", R / "scripts" / "phase0nw"):
    sys.path.insert(0, str(p))

NA = "--"
ATAG = {"Z1": "Zone", "Z2": "Ztwo", "Z3": "Zthree"}
DTAG = {"m25": "Mlo", "m49": "Mhi", "m36t5": "Five", "m36thin": "Thin", "m36": "Prod"}


def J(p):
    p = Path(p)
    try:
        return json.loads(p.read_text()) if p.is_file() else None
    except json.JSONDecodeError:
        return None


def fx(v, n=1):
    try:
        return NA if v is None else f"{float(v):.{n}f}"
    except (TypeError, ValueError):
        return NA


def fsgn(v, n=1):
    """signed, with a proper minus sign (math mode)"""
    if v is None:
        return NA
    s = f"{float(v):+.{n}f}"
    return ("$-$" + s[1:]) if s.startswith("-") else ("$+$" + s[1:])


def case(p):
    c = J(p)
    if not c:
        return None
    me = c.get("mechanics") or {}
    cr = (me.get("joint_search") or {}).get("critical") or {}
    th = c.get("thermal") or {}
    return {"P": c.get("P_loss_w"), "T": th.get("T_max_C"),
            "die": c.get("die_T_max_C") or th.get("die_T_max_C"),
            "warp": me.get("die_warpage_pv_um"), "du": cr.get("du_um"), "Tj": cr.get("T_C"),
            "raw": c}


def quiet(f, *a, **k):
    """call f without its console chatter"""
    buf = io.StringIO()
    with redirect_stdout(buf):
        return f(*a, **k)


# ------------------------------------------------------------------ design record
def design_record():
    import yaml
    return yaml.safe_load((R / "configs" / "design_points.yaml").read_text())["designs"]


def topo(d):
    t = d.get("topology") or {}
    return f"N{t.get('N')}K{t.get('K')}" if t else NA


def designs():
    m = {}
    rec = design_record()
    dc = J(TR / "design_comparison.json") or {}
    D = dc.get("designs") or {}
    prod = D.get("m36") or {}
    for name, tag in DTAG.items():
        d, r = D.get(name) or {}, rec.get(name) or {}
        m[f"Wr{tag}M"] = str(r.get("n_vr", d.get("n_vr", NA)))
        m[f"Wr{tag}Topo"] = topo(r)
        m[f"Wr{tag}Fsw"] = fx((r.get("f_sw_hz") or 0) / 1e3, 0) if r.get("f_sw_hz") else NA
        m[f"Wr{tag}Tiers"] = str(len(r.get("tiers") or [])) if r.get("tiers") else NA
        m[f"Wr{tag}Stack"] = fx((d.get("converter_stack_um") or r.get("converter_stack_um"))
                                and (d.get("converter_stack_um")
                                     or r.get("converter_stack_um")) / 1e3, 2)
        m[f"Wr{tag}Screen"] = fx(d.get("screen_P_total_W"), 1)
        to = r.get("tier_order") or {}
        m[f"Wr{tag}Ar"] = fx(to.get("worst_via_ar_both_faces"), 1)
        if name != "m36" and prod.get("screen_P_total_W") and d.get("screen_P_total_W"):
            m[f"Wr{tag}ScreenD"] = fx(d["screen_P_total_W"] - prod["screen_P_total_W"], 1)
            m[f"Wr{tag}ScreenDAbs"] = fx(abs(d["screen_P_total_W"] - prod["screen_P_total_W"]), 1)
        for key, cs in (d.get("cases") or {}).items():
            a, t = key.split("_")
            k = f"Wr{tag}{t}{ATAG[a]}"
            m[f"{k}Ploss"] = fx(cs.get("P_loss_W"), 1)
            m[f"{k}Tmax"] = fx(cs.get("T_max_C"), 1)
            m[f"{k}Die"] = fx(cs.get("die_T_max_C"), 1)
            m[f"{k}Warp"] = fx(cs.get("die_warpage_pv_um"), 1)
            m[f"{k}Du"] = fx(cs.get("du_c_um"), 2)
            pc = (prod.get("cases") or {}).get(key) or {}
            if name != "m36" and pc.get("die_warpage_pv_um") and cs.get("die_warpage_pv_um"):
                m[f"{k}WarpRatio"] = fx(cs["die_warpage_pv_um"] / pc["die_warpage_pv_um"], 2)
                m[f"{k}DuRatio"] = fx(cs["du_c_um"] / pc["du_c_um"], 2)
            if name != "m36" and pc.get("P_loss_W") is not None:
                dp = cs["P_loss_W"] - pc["P_loss_W"]
                dt = cs["T_max_C"] - pc["T_max_C"]
                m[f"{k}dP"], m[f"{k}dPAbs"] = fsgn(dp, 1), fx(abs(dp), 1)
                m[f"{k}dT"], m[f"{k}dTAbs"] = fsgn(dt, 1), fx(abs(dt), 1)
        # the design's joints: its own v2 law band (production law at its own maximum over the
        # BGA lattice, the other laws at theirs), x 1e-3 per cycle
        for lab, j in (d.get("joints") or {}).items():
            t, a = lab.split("_")
            k = f"Wr{tag}{t}{ATAG[a]}"
            m[f"{k}Eps"] = fx(1e3 * j["production"], 2)
            m[f"{k}EpsLo"], m[f"{k}EpsHi"] = fx(1e3 * j["min"], 2), fx(1e3 * j["max"], 2)
            m[f"{k}Tsj"] = fx(j.get("T_C"), 1)
            m[f"{k}Dudef"] = fx(j.get("du_def_xy_um"), 2)
            pj = (prod.get("joints") or {}).get(lab)
            if name != "m36" and pj:
                r = j["production"] / pj["production"]
                m[f"{k}EpsRatio"] = fx(r, 2)
                m[f"{k}EpsdPct"] = fsgn(100 * (r - 1), 0)
                m[f"{k}EpsdPctAbs"] = fx(abs(100 * (r - 1)), 0)
    # the 5-tier converter in the Z2 board opening: board + BGA depth minus attach + converter
    geo = (J(FC / "architecture_geometry.json") or {}).get("architectures", {}).get("Z2")
    if geo:
        lay = {L["name"]: L for L in geo["layers"]}
        depth = lay["board"]["t_um"] + (lay["bga"]["z1_um"] - lay["bga"]["z0_um"])
        # attach + land-side RDL between the substrate and the converter's first tier
        attach = -next(L for L in geo["layers"] if L["name"].startswith("conv_0"))["z0_um"]
        for name, tag in DTAG.items():
            st = (D.get(name) or {}).get("converter_stack_um")
            if st:
                clr = depth - (attach + st)
                m[f"Wr{tag}BoardClear"] = fx(clr, 0)
                m[f"Wr{tag}Protrude"] = fx(-clr, 0) if clr < 0 else "0"
        m["WrZtwoBoardT"] = fx(lay["board"]["t_um"] / 1e3, 1)
    # the largest change of an alternative design against the production design, over every
    # integration and cooling it ran (e.g. the thin-capacitor tier: Z1/Z2/Z3 x A/B)
    for name, tag in DTAG.items():
        if name == "m36":
            continue
        dps, dts = [], []
        for key, cs in ((D.get(name) or {}).get("cases") or {}).items():
            pc0 = (prod.get("cases") or {}).get(key) or {}
            if pc0.get("P_loss_W") is not None and cs.get("P_loss_W") is not None:
                dps.append(abs(cs["P_loss_W"] - pc0["P_loss_W"]))
                dts.append(abs(cs["T_max_C"] - pc0["T_max_C"]))
        if dps:
            m[f"Wr{tag}DPAbsMax"], m[f"Wr{tag}DTAbsMax"] = fx(max(dps), 1), fx(max(dts), 1)
            m[f"Wr{tag}Ncases"] = str(len(dps))
    rk = (dc.get("ranking") or {}).get("Z1_A") or {}
    m["WrCountSameRank"] = "yes" if rk.get("same_ranking") else "no"
    # the count comparison of the joints under the rule and the law band (Z1, each cooling)
    cj = dc.get("count_joints") or {}
    word = {"resolved": "resolved", "not resolved": "not resolved",
            "conditional on the law": "conditional on the law"}
    for t in ("A", "B"):
        r = cj.get(t) or {}
        if not r.get("complete"):
            continue
        m[f"WrCountEpsSameOrder{t}"] = "yes" if r.get("same_order_all_laws") else "no"
        prod_law = sorted(r["order_by_law"])[0]
        for law, order in r["order_by_law"].items():
            if law.startswith("schubert"):
                prod_law = law
        m[f"WrCountEpsOrder{t}"] = " $<$ ".join(
            f"$M = {D[k]['n_vr']}$" for k in r["order_by_law"][prod_law])
        for k, v in (r.get("pairs_vs_production") or {}).items():
            tag = DTAG.get(k)
            if tag:
                m[f"Wr{tag}{t}EpsVerdict"] = word.get(v.get("verdict"), v.get("verdict") or NA)
                m[f"Wr{tag}{t}EpsLower"] = (f"$M = {D[v['lower']]['n_vr']}$"
                                           if v.get("lower") in D else NA)
        vs = [v.get("verdict") for v in (r.get("pairs_vs_production") or {}).values()]
        m[f"WrCountEpsAllResolved{t}"] = "yes" if vs and all(x == "resolved" for x in vs) \
            else "no"
    return m


# ------------------------------------------------------------------ common temperature
def common_temperature():
    """production-state (implemented decoupling) ledger with every region at 25 / 100 C"""
    import final_closure_ledger as FL
    import tcpmt_decap_framework as DF
    dec = J(TR / "input_decoupling.json") or {}
    rec = ((dec.get("framework") or {}).get("ledger_at_S0_temperatures") or {}).get(
        "recommended") or {}
    k_eq, p_esr = rec.get("k_eq"), rec.get("P_ring_esr_W", 0.0)
    k_open = (dec.get("summary") or {}).get("k_open_cell_waveform")
    if not (k_eq and k_open):
        return {}
    quiet(DF._register, k_eq, k_open, p_esr, key="HV_SDEC")
    m = {}
    c = J(SENS / "etm_Z1_HV_SDEC__sdec_A.json")
    h = c["et_history"][-1]
    temps = {k[2:-2]: v for k, v in h.items() if k.startswith("T_") and k.endswith("_C")}
    rep = quiet(FL.self_consistent, "Z1", "HV_SDEC", temps)["P_loss_w"]
    m["WrIsoReproW"] = fx(abs(rep - c["P_loss_w"]), 3)
    keys = ("conv", "hs", "ls", "ind", "caps", "bga", "sub", "interface", "attach", "pcb_via")
    land = J(TR / "z3_land_isothermal.json") or {}
    vals = {}
    for T, tag in ((25.0, "Lo"), (100.0, "Hi")):
        for a in ("Z1", "Z2", "Z3"):
            L = quiet(FL.self_consistent, a, "HV_SDEC", {k: T for k in keys})
            p = L["P_loss_w"]
            if a == "Z3":
                base0 = quiet(FL.self_consistent, "Z3", "HV_S0", {k: T for k in keys})["P_loss_w"]
                lv = (land.get(f"{T:.1f}") or {}).get("P")
                p = None if lv is None else lv + (p - base0)
            if a == "Z1":
                m[f"WrIsoConv{tag}"] = fx(sum(r["P_w"] for r in L["rows"]
                                              if r["term"].startswith("P_conv")), 1)
            vals[(tag, a)] = p
            m[f"WrIso{tag}{ATAG[a]}"] = fx(p, 1)
        for b in ("Z2", "Z3"):
            if vals.get((tag, b)) is not None:
                m[f"WrIsoGap{tag}{ATAG[b]}"] = fx(abs(vals[(tag, b)] - vals[(tag, "Z1")]), 1)
    pa = (J(SENS / "etm_Z1_HV_SDEC__sdec_A.json") or {}).get("P_loss_w")
    if pa and vals.get(("Lo", "Z1")):
        m["WrUnderAZone"] = fx(100 * (pa - vals[("Lo", "Z1")]) / pa, 0)
        m["WrRiseAZone"] = fx(pa - vals[("Lo", "Z1")], 1)
    return m


# ------------------------------------------------------------------ the evaluated design
def evaluate_z1():
    m = {}
    c = J(SENS / "etm_Z1_HV_SDEC__sdec_A.json")
    if not c:
        return m
    rows = {r["term"]: r["P_w"] for r in c["ledger_rows"]}
    P = c["P_loss_w"]
    m["WrEffAZone"] = fx(100 * 1000.0 / (1000.0 + P), 1)
    m["WrEtItersAZone"] = str(len(c["et_history"]))
    hv = sum(rows.get(t, 0.0) for t in ("P_pkg_RDL_HV_supply", "P_pkg_RDL_HV_return",
                                        "P_BGA_supply", "P_BGA_return"))
    m["WrPhvAZone"] = fx(hv, 1)
    m["WrPintraAZone"] = fx(rows.get("P_intraVR_metal", 0) + rows.get("P_intraVR_vertical", 0), 1)
    m["WrPringAZone"] = fx(rows.get("P_Cin_ring_ESR"), 2)
    m["WrPconvLsAZone"] = fx(rows.get("P_conv_ls"), 1)
    m["WrPconvHsAZone"] = fx(rows.get("P_conv_hs"), 1)
    m["WrPconvIndAZone"] = fx(rows.get("P_conv_inductor_dcr"), 1)
    m["WrPconvCapAZone"] = fx(rows.get("P_conv_cap_esr"), 1)
    conv = sum(v for k, v in rows.items() if k.startswith("P_conv"))
    m["WrLsShareAZone"] = fx(100 * rows.get("P_conv_ls", 0) / conv, 0)
    rg = c["thermal"]["region_T_max_C"]
    tiers = sorted(k for k in rg if k.startswith("tier:"))
    for i, k in enumerate(tiers, 1):
        m[f"WrTtier{['', 'One', 'Two', 'Three', 'Four', 'Five'][i]}AZone"] = fx(rg[k], 1)
    m["WrTdieMeanAZone"] = fx(c.get("die_T_mean_C"), 1)
    h = c["et_history"][-1]
    m["WrTlsRiseAZone"] = fx(h["T_ls_C"] - 25.0, 0)
    m["WrThsRiseAZone"] = fx(h["T_hs_C"] - 25.0, 0)
    ic = c["mechanics"]["interconnects"]
    bga, itf = ic["bga"]["critical"], ic["interface"]["critical"]
    m["WrCritXAZone"] = fx(abs(bga["x_mm"]), 1)
    m["WrGamBgaAZone"] = fx(1e3 * bga["gamma"], 1)
    m["WrGamIfAZone"] = fx(1e3 * itf["gamma"], 0)
    m["WrTIfAZone"] = fx(itf["T_C"], 0)
    m["WrGamRatioAZone"] = fx(itf["gamma"] / bga["gamma"], 0)
    m["WrNIfSites"] = str(ic["interface"]["n_sites"])
    m["WrHIfUm"] = fx(ic["interface"]["h_um"], 0)
    # feasibility margins of the production Z1 case under cooling A (feasibility.json)
    fe = J(TR / "feasibility.json") or {}
    ch = ((fe.get("cases") or {}).get("A_Z1") or {}).get("checks") or {}
    for key, tag in (("ron_fit", "Ron"), ("mlcc", "Mlcc"), ("inductor", "Ind"), ("die", "Die"),
                     ("solder_law", "Solder"), ("ir_drop", "Vdrop"), ("gan_Tj_hs", "Gan")):
        if ch.get(key, {}).get("margin") is not None:
            m[f"Wr{tag}MarginAZone"] = fx(ch[key]["margin"], 1)
            m[f"Wr{tag}ValAZone"] = fx(ch[key]["value"], 1)
    return m


def interconnects():
    """every interconnect layer's critical site (driver gamma = |du_xy| / h), every case"""
    import tcpmt_cases as TC
    m = {}
    names = {"bga": "Bga", "interface": "If", "conv_attach_vr_substrate": "Att",
             "z3_attach_vr_pcb": "Att"}
    for t in ("A", "B"):
        for a in ("Z1", "Z2", "Z3"):
            p = TC.case_path("SDEC", t, a)
            c = J(p) if p else None
            if not c:
                continue
            for lay, v in ((c.get("mechanics") or {}).get("interconnects") or {}).items():
                tag = names.get(lay)
                cr = (v or {}).get("critical") or {}
                if not tag or cr.get("gamma") is None:
                    continue
                k = f"WrGam{tag}{t}{ATAG[a]}"
                m[k] = fx(1e3 * cr["gamma"], 1)
                m[f"WrT{tag}{t}{ATAG[a]}"] = fx(cr.get("T_C"), 0)
    return m


# ------------------------------------------------------------------ decoupling
def decoupling():
    d = J(TR / "input_decoupling.json")
    if not d:
        return {}
    s = d["summary"]
    pk = s["placement_k_eq"]
    rec = s.get("recommended") or {}
    m = {"WrKrms": fx(pk["i_dual6+c_ring"]["nominal"], 2),
         "WrKrmsLo": fx(pk["i_dual6+c_ring"]["band"][0], 2),
         "WrKrmsHi": fx(pk["i_dual6+c_ring"]["band"][1], 2),
         "WrKopen": fx(s["k_open_cell_waveform"], 2),
         "WrKsync": fx(pk["none_sync"]["nominal"], 2),
         # the bare-decoupling reference case: a rectangular pulse at the buck duty, 1/sqrt(D)
         "WrKbare": fx(((d.get("circuit") or {}).get("waveform") or {}).get("rect_D", {}).get(
             "k_open"), 1),
         "WrKgap": fx(pk["b_gap_0402_X7R"]["nominal"], 1),
         "WrKgapHi": fx(pk["b_gap_0402_X7R"]["band"][1], 0),
         "WrKring": fx(pk["c_ring_1206_X7S"]["nominal"], 2),
         "WrKinter": fx(pk["i_dual6"]["nominal"], 2),
         "WrKlatin": fx(pk["i_latin6+c_ring"]["nominal"], 2),
         "WrKspread": fx(pk["i_spread36+c_ring"]["nominal"], 2),
         "WrCchargeOneV": fx(s["requirement_charge_balance_uF_per_cell"]["1V"], 2),
         "WrCkTwelve": fx(s["C_for_k_le_1p2_uF_per_cell"]["100"], 0),
         "WrLloop": fx(s["loop_inductance_nominal_pH"], 0),
         "WrLloopLo": fx(s["loop_inductance_band_pH"][0], 0),
         "WrLloopHi": fx(s["loop_inductance_band_pH"][1], 0),
         "WrRloopHot": fx(s.get("network_R_loop_hot_mohm"), 2),
         "WrNphases": str(rec.get("n_clock_phases", NA)),
         "WrNphaseGroup": str(int(rec["n_clock_phases"]) // 2) if rec.get("n_clock_phases") else NA,
         "WrNring": str(rec.get("count", NA)),
         "WrRingCeach": fx(rec.get("C_each_48V_25C_uF"), 1),
         "WrRingCtot": fx((rec.get("C_each_48V_25C_uF") or 0) * (rec.get("count") or 0), 0)
         if rec.get("count") else NA}
    gp = (d.get("placement") or {}).get("gap_count") or {}
    m["WrGapCapsPerCell"] = str(gp.get("per_cell", NA))
    fw = (d.get("framework") or {}).get("ledger_at_S0_temperatures") or {}
    cs = (fw.get("cases") or {}).get("i_dual6+c_ring") or {}
    m["WrDecapFixedT"] = fx(cs.get("delta_vs_S0_W"), 1)
    m["WrHotLoop"] = fx(cs.get("hotloop_correction_W"), 1)
    a0, a1 = J(FC / "etm_Z1_HV_S0_h1.1_r21.json"), J(SENS / "etm_Z1_HV_SDEC__sdec_A.json")
    if a0 and a1:
        m["WrDecapCoupledA"] = fx(a1["P_loss_w"] - a0["P_loss_w"], 1)
    return m


# ------------------------------------------------------------------ BGA provisioning
def bga():
    d = J(FC / "bga_count_production.json")
    if not d:
        return {}
    cl = d["closure"]
    m = {"WrBgaRule": fx(d["criterion_A_per_ball"], 0),
         "WrBgaRuleSens": fx(d["criterion_sensitivity_A_per_ball"], 1),
         "WrBgaNmax": str(d.get("n_max_per_rail", NA))}
    sites = (J(TR / "feasibility.json") or {}).get("bga_sites") or {}
    for a in ("Z1", "Z2"):
        # the ADOPTED count (smallest legal count meeting the target within the site budget);
        # the closure's n_min is only the screen's first verified pass and may not be minimal
        ad = (d.get("adoption") or {}).get(a) or {}
        v = cl.get(f"{a}__HV_SDEC") or {}
        n, i_ball = ad.get("n_per_rail"), ad.get("peak_A")
        if n is None and v.get("n_min"):
            n, i_ball = v["n_min"], v.get("peak_at_n_min_A")
        if n:
            m[f"WrBgaN{ATAG[a]}"] = str(n)
            m[f"WrBgaI{ATAG[a]}"] = fx(i_ball, 2)
            if sites.get(a):
                m[f"WrBgaFrac{ATAG[a]}"] = fx(100 * 2 * n / sites[a], 1)
        s = (d.get("closure_sensitivity") or {}).get(f"{a}__HV_SDEC") or {}
        m[f"WrBgaSensStatus{ATAG[a]}"] = s.get("status", NA)
        if s.get("n_min_screen"):
            m[f"WrBgaSensN{ATAG[a]}"] = str(s["n_min_screen"])
            if sites.get(a):
                m[f"WrBgaSensFrac{ATAG[a]}"] = fx(100 * 2 * s["n_min_screen"] / sites[a], 0)
    m["WrBgaSitesZone"] = str(sites.get("Z1", NA))
    m["WrBgaSitesZtwo"] = str(sites.get("Z2", NA))
    pa = ((d.get("ball_currents_at_count") or {}).get("per_arch") or {}).get("Z1") or {}
    m["WrBgaRmsZone"] = fx(pa.get("I_ball_rms_max_A"), 1)
    # Z1 at its legal maximum count (the 1.5-A sensitivity) and the bare-decoupling current there
    sc = ((d.get("sensitivity_count") or {}).get("Z1") or {})
    vmax = (sc.get("verified") or {}).get(str(d.get("n_max_per_rail"))) or {}
    if vmax.get("peak_A") is not None:
        m["WrBgaAtNmaxZone"] = fx(vmax["peak_A"], 2)
        i_eq = (d.get("currents_A") or {}).get("Z1", {}).get("HV_SDEC")
        i_bare = (d.get("currents_A") or {}).get("Z1", {}).get("HV_S1")
        if vmax.get("peak_fraction") and i_bare:
            m["WrBgaBareAtNmaxZone"] = fx(vmax["peak_fraction"] * i_bare, 1)
    ce = ((d.get("coupled_effect") or {}).get("per_case") or {})
    for key in ("A_Z1", "B_Z1"):
        if (ce.get(key) or {}).get("dP_W") is not None:
            m[f"WrBgaFeedDp{key[0]}Zone"] = fx(ce[key]["dP_W"], 1)
    sb = (d.get("site_budget") or {}).get("Z2") or {}
    if sb.get("cap_per_rail"):
        m["WrBgaCapZtwo"] = str(sb["cap_per_rail"])
    # Z3 1-V balls (feasibility record, production cooling B)
    z3 = (((J(TR / "feasibility.json") or {}).get("cases") or {}).get("B_Z3") or {}).get("checks") or {}
    bc, bs = z3.get("bga_current") or {}, z3.get("bga_sites") or {}
    if bc.get("n_per_rail"):
        m["WrBgaNZthree"] = str(bc["n_per_rail"])
        m["WrBgaIZthree"] = fx(bc.get("value"), 1)
    if bs.get("value") is not None and sites.get("Z3"):
        m["WrBgaFracZthree"] = fx(100 * bs["value"], 0)
        m["WrBgaLeftZthree"] = str(round(sites["Z3"] * (1 - bs["value"])))
    return m


# ------------------------------------------------------------------ feasibility in memory
def feasibility_variants():
    """feasibility filter of cases feasibility.json does not hold (feedback, hot spot, the
    caloric variant) -- verdict, failing limits and the binding margins"""
    import tcpmt_feasibility as F
    m = {}
    lab = {"gan_Tj_hs": "GaN junction", "gan_Tj_ls": "GaN junction", "ron_fit": "on-resistance fit",
           "mlcc": "MLCC", "inductor": "inductor", "buildup": "dielectric", "encapsulant":
           "encapsulant", "board": "board", "die": "die", "solder_law": "solder law",
           "ir_drop": "static drop", "bga_sites": "ball sites", "bga_current": "ball current"}
    for tag, var in (("Fb", "tim_warp_fb"), ("Hot", "die_hotspot"), ("Cal", "plate_caloric_legacy")):
        for t in ("A", "B"):
            for a in ("Z1", "Z2", "Z3"):
                p = SENS / f"etm_{a}_HV_SDEC__{var}_{t}.json"
                c = J(p)
                if not c:
                    continue
                try:
                    r = quiet(F.evaluate, p, c, use_fields=False)
                except Exception as e:                       # noqa: BLE001 -- recorded
                    print(f"  feasibility {p.name}: {e}")
                    continue
                ch = r["checks"]
                # the BGA checks follow Table V (the production case of this integration)
                fails = [x for x in r["fails"] if not x.startswith("bga")]
                k = f"Wr{tag}{t}{ATAG[a]}"
                m[f"{k}Feas"] = "yes" if not fails else "no"
                seen = []
                for x in fails:
                    if lab.get(x, x) not in seen:
                        seen.append(lab.get(x, x))
                m[f"{k}Fails"] = ", ".join(seen) or "none"
                for key, nm in (("ron_fit", "Ron"), ("mlcc", "Mlcc"), ("die", "Die"),
                                ("solder_law", "Solder"), ("gan_Tj_hs", "Gan")):
                    v = ch.get(key) or {}
                    if v.get("value") is not None:
                        m[f"{k}{nm}"] = fx(v["value"], 1)
                        m[f"{k}{nm}Margin"] = fx(v["limit"] - v["value"], 1)
                m[f"{k}Die"] = fx(r.get("die_T_max_C"), 1)
    return m


def design_feasibility():
    """thermal, die and solder-law checks of the design variants (the count neighbours, the
    5-tier converter, the thin capacitor) under cooling A and B; their BGA and static-drop
    checks would need each design's own package network and are not claimed"""
    import tcpmt_feasibility as F
    m = {}
    keep = ("gan_Tj_hs", "gan_Tj_ls", "ron_fit", "mlcc", "inductor", "buildup", "encapsulant",
            "board", "die", "solder_law")
    lab = {"gan_Tj_hs": "GaN junction", "gan_Tj_ls": "GaN junction", "ron_fit":
           "on-resistance fit", "mlcc": "MLCC", "inductor": "inductor", "buildup": "dielectric",
           "encapsulant": "encapsulant", "board": "board", "die": "die", "solder_law": "solder law"}
    for name, tag in DTAG.items():
        if name == "m36":
            continue
        for t in ("A", "B"):
            for a in ("Z1", "Z2", "Z3"):
                p = ROOT / "designs" / name / "final_closure" / "sensitivity" / f"etm_{a}_HV_SDEC__sdec_{t}.json"
                c = J(p)
                if not c:
                    continue
                try:
                    r = quiet(F.evaluate, p, c, use_fields=False)
                except Exception as e:                       # noqa: BLE001 -- recorded
                    print(f"  design feasibility {name} {a} {t}: {e}")
                    continue
                ch = r["checks"]
                fails = [x for x in keep if (ch.get(x) or {}).get("ok") is False]
                k = f"Wr{tag}{t}{ATAG[a]}"
                m[f"{k}Feas"] = "yes" if not fails else "no"
                seen = []
                for x in fails:
                    if lab[x] not in seen:
                        seen.append(lab[x])
                m[f"{k}Fails"] = ", ".join(seen) or "none"
                for key, nm in (("ron_fit", "Ron"), ("mlcc", "Mlcc"), ("solder_law", "Solder")):
                    v = ch.get(key) or {}
                    if v.get("value") is not None:
                        m[f"{k}{nm}"] = fx(v["value"], 1)
    return m


# ------------------------------------------------------------------ comparison helpers
def compare():
    import tcpmt_cases as TC
    m = {}
    C = {(t, a): case(TC.case_path("SDEC", t, a)) for t in ("A", "B") for a in ("Z1", "Z2", "Z3")}
    S0 = {(t, a): case(TC.case_path("S0", t, a)) for t in ("A", "B") for a in ("Z1", "Z2", "Z3")}
    for t in ("A", "B"):
        z1, z2 = C[(t, "Z1")], C[(t, "Z2")]
        if not (z1 and z2):
            continue
        g1 = {r["term"]: r["P_w"] for r in z1["raw"]["ledger_rows"]}
        g2 = {r["term"]: r["P_w"] for r in z2["raw"]["ledger_rows"]}
        c1 = sum(v for k, v in g1.items() if k.startswith("P_conv"))
        c2 = sum(v for k, v in g2.items() if k.startswith("P_conv"))
        tl1 = z1["raw"]["et_history"][-1].get("T_ls_C")
        tl2 = z2["raw"]["et_history"][-1].get("T_ls_C")
        m[f"WrdPconv{t}Ztwo"] = fx(abs(c2 - c1), 1)
        m[f"WrdProute{t}Ztwo"] = fx(abs((z2["P"] - c2) - (z1["P"] - c1)), 1)
        m[f"WrdTls{t}Ztwo"] = fx(abs(tl2 - tl1), 1)
        m[f"WrWarpRatio{t}Ztwo"] = fx(z2["warp"] / z1["warp"], 1)
        m[f"WrDuRatio{t}Ztwo"] = fx(z2["du"] / z1["du"], 2)
        m[f"WrdTjoint{t}Ztwo"] = fx(abs(z1["Tj"] - z2["Tj"]), 0)
        m[f"WrdTmax{t}Ztwo"] = fx(abs(z2["T"] - z1["T"]), 1)
    # the routing terms Z2 and Z3 add (production state, cooling A; Fig. 9)
    for a in ("Z2", "Z3"):
        z = C[("A", a)]
        if z:
            g = {r["term"]: r["P_w"] for r in z["raw"]["ledger_rows"]}
            m[f"WrPtsvA{ATAG[a]}"] = fx(sum(v for k, v in g.items() if k.startswith("P_TSV")), 2)
            m[f"WrPattA{ATAG[a]}"] = fx(sum(v for k, v in g.items() if k.startswith(
                ("P_VR_attach", "P_VR_PCB_attach"))), 2)
            m[f"WrPbgaOneVA{ATAG[a]}"] = fx(sum(v for k, v in g.items()
                                                 if k.startswith("P_BGA_1V")), 2)
    # Z3: land side and board planes in the coupled ledger
    for t in ("A", "B"):
        z3 = C[(t, "Z3")]
        if z3:
            g = {r["term"]: r["P_w"] for r in z3["raw"]["ledger_rows"]}
            m[f"WrZthreeLand{t}"] = fx(g.get("P_sub_land_1V_spreading"), 1)
            m[f"WrZthreePlane{t}"] = fx(g.get("P_PCB_plane_1V_spreading"), 1)
            m[f"WrZthreeVias{t}"] = fx(g.get("P_PCB_via_VDD", 0) + g.get("P_PCB_via_GND", 0), 1)
            m[f"WrZthreeOneV{t}"] = fx(sum(v for k, v in g.items() if k.startswith(
                ("P_VR_PCB", "P_PCB", "P_BGA_1V", "P_sub_land"))), 1)
    # the production and the ideal-decoupling joints (the local response is solved for the
    # latter): largest change of the driver and of the joint temperature over the six cases
    dd, dt = [], []
    for k, c in C.items():
        s = S0.get(k)
        if c and s and c["du"] and s["du"]:
            dd.append(abs(c["du"] - s["du"]) / s["du"])
            dt.append(abs(c["Tj"] - s["Tj"]))
    if dd:
        m["WrDuShiftPct"] = fx(100 * max(dd), 0)
        m["WrTsjShiftK"] = fx(max(dt), 1)
    # board mean / underside of Z1 under A and B (mechanism of the bottom plate)
    return m


def uncertainty_rule():
    """verdicts of the unified rule for the production comparisons (uncertainty.json)"""
    d = J(TR / "uncertainty.json") or {}
    m = {}
    obs = {"P": "Ploss", "T": "Tmax", "warp": "Warp", "du": "Du", "eps": "Eps"}
    for c in d.get("comparisons") or []:
        if c["output"] not in obs:
            continue
        pair = "".join(sorted((ATAG[c["a"]], ATAG[c["b"]]), key=lambda s: ("Zone", "Ztwo", "Zthree").index(s)))
        k = f"WrRes{c['tier']}{pair}{obs[c['output']]}"
        m[k] = {"resolved": "resolved", "not resolved": "not resolved"}.get(c["verdict"], c["verdict"])
        m[k + "Ratio"] = fx(c.get("ratio"), 1)
        m[k + "Uni"] = fx(c.get("U95"), 2 if c["output"] in ("P", "du", "eps") else 1)
        m[k + "Lower"] = c.get("lower") or NA
        m[k + "Dc"] = fx(abs(c["D_corrected"]) if c.get("D_corrected") is not None else None,
                         2 if c["output"] in ("P", "du", "eps") else 1)
    return m


def _joint_outcomes():
    """{case: outcome} of the joint column of the map (the joint response at the worst sites of
    each variant's reference case, robustness_joint.json): the classical decisions on the
    ideal-decoupling reference and the newer production-state decisions under cooling A."""
    d = J(TR / "robustness_joint.json") or {}
    out = {}
    for g in ("S0_A", "SDEC_new_A"):
        for name, r in ((d.get("groups") or {}).get(g) or {}).items():
            o = (r.get("orderings") or {}).get("eps:Z1/Z2")
            if not o:
                continue
            v, b = o.get("verdict"), o.get("base_verdict")
            out[name] = ("pending" if v == "pending" else "preserved" if v == b else
                         "withdrawn" if v == "unresolved" else "reversed")
    return out


def robustness():
    """counts of the robustness verdicts (unified rule) over the four mapped observables:
    package loss, peak temperature and die warpage from the class-B rows, the joint response
    from the joint-response screen (the largest ball displacement is counted apart)"""
    rows = list(csv.DictReader(open(FC / "classB_sensitivity_rows.csv")))
    obs = ("P_loss_package_internal_w", "T_max_C", "die_warpage_pv_um")
    seen, du = {}, {}
    for r in rows:
        if " vs " in r["case"] or r["case"] == "per scenario":
            continue
        if r["outcome"] in ("n/a", "", "changed"):
            continue
        if r["observable"] in obs:
            seen[(r["case"], r["observable"])] = r["outcome"]
        elif r["observable"] == "du_c_um":
            du[r["case"]] = r["outcome"]
    jo = _joint_outcomes()
    for c, v in jo.items():
        seen[(c, "joint")] = v
    from collections import Counter
    n = Counter(v.split()[0] for v in seen.values())
    m = {"WrRobN": str(len(seen)), "WrRobPreserved": str(n.get("preserved", 0)),
         "WrRobPending": str(n.get("pending", 0)), "WrRobWithdrawn": str(n.get("withdrawn", 0)),
         "WrRobReversed": str(n.get("reversed", 0)),
         "WrRobCases": str(len({c for c, _ in seen}))}
    pend = sorted({c for (c, o), v in seen.items() if v == "pending"})
    m["WrRobPendingCases"] = str(len(pend))
    nj = Counter(jo.values())
    m["WrRobJointN"] = str(len(jo))
    for k in ("preserved", "withdrawn", "reversed", "pending"):
        m[f"WrRobJoint{k.capitalize()}"] = str(nj.get(k, 0))
    nd = Counter(v.split()[0] for v in du.values())
    m["WrRobDuN"] = str(len(du))
    m["WrRobDuReversed"] = str(nd.get("reversed", 0))
    return m


def platform():
    d = J(TR / "platform_inclusive.json") or {}
    t = d.get("tiers") or {}
    m = {}
    try:
        m["WrPlatGapA"] = fx(t["A"]["Z2"]["P_platform_W"] - t["A"]["Z1"]["P_platform_W"], 1)
        m["WrPlatGapB"] = fx(t["B"]["Z1"]["P_platform_W"] - t["B"]["Z2"]["P_platform_W"], 1)
        m["WrPumpLo"] = fx(min(t["A"]["Z1"]["P_pump_band_W"]), 1)
        m["WrPumpHi"] = fx(max(t["A"]["Z1"]["P_pump_band_W"]), 1)
    except (KeyError, TypeError):
        pass
    return m


# ------------------------------------------------------------------ omitted converter losses
def omitted():
    d = J(TR / "omitted_losses.json")
    if not d:
        return {}
    s = d["summary"]
    lo, nom, hi = s["omitted_total_w_production_A_Z1_low_nom_high"]
    m = {"WrOmitLo": fx(lo, 1), "WrOmitNom": fx(nom, 0), "WrOmitHi": fx(hi, 0)}
    a1 = d["cases"]["A_Z1"]["omitted"]["nominal"]
    m["WrOmitDead"] = fx(a1["dead_time_w"], 0)
    m["WrOmitDeadLo"] = fx(d["assumptions"]["dead_time"]["range_ns"][0], 0)
    m["WrOmitDeadHi"] = fx(d["assumptions"]["dead_time"]["range_ns"][1], 0)
    m["WrOmitDeadNom"] = fx(d["assumptions"]["dead_time"]["nominal_ns"], 0)
    m["WrOmitCore"] = fx(a1["core_w"], 1)
    m["WrOmitAc"] = fx(a1["ac_winding_w"], 1)
    m["WrOmitDiel"] = fx(a1["dielectric_w"], 1)
    pr = s["pairs"]
    plist = {(p["better"], p["worse"]): p for p in d.get("pairs") or []}
    for key, tag in (("A_Z2_vs_A_Z1", "A"), ("B_Z2_vs_B_Z1", "B")):
        p = pr.get(key)
        if p is None:                    # the pair's name follows the lower-loss integration
            alt = key.split("_vs_")
            p = pr.get(f"{alt[1]}_vs_{alt[0]}")
            key = f"{alt[1]}_vs_{alt[0]}"
        if p is None:
            continue
        nomt = p["delta_omitted_w_low_nom_high"][1] + p["delta_feedback_w_nom_high"][0]
        hit = p["delta_omitted_w_low_nom_high"][2] + p["delta_feedback_w_nom_high"][1]
        m[f"WrOmitGap{tag}"] = fx(abs(nomt), 1)
        m[f"WrOmitGap{tag}Hi"] = fx(abs(hit), 1)
        better, worse = (x.split("_")[1] for x in key.split("_vs_"))
        # a negative shift shrinks the better integration's advantage: it favors the worse one
        m[f"WrOmitFavor{tag}"] = worse if nomt < 0 else better
        gap = p.get("gap_paper_w")
        if gap is not None:
            m[f"WrOmitClose{tag}"] = (", enough to close it" if (nomt < 0 and abs(hit) >= gap)
                                      else "")
    dse = s["dse"]["T_25C"]
    m["WrOmitDseOptNom"] = str(dse["nominal"]["optimum_M"])
    m["WrOmitDseMarginNom"] = fx(dse["nominal"]["margin_w"], 1)
    m["WrOmitDseMarginLow"] = fx(dse["low"]["margin_w"], 1)
    m["WrOmitDseOptHi"] = str(dse["high"]["optimum_M"])
    m["WrOmitDseMarginHi"] = fx(dse["high"]["margin_w"], 1)
    fl = d.get("out_of_scope_flags") or {}
    import re
    mm = re.search(r"is ([\d.]+) W against ([\d.]+) W", fl.get("coss_term", ""))
    if mm:
        m["WrCossScreen"], m["WrCossDatasheet"] = fx(mm.group(1), 1), fx(mm.group(2), 1)
    # feasibility of Z1 (cooling A) under the nominal and the high bundle
    fe = J(TR / "feasibility.json") or {}
    om = (((fe.get("cases") or {}).get("A_Z1") or {}).get("omitted_losses") or {}).get("bundles") or {}
    for b, tag in (("nominal", "Nom"), ("high", "Hi")):
        ch = (om.get(b) or {}).get("checks") or {}
        for key, nm in (("ron_fit", "Ron"), ("mlcc", "Mlcc"), ("solder_law", "Solder"),
                        ("die", "Die")):
            if (ch.get(key) or {}).get("value") is not None:
                m[f"WrOmit{tag}{nm}AZone"] = fx(ch[key]["value"], 1)
    return m


# ------------------------------------------------------------------ sensitivities
def sensitivities():
    m = {}
    base = {a: case(FC / f"etm_{a}_HV_S0_h1.1_r21.json") for a in ("Z1", "Z2")}
    for var, tag in (("conv_posts_lower", "PostLo"), ("conv_posts_upper", "PostHi"),
                     ("gan_k_half", "GanHalf"), ("conv_k_tenth", "KTenth"),
                     ("encap_emc_lowcte", "Emc"), ("encap_uf_tg", "Uf"),
                     ("board_t2p4", "Board"), ("bga_card_local", "BgaCard")):
        for a in ("Z1", "Z2"):
            v, b = case(SENS / f"etm_{a}_HV_S0__{var}.json"), base[a]
            if not (v and b):
                continue
            k = f"Wr{tag}{ATAG[a]}"
            m[f"{k}dP"] = fsgn(v["P"] - b["P"], 1)
            m[f"{k}dT"] = fsgn(v["T"] - b["T"], 1)
            m[f"{k}Warp"] = fx(v["warp"], 1)
            m[f"{k}Du"] = fx(v["du"], 2)
            m[f"{k}Tj"] = fx(v["Tj"], 1)
            m[f"{k}Tmax"] = fx(v["T"], 1)
    # caloric (legacy plate coefficient) against the production state
    for t in ("A", "B"):
        for a in ("Z1", "Z2", "Z3"):
            v = case(SENS / f"etm_{a}_HV_SDEC__plate_caloric_legacy_{t}.json")
            b = case(SENS / f"etm_{a}_HV_SDEC__sdec_{t}.json")
            if v and b:
                m[f"WrCal{t}{ATAG[a]}dP"] = fx(v["P"] - b["P"], 1)
                m[f"WrCal{t}{ATAG[a]}dT"] = fx(v["T"] - b["T"], 1)
    return m



# ------------------------------------------------------------------ sign-safe wording
def verdicts():
    """Comparative words derived from the data, so a rerun that flips a sign rewrites the
    sentence instead of leaving a stale claim: the lower-loss integration of Z1/Z2 inside the
    package and at the platform boundary, per cooling and for the ideal-decoupling reference."""
    import tcpmt_cases as TC
    m = {}
    pl = (J(TR / "platform_inclusive.json") or {}).get("tiers") or {}
    low = {}
    for t in ("A", "B"):
        c1, c2 = (J(TC.case_path("SDEC", t, a)) for a in ("Z1", "Z2"))
        if not (c1 and c2):
            continue
        li = "Z1" if c1["P_loss_w"] < c2["P_loss_w"] else "Z2"
        low[t] = li
        m[f"WrLow{t}"] = li
        m[f"WrHigh{t}"] = "Z2" if li == "Z1" else "Z1"
        try:
            lp = "Z1" if pl[t]["Z1"]["P_platform_W"] < pl[t]["Z2"]["P_platform_W"] else "Z2"
        except (KeyError, TypeError):
            continue
        m[f"WrLowPlat{t}"] = lp
        if lp != li:
            m[f"WrElecVerdict{t}"] = (r"Electrically, neither integration leads under this cooling: "
                                     r"the boundary of the comparison decides.")
            m[f"WrElecShort{t}"] = "neither leads electrically"
        else:
            m[f"WrElecVerdict{t}"] = (f"Electrically, {li} leads under this cooling at both "
                                     f"boundaries.")
            m[f"WrElecShort{t}"] = f"{li} leads electrically at both boundaries"
        # the feed limit of Z2 as a sentence (R* = 0: behind even with a lossless feed)
        tf = ((J(TR / "tier_feed_crossover.json") or {}).get("states") or {}).get("SDEC", {})
        r = ((tf.get(t) or {}).get("Z2") or {}).get("R_star_mohm")
        if r is None:
            pass
        elif r > 0:
            m[f"WrRstarSent{t}"] = (r"Z2 keeps the lower loss only while that feed loop stays "
                                   f"below $R^* = {r:.1f}$~m$\\Omega$.")
        else:
            m[f"WrRstarSent{t}"] = "Z2 has the higher loss even with a lossless feed."
    r0 = (J(FC / "etm_Z1_HV_S0_h1.1_r21.json") or {}).get("P_loss_w")
    r2 = (J(FC / "etm_Z2_HV_S0_h1.1_r21.json") or {}).get("P_loss_w")
    if r0 and r2:
        lr = "Z1" if r0 < r2 else "Z2"
        m["WrLowRefA"] = lr
        if "A" in low:
            m["WrDecapRankSent"] = (
                "The loss ranking between Z1 and Z2 thus depends on the input decoupling itself."
                if lr != low["A"] else
                "The loss ranking between Z1 and Z2 is the same in both states.")
    return m


# ------------------------------------------------------------------ joint response, state-aware
def joint_response():
    """\\WrEps<t><A> (10^-3 per cycle), \\WrEpsU<t><A> (absolute) and the state they were solved
    in: the production state when the local study ran on the production cases, else the
    ideal-decoupling reference -- the text and Table V switch with the data."""
    d = J(TR / "solder_studies.json") or {}
    st = (d.get("stabilization") or {}).get("cases") or {}
    zl = (J(TR / "solder_z3land.json") or {}).get("cases") or {}
    m, files = {}, []
    for lab, v in st.items():
        t, a = lab.split("_")
        val, u = v.get("stabilised"), v.get("U_stab_num")
        if a == "Z3" and (zl.get(t) or {}).get("stabilised") is not None:
            val, u = zl[t]["stabilised"], zl[t].get("U_stab_num")
        if val is None:
            continue
        files.append(v.get("case_file") or "")
        m[f"WrEps{t}{ATAG[a]}"] = fx(1e3 * val, 2)
        if u is not None:
            m[f"WrEpsU{t}{ATAG[a]}"] = fx(1e3 * val * u, 2)
            m[f"WrEpsUrel{t}{ATAG[a]}"] = fx(100 * u, 1)
    for t in ("A", "B"):
        vals = {a: float(m[f"WrEps{t}{ATAG[a]}"]) for a in ("Z1", "Z2", "Z3")
                if m.get(f"WrEps{t}{ATAG[a]}", NA) != NA}
        if vals:
            m[f"WrEpsLow{t}"] = min(vals, key=vals.get)
    la, lb = m.get("WrEpsLowA"), m.get("WrEpsLowB")
    if la and lb:
        m["WrEpsLowSent"] = (f"The smallest increment belongs to {la} under both coolings."
                             if la == lb else
                             f"The smallest increment belongs to {la} under cooling~A and to "
                             f"{lb} under cooling~B.")
    prod = bool(files) and all("HV_SDEC" in f for f in files)
    m["WrEpsState"] = "in the production state" if prod else "for the ideal-decoupling reference"
    m["WrEpsStateShort"] = "production state" if prod else "ideal-decoupling reference"
    if prod:
        m["WrEpsStateNote"] = ""
    else:
        cm = compare()
        m["WrEpsStateNote"] = (
            f"Across the six compared cases its drivers differ from the production state's by at "
            f"most {cm.get('WrDuShiftPct', NA)}\\,\\% in $\\du$ and {cm.get('WrTsjShiftK', NA)}~K "
            f"in $T_{{\\mathrm{{sj}}}}$.")
    co = d.get("constitutive") or {}
    m["WrLawHold"] = "every" if co.get("rankings_hold_all_variants") else "not every"
    return m

def main():
    mac = {}
    for f in (designs, common_temperature, evaluate_z1, interconnects, decoupling, bga,
              feasibility_variants, design_feasibility, compare, uncertainty_rule, robustness,
              platform, omitted, sensitivities, verdicts, joint_response):
        try:
            mac.update(f())
        except Exception as e:                               # noqa: BLE001 -- keep building
            import traceback
            traceback.print_exc()
            print(f"WARNING {f.__name__}: {e}")
    lines = ["% GENERATED by scripts/tcpmt_writer_macros_results.py (numbers not in results_macros.tex)",
             f"% source: {ROOT}"]
    lines += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in mac.items()]
    OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT} ({len(mac)} macros)")


if __name__ == "__main__":
    main()
