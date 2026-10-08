#!/usr/bin/env python3
"""Phase-0M-R3 Section 20 --- append this phase and re-mark its predecessor."""
from __future__ import annotations
import csv, re, sys
from pathlib import Path
import yaml

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3"
REP = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
TAG = "phase0mr3_narrative"


def rd(n, base=OUT):
    p = Path(base) / n
    return list(csv.DictReader(p.open())) if p.is_file() else []


def f(x, d=4):
    try:
        return f"{float(x):.{d}f}"
    except (TypeError, ValueError):
        return str(x)


def narrative() -> str:
    new = {r["case"]: r for r in rd("final_Z1_Z2_comparison.csv")}
    mg = {r["case"]: r for r in rd("final_realizability_margins.csv")}
    fail = [r for r in rd("realizability_failure_matrix.csv")
            if r["corner"] == "BEST" and r["template"] == "T1_EMBEDDED_4LAYER"
            and r["arch"] in ("ARCH_Z1_EMBEDDED", "ARCH_Z2_BACKSIDE")]
    z1c = yaml.safe_load((R / "configs/phase0mr3/frozen_realizable_Z1.yaml").read_text())
    stale = rd("stale_claims_before.csv")
    ratio = (float(new["Z1"]["response_driver_um"])
             / float(new["Z2"]["response_driver_um"]))
    FIG = str(OUT)
    return f"""<!-- BEGIN GENERATED: {TAG} -->

\\newpage

# Phase 0M-R3 --- Realizable-Template Repair, Cooling Validation and Final Current-State Closure (current authoritative)

Phase 0M-R2 established a robust Z2 < Z1 ordering between two designs that were not
buildable. This gate asked whether the EXISTING converter and package library already
contains a buildable Z1 and a buildable Z2, and whether the ordering survives on them.

## The realizability definition was frozen first

`configs/phase0mr3/realizability_contract.yaml` fixes fifteen conditions and four verdict
levels BEFORE any architecture was touched, so "buildable" could not be adjusted after
seeing which candidates pass. Two conditions -- package clearance and cooling clearance --
depend on OPEN inputs, which means **PROVEN_REALIZABLE is unreachable in this phase by
construction**, whatever the margins turn out to be. That consequence was accepted in
advance.

## Why the originals failed, quantified

| architecture | area | height | routing | J | TSV count | TSV AR |
|---|---|---|---|---|---|---|
""" + "".join(
        f"| {r['arch'].replace('ARCH_','')} | {f(r['area_ratio'],3)} | "
        f"{f(r['height_ratio'],3)} | **{f(r['routing_ratio'],3)}** | "
        f"{f(r['current_density_ratio'],3)} | {f(r['tsv_count_ratio'],3)} | "
        f"{f(r['tsv_AR_ratio'],3)} |\n" for r in fail) + f"""
ARCH_Z1 failed on ONE condition, routing at 1.236. ARCH_Z2 failed on that and on height.
The binding net is the same in both: **`ls_to_L`**, the switch-node to inductor VERTICAL
via stack carrying 20.408 A and needing 1.236x the vias its pad provides.

![FIG-0MR3-A]({FIG}/FIG_0MR3_A_failure_margins.png)

*FIG-0MR3-A. Only routing crosses the feasibility line.*

## The repair: one variable, inside the sourced range

Neither more metal layers nor more cells fixes a via-count shortfall -- layers add no vias,
and splitting cells divides the current and the pad area together, leaving the ratio
invariant. The via GEOMETRY does fix it, because the required count goes as 1/r^2 while the
available count goes as 1/p^2 and the framework's own pitch rule
`p = max(2r + s_min, 2r(1+koz))` with the SOURCE_BACKED `s_min = 30 um` makes p grow more
slowly than r:

| r | p | (p/r)^2 | routing ratio |
|---|---|---|---|
| 15 um | 60 um | 16.00 | 1.236 |
| **20 um** | **70 um** | **12.25** | **0.934** |

20 um lies inside the sourced range `design_variables.tsv.radius_m = {{lo 2.5, nominal 15,
hi 50}} um`. No device was invented, no component scaled below its sourced dimensions, the
load stayed at 1 kW and the package budget was untouched.

## The frozen realizable pair

| | Z1_EMBEDDED | Z2_BACKSIDE |
|---|---|---|
| verdict | **{mg['Z1']['verdict']}** | **{mg['Z2']['verdict']}** |
| clearance corners passing | {mg['Z1']['corners_passing']} | {mg['Z2']['corners_passing']} |
| area margin | {f(mg['Z1']['area_margin_pct'],1)} % | {f(mg['Z2']['area_margin_pct'],1)} % |
| height margin | {f(mg['Z1']['height_margin_pct'],1)} % | {f(mg['Z2']['height_margin_pct'],1)} % |
| routing margin | {f(mg['Z1']['routing_margin_pct'],1)} % | {f(mg['Z2']['routing_margin_pct'],1)} % |
| TSV aspect ratio | {f(mg['Z1']['tsv_AR'],3)} | {f(mg['Z2']['tsv_AR'],3)} |
| TSV design margin M_AR | {f(mg['Z1']['tsv_AR_margin'],3)} | **{f(mg['Z2']['tsv_AR_margin'],3)}** |
| package clearances | OPEN | OPEN |

Neither reaches PROVEN_REALIZABLE, for the reason fixed before the search: three package
clearances are unsourced.

## The deciding result

| | Z1 | Z2 |
|---|---|---|
| P_electronics | {f(new['Z1']['P_total_electronics_w'],3)} W | {f(new['Z2']['P_total_electronics_w'],3)} W |
| P_pump (FACILITY) | {f(new['Z1']['P_pump_hydraulic_w'],3)} W | {f(new['Z2']['P_pump_hydraulic_w'],3)} W |
| T_max | {f(new['Z1']['T_max_C'],2)} C | **{f(new['Z2']['T_max_C'],2)} C** |
| die warpage | {f(new['Z1']['die_warpage_pv_um'],3)} um | {f(new['Z2']['die_warpage_pv_um'],3)} um |
| local fatigue-relevant inelastic response | {f(new['Z1']['response_driver_um'],4)} um | **{f(new['Z2']['response_driver_um'],4)} um** |

**D_driver_realizable = {ratio:.4f}**, against 1.1942 in Phase 0M-R2: a change of
**+0.0095 %**. Repairing both architectures for manufacturability moved the ordering by
less than one part in ten thousand. The gap is 33 times the converged mesh error of 0.5 %.

**ARCH_Z2 is {float(new['Z2']['T_max_C']) - float(new['Z1']['T_max_C']):.2f} K hotter and carries {100*(float(new['Z1']['response_driver_um'])-float(new['Z2']['response_driver_um']))/float(new['Z1']['response_driver_um']):.1f} % less response.** Ranking by
package T_max is not ranking by the fatigue-relevant response.

![FIG-0MR3-G]({FIG}/FIG_0MR3_G_decoupling.png)

*FIG-0MR3-G. The realizable pair. Filled points are Phase 0M-R3, hollow Phase 0M-R2.*

## What this is NOT

The quantity above is a **local fatigue-relevant inelastic response metric**: accumulated
equivalent inelastic strain per stabilised cycle, numerically converged and tied to a
documented solder-fatigue mechanism. It is a RESPONSE. It becomes DAMAGE only through a
sourced damage law, LIFE only through a life model, and a FAILURE CRITERION only with an
admissible allowable. None of those three is closed, so no statement of the form "Z2 lasts
1.19x longer" is available from this result.

## The TSV has no process margin

ARCH_Z2 sits at AR = 10.000, which passes the hard rule and gives M_AR = 1.000 -- the
boundary, not margin. Under a modest bound of -2 % diameter and +2 % depth it reaches
10.408 and violates the rule. A 34 um via, inside the sourced range, restores M_AR = 1.089
at the cost of 22.8 % more vias and a change of 0.02 % or less in copper fraction, field
resistance, thermal tensor, modulus and CTE. That is the Phase-0M allocation law confirmed
on a case it was not derived for.

![FIG-0MR3-C]({FIG}/FIG_0MR3_C_tsv_margin.png)

*FIG-0MR3-C. The hard rule and the design margin are different questions.*

## Cooling: the gap is closed by prohibition, not by interpolation

No correlation valid for a rectangular liquid microchannel in 2300 < Re < 3000 could be
sourced. Crossref and OpenAlex were reachable and returned nothing whose coefficients and
validity range could be read from an accessible primary text, and writing one from memory
would put unverifiable numbers into the production model. The band is therefore permanently
OUT_OF_MODEL_DOMAIN and **the production cooling design space is capped at Re <= 2300**.
The production point at 27 g/s sits at Re = 1264.8, far inside the validated domain, so
nothing in this phase depends on the gap.

![FIG-0MR3-D]({FIG}/FIG_0MR3_D_cooling_validity.png)

*FIG-0MR3-D. The shaded band has no sourced correlation and is now outside the design space.*

## Report state: {len(stale)} findings behind a zero-stale certificate

Phase 0M-R2 certified 0 stale current-facing claims. This phase found **{len(stale)}**, and
registered **DEFECT #56**. A section-scoped checker is still contract-driven: it cannot see
a contradiction BETWEEN two fields, and it cannot see a structural defect at all. Among the
findings: one paragraph shipped four times, two different report dates, a provenance table
claiming a solver that is not installed, the mechanical criterion described as though it were the
only obstacle to G2 when three independent ones exist, and the FE response metric called DAMAGE.

## Verdict

**E --- Z1/Z2 FEASIBILITY REMAINS CONDITIONAL ON OPEN PACKAGE RULES.**

A realizable Z1 and a realizable Z2 exist and pass every condition of the frozen contract
at all 27 corners of the bounded clearance envelope, and the deciding ordering survives
the repair essentially unchanged. Neither can be called PROVEN_REALIZABLE while three
package clearances are unsourced and ARCH_Z2's TSV field has zero process margin.

The optimizer remains **FORBIDDEN**.

<!-- END GENERATED: {TAG} -->
"""


def main() -> int:
    s = REP.read_text()
    fixed = []
    # Phase 0M-R2 is no longer current authoritative
    old = ("# Phase 0M-R2 --- Architecture Realizability, Cooling-Regime and "
           "Current-State Closure (current authoritative)")
    new = ("# Phase 0M-R2 --- Architecture Realizability, Cooling-Regime and "
           "Current-State Closure (superseded by Phase 0M-R3)")
    if old in s:
        s = s.replace(old, new); fixed.append("Phase 0M-R2 -> historical")
    body = narrative()
    pat = rf"<!-- BEGIN GENERATED: {TAG} -->\n.*?<!-- END GENERATED: {TAG} -->\n"
    if re.search(pat, s, re.S):
        s = re.sub(pat, lambda _m: body, s, count=1, flags=re.S)
        fixed.append("Phase 0M-R3 chapter replaced")
    else:
        k = s.index("<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml")
        s = s[:k] + body + "\n" + s[k:]
        fixed.append("Phase 0M-R3 chapter inserted")
    gs = (R / "results" / "phase0g" / "generated_status_sections.md").read_text()
    st = s.index("<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml")
    m = re.search(r"\n+\\newpage\n+# References", s[st:])
    assert m, "status block boundary not found"
    s = s[:st] + gs.rstrip("\n") + s[st + m.start():]
    s = s.replace("## Current scientific status (Phase 0M-R2)\n",
                  "## Current scientific status (Phase 0M-R3)\n")
    fixed.append("status block refreshed")
    REP.write_text(s)
    for x in fixed:
        print("  " + x)
    print(f"\nreport now {len(s.splitlines())} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
