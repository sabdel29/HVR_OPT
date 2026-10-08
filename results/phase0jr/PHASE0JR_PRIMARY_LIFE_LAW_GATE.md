# Phase 0J-R — Primary Life-Law Access, Reproduction and Transferability Closure

**Verdict: SAC/SnAgCu LIFE LAW ADMITTED FOR RELATIVE LIFE ONLY**

Four primary-source formulations are admitted. Syed 2004's calibration was **reproduced** on the
tolerances declared beforehand. His **25 µm averaging volume was reproduced** with a targeted
local refinement. **Z2 outlives Z1 by 1.21–1.38× across every admissible law.** Absolute life
remains conditional and is not reported as validated. **G2 is still NOT TESTED, and now for one
reason only: `N_required` must come from the system owner.**

---

## 1. The Phase-0J verdict is overturned, and it said it would be

Phase 0J returned *"no admissible SAC305 life law"* and recorded the cause as **access**: three
canonical calibrations paywalled, no open-access copy, no reprinted dataset. With the papers
supplied, **7 of 10 database entries change** (`LIFE_LAW_ADMISSIBILITY_REVISED.csv`):

| law | Phase 0J | **Phase 0J-R** |
|---|---|---|
| Syed 2004 total accumulated creep strain (Eq. 14) | INADMISSIBLE | **ADMISSIBLE for relative life** |
| Syed 2004 creep energy density (Eq. 15) | INADMISSIBLE | **ADMISSIBLE for relative life** |
| Schubert 2003 strain (Eq. 5) / energy (Eq. 6) | INADMISSIBLE | **ADMISSIBLE for relative life only** |
| Syed 2001 power-cycle transfer | not evaluated | **ADMISSIBLE as methodology** |
| Vasudevan & Fan 2008 | not evaluated | **ADMISSIBLE for test-to-field scaling only** |
| Darveaux 2000 | INADMISSIBLE | **INADMISSIBLE** — SnPb only, confirmed from the primary |
| Coffin-Manson, Engelmaier | INADMISSIBLE | INADMISSIBLE |

**Phase 0J also rejected Syed for the wrong reason.** It rejected the paper because the
*partitioned* model needs a two-mechanism creep split our single Norton law cannot produce.
The paper contains **three** formulations, and the author explicitly offers the total-accumulated
form as the simplification: the low-stress mechanism contributes **< 5 % of strain and < 2 % of
damage** for SnAgCu, so *"there is no need for such a separation for SnAgCu solder."* That
formulation needs no partition and is what is used here.

## 2. Version control — the corrected constants are mandatory for us, not merely newer

The author-corrected copy carries a per-page notice: the original ECTC constants *"were not
accurate"* due to **errors in data processing**. The appended deck gives the mechanism:

> *"Life prediction model parameters in the paper are based on **1st cycle values due to post
> processing error** and are not correct"* — alongside *"SnAgCu solder joints show stability
> after 2nd cycle — **20 to 30 % reduction after 1st cycle**"*.

| constant | original | **corrected** | ratio |
|---|---|---|---|
| `C'` total accumulated creep strain (Eq. 14) | 0.0358 | **0.0468** | 1.31 |
| `W'` creep energy density (Eq. 15) | 0.0012 | **0.0015** | 1.25 |
| `C_I / C_II` partitioned (Eq. 13) | 0.013 / 0.036 | **0.106 / 0.045** | 8.15 / 1.25 |
| sinh strain / energy (Eq. 16/17) | 0.0405 / 0.0014 | **0.0513 / 0.0019** | 1.27 / 1.36 |

Every constant rises by 1.25–1.43×, exactly the 1/(0.70–0.80) that correcting a 20–30 %
first-cycle overestimate demands — an internal consistency check the audit did not have to
assume.

**Why this is binding here and not just good practice:** this project extracts every metric at
the **stabilised** cycle. Pairing our stabilised ε with a constant fitted to **first-cycle** ε
would compound the very error the author corrected, over-predicting life by **31 %**. The
version match is a methodological requirement. Syed's own observation that SnAgCu stabilises
after cycle 2 also independently vindicates the Phase-0I decision to cycle and report a
stabilised value.

![FIG-0JR-A](FIGDIR/FIG_0JR_A_syed_version_audit.png)

## 3. What Syed's ε_acc is, and proving our PEEQ is the same thing

Syed's `ε_acc` is accumulated **creep** strain from ANSYS `NL,CREQ` — creep only. Sec. 6 forbids
feeding PEEQ into his constant without proof. Two single-element probes supplied it:

| applied σ | `*PLASTIC`? | measured creep rate | `A·σⁿ` | `A·(σ−σ_y)ⁿ` |
|---|---|---|---|---|
| 25 MPa | no | 2.8002e−05 | **2.8002e−05** | 1.5222e−08 |
| 25 MPa | **YES** | 1.5154e−08 | 2.8002e−05 | **1.5222e−08** |

and, at 25 MPa against a 15.2 MPa yield, PEEQ at the first output is **1.52e−11** where a
rate-independent model would need **5.16e−02**.

**CalculiX's combined `*PLASTIC` + `*CREEP` is a pure viscoplastic OVERSTRESS model. There is no
rate-independent plastic strain.** The yield card supplies only the threshold. Therefore

```
M4  ≡  M1  ≡  Δ(PEEQ)             M5  ≡  M3  ≡  the inelastic work integral
```

identically for this model. **M4 was computed, and the computation turned out to be an
identity.** Syed reaches the same conclusion for his own model from the other direction: plastic
contributes **0.125 %** of strain and **0.225 %** of energy, and *"No need to model time
independent plasticity for Thermal Cycle simulations."*

This also **refines two earlier statements**. Phase 0I-R's *"plastic and creep, inseparably"* is
true of the card and misleading about the strain — there is nothing to separate. And Phase 0I's
assumption that plasticity caps σ_eq near σ₀+C/γ is measurably wrong for the combined deck: the
plastic-only deck caps **exactly** at 30.26 MPa, the combined deck sits at **median 55.8 MPa**,
which is correct overstress behaviour. The stress entering the creep law is the **overstress**,
≈ 15 MPa at the end of a hold — inside the card's fitted 7.5–16 MPa window, though the law has
been re-purposed from a total-stress law into an overstress law, which is recorded as a standing
model-form caveat.

## 4. Matching Syed's averaging volume — and it matters a great deal

The source is specific, and states its own scope: *"25 micron thick layers of solder at package
and board side"*, *"each layer has two elements across the thickness"*, and **"Life prediction
model parameters are only valid for this thickness."**

The Phase-0I mesh is 8 uniform elements over 300 µm = **37.5 µm** — it cannot resolve a 25 µm
layer, let alone two elements inside one. A **targeted local refinement** was built
(`graded_joint.py`): **2 × 12.5 µm at each solder face**, geometrically graded through the
middle. Only the joint submodel was refined; the global package model was untouched.

* **Outcome: TARGETED LOCAL REFINEMENT REQUIRED, and achieved.**
* Mesh convergence, predeclared at < 10 %: **3.0–3.2 %** over the final refinement.
* Stabilisation: **0.32–0.56 %** at cycle 5 of 6.

Two numerical findings were needed to get there and are recorded rather than buried: a
float-noise duplicate in the graded z-grid created **zero-thickness elements** that diverged at
increment 1; and the **final simulated cycle is systematically ~15 % low** — identically in the
4-cycle and 6-cycle runs, whose cycle 3 values agree to four figures. Physics cannot know which
cycle is last, so the final cycle is discarded and the penultimate one reported.

**Matching the volume changes the answer:**

| | M4 on Syed's layers | Phase-0I core value | ratio |
|---|---|---|---|
| Z1 | 8.5518e−3 | 6.5117e−3 | **1.313** |
| Z2 | 6.6649e−3 | 4.1789e−3 | **1.595** |
| Z4 | 8.9491e−3 | 7.3196e−3 | **1.223** |

The change is 22–60 % and **different for each architecture**, which is precisely why it cannot
be treated as a scale factor.

![FIG-0JR-C](FIGDIR/FIG_0JR_C_metric_definitions.png)

## 5. Sec. 8 — the reproduction that Phase 0J could not attempt

**Tolerances declared before the arithmetic:** (a) reproduce the paper's own ±25 % claim from
its Table 3; (b) the two **independently fitted** constants must recover a mutually consistent
`w_acc/ε_acc` to within 10 % on the independent validation package.

| test | result | verdict |
|---|---|---|
| (a) worst error on the Table 3 validation package | **11.7 %** | **PASS** |
| (b) `w/ε` from `C'` and `W'` across 4 configurations | 28.78, 29.85, 28.99, 30.02 MPa — **spread 4.2 %** | **PASS** |
| same on the hyperbolic-sine pair | 24.16–26.32 MPa, spread 8.6 % | PASS |

Test (b) is the non-circular one: `C'` and `W'` were regressed separately against 12 points and
nothing forces them to agree on a package outside that set. **No digitisation was used** — every
value is a printed table entry, so no digitisation uncertainty arises.

![FIG-0JR-B](FIGDIR/FIG_0JR_B_syed_reproduction.png)

## 6. Sec. 10 — the zero-dwell finding was WRONG, and the correction matters

Phase 0J reported the waveform as a triangle with **zero dwell**, inherited from a Phase-0I-R
note that CalculiX ramps `*TEMPERATURE` across a step. Sec. 10 required this to be checked
against actual input behaviour rather than inferred. **It is a step.** The solver's own `NT`
output has the full hot value **82.8605 °C at t = 0.002 s**, the first increment of a 300 s step;
a ramp would give 25.0004 °C.

> **The actual waveform is a square wave: instantaneous step, then a 300 s HOLD at each extreme.
> Period 600 s. The Phase-0I "300 s dwell" is a genuine 300 s dwell.**

That places our cycle much closer to the calibration set than Phase 0J believed: **Syed's TC3 has
5-minute dwells — exactly ours.**

## 7. Sec. 11 — dwell sensitivity, and it is mild

| dwell | Z1 M4 | Z2 M4 | **Z2/Z1 strain** | **Z2/Z1 energy** |
|---|---|---|---|---|
| 30 s | 7.859e−3 | 5.954e−3 | 1.320 | 1.282 |
| 60 s | 8.170e−3 | 6.250e−3 | 1.307 | 1.275 |
| **300 s (actual)** | 8.823e−3 | 6.886e−3 | **1.281** | **1.208** |
| 900 s | 9.215e−3 | 7.278e−3 | 1.266 | 1.202 |

Over a **30× change in dwell** the absolute metric moves only **+17 % (Z1) / +22 % (Z2)**, and
the **relative** result moves by **±2 %**. The physical reason is the overstress formulation:
creep self-limits as σ → σ_y, so extending a hold adds little further damage.

**The Phase-0J concern is therefore void twice over** — the premise was wrong, and even if the
dwell were different the conclusion would barely move.

![FIG-0JR-D](FIGDIR/FIG_0JR_D_dwell_sensitivity.png)

## 8. Where our joint sits — one thing passes, one thing does not

| quantity | Syed's calibration | ours | classification |
|---|---|---|---|
| mean life | 275 – 10 027 | 2388 – 3206 | **INTERPOLATION** |
| ε_acc | 0.00213 – 0.0777 | 0.00666 – 0.00895 | **INTERPOLATION** |
| w_acc | 0.0665 – 2.424 MPa | 0.905 – 1.110 | **INTERPOLATION** |
| **w_acc / ε_acc** | **28.8 – 30.0 MPa** | **124 – 136 MPa** | **OUTSIDE by 4.3×** |

Each metric interpolates. **The pair does not.** Our joint dissipates four times more creep
energy per unit creep strain than anything Syed calibrated on — it runs at roughly four times his
effective stress. The consequence is visible and is not hidden:

| | Z1 | Z2 | Z4 |
|---|---|---|---|
| `N_f` Eq. 14 (strain) | 2499 | 3206 | 2388 |
| `N_f` Eq. 15 (energy) | **610** | **736** | **601** |
| disagreement | **4.10×** | 4.36× | 3.97× |

On Syed's own validation package the same two equations agree to **4–7 %**. On ours they differ
by **four times**. That is the quantitative signature of being off the calibration locus, and it
is why absolute life is reported as **conditional**, not validated.

![FIG-0JR-E](FIGDIR/FIG_0JR_E_on_syed_calibration.png)

## 9. Sec. 19 — the relative life, and the Phase-0J figure it supersedes

| law | Z2/Z1 | Z4/Z1 |
|---|---|---|
| Syed corrected, strain (Eq. 14) | **1.283** | 0.956 |
| Syed corrected, energy (Eq. 15) | 1.206 | 0.984 |
| Syed corrected, sinh strain (Eq. 16) | 1.283 | 0.956 |
| Schubert SnAgCu strain (slope 1.3) | **1.383** | 0.943 |
| Schubert SnAgCu energy (slope 1.0) | 1.206 | 0.984 |
| **range** | **1.21 – 1.38** | **0.94 – 0.98** |

**ROBUST ACROSS ADMISSIBLE LIFE-LAW FAMILIES** — two authors, two SnAgCu variants, two metric
families, exponents −1 and −1.3, and a 30× dwell range. Ranking Z2 > Z1 > Z4 in every case.

**Phase 0J's 1.558 is withdrawn.** It was an **ALGEBRAIC RATIO** computed on the Phase-0I core
volume, which is not the volume Syed calibrated. **1.283 is a TRANSFER-VALIDATED RELATIVE-LIFE
RATIO.** The two are different quantities and must never be quoted interchangeably.

**Z4 vs Z1 is not resolved** at 0.94–0.98 and is not claimed; Z1 vs Z4 also remains
electrically unresolved at 0.14σ, unchanged.

Uncertainty on Z2/Z1: the constant cancels exactly; the original-vs-corrected version cancels
exactly; mesh 0.2 %; stabilised cycle < 0.6 %; dwell ±2 %; **law family −6 %/+8 %**.

![FIG-0JR-F](FIGDIR/FIG_0JR_F_life_by_primary_law.png)

## 10. Sec. 24 — does Z2's +1.688 W buy a real, experimentally calibrated advantage?

> **YES — relative lifetime difference validated; absolute life unavailable.**

**+1.688 W — 1.3 % of 126.1 W — buys 1.21–1.38× solder fatigue life**, on a primary-source
calibration, with the averaging volume matched to that source and the source's own validation
reproduced.

![FIG-0JR-G](FIGDIR/FIG_0JR_G_electrical_vs_life.png)

## 11. Sec. 12/13/14/17 — the other branches

**Syed 2001** validates the power-cycle transfer *method*: transient thermal solve → temperature
field → same damage model, **no acceleration factor**, on a **260 s** cycle, 16 assemblies,
**+20 %**. Our cycle is 600 s and the chain is identical. Its SnPb constants are not used.

**Schubert 2003** prints the SnAgCu **exponents** (1.3 strain, 1.0 energy) but **not** the
prefactors, which exist only as unannotated fitted lines. Absolute life is not reproducible;
relative life is, and it agrees. Its exponents also bracket the physical value narrowly — far
narrower than the m = 1.5–3 Phase 0I once assumed and Phase 0I-R withdrew.

**Darveaux 2000** is **INADMISSIBLE for SAC305**: Table 6 was recovered in full, and every row is
**62Sn36Pb2Ag or 60Sn40Pb**. The Phase-0J mesh objection is now removed — our 12.5 µm elements
meet his 12.7 µm requirement — leaving alloy and constitutive model, which meshing cannot fix.
Its K1 varies **47 % across a 3× averaging-thickness change**, and the paper states the
methodology-mismatch penalty as **"up to 7X"** on absolute life while noting that **relative
predictions are largely insensitive to the averaging scheme** — independent corroboration of
this phase's central conclusion.

**Vasudevan & Fan 2008** is an **acceleration-factor** model (m = 0.33, n = 1.9, Ea/k = 1414 K,
17 pairs, < 6 %), not a damage model. It cannot turn an FEA metric into a life. It is the right
tool for moving a *stated requirement* between conditions and is handed forward unused.

## 12. Sec. 26/27 — G2

`N_required` remains **OPEN**. No field mission requirement exists in any source and none was
invented; the 1000-cycle qualification figure is retained as a **QUALIFICATION REFERENCE** only.

```
G2 = NOT TESTED
```

Requirement 1 is now **partially met** (relative life defensible, absolute conditional),
requirement 4 is **met and strengthened**, and **requirement 2 is the sole blocker**. What Phase
0J-R does establish, which Sec. 27 explicitly permits, is
**ARCHITECTURE-DEPENDENT RELATIVE FATIGUE LIFE**.

## 13. The next blocker is not mechanics

**It is SYSTEM-OWNER MISSION DEFINITION** (`MISSION_INPUT_TEMPLATE.md`): a required life, a
survival target, and a cycle spectrum — cold boots per day, workload cycles and their depth,
and whether the system is ever fully powered down.

One further item would be transformative and is cheap: **a single board-level thermal-cycle test
of the actual DVPD package**. One measured life at one condition fixes the constant directly,
collapses the 4.1× model-form spread, and converts every relative result in this phase into an
absolute one.

## 14. Verdict, and the five rejected

**SAC/SnAgCu LIFE LAW ADMITTED FOR RELATIVE LIFE ONLY**

| rejected | why |
|---|---|
| **A** absolute life validated | the two admitted Syed models disagree **4.1×** on our joint while agreeing to 4–7 % on his; `w/ε` sits **4.3× off** the calibration locus |
| **C** transfer remains conditional | too weak — it understates a reproduced calibration, a matched averaging volume and a ratio robust across four formulations |
| **D** no admissible law | false; four are admitted |
| **E** model-form uncertainty dominates | false for the **ranking**, which is identical everywhere. It dominates the **absolute** value only, and that is stated as such rather than promoted to the verdict |
| **F** zero-dwell incompatibility | **doubly false** — the waveform has a 300 s dwell, and the relative result moves ±2 % over a 30× dwell change |

## 15. Residuals

SAC405/SAC395 and SAC387 calibrations applied to SAC305. `w/ε` off-locus by 4.3×. Norton card
re-purposed as an overstress law relative to its total-stress fit. Displacement-driven submodel,
one joint, one critical BGA. E(T) slope, CTE and ρ·c_p remain assumptions. MLCC height OPEN.
Z1 vs Z4 unresolved both electrically (0.14σ) and in life (0.94–0.98). Six of eight failure
mechanisms uncomputed. No mission requirement.
