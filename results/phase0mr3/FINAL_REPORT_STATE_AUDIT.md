# PHASE 0M-R3 SECTION 1 --- FINAL REPORT-STATE AUDIT

> Phase 0M-R2 certified **0 stale current-facing claims**.
> Phase 0M-R3 finds **18**, in 4 claim, 4
> cross-field and 10 structural findings.

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
| claim | `g2_blockers_not_singular` | Phase 0M-R2 --- Architecture R | forbidden historical wording |
| claim | `cooling_production_point_not_in_gap` | Phase 0M-R2 --- Architecture R | forbidden historical wording |
| claim | `fe_output_is_response_not_damage` | Phase 0M-R2 --- Architecture R | forbidden historical wording |
| claim | `report_date_is_disambiguated` | Provenance and tool versions | forbidden historical wording |
| cross_field | `g2_blocker_count_consistent` | Phase 0M-R2 --- Architecture R | No current-facing section may assert a G2 blocker COUNT that differs from the authori |
| cross_field | `g2_blocker_count_consistent` | Phase 0M-R2 --- Architecture R | No current-facing section may assert a G2 blocker COUNT that differs from the authori |
| cross_field | `tool_availability_consistent` | Provenance and tool versions | No section may describe a solver as available when the measured environment says it i |
| cross_field | `tool_availability_consistent` | Provenance and tool versions | No section may describe a solver as available when the measured environment says it i |
| structural | `no_duplicate_paragraph` | - | paragraph appears 4 times |
| structural | `date_coherence` | - | 'Report date' = 2026-09-08 but front matter = 2026-09-17 |
| structural | `date_coherence` | Provenance and tool versions | required date label missing: 'Report generated' |
| structural | `date_coherence` | Provenance and tool versions | required date label missing: 'Repository baseline' |
| structural | `date_coherence` | Provenance and tool versions | required date label missing: 'Phase completed' |
| structural | `gate_count` | Executive Summary | expected Twenty and ['0B', '0C', '0D', '0D-R', '0E', '0F', '0G', '0H', '0I', '0I-R',  |
| structural | `date_coherence` | Provenance and tool versions | required date label missing: 'Report generated' |
| structural | `date_coherence` | Provenance and tool versions | required date label missing: 'Repository baseline' |
| structural | `date_coherence` | Provenance and tool versions | required date label missing: 'Phase completed' |
| structural | `gate_count` | Executive Summary | no gate sentence |

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

**0 finding(s).** The repair script is idempotent: a second run reports nothing
to do, which is the property whose absence produced the duplicated paragraph.
