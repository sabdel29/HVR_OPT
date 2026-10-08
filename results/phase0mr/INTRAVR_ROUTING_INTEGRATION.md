# PHASE 0M-R SECTIONS 5-6 --- INTRA-VR ROUTING AND TRANSITION RESISTANCE IN PRODUCTION

## The loss ledger: one owner per watt

Every term in the system total declares the module that computes it. A second writer to any
term RAISES. The conduction split is re-derived from the upstream closed form and checked
against the upstream aggregate to machine precision; **if it does not reproduce its own
total, the ledger refuses to produce a total at all**, because a decomposition that cannot
reproduce its aggregate is a guess rather than a split.

| term | owner | Z2 BEFORE | Z2 AFTER |
|---|---|---|---|
| `P_switch_hs_conduction` | upstream conduction | 9.8822 W | 11.0440 W |
| `P_switch_ls_conduction` | upstream conduction | 89.2487 W | 99.7408 W |
| `P_inductor_DCR` | upstream conduction | 13.5502 W | 14.5243 W |
| `P_cap_ESR` | upstream conduction | 1.4402 W | 1.4402 W |
| `P_switching_hard` | upstream switching | 5.3024 W | 5.3024 W |
| `P_gate` | upstream switching | 2.9590 W | 2.9590 W |
| `P_Coss` | upstream switching | 1.3409 W | 1.3409 W |
| `P_intraVR_metal` | **phase0mr.routing_production** | 0.0000 W | 3.6657 W |
| `P_intraVR_vertical` | **phase0mr.routing_production** | 0.0000 W | 1.9006 W |
| `P_TSV` | interconnect, R_bulk + dR | 1.6640 W | 1.0019 W |
| `P_bumps` | interconnect, R_bulk + dR | 0.1671 W | 0.0171 W |
| `P_pkg_RDL` | multilayer sheet | 0.6354 W | 0.6751 W |
| `P_other` | unassigned; must be zero | 0.0000 W | 0.0000 W |

**No double counting is possible by construction**, not by convention: the upstream converter
model owns every device and passive parasitic and contains no metallization, and this module
owns only the metal.

## How much intra-VR routing adds

Across every stack, current density and via-allocation policy examined, the Level-1 term is
**4.55 to 43.84 W** system-wide. At the reference stack it is:

| template | tiers | lateral | vertical | system | of the 1 kW load | infeasible nets |
|---|---|---|---|---|---|---|
| T0_SINGLE_LEVEL | 1 | 0.10899 W | 0.00000 W | **5.340 W** | 0.53 % | 0 |
| T1_EMBEDDED_4LAYER | 4 | 0.03608 W | 0.06535 W | **4.970 W** | 0.50 % | 2 |
| T2_BACKSIDE_CHIPLET | 3 | 0.03850 W | 0.06722 W | **5.180 W** | 0.52 % | 2 |
| T4_SPLIT_SC_BUCK | 2 | 0.10657 W | 0.00017 W | **5.230 W** | 0.52 % | 0 |

## Is it still common mode? --- the Phase-0M claim, retested

Phase 0M said intra-VR routing is common-mode across Z1, Z2 and Z4. **That was true only
while all three instantiated the same component-level layout.** Measured across partition
templates at a fixed stack, it varies by **7.5 %** --- small against the term, but no longer
zero, and the mechanism is clear: a template that splits by voltage domain puts the 16 V
intermediate rail across the tier boundary instead of the 1 V rail, and its vertical
metallization loss collapses by three orders of magnitude.

| template | vertical loss per VR | why |
|---|---|---|
| T0_SINGLE_LEVEL | 0.00000 W | no tier boundary to cross |
| T1_EMBEDDED_4LAYER | 0.06535 W | the 1 V rail at 20.4 A crosses a boundary |
| T2_BACKSIDE_CHIPLET | 0.06722 W | the 1 V rail at 20.4 A crosses a boundary |
| T4_SPLIT_SC_BUCK | 0.00017 W | the intermediate rail crosses the boundary at 1.44 A |

## Transition resistance in production

`CROWDING_DEFAULT = 1.326` no longer appears in any production path. Each class carries its
own `dR`, solved exactly at its production geometry by the finite-volume solver that was
cross-validated against MOOSE to 0.25-0.73 %.

The effect on the package is not a uniform inflation. At the nominal TSV geometry `dR` is
**negative**: the retired constant added 32.6 % to every tier, while the solved value
*reduces* the TSV field resistance. On the Z2 architecture, where the 1 V rail crosses the
substrate, that moves `P_TSV` from **1.6640 W** to
**1.0019 W** and `P_bumps` from
**0.1671 W** to **0.0171 W**.

## Net effect on each architecture

| architecture | P_elec before | P_elec after | change |
|---|---|---|---|
| Z1_EMBEDDED | 125.095 W | 141.778 W | **+16.683 W (+13.3 %)** |
| Z2_BACKSIDE | 126.190 W | 143.612 W | **+17.422 W (+13.8 %)** |
| Z4_POWER_DIE | 123.644 W | 134.739 W | **+11.095 W (+9.0 %)** |

The increase is intra-VR routing; the partial offset is the corrected transition model. The
ORDERING of the electrical loss is unchanged.
