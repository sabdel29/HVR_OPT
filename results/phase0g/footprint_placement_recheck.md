# Phase 0G Sec. 14/15 — Footprint opposition under the calibrated assembly, and the
# remaining placement freedom

## 1. Why the footprint lever had to be re-tested

Footprint opposition is the strongest DVPD-specific claim this project has made: that
electrical performance wants **more, larger-area distributed regulation** while mechanics
wants **less**, so that the two disciplines pull in opposite directions and a co-design
optimum exists between them. Sec. 7 showed the compact BC-B foundation is not a valid model
of a mounted package. Every previous footprint conclusion was drawn under BC-A or BC-B, so
the lever had to be re-evaluated under the explicit assembly.

The lever compares two realizable 1 kW designs at fixed current density `j = 3.0 A/mm²` and
fixed `h_sub = 1.50 mm`:

| | M = 36 | M = 49 |
|---|---|---|
| per-VR area (mm²) | 7.200 | 6.720 |
| **total HVR footprint (mm²)** | **259.20** | **329.28** |
| tile side (mm) | 2.6833 | 2.5923 |

Total footprint rises 27.0 %. Both count and total area increase together, which is how the
DVPD footprint lever is physically posed — at fixed `j` a finer partition buys more total
converter area. The comparison is not a pure granularity change, and is not reported as one.

## 2. The electrical direction, on corrected numbers

Recomputed with DEFECT #30 fixed:

| | M = 36 | M = 49 | Δ |
|---|---|---|---|
| P_total (W) | 131.02449 | **124.39163** | **−6.633 W** |
| P_RDL (W) | 0.98347 | 0.48867 | −0.495 W |
| P_TSV (W) | 4.39809 | 4.38588 | −0.012 W |
| T_max (°C) | 84.413 | 83.997 | −0.416 K |

**Electrically the larger, finer-partitioned footprint wins by 6.633 W** — a 5.3 % system
loss reduction, driven by the lateral RDL loss halving as delivery distances shorten. This is
not marginal and not within any numerical floor in this project.

## 3. The mechanical direction — the sign is assembly-state dependent

`S_A = [W(329.3 mm²) − W(259.2 mm²)] / W(259.2 mm²)`, at `h_sub = 1.50 mm`:

| assembly model | W(259.2) µm | W(329.3) µm | S_A | direction |
|---|---|---|---|---|
| BC_A, free package | 2.5285 | 3.0425 | **+0.2033** | larger footprint WORSE |
| BC_B, compact clamp | 0.6697 | 0.7088 | **+0.0583** | larger footprint WORSE |
| BC_BOARD, compliant | 15.3830 | 12.8297 | **−0.1660** | larger footprint BETTER |
| BC_BOARD, FR-4 1.6 mm | 19.2057 | 14.2530 | **−0.2579** | larger footprint BETTER |
| BC_BOARD, FR-4 2.4 mm | 16.5359 | 11.8887 | **−0.2810** | larger footprint BETTER |
| BC_BOARD, FR-4 3.2 mm | 13.4509 | 9.5501 | **−0.2900** | larger footprint BETTER |
| BC_BOARD, metal-backed | 10.8179 | 8.3987 | **−0.2236** | larger footprint BETTER |

**The sign flips.** It is positive in both idealized models and negative in **all five**
explicit assemblies, spanning the whole calibrated board envelope from compliant to
metal-backed. The mounted result is not marginal either: −17 % to −29 %.

## 4. The reference system asserts the mounted direction

June-2026 states the mechanism explicitly (Sec. I):

> "Partitioning power conversion into multiple smaller VRs reduces peak stress concentration
> and prevents the formation of a single mechanically stiff region within the substrate. Each
> VR produces localized deformation rather than global package deflection. With symmetric VR
> placement localized mechanical effects can partially offset one another, reducing overall
> warpage sensitivity."

The explicit-board model **reproduces the direction the reference paper asserts**. The free
and clamped models **contradict** it. This is independent corroboration — from the source
system, not from this project's own machinery — that the explicit assembly is the physically
relevant configuration and that the earlier footprint opposition was a modelling artifact.

The corroboration is of **direction only**. June-2026 attaches no number to the claim, so
nothing here validates the computed magnitudes.

## 5. Consequence: the footprint opposition does not exist in a mounted assembly

| lever | electrical preference | mechanical preference (mounted) | relationship |
|---|---|---|---|
| **footprint / distribution** | more (M = 49), by 6.633 W | more (M = 49), by 17–29 % less warpage | **AGREEMENT** |
| **substrate thickness** | thinner (ARCH_B monotonic to 0.80 mm) | thicker (S_h < 0 in all 5 boards) | **OPPOSITION** |

For a mounted assembly the two disciplines **agree** on the footprint lever. There is no
trade-off to co-optimize there: the electrically preferred design is also the mechanically
preferred one. The footprint opposition reported in Phases 0C–0F is **WITHDRAWN** as an
artifact of unmounted and clamped boundary conditions.

One genuine ETM opposition survives — **substrate thickness** — and it is the conventional
one, present identically in the free package. It is not assembly-state dependent, and Sec. 12
shows there is no criterion that would make it binding.

## 6. Sec. 15 — placement freedom is small but NOT eliminated

At the largest footprint the lattice is nearly saturated. Compaction headroom, from the
Phase-0F placement study at `h_sub = 1.50 mm`:

| design | total HVR (mm²) | compaction headroom |
|---|---|---|
| M = 25, j = 4.0 | 187.50 | 30.43 % |
| M = 36, j = 3.0 | 259.20 | 14.78 % |
| M = 49, j = 3.5 | 274.89 | 9.37 % |
| **M = 49, j = 3.0** | **329.28** | **1.14 %** |

Placement remains a design variable with a real electrical consequence. The three lattices at
M = 49, j = 3.5, **recomputed with DEFECT #30 fixed**, differ by **8.735 W**:

| lattice | P_total (W) | P_RDL (W) | P_TSV (W) | T_max (°C) | die warpage (µm) |
|---|---|---|---|---|---|
| **uniform** | **125.19021** | 0.64193 | 0.09943 | 84.176 | **2.6192** |
| compact | 129.83099 | 4.83603 | 0.09975 | 86.342 | 2.9017 |
| asymmetric | 133.92490 | 8.73503 | 0.09990 | 86.617 | 3.0008 |

**Placement does NOT cease to be a design variable.** 1.14 % headroom at the most aggressive
footprint is small, but it is not zero, and legal placement freedom is not mathematically
eliminated: the lattice family, the assignment of regulators to sites, and the residual
compaction all remain free. The correct statement is that **placement freedom contracts as
the footprint grows**, and that at `j = 3.0, M = 49` it is nearly exhausted — not that it
disappears.

The placement penalty is also strongly one-sided: the uniform lattice is best in **both**
disciplines (lowest loss *and* lowest warpage), so placement is another lever on which
electrical and mechanical preferences **agree** rather than compete.

### The placement numbers were recomputed, not adjusted

The Phase-0F placement table inherited DEFECT #30. The obvious shortcut — adding the missing
`P_TSV` term by hand, since the 49× correction is a near-identical additive shift across the
three lattices — would have given the wrong answer. The correction re-enters the ET fixed
point, so the actual shift is **+0.169 W** for the uniform lattice, not the +0.097 W a purely
additive estimate predicts. The table above is a full recomputation.

The **ordering is unchanged** and the spread moves from 8.728 W to 8.735 W. So the conclusion
carried forward from Phase 0F survives — but it survives because it was re-derived, not
because the shift was assumed to cancel.
