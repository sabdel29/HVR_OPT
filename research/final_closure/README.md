# Final closure — artifacts and the scripts that produce them

Everything here is generated; rerun the generator instead of editing a file. Solver runs
(package network, ETM cases, local solder, reference tools) are listed first; everything
derived from them is rebuilt by `scripts/final_closure_rebuild.sh`.

| artifact | producer | what it is |
|---|---|---|
| `package_network.json`, `bga_count_screen.csv` | `scripts/final_closure_pkg_network.py` | resolved HV package networks, exhaustive count screen, matched count |
| `etm_<arch>_<scen>_h1.1[_rXZ].json` | `scripts/final_closure_physical_etm.py` | one E-T fixed point (+ mechanics, all-site joint search) per case and mesh level; `_r21` is production, `_r11` (no suffix), `_r12`, `_r31` are the nested study |
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
