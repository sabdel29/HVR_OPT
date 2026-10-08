# PHASE 0M-R3 SECTION 3 --- REALIZABILITY FAILURE DECOMPOSITION

Every condition as a distance-to-feasibility ratio (required / available). Above 1.0 is a
failure; how far above says whether the repair is modest or structural. Evaluated at the
MOST FAVOURABLE corner of the bounded clearance envelope, so nothing here is pessimistic.

| template | architecture | area | height | routing | J | TSV count | TSV AR |
|---|---|---|---|---|---|---|---|
| T1_EMBEDDED_4LAYER | Z1_EMBEDDED | 0.564 | 0.989 | 1.236 | 0.999 | 0.009 | 0.247 |
| T1_EMBEDDED_4LAYER | Z2_BACKSIDE | 0.550 | 1.755 | 1.236 | 1.000 | 0.397 | 1.000 |
| T1_EMBEDDED_4LAYER | Z4_POWER_DIE | 0.550 | 1.609 | 1.236 | 0.999 | 0.009 | 1.000 |
| T4_SPLIT_SC_BUCK | Z1_EMBEDDED | 1.038 | 1.049 | 0.957 | 0.999 | 0.009 | 0.247 |
| T4_SPLIT_SC_BUCK | Z2_BACKSIDE | 1.019 | 1.192 | 0.957 | 1.000 | 0.397 | 1.000 |
| T4_SPLIT_SC_BUCK | Z4_POWER_DIE | 1.019 | 1.093 | 0.957 | 0.999 | 0.009 | 1.000 |
| T2_BACKSIDE_CHIPLET | Z1_EMBEDDED | 1.099 | 1.052 | 1.236 | 0.999 | 0.009 | 0.247 |
| T2_BACKSIDE_CHIPLET | Z2_BACKSIDE | 1.079 | 1.195 | 1.236 | 1.000 | 0.397 | 1.000 |
| T2_BACKSIDE_CHIPLET | Z4_POWER_DIE | 1.079 | 1.096 | 1.236 | 0.999 | 0.009 | 1.000 |
| T0_SINGLE_LEVEL | Z1_EMBEDDED | 1.987 | 0.556 | 0.957 | 0.999 | 0.009 | 0.247 |
| T0_SINGLE_LEVEL | Z2_BACKSIDE | 1.961 | 0.632 | 0.957 | 1.000 | 0.397 | 1.000 |
| T0_SINGLE_LEVEL | Z4_POWER_DIE | 1.961 | 0.579 | 0.957 | 0.999 | 0.009 | 1.000 |

## Ranked by distance to feasibility

| constraint | worst ratio | fails | character |
|---|---|---|---|
| area | 1.9874 | 9/12 | HARD --- T0_SINGLE_LEVEL is 2x over and cannot be repacked |
| height | 1.7555 | 8/12 | HARD for T1 on the backside; modest for T4 and T2 |
| **routing** | **1.2360** | **6/12** | **REPAIRABLE-SCALE --- and this is the one that was repaired** |
| current density | 1.0000 | 0/12 | at the limit, never over |
| TSV count | 0.3966 | 0/12 | comfortable |
| TSV AR | 1.0000 | 0/12 | passes the hard rule with ZERO margin (Section 7) |

## Why the original Z1 and Z2 failed

**ARCH_Z1 with T1_EMBEDDED_4LAYER** failed on ONE condition only: routing, at 1.2360.
Area 0.564 and height 0.989 both passed. It was one repair away from buildable.

**ARCH_Z2 with T1_EMBEDDED_4LAYER** failed on TWO: height at 1.7555 and the same routing
at 1.2360.

The binding routing constraint in both is the same net: **`ls_to_L`**, the switch-node to
inductor connection, a VERTICAL via stack carrying 20.408 A and needing 1.236x the vias
available in its pad. It is not a trace-width problem and no number of metal layers fixes
it, because layers do not add vias.

A correction worth recording: an earlier pass of this decomposition filtered the route
list to `geom == "lateral"` and reported routing as 0.957, i.e. feasible. That silently
dropped the only net that fails. The published matrix includes every net.
