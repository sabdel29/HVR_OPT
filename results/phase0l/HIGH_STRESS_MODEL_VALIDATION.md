# High-stress constitutive model validation

**Phase 0L, Parts VIII–X.** Candidate constitutive forms, whether each reproduces its own
source data, what each predicts at package stresses, and which are admissible.

Artifacts: `results/phase0l/high_stress_model_comparison.csv`,
`scripts/phase0l/candidate_laws.py`, `scripts/phase0l/model_validation.py`.

## 1. Part IX first — what the toolchain can actually integrate

The candidate set is constrained by what can be run, so the capability audit comes first.

| Capability | Status | Evidence |
|---|---|---|
| CalculiX Norton, `ε̇ = A(σ_vm − σ_y)^n t^m` | **available** | `creeps.f:228`; probes confirm to 1e-5 |
| CalculiX Norton with σ_y ≡ 0 | **available** | flat `*PLASTIC` at 1e-6 MPa; TEST A confirms ε̇ = Aσ^n |
| CalculiX `*CREEP, LAW=USER` | **not available as built** | needs a recompile; `creeps.f:217` is the only other branch. gfortran/gcc/make/cmake are present, but **SPOOLES is not installed** and ccx requires it. Not demonstrated, so not claimed |
| CalculiX Anand | **does not exist** | zero occurrences of "anand" in the 2.23 source tree and in the 2.22 manual |
| MOOSE SolidMechanics | **not available** | source tree exists at `/home/beams0/LPOPRYHO/projects/moose/modules/solid_mechanics/` but **no compiled binary**; only `heat_transfer/heat_transfer-opt` is built, and it belongs to another user |
| Python reduction of any law to a Norton card | available | `scripts/phase0l/candidate_laws.py` |

**Consequence.** Every candidate that is to be *run* must be expressible as a Norton card. A
hyperbolic-sine or Anand law can only enter the package simulation through a local power-law
reduction over a stated stress window, and the reduction error must be quantified. Anand cannot
be run at all in its own form.

## 2. Part VIII — the candidate forms

| ID | Form | Constants | Alloy behind it |
|---|---|---|---|
| **M0** AS-BUILT | ε̇ = A(σ_vm − σ_y(ε̄))^n | A, n from the σ_applied fit; σ_y from Chaboche | creep: Sn3.9Ag0.6Cu; yield: SAC305 |
| **M1** NORTON-ZY | ε̇ = A σ_vm^n | same A, n; σ_y → 0 | Sn3.9Ag0.6Cu |
| **M2** GAROFALO-ZY | ε̇ = C₁[sinh(C₂σ)]^C₃ e^(−Q/RT) | Yuan 2023 Table 6, EINN+BI | Sn3.9Ag0.6Cu |
| **M3** ANAND-ZY | Anand steady state, Yuan Eq. (10) | Yuan 2023 Tables 6/7/9, EINN+BI | SAC305 (via Motalab) |

Anand's steady state is used because that is the only part of the Anand model comparable to a
creep law: σ* = (ŝ/ξ)[(ε̇/A)e^(Q/RT)]^n · sinh⁻¹{[(ε̇/A)e^(Q/RT)]^m}, inverted numerically for
ε̇(σ, T).

No further forms were added. Part VII found no evidence for distinct stress regimes in SAC305
that would justify a piecewise Norton law, and the brief forbids adding complexity without
evidence.

## 3. Part X, test 1 — does each candidate reproduce its source data?

The only creep dataset available is the 19 Xiao & Armstrong points (Yuan Table 5).

| Model | reproduced within ×5 | median measured/predicted | worst factor |
|---|---|---|---|
| **M0** AS-BUILT | **0 / 19** | 4.65 × 10⁷ | 1.8 × 10¹² |
| **M1** NORTON-ZY | **19 / 19** | 0.979 | 1.15 |
| **M2** GAROFALO-ZY | **19 / 19** | 0.930 | 2.6 |
| **M3** ANAND-ZY | **0 / 19** | 8.0 × 10⁻⁴ | 3030 |

M0's failure was confirmed independently by solver probe (Part IV, TEST F) — not by arithmetic
alone. M3's failure is a cross-alloy, cross-rate comparison and should be read as such: it is
far larger than an Ag-content difference plausibly explains and is consistent with extrapolating
a set calibrated at 10⁻³–10⁻⁵ s⁻¹ down to 10⁻⁹–10⁻⁷ s⁻¹.

Tests 2–5 of Part X (high-stress SAC305 data, stress relaxation, cyclic response) **could not be
run**: Part VII retrieved no source data in those regimes. This is recorded as a gap, not passed.

## 4. Part X, test 2 — what each candidate does at package stresses

Uniaxial steady-state rate (s⁻¹) at 45 °C:

| σ (MPa) | M0 | M1 | M2 | M3 |
|---|---|---|---|---|
| 20 | 0 | 2.55e−7 | 1.39e−7 | 8.17e−5 |
| 40 | 1.97e−7 | 8.01e−5 | 4.33e−3 | 6.84e−1 |
| 60 | 7.05e−5 | 2.31e−3 | **1.34e+2** | **5.58e+3** |
| 80 | 2.13e−3 | 2.52e−2 | **4.17e+6** | **4.43e+7** |
| 100 | 2.36e−2 | 1.60e−1 | **1.30e+11** | no solution |
| 120 | 1.52e−1 | 7.27e−1 | **4.03e+15** | no solution |

The model-to-model spread at package stresses runs from **10⁶ to 10¹⁶**.

Two candidates fail outright in this regime:

- **M2** is an exponential in σ fitted over 7.5–15.9 MPa. At 120 MPa it predicts 4 × 10¹⁵ s⁻¹.
  That is not a large number, it is a meaningless one — no solid deforms at 10¹⁵ strain per
  second. The local exponent it implies at 60 MPa is C₃C₂σ·coth(C₂σ) ≈ 31.
- **M3** saturates. σ*(ε̇) grows only logarithmically in ε̇, so above roughly 60–80 MPa the
  model has **no solution at any rate** — it cannot represent those stresses.

## 5. Classification

| Model | Class | Reason |
|---|---|---|
| **M0** AS-BUILT | **REJECTED** | Cannot reproduce its own calibration data: 0 of 19, with 16 points giving identically zero. Its driving variable is not the variable it was fitted in (DEFECT #40) |
| **M1** NORTON-ZY | **CONDITIONALLY ADMISSIBLE** | Reproduces all 19 source points (worst 1.15×) and is exactly integrable by the solver. Conditions: (i) the source alloy is Sn3.9Ag0.6Cu, not SAC305, with no transferability evidence; (ii) it is evaluated 3.4–7.2× above its fitted stress window |
| **M2** GAROFALO-ZY | **REJECTED above ~40 MPa** (conditionally admissible below) | Reproduces the source data, but its extrapolation to package stresses is unphysical |
| **M3** ANAND-ZY | **REJECTED for this application** | Fails the only available creep data by 10³, and has no solution above ~60–80 MPa. Its own source data was not retrievable, so it cannot be validated on its own terms either |

**Exactly one model survives as a basis for the package replay: M1, and only conditionally.**

Because a single admissible model form cannot exhibit model-form spread, the Part XI replay
adds a *parametric* band around M1 taken from the source regression's own uncertainty:
M1_NLO and M1_NHI use n ∓ 2·SE(n), with A re-anchored so the rate at the 10 MPa window centre
is unchanged. The regression standard errors are SE(n) = 0.552 / 0.473 / 0.200 / 0.221 at
45 / 80 / 115 / 150 °C (mean band ±9.8 % on n), which is 0.09× to 11× on rate at 90 MPa. This
is an honest statement of what the 19 points constrain — it is **not** a substitute for the
model-form spread, which Part VII shows cannot be bounded from available data.
