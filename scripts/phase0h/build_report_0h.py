#!/usr/bin/env python3
"""Phase-0H Sec.1/21 -- bring every CURRENT-FACING report section under the single source
of truth (DEFECT #32), then splice Phase 0H itself.

Phase 0G brought the claims ledger under CURRENT_SCIENTIFIC_STATUS.yaml but left the
Executive Summary, governing equations, validation status, novelty, limitations, publication
claims and next steps hand-written. They drifted. This script replaces each of them with a
GENERATED fragment delimited by sentinels, so a later edit to the report is either
overwritten on the next build or caught by tests/phase0h/test_current_facing.py.

Every edit asserts its anchor first, and every splice is idempotent.
"""
from __future__ import annotations
import re, subprocess, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
REP = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
CF = R / "results" / "phase0h" / "generated_current_facing.md"


def fragments(text: str) -> dict[str, str]:
    out = {}
    for m in re.finditer(r"<!-- BEGIN GENERATED: (\w+) -->\n(.*?)<!-- END GENERATED: \1 -->\n",
                         text, re.S):
        out[m.group(1)] = m.group(0)
    return out


def splice(s: str, name: str, frag: str, start_anchor: str, end_anchor: str) -> str:
    """Replace an existing generated block, or the hand-written region between anchors."""
    pat = re.compile(rf"<!-- BEGIN GENERATED: {name} -->\n.*?<!-- END GENERATED: {name} -->\n",
                     re.S)
    if pat.search(s):
        print(f"  ok  {name}: refreshed generated block")
        return pat.sub(lambda _: frag, s, count=1)
    i = s.index(start_anchor)
    j = s.index(end_anchor, i + len(start_anchor))
    print(f"  ok  {name}: replaced {j - i} chars of hand-written text")
    return s[:i] + frag + s[j:]


def place(s: str, name: str, frag: str, before: str) -> str:
    """Insert a generated fragment before `before`, or refresh it if already present.

    Using sub() here was wrong and non-idempotent: the anchor still exists after the first
    insertion, so a second build inserted a duplicate copy.
    """
    pat = re.compile(rf"<!-- BEGIN GENERATED: {name} -->\n.*?<!-- END GENERATED: {name} -->\n",
                     re.S)
    if pat.search(s):
        print(f"  ok  {name}: refreshed generated block")
        return pat.sub(lambda _: frag, s, count=1)
    assert before in s, f"anchor missing for {name}"
    print(f"  ok  {name}: inserted")
    return s.replace(before, "\n" + frag + before, 1)


def sub(s: str, old: str, new: str, what: str) -> str:
    if new in s and old not in s:
        print(f"  ok  {what} (already applied)")
        return s
    assert old in s, f"anchor missing for {what}: {old[:70]!r}"
    assert s.count(old) == 1, f"anchor not unique for {what} ({s.count(old)})"
    print(f"  ok  {what}")
    return s.replace(old, new, 1)


NARRATIVE_0H = r"""<!-- BEGIN GENERATED: phase0h_narrative -->

\newpage

# Phase 0H --- Mechanical Failure-Mechanism and Criterion Acquisition Gate (current authoritative)

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

![FIG-0H-B](FIGDIR/FIG_0H_B_mechanism_map.png)

## Global warpage does not predict the local loading

Seventy paired runs, spanning assembly model, board case, thickness, footprint, stress-free
reference and thermal boundary, test whether the quantity this project measures best can stand
in for the quantity that matters.

It cannot. Across the mounted thickness sweep **die warpage varies 3.0x (9.66 to 29.23 um)
while interface shear stays within $\pm$9 %**. Overall Spearman $\rho$ = 0.112. Worse, the sign
is not stable: $\rho$ = $-$0.793 in the free package against $+$0.349 mounted, so in the free
configuration a design change that raises warpage *lowers* interface shear.

![FIG-0H-C](FIGDIR/FIG_0H_C_warpage_not_proxy.png)

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

![FIG-0H-D](FIGDIR/FIG_0H_D_admissibility.png)

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

![FIG-0H-E](FIGDIR/FIG_0H_E_geometry_closure.png)

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

![FIG-0H-A](FIGDIR/FIG_0H_A_defect30_ranking.png)

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

![FIG-0H-F](FIGDIR/FIG_0H_F_thickness_final.png)

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
"""


def main() -> int:
    subprocess.run([sys.executable,
                    str(R / "scripts/phase0g/generate_status_sections.py")],
                   check=True, capture_output=True)
    frag = fragments(CF.read_text())
    expect = {"exec_summary", "governing_equations", "validation_status",
              "publication_claims"}
    assert expect <= set(frag), sorted(frag)
    s = REP.read_text()

    # ---- 1. Executive Summary: the whole hand-written section ---------------------------
    s = splice(s, "exec_summary", frag["exec_summary"],
               "# Executive Summary", "![**Figure 1.**")

    # ---- 2. the governing equation itself, not only its status --------------------------
    s = sub(s,
            r"""$$n_{req} = \left\lceil \frac{I}{I_{max}} \right\rceil, \qquad
  R_{field} = \frac{R_{single}}{n_{req}}, \qquad""",
            r"""$$n_{req} = \left\lceil \frac{I}{I_{max}} \right\rceil, \qquad
  n_{req} \le n_{alloc} \le n_{avail}, \qquad
  R_{field} = \frac{R_{single}}{n_{alloc}}, \qquad""",
            "R_field now uses n_alloc")
    s = sub(s,
            r"| $n_{req}, n_{avail}$ | required / available parallel conductors | -- |",
            r"| $n_{req}, n_{alloc}, n_{avail}$ | required / **allocated** / available "
            r"parallel conductors. Resistance uses $n_{alloc}$; feasibility uses "
            r"$n_{avail}$ | -- |",
            "symbol table gains n_alloc")

    # ---- 3. the two stale validation statements ----------------------------------------
    s = sub(s,
            """**Not done:** a MOOSE or Icepak cross-check of the full 3-D package thermal model with
spatially mapped Joule heat (TH-1...TH-4). This is the largest open validation item and is
carried to the roadmap.""",
            """**Done in Phase 0E, and no longer open.** The full 3-D MOOSE package cross-check with
spatially mapped Joule heat was completed as TH-1...TH-5: candidate ordering preserved exactly,
maximum discrepancy 1.66 %, mean 1.05 %. Phase 0F repeated it at the 1-kW reference on the
decisive thickness pair (2.2--2.8 K on $T_{max}$, same thickness trend, energy balance closed to
$3\\times10^{-8}$ % in both codes). Icepak remains unusable: it returned exactly 5000 K on every
object, a solver clamp from applying an external boundary condition to an internal solid/air
interface, and that result was discarded.""",
            "thermal validation no longer claims MOOSE package check is undone")
    s = sub(s,
            """  BC-B is a compliant support layer anchored to source-backed BGA geometry.""",
            """  BC-B applies `*BOUNDARY {n},1,3` --- **all three degrees of freedom** on the
  underside plane --- so it is a CLAMP, not a compliant mounted support. Phase 0G withdrew it
  as a model of a mounted package: it never recovers its own free limit (0.739 um against
  8.287 um on the identical mesh) and no support stiffness $k^*$ exists over seven decades.
  Mounted conclusions use BC_BOARD, an explicit BGA + PCB stack restrained only by 3-2-1
  anchors, which is continuous with the free package.""",
            "BC-B described as the clamp it is")

    # ---- 4. governing-equation status + validation status tables ------------------------
    s = place(s, "governing_equations", frag["governing_equations"],
              "\n# Electrical Model Validation")
    s = place(s, "validation_status", frag["validation_status"],
              "\n# Coupled ETM Physics")

    # ---- 5. publication claims ----------------------------------------------------------
    # ORDER MATTERS. The publication-claims splice consumes the "# Publication-Defensible
    # Claims" heading, so anchoring the Phase-0I-R block on that heading works once and fails
    # on every rebuild. Splice publication_claims FIRST, then anchor on its BEGIN sentinel,
    # which is stable across rebuilds.
    s = splice(s, "publication_claims", frag["publication_claims"],
               "# Publication-Defensible Claims", "\n# Next Steps")
    if "reliability_metric" in frag:
        s = place(s, "reliability_metric", frag["reliability_metric"],
                  "<!-- BEGIN GENERATED: publication_claims -->")

    # ---- 5b. the Phase-0H narrative ------------------------------------------------------
    s = sub(s, "# Phase 0G --- Assembly-Boundary, Crossover-Robustness and "
            "Mechanical-Criterion Closure (current authoritative)",
            "# Phase 0G --- Assembly-Boundary, Crossover-Robustness and "
            "Mechanical-Criterion Closure (superseded by Phase 0H)",
            "demote Phase 0G")
    s = place(s, "phase0h_narrative", NARRATIVE_0H.replace("FIGDIR", "/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0h"),
              "\n<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml")

    # ---- 6. refresh the Phase-0G generated status block too -----------------------------
    # It is generated from the same YAML, so a Phase-0H edit to the YAML must reach it. Not
    # doing this left the report asserting the very conventional-limit comparison Sec.18
    # retracts, while the generated file on disk was already correct.
    gsp = R / "results" / "phase0g" / "generated_status_sections.md"
    gs = gsp.read_text()
    start = s.index("<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml")
    m = re.search(r"\n+\\newpage\n+# References", s[start:])
    assert m, "Phase-0G status block boundary not found"
    s = s[:start] + gs.rstrip("\n") + s[start + m.start():]
    print("  ok  phase0g status block: refreshed")

    REP.write_text(s)
    print(f"\nreport now {len(s.splitlines())} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
