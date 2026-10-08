# PHASE 0M-R3A SECTION 4 --- WHAT IS `ls_to_L`?

> **It is not a TSV, and the TSV process range does not govern it.**
> Phase 0M-R3's claim that the 15 -> 20 um repair is source-backed **does not hold**.

## The provenance chain

| step | finding | provenance |
|---|---|---|
| 1 logical net | **ls_to_L** | MODEL |
| 2 physical endpoints | **gan_ls -> inductor** | MODEL |
| 3 z span | **673 um** | DERIVED |
| 4 medium crossed | **substrate power layers** | SOURCE_BACKED |
| 5 is it the TSV field? | **NO** | SOURCE_BACKED |
| 6 fabrication technology | **INTRA-CONVERTER VERTICAL INTERCONNECT** | DERIVED |
| 7 sourced geometry rule for that class | **NONE** | OPEN |
| 8 rule Phase 0M-R3 applied | **tsv.radius_m {2.5, 15, 50} um** | INVALID |
| 9 current-density rule | **J_design = 1.0e8 A/m2** | DERIVED_FROM_SOURCE |
| 10 status of the 15 -> 20 um repair | **OPEN** | OPEN |

## The geometry, traced

`ls_to_L` connects the **low-side GaN switch node** on tier 1 to the **inductor
terminal** on tier 3 of `T1_EMBEDDED_4LAYER`, crossing the flying-capacitor tier in between.

| | |
|---|---|
| source tier mid-plane | 998.0 um |
| destination tier mid-plane | 1671.0 um |
| **vertical span** | **673 um** |
| current | 20.408 A |
| rail | SW (switch node) |

## Why it is not the TSV field

The framework states both structures explicitly and they are in different places:

| | TSV field | `ls_to_L` |
|---|---|---|
| where | beneath the cell, from the substrate underside | between embedded-component layers, inside the cell |
| span, ARCH_Z1 | 74 um (h_sub - t_cell) | 673 um |
| medium | through silicon | through substrate power-layer build-up |
| carries | the 48 V HV rail into the cell | the switch node to the inductor |

`scripts/phase0f/geometry.py` records the source picture directly: the components are
"embedded within the subsequent substrate power layers", and "the TSV field runs beneath
it from the substrate underside". One sentence describes each, and they are not the same
structure.

## What the design space actually contains

| entry | governs | applies to `ls_to_L`? |
|---|---|---|
| `tsv.radius_m` {2.5, 15, 50} um | through-silicon vias | **NO** --- wrong medium and wrong region |
| `rdl.width_m`, `rdl.space_m` | in-plane traces | no --- these are trace rules, not via rules |
| `bump.microbump.diameter_m` {5, 10, 40} um | microbumps | no --- a bump joins two surfaces, it is not a via through dielectric |
| **a stacked substrate via rule** | what this net needs | **ABSENT** |

## Consequence

Phase 0M-R3 reported the realizability repair as using "only existing/sourced
technologies", with 20 um justified as inside the TSV radius range. That justification is
**withdrawn**. The correct statement is:

> The repair sets the intra-converter vertical interconnect to r = 20 um at a 70 um pitch.
> Both values are **self-consistent with the framework's own current-density and spacing
> arithmetic**, and **neither is governed by a sourced process rule for this interconnect
> class, because no such rule exists in this repository.**

The repair is therefore **OPEN on process provenance**, not source-backed. It is not shown
to be wrong -- 20 um vias on a 70 um pitch through 673 um of build-up is not an
extraordinary structure -- but it is not demonstrated to be manufacturable either.

**This changes the realizability verdict.** Package clearances are no longer the sole
reason the repaired pair falls short of PROVEN_REALIZABLE; the via technology is now a
second, independent unsourced manufacturing assumption.
