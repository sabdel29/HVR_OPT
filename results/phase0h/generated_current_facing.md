<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml -- DO NOT EDIT BY HAND. -->
<!-- Regenerate with scripts/phase0g/generate_status_sections.py (DEFECT #32). -->

<!-- BEGIN GENERATED: exec_summary -->

# Executive Summary

**Original hypothesis.** Distributed vertical power delivery is normally optimised on electrical
and thermal grounds alone. This project asked whether package thermo-mechanics -- warpage and
stress -- is a SYNTHESIS constraint that changes which DVPD architecture one would choose,
rather than a downstream signoff check.

**Answer.** No, on the evidence available. Phases 0G through 0I find a real, sign-stable, cross-
validated mechanical RESPONSE to the electrical design variables -- now including a resolved,
architecture-dependent SOLDER-FATIGUE response -- and no admissible inequality anywhere that
could turn any of it into a constraint. Phase 0H tested nine candidate thresholds against six
admissibility conditions and admitted none. Phase 0I then added vertical placement as a genuine
design variable and a temperature-dependent elastic/plastic/creep joint model, and Phase 0I-R
verified that model's response metric; in that HISTORICAL architecture set the architectures
separated by -35.8 % and +12.4 % in per-cycle inelastic strain, at 5.8x and 5.1x their
uncertainty. The Phase-0M-R3 frozen comparison -- subsequently found not demonstrated realizable
under the Phase-0M-R3B substrate-via rule set -- separates by 16.3 %. What is still missing is
not the response but the THRESHOLD. Phase 0J searched for a life law and a required life and
found neither, recording ACCESS as the cause. The primary calibration papers were then supplied,
and Phase 0J-R closes half of that gap: four SnAgCu formulations are admitted for RELATIVE life,
Syed 2004's author-corrected calibration is reproduced, its 25 um averaging volume is matched,
and Z2 shows the lower response under all four. That is an ORDERING of a response metric, not a
lifetime; a survival claim is not earned while absolute N_f is unvalidated. Phases 0L and 0L-R
then audited the constitutive model under that result and found it fitted in the wrong stress
variable, on a different alloy, and evaluated far outside its source window. The ORDERING
survives all of that for a structural reason; its MAGNITUDE is a conditional envelope of 1.19 to
1.22, not a validated number. ABSOLUTE life stays conditional and NO required life exists.
Mechanics is design-relevant as a response model, with a robust RELATIVE ordering and a
conditional magnitude, and is still not a feasibility-set restriction.

**Method.** Twenty-three sequential falsification gates (0B, 0C, 0D, 0D-R, 0E, 0F, 0G, 0H, 0I,
0I-R, 0J, 0J-R, 0K, 0K-R, 0L, 0L-R, 0M, 0M-R, 0M-R2, 0M-R3, 0M-R3A, 0M-R3B, 0M-R3C), each
designed so that a negative result would stop the project rather than be absorbed. No gate was
allowed to pass on a metric that failed mesh convergence, and no mechanical allowable was ever
chosen after seeing results. From Phase 0H onward every automated guard must also be shown to
FAIL on an injected violation before it is trusted.

**What survived.**

* Mechanics responds strongly to architecture: die warpage spans 1.8-15.6 um across the frozen 20-case DOE at fixed load, footprint and heat (Phase 0C).
* Substrate thickness is a genuine three-domain variable and the electrical and mechanical preferences OPPOSE: electrically thinner is better (ARCH_B monotone in 9 corners of 9), mechanically thicker is better (S_h = -0.039 to -0.886 in the free package and all five explicit boards). Over the realizable band the trade is 4.04 W of ARCH_B loss against 29.3 % of mounted warpage. The thickness trend is PRESERVED in the M2-rung solder metrics and is smaller there than in global warpage: across all eleven z-sweep points it is monotone in every architecture, -5.6 % (Z1), -6.1 % (Z2) and -17.2 % (Z4) in accumulated inelastic path, against 29.7-52.6 % in warpage over the same range, so warpage overstates the benefit by 3-5x. The superseded Phase-0H figure of 1.96 %, which belonged to the REJECTED smeared interface-shear proxy and sat 7x below that proxy's own uncertainty, is withdrawn as a current result and is retained only in the Phase-0H historical section.
* The GaN device heights are now SOURCED from manufacturer datasheets -- 685 um high side, 606 um low side -- against the 0/100/250 um envelope earlier phases invented.
* COMPONENT-HEIGHT REALIZABILITY IS ARCHITECTURE DEPENDENT. Component height constrains substrate thickness only where the converter is EMBEDDED (h_sub >= 1.276 mm). Where it sits below, above or beside the substrate, nothing it contains constrains h_sub and the bound falls to the source-demonstrated 0.300 mm TSV layer -- a 4.3x wider range.
* Vertical integration is a real architecture variable with a measurable reliability consequence, and the effect is RESOLVED against uncertainty. On the Phase-0M-R3 frozen comparison -- subsequently found not demonstrated realizable under the Phase-0M-R3B substrate-via rule set. On the CURRENT frozen repartitioned pair the backside architecture carries 16.3 % LESS local fatigue-relevant inelastic RESPONSE than the embedded one, at D_driver = 1.1947 (Z1 4.6252 um, Z2 3.8714 um). The often-quoted 35.8 % and 12.4 % figures are the HISTORICAL Phase-0I result for a different, non-realizable architecture set and must not be presented as the present architecture result. All three inelastic measures -- accumulated path length, strain range and dissipated energy -- give the same ranking. The quantity is a RESPONSE, not damage: a damage law, a life model and an admissible allowable are all still OPEN.
* Temperature-dependent failure physics materially changes the answer, but the SIGN of the change depends on which inelastic measure is used, and Phase 0I-R makes that explicit. Against a no-creep model the STRAIN-based metric falls 29.8 % while the DISSIPATED INELASTIC ENERGY rises 164.6 % over the same solves. Creep relaxes stress and suppresses plastic strain accumulation, yet deforms at sustained stress and so dissipates far more. Neither number may be quoted as `damage decreased` without naming the measure. The Phase-0I -27.2 % figure is valid ONLY as a statement about the strain-based metric.
* Temperature enters the inelastic-response physics through more than thermal expansion: a temperature-INDEPENDENT model moves only -0.2 % as the cycle mean shifts 25 to 75 C, while the full model moves +22.7 %. The older model class was structurally blind to where in temperature a cycle sits.
* Under the PHYSICAL cooler the Z-architectures DO separate in temperature, and ARCH_Z2 is the hottest of the principal candidates: on the CURRENT frozen repartitioned pair, 126.46 C against 118.32 C for ARCH_Z1. It nevertheless carries 16.3 % LESS corner-joint driver. Under the retired calibrated boundary the joint temperatures spanned only 81.10-83.21 C and their correlation with the local inelastic-response metric was r = +0.017, which is why earlier phases described these architectures as separating on mechanics alone; that statement is historical and belongs to that boundary condition. Ranking by package T_max is NOT equivalent to ranking by the solder-fatigue driver, because geometry- and CTE-induced deformation and the local constitutive response are distinct mechanisms. Temperature-dependent physics matters and must not be dismissed.
* The physical metal stack is sourced, not assumed: 10 um Cu, 10/2 um line/space, 2 VDD + 2 GND layers from ECTC-2024 Table I, whose own derived quantities the model reproduces to better than 2 %.
* No AC correction is needed at the switching frequency -- HFSS shows loop resistance flat to 0.18 % below the 19.1 MHz skin crossover, with f_sw two orders below it.
* The rail carried by a vertical interconnect changes its loss by ~1960x for fixed transferred power, and which rail it carries is architecture-specific.
* A via field's loss is proportional to current only under minimum-capability provisioning; under geometric allocation the same field obeys P ~ I^2.
* The model chain is numerically sound: energy balance closes to +-0.000 %, warpage is mesh-converged to 0.50 %, and an independent solver (MOOSE) reproduces candidate ordering at both 240 W and 1 kW.

**What failed.**

* Regulator count is mechanically inert (+0.02 % for 4->6, -4.07 % for 4->8), which killed the variable the original novelty argument leaned on.
* Tile aspect ratio is inert (-1.76 %), and on this square vehicle the two aspect cases are provably identical by symmetry.
* Interface peel never converged (19-20 % per refinement against a <10 % target) and is excluded from all decision logic.
* The geometry used by Phases 0B-0E was not buildable: the selected converter needs a 720 um cell and the mechanical vehicle used a 150 um tile inside 200 or 500 um substrates. Trend DIRECTIONS survive re-running on realizable geometry; every absolute magnitude from those phases is superseded.
* The Phase-0B cooling calibration was not transferable -- at 1 kW the correct film coefficient is 9.47x larger.
* Substrate-side-only cooling, which is the reference system's actual topology, cannot reach the reference junction temperature at 1 kW: it floors at 90.96 C and reaches 110.4 C at h_sub = 2.00 mm.
* The compact BC-B foundation is not a valid model of a mounted package. It clamps all three degrees of freedom, never recovers its own free limit (0.739 um against 8.287 um on the identical mesh), and no support stiffness k* exists over seven decades.
* DEFECT #30: per-regulator and system-wide loss terms were summed together for three phases, understating every vertical tier by n_vr -- 49x at the 1 kW reference. It inverted the Phase-0F architecture conclusion and survived a 25x tighter convergence tolerance.
* DEFECT #31: the semantic ledger built to catch stale claims could not fail, because its exonerating vocabulary matched ordinary English prose within a +-800-character window.
* DEFECT #32: the single source of truth controlled the claims ledger but not the Executive Summary, governing equations, validation status, novelty, limitations, publication claims or next steps. Seven current-facing statements were stale behind a green build.
* Global warpage does not predict local interconnect loading (Spearman 0.112 over 70 paired runs) and inverts sign between assembly states (-0.793 free, +0.349 mounted). The quantity the project measured best is not the quantity that matters.
* Of eight enumerated failure mechanisms, TWO are now computable and SIX are not. Global bending is computable at M0 but is a driver, not a failure. Solder fatigue became computable at M2 in Phase 0I, was verified in Phase 0I-R, and Phase 0J-R admitted four primary-source SnAgCu life laws for it -- so it now yields a ROBUST RELATIVE ORDERING with a CONDITIONAL magnitude, though still no pass/fail: absolute life is model-form uncertain at 4.1x and no required life exists. mechanisms the reference paper itself names -- RDL shear and delamination -- which are absent from the mechanical model entirely.
* No admissible mechanical criterion exists. Nine candidates, zero admitted; every published warpage allowable located is a manufacturing or solderability limit.

**Current strongest novelty.** The defensible contribution is NOT 'mechanics changes the
optimum' -- it does not, and with a pure added objective it structurally cannot. It is an
AUDITED CROSS-DOMAIN DVPD MODEL AND A FALSIFICATION SEQUENCE that establishes where mechanics is
and is not design-relevant: physical-realizability coupling that excludes an entire previously-
swept design range; rail-aware interconnect modelling; corrected RDL / bump / TSV losses with
explicit allocation policy; an electrothermal fixed point with per-regulator local temperature;
a mounted package-mechanics model that is continuous with its own free limit; a demonstrated
thickness response opposition; and the negative result that footprint opposition disappears once
the package is actually mounted.

**Current limitations.**

* No admissible mechanical criterion exists, so G2 is NOT TESTED and no mechanical term may enter a feasibility test. Phase 0I supplies the METRIC half of G2 -- convergent, validated, tied to a documented failure mechanism. Phase 0J-R then supplied part of the ALLOWABLE half: four primary-source SnAgCu formulations are ADMITTED FOR RELATIVE LIFE, Syed 2004's author-corrected calibration was reproduced, and its 25 um averaging volume was matched. ABSOLUTE life remains CONDITIONAL -- the strain- and energy-based models disagree 4.1x on this joint, whose w_acc/eps_acc sits 4.3x off the calibration locus -- and NO required life exists. The Phase-0J statement that no SAC305 life law was retrievable is SUPERSEDED: it was an ACCESS limitation and the primary papers have since been supplied.
* THREE DIFFERENT THINGS, AND THEY MUST NOT BE CONFLATED. (1) THE RELATIVE ORDERING IS ROBUST: Z2 accumulates less local fatigue-relevant inelastic RESPONSE than Z1 under every admitted constitutive model, every admitted life law, every profile and all three response metrics. The FE quantity is a response; calling it damage would presume a sourced damage law that does not exist. It originates in the GLOBAL thermoelastic model, which imposes a 32 % larger corner shear on Z1 and contains no solder law at all: the global package supplies a constitutive-law-independent deformation driver favoring Z2, and every presently testable constitutive/life-law combination preserves that ordering. (2) THE MAGNITUDE IS CONDITIONAL, NOT VALIDATED: the strain-family envelope is 1.19 to 1.22 at the operating baseline, conditional because 99.8 % of the joint's accumulated inelastic-strain contribution is generated above the 7.51-15.92 MPa window the creep law was fitted in, on Sn3.9Ag0.6Cu rather than SAC305. The permitted wording is 'conditional relative-life envelope'; 'validated relative life' is NOT earned. (3) ABSOLUTE LIFE AND REQUIRED LIFE REMAIN OPEN -- the strain and energy formulations disagree 4.1x on this joint, and no field or product requirement exists anywhere in this repository.
* Two of eight failure mechanisms are now addressable: global bending (a driver) and solder fatigue (a real mechanism, added in Phase 0I). RDL damage, delamination, CPI and TSV interaction still need geometry or physics the model does not have, and two of those are mechanisms the reference paper itself names.
* The reliability submodel is displacement-driven and models one joint at the worst location. Its creep law is a variable-consistent SnAgCu Norton surrogate, high-stress extrapolative: fitted over 7.51-15.92 MPa on Sn3.9Ag0.6Cu, while the joint's inelastic-strain-weighted median stress is about 82 MPa and 99.8 % of its accumulated inelastic strain lies outside that window. The weight is the solver's own dPEEQ times element volume; no damage law is applied. Two constitutive FAMILIES can be parameterised there and only one can be integrated, because this solver fails above a Norton exponent of 9 to 10.
* The two PHASE-0H local proxies remain unfit for decisions: smeared interface shear is non-monotone under mesh refinement (7.6 % spread) and relative displacement carries 26.5 % spread from an unsourced underfill modulus. THEY ARE NOT THE CURRENT METRIC. The Phase-0I M2 metric replaces them and passes mesh convergence (1.90 %), creep- tolerance insensitivity (0.02 %) and corner-regularisation stability (6.4 %).
* MLCC height remains OPEN -- Murata is not retrievable in this environment -- so the realizable substrate bound is a 250 um band rather than a number.
* Mounted warpage magnitudes (9.7-29.2 um) are an engineering envelope from an assumed board, not a prediction. Only signs and orderings are claimed.
* All warpage is INCREMENTAL OPERATIONAL with a 25 C stress-free reference. Assembly pre-stress is bounded, not modelled: a 175 C reference raises mounted magnitudes by up to 54 %.
* GaN device height is SOURCE_BACKED (manufacturer datasheets, Phase 0H). MLCC height remains OPEN. Complete packaging clearance for the thinnest non-embedded stack is OPEN: 0.300 mm is COMPONENT-HEIGHT-REALIZABLE under the current Z-architecture model and a source-demonstrated TSV-layer thickness, NOT a manufacturability guarantee.
* The electromigration reliability limit for copper TSVs is open; what is closed is the provisioning current density the sources actually used.
* ECTC-2024's absolute loss magnitudes are not reproducible from its printed model, so RDL magnitudes are always quoted with their stack.
* Q3D Extractor is not licensed, so DC resistance is validated with a conduction FE rather than a commercial extractor. Icepak returned a clamped 5000 K solution on this package model and is unusable.
* Interface peel is excluded for non-convergence; interface shear converged but has no allowable.

**Exact next work.** Phase 0M-R3C is the current authoritative phase and its ranked follow-up is
in results/phase0mr3b/final_open_items.md. In order: (1) REPARTITION so the 20.4 A ls_to_L net
crosses fewer build-up layers, or source a package-substrate rule that permits three stacked
microvia levels -- this is now the binding blocker for BOTH architectures, and the nearest
sourced-legal option misses by only 6 % on area; (2) obtain the six primary sources listed in
results/phase0mr3b/PRIMARY_SOURCES_TO_DOWNLOAD.md; (3) source the two remaining package
clearances, cavity_sidewall_um and cooler_standoff_um; (4) source a TSV manufacturing tolerance,
without which 32 um stays parametrically margined rather than process-qualified; (5) high-stress
SAC305 characterisation; (6) the canonical conjugate CFD benchmark. Adopting the physical
cooling model into the ETM loop, putting the RDL into the production thermal model, and sourcing
the interconnect CLASS for ls_to_L are COMPLETE, in Phases 0M-R, 0M-R2 and 0M-R3B respectively,
and are not future work. G2 remains NOT TESTED behind three independent blockers; the optimizer
remains FORBIDDEN.

<!-- END GENERATED: exec_summary -->

<!-- BEGIN GENERATED: governing_equations -->

## Governing-equation status

| # | equation | status | note |
|---|---|---|---|
| 1 | `n_req = ceil(I / I_max); n_req <= n_alloc <= n_avail; R_field = R_single / n_alloc` | **CURRENT** | Phase 0E separated three quantities that Phase 0D-R had conflated into one. Electrical resistance uses n_ALLOCATED, which is what the design actually instantiates. Using n_req makes P ~ I look like a physical law when it is an allocation policy. **Superseded form:** `R_field = R_single / n_req (Phases 0D, 0D-R)`. |
| 2 | `infeasible if n_req > n_avail(A_fp, pitch)` | **CURRENT** | Unchanged. Feasibility is set by what the footprint can physically hold, not by what the allocation policy chose. |
| 3 | `sigma = C(T) : (eps_total - eps_thermal(T) - eps_in); eps_dot_in = A(T) * (sigma_vm - sigma_y(epsbar_in))**n(T) for sigma_vm > sigma_y, and eps_dot_in = 0 identically otherwise; m = 0` | **CURRENT** | CORRECTED IN PHASES 0L AND 0L-R. The earlier form eps_dot_cr = A(T) sigma^n(T) is WITHDRAWN: it is NOT what a *VISCO step executes. The solver drives creep with the OVERSTRESS sigma_vm - sigma_y and returns exactly zero below yield, traced in CalculiX 2.23 src/incplas.f and confirmed to 1.2e-5 over 7603 probe increments. There is NO rate-independent plastic strain in a *VISCO step. A(T), n(T) come from 19 creep points on Sn3.9Ag0.6Cu -- NOT SAC305 -- fitted over 7.51-15.92 MPa against TOTAL APPLIED STRESS, which is not the variable the solver consumes (DEFECT #40). The selected model M1 removes the yield threshold so that fit and solver share a variable; it is labelled a variable-consistent SnAgCu Norton surrogate, high-stress extrapolative, and 99.8 % of the joint's accumulated inelastic strain (dPEEQ*V) is generated outside its fitted window. A(T) and n are interpolated LINEARLY between card rows by the solver, not by Arrhenius; any Arrhenius relation exists only in how the row values were generated. |
| 4 | `d_eps_in(cycle k) = PEEQ(t_end,k) - PEEQ(t_end,k-1), volume-averaged over the solder core with a one-element corner exclusion band` | **CURRENT** | PEEQ is CalculiX's ACCUMULATED equivalent inelastic strain. Phase 0I-R proved by experiment that it includes BOTH plastic and creep: with a creep-only material and no *PLASTIC card, PEEQ / eq(eps_inelastic) = 1.0000. The metric is therefore the inelastic PATH LENGTH traversed per cycle, not a strain RANGE; the two differ by a factor of 3.72 here and the naming is fixed accordingly. |
| 5 | `the stabilised cycle is the first whose d_eps_in differs from the previous cycle by less than 5 %; reported values are from cycle 4 of 4` | **CURRENT** | Achieved 0.48-2.00 % cycle-to-cycle change at cycle 4 for every architecture. The metric is a per-cycle DIFFERENCE of an accumulated quantity, so it is not contaminated by total accumulated creep. |
| 6 | `NONE` | **AVAILABLE_FOR_RELATIVE_LIFE_ONLY** | SUPERSEDED BY PHASE 0J-R. The Phase-0I statement that no exponent is sourced no longer holds: two primary sources now bound it -- Syed 2004 derives -1 theoretically and measures -0.9607, and Schubert 2003 fits -1.3 for SnAgCu. C still cancels in a ratio. That is necessary but NOT sufficient: Phase 0L-R shows the response metric the law consumes is itself produced by an extrapolated constitutive model, so the RELATIVE ORDERING is robust while the MAGNITUDE is a CONDITIONAL envelope of 1.19 to 1.22. 'Validated relative life' is WITHDRAWN. What is also NOT current is an ABSOLUTE lifetime equation: the strain and energy formulations both have constants but disagree 4.1x on this joint. |
| 7 | `P_tier,SYSTEM = n_vr * P_tier,PER_REGULATOR; P_PDN = sum over tiers of SYSTEM-scope terms only` | **CURRENT** | Phase-0H structural guard for DEFECT #30. vertical_tier_per_regulator() returns a PER_REGULATOR quantity and rdl_network_solve() returns a SYSTEM quantity; adding them raises ScopeError. Negative-tested in tests/phase0h/test_scope.py. |

Symbols required by the current forms and therefore mandatory in the symbol table: `n_alloc`,
`n_avail`, `n_req`.

<!-- END GENERATED: governing_equations -->

<!-- BEGIN GENERATED: validation_status -->

## Validation status

| domain | status | validated | not validated |
|---|---|---|---|
| electrical | **SUPPORTED** | Multilayer RDL sheet model agrees with an independent MOOSE conduction solve to 0.45-1.10 % on power across three placements under one calibration. HFSS confirms no AC correction is needed below the 19.1 MHz skin crossover. | Q3D Extractor is not licensed, so no commercial-extractor cross-check of DC resistance exists. |
| thermal | **PROVEN** | Full 3-D MOOSE package thermal cross-check COMPLETED. Phase 0E ran TH-1..TH-5 with spatially mapped Joule heat: candidate ordering preserved exactly, maximum discrepancy 1.66 %, mean 1.05 %. Phase 0F repeated it at the 1-kW reference on the decisive thickness pair: 2.2-2.8 K on T_max, same thickness trend, energy balance closed to 3e-8 % in both codes. | Icepak remains unusable -- it returned exactly 5000 K on every object, a solver clamp from applying an external boundary condition to an internal solid/air interface. That result was discarded and is never used. |
| mechanical | **SUPPORTED** | Analytic free-expansion check exact; four graded mesh levels with die warpage converged to 0.50 %; BC-A reaction forces <= 4.3e-10 N, so the constraint manufactures no stress; the explicit BGA + board assembly is continuous with the free package (+18.1 % with a vanishing board, the residual being the BGA layer's own contribution). | No ANSYS structural validation exists. No assembly pre-stress model, no fracture mechanics, no cohesive zone. |

**Restraint models.** BC-A is 3-2-1 rigid-body suppression. BC-B applies *BOUNDARY {n},1,3 --
ALL THREE degrees of freedom on the underside plane -- so it is a CLAMP and NOT a compliant
mounted support; Phase 0G withdrew it as a model of a mounted package. BC_BOARD is an explicit
BGA + PCB stack restrained only by 3-2-1 anchors and is the model used for mounted conclusions.

<!-- END GENERATED: validation_status -->

<!-- BEGIN GENERATED: reliability_metric -->

## The local reliability metric, exactly defined

| field | value |
|---|---|
| **name** | d_eps_in -- accumulated equivalent inelastic strain per stabilised cycle |
| **exact definition** | d_eps_in(k) = PEEQ(t_end of cycle k) - PEEQ(t_end of cycle k-1), volume-averaged over the solder core with a one-element corner exclusion band: d_eps_in = sum_e(d_PEEQ_e * V_e) / sum_e(V_e) |
| **units** | dimensionless (strain) |
| **solver output** | CalculiX 2.23 PEEQ from *EL PRINT. CEEQ, CE and PE are aliased to PEEQ by the solver; no separate creep field is produced. |
| **plastic component** | INCLUDED |
| **creep component** | INCLUDED |
| **creep verification** | PROVEN BY EXPERIMENT, not inferred. With a creep-only material and NO *PLASTIC card in the deck, PEEQ is non-zero and PEEQ / eq(eps_inelastic) = 1.0000. The identity holds in four single-element probes and, at the first output, in the multiaxial temperature-varying joint (1.0029-1.0035). |
| **is a range** | False |
| **range clarification** | PEEQ is an ACCUMULATED path length, not a state, so the per-cycle difference is the inelastic PATH LENGTH traversed in one cycle, NOT a strain range. At stabilisation the ratio path-length / range is 3.72, not the 2.0 a fully-reversed uniaxial cycle would give, because the OFF-ON-OFF cycle is a multi-reversal path in strain space. Any future life law must be matched to the path-length form or the metric converted. |
| **stabilized cycle definition** | the first cycle whose d_eps_in differs from the previous cycle by less than 5 %; all reported values are cycle 4 of 4, achieved at 0.48-2.00 % |
| **numerical status** | CONVERGENT -- mesh 1.90 % over the final refinement, creep tolerance 0.02 %, corner-exclusion band 6.4 % across 0-2 elements. Including the corner LOWERS the value, so the metric is not corner-dominated. |
| **metric agreement** | The architecture ranking and magnitudes are the SAME under all three inelastic measures -- accumulated path length, instantaneous strain range, and dissipated inelastic energy -- to within 2 pp (Z2 -35.8/-35.7/-37.7 %, Z4 +12.4/+12.6/+13.0 %). The architecture conclusion therefore does not depend on the choice of measure. |
| **metric disagreement** | The CREEP-INCLUSION question DOES depend on the measure: enabling creep moves the strain metric -29.8 % and the energy metric +164.6 %. Direction-of-change statements must always name the measure. |

### Relative life

**PARAMETRIC LIFE-LAW SENSITIVITY -- NOT A LIFETIME PREDICTION.** `N_f = C * d_eps_in^(-m);
N_f,2/N_f,1 = (d_eps_in,1 / d_eps_in,2)^m`

- The constant **C cancels** in a ratio: `True`.
- The exponent **m does NOT cancel**: exponent required = `True`, status = **SOURCED AS OF PHASE 0J-R -- was UNSOURCED in Phase 0I-R. Syed 2004 derives -1 from Monkman-Grant plus a time-fraction rule and measures -0.9607; Schubert 2003 fits -1.3 for SnAgCu. The exponent is bounded, not free.**.
- *Provenance:* Phase 0I annotated a figure with 'typical solder k is 1.5-3'. That range was written from general knowledge, appears in no retrieved source, and was never labelled. It WAS the sole basis of the Phase-0I headline '1.9-3.8x relative life'. SUPERSEDED: Phase 0J-R obtained the exponent from two primary sources, so the Phase-0I parametric span (m = 0.5-5, ratio 1.25 to 9.18) is withdrawn.
- *Correction:* Phase 0I said relative life is 'parameter-free in the life-law constant'. That is literally true of C and MISLEADING as written, because it invites the reading that the ratio is parameter-free. It is not: the exponent m does not cancel. Over m = 0.5 to 5 the Z2/Z1 ratio spans 1.25 to 9.18 -- a factor of 7.4 from the exponent alone.
- *What may be claimed:* the METRIC ratio, which is a model output: Z2 is 35.8 % below Z1 and Z4 is 12.4 % above it. Any conversion to life must be labelled parametric in m.

### Architecture claim closure

| architecture | component height | electrical | local damage |
|---|---|---|---|
| **z1_embedded** | CONSTRAINED -- the LS GaN, flying capacitor and inductor occupy the substrate power layers. h_sub >= 1.276 mm at MLCC nominal (a 250 um band, MLCC OPEN). | BASELINE | BASELINE, d_eps_in = 6.513e-3 |
| **z2_backside** | NOT CONSTRAINED by converter component height. COMPONENT-HEIGHT-REALIZABLE under the current Z-architecture model down to 0.300 mm, the source-demonstrated TSV-layer thickness. Complete package manufacturability at 0.300 mm is OPEN. | RESOLVED -- +1688 mW against a 282 mW combined uncertainty, 5.98 sigma. Driven by carrying 1000 A rather than 23.4 A on the via field. | RESOLVED -- -35.8 % against a 6.2 pp spread across all material, mesh and regularisation perturbations (5.8x). Same sign and magnitude under all three measures. |
| **z4_power_die** | NOT CONSTRAINED. COMPONENT-HEIGHT-REALIZABLE down to 0.300 mm; complete package manufacturability OPEN, and its 1.23 mm power die sits in the die-to-cooler thermal path. | UNRESOLVED -- the +30 mW difference from Z1 is 0.024 % of the total and is dwarfed by a term the electrical sweep set to zero: every architecture was evaluated at a FROZEN T_c = 85.0 C, yet the global model shows Z4 running 1.444 K COOLER than Z1. At dP_conv/dT = 148 mW/K that is 214 mW -- 7.1x the claimed difference, and of the OPPOSITE sign. 0.14 sigma. Z1 AND Z4 ARE ELECTRICALLY INDISTINGUISHABLE AT CURRENT FIDELITY, and Z1 MUST NOT be described as electrically preferred. | RESOLVED -- +12.4 % against a 2.4 pp perturbation spread (5.1x). |
| **z5_lateral** | NOT CONSTRAINED. | THE TESTED TOPOLOGY IS ELIMINATED -- 768.07 W of modelled RDL loss, 52.8 % efficiency. This is NOT a statement about 2.5D as a class. | -- |

<!-- END GENERATED: reliability_metric -->

<!-- BEGIN GENERATED: publication_claims -->

## Publication-defensible claims

* Physical realizability is a first-class DVPD design coupling: the converter component stack sets a hard lower bound on substrate thickness that excluded the entire range swept in Phases 0B-0E.
* The rail a vertical interconnect carries changes its loss by ~1960x at fixed transferred power, and it is architecture-specific.
* Via-field loss scaling is set by allocation policy, not by physics alone.
* An electrothermal fixed point with per-regulator local temperature is required at kilowatt scale; a single global T_max is not adequate.
* The mechanical thickness response opposes the electrical one, with a sign that is stable across 20 combinations of assembly model, stress-free reference and thermal boundary.
* NEGATIVE RESULT: footprint opposition does not exist in a mounted assembly. It is positive only in the unmounted and clamped idealisations and negative on all five explicit boards, in the direction the reference paper itself asserts.
* NEGATIVE RESULT: a compact clamped foundation is not a substitute for an explicit board. It sits in the opposite regime and cannot reproduce its own free limit.

### Claims that must not be made

* That mechanics binds, constrains, or restricts the feasible design set. No admissible criterion exists.
* That footprint is an ETM opposition in a mounted assembly.
* Any absolute mounted warpage value as a prediction.
* Any comparison of the computed warpage against a 'conventional' or 'typical' package limit. No source satisfying the admissibility test has been obtained. The only supportable statement is that simulated mounted INCREMENTAL OPERATIONAL warpage stays below 40 um over the tested envelope; whether that is safe or constraining is UNKNOWN.
* Any board-level conclusion drawn from a BC-A or BC-B result.

<!-- END GENERATED: publication_claims -->

