# Phase 0L-R — constitutive robustness, report propagation and auditor-dossier closure

## Verdict: **C. Z2 > Z1 ORDERING ROBUST — RELATIVE-LIFE MAGNITUDE REMAINS CONDITIONAL**

Chosen from the closed list in the brief, Part 27. Section 9 records why each alternative
was rejected. The dominant blocker, stated in prose alongside the verdict as the brief
permits: **primary-data access, then material characterisation.**

## 1. What survives the unresolved high-stress uncertainty

The **ordering** survives: all 12 architecture ratios across every integrable constitutive model, every response metric and every profile exceed unity, the smallest being **1.1493**.

It survives for a **structural** reason, not because the replay happened to agree. The ordering originates in the GLOBAL linear-thermoelastic model, which imposes a **32 % larger corner shear on Z1** (2.7486 μm against 2.0796 μm) and contains no solder constitutive law at all. Stated without overreach (revised in Phase 0M Part 0-E): the global package supplies a constitutive-law-independent deformation driver favoring Z2, and every presently testable constitutive/life-law combination preserves that ordering. The local model only compresses that 1.322 to 1.197.

The **magnitude** does not survive as a validated number. The strain-family envelope at the operating baseline is **1.19 to 1.22**; including the energy family widens it to 1.15–1.30, and the energy family is ranking-only (Part 13). The permitted wording is **conditional relative-life envelope**.

## 2. Numerics versus physics — the decomposition

| quantity | change from NUMERICS alone | change from the CONSTITUTIVE model alone |
|---|---|---|
| D (law discrimination) | **+16.5 %** | −0.2 % |
| Z2/Z1 strain ratio | +0.2 % | **−6.5 %** |
| Z2/Z1 energy ratio | +5.5 % | −3.4 % |
| strain metric magnitude | +0.3 % | **+32.2 %** |
| energy metric magnitude | **+17.8 %** | +10.5 % |
| specimens per cell | 34 → 16 | 16 → 48 |

Of the move in D from the Phase-0K-R value of 1.4395, **102 % is energy-integration resolution and −2 % is the material model**. D is a numerics story; the architecture ratio is a physics story. They were conflated before this phase and are separated now.

A third correction was found during the audit and is larger than either: **DEFECT #46**, a step-boundary temperature aliasing bug that inflated every inelastic-energy number by 18.5 %.

The decomposition table above was computed BEFORE that fix, from runs in which both arms carried the bug equally, so the attribution between numerics and physics is unaffected while the absolute levels are not. Recomputed after the fix, D is **1.7174** for the incumbent model and **1.7256** for the corrected one — a constitutive effect of **+0.5 %**, against +16.5 % from integration control. The conclusion is unchanged and slightly strengthened: **D is a numerics story.**

## 3. Where the damage actually is

| damage-weighted σ_vm | Z1 | Z2 |
|---|---|---|
| p10 | 35.9 | 33.2 |
| p25 | 60.0 | 53.1 |
| **median** | 81.9 | 80.6 |
| p75 | 110.3 | 109.0 |
| p90 | 144.9 | 143.4 |
| p95 | 173.6 | 170.4 |
| max | 184.2 | 183.5 |

Only **0.22 %** (Z1) and **0.18 %** (Z2) of per-cycle damage is generated inside the 7.51–15.92 MPa calibration window.

**This corrects Phase 0L.** Phase 0L reported medians of 78 and 72 MPa and concluded the architectures 'do not extrapolate identically'. Weighted properly, element by element, they are **81.9** and **80.6 MPa — 1.5 % apart**. They occupy nearly the same extrapolation region. What differs is the peak: 151.6 MPa against 128.7, and 8.3 % of the cycle above 100 MPa against 5.5 %.

## 4. The predeclared model-form gate

> **INSUFFICIENT EVIDENCE**

Reason: only 2 distinct model FAMILIES could be parameterised AND integrated over the package stress range; the gate requires three. M1_NLO/M1_NHI are parametric perturbations of the Norton family, not a second form, and the gate says so explicitly.

The gate was frozen and hashed before any ratio under a second family existed. It fires on the family count, not on the spread, and that is deliberate: declaring model-form robustness from one family plus perturbations of its own exponent would test the parameters and report on the form.

Recorded outside the gate, as evidence rather than as a gate result: the two families that could both be integrated agree on the strain ratio to **0.2 %** (1.2000 against 1.2024).

## 5. Why only two families

**The Anand family is re-admitted.** Phase 0L rejected it on the Yuan 2023 EINN+BI parameter set, which misses the only available creep data by a median factor of 1240 and appeared to have no solution above 60–80 MPa. An open-access source retrieved in this phase (Yamin et al. 2025) supplies a different Anand set for SAC305, fitted to the *same* Motalab data, which reproduces published SAC305 tensile behaviour and, extrapolated four to six decades down in rate, lands within a median factor of **1.76** of the creep measurements. Both failures were properties of the parameter set, not of the form.

**But it cannot be integrated at package stresses.** Reducing Anand to the Norton form CalculiX can integrate gives n = 12–19 over the package's own stress window, and this solver has an **integrability ceiling at n ≈ 9–10**: swept deliberately, the joint converges at n = 8.13 and 8.97 and fails at n = 10.04 and 11.86. The Anand family can only be run through a low-stress reduction, which is why the model-form question cannot be settled by replay.

## 6. Experiment

| model | D | n per cell | packages |
|---|---|---|---|
| `M0_COARSE` | 1.7174 | 15 | 60 |
| `M1` | 1.7256 | 48 | 192 |

Current provisional requirement **48 per cell, 192 packages** — but the count must not be frozen. The binding term is the **simulation-uncertainty floor**: the ceiling on the discrimination Z-score is 3.61 against a target of 3.0, and halving that floor takes the campaign from 48 per cell to 18. No number of boards reduces it.

**DEFECT #45** records the consequence: fitting an absolute-life constant on top of an extrapolated constitutive model buries the constitutive error inside the fitted constant. Running the boards first does not merely under-inform, it contaminates the quantity it is run to obtain. The campaign is **re-sequenced behind material characterisation, not cancelled**.

## 7. Literature outcome

> **B. HIGH-STRESS SAC305 DATA IDENTIFIED BUT ACCESS-GATED — USER PDF ACQUISITION REQUIRED.**

632 works screened on axes other than the word *creep*. Four P0 and five P1 primary sources identified behind institutional access, two of them reported OPEN by Unpaywall but refused to scripted fetches. One retrieval already changed the phase result. See `HIGH_STRESS_PAPER_DOWNLOAD_REQUEST.md`.

## 8. Report propagation

**DEFECT #44 CONFIRMED.** 21 stale current-facing claims across the two reports. In the historical report they cluster in three generated blocks, chief among them an Executive Summary that contained **no mention of Phase 0L at all**. In the standalone report the worst is an internal contradiction: §17.4 said 68 specimens per cell and §23.1 said 34.

Both are repaired at source. The hostile review of the standalone report (`STANDALONE_REPORT_TECHNICAL_AUDIT.md`) examined 17 items: 8 correct, 5 wrong or superseded, 2 incomplete, 2 missing.

## 9. Why not the other verdicts

| option | why rejected |
|---|---|
| A — model closed, magnitude validated | no SAC305 data exists in the creep-rate regime; 99.8 % of damage is still extrapolated |
| B — model improved, magnitude narrowed | the envelope did not narrow. A second family was admitted, but it cannot be integrated at package stresses, and the predeclared gate fires INSUFFICIENT EVIDENCE |
| D — ordering itself model-form dependent | refuted. No admissible model reverses it, and the driver sits upstream of the constitutive model entirely |
| E — direct material characterisation required before quantification | true of the MAGNITUDE and recommended in Part 16, but it understates what is already established: the ordering is robust for a structural reason and is quantified |
| F — primary data access required before closure | true, and named as the dominant blocker in the verdict prose. As the headline it would describe only the constitutive half of the phase and omit the reliability conclusion, which C carries |

## 10. Artifacts

- `results/phase0lr/alloy_transferability_matrix.csv`
- `results/phase0lr/anand_family_replay.csv`
- `results/phase0lr/damage_weighted_stress_distribution.csv`
- `results/phase0lr/defect44_hits.csv`
- `results/phase0lr/energy_integration_convergence.csv`
- `results/phase0lr/high_stress_damage_fraction.csv`
- `results/phase0lr/model_form_gate_result.csv`
- `results/phase0lr/model_form_robustness.csv`
- `results/phase0lr/numerics_vs_constitutive_decomposition.csv`
- `results/phase0lr/package_replay_defect46_fixed.csv`
- `results/phase0lr/sample_count_vs_simulation_uncertainty.csv`
- `results/phase0lr/z1_z2_cycle_histories.csv`
- `results/phase0lr/ALLOY_TRANSFERABILITY_MATRIX.md`
- `results/phase0lr/BASELINE.md`
- `results/phase0lr/DEFECT44_REPORT_PROPAGATION_AUDIT.md`
- `results/phase0lr/ENERGY_INTEGRATION_AUDIT.md`
- `results/phase0lr/HIGH_STRESS_PAPER_DOWNLOAD_REQUEST.md`
- `results/phase0lr/LIFE_LAW_STATUS_AFTER_PHASE0L.md`
- `results/phase0lr/M1_IMPLEMENTATION_AUDIT.md`
- `results/phase0lr/MATERIAL_TEST_VS_PACKAGE_TEST_VALUE.md`
- `results/phase0lr/PART10_PREDECLARED_ROBUSTNESS_GATE.md`
- `results/phase0lr/STANDALONE_REPORT_TECHNICAL_AUDIT.md`
- `results/phase0lr/Z1_Z2_MECHANISM_AUDIT.md`
- `results/phase0lr/FIG_0LR_A_histories.png`
- `results/phase0lr/FIG_0LR_B_damage_bins.png`
- `results/phase0lr/FIG_0LR_C_domain.png`
- `results/phase0lr/FIG_0LR_D_decomposition.png`
- `results/phase0lr/FIG_0LR_E_ratios.png`
- `results/phase0lr/FIG_0LR_F_provenance.png`
- `results/phase0lr/FIG_0LR_G_ladder.png`
