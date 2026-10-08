# PHASE 0M-R3 --- BASELINE REPRODUCTION

Recorded before any science was modified.

## Environment

| item | value |
|---|---|
| working directory | `/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT` |
| version control | **NOT A GIT REPOSITORY.** `git status` and `git log` both return `fatal: not a git repository`. No commit hash exists. Provenance rests on the immutable phase directories and two MD5 manifests. |
| Python | 3.12.14 (`/home/beams0/MGHARIB/envs/etm/bin/python`) |
| CalculiX | ccx 2.23 |
| MOOSE | `heat_transfer-opt`, Application Version 09515f92aa |
| gmsh | 4.15.2 |
| ANSYS AEDT | v261 present at `/local/ansys/electronics/ansys_inc/v261/AnsysEM/ansysedt`; Icepak engine present. Licence reachable (previous phases launched and meshed successfully). |
| Fluent | **NOT INSTALLED.** `/local/ansys/ansys_inc/v251/` contains only `commonfiles`, `installer` and package metadata. |
| OpenFOAM / other CFD | **NOT FOUND** on PATH or in the project environment. |
| Palace | NOT FOUND (unchanged from Phase 0M-R2). |

## Baseline reproduction

| check | expected | actual |
|---|---|---|
| test suite | 627 pass | **627 passed in 84.77 s** |
| Phase-0M-R MD5 manifest (12 files) | 12 OK, 0 FAILED | **12 OK, 0 FAILED** |

The baseline is reproducible, so Phase 0M-R3 proceeds.

## What this phase archives

`results/phase0mr3/_baseline_phase0mr2/` holds a byte-identical copy of the Phase-0M-R2
deliverables with its own MD5 manifest (13 entries, read-only):

* both reports, Markdown and PDF;
* `CURRENT_SCIENTIFIC_STATUS.yaml` as Phase 0M-R2 left it;
* the decisive CSVs: architecture replay, mechanical and thermal metrics, realizability,
  the 324-row clearance sweep, the cooling regime table and the TSV geometry table.

`results/phase0mr2/_baseline_phase0mr/` (12 entries) remains untouched and verified, so the
chain back to Phase 0M-R is intact across two archive generations.
