# COMPUTATIONAL PLATFORM AND SOFTWARE

All results reported in the manuscript were produced on a single machine. Hardware is
recorded from the system itself, not from recollection.

## Hardware

| item | value |
|---|---|
| host | `pinback.xray.aps.anl.gov` |
| processor | 2 × Intel Xeon Gold 6342 @ 2.80 GHz (Ice Lake-SP) |
| cores | 24 per socket, 48 physical, 96 logical (2 threads per core) |
| turbo / base | 3.50 GHz max, 0.80 GHz min |
| L3 cache | 36 MiB per socket |
| NUMA nodes | 2 |
| memory | 2.0 TiB |
| accelerators | none used; every solver in the chain is CPU-only |

## Operating system and runtime

| item | value |
|---|---|
| OS | Red Hat Enterprise Linux 8.10 (Ootpa) |
| kernel | 4.18.0-553.150.1.el8_64 x86_64 |
| Python | 3.12.14 |
| NumPy / SciPy | 2.5.2 / 1.16.3 |
| Matplotlib | 3.10.8 |

## Solvers and their role

| solver | version | role in this work | parallelism |
|---|---|---|---|
| CalculiX CrunchiX | 2.23 | production thermal and thermoelastic package solves (C3D8 thermal, C3D8I structural); the displacement-driven local solder submodel (`*VISCO`) | OpenMP, `OMP_NUM_THREADS` = 48, `OMP_STACKSIZE` = 512 MB |
| MOOSE heat-transfer module | build `09515f92aa` | independent cross-check only: RDL plane resistance, interconnect transition resistance, explicit-fin cooling, full 3-D package thermal field | MPI, single rank for the cases reported |
| in-house finite-volume DC conduction solver | this work | current crowding and physical via-chain resistance; cell-centred, harmonic-mean face conductivities, conservative by construction | serial, SciPy sparse direct |
| in-house converter synthesis and PPDN models | this work | converter compile, rail-aware interconnect, cooling correlations, homogenisation | serial |
| ANSYS HFSS (AEDT 2026 R1) | 2026 R1 | **attempted** for via AC resistance; the adaptive solve did not converge in the allotted budget and **no result is used** | — |
| ANSYS Icepak | — | **attempted** for conjugate CFD of the cooled package; the run was discarded and **no result is used** | — |

Palace is present on the system but is not part of the validated chain and is not used.

## Reproducibility notes

The stack-height budget, the via geometry and the physical-span convention are supplied to
the production path through explicit environment hooks rather than by editing the model, so
a run is fully described by the frozen configuration file plus three variables:
`PHASE0MR3B_PHYSICAL_SPANS`, `PHASE0MR3_R_VIA_UM` and `PHASE0MR3_VIA_PITCH_UM`. The frozen
configurations are `configs/phase0mr3c/frozen_pair_Z1.yaml` and `..._Z2.yaml`, and the
timing reported in `RUNTIME_BENCHMARK.md` was produced with exactly those settings.
