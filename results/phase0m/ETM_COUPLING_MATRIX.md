# PHASE 0M PARTS 34-37 --- THE ETM COUPLING MATRIX

## The matrix

| from \ to | ELECTRICAL | THERMAL | MECHANICAL | DAMAGE |
|---|---|---|---|---|
| **ELECTRICAL** | -- | **PRESENT** loss -> heat, iterated to a fixed point | indirect, through T | absent |
| **THERMAL** | **PRESENT** rho(T), R_DS(on)(T), DCR(T) | -- | **PRESENT** thermal strain drives the global and local mechanics | indirect, through M |
| **MECHANICAL** | **ABSENT** --- measured at 0.16 % of R | **ABSENT** --- measured at 1.5 K for a 4 % bond-line change | -- | **ABSENT** no damage variable exists |
| **DAMAGE** | **ABSENT** --- would be +33 % R at 25 % joint area lost | **ABSENT** --- would be +12.5 K at 25 % delaminated | **ABSENT** | -- |

## Every absent arrow, with a number

| direction | mechanism | quantity | value | against | ratio | verdict |
|---|---|---|---|---|---|---|
| M->E | elastic deformation changes conductor geometry | dR/R | 0.001619 | 0.2274 | 0.00712 | **NEGLIGIBLE** |
| M->E | contact pressure changes contact resistance | applicability | 0 | 0 | 0 | **NOT APPLICABLE (intact package)** |
| M->E | crack reduces conducting cross-section | dR/R at 5 % joint area lost | 0.05263 | 0.2274 | 0.231 | **MATERIAL ONLY WITH DAMAGE** |
| M->E | crack reduces conducting cross-section | dR/R at 25 % joint area lost | 0.3333 | 0.2274 | 1.47 | **MATERIAL ONLY WITH DAMAGE** |
| M->E | crack reduces conducting cross-section | dR/R at 50 % joint area lost | 1 | 0.2274 | 4.4 | **MATERIAL ONLY WITH DAMAGE** |
| M->E | electromigration voiding changes resistance | applicability | nan | nan | nan | **OPEN -- NO DATA** |
| M->T | warpage changes the TIM bond line | dT_j at 2 % bond-line change | 0.75 | 51.05 | 0.0147 | **SECOND ORDER BUT NOT ZERO** |
| M->T | warpage changes the TIM bond line | dT_j at 4 % bond-line change | 1.5 | 51.05 | 0.0294 | **SECOND ORDER BUT NOT ZERO** |
| M->T | warpage changes the TIM bond line | dT_j at 10 % bond-line change | 3.75 | 51.05 | 0.0735 | **SECOND ORDER BUT NOT ZERO** |
| M->T | contact pressure changes interface thermal conductance | applicability | 0 | 0 | 0 | **NOT APPLICABLE (intact package)** |
| M->T | delamination removes interface thermal conductance | local dT_j at 5 % of the die area delaminated | 1.974 | 51.05 | 0.0387 | **MATERIAL ONLY WITH DAMAGE** |
| M->T | delamination removes interface thermal conductance | local dT_j at 25 % of the die area delaminated | 12.5 | 51.05 | 0.245 | **MATERIAL ONLY WITH DAMAGE** |

## Part 35 --- when does mechanics feed back electrically?

**Not before damage, by more than two orders of magnitude.** A free thermal expansion of
9.7e-4 over the operating excursion changes a conductor's resistance by
`eps (1 + 2 nu) = 0.16 %`. Over the same excursion `rho(T)` changes it by **22.8 %**, and
that term IS modelled. The geometric feedback is 0.7 % of a term already in the loop, and
far below the 2.4x spread in the current-crowding factor measured in Part 8.

Contact-pressure feedback does not apply: every current-carrying interface in this package is
metallurgical. There is no pressure contact in the power path.

Electromigration voiding is **OPEN, not negligible** --- the EM current-density limit itself
could not be sourced, so its resistance drift cannot be estimated and must not be invented.

**Conclusion: retain ONE-WAY mechanics. An iterative M -> E loop would consume solver time
to chase a term 137x smaller than one already present.**

## Part 36 --- when does mechanics feed back thermally?

**Second order, but not zero, and for a reason worth recording.** At the calibrated
`h = 166 kW/m2K` the convective resistance is 0.0121 K/W while the 50 um TIM contributes
0.0333 K/W: **the compliant polymer layer, not the cooler, dominates the junction-to-coolant
path.** A 4 % change in the bond line is therefore worth 1.5 K, or 2.9 % of the junction rise.

Not enough to justify an iterative loop for the intact package. Enough that TIM bond-line
thickness belongs in the cooling design-variable set, which Part 24 places it in.

With damage it is a different question: 25 % delamination is 12.5 K, which would change the
converter loss, the temperature, and the mechanics in turn.

## Part 37 --- "fully coupled ETM", defined

| level | definition | status | necessary for |
|---|---|---|---|
| **ETM-L1** | `E <-> T -> M` | THE CURRENT FRAMEWORK | architecture RANKING on electrical, thermal and relative solder-fatigue response |
| **ETM-L2** | `E <-> T <-> M` | NOT BUILT | packages with pressure contacts, sockets, or a deformation-sensitive bond line |
| **ETM-L3** | `E <-> T <-> M <-> DAMAGE` | NOT BUILT | predicting failure PROGRESSION, electrical opens, thermal runaway after delamination |

**Where this project is: ETM-L1.** E and T are iterated to a fixed point; T drives M; M
returns nothing.

**What each goal needs:**

* **architecture RANKING --- ETM-L1 is sufficient.** The absent arrows are 0.7 % and 2.9 % of
  terms already present, and they are common-mode across architectures.
* **absolute LIFETIME --- ETM-L1 is sufficient for the mechanics, and insufficient for other
  reasons.** The blockers are the high-stress constitutive response, the absence of a
  required life, and process history --- not the coupling direction.
* **failure PROGRESSION --- ETM-L3 is required.** Predicting what happens after a crack
  starts needs damage feeding back into conductance and stiffness. Nothing less will do, and
  nothing in this project currently does any of it.

A staggered iterative solution would be acceptable at L2 or L3; a monolithic multiphysics
solve is not required, and would be a poor use of effort given the feedback magnitudes above.
