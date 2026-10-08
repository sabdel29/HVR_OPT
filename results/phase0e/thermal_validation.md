# Phase-0E — Thermal Validation

## 1. What was and was not validated before

Phase 0D-R validated the **conduction operator** on a 2-D sheet (FD vs MOOSE, 0.33–0.45 %).
It never checked the complete 3-D package thermal model with spatially mapped heat. Phase 0E
does, in two independent codes.

## 2. MOOSE full-package model

The complete stack is rebuilt in MOOSE: 30 × 30 mm silicon substrate, four HVR tiles embedded
flush with the substrate top, the underfill/microbump interface layer, the 22.36 mm die, and
the TIM — with volumetric heat in the die and in each tile, Robin (convective) boundaries top
and bottom, and adiabatic sides. This is an independent mesher, element formulation and
linear solver, not a re-run of the same code.

### Two quantisation corrections, without which the comparison is invalid

`SubdomainBoundingBoxGenerator` assigns whole elements by centroid, so a 22.36 mm die on a
0.5 mm grid becomes 22.0 mm. Left uncorrected this:

* put the wrong source density in each block (nominal volume ≠ meshed volume), and
* shrank the cooled area from 500 to 484 mm², losing **3.2 % of the heat**, which showed up
  exactly as a −3.168 % energy residual.

Both meshed volumes and meshed areas are computed exactly in the driver; source densities use
the meshed volume, and the film coefficients are scaled so the **total cooling conductance
h·A matches the CalculiX model**. That is what makes this a like-for-like cross-check rather
than a different boundary-value problem. Energy balance then closes to **−0.000 %** in every
case, matching the CalculiX standard held since Phase 0B.

## 3. Result — does the independent solver preserve candidate ordering?

| case | configuration | CalculiX T_max (°C) | MOOSE T_max (°C) | difference |
|---|---|---:|---:|---:|
| TH-1 | distributed, h_sub = 500 µm | 68.982 | 69.905 | +1.34 % |
| TH-2 | distributed, h_sub = 200 µm | 71.650 | 72.587 | +1.31 % |
| TH-3 | small footprint (j = 4.0) | 77.440 | 78.725 | +1.66 % |
| TH-4 | large footprint (j = 1.5) | 66.623 | 67.083 | +0.69 % |
| TH-5 | edge-biased placement | 71.399 | 71.583 | +0.26 % |

```
CalculiX ordering:  TH-4 < TH-1 < TH-5 < TH-2 < TH-3
MOOSE    ordering:  TH-4 < TH-1 < TH-5 < TH-2 < TH-3
```

# ORDERING PRESERVED

Maximum discrepancy 1.66 %, mean 1.05 %, and MOOSE is systematically ~1 % warmer — consistent
with its coarser lateral mesh (0.5 mm uniform against the CalculiX graded mesh). Every design
decision in this project rests on *ordering*, and ordering is reproduced exactly across all
five cases, including the thickness pair and both footprint extremes.

## 4. Icepak — attempted, converged, and rejected

Icepak is licensed here (`elec_solve_icepak`) and the model built and solved: 14 min 55 s,
"Normal Completion", energy residual 9.7e-7. **Its result was nevertheless discarded.**

Every object — die, HVR tile, substrate — returned exactly 4726.85 °C, which is 5000.00 K: a
solver clamp, not a temperature. The external cooling did not take effect. The boundaries
`cool_top` and `cool_bot` are present in the saved project, so they were created; the likely
cause is that in Icepak an external convective boundary belongs on a **cabinet face**, whereas
these were applied to the internal solid/air interface of a floating solid stack.

This is reported rather than iterated on because MOOSE already provides a genuine independent
full-package cross-check, and a second commercial run would not have changed the conclusion.
**No Icepak number appears anywhere in this project's results.** The artifact is retained at
`results/phase0e/aedt/icepak_TH1.json` with its 5000 K signature intact so the failure is
auditable.

## 5. What remains open

* The cooling calibration (`h_top = 17 522 W/m²K`) is still a **derived** value fitted so the
  reference case reaches the June-2026 cooled baseline junction temperature. Both solvers
  inherit it, so agreement between them says nothing about whether that boundary is right.
* No transient or flow modelling. Both models are steady conduction with Robin boundaries.
* Icepak, and therefore any conjugate-heat-transfer check, remains unvalidated.

## 6. Artifacts

`thermal_moose_package.csv`, `thermal_crosscheck.csv`, `aedt/icepak_TH1.json`.
Drivers: `scripts/phase0e/thermal_moose_package.py`, `scripts/phase0e/thermal_icepak.py`.
