# PHASE 0M-R2 SECTION 5 --- COOLING CORRELATION REGIME AUDIT

## The finding

**The Phase-0M-R 50 g/s operating point is outside the domain of every correlation this
framework has.** Its reported numbers -- h = 166 000 W/m2K, dp = 1.46 MPa, 74 W of
pumping -- must be withdrawn as model outputs.

`scripts/phase0m/cooling.py` switched from the laminar correlation to Gnielinski at
Re = 2300 and labelled the result `transitional`. Gnielinski is validated from Re = 3000.
The 50 g/s point sits at **Re = 2342**, which is 42 above the laminar ceiling and 658
below Gnielinski's floor. The framework was extrapolating a turbulent correlation into a
regime it does not cover, and the choice is not a detail: at that Reynolds number the
laminar correlation gives Nu = 4.603 and Gnielinski gives Nu = 12.699, a factor of
**2.76**. The reported h was set by the choice of correlation, not by the flow.

## Every operating point, with its correlation and that correlation's domain

| point | m_dot | per channel | Re | regime | Nu | correlation | validity | h_eff | dp | pump | status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| source_stated | 1.6 g/s | 0.00717 g/s | 75.0 | laminar | 4.603 | Shah & London laminar FD | Re <= 2300, fully developed | 22827 | 0.032 MPa | 0.05 W | IN DOMAIN |
| production | 27.0 g/s | 0.12108 g/s | 1264.8 | laminar | 4.603 | Shah & London laminar FD | Re <= 2300, fully developed | 115553 | 0.538 MPa | 14.70 W | IN DOMAIN |
| high_flow | 50.0 g/s | 0.22422 g/s | 2342.3 | transitional | nan | OUT_OF_MODEL_DOMAIN | no validated correlation for 2300 < Re < 3000 | nan | nan MPa | nan W | **OUT_OF_MODEL_DOMAIN** |
| two_sided_per_side | 13.5 g/s | 0.06054 g/s | 632.4 | laminar | 4.603 | Shah & London laminar FD | Re <= 2300, fully developed | 92009 | 0.269 MPa | 3.67 W | IN DOMAIN |

Geometry and fluid state at every point, as required:

| point | D_h | flow area | velocity | rho | mu | k | cp | Pr | coolant rise | coolant max |
|---|---|---|---|---|---|---|---|---|---|---|
| source_stated | 85.7 um | 3.3450 mm2 | 0.484 m/s | 988.0 | 0.001 | 0.6440 | 4181.0 | 3.551 | 149.49 K | 174.49 C |
| production | 85.7 um | 3.3450 mm2 | 8.170 m/s | 988.0 | 0.001 | 0.6440 | 4181.0 | 3.551 | 8.86 K | 33.86 C |
| high_flow | 85.7 um | 3.3450 mm2 | 15.129 m/s | 988.0 | 0.001 | 0.6440 | 4181.0 | 3.551 | 4.78 K | 29.78 C |
| two_sided_per_side | 85.7 um | 3.3450 mm2 | 4.085 m/s | 988.0 | 0.001 | 0.6440 | 4181.0 | 3.551 | 17.72 K | 42.72 C |

## The second finding: the production point is thermally DEVELOPING

The laminar Nusselt number used is the FULLY DEVELOPED value. The thermal entrance length
is `L_t = 0.05 Re Pr D_h`:

| point | L_thermal | channel length | L_t / L | fully developed? |
|---|---|---|---|---|
| source_stated | 1.14 mm | 22.36 mm | 0.05 | yes |
| production | 19.25 mm | 22.36 mm | 0.86 | **no** |
| high_flow | 35.65 mm | 22.36 mm | 1.59 | **no** |
| two_sided_per_side | 9.62 mm | 22.36 mm | 0.43 | **no** |

At the production flow the entrance region occupies **86 %** of the channel. A developing
thermal boundary layer has a HIGHER Nusselt number than the fully-developed value, so the
production model UNDERSTATES h and therefore OVERSTATES temperature. The direction
matters: the production result is conservative, not optimistic. It is carried as a
one-sided bounded uncertainty rather than corrected, because no entrance-region
correlation for this duct family is sourced in this repository.

## What this does and does not change

**Withdrawn.** The 50 g/s point and every number derived from it: h = 166 000 W/m2K,
dp = 1.46 MPa, P_pump = 74 W, and the statement that 7.4 % of the load is needed to reach
the retired calibrated boundary. What can still be said is that the retired calibrated
h = 166 000 W/m2K is **not reachable by any correlation this framework can validate**,
which is a stronger statement about the retired boundary and a weaker one about 50 g/s.

**Unchanged.** The production cooler at 27 g/s sits at Re = 1264.8, comfortably laminar
and inside the correlation's domain. Every Phase-0M-R conclusion that rests on the
production point stands: the physical cooler changes absolute responses strongly, and it
makes ARCH_Z2 the hottest of the principal candidates.
