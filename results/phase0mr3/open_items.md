# PHASE 0M-R3 --- OPEN ITEMS

Ranked. Every item is OPEN in the strict sense: not determined, never defaulted.

## Blocking

| # | item | why open | what it blocks | what would close it |
|---|---|---|---|---|
| 1 | **three package clearances** | no framework source, no accessible foundry rule, nothing usable in reachable literature | PROVEN_REALIZABLE for both architectures; they are the sole reason the pair is CONDITIONAL | a process design rule from a named vendor |
| 2 | **TSV process margin on ARCH_Z2** | AR = 10.000 gives M_AR = 1.000 and fails a modest tolerance bound | calling the frozen Z2 manufacturable | adopt the 34 um via (sourced, +22.8 % vias, <= 0.02 % E/T/M change) or source a tolerance that the 30 um via survives |
| 3 | **transitional cooling correlation** | nothing sourceable for 2300 < Re < 3000 | any flow above the cap; currently avoided rather than solved | one primary correlation with its coefficients and range |
| 4 | **conjugate CFD of the cooler** | see CONJUGATE_CFD_VALIDATION.md | calling the cooler fully validated | a converged canonical benchmark |
| 5 | **high-stress SAC305 constitutive data** | no primary data above ~16 MPa at 45-150 C | every absolute reliability number and the MAGNITUDE of the relative one | coupon characterisation at 15-100+ MPa |
| 6 | **required life N_required** | not published for this system | G2 | a statement from the system owner |
| 7 | **absolute N_f validation** | strain and energy formulations disagree 4.1x | G2 | a validated life model |
| 8 | **admissible mechanical allowable** | nine candidates, none admissible | G2 and any constraint-based optimizer | a published allowable tied to a failure mode |
| 9 | **ARCH_Z4 power-die construction** | unsourced; stacked and planar give different rankings | any Z4 ordering claim | one process description |
| 10 | **electromigration allowable** | no primary study with its conditions | a feasibility verdict on any via field | one primary EM study |

Items 6, 7 and 8 are the **three independent G2 blockers**. Closing any one leaves the
other two, and G2 remains NOT TESTED until all three close.

## Not open, and not to be relitigated

* **Z2 carries less local fatigue-relevant response than Z1** --- D_driver = 1.1943,
  unchanged by the realizability repair.
* **A realizable Z1 and Z2 exist** in the current library, conditional only on item 1.
* **The production cooling point is inside its correlation's validated domain.**
* **The TSV allocation law** --- enlarging the via changes the count and nothing else.
* **Pumping power is FACILITY scope** --- not in the loss objective, not in the mesh.
