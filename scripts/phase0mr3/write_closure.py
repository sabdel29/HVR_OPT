#!/usr/bin/env python3
"""Phase-0M-R3 --- closure document, open items, optimizer preconditions."""
from __future__ import annotations
import csv, sys
from pathlib import Path
import yaml

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3"


def rd(n, base=OUT):
    p = Path(base) / n
    return list(csv.DictReader(p.open())) if p.is_file() else []


def f(x, d=4):
    try:
        return f"{float(x):.{d}f}"
    except (TypeError, ValueError):
        return str(x)


PRE = [
    ("interconnect geometry and crowding validated", "PARTIAL",
     "Delta_R cross-validated against MOOSE at 0.25-0.73 %; TSV span architecture-aware "
     "and consistent across all three domains. The EM allowable is still OPEN."),
    ("routing scope physically correct", "YES",
     "UPGRADED in 0M-R3. Routing is now a HARD GATE in the realizability contract, every "
     "net is checked lateral and vertical, and both frozen candidates pass with 6.6 % "
     "margin."),
    ("cooling boundary tied to physical hardware", "PARTIAL",
     "the production point is inside a SOURCE_BACKED correlation domain and the solid side "
     "is MOOSE-validated at 3.78 %. The fluid side has no conjugate CFD validation, and "
     "2300 < Re < 3000 has no correlation at all."),
    ("architecture templates realizable", "PARTIAL",
     "UPGRADED from NO. One Z1 and one Z2 are CONDITIONAL_REALIZABLE at all 27 clearance "
     "corners. Neither is PROVEN_REALIZABLE: three package clearances are unsourced."),
    ("architecture geometry physically represented", "PARTIAL",
     "ARCH_Z4's power die is explicit geometry but its construction is unsourced, so its "
     "ranking stays conditional."),
    ("process margin on the critical interconnect", "NO",
     "NEW in 0M-R3. ARCH_Z2's TSV field sits at AR = 10.000, M_AR = 1.000, and fails a "
     "modest tolerance bound. A 34 um via fixes it but has not been adopted into the "
     "frozen pair."),
    ("dominant mechanical physics closed", "NO",
     "high-stress SAC305 constitutive response is CONDITIONAL; cohesive-zone parameters "
     "OPEN; 6 of 8 enumerated failure mechanisms uncomputed."),
    ("an admissible mechanical criterion exists", "NO",
     "nine candidates tested against six admissibility conditions; none passed."),
    ("a required life exists", "NO", "N_required is OPEN."),
    ("absolute fatigue prediction validated", "NO",
     "the strain and energy formulations disagree 4.1x on this joint."),
]


def main() -> int:
    new = {r["case"]: r for r in rd("final_Z1_Z2_comparison.csv")}
    mg = {r["case"]: r for r in rd("final_realizability_margins.csv")}
    stale = rd("stale_claims_before.csv")
    after = rd("stale_claims_after.csv")
    ratio = (float(new["Z1"]["response_driver_um"])
             / float(new["Z2"]["response_driver_um"]))
    # compare against the EXACT Phase-0M-R2 ratio, not its rounded display value
    old = {r["case"]: r for r in rd("architecture_replay_0mr2.csv",
                                    OUT / "_baseline_phase0mr2")}
    ratio_prev = (float(old["Z1"]["du_corner_um"]) / float(old["Z2"]["du_corner_um"]))
    d_pct = 100 * (ratio - ratio_prev) / ratio_prev

    with open(OUT / "optimizer_preconditions.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["precondition", "status", "evidence"])
        w.writeheader()
        for a, b, c in PRE:
            w.writerow({"precondition": a, "status": b, "evidence": c})

    n_no = sum(1 for _, s, _ in PRE if s == "NO")
    md = f"""# PHASE 0M-R3 --- REALIZABLE-TEMPLATE REPAIR, COOLING VALIDATION AND FINAL CURRENT-STATE CLOSURE

**Verdict: E --- Z1/Z2 FEASIBILITY REMAINS CONDITIONAL ON OPEN PACKAGE RULES.**

A realizable Z1 and a realizable Z2 exist, the repair used only sourced technology, and the
deciding ordering survived it essentially unchanged. Neither design can be called
PROVEN_REALIZABLE while three package clearances are unsourced, and ARCH_Z2's TSV field has
no process margin.

---

## The deciding question

**D_driver_realizable = {ratio:.4f}** ({f(new['Z1']['response_driver_um'],4)} um / {f(new['Z2']['response_driver_um'],4)} um)

| | Phase 0M-R2 | Phase 0M-R3 | change |
|---|---|---|---|
| driver Z1 | {f(old['Z1']['du_corner_um'],4)} um | {f(new['Z1']['response_driver_um'],4)} um | {100*(float(new['Z1']['response_driver_um'])-float(old['Z1']['du_corner_um']))/float(old['Z1']['du_corner_um']):+.3f} % |
| driver Z2 | {f(old['Z2']['du_corner_um'],4)} um | {f(new['Z2']['response_driver_um'],4)} um | {100*(float(new['Z2']['response_driver_um'])-float(old['Z2']['du_corner_um']))/float(old['Z2']['du_corner_um']):+.3f} % |
| **ratio** | **{ratio_prev:.4f}** | **{ratio:.4f}** | **{d_pct:+.4f} %** |
| buildable? | NO, 0 of 12 | **both CONDITIONAL_REALIZABLE** | |

Repairing both architectures for manufacturability moved the ordering by less than one part
in ten thousand.

### Is it resolved against uncertainty?

| source | effect on the ratio | basis |
|---|---|---|
| numerical | < 0.5 % | four graded mesh levels, die warpage converged to 0.50 % |
| the realizability repair itself | {d_pct:+.4f} % | measured, this phase |
| geometry --- TSV span | 0 % | one source, enforced across all three domains |
| geometry --- TSV diameter | < 0.02 % | Section 7: copper fraction is radius-independent |
| RDL interface tensor | -0.105 % | Phase 0M-R2, almost pure common mode |
| cooling model | 0 % at the production point | already inside its validated domain |
| constitutive | NOT QUANTIFIED | the creep card is Sn3.9Ag0.6Cu over 7.51-15.92 MPa and 99.8 % of the response is generated outside it |

The gap is **19.4 %**, which is 33 times the converged mesh error. It is resolved against
every uncertainty that has been quantified. It is NOT resolved against the constitutive
question, which is why the magnitude is not a validated lifetime.

## What the quantity is, and what it is not

    LOAD DRIVER        -> the corner displacement imposed by the global thermoelastic model
    RESPONSE METRIC    -> accumulated equivalent inelastic strain per stabilised cycle  <-- THIS
    DAMAGE MODEL       -> OPEN, no sourced damage law maps the response onto damage
    LIFE MODEL         -> OPEN, absolute N_f unvalidated, formulations disagree 4.1x
    FAILURE CRITERION  -> OPEN, no admissible allowable

The FE output is a **local fatigue-relevant inelastic response metric**. Three rungs above
it are open, so "Z2 lasts 1.19x longer" is not available from this result and is not
claimed.

## Temperature and the response do not track

ARCH_Z2 runs **{f(new['Z2']['T_max_C'],2)} C** against ARCH_Z1's **{f(new['Z1']['T_max_C'],2)} C** --- {float(new['Z2']['T_max_C'])-float(new['Z1']['T_max_C']):.2f} K hotter --- and
carries **{100*(float(new['Z1']['response_driver_um'])-float(new['Z2']['response_driver_um']))/float(new['Z1']['response_driver_um']):.1f} % less** response. Ranking by package T_max is not ranking by the
fatigue-relevant response, because geometry- and CTE-induced deformation and the local
constitutive response are distinct mechanisms.

## The realizable pair

| | Z1_EMBEDDED | Z2_BACKSIDE |
|---|---|---|
| verdict | {mg['Z1']['verdict']} | {mg['Z2']['verdict']} |
| clearance corners passing | {mg['Z1']['corners_passing']} | {mg['Z2']['corners_passing']} |
| area margin | {f(mg['Z1']['area_margin_pct'],1)} % | {f(mg['Z2']['area_margin_pct'],1)} % |
| height margin | {f(mg['Z1']['height_margin_pct'],1)} % | {f(mg['Z2']['height_margin_pct'],1)} % |
| routing margin | {f(mg['Z1']['routing_margin_pct'],1)} % | {f(mg['Z2']['routing_margin_pct'],1)} % |
| TSV AR / M_AR | {f(mg['Z1']['tsv_AR'],3)} / {f(mg['Z1']['tsv_AR_margin'],3)} | {f(mg['Z2']['tsv_AR'],3)} / **{f(mg['Z2']['tsv_AR_margin'],3)}** |
| TSV under a modest tolerance | {mg['Z1']['tsv_process_margin_under_modest_bound']} | **{mg['Z2']['tsv_process_margin_under_modest_bound']}** |
| P_electronics | {f(new['Z1']['P_total_electronics_w'],3)} W | {f(new['Z2']['P_total_electronics_w'],3)} W |
| P_facility | {f(new['Z1']['P_total_facility_w'],3)} W | {f(new['Z2']['P_total_facility_w'],3)} W |

## Report state

Phase 0M-R2 certified zero stale current-facing claims. This phase found **{len(stale)}** and
registered **DEFECT #56**; after repair the same checker reports **{len(after)}**.

## Optimizer gate

**FORBIDDEN.** One precondition moved to YES and two upgraded to PARTIAL, but one was ADDED
at NO.

| precondition | status | evidence |
|---|---|---|
""" + "".join(f"| {a} | **{b}** | {c} |\n" for a, b, c in PRE) + f"""
**{n_no} remain NO, and any one is sufficient to keep the gate shut.**

## Verdicts considered and rejected

| candidate | why rejected |
|---|---|
| **A** pair found, ordering survives | both halves true, but the brief permits A only if both MEET the frozen contract, and the contract's own verdict is CONDITIONAL_REALIZABLE, not PROVEN |
| **B** ordering collapses | measurement: the ratio moved +0.009 % |
| **C** ordering reverses | measurement: Z2 = {f(new['Z2']['response_driver_um'],4)} um against Z1 = {f(new['Z1']['response_driver_um'],4)} um |
| **D** no realizable pair exists | a pair does exist, using only the existing compiler, the existing library and a via radius inside the sourced range |
| **F** cooling insufficiently validated | the fluid side is indeed unvalidated, but the production point is inside a sourced domain and the unvalidated band was removed from the design space rather than relied upon |
| **G** multiple blockers, selection premature | understates what closed: area, height, routing, current density, TSV count and AR all pass for both at every corner. What remains is nameable, which is what E says |
"""
    (OUT / "PHASE0MR3_REALIZABLE_TEMPLATE_AND_COOLING_CLOSURE.md").write_text(md)

    (OUT / "open_items.md").write_text(f"""# PHASE 0M-R3 --- OPEN ITEMS

Ranked. Every item is OPEN in the strict sense: not determined, never defaulted.

## Blocking

| # | item | why open | what it blocks | what would close it |
|---|---|---|---|---|
| 1 | **three package clearances** | no framework source, no accessible foundry rule, nothing usable in reachable literature | PROVEN_REALIZABLE for both architectures; they are the sole reason the pair is CONDITIONAL | a process design rule from a named vendor |
| 2 | **TSV process margin on ARCH_Z2** | AR = 10.000 gives M_AR = 1.000 and fails a modest tolerance bound | calling the frozen Z2 manufacturable | adopt the 34 um via (sourced, +22.8 % vias, <= 0.02 % E/T/M change) or source a tolerance that the 30 um via survives |
| 3 | **transitional cooling correlation** | nothing sourceable for 2300 < Re < 3000 | any flow above the cap; currently avoided rather than solved | one primary correlation with its coefficients and range |
| 4 | **conjugate CFD of the cooler** | see CONJUGATE_CFD_VALIDATION.md | calling the cooler fully validated | a converged canonical benchmark |
| 5 | **high-stress SAC305 constitutive data** | no primary data above ~16 MPa at 45-150 C | every absolute reliability number and the MAGNITUDE of the relative one | coupon characterisation at 15-100+ MPa |
| 6 | **required life N_required** | not published for this system | G2 | a statement from the system owner |
| 7 | **absolute N_f validation** | strain and energy formulations disagree 4.1x | G2 | a validated life model |
| 8 | **admissible mechanical allowable** | nine candidates, none admissible | G2 and any constraint-based optimizer | a published allowable tied to a failure mode |
| 9 | **ARCH_Z4 power-die construction** | unsourced; stacked and planar give different rankings | any Z4 ordering claim | one process description |
| 10 | **electromigration allowable** | no primary study with its conditions | a feasibility verdict on any via field | one primary EM study |

Items 6, 7 and 8 are the **three independent G2 blockers**. Closing any one leaves the
other two, and G2 remains NOT TESTED until all three close.

## Not open, and not to be relitigated

* **Z2 carries less local fatigue-relevant response than Z1** --- D_driver = {ratio:.4f},
  unchanged by the realizability repair.
* **A realizable Z1 and Z2 exist** in the current library, conditional only on item 1.
* **The production cooling point is inside its correlation's validated domain.**
* **The TSV allocation law** --- enlarging the via changes the count and nothing else.
* **Pumping power is FACILITY scope** --- not in the loss objective, not in the mesh.
""")
    print(f"  D_driver_realizable = {ratio:.4f}")
    print(f"  wrote closure, open_items, optimizer_preconditions ({n_no} NO)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
