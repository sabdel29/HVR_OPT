# M1 implementation audit

**Phase 0L-R, Part 8.** M1 removes the yield threshold so that the solver consumes the same
stress quantity the card was fitted in. That repairs a *variable* inconsistency. It does not
make the model physically valid, and this audit separates the two.

## 1. How zero yield is actually implemented

`scripts/phase0l/replay.py :: material()` writes, for every card temperature:

```
*PLASTIC
1.E-6, 0.0,  <T>
1.E-6, 0.02, <T>
```

so the yield surface is **flat at 1e-6 MPa**, not absent. Verified in the built deck
`results/phase0l/wd/M1_Z1_BASE.inp`: 36 rows of `1.E-6` and exactly one `*PLASTIC` keyword.

## 2. Is DEFECT #43 avoided? — YES

DEFECT #43: omitting `*PLASTIC` does **not** give a zero yield surface. It routes
`incplas.f:130` through `user_hardening = 1`, which calls `uhardening()`, whose shipped body is
an empty `RETURN` that never assigns `fiso` — a variable `incplas.f` never initialises. The
yield stress is then whatever the stack held.

M1 keeps an explicit `*PLASTIC` card, so `nplicon(1,imat) >= 1`, `plconloc(801) >= 1.5 > 0.8`,
and `user_hardening` stays 0. The undefined path is never entered. **The implementation is
explicit and deterministic, which is exactly what DEFECT #43 requires.**

## 3. Is the residual 1e-6 MPa threshold immaterial? — YES, to 1e-9

Direct test: the production Z1 baseline deck was re-run with every yield row changed from
1e-6 MPa to 1e-9 MPa, nothing else altered.

| | Δ PEEQ per cycle | W_in (MJ/m³) |
|---|---|---|
| σ_y = 1e-6 MPa (production M1) | 0.011645818 | 1.1797822 |
| σ_y = 1e-9 MPa (reference) | 0.011645818 | 1.1797822 |
| relative difference | **6.1e-9** | **1.1e-9** |

The residual threshold changes nothing. M1 is a true zero-yield model in every respect that
affects a result. A creep-only deck with `*PLASTIC` genuinely removed was **deliberately not
run** as the reference, because that is the undefined path of DEFECT #43; the 1e-9 MPa card is
the safe equivalent, and the single-element probe of Phase 0L (TEST A) already showed the two
routes agreeing to a median 3e-6 where the undefined path happened to read zero.

## 4. PEEQ semantics — unchanged

`incplas.f:516` sets `ep = epini + sqrt(2/3)·cop`, and `cop` is the single consistency parameter
carrying the whole inelastic increment. Removing the threshold changes *when* `cop` is non-zero,
not what PEEQ means. PEEQ remains the monotone accumulated equivalent inelastic strain, so M1
and M0 metrics are the same quantity and are directly comparable.

## 5. Does M1 create creep where it should not?

With no threshold the law is active at every stress, so the question is whether it produces
non-physical creep at low stress. It does not, because the power law suppresses itself: at
80 °C, A = 2.72e-17 and n = 8.19 give

| σ (MPa) | ε̇ (1/s) | strain in a 300 s dwell |
|---|---|---|
| 1 | 2.7e-17 | 8e-15 |
| 5 | 1.4e-11 | 4e-9 |
| 10 | 4.2e-9 | 1e-6 |

Nothing meaningful accumulates below about 10 MPa, and only 0.2 % of the joint's per-cycle
damage occurs below 16 MPa (`high_stress_damage_fraction.csv`). Removing the threshold therefore
did not invent a new low-stress damage mechanism; it removed an artificial floor that had been
suppressing creep in the regime where the source data were actually measured.

## 6. What M1 is, and what it must be called

M1 is **not** a corrected SAC305 model. Its parameters come from 19 steady-state creep points
measured on **Sn3.9Ag0.6Cu** (Xiao & Armstrong 2005, via Yuan 2023 Table 5), fitted over
7.51–15.92 MPa, and the package accumulates 99.8 % of its damage above that window.

> **Required label: "variable-consistent SnAgCu Norton surrogate, high-stress extrapolative."**

What M1 fixed: the fit variable now equals the solver variable, so the card reproduces its own
19 source points (worst 1.15×) instead of 0 of 19.

What M1 did **not** fix: the alloy is still wrong, and the stress domain is still extrapolated
by a factor of about 5 at the damage-weighted median.

## 7. Numerical standing

M1 integrates stably at the production exponents (n = 5.1–8.3). Phase 0L-R established that
this solver's viscoplastic integrator fails above **n ≈ 9–10** in this joint model
(`PHASE0LR_CONSTITUTIVE_AND_REPORT_CLOSURE.md`, Part 9), so M1 sits just inside the integrable
band and M1_NHI (n up to 9.4) needs the tightened start to converge at all.
