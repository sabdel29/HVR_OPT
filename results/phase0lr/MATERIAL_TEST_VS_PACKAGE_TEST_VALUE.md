# Material characterisation versus the board-level campaign — value of information

**Phase 0L-R, Part 16.** Before recommending a 272-package board-level campaign, compare what it
buys against a much smaller material-characterisation campaign.

## 1. What each campaign actually resolves

| uncertainty | board-level fatigue campaign | material characterisation |
|---|---|---|
| absolute life constant for THIS package | **resolves directly** | no |
| which life law (strain vs energy) | **resolves** (that is what D measures) | no |
| creep law valid in the package's own stress regime | **no** | **resolves** |
| creep data on the right alloy | **no** | **resolves** |
| plasticity above 122 °C | **no** | **resolves** |
| the simulation-uncertainty floor that sets the specimen count | **no** | **resolves** |

The board-level campaign measures the package's *response to* a material model it cannot check.
The material campaign checks the model. They are not substitutes, but they are not equal in
order either.

## 2. The decisive number: the specimen count is set by simulation uncertainty, not scatter

The required specimens per cell solve
\(Z = \sum_c \ln(\text{effect}_c) / \sqrt{2/(\beta^2 n) + \sigma_{sim}^2} / \sqrt{2} \ge 3\).
The Weibull term falls as \(1/n\); the simulation term \(\sigma_{sim}\) does not fall at all.

With the corrected model's effect sizes (1.1507 and 1.1803 at the two profiles) and the worst
observed \(\beta = 5.1\):

| σ_sim (architecture) | ceiling on Z | n per cell | total packages |
|---|---|---|---|
| **0.06 — today** | 3.61 | **48** | **192** |
| 0.05 | 4.33 | 29 | 116 |
| 0.04 | 5.41 | 22 | 88 |
| 0.03 | 7.22 | **18** | **72** |
| 0.02 | 10.82 | 16 | 64 |
| 0.01 | 21.65 | 16 | 64 |

Data: `sample_count_vs_simulation_uncertainty.csv`.

Today the ceiling on Z is 3.61 against a target of 3.0. The campaign is being designed with
almost no margin, and the margin is consumed by simulation uncertainty that more boards cannot
reduce. **Halving σ_sim from 0.06 to 0.03 removes 120 packages from the campaign** and saturates
near 16 per cell, which is the irreducible Weibull-scatter floor.

That is the value-of-information argument in one line: **material characterisation is on the
critical path of the board-level campaign's own cost.**

## 3. What a material campaign would need

Not designed in detail here, because the brief says not to. Scope only:

| axis | target |
|---|---|
| alloy | SAC305, one lot, microstructure and aging recorded |
| temperature | 50, 80, 110, 150 °C — spanning both candidate profiles and the operating baseline |
| stress | 15–100 MPa, i.e. the regime carrying 99.8 % of the package's damage |
| tests | steady-state creep at several stresses per temperature; stress relaxation from a strained state; constant-strain-rate tensile at 10⁻⁵, 10⁻⁴, 10⁻³ /s |
| coupons | of order 10–30 specimens total, counting repeats |

Stress relaxation is worth singling out. The joint's own damage is deposited in two brief stress
spikes at the thermal transitions and then relaxes (FIG-0LR-A), so a relaxation test reproduces
the loading path the package actually follows far more closely than a constant-load creep test
does.

## 4. The answer to the question as posed

> Would 10–30 coupon/material tests close more uncertainty than 272 complete packages?

**Yes.** On the evidence assembled in this phase:

- 99.8 % of the package's damage is generated outside the creep calibration window, and the
  creep data is for the wrong alloy. No number of boards changes either fact.
- The board campaign's own specimen count is dominated by a simulation-uncertainty floor that
  only material data can lower, and lowering it would cut the campaign by roughly 60 %.
- The board campaign's headline output — an absolute life constant — is only meaningful once the
  constitutive model that generates the response metric is trustworthy in the regime where it is
  evaluated. Calibrating a fatigue constant on top of an extrapolated constitutive model buries
  the constitutive error inside the fitted constant, where it cannot later be separated.

That last point is the strongest one, and it is a sequencing argument rather than a cost
argument: **running the board campaign first does not merely under-inform, it actively
contaminates the constant it is run to obtain.**

## 5. Recommendation

**MATERIAL CHARACTERISATION FIRST**, with **primary-paper acquisition in parallel** because it is
nearly free and may supply part of the same information (Part 6 lists four P0 papers, two of them
open-access documents that a browser can fetch in one click).

The board-level campaign is not cancelled. It is re-sequenced to follow the constitutive closure,
at which point its own specimen count is expected to fall from 48–68 per cell toward the Weibull
floor near 16.
