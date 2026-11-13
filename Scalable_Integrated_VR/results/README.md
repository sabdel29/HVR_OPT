# `results/` — generated artifacts and their provenance

Every file here is **reproducible output**, not source. Scripts write to the current working
directory, so after a run the new files land at the repo root and need moving back in here.

```
figures/  19 PNG plots
matlab/   MATLAB figures (.fig), exported data (.mat), companion plot scripts (.m)
slides/   generated PowerPoint decks
data/     exported result tables (.csv)
```

## figures/ — which script produced what

| Figure | Produced by |
|---|---|
| `v3_fig1…3*` *(not archived — regenerate)* | `Framework.py`, `Framework_bkp.py` |
| `v4_fig1…5*` *(not archived — regenerate)* | `Framework_V2.py` |
| `v5_fig1…5*` *(not archived — regenerate)* | `Framework_V3.py` |
| `cw_fig1_paper_reproduction.png` | `Framework_cowork*.py` — reproduces the GLSVLSI'24 reference result |
| `cw_fig2_topology_comparison.png` | `Framework_cowork*.py` |
| `cw_fig3_a1_vs_a2.png` | `Framework_cowork*.py` — **A1 periphery vs A2 under-die** VR placement |
| `cw_fig4_physical_intuition.png` | `Framework_cowork_physical (1).py` *only* |
| `hvr_v3_fig1_loss_comparison.png` | `HVR_FULL_OPT_EPC_V2.py` — default vs optimized loss |
| `hvr_v3_fig2_constraints.png` | `HVR_FULL_OPT_EPC_V2.py` — area / ripple constraint overview |
| `hvr_v3_fig3_pareto.png` | `HVR_FULL_OPT_EPC_V2.py` — Pareto: loss vs area |
| `hvr_width_fig1…3*.png` | `HVR_FULL_OPT_sizing.py` — same three views, width-swept switches |
| `hvr_efficiency_vs_vrcount_by_topology.png` | `Framework_w_HVR_OPT_sizing.py` / `_v2.py` |
| `hvr_system_loss_vs_vrcount_by_topology.png` | `Framework_w_HVR_OPT_sizing_v2.py` *only* |
| `total_loss_vs_vr_count.png` | `HVR_FULL_OPT_EPC_LIB_TOTAL_NVR_LOSS.py` and `HVR_FULL_OPT_sizing_TOTAL_NVR_LOSS.py` (same name — **whichever ran last wins**) |
| `total_loss_vs_vr_count_sizing.png` | `HVR_FULL_OPT_sizing_TOTAL_NVR_LOSS.py` |
| `dse_case1_planar.png` | `dse_study_cases.py` — planar packaging, 20 mm² budget |
| `dse_case2_stacked.png` | `dse_study_cases.py` — 3D vertical stacking, 20 mm² budget |
| `Efficiency_Comp.png` | **MATLAB** — exported from `matlab/Efficiency_Comp.fig` |
| `HVR_optimizer_output.png` | **MATLAB** — exported from `matlab/HVR_optimizer_output.fig` |
| `LOSS_AND_EFF_VS_VR_COUNT.png` | **MATLAB** — exported from `matlab/LOSS_AND_EFF_VS_VR_COUNT.fig` |

The `v3_`/`v4_`/`v5_` figure sets are declared in `Framework.py`, `Framework_V2.py` and
`Framework_V3.py` but no copies were kept — rerun those scripts to produce them.

## matlab/

The Python side exports raw arrays to `.mat`; MATLAB then does the final styling. That is
why some plots exist in both worlds.

| File | Notes |
|---|---|
| `total_loss_vs_vr_count.mat` + `_plot.m` | Written by `HVR_FULL_OPT_sizing_TOTAL_NVR_LOSS.py`. The `.m` is auto-generated and reloads the `.mat` to redraw total loss **and** efficiency vs VR count on twin axes, coloured per topology. |
| `total_loss_vs_vr_count_epc.mat` + `_epc_plot.m` | Same, from the EPC-library variant `HVR_FULL_OPT_EPC_LIB_TOTAL_NVR_LOSS.py`. |
| `Efficiency_Comp.fig`, `HVR_optimizer_output.fig`, `LOSS_AND_EFF_VS_VR_COUNT.fig` | Hand-made MATLAB figures (MATLAB 5.0 MAT-file, PCWIN64). No Python script generates these — they are original artifacts, so keep them. |

## data/

| File | Notes |
|---|---|
| `hvr_efficiency_vs_vrcount_by_topology.csv` | Efficiency vs VR count per `(N, K, K_A)` topology, from `Framework_w_HVR_OPT_sizing*.py`. |

> Not to be confused with **`EPC-Product-Table.csv` at the repo root**, which is *input*
> (the GaN device library) and must stay where it is.

## slides/

`dse_case1_planar.pptx`, `dse_case2_stacked.pptx` — written by `dse_study_cases.py`.
For fully editable native PowerPoint charts instead of embedded images, run
`dse_pptx_native.py`, which emits `dse_native.pptx`.

---

**Regenerated during the 2026-08-18 reorganization:** `dse_case1_planar.*` and
`dse_case2_stacked.*` were missing from the archive and were produced by running
`dse_study_cases.py` to verify the new layout end-to-end. Best design point found:
**N=4, K=2 → η = 97.36 %** at 14.6 mm², EPC2057 (HS) / EPC2366 (LS), f_sw = 0.47 MHz.
