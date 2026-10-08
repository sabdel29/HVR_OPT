# Phase 0K-R Sec. 9/10/11 — Profile selection, within the validated domain

## Selection rule, predeclared

A pair is admissible only if **neither condition is INVALID** on the constitutive-domain audit.
Among admissible pairs, the pair must reach the predeclared bar **Z ≥ 3 for model
discrimination at the observed worst Weibull slope β = 5.1 with n = 16**; among those, the
**shortest campaign wins**. Sec. 10 forbids selecting on `D` alone, and the rule is applied
rather than stated: the highest-`D` admissible pair was **not** chosen.

## Candidates searched

Eight profiles with `T_min ≥ 45 °C` (the creep floor) and `T_max ≤ 150 °C` (the ceiling), each
solved on the graded Syed-matched mesh to a stabilised cycle.

| condition | T range | ΔT | dwell | **w/ε (MPa)** | cycle |
|---|---|---|---|---|---|
| **D_LOW_WIDE** | **45 → 125 °C** | 80 | 5 min | **122.06** | 1.06 h |
| D_MID (= Phase-0K HOT_SHALLOW) | 55 → 125 °C | 70 | 5 min | 113.10 | 0.94 h |
| D_LOW_NARROW | 45 → 85 °C | 40 | 5 min | 106.79 | 0.61 h |
| D_LOW_LONG | 45 → 85 °C | 40 | 15 min | 104.16 | 0.94 h |
| D_HIGH_WIDE | 80 → 150 °C | 70 | 5 min | 99.97 | 0.94 h |
| **D_HIGH_NARROW** | **110 → 150 °C** | 40 | 5 min | **84.79** | 0.61 h |
| D_HIGH_LONG | 110 → 150 °C | 40 | 15 min | 82.91 | 0.94 h |

`D_FULL_SPAN` (45 → 150 °C) failed to converge and is recorded as such.

The physics that makes this work: the creep law sees the **overstress** `σ_eq − σ_y(T)`, and
`σ_y` falls with temperature, so a cold-in-domain cycle sustains a much higher stress per unit
creep than a hot one. **Within the domain, temperature band moves `w/ε` by 44 %; dwell by only
2–3 %.**

## Ranked pairs

| pair | D | separation | Z (β = 5.1, n = 16) | max cell | domain |
|---|---|---|---|---|---|
| **D_LOW_WIDE + D_HIGH_NARROW** | **1.4395** | **44.0 %** | **3.44** | **91 d** | severe (stress) |
| D_LOW_WIDE + D_HIGH_LONG | 1.4721 | 47.2 % | 3.65 | 133 d | severe (stress) |
| D_MID + D_HIGH_LONG | 1.3641 | 36.4 % | 2.93 | 133 d | severe (stress) |
| D_MID + D_HIGH_NARROW | 1.3339 | 33.4 % | 2.72 | 91 d | severe (stress) |
| D_LOW_WIDE + D_HIGH_WIDE | 1.2210 | 22.1 % | 1.89 | 64 d | severe (stress) |

## Selected

> ### D_LOW_WIDE (45 → 125 °C) + D_HIGH_NARROW (110 → 150 °C)
> both with **5-minute dwells** and **3 °C/min ramps**.
> **D = 1.4395**, 44.0 % separation between the two laws' predicted life ratios,
> **Z = 3.44** at β = 5.1 and n = 16.

`D_HIGH_LONG` scores marginally better (D = 1.4721, Z = 3.65) but costs **46 extra days per
cell** for a 2 % gain in D, and needs a second dwell recipe. It is rejected on the predeclared
rule, and this is exactly the case Sec. 10 warns about.

Both selected conditions share one dwell and one ramp rate, so a single chamber recipe family
covers the campaign.

## Sec. 11 — original versus revised

| | **ORIGINAL Phase-0K pair** | **REVISED Phase-0K-R pair** |
|---|---|---|
| conditions | −40/+25 °C and +55/+125 °C | **45/125 °C and 110/150 °C** |
| T below the 45 °C creep floor | **YES — −40 °C, 85 K below** | **NO** |
| damage accumulated below the floor | **100 %** (cold cell) | **0 % (both cells)** |
| damage-weighted median overstress | 114.9 MPa (cold cell) | 91.4 / 54.3 MPa |
| damage outside the stress window | 100 % / 98.7 % | 98.9 % / 93.7 % |
| **D** | 1.849 | **1.4395** |
| separation | 84.9 % | **44.0 %** |
| Z, β = 5.1, n = 16 | (6.19 claimed at β = 6; 5.99 at β = 5.1) | **3.44** |
| constitutive-domain status | **INVALID** | temperature **PASS**, stress **FAIL** |
| max cell duration | ≈ 91 d | ≈ 91 d |

> **The Phase-0K claims D = 1.849, 85 % separation and 6.19 σ are WITHDRAWN as current.**
> They are retained only as historical experiment-design screening, because the cold condition
> they depend on is invalid for this material model.

The redesign costs **41 % of the discriminating power** (D 1.849 → 1.4395) and buys validity.
It remains above the predeclared Z ≥ 3 bar.

## The limitation no profile removes

Every admissible pair is still **SEVERE EXTRAPOLATION on stress**: 93.7–98.9 % of damage
accumulates above the 15.92 MPa top of the fitted window, with damage-weighted medians of
54–91 MPa. **This is a property of how hard this package loads its joints and cannot be fixed
by choosing a profile.** It is carried forward as a standing limitation on every *predicted*
number here — including `D` itself — and it is one of the strongest arguments for running the
experiment, since a measurement is the only thing that retires it.
