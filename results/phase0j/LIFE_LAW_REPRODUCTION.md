# Phase 0J Sec. 8 — Reproduction of the source calibration: attempted, and why it failed

## What Sec. 8 requires

> Before applying it to Z1/Z2/Z4: reproduce the source paper's life prediction or calibration
> points… Require a documented reproduction tolerance. **If the published formula cannot
> reproduce its own data: do not use it.**

**Declared before attempting:** reproduction tolerance **±25 % on N_f**, matching the accuracy
the Syed and Darveaux families claim for themselves.

## Result: the gate is not passed, for a reason one step earlier than Sec. 8 anticipates

Sec. 8 anticipates a formula that *fails* to reproduce its data. What happened instead is that
**the data cannot be reached at all**. Reproduction was attempted for every candidate with a
usable form and abandoned only after the access route was exhausted:

| candidate | primary source | access outcome |
|---|---|---|
| **Syed 2004** | 10.1109/ectc.2004.1319419 | IEEE Xplore **HTTP 202** (paywall interstitial); Unpaywall `is_oa=false`; Semantic Scholar `openAccessPdf=null`; 0 of 139 open-access citing papers reprint the calibration points |
| **Schubert 2003** | 10.1109/ectc.2003.1216343 | IEEE Xplore paywall; `is_oa=false`; cited by 8 retrieved sources, coefficients reprinted by **none** |
| **Darveaux 2002** | 10.1115/1.1413764 | ASME **HTTP 403**; `is_oa=false`; no SAC305 `K1`–`K4` in any accessible source |

No paywall was circumvented. Where a primary could not be read, what is recorded is another
paper's description of it, attributed to that paper — the same discipline Phase 0H applied to
the JEDEC standards.

## What *was* reproducible, and what it establishes

The **model forms** were recovered verbatim from an open-access review retrieved in full
(Yu et al. 2026, *Eng. Res. Express* 8:132401), including the Syed SnAgCu constants
`C_I = 0.013`, `C_II = 0.036`, and the Darveaux methodology requirement was recovered verbatim
from a retrieved IMAPS paper. That is enough to **classify** the laws and to establish that
their metrics are not ours. It is not enough to **validate** any of them.

Two consequences follow, and both are load-bearing for the verdict:

1. **No absolute lifetime in this phase can be called validated.** Sec. 40 forbids calling a
   prediction validated because the solver converged; it is equally forbidden to call one
   validated because the arithmetic of an unverified formula was carried out correctly.
2. **The conditional numbers that Sec. 17–19 do report carry this status in every row.**
   `lifetime_by_law_and_architecture.csv` records
   `applicability_status = CONDITIONAL … NOT A VALIDATED LIFETIME` on every line.

## The one quantity this blocker does not touch

For a law of the Syed inverse-linear form `N_f = (C·ε_acc)^−1`:

```
N_f,2 / N_f,1  =  ε_acc,1 / ε_acc,2          C cancels, and there is NO exponent to assume
```

Unlike the Coffin-Manson family — where Phase 0I-R showed the ratio spans a factor of 7.4 over a
plausible exponent range — **the Syed form leaves no free parameter in a life ratio at all.** So
while no absolute life is defensible, the *relative* statement

> Z2 lives **1.558×** as long as Z1, and Z4 **0.890×** as long,
> **conditional on the Syed form being the right form**

rests only on the metric ratio, which is a model output resolved at 5.8× its paired-perturbation
spread. The conditionality is entirely in the choice of **form**, not in any fitted number.

`life_law_reproduction.csv` records the attempt, the blocker and the verdict per candidate.
