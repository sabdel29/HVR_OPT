# Phase 0K-R Sec. 1 — DEFECT #39, confirmed and fixed

## Confirmed

**The Phase-0K narrative section was current. The generated current-status fragments were not.**

The Executive Summary's **"Exact next work"** read, verbatim:

> "PHASE 0K — SYSTEM-OWNER MISSION DEFINITION. … The remaining blocker is therefore NOT
> mechanics and NOT literature: it is a REQUIRED LIFE, which must be declared by the system
> owner."

Both halves were wrong by the time they were read. Phase 0K had **run**, and Phase 0K's central
result was precisely that the required life is **not** the only blocker.

Worse than a single stale sentence: **no Phase-0K result appeared in current-facing text at
all.** Counting occurrences in `current_facing` before the fix —

| Phase-0K result | occurrences in current-facing text |
|---|---|
| the 474 / 3206 robust decision regions | **0** |
| the "two open pieces" finding | **0** |
| the G2 decision map | **0** |
| the board-level experiment design | **0** |

## Fixed

`next_work` rewritten from the source of truth to state: mission input and experiment
preparation **in parallel**; the two-blocker result; the −40 °C withdrawal and why; the
within-domain replacement; the specimen increase; and the declared stress-domain limitation.

Sec. 2's structured contract added so the current state is **generated, not hand-maintained**:
`relative_life_0kr`, `absolute_life_0kr`, `mission_0kr`, `g2_0kr`, `experiment_0kr`,
`next_step_0kr`.

## Guards, with verbatim self-tests

Four new current-facing guards, each paired with the **exact forbidden sentence** Sec. 3 names:

| guard | verbatim self-test sentence |
|---|---|
| `Phase 0K named as the next work` | "Exact next work. PHASE 0K — SYSTEM-OWNER MISSION DEFINITION." |
| `-40 C test called validated by the current model` | "The -40 C test is validated by the current SAC305 material model." |
| `16 specimens claimed sufficient for all scatter` | "16 specimens per cell is proven sufficient for all plausible Weibull scatter." |
| `one thermal condition claimed to identify the law` | "One thermal condition identifies the fatigue law." |

Together with the Phase-0K guards these cover the remaining Sec. 3 list — *"N_required is the
sole blocker."*, *"Only one failure mechanism is computable."*, *"No SAC305 life law exists."*,
*"2.5D is eliminated."* — all of which already had guards and self-tests from earlier phases.

**All negative-tested:** each sentence injected verbatim into a current-facing section, the
build failing on its own guard, content restored, `PDF VERIFIED`.

## Sec. 34 — audited after generation, not before

The final Markdown **and the text extracted from the final PDF** were re-read against fifteen
stale formulations across **8 current-facing headings**.
**Result: 0 hits in the Markdown, 0 in the PDF.** Record: `POSTBUILD_SEMANTIC_AUDIT.md`.

This step is mandatory because the three most recent report defects all occurred **at or after
the generation step**, not in the source:

| defect | where the truth was right | where it was wrong |
|---|---|---|
| #35 | the phase's own findings | the generated current-facing sections |
| #38 | the Phase-0J-R narrative | the generated Executive Summary |
| **#39** | **the Phase-0K narrative** | **the generated next-work and status fragments** |

## Pattern

#29 stale withdrawal · #32 stale scope · #35 stale capability · #37 stale superseded instrument
· #38 stale negative · **#39 stale next-step**.

Six instances of one failure: **the narrative advances and the generated status does not.** The
structural fix in this phase is not another guard but the Sec. 2 contract — current status is
now generated from typed fields rather than from prose that must be remembered to update — plus
the Sec. 34 rule that the **built artifact** is what gets audited.
