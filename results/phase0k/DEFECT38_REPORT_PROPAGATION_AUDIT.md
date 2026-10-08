# Phase 0K Sec. 1 — DEFECT #38, confirmed and fixed

## Confirmed

A directed re-read of every current-facing section against the Phase-0J-R state found **nine
current-facing violations**, all of them in the Executive Summary, all generated from
`CURRENT_SCIENTIFIC_STATUS.yaml`.

| # | stale formulation, as it stood | why it is no longer authoritative |
|---|---|---|
| A | *"No lifetime is predicted anywhere."* | Phase 0J-R predicts conditional absolute life for all three architectures |
| B | *"…the EXPONENT m does NOT cancel, and no m is sourced for this metric and alloy."* | Two primary sources now bound it: Syed derives −1 and measures −0.9607; Schubert fits −1.3 |
| C | *"Over m = 0.5 to 5 the Z2/Z1 ratio spans 1.25 to 9.18."* | That span was a consequence of the unsourced exponent and is withdrawn |
| D | *"no SAC305 life law was retrievable"* (unqualified) | The primary papers were supplied; four formulations are admitted |
| F | *"Solder fatigue … has no life law and so yields no pass/fail"* ×2 | It has four admitted laws; what it lacks is a required life and an absolute calibration |
| G | *"Every life ratio is therefore labelled PARAMETRIC LIFE-LAW SENSITIVITY."* | The relative ratio is now validated, not parametric |
| H | *"a factor of 7.4 driven purely by the unsourced exponent"* | Same root cause as B and C |
| — | *"N_required … is the sole blocker"* | Withdrawn by Sec. 2 of this phase — see below |

## Fixed

All repaired at the single source of truth and regenerated. The current-facing text now
separates the four things the brief requires be kept apart:

| | status |
|---|---|
| **A. RELATIVE LIFE** | **VALIDATED** — Z2/Z1 = 1.21–1.38 across four admitted primary-source formulations |
| **B. CONDITIONAL ABSOLUTE LIFE** | numerical predictions exist, **NOT VALIDATED** — admitted formulations disagree 4.1× |
| **C. REQUIRED LIFE** | **OPEN** — no field or product requirement exists anywhere |
| **D. G2** | **NOT TESTED** |

Also corrected while fixing the above: `governing_equations.no_life_equation.note`,
`relative_life.exponent_status` (UNSOURCED → SOURCED AS OF PHASE 0J-R), and
`relative_life.exponent_provenance`.

## Guards

Six new current-facing guards, each with a **verbatim** `GUARD_SELFTEST` sentence taken from
the text that was actually standing in the report — the DEFECT #36 discipline:

| guard | self-test sentence |
|---|---|
| `no lifetime predicted anywhere` | "No lifetime is predicted anywhere." |
| `relative life called exponent-limited` | "A RELATIVE life ratio can be reported because the life-law constant C cancels in a ratio — but the EXPONENT m does NOT cancel, and no m is sourced for this metric and alloy." |
| `withdrawn 1.25-9.18 parametric life span` | "Over m = 0.5 to 5 the Z2/Z1 ratio spans 1.25 to 9.18." |
| `no SAC305 life law asserted` | "No admissible SAC305 life law exists for the current metric and regime." |
| `solder fatigue said to have no life law` | "Solder fatigue became computable at M2 but has no life law and so yields no pass/fail." |
| `N_required called the sole blocker` | "Requirement 2 is now the sole blocker: N_required must come from the system owner." |

**Negative-tested:** all six injected verbatim into a current-facing section; the build failed
on each with its own guard; content restored; `PDF VERIFIED`.

Two of the six caught **real** stale text that the manual audit had already flagged, and a
third — the `sole blocker` guard — caught the Phase-0J-R narrative itself, which is the defect
Sec. 2 of this brief exists to correct.

## Pattern

DEFECT #29 stale withdrawal · #32 stale scope · #35 stale capability · #37 stale superseded
instrument · **#38 stale negative**. A phase that converts a negative result into a positive one
must retire the negative's language as carefully as a phase that withdraws a claim retires the
claim. The Executive Summary had been describing a project that could not predict life, three
phases after it could.
