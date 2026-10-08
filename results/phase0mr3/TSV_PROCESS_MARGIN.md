# PHASE 0M-R3 SECTION 7 --- TSV PROCESS MARGIN

## The hard rule and the design margin are different questions

    hard rule      AR = L/d <= AR_max = 10
    design margin  M_AR = AR_max / AR_actual

Phase 0M-R2 reported ARCH_Z2, Z4 and Z5 at AR = 10.000 exactly. That passes the rule and
gives **M_AR = 1.000**, which is not margin -- it is the boundary.

| architecture | d | AR nominal | M_AR nominal | AR worst | M_AR worst | under a modest bound |
|---|---|---|---|---|---|---|
| Z1_EMBEDDED | 30 um | 2.467 | 4.054 | 2.567 | 3.895 | OK |
| Z1_EMBEDDED | 34 um | 2.176 | 4.595 | 2.265 | 4.414 | OK |
| Z1_EMBEDDED | 40 um | 1.850 | 5.405 | 1.926 | 5.193 | OK |
| Z2_BACKSIDE | 30 um | 10.000 | 1.000 | 10.408 | 0.961 | **FAILS** |
| Z2_BACKSIDE | 34 um | 8.824 | 1.133 | 9.184 | 1.089 | OK |
| Z2_BACKSIDE | 40 um | 7.500 | 1.333 | 7.806 | 1.281 | OK |

## The tolerance bound is a PARAMETRIC BOUND, not a distribution

No source in this repository gives a TSV fabrication tolerance, so none is invented and no
Gaussian is assumed. Three labelled cases are swept:

| case | diameter | liner | via depth |
|---|---|---|---|
| none | 0 % | 0 % | 0 % |
| modest | -2 % | +10 % | +2 % |
| loose | -5 % | +20 % | +5 % |

The worst corner is the smallest diameter with the deepest via, which is the physically
correct pairing for an aspect-ratio limit.

## Result

**The 30 um via does NOT survive a modest bound on ARCH_Z2.** At -2 % diameter and +2 %
depth the aspect ratio reaches 10.408 and the hard rule is violated. ARCH_Z1, whose vias
traverse 74 um rather than 300 um, sits at M_AR = 3.895 even under the modest bound and is
unaffected.

**The smallest sourced diameter that restores positive margin is 34 um**, M_AR = 1.089.
That is inside the sourced range `design_variables.tsv.radius_m = {lo 2.5, nominal 15,
hi 50} um`, so it requires no new process.

## What changing the diameter costs --- almost nothing, and that is the point

| quantity | 30 um | 34 um | change |
|---|---|---|---|
| vias required | 15 140 | 11 692 | **-22.8 %** |
| copper fraction | 0.020002 | 0.020002 | -0.00 % |
| field resistance | 0.64026 uOhm | 0.64027 uOhm | +0.00 % |
| k_z | 134.92 W/mK | 134.94 W/mK | +0.02 % |
| E_xy | 167.18 GPa | 167.22 GPa | +0.02 % |
| CTE_eff | 2.7996e-6 | 2.7997e-6 | +0.00 % |

This is the Phase-0M TSV allocation law confirmed on a case it was not derived for: under
minimum-capability provisioning the copper fraction is radius-independent, so enlarging
the via changes the COUNT and essentially nothing else. The electrical, thermal and
mechanical behaviour of the field is unchanged to 0.02 %.

**Consequence for this phase.** The frozen realizability contract tests the HARD RULE,
which 30 um passes, so the frozen pair remains contract-compliant and the margin is
reported separately exactly as the contract requires. But ARCH_Z2 as frozen has no process
margin on its TSV field, and that is a named condition on its realizability, not a detail.
Closing it costs 22.8 % more vias and no measurable E/T/M change.
