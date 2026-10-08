# Phase 0K Sec. 2/3 — The robust G2 decision map

## Method

Every admitted absolute-life formulation is applied independently. No law is chosen.

| formulation | constant | Z1 | Z2 | Z4 |
|---|---|---|---|---|
| Syed Eq. 14, strain, double power law | C′ = 0.0468 | 2499 | 3206 | 2388 |
| Syed Eq. 16, strain, hyperbolic sine | C′ = 0.0513 | 2279 | 2925 | 2178 |
| Syed Eq. 15, energy, double power law | W′ = 0.0015 | 610 | 736 | 601 |
| Syed Eq. 17, energy, hyperbolic sine | W′ = 0.0019 | 482 | 581 | 474 |
| **envelope** | | **482 – 2499** | **581 – 3206** | **474 – 2388** |

Schubert 2003 is **excluded from this map and the exclusion is recorded**: it prints exponents
but no prefactor, so it yields relative life only and cannot vote on an absolute pass/fail.
Including a fifth absolute model could only widen the ambiguous band, never narrow it, so the
exclusion is conservative in the direction that matters.

## Regions

```
ROBUST ALL PASS        N_required <=   474
MODEL-FORM AMBIGUOUS     474 < N_required <= 3206      <-- a factor of 6.8
ROBUST ALL FAIL        N_required >   3206
```

**27.6 %** of the swept decade range (10² – 10⁵) is model-form ambiguous for at least one
architecture.

## The key question Sec. 3 poses

> Is there any `N_required` at which the current models **all** agree that Z1 fails and Z2 passes?

```
Z1 fails under EVERY law only when    N_required >  2499
Z2 passes under EVERY law only when   N_required <=  581
```

**The two conditions are DISJOINT: 581 < 2499.** Zero of 601 grid points classify as a robust
G2 reversal.

> ## NO. An experimental absolute-life calibration is NECESSARY before mechanics can alter the feasible architecture set.

The reason is structural rather than numerical. The **model-form spread within one architecture
is 5.2×**, while the **architecture separation is 1.21–1.38×**. A 5.2× uncertainty cannot
resolve a 1.3× effect, no matter what the requirement turns out to be. The relative result is
robust precisely because the spread cancels in a ratio — and that same cancellation means it
cannot be recovered by choosing a requirement.

## Why this withdraws "N_required is the sole blocker"

Phase 0J-R recorded the required life as the only thing standing between the project and a G2
decision. Formally tested, that is false. Take `N_required = 1500`, inside the ambiguous band:

| | strain family | energy family |
|---|---|---|
| Z1 | 2279–2499 → **PASS** | 482–610 → **FAIL** |
| Z2 | 2925–3206 → **PASS** | 581–736 → **FAIL** |

Both architectures pass under one admitted family and fail under the other. **Mission
definition alone produces no decision here.** The correct framing is:

> **TWO OPEN PIECES FOR ABSOLUTE G2**
> 1. the system mission / required life;
> 2. an absolute-life calibration, **or** a decision region demonstrably robust to the
>    model-form spread.

## What one calibration would change — and it is decisive

If a board-level test measured Z1's life at the operating cycle, both laws are forced through
that point, and each then extrapolates to Z2 and Z4 through its own metric ratio:

| | strain law | energy law | spread |
|---|---|---|---|
| Z1 | measured | measured | **0 %** |
| Z2 | 1.2400 × measured | 1.1665 × measured | **6.3 %** |
| Z4 | 0.9556 × measured | 0.9843 × measured | **3.0 %** |

**The ambiguous region vanishes.** Across 3721 (measured-life × required-life) cells, 0 %
remain ambiguous: 50.8 % all-pass, 47.6 % all-fail, **1.6 % a genuine G2 pass**.

The reason is that the three architectures sit within 6 % of each other in `w/ε`
(123.2 / 126.9 / 134.9 MPa), so **both laws extrapolate between them almost identically** even
though they disagree 4.1× on the absolute level. That is a fortunate property of this
comparison, not a general one, and it is exactly why the identifiability analysis matters: the
same calibration licenses **no** extrapolation to a *different cycle*, where the two laws
diverge by up to 85 %.

## Honest caveat on the width of the G2-pass band

Even after perfect calibration the robust G2-pass band is
`N_required ∈ (measured Z1 life, 1.1665 × measured Z1 life]` — a window only **17 % wide**,
using the conservative energy-law ratio. Z2's advantage changes feasibility only if the
requirement happens to land there. That is a property of a 1.2–1.4× advantage, and it is worth
stating plainly rather than discovering later.
