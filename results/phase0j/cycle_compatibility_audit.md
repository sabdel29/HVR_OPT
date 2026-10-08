# Phase 0J Sec. 15/16 — Does one simulated cycle equal one experimental fatigue cycle?

Sec. 15 forbids assuming it does. It does not.

## The two cycles side by side

| property | **Phase-0I simulated cycle** | **JESD22-A104-B as applied in the literature** | compatible? |
|---|---|---|---|
| T_min | **25.0 °C** | −40 °C | **no** — 65 K apart |
| T_max | **81.1 – 83.2 °C** | +125 °C | **no** — 42 K apart |
| **ΔT** | **56.1 – 58.2 K** | **165 K** | **no — 2.9× larger** |
| T_mean | 53.1 – 54.1 °C | 42.5 °C | close |
| ramp rate | ≈ 11.6 K/min | 3.6 K/min (guidance ≤ 15, preferred 10–14) | **inside guidance** |
| **dwell at each extreme** | **ZERO** | **15 min** | **no — qualitatively different** |
| period | 600 s = 10 min | ≈ 120 min | **no** |
| waveform | symmetric triangle | trapezoid | **no** |
| driver | **the system's own OFF → ON → OFF power cycle** | chamber air temperature | different physics |
| mechanical BC | displacement-driven from the global package model | whole-assembly CTE mismatch | comparable in kind |

Sources for the right-hand column: Springer 2025 (profile as applied), George 2010 (JEDEC ramp
guidance), IMAPS 2023 (1000-cycle board-level condition). All secondary descriptions — jedec.org
returns HTTP 403 — and labelled as such.

## The dwell is the decisive difference

The simulated waveform has **no hold at either extreme**. `write_inp` emits `*TEMPERATURE`
without `AMPLITUDE=STEP`, and CalculiX then ramps temperature linearly across the step, so the
300 s named `DWELL` in the Phase-0I driver is a 300 s **ramp**. All creep accumulates during
ramps, at continuously changing temperature and stress; none accumulates at a held extreme.

This is not a detail. It is the single variable solder thermal-fatigue correlations are most
sensitive to, and one of the two candidate strain-range laws makes the dependence explicit.
Engelmaier's fatigue exponent is

```
c = c0 + c1*T_sj + c2*ln(1 + 360/t_dwell)
```

At `t_dwell = 0` the logarithm **diverges**. The Engelmaier model is not merely inaccurate for
our cycle — it is **undefined** for it. That is recorded as the decisive incompatibility for
candidate L2 in `LIFE_LAW_ADMISSIBILITY.md`.

## Sec. 15 — which remedy applies

Sec. 15 offers two: **(A)** re-run the local submodel on a life-law-compatible cycle, or
**(B)** establish a source-backed acceleration/equivalence relation.

**Neither is available, for a reason that precedes both.** Both remedies exist to reconcile our
cycle with *a particular law's* calibration cycle. **No admissible law was found** (Sec. 6,
0 of 10), so there is no calibration cycle to reconcile with:

* **(A) is not actionable.** Re-running at −40/+125 °C with 15-min dwells is computationally
  easy and was considered. It was **not done**, because it would produce a metric matched to a
  law whose coefficients we do not have, and because −40 °C and +125 °C both sit **outside the
  validated 7.5–16 MPa window** of the Norton creep surrogate. Running it would have produced
  numbers that look like progress and mean nothing. The decision is recorded rather than
  quietly skipped.
* **(B) is not available.** The acceleration-factor literature retrieved (Norris–Landzberg and
  its lead-free recalibrations, IMAPS 2009) is itself the subject of an accuracy dispute — that
  source's whole argument is that published NL constants "differ widely" and produce
  non-conservative predictions. Sec. 40 forbids mapping an accelerated qualification cycle to
  field life without justification, and an acceleration factor whose own authors report wide
  disagreement is not that justification.

## Sec. 16 — the DVPD mission IS power cycling, and that is what was modelled

Sec. 16 asks that if the product experiences workload/power cycles rather than chamber cycling,
the joint cycle should come from `P(t) → T_local(t) → nonlinear solder solve`. **That is exactly
what Phase 0I did**, and it is why the simulated cycle looks nothing like a chamber profile:

* the 300 s half-period was justified from the package's own transient thermal time constant
  (Phase 0I Sec. 7), not assumed;
* T_max is the architecture's own computed joint temperature, not a chamber setpoint;
* the mechanical drive is the global model's own corner displacement `du(t)`.

**The cycle is right for the product and wrong for the literature.** That is the correct
orientation to have — the alternative would be to deform the physics to match the available
data. What is missing is a life law calibrated on power cycling of a lead-free BGA at moderate
ΔT, and that is a data gap, not a modelling error.

**Duty cycle remains parameterised.** No workload statistics exist for the reference system, so
the number of OFF→ON→OFF cycles per unit time is not claimed; the mission sweep is expressed in
cycles, not in years.

## Consequence carried into the verdict

Even if a SAC305 law with full coefficients were obtained tomorrow, applying it to these results
would require either re-running on its calibration cycle — which the Norton validity window
partly forbids — or a justified acceleration relation. **Cycle incompatibility is therefore an
independent blocker on top of the coefficient blocker**, and both must be cleared before any
absolute lifetime can be quoted.
