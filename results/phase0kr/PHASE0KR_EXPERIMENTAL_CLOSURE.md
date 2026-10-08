# Phase 0K-R — Experimental-Domain, Statistical-Power and Report-Consistency Closure

**Verdict: LOW-TEMPERATURE DATA INSUFFICIENT — ORIGINAL PROFILE WITHDRAWN**

Two secondary corrections, stated separately because one verdict does not carry them:
**(i)** a within-domain replacement pair was found and is adequate; **(ii)** the specimen count
must rise from **16 to 34 per cell**. And one limitation that no design removes: the **stress**
domain is violated by every profile, so the experiment is **ready to execute with a declared
limitation, not frozen**.

---

## 1. DEFECT #39 — confirmed and fixed

The Phase-0K *narrative* was current; the *generated* current-status fragments were not. The
Executive Summary's **"Exact next work"** still read **"PHASE 0K — SYSTEM-OWNER MISSION
DEFINITION"** and still asserted *"the remaining blocker is … a REQUIRED LIFE"* — the exact
claim Phase 0K withdrew. **No Phase-0K result appeared in current-facing text at all**: not the
474/3206 decision regions, not the two-blocker finding, not the experiment design.

Repaired at the single source of truth. Six new guards, each self-tested on the **verbatim**
standing sentence and each negative-tested to failure. Detail: `DEFECT39_REPORT_AUDIT.md`,
post-build verification in `POSTBUILD_SEMANTIC_AUDIT.md`.

## 2. The constitutive domain, read from the card rather than restated

| | calibration |
|---|---|
| **creep** (Yuan 2023 Table 26, 19 points) | **45, 80, 115, 150 °C** · **7.51–15.92 MPa** |
| **plastic** (Yuan 2023 Table 31, Chaboche) | **−40 … 122 °C** |
| elastic dE/dT, CTE | **ASSUMPTIONS** |

**The card rows at −40, 0 and 25 °C are already extrapolated on creep.** Every result this
project has produced uses a cycle whose cold half sits at 25 °C, 20 K below the floor. The
−40 °C proposal was not a new kind of problem — it was 85 K of an existing one.

## 3. The −40 °C profile is withdrawn

| | COLD_SHALLOW −40 → +25 °C |
|---|---|
| temperature | 85 K below the creep floor |
| **damage accumulated below 45 °C** | **100 %** |
| damage-weighted median driving overstress | **114.9 MPa** — the worst of any candidate |
| classification | **INVALID FOR MODEL-DISCRIMINATION DESIGN** |

### Can the model be extended? No.

Seven targeted searches. The low-temperature SAC305 literature **exists and is the wrong
regime**: 4 of 5 retrieved constitutive works are **high-strain-rate / impact**, 0 are creep.
A dedicated filter for sub-zero, creep, non-impact work returned two thermal-cycling papers that
use −40 °C as a *cycle minimum*, not as a creep-test temperature.

This is physics, not a search artefact: at −40 °C the homologous temperature of SAC305 is
**T/T_m = 0.475**, below the threshold at which creep governs, so steady-state creep tests there
are impractically long and are not performed. **Syed 2001 explicitly excludes fast loading from
the creep framework**, so a high-strain-rate set is not merely unhelpful — it belongs to the
regime the framework rules out.

Sec. 8 is explicit, and is followed: **the model is NOT extended.** No
`LOW_TEMPERATURE_MODEL_VALIDATION.md` exists, because producing one would mean inventing the
data it validated.

> **The Phase-0K claims D = 1.849, 85 % separation and 6.19 σ are WITHDRAWN as current**, and
> retained only as historical experiment-design screening.

![FIG-0KR-A](FIGDIR/FIG_0KR_A_domain.png)

## 4. A within-domain replacement was found

Eight profiles with `T_min ≥ 45 °C` solved on the graded Syed-matched mesh. The exploitable
physics: the creep law sees the **overstress** `σ_eq − σ_y(T)`, and σ_y falls with temperature,
so a cold-in-domain cycle sustains far more stress per unit creep than a hot one. **Within the
domain, temperature band moves `w/ε` by 44 %; dwell by only 2–3 %.**

> ### SELECTED: 45 → 125 °C  +  110 → 150 °C, 5-min dwells, 3 °C/min
> **D = 1.4395**, 44.0 % separation, **Z = 3.44** at β = 5.1 and n = 16.

Selection was **composite, not max-D**, and the rule bites: `110→150 °C with 15-min dwells`
scores D = 1.4721 but costs **46 extra days per cell** for a 2 % gain, and was rejected.

| | ORIGINAL | **REVISED** |
|---|---|---|
| damage below the creep floor | **100 %** | **0 %** |
| D | 1.849 | **1.4395** |
| domain | **INVALID** | temperature **PASS**, stress **FAIL** |

**The redesign costs 41 % of the discriminating power and buys validity.**

![FIG-0KR-B](FIGDIR/FIG_0KR_B_pair_comparison.png)
![FIG-0KR-C](FIGDIR/FIG_0KR_C_discrimination.png)

## 5. The limitation no profile removes

Phase 0J-R checked the **end-of-hold** overstress (≈ 15 MPa, inside the window) and concluded
the card was "being evaluated near its calibrated range". **That was optimistic.** End-of-hold
is the *minimum* of the cycle. Weighted by the solver's own ΔPEEQ increments:

| profile | median driving overstress | damage above 16 MPa |
|---|---|---|
| operating baseline 25/83 °C | **69.4 MPa** | **99.1 %** |
| COLD_SHALLOW −40/+25 °C | 114.9 MPa | 100.0 % |
| **45/125 °C (selected)** | **91.4 MPa** | **98.9 %** |
| **110/150 °C (selected)** | **54.3 MPa** | **93.7 %** |

**The damage-weighted median is 3.4–7.2× above the top of the fitted window, in every profile
including the one all current results rest on.** This is a property of how hard this package
loads its joints and **cannot be fixed by choosing a profile**. It is corrected here as a
Phase-0J-R overstatement, carried as a standing limitation on every *predicted* number
including `D` itself — and it is one of the strongest arguments **for** running the experiment,
since a measurement is the only thing that retires it.

**It does not disturb the relative-life result** (Sec. 27): the same extrapolation applies
identically to all three architectures, so it is common-mode and cancels in a ratio. **Z2/Z1 =
1.21–1.38 stands unchanged.**

## 6. "6.19 sigma" is not a sigma

Audited (`G2_WINDOW_WORDING_AUDIT.md`). It is `ln(D)/√[2/(β²n) + σ_sim²]`. It **omits**
uncertainty in β itself, censoring loss, and the constitutive-domain error in the predicted `D`.
It correctly excludes the life-law constants (they cancel in a ratio) and the model-form spread
(that is what is being tested).

> **Renamed: EXPECTED DISCRIMINATION Z-SCORE under a stated error budget.** "σ" is no longer
> used for it. Recomputed for the revised pair at β = 5.1, n = 16: **Z = 3.44**.

## 7. β = 6 is not conservative

**16 primary cells** transcribed from tables in papers held here — Syed 2004 Table 2b (12
SnAgCu board-level cells) and George 2010 Tables 4 and 6 (4 SAC305 BGA cells).

| | β |
|---|---|
| range | **5.1 – 20.4** |
| median | 8.92 |
| **SAC305 only** | **5.1, 5.4, 5.6, 10.1** |
| cells below 6 | **4 of 16 (25 %)** |

> **β = 6 is the 25th percentile of the observed distribution, not a conservative bound.**
> The observed minimum is **5.1** (SAC305 BGA, 16/16 failures), and that is what is used.

![FIG-0KR-D](FIGDIR/FIG_0KR_D_beta.png)

## 8. n = 16 tested, not defended — and it fails one of the two questions

| question | effect size | min n at β = 5.1 | at n = 16 |
|---|---|---|---|
| **Q1 — which life law?** | D = 1.4395 | **10** | Z = 3.41 · **ADEQUATE** |
| **Q2 — is Z2/Z1 real?** | 1.110 / 1.2485 | **34** | Z = 2.49 · **MARGINAL** |

> **n = 16 is SUFFICIENT for Q1 and INSUFFICIENT for Q2.**
> Sec. 15 requires the larger when one campaign answers both:
> **n = 34 per cell, 4 cells, 136 packages.**

![FIG-0KR-E](FIGDIR/FIG_0KR_E_power.png)
![FIG-0KR-F](FIGDIR/FIG_0KR_F_matrix.png)
![FIG-0KR-G](FIGDIR/FIG_0KR_G_workflow.png)

## 9. Two more wordings corrected

**"the robust G2 band is 17 % wide"** — denominator now attached. After calibration at one
condition, a robust Z1-fail/Z2-pass decision requires
`N_f,Z1 < N_required ≤ R_min · N_f,Z1` with `R_min = 1.1665`: a relative window of
**(1.000, 1.1665]**, **16.65 % of the measured Z1 life**, **0.0669 decades**, and 333 cycles
wide if Z1 measured 2000.

**"27.6 % of the range"** — it is **logarithmic** and must say so:
> "The ambiguous interval spans approximately **0.83 decades** — about **27.6 % of the
> three-decade 100–100 000-cycle logarithmic sweep**."
As a linear fraction it would be 2.7 %, an order of magnitude smaller and misleading. The linear
figure is not used.

**"one experiment"** — terminology frozen: **CONDITION** (one profile), **CELL** (one
architecture × one profile), **CAMPAIGN** (the whole thing). *A single CONDITION cannot identify
the fatigue-law family; a multi-condition CAMPAIGN can.*

## 10. Unchanged

`N_required` is still **OPEN** — no field or product requirement exists anywhere. The
questionnaire is preserved. **Mission and experiment still proceed in parallel**: the mission
defines demand, the experiment calibrates capability, and neither depends on the other to begin.
Verified against the updated decision map rather than assumed.

**The optimizer remains forbidden.** No condition of Sec. 32 is met.

## 11. Verdict, and the five rejected

**LOW-TEMPERATURE DATA INSUFFICIENT — ORIGINAL PROFILE WITHDRAWN**

| rejected | why |
|---|---|
| **A** frozen, current material model sufficient | the model is not sufficient: the −40 °C profile is 85 K outside the creep calibration and the stress domain is violated everywhere |
| **B** frozen after within-domain redesign | the redesign succeeded, but "FROZEN" requires all eight Sec. 31 criteria and criterion 2 fails irreducibly. Claiming frozen would paper over the stress-domain finding |
| **C** low-temperature model validated, original retained | no sub-zero SAC305 creep data exists; nothing was validated because nothing was extended |
| **E** statistical power insufficient, sample count must increase | **true, and stated as a secondary correction** (16 → 34), but it is a fix applied within this phase, not the dominant finding |
| **F** design not yet identifiable | false — it **is** identifiable: D = 1.4395 at Z = 3.44, with a stated n |

**D is chosen because the single most consequential fact is that the decisive Phase-0K
experiment cannot be made valid with data that exist.** Everything else in this phase is a
repair.

## 12. Residuals

Stress domain violated by 3.4–7.2× in every profile, irreducibly. No sub-zero SAC305 creep data.
Arrhenius creep interpolation fitted, never independently validated. `du ∝ ΔT` scaling for the
candidate profiles is a first-order CTE model. dE/dT and CTE remain assumptions. Absolute life
still model-form uncertain at 4.1×. `N_required` still open. Six of eight failure mechanisms
uncomputed. Z1 vs Z4 unresolved electrically and in life.
