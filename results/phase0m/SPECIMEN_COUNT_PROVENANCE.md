# PHASE 0M PART 0-D --- SPECIMEN-COUNT PROVENANCE

**Authoritative.** Four specimen counts are live in this repository. They are not competing
estimates of one quantity; each answers a different question and three of the four are not the
current design. Any document quoting a specimen count must name which row it means.

| Phase | n / cell | cells | packages | status | model | solver control | D | energy metric |
|---|---|---|---|---|---|---|---|---|
| 0K-R | **34** | 4 | **136** | HISTORICAL | `M0_COARSE` | DEFAULT (dt0=1e-5, dtmax=10 s) | 1.4395 | DEFECT #46 present (inflated ~18.5 %) |
| 0L | **68** | 4 | **272** | HISTORICAL | `M1_NHI (worst case across admitted models)` | TIGHT (dt0=1e-8, dtmax=10 s) | 1.4001 | DEFECT #46 present (inflated ~18.5 %) |
| 0L-R | **48** | 4 | **192** | CURRENT / CONDITIONAL | `M1 (the selected model)` | TIGHT (dt0=1e-8, dtmax=10 s) | 1.7256 | DEFECT #46 fixed; Phase-0M ME route agrees to 0.80 % |
| 0L-R counterfactual | **16** | 4 | **64** | NUMERICS-ONLY COUNTERFACTUAL | `M0_COARSE (the INCUMBENT physics)` | TIGHT (dt0=1e-8, dtmax=10 s) | 1.7174 | DEFECT #46 fixed |

## What each row answers

**0K-R --- HISTORICAL.** How many packages does a Z1-vs-Z2 discrimination need, at the solver settings and constitutive model Phase 0K-R actually ran?

* Superseded by: 0L; the solver settings were under-integrated
* Evidence: `results/phase0kr/PHASE0KR_EXPERIMENTAL_CLOSURE.md, results/phase0l/method_reproduction_check.csv`

**0L --- HISTORICAL.** What is the WORST-CASE requirement across every constitutive model admitted after the Phase-0L constitutive audit?

* Superseded by: 0L-R; a worst-case envelope over models is not a design point, and the energy metric it used was inflated
* Evidence: `results/phase0l/PHASE0L_HIGH_STRESS_CONSTITUTIVE_GATE.md Sec. 6`

**0L-R --- CURRENT / CONDITIONAL.** How many packages does the SELECTED model require at corrected solver settings and a corrected energy integral?

* Superseded by: -- current, but CONDITIONAL: not to be frozen while the constitutive extrapolation dominates the uncertainty budget
* Evidence: `results/phase0lr/PHASE0LR_CONSTITUTIVE_AND_REPORT_CLOSURE.md Sec. 6, results/phase0lr/sample_count_vs_simulation_uncertainty.csv`

**0L-R counterfactual --- NUMERICS-ONLY COUNTERFACTUAL.** What would Phase 0K-R's own model have required if ONLY the numerics were corrected and the physics left untouched?

* Superseded by: -- not a design; it exists to separate the numerical correction from the constitutive one
* Evidence: `results/phase0lr/numerics_vs_constitutive_decomposition.csv`

## The one-line summary

* **Current conditional estimate: 48 per cell, 192 packages** (Phase 0L-R, model M1, corrected
  solver control, DEFECT #46 fixed). CONDITIONAL, and explicitly **not frozen**.
* **34 / 136** is HISTORICAL (Phase 0K-R). It is reproducible at the settings it used and is
  not the current design.
* **68 / 272** is HISTORICAL (Phase 0L). It is a worst-case envelope across models, not a
  design point, and it was computed on an inflated energy metric.
* **16 / 64** is a COUNTERFACTUAL. It isolates the numerical correction from the constitutive
  one and is not a design.

## Why the current number moved, decomposed

The requirement moved for two independent reasons and the brief requires them separated:

| step | change | n / cell | cause |
|---|---|---|---|
| Phase-0K-R design | -- | 34 | baseline |
| correct the integration only | D 1.4395 -> 1.7174 | 34 -> 16 | **NUMERICS.** Same physics. |
| then correct the constitutive model | D 1.7174 -> 1.7256 | 16 -> 48 | **PHYSICS.** |

D moves **+19.3 %** from integration control and **+0.5 %** from the constitutive model, so the
discrimination ratio itself is overwhelmingly a numerics story. The specimen count is not: it
falls to 16 on numerics and then rises to 48 on the model, because n depends on the spread in
`w/eps` across the two test cells and not on D at a single cell.

## The count is not the binding term

The ceiling on the discrimination index is **Z = 3.61 against a target of 3.0**, and that
ceiling is set by the **simulation-uncertainty floor**, not by the specimen count. Halving the
simulation uncertainty (0.06 -> 0.03 per-architecture standard error) cuts the campaign from
192 packages to 72. No number of boards can lower the floor. See
`results/phase0lr/sample_count_vs_simulation_uncertainty.csv` and
`results/phase0lr/MATERIAL_TEST_VS_PACKAGE_TEST_VALUE.md`.
