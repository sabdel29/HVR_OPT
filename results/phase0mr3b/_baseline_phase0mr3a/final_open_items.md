# PHASE 0M-R3A --- FINAL OPEN ITEMS

Ranked. Two items now stand between the repaired pair and PROVEN_REALIZABLE, where Phase
0M-R3 recorded one.

| # | item | why open | what it blocks | what would close it |
|---|---|---|---|---|
| 1 | **process rule for the intra-converter vertical interconnect** | DEFECT #58: the design space has no geometry rule for a stacked via through substrate power layers, and the TSV range was borrowed | PROVEN_REALIZABLE for BOTH architectures, because the routing repair depends on it | one substrate-vendor build-up via design rule: diameter, pitch, aspect-ratio and stacking limits |
| 2 | **three package clearances** | no framework source, no accessible foundry rule | PROVEN_REALIZABLE for both | a process design rule from a named vendor |
| 3 | **ARCH_Z2 TSV process margin** | 30 um gives M_AR = 1.000 and fails the modest bound | calling the frozen Z2 manufacturable | adopt 32 um, the smallest evaluated diameter with positive margin, at 12.5 % FEWER vias |
| 4 | **high-stress SAC305 constitutive data** | no primary data above ~16 MPa at 45-150 C | every absolute reliability number and the MAGNITUDE of the relative one | coupon characterisation at 15-100+ MPa |
| 5 | **conjugate CFD of the cooler** | timed out at its declared budget in Phase 0M-R3 | calling the cooler fully validated | a converged canonical benchmark |
| 6 | **required life N_required** | not published for this system | G2 | a statement from the system owner |
| 7 | **absolute N_f validation** | strain and energy formulations disagree 4.1x | G2 | a validated life model |
| 8 | **admissible mechanical allowable** | nine candidates, none admissible | G2 and any constraint-based optimizer | a published allowable tied to a failure mode |
| 9 | **ARCH_Z4 power-die construction** | unsourced; stacked and planar give different rankings | any Z4 ordering claim | one process description |

Items 6, 7 and 8 are the **three independent G2 blockers**. G2 remains NOT TESTED until all
three close.

## COMPLETE --- must not reappear as future work

* adopting the physical cooling model into the ETM loop --- **done in Phase 0M-R**
* putting the RDL into the production thermal model --- **done in Phase 0M-R2**
* retiring the global 1.326 transition constant --- **done in Phase 0M-R**
* making the TSV span architecture-aware --- **done in Phase 0M-R2**

## Not open, and not to be relitigated

* **Z2 carries less local fatigue-relevant inelastic response than Z1** --- D_driver = 1.1943.
* **The routing arithmetic** --- reproduced exactly by an independent implementation.
* **The TSV allocation law** --- enlarging the via changes the COUNT and nothing else.
* **The production cooling point** --- Re = 1264.8, inside its validated domain; the design
  space is capped at Re <= 2300 and conjugate CFD is NOT COMPLETED.
