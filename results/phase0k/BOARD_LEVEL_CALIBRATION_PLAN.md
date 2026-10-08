# Phase 0K Sec. 12 — Board-level calibration experiment: executable plan

> **THIS EXPERIMENT HAS NOT BEEN RUN.** No measurements exist, none are synthesised, and no
> constant in this project has been fitted to hypothetical data. This is a design.

## Objectives, in priority order

| | objective | achieved by |
|---|---|---|
| **A** | calibrate **absolute** life for this package | any one cell, via η → mean life → `C` or `W` |
| **B** | validate the **Z2/Z1 relative** advantage of 1.21–1.38× | Z1 and Z2 at the **same** condition |
| **C** | **discriminate** strain-based from energy-based life law | **two conditions spanning `w/ε`** |

C is the one that cannot be obtained by adding specimens, and it drives the design.

## Test matrix — 4 cells, 64 packages

| cell | architecture | condition | T range | dwell | ramp | n |
|---|---|---|---|---|---|---|
| 1 | **Z1 embedded** | **COLD_SHALLOW** | −40 → +25 °C | 5 min each extreme | 3 °C/min | 16 |
| 2 | **Z1 embedded** | **HOT_SHALLOW** | +55 → +125 °C | 5 min each extreme | 3 °C/min | 16 |
| 3 | **Z2 backside** | COLD_SHALLOW | −40 → +25 °C | 5 min each extreme | 3 °C/min | 16 |
| 4 | **Z2 backside** | HOT_SHALLOW | +55 → +125 °C | 5 min each extreme | 3 °C/min | 16 |

**Z4 is deliberately excluded** — value-of-information analysis in
`ABSOLUTE_LIFE_IDENTIFIABILITY.md` shows it adds D = 1.03 of discrimination and its predicted
life sits inside the post-calibration model spread, so the test could not distinguish it from Z1.

### Why these two conditions

They are the pair that maximises `(w/ε)_A/(w/ε)_B` = **1.849**, because the creep law sees the
**overstress** `σ − σ_y(T)` and the yield stress is high at −40 °C and low at +125 °C. The two
laws then predict life ratios between the cells that differ by **85 %** — resolvable at 6.2σ.
Both have similar ΔT (65 K and 70 K), so the comparison is not confounded by excursion size.

The ramp rate and dwell match JESD22-A104-B guidance (≤ 15 °C/min, preferred 10–14; 5-min dwells
are TC3's) so the profiles are executable in a standard three-zone chamber and comparable to the
calibration set's conditions.

## Test vehicle — preserve what the model assumes

| attribute | specification | why |
|---|---|---|
| solder alloy | **SAC305**, both ball and paste | the alloy the model is built for; the calibration is SAC405/395, and this test is what closes that gap |
| ball diameter / standoff | **400 µm / 300 µm** | the June-2026 geometry the submodel represents |
| pitch | **800 µm** | as modelled |
| pad | **SMD, 400 µm**, electrolytic NiAu package side, OSP board | matches Syed's pad type and finish so the failure site is comparable |
| underfill | **none** | the model has none; adding it would change the joint's whole stress state |
| board | FR-4, **1.6 mm**, daisy-chain routed | inside Syed's 0.8–1.6 mm range |
| package | Z1 and Z2 **z-stacks as modelled**, including the substrate thickness each architecture uses (Z1 1.3 mm, Z2 0.3 mm) | the architecture difference IS the stack |
| die | as modelled, to preserve package stiffness | stiffness sets the corner displacement |
| daisy chains | **≥ 2 independent nets per package**, corner joints on separate nets | the corner joint is the predicted failure site; separating it isolates the signal |

## Monitoring and failure definition

**Identical to the calibration source** (`failure_definition_alignment.md`):

* in-situ continuity, every net, sampled **≤ 2 min**;
* event threshold **> 300 Ω**;
* failure confirmed by **ten further threshold events within 10 % of the time of the first**;
* monitoring continues after first failure so later failures in the same package are captured.

## Data recorded

Per specimen: cycle count at first event and at confirmation; full resistance trace; chamber
and board-mounted thermocouple profiles (board-mounted, not chamber setpoint — Syed makes this
distinction and it matters); cell, architecture, serial.
Per cell: 2-parameter Weibull η and β by MLE with right-censoring, 90 % profile-likelihood
intervals, and the derived **mean life** `η·Γ(1 + 1/β)`.
End of test: cross-section of 2 failures and 1 survivor per cell for crack-fraction
corroboration — not used in the calibration, only as a check that the electrical endpoint
matches the modelled crack state.

## Duration estimate

Predicted lives at these conditions are not yet known — that is the point of the test — but the
operating-cycle prediction of 482–3206 cycles at a 20-min cycle (2 × 5-min dwells + 2 × ~22-min
ramps at 3 °C/min for a 65–70 K range ≈ **54 min/cycle**) implies roughly **18 days to 4 months**
per cell to reach 63 % failures. Cells run in parallel in one chamber per condition.

**A pre-agreed cycle ceiling must be set before the test starts**, with the censoring treatment
in `sample_size_and_statistics.md` applied to whatever survives it.

## What this experiment would deliver

| | |
|---|---|
| **calibrated** | absolute life for **this** package at **these** conditions, both laws |
| **identified** | **which** life law extrapolates correctly, at 6.2σ |
| **validated** | the Z2/Z1 relative advantage, measured directly at two conditions |
| **enabled** | extrapolation to the operating cycle and to a declared mission |

## What it would NOT deliver

* a **required life** — that is the system owner's, not the laboratory's;
* validity for a **different package, alloy or pitch**;
* anything about the **six uncomputed failure mechanisms** — this is a solder-fatigue test;
* resolution of the **Z1 vs Z4 electrical** question, which is a thermal-coupling issue, not a
  reliability one.
