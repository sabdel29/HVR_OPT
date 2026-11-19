"""FINAL CLOSURE --- the physical electrothermal fixed point, mechanics, and joint search.

Runs the PHYSICAL Z1/Z2 packages (the Phase-0N builders) through:

  ledger(T)  -> tier-aware heat map -> conjugate thermal FE -> T  (repeat to a fixed point)
  -> thermoelastic FE once on the converged field -> warpage, all-site joint drivers

Three corrections to the historical production path are made here, each because the
historical form was wrong for the physical packages:

1. THE BOTTOM HEAT FLOW WAS NEVER COMPUTED. production_et.solve_thermal set
   q_bot = Q_total - q_top and then reported energy_residual = q_top + q_bot - Q_total,
   which is zero by construction -- every historical "energy residual" was a tautology.
   Here q_bot is integrated from the board-bottom film faces of the SOLVED field, so the
   residual can actually fail.
2. THE FE SUBSTRATE NOW HOLDS THE ELECTRICAL TSV FIELD. The substrate carried a
   19.6 % Cu fraction smeared over all 900 mm^2. The adopted field is the cell's 30-um via
   lattice (scaled with the cell current since TCPMT round 3: 2025 per cell at M = 36)
   inside the tiles and plain silicon elsewhere.
3. THE RDL TIER TENSOR IS THE TIER'S OWN. A four-metal-layer, 40 um stack tensor was
   applied to single 10 um tiers. It is replaced by the laminate of one 10 um tier
   (validated separately against an explicit RVE).

PHASE 0N-Z adds Z3, the same regulator hung from the PCB BACKSIDE
(configs/phase0nz/z3_board_backside.yaml), as a separate branch everywhere it differs:
its own geometry builder, the board elements under the cells as the PCB via-field
deposit/temperature region, and its production bottom boundary (a converter-underside
cold plate plus the natural-convection film on the uncovered board underside). Z3 writes
only its own case files; the Z1/Z2 results pipeline does not read them.

TCPMT REVISION (thermal model). The cold plate's Nu is the three-wall H1 fit with the short
wall adiabatic and the coolant properties are taken at the bulk mean temperature
(phase0m/cooling.py); the top plate's film uses the streamwise-sink coefficient
(TOP_PLATE_COEFF, no caloric double count); every second plate is sized by one declared rule
(BOTTOM_PLATE_RULE: the top plate's coolant rise) and charged its own pumping
(thermal.cooling); the converter tiers carry homogenized cards (tcpmt_converter_cards.py);
every case records the processor-die temperature (die_T_max_C, die_T_mean_C). Each
superseded setting is a variant (final_closure_sensitivity: nu_legacy_table,
props_legacy_50C, plate_caloric_legacy, *_fullflow, conv_k_legacy).
"""
from __future__ import annotations

import copy
import json
import math
import os
import sys
import time
from pathlib import Path

# Every pool worker would otherwise start a full-width OpenBLAS pool (64-96 idle threads);
# on this shared host that reached the per-user thread limit and killed CalculiX
# runs mid-solve (DEFECT #69). The solvers set their own thread counts.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np  # noqa: E402

R = Path(__file__).resolve().parents[1]
for _p in ("scripts/phase0nw", "scripts/phase0m", "scripts/phase0mr", "scripts/phase0i",
           "scripts/phase0g", "scripts/phase0b", "scripts/phase0e", "scripts/phase0dr",
           "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))

import final_closure_ledger as FL                                   # noqa: E402
import z1_design as Z1D                                             # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hvr_scratch import path as scratch                             # noqa: E402
import pkg_rdl_network as _K                                        # noqa: E402
# the BGA-fed CONTROL shares Z2's cutout and therefore its 528-site mechanical BGA field
_K.register_architecture("Z2BF", _K.architecture_cutout_mm("Z2"))
# Z3 (regulator on the PCB backside) has NO opening: the full 1369-site lattice, as Z1
_K.register_architecture("Z3", None)

OUT = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "final_closure"   # campaign hook
WD = Path(os.environ["FC_WORKDIR"]) if "FC_WORKDIR" in os.environ else scratch("fc_etm")
#: TCPMT revision: a non-default Z1 design (HVR_Z1_CONFIG, scripts/phase0nw/z1_design.py)
#: writes its case files to its config's results directory, named with its design tag, and
#: never into research/final_closure; the production names are unchanged
DESIGN_TAG = "" if Z1D.is_default() else Z1D.tag()
if not Z1D.is_default():
    OUT = Z1D.results_dir()
ET_TOL_K = 0.25            # declared before any physical result was read
#: mechanical mesh convergence, DECLARED before the h = 0.8 mm runs were read:
#: relative change of T_max, die warpage and critical-joint du between h_xy 1.1 and 0.8
MESH_TOL_REL = 0.02
MESH_LEVELS_MM = (1.1, 0.8)
#: The h_xy 1.1 -> 0.8 pair is NOT a refinement for Z2: lowering h_xy re-grades the grid,
#: Z2 keeps 38 lines per axis and its largest interior element GROWS from 1.12 to 1.72 mm,
#: and neither level refines z. It is kept only as a re-meshing sensitivity. Convergence
#: is judged on the NESTED study, declared before its results were read, with the same
#: 2 % tolerance on the same observables: every base (h_xy = 1.1) interval split in two
#: in-plane, r = (2, 1), and every layer's elements split in two through the thickness,
#: r = (1, 2). Every base node survives in both, so each is a strict refinement.
#: PRODUCTION MESH. The unrefined grid puts three elements across a 2.37 mm converter
#: tile, and the nested in-plane refinement raised the converged peak temperature by more
#: than the declared 2 % (mesh_convergence.json). Production therefore uses the h_xy = 1.1
#: grid with every in-plane interval split in two (r21); ITS convergence is judged against
#: r31 in-plane and against the measured through-thickness sensitivity (r11 -> r12).
PRODUCTION_H_XY = 1.1
PRODUCTION_REFINE = (2, 1)
#: refined meshes exceed the SPOOLES ceiling, so their structural solves use ITERATIVE
#: CHOLESKY, verified against SPOOLES on the base mesh (solver_check/)
PRODUCTION_SOLVER = "ITERATIVE CHOLESKY"
INPLANE_SEQUENCE = ((1, 1), (2, 1), (3, 1))
THROUGH_THICKNESS = ((1, 1), (1, 2))
ET_TOL_P_REL = 1e-3
ET_MAX_ITER = 8
THREADS = int(os.environ.get("FC_THREADS", "12"))
COOLER = "TOP_SI_MICROCHANNEL_27"
#: Class-B sensitivity hooks, set only by final_closure_sensitivity.py. On the production
#: path BUILD_HOOKS is empty and EXTRA_FILM is None, so nothing below changes.
#:   BUILD_HOOKS  callables (mesh, stack, tiles) -> dict, applied after the TSV/RDL
#:                material assignment and before the material cards are built
#:   EXTRA_FILM   callable (mesh, tiles, Q_W) -> {"elems", "h_W_m2K", "T_C", "label"}: one
#:                more convective face set (bottom faces, F1), whose heat flow is
#:                COMPUTED from the solved field and enters the heat balance
BUILD_HOOKS: list = []
EXTRA_FILM = None
#:   EXTRA_DEPOSITS callable (arch, scen, L) -> {(layers tuple, in_tiles): W}: heat that is
#:                NOT in the package-internal ledger but deposited in the FE domain (the
#:                direct-feed heat-location sensitivity); None on the production path
EXTRA_DEPOSITS = None
#:   TOP_FILM_HOOK callable (mesh, top_faces, h_face) -> h_face: per-face top-film
#:                coefficients, used consistently in the deck AND the coolant balance
#:                (the mechanical-to-thermal TIM feedback of the TCPMT revision,
#:                tcpmt_review_variants.py); None on the production path
TOP_FILM_HOOK = None
#: TCPMT round 3 (findings 2, 4, 6, 9). Structural boundary and extra step loads of the
#: thermoelastic solve, set only by the mounting/clamp studies (tcpmt_mech_board.py):
#:   STRUCT_BC     ccxio boundary name; production "BC_BOARD" (3-2-1 on the board underside)
#:   STRUCT_PARAMS dict for the mounting boundaries (screw inset/patch, footprint)
#:   STRUCT_LOADS  callable (mesh) -> list of deck lines inserted in the structural step
STRUCT_BC = "BC_BOARD"
STRUCT_PARAMS = None
STRUCT_LOADS = None
#: every configured interconnect layer is searched and the cut-boundary kinematics of its
#: candidate sites kept with the case (tcpmt_mech_kinematics); False skips it
INTERCONNECT_SEARCH = True

#: TOP-PLATE COEFFICIENT (TCPMT revision, caloric correction). The top boundary resolves the
#: coolant warming along the flow, T_fluid(x) = T_in + Q(0 -> x)/(m_dot c_p), so its film
#: coefficient must not also carry the caloric resistance R_cal = 1/(2 m_dot c_p) of the
#: uniform-sink convention: that counted half the coolant rise twice (~5 K at 1.1 kW, 27 g/s).
#: Production: "local" = 1/((R_conv + R_base) A) (CoolingDesign.h_local). "uniform_legacy"
#: restores the historical h_uniform (variant plate_caloric_legacy_*).
TOP_PLATE_COEFF = "local"
#: BOTTOM-PLATE FLOW RULE (TCPMT revision). Every second plate of the top plate's geometry
#: (cooling B under Z1/Z2/Z3, the Z2-cooled and Z3 interface-free plates) is sized by ONE
#: declared rule. Production "equal_rise": its mass flow gives it the SAME coolant temperature
#: rise as the top plate, m_b = m_top Q_b/Q_top (parallel branches of one loop balanced to a
#: common outlet temperature); its sink follows its own coolant along the flow (same direction
#: as the top plate), T_b(x) = T_in + dT_top Q_b(0 -> x)/Q_b from the SOLVED face fluxes, with
#: the local coefficient (in series with the interface where one is declared). Its pumping is
#: computed at its own flow. "fixed_flow_legacy": the full top-plate flow whatever the plate
#: carries, a uniform sink at the inlet temperature with h_uniform, pumping of a full plate
#: (the historical setting, variants *_fullflow).
BOTTOM_PLATE_RULE = "equal_rise"
#: the top TIM card (50 um at k = 3 W/mK) in series with a bottom plate's film
TIM_R_M2K_W = 50e-6 / 3.0


def top_plate_h(cooler, q_w):
    """The top plate's film coefficient under the production convention."""
    if TOP_PLATE_COEFF == "local":
        return float(cooler.h_local(q_w))
    if TOP_PLATE_COEFF == "uniform_legacy":
        return float(cooler.h_uniform(q_w))
    raise ValueError(f"unknown TOP_PLATE_COEFF {TOP_PLATE_COEFF!r}")


def bottom_plate_film(elems, layer, label, q_w, tim=True):
    """A second cold plate of the top plate's geometry on the faces `elems`, under the
    declared BOTTOM_PLATE_RULE. The film dict carries what solve_thermal needs to resolve
    its sink and to charge its pumping."""
    from cooling_production import CANDIDATES
    cooler = CANDIDATES[COOLER]
    r_tim = TIM_R_M2K_W if tim else 0.0
    if BOTTOM_PLATE_RULE == "equal_rise":
        h = float(cooler.h_local(q_w))
        streamwise = True
    elif BOTTOM_PLATE_RULE == "fixed_flow_legacy":
        h = float(cooler.h_uniform(q_w))
        streamwise = False
    else:
        raise ValueError(f"unknown BOTTOM_PLATE_RULE {BOTTOM_PLATE_RULE!r}")
    return {"elems": np.asarray(elems, int), "h_W_m2K": 1.0 / (1.0 / h + r_tim),
            "h_plate_W_m2K": h, "R_tim_m2K_W": r_tim, "T_C": float(cooler.t_in_c),
            "layer": layer, "label": label, "plate": True, "streamwise": streamwise,
            "rule": BOTTOM_PLATE_RULE}


def die_stats(m, Tn, arch=None):
    """Processor-die temperature: maximum and node mean over the die layer (the node mean is
    the definition of the E-T history's T_die_mean_C). Tn is the 0-based nodal array."""
    import production_et as PE
    die = FL.LAYERS[arch]["die"] if arch in FL.LAYERS else "die"
    ids = PE._layer_elems(m, die)
    nodes = np.unique(m.elems[ids - 1].ravel())
    t = np.asarray(Tn)[nodes - 1]
    return {"die_T_max_C": float(np.nanmax(t)), "die_T_mean_C": float(np.nanmean(t))}

# --- material corrections -------------------------------------------------
#: TCPMT round 3: the TSV fabric of one cell scaled with the cell current at the 49-cell
#: field's current per via (38 x 38 = 1444 at 1000/49 A; 45 x 45 = 2025 at 1000/36 A), on the
#: cell of the design in force (design_record.tsv_n_side) -- the ledger's TSV rows use the same
#: lattice (final_closure_ledger.ledger -> tsv_fields.system_report(n_side=...))
TSV_N_PER_CELL = Z1D.tsv_n_per_cell()
TSV_D_MM = 0.030


def tsv_tile_fraction(tile_side_mm):
    return TSV_N_PER_CELL * math.pi * (TSV_D_MM / 2) ** 2 / tile_side_mm ** 2


def tsv_material(stack, f):
    si, cu = stack["materials"]["silicon"], stack["materials"]["copper"]
    v = lambda d, k: d[k]["value"] if isinstance(d[k], dict) else d[k]
    E_si = si["isotropic_check"]["E"]; nu_si = si["isotropic_check"]["nu"]
    a_si, k_si = v(si, "cte"), v(si, "k")
    E_cu, nu_cu, a_cu, k_cu = v(cu, "E"), v(cu, "nu"), v(cu, "cte"), v(cu, "k")
    E = f * E_cu + (1 - f) * E_si
    kz = f * k_cu + (1 - f) * k_si
    kxy = k_si * (k_cu + k_si + f * (k_cu - k_si)) / (k_cu + k_si - f * (k_cu - k_si))
    return {"status": "DERIVED", "elastic_type": "iso",
            "E": {"value": E, "status": "DERIVED"},
            "nu": {"value": f * nu_cu + (1 - f) * nu_si, "status": "DERIVED"},
            "cte": {"value": (f * E_cu * a_cu + (1 - f) * E_si * a_si) / E,
                    "status": "DERIVED"},
            "k": {"value": kxy, "status": "DERIVED"},
            "k_ortho": {"value": [kxy, kxy, kz], "status": "DERIVED"},
            "cu_area_fraction": f}


#: one 10 um RDL tier = a Cu sublayer (t_Cu, in-layer occupancy) on dielectric
RDL_TIER = {"t_tier_um": 10.0, "t_cu_um": 5.0, "occupancy": 0.30,
            "k_cu": 400.0, "k_d": 0.35, "E_cu": 117e3, "E_d": 20e3,
            "a_cu": 17.0e-6, "a_d": 30.0e-6, "nu": 0.30}


def rdl_tier_laminate(p=RDL_TIER):
    """The production tensor of one 10 um RDL tier.

    VALIDATION CHANGED IT. The first version used the Voigt in-plane value
    occ*k_Cu (60.3 W/mK) and the series through-thickness value (0.698 W/mK). An
    explicit RVE of the DECLARED tier (square Cu grid, 30 % occupancy, 5 um Cu on
    5 um dielectric) solved in AEDT 2026 R1 Mechanical gave k_x = 34.28 and
    k_z = 0.620 W/mK: Voigt overstates in-plane conduction by 76 % for a grid
    (cross-lines do not conduct along x), and the series form overstates k_z by
    12.5 % because it ignores the constriction of heat onto the grid lines. The
    production tensor therefore ADOPTS the RVE values, read from
    research/final_closure/reference_rve.json rather than retyped; the grid
    laminate is kept as the analytic check (-3.7 % in-plane). Stiffness and CTE
    use the same grid laminate form; they were not RVE-validated (B-class).
    """
    import json as _json
    phi = p["t_cu_um"] / p["t_tier_um"]
    o = p["occupancy"]
    wp = 1.0 - math.sqrt(1.0 - o)
    ser = lambda a_, b_: 1.0 / (wp / a_ + (1 - wp) / b_)
    k_sub_x = wp * p["k_cu"] + (1 - wp) * ser(p["k_cu"], p["k_d"])
    kx = phi * k_sub_x + (1 - phi) * p["k_d"]
    k_sub_z = o * p["k_cu"] + (1 - o) * p["k_d"]
    kz = 1.0 / (phi / k_sub_z + (1 - phi) / p["k_d"])
    src = "grid laminate (analytic)"
    f = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "final_closure" / "reference_rve.json"
    if f.exists():
        rv = _json.loads(f.read_text())
        if rv.get("rdl_tier_kx", {}).get("reference_value") and \
                rv.get("rdl_tier_kz", {}).get("reference_value"):
            kx = float(rv["rdl_tier_kx"]["reference_value"])
            kz = float(rv["rdl_tier_kz"]["reference_value"])
            src = "explicit RVE, AEDT 2026 R1 Mechanical (reference_rve.json)"
    E_sub = wp * p["E_cu"] + (1 - wp) * ser(p["E_cu"], p["E_d"])
    E = phi * E_sub + (1 - phi) * p["E_d"]
    st_cu = wp * p["E_cu"]
    a = (phi * (st_cu * p["a_cu"] + (1 - wp) * p["E_d"] * p["a_d"])
         + (1 - phi) * p["E_d"] * p["a_d"]) / (phi * (st_cu + (1 - wp) * p["E_d"])
                                               + (1 - phi) * p["E_d"])
    return {"status": "DERIVED", "elastic_type": "iso",
            "E": {"value": E, "status": "DERIVED"},
            "nu": {"value": p["nu"], "status": "ASSUMPTION"},
            "cte": {"value": a, "status": "DERIVED"},
            "k": {"value": kz, "status": "DERIVED"},
            "k_ortho": {"value": [kx, kx, kz], "status": "DERIVED"},
            "provenance": src}


class _NestedRefinement:
    """Split every in-plane interval of the base graded grid into rxy equal parts and
    every layer's through-thickness elements into rz parts, while the mesh is built.
    Every base node survives, so the result is strictly nested in the base mesh."""

    def __init__(self, rxy=1, rz=1):
        self.rxy, self.rz = int(rxy), int(rz)

    def __enter__(self):
        import etm.mesh as M
        self.M, self.g0, self.L0 = M, M._grid_1d_graded, M.Layer
        rxy, rz, g0, L0 = self.rxy, self.rz, self.g0, self.L0

        def grid(*a, **k):
            xs = g0(*a, **k)
            if rxy == 1:
                return xs
            t = np.linspace(0.0, 1.0, rxy + 1)[1:-1]
            ins = (xs[:-1, None] + np.outer(np.diff(xs), t)).ravel()
            return np.unique(np.round(np.concatenate([xs, ins]), 9))

        def layer(name, z0, z1, nz, *rest, **kw):
            return L0(name, z0, z1, nz * rz, *rest, **kw)

        M._grid_1d_graded = grid
        if rz != 1:
            M.Layer = layer
        return self

    def __exit__(self, *exc):
        self.M._grid_1d_graded, self.M.Layer = self.g0, self.L0
        return False


def refine_tag(refine):
    return "" if tuple(refine) == (1, 1) else f"_r{refine[0]}{refine[1]}"


def design_suffix():
    """'' on the production design; '_<tag>' for a non-default Z1 design."""
    return f"_{DESIGN_TAG}" if DESIGN_TAG else ""


def case_path(arch, scen, h_xy=None, refine=None):
    """The ETM case file; the production mesh unless a level is named explicitly."""
    h_xy = PRODUCTION_H_XY if h_xy is None else h_xy
    refine = PRODUCTION_REFINE if refine is None else refine
    return OUT / f"etm_{arch}{design_suffix()}_{scen}_h{h_xy}{refine_tag(refine)}.json"


def work_dir(arch, scen, h_xy, refine):
    """The scratch directory of one case (the design tag keeps a candidate apart)."""
    return WD / f"{arch}{design_suffix()}_{scen}_h{h_xy}{refine_tag(refine)}"


def current_lineage(r):
    """True for a case of the corrected lineage: the named architecture variant (direct-fed
    Z2) and the in-cell E-T temperatures of DEFECT #68. A file of an older lineage keeps its
    name until a rerun overwrites it, so a reader must check this, never the name."""
    h = (r.get("et_history") or [{}])[-1]
    return (r.get("architecture_variant") == FL.VARIANT.get(r.get("arch"))
            and "T_hs_C" in h)


def production_label():
    r = tuple(PRODUCTION_REFINE)
    base = f"graded h_xy = {PRODUCTION_H_XY} mm grid"
    if r == (1, 1):
        return base
    return (base + (f", every in-plane interval split in {r[0]}" if r[0] > 1 else "")
            + (f", every layer split in {r[1]} through the thickness" if r[1] > 1 else ""))


def build(arch, h_xy=1.1, refine=(1, 1)):
    import physical_package as PP
    import production_et as PE
    Z1D.require_z1(arch, "build")
    with _NestedRefinement(*refine):
        if arch == "Z1":
            m, mats, st, tiles = PP.build_physical_z1(h_xy=h_xy)
        elif arch == "Z3":
            # the regulator on the PCB backside, from its OWN config (configs/phase0nz)
            m, mats, st, tiles = PP.build_physical_z3(h_xy=h_xy)
        else:
            cfg = PP.load_physical_package_config(
                R / "configs/phase0nt/z2_2p4mm_cutout.yaml")
            m, mats, st, tiles = PP.build_physical_package(cfg, h_xy=h_xy)
    st = copy.deepcopy(st)
    side = tiles[0].ax
    f = tsv_tile_fraction(side)
    st["materials"]["tsv_tile"] = tsv_material(st, f)
    st["materials"]["rdl_tier"] = rdl_tier_laminate()
    cen = m.elem_centroids()
    mat = list(m.elem_material)
    n_in = n_out = 0
    for e in np.concatenate([m.elem_set(layer="sub_lower"),
                             m.elem_set(layer="tile_band")]):
        x, y = cen[e - 1][:2]
        inside = any(abs(x - t.cx) <= t.ax / 2 + 1e-9 and abs(y - t.cy) <= t.ay / 2 + 1e-9
                     for t in tiles)
        mat[e - 1] = "tsv_tile" if inside else "silicon"
        n_in += inside
        n_out += not inside
    m.elem_material = np.array(mat, dtype=object) if isinstance(
        m.elem_material, np.ndarray) else mat
    info = {"tsv_tile_cu_fraction": f, "sub_lower_in_tiles": n_in,
            "sub_lower_outside_tiles": n_out}
    if arch == "Z3":
        # the two Z3 cards, recorded with the case as the TSV card is
        import z3_package as Z3P
        z3 = PP.load_z3_package_config()
        mat_a = np.asarray(m.elem_material, dtype=object)
        vn, an = Z3P.via_material_name(z3), Z3P.attach_material_name(z3)
        info.update({"pcb_via_field_elements": int((mat_a == vn).sum()),
                     "pcb_via_cu_fraction": st["materials"][vn]["cu_area_fraction"],
                     "pcb_via_card_k_ortho": st["materials"][vn]["k_ortho"]["value"],
                     "pcb_via_card_E_MPa": st["materials"][vn]["E"]["value"],
                     "vr_attach_pcb_elements": int((mat_a == an).sum()),
                     "vr_attach_pcb_card_k_ortho": st["materials"][an]["k_ortho"]["value"],
                     "vr_attach_pcb_fraction": st["materials"][an]["geometry"]["f"]})
    # TCPMT round 3 (finding 11a): the homogenised BGA layer takes the LOCAL solder card
    # (E(T), nu, CTE of configs/tcpmt_mech solder) when bga_global.production says so;
    # the default 'board_py' keeps the STAMP-2.5D card of board.py unchanged
    if _bga_global_mode() == "local_card":
        import tcpmt_mech_variants as MV
        info.update(MV.bga_local_hook()(m, st, tiles) or {})
    for hook in BUILD_HOOKS:
        info.update(hook(m, st, tiles) or {})
    mats = PE.build_materials(st)
    return m, mats, st, tiles, info


def _bga_global_mode():
    try:
        import tcpmt_mech_laws as LAW
        return (LAW.cfg().get("bga_global") or {}).get("production", "board_py")
    except Exception:                             # config absent: the historical card
        return "board_py"


def layer_mean_T(m, Tn, layers):
    import production_et as PE
    ids = np.concatenate([PE._layer_elems(m, L) for L in layers])
    nodes = np.unique(m.elems[ids - 1].ravel())
    return float(np.nanmean(Tn[nodes - 1]))


#: which deposits are confined to the cell footprints. The physical converter
#: tiers contain OUT-OF-CELL encapsulant as well as the devices; depositing a tier's
#: loss over every element of the layer put GaN device loss into the underfill out
#: to the package corners, where it has almost no path to the cold plate, and
#: produced a 362 C hot spot at (15, 15) mm in an element carrying no device at all.
IN_TILE_KEYS = ("hs", "ls", "caps", "ind", "rdl", "lv", "tsv", "pads", "attach")
#: Z3 also confines its PCB 1 V via-field loss to the cells: the plated through-holes exist
#: only in the board under the cell footprints, so that loss goes into those board elements and
#: never into the board out to the package corners. Every other architecture keeps
#: IN_TILE_KEYS unchanged.
IN_TILE_KEYS_BY_ARCH = {"Z3": IN_TILE_KEYS + ("pcb_via",)}


def in_tile_keys(arch):
    return IN_TILE_KEYS_BY_ARCH.get(arch, IN_TILE_KEYS)


def deposits_from_ledger(arch, L):
    """(layers tuple, in_tiles) -> W. A converter row carries its per-tier split (TCPMT round
    3, final_closure_ledger.converter_rows_split): each tier's share is deposited in that tier
    alone, inside the cells, so a part's loss lands in the tier holding it."""
    lay = FL.LAYERS[arch]
    tile_layers = set(lay.get("converter", []))
    for k in in_tile_keys(arch):
        if k not in lay:
            continue
        v = lay[k]
        tile_layers.update(v if isinstance(v, list) else [v])
    dep = {((lay["die"],), False): FL.P_LOAD_W}
    for r in L["rows"]:
        if r["P_w"] <= 0:
            continue
        for layers, w in _row_regions(r):
            key = (layers, all(x in tile_layers for x in layers))
            dep[key] = dep.get(key, 0.0) + w
    return dep


def _row_regions(r):
    """[(layers tuple, W)] of one ledger row: its per-tier split when it has one, else its
    whole loss over its deposit layers."""
    sp = r.get("deposit_split")
    if sp:
        tot = sum(x["P_w"] for x in sp)
        if abs(tot - r["P_w"]) > 1e-9 * max(1.0, abs(r["P_w"])):
            raise ValueError(f"{r['term']}: deposit split {tot} W != row {r['P_w']} W")
        return [((x["layer"],), x["P_w"]) for x in sp if x["P_w"] > 0]
    return [(tuple(r["deposit_layer"].split(",")), r["P_w"])]


def _region_elems(m, layers, in_tiles, tiles):
    import production_et as PE
    ids = np.concatenate([PE._layer_elems(m, x) for x in layers])
    if not in_tiles:
        return ids
    cen = m.elem_centroids()[ids - 1]
    keep = np.zeros(len(ids), bool)
    for t in tiles:
        keep |= ((np.abs(cen[:, 0] - t.cx) <= t.ax / 2 + 1e-9)
                 & (np.abs(cen[:, 1] - t.cy) <= t.ay / 2 + 1e-9))
    return ids[keep]


#: Z3 PRODUCTION thermal boundary (configs/phase0nz/z3_board_backside.yaml, thermal_boundary).
#: Z3's converter hangs UNDER the board, so the lowest surface of the model is its high-side
#: tier and ccxio.bottom_film_faces (the bottom of m.layers[0] at the lowest z) would put the
#: board's natural-convection film on the converter. Z3 instead cools the converter underside
#: with a second cold plate of the top plate's kind -- the v_z2_cooled film form of
#: final_closure_sensitivity (top-plate h at the dissipated power, fluid at the inlet
#: temperature), promoted to production for Z3 only -- and keeps the natural-convection film
#: on the board underside wherever nothing covers it. The two face sets never overlap.
def exposed_bottom_faces(m, layer):
    """Elements of `layer` whose BOTTOM face lies on the layer's underside and is not the top
    face of any other element, i.e. faces open to the environment. Exact on the conforming
    mesh: two elements share a face if and only if they share its four nodes (element nodes
    0-3 are the bottom face, 4-7 the top face)."""
    ids = m.elem_set(layer=layer)
    zb = m.nodes[m.elems[ids - 1][:, 0] - 1, 2]
    z0 = float(zb.min())
    on = ids[np.abs(zb - z0) < 1e-9]
    zt = m.nodes[m.elems[:, 4] - 1, 2]
    covered = {tuple(sorted(r[4:])) for r in m.elems[np.abs(zt - z0) < 1e-9]}
    return np.array([e for e in on if tuple(sorted(m.elems[e - 1][:4])) not in covered], int)


def board_bottom_faces(m, arch=None):
    """The faces that carry the production natural-convection (h_bottom) film: the board's
    exposed underside. Z3's converter hangs below the board, and a Z2 converter deeper than
    the board + BGA protrudes below the board backside (TCPMT round 3, PhysicalPackage.
    cutout_fit_margin_um < 0): in both the board faces are taken, never the converter's."""
    import production_et as PE
    if arch in ("Z3", "Z2", "Z2BF"):
        return exposed_bottom_faces(m, "board")
    return PE.ccxio.bottom_film_faces(m)


def z3_converter_cold_plate(m, q_w):
    """Z3's converter-underside cold plate: the bottom faces of the DEEPEST tier, which the
    tier order makes the high-side GaN, over the whole cell-grid bbox (cells + encapsulant)."""
    deepest = min(m.layers, key=lambda L: L.z0)
    if deepest.name not in FL.LAYERS["Z3"]["hs"]:
        raise ValueError(f"the Z3 cold plate belongs on the input-end (high-side) tier, but the "
                         f"deepest layer is {deepest.name}")
    return bottom_plate_film(
        exposed_bottom_faces(m, deepest.name), deepest.name,
        "Z3 production: second top-type cold plate on the converter underside", q_w,
        tim=False)


def _film_lines(film, PE):
    """*FILM lines of a bottom-face film; a per-face sink (T_face) when the film has one."""
    t = film.get("T_face")
    t = np.full(len(film["elems"]), film["T_C"]) if t is None else np.asarray(t, float)
    return [f"{int(e)},F1,{ti:.6f},{film['h_W_m2K'] * PE.W_M2K_TO_W_MM2K:.9g}"
            for e, ti in zip(film["elems"], t)]


_UNSET = object()


def write_thermal(m, mats, st, deposits, h_face, t_face, path, tiles, arch=None,
                  plate=_UNSET, extra=_UNSET):
    """`plate` / `extra`: the Z3 converter plate and the sensitivity film, prebuilt by
    solve_thermal (so a streamwise sink can be iterated); built here when not given."""
    import production_et as PE
    ccxio = PE.ccxio
    tb = st["thermal_bc"]
    h_bot, t_amb = tb["h_bottom"]["value"], tb["ambient_bottom"]["value"]
    L = ccxio._nodes_block(m) + ccxio._elements_blocks(m, "C3D8")
    L += ccxio._fmt_set("NALL", np.arange(1, m.n_nodes + 1), "NSET")
    for mat in sorted(set(m.elem_material)):
        L += [f"*MATERIAL, NAME={mat.upper()}"] + mats[mat].ccx_conductivity()
        L += [f"*SOLID SECTION, ELSET=E_{mat.upper()}, MATERIAL={mat.upper()}"]
    V = m.elem_volumes()
    dflux, deposited, k = [], 0.0, 0
    for (layers, in_tiles), w in deposits.items():
        ids = _region_elems(m, layers, in_tiles, tiles)
        vol = V[ids - 1].sum()
        if vol <= 0:
            raise PE.EnergyError(f"{layers} has no meshed volume for {w} W")
        k += 1
        L += ccxio._fmt_set(f"E_SRC_{k}", ids)
        dflux.append(f"E_SRC_{k},BF,{w / vol:.9g}")
        deposited += (w / vol) * vol
    top, bot = ccxio.top_film_faces(m), board_bottom_faces(m, arch)
    L += ["*INITIAL CONDITIONS, TYPE=TEMPERATURE", f"NALL,{float(t_face.mean()):.6f}"]
    L += ["*STEP", "*HEAT TRANSFER, STEADY STATE", "*DFLUX"] + dflux + ["*FILM"]
    for e, h_i, t_i in zip(top, h_face, t_face):
        L.append(f"{int(e)},F2,{t_i:.6f},{h_i * PE.W_M2K_TO_W_MM2K:.9g}")
    for e in bot:
        L.append(f"{int(e)},F1,{t_amb},{h_bot * PE.W_M2K_TO_W_MM2K:.9g}")
    if plate is _UNSET:
        plate = z3_converter_cold_plate(m, sum(deposits.values())) if arch == "Z3" else None
    if plate is not None:
        if set(map(int, plate["elems"])) & set(map(int, bot)):
            raise ValueError("Z3 converter cold-plate faces overlap the board-bottom film")
        L += _film_lines(plate, PE)
    if extra is _UNSET:
        extra = EXTRA_FILM(m, tiles, sum(deposits.values())) if EXTRA_FILM else None
    if extra is not None:
        if set(map(int, extra["elems"])) & set(map(int, bot)):
            raise ValueError("extra film faces overlap the board-bottom film")
        if plate is not None and set(map(int, extra["elems"])) & set(map(int, plate["elems"])):
            raise ValueError("extra film faces overlap the Z3 converter cold plate")
        L += _film_lines(extra, PE)
    L += ["*NODE FILE", "NT", "*END STEP"]
    path.write_text("\n".join(L) + "\n")
    return {"top": top, "bot": bot, "deposited_w": deposited,
            "h_bot": h_bot, "t_amb": t_amb, "extra": extra, "plate": plate}


def film_heat_w(m, Tn, film):
    """Heat leaving through one convective face set, COMPUTED from the solved field (the
    bottom-face node mean against the film's sink)."""
    return float(np.sum(film_face_heat(m, Tn, film)))


def film_face_heat(m, Tn, film):
    """Per-face heat (W) leaving through a bottom-face film, from the solved field, against
    the film's per-face sink when it has one."""
    import production_et as PE
    t = np.array([float(np.nanmean(Tn[m.elems[int(e) - 1][:4], 0])) for e in film["elems"]])
    a = np.array([PE.ccxio.face_area(m, e) for e in film["elems"]])
    sink = film.get("T_face")
    sink = film["T_C"] if sink is None else np.asarray(sink, float)
    return film["h_W_m2K"] * PE.W_M2K_TO_W_MM2K * a * (t - sink)


def solve_thermal(m, mats, st, deposits, wd, tiles, max_fluid_iter=8, tol_k=0.02, arch=None):
    import production_et as PE
    from cooling_production import CANDIDATES
    ccxio = PE.ccxio
    wd.mkdir(parents=True, exist_ok=True)
    cooler = CANDIDATES[COOLER]
    Q = sum(deposits.values())
    top = ccxio.top_film_faces(m)
    cen = np.array([m.elem_centroids()[int(e) - 1] for e in top])
    areas = np.array([ccxio.face_area(m, e) for e in top])
    h_face = np.full(len(top), top_plate_h(cooler, Q))
    if TOP_FILM_HOOK is not None:
        h_face = np.asarray(TOP_FILM_HOOK(m, top, h_face), float)
    m_dot = cooler.m_dot_g_s * 1e-3 * (2.0 if cooler.two_sided else 1.0)
    order = np.argsort(cen[:, 0])
    frac = np.zeros(len(top))
    frac[order] = (np.cumsum(areas[order]) - 0.5 * areas[order]) / areas.sum()
    t_face = cooler.t_in_c + frac * Q / (m_dot * PE.CP_F)
    # the bottom films, built ONCE so a sized plate's streamwise sink can be iterated
    plate = z3_converter_cold_plate(m, Q) if arch == "Z3" else None
    extra = EXTRA_FILM(m, tiles, Q) if EXTRA_FILM else None
    swept = []
    for f in (plate, extra):
        if f is not None and f.get("streamwise"):
            xb = np.array([m.nodes[m.elems[int(e) - 1][:4] - 1][:, 0].mean()
                           for e in f["elems"]])
            ab = np.array([ccxio.face_area(m, e) for e in f["elems"]])
            ob = np.argsort(xb)
            fb = np.zeros(len(ab))
            fb[ob] = (np.cumsum(ab[ob]) - 0.5 * ab[ob]) / ab.sum()
            # first guess: the top plate's full rise spread over the plate's own area
            f["T_face"] = f["T_C"] + fb * Q / (m_dot * PE.CP_F)
            f["_order"] = ob
            swept.append(f)
    hist, t0 = [], time.time()
    for it in range(max_fluid_iter):
        ti = wd / f"th_{it}.inp"
        info = write_thermal(m, mats, st, deposits, h_face, t_face, ti, tiles, arch=arch,
                             plate=plate, extra=extra)
        ccxio.run_ccx(ti, threads=THREADS)
        frd = wd / f"th_{it}.frd"
        if not frd.is_file():
            raise RuntimeError(f"CalculiX produced no result for {ti}")
        Tn = ccxio.read_frd(frd)["NDTEMP"]
        Tnode = Tn[1:m.n_nodes + 1, 0]
        ts = np.array([float(np.nanmean(Tn[m.elems[int(e) - 1][4:], 0])) for e in top])
        q_face = h_face * PE.W_M2K_TO_W_MM2K * areas * (ts - t_face)
        q_up = np.zeros_like(q_face)
        q_up[order] = np.cumsum(q_face[order]) - 0.5 * q_face[order]
        t_new = cooler.t_in_c + q_up / (m_dot * PE.CP_F)
        dmax = float(np.max(np.abs(t_new - t_face)))
        # equal-rise rule: every sized plate's coolant rises by the top plate's dT
        dt_top = float(q_face.sum()) / (m_dot * PE.CP_F)
        new_sw = []
        for f in swept:
            qb = film_face_heat(m, Tn, f)
            ob = f["_order"]
            if qb.sum() > 1e-9:
                cum = np.zeros_like(qb)
                cum[ob] = np.cumsum(qb[ob]) - 0.5 * qb[ob]
                tb = f["T_C"] + dt_top * cum / qb.sum()
            else:
                tb = np.full(len(qb), f["T_C"])
            dmax = max(dmax, float(np.max(np.abs(tb - f["T_face"]))))
            new_sw.append(tb)
        hist.append({"iter": it, "max_dT_fluid_K": dmax, "T_max_C": float(np.nanmax(Tnode))})
        # stop BEFORE relaxing, so the recorded sinks are those of the last solved field
        if dmax < tol_k or it == max_fluid_iter - 1:
            break
        t_face = 0.5 * t_face + 0.5 * t_new
        # a sized plate's sink depends only weakly on its own flux shape (the rise is set by
        # the top plate): direct substitution, no under-relaxation (with 0.5 the area-weighted
        # first guess, ~1.4 K off on Z1 cooling B, needed the full 8 coolant passes)
        for f, tb in zip(swept, new_sw):
            f["T_face"] = tb
    # the bottom heat flow, COMPUTED from the solved field
    bot = info["bot"]
    tb = np.array([float(np.nanmean(Tn[m.elems[int(e) - 1][:4], 0])) for e in bot])
    ab = np.array([ccxio.face_area(m, e) for e in bot])
    q_bot = float(np.sum(info["h_bot"] * PE.W_M2K_TO_W_MM2K * ab * (tb - info["t_amb"])))
    q_top = float(q_face.sum())
    out = {"T_node": Tnode, "T_max_C": float(np.nanmax(Tnode)),
           "T_mean_C": float(np.nanmean(Tnode)), "q_top_W": q_top, "q_bot_W": q_bot,
           "Q_deposited_W": info["deposited_w"], "Q_ledger_W": Q,
           "deposit_residual_rel": (info["deposited_w"] - Q) / Q,
           "energy_residual_rel": (q_top + q_bot - Q) / Q,
           "fluid_iters": len(hist), "fluid_hist": hist,
           "wall_s": time.time() - t0, "n_elems": m.n_elems, "n_nodes": m.n_nodes,
           **die_stats(m, Tnode, arch)}
    q_known = q_top + q_bot

    def film_record(f):
        r = {k: v for k, v in f.items() if k not in ("elems", "T_face", "_order")}
        if f.get("T_face") is not None:
            r["T_sink_min_C"] = float(np.min(f["T_face"]))
            r["T_sink_max_C"] = float(np.max(f["T_face"]))
        return r
    pl = info.get("plate")
    if pl is not None:                    # Z3 production: the converter cold plate's heat
        q_p = film_heat_w(m, Tn, pl)      # flow, computed from the solved field as well
        q_known = q_known + q_p
        out.update({"q_bottom_plate_W": q_p,
                    "bottom_plate_film": film_record(pl),
                    "bottom_plate_faces": int(len(pl["elems"])),
                    "board_bottom_film_faces": int(len(bot)),
                    "energy_residual_rel": (q_known - Q) / Q})
    ex = info.get("extra")
    q_x = None
    if ex is not None:                    # sensitivity only: the extra film's heat flow,
        q_x = film_heat_w(m, Tn, ex)      # computed from the solved field too
        out.update({"q_extra_W": q_x, "extra_film": film_record(ex),
                    "extra_film_faces": int(len(ex["elems"])),
                    "energy_residual_rel": (q_known + q_x - Q) / Q})
    out["cooling"] = plate_records(cooler, q_top, [(pl, out.get("q_bottom_plate_W")),
                                                   (ex, q_x)])
    return out


def plate_records(cooler, q_top, films):
    """Every cold plate of the solved case: flow, coolant rise, film coefficient, pressure
    drop and pumping AT ITS OWN FLOW (the top plate at the production flow; a second plate
    by the declared BOTTOM_PLATE_RULE). Natural-convection films are not plates."""
    import cooling as C
    from cooling_production import ETA_PUMP_BAND
    m_top = cooler.m_dot_g_s * (2.0 if cooler.two_sided else 1.0)
    top = cooler.plate_at_flow(m_top, q_top)
    top.update(name="top", coefficient=TOP_PLATE_COEFF,
               h_film_W_m2K=top_plate_h(cooler, q_top))
    plates = [top]
    for f, q in films:
        if f is None or not f.get("plate") or q is None:
            continue
        if f.get("rule") == "equal_rise":
            from cooling_production import equal_rise_flow_g_s
            m_b = equal_rise_flow_g_s(q, q_top, m_top)
        else:
            m_b = cooler.m_dot_g_s
        rec = cooler.plate_at_flow(m_b, q)
        rec.update(name=f.get("layer"), rule=f.get("rule"), label=f.get("label"),
                   h_film_W_m2K=f["h_W_m2K"], R_tim_m2K_W=f.get("R_tim_m2K_W"))
        plates.append(rec)
    tot = sum(p.get("P_pump_hydraulic_W", 0.0) for p in plates)
    return {"top_plate_coefficient": TOP_PLATE_COEFF, "bottom_plate_rule": BOTTOM_PLATE_RULE,
            "nu_model": C.NU_MODEL, "props_model": C.PROPS_MODEL,
            "wall_viscosity": C.WALL_VISCOSITY, "plates": plates,
            "P_pump_hydraulic_total_W": tot,
            "P_pump_shaft_total_W": {f"{e:.2f}": tot / e for e in ETA_PUMP_BAND}}


def temperature_regions(arch):
    """Ledger temperature key -> (layers, in_tiles): the region whose node mean sets the
    resistance (or the device on-resistance) of the terms that key controls. It contains
    the region those terms deposit their heat in (deposits_from_ledger, IN_TILE_KEYS) --
    each device tier exactly; the converter's internal metal, deposited in its RDL tiers,
    at the in-cell mean of all converter tiers it connects -- so a conductor's resistance
    is evaluated where its loss is produced, never over another region. DEFECT #68: the
    converter key used to average every node of the converter tiers, encapsulant included,
    while the device losses were deposited only inside the 49 cells -- 7.8 K below the
    in-cell mean for the direct-fed Z2 and 1.2 K above it for Z1 at HV-S0."""
    lay = FL.LAYERS[arch]
    # every converter tier (a mixed tier holds several classes) and the RDL tiers
    conv_layers = list(lay["converter"]) + lay["rdl"]
    reg = {"conv": (conv_layers, True),
           "hs": (list(lay["hs"]), True), "ls": (list(lay["ls"]), True),
           "ind": (list(lay["ind"]), True), "caps": (list(lay["caps"]), True),
           "bga": ([lay["bga"]], False),
           "sub": ([lay["tsv"]], True),
           "interface": ([lay["pads"]], True)}
    # TCPMT round 3: the in-cell temperature of EVERY converter tier -- each part's loss is
    # evaluated at the tier holding it and deposited there (converter_rows_split)
    for ln in lay["converter"]:
        reg[f"tier:{ln}"] = ([ln], True)
    if "attach" in lay:
        reg["attach"] = ([lay["attach"]], True)
    if "pcb_via" in lay:                  # Z3: the board elements under the cells (via fields)
        reg["pcb_via"] = ([lay["pcb_via"]], True)
    return reg


def region_nodes(m, tiles, layers, in_tiles):
    """1-based node ids of the elements of `layers` (inside the cell footprints if asked)."""
    ids = _region_elems(m, layers, in_tiles, tiles)
    return np.unique(m.elems[ids - 1].ravel())


def temps_from_history(h):
    """The ledger temperatures of one recorded E-T iteration (keys present in it), the
    per-tier keys (T_tier:<layer>_C) included."""
    out = {k: h[f"T_{k}_C"] for k in ("conv", "hs", "ls", "ind", "caps", "bga", "sub",
                                        "interface", "attach", "pcb_via") if f"T_{k}_C" in h}
    out.update({k[2:-2]: v for k, v in h.items() if k.startswith("T_tier:") and
                k.endswith("_C")})
    return out


def run_et(arch, scen, h_xy=1.1, refine=(1, 1)):
    t0 = time.time()
    m, mats, st, tiles, minfo = build(arch, h_xy, refine)
    lay = FL.LAYERS[arch]
    regions = {k: region_nodes(m, tiles, *v) for k, v in temperature_regions(arch).items()}
    temps = {k: (60.0 if k == "bga" else 85.0) for k in regions}
    hist, th, L = [], None, None
    wd = work_dir(arch, scen, h_xy, refine)
    for it in range(ET_MAX_ITER):
        L = FL.self_consistent(arch, scen, temps)
        dep = deposits_from_ledger(arch, L)
        if EXTRA_DEPOSITS is not None:
            for key, w in EXTRA_DEPOSITS(arch, scen, L).items():
                dep[key] = dep.get(key, 0.0) + w
        th = solve_thermal(m, mats, st, dep, wd / f"et{it}", tiles, arch=arch)
        Tn = th["T_node"]
        new = {k: float(np.nanmean(Tn[nd - 1])) for k, nd in regions.items()}
        d_t = max(abs(new[k] - temps[k]) for k in temps)
        d_p = (abs(L["P_loss_w"] - hist[-1]["P_loss_w"]) / L["P_loss_w"]) if hist else 1.0
        hist.append({"iter": it, "P_loss_w": L["P_loss_w"], "T_max_C": th["T_max_C"],
                     "T_die_mean_C": layer_mean_T(m, Tn, [lay["die"]]),
                     "die_T_max_C": th["die_T_max_C"],
                     **{f"T_{k}_C": v for k, v in new.items()},
                     "max_dT_K": d_t, "dP_rel": d_p,
                     "energy_residual_rel": th["energy_residual_rel"],
                     "wall_s": th["wall_s"]})
        temps = new
        print(f"  {arch} {scen} it{it}: Ploss={L['P_loss_w']:.3f} W Tmax={th['T_max_C']:.2f} "
              f"dT={d_t:.3f} K residual={th['energy_residual_rel']:+.2e}", flush=True)
        if d_t < ET_TOL_K and d_p < ET_TOL_P_REL:
            break
    t_et = time.time() - t0
    record_region_maxima(m, th, arch, tiles)
    return m, mats, st, tiles, minfo, L, th, hist, t_et, wd


def record_region_maxima(m, th, arch, tiles):
    """TCPMT review round 2: the component- and material-region maxima of the converged field
    (device tiers in the cells, die, encapsulant, build-up, board; tcpmt_region_temps), kept in
    the case's thermal record for the feasibility stage. Recorded, never fatal."""
    try:
        import tcpmt_region_temps as RT
        th["region_T_max_C"] = RT.region_maxima(m, th["T_node"], arch, tiles)
    except Exception as e:                                   # noqa: BLE001 -- recorded
        th["region_T_max_C"] = {"error": str(e)[-300:]}


def joint_search(m, U, Tn, arch, tiles):
    """In-plane relative displacement across the BGA layer at EVERY legal site."""
    from scipy.interpolate import LinearNDInterpolator
    import physical_coords as PCO
    import pkg_rdl_network as K
    zl = {L.name: (L.z0, L.z1) for L in m.layers}
    z0, z1 = zl["bga"]
    nb, nt = m.node_ids_at_z(z0), m.node_ids_at_z(z1)
    pb, pt = m.nodes[nb - 1][:, :2], m.nodes[nt - 1][:, :2]
    ub = LinearNDInterpolator(pb, U[nb, :2])
    ut = LinearNDInterpolator(pt, U[nt, :2])
    tb = LinearNDInterpolator(pb, Tn[nb - 1])
    sites = PCO.bga_lattice_sites(K.architecture_cutout_mm(arch))
    S = np.array(sites)
    dub, dut, tt = ub(S), ut(S), tb(S)
    du = np.hypot(dut[:, 0] - dub[:, 0], dut[:, 1] - dub[:, 1]) * 1000.0
    ok = np.isfinite(du)
    order = np.argsort(-np.where(ok, du, -1))
    ranked = [{"rank": i + 1, "x_mm": float(S[j, 0]), "y_mm": float(S[j, 1]),
               "du_um": float(du[j]), "T_C": float(tt[j])}
              for i, j in enumerate(order[:ok.sum()])]
    return {"n_sites": int(len(S)), "n_evaluated": int(ok.sum()), "ranked": ranked,
            "critical": ranked[0] if ranked else None}


def interconnect_kinematics(m, U, Tn, mats, st, arch, js):
    """Findings 2, 4, 9: every interconnect layer's site search (driver |du_xy| / h), the
    cut-boundary kinematics of its candidate sites (the v2 local submodel's boundary
    conditions), and the membrane / bending split of du at the BGA maximum-du site."""
    import pkg_rdl_network as K
    import tcpmt_mech_kinematics as KIN
    cut = K.architecture_cutout_mm(arch) if arch != "Z3" else None
    res = {"interconnects": KIN.interconnect_search(m, U, Tn, arch, cut)}
    c = (js or {}).get("critical")
    if c:
        t_ref = st["structural_bc"]["t_ref"]["value"]
        res["decomposition_bga_critical"] = KIN.decompose_site(m, U, Tn, mats, c["x_mm"],
                                                               c["y_mm"], t_ref=t_ref)
    return res


def mechanics(m, mats, st, Tn, wd, arch, tiles, solver="", threads=None):
    import production_et as PE
    ccxio = PE.ccxio
    t0 = time.time()
    si = wd / "structural.inp"
    wd.mkdir(parents=True, exist_ok=True)
    info = ccxio.write_structural(m, mats, Tn, st, STRUCT_BC, si, solver=solver,
                                  bc_params=STRUCT_PARAMS,
                                  loads=STRUCT_LOADS(m) if STRUCT_LOADS else None)
    ccxio.run_ccx(si, threads=threads or THREADS)
    sres = ccxio.read_frd(si.with_suffix(".frd"))
    sm = PE.metrics.structural_metrics(m, sres["DISP"], sres["STRESS"], st)
    js = joint_search(m, sres["DISP"], Tn, arch, tiles)
    out = {"die_warpage_pv_um": sm["die_warpage_pv_um"],
           "pkg_warpage_pv_um": sm.get("pkg_warpage_pv_um"),
           "joint_search": js, "wall_s": time.time() - t0,
           "structural_solver": solver or "SPOOLES",
           "structural_threads": threads or THREADS}
    if STRUCT_BC != "BC_BOARD" or STRUCT_LOADS:
        out["structural_bc"] = {k: v for k, v in info.items() if k != "anchor_coords"}
    if INTERCONNECT_SEARCH:
        try:
            out.update(interconnect_kinematics(m, sres["DISP"], Tn, mats, st, arch, js))
        except Exception as e:                    # recorded, never silently dropped
            out["interconnect_error"] = str(e)[-600:]
    return out


def _raise_stack_limit():
    """CalculiX segfaults (rc = -11) on the finer structural models under the default
    8 MB stack; solver subprocesses inherit this limit from the worker."""
    import resource
    try:
        resource.setrlimit(resource.RLIMIT_STACK,
                           (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
    except (ValueError, OSError):
        soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
        resource.setrlimit(resource.RLIMIT_STACK, (hard, hard))
    os.environ.setdefault("OMP_STACKSIZE", "512M")


def run_case(arch, scen, h_xy=1.1, do_mech=True, refine=(1, 1), solver="", threads=None):
    """solver = "NONE" runs the E-T fixed point only (thermal mesh-convergence levels)."""
    _raise_stack_limit()
    if solver == "NONE":
        do_mech = False
    m, mats, st, tiles, minfo, L, th, hist, t_et, wd = run_et(arch, scen, h_xy, refine)
    res = {"arch": arch, "scenario": scen, "h_xy_mm": h_xy, "refine": list(refine),
           "architecture_variant": FL.VARIANT[arch], "hv_feed": FL.HV_FEED[arch],
           "external_feed": L.get("external_feed"),
           "materials": minfo,
           "ledger_rows": L["rows"], "P_loss_w": L["P_loss_w"],
           "i_hv_avg_a": L["i_hv_avg_a"], "energy_ledger": L["energy"],
           "thermal": {k: v for k, v in th.items() if k not in ("T_node",)},
           "die_T_max_C": th["die_T_max_C"], "die_T_mean_C": th["die_T_mean_C"],
           "et_history": hist, "et_converged": (hist[-1]["max_dT_K"] < ET_TOL_K
                                                and hist[-1]["dP_rel"] < ET_TOL_P_REL),
           "et_wall_s": t_et, "threads": THREADS}
    if arch == "Z3":
        # the board-backside design numbers (counts, per-bump/per-ball currents, BGA field
        # consumption) and the converged temperatures they were evaluated at
        res["z3_design"] = L["z3_design"]
        res["thermal_boundary"] = {
            "top": f"{COOLER} cold plate on the TIM (as Z1/Z2)",
            "converter_underside": th.get("bottom_plate_film"),
            "board_underside_outside_converter": "production h_bottom natural convection",
            "q_split_W": {"top": th["q_top_W"], "converter_plate": th.get("q_bottom_plate_W"),
                          "board_bottom": th["q_bot_W"]}}
    # TCPMT round 3: every case records the design it was computed with (the design record
    # entry, or a count-study candidate config); tcpmt_cases refuses a case of another design
    res["design"] = Z1D.summary()
    res["tsv_per_cell"] = TSV_N_PER_CELL
    # write THIS case now, and again after mechanics: a failure in another worker, or a
    # long structural solve, must not withhold the converged thermal state
    f = case_path(arch, scen, h_xy, refine)
    f.write_text(json.dumps(res, indent=1, default=float))
    if do_mech:
        try:
            res["mechanics"] = mechanics(m, mats, st, th["T_node"], wd, arch, tiles,
                                         solver, threads)
        except Exception as e:                    # recorded, never silently dropped
            res["mechanics_error"] = str(e)[-600:]
        f.write_text(json.dumps(res, indent=1, default=float))
    return {"arch": arch, "scenario": scen, "h_xy_mm": h_xy, "file": str(f),
            "mechanics_ok": "mechanics" in res}


def main():
    import multiprocessing as mp
    cases = [(a, s) for s in FL.SCENARIOS for a in ("Z1", "Z2")]
    if len(sys.argv) > 1:
        cases = []
        for c in sys.argv[1:]:                    # ARCH:SCEN[:H[:rXZ[:SOLVER:THREADS]]]
            a, sc, *h = c.split(":")
            args = [a, sc] + ([float(h[0])] if h else [])
            if len(h) > 1:
                args += [True, (int(h[1][1]), int(h[1][2]))]
            if len(h) > 3:
                args += [h[2], int(h[3])]
            cases.append(tuple(args))
    with mp.Pool(len(cases)) as p:
        out = p.starmap(run_case, cases)
    for r in out:
        print(f"{r['arch']} {r['scenario']} h={r['h_xy_mm']}: written {r['file']} "
              f"mechanics_ok={r['mechanics_ok']}")


if __name__ == "__main__":
    main()
