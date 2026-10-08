# Phase-0E — TSV Current-Capability and Allocation Audit

## 1. The distinction Phase 0D-R failed to make

Phase 0D-R carried two candidate "per-via current limits", 33 mA and 4.8 mA, and reported
ARCH_B (LV-side TSV) as **INFEASIBLE** under the 4.8 mA reading. Both numbers were obtained by
dividing a June-2026 VIC count into a system current. Neither is a physical limit, and one of
them is arithmetically wrong.

Phase 0E separates three distinct quantities:

| symbol | meaning | status |
|---|---|---|
| `I_allocated_per_via` | the current the source's own provisioning rule puts on one via | **DERIVED_FROM_SOURCE** |
| `I_max_reliability` | the electromigration/lifetime limit J(T, t_life, geometry, liner) | **OPEN** |
| `n_req / n_alloc / n_avail` | required / actually assigned / geometrically available | now separate variables |

## 2. The allocation rule is stated verbatim in the source

June-2026, Sec. III-E:

> "Different nodes within a VR cell carry different currents; **the number of parallel VICs
> per connection is sized based on the connection current and per-via current limit**, with
> current assumed to be uniformly distributed across the allocated VICs."

and

> "Since RMS current directly governs **electromigration** and power loss in the interconnects
> and defines the current-carrying requirement and **long-term reliability** of each vertical
> link, it provides the appropriate basis for estimating VIC demand and footprint."

ECTC-2024 gives the rule in closed form (its eq. 2):

    N_Vpref = 2 I / (A_conn * J)          R_Veff = R / N_Vpref

The factor 2 is the source's own power-and-ground convention: *"both power and ground
distribution networks are considered in this work to estimate the net PPDN power loss."*

**Policy A (`n_alloc = n_req`) is therefore the SOURCE-BACKED policy**, not merely a modelling
convenience. It also explains something Phase 0D-R stated as if it were a law: `P_TSV` is
approximately linear in `I` **only because** `n_alloc` is provisioned proportional to `I`. Under
a geometric allocation policy that proportionality disappears.

## 3. Back-deriving J from two independent papers

### June-2026, Table III ("Optimized VIC Allocation")

First, the table's own area column validates the `n_available = footprint/pitch^2` model:

| level | N | pitch | N·pitch² | Area printed |
|---|---:|---:|---:|---:|
| BGA | 132 | 800 µm | 84.5 mm² | 85 mm² |
| PL1 TSV | 30 202 | 60 µm | 108.7 mm² | 110 mm² |
| PL2 TSV | 27 845 | 60 µm | 100.2 mm² | 100 mm² |
| PL3 TSV | 14 148 | 60 µm | 50.9 mm² | 50 mm² |

Then, with I_out = 1000 A and I_in,rms = I_out·sqrt(V_out/V_in) = 144.3 A (their eq. 5):

| tier | N_alloc | A_conn | implied J |
|---|---:|---:|---:|
| chiplet pads (Cu) | 200 000 | 100 µm² | **1.000e8 A/m²** |
| PL1 TSVs (Cu) | 30 202 | 707 µm² | **9.366e7 A/m²** |
| BGAs (solder) | 132 | 125 663 µm² | 1.740e7 A/m² |

The two independent copper tiers agree to **6.8 %**.

### ECTC-2024, Table I (N_Vpref recovered as R/R_Veff)

| tier | N_Vpref | A_conn | implied J |
|---|---:|---:|---:|
| advance pad (Cu) | 50 000 | 100 µm² | **4.000e8 A/m²** |
| TSV (Cu) | 5 811 | 20 µm² | **4.027e8 A/m²** |
| C4 (solder) | 150 | 7 854 µm² | 3.972e7 A/m² |

The two independent copper tiers agree to **0.7 %**.

### The envelope

| material | conservative | aggressive | ratio |
|---|---:|---:|---:|
| copper | **1.0e8 A/m²** (June-2026) | **4.0e8 A/m²** (ECTC-2024) | 4x |
| solder | 1.74e7 A/m² (June BGA) | 3.97e7 A/m² (ECTC C4) | 2.3x |

Each paper is internally self-consistent across independent tiers; the two differ by 4x for
copper. **That difference is the envelope, not an error.** For context, 1e8 A/m² = 1e4 A/cm²
is roughly two orders of magnitude below the classic ~1 MA/cm² copper electromigration design
limit, i.e. both readings are conservative operating densities rather than stress-test values.

One inconsistency is reported rather than smoothed over: the ECTC µ-bump row (solder, 707 µm²,
N = 15 333) implies 1.845e8 A/m², which fits neither the copper nor the solder value. No
reading of the load current reconciles it.

## 4. Where Phase 0D-R's 33 mA came from

    1000 A / 30 202 TSVs = 33.1 mA

This **omits the factor 2** in `N = 2I/(A·J)` — i.e. it treats the whole allocated field as
carrying supply current, when half of it is ground. The correct per-via current for that same
allocation is `2 x 1000 / 30 202 = 66.2 mA`, and the J-based value is `J·A = 70.7 mA`.

The 4.8 mA figure came from dividing the *input RMS* current by the *same* VIC count — mixing
the current of one rail with the allocation of another. It has no physical referent.

## 5. Per-via current limit for the Phase-0B/0C/0D vehicle

The vehicle uses the June TSV geometry (d = 30 µm, A = 707 µm²):

| basis | J | I_max per via |
|---|---:|---:|
| June-2026 (conservative) | 1.0e8 A/m² | **70.7 mA** |
| ECTC-2024 (aggressive) | 4.0e8 A/m² | **282.8 mA** |
| Phase-0D-R "33 mA" | — | 33 mA (factor-2 error) |
| Phase-0D-R "4.8 mA" | — | 4.8 mA (rail/allocation mismatch) |

**Both source-backed values are above both Phase-0D-R candidates.**

## 6. Consequence for ARCH_B

ARCH_B puts the full 60 A per-VR output rail through the substrate. In a 4.9 mm tile footprint
at 60 µm pitch, `n_available = 6 669`.

| per-via limit | n_required | n_available | verdict |
|---|---:|---:|---|
| 282.8 mA (ECTC J) | 213 | 6 669 | **FEASIBLE** (3.2 % utilisation) |
| **70.7 mA (June J)** | **849** | **6 669** | **FEASIBLE** (12.7 % utilisation) |
| 33 mA (0D-R, factor-2 error) | 1 819 | 6 669 | feasible (27 %) |
| 4.8 mA (0D-R, unsourced) | 12 501 | 6 669 | infeasible |

**ARCH_B is feasible under every source-backed current density.** The Phase-0D-R infeasibility
verdict rested entirely on the one candidate limit that has no source.

## 7. What remains OPEN

`I_max_reliability` is **not** closed. No primary electromigration study giving a
current-density limit together with its temperature, lifetime, geometry and liner conditions
could be retrieved here: `WebSearch` is disabled by organisation policy, the arXiv API returns
one TSV-EM paper with no quantitative design limit, and the Semantic Scholar API returned
HTTP 500 and 429. June-2026 ties its provisioning to electromigration and long-term
reliability explicitly, which supports reading `J_provision` as reliability-motivated, but the
paper does not print the limit.

**Therefore Phase 0E reports feasibility as a map over J and makes no claim of physical
infeasibility for any architecture.** The exact threshold, computed rather than estimated
(`archB_feasibility_map.csv`):

| tile side | A_HVR | n_available | J at which ARCH_B becomes infeasible | margin vs June J | margin vs ECTC J |
|---|---:|---:|---:|---:|---:|
| 3.873 mm | 15.00 mm² | 4 166 | 2.04e7 A/m² | 4.9x | 19.6x |
| 5.073 mm | 25.74 mm² | 7 148 | 1.19e7 A/m² | 8.4x | 33.7x |
| 5.858 mm | 34.32 mm² | 9 532 | 8.90e6 A/m² | 11.2x | 44.9x |

The permitted statement is: *"ARCH_B is feasible for every source-backed current density; it
would become infeasible only below ~1e7 A/m², which is 5-11x below the most conservative
value either primary source implies."*

## 8. The footprint-feasibility coupling asked for in Sec. 6

A larger tile holds more via sites, so footprint and feasibility are coupled in principle:

| A_HVR | n_available | n_required (June J) | utilisation |
|---:|---:|---:|---:|
| 15.00 mm² | 4 166 | 849 | 0.204 |
| 25.74 mm² | 7 148 | 849 | 0.119 |
| 34.32 mm² | 9 532 | 849 | 0.089 |

The coupling is real but **not active at this operating point**: utilisation never exceeds
20 %, so the via field is nowhere near saturated and enlarging the tile buys margin that is
not needed. It would only become a design driver at a current density roughly 5x lower than
any sourced value, or at the 1 kW reference scale. **No additional DVPD electro-mechanical
tension arises from this route at 240 W.**
