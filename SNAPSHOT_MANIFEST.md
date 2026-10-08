# SNAPSHOT MANIFEST

What in this repository is **authoritative** and what is **historical**. The tree carries the
full development record across ~22 phases; only a small part of it describes the current
state of the science.

Snapshot date: 2026-10-08 · tag `paper-freeze-r3c`

---

## AUTHORITATIVE — the current state

Anything cited by the manuscript comes from here.

| path | contents |
|---|---|
| **`results/phase0mr3c/`** | **the frozen final state.** Every number in the paper traces here |
| `manuscript/` | the paper, its 8 figures, and all supporting audits |
| `configs/phase0mr3c/frozen_pair_Z1.yaml`, `frozen_pair_Z2.yaml` | the two frozen architectures, frozen *before* they were solved |
| `results/PAPER_FREEZE_DECISION.md` | what was frozen and why development stopped |
| `results/PAPER_CLAIM_MATRIX.csv` | permitted / forbidden wording per claim |
| `results/PAPER_FIGURE_TABLE_PLAN.md` | figure and table plan |
| `results/ETM_DVPD_FULL_TECHNICAL_REPORT.md` | long-form technical record, current |
| `results/ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.md` | standalone current-state audit |
| `results/CURRENT_SCIENTIFIC_STATUS.yaml` | machine-readable current status |
| `scripts/` | all analysis, audit and figure code |
| `tests/` | regression and semantic-guard suite |

### The authoritative result files

| file | gives |
|---|---|
| `results/phase0mr3c/final_etm_replay.csv` | P_elec, T_max, T_mean, warpage, Δu_c for both |
| `results/phase0mr3c/final_local_response.csv` | Δε_in, strain range, inelastic work |
| `results/phase0mr3c/local_submodel_inputs.csv` | corner-joint temperature, traced inputs |
| `results/phase0mr3c/cetol_final_pair.csv` | integration-tolerance ladder |
| `results/phase0mr3c/local_response_decomposition.csv` | the 19.39 % / 0.75 % decomposition |
| `results/phase0mr3c/routing_feasibility.csv` | per-net aspect ratios, AR 5.05 → 0.833 |
| `results/phase0mr3c/conductor_plane_topology.csv` | via-level derivation |
| `results/phase0mr3c/gan_alpha_sensitivity.csv` | α_GaN sensitivity |
| `results/phase0mr3c/timing_breakdown.json` | measured stage costs |
| `results/phase0mr3c/platform.json`, `runtime_benchmark.csv` | machine and wall times |

---

## HISTORICAL — superseded, kept for provenance

These record how the result was reached. **Do not quote numbers from them.** Several contain
values that were later corrected; the audit tooling actively guards against them reappearing
as current.

| path | was |
|---|---|
| `results/phase0b` … `results/phase0lr` | the development phases, ~22 of them |
| `results/phase0mr`, `phase0mr2`, `phase0mr3`, `phase0mr3a`, `phase0mr3b` | the architecture-comparison line that preceded the freeze |
| `results/archive/` | superseded report snapshots |
| `results/**/_baseline_*/` | checksummed baselines proving earlier phases were not mutated |
| `manuscript/ETM_DVPD_MANUSCRIPT_BLUEPRINT.md` | pre-manuscript plan; its figure numbering is **wrong** and it is marked superseded at the top |
| `EPEPS_HVR_Framework/` | the earlier EPEPS figure set and slides |
| `NOVELTY_BOUNDARY_ETM*.md`, `deep-research-report_HVR.md` | early scoping notes |

### Known superseded values that must never be quoted as current

The ratio ladder through the refinement sequence was
`1.3225 → 1.2552 → 1.1942 → 1.1943 → 1.1947`. Only the last is current, and only as the
**displacement-driver** ratio D_u. Also withdrawn: the 1.558 relative-life ratio, the
35.8 %/12.4 % architecture separation, and every absolute-life figure.

---

## DEPENDENCY

| path | what |
|---|---|
| `Scalable_Integrated_VR/` | git submodule → `mgharib5/Scalable_VR_INTEGRATED`. Supplies `HVR_FULL_OPT_EPC_V2.py`, the converter loss model the synthesis path imports. Tracked as a submodule so that repository is referenced, never copied or overwritten. |

---

## NOT IN THIS REPOSITORY

Excluded at snapshot time. Nothing was deleted locally — see `.gitignore` for the rules and
`REPRODUCE.md` §7 for how to regenerate each.

| excluded | size / count | reason |
|---|---|---|
| CalculiX `.dat` / `.frd` / `.inp` scratch | ~33 GB, 650+ files | regenerable solver output |
| `.npy` mesh and displacement arrays | 240 MB, 543 files | solver intermediates |
| ANSYS `.aedtresults` trees, autosaves | ~1.5 GB | tool scratch |
| publisher PDFs | ~60 MB | copyrighted; all are cited in the manuscript |
| generated report PDFs | ~10 MB each | regenerable; Markdown source is tracked |
| CalculiX manual and source tarball | 9 MB | third party, upstream at dhondt.de |
| `Scalable_Integrated_VR.zip` | 129 MB | duplicate of the submodule |
| `.claude/`, `.pytest_cache/`, `__pycache__/` | — | local tooling and caches |
| `batch.log`, `.loglogin` | — | machine logs |

The working tree is ~36 GB; this repository is ~73 MB.

---

## Where to start

1. `README.md` — what the project is, in three minutes
2. `CURRENT_STATUS.md` — the authoritative numbers and what is / is not claimed
3. `manuscript/HANDOVER_README.md` — if you are picking up the paper itself
4. `REPRODUCE.md` — to re-derive anything
