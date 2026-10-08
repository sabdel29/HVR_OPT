---
title: "Electrothermal--Mechanical Co-Design of Distributed Vertical Power Delivery: Model Development, Falsification Gates, and Coupled Architecture Results"
author: "HVR\\_Journal\\_System\\_Level / ETM-DVPD --- HiPerCAS Lab, University of Illinois Chicago"
date: "2026-09-19"
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
| Report generated | 2026-09-19 |
| Repository baseline | 2026-09-08 |
| Phase completed | 0M-R3, 2026-09-19 |
| Structural + thermal FE |  --- C3D8I, direct SPOOLES |
| Independent FE cross-check | MOOSE `heat_transfer-opt`, build 09515f92aa |
| Full-wave EM available | **PALACE NOT FOUND on this system (measured Phase 0M-R3).** Earlier phases recorded it as built and functional; it is not present now and nothing current depends on it |
| Commercial EM/thermal | ANSYS AEDT v261, **licence restored 2026-09-06**; HFSS and Icepak used, Q3D not licensed ; Fluent NOT INSTALLED |
| Mesh generation | gmsh 4.15.2 |
| Python | 3.12.14 |
| Document build | pandoc + xelatex |

**Reading guide.** Every table below is generated programmatically from the source artifact
named beneath it; no numerical result was retyped. **Section 7 (Phase 0D-R) supersedes
Section 6 (Phase 0D) wherever they disagree**, and each disagreement is stated explicitly.

\newpage

<!-- BEGIN GENERATED: exec_summary -->

# Executive Summary

**Original hypothesis.** Distributed vertical power delivery is normally optimised on electrical
and thermal grounds alone. This project asked whether package thermo-mechanics -- warpage and
stress -- is a SYNTHESIS constraint that changes which DVPD architecture one would choose,
rather than a downstream signoff check.

**Answer.** No, on the evidence available. Phases 0G through 0I find a real, sign-stable, cross-
validated mechanical RESPONSE to the electrical design variables -- now including a resolved,
architecture-dependent SOLDER-FATIGUE response -- and no admissible inequality anywhere that
could turn any of it into a constraint. Phase 0H tested nine candidate thresholds against six
admissibility conditions and admitted none. Phase 0I then added vertical placement as a genuine
design variable and a temperature-dependent elastic/plastic/creep joint model, and Phase 0I-R
verified that model's response metric; in that HISTORICAL architecture set the architectures
separated by -35.8 % and +12.4 % in per-cycle inelastic strain, at 5.8x and 5.1x their
uncertainty. The CURRENT repaired realizable pair separates by 16.3 %. What is still missing is
not the response but the THRESHOLD. Phase 0J searched for a life law and a required life and
found neither, recording ACCESS as the cause. The primary calibration papers were then supplied,
and Phase 0J-R closes half of that gap: four SnAgCu formulations are admitted for RELATIVE life,
Syed 2004's author-corrected calibration is reproduced, its 25 um averaging volume is matched,
and Z2 shows the lower response under all four. That is an ORDERING of a response metric, not a
lifetime; a survival claim is not earned while absolute N_f is unvalidated. Phases 0L and 0L-R
then audited the constitutive model under that result and found it fitted in the wrong stress
variable, on a different alloy, and evaluated far outside its source window. The ORDERING
survives all of that for a structural reason; its MAGNITUDE is a conditional envelope of 1.19 to
1.22, not a validated number. ABSOLUTE life stays conditional and NO required life exists.
Mechanics is design-relevant as a response model, with a robust RELATIVE ordering and a
conditional magnitude, and is still not a feasibility-set restriction.

**Method.** Twenty-one sequential falsification gates (0B, 0C, 0D, 0D-R, 0E, 0F, 0G, 0H, 0I,
0I-R, 0J, 0J-R, 0K, 0K-R, 0L, 0L-R, 0M, 0M-R, 0M-R2, 0M-R3, 0M-R3A), each designed so that a
negative result would stop the project rather than be absorbed. No gate was allowed to pass on a
metric that failed mesh convergence, and no mechanical allowable was ever chosen after seeing
results. From Phase 0H onward every automated guard must also be shown to FAIL on an injected
violation before it is trusted.

**What survived.**

* Mechanics responds strongly to architecture: die warpage spans 1.8-15.6 um across the frozen 20-case DOE at fixed load, footprint and heat (Phase 0C).
* Substrate thickness is a genuine three-domain variable and the electrical and mechanical preferences OPPOSE: electrically thinner is better (ARCH_B monotone in 9 corners of 9), mechanically thicker is better (S_h = -0.039 to -0.886 in the free package and all five explicit boards). Over the realizable band the trade is 4.04 W of ARCH_B loss against 29.3 % of mounted warpage. The thickness trend is PRESERVED in the M2-rung solder metrics and is smaller there than in global warpage: across all eleven z-sweep points it is monotone in every architecture, -5.6 % (Z1), -6.1 % (Z2) and -17.2 % (Z4) in accumulated inelastic path, against 29.7-52.6 % in warpage over the same range, so warpage overstates the benefit by 3-5x. The superseded Phase-0H figure of 1.96 %, which belonged to the REJECTED smeared interface-shear proxy and sat 7x below that proxy's own uncertainty, is withdrawn as a current result and is retained only in the Phase-0H historical section.
* The GaN device heights are now SOURCED from manufacturer datasheets -- 685 um high side, 606 um low side -- against the 0/100/250 um envelope earlier phases invented.
* COMPONENT-HEIGHT REALIZABILITY IS ARCHITECTURE DEPENDENT. Component height constrains substrate thickness only where the converter is EMBEDDED (h_sub >= 1.276 mm). Where it sits below, above or beside the substrate, nothing it contains constrains h_sub and the bound falls to the source-demonstrated 0.300 mm TSV layer -- a 4.3x wider range.
* Vertical integration is a real architecture variable with a measurable reliability consequence, and the effect is RESOLVED against uncertainty. On the CURRENT repaired realizable pair (Phase 0M-R3) the backside architecture carries 16.3 % LESS local fatigue-relevant inelastic RESPONSE than the embedded one, at D_driver = 1.1943. The often-quoted 35.8 % and 12.4 % figures are the HISTORICAL Phase-0I result for a different, non-realizable architecture set and must not be presented as the present architecture result. All three inelastic measures -- accumulated path length, strain range and dissipated energy -- give the same ranking. The quantity is a RESPONSE, not damage: a damage law, a life model and an admissible allowable are all still OPEN.
* Temperature-dependent failure physics materially changes the answer, but the SIGN of the change depends on which inelastic measure is used, and Phase 0I-R makes that explicit. Against a no-creep model the STRAIN-based metric falls 29.8 % while the DISSIPATED INELASTIC ENERGY rises 164.6 % over the same solves. Creep relaxes stress and suppresses plastic strain accumulation, yet deforms at sustained stress and so dissipates far more. Neither number may be quoted as `damage decreased` without naming the measure. The Phase-0I -27.2 % figure is valid ONLY as a statement about the strain-based metric.
* Temperature enters the damage physics through more than thermal expansion: a temperature-INDEPENDENT model moves only -0.2 % as the cycle mean shifts 25 to 75 C, while the full model moves +22.7 %. The older model class was structurally blind to where in temperature a cycle sits.
* Under the PHYSICAL cooler the Z-architectures DO separate in temperature, and ARCH_Z2 is the hottest of the principal candidates: on the CURRENT repaired realizable pair, 126.91 C against 118.68 C for ARCH_Z1. It nevertheless carries 16.3 % LESS corner-joint driver. Under the retired calibrated boundary the joint temperatures spanned only 81.10-83.21 C and their correlation with damage was r = +0.017, which is why earlier phases described these architectures as separating on mechanics alone; that statement is historical and belongs to that boundary condition. Ranking by package T_max is NOT equivalent to ranking by the solder-fatigue driver, because geometry- and CTE-induced deformation and the local constitutive response are distinct mechanisms. Temperature-dependent physics matters and must not be dismissed.
* The physical metal stack is sourced, not assumed: 10 um Cu, 10/2 um line/space, 2 VDD + 2 GND layers from ECTC-2024 Table I, whose own derived quantities the model reproduces to better than 2 %.
* No AC correction is needed at the switching frequency -- HFSS shows loop resistance flat to 0.18 % below the 19.1 MHz skin crossover, with f_sw two orders below it.
* The rail carried by a vertical interconnect changes its loss by ~1960x for fixed transferred power, and which rail it carries is architecture-specific.
* A via field's loss is proportional to current only under minimum-capability provisioning; under geometric allocation the same field obeys P ~ I^2.
* The model chain is numerically sound: energy balance closes to +-0.000 %, warpage is mesh-converged to 0.50 %, and an independent solver (MOOSE) reproduces candidate ordering at both 240 W and 1 kW.

**What failed.**

* Regulator count is mechanically inert (+0.02 % for 4->6, -4.07 % for 4->8), which killed the variable the original novelty argument leaned on.
* Tile aspect ratio is inert (-1.76 %), and on this square vehicle the two aspect cases are provably identical by symmetry.
* Interface peel never converged (19-20 % per refinement against a <10 % target) and is excluded from all decision logic.
* The geometry used by Phases 0B-0E was not buildable: the selected converter needs a 720 um cell and the mechanical vehicle used a 150 um tile inside 200 or 500 um substrates. Trend DIRECTIONS survive re-running on realizable geometry; every absolute magnitude from those phases is superseded.
* The Phase-0B cooling calibration was not transferable -- at 1 kW the correct film coefficient is 9.47x larger.
* Substrate-side-only cooling, which is the reference system's actual topology, cannot reach the reference junction temperature at 1 kW: it floors at 90.96 C and reaches 110.4 C at h_sub = 2.00 mm.
* The compact BC-B foundation is not a valid model of a mounted package. It clamps all three degrees of freedom, never recovers its own free limit (0.739 um against 8.287 um on the identical mesh), and no support stiffness k* exists over seven decades.
* DEFECT #30: per-regulator and system-wide loss terms were summed together for three phases, understating every vertical tier by n_vr -- 49x at the 1 kW reference. It inverted the Phase-0F architecture conclusion and survived a 25x tighter convergence tolerance.
* DEFECT #31: the semantic ledger built to catch stale claims could not fail, because its exonerating vocabulary matched ordinary English prose within a +-800-character window.
* DEFECT #32: the single source of truth controlled the claims ledger but not the Executive Summary, governing equations, validation status, novelty, limitations, publication claims or next steps. Seven current-facing statements were stale behind a green build.
* Global warpage does not predict local interconnect loading (Spearman 0.112 over 70 paired runs) and inverts sign between assembly states (-0.793 free, +0.349 mounted). The quantity the project measured best is not the quantity that matters.
* Of eight enumerated failure mechanisms, TWO are now computable and SIX are not. Global bending is computable at M0 but is a driver, not a failure. Solder fatigue became computable at M2 in Phase 0I, was verified in Phase 0I-R, and Phase 0J-R admitted four primary-source SnAgCu life laws for it -- so it now yields a ROBUST RELATIVE ORDERING with a CONDITIONAL magnitude, though still no pass/fail: absolute life is model-form uncertain at 4.1x and no required life exists. mechanisms the reference paper itself names -- RDL shear and delamination -- which are absent from the mechanical model entirely.
* No admissible mechanical criterion exists. Nine candidates, zero admitted; every published warpage allowable located is a manufacturing or solderability limit.

**Current strongest novelty.** The defensible contribution is NOT 'mechanics changes the
optimum' -- it does not, and with a pure added objective it structurally cannot. It is an
AUDITED CROSS-DOMAIN DVPD MODEL AND A FALSIFICATION SEQUENCE that establishes where mechanics is
and is not design-relevant: physical-realizability coupling that excludes an entire previously-
swept design range; rail-aware interconnect modelling; corrected RDL / bump / TSV losses with
explicit allocation policy; an electrothermal fixed point with per-regulator local temperature;
a mounted package-mechanics model that is continuous with its own free limit; a demonstrated
thickness response opposition; and the negative result that footprint opposition disappears once
the package is actually mounted.

**Current limitations.**

* No admissible mechanical criterion exists, so G2 is NOT TESTED and no mechanical term may enter a feasibility test. Phase 0I supplies the METRIC half of G2 -- convergent, validated, tied to a documented failure mechanism. Phase 0J-R then supplied part of the ALLOWABLE half: four primary-source SnAgCu formulations are ADMITTED FOR RELATIVE LIFE, Syed 2004's author-corrected calibration was reproduced, and its 25 um averaging volume was matched. ABSOLUTE life remains CONDITIONAL -- the strain- and energy-based models disagree 4.1x on this joint, whose w_acc/eps_acc sits 4.3x off the calibration locus -- and NO required life exists. The Phase-0J statement that no SAC305 life law was retrievable is SUPERSEDED: it was an ACCESS limitation and the primary papers have since been supplied.
* THREE DIFFERENT THINGS, AND THEY MUST NOT BE CONFLATED. (1) THE RELATIVE ORDERING IS ROBUST: Z2 accumulates less local fatigue-relevant inelastic RESPONSE than Z1 under every admitted constitutive model, every admitted life law, every profile and all three response metrics. The FE quantity is a response; calling it damage would presume a sourced damage law that does not exist. It originates in the GLOBAL thermoelastic model, which imposes a 32 % larger corner shear on Z1 and contains no solder law at all: the global package supplies a constitutive-law-independent deformation driver favoring Z2, and every presently testable constitutive/life-law combination preserves that ordering. (2) THE MAGNITUDE IS CONDITIONAL, NOT VALIDATED: the strain-family envelope is 1.19 to 1.22 at the operating baseline, conditional because 99.8 % of the joint's damage is generated above the 7.51-15.92 MPa window the creep law was fitted in, on Sn3.9Ag0.6Cu rather than SAC305. The permitted wording is 'conditional relative-life envelope'; 'validated relative life' is NOT earned. (3) ABSOLUTE LIFE AND REQUIRED LIFE REMAIN OPEN -- the strain and energy formulations disagree 4.1x on this joint, and no field or product requirement exists anywhere in this repository.
* Two of eight failure mechanisms are now addressable: global bending (a driver) and solder fatigue (a real mechanism, added in Phase 0I). RDL damage, delamination, CPI and TSV interaction still need geometry or physics the model does not have, and two of those are mechanisms the reference paper itself names.
* The reliability submodel is displacement-driven and models one joint at the worst location. Its creep law is a variable-consistent SnAgCu Norton surrogate, high-stress extrapolative: fitted over 7.51-15.92 MPa on Sn3.9Ag0.6Cu, while the joint's damage-weighted median stress is about 82 MPa and 99.8 % of its damage lies outside that window. Two constitutive FAMILIES can be parameterised there and only one can be integrated, because this solver fails above a Norton exponent of 9 to 10.
* The two PHASE-0H local proxies remain unfit for decisions: smeared interface shear is non-monotone under mesh refinement (7.6 % spread) and relative displacement carries 26.5 % spread from an unsourced underfill modulus. THEY ARE NOT THE CURRENT METRIC. The Phase-0I M2 metric replaces them and passes mesh convergence (1.90 %), creep- tolerance insensitivity (0.02 %) and corner-regularisation stability (6.4 %).
* MLCC height remains OPEN -- Murata is not retrievable in this environment -- so the realizable substrate bound is a 250 um band rather than a number.
* Mounted warpage magnitudes (9.7-29.2 um) are an engineering envelope from an assumed board, not a prediction. Only signs and orderings are claimed.
* All warpage is INCREMENTAL OPERATIONAL with a 25 C stress-free reference. Assembly pre-stress is bounded, not modelled: a 175 C reference raises mounted magnitudes by up to 54 %.
* GaN device height is SOURCE_BACKED (manufacturer datasheets, Phase 0H). MLCC height remains OPEN. Complete packaging clearance for the thinnest non-embedded stack is OPEN: 0.300 mm is COMPONENT-HEIGHT-REALIZABLE under the current Z-architecture model and a source-demonstrated TSV-layer thickness, NOT a manufacturability guarantee.
* The electromigration reliability limit for copper TSVs is open; what is closed is the provisioning current density the sources actually used.
* ECTC-2024's absolute loss magnitudes are not reproducible from its printed model, so RDL magnitudes are always quoted with their stack.
* Q3D Extractor is not licensed, so DC resistance is validated with a conduction FE rather than a commercial extractor. Icepak returned a clamped 5000 K solution on this package model and is unusable.
* Interface peel is excluded for non-convergence; interface shear converged but has no allowable.

**Exact next work.** Phase 0M-R3A is the current authoritative phase and its ranked follow-up is
in results/phase0mr3a/final_open_items.md. In order: (1) source a process rule for the INTRA-
CONVERTER VERTICAL INTERCONNECT, which DEFECT #58 showed has none and on which the routing
repair depends; (2) source the three package clearances; (3) close the ARCH_Z2 TSV process
margin at 32 um, the smallest evaluated diameter with positive margin, which costs 12.5 % FEWER
vias rather than more; (4) high-stress SAC305 characterisation, still the dominant blocker on
every absolute reliability number; (5) the canonical conjugate CFD benchmark. Adopting the
physical cooling model into the ETM loop and putting the RDL into the production thermal model
are COMPLETE, in Phases 0M-R and 0M-R2 respectively, and are not future work. G2 remains NOT
TESTED behind three independent blockers; the optimizer remains FORBIDDEN.

<!-- END GENERATED: exec_summary -->
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

# Phase 0F --- 1-kW Reference-Scale ETM Gate (superseded by Phase 0G)

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
  n_{req} \le n_{alloc} \le n_{avail}, \qquad
  R_{field} = \frac{R_{single}}{n_{alloc}}, \qquad
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
| $n_{req}, n_{alloc}, n_{avail}$ | required / **allocated** / available parallel conductors. Resistance uses $n_{alloc}$; feasibility uses $n_{avail}$ | -- |
| $\mathbf K, h, T_\infty$ | conductivity tensor, film coefficient, sink temperature | W/mK, W/m$^2$K, $^\circ$C |
| $\mathbf C, \boldsymbol\alpha, T_{ref}$ | stiffness tensor, CTE, stress-free temperature | Pa, 1/K, $^\circ$C |
| $w_{pv}$ | peak-to-valley warpage | m |
| $S_m, u_m$ | architectural spread, numerical uncertainty | -- |
| $J$ | area-budget current density target ($A_{budget}=I_{out}/J$) | A/mm$^2$ |
\newpage

<!-- BEGIN GENERATED: governing_equations -->

## Governing-equation status

| # | equation | status | note |
|---|---|---|---|
| 1 | `n_req = ceil(I / I_max); n_req <= n_alloc <= n_avail; R_field = R_single / n_alloc` | **CURRENT** | Phase 0E separated three quantities that Phase 0D-R had conflated into one. Electrical resistance uses n_ALLOCATED, which is what the design actually instantiates. Using n_req makes P ~ I look like a physical law when it is an allocation policy. **Superseded form:** `R_field = R_single / n_req (Phases 0D, 0D-R)`. |
| 2 | `infeasible if n_req > n_avail(A_fp, pitch)` | **CURRENT** | Unchanged. Feasibility is set by what the footprint can physically hold, not by what the allocation policy chose. |
| 3 | `sigma = C(T) : (eps_total - eps_thermal(T) - eps_in); eps_dot_in = A(T) * (sigma_vm - sigma_y(epsbar_in))**n(T) for sigma_vm > sigma_y, and eps_dot_in = 0 identically otherwise; m = 0` | **CURRENT** | CORRECTED IN PHASES 0L AND 0L-R. The earlier form eps_dot_cr = A(T) sigma^n(T) is WITHDRAWN: it is NOT what a *VISCO step executes. The solver drives creep with the OVERSTRESS sigma_vm - sigma_y and returns exactly zero below yield, traced in CalculiX 2.23 src/incplas.f and confirmed to 1.2e-5 over 7603 probe increments. There is NO rate-independent plastic strain in a *VISCO step. A(T), n(T) come from 19 creep points on Sn3.9Ag0.6Cu -- NOT SAC305 -- fitted over 7.51-15.92 MPa against TOTAL APPLIED STRESS, which is not the variable the solver consumes (DEFECT #40). The selected model M1 removes the yield threshold so that fit and solver share a variable; it is labelled a variable-consistent SnAgCu Norton surrogate, high-stress extrapolative, and 99.8 % of the joint damage is generated outside its fitted window. A(T) and n are interpolated LINEARLY between card rows by the solver, not by Arrhenius; any Arrhenius relation exists only in how the row values were generated. |
| 4 | `d_eps_in(cycle k) = PEEQ(t_end,k) - PEEQ(t_end,k-1), volume-averaged over the solder core with a one-element corner exclusion band` | **CURRENT** | PEEQ is CalculiX's ACCUMULATED equivalent inelastic strain. Phase 0I-R proved by experiment that it includes BOTH plastic and creep: with a creep-only material and no *PLASTIC card, PEEQ / eq(eps_inelastic) = 1.0000. The metric is therefore the inelastic PATH LENGTH traversed per cycle, not a strain RANGE; the two differ by a factor of 3.72 here and the naming is fixed accordingly. |
| 5 | `the stabilised cycle is the first whose d_eps_in differs from the previous cycle by less than 5 %; reported values are from cycle 4 of 4` | **CURRENT** | Achieved 0.48-2.00 % cycle-to-cycle change at cycle 4 for every architecture. The metric is a per-cycle DIFFERENCE of an accumulated quantity, so it is not contaminated by total accumulated creep. |
| 6 | `NONE` | **AVAILABLE_FOR_RELATIVE_LIFE_ONLY** | SUPERSEDED BY PHASE 0J-R. The Phase-0I statement that no exponent is sourced no longer holds: two primary sources now bound it -- Syed 2004 derives -1 theoretically and measures -0.9607, and Schubert 2003 fits -1.3 for SnAgCu. C still cancels in a ratio. That is necessary but NOT sufficient: Phase 0L-R shows the response metric the law consumes is itself produced by an extrapolated constitutive model, so the RELATIVE ORDERING is robust while the MAGNITUDE is a CONDITIONAL envelope of 1.19 to 1.22. 'Validated relative life' is WITHDRAWN. What is also NOT current is an ABSOLUTE lifetime equation: the strain and energy formulations both have constants but disagree 4.1x on this joint. |
| 7 | `P_tier,SYSTEM = n_vr * P_tier,PER_REGULATOR; P_PDN = sum over tiers of SYSTEM-scope terms only` | **CURRENT** | Phase-0H structural guard for DEFECT #30. vertical_tier_per_regulator() returns a PER_REGULATOR quantity and rdl_network_solve() returns a SYSTEM quantity; adding them raises ScopeError. Negative-tested in tests/phase0h/test_scope.py. |

Symbols required by the current forms and therefore mandatory in the symbol table: `n_alloc`,
`n_avail`, `n_req`.

<!-- END GENERATED: governing_equations -->

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
correct. **No AC current-crowding correction is applied**, because none is demonstrated at this frequency --- introducing an empirical factor without evidence is precisely what the brief forbids. A **DC** transition resistance IS applied: since Phase 0M-R each interconnect class carries its own `Delta_R = R_3D - R_1D`, solved exactly at its production geometry and cross-validated against MOOSE on five geometries at 0.25-0.73 %. The single global 1.326 multiplier that preceded it is retired from every production path. `Delta_R` is a difference against a stated 1-D reference, not an excess, and at the nominal TSV geometry it is negative.

# Thermal Model Validation

**Production cooling boundary (Phase 0M-R, regime-audited in Phase 0M-R2).** The production ET loop no longer uses the inverse-calibrated Robin coefficient `h_top = 166 000 W/m2K`; that value is retained only as Phase-0B/0F historical context. The boundary is now a physical microchannel cooler: `h` from a regime-checked Nusselt correlation for the duct, corrected by fin efficiency and area amplification, a caloric resistance `1/(2 m_dot c_p)`, and a streamwise coolant temperature iterated to a fixed point against the wall flux. At the production flow of 27 g/s the channel is laminar at Re = 1264.8, inside the correlation's validated domain. The solid side is cross-validated against MOOSE with explicit fins: 2 of 4 geometries ACCEPTED, 1 CONDITIONAL at 6.04 %, 1 REJECTED at 10.11 %, with the production geometry in the accepted band at 3.78 %. Phase 0M-R2 additionally found that the 50 g/s operating point Phase 0M-R quoted lies at Re = 2342, between the laminar ceiling of 2300 and Gnielinski's floor of 3000, where no validated correlation exists; the numbers derived from that point are withdrawn. Conjugate CFD validation is reported separately in `results/phase0mr2/CONJUGATE_CFD_VALIDATION.md`.


* **Energy conservation.** Robin flux integrated over both cooled surfaces equals the injected
  power to $\pm 0.000$ % on every run in every phase --- an independent check, not a solver
  residual.
* **Cooling calibration.** $h_{top}$ secant-solved to the June-2026 cooled baseline: 83.514
  $^\circ$C against 84 $^\circ$C, residual $-0.49$ K, then frozen.
* **Mesh convergence.** $T_{max}$ changed 0.29 % (thin substrate) and 0.18 % (thick) over the
  final refinement step.
* **Conduction operator validated against MOOSE** to 5.8e-12 % on an analytic case.

**Done in Phase 0E, and no longer open.** The full 3-D MOOSE package cross-check with
spatially mapped Joule heat was completed as TH-1...TH-5: candidate ordering preserved exactly,
maximum discrepancy 1.66 %, mean 1.05 %. Phase 0F repeated it at the 1-kW reference on the
decisive thickness pair (2.2--2.8 K on $T_{max}$, same thickness trend, energy balance closed to
$3\times10^{-8}$ % in both codes). Icepak remains unusable: it returned exactly 5000 K on every
object, a solver clamp from applying an external boundary condition to an internal solid/air
interface, and that result was discarded.

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
  BC-B applies `*BOUNDARY {n},1,3` --- **all three degrees of freedom** on the
  underside plane --- so it is a CLAMP, not a compliant mounted support. Phase 0G withdrew it
  as a model of a mounted package: it never recovers its own free limit (0.739 um against
  8.287 um on the identical mesh) and no support stiffness $k^*$ exists over seven decades.
  Mounted conclusions use BC_BOARD, an explicit BGA + PCB stack restrained only by 3-2-1
  anchors, which is continuous with the free package.
* **Homogenisation.** Valid for warpage (spread preserved to 1.7 pp, absolute bias $-6$ to
  $-9$ %); **invalid for local stress** ($+82$ to $+97$ %).
* **Known limitations.** This section covers the **GLOBAL** package model only, which is
  linear thermoelastic at operational load with no assembly pre-stress and no plasticity,
  creep or fatigue. It is **not** the whole mechanical model: a separate **LOCAL** joint
  submodel carries the viscoplastic constitutive law and the fatigue response, and is
  validated on different axes --- numerically converged and solver-implementation verified,
  but conditional on source data and failing on domain. See the five-axis validation matrix
  in the current-framework audit report. **No ANSYS structural validation exists.**
\newpage

<!-- BEGIN GENERATED: validation_status -->

## Validation status

| domain | status | validated | not validated |
|---|---|---|---|
| electrical | **SUPPORTED** | Multilayer RDL sheet model agrees with an independent MOOSE conduction solve to 0.45-1.10 % on power across three placements under one calibration. HFSS confirms no AC correction is needed below the 19.1 MHz skin crossover. | Q3D Extractor is not licensed, so no commercial-extractor cross-check of DC resistance exists. |
| thermal | **PROVEN** | Full 3-D MOOSE package thermal cross-check COMPLETED. Phase 0E ran TH-1..TH-5 with spatially mapped Joule heat: candidate ordering preserved exactly, maximum discrepancy 1.66 %, mean 1.05 %. Phase 0F repeated it at the 1-kW reference on the decisive thickness pair: 2.2-2.8 K on T_max, same thickness trend, energy balance closed to 3e-8 % in both codes. | Icepak remains unusable -- it returned exactly 5000 K on every object, a solver clamp from applying an external boundary condition to an internal solid/air interface. That result was discarded and is never used. |
| mechanical | **SUPPORTED** | Analytic free-expansion check exact; four graded mesh levels with die warpage converged to 0.50 %; BC-A reaction forces <= 4.3e-10 N, so the constraint manufactures no stress; the explicit BGA + board assembly is continuous with the free package (+18.1 % with a vanishing board, the residual being the BGA layer's own contribution). | No ANSYS structural validation exists. No assembly pre-stress model, no fracture mechanics, no cohesive zone. |

**Restraint models.** BC-A is 3-2-1 rigid-body suppression. BC-B applies *BOUNDARY {n},1,3 --
ALL THREE degrees of freedom on the underside plane -- so it is a CLAMP and NOT a compliant
mounted support; Phase 0G withdrew it as a model of a mounted package. BC_BOARD is an explicit
BGA + PCB stack restrained only by 3-2-1 anchors and is the model used for mounted conclusions.

<!-- END GENERATED: validation_status -->

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

**Current position (Phase 0M-R3A).** Under the physical cooler the architectures DO separate in temperature. On the CURRENT repaired realizable pair ARCH_Z2 runs 126.91 C against ARCH_Z1's 118.68 C, so ARCH_Z2 is the hotter of the two principal candidates and still the better of them on the local fatigue-relevant inelastic RESPONSE. ARCH_Z4's 98.83 C is the Phase-0M-R2 figure, for a power-die construction that remains unsourced. The tables below this note are the Phase-0I/0M record and are retained as such.

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

# Positive Results (historical record --- Phases 0B..0D-R)

> **This section is a historical record, not a statement of current status.** Several claims below were superseded in Phases 0E, 0F and 0G --- notably *win/win/win substrate thickness* (the swept thicknesses are unbuildable) and *HVR footprint is a genuine ETM opposition* (the sign is assembly-state dependent and reverses on every explicit board). For what this project currently claims, see **Current scientific status** below, which is generated from `results/CURRENT_SCIENTIFIC_STATUS.yaml`.

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

# Negative and Null Results (historical record --- Phases 0B..0D-R)

> **This section is a historical record, not a statement of current status.** Items 4, 5 and 6 were superseded in Phases 0E and 0G: the placement spread is 46.7 % and not 188.8 %, the footprint exchange rate is 11.48--12.86 W/um and not 16.2 W/um, and an architecture-dependent thickness difference does appear at 1 kW once DEFECT #30 is fixed --- though not as the interior optimum Phase 0F reported. See **Current scientific status** below.

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

**Scope of this section.** The table below is the Phase-0B..0F record. Defects 26 onward are carried in the generated current-status section near the end of this report, where each row states its status AT DISCOVERY together with the phase that superseded it. Two are worth naming here because they were current-facing for several phases: **DEFECT #51**, intra-VR routing modelled but not summed, CLOSED IN PHASE 0M-R, which put it into the production loss ledger as `P_intraVR_metal` and `P_intraVR_vertical`; and **DEFECT #52**, the calibrated cooling boundary, CLOSED IN PHASE 0M-R, which placed a physical microchannel cooler in the production ETM loop and whose correlation domain Phase 0M-R2 then audited.


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

**PROVEN (as stated at Phase 0D-R --- superseded in part; see Current scientific status)**
--- architecture changes warpage 8.5x; thickness is win/win/win with
$w\propto h^{-1.95}$; count and aspect ratio inert; footprint opposition; RDL dominates
distribution loss; the model chain is numerically sound and MOOSE-validated. Of these,
*win/win/win thickness* and *footprint opposition* are superseded by Phases 0F and 0G.

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


<!-- BEGIN GENERATED: reliability_metric -->

## The local reliability metric, exactly defined

| field | value |
|---|---|
| **name** | d_eps_in -- accumulated equivalent inelastic strain per stabilised cycle |
| **exact definition** | d_eps_in(k) = PEEQ(t_end of cycle k) - PEEQ(t_end of cycle k-1), volume-averaged over the solder core with a one-element corner exclusion band: d_eps_in = sum_e(d_PEEQ_e * V_e) / sum_e(V_e) |
| **units** | dimensionless (strain) |
| **solver output** | CalculiX 2.23 PEEQ from *EL PRINT. CEEQ, CE and PE are aliased to PEEQ by the solver; no separate creep field is produced. |
| **plastic component** | INCLUDED |
| **creep component** | INCLUDED |
| **creep verification** | PROVEN BY EXPERIMENT, not inferred. With a creep-only material and NO *PLASTIC card in the deck, PEEQ is non-zero and PEEQ / eq(eps_inelastic) = 1.0000. The identity holds in four single-element probes and, at the first output, in the multiaxial temperature-varying joint (1.0029-1.0035). |
| **is a range** | False |
| **range clarification** | PEEQ is an ACCUMULATED path length, not a state, so the per-cycle difference is the inelastic PATH LENGTH traversed in one cycle, NOT a strain range. At stabilisation the ratio path-length / range is 3.72, not the 2.0 a fully-reversed uniaxial cycle would give, because the OFF-ON-OFF cycle is a multi-reversal path in strain space. Any future life law must be matched to the path-length form or the metric converted. |
| **stabilized cycle definition** | the first cycle whose d_eps_in differs from the previous cycle by less than 5 %; all reported values are cycle 4 of 4, achieved at 0.48-2.00 % |
| **numerical status** | CONVERGENT -- mesh 1.90 % over the final refinement, creep tolerance 0.02 %, corner-exclusion band 6.4 % across 0-2 elements. Including the corner LOWERS the value, so the metric is not corner-dominated. |
| **metric agreement** | The architecture ranking and magnitudes are the SAME under all three inelastic measures -- accumulated path length, instantaneous strain range, and dissipated inelastic energy -- to within 2 pp (Z2 -35.8/-35.7/-37.7 %, Z4 +12.4/+12.6/+13.0 %). The architecture conclusion therefore does not depend on the choice of measure. |
| **metric disagreement** | The CREEP-INCLUSION question DOES depend on the measure: enabling creep moves the strain metric -29.8 % and the energy metric +164.6 %. Direction-of-change statements must always name the measure. |

### Relative life

**PARAMETRIC LIFE-LAW SENSITIVITY -- NOT A LIFETIME PREDICTION.** `N_f = C * d_eps_in^(-m);
N_f,2/N_f,1 = (d_eps_in,1 / d_eps_in,2)^m`

- The constant **C cancels** in a ratio: `True`.
- The exponent **m does NOT cancel**: exponent required = `True`, status = **SOURCED AS OF PHASE 0J-R -- was UNSOURCED in Phase 0I-R. Syed 2004 derives -1 from Monkman-Grant plus a time-fraction rule and measures -0.9607; Schubert 2003 fits -1.3 for SnAgCu. The exponent is bounded, not free.**.
- *Provenance:* Phase 0I annotated a figure with 'typical solder k is 1.5-3'. That range was written from general knowledge, appears in no retrieved source, and was never labelled. It WAS the sole basis of the Phase-0I headline '1.9-3.8x relative life'. SUPERSEDED: Phase 0J-R obtained the exponent from two primary sources, so the Phase-0I parametric span (m = 0.5-5, ratio 1.25 to 9.18) is withdrawn.
- *Correction:* Phase 0I said relative life is 'parameter-free in the life-law constant'. That is literally true of C and MISLEADING as written, because it invites the reading that the ratio is parameter-free. It is not: the exponent m does not cancel. Over m = 0.5 to 5 the Z2/Z1 ratio spans 1.25 to 9.18 -- a factor of 7.4 from the exponent alone.
- *What may be claimed:* the METRIC ratio, which is a model output: Z2 is 35.8 % below Z1 and Z4 is 12.4 % above it. Any conversion to life must be labelled parametric in m.

### Architecture claim closure

| architecture | component height | electrical | local damage |
|---|---|---|---|
| **z1_embedded** | CONSTRAINED -- the LS GaN, flying capacitor and inductor occupy the substrate power layers. h_sub >= 1.276 mm at MLCC nominal (a 250 um band, MLCC OPEN). | BASELINE | BASELINE, d_eps_in = 6.513e-3 |
| **z2_backside** | NOT CONSTRAINED by converter component height. COMPONENT-HEIGHT-REALIZABLE under the current Z-architecture model down to 0.300 mm, the source-demonstrated TSV-layer thickness. Complete package manufacturability at 0.300 mm is OPEN. | RESOLVED -- +1688 mW against a 282 mW combined uncertainty, 5.98 sigma. Driven by carrying 1000 A rather than 23.4 A on the via field. | RESOLVED -- -35.8 % against a 6.2 pp spread across all material, mesh and regularisation perturbations (5.8x). Same sign and magnitude under all three measures. |
| **z4_power_die** | NOT CONSTRAINED. COMPONENT-HEIGHT-REALIZABLE down to 0.300 mm; complete package manufacturability OPEN, and its 1.23 mm power die sits in the die-to-cooler thermal path. | UNRESOLVED -- the +30 mW difference from Z1 is 0.024 % of the total and is dwarfed by a term the electrical sweep set to zero: every architecture was evaluated at a FROZEN T_c = 85.0 C, yet the global model shows Z4 running 1.444 K COOLER than Z1. At dP_conv/dT = 148 mW/K that is 214 mW -- 7.1x the claimed difference, and of the OPPOSITE sign. 0.14 sigma. Z1 AND Z4 ARE ELECTRICALLY INDISTINGUISHABLE AT CURRENT FIDELITY, and Z1 MUST NOT be described as electrically preferred. | RESOLVED -- +12.4 % against a 2.4 pp perturbation spread (5.1x). |
| **z5_lateral** | NOT CONSTRAINED. | THE TESTED TOPOLOGY IS ELIMINATED -- 768.07 W of modelled RDL loss, 52.8 % efficiency. This is NOT a statement about 2.5D as a class. | -- |

<!-- END GENERATED: reliability_metric -->
<!-- BEGIN GENERATED: publication_claims -->

## Publication-defensible claims

* Physical realizability is a first-class DVPD design coupling: the converter component stack sets a hard lower bound on substrate thickness that excluded the entire range swept in Phases 0B-0E.
* The rail a vertical interconnect carries changes its loss by ~1960x at fixed transferred power, and it is architecture-specific.
* Via-field loss scaling is set by allocation policy, not by physics alone.
* An electrothermal fixed point with per-regulator local temperature is required at kilowatt scale; a single global T_max is not adequate.
* The mechanical thickness response opposes the electrical one, with a sign that is stable across 20 combinations of assembly model, stress-free reference and thermal boundary.
* NEGATIVE RESULT: footprint opposition does not exist in a mounted assembly. It is positive only in the unmounted and clamped idealisations and negative on all five explicit boards, in the direction the reference paper itself asserts.
* NEGATIVE RESULT: a compact clamped foundation is not a substitute for an explicit board. It sits in the opposite regime and cannot reproduce its own free limit.

### Claims that must not be made

* That mechanics binds, constrains, or restricts the feasible design set. No admissible criterion exists.
* That footprint is an ETM opposition in a mounted assembly.
* Any absolute mounted warpage value as a prediction.
* Any comparison of the computed warpage against a 'conventional' or 'typical' package limit. No source satisfying the admissibility test has been obtained. The only supportable statement is that simulated mounted INCREMENTAL OPERATIONAL warpage stays below 40 um over the tested envelope; whether that is safe or constraining is UNKNOWN.
* Any board-level conclusion drawn from a BC-A or BC-B result.

<!-- END GENERATED: publication_claims -->

# Next Steps --- prioritised roadmap

Phase 0E closed the two inputs that blocked Phase 0E entry. What it did **not** close is
whether any mechanical constraint ever becomes active, and that was then the only thing standing
between this project and a defensible synthesis claim. **Phase 0G closed it negatively:** no
admissible criterion exists, so no mechanical constraint can become active, and the synthesis
claim cannot rest on one.

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
   the modelled stack. *"This does not affect trends but it forbids absolute claims"* was
   **an assumption, not a result**, and Phase 0F retracted it: the swept thicknesses are
   geometrically unbuildable, so the trend direction survives only on realizable geometry.
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


\newpage

# Phase 0G --- Assembly-Boundary, Crossover-Robustness and Mechanical-Criterion Closure (superseded by Phase 0H)

**Verdict: NO ACTIVE MECHANICAL CONSTRAINT --- RESPONSE COUPLING ONLY.**
**Global ETM optimizer: NOT recommended, NOT built.**

Phase 0F ended with three statements it explicitly flagged as unproven: a PROVISIONAL board
stiffness on which a thickness-sign reversal rested entirely; an ARCH_B electrical minimum
that was extremely shallow; and gate G2 still NOT TESTED for want of a criterion. Phase 0G
was instructed not to assume that wording was proven. It was not. Two of the three turn out
to be artifacts, and the third is unchanged.

## The interior electrical optimum was a unit error, not a numerical one

The Phase-0F minimum was $+14.5$ mW on a 125 W system, and the obvious suspect was
convergence: the ET loop held $T_{max}$ to 0.05 K, and at $dP_{conv}/dT = 148$ mW/K that
tolerance alone admits roughly 7.4 mW --- half the effect. Phase 0G re-ran the sweep at **25x
tighter tolerance** and 5x thickness resolution specifically to break the claim.

**The minimum survived.** Testing the obvious hypothesis and having it pass is exactly what
made the real defect look excluded.

Decomposing the curve as $P_{total,B}(h) = g(h) + P_{TSV,B}(h)$ and checking the units of each
term found it. `vertical_tier()` returns a **per-regulator** loss; `rdl_network_solve()`
returns a **system-wide** loss; Phases 0D-R, 0E and 0F added them together. Every vertical
tier was understated by $n_{vr}$ --- 4x at 240 W and **49x** at the 1 kW reference. The
signature is unambiguous: the ratio of corrected to uncorrected $P_{TSV}$ is **49.004 to
49.055** at all nine thicknesses, and an independent hand check (89.7768 mW/VR x 49 =
4.399 W) agrees. This is **DEFECT #30**.

Corrected, ARCH_B is monotonically increasing and its optimum sits on the **thin boundary** in
**9 corners of 9** spanning TSV current-density policy, crowding, allocation policy and copper
resistivity. ARCH_A retains a genuine interior optimum at $h = 0.90$ mm, resolved at 88x the
0.0977 mW numerical floor --- but it is **8.6 mW deep on a 125 W budget (0.0069 %)**, and the
ARCH_A/ARCH_B gap at fixed thickness is 52x larger than the whole depth of it.

![FIG-0G-A](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0g/FIG_0G_A_defect30.png)

## BC-B was a clamp, and the reversal was its artifact

`BC_B` emits `*BOUNDARY {n},1,3` across the underside plane --- **all three degrees of
freedom**. A BGA field does not: solder balls are compliant in shear, so a mounted package
retains in-plane freedom relative to its board. Two tests settle it, neither depending on a
material choice.

**The free-limit test.** At $k_z = 0.001$ N/mm$^3$ the foundation is mechanically absent, so
the answer must approach the free package. It gives **0.739 um** where the free package on the
identical mesh gives **8.287 um**. A foundation with no stiffness is still suppressing 91 % of
the warpage; that residual is the in-plane clamp, and it is present in every Phase-0C..0F BC-B
result.

**The $k^*$ search.** $S_h > 0$ at all twelve stiffnesses across seven decades. There is no
root. The effect is kinematic, not elastic, so it cannot be tuned away by softening the
support.

![FIG-0G-B](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0g/FIG_0G_B_no_kstar.png)

An explicit BGA + PCB assembly was built instead, from source-backed geometry (0.4 mm balls on
0.8 mm pitch, area fraction 0.19635, $E_{solder} = 20$ GPa from the STAMP-2.5D table) with five
board cases from compliant to metal-backed. It passes the limit test the compact model fails:
driving the board towards absence returns **13.20 um** against the free package's 11.17 um
($+18.1$ %, the residual being the BGA layer's own 3.93 GPa / 20.5 ppm/K contribution), and it
responds correctly to board CTE as well as stiffness --- a stiff CTE-matched board *flattens*
the package to 2.67 um.

A real board **amplifies** warpage, to 29.2 um --- 2.6x the free package --- because silicon at
2.6 ppm/K is bonded to FR-4 at $\approx$ 18 ppm/K. The compact model **suppresses** it to 0.37 um.
These are opposite regimes, not a quantitative disagreement.

![FIG-0G-C](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0g/FIG_0G_C_assembly_regimes.png)

Across the whole envelope, **every physically constructed assembly gives the free-package
sign**: thicker is better, $S_h = -0.039$ to $-0.886$. Only the clamp reverses it.

![FIG-0G-D](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0g/FIG_0G_D_Sh_by_model.png)

## The footprint opposition does not exist in a mounted assembly

This is the finding that changes the project's central claim. Footprint opposition --- that
electrical performance wants more distributed regulation while mechanics wants less --- was
the strongest DVPD-specific result Phases 0C..0F reported.

Comparing two realizable 1 kW designs at fixed $j = 3.0$ A/mm$^2$ (total HVR footprint
259.2 $\to$ 329.3 mm$^2$, $M = 36 \to 49$), the mechanical sign is **positive in the free
($+0.203$) and clamped ($+0.058$) models and negative in all five explicit boards ($-0.166$ to
$-0.290$)**. Electrically the larger footprint wins by **6.633 W**, as the lateral RDL loss
halves from 0.983 W to 0.489 W.

**In every mounted model the two disciplines agree.** There is no trade-off to co-optimize on
this lever.

![FIG-0G-E](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0g/FIG_0G_E_footprint_flip.png)

The reference system asserts the same direction. June-2026 (Sec. I) states that partitioning
conversion into multiple smaller VRs "prevents the formation of a single mechanically stiff
region", that each VR "produces localized deformation rather than global package deflection",
and that symmetric placement lets localized effects "partially offset one another, reducing
overall warpage sensitivity". The explicit-board model reproduces the direction the source
asserts; the free and clamped models contradict it. The corroboration is of **direction only**
--- June attaches no number to the claim.

## What survives, and how hard it was pushed

One genuine ETM opposition remains: **substrate thickness**, electrically thinner against
mechanically thicker. It is present identically in the free package, so it is the conventional
tension rather than an assembly-state effect --- and it is robust across everything tested.

| perturbation | range | sign flips |
|:--|:--|--:|
| assembly model | free, clamp, 5 explicit boards | 0 of 7 |
| stress-free reference (M1) | 25 / 150 / 175 $^\circ$C | 0 of 6 |
| thermal boundary | 4x $h_{top}$ band; substrate-side topology | 0 of 10 |
| **total** | | **0 of 20** |

The mounted normalized response is close to invariant: $S_h = -0.4419 / -0.4421 / -0.4422$
across a 4x thermal-boundary range (0.07 % spread) and $-0.4421 / -0.4397 / -0.4400$ across a
150 K reference-temperature span (0.5 % spread), while the magnitudes move by 45--64 %. The
normalized thickness response is a **structural property of the assembly**, not a thermal one.

![FIG-0G-F](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0g/FIG_0G_F_invariance.png)

Two bounds come out of the same work. Substrate-side cooling --- June's actual topology ---
changes warpage magnitudes by up to $+45$ % and halves $S_h$, but flips no sign; it is also
**thermally infeasible at 1 kW**, flooring at 90.96 $^\circ$C and reaching 110.4 $^\circ$C at
$h = 2.00$ mm. And every warpage number in this project is **incremental operational** with a
25 $^\circ$C reference: raising it to a cure temperature increases mounted warpage by up to
54 % (25.1 $\to$ 38.7 um) while leaving $S_h$ stable to 0.5 %. All absolute figures here are
therefore lower bounds.

## There is still no criterion, so nothing binds

June-2026 names the failure mechanisms it cares about --- global package warpage, delamination
risk, and shear stress in the RDL --- and attaches **no number** to any of them. No other
source in the corpus supplies one. External standards were unretrievable in this environment
and, on inspection of what they govern, would be inadmissible regardless: package-outline
coplanarity constrains the ball plane of a component *as supplied*, at a defined measurement
temperature, for solderability at reflow. This project computes incremental operational
warpage of a *mounted* assembly at steady-state operating temperature. Package state,
temperature, measurement definition and failure mechanism all differ.

On magnitude, the only statement this project can support is that simulated mounted
**incremental operational** warpage stays **below 40 um** across every assembly, reference
state and thermal boundary examined. Phase 0G additionally compared that range against a
"conventional" package tolerance band; **Phase 0H Sec. 18 retracts that comparison** as
unsourced. Whether 40 um is safe, marginal or constraining for this architecture is
**UNKNOWN** until an admissible criterion exists.

**G2 remains NOT TESTED --- not failed.** It has never been given a threshold to test against.
The $\varepsilon$ sweep is therefore a **parametric preference sensitivity** and never a
feasibility test, and it is reported in both assembly states because the answer depends on
which one is assumed: the mounted floor is 14.03 um, so the entire free-package range
(1.3--11.2 um) is unreachable once the package is on a board.

![FIG-0G-G](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0g/FIG_0G_G_epsilon.png)

## Optimizer gate

Both conditions set for Phase 0G were required.

| condition | met | why |
|:--|:--|:--|
| 1 --- the assembly-state response survives calibrated board and thermal-boundary uncertainty | **PARTIAL** | the thickness *response* survives with 0 sign flips in 20 combinations, but the assembly-state *reversal* the condition asked about does not survive: it does not exist |
| 2 --- a criterion or user-set $\varepsilon$ can actually alter the feasible design set | **NO** | no criterion exists, and the whole computed warpage range sits 1--2 orders of magnitude below any conventional limit |

**The global ETM optimizer is NOT recommended and was NOT built.** Optimizing over an
unconstrained mechanical objective would produce a weighted-sum artifact whose answer is set
by the weights rather than by the physics. The next gate is **0H --- criterion acquisition**.

Full detail: `results/phase0g/PHASE0G_ASSEMBLY_BOUNDARY_GATE.md`.

\newpage

<!-- BEGIN GENERATED: phase0h_narrative -->

\newpage

# Phase 0H --- Mechanical Failure-Mechanism and Criterion Acquisition Gate (superseded by Phase 0I)

**Verdict: NO ADMISSIBLE MECHANICAL CRITERION FOUND --- RESPONSE COUPLING ONLY.**
**Falsification gate G2: NOT TESTED, unchanged since Phase 0B.**
**Recommendation: reframe the publication. The optimizer was not built and is not recommended.**

Phase 0G ended by saying no mechanical criterion could be found. Phase 0H was asked not to
accept that on reasoning alone. This environment blocks the WebSearch tool but the machine has
outbound network access, so the standards family and 479 primary works were actually searched.
The answer is unchanged, and it is now evidenced rather than inferred --- and the search turned
up three things that change more than the criterion question did.

## The model can see one failure mechanism of eight

Phase 0G asked "is there a warpage limit?". That was the wrong first question, because global
warpage is not a failure mechanism. Enumerating the mechanisms that could actually end the life
of this assembly, and asking which the model can evaluate:

| # | mechanism | computable at M0? | blocking requirement |
|:--|:--|:--|:--|
| A | global package bending | **YES** | --- but it is a response, not a failure |
| B | BGA solder fatigue | NO | discrete balls + viscoplasticity + cycling |
| C | microbump / C4 | PARTIAL | smeared layer; no per-joint strain |
| D | RDL damage | NO | the RDL is not in the mechanical mesh at all |
| E | die / low-k CPI | NO | homogenisation invalid for local stress |
| F | delamination | NO | fracture mechanics; peel is a corner singularity |
| G | TSV interaction | NO | homogenised via field |

June-2026 names three mechanisms --- *"global package warpage, delamination risk, and shear
stress in the redistribution layer"*. **Two of those three are outside the mechanical model.**
The project has been measuring the load, not the damage.

![FIG-0H-B](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0h/FIG_0H_B_mechanism_map.png)

## Global warpage does not predict the local loading

Seventy paired runs, spanning assembly model, board case, thickness, footprint, stress-free
reference and thermal boundary, test whether the quantity this project measures best can stand
in for the quantity that matters.

It cannot. Across the mounted thickness sweep **die warpage varies 3.0x (9.66 to 29.23 um)
while interface shear stays within $\pm$9 %**. Overall Spearman $\rho$ = 0.112. Worse, the sign
is not stable: $\rho$ = $-$0.793 in the free package against $+$0.349 mounted, so in the free
configuration a design change that raises warpage *lowers* interface shear.

![FIG-0H-C](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0h/FIG_0H_C_warpage_not_proxy.png)

Global warpage is an architectural **response metric**, not a reliability quantity. Phase 0G's
"below 40 um" therefore carries no margin information --- an independent second reason for the
retraction recorded in that section.

Neither local candidate can replace it. Revalidated on the explicit board, interface shear is
**non-monotone** under refinement (7.6 % spread; its p99 samples a bimaterial corner) and
relative displacement carries **26.5 %** material spread from an underfill modulus the stack
itself flags UNSPECIFIED and HIGH-RISK. The closing shape of the mechanical side of this work
is that *the quantity that is trustworthy is not meaningful, and the quantities that are
meaningful are not trustworthy*.

## Every published warpage allowable is a manufacturing limit

`jedec.org` and the ANSI webstore return HTTP 403 here, so **IPC-9641 was read directly** and
the JEDEC family characterised from peer-reviewed open-access work that applies it. No standard
is cited from memory.

IPC-9641 turns out to govern the **printed board**, through a **reflow** profile, to prevent
*"open or bridging joints"* --- and contains no allowable at all. **JESD22-B112C is a
measurement method**, not a limit; the limits live in **JEP95** (80 um room-temperature
ball-plane coplanarity) and **SPP-024** ($-$120 to $+$170 um at peak reflow). A 2025 review
supplies the only package-level numbers found anywhere --- 0.2 mm maximum, 0.1 mm preferred ---
explicitly *"for high yields"* during wafer-level packaging, and lists *"Need for Materials
Data and Failure Criteria"* as an open challenge for the field.

Nine candidates were then tested against six admissibility conditions. **None passed**; the
best scored 3 of 6.

![FIG-0H-D](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0h/FIG_0H_D_admissibility.png)

The SPP-024 row deserves emphasis. At $-$120/$+$170 um for a comparable body size it is the
closest published number to this project's computed range --- and it measures a different
quantity, in a different package state, at a different temperature, for a different failure
mechanism. **Proximity in magnitude is not admissibility.** This is also why the Phase-0G
comparison against "conventional tolerances" is retracted.

## The GaN heights are sourced, and the electrical optimum becomes unbuildable

Phase 0F recorded the GaN and MLCC heights as OPEN and carried an invented 0/100/250 um
envelope. The EPC *product table* has no heights --- but the **datasheets do**:

| device | role | height |
|:--|:--|:--|
| EPC2212 | high side | **685 um nominal, 815 um max** |
| EPC2090 | low side | **606 um** (518 $\pm$ 25 die + 50 Cu + 3 Ni + 35 solder) |

Six to eight times the assumed nominal, and 2.4--3.3x the assumed *pessimistic* bound. With
June-2026's own statement of which components are embedded in the substrate power layers, the
minimum realizable substrate rises from **0.770 mm to 1.176--1.426 mm**.

![FIG-0H-E](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0h/FIG_0H_E_geometry_closure.png)

**The corrected ARCH_B electrical optimum at $h_{sub}$ = 0.80 mm is infeasible by 376--626 um**,
as are 0.90 and 1.00 mm. This is the Phase-0F finding recurring one level up: an electrical
optimum sitting on a geometric boundary that had been placed with an unsourced number. The
caveat travels with it --- datasheet heights are as-supplied, and die thinning before embedding
is a normal step that the reference system does not mention either way.

## DEFECT #30 also inverted a 240-W ranking

Phase 0G fixed the arithmetic and wrote a comment. Phase 0H makes it structural: every
electrical quantity now carries its scope, and adding a per-regulator term to a system-wide one
raises an exception naming the defect. Two deliberate mutations confirmed the guard fails when
the protection is removed.

Propagating the correction changed a published conclusion. Replaying the eleven Phase-0E 240-W
candidates moves **three ranking positions** --- ARCH_A cases shift 16--25 mW while ARCH_B at
$h$ = 0.5 mm shifts **+356.8 mW** and falls from third-best to worst.

![FIG-0H-A](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0h/FIG_0H_A_defect30_ranking.png)

The 1-kW decomposition also reclassifies a Phase-0D-R claim: *RDL dominates distribution loss*
holds for ARCH_A at every thickness, and **fails for ARCH_B** above roughly 0.9 mm where the
via field exceeds the RDL by up to 11x.

## What the thickness opposition actually rests on

Over the buildable band (MLCC-nominal, 1.30 to 2.00 mm) the trade is **4.043 W** of ARCH_B loss
against **29.3 %** of mounted warpage. But only one side of that is resolved:

| quantity | change | vs its own uncertainty |
|:--|:--|:--|
| $\Delta P_{elec}$, ARCH_B | $+$4042.6 mW | resolved overwhelmingly |
| $\Delta$ die warpage | $-$5.824 um ($-$29.3 %) | **resolved**, 7x the 4.00 % floor |
| $\Delta$ interface shear | $+$0.156 MPa ($+$1.96 %) | **NOT resolved**, 7x *below* its 14.14 % floor |

![FIG-0H-F](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0h/FIG_0H_F_thickness_final.png)

So the opposition survives --- and it is resolved **only in global warpage**, the quantity that
Sec. 7 disqualified as a predictor of local loading. In the one local metric available, the
thickness effect cannot be resolved at all. That is a sharper statement than Phase 0G's, and a
less comfortable one.

## Consequence

**Reframe from "ETM co-synthesis optimizer" to "audited cross-domain DVPD modelling and
falsification".** The search covered the standards family and 479 primary works and returned
zero admissible criteria for a structural reason --- operating-life limits are set by product
qualification, not by package-outline documents, and the mechanisms that would carry such a
limit are outside this model. Continuing the search is not expected to converge.

The contribution is the audit chain and the negative results, which are unusually well
evidenced. Full detail: `results/phase0h/PHASE0H_CRITERION_ACQUISITION_GATE.md`.

<!-- END GENERATED: phase0h_narrative -->

<!-- BEGIN GENERATED: phase0i_narrative -->

\newpage

# Phase 0I --- Vertical Integration and Local Reliability Physics (rescoped by Phase 0I-R)

**Verdict: ARCHITECTURE-DEPENDENT RELIABILITY RESPONSE --- NO ACTIVE CONSTRAINT.**
**G2 is now half-built: the metric exists, the allowable does not.**
**The global ETM optimizer was not built and is not recommended.**

Phase 0H concluded *no admissible mechanical criterion --- response coupling only*, and was
explicit that this applied to the M0 thermoelastic model and to the single architecture that
had actually been modelled. Phase 0I adds the two things it named as missing. Neither produces
an active constraint. Both change what the project can say.

## M0 and M1/M2 are different models and are labelled so

| rung | what it computes | where it is used |
|:--|:--|:--|
| **M0** | linear thermoelastic deformation; warpage, curvature, smeared interface stress | Phases 0B--0H, and the GLOBAL package model here |
| **M1** | M0 with a shifted stress-free reference --- a pre-stress SENSITIVITY, not a pre-stress model | Phase 0G Sec. 11 |
| **M2** | temperature-dependent elastic, plastic and creep response, cycled to a stabilised hysteresis loop; **local damage** | Phase 0I LOCAL joint submodel |

Everything Phase 0H said about global warpage remains a statement about M0. Everything said
below about damage is M2.

## DEFECT #33 --- realizability was architecture-blind

`kw1.design_1kw()` takes no architecture argument, so the *embedded* rule
$t_{cell} + h_{tsv} \le h_{sub}$ was applied to every architecture. At $h_{sub}$ = 0.30 mm the
code answers *"no inductor fits h_sub=300 um (budget 30 um)"* for ARCH_A, ARCH_B and ARCH_C
alike --- yet ARCH_B converts **below** the substrate and ARCH_C **beside** the die, and
neither puts the inductor inside $h_{sub}$.

The electrical model has varied the converter's vertical position since Phase 0D-R. The
geometric and mechanical models never did, and no test could catch it because each domain was
self-consistent on its own terms.

**The Phase-0H bound $h_{sub,min}$ = 1.176--1.426 mm is therefore EMBEDDED-SPECIFIC.**
Non-embedded architectures are **component-height-realizable under the current Z-architecture
model down to 0.300 mm** --- the source-demonstrated TSV-layer thickness, a 4.3x wider range
that includes the thin region the corrected electrical model prefers. Phase 0I-R scopes this:
0.300 mm is a component-height and TSV-layer statement, **not** a guarantee that a complete
package at that thickness satisfies backside clearance, cooler and board clearance, cavity and
lid rules or the full design-rule set. Those remain **open**.

The reference paper supports this directly: it describes its own architecture as *"vertically
stacked in-substrate **and backside** VR components"*, and separately records that multi-layer
substrate stacking *"remains an open challenge"*.

![FIG-0I-A](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0i/FIG_0I_A_cross_sections.png)

## Which rail crosses the substrate is an architecture choice

![FIG-0I-B](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0i/FIG_0I_B_power_paths.png)

Z2 puts **1000 A** on the via field; Z1, Z4 and Z5 put **23.4 A** on it --- a factor of 42.7 in
current, 1822 in $I^2$, decided purely by z-placement. The allocator returns **14 148** TSVs
for Z2's low-voltage field, and June-2026 Table III independently reports **14 148** TSVs for
PL3 in its own optimised allocation. Two different pieces of machinery, exact agreement.

| architecture | best realizable $h_{sub}$ | $P_{TSV}$ | $P_{RDL}$ | **$P_{total}$** |
|:--|--:|--:|--:|--:|
| Z1 embedded | 1.30 mm | 0.0098 W | 0.6451 W | **126.090 W** |
| Z4 power die | 0.30 mm | 0.0397 W | 0.6451 W | **126.120 W** |
| Z2 backside | 0.30 mm | 1.6979 W | 0.6451 W | **127.778 W** |
| Z5 2.5D lateral | 0.30 mm | 0.0397 W | **768.07 W** | **893.547 W** |

Z1 shows a 30 mW edge --- 0.024 % --- purely because its embedded cell shortens the via field
to 74 um. **Phase 0I-R finds that difference UNRESOLVED, and Z1 must not be called electrically
preferred.** Every tier except $P_{TSV}$ is bit-identical between the two, but the sweep
evaluated all architectures at a *frozen* $T_c$ = 85 C, and the global model shows Z4 running
1.444 K cooler; at 148 mW/K that neglected term is 214 mW --- 7.1x the claimed difference and
of the opposite sign. **Z1 and Z4 are electrically indistinguishable at current fidelity.** The
Z2 penalty of +1.688 W, by contrast, is resolved at 5.98 sigma.

**The tested Z5 low-voltage-lateral topology is electrically eliminated** by ~768 W of modelled
RDL loss. That prices the specific arrangement in which a long lateral interposer path carries
the ~1 V / 1 kA rail; it is **not** a statement that 2.5D as a class is infeasible. Untested
variants --- higher-voltage lateral distribution, distributed conversion, intermediate-voltage
distribution with local point-of-load conversion --- were not modelled.

## Reliability physics, built and validated

CalculiX 2.23 has `*PLASTIC`, `*CREEP,LAW=NORTON` and `*VISCO`, and **no Anand model**. That
was verified by running, not assumed: a solder cube under cyclic shear reversed stress
+/-91 MPa, accumulated inelastic strain monotonically, and relaxed **-38.0 %** during a
constant-strain hold.

The SAC305 card uses **only SAC305 data** --- SnAgCuCe and SAC405 Anand sets were found and
rejected for being different alloys. Because a single Norton power law cannot span Garofalo's
curvature (its effective exponent runs 3.1 at 2 MPa to 19.2 at 30 MPa, 253 % RMS over
1--30 MPa), the card is fitted **directly to 19 measured creep points** at 45/80/115/150 C,
whose 7.5--16 MPa range is exactly where a joint operates once plasticity caps the stress.
Per-temperature fit error is **4.1--12.2 % RMS**. Two independent cross-checks passed: yield
$\sigma_0$(25 C) = 24.46 MPa against a measured 23.3--25.6 MPa, and the fitted card's apparent
activation energy **64.4 kJ/mol** against a published 62.0 and 65.0.

![FIG-0I-D](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0i/FIG_0I_D_workflow.png)

Validation is 4/4: free expansion exact to 0.000 % with zero inelastic strain; creep rate
x535 and yield -57 % over the operating range; -49.6 % stress relaxation in a 600 s
hold; cycle stabilisation to 0.4 %. Convergence is mesh **1.90 %**, CETOL **0.02 %**, corner
exclusion band **6.4 %** --- and including the corner *lowers* the value, so the metric is not
corner-dominated. **This is the first local mechanical metric in the project to pass mesh,
tolerance and regularisation stability together**, against interface peel (19--20 % per
refinement, excluded in Phase 0C) and p99 shear (non-monotone, rejected in Phase 0H).

![FIG-0I-F](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0i/FIG_0I_F_hysteresis.png)

## Does the new physics matter?

| model | $\Delta\varepsilon_{in}$ per stabilised cycle | vs A |
|:--|--:|--:|
| **A** temperature-INDEPENDENT (the Phase-0H class; still has $\alpha\Delta T$) | 8.214e-3 | --- |
| **B** T-dependent $E$ and yield, no creep | 8.524e-3 | +3.8 % |
| **C** FULL: $E(T)$, $\sigma_y(T)$, thermally activated creep | **5.980e-3** | **-27.2 %** |

Yes --- and the sharper result is the mean-temperature sweep at a fixed 100 K swing. Model A
moves **-0.2 %** as the cycle mean shifts 25 to 75 C; model C moves **+22.7 %**. The older
model class is structurally blind to where in temperature a cycle sits.

**Phase 0I-R adds a necessary qualification.** The 27.2 % is a statement about the
*strain-based* measure only. Re-running the same three solves and integrating
$\sigma\!:\!d\varepsilon_{in}$ over the cycle shows the **dissipated inelastic energy rising
164.6 %** while the strain metric falls 29.8 %. Creep suppresses plastic strain accumulation by
relaxing stress, yet deforms at sustained stress and so dissipates far more. Neither number may
be quoted as "damage decreased" without naming the measure. The architecture *ranking* is
identical under all three measures.

![FIG-0I-C](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0i/FIG_0I_C_thermal.png)

Transient capability was added without touching shared code, and converges to the validated
steady solver to **0.110 %**. The response is two-mode --- a fast silicon package mode near
15 s and a slow FR-4 board mode near 600 s, $t_{95}$ = 1618 s --- so quoting one time constant
would be wrong.

## The architectures separate on mechanics, not on temperature

| architecture | $h^*$ | $P_{elec}$ | $T_{joint}$ | $\Delta u$ corner | **$\Delta\varepsilon_{in}$** | vs Z1 |
|:--|--:|--:|--:|--:|--:|--:|
| Z1 embedded | 1.30 mm | 126.090 W | 82.86 C | 2.749 um | 6.512e-3 | --- |
| Z2 backside | 0.30 mm | 127.778 W | 81.85 C | 2.080 um | **4.179e-3** | **-35.8 %** |
| Z4 power die | 0.30 mm | 126.120 W | 81.10 C | 2.984 um | **7.320e-3** | **+12.4 %** |

Joint temperature spans only 81.10--83.21 C across every architecture and thickness, and its
correlation with damage is **r = +0.017**. Z4's converter-in-the-thermal-path concern does not
materialise at the joint. **The architectures separate on mechanics.**

![FIG-0I-H](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0i/FIG_0I_H_loss_vs_damage.png)

No architecture dominates. What the model actually delivers is a **metric ratio**: Z2 is
**35.8 % below** Z1 and Z4 **12.4 % above** it, and Phase 0I-R shows both are RESOLVED --- 5.8x
and 5.1x their spread across every material, mesh and regularisation perturbation, with all
three inelastic measures agreeing to within 2 pp.

Converting that to life requires a fatigue exponent. In $N_f = C\,\Delta\varepsilon^{-m}$ the
constant $C$ cancels in a ratio but **the exponent $m$ does not**. Phase 0I quoted "1.9--3.8x"
from an $m$ = 1.5--3 range that was **never sourced**. Over $m$ = 0.5--5 the Z2/Z1 ratio spans
1.25 to 9.18 --- a factor of 7.4 from the exponent alone. Every life ratio in this project is
therefore labelled **PARAMETRIC LIFE-LAW SENSITIVITY**, and no lifetime is claimed.

![FIG-0I-I](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0i/FIG_0I_I_relative_life.png)

## What this changes about global warpage

Phase 0H found global warpage did not correlate with its local quantity ($\rho$ = 0.11 against
smeared interface shear). Against a proper damage metric it correlates **perfectly within an
architecture** ($\rho$ = 1.000 in all three) and **+0.909 pooled**. The Phase-0H finding
stands as a statement about smeared shear, which was a poor proxy; it does not stand as a
statement about local damage.

But warpage **overstates the benefit**. Over the same thickness range warpage moves
29.7--52.6 % while damage moves only 5.6--17.2 % --- a 3--5x exaggeration.

![FIG-0I-G](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0i/FIG_0I_G_damage_vs_thickness.png)

The thickness opposition survives in the reliability metric, in all three architectures:
electrical prefers thin, damage prefers thick. It is simply much weaker than global warpage
made it look.

## Why this is still not a constraint

$g_{mech}(x) \le g_{allow}$ needs both halves. Phase 0I builds the left-hand side: a
convergent, validated, failure-relevant metric tied to a documented mechanism. The right-hand
side is missing and it is **data, not physics** --- no SAC305 life law could be retrieved (both
candidate open-access sources return HTTP 403) and no mission profile exists for the reference
system. **No lifetime is predicted anywhere in this project.**

The next gate is therefore acquisition, not more modelling. Full detail:
`results/phase0i/PHASE0I_Z_ARCHITECTURE_RELIABILITY_GATE.md`.

<!-- END GENERATED: phase0i_narrative -->
<!-- BEGIN GENERATED: phase0ir_narrative -->

\newpage

# Phase 0I-R --- Reliability-Metric, Claim-Scope and Report-Consistency Closure (extended by Phase 0J)

**Verdict: PHASE-0I METRIC VALID AFTER REDEFINITION --- READY FOR LIFE-LAW ACQUISITION.**
**The creep-omission failure mode did NOT occur; no Phase-0I number was replayed.**
**The life interpretation IS withdrawn. Z1 vs Z4 is NOT electrically resolved.**

Phase 0I produced an architecture-dependent damage response. This gate asked whether the
quantity it calls *damage* is defined correctly, and whether every Phase-0I sentence says only
what the evidence supports. The physics survived. Several of the sentences did not.

## What exactly is $\Delta\varepsilon_{in}$?

Phase 0I justified its metric by quoting a CalculiX warning --- *"selection of CEEQ or CE or PE
is converted into PEEQ; no distinction is made"* --- and inferring that PEEQ aggregates plastic
and creep. **That inference does not follow**: the warning describes how the output *request* is
aliased, which is equally consistent with PEEQ being plastic-only and the creep request being
discarded. The question was settled by experiment instead.

| probe | material | PEEQ / eq($\varepsilon_{in}$) |
|:--|:--|--:|
| **creep only, no `*PLASTIC` card at all** | elastic + Norton creep | **1.0000** |
| plastic only, no `*CREEP` | elastic + plastic | **1.0000** |
| both, ramped | elastic + plastic + creep | **1.0000** |
| both, 3000 s hold, stress relaxing 35.7 to 17.8 MPa | full | **1.0000** |

The first row settles it: with no plasticity in the deck, PEEQ is non-zero and equals the
equivalent creep strain to five figures. The identity was then re-confirmed in the real
multiaxial, temperature-varying joint at 1.0029--1.0035.

$$\text{PEEQ} = \operatorname{eq}\!\left(\varepsilon_{tot}-\varepsilon_{el}-\varepsilon_{th}\right)
\ \text{accumulated along the path; plastic AND creep together}$$

**The one thing Phase 0I got wrong about it: PEEQ is a path length, not a state.** Phase 0I
called its metric an *"inelastic strain range"*. It is not a range --- it is the inelastic path
length traversed per cycle:

| stabilised cycle | EP | EPC |
|:--|--:|--:|
| $\Delta$(PEEQ) per cycle --- **the Phase-0I metric** | 8.524e-3 | 5.980e-3 |
| range of eq($\varepsilon_{in}$) within the cycle | 2.254e-3 | 1.609e-3 |
| **ratio** | **3.78** | **3.72** |

A fully-reversed uniaxial cycle would give 2.0. This OFF--ON--OFF cycle is a multi-reversal path
in strain space, so it gives 3.7. **The values are correct and stand; the label was wrong.** A
life law calibrated against a strain *range* would be misapplied by that factor if fed this
metric directly, and Phase 0J must match the law to the form or convert by the measured 3.72.

## The dangerous failure mode did not occur --- but the energy diagnostic dissents

The audit was commissioned to look for one specific trap: creep relaxes stress, plastic strain
falls, a plastic-only parser reports *"damage decreased"*, and the creep deformation is
invisible. **It did not happen** --- PEEQ contains creep, proven above, and the creep-only
variant returns a plainly non-zero 6.664e-3 from a deck with no `*PLASTIC` card. The Phase-0I
$-27.2\%$ result therefore survives as a statement about the strain-based metric.

But the same three solves, read two ways, disagree about the SIGN of what creep does:

| model | $\Delta\varepsilon_{in}$/cycle | vs EP | inelastic work (MJ/m$^3$) | vs EP |
|:--|--:|--:|--:|--:|
| **EP** elastic + plastic | 8.524e-3 | --- | 0.2064 | --- |
| **EC** elastic + creep | 6.664e-3 | $-21.8\%$ | 0.5773 | $+179.7\%$ |
| **EPC** full (Phase 0I) | 5.980e-3 | $-29.8\%$ | 0.5461 | $+164.6\%$ |

Creep relaxes stress and so suppresses plastic strain accumulation, yet it deforms throughout
every dwell and dissipates far more energy. **No direction-of-change statement about creep may
be written without naming the measure.** This is reported, not buried, because it constrains
Phase 0J: a Coffin-Manson-type law must be matched to the strain form and a Darveaux-type law to
the energy form.

![FIG-0IR-A](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0ir/FIG_0IR_A_strain_decomposition.png)

![FIG-0IR-B](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0ir/FIG_0IR_B_strain_vs_energy.png)

An error in this audit's own first attempt is worth recording: the energy integral initially
returned **negative dissipation**. The cause was that **CalculiX ramps `*TEMPERATURE` linearly
across a step** unless `AMPLITUDE=STEP` is given, so reconstructing temperature from the step
schedule corrupts the thermal-strain subtraction. Reading the solver's own `NT` output fixed it;
all dissipation became positive and the PEEQ identity sharpened from 0.9467 to 1.0029.

## The architecture conclusion is metric-independent

This is what decides whether Phase 0I's architecture claims survive the disagreement above:

| architecture | $\Delta$(PEEQ)/cycle | strain range | inelastic work |
|:--|--:|--:|--:|
| Z1 embedded | --- | --- | --- |
| **Z2 backside** | $-35.8\%$ | $-35.7\%$ | $-37.7\%$ |
| **Z4 power die** | $+12.4\%$ | $+12.6\%$ | $+13.0\%$ |

**All three measures agree on ranking and magnitude to within 2 pp.** Only the creep-inclusion
question is measure-dependent; the architecture ranking is not.

## Is the damage difference resolved? Yes --- and the ratio is the right thing to test

Adding RMS uncertainties would have been wrong. The three architectures share the same material
card, mesh, exclusion band and solver tolerance, so those errors are **common mode** and cancel
in a ratio. Each perturbation was therefore applied to all three at once and measured on the
ratio:

| comparison | effect | spread over ALL perturbations | ratio | verdict |
|:--|--:|--:|--:|:--|
| Z2 / Z1 | $-36.0\%$ | 6.2 pp | **5.8x** | **RESOLVED** |
| Z4 / Z1 | $+12.4\%$ | 2.4 pp | **5.1x** | **RESOLVED** |

Absolute damage moves a great deal under these perturbations --- $E \times 1.15$ raises Z1 by
9 % --- while the ratios barely move. The architecture claim is stronger than the absolute
numbers are.

## Z1 vs Z4 is NOT electrically resolved

Every electrical tier except the via field is bit-identical between architectures, so those
errors cancel exactly and the whole Z4--Z1 difference of 29.93 mW is the via-field term. That
looked resolved until the dominant neglected term was identified: **the electrical sweep
evaluated every architecture at a frozen $T_c = 85.0$ C**, while the global model shows the two
packages differing by 1.444 K. At $dP_{conv}/dT = 148$ mW/K that is **213.8 mW --- 7.1x the
claimed difference, and of the opposite sign**, since Z4 runs *cooler*.

| comparison | difference | dominant uncertainty | $\sigma$ | verdict |
|:--|--:|--:|--:|:--|
| **Z4 - Z1** | +29.93 mW (0.024 %) | 213.8 mW neglected temperature coupling | **0.14** | **UNRESOLVED** |
| **Z2 - Z1** | +1688.11 mW (1.3 %) | 282.1 mW combined | **5.98** | **RESOLVED** |

**Z1 and Z4 are electrically indistinguishable at current fidelity.** Z1 is not electrically
preferred. The Z2 penalty stands.

![FIG-0IR-D](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0ir/FIG_0IR_D_electrical_resolution.png)

## The relative-life claim was wrong in kind

Phase 0I wrote that relative life is *"parameter-free in the life-law constant"*. Literally true
of $C$; **misleading as written**, because it invites the reading that the ratio is
parameter-free. For $N_f = C\,\Delta\varepsilon_{in}^{-m}$ the constant cancels and **the
exponent does not**.

Traced: the range $m = 1.5$--$3$ appears exactly once in the Phase-0I codebase, as a figure
annotation reading *"typical solder k is 1.5--3"*. It was written from general knowledge,
appears in no retrieved source, and was never labelled. It is the sole basis of the headline
*"1.9--3.8x relative life"*. **Status: UNSOURCED.**

| $m$ | 0.5 | 1.5 | 3.0 | 5.0 |
|:--|--:|--:|--:|--:|
| Z2/Z1 life ratio | 1.25 | 1.94 | 3.78 | **9.18** |

Over $m = 0.5$--$5$ the ratio spans a factor of 7.4 from the exponent alone. Every life ratio in
this project is now labelled **PARAMETRIC LIFE-LAW SENSITIVITY**. What may be claimed is the
metric ratio, which is a model output.

![FIG-0IR-C](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0ir/FIG_0IR_C_relative_life_exponent.png)

## Claim scope

**Retained in full** --- the DEFECT #33 finding stands: component height constrains $h_{sub}$
**only** for the embedded architecture.

**Scoped** --- 0.300 mm is *component-height-realizable under the current Z-architecture model*
and a source-demonstrated TSV-layer thickness. It is **not** a manufacturability guarantee:
backside clearance, die attach, cooler and board clearance, bump-stack budget, cavity and lid
rules and the full design-rule set are unmodelled.

**Scoped** --- only the *tested Z5 low-voltage-lateral topology* is electrically eliminated, by
~768 W of modelled RDL loss. This is not a statement about 2.5D as a class.

## Two reframings

**Warpage.** Phase 0I read $\rho = 1.000$ within each architecture as warpage tracking damage.
Within one architecture the thickness sweep is monotonic and *both* quantities move monotonically
with it, so that correlation is close to guaranteed by construction. The defensible statement is
**directional only**: warpage tracks the direction of local damage but not its magnitude,
changing 29.7--52.6 % where damage changes 5.6--17.2 % --- **exaggerating the apparent
reliability benefit by 3--5x**. Global warpage is not a calibrated surrogate.

![FIG-0IR-E](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0ir/FIG_0IR_E_warpage_vs_damage.png)

**Temperature.** Two true statements that must not be conflated: **(A)** temperature-dependent
material physics matters --- a frozen-property model moves $-0.2\%$ across a 50 K shift in cycle
mean where the full model moves $+22.7\%$; **(B)** these particular architectures happen to have
near-identical joint temperatures (81.10--83.21 C, $r = +0.017$ against damage), so **their**
reliability difference is mechanical, not thermal.

## Two defects in the verification suite itself

**DEFECT #35** --- Phase 0I added capability and left eight current-facing statements in the
Phase-0H state, so the report *understated its own model*: it still said only one failure
mechanism was computable, still described the mechanics as M0-only, and still recommended
publication reframing as the next step. All eight repaired at the single source of truth.

**DEFECT #36** --- the six new semantic guards were negative-tested against **paraphrases the
author wrote to match the author's own regexes**. Re-tested against the sentences that had
actually appeared in the report, **all six missed**: the real text said *"Z5 is eliminated"*
where the guard looked for the literal *"2.5D"*, *"a 0.300 mm substrate is realizable"* where it
looked for *"manufacturable"*, *"Z1 keeps a 30 mW edge"* where it looked for *"electrically
better"*. One consequence was real: a stale Executive Summary sentence sat inside guard scope
and was found by manual re-reading, which is what the guard existed to replace. Two further
weaknesses surfaced --- an exoneration term that appeared in the violating sentence itself, and
DEFECT #35 having been logged as fixed before it was applied.

The fix is structural. `GUARD_SELFTEST` pairs **each of the fifteen** current-facing guards with
the verbatim sentence it exists to reject, and the build fails if any pattern misses its sentence
or if an exoneration context clears it. A coverage check makes it impossible to add a guard
without one. Both failure modes were negative-tested on the self-test itself.

## Conditions for Phase 0J

| condition | status |
|:--|:--|
| metric exactly defined | **MET**, with the path-length/range distinction stated |
| plastic and creep correctly represented | **MET** --- proven by experiment, ratio 1.0000 |
| stabilised-cycle extraction correct | **MET** --- 0.48--2.00 % at cycle 4, loop shape settled |
| architecture separation resolved | **MET** --- 5.8x its perturbation spread |
| compatible with a known class of SAC305 law | **MET with caveat** --- match the law to the path-length form, or convert by 3.72 |

All five met. **Phase 0J is authorised** to acquire exactly two things and build nothing: a
SAC305 fatigue relation matched to this metric, and a source-backed or explicitly declared
required life. Full detail: `results/phase0ir/PHASE0IR_RELIABILITY_METRIC_CLOSURE.md` and
`results/phase0ir/REPORT_CONSISTENCY_AUDIT.md`.

<!-- END GENERATED: phase0ir_narrative -->
<!-- BEGIN GENERATED: phase0j_narrative -->

\newpage

# Phase 0J --- SAC305 Life Law, Mission, and G2 Evaluation (SUPERSEDED by Phase 0J-R)

**Verdict: NO ADMISSIBLE SAC305 LIFE LAW FOUND FOR THE CURRENT METRIC / REGIME.**
**G2 remains NOT TESTED. $N_{required}$ = OPEN.**
**The global optimizer is not recommended and was not built.**

## Five words this section never interchanges

| term | what it means here | status in this project |
|:--|:--|:--|
| **mechanical response metric** | a converged model output: M1, M2, M3 | **three exist, all validated** |
| **fatigue damage parameter** | a response metric a *source* uses as the input to a life law | **none** --- no source uses ours that way for this alloy, joint and cycle |
| **predicted fatigue life** | $N_f$ from a calibrated law | **none validated** |
| **required life** | $N_{required}$, declared or sourced | **OPEN** |
| **constraint / pass--fail** | $N_f \ge N_{required}$ | **not evaluable** |

Phase 0I-R closed the metric. Phase 0J went looking for the two things that would turn it into
a constraint, with network access Phase 0H did not have. **Both are absent, and for different
reasons.**

## What the search actually reached

762 unique works, 15 targeted queries, two independent indices. Eleven full-text sources
retrieved and read. **The three canonical calibrations are paywalled with no legal open-access
copy**, verified three ways each:

| paper | DOI | doi.org | Unpaywall | Semantic Scholar |
|:--|:--|:--|:--|:--|
| **Syed 2004** SnAgCu | 10.1109/ectc.2004.1319419 | IEEE 202 | `is_oa=false` | `openAccessPdf=null` |
| **Schubert 2003** SnAgCu | 10.1109/ectc.2003.1216343 | IEEE 202 | `is_oa=false` | `openAccessPdf=null` |
| **Darveaux 2002** | 10.1115/1.1413764 | ASME 403 | `is_oa=false` | `openAccessPdf=null` |

**139 open-access papers citing them were enumerated. Not one reprints a calibration dataset.**
Exactly one review reprints numerical SnAgCu constants. No paywall was circumvented.

![FIG-0J-A](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0j/FIG_0J_A_admissibility_funnel.png)

## The three metrics, frozen before any law was chosen

| | definition | units | character |
|:--|:--|:--|:--|
| **M1** | $\Delta$(PEEQ) per stabilised cycle | --- | accumulated inelastic **path**; plastic and creep, inseparable |
| **M2** | $\max_t -\min_t$ of eq($\varepsilon_{in}$) in the cycle | --- | a true **range**, computed **directly** |
| **M3** | $\sum \sigma:d\varepsilon_{in}$ over the cycle | **MJ/m$^3$** | dissipated inelastic **energy** |

### The number that justifies the "compute M2 directly" rule

Phase 0I-R measured $M1/M2 = 3.72$ and warned it was not universal. Computing both natively at
**all eleven** z-sweep points settles it:

| trajectory | $\Delta T$ | displacement path | **M1/M2** |
|:--|--:|:--|--:|
| **all 11 DVPD architecture cases** | 56.1--58.2 K | unidirectional $0 \to du \to 0$ | **2.023--2.027** |
| Phase-0I-R representative case | 100 K | fully reversed $-du \to +du \to -du$ | **3.72** |

**The ratio belongs to the loading path, not the material.** Across three architectures and a
6.7x span in substrate thickness it varies by **0.2 %**. Had 3.72 been used to convert, any
strain-range law would have been wrong by $1.84^m$ --- **2.6x at $m=1.5$, 6.2x at $m=3$.**

![FIG-0J-C](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0j/FIG_0J_C_native_metrics.png)

## The admissibility gate: 0 of 10

Ten candidates, ten predeclared criteria. **0 ADMISSIBLE, 1 conditionally transferable, 9
inadmissible.** The operative reasons:

* **Engelmaier is *undefined* for our cycle**, not merely inaccurate:
  $c = c_0 + c_1 T_{sj} + c_2\ln(1 + 360/t_{dwell})$ and **our cycle has zero dwell**.
* **Darveaux** needs $\Delta W_{ave}$ from **three element layers each 12.7 µm** at the pad
  interface; our finest element is **37.5 µm**, 3x too coarse to reproduce the extraction, and
  the circulated constants are **eutectic SnPb**. The retrieved source states the penalty
  itself: absolute predictions *"could be off by a factor of 7."*
* **Syed 2004** is the closest family --- its native metric *is* accumulated creep strain per
  cycle --- but the two-mechanism form needs $\varepsilon_{acc}$ **partitioned by a double power
  law**, and our Norton card is a single power law.
* **Schubert 2003** is cited by eight retrieved sources and reprinted by **none**.
* Two *fully specified* laws were found and rejected on regime and alloy: a SnAgCu **vibration**
  law, and a **92.5Pb5Sn2.5Ag die-attach** recalibration with primary constants from 20 devices.

**Sec. 8 reproduction: not passed** --- and one step earlier than the brief anticipates. The
formulas did not fail to reproduce their data; **the data cannot be reached.**

![FIG-0J-B](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0j/FIG_0J_B_calibration_not_reproducible.png)

## One simulated cycle is not one experimental fatigue cycle

Read out of the deck, not assumed. `*TEMPERATURE` carries no `AMPLITUDE=STEP`, so CalculiX ramps
linearly and the 300 s named `DWELL` is a 300 s **ramp**. The waveform is a **symmetric triangle
with zero hold**.

| | Phase-0I | JESD22-A104-B as applied |
|:--|:--|:--|
| $\Delta T$ | **56.1--58.2 K** | 165 K |
| **dwell** | **ZERO** | **15 min** |
| period | 10 min | about 120 min |

Both Sec. 15 remedies are unavailable for a reason that precedes them: **no admissible law means
no calibration cycle to reconcile with.** Re-running at $-40/+125$ °C was considered and
**deliberately not done** --- both extremes lie outside the validated 7.5--16 MPa Norton window,
so it would have produced numbers that look like progress and mean nothing.

**The cycle is right for the product and wrong for the literature.** The DVPD mission *is* power
cycling and Phase 0I modelled it as such. That is a data gap, not a modelling error.

## Does the law family change what creep means? Yes, in every architecture

| architecture | M1 strain path, creep ON vs OFF | M3 inelastic work, creep ON vs OFF |
|:--|--:|--:|
| Z1 embedded | $-$23.5 % | $+$147.8 % |
| Z2 backside | $-$32.0 % | $+$115.2 % |
| Z4 power die | $-$21.5 % | $+$153.3 % |

**A strain-based law and an energy-based law disagree about the sign of what creep does.** Any
future law must be matched to the measure it was calibrated against.

![FIG-0J-H](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0j/FIG_0J_H_temperature_and_creep.png)

## What survives: the ranking, and a ratio with no free parameter

Across all three law families and every exponent tested, the ranking is **Z2 > Z1 > Z4**, without
exception. That is a **ROBUST LIFE RANKING**.

And the Syed form is **inverse-linear**, $N_f = (C\,\varepsilon_{acc})^{-1}$, so in a life ratio
the constant cancels **and there is no exponent to assume**:

$$\frac{N_{f,Z2}}{N_{f,Z1}} = \frac{M1_{Z1}}{M1_{Z2}} = 1.558 \qquad
  \frac{N_{f,Z4}}{N_{f,Z1}} = 0.890$$

This is the opposite of the Coffin-Manson case, where Phase 0I-R found the ratio spans a factor
of 7.4 over a plausible exponent range. **Conditional on the form** --- which the gate does not
establish --- the relative life rests only on a metric ratio resolved at 5.8x its
paired-perturbation spread.

![FIG-0J-E](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0j/FIG_0J_E_model_form.png)

![FIG-0J-D](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0j/FIG_0J_D_life_by_architecture.png)

**Absolute and relative uncertainty are not the same thing here, and the asymmetry is the most
useful result of the phase:**

| source | RELATIVE life | ABSOLUTE life |
|:--|:--|:--|
| life-law constant $C$ | **0 --- cancels** | factor **2.77** |
| life-law exponent | **0 --- fixed at 1 by the form** | --- |
| metric numerics, paired | 6.2 pp | 6.6 % |
| **no admissible law** | --- | **UNBOUNDED** |
| **cycle incompatibility** | --- | **UNBOUNDED** |

## The required life

$N_{required}$ = **OPEN**. What was found is categorised and **not promoted**: qualification
counts (1000 cycles, $-40/+125$ °C), accelerated conditions (15-min dwell, 3.6 °C/min), and one
measured characteristic life ($\eta = 1390$, $\beta = 5.4$ at $-40/+185$ °C). **No field mission
requirement exists in any accessible source**, and Sec. 14 forbids promoting the others.

This is structural: **operating-life limits are set by customer-specific qualification
programmes and are not published.** A required life for this system must be declared by its
owner.

Conditional on the Syed form, the **MISSION-LIFE CROSSOVER** band is $N_{required} \in (4266,
6647]$, in which only Z2 is feasible. **Its position is conditional on an unvalidated constant;
its width --- a factor 1.558 --- is not**, because $C$ cancels.

![FIG-0J-G](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0j/FIG_0J_G_mission_sweep.png)

## The electrical cost of reliability, replacing W per µm of warpage

> **$+$1.688 W buys 1.56x fatigue life** --- 8.76 W per decade of $N_f$, for Z1 $\to$ Z2.

That supersedes *W per µm of warpage* for local-reliability decisions. **Z1 and Z4 are not
ranked electrically**: that difference is 0.14$\sigma$ and remains unresolved.

![FIG-0J-F](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0j/FIG_0J_F_electrical_cost.png)

## G2, and the optimizer

| Sec. 23 requirement | status |
|:--|:--|
| 1. defensible predicted fatigue life | **NOT MET** |
| 2. defensible required life | **NOT MET** |
| 3. one attractive candidate fails while another passes | **NOT EVALUABLE** |
| 4. ranking survives uncertainty | **MET** at the metric level |

$$\textbf{G2 = NOT TESTED}$$

All four optimizer-gate conditions were required; two fail outright. **The global optimizer is
not recommended and was not built.**

Phase 0I-R ended with *"a validated metric and no allowable."* Phase 0J ends with *"three
natively-computed metrics whose ranking is model-form independent, no transferable law, and no
requirement"* --- and, unlike before, a precise specification of what each missing piece must
look like. Full detail: `results/phase0j/PHASE0J_LIFE_LAW_AND_MISSION_GATE.md`.

<!-- END GENERATED: phase0j_narrative -->
<!-- BEGIN GENERATED: phase0jr_narrative -->

\newpage

# Phase 0J-R --- Primary Life-Law Access, Reproduction and Transferability Closure (extended by Phase 0K)

**Verdict: SAC/SnAgCu LIFE LAW ADMITTED FOR RELATIVE LIFE ONLY.**
**Z2 outlives Z1 by 1.21--1.38x across four primary-source formulations.**
**Absolute life is CONDITIONAL. G2 is still NOT TESTED --- $N_{required}$ must come from the
system owner.**

## The Phase-0J verdict is superseded, as it said it might be

Phase 0J returned *no admissible SAC305 life law* and recorded the cause as **access**. The
primary papers were then supplied. **Seven of ten database entries change.** Phase 0J also
rejected Syed for the wrong reason: it rejected the paper because the *partitioned* model needs
a two-mechanism creep split our single Norton law cannot produce, but the paper contains
**three** formulations and the author explicitly offers the **total accumulated creep strain**
form as the simplification --- the low-stress mechanism contributes under 5 % of strain and under
2 % of damage for SnAgCu.

## Version control: the corrected constants, and why they are mandatory here

The author-corrected copy states the original ECTC constants *"were not accurate"* due to errors
in data processing. The appended deck gives the mechanism: they were regressed on **first-cycle**
values, and SnAgCu stabilises only after the **2nd** cycle with a **20--30 % reduction**.

| constant | original | **corrected** | ratio |
|:--|--:|--:|--:|
| $C'$ total accumulated creep strain (Eq. 14) | 0.0358 *(superseded)* | **0.0468** | 1.31 |
| $W'$ creep energy density (Eq. 15) | 0.0012 *(superseded)* | **0.0015** | 1.25 |
| $C_I / C_{II}$ partitioned (Eq. 13) | 0.013 / 0.036 | **0.106 / 0.045** | 8.15 / 1.25 |

This project extracts every metric at the **stabilised** cycle. Pairing a stabilised
$\varepsilon$ with a first-cycle-fitted constant would compound the very error the author
corrected and **over-predict life by 31 %**. The version match is a methodological requirement,
not a preference for the newer file.

![FIG-0JR-A](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0jr/FIG_0JR_A_syed_version_audit.png)

## Proving our PEEQ is Syed's $\varepsilon_{acc}$

Syed's metric is accumulated **creep** strain. Two single-element probes settle what CalculiX
actually integrates when `*PLASTIC` and `*CREEP` are both present:

| applied $\sigma$ | `*PLASTIC`? | measured rate | $A\sigma^n$ | $A(\sigma-\sigma_y)^n$ |
|:--|:--|--:|--:|--:|
| 25 MPa | no | 2.8002e-5 | **2.8002e-5** | 1.5222e-8 |
| 25 MPa | **YES** | 1.5154e-8 | 2.8002e-5 | **1.5222e-8** |

and at 25 MPa against a 15.2 MPa yield, PEEQ at the first output is **1.52e-11** where a
rate-independent model would need **5.16e-2**.

**It is a pure viscoplastic OVERSTRESS model with no rate-independent plastic strain.** The yield
card supplies only the threshold. Therefore $M4 \equiv M1$ and $M5 \equiv M3$ **identically**.
Syed reports the same for his own model: plastic is 0.125 % of strain, 0.225 % of energy.

This refines two earlier statements. Phase 0I-R's *"plastic and creep, inseparably"* is true of
the card and misleading about the strain --- there is nothing to separate. And Phase 0I's
assumption that plasticity caps $\sigma_{eq}$ is measurably wrong for the combined deck: the
plastic-only deck caps **exactly** at 30.26 MPa, the combined deck sits at **median 55.8 MPa**,
which is correct overstress behaviour.

## Matching the averaging volume, and why it is not a detail

The source is specific: *"25 micron thick layers of solder at package and board side"*, *"each
layer has two elements across the thickness"*, and **"Life prediction model parameters are only
valid for this thickness."** Our mesh was 37.5 µm --- unable to resolve it. A **targeted local
refinement** of the joint submodel alone gives **2 x 12.5 µm at each face**. Mesh convergence
**3.0--3.2 %** against a predeclared 10 %; stabilisation **0.32--0.56 %**.

| | $M4$ on Syed's layers | Phase-0I core value | ratio |
|:--|--:|--:|--:|
| Z1 | 8.5518e-3 | 6.5117e-3 | **1.313** |
| Z2 | 6.6649e-3 | 4.1789e-3 | **1.595** |
| Z4 | 8.9491e-3 | 7.3196e-3 | **1.223** |

The change is 22--60 % and **different for each architecture**, so it is not a scale factor.

![FIG-0JR-C](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0jr/FIG_0JR_C_metric_definitions.png)

## The reproduction Phase 0J could not attempt

**Tolerances declared beforehand:** reproduce the paper's own $\pm$25 % claim, and require the
two **independently fitted** constants to recover a consistent $w_{acc}/\varepsilon_{acc}$ to
10 %.

| test | result | verdict |
|:--|:--|:--|
| worst error, Table 3 independent validation package | **11.7 %** | **PASS** |
| $w/\varepsilon$ from $C'$ and $W'$ across 4 configurations | 28.78--30.02 MPa, **spread 4.2 %** | **PASS** |

**No digitisation was used** --- every value is a printed table entry.

![FIG-0JR-B](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0jr/FIG_0JR_B_syed_reproduction.png)

## The zero-dwell finding was wrong

Phase 0J reported a triangular waveform with **zero dwell**. The solver's own `NT` output carries
the full hot value **82.8605 °C at t = 0.002 s** --- the first increment of a 300 s step. A ramp
would give 25.0004 °C.

> **The waveform is a SQUARE WAVE: instantaneous step, then a 300 s HOLD at each extreme.
> Syed's TC3 has 5-minute dwells --- exactly ours.**

And the dependence is mild. Over a **30x** change in dwell the absolute metric moves **+17 %
(Z1) / +22 % (Z2)** and the **relative** result moves **$\pm$2 %**, because the overstress
formulation self-limits as $\sigma \to \sigma_y$.

![FIG-0JR-D](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0jr/FIG_0JR_D_dwell_sensitivity.png)

## Where our joint sits --- one thing passes, one does not

| quantity | Syed's calibration | ours | classification |
|:--|:--|:--|:--|
| $\varepsilon_{acc}$ | 0.00213--0.0777 | 0.00666--0.00895 | **INTERPOLATION** |
| $w_{acc}$ | 0.0665--2.424 MPa | 0.905--1.110 | **INTERPOLATION** |
| **$w_{acc}/\varepsilon_{acc}$** | **28.8--30.0 MPa** | **124--136 MPa** | **OUTSIDE by 4.3x** |

Each metric interpolates; **the pair does not**. Our joint dissipates four times more creep
energy per unit creep strain than anything Syed calibrated on. The consequence is visible and is
not hidden: the two models predict **2499** and **610** cycles for Z1 --- a **4.10x**
disagreement, where on Syed's own validation package they agree to 4--7 %. **That is why absolute
life is conditional.**

![FIG-0JR-E](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0jr/FIG_0JR_E_on_syed_calibration.png)

## What is validated: the relative life

| law | Z2/Z1 | Z4/Z1 |
|:--|--:|--:|
| Syed corrected, strain (Eq. 14) | **1.283** | 0.956 |
| Syed corrected, energy (Eq. 15) | 1.206 | 0.984 |
| Schubert SnAgCu strain (slope 1.3) | **1.383** | 0.943 |
| Schubert SnAgCu energy (slope 1.0) | 1.206 | 0.984 |
| **range** | **1.21--1.38** | **0.94--0.98** |

**ROBUST ACROSS ADMISSIBLE LIFE-LAW FAMILIES.** The constant cancels exactly, the
original-versus-corrected version cancels exactly, and alloy, geometry, extraction volume and
cycle are identical between our three architectures so those errors are common-mode. Darveaux
2000 states the same principle independently: *"Since the slopes are consistent, relative fatigue
life predictions should be somewhat independent of the averaging scheme chosen."*

**Phase 0J's 1.558 is withdrawn** --- it was an ALGEBRAIC RATIO on an unmatched volume. **1.283
is a TRANSFER-VALIDATED RELATIVE-LIFE RATIO.** Z4 vs Z1 at 0.94--0.98 is **not resolved** and is
not claimed.

![FIG-0JR-F](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0jr/FIG_0JR_F_life_by_primary_law.png)

## Does Z2's +1.688 W buy a real advantage?

> **YES --- relative lifetime difference validated; absolute life unavailable.**
> **+1.688 W, 1.3 % of 126.1 W, buys 1.21--1.38x solder fatigue life.**

![FIG-0JR-G](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0jr/FIG_0JR_G_electrical_vs_life.png)

## The other branches

**Syed 2001** validates the power-cycle transfer *method* --- transient thermal solve, same
damage model, **no acceleration factor** --- on a **260 s** cycle, 16 assemblies, **+20 %**. Our
cycle is 600 s and the chain is identical. **Schubert 2003** prints the SnAgCu exponents but not
the prefactors, so it gives relative life only --- and it agrees. **Darveaux 2000** is
**INADMISSIBLE for SAC305**: Table 6 was recovered in full and every row is eutectic SnPb. The
mesh objection is now removed; alloy and constitutive model remain. **Vasudevan & Fan 2008** is
an acceleration-factor model, not a damage model, and is handed forward unused.

## G2, and the next blocker

$$\textbf{G2 = NOT TESTED}$$

Requirement 1 is now partially met and requirement 4 is met and strengthened. Phase 0J-R
originally recorded requirement 2 --- a defensible required life --- as the **sole** blocker;
**Phase 0K withdraws that** after testing it formally. Knowing $N_{required}$ does not by itself
give a unique pass/fail, because the admitted absolute-life formulations differ by 4.1x. **Two
pieces are open:** the system mission, and an absolute-life calibration or a decision region
robust to the model-form spread.

**The next blocker is SYSTEM-OWNER MISSION DEFINITION, not another mechanics model.** One further
item would be transformative and is cheap: **a single board-level thermal-cycle test of the
actual DVPD package**, which would fix the constant directly, collapse the 4.1x model-form
spread, and make every relative result here absolute. Full detail:
`results/phase0jr/PHASE0JR_PRIMARY_LIFE_LAW_GATE.md`.

<!-- END GENERATED: phase0jr_narrative -->
<!-- BEGIN GENERATED: phase0k_narrative -->

\newpage

# Phase 0K --- Mission Definition, Absolute-Life Identifiability and G2 Decision Closure (extended by Phase 0K-R)

**Verdict: MISSION REQUIREMENT STILL OPEN --- ABSOLUTE-LIFE CALIBRATION ALSO REQUIRED.**
**Both. The second is not a consequence of the first.**
**G2 remains NOT TESTED. The optimizer is not justified and was not built.**

## Four things that must never be conflated

| | status |
|:--|:--|
| **RELATIVE LIFE** | **VALIDATED** --- Z2/Z1 = 1.21--1.38x across four admitted primary-source formulations |
| **CONDITIONAL ABSOLUTE LIFE** | numerical predictions exist, **NOT VALIDATED** --- the admitted formulations disagree 4.1x |
| **REQUIRED LIFE** | **OPEN** --- no field or product requirement exists anywhere |
| **G2** | **NOT TESTED** |

Nine current-facing statements still described a project that could not predict life, three
phases after it could (**DEFECT #38**). All repaired at the source of truth; six guards added,
each self-tested against the verbatim sentence that was standing and each negative-tested to
failure.

## "N_required is the sole blocker" is false

Phase 0J-R recorded the required life as the only thing standing between the project and a G2
decision. Tested formally at $N_{required} = 1500$:

| | strain family (Eq. 14/16) | energy family (Eq. 15/17) |
|:--|:--|:--|
| Z1 | 2279--2499 $\rightarrow$ **PASS** | 482--610 $\rightarrow$ **FAIL** |
| Z2 | 2925--3206 $\rightarrow$ **PASS** | 581--736 $\rightarrow$ **FAIL** |

Both architectures pass under one admitted family and fail under the other. **Mission definition
alone produces no decision.** There are **TWO OPEN PIECES**: the system mission, and an
absolute-life calibration or a decision region robust to model form.

## The robust decision map, built before any experiment was designed

All four admitted absolute formulations, applied independently over a 601-point log grid.

```
ROBUST ALL PASS        N_required <=   474
MODEL-FORM AMBIGUOUS     474 < N_required <= 3206      a factor of 6.8
ROBUST ALL FAIL        N_required >   3206
```

> **Is there any $N_{required}$ at which all models agree Z1 fails and Z2 passes?**
> Z1 fails under every law only above **2499**. Z2 passes under every law only below **581**.
> **DISJOINT. Zero of 601 grid points. NO.**

The reason is structural: the **model-form spread within one architecture is 5.2x** while the
**architecture separation is 1.21--1.38x**. A 5.2x uncertainty cannot resolve a 1.3x effect at
any requirement. **An experimental absolute-life calibration is NECESSARY before mechanics can
alter the feasible architecture set.**

![FIG-0K-A](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0k/FIG_0K_A_g2_decision_map.png)

## Mission: searched, and genuinely absent

The entire repository and all supplied material were searched for service life, required cycles,
cold boots, qualification targets, field lifetime, availability and duty cycle. **Nothing.**
Every `n_required` in this repository is the **TSV via count**. $N_{required}$ is **USER INPUT
REQUIRED**, now enforced mechanically: the contract file holds only `USER_REQUIRED` / `UNKNOWN`
/ `NOT_APPLICABLE`, and the tool refuses to emit a number without provenance, refuses to treat a
qualification count as a field mission, and refuses to collapse a multi-bin spectrum.

Illustrative only --- never a requirement:

| scenario | $N_{required}$ | region |
|:--|--:|:--|
| 5 y, 1 cold boot/day | 1 826 | **AMBIGUOUS** |
| 7 y, 2 boots/week + 1 workload cycle/day | 3 287 | ROBUST ALL FAIL |
| 5 y, 1 boot/day + 4 workload cycles/day | 9 131 | ROBUST ALL FAIL |
| 3 y, never powered down | 0 | mechanism not life-limiting |

**Every non-trivial illustrative mission lands in the ambiguous band or worse.**

## Auditing "one board-level test fixes everything"

**One condition cannot identify the law.** One measured life is one equation, each law has one
free constant, and both fit it exactly. Residual degrees of freedom for discrimination: **zero**.

**But one condition does more than expected for this particular comparison.** Forced through the
measured point, both laws extrapolate to the other architectures through their own metric ratio:
Z1 becomes exact, **Z2 known to 6.3 %** and Z4 to 3.0 % under *either* law, because the three
architectures sit within 6 % of each other in $w/\varepsilon$. Across 3721 what-if cells the
**ambiguous region vanishes**: 50.8 % all-pass, 47.6 % all-fail, 1.6 % a genuine G2 pass, **0 %
ambiguous**.

What it does **not** license is extrapolation to a **different cycle**, where the two laws
diverge by up to 85 %.

![FIG-0K-E](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0k/FIG_0K_E_calibration_vs_mission.png)

## What actually discriminates the two laws

$$D = \frac{\varepsilon_B/\varepsilon_A}{w_B/w_A} = \frac{(w/\varepsilon)_A}{(w/\varepsilon)_B}$$

**Discrimination comes from spanning $w/\varepsilon$, not from maximising damage.** Eight
candidate profiles were simulated on the graded Syed-matched mesh:

| condition | T range | $\Delta T$ | **$w/\varepsilon$ (MPa)** |
|:--|:--|--:|--:|
| **COLD_SHALLOW** | $-$40 / $+$25 °C | 65 | **209.2** |
| OP_BASELINE | 25 / 82.9 | 57.9 | 126.9 |
| **HOT_SHALLOW** | $+$55 / $+$125 °C | 70 | **113.1** |

The creep law sees the **overstress** $\sigma - \sigma_y(T)$, and $\sigma_y$ is high at low
temperature. **Temperature range moves $w/\varepsilon$ by 85 %; $\Delta T$ alone by 21 %; dwell
by only 14 %.**

| candidate experiment | D | laws differ by | $\sigma$ at $\beta$=6, n=16 |
|:--|--:|--:|--:|
| **COLD_SHALLOW vs HOT_SHALLOW** | **1.849** | **84.9 %** | **6.19** |
| one architecture, two dwells | 1.144 | 14.4 % | 1.4 |
| **two ARCHITECTURES at one profile** | **1.063** | **6.3 %** | **< 1** |

**Two architectures at one profile is nearly blind to model form** --- it validates the relative
claim but cannot identify the law.

![FIG-0K-C](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0k/FIG_0K_C_discrimination.png)

## The minimum identifiable design

> **2 architectures $\times$ 2 conditions $\times$ 16 specimens = 64 packages.**
> Z1 and Z2, at $-$40/$+$25 °C and $+$55/$+$125 °C, 5-min dwells, 3 °C/min.

**Z4 is excluded** on value-of-information: D = 1.03, and its predicted life sits inside the
6.3 % post-calibration spread. **n = 16** gives $>$ 6$\sigma$ at the pessimistic $\beta$ = 6,
matches Syed's own cell size, and sits at the point where the **8 % simulation uncertainty caps
the experiment at 7.7$\sigma$** --- beyond that, specimens buy nothing. Failure definition is
Syed's exact rule, $>$ 300 $\Omega$ confirmed by ten further events, with **mean life** reported
and $\beta$ **estimated, not assumed**.

**This experiment has not been run.** No measurements exist and no constant has been fitted to
hypothetical data.

![FIG-0K-F](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0k/FIG_0K_F_workflow.png)

## The ETM trade-off, preserved and not overstated

> **$+$1.688 W --- 1.3 % of 126.1 W --- buys $+$21--38 % RELATIVE solder-fatigue life.**

Not converted into "buys X cycles". And an honest limit: even after perfect calibration the
robust G2-pass band is only **17 % wide** in $N_{required}$. A 1.2--1.4x advantage reliably buys
**margin**; it flips a **pass/fail** only if the requirement lands in that window.

## G2, priority, and the optimizer

$$\textbf{G2 = NOT TESTED}$$

> **Recommendation: MISSION + EXPERIMENT IN PARALLEL.**

Every non-trivial illustrative mission lands in the ambiguous band or worse, so the mission alone
will probably not decide G2; the calibration alone cannot either, since it needs a requirement to
test against; the two are independent and neither blocks the other.

All four optimizer-gate conditions fail or are unreachable. **THE GLOBAL OPTIMIZER IS NOT
SCIENTIFICALLY JUSTIFIED AND WAS NOT BUILT.** Full detail:
`results/phase0k/PHASE0K_MISSION_AND_ABSOLUTE_LIFE_GATE.md`.

<!-- END GENERATED: phase0k_narrative -->
<!-- BEGIN GENERATED: phase0kr_narrative -->

\newpage

# Phase 0K-R --- Experimental-Domain and Statistical-Design Closure (extended by Phase 0L)

**Verdict: LOW-TEMPERATURE DATA INSUFFICIENT --- ORIGINAL PROFILE WITHDRAWN.**
Two secondary corrections: a within-domain replacement pair was found, and the specimen count
rises from **16 to 34 per cell**. One limitation no design removes: the **stress** domain is
violated by every profile, so the experiment is **ready to execute with a declared limitation,
not frozen**.

## Where the project stands

| | status |
|:--|:--|
| **RELATIVE LIFE** | **VALIDATED** --- Z2/Z1 = 1.21--1.38x across four admitted primary-source formulations. **Unchanged by this phase.** |
| **CONDITIONAL ABSOLUTE LIFE** | model-form uncertain at 4.1x; 5.2x across all four formulations |
| **REQUIRED LIFE** | **OPEN** --- no field or product requirement exists anywhere |
| **ABSOLUTE G2** | needs **BOTH** a mission and a calibration, unless the real $N_{required}$ falls where all admitted models already agree |
| **EXPERIMENT** | designed, domain- and power-audited, **ready to execute with a declared limitation** |
| **NEXT WORK** | mission input **and** experiment preparation, **in parallel** |

## DEFECT #39

The Phase-0K *narrative* was current; the *generated* current-status fragments were not. "Exact
next work" still read **"PHASE 0K --- SYSTEM-OWNER MISSION DEFINITION"** and still asserted the
remaining blocker was a required life --- the exact claim Phase 0K withdrew. **No Phase-0K result
appeared in current-facing text at all.** Repaired at the source of truth; four new guards, each
self-tested on the verbatim standing sentence and negative-tested to failure; and the **final
Markdown and final PDF text** re-audited after generation, not before.

## The constitutive domain, read from the card

| | calibration |
|:--|:--|
| **creep** (Yuan 2023 Table 26, 19 points) | **45, 80, 115, 150 °C** · **7.51--15.92 MPa** |
| **plastic** (Chaboche) | $-$40 ... 122 °C |

**The card rows at $-$40, 0 and 25 °C are already extrapolated on creep.** Every result this
project has produced uses a cycle whose cold half sits at 25 °C, 20 K below the floor.

## The $-$40 °C profile is withdrawn

| COLD_SHALLOW $-$40 $\rightarrow$ $+$25 °C | |
|:--|:--|
| **damage accumulated below the 45 °C floor** | **100 %** |
| damage-weighted median driving overstress | **114.9 MPa**, the worst of any candidate |
| classification | **INVALID FOR MODEL-DISCRIMINATION DESIGN** |

**The model cannot be extended.** Seven targeted searches: the low-temperature SAC305
literature exists and is the **wrong regime** --- 4 of 5 retrieved constitutive works are
**high-strain-rate/impact**, 0 are creep. At $-$40 °C the homologous temperature is
**0.475**, below where creep governs, so steady-state creep tests there are impractically long
and are not performed --- and Syed 2001 explicitly excludes fast loading from the creep
framework. **The model is NOT extended**, and no validation document is produced, because
producing one would mean inventing the data it validated.

> **The Phase-0K claims D = 1.849, 85 % separation and 6.19 σ are WITHDRAWN as current.**

![FIG-0KR-A](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0kr/FIG_0KR_A_domain.png)

## A within-domain replacement

Eight profiles with $T_{min} \ge$ 45 °C were solved. The exploitable physics: the creep law sees
the **overstress** $\sigma_{eq}-\sigma_y(T)$, and $\sigma_y$ falls with temperature, so a
cold-in-domain cycle sustains far more stress per unit creep. **Within the domain, temperature
band moves $w/\varepsilon$ by 44 %; dwell by only 2--3 %.**

> **SELECTED: 45 $\rightarrow$ 125 °C  +  110 $\rightarrow$ 150 °C, 5-min dwells, 3 °C/min**
> **D = 1.4395**, 44.0 % separation, expected discrimination **Z = 3.44**.

Selection was **composite, not max-D**: a 15-min-dwell variant scores D = 1.4721 but costs
**46 extra days per cell** for a 2 % gain and was rejected on the predeclared rule. **The
redesign costs 41 % of the discriminating power and buys validity.**

![FIG-0KR-B](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0kr/FIG_0KR_B_pair_comparison.png)

## The limitation no profile removes

Phase 0J-R checked the **end-of-hold** overstress ($\approx$ 15 MPa, inside the window) and
called the card "near its calibrated range". **That was optimistic** --- end-of-hold is the
cycle *minimum*. Weighted by the solver's own $\Delta$PEEQ increments:

| profile | median driving overstress | damage above 16 MPa |
|:--|--:|--:|
| operating baseline 25/83 °C | **69.4 MPa** | **99.1 %** |
| 45/125 °C (selected) | 91.4 MPa | 98.9 % |
| 110/150 °C (selected) | 54.3 MPa | 93.7 % |

**3.4--7.2x above the top of the fitted window, in every profile including the one all current
results rest on.** It is a property of how hard this package loads its joints and **cannot be
fixed by choosing a profile.** It does **not** disturb the relative-life result: the same
extrapolation applies identically to all three architectures, so it is common-mode and cancels
in a ratio.

## $\beta$ = 6 is not conservative

**16 primary cells** from Syed 2004 Table 2b and George 2010 Tables 4 and 6:

| | $\beta$ |
|:--|:--|
| range | **5.1 -- 20.4** |
| **SAC305 only** | **5.1, 5.4, 5.6, 10.1** |
| cells below 6 | **4 of 16 (25 %)** |

> **$\beta$ = 6 is the 25th percentile, not a conservative bound.** The observed minimum
> **5.1** is used instead.

![FIG-0KR-D](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0kr/FIG_0KR_D_beta.png)

## n = 16 tested, not defended

| question | effect size | min n at $\beta$ = 5.1 | at n = 16 |
|:--|:--|--:|:--|
| **Q1 --- which life law?** | D = 1.4395 | **10** | Z = 3.41 **ADEQUATE** |
| **Q2 --- is Z2/Z1 real?** | 1.110 / 1.2485 | **34** | Z = 2.49 **MARGINAL** |

> **n = 16 is SUFFICIENT for Q1 and INSUFFICIENT for Q2.**
> One campaign answering both needs **n = 34 per cell --- 4 cells, 136 packages.**

![FIG-0KR-E](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0kr/FIG_0KR_E_power.png)
![FIG-0KR-F](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0kr/FIG_0KR_F_matrix.png)

## Three wordings corrected

**"6.19 sigma"** is $\ln(D)/\sqrt{2/(\beta^2 n)+\sigma_{sim}^2}$. It omits uncertainty in
$\beta$ itself, censoring loss and the constitutive-domain error in the predicted D. **Renamed
EXPECTED DISCRIMINATION Z-SCORE**; "σ" is no longer used for it.

**"the robust G2 band is 17 % wide"** --- denominator attached: the window is
$(1.000, 1.1665]$ in $N_{required}/N_{f,Z1}$, i.e. **16.65 % of the measured Z1 life**, or
**0.0669 decades**.

**"27.6 % of the range"** --- it is **logarithmic**: the ambiguous interval spans
**0.83 decades**, about 27.6 % of the three-decade 100--100 000-cycle log sweep. As a linear
fraction it would be 2.7 %, and that figure is not used.

**Terminology frozen:** CONDITION (one profile) · CELL (one architecture × one profile) ·
CAMPAIGN (the whole experiment). *A single CONDITION cannot identify the fatigue-law family; a
multi-condition CAMPAIGN can.*

## Unchanged

$N_{required}$ is still **OPEN**. **Mission and experiment still proceed in parallel** ---
verified against the updated decision map, not assumed. **The optimizer remains forbidden**: no
condition of the gate is met. Full detail:
`results/phase0kr/PHASE0KR_EXPERIMENTAL_CLOSURE.md`.

![FIG-0KR-G](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0kr/FIG_0KR_G_workflow.png)

<!-- END GENERATED: phase0kr_narrative -->
<!-- BEGIN GENERATED: phase0l_narrative -->

\newpage

# Phase 0L --- High-Stress SAC305 Constitutive Closure (extended by Phase 0L-R)

**Verdict: C --- HIGH-STRESS MODEL-FORM UNCERTAINTY PRESENT BUT Z2/Z1 RANKING SURVIVES.**

Two defects confirmed and two more found. The relative-life ordering holds under every admissible constitutive model; its magnitude does not, and the claim that the stress extrapolation is common mode is **withdrawn** in favour of a measured figure.

## What the solver actually integrates

Traced from the CalculiX 2.23 source and confirmed against the binary over 7603 single-element increments:

$$ \dot{\varepsilon}_{in} = A(T)\left(\sigma_{vm} - \sigma_y(\bar\varepsilon_{in})\right)^{n(T)}, \qquad \dot{\varepsilon}_{in} \equiv 0 \ \text{ for } \ \sigma_{vm} \le \sigma_y $$

Median relative error of that form against the solver: 1.2e-5. The manual's stated form on the full von Mises stress is wrong by a median factor of 14.4. There is no rate-independent plastic strain in a `*VISCO` step, m = 0, and the temperature interpolation is linear in A rather than Arrhenius.

## DEFECT #40 --- CONFIRMED

The card was fitted against total applied stress and is consumed as an overstress. The overstress is non-positive at **16 of the 19 calibration points**, so the card reproduces **0 of 19** of its own source points when fed back through the solver: 16 return exactly zero and three are low by 4.7e7, 1.8e12 and 2.4e5. A consistent refit is not constructible (0 usable points at 45 and 80 C), so the resolution is to remove the yield threshold, which is what the CalculiX manual itself prescribes for creep below yield.

## DEFECT #41 --- the creep data is a different alloy

The 19 points are Yuan 2023 **Table 5**, not "Table 26"; the paper has eleven tables. Yuan sources them to Xiao & Armstrong 2005, alloy **Sn3.9Ag0.6Cu**, not SAC305. The yield half of the card is SAC305 but two model layers from measurement. No transferability evidence exists; 344 works were screened and none is retrievable in this environment.

## Was the extrapolation common mode?

Tested against a tolerance predeclared and hashed before any ratio under an alternative model existed.

| quantity | min | median | max | S | classification |
|---|---|---|---|---|---|
| Syed2004 Eq14 strain | 1.1887 | 1.2184 | 1.2875 | **0.0811** | PARTIAL CANCELLATION |
| Schubert2003 strain | 1.2520 | 1.2928 | 1.3889 | **0.1059** | PARTIAL CANCELLATION |
| Syed2004 Eq15 energy | 1.1710 | 1.2735 | 1.3017 | **0.1026** | PARTIAL CANCELLATION |
| Schubert2003 energy | 1.1710 | 1.2735 | 1.3017 | **0.1026** | PARTIAL CANCELLATION |

**PARTIAL CANCELLATION.** The ranking survives in every model, every law and every profile; the magnitude does not. Revised Z2/Z1 relative life **1.17 to 1.39**, against 1.21 to 1.38 before Phase 0L.

![FIG-0L-G](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0l/FIG_0L_G_ratios.png)

## Where the damage actually accumulates

![FIG-0L-E](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0l/FIG_0L_E_damage_weighted.png)

## Consequence for the experiment

| model | D | n per cell | packages |
|---|---|---|---|
| `M0_COARSE` | 1.6774 | 16 | 64 |
| `M0_FINE` | 1.6548 | 15 | 60 |
| `M1` | 1.6733 | 48 | 192 |
| `M1_NHI` | 1.4001 | 68 | 272 |
| `M1_NLO` | 1.9837 | 40 | 160 |

The incumbent model reproduces the Phase-0K-R design exactly (D = 1.4395, n = 34), verifying the method. Under the corrected model the architecture question needs **68 per cell, 272 packages**. The 34-per-cell design does not survive and the experiment stays unfrozen.

![FIG-0L-H](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0l/FIG_0L_H_experiment.png)

## Standalone deliverable

Phase 0L also produced a separate, non-chronological current-framework audit report for an independent reviewer: `results/ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.md` and its PDF. It is not part of this chronological record and is not reproduced here.

<!-- END GENERATED: phase0l_narrative -->
<!-- BEGIN GENERATED: phase0lr_narrative -->

\newpage

# Phase 0L-R --- Constitutive Robustness, Report Propagation and Auditor-Dossier Closure (extended by Phase 0M)

**Verdict: C --- Z2 > Z1 ORDERING ROBUST, RELATIVE-LIFE MAGNITUDE REMAINS CONDITIONAL.** Three defects confirmed, one of them found inside the framework's own post-processing, and one Phase-0L conclusion reversed.

## The ordering is robust for a structural reason

All 12 architecture ratios exceed unity, the smallest being 1.1493. More importantly, the ordering originates **upstream of the solder model**: the global thermoelastic model imposes a corner shear of 2.7486 um on Z1 against 2.0796 um on Z2 --- 32 % larger, because Z1's substrate is 1.30 mm against Z2's 0.30 mm --- and that model contains no solder constitutive law at all. The local model only compresses 1.322 to 1.197. Stated without overreach: the global package supplies a constitutive-law-independent deformation driver favoring Z2, and every presently testable constitutive/life-law combination preserves that ordering. That is a structural statement about the driver, not a theorem about every conceivable law.

The magnitude is a **conditional envelope of 1.19 to 1.22** on the strain family, widening to 1.15--1.30 if the ranking-only energy family is included. *Validated relative life* is WITHDRAWN as wording.

## Where the damage is --- correcting Phase 0L

| damage-weighted sigma_vm | Z1 | Z2 |
|---|---|---|
| p10 | 35.9 | 33.2 |
| p25 | 60.0 | 53.1 |
| median | 81.9 | 80.6 |
| p75 | 110.3 | 109.0 |
| p90 | 144.9 | 143.4 |
| p95 | 173.6 | 170.4 |
| max | 184.2 | 183.5 |

Only 0.22 % (Z1) and 0.18 % (Z2) of per-cycle damage falls inside the 7.51--15.92 MPa calibration window. Phase 0L reported medians of 78 and 72 MPa and concluded the architectures extrapolate differently; weighted properly, element by element, they are **81.9** and **80.6 MPa, 1.5 % apart**. That earlier separation was an artifact of weighting a layer-averaged stress, and is WITHDRAWN. What differs is the peak: 151.6 MPa against 128.7, and 8.3 % of the cycle above 100 MPa against 5.5 %.

![FIG-0LR-A](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0lr/FIG_0LR_A_histories.png)

## Numerics versus physics

| quantity | NUMERICS alone | CONSTITUTIVE model alone |
|---|---|---|
| D (law discrimination) | **+16.5 %** | -0.2 % |
| Z2/Z1 strain ratio | +0.2 % | **-6.5 %** |
| strain metric magnitude | +0.3 % | **+32.2 %** |
| energy metric magnitude | **+17.8 %** | +10.5 % |

Of the move in D from the Phase-0K-R value of 1.4395, **102 % is energy-integration resolution and -2 % is the material model.** D is a numerics story; the architecture ratio is a physics story.

![FIG-0LR-D](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0lr/FIG_0LR_D_decomposition.png)

## DEFECT #46 --- found by independent reimplementation

`parse_temperature` kept the FIRST temperature block at a given printed time while `parse_tensors` keeps the LAST. CalculiX prints the same rounded time on both sides of a step boundary, so tensors and temperature came from opposite sides of all 11 boundaries, with the parsed temperature wrong by about 55 K. The thermal strain is hydrostatic, so this injected a spurious VOLUMETRIC inelastic strain into a quantity that must be isochoric --- trace 8.7e-4 against 2.9e-6 --- and inflated every inelastic-energy number by **18.5 %**. PEEQ was unaffected, because it is read from the solver rather than reconstructed. Fixed; agreement with the independent implementation improves from 18.5 % to 0.76 %.

## The Anand family is re-admitted

Phase 0L rejected the Anand FORM on the strength of the Yuan 2023 EINN+BI parameter set, which misses the only available creep data by a median factor of 1240. An open-access source retrieved in this phase (Yamin et al. 2025, doi:10.11113/jurnalteknologi.v87.23172) gives a different Anand set for SAC305, fitted to the SAME Motalab data, which lands within a median factor of **1.76** of those measurements after a four-to-six-decade extrapolation in rate. Both failures were properties of the parameter set, not the form. The rejection is reversed.

It still cannot be integrated at package stresses. Reduced to the Norton form CalculiX accepts, the Anand law needs n = 12--19 over the package's stress window, and this solver has an **integrability ceiling at n = 9--10**: the joint converges at n = 8.13 and 8.97 and fails at n = 10.04 and 11.86.

> **Predeclared model-form gate: INSUFFICIENT EVIDENCE** --- two constitutive families (Norton and Anand) can currently be PARAMETERIZED in the relevant regime, and only ONE of them can presently be INTEGRATED through the production package solve; the gate requires three families parameterised and integrated. No model-form robustness claim is made from the replay; the structural argument above is separate and stands on its own.

![FIG-0LR-E](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0lr/FIG_0LR_E_ratios.png)

## DEFECT #44 --- report propagation, and DEFECT #45 --- experiment priority

21 stale current-facing claims were found across the two reports. In this report they clustered in three generated blocks, chief among them an Executive Summary that contained no mention of Phase 0L at all. They are repaired at source.

The board-level campaign is **re-sequenced behind material characterisation**. Its specimen count is set by the simulation-uncertainty floor, not by Weibull scatter: the ceiling on the discrimination Z-score is 3.61 against a target of 3.0, and halving that floor takes the campaign from 48 specimens per cell to 18. Worse, fitting an absolute-life constant on top of an extrapolated constitutive model buries the constitutive error inside the fitted constant.

![FIG-0LR-G](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0lr/FIG_0LR_G_ladder.png)

## Literature

**HIGH-STRESS SAC305 DATA IDENTIFIED BUT ACCESS-GATED.** 632 works screened on axes other than the word *creep*; four P0 and five P1 primary sources sit behind institutional access, two of them reported open by Unpaywall but refused to scripted fetches. One retrieval already reversed a Phase-0L conclusion. See `results/phase0lr/HIGH_STRESS_PAPER_DOWNLOAD_REQUEST.md`.

<!-- END GENERATED: phase0lr_narrative -->
<!-- BEGIN GENERATED: phase0m_narrative -->

\newpage

# Phase 0M --- Geometry-Resolved Power Delivery, Component-Level Architecture, Cooling and ETM-Coupling Audit (extended by Phase 0M-R)

**Verdict: G --- MULTIPLE MISSING PHYSICAL COUPLINGS ARE FIRST ORDER; OPTIMIZATION STILL PREMATURE.** Phase 0M is an audit and model-generalization gate. It did not build the optimizer, did not run an architecture DOE, and did not implement physics merely because it exists.

## Residual Phase-0L-R closure

DEFECT #46 is eliminated at the root rather than patched. CalculiX `ME` --- the mechanical strain, total minus thermal --- is now requested in the deck, the inelastic strain is reconstructed as `eps_in = ME - C^-1(T):S`, and the temperature itself is recovered from the same output block through `tr(E - ME) = 3 alpha (T - T_zero)`. No separately parsed temperature block appears anywhere in the energy path, so the class of error cannot recur.

| model | arch | W production | W solver-coherent | ratio | isochoric residual, ME | isochoric residual, Python |
|---|---|---|---|---|---|---|
| M1 | Z1 | 1.19157 | 1.20113 | 1.0080 | 1.91e-03 | 3.17e-02 |
| M1 | Z2 | 0.90762 | 0.91776 | 1.0112 | 1.97e-03 | 3.93e-02 |
| M0_COARSE | Z1 | 1.00874 | 1.01991 | 1.0111 | 2.15e-03 | 3.53e-02 |
| M0_COARSE | Z2 | 0.72697 | 0.73830 | 1.0156 | 2.29e-03 | 4.65e-02 |
| M1_NLO | Z1 | 1.31014 | 1.32168 | 1.0088 | 2.02e-03 | 3.23e-02 |
| M1_NLO | Z2 | 0.94187 | 0.95328 | 1.0121 | 2.06e-03 | 4.02e-02 |
| M1_NHI | Z1 | 0.98568 | 0.99351 | 1.0079 | 1.76e-03 | 3.13e-02 |
| M1_NHI | Z2 | 0.79220 | 0.80080 | 1.0109 | 1.85e-03 | 3.86e-02 |
| M2_ANAND | Z1 | 1.08972 | 1.09936 | 1.0088 | 1.81e-03 | 3.14e-02 |
| M2_ANAND | Z2 | 0.84656 | 0.85668 | 1.0120 | 1.89e-03 | 3.88e-02 |

The Phase-0L-R fix was correct and its residual is now bounded: the two routes agree to 0.79 to 1.56 %. On the assumption-free test --- inelastic flow must be isochoric --- the ME route is **16 to 20 times cleaner**. Recomputed Z1/Z2 inelastic energy: 1.20113 against 0.91776 MJ/m3, ratio **1.3088**.

One authoritative specimen-count provenance table now exists, because four counts were live and had been quoted against each other:

| phase | n / cell | packages | status | model | D |
|---|---|---|---|---|---|
| 0K-R | **34** | **136** | HISTORICAL | `M0_COARSE` | 1.4395 |
| 0L | **68** | **272** | HISTORICAL | `M1_NHI (worst case across admitted models)` | 1.4001 |
| 0L-R | **48** | **192** | CURRENT / CONDITIONAL | `M1 (the selected model)` | 1.7256 |
| 0L-R counterfactual | **16** | **64** | NUMERICS-ONLY COUNTERFACTUAL | `M0_COARSE (the INCUMBENT physics)` | 1.7174 |

The theorem-like wording *any monotone solder law MUST rank Z1 worse* is withdrawn from both reports, the status file and the two generators that produce them. The licensed statement is that the global package supplies a constitutive-law-independent deformation driver favoring Z2, and every presently testable constitutive/life-law combination preserves that ordering.

## The TSV radius law

The hypothesis under test was *increasing TSV radius decreases ohmic loss but decreases density*. It is true for one via. For a FIELD it depends entirely on the allocation policy, and under the policy the reference framework actually uses it is false in a strong sense:

$$R_{field} = \frac{\rho h}{A_c}\cdot\frac{J_{max} A_c}{I} = \frac{\rho h J_{max}}{I}$$

The conductor cross-section cancels **identically** --- not merely the radius, so the result is independent of via shape and of the liner too. Three corollaries follow: the IR drop `rho h J_max` does not depend on the current; the loss `I rho h J_max` is LINEAR in current, not quadratic; and the copper fraction `I / (J_max A_field)` contains neither the radius nor the height, so the effective conductivity, modulus and CTE do not move with radius either. **Derating harder --- a lower `J_max` --- lowers the loss.** Measured over r = 2.5 to 50 um the field resistance moves 0.07 % under minimum-capability allocation and 314 % under fixed-count allocation.

![FIG-0M-A](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0m/FIG_0M_A_tsv_allocation.png)

*FIG-0M-A. Single via against via field. The first panel shows the intuition holding for one via; the second shows it cancelling for a minimum-provisioned field.*

![FIG-0M-B](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0m/FIG_0M_B_tsv_coupling.png)

*FIG-0M-B. One TSV variable seen in four domains at once.*

## Current crowding is a function, not a constant

No DC conduction solver was installed, so one was built and verified: exact on a uniform bar at every mesh, and within 0.9 % of the analytic spreading resistance `rho/(4a)` on a contact resolved by six cells per radius. Across 107 converged transition geometries **`K_crowd` spans 0.606 to 1.483**, a factor of 2.45, against the single constant 1.326 the framework applies to BGA, C4, TSV and microbump alike. The excess resistance `dR` is length-independent to five decimal places while `K_crowd` is not, so `dR` is the transferable quantity and `K_crowd` is an artifact of how much bulk conductor is attached to the transition.

![FIG-0M-C](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0m/FIG_0M_C_crowding_map.png)

*FIG-0M-C. Current density through a TSV, its landing pad and the RDL trace.*

## Intra-converter routing did not exist

Of the three routing levels, the framework had two. Intra-converter metallization --- the metal between the input pads, the switches, the flying capacitors, the inductors and the output pads --- was absent entirely. It is worth **4.06 to 39.31 W** system-wide, 0.41 to 3.93 % of the load, against a converter loss of 125.26 W. There is no double counting: the upstream loss model contains every device and passive parasitic and no metallization at all.

It does not change the architecture ranking, because the converter cell is the same compiled design in Z1, Z2 and Z4 and the term is common-mode. What it does expose is a feasibility failure the framework could not see: **the VR output plane needs 8.6 times the available tile width** to stay inside the sourced copper current-density envelope at the reference 10 um single-layer RDL.

![FIG-0M-D](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0m/FIG_0M_D_routing_graph.png)

*FIG-0M-D. The intra-VR component-terminal graph and the three routing levels.*

## Component partitioning was already assumed, and never checked

`_compute_area` in the upstream converter sizing returns `max()` over the four component classes, not `sum()`. Four-layer vertical stacking is therefore already assumed --- by the area model and by nothing else. The electrical, thermal and mechanical models all place the VR as a single lumped block, and nothing verifies that the four layers exist in a given architecture.

| template | levels | stack height | array footprint | fits the 500 mm2 die shadow |
|---|---|---|---|---|
| `T0_SINGLE_LEVEL` | 1 | 685 um | 882.5 mm2 | **False** (1.76) |
| `T1_EMBEDDED_4LAYER` | 4 | 2071 um | 274.9 mm2 | **True** (0.55) |
| `T2_BACKSIDE_CHIPLET` | 3 | 1455 um | 539.5 mm2 | **False** (1.08) |
| `T3_POWER_DIE` | 3 | 1455 um | 539.5 mm2 | **False** (1.08) |
| `T4_SPLIT_SC_BUCK` | 2 | 1301 um | 470.9 mm2 | **True** (0.94) |
| `T5_SWITCH_INTERPOSER_IND_EMBEDDED` | 2 | 1195 um | 735.5 mm2 | **False** (1.47) |
| `T6_CAPS_NEAR_DIE` | 3 | 1455 um | 539.5 mm2 | **False** (1.08) |
| `T7_IND_SUBSTRATE_ACTIVE_BACKSIDE` | 2 | 1195 um | 735.5 mm2 | **False** (1.47) |

**A single-level VR misses the die shadow by 1.76x**, so vertical partitioning is a precondition rather than an optimization. Z2 and Z4 as three-level stacks are 8 % over and need a fourth level. `T4_SPLIT_SC_BUCK`, which splits by voltage domain, is the only two-level template that fits.

![FIG-0M-E](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0m/FIG_0M_E_partition_templates.png)

*FIG-0M-E. Component-partition templates against height and die-shadow area.*

## Z5 re-audited: the number survives, the class conclusion does not

Traced from rail voltage to `P = I^2 R`: **768.072 W**, equivalent loop resistance **0.76807 mOhm**, 0.2999 loop squares on a 2.5611 mOhm/sq stack, IR drop 0.7681 V on a 1 V rail. Grid-converged to 0.15 %.

It did not inherit PCB routing assumptions, and the check runs the other way: the PCB row of the same source table is **4.56 times more conductive per square** than the RDL row, because 152 um of copper at 50 % occupancy beats two 10 um layers at 83 %. Had Z5 used PCB geometry it would have reported about 169 W. No defect is logged.

The CLASS conclusion does move. Feeding the same 1 V rail from four die edges cuts the lateral loss 4.5x; a 12 V lateral rail cuts it 144x. What is eliminated is the one-sided low-voltage lateral topology, not 2.5D. No lateral variant beats the vertical architectures, and at 48 V the family degenerates into vertical delivery under another name.

![FIG-0M-F](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0m/FIG_0M_F_z5_decomposition.png)

*FIG-0M-F. Z5: PCB against RDL per square, loss against gap, and the voltage family.*

## Thermal homogenization, decided by explicit geometry

Three candidate models disagreed by up to 80 % on the same TSV array, so the question was settled by finite volumes on explicit unit cells with a predeclared 10 % / 25 % acceptance band. The rule of mixtures is essentially exact along the vias; Maxwell-Garnett is conditional across them; and the pre-existing framework's transverse model is rejected at four of the five geometries and conditional at the fifth --- never accepted --- 19 to 74 % low, because it puts the liner in series with the copper when heat can flow around the via.

The RDL is the most anisotropic layer in the package --- **154x to 276x** between along-line and across-line conduction --- and the framework gives it one isotropic value. A caveat the audit states itself: these cells are single-direction line layers; a meshed plane is far less anisotropic.

![FIG-0M-G](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0m/FIG_0M_G_k_tensors.png)

*FIG-0M-G. Anisotropic effective conductivity, and which homogenization survives.*

## Cooling: the largest single gap

The Robin coefficient `h_top = 166 000 W/m2K` was inverse-calibrated to reach 84 C. Derived instead from channel geometry and flow with source-backed correlations, three things appear that the calibrated boundary hides.

At the source's stated 1.6 g/s the coolant temperature rise for 1125 W of heat is **168 K**, which single-phase water cannot do; 26.9 g/s is needed for a 10 K rise. No laminar architecture reaches 166 kW/m2K --- the best gets 0.70x, and the calibrated value needs 50 g/s in the transitional regime, **74 W of pumping power, 7.4 % of the load**, and 1.46 MPa of pressure drop, none of which is charged anywhere. And because the sink is a single temperature, the boundary cannot produce a streamwise gradient.

Imposing the real coolant rise on the same global model, changing nothing else, moves the die warpage by up to **8.19 %** and `T_max` by **11.3 K**. Cooling mass flow is therefore a MECHANICAL design variable, and the uniform boundary sets its effect to zero by construction.

![FIG-0M-H](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0m/FIG_0M_H_cooling.png)

*FIG-0M-H. What physical cooler stands behind one calibrated coefficient.*

## Missing mechanics, measured where it could be

Ten of twelve mechanisms are not modelled. Six are P1: organic-substrate and board viscoelasticity, underfill / mold viscoelasticity, assembly / cure / reflow prestress, residual stress from process history, interface delamination / cohesive zone, TSV / RDL cracking or plasticity. Two were measured rather than classified by assertion.

**Polymer stiffness.** Halving the organic board's modulus moves the Z1 corner shear by about 12 % and the Z1/Z2 driver ratio by -3.18 %, against a relative-life envelope that itself spans 2.5 %. Underfill and TIM modulus move the ratio by less than 0.05 %. It is P1 rather than P0 because the effect is common-mode: the ordering is untouched at every modulus tried. What is not settled is the TIME dependence, and no DMA data for the specific laminate exists here, so a Prony series cannot be fitted.

**Assembly prestress.** With a reflow cool-down from 217 C prepended, the stabilised-cycle Z1/Z2 strain ratio moves from 1.2000 to 1.1987, a shift of -0.11 %.

**Rate-independent plasticity is not needed** and adding it to a unified viscoplastic law would double-count, because Anand and Norton both represent the total inelastic strain. **Moisture is out of scope**, declared rather than omitted: the publication claim is dry steady operating ETM. **Cohesive zones are not added**, because their traction-separation laws and fracture energies are not sourced and inventing them would put a fabricated parameter at the centre of a failure prediction.

## The coupling matrix, with the size of every absent arrow

| arrow | size | against | verdict |
|---|---|---|---|
| M to E, elastic geometry | 0.16 % on R | 22.8 % from rho(T), already modelled | **negligible, 137x smaller** |
| M to T, TIM bond line | 1.5 K at a 4 % change | 51 K junction rise | second order, 2.9 % |
| M to E, contact pressure | zero | -- | not applicable; every interface is metallurgical |
| DAMAGE to E, cracked area | +33 % R at 25 % lost | 22.8 % | **material, once damage exists** |
| DAMAGE to T, delamination | +12.5 K at 25 % | 51 K | **material, once damage exists** |
| EM voiding to E | **OPEN** | -- | the current-density limit itself is unsourced |

The framework is at **ETM-L1**, `E <-> T -> M`. That is sufficient for architecture ranking, because the absent arrows are 0.7 % and 2.9 % of terms already present and are common-mode across architectures. **ETM-L3** would be required to predict failure progression, and nothing in this project currently claims to.

![FIG-0M-I](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0m/FIG_0M_I_coupling_matrix.png)

*FIG-0M-I. Every coupling arrow, present and absent, with its measured magnitude.*

![FIG-0M-J](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0m/FIG_0M_J_priority_ladder.png)

*FIG-0M-J. The physics-priority ladder.*

## Does any new dimension change the ranking?

| TSV geometry | copper fraction | du Z1 | du Z2 | Z1/Z2 | ratio shift | die warpage Z1 |
|---|---|---|---|---|---|---|
| `baseline` | 0.1963 | 2.7486 | 2.0796 | 1.3217 | 0.00 % | **0.00 %** |
| `d_x0.5_p_x1` | 0.0491 | 2.6501 | 2.0341 | 1.3029 | -1.42 % | **-15.73 %** |
| `d_x1.5_p_x1` | 0.4418 | 2.9233 | 2.1598 | 1.3535 | 2.41 % | **28.09 %** |
| `d_x1_p_x0.7` | 0.4007 | 2.8931 | 2.1459 | 1.3482 | 2.00 % | **23.23 %** |
| `d_x1_p_x1.5` | 0.0873 | 2.6753 | 2.0457 | 1.3078 | -1.05 % | **-11.73 %** |
| `d_x2_p_x2` | 0.1963 | 2.7486 | 2.0796 | 1.3217 | 0.00 % | **0.00 %** |

The largest shift any interconnect-geometry change produces in the Z1/Z2 driver ratio is **2.41 %** (`d_x1.5_p_x1`) --- comparable to the whole width of the relative-life envelope, so not negligible, but the ratio never approaches unity and the ORDER never changes. **Interconnect geometry does not change the architecture ranking.**

The ABSOLUTE mechanical response is a different matter. The same changes move the die warpage by **-15.7 % to +28.1 %**, because the TSV field's copper fraction sets the effective CTE and stiffness of the entire through-substrate layer. That was invisible while the field was a frozen homogenized block. The control case `d_x2_p_x2`, which doubles the diameter and the pitch together and therefore holds the copper fraction constant, reproduces the baseline to the last digit --- confirming that the mechanical model responds to the copper FRACTION and not to the via.

## Verdict and what follows

Of the seven candidate verdicts, **G** is the only one the evidence supports as dominant. **A** fails because the model is not closed: the electromigration limit is open, no first-stage converter compiles below 48 V, meshed-plane RDL anisotropy is unvalidated and no cohesive parameters exist. **B** and **C** fail on measurement --- both change feasibility, neither changes order. **D** fails because the 768 W survives on interposer geometry and Phase 0I-R had already narrowed the class claim. **F** is contradicted by four separate results. **E** is TRUE and is the largest single instance of G rather than an alternative to it.

The optimizer remains **FORBIDDEN**. Of its six preconditions, none is fully met after Phase 0M and two moved from NO to PARTIAL.

<!-- END GENERATED: phase0m_narrative -->

<!-- BEGIN GENERATED: phase0mr_narrative -->

\newpage

# Phase 0M-R --- production-coupling closure

Phase 0M ended by naming five first-order models that existed as validated SCREENING tools
and drove nothing. Phase 0M-R wired them into the production path and replayed a small frozen
architecture set through it, to ask one question: **which Phase-0M conclusions survive when
those models actually set P_elec, T(x,y,z) and M(x,y,z)?**

This is an integration and falsification gate, not a search. No optimizer was started and no
architecture DOE was run.

## What changed in the production path

| model | Phase 0M | Phase 0M-R |
|---|---|---|
| intra-VR routing | measured in Phase 0M, not yet summed | in the Phase-0M-R total, template-aware |
| transition resistance | one global constant, 1.326 | per class, solved exactly, cross-validated |
| cooling | inverse-calibrated Robin coefficient | physical microchannel with a streamwise coolant rise |
| heat deposition | one lumped load | per layer, energy-checked |
| temperature feedback | package maximum | the converter's own layer temperature |

## What integration did to the answers

| architecture | system loss (W) | peak temperature (C) | die warpage (um) | corner-joint shear (um) |
|---|---|---|---|---|
| Z1_EMBEDDED | 125.10 -> **141.78** (+13.3 %) | 84.87 -> **123.53** (+38.7 K) | 20.04 -> **25.37** (+26.6 %) | 2.7447 -> **4.2803** (+55.9 %) |
| Z2_BACKSIDE | 126.19 -> **143.61** (+13.8 %) | 83.31 -> **130.31** (+47.0 K) | 17.24 -> **22.62** (+31.2 %) | 2.0754 -> **3.4101** (+64.3 %) |
| Z4_POWER_DIE | 123.64 -> **134.74** (+9.0 %) | 83.30 -> **96.32** (+13.0 K) | 30.14 -> **35.95** (+19.3 %) | 2.9744 -> **3.6681** (+23.3 %) |

![FIG-0MR-I](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0mr/FIG_0MR_I_before_after.png)

*FIG-0MR-I. The same three architectures through the Phase-0M production path and the
Phase-0M-R one. The bars that matter are the last pair: the reliability driver.*

## Orderings: two survive, two change, and only one change is physics

| metric | before | after | changed |
|---|---|---|---|
| system electrical loss | Z4_POWER_DIE < Z1_EMBEDDED < Z2_BACKSIDE | Z4_POWER_DIE < Z1_EMBEDDED < Z2_BACKSIDE | **no** |
| peak temperature | Z4_POWER_DIE < Z2_BACKSIDE < Z1_EMBEDDED | Z4_POWER_DIE < Z1_EMBEDDED < Z2_BACKSIDE | **YES** |
| die warpage | Z2_BACKSIDE < Z1_EMBEDDED < Z4_POWER_DIE | Z2_BACKSIDE < Z1_EMBEDDED < Z4_POWER_DIE | **no** |
| corner-joint shear | Z2_BACKSIDE < Z1_EMBEDDED < Z4_POWER_DIE | Z2_BACKSIDE < Z4_POWER_DIE < Z1_EMBEDDED | **YES** |

Telling the two changes apart required the depth of each converter layer below the cooled
face: Z1 `tile_band` at 0.973 mm, Z2 `conv` at 1.273 mm, Z4 `interface` at 0.355 mm.

**The temperature reordering is REAL.** Z2's backside converter sits 0.3 mm deeper than Z1's.
Against a calibrated Robin boundary --- a near-isothermal sink over the whole top face ---
that depth was almost free and Z2 came out 1.56 K cooler than Z1. Against a physical cooler
with finite `h` and a caloric rise it costs 6.78 K at the peak. The signature confirms the
mechanism: 6.78 K at the peak against only 1.44 K in the mean is a depth penalty, not an
offset.

**The corner-shear reordering is CONDITIONAL and says nothing about Z4.** `zglobal.stack_for`
gives the Z4 power-die architecture no converter layer --- the Phase-0I global model never
represented that die geometrically --- so its heat lands in the `interface` layer only
0.355 mm below the cooler, far closer than a real Z4 power die would sit. Z4 heats by 13 K
where Z1 heats by 39 K, and overtakes it. Recorded as conditional.

**What survives is the ordering the project's claim rests on:** Z2 carries less corner-joint
shear than Z1 before integration (2.0754 against 2.7447 um)
and after it (3.4101 against 4.2803 um).

And one result that neither ordering shows on its own: **Z2 becomes the hottest architecture
and remains the best on the reliability driver.** Peak temperature and the fatigue driver do
not track, because the driver is set by CTE mismatch across a thin substrate rather than by
absolute temperature. A screening study that ranked on `T_max` alone would have ordered these
architectures wrongly for the metric that decides the design.

## Cooling is a design variable, not a boundary condition

| cooler | total flow | Z2 peak | Z2 driver | hydraulic pumping |
|---|---|---|---|---|
| single-sided microchannel | 27 g/s | 130.31 C | 3.4101 um | 14.7 W |
| single-sided microchannel | 50 g/s | 114.89 C | 2.8842 um | 74 W (7.4 % of load) |
| two-sided, equal total flow | 27 g/s | 136.53 C | 3.6258 um | 14.7 W |

Buying flow works: 27 to 50 g/s is worth 15.4 K and
15.4 % of the driver. **Two-sided cooling at equal total flow is
worse, not better** (+6.2 K): the second side faces the board rather than the die, so
diverting half the heat into a thermally remote path costs more than the added area returns.

The retired calibrated boundary was not a neutral simplification. Reaching its
h = 166 000 W/m2K needs 50 g/s and 1.46 MPa, and it hid roughly 40 K of optimism and 7.4 % of
the load in uncharged pumping.

![FIG-0MR-F](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0mr/FIG_0MR_F_cooling.png)

*FIG-0MR-F. The physical cooling model: resistance chain, streamwise coolant temperature, and
what each candidate costs to pump.*

## Independent validation

| what | against | result |
|---|---|---|
| transition resistance, 5 geometries | MOOSE, independent mesher / formulation / solver | 0.25 to 0.73 %, **5/5 ACCEPTED** |
| uniform bar | analytic | exact at every mesh, in both codes |
| spreading resistance | analytic `rho/(4a)` | within 0.9 % |
| cooling solid side | MOOSE with explicit fins | 2/4 ACCEPTED; one REJECTED at 10.11 %; production geometry 3.78 % |
| cooling fluid side | analytic energy balance | exact |
| loss decomposition | the upstream aggregate | machine precision, or the ledger refuses to total |

The first cross-solver run **failed**, at 12.1 % and 18.7 % on the narrow-trace cases. The
cause was MOOSE's centroid-based subdomain assignment staircasing the trace, and the
disagreement tracked trace width and changed sign in the predicted direction each time. Mesh
alignment is now part of every case definition and each run reports the block volumes the
independent solver actually meshed.

![FIG-0MR-C](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0mr/FIG_0MR_C_transition_decomposition.png)

*FIG-0MR-C. Transition resistance per class, and the cross-solver agreement.*

## Four Phase-0M statements are narrowed; none is withdrawn

* **"intra-VR routing is common mode across architectures"** --- true only at fixed component
  topology. Across partition templates it varies **7.5 %**, because a template that splits by
  voltage domain puts the 16 V intermediate rail across the tier boundary instead of the 1 V
  rail and its vertical metallization loss collapses by three orders of magnitude.
* **"the RDL is 153x to 276x anisotropic"** --- that is IN-PLANE, for a single-direction line
  layer. Every realistic organisation --- orthogonal, mesh, plane --- is in-plane isotropic to
  solver precision. The real anisotropy is **through-thickness, 57x to 270x**, in the opposite
  sense. Adding the RDL to the mechanical mesh moves the Z1/Z2 ratio from
  1.3217 to 1.3202, at most 0.11 %.
* **"`dR` is the excess resistance"** --- it is a **difference against a stated 1-D reference**
  with identical terminals, and at the nominal TSV geometry it is NEGATIVE. The retired
  constant was inflating that tier by 32.6 %.
* **"TSV radius is not a lever"** --- not a FIELD-LOSS lever under minimum-capability
  provisioning with a geometry-independent `J_design`. It is decisively a **feasibility**
  variable: at 300 um only r >= 15 um is buildable at a 10:1 aspect limit, and 15 um is the
  reference radius, so the source geometry sits exactly ON the limit.

![FIG-0MR-E](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0mr/FIG_0MR_E_rdl_tensor.png)

*FIG-0MR-E. The RDL effective tensor by stack organisation. The in-plane ratio is 1.00
everywhere except single-direction lines.*

## Verdict

Of the seven candidates, **C** is the one the evidence supports as dominant: **production
coupling preserves the deciding architecture ordering; absolute responses change materially.**
**A** is not earned --- six items remain OPEN and blocking and no partition template is
realizable. **B** would report a modelling substitution as a physical reordering. **D** is
largely true and is the single largest contributor, but the question this gate had to settle
was what integration does to the ordering. **E** fails on measurement. **F** is contradicted
by 5/5 acceptance against an independent solver. **G** was Phase 0M's verdict and this phase
closed five of the models it named.

The optimizer remains **FORBIDDEN**. One precondition moved from NO to YES and two to PARTIAL;
four remain NO, and any one of them is sufficient.

![FIG-0MR-K](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0mr/FIG_0MR_K_closure_ladder.png)

*FIG-0MR-K. What is closed, what is conditional and what is open, after Phase 0M-R.*

<!-- END GENERATED: phase0mr_narrative -->

<!-- BEGIN GENERATED: phase0mr2_narrative -->

\newpage

# Phase 0M-R2 --- Architecture Realizability, Cooling-Regime and Current-State Closure (superseded by Phase 0M-R3)

Phase 0M-R2 is a falsification gate. It asked five questions that could each have
undermined the physical interpretation of Phase 0M-R, and four of them returned a defect.

## 1. Was "0 stale current-facing claims" true? --- No

**17 stale findings across eight claims**, in a report that had passed 46 of 46
cross-report checks. The checker matched each report as one flat string, so a required
phrase found anywhere satisfied the check for the whole document; it could not detect an
omission at all; and its forbidden patterns were paraphrases rather than the report's real
sentences. Registered as **DEFECT #54**. Phase-0M-R's own DEFECT #53 was also never added
to the numbered register, which stopped at 52; it is registered retroactively here.

The fix is a section-scoped claim contract: every claim names the sections that must carry
its CURRENT wording and the sections where HISTORICAL wording is allowed, and the gate
count is derived from the contract rather than typed.

## 2. Is ARCH_Z4 a real power die now? --- Yes, and it is still conditional

`zglobal.stack_for` had branches for "in" and "below" and **none for "above"**, which is
what ARCH_Z4 declares. Its converter heat was being deposited in the `interface` layer
0.355 mm below the cooled face. The power die is now explicit geometry --- 1921 um of
sourced components between the substrate top and the compute die --- and its converter
band sits 1.928 mm below the cooled face.

Z4 nevertheless **remains conditional**, for a different reason. No source describes a
monolithic power-die process, so two constructions are defensible, and Z4's rank depends
on which one is real: stacked gives a corner driver of 3.5306 um and
best place, planar gives 3.9937 um and second place, and the die warpage differs
by roughly a factor of two between them.

## 3. DEFECT #55, found while building the Z4 geometry

The TSV-field material override was keyed on a layer's in-plane FOOTPRINT. Every assembly
layer added below z = 0 in Phase 0G --- the PCB, the BGA field and ARCH_Z2's backside
converter --- spans the substrate extent, so all of them had their material overwritten
with `tsv_homog` inside every tile. **The PCB was being modelled as a copper/silicon
composite**: k too high by 530x, E by 6.3x, CTE too low by 3.4x, in the layers that set
package warpage. The misassigned volume was 522 to 859 mm3 against 20 to 77 mm3 of real
via field, and it was architecture-dependent, so it did not cancel. Fixing it moved Z1's
die warpage by +75 % and its corner driver by +16.4 %.

## 4. What span does each TSV actually traverse?

| architecture | h_sub | converter cell | **TSV span** | AR at d = 30 um | on the limit? |
|---|---|---|---|---|---|
| Z1_EMBEDDED | 1300 um | 1226 um | **74 um** | 2.47 | no |
| Z2_BACKSIDE | 300 um | 0 um | **300 um** | 10.00 | YES, exactly |
| Z4_POWER_DIE | 300 um | 0 um | **300 um** | 10.00 | YES, exactly |
| Z5_2P5D_LATERAL | 300 um | 0 um | **300 um** | 10.00 | YES, exactly |

**No architecture traverses 1300 um.** ARCH_Z1 has a 1.30 mm substrate, but 1226 um of it
is the embedded converter cell sitting on top of the via field; its vias traverse 74 um at
an aspect ratio of 2.47. The Phase-0M-R "1300 um is infeasible" rung corresponds to no
real geometry. The real exposure is the opposite of what that suggested: three of the four
architectures sit **exactly on** the 10:1 limit, with no margin at all.

Three domains had been using three different lengths for the same via --- 300 um
electrically, 280 um in the mesh, and a hard-coded ladder in the feasibility checker.
`configs/phase0mr2/architecture_geometry.yaml` is now the single source and a guard fails
if any two disagree by more than 0.5 %.

## 5. Is the cooling model inside its correlation domain?

| point | flow | Re | regime | Nu | h_eff | pumping | status |
|---|---|---|---|---|---|---|---|
| source_stated | 1.6 g/s | 75.0 | laminar | 4.603 | 22827 | 0.05 W | in domain |
| production | 27.0 g/s | 1264.8 | laminar | 4.603 | 115553 | 14.70 W | in domain |
| high_flow | 50.0 g/s | 2342.3 | transitional | nan | nan | nan W | **OUT_OF_MODEL_DOMAIN** |
| two_sided_per_side | 13.5 g/s | 632.4 | laminar | 4.603 | 92009 | 3.67 W | in domain |

**The 50 g/s point is outside the domain of every correlation this framework has.**
`scripts/phase0m/cooling.py` switched to Gnielinski at Re = 2300; Gnielinski is validated
from Re = 3000. The 50 g/s point sits at Re = 2342, in the gap. The two neighbouring
correlations differ by a factor of 2.76 there, so the reported h was set by the choice and
not by the flow. The Phase-0M-R numbers h = 166 000 W/m2K, dp = 1.46 MPa and 74 W of
pumping are **withdrawn**. What survives, and is stronger, is that the retired calibrated
boundary is not reachable by any correlation this framework can validate.

**The production point at 27 g/s is inside the laminar domain**, at Re = 1264.8, so every
Phase-0M-R conclusion resting on it stands. One caveat is now recorded: the thermal
entrance length occupies 86 % of the channel there, so the fully-developed Nusselt number
understates h and the production temperature is conservative rather than optimistic.

## 6. Does promoting the RDL thermal anisotropy change the answer?

The `interface` layer --- the one layer every watt crosses --- was isotropic underfill at
k = 0.70 W/mK. Homogenising its own sourced microbump geometry gives kxy = 0.891 and
kz = 11.739 W/mK: **16.8x more conductive through thickness** than the value in use. It is
now the production default.

| quantity | isotropic | anisotropic | change |
|---|---|---|---|
| Z1 peak temperature | 125.51 C | 118.80 C | -6.71 K |
| Z2 peak temperature | 134.23 C | 127.06 C | -7.17 K |
| **Z1/Z2 driver ratio** | **1.1955** | **1.1942** | **-0.105 %** |

It moves absolute temperature by about 7 K and the driver by about 6.7 %, and the ORDERING
by 0.105 %. It matters for absolute numbers and for nothing else.

## The frozen replay

| architecture | P_electronics | P_pump | P_facility | T_max | T_conv | die warpage | corner driver |
|---|---|---|---|---|---|---|---|
| Z1_EMBEDDED | 139.287 | 14.696 | 153.983 | 118.80 | 99.03 | 41.726 | 4.6450 |
| Z2_BACKSIDE | 141.688 | 14.696 | 156.385 | 127.06 | 101.48 | 39.031 | 3.8896 |
| Z4_POWER_DIE stacked | 136.126 | 14.696 | 150.822 | 98.83 | 93.50 | 22.769 | 3.5306 |
| Z4_POWER_DIE planar | 135.165 | 14.696 | 149.861 | 96.50 | 91.85 | 44.518 | 3.9937 |

Pumping power is **FACILITY** scope: it is spent outside the package, it is not in the
loss objective, and it is not deposited into the thermal mesh. Phase 0M-R's "system loss"
excluded it and never said so; the two ledgers now refuse each other's terms.

![FIG-0MR2-A](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0mr2/FIG_0MR2_A_zstacks.png)

*FIG-0MR2-A. The three architecture z-stacks with the real TSV span and the cooled face.*

![FIG-0MR2-E](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0mr2/FIG_0MR2_E_three_phases.png)

*FIG-0MR2-E. The frozen architectures through three successive production paths.*

## The deciding question

**D_driver = driver_Z1 / driver_Z2 = 1.1942** (4.6450 um against
3.8896 um).

The Phase-0M-R value was 1.2552. The ordering survives physical Z4 geometry, the
corrected board material, architecture-aware TSV spans, a regime-checked cooler and a
promoted RDL tensor. It narrows by -4.9 %, and it does not approach unity.

**This is a ROBUST ORDERING, not a VALIDATED MAGNITUDE.** The constitutive
transferability problem is untouched: the creep card is Sn3.9Ag0.6Cu fitted over
7.51-15.92 MPa, and 99.8 % of the damage is generated outside that window. Relative life
is not validated and absolute life remains OPEN.

## Temperature and the fatigue driver do not track

127.06 C against 118.80 C: **ARCH_Z2 is the hottest of the principal
candidates and still carries 16.3 % less corner-joint driver than ARCH_Z1.**

This must not be read as a claim that temperature is irrelevant to fatigue. It is not:
temperature-dependent constitutive behaviour is one of the dominant physics in this
framework. The narrower and correct statement is that **ranking architectures by package
T_max is not equivalent to ranking them by the current solder-fatigue driver**, because
geometry- and CTE-induced deformation and the local constitutive response are distinct
mechanisms.

![FIG-0MR2-F](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0mr2/FIG_0MR2_F_decoupling.png)

*FIG-0MR2-F. Peak temperature against the fatigue driver. Z2 is hotter and mechanically
preferable; Z4's two construction bounds straddle Z2.*

## Realizability

**0 of 12 template-architecture combinations are realizable, at any of the 27 corners of
the clearance bound.** The three package clearances remain OPEN --- no source, no foundry
rule, and nothing usable in the literature reachable from this host --- but they are not
the binding constraint. Even at their most favourable values, area still blocks 9 of 12,
height 8 of 12, and routing and current density 6 of 12 each. Closing the clearances would
make nothing buildable. T4 is 3.83 % over its area bound once the smallest sidewall
allowance is charged, not the 2 % Phase 0M-R reported with none.

**Neither architecture in the deciding comparison is presently buildable.** The mechanical
ordering is a statement about two designs that cannot yet be manufactured as specified.

<!-- END GENERATED: phase0mr2_narrative -->

<!-- BEGIN GENERATED: phase0mr3_narrative -->

\newpage

# Phase 0M-R3 --- Realizable-Template Repair, Cooling Validation and Final Current-State Closure (superseded by Phase 0M-R3A)

Phase 0M-R2 established a robust Z2 < Z1 ordering between two designs that were not
buildable. This gate asked whether the EXISTING converter and package library already
contains a buildable Z1 and a buildable Z2, and whether the ordering survives on them.

## The realizability definition was frozen first

`configs/phase0mr3/realizability_contract.yaml` fixes fifteen conditions and four verdict
levels BEFORE any architecture was touched, so "buildable" could not be adjusted after
seeing which candidates pass. Two conditions -- package clearance and cooling clearance --
depend on OPEN inputs, which means **PROVEN_REALIZABLE is unreachable in this phase by
construction**, whatever the margins turn out to be. That consequence was accepted in
advance.

## Why the originals failed, quantified

| architecture | area | height | routing | J | TSV count | TSV AR |
|---|---|---|---|---|---|---|
| Z1_EMBEDDED | 0.564 | 0.989 | **1.236** | 0.999 | 0.009 | 0.247 |
| Z2_BACKSIDE | 0.550 | 1.755 | **1.236** | 1.000 | 0.397 | 1.000 |

ARCH_Z1 failed on ONE condition, routing at 1.236. ARCH_Z2 failed on that and on height.
The binding net is the same in both: **`ls_to_L`**, the switch-node to inductor VERTICAL
via stack carrying 20.408 A and needing 1.236x the vias its pad provides.

![FIG-0MR3-A](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0mr3/FIG_0MR3_A_failure_margins.png)

*FIG-0MR3-A. Only routing crosses the feasibility line.*

## The repair: one variable, inside the sourced range

Neither more metal layers nor more cells fixes a via-count shortfall -- layers add no vias,
and splitting cells divides the current and the pad area together, leaving the ratio
invariant. The via GEOMETRY does fix it, because the required count goes as 1/r^2 while the
available count goes as 1/p^2 and the framework's own pitch rule
`p = max(2r + s_min, 2r(1+koz))` with the SOURCE_BACKED `s_min = 30 um` makes p grow more
slowly than r:

| r | p | (p/r)^2 | routing ratio |
|---|---|---|---|
| 15 um | 60 um | 16.00 | 1.236 |
| **20 um** | **70 um** | **12.25** | **0.934** |

20 um lies inside the sourced range `design_variables.tsv.radius_m = {lo 2.5, nominal 15,
hi 50} um`. No device was invented, no component scaled below its sourced dimensions, the
load stayed at 1 kW and the package budget was untouched.

## The frozen realizable pair

| | Z1_EMBEDDED | Z2_BACKSIDE |
|---|---|---|
| verdict | **CONDITIONAL_REALIZABLE** | **CONDITIONAL_REALIZABLE** |
| clearance corners passing | 27/27 | 27/27 |
| area margin | 43.6 % | 45.0 % |
| height margin | 41.6 % | 33.6 % |
| routing margin | 6.6 % | 6.6 % |
| TSV aspect ratio | 2.467 | 10.000 |
| TSV design margin M_AR | 4.054 | **1.000** |
| package clearances | OPEN | OPEN |

Neither reaches PROVEN_REALIZABLE, for the reason fixed before the search: three package
clearances are unsourced.

## The deciding result

| | Z1 | Z2 |
|---|---|---|
| P_electronics | 138.796 W | 141.189 W |
| P_pump (FACILITY) | 14.696 W | 14.696 W |
| T_max | 118.68 C | **126.91 C** |
| die warpage | 41.699 um | 39.003 um |
| local fatigue-relevant inelastic response | 4.6401 um | **3.8851 um** |

**D_driver_realizable = 1.1943**, against 1.1942 in Phase 0M-R2: a change of
**+0.0095 %**. Repairing both architectures for manufacturability moved the ordering by
less than one part in ten thousand. The gap is 33 times the converged mesh error of 0.5 %.

**ARCH_Z2 is 8.23 K hotter and carries 16.3 % less response.** Ranking by
package T_max is not ranking by the fatigue-relevant response.

![FIG-0MR3-G](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0mr3/FIG_0MR3_G_decoupling.png)

*FIG-0MR3-G. The realizable pair. Filled points are Phase 0M-R3, hollow Phase 0M-R2.*

## What this is NOT

The quantity above is a **local fatigue-relevant inelastic response metric**: accumulated
equivalent inelastic strain per stabilised cycle, numerically converged and tied to a
documented solder-fatigue mechanism. It is a RESPONSE. It becomes DAMAGE only through a
sourced damage law, LIFE only through a life model, and a FAILURE CRITERION only with an
admissible allowable. None of those three is closed, so no statement of the form "Z2 lasts
1.19x longer" is available from this result.

## The TSV has no process margin

ARCH_Z2 sits at AR = 10.000, which passes the hard rule and gives M_AR = 1.000 -- the
boundary, not margin. Under a modest bound of -2 % diameter and +2 % depth it reaches
10.408 and violates the rule. A 34 um via, inside the sourced range, restores M_AR = 1.089
at the cost of 22.8 % more vias and a change of 0.02 % or less in copper fraction, field
resistance, thermal tensor, modulus and CTE. That is the Phase-0M allocation law confirmed
on a case it was not derived for.

![FIG-0MR3-C](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0mr3/FIG_0MR3_C_tsv_margin.png)

*FIG-0MR3-C. The hard rule and the design margin are different questions.*

## Cooling: the gap is closed by prohibition, not by interpolation

No correlation valid for a rectangular liquid microchannel in 2300 < Re < 3000 could be
sourced. Crossref and OpenAlex were reachable and returned nothing whose coefficients and
validity range could be read from an accessible primary text, and writing one from memory
would put unverifiable numbers into the production model. The band is therefore permanently
OUT_OF_MODEL_DOMAIN and **the production cooling design space is capped at Re <= 2300**.
The production point at 27 g/s sits at Re = 1264.8, far inside the validated domain, so
nothing in this phase depends on the gap.

![FIG-0MR3-D](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0mr3/FIG_0MR3_D_cooling_validity.png)

*FIG-0MR3-D. The shaded band has no sourced correlation and is now outside the design space.*

## Report state: 18 findings behind a zero-stale certificate

Phase 0M-R2 certified 0 stale current-facing claims. This phase found **18**, and
registered **DEFECT #56**. A section-scoped checker is still contract-driven: it cannot see
a contradiction BETWEEN two fields, and it cannot see a structural defect at all. Among the
findings: one paragraph shipped four times, two different report dates, a provenance table
claiming a solver that is not installed, the mechanical criterion described as though it were the
only obstacle to G2 when three independent ones exist, and the FE response metric called DAMAGE.

## Verdict

**E --- Z1/Z2 FEASIBILITY REMAINS CONDITIONAL ON OPEN PACKAGE RULES.**

A realizable Z1 and a realizable Z2 exist and pass every condition of the frozen contract
at all 27 corners of the bounded clearance envelope, and the deciding ordering survives
the repair essentially unchanged. Neither can be called PROVEN_REALIZABLE while three
package clearances are unsourced and ARCH_Z2's TSV field has zero process margin.

The optimizer remains **FORBIDDEN**.

<!-- END GENERATED: phase0mr3_narrative -->

<!-- BEGIN GENERATED: phase0mr3a_narrative -->

\newpage

# Phase 0M-R3A --- Final State, Via-Technology and TSV-Margin Closure (current authoritative)

A narrow closure gate on four specific issues left by Phase 0M-R3. Three were confirmed as
defects and one claim was found to have the wrong sign.

## The intra-VR via repair is not source-backed --- DEFECT #58

Phase 0M-R3 made both architectures routable by raising the via radius on the binding net
`ls_to_L` from 15 to 20 um, justified as inside `design_variables.tsv.radius_m =
{lo 2.5, nominal 15, hi 50} um`. **That range governs THROUGH-SILICON VIAS.**

`ls_to_L` connects the low-side GaN switch node on tier 1 to the inductor terminal on tier
3 --- a **673 um** vertical span between embedded-component layers inside the converter
cell, carrying 20.408 A. The framework's own source picture separates the two structures
in one sentence each: the components are "embedded within the subsequent substrate power
layers", and "the TSV field runs beneath it from the substrate underside", spanning 74 um
for ARCH_Z1.

| | TSV field | `ls_to_L` |
|---|---|---|
| where | beneath the cell, from the substrate underside | between embedded-component layers, inside the cell |
| span, ARCH_Z1 | 74 um | **673 um** |
| medium | through silicon | through substrate power-layer build-up |

The design space holds `tsv.*`, `rdl.*` (trace width and space only) and `bump.*`. **No
entry governs a stacked via through substrate power layers.** The repair is therefore a
design point in an **unsourced process window**: arithmetically self-consistent, and not
demonstrated to be manufacturable.

## The arithmetic, independently reproduced

An implementation sharing no code with the production path:

| r | pitch | n_required | n_available | ratio | production |
|---|---|---|---|---|---|
| 15.0 um | 60.0 um | 309 | 250 | 1.2360 | 1.2360 |
| 17.5 um | 65.0 um | 225 | 213 | 1.0563 | 1.0563 |
| 20.0 um | 70.0 um | 171 | 183 | 0.9344 | 0.9344 |
| 22.5 um | 75.0 um | 135 | 160 | 0.8438 | 0.8438 |
| 25.0 um | 80.0 um | 109 | 140 | 0.7786 | 0.7786 |

Exact at all five radii. The numbers were right; only their provenance was not.

## The 34 um claim had the sign backwards --- DEFECT #59

Phase 0M-R3 wrote that a 34 um TSV restores margin "at the cost of 22.8 % MORE vias".
`n_required = ceil(I / (J * A_cu))` scales as `1/A_cu`, so:

| quantity | 30 um | 34 um | change |
|---|---|---|---|
| n_required | 15140 | 11692 | **-22.8 %** |
| n_available | 69440 | 61031 | -12.1 % |
| phi_Cu | 0.020002 | 0.020002 | -0.001 % |

**22.8 % FEWER**, and a reduction rather than a cost. A second error in the same sweep:
34 um was reported as the smallest diameter with positive margin, but the grid was
30/34/40/50/60 and never evaluated **32 um**, which passes the same modest bound at
M_AR = 1.067 for 12.5 % fewer vias.

![FIG-0MR3A](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0mr3a/FIG_0MR3A_tsv_diameter_margin_and_count.png)

*(a) ARCH_Z2 at 30 um sits exactly on the 10:1 aspect-ratio limit, so any tolerance at all
puts it over; 32 um is the smallest diameter on the evaluated grid with positive margin.
(b) the required count falls as the via grows, because `n_required` scales as `1/A_cu`.
Faint verticals mark diameters the Phase-0M-R3 grid never evaluated.*

"34 um sourced" is also withdrawn: no primary source specifies 34 um, only the RANGE is
source-backed. The licensed wording is **a design point selected within the source-backed
allowable range**.

## The current-state table was a phase behind --- DEFECT #57

Two independent representations of current state exist, and Phase 0M-R3 advanced only one.
The report carried a section headed "Current scientific status (Phase 0M-R3)" whose table
said phase = 0M-R2 complete, gave the Phase-0M-R2 verdict and said ZERO OF TWELVE
REALIZABLE after a realizable pair had been found. A separate `next_gate` field still
listed adopting the physical cooling model and putting the RDL in the mechanical mesh as
future work; both were completed in Phases 0M-R and 0M-R2.

## Terminology

Current-facing text presented the HISTORICAL Phase-0I 35.8 % separation as the present
architecture result, called the FE output "damage", and said "Z2 outlives Z1". All three
are corrected. The present repaired pair separates by **16.3 %**, the FE quantity is a
**local fatigue-relevant inelastic response metric**, and no survival claim is made while
absolute N_f is unvalidated.

## No replay was needed

The 30 -> 34 um change moves phi_Cu, R_field, the thermal tensor, the modulus and the CTE
by under 0.1 %, exactly as the Phase-0M allocation law predicts: the copper fraction is
`I / (J_design * A_field)`, in which the radius cancels. The frozen pair therefore stands:

| | Z1 | Z2 |
|---|---|---|
| P_electronics | 138.796 W | 141.189 W |
| T_max | 118.68 C | **126.91 C** |
| local fatigue-relevant inelastic response | 4.6401 um | **3.8851 um** |

**D_driver = 1.1943**, unchanged.

## Verdict

**B --- Z1/Z2 ORDERING SURVIVES, BUT THE INTRA-VR VIA TECHNOLOGY REMAINS UNSOURCED.**

Phase 0M-R3's verdict E rested on package clearances being the sole blocker. DEFECT #58
adds a second, independent unsourced manufacturing assumption, so that premise no longer
holds. The optimizer remains **FORBIDDEN**.

### Verdict history

Phase 0M-R3A withdrew the stale current-state table that had been asserting the
Phase-0M-R2 verdict as the present one. The verdicts themselves are part of the record and
are kept here, each as the finding of the gate that issued it and none of them current
except the last.

| gate | option | verdict |
|---|---|---|
| Phase 0M | **G** | MULTIPLE MISSING PHYSICAL COUPLINGS ARE FIRST ORDER -- OPTIMIZATION STILL PREMATURE |
| Phase 0M-R | **C** | PRODUCTION COUPLING PRESERVES THE DECIDING ARCHITECTURE ORDERING -- ABSOLUTE RESPONSES CHANGE MATERIALLY |
| Phase 0M-R2 | **H** | PRODUCTION MODEL STILL NOT PHYSICALLY CLOSED -- NO ARCHITECTURE VERDICT BEYOND Z1/Z2 IS DEFENSIBLE |
| Phase 0M-R3 | **E** | Z1/Z2 FEASIBILITY REMAINS CONDITIONAL ON OPEN PACKAGE RULES |
| Phase 0M-R3A (current) | **B** | Z1/Z2 ORDERING SURVIVES BUT INTRA-VR VIA TECHNOLOGY REMAINS UNSOURCED |

<!-- END GENERATED: phase0mr3a_narrative -->

<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml -- DO NOT EDIT BY HAND. -->
<!-- Regenerate with scripts/phase0g/generate_status_sections.py (DEFECT #29). -->

## Current scientific status (Phase 0M-R3A)

<!-- BEGIN GENERATED: current_state_contract -->
<!-- Generated from results/CURRENT_SCIENTIFIC_STATUS.yaml::current_state_contract
     by scripts/phase0mr/state_contract.py. DO NOT EDIT BY HAND. -->

| question | current answer | evidence |
|---|---|---|
| phase | **0M-R3A complete** | `results/phase0mr3a/PHASE0MR3A_FINAL_CLOSURE.md` |
| verdict | **Phase 0M-R3A: Z1/Z2 ORDERING SURVIVES, BUT THE INTRA-VR VIA TECHNOLOGY REMAINS UNSOURCED (option B). A realizable Z1 and Z2 pair exists and the deciding ordering holds at D_driver = 1.1943, but the repair that made them routable sets an intra-converter vertical interconnect to r = 20 um using a range that governs THROUGH-SILICON VIAS, not the package-substrate via this net actually is (DEFECT #58). Package clearances are no longer the sole blocker: via-technology provenance is a second, independent unsourced manufacturing assumption.** | `results/phase0mr3a/LS_TO_L_INTERCONNECT_AUDIT.md` |
| ET coupling level | **ETM-L1: E <-> T iterated to a fixed point, T -> M one-way. Intact M -> E is 0.16 % of R against 22.8 % from rho(T); M -> T is 1.5 K for a 4 % TIM bond-line change. Neither is solved back.** | `results/phase0m/etm_feedback_magnitudes.csv` |
| mechanical capability | **Global thermoelastic warpage and stress (M0), plus a convergent local solder viscoplastic damage metric (M2) added in Phase 0I and verified in 0I-R. TWO of eight enumerated mechanisms are addressable, not one. RDL fracture, delamination, via fatigue, dielectric cracking, pad cratering and EM-assisted damage remain uncomputed.** | `results/phase0m/PHYSICS_PRIORITY_MATRIX.csv` |
| solder metric status | **AVAILABLE AND CONVERGENT, AND IT IS A RESPONSE. The FE quantity is a LOCAL FATIGUE-RELEVANT INELASTIC RESPONSE METRIC: accumulated equivalent inelastic strain per stabilised cycle, volume averaged over the solder core and matched to the Syed 25 um averaging volume. It is NOT damage, NOT life and NOT a failure criterion: those require a sourced damage law, a life model and an admissible allowable respectively, and none of the three is closed.** | `results/phase0i/local_metric_convergence.csv` |
| constitutive status | **CONDITIONAL. The creep card is fitted on Sn3.9Ag0.6Cu, NOT SAC305, over 7.51-15.92 MPa, while 99.8 % of package damage is generated outside that window. Two families can be PARAMETERIZED in the regime; only NORTON can be INTEGRATED through the production solve. This is the dominant open blocker.** | `results/phase0lr/ALLOY_TRANSFERABILITY_MATRIX.md` |
| life law status | **AVAILABLE FOR RELATIVE LIFE. The primary sources were obtained in Phase 0J-R and Syed 2004's author-corrected calibration was reproduced. HTTP 403 is NO LONGER the blocker; it was, in Phase 0J, and that statement is historical.** | `results/phase0jr/PHASE0JR_PRIMARY_LIFE_LAW_GATE.md` |
| required life status | **OPEN. No field or product requirement exists in this repository or any supplied source. It is NOT the sole G2 blocker -- Phase 0K withdrew that framing.** | `results/phase0k/G2_DECISION_REGIONS.md` |
| G2 status | **NOT TESTED, and not testable. THREE independent blockers, any one sufficient: N_required is OPEN, absolute N_f is unvalidated (the strain and energy formulations disagree 4.1x on this joint), and no admissible operational mechanical allowable exists (nine candidates tested against six admissibility conditions, none passed). Closing any one leaves the other two.** | `results/phase0h/criterion_admissibility.csv` |
| optimizer status | **FORBIDDEN. SIX preconditions stand at NO, any one sufficient: process margin on the critical interconnect; intra-VR via technology sourced; dominant mechanical physics closed; an admissible mechanical criterion exists; a required life exists; absolute fatigue prediction validated. Phase 0M-R3A added the second of those and DOWNGRADED 'routing scope physically correct' from YES to PARTIAL, because the repair that makes both candidates pass sets a via radius in an unsourced process window (DEFECT #58). Counted against results/phase0mr3a/optimizer_preconditions.csv.** | `results/phase0mr3a/final_open_items.md` |
| cooling status | **IN PRODUCTION, PHYSICAL, AND NOW REGIME-CHECKED. The production point at 27 g/s is laminar at Re = 1264.8 and inside the Shah & London correlation's validated domain, so every Phase-0M-R conclusion resting on it stands. Phase 0M-R2 found that the 50 g/s point Phase 0M-R quoted sits at Re = 2342, above the laminar ceiling of 2300 and below Gnielinski's floor of 3000, where the two neighbouring correlations differ by 2.76x: h = 166 000 W/m2K, dp = 1.46 MPa and P_pump = 74 W are WITHDRAWN as model outputs. An explicit dispatcher now returns OUT_OF_MODEL_DOMAIN there rather than extrapolating. Separately, at 27 g/s the thermal entrance length occupies 86 % of the channel, so the fully-developed Nusselt number understates h and the production temperature is CONSERVATIVE. Conjugate CFD validation is reported in results/phase0mr2/CONJUGATE_CFD_VALIDATION.md.** | `results/phase0mr2/cooling_regime_table.csv` |
| routing status | **ALL THREE LEVELS IN PRODUCTION. Level 1 intra-converter metallization is now in the loss ledger, template-aware, at 4.97-5.34 W system-wide across templates at the reference stack and 4.55-43.84 W across every stack examined. The Phase-0M claim that it is common mode is NARROWED: at fixed component topology it is, but across partition templates it varies 7.5 %, because a template that splits by voltage domain puts the 16 V intermediate rail across the tier boundary instead of the 1 V rail and its vertical loss collapses by three orders of magnitude.** | `results/phase0mr/intravr_routing_by_template.csv` |
| crowding status | **IN PRODUCTION, PER CLASS, CROSS-VALIDATED. The global 1.326 constant is retired from every production path. Each interconnect class carries its own Delta_R = R_3D - R_1D, solved exactly at its production geometry and cached. Cross-validated against MOOSE (independent mesher, formulation and solver) on five geometries: 5/5 ACCEPTED at 0.25-0.73 %. Delta_R is a DIFFERENCE against a stated 1-D reference using identical terminals, NOT an excess: at the nominal TSV geometry it is NEGATIVE, so the retired constant was inflating the TSV tier by 32.6 %.** | `results/phase0mr/current_crowding_validation.csv` |
| RDL anisotropy status | **PROMOTED TO THE PRODUCTION THERMAL DEFAULT. The interface layer -- the one layer every watt crosses -- was isotropic underfill at k = 0.70 W/mK. Homogenising its own sourced microbump geometry (r = 5 um, pitch 20 um, h = 10 um) gives kxy = 0.891 and kz = 11.739 W/mK, i.e. 16.8x more conductive through thickness, within 0.55 % of the Voigt bound and 0.61 % of Maxwell-Garnett. Promotion moves peak temperature by about 7 K and the driver by about 6.7 %, and the Z1/Z2 ratio by 0.105 %: it matters for absolute numbers and changes no ordering.** | `results/phase0mr2/rdl_isotropic_vs_anisotropic.csv` |
| component partition status | **A REALIZABLE PAIR EXISTS, BOTH CONDITIONAL. Phase 0M-R3 superseded the zero-of-twelve result: one ARCH_Z1 and one ARCH_Z2 candidate satisfy every condition of a realizability contract frozen before the search, at all 27 corners of the bounded clearance envelope. Margins: area 43.6 % and 45.0 %, height 41.6 % and 33.6 %, routing 6.6 % on both. Neither is PROVEN_REALIZABLE, now for TWO reasons: three package clearances are unsourced, and the intra-VR via technology that made the routing feasible has no sourced process rule (DEFECT #58).** | `results/phase0mr3a/LS_TO_L_INTERCONNECT_AUDIT.md` |
| next work | **Phase 0N is NOT authorised. Ranked: (1) source a process rule for the INTRA-CONVERTER VERTICAL INTERCONNECT, which DEFECT #58 showed has none and which the routing repair depends on; (2) source the three package clearances; (3) close the ARCH_Z2 TSV process margin, for which 32 um is the smallest diameter on the evaluated grid with positive margin and which costs 12.5 % FEWER vias, not more; (4) high-stress SAC305 characterisation, still the dominant blocker on every absolute reliability number; (5) the canonical conjugate CFD benchmark. Items already COMPLETE and not to be relisted: adopting the physical cooling model into the ETM loop (Phase 0M-R) and putting the RDL into the production thermal model (Phase 0M-R2).** | `results/phase0mr3a/final_open_items.md` |

*Contract version 0M-R.1, 2026-09-21. Every current-facing statement in this report and in the standalone audit report is generated from this table. A statement that contradicts it is a defect, not a difference of emphasis.*

<!-- END GENERATED: current_state_contract -->


**Phase 0M-R3A — Final state, via-technology and TSV-margin closure.** This section supersedes
the corresponding statements of Phase 0H.

### Verdict — Z1/Z2 ORDERING SURVIVES BUT INTRA-VR VIA TECHNOLOGY REMAINS UNSOURCED

*Phase 0G verdict, still standing and refined by this phase:* NO ACTIVE MECHANICAL CONSTRAINT --
RESPONSE COUPLING ONLY.

- THE ORDERING IS UNTOUCHED. D_driver = 1.1943 on the frozen Phase-0M-R3 pair. Nothing in this gate changed a solve: the corrections are to provenance, to arithmetic direction and to stale current-state text.
- DEFECT #58, THE MOST IMPORTANT FINDING. `ls_to_L` connects the low-side GaN switch node on tier 1 to the inductor terminal on tier 3, a 673 um vertical span between embedded-component layers inside the converter cell, carrying 20.408 A. Phase 0M-R3 justified its 15 -> 20 um repair as inside `design_variables.tsv.radius_m`, a range that governs THROUGH-SILICON VIAS. The framework's own source picture separates the two structures: components are embedded within the substrate power layers, and the TSV field runs BENEATH the cell from the substrate underside, spanning 74 um for ARCH_Z1. No sourced rule governs a stacked via through substrate power layers, so the repair is a design point in an unsourced process window.
- DEFECT #59, A SIGN ERROR. Phase 0M-R3 wrote that a 34 um TSV costs 22.8 % MORE vias. n_required scales as 1/A_cu, so 15 140 -> 11 692 is 22.8 % FEWER, and a reduction rather than a cost. A second error in the same sweep: 34 um was reported as the smallest diameter with positive margin, but the grid was 30/34/40/50/60 and never evaluated 32 um, which passes the same modest bound at M_AR = 1.067 for 12.5 % fewer vias.
- DEFECT #57, THE CURRENT-STATE TABLE WAS A PHASE BEHIND. Two independent representations of current state exist and only one was advanced in Phase 0M-R3. The report carried a section headed `Current scientific status (Phase 0M-R3)` whose table said phase = 0M-R2 complete, gave the Phase-0M-R2 verdict and said ZERO OF TWELVE REALIZABLE after a realizable pair had been found. A separate next-gate field still listed adopting the cooling model and putting the RDL in the mesh as future work, both completed two phases earlier.
- THE ROUTING ARITHMETIC IS CORRECT AND INDEPENDENTLY REPRODUCED. An implementation sharing no code with the production path returns 1.2360 at r = 15 um and 0.9344 at r = 20 um, matching to machine precision at all five radii tested. Only the provenance claim failed, not the numbers.
- THE WORDING `SOURCED 34 um VIA` IS WITHDRAWN. No primary source specifies 34 um; what is source-backed is the RANGE. The licensed phrasing is a design point selected within the source-backed allowable range.

**What this is not.** This is NOT a finding that the mechanics is wrong or irrelevant. The
response model is converged, cross-validated and sign-stable, and since Phase 0I it yields a
LOCAL FATIGUE-RELEVANT INELASTIC RESPONSE METRIC rather than load alone. That metric is a
RESPONSE, not damage: it becomes damage only through a sourced damage law, life only through a
life model, and a criterion only with an admissible allowable, and none of those three is
closed. It is a finding that no admissible mechanical inequality exists to turn that response
into a constraint, and that several first-order physical models exist as validated screening
tools without yet driving the production path.

**Falsification gate G2: NOT_TESTED.** NOT TESTED since Phase 0B, and the reason has narrowed
twice. Phase 0H could test nothing because it had neither a failure-relevant metric nor an
allowable. Phase 0I supplied the metric -- convergent, verified in 0I-R, tied to a documented
mechanism -- so g_mech(x) <= g_allow is writable in FORM. Phase 0J-R then obtained the primary
life-law sources and reproduced Syed 2004's author-corrected calibration, so ACCESS is no longer
the blocker. What remains is g_allow itself, blocked for TWO independent reasons, either
sufficient: no required life exists anywhere in this repository or in any supplied source, and
absolute N_f is unvalidated because the constitutive model that feeds it is fitted on
Sn3.9Ag0.6Cu far below the stresses the package reaches. Phase 0K withdrew the framing that
N_required was the sole blocker.

#### Verdicts considered and rejected

| candidate verdict | why rejected |
|---|---|
| Final Report State Closed; Z1/Z2 Conditional Realizability And Ordering Survive | rejected. Option A is unavailable while any current-facing stale block remains, and three were found: the Phase-0M-R2 current-state table, the obsolete next-gate block and residual damage terminology. It would also ignore DEFECT #58 entirely. |
| Z2 Tsv Process-Margin Repair Valid; Ordering Unchanged | rejected as the dominant statement. It is true of the TSV and it answers the smaller of the two questions this gate asked, omitting the finding that the intra-VR via repair has no process provenance at all. |
| Phase-0M-R3 Via Repair Used The Wrong Process Technology | rejected as the dominant statement although it is TRUE and is the single most important finding. Stated alone it implies the architecture result fell with it. The ordering is untouched at D_driver = 1.1943, and a verdict must say so. |
| Phase-0M-R3 Tsv Count Claim Was Numerically Wrong But Architecture Ordering Survives | rejected as the dominant statement. The count claim was indeed wrong in sign, but it is the lesser of the two defects: it misstates a benefit as a cost, whereas DEFECT #58 removes the provenance from the repair the whole realizability result rests on. |
| Realizability Status Must Be Reopened | rejected only because option B says the same thing more precisely. Realizability IS reopened -- that is what "via technology remains unsourced" means -- and B additionally records what survived. |

#### Optimizer gate

| condition | met | detail |
|---|---|---|
| 1 — assembly-state response survives calibrated board and thermal-boundary uncertainty | **PARTIAL** | The thickness RESPONSE survives calibrated board and thermal-boundary uncertainty with 0 sign flips in 20 combinations. But the assembly-state REVERSAL the condition was posed about does not survive -- it does not exist. |
| 2 — a criterion or user-set ε can actually alter the feasible design set | **FALSE** | No criterion exists, so nothing can alter the feasible set. Phase 0G additionally argued the computed range sits far below conventional tolerances; Phase 0H Sec.18 RETRACTED that comparison as unsourced, which strengthens rather than weakens the conclusion -- whether the range is safe or constraining is UNKNOWN. |

**BOTH conditions were required. Condition 2 fails outright and condition 1 fails in the sense
it was posed. The global ETM optimizer is NOT recommended and was NOT built.**

### Claims by status

Status vocabulary: **PROVEN** — numerically converged *and* cross-checked against an independent solver. **SUPPORTED** — converged in one solver, no independent cross-check. **CONDITIONAL** — true only under a named open input. **SUPERSEDED** — asserted in an earlier phase and no longer current.

#### PROVEN (12)

- **geometry_realizability** (Phase 0F) — A DVPD converter's component stack sets a hard lower bound on substrate thickness, and that bound excluded both thicknesses swept in Phases 0B-0E.
    - *Evidence:* `results/phase0f/GEOMETRY_REALIZABILITY_AUDIT.md`
- **rail_dependence** (Phase 0D-R) — The rail carried by a vertical interconnect changes its loss by ~1960x for fixed transferred power, and which rail it carries is architecture-specific.
    - *Evidence:* `results/phase0dr/POWER_PATH_AUDIT.md`
- **allocation_policy** (Phase 0E) — A via field's loss is proportional to current only under minimum-capability provisioning; under geometric allocation the same field obeys P ~ I^2.
    - *Evidence:* `results/phase0e/tsv_allocation_sensitivity.csv`
- **no_ac_correction** (Phase 0E) — No AC correction to the vertical interconnect is required at the switching frequency; HFSS shows loop resistance flat to 0.18 % below the 19.1 MHz skin crossover.
    - *Evidence:* `results/phase0e/em_validation.md`
- **thermal_ordering** (Phase 0E,0F) — An independent 3-D thermal solver reproduces candidate ordering exactly at both 240 W and 1 kW.
    - *Evidence:* `results/phase0e/thermal_validation.md, results/phase0f/thermal_moose_1kw.csv`
- **unit_consistency_defect** (Phase 0G) — Vertical-tier losses were evaluated per regulator and summed with a system-wide lateral loss, understating every vertical tier by n_vr -- 4x at 240 W and 49x at the 1 kW reference.
    - *Quantitative:* P_TSV / P_TSV,corrected = 49.004 to 49.055 at all nine thicknesses; independent hand check 89.7768 mW/VR x 49 = 4.399 W agrees
    - *Evidence:* `results/phase0g/electrical_crossover_uncertainty.md, DEFECT #30`
- **bcb_is_a_clamp** (Phase 0G) — The compact BC-B foundation restrains all three DOF on the underside plane, so it models a clamp and not a board. It never recovers its own free limit: at vanishing stiffness it gives 0.739 um where the free package on the identical mesh gives 8.287 um.
    - *Quantitative:* S_h > 0 at all 12 stiffnesses over 7 decades -- no crossover k* exists
    - *Evidence:* `results/phase0g/support_stiffness_sweep.csv, results/phase0g/board_foundation_calibration.md`
- **thickness_ordering_universal** (Phase 0G) — Thicker substrate reduces warpage in the free package and in every explicitly constructed assembly, across the whole board envelope from compliant to metal-backed, at every stress-free reference temperature and under every thermal boundary tested.
    - *Quantitative:* S_h = -0.039 to -0.886 in 5 board cases; sign stable across 3 reference temperatures and 4 thermal boundaries; 0 sign flips in 20 combinations
    - *Evidence:* `results/phase0g/explicit_board_crosscheck.csv, results/phase0g/footprint_m1_1kw.csv, results/phase0g/cooling_topology_comparison.csv`
- **gan_height_sourced** (Phase 0H) — The GaN device heights are no longer open. Manufacturer datasheets give 685 um nominal (815 max) for the high-side EPC2212 and 606 um for the low-side EPC2090, against the 0/100/250 um envelope Phases 0F-0G invented.
    - *Quantitative:* for the EMBEDDED architecture this raises h_sub,min from 0.770 mm to 1.176-1.426 mm
    - *Evidence:* `results/phase0h/geometry_height_closure.md`
- **architecture_dependent_realizability** (Phase 0I) — COMPONENT-HEIGHT REALIZABILITY IS ARCHITECTURE DEPENDENT. Component height constrains substrate thickness ONLY for the embedded architecture. Where the converter is below, above or beside the substrate, nothing it contains constrains h_sub, and the binding constraint becomes TSV manufacturability.
    - *Quantitative:* h_sub,min = 1.276 mm embedded (MLCC nominal) against 0.300 mm for backside, power-die and 2.5D -- the source-demonstrated TSV layer thickness (June-2026 Table III, d = 30 um at h = 300 um, AR 10:1). A 4.3x wider realizable range.
    - *Evidence:* `results/phase0i/REALIZABILITY_BY_Z_ARCHITECTURE.md, DEFECT #33`
- **warpage_is_not_a_reliability_proxy** (Phase 0H) — Global die warpage does not predict the local interconnect loading for this architecture, and the relationship is not even sign-stable across assembly states.
    - *Quantitative:* 70 paired runs: Spearman rho = 0.112 (all cases), 0.349 (mounted), -0.793 (free) against interface shear. Across the mounted thickness sweep warpage varies 3.0x (9.66 -> 29.23 um) while shear stays within +-9 %.
    - *Evidence:* `results/phase0h/warpage_local_correlation.csv, results/phase0h/local_metric_selection.md`
- **defect30_changed_a_240w_ranking** (Phase 0H) — DEFECT #30 inverted an architecture comparison at 240 W as well as at 1 kW. Replaying the eleven Phase-0E candidates with the scope-guarded evaluator moves three ranking positions.
    - *Quantitative:* ARCH_B distributed j=2.0 h=0.5 shifts +356.83 mW (+1.576 %) and falls from third-best to worst of the five distributed cases; ARCH_A cases shift 16-25 mW because their vias carry only leakage-scale current
    - *Evidence:* `results/phase0h/DEFECT30_GLOBAL_PROPAGATION_AUDIT.md`

#### SUPPORTED (3)

- **footprint_agreement_mounted** (Phase 0G) — In a mounted assembly the electrical and mechanical preferences on the footprint lever AGREE: the larger, finer-partitioned footprint is both lower loss and lower warpage.
    - *Quantitative:* electrical -6.633 W for M = 36 -> 49 (259.2 -> 329.3 mm2); mechanical S_A = -0.166 to -0.290 in all 5 board cases
    - *Independent corroboration:* June-2026 Sec. I asserts the same direction qualitatively -- distributed VRs produce localized deformation rather than global package deflection, reducing overall warpage sensitivity. Direction only; no number is given.
    - *Evidence:* `results/phase0g/footprint_board_envelope.csv, results/phase0g/footprint_placement_recheck.md`
- **count_inert** (Phase 0B,0C) — Regulator count is mechanically inert at constant total footprint and heat.
    - *Evidence:* `results/phase0b, results/phase0c`
- **rdl_dominates_arch_conditional** (Phase 0H) — Package distribution loss is dominated by lateral RDL spreading for ARCH_A at every realizable thickness, but NOT for ARCH_B, whose via field exceeds the RDL by up to 11x above roughly 0.9 mm.
    - *Quantitative:* ARCH_A: RDL 0.642 W against TSV 0.010-0.163 W. ARCH_B: TSV 0.450 W at 0.80 mm rising to 7.210 W at 2.00 mm against a flat 0.642 W RDL.
    - *Evidence:* `results/phase0h/interconnect_decomposition_1kw.csv`

#### CONDITIONAL (3)

- **archA_interior_optimum** (Phase 0G) — ARCH_A retains a numerically resolved interior electrical optimum at h_sub = 0.90 mm.
    - *Condition:* resolved but NOT actionable -- the optimum is 8.634 mW deep on a 125 W budget (0.0069 %). The ARCH_A/ARCH_B gap at fixed thickness is 52x larger than the entire depth of this optimum.
    - *Quantitative:* numerical floor 0.0977 mW; depth vs 0.80 mm = 88.4x floor, vs 1.00 mm = 9.6x floor
    - *Evidence:* `results/phase0g/crossover_hires_ARCH_A_fixedA.csv`
- **thickness_opposition** (Phase 0G) — Substrate thickness is a genuine ETM opposition: electrically thinner is better, mechanically thicker is better.
    - *Condition:* the opposition is real and sign-stable, but NO criterion exists to make it binding (G2 NOT TESTED), so it cannot restrict a feasible set. It is a response coupling, not a constraint.
    - *Quantitative:* electrical +6.706 W for 0.80 -> 2.00 mm (ARCH_B nominal); mechanical -44 % warpage over the same range (FR-4 1.6 mm board)
    - *Evidence:* `results/phase0g/electrical_crossover_uncertainty.md, results/phase0g/explicit_board_crosscheck.csv`
- **mounted_warpage_floor** (Phase 0G) — A mounted assembly cannot reach the warpage levels the free package suggests: its floor is 14.03 um where the free package reaches 1.27 um.
    - *Condition:* magnitudes are NOT validated -- board CTE, board modulus envelope and the absence of a solder-mask/copper-plane laminate structure are engineering values, not measurements of the reference system.
    - *Evidence:* `results/phase0g/mechanical_epsilon_corrected.csv`

#### SUPERSEDED (9)

| claim | asserted in | superseded by |
|---|---|---|
| **footprint_opposition** — HVR footprint is simultaneously an electrical and a mechanical design variable and the two OPPOSE: larger footprint lowers electrical loss and raises warpage. Sign preserved in both assembly states. | 0C,0D,0D-R,0E,0F | Phase 0G: the sign is ASSEMBLY-STATE DEPENDENT. It is positive in the free package (+0.203) and the compact clamp (+0.058) and NEGATIVE in all five explicit assemblies (-0.166 to -0.290). In a mounted assembly the two disciplines AGREE. The reference paper asserts the mounted direction. Replaced by claim footprint_agreement_mounted. |
| **assembly_state_reversal** — The mechanical thickness preference REVERSES between assembly states: free packages prefer thicker substrates, mounted packages prefer thinner ones. | 0F | Phase 0G: an artifact of BC-B's three-DOF in-plane clamp. No explicit assembly reproduces it -- S_h < 0 in all five board cases, at three reference temperatures and four thermal boundaries. BC-B cannot recover its own free limit (0.739 vs 8.287 um) and no support stiffness k* exists over seven decades. |
| **archB_interior_optimum** — ARCH_B has an interior electrical thickness optimum near h_sub = 1.0 mm. | 0F | Phase 0G: an artifact of DEFECT #30. The minimum SURVIVED a 25x tighter convergence tolerance -- it was not numerical -- but vanished when the vertical-tier unit error was fixed. Corrected ARCH_B is monotonically increasing with the optimum on the thin boundary in 9 corners of 9. |
| **win_win_win_200_500** — Substrate thickness 200 -> 500 um is win/win/win and survived every correction. | 0B,0C,0D,0D-R,0E | Phase 0F: both thicknesses are GEOMETRICALLY INFEASIBLE for the selected converter. The trend DIRECTION survives on realizable geometry (800 -> 1500 um, -81.9 % warpage) but the magnitudes and the swept range do not. |
| **no_arch_dependent_thickness** — No architecture-dependent thickness tradeoff exists. | 0D-R,0E | Phase 0F: at 1 kW ARCH_B's electrical optimum is interior while its mechanical preference is monotone. Phase 0G audits whether that interior optimum is numerically resolved. |
| **archB_infeasible** — ARCH_B is infeasible. | 0D-R | Phase 0E: feasible under every source-backed current density; the verdict rested on an unsourced 4.8 mA per-via limit. |
| **placement_spread_188** — The electrical spread across placements is 188.8 %. | 0D-R | Phase 0E: 46.7 % on the sourced RDL stack. |
| **exchange_rate_16** — The footprint ETM exchange rate is 16.2 W/um. | 0D-R | Phase 0E: 11.48 W/um; Phase 0F at 1 kW: 12.86 W/um. |
| **ansys_unavailable** — ANSYS cross-validation is impossible because the licence server is down. | 0B,0C,0D,0D-R,0E | Licence restored 2026-09-06. HFSS and Icepak used; Q3D is not licensed. |

### Open items

- **gan_mlcc_layer_heights** — GaN device and MLCC layer heights
    - *Why it matters:* sets the HVR cell height and hence the minimum realizable substrate
- **em_lifetime_limit** — electromigration lifetime current density for copper TSVs
    - *Why it matters:* the provisioning density is closed; the reliability limit is not
- **rdl_dielectric_and_stitching** — RDL dielectric stack and inter-layer stitching via density
- **board_laminate_structure** — real board laminate structure -- copper plane fractions, solder mask, stiffener, and the board's true in-plane CTE
    - *Why it matters:* Phase 0G CLOSED the question the Phase-0F reversal rested on: BC-B is a clamp, no k* exists, and every explicit board gives the free-package sign. What remains open is only MAGNITUDE. The 9.7-29.2 um range is an engineering envelope, not a prediction, and must not be quoted as predicted warpage.
    - *Change in this phase:* was board_foundation_stiffness (OPEN, Phase 0F) -- the SIGN question is now closed; only magnitude remains
- **cooling_topology** — whether the real package is cooled from the top or from inside the substrate
    - *Why it matters:* sets the sign of the through-thickness thermal gradient
    - *Change in this phase:* BOUNDED in Phase 0G rather than closed. It moves warpage magnitudes by up to 45 % and halves S_h, but flips no sign in any configuration tested. The mounted normalized response is invariant to 0.07 % across a 4x h_top band. Substrate-side-only cooling is separately thermally infeasible at 1 kW.
- **assembly_pre_stress** — assembly / cure / cooldown reference state (M1)
    - *Why it matters:* all warpage here is INCREMENTAL OPERATIONAL, not TOTAL ASSEMBLED
    - *Change in this phase:* BOUNDED in Phase 0G. Raising the reference to 150/175 C changes MAGNITUDES by up to +54 % (25.1 -> 38.7 um mounted) but leaves the mounted normalized response stable to 0.5 % (S_h = -0.4421 / -0.4397 / -0.4400) and flips no ordering. Every absolute warpage number in this project is therefore a LOWER BOUND. A validated pre-stress model still requires the cure schedule, cure shrinkage, viscoelastic relaxation and reflow profile -- none available for the reference system.
- **mechanical_criterion** — an admissible operational-state warpage or RDL-shear allowable for this stack
    - *Why it matters:* this is ONE OF THREE INDEPENDENT blockers for G2 -- the other two being an OPEN N_required and an unvalidated absolute N_f -- and it independently blocks any constraint-based optimizer. Phase 0G searched the full corpus and found none: June-2026 names the failure mechanisms (global package warpage, delamination, RDL shear) but attaches no number to any of them. External standards are unretrievable in this environment AND inadmissible on inspection -- package-outline coplanarity governs the ball plane of a component as supplied at a defined measurement temperature for solderability at reflow, which matches neither the package state, the temperature, the measurement definition nor the failure mechanism analysed here.
    - *Evidence:* `results/phase0g/mechanical_criterion_audit.md`

### Not tested

- **G2** — feasible-set reversal under a mechanical criterion
    - *Why:* no source-backed criterion matching this package state, temperature, size, measurement definition and failure mechanism could be found
    - *Consequence:* the epsilon sweep is PARAMETRIC CONSTRAINT SENSITIVITY, never feasibility
- **transient** — transient electrothermal and mechanical response
- **m1_full** — full assembly-pre-stress model with plasticity and lifetime

### Defects logged in this phase

#### DEFECT #29 — DUPLICATED CURRENT CLAIMS CAN BECOME SEMANTICALLY STALE

The report stated the same claim in Executive Summary, Positive Results, Negative Results, the
uncertainty ladder and Next Steps; each phase updated only some. Every individual sentence was
true when written, so regex assertions could not catch the contradiction.

- *Fix:* This file is the single source of truth. Current-status sections are GENERATED from it and semantic tests compare the generated text against it.
- *Status:* **FIXED**

#### DEFECT #30 — UNIT INCONSISTENCY BETWEEN PER-REGULATOR AND SYSTEM-WIDE LOSS TERMS

vertical_tier() returns a PER-REGULATOR loss; rdl_network_solve() returns a SYSTEM-WIDE loss.
Phases 0D-R, 0E and 0F summed them directly, understating every vertical tier by n_vr -- 4x at
240 W, 49x at 1 kW.

- *Detected by:* Phase 0G Sec. 2 curve decomposition, after the convergence-tolerance hypothesis had been tested and eliminated
- *Impact:* INVERTED the Phase-0F architecture conclusion. ARCH_B's interior optimum was an artifact; corrected ARCH_B is monotonic with its optimum on the thin boundary.
- *Fix:* scripts/phase0e/architecture0e.py -- both terms expressed system-wide; guard test added; 151 tests pass.
- *Status:* **FIXED**

#### DEFECT #31 — THE SEMANTIC LEDGER WAS VACUOUS -- IT COULD NOT FAIL

The Phase-0F semantic ledger scored each withdrawn claim against a +-800-character window and
accepted 'was ', 'were ', 'became', 'becomes' and 'earlier' as exonerating context. In English
technical prose at least one of those appears in any such window, so EVERY ledger entry passed
unconditionally. The mechanism built to catch DEFECT #29 could not catch anything.

- *Detected by:* a deliberate NEGATIVE TEST -- three unqualified re-assertions of withdrawn claims were injected into the report and the ledger stayed green. The guards had never been checked for the ability to fail.
- *Impact:* Five genuinely stale statements were standing in the Executive Summary, the uncertainty ladder and Next Steps, all of them invisible to a green build.
- *Fix:* The exonerating vocabulary is restricted to markers that can only be present deliberately; the window is the containing PARAGRAPH or table cell instead of a page of prose; scoring runs on the Markdown so headings are unambiguous; and a claim is exonerated by its enclosing heading CHAIN, so a subsection inside a superseded phase inherits that framing. Verified in BOTH directions: the real report passes 49 checks, and five injected re-assertions are each caught.
- *Status:* **FIXED**
- *Lesson:* A guard that has never been observed to fail has not been tested. Every assertion added from Phase 0G onward is negative-tested before it is trusted.

#### DEFECT #32 — CURRENT_SCIENTIFIC_STATUS DID NOT CONTROL ALL CURRENT-FACING REPORT CONTENT

Phase 0G brought the CLAIMS LEDGER under this file and generated it, then declared DEFECT #29
fixed. But the Executive Summary, governing equations, validation status, novelty statement,
current limitations, publication-defensible claims and next steps were still hand-written, and
the Phase-0G ledger deliberately exonerates any withdrawn claim whose enclosing heading names a
historical phase -- which is right for narrative sections and wrong for sections that speak in
the present tense. Seven current-facing statements were therefore stale behind a green build:
thickness still called win/win/win and 'survived every correction'; 'no architecture-dependent
thickness tradeoff exists'; the withdrawn ARCH_B interior optimum; footprint still advertised as
the ETM opposition novelty; R_field = R_single / n_req with n_alloc absent from the symbol
table; the full 3-D MOOSE package validation still called NOT DONE when Phase 0E completed it as
TH-1..TH-5; and BC-B still described as a compliant mounted support after Phase 0G proved it a
three-DOF clamp.

- *Fix:* All seven are now GENERATED from this file into sentinel-delimited blocks, the report is checked to carry each block verbatim, and a CURRENT-FACING SECTION AUDIT forbids nine stale-claim signatures inside present-tense sections with per-pattern exonerations for ledger rows, negations and retractions. Verified in both directions: the clean report passes, and nine injected stale claims are each caught.
- *Status:* **FIXED**

#### DEFECT #33 — REALIZABILITY WAS ARCHITECTURE-BLIND

kw1.design_1kw() takes no architecture argument, so the EMBEDDED geometric rule t_cell + h_tsv
<= h_sub was applied to every architecture -- including ARCH_B, which converts BELOW the
substrate, and ARCH_C, which converts BESIDE the die. At h_sub = 0.30 mm the code answers 'no
inductor fits h_sub=300 um (budget 30 um)' identically for all three. The electrical model has
varied the converter's vertical position since Phase 0D-R; the geometric and mechanical models
never did.

- *Detected by:* Phase 0I Sec.2, on treating z-placement as an architecture variable
- *Impact:* Every 'unbuildable' verdict Phase 0H issued against a thin substrate is EMBEDDED-SPECIFIC. Non-embedded architectures reach 0.300 mm against the embedded 1.276 mm -- a 4.3x wider range including exactly the region the corrected electrical model prefers.
- *Fix:* scripts/phase0i/zarch.py -- realizable(arch, h_sub) applies the embedded stack rule only where the converter is embedded, and the source-demonstrated TSV-layer rule (June-2026 Table III, d = 30 um at h = 300 um, AR 10:1) elsewhere.
- *Status:* **FIXED**
- *Lesson:* A coupling is only modelled if EVERY domain sees it. The electrical model carried z-placement for five phases while geometry and mechanics silently did not, and no test could catch it because each domain was self-consistent on its own terms.

#### DEFECT #34 — PHASE-0G AND 0H FIGURES WERE NEVER EMBEDDED IN THE PDF

pandoc is invoked with cwd = results/, so a figure path written relative to the REPO ROOT
('results/phase0g/FIG.png') resolves to results/results/... . pandoc emitted 'Could not fetch
resource ... replacing image with description' for all 21 such references and substituted the
alt text. Every Phase-0G and Phase-0H figure was missing from the PDF, and the Phase-0I figures
would have been too.

- *Detected by:* Phase 0I, when a LaTeX error surfaced the pandoc warning stream that had been carrying these messages unread since Phase 0G
- *Impact:* Two full phases of figures absent from the delivered PDF while the build reported VERIFIED. No numerical result is affected; the deliverable was.
- *Fix:* Figure references are absolute, matching the convention every phase before 0G used. Two new checks: paths are resolved FROM PANDOC'S WORKING DIRECTORY, and the pandoc warning stream is scanned for 'Could not fetch resource'. Negative-tested: reverting one path to repo-relative fails both.
- *Status:* **FIXED**
- *Lesson:* A build warning nobody reads is not a warning. The verification suite now consumes the toolchain's own warning stream instead of only inspecting its output.

#### DEFECT #35 — PHASE-0I SCIENCE NOT FULLY PROPAGATED INTO CURRENT-FACING REPORT SECTIONS

Phase 0I added reliability physics but left seven current-facing statements in the Phase-0H
state. The Executive Summary still framed the answer as 'Phases 0G and 0H find'; the limitations
still said 'Neither local metric is fit for decisions', which referred to the two REJECTED
Phase-0H proxies and not to the new M2 metric that passes every convergence test; they still
said 'GaN and MLCC layer heights are still open' when GaN is source-backed; 'Exact next work'
still recommended publication reframing; the validation status still described the mechanics as
'M0 -- no plasticity, creep or fatigue' when a temperature-dependent elastic/plastic/creep
submodel now exists; the governing equations stopped at M0 thermoelasticity with no M2
constitutive law, damage-metric definition or stabilised-cycle definition; and the method still
counted eight gates.

- *Detected by:* Phase 0I-R Sec.18, a dedicated re-read of the current-facing sections against the Phase-0I evidence
- *Impact:* The report understated its own capability -- it described a model without failure physics after failure physics had been added -- and pointed the reader at the wrong next step.
- *Fix:* All eight items (A-H) repaired at the single source of truth and regenerated. The validation block now splits GLOBAL M0 from LOCAL M2 explicitly, and four M2 governing equations were added: the constitutive law, the damage-metric definition, the stabilised-cycle definition, and an explicit no_life_equation entry recording that no lifetime equation is current. Two further items were found while verifying A-H and are also fixed: the current-facing guard scope excluded the LIVE phase narrative even though it is headed 'current authoritative', so three over-claims inside it had never been checked; and the report build was not idempotent, because the new reliability_metric fragment was anchored on a heading that a later splice consumes.
- *Status:* **FIXED**
- *Lesson:* A phase that ADDS capability must audit the current-facing text as carefully as a phase that withdraws a claim. DEFECT #29, #32 and #35 are the same failure in three directions: stale withdrawal, stale scope, and now stale capability.

#### DEFECT #36 — SIX NEW GUARDS WERE NEGATIVE-TESTED AGAINST PARAPHRASES, NOT THE REAL SENTENCES

Sec.20 requires every new semantic guard to be shown FAILING on an injected violation before it
is trusted. All six Phase-0I-R guards passed that test. The test was invalid. The injected
sentences were written by the same author, in the same sitting, as the regexes -- so each
injection was phrased to match its own pattern. Checked afterwards against the sentences that
had ACTUALLY appeared in the report, ALL SIX guards missed: the real text said 'Z5 is
eliminated' where the guard looked only for the literal string '2.5D'; 'A 0.300 mm substrate is
realizable' where the guard looked for 'manufacturable'; 'Z1 keeps a 30 mW edge' where the guard
looked for 'electrically better'; 'the relative-life ratio is parameter-free' where the guard
required the unhyphenated 'relative life'; and 'of eight failure mechanisms only ONE is
computable' where the guard required the reversed word order 'only one of eight failure
mechanisms'.

- *Detected by:* Phase 0I-R Sec.20 follow-up, by testing each pattern against text quoted from the report itself rather than against text written for the test
- *Impact:* Six guards reporting PASS while blind to their own subject matter, and one real consequence: the stale Executive Summary sentence 'of eight failure mechanisms only ONE is computable' sat in a current-facing section, in guard scope, and was not flagged. It was found by manual re-reading, which is exactly what the guard existed to replace.
- *Fix:* Patterns rewritten against the verbatim historical sentences. A PERMANENT self-test replaces the one-off injection: GUARD_SELFTEST pairs every one of the fifteen current-facing guards with the exact sentence it exists to reject, and the build fails if any pattern misses its sentence OR if an exoneration context clears it. A coverage check makes it impossible to add a guard without a self-test sentence. The eight pre-0I-R guards were retro-fitted with the same self-test.
- *Status:* **FIXED**
- *Lesson:* A negative test written by the author of the guard, at the same time as the guard, tests the author's model of the failure and not the failure. The injection must be the REAL text -- recovered from the artifact or its history -- and it must be asserted permanently in the suite, not performed once by hand. DEFECT #31 said a check never seen to fail has not been tested; #36 adds that a check seen to fail on a straw man has still not been tested.

#### DEFECT #37 — OLD LOCAL-PROXY RESULT SURVIVED AFTER THE M2 METRIC REPLACED IT

The Executive Summary stated, as a CURRENT result, that 'the opposition is resolved ONLY in
global warpage: in the one local metric available the thickness effect is 1.96 %, which is 7x
below that metric's own uncertainty.' Both halves belonged to Phase 0H. The '1.96 %' is the
thickness effect in the SMEARED INTERFACE SHEAR proxy, and the '7x below its own uncertainty' is
that proxy's 14.14 % floor. Phase 0H REJECTED that proxy as non-monotone under refinement, and
Phase 0I replaced it with a convergent M2 solder metric -- but the sentence describing the
rejected proxy stayed in the current-facing text and kept asserting that no local metric
resolves the thickness effect.

- *Detected by:* Phase 0J Sec.38, a directed re-read of the Executive Summary against the Phase-0I-R state
- *Impact:* The report asserted, as current, that the thickness opposition is invisible locally. Phase 0J measures it directly at all eleven z-sweep points and finds it monotone in every architecture: -5.6 % (Z1), -6.1 % (Z2), -17.2 % (Z4) in accumulated inelastic path. The trend is real, preserved, and simply 3-5x smaller than global warpage makes it look.
- *Fix:* Replaced at the single source of truth with the measured M1 values and the explicit statement that the 1.96 % figure is withdrawn as a current result and retained only in the Phase-0H historical section, which Sec.38 forbids editing.
- *Status:* **FIXED**
- *Lesson:* A phase that REPLACES a metric must retire the replaced metric's CONCLUSIONS, not only its numbers. DEFECT #29, #32, #35 and now #37 are four faces of one failure: stale withdrawal, stale scope, stale capability, and stale superseded-instrument.

#### DEFECT #38 — PHASE-0J-R LIFE-LAW STATUS NOT FULLY PROPAGATED INTO CURRENT-FACING REPORT TEXT

Nine current-facing statements still described a project that could not predict life, three
phases after it could: 'No lifetime is predicted anywhere'; 'the EXPONENT m does NOT cancel, and
no m is sourced'; 'Over m = 0.5 to 5 the Z2/Z1 ratio spans 1.25 to 9.18'; 'solder fatigue ...
has no life law and so yields no pass/fail'. All were in the Executive Summary and all were
generated from the single source of truth.

- *Detected by:* Phase 0K Sec.1
- *Impact:* The report understated its own capability -- no life law after four had been admitted, no sourced exponent after two primary sources had bounded it at -1 and -1.3.
- *Fix:* Repaired at the source of truth and regenerated, separating the four things that must not be conflated: RELATIVE LIFE validated at 1.21-1.38x, CONDITIONAL ABSOLUTE LIFE not validated at a 4.1x spread, REQUIRED LIFE open, G2 not tested. Six guards added, each self-tested on the VERBATIM standing sentence and each negative-tested to failure.
- *Status:* **FIXED**
- *Lesson:* A phase that converts a negative result into a positive one must retire the negative's language as carefully as a phase that withdraws a claim retires the claim. Understating your own model never trips a scepticism check.

#### DEFECT #39 — PHASE-0K NARRATIVE CURRENT, BUT GENERATED STATUS AND NEXT-WORK FRAGMENTS PRE-0K

The Executive Summary's 'Exact next work' still read 'PHASE 0K -- SYSTEM-OWNER MISSION
DEFINITION' and still asserted 'the remaining blocker is ... a REQUIRED LIFE' -- the exact claim
Phase 0K withdrew. Worse than one stale sentence: NO Phase-0K result appeared in current-facing
text at all. The 474/3206 decision regions, the two-blocker finding, the G2 decision map and the
experiment design each occurred ZERO times.

- *Detected by:* Phase 0K-R Sec.1
- *Impact:* The report recommended as next work a phase that had already run, and named one blocker where its own analysis had established two.
- *Fix:* next_work rewritten from the source of truth. Sec.2 typed contract added (relative_life_0kr, absolute_life_0kr, mission_0kr, g2_0kr, experiment_0kr, next_step_0kr) so current status is GENERATED rather than remembered. Four guards with verbatim self-tests, all negative-tested. Sec.34 post-build audit added: the FINAL Markdown and the text extracted from the FINAL PDF are re-read AFTER generation -- 8 current-facing headings, 15 stale patterns, 0 hits.
- *Status:* **FIXED**
- *Lesson:* DEFECTS #29, #32, #35, #37, #38 and #39 are six instances of ONE failure: the narrative advances and the generated status does not. The structural fix is not another guard but a typed contract plus the rule that the BUILT ARTIFACT is what gets audited -- all three most recent report defects occurred at or after the generation step, not in the source.

#### DEFECT #40 — CREEP CALIBRATION VARIABLE DOES NOT MATCH THE SOLVER'S DRIVING VARIABLE

fit_norton_data (solder_model.py:84-96) regresses log(rate) on log(sigma_APPLIED) -- the total
uniaxial stress of a constant-load creep test, with no yield subtraction. CalculiX integrates
eps_dot = A*(sigma_vm - sigma_y(eps_in))^n and gives IDENTICALLY ZERO inelastic strain when
sigma_vm <= sigma_y (incplas.f:310-311, 599-605). These are different independent variables.

- *Detected by:* Phase 0L Parts III-V: CalculiX 2.23 source trace, then 7603 single-element solver increments against three candidate laws.
- *Impact:* The overstress is NEGATIVE at 16 of the 19 calibration points, so in the solver's own variable the calibration experiment lies entirely inside the elastic domain. Solver probe TEST F: the card reproduces 0 of 19 of its own source points; 16 give exactly 0.0 and the other three are low by 4.7e7x, 1.8e12x and 2.4e5x. The quoted 8.3 % rms fit residual measures a curve in a variable the solver never evaluates.
- *Fix:* NOT repaired silently. Part VI shows the consistent refit FIT-B is NOT CONSTRUCTIBLE (0 usable points at 45 and 80 C, 1 at 115, 2 at 150). The only consistent route is sigma_y -> 0, which is what the CalculiX manual itself prescribes for creep below yield, and is carried as model M1 in the Part XI replay.
- *Status:* **CONFIRMED**
- *Lesson:* A fit residual is only evidence if the residual is computed in the variable the consumer uses. The check that caught this -- feed the calibration points back through the solver and see if it returns them -- costs one afternoon and was never run in eleven phases.

#### DEFECT #41 — THE CREEP DATA IS Sn3.9Ag0.6Cu, AND ALL THREE YUAN TABLE CITATIONS ARE WRONG

solder_model.py cites Yuan 2023 'Table 26' for the 19 creep points, 'Table 27' for the Garofalo
constants and 'Table 31' for the Chaboche constants. The paper was retrieved in full
(PMC10381129). It has ELEVEN tables. The correct sources are Table 5, Table 6 and Table 10; the
VALUES all match, only the table numbers are wrong. Yuan section 4.1 states the creep dataset
'is drawn from Xiao and Armstrong [10]', whose title is 'Tensile creep and microstructural
characterization of bulk Sn3.9Ag0.6Cu lead-free solder'.

- *Detected by:* Phase 0L Part V, by fetching the cited paper instead of the citation.
- *Impact:* The creep half of the SAC305 card is calibrated on Sn3.9Ag0.6Cu -- 3.9 wt% Ag against SAC305's 3.0 wt%. The yield half traces to Motalab SAC305 data through an Anand fit and then synthetic curves, so the two halves of one card are different alloys, and the overstress law subtracts one from the other. The brief forbids transplanting high-Ag SAC sets without transferability evidence; Part VII searched 344 works and found none.
- *Fix:* Citations corrected in solder_model.py (values unchanged, so no result moves). The alloy mismatch is NOT repairable from available data and is carried as a standing condition on every creep-derived result.
- *Status:* **CONFIRMED**
- *Lesson:* A citation that names a table number is checkable in minutes and was carried for eleven phases, into the report and into the Phase-0K-R domain audit, unchecked.

#### DEFECT #42 — *CREEP TEMPERATURE GRID: LINEAR-IN-A INTERPOLATION AND CLAMPING ABOVE 125 C

creeps.f:300-330 and materialdata_me.f:413-429 interpolate A, n and m LINEARLY between card rows
and CLAMP outside them. norton_at() builds the rows on an Arrhenius basis, so solver and intent
agree only AT the rows. Production decks (run_zcompare.py:36, run_convergence.py:27) write rows
at -40/0/25/50/75/100/125 C.

- *Detected by:* Phase 0L Part IV TEST G (measured 0.9996-0.9999 against linear-in-A, and 1.33x / 2.80x / 20.0x against Arrhenius) plus card_grid_audit.py.
- *Impact:* Between rows over 45-150 C the solver's rate is 0.83x to 3.88x the intended value; worst on the grid is 8.94x. Above the 125 C top row the card clamps, and because the clamped exponent is wrong too the error is stress-dependent: 0.62x at 20 MPa rising to 8.70x at 100 MPa. The 110->150 C candidate experiment profile runs entirely above the top row.
- *Fix:* Part XI replays every model on a corrected 18-row grid spanning -40..150 C, which cuts the between-row span to 0.81-1.51x and removes the clamping. M0_COARSE is retained in the replay so the grid effect is separable from the constitutive effect.
- *Status:* **CONFIRMED**
- *Lesson:* A material card is an interpolation table, not a function. Whatever the card generator believes about the functional form is discarded at the solver boundary.

#### DEFECT #43 — OMITTING *PLASTIC IS UNDEFINED BEHAVIOUR, NOT A ZERO YIELD SURFACE

The manual says that without a *PLASTIC card 'a zero yield surface without any hardening is
assumed'. In fact materialdata_me.f:331-333 sets plconloc(801)=0.5, incplas.f:130 therefore sets
user_hardening=1, and incplas.f:288 calls uhardening(). The shipped src/uhardening.f is an empty
stub that never assigns fiso, which incplas.f never initialises.

- *Detected by:* Phase 0L Part IV TEST A, which probed both routes precisely because the source said they need not agree.
- *Impact:* LATENT, not active: every current deck carries a *PLASTIC card. In this binary the two routes agree to 3e-6, so the uninitialised value reads as zero here -- an observation about one build, not a guarantee.
- *Fix:* Rule adopted and used in all Phase-0L decks: to obtain a zero yield surface, write an explicit flat *PLASTIC card at sigma_y = 1e-6 MPa rather than omitting the card.
- *Status:* **DOCUMENTED (latent, not triggered)**
- *Lesson:* Where the manual and the source disagree about a default, the source wins and the behaviour must be probed rather than assumed.

#### DEFECT #44 — PHASE-0L CONSTITUTIVE AND RELIABILITY STATUS NOT PROPAGATED INTO CURRENT-FACING TEXT

A directed comparison of both reports against the Phase-0L findings, on thirteen named claim
patterns, found 21 stale current-facing hits. In the historical report they cluster in three
GENERATED blocks: the Executive Summary (8 hits, and NO mention of Phase 0L anywhere in it), the
governing-equation status (2 hits, including 'C still cancels in a ratio, so the RELATIVE ratio
Z2/Z1 = 1.21-1.38 is validated', which is wrong in the number, in the word validated and in the
cancellation claim), and the mechanical validation status ('M0 rung only ... no plasticity,
creep or fatigue', which describes the GLOBAL model as if it were the whole mechanical model).
In the standalone report there are three genuine defects plus one wrong mechanism, the worst
being an INTERNAL CONTRADICTION: section 17.4 says 68 specimens per cell and section 23.1 says
34.

- *Detected by:* Phase 0L-R Part 1, scripts/phase0lr/propagation_audit.py
- *Impact:* A reader of either Executive Summary would take away a superseded relative-life range, the word VALIDATED where only CONDITIONAL is earned, an experiment described as ready to execute when it is blocked, and a specimen count superseded twice over.
- *Fix:* Repaired at the source. All three historical blocks are generated from current_facing.* in this file, so the YAML was rewritten and the blocks regenerated; the five standalone defects were repaired in place. A scanner bug was also fixed during the audit: '##' subsections did not inherit their parent chapter's scope, which made superseded chapters read as current.
- *Status:* **CONFIRMED AND FIXED**
- *Lesson:* This is the SEVENTH instance of one failure -- the narrative advances and the generated status does not. Phase 0K-R added a typed contract to stop it and the contract itself was not extended by Phase 0L. A contract only works if the phase that changes the science is required to change the contract in the same breath.

#### DEFECT #45 — BOARD-LEVEL CAMPAIGN WAS DESIGNED BEFORE THE DOMINANT CONSTITUTIVE UNCERTAINTY WAS CLOSED

The 4-cell, 34-per-cell, 136-package campaign was designed in Phase 0K-R and costed in Phase 0L
on the assumption that specimen count was the binding constraint. It is not. With the corrected
model the ceiling on the discrimination Z-score is 3.61 against a target of 3.0, and that
ceiling is set by the SIMULATION-uncertainty floor of 0.06, which no number of boards reduces.
Halving that floor takes the campaign from 48 specimens per cell to 18, i.e. from 192 packages
to 72.

- *Detected by:* Phase 0L-R Part 16 value-of-information analysis, results/phase0lr/sample_count_vs_simulation_uncertainty.csv
- *Impact:* Worse than inefficiency. The campaign's headline output is an absolute-life constant, and fitting that constant on top of an extrapolated constitutive model buries the constitutive error INSIDE the fitted constant, where it can never be separated again. Running the campaign first does not merely under-inform, it contaminates the quantity it is run to obtain.
- *Fix:* Not a code defect -- classified as a SEQUENCING defect. The campaign is re-sequenced behind material characterisation, not cancelled. Sample count is marked PROVISIONAL and must not be frozen while constitutive uncertainty dominates.
- *Status:* **CONFIRMED (sequencing, not code)**
- *Lesson:* A design of experiments is only as good as the uncertainty decomposition behind it. Phase 0K-R optimised the term it could compute -- Weibull scatter -- without checking which term actually bound the answer.

#### DEFECT #46 — STEP-BOUNDARY TEMPERATURE ALIASING INFLATED EVERY INELASTIC-ENERGY NUMBER BY 18.5 %

parse_temperature() kept the FIRST temperature block at a given printed time while
parse_tensors() keeps the LAST. CalculiX prints the same rounded time on both sides of a step
boundary, so tensors and temperature were taken from OPPOSITE sides of every boundary -- 11 of
690 time points, at which the parsed temperature was wrong by about 55 K. The thermal strain is
hydrostatic, so this injected a spurious VOLUMETRIC inelastic strain of 1.2e-3 into a quantity
that must be isochoric: the trace of the reconstructed inelastic strain was 8.7e-4 against
2.9e-6 for a reconstruction using the solver's own mechanical strain.

- *Detected by:* Phase 0L-R Part 4. An independent reimplementation using the solver's ME output disagreed with production by a suspiciously STABLE 18.5 %; splitting the work into deviatoric and volumetric parts localised it immediately -- the deviatoric parts were identical to six figures and the whole discrepancy was volumetric.
- *Impact:* Every energy-derived quantity produced before this phase is affected: M3/M5, w_acc, w/eps, the discrimination ratio D, the energy-based life-law ratios and hence the experiment sample count. PEEQ and every strain-based metric are UNAFFECTED, because PEEQ is read from the solver rather than reconstructed. Measured on the M1 Z1 baseline, W falls from 1.45725 to 1.19157 MJ/m3 once fixed.
- *Fix:* parse_temperature now keeps the LAST block at each time, matching parse_tensors; agreement with the independent implementation improves from 18.5 % to 0.76 %. The decision-relevant replay cells were re-run with the fix. RECOMMENDED PERMANENT FIX, not applied in this phase because it requires re-running every deck: request ME in the decks and compute eps_in = ME - eps_elastic, which removes the temperature from the energy path entirely.
- *Status:* **CONFIRMED AND FIXED**
- *Lesson:* The audit that found this was written to check quadrature and convergence. What it actually caught was a parser disagreeing with its sibling about which side of a discontinuity to stand on. An independent reimplementation is worth more than a more careful reading of the same one -- and the first version of THIS audit was itself wrong in the opposite direction, for the same class of reason, until its own temperature parser was checked against the solver's thermal strain.

#### DEFECT #47 — PER-VIA CURRENT LIMIT WAS A PRIMITIVE IN AMPERES, AND IT IS THE ONLY THING THAT SETS FIELD RESISTANCE

configs/phase0dr/power_path_graphs.yaml carries i_max_a per tier -- BGA 0.5 A, C4 0.2 A, TSV
0.033 A, microbump 0.02 A -- as a primitive number. Phase 0M Part 3 derives that under the
allocation policy the framework actually uses, R_field = rho h J_max / I with the conductor
cross-section cancelling identically, so J_max is the ONLY parameter that sets the field
resistance and it was entered rather than derived.

- *Detected by:* Phase 0M Part 1 parameter classification
- *Impact:* The via-field resistance, IR drop and Joule loss of every architecture depend on a primitive. The geometry the framework carefully models cancels out.
- *Fix:* i_max_a is replaced by J_max * A_conductor, with J_max a PROCESS limit swept over the sourced 1e8 to 4e8 A/m2 envelope and A_conductor DERIVED from r and the liner.
- *Status:* **CONFIRMED, MODEL REPLACED IN scripts/phase0m/interconnect.py**

#### DEFECT #48 — ONE GLOBAL CURRENT-CROWDING CONSTANT APPLIED TO FOUR DIFFERENT INTERCONNECT CLASSES

scripts/phase0e/architecture0e.py sets CROWDING_DEFAULT = 1.326, measured in HFSS on ONE P/G TSV
loop, and multiplies the single-conductor resistance of BGA, C4, TSV and microbump by it alike.

- *Detected by:* Phase 0M Parts 7 and 8
- *Impact:* K_crowd measured over 107 converged transition geometries spans 0.606 to 1.483, a factor of 2.45. A generous landing pad gives K < 1; a narrow trace entry gives K > 1.4. The excess resistance dR is length-INDEPENDENT while K_crowd is not, so K_crowd is not even the right form.
- *Fix:* A 3-D DC conduction solver derives K_crowd per geometry (results/phase0m/current_crowding_transition_sweep.csv). dR, not K_crowd, is the transferable quantity.
- *Status:* **CONFIRMED, FUNCTION AVAILABLE, NOT YET WIRED INTO THE PRODUCTION PATH**

#### DEFECT #49 — THE TSV LINER IS ABSENT FROM THE CONDUCTOR AREA

ppdn.tier_area_m2() uses the full drilled diameter as conductor. A real TSV has a dielectric
liner between the copper and the silicon.

- *Detected by:* Phase 0M Part 2
- *Impact:* The conducting area is overstated by [r/(r-t_ox)]^2 = 7.0 % at r = 15 um, t_ox = 0.5 um. R_field is UNAFFECTED under minimum-capability allocation because the cross-section cancels, but the per-via current, the copper fraction and every derived thermal and mechanical effective property are wrong -- and Part 21 shows the liner fraction t_ox/r is what makes a fine-pitch field thermally worse in plane at equal copper.
- *Fix:* TSVGeometry carries t_liner and uses r_cu = r - t_liner for all conducting areas.
- *Status:* **CONFIRMED, MODEL REPLACED**

#### DEFECT #50 — THE CONVERTER AREA MODEL SILENTLY ASSUMES FOUR-LAYER VERTICAL STACKING, AND SAYS THE OPPOSITE

Scalable_Integrated_VR/src/HVR_FULL_OPT_EPC_V2.py::_compute_area returns max(N*fp_hs, K*fp_ls,
K*fp_ind, (N-1)*fp_cap). Its docstring says 'Total estimated component footprint' and the file
header claims the function was 'fixed: area = SUM of all component footprints (not max)'. It is
a max. The sibling implementation in HVR_FULL_OPT_sizing.py is honest about it: 'Vertical
stacking model: total footprint is the max across layers'.

- *Detected by:* Phase 0M Part 14
- *Impact:* The reported 5.61 mm2 per VR cell is a PER-LAYER footprint. The summed component footprint of the compiled 1-kW cell is 18.01 mm2, 3.21x larger. Component-level z partitioning is therefore ALREADY assumed -- by the area model and by nothing else. Nothing checks that the four layers exist in a given architecture, and a single-level VR misses the 500 mm2 die shadow by 1.76x.
- *Fix:* configs/phase0m/component_partition_templates.yaml makes the partition explicit and checks each template for height, per-level area, array footprint against the die shadow, voltage-domain mixing and level crossings.
- *Status:* **CONFIRMED, DOCUMENTED, UPSTREAM NOT EDITED (separate repository)**

#### DEFECT #51 — INTRA-CONVERTER ROUTING IS ABSENT FROM EVERY LOSS TERM

The framework models VR-to-package and package-to-POL routing. It models no metal between the
converter's own components. The upstream loss model contains R_DS(on), the inductor DCR, the
capacitor ESR and the switching losses, and no metallization at all.

- *Detected by:* Phase 0M Part 10
- *Impact:* 4.06 to 39.31 W system-wide, 0.41 to 3.93 % of the load, against a converter loss of 125.26 W. Common-mode across Z1, Z2 and Z4, so it does not reorder them, but it is not small. It also exposes a feasibility failure the framework could not see: the VR output plane needs 8.6x the available tile width to stay inside the sourced copper current-density envelope.
- *Fix:* scripts/phase0m/routing.py models it at R0/R1/R2 fidelity.
- *Status:* **CLOSED IN PHASE 0M-R. Status at discovery (Phase 0M): CONFIRMED, MODEL BUILT, NOT YET WIRED INTO THE PRODUCTION LOSS TOTAL. Superseded by Phase 0M-R, which put intra-VR routing into the production loss ledger as P_intraVR_metal and P_intraVR_vertical, template-aware.**

#### DEFECT #52 — THE CALIBRATED COOLING BOUNDARY IS INCONSISTENT WITH THE SOURCE'S OWN FLOW RATE BY A FACTOR OF 16.8

h_top = 166 000 W/m2K was inverse-calibrated to reach 84 C. Derived from geometry and flow, no
laminar microchannel architecture reaches it: the best laminar case gets 0.70x and reaching the
calibrated value appeared to need 50 g/s in the transitional regime, 74 W of pumping and 1.46
MPa -- three figures WITHDRAWN in Phase 0M-R2 and retained here only as the status at discovery.
Withdrawn because: the 50 g/s point sits at Re = 2342, between the laminar ceiling of 2300 and
Gnielinski's floor of 3000, where no validated correlation exists. What survives is the
qualitative finding that no laminar microchannel architecture reaches the calibrated value.
Separately, at the source's stated 1.6 g/s the coolant temperature rise for 1125 W of heat is
168 K, which single-phase water cannot do; 26.9 g/s is needed for a 10 K rise.

- *Detected by:* Phase 0M Parts 23-25
- *Impact:* The Robin boundary absorbs a caloric resistance that DOMINATES the thermal path at low flow and presents it as a surface property. It charges no pumping power -- 7.4 % of the load at the calibrated operating point. And because its sink is a single temperature it cannot produce a streamwise gradient: imposing the real coolant rise moves the die warpage by up to 8.19 % and T_max by 11.3 K.
- *Fix:* scripts/phase0m/cooling.py derives h from channel geometry and flow with source-backed correlations and charges the pressure drop and pumping power.
- *Status:* **CLOSED IN PHASE 0M-R. Status at discovery (Phase 0M): CONFIRMED, MODEL BUILT, NOT YET ADOPTED BY THE ETM LOOP. Superseded by Phase 0M-R, which placed the physical microchannel cooler in the production ETM loop. The correlation-domain question this row raises about the 50 g/s point is itself re-audited in Phase 0M-R2.**

#### DEFECT #53 — THE CURRENT-STATUS GENERATOR PRINTED A SUPERSEDED PHASE'S BASIS UNDER THE CURRENT PHASE'S VERDICT HEADING

`verdict.basis` was written at Phase 0H and never phase-scoped, so every later phase printed six
Phase-0H bullets beneath its own verdict heading while the same report's Executive Summary said
the opposite. Cross-report consistency was 25/25 throughout, because both reports were generated
from the same stale field and therefore agreed with each other.

- *Detected by:* Phase 0M-R Section 2
- *Impact:* Eight phases of reports carried a basis that did not belong to their verdict. Agreement between two reports generated from one stale source is not evidence.
- *Fix:* scripts/phase0g/generate_status_sections.py scopes the key as `basis_<phase>` with the unscoped key as a fallback only for the phase that wrote it; scripts/phase0mr/state_contract.py owns the authoritative field set.
- *Status:* **CLOSED IN PHASE 0M-R. Registered retroactively in Phase 0M-R2: Phase 0M-R documented this defect in results/phase0mr/DEFECT53_REPORT_STATE_AUDIT.md and referenced it in three superseded notes, but never added it as a numbered row, so the defect register itself stopped at 52 while the prose spoke of #53.**

#### DEFECT #55 — THE TSV-FIELD MATERIAL OVERRIDE WAS KEYED ON IN-PLANE FOOTPRINT, SO THE PCB, THE BGA FIELD AND THE BACKSIDE CONVERTER WERE MODELLED AS A COPPER/SILICON COMPOSITE

etm.mesh decided which layers CONTAIN the TSV field from the same `footprint` field that says
how far a layer extends IN PLANE. Every assembly layer added below z = 0 in Phase 0G -- the PCB,
the BGA field, and for ARCH_Z2 the backside converter -- spans the substrate extent and
therefore had its material overwritten with `tsv_homog` inside every tile.

- *Detected by:* Phase 0M-R2 Section 2, while building the ARCH_Z4 power die
- *Impact:* 522 to 859 mm3 of misassigned volume against 20 to 77 mm3 of real via field, and the ratio is architecture-dependent (25.7x for Z1, 11.2x for Z2, 6.8x for Z4), so it did not cancel in the comparison. Where FR4 belongs the model had k too high by 530x, E by 6.3x and CTE too low by 3.4x -- in precisely the layers that set package warpage and corner-joint shear, the deciding metric. Correcting it moved Z1 die warpage from 25.37 to 44.50 um (+75 %) and the Z1 corner driver from 4.2803 to 4.9803 um (+16.4 %), and moved the Z1/Z2 driver ratio from 1.2552 to 1.1942.
- *Fix:* etm.mesh.Layer gains an explicit `tsv_host` flag. `footprint` and `tsv_host` are now separate questions, and only layers the field actually passes through carry it. Negative-tested in tests/phase0mr2/test_geometry_and_cooling.py.
- *Status:* **CONFIRMED AND CLOSED IN PHASE 0M-R2**

#### DEFECT #54 — PHASE-0M-R PRODUCTION STATE DID NOT PROPAGATE THROUGH ALL CURRENT-FACING REPORT SECTIONS, AND THE CHECKER COULD NOT SEE IT

The Phase-0M-R cross-report checker matched each report as ONE FLAT STRING. A REQUIRED phrase
found anywhere satisfied the check for the whole document, so `microchannel` occurring in the
Phase-0M-R chapter passed the cooling check while the Validation Status block three thousand
lines earlier still described the frozen inverse-calibrated Robin boundary. The checker also had
no way to detect an OMISSION: a current-facing section that never mentions a production model
cannot be caught by a forbidden-phrase list. Two further gaps: its FORBIDDEN patterns were
paraphrases rather than the report's real sentences, and its chapter- supersession vocabulary
knew `superseded by` and `extended by` but not `rescoped by`.

- *Detected by:* Phase 0M-R2 Section 1
- *Impact:* SEVENTEEN stale current-facing findings across EIGHT claims survived a green 46/46 cross-report run and a `0 stale current-facing claims` assertion: the gate count stood at seventeen after nineteen gates; Phase 0M was still labelled `current authoritative` after Phase 0M-R; the Executive Summary's next work was the pre-0M-R material-characterisation plan; Electrical Model Validation said no current-crowding correction was applied; Thermal Model Validation described only the retired Robin boundary; defects 51 and 52 read as live; the Executive Summary said the architectures do not differ in temperature; and the document carried a date nine days older than the phases inside it.
- *Fix:* configs/phase0mr2/current_state_claims.yaml gives every claim a SECTION SCOPE, and scripts/phase0mr2/claim_propagation.py checks each named section for the current wording and for un-qualified historical wording. The gate count is DERIVED from meta.gates rather than typed. Every guard is negative-tested against the verbatim stale sentence recovered from the delivered report.
- *Status:* **CONFIRMED AND CLOSED IN PHASE 0M-R2**

#### DEFECT #56 — SECTION-SCOPED CLAIM PROPAGATION STILL MISSED CROSS-FIELD SEMANTIC CONTRADICTIONS AND STRUCTURAL DEFECTS

Phase 0M-R2 fixed DEFECT #54 by making the checker SECTION-SCOPED, which removed the flat-string
failure. The checker remained CONTRACT-DRIVEN: it could only find a contradiction for a claim
somebody had already entered in its list. Two further classes of defect are invisible to any
such list. (1) CROSS-FIELD contradictions, where two fields are each individually well-formed
but jointly inconsistent -- an open-items entry treating the mechanical criterion as though it
were the only obstacle to G2 while the authoritative field lists THREE independent ones. (2)
STRUCTURAL defects, which are not claims at all -- one paragraph shipped FOUR times, and a
provenance row reading 'Report date 2026-09-08' beside a front matter reading 2026-09-17. A
third weakness was found while building the replacement: the retraction heuristic cleared a
forbidden sentence because an UNRELATED 'WITHDRAWN' appeared in the same paragraph, which
silently exonerated both the cooling wording and the 'measures DAMAGE' wording.

- *Detected by:* Phase 0M-R3 Section 1
- *Impact:* EIGHTEEN current-facing findings survived a report certified as having zero: a verdict bullet reading 'THE COOLING MODEL HAS A DOMAIN HOLE, AND THE PRODUCTION POINT IS NOT IN IT' immediately before a sentence saying the production point is inside the validated domain; the mechanical criterion written up as the only obstacle to G2; the FE response metric called DAMAGE while no damage law, life model or failure criterion is closed; four identical copies of one paragraph; two different report dates; and a provenance table claiming 'PALACE (built, functional)' for a solver that is not on this system at all.
- *Fix:* configs/phase0mr3/semantic_contract.yaml adds CROSS_FIELD invariants and STRUCTURAL rules alongside the per-claim list, and marks self-contradictory claims as not exonerable by a neighbouring retraction. scripts/phase0mr3/semantic_audit.py enforces all three families. scripts/phase0mr3/repair_report.py performs the structural repairs idempotently.
- *Status:* **CONFIRMED AND CLOSED IN PHASE 0M-R3**

#### DEFECT #57 — THE CURRENT-STATE CONTRACT REMAINED AT PHASE 0M-R2 AFTER PHASE 0M-R3 WAS DECLARED AUTHORITATIVE

Two independent representations of the current state exist. `meta.current_phase` and
`verdict.phase0mr3` drive the verdict heading and were advanced in Phase 0M-R3. The
`current_state_contract` block, owned by scripts/phase0mr/state_contract.py and rendered as the
'Current scientific status' TABLE, was not. The report therefore carried a section headed
'Current scientific status (Phase 0M-R3)' whose table said phase = 0M-R2 complete, gave the
Phase-0M-R2 verdict, said ZERO OF TWELVE REALIZABLE after a realizable pair had been found, and
listed Phase-0M-R2 next work. A third stale source, `next_gate.id`, still named two actions --
adopt the physical cooling model and put the RDL in the mechanical mesh -- that Phases 0M-R and
0M-R2 had already completed. A fourth: `current_G2_status` said TWO independent blockers where
the authoritative field lists THREE. A FIFTH was found while re-running the suite:
configs/phase0mr2/current_state_claims.yaml carries its own copy of current state -- meta.gates,
meta.current_authoritative_phase, and the gate_count and phase_authority claim wordings -- and
none had been advanced past 0M-R3 either, so the Phase-0M-R2 checker was validating the report
against a superseded contract. The number of falsification gates alone was written out in FOUR
places. A separate latent bug hid every one of them: the regex that reads the count word cannot
capture a hyphenated number word, so at the twenty-first gate it read 'Twenty-one' as 'one' and
reported a correct report as wrong. It had been silently correct for gates 17 to 20 because
those words have no hyphen.

- *Detected by:* Phase 0M-R3A Section 1
- *Impact:* The single most prominent current-state table in the report was a full phase behind, and disagreed with the verdict printed immediately above it. The Phase 0M-R3 semantic checker did not catch it because its contract listed claims by SENTENCE, and these fields were never entered as claims.
- *Fix:* Every current_state_contract field advanced to Phase 0M-R3A; next_gate rewritten from the open-items ledger; a structural rule added that fails when two current next-work sources disagree or when any current-state field names a superseded phase.
- *Status:* **CONFIRMED AND CLOSED IN PHASE 0M-R3A**

#### DEFECT #58 — THE INTRA-VR ROUTING REPAIR BORROWED THE THROUGH-SILICON VIA PROCESS RANGE FOR A PACKAGE-SUBSTRATE INTERCONNECT

Phase 0M-R3 repaired the binding route `ls_to_L` by raising its via radius from 15 to 20 um and
justified 20 um as inside `design_variables.tsv.radius_m = {lo 2.5, nominal 15, hi 50} um`. That
range governs THROUGH-SILICON VIAS. `ls_to_L` connects the low-side GaN switch node on tier 1 to
the inductor terminal on tier 3, a 673 um vertical span BETWEEN EMBEDDED-COMPONENT LAYERS inside
the converter cell. The framework's own source picture separates the two structures explicitly:
components are 'embedded within the subsequent substrate power layers' while 'the TSV field runs
beneath it from the substrate underside', spanning 74 um for ARCH_Z1. They are different
technologies in different regions of the stack.

- *Detected by:* Phase 0M-R3A Section 4
- *Impact:* Phase 0M-R3's claim that the realizability repair used 'only existing/sourced technologies' does not hold. The design space contains no geometry rule for a stacked via through substrate power layers: it has tsv.* (through-silicon), rdl.* (trace width and space only), and bump.* (bumps, not vias through dielectric). The repair is a self-consistent design point in an UNSOURCED process window. It is not shown to be wrong, and it is not shown to be manufacturable. Package clearances are therefore NO LONGER the sole reason the repaired pair falls short of PROVEN_REALIZABLE.
- *Fix:* Provenance chain recorded in results/phase0mr3a/LS_TO_L_INTERCONNECT_AUDIT.md and interconnect_technology_provenance.csv. The wording 'source-backed repair' is withdrawn and replaced by 'design point in an unsourced process window'. The realizability verdict is reopened accordingly.
- *Status:* **CONFIRMED AND CLOSED IN PHASE 0M-R3A**

#### DEFECT #59 — THE Z2 TSV PROCESS-MARGIN REPAIR STATED THE DIRECTION OF THE VIA-COUNT CHANGE BACKWARDS

Phase 0M-R3 wrote that moving ARCH_Z2 from a 30 um to a 34 um TSV restores M_AR = 1.089 'at the
cost of 22.8 % more vias'. Under minimum-capability provisioning n_required = ceil(I / (J_design
* A_cu)) scales as 1/A_cu, so a larger via needs FEWER of them: 15 140 -> 11 692, which is 22.8
% FEWER. The magnitude was right and the sign was inverted, and the change was labelled a cost
when it is a reduction. The underlying source of the error is that 'via count' was used without
saying WHICH count.

- *Detected by:* Phase 0M-R3A Section 6
- *Impact:* A reader would conclude the margin repair carries a routing-density penalty it does not have. A second error was found in the same sweep: Phase 0M-R3 reported 34 um as the smallest diameter with positive margin, but its grid was 30/34/40/50/60 and never evaluated 32 um, which passes the same modest bound at M_AR = 1.067.
- *Fix:* results/phase0mr3a/Z2_TSV_PROCESS_MARGIN_REAUDIT.md separates n_required, n_allocated, n_available and total Cu area, verifies n_required against an independent hand calculation at every diameter, and adds 32 and 36 um to the grid. All report text corrected.
- *Status:* **CONFIRMED AND CLOSED IN PHASE 0M-R3A**

### Next gate

**POST-0M-R3A -- (1) source a process rule for the intra-converter vertical interconnect; (2)
source the three package clearances; (3) close the ARCH_Z2 TSV process margin at 32 um; (4)
high-stress SAC305 characterisation; (5) canonical conjugate CFD. Adopting physical cooling and
putting the RDL into the production thermal model are COMPLETE and are not future work..** Phase
0M found five first-order physical models that exist as validated SCREENING tools and do not
drive the production path: intra-VR routing, geometry-specific transition resistance, physical
cooling, RDL thermal anisotropy and component-level z partitioning. Phase 0M-R wires the ones
with sufficient evidence into production and re-asks which Phase-0M conclusions survive. In
parallel, and NOT blocking it, high-stress SAC305 material characterisation remains the dominant
scientific blocker.

**Explicitly not next:** the global ETM optimizer.


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
