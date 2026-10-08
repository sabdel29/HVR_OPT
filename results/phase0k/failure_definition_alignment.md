# Phase 0K Sec. 14 — Failure definition alignment

## What the calibration sources actually define as failure

| source | endpoint | statistic the model predicts |
|---|---|---|
| **Syed 2004** (the admitted calibration) | in-situ resistance exceeding **300 Ω**, confirmed by **ten further events within 10 % of the time of first failure**, with manual confirmation within a week | **MEAN life**, explicitly — the paper states the models predict mean life, not characteristic life, and gives the Gamma-function conversion to η using β |
| Schubert 2003 | not stated in the retrieved text beyond "characteristic life" | **characteristic life (η)** |
| Darveaux 2000 | measured **crack length** by cross-section, correlated to `N_0` (initiation) and `da/dN` (growth); `N_f = N_0 + a/(da/dN)` | crack-based, converted to characteristic life |

## The alignment requirement, and what it rules out

Syed's constants were regressed against **mean life measured by a 300 Ω resistance threshold**.
Any calibration experiment must therefore reproduce **both halves** of that definition:

* **the endpoint** — a resistance threshold with a confirmation rule, monitored **in situ**, not
  a post-test cross-section and not a "50 % resistance increase" criterion;
* **the statistic** — **mean life**, or a distribution from which mean life can be computed.

Two mismatches that would silently invalidate the calibration:

1. **Calibrating a 50 %-resistance-increase endpoint against Syed's constants.** A 50 % rise
   occurs substantially earlier than a 300 Ω open. Mixing them would attribute a real crack-growth
   difference to the fitted constant. Sec. 14 forbids it, and it is not done.
2. **Calibrating characteristic life η against a mean-life model.** For β ≈ 11 the mean is about
   **4.5 % below** η; for β = 6 about **7.5 % below**. Small, but it is a systematic bias in the
   direction of over-predicting life, and it is free to remove — so the proposed test records
   the full distribution and converts explicitly.

## Specified endpoint for the proposed experiment

> **In-situ continuity monitoring of a daisy chain, event threshold > 300 Ω, confirmed by ten
> further threshold events within 10 % of the time of first event.** Identical to Syed's rule,
> because the constants being calibrated are his.

Recorded per specimen: time and cycle of first event, all confirmation events, and continued
monitoring after first failure so that later failures in the same daisy chain are captured.

**Reported statistic: mean life**, computed from a fitted 2-parameter Weibull as
`mean = η·Γ(1 + 1/β)`, with η and β both estimated rather than assumed, and with the conversion
stated explicitly so the comparison to Syed is auditable.

## Cross-check available at no extra cost

Because Darveaux's framework is crack-based and Syed's is resistance-based, a **destructive
cross-section of a small number of survivors and failures** at the end of the test would let the
crack fraction be compared against the resistance endpoint. This is not required for the
calibration and is not counted in the specimen budget, but it is cheap and it is the only way to
check that the electrical endpoint corresponds to the crack state the mechanics model computes.
