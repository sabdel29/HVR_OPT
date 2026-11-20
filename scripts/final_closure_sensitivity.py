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

MESH LADDERS (TCPMT round 3). A full variant can also be solved on another rung of the
production nested refinement (r11, r31, r12, ...: E.build(arch, h_xy, refine), the mechanism of
the production ladder), so cooling-B, Z3 land-side and production-state cases get ladders of
their own. The rung is a process setting (set_refine / --refine rXZ); a rung other than the
production mesh writes research/final_closure/sensitivity/ladder/etm_{ARCH}_{SCEN}__{VARIANT}_
{rXZ}.json (variant_file) and solves in its own work tree, never replacing the production case.

    python final_closure_sensitivity.py [--refine rXZ] [VARIANT[:ARCH] ...]   (default: all)
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

OUT = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "final_closure" / "sensitivity"   # campaign hook
SCEN = "HV_S0"

#: converged production temperature fields kept outside the repo (scratch), see README
FIELDS = Path(os.environ.get("HVR_FIELDS", Path.home() / "claude_scratch" / "hvr_work"
                             / "fields"))
HOMOG = R / "research" / "phase0nv" / "pcb_homogenization.json"
CONV_TIERS = ("flying_caps", "inductor_plus_cout")


#: cap on concurrent solver processes (shared host); unset = the previous behaviour
POOL_MAX = int(os.environ.get("FC_POOL_MAX", "10000"))

#: TCPMT round 3: the mesh rung of THIS process's full-variant runs. None = the production
#: mesh (E.PRODUCTION_REFINE); otherwise a nested-refinement rung (rx, rz) of the same h_xy grid
#: (E.build), written under LADDER with the rung in the name (variant_file).
REFINE = None
LADDER = OUT / "ladder"


def parse_refine(tok):
    """'r31' -> (3, 1); None / '' -> None."""
    if not tok:
        return None
    t = str(tok).strip().lower()
    if len(t) != 3 or t[0] != "r" or not t[1:].isdigit() or "0" in t[1:]:
        raise ValueError(f"refinement rung {tok!r} is not rXZ (e.g. r11, r21, r31, r12)")
    return int(t[1]), int(t[2])


def set_refine(refine):
    """Solve this process's full variants on rung `refine` ('r31', (3, 1) or None)."""
    global REFINE
    r = parse_refine(refine) if isinstance(refine, str) or refine is None else tuple(refine)
    REFINE = None if r is None or tuple(r) == tuple(E.PRODUCTION_REFINE) else tuple(r)
    return mesh_level()


def mesh_level():
    """The (rx, rz) rung of this process's variant runs."""
    return tuple(E.PRODUCTION_REFINE) if REFINE is None else tuple(REFINE)


def is_production_level():
    return mesh_level() == tuple(E.PRODUCTION_REFINE)


def rung_tag(refine=None):
    r = mesh_level() if refine is None else tuple(refine)
    return f"r{r[0]}{r[1]}"


def work_name(variant):
    """Work-tree name of a variant run at this process's rung (tcpmt_cases.converged_field
    looks for fc_sens/<case-file suffix>/...)."""
    return variant if is_production_level() else f"{variant}_{rung_tag()}"


def ladder_file(path, refine=None):
    """The rung file of a production-mesh variant case file."""
    p = Path(path)
    r = mesh_level() if refine is None else tuple(refine)
    if r == tuple(E.PRODUCTION_REFINE):
        return p
    return p.parent / "ladder" / f"{p.stem}_{rung_tag(r)}.json"


def variant_file(arch, variant, refine=None):
    """The case file of a variant run at this process's rung (the production name at the
    production mesh); whatever case_file the process uses (a driver may replace it to name
    another scenario) gives the production name."""
    return ladder_file(case_file(arch, variant), refine)


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
        if base[0][0] != "board":
            raise RuntimeError(f"H1 variant applied to an unexpected board stack {base}")
        tb = float(base[0][1])           # the board in force (2.4-mm IT968G or the 3.2-mm board):
        blocks = [("board", b[1], "board_fr4" if h0_material else b[2], b[3])  # same schedule,
                  for b in H1.bottom_layers(tb, 0.50, nz=1)]                   # scaled to it
        if abs(sum(b[1] for b in blocks) - base[0][1]) > 1e-12:
            raise RuntimeError("H1 blocks do not add up to the board thickness")
        return blocks + base[1:]

    def stack_with_board(stack, t_tile_mm, case="fr4_1p6mm"):
        st = so(stack, t_tile_mm, case)
        if not h0_material:
            tb = BRD.BOARD_CASES.get(case, {}).get("t_mm", t)
            st["materials"].update(H1.board_materials(tb, 0.50))
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
        kw = {k: v for k, v in kw.items() if k not in ("pitch_mm", "n_side")}
        # the design record sizes the production lattice (round 3): the variant overrides BOTH
        # its pitch and its count, so the FE field and the ledger get the same n_side x n_side
        r = orig(cells, cell_side_mm, h_tsv_mm, i_total_a,
                 pitch_mm=pitch * (1.0 - 1e-12), n_side=n_side, **kw)
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
    cx = json.loads((OUT.parent / "direct_feed_crossover.json").read_text())   # campaign hook
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
        return {((FL.input_end_layer(arch),), True): p}
    E.EXTRA_DEPOSITS = extra


# ------------------------------------------------------------------ cooling model form
def icepak_factor():
    """h_eq / h_compact implied by the matched Icepak case, for BOTH coefficient forms,
    from the compact model in force evaluated at the CFD's loading and property set
    (cooling.cfd_comparison; the JSON's stored correlation value belongs to the superseded
    Nu table). Uniform sink: h_eq = h dT_compact/dT_CFD. Streamwise sink: the local
    resistance that reproduces the CFD's mean base rise, R_loc' = dT_CFD/Q - R_cal.
    A SENSITIVITY, never a recalibration."""
    import cooling as C
    from cooling_production import CANDIDATES
    cc = C.cfd_comparison()
    j = json.loads(C.ICEPAK_REF.read_text())
    q = j["inputs"]["Q_W"] * cc["loading_factor"]
    c = CANDIDATES[E.COOLER]
    s = c.channel().solve(j["inputs"]["Q_W"], props=C.LEGACY_PROPS, wall_viscosity=False)
    r_loc_eq = cc["dT_base_mean_cfd_K"] / q - s["R_caloric_K_W"]
    return {"uniform": cc["dT_base_mean_correlation_K"] / cc["dT_base_mean_cfd_K"],
            "local": s["R_local_K_W"] / r_loc_eq, "cfd": cc}


def v_icepak_equivalent():
    from cooling_production import CANDIDATES
    c = CANDIDATES[E.COOLER]
    f = icepak_factor()
    ou, ol = type(c).h_uniform, type(c).h_local
    type(c).h_uniform = lambda self, q_w: ou(self, q_w) * f["uniform"]
    type(c).h_local = lambda self, q_w: ol(self, q_w) * f["local"]
    return {"factor_uniform": f["uniform"], "factor_local": f["local"]}


def v_cooling_model(nu=None, props=None, wall=None, top=None, bottom=None, plate=None):
    """Cooling-model form, one switch at a time (TCPMT revision): the superseded Nu table
    (long wall adiabatic), the legacy constant properties (~50 C), the wall-viscosity
    correction, the legacy top-plate coefficient with the caloric double count, the legacy
    full-flow bottom plate, the single-pass plate (round 3: production is the 4-zone
    manifold)."""
    import cooling as C
    if nu is not None:
        C.NU_MODEL = nu
    if props is not None:
        C.PROPS_MODEL = props
    if wall is not None:
        C.WALL_VISCOSITY = bool(wall)
    if top is not None:
        E.TOP_PLATE_COEFF = top
    if bottom is not None:
        E.BOTTOM_PLATE_RULE = bottom
    if plate is not None:
        if plate not in C.PLATE_MODELS:
            raise ValueError(f"unknown plate model {plate!r}")
        C.PLATE_MODEL = plate
    return {"NU_MODEL": C.NU_MODEL, "PROPS_MODEL": C.PROPS_MODEL,
            "WALL_VISCOSITY": C.WALL_VISCOSITY, "TOP_PLATE_COEFF": E.TOP_PLATE_COEFF,
            "BOTTOM_PLATE_RULE": E.BOTTOM_PLATE_RULE, "PLATE_MODEL": C.PLATE_MODEL}
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


def _z2_underside_faces(m):
    inside = [L for L in m.layers if L.region == "inside_cutout"]
    deepest = min(inside, key=lambda L: L.z0)
    ids = m.elem_set(layer=deepest.name)
    keep = [e for e in ids
            if abs(m.nodes[m.elems[e - 1] - 1][:, 2].min() - deepest.z0) < 1e-9]
    return np.array(keep, int), deepest.name


def v_z2_cooled(legacy_flow=False):
    """Z2-COOLED, bounding: a second cold plate of the SAME kind as the top one on the
    whole converter underside inside the PCB opening, without an interface. Its flow and
    sink follow final_closure_physical_etm.BOTTOM_PLATE_RULE (production: the coolant rise
    of the top plate); legacy_flow=True restores the full-flow uniform-sink plate."""
    if legacy_flow:
        E.BOTTOM_PLATE_RULE = "fixed_flow_legacy"

    def film(m, tiles, q_w):
        faces, layer = _z2_underside_faces(m)
        return E.bottom_plate_film(faces, layer, "second top-type cold plate on the "
                                   "converter underside (no interface)", q_w, tim=False)
    E.EXTRA_FILM = film
    return {"bottom_plate_rule": E.BOTTOM_PLATE_RULE}


def v_z2_cooled_tim(legacy_flow=False):
    """Backside thermal interface: the Z2-COOLED plate, but through the stack's TIM card
    (50 um at k = 3 W/mK, the top TIM) in series with the film (cooling B for Z2)."""
    if legacy_flow:
        E.BOTTOM_PLATE_RULE = "fixed_flow_legacy"

    def film(m, tiles, q_w):
        faces, layer = _z2_underside_faces(m)
        return E.bottom_plate_film(faces, layer, "second cold plate on the converter "
                                   "underside through a 50 um TIM", q_w, tim=True)
    E.EXTRA_FILM = film
    return {"bottom_plate_rule": E.BOTTOM_PLATE_RULE}


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
#: the materials a converter tier may carry besides its card (the fill between the cells)
_FILL = ("underfill_homog",)


def _retag(m, st, suffix, card_edit, layer_has):
    """Every card carried by the IN-CELL elements of the tiers whose layer name contains one
    of `layer_has` -> a copy with card_edit applied, named <card>_<suffix>, and those elements
    retagged to it. Whatever card the tier carries (derived cards in production, the legacy
    ones under conv_k_legacy) is bounded. A variant that retags nothing raises: a silently
    empty sensitivity was possible when the tiers changed card."""
    mat = np.array(m.elem_material, dtype=object)
    lay = np.array(m.elem_layer, dtype=object)
    in_t = np.array([any(t in str(l) for t in layer_has) for l in lay])
    n, bases = 0, []
    for base in sorted(set(mat[in_t]) - set(_FILL)):
        card = copy.deepcopy(st["materials"][base])
        card_edit(card)
        card["status"] = "ASSUMPTION"
        card["note"] = "class-B sensitivity bound (final_closure_sensitivity.py), not a property"
        new = f"{base}_{suffix}"
        st["materials"][new] = card
        sel = in_t & (mat == base)
        mat[sel] = new
        n += int(sel.sum())
        bases.append(base)
    if n == 0:
        raise RuntimeError(f"variant retagged no element in the tiers {layer_has}")
    m.elem_material = mat
    return n, bases


def _scale_k(card, factor):
    v = card["k"]["value"] if isinstance(card["k"], dict) else card["k"]
    card["k"] = {"value": v * factor, "status": "ASSUMPTION"}
    if isinstance(card.get("k_ortho"), dict):
        card["k_ortho"] = {"value": [x * factor for x in card["k_ortho"]["value"]],
                           "status": "ASSUMPTION"}


def v_gan_k_half():
    """GaN device-tier bound: the tier card (derived: dies + solder terminals + encapsulant;
    legacy: the Si carrier) at half its conductivity, every component. On the legacy card this
    adds t_tier/k_Si of through-thickness resistance (4.9e-6 and 5.3e-6 m^2K/W for the 638 and
    685 um tiers at 130 W/mK) -- more than any epi stack with t_epi/k_epi below that can add,
    e.g. 10 um at k > 2.1 W/mK. A stress bound, not a GaN property."""
    def hook(m, st, tiles):
        n, bases = _retag(m, st, "k_half", lambda c: _scale_k(c, 0.5), ("gan_",))
        return {"variant_elements_retagged": n, "variant_base_cards": bases}
    E.BUILD_HOOKS.append(hook)


def v_conv_k(factor):
    """Converter-tier conductivity bound: the flying-cap and inductor/C_out tiers' cards
    (derived by unit-cell homogenization in production; hvr_effective under conv_k_legacy) at
    `factor` times their conductivity, every component. A declared stress test."""
    def hook(m, st, tiles):
        n, bases = _retag(m, st, "k_bound", lambda c: _scale_k(c, factor), CONV_TIERS)
        return {"variant_elements_retagged": n, "variant_base_cards": bases}
    E.BUILD_HOOKS.append(hook)


def v_conv_mech(E_mpa, cte):
    """A corner of the legacy converter medium's declared range (package_stack.yaml
    hvr_effective: 'Sensitivity E = 80-160 GPa, CTE 4-10 ppm/K') imposed on the flying-cap and
    inductor/C_out tiers' cards. Conductivity unchanged. The derived cards carry their own
    Voigt/Reuss and Turner/volume bounds (research/tcpmt_revision/converter_cards.json)."""
    def hook(m, st, tiles):
        def edit(c):
            c["E"] = {"value": E_mpa, "status": "ASSUMPTION"}
            c["cte"] = {"value": cte, "status": "ASSUMPTION"}
        n, bases = _retag(m, st, "corner", edit, CONV_TIERS)
        return {"variant_elements_retagged": n, "variant_base_cards": bases}
    E.BUILD_HOOKS.append(hook)


def v_conv_k_legacy():
    """The converter-tier cards BEFORE the homogenization: hvr_effective (k 60 W/mK iso, E 120
    GPa, CTE 6 ppm/K, 'UNSPECIFIED surrogate') on the inductor/C_out and flying-cap tiers,
    solid silicon on the GaN tiers."""
    import tcpmt_converter_cards as CC

    def hook(m, st, tiles):
        mat = np.array(m.elem_material, dtype=object)
        n = 0
        for new, old in CC.LEGACY.items():
            if old not in st["materials"]:
                raise RuntimeError(f"legacy card {old} missing from the stack")
            sel = mat == new
            mat[sel] = old
            n += int(sel.sum())
        if n == 0:
            raise RuntimeError("conv_k_legacy found no derived converter card to replace")
        m.elem_material = mat
        return {"converter_cards": "legacy (hvr_effective, silicon)",
                "variant_elements_retagged": n}
    E.BUILD_HOOKS.append(hook)


def v_conv_tier_cards(gap="posts", post_basis=None, suffix="gapenc"):
    """Every mixed-tier card conv_tier<i> of the stack replaced by that tier's card (its own
    contents and height) under another gap model / post basis of tcpmt_converter_cards,
    under the name conv_tier<i>_<suffix>: the legacy encapsulant gap (conv_gap_legacy) or
    the lower / upper bound of the copper posts (conv_posts_lower / conv_posts_upper)."""
    import re
    import tcpmt_converter_cards as CC

    def hook(m, st, tiles):
        import design_record as DR
        mc = CC.MixedContents.from_record()
        mat = np.array(m.elem_material, dtype=object)
        n, swapped = 0, {}
        for name in sorted(set(mat)):
            if not re.match(r"^conv_tier\d+$", str(name)):
                continue
            der = st["materials"][name]["derivation"]
            tier = der["tier"]
            if tier not in {t["name"] for t in DR.tiers()}:
                raise RuntimeError(f"{suffix}: {tier} is not a tier of {DR.name()}")
            card = CC.mixed_tier(mc, tier, der["parts"], float(der["tier_um"]), gap=gap,
                                 post_basis=post_basis)
            new = f"{name}_{suffix}"
            st["materials"][new] = json.loads(json.dumps(card))
            sel = mat == name
            mat[sel] = new
            n += int(sel.sum())
            swapped[name] = {"k_ortho_production": st["materials"][name]["k_ortho"]["value"],
                             "k_ortho_variant": card["k_ortho"]["value"]}
        if n == 0:
            raise RuntimeError(f"{suffix}: found no mixed-tier card to replace")
        m.elem_material = mat
        return {"converter_cards": f"gap model {gap}, post basis {post_basis}",
                "variant_elements_retagged": n, "cards": swapped}
    E.BUILD_HOOKS.append(hook)


def v_conv_gap_legacy():
    """The mixed-tier cards BEFORE review round 3: a part shorter than its tier sits under an
    ENCAPSULANT cap (tcpmt_converter_cards GAP_MODEL 'encapsulant', with the declared EPC2055
    / EPC2090 terminal patterns) instead of being bridged to the RDLs by copper posts on its
    terminals."""
    v_conv_tier_cards(gap="encapsulant", suffix="gapenc")



# ------------------------------------------------------------------ cooling (Z3)
def v_z3_top_only():
    """Z3 with the top cold plate only: the converter underside carries the board's
    natural-convection film (h_bottom at the bottom ambient) instead of the second cold
    plate of the Z3 production boundary. Asks whether the cooling solution of Z1 and Z2
    survives the board-backside integration; everything else is the Z3 production case."""
    bc = {}

    def hook(m, st, tiles):
        tb = st["thermal_bc"]
        bc["h"], bc["T"] = tb["h_bottom"]["value"], tb["ambient_bottom"]["value"]
        return {"z3_converter_underside": "natural-convection film (no second cold plate)"}
    E.BUILD_HOOKS.append(hook)
    orig = E.z3_converter_cold_plate

    def plate(m, q_w):
        p = orig(m, q_w)
        p.update({"h_W_m2K": float(bc["h"]), "T_C": float(bc["T"]),
                  "label": "Z3 top-only: natural-convection film on the converter underside",
                  "plate": False, "streamwise": False, "rule": "natural_convection"})
        return p
    E.z3_converter_cold_plate = plate

# ------------------------------------------------------------------ cooling B (all three)
#: the cell-grid footprint the second plate covers in every integration (21.36 mm square,
#: the measured cell-grid bbox of configs/phase0nz), so the three plates are identical
PLATE_HALF_MM = 10.68 + 1e-6
TIM_R = 50e-6 / 3.0        # the top plate's TIM card: 50 um at k = 3 W/mK, in series


def v_z1_bottom_plate_tim(legacy_flow=False):
    """Cooling B for Z1: the same second plate as the backside integrations get -- the top
    plate's geometry, flow and sink by final_closure_physical_etm.BOTTOM_PLATE_RULE, through the
    top plate's 50-um TIM -- under the board beneath the cell-grid footprint. Z1's converter
    reaches it only through the substrate, the ball field and 2.4 mm of board; the
    natural-convection film stays on the rest of the board underside. legacy_flow=True: the
    full-flow uniform-sink plate of the historical setting."""
    if legacy_flow:
        E.BOTTOM_PLATE_RULE = "fixed_flow_legacy"

    def in_plate(m, e):
        c = m.nodes[m.elems[int(e) - 1][:4] - 1][:, :2].mean(0)
        return abs(c[0]) <= PLATE_HALF_MM and abs(c[1]) <= PLATE_HALF_MM
    orig = E.board_bottom_faces

    def board_bottom_faces(m, arch=None):
        faces = orig(m, arch)
        if arch != "Z1":
            return faces
        return np.array([e for e in faces if not in_plate(m, e)], int)
    E.board_bottom_faces = board_bottom_faces

    def film(m, tiles, q_w):
        faces = orig(m, "Z1")
        return E.bottom_plate_film([e for e in faces if in_plate(m, e)], "board",
                                   "Z1 cooling B: second plate under the board through a "
                                   "50 um TIM", q_w, tim=True)
    E.EXTRA_FILM = film
    return {"bottom_plate_rule": E.BOTTOM_PLATE_RULE}


def v_z3_plate_tim(legacy_flow=False):
    """Cooling B for Z3: its converter plate through the same 50-um TIM as the top plate (the
    Z3 production plate sits on the converter without an interface: a bound). Flow and sink by
    final_closure_physical_etm.BOTTOM_PLATE_RULE; legacy_flow=True: the full-flow plate."""
    if legacy_flow:
        E.BOTTOM_PLATE_RULE = "fixed_flow_legacy"
    orig = E.z3_converter_cold_plate

    def plate(m, q_w):
        p = orig(m, q_w)
        if abs(TIM_R - E.TIM_R_M2K_W) > 1e-15:
            raise RuntimeError("cooling-B TIM card differs from the bottom-plate TIM")
        p.update({"h_W_m2K": 1.0 / (1.0 / p["h_plate_W_m2K"] + TIM_R),
                  "R_tim_m2K_W": TIM_R,
                  "label": "Z3 cooling B: converter plate through a 50 um TIM"})
        return p
    E.z3_converter_cold_plate = plate
    return {"bottom_plate_rule": E.BOTTOM_PLATE_RULE}

# ------------------------------------------------------------------ tier order (Z1)
def v_z1_tier_reference():
    """Z1 built in the REFERENCE tier order of Krishnakumar 2026 (HS -> LS -> C_f -> L)
    instead of the production repartitioned order (HS -> C_f -> LS -> L), everything else
    unchanged: the same components, heights, interlayers and total. Isolates what tier
    order alone does to device temperature and loss, on top of its realizability verdict
    (worst via AR 5.32 vs 0.83). The mesh, the deposits (FL.LAYERS) and the intra-VR
    routing (FL.cell_tiers) all follow the swapped order."""
    import yaml
    import final_closure_ledger as FL
    import physical_package as PP
    sys.path.insert(0, str(R / "scripts" / "phase0nw"))
    import z1_package as Z1P
    cfg = yaml.safe_load(Z1P.Z1_CFG.read_text())
    t = cfg["converter"]["tiers_from_substrate_upward"]
    names = [x["name"] for x in t]
    if "gan_ls_EPC2057" not in names or "flying_caps" not in names:
        # TCPMT round 3: a mixed-tier design has no class tiers to swap; its tier orders
        # are evaluated by scripts/tcpmt_tier_order.py (research/tcpmt_revision/tier_order.json)
        raise RuntimeError("z1_tier_reference is a single-class (49-cell) stack variant: not "
                           "applicable to the design record's mixed tiers")
    i_ls, i_cf = names.index("gan_ls_EPC2057"), names.index("flying_caps")
    t[i_ls], t[i_cf] = t[i_cf], t[i_ls]
    tmp = scratch("fc_sens", "z1_tier_reference") / "z1_physical_reference_order.yaml"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(yaml.safe_dump(cfg, sort_keys=False))
    load = PP.load_z1_package_config
    PP.load_z1_package_config = lambda path=None: load(path or tmp)
    Z1P.Z1_CFG = tmp
    tiers = [(next((c for key, c in FL._TIER_CLASS if x["name"].startswith(key)), "rdl"),
              float(x["um"])) for x in t]
    ct = FL.cell_tiers
    FL.cell_tiers = lambda arch: list(tiers) if arch == "Z1" else ct(arch)
    lay = dict(FL.LAYERS["Z1"])
    lay["ls"] = f"z1conv_{i_cf}_gan_ls_EPC2057"
    lay["caps"] = f"z1conv_{i_ls}_flying_caps"
    FL.LAYERS["Z1"] = lay


VARIANTS = {
    "board_t3p2": dict(kind="full", archs=("Z1", "Z2"), apply=lambda: v_board_thickness(
        "it968g_3p2mm", 3200.0), gates=["board.t_only_comparison_run",
                                        "mech.t_only_mechanical"],
        nature="declared case (the round-2 thickness_sensitivity_case)",
        what="PCB 3.2 mm instead of 2.4 mm, same IT-968G material dict (TCPMT round 3: the "
             "production board; kept for the frozen lineage)"),
    # TCPMT round 3: the production board is 3.2 mm (Z2's four-tier converter needs it); the
    # thickness sensitivity is the 2.4-mm board (config thickness_sensitivity_case). Z2's
    # converter then protrudes below the board backside (recorded, cutout_fit_margin_um < 0).
    "board_t2p4": dict(kind="full", archs=("Z1", "Z2"), apply=lambda: v_board_thickness(
        "it968g_2p4mm", 2400.0), gates=["board.t_only_comparison_run",
                                        "mech.t_only_mechanical"],
        nature="declared case (config thickness_sensitivity_case)",
        what="PCB 2.4 mm instead of 3.2 mm, same IT-968G material dict"),
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
                          what="Z2-COOLED plate through a 50 um TIM at k = 3 W/mK (flow: the "
                               "top plate's coolant rise)"),
    "bga_depop": dict(kind="full", archs=("Z2",), apply=lambda: v_bga_population(420 / 528),
                      gates=["mech.bga_population"],
                      nature="BGA mechanical population (smeared)",
                      what="BGA field populated at 420/528: the 54 + 54 48 V balls of the "
                           "BGA-fed design removed"),
    "z1_bottom_plate_tim": dict(kind="full", archs=("Z1",), apply=v_z1_bottom_plate_tim,
                                gates=[], nature="ENGINEERING_SENSITIVITY (cooling B)",
                                what="Z1 with a second plate under the board beneath the cell "
                                     "grid, through a 50 um TIM (flow: the top plate's "
                                     "coolant rise)"),
    "z3_plate_tim": dict(kind="full", archs=("Z3",), apply=v_z3_plate_tim,
                         gates=[], nature="ENGINEERING_SENSITIVITY (cooling B)",
                         what="Z3 converter plate through a 50 um TIM (flow: the top plate's "
                              "coolant rise)"),
    "z3_top_only": dict(kind="full", archs=("Z3",), apply=v_z3_top_only,
                        gates=[], nature="ENGINEERING_SENSITIVITY (cooling solution, Z3)",
                        what="Z3 with the top cold plate only (converter underside in the "
                             "board's natural-convection film instead of its own plate)"),
    "z1_tier_reference": dict(kind="full", archs=("Z1",), apply=v_z1_tier_reference,
                              gates=["geom.tier_order"], nature="ENGINEERING_SENSITIVITY (tier order)",
                              what="Z1 in the reference tier order HS-LS-Cf-L (production: "
                                   "repartitioned HS-Cf-LS-L); components, heights unchanged"),
    "board_hbot100": dict(kind="full", archs=("Z1", "Z2", "Z3"), apply=lambda: v_board_hbot(100.0),
                          gates=["board.bottom_boundary"], nature="ENGINEERING_SENSITIVITY (board thermal boundary)",
                          what="effective board-bottom coefficient 100 W/m2K instead of 10 "
                               "(full server board, forced air)"),
    "board_hbot500": dict(kind="full", archs=("Z1", "Z2", "Z3"), apply=lambda: v_board_hbot(500.0),
                          gates=["board.bottom_boundary"], nature="ENGINEERING_SENSITIVITY (board thermal boundary)",
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
                       what="GaN device-tier cards at half their conductivity"),
    "conv_k_tenth": dict(kind="full", archs=("Z1", "Z2"), apply=lambda: v_conv_k(0.1),
                         gates=["mat.mlcc_bounded", "mat.inductor_tier_bounded"],
                         nature="bounding stress test",
                         what="flying-cap and inductor/Cout tier cards at a tenth of their "
                              "conductivity"),
    # ---- TCPMT revision: the superseded settings of the thermal model, one at a time
    "conv_k_legacy": dict(kind="full", archs=("Z1", "Z2", "Z3"), apply=v_conv_k_legacy,
                          gates=["mat.mlcc_bounded", "mat.inductor_tier_bounded",
                                 "mat.gan_bounded"],
                          nature="LEGACY_SETTING (converter cards before the homogenization)",
                          what="hvr_effective (k 60 W/mK) on the inductor/Cout and flying-cap "
                               "tiers, solid silicon on the GaN tiers"),
    # ---- review round 3: parts shorter than their tier bridged by copper posts (production);
    # the encapsulant cap of the earlier mixed-tier cards is this legacy setting
    "conv_gap_legacy": dict(kind="full", archs=("Z1", "Z2", "Z3"), apply=v_conv_gap_legacy,
                            gates=["mat.mlcc_bounded", "mat.inductor_tier_bounded",
                                   "mat.gan_bounded"],
                            nature="LEGACY_SETTING (mixed-tier cards before review round 3)",
                            what="encapsulant cap over the parts shorter than their tier "
                                 "(dies, inductors, capacitors) instead of copper posts on "
                                 "their terminals"),
    "conv_posts_lower": dict(kind="full", archs=("Z1", "Z2", "Z3"),
                             apply=lambda: v_conv_tier_cards(post_basis="current",
                                                             suffix="posts_lo"),
                             gates=["mat.mlcc_bounded", "mat.inductor_tier_bounded",
                                    "mat.gan_bounded"],
                             nature="declared range end (copper-post cross-section)",
                             what="gap posts carrying only the terminal RMS currents at the "
                                  "intra-VR density (the lower end of kz_post_range)"),
    "conv_posts_upper": dict(kind="full", archs=("Z1", "Z2", "Z3"),
                             apply=lambda: v_conv_tier_cards(post_basis="terminal",
                                                             suffix="posts_hi"),
                             gates=["mat.mlcc_bounded", "mat.inductor_tier_bounded",
                                    "mat.gan_bounded"],
                             nature="declared range end (copper-post cross-section)",
                             what="gap posts of the full solder-bar outline, the widest MLCC "
                                  "band and half the inductor post density (the upper end of "
                                  "kz_post_range)"),
    "nu_legacy_table": dict(kind="full", archs=("Z1", "Z2", "Z3"),
                            apply=lambda: v_cooling_model(nu="legacy_3w_table"),
                            gates=["therm.cooling_model_form"],
                            nature="LEGACY_SETTING (cold-plate Nu table with a long wall "
                                   "adiabatic, alpha->0 limit 5.385)",
                            what="cold-plate Nu from the superseded three-wall table instead of "
                                 "the Shah & London short-wall-adiabatic H1 fit"),
    "props_legacy_50C": dict(kind="full", archs=("Z1", "Z2", "Z3"),
                             apply=lambda: v_cooling_model(props="legacy_50C"),
                             gates=["therm.cooling_model_form"],
                             nature="LEGACY_SETTING (water properties at ~50 C)",
                             what="coolant properties at ~50 C instead of the bulk mean"),
    "wall_viscosity": dict(kind="full", archs=("Z1", "Z2", "Z3"),
                           apply=lambda: v_cooling_model(wall=True),
                           gates=["therm.cooling_model_form"],
                           nature="ENGINEERING_SENSITIVITY (property variation)",
                           what="wall-viscosity correction (Nu (mu_b/mu_w)^0.14, "
                                "f (mu_w/mu_b)^0.58)"),
    "plate_caloric_legacy": dict(kind="full", archs=("Z1", "Z2", "Z3"),
                                 apply=lambda: v_cooling_model(top="uniform_legacy"),
                                 gates=["therm.cooling_model_form"],
                                 nature="LEGACY_SETTING (caloric double count)",
                                 what="top plate with the uniform-sink coefficient (R_cal "
                                      "included) on the streamwise sink"),
    "plate_single_pass": dict(kind="full", archs=("Z1", "Z2", "Z3"),
                              apply=lambda: v_cooling_model(plate="single_pass"),
                              gates=["therm.cooling_model_form"],
                              nature="LEGACY_SETTING (single-pass cold plate, before the "
                                     "round-3 manifold)",
                              what="every plate single pass (one inlet, one outlet, full "
                                   "length and flow; ~16 x the manifold pressure drop) instead "
                                   "of the 4-zone manifold; same h, one-way coolant sink"),
    "z1_bottom_plate_tim_fullflow": dict(
        kind="full", archs=("Z1",), apply=lambda: v_z1_bottom_plate_tim(legacy_flow=True),
        gates=[], nature="LEGACY_SETTING (cooling B, full-flow bottom plate)",
        what="Z1 cooling B with the bottom plate at the full 27 g/s, uniform inlet sink"),
    "z2_cooled_tim_fullflow": dict(
        kind="full", archs=("Z2",), apply=lambda: v_z2_cooled_tim(legacy_flow=True),
        gates=[], nature="LEGACY_SETTING (cooling B, full-flow bottom plate)",
        what="Z2 cooling B with the bottom plate at the full 27 g/s, uniform inlet sink"),
    "z3_plate_tim_fullflow": dict(
        kind="full", archs=("Z3",), apply=lambda: v_z3_plate_tim(legacy_flow=True),
        gates=[], nature="LEGACY_SETTING (cooling B, full-flow bottom plate)",
        what="Z3 cooling B with the converter plate at the full 27 g/s, uniform inlet sink"),
    "z2_cooled_fullflow": dict(
        kind="full", archs=("Z2",), apply=lambda: v_z2_cooled(legacy_flow=True),
        gates=["therm.z2_cooled"], nature="LEGACY_SETTING (interface-free plate, full flow)",
        what="interface-free Z2 underside plate at the full 27 g/s, uniform inlet sink"),
    "z3_plate_fullflow": dict(
        kind="full", archs=("Z3",), apply=lambda: v_cooling_model(bottom="fixed_flow_legacy"),
        gates=[], nature="LEGACY_SETTING (interface-free plate, full flow)",
        what="Z3 production (interface-free) converter plate at the full 27 g/s, uniform "
             "inlet sink"),
}
# TCPMT round 3 (finding 6): the authors' own 60-520 W/m2K board-spreading estimate, both ends,
# on all three architectures (the 100/500 pair above predates Z3 and the estimate)
for _h in (60.0, 520.0):
    VARIANTS[f"board_hbot{_h:g}"] = dict(
        kind="full", archs=("Z1", "Z2", "Z3"), apply=(lambda h_=_h: v_board_hbot(h_)),
        gates=["board.bottom_boundary"],
        nature="ENGINEERING_SENSITIVITY (board thermal boundary, finding 6)",
        what=f"effective board-bottom coefficient {_h:g} W/m2K instead of 10 (end of the "
             "60-520 W/m2K full-board estimate)")
# TCPMT round 3 (findings 7, 11a): encapsulant classes with their glass transition and the
# BGA layer from the local solder card, all from configs/tcpmt_mech/mechanics_revision.yaml
import tcpmt_mech_variants as _MV                                     # noqa: E402
_MV.register(VARIANTS, lambda h: E.BUILD_HOOKS.append(h))

for _E in (80e3, 160e3):
    for _a in (4e-6, 10e-6):
        VARIANTS[f"conv_E{_E / 1e3:.0f}_a{_a * 1e6:.0f}"] = dict(
            kind="mech", archs=("Z1", "Z2"),
            apply=(lambda E_=_E, a_=_a: v_conv_mech(E_, a_)),
            gates=["mat.mlcc_bounded", "mat.inductor_tier_bounded"],
            nature="declared range (package_stack.yaml hvr_effective)",
            what=f"converter medium E = {_E / 1e3:.0f} GPa, CTE = {_a * 1e6:.0f} ppm/K")


def case_file(arch, variant, scen=SCEN):
    """A variant NAME@B (mechanics only on the cooling-B field, finding 8) is stored as
    etm_<arch>_<scen>__NAME__B.json (a non-production mesh level adds its suffix)."""
    return OUT / f"etm_{arch}_{scen}__{variant.replace('@', '__')}.json"


def split_tier(variant):
    """'NAME@B' -> ('NAME', 'B'); 'NAME' -> ('NAME', 'A')."""
    name, _, tier = variant.partition("@")
    return name, (tier or "A")


def thermal_base(arch, tier):
    """(base case dict, converged-field .frd, base label) of a mechanics-only variant: the
    production (cooling-A) case, or the architecture's cooling-B case
    (configs/tcpmt_mech: cooling_B_base)."""
    if tier == "A":
        return (json.loads(E.case_path(arch, SCEN).read_text()),
                FIELDS / f"etm_{arch}_{SCEN}_r21" / "thermal_converged.frd",
                E.case_path(arch, SCEN).name)
    import tcpmt_mech_laws as LAW
    cfg = LAW.cfg()
    bv = cfg["cooling_B_base"][arch]
    d = FIELDS / f"etm_{arch}_{SCEN}__{bv}"
    if not (d / "thermal_converged.frd").exists():
        d = Path((cfg.get("cooling_B_field_fallback") or {}).get(arch) or d)
    frd = d / "thermal_converged.frd"
    if not frd.exists():
        its = sorted(d.glob("et*"), key=lambda p: int(p.name[2:]))
        if not its:
            raise FileNotFoundError(f"no converged cooling-B field for {arch} under {d} "
                                    "(set HVR_FIELDS or cooling_B_field_fallback)")
        frd = sorted(its[-1].glob("th_*.frd"), key=lambda p: int(p.stem.split("_")[1]))[-1]
    base = json.loads(case_file(arch, bv).read_text())
    return base, frd, case_file(arch, bv).name


def _spec(variant):
    name, tier = split_tier(variant)
    v = VARIANTS[name]
    return {"name": variant, "kind": v["kind"], "gates": v["gates"],
            "nature": v["nature"], "what": v["what"], "cooling_tier": tier}


def run_full(arch, variant):
    """E-T fixed point + mechanics of one full variant, on this process's mesh rung (the
    production mesh unless set_refine chose a ladder rung)."""
    E.WD = scratch("fc_sens", work_name(variant))
    VARIANTS[variant]["apply"]()
    E._raise_stack_limit()
    h, r = E.PRODUCTION_H_XY, mesh_level()
    m, mats, st, tiles, minfo, L, th, hist, t_et, wd = E.run_et(arch, SCEN, h, r)
    res = {"arch": arch, "scenario": SCEN, "h_xy_mm": h, "refine": list(r),
           "mesh_rung": rung_tag(r), "production_mesh": is_production_level(),
           "variant": _spec(variant), "materials": minfo,
           "ledger_rows": L["rows"], "P_loss_w": L["P_loss_w"],
           "i_hv_avg_a": L["i_hv_avg_a"], "energy_ledger": L["energy"],
           "thermal": {k: v for k, v in th.items() if k != "T_node"},
           "die_T_max_C": th["die_T_max_C"], "die_T_mean_C": th["die_T_mean_C"],
           "et_history": hist,
           "et_converged": (hist[-1]["max_dT_K"] < E.ET_TOL_K
                            and hist[-1]["dP_rel"] < E.ET_TOL_P_REL),
           "et_wall_s": t_et, "threads": E.THREADS,
           "production_case": E.case_path(arch, SCEN).name,
           # TCPMT round 3: the design record entry it was computed with (tcpmt_cases.guard
           # refuses a case of another design; without this a variant file passed unchecked)
           "design": E.Z1D.summary()}
    f = variant_file(arch, variant)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(res, indent=1, default=float))
    try:
        res["mechanics"] = E.mechanics(m, mats, st, th["T_node"], wd, arch, tiles,
                                       E.PRODUCTION_SOLVER, 1)
    except Exception as e:                        # recorded, never silently dropped
        res["mechanics_error"] = str(e)[-600:]
    f.write_text(json.dumps(res, indent=1, default=float))
    return f.name, "mechanics" in res


def run_mech(arch, variant):
    """Mechanics only on a converged field: the production (cooling-A) field, or with
    variant NAME@B the cooling-B field of the architecture (finding 8)."""
    import production_et as PE
    name, tier = split_tier(variant)
    if VARIANTS[name]["kind"] != "mech":
        raise ValueError(f"{name} changes heat paths: it cannot run on a converged field")
    if not is_production_level():
        raise ValueError("mechanics-only variants run on the production-mesh field only")
    VARIANTS[name]["apply"]()
    E._raise_stack_limit()
    base, frd, base_name = thermal_base(arch, tier)
    m, mats, st, tiles, minfo = E.build(arch, E.PRODUCTION_H_XY, E.PRODUCTION_REFINE)
    tn = PE.ccxio.read_frd(frd)["NDTEMP"][1:m.n_nodes + 1, 0]
    if abs(float(np.nanmax(tn)) - base["thermal"]["T_max_C"]) > 1e-6:
        raise RuntimeError(f"{frd} is not the converged field of {base_name}")
    res = {k: base[k] for k in ("arch", "scenario", "h_xy_mm", "refine", "ledger_rows",
                                "P_loss_w", "i_hv_avg_a", "energy_ledger", "thermal",
                                "et_history", "et_converged", "et_wall_s")}
    die = E.die_stats(m, tn, arch)
    res["thermal"] = {**res["thermal"], **die}
    res.update({"variant": _spec(variant), "materials": minfo, **die,
                "thermal_from": (f"converged field of {base_name} (mechanics-only variant, "
                                 f"cooling {tier})"),
                "production_case": E.case_path(arch, SCEN).name, "thermal_case": base_name,
                "design": base.get("design") or E.Z1D.summary()})
    try:
        res["mechanics"] = E.mechanics(m, mats, st, tn,
                                       scratch("fc_sens", variant.replace("@", "_"), arch),
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
        fn = run_full if VARIANTS[split_tier(variant)[0]]["kind"] == "full" else run_mech
        name, ok = fn(arch, variant)
        return {"arch": arch, "variant": variant, "file": name, "mechanics_ok": ok,
                "wall_s": time.time() - t0}
    except Exception as e:                        # a crash is a recorded result
        return {"arch": arch, "variant": variant, "error": str(e)[-600:],
                "wall_s": time.time() - t0}


def _bga_kin(c):
    return ((c.get("mechanics") or {}).get("interconnects") or {}).get("bga", {}).get("critical")


def _local_task(t):
    """The local response at a variant's own critical joint. With the v2 local model
    (configs/tcpmt_mech local.harness = v2; TCPMT round 3) the joint is driven by the full
    cut-boundary kinematics the case stores (mechanics.interconnects.bga.critical), with the
    production law and ramped loading; the legacy harness (split load step, the temporal
    study's first increment, |du_xy| and T only) is kept for cases without kinematics."""
    arch, variant = t
    c = json.loads(case_file(arch, variant).read_text())
    kin = _bga_kin(c)
    import tcpmt_mech_laws as LAW
    if kin and LAW.cfg()["local"]["harness"] == "v2":
        import tcpmt_mech_submodel as SUB
        r = SUB.solve(dict(study="sens_local", tag=f"{arch}_{variant.replace('@', '_')}",
                           kin=kin, meta={"arch": arch, "variant": variant}))
        r["du_um"], r["T_joint_C"] = kin["du_xy_um"], SUB.site_temperature(kin)
        r["harness"] = "v2"
        return arch, variant, r
    import final_closure_local_mesh as LM
    crit = c["mechanics"]["joint_search"]["critical"]
    inc0 = json.loads(LM.TIME_STUDY.read_text())["production_dt0_s"]
    r = LM._solve(f"{arch}_{variant}", crit["du_um"], crit["T_C"],
                  scratch("fc_sens_local", variant, arch), "L0", inc0, True)
    r["harness"] = "legacy"
    return arch, variant, r


def _needs_local(a, v):
    if not case_file(a, v).exists():
        return False
    c = json.loads(case_file(a, v).read_text())
    if "mechanics" not in c:
        return False
    crit, loc = c["mechanics"]["joint_search"]["critical"], c.get("local") or {}
    kin = _bga_kin(c)
    if kin and loc.get("harness") == "v2":
        return not (loc.get("d_peeq_per_cycle")
                    and abs(loc.get("du_um", -1.0) - kin["du_xy_um"]) < 1e-12)
    return not (loc.get("d_peeq_per_cycle") and loc.get("du_um") == crit["du_um"]
                and loc.get("T_joint_C") == crit["T_C"])


def local_main(names):
    tasks = [(a, v) for v in (names or list(VARIANTS))
             for a in VARIANTS[split_tier(v)[0]]["archs"] if _needs_local(a, v)]
    if not tasks:
        print("no variant needs a local solve", flush=True)
        return
    with mp.Pool(min(len(tasks), 24, POOL_MAX)) as p:
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
    args = sys.argv[1:]
    if args[:1] == ["--refine"]:                  # a ladder rung for every task of this call
        set_refine(args[1])
        args = args[2:]
    tasks = []
    for a in (args or list(VARIANTS)):
        v, *arch = a.split(":")                   # VARIANT[@B][:ARCH ...]
        tasks += [(x, v) for x in (arch or VARIANTS[split_tier(v)[0]]["archs"])]
    with mp.Pool(min(len(tasks), POOL_MAX)) as p:
        out = p.map(_task, tasks)
    log = OUT / "run_log.json"
    old = json.loads(log.read_text()) if log.exists() else []
    log.write_text(json.dumps(old + out, indent=1, default=float))
    for r in out:
        print(r, flush=True)


if __name__ == "__main__":
    main()
