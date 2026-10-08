---
title: "Electrothermal--Mechanical Co-Design of Distributed Vertical Power Delivery: Model Development, Falsification Gates, and Coupled Architecture Results"
author: "HVR\\_Journal\\_System\\_Level / ETM-DVPD --- HiPerCAS Lab, University of Illinois Chicago"
date: "2026-09-05"
geometry: margin=2.1cm
fontsize: 10pt
colorlinks: true
linkcolor: NavyBlue
numbersections: true
---

\newpage

# Provenance and tool versions

| Item | Value |
|:--|:--|
| Repository root | `/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT` |
| Converter-model repo commit | `ed56ae6` (`Scalable_Integrated_VR`) |
| Report date | 2026-09-05 |
| Structural + thermal FE |  --- C3D8I, direct SPOOLES |
| Independent FE cross-check | MOOSE `heat_transfer-opt`, build 09515f92aa |
| Full-wave EM available | PALACE (built, functional) |
| Commercial EM/thermal | ANSYS AEDT v261 installed; **licence unavailable** (S16.7) |
| Mesh generation | gmsh 4.15.2 |
| Python | 3.12.14 |
| Document build | pandoc + xelatex |

**Reading guide.** Every table below is generated programmatically from the source artifact
named beneath it; no numerical result was retyped. **Section 7 (Phase 0D-R) supersedes
Section 6 (Phase 0D) wherever they disagree**, and each disagreement is stated explicitly.

\newpage

# Executive Summary
**Original hypothesis.** Distributed vertical power delivery (DVPD) is normally optimised
on electrical and thermal grounds alone. This project asked whether package
thermo-mechanics --- warpage and stress --- is a *synthesis* constraint that changes which
DVPD architecture one would choose, rather than a downstream signoff check. If so, the
contribution would be an electro-thermo-mechanical (ETM) co-synthesis framework; if not,
the work reduces to thermo-mechanical placement, which STAMP-2.5D and ATMPlace already do.

**Method.** Five sequential falsification gates, each designed so that a negative result
would stop the project rather than be absorbed. No gate was allowed to pass on a metric
that failed mesh convergence, and no mechanical allowable was ever chosen after seeing
results.

**What survived.**

* *Mechanics responds strongly to architecture.* Die warpage spans 1.8--15.6 um across the
  frozen 20-case DOE --- a factor of 8.5 --- at fixed load and fixed total regulator
  footprint and heat (Phase 0C).
* *Substrate thickness is a genuine three-domain variable and it is win/win/win.* Going
  200 -> 500 um lowers warpage 56.5 %, temperature 2.75 K **and** total electrical loss
  1.0 %. This survived every correction, including the architecture-aware rail assignment.
* *HVR footprint is a real ETM opposition.* Larger footprint lowers converter loss, RDL
  spreading loss and temperature while raising warpage: -54 % loss for +84 % warpage.
* *The model chain is numerically sound.* Energy balance closes to +-0.000 %, warpage is
  mesh-converged to 0.50 %, and the electrical sheet model agrees with an independent
  finite-element solver (MOOSE) to 0.33--0.45 %.

**What failed.**

* *Regulator count is mechanically inert* --- 0.02 % (4->6) and -4.07 % (4->8) --- killing
  the variable the original novelty argument leaned on (Phase 0B, confirmed 0C).
* *Tile aspect ratio is inert* (-1.76 %), and on this square vehicle the two aspect cases
  are provably identical by symmetry.
* *Interface peel never converged* and was removed from all decision logic.
* *The Phase-0D claim that "ET is blind to placement" is withdrawn.* It was an artifact of
  a lumped RDL model that was wrong by ~65x. Corrected, the electrical spread across
  placements is **189 %**, not 1.08 %.
* *No architecture-dependent thickness tradeoff exists.* Even when the 1 V rail is forced
  through the substrate (ARCH_B), the thickness penalty (34 mW) stays an order of magnitude
  below the thermal benefit.

**Current strongest novelty.** Not "mechanics changes the optimum" --- it does not, and with
a pure added objective it structurally cannot. The defensible claim is narrower: *HVR
footprint is simultaneously an electrical design variable (it sets the per-layer area budget
and hence switch sizing) and a mechanical one (it sets the CTE-mismatched inclusion volume),
and the two point in opposite directions.* Chiplet placers cannot express this because
chiplet area and power are fixed inputs, whereas HVR cell area and dissipation are outputs
of converter sizing.

**Current limitations.** The exchange rate between watts and microns is unsourced, so no
selection rule can be applied; the RDL metal stack is an assumption and now dominates the
electrical answer; all mechanical results are free-warpage (BC-A); and no ANSYS
cross-validation exists because the licence server is down.

**Exact next work.** Source the RDL metal stack and the per-via current limit, run targeted
PALACE and MOOSE validation, and only then consider a synthesis framework. Building the
optimiser now would encode an arbitrary metal stack and an arbitrary exchange rate into the
answer.

![**Figure 1.** What the architecture-aware correction changed. Four of five headline quantities moved by an order of magnitude; only the thickness benefit is unchanged. *(Phase 0D-R; data: `results/phase0dr/FIG_H_phase0d_vs_0dr.png`)*](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0dr/FIG_H_phase0d_vs_0dr.png){width=92%}
\newpage

# Research Motivation

AI accelerators draw kilowatts per package from a 48 V backplane at sub-1 V. Conventional
lateral delivery places regulators at the board or package edge, paying twice: resistive
IR drop along the path, and path inductance that adds an $L\,di/dt$ transient droop.
**Vertical power delivery** puts compact regulators directly beneath or inside the package.
A plain buck cannot do 48 V -> 1 V at a practical duty cycle, so the converter of interest
is a **hybrid VR (HVR)**: a switched-capacitor stage to an intermediate rail followed by a
multiphase buck.

The system-level design problem is a genuine trade: more regulators shorten the delivery
path but shrink the area available to each, which worsens converter efficiency. Existing
DVPD frameworks resolve that trade on electrical and thermal grounds.

**Why mechanics was introduced.** Regulator distribution changes not only path length and
heat generation but also the spatial distribution of stiffness and CTE mismatch, hence
warpage and interconnect stress. If the electrically optimal architecture were mechanically
infeasible --- or merely mechanically much worse at little electrical cost --- then
mechanics would belong inside synthesis rather than after it.

**The novelty question.** Thermo-mechanical-aware *placement* is not new. STAMP-2.5D
performs FEA-in-the-loop chiplet placement against von Mises stress; ATMPlace is an
analytical placer that co-optimises wirelength, peak temperature and operational warpage.
Both treat the objects being placed as fixed-size, fixed-power blocks and freeze the
stack-up. The project therefore had to show that DVPD contributes something those
formulations cannot express --- not merely that mechanics matters.

# Baseline: the June-2026 DVPD Framework

The reference point is *A Comprehensive Design Framework for Vertical Power Delivery in
High-Performance Computing* (arXiv:2606.28837), from the same research ecosystem as this
project. Its full text was read and reconstructed in Phase 0A.

| Aspect | June-2026 treatment |
|:--|:--|
| Load | 1 kW reference, 1--50 kW sweep, 1 V POL, 100 POL segments, 500 mm$^2$ |
| Current density | 2 A/mm$^2$ target (roadmap 2--4) |
| Converter | DSCH hybrid SC--buck as demonstration vehicle; framework claimed topology-agnostic |
| Regulator count $M$ | **enumerated**; the minimiser of total modelled system loss ($M=70$ for the 1 kW case) |
| Switching frequency | **derived** --- minimum feasible from the ripple budget |
| Switch width | **analytically optimised**, $\partial P/\partial w = 0$, then clamped by the per-layer area budget |
| Area budget | $w_{LS}^{max} = A_{budget} / (M \cdot \max\{l_{ind}, l_{LS}\})$ |
| Placement | regular $m \times n$ array, aspect ratio $\approx 1$ |
| POL-to-VR allocation | **proximity heuristic**, not an optimisation variable |
| Interconnect | BGA / TSV / chiplet pad geometry, Table III |
| Objective | minimise total system-wide loss subject to footprint, power-density and ripple |
| Mechanics | **absent** |

Three of its stated modelling conditions became the seams this project works in: current is
allocated by proximity rather than optimised; the VR array is regular with locally similar
cells; and *"intra-VR routing is not constrained by local blockages, keep-out regions, or
package design-rule limitations."* A mechanical keep-out is exactly such a blockage.

# Phase 0A --- Novelty Boundary and Falsification Design

Phase 0A was a literature and code audit rather than a simulation phase. It established
the reviewer-risk position and the gate structure the rest of the project follows.

**Prior art.** Optimal VR count and placement is occupied (ISCAS 2024, ECTC 2024, and
comprehensively by June-2026). Electrothermal DVPD is occupied. Thermo-mechanical placement
is occupied by STAMP-2.5D and ATMPlace. What was *not* found was a framework in which
mechanics constrains variables that are themselves converter-synthesis outputs.

**Gate definitions, fixed in advance:**

* **G1 --- architecture reversal.** Including mechanics changes the preferred architecture.
* **G2 --- feasible-set reversal.** A mechanical constraint removes the electrically
  attractive design. Requires a source-backed allowable.
* **G3 --- robust physical signal.** A mechanically relevant metric changes by $\ge 15\,\%$
  between architectures **and** by more than twice the combined numerical uncertainty.

**Why falsification gates.** Each gate can return a negative that stops the project. The
alternative --- building the framework first and looking for a result afterwards --- is the
failure mode the reviewer audit identified as most likely to produce an unpublishable
outcome after large effort.
\newpage

# Phase 0B --- First Mechanical Gate
**Question.** Does changing the DVPD architecture produce a mechanically *resolved* difference
--- larger than the numerical uncertainty --- at all?

**Implementation.** ANSYS was unavailable (S16.7), so the mechanical chain was built on
**CalculiX 2.23**: a graded structured hexahedral mesh conforming to every material boundary,
a steady-state thermal solve, and a Static Structural solve reading the temperature field
node-for-node on the *same* mesh, so the transfer carries zero interpolation error.
Silicon uses its cubic elastic tensor, not an isotropic approximation.

**Cooling was calibrated, not chosen.** The spec forbids picking a heat-transfer coefficient
because it looks reasonable, so $h_{top}$ was secant-solved until the reference architecture
reached the June-2026 cooled baseline junction temperature, then frozen for the entire study:
**17 521.6 W/m$^2$K**, achieving 83.514 $^\circ$C against an 84 $^\circ$C target (residual
$-0.49$ K).

**Mesh convergence (C05, four graded levels).**

| level | elements | T_max (°C) | die warp (µm) | pkg warp (µm) | Si σ₁ p99 (MPa) |
|:--|--:|--:|--:|--:|--:|
| M1 | 9121 | 81.698 | 7.7544 | 12.1384 | 9.975 |
| M2 | 17579 | 82.855 | 7.7515 | 12.1412 | 10.335 |
| M3 | 22981 | 83.474 | 7.7331 | 12.1264 | 10.519 |
| M4 | 37535 | 83.234 | 7.7720 | 12.1752 | 11.007 |

Source: `results/phase0b/mesh_convergence.csv`

Final-step changes: die warpage **0.50 %**, package warpage 0.40 %, Si $\sigma_1$ p99 4.43 %
--- all inside the acceptance targets (5 % / 10 %). Interface peel changed 19.24 % and
**failed**; it was withheld from every subsequent decision.

**Two solver findings that shaped everything after.** CalculiX's ITERATIVE CHOLESKY solver
disagreed with the direct solver by **35 % on package warpage** and was rejected. And the
C3D8I incompatible-mode element --- required because plain C3D8 shear-locks in bending ---
segfaults above ~40 k elements in this build. The mesh was therefore **graded** (fine at every
tile and die edge, coarse in the far field) with a hard guard that refuses to run above the
ceiling rather than silently falling back.

**Result.**

| metric | C05 (4 distrib.) | C07 (4 asym.) | C13 (6 distrib.) | S_m (%) | 2u_mesh (%) | resolved |
|:--|--:|--:|--:|--:|--:|--:|
| T_max (C) | 83.2337 | 87.2176 | 79.7323 | 8.99 | 0.29 | True |
| die warpage p-v (um) | 7.772 | 12.4808 | 7.7739 | 60.57 | 0.5 | True |
| package warpage p-v (um) | 12.1752 | 15.8212 | 12.078 | 30.74 | 0.4 | True |
| Si max principal p99 (MPa) | 11.0066 | 13.4674 | 10.3524 | 28.3 | 4.43 | True |
| TSV-region vonMises p99 (MPa) | 16.1233 | 17.7947 | 14.4233 | 20.91 | 5.66 | True |
| interface shear p99 (MPa) | 1.6954 | 2.0055 | 1.8278 | 16.97 | 8.7 | False |
| interface peel p99 (MPa) | 1.5703 | 1.889 | 1.6654 | 19.14 | 19.24 | False |

Source: `results/phase0b/three_case_comparison.csv`

**Verdict: GATE PASSED --- resolved mechanical signal.** Placement asymmetry changes die
warpage by **+60.6 %** against 0.50 % mesh uncertainty, and the ordering survives nine material
corners and both boundary-condition families.

**But the mechanism was not the expected one.** Regulator count, at constant footprint and
heat, changed die warpage by **+0.02 %**. The DVPD-specific variable the novelty argument
rested on was inert; the effect came entirely from placement, which is generic floorplanning.

Only die warpage was trusted. Interface shear and peel fell below twice their own uncertainty,
and the homogenised model's local stresses were later shown invalid (S11).

![**Figure 2.** Phase-0B decisive figure. Identical converter heat and footprint; only placement differs. C05 and C13 are visually indistinguishable while C07's asymmetry produces a displaced warpage bowl. *(Phase 0B; data: `results/phase0b/PHASE0B_DECISIVE_FIGURE_BC_A.png`)*](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0b/PHASE0B_DECISIVE_FIGURE_BC_A.png){width=92%}
\newpage

# Phase 0C --- DVPD-Specific Mechanical Lever Gate
**Question.** Phase 0B proved mechanics responds to *placement* --- occupied territory. Does
any genuinely DVPD-specific variable produce a robust mechanical effect?

A frozen 20-case DOE (C01--C20) held the functional-die load at 240 W, total HVR heat at 42 W
and total HVR footprint at 96 mm$^2$, varying only count, placement, thickness, aspect ratio,
footprint and converter heat. Holding heat and footprint constant is what makes an $N_{VR}$
effect attributable to count rather than to more embedded material.

**Variable-level effects, ranked by die-warpage response.**

| variable | cases | ΔT_max % | Δdie warp % | ΔSi σ₁ % | band | DVPD? |
|:--|--:|--:|--:|--:|--:|--:|
| placement (N=4 family) | C04 C05 C06 C07 | 7.65 | 103.78 | 20.58 | STRONG | generic |
| placement (N=6 family) | C13 C14 C15 | 6.48 | 92.83 | 17.67 | STRONG | generic |
| substrate thickness (N=4 distrib.) | C05 C08 | 7.17 | 79.73 | 25.31 | STRONG | YES |
| substrate thickness (N=6 distrib.) | C13 C16 | 6.1 | 79.1 | 19.17 | STRONG | YES |
| substrate thickness (N=2 compact) | C01 C03 | 6.39 | 78.33 | 27.82 | STRONG | YES |
| placement asymmetry only (N=6) | C13 C15 | 6.6 | 51.36 | 18.08 | STRONG | generic |
| placement asymmetry only (N=4) | C05 C07 | 4.67 | 46.5 | 20.11 | STRONG | generic |
| HVR footprint (N=4 distrib.) | C11 C05 C12 | 8.78 | 41.78 | 4.95 | STRONG | YES |
| placement (N=2 family) | C01 C02 | 1.11 | 32.1 | 13.0 | STRONG | generic |
| HVR heat (N=4 asymmetric) | C19 C07 C20 | 15.09 | 21.57 | 22.4 | MODERATE | YES |
| VR count (symmetric distributed) | C05 C13 C17 | 5.36 | 4.1 | 6.13 | BELOW-BAND | YES |
| HVR tile aspect ratio (N=4) | C10 C05 C09 | 1.57 | 1.8 | 1.09 | BELOW-BAND | YES |
| VR count (compact family) | C01 C04 | 1.66 | 0.21 | 3.95 | BELOW-BAND | YES |

Source: `results/phase0c/variable_effects.csv`

**Substrate thickness obeys a clean law.** Across three placement families,
$w_{pv} \propto h_{total}^{-1.949 \pm 0.016}$,
with the thickness effect identical to within
**0.72 percentage points** ---
i.e. no thickness x placement interaction. Two competing mechanisms explain the exponent:
plate stiffness grows as $D \sim Eh^3$, while the fixed-thickness HVR/TSV inclusion sits
further from the shifted neutral axis so its thermal moment arm grows as $\sim h$; net
$w \sim h^{-2}$.

**Homogenisation validation (H0 vs H1).** The smeared TSV block was checked two ways: a
unit-cell numerical homogenisation (E, $\nu$, $k$ within 0.5 %; **in-plane CTE off by
12.59 %**) and a package-scale discrete-inclusion model at equal copper volume. The
architectural spread was preserved to within **1.7 percentage points**, but local silicon
stress rose **+82 to +97 %** when the copper was resolved. **H0 is therefore valid for
architectural screening on warpage and invalid for local stress**, and no local-stress claim
is made anywhere in this project.

**Mechanism.** Die warpage correlates negatively with the inclusion field's polar second
moment ($r=-0.62$; spreading the inclusion lowers peak deflection) and positively with its
first moment ($r=+0.48$; asymmetry raises it). Shape-only anisotropy correlates at exactly
$r=0.000$ --- the quantitative statement of the aspect-ratio null. A three-descriptor physical
model reaches adjusted $R^2 = 0.719$.
These are interpretation aids, not surrogates; no machine learning was trained.

**Verdict: DVPD-SPECIFIC MECHANICAL LEVER PROVEN** --- thickness ($-57$ %), footprint
($\pm 21$ %) and converter loss ($\pm 10.8$ %), with count and aspect ratio confirmed inert.
All results are BC-A (free warpage); under a board-restrained support every architecture
effect, DVPD-specific and generic alike, falls toward the numerical floor.

![**Figure 3.** Phase-0C lever ranking. Red = DVPD-specific, blue = generic floorplanning, grey = below the materiality band. Substrate thickness is the largest DVPD-specific lever; VR count and aspect ratio are inert. *(Phase 0C; data: `results/phase0c/PHASE0C_DVPD_LEVER_FIGURE.png`)*](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0c/PHASE0C_DVPD_LEVER_FIGURE.png){width=92%}
\newpage

# Phase 0D --- First Electrical Coupling
**Question.** Does including mechanics change which architecture is preferred, relative to an
electrical/thermal-only design?

Phase 0C had left the strongest mechanical lever, substrate thickness, with **no path into the
electrical objective**: the PDN model carried two hard-coded floats, `r_bump_ohm = 0.08 m`$\Omega$
and `r_tsv_ohm = 0.04 m`$\Omega$, with no diameter, height, pitch or count. Closing that was
the critical-path task.

**What was built.** A geometry-derived TSV model $R = \rho(T)h/A$ with parallel-count sizing,
validated against June Table III to **+1.62 %**; temperature dependence for GaN $R_{DS(on)}$,
inductor DCR and copper resistivity; and an electrical--thermal fixed point with the validated
FE thermal model inside the loop, converging in 4--5 iterations with energy balance
$\pm 0.000$ %.

**A defect found by running the objective.** The upstream lateral resistance default,
`rho_mohm_per_mm = 50`, is unphysical: it puts ~2100 % IR drop on a 1 V / 60 A branch and drove
one fixed point to 569 $^\circ$C. It was replaced by a first-order geometry-derived plane
resistance, $R/\mathrm{mm} = \rho/(t_{Cu}W_{eff}) = 0.155$ m$\Omega$/mm. **Phase 0D-R shows
that replacement was still wrong**, for a different reason (S7).

**Phase-0D ETM Pareto set (6 members).**

| candidate | N | J | h_sub (µm) | placement | P_elec (W) | T_max (°C) | warpage (µm) |
|:--|--:|--:|--:|--:|--:|--:|--:|
| D23 | 6 | 1.5 | 500 | distributed_3x2 | 15.37 | 65.34 | 4.281 |
| D11 | 4 | 1.5 | 500 | distributed_2x2 | 16.39 | 66.41 | 3.714 |
| D19 | 6 | 2.0 | 500 | distributed_3x2 | 19.04 | 67.38 | 2.895 |
| D07 | 4 | 2.0 | 500 | distributed_2x2 | 20.51 | 68.68 | 2.884 |
| D28 | 4 | 2.0 | 500 | edge_corner_biased | 20.67 | 70.43 | 1.670 |
| D15 | 6 | 4.0 | 500 | distributed_3x2 | 42.15 | 80.23 | 1.575 |

Source: `results/phase0d/coupled_candidates.csv`

**Phase-0D conclusions, as reported at the time:** substrate thickness improves all three
domains ($-0.62$ % electrical, $-2.83$ K, $-57$ % warpage); HVR footprint is a genuine
opposition; and *placement is nearly free electrically (1.08 % spread) while spanning 240 % in
warpage*, so mechanics decides what electrical analysis cannot. The ETM front expanded from 1
architecture to 6, at an exchange rate of 2.03 W/um.

**Why "conditional reversal" was the wrong label.** With warpage entering as a *pure additional
objective*, the minimum-loss design holds minimum $P_{elec}$ by construction and therefore
**can never be Pareto-dominated**. What Phase 0D observed was a **Pareto-front expansion**
priced by an unsourced scalar exchange rate --- not a reversal in any decision-theoretic sense.
Phase 0D-R adopts the stricter terminology throughout.

![**Figure 4.** Phase-0D ET vs ETM Pareto fronts. Superseded by Figure 7: the lateral RDL model underlying these electrical values was wrong by ~65x. *(Phase 0D; data: `results/phase0d/PHASE0D_ET_VS_ETM_PARETO.png`)*](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0d/PHASE0D_ET_VS_ETM_PARETO.png){width=92%}
\newpage

# Phase 0D-R --- Architecture-Aware Correction (authoritative)
**This section supersedes Section 6 wherever they disagree.**

Phase 0D applied a *global* rule --- the thickness-dependent TSV carries converter input
current. That is a property of one stack ordering, not of DVPD. Three architectures were
therefore traced segment by segment.

![**Figure 5.** Architecture-aware power paths. Which rail traverses each interconnect is set by where conversion sits in the stack. The Phase-0D assumption is correct for ARCH_A and wrong for ARCH_B. *(Phase 0D-R; data: `results/phase0dr/FIG_A_power_paths.png`)*](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0dr/FIG_A_power_paths.png){width=92%}

**Rail-aware currents.** At 60 A/VR, 48 -> 1 V, $P_{conv}\approx5$ W: the LV rail carries
60.0 A and the HV rail 1.354 A --- a factor **44.3**, hence about **1960x** in $I^2R$ for an
identical segment. Which side of the converter a segment sits on is the single most important
electrical fact about it.

**Interconnect library.** Every tier is modelled separately with its own geometry, material,
temperature dependence and **cross-section shape**. Validating against June Table III recovered
a detail worth stating: BGA (125 663 um$^2$) and TSV (707 um$^2$) are **circular**, but the
chiplet pad's 100 um$^2$ is a **square** 10x10 um. Assuming it circular would overstate that
tier by 27 %; the square reproduces June's 1.7 m$\Omega$ **exactly**.

| tier | shape | model R (20 °C) | June Table III | error | status |
|:--|--:|--:|--:|--:|--:|
| BGA | circular | 0.3104 mΩ | 0.3 mΩ | +3.45 % | SOURCE_BACKED |
| TSV @300 µm | circular | 7.2150 mΩ | 7.1 mΩ | +1.62 % | SOURCE_BACKED |
| micro-bump | **square** | **1.7000 mΩ** | 1.7 mΩ | **−0.00 %** | SOURCE_BACKED |
| C4 | circular | 1.1586 mΩ | absent | — | ASSUMPTION |
| RDL | 2-D sheet | 5.667 mΩ/sq | absent | — | ASSUMPTION |

Source: `configs/phase0dr/power_path_graphs.yaml`

**Ground return.** Phase 0D modelled supply only. $R_{loop}=R_{supply}+R_{ground}$; modelled
symmetric, so **every Phase-0D interconnect loss was understated by 2x**.

**Feasibility is now a hard gate.** $n_{req}=\lceil I/I_{max}\rceil$; if it exceeds what the
pitch allows in the footprint the architecture is INFEASIBLE, never clipped with `min()`. This
immediately produces an architecture-dependent result: at the conservative per-via limit
(4.8 mA) **ARCH_B needs 12 501 vias where the tile holds 6 666 and is not buildable**, while
ARCH_A remains feasible.

## The dominant correction: the RDL model

Phase 0D's $R/\mathrm{mm} = \rho/(t_{Cu}W_{die})$ inside a parallel-branch network gives every
source--load pair its own full-die-width conductor and no current sharing. It was replaced by a
**2-D resistive sheet**, $\nabla\!\cdot\!(\sigma_s\nabla V) = -J$ with
$\sigma_s = t_{Cu}\,\mathrm{occ}/\rho(T)$, sources injecting over the tile footprint and loads
extracting over each POL segment.

Two numerical points materially affect the answer. A **point** source in a 2-D sheet is
logarithmically singular, so point injection overstates the loss by **776 %**; a real VR injects
over its footprint. And assigning a footprint to the nearest grid cell destroys convergence ---
**exact cell-overlap area weighting** was required, after which the solve converges to
$\le 0.72$ % over $n=41\to121$.

**Independent validation against MOOSE** (DC conduction and heat conduction are the same operator, $\nabla\!\cdot\!\sigma\nabla V \equiv \nabla\!\cdot\!k\nabla T$):

| check | reference | this model | agreement |
|:--|--:|--:|--:|
| analytic uniform-strip conductance | 173.0704 S | MOOSE 173.0704 S | 5.8e-12 % |
| distributed 4-source / 100-load sheet dissipation | MOOSE 5.4915 W | FD 5.5095 W | **0.33 %** |
| peak potential | 0.04484 V | 0.04614 V | 2.90 % |

Source: `results/phase0dr/rdl_validation.json`

**Consequence.** Lateral RDL loss rises from 0.17 W to **12.13 W** (best placement) and
**73.00 W** (worst) --- a 71x to 365x correction. Package distribution is **37--77 %** of total
electrical loss, not 0.25--1.15 %. Lateral RDL, not the TSV, is the dominant term.

## Placement re-audit --- a Phase-0D claim withdrawn

Identical converter, footprint and thickness; only placement differs.

| placement | P_RDL (W) | P_elec (W) | η (%) | T_max (°C) | warpage (µm) |
|:--|--:|--:|--:|--:|--:|
| distributed_2x2 | 12.13 | 32.73 | 88.00 | 70.56 | 3.003 |
| edge_corner_biased | 36.15 | 57.18 | 80.76 | 76.07 | 1.846 |
| compact_2x2_central | 43.13 | 64.40 | 78.84 | 79.01 | 6.490 |
| asymmetric_left | 73.00 | 94.53 | 71.74 | 82.34 | 5.623 |

Source: `results/phase0dr/coupled_candidates_corrected.csv`

The electrical spread across placements is **188.8 %**, not 1.08 %. **"ET is blind to
placement" is withdrawn.** The electrical objective discriminates placement strongly and
largely *agrees* with mechanics --- compact and asymmetric are bad on both counts and are
Pareto-dominated. The one genuine disagreement, distributed (electrically best) versus
edge-biased (mechanically best), now costs **+24.45 W (+75 %) for -1.157 um (-39 %) =
21.1 W/um**.

## Thickness re-audit --- the decisive architecture test

| arch | TSV rail | h_sub (µm) | P_TSV (mW) | P_RDL (W) | P_elec (W) | η (%) | T_max (°C) | warpage (µm) |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| ARCH_A | 48 V | 200 | 0.13 | 12.24 | 33.05 | 87.89 | 73.31 | 6.907 |
| ARCH_A | 48 V | 500 | 0.89 | 12.13 | 32.73 | 88.00 | 70.56 | 3.003 |
| ARCH_B | **1 V** | 200 | 5.76 | 12.24 | 33.06 | 87.89 | 73.31 | 6.908 |
| ARCH_B | **1 V** | 500 | 39.94 | 12.13 | 32.77 | 87.99 | 70.57 | 3.004 |

Source: `results/phase0dr/coupled_candidates_corrected.csv`

**The hypothesis this phase was built to test is NOT confirmed.** The LV-rail TSV penalty is
**45x larger** than the HV-rail one (+34.2 vs +0.76 mW), exactly as the rail argument predicts
--- but it stays an order of magnitude below the thermal benefit, so total electrical loss
still *falls* with thickness in **both** architectures. The reason is structural: sizing vias by
current density makes $P_{TSV} = I\rho h I_{via,max}/A$, **linear** in current rather than
quadratic, so provisioning enough vias caps the penalty.

Architecture-dependence appears in **feasibility**, not in the loss tradeoff.

![**Figure 6.** HV-TSV vs LV-TSV thickness chain. The LV penalty is 45x larger yet total electrical loss still falls with thickness in both architectures. *(Phase 0D-R; data: `results/phase0dr/FIG_C_hv_lv_thickness.png`)*](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0dr/FIG_C_hv_lv_thickness.png){width=92%}

![**Figure 7.** Interconnect loss decomposition. Lateral RDL, not the TSV, dominates; per-tier losses span five decades. *(Phase 0D-R; data: `results/phase0dr/FIG_B_loss_decomposition.png`)*](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0dr/FIG_B_loss_decomposition.png){width=92%}

![**Figure 8.** Footprint tradeoff after the PPDN correction. Larger footprint now improves converter loss, RDL spreading loss and temperature while worsening warpage. *(Phase 0D-R; data: `results/phase0dr/FIG_F_footprint.png`)*](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0dr/FIG_F_footprint.png){width=92%}

![**Figure 9.** Corrected ET vs ETM Pareto. ET front is a single point; the ETM front has four members, all at h_sub = 500 um. The mechanical option costs 16.2 W/um, 8x the Phase-0D estimate. *(Phase 0D-R; data: `results/phase0dr/FIG_G_pareto_corrected.png`)*](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0dr/FIG_G_pareto_corrected.png){width=72%}

## Corrected rankings

**ET Pareto front: a single point** --- `ARCH_A_distributed_J1.5_h500`, which simultaneously minimises loss
and temperature. **ETM Pareto front: 4 members, all at $h_{sub}=500$ um.**

Moving from the ET optimum to the minimum-warpage design costs
**+32.07 W (+127.7 %) for -1.985 um (-51.8 %) = 16.2 W/um** ---
**8.0x more expensive** than Phase 0D's 2.03 W/um.

**Verdict: PHASE-0D CONCLUSION CHANGED BY CURRENT-PATH AND PPDN CORRECTION.** In the stricter
terminology: **ROBUST ETM PARETO TRADEOFF, NO UNIQUE REVERSAL.**
\newpage

# Governing Equations

**Converter loss** (upstream `compute_total_loss`, unmodified). Conduction and switching:

$$P_{cond} = \frac{V_{out}}{V_{in}} I_{out,rms}^2 \big( R_{common} - R_{corr} \big), \qquad
  I_{out,rms} = \sqrt{I_{out}^2 + \Delta i_{eff}^2/12}$$

$$P_{sw} = \underbrace{f_{sw}\Big(\tfrac{V_{in}}{N}-V_{out}\Big) I_{out,rms}\frac{Q_{GD}+Q_G}{I_g}}_{HS}
 + \underbrace{f_{sw}\big(N C_G^{HS} + K C_G^{LS}\big) V_{gs}^2}_{gate}
 + \underbrace{\tfrac{f_{sw}}{2}\Big(N C_{OSS}^{HS}(\tfrac{V_{in}}{N}-V_{out})^2 + K C_{OSS}^{LS} V_{out}^2\Big)}_{C_{OSS}}$$

Coupled-inductor ripple correction: $\Delta i_{eff} = \Delta i_{raw}/(1+k_c(K-1))$.

**Rail assignment and stage currents.**

$$P_{in} = V_{out} I_{out} + P_{conv}, \qquad I_{in} = P_{in}/V_{in}, \qquad
  \eta_{stage} = \frac{V_{out}I_{out}}{P_{in}}$$

**Bulk interconnect resistance**, per tier, with temperature and parallelism:

$$R_{single}(T) = \frac{\rho(T)\,L}{A}, \qquad \rho(T) = \rho_{20}\big[1+\alpha(T-20)\big],
  \qquad A = \begin{cases}\pi d^2/4 & \text{circular (BGA, TSV, C4)}\\ d^2 & \text{square (pad)}\end{cases}$$

$$n_{req} = \left\lceil \frac{I}{I_{max}} \right\rceil, \qquad
  R_{field} = \frac{R_{single}}{n_{req}}, \qquad
  R_{loop} = R_{supply} + R_{ground}, \qquad P = I_{rms}^2 R_{loop}$$

Feasibility: if $n_{req} > n_{avail}(A_{fp},\text{pitch})$ the architecture is **infeasible**.

**Device temperature coefficients.**

$$R_{DS(on)}(T) = R_{25}\big[1+\alpha_{GaN}(T-25)\big], \qquad
  R_{DCR}(T) = R_{25}\big[1+\alpha_{Cu}(T-25)\big]$$

**2-D RDL sheet.** With sheet conductance $\sigma_s = t_{Cu}\,\mathrm{occ}/\rho(T)$:

$$\nabla\!\cdot\!\big(\sigma_s \nabla V\big) = -J(x,y), \qquad
  P_{supply} = \int \sigma_s |\nabla V|^2\, dA, \qquad P_{loop} = 2P_{supply}$$

**Skin depth** (used to justify the DC treatment at $f_{sw}$):
$\delta = \sqrt{\rho/(\pi f \mu)}$.

**Thermal.** Steady-state anisotropic conduction with Robin cooling:

$$\nabla\!\cdot\!(\mathbf{K}\nabla T) + q = 0, \qquad
  -\mathbf{K}\nabla T\cdot\mathbf{n} = h\,(T - T_\infty)$$

**Thermoelasticity.** Temperature enters only as a load; a gradient is never used as a stress:

$$\nabla\!\cdot\!\boldsymbol\sigma + \mathbf b = 0, \qquad
  \boldsymbol\sigma = \mathbf C : \big(\boldsymbol\varepsilon - \boldsymbol\alpha\,\Delta T\big),
  \qquad \Delta T = T - T_{ref}$$

Silicon uses the cubic tensor ($C_{11}=166$, $C_{12}=64$, $C_{44}=79.6$ GPa).

**Warpage metric.** Peak-to-valley out-of-plane displacement over a named surface:

$$w_{pv} = \max_{(x,y)} u_z(x,y) - \min_{(x,y)} u_z(x,y)$$

**Materiality and resolution** (Phase-0B/0C decision rule):

$$S_m = \frac{m_{max}-m_{min}}{|m_{med}|}, \qquad \text{resolved} \iff S_m > 2u_m$$

**Pareto dominance.** $x$ dominates $y$ iff $f_i(x)\le f_i(y)\ \forall i$ and $\exists i: f_i(x)<f_i(y)$.
ET tuple $(P_{elec}, T_{max})$; ETM tuple $(P_{elec}, T_{max}, w_{pv})$.

### Symbols

| Symbol | Meaning | Units |
|:--|:--|:--|
| $V_{in}, V_{out}$ | converter input / output rail | V |
| $I_{in}, I_{out}$ | rail currents (upstream / downstream of conversion) | A |
| $P_{conv}, P_{PDN}, P_{elec}$ | converter, distribution, total electrical loss | W |
| $\rho(T), \alpha$ | resistivity and its temperature coefficient | $\Omega$m, 1/K |
| $\sigma_s, t_{Cu}$, occ | RDL sheet conductance, Cu thickness, metal occupancy | S/sq, m, -- |
| $h_{sub}, t_{tile}$ | power-substrate and HVR-tile thickness | m |
| $n_{req}, n_{avail}$ | required / available parallel conductors | -- |
| $\mathbf K, h, T_\infty$ | conductivity tensor, film coefficient, sink temperature | W/mK, W/m$^2$K, $^\circ$C |
| $\mathbf C, \boldsymbol\alpha, T_{ref}$ | stiffness tensor, CTE, stress-free temperature | Pa, 1/K, $^\circ$C |
| $w_{pv}$ | peak-to-valley warpage | m |
| $S_m, u_m$ | architectural spread, numerical uncertainty | -- |
| $J$ | area-budget current density target ($A_{budget}=I_{out}/J$) | A/mm$^2$ |
\newpage

# Electrical Model Validation

**Analytic scaling.** All 23 checks in `results/phase0d/tsv_resistance_validation.csv` agree
with the closed form to a maximum of **2.83e-14 %** (machine precision): $R\propto h$,
$R\propto 1/d^2$, $R\propto 1/n$, and $\rho(125)/\rho(20)=1.41265=1+\alpha\cdot105$.

**June-2026 reference.** Model 7.215 m$\Omega$ vs quoted 7.1 m$\Omega$ for a 300 um Cu TSV
(**+1.62 %**); BGA +3.45 %; micro-bump **exact** once the square cross-section is recovered.

**Independent FE (MOOSE).** Analytic strip conductance reproduced to 5.8e-12 %; distributed
source/load sheet dissipation agrees to **0.33--0.45 %**.

**AC correction is not required at the operating point.** Skin depth in copper:

| $f$ | $\delta$ | vs 15 um TSV radius | vs 5 um RDL |
|:--|--:|:--|:--|
| $f_{sw}$ = 0.286 MHz | 123 um | 8.2x larger --- no skin effect | 25x larger --- none |
| 10 MHz (35th harmonic) | 20.7 um | 1.4x larger --- onset | 4x larger --- none |
| 1 GHz | 2.1 um | 7x smaller --- deep skin effect | comparable |

At $f_{sw}$ every conductor is electrically thin, so $R_{ac}\approx R_{dc}$ and the DC model is
correct. **No current-crowding correction was applied**, because none was demonstrated ---
introducing an empirical factor without evidence is precisely what the brief forbids.

# Thermal Model Validation

* **Energy conservation.** Robin flux integrated over both cooled surfaces equals the injected
  power to $\pm 0.000$ % on every run in every phase --- an independent check, not a solver
  residual.
* **Cooling calibration.** $h_{top}$ secant-solved to the June-2026 cooled baseline: 83.514
  $^\circ$C against 84 $^\circ$C, residual $-0.49$ K, then frozen.
* **Mesh convergence.** $T_{max}$ changed 0.29 % (thin substrate) and 0.18 % (thick) over the
  final refinement step.
* **Conduction operator validated against MOOSE** to 5.8e-12 % on an analytic case.

**Not done:** a MOOSE or Icepak cross-check of the full 3-D package thermal model with
spatially mapped Joule heat (TH-1...TH-4). This is the largest open validation item and is
carried to the roadmap.

# Mechanical Model Validation

* **Analytic check.** Single-element free thermal expansion reproduces $\alpha\Delta T$ exactly
  (1.666e-3 mm for 16.66 ppm/K over 100 K).
* **Mesh convergence.** Four graded levels; die warpage 0.50 %, package warpage 0.40 %,
  Si $\sigma_1$ p99 4.43 % --- all inside target. Independently repeated for the thick
  substrate (0.45 %).
* **Solver discovery.** ITERATIVE CHOLESKY disagreed with the direct solver by **35 % on
  package warpage** and was rejected; C3D8I has a ~40 k element ceiling in this build, handled
  by graded meshing plus a hard guard.
* **Support conditions.** BC-A is 3-2-1 rigid-body suppression with reaction forces
  $\le 4.3\times10^{-10}$ N --- direct evidence the constraint manufactures no stress.
  BC-B is a compliant support layer anchored to source-backed BGA geometry.
* **Homogenisation.** Valid for warpage (spread preserved to 1.7 pp, absolute bias $-6$ to
  $-9$ %); **invalid for local stress** ($+82$ to $+97$ %).
* **Known limitations.** M0 rung only --- linear thermoelastic, operational load, no assembly
  pre-stress, no plasticity, creep or fatigue. **No ANSYS structural validation exists.**
\newpage

# Coupled ETM Physics --- mechanisms, not just numbers

**Why placement affects warpage.** The HVR tiles are stiff, low-CTE inclusions embedded in a
silicon substrate and heated from within. Global curvature follows the first and second moments
of that inclusion field about the neutral axis. Concentrating it centrally (compact) maximises
local curvature; spreading it to the perimeter (edge) reduces peak deflection; offsetting it
(asymmetric) adds a tilt. Measured correlations bear this out: $r(w, I_{polar}) = -0.62$,
$r(w, |M_1|) = +0.48$.

**Why count is inert.** Subdividing a fixed total inclusion area into more, smaller, still
symmetric pieces changes neither the first moment (still zero) nor materially the second
moment. C05, C13 and C17 have identical $A_{tot}$ and near-identical $I_{polar}$, and their
warpages agree to 0.02--4 %.

**Why footprint changes the mechanical moment.** Unlike count, footprint changes $A_{tot}$
directly, hence the inclusion volume and its moment --- which is why it moves warpage ($\pm21$ %)
where count does not.

**Why thickness changes bending stiffness.** Two competing effects: plate stiffness grows as
$D\sim Eh^3$, while the *fixed-thickness* inclusion sits further from the shifted neutral axis
so its moment arm grows as $\sim h$. Net $w\sim h^{-1.95\pm0.02}$, measured identically across
four placement configurations.

**Why converter loss has high mechanical leverage.** A $\pm25$ % change in HVR loss is only
$\pm3.7$ % of total package heat yet moves warpage $\pm10.8$ %, because that heat is deposited
exactly at the CTE-mismatched inclusion rather than spread over the die.

**Why the rail voltage sets the interconnect penalty.** For fixed transferred power,
$I\propto 1/V$, so an identical segment on the 1 V rail carries 44x the current and dissipates
~1960x more. This is why the same physical TSV is negligible in ARCH_A and 45x more lossy in
ARCH_B --- and why the *feasibility* limit bites only on the LV rail.
\newpage

# Architecture Comparison

| case | TSV rail | N | A_HVR (mm²) | h_sub (µm) | P_conv (W) | P_BGA (mW) | P_C4 (mW) | P_TSV (mW) | P_RDL (W) | P_µb (mW) | P_elec (W) | η (%) | T_max (°C) | warp (µm) |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| A/dist_J1.5_h500 | HV | 4 | 137.3 | 500 | 16.36 | 0.44 | 0.00 | 0.87 | 8.75 | 4.85 | 25.11 | 90.53 | 67.74 | 3.831 |
| A/dist_J1.5_h200 | HV | 4 | 137.3 | 200 | 16.46 | 0.44 | 0.00 | 0.12 | 8.79 | 4.87 | 25.26 | 90.48 | 69.36 | 8.632 |
| A/dist_J2_h500 | HV | 4 | 103.0 | 500 | 20.59 | 0.46 | 0.00 | 0.89 | 12.13 | 4.89 | 32.73 | 88.00 | 70.56 | 3.003 |
| B/dist_J2_h500 | LV | 4 | 103.0 | 500 | 20.59 | 0.46 | 0.00 | 39.94 | 12.13 | 4.89 | 32.77 | 87.99 | 70.57 | 3.004 |
| A/dist_J2_h200 | HV | 4 | 103.0 | 200 | 20.81 | 0.46 | 0.00 | 0.13 | 12.24 | 4.93 | 33.05 | 87.89 | 73.31 | 6.907 |
| B/dist_J2_h200 | LV | 4 | 103.0 | 200 | 20.81 | 0.46 | 0.00 | 5.76 | 12.24 | 4.93 | 33.06 | 87.89 | 73.31 | 6.908 |
| A/dist_J4_h500 | HV | 4 | 60.0 | 500 | 35.17 | 0.53 | 0.00 | 0.97 | 19.72 | 5.05 | 54.89 | 81.39 | 80.26 | 2.083 |
| A/dist_J4_h200 | HV | 4 | 60.0 | 200 | 36.42 | 0.55 | 0.00 | 0.14 | 20.22 | 5.17 | 56.64 | 80.91 | 88.13 | 5.152 |
| A/edge_J2_h500 | HV | 4 | 103.0 | 500 | 21.03 | 0.47 | 0.00 | 0.90 | 36.15 | 4.98 | 57.18 | 80.76 | 76.07 | 1.846 |
| A/comp_J2_h500 | HV | 4 | 103.0 | 500 | 21.26 | 0.47 | 0.00 | 0.91 | 43.13 | 5.03 | 64.40 | 78.84 | 79.01 | 6.490 |
| A/asym_J2_h500 | HV | 4 | 103.0 | 500 | 21.52 | 0.48 | 0.00 | 0.93 | 73.00 | 5.08 | 94.53 | 71.74 | 82.34 | 5.623 |

Source: `results/phase0dr/coupled_candidates_corrected.csv`

ET Pareto: `ARCH_A_distributed_J1.5_h500` (single point). ETM Pareto (4 members): `ARCH_A_distributed_J2_h500`, `ARCH_A_edge_J2_h500`, `ARCH_A_distributed_J4_h500`, `ARCH_A_distributed_J1.5_h500`.
\newpage

# Positive Results

1. **Architecture changes mechanics substantially.** Die warpage spans 1.8--15.6 um (8.5x)
   across the frozen DOE at fixed load, footprint and heat.
2. **Substrate thickness is win/win/win**, and survives every correction: $-56.5$ % warpage,
   $-2.75$ K, $-1.0$ % electrical loss, with $w\propto h^{-1.95\pm0.02}$ measured identically
   across four placement configurations (interaction spread 0.79 pp).
3. **HVR footprint is a genuine ETM opposition**: $-54$ % electrical loss for $+84$ % warpage.
4. **Converter loss carries disproportionate mechanical leverage** --- 3.7 % of package heat
   moves warpage 10.8 %.
5. **The rail carried by a segment is decisive**, and it is architecture-specific: the same TSV
   is 45x more lossy on the LV rail, and only there can it become infeasible.
6. **Numerical soundness**: energy balance $\pm0.000$ %, warpage converged to 0.50 %, reactions
   $\le 4.3\times10^{-10}$ N, sheet model within 0.33--0.45 % of an independent FE solver.

# Negative and Null Results

These are reported at equal prominence because several of them constrain the thesis more than
the positive results support it.

1. **VR count is mechanically inert.** +0.02 % (4->6), $-4.07$ % (4->8), $-0.21$ % (2->4
   compact). This killed the variable the original novelty argument leaned on.
2. **Tile aspect ratio is inert** ($-1.76$ %). On this square vehicle the AR = 2 and AR = 0.5
   cases are provably *identical* by 90$^\circ$ symmetry, so that DOE case can never detect
   anisotropy.
3. **Interface peel never converged** --- 19.2 % per refinement step, and the exclusion-radius
   variants were no better (19.98--20.07 %). Root cause: the underfill is one element thick at
   every standard level. Marked UNRESOLVED AT M0 and excluded from all decisions.
4. **No architecture-dependent thickness tradeoff.** Even forcing the 1 V rail through the
   substrate leaves the penalty an order of magnitude below the thermal benefit.
5. **"ET is blind to placement" was wrong** --- an artifact of a lumped RDL model. Corrected
   spread is 188.8 %, not 1.08 %.
6. **The cheap mechanical win was wrong.** 2.03 W/um becomes **16.2 W/um**, 8x worse.
7. **No dominance reversal is achievable** with warpage as a pure added objective ---
   structurally, not empirically.
8. **G2 has never been testable.** No source-backed allowable exists, and all warpages
   (1.8--8.6 um) sit far inside any plausible limit at this power scale.
\newpage

# Model Defects Discovered and Fixed

| # | defect | found in | consequence if unfixed | resolution |
|--:|:--|:--|:--|--:|
| 1 | `rho_mohm_per_mm = 50` uncalibrated | Phase 0D | 2100 % IR drop; a fixed point at 569 °C | geometry-derived plane resistance |
| 2 | lumped RDL gives every pair its own full-width conductor | Phase 0D-R | RDL loss wrong by ~65x; false 'ET is blind to placement' | 2-D sheet solve, MOOSE-validated |
| 3 | hard-coded `r_tsv_ohm`/`r_bump_ohm` | Phase 0C | h_sub had no path into the electrical objective | geometry-derived R(h,d,n,T) |
| 4 | global 'TSV carries input current' | Phase 0D-R | wrong rail (and 44x wrong current) for ARCH_B | per-segment rail from the power-path graph |
| 5 | ground return omitted | Phase 0D-R | every interconnect loss understated 2x | R_loop = R_supply + R_ground |
| 6 | `min(n_req, n_avail)` silently overloads vias | Phase 0D-R | hides that ARCH_B is unbuildable | hard infeasibility gate |
| 7 | circular cross-section assumed for the chiplet pad | Phase 0D-R | +27 % on that tier | square pad recovered from June's 100 µm² area |
| 8 | point-source injection in the RDL sheet | Phase 0D-R | +776 % loss from a log singularity | finite-area injection over the tile footprint |
| 9 | footprint snapped to nearest grid cell | Phase 0D-R | destroys grid convergence | exact cell-overlap area weighting |
| 10 | ITERATIVE CHOLESKY solver | Phase 0B | 35 % error on package warpage | rejected; direct solver only |
| 11 | C3D8I element ceiling ~40 k | Phase 0B | silent segfault | graded mesh + hard guard |
| 12 | underfill 1 element thick at all levels | Phase 0C | peel can never converge | diagnosed; metric demoted |
| 13 | placement classes count-specific | Phase 0C / 0D | N=6 distributed silently skipped | family-to-class mapping per count |
| 14 | `p99` not population-stable in a thin layer | Phase 0C | 191 % artifact under refinement | documented; raw + p99 both reported |

This table is evidence of audit rigour: **four of these were found by Phase 0D-R alone**, and two of them (2 and 4) changed published conclusions.
\newpage

# Uncertainty and Fidelity Ladder

| class | item | magnitude | effect on conclusions |
|:--|:--|:--|:--|
| numerical | mechanical mesh convergence | 0.50 % (die warpage) | negligible |
| numerical | RDL sheet grid | ≤0.72 % | negligible |
| numerical | FD vs MOOSE | 0.33–0.45 % | negligible |
| parameter | **RDL t_Cu (5 µm)** | **5→40 µm changes P_RDL 8x** | **dominant; all RDL magnitudes are upper bounds** |
| parameter | RDL metal occupancy (0.60) | linear | same direction as t_Cu |
| parameter | **I_via,max (33 vs 4.8 mA)** | **decides ARCH_B feasibility** | **binary architecture outcome** |
| parameter | hvr_effective E, CTE | warpage 3.5x across the range | magnitudes untrustworthy; ordering holds |
| parameter | α_GaN (7.5e-3 /K) | 2x change moves rate ~12 % | not load-bearing |
| parameter | C4 geometry | P_C4 ≈ 0.74 mW | negligible |
| model-form | H0 homogenisation | −6 to −9 % warpage; +82–97 % local stress | warpage usable; local stress excluded |
| model-form | 2-D single-layer RDL | unquantified | real stacks are multi-layer |
| model-form | symmetric ground return | factor 2 | asymmetric return would change it |
| model-form | M0 rung | no assembly pre-stress, no plasticity | no lifetime claim possible |
| boundary | **BC-A vs BC-B** | **warpage suppressed ~20x under BC-B** | **everything here is free-warpage** |
| boundary | cooling calibration | residual −0.49 K | frozen for all phases |

### Status of every major claim

**PROVEN** --- architecture changes warpage 8.5x; thickness is win/win/win with
$w\propto h^{-1.95}$; count and aspect ratio inert; footprint opposition; RDL dominates
distribution loss; the model chain is numerically sound and MOOSE-validated.

**SUPPORTED** --- the moment-based mechanism (adj-$R^2=0.72$); LV-rail TSV 45x penalty;
converter-loss leverage; H0 bias of $-6$ to $-9$ %.

**PROVISIONAL** --- all absolute warpage values; all absolute RDL losses; BC-B magnitudes;
$\alpha_{GaN}$; C4 geometry; the square-tile footprint approximation.

**OPEN** --- any mechanical allowable; the RDL metal stack; $I_{via,max}$; capacitor-ESR and
gate-charge temperature dependence; ANSYS cross-validation; assembly pre-stress.

**NOT TESTED** --- G2 feasible-set reversal; kW-scale behaviour; transient response; BC-B under
the corrected electrical model; PALACE EM validation; MOOSE package-thermal validation.
\newpage

# Novelty Relative to Prior Work

The comparison must be made carefully. It is not defensible to say prior frameworks *cannot*
model something; the accurate statement is what their **published formulations treat as fixed
inputs** versus what this framework co-designs through the converter model.

| Capability | STAMP-2.5D | ATMPlace | June-2026 DVPD | This work |
|:--|:--|:--|:--|:--|
| objects placed | chiplets | chiplets | VR cells (regular array) | HVR cells (arbitrary sites) |
| object **area** | fixed input (150 µm die) | fixed input | derived from the area budget | **co-designed via the converter** |
| object **power** | fixed per-chiplet flux | fixed input | converter-model output | **converter-model output** |
| stack-up / substrate thickness | fixed (100 µm interposer) | frozen | fixed 300 µm, sensitivity only | **design variable** |
| mechanical quantity | von Mises stress | operational warpage | none | die warpage (p-v) |
| assembly residual stress | acknowledged, not modelled | fitted T_ref + bias | n/a | not modelled (M0) |
| power delivery / PDN | none | "handled later" | full electrical model | full rail-aware PPDN |
| rail-dependent interconnect loss | n/a | n/a | uniform allocation | **per-segment rail assignment** |

**What is genuinely distinctive.** In a chiplet placer the heat sources are *given*: count,
footprint and dissipation are inputs, so mechanics can only relocate fixed blocks. In DVPD
synthesis those three are *outputs* of converter design, coupled through the per-layer area
budget $w_{LS}^{max} = A_{budget}/(M\max\{l_{ind},l_{LS}\})$. Mechanics can therefore delete,
shrink or re-power a heat source --- operations with no counterpart in the placement literature.

**What is honestly not distinctive.** The single largest mechanical effect in this project is
placement, which is exactly what STAMP-2.5D and ATMPlace optimise. And after the Phase-0D-R
correction, the electrical objective *also* discriminates placement strongly and largely agrees
with mechanics --- so the case for needing a *coupled* formulation to make placement decisions
is weaker than Phase 0D suggested, not stronger.

**Current strongest DVPD-specific novelty.** HVR footprint: it is simultaneously an electrical
design variable and a mechanical one, and the two point in opposite directions. Substrate
thickness is a genuine three-domain variable but produces **no tension** --- which is itself a
useful, publishable negative result, since it says a designer may thicken freely.

# Publication-Defensible Claims

### Claims that can be made today

1. *In DVPD, converter footprint is simultaneously an electrical variable (it sets the
   per-layer area budget and hence switch sizing and conversion loss) and a mechanical one (it
   sets the CTE-mismatched inclusion volume and hence package warpage), and the two oppose:
   $-54\,\%$ electrical loss for $+84\,\%$ warpage.*
2. *Regulator count, at constant total footprint and heat, is mechanically inert* (0.02--4 %
   across three counts and two placement families) --- a clean null that constrains how DVPD
   mechanical models should be parameterised.
3. *Power-substrate thickness improves electrical, thermal and mechanical objectives
   simultaneously*, with $w \propto h^{-1.95\pm0.02}$ independent of placement to within
   0.79 pp.
4. *The rail carried by a vertical interconnect --- set by where conversion sits in the stack ---
   changes its loss by ~1960x for fixed transferred power, and determines whether the via field
   is feasible at all.*
5. *Package distribution loss in DVPD is dominated by lateral RDL spreading, not by TSVs*, and
   a lumped per-millimetre resistance can understate it by ~65x.

### Claims that must NOT be made yet

* That mechanics **changes the optimum**. It does not, and with a pure added objective it
  structurally cannot.
* Any **feasibility** or reliability claim. No source-backed allowable exists (G2 NOT TESTED).
* Any **absolute** efficiency, warpage or loss number as a design value --- the RDL stack and
  the HVR effective material are unsourced.
* Any **local stress** result from the homogenised model (+82--97 % error).
* Any claim validated by **ANSYS** --- no ANSYS result exists in this project.
* Any **board-mounted** conclusion --- everything is free-warpage BC-A.
\newpage

# Next Steps --- prioritised roadmap

**IMMEDIATE (blocking; not computation)**

1. Source the **RDL metal stack** --- thickness, layer count, P/G occupancy. It is now the
   dominant electrical term; a 5->40 um change moves P_RDL by 8x and every efficiency number
   with it.
2. Resolve **$I_{via,max}$**. It alone decides whether the LV-TSV architecture exists.

**NEXT VALIDATION**

3. **PALACE** EM validation at DC and $f_{sw}$ on the vertical stack and a bump/RDL transition,
   to confirm bulk resistance and quantify current crowding. PALACE is installed and functional;
   the skin-depth argument predicts a negligible AC correction and deserves one confirming run.
4. **MOOSE** package-thermal cross-check (TH-1...TH-4) with spatially mapped Joule heat,
   extending the conduction validation already completed.
5. **BC-B** under the corrected electrical model.
6. **ANSYS** cross-check if the licence returns --- restart `lmgrd` on pinback:1055.

**NEXT SCIENTIFIC GATE**

7. Either source a mechanical allowable, or **scale the vehicle to the 1 kW / 500 mm$^2$ June
   reference** where warpage may approach one. At 240 W no feasibility reversal is reachable by
   any computation.
8. Reformulate warpage as an **$\varepsilon$-constraint** rather than a scalarised objective,
   which removes the need for an exchange rate entirely.

**FINAL SYNTHESIS** --- only after 1, 2 and 7.

**PUBLICATION VALIDATION** --- assembly pre-stress (M1), a package coupon with shadow-moire or
DIC warpage metrology, and hardware efficiency measurement.

### Should Phase 0E start?

**Not as a synthesis framework.** Two of its three inputs --- the metal stack and any mechanical
constraint --- are unsourced, and the corrected exchange rate (16.2 W/um) makes the mechanical
option markedly less attractive than Phase 0D suggested. Building the optimiser now would
encode an arbitrary metal stack and an arbitrary exchange rate into its answer. **Phase 0E
should be the metal-stack closure and validation phase described above.**
\newpage

# References

Primary sources actually used for parameters or positioning. Parameters taken from these are
tagged SOURCE_BACKED in `configs/phase0dr/power_path_graphs.yaml` and
`configs/phase0b/package_stack.yaml`.

[1] S. Krishnakumar, Y. Popryho, M. Choi, R. Rahimzadeh Khorasani, M. Swaminathan, S. Kumar,
and I. Partin-Vaisband, "A Comprehensive Design Framework for Vertical Power Delivery in
High-Performance Computing," arXiv:2606.28837, Jun. 2026.
<https://arxiv.org/abs/2606.28837>
*Used for:* Table III interconnect geometry and resistivities (BGA 400/300/800 µm, TSV
30/300/60 µm Cu, chiplet pad 10/10/20 µm, ρ_Cu = 17 nΩ·m, ρ_solder = 130 nΩ·m); 500 mm² load
footprint; 100 POL segments; 2 A/mm² current density; cooled-baseline junction temperature;
the per-layer area-budget formulation; efficiency and IR-drop reference values.

[2] V. D. Parekh, Z. W. Hazenstab, S. R. Srinivasa, K. Chakrabarty, K. Ni, and V. Narayanan,
"STAMP-2.5D: Structural and Thermal Aware Methodology for Placement in 2.5D Integration,"
arXiv:2504.21140; IEEE ICCD 2025. DOI: 10.1109/ICCD65941.2025.00029
*Used for:* prior-art boundary; solder material properties (Tin-Lead 60-40, E = 20 GPa,
CTE 20.5 ppm/K); substrate-underside natural-convection coefficient (10 W/m²K); mesh-size
reference point (~40 k elements).

[3] Q. Wang, T. Zhu, T. Jia, Y. Lin, R. Wang, and R. Huang, "ATMPlace: Analytical
Thermo-Mechanical-Aware Placement Framework for 2.5D-IC," arXiv:2511.17319, Nov. 2025.
<https://arxiv.org/abs/2511.17319>
*Used for:* prior-art boundary (operational warpage as a placement objective; compact
biharmonic-plate surrogate; chiplet x, y, θ as the only design variables).

[4] "Design Considerations for DC-DC Voltage Regulators in Distributed Vertical Power Delivery
Systems," IEEE ISCAS 2024. DOI: 10.1109/ISCAS58744.2024.10558456
*Used for:* prior-art boundary only. **Full text not retrieved** (paywalled); characterised via
the internal deep-research report and the June-2026 related-work discussion.

[5] "Vertical Power Delivery for High Performance Computing Systems with Buck-Derived
Regulators," IEEE ECTC 2024. DOI: 10.1109/ECTC51529.2024.00364
*Used for:* prior-art boundary only. **Full text not retrieved**; same caveat as [4].

[6] G. Dhondt, *CalculiX CrunchiX* v2.23, 2025. <http://www.calculix.de>
*Used for:* all thermal and structural finite-element solutions.

[7] Idaho National Laboratory, *MOOSE Framework*, `heat_transfer` module, build 09515f92aa.
<https://mooseframework.inl.gov>
*Used for:* independent finite-element validation of the conduction operator and the 2-D RDL
sheet model.

[8] AWS Labs, *Palace: 3D finite element solver for computational electromagnetics*.
<https://github.com/awslabs/palace>
*Installed and functional; recommended for the EM validation in the roadmap. No PALACE result
is claimed in this report.*

[9] C. Geuzaine and J.-F. Remacle, "Gmsh: a three-dimensional finite element mesh generator,"
*Int. J. Numer. Meth. Engng.*, 79(11), 1309--1331, 2009. Version 4.15.2 used.

### Parameters with no citation

The following are **ASSUMPTION** or **OPEN** and are flagged as such throughout: RDL Cu
thickness (5 µm) and metal occupancy (0.60); C4 geometry; per-via current limit; GaN
$R_{DS(on)}$ temperature coefficient; HVR effective-tile E, ν, CTE, k; underfill and TIM
properties; HVR tile thickness; BC-B foundation stiffness; and any mechanical allowable.
No literature value was fabricated to fill these.
