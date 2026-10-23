# Physical Z1/Z2 implementation audit

Phase 0N-W. **Every row is evaluated at run time** by `scripts/phase0nw/audit_physical_gates.py`: the config is loaded, the mesh is built, and the measured geometry decides the status. Nothing here is typed by hand, because a hand-typed status table goes stale a phase after it is written.

**5 of 26 gates are OPEN.** No physical ETM result lineage may be created while that number is non-zero.

| status | meaning |
|---|---|
| SPECIFIED | written down with a source or a rule |
| IMPLEMENTED | the solver builds it, verified by measuring the mesh |
| VALIDATED | a convergence or cross-model check has been run |
| OPEN | neither |

## Gate table

| area | gate | status | evidence |
|---|---|---|---|
| Board | physical YAML uses it968g_2p4mm | **IMPLEMENTED** | config board.case = it968g_2p4mm |
| Board | board thickness reaches the mesh | **IMPLEMENTED** | meshed 2400 um against config 2400 um |
| Board | PCB-H0 documented | **SPECIFIED** | model_level = PCB-H0; see PCB_IT968G_HOMOGENIZATION.md Sec.8 |
| Board | PCB-H1 thermal validation | **OPEN** | not implemented |
| Board | eta uncertainty retained | **SPECIFIED** | eta_sensitivity = [0.25, 0.5, 0.75] |
| Board | T-only cases material-identical | **IMPLEMENTED** | it968g_2p4mm and it968g_3p2mm share one material dict |
| Z2 | 2.4 mm board | **IMPLEMENTED** | meshed 2400 um |
| Z2 | 23.36 mm conforming cutout | **IMPLEMENTED** | cutout 23.36 mm, edges are grid breakpoints |
| Z2 | 49 discrete cells | **IMPLEMENTED** | 49 tile footprints in the mesh |
| Z2 | full 1.963 mm stack | **IMPLEMENTED** | 8 tiers measured, total 1963.0 um |
| Z2 | EPC2014C high side explicitly present | **IMPLEMENTED** | deepest tier conv_7_gan_hs_EPC2014C at 737 um above the PCB backside |
| Z2 | no full-area converter slab | **IMPLEMENTED** | 0 of 37254 elements belong to a layer named 'conv' |
| Z2 | no converter medium outside a cell | **IMPLEMENTED** | 0 of 6615 in-cell converter elements lie outside a footprint |
| Z2 | out-of-cell material/void defined | **SPECIFIED** | F1 encapsulated (primary) and F2 void both build; bracket not yet run |
| Z2 | converter descends into the cutout | **IMPLEMENTED** | HVR occupies 1422 -> 737 um, inside the board's 0 -> 2400 um extent |
| Z2 | no overlap | **IMPLEMENTED** | the mesh builder raises if two layers claim one element; all 37254 elements were accepted |
| Z2 | symmetric BGA feed | **IMPLEMENTED** | 16+16 mirror-symmetric pairs, first moments (0,0); research/phase0nt/annular_pcb.json |
| Z2 | split VDD / GND TSV fields meshed | **OPEN** | analytical model exists; the two rails are not yet distinct mesh regions |
| Z2 | per-tier material fidelity | **OPEN** | MLCC tier has no sourced card; GaN epi not resolved (mapped to the Si carrier) |
| Z1 | complete physical stack | **IMPLEMENTED** | package top 5333 um above the PCB backside (specified 5333); converter 1973 um in 9 tiers |
| Z1 | HS explicitly present | **IMPLEMENTED** | EPC2014C meshed 685 um at 3010 -> 3695 um |
| Z1 | selected-device dimensions | **IMPLEMENTED** | EPC2014C 685 um and EPC2057 638 um in both architectures |
| Z1 | same converter inventory | **IMPLEMENTED** | 147 HS / 147 LS / 147 inductors / 98 flying caps in both; active volume 528.613 mm3 equal to machine precision |
| Z1 | explicit supply/return | **OPEN** | 48 V VDD/GND TSV fields not yet meshed (analytical model exists) |
| Z2 | VDD/GND TSV fields: analytical model | **SPECIFIED** | interleaved 37x37 lattice, 685 VDD / 684 GND per cell, I_cell 20.408 A; R_loop includes constriction (1.4 % of the loop) |
| Results | physical ET result lineage | **OPEN** | BLOCKED: no new ETM result may be generated until every gate above is closed |

## Measured Z2 converter tiers

z is given in the PCB-backside frame, matching `Z1_Z2_PHYSICALLY_SPECIFIED_STACKS.md` section 6.

| tier | material | spec (um) | mesh (um) | z top | z bottom |
|---|---|---:|---:|---:|---:|
| conv_7_gan_hs_EPC2014C | `silicon` | 685 | 685 | 1422 | 737 |
| conv_6_interlayer_rdl | `rdl_composite` | 10 | 10 | 1432 | 1422 |
| conv_5_flying_caps | `hvr_effective` | 100 | 100 | 1532 | 1432 |
| conv_4_interlayer_rdl | `rdl_composite` | 10 | 10 | 1542 | 1532 |
| conv_3_gan_ls_EPC2057 | `silicon` | 638 | 638 | 2180 | 1542 |
| conv_2_interlayer_rdl | `rdl_composite` | 10 | 10 | 2190 | 2180 |
| conv_1_inductor_plus_cout | `hvr_effective` | 500 | 500 | 2690 | 2190 |
| conv_0_land_side_attach_rdl | `rdl_composite` | 10 | 10 | 2700 | 2690 |
| **total** | | **1963** | **1963** | | |

## Measured Z1 converter tiers

Specified table: `Z1_Z2_PHYSICALLY_SPECIFIED_STACKS.md` section 1.

| tier | material | spec (um) | mesh (um) | z bottom | z top |
|---|---|---:|---:|---:|---:|
| z1conv_0_bottom_substrate_rdl | `rdl_composite` | 10 | 10 | 3000 | 3010 |
| z1conv_1_gan_hs_EPC2014C | `silicon` | 685 | 685 | 3010 | 3695 |
| z1conv_2_interlayer_rdl | `rdl_composite` | 10 | 10 | 3695 | 3705 |
| z1conv_3_gan_ls_EPC2057 | `silicon` | 638 | 638 | 3705 | 4343 |
| z1conv_4_interlayer_rdl | `rdl_composite` | 10 | 10 | 4343 | 4353 |
| z1conv_5_flying_caps | `hvr_effective` | 100 | 100 | 4353 | 4453 |
| z1conv_6_interlayer_rdl | `rdl_composite` | 10 | 10 | 4453 | 4463 |
| z1conv_7_inductor_plus_cout | `hvr_effective` | 500 | 500 | 4463 | 4963 |
| z1conv_8_output_rdl | `rdl_composite` | 10 | 10 | 4963 | 4973 |

Package top **5333 um** above the PCB backside (specified 5333). Substrate **300 um** -- the 1300 um embedded proxy with its 1226 um homogenized band, which contains no high-side device at all, is gone from the physical path.

## Converter inventory equality

Volumes are measured from the two MESHES, not computed from the specification, so a dropped or duplicated tier would show up here.

| component | per cell | total | Z1 (mm3) | Z2 (mm3) | relative delta |
|---|---:|---:|---:|---:|---:|
| hs | 3 | 147 | 188.2996 | 188.2996 | 0.0e+00 |
| ls | 3 | 147 | 175.3798 | 175.3798 | 3.2e-16 |
| inductor | 3 | 147 | 137.4450 | 137.4450 | 0.0e+00 |
| flying_cap | 2 | 98 | 27.4890 | 27.4890 | 2.2e-15 |

**Total active converter volume: Z1 528.6135 mm3, Z2 528.6135 mm3 — equal to machine precision.**

The only difference is interconnect: Z1 carries 5 RDLs (13.7445 mm3) against Z2's 4 (10.9956 mm3), so the totals are 1973 and 1963 um. Z1's converter is sandwiched -- it lands on the bottom-substrate RDL below and must present an output RDL to the microbumps above, so it carries a landing RDL at BOTH ends. Z2 attaches only at the substrate side; its far end descends into the cutout and terminates free. The 10 um / one-RDL difference is interconnect, not active converter content.

## VDD / GND TSV fields (analytical)

**Per cell I = 20.408 A.** The ~1000 A figure is the SYSTEM aggregate across all 49 cells and is never carried by one local field.

| quantity | VDD | GND |
|---|---:|---:|
| TSVs per cell | 685 | 684 |
| TSVs, system | 33565 | 33516 |
| Cu area fraction | 0.0863 | 0.0862 |
| current per via (mA) | 29.79 | 29.84 |
| current density (A/cm2) | 4215 | 4221 |
| field resistance (uohm) | 10.409 | 10.424 |
| spreading resistance (uohm) | 0.145 | 0.145 |
| loss per cell (mW) | 4.40 | 4.40 |

Geometry is the SOURCE_BACKED 30 um / 60 um pitch over a 300 um substrate, checkerboard-interleaved on a 37x37 lattice so every VDD via has GND nearest neighbours. Both fields are symmetric about the cell centre to machine precision, so neither rail sees a systematically different thermal or mechanical environment.

**R_loop = 21.122 uohm**, against 20.818 uohm for the naive `2 R_field`. Constriction at the via mouths contributes 1.4 % of the loop, so the naive form UNDER-predicts by 1.4 %. That is a small correction here, but it was computed rather than assumed, which is what the brief asks for. System TSV loss 0.431 W.

**These fields are not yet meshed as distinct regions** -- the model is analytical and the gate stays OPEN.

## What 'IMPLEMENTED' means here, and what it does not

The converter rows above are a **geometry** result. The mesh carries 49 discrete footprints, eight tiers at their specified depths, a 1963 um total, the high-side device explicitly present and deepest, and no converter medium outside a cell footprint.

It is **not** a material result. Each tier is meshed at a medium that already exists in the framework, because the geometry gate does not license inventing material data. The flying-capacitor tier in particular is meshed at the homogenized converter medium, which an MLCC ceramic/Ni stack is not; that tier's material is **OPEN**. The GaN devices are meshed as their silicon carrier, with the epi unresolved, and that is **BOUNDED**.

## Out-of-cell region

The opening is 23.36^2 = 545.69 mm2 and the 49 cells occupy 274.89 mm2, so **49.6 % of the opening** is outside a cell. The 69.5 % figure quoted in the brief is the fraction of the 30 x 30 mm substrate footprint, which was the governing number while the converter was a full-area slab; now that the converter exists only inside the cutout, 49.6 % is the one that applies.

Both cases build: **F1 encapsulated** (primary, `underfill_homog`) and **F2 void** (elements are never created -- genuinely no material, not an air-property relabel). The final mechanical result must be reported across the bracket; that has not been run.
