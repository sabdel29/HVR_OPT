# Phase 0K-R Sec. 18 — Failure criterion, re-read against the primary

## What Syed 2004 actually says

Verbatim from the author-corrected paper:

> "The resistance of each electrical net was measured **every two minutes** and was compared
> with the **threshold resistance of 300 ohms**. A net is considered as failed at the **first
> instance** when its resistance exceeded the threshold value **followed by ten additional such
> instances within 10 % of the time of first failure**. The failures were **also confirmed
> manually within a week** of first occurrence."

## Element-by-element comparison with the Phase-0K proposal

| element | Syed 2004 | Phase-0K proposal | match? |
|---|---|---|---|
| threshold | **300 Ω** | 300 Ω | **exact** |
| sampling interval | **every 2 minutes** | "≤ 2 min" | **compatible** — ours is at least as fast |
| confirmation count | **ten additional instances** | ten further events | **exact** |
| temporal tolerance | **within 10 % of the time of first failure** | within 10 % of t | **exact** |
| manual confirmation | **within a week** | not specified | **DIFFERENCE — now added** |
| intermittent opens | counted, provided the confirmation rule is met | not stated | **DIFFERENCE — now stated** |
| statistic the model predicts | **MEAN life** (Table 2b reports 1st failure, β, characteristic life and mean life; the models predict mean) | mean life via η·Γ(1+1/β) | **exact** |

## Verdict on the "Syed's exact rule" wording

**Substantially accurate, and now made exact.** The threshold, confirmation count, temporal
tolerance and reported statistic all match the primary. Two items were unstated rather than
wrong, and are now specified:

1. **Manual confirmation within one week of first occurrence** is adopted.
2. **Intermittent opens count**, provided the ten-within-10 % rule is satisfied — i.e. a single
   transient excursion above 300 Ω is not a failure, and the criterion is a confirmed event
   sequence rather than a first crossing.

With those two added the proposed monitor **is** Syed's rule, and the phrase may be used.

## What must not be substituted

* **Not** a 50 % resistance-increase endpoint. It occurs materially earlier than a 300 Ω open
  and would bias the fitted constant.
* **Not** characteristic life η in place of mean life. For β ≈ 5 the mean is about 8 % below η
  and for β ≈ 10 about 5 % below — small, systematic, in the direction of over-predicting life,
  and free to remove by reporting `η·Γ(1+1/β)` explicitly.
* **Not** a crack-length endpoint. Darveaux's framework uses one; Syed's does not, and the
  constants being calibrated here are Syed's.
