# PHASE 0M PART 40 --- NEW CROSS-DOMAIN ETM DESIGN LEVERS

A lever qualifies here only if it moves at least two domains in OPPOSITE or non-obvious
directions, and only if Phase 0M measured it.

## 1. TSV allocation POLICY, not TSV radius

The radius is not a loss lever for a minimum-provisioned field: `R_field = rho h J_max / I`
contains no geometry at all, and `phi_Cu = I / (J_max A_field)` contains neither the radius
nor the height, so the thermal and mechanical effective properties do not move either.
The lever is the POLICY and the provisioning current density.

| what moves | electrical | thermal | mechanical | feasibility |
|---|---|---|---|---|
| radius, policy A | **nothing** (0.07 % over r = 2.5 to 50 um) | nothing | nothing | improves |
| radius, policy B | `1/r^2`, 314 % | `phi ~ r^2` | `phi ~ r^2` | worsens |
| provisioning `J_max` | `R ~ J_max` | `phi ~ 1/J_max` | `phi ~ 1/J_max` | improves |

**Derating harder LOWERS the loss.** Halving `J_max` halves the field resistance and doubles
the copper fraction, at twice the area. No part of the current framework can express that,
because `J_max` enters only as a feasibility check.

## 2. Liner fraction, which is `t_ox / r` and not a thickness

At the SAME copper fraction (0.196) and the same `k_z`, a 5 um via at 20 um pitch gives
`k_xy = 94.9` W/m.K against
`142.4` for a 15 um via at 60 um pitch --- a
1.50x difference
caused entirely by the liner occupying a larger fraction of a smaller via. Fine-pitch TSV
fields are thermally worse in plane at equal copper. Electrically they are identical.

## 3. RDL copper: three domains, three different signs

More RDL copper lowers the electrical loss, raises lateral thermal spreading and raises the
copper fraction of a layer whose CTE sits between silicon and organic. Phase 0M adds the
quantity that was missing: the RDL is **153x to 276x anisotropic** in plane, so "more copper"
is direction-dependent and the framework's single isotropic `k` cannot express it.

## 4. Transition geometry, which is worth more than the transition

`K_crowd` spans **0.606 to 1.483** over 107 converged geometries
against the single constant 1.326 in use. More usefully, the EXCESS resistance `dR` is
length-INDEPENDENT to five decimals while `K_crowd` is not, so `dR` is the transferable
quantity and `K_crowd` is an artifact of how much bulk conductor one attaches to the
transition. A generous landing pad can make `K_crowd < 1`.

## 5. Component z placement changes feasibility before it changes loss

Three of eight partition templates do not fit the 500 mm2 die shadow; a single-level VR
misses by 1.76x. The `T4_SPLIT_SC_BUCK` template puts an intermediate 16 V rail across a
tier boundary --- a rail the power-path graph cannot currently represent.

## 6. Cooling mass flow, which is a MECHANICAL variable

The coolant temperature rise is an IN-PLANE gradient across the die. Measured on the global
model with only the sink field changed:

| coolant rise across the die | T_max shift | die warpage shift |
|---|---|---|
| 0.00 K | 0.00 K | 0.00 % |
| 9.97 K | 2.02 K | 1.52 % |
| 26.91 K | 5.46 K | 4.10 % |
| 53.81 K | 11.34 K | 8.19 % |

A uniform Robin boundary sets both to zero by construction. Flow rate is therefore a
mechanical design variable, and pumping power is a real cost: reaching the calibrated
`h = 166 kW/m2K` needs about 74 W, **7.4 % of the load**, which nothing in the framework
charges.

## 7. Intra-VR metallization, which is a loss term nobody has

4.06 to 39.31 W system-wide depending on the RDL stack and the via
allocation policy --- 0.41 % to 3.93 % of the load,
against a converter loss of 125.3 W. It is common-mode across architectures, so it does not
reorder them, but it is not small and it is currently zero.

## Summary: what should become an optimizer variable

| variable | why it qualifies | measured effect |
|---|---|---|
| TSV allocation policy | sets whether radius matters at all | 0.07 % vs 314 % on field R |
| provisioning `J_max` | inverts the usual area/loss trade | `R ~ J_max` exactly |
| `t_ox / r` (liner fraction) | thermal-only, invisible electrically | 1.5x on in-plane k |
| RDL `t x N_layers` | electrical, thermal spreading, stiffness | 4.06 to 39.31 W intra-VR |
| pad / trace transition geometry | 2.4x on a factor now held constant | `K_crowd` 0.61 to 1.48 |
| component partition template | decides FEASIBILITY, not loss | 3 of 8 do not fit |
| coolant mass flow | thermal AND mechanical | 8.2 % warpage, 74 W pumping |
| lateral rail voltage (Z5 family) | 2.5D is not one point | 768 W to 0.33 W |
