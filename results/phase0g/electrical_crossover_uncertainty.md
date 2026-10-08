# Phase 0G Sec. 2/4 — Electrical thickness crossover: resolution, robustness, and the
# withdrawal of the ARCH_B interior optimum

## 1. What Phase 0F claimed and why it had to be audited

Phase 0F reported an interior electrical optimum for ARCH_B near `h_sub = 1.0 mm`, from five
sweep points whose decisive step was **+14.5 mW on a 125 W system**. Two independent reasons
made that claim unsafe to carry forward:

1. **Convergence resolution.** The Phase-0F ET loop converged `T_max` to 0.05 K. With
   `dP_conv/dT = 148 mW/K`, that tolerance alone admits about **7.4 mW** of error — half the
   effect being claimed.
2. **Curve decomposition.** Writing `P_total,B(h) = g(h) + P_TSV,B(h)`, the term `g(h)`
   (converter plus everything except the LV via field) falls only because the package runs
   cooler, over temperature steps of **0.038–0.093 K**.

Phase 0G therefore re-ran the sweep at 5× thickness resolution and a **25× tighter**
convergence tolerance (`tol = 0.002 K`, `max_it = 30`, RDL grid 161).

## 2. The tolerance audit did NOT dispose of the minimum

At `tol = 0.002 K` the ET fixed point converges to `dT_last = 3–4 × 10⁻⁴ K` in 5 iterations,
and the high-resolution sweep **reproduced the interior minimum at `h = 1.00 mm`**:

| h_sub (mm) | 0.80 | 0.90 | **1.00** | 1.10 | 1.20 | 1.50 | 2.00 |
|---|---|---|---|---|---|---|---|
| P_total (W), pre-fix | 125.0888 | 125.0789 | **125.0785** | 125.0827 | 125.0892 | 125.1154 | 125.1658 |

The minimum was therefore **not** a convergence artifact. It survived the exact test designed
to break it. This is recorded because it is the reason the defect below went undetected for
three phases: the obvious numerical explanation had been checked and eliminated.

## 3. What actually caused it — DEFECT #30

The minimum was a **unit-consistency defect**, not a numerical one.

`vertical_tier()` is evaluated with the **per-regulator** current and the **per-tile**
footprint, so its returned `p_w` is one regulator's via-field loss. `rdl_network_solve()` is
driven with all sources and the full load, so its `p_rdl` is the **whole system's** lateral
loss. Phases 0D-R, 0E and 0F summed the two directly. Every vertical tier was therefore
understated by a factor `n_vr` — **4× at 240 W and 49× at the 1 kW reference**.

The corrected evaluator expresses both system-wide (`scripts/phase0e/architecture0e.py`).
The fix is confirmed exactly against the pre-fix sweep:

| h_sub (mm) | 0.80 | 1.00 | 1.20 | 1.50 | 2.00 |
|---|---|---|---|---|---|
| P_TSV pre-fix (W) | 0.009189 | 0.032157 | 0.055122 | 0.089570 | 0.146981 |
| P_TSV corrected (W) | 0.450316 | 1.576089 | 2.702151 | 4.391938 | 7.210136 |
| ratio | 49.004 | 49.012 | 49.021 | 49.034 | 49.055 |

The ratio is `n_vr = 49` to four significant figures at every thickness, which is the
signature of exactly this defect and of no other. An independent hand check
(89.7768 mW/VR × 49 = 4.399 W) agrees with the corrected field loss.

## 4. Corrected ARCH_B: the interior optimum does not exist

With the via-field loss expressed system-wide, `P_TSV,B` rises from 0.450 W to 7.210 W across
the sweep — 16× — and swamps the sub-0.1 K thermal benefit that produced the old minimum:

| h_sub (mm) | 0.80 | 0.90 | 1.00 | 1.10 | 1.20 | 1.30 | 1.40 | 1.50 | 2.00 |
|---|---|---|---|---|---|---|---|---|---|
| P_total (W) | **125.611** | 126.168 | 126.735 | 127.306 | 127.880 | 128.455 | 129.031 | 129.608 | 132.497 |

The corrected curve is **monotonically increasing**. The optimum sits on the **thin
boundary** of the search interval, not in its interior.

### Robustness across corners

Nine corners spanning TSV current-density policy, crowding factor, allocation policy and
copper resistivity were evaluated (`electrical_crossover_summary.csv`):

| corner | h_opt (mm) | interior? | P(0.80 mm) → P(2.00 mm) (W) | penalty at 2.00 mm |
|---|---|---|---|---|
| nominal | 0.80 | No | 125.531 → 132.237 | 6.706 W |
| J_ectc_4e8 | 0.80 | No | 126.868 → 153.595 | 26.727 W |
| crowding_1.00 | 0.80 | No | 125.420 → 130.462 | 5.042 W |
| crowding_1.96 | 0.80 | No | 125.747 → 135.688 | 9.941 W |
| policy_B_geometric | 0.80 | No | 125.247 → 127.697 | 2.449 W |
| policy_C_area_optimal | 0.80 | No | 125.163 → 126.358 | 1.194 W |
| rho_cu_+10pct | 0.80 | No | 125.577 → 132.959 | 7.382 W |
| rho_cu_−10pct | 0.80 | No | 125.486 → 131.515 | 6.029 W |
| J_ectc_x_crowd_1.96 | 0.80 | No | 127.723 → 167.258 | 39.535 W |

**`interior = False` in 9 corners of 9.** The boundary optimum is not corner-dependent; the
corners change only how steeply the penalty grows. The ARCH_B interior optimum is
**WITHDRAWN**, and with it the premise that an electrical crossover exists for ARCH_B to
trade against a mechanical preference.

## 5. Corrected ARCH_A: a real but negligible interior optimum

ARCH_A carries no LV via field of consequence (`P_TSV` 0.010 → 0.163 W across the sweep), so
the sub-0.1 K thermal benefit is not swamped and a genuine interior minimum survives at
**`h = 0.90 mm`**:

| h_sub (mm) | 0.80 | **0.90** | 1.00 | 1.10 | 1.20 | 1.50 | 2.00 |
|---|---|---|---|---|---|---|---|
| P_total (W) | 125.15827 | **125.14963** | 125.15057 | 125.15598 | 125.16382 | 125.19387 | 125.25079 |

### Numerical floor on the difference

The uncertainty is quantified **on the difference**, which is what the claim rests on, not on
the absolute power:

| contribution | magnitude | as power |
|---|---|---|
| fixed-point residual | `dT_last ≤ 4 × 10⁻⁴ K` × 148 mW/K | 0.0592 mW |
| energy-balance residual | `≤ 3.07 × 10⁻⁵ %` of 125.15 W | 0.0385 mW |
| **combined floor** | | **0.0977 mW** |

| Δ from the minimum | value | multiples of the floor | verdict |
|---|---|---|---|
| h = 1.00 mm | +0.937 mW | 9.6× | RESOLVED |
| h = 0.80 mm | +8.634 mW | 88.4× | RESOLVED |
| h = 1.10 mm | +6.353 mW | 65.1× | RESOLVED |
| h = 2.00 mm | +101.154 mW | 1036× | RESOLVED |

The ARCH_A minimum is therefore **numerically resolved** — the tightest comparison, against
`h = 1.00 mm`, still stands at 9.6× the floor.

### But it is not a design lever

The optimum is **8.6 mW deep** against the thin boundary on a **125 W** electrical budget:
**0.0069 %**. It is resolved by the solver and irrelevant to the design. No component
tolerance, no assembly tolerance and no measurement in this project resolves 0.0069 %, and
the ARCH_A/ARCH_B architecture gap at the same thickness (125.16 W vs 125.61 W, 0.45 W) is
**52× larger** than the entire depth of the ARCH_A optimum.

## 6. Consequences

1. **The ARCH_B interior electrical optimum near 1.0 mm is withdrawn** (defect, not noise).
2. **ARCH_B prefers the thin boundary monotonically, in all 9 corners.**
3. **ARCH_A retains a resolved interior optimum at 0.90 mm that is too shallow to act on.**
4. Phase 0F's architecture comparison at fixed thickness inherits the same 49× error and is
   **re-derived, not reused**, wherever it appears downstream.
5. The ETM thickness tension **survives, with its ordinary sign**. Electrically thinner is
   better (this section); mechanically thicker is better under the free package **and under
   every explicit board in the calibrated envelope** (Sec. 7, `S_h` = −0.039 to −0.886). What
   Phase 0F reported was different and stronger — that *mounting reverses* the mechanical
   preference, so that the assembly state decides the direction of the trade. Sec. 6/7 shows
   no physically constructed assembly does that; only the compact clamped foundation does.
   The tension is therefore the conventional thin-versus-thick one, present free or mounted,
   and **not** an assembly-state-dependent reversal.
