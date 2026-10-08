#!/usr/bin/env python3
"""Phase-0M-R3 --- audit documents generated from the result files."""
from __future__ import annotations
import csv, sys
from pathlib import Path
import yaml

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3"


def rd(n):
    p = OUT / n
    return list(csv.DictReader(p.open())) if p.is_file() else []


def f(x, d=4):
    try:
        return f"{float(x):.{d}f}"
    except (TypeError, ValueError):
        return str(x)


def report_state_audit() -> None:
    before = rd("stale_claims_before.csv")
    after = rd("stale_claims_after.csv")
    fam = {}
    for r in before:
        fam[r["rule_family"]] = fam.get(r["rule_family"], 0) + 1
    md = f"""# PHASE 0M-R3 SECTION 1 --- FINAL REPORT-STATE AUDIT

> Phase 0M-R2 certified **0 stale current-facing claims**.
> Phase 0M-R3 finds **{len(before)}**, in {fam.get('claim',0)} claim, {fam.get('cross_field',0)}
> cross-field and {fam.get('structural',0)} structural findings.

## Why a second section-scoped audit found more --- DEFECT #56

Phase 0M-R2 fixed the flat-string failure by making the checker SECTION-SCOPED. It stayed
**contract-driven**: it could only find a contradiction for a claim already written into
its list. Three weaknesses follow, and all three were exercised.

**1. Cross-field contradictions are invisible to a list of claims.** Two fields can each
be well-formed and jointly inconsistent. An open-items entry called the mechanical
criterion "the single blocking item for G2" while the authoritative G2 field lists THREE
independent blockers. Neither statement is wrong in isolation; together they cannot both
hold.

**2. Structural defects are not claims at all.** One paragraph was shipped FOUR times. A
provenance row read "Report date 2026-09-08" beside a front matter reading 2026-09-17.
Neither is a scientific assertion, so no claim-shaped rule could express either.

**3. The retraction heuristic cleared sentences it should not have.** A nearby "WITHDRAWN"
-- about a different statement in the same paragraph -- exonerated both the cooling
wording and the "measures DAMAGE" wording. Self-contradictory claims are now marked
`retraction_exonerates: false`.

## The findings

| family | rule | section | problem |
|---|---|---|---|
""" + "".join(
        f"| {r['rule_family']} | `{r['rule_id']}` | {r['section'][:30]} | {r['problem'][:85]} |\n"
        for r in before) + f"""
## The five the brief named, each confirmed

| # | issue | verdict | what was found |
|---|---|---|---|
| 1A | cooling wording | **CONFIRMED** | the verdict bullet read "THE COOLING MODEL HAS A DOMAIN HOLE, AND THE PRODUCTION POINT IS NOT IN IT" immediately before a sentence saying the production point is inside the validated domain. Now: "...BUT THE PRODUCTION POINT IS NOT IN IT -- THE 50 G/S COMPARISON POINT IS." |
| 1B | G2 single blocker | **CONFIRMED** | `mechanical_criterion.why_it_matters` said "the single blocking item for G2", and it reached the report. Now "ONE OF THREE INDEPENDENT blockers", and a cross-field invariant fails any section that asserts a different count |
| 1C | "damage" wording | **CONFIRMED** | `verdict.what_this_is_not` said "since Phase 0I it measures DAMAGE and not only load". It was line-wrapped in the report, so a plain grep missed it. Now a LOCAL FATIGUE-RELEVANT INELASTIC RESPONSE METRIC, with the ladder response -> damage -> life -> criterion stated and three rungs marked open |
| 1D | report dates | **CONFIRMED** | front matter 2026-09-17, provenance row "Report date 2026-09-08". Now three labelled rows: generated, repository baseline, phase completed |
| 1E | duplicate blocks | **CONFIRMED, REAL SOURCE DUPLICATION** | four identical copies of one paragraph at lines 1169-1175. Not an extraction artifact. The Phase-0M-R2 builder inserted outside a sentinel block and its idempotency guard had a case mismatch, so each re-run added a copy. Sentinel blocks themselves were all unique, which is why the sentinel test passed |

## A sixth, found by the new tool-availability invariant

The provenance table claimed **"PALACE (built, functional)"**. Palace is not on this system
-- Phase 0M-R2's own environment record already said NOT FOUND. Neither statement is a
scientific claim, so only a cross-field rule comparing the provenance table against the
measured environment could catch it.

## After the repair

**{len(after)} finding(s).** The repair script is idempotent: a second run reports nothing
to do, which is the property whose absence produced the duplicated paragraph.
"""
    (OUT / "FINAL_REPORT_STATE_AUDIT.md").write_text(md)
    print(f"  wrote {OUT/'FINAL_REPORT_STATE_AUDIT.md'}")


def failure_decomp() -> None:
    rows = [r for r in rd("realizability_failure_matrix.csv") if r["corner"] == "BEST"]
    md = """# PHASE 0M-R3 SECTION 3 --- REALIZABILITY FAILURE DECOMPOSITION

Every condition as a distance-to-feasibility ratio (required / available). Above 1.0 is a
failure; how far above says whether the repair is modest or structural. Evaluated at the
MOST FAVOURABLE corner of the bounded clearance envelope, so nothing here is pessimistic.

| template | architecture | area | height | routing | J | TSV count | TSV AR |
|---|---|---|---|---|---|---|---|
"""
    for r in rows:
        md += (f"| {r['template']} | {r['arch'].replace('ARCH_','')} | "
               f"{f(r['area_ratio'],3)} | {f(r['height_ratio'],3)} | "
               f"{f(r['routing_ratio'],3)} | {f(r['current_density_ratio'],3)} | "
               f"{f(r['tsv_count_ratio'],3)} | {f(r['tsv_AR_ratio'],3)} |\n")
    md += """
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
"""
    (OUT / "REALIZABILITY_FAILURE_DECOMPOSITION.md").write_text(md)
    print(f"  wrote {OUT/'REALIZABILITY_FAILURE_DECOMPOSITION.md'}")


def tsv_margin() -> None:
    rows = rd("tsv_margin_sweep.csv")
    md = """# PHASE 0M-R3 SECTION 7 --- TSV PROCESS MARGIN

## The hard rule and the design margin are different questions

    hard rule      AR = L/d <= AR_max = 10
    design margin  M_AR = AR_max / AR_actual

Phase 0M-R2 reported ARCH_Z2, Z4 and Z5 at AR = 10.000 exactly. That passes the rule and
gives **M_AR = 1.000**, which is not margin -- it is the boundary.

| architecture | d | AR nominal | M_AR nominal | AR worst | M_AR worst | under a modest bound |
|---|---|---|---|---|---|---|
"""
    for arch in ("ARCH_Z1_EMBEDDED", "ARCH_Z2_BACKSIDE"):
        for d in ("30.0", "34.0", "40.0"):
            n = next((r for r in rows if r["arch"] == arch and r["d_nominal_um"] == d
                      and r["tolerance_case"] == "none"), None)
            m = next((r for r in rows if r["arch"] == arch and r["d_nominal_um"] == d
                      and r["tolerance_case"] == "modest"), None)
            if not (n and m):
                continue
            md += (f"| {arch.replace('ARCH_','')} | {f(d,0)} um | {f(n['AR_nominal'],3)} | "
                   f"{f(n['M_AR_nominal'],3)} | {f(m['AR_worst'],3)} | "
                   f"{f(m['M_AR_worst'],3)} | "
                   f"{'OK' if m['feasible_worst']=='True' else '**FAILS**'} |\n")
    md += """
## The tolerance bound is a PARAMETRIC BOUND, not a distribution

No source in this repository gives a TSV fabrication tolerance, so none is invented and no
Gaussian is assumed. Three labelled cases are swept:

| case | diameter | liner | via depth |
|---|---|---|---|
| none | 0 % | 0 % | 0 % |
| modest | -2 % | +10 % | +2 % |
| loose | -5 % | +20 % | +5 % |

The worst corner is the smallest diameter with the deepest via, which is the physically
correct pairing for an aspect-ratio limit.

## Result

**The 30 um via does NOT survive a modest bound on ARCH_Z2.** At -2 % diameter and +2 %
depth the aspect ratio reaches 10.408 and the hard rule is violated. ARCH_Z1, whose vias
traverse 74 um rather than 300 um, sits at M_AR = 3.895 even under the modest bound and is
unaffected.

**The smallest sourced diameter that restores positive margin is 34 um**, M_AR = 1.089.
That is inside the sourced range `design_variables.tsv.radius_m = {lo 2.5, nominal 15,
hi 50} um`, so it requires no new process.

## What changing the diameter costs --- almost nothing, and that is the point

| quantity | 30 um | 34 um | change |
|---|---|---|---|
| vias required | 15 140 | 11 692 | **-22.8 %** |
| copper fraction | 0.020002 | 0.020002 | -0.00 % |
| field resistance | 0.64026 uOhm | 0.64027 uOhm | +0.00 % |
| k_z | 134.92 W/mK | 134.94 W/mK | +0.02 % |
| E_xy | 167.18 GPa | 167.22 GPa | +0.02 % |
| CTE_eff | 2.7996e-6 | 2.7997e-6 | +0.00 % |

This is the Phase-0M TSV allocation law confirmed on a case it was not derived for: under
minimum-capability provisioning the copper fraction is radius-independent, so enlarging
the via changes the COUNT and essentially nothing else. The electrical, thermal and
mechanical behaviour of the field is unchanged to 0.02 %.

**Consequence for this phase.** The frozen realizability contract tests the HARD RULE,
which 30 um passes, so the frozen pair remains contract-compliant and the margin is
reported separately exactly as the contract requires. But ARCH_Z2 as frozen has no process
margin on its TSV field, and that is a named condition on its realizability, not a detail.
Closing it costs 22.8 % more vias and no measurable E/T/M change.
"""
    (OUT / "TSV_PROCESS_MARGIN.md").write_text(md)
    print(f"  wrote {OUT/'TSV_PROCESS_MARGIN.md'}")


def cooling_lit() -> None:
    reg = yaml.safe_load(
        (R / "configs/phase0mr3/cooling_correlation_registry.yaml").read_text())
    t = next(c for c in reg["correlations"]
             if c["id"] == "TRANSITIONAL_RECTANGULAR_MICROCHANNEL")
    md = f"""# PHASE 0M-R3 SECTION 10 --- TRANSITIONAL COOLING LITERATURE AUDIT

## The question

Phase 0M-R2 found 2300 < Re < 3000 uncovered: above the laminar ceiling, below
Gnielinski's floor, with the two neighbours differing by a factor of 2.76 there. Can a
correlation valid for a rectangular liquid microchannel in that band be sourced?

## What was searched

| query | |
|---|---|
""" + "".join(f"| `{q}` | |\n" for q in t["search_record"]["queries"]) + f"""
APIs reachable from this host: {', '.join(t['search_record']['apis_reached'])}.
WebSearch is blocked in this environment.

## Outcome: NOTHING USABLE

{t['search_record']['outcome']}

**Nothing was implemented.** {t['search_record']['why_nothing_was_implemented']}

## Decision: restrict the production design space

    production design space: Re <= 2300

{reg['meta']['production_design_space_rule']}

The registry keeps Gnielinski with its real floor of 3000 so that any evaluation above
that dispatches to a correlation whose range covers the point, and keeps an explicit OPEN
entry for the gap so the absence is recorded rather than implied.

## Boundary continuity

Reported, not smoothed:

| | |
|---|---|
| laminar Nu at Re = 2300 | {reg['boundary_continuity_check']['laminar_Nu_at_2300']} |
| Gnielinski Nu at Re = 2342 | {reg['boundary_continuity_check']['gnielinski_Nu_at_2342']} |
| ratio | **{reg['boundary_continuity_check']['ratio']}** |

A factor of 2.76 across the gap is precisely why interpolating it to obtain a smooth curve
would be fabricating the answer.

## Effect on this phase

None on the production result. The production cooler runs at 27 g/s, Re = 1264.8, well
inside the validated laminar domain. The restriction removes flow rates the design never
used and forbids the framework from ever quoting one again without a source.
"""
    (OUT / "TRANSITIONAL_COOLING_LITERATURE_AUDIT.md").write_text(md)
    print(f"  wrote {OUT/'TRANSITIONAL_COOLING_LITERATURE_AUDIT.md'}")


if __name__ == "__main__":
    report_state_audit(); failure_decomp(); tsv_margin(); cooling_lit()
