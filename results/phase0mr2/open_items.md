# PHASE 0M-R2 --- OPEN ITEMS

Ranked. Every item is OPEN in the strict sense: not determined, and never defaulted.

## Blocking

| # | item | why open | what it blocks | what would close it |
|---|---|---|---|---|
| 1 | **ARCH_Z4 power-die construction** | no source describes a monolithic power-die process | the Z4 ranking, which is first place stacked and second planar | one process description, or a decision that the stacked construction is the design |
| 2 | **transitional-regime Nusselt correlation** | none in this repository for 2300 < Re < 3000 | any operating point above 27 g/s; the two neighbours differ by 2.76x | a sourced transitional correlation, or an explicit decision to cap the model at Re < 2300 |
| 3 | **area, routing and current-density shortfalls** | the converter area model outputs 5.61 mm2 per level against a 10.20 mm2 budget, and T4 exceeds it | realizability, more than the clearances do | a component topology the converter model supports |
| 4 | **three package clearances** | no framework source, no accessible foundry rule, nothing usable in the literature | calling any template buildable --- but NOT the binding constraint | a process design rule from a named vendor |
| 5 | **high-stress SAC305 constitutive response** | no primary data above about 16 MPa at 45-150 C | every absolute reliability number, and the MAGNITUDE of the relative one | coupon characterisation at 15-100+ MPa |
| 6 | **required life N_required** | not published for this system | the falsification gate G2 | a statement from the system owner |
| 7 | **mechanical allowable** | nine candidates tested, none admissible | turning the response into a constraint | a published allowable tied to a failure mode |
| 8 | **electromigration allowable** | no primary study with its conditions | a feasibility verdict on any via field | one primary EM study |
| 9 | **cohesive-zone parameters** | unsourced | predicting delamination at all | interface fracture testing |

## Non-blocking

| item | status |
|---|---|
| conjugate CFD validation | see `CONJUGATE_CFD_VALIDATION.md` |
| entrance-region Nusselt correlation | OPEN. At 27 g/s the entrance occupies 86 % of the channel, so the production temperature is conservative. Carried as a one-sided bound |
| density and specific heat of `hvr_effective` | OPEN. Needed only for transient claims; none are made |
| pump efficiency | OPEN. Hydraulic power is primary; a 35/55/75 % band is carried |
| polymer viscoelastic spectra | no DMA data; a modulus sensitivity is carried |
| trace-level RDL stress | needs explicit geometry, a declared averaging volume and a convergence study; no allowable exists for it anyway |

## Not open, and not to be relitigated

* **Z2 better than Z1 on the solder-fatigue driver** --- survives every Phase-0M-R2 correction, ratio 1.1942.
* **The TSV span per architecture** --- one source, enforced across all three domains.
* **DEFECT #54 and #55** --- both confirmed, fixed and negative-tested.
* **The production cooling point at 27 g/s** --- inside its correlation's validated domain.
* **Pumping power is FACILITY scope** --- not in the loss objective, not in the thermal mesh.
