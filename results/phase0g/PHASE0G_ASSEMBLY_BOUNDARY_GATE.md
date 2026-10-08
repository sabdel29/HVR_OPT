# Phase 0G — Assembly-Boundary, Crossover-Robustness and Mechanical-Criterion Closure

**Verdict: NO ACTIVE MECHANICAL CONSTRAINT — RESPONSE COUPLING ONLY**
**Global ETM optimizer: NOT recommended, NOT built.**

---

## 1. What this phase was asked to settle

Phase 0F ended with three load-bearing statements that were flagged as unproven:

1. the BC-B foundation stiffness was **PROVISIONAL**, and the reported thickness-sign
   reversal rested entirely on it;
2. the ARCH_B electrical minimum near `h ≈ 1.0 mm` was **extremely shallow** and had not been
   tested against uncertainty;
3. no source-backed mechanical criterion existed, so gate **G2 remained NOT TESTED**.

Phase 0G was instructed not to assume any of that wording was proven. It is not. **All three
statements are withdrawn or reclassified**, two of them because they were artifacts.

## 2. Headline findings

| # | finding | consequence |
|---|---|---|
| 1 | **DEFECT #30** — per-regulator and system-wide loss terms were summed together, understating every vertical tier by `n_vr` (4× at 240 W, **49× at 1 kW**) | the ARCH_B interior optimum **does not exist**; corrected ARCH_B is monotone with its optimum on the thin boundary in **9 corners of 9** |
| 2 | **BC-B is a clamp, not a foundation** — it restrains all three DOF and cannot recover its own free limit (0.739 µm vs 8.287 µm on the identical mesh) | the Phase-0F **assembly-state reversal is withdrawn** |
| 3 | **No support-stiffness crossover `k*` exists** — `S_h > 0` at all 12 stiffnesses over seven decades | the reversal is **kinematic, not elastic**; it cannot be tuned away |
| 4 | **Every explicit assembly gives the free-package sign** — `S_h` = −0.039 to −0.886 across five boards | thicker is better, mounted or free |
| 5 | **The footprint sign flips** — positive in the free (+0.203) and clamped (+0.058) models, **negative in all five explicit boards** (−0.166 to −0.290) | the **footprint opposition is withdrawn** for mounted assemblies |
| 6 | **Electrical and mechanical AGREE on footprint when mounted** — electrical prefers M = 49 by **6.633 W**; so does every mounted mechanical model | there is **no trade-off to co-optimize** on the strongest DVPD-specific lever |
| 7 | **No admissible mechanical criterion exists** | **G2 remains NOT TESTED**; nothing can bind |

## 3. Why DEFECT #30 escaped three phases

This is worth recording because the near-miss is instructive.

The Phase-0F minimum was **+14.5 mW on a 125 W system**, and the obvious explanation was
convergence: the ET loop converged `T_max` to 0.05 K, and at `dP_conv/dT = 148 mW/K` that
tolerance alone admits ~7.4 mW — half the effect. Phase 0G re-ran the sweep at **25× tighter
tolerance** and 5× thickness resolution specifically to break the claim.

**The minimum survived.** It was not a convergence artifact.

Only decomposing the curve into `P_total,B(h) = g(h) + P_TSV,B(h)` and checking the units of
each term exposed the real cause. `vertical_tier()` returns a **per-regulator** loss;
`rdl_network_solve()` returns a **system-wide** loss; the two were added. The signature is
unambiguous — the ratio of corrected to uncorrected `P_TSV` is **49.004 to 49.055** at all
nine thicknesses, and an independent hand check (89.7768 mW/VR × 49 = 4.399 W) agrees.

Testing the obvious hypothesis and having it pass is what made the defect *look* excluded.
The tight-tolerance sweep is retained in `crossover_hires_ARCH_B_tight.csv` as the control
that proves the distinction.

## 3b. A second defect: the guard built to catch DEFECT #29 could not fail

Phase 0F's response to DEFECT #29 was a **semantic ledger** — regex patterns for withdrawn
claims, each exonerated by "historical" context nearby. Phase 0G added five entries to it for
its own withdrawals and then, before trusting them, ran a **negative test**: three unqualified
re-assertions of withdrawn claims were injected into the report to confirm the ledger caught
them.

**It did not.** The build stayed green.

The cause was the exonerating vocabulary. It accepted `"was "`, `"were "`, `"became"`,
`"becomes"` and `"earlier"` within a **±800-character** window. In English technical prose at
least one of those appears in any such window, so every entry in the ledger — including all
sixteen Phase-0F entries — had been passing **unconditionally** since it was written. This is
**DEFECT #31**.

Five genuinely stale statements were standing behind that green build, in the Executive
Summary, the uncertainty ladder and Next Steps: *"HVR footprint is a real ETM opposition"*,
*"the footprint opposition survives a physical material model"*, the claim ladder still
listing footprint opposition as PROVEN, and two Next Steps paragraphs treating "whether a
mechanical constraint binds" as open after Phase 0F had addressed it.

The repair has four parts: the vocabulary is restricted to markers that can only be present
deliberately; the window is the containing **paragraph or table cell** rather than a page of
prose; scoring runs on the **Markdown**, where headings are unambiguous; and a claim is
exonerated by its enclosing **heading chain**, so a subsection inside a superseded phase
inherits that framing while the same sentence in a current section does not.

It is verified in **both** directions — the real report passes 49 checks, and five injected
re-assertions are each caught with exactly one unqualified hit.

> **A guard that has never been observed to fail has not been tested.** Every assertion added
> from Phase 0G onward is negative-tested before it is trusted.

## 4. Why BC-B had to be withdrawn

`BC_B` emits `*BOUNDARY {n},1,3` across the underside plane — **all three degrees of
freedom**. A BGA field does not: solder balls are compliant in shear, so a mounted package
keeps in-plane freedom relative to its board.

Two tests settle it, and neither depends on a material choice:

- **The free-limit test.** At `k_z = 0.001 N/mm³` the foundation is mechanically absent, so
  the result must approach the free package. It gives **0.739 µm** where the free package on
  the identical mesh gives **8.287 µm** — 11.2× apart. A foundation with no stiffness is
  still suppressing 91 % of the warpage. That residual is the in-plane clamp.
- **The `k*` search.** `S_h > 0` at every stiffness across seven decades. There is no root.

The explicit BGA + PCB model passes the corresponding limit test: driving the board towards
absence returns **13.20 µm against the free package's 11.17 µm** (+18.1 %, the residual being
the BGA layer's own 3.93 GPa / 20.5 ppm/K contribution), and it responds correctly to board
CTE as well as stiffness — a stiff CTE-matched board *flattens* the package to 2.67 µm.

A real board **amplifies** warpage (to 29.2 µm, 2.6× the free package) because silicon at
2.6 ppm/K is bonded to FR-4 at ~18 ppm/K. The compact model **suppresses** it to 0.37 µm.
These are opposite regimes, not a quantitative disagreement.

## 5. The finding that changes the paper's central claim

Footprint opposition was this project's strongest DVPD-specific claim: that electrical
performance wants more distributed regulation and mechanics wants less.

| assembly model | S_A | direction |
|---|---|---|
| free package | +0.2033 | larger footprint WORSE |
| compact BC-B clamp | +0.0583 | larger footprint WORSE |
| board: compliant | −0.1660 | larger footprint BETTER |
| board: FR-4 1.6 mm | −0.2579 | larger footprint BETTER |
| board: FR-4 2.4 mm | −0.2810 | larger footprint BETTER |
| board: FR-4 3.2 mm | −0.2900 | larger footprint BETTER |
| board: metal-backed | −0.2236 | larger footprint BETTER |

Electrically the larger footprint wins by **6.633 W** (RDL loss halves, 0.983 → 0.489 W).
**In every mounted model the two disciplines agree.**

This is independently corroborated by the reference system itself. June-2026 (Sec. I) states:

> "Partitioning power conversion into multiple smaller VRs reduces peak stress concentration
> and prevents the formation of a single mechanically stiff region within the substrate. Each
> VR produces localized deformation rather than global package deflection. With symmetric VR
> placement localized mechanical effects can partially offset one another, reducing overall
> warpage sensitivity."

The explicit-board model **reproduces the direction the source asserts**; the free and clamped
models contradict it. The corroboration is of direction only — June attaches no number.

## 6. What survives

One genuine ETM opposition remains: **substrate thickness**. Electrically thinner is better;
mechanically thicker is better. It is present identically in the free package, so it is the
conventional tension, not an assembly-state effect — and it is remarkably robust:

| perturbation | range tested | sign flips |
|---|---|---|
| assembly model | free, clamp, 5 boards | 0 of 7 (excluding the invalid clamp) |
| stress-free reference | 25 / 150 / 175 °C | 0 of 6 |
| thermal boundary | 4× `h_top` band; substrate-side topology | 0 of 10 |
| **total** | **20 combinations** | **0** |

The mounted normalized response is close to invariant: `S_h` = −0.4419 / −0.4421 / −0.4422
across a 4× thermal-boundary range (**0.07 %** spread) and −0.4421 / −0.4397 / −0.4400 across
a 150 K reference-temperature span (**0.5 %** spread), while magnitudes move by 45–64 %. The
normalized thickness response is a **structural property of the assembly**, not a thermal one.

## 7. Why this is not a constraint

`mechanical_criterion_audit.md` searched the full corpus. June-2026 names the failure
mechanisms it cares about — global package warpage, delamination, RDL shear — and attaches
**no number** to any of them. No other source supplies one. External standards were
unretrievable in this environment and, on inspection of what they govern, would be
**inadmissible anyway**: package-outline coplanarity constrains the ball plane of a component
*as supplied*, at a defined measurement temperature, for solderability at reflow. This project
computes incremental operational warpage of a *mounted* assembly at steady-state operating
temperature. Package state, temperature, measurement definition and failure mechanism all
differ.

Nor would a conventional limit discriminate. Warpage stays **below 40 µm** across every
assembly, reference state and thermal boundary examined — one to two orders of magnitude
below the hundreds-of-micrometres band conventional for this package class. A criterion that
every design in the space satisfies is not active.

**G2 remains NOT TESTED** — not failed. It has never been given a threshold to be tested
against.

## 8. Optimizer gate

Both conditions were required.

| condition | met | why |
|---|---|---|
| 1 — the assembly-state response survives calibrated board and thermal-boundary uncertainty | **PARTIAL** | the thickness *response* survives with 0 sign flips in 20 combinations, but the assembly-state *reversal* the condition was posed about does not survive — it does not exist |
| 2 — a criterion or user-set ε can actually alter the feasible design set | **NO** | no criterion exists, and the entire computed warpage range sits 1–2 orders of magnitude below any conventional limit |

**The global ETM optimizer is NOT recommended and was NOT built.** Optimizing over an
unconstrained mechanical objective would produce a weighted-sum artifact whose answer is set
by the weights rather than by physics.

## 9. Next gate — 0H, criterion acquisition

Every remaining ETM question is blocked on the same single item. To unblock:

1. an **operational-state warpage or RDL-shear allowable for this stack**, from a measurement
   or qualification specification — not a literature value from a different package state;
2. **GaN and MLCC layer heights**, to close the geometry bound that currently excludes the
   entire Phase-0B–0E swept range;
3. **board laminate structure**, to turn the 9.7–29.2 µm engineering envelope into a
   prediction.

**Explicitly not next: the global ETM optimizer.**

## 10. Deliverables

| # | artifact | section |
|---|---|---|
| 1 | `electrical_crossover_uncertainty.md` | 2, 4 |
| 2 | `board_foundation_calibration.md` | 5, 6, 7 |
| 3 | `thermal_boundary_closure.md` | 8, 9, 10 |
| 4 | `m1_reference_state_audit.md` | 11 |
| 5 | `mechanical_criterion_audit.md` | 12 |
| 6 | `footprint_placement_recheck.md` | 14, 15 |
| 7 | `mechanical_epsilon_corrected.csv` | 13 |
| 8 | `../CURRENT_SCIENTIFIC_STATUS.yaml` | 16, 17 |
| 9 | `explicit_board_crosscheck.csv`, `footprint_board_envelope.csv` | 7, 14 |
| 10 | `support_stiffness_sweep.csv`, `restraint_kinematics.csv` | 6 |
| 11 | `cooling_topology_comparison.csv`, `placement_corrected_1kw.csv` | 10, 15 |
| 12 | `PHASE0G_ASSEMBLY_BOUNDARY_GATE.md` (this document) | 3b, 18, 19 |

Figures: `FIG_0G_A`–`FIG_0G_G` (7).

### Known residuals

- **Board magnitudes are not validated.** The 9.7–29.2 µm range rests on an engineering board
  envelope. Only signs and orderings are claimed.
- **Warpage is incremental operational**, 25 °C reference. Real assemblies carry additional
  pre-stress; the M1 bound puts that at up to +54 %.
- **Interface peel remains excluded** (Phase 0C, 19–20 % mesh change against a <10 % target).
  Shear converged but has no allowable.
- **Icepak remains unusable** — the 5000 K clamped solution was discarded and is never used.
- **Substrate-side-only cooling is thermally infeasible at 1 kW** (floors at 90.96 °C,
  reaching 110.4 °C at `h = 2.00 mm`). Recorded as a separate finding.
