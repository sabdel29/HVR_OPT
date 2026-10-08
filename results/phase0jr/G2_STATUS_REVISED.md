# Phase 0J-R Sec. 27 — G2 status, revised

```
G2 :  g_reliability(x) = N_required / N_f(x) − 1 ≤ 0        and the constraint must
                                                             change the feasible set
```

## Status: **STILL NOT TESTED** — but for one reason now, not two

| requirement | Phase 0J | **Phase 0J-R** |
|---|---|---|
| 1. a defensible predicted fatigue life `N_f(x)` | **NOT MET** — 0 of 10 laws admissible, reproduction impossible | **PARTIALLY MET** — four primary-source laws admitted for **relative** life, reproduction **passed** on declared tolerances, averaging volume **matched**. Absolute life remains conditional. |
| 2. a defensible required life `N_required` | **NOT MET** | **NOT MET — unchanged.** No field mission requirement exists in any source, and none was invented. |
| 3. one attractive candidate fails while another passes | NOT EVALUABLE | **NOT EVALUABLE** — requires 2 |
| 4. the ranking survives uncertainty | MET at metric level | **MET, and strengthened** — Z2/Z1 = 1.21–1.38 across two authors, two alloy variants, two metric families and a 30× dwell range |

**Requirement 2 is now the sole blocker.** Phase 0J could not evaluate G2 because both halves of
the inequality were missing. Phase 0J-R has built the left half to the point where a *relative*
statement is defensible and an *absolute* one is conditional. The right half is unchanged and
**cannot** be supplied by physics or literature — it must come from the system owner
(`MISSION_INPUT_TEMPLATE.md`).

## What Phase 0J-R DOES establish, which Sec. 27 explicitly permits

> **ARCHITECTURE-DEPENDENT RELATIVE FATIGUE LIFE.**

Established, with primary-source calibration, matched averaging volume and reproduced source
validation:

| | Z2 vs Z1 | Z4 vs Z1 |
|---|---|---|
| Syed corrected, strain (Eq. 14) | **1.283×** | 0.956× |
| Syed corrected, energy (Eq. 15) | 1.206× | 0.984× |
| Schubert, strain (slope 1.3) | 1.383× | 0.943× |
| Schubert, energy (slope 1.0) | 1.206× | 0.984× |
| **range** | **1.21 – 1.38** | **0.94 – 0.98** |

**Z2 lives 21–38 % longer than Z1. Z4 lives 2–6 % shorter than Z1 — a difference that is not
resolved and should not be claimed.**

## Why G2 cannot be passed by asserting a threshold

Sec. 24 of Phase 0J and Sec. 27 here both forbid it, and the arithmetic shows why it would be
meaningless. The two admitted Syed models put the absolute life at **2499** and **610** cycles
for Z1 — a 4.1× spread. Any `N_required` between those two numbers would flip the verdict purely
on the choice of metric family. Until either the spread is closed or a requirement is declared
by someone with authority over the product, a pass/fail is not a scientific statement.

## Conditions for G2 to become testable

1. `N_required` from the system owner, in joint thermal cycles — **the blocker**.
2. Ideally, one measured life for this joint at one condition, which would collapse the 4.1×
   model-form spread and make the absolute prediction defensible.

Item 1 alone would permit a **relative** feasibility statement (which architectures are ordered
where, and whether the ordering matters at that threshold). Items 1 and 2 together would permit
a full G2 pass/fail.
