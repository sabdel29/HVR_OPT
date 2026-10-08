---
title: "Electrothermal--Mechanical Co-Design of Distributed Vertical Power Delivery: Model Development, Falsification Gates, and Coupled Architecture Results"
author: "HVR\\_Journal\\_System\\_Level / ETM-DVPD --- HiPerCAS Lab, University of Illinois Chicago"
date: "2026-09-08"
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
| Report date | 2026-09-08 |
| Structural + thermal FE |  --- C3D8I, direct SPOOLES |
| Independent FE cross-check | MOOSE `heat_transfer-opt`, build 09515f92aa |
| Full-wave EM available | PALACE (built, functional) |
| Commercial EM/thermal | ANSYS AEDT v261, **licence restored 2026-09-06**; HFSS and Icepak used, Q3D not licensed |
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

**Method.** Seven sequential falsification gates, each designed so that a negative result
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
  mesh-converged to 0.50 %, and the multilayer RDL model agrees with an independent
  finite-element solver (MOOSE) to 0.45--1.10 % on power across three placements under one
  calibration.
* *The physical metal stack is now sourced, not assumed* (Phase 0E). The RDL is 10 um Cu on
  a 10/2 um line/space rule with 2 VDD + 2 GND layers, taken from ECTC-2024 Table I, whose
  own derived quantities the model reproduces to better than 2 %. This makes the sheet
  5.56x more conductive than Phase 0D-R assumed.
* *The footprint opposition survives a physical material model* (Phase 0E). Replacing the
  homogeneous tile with a composite built from the compiler's own component inventory
  changes the footprint sensitivity by **0.06 %** --- the effect is geometric, not a
  property of the assumed moduli, which is what makes it robust.
* *No AC correction is needed at the switching frequency* --- HFSS shows loop resistance
  flat to 0.18 % below the 19.1 MHz skin crossover, with f_sw = 0.286 MHz two orders of
  magnitude below it. Verified, not assumed.

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
  through the substrate (ARCH_B), the thickness penalty stays an order of magnitude below
  the thermal benefit.
* *The Phase-0D-R verdict that ARCH_B is infeasible is withdrawn* (Phase 0E). It rested on a
  4.8 mA per-via limit with no source; both primary sources imply 70.7 mA or 282.8 mA, and
  the architecture needs 849 of 7 148 available vias --- 11.9 % utilisation. A second
  Phase-0D-R figure, 33 mA, dropped the power-and-ground factor of two.
* *ECTC-2024's published loss magnitudes could not be reproduced* from its own printed
  stack and equations (0.22--0.35 W against a published 39.5--76 W). The stack parameters
  validate; the magnitudes do not, so RDL losses are always quoted with their stack.
* ***Every free-warpage ordering reverses or vanishes under board restraint*** (Phase 0E).
  Footprint goes from +88 % to -12 %, placement from -42 % to +7 %, and thickness stops
  being resolvable in warpage at all (-56 % to -0.14 %), while interface shear rises in
  every case. No single mechanical response is robust across all three levers. This is the
  most serious caveat in the project: it does not invalidate the package-level results, but
  **no board-level conclusion may be drawn from any BC-A result here**.
* *Placement, not footprint, is the cheapest mechanical lever at 240 W* --- 3.70 W/um
  against 11.48 W/um. The DVPD-specific variable is the expensive one, and the cheap one is
  what chiplet placers already optimise. **At the 1 kW reference this lever disappears
  entirely** (Phase 0F): the regulators occupy 55 % of the die and the lattice can be
  compacted by only 9.4 % before the minimum-gap rule is violated, so there is no room left
  to move them.
* ***The geometry used by Phases 0B-0E was not buildable*** (Phase 0F). The selected
  converter needs a 720 um cell; the mechanical model used a 150 um tile inside 200 or
  500 um substrates. **Both endpoints of the thickness sweep that produced the
  "win/win/win" result are impossible with the converter that sweep assumed.** The trend
  DIRECTIONS survive re-running on realizable geometry -- and strengthen -- but every
  absolute magnitude from those phases is superseded, and the Phase-0E remark that the
  mismatch "does not affect trends" was an assumption, not a result.
* *The Phase-0B cooling calibration was not transferable.* At 1 kW the correct film
  coefficient is 9.47x larger; reusing the old one would have put the package near 130 C
  instead of 84 C.

**What Phase 0F found at the reference scale.** Mechanics does become larger and more
robust: free warpage reaches 11.2 um, and unlike at 240 W it **qualifies as a board-mounted
metric** (converged, ordering stable across nine material corners, 72 % separation). The
LV-TSV architecture develops the interior electrical optimum Phase 0E predicted, so a
genuine three-domain thickness conflict does appear -- but overruling it costs 0.016 W/um,
which is 800x cheaper than the footprint lever and not a tradeoff any designer would
deliberate. No source-backed mechanical criterion could be found, so G2 remains NOT TESTED;
a hypothetical limit only changes the answer if it lands inside the narrow band
1.27-3.04 um.

**What Phase 0E added and removed.** It closed the physical stack, but it also withdrew the
most striking Phase-0D-R result (ARCH_B is *not* infeasible; that verdict rested on an
unsourced per-via limit), cut the placement electrical spread from 188.8 % to 46.7 %, and
exposed the board-restraint reversal above. In exchange it produced one genuinely new
DVPD-specific finding: the architecture-dependent thickness margin, 1.46x in ARCH_B against
67.7x in ARCH_A, where Phase 0D-R had concluded no architecture dependence existed.

**Current strongest novelty.** Not "mechanics changes the optimum" --- it does not, and with
a pure added objective it structurally cannot. The defensible claim is narrower: *HVR
footprint is simultaneously an electrical design variable (it sets the per-layer area budget
and hence switch sizing) and a mechanical one (it sets the CTE-mismatched inclusion volume),
and the two point in opposite directions.* Chiplet placers cannot express this because
chiplet area and power are fixed inputs, whereas HVR cell area and dissipation are outputs
of converter sizing.

**Current limitations.** The exchange rate between watts and microns is still unsourced, so
no selection rule can be applied, and no mechanical allowable exists, so G2 remains
untested. The electromigration *reliability* limit is still open --- what Phase 0E closed is
the *provisioning* current density the sources actually used. ECTC-2024's absolute loss
magnitudes are not reproducible from its printed model, so RDL magnitudes stay provisional.
The selected inductor is 500 um tall while the mechanical vehicle uses a 150 um tile, so
absolute warpage values are not design numbers. Q3D Extractor is not licensed, so DC
resistance is validated with a conduction FE rather than a commercial extractor.

**Exact next work.** The physical stack and the allocation rule are closed; what is not
closed is whether any mechanical constraint ever becomes active. That is a question of
scale, not of modelling: at 240 W the warpage numbers are microns. The next gate should
scale to the June 1 kW / 500 mm2 reference and ask whether a mechanical constraint binds
there. Building the synthesis optimiser before that would still encode an arbitrary
exchange rate into the answer.

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
> **STATUS: HISTORICAL.** The mechanical machinery, mesh convergence and cooling calibration established here are still in use. The GEOMETRY is not: Phase 0F shows the 150 um tile and the 200/500 um substrates cannot contain the selected converter, so the absolute magnitudes in this chapter are superseded.
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
> **STATUS: HISTORICAL.** The lever ranking and its robustness study stand as trends. The absolute magnitudes rest on the same unbuildable geometry corrected in Phase 0F.
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
> **STATUS: SUPERSEDED.** Every quantitative result in this chapter was overturned by the Phase-0D-R current-path correction and again by the Phase-0E stack closure. It is retained because the corrections are only intelligible against what they replaced. For the current authoritative values see the Phase-0E and Phase-0F chapters.
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

# Phase 0D-R --- Architecture-Aware Correction
> **STATUS: SUPERSEDED for all magnitudes; its structural corrections stand.** The rail-aware power path, the ground return and the hard feasibility gate introduced here are still in force. Its numbers are not: the RDL stack was unsourced (Phase 0E: 5.56x too resistive), the placement spread of 188.8 % becomes 46.7 %, the exchange rate of 16.2 W/um becomes 11.48 W/um, and the ARCH_B infeasibility verdict is withdrawn. Values below are **historical**.
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

# Phase 0E --- Physical Stack Closure and Independent Validation (authoritative)

Phase 0D-R corrected the *current paths*. It left the *physical stack* unsourced, and since
its own dominant term was the RDL, the dominant term rested on four assumptions. Phase 0E
closes them from primary sources, separates three quantities that had been conflated in the
TSV model, and revalidates against independent solvers. **The ANSYS licence was restored on
2026-09-06**, so HFSS and Icepak are used here; Q3D Extractor is not licensed.

## The four assumptions that set the dominant term

| parameter | Phase 0D-R | Phase 0E | source |
|---|---|---|---|
| RDL Cu thickness | 5 µm (ASSUMPTION) | **10 µm** | ECTC-2024 Table I; independently confirmed by ISCAS-2024 |
| metal occupancy | 0.60 (ASSUMPTION) | **0.833, derived** from the 10/2 µm line/space rule | ECTC-2024 Table I |
| layer count | 1 (ASSUMPTION) | **2 VDD + 2 GND** | ECTC-2024 "P/G layers" column, settled by the PCB row |
| ground return | "×2 on the answer" | explicit second network, solved | — |

![**Figure 10.** The sourced multilayer power stack replaces the assumed single sheet. Occupancy is derived from the line/space design rule, not chosen. *(Phase 0E; data: `results/phase0e/`)*](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0e/FIG_0E_A_metal_stack.png){width=92%}

Sheet conductance rises by **5.556×**, so every Phase-0D-R RDL magnitude falls by that factor. The stack is not merely quoted: both trace rows of the source table reproduce the paper's own derived `R'_Heff` to better than 2 %, which is why it is treated as closed.

## What the sources would not confirm

The June-2026 framework contains **no metal stack at all** --- its PPDN is a lumped
`rho_mohm_per_mm = 0.5` distance model with no thickness, layer count or occupancy. And
ECTC-2024's *published loss magnitudes* (Table II) cannot be reconstructed from its own
printed stack and equations: applying them literally gives 0.22-0.35 W against a published
39.5-76 W, and no segment count closes a gap that scales as 1/S. The stack **parameters** are
validated; the **magnitudes** are not. RDL losses are therefore always quoted with the stack
that produced them.

## The compact multilayer model is validated against an independent solver
Predeclared before any run: $|\Delta P| \le 2.0$ %, $|\Delta V| \le 4.0$ %, **one calibration for all placements** --- no per-case fitting.

| placement | compact (W) | MOOSE FE (W) | ΔP | ΔV | |
|---|---:|---:|---:|---:|---|
| distributed | 0.97838 | 0.98282 | -0.45 % | -2.16 % | PASS |
| edge_biased | 1.75046 | 1.76998 | -1.10 % | -2.19 % | PASS |
| asymmetric | 6.82347 | 6.86353 | -0.58 % | -0.90 % | PASS |

![**Figure 11.** Multilayer RDL compact model against an independent FE solver, with the grid convergence that fixes the working resolution. *(Phase 0E; data: `results/phase0e/`)*](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0e/FIG_0E_D_rdl_validation.png){width=92%}

Getting this right required fixing three defects in the *comparison*, each of which would have produced a confident wrong answer: a whole-edge Dirichlet reference (a different boundary-value problem, +25 % / +55 % error), a 104-term `ParsedFunction` that silently lost terms (18 % of the injected current), and a tile placed 0.27 mm off the die edge where the two codes treat clipping differently.

## EM validation --- and a solver used only where it is valid

Q3D Extractor is **not licensed** on this server (`UNSUPPORTED "elec_solve_q3d" ... No such
feature exists (-5,346)`), so DC conduction is validated with MOOSE and HFSS is confined to
its valid regime. A two-port series extraction at 286 kHz was tried first and **rejected**:
HFSS returned `Z11 = Z12 = -4.2e7` ohm and the series impedance is their difference --- eleven
digits of cancellation. With the far end shorted instead, a one-port gives the loop
impedance directly.

Skin depth equals the via radius at **19.1 MHz**; at f_sw = 0.286 MHz, δ/r = 8.18. HFSS
shows R varying by **0.18 %** between 1 and 5.6 MHz and then rising
3.1× by 1 GHz. **No AC correction is
needed at the switching frequency --- verified rather than assumed.** Measured resistance
exceeds a 1-D series sum of the same geometry by 1.33×
(1.96× for a second geometry), so bulk-cylinder resistance is not total connection
resistance; that band is carried as an uncertainty, not a calibration.

## TSV allocation --- three quantities that were one

Phase 0D-R computed `R_field = R_single / n_required`. That silently makes the via field's
loss proportional to current --- but only because `n_required` is itself proportional to
current. Phase 0E separates `n_required` (capability), `n_allocated` (actually assigned, and
what resistance must use) and `n_available` (geometry), and enforces
`n_req <= n_alloc <= n_avail`. Under a geometric allocation policy the same field gives
`P ~ I^2`, so the apparent linearity is a **design policy, not a law**.

The policy itself is source-backed. June-2026 states it verbatim: *"the number of parallel
VICs per connection is sized based on the connection current and per-via current limit, with
current assumed to be uniformly distributed across the allocated VICs."*

Measured across the same via field, with the LV rail carrying 44.31x the HV rail's current:

| policy | current ratio | TSV field-loss ratio | law |
|---|---:|---:|---|
| `A_min_capability` (June's own) | x44.31 | x46.26 | **P ~ I** (linear) |
| `B_geometric` | x44.31 | x1963.65 | **P ~ I²** (quadratic) |
| `C_area_optimal` | x44.31 | x1963.65 | **P ~ I²** (quadratic) |


The quadratic ratio is exactly 44.31² = 1963. The linear behaviour Phase 0D-R reported as if
it were a property of through-silicon vias is a consequence of provisioning the count at the
bare current-capability minimum. It also means the architecture-dependent thickness margin
below is a consequence of that provisioning policy rather than of the LV-TSV architecture
itself: allocating all available vias instead of the minimum cuts ARCH_B's TSV loss from
89.6 mW to 10.6 mW and would raise its thickness margin from 1.46x to roughly 12x.

![**Figure 12.** TSV allocation and the current-capability envelope. ARCH_B is feasible across the whole source-backed range; only the unsourced 4.8 mA candidate makes it infeasible. *(Phase 0E; data: `results/phase0e/`)*](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0e/FIG_0E_BC_allocation_feasibility.png){width=92%}

### The per-via limit, and the error it exposes

| basis | J (A/m²) | I_max per 707 µm² via | agreement across independent tiers |
|---|---:|---:|---|
| June-2026 (conservative) | 1.0e+08 | 70.7 mA | pads 1.000e8 vs TSVs 9.366e7 → 6.8 % |
| ECTC-2024 (aggressive) | 4.0e+08 | 282.8 mA | pad 4.000e8 vs TSV 4.027e8 → 0.7 % |
| Phase-0D-R "33 mA" | — | 33 mA | **dropped the P&G factor of 2** |
| Phase-0D-R "4.8 mA" | — | 4.8 mA | mixed one rail's current with another's allocation |


Separating the counts also changes a Phase-0D-R conclusion about thickness. Decomposing the
200 -> 500 um change at the reference point, the vertical penalty in ARCH_A is +2.09 mW
against a 141.21 mW converter saving (a 67.7x margin), but in ARCH_B it is +96.22 mW against
140.08 mW --- a margin of only **1.46x**, consuming 69 % of the benefit, and the package
distribution loss actually *rises* with thickness. Thicker still wins in both architectures,
but Phase 0D-R's conclusion that no architecture-dependent thickness tradeoff exists rested on
a penalty an order of magnitude smaller than the corrected one. The tension is real and close
to binding; it simply does not flip the sign at 240 W.

**ARCH_B is feasible under every source-backed current density.** At the reference point it
needs 849 of 7 148 available vias --- 11.9 % utilisation. It would become infeasible only
below about 1e7 A/m², which is 5-11× below the most conservative value either primary source
implies. The Phase-0D-R infeasibility verdict rested entirely on the one candidate with no
source, and is **withdrawn**.

## The most important mechanical result: footprint survives

Every mechanical footprint result in this project assumed the HVR tile was a homogeneous
block of `hvr_effective` filling the whole electrical bounding box. The compiler's own area
rule is a **maximum** over component-layer areas, not a sum --- components are vertically
stacked and every layer but the largest is only partly filled.

| j (A/mm²) | A_HVR (mm²) | Σ component area (mm²) | areal fill | E_eff (GPa) | CTE_eff (ppm/K) |
|---:|---:|---:|---:|---:|---:|
| 1.5 | 34.32 | 66.82 | 0.4867 | 65.4 | 5.544 |
| 2.0 | 25.74 | 48.99 | 0.4758 | 64.3 | 5.493 |
| 4.0 | 15.00 | 47.50 | 0.7917 | 100.1 | 4.886 |


The bounding box spans 2.288× while the actual CTE-mismatched material spans only 1.407×:
between j = 2.0 and j = 4.0 the box shrinks 42 % and the component area shrinks 3 %. The
parts do not get smaller, they pack more densely.

A scaling argument on `E_eff · CTE_eff · A_HVR` predicts the footprint sensitivity weakening
by 26 %. **The finite-element answer is that it does not weaken at all.**

| variant | warpage over A = 60 → 137 mm² | span |
|---|---|---:|
| homogeneous | 2.009 → 3.756 µm | **1.8696×** |
| composite | 2.128 → 3.976 µm | **1.8685×** |

![**Figure 13.** Left: the CTE-mismatched material does not scale with the electrical bounding box. Right: the footprint opposition survives the physical material model. *(Phase 0E; data: `results/phase0e/`)*](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0e/FIG_0E_F_footprint_material.png){width=92%}


The physical material distribution shifts warpage uniformly by about +6 % and changes the
footprint **sensitivity by 0.06 %**. The reason is that the tile both drives bending through
CTE mismatch and resists it as a local stiffener; softening it moves those two in opposite
directions and they nearly cancel. What survives is that the footprint dependence is
**geometric** --- it is set by how much package area is occupied by a dissimilar inclusion,
not by that inclusion's moduli. That is what makes it robust to the largest material
uncertainty in the model.

**Verdict: FOOTPRINT ETM OPPOSITION ROBUST.**

## Board restraint changes which response discriminates

Phase 0C showed that a compliant board support suppresses free warpage by roughly twenty
times, and left the question there. Phase 0E runs the decisive pairs under both boundary
families and asks the question that actually matters for a design framework: **when the
package is restrained, which response still separates the candidates?** Interface peel is
excluded throughout --- it never converged and remains demoted.

| pair | member | BC-A warpage (µm) | BC-B warpage (µm) | BC-A shear p99 (MPa) | BC-B shear p99 (MPa) |
|---|---|---:|---:|---:|---:|
| A_footprint | large_j1.5 | 3.7531 | 0.4719 | 2.325 | 3.854 |
| A_footprint | small_j4.0 | 1.9930 | 0.5376 | 2.852 | 5.186 |
| B_thickness | h200 | 6.7021 | 0.5099 | 1.593 | 4.479 |
| B_thickness | h500 | 2.9172 | 0.5092 | 2.432 | 4.048 |
| C_placement | distributed | 2.9172 | 0.5092 | 2.432 | 4.048 |
| C_placement | edge_biased | 1.7052 | 0.5441 | 2.899 | 4.676 |

![**Figure 14.** Under board restraint warpage collapses while interface shear grows. The discriminating response changes, and for footprint the warpage ordering reverses. *(Phase 0E; data: `results/phase0e/`)*](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0e/FIG_0E_G_bcb.png){width=92%}


Two things happen at once. Warpage falls by roughly an order of magnitude, and interface
shear **rises** --- the restraint converts bending into shear at the die attach. For the
footprint pair the warpage ordering also **reverses**: the larger footprint is worse under
free warpage and better under restraint. Any board-level design conclusion drawn from the
BC-A results in this report would therefore be wrong in sign.

This does not invalidate the free-warpage work, which is a legitimate package-level
quantity and the one prior thermo-mechanical placement work also reports. It does mean the
ETM formulation must eventually choose its response deliberately: **free warpage for a
package-level objective, interface shear for a board-mounted one**, and they do not agree.
\newpage

# Phase 0F --- 1-kW Reference-Scale ETM Gate (current authoritative)

Phase 0E closed the physical stack and concluded that the ETM novelty weakens. It also left
one question open that no amount of modelling at 240 W could answer: at 240 W every warpage
number is a few microns, so no mechanical constraint can bind and the question of whether
thermo-mechanics belongs inside DVPD synthesis is really a question about **scale**. Phase 0F
scales the validated model to the June 1 kW / 500 mm2 reference and asks it.

Two things had to be repaired before the question could even be posed.

## The geometry was not buildable

Phase 0E recorded that the selected converter contains a 500 um inductor while the mechanical
tile is 150 um, and added that this *"does not affect trends"*. That was an assumption, and
testing it is the first thing Phase 0F did.

The converter's cell needs **720 um** of substrate. A 200 um substrate cannot contain it under
any height bound, and a 500 um substrate cannot under the nominal or pessimistic bound.
**Both endpoints of the thickness sweep that produced "thicker is win/win/win" across four
phases are unbuildable with the converter that sweep assumed.** Under the most generous bound
a 500 um substrate does admit a converter, but the best one available costs 27.4 W per
regulator at 25 C against 4.2 W --- 6.4x worse. The realizable range starts near 800 um.

![**Figure 15.** The height rule. Left: the converter cell must fit inside the substrate with a via field beneath it; the two thicknesses used in Phases 0B-0E cannot contain it. Right: how much of the inductor library each substrate thickness admits. *(Phase 0F; data: `results/phase0f/`)*](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0f/FIG_0F_A_realizable_stack.png){width=92%}
Re-run on realizable geometry, the three decisive 240 W comparisons behave as follows:

| comparison | Phases 0B-0E (unbuildable) | Phase 0F (realizable) |
|---|---:|---:|
| thickness, thin -> thick | -56.5 % | **-81.9 %** |
| footprint, small -> large | +87.9 % | **+108.3 %** |
| placement, distributed -> edge | -41.5 % | **-49.4 %** |

The **directions all survive** and in fact strengthen. The Phase-0E remark was therefore half right --- but it was an assumption about a geometry that could not be built, and the magnitudes it produced were wrong by tens of percent.

## The cooling boundary was not transferable

Phase 0B solved for h_top = 17 521.6 W/m2K so a ~282 W vehicle reached the June junction
temperature. At 1 kW the package rejects four times the heat through the same die. Carrying
that coefficient over would have put the package near 130 C instead of 84 C and overstated
converter loss by roughly 25 W.

Recalibrated against the June 1-kW reference (T_j,max = 84 C):
**h_top = 166,000 W/m2K, 9.47x the Phase-0B
value**, achieving 84.07 C.

June actually cools with substrate-embedded micro-channels *adjacent to the GaN switch
layer*. That topology was calibrated too and **cannot reach the target at all**: it
flattens at 91.0 C even at
398,672 W/m2K, because the die holds 1000 W of the ~1100 W total and
sits on the far side of the package from the coolant. A 1-kW DVPD package cannot be cooled
from the substrate side alone.

![**Figure 16.** Every element of the 240 W vehicle had to be rebuilt for the 1-kW reference rather than scaled. *(Phase 0F; data: `results/phase0f/`)*](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0f/FIG_0F_B_scaling_chain.png){width=92%}

## The result: an architecture-dependent thickness conflict appears

Phase 0E found that ARCH_B's thickness margin was 1.46x against ARCH_A's 67.7x and
predicted the sign would flip at scale. It does.

| arch | h_sub (mm) | P_elec (W) | P_TSV (mW) | warpage (um) | |
|---|---:|---:|---:|---:|---|
| ARCH_A | 0.80 | 125.076 | 0.21 | 11.163 | |
| ARCH_A | 1.00 | 125.043 | 0.73 | 6.775 | |
| ARCH_A | 1.25 | 125.028 | 1.38 | 4.048 | |
| ARCH_A | 1.50 | 125.022 | 2.03 | 2.619 | |
| ARCH_A | 2.00 | 125.014 | 3.33 | 1.272 | <- electrical optimum |
| ARCH_B | 0.80 | 125.085 | 9.19 | 11.163 | |
| ARCH_B | 1.00 | 125.075 | 32.16 | 6.776 | <- electrical optimum |
| ARCH_B | 1.25 | 125.089 | 60.86 | 4.049 | |
| ARCH_B | 1.50 | 125.112 | 89.57 | 2.619 | |
| ARCH_B | 2.00 | 125.162 | 146.98 | 1.272 | |


**ARCH_A's electrical optimum is the thickest substrate --- no conflict. ARCH_B's is
INTERIOR, at h = 1.00 mm.** Its LV rail drives the whole output current
through the substrate, so the TSV field loss grows fast enough with thickness to turn the
electrical curve around while warpage keeps falling. That is a genuine three-domain
conflict and it is architecture-specific.

It is also nearly free. Overruling the electrical optimum to take the thickest substrate
costs **+0.0873 W** --- 0.07 % of system loss --- and
buys **5.504 um**, an exchange rate of **0.0159 W/um**. Set against the
footprint lever's 12.9 W/um, this is a tradeoff no designer would deliberate over: they
would simply thicken the substrate.

![**Figure 17.** The LV-TSV architecture develops an interior electrical optimum at 1 kW while the mechanical preference stays monotone. The conflict is real in sign and negligible in magnitude. *(Phase 0F; data: `results/phase0f/`)*](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0f/FIG_0F_C_thickness_margin.png){width=92%}

## A mounted metric had to be qualified before it could be used

Phase 0E showed board restraint converts warpage into interface shear, but Phase 0B/0C had
already found interface shear only marginally converged and material-sensitive. Using it
without a dedicated study would have repeated the interface-peel mistake. So every
candidate mounted metric was put through convergence (interface mesh 1/2/4) and robustness
(nine material corners) before any mounted conclusion was drawn.

**7 of 9 metrics qualify.** The two rejected are the p99 and p95
percentiles of relative interface displacement: superbly converged, but their ordering
flips between material corners.

The important row is the first. **Free die warpage itself qualifies as a mounted metric at
1 kW**, converging to 0.0 % and separating thin from thick by 72.3 % in the worst corner.
At 240 W it did not: Phase 0E measured -56 % free collapsing to -0.14 % mounted, below the
resolution floor. The difference is purely scale --- at 1 kW the residual mounted warpage
stays far above the numerical floor.

![**Figure 18.** Qualifying a board-mounted metric: ordering stability across nine material corners, and convergence under interface refinement. *(Phase 0F; data: `results/phase0f/`)*](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0f/FIG_0F_E_bcb_metric_qualification.png){width=92%}

## The assembly state decides the sign of the thickness lever

Phase 0E established that the discriminating mechanical response changes under board
restraint. Phase 0F asks the sharper question at the reference scale: does the DIRECTION
of the correct design move survive mounting? For the dominant lever it does not.

| lever | BC-A free package | BC-B board-mounted | |
|---|---:|---:|---|
| thickness ARCH_A 0.8 -> 1.5 mm | -76.54 % | +81.65 % | **SIGN REVERSES** |
| thickness ARCH_B 0.8 -> 2.0 mm | -88.61 % | +138.77 % | **SIGN REVERSES** |
| footprint 259 -> 329 mm2 | +20.30 % | +5.79 % | preserved |
| placement uniform -> compact | +10.78 % | +6.72 % | preserved |


**Only thickness reverses.** Footprint and placement keep their sign in both states,
merely compressed by the restraint. The reversal is specific to the one lever that acts
through the substrate's bending stiffness -- exactly the quantity a board foundation
overrides. A thicker substrate resists bending when it is free and transmits more
differential deformation into the die when it is held flat.

This is the Phase-0F verdict in one sentence: **the mechanical preference for substrate
thickness is not a property of the design, it is a property of the design and its assembly
state.** A DVPD framework that optimises free-package warpage and then mounts the result
will move the substrate thickness the wrong way.

![**Figure 19.** Footprint response in both assembly states at 1 kW. Unlike thickness, the footprint opposition keeps its sign when the package is mounted. *(Phase 0F; data: `results/phase0f/`)*](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0f/FIG_0F_D_footprint_free_vs_mounted.png){width=92%}

## Verdict
```
ASSEMBLY-STATE-DEPENDENT ETM CONSTRAINT
```

Warpage grew fourfold at the reference scale, and growth alone does not license a positive
verdict. What does is that the mechanical and electrical preferences change places depending
on how the package is mounted, in a signal that is qualified rather than noise.

Mechanics is **not** a synthesis constraint at 1 kW: nothing binds, because no source-backed
criterion exists, and in the free state the mechanical improvement costs 0.016 W/um -- a
tradeoff no designer would deliberate. But it is **not** merely a signoff quantity either,
because the direction of the correct thickness move depends on an assembly-state choice that
an electrical/thermal framework does not represent at all.

What would settle it is a calibrated board foundation -- the BC-B stiffness is still
PROVISIONAL and the entire reversal rests on it -- and one source-backed mechanical criterion,
which would let the epsilon band 1.27-3.04 um be turned into a real feasibility statement.

![**Figure 20.** Where mechanics becomes decision-relevant. Left: at 1 kW mechanics improves ~90 % across the realizable thickness range while electrics move under 0.15 %. Right: the cost of buying mechanics, against the Phase-0E levers at 240 W. *(Phase 0F; data: `results/phase0f/`)*](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0f/FIG_0F_H_crossover_map.png){width=92%}
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
   is 45x more lossy on the LV rail. Phase 0E shows this does **not** eliminate the LV-TSV
   architecture --- it is feasible under every source-backed current density --- but it does
   leave that architecture with a 1.46x thickness margin against ARCH_A's 67.7x.
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
| 15 | RDL stack (5 µm, occ 0.60, 1 layer) unsourced | Phase 0E | the DOMINANT term was an assumption; 5.56x too resistive | ECTC-2024 Table I, verified against its own R'_Heff |
| 16 | `R_field = R_single / n_required` | Phase 0E | makes P ~ I look like a law when it is an allocation policy | n_req / n_alloc / n_avail separated; R uses n_alloc |
| 17 | per-via limit 33 mA dropped the P&G factor of 2 | Phase 0E | halves the apparent via capability | N = 2I/(A·J) applied as the source writes it |
| 18 | per-via limit 4.8 mA had no source | Phase 0E | **falsely declared ARCH_B infeasible** | source-backed J envelope; feasibility reported as a map |
| 19 | whole-edge Dirichlet used as a solver reference | Phase 0E | +25 % / +55 % error in the MOOSE comparison | finite-area reference at the same point in both codes |
| 20 | 104-term `ParsedFunction` silently loses terms | Phase 0E | 18 % of injected current lost, ~35 % in power | uniform load + 4 boxcars + 11th-order Gauss |
| 21 | tile placed 0.27 mm off the die edge | Phase 0E | clipped footprint treated differently by the two codes | placements asserted to lie on the substrate |
| 22 | AEDT exported `im(Z)` before `re(Z)` | Phase 0E | R and X transposed; a confident wrong EM validation | columns matched by header name, never by position |
| 23 | homogeneous HVR tile filling the bounding box | Phase 0E | mechanical inclusion volume overstated at small footprints | composite from the compiler's own component inventory |
| 24 | **150 µm tile holding a 500 µm inductor** | Phase 0F | **both thickness endpoints of four phases are unbuildable** | height rule `t_cell + h_tsv <= h_sub`; geometry gate before every mesh |
| 25 | Phase-0B cooling calibration reused at 4x the load | Phase 0F | package at ~130 °C instead of 84 °C; converter loss overstated ~25 mW/K x 46 K | recalibrated at 1 kW; h_top is 9.47x larger |
| 26 | Phase-0B placement families hard-wired to n_vr = 4 | Phase 0F | no 49-regulator layout expressible at all | Phase-0F lattice families with the same validation rules |
| 27 | interface shear used without qualification | Phase 0F | a marginally converged, material-sensitive metric would have carried mounted design decisions | convergence + 9-corner ordering test before any mounted claim |
| 28 | electrical-only crossover sweep at frozen temperature | Phase 0F | removes the converter-loss reduction that motivates thickening; every load then falsely prefers thin | crossover taken from full ET fixed points only |

This table is evidence of audit rigour: nine were found by Phase 0E and five more by Phase 0F. **Defect 24 is the most consequential in the project.** For four phases the mechanical vehicle held a converter that could not physically fit inside it, and the inconsistency was carried forward once with the remark that it "does not affect trends" -- an assumption that was never tested until Phase 0F tested it. The directions did survive; the magnitudes and the swept thicknesses did not.
\newpage

# Uncertainty and Fidelity Ladder

| class | item | magnitude | effect on conclusions |
|:--|:--|:--|:--|
| numerical | mechanical mesh convergence | 0.50 % (die warpage) | negligible |
| numerical | RDL sheet grid | ≤0.72 % | negligible |
| numerical | multilayer RDL vs MOOSE, 3 placements | 0.45–1.10 % (power) | negligible; one calibration |
| numerical | HFSS R(f) flatness below the skin crossover | 0.18 % | no AC term needed at f_sw |
| parameter | RDL t_Cu — **CLOSED** at 10 µm | envelope 1.02–3.40 mΩ/sq across readings | no longer dominant-by-assumption; doubly sourced |
| parameter | RDL occupancy — **CLOSED**, derived 0.833 | set by the 10/2 µm line/space rule | no longer free |
| parameter | RDL layer count — **CLOSED**, 2 VDD + 2 GND | factor 2 vs the 1+1 reading | settled by the source's own PCB row |
| parameter | **J_Cu provisioning (1.0e8 vs 4.0e8)** | **4x; each self-consistent across 2 tiers** | ARCH_B feasible under BOTH; no longer binary |
| parameter | **I_max,reliability** — still OPEN | no primary EM study retrievable here | **no feasibility claim is made** |
| parameter | ECTC Table II magnitudes not reproducible | 0.22–0.35 W vs published 39.5–76 W | **RDL magnitudes stay provisional** |
| parameter | hvr_effective E, CTE | warpage 3.5x across the range | magnitudes untrustworthy; **footprint ordering robust to 0.06 %** |
| parameter | HVR tile height (150 µm modelled) | the chosen inductor alone is 500 µm tall | absolute warpage is not a design value |
| parameter | current crowding at via/pad | 1.33–1.96x on a 1-D series estimate | <1 % of PDN loss; carried as a band |
| parameter | α_GaN (7.5e-3 /K) | 2x change moves rate ~12 % | not load-bearing |
| parameter | C4 geometry | P_C4 ≈ 0.74 mW | negligible |
| model-form | H0 homogenisation | −6 to −9 % warpage; +82–97 % local stress | warpage usable; local stress excluded |
| model-form | multilayer RDL, ideal stitching | stitching density unstated by any source | optimistic bound; solver supports finite stitching |
| model-form | explicit VDD + GND networks | exactly 2x only for a symmetric stack | now derived rather than assumed |
| model-form | M0 rung | no assembly pre-stress, no plasticity | no lifetime claim possible |
| boundary | **BC-A vs BC-B** | **warpage suppressed ~20-30x under BC-B** | at 240 W orderings reverse or vanish; **at 1 kW warpage QUALIFIES as a mounted metric** |
| geometry | **HVR cell height (720 µm, was 150 µm)** | **h_sub < 770 µm is unbuildable** | **supersedes every 0B-0E absolute magnitude** |
| boundary | 1-kW cooling calibration | 9.47x the Phase-0B coefficient; DERIVED | sets every 1-kW temperature-dependent loss |
| model-form | top- vs substrate-side cooling | substrate-side cannot reach 84 °C at all | gradient direction, and therefore warpage sign, depends on it |
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

**What Phase 0E added to the novelty case.** Three things, none of which is an optimiser:

* *The footprint mechanism is geometric, not a property of assumed material cards.* Rebuilding
  the tile as a composite from the converter compiler's own component inventory changes the
  footprint warpage sensitivity by 0.06 %. A mechanism that survives replacing its dominant
  PROVISIONAL input is worth publishing; one that does not, is not. This test is only possible
  because the objects being placed are *synthesised*, so their internal composition is known ---
  a chiplet placer has no component inventory to appeal to.
* *A DVPD-specific interconnect result with no placement analogue.* Whether a via field's loss
  scales as $I$ or as $I^2$ depends on the allocation policy, and which rail traverses a given
  tier depends on where conversion sits in the stack. Both are consequences of co-designing the
  converter with the package; neither arises when the power delivery is a fixed input.
* *A worked demonstration that the mechanical half of a DVPD tradeoff can be sourced.* The RDL
  stack, the allocation rule and the provisioning current density all came from the primary
  DVPD literature and were verified against those papers' own derived quantities. That is the
  difference between a tradeoff and an illustration.

**What Phase 0E removed from the novelty case.** The claim that an architecture can be
*eliminated* by a vertical-interconnect feasibility limit. That was the most striking Phase-0D-R
result and it does not survive: ARCH_B is feasible under every source-backed current density,
and the infeasibility came from an unsourced number.

# Publication-Defensible Claims

### Claims that can be made today

1. *In DVPD, converter footprint is simultaneously an electrical design variable (it sets the
   per-layer area budget and hence switch sizing and conversion loss) and a mechanical one (it
   sets the CTE-mismatched inclusion volume and hence package warpage), and the two oppose.*
   **This survives a physically derived material model**: replacing the homogeneous tile with a
   composite built from the converter compiler's own component inventory changes the footprint
   warpage sensitivity from 1.8696x to 1.8685x --- 0.06 %. The effect is geometric rather than a
   property of the assumed moduli, which is precisely what makes it robust.
2. *Regulator count, at constant total footprint and heat, is mechanically inert* (0.02--4 %
   across three counts and two placement families) --- a clean null that constrains how DVPD
   mechanical models should be parameterised.
3. *Power-substrate thickness improves electrical, thermal and mechanical objectives
   simultaneously*, with $w \propto h^{-1.95\pm0.02}$ independent of placement to within
   0.79 pp.
4. *The rail carried by a vertical interconnect --- set by where conversion sits in the stack ---
   changes its loss by ~1960x for fixed transferred power.*
5. *Package distribution loss in DVPD is dominated by lateral RDL spreading, not by TSVs*, and a
   lumped per-millimetre resistance can understate it by ~65x.
6. *A DVPD via field's loss is proportional to current only under a minimum-current-capability
   allocation policy.* When the count is provisioned at `n = ceil(I/I_max)` the field loss
   becomes approximately linear in current; under a fixed-density geometric allocation the same
   field gives the ordinary quadratic law. The linearity is a design policy, not a property of
   TSVs.
7. *At a 0.286 MHz switching frequency, no AC correction to the vertical interconnect is
   required* --- verified in HFSS, which shows loop resistance flat to 0.18 % below the 19.1 MHz
   skin crossover.
8. *A bulk-cylinder resistance understates a real vertical connection by 1.3--2.0x* because of
   current crowding where the via meets its pad.

### Required qualifications on any RDL or loss number

Every RDL magnitude must be quoted **with the stack that produced it** --- for example *"under
the ECTC-2024 sourced RDL stack (10 um Cu, 10/2 um line/space, 2 VDD + 2 GND layers), RDL loss
is X W"*. The bare form *"RDL loss is X W"* is not permitted, because ECTC-2024's own published
loss totals could not be reconstructed from its printed stack and equations. RDL magnitudes are
**provisional values under the sourced stack**, not upper bounds and not design values.

### Claims added by Phase 0F

9. *A DVPD converter's component stack sets a hard lower bound on substrate thickness, and
   that bound can exclude the thicknesses a purely electrical/thermal study would sweep.* The
   selected converter needs 720 um; 200 and 500 um substrates cannot contain it.
10. *At the 1 kW reference the LV-TSV architecture has an INTERIOR electrical optimum in
    substrate thickness while the mechanical preference stays monotone* --- a genuine
    architecture-specific three-domain conflict, costing 0.016 W/um to overrule.
11. *Whether package warpage is usable as a board-mounted design metric is scale-dependent.*
    At 240 W it loses resolution under board restraint; at 1 kW it converges to 0.0 %, holds
    its ordering across nine material corners and separates candidates by 72 %.
12. *Placement ceases to be a design variable at the reference scale* --- 9.4 % compaction
    headroom at 55 % areal utilisation, against 25 % at M = 16.

### Claims that must NOT be made

* That mechanics **changes the optimum**. It does not, and with a pure added objective it
  structurally cannot.
* Any **feasibility** or reliability claim. No source-backed mechanical allowable exists:
  **G2 remains untested because no source-backed mechanical criterion exists.** In particular
  the earlier statement that "no feasibility reversal is reachable at 240 W" is withdrawn --- it
  asserted a negative about a criterion that was never defined.
* That **ARCH_B is infeasible**. That Phase-0D-R verdict is **withdrawn**: it rested on a
  4.8 mA per-via limit with no source. Under both primary sources ARCH_B needs 849 of 7 148
  available vias. The permitted statement is *"ARCH_B is feasible for every source-backed
  current density; it would become infeasible only below about 1e7 A/m2, which is 5--11x below
  the most conservative sourced value."*
* Any **electromigration lifetime** claim. What Phase 0E closed is the *provisioning* current
  density the sources used, not `I_max,reliability`, which remains OPEN.
* Any **absolute** efficiency or warpage number from Phases 0B-0E as a design value: that
  geometry was not buildable. Phase-0F magnitudes rest on a 720 um cell whose GaN and MLCC
  layer heights are still OPEN.
* That **mechanics binds** at 1 kW. No source-backed criterion exists; G2 remains NOT TESTED.
  The epsilon-sweep is **PARAMETRIC CONSTRAINT SENSITIVITY**, not feasibility.
* Any conclusion that depends on the **direction of the through-thickness thermal gradient**.
  June cools from inside the substrate; this model cools from above, and the substrate-side
  boundary cannot even reach the reference junction temperature.
* Any **local stress** result from the homogenised model (+82--97 % error).
* Any **board-mounted** conclusion from the BC-A results --- and note that under BC-B the
  footprint warpage ordering **reverses** while interface shear grows.
\newpage

# Next Steps --- prioritised roadmap

Phase 0E closed the two inputs that blocked Phase 0E entry. What it did **not** close is
whether any mechanical constraint ever becomes active, and that is now the only thing standing
between this project and a defensible synthesis claim.

**CLOSED in Phase 0E**

1. ~~Source the RDL metal stack~~ --- ECTC-2024 Table I, verified against its own derived
   `R'_Heff` on both trace rows.
2. ~~Resolve `I_via,max`~~ --- a source-backed provisioning envelope of 1.0e8--4.0e8 A/m2 for
   copper, self-consistent across independent tiers within each source. ARCH_B is feasible
   throughout it.
3. ~~Independent EM validation~~ --- HFSS, within its valid regime, with Q3D unavailable and
   the reason recorded.
4. ~~Package thermal cross-check~~ --- MOOSE for the RDL operator across three placements under
   one calibration, plus an Icepak package model.
5. ~~BC-B~~ --- run on decisive pairs; the discriminating response changes from warpage to
   interface shear.

**STILL OPEN, in priority order**

1. **A mechanical criterion, or an admission that none exists.** G2 has been untested for three
   phases. Either a source-backed warpage/coplanarity/strain limit is found that matches the
   package state, temperature and measurement definition, or the framework must be reformulated
   with warpage as an $\varepsilon$-constraint whose level the *user* sets --- which removes the
   need for an exchange rate entirely and is probably the honest resolution.
2. **Scale.** At 240 W every warpage number is a few microns and no constraint can bind. The
   June reference is 1 kW into 500 mm2. Whether mechanics matters at all is a question about
   that scale, not about the model.
3. **The tile height inconsistency.** The selected inductor is 500 um tall; the mechanical
   vehicle uses a 150 um tile inside a 200--500 um substrate. The chosen converter does not fit
   the modelled stack. This does not affect trends but it forbids absolute claims.
4. **`I_max,reliability`** --- an actual electromigration study with temperature, lifetime and
   liner conditions. Not retrievable in this environment.
5. **Assembly pre-stress (M1)** and a metrology comparison (shadow moire or DIC).

### Should the synthesis framework be built now?

**No --- but for a different reason than in Phase 0D-R.** Then, two of three inputs were
unsourced. Now the stack and the allocation rule are closed and the footprint mechanism is
validated; what is missing is any evidence that a mechanical constraint *binds*. Building a
constrained optimiser whose constraint never activates would produce the electrical optimum
with extra steps, and would encode an arbitrary exchange rate while doing it.

# PHASE 0F --- 1 kW REFERENCE-SCALE ETM GATE

Scale the validated model to the June 1 kW / 500 mm2 reference and ask one question: **does any
mechanical quantity approach a plausible limit there?** If it does, the synthesis framework has
a subject. If warpage remains microns at 1 kW, then the honest conclusion is that DVPD
thermo-mechanics is a signoff check rather than a synthesis constraint, and the contribution
should be reframed around what Phase 0E actually established --- the sourced stack, the
allocation correction, the rail-dependence result, and the footprint opposition --- rather than
around an ETM optimiser.

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
*Full text retrieved and read in Phase 0E* (the earlier statement that it was unavailable is
corrected). *Used for:* independent confirmation of the RDL copper thickness (10 um).

[5] "Vertical Power Delivery for High Performance Computing Systems with Buck-Derived
Regulators," IEEE ECTC 2024. DOI: 10.1109/ECTC51529.2024.00364
*Full text retrieved and read in Phase 0E* (the earlier statement that it was unavailable is
corrected). **This is the primary source for the Phase-0E physical stack.** *Used for:* Table I
RDL trace stack (t = 10 um, W/S = 10/2 um, 2 P/G layers, R/l = 170 Ohm/m, R'_Heff = 0.046
Ohm/m), the C4 tier geometry (100/70/200 um), the effective-resistance formulation
`N_Hmax = sqrt(A_L)/(W+S)` and `N_Vpref = 2I/(A J)`, and Table II PPDN totals.

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

[10] ANSYS Electronics Desktop 2026 R1 (HFSS, Icepak), licence server restored 2026-09-06.
*Used for:* frequency-domain loop impedance of the P/G TSV structure (HFSS) and an independent
package thermal solution (Icepak). **Q3D Extractor is not licensed on this server**
(`elec_solve_q3d`: no such feature), which is why DC resistance is validated with a conduction
finite-element solver instead.

[11] PyAEDT 1.1.0 (`ansys.aedt.core`), used to drive AEDT headless.

### Parameters with no citation

Closed in Phase 0E and no longer in this list: RDL Cu thickness, metal occupancy, RDL layer
count, C4 geometry, and the per-via provisioning current density.

Still **ASSUMPTION** or **OPEN**, and flagged as such throughout: the electromigration
*reliability* limit `I_max,reliability`; GaN $R_{DS(on)}$ temperature coefficient; the MLCC
ceramic elastic card; mould-compound properties; HVR tile height (the modelled 150 um is
contradicted by the selected 500 um inductor); RDL dielectric stack and inter-layer stitching
density; BC-B foundation stiffness; and any mechanical allowable. No literature value was
fabricated to fill these.
