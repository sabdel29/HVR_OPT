# PHASE 0M-R3A --- FINAL STATE, VIA-TECHNOLOGY AND TSV-MARGIN CLOSURE

**Verdict: B --- Z1/Z2 ORDERING SURVIVES, BUT THE INTRA-VR VIA TECHNOLOGY REMAINS
UNSOURCED.**

Phase 0M-R3's verdict E said package clearances were the sole reason the repaired pair
fell short of PROVEN_REALIZABLE. That is no longer true. The repair that made both
architectures routable rests on a process range that does not govern the interconnect it
was applied to, so there are now **two independent unsourced manufacturing assumptions**.

---

## What this gate found

| # | issue | verdict |
|---|---|---|
| 1 | the current-state table was still Phase 0M-R2 | **CONFIRMED** --- DEFECT #57 |
| 2 | the next-work block listed two already-completed actions | **CONFIRMED** --- same defect |
| 3 | current-facing text still called the FE response "damage" | **CONFIRMED** --- corrected |
| 4 | the 15 -> 20 um repair borrowed the TSV process range | **CONFIRMED** --- DEFECT #58 |
| 5 | "34 um costs 22.8 % MORE vias" | **CONFIRMED WRONG SIGN** --- DEFECT #59 |

## 1. `ls_to_L` is not a TSV

| | |
|---|---|
| connects | low-side GaN switch node (tier 1) to inductor terminal (tier 3) |
| span | **673 um**, crossing the flying-capacitor tier |
| current | 20.408 A |
| medium | substrate power layers, between embedded components |
| technology | **intra-converter vertical interconnect** (stacked package-substrate via) |
| sourced geometry rule | **NONE** |

The framework's own source picture separates the two structures in one sentence each: the
components are "embedded within the subsequent substrate power layers", and "the TSV field
runs beneath it from the substrate underside". For ARCH_Z1 that TSV field spans 74 um.
This net spans 673 um in the opposite region of the stack.

The design space holds `tsv.*` (through-silicon), `rdl.*` (trace width and space, no via)
and `bump.*` (bumps, not vias through dielectric). **No entry governs a stacked via through
substrate power layers.**

Phase 0M-R3's wording -- a repair using "only existing/sourced technologies" -- is
**withdrawn**. The correct statement:

> r = 20 um at a 70 um pitch is a **design point in an unsourced process window**,
> arithmetically self-consistent with the framework's current-density and spacing rules,
> and **not demonstrated to be manufacturable**.

## 2. The routing arithmetic is correct

Re-derived from the physics without calling the production function:

| r | pitch | n_required | n_available | ratio | production | agreement |
|---|---|---|---|---|---|---|
| 15.0 um | 60.0 um | 309 | 250 | 1.2360 | 1.2360 | EXACT |
| 17.5 um | 65.0 um | 225 | 213 | 1.0563 | 1.0563 | EXACT |
| 20.0 um | 70.0 um | 171 | 183 | 0.9344 | 0.9344 | EXACT |
| 22.5 um | 75.0 um | 135 | 160 | 0.8438 | 0.8438 | EXACT |
| 25.0 um | 80.0 um | 109 | 140 | 0.7786 | 0.7786 | EXACT |

1.2360 at r = 15 um and 0.9344 at r = 20 um reproduce to machine precision. The numbers
were right; only their provenance was not.

## 3. The 30 -> 34 um claim had the sign backwards

| quantity | 30 um | 34 um | change |
|---|---|---|---|
| n_required | 15140 | 11692 | **-22.8 %** |
| n_allocated | 15140 | 11692 | -22.8 % |
| n_available | 69440 | 61031 | -12.1 % |
| phi_Cu | 0.020002 | 0.020002 | -0.001 % |
| R_field | 0.000640 mOhm | 0.000640 mOhm | +0.001 % |
| k_z | 134.920 | 134.942 | +0.016 % |
| E_xy | 167182 MPa | 167222 MPa | +0.024 % |

`n_required` scales as `1 / (d/2 - t_liner)^2`, so `(14.5/16.5)^2 = 0.7723`: **22.8 %
FEWER**, not more, and a reduction rather than a cost. Verified against an independent hand
calculation at every diameter.

**A second error in the same sweep.** Phase 0M-R3 reported 34 um as the smallest diameter
with positive margin, but its grid was 30/34/40/50/60 and never evaluated 32 um, which
passes the same modest bound:

| d | AR | M_AR | modest bound |
|---|---|---|---|
| 30 um | 10.000 | 1.000 | **FAILS** |
| 32 um | 9.375 | 1.067 | PASSES |
| 34 um | 8.824 | 1.133 | PASSES |
| 36 um | 8.333 | 1.200 | PASSES |

**32 um is the smallest evaluated diameter with positive margin**, at 12.5 % fewer vias.

## 4. "34 um sourced" is not what the evidence supports

No primary source in this repository specifies a 34 um TSV. What is source-backed is the
RANGE. The licensed wording is therefore:

> **a 32 um design point selected within the source-backed allowable diameter range**

and not "the sourced 34 um via". Applied everywhere.

## 5. No replay was run

The 30 -> 34 um change moves `phi_Cu`, `R_field`, `k_z`, `E_xy` and `CTE_eff` by under
0.1 %, as the table above shows and as the Phase-0M allocation law predicts: under
minimum-capability provisioning the copper fraction is `I / (J_design * A_field)`, in which
the radius cancels identically. Re-running the ETM pipeline would consume two solves to
reproduce the frozen result to four decimal places. The frozen Phase-0M-R3 pair therefore
stands unchanged:

| | Z1 | Z2 |
|---|---|---|
| P_electronics | 138.796 W | 141.189 W |
| T_max | 118.68 C | **126.91 C** |
| local fatigue-relevant inelastic response | 4.6401 um | **3.8851 um** |

**D_driver = 1.1943**, unchanged. ARCH_Z2 is
8.23 K hotter and carries
16.3 % less response.

## 6. Why the verdict changed from E to B

Phase 0M-R3 chose E because the three package clearances were the only thing standing
between CONDITIONAL and PROVEN. DEFECT #58 adds a second, independent unsourced
assumption -- the via technology the routing repair depends on -- so E's premise no longer
holds. B states what is true: the ordering survives, and the via technology does not have
a source.

## Verdicts considered and rejected

| candidate | why rejected |
|---|---|
| **A** final report state closed, ordering survives | rejected: A is not available while any current-facing stale block remains, and three were found. It also ignores DEFECT #58 |
| **C** margin repair valid, ordering unchanged | true of the TSV, but it answers the smaller question and omits the via-technology finding |
| **D** the via repair used the wrong process technology | TRUE and the most important single finding, but stated alone it implies the architecture result fell, which it did not |
| **E** conditional on open package rules (Phase 0M-R3's verdict) | **withdrawn**: clearances are no longer the sole blocker |
| **F** realizability status must be reopened | close, and B says the same thing more precisely by naming what reopened it and what survived |
