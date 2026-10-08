# PHASE 0M-R3B --- FINAL OPEN ITEMS

Ranked. The interconnect has overtaken the clearances as the binding blocker.

| # | item | why open | what it blocks | what would close it |
|---|---|---|---|---|
| 1 | **`ls_to_L` cannot be built under sourced rules** | every feasible via configuration needs 3 stacked microvia levels, which the HDI qualification calls a reliability risk; the nearest sourced-legal option is 6 % short on area | realizability of BOTH architectures | repartition so the 20.4 A net crosses fewer layers, or source a package-substrate rule that permits 3 stacked levels |
| 2 | **microvia diameter, capture pad, landing area, via current limit** | no package-substrate design rule was reachable; the EPC2057 land pattern is not in this repository | any via-level feasibility claim | items 3, 5 and 6 of `PRIMARY_SOURCES_TO_DOWNLOAD.md` |
| 3 | **two package clearances** | `cavity_sidewall_um` and `cooler_standoff_um`; searched again this phase against two new primary sources, still nothing | PROVEN_REALIZABLE | a vendor design rule |
| 4 | **TSV manufacturing tolerance** | no source; the 2 % bound is parametric | calling any diameter process-qualified | items 1 and 2 of the download list |
| 5 | **high-stress SAC305 constitutive data** | no primary data above ~16 MPa | every absolute reliability number | coupon characterisation |
| 6 | **conjugate CFD of the cooler** | timed out in Phase 0M-R3 | calling the cooler fully validated | a converged benchmark |
| 7 | **N_required**, **absolute N_f**, **admissible allowable** | unchanged | G2 | unchanged |

Items 5, 6 and 7 are carried from Phase 0M-R3A unchanged.

## Closed or downgraded this phase

* the 673 um `ls_to_L` span -- **withdrawn**, it was a mid-plane artifact
* `die_to_component_gap_um` -- OPEN to **SOURCE_BOUNDED** (15-20 um, inside the existing bound, no corner moves)
* the Phase-0M-R3 routing repair -- **withdrawn**: infeasible at the corrected landing area
* "32 um has process margin" -- restated as **parametrically margined, not process-qualified**

## Not open, and not to be relitigated

* the production cooling point, Re = 1264.8, inside its validated domain
* 2300 < Re < 3000 OUT_OF_MODEL_DOMAIN; conjugate CFD NOT COMPLETED
* the TSV allocation law: enlarging a via changes the COUNT and nothing else
* the Z1/Z2 response ordering at D_driver = 1.1943, as a statement about the Phase-0M-R3 configuration
