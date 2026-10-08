# PHASE 0M-R2 SECTION 2 --- Z4 GEOMETRY AUDIT

## What was wrong

`zglobal.stack_for` had branches for `"in"` (ARCH_Z1, converter inside the substrate) and
`"below"` (ARCH_Z2, converter under the substrate). It had **no branch for `"above"`**,
which is what ARCH_Z4 declares. `zglobal.conv_above_layers()` was written for that branch
and is never called anywhere in the repository -- dead code marking the gap.

The consequence: ARCH_Z4's converter heat was deposited into the `interface` layer, a
10 um underfill band 0.355 mm below the cooled face. A real Z4 power die sits far deeper
and is far thicker. Every Z4 thermal and mechanical number produced before this phase was
conditional on that substitution.

## The power die as real geometry

Built from the components the framework already sources, stacked where ARCH_Z4 puts them:
above the substrate top, below the compute die.

| layer | thickness | provenance | source |
|---|---|---|---|
| `power_die_rdl_lower` | 10 um | SOURCE_BACKED | geometry.INTERLAYER_RDL_H_UM --- ECTC-2024, 2 x 10 um Cu plus dielectric |
| `gan_hs` | 685 um | SOURCE_BACKED | zarch.GAN_HS_UM --- EPC2212 datasheet Side View, nominal (815 um max) |
| `gan_ls` | 606 um | SOURCE_BACKED | zarch.GAN_LS_UM --- EPC2090 datasheet, 518 +/- 25 die + 50 Cu + 3 Ni + 35 solder |
| `inductor` | 500 um | SOURCE_BACKED | geometry.inductor_library, the 250 nH part used by the compiled N3K3KA2 design |
| `mlcc` | 100 um | BOUNDED | geometry.MLCC_H_UM --- the manufacturer page could not be reached in any phase. The framework carries opt |
| `power_die_rdl_upper` | 10 um | SOURCE_BACKED | geometry.INTERLAYER_RDL_H_UM |
| `hybrid_bond` | 10 um | SOURCE_BACKED | zarch.path_for declares "10 um hybrid pads, the SHORTEST possible 1 V path" for the power-die-to-compute- |

**Total: 1921 um.**

The high-side device is in this stack. For ARCH_Z1 the source flip-chips it to the RDL of
the bottom substrate, below z = 0, which is why Z1's charged cell is 1226 um and not 1911.
ARCH_Z4 has no such surface: all of its conversion happens on the power die. That is a
DERIVED consequence of the declared power path, not a new assumption.

The component layers use `hvr_effective`, the same effective converter medium ARCH_Z1 uses
for its tile band and ARCH_Z2 for its backside layer. Using a different material for Z4
would turn an architecture comparison into a material comparison. **The power die is not
modelled as a generic silicon slab.**

### Provenance summary

| class | count |
|---|---|
| SOURCE_BACKED | 6 |
| DERIVED | 2 |
| BOUNDED | 2 |
| OPEN | 4 |

## The construction question the sources do not settle

No source in this repository describes a monolithic power-die process, so two
constructions are defensible and BOTH are run:

| variant | thickness | rule | status |
|---|---|---|---|
| **Z4_STACKED** | 1921 um | sum of all layer thicknesses | primary |
| **Z4_PLANAR** | 715 um | max(component heights) + both RDLs + bond = 685 + 10 + 10 + 10 | bound |

## Where the converter heat now goes

| architecture | converter layer | depth below the cooled face | real layer? |
|---|---|---|---|
| Z1_EMBEDDED | `tile_band` | 0.973 mm | yes |
| Z2_BACKSIDE | `conv` | 1.273 mm | yes |
| Z4, Phase 0M-R | `interface` | **0.355 mm** | **NO --- substituted** |
| Z4, Phase 0M-R2 | `pdie_gan_hs` + `pdie_gan_ls` + `pdie_inductor` + `pdie_mlcc` | **1.928 mm** | yes |

The heat is spread across the whole component band weighted by volume, not dumped into
whichever sub-layer is named first. The `interface` fallback has been REMOVED rather than
left as a safety net: a missing power die now raises, because a silent fallback is exactly
how the conditional result was produced.

## Result

| quantity | Phase 0M-R (substituted) | 0M-R2 STACKED | 0M-R2 PLANAR |
|---|---|---|---|
| system electrical loss (W) | 134.739 | **140.657** | 139.641 |
| peak temperature (C) | 96.32 | **106.44** | 104.02 |
| converter layer temperature (C) | 91.34 | **101.36** | 99.60 |
| die warpage (um) | 35.946 | **25.539** | 50.146 |
| corner-joint driver (um) | 3.6681 | **3.9120** | 4.4451 |

Two corrections landed together, so the Z4 change is not attributable to geometry alone:
DEFECT #55 (below) affects all three architectures, and the power-die geometry affects Z4
only. The control runs separate them.

## Verdict on Z4: **Z4 REMAINS CONDITIONAL**

Not for the old reason. The heat-source substitution is gone and the die is real geometry.
Z4 is now conditional on a **sourcing** question instead of a modelling one: its rank
depends on which construction the power die actually is.

| | corner driver | rank among the three |
|---|---|---|
| Z4_STACKED | 3.9120 um | **best** |
| Z4_PLANAR | 4.4451 um | middle |

Between the two constructions the die warpage differs by about a factor of two, and Z4
moves from first to second place. The stacked variant inserts 1.921 mm of stiff
`hvr_effective` between the substrate and the compute die, which acts as a stiffening
plate; the planar variant does not. **Nothing about Z4's ranking can be closed until the
power-die construction is sourced.**

What CAN be said, and is stable across both variants: Z4's converter sits deeper below the
cooled face than either alternative, its peak temperature is nonetheless the lowest of the
three because its loss is spread through a much thicker volume, and **the Z1 / Z2 ordering
is unaffected by anything Z4 does** -- it is a separate comparison and is reported as one.

## DEFECT #55, found while building this

The TSV-field material override was keyed on a layer's in-plane FOOTPRINT. Every assembly
layer added below z = 0 in Phase 0G -- the PCB, the BGA field, and for ARCH_Z2 the
backside converter -- spans the substrate extent, so all of them had their material
overwritten with `tsv_homog` inside every tile. The PCB was being modelled as a
copper/silicon composite.

| architecture | misassigned volume | legitimate TSV volume | ratio |
|---|---|---|---|
| Z1_EMBEDDED | 522.29 mm3 | 20.34 mm3 | 25.7x |
| Z2_BACKSIDE | 859.31 mm3 | 76.97 mm3 | 11.2x |
| Z4_POWER_DIE | 522.29 mm3 | 76.97 mm3 | 6.8x |

The property error is large and it is architecture-dependent, so it does not cancel in the
comparison:

| where FR4 belongs | k | E | CTE |
|---|---|---|---|
| `board_fr4`, correct | 0.30 W/mK | 20 000 MPa | 1.70e-5 /K |
| `tsv_homog`, what was used | 158.90 W/mK | 126 073 MPa | 5.01e-6 /K |
| error | **530x** | **6.3x** | **3.4x low** |

Board stiffness and CTE are precisely what drive package warpage and corner-joint shear,
which is the deciding metric. Fixing it moves Z1's die warpage from 25.37 to 44.50 um
(+75 %) and its corner driver from 4.2803 to 4.9803 um (+16.4 %). `footprint` and
`tsv_host` are now separate fields on `Layer`.
