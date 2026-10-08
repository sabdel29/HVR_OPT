# Phase 0K-R Sec. 7/8 — Can the SAC305 model be extended to −40 °C?

**Answer: NO. The data do not exist, and the model is NOT extended.**

## What was searched

Seven targeted OpenAlex queries over SAC305 / SnAgCu constitutive behaviour at sub-room
temperature: creep below room temperature; tensile and stress–strain at −40 / −25 / 0 / 25 °C;
Anand, Garofalo and Norton parameter sets including sub-zero points; BGA solder constitutive
characterisation; strain-rate dependence; and creep-mechanism change with homologous
temperature.

## What the low-temperature SAC305 literature actually is

It exists, and it is almost entirely the **wrong regime**:

| retrieved title (representative) | year | regime |
|---|---|---|
| Low-Temperature **High Strain Rate** Constitutive Behavior of Doped and Undoped SAC | 2021 | impact |
| Extreme Low-Temperature **High Strain-Rate** Constitutive Behavior Evolution | 2022 | impact |
| Low Temperature **High Strain Rate** Material Properties for SAC-Q | 2020 | impact |
| Low Operating-Temperature **High Strain Rate** Constitutive Behavior of SnAgCu | 2021 | impact |
| High Strain Rate Mechanical Properties of SAC-Q for Extreme Temperature | 2021 | impact |

Classifying the `SAC305 AND "low temperature" AND constitutive` result set by regime:
**4 of 5 are high-strain-rate / impact, 0 are creep.**

This is physically unsurprising and it is the substantive point, not a search artefact:

* sub-zero SAC305 characterisation is driven by **drop and shock** requirements in portable
  electronics, which is a high-strain-rate problem;
* at −40 °C the homologous temperature of SAC305 (T_m = 217 °C = 490 K) is
  **T/T_m = 233/490 = 0.475**, below the ≈ 0.5 threshold at which creep becomes the dominant
  deformation mode. Steady-state creep tests there would run impractically long and are
  therefore not performed;
* **Syed 2001 explicitly excludes fast loading from the creep-based framework** — bend cycling
  at 1 cycle/s "creep effects are not expected to play a role there" — so a high-strain-rate
  constitutive set is not merely unhelpful, it belongs to the regime the framework rules out.

## Targeted check for sub-zero steady-state creep

A dedicated filter for works that are simultaneously (a) sub-zero, (b) creep and (c) **not**
high-strain-rate returned **two** candidates, both Derby-repository thermal-cycling studies
already seen in Phase 0J. Both use −40 °C as a **cycle minimum**, not as a creep-test
temperature; neither reports creep constants below room temperature.

**No source was found that provides SAC305 steady-state creep data below 45 °C.**

## Sec. 8 — the model is therefore NOT extended

Sec. 8 is explicit: *"If suitable low-temperature data do NOT exist: do not extend."*

No refit was attempted. No `LOW_TEMPERATURE_MODEL_VALIDATION.md` is produced, because there is
nothing to validate — producing one would mean inventing the data it validated.

Extending the Arrhenius form by fiat from 45 °C down to −40 °C would be indefensible on its own
terms: it is an 85 K extrapolation across the homologous-temperature threshold at which the
governing mechanism is expected to change, and the Arrhenius fit was never independently
validated even inside its own range.

## Verdict on the Phase-0K decisive profile

> **−40 °C → +25 °C is INVALID FOR EXPERIMENT DESIGN USING THE CURRENT MODEL.**
>
> **100 % of its damage accumulates below the 45 °C creep-calibration floor**, and its
> damage-weighted median driving overstress of 114.9 MPa is the worst of any candidate.
> The Phase-0K claims attached to it — **D = 1.849, 85 % separation, 6.19 σ** — are
> **WITHDRAWN as current** and retained only as historical experiment-design screening.

## What would change this

One of:

* SAC305 steady-state creep data at, say, 0 and 25 °C, which would lower the floor to 0 °C and
  make a 0/+60 °C cycle admissible; or
* a constitutive model valid across the mechanism change — unified viscoplastic with a
  low-temperature branch — refitted and independently validated.

Neither is available now, and neither is required: a within-domain pair with adequate
discriminating power **was** found (`EXPERIMENT_PROFILE_SELECTION.md`).
