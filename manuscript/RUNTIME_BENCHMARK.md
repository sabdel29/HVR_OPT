# RUNTIME AND COMPUTATIONAL COST

Measured on the platform of `COMPUTATIONAL_SETUP.md`, using the frozen configurations of
`configs/phase0mr3c/frozen_pair_*.yaml` and the same environment hooks as the reported
results. The timing run reproduced the frozen results exactly — 118.32 °C and 4.6252 µm for
Z1, 126.46 °C and 3.8714 µm for Z2 — so the timings correspond to the evaluation that
produced the published numbers and not to a reduced variant.

## Measured cost per stage

| stage | case | problem size | wall time | threads |
|---|---|---|---|---|
| converter synthesis (HVR compile) | shared | 90-device library, architecture search over N, K, K_A, B; N3K3K_A2 selected | 4.56 s | 1 |
| rail-aware PPDN and intra-converter routing | shared | 6 segments per cell × 49 cells | 0.10 ms | 1 |
| cooling boundary, correlation evaluation | shared | 223 channels | 11.2 ms | 1 |
| full ETM evaluation | Z1 | 3 E–T iterations, each a thermal and a structural solve | 134.6 s | 48 |
| full ETM evaluation | Z2 | 3 E–T iterations | 204.2 s | 48 |

The two architectures differ in cost because the backside stack carries a through-substrate
via field that the embedded stack does not resolve in the same way, which changes the
element count of the thermal and structural meshes.

## Cost structure

The analytical layers are effectively free relative to the finite-element solves. Converter
synthesis, the rail-aware network and the cooling correlation together account for 4.6 s,
of which 4.56 s is the one-off architecture search over the device library; the per-design
electrical and cooling evaluation is under 12 ms. A complete architecture evaluation is
therefore dominated by the two finite-element solves inside the E–T fixed point, and a
design-space exploration that reuses one converter compile costs approximately the
finite-element time per candidate.

This is the practical argument for the framework's structure: the physics that must be
solved numerically is isolated to two solves per iteration, and everything that can be
evaluated in closed form — the converter, the rail assignment, the interconnect
provisioning, the homogenisation and the cooling correlation — is, so that the expensive
part is entered once per candidate rather than once per design variable.

## Speedup against higher-fidelity references

A speedup is reported only where a valid reference of the same quantity exists.

| quantity | framework | reference | reference status | speedup |
|---|---|---|---|---|
| package thermal field | in-house conduction solver | MOOSE, full 3-D | valid; ordering preserved | **not available** — the MOOSE cross-checks were run on a different mesh and case set, and no controlled same-geometry timing pair was recorded |
| cooling solid side | correlation with fin efficiency, 11.2 ms | MOOSE with explicitly meshed fins, 3.78 % error | valid | **not available** — the explicit-fin runs were not timed under controlled conditions |
| via AC resistance | analytic skin-depth model | ANSYS HFSS | **invalid**: the adaptive solve did not converge in budget | not applicable |
| conjugate cooled package | in-house conduction plus correlation | ANSYS Icepak | **invalid**: the conjugate run was discarded | not applicable |

No speedup figure is claimed. Reporting one would require controlled same-geometry,
same-machine timing pairs against the reference solvers, and those were not recorded when
the cross-checks were performed. The accuracy of each cross-check is reported instead, in
`VALIDATION_MATRIX.md`, and the absolute cost of the framework is reported above.

## Reproducing the measurement

```
python scripts/phase0mr3c/benchmark_runtime.py
```

writes `results/phase0mr3c/runtime_benchmark.csv` and `results/phase0mr3c/platform.json`.
