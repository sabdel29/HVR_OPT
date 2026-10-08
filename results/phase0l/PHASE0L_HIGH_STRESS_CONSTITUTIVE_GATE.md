# Phase 0L --- high-stress SAC305 constitutive gate

## Verdict: **C. HIGH-STRESS MODEL-FORM UNCERTAINTY PRESENT BUT Z2/Z1 RANKING SURVIVES**

Chosen from the closed list in the Phase-0L brief, Part XV. The rejected options and the reason each was rejected are in section 8 below.

## 1. DEFECT #40 --- CONFIRMED

The creep card was fitted against **total applied stress**; CalculiX drives the creep law with the **overstress** \(\sigma_{vm} - \sigma_y\). These are different independent variables, so the defect is confirmed.

The consequence is not a bias but a contradiction: the overstress is **non-positive at 16 of the 19 calibration points**, so in the solver's own variable the calibration experiment lies entirely inside the elastic domain. Fed back through the solver the card reproduces **0 of 19** of its own source points.

## 2. What the solver actually integrates

From `src/incplas.f` lines 310, 599 and 605, confirmed against the binary over 7603 single-element increments:

```
  eps_dot_in = A(T) * ( sigma_vm - sigma_y(eps_in) ) ** n(T)
  eps_dot_in = 0            identically, whenever sigma_vm <= sigma_y
```

Median relative error of that form against the solver: **1.2e-5**. The manual's stated form, A*sigma^n on the full von Mises stress, is wrong by a median factor of **14.4** and by up to **1.8e6**. There is **no rate-independent plastic strain** in a `*VISCO` step; `m = 0`, so there is no time hardening; and the temperature interpolation is **linear in A**, not Arrhenius.

## 3. Provenance --- DEFECT #41

The 19 creep points are **Yuan 2023 Table 5**, not "Table 26" (the paper has eleven tables). Yuan section 4.1 sources them to Xiao & Armstrong 2005, whose alloy is **Sn3.9Ag0.6Cu, not SAC305**. The yield half of the card is SAC305 but two model layers from measurement. The two halves of one card are different alloys, and the overstress formulation subtracts one from the other. No transferability evidence exists (344 works screened).

## 4. Admissible models

| model | source-data reproduction | class |
|---|---|---|
| M0 AS-BUILT (Norton on overstress) | **0 of 19** | **REJECTED** |
| M1 NORTON-ZY (yield removed) | **19 of 19**, worst 1.15x | CONDITIONALLY ADMISSIBLE |
| M2 GAROFALO-ZY | 19 of 19, worst 2.6x | REJECTED above ~40 MPa (4e15 1/s at 120 MPa) |
| M3 ANAND-ZY (SAC305) | **0 of 19**, median 1240x too fast | REJECTED for this regime |

Only M1 survives, and only conditionally: wrong alloy, and evaluated 3.4x to 7.2x above its fitted stress window. The replay therefore adds a **parametric** band from the source regression's own uncertainty, n +/- 2 SE, which is +/-9.8 % on n and 0.09x to 11x on rate at 90 MPa.

## 5. Part XII --- common-mode cancellation, tested not assumed

Tolerance predeclared and hashed before any ratio under an alternative model existed (`PART12_PREDECLARED_TOLERANCE.md`, sha256 `fc19abf7...`): ROBUST at S <= 0.0525, PARTIAL at S <= 0.21, both requiring every ratio above 1.

| quantity | min | median | max | S | classification |
|---|---|---|---|---|---|
| Syed2004 Eq14 strain | 1.1887 | 1.2184 | 1.2875 | **0.0811** | PARTIAL CANCELLATION |
| Schubert2003 strain | 1.2520 | 1.2928 | 1.3889 | **0.1059** | PARTIAL CANCELLATION |
| Syed2004 Eq15 energy | 1.1710 | 1.2735 | 1.3017 | **0.1026** | PARTIAL CANCELLATION |
| Schubert2003 energy | 1.1710 | 1.2735 | 1.3017 | **0.1026** | PARTIAL CANCELLATION |

> **PARTIAL CANCELLATION** at the operating baseline, worst quantity `Schubert2003_strain`, S = 0.1059.

**The ranking survives** --- every admitted model, every admitted law, every profile puts Z2 ahead of Z1. **The magnitude does not** --- the spread is a substantial fraction of the architecture effect itself. The Phase-0K-R claim that the extrapolation "is common mode and cancels in a ratio" is **withdrawn** and replaced by the measured figure.

Revised Z2/Z1 relative life: **1.17 to 1.39** (was 1.21 to 1.38).

## 6. Part XIII --- the experiment does not survive unchanged

| model | D | n per cell for Z = 3 | packages |
|---|---|---|---|
| `M0_COARSE` | 1.6774 | 16 | 64 |
| `M0_FINE` | 1.6548 | 15 | 60 |
| `M1` | 1.6733 | 48 | 192 |
| `M1_NHI` | 1.4001 | 68 | 272 |
| `M1_NLO` | 1.9837 | 40 | 160 |

Three statements, deliberately separated:

1. **The method is verified.** At the solver settings Phase 0K-R actually used, the incumbent model reproduces its design exactly: D = 1.4395 and n = 34 (`method_reproduction_check.csv`).
2. **A numerical correction comes first.** At the corrected solver settings the *same* incumbent model gives D = 1.6774 and n = 16, with no change of physics. Phase 0K-R's inelastic-energy metric was under-integrated, so its w/eps and hence its D were biased.
3. **A constitutive correction on top.** Across the admitted models the requirement spans 15 to 68 per cell; the design value is the worst case, **n = 68, 272 packages**.

The binding term is the simulation-uncertainty floor rather than the specimen count. **The 34-per-cell design does not survive; the experiment stays unfrozen.**

## 7. Part XIV --- the whole constitutive domain, not just creep

| profile | severely extrapolated quantities |
|---|---|
| OP_BASELINE | 5 of 7: E(T) elastic modulus; nu Poisson ratio; CTE alpha(T); A(T), n(T) creep; A(T), n(T) creep -- STRESS domain |
| EXP_45_125 | 4 of 7: E(T) elastic modulus; nu Poisson ratio; CTE alpha(T); A(T), n(T) creep -- STRESS domain |
| EXP_110_150 | 6 of 7: E(T) elastic modulus; nu Poisson ratio; CTE alpha(T); sigma_0(T) yield; C(T), gamma(T) hardening; A(T), n(T) creep -- STRESS domain |

No profile is within domain for the complete material card. E(T)'s slope, Poisson ratio and CTE have no sourced temperature dependence at all, and the creep stress window is violated by every profile including the operating baseline.

## 8. Why not the other verdicts

| option | why rejected |
|---|---|
| A --- model validated, result confirmed | the card fails its own source-data test, 0 of 19 |
| B --- law corrected, result survives | the law WAS corrected, but the correction does not close the high-stress problem: the extrapolation and the alloy mismatch both remain |
| D --- magnitude changes, ranking survives | true but incomplete; it names the symptom and not the cause. The magnitude moved *because* model-form uncertainty is present, which is what C says |
| E --- claim not robust | refuted: no admissible model reverses the ranking, at any profile, under any admitted law |
| F --- data insufficient to close | true as a sub-finding and stated in section 4, but it describes only deliverable A. The phase also answered the ranking question, and C carries both halves |

## 9. Artifacts

- `results/phase0l/calculix_creep_probe.csv`
- `results/phase0l/card_temperature_grid_audit.csv`
- `results/phase0l/common_mode_cancellation_test.csv`
- `results/phase0l/common_mode_verdict.csv`
- `results/phase0l/complete_constitutive_domain.csv`
- `results/phase0l/experiment_reaudit.csv`
- `results/phase0l/high_stress_model_comparison.csv`
- `results/phase0l/high_stress_sac305_sources.csv`
- `results/phase0l/method_reproduction_check.csv`
- `results/phase0l/original_19point_fit.csv`
- `results/phase0l/package_model_replay.csv`
- `results/phase0l/package_model_replay_tight.csv`
- `results/phase0l/refit_comparison.csv`
- `results/phase0l/BASELINE.md`
- `results/phase0l/CALCULIX_CREEP_IMPLEMENTATION_AUDIT.md`
- `results/phase0l/HIGH_STRESS_MODEL_VALIDATION.md`
- `results/phase0l/HIGH_STRESS_SAC305_LITERATURE_AUDIT.md`
- `results/phase0l/ORIGINAL_CREEP_FIT_AUDIT.md`
- `results/phase0l/PART12_PREDECLARED_TOLERANCE.md`
- `results/phase0l/PHASE0L_HIGH_STRESS_CONSTITUTIVE_GATE.md`
