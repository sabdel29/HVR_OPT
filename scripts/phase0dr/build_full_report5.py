#!/usr/bin/env python3
"""Append sections 18-20 (novelty, defensible claims, roadmap) + references."""
from __future__ import annotations
import textwrap
from pathlib import Path

RES = Path(__file__).resolve().parents[2] / "results"
MD = RES / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
S = []
A = S.append

A("\\newpage\n# Novelty Relative to Prior Work\n")
A(textwrap.dedent("""
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
budget $w_{LS}^{max} = A_{budget}/(M\\max\\{l_{ind},l_{LS}\\})$. Mechanics can therefore delete,
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
"""))

A("# Publication-Defensible Claims\n")
A(textwrap.dedent("""
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
   simultaneously*, with $w \\propto h^{-1.95\\pm0.02}$ independent of placement to within
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
"""))

A("\\newpage\n# Next Steps --- prioritised roadmap\n")
A(textwrap.dedent("""
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
   with warpage as an $\\varepsilon$-constraint whose level the *user* sets --- which removes the
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

"""))

A("\\newpage\n# References\n")
A(textwrap.dedent("""
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
"""))

MD.write_text(MD.read_text() + "".join(S))
print(f"appended sections 18-20 + references; total {len(MD.read_text().splitlines())} lines")
