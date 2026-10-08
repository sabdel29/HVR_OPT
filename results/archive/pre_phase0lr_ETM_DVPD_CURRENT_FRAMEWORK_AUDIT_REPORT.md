---
title: "Electro-Thermo-Mechanical Co-Design of Distributed Vertical Power Delivery"
subtitle: "Current-Framework Technical Audit Report"
date: "2026-09-14"
---

# Preface --- what this document is

This report describes **what the ETM-DVPD framework does today**. It is not a history of how it
got here. It is written for an independent technical auditor who understands circuits, power
delivery, packaging and basic heat transfer, but who may have little or no background in
nonlinear solid mechanics or solder fatigue. Every mechanical concept therefore appears twice:
once as a precise definition, and once in plain language.

A reader who has never seen this project should be able to finish this document knowing exactly
which physics are included, how the electrical, thermal and mechanical models are coupled, which
equations are solved, which software does what, what has been validated and to what standard,
what remains uncertain, and how to reproduce every major result.

Two conventions are used throughout and are worth stating up front.

**Provenance labels.** Every number carries one of five labels: **SOURCE-BACKED** (traceable to
a primary publication or datasheet), **CALIBRATED** (fitted to data inside this project),
**ASSUMPTION** (chosen, with the choice recorded), **DERIVED** (computed from the above), or
**OPEN** (not yet determined). A number without a label is a bug.

**Validation language.** "Validated" means compared against an independent measurement or an
independent solver and found to agree within a stated criterion. "Cross-checked" means compared
against a second computation of the same thing. "Conditional" means the result holds only under
stated assumptions that are not themselves established. These words are not interchangeable and
this report does not use "validated" where only "cross-checked" is true.

\newpage

# 1. Executive technical overview

## 1.1 The system being modelled

A 1 kW load --- a 500 mm2 compute die drawing **1000 A at 1 V** --- fed from a **48 V** input.
At that current, the power delivery network is not a detail of the package; it is the dominant
design constraint. Delivering 1000 A laterally across a board and up through a conventional
substrate costs more power than the load's own logic in many practical stacks.

**Distributed vertical power delivery (DVPD)** attacks this by moving the final conversion stage
physically close to the load and routing power *vertically* through the package rather than
laterally across it. The converter is a **hybrid voltage regulator (HVR)**: a switched-capacitor
stage that divides 48 V down to an intermediate rail, followed by a multiphase buck stage that
regulates to 1 V. "Hybrid" refers to that combination --- the switched-capacitor stage does the
bulk ratio efficiently without magnetics, and the buck stage provides regulation and transient
response.

The design question this framework exists to answer is deceptively simple:

> **Where in the vertical stack should the converter go?**

Moving it changes the electrical path, the heat map, the mechanical stiffness distribution and
the substrate thickness *simultaneously*, and those effects push in opposite directions. That is
what makes it an electro-thermo-mechanical (ETM) problem rather than three separate ones.

## 1.2 What ETM means here, concretely

Three physics are solved, in a specific order, with a specific coupling:

1. **Electrical.** Converter losses and interconnect losses, both of which depend on
   temperature through $R_{DS(on)}(T)$, inductor DCR(T) and copper resistivity $\rho_{Cu}(T)$.
2. **Thermal.** Steady conduction through the package stack, driven by those losses as spatially
   mapped heat sources.
3. **Mechanical.** Thermal expansion mismatch between the layers produces warpage and strains
   the solder joints; cycling that strain fatigues them.

Electrical and thermal are **two-way coupled** and are solved as a fixed point: losses set the
temperature, and the temperature changes the losses. Mechanical is **one-way coupled
downstream**: the temperature field loads the structure, but the structure has no back-action on
the electrical or thermal problem in this model (linear thermoelasticity, no
deformation-dependent contact). That is why the order is *electrical-thermal fixed point first,
converged temperature field second, structural solve third* --- and it is a modelling decision,
recorded as such, not a law of nature.

The complete dataflow, block by block, is Section 3 and AUDIT-FIG-1.

## 1.3 What goes in and what comes out

**Inputs.** Architecture choice, package geometry, switching frequency, device selection from a
GaN device library, TSV counts and allocation, material properties, coolant conditions, and a
thermal cycling profile.

**Outputs.** Total system power loss and its breakdown; the converged temperature field; package
warpage; the stress and inelastic strain history in the critical solder joint; a per-cycle
fatigue response metric; and --- conditionally --- a cycles-to-failure estimate.

## 1.4 The current strongest conclusion

> **Z2 (backside) has a relative solder-fatigue-life advantage over Z1 (embedded) of
> approximately 1.17 to 1.39, at an electrical cost of +1.688 W, which is +1.3 % of
> system loss.**

This is a **relative** result. It survives because the unknown constant in the fatigue law
cancels exactly when two architectures are compared through the same law, and because the
architectures are compared at the same reference condition on the same extraction volume.

## 1.5 What the framework does NOT claim

This is the more important half of the summary.

- **It does not claim an absolute life.** No statement of the form "Z2 survives N cycles" is
  defensible. Model-form spread between the admitted fatigue laws is a factor of 4.1 on this
  joint, and Phase 0L has now added a constitutive uncertainty on top of that.
- **It does not claim the solder constitutive model is valid where it is used.** It is not. The
  creep law is calibrated over 7.51 to 15.92 MPa and evaluated at damage-weighted stresses of
  54 to 91 MPa. Section 13 states this precisely.
- **It does not claim the creep data is for the right alloy.** It is not. Section 13.6.
- **It does not know what life is required.** $N_{required}$ has no source anywhere in this
  project. Without it the pass-fail gate cannot be evaluated at all. Section 16.
- **It does not model any failure mechanism other than solder thermal fatigue.**
  Electromigration, delamination, chip-package interaction and dielectric failure are all
  outside the model.
- **There is no optimizer.** The framework evaluates architectures; it does not search over them.

## 1.6 Framework at a glance

| Item | Current state |
|---|---|
| Reference load | 1 kW, 48 V input, 1 V / 1000 A output, 500 mm2 die (22.36 mm square) |
| Architectures live | Z1 embedded, Z2 backside, Z4 separate power die |
| Architecture eliminated | Z5 2.5D lateral (tested, eliminated); Z3 topside not source-described |
| Electrical model | converter synthesis + rail-aware vertical path + multilayer RDL sheet PDE |
| Electrical-thermal coupling | fixed point on $R(T)$, convergence enforced, non-convergence rejects the candidate |
| Thermal solver | CalculiX steady conduction; MOOSE heat_transfer cross-check |
| Global mechanics | CalculiX linear thermoelasticity, explicit BGA + PCB, boundary condition BC-A |
| Local mechanics | CalculiX submodel of one joint, graded mesh, 25 μm Syed extraction layers |
| Solder constitutive law | viscoplastic overstress, $\dot{\varepsilon} = A (\sigma_{vm} - \sigma_y)^n$, **no rate-independent plasticity** |
| Reliability metrics | M1 accumulated inelastic path, M2 within-cycle range, M3 inelastic energy |
| Fatigue laws admitted | Syed 2004 (author-corrected), Schubert 2003 |
| Relative life Z2/Z1 | 1.17 to 1.39 (Phase 0L, across every admitted constitutive variant) |
| Absolute life | CONDITIONAL, not validated |
| $N_{required}$ | **OPEN** --- no source exists |
| Gate G2 | **NOT TESTED** |
| Optimizer | **FORBIDDEN** until the gates close |
| Board-level experiment | designed, not frozen; blocked on a stress-domain limitation |

\newpage

# 2. Physical system and architectures

## 2.1 The stack

All architectures share a common skeleton, described from the substrate underside
(the datum, $z = 0$, with $+z$ towards the compute die):

- a **PCB**, 1600 μm, present when the package is board-mounted;
- a **BGA** ball array, 400 μm diameter on 800 μm pitch, 300 μm standoff --- this is the joint
  population whose fatigue this framework predicts;
- a **substrate** containing the **TSV field**, 30 μm diameter vias on 60 μm pitch, 300 μm per
  power layer;
- the **compute die**, 22.36 mm square, 780 μm thick;
- the **HVR** itself, whose position is the design variable.

Vertical interconnect dimensions and unit resistances are SOURCE-BACKED from the reference
system's own Table III: BGA 0.3 mΩ, power-layer TSV 7.1 mΩ, chiplet pad 1.7 mΩ. The reference
system implies three 300 μm power layers, hence a 900 μm substrate --- a source-backed number
that matters because it is exactly what Z2 escapes.

![AUDIT-FIG-2](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0l/auditfig/AUDIT_FIG_02_cross_sections.png)

## 2.2 Z1 --- EMBEDDED (project baseline)

The converter sits **inside** the substrate power layers. The 48 V input rises through the TSV
field to the embedded cell; conversion happens there; 1 V then travels a short vertical distance
to the die.

- Conversion occurs: inside the substrate.
- TSV rail: **48 V**, so the TSV field carries about 20.8 A.
- Substrate thickness: constrained to be at least 900 μm, because the cell must fit inside it.
- Heat: converter loss is injected in the middle of the substrate.
- Source status: **SOURCE-DESCRIBED but NOT DEMONSTRATED.** The reference publication states
  that multi-layer substrates integrating active and passive components "remains an open
  challenge".

## 2.3 Z2 --- BACKSIDE

VR chiplets are stacked on the substrate **underside**, between the BGA and the substrate. The
48 V input reaches them directly from the board; conversion happens below the substrate; **1 V
then crosses the TSV field** to reach the die.

- Conversion occurs: below the substrate.
- TSV rail: **1 V**, so the TSV field carries the full **1000 A**.
- Substrate thickness: free to thin to 300 μm, because nothing needs to be embedded.
- Heat: converter loss is injected below the substrate, on the board side.
- Source status: **SOURCE-BACKED.** The reference states that VR components fabricated as
  chiplets "can be vertically stacked on the backside of a substrate and interconnected through
  TSVs".

## 2.4 Z4 --- SEPARATE POWER DIE

A dedicated VR die is bonded directly beneath the compute die, above the substrate.

- Conversion occurs: immediately under the die.
- TSV rail: **48 V**.
- Substrate thickness: 900 μm.
- Heat: converter loss is injected directly under the compute die --- thermally the worst place.
- Source status: **PARTIALLY source-backed**; a monolithic power die extrapolates the source's
  chiplet framing.

## 2.5 Z5 --- 2.5D LATERAL (eliminated)

HVR and compute die side by side on a common interposer. This was evaluated and **eliminated**:
the 1 V rail must travel laterally across the interposer, which reintroduces exactly the lateral
IR-drop problem DVPD exists to remove. It is retained in the configuration only so that the
elimination is reproducible.

## 2.6 Why this is not just an electrical trade

The reason the answer is not obvious is that the three effects of moving the converter do not
agree:

| Moving from Z1 to Z2 | Direction |
|---|---|
| TSV rail changes from 48 V to 1 V | **worse** electrically, by about 1960x on TSV I2R |
| Substrate can thin from 900 μm to 300 μm | **better** mechanically --- less bending stiffness mismatch |
| Converter heat moves from inside the substrate to below it | changes the temperature field and the warpage |
| The stiff converter block moves relative to the neutral plane | changes the curvature, hence the joint shear |

A purely electrical study picks Z1. A purely mechanical study picks Z2. Only the coupled model
can weigh +1.688 W against a fatigue-life ratio.

\newpage

# 3. The full ETM dataflow

This is the most important figure in the report. Every box is a computation, every arrow is a
quantity handed from one solver to the next, and the colour of each box states how well that
step is currently supported: **green = closed**, **orange = conditional**, **red = open**.

![AUDIT-FIG-1](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0l/auditfig/AUDIT_FIG_01_dataflow.png)

## 3.1 Every arrow, explained

| From | To | What crosses the arrow | Units |
|---|---|---|---|
| design variables | converter synthesis | architecture, $f_{sw}$, device choice, cell count | --- |
| converter synthesis | rail-aware current path | the converter's input and output currents, and where conversion happens in $z$ | A, --- |
| rail-aware current path | PDN losses | which rail (48 V or 1 V) crosses each interconnect class, and the current in it | A |
| PDN losses | ET fixed point | $P_{conv}$ and $P_{PDN}$ at the current temperature estimate | W |
| ET fixed point | heat-source mapping | converged per-component losses | W |
| heat-source mapping | thermal solver | a volumetric source field $q(x,y,z)$ whose integral equals the electrical loss | W/m3 |
| thermal solver | $T(x,y,z,t)$ | the converged temperature field | K |
| $T(x,y,z,t)$ | ET fixed point (feedback) | temperature, which changes $R_{DS(on)}$, DCR and $\rho_{Cu}$ | K |
| $T(x,y,z,t)$ | global thermoelastic model | the same field, used as the thermal load $\varepsilon_{th} = \alpha \Delta T$ | K |
| global thermoelastic | boundary displacement history | $\Delta u(t)$ across the critical joint standoff, and $T(t)$ at that joint | μm, °C |
| boundary history | local solder submodel | the two histories, applied as boundary conditions to the refined joint model | μm, °C |
| local submodel | creep / inelastic metrics | the per-cycle increment of accumulated inelastic strain, its within-cycle range, and the inelastic work density | ---, ---, MJ/m3 |
| metrics | fatigue life law | one scalar response metric per stabilised cycle | --- |
| fatigue life law | $N_f$ | cycles to a defined failure fraction | cycles |
| $N_f$ | pass/fail (G2) | compared against $N_{required}$ | cycles |

## 3.2 Why the loop closes where it does

Only one arrow points backwards: temperature into the loss models. That is the electrical-thermal
fixed point of Section 9, and it is a genuine two-way coupling because the loss is a function of
the temperature it produces.

Every other arrow points forward. In particular **mechanics never feeds back**. In this model the
deformation does not change the electrical resistance (no piezoresistance, no contact area
change) and does not change the thermal conductance (no gap opening, no delamination). That is a
modelling decision with a stated justification --- linear thermoelasticity with perfectly bonded
interfaces has no such mechanism --- and it is what allows the problem to be solved as a
sequence rather than as one monolithic coupled system.

## 3.3 Where the chain is broken today

The chain is complete and closed from design variables all the way to a per-cycle response
metric. It becomes conditional at the fatigue law, and it is open at the mission requirement. In
practical terms: **the framework can currently tell you which architecture is better and by how
much, but not whether either one is good enough.** Sections 15 to 17 develop that statement
precisely.

\newpage

# 4. Design variables and the input contract

Inputs are separated by provenance, because that separation is what makes the result auditable.

## 4.1 User / design variables

| Variable | Units | Range or set |
|---|---|---|
| architecture | --- | Z1, Z2, Z4 (Z5 eliminated) |
| switching frequency $f_{sw}$ | MHz | device- and topology-dependent |
| GaN device | --- | selected from the EPC product table (90 usable parts) |
| inductor | --- | selected from a sourced inductor library |
| number of VR cells $n_{vr}$ | --- | integer, drives per-regulator scope |
| TSV allocation $n_{alloc}$ | --- | integer, bounded below by $n_{required}$ and above by $n_{available}$ |
| substrate thickness $h_{sub}$ | μm | architecture-constrained (Section 2) |
| thermal cycling profile | °C, s | $T_{min}$, $T_{max}$, dwell, ramp rate |

## 4.2 Source-backed parameters

| Parameter | Value | Source |
|---|---|---|
| BGA unit resistance | 0.3 mΩ | reference system Table III |
| power-layer TSV unit resistance | 7.1 mΩ | reference system Table III |
| chiplet pad unit resistance | 1.7 mΩ | reference system Table III |
| TSV geometry | 30 μm diameter, 60 μm pitch, 300 μm height | reference system Table III |
| BGA geometry | 400 μm diameter, 800 μm pitch, 300 μm standoff | reference system Table III |
| RDL stack | 10 μm Cu, 10/2 line/space, 2 VDD + 2 GND layers | ECTC 2024 |
| inductor height | 500 μm | upstream inductor library (TCPMT 2026) |
| die size | 22.36 mm square, 500 mm2 | reference system |
| SAC305 yield $\sigma_0(T)$ | 39.32 to 10.50 MPa over -40 to 122 °C | Yuan 2023 Table 10 |
| SAC305 creep points | 19 points, 45 to 150 °C, 7.51 to 15.92 MPa | Yuan 2023 Table 5 (see Section 13.6) |

## 4.3 Calibrated parameters

| Parameter | How calibrated |
|---|---|
| Norton $A(T)$, $n(T)$ | least squares in $\log \dot{\varepsilon}$ vs $\log \sigma$ on the 19 points, per temperature |
| cooling coefficient | calibrated so the 1 kW reference case reaches its design junction temperature |
| AC current-crowding factor | from HFSS frequency-domain simulation |

## 4.4 Assumptions

Each of these is a *choice*, recorded so that an auditor can challenge it.

| Assumption | Value | Note |
|---|---|---|
| SAC305 Young's modulus at 25 °C | 45 000 MPa | midpoint of a sourced 40 to 50 GPa band |
| SAC305 $dE/dT$ | -120 MPa/K | **no source** |
| SAC305 Poisson ratio | 0.36 | **no source**, no temperature dependence |
| SAC305 CTE | 21.5 ppm/K | commonly quoted 21 to 24; **no temperature dependence** |
| stabilised cycle | cycle 5 of 6 | the final simulated cycle is discarded (Section 12.5) |

## 4.5 Open parameters

| Parameter | Why it is open |
|---|---|
| $N_{required}$ | no field or product requirement exists in this project or in any supplied source |
| absolute fatigue-law constant for this package | requires a package-specific calibration experiment |
| SAC305 constitutive response above about 16 MPa | no retrievable primary data (Section 13.7) |

\newpage

# 5. Converter electrical model

## 5.1 Topology

48 V enters a **switched-capacitor (SC) stage** that divides it to an intermediate rail, and the
intermediate rail feeds a **multiphase buck** that regulates to 1 V. The SC stage does the bulk
ratio without magnetics, which is what makes the tall inductor problem tractable; the buck stage
provides regulation and transient response. This split is the "hybrid" in hybrid voltage
regulator.

## 5.2 Loss components

Total converter loss is the sum of five terms. Every symbol is defined in Section 27.

**Conduction loss** --- the resistive loss in the power FETs while they are on:

$$ P_{cond} = I_{rms}^2 \, R_{DS(on)}(T_j) \, D $$

where $I_{rms}$ is the RMS device current (A), $R_{DS(on)}(T_j)$ the on-state resistance at
junction temperature $T_j$ (Ω), and $D$ the duty ratio. The temperature dependence is the
first half of the electrical-thermal coupling:

$$ R_{DS(on)}(T) = R_{DS(on),25} \left[ 1 + \alpha_{GaN} (T - 25) \right] $$

with $\alpha_{GaN}$ the normalised temperature coefficient of the selected GaN part
(SOURCE-BACKED, from the device library; swept as a corner in the robustness study).

**Switching loss** --- energy lost while the device transitions:

$$ P_{sw} = \tfrac{1}{2} V_{ds} I_{sw} (t_r + t_f) f_{sw} $$

**Output-capacitance loss** --- the energy stored in $C_{oss}$ and dumped each cycle:

$$ P_{Coss} = E_{oss}(V_{ds}) \, f_{sw} $$

$E_{oss}$ is taken from the device datasheet curve rather than from $\tfrac{1}{2} C V^2$,
because $C_{oss}$ is strongly nonlinear in $V_{ds}$ for GaN.

**Gate-drive loss:**

$$ P_{gate} = Q_g V_{drv} f_{sw} $$

**Inductor loss** --- winding resistance plus core loss:

$$ P_{L} = I_{rms}^2 \, \mathrm{DCR}(T) + P_{core}(B, f_{sw}) $$

$$ \mathrm{DCR}(T) = \mathrm{DCR}_{25} \left[ 1 + \alpha_{Cu} (T - 25) \right] $$

with $\alpha_{Cu} = 0.00393$ per K. This is the second half of the electrical-thermal coupling.

**Ripple** enters through $I_{rms}$: for a buck phase with peak-to-peak ripple
$\Delta I_L = V_o (1 - D) / (L f_{sw})$, the RMS current is
$I_{rms}^2 = I_{dc}^2 + \Delta I_L^2 / 12$, so higher $f_{sw}$ reduces conduction loss
through ripple while increasing switching and $C_{oss}$ loss. That trade is why $f_{sw}$ is
a design variable and not a constant.

## 5.3 Where this is implemented

| Quantity | Module | Function |
|---|---|---|
| device library | `Scalable_Integrated_VR/EPC-Product-Table.csv` | 90 usable parts |
| $R_{DS(on)}(T)$, DCR(T) | `scripts/phase0d/electrical.py` | `rdson_at`, `dcr_at` |
| converter compilation | `scripts/phase0d/electrical.py` | `compile_hvr`, `HVRDesign` |
| 1 kW reference assembly | `scripts/phase0f/kw1.py` | `design_1kw` |

The converter loss model is **cross-checked, not validated**: it reproduces the upstream
`DVPDRoutingModel` implementation numerically by unit test, but no independent measurement of a
built converter exists inside this project. Section 21 records this honestly.

\newpage

# 6. Rail-aware power-path model

## 6.1 Why the rail matters more than anything else

The same 1 kW crosses the substrate either as 48 V or as 1 V. Since $P = VI$:

$$ I_{48} = \frac{1000\ \mathrm{W}}{48\ \mathrm{V}} = 20.83\ \mathrm{A}, \qquad
   I_{1} = \frac{1000\ \mathrm{W}}{1\ \mathrm{V}} = 1000\ \mathrm{A} $$

a current ratio of 48. Resistive loss goes as the square:

$$ \frac{P_{I^2R}(1\ \mathrm{V})}{P_{I^2R}(48\ \mathrm{V})} = 48^2 = 2304 $$

for the *same* conductor. With Z2's larger allocated via count the realised penalty is about
**1960x** on the TSV field. This single fact is why architecture choice is a power-delivery
question and not a packaging preference.

![AUDIT-FIG-3](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0l/auditfig/AUDIT_FIG_03_rail.png)

## 6.2 Three via counts that must never be conflated

This distinction was the subject of a real defect in this project and is now structurally
enforced.

| Symbol | Meaning | Set by |
|---|---|---|
| $n_{required}$ | the minimum vias needed to carry the current without exceeding the per-via current limit | $\lceil I_{total} / (J_{max} A_{via}) \rceil$ |
| $n_{allocated}$ | the vias the floorplan actually assigns to this net | a design decision |
| $n_{available}$ | how many vias physically fit in the field at the given pitch | geometry |

Feasibility requires $n_{required} \le n_{allocated} \le n_{available}$. **Electrical
resistance must use $n_{allocated}$**, because that is the number of conductors actually in
parallel:

$$ R_{field} = \frac{R_{single}}{n_{allocated}} $$

Dividing by $n_{required}$ instead silently makes every design look feasible and
under-resistive at the same time. The per-via limit is $J_{max} A_{via}$ with $J_{max}$ taken
from a source-backed envelope, and feasibility is reported as a **map over $J_{max}$** rather
than as a single verdict, because $J_{max}$ is itself a reliability assumption.

Implementation: `scripts/phase0e/stack.py`, functions `n_required`, `n_available`, `allocate`,
`r_field`.

## 6.3 Hard feasibility

A configuration is **infeasible**, not merely poor, if $n_{required} > n_{available}$. The code
raises `Infeasible` rather than returning a large loss, so an infeasible point can never be
averaged into a trend or selected by a search.

\newpage

# 7. Vertical interconnect model

Each vertical conductor class --- BGA ball, C4 bump, TSV, microbump/pad --- is modelled as a
temperature-dependent resistor:

$$ R = \frac{\rho(T)\, L}{A}, \qquad \rho_{Cu}(T) = \rho_{Cu,20}\left[1 + \alpha_{Cu}(T - 20)\right] $$

with $L$ the conductor length (m), $A$ its cross-sectional area (m2), and
$\rho_{Cu,20} = 1.68 \times 10^{-8}$ Ω m.

Conductors of a class are in parallel, so $R_{class} = R_{single} / n_{allocated}$. Crucially,
the model carries the **supply and return** paths: current goes up the VDD vias and comes back
down the GND vias, so the loop resistance is the sum, not the supply resistance doubled by
assumption. An earlier version multiplied the supply loss by two; the present model solves
VDD + load + GND explicitly.

The AC behaviour --- skin effect and current crowding at the via-to-pad transition --- is not
computed analytically. It enters as a **measured crowding factor from HFSS** applied to the DC
resistance (Section 18).

**Stated limitation.** Contact resistance at the via-to-pad interface and current crowding into
the pad are the least certain part of this model. They are represented by a single factor, not
resolved geometrically. Q3D, which is the natural tool for extracting that geometry-resolved
parasitic, is **not licensed on this system**, so no Q3D result exists.

\newpage

# 8. RDL and the horizontal PDN

## 8.1 The governing equation

The redistribution layer is a thin metal sheet, so the in-plane potential obeys a
two-dimensional conduction PDE:

$$ \nabla \cdot \left( \sigma_s \, \nabla V \right) = -J $$

where $V$ is potential (V), $\sigma_s$ is the **sheet conductance** (S, i.e. per square) of the
layer, and $J$ is the areal current density injected or extracted (A/m2). The dissipated power
follows from the field:

$$ P = \int_{A} \sigma_s \, \left| \nabla V \right|^{2} \, dA $$

Both are solved on a finite-difference grid over the die footprint.

## 8.2 Why a scalar resistance is not enough

The obvious shortcut is to write $R = \rho L / (W t)$ for "the RDL" and be done. That fails here
for a specific, quantifiable reason: **the sources have finite area and so does the load.**
Current does not flow from a point to a point; it spreads from 49 distributed VR tiles into a
distributed load. The effective resistance of that spreading problem is not any single
$\rho L / A$, and the error is not a constant factor --- it depends on the placement, which is
one of the design variables. The scalar model is therefore no longer used anywhere.

## 8.3 What the implementation carries

- **Explicit VDD and GND layers.** The stack is 2 VDD + 2 GND layers of 10 μm copper. The loop
  is solved as VDD + load + GND return, not as the supply solved once and doubled.
- **Occupancy derived, not assumed.** The fraction of each layer that is actually metal is
  derived from the 10/2 μm line/space design rule, not guessed.
- **Exact cell-overlap weighting.** Each VR tile injects its current into the grid cells it
  physically overlaps, weighted by the overlap *area*. This is what makes the injected-current
  integral equal the electrical current to machine precision.
- **Boundary conditions.** Natural (zero-flux) on the die edges; the load is a distributed
  extraction over the die footprint.

Implementation: `scripts/phase0e/stack.py`, functions `multilayer_sheet_solve`,
`rdl_network_solve`, class `RDLStack`.

## 8.4 MOOSE validation

The compact sheet solver was checked against MOOSE's `heat_transfer` module, which solves the
mathematically identical operator $\nabla \cdot (k \nabla T) = -q$. Agreement is reported per
placement case in `results/phase0e/` and the comparison script is
`scripts/phase0e/validate_moose_rdl.py`. This is a genuine **independent-solver validation** of
the PDE solution --- it does not validate the sheet conductance value itself, which is derived
from the sourced stack.

\newpage

# 9. Electrical-thermal fixed point

## 9.1 The loop

Losses depend on temperature; temperature depends on losses. The two are solved together:

```
initialize T  <- ambient + a first guess
repeat:
    P_conv   <- converter_loss(T)          # R_DS(on)(T), DCR(T)
    P_pdn    <- interconnect_loss(T)       # rho_Cu(T) in TSV, BGA, RDL
    q(x,y,z) <- map_heat_sources(P_conv, P_pdn)    # exact cell overlap
    T_new    <- thermal_fe_solve(q)
    if max |T_new - T| < tol:  break
    T        <- T_new
until converged
```

![AUDIT-FIG-4](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0l/auditfig/AUDIT_FIG_04_fixed_point.png)

## 9.2 Convergence

The convergence test is on the **maximum** change in any monitored component temperature between
successive iterates, not on a mean and not on total power. Typical behaviour is convergence in a
handful of iterations, because the loop gain is modest: a 10 K temperature error moves
$R_{DS(on)}$ by a few per cent, which moves the temperature by a fraction of a kelvin.

**A candidate that does not converge is REJECTED.** It is never reported at its last iterate.
This is enforced in code, not by convention.

Implementation: `scripts/phase0d/coupled.py`, function `solve_et`, returning `ETResult`.

## 9.3 PER_REGULATOR versus SYSTEM scope, and ScopeError

This is the most important structural protection in the electrical model, and it exists because
of a real defect that produced a 4x error at 240 W and a 49x error at 1 kW.

The problem: `vertical_tier()` is naturally evaluated with the **per-regulator** current and the
**per-tile** footprint, so its result is *one regulator's* loss. `rdl_network_solve()` is
naturally driven with every source and the full load, so its result is *the whole system's*
loss. Adding the two together is a units error that no dimensional check catches, because both
are in watts.

The fix is a typed quantity. Every electrical power value carries a `Scope` tag --- either
`PER_REGULATOR` or `SYSTEM` --- and the arithmetic refuses to mix them:

- `watts_per_regulator(x)` and `watts_system(x)` construct tagged quantities;
- `total(...)` raises **`ScopeError`** if the operands disagree;
- conversion between scopes must be explicit, by multiplying by $n_{vr}$.

Implementation: `scripts/phase0h/scope.py`, class `Scope`, exception `ScopeError`,
functions `Q`, `watts_per_regulator`, `watts_system`, `total`.

\newpage

# 10. Thermal model

## 10.1 Governing equation

Steady-state conduction with an anisotropic conductivity tensor:

$$ \nabla \cdot \left( \mathbf{K} \, \nabla T \right) + q(x,y,z) = 0 $$

$\mathbf{K}$ is the thermal conductivity tensor (W/m K). It is anisotropic where the physical
structure is: the TSV field is a copper-in-dielectric composite whose through-thickness
conductivity differs from its in-plane conductivity, and it is **homogenised** to an equivalent
tensor rather than meshed via by via. The homogenisation is derived in
`scripts/phase0b/etm/config.py`, function `derive_tsv_homog`, and the derived value carries its
provenance into the run manifest.

## 10.2 Boundary conditions

A **Robin** (convective) condition on the cooled surfaces:

$$ -\mathbf{K}\nabla T \cdot \mathbf{n} = h \left( T - T_{\infty} \right) $$

with $h$ the effective heat transfer coefficient (W/m2 K) and $T_{\infty}$ the coolant
temperature. Other external surfaces are adiabatic. The coolant condition is a CALIBRATED
parameter: $h$ is set so that the 1 kW reference case reaches its design junction temperature
(`scripts/phase0f/calibrate_cooling_1kw.py`). That calibration is a modelling convenience, and
it means absolute temperatures are anchored by construction --- **temperature differences
between architectures are the meaningful output, not absolute junction temperature.**

## 10.3 Which regions receive which heat

| Heat source | Where it is injected |
|---|---|
| die power | top of the compute die, uniformly over the 500 mm2 footprint |
| HVR converter loss | the converter block, whose $z$ position IS the architecture (Section 2) |
| RDL sheet loss | distributed over the RDL layers by the local $\sigma_s |\nabla V|^2$ density |
| TSV field loss | distributed through the TSV field volume |
| BGA / bump loss | at the joint layer |

Source mapping is by **exact area overlap** between the physical source footprint and the mesh
cells, so the integral of the mapped heat equals the electrical loss to machine precision. This
is checked as an assertion, not assumed.

![AUDIT-FIG-5](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0l/auditfig/AUDIT_FIG_05_heat_map.png)

## 10.4 Steady versus transient

The electrical-thermal fixed point is solved **steady**. The mechanical cycling problem is
**transient in temperature** but the temperature history is prescribed from the cycling profile
rather than recomputed at every instant, because the thermal time constant of the package is
short compared with the 5-minute dwells used in the profiles. This is a stated modelling
decision.

## 10.5 Thermal cross-validation

| Comparison | Status |
|---|---|
| CalculiX vs MOOSE `heat_transfer` on the RDL/conduction operator | **agrees**; the independent-solver check that is relied upon |
| CalculiX vs Icepak on the package | **DISCARDED.** The Icepak model failed cross-validation and its result is not used for any current claim |

The Icepak attempt is reported because an auditor should know it was made and why it is absent,
not because it contributes evidence.

\newpage

# 11. Global package mechanics, explained from first principles

## 11.1 Start here: materials expand by different amounts

Heat a free bar of material and it gets longer. The fractional length change is the **thermal
strain**:

$$ \varepsilon_{th} = \alpha \, \Delta T $$

$\alpha$ is the coefficient of thermal expansion (CTE), in parts per million per kelvin. Silicon
is about 2.6 ppm/K; organic substrate about 16; PCB about 18; SAC305 solder about 21.5; copper
about 17.

Now bond those materials together. They cannot each take the length they individually want.
Whatever length they end up sharing, each layer is strained away from its own free length, and a
strained elastic solid carries stress. That is **CTE mismatch**, and it is the entire origin of
the mechanical problem. No external force is applied anywhere in this model --- every stress in
this package comes from materials disagreeing about how long they should be.

## 11.2 The constitutive equation

Stress is produced by the part of the strain that is *not* free thermal expansion:

$$ \boldsymbol{\sigma} = \mathbf{C} : \left( \boldsymbol{\varepsilon}_{total}
   - \boldsymbol{\varepsilon}_{th} \right) $$

$\mathbf{C}$ is the fourth-order elastic stiffness tensor; for an isotropic material it is set
by Young's modulus $E$ and Poisson ratio $\nu$. Read the equation as: *"take the total strain,
subtract the part the material would have had for free, and the remainder is what the material
is fighting."*

This is closed by equilibrium --- forces must balance everywhere:

$$ \nabla \cdot \boldsymbol{\sigma} = 0 $$

## 11.3 Neutral axis, bending stiffness and warpage

A layered plate whose layers have different CTEs does not just expand; it **bends**. The reason
is that the expansion mismatch is not symmetric about the plate's mid-plane.

Every plate has a **neutral axis**: the height at which the in-plane strain is unchanged by
bending. For a layered plate it sits at the stiffness-weighted centroid,

$$ z_{NA} = \frac{\sum_i E_i t_i z_i}{\sum_i E_i t_i} $$

and the plate's resistance to bending, its **bending stiffness** $D$, is the second moment of
the same weighting about that axis. A layer that wants to expand more than its neighbours and
sits *above* the neutral axis bends the plate one way; the same layer *below* the neutral axis
bends it the other way.

**This is precisely why moving the converter matters mechanically.** The converter block is
stiff and has its own CTE. In Z1 it sits inside the substrate; in Z2 it sits below it. Same
block, opposite side of the neutral axis, opposite contribution to curvature --- and a different
substrate thickness as well, which moves the neutral axis itself.

**Warpage** is the resulting out-of-plane deflection. It is what a shadow-moire measurement of a
real package reports, which makes it the most directly checkable mechanical output.

![AUDIT-FIG-6](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0l/auditfig/AUDIT_FIG_06_cte.png)

## 11.4 Free package versus board-mounted package

A package sitting on a bench is free to warp. The same package soldered to a PCB is not: the
board restrains it, and the restraint force flows through the solder joints. The two situations
give **different joint loading**, and only the second is relevant to BGA fatigue.

The framework therefore uses:

- **BC-A** --- the current boundary condition. The package is modelled **with an explicit BGA
  ball array and an explicit PCB**. The board's own stiffness and CTE participate, and the
  joints carry the mismatch between package and board. This is the configuration used for every
  current mechanical result.
- **BC-B** --- a historical rigid-clamp boundary condition, in which the package underside was
  kinematically constrained. **It is not used.** A clamp imposes whatever force is needed to
  enforce the constraint, which both over-stiffens the assembly and hides the fact that the
  joints are the load path. It is recorded here only so that an auditor who finds BC-B in the
  history knows it was superseded and why.

## 11.5 What the mechanical model does not include

- No **rate-independent plasticity in the solder** --- see Section 13.4; this is a property of
  the solver's formulation, not an omission of convenience.
- No **viscoelasticity** in the organic substrate or underfill.
- No **moisture**, no **assembly prestress**, no **residual stress from reflow**.
- No **damage or crack growth**: fatigue is inferred from a strain or energy metric through an
  empirical law, not simulated.
- No **contact or delamination**: all interfaces are perfectly bonded.

\newpage

# 12. Global-to-local submodelling

## 12.1 Why the problem is split

The package contains on the order of a thousand BGA joints. Resolving each one with the mesh
refinement that a nonlinear viscoplastic solder calculation needs --- two elements across each
12.5 μm layer --- is not affordable in a model that also contains the board, the substrate, the
die and the converter. The available solver has a practical ceiling of about 40 000 elements for
this class of nonlinear transient problem.

So the problem is split:

1. The **global model** resolves the whole package and board with joints represented coarsely.
   It gets the warpage and the load path right.
2. It hands the **critical joint** two histories: the relative in-plane displacement imposed
   across the joint standoff, $\Delta u(t)$, and the joint temperature, $T(t)$.
3. The **local model** resolves that one joint in full detail, driven by those two histories.

![AUDIT-FIG-7](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0l/auditfig/AUDIT_FIG_07_submodel.png)

## 12.2 Which joint is critical

The outermost corner joint --- the one at the greatest distance from the neutral point of the
package. Shear from CTE mismatch grows with distance from the neutral point, so the corner joint
sees the largest $\Delta u$. This is the standard choice in board-level reliability and it is
applied here without modification.

## 12.3 The 25 μm extraction layers

This detail is not a mesh preference; it is a compatibility requirement with the fatigue law.

Syed's fatigue constants were calibrated on a specific averaging volume: **a 25 μm thick layer
of solder at the joint interface**, with the metric volume-averaged over that layer. The source
states the constants are valid only for that thickness. Averaging over a different volume gives
a different number and the published constant no longer applies to it.

The local mesh therefore reproduces the source's own extraction geometry exactly:

- two extraction layers, **package side and board side**;
- each **25 μm** thick;
- each **two elements** across the thickness, so 12.5 μm per element;
- the metric is the volume-weighted average over those elements.

Implementation: `scripts/phase0jr/graded_joint.py`, function `build_joint_graded`, which creates
the element sets `ESYED`, `ESYED_BOT`, `ESYED_TOP` and `ESYEDCORE`.

## 12.4 Mesh grading and corner singularities

The mesh is **geometrically graded** from the 12.5 μm interface elements into a coarser bulk, so
that refinement is spent where the metric is extracted rather than uniformly.

At a bimaterial corner the elastic solution is genuinely singular --- the computed stress rises
without bound as the element size falls, so the peak element value is a mesh artefact, not a
material state. The framework therefore **never reports a raw maximum as a scientific result**.
Every stress metric is reported three ways: `raw_max` (diagnostic only), `p99` (the headline),
and `p95` (a robustness check). If p99 and p95 diverge, the metric is mesh-sensitive and is
treated as such.

Implementation: `scripts/phase0b/etm/metrics.py`.

## 12.5 Two numerical details an auditor will otherwise trip over

The **final simulated cycle is discarded** and the penultimate cycle is reported. In every run,
the last cycle comes out about 15 % low --- identically in 4-cycle and 6-cycle runs whose cycle 3
values agree to four significant figures. Since the physics cannot know which cycle is last,
this is an output artefact of the final step, not a stabilisation trend. Six cycles are run and
cycle 5 is reported.

**The energy metric needs finer time stepping than the strain metric.** M1 is an accumulated
strain and is converged at ordinary increment sizes. M3 is an integral of stress against
inelastic strain increment, and most of the inelastic work is deposited in the fast transient at
the start of each half-cycle. Coarse stepping through that transient under-integrates it: moving
to a tighter solver start raises M3 by 11 to 24 % while moving M1 by at most 0.41 %. Every
Phase-0L comparison is therefore run at one uniform tight setting, and the analysis scripts
refuse to compare runs whose solver control differs.

\newpage

# 13. The SAC305 solder constitutive model

This section reflects the **final Phase-0L audit result**, which changed what the framework is
understood to be integrating. It supersedes every earlier description of the solder law in this
project.

## 13.1 What the material card contains

Four cards are written into every CalculiX deck for SAC305:

| Card | Content | Provenance |
|---|---|---|
| `*ELASTIC` | $E(T)$, $\nu$ | 45 000 MPa at 25 °C SOURCE-BACKED band; $dE/dT = -120$ MPa/K and $\nu = 0.36$ are ASSUMPTIONS |
| `*PLASTIC` | bilinear $\sigma_y$ vs equivalent inelastic strain, per temperature | Yuan 2023 Table 10 (Chaboche), SAC305 |
| `*CREEP, LAW=NORTON` | $A(T)$, $n(T)$, $m = 0$ | fitted to 19 points, Yuan 2023 Table 5 |
| `*EXPANSION, ZERO=25.` | $\alpha = 21.5$ ppm/K | ASSUMPTION |

A detail worth flagging because it is easy to misread: CalculiX's `*EXPANSION` with `ZERO=25.`
is a **secant** coefficient referenced to 25 °C, not an instantaneous one. The thermal strain it
applies is $\alpha (T - 25)$, differenced against the same expression at the initial temperature.

## 13.2 The elastic part

$$ \boldsymbol{\sigma} = \mathbf{C}(E(T), \nu) : \boldsymbol{\varepsilon}_{el}, \qquad
   E(T) = 45000 - 120 \,(T - 25)\ \mathrm{MPa} $$

clamped below at 5000 MPa. **In plain language:** the solder gets softer as it heats up, by about
12 % per 100 K. The slope is an assumption with no source, and it is swept as a corner in the
robustness study.

## 13.3 The thermal part

$$ \varepsilon_{th} = \alpha \,(T - T_{ref}), \qquad \alpha = 21.5 \times 10^{-6}\ \mathrm{K^{-1}} $$

Temperature-independent, which is an assumption: real SAC305 CTE rises measurably over this
range.

## 13.4 The inelastic part --- and what it is NOT

This is the part that Phase 0L audited from the solver source and from controlled probes, and
the finding is important enough to state as plainly as possible.

**What the documentation suggests.** The CalculiX manual's `*CREEP` page gives the Norton law as

$$ \dot{\varepsilon} = A \,\sigma^{n}\, t^{m}, \qquad \text{"$\sigma$ is the true Von Mises stress"} $$

**What the solver actually integrates.** With `*PLASTIC` and `*CREEP` both present in a `*VISCO`
step, CalculiX 2.23 integrates

$$ \dot{\varepsilon}_{in} = A(T) \left( \sigma_{vm} - \sigma_y(\bar{\varepsilon}_{in}) \right)^{n(T)},
   \qquad \dot{\varepsilon}_{in} \equiv 0 \ \text{ whenever } \ \sigma_{vm} \le \sigma_y $$

This was traced in `src/incplas.f` --- the yield test at line 310, the driving stress at line 599
and the flow rule at line 605 --- and then confirmed against the binary over 7603 single-element
increments. The source-derived law reproduces the solver to a median relative error of
$1.2 \times 10^{-5}$; the manual's form is wrong by a median factor of 14.4 and by up to
$1.8 \times 10^{6}$.

Three consequences follow, and each matters for how results must be read.

**(a) There is no rate-independent plasticity in this model at all.** In a `*VISCO` step the
rate-independent plastic corrector is never executed. A single consistency parameter carries the
entire inelastic increment, and that increment is governed by the creep law. The `*PLASTIC` card
does not define a plastic flow rule here; it supplies the threshold $\sigma_y(\bar{\varepsilon})$
and its hardening slope *to the creep law*. So the familiar decomposition
"elastic + plastic + creep" does not describe this model: it is **elastic + one viscoplastic
strain**.

**(b) The yield stress acts as a hard threshold on creep.** Below $\sigma_y$ the computed creep
rate is not small --- it is exactly zero. Twenty probe states at $\sigma / \sigma_y$ from 0.25 to
0.99, held for up to $5.8 \times 10^{8}$ s of simulated time (eighteen years), returned a final
PEEQ of exactly 0.0.

**(c) There is no time hardening.** $m = 0$ in the card, and the probe confirms it: PEEQ is
bit-identical across total-analysis-time offsets spanning nine decades.

![AUDIT-FIG-8](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0l/auditfig/AUDIT_FIG_08_deformation.png)

## 13.5 Temperature interpolation --- a card is a table, not a function

CalculiX interpolates $A$, $n$ and $\sigma_y$ **linearly between card rows**, and **clamps**
outside them. It does not know or care what functional form the card generator had in mind.

The card generator builds intermediate rows by Arrhenius interpolation of the rate at a reference
stress, which is the physically right thing to do --- but the solver then draws straight lines
between those rows. The two agree only *at* the rows. Measured at 62.5, 97.5 and 132.5 °C, the
solver matches linear-in-$A$ to within 0.04 % and disagrees with the Arrhenius curve by factors
of 1.33, 2.80 and **20.0**.

For the production card (rows at $-40/0/25/50/75/100/125$ °C) the practical consequences are:

- between rows, over 45 to 150 °C, the realised creep rate is **0.83x to 3.88x** the intended one;
- **above 125 °C the card clamps**, so a 150 °C profile is run on the 125 °C row, giving 0.62x at
  20 MPa rising to **8.70x** at 100 MPa.

Refining the grid to 18 rows spanning $-40$ to 150 °C reduces the between-row span to 0.81x to
1.51x and removes the clamping. **All Phase-0L replays use the refined grid**, and the coarse
grid is retained as a separate model so that the grid effect can be separated from the
constitutive effect.

## 13.6 Provenance of the creep data --- the alloy is not SAC305

The 19 creep points were attributed in the code to "Yuan (2023), Table 26". That paper was
retrieved in full. **It has eleven tables.** The points are its **Table 5**, and Yuan section 4.1
states that "the experimental dataset is drawn from Xiao and Armstrong", whose paper is titled
*"Tensile creep and microstructural characterization of bulk **Sn3.9Ag0.6Cu** lead-free solder"*.

So the creep half of this material card is calibrated on **Sn3.9Ag0.6Cu** --- 3.9 wt % silver
against SAC305's 3.0 wt %. Silver content is the principal control on Ag3Sn precipitate
strengthening and therefore on creep rate in this alloy family. A focused search of 344 works
found **no transferability evidence** between the two alloys.

The yield half of the card is genuinely SAC305, but is two model layers removed from measurement:
Motalab's SAC305 data was fitted with an Anand model, that model generated synthetic
stress-strain curves, and the Chaboche constants were fitted to those curves.

**The two halves of one material card are different alloys, and the overstress formulation
subtracts one from the other.**

## 13.7 Calibration domain versus operating domain

| | Calibrated over | Package actually reaches |
|---|---|---|
| Temperature | 45 to 150 °C | $-40$ to 150 °C depending on profile |
| Stress | **7.51 to 15.92 MPa** | damage-weighted **54 to 91 MPa**; peak $\sigma_{vm}$ to 217 MPa |

**In plain language: extrapolation means using a curve outside the range where anyone measured
it.** A power law fitted between 7.5 and 15.9 MPa says nothing reliable about 60 MPa; the fit had
no opportunity to be wrong there. Concretely, the fitted law predicts that the creep rate at
100 MPa is **4.2 million times** the rate at the top of the window it was fitted in, and nothing
in the data constrains that number.

![AUDIT-FIG-13](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0l/auditfig/AUDIT_FIG_13_domain.png)

## 13.8 The calibration-variable defect

The regression that produced $A(T)$ and $n(T)$ was performed on **total applied stress**:
`fit_norton_data` regresses $\log\dot{\varepsilon}$ on $\log \sigma_{applied}$, with no yield
subtraction. The solver consumes $\sigma_{vm} - \sigma_y$. **These are different variables.**

The consequence is not a bias, it is a contradiction. At the four calibration temperatures the
yield stress is 20.61, 15.43, 11.32 and 10.50 MPa, while the data spans 7.51 to 15.92 MPa. **The
overstress is negative at 16 of the 19 calibration points.** In the solver's own variable, the
calibration experiment lies entirely inside the elastic domain, where the model produces no
inelastic strain at all.

Fed back through the solver, the card reproduces **0 of its 19 source points**: 16 return exactly
zero, and the three with positive overstress are low by factors of $4.7\times10^{7}$,
$1.8\times10^{12}$ and $2.4\times10^{5}$.

**The quoted 8.3 % rms fit residual is therefore not a measure of model quality.** It measures how
well a curve fits data in a variable the solver never evaluates.

## 13.9 What is actually used going forward

A consistent refit in the solver's variable is **not constructible**: with negative overstress
forbidden, there are zero usable points at 45 °C, zero at 80 °C, one at 115 °C and two at 150 °C,
against the two per temperature a Norton law needs.

The only self-consistent option is to set $\sigma_y \rightarrow 0$, which makes the solver's
driving variable equal the variable the card was fitted in. This is supported on three
independent grounds:

1. **Solver implementation.** With no yield surface the integrated law is exactly
   $\dot{\varepsilon} = A\sigma^{n}$, confirmed to a median $3\times10^{-6}$ relative error.
2. **Experimental definition.** The source data is steady-state creep under constant applied
   load, with no threshold anywhere in its definition.
3. **Physics.** At 45 to 150 °C, SAC305 sits at a homologous temperature of 0.65 to 0.86. Power-law
   creep in solder at those temperatures has no yield threshold; it is the dominant deformation
   mode well below yield. The CalculiX manual says this itself: *"At high temperatures creep is
   frequently observed well below the yield stress. To simulate this behavior one can set the
   yield stress to zero."*

That choice was made on these three grounds **before** any architecture ratio was computed under
it. Section 17 reports what it did to the ratio.

\newpage

# 14. Reliability metrics

## 14.1 The three metrics

| ID | Name | Definition |
|---|---|---|
| **M1** | accumulated equivalent inelastic strain per stabilised cycle | $\Delta \bar{\varepsilon}_{in}$, the increment of PEEQ over one cycle, volume-averaged over the 25 μm layers |
| **M2** | within-cycle range | $\max_t \bar{\varepsilon}_{eq}(t) - \min_t \bar{\varepsilon}_{eq}(t)$ over one cycle |
| **M3** | inelastic energy density per cycle | $\Delta w = \oint \boldsymbol{\sigma} : d\boldsymbol{\varepsilon}_{in}$ over one cycle, volume-averaged the same way |

Two further identities matter and were established by probe rather than assumed:
**M4 (creep-only strain) is identical to M1**, and **M5 (creep-only energy) is identical to M3**,
because Section 13.4 established that every inelastic increment in this model *is* creep. There
is no separate plastic part to exclude.

## 14.2 The odometer analogy

This is the single most common source of confusion in reading these results, so it is worth
being explicit.

**PEEQ behaves like a car's odometer, not like its position.** Drive to the shops and back and
your position is unchanged, but the odometer has advanced by twice the distance. In the same way,
the solder joint returns to almost exactly its starting shape at the end of every thermal cycle
--- but PEEQ counts every increment of irreversible deformation accumulated along the way, in
both directions, and only ever increases.

So M1 (how far the odometer moved this cycle) and M2 (how far the joint actually travelled from
one extreme to the other) are **different physical quantities**. For a symmetric cycle M1 is
roughly twice M2, but that factor is not universal --- it depends on the shape of the cycle. A
fatigue law calibrated against one of them cannot be used with the other, and Section 15 takes
that seriously.

![AUDIT-FIG-9](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0l/auditfig/AUDIT_FIG_09_peeq.png)

## 14.3 Spatial averaging

Each metric is the **volume-weighted average** over the two 25 μm extraction layers described in
Section 12.3:

$$ \langle X \rangle = \frac{\sum_{e \in \mathrm{ESYED}} X_e \, V_e}{\sum_{e \in \mathrm{ESYED}} V_e} $$

The element set `ESYED` is exactly the package-side and board-side layers, two elements deep
each. Nothing outside that set enters the reported metric.

## 14.4 The stabilised cycle

The first cycles of a viscoplastic simulation are not representative: the joint is still finding
its cyclic steady state. Six cycles are run and the metric is taken from **cycle 5**, with cycle
6 discarded for the reason given in Section 12.5. Stabilisation is reported as the percentage
change between cycle 4 and cycle 5, and a run whose stabilisation exceeds a few per cent is
treated as not stabilised.

\newpage

# 15. Fatigue life

## 15.1 Three different things that are easy to conflate

| Quantity | What it is | Where it comes from |
|---|---|---|
| **response metric** | how hard the joint is worked per cycle | the FE model |
| **fatigue law** | how many such cycles the joint survives | empirical, from somebody else's test campaign |
| **required life** | how many cycles the product must survive | the product owner |

The framework computes the first, borrows the second, and **does not have** the third.

![AUDIT-FIG-10](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0l/auditfig/AUDIT_FIG_10_life_bridge.png)

## 15.2 The admitted laws

**Syed 2004** (author-corrected values), in the accumulated-strain and accumulated-energy forms:

$$ N_f = \left( 0.0468 \, \varepsilon_{acc} \right)^{-1}, \qquad
   N_f = \left( 0.0015 \, w_{acc} \right)^{-1} $$

**Schubert 2003** for SnAgCu, which publishes exponents but **no prefactors**: slope 1.3 on
strain and 1.0 on energy. Because the prefactor is missing, Schubert can only ever be used for
*ratios*, never for an absolute life. That is a property of the source, not a choice.

Both laws are calibrated on the 25 μm averaging volume reproduced in Section 12.3. Darveaux's
constants are **not** admitted: they are for eutectic SnPb on 12.7 μm layers, and the source
itself warns of a "factor of 7" spread.

## 15.3 Why constants cancel in a ratio, and what does not

For a law of the form $N_f = (C \, \varepsilon)^{-k}$, the ratio between two architectures is

$$ \frac{N_{f,Z2}}{N_{f,Z1}} = \left( \frac{\varepsilon_{Z1}}{\varepsilon_{Z2}} \right)^{k} $$

The constant $C$ has vanished. This is why a relative claim can be defensible when an absolute
one is not --- and it is the load-bearing reason the project's strongest result is a ratio.

**What does not cancel:**

- the **exponent** $k$, which differs between the admitted laws;
- the **choice of metric family** --- strain and energy do not rank architectures identically;
- any **architecture-dependent** modelling error. An error that is common to both architectures
  cancels; one that is not, does not. Section 17 tests exactly this rather than assuming it.

## 15.4 Absolute life

Under the admitted laws, the conditional absolute life at the reference condition is roughly
2500 cycles (Syed strain) or 610 cycles (Syed energy) for Z1 --- a **4.1x model-form spread on
the same joint under the same simulation**. Both are additionally conditional on a constitutive
model whose calibration domain the package leaves by a factor of 3.4 to 7.2 in stress, and whose
underlying creep data is for a different alloy.

**No absolute life is claimed.** The numbers above are quoted only to show the size of the
spread.

\newpage

# 16. Mission requirement and gate G2

## 16.1 The gate, in one line

$$ N_f \ \ge \ N_{required} $$

$N_f$ is what the package can survive. $N_{required}$ is what the product must survive. G2 is
satisfied when the first exceeds the second. **In plain language: G2 asks "is it good enough?",
and answering it needs both a capability and a demand.**

## 16.2 Why relative life cannot substitute for the gate

Knowing that Z2 lasts about 1.2 to 1.3 times as long as Z1 tells you which to prefer. It tells
you nothing about whether *either* passes. If the requirement is 500 cycles, both pass and the
architecture choice is free to be made on electrical grounds. If it is 50 000, both fail and the
ratio is irrelevant. The ratio only becomes decision-relevant in the narrow band where one passes
and the other does not.

## 16.3 That band has been mapped, and it is empty

The decision map, computed across all admitted laws:

| Region | Condition |
|---|---|
| all architectures pass under every admitted law | $N_{required} \le 474$ |
| all architectures fail under every admitted law | $N_{required} > 3206$ |
| **robust Z1-fail / Z2-pass** | **NONE** |

The last row is the important one. Z1 fails under *every* admitted law only above 2499 cycles;
Z2 passes under *every* admitted law only below 581 cycles. Those conditions are **disjoint**.
There is no requirement value at which the architecture choice is robustly decision-critical
given today's model-form spread.

The ambiguous interval 474 to 3206 cycles spans about **0.83 decades**, which is 27.6 % of a
three-decade sweep from 100 to 100 000 cycles. Quoted as a linear fraction it would be 2.7 %,
which is an order of magnitude smaller and misleading; the logarithmic figure is the honest one
and is the one used.

## 16.4 Status of $N_{required}$

**OPEN.** No field requirement, product specification or qualification target exists anywhere in
this repository or in any supplied source. Every occurrence of the identifier `n_required` in the
codebase refers to the **TSV via count** of Section 6.2, which is an entirely different quantity
that happens to share a name.

This is recorded as **USER_INPUT_REQUIRED**. A structured request with eight specific questions
is in `results/phase0k/SYSTEM_OWNER_MISSION_REQUEST.md` and remains outstanding.

## 16.5 Status of G2

**NOT TESTED**, and not testable today. Two independent blockers, either of which is sufficient:

1. $N_{required}$ is undefined (this section);
2. absolute $N_f$ carries a 4.1x model-form spread, on top of a constitutive model that is
   extrapolated far outside its calibration domain (Section 13).

Closing only the first would leave the gate decidable but with an answer that depends on which
admitted fatigue law is chosen. **Both must close.**

\newpage

# 17. Architecture comparison

<!-- BEGIN GENERATED: architecture_comparison -->
All values are at the reference condition and come from the artifacts named in each row. Nothing here is carried over from a superseded phase.

## 17.1 The authoritative comparison

| Quantity | Z1 EMBEDDED | Z2 BACKSIDE | Z4 POWER DIE | source |
|---|---|---|---|---|
| substrate thickness (mm) | 1.30 | 0.30 | 0.30 | `results/phase0i/z_architecture_comparison.csv` |
| TSV rail | HV (48 V) | **LV (1 V)** | HV (48 V) | `results/phase0i/z_architecture_comparison.csv` |
| TSV current (A) | 23.4 | 1000.0 | 23.4 | `results/phase0i/z_architecture_comparison.csv` |
| total electrical loss (W) | 126.090 | 127.778 | 126.120 | `results/phase0i/z_architecture_comparison.csv` |
| of which TSV loss (W) | 0.0098 | 1.6979 | 0.0397 | `results/phase0i/z_architecture_comparison.csv` |
| of which PDN loss (W) | 0.825 | 2.514 | 0.855 | `results/phase0i/z_architecture_comparison.csv` |
| converter efficiency (%) | 88.80 | 88.67 | 88.80 | `results/phase0i/z_architecture_comparison.csv` |
| joint temperature (°C) | 82.86 | 81.85 | 81.10 | `results/phase0i/z_architecture_comparison.csv` |
| package maximum (°C) | 84.96 | 83.45 | 83.52 | `results/phase0i/z_architecture_comparison.csv` |
| die warpage p-v (μm) | 20.08 | 17.27 | 30.25 | `results/phase0i/z_architecture_comparison.csv` |
| corner joint shear Δu (μm) | 2.7486 | 2.0796 | 2.9840 | `results/phase0i/z_architecture_comparison.csv` |
| M1 creep strain ratio vs Z1 | 1.0000 | 1.2000 | 1.0330 | `results/phase0l/package_model_replay.csv` (model M1) |
| **relative life vs Z1** | 1.000 | **1.17 to 1.39** | 0.94 to 0.98, NOT RESOLVED | `results/phase0l/common_mode_verdict.csv` |
| status | baseline; SOURCE-DESCRIBED, not demonstrated | preferred on fatigue, +1.688 W (+1.34 %) | not resolved against Z1 | --- |

Z2 costs **1.688 W** more than Z1, which is **+1.34 %** of Z1's total loss, essentially all of it in the TSV field (1.698 W against 0.0098 W, a factor of 173).

## 17.2 Is the constitutive extrapolation common mode? --- the Phase-0L test

Before Phase 0L this project asserted that the stress extrapolation "applies identically to all three architectures, so it is common mode and cancels in a ratio" --- a claim **withdrawn** here, because it was an assumption and Phase 0L tested it against a tolerance fixed and hashed **before** any ratio under an alternative model existed (`results/phase0l/PART12_PREDECLARED_TOLERANCE.md`, sha256 `fc19abf7...`).

The test replays Z1, Z2 and Z4 under every admitted constitutive model and asks how much the architecture ratio moves:

| model | what it is | M1 strain ratio | M3 energy ratio | Syed Eq.14 life ratio |
|---|---|---|---|---|
| `M0_COARSE` | the incumbent, verbatim | 1.2834 | 1.2735 | 1.2834 |
| `M0_FINE` | incumbent law, corrected card temperature grid | 1.2875 | 1.2747 | 1.2875 |
| `M1` | **corrected**: yield threshold removed, so fit and solver share a variable | 1.2000 | 1.2301 | 1.2000 |
| `M1_NHI` | M1 with n + 2 SE | 1.1887 | 1.1710 | 1.1887 |
| `M1_NLO` | M1 with n - 2 SE | 1.2184 | 1.3017 | 1.2184 |

| quantity | min | median | max | spread S | every ratio > 1? | classification |
|---|---|---|---|---|---|---|
| Syed2004 Eq14 strain | 1.1887 | 1.2184 | 1.2875 | **0.0811** | yes | PARTIAL CANCELLATION |
| Schubert2003 strain | 1.2520 | 1.2928 | 1.3889 | **0.1059** | yes | PARTIAL CANCELLATION |
| Syed2004 Eq15 energy | 1.1710 | 1.2735 | 1.3017 | **0.1026** | yes | PARTIAL CANCELLATION |
| Schubert2003 energy | 1.1710 | 1.2735 | 1.3017 | **0.1026** | yes | PARTIAL CANCELLATION |

Against the predeclared thresholds --- ROBUST at S ≤ 0.0525, PARTIAL at S ≤ 0.21, both requiring every ratio above 1 --- the operating baseline classifies as:

> **PARTIAL CANCELLATION**

The two halves of that verdict matter separately.

**The ranking survives.** Every admitted model, under every admitted fatigue law, at every profile, puts Z2 ahead of Z1. No admissible model reverses the ordering.

**The magnitude does not.** The spread across model forms is S = 0.1059 on the worst quantity, against an architecture effect of about 0.21. The extrapolation is therefore **not** the clean common-mode cancellation it was assumed to be: it cancels partially. The previous claim that it "cancels in a ratio" is withdrawn and replaced by the measured figure.

The Z2/Z1 relative life at the operating baseline is **1.17 to 1.39** across all admitted constitutive models and all admitted fatigue laws --- wider than the 1.21 to 1.38 carried before Phase 0L, and with a lower floor.

## 17.3 What the correction did to the physics

Removing the yield threshold raises the per-cycle inelastic strain, because creep now occurs below yield instead of being suppressed to exactly zero. On the same mesh and the same load history, the Z1 baseline metric rises and the architecture ratio falls from 1.2875 to 1.2000.

The mechanism is stress relaxation. With the threshold in place, the joint holds stress that the real material would have crept away; with it removed, the joint relaxes faster and reaches lower peak stresses. Z1 and Z2 do not sit at the same stress, so they do not relax by the same amount --- which is precisely why the extrapolation does not fully cancel.

## 17.4 Consequence for the board-level experiment

| model | D (law discrimination) | n per cell for Z = 3 | total packages |
|---|---|---|---|
| `M0_COARSE` | 1.6774 | 16 | 64 |
| `M0_FINE` | 1.6548 | 15 | 60 |
| `M1` | 1.6733 | 48 | 192 |
| `M1_NHI` | 1.4001 | 68 | 272 |
| `M1_NLO` | 1.9837 | 40 | 160 |

Two separate things changed, and they must not be conflated.

**The method is verified.** Run at the solver settings Phase 0K-R actually used, the incumbent model reproduces that design exactly: D = 1.4395 against its 1.4395, and n = 34 against its 34.

**A numerical correction, before any physics.** Run at the corrected solver settings, the *same* incumbent model gives D = 1.6774 and n = 16. No constitutive model changed; the inelastic-energy metric that sets w/eps was simply under-integrated before, so the Phase-0K-R design figures were biased.

**A constitutive correction on top of that.** Across all admitted models at the corrected settings, n ranges from 15 to 68 per cell. The design value is the worst case: **68 specimens per cell, 272 packages**, to reach Z = 3 at the worst observed Weibull beta of 5.1.

The binding term is not the specimen count but the simulation-uncertainty floor: the ceiling on Z sits close to the Z = 3 target, so the required n is very sensitive to the architecture effect and therefore to the constitutive model. **The 34-per-cell design does not survive Phase 0L** and the experiment stays unfrozen.
<!-- END GENERATED: architecture_comparison -->

\newpage

# 18. Toolchain

![AUDIT-FIG-11](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0l/auditfig/AUDIT_FIG_11_toolchain.png)

| Tool | Purpose | Current use | Validation role | Limitation |
|---|---|---|---|---|
| **Python 3.12** | orchestration and analysis | converter synthesis, PDN network solves, all fitting, all post-processing, report generation | implements the compact models that the FE solvers check | not a solver; every physical claim must terminate in a solver or a source |
| **CalculiX 2.23** | finite elements | thermal conduction, global thermoelasticity, local nonlinear solder | the primary physics solver | creep law limited to Norton or a user subroutine; **no Anand**; practical ceiling about 40 000 elements for this nonlinear transient class |
| **Gmsh 4.15.2** | geometry and meshing | supports mesh generation | --- | the structured package mesher is bespoke (`etm/mesh.py`), not Gmsh |
| **MOOSE** | independent FE | conduction / RDL cross-check | the independent-solver check for the sheet PDE | only `heat_transfer` is built; **no compiled `solid_mechanics` binary exists**, so MOOSE cannot check the mechanics |
| **HFSS / AEDT 2026 R1** | 3-D full-wave EM | loop impedance, AC current-crowding factor | supplies the crowding factor used by the DC interconnect model | frequency-domain; does not produce the DC geometry-resolved parasitic |
| **Icepak** | CFD thermal | attempted package cross-check | **none --- result discarded** | failed cross-validation; retained only as a recorded negative |
| **PALACE** | EM eigen/driven | installed and functional | **none claimed** | no validation result has been produced with it |
| **pandoc 2.0.6 + xelatex** | document build | Markdown to PDF | --- | closing `$` before a digit is not parsed as math; several Unicode glyphs need explicit substitution |

Two absences are as important as the presences:

- **Q3D is not licensed on this system.** No Q3D result exists anywhere in the project. The
  geometry-resolved via/pad parasitic that Q3D would extract is represented instead by a single
  HFSS-derived factor.
- **MOOSE SolidMechanics is not available as a binary.** Any statement that a better solder
  constitutive model "could be implemented in MOOSE" is therefore a plan, not a capability.

\newpage

# 19. Software and code architecture

## 19.1 Layout

```
HVR_OPT/
  configs/<phase>/        YAML inputs: stacks, architectures, DOE definitions
  scripts/<phase>/        the implementation, one directory per research phase
  results/<phase>/        generated artifacts: CSV, PNG, MD
  tests/<phase>/          the regression suite
  Scalable_Integrated_VR/ upstream converter-synthesis repository (separate git repo)
```

Phase directories are chronological, but the **live modules** --- the ones every current result
imports --- are a small subset. Those are listed below; anything not listed is historical.

## 19.2 Live modules by function

| Function | Module | Key entry points | Produces |
|---|---|---|---|
| package configuration, provenance tagging | `scripts/phase0b/etm/config.py` | `load_stack`, `build_materials`, `derive_tsv_homog` | material cards with provenance |
| structured hex mesher | `scripts/phase0b/etm/mesh.py` | `build`, `Layer`, `Mesh` | the global package mesh |
| HVR tile placement | `scripts/phase0b/etm/placement.py` | `generate`, `validate`, `legal_halfspan` | validated tile coordinates |
| metric extraction with singularity regularisation | `scripts/phase0b/etm/metrics.py` | `thermal_metrics`, `structural_metrics` | raw_max / p99 / p95 triples |
| electrical: R(T), TSV field, PDN | `scripts/phase0d/electrical.py` | `rdson_at`, `dcr_at`, `lateral_pdn`, `compile_hvr` | converter and interconnect losses |
| electrical-thermal fixed point | `scripts/phase0d/coupled.py` | `solve_et` | `ETResult` with converged T |
| RDL stack, TSV allocation, sheet PDE | `scripts/phase0e/stack.py` | `RDLStack`, `n_required`, `allocate`, `multilayer_sheet_solve`, `rdl_network_solve` | RDL loss, feasibility |
| architecture evaluation | `scripts/phase0e/architecture0e.py` | `evaluate`, `vertical_tier_per_regulator` | per-architecture electrical result |
| geometry realizability gate | `scripts/phase0f/geometry.py` | `cell_stack`, `check`, `fitting_inductors` | `Realizability` verdict |
| 1 kW reference assembly | `scripts/phase0f/kw1.py` | `design_1kw`, `coupled_1kw`, `thermal_structural` | the reference-scale result |
| scope and unit guards | `scripts/phase0h/scope.py` | `Q`, `watts_system`, `total`, `ScopeError` | typed electrical quantities |
| Z-architecture rails and realizability | `scripts/phase0i/zarch.py` | `rail_currents`, `tsv_rail`, `realizable` | which rail crosses what |
| per-architecture electrical | `scripts/phase0i/zpower.py` | `evaluate_z` | SYSTEM-scope loss per architecture |
| per-architecture global mechanics | `scripts/phase0i/zglobal.py` | `stack_for`, `corner_joint_response` | $\Delta u(t)$, $T(t)$ at the critical joint |
| solder material card | `scripts/phase0i/solder_model.py` | `fit_norton_data`, `norton_at`, `calculix_cards`, `inp_material` | the SAC305 `*MATERIAL` block |
| local joint model | `scripts/phase0i/joint.py` | `build_joint`, `write_inp`, `run`, `cycle_metric` | the joint deck and its result |
| graded joint with Syed layers | `scripts/phase0jr/graded_joint.py` | `build_joint_graded`, `solder_z` | refined mesh, `ESYED` sets |
| cycle post-processing | `scripts/phase0ir/cycle_audit.py` | `per_element_series`, `cycle_quantities` | M1, M2, M3 per cycle |
| creep metric reconstruction | `scripts/phase0jr/creep_metric.py` | `norton_at_T`, `yield_at`, `driving_stress` | analytic cross-checks |
| report build and verification | `scripts/phase0dr/build_pdf.py` | `build`, `sanitise`, `repair_markdown` | the historical report PDF plus 89 checks |

## 19.3 Phase-0L modules

| Module | Purpose | Output |
|---|---|---|
| `scripts/phase0l/calculix_creep_probe.py` | single-element probes TEST A-H | `calculix_creep_probe.csv` |
| `scripts/phase0l/original_fit_audit.py` | audit of the 19-point fit | `original_19point_fit.csv` |
| `scripts/phase0l/refit.py` | FIT-A vs FIT-B | `refit_comparison.csv` |
| `scripts/phase0l/card_grid_audit.py` | card temperature-grid error | `card_temperature_grid_audit.csv` |
| `scripts/phase0l/lit_search.py` | open-API literature search | `lit/raw_hits.json` |
| `scripts/phase0l/candidate_laws.py` | M0/M1/M2/M3 constitutive forms | --- |
| `scripts/phase0l/model_validation.py` | source-data reproduction tests | `high_stress_model_comparison.csv` |
| `scripts/phase0l/constitutive_domain.py` | all six properties x three profiles | `complete_constitutive_domain.csv` |
| `scripts/phase0l/replay.py` | the package replay harness | --- |
| `scripts/phase0l/run_replay_all.py` | default-control replay driver | `package_model_replay.csv` |
| `scripts/phase0l/run_replay_tight.py` | tight-control re-runs and the settings control | `package_model_replay_tight.csv` |
| `scripts/phase0l/common_mode.py` | the Z2/Z1 cancellation test | `common_mode_cancellation_test.csv` |
| `scripts/phase0l/experiment_reaudit.py` | experiment design re-audit | `experiment_reaudit.csv` |
| `scripts/phase0l/make_figures.py` | FIG-0L-A..H | `FIG_0L_*.png` |
| `scripts/phase0l/audit_figures.py` | AUDIT-FIG-1..13 | `auditfig/AUDIT_FIG_*.png` |
| `scripts/phase0l/build_audit_report.py` | this document | the report MD and PDF |

## 19.4 Code flow

```
configs/*.yaml
     |
     v
 etm/config.py  --------> materials with provenance
     |
     v
 zarch.py (rails, realizability)
     |
     v
 zpower.py  <---->  scope.py (PER_REGULATOR vs SYSTEM, ScopeError)
     |
     v
 electrical.py + stack.py  (converter loss, TSV field, RDL sheet PDE)
     |
     v
 coupled.py :: solve_et   <-------+   fixed point on R(T)
     |                            |
     v                            |
 etm/mesh.py -> CalculiX thermal --+
     |
     v
 zglobal.py  (global thermoelastic, BC-A)  -> du(t), T(t)
     |
     v
 graded_joint.py + joint.py -> CalculiX *VISCO local solve
     |
     v
 cycle_audit.py  -> M1 / M2 / M3 on the 25 um ESYED layers
     |
     v
 fatigue law (Syed / Schubert)  -> N_f  [CONDITIONAL]
     |
     v
 N_required  [OPEN]  -> G2  [NOT TESTED]
```

\newpage

# 20. Unit and scope contracts

The framework has been bitten by unit and scope errors that dimensional analysis cannot catch,
because the wrong quantity had the right units. Three structural protections are now in place.

## 20.1 Electrical scope

Described in Section 9.3. Every electrical power is tagged `PER_REGULATOR` or `SYSTEM`; `total()`
raises `ScopeError` on a mismatch; conversion is explicit, by $n_{vr}$. This exists because
adding a per-regulator tier loss to a system-scope RDL loss understated every vertical tier by
$n_{vr}$ --- 4x at 240 W, 49x at 1 kW --- with both operands correctly in watts.

## 20.2 The three via counts

Described in Section 6.2. `n_required`, `n_allocated` and `n_available` are separate quantities
with separate names, and resistance uses `n_allocated`. The failure mode this prevents is silent:
using `n_required` makes a design look simultaneously feasible and low-resistance.

## 20.3 Rail voltage

Which rail crosses which interconnect is a property of the **architecture**, not a global
constant. `zarch.rail_currents` and `zarch.tsv_rail` derive it per architecture. The failure mode
this prevents is applying Z1's 20.8 A to Z2's TSV field, which would understate Z2's penalty by
about 1960x and reverse the architecture ranking outright.

## 20.4 Temperature reference

Two distinct references exist and must not be confused: the **stress-free reference temperature**
for thermal strain, and the **`*EXPANSION, ZERO=`** datum of the CalculiX card. They are set
consistently in `write_inp(..., t_ref_c=...)`; the thermal strain applied is
$\alpha(T - T_{zero})$ differenced against the same expression at the initial temperature.

## 20.5 Assertions that are load-bearing

| Assertion | Where | What it prevents |
|---|---|---|
| mapped heat integral equals electrical loss | heat-source mapping | losing or inventing power in the interpolation |
| tiles do not overlap and stay in the legal region | `placement.validate` | a layout that is geometrically impossible |
| total footprint and heat-source integral preserved across placements | `placement.validate` | comparing placements that are not the same design |
| `n_required <= n_allocated <= n_available` | `stack.allocate` | reporting an infeasible point as merely lossy |
| ET fixed point converged | `coupled.solve_et` | reporting an unconverged iterate as a result |
| scope match | `scope.total` | adding per-regulator to system watts |

\newpage

# 21. Validation matrix

The word in the STATUS column is chosen precisely. **VALIDATED** means compared against an
independent measurement or an independent solver and found to agree within a stated criterion.
**CROSS-CHECKED** means compared against a second computation of the same thing. **CONDITIONAL**
means it holds only under assumptions that are not themselves established. **NOT VALIDATED**
means what it says.

![AUDIT-FIG-12](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0l/auditfig/AUDIT_FIG_12_validation_ladder.png)

| Model block | What was checked | Reference | Error | Pass criterion | Status | Known gap |
|---|---|---|---|---|---|---|
| converter loss | reimplementation reproduces the upstream model | upstream `DVPDRoutingModel` | numerically identical by unit test | bit-level agreement | **CROSS-CHECKED** | no measurement of a built converter exists in this project |
| vertical interconnect | $R = \rho L / A$ against sourced unit resistances | reference system Table III | consistent | agreement with source values | **CROSS-CHECKED** | contact resistance and pad crowding are a single factor, not resolved geometry; Q3D unavailable |
| RDL multilayer sheet | compact sheet solver vs independent FE | MOOSE `heat_transfer` | per-case, reported in `results/phase0e/` | agreement across placements | **VALIDATED (solver)** | validates the PDE solution, not the sheet conductance value |
| HFSS AC behaviour | loop impedance and crowding factor | HFSS 3-D full-wave | --- | --- | **CROSS-CHECKED** | frequency-domain only; the DC parasitic is inferred |
| thermal conduction | CalculiX vs independent FE | MOOSE `heat_transfer` | agrees | agreement on the same operator | **VALIDATED (solver)** | Icepak cross-check **failed and was discarded** |
| thermal absolute level | cooling coefficient calibrated to the design junction temperature | --- | exact by construction | --- | **CALIBRATED** | absolute temperature is anchored, not predicted; only differences are meaningful |
| global mechanics | mesh convergence, singularity regularisation | internal | p99 vs p95 | metric not mesh-sensitive | **CROSS-CHECKED** | no warpage measurement to compare against |
| local solder mesh | Syed's 25 μm averaging volume reproduced exactly | Syed 2004 | geometry matched | two elements per 12.5 μm | **VALIDATED (against source geometry)** | --- |
| **creep implementation** | what CalculiX integrates, from source and probe | CalculiX 2.23 source; 7603 probe increments | median $1.2\times10^{-5}$ | law identified to 5 significant figures | **VALIDATED** | --- |
| **creep CARD** | does the card reproduce its own source data? | Yuan 2023 Table 5, 19 points | **0 of 19 reproduced** | reproduce the calibration set | **FAILS** | see Section 13.8; wrong variable, and wrong alloy |
| fatigue law, relative | ratio robustness across admitted laws | Syed 2004, Schubert 2003 | ranking preserved | same ordering under every law | **CONDITIONAL** | conditional on the constitutive model |
| fatigue law, absolute | --- | --- | 4.1x model-form spread | --- | **NOT VALIDATED** | needs a package-specific calibration experiment |
| mission requirement | --- | --- | --- | --- | **OPEN** | no source exists |

The row that changed in Phase 0L is "creep CARD". It was previously carried as calibrated; the
audit showed that the calibration cannot be reproduced through the solver, so it now reads
FAILS. The row above it, "creep implementation", is the opposite: what the solver does is now
known exactly, to five significant figures.

\newpage

# 22. Uncertainty budget

Errors are separated by kind, because they behave differently in a ratio.

## 22.1 Numerical

| Source | Size | Common mode? |
|---|---|---|
| mesh discretisation in the joint | controlled by p99/p95 agreement and mesh convergence | largely yes |
| time discretisation, **strain** metric M1 | 0.41 % worst case between default and tight solver control | yes |
| time discretisation, **energy** metric M3 | **+11 % to +24 %** under tighter control --- the default start under-resolves the fast transient at the beginning of each half-cycle, where most inelastic work is deposited | **no** --- it shifts the energy ratio by up to 6 % |
| final-cycle output artefact | about 15 %, **removed** by discarding the last cycle | yes |
| card temperature grid | **0.83x to 3.88x** between rows; up to 8.70x clamped above 125 °C | mostly, but profile-dependent |

**The energy row deserves emphasis.** M1 and M3 are not equally trustworthy numerically. The
accumulated-strain metric is converged with respect to time discretisation; the inelastic-energy
metric is not, at the settings used before Phase 0L. Because energy is an integral
$\oint \boldsymbol{\sigma}:d\boldsymbol{\varepsilon}_{in}$ accumulated over output
increments, coarse stepping through the stress peak at the start of each half-cycle simply
misses work that a finer sweep captures. Every Phase-0L comparison is therefore run at one
uniform, tighter solver setting, and the analysis scripts **refuse to compare runs whose solver
control differs** --- otherwise a purely numerical difference would appear as model-form spread.

## 22.2 Parameter

| Source | Size | Common mode? |
|---|---|---|
| Norton exponent $n$ | $\pm 2\,\mathrm{SE}$ is $\pm 9.8$ % on $n$, which is 0.09x to 11x on rate at 90 MPa | yes, if the architectures sit at similar stress |
| $E(T)$ slope | assumption, swept as a corner | yes |
| CTE | assumption, swept as a corner | yes |
| $\nu$ | assumption, not swept | yes |
| cooling coefficient | calibrated | yes |

## 22.3 Model form --- the dominant term

| Source | Size | Common mode? |
|---|---|---|
| **high-stress constitutive law** | candidate laws that all fit the low-stress data to within 2.6x diverge by **$10^{6}$ to $10^{16}$** at 20 to 120 MPa | **tested, not assumed --- Section 17** |
| creep alloy mismatch (Sn3.9Ag0.6Cu vs SAC305) | unquantified; no transferability data exists | probably yes, but unverifiable |
| yield threshold present or absent | changes the per-cycle metric materially; see Section 17 | **tested** |
| fatigue law family (strain vs energy) | 4.1x on absolute life | **no** --- the two families rank architectures differently |
| fatigue law exponent | 1.0 to 1.3 across admitted laws | no |

## 22.4 Which errors cancel and which do not

This is the crux of the whole argument, so it is worth stating carefully.

An error **cancels in a ratio** if it multiplies both architectures by the same factor. An error
that depends on the stress level, the temperature, or the shape of the cycle does **not**
necessarily cancel, because the two architectures do not sit at the same stress, temperature or
cycle shape --- that is precisely why they differ.

The high-stress constitutive extrapolation was *assumed* common mode before Phase 0L. Section 17
reports the result of actually testing it against a tolerance fixed in advance.

## 22.5 Architecture and mission

| Source | Status |
|---|---|
| which architectures are physically realisable | Z1 is SOURCE-DESCRIBED but NOT DEMONSTRATED; the source calls substrate-embedded active integration "an open challenge" |
| $N_{required}$ | OPEN, no source |
| failure mechanisms not modelled | electromigration, delamination, CPI, dielectric --- none are bounded |

\newpage

# 23. Current assumptions and open items

| Item | Status | Why it is open | Potential impact | What would close it |
|---|---|---|---|---|
| high-stress SAC305 constitutive response | **OPEN** | no retrievable primary data above about 16 MPa at 45 to 150 °C; the corpus exists but is paywalled | dominant; sets the model-form term in the uncertainty budget | institutional access to the ITherm / ECTC / IPACK SAC305 Anand and high-strain-rate papers listed in `high_stress_sac305_sources.csv` |
| creep data alloy (Sn3.9Ag0.6Cu, not SAC305) | **OPEN** | the only retrievable creep dataset is a different alloy | unquantified bias on every creep-derived number | SAC305 creep data at 45 to 150 °C, or a published SAC305/SAC396 comparison |
| absolute life calibration | **OPEN** | the fatigue-law prefactor is package-specific | 4.1x spread on $N_f$ | the board-level experiment of Section 23.1 |
| $N_{required}$ | **OPEN** | no product requirement exists | G2 cannot be evaluated at all | the system owner answering `SYSTEM_OWNER_MISSION_REQUEST.md` |
| MLCC height | ASSUMPTION | not sourced | affects the Z1 cell stack and hence substrate thickness | a part selection |
| manufacturing clearance | ASSUMPTION | not sourced | affects realizability verdicts | a process constraint from an assembly house |
| electromigration criterion | **NOT MODELLED** | out of scope by decision | a 1000 A rail is an obvious EM concern | an EM model and a current-density limit |
| RDL dielectric and stitching detail | simplified | stack is sourced, but via stitching between layers is idealised | modest on RDL loss | a real routing floorplan |
| assembly prestress and reflow residual stress | **NOT MODELLED** | no data | unknown sign and size on joint life | measurement or a process model |
| delamination, CPI, dielectric failure | **NOT MODELLED** | out of scope by decision | unbounded | separate mechanism models |
| Icepak package thermal | **DISCARDED** | failed cross-validation | none, it is unused | a corrected Icepak model, or accept MOOSE as the only independent thermal check |
| Q3D parasitic extraction | **UNAVAILABLE** | not licensed on this system | via/pad parasitic rests on one HFSS-derived factor | a Q3D licence |
| $E(T)$ slope, $\nu$, CTE for SAC305 | ASSUMPTION | no source for the temperature dependences | swept as corners; ranking robust to the sweeps performed | sourced temperature-dependent properties |

## 23.1 The board-level experiment

A four-cell experiment is designed and costed: Z1 and Z2, two thermal profiles (45 to 125 °C and
110 to 150 °C, 5-minute dwells, 3 °C/min), 34 specimens per cell, 136 packages total.

It is **not frozen**. Seven of the eight acceptance criteria pass; the criterion that fails is
"stress inside or defensibly near the calibration domain", and Section 13.7 explains why **no**
profile can satisfy it: the package leaves the calibration stress window in every profile,
including the operating baseline. Section 17 reports whether the Phase-0L constitutive work
changes the effect size and therefore the specimen count.

\newpage

# 24. Current claims --- what can and cannot be said

| DEFENSIBLE TODAY | NOT DEFENSIBLE TODAY |
|---|---|
| Vertical placement of the converter changes both the electrical path and the local solder response, and the two trade against each other. | "Z2 has X cycles of life." No absolute life is defensible. |
| Moving conversion below the substrate puts the 1 V rail on the TSVs, costing about 1960x on TSV $I^2R$ and +1.688 W of system loss, which is +1.3 %. | "The solder model is valid for this package." It is evaluated 3.4x to 7.2x outside its fitted stress window. |
| Z2's thinner substrate and its converter's position relative to the neutral plane reduce the per-cycle inelastic strain in the critical joint relative to Z1. | "The creep law is SAC305." Its data is Sn3.9Ag0.6Cu. |
| The ordering Z2 better than Z1 is preserved under every fatigue law admitted, because the law's constant cancels in a ratio. | "The 3.4x to 7.2x stress extrapolation is common mode and cancels." Section 17 reports the measured result of testing this. |
| What CalculiX integrates for this material card is known exactly and confirmed to five significant figures. | "There is plastic and creep strain in the joint." There is one viscoplastic strain; rate-independent plasticity never executes. |
| The RDL sheet PDE solution agrees with an independent FE solver. | "The thermal model is validated against CFD." The Icepak cross-check failed and was discarded. |
| The framework can rank Z1, Z2 and Z4 at a stated reference condition. | "Architecture X passes qualification." G2 is NOT TESTED and $N_{required}$ is OPEN. |
| Z4 is not resolved against Z1: its ratio sits at 0.94 to 0.98, which is inside the model-form spread. | "Z4 is worse than Z1." The difference is not resolved. |

\newpage

# 25. Reproducibility

All commands are run from the repository root,
`/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT`, with the conda environment at
`/home/beams0/MGHARIB/envs/etm` on `PATH` (this provides `ccx` 2.23 and Python 3.12).

```bash
export PATH=/home/beams0/MGHARIB/envs/etm/bin:$PATH
cd /home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT
```

| Task | Command | Expected output |
|---|---|---|
| one electrical architecture solve | `python3 scripts/phase0i/run_zcompare.py` | per-architecture loss table; `results/phase0i/` |
| one ET fixed point | `python3 scripts/phase0f/kw1.py` | converged temperatures and the 1 kW loss breakdown |
| one thermal FE solve | invoked inside the above; the deck is written to `results/phase0f/` and solved with `ccx -i <case>` | `.dat` and `.frd` for the case |
| one global mechanical solve | `python3 scripts/phase0i/run_zcompare.py` | $\Delta u(t)$, $T(t)$ at the critical joint |
| one local solder solve | `python3 scripts/phase0l/replay.py M1 Z1 OP_BASELINE` | a dict with `d_peeq_per_cycle`, `range_eq_inelastic`, `inelastic_work_MJ_per_m3` |
| the full Phase-0L replay | `python3 scripts/phase0l/run_replay_all.py` | `results/phase0l/package_model_replay.csv`, 35 runs, about one hour |
| solver-law probes | `python3 scripts/phase0l/calculix_creep_probe.py` | `results/phase0l/calculix_creep_probe.csv`, 7603 increments |
| fatigue post-processing | `python3 scripts/phase0l/common_mode.py` | `results/phase0l/common_mode_cancellation_test.csv` |
| full regression suite | `python3 -m pytest tests/ -q` | the current test count, all passing |
| historical report build | `python3 scripts/phase0dr/build_pdf.py` | `results/ETM_DVPD_FULL_TECHNICAL_REPORT.pdf` plus its verification checks |
| this report | `python3 scripts/phase0l/build_audit_report.py` | this document and its PDF |

**Where an exact command cannot be given.** The MOOSE RDL cross-check
(`scripts/phase0e/validate_moose_rdl.py`) hard-codes a binary path in another user's home
directory, `/home/beams0/LPOPRYHO/projects/moose/modules/heat_transfer/heat_transfer-opt`. It
will not run for a different user without editing that path, and no portable invocation is
offered here because none has been verified. The HFSS and Icepak runs were performed
interactively in AEDT and are not scripted in this repository; their results enter as recorded
numbers, and the Icepak result is not used at all.

\newpage

# 26. Auditor checklist

Each item is phrased so that it can be checked against a named artifact rather than against
prose.

**Electrical**

- [ ] Rail assignment verified per architecture --- `zarch.tsv_rail` returns 48 V for Z1/Z4 and 1 V for Z2
- [ ] Supply and ground both included in every vertical loop, not supply doubled
- [ ] `n_allocated`, not `n_required`, used in every resistance
- [ ] `n_required <= n_allocated <= n_available` enforced, and infeasible points raise rather than return
- [ ] Every power quantity carries a scope tag; `total()` raises on a mismatch
- [ ] Energy balance: mapped heat integral equals electrical loss

**Thermal**

- [ ] ET fixed point converged, and a non-converged candidate is rejected rather than reported
- [ ] Temperature field transferred to the mechanical model without resampling error
- [ ] Cooling coefficient is calibrated, so only temperature *differences* are used in conclusions

**Mechanical**

- [ ] Global-to-local displacement transfer checked at the critical joint
- [ ] Critical joint is the outermost corner, and that choice is stated
- [ ] Extraction volume is two 25 μm layers, two elements each --- matching the fatigue law's calibration
- [ ] No raw maximum reported as a result; p99 headline with p95 agreement
- [ ] Stabilised cycle is cycle 5 of 6, with cycle 6 discarded and the reason stated

**Constitutive**

- [ ] The law the solver integrates is the law the report states --- re-run `calculix_creep_probe.py`
- [ ] Card temperature grid spans every profile, with no clamping
- [ ] Calibration domain versus operating domain stated in both temperature **and** stress
- [ ] The card reproduces its own source data --- **this currently FAILS; confirm the report says so**
- [ ] Alloy of every dataset stated explicitly

**Fatigue and decision**

- [ ] Fatigue law's metric matches the metric extracted (accumulated vs range; strain vs energy)
- [ ] Relative and absolute life never conflated in any sentence
- [ ] Mission criterion sourced, or explicitly marked OPEN
- [ ] Current claims match code outputs --- spot-check any number in Section 17 against the CSV it cites

\newpage

# 27. Symbol table

| Symbol | Meaning | Units |
|---|---|---|
| $A$ | Norton creep coefficient | MPa$^{-n}$ s$^{-1}$ |
| $A_{via}$ | cross-sectional area of one via | m2 |
| $\mathbf{C}$ | fourth-order elastic stiffness tensor | MPa |
| $C_{oss}$ | device output capacitance | F |
| $D$ | duty ratio (Section 5); bending stiffness (Section 11) | ---; N m |
| $E$ | Young's modulus | MPa |
| $E_{oss}$ | energy stored in $C_{oss}$ | J |
| $f_{sw}$ | switching frequency | Hz |
| $h$ | convective heat transfer coefficient | W m$^{-2}$ K$^{-1}$ |
| $h_{sub}$ | substrate thickness | μm |
| $I_{rms}$ | RMS device current | A |
| $J$ | areal current density injected into the RDL sheet | A m$^{-2}$ |
| $J_{max}$ | per-via current-density limit | A m$^{-2}$ |
| $\mathbf{K}$ | thermal conductivity tensor | W m$^{-1}$ K$^{-1}$ |
| $k$ | fatigue-law exponent | --- |
| $L$ | conductor length (Section 7); inductance (Section 5) | m; H |
| $m$ | Norton time-hardening exponent (**$m = 0$ here**) | --- |
| $N_f$ | cycles to failure | cycles |
| $N_{required}$ | cycles the product must survive | cycles |
| $n$ | Norton stress exponent | --- |
| $n_{alloc}$, $n_{avail}$, $n_{req}$ | vias allocated / available / required | --- |
| $n_{vr}$ | number of voltage-regulator cells | --- |
| $P$ | power | W |
| $Q_g$ | gate charge | C |
| $q$ | volumetric heat source | W m$^{-3}$ |
| $R_{DS(on)}$ | device on-state resistance | Ω |
| $T$, $T_j$, $T_{\infty}$ | temperature, junction temperature, coolant temperature | °C or K |
| $t_r$, $t_f$ | switching rise and fall times | s |
| $V$ | electric potential | V |
| $w_{acc}$ | accumulated inelastic energy density per cycle | MJ m$^{-3}$ |
| $z_{NA}$ | neutral-axis height | μm |
| $\alpha$ | coefficient of thermal expansion | K$^{-1}$ |
| $\alpha_{Cu}$, $\alpha_{GaN}$ | resistance temperature coefficients | K$^{-1}$ |
| $\beta$ | Weibull shape parameter | --- |
| $\Delta u$ | relative in-plane displacement across the joint standoff | μm |
| $\varepsilon_{th}$, $\varepsilon_{el}$, $\varepsilon_{in}$ | thermal, elastic and inelastic strain | --- |
| $\bar{\varepsilon}_{in}$ | equivalent accumulated inelastic strain (PEEQ) | --- |
| $\varepsilon_{acc}$ | accumulated inelastic strain per cycle, the M1 metric | --- |
| $\eta$ | Weibull characteristic life | cycles |
| $\nu$ | Poisson ratio | --- |
| $\rho$, $\rho_{Cu}$ | electrical resistivity | Ω m |
| $\boldsymbol{\sigma}$, $\sigma_{vm}$ | stress tensor, von Mises stress | MPa |
| $\sigma_y$, $\sigma_0$ | yield stress, initial yield stress | MPa |
| $\sigma_s$ | sheet conductance of an RDL layer | S per square |

\newpage

# 28. Glossary

**Anand model.** A unified viscoplastic constitutive model with a single internal state variable
representing deformation resistance. Widely used for solder. **CalculiX does not implement it.**

**BC-A / BC-B.** The two boundary-condition treatments used historically for the global package
model. BC-A includes an explicit BGA array and PCB and is the only one used now; BC-B was a rigid
clamp and is superseded.

**Chaboche model.** A plasticity model with combined isotropic and kinematic hardening. Here it
is the source of the temperature-dependent yield stress that the creep law uses as a threshold.

**Creep.** Time-dependent irreversible deformation under sustained load. **Plainly:** if you hang
a weight on solder and leave it, the solder keeps stretching even though the weight never changes.

**CTE mismatch.** Two bonded materials with different thermal expansion coefficients cannot both
have their natural length when heated, so both end up strained and the assembly bends. The origin
of every stress in this package.

**DVPD.** Distributed vertical power delivery: converting close to the load and routing power
vertically through the package rather than laterally.

**Elastic strain.** Reversible deformation. Remove the load and it disappears.

**Garofalo (hyperbolic-sine) law.** A creep law
$\dot{\varepsilon} = C_1 [\sinh(C_2\sigma)]^{C_3} e^{-Q/RT}$
that behaves as a power law at low stress and exponentially at high stress.

**HVR.** Hybrid voltage regulator: a switched-capacitor stage followed by a multiphase buck.

**Inelastic energy density.** The area enclosed by the stress-strain loop over one cycle; the work
that went into permanent deformation rather than being stored elastically. Units MJ/m3.

**Neutral axis.** The height in a layered plate at which in-plane strain is unaffected by bending.
Which side of it a stiff layer sits on determines which way the plate warps.

**Norton law.** A power-law creep model, $\dot{\varepsilon} = A\sigma^{n}$. Simple, and the only
built-in creep law CalculiX offers.

**Overstress model.** A viscoplastic formulation in which the creep rate is driven by the
*excess* of stress over a threshold, $(\sigma - \sigma_y)$, and is exactly zero below it. **This
is what CalculiX integrates**, and it is not what the `*CREEP` manual page says.

**PEEQ.** Accumulated equivalent inelastic strain. **Plainly:** an odometer, not a position --- it
counts deformation travelled in both directions and never decreases.

**Plastic strain (rate-independent).** Permanent deformation that occurs above a yield stress and
does not depend on how long the load is held. **This model contains none** --- see Section 13.4.

**Relative vs absolute life.** Relative life is a ratio between two designs and survives the
cancellation of unknown constants. Absolute life is a number of cycles and does not.

**Stabilised cycle.** The cycle after which the per-cycle response stops changing appreciably.
Here, cycle 5 of 6.

**Stress relaxation.** Stress falling over time at fixed displacement, because creep converts
elastic strain into permanent strain. The mechanism that limits how high joint stresses go during
a dwell.

**Submodelling.** Solving a coarse global model, then re-solving a small region in detail driven
by the global model's boundary displacements.

**TSV.** Through-silicon (or through-substrate) via: a vertical conductor through the substrate.

**Warpage.** Out-of-plane deflection of the package caused by CTE mismatch. Directly measurable
by shadow moire, which makes it the most checkable mechanical output.

**Weibull beta.** The shape parameter of the Weibull failure distribution. Higher beta means a
tighter spread of failure times and hence fewer specimens needed for the same confidence.
