# Phase 0K-R Sec. 4 — The SAC305 constitutive domain, from the material card itself

Not restated from memory. Read out of `scripts/phase0i/solder_model.py` and the primary tables
it cites.

## Creep — the binding constraint

| | |
|---|---|
| source | Yuan 2023, *Materials* 16(14):4922, **Table 26** — 19 measured steady-state points |
| law implemented | `*CREEP, LAW=NORTON`, `ε̇ = A σⁿ tᵐ` with m = 0 |
| **calibration temperatures** | **45, 80, 115, 150 °C** — four, and only four |
| **calibration stress window** | **7.51 – 15.92 MPa** |

| T (°C) | points | stress span (MPa) |
|---|---|---|
| 45 | 4 | 10.54 – 15.92 |
| 80 | 5 | 10.43 – 14.46 |
| 115 | 5 | 8.73 – 12.41 |
| 150 | 5 | 7.51 – 11.52 |

Intermediate temperatures come from Arrhenius interpolation of the rate at σ_ref = 10 MPa with
the exponent interpolated separately. **The Arrhenius form is fitted, not independently
validated**; its only external check is that the implied activation energy (64.4 kJ/mol at
10 MPa) agrees with published values of 62–65.

## Plastic — sourced wider than the creep

| | |
|---|---|
| source | Yuan 2023 **Table 31**, Chaboche fit |
| **calibration temperatures** | **−40, −20, 40, 80, 122 °C** |
| form | bilinear, (σ₀, 0) → (σ₀ + C/γ, 0.02) |

## Elastic and expansion

| | |
|---|---|
| E(25 °C) | 40–50 GPa band sourced (Paska 2024); **45 GPa adopted** |
| dE/dT = −120 MPa/K | **ASSUMPTION** — no temperature dependence found in an accessible source |
| ν = 0.36 | sourced |
| CTE = 21.5 ppm/K | **ASSUMPTION** |

## Extrapolation already present, before any Phase-0K-R change

The card is written at −40, 0, 25, 50, 75, 100, 125 °C. Against the creep calibration:

| card row | creep | plastic |
|---|---|---|
| **−40 °C** | **EXTRAPOLATED** (85 K below the floor) | interpolated |
| **0 °C** | **EXTRAPOLATED** (45 K below) | interpolated |
| **25 °C** | **EXTRAPOLATED** (20 K below) | interpolated |
| 50, 75, 100 °C | interpolated | interpolated |
| 125 °C | interpolated | **EXTRAPOLATED** (3 K above 122) |

> **The 25 °C row is already outside the creep calibration.** Every result this project has
> produced uses a cycle whose cold half sits at 25 °C. The extrapolation the −40 °C proposal
> would introduce is not a new kind of problem — it is a much larger amount of an existing one.

## The stress domain, and why it is the harder constraint

Phase 0J-R proved CalculiX integrates the **overstress** `σ_eq − σ_y(T, PEEQ)`, so the
7.51–15.92 MPa window must be checked on **that** variable, not on `σ_eq`. Damage-weighted by
the solver's own ΔPEEQ increments:

| profile | median driving overstress | p90 | max | damage above 16 MPa |
|---|---|---|---|---|
| OP_BASELINE 25/83 °C | **69.4 MPa** | 149.0 | 193.1 | **99.1 %** |
| COLD_SHALLOW −40/+25 °C | **114.9 MPa** | 226.2 | 306.7 | **100.0 %** |
| D_LOW_WIDE 45/125 °C | **91.4 MPa** | 147.0 | 160.4 | **98.9 %** |
| D_HIGH_NARROW 110/150 °C | **54.3 MPa** | 102.5 | 134.1 | **93.7 %** |

**The damage-weighted median driving stress is 3.4× to 7.2× above the top of the fitted
window, in every profile including the operating baseline.** This is a property of how hard
this package loads its joints, not of the thermal profile, and **no choice of profile removes
it.**

Phase 0J-R checked the *end-of-hold* overstress (≈ 15 MPa, inside the window) and concluded the
card was "being evaluated near its calibrated range". **That was optimistic**: end-of-hold is
the *minimum* of the cycle, and 94–100 % of the damage accumulates above it. Corrected here.

## Machine-readable domain

`configs/phase0kr/constitutive_domain.yaml`.

## Consequence

* **Temperature domain is controllable** by profile choice — keep T_min ≥ 45 °C.
* **Stress domain is not.** It is a standing limitation of every absolute prediction this
  project makes, and it is one of the reasons absolute life is reported as conditional.
* It is also an argument **for** the experiment rather than against it: a measured life
  calibrates the law in the regime the package actually operates in, which is the only way to
  retire this limitation.
