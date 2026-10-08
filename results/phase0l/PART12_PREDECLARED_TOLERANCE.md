# Part XII — predeclared common-mode-cancellation tolerance

**Declared 2026-09-14T22:42:00Z UTC, BEFORE any Z2/Z1 ratio was computed under any alternative constitutive
model.** At the time of writing, the only Z2/Z1 numbers in existence are the Phase-0K-R values
(1.21–1.38) produced under the single pre-0L Norton card. No replay (Part XI) has been run.

## The quantity under test

For each admissible constitutive model $m$ and each response metric $M$
(creep strain, inelastic energy, native fatigue metric, relative life where transferable):

$$ r_m = M_{Z2}(m) \; / \; M_{Z1}(m) $$

The **model-form spread** is

$$ S = \frac{\max_m r_m - \min_m r_m}{\mathrm{median}_m \, r_m} $$

## The architecture effect it is measured against

The Phase-0K-R architecture effect is $\bar r = 1.21$–$1.38$, i.e. an excess over unity of
21 % to 38 %. The conservative (smallest) architecture effect is therefore

$$ E_{\min} = 0.21 . $$

## Predeclared thresholds

| Classification | Condition |
|---|---|
| **ROBUST COMMON-MODE CANCELLATION** | $S \le 0.25\,E_{\min} = 0.0525$ **and** every $r_m > 1$ |
| **PARTIAL CANCELLATION** | $0.0525 < S \le 1.00\,E_{\min} = 0.21$ **and** every $r_m > 1$ |
| **RELATIVE-LIFE RESULT MODEL-FORM DEPENDENT** | $S > 0.21$ **or** any $r_m \le 1$ |

## Justification of the thresholds

The claim under test is that the architecture ranking is a physical result rather than an
artifact of the constitutive extrapolation. A spread that is a quarter of the smallest
architecture effect leaves the effect resolvable by a factor of four against model-form noise,
which is the usual bar for calling a difference "not explained by" a nuisance term — it is the
same 4:1 signal-to-nuisance ratio the project already applies when separating mesh error from
architecture effect. That fixes the ROBUST boundary at $S \le 0.0525$.

Above that, the effect is still directionally intact but is no longer cleanly separable from
model form, which is exactly what "partial" should mean; the effect survives but its magnitude
is not defensible. Once the spread equals or exceeds the whole architecture effect
($S > 0.21$), a different admissible model could in principle reorder the architectures, so
the relative-life claim is model-form dependent regardless of which way the medians happen to
fall.

The **sign condition** ($r_m > 1$ for every model) is separate from the spread condition and
is decisive on its own: a single admissible model that reverses the ranking makes the result
model-form dependent no matter how tight the spread is, because the claim being defended is an
ordering, not a magnitude.

## Commitments

- The threshold set above is frozen. It will not be revised after results are seen.
- If the outcome lands near a boundary, the classification follows the inequality as written;
  the boundary will not be moved to accommodate the result.
- $S$ is computed over the admissible model set fixed by Part X, not over a subset chosen
  after inspecting the ratios.
