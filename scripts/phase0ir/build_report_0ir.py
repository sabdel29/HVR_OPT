#!/usr/bin/env python3
"""Phase-0I-R Sec.25 -- splice Phase 0I-R into the full technical report.

Phase 0I is NOT removed and NOT contradicted. Its numbers stand. It is demoted from "current
authoritative" to "rescoped by Phase 0I-R", and this section states exactly which of its
claims survive unchanged, which survive with a corrected LABEL, and which are withdrawn.
"""
from __future__ import annotations
import re, subprocess, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
REP = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
G = "/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0ir"


def place(s: str, name: str, frag: str, before: str) -> str:
    pat = re.compile(rf"<!-- BEGIN GENERATED: {name} -->\n.*?<!-- END GENERATED: {name} -->\n",
                     re.S)
    if pat.search(s):
        print(f"  ok  {name}: refreshed")
        return pat.sub(lambda _: frag, s, count=1)
    assert before in s, f"anchor missing for {name}"
    print(f"  ok  {name}: inserted")
    return s.replace(before, frag + before, 1)


def sub(s: str, old: str, new: str, what: str) -> str:
    if new in s and old not in s:
        print(f"  ok  {what} (already applied)"); return s
    assert old in s, f"anchor missing for {what}"
    assert s.count(old) == 1, f"anchor not unique for {what}"
    print(f"  ok  {what}")
    return s.replace(old, new, 1)


NARRATIVE = r"""<!-- BEGIN GENERATED: phase0ir_narrative -->

\newpage

# Phase 0I-R --- Reliability-Metric, Claim-Scope and Report-Consistency Closure (current authoritative)

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

![FIG-0IR-A](FIGDIR/FIG_0IR_A_strain_decomposition.png)

![FIG-0IR-B](FIGDIR/FIG_0IR_B_strain_vs_energy.png)

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

![FIG-0IR-D](FIGDIR/FIG_0IR_D_electrical_resolution.png)

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

![FIG-0IR-C](FIGDIR/FIG_0IR_C_relative_life_exponent.png)

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

![FIG-0IR-E](FIGDIR/FIG_0IR_E_warpage_vs_damage.png)

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
"""


def main() -> int:
    subprocess.run([sys.executable, str(R / "scripts/phase0i/build_report_0i.py")],
                   check=True, capture_output=True)
    s = REP.read_text()
    s = sub(s, "# Phase 0I --- Vertical Integration and Local Reliability Physics "
            "(current authoritative)",
            "# Phase 0I --- Vertical Integration and Local Reliability Physics "
            "(rescoped by Phase 0I-R)", "demote Phase 0I")
    s = place(s, "phase0ir_narrative", NARRATIVE.replace("FIGDIR", G),
              "\n<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml")
    REP.write_text(s)
    print(f"\nreport now {len(s.splitlines())} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
