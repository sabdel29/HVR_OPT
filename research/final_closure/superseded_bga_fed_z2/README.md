# Superseded case files (previous lineage, commit abba03e)

These case files belong to the lineage in which the primary Z2 was **BGA-fed**: its 48 V
came through peripheral package BGA balls and a package 48 V RDL. That Z2 also had **no
explicit VR-to-substrate attach**, and its encapsulant **filled the PCB opening to the
sidewall** (DEFECT #66).

They are kept here, unchanged, for provenance only. **No current result reads them.**
Some levels have a corrected counterpart in the parent folder
(`../Z2_DIRECT_FEED_ARCHITECTURE.md` describes the corrected lineage); others were not
regenerated:

- The production (r21) and nested-ladder (r11, r12, r31) case files in the parent folder
  were all re-run on the corrected lineage. Their previous versions are kept here under the
  same names (`etm_{arch}_HV_S*_h1.1[_rNN].json`), copied byte-for-byte from commit abba03e.
- The h_xy = 0.8 mm re-mesh sensitivity is re-run separately.
- The S1/S2 files without a refinement tag were the coarse-mesh scenario runs of the
  previous lineage. The corrected lineage runs every scenario at the production mesh (r21)
  instead.

The Z1 files are kept for the same reason. Z1's construction did not change, and its
corrected runs reproduce the previous E-T histories exactly (same loss, same temperatures,
same residuals; only the wall time differs).

`sensitivity/` holds every class-B case of the previous lineage, together with its run log.
Their Z2 values describe the superseded BGA-fed, sidewall-filled Z2 without an attach, and
`f1_clearance` was the clearance variant of that baseline. The corrected campaign re-runs
every class-B case, Z1 included, into `../sensitivity/`.

The local solder records of the previous lineage are kept beside the case files:
`local_solder_HV_S*.json` (the L0 family at the old critical joints) and
`local_time_study_pass3.json`, `local_cycle_study_pass3.json` and `local_mesh_study_pass3.json`
(pass 3 of the declared local mesh policy). The corrected lineage re-runs all of them under
policy amendment 4.
