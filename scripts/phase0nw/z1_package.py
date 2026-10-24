"""PHASE 0N-W --- the complete physical Z1 (brief section 17).

The historical Z1 is a 1.30 mm substrate whose top 1.226 mm is a homogenized `hvr_effective`
band -- one medium standing in for the whole converter, with no high-side device anywhere
in the geometry. That is the proxy whose height (1226 um) structurally EXCLUDES the HS.

The specified Z1 (research/Z1_Z2_PHYSICALLY_SPECIFIED_STACKS.md section 1) is a 300 um
bottom substrate carrying a stacked converter beneath the compute die:

    PCB 2400 | BGA 300 | bottom substrate 300 | <converter 1973> | ubump 10 | die 300 | TIM 50

The converter is the SAME tier set as Z2 with one extra RDL, and for the same reason the
Z2 cells are discrete: it occupies 49 cell footprints, not a full-area slab.

WHY Z1 HAS NINE TIERS AND Z2 HAS EIGHT. Z1's converter is sandwiched -- it lands on the
bottom-substrate RDL underneath and must present an output RDL to the microbumps above, so
it carries a landing RDL at BOTH ends. Z2 attaches only at the substrate side; its far end
descends into the cutout and terminates free. So Z1 = 1973 um and Z2 = 1963 um, and the
10 um difference is one RDL, not a difference in active converter content. Section 18's
inventory equality is over the ACTIVE components (HS, LS, inductors, flying caps), which
are identical.
"""
from __future__ import annotations

import sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for _p in ("scripts/phase0nw", "scripts/phase0mr", "scripts/phase0i", "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))

from z2_converter import (OUT_OF_CELL, TIER_MATERIAL,  # noqa: E402
                          microbump_material, rdl_tier_material)

Z1_CFG = R / "configs" / "phase0nx" / "z1_physical.yaml"


def load_z1_config(path=None) -> dict:
    """Parse and CROSS-CHECK the Z1 physical config.

    Same philosophy as the Z2 loader: a config that states a tier list AND a total AND a
    package height is asserting relations, and the loader re-derives them rather than
    trusting them. Z1 previously had no config at all -- its stack was Python constants,
    which is how two architectures that must stay comparable drift apart unnoticed.
    """
    import yaml
    p = Path(path) if path else Z1_CFG
    c = yaml.safe_load(p.read_text())
    conv = c["converter"]
    tiers = conv["tiers_from_substrate_upward"]
    summed = sum(float(t["um"]) for t in tiers)
    if abs(summed - float(conv["total_um"])) > 1e-9:
        raise ValueError(f"{p.name}: tiers sum to {summed} um, total_um says "
                         f"{conv['total_um']}")
    if c["board"]["case"].startswith("fr4_"):
        raise ValueError(f"{p.name}: legacy board case {c['board']['case']} is forbidden "
                         f"on the physical path")
    side, area = float(conv["cell_side_mm"]), float(conv["cell_area_mm2"])
    if abs(side * side - area) / area > 2e-4:
        raise ValueError(f"{p.name}: cell_side {side} squares to {side*side:.4f}, not "
                         f"cell_area_mm2 {area}")
    # the stated package height must equal the sum of everything in the stack
    height = (float(c["board"]["thickness_um"]) + float(c["bga"]["height_um"])
              + float(c["substrate"]["thickness_um"]) + summed
              + float(c["interface"]["thickness_um"]) + float(c["die"]["thickness_um"])
              + float(c["tim"]["thickness_um"]))
    want = float(c["expected"]["package_top_um"])
    if abs(height - want) > 1e-6:
        raise ValueError(f"{p.name}: layers sum to {height} um but expected.package_top_um "
                         f"says {want}")
    return c


_C = load_z1_config()
SUBSTRATE_UM = float(_C["substrate"]["thickness_um"])

UBUMP_UM = float(_C["interface"]["thickness_um"])   # the production `interface` layer

# Specified Z1 converter, FROM THE CONFIG -- no longer a Python constant.
Z1_TIERS = tuple((t["name"], float(t["um"]))
                 for t in _C["converter"]["tiers_from_substrate_upward"])
Z1_CONV_UM = sum(t for _n, t in Z1_TIERS)
Z1_CELLS = int(_C["converter"]["cells"])
Z1_CELL_SIDE_MM = float(_C["converter"]["cell_side_mm"])
Z1_BOARD_CASE = _C["board"]["case"]
Z1_RAIL_V = float(_C["supply_return"]["rail_v"])


def _material(tier_name: str) -> str:
    if tier_name.endswith("_rdl"):
        return "rdl_tier"
    return TIER_MATERIAL[tier_name][0]


def mid_layers(cfg=None, nz_thin: int = 1, nz_thick: int = 2) -> list:
    """(name, thickness_mm, material, nz, footprint) stacked UPWARD from the substrate top.

    Footprint 'substrate' so the 49 cell footprints and the out-of-cell rule apply; the
    historical 4-tuple form would silently give these the die footprint.
    """
    tiers = cfg.tiers if cfg is not None else Z1_TIERS
    out = []
    for i, (nm, um) in enumerate(tiers):
        out.append((f"z1conv_{i}_{nm}", um / 1e3, _material(nm),
                    nz_thin if um <= 20.0 else nz_thick, "substrate"))
    # NO separate microbump layer. The production stack already carries a 10 um
    # `interface` layer of underfill_homog between the converter top and the die, and
    # that IS the "microbumps + underfill 10 um" row of the specified table. Adding
    # another would put the die 10 um too high -- which is exactly what the first build
    # did, landing the TIM at 5343 um against a specified 5333 um.
    return out


def install(stack: dict, out_of_cell: str = "F1_encapsulated", cfg=None):
    """Materials + mid layers + the out-of-cell rule for the complete physical Z1."""
    if out_of_cell not in OUT_OF_CELL:
        raise ValueError(f"unknown out-of-cell case {out_of_cell!r}")
    stack["materials"]["rdl_tier"] = rdl_tier_material()
    stack["materials"]["microbump"] = microbump_material()
    mids = mid_layers(cfg)
    conv_names = tuple(m[0] for m in mids if m[0].startswith("z1conv_"))
    return mids, conv_names, OUT_OF_CELL[out_of_cell]


def tier_report(mesh, cfg=None) -> list:
    from physical_package import measure_layers
    lay = measure_layers(mesh)
    rows = []
    for nm, t_mm, mat, _nz, _fp in mid_layers(cfg):
        m = lay.get(nm)
        rows.append({"tier": nm, "material": mat, "spec_um": round(t_mm * 1e3, 3),
                     "mesh_um": None if m is None else round(m["t_um"], 3),
                     "z0_um": None if m is None else round(m["z0_um"], 2),
                     "z1_um": None if m is None else round(m["z1_um"], 2)})
    return rows
