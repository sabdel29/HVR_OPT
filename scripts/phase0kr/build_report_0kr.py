#!/usr/bin/env python3
"""Phase-0K-R Sec.33 -- splice Phase 0K-R into the full technical report."""
from __future__ import annotations
import re, subprocess, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
REP = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
G = "/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0kr"


def place(s, name, frag, before):
    pat = re.compile(rf"<!-- BEGIN GENERATED: {name} -->\n.*?<!-- END GENERATED: {name} -->\n", re.S)
    if pat.search(s):
        print(f"  ok  {name}: refreshed"); return pat.sub(lambda _: frag, s, count=1)
    assert before in s, f"anchor missing for {name}"
    print(f"  ok  {name}: inserted"); return s.replace(before, frag + before, 1)


def sub(s, old, new, what):
    if new in s and old not in s:
        print(f"  ok  {what} (already applied)"); return s
    assert old in s and s.count(old) == 1, f"anchor problem for {what}"
    print(f"  ok  {what}"); return s.replace(old, new, 1)


NARRATIVE = r"""<!-- BEGIN GENERATED: phase0kr_narrative -->

\newpage

# Phase 0K-R --- Experimental-Domain and Statistical-Design Closure (current authoritative)

**Verdict: LOW-TEMPERATURE DATA INSUFFICIENT --- ORIGINAL PROFILE WITHDRAWN.**
Two secondary corrections: a within-domain replacement pair was found, and the specimen count
rises from **16 to 34 per cell**. One limitation no design removes: the **stress** domain is
violated by every profile, so the experiment is **ready to execute with a declared limitation,
not frozen**.

## Where the project stands

| | status |
|:--|:--|
| **RELATIVE LIFE** | **VALIDATED** --- Z2/Z1 = 1.21--1.38x across four admitted primary-source formulations. **Unchanged by this phase.** |
| **CONDITIONAL ABSOLUTE LIFE** | model-form uncertain at 4.1x; 5.2x across all four formulations |
| **REQUIRED LIFE** | **OPEN** --- no field or product requirement exists anywhere |
| **ABSOLUTE G2** | needs **BOTH** a mission and a calibration, unless the real $N_{required}$ falls where all admitted models already agree |
| **EXPERIMENT** | designed, domain- and power-audited, **ready to execute with a declared limitation** |
| **NEXT WORK** | mission input **and** experiment preparation, **in parallel** |

## DEFECT #39

The Phase-0K *narrative* was current; the *generated* current-status fragments were not. "Exact
next work" still read **"PHASE 0K --- SYSTEM-OWNER MISSION DEFINITION"** and still asserted the
remaining blocker was a required life --- the exact claim Phase 0K withdrew. **No Phase-0K result
appeared in current-facing text at all.** Repaired at the source of truth; four new guards, each
self-tested on the verbatim standing sentence and negative-tested to failure; and the **final
Markdown and final PDF text** re-audited after generation, not before.

## The constitutive domain, read from the card

| | calibration |
|:--|:--|
| **creep** (Yuan 2023 Table 26, 19 points) | **45, 80, 115, 150 °C** · **7.51--15.92 MPa** |
| **plastic** (Chaboche) | $-$40 ... 122 °C |

**The card rows at $-$40, 0 and 25 °C are already extrapolated on creep.** Every result this
project has produced uses a cycle whose cold half sits at 25 °C, 20 K below the floor.

## The $-$40 °C profile is withdrawn

| COLD_SHALLOW $-$40 $\rightarrow$ $+$25 °C | |
|:--|:--|
| **damage accumulated below the 45 °C floor** | **100 %** |
| damage-weighted median driving overstress | **114.9 MPa**, the worst of any candidate |
| classification | **INVALID FOR MODEL-DISCRIMINATION DESIGN** |

**The model cannot be extended.** Seven targeted searches: the low-temperature SAC305
literature exists and is the **wrong regime** --- 4 of 5 retrieved constitutive works are
**high-strain-rate/impact**, 0 are creep. At $-$40 °C the homologous temperature is
**0.475**, below where creep governs, so steady-state creep tests there are impractically long
and are not performed --- and Syed 2001 explicitly excludes fast loading from the creep
framework. **The model is NOT extended**, and no validation document is produced, because
producing one would mean inventing the data it validated.

> **The Phase-0K claims D = 1.849, 85 % separation and 6.19 σ are WITHDRAWN as current.**

![FIG-0KR-A](FIGDIR/FIG_0KR_A_domain.png)

## A within-domain replacement

Eight profiles with $T_{min} \ge$ 45 °C were solved. The exploitable physics: the creep law sees
the **overstress** $\sigma_{eq}-\sigma_y(T)$, and $\sigma_y$ falls with temperature, so a
cold-in-domain cycle sustains far more stress per unit creep. **Within the domain, temperature
band moves $w/\varepsilon$ by 44 %; dwell by only 2--3 %.**

> **SELECTED: 45 $\rightarrow$ 125 °C  +  110 $\rightarrow$ 150 °C, 5-min dwells, 3 °C/min**
> **D = 1.4395**, 44.0 % separation, expected discrimination **Z = 3.44**.

Selection was **composite, not max-D**: a 15-min-dwell variant scores D = 1.4721 but costs
**46 extra days per cell** for a 2 % gain and was rejected on the predeclared rule. **The
redesign costs 41 % of the discriminating power and buys validity.**

![FIG-0KR-B](FIGDIR/FIG_0KR_B_pair_comparison.png)

## The limitation no profile removes

Phase 0J-R checked the **end-of-hold** overstress ($\approx$ 15 MPa, inside the window) and
called the card "near its calibrated range". **That was optimistic** --- end-of-hold is the
cycle *minimum*. Weighted by the solver's own $\Delta$PEEQ increments:

| profile | median driving overstress | damage above 16 MPa |
|:--|--:|--:|
| operating baseline 25/83 °C | **69.4 MPa** | **99.1 %** |
| 45/125 °C (selected) | 91.4 MPa | 98.9 % |
| 110/150 °C (selected) | 54.3 MPa | 93.7 % |

**3.4--7.2x above the top of the fitted window, in every profile including the one all current
results rest on.** It is a property of how hard this package loads its joints and **cannot be
fixed by choosing a profile.** It does **not** disturb the relative-life result: the same
extrapolation applies identically to all three architectures, so it is common-mode and cancels
in a ratio.

## $\beta$ = 6 is not conservative

**16 primary cells** from Syed 2004 Table 2b and George 2010 Tables 4 and 6:

| | $\beta$ |
|:--|:--|
| range | **5.1 -- 20.4** |
| **SAC305 only** | **5.1, 5.4, 5.6, 10.1** |
| cells below 6 | **4 of 16 (25 %)** |

> **$\beta$ = 6 is the 25th percentile, not a conservative bound.** The observed minimum
> **5.1** is used instead.

![FIG-0KR-D](FIGDIR/FIG_0KR_D_beta.png)

## n = 16 tested, not defended

| question | effect size | min n at $\beta$ = 5.1 | at n = 16 |
|:--|:--|--:|:--|
| **Q1 --- which life law?** | D = 1.4395 | **10** | Z = 3.41 **ADEQUATE** |
| **Q2 --- is Z2/Z1 real?** | 1.110 / 1.2485 | **34** | Z = 2.49 **MARGINAL** |

> **n = 16 is SUFFICIENT for Q1 and INSUFFICIENT for Q2.**
> One campaign answering both needs **n = 34 per cell --- 4 cells, 136 packages.**

![FIG-0KR-E](FIGDIR/FIG_0KR_E_power.png)
![FIG-0KR-F](FIGDIR/FIG_0KR_F_matrix.png)

## Three wordings corrected

**"6.19 sigma"** is $\ln(D)/\sqrt{2/(\beta^2 n)+\sigma_{sim}^2}$. It omits uncertainty in
$\beta$ itself, censoring loss and the constitutive-domain error in the predicted D. **Renamed
EXPECTED DISCRIMINATION Z-SCORE**; "σ" is no longer used for it.

**"the robust G2 band is 17 % wide"** --- denominator attached: the window is
$(1.000, 1.1665]$ in $N_{required}/N_{f,Z1}$, i.e. **16.65 % of the measured Z1 life**, or
**0.0669 decades**.

**"27.6 % of the range"** --- it is **logarithmic**: the ambiguous interval spans
**0.83 decades**, about 27.6 % of the three-decade 100--100 000-cycle log sweep. As a linear
fraction it would be 2.7 %, and that figure is not used.

**Terminology frozen:** CONDITION (one profile) · CELL (one architecture × one profile) ·
CAMPAIGN (the whole experiment). *A single CONDITION cannot identify the fatigue-law family; a
multi-condition CAMPAIGN can.*

## Unchanged

$N_{required}$ is still **OPEN**. **Mission and experiment still proceed in parallel** ---
verified against the updated decision map, not assumed. **The optimizer remains forbidden**: no
condition of the gate is met. Full detail:
`results/phase0kr/PHASE0KR_EXPERIMENTAL_CLOSURE.md`.

![FIG-0KR-G](FIGDIR/FIG_0KR_G_workflow.png)

<!-- END GENERATED: phase0kr_narrative -->
"""


def main() -> int:
    subprocess.run([sys.executable, str(R / "scripts/phase0k/build_report_0k.py")],
                   check=True, capture_output=True)
    s = REP.read_text()
    s = sub(s, "# Phase 0K --- Mission Definition, Absolute-Life Identifiability and G2 "
            "Decision Closure (current authoritative)",
            "# Phase 0K --- Mission Definition, Absolute-Life Identifiability and G2 "
            "Decision Closure (extended by Phase 0K-R)", "demote Phase 0K")
    s = place(s, "phase0kr_narrative", NARRATIVE.replace("FIGDIR", G),
              "\n<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml")
    REP.write_text(s)
    print(f"\nreport now {len(s.splitlines())} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
