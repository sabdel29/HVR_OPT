# PHASE 0M-R SECTION 3 --- TSV GEOMETRY: WHAT THE RADIUS RESULT DOES AND DOES NOT SAY

## The derivation is retained

For one conductor `R_single = rho(T) h / A_c`. Under minimum-current-capability provisioning
`n_alloc = ceil(I / (J_design A_c))`, so

$$R_{field} = \frac{\rho(T) h}{A_c} \cdot \frac{J_{design} A_c}{I} = \frac{\rho(T) h J_{design}}{I}$$

and the conductor area cancels. Measured across r = 2.5 to 50 um at h = 300 um and 1000 A,
the field resistance moves **0.070 %**.

## The conclusion is NARROWED

**Not permitted:** *"TSV radius is irrelevant."*

**Permitted:** *the TSV cross-section is not an independent FIELD-LOSS lever under
minimum-capability provisioning when `J_design` is geometry-independent.*

Four qualifiers do real work in that sentence, and Phase 0M's wording carried none of them:
the allocation POLICY, the assumption that `J_design` does not depend on geometry, the word
FIELD (a single via still obeys `1/r^2`), and the word LOSS (feasibility is a different
question, answered below).

## Three current densities, kept apart

Phase 0M ran them together. Conflating them is how a process bound becomes an optimizer
variable.

| symbol | meaning | value here | status |
|---|---|---|---|
| `J_design` | what the design provisions to | 1.0e8 A/m2 | DERIVED_FROM_SOURCE, June-2026 Table III |
| `J_process_max` | manufacturing capability bound | 4.0e8 A/m2 | DERIVED_FROM_SOURCE, the most aggressive density any available source demonstrates (ECTC-2024) |
| `J_reliability_allow` | EM / lifetime allowable | **OPEN** | no primary EM study with its temperature, lifetime and geometry was retrievable |

`J_design <= J_process_max` is **enforced in code** and raises `ProcessViolation` rather than
clipping. `J_process_max` is never swept as a free variable: a design that moves it is a
different technology, not a different design. `J_reliability_allow` stays OPEN, so
feasibility is reported as a map over `J` and never as a verdict.

## The discrete count is NOT smoothed

`ceil()` on `n_required` and `int()` on `n_available` are kept in production. The continuous
idealisation is computed alongside, for comparison only. It matters where the count is small:

| rail | r_drill | n_required | continuous | discrete penalty |
|---|---|---|---|---|
| per_phase_6p8A | 25.0 um | 37 | 36.07 | **2.57 %** |
| per_phase_6p8A | 25.0 um | 37 | 36.07 | **2.57 %** |
| per_phase_6p8A | 25.0 um | 37 | 36.07 | **2.57 %** |
| per_phase_6p8A | 50.0 um | 9 | 8.84 | **1.84 %** |
| per_phase_6p8A | 50.0 um | 9 | 8.84 | **1.84 %** |
| per_phase_6p8A | 50.0 um | 9 | 8.84 | **1.84 %** |

Negligible on the 1 kA rail, where `n` is tens of thousands. Up to **0.88 %** on a 6.8 A
per-phase net with a large via, where `n = 14`. That is precisely the intra-VR vertical link
of Section 6, so smoothing the ceiling would bias the term this phase is adding.

## Where the radius DOES become decision-relevant

### 1. Aspect ratio --- the binding constraint, and it is severe

| via height | feasible radii (AR_max = 10) | of the 12 swept |
|---|---|---|
| 100.0 um | 7.5 to 50.0 um | 10/12 |
| 300.0 um | 15.0 to 50.0 um | 7/12 |
| 1300.0 um | **NONE** | 0/12 |

At the reference 300 um substrate, **only r >= 15 um is buildable** --- and 15 um is exactly
the reference radius. The source-demonstrated geometry sits **on** the aspect-ratio limit,
not inside it. At 1.30 mm no radius in the swept range works at all; the rule `r >= h/20`
demands r >= 65 um. (Z1 escapes this because its embedded cell shortens the via field to
74 um; Z2 and Z4 do not.)

So the radius is not a loss lever and IS a hard feasibility variable, coupled to the
substrate thickness that the whole architecture argument turns on.

### 2. The liner --- the one geometry term that does not cancel

Under fixed-pitch allocation the liner changes `A_Cu` without changing the pitch, so nothing
cancels:

| drilled radius | t_liner | r_Cu | phi_Cu | k_xy | CTE_eff | R_field |
|---|---|---|---|---|---|---|
| 5.0 um | 0.00 um | 5.00 um | 0.0245 | 133.20 | 2.85 ppm/K | 0.000522 mOhm |
| 5.0 um | 0.25 um | 4.75 um | 0.0222 | 132.94 | 2.82 ppm/K | 0.000578 mOhm |
| 5.0 um | 0.50 um | 4.50 um | 0.0199 | 132.66 | 2.80 ppm/K | 0.000644 mOhm |
| 5.0 um | 1.00 um | 4.00 um | 0.0157 | 131.99 | 2.75 ppm/K | 0.000815 mOhm |
| 5.0 um | 2.00 um | 3.00 um | 0.0088 | 130.23 | 2.68 ppm/K | 0.001449 mOhm |
| 5.0 um | 4.00 um | 1.00 um | 0.0010 | 125.17 | 2.59 ppm/K | 0.013045 mOhm |

A 4 um liner in a 5 um via leaves 1 um of copper and raises the field resistance **25x**. The
same liner in a 15 um via costs 87 %. The governing ratio is `t_ox / r`, confirming the
Phase-0M thermal finding from the electrical side.

### 3. Keep-out zone --- binds above `k_KOZ = s_min / 2r`

| radius | k_KOZ | pitch | n_available | phi_Cu | R_field |
|---|---|---|---|---|---|


Below the crossover the additive spacing rule binds and the keep-out is free; above it the
pitch grows with the radius and the field resistance rises as `(1 + k_KOZ)^2` --- **2.2x**
from `k_KOZ` 1.0 to 2.0. `k_KOZ` is an ASSUMPTION in this repository and is swept, never
fixed.

## Summary

| question | answer |
|---|---|
| is radius a FIELD-LOSS lever under policy A? | **No** --- 0.07 % over a 20x radius range |
| is radius a lever under fixed-count allocation? | Yes, `1/r^2` |
| is radius a FEASIBILITY variable? | **Yes, decisively** --- aspect ratio eliminates 5 of 12 radii at 300 um and all 12 at 1300 um |
| does the liner cancel? | **No** --- it is the one geometry term that does not |
| does the keep-out matter? | Only above `k_KOZ = s_min/2r`, then as `(1+k_KOZ)^2` |
| does discreteness matter? | Not at 1 kA; up to 0.88 % on low-current intra-VR links |
| is `J_process_max` an optimizer variable? | **No.** It is a bound, enforced, and raises rather than clips |
