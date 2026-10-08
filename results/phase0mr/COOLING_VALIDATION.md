# PHASE 0M-R SECTION 11 --- COOLING VALIDATION

## The compact model has three parts and they are validated separately

| part | what it is | how it is validated |
|---|---|---|
| FLUID SIDE | `m_dot cp dT = Q`, the Nusselt correlation, the friction factor | ANALYTICALLY: energy balance to machine precision, correlation used only inside its stated Reynolds range |
| SOLID SIDE | fin efficiency, area amplification, base conduction | NUMERICALLY against MOOSE on the explicit finned solid |
| COUPLING | streamwise fluid temperature feeding back on the wall | by construction: iterated to a fixed point in the production solve, with the removed energy compared against the deposited energy |

MOOSE cannot model the flow. Saying otherwise would be the same category error as calling an
electrostatic solve a DC conduction validation, which this project has already refused to do
once. It is used for the conduction problem it can pose exactly.

## Predeclared acceptance, fixed before running

solid-side thermal resistance: <= 5 % ACCEPTED, <= 10 % CONDITIONAL, else REJECTED;
energy balance <= 0.1 %.

## Fluid side --- energy balance

| design | m_dot | Re | regime | dT_fluid | Q from `m_dot cp dT` | residual |
|---|---|---|---|---|---|---|
| TOP_SI_MICROCHANNEL_27 | 27.0 g/s | 1265 | laminar | 9.97 K | 1125.00 W | **0.00 %** |
| TOP_SI_MICROCHANNEL_50 | 50.0 g/s | 2342 | transitional | 5.38 K | 1125.00 W | **0.00 %** |
| TOP_CU_COLDPLATE_27 | 27.0 g/s | 1482 | laminar | 9.97 K | 1125.00 W | **0.00 %** |
| TWO_SIDED_SI_14 | 13.5 g/s | 632 | laminar | 9.97 K | 562.50 W | **0.00 %** |
| SUBSTRATE_EMBEDDED_27 | 27.0 g/s | 2965 | transitional | 9.97 K | 1125.00 W | **0.00 %** |

Exact for every design.

## Solid side --- against MOOSE on the explicit finned geometry

A half-fin plus half-channel unit cell, base heated with a uniform flux, wetted walls
convective to the fluid, symmetry on the mid-planes. The compact model's fin efficiency and
area amplification are compared with the resistance the explicit solve returns.

| case | fin efficiency | area amplification | R compact | R MOOSE | error | verdict |
|---|---|---|---|---|---|---|
| TuckermanPease_50x302 | 0.7666 | 5.13 | 6.4033e-06 | 6.1699e-06 | **3.78 %** | **ACCEPTED** |
| wide_100x200 | 0.8562 | 2.21 | 6.1063e-06 | 5.5458e-06 | **10.11 %** | **REJECTED** |
| tall_50x500 | 0.5632 | 6.13 | 5.3826e-06 | 5.4517e-06 | **1.27 %** | **ACCEPTED** |
| copper_100x500 | 0.9322 | 5.16 | 1.1633e-05 | 1.0971e-05 | **6.04 %** | **CONDITIONAL** |

**The compact solid model is valid where the fin is tall and thin and degrades where it is
short and thick.** That is the expected failure mode: the straight-fin formula assumes 1-D
conduction along the fin, which stops holding when the fin is only twice as tall as it is
thick. The `wide_100x200` case is 10.1 % and is REJECTED against the predeclared band; the
copper cold plate is 6.0 % and CONDITIONAL.

**The production cooler is the Tuckerman-Pease geometry at 3.78 %, inside the accepted
band.** The compact model is therefore authorised for the production configuration and NOT
for short, thick fins, and that boundary is recorded rather than glossed.

## Pumping power is reported, never folded in

`P_electronics` and `P_pumping` are separate quantities throughout. Pump efficiency is not
sourced, so **hydraulic power is the primary figure** and a shaft-power band at 35 %, 55 %
and 75 % efficiency is carried beside it in `cooling_energy_balance.csv`.

## Icepak

**Not revisited in this phase.** The earlier Phase-0E attempt returned exactly 5000 K on
every object -- a solver clamp meaning the external boundary never took effect -- and that
result stays discarded. The Icepak licence IS available (`elec_solve_icepak`, 1 seat,
verified free), so the door is open; what this phase did instead was validate the two halves
of the compact model against tools that could pose each half exactly. **No Icepak validation
is claimed, and none may be claimed until a canonical single-channel benchmark reproduces the
analytical correlation.** That benchmark is named as the next action rather than asserted.
