"""Macros of the front matter of the TCPMT paper (abstract, introduction, framework, converter
synthesis and design-space exploration, Tables I-II, Figs. 1-4) that results_macros.tex does
not provide. Every macro name starts with "Fr" so none collides with another writer's file.

Sources (all read, none written):
  <root>/tcpmt_revision/dse_phase2_summary.json   regulator-count screen (27 counts, tier limits
                                                   4 / 5 / none), every count's pick
  <root>/tcpmt_revision/design_comparison.json    the production design, the 5-tier co-design
                                                   candidate, the thin-capacitor variant and the
                                                   count neighbours through the full chain
  <root>/tcpmt_revision/input_decoupling.json     the implemented input decoupling (ring parts,
                                                   clock plan, k_rms)
  <root>/final_closure/sensitivity/etm_*_HV_SDEC__{sdec,die_hotspot}_{A,B}.json
                                                   production cases and the die power map
  configs/design_points.yaml                      THE design record (tiers, heights)
  scripts/tcpmt_production_converter.record()     the production converter, compiled exactly as
                                                   the package chain compiles it (in memory)
  configs/phase0nt/z2_2p4mm_cutout.yaml           the Z2 board-opening fit of each design
                                                   (physical_package.cutout_fit_margin_um)
<root> = $ETM_RESULTS_ROOT, default research/campaign_v3.

    python scripts/tcpmt_writer_macros_front.py   -> manuscript_v2/macros_front.tex
A missing source yields "--", never a stale number.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
R = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research" / "campaign_v3")
os.environ["ETM_RESULTS_ROOT"] = str(ROOT)          # every imported module reads the same root
TR = ROOT / "tcpmt_revision"
SENS = ROOT / "final_closure" / "sensitivity"
OUT = R / "manuscript_v2" / "macros_front.tex"
NA = "--"
ARCH = {"Z1": "Zone", "Z2": "Ztwo", "Z3": "Zthree"}
WORD = {16: "Sixteen", 25: "Twentyfive", 36: "Thirtysix", 49: "Fortynine", 64: "Sixtyfour",
        81: "Eightyone"}


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
        v = float(v)
    except (TypeError, ValueError):
        return NA
    if not math.isfinite(v):
        return NA
    s = f"{v:.{n}f}"
    return "0" + s[2:] if s.startswith("-0") and float(s) == 0 else s


def topo(label):
    """'N=3,K=3,K_A=2' -> 'N3K3' (the paper's NxKy notation)."""
    try:
        n, k, _ka = (int(x.split("=")[1]) for x in label.split(","))
    except (AttributeError, ValueError, IndexError):
        return NA
    return f"N{n}K{k}"


def tier_text(plan):
    """[{'gan_hs': 2, 'cap_fly': 2, 'height_um': ...}, ...] -> '2HS+2C_f | HS+LS | ...'."""
    short = {"gan_hs": "HS", "gan_ls": "LS", "inductor": "L", "cap_fly": "C$_\\mathrm{f}$"}
    order = ("gan_hs", "gan_ls", "inductor", "cap_fly")
    out = []
    for t in plan:
        parts = [f"{t[c] if t[c] > 1 else ''}{short[c]}" for c in order if t.get(c)]
        out.append("+".join(parts))
    return " $|$ ".join(out)


# ------------------------------------------------------------------ count screen
def dse():
    d = J(TR / "dse_phase2_summary.json")
    if not d:
        return {}
    m = {}
    runs = d["runs"]
    r4 = runs.get("etm35_p2_t4") or {}
    pc = {int(k): v for k, v in (r4.get("per_count") or {}).items()}
    counts = sorted(pc)
    feas = sorted(k for k, v in pc.items() if v)
    m["FrDseNcounts"] = str(len(counts))
    m["FrDseMlo"], m["FrDseMhi"] = str(counts[0]), str(counts[-1])
    m["FrDseCountList"] = ", ".join(str(c) for c in counts)
    m["FrDseTierLimit"] = str(r4.get("max_tiers"))
    m["FrDseNfeas"] = str(len(feas))
    m["FrDseFeasHi"] = str(feas[-1])
    m["FrDseInfeasLo"] = str(min(k for k in counts if k > feas[-1]))
    m["FrDseNmembers"] = str(len({pc[k]["arch"] for k in feas}))
    fsw = [pc[k]["f_sw_kHz"] for k in feas]
    m["FrDseFswLo"], m["FrDseFswHi"] = fx(min(fsw), 0), fx(max(fsw), 0)
    o = r4["optimum"]
    m["FrDseOptM"] = str(o["M"])
    m["FrDseOptGrid"] = str(int(round(math.sqrt(o["M"])))) if o.get("square") else NA
    m["FrDseOptTopo"] = topo(o["arch"])
    m["FrDseOptFsw"] = fx(o["f_sw_kHz"], 0)
    m["FrDseOptLoss"] = fx(o["P_total_W"], 1)
    m["FrDseOptConv"] = fx(o["conv_total_W"], 1)
    m["FrDseOptRoute"] = fx(o["routing_W"], 1)
    m["FrDseOptTiers"] = str(o["tiers"])
    m["FrDseOptStack"] = fx(o["stack_height_um"] / 1e3, 2)
    m["FrDseOptIsSquare"] = "yes" if o.get("square") else "no"
    m["FrDseBestSquare"] = str(r4.get("best_square_grid"))
    sq = r4.get("square_grid_P_total_W") or {}
    for k, v in sq.items():
        m[f"FrDseSq{WORD.get(int(k), k)}"] = fx(v, 1) if v is not None else "infeasible"
    inf_sq = [int(k) for k, v in sq.items() if v is None]
    m["FrDseSqInfeasList"] = " and ".join(str(k) for k in sorted(inf_sq)) if inf_sq else "none"
    for mm in (25, 49):
        v = pc.get(mm)
        w = WORD[mm]
        if v:
            m[f"FrDse{w}Topo"] = topo(v["arch"])
            m[f"FrDse{w}Fsw"] = fx(v["f_sw_kHz"], 0)
            m[f"FrDse{w}Loss"] = fx(v["P_total_W"], 1)
            m[f"FrDse{w}Margin"] = fx(v["P_total_W"] - o["P_total_W"], 1)
            m[f"FrDse{w}Stack"] = fx(v["stack_height_um"] / 1e3, 2)
    # the tier limit as a design variable: at most 5 tiers, and none
    r5 = runs.get("etm35_p2_t5") or {}
    if r5:
        o5 = r5["optimum"]
        m["FrDseTfiveOptM"] = str(o5["M"])
        m["FrDseTfiveOptSquare"] = "yes" if o5.get("square") else "no"
        m["FrDseTfiveOptLoss"] = fx(o5["P_total_W"], 1)
        m["FrDseTfiveOptStack"] = fx(o5["stack_height_um"] / 1e3, 2)
        bs = int(r5.get("best_square_grid"))
        p5 = {int(k): v for k, v in r5["per_count"].items()}[bs]
        m["FrDseTfiveSqM"] = str(bs)
        m["FrDseTfiveSqTopo"] = topo(p5["arch"])
        m["FrDseTfiveSqHs"], m["FrDseTfiveSqLs"] = p5["hs"], p5["ls"]
        m["FrDseTfiveSqFsw"] = fx(p5["f_sw_kHz"], 0)
        m["FrDseTfiveSqLoss"] = fx(p5["P_total_W"], 1)
        m["FrDseTfiveSqConv"] = fx(p5["conv_total_W"], 1)
        m["FrDseTfiveSqTiers"] = str(p5["tiers"])
        m["FrDseTfiveSqStack"] = fx(p5["stack_height_um"] / 1e3, 2)
        if bs == o["M"]:
            m["FrDseTfiveSqGain"] = fx(o["P_total_W"] - p5["P_total_W"], 1)
        m["FrDseTfiveFeasHi"] = str(max(r5["feasible_counts"]))
    ri = runs.get("etm35_p2_tinf") or {}
    if ri:
        oi = ri["optimum"]
        m["FrDseTinfOptM"] = str(oi["M"])
        m["FrDseTinfOptTopo"] = topo(oi["arch"])
        m["FrDseTinfOptLoss"] = fx(oi["P_total_W"], 1)
        m["FrDseTinfOptTiers"] = str(oi["tiers"])
        m["FrDseTinfOptStack"] = fx(oi["stack_height_um"] / 1e3, 2)
        m["FrDseTinfFeasHi"] = str(max(ri["feasible_counts"]))
        pi = {int(k): v for k, v in ri["per_count"].items() if v}
        m["FrDseTinfTiersMax"] = str(max(v["tiers"] for v in pi.values()))
        m["FrDseTinfStackMax"] = fx(max(v["stack_height_um"] for v in pi.values()) / 1e3, 1)
        bsi = int(ri.get("best_square_grid"))
        m["FrDseTinfSqM"] = str(bsi)
        m["FrDseTinfSqLoss"] = fx(pi[bsi]["P_total_W"], 1)
        m["FrDseTinfSqTiers"] = str(pi[bsi]["tiers"])
        m["FrDseTinfSqStack"] = fx(pi[bsi]["stack_height_um"] / 1e3, 2)
    return m


def fsw_fine():
    """The four-tier screen on the nested 16x finer f_sw grid under the full rules
    (scripts/tcpmt_dse_fsw_grid.py -> dse_fsw_fine.json)."""
    d = J(TR / "dse_fsw_fine.json")
    if not d:
        return {}
    m = {}
    pc = {int(k): v for k, v in d["counts"].items()}
    m["FrFswFineN"] = str(d["n_grid_points"])
    m["FrFswCoarseN"] = str(d["n_grid_points_screen"])
    m["FrFswFineFactor"] = str(round((d["n_grid_points"] - 1)
                                     / (d["n_grid_points_screen"] - 1)))
    o = d["optimum_fine"]
    f, c = pc[o]["fine"], pc[o]["grid50"]
    m["FrFswFineOptM"] = str(o)
    m["FrFswFineOptSame"] = "yes" if d["optimum_unchanged"] else "no"
    m["FrFswFineSelSame"] = "yes" if d["optimum_selection_unchanged"] else "no"
    m["FrFswFineOptFsw"] = fx(f["f_sw_kHz"], 0)
    m["FrFswFineOptLoss"] = fx(f["total_loss_W"], 1)
    m["FrFswFineOptGain"] = fx(c["total_loss_W"] - f["total_loss_W"], 2)
    m["FrFswFineNselChanged"] = str(d["n_counts_selection_changed"])
    m["FrFswFineNfswChanged"] = str(d["n_counts_f_sw_changed"])
    m["FrFswFineNfeasChanged"] = str(d["n_counts_feasibility_changed"])
    m["FrFswFineNfeas"] = str(sum(1 for v in pc.values() if v["fine"]))
    lo, hi = d["loss_change_range_W"]
    m["FrFswFineGainMax"] = fx(-lo, 1)
    m["FrFswFineRunnerUp"] = str(d["runner_up_fine"])
    m["FrFswFineRunnerUpMargin"] = fx(d["margin_to_runner_up_W"], 1)
    # the same on the coarse (screen) grid
    c50 = sorted((v["grid50"]["total_loss_W"], k) for k, v in pc.items() if v["grid50"])
    if len(c50) > 1:
        m["FrFswCoarseRunnerUp"] = str(c50[1][1])
        m["FrFswCoarseRunnerUpMargin"] = fx(c50[1][0] - c50[0][0], 1)
    sq_ = int(round(d["runner_up_fine"] ** 0.5)) ** 2 == d["runner_up_fine"]
    m["FrFswFineRunnerUpSquare"] = "yes" if sq_ else "no"
    for mm in (25, 49):
        v = pc.get(mm) or {}
        if v.get("fine") and f:
            m[f"FrFswFine{WORD[mm]}Margin"] = fx(v["fine"]["total_loss_W"] - f["total_loss_W"], 1)
    sq = d.get("square_ranking_fine") or []
    m["FrFswFineSqSecond"] = str(sq[1]) if len(sq) > 1 else NA
    return m


# ------------------------------------------------------------------ designs through the chain
def chain():
    d = J(TR / "design_comparison.json")
    if not d:
        return {}
    m = {}
    D = d["designs"]

    def P(des, case):
        c = ((D.get(des) or {}).get("cases") or {}).get(case)
        return c["P_loss_W"] if c and c.get("et_converged") else None

    for t in ("A", "B"):
        p36 = P("m36", f"Z1_{t}")
        m[f"FrChainThirtysix{t}"] = fx(p36, 1)
        for des, w in (("m25", "Twentyfive"), ("m49", "Fortynine")):
            p = P(des, f"Z1_{t}")
            m[f"FrChain{w}{t}"] = fx(p, 1)
            m[f"FrChainMargin{w}{t}"] = fx(p - p36, 1) if p is not None and p36 else NA
    margins = [P(x, f"Z1_{t}") - P("m36", f"Z1_{t}") for x in ("m25", "m49") for t in "AB"
               if P(x, f"Z1_{t}") is not None and P("m36", f"Z1_{t}") is not None]
    if margins:
        m["FrChainMarginLo"], m["FrChainMarginHi"] = fx(min(margins), 1), fx(max(margins), 1)
    rk = d.get("ranking") or {}
    same = [v.get("same_ranking") and v.get("complete") for v in rk.values()]
    m["FrChainSameRank"] = "yes" if same and all(same) else "no"
    for des in ("m36", "m36t5", "m25", "m49", "m36thin"):
        x = D.get(des) or {}
        w = {"m36": "Thirtysix", "m36t5": "Tfive", "m25": "Twentyfive", "m49": "Fortynine",
             "m36thin": "Thin"}[des]
        if x.get("converter_stack_um"):
            m[f"FrStack{w}"] = fx(x["converter_stack_um"] / 1e3, 2)
    # the 5-tier co-design candidate and the thin-capacitor variant against the production design
    sav, thin = [], []
    for a in ("Z1", "Z2", "Z3"):
        for t in ("A", "B"):
            p36, p5, pth = P("m36", f"{a}_{t}"), P("m36t5", f"{a}_{t}"), P("m36thin", f"{a}_{t}")
            m[f"FrTfive{ARCH[a]}{t}"] = fx(p5, 1)
            if p36 is not None and p5 is not None:
                m[f"FrTfiveSave{ARCH[a]}{t}"] = fx(p36 - p5, 1)
                if a in ("Z1", "Z2"):
                    sav.append(p36 - p5)
            if p36 is not None and pth is not None:
                thin.append(pth - p36)
    if sav:
        m["FrTfiveSaveLo"], m["FrTfiveSaveHi"] = fx(min(sav), 1), fx(max(sav), 1)
    if thin:
        m["FrThinDeltaMax"] = fx(max(abs(x) for x in thin), 1)
    return m


def cutout_fit():
    """Z2: board + BGA depth minus attach + converter (um) for each design, from the Z2 config
    as the chain loads it (HVR_DESIGN selects the design record entry)."""
    code = ("import sys; sys.path.insert(0, 'scripts/phase0nw'); sys.path.insert(0, 'scripts');"
            "import physical_package as PP;"
            "p = PP.load_physical_package_config('configs/phase0nt/z2_2p4mm_cutout.yaml');"
            "print(p.cutout_fit_margin_um, p.board_thickness_um, p.conv_total_um)")
    m = {}
    for des, w in (("m36", "Thirtysix"), ("m36t5", "Tfive"), ("m36thin", "Thin")):
        env = dict(os.environ, HVR_DESIGN=des, PYTHONDONTWRITEBYTECODE="1")
        try:
            r = subprocess.run([sys.executable, "-c", code], cwd=R, env=env, text=True,
                               capture_output=True, timeout=600)
            fit, board, _conv = (float(x) for x in r.stdout.split()[-3:])
        except Exception:                                          # noqa: BLE001
            continue
        m[f"FrFit{w}"] = fx(fit, 0)
        if fit < 0:
            m[f"FrProtrude{w}"] = fx(-fit, 0)
        m["FrBoardMm"] = fx(board / 1e3, 1)
    return m


# ------------------------------------------------------------------ production converter
def converter():
    sys.path.insert(0, str(R / "scripts"))
    try:
        import tcpmt_production_converter as T
        p = T.record()
    except Exception as e:                                         # noqa: BLE001
        print("production converter unavailable:", e, file=sys.stderr)
        return {}
    dp, dev, ind, cf, cell = (p["design_point"], p["devices"], p["inductor"],
                              p["flying_capacitors"], p["cell"])
    lo, ru = p["loss_25C_per_cell_W"], p["rules"]
    n, k, ka = dp["topology"]
    hs, ls = dev["high_side"], dev["low_side"]
    m = {"FrConvM": str(dp["n_vr"]), "FrConvGrid": str(int(round(math.sqrt(dp["n_vr"])))),
         "FrConvTopo": f"N{n}K{k}", "FrConvN": str(n), "FrConvK": str(k), "FrConvKA": str(ka),
         "FrConvB": ", ".join(str(b) for b in dp["B_array"]),
         "FrConvDuty": f"{dp['D']:.4f}", "FrConvFsw": fx(dp["f_sw_hz"] / 1e3, 0),
         "FrConvIcell": fx(dp["i_out_per_cell_A"], 1), "FrConvJt": fx(dp["j_target_A_mm2"], 1),
         "FrConvHsPart": hs["part"], "FrConvHsVmax": fx(hs["V_DS_max_V"], 0),
         "FrConvHsVsone": fx(hs["V_stress_S1_V"], 0), "FrConvHsVstack": fx(hs["V_stress_V"], 0),
         "FrConvHsRon": fx(hs["R_DS_on_25C_ohm"] * 1e3, 0), "FrConvHsId": fx(hs["I_D_A"], 0),
         "FrConvLsPart": ls["part"], "FrConvLsVmax": fx(ls["V_DS_max_V"], 0),
         "FrConvLsVs": fx(ls["V_stress_V"], 0),
         "FrConvLsRon": fx(ls["R_DS_on_25C_ohm"] * 1e3, 1), "FrConvLsId": fx(ls["I_D_A"], 0),
         "FrConvSwDerate": fx(ru.get("SW_V_DERATING"), 1),
         "FrConvSwVallow": fx(ru.get("SW_V_DERATING", float("nan")) * hs["V_DS_max_V"], 0),
         "FrConvCapDerate": fx(ru.get("CAP_V_DERATING"), 1),
         "FrConvCapVallow": fx(ru.get("CAP_V_DERATING", float("nan")) * cf["V_max_V"], 0),
         "FrConvTierMax": str(ru.get("MAX_TIERS")),
         "FrConvIndL": fx(ind["L_nH"], 0), "FrConvIndDcr": fx(ind["DCR_mohm"], 1),
         "FrConvIndIsat": fx(ind["I_sat_A"], 0), "FrConvIndIavg": fx(ind["I_branch_avg_A"], 1),
         "FrConvIndIpk": fx(ind["I_branch_peak_A"], 1),
         "FrConvIndRipple": fx(ind["delta_I_branch_A"], 1),
         "FrConvIndArea": fx(ind["footprint_mm2"], 0), "FrConvIndH": fx(ind["height_um"], 0),
         "FrConvOutRipple": fx(ind["delta_I_out_A"], 1),
         "FrConvOutRippleLim": fx(0.5 * dp["i_out_per_cell_A"], 1),
         "FrConvCout": fx(p["output_capacitance_uF_per_cell"], 0),
         "FrConvCapPart": cf["vendor_part"] or cf["part"], "FrConvCapVmax": fx(cf["V_max_V"], 0),
         "FrConvCapCnom": fx(cf["C_nominal_uF"], 0),
         "FrConvCapVone": fx(cf["stress_V"]["C1"], 0), "FrConvCapVtwo": fx(cf["stress_V"]["C2"], 0),
         "FrConvCapEsr": fx(cf["ESR_at_fsw_mohm"], 1),
         "FrConvCapRipple": fx(100 * cf["ripple_worst_at_design_T"], 1),
         "FrConvCapH": fx(cf["height_um"] / 1e3, 1), "FrConvCapArea": fx(cf["footprint_mm2"], 2),
         "FrConvCellArea": fx(cell["area_budget_mm2"], 2),
         "FrConvCellSide": fx(math.sqrt(cell["area_budget_mm2"]), 2),
         "FrConvTierArea": fx(cell["area_mm2"], 2),
         "FrConvLossCell": fx(lo["total"], 2), "FrConvCondCell": fx(lo["conduction"], 2),
         "FrConvSwCell": fx(lo["switching"], 2), "FrConvLossSys": fx(p["loss_25C_system_W"], 1)}
    sp = lo.get("split") or {}
    for key, name in (("P_switch_hs_conduction", "HsCond"), ("P_switch_ls_conduction", "LsCond"),
                      ("P_inductor_DCR", "Dcr"), ("P_cap_ESR", "Esr"),
                      ("P_switching_hard", "Hard"), ("P_gate", "Gate"), ("P_Coss", "Coss")):
        if key in sp:
            m[f"FrConv{name}Cell"] = fx(sp[key], 2)
    if "P_switch_ls_conduction" in sp:
        m["FrConvLsCondShare"] = fx(100 * sp["P_switch_ls_conduction"] / lo["total"], 0)
    cb, ce = cf.get("C_bias_25C_uF") or {}, (cf.get("C_eff_uF") or {})
    for i, w in ((1, "One"), (2, "Two")):
        if cb.get(f"C{i}") is not None:
            m[f"FrConvCapCbias{w}"] = fx(cb[f"C{i}"], 2)
        for tk, tw in (("25C", ""), ("105C", "Hot")):
            v = (ce.get(tk) or {}).get(f"C{i}")
            if v is not None:
                m[f"FrConvCapCeff{tw}{w}"] = fx(v, 2)
    # output ripple voltage at the per-cell output capacitance (the synthesis' gate)
    m["FrConvVripple"] = fx(1e3 * ind["delta_I_out_A"]
                            / (8 * dp["f_sw_hz"] * p["output_capacitance_uF_per_cell"] * 1e-6), 0)
    return m


def record_tiers():
    """Tier plan and heights of the production design (the design record)."""
    sys.path.insert(0, str(R / "scripts" / "phase0nw"))
    try:
        import design_record as DR
        rec = DR.get()
    except Exception as e:                                         # noqa: BLE001
        print("design record unavailable:", e, file=sys.stderr)
        return {}
    tiers = rec["tiers"]
    words = ("One", "Two", "Three", "Four", "Five", "Six")
    m = {"FrTierPlan": tier_text([dict(t["parts"]) for t in tiers]),
         "FrTierN": str(len(tiers)),
         "FrStackUm": fx(rec["converter_stack_um"], 0)}
    for i, t in enumerate(tiers):
        m[f"FrTier{words[i]}H"] = fx(t["height_um"], 0)
    ph = rec.get("part_heights_um") or {}
    for c, w in (("gan_hs", "Hs"), ("gan_ls", "Ls"), ("inductor", "Ind"), ("cap_fly", "Cap")):
        if c in ph:
            m[f"FrH{w}"] = fx(ph[c], 0)
    m["FrKeepout"] = fx(rec.get("keepout_um"), 0)
    to = rec.get("tier_order") or {}
    if to.get("routing_loss_W") is not None:
        m["FrTierRouting"] = fx(to["routing_loss_W"], 2)
    if to.get("worst_via_ar_both_faces") is not None:
        m["FrTierViaAr"] = fx(to["worst_via_ar_both_faces"], 1)
    if to.get("n_orders"):
        m["FrTierNorders"] = str(to["n_orders"])
    return m


# ------------------------------------------------------------------ input decoupling
def decoupling():
    d = J(TR / "input_decoupling.json")
    if not d:
        return {}
    s = d.get("summary") or {}
    r = s.get("recommended") or {}
    m = {}
    if r:
        m["FrDecapN"] = str(r.get("count"))
        m["FrDecapPart"] = str(r.get("part", "")).split()[-1]
        m["FrDecapCtot"] = fx(r.get("C_total_48V_105C_uF"), 0)
        m["FrDecapPhases"] = str(r.get("n_clock_phases"))
        pat = str(r.get("phase_pattern") or "")
        if pat.startswith("dual"):
            m["FrDecapGroup"] = pat[4:]
        m["FrKrms"] = fx(r.get("k_eq"), 2)
        band = r.get("k_eq_band") or [None, None]
        m["FrKrmsLo"], m["FrKrmsHi"] = fx(band[0], 2), fx(band[1], 2)
    m["FrKopen"] = fx(s.get("k_open_cell_waveform"), 2)
    return m


# ------------------------------------------------------------------ die temperature, mechanics
def die_and_mech():
    sys.path.insert(0, str(R / "scripts"))
    m = {}
    try:
        import tcpmt_cases as TC
    except Exception:                                              # noqa: BLE001
        TC = None
    uni, hot = {}, {}
    mech, wall_h = {}, []
    for a in ("Z1", "Z2", "Z3"):
        for t in ("A", "B"):
            pc = TC.case_path("SDEC", t, a) if TC else SENS / f"etm_{a}_HV_SDEC__sdec_{t}.json"
            c = J(pc) if pc else None
            if c:
                uni[(a, t)] = c.get("die_T_max_C")
                mm = c.get("mechanics") or {}
                if t == "A":        # one coupled evaluation: E-T fixed point + mechanics
                    wall_h.append(((c.get("et_wall_s") or 0) + (mm.get("wall_s") or 0)) / 3600.0)
                cr = (mm.get("joint_search") or {}).get("critical") or {}
                mech[(a, t)] = (mm.get("die_warpage_pv_um"), cr.get("du_um"))
            h = J(SENS / f"etm_{a}_HV_SDEC__die_hotspot_{t}.json")
            if h and h.get("et_converged", True):
                hot[(a, t)] = h.get("die_T_max_C")
                m[f"FrDieHot{ARCH[a]}{t}"] = fx(h.get("die_T_max_C"), 1)
    if uni:
        m["FrDieUniMax"] = fx(max(v for v in uni.values() if v is not None), 1)
    if wall_h:
        m["FrEvalHLo"], m["FrEvalHHi"] = fx(min(wall_h), 1), fx(max(wall_h), 1)
    if hot:
        m["FrDieHotMax"] = fx(max(hot.values()), 1)
        over = [f"{a}-{t}" for (a, t), v in sorted(hot.items()) if v > 105.0]
        m["FrDieHotNover"] = str(len(over))
    for t in ("A", "B"):
        z1, z2 = mech.get(("Z1", t)), mech.get(("Z2", t))
        if z1 and z2 and all(z1) and all(z2):
            m[f"FrWarpRatio{t}"] = fx(z2[0] / z1[0], 1)
            m[f"FrDuRatio{t}"] = fx(z2[1] / z1[1], 1)
    return m


def main():
    m = {}
    for f in (dse, fsw_fine, chain, cutout_fit, converter, record_tiers, decoupling,
              die_and_mech):
        try:
            m.update(f())
        except Exception as e:                                     # noqa: BLE001
            print(f"{f.__name__}: {e}", file=sys.stderr)
    lines = ["% GENERATED by scripts/tcpmt_writer_macros_front.py -- do not edit "
             "(numbers not in results_macros.tex)",
             f"% source root: {ROOT.relative_to(R) if ROOT.is_relative_to(R) else ROOT}"]
    for k in sorted(m):
        lines.append(f"\\newcommand{{\\{k}}}{{{m[k]}}}")
    OUT.write_text("\n".join(lines) + "\n")
    print(f"{len(m)} macros -> {OUT}")


if __name__ == "__main__":
    main()
