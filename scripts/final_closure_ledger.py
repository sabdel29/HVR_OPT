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
    "Z1": {"hs": "z1conv_1_gan_hs_EPC2014C", "ls": "z1conv_5_gan_ls_EPC2057",
           "caps": "z1conv_3_flying_caps", "ind": "z1conv_7_inductor_plus_cout",
           "rdl": ["z1conv_0_bottom_substrate_rdl", "z1conv_2_interlayer_rdl",
                   "z1conv_4_interlayer_rdl", "z1conv_6_interlayer_rdl",
                   "z1conv_8_output_rdl"],
           "lv": "z1conv_8_output_rdl", "tsv": "sub_lower", "pads": "interface",
           "bga": "bga", "pkg_hv": "bga", "die": "die"},
    "Z2": {"hs": "conv_7_gan_hs_EPC2014C", "ls": "conv_3_gan_ls_EPC2057",
           "caps": "conv_5_flying_caps", "ind": "conv_1_inductor_plus_cout",
           "rdl": ["conv_0_land_side_attach_rdl", "conv_2_interlayer_rdl",
                   "conv_4_interlayer_rdl", "conv_6_interlayer_rdl"],
           "attach": "conv_attach_vr_substrate",
           "lv": "z2_top_rdl", "tsv": "sub_lower", "pads": "interface",
           "bga": "bga", "pkg_hv": "bga", "die": "die"},
}
#: the BGA-fed CONTROL shares Z2's geometry (attach, clearance) and differs only in its
#: 48 V path (Z2_DIRECT_FEED_ARCHITECTURE.md section 8)
LAYERS["Z2BF"] = dict(LAYERS["Z2"])

#: architecture identity, carried into every artifact so the two Z2s can never be confused
VARIANT = {"Z1": "Z1_EMBEDDED", "Z2": "Z2_DIRECT_FEED", "Z2BF": "Z2_BGA_FED_CONTROL"}
HV_FEED = {"Z1": "BGA_FED", "Z2": "DIRECT_FEED", "Z2BF": "BGA_FED"}
#: the package-level 48 V network of a BGA-fed architecture; package_network.json keys its
#: BGA-fed Z2 network as "Z2"
NETWORK_KEY = {"Z1": "Z1", "Z2BF": "Z2"}
#: terms a direct-fed architecture can NEVER carry: its 48 V never enters the package
FORBIDDEN_DIRECT_FEED_TERMS = ("P_pkg_RDL_HV_supply", "P_pkg_RDL_HV_return",
                               "P_BGA_supply", "P_BGA_return")
ARCH_SPEC = R / "research" / "final_closure" / "z2_direct_feed_architecture.json"

#: Z3 -- the SAME regulator and tier order as Z2, hung from the PCB BACKSIDE
#: (configs/phase0nz/z3_board_backside.yaml). Direct-fed like Z2, so no package 48 V term;
#: its 1 V output crosses a VR-to-PCB solder attach, the board's plated through-holes and the
#: full BGA before the substrate TSVs. `pcb_via` is the board, whose elements under the cells
#: hold the via fields (final_closure_physical_etm.in_tile_keys confines that loss to them).
Z3_CFG = R / "configs" / "phase0nz" / "z3_board_backside.yaml"
LAYERS["Z3"] = {"hs": "z3conv_7_gan_hs_EPC2014C", "ls": "z3conv_3_gan_ls_EPC2057",
                "caps": "z3conv_5_flying_caps", "ind": "z3conv_1_inductor_plus_cout",
                "rdl": ["z3conv_0_land_side_attach_rdl", "z3conv_2_interlayer_rdl",
                        "z3conv_4_interlayer_rdl", "z3conv_6_interlayer_rdl"],
                "attach": "z3_attach_vr_pcb", "pcb_via": "board",
                "lv": "z2_top_rdl", "tsv": "sub_lower", "pads": "interface",
                "bga": "bga", "die": "die"}
VARIANT["Z3"] = "Z3_BOARD_BACKSIDE"
HV_FEED["Z3"] = "DIRECT_FEED"

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


#: component class of each converter tier name in the architecture configs
_TIER_CLASS = (("gan_hs", "gan_hs"), ("gan_ls", "gan_ls"), ("flying_caps", "cap_fly"),
               ("inductor", "inductor"))


def cell_tiers(arch):
    """The tiers of ONE regulator cell, from the input (high-side) end to the output end,
    as [(component_class or 'rdl', thickness_um)], read from the architecture's own config
    so the electrical routing and the meshed stack can never disagree on the tier order
    (TCPMT revision: the physical-lineage ledger used one legacy layout for every
    architecture, with mid-plane via heights, whatever order the mesh carried)."""
    import yaml
    if arch == "Z1":
        cfg = yaml.safe_load((R / "configs" / "phase0nx" / "z1_physical.yaml").read_text())
        raw = cfg["converter"]["tiers_from_substrate_upward"]          # HS end first
    elif arch == "Z3":                       # board-backside Z3: its OWN list, HS deepest
        cfg = yaml.safe_load(Z3_CFG.read_text())
        raw = list(reversed(cfg["converter"]["tiers_from_board_downward"]))
    else:                                    # Z2, Z2BF: HS deepest
        cfg = yaml.safe_load((R / "configs" / "phase0nt" / "z2_2p4mm_cutout.yaml").read_text())
        raw = list(reversed(cfg["converter"]["tiers_from_substrate_downward"]))
    out = []
    for t in raw:
        cls = next((c for key, c in _TIER_CLASS if t["name"].startswith(key)), "rdl")
        out.append((cls, float(t["um"])))
    return out


def face_span_um(tiers, a, b):
    """Dielectric/RDL depth a via must cross between the terminal faces of component
    classes a and b (cap_out shares the inductor tier; 'out' is the output plane)."""
    cls = [c for c, _ in tiers]
    def idx(c):
        c = "inductor" if c == "cap_out" else c
        return len(tiers) if c == "out" else cls.index(c)
    i, j = sorted((idx(a), idx(b)))
    if j == len(tiers):          # inductor terminal -> the output RDL plane above it
        nxt = [h for c, h in tiers[i + 1:] if c == "rdl"]
        return nxt[0] if nxt else 10.0
    return sum(h for _, h in tiers[i + 1:j])


def intra_vr(t_conv_c, scen, arch="Z1"):
    """Per-system intra-VR metal and vertical losses under the fidelity policy.

    Same R0 trace and via models as before; the GEOMETRY now follows the cell's actual tier
    order: every link between components in different tiers is a via stack across the
    face-to-face span of that order (Phase-0M-R3B DEFECT #62 convention), and links
    between components in the same tier are lateral R0 runs."""
    import routing as RT
    d = RT.DESIGN
    comps = {c.name: c for c in RT.tile_layout(d["tile_side_mm"], d)}
    tiers = cell_tiers(arch)
    tier_cls = {c for c, _ in tiers}
    s_m = d["tile_side_mm"] * 1e-3
    k_t = rho_ratio_cu(t_conv_c, RT.T_C)
    p_lat = p_vert = 0.0
    nets = []
    for n in RT.nets(d):
        if n.name == "vout_plane":
            continue
        a, b = comps[n.src], comps[n.dst]
        ka = a.kind if a.kind in tier_cls or a.kind == "cap_out" else None
        kb = ("out" if b.kind == "pad_out" else
              b.kind if b.kind in tier_cls or b.kind == "cap_out" else None)
        same = (ka is None or kb is None or
                ("inductor" if ka == "cap_out" else ka) == ("inductor" if kb == "cap_out" else kb))
        if not same:
            hgt = face_span_um(tiers, ka, kb)
            fp = min(a.w_mm * a.h_mm, b.w_mm * b.h_mm)
            seg = RT.vertical_segment(max(n.i_rms_a, 1e-9), hgt, INTRA_J_MAX, fp,
                                      "D_area_optimal")
            geom, length_mm = "vertical", hgt * 1e-3
        else:
            length_mm = RT.manhattan(a, b)
            seg = RT.lateral_segment(max(n.i_rms_a, 1e-9), length_mm, INTRA_T_CU_M,
                                     INTRA_J_MAX, s_m, INTRA_N_LAYERS)
            geom = "lateral"
        scale = SCEN_RATIO[scen] ** 2 if n.rail == "HV" else 1.0
        p = n.i_rms_a ** 2 * seg["R_ohm"] * k_t * scale
        if geom == "vertical":
            p_vert += p
        else:
            p_lat += p
        nets.append({"net": n.name, "geom": geom, "rail": n.rail,
                     "model": FIDELITY_POLICY[geom], "length_mm": length_mm,
                     "R_ohm": seg["R_ohm"] * k_t, "P_w_per_vr": p})
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


@lru_cache(maxsize=1)
def attach_spec():
    return json.loads(ARCH_SPEC.read_text())["vr_attach"]


def vr_attach_r_per_rail_cell(t_c, spec=None):
    """Resistance of ONE rail of ONE cell's VR attach: n Cu-pillar + solder-cap bumps in
    parallel, R_bump = (rho_Cu h_Cu + rho_solder h_cap) / A at the attach temperature.
    Contact and IMC resistance are not resolved (the all-solder class-B bound brackets
    them). Returns (R_ohm, n_bumps, R_bump_ohm)."""
    from interconnect import rho_cu, rho_solder
    sp = dict(spec or attach_spec())
    a = math.pi * (sp["d_um"] * 1e-6 / 2.0) ** 2
    r_b = (rho_cu(t_c) * sp["h_cu_um"] * 1e-6 + rho_solder(t_c) * sp["h_cap_um"] * 1e-6) / a
    n = int(math.floor(sp["cell_side_mm"] / (sp["pitch_um"] * 1e-3)) ** 2 // 2)
    return r_b / n, n, r_b


def vr_attach_rails(t_c, spec=None):
    """Per rail: (R_rail_per_cell_ohm, n_bumps, R_bump_ohm). A spec from
    final_closure_vr_attach.ledger_spec (the attach-density study) carries the REAL lattice's
    VDD and GND counts (a checkerboard can be odd) and the two-sided constriction into each
    bump, which lives in Cu and scales with its resistivity. The production spec carries
    neither and keeps the legacy model (equal rails, no constriction) -- for the production
    geometry the two agree to the study's stated difference."""
    sp = dict(spec or attach_spec())
    r1, n_leg, r_b = vr_attach_r_per_rail_cell(t_c, sp)
    if "n_vdd" not in sp:
        return {"VDD": (r1, n_leg, r_b), "GND": (r1, n_leg, r_b)}
    r_b = r_b + float(sp.get("r_constriction_20c_ohm", 0.0)) * rho_ratio_cu(t_c)
    return {rail: (r_b / int(sp[k]), int(sp[k]), r_b)
            for rail, k in (("VDD", "n_vdd"), ("GND", "n_gnd"))}


@lru_cache(maxsize=1)
def z3_spec():
    """Z3's board-level 1 V path, from its OWN config (configs/phase0nz/z3_board_backside.yaml):

      attach  the attach-density study's machinery (final_closure_vr_attach): bumps on the
              REAL legal lattice of each cell (edge clearance >= (p - d)/2, VDD/GND
              checkerboard), the series column -- all solder here -- and the two-sided
              constriction of the output-plane current into each bump; the spec form
              vr_attach_rails reads
      via     one plated through-hole under every bump (via-in-pad), so the via field's
              VDD/GND counts ARE the attach lattice's; R = rho_Cu(T) L / A_annulus
      bga     the 1 V ball count of the 1.5 A/ball ENGINEERING criterion on the DC rail
              current, equal sharing (a lower bound on the BGA loss)
    """
    import final_closure_vr_attach as VA
    import physical_package as PPK
    import z3_package as Z3P
    cfg = PPK.load_z3_package_config(Z3_CFG)
    if abs(cfg.bga_1v_criterion_current_a - P_LOAD_W / V_OUT) > 1e-9:
        raise RuntimeError(f"the Z3 BGA count is provisioned for {cfg.bga_1v_criterion_current_a}"
                           f" A but the ledger's 1 V rail carries {P_LOAD_W / V_OUT} A DC")
    a = cfg.attach_dict()
    lat = Z3P.attach_lattice(cfg)
    c_fv = VA.constriction_fv(float(a["pitch_um"]), float(a["diameter_um"]))
    attach = {"h_cu_um": float(a["cu_height_um"]), "h_cap_um": float(a["cap_height_um"]),
              "d_um": float(a["diameter_um"]), "pitch_um": float(a["pitch_um"]),
              "cell_side_mm": Z3P.cell_side_um(cfg) / 1e3,
              "n_vdd": int(lat["n_vdd"]), "n_gnd": int(lat["n_gnd"]),
              "r_constriction_20c_ohm": 2.0 * c_fv * VA.sheet_resistance(20.0),
              "model": "real lattice + all-solder column + two-sided constriction"}
    return {"cfg": cfg, "attach": attach,
            "attach_lattice": {k: lat[k] for k in ("n_per_axis", "n_total", "n_vdd", "n_gnd",
                                                   "edge_clearance_um", "edge_rule_um",
                                                   "area_fraction",
                                                   "area_fraction_infinite_lattice")},
            "via": Z3P.via_field(cfg),
            "bga": {"n_per_rail": cfg.bga_1v_n_per_rail, "sites_total": cfg.bga_sites_total,
                    "criterion_a": cfg.bga_1v_criterion_a,
                    "criterion_current_a": cfg.bga_1v_criterion_current_a}}


def z3_rows(add, lay, temps, t_sub, t_bga, i_cell_rms):
    """The Z3 1 V rows between the converter and the substrate TSVs, in power-path order.
    Each conductor is deposited in its own FE region: the attach tier, the board elements
    under the cells (the via fields), the BGA layer (equal sharing over the whole field).
    The two lateral-spreading conductors the geometry needs but the model does not carry are
    RECORDED as NOT_MODELLED zero rows, never silently absent: each makes the Z3 1 V loss a
    lower bound."""
    import pad_interface as PAD
    from interconnect import rho_cu, rho_solder
    z3 = z3_spec()
    t_att = temps.get("attach", t_sub)
    sp_att = z3["attach"]
    a_bump = math.pi * (sp_att["d_um"] * 1e-6 / 2.0) ** 2
    for rail, (r_rc, n_b, r_b) in vr_attach_rails(t_att, sp_att).items():
        add(f"P_VR_PCB_attach_{rail}", f"VR-to-PCB attach {rail}: {n_b} SAC305 bumps/cell",
            "1V", N_VR * i_cell_rms ** 2 * r_rc, r_rc / N_VR, i_cell_rms, "cell output RMS",
            "rho_solder h / A per bump (all-solder column) + two-sided constriction (real "
            "lattice), n in parallel", lay["attach"], "GEOMETRY_DESIGN_CHOICE", "BOUNDED",
            "d %g um / pitch %g um / standoff %g um; R_bump = %.4g mOhm at %.1f C; %.3f A and "
            "%.0f A/cm2 per bump (OUTPUT only, no allowable claimed)"
            % (sp_att["d_um"], sp_att["pitch_um"], sp_att["h_cap_um"] + sp_att["h_cu_um"],
               r_b * 1e3, t_att, i_cell_rms / n_b, i_cell_rms / n_b / a_bump * 1e-4))
    via = z3["via"]
    t_via = temps.get("pcb_via", t_bga)
    r_via = rho_cu(t_via) * via["L_um"] * 1e-6 / (via["A_annulus_um2"] * 1e-12)
    for rail in ("VDD", "GND"):
        n = via[f"n_{rail.lower()}"]
        add(f"P_PCB_via_{rail}", f"PCB 1 V plated through-holes {rail}: {n}/cell", "1V",
            N_VR * i_cell_rms ** 2 * r_via / n, r_via / n / N_VR, i_cell_rms,
            "cell output RMS", "rho_Cu(T) L / A_annulus per via, n in parallel per rail per "
            "cell", lay["pcb_via"], "CLOSED_FORM_GEOMETRY_DESIGN_CHOICE", "BOUNDED",
            "finished hole %g um, plating %g um (drill %g um), pitch %g um, L %g um, via-in-pad "
            "under the attach bumps; R_via = %.4g mOhm at %.1f C"
            % (via["d_finished_um"], (via["d_drill_um"] - via["d_finished_um"]) / 2.0,
               via["d_drill_um"], via["pitch_um"], via["L_um"], r_via * 1e3, t_via))
    i_rail = i_cell_rms * N_VR
    add("P_PCB_plane_1V_spreading", "PCB 1 V copper planes: via fields -> BGA balls", "1V",
        0.0, None, i_rail, "1 V output RMS of the 49 cells", "none -- NOT MODELLED",
        lay["pcb_via"], "STRUCTURAL", "NOT_MODELLED",
        "the via fields sit only under the 49 cells while the 1 V balls cover the whole "
        "lattice, so the PCB planes must spread ~1 kA laterally between them; that loss is "
        "NOT modelled and the Z3 1 V loss is a LOWER BOUND")
    bga = z3["bga"]
    r_ball = PAD.bga_ball_resistance_ohm(20.0) * rho_solder(t_bga) / rho_solder(20.0)
    n = bga["n_per_rail"]
    for rail in ("VDD", "GND"):
        add(f"P_BGA_1V_{rail}", f"BGA 1 V {rail} balls (N={n}, equal sharing)", "1V",
            i_rail ** 2 * r_ball / n, r_ball / n, i_rail, "1 V output RMS of the 49 cells",
            "Table III rho_solder h / A per ball, equal sharing", lay["bga"],
            "SOURCE_REPRODUCTION", "LOWER_BOUND",
            "%d per rail by the %.1f A/ball ENGINEERING criterion on %.0f A DC (%d of %d sites, "
            "%.1f %%); equal sharing is a lower bound; %.3f A RMS per ball"
            % (n, bga["criterion_a"], bga["criterion_current_a"], 2 * n, bga["sites_total"],
               100.0 * 2 * n / bga["sites_total"], i_rail / n))
    add("P_sub_land_1V_spreading", "package land-side 1 V redistribution: BGA balls -> TSV "
        "fields", "1V", 0.0, None, i_rail, "1 V output RMS of the 49 cells",
        "none -- NOT MODELLED", lay["tsv"], "STRUCTURAL", "NOT_MODELLED",
        "the balls cover the whole lattice while the TSV fields sit only under the 49 cells, "
        "and the Z2 package adopted above the board has no land-side 1 V RDL to carry that "
        "redistribution; NOT modelled, so the Z3 1 V loss is a LOWER BOUND")


def z3_design(rows, temps, i_cell_rms):
    """The Z3 design numbers a reader needs next to the ledger: counts, per-bump and per-ball
    currents (outputs, no allowable claimed) and the fraction of the BGA field the 1 V rails
    consume."""
    z3 = z3_spec()
    p = {r["term"]: r["P_w"] for r in rows}
    att, lat, via, bga = z3["attach"], z3["attach_lattice"], z3["via"], z3["bga"]
    a_bump = math.pi * (att["d_um"] * 1e-6 / 2.0) ** 2
    i_rail = i_cell_rms * N_VR
    n = bga["n_per_rail"]
    return {
        "vr_attach": {
            "technology": "SAC305 solder bumps + underfill", "d_um": att["d_um"],
            "pitch_um": att["pitch_um"], "standoff_um": att["h_cu_um"] + att["h_cap_um"],
            **lat, "bumps_per_rail_per_cell": {"VDD": att["n_vdd"], "GND": att["n_gnd"]},
            "I_per_bump_A": {r: i_cell_rms / att[f"n_{r.lower()}"] for r in ("VDD", "GND")},
            "J_per_bump_A_cm2": {r: i_cell_rms / att[f"n_{r.lower()}"] / a_bump * 1e-4
                                 for r in ("VDD", "GND")},
            "T_attach_C": temps.get("attach"),
            "P_attach_w": p["P_VR_PCB_attach_VDD"] + p["P_VR_PCB_attach_GND"],
            "note": "per-bump current is an OUTPUT; no solder electromigration allowable is "
                    "claimed"},
        "pcb_via_field": {**via, "T_via_C": temps.get("pcb_via"),
                          "P_via_w": p["P_PCB_via_VDD"] + p["P_PCB_via_GND"]},
        "bga_1v": {"n_per_rail": n, "n_total": 2 * n, "sites_total": bga["sites_total"],
                   "fraction_of_field": 2 * n / bga["sites_total"],
                   "sites_left_for_signals_and_other_rails": bga["sites_total"] - 2 * n,
                   "criterion_A_per_ball": bga["criterion_a"],
                   "criterion_current_A_dc": bga["criterion_current_a"],
                   "I_per_ball_A_dc_equal_sharing": bga["criterion_current_a"] / n,
                   "I_per_ball_A_rms_equal_sharing": i_rail / n,
                   "n_per_rail_if_provisioned_on_rms": math.ceil(i_rail / bga["criterion_a"]),
                   "T_bga_C": temps.get("bga"),
                   "P_bga_1v_w": p["P_BGA_1V_VDD"] + p["P_BGA_1V_GND"],
                   "sharing": "EQUAL (lower bound)"},
        "not_modelled": [r["term"] for r in rows if r["maturity"] == "NOT_MODELLED"],
        "lower_bound_statement": ("the Z3 1 V loss is a LOWER BOUND: equal BGA sharing, and "
                                  "neither the PCB plane spreading nor the package land-side "
                                  "redistribution is modelled"),
    }


def ledger(arch, scen, temps, i_hv_avg_a, pad_case=PAD_PRODUCTION):
    """All terms for one architecture and scenario at the given temperatures."""
    import pad_interface as PAD
    import rms_currents as RMS
    import tsv_fields as TF
    import physical_package as PPK
    if arch not in VARIANT:
        raise KeyError(f"unknown architecture {arch!r}; known {sorted(VARIANT)}")
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

    # each device term at the in-cell temperature of its OWN tier, the region its loss is
    # deposited in (final_closure_physical_etm.temperature_regions; DEFECT #68). Without
    # per-tier keys (an older caller) every term falls back to the converter mean.
    ct_at = lru_cache(maxsize=8)(converter_terms)
    for k, layer, comp, key in (
            ("P_conv_hs", lay["hs"], "high-side GaN (cond+sw+gate+Coss)", "hs"),
            ("P_conv_ls", lay["ls"], "low-side GaN conduction", "ls"),
            ("P_conv_inductor_dcr", lay["ind"], "inductor DCR", "ind"),
            ("P_conv_cap_esr", lay["caps"], "capacitor ESR", "caps")):
        t_k = float(temps.get(key, t_conv))
        add(k, comp, "converter", ct_at(t_k)[k], None, None, "converter model RMS",
            f"HVR_FULL_OPT_EPC_V2 closed form at its tier's in-cell temperature "
            f"({t_k:.2f} C)", layer, "CONSERVATION_VERIFICATION", "CLOSED")

    iv = intra_vr(t_conv, scen, arch)
    add("P_intraVR_metal", "cell traces (R0) + output plane (R2)", "mixed",
        iv["P_intraVR_metal"], None, None, "converter-model RMS; HV nets per scenario",
        "R0 width rule + R2 refined FV sheet", ",".join(lay["rdl"]),
        "MODEL_CONSISTENCY", "SCENARIO" if scen != "HV_S0" else "CLOSED")
    add("P_intraVR_vertical", "cell via stacks", "mixed", iv["P_intraVR_vertical"],
        None, None, "converter-model RMS", "R0 via stack, footprint-filling policy",
        ",".join(lay["rdl"]), "CLOSED_FORM_VERIFICATION", "CLOSED")

    if HV_FEED[arch] == "BGA_FED":
        # the package-level 48 V network: BGA balls + package 48 V RDL sheet (Z1, and the
        # Z2_BGA_FED_CONTROL). A direct-fed architecture has no such network.
        pn = package_network()
        nk = NETWORK_KEY[arch]
        loop = pn["loop"][nk]
        kt_bga = rho_ratio_cu(t_bga)
        from interconnect import rho_solder
        kt_sol = rho_solder(t_bga) / rho_solder(20.0)
        for rail in ("supply", "return"):
            r20 = loop[f"r_{rail}_ohm"]
            add(f"P_pkg_RDL_HV_{rail}", f"package HV RDL {rail} sheet", "48V",
                i_hv_rms ** 2 * r20 * kt_bga, r20 * kt_bga, i_hv_rms, f"HV RMS, {scen}",
                "voltage-fed refined FV sheet, N=%d/rail" % loop["n_per_rail"],
                lay["pkg_hv"], "MESH_CONVERGENCE",
                "SCENARIO" if scen != "HV_S0" else "CLOSED")
            f = np.asarray(pn["convergence"][f"{nk}_{rail}"]["i_ball_frac"])
            r_ball = PAD.bga_ball_resistance_ohm(20.0) * kt_sol
            add(f"P_BGA_{rail}", f"BGA {rail} balls (N=%d)" % len(f), "48V",
                r_ball * i_hv_rms ** 2 * float(np.sum(f ** 2)),
                r_ball / max(1e-30, 1.0 / float(np.sum(f ** 2))), i_hv_rms,
                f"HV RMS, {scen}, solved per-ball split", "Table III rho_solder h / A",
                lay["bga"], "SOURCE_REPRODUCTION",
                "SCENARIO" if scen != "HV_S0" else "CLOSED")

    if arch == "Z3":
        # Z3: VR-to-PCB attach, PCB plated through-holes, 1 V BGA (z3_rows); the TSV field,
        # top RDL and pads below are Z2's
        z3_rows(add, lay, temps, t_sub, t_bga, i_cell_rms)
    elif "attach" in lay:
        # the explicit VR-to-substrate attach: Cu pillar + solder cap per bump, one
        # VDD/GND checkerboard over each cell, carrying only the 1 V output current
        t_att = temps.get("attach", t_sub)
        sp_att = attach_spec()
        for rail, (r_rc, n_b, r_b) in vr_attach_rails(t_att, sp_att).items():
            add(f"P_VR_attach_{rail}", f"VR attach {rail}: {n_b} Cu-pillar bumps/cell",
                "1V", N_VR * i_cell_rms ** 2 * r_rc, r_rc / N_VR, i_cell_rms,
                "cell output RMS", "(rho_Cu h_Cu + rho_solder h_cap) / A per bump, "
                "n in parallel" + (" + two-sided constriction (real lattice)"
                                   if "n_vdd" in sp_att else ""),
                lay["attach"], "GEOMETRY_CLOSE_ANALOG", "BOUNDED",
                ("d %g um / pitch %g um, %s; R_bump = %.4g mOhm at %.1f C"
                 % (sp_att["d_um"], sp_att["pitch_um"], sp_att["model"], r_b * 1e3, t_att))
                if "n_vdd" in sp_att else
                ("Au et al. ECTC 2016 geometry (CLOSE_ANALOG); R_bump = %.4g mOhm at %.1f C"
                 % (r_b * 1e3, t_att)))

    # Z3's TSV field is Z2's, but its cells and substrate come from Z3's own config
    cfg = (z3_spec()["cfg"] if arch == "Z3" else
           PPK.load_physical_package_config(R / "configs/phase0nt/z2_2p4mm_cutout.yaml"))
    h_tsv = cfg.substrate_mm if arch == "Z3" else 0.300
    if arch == "Z1":
        rep = TF.system_report(cfg.cells, cfg.cell_side_mm, 0.300,
                               i_hv_rms, T_C=t_sub)
        rail_v, cur = "48V", f"HV RMS, {scen}"
    else:
        rep = TF.system_report(cfg.cells, cfg.cell_side_mm, h_tsv,
                               i_cell_rms * N_VR, T_C=t_sub)
        rail_v, cur = "1V", "cell output RMS"
    for rail, key in (("VDD", "p_vdd_total_w"), ("GND", "p_gnd_total_w")):
        pc = rep["per_cell"]
        r_cell = pc[f"r_{rail.lower()}_ohm"] + pc[f"r_spread_{rail.lower()}_ohm"]
        add(f"P_TSV_{rail}", f"TSV field {rail}, {pc[f'n_{rail.lower()}']}/cell, "
            f"incl. two-end spreading", rail_v, rep[key], r_cell / N_VR,
            pc["i_cell_a"] * N_VR, cur, "rho L/A per via + compact spreading",
            lay["tsv"], "INDEPENDENT_NUMERICAL_VALIDATION",
            "CLOSED" if (arch in ("Z2", "Z3") or scen == "HV_S0") else "SCENARIO")

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
    check_direct_feed(arch, rows)
    total = sum(r["P_w"] for r in rows)
    out = {"rows": rows, "P_loss_w": total, "intra_vr_nets": iv["nets"],
           "n_pad": n_pad, "i_hv_avg_a": i_hv_avg_a, "i_hv_rms_a": i_hv_rms,
           "architecture_variant": VARIANT[arch], "hv_feed": HV_FEED[arch]}
    if HV_FEED[arch] == "DIRECT_FEED":
        # OUTSIDE the package-internal boundary: the external feed is a swept parameter
        # (R_Z2_direct_feed_loop; Z3's own loop to the board backside for Z3), so only its
        # scaling is recorded here
        out["external_feed"] = {"parameter": ("R_Z3_direct_feed_loop" if arch == "Z3" else
                                              "R_Z2_direct_feed_loop"),
                                "i_48_avg_a": i_hv_avg_a, "i_48_rms_a": i_hv_rms,
                                "P_feed_per_mohm_w": i_hv_rms ** 2 * 1e-3,
                                "in_package_internal_total": False}
    if arch == "Z3":
        out["z3_design"] = z3_design(rows, temps, i_cell_rms)
    return out


def check_direct_feed(arch, rows):
    """A direct-fed architecture's 48 V never enters the package: refuse any package 48 V
    BGA or RDL term in its ledger (Z2_DIRECT_FEED_ARCHITECTURE.md section 2)."""
    if HV_FEED.get(arch) != "DIRECT_FEED":
        return
    bad = sorted({r["term"] for r in rows if r["term"] in FORBIDDEN_DIRECT_FEED_TERMS})
    if bad:
        raise RuntimeError(f"{VARIANT[arch]} acquired package 48 V terms {bad}: its 48 V "
                           "never enters the package")


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
