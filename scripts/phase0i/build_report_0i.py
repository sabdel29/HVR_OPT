#!/usr/bin/env python3
"""Phase-0I Sec.28 -- splice Phase 0I into the full technical report.

The Phase-0H negative result is NOT removed. It is retained, demoted from "current
authoritative", and the Phase-0I section explains what changed once the two things Phase 0H
named as missing -- z-placement as a real variable, and temperature-dependent failure physics
-- were actually added.
"""
from __future__ import annotations
import re, subprocess, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
REP = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
G = "/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0i"


def place(s: str, name: str, frag: str, before: str) -> str:
    pat = re.compile(rf"<!-- BEGIN GENERATED: {name} -->\n.*?<!-- END GENERATED: {name} -->\n",
                     re.S)
    if pat.search(s):
        print(f"  ok  {name}: refreshed")
        return pat.sub(lambda _: frag, s, count=1)
    assert before in s, f"anchor missing for {name}"
    print(f"  ok  {name}: inserted")
    return s.replace(before, "\n" + frag + before, 1)


def sub(s: str, old: str, new: str, what: str) -> str:
    if new in s and old not in s:
        print(f"  ok  {what} (already applied)"); return s
    assert old in s, f"anchor missing for {what}"
    assert s.count(old) == 1, f"anchor not unique for {what}"
    print(f"  ok  {what}")
    return s.replace(old, new, 1)


NARRATIVE = r"""<!-- BEGIN GENERATED: phase0i_narrative -->

\newpage

# Phase 0I --- Vertical Integration and Local Reliability Physics (current authoritative)

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

![FIG-0I-A](FIGDIR/FIG_0I_A_cross_sections.png)

## Which rail crosses the substrate is an architecture choice

![FIG-0I-B](FIGDIR/FIG_0I_B_power_paths.png)

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

![FIG-0I-D](FIGDIR/FIG_0I_D_workflow.png)

Validation is 4/4: free expansion exact to 0.000 % with zero inelastic strain; creep rate
x535 and yield -57 % over the operating range; -49.6 % stress relaxation in a 600 s
hold; cycle stabilisation to 0.4 %. Convergence is mesh **1.90 %**, CETOL **0.02 %**, corner
exclusion band **6.4 %** --- and including the corner *lowers* the value, so the metric is not
corner-dominated. **This is the first local mechanical metric in the project to pass mesh,
tolerance and regularisation stability together**, against interface peel (19--20 % per
refinement, excluded in Phase 0C) and p99 shear (non-monotone, rejected in Phase 0H).

![FIG-0I-F](FIGDIR/FIG_0I_F_hysteresis.png)

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

![FIG-0I-C](FIGDIR/FIG_0I_C_thermal.png)

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

![FIG-0I-H](FIGDIR/FIG_0I_H_loss_vs_damage.png)

No architecture dominates. What the model actually delivers is a **metric ratio**: Z2 is
**35.8 % below** Z1 and Z4 **12.4 % above** it, and Phase 0I-R shows both are RESOLVED --- 5.8x
and 5.1x their spread across every material, mesh and regularisation perturbation, with all
three inelastic measures agreeing to within 2 pp.

Converting that to life requires a fatigue exponent. In $N_f = C\,\Delta\varepsilon^{-m}$ the
constant $C$ cancels in a ratio but **the exponent $m$ does not**. Phase 0I quoted "1.9--3.8x"
from an $m$ = 1.5--3 range that was **never sourced**. Over $m$ = 0.5--5 the Z2/Z1 ratio spans
1.25 to 9.18 --- a factor of 7.4 from the exponent alone. Every life ratio in this project is
therefore labelled **PARAMETRIC LIFE-LAW SENSITIVITY**, and no lifetime is claimed.

![FIG-0I-I](FIGDIR/FIG_0I_I_relative_life.png)

## What this changes about global warpage

Phase 0H found global warpage did not correlate with its local quantity ($\rho$ = 0.11 against
smeared interface shear). Against a proper damage metric it correlates **perfectly within an
architecture** ($\rho$ = 1.000 in all three) and **+0.909 pooled**. The Phase-0H finding
stands as a statement about smeared shear, which was a poor proxy; it does not stand as a
statement about local damage.

But warpage **overstates the benefit**. Over the same thickness range warpage moves
29.7--52.6 % while damage moves only 5.6--17.2 % --- a 3--5x exaggeration.

![FIG-0I-G](FIGDIR/FIG_0I_G_damage_vs_thickness.png)

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
"""


def main() -> int:
    subprocess.run([sys.executable, str(R / "scripts/phase0g/generate_status_sections.py")],
                   check=True, capture_output=True)
    subprocess.run([sys.executable, str(R / "scripts/phase0h/build_report_0h.py")],
                   check=True, capture_output=True)
    s = REP.read_text()
    s = sub(s, "# Phase 0H --- Mechanical Failure-Mechanism and Criterion Acquisition Gate "
            "(current authoritative)",
            "# Phase 0H --- Mechanical Failure-Mechanism and Criterion Acquisition Gate "
            "(superseded by Phase 0I)", "demote Phase 0H")
    s = place(s, "phase0i_narrative", NARRATIVE.replace("FIGDIR", G),
              "\n<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml")
    REP.write_text(s)
    print(f"\nreport now {len(s.splitlines())} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
