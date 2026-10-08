# Phase 0K-R Sec. 12/22/23 — Three pieces of loose wording, corrected

## Sec. 12 — "6.19 sigma" is not a sigma

Phase 0K reported the original pair as **D = 1.849, 85 % separation, 6.19 σ**. Audited, that
number is

```
Z = ln(D) / sqrt[ 2/(beta^2 n)  +  sigma_sim^2 ]
```

with β = 6, n = 16, σ_sim = 0.08. What it **does** contain: Weibull life scatter through
β and n, and a stated simulation uncertainty on the predicted metric ratio.

What it does **not** contain, and Sec. 12 requires be said:

| omitted | why it matters |
|---|---|
| uncertainty in **β itself** | β was assumed, not estimated, and the assumed value is now shown to be the 25th percentile |
| uncertainty in the **life-law constants** `C′`, `W′` | they cancel in a *ratio between conditions*, so this omission is defensible — and it is the reason a ratio was chosen as the statistic |
| **censoring** loss | cells that do not reach 63 % failures carry less information than n implies |
| **model-form spread** | the 4.1× strain-vs-energy disagreement is the thing being tested, not an error term — correctly excluded |
| **constitutive-domain error** | the predicted `D` itself comes from a model evaluated 3–7× outside its fitted stress window |

**It is therefore an EXPECTED DISCRIMINATION Z-SCORE under a stated error budget, not a
measured standard deviation.** Renamed accordingly everywhere; "σ" is no longer used for it.

Recomputed for the **revised** pair at the **source-backed worst** β = 5.1 and n = 16:

```
SE_experimental = sqrt(2)/(5.1 * sqrt(16)) = 0.0693
SE_simulation                              = 0.0800
SE_total                                   = 0.1059
Z = ln(1.4395) / 0.1059                    = 3.44
```

## Sec. 22 — "the robust G2 band is 17 % wide"

Vague, and the denominator was never stated. Expressed directly instead.

After a package-specific calibration at one condition, both laws pass through the measured Z1
life `N₁`, and Z2 follows through each law's own metric ratio. Writing `R_min` for the smaller
of the two predicted ratios, a robust Z1-fail / Z2-pass decision requires

```
N_f,Z1  <  N_required  <=  R_min  x  N_f,Z1
```

At the Phase-0J-R reference condition `R_min = 1.1665` (energy law; strain gives 1.2400):

| | value |
|---|---|
| **relative window** | `N_required / N₁` ∈ **(1.000, 1.1665]** |
| **width as a fraction of N₁** | **16.65 %** — this is the denominator: the measured Z1 life |
| **log-space width** | log₁₀(1.1665) = **0.0669 decades** |
| **absolute window, if N₁ were 2000 cycles** | (2000, 2333] cycles — **333 cycles wide** |

The "17 %" was `R_min − 1` expressed as a percentage of `N₁`. Correct, but it must be written
with the denominator attached.

## Sec. 23 — "27.6 % of the range"

Phase 0K reported the model-form ambiguous interval **474 – 3206 cycles** as "27.6 % of the
swept range". That figure is **logarithmic** and must say so.

```
log10(3206/474) = 0.830 decades
swept range     = 10^2 to 10^5 = 3.000 decades
0.830 / 3.000   = 27.6 %
```

**Corrected wording, adopted everywhere:**

> "The ambiguous interval spans approximately **0.83 decades** — about **27.6 % of the
> three-decade 100–100 000-cycle logarithmic sweep**."

For contrast, as a *linear* fraction of the same range it would be
(3206 − 474)/(100 000 − 100) = **2.7 %**, an order of magnitude smaller and thoroughly
misleading. The linear figure is not used.

## Sec. 19 — "one experiment"

Frozen terminology, applied throughout:

| term | meaning |
|---|---|
| **ONE CONDITION** | one thermal profile |
| **ONE CELL** | one architecture × one thermal profile |
| **ONE CAMPAIGN** | the complete multi-cell experiment |

And the statement it disambiguates:

> **A single thermal-cycle CONDITION cannot identify the fatigue-law family** — one measured
> life is one equation and each law has one free constant, so both fit it exactly.
> **A multi-condition CAMPAIGN can** — two conditions spanning `w/ε` separate the two laws'
> predicted life ratios by 44 %.
