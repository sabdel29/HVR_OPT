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

from z2_converter import OUT_OF_CELL, TIER_MATERIAL, rdl_composite_material  # noqa: E402

SUBSTRATE_UM = 300.0
UBUMP_UM = 10.0        # carried by the production `interface` layer, not added here

# Specified Z1 converter, from the bottom substrate UPWARD (section 1 of the stack doc).
Z1_TIERS = (
    ("bottom_substrate_rdl", 10.0),
    ("gan_hs_EPC2014C",     685.0),
    ("interlayer_rdl",       10.0),
    ("gan_ls_EPC2057",      638.0),
    ("interlayer_rdl",       10.0),
    ("flying_caps",         100.0),
    ("interlayer_rdl",       10.0),
    ("inductor_plus_cout",  500.0),
    ("output_rdl",           10.0),
)
Z1_CONV_UM = sum(t for _n, t in Z1_TIERS)        # 1973


def _material(tier_name: str) -> str:
    if tier_name.endswith("_rdl"):
        return "rdl_composite"
    return TIER_MATERIAL[tier_name][0]


def mid_layers(nz_thin: int = 1, nz_thick: int = 2) -> list:
    """(name, thickness_mm, material, nz, footprint) stacked UPWARD from the substrate top.

    Footprint 'substrate' so the 49 cell footprints and the out-of-cell rule apply; the
    historical 4-tuple form would silently give these the die footprint.
    """
    out = []
    for i, (nm, um) in enumerate(Z1_TIERS):
        out.append((f"z1conv_{i}_{nm}", um / 1e3, _material(nm),
                    nz_thin if um <= 20.0 else nz_thick, "substrate"))
    # NO separate microbump layer. The production stack already carries a 10 um
    # `interface` layer of underfill_homog between the converter top and the die, and
    # that IS the "microbumps + underfill 10 um" row of the specified table. Adding
    # another would put the die 10 um too high -- which is exactly what the first build
    # did, landing the TIM at 5343 um against a specified 5333 um.
    return out


def install(stack: dict, out_of_cell: str = "F1_encapsulated"):
    """Materials + mid layers + the out-of-cell rule for the complete physical Z1."""
    if out_of_cell not in OUT_OF_CELL:
        raise ValueError(f"unknown out-of-cell case {out_of_cell!r}")
    stack["materials"]["rdl_composite"] = rdl_composite_material()
    mids = mid_layers()
    conv_names = tuple(m[0] for m in mids if m[0].startswith("z1conv_"))
    return mids, conv_names, OUT_OF_CELL[out_of_cell]


def tier_report(mesh) -> list:
    from physical_package import measure_layers
    lay = measure_layers(mesh)
    rows = []
    for nm, t_mm, mat, _nz, _fp in mid_layers():
        m = lay.get(nm)
        rows.append({"tier": nm, "material": mat, "spec_um": round(t_mm * 1e3, 3),
                     "mesh_um": None if m is None else round(m["t_um"], 3),
                     "z0_um": None if m is None else round(m["z0_um"], 2),
                     "z1_um": None if m is None else round(m["z1_um"], 2)})
    return rows
