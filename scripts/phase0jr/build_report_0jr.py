#!/usr/bin/env python3
"""Phase-0J-R Sec.32 -- splice Phase 0J-R into the full technical report."""
from __future__ import annotations
import re, subprocess, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
REP = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
G = "/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0jr"


def place(s, name, frag, before):
    pat = re.compile(rf"<!-- BEGIN GENERATED: {name} -->\n.*?<!-- END GENERATED: {name} -->\n",
                     re.S)
    if pat.search(s):
        print(f"  ok  {name}: refreshed"); return pat.sub(lambda _: frag, s, count=1)
    assert before in s, f"anchor missing for {name}"
    print(f"  ok  {name}: inserted"); return s.replace(before, frag + before, 1)


def sub(s, old, new, what):
    if new in s and old not in s:
        print(f"  ok  {what} (already applied)"); return s
    assert old in s and s.count(old) == 1, f"anchor problem for {what}"
    print(f"  ok  {what}"); return s.replace(old, new, 1)


NARRATIVE = r"""<!-- BEGIN GENERATED: phase0jr_narrative -->

\newpage

# Phase 0J-R --- Primary Life-Law Access, Reproduction and Transferability Closure (current authoritative)

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

![FIG-0JR-A](FIGDIR/FIG_0JR_A_syed_version_audit.png)

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

![FIG-0JR-C](FIGDIR/FIG_0JR_C_metric_definitions.png)

## The reproduction Phase 0J could not attempt

**Tolerances declared beforehand:** reproduce the paper's own $\pm$25 % claim, and require the
two **independently fitted** constants to recover a consistent $w_{acc}/\varepsilon_{acc}$ to
10 %.

| test | result | verdict |
|:--|:--|:--|
| worst error, Table 3 independent validation package | **11.7 %** | **PASS** |
| $w/\varepsilon$ from $C'$ and $W'$ across 4 configurations | 28.78--30.02 MPa, **spread 4.2 %** | **PASS** |

**No digitisation was used** --- every value is a printed table entry.

![FIG-0JR-B](FIGDIR/FIG_0JR_B_syed_reproduction.png)

## The zero-dwell finding was wrong

Phase 0J reported a triangular waveform with **zero dwell**. The solver's own `NT` output carries
the full hot value **82.8605 °C at t = 0.002 s** --- the first increment of a 300 s step. A ramp
would give 25.0004 °C.

> **The waveform is a SQUARE WAVE: instantaneous step, then a 300 s HOLD at each extreme.
> Syed's TC3 has 5-minute dwells --- exactly ours.**

And the dependence is mild. Over a **30x** change in dwell the absolute metric moves **+17 %
(Z1) / +22 % (Z2)** and the **relative** result moves **$\pm$2 %**, because the overstress
formulation self-limits as $\sigma \to \sigma_y$.

![FIG-0JR-D](FIGDIR/FIG_0JR_D_dwell_sensitivity.png)

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

![FIG-0JR-E](FIGDIR/FIG_0JR_E_on_syed_calibration.png)

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

![FIG-0JR-F](FIGDIR/FIG_0JR_F_life_by_primary_law.png)

## Does Z2's +1.688 W buy a real advantage?

> **YES --- relative lifetime difference validated; absolute life unavailable.**
> **+1.688 W, 1.3 % of 126.1 W, buys 1.21--1.38x solder fatigue life.**

![FIG-0JR-G](FIGDIR/FIG_0JR_G_electrical_vs_life.png)

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
"""


def main() -> int:
    subprocess.run([sys.executable, str(R / "scripts/phase0j/build_report_0j.py")],
                   check=True, capture_output=True)
    s = REP.read_text()
    s = sub(s, "# Phase 0J --- SAC305 Life Law, Mission, and G2 Evaluation (current authoritative)",
            "# Phase 0J --- SAC305 Life Law, Mission, and G2 Evaluation "
            "(SUPERSEDED by Phase 0J-R)", "demote Phase 0J")
    s = place(s, "phase0jr_narrative", NARRATIVE.replace("FIGDIR", G),
              "\n<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml")
    REP.write_text(s)
    print(f"\nreport now {len(s.splitlines())} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
