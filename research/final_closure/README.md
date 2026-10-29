# Final closure — artifacts and the scripts that produce them

Everything here is generated; rerun the generator instead of editing a file. Solver runs
(package network, ETM cases, local solder, reference tools) are listed first; everything
derived from them is rebuilt by `scripts/final_closure_rebuild.sh`.

| artifact | producer | what it is |
|---|---|---|
| `package_network.json`, `bga_count_screen.csv` | `scripts/final_closure_pkg_network.py` | resolved HV package networks, exhaustive count screen, matched count |
| `Z2_DIRECT_FEED_ARCHITECTURE.md`, `z2_direct_feed_architecture.json` | hand-written, frozen before any result of the corrected lineage | the primary Z2 (direct-fed, explicit VR attach, 1 mm sidewall clearance), the BGA-fed control, boundaries and sources |
| `etm_<arch>_<scen>_h1.1[_rXZ].json` | `scripts/final_closure_physical_etm.py` | one E-T fixed point (+ mechanics, all-site joint search) per case and mesh level; `_r21` is production, `_r11` (no suffix), `_r12`, `_r31` are the nested study, `_h0.8` the re-graded (not nested) mesh; arch `Z2BF` is the BGA-fed control |
| `direct_feed_crossover.json` | `scripts/final_closure_direct_feed.py` | the swept external feed loop of the direct-fed Z2 and the crossover R* per scenario |
| `control_results.json` | `scripts/final_closure_results.py` | the controlled BGA-fed Z1 vs Z2 experiment |
| `sensitivity/etm_<arch>_HV_S0__<variant>.json`, `classB_resolution.{csv,json}`, `classB_sensitivity_rows.csv` | `scripts/final_closure_sensitivity.py`, `scripts/final_closure_classB.py` | class-B variants on the production mesh and their verdicts |
| `local_mesh_policy.json`, `local_time_study.json`, `local_cycle_study.json`, `local_mesh_study.json` | `scripts/final_closure_local_mesh.py` | the declared local solder mesh family (amendment 4 for the corrected lineage) |
| `tool_provenance.json` | `scripts/final_closure_provenance.py` (consistency fix and guard) | every tool, its lane, version and evidence |
| `reference_cooling_icepak.json`, `reference_artifacts/icepak/` | `scripts/reference_tools/icepak_cooling_benchmark.py`, `preserve_icepak_artifact.py` | the matched Icepak conjugate CFD and its preserved AEDT projects |
| `solver_check/` | `scripts/final_closure_solver_check.py` | iterative vs direct structural solver on the same mesh and field |
| `local_solder_<scen>.json` | `scripts/final_closure_local_solder.py` | local viscoplastic response at the production critical joint |
| `reference_rve.json` | `scripts/reference_tools/aedt_rve_references.py` | AEDT via / homogenisation references (adopted RDL tensor) |
| `reference_rve_timing.json` | same, `RVE_RETIME_REPEATS=3` | re-solved references, warm-up + 3 timed repeats; never rewrites the adopted values |
| `reference_pkg_rdl_moose_<arch>.json` | `scripts/reference_tools/moose_pkg_rdl_reference.py` | package network vs MOOSE |
| `reference_thermal_column_<arch>.json` | `scripts/reference_tools/thermal_column_benchmark.py` | unit-cell thermal, CalculiX vs AEDT |
| `reference_thermal_column_moose_<arch>.json` | `scripts/reference_tools/moose_thermal_column.py` | unit-cell thermal, CalculiX vs MOOSE |
| `reference_mech_bilayer.json` | `scripts/reference_tools/mech_bilayer_benchmark.py` | bilayer warpage, CalculiX vs closed form and AEDT |
| `accuracy_speed_matrix.{csv,json}` | `scripts/final_closure_accuracy_matrix.py` | one row per stage and observable; no overall accuracy |
| `final_results.json`, `electrical_ledger.*`, `energy_audit.json`, `mesh_convergence.json`, `coupling_checks.json`, `ordering.json`, `FINAL_PAPER_DECISION.md` | `scripts/final_closure_results.py` | the frozen lineage, its checks and the paper decision |
| `paper_gate_classification.{csv,json}` | `scripts/final_closure_gate_classes.py` | every OPEN gate in class A, B or C |
| `literature_rules.{json,md}` | `scripts/final_closure_literature_rules.py` | DIRECT / CLOSE_ANALOG / CONTEXT_ONLY / NOT_HELD |
| `FINAL_PAPER_SCOPE.md` | hand-written, frozen before the manuscript changed; dated amendments only | what the paper may and may not claim |
| `superseded_pre_rve/`, `superseded_base_mesh/` | archived | results replaced by the RVE tensor and by the production mesh; provenance only |
| `superseded_bga_fed_z2/` | archived | the previous lineage, whose primary Z2 was BGA-fed, attach-less and sidewall-filled; provenance only |
| `superseded_pre_tile_temperature/` | archived | the first direct-fed HV-S0 cases and crossover, computed before the E-T coupling fix (DEFECT #68), with the diagnostic that found it; provenance only |
| `literature_metadata/` | `scripts/final_closure_literature_rules.py` (registered there) | OpenAlex records (abstracts removed) and the parsed public patent texts behind the new citations |

The converged production temperature and structural fields that the mechanics-only
variants and the warpage maps read are copied out of the scratch work tree by
`scripts/final_closure_collect_fields.py` (verified against each case's T_max).

**Solver-run integrity (DEFECT #69, 2026-10-28).** On this shared host the per-user thread
limit (8192) was reached when a pool of local solves each started a full-width OpenBLAS
pool; CalculiX processes died mid-solve, and the historical local runner returned a cycle
metric from a cut-off `.dat`. The pool-based drivers now cap OpenBLAS at one thread, a
local solve counts only if its `.dat` reaches the schedule end
(`final_closure_local_extract.complete`), old outputs are removed before each solve, and a
solid-solder joint without a response stops `final_closure_local_solder.py`. Every class-B
and local solve that overlapped the exhaustion window (22:18–22:34) was discarded and re-run;
the discarded files were never committed. The two r31 ladder cases had one
intermediate E-T iterate in that window; their reported state comes from later solves
(contraction shown in `FINAL_PAPER_DECISION.md`). Readers of the case files decide lineage by
content (`final_closure_physical_etm.current_lineage`), never by file name.
