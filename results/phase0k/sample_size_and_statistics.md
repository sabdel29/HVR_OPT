# Phase 0K Sec. 13/15 — Specimens, statistics, and what "one test" means

## Sec. 13 — one TEST CONDITION is not one SPECIMEN

These are independent axes and conflating them is the error Sec. 13 exists to prevent:

| axis | what it controls | minimum here |
|---|---|---|
| **number of TEST CONDITIONS** | whether the **life law** can be identified | **2** — see `ABSOLUTE_LIFE_IDENTIFIABILITY.md` |
| **number of SPECIMENS per condition** | the **precision** of the life estimate at that condition | **16** recommended, 4 is the bare 3σ minimum |
| **number of ARCHITECTURES** | whether the **relative claim** is validated | **2** (Z1, Z2); Z4 excluded by value-of-information |

A single physical package failure establishes neither a characteristic life nor a scatter, so
"one test" in the Phase-0J-R sense was never going to mean one specimen. What this phase adds is
that it cannot mean one **condition** either, if the goal includes identifying the law.

## Sec. 15 — the statistical model

The calibration source reports a **2-parameter Weibull** per cell and an average slope of about
**β ≈ 11** across its twelve data points, with a range of roughly 6–20. **β is not assumed here.**
The design estimates it, because:

* it is needed to convert η to the **mean life** Syed's constants are regressed against;
* it is the dominant term in the precision of that conversion;
* an assumed β would silently import the calibration set's packaging into our package.

Standard large-sample MLE result used throughout: `SE(ln η) ≈ 1/(β√n)`, and for a ratio of two
cells `SE(ln ratio) = √2/(β√n)`.

## Precision achieved

Separation between the two laws' predicted life ratios, for the recommended
COLD_SHALLOW vs HOT_SHALLOW pair (D = 1.849):

| | n = 8 | **n = 16** | n = 32 |
|---|---|---|---|
| β = 6 (pessimistic) | 5.32σ | **6.19σ** | 6.82σ |
| β = 11 (Syed's average) | 6.68σ | **7.13σ** | 7.39σ |

**n = 16 per cell is the recommendation, and it is not arbitrary:**

* at the pessimistic β it already gives > 6σ, far beyond the 3σ that would settle the question;
* the **ceiling imposed by simulation uncertainty alone (8 %) is 7.7σ**, so beyond about 16 the
  precision stops improving — the limit becomes the model, not the sample;
* 16 is the cell size Syed's own dataset used (16/16 failures at several of his data points),
  so the resulting Weibull statistics are directly comparable to the calibration set;
* it leaves margin for early censoring and for specimens lost to non-solder failure modes.

**Total: 2 architectures × 2 conditions × 16 = 64 packages.**

## Censoring

Right-censoring is expected in the cold cell, whose predicted life is the longest. Treatment is
specified in advance rather than decided after the data arrive:

* the test runs to **either** 63 % failures in every cell **or** a pre-agreed cycle ceiling;
* survivors enter the Weibull fit as **right-censored** observations via maximum likelihood, not
  by exclusion, which would bias η upward;
* if a cell reaches the ceiling with fewer than **7 failures**, its η is reported with a profile
  likelihood interval rather than a point estimate, and that cell's contribution to the
  discrimination test is downweighted accordingly.

## Confidence

Report **two-sided 90 % confidence intervals** on η, β and the mean, by profile likelihood. The
discrimination test is then a comparison of the measured cold/hot life ratio against two
predicted ratios that differ by 85 %; with the intervals above, the two hypotheses are separated
by more than 6σ, so the test is decisive rather than suggestive.

## What the statistics cannot fix

The **8 % simulation uncertainty** on the predicted metric ratio is not reducible by specimens.
It comes from the material card, the mesh and the extraction volume, and it is the term that
caps the experiment at 7.7σ. It is quoted here so that no one proposes 64 specimens per cell in
the belief that precision keeps improving.
