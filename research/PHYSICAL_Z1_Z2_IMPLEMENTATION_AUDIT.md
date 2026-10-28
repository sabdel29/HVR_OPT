# Physical Z1/Z2 implementation audit

Phase 0N-W. **Every row is evaluated at run time** by `scripts/phase0nw/audit_physical_gates.py`: the config is loaded, the mesh is built, and the measured geometry decides the status. Nothing here is typed by hand, because a hand-typed status table goes stale a phase after it is written.

**26 of 115 gates are OPEN.** No physical ETM result lineage may be created while that number is non-zero.

Maturity is reported by status rather than collapsed into "closed", because SPECIFIED and IMPLEMENTED are not the same claim and neither is VALIDATED:

| status | count |
|---|---:|
| IMPLEMENTED | 59 |
| OPEN | 26 |
| SPECIFIED | 27 |
| SUPERSEDED | 3 |
| **total** | **115** |

So **89 of 115 are non-open**, of which only 59 are IMPLEMENTED and **0 are VALIDATED**. Nothing in this package has been validated against a solve yet. 3 gate(s) are SUPERSEDED: the model they describe has been replaced, and they are retained only so the replaced result cannot quietly return as a current one.

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
| Electrical | BGA loss recomputed on the physical geometry | **SPECIFIED** | per named scenario from the solved per-ball split at the matched N = 54; SPECIFIED because the 48 V RMS waveform is scenario-defined |
| Electrical | package RDL loss, HV rail recomputed on the physical geometry | **SPECIFIED** | SUPERSEDES 'still has only the Phase-0M-R3C value', which is false at HEAD. The HV rail is recomputed from the solved voltage-fed network for Z2, with supply and return as separate conductors and per-scenario I_rms^2 R losses in research/phase0nab/interconnect_loss.json. Z1 is still OPEN because its network fails the 1 % convergence test. SPECIFIED, not IMPLEMENTED, while any architecture remains open and while the RMS waveform stays scenario-defined. |
| Electrical | microbump loss recomputed on the physical geometry | **OPEN** | microbump loss still has only the Phase-0M-R3C value, computed on the OLD geometry; usable as a reference, never as a physical result. The HV package rail is NOT in this list any more -- it is recomputed (elec.package_rdl_hv_recomputed) -- so this gate no longer implies that nothing has been recomputed |
| Electrical | package RDL loss, LV rail recomputed on the physical geometry | **SPECIFIED** | STRUCTURALLY ABSENT in the production geometry: the source-pad field sits over each tile, so 1 V leaves the package above the cell and the in-tile collection is owned by the R2 output plane. The alternative (pads over the full pitch) is quantified, not asserted: about 0.59 W for both rails |
| Electrical | intra-VR horizontal routing loss recomputed on the physical geometry | **SPECIFIED** | recomputed on the physical tiers under the declared fidelity policy: R0 width rule for point-to-point traces, R0 via stacks, R2 refined sheet for the output plane (R0 overstates it 37-258 %). HV nets carried per named scenario. SPECIFIED: via heights come from the layout model's tier spacing |
| Electrical | intra-VR vertical via-stack loss recomputed on the physical geometry | **SPECIFIED** | recomputed on the physical tiers under the declared fidelity policy: R0 width rule for point-to-point traces, R0 via stacks, R2 refined sheet for the output plane (R0 overstates it 37-258 %). HV nets carried per named scenario. SPECIFIED: via heights come from the layout model's tier spacing |
| Electrical | contact / UBM / IMC resistance modelled or bounded | **OPEN** | the power-path library carries R_contact = 0 with status OPEN; zero is 'not modelled because unsourced', NOT 'physically negligible', and the distinction must survive into the manuscript |
| Electrical | 10 um RDL electrical (resistance) model closed or bounded | **OPEN** | the mechanical/thermal tensor is bracketed, but the electrical sheet resistance of the actual 10 um tier -- Cu thickness, occupancy, routing layer count, supply/ground split -- is not yet defined |
| Electrical | Z1-specific TSV sizing | **SPECIFIED** | 48 V rail, 480 mV budget. N_electrical = 2 (1 VDD + 1 return, 7.51 mV); N_checkerboard = 4. The second is a SYMMETRY floor, not a requirement -- Z2's bracket does not apply to Z1 |
| Electrical | Z2-specific TSV sizing | **SPECIFIED** | 1 V rail, 10 mV budget: 64 / 729 / 1444 vias/cell |
| TSV | thermal/mechanical sensitivity to TSV density | **OPEN** | the adopted field is 1444 vias/cell, 23x the electrically required minimum, so Cu volume fraction -- and therefore substrate k, E and CTE -- depends strongly on a choice no solve has tested |
| TSV | TSV copper represented consistently in the FE model | **IMPLEMENTED** | sub_lower and tile_band hold the adopted 1444-via field: 18.2 % Cu inside the 49 tiles, plain silicon outside, replacing a 19.6 % fraction smeared over the whole 900 mm^2 |
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
| RMS | source-backed bulk BGA DC lower bound | **IMPLEMENTED** | Z1 10.889 mW supply at equal sharing and I_avg; single-ball bulk R 0.310 mOhm, consistent with the source's ~0.3 mOhm. 'At equal sharing' is a DECLARED PROPERTY OF THIS BASELINE TERM, not a framework assumption: elec.bga_network_sharing solves the real split and finds it unequal, so this row is a reference figure and must not be used to size balls |
| RMS | BGA loss uses RMS current | **OPEN** | SUPERSEDES the evidence 'the 48 V RMS is a bracket'. HV-S0/S1/S2 are NAMED SCENARIOS, not a bracket and not lower/nominal/upper: from an average current alone there is no finite RMS upper bound, because a narrower, taller pulse of the same average has strictly higher RMS without limit. Blocked by elec.hv_waveform_determination, which proves the waveform is not derivable from the pinned converter model |
| RMS | BGA current sharing from the RDL network | **IMPLEMENTED** | SUPERSEDES the evidence 'equal sharing is assumed ... no package RDL network exists to produce the real split', which was true when written and is false at HEAD. The voltage-fed network solves the split: under a UNIFORM load the balls carry 0.0311-0.0957 A against the 0.0625 A equal sharing would give, a spread of 103.4 % of the mean, and the peak moves with the load. Equal sharing is therefore not merely unproven, it is DISPROVEN for this geometry, which invalidates any I_total/N_ball per-ball current used as a sizing criterion |
| RMS | one canonical copper resistivity | **IMPLEMENTED** | tsv_fields carried its own 16.8 nOhm.m ASSUMPTION against phase0m's 17.0 nOhm.m SOURCE_BACKED; now imported, 17.0 nOhm.m everywhere |
| RMS | TSV conducting diameter resolved against the source resistance | **IMPLEMENTED** | 30 um as CONDUCTING Cu diameter gives 7.215 mOhm, matching the source's ~7.1 mOhm; subtracting the 0.5 um liner gives 7.721 mOhm and does not. Electrical conducting diameter and mechanical outer diameter are now distinct |
| PkgRDL | continuous Z1 package HV RDL exists | **IMPLEMENTED** | 2-D sheet over the 30 mm substrate, 16 supply contacts to 49 cell nodes, BGA_P1/nearest_symmetric: 16+16 from full lattice (1369 candidates); R_eff 1.7849 mOhm at RDL_T2_RDL_M |
| PkgRDL | continuous Z2 package HV RDL exists | **IMPLEMENTED** | same sheet but sources restricted to the BGA_P1/nearest_symmetric: 16+16 from annulus (cutout removes the interior) (528 candidates); R_eff 1.4337 mOhm. THE RATIO TO Z1 IS WITHDRAWN as a physical conclusion: it is unconverged (5.13x at 61x61 against 4.53x at 101x101) and contaminated by a hard-coded 3.0 mm cell pitch against the actual 3.165243 mm, synthetic non-lattice Z1 sources, BGA contacts smaller than the grid spacing, and imposed equal source currents. Preliminary unconverged network observation only |
| PkgRDL | RDL electrical sheet model | **SPECIFIED** | R_sq = rho_Cu(T)/(t_Cu*occupancy), independent of the thermal tensor. t_Cu swept 2/5/10 um (BOUNDED_FROM_LITERATURE, 10 um scale from TVLSI 2022 CLOSE_ANALOG) x occupancy 0.80/0.30 (BOUNDED_ENGINEERING). The DVPD source explicitly defers trace dimensions to process technology |
| PkgRDL | BGA modelled as voltage-fed branches rather than imposed currents | **IMPLEMENTED** | a rail node feeds each ball through its own Table III series resistance (0.3104 mOhm, rho_solder*h/A) and a finite contact, so the split is an OUTPUT. Under a UNIFORM load the balls carry 0.0311-0.0957 A against the 0.0625 A the imposed model forced on every ball, a spread of 103.4 % of the mean; moving half the load to one corner cell widens it to 129.5 % |
| PkgRDL | package return RDL network solved | **IMPLEMENTED** | supply and return are two separate sheets, each with its own sites, solved separately and added in series. Z1 R_supply 0.8063 + R_return 0.4382 = 1.2445 mOhm; Z2 0.7666 + 0.5996 = 1.3662 mOhm. The return leg was previously computed and DISCARDED, so every earlier package RDL resistance understated the loop by 54 % (Z1) and 78 % (Z2) |
| PkgRDL | cutout penalty isolated from BGA-placement penalty | **SPECIFIED** | CTRL_FULL is BIT-IDENTICAL to Z1 and CTRL_CUTOUT to Z2 (verified on R_supply and R_return), so dR_cutout IS the Z1/Z2 loop difference expressed as a difference -- which means it inherits Z1's convergence failure and cannot be called IMPLEMENTED. What survives that failure is the SIGN: Z1's worst R_eff drift over the final refinement is 1.4101 %, bounding its loop resistance to 0.01755 mOhm, against a cutout term of +0.1217 mOhm -- a factor of 7. re-run on the voltage-fed, loop-inclusive, contact-resolved model. dR_cutout = +0.1217 mOhm against dR_placement = +3.6030 mOhm (29.60x). THE SIGN OF THE CUTOUT TERM FLIPPED: the imposed-current model read -0.351 mOhm (the cutout appearing to HELP) and the corrected model reads +0.1217 mOhm. The earlier conclusion that the cutout penalty was a placement artefact 'in both magnitude and sign' was itself an artefact of imposing equal ball currents and discarding the return conductor. Placement still moves the answer more than the cutout does, but by 29.60x rather than 5.8x, and dR_placement contrasts two DELIBERATELY OPPOSITE rules (nearest-to-centroid against furthest), so it is a span, not a typical sensitivity |
| PkgRDL | superseded imposed-current cutout decomposition | **SUPERSEDED** | CTRL_FULL (1369 candidate sites) against CTRL_CUTOUT (528), with sheet, cells, ball count, allocation rule and grid all held identical: dR_cutout = -0.351 mOhm, i.e. the cutout slightly REDUCES resistance because nearest-to-centroid selection would otherwise cluster balls centrally. Changing only the rule on the same annulus moves R_eff 2.047 mOhm, so placement dominates the cutout by ~5.8x. SPECIFIED not IMPLEMENTED: Z1 remains unconverged and the sources are still current-fed |
| PkgRDL | package RDL network converged | **SPECIFIED** | convergence is now declared on ALL of r_eff_ohm, p_loss_w, max_cell_drop_v, i_ball_max_a, ball_imax_over_imean between the two finest of five levels, threshold 1 % set before any value was read. 2 of 4 networks pass: Z2_return, Z2_supply. FAILING: Z1_return at 1.0688 %, Z1_supply at 1.4101 %. SPECIFIED not IMPLEMENTED because Z1 still fails, for the third successive phase. The threshold is NOT relaxed to admit it. The earlier study checked R_eff ONLY at grids where a 400 um ball was sub-grid (h = 0.3 mm); the grid here is n = 601 (h = 50 um, ball spanning 8 cells) |
| PkgRDL | the BGA lattice is closed under negation | **IMPLEMENTED** | `-14.4 + i*0.8` drifts, so the mirror of (-14.4,-12.8) existed as (14.4, 12.800000000000002) and select_power_sites' exact-equality `mirror not in cand` discarded 1080 of 1369 full-lattice and 408 of 528 annulus sites -- about 79 % of the legal design space, chosen by floating-point luck. Every selection, package-RDL resistance and cutout experiment before this phase used that subset. Coordinates are snapped to 9 decimals; unpaired sites now 0 |
| PkgRDL | BGA count solved against a declared criterion | **SPECIFIED** | the adopted 16+16 came from I_total/N <= 1.5 A/ball, which presumes equal sharing -- disproven by the network. Solved peak at N=16 is 4.01 A (Z1) and 1.96 A (Z2), so the adopted count FAILS its own criterion even at the DC average. Required: 40 per rail (Z1), 24 (Z2). HV-S1/S2 are not satisfiable for Z2 in the legal lattice. SPECIFIED not IMPLEMENTED: the criterion is ENGINEERING_CRITERION with no source, and local crowding stays OPEN |
| PadCount | source-pad count bounded as a region | **SPECIFIED** | no single count is adopted: loss falls monotonically with N and only geometry bounds it from above, so every available criterion is one-sided. Admissible N is [256, 4908] at 1e5 A/cm^2 and [32, 4908] at the ACCELERATED-stress 1e6 A/cm^2 marker. The old voltage-drop floor of 4 pads/rail/cell implies 5.14e+06 A/cm^2 and is NON-PHYSICAL, so drop was never the binding constraint |
| Recompute | intra-VR fidelity levels compared, not merely listed | **SPECIFIED** | R1 is RETIRED: the obstacle router was repaired (blockage and detour now use ONE geometric test; it detours on a synthetic blocker, asserted by test) and still no physical net is obstructed, so R1 reproduces R0 for a real reason. R2 was being computed and never compared; R0 overstates the output-net loss by 37.2-258.3 %, so R0 is NOT adequate for that net. SPECIFIED: the graph is still on frozen R3C geometry and is not wired into the ledger |
| RMS | 48 V input current waveform closed | **OPEN** | DETERMINED UNRESOLVABLE from the present model, not merely unattempted. The pinned generator HVR_FULL_OPT_EPC_V2.py builds every electrical quantity from one scalar I_out_rms via the triangular-ripple identity; it contains no switched-capacitor state sequence, no flying-capacitor charge balance and no input-current variable, so the 48 V average comes only from power balance and no RMS follows from it. Closing it needs the per-state switch conduction table, the charge-transfer schedule, or a netlist. See research/phase0naj/HV_WAVEFORM_DETERMINATION.md |
| PkgRDL | the cause of Z1's non-convergence is isolated, not just observed | **IMPLEMENTED** | Z1 draws sites from the full lattice by nearest-to-centroid, so 8/16 supply and 8/16 return balls land beneath a VR cell tile and couple to it through rho_c instead of through the sheet; Z2's 23.36 mm cutout removes exactly those central sites and it has 0 and 0. Removing ONLY the overlapping candidates, at the identical 501->601 step: PARTIAL: removing the overlapping sites improves the worst metric but does NOT reach the 1 % threshold, so contact overlap is a contributing cause and not the whole cause: 1.4101 % -> 1.0902 % at the identical 501->601 step; worst metric p_loss_w -> p_loss_w; converged False -> False. CAUSE CONFIRMED: removing only the overlapping candidate sites takes this rail across the 1 % threshold: 1.0688 % -> 0.7858 % at the identical 501->601 step; worst metric max_cell_drop_v -> max_cell_drop_v; converged False -> True. Corroborated by the rho_c sweep, where Z1's loop resistance moves 1.58x across three decades against Z2's 1.12x |
| PkgRDL | superseded imposed-current convergence study | **SUPERSEDED** | Z2 NOW CONVERGES at 0.430 % after the ball counts were matched, but Z1 does not at 2.168 %. A ratio is only as converged as its worse half, so no architecture ratio is reportable. Threshold 1 % on R_eff was declared before any result was read; four levels (41/61/81/101) give 0.43 % for Z2 and 2.17 % for Z1. Finite-area contacts already removed the point-source log singularity that made the first attempt diverge; the residual is reported rather than absorbed by loosening the threshold |
| Interface | primary die-side interface technology selected | **IMPLEMENTED** | IF_PAD_SRC (Table III Cu pad) is primary; IF_MB_ALT (Cu pillar + solder + UBM + IMC) is an ALTERNATIVE technology only. The source's R_c of 1.7 mOhm is exactly bulk Cu to 0.00 %, which is consistent with a pad and inconsistent with a solder microbump carrying IMC and contact terms |
| Interface | source pad geometry verified | **IMPLEMENTED** | Table III RDL/Chiplet read directly from arXiv:2606.28837: d_c 10 um, h_c 10 um, p_c 20 um, A_c 100 um^2. The pad is source_effective_area: a circular reading of d_c gives 78.54 um^2 and contradicts the source's own A_c |
| Interface | source pad resistance reproduced | **IMPLEMENTED** | rho_Cu*h/A = 1.7000 mOhm against Table III's 1.7 mOhm, 0.00 % apart. The published value contains NO contact, UBM or IMC term. A circular misreading would give 2.165 mOhm |
| PkgRDL | one source of cell coordinates | **IMPLEMENTED** | physical_cell_coordinates() returns the FE placement's own 49 centres at 3.165243 mm pitch; the RDL solver had hard-coded 3.0 mm |
| PkgRDL | BGA sites are legal centred-lattice positions | **IMPLEMENTED** | 1369 legal sites at 0.8 mm pitch, 528 outside the cutout; the recorded annulus allocation is on-lattice, while the synthetic Z1 (+0.4, +0.4) offsets were NOT and are removed |
| PadCount | a physical criterion selects the pad count | **OPEN** | NONE EXISTS. The previous logic min(n_geom, max(n_drop, n_geom)) is identically n_geom, so it always chose maximum density and called it closed. Voltage drop gives a floor of 4, geometry a ceiling of 4908, and the source's allocation semantics are ambiguous |
| PadCount | pad count swept | **IMPLEMENTED** | 8 counts from 4 to 4908 per rail per cell; system interface loss spans 1227x (17.63 W to 0.014 W). Keepout swept 0.10/0.30/0.60. Counts [4, 10] sit at or above 1e6 A/cm^2, the regime 10.3390/ma14216394 associates with Cu-Cu bump EM -- CONTEXT_ONLY / RELIABILITY_WARNING -- not an allowable, not a safe limit, not a lifetime criterion |
| PadCount | pad interface loss closed | **OPEN** | loss is a COUNT SCENARIO spanning 1227x. The 14.37 mW previously reported as CLOSED was the maximum-density end of that span |
| Interface | pad count sized for the 49-cell design | **SPECIFIED** | drop floor 4, geometry ceiling 4908 per rail per cell, NO adopted value. The source's 200,000 VIC allocation is NOT copied -- its semantics are AMBIGUOUS -- the paper does not state wh... and it optimized a 70-VR architecture |
| Interface | pad interface loss | **SPECIFIED** | per-rail system loss 8.814 W at the drop floor against 7.184 mW at the geometry ceiling. One pad's geometry, its resistance and the cell current are closed; the FIELD COUNT is not, so the field loss is a scenario |
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
| Electrical | temperature-dependent TSV resistance in the fixed point | **IMPLEMENTED** | the TSV rows are evaluated at the converged substrate temperature inside the E-T loop; resetting only T_sub to 20 C changes the HV-S0 TSV loss by a factor 1.388 (Z1, T_sub 118.6 C) and 1.297 (Z2, T_sub 95.7 C) (research/final_closure/coupling_checks.json) |
| Electrical | package RDL loss recomputed on the physical geometry | **SPECIFIED** | SUPERSEDES 'no artifact exists', false at HEAD. Recomputed from the solved voltage-fed network for Z2: package HV supply/return carry I_rms^2 R scenario losses in research/phase0nab/interconnect_loss.json. Z1 remains OPEN because its networks fail the 1 % convergence test, so a loss taken from them would be a number resting on an unconverged resistance. SPECIFIED, not IMPLEMENTED, while any architecture is still open. |
| Electrical | superseded pre-network RDL loss status | **SUPERSEDED** | retained so the pre-network wording 'no artifact exists for RDL loss recomputed on the physical geometry' cannot return as a current claim; elec.package_rdl_hv_recomputed now carries the live status |
| Electrical | energy conservation verified on the physical heat map | **IMPLEMENTED** | heat-map deposition and the COMPUTED thermal heat balance close to 1e-06 in every case: True. The historical production path never computed the bottom heat flow -- it set q_bot = Q - q_top, so every earlier energy residual was zero by construction |
| Electrical | physical Z1/Z2 loss audit frozen | **IMPLEMENTED** | research/final_closure/electrical_ledger.json: 96 rows -- every conductor, both architectures, every named scenario, at the converged E-T temperatures, one owner each, no silent zeros; HV-S0 totals Z1 146.472 W, Z2 142.672 W |
| Thermal | tier-aware converter heat deposition | **IMPLEMENTED** | HS, LS, inductor and capacitor losses deposited in their own GaN / inductor / flying-cap tiers, confined to the 49 cell footprints. The first physical deposition spread each tier's loss over the out-of-cell encapsulant as well and produced a 362 C corner hot spot in an element carrying no device; confinement removed it |
| Thermal | physical thermal BC selected | **SPECIFIED** | one declared boundary for both: the same top Si microchannel cold plate (27 g/s, staggered fluid temperature) and the board-bottom film; Z2's converter underside faces the cutout and is adiabatic (Z2-PASSIVE). Z2-COOLED remains a B-class sensitivity |
| Thermal | Z2-PASSIVE case implemented | **IMPLEMENTED** | the physical Z2 lineage is the Z2-PASSIVE case: the bottom film sits only on the board underside (1632 faces, 0 inside the 23.36 mm cutout), so the converter underside in the cutout is adiabatic (research/final_closure/coupling_checks.json) |
| Thermal | Z2-COOLED case implemented | **OPEN** | not run -- no artifact exists for 'Z2-COOLED case implemented' |
| Thermal | ET fixed point converged | **IMPLEMENTED** | every case met the DECLARED 0.25 K / 1e-3 criteria within 8 iterations; worst final max|dT| 0.058 K |
| Thermal | PCB MOT/Tg checks evaluated | **OPEN** | not run -- no artifact exists for 'PCB MOT/Tg checks evaluated' |
| Thermal | H0 vs H1 thermal comparison run | **OPEN** | not run -- no artifact exists for 'H0 vs H1 thermal comparison run' |
| Mechanical | F1/F2 out-of-cell bracket run | **OPEN** | both cases BUILD; neither has been solved |
| Mechanical | physical mesh convergence | **IMPLEMENTED** | nested refinement of the production mesh (every in-plane interval split in two, and separately every layer split in two through the thickness): worst relative change of T_max, die warpage, critical du and loss = 1.299 % against the 2 % tolerance declared before the refined runs were read (PASS). Refined-mesh structural solves use ITERATIVE CHOLESKY, verified against SPOOLES on the production mesh. The earlier h_xy 1.1 -> 0.8 pair is not nested and is kept only as a re-meshing sensitivity. Mesh convergence, not validation |
| Mechanical | critical-joint search over all 528 surviving sites | **IMPLEMENTED** | every legal site searched (Z1 1369, Z2 528); the critical joint is the outermost lattice corner in both, (14.4, 14.4) mm, du = 2.374 (Z1) and 3.951 um (Z2) at HV-S0 -- found, not assumed |
| Mechanical | 2.4/3.2 T-only mechanical comparison | **OPEN** | not run -- no artifact exists for '2.4/3.2 T-only mechanical comparison' |
| Local | local solder rerun at the new critical site | **IMPLEMENTED** | validated local family rerun at the new critical joints after the harness reproduced the published control to 0.0000 %; response only, no life |
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
| Material | 10 um RDL tier tensor transfer validated | **IMPLEMENTED** | single-tier tensor from an explicit RVE in AEDT 2026 R1 Mechanical: k_x 34.28, k_z 0.620 W/mK; the analytic grid laminate agrees in-plane to -3.7 % and overstates k_z by +12.5 % (constriction), so the RVE values are adopted. The earlier Voigt in-plane value was 76 % too high |
| Results | physical ETM result lineage | **IMPLEMENTED** | final physical lineage executed for Z1 and Z2 in every named 48 V scenario: E-T fixed point, global thermoelastic FE, all-site joint search, local solder rerun. HV-S0: Z1 146.472 W / 121.58 C / 27.64 um warp; Z2 142.672 W / 120.59 C / 69.28 um warp (research/final_closure/final_results.json) |

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
