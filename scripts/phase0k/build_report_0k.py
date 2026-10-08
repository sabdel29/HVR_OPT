#!/usr/bin/env python3
"""Phase-0K Sec.32 -- splice Phase 0K into the full technical report."""
from __future__ import annotations
import re, subprocess, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
REP = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
G = "/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0k"


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


NARRATIVE = r"""<!-- BEGIN GENERATED: phase0k_narrative -->

\newpage

# Phase 0K --- Mission Definition, Absolute-Life Identifiability and G2 Decision Closure (current authoritative)

**Verdict: MISSION REQUIREMENT STILL OPEN --- ABSOLUTE-LIFE CALIBRATION ALSO REQUIRED.**
**Both. The second is not a consequence of the first.**
**G2 remains NOT TESTED. The optimizer is not justified and was not built.**

## Four things that must never be conflated

| | status |
|:--|:--|
| **RELATIVE LIFE** | **VALIDATED** --- Z2/Z1 = 1.21--1.38x across four admitted primary-source formulations |
| **CONDITIONAL ABSOLUTE LIFE** | numerical predictions exist, **NOT VALIDATED** --- the admitted formulations disagree 4.1x |
| **REQUIRED LIFE** | **OPEN** --- no field or product requirement exists anywhere |
| **G2** | **NOT TESTED** |

Nine current-facing statements still described a project that could not predict life, three
phases after it could (**DEFECT #38**). All repaired at the source of truth; six guards added,
each self-tested against the verbatim sentence that was standing and each negative-tested to
failure.

## "N_required is the sole blocker" is false

Phase 0J-R recorded the required life as the only thing standing between the project and a G2
decision. Tested formally at $N_{required} = 1500$:

| | strain family (Eq. 14/16) | energy family (Eq. 15/17) |
|:--|:--|:--|
| Z1 | 2279--2499 $\rightarrow$ **PASS** | 482--610 $\rightarrow$ **FAIL** |
| Z2 | 2925--3206 $\rightarrow$ **PASS** | 581--736 $\rightarrow$ **FAIL** |

Both architectures pass under one admitted family and fail under the other. **Mission definition
alone produces no decision.** There are **TWO OPEN PIECES**: the system mission, and an
absolute-life calibration or a decision region robust to model form.

## The robust decision map, built before any experiment was designed

All four admitted absolute formulations, applied independently over a 601-point log grid.

```
ROBUST ALL PASS        N_required <=   474
MODEL-FORM AMBIGUOUS     474 < N_required <= 3206      a factor of 6.8
ROBUST ALL FAIL        N_required >   3206
```

> **Is there any $N_{required}$ at which all models agree Z1 fails and Z2 passes?**
> Z1 fails under every law only above **2499**. Z2 passes under every law only below **581**.
> **DISJOINT. Zero of 601 grid points. NO.**

The reason is structural: the **model-form spread within one architecture is 5.2x** while the
**architecture separation is 1.21--1.38x**. A 5.2x uncertainty cannot resolve a 1.3x effect at
any requirement. **An experimental absolute-life calibration is NECESSARY before mechanics can
alter the feasible architecture set.**

![FIG-0K-A](FIGDIR/FIG_0K_A_g2_decision_map.png)

## Mission: searched, and genuinely absent

The entire repository and all supplied material were searched for service life, required cycles,
cold boots, qualification targets, field lifetime, availability and duty cycle. **Nothing.**
Every `n_required` in this repository is the **TSV via count**. $N_{required}$ is **USER INPUT
REQUIRED**, now enforced mechanically: the contract file holds only `USER_REQUIRED` / `UNKNOWN`
/ `NOT_APPLICABLE`, and the tool refuses to emit a number without provenance, refuses to treat a
qualification count as a field mission, and refuses to collapse a multi-bin spectrum.

Illustrative only --- never a requirement:

| scenario | $N_{required}$ | region |
|:--|--:|:--|
| 5 y, 1 cold boot/day | 1 826 | **AMBIGUOUS** |
| 7 y, 2 boots/week + 1 workload cycle/day | 3 287 | ROBUST ALL FAIL |
| 5 y, 1 boot/day + 4 workload cycles/day | 9 131 | ROBUST ALL FAIL |
| 3 y, never powered down | 0 | mechanism not life-limiting |

**Every non-trivial illustrative mission lands in the ambiguous band or worse.**

## Auditing "one board-level test fixes everything"

**One condition cannot identify the law.** One measured life is one equation, each law has one
free constant, and both fit it exactly. Residual degrees of freedom for discrimination: **zero**.

**But one condition does more than expected for this particular comparison.** Forced through the
measured point, both laws extrapolate to the other architectures through their own metric ratio:
Z1 becomes exact, **Z2 known to 6.3 %** and Z4 to 3.0 % under *either* law, because the three
architectures sit within 6 % of each other in $w/\varepsilon$. Across 3721 what-if cells the
**ambiguous region vanishes**: 50.8 % all-pass, 47.6 % all-fail, 1.6 % a genuine G2 pass, **0 %
ambiguous**.

What it does **not** license is extrapolation to a **different cycle**, where the two laws
diverge by up to 85 %.

![FIG-0K-E](FIGDIR/FIG_0K_E_calibration_vs_mission.png)

## What actually discriminates the two laws

$$D = \frac{\varepsilon_B/\varepsilon_A}{w_B/w_A} = \frac{(w/\varepsilon)_A}{(w/\varepsilon)_B}$$

**Discrimination comes from spanning $w/\varepsilon$, not from maximising damage.** Eight
candidate profiles were simulated on the graded Syed-matched mesh:

| condition | T range | $\Delta T$ | **$w/\varepsilon$ (MPa)** |
|:--|:--|--:|--:|
| **COLD_SHALLOW** | $-$40 / $+$25 °C | 65 | **209.2** |
| OP_BASELINE | 25 / 82.9 | 57.9 | 126.9 |
| **HOT_SHALLOW** | $+$55 / $+$125 °C | 70 | **113.1** |

The creep law sees the **overstress** $\sigma - \sigma_y(T)$, and $\sigma_y$ is high at low
temperature. **Temperature range moves $w/\varepsilon$ by 85 %; $\Delta T$ alone by 21 %; dwell
by only 14 %.**

| candidate experiment | D | laws differ by | $\sigma$ at $\beta$=6, n=16 |
|:--|--:|--:|--:|
| **COLD_SHALLOW vs HOT_SHALLOW** | **1.849** | **84.9 %** | **6.19** |
| one architecture, two dwells | 1.144 | 14.4 % | 1.4 |
| **two ARCHITECTURES at one profile** | **1.063** | **6.3 %** | **< 1** |

**Two architectures at one profile is nearly blind to model form** --- it validates the relative
claim but cannot identify the law.

![FIG-0K-C](FIGDIR/FIG_0K_C_discrimination.png)

## The minimum identifiable design

> **2 architectures $\times$ 2 conditions $\times$ 16 specimens = 64 packages.**
> Z1 and Z2, at $-$40/$+$25 °C and $+$55/$+$125 °C, 5-min dwells, 3 °C/min.

**Z4 is excluded** on value-of-information: D = 1.03, and its predicted life sits inside the
6.3 % post-calibration spread. **n = 16** gives $>$ 6$\sigma$ at the pessimistic $\beta$ = 6,
matches Syed's own cell size, and sits at the point where the **8 % simulation uncertainty caps
the experiment at 7.7$\sigma$** --- beyond that, specimens buy nothing. Failure definition is
Syed's exact rule, $>$ 300 $\Omega$ confirmed by ten further events, with **mean life** reported
and $\beta$ **estimated, not assumed**.

**This experiment has not been run.** No measurements exist and no constant has been fitted to
hypothetical data.

![FIG-0K-F](FIGDIR/FIG_0K_F_workflow.png)

## The ETM trade-off, preserved and not overstated

> **$+$1.688 W --- 1.3 % of 126.1 W --- buys $+$21--38 % RELATIVE solder-fatigue life.**

Not converted into "buys X cycles". And an honest limit: even after perfect calibration the
robust G2-pass band is only **17 % wide** in $N_{required}$. A 1.2--1.4x advantage reliably buys
**margin**; it flips a **pass/fail** only if the requirement lands in that window.

## G2, priority, and the optimizer

$$\textbf{G2 = NOT TESTED}$$

> **Recommendation: MISSION + EXPERIMENT IN PARALLEL.**

Every non-trivial illustrative mission lands in the ambiguous band or worse, so the mission alone
will probably not decide G2; the calibration alone cannot either, since it needs a requirement to
test against; the two are independent and neither blocks the other.

All four optimizer-gate conditions fail or are unreachable. **THE GLOBAL OPTIMIZER IS NOT
SCIENTIFICALLY JUSTIFIED AND WAS NOT BUILT.** Full detail:
`results/phase0k/PHASE0K_MISSION_AND_ABSOLUTE_LIFE_GATE.md`.

<!-- END GENERATED: phase0k_narrative -->
"""


def main() -> int:
    subprocess.run([sys.executable, str(R / "scripts/phase0jr/build_report_0jr.py")],
                   check=True, capture_output=True)
    s = REP.read_text()
    s = sub(s, "# Phase 0J-R --- Primary Life-Law Access, Reproduction and Transferability "
            "Closure (current authoritative)",
            "# Phase 0J-R --- Primary Life-Law Access, Reproduction and Transferability "
            "Closure (extended by Phase 0K)", "demote Phase 0J-R")
    s = place(s, "phase0k_narrative", NARRATIVE.replace("FIGDIR", G),
              "\n<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml")
    REP.write_text(s)
    print(f"\nreport now {len(s.splitlines())} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
