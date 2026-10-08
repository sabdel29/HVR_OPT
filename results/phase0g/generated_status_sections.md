<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml -- DO NOT EDIT BY HAND. -->
<!-- Regenerate with scripts/phase0g/generate_status_sections.py (DEFECT #29). -->

## Current scientific status (Phase 0M-R3C)

<!-- BEGIN GENERATED: current_state_contract -->
<!-- Generated from results/CURRENT_SCIENTIFIC_STATUS.yaml::current_state_contract
     by scripts/phase0mr/state_contract.py. DO NOT EDIT BY HAND. -->

| question | current answer | evidence |
|---|---|---|
| phase | **0M-R3C complete** | `results/phase0mr3c/PHASE0MR3C_REPARTITION_AND_PAPER_FREEZE.md` |
| verdict | **Phase 0M-R3C: PROCESS-CONDITIONAL REPARTITION FOUND; THE FINAL Z1/Z2 RESPONSE ORDERING SURVIVES (option B). Phase 0M-R3B counted three microvia levels from three MATERIAL layers; counting CONDUCTOR PLANES gives one (DEFECT #64), which withdraws its zero-feasible-configurations finding. A permutation of the existing components, T1C_REORDERED, makes the 20.408 A switch node an adjacent-tier RDL transition and drops the worst build-up aspect ratio from 5.05 to 0.83 at identical component set, per-tier area and 1921 um stack. One ETM replay on a pair frozen before solving gives D_driver_final = 1.1947 against the historical 1.1943, +0.04 %. Neither architecture is PROVEN_REALIZABLE: geometry closes, manufacturing does not.** | `results/phase0mr3a/LS_TO_L_INTERCONNECT_AUDIT.md` |
| ET coupling level | **ETM-L1: E <-> T iterated to a fixed point, T -> M one-way. Intact M -> E is 0.16 % of R against 22.8 % from rho(T); M -> T is 1.5 K for a 4 % TIM bond-line change. Neither is solved back.** | `results/phase0m/etm_feedback_magnitudes.csv` |
| mechanical capability | **Global thermoelastic warpage and stress (M0), plus a convergent local solder viscoplastic RESPONSE metric (M2) added in Phase 0I and verified in 0I-R. TWO of eight enumerated mechanisms are addressable, not one. RDL fracture, delamination, via fatigue, dielectric cracking, pad cratering and EM-assisted damage remain uncomputed.** | `results/phase0m/PHYSICS_PRIORITY_MATRIX.csv` |
| solder metric status | **AVAILABLE AND CONVERGENT, AND IT IS A RESPONSE. The FE quantity is a LOCAL FATIGUE-RELEVANT INELASTIC RESPONSE METRIC: accumulated equivalent inelastic strain per stabilised cycle, volume averaged over the solder core and matched to the Syed 25 um averaging volume. It is NOT damage, NOT life and NOT a failure criterion: those require a sourced damage law, a life model and an admissible allowable respectively, and none of the three is closed.** | `results/phase0i/local_metric_convergence.csv` |
| constitutive status | **CONDITIONAL. The creep card is fitted on Sn3.9Ag0.6Cu, NOT SAC305, over 7.51-15.92 MPa, while 99.8 % of the package's accumulated inelastic strain (dPEEQ*V) is generated outside that window. Two families can be PARAMETERIZED in the regime; only NORTON can be INTEGRATED through the production solve. This is the dominant open blocker.** | `results/phase0lr/ALLOY_TRANSFERABILITY_MATRIX.md` |
| life law status | **AVAILABLE FOR RELATIVE LIFE. The primary sources were obtained in Phase 0J-R and Syed 2004's author-corrected calibration was reproduced. HTTP 403 is NO LONGER the blocker; it was, in Phase 0J, and that statement is historical.** | `results/phase0jr/PHASE0JR_PRIMARY_LIFE_LAW_GATE.md` |
| required life status | **OPEN. No field or product requirement exists in this repository or any supplied source. It is NOT the sole G2 blocker -- Phase 0K withdrew that framing.** | `results/phase0k/G2_DECISION_REGIONS.md` |
| G2 status | **NOT TESTED, and not testable. THREE independent blockers, any one sufficient: N_required is OPEN, absolute N_f is unvalidated (the strain and energy formulations disagree 4.1x on this joint), and no admissible operational mechanical allowable exists (nine candidates tested against six admissibility conditions, none passed). Closing any one leaves the other two.** | `results/phase0h/criterion_admissibility.csv` |
| optimizer status | **FORBIDDEN. SIX preconditions stand at NO: intra-VR via technology sourced; process margin on the critical interconnect; dominant mechanical physics closed; an admissible mechanical criterion exists; a required life exists; absolute fatigue prediction validated. Phase 0M-R3C UPGRADED 'architecture templates realizable' from NO to PARTIAL: geometry now closes for a frozen pair, but four manufacturing inputs remain OPEN so it cannot reach YES.** | `results/phase0mr3a/final_open_items.md` |
| cooling status | **IN PRODUCTION, PHYSICAL, AND NOW REGIME-CHECKED. The production point at 27 g/s is laminar at Re = 1264.8 and inside the Shah & London correlation's validated domain, so every Phase-0M-R conclusion resting on it stands. Phase 0M-R2 found that the 50 g/s point Phase 0M-R quoted sits at Re = 2342, above the laminar ceiling of 2300 and below Gnielinski's floor of 3000, where the two neighbouring correlations differ by 2.76x: h = 166 000 W/m2K, dp = 1.46 MPa and P_pump = 74 W are WITHDRAWN as model outputs. An explicit dispatcher now returns OUT_OF_MODEL_DOMAIN there rather than extrapolating. Separately, at 27 g/s the thermal entrance length occupies 86 % of the channel, so the fully-developed Nusselt number understates h and the production temperature is CONSERVATIVE. Conjugate CFD validation is reported in results/phase0mr2/CONJUGATE_CFD_VALIDATION.md.** | `results/phase0mr2/cooling_regime_table.csv` |
| routing status | **IN PRODUCTION AND GEOMETRICALLY CORRECTED. Vertical spans are measured face to face (PHASE0MR3B_PHYSICAL_SPANS, used by the Phase-0M-R3C frozen pair), and via levels are counted from conductor planes rather than material layers. In the frozen partition ls_to_L and hs_to_cf are adjacent-tier RDL transitions at AR 0.083 and the only build-up via is hs_to_ls, 100 um at AR 0.833 carrying 1.435 A. n_required is FRAMEWORK PROVISIONING at J_design = 1e8 A/m2, a conservative design-side allocation, and is never a manufacturing qualification. A 3-D DC solve of one physical via column gives 1.16x the analytical series resistance from land spreading.** | `results/phase0mr/intravr_routing_by_template.csv` |
| crowding status | **IN PRODUCTION, PER CLASS, CROSS-VALIDATED. The global 1.326 constant is retired from every production path. Each interconnect class carries its own Delta_R = R_3D - R_1D, solved exactly at its production geometry and cached. Cross-validated against MOOSE (independent mesher, formulation and solver) on five geometries: 5/5 ACCEPTED at 0.25-0.73 %. Delta_R is a DIFFERENCE against a stated 1-D reference using identical terminals, NOT an excess: at the nominal TSV geometry it is NEGATIVE, so the retired constant was inflating the TSV tier by 32.6 %.** | `results/phase0mr/current_crowding_validation.csv` |
| RDL anisotropy status | **PROMOTED TO THE PRODUCTION THERMAL DEFAULT. The interface layer -- the one layer every watt crosses -- was isotropic underfill at k = 0.70 W/mK. Homogenising its own sourced microbump geometry (r = 5 um, pitch 20 um, h = 10 um) gives kxy = 0.891 and kz = 11.739 W/mK, i.e. 16.8x more conductive through thickness, within 0.55 % of the Voigt bound and 0.61 % of Maxwell-Garnett. Promotion moves peak temperature by about 7 K and the driver by about 6.7 %, and the Z1/Z2 ratio by 0.105 %: it matters for absolute numbers and changes no ordering.** | `results/phase0mr2/rdl_isotropic_vs_anisotropic.csv` |
| component partition status | **GEOMETRICALLY_REALIZABLE / PROCESS-CONDITIONAL, for both architectures. The frozen pair is T1C_REORDERED at a 120 um microvia on a 150 um pitch: worst aspect ratio 0.833, worst framework routing ratio 0.633, one build-up via level on one net (hs_to_ls, 1.435 A). 144 enumerated partitions meet the per-tier area budget and 8 keep both ends the June-2026 source fixes. PROVEN_REALIZABLE is NOT available: the microvia current allowable, the capture-pad diameter, a vendor design rule and two package clearances are OPEN.** | `results/phase0mr3a/LS_TO_L_INTERCONNECT_AUDIT.md` |
| next work | **MANUSCRIPT FREEZE. Phase 0N is NOT authorised and no further technical phase is scientifically necessary: Phase 0M-R3C found no fundamental model contradiction and the deciding ordering survived the entire interconnect correction at +0.04 %. See results/PAPER_FREEZE_DECISION.md, results/PAPER_CLAIM_MATRIX.csv and results/PAPER_FIGURE_TABLE_PLAN.md. FUTURE WORK, none of which blocks submission because none bears on a claimed result: high-stress SAC305 characterisation; N_required; an admissible mechanical allowable and G2; conjugate CFD; the microvia current allowable and a vendor design rule; the two remaining package clearances; cohesive delamination, crack growth and moisture. Items already COMPLETE and not to be relisted: adopting the physical cooling model into the ETM loop (Phase 0M-R), putting the RDL into the production thermal model (Phase 0M-R2), sourcing the interconnect CLASS for ls_to_L (Phase 0M-R3B), and the component repartition (Phase 0M-R3C).** | `results/phase0mr3a/final_open_items.md` |

*Contract version 0M-R.1, 2026-09-21. Every current-facing statement in this report and in the standalone audit report is generated from this table. A statement that contradicts it is a defect, not a difference of emphasis.*

<!-- END GENERATED: current_state_contract -->


**Phase 0M-R3C — Final state, via-technology and TSV-margin closure.** This section supersedes
the corresponding statements of Phase 0H.

### Verdict — PROCESS-CONDITIONAL REPARTITION FOUND; THE FINAL Z1/Z2 RESPONSE ORDERING SURVIVES

*Phase 0G verdict, still standing and refined by this phase:* NO ACTIVE MECHANICAL CONSTRAINT --
RESPONSE COUPLING ONLY.

- THE THREE-LEVEL VIA COUNT WAS WRONG (DEFECT #64). Phase 0M-R3B counted three MATERIAL layers across the 120 um gap. RDL_UM = 10 um is an interlayer REDISTRIBUTION layer -- patterned copper, which is what a microvia lands on. Counting CONDUCTOR PLANES gives ONE via level of 100 um, not three stacked. The stacking-limit objection dissolves and the Phase-0M-R3B finding that zero configurations satisfy both sourced bounds is WITHDRAWN.
- THE BASELINE'S REAL BINDING NET WAS hs_to_cf, not ls_to_L. In the Phase-0M-R3 tier order it crosses the whole 606 um low-side GaN tier in one via level, an aspect ratio of 5.05 at the sourced pitch.
- A REPARTITION FIXES BOTH. T1C_REORDERED swaps gan_ls and cap_fly only. ls_to_L becomes an adjacent-tier RDL transition (10 um, AR 0.083) and hs_to_cf becomes adjacent too; the only remaining build-up via is hs_to_ls at 100 um and 1.435 A, AR 0.833. It is a PERMUTATION: same components, same per-tier areas, same 1921 um stack, and it keeps both ends the June-2026 source fixes.
- FRAMEWORK PROVISIONING IS NOT A PROCESS QUALIFICATION, and the two are reported separately everywhere. n_required is a conservative design-side allocation at J_design = 1e8 A/m2; no sourced current allowable exists for this microvia technology.
- TWO PRIMARY SOURCES WERE OBTAINED IN FULL TEXT. The EPC2057 datasheet shows four solder bars on a 1500 x 1200 um die, so the switch-node landing area is at most a quarter of the die. The ls_to_L edge is an AGGREGATE over K = 3 phases: per device the switch node carries 6.803 A, inside the part's 9.6 A continuous rating.
- ONE FINAL ETM REPLAY WAS RUN on a pair frozen before solving, with the corrected physical spans enabled. D_driver_final = 1.1947 against the historical 1.1943, a change of +0.03 %. The ordering survives the entire interconnect correction.
- THE TEMPERATURE/RESPONSE DECOUPLING SURVIVES TOO. ARCH_Z2 runs 126.46 C against ARCH_Z1's 118.32 C and still carries 16.3 % less local fatigue-relevant inelastic response.

**What this is not.** This is NOT a finding that the mechanics is wrong or irrelevant. The
response model is converged, cross-validated and sign-stable, and since Phase 0I it yields a
LOCAL FATIGUE-RELEVANT INELASTIC RESPONSE METRIC rather than load alone. That metric is a
RESPONSE, not damage: it becomes damage only through a sourced damage law, life only through a
life model, and a criterion only with an admissible allowable, and none of those three is
closed. It is a finding that no admissible mechanical inequality exists to turn that response
into a constraint, and that several first-order physical models exist as validated screening
tools without yet driving the production path.

**Falsification gate G2: NOT_TESTED.** NOT TESTED since Phase 0B, and the reason has narrowed
twice. Phase 0H could test nothing because it had neither a failure-relevant metric nor an
allowable. Phase 0I supplied the metric -- convergent, verified in 0I-R, tied to a documented
mechanism -- so g_mech(x) <= g_allow is writable in FORM. Phase 0J-R then obtained the primary
life-law sources and reproduced Syed 2004's author-corrected calibration, so ACCESS is no longer
the blocker. What remains is g_allow itself, blocked for TWO independent reasons, either
sufficient: no required life exists anywhere in this repository or in any supplied source, and
absolute N_f is unvalidated because the constitutive model that feeds it is fitted on
Sn3.9Ag0.6Cu far below the stresses the package reaches. Phase 0K withdrew the framing that
N_required was the sole blocker.

#### Verdicts considered and rejected

| candidate verdict | why rejected |
|---|---|
| Source-Compatible Repartition Found; Final Z1/Z2 Etm Ordering Survives | rejected. "Source-compatible" would claim the process rules are closed. Four are OPEN: microvia current allowable, capture-pad diameter, vendor design rule, and two package clearances. |
| Repartition Found; Z1/Z2 Response Ordering Changes | rejected and measured. The ordering does not change: D_driver moves by +0.04 %. |
| No Realizable Repartition Exists In The Current Component Library | rejected and contradicted. 144 enumerated partitions satisfy the per-tier area budget, 8 of them keep both sourced stack ends, and the best has a worst aspect ratio of 0.83. |
| Geometry Closes But Process Data Remain Insufficient; Architecture Claim Stays Conditional | rejected as incomplete. It is true, and it omits the result the gate was opened to obtain: the replay ran and the ordering held. Option B states both. |

#### Optimizer gate

| condition | met | detail |
|---|---|---|
| 1 — assembly-state response survives calibrated board and thermal-boundary uncertainty | **PARTIAL** | The thickness RESPONSE survives calibrated board and thermal-boundary uncertainty with 0 sign flips in 20 combinations. But the assembly-state REVERSAL the condition was posed about does not survive -- it does not exist. |
| 2 — a criterion or user-set ε can actually alter the feasible design set | **FALSE** | No criterion exists, so nothing can alter the feasible set. Phase 0G additionally argued the computed range sits far below conventional tolerances; Phase 0H Sec.18 RETRACTED that comparison as unsourced, which strengthens rather than weakens the conclusion -- whether the range is safe or constraining is UNKNOWN. |

**BOTH conditions were required. Condition 2 fails outright and condition 1 fails in the sense
it was posed. The global ETM optimizer is NOT recommended and was NOT built.**

### Claims by status

Status vocabulary: **PROVEN** — numerically converged *and* cross-checked against an independent solver. **SUPPORTED** — converged in one solver, no independent cross-check. **CONDITIONAL** — true only under a named open input. **SUPERSEDED** — asserted in an earlier phase and no longer current.

#### PROVEN (12)

- **geometry_realizability** (Phase 0F) — A DVPD converter's component stack sets a hard lower bound on substrate thickness, and that bound excluded both thicknesses swept in Phases 0B-0E.
    - *Evidence:* `results/phase0f/GEOMETRY_REALIZABILITY_AUDIT.md`
- **rail_dependence** (Phase 0D-R) — The rail carried by a vertical interconnect changes its loss by ~1960x for fixed transferred power, and which rail it carries is architecture-specific.
    - *Evidence:* `results/phase0dr/POWER_PATH_AUDIT.md`
- **allocation_policy** (Phase 0E) — A via field's loss is proportional to current only under minimum-capability provisioning; under geometric allocation the same field obeys P ~ I^2.
    - *Evidence:* `results/phase0e/tsv_allocation_sensitivity.csv`
- **no_ac_correction** (Phase 0E) — No AC correction to the vertical interconnect is required at the switching frequency; HFSS shows loop resistance flat to 0.18 % below the 19.1 MHz skin crossover.
    - *Evidence:* `results/phase0e/em_validation.md`
- **thermal_ordering** (Phase 0E,0F) — An independent 3-D thermal solver reproduces candidate ordering exactly at both 240 W and 1 kW.
    - *Evidence:* `results/phase0e/thermal_validation.md, results/phase0f/thermal_moose_1kw.csv`
- **unit_consistency_defect** (Phase 0G) — Vertical-tier losses were evaluated per regulator and summed with a system-wide lateral loss, understating every vertical tier by n_vr -- 4x at 240 W and 49x at the 1 kW reference.
    - *Quantitative:* P_TSV / P_TSV,corrected = 49.004 to 49.055 at all nine thicknesses; independent hand check 89.7768 mW/VR x 49 = 4.399 W agrees
    - *Evidence:* `results/phase0g/electrical_crossover_uncertainty.md, DEFECT #30`
- **bcb_is_a_clamp** (Phase 0G) — The compact BC-B foundation restrains all three DOF on the underside plane, so it models a clamp and not a board. It never recovers its own free limit: at vanishing stiffness it gives 0.739 um where the free package on the identical mesh gives 8.287 um.
    - *Quantitative:* S_h > 0 at all 12 stiffnesses over 7 decades -- no crossover k* exists
    - *Evidence:* `results/phase0g/support_stiffness_sweep.csv, results/phase0g/board_foundation_calibration.md`
- **thickness_ordering_universal** (Phase 0G) — Thicker substrate reduces warpage in the free package and in every explicitly constructed assembly, across the whole board envelope from compliant to metal-backed, at every stress-free reference temperature and under every thermal boundary tested.
    - *Quantitative:* S_h = -0.039 to -0.886 in 5 board cases; sign stable across 3 reference temperatures and 4 thermal boundaries; 0 sign flips in 20 combinations
    - *Evidence:* `results/phase0g/explicit_board_crosscheck.csv, results/phase0g/footprint_m1_1kw.csv, results/phase0g/cooling_topology_comparison.csv`
- **gan_height_sourced** (Phase 0H) — The GaN device heights are no longer open. Manufacturer datasheets give 685 um nominal (815 max) for the high-side EPC2212 and 606 um for the low-side EPC2090, against the 0/100/250 um envelope Phases 0F-0G invented.
    - *Quantitative:* for the EMBEDDED architecture this raises h_sub,min from 0.770 mm to 1.176-1.426 mm
    - *Evidence:* `results/phase0h/geometry_height_closure.md`
- **architecture_dependent_realizability** (Phase 0I) — COMPONENT-HEIGHT REALIZABILITY IS ARCHITECTURE DEPENDENT. Component height constrains substrate thickness ONLY for the embedded architecture. Where the converter is below, above or beside the substrate, nothing it contains constrains h_sub, and the binding constraint becomes TSV manufacturability.
    - *Quantitative:* h_sub,min = 1.276 mm embedded (MLCC nominal) against 0.300 mm for backside, power-die and 2.5D -- the source-demonstrated TSV layer thickness (June-2026 Table III, d = 30 um at h = 300 um, AR 10:1). A 4.3x wider realizable range.
    - *Evidence:* `results/phase0i/REALIZABILITY_BY_Z_ARCHITECTURE.md, DEFECT #33`
- **warpage_is_not_a_reliability_proxy** (Phase 0H) — Global die warpage does not predict the local interconnect loading for this architecture, and the relationship is not even sign-stable across assembly states.
    - *Quantitative:* 70 paired runs: Spearman rho = 0.112 (all cases), 0.349 (mounted), -0.793 (free) against interface shear. Across the mounted thickness sweep warpage varies 3.0x (9.66 -> 29.23 um) while shear stays within +-9 %.
    - *Evidence:* `results/phase0h/warpage_local_correlation.csv, results/phase0h/local_metric_selection.md`
- **defect30_changed_a_240w_ranking** (Phase 0H) — DEFECT #30 inverted an architecture comparison at 240 W as well as at 1 kW. Replaying the eleven Phase-0E candidates with the scope-guarded evaluator moves three ranking positions.
    - *Quantitative:* ARCH_B distributed j=2.0 h=0.5 shifts +356.83 mW (+1.576 %) and falls from third-best to worst of the five distributed cases; ARCH_A cases shift 16-25 mW because their vias carry only leakage-scale current
    - *Evidence:* `results/phase0h/DEFECT30_GLOBAL_PROPAGATION_AUDIT.md`

#### SUPPORTED (3)

- **footprint_agreement_mounted** (Phase 0G) — In a mounted assembly the electrical and mechanical preferences on the footprint lever AGREE: the larger, finer-partitioned footprint is both lower loss and lower warpage.
    - *Quantitative:* electrical -6.633 W for M = 36 -> 49 (259.2 -> 329.3 mm2); mechanical S_A = -0.166 to -0.290 in all 5 board cases
    - *Independent corroboration:* June-2026 Sec. I asserts the same direction qualitatively -- distributed VRs produce localized deformation rather than global package deflection, reducing overall warpage sensitivity. Direction only; no number is given.
    - *Evidence:* `results/phase0g/footprint_board_envelope.csv, results/phase0g/footprint_placement_recheck.md`
- **count_inert** (Phase 0B,0C) — Regulator count is mechanically inert at constant total footprint and heat.
    - *Evidence:* `results/phase0b, results/phase0c`
- **rdl_dominates_arch_conditional** (Phase 0H) — Package distribution loss is dominated by lateral RDL spreading for ARCH_A at every realizable thickness, but NOT for ARCH_B, whose via field exceeds the RDL by up to 11x above roughly 0.9 mm.
    - *Quantitative:* ARCH_A: RDL 0.642 W against TSV 0.010-0.163 W. ARCH_B: TSV 0.450 W at 0.80 mm rising to 7.210 W at 2.00 mm against a flat 0.642 W RDL.
    - *Evidence:* `results/phase0h/interconnect_decomposition_1kw.csv`

#### CONDITIONAL (3)

- **archA_interior_optimum** (Phase 0G) — ARCH_A retains a numerically resolved interior electrical optimum at h_sub = 0.90 mm.
    - *Condition:* resolved but NOT actionable -- the optimum is 8.634 mW deep on a 125 W budget (0.0069 %). The ARCH_A/ARCH_B gap at fixed thickness is 52x larger than the entire depth of this optimum.
    - *Quantitative:* numerical floor 0.0977 mW; depth vs 0.80 mm = 88.4x floor, vs 1.00 mm = 9.6x floor
    - *Evidence:* `results/phase0g/crossover_hires_ARCH_A_fixedA.csv`
- **thickness_opposition** (Phase 0G) — Substrate thickness is a genuine ETM opposition: electrically thinner is better, mechanically thicker is better.
    - *Condition:* the opposition is real and sign-stable, but NO criterion exists to make it binding (G2 NOT TESTED), so it cannot restrict a feasible set. It is a response coupling, not a constraint.
    - *Quantitative:* electrical +6.706 W for 0.80 -> 2.00 mm (ARCH_B nominal); mechanical -44 % warpage over the same range (FR-4 1.6 mm board)
    - *Evidence:* `results/phase0g/electrical_crossover_uncertainty.md, results/phase0g/explicit_board_crosscheck.csv`
- **mounted_warpage_floor** (Phase 0G) — A mounted assembly cannot reach the warpage levels the free package suggests: its floor is 14.03 um where the free package reaches 1.27 um.
    - *Condition:* magnitudes are NOT validated -- board CTE, board modulus envelope and the absence of a solder-mask/copper-plane laminate structure are engineering values, not measurements of the reference system.
    - *Evidence:* `results/phase0g/mechanical_epsilon_corrected.csv`

#### SUPERSEDED (9)

| claim | asserted in | superseded by |
|---|---|---|
| **footprint_opposition** — HVR footprint is simultaneously an electrical and a mechanical design variable and the two OPPOSE: larger footprint lowers electrical loss and raises warpage. Sign preserved in both assembly states. | 0C,0D,0D-R,0E,0F | Phase 0G: the sign is ASSEMBLY-STATE DEPENDENT. It is positive in the free package (+0.203) and the compact clamp (+0.058) and NEGATIVE in all five explicit assemblies (-0.166 to -0.290). In a mounted assembly the two disciplines AGREE. The reference paper asserts the mounted direction. Replaced by claim footprint_agreement_mounted. |
| **assembly_state_reversal** — The mechanical thickness preference REVERSES between assembly states: free packages prefer thicker substrates, mounted packages prefer thinner ones. | 0F | Phase 0G: an artifact of BC-B's three-DOF in-plane clamp. No explicit assembly reproduces it -- S_h < 0 in all five board cases, at three reference temperatures and four thermal boundaries. BC-B cannot recover its own free limit (0.739 vs 8.287 um) and no support stiffness k* exists over seven decades. |
| **archB_interior_optimum** — ARCH_B has an interior electrical thickness optimum near h_sub = 1.0 mm. | 0F | Phase 0G: an artifact of DEFECT #30. The minimum SURVIVED a 25x tighter convergence tolerance -- it was not numerical -- but vanished when the vertical-tier unit error was fixed. Corrected ARCH_B is monotonically increasing with the optimum on the thin boundary in 9 corners of 9. |
| **win_win_win_200_500** — Substrate thickness 200 -> 500 um is win/win/win and survived every correction. | 0B,0C,0D,0D-R,0E | Phase 0F: both thicknesses are GEOMETRICALLY INFEASIBLE for the selected converter. The trend DIRECTION survives on realizable geometry (800 -> 1500 um, -81.9 % warpage) but the magnitudes and the swept range do not. |
| **no_arch_dependent_thickness** — No architecture-dependent thickness tradeoff exists. | 0D-R,0E | Phase 0F: at 1 kW ARCH_B's electrical optimum is interior while its mechanical preference is monotone. Phase 0G audits whether that interior optimum is numerically resolved. |
| **archB_infeasible** — ARCH_B is infeasible. | 0D-R | Phase 0E: feasible under every source-backed current density; the verdict rested on an unsourced 4.8 mA per-via limit. |
| **placement_spread_188** — The electrical spread across placements is 188.8 %. | 0D-R | Phase 0E: 46.7 % on the sourced RDL stack. |
| **exchange_rate_16** — The footprint ETM exchange rate is 16.2 W/um. | 0D-R | Phase 0E: 11.48 W/um; Phase 0F at 1 kW: 12.86 W/um. |
| **ansys_unavailable** — ANSYS cross-validation is impossible because the licence server is down. | 0B,0C,0D,0D-R,0E | Licence restored 2026-09-06. HFSS and Icepak used; Q3D is not licensed. |

### Open items

- **gan_mlcc_layer_heights** — GaN device and MLCC layer heights
    - *Why it matters:* sets the HVR cell height and hence the minimum realizable substrate
- **em_lifetime_limit** — electromigration lifetime current density for copper TSVs
    - *Why it matters:* the provisioning density is closed; the reliability limit is not
- **rdl_dielectric_and_stitching** — RDL dielectric stack and inter-layer stitching via density
- **board_laminate_structure** — real board laminate structure -- copper plane fractions, solder mask, stiffener, and the board's true in-plane CTE
    - *Why it matters:* Phase 0G CLOSED the question the Phase-0F reversal rested on: BC-B is a clamp, no k* exists, and every explicit board gives the free-package sign. What remains open is only MAGNITUDE. The 9.7-29.2 um range is an engineering envelope, not a prediction, and must not be quoted as predicted warpage.
    - *Change in this phase:* was board_foundation_stiffness (OPEN, Phase 0F) -- the SIGN question is now closed; only magnitude remains
- **cooling_topology** — whether the real package is cooled from the top or from inside the substrate
    - *Why it matters:* sets the sign of the through-thickness thermal gradient
    - *Change in this phase:* BOUNDED in Phase 0G rather than closed. It moves warpage magnitudes by up to 45 % and halves S_h, but flips no sign in any configuration tested. The mounted normalized response is invariant to 0.07 % across a 4x h_top band. Substrate-side-only cooling is separately thermally infeasible at 1 kW.
- **assembly_pre_stress** — assembly / cure / cooldown reference state (M1)
    - *Why it matters:* all warpage here is INCREMENTAL OPERATIONAL, not TOTAL ASSEMBLED
    - *Change in this phase:* BOUNDED in Phase 0G. Raising the reference to 150/175 C changes MAGNITUDES by up to +54 % (25.1 -> 38.7 um mounted) but leaves the mounted normalized response stable to 0.5 % (S_h = -0.4421 / -0.4397 / -0.4400) and flips no ordering. Every absolute warpage number in this project is therefore a LOWER BOUND. A validated pre-stress model still requires the cure schedule, cure shrinkage, viscoelastic relaxation and reflow profile -- none available for the reference system.
- **mechanical_criterion** — an admissible operational-state warpage or RDL-shear allowable for this stack
    - *Why it matters:* this is ONE OF THREE INDEPENDENT blockers for G2 -- the other two being an OPEN N_required and an unvalidated absolute N_f -- and it independently blocks any constraint-based optimizer. Phase 0G searched the full corpus and found none: June-2026 names the failure mechanisms (global package warpage, delamination, RDL shear) but attaches no number to any of them. External standards are unretrievable in this environment AND inadmissible on inspection -- package-outline coplanarity governs the ball plane of a component as supplied at a defined measurement temperature for solderability at reflow, which matches neither the package state, the temperature, the measurement definition nor the failure mechanism analysed here.
    - *Evidence:* `results/phase0g/mechanical_criterion_audit.md`

### Not tested

- **G2** — feasible-set reversal under a mechanical criterion
    - *Why:* no source-backed criterion matching this package state, temperature, size, measurement definition and failure mechanism could be found
    - *Consequence:* the epsilon sweep is PARAMETRIC CONSTRAINT SENSITIVITY, never feasibility
- **transient** — transient electrothermal and mechanical response
- **m1_full** — full assembly-pre-stress model with plasticity and lifetime

### Defects logged in this phase

#### DEFECT #29 — DUPLICATED CURRENT CLAIMS CAN BECOME SEMANTICALLY STALE

The report stated the same claim in Executive Summary, Positive Results, Negative Results, the
uncertainty ladder and Next Steps; each phase updated only some. Every individual sentence was
true when written, so regex assertions could not catch the contradiction.

- *Fix:* This file is the single source of truth. Current-status sections are GENERATED from it and semantic tests compare the generated text against it.
- *Status:* **FIXED**

#### DEFECT #30 — UNIT INCONSISTENCY BETWEEN PER-REGULATOR AND SYSTEM-WIDE LOSS TERMS

vertical_tier() returns a PER-REGULATOR loss; rdl_network_solve() returns a SYSTEM-WIDE loss.
Phases 0D-R, 0E and 0F summed them directly, understating every vertical tier by n_vr -- 4x at
240 W, 49x at 1 kW.

- *Detected by:* Phase 0G Sec. 2 curve decomposition, after the convergence-tolerance hypothesis had been tested and eliminated
- *Impact:* INVERTED the Phase-0F architecture conclusion. ARCH_B's interior optimum was an artifact; corrected ARCH_B is monotonic with its optimum on the thin boundary.
- *Fix:* scripts/phase0e/architecture0e.py -- both terms expressed system-wide; guard test added; 151 tests pass.
- *Status:* **FIXED**

#### DEFECT #31 — THE SEMANTIC LEDGER WAS VACUOUS -- IT COULD NOT FAIL

The Phase-0F semantic ledger scored each withdrawn claim against a +-800-character window and
accepted 'was ', 'were ', 'became', 'becomes' and 'earlier' as exonerating context. In English
technical prose at least one of those appears in any such window, so EVERY ledger entry passed
unconditionally. The mechanism built to catch DEFECT #29 could not catch anything.

- *Detected by:* a deliberate NEGATIVE TEST -- three unqualified re-assertions of withdrawn claims were injected into the report and the ledger stayed green. The guards had never been checked for the ability to fail.
- *Impact:* Five genuinely stale statements were standing in the Executive Summary, the uncertainty ladder and Next Steps, all of them invisible to a green build.
- *Fix:* The exonerating vocabulary is restricted to markers that can only be present deliberately; the window is the containing PARAGRAPH or table cell instead of a page of prose; scoring runs on the Markdown so headings are unambiguous; and a claim is exonerated by its enclosing heading CHAIN, so a subsection inside a superseded phase inherits that framing. Verified in BOTH directions: the real report passes 49 checks, and five injected re-assertions are each caught.
- *Status:* **FIXED**
- *Lesson:* A guard that has never been observed to fail has not been tested. Every assertion added from Phase 0G onward is negative-tested before it is trusted.

#### DEFECT #32 — CURRENT_SCIENTIFIC_STATUS DID NOT CONTROL ALL CURRENT-FACING REPORT CONTENT

Phase 0G brought the CLAIMS LEDGER under this file and generated it, then declared DEFECT #29
fixed. But the Executive Summary, governing equations, validation status, novelty statement,
current limitations, publication-defensible claims and next steps were still hand-written, and
the Phase-0G ledger deliberately exonerates any withdrawn claim whose enclosing heading names a
historical phase -- which is right for narrative sections and wrong for sections that speak in
the present tense. Seven current-facing statements were therefore stale behind a green build:
thickness still called win/win/win and 'survived every correction'; 'no architecture-dependent
thickness tradeoff exists'; the withdrawn ARCH_B interior optimum; footprint still advertised as
the ETM opposition novelty; R_field = R_single / n_req with n_alloc absent from the symbol
table; the full 3-D MOOSE package validation still called NOT DONE when Phase 0E completed it as
TH-1..TH-5; and BC-B still described as a compliant mounted support after Phase 0G proved it a
three-DOF clamp.

- *Fix:* All seven are now GENERATED from this file into sentinel-delimited blocks, the report is checked to carry each block verbatim, and a CURRENT-FACING SECTION AUDIT forbids nine stale-claim signatures inside present-tense sections with per-pattern exonerations for ledger rows, negations and retractions. Verified in both directions: the clean report passes, and nine injected stale claims are each caught.
- *Status:* **FIXED**

#### DEFECT #33 — REALIZABILITY WAS ARCHITECTURE-BLIND

kw1.design_1kw() takes no architecture argument, so the EMBEDDED geometric rule t_cell + h_tsv
<= h_sub was applied to every architecture -- including ARCH_B, which converts BELOW the
substrate, and ARCH_C, which converts BESIDE the die. At h_sub = 0.30 mm the code answers 'no
inductor fits h_sub=300 um (budget 30 um)' identically for all three. The electrical model has
varied the converter's vertical position since Phase 0D-R; the geometric and mechanical models
never did.

- *Detected by:* Phase 0I Sec.2, on treating z-placement as an architecture variable
- *Impact:* Every 'unbuildable' verdict Phase 0H issued against a thin substrate is EMBEDDED-SPECIFIC. Non-embedded architectures reach 0.300 mm against the embedded 1.276 mm -- a 4.3x wider range including exactly the region the corrected electrical model prefers.
- *Fix:* scripts/phase0i/zarch.py -- realizable(arch, h_sub) applies the embedded stack rule only where the converter is embedded, and the source-demonstrated TSV-layer rule (June-2026 Table III, d = 30 um at h = 300 um, AR 10:1) elsewhere.
- *Status:* **FIXED**
- *Lesson:* A coupling is only modelled if EVERY domain sees it. The electrical model carried z-placement for five phases while geometry and mechanics silently did not, and no test could catch it because each domain was self-consistent on its own terms.

#### DEFECT #34 — PHASE-0G AND 0H FIGURES WERE NEVER EMBEDDED IN THE PDF

pandoc is invoked with cwd = results/, so a figure path written relative to the REPO ROOT
('results/phase0g/FIG.png') resolves to results/results/... . pandoc emitted 'Could not fetch
resource ... replacing image with description' for all 21 such references and substituted the
alt text. Every Phase-0G and Phase-0H figure was missing from the PDF, and the Phase-0I figures
would have been too.

- *Detected by:* Phase 0I, when a LaTeX error surfaced the pandoc warning stream that had been carrying these messages unread since Phase 0G
- *Impact:* Two full phases of figures absent from the delivered PDF while the build reported VERIFIED. No numerical result is affected; the deliverable was.
- *Fix:* Figure references are absolute, matching the convention every phase before 0G used. Two new checks: paths are resolved FROM PANDOC'S WORKING DIRECTORY, and the pandoc warning stream is scanned for 'Could not fetch resource'. Negative-tested: reverting one path to repo-relative fails both.
- *Status:* **FIXED**
- *Lesson:* A build warning nobody reads is not a warning. The verification suite now consumes the toolchain's own warning stream instead of only inspecting its output.

#### DEFECT #35 — PHASE-0I SCIENCE NOT FULLY PROPAGATED INTO CURRENT-FACING REPORT SECTIONS

Phase 0I added reliability physics but left seven current-facing statements in the Phase-0H
state. The Executive Summary still framed the answer as 'Phases 0G and 0H find'; the limitations
still said 'Neither local metric is fit for decisions', which referred to the two REJECTED
Phase-0H proxies and not to the new M2 metric that passes every convergence test; they still
said 'GaN and MLCC layer heights are still open' when GaN is source-backed; 'Exact next work'
still recommended publication reframing; the validation status still described the mechanics as
'M0 -- no plasticity, creep or fatigue' when a temperature-dependent elastic/plastic/creep
submodel now exists; the governing equations stopped at M0 thermoelasticity with no M2
constitutive law, damage-metric definition or stabilised-cycle definition; and the method still
counted eight gates.

- *Detected by:* Phase 0I-R Sec.18, a dedicated re-read of the current-facing sections against the Phase-0I evidence
- *Impact:* The report understated its own capability -- it described a model without failure physics after failure physics had been added -- and pointed the reader at the wrong next step.
- *Fix:* All eight items (A-H) repaired at the single source of truth and regenerated. The validation block now splits GLOBAL M0 from LOCAL M2 explicitly, and four M2 governing equations were added: the constitutive law, the damage-metric definition, the stabilised-cycle definition, and an explicit no_life_equation entry recording that no lifetime equation is current. Two further items were found while verifying A-H and are also fixed: the current-facing guard scope excluded the LIVE phase narrative even though it is headed 'current authoritative', so three over-claims inside it had never been checked; and the report build was not idempotent, because the new reliability_metric fragment was anchored on a heading that a later splice consumes.
- *Status:* **FIXED**
- *Lesson:* A phase that ADDS capability must audit the current-facing text as carefully as a phase that withdraws a claim. DEFECT #29, #32 and #35 are the same failure in three directions: stale withdrawal, stale scope, and now stale capability.

#### DEFECT #36 — SIX NEW GUARDS WERE NEGATIVE-TESTED AGAINST PARAPHRASES, NOT THE REAL SENTENCES

Sec.20 requires every new semantic guard to be shown FAILING on an injected violation before it
is trusted. All six Phase-0I-R guards passed that test. The test was invalid. The injected
sentences were written by the same author, in the same sitting, as the regexes -- so each
injection was phrased to match its own pattern. Checked afterwards against the sentences that
had ACTUALLY appeared in the report, ALL SIX guards missed: the real text said 'Z5 is
eliminated' where the guard looked only for the literal string '2.5D'; 'A 0.300 mm substrate is
realizable' where the guard looked for 'manufacturable'; 'Z1 keeps a 30 mW edge' where the guard
looked for 'electrically better'; 'the relative-life ratio is parameter-free' where the guard
required the unhyphenated 'relative life'; and 'of eight failure mechanisms only ONE is
computable' where the guard required the reversed word order 'only one of eight failure
mechanisms'.

- *Detected by:* Phase 0I-R Sec.20 follow-up, by testing each pattern against text quoted from the report itself rather than against text written for the test
- *Impact:* Six guards reporting PASS while blind to their own subject matter, and one real consequence: the stale Executive Summary sentence 'of eight failure mechanisms only ONE is computable' sat in a current-facing section, in guard scope, and was not flagged. It was found by manual re-reading, which is exactly what the guard existed to replace.
- *Fix:* Patterns rewritten against the verbatim historical sentences. A PERMANENT self-test replaces the one-off injection: GUARD_SELFTEST pairs every one of the fifteen current-facing guards with the exact sentence it exists to reject, and the build fails if any pattern misses its sentence OR if an exoneration context clears it. A coverage check makes it impossible to add a guard without a self-test sentence. The eight pre-0I-R guards were retro-fitted with the same self-test.
- *Status:* **FIXED**
- *Lesson:* A negative test written by the author of the guard, at the same time as the guard, tests the author's model of the failure and not the failure. The injection must be the REAL text -- recovered from the artifact or its history -- and it must be asserted permanently in the suite, not performed once by hand. DEFECT #31 said a check never seen to fail has not been tested; #36 adds that a check seen to fail on a straw man has still not been tested.

#### DEFECT #37 — OLD LOCAL-PROXY RESULT SURVIVED AFTER THE M2 METRIC REPLACED IT

The Executive Summary stated, as a CURRENT result, that 'the opposition is resolved ONLY in
global warpage: in the one local metric available the thickness effect is 1.96 %, which is 7x
below that metric's own uncertainty.' Both halves belonged to Phase 0H. The '1.96 %' is the
thickness effect in the SMEARED INTERFACE SHEAR proxy, and the '7x below its own uncertainty' is
that proxy's 14.14 % floor. Phase 0H REJECTED that proxy as non-monotone under refinement, and
Phase 0I replaced it with a convergent M2 solder metric -- but the sentence describing the
rejected proxy stayed in the current-facing text and kept asserting that no local metric
resolves the thickness effect.

- *Detected by:* Phase 0J Sec.38, a directed re-read of the Executive Summary against the Phase-0I-R state
- *Impact:* The report asserted, as current, that the thickness opposition is invisible locally. Phase 0J measures it directly at all eleven z-sweep points and finds it monotone in every architecture: -5.6 % (Z1), -6.1 % (Z2), -17.2 % (Z4) in accumulated inelastic path. The trend is real, preserved, and simply 3-5x smaller than global warpage makes it look.
- *Fix:* Replaced at the single source of truth with the measured M1 values and the explicit statement that the 1.96 % figure is withdrawn as a current result and retained only in the Phase-0H historical section, which Sec.38 forbids editing.
- *Status:* **FIXED**
- *Lesson:* A phase that REPLACES a metric must retire the replaced metric's CONCLUSIONS, not only its numbers. DEFECT #29, #32, #35 and now #37 are four faces of one failure: stale withdrawal, stale scope, stale capability, and stale superseded-instrument.

#### DEFECT #38 — PHASE-0J-R LIFE-LAW STATUS NOT FULLY PROPAGATED INTO CURRENT-FACING REPORT TEXT

Nine current-facing statements still described a project that could not predict life, three
phases after it could: 'No lifetime is predicted anywhere'; 'the EXPONENT m does NOT cancel, and
no m is sourced'; 'Over m = 0.5 to 5 the Z2/Z1 ratio spans 1.25 to 9.18'; 'solder fatigue ...
has no life law and so yields no pass/fail'. All were in the Executive Summary and all were
generated from the single source of truth.

- *Detected by:* Phase 0K Sec.1
- *Impact:* The report understated its own capability -- no life law after four had been admitted, no sourced exponent after two primary sources had bounded it at -1 and -1.3.
- *Fix:* Repaired at the source of truth and regenerated, separating the four things that must not be conflated: RELATIVE LIFE validated at 1.21-1.38x, CONDITIONAL ABSOLUTE LIFE not validated at a 4.1x spread, REQUIRED LIFE open, G2 not tested. Six guards added, each self-tested on the VERBATIM standing sentence and each negative-tested to failure.
- *Status:* **FIXED**
- *Lesson:* A phase that converts a negative result into a positive one must retire the negative's language as carefully as a phase that withdraws a claim retires the claim. Understating your own model never trips a scepticism check.

#### DEFECT #39 — PHASE-0K NARRATIVE CURRENT, BUT GENERATED STATUS AND NEXT-WORK FRAGMENTS PRE-0K

The Executive Summary's 'Exact next work' still read 'PHASE 0K -- SYSTEM-OWNER MISSION
DEFINITION' and still asserted 'the remaining blocker is ... a REQUIRED LIFE' -- the exact claim
Phase 0K withdrew. Worse than one stale sentence: NO Phase-0K result appeared in current-facing
text at all. The 474/3206 decision regions, the two-blocker finding, the G2 decision map and the
experiment design each occurred ZERO times.

- *Detected by:* Phase 0K-R Sec.1
- *Impact:* The report recommended as next work a phase that had already run, and named one blocker where its own analysis had established two.
- *Fix:* next_work rewritten from the source of truth. Sec.2 typed contract added (relative_life_0kr, absolute_life_0kr, mission_0kr, g2_0kr, experiment_0kr, next_step_0kr) so current status is GENERATED rather than remembered. Four guards with verbatim self-tests, all negative-tested. Sec.34 post-build audit added: the FINAL Markdown and the text extracted from the FINAL PDF are re-read AFTER generation -- 8 current-facing headings, 15 stale patterns, 0 hits.
- *Status:* **FIXED**
- *Lesson:* DEFECTS #29, #32, #35, #37, #38 and #39 are six instances of ONE failure: the narrative advances and the generated status does not. The structural fix is not another guard but a typed contract plus the rule that the BUILT ARTIFACT is what gets audited -- all three most recent report defects occurred at or after the generation step, not in the source.

#### DEFECT #40 — CREEP CALIBRATION VARIABLE DOES NOT MATCH THE SOLVER'S DRIVING VARIABLE

fit_norton_data (solder_model.py:84-96) regresses log(rate) on log(sigma_APPLIED) -- the total
uniaxial stress of a constant-load creep test, with no yield subtraction. CalculiX integrates
eps_dot = A*(sigma_vm - sigma_y(eps_in))^n and gives IDENTICALLY ZERO inelastic strain when
sigma_vm <= sigma_y (incplas.f:310-311, 599-605). These are different independent variables.

- *Detected by:* Phase 0L Parts III-V: CalculiX 2.23 source trace, then 7603 single-element solver increments against three candidate laws.
- *Impact:* The overstress is NEGATIVE at 16 of the 19 calibration points, so in the solver's own variable the calibration experiment lies entirely inside the elastic domain. Solver probe TEST F: the card reproduces 0 of 19 of its own source points; 16 give exactly 0.0 and the other three are low by 4.7e7x, 1.8e12x and 2.4e5x. The quoted 8.3 % rms fit residual measures a curve in a variable the solver never evaluates.
- *Fix:* NOT repaired silently. Part VI shows the consistent refit FIT-B is NOT CONSTRUCTIBLE (0 usable points at 45 and 80 C, 1 at 115, 2 at 150). The only consistent route is sigma_y -> 0, which is what the CalculiX manual itself prescribes for creep below yield, and is carried as model M1 in the Part XI replay.
- *Status:* **CONFIRMED**
- *Lesson:* A fit residual is only evidence if the residual is computed in the variable the consumer uses. The check that caught this -- feed the calibration points back through the solver and see if it returns them -- costs one afternoon and was never run in eleven phases.

#### DEFECT #41 — THE CREEP DATA IS Sn3.9Ag0.6Cu, AND ALL THREE YUAN TABLE CITATIONS ARE WRONG

solder_model.py cites Yuan 2023 'Table 26' for the 19 creep points, 'Table 27' for the Garofalo
constants and 'Table 31' for the Chaboche constants. The paper was retrieved in full
(PMC10381129). It has ELEVEN tables. The correct sources are Table 5, Table 6 and Table 10; the
VALUES all match, only the table numbers are wrong. Yuan section 4.1 states the creep dataset
'is drawn from Xiao and Armstrong [10]', whose title is 'Tensile creep and microstructural
characterization of bulk Sn3.9Ag0.6Cu lead-free solder'.

- *Detected by:* Phase 0L Part V, by fetching the cited paper instead of the citation.
- *Impact:* The creep half of the SAC305 card is calibrated on Sn3.9Ag0.6Cu -- 3.9 wt% Ag against SAC305's 3.0 wt%. The yield half traces to Motalab SAC305 data through an Anand fit and then synthetic curves, so the two halves of one card are different alloys, and the overstress law subtracts one from the other. The brief forbids transplanting high-Ag SAC sets without transferability evidence; Part VII searched 344 works and found none.
- *Fix:* Citations corrected in solder_model.py (values unchanged, so no result moves). The alloy mismatch is NOT repairable from available data and is carried as a standing condition on every creep-derived result.
- *Status:* **CONFIRMED**
- *Lesson:* A citation that names a table number is checkable in minutes and was carried for eleven phases, into the report and into the Phase-0K-R domain audit, unchecked.

#### DEFECT #42 — *CREEP TEMPERATURE GRID: LINEAR-IN-A INTERPOLATION AND CLAMPING ABOVE 125 C

creeps.f:300-330 and materialdata_me.f:413-429 interpolate A, n and m LINEARLY between card rows
and CLAMP outside them. norton_at() builds the rows on an Arrhenius basis, so solver and intent
agree only AT the rows. Production decks (run_zcompare.py:36, run_convergence.py:27) write rows
at -40/0/25/50/75/100/125 C.

- *Detected by:* Phase 0L Part IV TEST G (measured 0.9996-0.9999 against linear-in-A, and 1.33x / 2.80x / 20.0x against Arrhenius) plus card_grid_audit.py.
- *Impact:* Between rows over 45-150 C the solver's rate is 0.83x to 3.88x the intended value; worst on the grid is 8.94x. Above the 125 C top row the card clamps, and because the clamped exponent is wrong too the error is stress-dependent: 0.62x at 20 MPa rising to 8.70x at 100 MPa. The 110->150 C candidate experiment profile runs entirely above the top row.
- *Fix:* Part XI replays every model on a corrected 18-row grid spanning -40..150 C, which cuts the between-row span to 0.81-1.51x and removes the clamping. M0_COARSE is retained in the replay so the grid effect is separable from the constitutive effect.
- *Status:* **CONFIRMED**
- *Lesson:* A material card is an interpolation table, not a function. Whatever the card generator believes about the functional form is discarded at the solver boundary.

#### DEFECT #43 — OMITTING *PLASTIC IS UNDEFINED BEHAVIOUR, NOT A ZERO YIELD SURFACE

The manual says that without a *PLASTIC card 'a zero yield surface without any hardening is
assumed'. In fact materialdata_me.f:331-333 sets plconloc(801)=0.5, incplas.f:130 therefore sets
user_hardening=1, and incplas.f:288 calls uhardening(). The shipped src/uhardening.f is an empty
stub that never assigns fiso, which incplas.f never initialises.

- *Detected by:* Phase 0L Part IV TEST A, which probed both routes precisely because the source said they need not agree.
- *Impact:* LATENT, not active: every current deck carries a *PLASTIC card. In this binary the two routes agree to 3e-6, so the uninitialised value reads as zero here -- an observation about one build, not a guarantee.
- *Fix:* Rule adopted and used in all Phase-0L decks: to obtain a zero yield surface, write an explicit flat *PLASTIC card at sigma_y = 1e-6 MPa rather than omitting the card.
- *Status:* **DOCUMENTED (latent, not triggered)**
- *Lesson:* Where the manual and the source disagree about a default, the source wins and the behaviour must be probed rather than assumed.

#### DEFECT #44 — PHASE-0L CONSTITUTIVE AND RELIABILITY STATUS NOT PROPAGATED INTO CURRENT-FACING TEXT

A directed comparison of both reports against the Phase-0L findings, on thirteen named claim
patterns, found 21 stale current-facing hits. In the historical report they cluster in three
GENERATED blocks: the Executive Summary (8 hits, and NO mention of Phase 0L anywhere in it), the
governing-equation status (2 hits, including 'C still cancels in a ratio, so the RELATIVE ratio
Z2/Z1 = 1.21-1.38 is validated', which is wrong in the number, in the word validated and in the
cancellation claim), and the mechanical validation status ('M0 rung only ... no plasticity,
creep or fatigue', which describes the GLOBAL model as if it were the whole mechanical model).
In the standalone report there are three genuine defects plus one wrong mechanism, the worst
being an INTERNAL CONTRADICTION: section 17.4 says 68 specimens per cell and section 23.1 says
34.

- *Detected by:* Phase 0L-R Part 1, scripts/phase0lr/propagation_audit.py
- *Impact:* A reader of either Executive Summary would take away a superseded relative-life range, the word VALIDATED where only CONDITIONAL is earned, an experiment described as ready to execute when it is blocked, and a specimen count superseded twice over.
- *Fix:* Repaired at the source. All three historical blocks are generated from current_facing.* in this file, so the YAML was rewritten and the blocks regenerated; the five standalone defects were repaired in place. A scanner bug was also fixed during the audit: '##' subsections did not inherit their parent chapter's scope, which made superseded chapters read as current.
- *Status:* **CONFIRMED AND FIXED**
- *Lesson:* This is the SEVENTH instance of one failure -- the narrative advances and the generated status does not. Phase 0K-R added a typed contract to stop it and the contract itself was not extended by Phase 0L. A contract only works if the phase that changes the science is required to change the contract in the same breath.

#### DEFECT #45 — BOARD-LEVEL CAMPAIGN WAS DESIGNED BEFORE THE DOMINANT CONSTITUTIVE UNCERTAINTY WAS CLOSED

The 4-cell, 34-per-cell, 136-package campaign was designed in Phase 0K-R and costed in Phase 0L
on the assumption that specimen count was the binding constraint. It is not. With the corrected
model the ceiling on the discrimination Z-score is 3.61 against a target of 3.0, and that
ceiling is set by the SIMULATION-uncertainty floor of 0.06, which no number of boards reduces.
Halving that floor takes the campaign from 48 specimens per cell to 18, i.e. from 192 packages
to 72.

- *Detected by:* Phase 0L-R Part 16 value-of-information analysis, results/phase0lr/sample_count_vs_simulation_uncertainty.csv
- *Impact:* Worse than inefficiency. The campaign's headline output is an absolute-life constant, and fitting that constant on top of an extrapolated constitutive model buries the constitutive error INSIDE the fitted constant, where it can never be separated again. Running the campaign first does not merely under-inform, it contaminates the quantity it is run to obtain.
- *Fix:* Not a code defect -- classified as a SEQUENCING defect. The campaign is re-sequenced behind material characterisation, not cancelled. Sample count is marked PROVISIONAL and must not be frozen while constitutive uncertainty dominates.
- *Status:* **CONFIRMED (sequencing, not code)**
- *Lesson:* A design of experiments is only as good as the uncertainty decomposition behind it. Phase 0K-R optimised the term it could compute -- Weibull scatter -- without checking which term actually bound the answer.

#### DEFECT #46 — STEP-BOUNDARY TEMPERATURE ALIASING INFLATED EVERY INELASTIC-ENERGY NUMBER BY 18.5 %

parse_temperature() kept the FIRST temperature block at a given printed time while
parse_tensors() keeps the LAST. CalculiX prints the same rounded time on both sides of a step
boundary, so tensors and temperature were taken from OPPOSITE sides of every boundary -- 11 of
690 time points, at which the parsed temperature was wrong by about 55 K. The thermal strain is
hydrostatic, so this injected a spurious VOLUMETRIC inelastic strain of 1.2e-3 into a quantity
that must be isochoric: the trace of the reconstructed inelastic strain was 8.7e-4 against
2.9e-6 for a reconstruction using the solver's own mechanical strain.

- *Detected by:* Phase 0L-R Part 4. An independent reimplementation using the solver's ME output disagreed with production by a suspiciously STABLE 18.5 %; splitting the work into deviatoric and volumetric parts localised it immediately -- the deviatoric parts were identical to six figures and the whole discrepancy was volumetric.
- *Impact:* Every energy-derived quantity produced before this phase is affected: M3/M5, w_acc, w/eps, the discrimination ratio D, the energy-based life-law ratios and hence the experiment sample count. PEEQ and every strain-based metric are UNAFFECTED, because PEEQ is read from the solver rather than reconstructed. Measured on the M1 Z1 baseline, W falls from 1.45725 to 1.19157 MJ/m3 once fixed.
- *Fix:* parse_temperature now keeps the LAST block at each time, matching parse_tensors; agreement with the independent implementation improves from 18.5 % to 0.76 %. The decision-relevant replay cells were re-run with the fix. RECOMMENDED PERMANENT FIX, not applied in this phase because it requires re-running every deck: request ME in the decks and compute eps_in = ME - eps_elastic, which removes the temperature from the energy path entirely.
- *Status:* **CONFIRMED AND FIXED**
- *Lesson:* The audit that found this was written to check quadrature and convergence. What it actually caught was a parser disagreeing with its sibling about which side of a discontinuity to stand on. An independent reimplementation is worth more than a more careful reading of the same one -- and the first version of THIS audit was itself wrong in the opposite direction, for the same class of reason, until its own temperature parser was checked against the solver's thermal strain.

#### DEFECT #47 — PER-VIA CURRENT LIMIT WAS A PRIMITIVE IN AMPERES, AND IT IS THE ONLY THING THAT SETS FIELD RESISTANCE

configs/phase0dr/power_path_graphs.yaml carries i_max_a per tier -- BGA 0.5 A, C4 0.2 A, TSV
0.033 A, microbump 0.02 A -- as a primitive number. Phase 0M Part 3 derives that under the
allocation policy the framework actually uses, R_field = rho h J_max / I with the conductor
cross-section cancelling identically, so J_max is the ONLY parameter that sets the field
resistance and it was entered rather than derived.

- *Detected by:* Phase 0M Part 1 parameter classification
- *Impact:* The via-field resistance, IR drop and Joule loss of every architecture depend on a primitive. The geometry the framework carefully models cancels out.
- *Fix:* i_max_a is replaced by J_max * A_conductor, with J_max a PROCESS limit swept over the sourced 1e8 to 4e8 A/m2 envelope and A_conductor DERIVED from r and the liner.
- *Status:* **CONFIRMED, MODEL REPLACED IN scripts/phase0m/interconnect.py**

#### DEFECT #48 — ONE GLOBAL CURRENT-CROWDING CONSTANT APPLIED TO FOUR DIFFERENT INTERCONNECT CLASSES

scripts/phase0e/architecture0e.py sets CROWDING_DEFAULT = 1.326, measured in HFSS on ONE P/G TSV
loop, and multiplies the single-conductor resistance of BGA, C4, TSV and microbump by it alike.

- *Detected by:* Phase 0M Parts 7 and 8
- *Impact:* K_crowd measured over 107 converged transition geometries spans 0.606 to 1.483, a factor of 2.45. A generous landing pad gives K < 1; a narrow trace entry gives K > 1.4. The excess resistance dR is length-INDEPENDENT while K_crowd is not, so K_crowd is not even the right form.
- *Fix:* A 3-D DC conduction solver derives K_crowd per geometry (results/phase0m/current_crowding_transition_sweep.csv). dR, not K_crowd, is the transferable quantity.
- *Status:* **CONFIRMED, FUNCTION AVAILABLE, NOT YET WIRED INTO THE PRODUCTION PATH**

#### DEFECT #49 — THE TSV LINER IS ABSENT FROM THE CONDUCTOR AREA

ppdn.tier_area_m2() uses the full drilled diameter as conductor. A real TSV has a dielectric
liner between the copper and the silicon.

- *Detected by:* Phase 0M Part 2
- *Impact:* The conducting area is overstated by [r/(r-t_ox)]^2 = 7.0 % at r = 15 um, t_ox = 0.5 um. R_field is UNAFFECTED under minimum-capability allocation because the cross-section cancels, but the per-via current, the copper fraction and every derived thermal and mechanical effective property are wrong -- and Part 21 shows the liner fraction t_ox/r is what makes a fine-pitch field thermally worse in plane at equal copper.
- *Fix:* TSVGeometry carries t_liner and uses r_cu = r - t_liner for all conducting areas.
- *Status:* **CONFIRMED, MODEL REPLACED**

#### DEFECT #50 — THE CONVERTER AREA MODEL SILENTLY ASSUMES FOUR-LAYER VERTICAL STACKING, AND SAYS THE OPPOSITE

Scalable_Integrated_VR/src/HVR_FULL_OPT_EPC_V2.py::_compute_area returns max(N*fp_hs, K*fp_ls,
K*fp_ind, (N-1)*fp_cap). Its docstring says 'Total estimated component footprint' and the file
header claims the function was 'fixed: area = SUM of all component footprints (not max)'. It is
a max. The sibling implementation in HVR_FULL_OPT_sizing.py is honest about it: 'Vertical
stacking model: total footprint is the max across layers'.

- *Detected by:* Phase 0M Part 14
- *Impact:* The reported 5.61 mm2 per VR cell is a PER-LAYER footprint. The summed component footprint of the compiled 1-kW cell is 18.01 mm2, 3.21x larger. Component-level z partitioning is therefore ALREADY assumed -- by the area model and by nothing else. Nothing checks that the four layers exist in a given architecture, and a single-level VR misses the 500 mm2 die shadow by 1.76x.
- *Fix:* configs/phase0m/component_partition_templates.yaml makes the partition explicit and checks each template for height, per-level area, array footprint against the die shadow, voltage-domain mixing and level crossings.
- *Status:* **CONFIRMED, DOCUMENTED, UPSTREAM NOT EDITED (separate repository)**

#### DEFECT #51 — INTRA-CONVERTER ROUTING IS ABSENT FROM EVERY LOSS TERM

The framework models VR-to-package and package-to-POL routing. It models no metal between the
converter's own components. The upstream loss model contains R_DS(on), the inductor DCR, the
capacitor ESR and the switching losses, and no metallization at all.

- *Detected by:* Phase 0M Part 10
- *Impact:* 4.06 to 39.31 W system-wide, 0.41 to 3.93 % of the load, against a converter loss of 125.26 W. Common-mode across Z1, Z2 and Z4, so it does not reorder them, but it is not small. It also exposes a feasibility failure the framework could not see: the VR output plane needs 8.6x the available tile width to stay inside the sourced copper current-density envelope.
- *Fix:* scripts/phase0m/routing.py models it at R0/R1/R2 fidelity.
- *Status:* **CLOSED IN PHASE 0M-R. Status at discovery (Phase 0M): CONFIRMED, MODEL BUILT, NOT YET WIRED INTO THE PRODUCTION LOSS TOTAL. Superseded by Phase 0M-R, which put intra-VR routing into the production loss ledger as P_intraVR_metal and P_intraVR_vertical, template-aware.**

#### DEFECT #52 — THE CALIBRATED COOLING BOUNDARY IS INCONSISTENT WITH THE SOURCE'S OWN FLOW RATE BY A FACTOR OF 16.8

h_top = 166 000 W/m2K was inverse-calibrated to reach 84 C. Derived from geometry and flow, no
laminar microchannel architecture reaches it: the best laminar case gets 0.70x and reaching the
calibrated value appeared to need 50 g/s in the transitional regime, 74 W of pumping and 1.46
MPa -- three figures WITHDRAWN in Phase 0M-R2 and retained here only as the status at discovery.
Withdrawn because: the 50 g/s point sits at Re = 2342, between the laminar ceiling of 2300 and
Gnielinski's floor of 3000, where no validated correlation exists. What survives is the
qualitative finding that no laminar microchannel architecture reaches the calibrated value.
Separately, at the source's stated 1.6 g/s the coolant temperature rise for 1125 W of heat is
168 K, which single-phase water cannot do; 26.9 g/s is needed for a 10 K rise.

- *Detected by:* Phase 0M Parts 23-25
- *Impact:* The Robin boundary absorbs a caloric resistance that DOMINATES the thermal path at low flow and presents it as a surface property. It charges no pumping power -- 7.4 % of the load at the calibrated operating point. And because its sink is a single temperature it cannot produce a streamwise gradient: imposing the real coolant rise moves the die warpage by up to 8.19 % and T_max by 11.3 K.
- *Fix:* scripts/phase0m/cooling.py derives h from channel geometry and flow with source-backed correlations and charges the pressure drop and pumping power.
- *Status:* **CLOSED IN PHASE 0M-R. Status at discovery (Phase 0M): CONFIRMED, MODEL BUILT, NOT YET ADOPTED BY THE ETM LOOP. Superseded by Phase 0M-R, which placed the physical microchannel cooler in the production ETM loop. The correlation-domain question this row raises about the 50 g/s point is itself re-audited in Phase 0M-R2.**

#### DEFECT #53 — THE CURRENT-STATUS GENERATOR PRINTED A SUPERSEDED PHASE'S BASIS UNDER THE CURRENT PHASE'S VERDICT HEADING

`verdict.basis` was written at Phase 0H and never phase-scoped, so every later phase printed six
Phase-0H bullets beneath its own verdict heading while the same report's Executive Summary said
the opposite. Cross-report consistency was 25/25 throughout, because both reports were generated
from the same stale field and therefore agreed with each other.

- *Detected by:* Phase 0M-R Section 2
- *Impact:* Eight phases of reports carried a basis that did not belong to their verdict. Agreement between two reports generated from one stale source is not evidence.
- *Fix:* scripts/phase0g/generate_status_sections.py scopes the key as `basis_<phase>` with the unscoped key as a fallback only for the phase that wrote it; scripts/phase0mr/state_contract.py owns the authoritative field set.
- *Status:* **CLOSED IN PHASE 0M-R. Registered retroactively in Phase 0M-R2: Phase 0M-R documented this defect in results/phase0mr/DEFECT53_REPORT_STATE_AUDIT.md and referenced it in three superseded notes, but never added it as a numbered row, so the defect register itself stopped at 52 while the prose spoke of #53.**

#### DEFECT #55 — THE TSV-FIELD MATERIAL OVERRIDE WAS KEYED ON IN-PLANE FOOTPRINT, SO THE PCB, THE BGA FIELD AND THE BACKSIDE CONVERTER WERE MODELLED AS A COPPER/SILICON COMPOSITE

etm.mesh decided which layers CONTAIN the TSV field from the same `footprint` field that says
how far a layer extends IN PLANE. Every assembly layer added below z = 0 in Phase 0G -- the PCB,
the BGA field, and for ARCH_Z2 the backside converter -- spans the substrate extent and
therefore had its material overwritten with `tsv_homog` inside every tile.

- *Detected by:* Phase 0M-R2 Section 2, while building the ARCH_Z4 power die
- *Impact:* 522 to 859 mm3 of misassigned volume against 20 to 77 mm3 of real via field, and the ratio is architecture-dependent (25.7x for Z1, 11.2x for Z2, 6.8x for Z4), so it did not cancel in the comparison. Where FR4 belongs the model had k too high by 530x, E by 6.3x and CTE too low by 3.4x -- in precisely the layers that set package warpage and corner-joint shear, the deciding metric. Correcting it moved Z1 die warpage from 25.37 to 44.50 um (+75 %) and the Z1 corner driver from 4.2803 to 4.9803 um (+16.4 %), and moved the Z1/Z2 driver ratio from 1.2552 to 1.1942.
- *Fix:* etm.mesh.Layer gains an explicit `tsv_host` flag. `footprint` and `tsv_host` are now separate questions, and only layers the field actually passes through carry it. Negative-tested in tests/phase0mr2/test_geometry_and_cooling.py.
- *Status:* **CONFIRMED AND CLOSED IN PHASE 0M-R2**

#### DEFECT #54 — PHASE-0M-R PRODUCTION STATE DID NOT PROPAGATE THROUGH ALL CURRENT-FACING REPORT SECTIONS, AND THE CHECKER COULD NOT SEE IT

The Phase-0M-R cross-report checker matched each report as ONE FLAT STRING. A REQUIRED phrase
found anywhere satisfied the check for the whole document, so `microchannel` occurring in the
Phase-0M-R chapter passed the cooling check while the Validation Status block three thousand
lines earlier still described the frozen inverse-calibrated Robin boundary. The checker also had
no way to detect an OMISSION: a current-facing section that never mentions a production model
cannot be caught by a forbidden-phrase list. Two further gaps: its FORBIDDEN patterns were
paraphrases rather than the report's real sentences, and its chapter- supersession vocabulary
knew `superseded by` and `extended by` but not `rescoped by`.

- *Detected by:* Phase 0M-R2 Section 1
- *Impact:* SEVENTEEN stale current-facing findings across EIGHT claims survived a green 46/46 cross-report run and a `0 stale current-facing claims` assertion: the gate count stood at seventeen after nineteen gates; Phase 0M was still labelled `current authoritative` after Phase 0M-R; the Executive Summary's next work was the pre-0M-R material-characterisation plan; Electrical Model Validation said no current-crowding correction was applied; Thermal Model Validation described only the retired Robin boundary; defects 51 and 52 read as live; the Executive Summary said the architectures do not differ in temperature; and the document carried a date nine days older than the phases inside it.
- *Fix:* configs/phase0mr2/current_state_claims.yaml gives every claim a SECTION SCOPE, and scripts/phase0mr2/claim_propagation.py checks each named section for the current wording and for un-qualified historical wording. The gate count is DERIVED from meta.gates rather than typed. Every guard is negative-tested against the verbatim stale sentence recovered from the delivered report.
- *Status:* **CONFIRMED AND CLOSED IN PHASE 0M-R2**

#### DEFECT #56 — SECTION-SCOPED CLAIM PROPAGATION STILL MISSED CROSS-FIELD SEMANTIC CONTRADICTIONS AND STRUCTURAL DEFECTS

Phase 0M-R2 fixed DEFECT #54 by making the checker SECTION-SCOPED, which removed the flat-string
failure. The checker remained CONTRACT-DRIVEN: it could only find a contradiction for a claim
somebody had already entered in its list. Two further classes of defect are invisible to any
such list. (1) CROSS-FIELD contradictions, where two fields are each individually well-formed
but jointly inconsistent -- an open-items entry treating the mechanical criterion as though it
were the only obstacle to G2 while the authoritative field lists THREE independent ones. (2)
STRUCTURAL defects, which are not claims at all -- one paragraph shipped FOUR times, and a
provenance row reading 'Report date 2026-09-08' beside a front matter reading 2026-09-17. A
third weakness was found while building the replacement: the retraction heuristic cleared a
forbidden sentence because an UNRELATED 'WITHDRAWN' appeared in the same paragraph, which
silently exonerated both the cooling wording and the 'measures DAMAGE' wording.

- *Detected by:* Phase 0M-R3 Section 1
- *Impact:* EIGHTEEN current-facing findings survived a report certified as having zero: a verdict bullet reading 'THE COOLING MODEL HAS A DOMAIN HOLE, AND THE PRODUCTION POINT IS NOT IN IT' immediately before a sentence saying the production point is inside the validated domain; the mechanical criterion written up as the only obstacle to G2; the FE response metric called DAMAGE while no damage law, life model or failure criterion is closed; four identical copies of one paragraph; two different report dates; and a provenance table claiming 'PALACE (built, functional)' for a solver that is not on this system at all.
- *Fix:* configs/phase0mr3/semantic_contract.yaml adds CROSS_FIELD invariants and STRUCTURAL rules alongside the per-claim list, and marks self-contradictory claims as not exonerable by a neighbouring retraction. scripts/phase0mr3/semantic_audit.py enforces all three families. scripts/phase0mr3/repair_report.py performs the structural repairs idempotently.
- *Status:* **CONFIRMED AND CLOSED IN PHASE 0M-R3**

#### DEFECT #57 — THE CURRENT-STATE CONTRACT REMAINED AT PHASE 0M-R2 AFTER PHASE 0M-R3 WAS DECLARED AUTHORITATIVE

Two independent representations of the current state exist. `meta.current_phase` and
`verdict.phase0mr3` drive the verdict heading and were advanced in Phase 0M-R3. The
`current_state_contract` block, owned by scripts/phase0mr/state_contract.py and rendered as the
'Current scientific status' TABLE, was not. The report therefore carried a section headed
'Current scientific status (Phase 0M-R3)' whose table said phase = 0M-R2 complete, gave the
Phase-0M-R2 verdict, said ZERO OF TWELVE REALIZABLE after a realizable pair had been found, and
listed Phase-0M-R2 next work. A third stale source, `next_gate.id`, still named two actions --
adopt the physical cooling model and put the RDL in the mechanical mesh -- that Phases 0M-R and
0M-R2 had already completed. A fourth: `current_G2_status` said TWO independent blockers where
the authoritative field lists THREE. A FIFTH was found while re-running the suite:
configs/phase0mr2/current_state_claims.yaml carries its own copy of current state -- meta.gates,
meta.current_authoritative_phase, and the gate_count and phase_authority claim wordings -- and
none had been advanced past 0M-R3 either, so the Phase-0M-R2 checker was validating the report
against a superseded contract. The number of falsification gates alone was written out in FOUR
places. A separate latent bug hid every one of them: the regex that reads the count word cannot
capture a hyphenated number word, so at the twenty-first gate it read 'Twenty-one' as 'one' and
reported a correct report as wrong. It had been silently correct for gates 17 to 20 because
those words have no hyphen.

- *Detected by:* Phase 0M-R3A Section 1
- *Impact:* The single most prominent current-state table in the report was a full phase behind, and disagreed with the verdict printed immediately above it. The Phase 0M-R3 semantic checker did not catch it because its contract listed claims by SENTENCE, and these fields were never entered as claims.
- *Fix:* Every current_state_contract field advanced to Phase 0M-R3A; next_gate rewritten from the open-items ledger; a structural rule added that fails when two current next-work sources disagree or when any current-state field names a superseded phase.
- *Status:* **CONFIRMED AND CLOSED IN PHASE 0M-R3A**

#### DEFECT #58 — THE INTRA-VR ROUTING REPAIR BORROWED THE THROUGH-SILICON VIA PROCESS RANGE FOR A PACKAGE-SUBSTRATE INTERCONNECT

Phase 0M-R3 repaired the binding route `ls_to_L` by raising its via radius from 15 to 20 um and
justified 20 um as inside `design_variables.tsv.radius_m = {lo 2.5, nominal 15, hi 50} um`. That
range governs THROUGH-SILICON VIAS. `ls_to_L` connects the low-side GaN switch node on tier 1 to
the inductor terminal on tier 3, a 673 um vertical span BETWEEN EMBEDDED-COMPONENT LAYERS inside
the converter cell. The framework's own source picture separates the two structures explicitly:
components are 'embedded within the subsequent substrate power layers' while 'the TSV field runs
beneath it from the substrate underside', spanning 74 um for ARCH_Z1. They are different
technologies in different regions of the stack.

- *Detected by:* Phase 0M-R3A Section 4
- *Impact:* Phase 0M-R3's claim that the realizability repair used 'only existing/sourced technologies' does not hold. The design space contains no geometry rule for a stacked via through substrate power layers: it has tsv.* (through-silicon), rdl.* (trace width and space only), and bump.* (bumps, not vias through dielectric). The repair is a self-consistent design point in an UNSOURCED process window. It is not shown to be wrong, and it is not shown to be manufacturable. Package clearances are therefore NO LONGER the sole reason the repaired pair falls short of PROVEN_REALIZABLE.
- *Fix:* Provenance chain recorded in results/phase0mr3a/LS_TO_L_INTERCONNECT_AUDIT.md and interconnect_technology_provenance.csv. The wording 'source-backed repair' is withdrawn and replaced by 'design point in an unsourced process window'. The realizability verdict is reopened accordingly.
- *Status:* **CONFIRMED AND CLOSED IN PHASE 0M-R3A**

#### DEFECT #60 — THE STRESS DISTRIBUTION WAS CALLED `DAMAGE-WEIGHTED` WHEN NO DAMAGE LAW IS APPLIED ANYWHERE IN THE WEIGHT

scripts/phase0lr/mechanism_audit.py::elementwise_damage forms the element weight as w = dPEEQ *
V -- the solver's own equivalent inelastic strain increment times element volume. There is no
Coffin-Manson relation, no Darveaux energy-to- cycles law and no accumulated damage variable
anywhere in that calculation. The quantity is therefore a RESPONSE weighting. Current-facing
text nevertheless said `damage-weighted median stress`, `99.8 % of package damage`, `temperature
enters the damage physics`, and `a local solder viscoplastic damage metric`, each of which
presumes the sourced damage law the framework lists as OPEN.

- *Detected by:* Phase 0M-R3B Section 1
- *Impact:* The report asserted in one row that the FE output is NOT damage and in another that `99.8 % of package damage` lies outside the fitted window. Nine such statements were current-facing across both reports.
- *Fix:* Renamed to inelastic-strain-weighted and accumulated inelastic strain, with the weight stated explicitly. A cross-field rule weighting_is_response_not_damage now rejects the old wording in any current section, negative-tested against the real sentences.
- *Status:* **CONFIRMED AND CLOSED IN PHASE 0M-R3B**

#### DEFECT #61 — THE SEMANTIC AUDIT TREATED AN INTRA-WORD APOSTROPHE AS AN OPENING QUOTE AND EXONERATED EVERY FORBIDDEN PHRASE AFTER A POSSESSIVE

mentioned_not_asserted() clears an occurrence when an odd number of quote marks precedes it in
the sentence, and _QUOTE included the plain apostrophe. In `the joint's damage-weighted median
stress is about 82 MPa` the apostrophe in joint's is the only mark before the match, so the
count is odd and the sentence was silently read as a quotation. Any forbidden phrase that
happened to follow a possessive in the same sentence was unreachable by every cross-field rule.

- *Detected by:* Phase 0M-R3B Section 1, while DEFECT #60 failed to fire
- *Impact:* Three of the nine DEFECT #60 findings were hidden by this, including the Executive Summary sentence. The guard family had been reporting 0 findings.
- *Fix:* Apostrophes with a letter on both sides are stripped before the quote count. Negative-tested with the real sentence.
- *Status:* **CONFIRMED AND CLOSED IN PHASE 0M-R3B**

#### DEFECT #64 — VIA LEVELS WERE COUNTED FROM MATERIAL LAYERS INSTEAD OF CONDUCTOR PLANES

Phase 0M-R3B observed that ls_to_L crosses three material layers -- RDL 10, flying-capacitor
tier 100, RDL 10 -- and concluded three stacked microvia levels. RDL_UM is an interlayer
REDISTRIBUTION layer: patterned copper, which is exactly what a laser microvia lands on. A via
level is needed per DIELECTRIC region between conductor planes, not per material layer. The
correct count is ONE via level of 100 um. The same recount shows the baseline's genuinely hard
net is hs_to_cf, which crosses the entire 606 um low-side GaN tier.

- *Detected by:* Phase 0M-R3C Section 3
- *Impact:* Phase 0M-R3B measured a three-level stack against a sourced two-stacked-plus-one-staggered limit, applied a factor-two staggering penalty to the available count, and concluded that ZERO configurations satisfy both sourced bounds. That conclusion is WITHDRAWN: at one via level the baseline already passes at a sourced pitch, with a routing ratio of 0.543 at 150 um.
- *Fix:* scripts/phase0mr3c/conductor_planes.py derives the via count from the conductor-plane sequence for every template and net, and the feasibility contract is recomputed from it.
- *Status:* **CONFIRMED AND CLOSED IN PHASE 0M-R3C**

#### DEFECT #62 — VERTICAL INTERCONNECT SPANS WERE MEASURED TIER MID-PLANE TO TIER MID-PLANE

routing_production.build_edges() builds every vertical Edge with abs(z_of(b) - z_of(a)), and
z_of() returns a tier MID-PLANE. The link from the low-side GaN switch to the inductor was
therefore measured centre-of-die to centre-of-inductor, 673 um, a line that passes through 303
um of GaN body and 250 um of inductor body. Components are contacted at their terminal faces, so
the build-up a via chain crosses is the 120 um gap between them: RDL 10 + flying- capacitor
layer 100 + RDL 10. The defect is systematic across all three vertical edges, at 1.63x on
hs_to_cf, 5.61x on ls_to_L and 65.55x on hs_to_ls, where two dies in adjacent tiers are
separated physically by one 10 um RDL.

- *Detected by:* Phase 0M-R3B Section 2
- *Impact:* Vertical resistance and loss were overstated: 1.110 W of intra-VR vertical loss, 0.80 % of the electronics total. n_required is unaffected because it has no length in it, so no Phase-0M-R3A count or ratio changes. It also misdirected the Phase-0M-R3A sourcing question towards an exotic 673 um structure when the real one is ordinary embedded-component build-up.
- *Fix:* Physical face-to-face spans are available behind PHASE0MR3B_PHYSICAL_SPANS=1, default off so every prior result stays bit-identical until a phase adopts them.
- *Status:* **CONFIRMED; correction available opt-in, not yet adopted into production**

#### DEFECT #63 — VIAS AVAILABLE WERE COUNTED OVER THE SOURCE DIE FOOTPRINT, NOT THE FREE AREA OF THE LAYER THE CHAIN CROSSES

edge_loss() computes n_available = footprint_mm2 * packing / pitch^2 with footprint_mm2 = 1.80,
the gan_ls footprint. The ls_to_L chain has to get through the flying-capacitor power layer, and
in that layer the 5.61 mm2 cell already holds two 2.00 mm2 embedded MLCCs, leaving 1.61 mm2. The
binding area is the free area of the most crowded layer crossed, not the footprint of the
component the net starts at. Separately, EPC2057 is an LGA 1.5 x 1.2 mm part, so vias can only
land on its lands and not on arbitrary points of its footprint; that land pattern is in no
source held here and is recorded OPEN.

- *Detected by:* Phase 0M-R3B Section 4
- *Impact:* At 1.61 mm2 the Phase-0M-R3 repair gives a routing ratio of 1.0427 and is INFEASIBLE, where 1.80 mm2 gave 0.9344 and feasible. The repair that produced the Phase-0M-R3 CONDITIONAL_REALIZABLE pair does not survive the corrected area.
- *Fix:* Feasibility is recomputed over the free area of the binding layer in results/phase0mr3b/ls_to_L_feasibility.csv, across the sourced pitch and stacking bounds.
- *Status:* **CONFIRMED. The Phase-0M-R3 routing repair is WITHDRAWN.**

#### DEFECT #59 — THE Z2 TSV PROCESS-MARGIN REPAIR STATED THE DIRECTION OF THE VIA-COUNT CHANGE BACKWARDS

Phase 0M-R3 wrote that moving ARCH_Z2 from a 30 um to a 34 um TSV restores M_AR = 1.089 'at the
cost of 22.8 % more vias'. Under minimum-capability provisioning n_required = ceil(I / (J_design
* A_cu)) scales as 1/A_cu, so a larger via needs FEWER of them: 15 140 -> 11 692, which is 22.8
% FEWER. The magnitude was right and the sign was inverted, and the change was labelled a cost
when it is a reduction. The underlying source of the error is that 'via count' was used without
saying WHICH count.

- *Detected by:* Phase 0M-R3A Section 6
- *Impact:* A reader would conclude the margin repair carries a routing-density penalty it does not have. A second error was found in the same sweep: Phase 0M-R3 reported 34 um as the smallest diameter with positive margin, but its grid was 30/34/40/50/60 and never evaluated 32 um, which passes the same modest bound at M_AR = 1.067.
- *Fix:* results/phase0mr3a/Z2_TSV_PROCESS_MARGIN_REAUDIT.md separates n_required, n_allocated, n_available and total Cu area, verifies n_required against an independent hand calculation at every diameter, and adds 32 and 36 um to the grid. All report text corrected.
- *Status:* **CONFIRMED AND CLOSED IN PHASE 0M-R3A**

### Next gate

**POST-0M-R3A -- (1) source a process rule for the intra-converter vertical interconnect; (2)
source the three package clearances; (3) close the ARCH_Z2 TSV process margin at 32 um; (4)
high-stress SAC305 characterisation; (5) canonical conjugate CFD. Adopting physical cooling and
putting the RDL into the production thermal model are COMPLETE and are not future work..** Phase
0M found five first-order physical models that exist as validated SCREENING tools and do not
drive the production path: intra-VR routing, geometry-specific transition resistance, physical
cooling, RDL thermal anisotropy and component-level z partitioning. Phase 0M-R wires the ones
with sufficient evidence into production and re-asks which Phase-0M conclusions survive. In
parallel, and NOT blocking it, high-stress SAC305 material characterisation remains the dominant
scientific blocker.

**Explicitly not next:** the global ETM optimizer.

