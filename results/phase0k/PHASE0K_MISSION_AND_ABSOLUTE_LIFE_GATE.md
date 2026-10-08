# Phase 0K — Mission Definition, Absolute-Life Identifiability, and G2 Decision Closure

**Verdict: MISSION REQUIREMENT STILL OPEN — ABSOLUTE-LIFE CALIBRATION ALSO REQUIRED**

Both, and the second is not a consequence of the first. **G2 remains NOT TESTED.** The global
optimizer is not justified and was not built.

---

## 1. The correction that had to come first — DEFECT #38

Nine current-facing statements were still describing a project that could not predict life,
three phases after it could: *"No lifetime is predicted anywhere"*, *"no m is sourced"*,
*"Z2/Z1 spans 1.25 to 9.18"*, *"solder fatigue … has no life law"*. All were in the Executive
Summary, all generated from the source of truth, all now repaired there and regenerated.

Six guards added, each self-tested against the **verbatim** sentence that was standing, and each
negative-tested to failure. One of them immediately caught a seventh problem — the Phase-0J-R
narrative's own *"requirement 2 … is the sole blocker"* — which is the subject of the next
section. Detail: `DEFECT38_REPORT_PROPAGATION_AUDIT.md`.

## 2. "N_required is the sole blocker" is false, and the proof is arithmetic

Phase 0J-R recorded the required life as the only thing standing between the project and a G2
decision. Tested formally, it is not. Take `N_required = 1500`:

| | strain family (Eq. 14/16) | energy family (Eq. 15/17) |
|---|---|---|
| Z1 | 2279–2499 → **PASS** | 482–610 → **FAIL** |
| Z2 | 2925–3206 → **PASS** | 581–736 → **FAIL** |

Both architectures pass under one admitted family and fail under the other. **Knowing the
mission produces no decision here.** The correct framing, adopted throughout:

> **TWO OPEN PIECES FOR ABSOLUTE G2**
> 1. the system mission / required life;
> 2. an absolute-life calibration, **or** a decision region demonstrably robust to model form.

## 3. The robust decision map, built before any experiment was designed

All four admitted absolute formulations applied independently; none chosen
(`g2_decision_map.csv`, 601-point log grid).

| | Z1 | Z2 | Z4 |
|---|---|---|---|
| Syed Eq. 14 strain, power law | 2499 | 3206 | 2388 |
| Syed Eq. 16 strain, sinh | 2279 | 2925 | 2178 |
| Syed Eq. 15 energy, power law | 610 | 736 | 601 |
| Syed Eq. 17 energy, sinh | 482 | 581 | 474 |
| **envelope** | **482–2499** | **581–3206** | **474–2388** |

```
ROBUST ALL PASS        N_required <=   474
MODEL-FORM AMBIGUOUS     474 < N_required <= 3206      a factor of 6.8
ROBUST ALL FAIL        N_required >   3206
```

### The question Sec. 3 poses, answered

> Is there **any** `N_required` at which all admitted models agree Z1 fails and Z2 passes?

```
Z1 fails under EVERY law only when   N_required >  2499
Z2 passes under EVERY law only when  N_required <=  581
```

**DISJOINT. 581 < 2499. Zero of 601 grid points.**

> ### NO. An experimental absolute-life calibration is NECESSARY before mechanics can alter the feasible architecture set.

The reason is structural, not numerical: the **model-form spread within one architecture is
5.2×**, the **architecture separation is 1.21–1.38×**. A 5.2× uncertainty cannot resolve a 1.3×
effect at any requirement. The relative result survives *because* the spread cancels in a
ratio — and that same cancellation is why choosing a requirement cannot recover it.

![FIG-0K-A](FIGDIR/FIG_0K_A_g2_decision_map.png)

## 4. Mission: searched, and genuinely absent

The **entire repository** and all supplied source material were searched for service life,
required cycles, cold boots, qualification targets, field lifetime, availability, maintenance
intervals and duty cycles (Sec. 5). **Nothing.** Every `n_required` in this repository is the
**TSV via count** — an unrelated quantity. The June-2026 and ECTC reference papers discuss
reliability only qualitatively.

`N_required` = **USER INPUT REQUIRED**, now enforced mechanically:
`configs/phase0k/mission_profile.yaml` holds only `USER_REQUIRED` / `UNKNOWN` /
`NOT_APPLICABLE`, and `mission_requirement.py` **refuses to emit a number** without a populated
`mission_source`, refuses to treat a `QUALIFICATION` type as a field mission, and refuses to
collapse a multi-bin spectrum.

**Sec. 7 — is one cycle count enough?** Not necessarily, and the framework does support the
alternative: Syed derives his model from Monkman-Grant plus the **time-fraction rule** and builds
it by summing damage over the steps *within* a cycle, so Miner-type summation **across** cycle
types is consistent with the framework's own construction rather than an outside assumption. The
caveat is recorded: Syed warns that for small field ΔT the low-stress creep mechanism — under
5 % of strain in his accelerated tests — can become prominent, so a shallow-cycle-dominated
spectrum is outside the calibrated range and bins are retained separately.

Illustrative only, never a requirement (`mission_requirement_examples.csv`):

| scenario | `N_required` | region |
|---|---|---|
| 5 y, 1 cold boot/day | 1 826 | **AMBIGUOUS** |
| 7 y, 2 boots/week + 1 workload cycle/day | 3 287 | ROBUST ALL FAIL |
| 5 y, 1 boot/day + 4 workload cycles/day | 9 131 | ROBUST ALL FAIL |
| 10 y, monthly boot + 24 workload cycles/day | 87 780 | ROBUST ALL FAIL |
| 3 y, never powered down | 0 | mechanism not life-limiting |

**Every non-trivial illustrative mission lands in the ambiguous band or worse.** That is the
argument for running the experiment in parallel rather than waiting.

## 5. Auditing "one board-level test fixes everything"

Phase 0J-R claimed one test would *"fix the constant"* and *"make every relative result
absolute."* Half right, and the half that is wrong is the half that matters.

**One condition cannot identify the law.** One measured life is one equation; each law has one
free constant; both fit **exactly**:

| hypothetical measured Z1 life | `C_fit` | `W_fit` |
|---|---|---|
| 800 | 0.14168 | 0.00112 |
| 1500 | 0.07556 | 0.00060 |
| 3000 | 0.03778 | 0.00030 |

Residual degrees of freedom for discrimination: **zero**. It re-labels the disagreement; it does
not resolve it.

**But one condition does more than expected for *this* comparison.** Both laws are forced
through the measured point and then extrapolate to the other architectures through their own
metric ratio:

| | strain law | energy law | spread |
|---|---|---|---|
| Z1 | measured | measured | **0 %** |
| Z2 | 1.2400 × | 1.1665 × | **6.3 %** |
| Z4 | 0.9556 × | 0.9843 × | **3.0 %** |

Across 3721 (measured-life × required-life) cells, the **ambiguous region vanishes**: 50.8 %
all-pass, 47.6 % all-fail, 1.6 % a genuine G2 pass, **0 % ambiguous**. The reason is that the
three architectures sit within 6 % of each other in `w/ε` (123.2 / 126.9 / 134.9 MPa), so both
laws extrapolate *between them* almost identically even while disagreeing 4.1× on the level.

**What one condition still does not license is extrapolation to a different cycle**, where the
two laws diverge by up to 85 %.

![FIG-0K-E](FIGDIR/FIG_0K_E_calibration_vs_mission.png)

## 6. What actually discriminates the two laws

The algebra determines the experiment:

```
strain:  N_A/N_B = ε_B/ε_A      energy:  N_A/N_B = w_B/w_A
D = (ε_B/ε_A)/(w_B/w_A) = (w/ε)_A / (w/ε)_B
```

**Discrimination comes from spanning `w/ε`, not from maximising damage.** Eight candidate
board-level profiles were simulated on the graded Syed-matched mesh:

| condition | T range | ΔT | dwell | **w/ε (MPa)** |
|---|---|---|---|---|
| **COLD_SHALLOW** | −40 / +25 °C | 65 | 5 min | **209.2** |
| SHORT_DWELL | 25 / 82.9 | 57.9 | 30 s | 142.5 |
| WIDE_HOT | 25 / 125 | 100 | 5 min | 142.8 |
| OP_BASELINE | 25 / 82.9 | 57.9 | 5 min | 126.9 |
| LONG_DWELL | 25 / 82.9 | 57.9 | 15 min | 124.5 |
| SMALL_DT | 25 / 55 | 30 | 5 min | 118.0 |
| **HOT_SHALLOW** | +55 / +125 °C | 70 | 5 min | **113.1** |

The physics is exploitable: the creep law sees the **overstress** `σ − σ_y(T)`, and σ_y is high
at low temperature. **Temperature range moves `w/ε` by 85 %; ΔT alone by 21 %; dwell by only
14 %.**

| candidate experiment | D | laws differ by | σ at β = 6, n = 16 |
|---|---|---|---|
| **COLD_SHALLOW vs HOT_SHALLOW, one architecture** | **1.849** | **84.9 %** | **6.19** |
| OP_BASELINE vs COLD_SHALLOW | 1.649 | 64.8 % | 5.03 |
| one architecture, two dwells (30 s vs 900 s) | 1.144 | 14.4 % | 1.4 |
| **two ARCHITECTURES at one profile** | **1.063** | **6.3 %** | **< 1** |

**Two architectures at one profile is nearly blind to model form** — it validates the relative
claim, which is worth doing, but it cannot identify the law.

![FIG-0K-C](FIGDIR/FIG_0K_C_discrimination.png)
![FIG-0K-B](FIGDIR/FIG_0K_B_strain_vs_energy.png)

## 7. The minimum experimentally identifiable design

> **TWO CONDITIONS spanning `w/ε`, on at least ONE architecture.**
> Adding the second architecture at both conditions buys the direct relative-life validation.
> **2 architectures × 2 conditions × 16 specimens = 64 packages.**

| cell | architecture | condition | n |
|---|---|---|---|
| 1 | Z1 embedded | −40 → +25 °C, 5-min dwells, 3 °C/min | 16 |
| 2 | Z1 embedded | +55 → +125 °C, 5-min dwells, 3 °C/min | 16 |
| 3 | Z2 backside | −40 → +25 °C | 16 |
| 4 | Z2 backside | +55 → +125 °C | 16 |

**Z4 is excluded** on value-of-information: D = 1.03, and its predicted life sits *inside* the
6.3 % post-calibration model spread, so the test could not distinguish it from Z1.

**n = 16 is not arbitrary**: it gives > 6σ at the pessimistic β = 6; it matches the cell size of
Syed's own dataset so the Weibull statistics are comparable; and the **ceiling set by the 8 %
simulation uncertainty is 7.7σ**, so specimens beyond ~16 buy almost nothing — the limit becomes
the model, not the sample. Bare 3σ minimum is n = 4.

**Failure definition is matched to the calibration**: in-situ > 300 Ω confirmed by ten further
events within 10 % of the time of the first — Syed's exact rule — with **mean life** reported
via `η·Γ(1+1/β)`, and **β estimated, not assumed**. Right-censoring by maximum likelihood.
Details: `BOARD_LEVEL_CALIBRATION_PLAN.md`, `sample_size_and_statistics.md`,
`failure_definition_alignment.md`.

![FIG-0K-D](FIGDIR/FIG_0K_D_relative_ratio_by_profile.png)
![FIG-0K-F](FIGDIR/FIG_0K_F_workflow.png)

## 8. The electrical-cost statement, preserved and not overstated

> **+1.688 W — 1.3 % of 126.1 W — buys +21–38 % relative solder-fatigue life.**

That remains the current ETM trade-off. It is **not** converted into "+1.688 W buys X cycles",
because absolute life is not validated. After calibration and a declared mission it could
legitimately be expressed as an electrical penalty per reliability-margin multiple.

**An honest limit worth stating now:** even after perfect calibration, the robust G2-pass band is
`N_required ∈ (measured Z1 life, 1.1665 × measured Z1 life]` — a window only **17 % wide**. A
1.2–1.4× advantage changes feasibility only if the requirement lands there. Z2 buys margin
reliably; it flips a pass/fail only in a narrow window.


## 9. G2

| Sec. 24 requirement | status |
|---|---|
| `N_f(x) ≥ N_required` evaluable | **NO** — neither side is closed |
| the condition changes the feasible architecture set | **NOT DEMONSTRABLE** — no robust reversal band exists |

```
G2 = NOT TESTED
```

Relative life alone does not pass G2, and this phase does not claim it does. What is established
is **ARCHITECTURE-DEPENDENT RELATIVE FATIGUE LIFE**, unchanged from Phase 0J-R and now bounded by
a decision map that says exactly what it would take to go further.

## 10. Sec. 26 — experimental priority

> **MISSION + EXPERIMENT IN PARALLEL.**

Justified from the decision map, not from preference:

* every non-trivial illustrative mission lands in the **ambiguous** band or in **robust all-fail**,
  so the mission alone will very probably not decide G2;
* the calibration alone cannot decide it either — it needs a requirement to test against;
* they are **independent** and neither blocks the other: the questionnaire costs the owner an
  hour, the test takes months;
* running them sequentially would add the test duration to the critical path for no information
  gain.

## 11. Sec. 31 — the optimizer gate

| condition | met? |
|---|---|
| 1. `N_required` real and defensible | **NO** |
| 2. absolute life calibrated, **or** all admitted models agree on feasibility | **NO** — 5.2× spread, 27.6 % of the range ambiguous |
| 3. one electrically attractive candidate fails while another passes | **NO** — no robust reversal band exists |
| 4. that result survives uncertainty | not reached |

**THE GLOBAL OPTIMIZER IS NOT SCIENTIFICALLY JUSTIFIED AND WAS NOT BUILT.**

## 12. Verdict, and the five rejected

**MISSION REQUIREMENT STILL OPEN — ABSOLUTE-LIFE CALIBRATION ALSO REQUIRED**

| rejected | why |
|---|---|
| **A / B / C** all begin "mission requirement acquired" | no mission requirement exists anywhere in the repository or the supplied material |
| **D** absolute-life calibration required before G2 can be decided | **true but incomplete** — it is silent on the mission, which is equally open and equally blocking. Choosing D would repeat the Phase-0J-R error of naming one blocker when there are two |
| **F** mission open, relative life is the maximum defensible claim | **understates the phase.** It is true that relative life is currently the maximum *validated* claim, but F implies nothing further is obtainable. This phase shows precisely what is obtainable, how, and at what cost: 64 packages, two conditions, 6.2σ |

**E is chosen because both pieces are open and this phase proved both are necessary** — the
mission by exhaustive search, the calibration by the disjointness of the robust regions.

## 13. Stop condition

No new physics model was started. No delamination, no RDL fracture, no TSV fatigue, no optimizer.
**Both** a physical test protocol and a system-owner questionnaire are required, and both are
delivered: `BOARD_LEVEL_CALIBRATION_PLAN.md` and `SYSTEM_OWNER_MISSION_REQUEST.md`.

## 14. Residuals

Absolute life model-form uncertain at 4.1×. `w/ε` 4.3× off the Syed calibration locus.
SAC405/395 and SAC387 calibrations applied to SAC305. Norton card used as an overstress law
relative to its total-stress fit. Displacement-driven submodel, one joint, one critical BGA.
The `du ∝ ΔT` scaling used for the candidate test conditions is a first-order CTE model.
Z1 vs Z4 unresolved electrically (0.14σ) and in life (0.94–0.98). Six of eight failure mechanisms
uncomputed. E(T) slope, CTE and ρ·c_p remain assumptions. MLCC height OPEN.
