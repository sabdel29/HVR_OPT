# Phase-0F Sec.2 — 1-kW Cooling Calibration

## 1. Why the Phase-0B calibration could not be carried over

Phase 0B solved for `h_top = 17 521.6 W/m2K` so that a ~282 W controlled vehicle reached the
June cooled-baseline junction temperature. That was a deliberate choice for a controlled
mechanical experiment. Phase 0F simulates the actual 1-kW reference, where the package rejects
roughly **four times** the heat through the same die area. Carrying the old coefficient over
would have left the package tens of degrees off the reference and corrupted every
temperature-dependent loss in the ET loop.

## 2. The June 1-kW thermal reference, as stated

June-2026 Sec. IV-D:

* *"substrate-embedded micro-channel cooling is employed, with cooling channels positioned
  adjacent to the GaN switch layer"*
* *"a coolant flow rate of 1.6 g/s, limiting the maximum junction temperature to
  approximately 84 C"*
* *"the total system loss converges to 210 W ... end-to-end efficiency of 82.6%"*
* isothermal: 185 W and 84.6 %; **without** thermal management the junction exceeds 110 C,
  loss rises to 225 W and efficiency falls to 81.6 %

The calibration target adopted here is **T_j,max = 84 C at the 1-kW load with the ET loop
converged**.

## 3. Result — top-surface cooling (primary, keeps continuity with Phase 0B-0E)

| quantity | Phase 0B (282 W vehicle) | **Phase 0F (1 kW)** |
|---|---:|---:|
| h_top | 17 521.6 W/m2K | **166,000.0 W/m2K** |
| ratio | 1.00x | **9.47x** |
| target T_j,max | 84.0 C | 84.0 C |
| achieved | 83.51 C | **84.071 C** |
| residual | -0.49 K | **+0.071 K** |
| converged | yes | **True** |

At the converged point: converter loss **124.38 W**, package distribution loss
**0.64 W**, total heat **1125.0 W**, efficiency
**88.89 %**.

The coefficient is **9.5x** the Phase-0B value. That is the whole
justification for Sec. 2 of the brief: reusing the old number would have put the 1-kW package
at roughly 130 C rather than 84 C, a 46 K error, and converter loss would have been
overstated by about 25 W.

## 4. Result — substrate-side cooling (the topology June actually describes)

June places the channels **inside the substrate adjacent to the GaN switch layer**, not above
the die. That reverses the through-thickness thermal gradient, and warpage is driven by that
gradient, so the alternative was calibrated too — with the cooled surface at the substrate
underside and the TIM top reverting to natural convection.

**It does not converge.** The residual flattens at **+6.96 K** with
`h_bottom = 398,672 W/m2K` (22.8x Phase 0B), giving
T_max = **90.96 C** against the 84 C target.

This is a physical result, not a numerical failure. The die dissipates 1000 W of the ~1100 W
total and sits on the far side of the package from the coolant, so cooling from the substrate
underside alone cannot hold it at 84 C no matter how large the film coefficient becomes: the
conduction resistance of the intervening stack sets a floor near 91 C. **A 1-kW DVPD package
cannot be cooled from the substrate side alone**; June's architecture must be removing the
die's heat by some path this single-sided model does not represent, or their 84 C refers to
the GaN junction rather than the die.

## 5. What is carried forward, and the caveat that goes with it

`h_top = 166,000 W/m2K` is used for every Phase-0F case. It is **DERIVED**,
not sourced, and it is a large number: 9x the Phase-0B value and in
the range of aggressive two-phase or jet-impingement cooling rather than ordinary
single-phase microchannels.

The model-form caveat is explicit: matching the junction temperature does not match the
internal temperature FIELD. A substrate-side boundary would cool the converter layer directly
and the die less, reversing the through-thickness gradient. Since Sec. 4 above shows that
boundary cannot reach the reference temperature at all, the top-cooled field is the only one
consistent with the June junction target, but every mechanical result in Phase 0F inherits
that assumption and would change sign in the gradient if the real package cools from below.

Artifacts: `cooling_1kw_calibration.json`, `cooling_1kw_calibration_substrate.json`.
Driver: `scripts/phase0f/calibrate_cooling_1kw.py`.
