"""PHASE 0N-W --- the Z2 backside converter as 49 DISCRETE CELLS, not a full-area slab.

What was there before: one 1226 um `conv` band spanning the whole substrate footprint,
filled with `hvr_effective`. Three things wrong with it. It is the Z1 EMBEDDED-cell proxy,
which structurally EXCLUDES the high-side device. It is a slab, so 69.5 % of its volume is
converter medium sitting where there is no converter. And its height is not the specified
one.

What this builds: the eight specified tiers, totalling 1963 um, present ONLY inside the 49
cell footprints, with a declared medium outside them.

MATERIAL HONESTY. This module implements the GEOMETRY gate. It does not invent material
data to do it. Every tier maps to a medium already in the framework, and the mapping and
its status are stated here and carried into the mesh audit:

  RDL tiers        rdl_tier        DERIVED   the Phase-0M-R RDL effective tensor, RDL
                                             ALONE. It must NOT be the old
                                             composite(RDL 40 um, BUMP 10 um) blend: that
                                             folds in a microbump layer this geometry
                                             represents separately, on a thickness basis
                                             that is not the tier's.
  GaN HS and LS    silicon         BOUNDED   EPC eGaN FETs are GaN-on-Si; the 685/638 um
                                             body is predominantly the Si carrier. The
                                             thin GaN epi is NOT resolved.
  inductor + Cout  hvr_effective   PROVISIONAL  the existing homogenized converter medium,
                                             whose original meaning is exactly this blend
  flying caps      hvr_effective   OPEN      an MLCC ceramic/Ni stack is NOT this medium.
                                             No sourced MLCC card exists in the framework,
                                             so the tier is meshed at the converter medium
                                             and its material is recorded as an OPEN gate.

So: the 1963 um geometry, the 49 footprints and the explicit high-side device are
IMPLEMENTED. Per-tier material fidelity is NOT, and is not claimed to be.
"""
from __future__ import annotations

import sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for _p in ("scripts/phase0mr", "scripts/phase0i", "scripts/phase0b", "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))

# Tier name -> (framework material, status, note)
TIER_MATERIAL = {
    "land_side_attach_rdl": ("rdl_tier", "DERIVED", "Phase-0M-R RDL effective tensor, RDL ALONE"),
    "interlayer_rdl":       ("rdl_tier", "DERIVED", "Phase-0M-R RDL effective tensor, RDL ALONE"),
    "inductor_plus_cout":   ("hvr_effective", "PROVISIONAL", "existing converter medium"),
    "gan_ls_EPC2057":       ("silicon", "BOUNDED", "GaN-on-Si carrier; epi not resolved"),
    "gan_hs_EPC2014C":      ("silicon", "BOUNDED", "GaN-on-Si carrier; epi not resolved"),
    "flying_caps":          ("hvr_effective", "OPEN", "no sourced MLCC card in framework"),
}

# Out-of-cell region (brief section 15).
OUT_OF_CELL = {
    "F1_encapsulated": "underfill_homog",   # SENSITIVITY: fills the WHOLE opening, bonding the
                                            # converter to the PCB sidewall (DEFECT #66)
    "F1_clearance":    "underfill_homog",   # PRODUCTION: encapsulant between the cells only;
                                            # the 1.0 mm clearance ring to the PCB wall is void
    "F2_void":         "VOID",              # elements are never created
}
#: out-of-cell cases whose fill stops at the cell-grid bounding box (clearance ring void)
CLEARANCE_RING_VOID = {"F1_clearance"}

#: the explicit VR-to-substrate attach (Z2_DIRECT_FEED_ARCHITECTURE.md section 4)
ATTACH_LAYER = "conv_attach_vr_substrate"
#: the inputs of the validated microbump homogenisation (results/phase0mr/
#: bump_layer_effective_tensor.csv: k_matrix 0.6, solder inclusion 57 W/mK) and the
#: framework copper card (k 400 W/mK)
K_UNDERFILL, K_SOLDER, K_COPPER = 0.6, 57.0, 400.0


def _maxwell_garnett_2d(k_i, k_m, f):
    """Transverse conductivity of aligned cylinders (Maxwell-Garnett, 2-D)."""
    return k_m * ((k_i + k_m) + f * (k_i - k_m)) / ((k_i + k_m) - f * (k_i - k_m))


def vr_attach_material(att: dict, column_stiffened: bool = False) -> dict:
    """Card of the Cu-pillar + solder-cap + underfill attach, homogenised by the method
    Phase 0M-R validated for the existing microbump row (Voigt through thickness, within
    0.55 % of an explicit RVE; Maxwell-Garnett in plane, within 0.61 %).

    Through thickness each pillar is Cu (h_cu) and solder (h_cap) in SERIES; columns and
    underfill act in PARALLEL. In plane each z-slice is a Maxwell-Garnett array of its own
    inclusion, and the slices act in parallel. The MECHANICAL card follows the convention of
    the existing `microbump` card (underfill-dominated: E 8 GPa, nu 0.32, CTE 30 ppm/K);
    `column_stiffened=True` gives the Voigt (column-carried) bound used as a class-B case.
    """
    import math
    h_cu, h_cap = float(att["cu_height_um"]), float(att["cap_height_um"])
    h = h_cu + h_cap
    f = math.pi * (float(att["diameter_um"]) / 2.0) ** 2 / float(att["pitch_um"]) ** 2
    k_col = h / (h_cu / K_COPPER + h_cap / K_SOLDER)
    kz = f * k_col + (1.0 - f) * K_UNDERFILL
    kxy = (h_cu * _maxwell_garnett_2d(K_COPPER, K_UNDERFILL, f)
           + h_cap * _maxwell_garnett_2d(K_SOLDER, K_UNDERFILL, f)) / h
    E, nu, cte = 8000.0, 0.32, 30.0e-6
    if column_stiffened:
        e_cu, e_sol, cte_cu, cte_sol = 110000.0, 50000.0, 16.66e-6, 22.0e-6
        e_col = h / (h_cu / e_cu + h_cap / e_sol)
        cte_col = (h_cu * cte_cu + h_cap * cte_sol) / h
        E_v = f * e_col + (1.0 - f) * E
        cte = (f * e_col * cte_col + (1.0 - f) * E * cte) / E_v
        E = E_v
    return {"status": "DERIVED", "elastic_type": "iso",
            "E": {"value": E, "status": "DERIVED"},
            "nu": {"value": nu, "status": "ASSUMPTION"},
            "cte": {"value": cte, "status": "DERIVED"},
            "k": {"value": kz, "status": "DERIVED"},
            "k_ortho": {"value": [kxy, kxy, kz], "status": "DERIVED"},
            "provenance": ("Cu pillar + solder cap + underfill (Au et al. ECTC 2016 geometry, "
                           "CLOSE_ANALOG), Voigt/Maxwell-Garnett as Phase 0M-R"),
            "geometry": {"f": f, "h_um": h, "h_cu_um": h_cu, "h_cap_um": h_cap,
                         "column_stiffened": column_stiffened}}


def rdl_tier_material() -> dict:
    """The RDL tensor ITSELF, for the explicit 10 um converter RDL tiers.

    THIS REPLACES A WRONG MAPPING. The first version called
    rdl_mechanical.composite(RDL.t_um=40, BUMP.t_um=10), which blends a 40 um RDL with a
    10 um microbump/underfill layer. Applying that blend to a nominal 10 um RDL tier is
    wrong twice: the thickness basis is not the tier's, and it folds in a microbump layer
    that this geometry represents SEPARATELY. The two media must not be merged when the
    mesh already carries them apart.

    Source: `RDL` in scripts/phase0mr/rdl_mechanical.py, whose provenance is
    results/phase0mr/rdl_effective_tensor.csv, ORTHOGONAL routing at t_diel = 5 um --
    the Phase-0M-R RDL homogenization. Orthotropic: k_x = k_y >> k_z.
    """
    import rdl_mechanical as RM
    r = RM.RDL
    return {"status": "DERIVED", "elastic_type": "iso",
            "E": {"value": r["E_MPa"], "status": "DERIVED"},
            "nu": {"value": r["nu"], "status": "ASSUMPTION"},
            "cte": {"value": r["cte"], "status": "DERIVED"},
            "k": {"value": r["k_z"], "status": "DERIVED"},
            "k_ortho": {"value": [r["k_x"], r["k_y"], r["k_z"]], "status": "DERIVED"},
            "provenance": r["src"]}


def microbump_material() -> dict:
    """The microbump + underfill layer, kept SEPARATE from the RDL tiers.

    Source: `BUMP` in scripts/phase0mr/rdl_mechanical.py, from
    results/phase0mr/bump_layer_effective_tensor.csv, microbump_underfill. Note k_z
    (11.7 W/mK, the copper bumps conducting through) greatly exceeds k_x (0.89, the
    underfill in plane) -- the opposite anisotropy to an RDL, which is precisely why
    blending the two into one medium destroys both.
    """
    import rdl_mechanical as RM
    b = RM.BUMP
    return {"status": "DERIVED", "elastic_type": "iso",
            "E": {"value": b["E_MPa"], "status": "DERIVED"},
            "nu": {"value": b["nu"], "status": "ASSUMPTION"},
            "cte": {"value": b["cte"], "status": "DERIVED"},
            "k": {"value": b["k_z"], "status": "DERIVED"},
            "k_ortho": {"value": [b["k_x"], b["k_y"], b["k_z"]], "status": "DERIVED"},
            "provenance": b["src"]}


def converter_layers(cfg, nz_thin: int = 1, nz_thick: int = 2) -> list:
    """(name, thickness_mm, material, nz) for the 8 tiers, DEEPEST FIRST.

    The config lists tiers from the substrate DOWNWARD (land-side RDL first, high-side
    device last). `extra_bottom_layers` is laid down deepest-first, so the list is
    reversed here -- getting this backwards is what produced the Phase-0N-T defect where
    the HVR was drawn growing upward out of the package.
    """
    out = []
    for i, t in enumerate(reversed(cfg.tiers)):
        mat, _st, _n = TIER_MATERIAL[t.name]
        nz = nz_thin if t.um <= 20.0 else nz_thick
        # names must be unique per layer: four tiers share the name "interlayer_rdl"
        out.append((f"conv_{len(cfg.tiers)-1-i:d}_{t.name}", t.um / 1e3, mat, nz))
    return out


def install(cfg, stack: dict, extra_bottom: list, out_of_cell: str = "F1_encapsulated"):
    """Replace the full-area `conv` slab with the discrete 8-tier stack IN THE CUTOUT.

    The converter does not stack in series below the BGA. It descends INTO the PCB
    opening, so it shares a z range with the board and the BGA and is separated from them
    only in plane. Returns

        (sequential_bottom_layers, explicit_bottom_layers, conv_layer_names, fill)

    where the sequential list keeps board + BGA (so the PCB backside and the BGA stay at
    their specified coordinates) and the explicit list carries the tiers at absolute z
    with region 'inside_cutout'.
    """
    if out_of_cell not in OUT_OF_CELL:
        raise ValueError(f"unknown out-of-cell case {out_of_cell!r}")
    if cfg.cutout_mm is None:
        raise ValueError("a backside converter needs a cutout to descend into")
    stack["materials"]["rdl_tier"] = rdl_tier_material()
    stack["materials"]["microbump"] = microbump_material()
    att = dict(getattr(cfg, "attach", ()) or ())
    t_att = float(getattr(cfg, "attach_um", 0.0) or 0.0) / 1e3
    if t_att > 0:
        stack["materials"]["vr_attach"] = vr_attach_material(att)
    kept = [e for e in extra_bottom if e[0] != "conv"]
    if len(kept) == len(extra_bottom):
        raise ValueError("no full-area 'conv' layer found to replace")

    # z = 0 is the substrate underside; the converter hangs downward from it.
    # Lay the tiers downward from the substrate underside IN CONFIG ORDER, i.e. the
    # land-side attach RDL first (it attaches TO the substrate) and the high-side device
    # last (it is deepest into the cutout). converter_layers() returns deepest-first for
    # the sequential-stack convention, so it is walked in reverse here. Getting this
    # round the wrong way puts the HS against the substrate and the land-side RDL at the
    # bottom of the hole -- the mesh still totals 1963 um, so only a per-tier coordinate
    # audit catches it.
    explicit, z = [], 0.0
    if t_att > 0:
        # the explicit VR-to-substrate attach: between the substrate underside (z = 0) and
        # the converter's land-side (1 V output/attach) RDL. It carries only the 1 V
        # supply/return of each cell and takes the out-of-cell rule of the other tiers.
        explicit.append((ATTACH_LAYER, -t_att, 0.0, "vr_attach", 1, "inside_cutout"))
        z = -t_att
    for nm, t_mm, mat, nz in reversed(converter_layers(cfg)):
        explicit.append((nm, z - t_mm, z, mat, nz, "inside_cutout"))
        z -= t_mm
    return (kept, explicit, tuple(e[0] for e in explicit), OUT_OF_CELL[out_of_cell],
            out_of_cell in CLEARANCE_RING_VOID)


# Above the substrate, Z2 carries a 10 um top RDL (1 V + ground plane) between the
# substrate top and the microbumps -- specified table, 3000 -> 3010 um. It is NOT part of
# the 1963 um land-side converter. Omitting it let the production `interface` layer stand
# in for the RDL, which silently dropped the microbump row and put the package top at
# 3360 instead of 3370 um.
TOP_RDL_UM = 10.0


def mid_layers(nz_thin: int = 1) -> list:
    """(name, thickness_mm, material, nz, footprint) above the substrate top."""
    return [("z2_top_rdl", TOP_RDL_UM / 1e3, "rdl_tier", nz_thin, "substrate")]


def tier_report(cfg, mesh) -> list:
    """Measured z extent of every converter tier, from the MESH (brief section 14)."""
    from physical_package import measure_layers
    lay = measure_layers(mesh)
    rows = []
    for nm, t_mm, mat, _nz in converter_layers(cfg):
        m = lay.get(nm)
        rows.append({"tier": nm, "material": mat,
                     "spec_um": round(t_mm * 1e3, 3),
                     "mesh_um": None if m is None else round(m["t_um"], 3),
                     "z0_um": None if m is None else round(m["z0_um"], 2),
                     "z1_um": None if m is None else round(m["z1_um"], 2)})
    return rows


# =======================================================================================
# SECTION 14 --- IS THE 40 um RDL TENSOR TRANSFERABLE TO A 10 um TIER?
#
# NO. It is a STACK-LEVEL effective property, not a thickness-independent material.
#
# results/phase0mr/rdl_effective_tensor.csv computes a FOUR-METAL-LAYER unit cell (10 um
# Cu lines separated by t_diel dielectric). Its own sweep shows the dependence directly,
# for the ORGANISATION the physical path uses:
#
#   t_diel   stack h   f_Cu     k_x      k_z      E_x
#     2 um     46 um   0.725   140.59    2.459   66503 MPa
#     5 um     55 um   0.606   117.63    1.236   57251 MPa     <- the adopted row
#    10 um     70 um   0.476    92.49    0.801   48424 MPa
#
# k_x varies by 1.5x and k_z by 3.1x across that bracket, so the tensor plainly depends
# on the construction, not only on the material.
#
# A SECOND INCONSISTENCY. rdl_mechanical.RDL records t_um = 40.0, but the source row's
# stack_height_um is 55.0 -- 40 um counts only the four 10 um metal layers and omits the
# dielectric between them. So the "40 um" label does not even describe the cell the
# tensor came from.
#
# The explicit converter interlayer RDLs are 10 um TOTAL. That is not four metal layers
# plus dielectric; it is a thin single-layer RDL whose unit cell does not exist in the
# Phase-0M-R sweep. Recomputing it would need a new homogenization, which this phase does
# not do. So the tensor is carried with the sweep's own bracket as a BOUNDED sensitivity,
# and the gate stays open until either the recomputation or a demonstrated insensitivity.
# =======================================================================================

RDL_TRANSFER_STATUS = "BOUNDED"


def rdl_tensor_bracket() -> dict:
    """The ORTHOGONAL tensor across the available t_diel sweep, as a bounded range."""
    import csv
    rows = [r for r in csv.DictReader(
        (R / "results" / "phase0mr" / "rdl_effective_tensor.csv").open())
        if r["organisation"] == "ORTHOGONAL"]
    f = lambda k: [float(r[k]) for r in rows]                        # noqa: E731
    return {
        "organisation": "ORTHOGONAL",
        "adopted_t_diel_um": 5.0,
        "source_stack_height_um": 55.0,
        "recorded_t_um_in_code": 40.0,
        "label_inconsistency": ("rdl_mechanical.RDL says t_um = 40 (metal only) while "
                                "the source row's stack_height_um is 55 (metal + "
                                "dielectric)"),
        "tier_thickness_um": 10.0,
        "transferable": False,
        "reason": ("a four-metal-layer stack property applied to a 10 um single-layer "
                   "tier; the sweep shows k_x varying 1.5x and k_z 3.1x with "
                   "construction"),
        "k_x_range": [min(f("k_x")), max(f("k_x"))],
        "k_z_range": [min(f("k_z")), max(f("k_z"))],
        "E_MPa_range": [min(f("E_x_MPa")), max(f("E_x_MPa"))],
        "cte_range": [min(f("CTE_x")), max(f("CTE_x"))],
        "f_cu_range": [min(f("f_cu")), max(f("f_cu"))],
        "status": RDL_TRANSFER_STATUS,
    }
