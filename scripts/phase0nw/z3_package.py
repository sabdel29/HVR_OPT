"""PHASE 0N-Z --- Z3, the regulator on the PCB BACKSIDE (configs/phase0nz/z3_board_backside.yaml).

Z3 hangs the SAME 49-cell regulator as Z2, in the SAME tier order, from the BOARD
UNDERSIDE at Z2's cell x-y positions, so nothing of the converter descends into the board:

    TIM 50 | die 300 | ubump 10 | top RDL 10 | substrate 300 (TSV fields)          (= Z2)
    BGA 300 (FULL lattice) | board 2400 (FULL slab, 1 V vias in the cell footprints)
    VR-to-PCB attach 100 (SAC305 bumps + underfill)
    land-side RDL 10 | L + Cout 500 | RDL 10 | LS GaN 638 | RDL 10 | C_fly 100 | RDL 10 | HS GaN 685

WHY A SEQUENTIAL BOTTOM STACK. The Z2 converter shares the board's z range and is separated
from it only in plane, so it needs the explicit (absolute-z) layer path and a cutout. The Z3
converter is entirely BELOW the board, so the ordinary deepest-first sequential stack
(etm.mesh `extra_bottom_layers`) expresses it exactly; the out-of-cell rule of the mesher
(fill inside the cell-grid bbox, void outside) then applies to the converter tiers and the
attach exactly as it does to Z2's.

WHAT IS NEW MATERIAL. Two cards, both homogenised by the rules the framework already uses:
  vr_attach_pcb   z2_converter.vr_attach_material with Z3's all-solder geometry (Voigt through
                  thickness, Maxwell-Garnett in plane, underfill-dominated mechanics)
  pcb_via_field   the board card with the plated through-hole annulus mixed in (parallel rule
                  along z, Maxwell-Garnett in plane, Voigt mechanics) -- ONLY inside the 49 cell
                  footprints, the board elements under which the via fields exist
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
for _p in ("scripts/phase0nw", "scripts/phase0mr", "scripts/phase0i", "scripts/phase0g",
           "scripts/phase0b", "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))

import z2_converter as Z2C                                           # noqa: E402

#: the converter tiers carry their config index from the board DOWNWARD, as Z2's do from the
#: substrate downward; the prefix keeps them distinct from Z2's in every artifact
CONV_PREFIX = "z3conv_"
#: board.bottom_layers names; the joint search, the films and the deposits key on them
BOARD_LAYER, BGA_LAYER = "board", "bga"


def attach_layer(cfg) -> str:
    return str(cfg.attach_dict()["layer"])


def attach_material_name(cfg) -> str:
    return str(cfg.attach_dict()["card_material"])


def via_material_name(cfg) -> str:
    return str(cfg.pcb_via_dict()["card_material"])


def converter_layers(cfg, nz_thin: int = 1, nz_thick: int = 2) -> list:
    """(name, thickness_mm, material, nz) for the 8 tiers, DEEPEST FIRST (high-side GaN first).

    The config lists the tiers from the board DOWNWARD; the sequential bottom stack is laid
    deepest first, so the list is reversed here (the Phase-0N-T orientation defect is the
    reason this is stated, and tier_report audits the result on the mesh). The materials and
    the through-thickness counts are Z2's (z2_converter.TIER_MATERIAL, 1 element per RDL tier,
    2 per thick tier)."""
    out = []
    n = len(cfg.tiers)
    for i, t in enumerate(reversed(cfg.tiers)):
        mat = Z2C.tier_material(t.name)
        out.append((f"{CONV_PREFIX}{n - 1 - i:d}_{t.name}", t.um / 1e3, mat,
                    nz_thin if t.um <= 20.0 else nz_thick))
    return out


def mid_layers(cfg, nz_thin: int = 1) -> list:
    """Above the substrate top: Z2's 10 um top 1 V RDL (the loader checked the thickness
    against z2_converter.TOP_RDL_UM), under its own name so the ledger's lv key is Z2's."""
    return [("z2_top_rdl", cfg.top_rdl_um / 1e3, "rdl_tier", nz_thin, "substrate")]


# ------------------------------------------------------------------ lattices (attach machinery)
def _attach_case(cfg) -> dict:
    a = cfg.attach_dict()
    return {"d_um": float(a["diameter_um"]), "pitch_um": float(a["pitch_um"]),
            "h_cu_um": float(a["cu_height_um"]), "h_cap_um": float(a["cap_height_um"])}


def cell_side_um(cfg) -> float:
    """The footprint the attach covers: sqrt of the stated cell area, as the mesh tiles."""
    return math.sqrt(cfg.cell_area_mm2) * 1e3


def attach_lattice(cfg) -> dict:
    """The legal VR-to-PCB bump sites of ONE cell by the attach-density study's own rule
    (final_closure_vr_attach.lattice: bump inside the cell, edge clearance >= (p - d)/2,
    VDD/GND checkerboard)."""
    import final_closure_vr_attach as VA
    return VA.lattice(_attach_case(cfg), cell_side_um(cfg))


def annulus_area_um2(cfg) -> float:
    v = cfg.pcb_via_dict()
    d_in = float(v["finished_hole_um"])
    d_out = d_in + 2.0 * float(v["plating_um"])
    return math.pi / 4.0 * (d_out ** 2 - d_in ** 2)


def via_field(cfg) -> dict:
    """The PCB 1 V via field of ONE cell: via-in-pad, one plated through-hole under every
    attach bump, so its VDD/GND counts ARE the attach lattice's."""
    L = attach_lattice(cfg)
    v = cfg.pcb_via_dict()
    a_ann = annulus_area_um2(cfg)
    p = float(v["pitch_um"])
    side = cell_side_um(cfg)
    return {"n_vdd": int(L["n_vdd"]), "n_gnd": int(L["n_gnd"]), "n_total": int(L["n_total"]),
            "n_per_axis": int(L["n_per_axis"]), "A_annulus_um2": a_ann,
            "L_um": float(cfg.board_thickness_um),
            "d_finished_um": float(v["finished_hole_um"]),
            "d_drill_um": float(v["finished_hole_um"]) + 2.0 * float(v["plating_um"]),
            "pitch_um": p, "cu_fraction_unit_cell": a_ann / p ** 2,
            "cu_fraction_real_lattice": L["n_total"] * a_ann / side ** 2,
            "card_fraction_basis": str(v["card_fraction_basis"])}


def via_card_fraction(cfg) -> float:
    vf = via_field(cfg)
    return (vf["cu_fraction_unit_cell"] if vf["card_fraction_basis"] == "unit_cell"
            else vf["cu_fraction_real_lattice"])


# ------------------------------------------------------------------ material cards
def attach_material(cfg) -> dict:
    """The VR-to-PCB attach card: z2_converter.vr_attach_material, the production attach
    homogenisation, with Z3's geometry. h_cu = 0 makes the column all solder (k_col = k_SAC305
    = 57 W/mK) and the in-plane slices a single Maxwell-Garnett array of solder in underfill.
    The fraction follows the config basis: 'unit_cell' is the production Z2 convention
    (pi d^2 / 4 p^2), 'real_lattice' the finite lattice's own share of the cell."""
    a = cfg.attach_dict()
    att = {"cu_height_um": float(a["cu_height_um"]), "cap_height_um": float(a["cap_height_um"]),
           "diameter_um": float(a["diameter_um"]), "pitch_um": float(a["pitch_um"])}
    if a["card_fraction_basis"] == "real_lattice":
        att["area_fraction"] = attach_lattice(cfg)["area_fraction"]
    c = Z2C.vr_attach_material(att)
    c["provenance"] = ("Z3 VR-to-PCB attach: SAC305 solder bumps (all-solder column) + "
                       "underfill, DESIGN_CHOICE geometry; Voigt through thickness and "
                       "Maxwell-Garnett in plane as Phase 0M-R; underfill-dominated mechanics "
                       "(the production attach convention)")
    c["geometry"]["fraction_basis"] = a["card_fraction_basis"]
    return c


def pcb_via_field_material(cfg, stack: dict) -> dict:
    """The board card INSIDE the cell footprints, with the plated through-hole field mixed in.

    Thermal, by the rules the TSV field uses (etm.config.derive_tsv_homog): along z the Cu
    barrels and the board conduct in PARALLEL, k_z = f k_Cu + (1 - f) k_z,board, exact for
    aligned barrels; in plane the barrels are cylinders in the board's in-plane matrix
    (Maxwell-Garnett 2-D). The plugged core is taken as board (non-conductive fill), so only
    the annulus counts.

    Mechanical: a Voigt (iso-strain) rule on the board card -- E = f E_Cu + (1 - f) E_board,
    CTE stiffness-weighted, nu linear. It is exact along the barrels and an UPPER bound in
    plane; it is applied isotropically because the board card itself is isotropic at its
    in-plane modulus (board.board_material: the solver's ORTHO elastic card is cubic-only).
    """
    v = lambda d: d["value"] if isinstance(d, dict) else d            # noqa: E731
    f = via_card_fraction(cfg)
    b, cu = stack["materials"]["board_fr4"], stack["materials"]["copper"]
    kxy_b, _kyy, kz_b = (b["k_ortho"]["value"] if "k_ortho" in b else [v(b["k"])] * 3)
    k_cu = v(cu["k"])
    E_b, nu_b, a_b = v(b["E"]), v(b["nu"]), v(b["cte"])
    E_cu, nu_cu, a_cu = v(cu["E"]), v(cu["nu"]), v(cu["cte"])
    kz = f * k_cu + (1.0 - f) * kz_b
    kxy = Z2C._maxwell_garnett_2d(k_cu, kxy_b, f)
    E = f * E_cu + (1.0 - f) * E_b
    return {"status": "DERIVED", "elastic_type": "iso",
            "E": {"value": E, "status": "ASSUMPTION"},
            "nu": {"value": f * nu_cu + (1.0 - f) * nu_b, "status": "ASSUMPTION"},
            "cte": {"value": (f * E_cu * a_cu + (1.0 - f) * E_b * a_b) / E,
                    "status": "ASSUMPTION"},
            "k": {"value": kz, "status": "DERIVED"},
            "k_ortho": {"value": [kxy, kxy, kz], "status": "DERIVED"},
            "cu_area_fraction": f,
            "provenance": ("Z3 PCB 1 V via field (plated through-holes, via-in-pad) in the "
                           "IT-968G board card: parallel k_z, Maxwell-Garnett k_xy, Voigt "
                           "mechanics (upper bound in plane); fraction basis "
                           + str(cfg.pcb_via_dict()["card_fraction_basis"]))}


# ------------------------------------------------------------------ mesh construction
def install(cfg, stack: dict, extra_bottom: list):
    """The Z3 bottom stack, its materials and its out-of-cell rule.

    `extra_bottom` is the board + BGA stack of board.bottom_layers (deepest first). The
    converter tiers and the attach go UNDER it, deepest first, so z = 0 stays the substrate
    underside and every package coordinate is Z2's. Returns

        (sequential_bottom_layers, conv_layer_names, fill_material)

    where conv_layer_names (the 8 tiers AND the attach) take the out-of-cell rule: their own
    material inside the cells, `fill_material` between the cells inside the cell-grid bbox,
    and no element outside it.
    """
    names = [e[0] for e in extra_bottom]
    if names != [BOARD_LAYER, BGA_LAYER]:
        raise ValueError(f"Z3 hangs its converter under the board + BGA stack, got {names}")
    if abs(extra_bottom[0][1] - cfg.board_thickness_mm) > 1e-12:
        raise ValueError(f"board layer {extra_bottom[0][1]} mm differs from the Z3 config "
                         f"{cfg.board_thickness_mm} mm")
    stack["materials"]["rdl_tier"] = Z2C.rdl_tier_material()
    stack["materials"]["microbump"] = Z2C.microbump_material()
    Z2C.install_converter_cards(stack, [(t.name, t.um) for t in cfg.tiers])
    stack["materials"][attach_material_name(cfg)] = attach_material(cfg)
    stack["materials"][via_material_name(cfg)] = pcb_via_field_material(cfg, stack)
    conv = converter_layers(cfg)
    t_att = cfg.attach_um / 1e3
    # the attach takes the thick-tier element count: it carries the attach loss and every
    # watt of converter heat that leaves through the board
    att = (attach_layer(cfg), t_att, attach_material_name(cfg), 1 if cfg.attach_um <= 20.0 else 2)
    bottom = conv + [att] + list(extra_bottom)
    return bottom, tuple(c[0] for c in conv) + (att[0],), cfg.out_of_cell_fill


def check_fill_extent(cfg, extent) -> None:
    """The fill extent is the MEASURED cell-grid bbox; it must be the declared one."""
    x0, x1, y0, y1 = extent
    for a, b in ((x0, x1), (y0, y1)):
        if abs((b - a) - cfg.cell_grid_bbox_mm) > 1e-6:
            raise ValueError(f"cell-grid bbox {b - a:.6f} mm != declared "
                             f"{cfg.cell_grid_bbox_mm} mm")


def assign_via_field(cfg, m) -> int:
    """Board elements INSIDE the 49 cell footprints take the via-field card; the rest of the
    board keeps the board card. The board layer has the substrate footprint, so the mesher
    has already recorded which tile (if any) holds each of its elements."""
    mat = np.array(m.elem_material, dtype=object)
    sel = (np.asarray(m.elem_layer, dtype=object) == BOARD_LAYER) & (np.asarray(m.elem_tile) >= 0)
    mat[sel] = via_material_name(cfg)
    m.elem_material = mat
    return int(sel.sum())


def tier_report(cfg, mesh) -> list:
    """Measured z extent of every converter tier and the attach, from the MESH."""
    from physical_package import measure_layers
    lay = measure_layers(mesh)
    rows = []
    for nm, t_mm, mat, _nz in converter_layers(cfg) + [
            (attach_layer(cfg), cfg.attach_um / 1e3, attach_material_name(cfg), 0)]:
        m = lay.get(nm)
        rows.append({"tier": nm, "material": mat, "spec_um": round(t_mm * 1e3, 3),
                     "mesh_um": None if m is None else round(m["t_um"], 3),
                     "z0_um": None if m is None else round(m["z0_um"], 2),
                     "z1_um": None if m is None else round(m["z1_um"], 2)})
    return rows
