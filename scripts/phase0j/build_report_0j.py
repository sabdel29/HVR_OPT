#!/usr/bin/env python3
"""Phase-0J Sec.39 -- splice Phase 0J into the full technical report.

Phase 0I-R is demoted from "current authoritative" to "extended by Phase 0J". Nothing it
concluded is withdrawn; Phase 0J adds the acquisition result its verdict called for.

Sec.39 requires the report to distinguish, and never interchange:
  mechanical response metric | fatigue damage parameter | predicted fatigue life |
  required life | constraint / pass-fail.
"""
from __future__ import annotations
import re, subprocess, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
REP = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
G = "/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0j"


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


NARRATIVE = r"""<!-- BEGIN GENERATED: phase0j_narrative -->

\newpage

# Phase 0J --- SAC305 Life Law, Mission, and G2 Evaluation (current authoritative)

**Verdict: NO ADMISSIBLE SAC305 LIFE LAW FOUND FOR THE CURRENT METRIC / REGIME.**
**G2 remains NOT TESTED. $N_{required}$ = OPEN.**
**The global optimizer is not recommended and was not built.**

## Five words this section never interchanges

| term | what it means here | status in this project |
|:--|:--|:--|
| **mechanical response metric** | a converged model output: M1, M2, M3 | **three exist, all validated** |
| **fatigue damage parameter** | a response metric a *source* uses as the input to a life law | **none** --- no source uses ours that way for this alloy, joint and cycle |
| **predicted fatigue life** | $N_f$ from a calibrated law | **none validated** |
| **required life** | $N_{required}$, declared or sourced | **OPEN** |
| **constraint / pass--fail** | $N_f \ge N_{required}$ | **not evaluable** |

Phase 0I-R closed the metric. Phase 0J went looking for the two things that would turn it into
a constraint, with network access Phase 0H did not have. **Both are absent, and for different
reasons.**

## What the search actually reached

762 unique works, 15 targeted queries, two independent indices. Eleven full-text sources
retrieved and read. **The three canonical calibrations are paywalled with no legal open-access
copy**, verified three ways each:

| paper | DOI | doi.org | Unpaywall | Semantic Scholar |
|:--|:--|:--|:--|:--|
| **Syed 2004** SnAgCu | 10.1109/ectc.2004.1319419 | IEEE 202 | `is_oa=false` | `openAccessPdf=null` |
| **Schubert 2003** SnAgCu | 10.1109/ectc.2003.1216343 | IEEE 202 | `is_oa=false` | `openAccessPdf=null` |
| **Darveaux 2002** | 10.1115/1.1413764 | ASME 403 | `is_oa=false` | `openAccessPdf=null` |

**139 open-access papers citing them were enumerated. Not one reprints a calibration dataset.**
Exactly one review reprints numerical SnAgCu constants. No paywall was circumvented.

![FIG-0J-A](FIGDIR/FIG_0J_A_admissibility_funnel.png)

## The three metrics, frozen before any law was chosen

| | definition | units | character |
|:--|:--|:--|:--|
| **M1** | $\Delta$(PEEQ) per stabilised cycle | --- | accumulated inelastic **path**; plastic and creep, inseparable |
| **M2** | $\max_t -\min_t$ of eq($\varepsilon_{in}$) in the cycle | --- | a true **range**, computed **directly** |
| **M3** | $\sum \sigma:d\varepsilon_{in}$ over the cycle | **MJ/m$^3$** | dissipated inelastic **energy** |

### The number that justifies the "compute M2 directly" rule

Phase 0I-R measured $M1/M2 = 3.72$ and warned it was not universal. Computing both natively at
**all eleven** z-sweep points settles it:

| trajectory | $\Delta T$ | displacement path | **M1/M2** |
|:--|--:|:--|--:|
| **all 11 DVPD architecture cases** | 56.1--58.2 K | unidirectional $0 \to du \to 0$ | **2.023--2.027** |
| Phase-0I-R representative case | 100 K | fully reversed $-du \to +du \to -du$ | **3.72** |

**The ratio belongs to the loading path, not the material.** Across three architectures and a
6.7x span in substrate thickness it varies by **0.2 %**. Had 3.72 been used to convert, any
strain-range law would have been wrong by $1.84^m$ --- **2.6x at $m=1.5$, 6.2x at $m=3$.**

![FIG-0J-C](FIGDIR/FIG_0J_C_native_metrics.png)

## The admissibility gate: 0 of 10

Ten candidates, ten predeclared criteria. **0 ADMISSIBLE, 1 conditionally transferable, 9
inadmissible.** The operative reasons:

* **Engelmaier is *undefined* for our cycle**, not merely inaccurate:
  $c = c_0 + c_1 T_{sj} + c_2\ln(1 + 360/t_{dwell})$ and **our cycle has zero dwell**.
* **Darveaux** needs $\Delta W_{ave}$ from **three element layers each 12.7 µm** at the pad
  interface; our finest element is **37.5 µm**, 3x too coarse to reproduce the extraction, and
  the circulated constants are **eutectic SnPb**. The retrieved source states the penalty
  itself: absolute predictions *"could be off by a factor of 7."*
* **Syed 2004** is the closest family --- its native metric *is* accumulated creep strain per
  cycle --- but the two-mechanism form needs $\varepsilon_{acc}$ **partitioned by a double power
  law**, and our Norton card is a single power law.
* **Schubert 2003** is cited by eight retrieved sources and reprinted by **none**.
* Two *fully specified* laws were found and rejected on regime and alloy: a SnAgCu **vibration**
  law, and a **92.5Pb5Sn2.5Ag die-attach** recalibration with primary constants from 20 devices.

**Sec. 8 reproduction: not passed** --- and one step earlier than the brief anticipates. The
formulas did not fail to reproduce their data; **the data cannot be reached.**

![FIG-0J-B](FIGDIR/FIG_0J_B_calibration_not_reproducible.png)

## One simulated cycle is not one experimental fatigue cycle

Read out of the deck, not assumed. `*TEMPERATURE` carries no `AMPLITUDE=STEP`, so CalculiX ramps
linearly and the 300 s named `DWELL` is a 300 s **ramp**. The waveform is a **symmetric triangle
with zero hold**.

| | Phase-0I | JESD22-A104-B as applied |
|:--|:--|:--|
| $\Delta T$ | **56.1--58.2 K** | 165 K |
| **dwell** | **ZERO** | **15 min** |
| period | 10 min | about 120 min |

Both Sec. 15 remedies are unavailable for a reason that precedes them: **no admissible law means
no calibration cycle to reconcile with.** Re-running at $-40/+125$ °C was considered and
**deliberately not done** --- both extremes lie outside the validated 7.5--16 MPa Norton window,
so it would have produced numbers that look like progress and mean nothing.

**The cycle is right for the product and wrong for the literature.** The DVPD mission *is* power
cycling and Phase 0I modelled it as such. That is a data gap, not a modelling error.

## Does the law family change what creep means? Yes, in every architecture

| architecture | M1 strain path, creep ON vs OFF | M3 inelastic work, creep ON vs OFF |
|:--|--:|--:|
| Z1 embedded | $-$23.5 % | $+$147.8 % |
| Z2 backside | $-$32.0 % | $+$115.2 % |
| Z4 power die | $-$21.5 % | $+$153.3 % |

**A strain-based law and an energy-based law disagree about the sign of what creep does.** Any
future law must be matched to the measure it was calibrated against.

![FIG-0J-H](FIGDIR/FIG_0J_H_temperature_and_creep.png)

## What survives: the ranking, and a ratio with no free parameter

Across all three law families and every exponent tested, the ranking is **Z2 > Z1 > Z4**, without
exception. That is a **ROBUST LIFE RANKING**.

And the Syed form is **inverse-linear**, $N_f = (C\,\varepsilon_{acc})^{-1}$, so in a life ratio
the constant cancels **and there is no exponent to assume**:

$$\frac{N_{f,Z2}}{N_{f,Z1}} = \frac{M1_{Z1}}{M1_{Z2}} = 1.558 \qquad
  \frac{N_{f,Z4}}{N_{f,Z1}} = 0.890$$

This is the opposite of the Coffin-Manson case, where Phase 0I-R found the ratio spans a factor
of 7.4 over a plausible exponent range. **Conditional on the form** --- which the gate does not
establish --- the relative life rests only on a metric ratio resolved at 5.8x its
paired-perturbation spread.

![FIG-0J-E](FIGDIR/FIG_0J_E_model_form.png)

![FIG-0J-D](FIGDIR/FIG_0J_D_life_by_architecture.png)

**Absolute and relative uncertainty are not the same thing here, and the asymmetry is the most
useful result of the phase:**

| source | RELATIVE life | ABSOLUTE life |
|:--|:--|:--|
| life-law constant $C$ | **0 --- cancels** | factor **2.77** |
| life-law exponent | **0 --- fixed at 1 by the form** | --- |
| metric numerics, paired | 6.2 pp | 6.6 % |
| **no admissible law** | --- | **UNBOUNDED** |
| **cycle incompatibility** | --- | **UNBOUNDED** |

## The required life

$N_{required}$ = **OPEN**. What was found is categorised and **not promoted**: qualification
counts (1000 cycles, $-40/+125$ °C), accelerated conditions (15-min dwell, 3.6 °C/min), and one
measured characteristic life ($\eta = 1390$, $\beta = 5.4$ at $-40/+185$ °C). **No field mission
requirement exists in any accessible source**, and Sec. 14 forbids promoting the others.

This is structural: **operating-life limits are set by customer-specific qualification
programmes and are not published.** A required life for this system must be declared by its
owner.

Conditional on the Syed form, the **MISSION-LIFE CROSSOVER** band is $N_{required} \in (4266,
6647]$, in which only Z2 is feasible. **Its position is conditional on an unvalidated constant;
its width --- a factor 1.558 --- is not**, because $C$ cancels.

![FIG-0J-G](FIGDIR/FIG_0J_G_mission_sweep.png)

## The electrical cost of reliability, replacing W per µm of warpage

> **$+$1.688 W buys 1.56x fatigue life** --- 8.76 W per decade of $N_f$, for Z1 $\to$ Z2.

That supersedes *W per µm of warpage* for local-reliability decisions. **Z1 and Z4 are not
ranked electrically**: that difference is 0.14$\sigma$ and remains unresolved.

![FIG-0J-F](FIGDIR/FIG_0J_F_electrical_cost.png)

## G2, and the optimizer

| Sec. 23 requirement | status |
|:--|:--|
| 1. defensible predicted fatigue life | **NOT MET** |
| 2. defensible required life | **NOT MET** |
| 3. one attractive candidate fails while another passes | **NOT EVALUABLE** |
| 4. ranking survives uncertainty | **MET** at the metric level |

$$\textbf{G2 = NOT TESTED}$$

All four optimizer-gate conditions were required; two fail outright. **The global optimizer is
not recommended and was not built.**

Phase 0I-R ended with *"a validated metric and no allowable."* Phase 0J ends with *"three
natively-computed metrics whose ranking is model-form independent, no transferable law, and no
requirement"* --- and, unlike before, a precise specification of what each missing piece must
look like. Full detail: `results/phase0j/PHASE0J_LIFE_LAW_AND_MISSION_GATE.md`.

<!-- END GENERATED: phase0j_narrative -->
"""


def main() -> int:
    subprocess.run([sys.executable, str(R / "scripts/phase0ir/build_report_0ir.py")],
                   check=True, capture_output=True)
    s = REP.read_text()
    s = sub(s, "# Phase 0I-R --- Reliability-Metric, Claim-Scope and Report-Consistency "
            "Closure (current authoritative)",
            "# Phase 0I-R --- Reliability-Metric, Claim-Scope and Report-Consistency "
            "Closure (extended by Phase 0J)", "demote Phase 0I-R")
    s = place(s, "phase0j_narrative", NARRATIVE.replace("FIGDIR", G),
              "\n<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml")
    REP.write_text(s)
    print(f"\nreport now {len(s.splitlines())} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
