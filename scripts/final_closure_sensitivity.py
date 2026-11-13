"""Class-B sensitivities on the production lineage (headline scenario, production mesh).

Each variant changes ONE declared input of the physical Z1/Z2 packages and runs the same
E-T fixed point, thermoelastic solve and all-site joint search as the production cases.
Results go to research/final_closure/sensitivity/etm_{ARCH}_{SCEN}__{VARIANT}.json; the
production case files are never touched, and the production path is unchanged (the hooks
in final_closure_physical_etm are empty unless a variant sets them in its own process).

Two kinds:
  full   electrical-thermal fixed point + mechanics, because the variant changes heat
         paths or losses
  mech   mechanics only, on the CONVERGED production temperature field, because the
         variant changes only stiffness and expansion (asserted: the field's peak must
         equal the production case's to 1e-6 K)

Variants that are bounding stress tests, not property claims, say so in `nature`.

    python final_closure_sensitivity.py [VARIANT[:ARCH] ...]     (default: all)
"""
from __future__ import annotations

import copy
import json
import multiprocessing as mp
import os
import sys
import time
from dataclasses import replace
from pathlib import Path

# Every pool worker would otherwise start a full-width OpenBLAS pool (64-96 idle threads);
# on this shared host that reached the per-user thread limit and killed CalculiX
# runs mid-solve (DEFECT #69). The solvers set their own thread counts.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np  # noqa: E402

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import final_closure_physical_etm as E                              # noqa: E402
from hvr_scratch import path as scratch                             # noqa: E402

OUT = R / "research" / "final_closure" / "sensitivity"
SCEN = "HV_S0"
#: converged production temperature fields kept outside the repo (scratch), see README
FIELDS = Path(os.environ.get("HVR_FIELDS", Path.home() / "claude_scratch" / "hvr_work"
                             / "fields"))
HOMOG = R / "research" / "phase0nv" / "pcb_homogenization.json"
CONV_TIERS = ("flying_caps", "inductor_plus_cout")


# ------------------------------------------------------------------ board variants
def eta_material(eta):
    """The IT-968G board card at copper coverage eta, by the SAME rule that derives the
    production card (research/phase0nv nominal_tensor: in-plane E and CTE of the sweep
    row, midpoint of each bounded conductivity bracket). At eta = 0.5 it must reproduce
    the production card exactly -- checked in board_case_check()."""
    h = json.loads(HOMOG.read_text())
    row = next(r for r in h["sweep"] if abs(r["eta"] - eta) < 1e-12)
    mid = lambda b: 0.5 * (b[0] + b[1])
    return {"E_MPa": row["Ex_MPa"], "nu": h["nominal_tensor"]["nu"],
            "cte": row["cte_x"] * 1e-6, "k": mid(row["k_z_bounds"]),
            "k_ortho": [mid(row["k_xy_bounds"]), mid(row["k_xy_bounds"]),
                        mid(row["k_z_bounds"])]}


def board_case_check():
    import board as BRD
    prod = {k: v for k, v in BRD.BOARD_CASES["it968g_2p4mm"].items() if k != "t_mm"}
    mine = eta_material(0.5)
    for k, v in prod.items():
        a, b = np.atleast_1d(v), np.atleast_1d(mine[k])
        if not np.allclose(a, b, rtol=1e-12, atol=0.0):
            raise RuntimeError(f"eta rule does not reproduce the production board: {k}")


def v_board_thickness(case, t_um):
    import physical_package as PP
    z1o, z2o = PP.load_z1_package_config, PP.load_physical_package_config
    PP.load_z1_package_config = lambda path=None: replace(
        z1o(path), board_case=case, board_thickness_um=t_um)
    PP.load_physical_package_config = lambda path: replace(
        z2o(path), board_case=case, board_thickness_um=t_um)


def v_board_eta(eta):
    import board as BRD
    board_case_check()
    t = BRD.BOARD_CASES["it968g_2p4mm"]["t_mm"]
    BRD.BOARD_CASES["it968g_2p4mm"] = dict(eta_material(eta), t_mm=t)


def v_board_h1(h0_material=False):
    """PCB-H1: the 18-layer schedule as five depth blocks (scripts/phase0nw/pcb_h1.py),
    each its own material. The blocks keep the layer NAME 'board' so the cutout, the
    board-bottom film and the 3-2-1 restraint treat them exactly as the H0 slab.
    h0_material=True is the CONTROL: the H0 card on the same five-block z grid, so the
    H0 -> H1 difference separates material representation from z discretisation."""
    import board as BRD
    import pcb_h1 as H1
    t = BRD.BOARD_CASES["it968g_2p4mm"]["t_mm"]
    lo, so = BRD.bottom_layers, BRD.stack_with_board

    def bottom_layers(case="fr4_1p6mm", nz_board=2, nz_bga=2):
        base = lo(case, nz_board, nz_bga)
        if case != "it968g_2p4mm" or base[0][0] != "board":
            raise RuntimeError(f"H1 variant applied to an unexpected board stack {base}")
        blocks = [("board", b[1], "board_fr4" if h0_material else b[2], b[3])
                  for b in H1.bottom_layers(t, 0.50, nz=1)]
        if abs(sum(b[1] for b in blocks) - base[0][1]) > 1e-12:
            raise RuntimeError("H1 blocks do not add up to the board thickness")
        return blocks + base[1:]

    def stack_with_board(stack, t_tile_mm, case="fr4_1p6mm"):
        st = so(stack, t_tile_mm, case)
        if not h0_material:
            st["materials"].update(H1.board_materials(t, 0.50))
        return st
    BRD.bottom_layers, BRD.stack_with_board = bottom_layers, stack_with_board


# ------------------------------------------------------------------ TSV density
def v_tsv(n_side):
    """The same field change in the FE substrate AND in the electrical ledger: an
    n_side x n_side checkerboard at the largest pitch that fits (tsv_fields.lattice_for_n,
    the sizing study's own lattice)."""
    import tsv_fields as TF
    E.TSV_N_PER_CELL = n_side * n_side
    orig = TF.system_report

    def system_report(cells, cell_side_mm, h_tsv_mm, i_total_a, n_per_cell=None, **kw):
        pitch, _nv, _ng = TF.lattice_for_n(cell_side_mm, n_side)
        r = orig(cells, cell_side_mm, h_tsv_mm, i_total_a,
                 pitch_mm=pitch * (1.0 - 1e-12), **kw)
        if r["per_cell"]["n_total"] != n_side * n_side:
            raise RuntimeError(f"lattice gave {r['per_cell']['n_total']} vias, "
                               f"not {n_side * n_side}")
        return r
    TF.system_report = system_report


# ------------------------------------------------------------------ fill, cooling
def v_out_of_cell(case):
    import physical_package as PP
    o1, o2 = PP.build_physical_z1, PP.build_physical_package
    PP.build_physical_z1 = lambda cfg=None, h_xy=1.1, out_of_cell=None: o1(cfg, h_xy, case)
    PP.build_physical_package = (lambda cfg, h_xy=1.1, discrete_cells=True,
                                 out_of_cell=None: o2(cfg, h_xy, discrete_cells, case))


def v_f1_sidewall_filled():
    """The DEFECT #66 construction as a SENSITIVITY: the encapsulant fills the WHOLE PCB
    opening, including the 1.0 mm clearance ring, bonding the converter block to the PCB
    sidewall. Production voids that ring (F1_clearance). Z2 only: Z1 has no opening."""
    v_out_of_cell("F1_encapsulated")


# ------------------------------------------------------------------ VR attach (Z2)
def _attach_override(**kw):
    """Change the VR attach in the mesh (config) AND in the electrical ledger together."""
    import physical_package as PP
    import final_closure_ledger as FL
    o = PP.load_physical_package_config
    def load(path):
        cfg = o(path)
        att = dict(cfg.attach)
        att.update(kw)
        h = float(att["cu_height_um"]) + float(att["cap_height_um"])
        return replace(cfg, attach=tuple(sorted(att.items())), attach_um=h)
    PP.load_physical_package_config = load
    sp = dict(FL.attach_spec())
    sp.update({{"cu_height_um": "h_cu_um", "cap_height_um": "h_cap_um", "diameter_um": "d_um",
                "pitch_um": "pitch_um"}[k]: v for k, v in kw.items()})
    FL.attach_spec = lambda: sp


def v_attach_height(h_um):
    """Joint height bound (20 / 40 um) with the Cu/cap proportions of the nominal 14/16 um
    split, so only the height (and with it the series resistance) changes."""
    _attach_override(cu_height_um=14.0 * h_um / 30.0, cap_height_um=16.0 * h_um / 30.0)


def v_attach_sn():
    """All-solder BOUND at the Na et al. density (30 um diameter, 50 um space, i.e. 80 um
    pitch) in the same 30 um envelope. Na et al. report a pure-Sn cap on a Cu post/Ni
    barrier; the all-Sn column is that construction's resistive upper bound (its post/cap
    split is not in the accessible text). Material AND density change together, so this is
    NOT the density sensitivity (geom.vr_attach_density holds the material)."""
    _attach_override(cu_height_um=0.0, cap_height_um=30.0, diameter_um=30.0, pitch_um=80.0)


def _attach_card(edit):
    def hook(m, st, tiles):
        c = st["materials"]["vr_attach"]
        edit(c)
        c["status"] = "ASSUMPTION"
        c["note"] = "class-B bound (final_closure_sensitivity.py), not a property"
        return {"vr_attach_card": {k: c[k]["value"] for k in ("E", "cte", "k")}}
    E.BUILD_HOOKS.append(hook)


def v_attach_stiff():
    """Column-stiffened (Voigt) mechanical card of the attach instead of the
    underfill-dominated production convention."""
    import z2_converter as Z2C
    def edit(c):
        att = {"cu_height_um": 14.0, "cap_height_um": 16.0, "diameter_um": 15.0,
               "pitch_um": 30.0}
        st = Z2C.vr_attach_material(att, column_stiffened=True)
        c["E"], c["cte"] = st["E"], st["cte"]
    _attach_card(edit)


def v_attach_density(name, stiff=False):
    """geom.vr_attach_density: the attach of final_closure_vr_attach.CASES[name] in the
    mesh (its REAL lattice metal fraction in the homogenised card) and in the ledger (real
    VDD/GND counts, series column + two-sided constriction). Heights and material stay at
    production, so the z grid is the production grid. stiff=True puts the column-stiffened
    (Voigt, real f) mechanical card on it: the second of the two mechanical bounds."""
    import final_closure_vr_attach as VA
    import physical_package as PP
    import final_closure_ledger as FL
    case = VA.CASES[name]
    att_mesh = VA.mesh_attach(case)
    o = PP.load_physical_package_config

    def load(path):
        cfg = o(path)
        att = dict(cfg.attach)
        att.update(att_mesh)
        h = float(att["cu_height_um"]) + float(att["cap_height_um"])
        return replace(cfg, attach=tuple(sorted(att.items())), attach_um=h)
    PP.load_physical_package_config = load
    sp = dict(FL.attach_spec())
    sp.update(VA.ledger_spec(case))
    FL.attach_spec = lambda: sp
    if stiff:
        def edit(c):
            st = VA.card(case, column_stiffened=True)
            c["E"], c["cte"] = st["E"], st["cte"]
        _attach_card(edit)


def v_attach_underfill(E_mpa, cte):
    """Declared stress corners of the attach underfill (E, CTE), not a sourced range."""
    def edit(c):
        c["E"] = {"value": E_mpa, "status": "ASSUMPTION"}
        c["cte"] = {"value": cte, "status": "ASSUMPTION"}
    _attach_card(edit)


# ------------------------------------------------------------------ direct feed (Z2)
def feed_bound_ohm():
    """The largest external loop resistance any requirement admits: the largest crossover
    R* over the scenarios that have a valid comparison (direct_feed_crossover.json). A
    scenario in which Z2 is not ahead even with a lossless feed (R* = 0) admits none."""
    cx = json.loads((R / "research/final_closure/direct_feed_crossover.json").read_text())
    rs = [c["R_star_mohm"] for c in cx["scenarios"].values()
          if c.get("R_star_mohm") and not c.get("Z1_operating_point_inadmissible")]
    if not rs:
        raise RuntimeError("no scenario admits a positive direct-feed loop resistance")
    return max(rs) * 1e-3


def v_feed_heat():
    """The external direct-feed loss at the largest admissible loop resistance
    (feed_bound_ohm), at the HV-S0 current, deposited INSIDE the package in the deepest
    converter tier (in-cell): the worst place the feed's heat could land."""
    import final_closure_ledger as FL
    r_b = feed_bound_ohm()
    def extra(arch, scen, L):
        if FL.HV_FEED[arch] != "DIRECT_FEED":
            return {}
        p = L["i_hv_rms_a"] ** 2 * r_b
        return {((FL.LAYERS[arch]["hs"],), True): p}
    E.EXTRA_DEPOSITS = extra


# ------------------------------------------------------------------ cooling model form
def icepak_factor():
    """h_eq / h_compact implied by the matched Icepak case: the compact model gives
    dT = q''/h at the CFD's exact loading, so the coefficient that reproduces the CFD's
    mean base rise is h * dT_compact / dT_CFD. A SENSITIVITY, never a recalibration."""
    j = json.loads((R / "research/final_closure/reference_cooling_icepak.json").read_text())
    lv = {k: v for k, v in j["levels"].items() if v.get("solved")}
    fin = max(lv, key=lambda k: lv[k]["cells"])
    return j["correlation_dT_matched_loading_K"] / lv[fin]["dT_base_mean_K"]


def v_icepak_equivalent():
    from cooling_production import CANDIDATES
    c = CANDIDATES[E.COOLER]
    f = icepak_factor()
    orig = type(c).h_uniform
    type(c).h_uniform = lambda self, q_w: orig(self, q_w) * f
def v_board_hbot(h_w_m2k):
    """Board thermal boundary (TCPMT revision). The production board is a 30 x 30 mm coupon
    with adiabatic sides and h_bottom = 10 W/m2K (natural convection), so heat can leave
    almost only through the top cold plate and the whole Z1 board settles near the joint
    temperature (114-122 C). An effective bottom coefficient stands for the lateral
    spreading of a full server board and its forced-air cooling (a fin of k_xy = 66 W/mK,
    t = 2.4 mm gives 60-520 W/m2K referred to the coupon footprint for h_air = 10-100)."""
    def hook(m, st, tiles):
        st["thermal_bc"]["h_bottom"]["value"] = float(h_w_m2k)
        return {"h_bottom_W_m2K": float(h_w_m2k)}
    E.BUILD_HOOKS.append(hook)


def v_z2_cooled():
    """Z2-COOLED, bounding: a second cold plate of the SAME kind as the top one (uniform
    h of the top microchannel plate at the dissipated power, fluid at the inlet
    temperature) on the whole converter underside inside the PCB opening. The strongest
    backside cooling this model can state without inventing a new cooler."""
    from cooling_production import CANDIDATES
    cooler = CANDIDATES[E.COOLER]

    def film(m, tiles, q_w):
        inside = [L for L in m.layers if L.region == "inside_cutout"]
        deepest = min(inside, key=lambda L: L.z0)
        ids = m.elem_set(layer=deepest.name)
        keep = [e for e in ids
                if abs(m.nodes[m.elems[e - 1] - 1][:, 2].min() - deepest.z0) < 1e-9]
        return {"elems": np.array(keep, int), "h_W_m2K": float(cooler.h_uniform(q_w)),
                "T_C": float(cooler.t_in_c), "layer": deepest.name,
                "label": "second top-type cold plate on the converter underside"}
    E.EXTRA_FILM = film


def v_z2_cooled_tim():
    """Backside thermal interface: the Z2-COOLED plate, but through the stack's TIM card
    (50 um at k = 3 W/mK, the top TIM) in series with the film."""
    from cooling_production import CANDIDATES
    cooler = CANDIDATES[E.COOLER]

    def film(m, tiles, q_w):
        inside = [L for L in m.layers if L.region == "inside_cutout"]
        deepest = min(inside, key=lambda L: L.z0)
        ids = m.elem_set(layer=deepest.name)
        keep = [e for e in ids
                if abs(m.nodes[m.elems[e - 1] - 1][:, 2].min() - deepest.z0) < 1e-9]
        h = float(cooler.h_uniform(q_w))
        r_tim = 50e-6 / 3.0
        return {"elems": np.array(keep, int), "h_W_m2K": 1.0 / (1.0 / h + r_tim),
                "T_C": float(cooler.t_in_c), "layer": deepest.name,
                "label": "second cold plate on the converter underside through a 50 um TIM"}
    E.EXTRA_FILM = film


def v_bga_population(frac):
    """BGA mechanical population: the homogenised BGA layer at a smaller populated
    fraction (its stiffness and conductivity scale with the ball area fraction). For the
    direct-fed Z2 the 54 + 54 balls the BGA-fed design used for 48 V are electrically
    unnecessary; frac = 420/528 depopulates them. Uniform smearing is a simplification."""
    def hook(m, st, tiles):
        c = st["materials"]["bga_homog"]
        for key in ("E", "k"):
            v = c[key]["value"] if isinstance(c[key], dict) else c[key]
            c[key] = {"value": v * frac, "status": "ASSUMPTION"}
        c["note"] = f"class-B population {frac:.4f} of the sites"
        return {"bga_population": frac}
    E.BUILD_HOOKS.append(hook)


# ------------------------------------------------------------------ pad count
def v_pad_drop():
    """The 1 V source-pad field at its voltage-drop FLOOR (pad_interface.size_for_cell
    PAD_DROP: the fewest pads per rail per cell that meet the drop budget) instead of the
    production SOURCE_ANCHORED count. Both architectures carry the same pad field and
    current, so the electrical change is common-mode; this run shows what the extra
    interface heat does to temperatures and mechanics. A range END, not a design: the
    floor puts several MA/cm^2 through each pad."""
    import final_closure_ledger as FL
    import pad_interface as PAD
    import rms_currents as RMS
    n = PAD.size_for_cell(RMS.cell_currents()["i_cell_out_rms_a"])["PAD_DROP"]["n_per_rail"]
    orig = FL.pad_count
    FL.PAD_CASES["PAD_DROP"] = "voltage-drop floor of the pad sweep (range end, not a design)"
    FL.pad_count = lambda case: n if case == "PAD_DROP" else orig(case)
    FL.ledger.__defaults__ = ("PAD_DROP",)          # the ledger's pad_case default


# ------------------------------------------------------------------ tier materials
def _retag(m, st, new, base, card_edit, layer_has, base_mat):
    card = copy.deepcopy(st["materials"][base])
    card_edit(card)
    card["status"] = "ASSUMPTION"
    card["note"] = "class-B sensitivity bound (final_closure_sensitivity.py), not a property"
    st["materials"][new] = card
    mat = np.array(m.elem_material, dtype=object)
    lay = np.array(m.elem_layer, dtype=object)
    sel = np.array([any(t in str(l) for t in layer_has) for l in lay]) & (mat == base_mat)
    mat[sel] = new
    m.elem_material = mat
    return int(sel.sum())


def v_gan_k_half():
    """GaN epi bound: the two device tiers are meshed as their Si carrier. Halving the
    tier conductivity adds t_tier/k_Si of through-thickness resistance (4.9e-6 and
    5.3e-6 m^2K/W for the 638 and 685 um tiers at 130 W/mK) -- more than any epi stack
    with t_epi/k_epi below that can add, e.g. 10 um at k > 2.1 W/mK. A stress bound,
    not a GaN property."""
    def hook(m, st, tiles):
        def edit(c):
            c["k"] = {"value": st["materials"]["silicon"]["k"]["value"] / 2.0,
                      "status": "ASSUMPTION"}
        n = _retag(m, st, "gan_tier_bound", "silicon", edit, ("gan_",), "silicon")
        return {"variant_elements_retagged": n}
    E.BUILD_HOOKS.append(hook)


def v_conv_k(factor):
    """Converter-medium conductivity bound: the flying-cap and inductor/Cout tiers carry
    the generic hvr_effective card (k 60 W/mK, PROVISIONAL, no sourced MLCC/ferrite
    card in the framework). Reducing it tenfold is a declared stress test."""
    def hook(m, st, tiles):
        def edit(c):
            c["k"] = {"value": st["materials"]["hvr_effective"]["k"]["value"] * factor,
                      "status": "ASSUMPTION"}
        n = _retag(m, st, "hvr_effective_k_bound", "hvr_effective", edit, CONV_TIERS,
                   "hvr_effective")
        return {"variant_elements_retagged": n}
    E.BUILD_HOOKS.append(hook)


def v_conv_mech(E_mpa, cte):
    """A corner of the converter medium's OWN declared range (package_stack.yaml:
    'Sensitivity E = 80-160 GPa, CTE 4-10 ppm/K'). Conductivity unchanged."""
    def hook(m, st, tiles):
        def edit(c):
            c["E"] = {"value": E_mpa, "status": "ASSUMPTION"}
            c["cte"] = {"value": cte, "status": "ASSUMPTION"}
        n = _retag(m, st, "hvr_effective_corner", "hvr_effective", edit, CONV_TIERS,
                   "hvr_effective")
        return {"variant_elements_retagged": n}
    E.BUILD_HOOKS.append(hook)


VARIANTS = {
    "board_t3p2": dict(kind="full", archs=("Z1", "Z2"), apply=lambda: v_board_thickness(
        "it968g_3p2mm", 3200.0), gates=["board.t_only_comparison_run",
                                        "mech.t_only_mechanical"],
        nature="declared case (config thickness_sensitivity_case)",
        what="PCB 3.2 mm instead of 2.4 mm, same IT-968G material dict"),
    "board_eta025": dict(kind="full", archs=("Z1", "Z2"), apply=lambda: v_board_eta(0.25),
                         gates=["board.eta_sensitivity_run"],
                         nature="declared range (config eta_sensitivity)",
                         what="board copper coverage eta = 0.25 instead of 0.50"),
    "board_eta075": dict(kind="full", archs=("Z1", "Z2"), apply=lambda: v_board_eta(0.75),
                         gates=["board.eta_sensitivity_run"],
                         nature="declared range (config eta_sensitivity)",
                         what="board copper coverage eta = 0.75 instead of 0.50"),
    "board_h1": dict(kind="full", archs=("Z1", "Z2"), apply=lambda: v_board_h1(False),
                     gates=["board.h1_meshed", "board.h1_thermal_validated",
                            "therm.h0_h1_compared"],
                     nature="model-form check of the homogenised board",
                     what="PCB-H1: five depth blocks with their own copper fractions"),
    "board_h0_h1grid": dict(kind="full", archs=("Z1", "Z2"),
                            apply=lambda: v_board_h1(True),
                            gates=["board.h1_meshed", "therm.h0_h1_compared"],
                            nature="control for board_h1",
                            what="the H0 card on the H1 five-block z grid"),
    "tsv_min": dict(kind="full", archs=("Z1", "Z2"), apply=lambda: v_tsv(8),
                    gates=["tsv.density_sensitivity_run"],
                    nature="declared range (TSV sizing study: electrical minimum)",
                    what="64 vias/cell (8 x 8) instead of 1444, FE substrate and ledger"),
    "tsv_mid": dict(kind="full", archs=("Z1", "Z2"), apply=lambda: v_tsv(27),
                    gates=["tsv.density_sensitivity_run"],
                    nature="declared range (TSV sizing study: mid)",
                    what="729 vias/cell (27 x 27) instead of 1444, FE substrate and ledger"),
    "f2_void": dict(kind="full", archs=("Z1", "Z2"), apply=lambda: v_out_of_cell("F2_void"),
                    gates=["mech.f1_f2_bracket_run"],
                    nature="declared bracket (z2_converter.OUT_OF_CELL)",
                    what="out-of-cell converter-tier volume void instead of encapsulated"),
    "f1_sidewall_filled": dict(kind="full", archs=("Z2",), apply=v_f1_sidewall_filled,
                               gates=["mech.f1_f2_bracket_run", "geom.sidewall_clearance"],
                               nature="the DEFECT #66 construction, kept as a sensitivity",
                               what="encapsulant fills the whole opening, bonding the converter "
                                    "to the PCB sidewall (production: 1.0 mm clearance void)"),
    "attach_h20": dict(kind="full", archs=("Z2",), apply=lambda: v_attach_height(20.0),
                       gates=["geom.vr_attach_height"], nature="declared bound (architecture spec)",
                       what="VR attach joint 20 um instead of 30 um"),
    "attach_h40": dict(kind="full", archs=("Z2",), apply=lambda: v_attach_height(40.0),
                       gates=["geom.vr_attach_height"],
                       nature="declared bound (Na et al. 2022, CLOSE_ANALOG)",
                       what="VR attach joint 40 um instead of 30 um; the z grid loses one "
                            "10 um sliver plane (at 40 um the inductor-tier midplane meets "
                            "the BGA bottom at z = -0.30 mm), a discretisation change of "
                            "the size the through-thickness mesh check bounds"),
    "attach_sn": dict(kind="full", archs=("Z2",), apply=v_attach_sn,
                      gates=["mat.vr_attach_material"],
                      nature="all-solder resistive bound at the Na et al. 2023 density "
                             "(CLOSE_ANALOG)",
                      what="an all-solder (pure Sn) column, 30 um at 80 um pitch, instead of "
                           "15 um Cu pillars at 30 um pitch (material and density together)"),
    "attach_dense": dict(kind="full", archs=("Z2",), apply=lambda: v_attach_density("dense"),
                         gates=["geom.vr_attach_density"],
                         nature="published geometry (Au et al. ECTC 2016, CLOSE_ANALOG)",
                         what="15 um pillars at 30 um pitch (production geometry) on the real "
                              "lattice with the two-sided constriction: the dense endpoint"),
    "attach_sparse": dict(kind="full", archs=("Z2",), apply=lambda: v_attach_density("sparse"),
                          gates=["geom.vr_attach_density"],
                          nature="published geometry (Na et al. 2023, CLOSE_ANALOG); "
                                 "production material and height held",
                          what="30 um bumps at 80 um pitch instead of 15 um at 30 um, "
                               "underfill-dominated mechanical card (bound A)"),
    "attach_sparse_stiff": dict(kind="full", archs=("Z2",),
                                apply=lambda: v_attach_density("sparse", stiff=True),
                                gates=["geom.vr_attach_density"],
                                nature="published geometry, column-stiffened mechanical "
                                       "bound (B)",
                                what="the sparse attach with the column-stiffened (Voigt, "
                                     "real metal fraction) card instead of the underfill-"
                                     "dominated one"),
    **{f"attach_eng_p{p:g}": dict(kind="full", archs=("Z2",),
                                  apply=(lambda p=p: v_attach_density(f"eng_p{p:g}")),
                                  gates=[], nature="ENGINEERING_SENSITIVITY (not a published "
                                                   "geometry)",
                                  what=f"15 um pillars at {p:g} um pitch, between the "
                                       "published endpoints, to locate a crossover")
       for p in (34.0, 37.0, 41.0)},
    "attach_stiff": dict(kind="mech", archs=("Z2",), apply=v_attach_stiff,
                         gates=["mat.vr_attach_material"], nature="bounding model form",
                         what="column-stiffened (Voigt) attach card instead of the "
                              "underfill-dominated convention"),
    "attach_uf_soft": dict(kind="mech", archs=("Z2",),
                           apply=lambda: v_attach_underfill(4000.0, 40e-6),
                           gates=["mat.vr_attach_underfill"], nature="declared stress corner",
                           what="attach underfill E = 4 GPa, CTE = 40 ppm/K"),
    "attach_uf_stiff": dict(kind="mech", archs=("Z2",),
                            apply=lambda: v_attach_underfill(12000.0, 20e-6),
                            gates=["mat.vr_attach_underfill"], nature="declared stress corner",
                            what="attach underfill E = 12 GPa, CTE = 20 ppm/K"),
    "feed_heat_at_crossover": dict(kind="full", archs=("Z2",), apply=v_feed_heat,
                                   gates=["elec.direct_feed_heat_location"],
                                   nature="bounding heat location (worst place)",
                                   what="the external feed loss at the largest admissible "
                                        "loop resistance (largest crossover R* over the "
                                        "scenarios with a valid comparison), at the HV-S0 "
                                        "current, deposited in the deepest converter tier"),
    "icepak_equivalent": dict(kind="full", archs=("Z1", "Z2"), apply=v_icepak_equivalent,
                              gates=["therm.cooling_model_form"],
                              nature="ICEPAK_EQUIVALENT_COOLING_SENSITIVITY (not a "
                                     "recalibration)",
                              what="top-plate coefficient scaled by dT_compact/dT_CFD of the "
                                   "matched Icepak case"),
    "z2_cooled_tim": dict(kind="full", archs=("Z2",), apply=v_z2_cooled_tim,
                          gates=["therm.backside_interface"],
                          nature="backside thermal interface (bounding cooling)",
                          what="Z2-COOLED plate through a 50 um TIM at k = 3 W/mK"),
    "bga_depop": dict(kind="full", archs=("Z2",), apply=lambda: v_bga_population(420 / 528),
                      gates=["mech.bga_population"],
                      nature="BGA mechanical population (smeared)",
                      what="BGA field populated at 420/528: the 54 + 54 48 V balls of the "
                           "BGA-fed design removed"),
    "board_hbot100": dict(kind="full", archs=("Z1", "Z2"), apply=lambda: v_board_hbot(100.0),
                          gates=[], nature="ENGINEERING_SENSITIVITY (board thermal boundary)",
                          what="effective board-bottom coefficient 100 W/m2K instead of 10 "
                               "(full server board, forced air)"),
    "board_hbot500": dict(kind="full", archs=("Z1", "Z2"), apply=lambda: v_board_hbot(500.0),
                          gates=[], nature="ENGINEERING_SENSITIVITY (board thermal boundary)",
                          what="effective board-bottom coefficient 500 W/m2K instead of 10 "
                               "(upper end of board spreading)"),
    "z2_cooled": dict(kind="full", archs=("Z2",), apply=v_z2_cooled,
                      gates=["therm.z2_cooled"],
                      nature="bounding case (strongest backside cooling the model states)",
                      what="top-type cold plate on the Z2 converter underside"),
    "pad_drop": dict(kind="full", archs=("Z1", "Z2"), apply=v_pad_drop,
                     gates=["elec.pad_count_criterion", "elec.pad_loss_closed"],
                     nature="declared range end (pad sweep: voltage-drop floor)",
                     what="1 V source pads at the drop floor (4 per rail per cell) "
                          "instead of 2040"),
    "gan_k_half": dict(kind="full", archs=("Z1", "Z2"), apply=v_gan_k_half,
                       gates=["mat.gan_bounded"], nature="bounding stress test",
                       what="GaN device tiers at half the Si carrier conductivity"),
    "conv_k_tenth": dict(kind="full", archs=("Z1", "Z2"), apply=lambda: v_conv_k(0.1),
                         gates=["mat.mlcc_bounded", "mat.inductor_tier_bounded"],
                         nature="bounding stress test",
                         what="flying-cap and inductor/Cout tiers at k = 6 W/mK"),
}
for _E in (80e3, 160e3):
    for _a in (4e-6, 10e-6):
        VARIANTS[f"conv_E{_E / 1e3:.0f}_a{_a * 1e6:.0f}"] = dict(
            kind="mech", archs=("Z1", "Z2"),
            apply=(lambda E_=_E, a_=_a: v_conv_mech(E_, a_)),
            gates=["mat.mlcc_bounded", "mat.inductor_tier_bounded"],
            nature="declared range (package_stack.yaml hvr_effective)",
            what=f"converter medium E = {_E / 1e3:.0f} GPa, CTE = {_a * 1e6:.0f} ppm/K")


def case_file(arch, variant, scen=SCEN):
    return OUT / f"etm_{arch}_{scen}__{variant}.json"


def _spec(variant):
    v = VARIANTS[variant]
    return {"name": variant, "kind": v["kind"], "gates": v["gates"],
            "nature": v["nature"], "what": v["what"]}


def run_full(arch, variant):
    E.WD = scratch("fc_sens", variant)
    VARIANTS[variant]["apply"]()
    E._raise_stack_limit()
    h, r = E.PRODUCTION_H_XY, E.PRODUCTION_REFINE
    m, mats, st, tiles, minfo, L, th, hist, t_et, wd = E.run_et(arch, SCEN, h, r)
    res = {"arch": arch, "scenario": SCEN, "h_xy_mm": h, "refine": list(r),
           "variant": _spec(variant), "materials": minfo,
           "ledger_rows": L["rows"], "P_loss_w": L["P_loss_w"],
           "i_hv_avg_a": L["i_hv_avg_a"], "energy_ledger": L["energy"],
           "thermal": {k: v for k, v in th.items() if k != "T_node"},
           "et_history": hist,
           "et_converged": (hist[-1]["max_dT_K"] < E.ET_TOL_K
                            and hist[-1]["dP_rel"] < E.ET_TOL_P_REL),
           "et_wall_s": t_et, "threads": E.THREADS,
           "production_case": E.case_path(arch, SCEN).name}
    f = case_file(arch, variant)
    f.write_text(json.dumps(res, indent=1, default=float))
    try:
        res["mechanics"] = E.mechanics(m, mats, st, th["T_node"], wd, arch, tiles,
                                       E.PRODUCTION_SOLVER, 1)
    except Exception as e:                        # recorded, never silently dropped
        res["mechanics_error"] = str(e)[-600:]
    f.write_text(json.dumps(res, indent=1, default=float))
    return f.name, "mechanics" in res


def run_mech(arch, variant):
    import production_et as PE
    VARIANTS[variant]["apply"]()
    E._raise_stack_limit()
    base = json.loads(E.case_path(arch, SCEN).read_text())
    m, mats, st, tiles, minfo = E.build(arch, E.PRODUCTION_H_XY, E.PRODUCTION_REFINE)
    frd = FIELDS / f"etm_{arch}_{SCEN}_r21" / "thermal_converged.frd"
    tn = PE.ccxio.read_frd(frd)["NDTEMP"][1:m.n_nodes + 1, 0]
    if abs(float(np.nanmax(tn)) - base["thermal"]["T_max_C"]) > 1e-6:
        raise RuntimeError(f"{frd} is not the converged field of {base['arch']}")
    res = {k: base[k] for k in ("arch", "scenario", "h_xy_mm", "refine", "ledger_rows",
                                "P_loss_w", "i_hv_avg_a", "energy_ledger", "thermal",
                                "et_history", "et_converged", "et_wall_s")}
    res.update({"variant": _spec(variant), "materials": minfo,
                "thermal_from": "production converged field (mechanics-only variant)",
                "production_case": E.case_path(arch, SCEN).name})
    try:
        res["mechanics"] = E.mechanics(m, mats, st, tn, scratch("fc_sens", variant, arch),
                                       arch, tiles, E.PRODUCTION_SOLVER, 1)
    except Exception as e:
        res["mechanics_error"] = str(e)[-600:]
    f = case_file(arch, variant)
    f.write_text(json.dumps(res, indent=1, default=float))
    return f.name, "mechanics" in res


def _task(t):
    arch, variant = t
    t0 = time.time()
    try:
        fn = run_full if VARIANTS[variant]["kind"] == "full" else run_mech
        name, ok = fn(arch, variant)
        return {"arch": arch, "variant": variant, "file": name, "mechanics_ok": ok,
                "wall_s": time.time() - t0}
    except Exception as e:                        # a crash is a recorded result
        return {"arch": arch, "variant": variant, "error": str(e)[-600:],
                "wall_s": time.time() - t0}


def _local_task(t):
    """The local response at a variant's own critical joint, at the SAME level and
    settings as the production pass-3 L0 solve (block-order extraction, split load step,
    the temporal study's first increment), so variant and production differ only in the
    joint's du and temperature."""
    arch, variant = t
    import final_closure_local_mesh as LM
    c = json.loads(case_file(arch, variant).read_text())
    crit = c["mechanics"]["joint_search"]["critical"]
    inc0 = json.loads(LM.TIME_STUDY.read_text())["production_dt0_s"]
    r = LM._solve(f"{arch}_{variant}", crit["du_um"], crit["T_C"],
                  scratch("fc_sens_local", variant, arch), "L0", inc0, True)
    return arch, variant, r


def _needs_local(a, v):
    if not case_file(a, v).exists():
        return False
    c = json.loads(case_file(a, v).read_text())
    if "mechanics" not in c:
        return False
    crit, loc = c["mechanics"]["joint_search"]["critical"], c.get("local") or {}
    return not (loc.get("d_peeq_per_cycle") and loc.get("du_um") == crit["du_um"]
                and loc.get("T_joint_C") == crit["T_C"])


def local_main(names):
    tasks = [(a, v) for v in (names or list(VARIANTS)) for a in VARIANTS[v]["archs"]
             if _needs_local(a, v)]
    if not tasks:
        print("no variant needs a local solve", flush=True)
        return
    with mp.Pool(min(len(tasks), 24)) as p:
        out = p.map(_local_task, tasks, chunksize=1)
    for arch, variant, r in out:
        f = case_file(arch, variant)
        c = json.loads(f.read_text())
        c["local"] = r
        f.write_text(json.dumps(c, indent=1, default=float))
        print(arch, variant, r["d_peeq_per_cycle"], r["error"], flush=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if sys.argv[1:2] == ["--local"]:
        return local_main(sys.argv[2:])
    tasks = []
    for a in (sys.argv[1:] or list(VARIANTS)):
        v, *arch = a.split(":")
        tasks += [(x, v) for x in (arch or VARIANTS[v]["archs"])]
    with mp.Pool(len(tasks)) as p:
        out = p.map(_task, tasks)
    log = OUT / "run_log.json"
    old = json.loads(log.read_text()) if log.exists() else []
    log.write_text(json.dumps(old + out, indent=1, default=float))
    for r in out:
        print(r, flush=True)


if __name__ == "__main__":
    main()
