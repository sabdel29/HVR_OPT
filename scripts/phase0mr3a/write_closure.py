#!/usr/bin/env python3
"""Phase-0M-R3A --- closure document, final open items, final state audit."""
from __future__ import annotations
import csv, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3a"


def rd(n, base=OUT):
    p = Path(base) / n
    return list(csv.DictReader(p.open())) if p.is_file() else []


def f(x, d=4):
    try:
        return f"{float(x):.{d}f}"
    except (TypeError, ValueError):
        return str(x)


def main() -> int:
    z = {r["d_um"]: r for r in rd("z2_tsv_diameter_sweep.csv")}
    v = {r["r_um"]: r for r in rd("ls_to_L_via_check.csv")}
    prov = rd("interconnect_technology_provenance.csv")
    cur = {r["case"]: r for r in rd("final_Z1_Z2_comparison.csv",
                                    OUT / "_baseline_phase0mr3")}
    ratio = (float(cur["Z1"]["response_driver_um"])
             / float(cur["Z2"]["response_driver_um"]))

    md = f"""# PHASE 0M-R3A --- FINAL STATE, VIA-TECHNOLOGY AND TSV-MARGIN CLOSURE

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
""" + "".join(
        f"| {f(r['r_um'],1)} um | {f(r['pitch_um'],1)} um | {r['n_required']} | "
        f"{r['n_available']} | {f(r['ratio'],4)} | {f(r['production_ratio'],4)} | "
        f"{'EXACT' if r['reproduces']=='True' else 'DIFFERS'} |\n"
        for r in rd("ls_to_L_via_check.csv")) + f"""
1.2360 at r = 15 um and 0.9344 at r = 20 um reproduce to machine precision. The numbers
were right; only their provenance was not.

## 3. The 30 -> 34 um claim had the sign backwards

| quantity | 30 um | 34 um | change |
|---|---|---|---|
| n_required | {z['30.0']['n_required']} | {z['34.0']['n_required']} | **{100*(int(z['34.0']['n_required'])-int(z['30.0']['n_required']))/int(z['30.0']['n_required']):+.1f} %** |
| n_allocated | {z['30.0']['n_allocated']} | {z['34.0']['n_allocated']} | {100*(int(z['34.0']['n_allocated'])-int(z['30.0']['n_allocated']))/int(z['30.0']['n_allocated']):+.1f} % |
| n_available | {z['30.0']['n_available']} | {z['34.0']['n_available']} | {100*(int(z['34.0']['n_available'])-int(z['30.0']['n_available']))/int(z['30.0']['n_available']):+.1f} % |
| phi_Cu | {f(z['30.0']['phi_cu'],6)} | {f(z['34.0']['phi_cu'],6)} | {100*(float(z['34.0']['phi_cu'])-float(z['30.0']['phi_cu']))/float(z['30.0']['phi_cu']):+.3f} % |
| R_field | {f(z['30.0']['R_field_mohm'],6)} mOhm | {f(z['34.0']['R_field_mohm'],6)} mOhm | {100*(float(z['34.0']['R_field_mohm'])-float(z['30.0']['R_field_mohm']))/float(z['30.0']['R_field_mohm']):+.3f} % |
| k_z | {f(z['30.0']['k_z'],3)} | {f(z['34.0']['k_z'],3)} | {100*(float(z['34.0']['k_z'])-float(z['30.0']['k_z']))/float(z['30.0']['k_z']):+.3f} % |
| E_xy | {f(z['30.0']['E_xy_MPa'],0)} MPa | {f(z['34.0']['E_xy_MPa'],0)} MPa | {100*(float(z['34.0']['E_xy_MPa'])-float(z['30.0']['E_xy_MPa']))/float(z['30.0']['E_xy_MPa']):+.3f} % |

`n_required` scales as `1 / (d/2 - t_liner)^2`, so `(14.5/16.5)^2 = 0.7723`: **22.8 %
FEWER**, not more, and a reduction rather than a cost. Verified against an independent hand
calculation at every diameter.

**A second error in the same sweep.** Phase 0M-R3 reported 34 um as the smallest diameter
with positive margin, but its grid was 30/34/40/50/60 and never evaluated 32 um, which
passes the same modest bound:

| d | AR | M_AR | modest bound |
|---|---|---|---|
""" + "".join(
        f"| {f(z[k]['d_um'],0)} um | {f(z[k]['AR'],3)} | {f(z[k]['M_AR'],3)} | "
        f"{'PASSES' if z[k]['passes_modest_bound']=='True' else '**FAILS**'} |\n"
        for k in ("30.0", "32.0", "34.0", "36.0")) + f"""
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
| P_electronics | {f(cur['Z1']['P_total_electronics_w'],3)} W | {f(cur['Z2']['P_total_electronics_w'],3)} W |
| T_max | {f(cur['Z1']['T_max_C'],2)} C | **{f(cur['Z2']['T_max_C'],2)} C** |
| local fatigue-relevant inelastic response | {f(cur['Z1']['response_driver_um'],4)} um | **{f(cur['Z2']['response_driver_um'],4)} um** |

**D_driver = {ratio:.4f}**, unchanged. ARCH_Z2 is
{float(cur['Z2']['T_max_C'])-float(cur['Z1']['T_max_C']):.2f} K hotter and carries
{100*(float(cur['Z1']['response_driver_um'])-float(cur['Z2']['response_driver_um']))/float(cur['Z1']['response_driver_um']):.1f} % less response.

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
"""
    (OUT / "PHASE0MR3A_FINAL_CLOSURE.md").write_text(md)

    (OUT / "final_open_items.md").write_text(f"""# PHASE 0M-R3A --- FINAL OPEN ITEMS

Ranked. Two items now stand between the repaired pair and PROVEN_REALIZABLE, where Phase
0M-R3 recorded one.

| # | item | why open | what it blocks | what would close it |
|---|---|---|---|---|
| 1 | **process rule for the intra-converter vertical interconnect** | DEFECT #58: the design space has no geometry rule for a stacked via through substrate power layers, and the TSV range was borrowed | PROVEN_REALIZABLE for BOTH architectures, because the routing repair depends on it | one substrate-vendor build-up via design rule: diameter, pitch, aspect-ratio and stacking limits |
| 2 | **three package clearances** | no framework source, no accessible foundry rule | PROVEN_REALIZABLE for both | a process design rule from a named vendor |
| 3 | **ARCH_Z2 TSV process margin** | 30 um gives M_AR = 1.000 and fails the modest bound | calling the frozen Z2 manufacturable | adopt 32 um, the smallest evaluated diameter with positive margin, at 12.5 % FEWER vias |
| 4 | **high-stress SAC305 constitutive data** | no primary data above ~16 MPa at 45-150 C | every absolute reliability number and the MAGNITUDE of the relative one | coupon characterisation at 15-100+ MPa |
| 5 | **conjugate CFD of the cooler** | timed out at its declared budget in Phase 0M-R3 | calling the cooler fully validated | a converged canonical benchmark |
| 6 | **required life N_required** | not published for this system | G2 | a statement from the system owner |
| 7 | **absolute N_f validation** | strain and energy formulations disagree 4.1x | G2 | a validated life model |
| 8 | **admissible mechanical allowable** | nine candidates, none admissible | G2 and any constraint-based optimizer | a published allowable tied to a failure mode |
| 9 | **ARCH_Z4 power-die construction** | unsourced; stacked and planar give different rankings | any Z4 ordering claim | one process description |

Items 6, 7 and 8 are the **three independent G2 blockers**. G2 remains NOT TESTED until all
three close.

## COMPLETE --- must not reappear as future work

* adopting the physical cooling model into the ETM loop --- **done in Phase 0M-R**
* putting the RDL into the production thermal model --- **done in Phase 0M-R2**
* retiring the global 1.326 transition constant --- **done in Phase 0M-R**
* making the TSV span architecture-aware --- **done in Phase 0M-R2**

## Not open, and not to be relitigated

* **Z2 carries less local fatigue-relevant inelastic response than Z1** --- D_driver = {ratio:.4f}.
* **The routing arithmetic** --- reproduced exactly by an independent implementation.
* **The TSV allocation law** --- enlarging the via changes the COUNT and nothing else.
* **The production cooling point** --- Re = 1264.8, inside its validated domain; the design
  space is capped at Re <= 2300 and conjugate CFD is NOT COMPLETED.
""")
    print(f"  D_driver unchanged at {ratio:.4f}")
    print(f"  wrote PHASE0MR3A_FINAL_CLOSURE.md and final_open_items.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
