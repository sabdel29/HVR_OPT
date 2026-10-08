# Standalone audit report — hostile technical review

**Phase 0L-R, Part 18.** The 59-page current-framework report was read front to back as if by an
external reviewer who did not write the code, and independently of the historical report. Its
66/66 build checks were **not** treated as evidence: those checks verify that the document builds
and that no *known* stale phrase survives, not that its claims match the code.

Each row asks the brief's questions A–J: does the equation match the current code, does the
stated validation match the current evidence, is the alloy named correctly, is the parameter
source correct, is the validation domain stated, is conditional-versus-validated language
correct, are absolute and relative life separated, and are the experiment, G2 and optimizer
statuses current.

## Findings

| # | section | claim as written | evidence | status | required correction |
|---|---|---|---|---|---|
| 1 | §4.2 Source-backed parameters | table row reads **"SAC305 creep points \| 19 points, 45 to 150 °C, 7.51–15.92 MPa"** | the 19 points are Xiao & Armstrong Sn3.9Ag0.6Cu (Phase 0L Part V; `alloy_transferability_matrix.csv`) | **FALSE** | relabel the row "Sn3.9Ag0.6Cu creep points (used as a SAC305 surrogate)" and move it out of the source-backed-for-SAC305 block |
| 2 | §23.1 The board-level experiment | "**34 specimens per cell, 136 packages total**" | superseded inside this very report: §17.4 already states 68 per cell and 272 packages | **FALSE and internally inconsistent** | replace with the current provisional count and mark it provisional |
| 3 | §13.7 Calibration vs operating domain | "damage-weighted **54 to 91 MPa**" | properly weighted element-by-element, Phase 0L-R gets p10–p90 = 33–145 MPa with a median of 81 MPa (`damage_weighted_stress_distribution.csv`) | **SUPERSEDED** | quote the median and the p10–p90 band, and cite the distribution artifact |
| 4 | §17.2 common-mode test | mechanism given as "Z1 sits at 78 MPa and Z2 at 72, so they do not extrapolate identically" | the proper weighting gives 81.85 and 80.63 MPa, 1.5 % apart; the real mechanism is a 15 % lower PEAK and 34 % less time above 100 MPa (`Z1_Z2_MECHANISM_AUDIT.md`) | **FALSE mechanism, correct conclusion** | replace the mechanism; the PARTIAL classification itself stands |
| 5 | §21 Validation matrix | single STATUS column | the brief requires five independent axes, and a model can pass the first two while failing the fourth — which is exactly this model's situation | **INCOMPLETE** | split into NUMERICAL / SOLVER-IMPLEMENTATION / SOURCE-DATA / DOMAIN / LIFE-LAW |
| 6 | §1.4 strongest conclusion | "relative solder-fatigue-life advantage of approximately **1.17 to 1.39**" | correct as a range over all metrics, but it mixes the strain family (converged) with the energy family (not numerically converged, Part 13) | **CONDITIONAL, needs qualification** | quote 1.19–1.22 from the strain family as the defensible envelope and say the energy family is ranking-only |
| 7 | §13.4 constitutive law | states the overstress law and that there is no rate-independent plasticity | matches `incplas.f` and the probe to 1.2e-5 | **CURRENT — correct** | none |
| 8 | §13.5 temperature interpolation | "CalculiX interpolates linearly in A; Arrhenius is refuted" | matches the solver probe | **CURRENT — correct** | none |
| 9 | §13.6 alloy provenance | states Sn3.9Ag0.6Cu plainly | correct | **CURRENT — correct** | none |
| 10 | §13.8 calibration-variable defect | "0 of 19 reproduced" | confirmed by solver probe | **CURRENT — correct** | none |
| 11 | §16 mission and G2 | N_required OPEN, G2 NOT TESTED | unchanged | **CURRENT — correct** | none |
| 12 | §18 toolchain | "no compiled MOOSE solid_mechanics binary"; "Q3D not licensed" | verified again in Phase 0L-R | **CURRENT — correct** | none |
| 13 | §22.1 uncertainty | energy metric moves 11–24 % with solver control | Phase 0L-R measures 28.5 % between the pre-0L and resolved controls, converging to 0.15 % thereafter | **UNDERSTATED** | update with the measured convergence series |
| 14 | §24 current claims | "Z4 is not resolved against Z1" | Z4/Z1 = 0.956–0.970 across models, inside the model-form spread | **CURRENT — correct** | none |
| 15 | §19 code architecture | module and function table | spot-checked against the tree; paths resolve | **CURRENT — correct** | add the Phase-0L-R modules |
| 16 | whole document | no statement anywhere that the **Anand family is now re-admitted** | Phase 0L-R re-admits it on the Yamin parameterisation | **MISSING** | add to §13 and to the uncertainty section |
| 17 | §13 constitutive | no statement of the **solver's integrability ceiling** (n ≈ 9–10) | Phase 0L-R measured it | **MISSING** | add — it bounds which model forms can ever be replayed |

## Summary

**17 items examined, 8 correct as written, 5 wrong or superseded, 2 incomplete, 2 missing.**

The errors cluster in exactly one place: the parts of the report that quote *numbers carried
forward* (§4.2, §23.1, §13.7, §17.2) rather than the parts that describe *what the code does*
(§13.4, §13.5, §13.8, §16, §18). The mechanism sections are sound; the inherited figures are not.

Item 2 is the most serious, because it is an internal contradiction: §17.4 and §23.1 of the same
document give different specimen counts. A reader who read only §23 would take away a number the
same report contradicts fourteen pages earlier. That is the precise failure mode DEFECT #44
describes, occurring *inside* the document written to be free of it.

Item 4 is the most interesting: the conclusion (PARTIAL cancellation) was right, but the
mechanism offered for it was wrong, and the wrong mechanism was more alarming than the truth.
The two architectures occupy nearly the same extrapolation region; what differs is the peak.
