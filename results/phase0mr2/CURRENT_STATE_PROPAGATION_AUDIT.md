# PHASE 0M-R2 SECTION 1 --- CURRENT-STATE PROPAGATION AUDIT

> **The Phase-0M-R assertion of "0 stale current-facing claims" is DISPROVED.**
> **17 stale findings across 9 distinct claims**, in a report that passed
> 46 of 46 cross-report checks.

## Why the checker passed a report full of stale claims --- DEFECT #54

The Phase-0M-R cross-report checker had three independent weaknesses, and all three were
necessary for the failure:

**1. It matched each report as ONE FLAT STRING.** A REQUIRED phrase found ANYWHERE
satisfied the check for the whole document. The word `microchannel` occurring in the
Phase-0M-R chapter satisfied the cooling check while the Validation Status block three
thousand lines earlier still described the frozen inverse-calibrated Robin boundary.
Presence somewhere is not propagation everywhere.

**2. It could not detect an OMISSION at all.** A current-facing section that simply never
mentions a production model cannot be caught by a forbidden-phrase list. The Thermal Model
Validation block failed this way: it does not contain a false sentence, it is missing a
true one.

**3. Its FORBIDDEN patterns were paraphrases.** The pattern written for the intra-VR
defect row was `NOT IN THE PRODUCTION LOSS`; the report's actual sentence is
`NOT YET WIRED INTO THE PRODUCTION LOSS TOTAL`. The paraphrase does not match the real
text. This is the failure mode the project's own standing rule warns about, reproduced by
the checker written to prevent it.

A fourth, smaller gap: the chapter-supersession vocabulary knew `superseded by` and
`extended by` but not `rescoped by`, so the Phase 0I chapter was read as current-facing.

## The seventeen findings

| claim | section | problem |
|---|---|---|
| `gate_count` | Executive Summary | current wording absent: count word is 'Seventeen', expected 'Nineteen' |
| `gate_count` | Executive Summary | historical wording in a current-facing section |
| `phase_authority` | Executive Summary | current wording absent: no sentence of the form 'Phase 0M-R2 is the current authoritative phase' |
| `phase_authority` | Phase 0M --- Geometry-Resolved Power Deliver | historical wording in a current-facing section |
| `next_work` | Executive Summary | current wording absent: next-work paragraph must reference the Phase-0M-R2 ledger |
| `next_work` | Executive Summary | historical wording in a current-facing section |
| `transition_resistance_production` | Electrical Model Validation | current wording absent: electrical validation must state the per-class transition resistance |
| `transition_resistance_production` | Electrical Model Validation | historical wording in a current-facing section |
| `cooling_production_boundary` | Thermal Model Validation | current wording absent: thermal validation must state the physical cooler in production |
| `intravr_routing_production` | Model Defects Discovered and Fixed | current wording absent: defect register must record intra-VR routing |
| `intravr_routing_production` | Phase 0M-R --- production-coupling closure | historical wording in a current-facing section |
| `cooling_model_adopted` | Phase 0M-R --- production-coupling closure | historical wording in a current-facing section |
| `thermal_separation` | Executive Summary | current wording absent: must state that the architectures DO separate in temperature |
| `thermal_separation` | Architecture Comparison | current wording absent: must state that the architectures DO separate in temperature |
| `thermal_separation` | Executive Summary | historical wording in a current-facing section |
| `report_date` | __frontmatter__ | current wording absent: date is 2026-09-08 |
| `report_date` | __frontmatter__ | historical wording in a current-facing section |

## The eight stale claims, with the verbatim text recovered from the delivered report

| # | claim | what the report said | what is true after Phase 0M-R |
|---|---|---|---|
| A | gate count | "Seventeen sequential falsification gates (0B ... 0M)" | nineteen, through 0M-R2. The count and the list are now DERIVED from `meta.gates`, not typed |
| B | phase authority | "# Phase 0M --- ... (current authoritative)" | Phase 0M-R2 is current authoritative; exactly one heading may carry the label |
| C | exact next work | "MATERIAL CHARACTERISATION FIRST, with PRIMARY-PAPER ACQUISITION IN PARALLEL" | the Phase-0M-R2 ranked follow-up, which must agree with the open-items ledger |
| D | current crowding | "**No current-crowding correction was applied**, because none was demonstrated" | a per-class Delta_R = R_3D - R_1D is in production, cross-validated against MOOSE at 0.25-0.73 % |
| E | thermal boundary | the Validation Status block describes only the Phase-0E/0F MOOSE cross-check and the discarded Icepak run | a physical microchannel cooler is in the production loop. This one is an OMISSION, not a false sentence |
| F | defect 51 | "CONFIRMED, MODEL BUILT, NOT YET WIRED INTO THE PRODUCTION LOSS TOTAL" | closed in Phase 0M-R; the row must say so |
| G | defect 52 | "CONFIRMED, MODEL BUILT, NOT YET ADOPTED BY THE ETM LOOP" | closed in Phase 0M-R; the row must say so |
| H | thermal separation | "these particular architectures happen not to differ in temperature" | under the physical cooler they DO separate, and Z2 is the hottest |

A ninth was found while building the contract: the document carries `date: "2026-09-08"`,
nine days older than the phases inside it.

## A tenth finding: the defect register itself stopped at 52

Phase 0M-R documented DEFECT #53 in `results/phase0mr/DEFECT53_REPORT_STATE_AUDIT.md` and
referenced it in three superseded notes, but never added it as a numbered row. The
register ended at 52 while the prose spoke of #53. It is registered retroactively in this
phase, and the new defect is #54.

## The fix

`configs/phase0mr2/current_state_claims.yaml` gives every claim:

    claim_id, status, originating phase, superseding phase, current wording,
    historical wording, sections where CURRENT wording is REQUIRED, sections where
    HISTORICAL wording is ALLOWED, evidence artifact, and the verbatim stale sentence

`scripts/phase0mr2/claim_propagation.py` checks each NAMED SECTION for the current wording
and for un-qualified historical wording. It fails if a current section carries a
historical status, if a later phase is missing from the gate list, if a superseded phase
claims authority, if a defect row reads as live without naming the phase that closed it,
or if the next-work text does not reference the current ledger.

## Negative-test evidence

Every guard was tested against the REAL sentence, never a paraphrase.

| claim | injected sentence (verbatim, truncated) | passes clean | fails on injection |
|---|---|---|---|
| `gate_count` | Seventeen sequential falsification gates (0B, 0C, 0D, 0D-R, 0E, 0F, 0G, 0H, 0I, 0I-R, 0J | True | **True** |
| `phase_authority` | # Phase 0M --- Geometry-Resolved Power Delivery, Component-Level Architecture, Cooling a | True | **True** |
| `next_work` | **Exact next work.** MATERIAL CHARACTERISATION FIRST, with PRIMARY-PAPER ACQUISITION IN  | True | **True** |
| `transition_resistance_production` | **No current-crowding correction was applied**, because none was demonstrated --- | True | **True** |
| `intravr_routing_production` | - *Status:* **CONFIRMED, MODEL BUILT, NOT YET WIRED INTO THE PRODUCTION LOSS TOTAL** | True | **True** |
| `cooling_model_adopted` | - *Status:* **CONFIRMED, MODEL BUILT, NOT YET ADOPTED BY THE ETM LOOP** | True | **True** |
| `thermal_separation` | The current Z-architectures nevertheless separate on MECHANICS, not temperature: their j | True | **True** |
| `report_date` | date: "2026-09-08" | True | **True** |

Two further guards were found to be too weak while writing these tests, and both were the
same defect one level down: checking that a gate name appears *somewhere in the section*
passed when `0M-R2` occurred in a neighbouring sentence, and checking that the current
phase name appears *somewhere in the section* passed when a superseded phase claimed
authority two lines away. Both now parse the actual sentence: the enumerated gate list is
compared element by element, and the authority claim is matched as a whole clause.

`tests/phase0mr2/test_claim_propagation.py` holds 23 tests covering these.
