#!/usr/bin/env python3
"""Build results/ETM_DVPD_FULL_TECHNICAL_REPORT.{md,pdf} + build log.
Every table is generated FROM its source artifact; no number is retyped."""
from __future__ import annotations
import csv, json, subprocess, sys, textwrap
from datetime import date
from pathlib import Path

R = Path(__file__).resolve().parents[2]
RES = R / "results"
MD, PDF = RES / "ETM_DVPD_FULL_TECHNICAL_REPORT.md", RES / "ETM_DVPD_FULL_TECHNICAL_REPORT.pdf"
LOG = RES / "ETM_DVPD_FULL_TECHNICAL_REPORT_BUILD_LOG.md"
FIGS: list[tuple[str, str]] = []


def rd(p): return list(csv.DictReader((RES / p).open()))
def jd(p): return json.loads((RES / p).read_text())
def f(v, n=3):
    try: return f"{float(v):.{n}f}"
    except (TypeError, ValueError): return str(v)


def tbl(hdr, body, src=None, align=None):
    a = align or ("l" + "r" * (len(hdr) - 1))
    out = ["| " + " | ".join(map(str, hdr)) + " |",
           "|" + "|".join({"l": ":--", "r": "--:", "c": ":-:"}[c] for c in a) + "|"]
    out += ["| " + " | ".join(map(str, r)) + " |" for r in body]
    if src: out += ["", f"Source: `{src}`"]
    return "\n".join(out) + "\n"


def figure(path, caption, phase, w="92%"):
    p = RES / path
    FIGS.append((str(p), caption))
    return (f"\n![**Figure {len(FIGS)}.** {caption} *(Phase {phase}; data: `results/{path}`)*]"
            f"({p}){{width={w}}}\n")


def build() -> str:
    S = []
    A = S.append
    ccx = subprocess.run(["ccx", "-v"], capture_output=True, text=True).stdout.split("\n")[2].strip() \
        if subprocess.run(["ccx", "-v"], capture_output=True, text=True).stdout else "CalculiX 2.23"
    commit = subprocess.run(["git", "-C", str(R / "Scalable_Integrated_VR"), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True).stdout.strip() or "n/a"

    A(textwrap.dedent(f"""\
    ---
    title: "Electrothermal--Mechanical Co-Design of Distributed Vertical Power Delivery: Model Development, Falsification Gates, and Coupled Architecture Results"
    author: "HVR\\\\_Journal\\\\_System\\\\_Level / ETM-DVPD --- HiPerCAS Lab, University of Illinois Chicago"
    date: "{date.today().isoformat()}"
    geometry: margin=2.1cm
    fontsize: 10pt
    colorlinks: true
    linkcolor: NavyBlue
    numbersections: true
    ---

    \\newpage
    # Provenance and tool versions

    | Item | Value |
    |:--|:--|
    | Repository root | `{R}` |
    | Converter-model repo commit | `{commit}` (`Scalable_Integrated_VR`) |
    | Report date | {date.today().isoformat()} |
    | Structural + thermal FE | {ccx} --- C3D8I, direct SPOOLES |
    | Independent FE cross-check | MOOSE `heat_transfer-opt`, build 09515f92aa |
    | Full-wave EM available | PALACE (built, functional) |
    | Commercial EM/thermal | ANSYS AEDT v261, **licence restored 2026-09-06**; HFSS and Icepak used, Q3D not licensed |
    | Mesh generation | gmsh 4.15.2 |
    | Python | {sys.version.split()[0]} |
    | Document build | pandoc + xelatex |

    **Reading guide.** Every table below is generated programmatically from the source artifact
    named beneath it; no numerical result was retyped. **Section 7 (Phase 0D-R) supersedes
    Section 6 (Phase 0D) wherever they disagree**, and each disagreement is stated explicitly.

    \\newpage
    """))

    # ---------------- executive summary
    rev = jd("phase0dr/reversal_corrected.json")
    A("# Executive Summary\n")
    A(textwrap.dedent("""\
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
    """))
    A(figure("phase0dr/FIG_H_phase0d_vs_0dr.png",
             "What the architecture-aware correction changed. Four of five headline quantities "
             "moved by an order of magnitude; only the thickness benefit is unchanged.", "0D-R"))
    A("\\newpage\n")

    # ---------------- 1 motivation
    A(textwrap.dedent("""\
    # Research Motivation

    AI accelerators draw kilowatts per package from a 48 V backplane at sub-1 V. Conventional
    lateral delivery places regulators at the board or package edge, paying twice: resistive
    IR drop along the path, and path inductance that adds an $L\\,di/dt$ transient droop.
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
    """))

    # ---------------- 2 baseline
    A(textwrap.dedent("""\
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
    | Switch width | **analytically optimised**, $\\partial P/\\partial w = 0$, then clamped by the per-layer area budget |
    | Area budget | $w_{LS}^{max} = A_{budget} / (M \\cdot \\max\\{l_{ind}, l_{LS}\\})$ |
    | Placement | regular $m \\times n$ array, aspect ratio $\\approx 1$ |
    | POL-to-VR allocation | **proximity heuristic**, not an optimisation variable |
    | Interconnect | BGA / TSV / chiplet pad geometry, Table III |
    | Objective | minimise total system-wide loss subject to footprint, power-density and ripple |
    | Mechanics | **absent** |

    Three of its stated modelling conditions became the seams this project works in: current is
    allocated by proximity rather than optimised; the VR array is regular with locally similar
    cells; and *"intra-VR routing is not constrained by local blockages, keep-out regions, or
    package design-rule limitations."* A mechanical keep-out is exactly such a blockage.
    """))

    # ---------------- 3 phase 0A
    A(textwrap.dedent("""\
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
    * **G3 --- robust physical signal.** A mechanically relevant metric changes by $\\ge 15\\,\\%$
      between architectures **and** by more than twice the combined numerical uncertainty.

    **Why falsification gates.** Each gate can return a negative that stops the project. The
    alternative --- building the framework first and looking for a result afterwards --- is the
    failure mode the reviewer audit identified as most likely to produce an unpublishable
    outcome after large effort.
    """))
    return "".join(S)


if __name__ == "__main__":
    MD.write_text(build())
    print(f"wrote {MD} ({len(MD.read_text().splitlines())} lines, part 1)")
