# Phase 0K Sec. 9/10/11/29 — Absolute-life model identifiability

## The algebra, before any simulation

```
strain law   N = 1/(C·ε_acc)            energy law   N = 1/(W·w_acc)
```

**One condition cannot discriminate them.** One measured life supplies one equation and each law
has exactly one free constant, so both fit it exactly:

| hypothetical measured Z1 life | `C_fit` | `W_fit` | residual |
|---|---|---|---|
| 800 | 0.14168 | 0.00112 | **both exact** |
| 1500 | 0.07556 | 0.00060 | **both exact** |
| 3000 | 0.03778 | 0.00030 | **both exact** |

Residual degrees of freedom for discrimination: **zero**. A single condition re-labels the
disagreement as two different constants. It does not resolve model form.

**With two conditions A and B** the laws predict *different* ratios between them:

```
strain:  N_A/N_B = ε_B/ε_A          energy:  N_A/N_B = w_B/w_A

DISCRIMINATION POWER   D = (ε_B/ε_A)/(w_B/w_A) = (w/ε)_A / (w/ε)_B
```

**So an experiment discriminates only to the extent that its two conditions differ in `w/ε`.**
Maximising damage is irrelevant. Maximising the spread in `w/ε` is the entire design problem.
This is the analytic reason the Phase-0J-R claim that "one board-level test would fix the
constant and make every relative result absolute" needed auditing — it is half right, and the
half that is wrong matters.

## Sec. 9 — auditing the "one test is sufficient" claim

| what one condition at the operating cycle **does** | what it **does not** |
|---|---|
| fixes the absolute level for Z1 exactly | identify which law is correct |
| fixes Z2 to within **6.3 %** and Z4 to within **3.0 %**, under *either* law | license extrapolation to a **different cycle** |
| collapses the ambiguous G2 region to **zero** | resolve the 4.1× model-form disagreement |
| validates the Z2/Z1 relative claim directly if both are tested | say anything about field conditions unlike the test |

The first column is stronger than expected and the second is the limitation. Both are reported.

## Sec. 10/11 — candidate conditions, ranked by discrimination

`w/ε` was computed for eight candidate board-level profiles, on the graded Syed-matched mesh,
at the stabilised cycle (`experiment_condition_metrics.csv`). The imposed displacement is scaled
linearly with ΔT from the global-model operating point — a first-order CTE-mismatch model,
declared as an assumption.

| condition | T range (°C) | dwell | ΔT | **w/ε (MPa)** |
|---|---|---|---|---|
| **COLD_SHALLOW** | −40 / +25 | 300 s | 65 | **209.2** |
| SHORT_DWELL | 25 / 82.9 | 30 s | 57.9 | 142.5 |
| WIDE_HOT | 25 / 125 | 300 s | 100 | 142.8 |
| OP_BASELINE | 25 / 82.9 | 300 s | 57.9 | 126.9 |
| LONG_DWELL | 25 / 82.9 | 900 s | 57.9 | 124.5 |
| SMALL_DT | 25 / 55 | 300 s | 30 | 118.0 |
| **HOT_SHALLOW** | +55 / +125 | 300 s | 70 | **113.1** |

The physics is clear and exploitable: **`w/ε` is set by the stress the creep law sees, and the
overstress `σ − σ_y(T)` is largest at low temperature where the yield stress is high.** A cold
half-range cycle and a hot half-range cycle at nearly the same ΔT therefore sit at opposite ends
of the `w/ε` axis. Dwell moves it only 14 %; ΔT alone moves it 21 %; **temperature range moves
it 85 %**.

## Best pairs

| pair | D | laws differ by | σ (β = 6, n = 16) | σ (β = 11, n = 16) |
|---|---|---|---|---|
| **COLD_SHALLOW vs HOT_SHALLOW** | **1.849** | **84.9 %** | **6.19** | **7.13** |
| COLD_SHALLOW vs SMALL_DT | 1.773 | 77.3 % | 5.77 | 6.64 |
| COLD_SHALLOW vs LONG_DWELL | 1.680 | 68.0 % | 5.22 | 6.01 |
| OP_BASELINE vs COLD_SHALLOW | 1.649 | 64.8 % | 5.03 | 5.80 |
| HOT_SHALLOW vs SHORT_DWELL | 1.260 | 26.0 % | 2.33 | 2.68 |
| **two ARCHITECTURES at one profile** | **1.063** | **6.3 %** | **< 1** | **< 1** |
| one architecture, two dwells (30 s vs 900 s) | 1.144 | 14.4 % | 1.4 | 1.6 |

**Two architectures at one profile is nearly blind to model form.** It validates the relative
claim — which is valuable and is recommended for that reason — but it cannot identify the law,
because Z1 and Z2 differ by only 6 % in `w/ε`.

## Sec. 29 — the minimum experimentally identifiable design

> **TWO TEST CONDITIONS, chosen to span `w/ε`, on at least ONE architecture.**
> A cold half-range cycle (−40/+25 °C) and a hot half-range cycle (+55/+125 °C) give
> **D = 1.85**, an **85 %** separation between the two laws' predicted life ratios, resolvable at
> **6.2σ** with 16 specimens per cell even at the pessimistic Weibull slope β = 6.

Adding the second architecture at both conditions costs two more cells and buys the direct
relative-life validation (Sec. 17), which no single-architecture design can provide.

**Recommended: 2 architectures × 2 conditions = 4 cells.**

## Statistical model used

Weibull MLE large-sample result, `SE(ln η) ≈ 1/(β√n)`; for a ratio of two conditions
`SE(ln ratio) = √2/(β√n)`. Simulation uncertainty on the *predicted* metric ratio is carried
separately at **8 %** — larger than the 6.2 pp Phase 0I-R measured under paired perturbations,
because across different **temperature** conditions the material-property errors do not fully
cancel. That 8 % is a stated assumption and it is the binding term:

| | n = 8 | n = 16 | n = 32 |
|---|---|---|---|
| β = 6 | 5.32σ | 6.19σ | 6.82σ |
| β = 11 | 6.68σ | 7.13σ | 7.39σ |

Minimum n per condition for 3σ at β = 6: **4**. The ceiling set by simulation uncertainty alone
is **7.7σ**, so **specimens beyond ~16 per cell buy almost nothing** — the limit is the model,
not the sample.

## Sec. 18 — is Z4 worth fabricating? No.

| | value of including Z4 |
|---|---|
| discriminate life-law families | **no** — `w/ε` = 123.2 vs Z1's 126.9, D = 1.03, negligible |
| validate a distinct mechanical regime | **no** — same joint, same cycle, same stress regime |
| resolve a publication-critical point | **no** — Z4/Z1 = 0.956–0.984 sits *inside* the 6.3 % post-calibration model spread, so the experiment could not distinguish Z4 from Z1 even if run |
| electrical ranking | Z1 vs Z4 is unresolved at 0.14σ and a life test does not address that |

**Recommendation: do not fabricate Z4.** Spend the specimens on the Z1/Z2 cold and hot cells,
where they buy both discrimination and relative validation.
