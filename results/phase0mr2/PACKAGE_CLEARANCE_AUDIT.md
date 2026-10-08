# PHASE 0M-R2 SECTION 4 --- PACKAGE CLEARANCE AUDIT

## The three clearances

| clearance | definition | where | sourcing | bound swept | anchor |
|---|---|---|---|---|---|
| `die_to_component_gap_um` | Minimum vertical gap between the compute-die underside and the top of the tallest component in the tier below it. | between the top of the converter tier and the bottom of the compute die | **OPEN** | [10.0, 25.0, 50.0] um | Lower end 10 um is the sourced `interface_layer` thickness and the sourced 10 um hybrid-pad height -- the framework already builds a 10 um gap there,  |
| `cavity_sidewall_um` | Lateral allowance between an embedded component's edge and the cavity wall milled or built into the substrate. | in plane, around every embedded component in ARCH_Z1's substrate cavity | **OPEN** | [15.0, 30.0, 60.0] um | Centred on the sourced minimum conductor spacing s_min = 30 um used by interconnect.TSVGeometry, with a factor of two either side. A cavity wall is a  |
| `cooler_standoff_um` | Vertical standoff between the cooled surface and the nearest active component. | between the top of the die/TIM stack and the cooler base | **OPEN** | [0.0, 50.0, 100.0] um | Lower end 0 um is the present model, which bonds the cooler directly to the TIM. Upper end 100 um is the sourced cooler base thickness t_base_um = 100 |

## What was searched

In the order the brief specifies:

1. **the exact package/process source used by this framework** --- NOT AVAILABLE. The
   June-2026 DVPD source describes embedded components and names stacking as a
   fabrication challenge, but publishes no cavity or clearance design rule.
2. **foundry / OSAT / substrate-vendor design rules** --- NOT ACCESSIBLE. These are
   released under NDA; no public copy was reachable from this host.
3. **directly comparable peer-reviewed implementations** --- SEARCHED, NOTHING USABLE.
   Crossref and OpenAlex were reachable and returned no paper giving a numeric
   embedded-component cavity clearance. WebSearch is blocked in this environment.
4. **explicit bounded engineering envelope** --- ADOPTED. Each bound is anchored to a
   length the framework already sources, and the anchor is named. These are ANALOGIES,
   NOT SOURCES, and they are labelled BOUNDED.
5. **OPEN** --- retained as the sourcing status of all three.

No single "reasonable" value was adopted. Every template was evaluated at all 27 corners
of the three-way bound.

## The result: 0 of 12 combinations are realizable, at ANY corner

| template | architecture | FULLY_REALIZABLE | dimensions that fail at EVERY corner |
|---|---|---|---|
| T0_SINGLE_LEVEL | Z1_EMBEDDED | **NEVER** | AREA, PACKAGE_CLEARANCE |
| T0_SINGLE_LEVEL | Z2_BACKSIDE | **NEVER** | AREA, PACKAGE_CLEARANCE |
| T0_SINGLE_LEVEL | Z4_POWER_DIE | **NEVER** | AREA, PACKAGE_CLEARANCE |
| T1_EMBEDDED_4LAYER | Z1_EMBEDDED | **NEVER** | THERMAL, ROUTING, CURRENT_DENSITY |
| T1_EMBEDDED_4LAYER | Z2_BACKSIDE | **NEVER** | HEIGHT, ROUTING, CURRENT_DENSITY, PACKAGE_CLEARANCE |
| T1_EMBEDDED_4LAYER | Z4_POWER_DIE | **NEVER** | HEIGHT, THERMAL, ROUTING, CURRENT_DENSITY, PACKAGE_CLEARANCE |
| T2_BACKSIDE_CHIPLET | Z1_EMBEDDED | **NEVER** | AREA, HEIGHT, ROUTING, CURRENT_DENSITY, PACKAGE_CLEARANCE |
| T2_BACKSIDE_CHIPLET | Z2_BACKSIDE | **NEVER** | AREA, HEIGHT, ROUTING, CURRENT_DENSITY, PACKAGE_CLEARANCE |
| T2_BACKSIDE_CHIPLET | Z4_POWER_DIE | **NEVER** | AREA, HEIGHT, ROUTING, CURRENT_DENSITY, PACKAGE_CLEARANCE |
| T4_SPLIT_SC_BUCK | Z1_EMBEDDED | **NEVER** | AREA, HEIGHT, PACKAGE_CLEARANCE |
| T4_SPLIT_SC_BUCK | Z2_BACKSIDE | **NEVER** | AREA, HEIGHT, PACKAGE_CLEARANCE |
| T4_SPLIT_SC_BUCK | Z4_POWER_DIE | **NEVER** | AREA, HEIGHT, PACKAGE_CLEARANCE |

## How often each dimension blocks

| dimension | blocks at every corner |
|---|---|
| AREA_FEASIBLE | 9 of 12 |
| HEIGHT_FEASIBLE | 8 of 12 |
| THERMAL_FEASIBLE | 2 of 12 |
| ROUTING_FEASIBLE | 6 of 12 |
| CURRENT_DENSITY_FEASIBLE | 6 of 12 |
| PACKAGE_CLEARANCE_SATISFIED | 11 of 12 |

## The Phase-0M-R claim, narrowed

Phase 0M-R said all twelve templates fail FULLY_REALIZABLE **because** three package
clearances are OPEN. That is not right. Even if all three clearances were sourced at
their most favourable values, area would still block 9 of 12, height 8 of 12, and routing
and current density 6 of 12 each. **Closing the clearances would make nothing realizable.**
They are a necessary condition, not the binding one.

## T4, specifically

Phase 0M-R reported T4 as about 2 % outside its area bound, with no cavity sidewall
allowance charged at all. Charging the SMALLEST sidewall in the bound, T4 is **3.83 %**
over. T4 does not get closer to feasible once clearances are represented; it gets further
away. And because the 5.61 mm2 per-level area is an OUTPUT of the converter area model,
the shortfall cannot be closed by repacking: it would require changing the component
topology, which the converter model does not currently support.

## Does any architecture in the Z1/Z2 comparison fail on clearance?

Both do, at most corners. ARCH_Z1 with T1 has only 24 um of height slack, so its clearance
is satisfiable at just 3 of 27 corners and only when the die-to-component gap plus the
cooler standoff together stay at or below 10 um. ARCH_Z2 with T1 fails height at every
corner. **Neither architecture in the deciding comparison is presently buildable**, and
that is stated plainly rather than folded into the mechanical result.
