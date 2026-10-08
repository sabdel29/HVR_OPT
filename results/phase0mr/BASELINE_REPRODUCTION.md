# PHASE 0M-R SECTION 1 --- BASELINE REPRODUCTION

Nothing in this phase was modified until the Phase-0M state was reproduced from a clean run.

## Test suite

```
461 passed in 93.25s
```

Matches the Phase-0M closing count exactly. **Baseline reproduced.**

## Version control

This repository is **NOT under git** (`fatal: not a git repository`). There are therefore no
commit hashes to record. Content addressing is used instead: the md5 of every authoritative
artifact is recorded below and the Phase-0M PDFs are archived byte-identically.

| artifact | md5 at the start of Phase 0M-R |
|---|---|
| `results/ETM_DVPD_FULL_TECHNICAL_REPORT.pdf` | `9338b64f7fb08ee8e4e584ca9aa8f2d1` |
| `results/ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.pdf` | `1bf4a9444c3d218affe5a1cce84e82c3` |
| `results/CURRENT_SCIENTIFIC_STATUS.yaml` | archived as `pre_phase0mr_CURRENT_SCIENTIFIC_STATUS.yaml` |

Archived byte-identically to `results/archive/phase0m/`, verified with `cmp`.

## Environment

| tool | version / status |
|---|---|
| Python | 3.12.14 (`/home/beams0/MGHARIB/envs/etm/bin/python`) |
| CalculiX | 2.23 (`/home/beams0/MGHARIB/envs/etm/bin/ccx`) |
| MOOSE | `heat_transfer-opt`, application version `09515f92aa`. **Only** the heat-transfer module is built; there is no `solid_mechanics` binary |
| gmsh | 4.15.2 |
| pandoc | 2.0.6 |
| xelatex | TeX Live 2018 |
| gfortran / cmake / make | GCC 8.5.0 / 3.26.5 / GNU Make 4.2.1 |
| numpy / scipy | 2.2.3 / 1.16.3 |
| pyamg | **absent** |

## ANSYS AEDT --- checked rather than assumed

The brief states that HFSS and Icepak are available. That was verified against the license
manager rather than taken on trust.

```
Flexible License Manager status on Thu 9/17/2026
License server status: 1055@pinback.xray.aps.anl.gov
pinback.xray.aps.anl.gov: license server UP (MASTER) v11.19.5
ansyslmd: UP v11.19.5
```

| feature | licenses | in use |
|---|---|---|
| `elec_solve_hfss` | **1** | 0 |
| `elec_solve_icepak` | **1** | 0 |
| `elec_solve_2d` | 2 | 0 |
| `elec_solve_level1` / `level2` | 2 / 2 | 0 |
| `electronics_desktop` | 2 | 0 |
| **`elec_solve_q3d`** | **not present** | -- |

* Install: `/local/ansys/electronics/ansys_inc/v261/AnsysEM` (AEDT 2026 R1),
  `$ANSYSEM_ROOT261` already exported in the environment.
* Batch scripting confirmed working: `ansysedt -ng -RunScriptAndExit <script>` launches and
  reports script-level errors, so the non-graphical path is live.
* **Q3D remains unlicensed**, which is consistent with every earlier phase. HFSS and Icepak
  are genuinely available and are used in Sections 4 and 11.
* `pyaedt` is **not installed** in either Python, so AEDT is driven through its native
  scripting interface rather than through PyAEDT.

## PALACE

**Absent.** Not installed, not on `PATH`, no build present. Its electrostatic formulation
solves a permittivity problem in any case and is not a DC conduction solver, so its absence
does not affect Section 4.

## Solvers NOT available

Elmer (`StaticCurrentSolver`), GetDP, OpenFOAM, Palace, MOOSE `solid_mechanics`, Q3D.

## Decision

The Phase-0M baseline reproduces exactly. Phase 0M-R proceeds.
