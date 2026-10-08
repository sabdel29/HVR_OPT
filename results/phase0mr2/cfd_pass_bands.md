# PHASE 0M-R2 SECTION 6 --- CONJUGATE CFD PASS BANDS, DECLARED BEFORE THE RUN

Written and committed to disk BEFORE any solver was launched, so the bands cannot be
chosen after seeing the answer.

| quantity | band | why this number |
|---|---|---|
| outlet coolant temperature | **<= 3 %** | the fluid-side energy balance is exact by construction in the compact model, so any disagreement here is a CFD discretisation or property-table difference, not physics. A tight band is appropriate. |
| pressure drop | **<= 10 %** | the compact model uses a fully-developed friction factor and charges no entrance, exit, header or manifold loss. A single-channel CFD case with developing flow will read higher. 10 % is the loosest band because it is the quantity the compact model most clearly under-models. |
| mean wall temperature rise above inlet | **<= 5 %** | this is the quantity the compact model is FOR. A wider band would make the comparison uninformative. |
| effective thermal resistance | **<= 7 %** | R_total is the sum of three terms with independent errors (base conduction, convection, caloric). 7 % allows each to carry a few percent without the sum being called a failure. |

**Verdict rule, also fixed in advance.**

* **CFD VALIDATED** --- every quantity inside its band.
* **CFD CONDITIONAL** --- the thermal quantities inside their bands, pressure drop outside
  its band. The compact model would then be usable for temperature and not for pumping.
* **CFD REJECTED** --- any thermal quantity outside its band.
* **CFD UNAVAILABLE / NOT COMPLETED** --- the case could not be made physically valid, or
  did not converge. This is an acceptable outcome and is reported as itself, never
  upgraded.

**No compact-model constant will be tuned case by case.** If the compact model disagrees,
the disagreement is the result.

**Geometry.** The production channel: 50 um wide, 300 um tall, 50 um fin, 100 um base,
22.36 mm long, silicon at k = 130 W/mK, water at the declared reference properties, at the
production flow of 27 g/s total. One channel with symmetry half-fins on both sides, which
is the unit cell the compact model itself represents.
