# Physical Z1/Z2 implementation audit

Phase 0N-W. **Every row is evaluated at run time** by `scripts/phase0nw/audit_physical_gates.py`: the config is loaded, the mesh is built, and the measured geometry decides the status. Nothing here is typed by hand, because a hand-typed status table goes stale a phase after it is written.

**27 of 54 gates are OPEN.** No physical ETM result lineage may be created while that number is non-zero.

Maturity is reported by status rather than collapsed into "closed", because SPECIFIED and IMPLEMENTED are not the same claim and neither is VALIDATED:

| status | count |
|---|---:|
| IMPLEMENTED | 20 |
| SPECIFIED | 7 |
| VALIDATED | 0 |
| OPEN | 27 |

So **27 of 54 are non-open**, of which only 20 are IMPLEMENTED and **0 are VALIDATED**. Nothing in this package has been validated against a solve yet.

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
| Board | PCB-H0 documented | **SPECIFIED** | model_level = PCB-H0; PCB_IT968G_HOMOGENIZATION.md Sec.8 |
| Board | PCB-H1 meshed as FE depth blocks | **OPEN** | five-block model defined and 1-D consistent with H0 (k_xy exact, k_z 7.9e-07), but not yet built into the mesh |
| Board | PCB-H1 thermal validation | **OPEN** | no H0-vs-H1 solve exists |
| Board | eta coverage sensitivity completed | **OPEN** | material tensors exist for eta 0.25/0.50/0.75; no solve run |
| Board | T-only cases material-identical | **IMPLEMENTED** | it968g_2p4mm and it968g_3p2mm share one material dict |
| Board | 2.4/3.2 T-only comparison completed | **OPEN** | not run -- no artifact exists for '2.4/3.2 T-only comparison completed' |
| Electrical | Z1 power bookkeeping distinguishes load, loss and input | **IMPLEMENTED** | P_in = P_load 1000 W + P_loss 137.292 W = 1137.2923 W -> I = 23.6936 A. The earlier model divided the LOSS by 48 V and reported 2.86 A, low by 8.3x in current and 69x in I^2 R. |
| Electrical | Z1 48 V rail-specific VDD/GND model | **SPECIFIED** | 48 V rail at 23.6936 A from (P_load + P_loss)/48. Source: Phase-0M-R3C electronics LOSS + load (PLACEHOLDER). Stays SPECIFIED, not IMPLEMENTED, until a physical loss ledger replaces the historical placeholder. |
| Electrical | Z2 1 V rail-specific VDD/GND model | **SPECIFIED** | 1 V rail, I = 1000 A load current, 20.408 A per cell |
| Electrical | Z1-specific TSV sizing | **SPECIFIED** | 48 V rail, 480 mV budget: minimum 4 vias/cell against Z2's 81 -- the Z2 bracket does not apply to Z1 |
| Electrical | Z2-specific TSV sizing | **SPECIFIED** | 1 V rail, 10 mV budget: 81 / 324 / 1369 vias/cell |
| TSV | thermal/mechanical sensitivity to TSV density | **OPEN** | the adopted field is 1369 vias/cell, 17x the electrically required minimum, so Cu volume fraction -- and therefore substrate k, E and CTE -- depends strongly on a choice no solve has tested |
| TSV | TSV copper represented consistently in the FE model | **OPEN** | the substrate currently carries the historical tsv_homog fraction, which is not tied to the adopted TSV density; electrical rails are separated analytically while thermal/mechanical Cu would be one co-located homogenized field, and that is not yet implemented or stated in the mesh |
| Configuration | Z1 YAML drives the Z1 mesh | **IMPLEMENTED** | build_physical_z1 takes a Z1Package from configs/phase0nx/z1_physical.yaml (300 um substrate, 9 tiers, 48 V rail) and REFUSES a Z2 PhysicalPackage |
| Electrical | TSV count justified by a design criterion | **SPECIFIED** | three-point study: N_min_drop 81, N_mid 324, N_max_density 1369; adopted = max_density |
| Electrical | temperature-dependent TSV resistance in the fixed point | **OPEN** | rho(T) exists in the analytical model but is evaluated at 20 C; not yet coupled |
| Electrical | RDL loss recomputed on the physical geometry | **OPEN** | not run -- no artifact exists for 'RDL loss recomputed on the physical geometry' |
| Electrical | energy conservation verified on the physical heat map | **OPEN** | not run -- no artifact exists for 'energy conservation verified on the physical heat map' |
| Electrical | physical Z1/Z2 loss audit frozen | **OPEN** | not run -- no artifact exists for 'physical Z1/Z2 loss audit frozen' |
| Thermal | tier-aware converter heat deposition | **OPEN** | production heat map still targets a single converter layer |
| Thermal | physical thermal BC selected | **OPEN** | not run -- no artifact exists for 'physical thermal BC selected' |
| Thermal | Z2-PASSIVE case implemented | **OPEN** | not run -- no artifact exists for 'Z2-PASSIVE case implemented' |
| Thermal | Z2-COOLED case implemented | **OPEN** | not run -- no artifact exists for 'Z2-COOLED case implemented' |
| Thermal | ET fixed point converged | **OPEN** | not run -- no artifact exists for 'ET fixed point converged' |
| Thermal | PCB MOT/Tg checks evaluated | **OPEN** | not run -- no artifact exists for 'PCB MOT/Tg checks evaluated' |
| Thermal | H0 vs H1 thermal comparison run | **OPEN** | not run -- no artifact exists for 'H0 vs H1 thermal comparison run' |
| Mechanical | F1/F2 out-of-cell bracket run | **OPEN** | both cases BUILD; neither has been solved |
| Mechanical | physical mesh convergence | **OPEN** | not run -- no artifact exists for 'physical mesh convergence' |
| Mechanical | critical-joint search over all 528 surviving sites | **OPEN** | not run -- no artifact exists for 'critical-joint search over all 528 surviving sites' |
| Mechanical | 2.4/3.2 T-only mechanical comparison | **OPEN** | not run -- no artifact exists for '2.4/3.2 T-only mechanical comparison' |
| Local | local solder rerun at the new critical site | **OPEN** | not run -- no artifact exists for 'local solder rerun at the new critical site' |
| Z2 geometry | 23.36 mm conforming cutout | **IMPLEMENTED** | cutout 23.36 mm, edges are grid breakpoints |
| Z2 geometry | 49 discrete cells | **IMPLEMENTED** | 49 tile footprints in the mesh |
| Z2 geometry | full 1.963 mm stack | **IMPLEMENTED** | 8 tiers measured, total 1963.0 um |
| Z2 geometry | no full-area converter slab | **IMPLEMENTED** | 0 of 38623 elements belong to a layer named 'conv' |
| Z2 geometry | no converter medium outside a cell | **IMPLEMENTED** | 0 of 6615 in-cell converter elements lie outside a footprint |
| Z2 geometry | converter descends into the cutout | **IMPLEMENTED** | HVR occupies 1422 -> 737 um inside the board's 0 -> 2400 um extent |
| Z2 geometry | no overlap | **IMPLEMENTED** | the mesh builder raises if two layers claim one element; all 38623 elements were accepted |
| Z2 geometry | out-of-cell material/void defined | **SPECIFIED** | F1 encapsulated (primary) and F2 void both build; bracket not run |
| Z2 geometry | symmetric BGA feed | **IMPLEMENTED** | 16+16 mirror-symmetric pairs, first moments (0,0); research/phase0nt/annular_pcb.json |
| Z1 geometry | complete physical stack | **IMPLEMENTED** | package top 5333 um (specified 5333); converter 1973 um in 9 tiers |
| Z1 geometry | HS explicitly present | **IMPLEMENTED** | EPC2014C meshed 685 um at 3010 -> 3695 um |
| Z1 geometry | selected-device dimensions | **IMPLEMENTED** | EPC2014C 685 um and EPC2057 638 um in both architectures |
| Inventory | same converter inventory | **IMPLEMENTED** | 147 HS / 147 LS / 147 inductors / 98 flying caps as a TOPOLOGY inventory, homogenized within each cell tier footprint; active volume 528.613 mm3 equal to machine precision |
| Inventory | 1-D stack thickness conserves exactly | **IMPLEMENTED** | Z2 cutout column 2633 um and periphery 3010 um; Z1 5333 um; no gaps, no overlaps |
| Material | explicit RDL tiers use the RDL tensor | **IMPLEMENTED** | Phase-0M-R rdl_effective_tensor.csv (RDL alone), replacing the 40 um RDL + 10 um bump composite previously applied to a 10 um tier |
| Material | microbump/underfill kept separate | **IMPLEMENTED** | 841 interface elements carry bump_layer_effective_tensor.csv (k_z 11.7 vs underfill 0.7 W/mK) |
| Material | GaN epi contribution bounded | **OPEN** | devices meshed as the Si carrier; the epi contribution is not yet bounded |
| Material | MLCC tier material bounded | **OPEN** | flying-cap tier meshed at hvr_effective; no ceramic/Ni bracket yet |
| Material | inductor/Cout tier bounded | **OPEN** | hvr_effective is generic; occupancy-based bracket not built |
| Material | 10 um RDL tier tensor transfer validated | **OPEN** | NOT transferable as-is: the tensor is a four-metal-layer STACK property (source stack height 55 um, recorded in code as 40 um -- rdl_mechanical.RDL says t_um = 40 (metal only) while the source row's stack_height_um is 55 (metal + dielectric)), applied to a 10 um single-layer tier. Across the sweep k_x spans 92.5-140.6 and k_z 0.80-2.46 W/mK. Carried as BOUNDED; closes on recomputation for the actual tier or demonstrated insensitivity |
| Results | physical ETM result lineage | **OPEN** | BLOCKED: no physical ETM result may be generated until every gate above closes |

## Measured Z2 converter tiers

z is given in the PCB-backside frame, matching `Z1_Z2_PHYSICALLY_SPECIFIED_STACKS.md` section 6.

| tier | material | spec (um) | mesh (um) | z top | z bottom |
|---|---|---:|---:|---:|---:|
| conv_7_gan_hs_EPC2014C | `silicon` | 685 | 685 | 1422 | 737 |
| conv_6_interlayer_rdl | `rdl_tier` | 10 | 10 | 1432 | 1422 |
| conv_5_flying_caps | `hvr_effective` | 100 | 100 | 1532 | 1432 |
| conv_4_interlayer_rdl | `rdl_tier` | 10 | 10 | 1542 | 1532 |
| conv_3_gan_ls_EPC2057 | `silicon` | 638 | 638 | 2180 | 1542 |
| conv_2_interlayer_rdl | `rdl_tier` | 10 | 10 | 2190 | 2180 |
| conv_1_inductor_plus_cout | `hvr_effective` | 500 | 500 | 2690 | 2190 |
| conv_0_land_side_attach_rdl | `rdl_tier` | 10 | 10 | 2700 | 2690 |
| **total** | | **1963** | **1963** | | |

## Measured Z1 converter tiers

Specified table: `Z1_Z2_PHYSICALLY_SPECIFIED_STACKS.md` section 1.

| tier | material | spec (um) | mesh (um) | z bottom | z top |
|---|---|---:|---:|---:|---:|
| z1conv_0_bottom_substrate_rdl | `rdl_tier` | 10 | 10 | 3000 | 3010 |
| z1conv_1_gan_hs_EPC2014C | `silicon` | 685 | 685 | 3010 | 3695 |
| z1conv_2_interlayer_rdl | `rdl_tier` | 10 | 10 | 3695 | 3705 |
| z1conv_3_gan_ls_EPC2057 | `silicon` | 638 | 638 | 3705 | 4343 |
| z1conv_4_interlayer_rdl | `rdl_tier` | 10 | 10 | 4343 | 4353 |
| z1conv_5_flying_caps | `hvr_effective` | 100 | 100 | 4353 | 4453 |
| z1conv_6_interlayer_rdl | `rdl_tier` | 10 | 10 | 4453 | 4463 |
| z1conv_7_inductor_plus_cout | `hvr_effective` | 500 | 500 | 4463 | 4963 |
| z1conv_8_output_rdl | `rdl_tier` | 10 | 10 | 4963 | 4973 |

Package top **5333 um** above the PCB backside (specified 5333). Substrate **300 um** -- the 1300 um embedded proxy with its 1226 um homogenized band, which contains no high-side device at all, is gone from the physical path.

## Converter inventory equality

Volumes are measured from the two MESHES, not computed from the specification, so a dropped or duplicated tier would show up here.

**These counts are a TOPOLOGY inventory, not a count of separately resolved bodies in the FE model.** The mesh carries 49 cell-sized tier footprints per architecture; each cell's component population is homogenized within its corresponding tier footprint. There are not 147 individually meshed transistor bodies. The volume equality below is still the meaningful result -- it says both architectures carry the same active material -- but it must not be read as spatial resolution.

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
| spreading resistance (uohm) | 0.289 | 0.289 |
| loss per cell (mW) | 4.46 | 4.46 |

Geometry is the SOURCE_BACKED 30 um / 60 um pitch over a 300 um substrate, checkerboard-interleaved on a 37x37 lattice so every VDD via has GND nearest neighbours. Both fields are symmetric about the cell centre to machine precision, so neither rail sees a systematically different thermal or mechanical environment.

**R_loop = 21.412 uohm**, against 20.818 uohm for the naive `2 R_field`. Constriction at the via mouths contributes 2.7 % of the loop, so the naive form UNDER-predicts by 2.8 %. That is a small correction here, but it was computed rather than assumed, which is what the brief asks for. System TSV loss 0.437 W.

**These fields are not yet meshed as distinct regions** -- the model is analytical and the gate stays OPEN.

## The two TSV rails are electrically different

Same via geometry. The rail CURRENT differs by more than 40x, and because Joule loss goes as I^2 the TSV LOSS differs by roughly three orders of magnitude. The two ratios are different numbers and must not be quoted interchangeably. A single 1000 A model applied to both erased the distinction entirely.

| | Z1 | Z2 |
|---|---:|---:|
| rail | 48 V input | 1 V output |
| system current | 23.694 A | 1000 A |
| per-cell current | 0.4835 A | 20.408 A |
| system TSV loss | 0.2453 mW | 437.0 mW |

| ratio (Z2/Z1) | | **42.2x current, 1781x loss** |

Z1's current is **a placeholder**: Phase-0M-R3C electronics LOSS + load (PLACEHOLDER). It is I = (P_load + P_loss)/48 V = (1000 + 137.292)/48 = 23.6936 A, and cannot be final until the physical electrical solution replaces the loss term. Z2's is the 1 V load current and must still be updated self-consistently with losses.

**A previous version divided the LOSS by 48 V**, giving 2.86 A -- low by 8.3x in current and 69x in I^2 R. P_total_electronics_w in the frozen replay is exactly sum(L_P_*), i.e. a loss total, not an input power.

**Two consistency problems this exposes.** The framework's own `zarch.rail_currents()` uses a FIXED Phase-0F efficiency eta = 0.889, giving 23.4346 A and an implied loss of 124.86 W -- 12.43 W below the 137.29 W the ETM ledger actually reports, so the canonical current is about 10 % inconsistent with the framework's own losses. And the BGA supply allocation (16 balls x 1.5 A = 24.0 A) was sized against the eta-based 23.4346 A; against the ledger-derived 23.6936 A the margin is only 1.3 %, so any further loss growth makes 16 balls insufficient.

### The TSV count is a choice, and the adopted one is the maximum

Declared budget: 1 % of the rail (10 mV). BOUNDED -- declared engineering budget, not a sourced allowable. No validated em/current-density allowable exists for this via geometry, so none is asserted; the field is bracketed by voltage drop and geometry instead.

| point | pitch | lattice | N | drop | % of rail |
|---|---:|---:|---:|---:|---:|
| min_drop | 240 um | 9x9 | 81 | 7.649 mV | 0.76 % |
| mid | 120 um | 18x18 | 324 | 1.888 mV | 0.19 % |
| max_density | 60 um | 37x37 | 1369 | 0.437 mV | 0.04 % |

**Adopted: max_density.** the mechanical and thermal models need the copper volume fraction to be an upper bound on stiffening and spreading; the ELECTRICAL bracket is reported alongside so the sensitivity is visible. This is a MAXIMUM-DENSITY field, explicitly not a minimum-required one. The electrically required field is 81 vias; the adopted field is 1369, about 17x larger. 685/684 per cell is therefore a geometric upper bound, not a requirement.

### Spreading resistance is counted at BOTH ends

R_loop = R_vdd + R_gnd + 2 R_spread,vdd + 2 R_spread,gnd = 21.412 uohm. Current converges out of the plane into the via mouths at one end and diverges back out at the other, so each rail carries two constrictions -- Holm's contact resistance, rho/(2a) per via rather than rho/(4a). The earlier version charged one end per rail. Correcting it moved the spreading share from 1.4 % to 2.7 % of the loop and the naive 2 R_field error from -1.4 % to -2.8 %. A modest change, reported as a modest one.

## 1-D stack conservation

Every layer accounted for exactly once, from the PCB backside to the TIM top. This audit caught two defects that the converter total could not see: Z1 double-counted the microbump layer (package top 5343 um), and Z2 was missing the 10 um top RDL so the `interface` layer stood in for it and the microbump row vanished (package top 3360 um).

### Z2

**cutout** — 14 layers, span 2633.0 um, sum of thicknesses 2633.0 um, conserved = True

| layer | z0 | z1 | t |
|---|---:|---:|---:|
| conv_7_gan_hs_EPC2014C | 737.0 | 1422.0 | 685.0 |
| conv_6_interlayer_rdl | 1422.0 | 1432.0 | 10.0 |
| conv_5_flying_caps | 1432.0 | 1532.0 | 100.0 |
| conv_4_interlayer_rdl | 1532.0 | 1542.0 | 10.0 |
| conv_3_gan_ls_EPC2057 | 1542.0 | 2180.0 | 638.0 |
| conv_2_interlayer_rdl | 2180.0 | 2190.0 | 10.0 |
| conv_1_inductor_plus_cout | 2190.0 | 2690.0 | 500.0 |
| conv_0_land_side_attach_rdl | 2690.0 | 2700.0 | 10.0 |
| sub_lower | 2700.0 | 2980.0 | 280.0 |
| tile_band | 2980.0 | 3000.0 | 20.0 |
| z2_top_rdl | 3000.0 | 3010.0 | 10.0 |
| interface | 3010.0 | 3020.0 | 10.0 |
| die | 3020.0 | 3320.0 | 300.0 |
| tim | 3320.0 | 3370.0 | 50.0 |

**periphery** — 5 layers, span 3010.0 um, sum of thicknesses 3010.0 um, conserved = True

| layer | z0 | z1 | t |
|---|---:|---:|---:|
| board | -0.0 | 2400.0 | 2400.0 |
| bga | 2400.0 | 2700.0 | 300.0 |
| sub_lower | 2700.0 | 2980.0 | 280.0 |
| tile_band | 2980.0 | 3000.0 | 20.0 |
| z2_top_rdl | 3000.0 | 3010.0 | 10.0 |

### Z1

**single** — 16 layers, span 5333.0 um, sum of thicknesses 5333.0 um, conserved = True

| layer | z0 | z1 | t |
|---|---:|---:|---:|
| board | -0.0 | 2400.0 | 2400.0 |
| bga | 2400.0 | 2700.0 | 300.0 |
| sub_lower | 2700.0 | 2980.0 | 280.0 |
| tile_band | 2980.0 | 3000.0 | 20.0 |
| z1conv_0_bottom_substrate_rdl | 3000.0 | 3010.0 | 10.0 |
| z1conv_1_gan_hs_EPC2014C | 3010.0 | 3695.0 | 685.0 |
| z1conv_2_interlayer_rdl | 3695.0 | 3705.0 | 10.0 |
| z1conv_3_gan_ls_EPC2057 | 3705.0 | 4343.0 | 638.0 |
| z1conv_4_interlayer_rdl | 4343.0 | 4353.0 | 10.0 |
| z1conv_5_flying_caps | 4353.0 | 4453.0 | 100.0 |
| z1conv_6_interlayer_rdl | 4453.0 | 4463.0 | 10.0 |
| z1conv_7_inductor_plus_cout | 4463.0 | 4963.0 | 500.0 |
| z1conv_8_output_rdl | 4963.0 | 4973.0 | 10.0 |
| interface | 4973.0 | 4983.0 | 10.0 |
| die | 4983.0 | 5283.0 | 300.0 |
| tim | 5283.0 | 5333.0 | 50.0 |

## What 'IMPLEMENTED' means here, and what it does not

The converter rows above are a **geometry** result. The mesh carries 49 discrete footprints, eight tiers at their specified depths, a 1963 um total, the high-side device explicitly present and deepest, and no converter medium outside a cell footprint.

It is **not** a material result. Each tier is meshed at a medium that already exists in the framework, because the geometry gate does not license inventing material data. The flying-capacitor tier in particular is meshed at the homogenized converter medium, which an MLCC ceramic/Ni stack is not; that tier's material is **OPEN**. The GaN devices are meshed as their silicon carrier, with the epi unresolved, and that is **BOUNDED**.

## Out-of-cell region

The opening is 23.36^2 = 545.69 mm2 and the 49 cells occupy 274.89 mm2, so **49.6 % of the opening** is outside a cell. The 69.5 % figure quoted in the brief is the fraction of the 30 x 30 mm substrate footprint, which was the governing number while the converter was a full-area slab; now that the converter exists only inside the cutout, 49.6 % is the one that applies.

Both cases build: **F1 encapsulated** (primary, `underfill_homog`) and **F2 void** (elements are never created -- genuinely no material, not an air-property relabel). The final mechanical result must be reported across the bracket; that has not been run.
