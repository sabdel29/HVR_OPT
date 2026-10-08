# PHASE 0M-R SECTION 2 --- DEFECT #53 REPORT-STATE AUDIT

> **DEFECT #53 IS REAL AND CONFIRMED.**
> The current-scientific-status generator was internally consistent across both reports and
> consistently stale relative to the actual authoritative science. Cross-report consistency
> was **25/25** the entire time.

## What was wrong

The section headed **"Current scientific status (Phase 0M)"** printed a Phase-0M verdict line
followed by **six Phase-0H basis bullets** and a **Phase-0I next-gate rationale**. The
`verdict.basis` list had never been phase-scoped: `rejected_verdicts_` was scoped in an
earlier phase and `basis` was not, so every phase from 0I onward printed Phase-0H's six
bullets under its own verdict heading.

Worse, the **same report contradicted itself**. Its Executive Summary --- generated from
`current_facing`, which HAD been maintained --- said:

> "Two of eight failure mechanisms are now addressable: global bending (a driver) and solder
> fatigue (a real mechanism, added in Phase 0I)."

while the current-status section, two hundred lines later, said:

> "Of eight enumerated failure mechanisms, ONE is computable at M0."

Both were current-facing. Both were generated. Neither generator knew about the other.

## Why cross-report comparison could not catch it

Both reports derive from `results/CURRENT_SCIENTIFIC_STATUS.yaml`. Comparing them against
each other tests only that the same file was read twice. It passes by construction whenever
both are stale in the same way, which is the normal case for a shared generator. **Report
agreement is not evidence of correctness.**

## The five stale current-facing statements found

| id | verbatim fragment | contract field it contradicts | superseded by | copied from |
|---|---|---|---|---|
| `S1` | Of eight enumerated failure mechanisms, ONE is computable at M0 | `current_mechanical_capability` | Phase 0I added the solder-fatigue mechanism | `results/CURRENT_SCIENTIFIC_STATUS.yaml::verdict.basis[3] (Phase-0H text)` |
| `S2` | Neither local candidate survives validation for decision use | `current_solder_metric_status` | Phase 0I supplied a convergent metric; Phase 0I-R verified it | `results/CURRENT_SCIENTIFIC_STATUS.yaml::verdict.basis[5] (Phase-0H text)` |
| `S3` | both candidate sources return HTTP 403 | `current_life_law_status` | Phase 0J-R obtained the primary sources and reproduced the calibration | `results/CURRENT_SCIENTIFIC_STATUS.yaml::verdict.g2_note (Phase-0J text)` |
| `S4` | failure-relevant local damage metric with a sourced SAC305 constitutive model | `current_constitutive_status` | Phases 0L and 0L-R: the creep card is Sn3.9Ag0.6Cu and is not validated at package stresses | `results/CURRENT_SCIENTIFIC_STATUS.yaml::next_gate.rationale (Phase-0I text)` |
| `S5` | the project has been measuring the LOAD rather than the DAMAGE | `current_mechanical_capability` | Phase 0I added the local inelastic damage metric | `results/CURRENT_SCIENTIFIC_STATUS.yaml::verdict.what_this_is_not (Phase-0H text)` |
| `S6` | N_required is the sole blocker | `current_required_life_status` | Phase 0K withdrew that framing | `results/phase0k/G2_DECISION_REGIONS.md (quoted there in order to be refused)` |

`S6` is included in the guard even though it appears in the repository only inside a heading
that refuses it (`"N_required is the sole blocker" is false`), because the claim itself is
one an auditor might otherwise be told.

**Count: 5 distinct stale current-facing claims, appearing at 4 distinct sites in the
generated blocks** (S1, S2, S3, S4 each once; S5 in `verdict.what_this_is_not`, which feeds
the same section). All five are now repaired **at source**, in the YAML, not in the rendered
text --- and each repair carries a `_superseded_note` sibling recording what the text used to
say and which phase falsified it.

## The fix: an authoritative current-state contract

A keyword scanner over the reports can only find what someone already suspected. The fix is
an explicit contract of what is true NOW, one field per question an auditor would ask, each
with its own evidence path, living in the existing authoritative YAML under
`current_state_contract` so there is still exactly one source of truth.

| field | current state |
|---|---|
| `current_phase` | 0M-R (in progress); 0M complete |
| `current_verdict` | Phase 0M: MULTIPLE MISSING PHYSICAL COUPLINGS ARE FIRST ORDER -- OPTIMIZATION STILL PREMATURE (option G) |
| `current_ET_coupling_level` | ETM-L1: E <-> T iterated to a fixed point, T -> M one-way. Intact M -> E is 0.16 % of R against 22.8 % from rho(T); M -> T is 1.5 K for a 4 % TIM bond... |
| `current_mechanical_capability` | Global thermoelastic warpage and stress (M0), plus a convergent local solder viscoplastic damage metric (M2) added in Phase 0I and verified in 0I-R. T... |
| `current_solder_metric_status` | AVAILABLE AND CONVERGENT. Accumulated PEEQ path per stabilised cycle, volume averaged over the solder core, matched to the Syed 25 um averaging volume... |
| `current_constitutive_status` | CONDITIONAL. The creep card is fitted on Sn3.9Ag0.6Cu, NOT SAC305, over 7.51-15.92 MPa, while 99.8 % of package damage is generated outside that windo... |
| `current_life_law_status` | AVAILABLE FOR RELATIVE LIFE. The primary sources were obtained in Phase 0J-R and Syed 2004's author-corrected calibration was reproduced. HTTP 403 is ... |
| `current_required_life_status` | OPEN. No field or product requirement exists in this repository or any supplied source. It is NOT the sole G2 blocker -- Phase 0K withdrew that framin... |
| `current_G2_status` | NOT TESTED, and not testable. Two independent blockers, either sufficient: N_required is undefined, and absolute N_f is unvalidated. A mechanical ALLO... |
| `current_optimizer_status` | FORBIDDEN. None of the six preconditions is fully met. |
| `current_cooling_status` | SCREENING-ONLY, NOT IN PRODUCTION. The production ET loop still uses an inverse-calibrated Robin coefficient h_top = 166 000 W/m2K with one uniform si... |
| `current_routing_status` | LEVELS 2 AND 3 IN PRODUCTION; LEVEL 1 (intra-converter metallization) MODELLED BUT NOT IN THE PRODUCTION LOSS TOTAL. Worth 4.06 to 39.31 W system-wide... |
| `current_current_crowding_status` | SCREENING-ONLY. Production still multiplies every interconnect class by one global constant, 1.326. The measured spread over 107 geometries is 0.606 t... |
| `current_RDL_anisotropy_status` | MEASURED ON UNIT CELLS, NOT IN PRODUCTION. Single-direction line cells are 153x to 276x anisotropic; the production package still carries one isotropi... |
| `current_component_partition_status` | TEMPLATES EXIST, PRODUCTION SEES A LUMPED VR. Four-layer stacking is already assumed by the converter AREA model alone (max, not sum). A single-level ... |
| `current_next_work` | Phase 0M-R: wire the Phase-0M screening models into the production path and re-ask which Phase-0M conclusions survive. In parallel and NOT blocking: h... |

`scripts/phase0mr/state_contract.py` owns it, validates that every field is present and that
**every evidence path exists on disk**, and renders the table that both reports carry. That
validator earned its keep immediately: it rejected the first draft of the contract because
one evidence path was wrong.

## Forbidden current-facing claims

Section 24 of the brief lists claims that must never stand unqualified in a current-facing
block. They are compiled into the guard as patterns:

| id | pattern | contract field |
|---|---|---|
| `F1` | `only one mechanical mechanism (is )?computable` | `current_mechanical_capability` |
| `F2` | `no (SAC305 )?life law exists` | `current_life_law_status` |
| `F3` | `intra-VR routing is (already )?included` | `current_routing_status` |
| `F4` | `physical cooling is (already )?(active|in production|used)` | `current_cooling_status` |
| `F5` | `2\.5D (as a class )?is eliminated` | `current_phase` |
| `F6` | `TSV radius is (universally )?irrelevant` | `current_phase` |
| `F7` | `fully bidirectionally (ETM )?coupled|fully coupled ETM framework` | `current_ET_coupling_level` |
| `F8` | `CROWDING_DEFAULT = 1\.326 is (the )?current` | `current_current_crowding_status` |

## How the guard works, and why it is not a paraphrase test

`scripts/phase0mr/defect53_audit.py` scans only the **current-facing spans** --- the named
generated blocks and the current-status section --- and skips any hit whose sentence carries
an explicit historical marker, so a defect report may quote the defect it fixed. Every stale
entry is a **verbatim fragment copied from the artifact named in the last column**, never an
invented paraphrase. Two tests exercise it in both directions:

* **mutation:** change one contract field and BOTH reports must fail until regenerated;
* **injection:** insert a real stale sentence into a current-facing block and the build must
  fail.

## Result after repair

```
0 stale current-facing claim(s)
```
