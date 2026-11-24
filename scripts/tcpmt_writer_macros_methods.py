"""Macros of the methods writer (Sections IV and V of the TCPMT manuscript) that are not in
results_macros.tex.

Every value is read from the campaign result root (ETM_RESULTS_ROOT, default
research/campaign_v3) or from the design record (configs/design_points.yaml); a missing artifact
prints "--", never a stale number. Macro names start with "Mth" (no collision with
results_macros.tex or the other writers' files).

    ETM_RESULTS_ROOT=research/campaign_v3 python scripts/tcpmt_writer_macros_methods.py
        -> manuscript_v2/macros_methods.tex
"""
from __future__ import annotations

import ast
import json
import math
import os
import statistics
from pathlib import Path

R = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research" / "campaign_v3")
if not ROOT.is_absolute():
    ROOT = R / ROOT
FC, TR = ROOT / "final_closure", ROOT / "tcpmt_revision"
SENS = FC / "sensitivity"
OUT = R / "manuscript_v2" / "macros_methods.tex"
NA = "--"
ATAG = {"Z1": "Zone", "Z2": "Ztwo", "Z3": "Zthree"}
#: IEEE style spells out integers below ten in running text: each count the prose prints as a
#: word gets a "<name>Word" twin from the same value (digits from ten on)
WORD_FORM = ("MthNtie", "MthPlaneN", "MthNasym", "MthNosc")
_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine")


def word(v):
    """'4' -> 'four' for 0-9; any other value unchanged."""
    s = str(v).strip()
    return _WORDS[int(s)] if s.isdigit() and int(s) < 10 else s


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


def sfx(v, n=0):
    """a signed number with a typographic minus (textcomp) and an explicit plus"""
    if v is None:
        return NA
    t = f"{float(v):+.{n}f}"
    return t.replace("-", r"\textminus{}")


def thou(v):
    """an integer with a LaTeX thousands separator"""
    if v is None:
        return NA
    return f"{int(round(float(v))):,}".replace(",", "{,}")


def get(d, *keys):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


M: dict[str, str] = {}


# ------------------------------------------------------------------ design record and stack
def design():
    import yaml
    rec = yaml.safe_load((R / "configs" / "design_points.yaml").read_text())
    key = rec["production"]
    e = rec["designs"][key]
    M["MthNcells"] = str(e["n_vr"])
    M["MthGrid"] = str(int(round(math.sqrt(e["n_vr"]))))
    M["MthCellSide"] = fx(e["cell_side_mm"], 2)
    M["MthCellArea"] = fx(e["cell_area_mm2"], 2)
    M["MthSynthArea"] = fx(e["synthesized_area_mm2"], 2)
    hts = [t["height_um"] for t in e["tiers"]]
    for k, h in zip(("One", "Two", "Three", "Four"), hts):
        M[f"MthTier{k}"] = fx(h, 0)
    M["MthStackUm"] = fx(e["converter_stack_um"], 0)
    M["MthStackMm"] = fx(e["converter_stack_um"] / 1000.0, 2)
    ph = e["part_heights_um"]
    M["MthHtHs"], M["MthHtLs"] = fx(ph["gan_hs"], 0), fx(ph["gan_ls"], 0)
    M["MthHtL"], M["MthHtCf"] = fx(ph["inductor"], 0), fx(ph["cap_fly"], 0)
    M["MthKeepout"] = fx(e["keepout_um"], 0)
    dec = e.get("decoupling") or {}
    M["MthKopen"] = fx(dec.get("k_open"), 2)
    M["MthNring"] = str(dec.get("n_ring", NA))
    # the co-design comparison (5 tiers) and the thin-capacitor sensitivity
    for k, v in rec["designs"].items():
        if v.get("role") == "co-design comparison":
            M["MthStackFiveMm"] = fx(v["converter_stack_um"] / 1000.0, 2)
            M["MthFswFive"] = fx(v["f_sw_hz"] / 1e3, 0)
    return rec, key, e


def geometry(e):
    g = (J(FC / "architecture_geometry.json") or {}).get("architectures") or {}
    z1, z2 = g.get("Z1") or {}, g.get("Z2") or {}
    cx = sorted((z1.get("cells") or {}).get("centres_x_mm") or [])
    if len(cx) > 1:
        M["MthCellPitch"] = fx(cx[1] - cx[0], 2)
    M["MthSitesFull"] = str(get(z1, "bga", "sites_legal") or NA)
    M["MthSitesRing"] = str(get(z2, "bga", "sites_legal") or NA)
    M["MthCutout"] = fx(z2.get("cutout_mm"), 2)
    M["MthTsvCell"] = thou(get(z1, "tsv", "n_per_cell"))
    L = {l["name"]: l for l in z2.get("layers", [])}
    brd = L.get("board")
    conv = [l for l in z2.get("layers", []) if "converter" in (l.get("roles") or [])]
    if brd and conv:
        zb = min(l["z0_um"] for l in conv)
        M["MthClearZtwo"] = fx(zb - brd["z0_um"], 0)          # converter bottom above board bottom
        # the 5-tier stack hung the same way: attach + land RDL + its stack
        to = (J(TR / "tier_order.json") or {}).get("designs") or {}
        t5 = next((v for v in to.values() if len(v["chosen"]["tier_um"]) == 5), None)
        top = max(l["z1_um"] for l in conv)                    # output end (just below the RDL)
        hang = -top                                            # attach + land-side RDL depth
        if t5:
            z5 = -(hang + t5["chosen"]["stack_um"])
            M["MthProtrude"] = fx(brd["z0_um"] - z5, 0)
    M["MthBoardMm"] = fx((brd or {}).get("t_um", 0) / 1000.0, 1) if brd else NA


def tier_order(key):
    to = (J(TR / "tier_order.json") or {}).get("designs") or {}
    t = to.get(key)
    if not t:
        return
    ch = t["chosen"]
    M["MthNorders"] = str(t["n_decided_orders"])
    M["MthNviaOK"] = str(t["n_meeting_via_rule"])
    M["MthWorstAR"] = fx(ch["worst_ar_both"], 1)
    M["MthViaD"] = fx(t["via_diameter_um"], 0)
    M["MthRouteChosen"] = fx(ch["routing_loss_W"], 2)
    M["MthRouteWorst"] = fx(ch["routing_loss_range_W"][1], 1)
    M["MthRouteLeast"] = fx(t["least_routing_loss_order"]["routing_loss_W"], 2)
    M["MthRouteTie"] = fx(t["routing"]["tie_W"], 1)
    M["MthHeatChosen"] = fx(ch["heat_path_K"], 1)
    M["MthHeatLeast"] = fx(t["least_routing_loss_order"]["heat_path_K"], 1)
    M["MthHeatBest"] = fx(t["best_heat_path_order"]["heat_path_K"], 1)
    M["MthRouteBestHeat"] = fx(t["best_heat_path_order"]["routing_loss_W"], 2)
    M["MthKhot"] = fx(t["routing"]["k_hot_48V_nets"], 2)
    # orders whose routing loss lies within the tie band of the least
    lmin = t["least_routing_loss_order"]["routing_loss_W"]
    tie = t["routing"]["tie_W"]
    M["MthNtie"] = str(sum(1 for r in t["rule_ranking"]
                           if r["routing_loss_W"] <= lmin + tie + 1e-12))
    sf = t.get("single_face") or {}
    M["MthSingleSame"] = "yes" if sf.get("same_as_chosen") else "no"
    M["MthSingleAR"] = fx(sf.get("chosen_order_worst_ar_single"), 1)
    rs = t.get("repartition_search") or {}
    M["MthNgroupings"] = str(rs.get("n_groupings", NA))
    M["MthNregroup"] = str(rs.get("n_ordered", NA))
    M["MthRegroupAR"] = fx(get(rs, "best_worst_ar", "worst_ar_both"), 1)
    M["MthRegroupVia"] = str(rs.get("n_meeting_via_rule", NA))
    for k, v in to.items():
        n = len(v["chosen"]["tier_um"])
        if "THIN" in v.get("design", ""):
            M["MthThinAR"] = fx(v["chosen"]["worst_ar_both"], 1)
            M["MthThinStackMm"] = fx(v["chosen"]["stack_um"] / 1000.0,2)
            M["MthThinVia"] = str(v["n_meeting_via_rule"])
            M["MthThinRegroupVia"] = str(get(v, "repartition_search", "n_meeting_via_rule") or 0)
        elif n == 5:
            M["MthFiveOrders"] = str(v["n_decided_orders"])
            M["MthFiveAR"] = fx(v["chosen"]["worst_ar_both"], 1)


def cards(key):
    cc = (J(TR / "converter_cards.json") or {})
    d = get(cc, "designs", key) or {}
    s = d.get("summary") or {}
    kz = [v["kz"] for v in s.values()]
    if kz:
        M["MthKzLo"], M["MthKzHi"] = fx(min(kz), 0), fx(max(kz), 0)
    t1 = s.get("conv_tier1") or {}
    M["MthKzTierOne"] = fx(t1.get("kz"), 1)
    M["MthKzTierOneEncap"] = fx(t1.get("kz_gap_encapsulant_legacy"), 1)
    lo = [v["kz_post_range"][0] for v in s.values() if v.get("kz_post_range")]
    hi = [v["kz_post_range"][1] for v in s.values() if v.get("kz_post_range")]
    if lo:
        M["MthKzPostLo"], M["MthKzPostHi"] = fx(min(lo), 0), fx(max(hi), 0)
    kxy = [v["kx"] for v in s.values()]
    if kxy:
        M["MthKxyLo"], M["MthKxyHi"] = fx(min(kxy), 1), fx(max(kxy), 1)
    M["MthJpost"] = fx((cc.get("j_post_A_m2") or 0) / 1e6, 0) if cc.get("j_post_A_m2") else NA


# ------------------------------------------------------------------ cold plate
def cooling():
    c = J(TR / "cooling_spec.json")
    if not c:
        return
    p = c["plate"]
    cf = p.get("cfd_comparison") or {}
    M["MthCfdErr"] = fx(abs(cf.get("dT_base_mean_rel_diff", float("nan"))) * 100, 1) \
        if cf.get("dT_base_mean_rel_diff") is not None else NA
    M["MthCfdSign"] = ("lower" if (cf.get("dT_base_mean_rel_diff") or 0) < 0 else "higher")
    M["MthCfdCells"] = thou(cf.get("cfd_cells"))
    dv = p.get("developing_flow_check") or {}
    M["MthLthRatio"] = fx(dv.get("L_th_over_pass"), 2)
    M["MthNuDevRatio"] = fx(dv.get("Nu_mean_developing_over_fd"), 2)
    M["MthTbulk"] = fx(get(p, "fluid", "T_bulk_mean_C"), 1)
    M["MthAspect"] = fx(get(p, "geometry", "aspect_ratio"), 3)
    M["MthDh"] = fx(get(p, "geometry", "D_h_um"), 0)
    M["MthFlowPass"] = fx(get(p, "construction", "m_dot_per_pass_g_s"), 2)
    for a, tag in ATAG.items():
        cs = get(c, "tiers", "B", "cases", a) or {}
        M[f"MthBotFlow{tag}"] = fx(cs.get("m_dot_bottom_g_s"), 2)
        M[f"MthBotQ{tag}"] = fx(cs.get("q_bottom_plate_W"), 0)
    hy = p.get("hydraulics") or {}
    M["MthDpTurnHead"] = fx((hy.get("dp_turns_kPa") or 0) + (hy.get("dp_header_kPa") or 0), 1)


# ------------------------------------------------------------------ production cases
def production_cases():
    import sys
    sys.path.insert(0, str(R / "scripts"))
    files = {(t, a): SENS / f"etm_{a}_HV_SDEC__sdec_{t}.json" for t in "AB" for a in ATAG}
    iters, ratios, resid, per_case, dep = [], [], [], [], []
    for (t, a), f in files.items():
        c = J(f)
        if not c:
            continue
        h = c.get("et_history") or []
        iters.append(len(h))
        P = [r["P_loss_w"] for r in h]
        dP = [abs(P[k + 1] - P[k]) for k in range(len(P) - 1)]
        rc = [dP[k] / dP[k - 1] for k in range(1, len(dP)) if dP[k - 1] > 1e-9]
        ratios += rc
        if rc:
            per_case.append((statistics.median(rc), t, a))
        resid.append(abs(get(c, "thermal", "energy_residual_rel") or 0))
        dep.append(abs(get(c, "thermal", "deposit_residual_rel") or 0))
        tag = ATAG[a]
        if t == "A":
            M[f"MthEtMin{tag}"] = fx((c.get("et_wall_s") or 0) / 60.0, 0)
            M[f"MthMechMin{tag}"] = fx((get(c, "mechanics", "wall_s") or 0) / 60.0, 0)
            M[f"MthTotH{tag}"] = fx(((c.get("et_wall_s") or 0)
                                      + (get(c, "mechanics", "wall_s") or 0)) / 3600.0, 1)
            M[f"MthNodes{tag}"] = thou(get(c, "thermal", "n_nodes"))
            M[f"MthElems{tag}"] = thou(get(c, "thermal", "n_elems"))
            M[f"MthEtIters{tag}"] = str(len(h))
            M[f"MthEtIterMin{tag}"] = fx((c.get("et_wall_s") or 0) / max(len(h), 1) / 60.0, 1)
        # interconnect-layer search: largest shear driver gamma = |du_xy| / h per layer
        ic = get(c, "mechanics", "interconnects") or {}
        for lay, v in ic.items():
            g = v.get("gamma_max")
            nm = {"bga": "Bga", "interface": "Bump", "conv_attach_vr_substrate": "Attach",
                  "z3_attach_vr_pcb": "Attach"}.get(lay)
            if nm and g is not None:
                M[f"MthGamma{nm}{t}{tag}"] = fx(100 * g, 2)
    if iters:
        M["MthEtItersLo"], M["MthEtItersHi"] = str(min(iters)), str(max(iters))
    if per_case:
        # the fixed point contracts geometrically: the ratio of successive loss changes,
        # per case (median over its iterations), and its range over the compared cases
        lo, hi = min(per_case), max(per_case)
        M["MthEtContractLo"], M["MthEtContractHi"] = fx(lo[0], 2), fx(hi[0], 2)
        M["MthEtContractCase"] = f"{hi[2]} under cooling~{hi[1]}"
    if resid:
        # math-mode strings: the largest relative residual, as an order-of-magnitude bound
        M["MthEnergyResid"] = f"10^{{{math.ceil(math.log10(max(resid)))}}}"
    if dep and max(dep) > 0:
        M["MthDepositResid"] = f"10^{{{math.ceil(math.log10(max(dep)))}}}"
    et = [float(M[f"MthEtMin{t}"]) for t in ATAG.values() if M.get(f"MthEtMin{t}", NA) != NA]
    if et:
        M["MthEtMinLo"], M["MthEtMinHi"] = fx(min(et), 0), fx(max(et), 0)
    me = [float(M[f"MthMechMin{t}"]) for t in ATAG.values() if M.get(f"MthMechMin{t}", NA) != NA]
    if me:
        M["MthMechMinLo"], M["MthMechMinHi"] = fx(min(me), 0), fx(max(me), 0)
    th = [float(M[f"MthTotH{t}"]) for t in ATAG.values() if M.get(f"MthTotH{t}", NA) != NA]
    if th:
        M["MthTotHLo"], M["MthTotHHi"] = fx(min(th), 1), fx(max(th), 1)


# ------------------------------------------------------------------ BGA provisioning
def bga():
    d = J(FC / "bga_count_production.json")
    if not d:
        return
    pm = get(d, "ball_currents_at_count", "port_model") or {}
    M["MthBgaRmsBound"] = fx(pm.get("I_ball_rms_max_A"), 1)
    M["MthBgaTarget"] = fx(d.get("criterion_A_per_ball"), 1)
    M["MthBgaTargetSens"] = fx(d.get("criterion_sensitivity_A_per_ball"), 1)
    cs = d.get("closure_sensitivity") or {}
    z1 = cs.get("Z1__HV_SDEC") or {}
    z2 = cs.get("Z2__HV_SDEC") or {}
    M["MthBgaSensZone"] = ("none" if str(z1.get("status", "")).startswith("NOT_SATISFIABLE")
                           else str(z1.get("n_min_screen") or NA))
    M["MthBgaSensZtwo"] = ("none" if str(z2.get("status", "")).startswith("NOT_SATISFIABLE")
                           else str(z2.get("n_min_screen") or NA))


def limits():
    """the declared limits of the feasibility stage, parsed from its source (no import)"""
    src = (R / "scripts" / "tcpmt_feasibility.py").read_text()
    tree = ast.parse(src)
    lim = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "LIMITS"
                                                for t in node.targets):
            lim = ast.literal_eval(node.value)
    if not lim:
        return
    M["MthLimGan"] = fx(lim["gan_Tj_C"], 0)
    M["MthLimRonFit"] = fx(lim["ron_fit_max_C"], 0)
    M["MthLimMlcc"] = fx(lim["mlcc_C"], 0)
    M["MthLimInd"] = fx(lim["inductor_C"], 0)
    M["MthLimBuildup"] = fx(lim["buildup_Tg_C"], 0)
    M["MthLimEncap"] = fx(lim["encapsulant_Tg_C"], 0)
    M["MthLimBoard"] = fx(lim["board_Tg_C"], 0)
    M["MthLimDie"] = fx(lim["die_C"], 0)
    M["MthLimSolder"] = fx(lim["solder_cal_C"], 0)
    M["MthLimSolidus"] = fx(lim["solder_solidus_C"], 0)
    M["MthLimDrop"] = fx(lim["ir_drop_mV_per_rail"], 0)
    M["MthLimSites"] = fx(100 * lim["bga_power_site_fraction_max"], 0)


# ------------------------------------------------------------------ Z3 land side
def z3land():
    d = J(TR / "z3_board_plane_spreading.json")
    if not d:
        return
    M["MthLandKappa"] = fx(get(d, "land_side", "committed", "kappa_one_rail"), 4)
    M["MthLandKappaV"] = fx(get(d, "land_side", "committed", "kappa_V_one_rail"), 3)
    M["MthLandOcc"] = fx(100 * (get(d, "land_side", "committed", "occupancy") or 0), 0)
    M["MthLandGrid"] = fx(get(d, "grid_mm"), 1)
    M["MthLandGridChk"] = fx(abs(get(d, "land_side", "grid_check", "kappa_change_rel") or 0)
                             * 100, 0)
    M["MthPlaneKappa"] = fx(get(d, "board_planes", "kappa_two_rails"), 4)
    M["MthPlaneT"] = fx(get(d, "board_planes", "allocation", "t_plane_um"), 0)
    M["MthPlaneN"] = str(get(d, "board_planes", "allocation", "planes_per_rail") or NA)
    M["MthPlaneOcc"] = fx(100 * (get(d, "board_planes", "allocation", "occupancy") or 0), 0)
    M["MthPlaneGridChk"] = fx(abs(get(d, "board_planes", "grid_check_change_rel") or 0) * 100, 0)
    zc = J(SENS / "etm_Z3_HV_SDEC__sdec_A.json") or {}
    for r in zc.get("ledger_rows", []):
        if r["term"] == "P_sub_land_1V_spreading":
            import re
            m = re.search(r"t_Cu (\d+) um", r["conductor"])
            M["MthLandT"] = m.group(1) if m else NA
        if r["term"] == "P_PCB_via_VDD":
            import re
            m = re.search(r"VDD: (\d+)/cell", r["conductor"])
            M["MthPthCell"] = m.group(1) if m else NA
        if r["term"] == "P_VR_PCB_attach_VDD":
            import re
            m = re.search(r"VDD: (\d+) SAC305", r["conductor"])
            M["MthZthreeBumps"] = m.group(1) if m else NA
    z2 = J(SENS / "etm_Z2_HV_SDEC__sdec_A.json") or {}
    for r in z2.get("ledger_rows", []):
        if r["term"] == "P_VR_attach_VDD":
            import re
            m = re.search(r"VDD: (\d+) Cu-pillar", r["conductor"])
            M["MthPillarCell"] = thou(m.group(1)) if m else NA


def feed():
    d = J(TR / "platform_inclusive.json") or {}
    pp = get(d, "feed_design", "Z3_plane_pair") or {}
    M["MthFeedPlaneT"] = fx(pp.get("t_um"), 0)
    ring = get(d, "feed_design", "Z2_bga_ring") or {}
    M["MthRingDropMv"] = fx(get(ring, "max_sheet_drop_mV", "SDEC"), 0)


# ------------------------------------------------------------------ verification
def fullpkg():
    d = J(TR / "fullpkg_verification.json")
    if not d:
        return
    s = get(d, "summary", "Z1") or {}
    c = get(d, "cases", "Z1") or {}
    M["MthFpElems"] = thou(get(c, "moose_mesh", "n_hex"))
    rl = s.get("refinement_ladder") or {}
    M["MthFpErr"] = fx(abs(get(rl, "T_max", "production_mesh_error") or 0), 1)
    M["MthFpOrder"] = fx(get(rl, "T_max", "observed_order"), 1)
    le = rl.get("layer_mean_production_mesh_error_K") or {}
    stack = [abs(le[k]) for k in ("converter_all_tiers", "substrate", "bga", "board") if k in le]
    if stack:
        M["MthFpLayerLo"], M["MthFpLayerHi"] = fx(min(stack), 1), fx(max(stack), 1)
    M["MthFpDie"] = fx(abs(le.get("die", 0)), 2) if "die" in le else NA
    at = s.get("refinement_attribution_x2") or {}
    M["MthFpTt"] = fx(at.get("through_thickness_only_T_max_change_K"), 2)
    M["MthFpX"] = fx(at.get("uniform_2x2x2_T_max_change_K"), 2)
    ne = rl.get("n_elems") or []
    if ne:
        M["MthFpMaxElems"] = fx(max(ne) / 1e6, 1)
    # does the production GCI band of the laddered reference (Z1, ideal decoupling) contain the
    # MOOSE estimate of the production-mesh error of the peak temperature?
    u = J(TR / "uncertainty.json") or {}
    o = get(u, "reference_cases", "Z1", "outputs", "T") or {}
    err = get(rl, "T_max", "production_mesh_error")
    if o.get("U95") is not None and err is not None:
        beta, U = o["bias"], o["U95"]
        inside = beta - U <= -err <= beta + U
        M["MthFpInBand"] = "inside" if inside else "outside"
        M["MthFpBandHi"] = fx(beta + U, 1)


def solver_check():
    d = J(FC / "mesh_convergence.json") or {}
    sc = d.get("structural_solver_checks") or {}
    it = next((v for k, v in sc.items() if "ITERATIVE" in k and v.get("ok")), None)
    dr = next((v for k, v in sc.items() if "SPOOLES" in k and v.get("ok")), None)
    if not (it and dr):
        return
    w = (it["die_warpage_pv_um"] - dr["die_warpage_pv_um"]) / dr["die_warpage_pv_um"]
    du = (it["du_c_um"] - dr["du_c_um"]) / dr["du_c_um"]
    M["MthSolverWarp"] = fx(100 * abs(w), 0)
    M["MthSolverDu"] = fx(100 * abs(du), 0)
    M["MthSolverElems"] = thou(it["n_elems"])
    M["MthSolverMaxDirect"] = thou(max((v.get("n_elems") or 0) for v in sc.values()
                                       if v.get("ok") and "SPOOLES" in v.get("solver", "")))
    # every resolved warpage comparison stays resolved with an uncorrelated solver term
    # |w| y added for each case
    u = J(TR / "uncertainty.json") or {}
    hold = []
    for r in u.get("comparisons", []):
        if r["output"] != "warp" or r["verdict"] != "resolved":
            continue
        s2 = (r["U95"] ** 2 + (abs(w) * r["y_a"]) ** 2 + (abs(w) * r["y_b"]) ** 2) ** 0.5
        hold.append(abs(r["D"] + r["bias"]) > s2)
    M["MthSolverHold"] = ("all" if hold and all(hold) else
                          f"{sum(hold)} of {len(hold)}" if hold else NA)
    mc = d.get("cases", {}).get("Z1", {}).get("steps", {}).get("r11->r21", {})
    M["MthMeshStepT"] = fx(100 * (mc.get("T_max_C") or 0), 1) if mc else NA


def cfd_runtime():
    a = J(FC / "accuracy_speed_matrix.json") or {}
    for r in a.get("rows", []):
        if r["stage"] == "cooling_icepak" and r.get("reference_runtime_s"):
            M["MthCfdMin"] = fx(r["reference_runtime_s"] / 60.0, 0)


def uncertainty():
    u = J(TR / "uncertainty.json")
    if not u:
        return
    comp = [r for r in u.get("comparisons", []) if r["output"] != "eps"]
    M["MthNcomp"] = str(len(comp))
    M["MthNresolved"] = str(sum(1 for r in comp if r["verdict"] == "resolved"))
    cls = [r.get("ladder_class") for r in comp]
    M["MthNasym"] = str(sum(1 for c in cls if c == "asymptotic"))
    M["MthNosc"] = str(sum(1 for c in cls if c == "oscillatory"))
    M["MthNnotasym"] = str(sum(1 for c in cls if c == "not asymptotic"))
    own = [r for r in comp if r.get("basis") == "own ladders"]
    M["MthNownLadder"] = str(len(own))
    cases = u.get("cases") or {}
    nlad = sum(1 for t in cases.values() for c in t.values() if c.get("own_ladder"))
    M["MthNladders"] = str(nlad)
    bp = [c["outputs"]["P"]["bias"] for t in cases.values() for c in t.values()
          if get(c, "outputs", "P", "bias") is not None]
    bt = [c["outputs"]["T"]["bias"] for t in cases.values() for c in t.values()
          if get(c, "outputs", "T", "bias") is not None]
    if bp:
        M["MthBiasPLo"], M["MthBiasPHi"] = fx(min(bp), 2), fx(max(bp), 2)
    if bt:
        M["MthBiasTLo"], M["MthBiasTHi"] = fx(min(bt), 1), fx(max(bt), 1)
    up = [c["outputs"]["P"]["U95_rel"] for t in cases.values() for c in t.values()
          if get(c, "outputs", "P", "U95_rel") is not None]
    if up:
        M["MthUPrelLo"], M["MthUPrelHi"] = fx(100 * min(up), 1), fx(100 * max(up), 1)
    ut = [c["outputs"]["T"]["U95"] for t in cases.values() for c in t.values()
          if get(c, "outputs", "T", "U95") is not None]
    if ut:
        M["MthUTLo"], M["MthUTHi"] = fx(min(ut), 1), fx(max(ut), 1)
    rel = u.get("relative") or {}
    for a in ("Z1", "Z2"):
        tag = ATAG[a]
        for y, nm in (("warp", "Warp"), ("du", "Du"), ("T", "T"), ("P", "P")):
            v = get(rel, a, y, "tt")
            if v is not None:
                M[f"MthTt{nm}{tag}"] = fx(100 * v, 1 if 100 * v < 10 else 0)
    nr = [r for r in comp if r["verdict"] != "resolved"]
    M["MthNotResolved"] = "; ".join(f"{r['tier']} {r['a']}/{r['b']} {r['output']}" for r in nr) \
        or "none"
    # the Z1/Z2 loss gap under cooling A on its own ladder
    for r in comp:
        if (r["tier"], r["a"], r["b"], r["output"]) == ("A", "Z1", "Z2", "P"):
            M["MthGapAPloss"] = fx(abs(r["D"]), 1)
            M["MthGapAPlossU"] = fx(r["U95"], 2)
            M["MthGapAPlossSum"] = fx((get(cases, "A", "Z1", "outputs", "P", "U95") or 0)
                                      + (get(cases, "A", "Z2", "outputs", "P", "U95") or 0), 1)


# ------------------------------------------------------------------ local solder model
def solder():
    d = J(TR / "solder_studies.json")
    if not d:
        return
    co = d.get("constitutive") or {}
    cal = co.get("production_card_calibration_window_MPa")
    if cal:
        M["MthCalLo"], M["MthCalHi"] = fx(cal[0], 1), fx(cal[1], 1)
    tw = co.get("production_window_time_weighted_MPa") or {}
    if tw:
        M["MthVisHotLo"], M["MthVisHotHi"] = fx(tw["hot"][0], 0), fx(tw["hot"][1], 0)
        M["MthVisColdLo"], M["MthVisColdHi"] = fx(tw["cold"][0], 0), fx(tw["cold"][1], 0)
    fin = co.get("final") or {}
    wf = fin.get("window_fit_MPa") or {}
    if wf:
        M["MthRefitHotLo"], M["MthRefitHotHi"] = fx(wf["hot"][0], 1), fx(wf["hot"][1], 1)
        M["MthRefitColdLo"], M["MthRefitColdHi"] = fx(wf["cold"][0], 1), fx(wf["cold"][1], 1)
    M["MthRefitIters"] = str(len(co.get("iterations") or [])) if co.get("iterations") else NA
    M["MthRefitConv"] = "yes" if co.get("converged") else "no"
    sp = co.get("mapping_spread_rel") or {}
    if sp:
        M["MthRefitSpread"] = fx(100 * max(sp.values()), 1)
    alt = co.get("alternative_law") or {}
    M["MthRefitN"] = fx(alt.get("n"), 2)
    rk = co.get("rankings_production") or {}
    M["MthRankLawA"] = rk.get("A", NA)
    M["MthRankLawB"] = rk.get("B", NA)
    # critical joint: the case where another site out-responds the max-du site, and by how much
    cj = (d.get("critical_joint") or {}).get("cases") or {}
    worst = min(((v.get("margin_rel"), k) for k, v in cj.items()
                 if v.get("margin_rel") is not None), default=(None, None))
    M["MthCritMargin"] = fx(abs(worst[0]) * 100, 1) if worst[0] is not None and worst[0] < 0 \
        else "0"
    M["MthCritCase"] = (worst[1] or NA).replace("_", " ")
    M["MthCritNotMax"] = str(sum(1 for v in cj.values() if not v.get("critical_is_max_du")))
    # averaging band: the v2 study at the production critical joints (tcpmt_mech_band_study:
    # the production local model, six joints, L0 and L2); the round-2 legacy study otherwise
    v2 = J(TR / "solder_band_study_v2.json") or {}
    if v2.get("complete"):
        lo, hi = v2["change_range_rel"]
        M["MthBandLo"], M["MthBandHi"] = sfx(100 * lo, 0), sfx(100 * hi, 0)
        bu = sorted(b["band_um"] for b in v2["bands"].values())
        M["MthBandUm"] = ", ".join(fx(x, 0) for x in bu[:-1]) + " and " + fx(bu[-1], 0)
        M["MthBandNjoints"] = str(len(v2["joints"]))
        M["MthBandLevels"] = " and ".join(v2["levels"][::-1])
        M["MthBandProdUm"] = fx(v2["bands"][v2["production_band"]]["band_um"], 0)
        M["MthBandOrderHold"] = "yes" if v2.get("orderings_hold_everywhere") else "no"
    else:
        ab = (d.get("averaging_band") or {}).get("bands") or {}
        ch = []
        for b in ab.values():
            for lev in ("L0", "L2"):
                for a in ("Z1", "Z2"):
                    x = get(b, lev, a, "change_vs_production_band")
                    if x is not None:
                        ch.append(x)
        if ch:
            M["MthBandLo"], M["MthBandHi"] = sfx(100 * min(ch), 0), sfx(100 * max(ch), 0)
        bu = sorted(b.get("band_um") for b in ab.values() if b.get("band_um"))
        if bu:
            M["MthBandUm"] = ", ".join(fx(x, 0) for x in bu[:-1]) + " and " + fx(bu[-1], 0)
    lc = J(FC / "local_cycle_study.json") or {}
    w = [v.get("wall_s") for v in (lc.get("cases") or {}).values() if v.get("wall_s")]
    if w:
        M["MthLocalMin"] = fx(statistics.median(w) / 60.0, 0)
        M["MthLocalCycles"] = str(lc.get("n_cycles", NA))


# ------------------------------------------------------------------ added checks and costs
def extras(e):
    # cell currents of the design record and the production case
    M["MthIcell"] = fx(get(e, "routing", "i_out_per_vr_a"), 1)
    if get(e, "routing", "i_out_per_vr_a") and e.get("i_cell_out_rms_A"):
        M["MthIoutRatio"] = fx(e["i_cell_out_rms_A"] / e["routing"]["i_out_per_vr_a"], 3)
    c = J(SENS / "etm_Z1_HV_SDEC__sdec_A.json") or {}
    if c.get("i_hv_avg_a"):
        M["MthIinCell"] = fx(c["i_hv_avg_a"] / e["n_vr"], 2)
    # matched-reference error of the Z2 ring-feed network
    a = J(FC / "accuracy_speed_matrix.json") or {}
    for r in a.get("rows", []):
        if r["stage"] == "pkg_rdl_Z2" and isinstance(r.get("error"), (int, float)):
            M["MthErrRingNet"] = fx(100 * abs(r["error"]), 2)
    # CFD pressure drop against the correlation (single pass, the CFD's properties)
    cf = get(J(TR / "cooling_spec.json") or {}, "plate", "cfd_comparison") or {}
    if cf.get("dp_cfd_kPa") and cf.get("dp_fd_plus_entrance_correlation_kPa"):
        M["MthCfdDpErr"] = fx(100 * abs(cf["dp_fd_plus_entrance_correlation_kPa"]
                                        / cf["dp_cfd_kPa"] - 1), 1)
    # local numerical U of the stabilized joint responses
    ss = J(TR / "solder_studies.json") or {}
    us = [v.get("U_stab_num") for v in get(ss, "stabilization", "cases").values()
          if v.get("U_stab_num") is not None] if get(ss, "stabilization", "cases") else []
    if us:
        M["MthLocalULo"], M["MthLocalUHi"] = fx(100 * min(us), 1), fx(100 * max(us), 1)
    # through-thickness term of the reference ladders added to every compared case: do the
    # resolved verdicts stay resolved? (Z3 has no reference r12 rung: the larger of the Z1 and
    # Z2 relative terms is applied to it)
    u = J(TR / "uncertainty.json") or {}
    rel = u.get("relative") or {}
    base = {"P": lambda y: y, "T": lambda y: y - 25.0, "warp": lambda y: y, "du": lambda y: y}
    def tt(arch, y):
        v = [get(rel, a, y, "tt") for a in (("Z1", "Z2") if arch == "Z3" else (arch,))]
        v = [x for x in v if x is not None]
        return max(v) if v else 0.0
    hold, flips = [], []
    w = None
    if M.get("MthSolverWarp", NA) != NA:
        w = float(M["MthSolverWarp"]) / 100.0
    for r in u.get("comparisons", []):
        y = r["output"]
        if y not in base or r["verdict"] != "resolved":
            continue
        ua = tt(r["a"], y) * abs(base[y](r["y_a"]))
        ub = tt(r["b"], y) * abs(base[y](r["y_b"]))
        sa = sb = 0.0
        if y == "warp" and w is not None:
            sa, sb = w * r["y_a"], w * r["y_b"]
        s2 = (r["U95"] ** 2 + ua ** 2 + ub ** 2 + sa ** 2 + sb ** 2) ** 0.5
        ok = abs(r["D"] + r["bias"]) > s2
        hold.append(ok)
        if not ok:
            flips.append(f"{r['tier']} {r['a']}/{r['b']} {y}")
    M["MthTtHold"] = ("all" if hold and all(hold) else
                      f"{sum(hold)} of {len(hold)}" if hold else NA)
    M["MthTtFlips"] = "; ".join(flips) or "none"
    # RMS factors of the input states: bare (the pulse at the buck duty) and implemented
    pl = J(TR / "platform_inclusive.json") or {}
    M["MthKbare"] = fx(get(pl, "k_feed", "S1"), 1)
    idc = J(TR / "input_decoupling.json") or {}
    M["MthKeq"] = fx(get(idc, "summary", "recommended", "k_eq"), 2)
    M["MthNphases"] = str(get(idc, "summary", "recommended", "n_clock_phases") or NA)
    M["MthKcell"] = fx(get(idc, "summary", "k_open_cell_waveform"), 2)
    sc = (J(FC / "mesh_convergence.json") or {}).get("structural_solver_checks") or {}
    bad = [v.get("n_elems") for v in sc.values() if not v.get("ok") and v.get("n_elems")]
    if bad:
        M["MthSolverFailElems"] = thou(min(bad))
    # campaign wall times of the analytical stages (job ledger)
    led = ROOT / "_campaign" / "ledger.jsonl"
    walls = {}
    if led.is_file():
        for ln in led.read_text().splitlines():
            try:
                x = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if x.get("event") == "done" and x.get("wall_s") is not None:
                walls[x["job"]] = x["wall_s"]
    if "dse.etm35_p2_t4" in walls:
        M["MthDseMin"] = fx(walls["dse.etm35_p2_t4"] / 60.0, 0)
    if "prep.tier_order" in walls:
        M["MthTierOrderMin"] = fx(walls["prep.tier_order"] / 60.0, 0)
    if "prep.converter_cards" in walls:
        M["MthCardsSec"] = fx(walls["prep.converter_cards"], 0)
    import csv
    pc = TR / "dse_j35" / "data" / "case_D_etm35_p2_t4.csv"
    if pc.is_file():
        rows = list(csv.DictReader(pc.open()))
        M["MthDseCounts"] = str(len({r["M"] for r in rows}))


def main():
    rec, key, e = design()
    geometry(e)
    tier_order(key)
    cards(key)
    cooling()
    production_cases()
    bga()
    limits()
    z3land()
    feed()
    fullpkg()
    solver_check()
    cfd_runtime()
    uncertainty()
    solder()
    extras(e)
    M.update({f"{k}Word": word(M[k]) for k in WORD_FORM if k in M})
    lines = ["% GENERATED by scripts/tcpmt_writer_macros_methods.py (numbers not in "
             "results_macros.tex)", f"% source: {ROOT.relative_to(R) if ROOT.is_relative_to(R) else ROOT}"]
    for k in sorted(M):
        lines.append(f"\\newcommand{{\\{k}}}{{{M[k]}}}")
    OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT} ({len(M)} macros)")
    for k in sorted(M):
        print(f"  {k} = {M[k]}")


if __name__ == "__main__":
    main()
