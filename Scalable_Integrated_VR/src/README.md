# `src/` — code map

19 modules, deliberately kept **flat**. Every cross-module import is a bare sibling import
(`from HVR_FULL_OPT_EPC_V2 import ...`), so flattening is what keeps them resolvable:
running `python3 src/<script>.py` from the repo root puts `src/` first on `sys.path`, and the
working directory stays at the root where `EPC-Product-Table.csv` lives. Moving any file into
a sub-package would break both halves of that.

## Dependency graph

```
                       EPC-Product-Table.csv  (repo root, 97 GaN parts)
                                  │
   ┌──────────────────────────────┴───────────────────────────────┐
   │                                                              │
HVR_FULL_OPT_EPC.py          ┌─── HVR_FULL_OPT_EPC_V2.py ◄────────┴──┐
  (v1 engine)                │      (MAIN engine)                    │
   │                         │            ▲                          │
   ├─ dse_study_cases.py     │            │                          │
   │    └─ dse_pptx_native.py│    HVR_FULL_OPT_sizing.py             │
   └─ sota_model_vs_optimizer.py    (width-sweep engine)             │
                             │            ▲                          │
                             │            ├─ Framework_w_HVR_OPT_sizing.py
                             │            └─ Framework_w_HVR_OPT_sizing_v2.py
                             │
      Framework.py, Framework_bkp.py, Framework_V2.py, Framework_V3.py,
      Framework_cowork*.py, diag_hs_sweep.py,
      HVR_FULL_OPT_EPC_LIB_TOTAL_NVR_LOSS.py, HVR_FULL_OPT_sizing_TOTAL_NVR_LOSS.py

Ind_and_Cap_data.py — standalone passive library, imported by nothing (reference data)
```

## Engines

The four modules other code builds on.

| Module | Role | Notes |
|---|---|---|
| **`HVR_FULL_OPT_EPC_V2.py`** | **Main HVR engine.** Architecture generation, EPC device/inductor/capacitor filtering, loss model, `run_hvr_optimization()`. | Despite the `_V2` filename its header says *"V3 content"*. Adds over v1: hard area budget `I_out/J_target`, ΔV_out ripple gate, coupled-inductor ripple correction `ΔI/(1+k_c(K-1))`, per-inductor `f_sw ≤ f_max`. **Imported by 9 modules.** |
| `HVR_FULL_OPT_EPC.py` | v1 engine — same architecture search, **no area or ripple constraints**. | Its own header lists those constraints under *"What needs to be added"*. Superseded by `_V2` for framework work, but still the engine behind the three newest studies. Needs **Python ≥ 3.10** (PEP-604 unions). |
| `HVR_FULL_OPT_sizing.py` | **Width-based** variant: sweeps transistor widths `W_H`/`W_L` instead of picking discrete EPC parts (`R_on ∝ 1/W`, parasitics `∝ W`). | Reuses architecture generation and passive libraries from `_V2`. Answers "what device *should* exist", not "what can I buy". |
| `Ind_and_Cap_data.py` | Passive component library — 8 integrated inductors + 8 capacitors, each with measured values and a full citation. | Categories: organic-package-embedded, silicon-interposer, PCB-embedded. Currently **imported by nothing**; the live libraries are duplicated inside `_V2`. |

## Study drivers

Run these directly. "Outputs" are written to the **current working directory**.

### Newest work (created most recently, built on the v1 engine)

| Script | What it does | Outputs |
|---|---|---|
| `dse_study_cases.py` | Design-space exploration under a **20 mm² budget**, two packaging cases: **planar** (area = Σ footprints) vs **3D vertical stacking** (area = largest layer). 48 V→1 V, 20 A, ΔI<40 %, ΔV<5 %, C_out=100 µF. | `dse_case1_planar.png`, `dse_case2_stacked.png` (+ `.pptx`) |
| `dse_pptx_native.py` | Rebuilds the DSE bar charts as **native, editable PowerPoint charts** (right-click → Edit Data). | `dse_native.pptx` |
| `sota_model_vs_optimizer.py` | Apples-to-apples: re-evaluates published SOTA designs through *this* loss model, then compares to the optimizer's best at equal topology and footprint. **DSCH** (N=3,K=2, EPC2216/EPC2014C) and **DPMIH** (N=4,K=4, 2×EPC2015C ∥ / 2×EPC2023 ∥). | `sota_model_vs_optimizer.png` |

> `dse_pptx_native.py` imports `dse_study_cases`, which **runs the whole DSE at import time**
> (no `__main__` guard) — expect the full sweep to execute before any chart is drawn.

### System framework — VR count, placement, routing loss

Implements the GLSVLSI'24 routing model of *Krishnakumar, Popryho & Partin-Vaisband,
"System Architecture Optimization for Vertical Power Delivery"*: `R_eff` as a parallel
network over Manhattan distances, with **A1 (periphery)** vs **A2 (under-die)** VR placement.

| Script | Status | What changed | Outputs |
|---|---|---|---|
| `Framework.py` | v3 — baseline | The original routing model + joint sweep. Only file in git history. | `v3_fig1…3*.png` |
| `Framework_bkp.py` | backup | Snapshot of `Framework.py` (~143 lines differ). | `v3_fig*.png` |
| `Framework_V2.py` | v4 | Adds HVR topology exploration on top of v3; HVR results cached per `I_per_VR`. | `v4_fig1…5*.png` |
| **`Framework_V3.py`** | **v5 — current** | Fixes 3 root-cause bugs in v4: (1) un-normalised core-loss term that exploded at high `f`; (2) inductor library pointing at 13 mm² research parts, collapsing `max_vrs` to ~23; (3) `vr_footprint_mm2()` ignoring `n_phases`. | `v5_fig1…5*.png` |
| `Framework_cowork.py` | parallel fork | `ProcessPoolExecutor` over ~576 `(topo, nl, gan, ind)` tasks; vectorised the PPDN distance loop. | `cw_fig1…3*.png` |
| `Framework_cowork_physical.py` | parallel + physical | Adds physical-intuition modelling. | `cw_fig1…3*.png` |
| **`Framework_cowork_physical (1).py`** | **newest of the cowork line** | ⚠ The `(1)` suffix is a download artifact, **not** an older copy — this file is *ahead*: bounded ripple-based core-loss surrogate replacing `k·L·f^α`, plus a 4th figure. | `cw_fig1…4*.png` |

### VR-count sweeps

| Script | Engine | What it does | Outputs |
|---|---|---|---|
| `Framework_w_HVR_OPT_sizing.py` | width-based | Sweeps VR count `M`, re-optimizing each topology at `I_out/M`, then adds system routing loss. | `hvr_efficiency_vs_vrcount_by_topology.png/.csv` |
| **`Framework_w_HVR_OPT_sizing_v2.py`** | width-based | Same, but routing loss now depends on Manhattan distance **+ TSV + bumps + skin effect at the optimized `f_sw`**, recomputed per topology. | `+ hvr_system_loss_vs_vrcount_by_topology.png` |
| `HVR_FULL_OPT_EPC_LIB_TOTAL_NVR_LOSS.py` | EPC library | Total loss across all `N` VRs, exported for MATLAB. (Docstring is a stale copy-paste from the width-based module.) | `total_loss_vs_vr_count.png`, `total_loss_vs_vr_count_epc.mat` |
| `HVR_FULL_OPT_sizing_TOTAL_NVR_LOSS.py` | width-based | Same study, width sweep instead of catalogue parts. | `total_loss_vs_vr_count_sizing.png`, `total_loss_vs_vr_count.mat` |

### Diagnostic

| Script | What it does |
|---|---|
| `diag_hs_sweep.py` | For Arch `N=3, K=2, K_A=1`, sweeps **every** qualifying high-side device by ascending `R_DS_on` and reports the minimum achievable loss with its `P_cond / P_sw_HS / P_sw_GD / P_sw_COSS` breakdown. LS device, passives and `f_sw` are co-optimized per candidate so the comparison is fair. Writes no files. |

## Behaviour notes

* **14 of 19 modules are `__main__`-guarded.** The exceptions run work on import:
  `dse_study_cases.py`, `dse_pptx_native.py`, `sota_model_vs_optimizer.py`, and
  `Ind_and_Cap_data.py` (harmless — data only).
* **All 19 compile cleanly**, and every cross-module import resolves in this layout
  (verified end-to-end: `dse_study_cases.py` runs to completion, best point
  `N=4, K=2 → η=97.36 %` at 14.6 mm²).
* Files use **CRLF** line endings — they were authored on Windows.
