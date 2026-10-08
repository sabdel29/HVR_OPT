---
title: "ETM-DVPD Framework --- Current-State Technical Audit"
subtitle: "A self-contained description of the framework as it exists after Phase 0M-R3A"
date: "2026-09-21"
geometry: margin=2.2cm
fontsize: 10pt
colorlinks: true
toc: true
toc-depth: 2
---

# Preface --- what this document is, and what it is not

This is a description of a modelling framework **as it stands today**. It is written for a technical auditor who understands power delivery and packaging and who has never seen this repository. It does not assume, and does not require, any knowledge of the development history.

Three things follow from that.

* **Every claim about the present is generated** from a single machine-readable contract, `results/CURRENT_SCIENTIFIC_STATUS.yaml::current_state_contract`. A sentence in this document that contradicts that contract is a build failure, not a difference of emphasis. That mechanism exists because the previous version of this report was internally consistent with its sibling report and consistently stale relative to the actual science --- see Section 22.
* **Missing physics is listed, not hidden.** Sections 20 and 21 say what the framework cannot do and which claims are therefore unsafe.
* **Audited is not implemented.** Where a model was built and measured but does not drive the production path, the text says so at that point, every time.

The companion document `ETM_DVPD_FULL_TECHNICAL_REPORT.pdf` is the chronological record of how the framework reached this state, including superseded results. Nothing here depends on it.

\newpage

# 1. The problem the framework solves

A 1 kW compute die drawing **1000 A at 1 V** cannot be fed laterally. The IR drop and the $I^2R$ loss of a 1 V rail crossing even a few millimetres of package metal are comparable with the load itself. **Distributed vertical power delivery (DVPD)** answers that by converting 48 V down to 1 V immediately above, below or inside the package, so that the high-current rail travels micrometres rather than millimetres.

That choice is usually made on electrical and thermal grounds. This framework exists to ask a third question:

> **Does package thermo-mechanics change which DVPD architecture you would choose, or is it only a downstream sign-off check?**

Answering it requires a chain that runs from an architecture choice all the way to a local solder-fatigue response, with every link converged and every parameter traced. The framework is that chain. It is a **falsification framework**, not a design tool: each stage was built so that a negative result would stop the work rather than be absorbed.

**The headline answer today.** Mechanics responds strongly and measurably to the architecture, the ordering of the architectures is robust, and there is still no admissible mechanical inequality that would turn that response into a constraint. The framework therefore RANKS architectures and does not yet CONSTRAIN them.

## 1.1 The current state, in one table

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


\newpage

| Report generated | 2026-09-21 |
| Repository baseline | 2026-09-08 |
| Phase completed | 0M-R3A, 2026-09-21 |

**Method.** Twenty-one sequential falsification gates (0B, 0C, 0D, 0D-R, 0E, 0F, 0G, 0H, 0I, 0I-R, 0J, 0J-R, 0K, 0K-R, 0L, 0L-R, 0M, 0M-R, 0M-R2, 0M-R3, 0M-R3A), each designed so that a negative result would stop the project rather than be absorbed.

## 1.2 What Phase 0M-R3A changed

A narrow closure gate on four issues left open by Phase 0M-R3. Three were confirmed as defects; one claim was found to have the wrong sign.

| question | answer |
|---|---|
| Was the 15 -> 20 um routing repair source-backed? | **No --- DEFECT #58.** The range quoted to license it, `tsv.radius_m`, governs THROUGH-SILICON vias. `ls_to_L` is a **673 um** stacked via between embedded-component layers inside the converter cell, where the Z1 TSV field spans 74 um. The design space holds `tsv.*`, `rdl.*` and `bump.*` and has no entry for this structure. The repair is a design point in an unsourced process window |
| Is the repair arithmetic right? | **Yes.** An independent implementation sharing no code with production reproduces the routing ratio exactly at 5 of 5 radii --- 1.2360 at r = 15 um, 0.9344 at r = 20 um. The numbers were right; only their provenance was not |
| Does a 34 um TSV cost 22.8 % more vias? | **No --- DEFECT #59, the sign was backwards.** n_required scales as 1/A_cu, so 30 -> 34 um gives -22.8 %: 15140 -> 11692. It is a reduction, not a cost. The sweep also skipped **32 um**, which passes the same bound at M_AR = 1.067 |
| Was the current-state table current? | **No --- DEFECT #57.** A section headed "Current scientific status (Phase 0M-R3)" carried a table saying phase = 0M-R2 complete, the 0M-R2 verdict, ZERO OF TWELVE REALIZABLE, and two already-completed actions listed as future work |

Nothing was re-solved. The 30 -> 34 um change moves every E/T/M property by under 0.1 %, because under minimum-capability provisioning the copper fraction is `I / (J_design * A_field)`, in which the radius cancels.

**Verdict B --- the Z1/Z2 ordering survives, but the intra-VR via technology remains unsourced.** Phase 0M-R3's verdict rested on package clearances being the sole remaining blocker. DEFECT #58 adds a second, independent unsourced manufacturing assumption, so that premise no longer holds.

\newpage

## 1.3 Superseded Phase-0M-R3 summary

| question | answer |
|---|---|
| Is there a buildable Z1 and a buildable Z2 in the existing library? | **Yes, both CONDITIONAL_REALIZABLE**, passing every condition of a contract frozen before the search, at all 27 corners of the bounded clearance envelope. Neither is PROVEN_REALIZABLE: three package clearances are unsourced |
| What repair was needed? | **One.** The intra-VR via radius 15 -> 20 um at the framework's own legal pitch. *(Phase 0M-R3A withdrew "inside the sourced range": that range governs through-silicon vias, DEFECT #58.)* The binding net was `ls_to_L`, a vertical via stack at 1.236x the vias available |
| Does the ordering survive? | **Yes, essentially unchanged.** D_driver 1.1942 -> 1.1943, +0.009 % |
| Does the 30 um TSV have process margin? | **No.** ARCH_Z2 sits at M_AR = 1.000 and fails a modest tolerance bound. 34 um restores 1.089. *(Phase 0M-R3A: that is 22.8 % FEWER vias, not more, and 32 um already passes at M_AR = 1.067; DEFECT #59.)* Every E/T/M property moves by <= 0.02 % |
| Was a transitional cooling correlation found? | **No.** 2300 < Re < 3000 is permanently OUT_OF_MODEL_DOMAIN and the design space is capped at Re <= 2300 |
| Was the previous zero-stale certificate right? | **No.** 18 findings; DEFECT #56 |

\newpage

## 1.4 Superseded Phase-0M-R2 summary

This gate asked five falsification questions. Four returned a defect.

| question | answer |
|---|---|
| Was the previous phase's "0 stale current-facing claims" true? | **No.** 17 stale findings across 8 claims, behind a green 46/46 cross-report run. DEFECT #54: the checker matched each report as one flat string and could not detect an omission at all |
| Is ARCH_Z4 a real power die? | **Now yes, still conditional.** 1921 um of sourced components replace a heat source in a 10 um underfill layer. Its construction is unsourced, and Z4 takes first or second place depending on which construction is real |
| Does each TSV span what the architecture says? | **Now yes.** Three domains had been using 300, 280 and a hard-coded ladder for the same via. No architecture traverses 1300 um; ARCH_Z1 traverses 74 um. Three of four sit exactly on the 10:1 limit |
| Is the cooler inside its correlation domain? | **At 27 g/s yes, at 50 g/s no.** Re = 2342 lies between the laminar ceiling of 2300 and Gnielinski's floor of 3000. h = 166 000 W/m2K, 1.46 MPa and 74 W are withdrawn |
| Does the RDL thermal tensor change the answer? | **It changes absolute temperature by 7 K and the ordering by 0.105 %.** Promoted to the production default for the absolute numbers |

A sixth finding came out of the second: **DEFECT #55**, the TSV-field material override was keyed on in-plane footprint, so the PCB, the BGA field and ARCH_Z2's backside converter were all modelled as a copper/silicon composite -- k too high by 530x, E by 6.3x, CTE too low by 3.4x, in the layers that set package warpage. It was architecture-dependent and did not cancel: correcting it moved the Z1/Z2 driver ratio from 1.2552 to 1.1942.

**The deciding ordering survived all of it.** driver_Z1 / driver_Z2 = 1.1942, ARCH_Z2 better. **Nothing is buildable:** 0 of 12 template-architecture combinations are realizable at any of 27 clearance-bound corners, and area, routing and current density block more of them than the clearances do.

\newpage

# 2. The physical system and the architectures

| quantity | value | provenance |
|---|---|---|
| load | 1000 W at 1 V, 1000 A | reference system (June-2026) |
| input rail | 48 V | reference system |
| compute die | 22.36 mm square, 500 mm2 | reference system |
| voltage regulators | 49 cells, 20.41 A each | Phase-0F 1 kW design point |
| converter topology | 3:1 switched capacitor into a 3-phase buck (`N3K3KA2`) | compiled by the upstream optimizer |
| switching frequency | 805.17 kHz | compiled |
| devices | EPC2014C high side, EPC2057 low side | EPC product table |
| inductor | 250 nH, 1.6 mOhm DCR, 500 um tall | Rasheedi, TCPMT 2026 |
| capacitor | 10 uF, 2.5 mOhm ESR | Murata GCM21 datasheet |

Four vertical-integration architectures are compared. They differ in **where the conversion happens**, which decides **which rail crosses the substrate** --- and that single fact dominates the electrical comparison.

| architecture | where the converter sits | rail on the TSVs | substrate |
|---|---|---|---|
| **Z1 EMBEDDED** | inside the substrate power layers | 48 V, 23.4 A | 1.30 mm (component-height limited) |
| **Z2 BACKSIDE** | on the substrate underside, as chiplets | **1 V, 1000 A** | 0.30 mm |
| **Z4 POWER DIE** | a dedicated die between substrate and compute die | 48 V, 23.4 A | 0.30 mm |
| **Z5 2.5D LATERAL** | beside the die on a common interposer | 48 V | 0.30 mm |

Z2 puts 1000 A on the TSV field where Z1 and Z4 put 23.4 A: a factor of **1822 in $I^2$** at the same geometry. Z5 is the control --- it is the architecture DVPD exists to beat.

![Architecture cross-sections](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0m/FIG_0M_E_partition_templates.png)

*Component-partition templates and whether each fits the die shadow.*

\newpage

# 3. The data flow, end to end

```
  architecture choice
        |
        v
  component partition template          which component sits on which tier
        |
        v
  converter synthesis (upstream)        devices, inductor, capacitor, f_sw, area
        |
        v
  loss ledger                           one owner per watt, system scope enforced
        |
        +--> intra-VR routing           metal BETWEEN the converter components
        +--> vertical interconnect      R_bulk + dR_transition, per class
        +--> package RDL                multilayer resistive sheet
        |
        v
  spatial heat deposition               each term into the layer it occurs in
        |                               (checked against the electrical total)
        v
  thermal solve (CalculiX)  <---->  physical cooling
        |                            h(x) from channel geometry and flow
        |                            T_fluid(x) from the heat removed upstream
        v
  temperature field T(x,y,z)
        |
        +--> back to the loss ledger    rho(T), R_DS(on)(T), DCR(T)   [FIXED POINT]
        |
        v
  structural solve (CalculiX)           global thermoelastic warpage and stress
        |
        v
  corner-joint relative displacement    the driver handed to the local model
        |
        v
  local solder submodel (CalculiX)      viscoplastic, cyclic, graded mesh
        |
        v
  per-cycle inelastic damage metric --> RELATIVE life only
```

Two loops close and one does not. **Electrical and thermal are iterated to a fixed point.** **Thermal drives mechanics one way.** Mechanics returns nothing, and Section 19 gives the measured reason.

![Production flow](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0mr/FIG_0MR_A_production_flow.png)

*Which parts of this flow were measured in Phase 0M and which now drive it.*

\newpage

# 4. Governing equations

## 4.1 Electrical

Conductor resistance, temperature dependent:

$$R = \frac{\rho(T)\,\ell}{A}, \qquad \rho(T) = \rho_{20}\left[1 + \alpha (T - 20)\right]$$

Via-field allocation and field resistance, with the count DISCRETE:

$$n_{req} = \left\lceil \frac{I}{J_{design} A_c} \right\rceil, \qquad R_{field} = \frac{R_{single}}{n_{alloc}} + \Delta R_{transition}$$

Under minimum-capability provisioning the first term collapses to
$R_{field} = \rho(T) h J_{design} / I$ and **the conductor cross-section cancels**. That is derived, verified numerically and discussed in Section 9.

Lateral distribution, solved as a PDE rather than a lumped resistance:

$$\nabla \cdot \left( \sigma_s \nabla V \right) = -J, \qquad \sigma_s = \frac{N_{layers}\, t_{Cu}\, \text{occupancy}}{\rho(T)}$$

Three-dimensional conduction, for transitions:

$$\nabla \cdot \left( \sigma \nabla V \right) = 0, \qquad \mathbf{J} = -\sigma \nabla V, \qquad P = \int \mathbf{J} \cdot \mathbf{E}\, dV$$

Converter loss --- the upstream closed form, decomposed per component and checked against its own aggregate:

$$P_{cond} = \frac{V_{out}}{V_{in}} I_{rms}^2 \left[ R_{DS,hs} + 2\left(1-\tfrac{1}{N}\right) R_{C,ESR} + \left( \frac{V_{in}}{N^2 V_{out}}(R_{L} + R_{DS,ls}) + \frac{2 R_{DS,ls}}{N} \right) \Sigma B^2 - \text{corr} \right]$$

## 4.2 Thermal

$$\nabla \cdot \left( \mathbf{k}_{eff} \nabla T \right) + \dot{q} = 0$$

with an anisotropic $\mathbf{k}_{eff}$ for every heterogeneous layer, and the cooled boundary

$$-\mathbf{k}\nabla T \cdot \mathbf{n} = h(x)\left[T_s(x) - T_f(x)\right], \qquad T_f(x) = T_{in} + \frac{Q(0 \to x)}{\dot{m} c_p}$$

$h$ from a Nusselt correlation, $T_f$ from the heat actually removed upstream. Both are iterated with the wall temperature to a fixed point.

## 4.3 Mechanical

Global, linear thermoelastic:

$$\nabla \cdot \boldsymbol{\sigma} = 0, \qquad \boldsymbol{\sigma} = \mathbf{C} : \left( \boldsymbol{\varepsilon} - \boldsymbol{\alpha}\,\Delta T \right)$$

Local solder, viscoplastic. **What CalculiX actually integrates in a `*VISCO` step is an OVERSTRESS law**, and the distinction matters:

$$\dot{\varepsilon}_{in} = A(T)\left( \sigma_{vm} - \sigma_y(\bar{\varepsilon}_{in}) \right)^{n(T)} \ \text{for}\ \sigma_{vm} > \sigma_y, \qquad \dot{\varepsilon}_{in} = 0 \ \text{otherwise}$$

There is **no rate-independent plastic strain** in such a step, and $A$, $n$ and $\sigma_y$ are interpolated **linearly** between card rows by the solver --- not by an Arrhenius law. Any Arrhenius relation exists only in how the rows were generated.

A separate rate-independent plastic branch **is not presently justified if a validated UNIFIED viscoplastic law such as Anand is used**, because a unified law already carries the rate-independent response inside its single inelastic flow rule. That is a statement about unified laws, not a general claim about plasticity.

**The variable mismatch, stated plainly.** The creep card in this repository was fitted against **total applied stress** $\sigma_{vm}$ in the source experiments, while the solver drives it with the **overstress** $\sigma_{vm} - \sigma_y$. The two agree only where $\sigma_y$ is small against $\sigma_{vm}$. This is not a coding error and cannot be fixed by refitting the same data; it is why the constitutive status is CONDITIONAL rather than closed, and it is the dominant open blocker on every absolute reliability number in this framework.

Damage metric, per stabilised cycle:

$$D = \Delta \text{PEEQ}\big|_{cycle}, \qquad W_{in} = \oint \boldsymbol{\sigma} : d\boldsymbol{\varepsilon}_{in}, \qquad \boldsymbol{\varepsilon}_{in} = \mathbf{ME} - \mathbf{C}^{-1}(T):\boldsymbol{\sigma}$$

`ME` is the solver's own mechanical strain. Reconstructing the inelastic strain from it, rather than from a separately parsed temperature, removes an entire class of error (Section 22, defect 46).

\newpage

# 5. Solvers, and what each is used for

| solver | version | used for | why this one |
|---|---|---|---|
| **CalculiX** | 2.23 | thermal conduction, global thermoelasticity, local nonlinear solder | the primary physics solver. Practical ceiling about 40 000 elements for this nonlinear transient class |
| **MOOSE** `heat_transfer` | 09515f92aa | independent cross-check on scalar conduction | a different mesher, element formulation, quadrature and linear solver. `div(k grad T)` and `div(sigma grad V)` are the same operator |
| **finite-volume solver** | this repository | 3-D DC conduction for transitions | no DC conduction solver is installed. Cell-centred FV with harmonic-mean face conductivities is exactly conservative across a nine-decade conductivity jump |
| **analytic Python** | -- | via allocation, sheet conduction, effective media, routing, cooling correlations | cheap enough to sweep, and each form is checked against a numerical solve |
| **HFSS** | AEDT 2026 R1 | AC / skin validation only | licensed and available. It is a full-wave solver and **cannot pose a pure conduction problem with no return path**, so it is NOT used for the DC transition resistance |
| **Icepak** | AEDT 2026 R1 | nothing, currently | licensed and available. An earlier attempt returned a solver clamp of exactly 5000 K on every object and that result stays discarded. **No Icepak validation is claimed** |
| **Q3D** | -- | nothing | **not licensed**. Checked against the licence manager, not assumed |
| Elmer, GetDP, Palace, OpenFOAM | -- | nothing | **not installed**. Palace's electrostatic mode solves a permittivity problem and would not be a DC conduction solver in any case |

## 5.1 What the finite-volume solver was verified against

| case | result |
|---|---|
| uniform bar, analytic rho L / A | **exact at every mesh** |
| circular contact on a half-space, analytic rho/(4a) | +0.9 % at 6 cells per contact radius |
| five transition geometries against MOOSE | **0.25 to 0.73 %, 5 of 5 ACCEPTED** |

Both terminals are equipotential Dirichlet planes in both codes, the dielectric is present in both, and each run reports its discretised block volumes so the geometry match is proved rather than assumed.

\newpage

# 6. How to read every number in this framework

Each quantity carries one of these classes, and they are not interchangeable:

| class | meaning |
|---|---|
| **SOURCE_BACKED** | taken from a named primary source with its conditions |
| **ANALYTICALLY_DERIVED** | a closed form, verified numerically |
| **NUMERICALLY_VALIDATED** | solved, mesh-converged, checked against a closed form |
| **INDEPENDENTLY_CROSS_VALIDATED** | reproduced by a second, independent solver |
| **CALIBRATED** | fitted to reproduce a target. Not transferable |
| **HOMOGENIZED** | an effective property of a heterogeneous layer, with its RVE error |
| **CONDITIONAL** | true only under a stated open input, and the input is named |
| **OPEN** | not determined. Never silently defaulted |

The full ledger is `results/phase0mr/uncertainty_ledger.csv`. Its headline:

| class | count |
|---|---|
| INDEPENDENTLY_CROSS_VALIDATED | 1 |
| NUMERICALLY_VALIDATED | 4 |
| ANALYTICALLY_DERIVED | 2 |
| SOURCE_BACKED | 1 |
| CONDITIONAL | 1 |
| **OPEN** | **5** |

**Uncertainties are never RMS-summed across common-mode terms.** For an architecture RATIO the cancellation is TESTED and the tested residual is what is quoted.

\newpage

# 7. Input parameters and their provenance

| parameter | value | class | source |
|---|---|---|---|
| rho_Cu at 20 C | 17.0 nOhm.m | SOURCE_BACKED | June-2026 Table III |
| rho_solder at 20 C | 130 nOhm.m | SOURCE_BACKED | June-2026 |
| alpha_Cu | 3.93e-3 /K | ASSUMPTION | bulk Cu TCR |
| TSV diameter / pitch / height | 30 / 60 / 300 um | SOURCE_BACKED | June-2026 Table III |
| TSV liner thickness | 0.5 um | ASSUMPTION | typical SiO2 liner; swept |
| TSV aspect-ratio limit | 10:1 | DERIVED_FROM_SOURCE | the source demonstrates d = 30 um at h = 300 um |
| keep-out ratio | swept 0 to 1.5 | ASSUMPTION | no source; never fixed |
| RDL stack | t = 10 um, W/S = 10/2, 2 VDD + 2 GND | SOURCE_BACKED | ECTC-2024 Table I |
| J_design | 1.0e8 A/m2 | DERIVED_FROM_SOURCE | June-2026 provisioning |
| J_process_max | 4.0e8 A/m2 | DERIVED_FROM_SOURCE | ECTC-2024, the most aggressive available |
| **J_reliability_allow** | -- | **OPEN** | no primary EM study with its T, lifetime and geometry was retrievable |
| GaN heights | 685 / 606 um | SOURCE_BACKED | EPC2212 / EPC2090 datasheets |
| inductor | 250 nH, 1.6 mOhm, 500 um | SOURCE_BACKED | Rasheedi, TCPMT 2026 |
| MLCC height | 100 um nominal, 250 um upper | PARTIAL | manufacturer page unreachable; envelope carried |
| solder E, nu, CTE | 45 GPa, 0.36, 21.5 ppm/K | ASSUMPTION | commonly quoted band |
| **solder creep A(T), n(T)** | 19 points over 7.51-15.92 MPa | **CONDITIONAL** | **Sn3.9Ag0.6Cu, NOT SAC305** |
| underfill E / CTE | 8 GPa / 30 ppm/K | PROVISIONAL | unsourced; sensitivity run |
| board | 20 GPa, 17 ppm/K, 1.6 mm FR4 | ASSUMPTION | typical laminate |
| coolant | water, 27 g/s, 25 C inlet | DESIGN VARIABLE | derived, not calibrated |
| **required life** | -- | **OPEN** | no field or product requirement exists |
| **mechanical allowable** | -- | **OPEN** | nine candidates tested, none admissible |

\newpage

# 8. Interconnect geometry

**No resistance is a primitive.** Every interconnect quantity is classified as exactly one of MATERIAL, PROCESS, DESIGN or DERIVED, and the classifier raises on anything unclassified.

| class | examples |
|---|---|
| MATERIAL | rho_Cu(T), alpha, k_Cu, k_Si, k_SiO2 |
| PROCESS | minimum pitch, liner thickness, aspect-ratio limit, keep-out ratio, J_process_max |
| DESIGN | via radius, pitch, height, allocated count, RDL thickness / width / spacing / layer count, bump diameter / height / pitch, pad size |
| DERIVED | conductor area, single-via R, per-via current limit, available and required counts, field R, Joule loss, copper fraction, effective k and CTE, transition dR |

Three quantities that used to be primitives and are now derived:

1. the per-via current limit, which was entered in amperes and is now `J_design * A_c`;
2. the current-crowding correction, which was one global constant and is now solved per class and per geometry;
3. the TSV liner, which was absent and now sets the conducting radius.

## 8.1 Transition resistance

$$R_{total} = R_{bulk}(\text{geometry}, T) + \Delta R_{transition}(\text{class}, \text{geometry}, T)$$

`dR` is solved exactly for each production geometry by the finite-volume solver and cached against a geometry fingerprint. There is **no fitted surrogate**: a two-term logarithmic form was tried over 178 geometries and rejected at 9 to 29 % of the spread of the quantity it was fitting.

**`dR` can be negative, and that is physical, not an error.** The 1-D reference is a series of named conductors with implicit equipotential cross-sections everywhere; the 3-D solve constrains only the two terminal planes. A generous landing pad genuinely replaces part of a narrow trace. `dR` is therefore reported as a difference against a stated reference and never as an "excess".

| class | R_1D | dR | R_3D / R_1D |
|---|---|---|---|
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| bga | 2.5253 mOhm | -0.3255 mOhm | **0.8711** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| microbump | 36.8657 mOhm | -2.2667 mOhm | **0.9385** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |
| tsv | 22.2485 mOhm | -2.3440 mOhm | **0.8946** |

Against the retired global constant of **1.326**, applied identically to all four classes.

![Transition decomposition](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0mr/FIG_0MR_C_transition_decomposition.png)

## 8.2 The TSV radius result, stated precisely

Under the minimum-capability allocation this framework uses, `R_field = rho h J_design / I` and **the conductor cross-section cancels identically** --- not merely the radius. The copper fraction `I / (J_design A_field)` is likewise independent of radius, so the effective conductivity, modulus and CTE do not move either.

The permitted conclusion is therefore **not** "TSV radius is irrelevant". It is: *the TSV cross-section is not an independent field-loss lever under minimum-capability provisioning when `J_design` is geometry-independent.* Radius remains decisive for **feasibility**:

| via height | feasible radii at a 10:1 aspect limit |
|---|---|
| 100 um | 7.5 to 50 um |
| 300 um | **15 to 50 um** --- and 15 um is the reference radius, so the source geometry sits ON the limit |
| 1300 um | **none in the swept range**; the rule `r >= h/20` demands r >= 65 um |

![TSV feasibility](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0mr/FIG_0MR_D_tsv_feasibility.png)

\newpage

# 9. Converter component-level partitioning

The converter is nine components per cell: 3 high-side GaN, 3 low-side GaN, 2 flying capacitors, 3 inductors and an output capacitor. Their summed footprint is **18.01 mm2** against a 500 mm2 die shared by 49 cells --- **10.20 mm2 per cell**. A single-level VR therefore misses the die shadow by **1.76x**, and vertical partitioning is a precondition rather than an optimization.

Each template is checked on six independent questions, not on area alone:

| template | tiers | charged height / available | area | height | routing | thermal | clearance |
|---|---|---|---|---|---|---|---|
| T1_EMBEDDED_4LAYER in Z1_EMBEDDED | 4 | 1226 / 1250 um | True | True | False | False | OPEN |
| T1_EMBEDDED_4LAYER in Z2_BACKSIDE | 4 | 1921 / 1100 um | True | False | False | True | OPEN |
| T1_EMBEDDED_4LAYER in Z4_POWER_DIE | 4 | 1921 / 1200 um | True | False | False | False | OPEN |
| T4_SPLIT_SC_BUCK in Z1_EMBEDDED | 2 | 1301 / 1250 um | False | False | True | True | OPEN |
| T4_SPLIT_SC_BUCK in Z2_BACKSIDE | 2 | 1301 / 1100 um | False | False | True | True | OPEN |
| T4_SPLIT_SC_BUCK in Z4_POWER_DIE | 2 | 1301 / 1200 um | False | False | True | True | OPEN |
| T2_BACKSIDE_CHIPLET in Z1_EMBEDDED | 3 | 1305 / 1250 um | False | False | False | True | OPEN |
| T2_BACKSIDE_CHIPLET in Z2_BACKSIDE | 3 | 1305 / 1100 um | False | False | False | True | OPEN |
| T2_BACKSIDE_CHIPLET in Z4_POWER_DIE | 3 | 1305 / 1200 um | False | False | False | True | OPEN |
| T0_SINGLE_LEVEL in Z1_EMBEDDED | 1 | 685 / 1250 um | False | True | True | True | OPEN |
| T0_SINGLE_LEVEL in Z2_BACKSIDE | 1 | 685 / 1100 um | False | True | True | True | OPEN |
| T0_SINGLE_LEVEL in Z4_POWER_DIE | 1 | 685 / 1200 um | False | True | True | True | OPEN |

**No template is fully realizable.** The closest is the embedded four-layer stack in the embedded architecture, whose charged height of 1226 um reproduces an independently derived earlier figure exactly and fits the 1250 um available. It is blocked on routing and on thermal depth.

**Three package clearances have no source** --- die-to-component gap, cavity sidewall allowance, cooled-surface standoff --- so every template carries CLEARANCE OPEN and **none may be called buildable**. Treating them as zero would convert three unknowns into a pass.

## 9.1 The intermediate rail

A partition that splits by VOLTAGE DOMAIN puts the 16 V intermediate rail across the tier boundary, carrying **1.44 A where the 1 V rail would carry 20.4 A** --- a factor of 200 in `I^2`. That is why the split SC/buck template has essentially zero vertical intra-VR loss.

![Component power path](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0mr/FIG_0MR_B_component_power_path.png)

\newpage

# 10. Intra-VR routing

**The metal between the converter's own components is now in the loss total.** Before Phase 0M-R it was absent entirely: the framework modelled VR-to-package and package-to-POL routing and nothing inside the converter.

There is no double counting, and the reason is structural rather than a comment. The upstream converter model owns every device and passive parasitic --- switch `R_DS(on)`, inductor DCR, capacitor ESR, and all switching loss --- and contains no metallization. The ledger enforces **one owner per watt**: a second writer to any term raises, and the conduction split is checked against the upstream aggregate to machine precision before a total may be produced.

| term | owner |
|---|---|
| `P_switch_hs_conduction`, `P_switch_ls_conduction` | upstream conduction formula |
| `P_inductor_DCR`, `P_cap_ESR` | upstream conduction formula |
| `P_switching_hard`, `P_gate`, `P_Coss` | upstream switching formula |
| `P_intraVR_metal`, `P_intraVR_vertical` | **this framework, new** |
| `P_TSV`, `P_bumps` | vertical tier model, `R_bulk + dR` |
| `P_pkg_RDL` | multilayer resistive sheet |

The routing model is **template-aware**: components on the same tier need a lateral run, components on different tiers need a via stack, and the via-stack height is set by the components below it. Phase 0M's claim that intra-VR routing is common-mode across architectures held only while every architecture used the same layout; measured across partition templates it varies by **7.5 %**.

\newpage

# 11. The cooling model

**The cooled boundary is derived from hardware, not calibrated to a target.**

$$-k \nabla T \cdot n = h(x)\left[T_s(x) - T_f(x)\right], \qquad T_f(x) = T_{in} + \frac{Q(0 \to x)}{\dot{m} c_p}$$

`h` comes from a Nusselt correlation for the channel geometry, corrected by fin efficiency and area amplification. `T_f` comes from the heat actually removed upstream of each face, integrated from the solved flux and iterated with the wall temperature to a fixed point. The design variables are coolant, inlet temperature, mass flow, channel width, height and pitch, base thickness and solid conductivity.

| design | m_dot | Re | regime | h_effective | coolant rise | T_j | dp | pumping |
|---|---|---|---|---|---|---|---|---|
| TOP_SI_MICROCHANNEL_27 | 27.0 g/s | 1265 | laminar | 115553 | 9.97 K | 44.5 C | 538 kPa | 14.70 W |
| TOP_SI_MICROCHANNEL_50 | 50.0 g/s | 2342 | transitional | 215115 | 5.38 K | 35.5 C | 1463 kPa | 74.06 W |
| TOP_CU_COLDPLATE_27 | 27.0 g/s | 1482 | laminar | 70478 | 9.97 K | 56.9 C | 83 kPa | 2.26 W |
| TWO_SIDED_SI_14 | 13.5 g/s | 632 | laminar | 92009 | 9.97 K | 37.2 C | 269 kPa | 7.35 W |
| SUBSTRATE_EMBEDDED_27 | 27.0 g/s | 2965 | transitional | 125399 | 9.97 K | 42.9 C | 574 kPa | 15.69 W |

**Pumping power is reported and never folded into the electrical total.** `P_electronics` and `P_pumping` stay separate; pump efficiency is unsourced, so hydraulic power is primary and a 35/55/75 % shaft-power band is carried beside it.

## 11.1 What this replaced, and why it mattered

The previous boundary was a single inverse-calibrated coefficient, **h = 166 000 W/m2K**, with one uniform sink temperature, chosen so the package would reach a target junction temperature. Three things were hidden inside it:

* **no laminar microchannel architecture reaches that coefficient.** The best gets 0.70x. Reaching it needs 50 g/s in the transitional regime, **74 W of pumping --- 7.4 % of the load ---** and 1.46 MPa;
* at the flow rate the reference system states, the coolant would rise **168 K**, which single-phase water cannot do. A 10 K rise needs 26.9 g/s;
* a single sink temperature cannot produce a streamwise gradient, and a real one moves the die warpage by several per cent.

![Cooling](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0mr/FIG_0MR_F_cooling.png)

## 11.2 Validation

The compact model has three parts and each is validated by a tool that can pose it:

| part | method | result |
|---|---|---|
| fluid side | analytic energy balance | exact for every design |
| solid side | MOOSE on the explicit finned geometry | see below |
| coupling | fixed-point iteration, energy checked | residual reported per solve |

| case | fin efficiency | R compact | R MOOSE | error | verdict |
|---|---|---|---|---|---|
| TuckermanPease_50x302 | 0.7666 | 6.4033e-06 | 6.1699e-06 | 3.78 % | **ACCEPTED** |
| wide_100x200 | 0.8562 | 6.1063e-06 | 5.5458e-06 | 10.11 % | **REJECTED** |
| tall_50x500 | 0.5632 | 5.3826e-06 | 5.4517e-06 | 1.27 % | **ACCEPTED** |
| copper_100x500 | 0.9322 | 1.1633e-05 | 1.0971e-05 | 6.04 % | **CONDITIONAL** |

**The compact solid model is valid for tall thin fins and degrades for short thick ones**, which is the expected failure of a 1-D fin assumption. The production geometry is inside the accepted band at 3.78 %; the short-fin case is REJECTED at 10.11 % against a band declared before the runs. That boundary is recorded, not glossed.

\newpage

# 12. Thermal homogenization

Every heterogeneous layer carries an anisotropic effective tensor, validated against explicit-geometry finite volumes on unit cells with a predeclared 10 % / 25 % acceptance band. The unit cell is its own periodic cell: for a centred inclusion in a square cell, symmetry puts zero normal flux on every mid-plane, and a 1x1 against 2x2 check confirms it to 0.000 %.

| layer | what survives | what does not |
|---|---|---|
| TSV + Si + liner | Voigt for k_z, better than 1 % | the pre-existing framework's transverse model, 19 to 74 % low, because it puts the liner in series with the copper |
| bump + underfill | Voigt for k_z and Maxwell for k_xy, both under 1.5 % | the TSV formula, which must not be reused: the contrast and the matrix are different |
| RDL stack | direction-resolved tensor per stack organisation | any single isotropic value |

## 12.1 The RDL, where the number depends on the organisation

| organisation | k_x | k_y | k_z | in-plane x/y | in-plane / through |
|---|---|---|---|---|---|
| LINES_1D | 233.47 | 1.76 | 1.24 | **132.55** | 189x |
| ORTHOGONAL | 117.63 | 117.63 | 1.24 | **1.00** | 95x |
| MESH | 260.74 | 260.74 | 1.27 | **1.00** | 205x |
| PLANE | 280.10 | 280.10 | 1.28 | **1.00** | 219x |

A single-direction line layer is strongly anisotropic in plane. **Every realistic organisation --- orthogonal routing, a mesh, a plane --- is in-plane isotropic to 1.00.** The real anisotropy is through-thickness against in-plane, 57x to 270x, because the inter-layer dielectric sits in series through the stack while the copper is in parallel across it.

That matters because the production package still gives this layer **one isotropic 0.7 W/m.K**: roughly right through thickness by accident, and two to three orders of magnitude too low in plane. The framework is missing a major lateral heat-spreading path, and the correction is built and measured but is not yet the default.

![RDL tensor](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0mr/FIG_0MR_E_rdl_tensor.png)

## 12.2 What is deliberately NOT homogenized

The local solder and transition regions keep explicit geometry. Homogenizing them would destroy the gradients the reliability chain reads. Global/local submodelling is retained throughout: tensors in the package model, explicit geometry in the joint and transition submodels.

\newpage

# 13. The mechanical model

## 13.1 Global

A linear thermoelastic finite-element model of the whole package: board, BGA field, converter layer, substrate with a homogenized TSV region, interface layer, die and TIM. Silicon is cubic-anisotropic; everything else is isotropic. The converged temperature field from Section 11 drives it.

It produces two things the rest of the chain uses: **die and package warpage**, and **the relative in-plane displacement across the corner BGA standoff** --- the quantity handed to the local solder model.

## 13.2 Local solder submodel

A graded finite-element model of the single worst joint, driven by the corner displacement, cycled to a stabilised response. The constitutive law is the overstress form in Section 4.3. The metric is the accumulated equivalent inelastic strain per stabilised cycle, volume-averaged over the solder core with a one-element corner exclusion band and matched to the averaging volume of the life law it feeds.

## 13.3 The RDL in the mechanical model

**The redistribution metal is not in the mechanical mesh.** The layer between the substrate and the die is 10 um of homogenized microbump and underfill at 8 GPa; the real RDL stack is 48 to 104 GPa in plane. A fidelity ladder was built and measured:

| rung | interface layer | Z1 corner shear | Z2 corner shear | Z1/Z2 |
|---|---|---|---|---|
| M-RDL0 | as built | 2.7486 um | 2.0796 um | **1.3217** |
| M-RDL1 | composite, 10 um | 2.6502 um | 2.0044 um | **1.3222** |
| M-RDL2 | composite, 50 um | 2.9358 um | 2.2237 um | **1.3202** |

Adding the RDL moves the absolute corner shear by **-3.6 % to +6.8 %** and the architecture RATIO by at most **0.11 %**. It changes the numbers and it does not change the ordering. **No RDL allowable is invented**, so the new stress remains response coupling and not a constraint.

\newpage

# 14. The solder reliability model, and what it cannot do

## 14.1 What is solid

* The metric is convergent, mesh-independent within its declared band, and verified to equal the solver's own accumulated inelastic strain including creep.
* Four SnAgCu fatigue formulations are admitted for RELATIVE life, their primary sources obtained and one calibration reproduced from the authors' own corrected coefficients.
* The inelastic energy is reconstructed from the solver's mechanical strain, so no separately parsed temperature enters the energy path.

## 14.2 What is conditional --- the dominant open item

> The creep half of the solder card is fitted on **Sn3.9Ag0.6Cu, not SAC305**, over **7.51 to 15.92 MPa**, while the joint's damage-weighted median stress is about **82 MPa** and **99.8 % of the damage is generated outside the fitted window**.

Two consequences that must not be conflated:

* **The ORDERING is robust.** It originates in the global thermoelastic model, which imposes a 32 % larger corner shear on Z1 and contains no solder law at all. The global package supplies a constitutive-law-independent deformation driver favoring Z2, and every presently testable constitutive and life-law combination preserves that ordering.
* **The MAGNITUDE is a conditional envelope of 1.19 to 1.22**, not a validated number. The permitted wording is "conditional relative-life envelope". "Validated relative life" is not earned.

## 14.3 What is absent

**Absolute life.** No required life exists anywhere in the sources, and the absolute life constant cannot be calibrated on top of an extrapolated constitutive model without burying the constitutive error inside the constant.

**A mechanical allowable.** Nine candidate thresholds were tested against six admissibility conditions and none passed. Without one, the reliability response cannot become a feasibility constraint, and the falsification gate that would test that remains untestable.

## 14.4 Which mechanisms exist at all

| mechanism | status |
|---|---|
| global bending | modelled --- a driver, not a failure |
| solder fatigue | **modelled**, convergent, conditional magnitude |
| solder creep / unified viscoplasticity | modelled |
| rate-independent plasticity | not separately modelled, and not justified on top of a unified law |
| organic board and underfill viscoelasticity | NOT modelled. Measured sensitivity: halving the board modulus moves the driver ratio about 3 % |
| assembly and reflow prestress | NOT modelled. Measured: it moves the stabilised ratio by 0.11 % |
| process residual stress | NOT modelled, no data |
| interface delamination | NOT modelled. Traction-separation parameters are unsourced |
| solder crack propagation | NOT modelled. Not needed for ranking |
| **RDL and TSV cracking** | **NOT modelled. The largest unmodelled mechanism that could change ranking** |
| moisture, hygroscopic swelling | OUT OF SCOPE, declared. The claim is dry steady operating ETM |

\newpage

# 15. Coupling directions

| from -> to | status | measured magnitude |
|---|---|---|
| electrical -> thermal | **solved, iterated** | the whole loss |
| thermal -> electrical | **solved, iterated** | rho(T) moves R by 22.8 % over the cycle |
| thermal -> mechanical | **solved, one way** | the whole thermal strain |
| geometry -> electrical / thermal / mechanical | **solved** | Sections 8, 12, 13 |
| cooling -> electrical / thermal / mechanical | **solved** | Section 11, and Section 17 |
| mechanical -> electrical | **absent** | 0.16 % on R, against 22.8 % from rho(T) already in the loop |
| mechanical -> thermal | **absent** | 1.5 K for a 4 % TIM bond-line change |
| damage -> electrical | **absent** | would be +33 % on R at 25 % of a joint lost |
| damage -> thermal | **absent** | would be +12.5 K at 25 % of the die delaminated |
| electromigration -> electrical | **OPEN** | the current-density allowable itself is unsourced |

**The framework is at ETM-L1**: electrical and thermal iterated to a fixed point, thermal driving mechanics one way, mechanics returning nothing.

That is a deliberate, measured choice and not an omission. The two absent arrows before damage are 0.7 % and 2.9 % of terms already in the loop, and both are common-mode across architectures, so solving them iteratively would cost solver time to chase a term two orders of magnitude smaller than one already present. **It is therefore accurate to describe this framework as geometry-coupled electrothermal-mechanical co-design with one-way mechanical response in the intact regime, and inaccurate to call it fully coupled.**

ETM-L3, with damage feeding back into conductance and stiffness, would be required to predict failure PROGRESSION. Nothing in this framework currently claims to.

\newpage

# 16. Validation matrix

| quantity | method | independent? | result |
|---|---|---|---|
| RDL sheet PDE | MOOSE | yes | 0.33 to 0.45 % |
| 3-D conduction, uniform bar | analytic | yes | exact at every mesh |
| 3-D conduction, spreading | analytic `rho/(4a)` | yes | +0.9 % at 6 cells per radius |
| **transition resistance, 5 geometries** | **MOOSE** | **yes** | **0.25 to 0.73 %, 5/5 ACCEPTED** |
| TSV single-via DC resistance | pre-existing framework, independent implementation | yes | exact |
| TSV skin ratio at 1 MHz | Bessel solution | yes | delta/r = 4.41, ratio 1.0001 |
| effective k_z, all layers | explicit-geometry RVE | yes | Voigt within 1 % |
| effective k_xy, bump layers | explicit-geometry RVE | yes | Maxwell within 1.5 % |
| effective k_xy, TSV arrays | explicit-geometry RVE | yes | Maxwell 11 to 39 % high; the pre-existing model 19 to 74 % low |
| unit-cell periodicity | 1x1 against 2x2 | yes | 0.000 % |
| cooling fluid side | analytic energy balance | yes | exact |
| **cooling solid side** | **MOOSE, explicit fins** | **yes** | **3.78 % at the production geometry; 10.11 % for short thick fins, REJECTED** |
| converter loss decomposition | upstream aggregate | yes | machine precision, or the ledger refuses to total |
| spatial heat deposition | electrical total | yes | within 1e-6 relative, guarded |
| solder PEEQ identity | creep-only experiment | yes | 1.0000 |
| inelastic energy route | solver mechanical strain | yes | 0.79 to 1.56 %, and 16 to 21x cleaner on the isochoric test |
| package thermal | MOOSE, full 3-D | yes | ordering preserved |
| **package thermal against CFD** | Icepak | -- | **FAILED and discarded.** No CFD validation is claimed |
| **TSV loop AC resistance** | HFSS | -- | **ATTEMPTED, did not converge in budget** |

\newpage

# 17. What the production models changed, measured

The same frozen comparison matrix was run twice, changing only which models drive the path. BEFORE is the previous production path: one global crowding constant, no intra-VR routing, a calibrated Robin boundary with a uniform sink, a lumped VR. AFTER is the path described in this document.

| architecture | mode | P_elec | T_max | die warpage | corner shear |
|---|---|---|---|---|---|
| Z1_EMBEDDED | AFTER | 141.78 W | 123.53 C | 25.373 um | 4.2803 um |
| Z1_EMBEDDED | AFTER | 141.76 W | 123.53 C | 25.372 um | 4.2801 um |
| Z1_EMBEDDED | BEFORE | 125.10 W | 84.87 C | 20.042 um | 2.7447 um |
| Z2_BACKSIDE | AFTER | 143.61 W | 130.31 C | 22.622 um | 3.4101 um |
| Z2_BACKSIDE | AFTER | 143.60 W | 130.31 C | 22.621 um | 3.4100 um |
| Z2_BACKSIDE | AFTER | 136.25 W | 114.89 C | 18.825 um | 2.8842 um |
| Z2_BACKSIDE | AFTER | 146.89 W | 136.53 C | 24.242 um | 3.6258 um |
| Z2_BACKSIDE | BEFORE | 126.19 W | 83.31 C | 17.236 um | 2.0754 um |
| Z4_POWER_DIE | AFTER | 134.74 W | 96.32 C | 35.946 um | 3.6681 um |
| Z4_POWER_DIE | BEFORE | 123.64 W | 83.30 C | 30.138 um | 2.9744 um |

\newpage

# 18. Numerical convergence

| model | convergence evidence |
|---|---|
| RDL sheet | grid-converged; 121 to 201 nodes moves the answer 0.15 % |
| 3-D transition | mesh drift 0.03 to 0.26 % between refinement levels |
| RVE homogenization | 1x1 against 2x2 periodic cell, 0.000 % |
| global thermal / structural | element budget is a hard gate at the measured solver ceiling, never a silent fallback |
| local solder | stabilised cycle declared as a cycle-to-cycle change below 5 %; achieved 0.03 to 0.22 % |
| energy integration | tightened until the answer stopped moving; time step and output frequency both refined |
| ET fixed point | iterated on LOCAL layer temperature to below 0.25 K |
| cooling fluid coupling | fluid temperature iterated to below 0.02 K |
| spatial heat | deposited total checked against the electrical total, guarded at 1e-6 relative |

\newpage

# 19. Defects found and corrected

This framework has a standing rule: a defect is recorded with the mechanism that let it survive, not only with its fix. Fifty-three are logged. The ones an auditor should know about:

| id | defect | how it survived | status |
|---|---|---|---|
| 30 | vertical-tier losses summed per-regulator with system-wide RDL loss | no scope type existed | FIXED, and made structural: mixing scopes now raises |
| 40 | the creep law was fitted in a stress variable the solver does not consume | the fit and the solver were never compared in the same variable | FIXED by removing the yield threshold |
| 44 | stale current-facing claims propagated into both reports | each sentence was true when written | FIXED at source |
| 46 | two parsers stood on opposite sides of a step boundary, inflating every inelastic-energy number by 18.5 % | both parsers were individually correct | FIXED, then ELIMINATED by reading the solver's own mechanical strain |
| 47 | the per-via current limit was a primitive in amperes, and it is the only thing that sets field resistance | it looked like a device property | FIXED: `J_design * A_c` |
| 48 | one global crowding constant for four interconnect classes | it was measured once, on one geometry | FIXED: solved per class, cross-validated |
| 49 | the TSV liner was absent from the conductor area | never modelled | FIXED |
| 50 | the converter area model assumes four-layer stacking and its own docstring says the opposite | `max()` reads like `sum()` at a glance | DOCUMENTED; upstream is a separate repository |
| 51 | intra-converter routing absent from every loss term | the converter was a black box with a loss number | FIXED: now in the total |
| 52 | the calibrated cooling coefficient is unreachable by any laminar cooler and hides 7.4 % of the load in uncharged pumping | it was calibrated to a temperature, and it hit it | FIXED: derived from hardware |
| **53** | **the current-status generator was internally consistent across both reports and consistently stale** | **cross-report comparison passes when both are stale in the same way** | **FIXED: a single authoritative contract, with mutation and injection tests** |

Four faults in this phase's own new code were caught before they reached a conclusion and are recorded for the same reason: a zero-width mesh cell that produced a silently wrong resistance whose only symptom was a current-balance residual; dead-ended traces that made a three-trace case look 2.5x worse; a planar intra-VR layout that returned 61 % of the load because it assumed a topology the architecture does not have; and a fit-quality metric that was misleading in both directions at once.

\newpage

# 20. Open physical gaps

| gap | why it is open | consequence |
|---|---|---|
| **high-stress SAC305 constitutive response** | no primary data above ~16 MPa retrievable; four P0 and five P1 papers behind institutional access | **the dominant blocker.** Every absolute reliability number is conditional on it |
| **required life** | not published for the reference system, and inventing one is forbidden | the falsification gate cannot be evaluated |
| **mechanical allowable** | nine candidates tested, none admissible | mechanics ranks but cannot constrain |
| electromigration current-density allowable | no primary study with its temperature, lifetime and geometry | feasibility is a map over J, never a verdict |
| package clearances | three unsourced | no partition template may be called buildable |
| cohesive-zone parameters | traction-separation laws unsourced | delamination cannot be predicted |
| polymer viscoelastic spectra | no DMA data for the specific laminate | a modulus sensitivity is carried instead of a Prony series |
| Z4 power-die layer geometry | the global mesh has no such layer | the Z4 thermal result is conditional on depositing its heat in the interface layer |
| conjugate CFD validation | the earlier attempt returned a solver clamp | no CFD validation is claimed |

![Closure ladder](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0mr/FIG_0MR_K_closure_ladder.png)

\newpage

# 21. Which claims are safe, and which are not

## 21.1 Safe to publish now

* Vertical placement of the converter changes both the electrical path and the local solder response, and the two trade against each other.
* Moving conversion below the substrate puts the 1 V rail on the TSVs, and the electrical cost of that is quantified.
* **Z2 carries a lower local fatigue-relevant inelastic response than Z1**, under every admitted constitutive model, every admitted life law, every profile and all three response metrics. The ordering originates upstream of the solder model. It is a RESPONSE ordering: calling it less damage would presume a sourced damage law, and that is OPEN.
* The conditional relative-life envelope is **1.19 to 1.22** at the operating baseline.
* Under minimum-capability provisioning the TSV conductor cross-section cancels out of the field resistance, and radius is a feasibility variable rather than a loss lever.
* A single global current-crowding multiplier is the wrong functional form; the measured spread over 107 geometries is 2.4x.
* Intra-converter metallization is a real loss term of order 0.4 to 3.9 % of the load and was previously absent.
* The calibrated cooling coefficient is not reachable by any laminar microchannel architecture, and reaching it costs about 7.4 % of the load in pumping power.
* A single-level VR does not fit the die shadow at 1 kW; vertical partitioning is a precondition.
* What CalculiX integrates in a `*VISCO` step is an overstress law with no rate-independent branch, traced in the solver source.

## 21.2 NOT safe, and why

| claim | why not |
|---|---|
| "Z2 lasts N cycles" | no absolute life is defensible |
| "validated relative life" | the magnitude is a conditional envelope; the wording is not earned |
| "the solder model is valid for this package" | it is evaluated far outside its fitted stress window |
| "the creep law is SAC305" | its data is Sn3.9Ag0.6Cu |
| "the stress extrapolation is common mode and cancels" | measured, and it only partly cancels |
| "mechanics constrains the design" | no admissible allowable exists |
| "the framework is fully ETM coupled" | mechanics returns nothing; it is ETM-L1 |
| "2.5D is eliminated" | only the one-sided low-voltage lateral topology is |
| "TSV radius is irrelevant" | it is not a field-loss lever; it is decisive for feasibility |
| "the thermal model is validated against CFD" | the CFD attempt failed and was discarded |
| "this partition template is buildable" | three package clearances are unsourced |
| "there is plastic and creep strain in the joint" | there is one viscoplastic strain |

\newpage

# 22. How this document stays true

Both this report and its chronological companion are generated from one file. That meant, for eight phases, that comparing them against each other could pass while both were stale --- and it did. The section headed "current scientific status" printed a current verdict above six bullets from a much earlier phase, and cross-report consistency was 25 of 25 the whole time.

The fix is the contract in Section 1.1. Every current-facing statement derives from it, and three tests keep it honest:

* **mutation** --- change one contract field and both reports fail until regenerated;
* **injection** --- each of five REAL stale sentences, copied verbatim from the artifact that contained it, is inserted into a current-facing block and must be caught;
* **exoneration** --- a defect report must still be able to quote the defect it fixed, or the guard becomes unusable and someone will switch it off.

Every evidence path in the contract is checked to exist on disk. That check rejected the first draft.

\newpage

# 23. What should happen next

In priority order, with the reason each is ahead of the next:

1. **Characterise SAC305 above 16 MPa**, by coupon test and by acquiring the four P0 papers. It is the dominant blocker on every absolute number, and no amount of modelling removes it.
2. **Obtain a required life** from the system owner. Without it the falsification gate cannot be evaluated, whatever the mechanics says.
3. **Put the RDL into the production mechanical and thermal stack by default.** The ladder is built and measured; it moves the absolute response by up to 7 % and the peak temperature by up to 4.7 K.
4. **Run a canonical single-channel Icepak benchmark** against the analytical correlation. The licence is available. Until it reproduces the correlation, no CFD validation may be claimed.
5. **Source the package clearances**, without which no partition template can be called buildable.
6. **Then, and only then, consider an optimizer.** Its preconditions are listed in Section 24 and none of them is currently met in full.

\newpage

# 24. The optimizer gate

A global optimizer is **FORBIDDEN** and remains so. Its preconditions, and where they stand:

| precondition | status after Phase 0M-R3A | evidence |
|---|---|---|
| interconnect geometry and crowding validated | **PARTIAL** | Delta_R cross-validated against MOOSE at 0.25-0.73 %; TSV span architecture-aware and consistent across all three domains. The EM allowable is still OPEN. |
| routing scope physically correct | **PARTIAL** | DOWNGRADED from YES by 0M-R3A. Routing is a hard gate and both frozen candidates pass it, but the repair that makes them pass sets a via radius in an UNSOURCED process window: ls_to_L is a 673 um intra-converter stacked via and the range used to license it governs through-silicon vias (DEFECT #58). |
| cooling boundary tied to physical hardware | **PARTIAL** | the production point is inside a SOURCE_BACKED correlation domain and the solid side is MOOSE-validated at 3.78 %. The fluid side has no conjugate CFD validation, and 2300 < Re < 3000 has no correlation at all. |
| architecture templates realizable | **PARTIAL** | UPGRADED from NO. One Z1 and one Z2 are CONDITIONAL_REALIZABLE at all 27 clearance corners. Neither is PROVEN_REALIZABLE: three package clearances are unsourced. |
| architecture geometry physically represented | **PARTIAL** | ARCH_Z4's power die is explicit geometry but its construction is unsourced, so its ranking stays conditional. |
| process margin on the critical interconnect | **NO** | ARCH_Z2's TSV field sits at AR = 10.000, M_AR = 1.000, and fails a modest tolerance bound. 0M-R3A re-derived the sweep: the smallest passing diameter is 32 um, not 34 um, and enlarging the via REDUCES the required count. Neither is adopted into the frozen pair. |
| intra-VR via technology sourced | **NO** | NEW in 0M-R3A. The design space has tsv.*, rdl.* and bump.* and no entry governing a stacked via through substrate power layers. The 20 um repair radius is arithmetically self-consistent and not shown to be manufacturable. |
| dominant mechanical physics closed | **NO** | high-stress SAC305 constitutive response is CONDITIONAL; cohesive-zone parameters OPEN; 6 of 8 enumerated failure mechanisms uncomputed. |
| an admissible mechanical criterion exists | **NO** | nine candidates tested against six admissibility conditions; none passed. |
| a required life exists | **NO** | N_required is OPEN. |
| absolute fatigue prediction validated | **NO** | the strain and energy formulations disagree 4.1x on this joint. |

Phase 0M-R3A DOWNGRADED the routing precondition from YES to PARTIAL, because the repair that makes both candidates pass sits in an unsourced via process window, and added a new precondition for whether that via technology is sourced at all. Phase 0M-R2 had DOWNGRADED the cooling precondition from YES to PARTIAL --- the model has no validated correlation between Re 2300 and Re 3000, and an optimizer would be free to walk into that hole --- and added a new one for whether the architecture geometry is physically represented at all. **6 remain NO, and any one of them is sufficient to keep the gate shut.**

\newpage

# 25. Reproducibility

| item | location |
|---|---|
| single source of truth for current state | `results/CURRENT_SCIENTIFIC_STATUS.yaml::current_state_contract` |
| production interconnect model | `scripts/phase0mr/interconnect_production.py` |
| 3-D conduction solver | `scripts/phase0m/conduction3d.py` |
| independent cross-check | `scripts/phase0mr/moose_conduction.py` |
| intra-VR routing | `scripts/phase0mr/routing_production.py` |
| loss ledger, one owner per watt | `scripts/phase0mr/ledger.py` |
| physical cooling | `scripts/phase0mr/cooling_production.py` |
| production ET fixed point | `scripts/phase0mr/production_et.py` |
| controlled replay | `scripts/phase0mr/run_replay.py` |
| current-state guard | `scripts/phase0mr/defect53_audit.py` |
| tests | `tests/`, run with `python -m pytest tests -q` |

The repository is **not under version control**, so content addressing is used: every authoritative artifact's md5 is recorded at each phase boundary and the previous PDFs are archived byte-identically under `results/archive/`.

Environment: Python 3.12.14, CalculiX 2.23, MOOSE heat_transfer `09515f92aa`, gmsh 4.15.2, AEDT 2026 R1 (HFSS and Icepak licensed, Q3D not), pandoc 2.0.6 with xelatex.

# 26. Auditor checklist

Ten questions worth asking of this framework, with where to find the answer:

| question | where |
|---|---|
| is any resistance a primitive? | Section 8 --- no, and the classifier raises on anything unclassified |
| can any loss term be double counted? | Section 10 --- the ledger enforces one owner per watt and refuses to total otherwise |
| is the cooling boundary fitted to its own answer? | Section 11 --- no longer; it is derived from channel geometry and flow |
| is any solver used outside what it can pose? | Section 5 --- HFSS is explicitly NOT used for DC conduction, and why |
| is any effective property unvalidated? | Section 12 --- every tensor has an RVE error and a verdict |
| is the metric mesh-converged? | Section 18 |
| is any claim stale? | Section 22 --- generated from a contract, with mutation and injection tests |
| what would change the ranking? | Section 20 --- RDL and TSV cracking is the largest unmodelled candidate |
| what is conditional and on what? | Section 14.2, and the uncertainty ledger |
| may an optimizer be built? | Section 24 --- no, four preconditions remain unmet |

# 27. Symbols

| symbol | meaning | units |
|---|---|---|
| `rho(T)` | resistivity | Ohm.m |
| `A_c` | conductor cross-section | m2 |
| `J_design` | provisioning current density | A/m2 |
| `J_process_max` | manufacturing capability bound | A/m2 |
| `J_reliability_allow` | electromigration allowable --- **OPEN** | A/m2 |
| `n_req`, `n_avail`, `n_alloc` | required, available and allocated via counts | -- |
| `dR_transition` | 3-D resistance minus the 1-D reference | Ohm |
| `sigma_s` | sheet conductance | S |
| `k_x, k_y, k_z` | effective conductivity tensor diagonal | W/m.K |
| `h(x)` | local film coefficient | W/m2.K |
| `T_f(x)` | local coolant temperature | C |
| `eta_fin` | fin efficiency | -- |
| `du_corner` | corner-BGA relative in-plane displacement | um |
| `PEEQ` | accumulated equivalent inelastic strain | -- |
| `ME` | solver mechanical strain, total minus thermal | -- |
| `D` | per-cycle inelastic damage metric | -- |
| `N_required` | required life --- **OPEN** | cycles |

# 28. Glossary

**DVPD** --- distributed vertical power delivery: converting close to the load so the high-current rail travels vertically and briefly rather than laterally.

**Overstress law** --- a creep law driven by the amount by which the stress exceeds a yield surface, rather than by the stress itself. It returns exactly zero below yield. This is what CalculiX integrates in a `*VISCO` step.

**Homogenization** --- replacing a geometrically detailed layer with an equivalent uniform material. Valid only with a stated error against the explicit geometry.

**RVE** --- representative volume element: the smallest repeating cell whose solution gives the effective property of the whole layer.

**Constriction / spreading resistance** --- the extra resistance where current converges into or diverges out of a smaller cross-section. Not captured by `rho L / A`.

**Fin efficiency** --- the fraction of a cooling fin's surface that is as effective as its base. It falls as the fin gets taller or thinner.

**Caloric resistance** --- the temperature rise caused simply by the coolant absorbing heat, `1/(2 m_dot c_p)`. It is a property of the flow, not of the surface, and a single film coefficient hides it.

**Common mode** --- an error that multiplies both architectures by the same factor and therefore cancels in their ratio. Whether it does must be tested, not assumed.

**ETM-L1 / L2 / L3** --- coupling levels: L1 is electrical-thermal iterated with one-way mechanics; L2 adds mechanical feedback into conductance or geometry; L3 adds damage feeding back. This framework is L1.

