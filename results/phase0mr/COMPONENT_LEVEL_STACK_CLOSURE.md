# PHASE 0M-R SECTION 7 --- COMPONENT PARTITION AS PHYSICAL GEOMETRY

Phase 0M classified a template as "fits" on AREA alone. Area is one of six independent
questions and it is not the binding one.

## Z-envelopes

| template | tier | components | z_min | z_max | tier height | RDL above |
|---|---|---|---|---|---|---|
| T1_EMBEDDED_4LAYER | 0 | gan_hs | 0.0 | 685.0 | 685.0 um | 10.0 um |
| T1_EMBEDDED_4LAYER | 1 | gan_ls | 695.0 | 1301.0 | 606.0 um | 10.0 um |
| T1_EMBEDDED_4LAYER | 2 | cap_fly | 1311.0 | 1411.0 | 100.0 um | 10.0 um |
| T1_EMBEDDED_4LAYER | 3 | inductor+cap_out | 1421.0 | 1921.0 | 500.0 um | 0.0 um |
| T4_SPLIT_SC_BUCK | 0 | gan_hs+cap_fly | 0.0 | 685.0 | 685.0 um | 10.0 um |
| T4_SPLIT_SC_BUCK | 1 | gan_ls+inductor+cap_out | 695.0 | 1301.0 | 606.0 um | 0.0 um |
| T2_BACKSIDE_CHIPLET | 0 | gan_hs+gan_ls | 0.0 | 685.0 | 685.0 um | 10.0 um |
| T2_BACKSIDE_CHIPLET | 1 | cap_fly | 695.0 | 795.0 | 100.0 um | 10.0 um |
| T2_BACKSIDE_CHIPLET | 2 | inductor+cap_out | 805.0 | 1305.0 | 500.0 um | 0.0 um |
| T0_SINGLE_LEVEL | 0 | gan_hs+gan_ls+cap_fly+cap_out+inductor | 0.0 | 685.0 | 685.0 um | 0.0 um |

Two corrections to the Phase-0M templates, both of which changed a verdict:

* **The high-side device is BELOW the substrate** in the embedded architecture --- June-2026
  Sec. II flip-chips it to the bottom RDL --- so it must not be charged against substrate
  thickness. With that fixed, T1's charged height is **1226 um**, which reproduces Phase 0H's
  independently-derived embedded-cell height exactly.
* **The output capacitor was tiered with the flying capacitors**, which alone pushed that
  tier to 6.00 mm2. It belongs with the output.

A third correction is to the CHECK rather than the template: the 5.61 mm2 tile is an OUTPUT
of the converter area model (`max()` over component classes), so constraining a level to it
would be circular. The bound is the die shadow --- 500 mm2 for the array, 10.20 mm2 per cell
per level.

## Six feasibility questions, answered separately

| template | architecture | charged height / available | area | height | routing | thermal | verdict |
|---|---|---|---|---|---|---|---|
| T1_EMBEDDED_4LAYER | Z1_EMBEDDED | 1226 / 1250 um | True | True | False | False | BLOCKED: ROUTING_FEASIBLE, THERMAL_FEASIBLE |
| T1_EMBEDDED_4LAYER | Z2_BACKSIDE | 1921 / 1100 um | True | False | False | True | BLOCKED: HEIGHT_FEASIBLE, ROUTING_FEASIBLE |
| T1_EMBEDDED_4LAYER | Z4_POWER_DIE | 1921 / 1200 um | True | False | False | False | BLOCKED: HEIGHT_FEASIBLE, ROUTING_FEASIBLE, THERMAL_ |
| T4_SPLIT_SC_BUCK | Z1_EMBEDDED | 1301 / 1250 um | False | False | True | True | BLOCKED: AREA_FEASIBLE, HEIGHT_FEASIBLE |
| T4_SPLIT_SC_BUCK | Z2_BACKSIDE | 1301 / 1100 um | False | False | True | True | BLOCKED: AREA_FEASIBLE, HEIGHT_FEASIBLE |
| T4_SPLIT_SC_BUCK | Z4_POWER_DIE | 1301 / 1200 um | False | False | True | True | BLOCKED: AREA_FEASIBLE, HEIGHT_FEASIBLE |
| T2_BACKSIDE_CHIPLET | Z1_EMBEDDED | 1305 / 1250 um | False | False | False | True | BLOCKED: AREA_FEASIBLE, HEIGHT_FEASIBLE, ROUTING_FEA |
| T2_BACKSIDE_CHIPLET | Z2_BACKSIDE | 1305 / 1100 um | False | False | False | True | BLOCKED: AREA_FEASIBLE, HEIGHT_FEASIBLE, ROUTING_FEA |
| T2_BACKSIDE_CHIPLET | Z4_POWER_DIE | 1305 / 1200 um | False | False | False | True | BLOCKED: AREA_FEASIBLE, HEIGHT_FEASIBLE, ROUTING_FEA |
| T0_SINGLE_LEVEL | Z1_EMBEDDED | 685 / 1250 um | False | True | True | True | BLOCKED: AREA_FEASIBLE |
| T0_SINGLE_LEVEL | Z2_BACKSIDE | 685 / 1100 um | False | True | True | True | BLOCKED: AREA_FEASIBLE |
| T0_SINGLE_LEVEL | Z4_POWER_DIE | 685 / 1200 um | False | True | True | True | BLOCKED: AREA_FEASIBLE |

**No template is FULLY_REALIZABLE.** The closest is **T1 in the embedded architecture**,
which passes area and height and is blocked on routing (the output plane needs more copper
than the reference stack provides) and on thermal depth. T4 misses the area bound by 2 %.

## Package clearances are OPEN, not zero

Three clearances no source in this repository gives:

* the minimum gap between the compute-die underside and the tallest VR component;
* the cavity sidewall allowance for an embedded component;
* the standoff between the cooled surface and the nearest active component.

Every template therefore carries `PACKAGE_CLEARANCE_OPEN = True` and **none may be called
buildable**. Assuming them to be zero would convert three unknowns into a pass.

## Does a partition put an intermediate rail across a tier boundary?

| template | crossings | consequence |
|---|---|---|
| T1_EMBEDDED_4LAYER | MID 16V 1.44A; SW 1V 20.4A | an intermediate rail crosses the boundary, carrying 1.44 A instead of 20.4 A -- an I^2 reduction of 202x |
| T4_SPLIT_SC_BUCK | MID 16V 1.44A | an intermediate rail crosses the boundary, carrying 1.44 A instead of 20.4 A -- an I^2 reduction of 202x |
| T2_BACKSIDE_CHIPLET | SW 1V 20.4A | no intermediate rail crosses a tier boundary |
| T0_SINGLE_LEVEL | none | no intermediate rail crosses a tier boundary |

**T1 and T4 both put the 16 V intermediate rail across a tier boundary, carrying 1.44 A
where the 1 V rail would carry 20.4 A --- a factor of 200 in `I^2`.** T4 does it with only
one crossing, so its entire inter-tier conduction happens at the intermediate voltage. That
is why T4's vertical intra-VR loss is essentially zero while T1's is not.
