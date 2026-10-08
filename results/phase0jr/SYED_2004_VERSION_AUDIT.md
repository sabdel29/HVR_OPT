# Phase 0J-R Sec. 1 — Syed 2004: original ECTC versus author-corrected version

## The correction exists, is explicit, and is the author's own

Both supplied PDFs are read. The author-corrected copy carries a footer note repeated on
**every page** of the paper body (pp. 1–10 of the supplied PDF), verbatim:

> "This paper was originally published in ECTC 2004 conference proceedings (pp 737 – 746),
> however, due to errors in data processing the constants for life prediction models published
> in the original paper were not accurate. These constants, along with associated figures, have
> been corrected here."

**Provenance is confirmed, not assumed.** The corrected file is the same paper — same title,
same author, same Amkor affiliation and address, same Tables 1/2a/2b, same equation numbering —
with a page-level correction notice and an appended ECTC presentation deck (pp. 11–34) that the
IEEE original does not contain.

## The root cause, from the author's own slides

The appended deck states the mechanism of the error (p. 22 of the supplied PDF):

> "Life prediction model parameters in the paper are based on **1st cycle values due to post
> processing error** and are not correct"

in the context of a stabilisation slide reporting:

> "SnPb solder joints show cyclic stability after 1st cycle — **SnAgCu solder joints show
> stability after 2nd cycle** — **20 to 30% reduction after 1st cycle**"

**This is the single most important fact in this audit for our purposes.** The original constants
were regressed against **first-cycle** creep values, which are 20–30 % larger than the
stabilised values. Since `N_f = (C·ε_acc)^−1`, fitting a too-large ε to a fixed measured N_f
forces a too-small C. Correcting to stabilised values must therefore **raise** C by roughly
1/(0.70–0.80) = **1.25–1.43×**. Every corrected constant below moves in exactly that direction
and by very nearly that factor — an internal consistency check the audit did not have to assume.

## Constant-by-constant comparison

### Double power law constitutive model (Wiese, Table 1 Eq. 1)

| quantity | equation | **ORIGINAL (IEEE)** | **CORRECTED (author)** | ratio |
|---|---|---|---|---|
| partitioned, mechanism I | Eq. 13 | `C_I = 0.013` | **`C_I = 0.106`** | 8.15× |
| partitioned, mechanism II | Eq. 13 | `C_II = 0.036` | **`C_II = 0.045`** | **1.25×** |
| coefficient of determination | — | 0.9997 | 0.997 | — |
| **total accumulated creep strain** | **Eq. 14** | **`C' = 0.0358`** | **`C' = 0.0468`** | **1.31×** |
| creep strain energy density | Eq. 15 | `W' = 0.0012` | **`W' = 0.0015`** | **1.25×** |
| fitted strain exponent (Fig. 8) | — | −1.0012 | **−0.9607** | — |
| fitted energy exponent (Fig. 10) | — | −0.91537 | **−0.9229** | — |

### Hyperbolic sine constitutive model (Schubert, Table 1 Eq. 2)

| quantity | equation | **ORIGINAL** | **CORRECTED** | ratio |
|---|---|---|---|---|
| accumulated creep strain | Eq. 16 | `0.0405` | **`0.0513`** | 1.27× |
| creep energy density | Eq. 17 | `0.0014` | **`0.0019`** | 1.36× |

### Affected figures

Figures 5, 6, 7, 8, 9, 10 and 11 all carry the correction notice and differ between versions.
Figure 6 is retitled: the original's *"Comparison of relative contribution of two mechanisms"*
becomes *"Comparison of relative contribution of low stress mechanism"*.

### Affected predicted life

Because every model is inverse-linear in its metric, the change in predicted life is exactly the
inverse ratio of the constant, for any given metric value:

| model | life change, corrected vs original |
|---|---|
| total accumulated creep strain (Eq. 14) | **× 0.765** — 23.5 % SHORTER |
| creep energy density (Eq. 15) | × 0.80 — 20 % shorter |
| hyperbolic-sine strain (Eq. 16) | × 0.79 |
| hyperbolic-sine energy (Eq. 17) | × 0.74 |

Had the original constants been used, every predicted life in this project would have been
**over-predicted by about 31 %** on the total-creep-strain model.

## Which version is authoritative for THIS project, and why it is not merely "the later one"

**The corrected version, and for a reason specific to us.**

Phase 0I-R established that this project extracts every metric at the **stabilised cycle**
(cycle 4 of 4, converged to 0.48–2.00 %). The original Syed constants were fitted to
**first-cycle** values. Feeding a stabilised metric into a first-cycle-calibrated constant would
**compound** the very error the author corrected — our ε is already the smaller, stabilised
quantity, so pairing it with the smaller, first-cycle-fitted C under-predicts damage twice over.

The corrected constants are the ones calibrated against **stabilised** creep response, which is
the same convention our M1/M2/M3/M4/M5 use. The version match is therefore a **methodological
requirement**, not a preference for the more recent file.

Syed's own stabilisation observation — SnAgCu stabilises after the **2nd** cycle — also
independently validates the Phase-0I choice to cycle to 4 and report cycle 4.

## What is NOT corrected, and remains as published

The experimental dataset (Tables 2a, 2b), the test conditions TC1/TC2/TC3, the constitutive
models (Table 1), the 25 µm averaging methodology, and the Table 3 stack-package validation are
identical between versions. **The correction is confined to the regressed life-model constants
and the figures that display them.**

## Guard

A build guard now fails if any superseded Syed constant (`0.0358`, `0.0012`, `0.0405`,
`0.0014`, or the pair `0.013`/`0.036`) appears in a current-facing section without a
superseded/original/withdrawn marker.
