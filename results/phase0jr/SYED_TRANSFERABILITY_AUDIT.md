# Phase 0J-R Sec. 9/19/20 — Is Syed 2004 admissible, and for what?

## Classification

> **ADMISSIBLE FOR RELATIVE LIFE ONLY.**
> Absolute life is **CONDITIONALLY TRANSFERABLE** and is **not** reported as validated.

## The ten Phase-0J criteria, re-evaluated against the primary source

| # | criterion | verdict | evidence from the primary |
|---|---|---|---|
| 1 | alloy SAC305 or transferable | **PARTIAL** | Syed's balls are **4.0Ag0.5Cu / 3.9Ag0.5Cu** (SAC405/395); ours is **SAC305**. Same alloy family, different Ag content. Schubert's is SAC387. No SAC305-specific calibration exists in any supplied source. |
| 2 | metric reproducible by our solver | **PASS** | M4 ≡ Δ(PEEQ) proven by probe; M5 ≡ the inelastic work integral |
| 3 | metric definition unambiguous | **PASS** | now fully specified: accumulated **creep** strain, volume-averaged over 25 µm layers at both faces, two elements each |
| 4 | loading regime overlaps | **PASS on ΔT/dwell, PARTIAL on T range** | ours 25→83 °C, ΔT 58 K, **300 s dwell**; his TC3 is 0→100 °C with **5 min dwells**. Dwell matches TC3 exactly; our ΔT is smaller and our T_min much warmer. |
| 5 | joint type relevant | **PASS** | board-level BGA solder ball, SMD pad, 0.4–0.76 mm ball — ours is a 400 µm ball at 800 µm pitch, inside his range |
| 6 | defined endpoint | **PASS** | 300 Ω with confirmation; **mean** life |
| 7 | coefficients available | **PASS** | author-corrected `C' = 0.0468`, `W' = 0.0015` |
| 8 | units reconcilable | **PASS** | strain dimensionless; energy MJ/m³ = MPa, and our M5 = 1.09 sits inside his 0.066–2.42 |
| 9 | source experimental | **PASS** | 12 calibration points + 4-configuration independent validation, all measured |
| 10 | no undocumented conversion | **PASS for relative, FAIL for absolute** | see below |

**Nine of ten pass or partially pass.** Phase 0J scored this candidate 5/10 and could not test
criteria 3, 7 or 10 at all. **The Phase-0J score was limited by access, exactly as its verdict
said.**

## Sec. 8 reproduction — passed, on tolerances declared in advance

Declared before the arithmetic: (a) reproduce the paper's ±25 % claim from its own Table 3;
(b) the two **independently fitted** constants must recover a mutually consistent effective
stress `w_acc/ε_acc` to within 10 % on the independent validation package.

| test | result |
|---|---|
| (a) worst prediction error on Table 3 | **11.7 %** — inside ±25 % ✔ |
| (b) `w/ε` recovered from `C'` and `W'` across 4 configurations | **28.78, 29.85, 28.99, 30.02 MPa — spread 4.2 %** ✔ |
| same test on the hyperbolic-sine pair | 24.16–26.32 MPa, spread 8.6 % ✔ |

Test (b) is **not circular**: `C'` and `W'` were regressed separately against 12 points, and
nothing forces them to agree on a package that was not in that set. They do. The published
constants are internally consistent and correctly transcribed. **No digitisation was used** —
every number is a printed table value.

## Where our joint sits — the one thing that fails

| quantity | Syed's calibration | **ours** | verdict |
|---|---|---|---|
| mean life | 275 – 10 027 cycles | 2388 – 3206 (predicted) | **INTERPOLATION** |
| ε_acc | 0.00213 – 0.0777 | **0.00666 – 0.00895** | **INTERPOLATION** |
| w_acc | 0.0665 – 2.424 MPa | **0.905 – 1.110** | **INTERPOLATION** |
| **w_acc / ε_acc** | **28.8 – 30.0 MPa** | **124 – 136 MPa** | **OUTSIDE by 4.3×** |

Each metric individually lands comfortably inside the calibrated domain. **The pair does not.**
Our joint dissipates about four times more creep energy per unit creep strain than any package
Syed calibrated on, which is a direct statement that it operates at roughly four times his
effective stress. Nothing is hidden by this: it is the reason the two Syed models, which agree
with each other on his own data, disagree by **4.1×** on ours.

| | Z1 | Z2 | Z4 |
|---|---|---|---|
| `N_f` from Eq. 14 (strain) | 2499 | 3206 | 2388 |
| `N_f` from Eq. 15 (energy) | **610** | **736** | **601** |
| ratio between the two models | **4.10×** | 4.36× | 3.97× |

On Syed's own validation package the same two equations agree to **4–7 %**. On ours they differ
by a factor of four. **That is the quantitative signature of being off the calibration locus,
and it is why absolute life is not reported as validated.**

## What IS defensible

**The relative life.** Both Syed models, and both Schubert models, agree:

| law | Z2/Z1 | Z4/Z1 |
|---|---|---|
| Syed corrected, strain (Eq. 14) | **1.283** | 0.956 |
| Syed corrected, energy (Eq. 15) | **1.206** | 0.984 |
| Syed corrected, sinh strain (Eq. 16) | 1.283 | 0.956 |
| Schubert SnAgCu strain (slope 1.3) | **1.383** | 0.943 |
| Schubert SnAgCu energy (slope 1.0) | 1.206 | 0.984 |

**Z2/Z1 = 1.21 – 1.38 across four independent primary-source formulations, two authors and two
alloy variants. Ranking Z2 > Z1 > Z4 in every one.** The reasons the relative figure survives
what the absolute figure does not:

* the constant `C'` cancels exactly in a ratio;
* the strain exponent is −1 in Syed and −1.3 in Schubert, so the *spread* of the ratio is
  bounded by that exponent range rather than by an unknown;
* the alloy, joint geometry, extraction volume, failure definition and cycle are **identical
  between our three architectures**, so those transfer errors are common-mode and cancel;
* Darveaux 2000 states the same principle from the other side: *"Since the slopes are consistent
  (K4 = 1.04 to 1.05), relative fatigue life predictions should be somewhat independent of the
  averaging scheme chosen."*

## The Phase-0J relative figure is superseded

Phase 0J reported **Z2/Z1 = 1.558** from the Phase-0I core-averaged M1 on the uniform mesh.
Matching Syed's 25 µm extraction changes the metric by 22–60 %, **and by different amounts per
architecture**, moving the ratio to **1.283**. Z4/Z1 moves from 0.890 to 0.956.

> The Phase-0J value was an **ALGEBRAIC RATIO** on an unmatched volume.
> **1.283 is a TRANSFER-VALIDATED RELATIVE-LIFE RATIO**, on the source's own extraction.
> They must never be quoted interchangeably, and the earlier one is withdrawn.

## Uncertainty on the relative ratio

| contributor | effect on Z2/Z1 |
|---|---|
| life-law constant `C'` or `W'` | **0 — cancels exactly** |
| Syed original vs corrected constants | **0 — cancels exactly** |
| mesh (n_mid 6 → 10) | 0.2 % |
| stabilised-cycle choice | < 0.6 % |
| dwell, 30 s → 900 s | **1.266 – 1.320, i.e. ±2 %** |
| law family (Syed strain / energy / Schubert) | **1.206 – 1.383, i.e. −6 % / +8 %** |
| **combined range** | **1.21 – 1.38** |

Absolute life carries, on top of all of this, the **4.1× model-form disagreement** and the
**4.3× off-locus** flag, and is therefore quoted only as conditional.
