# PHASE 0M-R2 --- ENVIRONMENT OF RECORD

Recorded before any code was modified.

| item | value |
|---|---|
| working directory | `/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT` |
| version control | **NOT A GIT REPOSITORY.** `git status` and `git log` both return `fatal: not a git repository`. There is no commit hash to record. Provenance rests on the immutable phase directories and the MD5 manifest in `results/phase0mr2/_baseline_phase0mr/MD5SUMS.txt`. |
| Python | 3.12.14 (`/home/beams0/MGHARIB/envs/etm/bin/python`) |
| CalculiX | ccx 2.23 |
| MOOSE | `heat_transfer-opt`, Application Version 09515f92aa, present and executable |
| Palace | NOT FOUND on this system. No DC-conduction or electrostatic Palace path exists. |
| AEDT | `/local/ansys/electronics/ansys_inc/v261/AnsysEM/ansysedt` present (2026 R1) |
| Icepak | present as an AEDT solver (`icepak`, `ICEPAKCOMENGINE`, `ICEPAKMESHENGINE` in the AnsysEM tree) |
| Fluent | **NOT INSTALLED.** `/local/ansys/ansys_inc/v251/` contains only `commonfiles`, `installer`, `install.id`, `package.id` --- no `fluent` directory. |
| test count at entry | **549 passed** in 66.50 s |

The entry test count matches the Phase-0M-R reported figure exactly, so no science was
modified before this phase began.
