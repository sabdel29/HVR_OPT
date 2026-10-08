#!/usr/bin/env python3
"""Phase-0G Sec.19/20 -- splice Phase 0G into the full technical report.

Three edits, each of which is asserted before it is applied:

  1. mark the Phase-0F gate SUPERSEDED (it is no longer the current authority);
  2. mark the historical Positive/Negative Results sections as historical -- they are a
     Phase-0B..0D-R record and several of their claims are now withdrawn (DEFECT #29);
  3. append the Phase 0G narrative, then the GENERATED current-status block.

The generated block is inserted verbatim from results/phase0g/generated_status_sections.md
so that tests/phase0g/test_status_sections.py can verify the report has not drifted from the
YAML.
"""
from __future__ import annotations
import subprocess, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
REP = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
GEN = R / "results" / "phase0g" / "generated_status_sections.md"
G = "/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0g"


def sub(s: str, old: str, new: str, what: str) -> str:
    assert old in s, f"anchor missing for {what}: {old[:70]!r}"
    assert s.count(old) == 1, f"anchor not unique for {what} ({s.count(old)} hits)"
    print(f"  ok  {what}")
    return s.replace(old, new)


NARRATIVE = r"""
\newpage

# Phase 0G --- Assembly-Boundary, Crossover-Robustness and Mechanical-Criterion Closure (current authoritative)

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
49.055** at all nine thicknesses, and an independent hand check (89.7768 mW/VR $\times$ 49 =
4.399 W) agrees. This is **DEFECT #30**.

Corrected, ARCH_B is monotonically increasing and its optimum sits on the **thin boundary** in
**9 corners of 9** spanning TSV current-density policy, crowding, allocation policy and copper
resistivity. ARCH_A retains a genuine interior optimum at $h = 0.90$ mm, resolved at 88x the
0.0977 mW numerical floor --- but it is **8.6 mW deep on a 125 W budget (0.0069 %)**, and the
ARCH_A/ARCH_B gap at fixed thickness is 52x larger than the whole depth of it.

![FIG-0G-A](FIGDIR/FIG_0G_A_defect30.png)

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

![FIG-0G-B](FIGDIR/FIG_0G_B_no_kstar.png)

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

![FIG-0G-C](FIGDIR/FIG_0G_C_assembly_regimes.png)

Across the whole envelope, **every physically constructed assembly gives the free-package
sign**: thicker is better, $S_h = -0.039$ to $-0.886$. Only the clamp reverses it.

![FIG-0G-D](FIGDIR/FIG_0G_D_Sh_by_model.png)

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

![FIG-0G-E](FIGDIR/FIG_0G_E_footprint_flip.png)

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

![FIG-0G-F](FIGDIR/FIG_0G_F_invariance.png)

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

Nor would a conventional limit discriminate. Warpage stays **below 40 um** across every
assembly, reference state and thermal boundary examined --- one to two orders of magnitude
below the hundreds-of-micrometres band conventional for this package class. A criterion
satisfied by every design in the space is not active.

**G2 remains NOT TESTED --- not failed.** It has never been given a threshold to test against.
The $\varepsilon$ sweep is therefore a **parametric preference sensitivity** and never a
feasibility test, and it is reported in both assembly states because the answer depends on
which one is assumed: the mounted floor is 14.03 um, so the entire free-package range
(1.3--11.2 um) is unreachable once the package is on a board.

![FIG-0G-G](FIGDIR/FIG_0G_G_epsilon.png)

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
"""


def main() -> int:
    subprocess.run([sys.executable,
                    str(R / "scripts/phase0g/generate_status_sections.py")], check=True)
    s = REP.read_text()

    s = sub(s, "# Phase 0F --- 1-kW Reference-Scale ETM Gate (current authoritative)",
            "# Phase 0F --- 1-kW Reference-Scale ETM Gate (superseded by Phase 0G)",
            "demote Phase 0F")

    s = sub(s, "# Positive Results\n",
            "# Positive Results (historical record --- Phases 0B..0D-R)\n\n"
            "> **This section is a historical record, not a statement of current status.** "
            "Several claims below were superseded in Phases 0E, 0F and 0G --- notably "
            "*win/win/win substrate thickness* (the swept thicknesses are unbuildable) and "
            "*HVR footprint is a genuine ETM opposition* (the sign is assembly-state "
            "dependent and reverses on every explicit board). For what this project currently "
            "claims, see **Current scientific status** below, which is generated from "
            "`results/CURRENT_SCIENTIFIC_STATUS.yaml`.\n",
            "mark Positive Results historical")

    s = sub(s, "# Negative and Null Results\n",
            "# Negative and Null Results (historical record --- Phases 0B..0D-R)\n\n"
            "> **This section is a historical record, not a statement of current status.** "
            "Items 4, 5 and 6 were superseded in Phases 0E and 0G: the placement spread is "
            "46.7 % and not 188.8 %, the footprint exchange rate is 11.48--12.86 W/um and not "
            "16.2 W/um, and an architecture-dependent thickness difference does appear at "
            "1 kW once DEFECT #30 is fixed --- though not as the interior optimum Phase 0F "
            "reported. See **Current scientific status** below.\n",
            "mark Negative Results historical")

    gen = GEN.read_text()
    body = NARRATIVE.replace("FIGDIR", G)
    s = sub(s, "\n# References",
            f"\n{body}\n\\newpage\n\n{gen}\n\\newpage\n\n# References",
            "append Phase 0G narrative + generated status")

    REP.write_text(s)
    print(f"\nreport now {len(s.splitlines())} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
