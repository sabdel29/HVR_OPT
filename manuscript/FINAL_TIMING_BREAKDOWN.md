# COMPUTATIONAL COST --- MEASURED BREAKDOWN BY THE REAL EXECUTION PATH

Reproduce the stage split from the timing run's own artifacts with
`python scripts/phase0mr3c/timing_from_replay.py`; the aggregate wall times are
`results/phase0mr3c/runtime_benchmark.csv`.

## 1. What the execution path actually is --- established by code inspection

`scripts/phase0mr/replay_production.py::run_case`:

```
for it in range(max_et_iter):          # electrical <-> thermal fixed point
    el = electrical(...)               #   closed form, no FE
    th = PE.solve_thermal(...)         #   thermal FE  (itself fluid-coupled, see below)
    if d_t < tol_k: break
# ---- mechanics on the converged temperature field --------------------------
ccxio_.write_structural(m, mats, Tn, st, "BC_BOARD", si, solver="")
ccxio_.run_ccx(si, threads=8)          # ONE thermoelastic solve, after the loop
```

**The mechanical solve is not inside the fixed-point loop.** It runs once, after the loop has
converged, on the converged temperature field. This is the one-way T -> M coupling the paper
states, and the earlier description of "two finite-element solves inside each iteration" did
not match the code.

A second structure is visible only in the artifacts: `solve_thermal` is itself iterative,
because the solid field and the coolant energy balance are coupled. Each E-T iteration
therefore contains **three to four thermal FE sub-solves**, not one.

## 2. Measured stage times --- frozen R3C pair, 48 cores

Derived from the file timestamps written by the timing run itself, so the split is measured
rather than apportioned.

| stage | Z1 embedded | Z2 backside | in the E-T loop? |
|---|---:|---:|---|
| Converter synthesis, 90-device library | 4.56 s (shared, once) | --- | no, precedes it |
| Rail-aware PPDN + intra-VR routing | 0.10 ms per evaluation | 0.10 ms | closed form, inside |
| Cooling correlation | 11.2 ms | 11.2 ms | closed form, inside |
| E-T iterations to `dT < 0.25 K` | 3 | 3 | --- |
| Thermal FE sub-solves per iteration | 3, 4, 4 | 3, 4, 4 | yes |
| Thermal FE solves, total | 11 | 11 | yes |
| **All thermal FE, total** | **75.1 s** | **121.4 s** | yes |
| **Global thermoelastic solve** | **49.5 s** | **67.6 s** | **no --- once, after convergence** |
| Span, first thermal input to structural output | 125.0 s | 189.8 s | --- |
| Reported total wall time | 134.6 s | 204.2 s | --- |
| Local solder submodel, 4 cycles | 45.0 s | 35.1 s | no --- separate, driven by du_c |

The reported total exceeds the span by about 10 s and 14 s: mesh construction, material
assembly, `.inp` writing and result parsing sit between the solver calls and are attributed
to neither.

## 3. Why the two architectures differ

The backside stack resolves a through-substrate via field the embedded stack does not, which
raises the element count and lengthens every FE solve. The difference is in the solves, not
in the number of iterations: both converge in three.

## 4. Cost structure

Everything analytical --- synthesis, rail-aware network, homogenisation, cooling --- is
milliseconds. The cost is two FE families: eleven thermal solves inside the loop and one
thermoelastic solve after it. The local solder submodel is a further 35--45 s, and it is
entered once per architecture, not once per fixed-point iteration.

## 5. Speedup

**Not available**, unchanged. No controlled same-geometry, same-machine timing pair against a
higher-fidelity reference was recorded, and the two commercial attempts produced no valid
reference. The absolute cost above is reported instead.
