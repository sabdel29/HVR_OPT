# Phase 0I Sec. 10/11 — Failure metric, predeclared BEFORE any architecture was run

This file was written before the first architecture submodel was executed. Its purpose is to
remove the freedom to pick, after seeing results, whichever metric produces the strongest
architecture effect.

| field | declaration |
|---|---|
| **METRIC** | `Δε_in` — the increment of accumulated equivalent **inelastic** strain over one stabilised thermal cycle. CalculiX's `PEEQ` aggregates plastic and creep equivalent strain (the solver states: *"selection of CEEQ or CE or PE is converted into PEEQ; no distinction is made"*), so `Δε_in = PEEQ(end of cycle k) − PEEQ(end of cycle k−1)`. |
| **UNITS** | dimensionless (strain) |
| **EXTRACTION REGION** | the solder volume of the single critical joint, **excluding a corner exclusion band** of one element layer adjacent to each pad free edge |
| **AVERAGING VOLUME** | element-volume-weighted mean over that region: `Δε_in = Σ(Δε_in,e · V_e) / Σ V_e`, using CalculiX `EVOL` |
| **CYCLE DEFINITION** | one full thermal excursion `T_low → T_high → T_low` with declared dwells; the reported value is taken from the **stabilised** cycle, defined as the first cycle whose `Δε_in` differs from the previous cycle by less than 5 % |
| **SECONDARY METRIC** | `ΔW_in`, volume-averaged inelastic strain-energy density per stabilised cycle, from the hysteresis loop area. Reported alongside, never substituted for the primary. |
| **LIFETIME CORRELATION** | **NONE ADMITTED.** No SAC305 `N_f = f(Δε_in)` or `N_f = f(ΔW_in)` relation could be retrieved in this environment: the two candidate open-access sources return HTTP 403 to publisher servers. Consequently **no N_f is predicted**, and a parametric required-life sweep is reported instead (Sec. 20). |
| **SOURCE (constitutive)** | `reliability_material_model.yaml` — SAC305 only, no cross-alloy mixing |

## Why not a single corner element

Phase 0C measured interface **peel** diverging at 19.2–20.1 % per mesh refinement because the
underfill free edge is a bimaterial corner with a theoretical stress singularity, and excluded
it from all decision logic. Phase 0H found the p99 interface **shear** non-monotone under
refinement for the same reason. A single corner-element maximum of an inelastic quantity would
inherit exactly that behaviour.

The regularisation adopted here is **volume averaging over a declared region with a corner
exclusion band**, which is the standard remedy in the solder-fatigue literature and is the
reason Darveaux-family metrics are quoted as volume averages rather than peaks. Mesh
convergence of the averaged quantity is demonstrated in `local_metric_convergence.csv`; if it
does not converge, the metric is not used.

## What would change this declaration

Only the discovery of an admissible SAC305 life relation, which would add an `N_f` column. It
would not change the metric, the extraction region or the averaging rule.
