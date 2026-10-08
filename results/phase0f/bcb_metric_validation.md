# Phase-0F Sec.6 — Qualifying a Board-Mounted Mechanical Metric

## 1. Why a qualification step was required

Phase 0E showed that board restraint suppresses free warpage and converts deformation into
interface shear, and concluded that the discriminating response changes. It did **not**
establish that the replacement response is usable. Phase 0B/0C had already found interface
shear only marginally mesh-converged (8.7-9.3 % at the final refinement step) and
material-sensitive in its ordering. Using it for synthesis without a dedicated study would
have repeated exactly the mistake that interface peel caused.

So before any Phase-0F design conclusion is drawn in the mounted state, every candidate
metric is put through the same two tests.

## 2. Test design

Two configurations the free state separates strongly -- the thin and thick realizable
substrates at 1 kW -- are run under **BC-B** across:

* **convergence**: interface through-thickness elements = 1, 2, 4;
* **robustness**: nine material corners (reference, underfill E +/-30 %, underfill CTE
  +/-30 %, HVR E +/-30 %, HVR CTE +/-30 %).

A metric is QUALIFIED only if it (a) changes by <= 10 % between the two finest interface
meshes, (b) keeps the same thin/thick ordering in **all nine** corners, and (c) separates the
two configurations by more than 2 u_m = 1 % everywhere. Interface **peel is excluded
throughout** and remains demoted.

## 3. Results

| metric | convergence (finest two meshes) | ordering across 9 corners | min separation | verdict |
|---|---|---|---:|---|
| `die_warpage_pv_um` | thin:0.0%; thick:0.0% | stable | 72.31 % | **QUALIFIED** |
| `curvature_um_per_mm2` | thin:0.0%; thick:0.0% | stable | 60.18 % | **QUALIFIED** |
| `shear_p99_MPa` | thin:0.3%; thick:0.2% | stable | 2.83 % | **QUALIFIED** |
| `shear_p95_MPa` | thin:3.1%; thick:3.7% | stable | 13.30 % | **QUALIFIED** |
| `shear_raw_max_MPa` | thin:0.3%; thick:0.2% | stable | 1.18 % | **QUALIFIED** |
| `shear_excl050_p99_MPa` | thin:0.4%; thick:0.4% | stable | 2.82 % | **QUALIFIED** |
| `rel_disp_p99_um` | thin:0.0%; thick:0.0% | **UNSTABLE** | 4.71 % | **REJECTED** |
| `rel_disp_max_um` | thin:0.0%; thick:0.0% | stable | 2.58 % | **QUALIFIED** |
| `rel_disp_p95_um` | thin:0.0%; thick:0.0% | **UNSTABLE** | 3.63 % | **REJECTED** |

## 4. What this means

**7 of 9 candidate metrics qualify.** The two rejected are the p99 and p95
percentiles of relative interface displacement: both are extremely well converged (0.0 %) but
their thin/thick ordering **flips** between material corners, so they cannot carry a design
decision. Their maximum (`rel_disp_max_um`) does hold its ordering and qualifies.

The important result is the first row. **Free die warpage itself qualifies as a mounted
metric at 1 kW**, converging to 0.0 % and separating the two substrates by 72.3 % in the worst
corner. That is a change from Phase 0E, where at 240 W the thickness lever lost warpage
resolution entirely under BC-B (-56 % free became -0.14 % mounted, below the resolution
floor). The difference is scale: at 1 kW the free warpage is 11.2 um rather than 2.9 um, so
even after the board suppresses it the residual stays far above the numerical floor and keeps
its ordering.

Interface shear also qualifies, but by a much narrower margin -- 2.83 % minimum separation
against warpage's 72.3 %. It is reported, and it is not relied on where warpage is available.

## 5. Chosen metric for Phase-0F mounted results

**`die_warpage_pv_um` under BC-B**, with `curvature_um_per_mm2` (60.2 % separation) as the
corroborating quantity and `interface_shear_p99_MPa` reported alongside. This choice is made
before any Phase-0F mounted conclusion, not after seeing one.

## 6. Caveats

* The BC-B foundation is still **PROVISIONAL**: its stiffness has never been calibrated
  against a BGA unit cell or board data. Qualification shows the metric is well behaved under
  *this* foundation; a different stiffness would need re-qualification.
* The 9-corner study varies underfill and HVR properties. It does not vary the foundation
  stiffness itself, which is the largest single unknown in the mounted state.
* All of this is at 1 kW. The Phase-0E finding that warpage loses resolution under BC-B at
  240 W stands; the two are not in conflict, they are the same metric at different scales.

Artifacts: `bcb_metric_qualification.csv` (22 runs), `bcb_metric_verdicts.csv`.
Driver: `scripts/phase0f/run_bcb_qualify.py`, metric definitions in `scripts/phase0f/metrics0f.py`.
