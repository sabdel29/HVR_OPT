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
    "F1_encapsulated": "underfill_homog",   # mold/underfill medium already in the stack
    "F2_void":         "VOID",              # elements are never created
}


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
    for nm, t_mm, mat, nz in reversed(converter_layers(cfg)):
        explicit.append((nm, z - t_mm, z, mat, nz, "inside_cutout"))
        z -= t_mm
    return kept, explicit, tuple(e[0] for e in explicit), OUT_OF_CELL[out_of_cell]


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
