"""FINAL CLOSURE --- the physical electrical ledger, one owner per conductor.

Every conductor in the Z1/Z2 power path appears exactly once, with its geometry,
current type, scenario, resistance model, resistance at its own temperature, loss,
the FE tier its heat is deposited in, and its evidence class. Nothing is silently
zero: a term the production geometry does not contain is recorded as
STRUCTURALLY_ABSENT with the reason and the alternative quantified.

The 48 V side is SCENARIO-CONDITIONED (HV-S0/S1/S2 are named scenarios, never a
bracket). The 48 V average current is SELF-CONSISTENT: it is the current that
carries the load plus the losses this ledger itself computes, iterated to a fixed
point, because the package losses depend on the very current they help set.
"""
from __future__ import annotations

import json
import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
for _p in ("scripts/phase0nw", "scripts/phase0m", "scripts/phase0mr", "scripts/phase0e",
           "scripts/phase0dr", "scripts/phase0i", "scripts/phase0g", "scripts/phase0b",
           "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))

P_LOAD_W, V_IN, V_OUT, N_VR = 1000.0, 48.0, 1.0, 49
SCENARIOS = ("HV_S0", "HV_S1", "HV_S2")
#: HV RMS / HV average for each named scenario -- the rms_currents definitions
#: (S0 continuous; S1 square pulse at the buck duty; S2 square pulse at 1/48).
SCEN_RATIO = {"HV_S0": 1.0, "HV_S1": 1.0 / math.sqrt(0.0625),
              "HV_S2": math.sqrt(V_IN / V_OUT)}

LAYERS = {
    "Z1": {"hs": "z1conv_1_gan_hs_EPC2014C", "ls": "z1conv_3_gan_ls_EPC2057",
           "caps": "z1conv_5_flying_caps", "ind": "z1conv_7_inductor_plus_cout",
           "rdl": ["z1conv_0_bottom_substrate_rdl", "z1conv_2_interlayer_rdl",
                   "z1conv_4_interlayer_rdl", "z1conv_6_interlayer_rdl",
                   "z1conv_8_output_rdl"],
           "lv": "z1conv_8_output_rdl", "tsv": "sub_lower", "pads": "interface",
           "bga": "bga", "pkg_hv": "bga", "die": "die"},
    "Z2": {"hs": "conv_7_gan_hs_EPC2014C", "ls": "conv_3_gan_ls_EPC2057",
           "caps": "conv_5_flying_caps", "ind": "conv_1_inductor_plus_cout",
           "rdl": ["conv_0_land_side_attach_rdl", "conv_2_interlayer_rdl",
                   "conv_4_interlayer_rdl", "conv_6_interlayer_rdl"],
           "lv": "z2_top_rdl", "tsv": "sub_lower", "pads": "interface",
           "bga": "bga", "pkg_hv": "bga", "die": "die"},
}

#: the intra-VR fidelity policy, declared before the R0/R2/reference differences
#: were read: point-to-point traces -> R0 width rule; via stacks -> R0 via model;
#: the distributed output plane -> R2 sheet. R1 is retired (no net obstructed).
FIDELITY_POLICY = {"lateral": "R0", "vertical": "R0_VIA", "plane": "R2"}
#: production construction of every intra-VR tier: one 10 um copper layer, as the
#: physical stacks carry it. The historical 9-layer routing assumption matched no
#: physical stack (Z1 has five RDL tiers, Z2 four).
INTRA_T_CU_M, INTRA_N_LAYERS, INTRA_J_MAX = 10e-6, 1, 1.0e8
VOUT_PLANE_OCCUPANCY = 0.80          # DECLARED, swept in the sensitivity

PAD_CASES = {
    "COMPACT": "pad field confined to a quarter of the tile",
    "SOURCE_ANCHORED": "DVPD Table III: 200,000 VICs over 20 mm^2, split evenly "
                       "between the two 1 V rails",
    "DISTRIBUTED": "geometric maximum over the full tile at the 0.30 keepout",
}
PAD_PRODUCTION = "SOURCE_ANCHORED"


def rho_ratio_cu(t_c, t_ref=20.0):
    from interconnect import rho_cu
    return rho_cu(t_c) / rho_cu(t_ref)


# ---------------------------------------------------------------------------
# converter intrinsic losses
# ---------------------------------------------------------------------------
def converter_terms(t_conv_c):
    import replay_production as RPX
    dec = RPX.converter_terms(t_conv_c)
    sysw = lambda k: dec[k] * N_VR
    return {
        "P_conv_hs": sysw("P_switch_hs_conduction") + sysw("P_switching_hard")
                     + sysw("P_gate") + sysw("P_Coss"),
        "P_conv_ls": sysw("P_switch_ls_conduction"),
        "P_conv_inductor_dcr": sysw("P_inductor_DCR"),
        "P_conv_cap_esr": sysw("P_cap_ESR"),
        "_check_total_w": dec["p_conv_total_w"],
    }


# ---------------------------------------------------------------------------
# intra-VR: R0 traces and via stacks, R2 output plane
# ---------------------------------------------------------------------------
@lru_cache(maxsize=4)
def vout_plane_r2(occupancy=VOUT_PLANE_OCCUPANCY, level=2):
    """Output plane on the tile: three inductor footprints inject I/3 each, the pad
    field over the tile extracts uniformly. Returns R_eff (Ohm) at 20 C."""
    import routing as RT
    import pkg_rdl_refined as RF
    from interconnect import rho_cu
    s = RT.DESIGN["tile_side_mm"]
    comps = {c.name: c for c in RT.tile_layout(s)}
    legs = [comps[f"L{k}"] for k in range(3)]
    h_fine, h_coarse = RF.LEVELS[level]
    tx = sorted({round(c.x_mm + k * c.w_mm / 2, 9) for c in legs for k in (-1, 1)})
    ty = sorted({round(c.y_mm + k * c.h_mm / 2, 9) for c in legs for k in (-1, 1)})
    fx = RF.axis_faces(-s / 2, s / 2, tx, [], h_fine / 4, h_coarse / 4)
    fy = RF.axis_faces(-s / 2, s / 2, ty, [], h_fine / 4, h_coarse / 4)
    rsq = rho_cu(20.0) / (INTRA_T_CU_M * occupancy)
    sh = RF.RefinedSheet(fx, fy, rsq)
    G = sh.laplacian().tolil()
    rhs = np.zeros(sh.n)
    area = np.outer(sh.dx, sh.dy).ravel()
    rhs -= area / area.sum()                       # uniform extraction, 1 A total
    for c in legs:                                  # 1/3 A over each footprint
        ar = np.zeros(sh.n)
        for i in range(sh.nx):
            ox = min(sh.fx[i + 1], c.x_mm + c.w_mm / 2) - max(sh.fx[i], c.x_mm - c.w_mm / 2)
            if ox <= 0:
                continue
            for j in range(sh.ny):
                oy = (min(sh.fy[j + 1], c.y_mm + c.h_mm / 2)
                      - max(sh.fy[j], c.y_mm - c.h_mm / 2))
                if oy > 0:
                    ar[sh.node(i, j)] = ox * oy
        rhs += (1.0 / 3.0) * ar / ar.sum()
    ref = int(np.argmin(np.abs(sh.cx - 0)[:, None] + np.abs(sh.cy - s / 2)[None, :]))
    G[ref, :] = 0.0
    G[ref, ref] = 1.0
    rhs[ref] = 0.0
    import scipy.sparse.linalg as spla
    V = spla.spsolve(G.tocsr(), rhs)
    Lp = sh.laplacian().tocoo()
    up = Lp.row < Lp.col
    p = float(np.sum(-Lp.data[up] * (V[Lp.row[up]] - V[Lp.col[up]]) ** 2))
    return p, sh.n


def intra_vr(t_conv_c, scen):
    """Per-system intra-VR metal and vertical losses under the fidelity policy."""
    import routing as RT
    rr = RT.route_loss("R0", t_cu_m=INTRA_T_CU_M, j_max=INTRA_J_MAX,
                       via_policy="D_area_optimal", n_layers=INTRA_N_LAYERS)
    k_t = rho_ratio_cu(t_conv_c, RT.T_C)
    p_lat = p_vert = 0.0
    nets = []
    for n in rr["nets"]:
        if n["net"] == "vout_plane":
            continue
        scale = SCEN_RATIO[scen] ** 2 if n["rail"] == "HV" else 1.0
        p = n["P_w_per_vr"] * k_t * scale
        if n["geom"] == "vertical":
            p_vert += p
        else:
            p_lat += p
        nets.append({"net": n["net"], "geom": n["geom"], "rail": n["rail"],
                     "model": FIDELITY_POLICY["vertical" if n["geom"] == "vertical"
                                               else "lateral"],
                     "R_ohm": n["R_mohm"] * 1e-3 * k_t, "P_w_per_vr": p})
    r_plane_20, n_cv = vout_plane_r2()
    i_out = RT.DESIGN["i_out_per_vr_a"]
    import rms_currents as RMS
    i_out_rms = RMS.cell_currents()["i_cell_out_rms_a"]
    p_plane = i_out_rms ** 2 * r_plane_20 * rho_ratio_cu(t_conv_c)
    nets.append({"net": "vout_plane", "geom": "plane", "rail": "LV", "model": "R2",
                 "R_ohm": r_plane_20 * rho_ratio_cu(t_conv_c), "P_w_per_vr": p_plane,
                 "n_cv": n_cv, "i_rms_a": i_out_rms, "i_avg_a": i_out})
    return {"P_intraVR_metal": (p_lat + p_plane) * N_VR,
            "P_intraVR_vertical": p_vert * N_VR, "nets": nets}


# ---------------------------------------------------------------------------
# package HV network, BGA, TSV, pads
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def package_network():
    return json.loads((R / "research/final_closure/package_network.json").read_text())


def pad_count(case):
    import pad_interface as PAD
    import rms_currents as RMS
    i = RMS.cell_currents()["i_cell_out_rms_a"]
    base = PAD.size_for_cell(i)
    if case == "DISTRIBUTED":
        return base["PAD_GEOM_MAX"]["n_per_rail"]
    if case == "COMPACT":
        return PAD.geometric_capacity(5.61 / 4.0, 0.30)["n_vdd"]
    if case == "SOURCE_ANCHORED":
        return int(200_000 / N_VR / 2)
    raise ValueError(case)


def ledger(arch, scen, temps, i_hv_avg_a, pad_case=PAD_PRODUCTION):
    """All terms for one architecture and scenario at the given temperatures."""
    import pad_interface as PAD
    import rms_currents as RMS
    import tsv_fields as TF
    import physical_package as PPK
    t_conv, t_bga, t_sub, t_if = (temps["conv"], temps["bga"], temps["sub"],
                                  temps["interface"])
    lay = LAYERS[arch]
    i_hv_rms = i_hv_avg_a * SCEN_RATIO[scen]
    i_cell_rms = RMS.cell_currents()["i_cell_out_rms_a"]
    rows = []

    def add(term, conductor, rail, value, R_ohm, I_a, current_type, model, layer,
            evidence, maturity, note=""):
        rows.append({"arch": arch, "scenario": scen, "term": term,
                     "conductor": conductor, "rail": rail, "P_w": value,
                     "R_ohm": R_ohm, "I_a": I_a, "current_type": current_type,
                     "model": model, "deposit_layer": layer, "evidence": evidence,
                     "maturity": maturity, "note": note})

    ct = converter_terms(t_conv)
    for k, layer, comp in (("P_conv_hs", lay["hs"], "high-side GaN (cond+sw+gate+Coss)"),
                           ("P_conv_ls", lay["ls"], "low-side GaN conduction"),
                           ("P_conv_inductor_dcr", lay["ind"], "inductor DCR"),
                           ("P_conv_cap_esr", lay["caps"], "capacitor ESR")):
        add(k, comp, "converter", ct[k], None, None, "converter model RMS",
            "HVR_FULL_OPT_EPC_V2 closed form at T_conv", layer,
            "CONSERVATION_VERIFICATION", "CLOSED")

    iv = intra_vr(t_conv, scen)
    add("P_intraVR_metal", "cell traces (R0) + output plane (R2)", "mixed",
        iv["P_intraVR_metal"], None, None, "converter-model RMS; HV nets per scenario",
        "R0 width rule + R2 refined FV sheet", ",".join(lay["rdl"]),
        "MODEL_CONSISTENCY", "SCENARIO" if scen != "HV_S0" else "CLOSED")
    add("P_intraVR_vertical", "cell via stacks", "mixed", iv["P_intraVR_vertical"],
        None, None, "converter-model RMS", "R0 via stack, footprint-filling policy",
        ",".join(lay["rdl"]), "CLOSED_FORM_VERIFICATION", "CLOSED")

    pn = package_network()
    loop = pn["loop"][arch]
    kt_bga = rho_ratio_cu(t_bga)
    from interconnect import rho_solder
    kt_sol = rho_solder(t_bga) / rho_solder(20.0)
    for rail in ("supply", "return"):
        r20 = loop[f"r_{rail}_ohm"]
        add(f"P_pkg_RDL_HV_{rail}", f"package HV RDL {rail} sheet", "48V",
            i_hv_rms ** 2 * r20 * kt_bga, r20 * kt_bga, i_hv_rms, f"HV RMS, {scen}",
            "voltage-fed refined FV sheet, N=%d/rail" % loop["n_per_rail"],
            lay["pkg_hv"], "MESH_CONVERGENCE", "SCENARIO" if scen != "HV_S0" else "CLOSED")
        f = np.asarray(pn["convergence"][f"{arch}_{rail}"]["i_ball_frac"])
        r_ball = PAD.bga_ball_resistance_ohm(20.0) * kt_sol
        add(f"P_BGA_{rail}", f"BGA {rail} balls (N=%d)" % len(f), "48V",
            r_ball * i_hv_rms ** 2 * float(np.sum(f ** 2)),
            r_ball / max(1e-30, 1.0 / float(np.sum(f ** 2))), i_hv_rms,
            f"HV RMS, {scen}, solved per-ball split", "Table III rho_solder h / A",
            lay["bga"], "SOURCE_REPRODUCTION", "SCENARIO" if scen != "HV_S0" else "CLOSED")

    cfg = PPK.load_physical_package_config(R / "configs/phase0nt/z2_2p4mm_cutout.yaml")
    if arch == "Z1":
        rep = TF.system_report(cfg.cells, cfg.cell_side_mm, 0.300,
                               i_hv_rms, T_C=t_sub)
        rail_v, cur = "48V", f"HV RMS, {scen}"
    else:
        rep = TF.system_report(cfg.cells, cfg.cell_side_mm, 0.300,
                               i_cell_rms * N_VR, T_C=t_sub)
        rail_v, cur = "1V", "cell output RMS"
    for rail, key in (("VDD", "p_vdd_total_w"), ("GND", "p_gnd_total_w")):
        pc = rep["per_cell"]
        r_cell = pc[f"r_{rail.lower()}_ohm"] + pc[f"r_spread_{rail.lower()}_ohm"]
        add(f"P_TSV_{rail}", f"TSV field {rail}, {pc[f'n_{rail.lower()}']}/cell, "
            f"incl. two-end spreading", rail_v, rep[key], r_cell / N_VR,
            pc["i_cell_a"] * N_VR, cur, "rho L/A per via + compact spreading",
            lay["tsv"], "INDEPENDENT_NUMERICAL_VALIDATION",
            "CLOSED" if (arch == "Z2" or scen == "HV_S0") else "SCENARIO")

    n_pad = pad_count(pad_case)
    r_pad = PAD.pad_bulk_resistance_ohm(t_if)
    for rail in ("VDD", "GND"):
        add(f"P_pad_{rail}", f"source Cu pads, {n_pad}/rail/cell ({pad_case})", "1V",
            N_VR * i_cell_rms ** 2 * r_pad / n_pad, r_pad / n_pad / N_VR, i_cell_rms,
            "cell output RMS", "Table III rho_Cu h / A", lay["pads"],
            "SOURCE_REPRODUCTION", "SENSITIVITY_BOUNDED", PAD_CASES[pad_case])

    p_lv_alt = lv_alternative_loss_w(t_if) / 2.0          # per rail
    for rail in ("supply", "return"):
        add(f"P_pkg_RDL_LV_{rail}", "package LV lateral spreading", "1V", 0.0, 0.0,
            i_cell_rms, "cell output RMS", "none -- see note", lay["lv"],
            "STRUCTURAL", "STRUCTURALLY_ABSENT",
            "the source-pad field sits over the tile footprint (the pad model's own "
            "geometric capacity), so 1 V leaves the package directly above each cell; "
            "the in-tile collection is owned by P_intraVR_metal (R2 output plane) and "
            "the lateral spreading beyond the tile happens in the die's power grid, "
            "outside package scope. ALTERNATIVE, quantified: if the pad field were "
            "spread over the whole cell pitch, a 10 um / 80 %% plane would carry the "
            "spreading at %.4f W per rail (lv_alternative_r_ohm, periodic unit cell)"
            % p_lv_alt)
        rows[-1]["alternative_P_w"] = p_lv_alt
    total = sum(r["P_w"] for r in rows)
    return {"rows": rows, "P_loss_w": total, "intra_vr_nets": iv["nets"],
            "n_pad": n_pad, "i_hv_avg_a": i_hv_avg_a, "i_hv_rms_a": i_hv_rms}


def self_consistent(arch, scen, temps, tol_w=1e-6, max_iter=50, **kw):
    """Fixed point: I_48 = (P_load + P_loss(I_48)) / 48."""
    i = (P_LOAD_W + 130.0) / V_IN
    hist = []
    for k in range(max_iter):
        L = ledger(arch, scen, temps, i, **kw)
        i_new = (P_LOAD_W + L["P_loss_w"]) / V_IN
        hist.append({"iter": k, "i_hv_avg_a": i, "P_loss_w": L["P_loss_w"]})
        if abs(i_new - i) * V_IN < tol_w:
            L["i_hv_avg_a"] = i_new
            break
        i = i_new
    p_in = V_IN * L["i_hv_avg_a"]
    L["energy"] = {"P_input_w": p_in, "P_load_w": P_LOAD_W, "P_loss_w": L["P_loss_w"],
                   "residual_w": p_in - P_LOAD_W - L["P_loss_w"],
                   "residual_rel": (p_in - P_LOAD_W - L["P_loss_w"]) / p_in}
    L["fixed_point_history"] = hist
    return L


# ---------------------------------------------------------------------------
# the ALTERNATIVE LV geometry, quantified rather than asserted
# ---------------------------------------------------------------------------
LV_ALT_T_CU_M, LV_ALT_OCC = 10e-6, 0.80     # a 10 um power plane, declared


@lru_cache(maxsize=2)
def lv_alternative_r_ohm(level=2):
    """If the 1 V pad field were spread over the WHOLE cell pitch instead of the tile,
    the package would have to carry each cell's current laterally from the VOUT tile
    to the pitch boundary. Periodic unit cell (Neumann edges = symmetry), tile held
    through rho_c, uniform areal draw. Returns R per cell at 20 C."""
    import pkg_rdl_refined as RF
    import physical_coords as PCO
    import routing as RT
    from interconnect import rho_cu
    import scipy.sparse as sp
    import scipy.sparse.linalg as spla
    cells = PCO.physical_cell_coordinates()
    xs = sorted({round(x, 6) for x, _ in cells})
    p = xs[1] - xs[0]
    s = RT.DESIGN["tile_side_mm"]
    h_fine, h_coarse = RF.LEVELS[level]
    fx = RF.axis_faces(-p / 2, p / 2, [-s / 2, s / 2], [], h_fine / 2, h_coarse / 2)
    sh = RF.RefinedSheet(fx, fx, rho_cu(20.0) / (LV_ALT_T_CU_M * LV_ALT_OCC))
    G = sh.laplacian().tolil()
    area = np.outer(sh.dx, sh.dy).ravel()
    rhs = -area / area.sum()                         # 1 A drawn uniformly
    tile = np.array([abs(sh.cx[i]) < s / 2 and abs(sh.cy[j]) < s / 2
                     for i in range(sh.nx) for j in range(sh.ny)])
    rho_c = 1e-5
    g_t = np.where(tile, area / rho_c, 0.0)          # tile -> source node at V = 0
    A = G.tocsr() + sp.diags(g_t)
    V = spla.spsolve(A.tocsc(), rhs)
    Lp = sh.laplacian().tocoo()
    up = Lp.row < Lp.col
    p_sheet = float(np.sum(-Lp.data[up] * (V[Lp.row[up]] - V[Lp.col[up]]) ** 2))
    p_cont = float(np.sum(g_t * V ** 2))
    return p_sheet + p_cont


def lv_alternative_loss_w(t_c):
    import rms_currents as RMS
    i = RMS.cell_currents()["i_cell_out_rms_a"]
    return 2 * N_VR * i ** 2 * lv_alternative_r_ohm() * rho_ratio_cu(t_c)
