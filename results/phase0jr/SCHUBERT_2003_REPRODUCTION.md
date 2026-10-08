# Phase 0J-R Sec. 13 — Schubert 2003: reproduction attempted

## What the paper provides

| item | value |
|---|---|
| alloy | **Sn95.5Ag3.8Cu0.7 (SAC387)** vs Sn59Pb40Ag1 |
| packages | flip-chip on board ± underfill; PBGA 256 / 272 / 313 / 316, 1.27 mm pitch |
| cycles | −55/+125 °C and −55/+150 °C, 30 min total, **10 min dwells, 5 min ramps**; plus literature data at −40/+125 °C, 60 min |
| constitutive | creep with **primary + secondary** parts, fitted to 108 creep data points |
| **strain model** (Eq. 5) | `N_f = θ1·(ε_acc^cr)^−θ2` |
| **energy model** (Eq. 6) | `N_f = θ3·(ΔW_cr)^−θ4` |
| **metric definition** | *"the actual minimum (or average) over the path of local maximum equivalent creep strain"* — a **band of local maxima crossing the joint**, NOT a fixed-thickness interface layer |
| **exponents, printed in the text** | SnAgCu: **1.3 (strain)**, **1.0 (energy)**. SnPb(Ag): 1.80 and 1.20 |
| **prefactors θ1, θ3** | **NOT PRINTED ANYWHERE.** They exist only as fitted lines in Figures 7 and 8. |
| dataset | best-fit through **14 experiments** |

## Reproduction: attempted, and the outcome

**Absolute life: NOT REPRODUCIBLE.** The prefactors are not in the text, not in a table, and not
in the figure captions. Figures 7 and 8 are log-log scatter plots whose data points and fitted
lines are raster content; the axis tick labels are the only numeric text extractable, and no
individual (life, strain) pair is recoverable. Sec. 8 permits digitisation with a declared
uncertainty, but here **there is nothing reliable to digitise** — the two alloys' point clouds
overlap and the fitted lines are not annotated with equations. Digitisation was therefore **not
performed**, and that is recorded rather than the uncertainty being invented.

**Relative life: REPRODUCIBLE, and it is the more useful half.** The exponent alone determines
a life ratio:

```
N_f,2 / N_f,1 = (ε_1 / ε_2)^1.3          strain
N_f,2 / N_f,1 = (w_1 / w_2)^1.0          energy
```

Applied to our M4 and M5 on the Syed-matched extraction:

| | Z2/Z1 | Z4/Z1 |
|---|---|---|
| Schubert strain, exponent 1.3 | **1.383** | 0.943 |
| Schubert energy, exponent 1.0 | **1.206** | 0.984 |

## Value of this branch

Schubert is a genuinely **independent** check on Syed: a different laboratory, a different
SnAgCu composition (SAC387 vs SAC405/395), a different constitutive model (primary + secondary
creep vs double power law), a different spatial definition (band of local maxima vs 25 µm
layers), and a different exponent (1.3 vs 1.0).

**It agrees.** Z2/Z1 = 1.21–1.38 spans both authors. A relative result that survives that much
methodological variation is the strongest statement Phase 0J-R can make.

Note also the exponent difference is itself informative: Syed derives −1 *theoretically* from
Monkman–Grant plus a time-fraction rule, and measures −0.9607; Schubert fits −1.3 empirically.
The two bracket the physical exponent for SnAgCu accumulated creep strain, and the bracket is
narrow — far narrower than the m = 1.5–3 range Phase 0I once assumed and Phase 0I-R withdrew as
unsourced.

## Caveats carried forward

* **SAC387, not SAC305.** Same family, higher Ag.
* The spatial definition is not ours and not Syed's. Because only the exponent is used, the
  prefactor's dependence on that definition **cancels in a ratio** — which is precisely why the
  relative result is usable and the absolute one is not.
* Schubert's own summary notes a SnAgCu/SnPb crossover and warns that relative alloy performance
  depends on strain level; that caution applies to alloy comparisons, not to our
  architecture-to-architecture comparison at fixed alloy.
