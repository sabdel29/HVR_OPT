# PHASE 0M-R SECTION 9 --- THE RDL IN THE MECHANICAL MODEL

## What was missing

The layer between the substrate top and the die is 10 um of `underfill_homog` --- E = 8 GPa,
k = 0.7 W/m.K isotropic --- and the package stack calls it *"homogenized microbump +
underfill"*. The redistribution metal that carries the entire 1 V rail is not in it. Two
things are wrong as a result, and they pull in opposite directions:

| | model | measured (Section 8) | error |
|---|---|---|---|
| in-plane conductivity | 0.7 W/m.K | 92 to 335 W/m.K | **two to three orders of magnitude low** |
| in-plane modulus | 8 GPa | 48 to 104 GPa | **six to thirteen times too compliant** |
| through-thickness conductivity | 0.7 W/m.K | 0.8 to 2.7 W/m.K | roughly right, by accident |

## Fidelity ladder

| rung | interface layer |
|---|---|
| M-RDL0 | as built: 10 um of `underfill_homog` |
| M-RDL1 | same thickness, composite RDL + bump properties, orthotropic conductivity |
| M-RDL2 | true thickness (40 um RDL stack + 10 um bump layer), same properties |

| rung | architecture | corner shear | die warpage | T_max |
|---|---|---|---|---|
| M-RDL0 | Z1_EMBEDDED | 2.7486 um | 20.0753 um | 84.962 C |
| M-RDL0 | Z2_BACKSIDE | 2.0796 um | 17.2747 um | 83.447 C |
| M-RDL1 | Z1_EMBEDDED | 2.6502 um | 19.1794 um | 83.026 C |
| M-RDL1 | Z2_BACKSIDE | 2.0044 um | 16.4784 um | 81.448 C |
| M-RDL2 | Z1_EMBEDDED | 2.9358 um | 20.6659 um | 89.703 C |
| M-RDL2 | Z2_BACKSIDE | 2.2237 um | 17.8771 um | 88.222 C |

## The six questions

| question | answer |
|---|---|
| 1. does it change global warpage? | **Yes** --- 20.075 to 20.666 um on Z1, -4.4 % at M-RDL1 and +2.9 % at M-RDL2 |
| 2. does it change corner shear? | **Yes** --- -3.6 % at M-RDL1, +6.8 % at M-RDL2 |
| 3. does it alter the Z1/Z2 ordering? | **No.** The ratio moves 1.3217 -> 1.3222 -> 1.3202, a shift of at most 0.11 %, and never approaches unity |
| 4. does it give a meaningful RDL damage driver? | Not yet. The layer is homogenized, so it carries an average stress and not a trace-level one |
| 5. is local RDL stress mesh-convergent? | **Not tested at rung M-RDL2** and deliberately not claimed. A homogenized layer has no local stress to converge |
| 6. is the result material-property dominated? | **Yes** --- the two rungs differ only in thickness and they bracket the baseline in opposite directions |

## What this does NOT establish

**No RDL allowable is invented.** The added layer gives a stress RESPONSE and there is no
inequality to compare it with, so it remains response coupling, exactly as the global warpage
metric has been since Phase 0H. Nothing here converts the RDL into a constraint.

Nor is a trace-level RDL stress computed. That would be rung M-RDL3 --- explicit
redistribution geometry near the critical corner --- and it needs a declared averaging volume
and a convergence study before any number from it could be used, because a metal/dielectric
corner is singular and a point maximum would be meaningless.

## Conclusion

Putting the RDL into the model is worth doing: it moves the absolute mechanical response by
up to 7 % and the peak temperature by up to 4.7 K, both of which the incumbent model gets
wrong. It does not change the architecture ranking, and it does not create a constraint.
