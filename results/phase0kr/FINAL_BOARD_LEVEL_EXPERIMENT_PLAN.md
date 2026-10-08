# Phase 0K-R Sec. 24 — Final board-level experiment

> **NOT FROZEN.** Acceptance criterion 2 of Sec. 31 — stress inside or defensibly near the
> constitutive calibration domain — **cannot be met by any profile**, and that is a property of
> the package, not of the design. Every other criterion passes. The design below is
> **READY TO EXECUTE with a declared and quantified limitation**, not frozen.
>
> **THIS EXPERIMENT HAS NOT BEEN RUN.** No measurements exist and none are synthesised.

## Acceptance criteria, Sec. 31

| # | criterion | status |
|---|---|---|
| 1 | every profile inside a validated constitutive domain, or source-backed extension | **PASS** — both profiles have `T_min ≥ 45 °C`; **0 %** of damage below the creep floor |
| 2 | stress inside or defensibly near the calibration domain | **FAIL** — damage-weighted median driving overstress 54–91 MPa against a 7.5–16 MPa fit; **unfixable by profile choice** |
| 3 | strain and energy models sufficiently separated | **PASS** — D = 1.4395, 44.0 % separation |
| 4 | sample size adequate under a source-backed β range | **PASS at n = 34**; fails at the Phase-0K n = 16 for Q2 |
| 5 | Z1/Z2 ratio validation has adequate power | **PASS at n = 34** (Z = 3.0 combined at β = 5.1) |
| 6 | failure definition source-aligned | **PASS** — Syed's rule, now exact |
| 7 | censoring and statistics declared | **PASS** |
| 8 | no single-condition claim used to infer model form | **PASS** — two conditions, and the terminology is frozen |

## Test matrix — 4 cells, 136 packages

| cell | architecture | condition | T range | dwell | ramp | n |
|---|---|---|---|---|---|---|
| 1 | **Z1 embedded** | **LOW_WIDE** | **45 → 125 °C** | 5 min each extreme | 3 °C/min | **34** |
| 2 | **Z1 embedded** | **HIGH_NARROW** | **110 → 150 °C** | 5 min each extreme | 3 °C/min | **34** |
| 3 | **Z2 backside** | LOW_WIDE | 45 → 125 °C | 5 min | 3 °C/min | **34** |
| 4 | **Z2 backside** | HIGH_NARROW | 110 → 150 °C | 5 min | 3 °C/min | **34** |

Cycle times: **1.06 h** (LOW_WIDE, 80 K span) and **0.61 h** (HIGH_NARROW, 40 K span).

**Z4 is excluded**, unchanged and rechecked: `w/ε` = 123.2 MPa against Z1's 126.9 gives
D = 1.030 — 3 % of model separation for a 50 % increase in specimen count.

### Why 34 and not 16

The two experimental questions need different sample sizes, and Sec. 15 requires the larger
when one campaign answers both:

| question | effect size | min n at β = 5.1 | n = 16 gives |
|---|---|---|---|
| **Q1 — which life law?** | D = 1.4395 | **10** | Z = 3.41 **ADEQUATE** |
| **Q2 — is Z2/Z1 ≈ 1.2–1.4 real?** | 1.110 (LOW_WIDE), 1.2485 (HIGH_NARROW) | **34** | Z = 2.49 **MARGINAL** |

β = 5.1 is the **observed minimum** across 16 primary SnAgCu/SAC305 cells, not an assumption.

## Predicted behaviour — predictions, not measurements

| cell | `N_f` strain (Eq. 14) | `N_f` energy (Eq. 15) | ratio | days to 63 % |
|---|---|---|---|---|
| Z1 / LOW_WIDE | 1435 | 367 | 3.91 | 16 – 63 |
| Z2 / LOW_WIDE | 1695 | 407 | 4.16 | 18 – 75 |
| Z1 / HIGH_NARROW | 3574 | 1315 | 2.72 | 34 – 91 |
| Z2 / HIGH_NARROW | 4504 | 1642 | 2.74 | 42 – 115 |

**Longest cell: 91–115 days** if the strain family is right, 34–42 if the energy family is.
Cells run in parallel; two chambers, one per condition.

## Test vehicle

| attribute | specification |
|---|---|
| alloy | **SAC305**, ball and paste |
| ball / standoff | **400 µm / 300 µm** |
| pitch | **800 µm** |
| pad | SMD 400 µm, electrolytic NiAu package side, OSP board |
| underfill | **none** — the model has none |
| board | FR-4, 1.6 mm, daisy-chain routed |
| package | Z1 and Z2 z-stacks as modelled (h_sub 1.3 mm and 0.3 mm) |
| nets | ≥ 2 independent daisy chains per package, corner joints isolated |

## Monitoring and failure definition

Syed's rule, verified against the primary and now exact
(`failure_criterion_reaudit.md`):

* in-situ continuity, **sampled every 2 minutes**;
* event threshold **> 300 Ω**;
* failure = first crossing **followed by ten further crossings within 10 % of the time of the
  first**;
* **manual confirmation within one week** of first occurrence;
* intermittent opens count provided the ten-within-10 % rule is met;
* monitoring continues after first failure.

## Statistics

* **2-parameter Weibull per cell by maximum likelihood**, with **β estimated, not assumed**.
* **Right-censoring by MLE**, never exclusion.
* Reported statistic: **mean life** `η·Γ(1 + 1/β)` — the quantity Syed's constants predict —
  with the conversion stated so it is auditable.
* **90 % two-sided profile-likelihood intervals** on η, β and the mean.
* **Stopping rule declared in advance**: each cell runs to 63 % failures or to a pre-agreed
  cycle ceiling, whichever comes first. A cell finishing with fewer than 7 failures reports a
  profile-likelihood interval rather than a point estimate and is downweighted in the
  discrimination test.

## Primary and secondary outputs

**Primary:** the measured life ratio between the two conditions, compared against the two laws'
predictions, which differ by **44.0 %**.
**Secondary:** absolute life for this package; the measured Z2/Z1 ratio at both conditions; an
estimate of β for this package and joint.

## The limitation that travels with the result

The **stress-domain violation is not removed by this experiment design and cannot be.** What the
experiment does is make it irrelevant to the *answer*: a measured life calibrates the law in the
regime this package actually operates in, which is the only way to retire an extrapolation that
no amount of profile selection can avoid.
