# Z1/Z2 supply and return geometry

Phase 0N-S Tasks 8 and 9. **Specification and quantification. Not yet implemented in the
ETM mesh** — see §4.

## 1. The present representation, and why it is not enough

The electrical model accounts return as `R_loop = 2 × R_field` in
`replay_production.tier_resistance`. That is a **factor, not geometry**: there is no ground
via field, no ground plane and no board return anywhere in the mesh. For an abstraction
that is defensible; for something called a physically closed package it is not, because
return copper has volume, position, stiffness and thermal conductivity that the mechanical
and thermal solves need.

## 2. Required regions, per architecture

| region | Z1 (embedded) | Z2 (land-side cutout) |
|---|---|---|
| 48 V feed | BGA power balls → bottom-substrate TSV field → bottom RDL | peripheral BGA power balls → land-side HV RDL |
| 48 V return | bottom RDL ground → TSV ground field → BGA ground balls | land-side ground plane → peripheral BGA ground balls |
| conversion | inside the substrate power layers | in the land-side cells |
| 1 V supply | cell output RDL → microbumps → die | cell output RDL → **substrate supply TSV field** → top RDL → microbumps |
| 1 V return | die ground → microbumps → output RDL ground | die ground → microbumps → top RDL ground → **substrate return TSV field** → cell ground |

The Z2 substrate TSV field must therefore be **split into two interleaved fields**, supply
and return, each carrying 1000 A at system level.

## 3. Minimum acceptable implementation

Separate homogenised supply and return via fields, each with correct **copper volume,
position, pitch, count, current, thermal conductivity and elastic properties**, placed at
the actual cell footprints rather than smeared over the substrate. Provisioning must be
recomputed **independently** for supply and return rather than assuming symmetry, because
the ground field also carries the die's return and may need more copper.

Preferred: instantiate actual via arrays per cell if the element budget allows — the mesh
already supports discrete via inclusions (`tsv_discrete_pitch` in `mesh.build`).

## 4. Status

**Not implemented.** The frozen mesh has one `tsv_homog` region per architecture and no
ground counterpart. Until the split exists, no ETM result from a "physically closed"
geometry may be reported.

## 5. The residual low-voltage lateral path, quantified (Task 9)

The cell grid and the die POL partition are nearly co-pitched, so the 1 V path is close to
vertical — but "close" needed a number.

| | value |
|---|---:|
| cell-centre → POL-region-centre offset, mean | 77.0 µm |
| offset, max | 123.2 µm |
| Cu resistivity at 95 °C | 2.201e-08 Ω·m |
| sheet resistance, 10 µm Cu | 2.2011 mΩ/sq |
| squares traversed (offset ÷ cell side), mean | 0.0325 |
| loop resistance per cell, mean | 143.2 µΩ |
| **single-layer strip estimate, system** | **2.922 W** (mean offset), 4.674 W (max) |

**This is an upper bound, not an additional term.** The framework already solves lateral
spreading: `P_pkg_RDL` comes from `rdl_network_solve` on the `ectc2024_primary` stack —
**2 VDD + 2 GND layers of 10 µm Cu**, as a 2-D network over the real source/POL grid. The
strip estimate above is 1-D, single-layer and confined to the cell width, so it bounds a
degenerate implementation.

### The finding

| term (Z2, system) | W |
|---|---:|
| `P_pkg_RDL` — **the authoritative lateral term** | **0.6693** |
| `P_TSV` | 0.9905 |
| `P_bumps` | 0.0160 |
| `P_intraVR_metal` | 3.6272 |

Lateral spreading costs **0.669 W — 68 % of the TSV loss** on which the whole Z1/Z2
architecture comparison turns, and it would be 2.9 W on a single layer. **Describing the
DVPD path as "almost vertical" understates a term of the same order as the one being
compared.** The multilayer RDL is doing real work, and that work should be stated rather
than absorbed into a qualitative claim.
