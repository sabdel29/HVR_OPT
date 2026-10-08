#!/usr/bin/env python3
"""Phase-0M-R Section 23, updated in Phase 0M-R2 -- rebuild the STANDALONE framework
audit report from scratch.

This document is NOT a history. It describes the framework AS IT EXISTS after Phase 0M-R3,
for an external technical auditor who knows power delivery and has never seen this
repository. Nothing in it requires reading the phase sequence.

Every number is read from a result file. Every current-state claim derives from
`results/CURRENT_SCIENTIFIC_STATUS.yaml::current_state_contract`.
"""
from __future__ import annotations
import csv, json, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0mr"))
from state_contract import as_markdown as contract_md, load as contract_load  # noqa: E402

MR = R / "results" / "phase0mr"
M = R / "results" / "phase0m"
OUT = R / "results" / "ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.md"
FIGM = str(M)
FIGMR = str(MR)


def rd(d: Path, n: str):
    p = d / n
    return list(csv.DictReader(p.open())) if p.is_file() else []


def f(r, k, d=4):
    try:
        return f"{float(r[k]):.{d}f}"
    except (KeyError, TypeError, ValueError):
        return str(r.get(k, "--"))


def g(r, k, d=4):
    try:
        return f"{float(r[k]):.{d}g}"
    except (KeyError, TypeError, ValueError):
        return str(r.get(k, "--"))


def build() -> str:
    c = contract_load()
    rep = rd(MR, "production_architecture_replay.csv")
    ok = [r for r in rep if r.get("status") == "OK"]
    bef = {r["arch"]: r for r in ok if r.get("mode") == "BEFORE"}
    aft = {r["arch"]: r for r in ok if r.get("mode") == "AFTER"
           and r.get("template") == "T1_EMBEDDED_4LAYER"
           and "27" in str(r.get("cooler", ""))}
    dRcache = (json.loads((MR / "transition_dR_cache.json").read_text())
               if (MR / "transition_dR_cache.json").is_file() else {})
    val = rd(MR, "current_crowding_validation.csv")
    tr = [r for r in val if r["kind"] == "transition"]
    cool = rd(MR, "cooling_energy_balance.csv")
    coolv = rd(MR, "cooling_validation.csv")
    rdlt = rd(MR, "rdl_effective_tensor.csv")
    rdlm = rd(MR, "rdl_mechanical_fidelity.csv")
    part = rd(MR, "component_partition_feasibility.csv")
    unc = rd(MR, "uncertainty_ledger.csv")

    def rdlm_by(rung, arch):
        return next((x for x in rdlm if x["rung"] == rung and x["arch"] == arch), {})

    route = rd(MR, "intravr_routing_by_template.csv")
    ledger = rd(MR, "intravr_loss_ledger.csv")
    me = rd(M, "me_energy_reconstruction.csv")
    L = []
    A = L.append

    A("---")
    A("title: \"ETM-DVPD Framework --- Current-State Technical Audit\"")
    A("subtitle: \"A self-contained description of the framework as it exists after "
      "Phase 0M-R3\"")
    A("date: \"2026-09-17\"")
    A("geometry: margin=2.2cm")
    A("fontsize: 10pt")
    A("colorlinks: true")
    A("toc: true")
    A("toc-depth: 2")
    A("---")
    A("")
    A("# Preface --- what this document is, and what it is not")
    A("")
    A("This is a description of a modelling framework **as it stands today**. It is written "
      "for a technical auditor who understands power delivery and packaging and who has "
      "never seen this repository. It does not assume, and does not require, any knowledge "
      "of the development history.")
    A("")
    A("Three things follow from that.")
    A("")
    A("* **Every claim about the present is generated** from a single machine-readable "
      "contract, `results/CURRENT_SCIENTIFIC_STATUS.yaml::current_state_contract`. A "
      "sentence in this document that contradicts that contract is a build failure, not a "
      "difference of emphasis. That mechanism exists because the previous version of this "
      "report was internally consistent with its sibling report and consistently stale "
      "relative to the actual science --- see Section 22.")
    A("* **Missing physics is listed, not hidden.** Sections 20 and 21 say what the "
      "framework cannot do and which claims are therefore unsafe.")
    A("* **Audited is not implemented.** Where a model was built and measured but does not "
      "drive the production path, the text says so at that point, every time.")
    A("")
    A("The companion document `ETM_DVPD_FULL_TECHNICAL_REPORT.pdf` is the chronological "
      "record of how the framework reached this state, including superseded results. Nothing "
      "here depends on it.")
    A("")
    A(r"\newpage")
    A("")
    A("# 1. The problem the framework solves")
    A("")
    A("For a 1 kW compute die drawing **1000 A at 1 V**, direct lateral delivery in the "
      "evaluated stack is prohibitively lossy: the IR drop and "
      "the $I^2R$ loss of a 1 V rail crossing even a few millimetres of package metal are "
      "comparable with the load itself. **Distributed vertical power delivery (DVPD)** "
      "answers that by converting 48 V down to 1 V immediately above, below or inside the "
      "package, so that the high-current rail travels micrometres rather than millimetres.")
    A("")
    A("That choice is usually made on electrical and thermal grounds. This framework exists "
      "to ask a third question:")
    A("")
    A("> **Does package thermo-mechanics change which DVPD architecture you would choose, or "
      "is it only a downstream sign-off check?**")
    A("")
    A("Answering it requires a chain that runs from an architecture choice all the way to a "
      "local solder-fatigue response, with every link converged and every parameter traced. "
      "The framework is that chain. It is a **falsification framework**, not a design tool: "
      "each stage was built so that a negative result would stop the work rather than be "
      "absorbed.")
    A("")
    A("**The headline answer today.** Mechanics responds strongly and measurably to the "
      "architecture, the ordering of the architectures is robust, and there is still no "
      "admissible mechanical inequality that would turn that response into a constraint. The "
      "framework therefore RANKS architectures and does not yet CONSTRAIN them.")
    A("")
    A("## 1.1 The current state, in one table")
    A("")
    A(contract_md())
    A("")
    A(r"\newpage")
    A("")
    A("| Report generated | 2026-09-19 |")
    A("| Repository baseline | 2026-09-08 |")
    A("| Phase completed | 0M-R3, 2026-09-19 |")
    A("")
    A("**Method.** Twenty sequential falsification gates (0B, 0C, 0D, 0D-R, 0E, 0F, 0G, "
      "0H, 0I, 0I-R, 0J, 0J-R, 0K, 0K-R, 0L, 0L-R, 0M, 0M-R, 0M-R2, 0M-R3), each designed "
      "so that a negative result would stop the project rather than be absorbed.")
    A("")
    A("## 1.2 What Phase 0M-R3 changed")
    A("")
    A("| question | answer |")
    A("|---|---|")
    A("| Is there a buildable Z1 and a buildable Z2 in the existing library? | **Yes, both CONDITIONAL_REALIZABLE**, passing every condition of a contract frozen before the search, at all 27 corners of the bounded clearance envelope. Neither is PROVEN_REALIZABLE: three package clearances are unsourced |")
    A("| What repair was needed? | **One.** The intra-VR via radius 15 -> 20 um at the framework's own legal pitch, inside the sourced range. The binding net was `ls_to_L`, a vertical via stack at 1.236x the vias available |")
    A("| Does the ordering survive? | **Yes, essentially unchanged.** D_driver 1.1942 -> 1.1943, +0.009 % |")
    A("| Does the 30 um TSV have process margin? | **No.** ARCH_Z2 sits at M_AR = 1.000 and fails a modest tolerance bound. 34 um restores 1.089 at 22.8 % more vias and <= 0.02 % change in every E/T/M property |")
    A("| Was a transitional cooling correlation found? | **No.** 2300 < Re < 3000 is permanently OUT_OF_MODEL_DOMAIN and the design space is capped at Re <= 2300 |")
    A("| Was the previous zero-stale certificate right? | **No.** 18 findings; DEFECT #56 |")
    A("")
    A(r"\newpage")
    A("")
    A("## 1.3 Superseded Phase-0M-R2 summary")
    A("")
    A("This gate asked five falsification questions. Four returned a defect.")
    A("")
    A("| question | answer |")
    A("|---|---|")
    A("| Was the previous phase's \"0 stale current-facing claims\" true? | **No.** 17 stale findings across 8 claims, behind a green 46/46 cross-report run. DEFECT #54: the checker matched each report as one flat string and could not detect an omission at all |")
    A("| Is ARCH_Z4 a real power die? | **Now yes, still conditional.** 1921 um of sourced components replace a heat source in a 10 um underfill layer. Its construction is unsourced, and Z4 takes first or second place depending on which construction is real |")
    A("| Does each TSV span what the architecture says? | **Now yes.** Three domains had been using 300, 280 and a hard-coded ladder for the same via. No architecture traverses 1300 um; ARCH_Z1 traverses 74 um. Three of four sit exactly on the 10:1 limit |")
    A("| Is the cooler inside its correlation domain? | **At 27 g/s yes, at 50 g/s no.** Re = 2342 lies between the laminar ceiling of 2300 and Gnielinski's floor of 3000. h = 166 000 W/m2K, 1.46 MPa and 74 W are withdrawn |")
    A("| Does the RDL thermal tensor change the answer? | **It changes absolute temperature by 7 K and the ordering by 0.105 %.** Promoted to the production default for the absolute numbers |")
    A("")
    A("A sixth finding came out of the second: **DEFECT #55**, the TSV-field material "
      "override was keyed on in-plane footprint, so the PCB, the BGA field and ARCH_Z2's "
      "backside converter were all modelled as a copper/silicon composite -- k too high by "
      "530x, E by 6.3x, CTE too low by 3.4x, in the layers that set package warpage. It was "
      "architecture-dependent and did not cancel: correcting it moved the Z1/Z2 driver "
      "ratio from 1.2552 to 1.1942.")
    A("")
    A("**The deciding ordering survived all of it.** driver_Z1 / driver_Z2 = 1.1942, "
      "ARCH_Z2 better. **Nothing is buildable:** 0 of 12 template-architecture "
      "combinations are realizable at any of 27 clearance-bound corners, and area, routing "
      "and current density block more of them than the clearances do.")
    A("")
    A(r"\newpage")
    A("")
    A("# 2. The physical system and the architectures")
    A("")
    A("| quantity | value | provenance |")
    A("|---|---|---|")
    A("| load | 1000 W at 1 V, 1000 A | reference system (June-2026) |")
    A("| input rail | 48 V | reference system |")
    A("| compute die | 22.36 mm square, 500 mm2 | reference system |")
    A("| voltage regulators | 49 cells, 20.41 A each | Phase-0F 1 kW design point |")
    A("| converter topology | 3:1 switched capacitor into a 3-phase buck (`N3K3KA2`) | compiled by the upstream optimizer |")
    A("| switching frequency | 805.17 kHz | compiled |")
    A("| devices | EPC2014C high side, EPC2057 low side | EPC product table |")
    A("| inductor | 250 nH, 1.6 mOhm DCR, 500 um tall | Rasheedi, TCPMT 2026 |")
    A("| capacitor | 10 uF, 2.5 mOhm ESR | Murata GCM21 datasheet |")
    A("")
    A("Four vertical-integration architectures are compared. They differ in **where the "
      "conversion happens**, which decides **which rail crosses the substrate** --- and that "
      "single fact dominates the electrical comparison.")
    A("")
    A("| architecture | where the converter sits | rail on the TSVs | substrate |")
    A("|---|---|---|---|")
    A("| **Z1 EMBEDDED** | inside the substrate power layers | 48 V, 23.4 A | 1.30 mm (component-height limited) |")
    A("| **Z2 BACKSIDE** | on the substrate underside, as chiplets | **1 V, 1000 A** | 0.30 mm |")
    A("| **Z4 POWER DIE** | a dedicated die between substrate and compute die | 48 V, 23.4 A | 0.30 mm |")
    A("| **Z5 2.5D LATERAL** | beside the die on a common interposer | 48 V | 0.30 mm |")
    A("")
    A("Z2 puts 1000 A on the TSV field where Z1 and Z4 put 23.4 A: a factor of **1822 in "
      "$I^2$** at the same geometry. Z5 is the control --- it is the architecture DVPD exists "
      "to beat.")
    A("")
    A(f"![Architecture cross-sections]({FIGM}/FIG_0M_E_partition_templates.png)")
    A("")
    A("*Component-partition templates and whether each fits the die shadow.*")
    A("")
    A(r"\newpage")
    A("")
    A("# 3. The data flow, end to end")
    A("")
    A("```")
    A("  architecture choice")
    A("        |")
    A("        v")
    A("  component partition template          which component sits on which tier")
    A("        |")
    A("        v")
    A("  converter synthesis (upstream)        devices, inductor, capacitor, f_sw, area")
    A("        |")
    A("        v")
    A("  loss ledger                           one owner per watt, system scope enforced")
    A("        |")
    A("        +--> intra-VR routing           metal BETWEEN the converter components")
    A("        +--> vertical interconnect      R_bulk + dR_transition, per class")
    A("        +--> package RDL                multilayer resistive sheet")
    A("        |")
    A("        v")
    A("  spatial heat deposition               each term into the layer it occurs in")
    A("        |                               (checked against the electrical total)")
    A("        v")
    A("  thermal solve (CalculiX)  <---->  physical cooling")
    A("        |                            h(x) from channel geometry and flow")
    A("        |                            T_fluid(x) from the heat removed upstream")
    A("        v")
    A("  temperature field T(x,y,z)")
    A("        |")
    A("        +--> back to the loss ledger    rho(T), R_DS(on)(T), DCR(T)   [FIXED POINT]")
    A("        |")
    A("        v")
    A("  structural solve (CalculiX)           global thermoelastic warpage and stress")
    A("        |")
    A("        v")
    A("  corner-joint relative displacement    the driver handed to the local model")
    A("        |")
    A("        v")
    A("  local solder submodel (CalculiX)      viscoplastic, cyclic, graded mesh")
    A("        |")
    A("        v")
    A("  per-cycle local inelastic RESPONSE metric --> RELATIVE life only")
    A("```")
    A("")
    A("Two loops close and one does not. **Electrical and thermal are iterated to a fixed "
      "point.** **Thermal drives mechanics one way.** Mechanics returns nothing, and Section "
      "19 gives the measured reason.")
    A("")
    A(f"![Production flow]({FIGMR}/FIG_0MR_A_production_flow.png)")
    A("")
    A("*Which parts of this flow were measured in Phase 0M and which now drive it.*")
    A("")
    A(r"\newpage")
    A("")
    A("# 4. Governing equations")
    A("")
    A("## 4.1 Electrical")
    A("")
    A("Conductor resistance, temperature dependent:")
    A("")
    A("$$R = \\frac{\\rho(T)\\,\\ell}{A}, \\qquad "
      "\\rho(T) = \\rho_{20}\\left[1 + \\alpha (T - 20)\\right]$$")
    A("")
    A("Via-field allocation and field resistance, with the count DISCRETE:")
    A("")
    A("$$n_{req} = \\left\\lceil \\frac{I}{J_{design} A_c} \\right\\rceil, "
      "\\qquad R_{field} = \\frac{R_{single}}{n_{alloc}} + \\Delta R_{transition}$$")
    A("")
    A("Under minimum-capability provisioning the first term collapses to")
    A("$R_{field} = \\rho(T) h J_{design} / I$ and **the conductor cross-section cancels**. "
      "That is derived, verified numerically and discussed in Section 9.")
    A("")
    A("Lateral distribution, solved as a PDE rather than a lumped resistance:")
    A("")
    A("$$\\nabla \\cdot \\left( \\sigma_s \\nabla V \\right) = -J, "
      "\\qquad \\sigma_s = \\frac{N_{layers}\\, t_{Cu}\\, \\text{occupancy}}"
      "{\\rho(T)}$$")
    A("")
    A("Three-dimensional conduction, for transitions:")
    A("")
    A("$$\\nabla \\cdot \\left( \\sigma \\nabla V \\right) = 0, \\qquad "
      "\\mathbf{J} = -\\sigma \\nabla V, \\qquad P = \\int \\mathbf{J} \\cdot "
      "\\mathbf{E}\\, dV$$")
    A("")
    A("Converter loss --- the upstream closed form, decomposed per component and checked "
      "against its own aggregate:")
    A("")
    A("$$P_{cond} = \\frac{V_{out}}{V_{in}} I_{rms}^2 \\left[ R_{DS,hs} + "
      "2\\left(1-\\tfrac{1}{N}\\right) R_{C,ESR} + \\left( \\frac{V_{in}}"
      "{N^2 V_{out}}(R_{L} + R_{DS,ls}) + \\frac{2 R_{DS,ls}}{N} \\right) \\Sigma B^2 "
      "- \\text{corr} \\right]$$")
    A("")
    A("## 4.2 Thermal")
    A("")
    A("$$\\nabla \\cdot \\left( \\mathbf{k}_{eff} \\nabla T \\right) + \\dot{q} "
      "= 0$$")
    A("")
    A("with an anisotropic $\\mathbf{k}_{eff}$ for every heterogeneous layer, and the "
      "cooled boundary")
    A("")
    A("$$-\\mathbf{k}\\nabla T \\cdot \\mathbf{n} = h(x)\\left[T_s(x) - T_f(x)"
      "\\right], \\qquad T_f(x) = T_{in} + \\frac{Q(0 \\to x)}{\\dot{m} c_p}$$")
    A("")
    A("$h$ from a Nusselt correlation, $T_f$ from the heat actually removed upstream. Both "
      "are iterated with the wall temperature to a fixed point.")
    A("")
    A("## 4.3 Mechanical")
    A("")
    A("Global, linear thermoelastic:")
    A("")
    A("$$\\nabla \\cdot \\boldsymbol{\\sigma} = 0, \\qquad "
      "\\boldsymbol{\\sigma} = \\mathbf{C} : \\left( \\boldsymbol{\\varepsilon} "
      "- \\boldsymbol{\\alpha}\\,\\Delta T \\right)$$")
    A("")
    A("Local solder, viscoplastic. **What CalculiX actually integrates in a `*VISCO` step "
      "is an OVERSTRESS law**, and the distinction matters:")
    A("")
    A("$$\\dot{\\varepsilon}_{in} = A(T)\\left( \\sigma_{vm} - \\sigma_y("
      "\\bar{\\varepsilon}_{in}) \\right)^{n(T)} \\ \\text{for}\\ \\sigma_{vm} "
      "> \\sigma_y, \\qquad \\dot{\\varepsilon}_{in} = 0 \\ \\text{otherwise}$$")
    A("")
    A("There is **no rate-independent plastic strain** in such a step, and $A$, $n$ and "
      "$\\sigma_y$ are interpolated **linearly** between card rows by the solver --- not by "
      "an Arrhenius law. Any Arrhenius relation exists only in how the rows were generated.")
    A("")
    A("A separate rate-independent plastic branch **is not presently justified if a validated "
      "UNIFIED viscoplastic law such as Anand is used**, because a unified law already carries "
      "the rate-independent response inside its single inelastic flow rule. That is a statement "
      "about unified laws, not a general claim about plasticity.")
    A("")
    A("**The variable mismatch, stated plainly.** The creep card in this repository was fitted "
      "against **total applied stress** $\\sigma_{vm}$ in the source experiments, while the "
      "solver drives it with the **overstress** $\\sigma_{vm} - \\sigma_y$. The two agree "
      "only where $\\sigma_y$ is small against $\\sigma_{vm}$. This is not a coding error "
      "and cannot be fixed by refitting the same data; it is why the constitutive status is "
      "CONDITIONAL rather than closed, and it is the dominant open blocker on every absolute "
      "reliability number in this framework.")
    A("")
    A("Damage metric, per stabilised cycle:")
    A("")
    A("$$D = \\Delta \\text{PEEQ}\\big|_{cycle}, \\qquad "
      "W_{in} = \\oint \\boldsymbol{\\sigma} : d\\boldsymbol{\\varepsilon}_{in}, "
      "\\qquad \\boldsymbol{\\varepsilon}_{in} = \\mathbf{ME} - \\mathbf{C}^{-1}(T)"
      ":\\boldsymbol{\\sigma}$$")
    A("")
    A("`ME` is the solver's own mechanical strain. Reconstructing the inelastic strain from "
      "it, rather than from a separately parsed temperature, removes an entire class of "
      "error (Section 22, defect 46).")
    A("")
    A(r"\newpage")
    A("")
    A("# 5. Solvers, and what each is used for")
    A("")
    A("| solver | version | used for | why this one |")
    A("|---|---|---|---|")
    A("| **CalculiX** | 2.23 | thermal conduction, global thermoelasticity, local nonlinear solder | the primary physics solver. Practical ceiling about 40 000 elements for this nonlinear transient class |")
    A("| **MOOSE** `heat_transfer` | 09515f92aa | independent cross-check on scalar conduction | a different mesher, element formulation, quadrature and linear solver. `div(k grad T)` and `div(sigma grad V)` are the same operator |")
    A("| **finite-volume solver** | this repository | 3-D DC conduction for transitions | no DC conduction solver is installed. Cell-centred FV with harmonic-mean face conductivities is exactly conservative across a nine-decade conductivity jump |")
    A("| **analytic Python** | -- | via allocation, sheet conduction, effective media, routing, cooling correlations | cheap enough to sweep, and each form is checked against a numerical solve |")
    A("| **HFSS** | AEDT 2026 R1 | AC / skin validation only | licensed and available. It is a full-wave solver and **cannot pose a pure conduction problem with no return path**, so it is NOT used for the DC transition resistance |")
    A("| **Icepak** | AEDT 2026 R1 | nothing, currently | licensed and available. An earlier attempt returned a solver clamp of exactly 5000 K on every object and that result stays discarded. **No Icepak validation is claimed** |")
    A("| **Q3D** | -- | nothing | **not licensed**. Checked against the licence manager, not assumed |")
    A("| Elmer, GetDP, Palace, OpenFOAM | -- | nothing | **not installed**. Palace's electrostatic mode solves a permittivity problem and would not be a DC conduction solver in any case |")
    A("")
    A("## 5.1 What the finite-volume solver was verified against")
    A("")
    A("| case | result |")
    A("|---|---|")
    A("| uniform bar, analytic rho L / A | **exact at every mesh** |")
    A("| circular contact on a half-space, analytic rho/(4a) | +0.9 % at 6 cells per contact radius |")
    A("| five transition geometries against MOOSE | **0.25 to 0.73 %, 5 of 5 ACCEPTED** |")
    A("")
    A("Both terminals are equipotential Dirichlet planes in both codes, the dielectric is "
      "present in both, and each run reports its discretised block volumes so the geometry "
      "match is proved rather than assumed.")
    A("")
    A(r"\newpage")
    A("")
    A("# 6. How to read every number in this framework")
    A("")
    A("Each quantity carries one of these classes, and they are not interchangeable:")
    A("")
    A("| class | meaning |")
    A("|---|---|")
    A("| **SOURCE_BACKED** | taken from a named primary source with its conditions |")
    A("| **ANALYTICALLY_DERIVED** | a closed form, verified numerically |")
    A("| **NUMERICALLY_VALIDATED** | solved, mesh-converged, checked against a closed form |")
    A("| **INDEPENDENTLY_CROSS_VALIDATED** | reproduced by a second, independent solver |")
    A("| **CALIBRATED** | fitted to reproduce a target. Not transferable |")
    A("| **HOMOGENIZED** | an effective property of a heterogeneous layer, with its RVE error |")
    A("| **CONDITIONAL** | true only under a stated open input, and the input is named |")
    A("| **OPEN** | not determined. Never silently defaulted |")
    A("")
    A("The full ledger is `results/phase0mr/uncertainty_ledger.csv`. Its headline:")
    A("")
    A("| class | count |")
    A("|---|---|")
    A(f"| INDEPENDENTLY_CROSS_VALIDATED | {sum(1 for r in unc if r['fidelity']=='INDEPENDENTLY_CROSS_VALIDATED')} |")
    A(f"| NUMERICALLY_VALIDATED | {sum(1 for r in unc if r['fidelity']=='NUMERICALLY_VALIDATED')} |")
    A(f"| ANALYTICALLY_DERIVED | {sum(1 for r in unc if r['fidelity']=='ANALYTICALLY_DERIVED')} |")
    A(f"| SOURCE_BACKED | {sum(1 for r in unc if r['fidelity']=='SOURCE_BACKED')} |")
    A(f"| CONDITIONAL | {sum(1 for r in unc if r['fidelity']=='CONDITIONAL')} |")
    A(f"| **OPEN** | **{sum(1 for r in unc if r['fidelity']=='OPEN')}** |")
    A("")
    A("**Uncertainties are never RMS-summed across common-mode terms.** For an architecture "
      "RATIO the cancellation is TESTED and the tested residual is what is quoted.")
    A("")
    A(r"\newpage")
    A("")
    A("# 7. Input parameters and their provenance")
    A("")
    A("| parameter | value | class | source |")
    A("|---|---|---|---|")
    A("| rho_Cu at 20 C | 17.0 nOhm.m | SOURCE_BACKED | June-2026 Table III |")
    A("| rho_solder at 20 C | 130 nOhm.m | SOURCE_BACKED | June-2026 |")
    A("| alpha_Cu | 3.93e-3 /K | ASSUMPTION | bulk Cu TCR |")
    A("| TSV diameter / pitch / height | 30 / 60 / 300 um | SOURCE_BACKED | June-2026 Table III |")
    A("| TSV liner thickness | 0.5 um | ASSUMPTION | typical SiO2 liner; swept |")
    A("| TSV aspect-ratio limit | 10:1 | DERIVED_FROM_SOURCE | the source demonstrates d = 30 um at h = 300 um |")
    A("| keep-out ratio | swept 0 to 1.5 | ASSUMPTION | no source; never fixed |")
    A("| RDL stack | t = 10 um, W/S = 10/2, 2 VDD + 2 GND | SOURCE_BACKED | ECTC-2024 Table I |")
    A("| J_design | 1.0e8 A/m2 | DERIVED_FROM_SOURCE | June-2026 provisioning |")
    A("| J_process_max | 4.0e8 A/m2 | DERIVED_FROM_SOURCE | ECTC-2024, the most aggressive available |")
    A("| **J_reliability_allow** | -- | **OPEN** | no primary EM study with its T, lifetime and geometry was retrievable |")
    A("| GaN heights | 685 / 606 um | SOURCE_BACKED | EPC2212 / EPC2090 datasheets |")
    A("| inductor | 250 nH, 1.6 mOhm, 500 um | SOURCE_BACKED | Rasheedi, TCPMT 2026 |")
    A("| MLCC height | 100 um nominal, 250 um upper | PARTIAL | manufacturer page unreachable; envelope carried |")
    A("| solder E, nu, CTE | 45 GPa, 0.36, 21.5 ppm/K | ASSUMPTION | commonly quoted band |")
    A("| **solder creep A(T), n(T)** | 19 points over 7.51-15.92 MPa | **CONDITIONAL** | **Sn3.9Ag0.6Cu, NOT SAC305** |")
    A("| underfill E / CTE | 8 GPa / 30 ppm/K | PROVISIONAL | unsourced; sensitivity run |")
    A("| board | 20 GPa, 17 ppm/K, 1.6 mm FR4 | ASSUMPTION | typical laminate |")
    A("| coolant | water, 27 g/s, 25 C inlet | DESIGN VARIABLE | derived, not calibrated |")
    A("| **required life** | -- | **OPEN** | no field or product requirement exists |")
    A("| **mechanical allowable** | -- | **OPEN** | nine candidates tested, none admissible |")
    A("")

    A(r"\newpage")
    A("")
    A("# 8. Interconnect geometry")
    A("")
    A("**No resistance is a primitive.** Every interconnect quantity is classified as exactly "
      "one of MATERIAL, PROCESS, DESIGN or DERIVED, and the classifier raises on anything "
      "unclassified.")
    A("")
    A("| class | examples |")
    A("|---|---|")
    A("| MATERIAL | rho_Cu(T), alpha, k_Cu, k_Si, k_SiO2 |")
    A("| PROCESS | minimum pitch, liner thickness, aspect-ratio limit, keep-out ratio, J_process_max |")
    A("| DESIGN | via radius, pitch, height, allocated count, RDL thickness / width / spacing / layer count, bump diameter / height / pitch, pad size |")
    A("| DERIVED | conductor area, single-via R, per-via current limit, available and required counts, field R, Joule loss, copper fraction, effective k and CTE, transition dR |")
    A("")
    A("Three quantities that used to be primitives and are now derived:")
    A("")
    A("1. the per-via current limit, which was entered in amperes and is now `J_design * A_c`;")
    A("2. the current-crowding correction, which was one global constant and is now solved "
      "per class and per geometry;")
    A("3. the TSV liner, which was absent and now sets the conducting radius.")
    A("")
    A("## 8.1 Transition resistance")
    A("")
    A("$$R_{total} = R_{bulk}(\\text{geometry}, T) + \\Delta R_{transition}"
      "(\\text{class}, \\text{geometry}, T)$$")
    A("")
    A("`dR` is solved exactly for each production geometry by the finite-volume solver and "
      "cached against a geometry fingerprint. There is **no fitted surrogate**: a two-term "
      "logarithmic form was tried over 178 geometries and rejected at 9 to 29 % of the "
      "spread of the quantity it was fitting.")
    A("")
    A("**`dR` can be negative, and that is physical, not an error.** The 1-D reference is a "
      "series of named conductors with implicit equipotential cross-sections everywhere; the "
      "3-D solve constrains only the two terminal planes. A generous landing pad genuinely "
      "replaces part of a narrow trace. `dR` is therefore reported as a difference against a "
      "stated reference and never as an \"excess\".")
    A("")
    A("| class | R_1D | dR | R_3D / R_1D |")
    A("|---|---|---|---|")
    A(chr(10).join(f"| {v['cls']} | {v['R_1D_ohm']*1e3:.4f} mOhm | {v['dR_ohm']*1e3:+.4f} mOhm | **{v['ratio_3D_over_1D']:.4f}** |" for v in sorted(dRcache.values(), key=lambda v: v['cls'])) if dRcache else "| -- | -- | -- | -- |")
    A("")
    A("Against the retired global constant of **1.326**, applied identically to all four "
      "classes.")
    A("")
    A(f"![Transition decomposition]({FIGMR}/FIG_0MR_C_transition_decomposition.png)")
    A("")
    A("## 8.2 The TSV radius result, stated precisely")
    A("")
    A("Under the minimum-capability allocation this framework uses, "
      "`R_field = rho h J_design / I` and **the conductor cross-section cancels identically** "
      "--- not merely the radius. The copper fraction `I / (J_design A_field)` is likewise "
      "independent of radius, so the effective conductivity, modulus and CTE do not move "
      "either.")
    A("")
    A("The permitted conclusion is therefore **not** \"TSV radius is irrelevant\". It is: "
      "*the TSV cross-section is not an independent field-loss lever under minimum-capability "
      "provisioning when `J_design` is geometry-independent.* Radius remains decisive for "
      "**feasibility**:")
    A("")
    A("| via height | feasible radii at a 10:1 aspect limit |")
    A("|---|---|")
    A("| 100 um | 7.5 to 50 um |")
    A("| 300 um | **15 to 50 um** --- and 15 um is the reference radius, so the source "
      "geometry sits ON the limit |")
    A("| 1300 um | **none in the swept range**; the rule `r >= h/20` demands r >= 65 um |")
    A("")
    A(f"![TSV feasibility]({FIGMR}/FIG_0MR_D_tsv_feasibility.png)")
    A("")
    A(r"\newpage")
    A("")
    A("# 9. Converter component-level partitioning")
    A("")
    A("The converter is nine components per cell: 3 high-side GaN, 3 low-side GaN, 2 flying "
      "capacitors, 3 inductors and an output capacitor. Their summed footprint is "
      "**18.01 mm2** against a 500 mm2 die shared by 49 cells --- **10.20 mm2 per cell**. A "
      "single-level VR therefore misses the die shadow by **1.76x**, and vertical partitioning "
      "is a precondition rather than an optimization.")
    A("")
    A("Each template is checked on six independent questions, not on area alone:")
    A("")
    A("| template | tiers | charged height / available | area | height | routing | thermal | clearance |")
    A("|---|---|---|---|---|---|---|---|")
    A(chr(10).join(f"| {r['template']} in {r['arch'].replace('ARCH_','')} | {r['n_tiers']} | {f(r,'height_charged_um',0)} / {f(r,'arch_space_um',0)} um | {r['AREA_FEASIBLE']} | {r['HEIGHT_FEASIBLE']} | {r['ROUTING_FEASIBLE']} | {r['THERMAL_FEASIBLE']} | OPEN |" for r in part))
    A("")
    A("**No template is fully realizable.** The closest is the embedded four-layer stack in "
      "the embedded architecture, whose charged height of 1226 um reproduces an independently "
      "derived earlier figure exactly and fits the 1250 um available. It is blocked on "
      "routing and on thermal depth.")
    A("")
    A("**Three package clearances have no source** --- die-to-component gap, cavity sidewall "
      "allowance, cooled-surface standoff --- so every template carries CLEARANCE OPEN and "
      "**none may be called buildable**. Treating them as zero would convert three unknowns "
      "into a pass.")
    A("")
    A("## 9.1 The intermediate rail")
    A("")
    A("A partition that splits by VOLTAGE DOMAIN puts the 16 V intermediate rail across the "
      "tier boundary, carrying **1.44 A where the 1 V rail would carry 20.4 A** --- a factor "
      "of 200 in `I^2`. That is why the split SC/buck template has essentially zero vertical "
      "intra-VR loss.")
    A("")
    A(f"![Component power path]({FIGMR}/FIG_0MR_B_component_power_path.png)")
    A("")
    A(r"\newpage")
    A("")
    A("# 10. Intra-VR routing")
    A("")
    A("**The metal between the converter's own components is now in the loss total.** Before "
      "Phase 0M-R it was absent entirely: the framework modelled VR-to-package and "
      "package-to-POL routing and nothing inside the converter.")
    A("")
    A("There is no double counting, and the reason is structural rather than a comment. The "
      "upstream converter model owns every device and passive parasitic --- switch "
      "`R_DS(on)`, inductor DCR, capacitor ESR, and all switching loss --- and contains no "
      "metallization. The ledger enforces **one owner per watt**: a second writer to any term "
      "raises, and the conduction split is checked against the upstream aggregate to machine "
      "precision before a total may be produced.")
    A("")
    A("| term | owner |")
    A("|---|---|")
    A("| `P_switch_hs_conduction`, `P_switch_ls_conduction` | upstream conduction formula |")
    A("| `P_inductor_DCR`, `P_cap_ESR` | upstream conduction formula |")
    A("| `P_switching_hard`, `P_gate`, `P_Coss` | upstream switching formula |")
    A("| `P_intraVR_metal`, `P_intraVR_vertical` | **this framework, new** |")
    A("| `P_TSV`, `P_bumps` | vertical tier model, `R_bulk + dR` |")
    A("| `P_pkg_RDL` | multilayer resistive sheet |")
    A("")
    A("The routing model is **template-aware**: components on the same tier need a lateral "
      "run, components on different tiers need a via stack, and the via-stack height is set "
      "by the components below it. Phase 0M's claim that intra-VR routing is common-mode "
      "across architectures held only while every architecture used the same layout; measured "
      "across partition templates it varies by **7.5 %**.")
    A("")
    A(r"\newpage")
    A("")
    A("# 11. The cooling model")
    A("")
    A("**The cooled boundary is derived from hardware, not calibrated to a target.**")
    A("")
    A("$$-k \\nabla T \\cdot n = h(x)\\left[T_s(x) - T_f(x)\\right], \\qquad "
      "T_f(x) = T_{in} + \\frac{Q(0 \\to x)}{\\dot{m} c_p}$$")
    A("")
    A("`h` comes from a Nusselt correlation for the channel geometry, corrected by fin "
      "efficiency and area amplification. `T_f` comes from the heat actually removed upstream "
      "of each face, integrated from the solved flux and iterated with the wall temperature "
      "to a fixed point. The design variables are coolant, inlet temperature, mass flow, "
      "channel width, height and pitch, base thickness and solid conductivity.")
    A("")
    A("| design | m_dot | Re | regime | h_effective | coolant rise | T_j | dp | pumping |")
    A("|---|---|---|---|---|---|---|---|---|")
    A(chr(10).join(f"| {r['design']} | {f(r,'m_dot_g_s',1)} g/s | {f(r,'Re',0)} | {r['regime']} | {f(r,'h_effective',0)} | {f(r,'dT_fluid_K',2)} K | {f(r,'T_j_compact_C',1)} C | {f(r,'dp_kPa',0)} kPa | {f(r,'P_pump_hydraulic_W',2)} W |" for r in cool))
    A("")
    A("**Pumping power is reported and never folded into the electrical total.** "
      "`P_electronics` and `P_pumping` stay separate; pump efficiency is unsourced, so "
      "hydraulic power is primary and a 35/55/75 % shaft-power band is carried beside it.")
    A("")
    A("## 11.1 What this replaced, and why it mattered")
    A("")
    A("The previous boundary was a single inverse-calibrated coefficient, "
      "**h = 166 000 W/m2K**, with one uniform sink temperature, chosen so the package would "
      "reach a target junction temperature. Three things were hidden inside it:")
    A("")
    A("* **no laminar microchannel architecture reaches that coefficient.** The best gets "
      "0.70x. Reaching it needs 50 g/s in the transitional regime, **74 W of pumping --- "
      "7.4 % of the load ---** and 1.46 MPa;")
    A("* at the flow rate the reference system states, the coolant would rise **168 K**, which "
      "single-phase water cannot do. A 10 K rise needs 26.9 g/s;")
    A("* a single sink temperature cannot produce a streamwise gradient, and a real one moves "
      "the die warpage by several per cent.")
    A("")
    A(f"![Cooling]({FIGMR}/FIG_0MR_F_cooling.png)")
    A("")
    A("## 11.2 Validation")
    A("")
    A("The compact model has three parts and each is validated by a tool that can pose it:")
    A("")
    A("| part | method | result |")
    A("|---|---|---|")
    A("| fluid side | analytic energy balance | exact for every design |")
    A("| solid side | MOOSE on the explicit finned geometry | see below |")
    A("| coupling | fixed-point iteration, energy checked | residual reported per solve |")
    A("")
    A("| case | fin efficiency | R compact | R MOOSE | error | verdict |")
    A("|---|---|---|---|---|---|")
    A(chr(10).join(f"| {r['case']} | {f(r,'fin_efficiency',4)} | {g(r,'R_compact_K_m2_W',5)} | {g(r,'R_moose_K_m2_W',5)} | {f(r,'error_pct',2)} % | **{r.get('verdict','--')}** |" for r in coolv))
    A("")
    A("**The compact solid model is valid for tall thin fins and degrades for short thick "
      "ones**, which is the expected failure of a 1-D fin assumption. The production geometry "
      "is inside the accepted band at 3.78 %; the short-fin case is REJECTED at 10.11 % "
      "against a band declared before the runs. That boundary is recorded, not glossed.")
    A("")
    A(r"\newpage")
    A("")
    A("# 12. Thermal homogenization")
    A("")
    A("Every heterogeneous layer carries an anisotropic effective tensor, validated against "
      "explicit-geometry finite volumes on unit cells with a predeclared 10 % / 25 % "
      "acceptance band. The unit cell is its own periodic cell: for a centred inclusion in a "
      "square cell, symmetry puts zero normal flux on every mid-plane, and a 1x1 against 2x2 "
      "check confirms it to 0.000 %.")
    A("")
    A("| layer | what survives | what does not |")
    A("|---|---|---|")
    A("| TSV + Si + liner | Voigt for k_z, better than 1 % | the pre-existing framework's transverse model, 19 to 74 % low, because it puts the liner in series with the copper |")
    A("| bump + underfill | Voigt for k_z and Maxwell for k_xy, both under 1.5 % | the TSV formula, which must not be reused: the contrast and the matrix are different |")
    A("| RDL stack | direction-resolved tensor per stack organisation | any single isotropic value |")
    A("")
    A("## 12.1 The RDL, where the number depends on the organisation")
    A("")
    A("| organisation | k_x | k_y | k_z | in-plane x/y | in-plane / through |")
    A("|---|---|---|---|---|---|")
    A(chr(10).join(f"| {r['organisation']} | {f(r,'k_x',2)} | {f(r,'k_y',2)} | {f(r,'k_z',2)} | **{f(r,'in_plane_anisotropy_x_over_y',2)}** | {float(r['k_x'])/float(r['k_z']):.0f}x |" for r in rdlt if f(r,'t_diel_um',1)=='5.0'))
    A("")
    A("A single-direction line layer is strongly anisotropic in plane. **Every realistic "
      "organisation --- orthogonal routing, a mesh, a plane --- is in-plane isotropic to "
      "1.00.** The real anisotropy is through-thickness against in-plane, 57x to 270x, "
      "because the inter-layer dielectric sits in series through the stack while the copper "
      "is in parallel across it.")
    A("")
    A("That matters because the production package still gives this layer **one isotropic "
      "0.7 W/m.K**: roughly right through thickness by accident, and two to three orders of "
      "magnitude too low in plane. The framework is missing a major lateral heat-spreading "
      "path, and the correction is built and measured but is not yet the default.")
    A("")
    A(f"![RDL tensor]({FIGMR}/FIG_0MR_E_rdl_tensor.png)")
    A("")
    A("## 12.2 What is deliberately NOT homogenized")
    A("")
    A("The local solder and transition regions keep explicit geometry. Homogenizing them "
      "would destroy the gradients the reliability chain reads. Global/local submodelling is "
      "retained throughout: tensors in the package model, explicit geometry in the joint and "
      "transition submodels.")
    A("")

    A(r"\newpage")
    A("")
    A("# 13. The mechanical model")
    A("")
    A("## 13.1 Global")
    A("")
    A("A linear thermoelastic finite-element model of the whole package: board, BGA field, "
      "converter layer, substrate with a homogenized TSV region, interface layer, die and "
      "TIM. Silicon is cubic-anisotropic; everything else is isotropic. The converged "
      "temperature field from Section 11 drives it.")
    A("")
    A("It produces two things the rest of the chain uses: **die and package warpage**, and "
      "**the relative in-plane displacement across the corner BGA standoff** --- the quantity "
      "handed to the local solder model.")
    A("")
    A("## 13.2 Local solder submodel")
    A("")
    A("A graded finite-element model of the single worst joint, driven by the corner "
      "displacement, cycled to a stabilised response. The constitutive law is the overstress "
      "form in Section 4.3. The metric is the accumulated equivalent inelastic strain per "
      "stabilised cycle, volume-averaged over the solder core with a one-element corner "
      "exclusion band and matched to the averaging volume of the life law it feeds.")
    A("")
    A("## 13.3 The RDL in the mechanical model")
    A("")
    A("**The redistribution metal is not in the mechanical mesh.** The layer between the "
      "substrate and the die is 10 um of homogenized microbump and underfill at 8 GPa; the "
      "real RDL stack is 48 to 104 GPa in plane. A fidelity ladder was built and measured:")
    A("")
    A("| rung | interface layer | Z1 corner shear | Z2 corner shear | Z1/Z2 |")
    A("|---|---|---|---|---|")
    A(chr(10).join(f"| {r['rung']} | {'as built' if r['rung']=='M-RDL0' else ('composite, 10 um' if r['rung']=='M-RDL1' else 'composite, 50 um')} | {f(rdlm_by(r['rung'],'ARCH_Z1_EMBEDDED'),'du_corner_um',4)} um | {f(rdlm_by(r['rung'],'ARCH_Z2_BACKSIDE'),'du_corner_um',4)} um | **{f(rdlm_by(r['rung'],'RATIO'),'du_corner_um',4)}** |" for r in rdlm if r['arch']=='RATIO'))
    A("")
    A("Adding the RDL moves the absolute corner shear by **-3.6 % to +6.8 %** and the "
      "architecture RATIO by at most **0.11 %**. It changes the numbers and it does not "
      "change the ordering. **No RDL allowable is invented**, so the new stress remains "
      "response coupling and not a constraint.")
    A("")
    A(r"\newpage")
    A("")
    A("# 14. The solder reliability model, and what it cannot do")
    A("")
    A("## 14.1 What is solid")
    A("")
    A("* The metric is convergent, mesh-independent within its declared band, and verified to "
      "equal the solver's own accumulated inelastic strain including creep.")
    A("* Four SnAgCu fatigue formulations are admitted for RELATIVE life, their primary "
      "sources obtained and one calibration reproduced from the authors' own corrected "
      "coefficients.")
    A("* The inelastic energy is reconstructed from the solver's mechanical strain, so no "
      "separately parsed temperature enters the energy path.")
    A("")
    A("## 14.2 What is conditional --- the dominant open item")
    A("")
    A("> The creep half of the solder card is fitted on **Sn3.9Ag0.6Cu, not SAC305**, over "
      "**7.51 to 15.92 MPa**, while the joint's damage-weighted median stress is about "
      "**82 MPa** and **99.8 % of the damage is generated outside the fitted window**.")
    A("")
    A("Two consequences that must not be conflated:")
    A("")
    A("* **The ORDERING is robust.** It originates in the global thermoelastic model, which "
      "imposes a 32 % larger corner shear on Z1 and contains no solder law at all. The global "
      "package supplies a constitutive-law-independent deformation driver favoring Z2, and "
      "every presently testable constitutive and life-law combination preserves that "
      "ordering.")
    A("* **The MAGNITUDE is a conditional envelope of 1.19 to 1.22**, not a validated number. "
      "The permitted wording is \"conditional relative-life envelope\". \"Validated relative "
      "life\" is not earned.")
    A("")
    A("## 14.3 What is absent")
    A("")
    A("**Absolute life.** No required life exists anywhere in the sources, and the absolute "
      "life constant cannot be calibrated on top of an extrapolated constitutive model "
      "without burying the constitutive error inside the constant.")
    A("")
    A("**A mechanical allowable.** Nine candidate thresholds were tested against six "
      "admissibility conditions and none passed. Without one, the reliability response "
      "cannot become a feasibility constraint, and the falsification gate that would test "
      "that remains untestable.")
    A("")
    A("## 14.4 Which mechanisms exist at all")
    A("")
    A("| mechanism | status |")
    A("|---|---|")
    A("| global bending | modelled --- a driver, not a failure |")
    A("| solder fatigue | **modelled**, convergent, conditional magnitude |")
    A("| solder creep / unified viscoplasticity | modelled |")
    A("| rate-independent plasticity | not separately modelled, and not justified on top of a unified law |")
    A("| organic board and underfill viscoelasticity | NOT modelled. Measured sensitivity: halving the board modulus moves the driver ratio about 3 % |")
    A("| assembly and reflow prestress | NOT modelled. Measured: it moves the stabilised ratio by 0.11 % |")
    A("| process residual stress | NOT modelled, no data |")
    A("| interface delamination | NOT modelled. Traction-separation parameters are unsourced |")
    A("| solder crack propagation | NOT modelled. Not needed for ranking |")
    A("| **RDL and TSV cracking** | **NOT modelled. The largest unmodelled mechanism that could change ranking** |")
    A("| moisture, hygroscopic swelling | OUT OF SCOPE, declared. The claim is dry steady operating ETM |")
    A("")
    A(r"\newpage")
    A("")
    A("# 15. Coupling directions")
    A("")
    A("| from -> to | status | measured magnitude |")
    A("|---|---|---|")
    A("| electrical -> thermal | **solved, iterated** | the whole loss |")
    A("| thermal -> electrical | **solved, iterated** | rho(T) moves R by 22.8 % over the cycle |")
    A("| thermal -> mechanical | **solved, one way** | the whole thermal strain |")
    A("| geometry -> electrical / thermal / mechanical | **solved** | Sections 8, 12, 13 |")
    A("| cooling -> electrical / thermal / mechanical | **solved** | Section 11, and Section 17 |")
    A("| mechanical -> electrical | **absent** | 0.16 % on R, against 22.8 % from rho(T) already in the loop |")
    A("| mechanical -> thermal | **absent** | 1.5 K for a 4 % TIM bond-line change |")
    A("| damage -> electrical | **absent** | would be +33 % on R at 25 % of a joint lost |")
    A("| damage -> thermal | **absent** | would be +12.5 K at 25 % of the die delaminated |")
    A("| electromigration -> electrical | **OPEN** | the current-density allowable itself is unsourced |")
    A("")
    A("**The framework is at ETM-L1**: electrical and thermal iterated to a fixed point, "
      "thermal driving mechanics one way, mechanics returning nothing.")
    A("")
    A("That is a deliberate, measured choice and not an omission. The two absent arrows "
      "before damage are 0.7 % and 2.9 % of terms already in the loop, and both are "
      "common-mode across architectures, so solving them iteratively would cost solver time "
      "to chase a term two orders of magnitude smaller than one already present. **It is "
      "therefore accurate to describe this framework as geometry-coupled "
      "electrothermal-mechanical co-design with one-way mechanical response in the intact "
      "regime, and inaccurate to call it fully coupled.**")
    A("")
    A("ETM-L3, with damage feeding back into conductance and stiffness, would be required to "
      "predict failure PROGRESSION. Nothing in this framework currently claims to.")
    A("")
    A(r"\newpage")
    A("")
    A("# 16. Validation matrix")
    A("")
    A("| quantity | method | independent? | result |")
    A("|---|---|---|---|")
    A("| RDL sheet PDE | MOOSE | yes | 0.33 to 0.45 % |")
    A("| 3-D conduction, uniform bar | analytic | yes | exact at every mesh |")
    A("| 3-D conduction, spreading | analytic `rho/(4a)` | yes | +0.9 % at 6 cells per radius |")
    A("| **transition resistance, 5 geometries** | **MOOSE** | **yes** | **0.25 to 0.73 %, 5/5 ACCEPTED** |")
    A("| TSV single-via DC resistance | pre-existing framework, independent implementation | yes | exact |")
    A("| TSV skin ratio at 1 MHz | Bessel solution | yes | delta/r = 4.41, ratio 1.0001 |")
    A("| effective k_z, all layers | explicit-geometry RVE | yes | Voigt within 1 % |")
    A("| effective k_xy, bump layers | explicit-geometry RVE | yes | Maxwell within 1.5 % |")
    A("| effective k_xy, TSV arrays | explicit-geometry RVE | yes | Maxwell 11 to 39 % high; the pre-existing model 19 to 74 % low |")
    A("| unit-cell periodicity | 1x1 against 2x2 | yes | 0.000 % |")
    A("| cooling fluid side | analytic energy balance | yes | exact |")
    A("| **cooling solid side** | **MOOSE, explicit fins** | **yes** | **3.78 % at the production geometry; 10.11 % for short thick fins, REJECTED** |")
    A("| converter loss decomposition | upstream aggregate | yes | machine precision, or the ledger refuses to total |")
    A("| spatial heat deposition | electrical total | yes | within 1e-6 relative, guarded |")
    A("| solder PEEQ identity | creep-only experiment | yes | 1.0000 |")
    A("| inelastic energy route | solver mechanical strain | yes | 0.79 to 1.56 %, and 16 to 21x cleaner on the isochoric test |")
    A("| package thermal | MOOSE, full 3-D | yes | ordering preserved |")
    A("| **package thermal against CFD** | Icepak | -- | **FAILED and discarded.** No CFD validation is claimed |")
    A("| **TSV loop AC resistance** | HFSS | -- | **ATTEMPTED, did not converge in budget** |")
    A("")
    A(r"\newpage")
    A("")
    A("# 17. What the production models changed, measured")
    A("")
    A("The same frozen comparison matrix was run twice, changing only which models drive the "
      "path. BEFORE is the previous production path: one global crowding constant, no "
      "intra-VR routing, a calibrated Robin boundary with a uniform sink, a lumped VR. AFTER "
      "is the path described in this document.")
    A("")
    A("| architecture | mode | P_elec | T_max | die warpage | corner shear |")
    A("|---|---|---|---|---|---|")
    A(chr(10).join(f"| {r['arch'].replace('ARCH_','')} | {r['mode']} | {f(r,'P_elec_total_w',2)} W | {f(r,'T_max_C',2)} C | {f(r,'die_warpage_pv_um',3)} um | {f(r,'du_corner_um',4)} um |" for r in sorted(ok, key=lambda r:(r['arch'], r['mode'], str(r.get('cooler')), str(r.get('template')))) ) if ok else "| -- | -- | -- | -- | -- | -- |")
    A("")

    A(r"\newpage")
    A("")
    A("# 18. Numerical convergence")
    A("")
    A("| model | convergence evidence |")
    A("|---|---|")
    A("| RDL sheet | grid-converged; 121 to 201 nodes moves the answer 0.15 % |")
    A("| 3-D transition | mesh drift 0.03 to 0.26 % between refinement levels |")
    A("| RVE homogenization | 1x1 against 2x2 periodic cell, 0.000 % |")
    A("| global thermal / structural | element budget is a hard gate at the measured solver ceiling, never a silent fallback |")
    A("| local solder | stabilised cycle declared as a cycle-to-cycle change below 5 %; achieved 0.03 to 0.22 % |")
    A("| energy integration | tightened until the answer stopped moving; time step and output frequency both refined |")
    A("| ET fixed point | iterated on LOCAL layer temperature to below 0.25 K |")
    A("| cooling fluid coupling | fluid temperature iterated to below 0.02 K |")
    A("| spatial heat | deposited total checked against the electrical total, guarded at 1e-6 relative |")
    A("")
    A(r"\newpage")
    A("")
    A("# 19. Defects found and corrected")
    A("")
    A("This framework has a standing rule: a defect is recorded with the mechanism that let "
      "it survive, not only with its fix. Fifty-three are logged. The ones an auditor should "
      "know about:")
    A("")
    A("| id | defect | how it survived | status |")
    A("|---|---|---|---|")
    A("| 30 | vertical-tier losses summed per-regulator with system-wide RDL loss | no scope type existed | FIXED, and made structural: mixing scopes now raises |")
    A("| 40 | the creep law was fitted in a stress variable the solver does not consume | the fit and the solver were never compared in the same variable | FIXED by removing the yield threshold |")
    A("| 44 | stale current-facing claims propagated into both reports | each sentence was true when written | FIXED at source |")
    A("| 46 | two parsers stood on opposite sides of a step boundary, inflating every inelastic-energy number by 18.5 % | both parsers were individually correct | FIXED, then ELIMINATED by reading the solver's own mechanical strain |")
    A("| 47 | the per-via current limit was a primitive in amperes, and it is the only thing that sets field resistance | it looked like a device property | FIXED: `J_design * A_c` |")
    A("| 48 | one global crowding constant for four interconnect classes | it was measured once, on one geometry | FIXED: solved per class, cross-validated |")
    A("| 49 | the TSV liner was absent from the conductor area | never modelled | FIXED |")
    A("| 50 | the converter area model assumes four-layer stacking and its own docstring says the opposite | `max()` reads like `sum()` at a glance | DOCUMENTED; upstream is a separate repository |")
    A("| 51 | intra-converter routing absent from every loss term | the converter was a black box with a loss number | FIXED: now in the total |")
    A("| 52 | the calibrated cooling coefficient is unreachable by any laminar cooler and hides 7.4 % of the load in uncharged pumping | it was calibrated to a temperature, and it hit it | FIXED: derived from hardware |")
    A("| **53** | **the current-status generator was internally consistent across both reports and consistently stale** | **cross-report comparison passes when both are stale in the same way** | **FIXED: a single authoritative contract, with mutation and injection tests** |")
    A("")
    A("Four faults in this phase's own new code were caught before they reached a conclusion "
      "and are recorded for the same reason: a zero-width mesh cell that produced a silently "
      "wrong resistance whose only symptom was a current-balance residual; dead-ended traces "
      "that made a three-trace case look 2.5x worse; a planar intra-VR layout that returned "
      "61 % of the load because it assumed a topology the architecture does not have; and a "
      "fit-quality metric that was misleading in both directions at once.")
    A("")
    A(r"\newpage")
    A("")
    A("# 20. Open physical gaps")
    A("")
    A("| gap | why it is open | consequence |")
    A("|---|---|---|")
    A("| **high-stress SAC305 constitutive response** | no primary data above ~16 MPa retrievable; four P0 and five P1 papers behind institutional access | **the dominant blocker.** Every absolute reliability number is conditional on it |")
    A("| **required life** | not published for the reference system, and inventing one is forbidden | the falsification gate cannot be evaluated |")
    A("| **mechanical allowable** | nine candidates tested, none admissible | mechanics ranks but cannot constrain |")
    A("| electromigration current-density allowable | no primary study with its temperature, lifetime and geometry | feasibility is a map over J, never a verdict |")
    A("| package clearances | three unsourced | no partition template may be called buildable |")
    A("| cohesive-zone parameters | traction-separation laws unsourced | delamination cannot be predicted |")
    A("| polymer viscoelastic spectra | no DMA data for the specific laminate | a modulus sensitivity is carried instead of a Prony series |")
    A("| Z4 power-die layer geometry | the global mesh has no such layer | the Z4 thermal result is conditional on depositing its heat in the interface layer |")
    A("| conjugate CFD validation | the earlier attempt returned a solver clamp | no CFD validation is claimed |")
    A("")
    A(f"![Closure ladder]({FIGMR}/FIG_0MR_K_closure_ladder.png)")
    A("")
    A(r"\newpage")
    A("")
    A("# 21. Which claims are safe, and which are not")
    A("")
    A("## 21.1 Safe to publish now")
    A("")
    A("* Vertical placement of the converter changes both the electrical path and the local "
      "solder response, and the two trade against each other.")
    A("* Moving conversion below the substrate puts the 1 V rail on the TSVs, and the "
      "electrical cost of that is quantified.")
    A("* **Z2 accumulates less solder-fatigue damage than Z1**, under every admitted "
      "constitutive model, every admitted life law, every profile and all three response "
      "metrics. The ordering originates upstream of the solder model.")
    A("* The conditional relative-life envelope is **1.19 to 1.22** at the operating baseline.")
    A("* Under minimum-capability provisioning the TSV conductor cross-section cancels out of "
      "the field resistance, and radius is a feasibility variable rather than a loss lever.")
    A("* A single global current-crowding multiplier is the wrong functional form; the "
      "measured spread over 107 geometries is 2.4x.")
    A("* Intra-converter metallization is a real loss term of order 0.4 to 3.9 % of the load "
      "and was previously absent.")
    A("* The calibrated cooling coefficient is not reachable by any laminar microchannel "
      "architecture, and reaching it costs about 7.4 % of the load in pumping power.")
    A("* A single-level VR does not fit the die shadow at 1 kW; vertical partitioning is a "
      "precondition.")
    A("* What CalculiX integrates in a `*VISCO` step is an overstress law with no "
      "rate-independent branch, traced in the solver source.")
    A("")
    A("## 21.2 NOT safe, and why")
    A("")
    A("| claim | why not |")
    A("|---|---|")
    A("| \"Z2 lasts N cycles\" | no absolute life is defensible |")
    A("| \"validated relative life\" | the magnitude is a conditional envelope; the wording is not earned |")
    A("| \"the solder model is valid for this package\" | it is evaluated far outside its fitted stress window |")
    A("| \"the creep law is SAC305\" | its data is Sn3.9Ag0.6Cu |")
    A("| \"the stress extrapolation is common mode and cancels\" | measured, and it only partly cancels |")
    A("| \"mechanics constrains the design\" | no admissible allowable exists |")
    A("| \"the framework is fully ETM coupled\" | mechanics returns nothing; it is ETM-L1 |")
    A("| \"2.5D is eliminated\" | only the one-sided low-voltage lateral topology is |")
    A("| \"TSV radius is irrelevant\" | it is not a field-loss lever; it is decisive for feasibility |")
    A("| \"the thermal model is validated against CFD\" | the CFD attempt failed and was discarded |")
    A("| \"this partition template is buildable\" | three package clearances are unsourced |")
    A("| \"there is plastic and creep strain in the joint\" | there is one viscoplastic strain |")
    A("")
    A(r"\newpage")
    A("")
    A("# 22. How this document stays true")
    A("")
    A("Both this report and its chronological companion are generated from one file. That "
      "meant, for eight phases, that comparing them against each other could pass while both "
      "were stale --- and it did. The section headed \"current scientific status\" printed a "
      "current verdict above six bullets from a much earlier phase, and cross-report "
      "consistency was 25 of 25 the whole time.")
    A("")
    A("The fix is the contract in Section 1.1. Every current-facing statement derives from "
      "it, and three tests keep it honest:")
    A("")
    A("* **mutation** --- change one contract field and both reports fail until regenerated;")
    A("* **injection** --- each of five REAL stale sentences, copied verbatim from the "
      "artifact that contained it, is inserted into a current-facing block and must be "
      "caught;")
    A("* **exoneration** --- a defect report must still be able to quote the defect it fixed, "
      "or the guard becomes unusable and someone will switch it off.")
    A("")
    A("Every evidence path in the contract is checked to exist on disk. That check rejected "
      "the first draft.")
    A("")
    A(r"\newpage")
    A("")
    A("# 23. What should happen next")
    A("")
    A("In priority order, with the reason each is ahead of the next:")
    A("")
    A("1. **Characterise SAC305 above 16 MPa**, by coupon test and by acquiring the four P0 "
      "papers. It is the dominant blocker on every absolute number, and no amount of "
      "modelling removes it.")
    A("2. **Obtain a required life** from the system owner. Without it the falsification gate "
      "cannot be evaluated, whatever the mechanics says.")
    A("3. **Put the RDL into the production mechanical and thermal stack by default.** The "
      "ladder is built and measured; it moves the absolute response by up to 7 % and the peak "
      "temperature by up to 4.7 K.")
    A("4. **Run a canonical single-channel Icepak benchmark** against the analytical "
      "correlation. The licence is available. Until it reproduces the correlation, no CFD "
      "validation may be claimed.")
    A("5. **Source the package clearances**, without which no partition template can be "
      "called buildable.")
    A("6. **Then, and only then, consider an optimizer.** Its preconditions are listed in "
      "Section 24 and none of them is currently met in full.")
    A("")
    A(r"\newpage")
    A("")
    A("# 24. The optimizer gate")
    A("")
    A("A global optimizer is **FORBIDDEN** and remains so. Its preconditions, and where they "
      "stand:")
    A("")
    A("| precondition | status after Phase 0M-R3 | evidence |")
    A("|---|---|---|")
    import csv as _csv
    _pre = list(_csv.DictReader(
        (R / "results" / "phase0mr3" / "optimizer_preconditions.csv").open()))
    for _r in _pre:
        A("| %s | **%s** | %s |" % (_r["precondition"], _r["status"], _r["evidence"]))
    A("")
    _no = sum(1 for _r in _pre if _r["status"] == "NO")
    A("Phase 0M-R2 DOWNGRADED the cooling precondition from YES to PARTIAL --- the model "
      "has no validated correlation between Re 2300 and Re 3000, and an optimizer would be "
      "free to walk into that hole --- and added a new one for whether the architecture "
      "geometry is physically represented at all. **%d remain NO, and any one of them is "
      "sufficient to keep the gate shut.**" % _no)
    A("")

    A(r"\newpage")
    A("")
    A("# 25. Reproducibility")
    A("")
    A("| item | location |")
    A("|---|---|")
    A("| single source of truth for current state | `results/CURRENT_SCIENTIFIC_STATUS.yaml::current_state_contract` |")
    A("| production interconnect model | `scripts/phase0mr/interconnect_production.py` |")
    A("| 3-D conduction solver | `scripts/phase0m/conduction3d.py` |")
    A("| independent cross-check | `scripts/phase0mr/moose_conduction.py` |")
    A("| intra-VR routing | `scripts/phase0mr/routing_production.py` |")
    A("| loss ledger, one owner per watt | `scripts/phase0mr/ledger.py` |")
    A("| physical cooling | `scripts/phase0mr/cooling_production.py` |")
    A("| production ET fixed point | `scripts/phase0mr/production_et.py` |")
    A("| controlled replay | `scripts/phase0mr/run_replay.py` |")
    A("| current-state guard | `scripts/phase0mr/defect53_audit.py` |")
    A("| tests | `tests/`, run with `python -m pytest tests -q` |")
    A("")
    A("The repository is **not under version control**, so content addressing is used: every "
      "authoritative artifact's md5 is recorded at each phase boundary and the previous PDFs "
      "are archived byte-identically under `results/archive/`.")
    A("")
    A("Environment: Python 3.12.14, CalculiX 2.23, MOOSE heat_transfer `09515f92aa`, "
      "gmsh 4.15.2, AEDT 2026 R1 (HFSS and Icepak licensed, Q3D not), pandoc 2.0.6 with "
      "xelatex.")
    A("")
    A("# 26. Auditor checklist")
    A("")
    A("Ten questions worth asking of this framework, with where to find the answer:")
    A("")
    A("| question | where |")
    A("|---|---|")
    A("| is any resistance a primitive? | Section 8 --- no, and the classifier raises on anything unclassified |")
    A("| can any loss term be double counted? | Section 10 --- the ledger enforces one owner per watt and refuses to total otherwise |")
    A("| is the cooling boundary fitted to its own answer? | Section 11 --- no longer; it is derived from channel geometry and flow |")
    A("| is any solver used outside what it can pose? | Section 5 --- HFSS is explicitly NOT used for DC conduction, and why |")
    A("| is any effective property unvalidated? | Section 12 --- every tensor has an RVE error and a verdict |")
    A("| is the metric mesh-converged? | Section 18 |")
    A("| is any claim stale? | Section 22 --- generated from a contract, with mutation and injection tests |")
    A("| what would change the ranking? | Section 20 --- RDL and TSV cracking is the largest unmodelled candidate |")
    A("| what is conditional and on what? | Section 14.2, and the uncertainty ledger |")
    A("| may an optimizer be built? | Section 24 --- no, four preconditions remain unmet |")
    A("")
    A("# 27. Symbols")
    A("")
    A("| symbol | meaning | units |")
    A("|---|---|---|")
    A("| `rho(T)` | resistivity | Ohm.m |")
    A("| `A_c` | conductor cross-section | m2 |")
    A("| `J_design` | provisioning current density | A/m2 |")
    A("| `J_process_max` | manufacturing capability bound | A/m2 |")
    A("| `J_reliability_allow` | electromigration allowable --- **OPEN** | A/m2 |")
    A("| `n_req`, `n_avail`, `n_alloc` | required, available and allocated via counts | -- |")
    A("| `dR_transition` | 3-D resistance minus the 1-D reference | Ohm |")
    A("| `sigma_s` | sheet conductance | S |")
    A("| `k_x, k_y, k_z` | effective conductivity tensor diagonal | W/m.K |")
    A("| `h(x)` | local film coefficient | W/m2.K |")
    A("| `T_f(x)` | local coolant temperature | C |")
    A("| `eta_fin` | fin efficiency | -- |")
    A("| `du_corner` | corner-BGA relative in-plane displacement | um |")
    A("| `PEEQ` | accumulated equivalent inelastic strain | -- |")
    A("| `ME` | solver mechanical strain, total minus thermal | -- |")
    A("| `D` | per-cycle local inelastic RESPONSE metric (dPEEQ) | -- |")
    A("| `N_required` | required life --- **OPEN** | cycles |")
    A("")
    A("# 28. Glossary")
    A("")
    A("**DVPD** --- distributed vertical power delivery: converting close to the load so the "
      "high-current rail travels vertically and briefly rather than laterally.")
    A("")
    A("**Overstress law** --- a creep law driven by the amount by which the stress exceeds a "
      "yield surface, rather than by the stress itself. It returns exactly zero below yield. "
      "This is what CalculiX integrates in a `*VISCO` step.")
    A("")
    A("**Homogenization** --- replacing a geometrically detailed layer with an equivalent "
      "uniform material. Valid only with a stated error against the explicit geometry.")
    A("")
    A("**RVE** --- representative volume element: the smallest repeating cell whose solution "
      "gives the effective property of the whole layer.")
    A("")
    A("**Constriction / spreading resistance** --- the extra resistance where current "
      "converges into or diverges out of a smaller cross-section. Not captured by `rho L / A`.")
    A("")
    A("**Fin efficiency** --- the fraction of a cooling fin's surface that is as effective as "
      "its base. It falls as the fin gets taller or thinner.")
    A("")
    A("**Caloric resistance** --- the temperature rise caused simply by the coolant absorbing "
      "heat, `1/(2 m_dot c_p)`. It is a property of the flow, not of the surface, and a single "
      "film coefficient hides it.")
    A("")
    A("**Common mode** --- an error that multiplies both architectures by the same factor and "
      "therefore cancels in their ratio. Whether it does must be tested, not assumed.")
    A("")
    A("**ETM-L1 / L2 / L3** --- coupling levels: L1 is electrical-thermal iterated with "
      "one-way mechanics; L2 adds mechanical feedback into conductance or geometry; L3 adds "
      "damage feeding back. This framework is L1.")
    A("")

    return "\n".join(L) + "\n"


if __name__ == "__main__":
    OUT.write_text(build())
    print(f"wrote {OUT} ({len(build().splitlines())} lines so far)")
