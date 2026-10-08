# DEFECT #44 — report-propagation audit

**Phase 0L-R, Part 1.** Directed comparison of BOTH reports against the Phase-0L findings.
Machine-readable: `results/phase0lr/defect44_hits.csv`. Scanner: `scripts/phase0lr/propagation_audit.py`.

## Method

Thirteen stale-claim patterns named by the brief were searched in both reports. Each hit is classified by the SCOPE of the chapter it sits in and by whether its own sentence carries a retraction.

* **HISTORICAL report** — chronological. A `# Phase 0X … (superseded by | extended by)` chapter is HISTORICAL and its subsections inherit that scope; everything else at top level is CURRENT-FACING.
* **STANDALONE report** — describes only today, so EVERY section is CURRENT-FACING by definition (brief, Part 23). A stale claim anywhere in it is a defect.

A scanner bug was found and fixed during this audit: `##` subsections did not inherit their parent chapter's scope, so subsections inside superseded chapters were read as current and the historical report appeared far more damaged than it is. The counts below are post-fix.

## Result

| report | STALE-CURRENT | HISTORICAL-UNMARKED | CURRENT-RETRACTED | HISTORICAL-RETRACTED |
|---|---|---|---|---|
| HISTORICAL | **12** | 13 | 4 | 4 |
| STANDALONE | **9** | 0 | 3 | 0 |

> **DEFECT #44 is CONFIRMED.** 21 stale current-facing hits across the two reports.

## Classification of every named claim

| id | claim | historical report | standalone report | verdict |
|---|---|---|---|---|
| C01 | Z2/Z1 = 1.21-1.38 presented as current | CURRENT-FACING, STALE | not present | **FALSE** — 1.21–1.38 is superseded by 1.17–1.39 (Phase 0L) and by the strain-family envelope 1.19–1.22 (Phase 0L-R) |
| C02 | relative life called validated | CURRENT-FACING, STALE | not present | **FALSE** — 'VALIDATED relative life' is not earned; the correct level is CONDITIONAL (Part 14) |
| C03 | experiment called ready to execute | CURRENT-FACING, STALE | not present | **FALSE** — the experiment is BLOCKED, not ready to execute |
| C04 | 34 specimens per cell as current | CURRENT-FACING, STALE | **STALE in §23.1** | **FALSE** — 34/cell is superseded; §17.4 of the same standalone report already says 68 |
| C05 | 136 packages as current | CURRENT-FACING, STALE | **STALE in §23.1** | **FALSE** — 136 packages is superseded |
| C06 | creep data called SAC305 | CURRENT-FACING, STALE | **STALE in §4.2** | **FALSE** — the creep data is Sn3.9Ag0.6Cu, not SAC305 |
| C07 | creep model called valid over the operating regime | CURRENT-FACING, STALE | correctly retracted | **FALSE** — 'near its calibrated range' was withdrawn in Phase 0L |
| C08 | eps_dot = A sigma^n given as the current CalculiX law | not present | definitional use only | **CURRENT** — eps_dot = A sigma^n is correct for the zero-yield case and as a generic Norton definition; it is NOT presented as the combined-deck law |
| C10 | mechanics described as M0 only | CURRENT-FACING, STALE | not present | **FALSE** — 'M0 only, no creep or fatigue' ignores the LOCAL joint model (Part 21) |
| C11 | high-stress extrapolation said to cancel | CURRENT-FACING, STALE | definitional use only | **FALSE in the historical report**; the standalone hits are the definition of cancellation and the NOT-DEFENSIBLE column, both correct |
| C12 | N_required called the only blocker | CURRENT-FACING, STALE | correctly stated as two blockers | **FALSE** — there are two blockers, not one |
| C13 | Phase 0K-R said to have frozen or closed the matrix | CURRENT-FACING, STALE | not present | **FALSE** — Phase 0K-R did not close the matrix; Phase 0L unfroze it |

## Where the damage is

In the historical report every stale current-facing hit is in one of three places:

1. **Executive Summary** — 8 hits. It is a GENERATED block driven by `current_facing.executive_summary` in the status YAML, and that block had not been updated for Phase 0L at all. The Executive Summary contains **no mention of Phase 0L**.
2. **Governing-equation status** — 2 hits, including the sentence 'C still cancels in a ratio, so the RELATIVE ratio Z2/Z1 = 1.21–1.38 is validated', which is wrong three times over: the number, the word validated, and the cancellation claim.
3. **Mechanical Model Validation** — 1 hit, 'M0 rung only … no plasticity, creep or fatigue', which describes the GLOBAL model as if it were the whole mechanical model.

All three are generated from the status YAML, so the repair is at the source, not in prose.

In the standalone report there are three genuine defects (§4.2 alloy label, §23.1 specimen count, and the §13.7 stress range), plus one wrong mechanism in §17.2. The remaining hits are the scanner matching correct definitional text — for instance §22.4 defining what 'cancels in a ratio' means, and §24 listing the cancellation claim in the NOT-DEFENSIBLE column.

The §23.1 finding is the most serious of all, because it is **internally inconsistent within one document**: §17.4 says 68 specimens per cell and §23.1 says 34.

## HISTORICAL-UNMARKED hits

13 hits sit in superseded chapters and state that chapter's own finding without an in-sentence retraction. These are ACCEPTED: the chapter heading carries '(superseded by …)' or '(extended by …)', which is the marking the brief requires. Rewriting them would falsify the chronological record.
