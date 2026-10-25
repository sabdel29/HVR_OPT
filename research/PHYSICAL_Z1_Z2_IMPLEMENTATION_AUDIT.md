# Physical Z1/Z2 implementation audit

Phase 0N-W. **Every row is evaluated at run time** by `scripts/phase0nw/audit_physical_gates.py`: the config is loaded, the mesh is built, and the measured geometry decides the status. Nothing here is typed by hand, because a hand-typed status table goes stale a phase after it is written.

**44 of 98 gates are OPEN.** No physical ETM result lineage may be created while that number is non-zero.

Maturity is reported by status rather than collapsed into "closed", because SPECIFIED and IMPLEMENTED are not the same claim and neither is VALIDATED:

| status | count |
|---|---:|
| IMPLEMENTED | 40 |
| SPECIFIED | 14 |
| VALIDATED | 0 |
| OPEN | 44 |

So **54 of 98 are non-open**, of which only 40 are IMPLEMENTED and **0 are VALIDATED**. Nothing in this package has been validated against a solve yet.

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
| Electrical | TSV minimum from an exact integer lattice sweep | **IMPLEMENTED** | every n from 2 upward is enumerated. Z2 minimum is 64 (8x8, 9.83 mV vs a 10 mV budget); 7x7 = 49 fails at 12.71 mV. The previous sparse-pitch search reported 81 because its pitch set landed on n = 9 and n = 6 and skipped n = 8 entirely |
| Electrical | BGA power-ball count recomputed from the ledger current | **SPECIFIED** | I_in 23.6936 A at 1.5 A/ball needs 16+16; 16+16 gives 24.0 A, margin 1.28 %. Recomputed dynamically, NOT frozen: +20 W of additional loss already requires 18+18. Stays SPECIFIED until the physical ledger replaces the placeholder |
| Electrical | BGA loss recomputed on the physical geometry | **OPEN** | a source-backed bulk-BGA DC/equal-sharing LOWER BOUND now exists (21.78 mW for Z1), but the final physical BGA loss remains open pending RMS-current and network-sharing closure |
| Electrical | microbump loss recomputed on the physical geometry | **OPEN** | microbump loss still has only the Phase-0M-R3C value, which was computed on the OLD geometry and may be used as a reference but never as a physical result |
| Electrical | package RDL loss, HV rail recomputed on the physical geometry | **OPEN** | package RDL loss, HV rail still has only the Phase-0M-R3C value, which was computed on the OLD geometry and may be used as a reference but never as a physical result |
| Electrical | package RDL loss, LV rail recomputed on the physical geometry | **OPEN** | package RDL loss, LV rail still has only the Phase-0M-R3C value, which was computed on the OLD geometry and may be used as a reference but never as a physical result |
| Electrical | intra-VR horizontal routing loss recomputed on the physical geometry | **OPEN** | intra-VR horizontal routing loss still has only the Phase-0M-R3C value, which was computed on the OLD geometry and may be used as a reference but never as a physical result |
| Electrical | intra-VR vertical via-stack loss recomputed on the physical geometry | **OPEN** | intra-VR vertical via-stack loss still has only the Phase-0M-R3C value, which was computed on the OLD geometry and may be used as a reference but never as a physical result |
| Electrical | contact / UBM / IMC resistance modelled or bounded | **OPEN** | the power-path library carries R_contact = 0 with status OPEN; zero is 'not modelled because unsourced', NOT 'physically negligible', and the distinction must survive into the manuscript |
| Electrical | 10 um RDL electrical (resistance) model closed or bounded | **OPEN** | the mechanical/thermal tensor is bracketed, but the electrical sheet resistance of the actual 10 um tier -- Cu thickness, occupancy, routing layer count, supply/ground split -- is not yet defined |
| Electrical | Z1-specific TSV sizing | **SPECIFIED** | 48 V rail, 480 mV budget. N_electrical = 2 (1 VDD + 1 return, 7.51 mV); N_checkerboard = 4. The second is a SYMMETRY floor, not a requirement -- Z2's bracket does not apply to Z1 |
| Electrical | Z2-specific TSV sizing | **SPECIFIED** | 1 V rail, 10 mV budget: 64 / 729 / 1444 vias/cell |
| TSV | thermal/mechanical sensitivity to TSV density | **OPEN** | the adopted field is 1444 vias/cell, 23x the electrically required minimum, so Cu volume fraction -- and therefore substrate k, E and CTE -- depends strongly on a choice no solve has tested |
| TSV | TSV copper represented consistently in the FE model | **OPEN** | the substrate currently carries the historical tsv_homog fraction, which is not tied to the adopted TSV density; electrical rails are separated analytically while thermal/mechanical Cu would be one co-located homogenized field, and that is not yet implemented or stated in the mesh |
| Electrical | complete rail-aware power-path graph for both architectures | **IMPLEMENTED** | Z1 15 segments, Z2 15, 48 V board to 1 V die with supply and return enumerated separately; chain continuity and rail assignment checked. Z1 and Z2 draw INDEPENDENT 48 V currents (23.6936 A and 23.7429 A, from their own loss totals); the substrate TSVs carry 48 V in Z1 and 1000 A at 1 V in Z2. Return chains are continuity-checked end to end and must terminate at PCB ground |
| Electrical | every physical conductor has exactly one ledger owner | **IMPLEMENTED** | 19 declared owners (7 converter-intrinsic + 12 interconnect); every interconnect owner has at least one segment, no segment has two, converter-intrinsic terms are forbidden from owning a conductor, and an unknown owner raises. STRUCTURE only -- 10 Z1 and 10 Z2 segments still have OPEN loss values and 5 carry Phase-0M-R3C references |
| RMS | avg, RMS and peak current defined per rail | **IMPLEMENTED** | branch I_avg 6.8027 A (= I_cell*B_i/sum(B), NOT 20.4) is KNOWN; cell output rms/avg 1.00808 is KNOWN from the model's own aggregate ripple. Individual branch ripple and RMS are WITHDRAWN and OPEN |
| RMS | branch average currents | **IMPLEMENTED** | I_branch = I_cell*B_i/sum(B) = 6.8027 A, with B_array built by generate_B_array() in the pinned source |
| RMS | aggregate output ripple | **IMPLEMENTED** | 9.0043 A pp, the converter model's own expression |
| RMS | individual branch waveforms | **OPEN** | WITHDRAWN in Phase 0N-AD. Decomposing the summed output ripple into per-branch terms over D*T does not give a branch's periodic waveform; volt-second balance on a conventional branch gives 4.6574 A on both ramps against the 0.310 A previously claimed for phase B. The pinned source has no switch-state sequence to settle it |
| RMS | 48 V input waveform | **OPEN** | no SC charge-transfer sequence, phase displacement or dead time in the pinned source; see research/phase0nad/HVR_SWITCH_STATE_SOURCE_AUDIT.md |
| RMS | RMS scenario framework | **IMPLEMENTED** | L0 DC lower bound; L1A aggregate quantities the converter model genuinely provides; L1B explicit named SCENARIOS (HV-S0 continuous, HV-S1 square at D). L2 is NOT built and cannot be from the pinned source |
| RMS | 48 V rail RMS current | **OPEN** | THREE named SCENARIOS, not a bracket: HV-S0 continuous 23.69 A, HV-S1 square pulse at the buck duty 94.77 A, HV-S2 square pulse at the overall ratio 164.15 A (the duty the DVPD source's Eq.(5) assumes). S1 and S2 are MINIMUM RMS values for their supports, NOT upper bounds; NONE EXISTS from average current alone. Z1 BGA supply spans 10.9 / 174 / 523 mW |
| RMS | 1 V substrate rail RMS current | **IMPLEMENTED** | per-cell rms/avg = 1.008078 from the model's own aggregate ripple. The 49 TSV fields are ELECTRICALLY SEPARATE, so P = 49*I_cell_rms^2*(R_VDD+R_GND) with no cross terms and inter-cell phase cannot enter. Z2 substrate TSV loss is RMS-CLOSED at 213.0 mW per rail |
| RMS | source-backed bulk BGA DC lower bound | **IMPLEMENTED** | Z1 10.889 mW supply at equal sharing and I_avg; single-ball bulk R 0.310 mOhm, consistent with the source's ~0.3 mOhm |
| RMS | BGA loss uses RMS current | **OPEN** | blocked by elec.z1_hv_rms_current: the 48 V RMS is a bracket |
| RMS | BGA current sharing from the RDL network | **OPEN** | equal sharing is assumed and flagged a lower bound; no package RDL network exists to produce the real split |
| RMS | one canonical copper resistivity | **IMPLEMENTED** | tsv_fields carried its own 16.8 nOhm.m ASSUMPTION against phase0m's 17.0 nOhm.m SOURCE_BACKED; now imported, 17.0 nOhm.m everywhere |
| RMS | TSV conducting diameter resolved against the source resistance | **IMPLEMENTED** | 30 um as CONDUCTING Cu diameter gives 7.215 mOhm, matching the source's ~7.1 mOhm; subtracting the 0.5 um liner gives 7.721 mOhm and does not. Electrical conducting diameter and mechanical outer diameter are now distinct |
| PkgRDL | continuous Z1 package HV RDL exists | **IMPLEMENTED** | 2-D sheet over the 30 mm substrate, 16 supply contacts to 49 cell nodes, full lattice beneath the cell grid, offset half a ball pitch (no cutout to cross); R_eff 0.3161 mOhm at RDL_T2_RDL_M |
| PkgRDL | continuous Z2 package HV RDL exists | **IMPLEMENTED** | same sheet but sources restricted to the surviving annulus (cutout removes the interior); R_eff 1.6226 mOhm, 5.13x Z1 because the 48 V must cross the 23.36 mm opening laterally |
| PkgRDL | RDL electrical sheet model | **SPECIFIED** | R_sq = rho_Cu(T)/(t_Cu*occupancy), independent of the thermal tensor. t_Cu swept 2/5/10 um (BOUNDED_FROM_LITERATURE, 10 um scale from TVLSI 2022 CLOSE_ANALOG) x occupancy 0.80/0.30 (BOUNDED_ENGINEERING). The DVPD source explicitly defers trace dimensions to process technology |
| PkgRDL | package RDL network converged | **OPEN** | NOT CONVERGED. Threshold 1 % on R_eff was declared before any result was read; four levels (41/61/81/101) give 1.22 % for Z2 and 6.64 % for Z1. Finite-area contacts already removed the point-source log singularity that made the first attempt diverge; the residual is reported rather than absorbed by loosening the threshold |
| Interface | primary die-side interface technology selected | **IMPLEMENTED** | IF_PAD_SRC (Table III Cu pad) is primary; IF_MB_ALT (Cu pillar + solder + UBM + IMC) is an ALTERNATIVE technology only. The source's R_c of 1.7 mOhm is exactly bulk Cu to 0.00 %, which is consistent with a pad and inconsistent with a solder microbump carrying IMC and contact terms |
| Interface | source pad geometry verified | **IMPLEMENTED** | Table III RDL/Chiplet read directly from arXiv:2606.28837: d_c 10 um, h_c 10 um, p_c 20 um, A_c 100 um^2. The pad is square_10x10_um: a circular reading of d_c gives 78.54 um^2 and contradicts the source's own A_c |
| Interface | source pad resistance reproduced | **IMPLEMENTED** | rho_Cu*h/A = 1.7000 mOhm against Table III's 1.7 mOhm, 0.00 % apart. The published value contains NO contact, UBM or IMC term. A circular misreading would give 2.165 mOhm |
| Interface | pad count sized for the 49-cell design | **SPECIFIED** | 4908 per rail per cell, geometry-limited; the drop-limited count is only 4. The source's 200,000 VIC allocation is NOT copied -- its semantics are AMBIGUOUS -- the paper does not state wh... and it optimized a 70-VR architecture |
| Interface | pad interface loss | **IMPLEMENTED** | P_pad_VDD = P_pad_GND = 7.184 mW at T_ref, CLOSED because the 1 V cell output RMS is known from the converter model |
| Interface | branch phase group derived from the generator, not the index | **IMPLEMENTED** | generate_B_array() interleaves distA and distB, giving A,B,A for N=3 K=3 K_A=2. The naive 'A if k < K_A else B' gives A,A,B and was wrong; B_array [1,1,1] alone cannot distinguish them |
| Recompute | BGA solder alloy provenance | **SPECIFIED** | Table III footnote b gives 'Solder resistivity: 130 nOhm.m, Cu resistivity: 17 nOhm.m' and names the BGA material only as 'solder' -- the alloy is still not stated, so the model does not assert SAC305. The RESISTIVITY is sourced separately: 130 nOhm.m, SOURCE_BACKED -- June-2026 via scripts/phase0m/interconnect.py. Alloy itself: OPEN -- the design source does not state the alloy |
| Recompute | BGA resistivity is temperature dependent | **IMPLEMENTED** | rho_solder(T) = 130 nOhm.m x (1 + 4.0e-03(T-20)); alpha is an ASSUMPTION. Recomputed BGA loss at 20 C: Z1 21.78 mW, Z2 21.87 mW (equal-sharing lower bound) |
| Recompute | microbump field geometry defined | **OPEN** | SUPERSEDED as the primary interface by the source Cu pad (elec.source_pad_*). The arbitrary microbump bracket is retained only as legacy_sensitivity and no longer drives any ledger term |
| Recompute | microbump modelled as a series ladder with an explicit contact term | **SPECIFIED** | R = R_bulk + R_constriction + R_contact, with r_contact = 0 labelled the IDEAL-CONTACT LOWER BOUND rather than a claim of zero |
| Recompute | TSV landing/transition resistance audited against the existing spreading term | **SPECIFIED** | 10.1145/3698364.3705353 describes DC crowding where current TURNS between landing pad, via and TSV. The two-ended constriction already modelled is the plane-to-via-mouth convergence. They may be different effects; no second factor is added until that is established, because adding one would double-count. Recomputed TSV loss: Z1 0.235 mW, Z2 419.2 mW |
| Literature | DOI-backed provenance matrix for interconnect assumptions | **IMPLEMENTED** | 16 DOIs resolved via Crossref/OpenAlex: 0 DIRECT, 5 CLOSE_ANALOG, 11 CONTEXT_ONLY. research/phase0naa/interconnect_literature_matrix.csv |
| Literature | 1.5 A/ball examined against the literature | **SPECIFIED** | our BGA runs at 1178 A/cm2 NOMINAL, only 1.95x below the MILDEST accelerated EM condition in 10.1016/j.jmrt.2023.12.187 (2300 A/cm2 at 160 C). That paper also reports ~22x crowding at ITS UBM contact; that factor is NOT transferred here and our local J stays OPEN pending a pad/RDL solve of this package. 1.5 A/ball is a BOUNDED provisioning rule, NOT an EM-safe limit; no lifetime claim is made |
| Literature | microbump contact/UBM/IMC resistance bounded from literature | **OPEN** | 10.1109/EPTC.2015.7412351 shows microbump resistance RISES as solder converts to Cu6Sn5 then Cu3Sn, so R_contact = 0 is 'not modelled', not 'negligible'. No transferable value for our geometry was found; the two most on-point papers (ICEPT 2026, TCPMT 2026) have no retrievable abstract in this environment |
| Literature | TSV current-density allowable sourced or explicitly refused | **OPEN** | the 1 MA/cm2 in 10.1016/j.microrel.2015.05.019 is an accelerated stress condition, not an allowable; 10.1109/TED.2023.3307505 and 10.1016/j.ijmecsci.2025.110758 both show J alone is insufficient without T and stress. No allowable is asserted |
| Configuration | Z1 YAML drives the Z1 mesh | **IMPLEMENTED** | build_physical_z1 takes a Z1Package from configs/phase0nx/z1_physical.yaml (300 um substrate, 9 tiers, 48 V rail) and REFUSES a Z2 PhysicalPackage |
| Electrical | TSV count justified by a design criterion | **SPECIFIED** | three-point study: N_min_drop 64, N_mid 729, N_max_density 1444; adopted = max_density |
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
| TSVs per cell | 722 | 722 |
| TSVs, system | 35378 | 35378 |
| Cu area fraction | 0.0910 | 0.0910 |
| current per via (mA) | 28.27 | 28.27 |
| current density (A/cm2) | 3999 | 3999 |
| field resistance (uohm) | 9.993 | 9.993 |
| spreading resistance (uohm) | 0.277 | 0.277 |
| loss per cell (mW) | 4.28 | 4.28 |

Geometry is the SOURCE_BACKED 30 um / 60 um pitch over a 300 um substrate, checkerboard-interleaved on a 38x38 lattice so every VDD via has GND nearest neighbours. Both fields are symmetric about the cell centre to machine precision, so neither rail sees a systematically different thermal or mechanical environment.

**R_loop = 20.541 uohm**, against 19.986 uohm for the naive `2 R_field`. Constriction at the via mouths contributes 2.7 % of the loop, so the naive form UNDER-predicts by 2.7 %. That is a small correction here, but it was computed rather than assumed, which is what the brief asks for. System TSV loss 0.419 W.

**These fields are not yet meshed as distinct regions** -- the model is analytical and the gate stays OPEN.

## The two TSV rails are electrically different

Same via geometry. The rail CURRENT differs by more than 40x, and because Joule loss goes as I^2 the TSV LOSS differs by roughly three orders of magnitude. The two ratios are different numbers and must not be quoted interchangeably. A single 1000 A model applied to both erased the distinction entirely.

| | Z1 | Z2 |
|---|---:|---:|
| rail | 48 V input | 1 V output |
| system current | 23.694 A | 1000 A |
| per-cell current | 0.4835 A | 20.408 A |
| system TSV loss | 0.2353 mW | 419.2 mW |

| ratio (Z2/Z1) | | **42.2x current, 1781x loss** |

Z1's current is **a placeholder**: Phase-0M-R3C electronics LOSS + load (PLACEHOLDER). It is I = (P_load + P_loss)/48 V = (1000 + 137.292)/48 = 23.6936 A, and cannot be final until the physical electrical solution replaces the loss term. Z2's is the 1 V load current and must still be updated self-consistently with losses.

**A previous version divided the LOSS by 48 V**, giving 2.86 A -- low by 8.3x in current and 69x in I^2 R. P_total_electronics_w in the frozen replay is exactly sum(L_P_*), i.e. a loss total, not an input power.

**Two consistency problems this exposes.** The framework's own `zarch.rail_currents()` uses a FIXED Phase-0F efficiency eta = 0.889, giving 23.4346 A and an implied loss of 124.86 W -- 12.43 W below the 137.29 W the ETM ledger actually reports, so the canonical current is about 10 % inconsistent with the framework's own losses. And the BGA supply allocation (16 balls x 1.5 A = 24.0 A) was sized against the eta-based 23.4346 A; against the ledger-derived 23.6936 A the margin is only 1.3 %, so any further loss growth makes 16 balls insufficient.

### The TSV count is a choice, and the adopted one is the maximum

Declared budget: 1 % of the rail (10 mV). BOUNDED -- declared engineering budget, not a sourced allowable. No validated em/current-density allowable exists for this via geometry, so none is asserted; the field is bracketed by voltage drop and geometry instead.

| point | pitch | lattice | N | drop | % of rail |
|---|---:|---:|---:|---:|---:|
| n_min_electrical (1 VDD + 1 GND) | - | 1+1 | 2 | 317.163 mV | 31.716 % |
| min_drop | 324 um | 8x8 | 64 | 9.828 mV | 0.983 % |
| mid | 87 um | 27x27 | 729 | 0.842 mV | 0.084 % |
| max_density | 61 um | 38x38 | 1444 | 0.420 mV | 0.042 % |

**Adopted: max_density, 1444 vias/cell.** the mechanical and thermal models need the copper volume fraction to be an upper bound on stiffening and spreading; the ELECTRICAL bracket is reported alongside so the sensitivity is visible. This is a MAXIMUM-DENSITY field at the SOURCE_BACKED 60 um minimum pitch, explicitly not a minimum-required one.

THREE DIFFERENT NUMBERS, PREVIOUSLY CONFLATED. The voltage-drop floor is 2 vias (1 VDD + 1 return). The smallest SYMMETRIC checkerboard that passes is 64. The adopted field is 1444, 23x the symmetric minimum. the gap between n_min_electrical and n_min_checkerboard is a SYMMETRY/representability choice, not a physical requirement. No EM or redundancy criterion is invented to justify it.

The earlier sparse-pitch search reported a Z2 minimum of 81. It is 64: an 8x8 field drops 9.71 mV against the 10 mV budget and 7x7 drops 12.71 mV. The old pitch set landed on n = 9 and n = 6 and never evaluated n = 8.

### Spreading resistance is counted at BOTH ends

R_loop = R_vdd + R_gnd + 2 R_spread,vdd + 2 R_spread,gnd = 20.541 uohm. Current converges out of the plane into the via mouths at one end and diverges back out at the other, so each rail carries two constrictions -- Holm's contact resistance, rho/(2a) per via rather than rho/(4a). The earlier version charged one end per rail. Correcting it moved the spreading share from 1.4 % to 2.7 % of the loop and the naive 2 R_field error from -1.4 % to -2.7 %. A modest change, reported as a modest one.

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
