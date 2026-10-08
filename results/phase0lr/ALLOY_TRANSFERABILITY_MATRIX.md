# Alloy transferability matrix

**Phase 0L-R, Part 7.** Alloy labels are kept strict and are never merged. Machine-readable
form: `results/phase0lr/alloy_transferability_matrix.csv`.

## Why this exists

The current SAC305 material card is built from two different alloys. Its creep half comes from
**Sn3.9Ag0.6Cu**; its yield half comes from **SAC305**. The overstress formulation then
subtracted one from the other. Phase 0L found that; Phase 0L-R keeps the distinction explicit so
it cannot be re-merged by accident.

Silver content is not a cosmetic difference in this alloy family. Ag controls Ag₃Sn precipitate
density, and precipitate strengthening is the dominant creep-resistance mechanism in SnAgCu.
3.9 wt % against 3.0 wt % is a 30 % relative difference in the controlling element.

## The four accepted roles

| Role | Meaning |
|---|---|
| **DIRECT SAC305 CALIBRATION** | may supply parameters for the SAC305 card |
| **BOUNDING DATA ONLY** | may bound a quantity, may not supply a parameter |
| **MODEL-FORM EVIDENCE ONLY** | may justify a functional FORM, never its constants |
| **REJECTED FOR PARAMETER TRANSFER** | may not be used for either |

## The matrix

| dataset | alloy | Ag % | T (°C) | σ (MPa) | ε̇ (1/s) | role |
|---|---|---|---|---|---|---|
| Xiao & Armstrong 2005, 19 creep points | **Sn3.9Ag0.6Cu** | 3.9 | 45–150 | 7.51–15.92 | 1.4e−9…8.1e−7 | MODEL-FORM + BOUNDING |
| Motalab et al. tensile curves | SAC305 | 3.0 | −40…125 | ~12–45 | 1e−5…1e−3 | DIRECT (secondary access only) |
| **Yamin 2025 Anand set** | SAC305 | 3.0 | 25–125 | ~14–40 | 1e−5…1e−3 | **DIRECT** |
| Yuan 2023 Anand set (EINN+BI) | SAC305 | 3.0 | −40…122 | tensile | 1e−5…1e−3 | **REJECTED** (badly identified) |
| Yuan 2023 Chaboche σ₀(T) | SAC305 | 3.0 | −40…122 | 10.5–39.3 | 1e−5 | DIRECT, two model layers out |
| Yuan 2023 Garofalo constants | **Sn3.9Ag0.6Cu** | 3.9 | 45–150 | 7.51–15.92 | 1.4e−9…8.1e−7 | MODEL-FORM ONLY; rejected above ~40 MPa |
| Paska 2024 tensile + creep | SAC305 | 3.0 | RT only | — | — | BOUNDING ONLY |
| Micromachines 2018 | SAC305 | 3.0 | 27 only | ~25 | 0.05 | BOUNDING ONLY |
| Materials 2021 Hill–Norton | SAC | 3.0 | RT | **< 12 by construction** | — | REJECTED for this window |

## Two judgements that matter

**The 19 creep points stay in, but relabelled.** They remain the only dataset anywhere near the
creep-rate regime, so they still bound low-stress rate behaviour and still justify a power-law
form. What changes is the label: the resulting A(T), n(T) are **SnAgCu surrogate parameters**,
not SAC305 parameters, and M1 must be described as a "variable-consistent SnAgCu Norton
surrogate" (Part 8).

**Two Anand sets fitted to the SAME SAC305 data disagree wildly, and only one is usable.**
Yuan's EINN+BI set (Q/R = 7818 K) and Yamin's set (Q/R = 11690 K) were both fitted to Motalab's
curves. Extrapolated down to creep rates, Yamin's lands within a median factor of **1.76** of
the Sn3.9Ag0.6Cu measurements while Yuan's misses by **1240**. That gap is between two fits, not
between two alloys, and it is direct evidence of Anand parameter non-identifiability from
tensile data alone.

**This corrects Phase 0L.** Phase 0L rejected the whole Anand FAMILY on the basis of the Yuan
set. The rejection was parameter-set-specific: with a better-identified set the same functional
form spans the regime creditably and has no finite stress ceiling. The family is re-admitted in
Phase 0L-R; what remains rejected is the Yuan parameterisation.

## What is still missing

No dataset in this matrix measures SAC305 **in the creep-rate regime** (1e−9…1e−7 /s) at
**45–150 °C**. Every SAC305 entry is tensile-rate work; the only creep-rate entry is the wrong
alloy. That single gap is what keeps the high-stress constitutive response open, and it is what
the material-characterisation option in
`MATERIAL_TEST_VS_PACKAGE_TEST_VALUE.md` is designed to close.
