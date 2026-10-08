# Phase 0J — SAC305 Life-Law, Mission, and G2 Acquisition Gate

**Verdict: NO ADMISSIBLE SAC305 LIFE LAW FOUND FOR THE CURRENT METRIC / REGIME**

**G2 remains NOT TESTED.** `N_required` = **OPEN**. **The global optimizer is not recommended
and was not built.** What Phase 0J adds is not a lifetime: it is three natively-computed
metrics, a quantified demonstration that the architecture ranking is model-form independent,
and a precise statement of exactly which two things are missing and why.

---

## 1. What was actually looked for, and with what reach

Phase 0I recorded that publisher access was uneven and that both candidate life-law sources
returned HTTP 403. **That was re-tested, not inherited.** Crossref, OpenAlex, Semantic Scholar,
arXiv, PMC, Springer, CORE, CiteSeerX, NTRS and OSTI are all reachable in this environment now.

**762 unique works** were harvested from 15 targeted queries across two independent indices
(OpenAlex `title_and_abstract.search`, Crossref `query.bibliographic`), covering all four law
families Sec. 4 requires. Eleven full-text sources were retrieved and read.

**The three canonical primary calibrations are paywalled with no legal open-access copy**, and
this was verified three ways rather than assumed:

| paper | DOI | doi.org | Unpaywall | Semantic Scholar |
|---|---|---|---|---|
| **Syed 2004** SnAgCu accumulated creep strain / energy | 10.1109/ectc.2004.1319419 | IEEE HTTP 202 | `is_oa=false` | `openAccessPdf=null` |
| **Schubert 2003** SnAgCu/SnPb fatigue life models | 10.1109/ectc.2003.1216343 | IEEE HTTP 202 | `is_oa=false` | `openAccessPdf=null` |
| **Darveaux 2002** crack-growth correlation | 10.1115/1.1413764 | ASME HTTP 403 | `is_oa=false` | `openAccessPdf=null` |

**139 distinct open-access papers citing them** were enumerated and the most promising fetched.
**Not one reprints a calibration dataset.** Exactly one — an open-access review retrieved in
full (Yu et al. 2026, *Eng. Res. Express* **8**:132401) — reprints numerical SnAgCu constants:
`C_I = 0.013`, `C_II = 0.036`. No paywall was circumvented.

![FIG-0J-A](FIGDIR/FIG_0J_A_admissibility_funnel.png)

## 2. Sec. 1 — the three metrics, frozen before any law was chosen

Full definitions in `RELIABILITY_METRIC_DEFINITIONS.md`. All three come from the same solve,
the same volume-averaged solder core, the same one-element corner exclusion, and the same
stabilised cycle (cycle 4 of 4, converged to 0.48–2.00 %).

| | definition | units | character |
|---|---|---|---|
| **M1** | `Δ(PEEQ)` per stabilised cycle | dimensionless | accumulated inelastic **path length** — plastic and creep, inseparable |
| **M2** | `max−min` of instantaneous `eq(ε_in)` within the cycle | dimensionless | a true **range**, computed **directly** from the time history |
| **M3** | `Σ σ:dε_in` over the cycle, engineering shear factor 2 | **MJ/m³** | dissipated inelastic **energy**, per cycle |

### The Sec. 2 rule, and the number that proves it was needed

Sec. 2 forbids obtaining M2 as `M1/3.72`. Computing both natively at **all eleven** z-sweep
points shows why:

| trajectory | ΔT | displacement path | **M1/M2** |
|---|---|---|---|
| **all 11 DVPD architecture cases** | 56.1–58.2 K | unidirectional 0→du→0 | **2.023 – 2.027** |
| Phase-0I-R representative case | 100 K | fully reversed −du→+du→−du | **3.72** |

**The ratio is a property of the loading path.** Across three architectures and a 6.7× span in
substrate thickness it varies by **0.2 %**; change the cycle shape and it moves by 84 %. Had
3.72 been used, any strain-range law would have been wrong by `1.84^m` — a factor of **2.6 at
m = 1.5**, **6.2 at m = 3**.

![FIG-0J-C](FIGDIR/FIG_0J_C_native_metrics.png)

## 3. Sec. 6 — the admissibility gate: 0 of 10

Ten candidates, ten predeclared criteria, applied identically
(`LIFE_LAW_ADMISSIBILITY.md`, `SAC305_LIFE_LAW_DATABASE.csv`).

| classification | count |
|---|---|
| **ADMISSIBLE** | **0** |
| CONDITIONALLY TRANSFERABLE | 1 — Syed 2004 SnAgCu |
| INADMISSIBLE | 9 |

The operative reasons, not the counts:

* **Engelmaier** is *undefined* for our cycle, not merely inaccurate: its fatigue exponent is
  `c = c0 + c1·T_sj + c2·ln(1 + 360/t_dwell)`, and **our cycle has zero dwell**, so the
  logarithm diverges.
* **Darveaux** requires `ΔW_ave` from **three element layers each 0.0005 in (12.7 µm)** at the
  pad interface. Our finest element is **37.5 µm — 3× too coarse to reproduce the extraction** —
  and the widely circulated `K1`–`K4` are **eutectic SnPb**. The retrieved IMAPS source states
  the penalty for methodological inconsistency verbatim: **"absolute predictions could be off by
  a factor of 7."**
* **Syed 2004** is the closest family — its native metric *is* accumulated creep strain per
  cycle — but the two-mechanism form needs `ε_acc` **partitioned by a double power law**, and
  our Norton card is a single power law that cannot produce that partition.
* **Coffin-Manson** needs a plastic-only strain range; CalculiX aliases `CEEQ`/`CE`/`PE` to
  `PEEQ` and cannot separate plastic from creep.
* **Schubert 2003** is cited by eight retrieved sources and **reprinted by none**.
* Two fully-specified laws were found and rejected on regime and alloy: a SnAgCu **vibration**
  law (`N_f = 7758.3·W^−1.036`) and a **92.5Pb5Sn2.5Ag die-attach** Darveaux recalibration with
  primary constants from 20 devices. Sec. 4 forbids grouping laws by the word "energy", and the
  project's no-alloy-mixing rule — which already rejected SAC405 and SnAgCuCe in Phase 0I —
  forbids the second.

## 4. Sec. 8 — reproduction: the gate is not passed

**Declared tolerance before attempting: ±25 % on N_f.** The gate fails one step earlier than
Sec. 8 anticipates: the formulas did not fail to reproduce their data — **the data cannot be
reached**. `LIFE_LAW_REPRODUCTION.md`, `life_law_reproduction.csv`.

Consequently **no absolute lifetime in this phase is validated**, and every row of
`lifetime_by_law_and_architecture.csv` carries
`applicability_status = CONDITIONAL … NOT A VALIDATED LIFETIME`.

![FIG-0J-B](FIGDIR/FIG_0J_B_calibration_not_reproducible.png)

## 5. Sec. 15/16 — one simulated cycle is NOT one experimental fatigue cycle

Recovered from the deck rather than assumed (`cycle_compatibility_audit.md`). The Phase-0I
waveform is a **symmetric triangle with zero dwell**: `*TEMPERATURE` carries no
`AMPLITUDE=STEP`, so CalculiX ramps linearly and the 300 s named `DWELL` is a 300 s *ramp*.

| | Phase-0I | JESD22-A104-B as applied | |
|---|---|---|---|
| ΔT | **56.1–58.2 K** | 165 K | **2.9× apart** |
| T range | 25 → 83 °C | −40 → +125 °C | |
| **dwell** | **ZERO** | **15 min** | **qualitatively different** |
| period | 10 min | ≈ 120 min | |

Sec. 15's two remedies are both unavailable, and the reason precedes both: **there is no
admissible law, hence no calibration cycle to reconcile with.** Re-running at −40/+125 °C was
considered and **deliberately not done** — it would match a law whose coefficients we do not
have, and both extremes lie outside the validated 7.5–16 MPa window of the Norton surrogate.

**Sec. 16 is already satisfied.** The DVPD mission *is* power cycling, and Phase 0I modelled it
that way: `P(t) → T_local(t) → nonlinear solder solve`, with the half-period justified from the
package's own thermal time constant. **The cycle is right for the product and wrong for the
literature** — a data gap, not a modelling error.

## 6. Sec. 12 — does the law family change the interpretation of creep? YES

Re-run at each architecture's own optimum (`creep_effect_by_architecture.csv`), not only on the
Phase-0I-R representative trajectory:

| architecture | M1 strain path, creep ON vs OFF | M3 inelastic work, creep ON vs OFF |
|---|---|---|
| Z1 embedded | **−23.5 %** | **+147.8 %** |
| Z2 backside | **−32.0 %** | **+115.2 %** |
| Z4 power die | **−21.5 %** | **+153.3 %** |

**A strain-based law and an energy-based law disagree about the SIGN of what creep does**, in
every architecture. This is reported, not buried, and it is binding on any future acquisition:
a Coffin-Manson-type law must be matched to M2, a Darveaux-type law to M3, and a Syed-type law
to M1 — never interchanged.

![FIG-0J-H](FIGDIR/FIG_0J_H_temperature_and_creep.png)

## 7. Sec. 19/20 — the central question, and what survives

> **Does the 35.8 % metric reduction translate into a material lifetime advantage?**

**Conditionally yes, and the ranking is model-form independent.** Across all three law families
and every exponent tested, the ranking is **Z2 > Z1 > Z4** without exception
(`lifetime_model_form_comparison.csv`). That is a **ROBUST LIFE RANKING** in Sec. 20's sense.

The *magnitude* is not robust, with one important exception. For a Coffin-Manson-type law the
ratio spans a factor of 7.4 over a plausible exponent range (Phase 0I-R). But the **Syed form is
inverse-linear**, `N_f = (C·ε_acc)^−1`, so in a life ratio the constant cancels **and there is no
exponent to assume**:

```
N_f,Z2 / N_f,Z1  =  M1_Z1 / M1_Z2  =  1.558      exactly, no fitted parameter
N_f,Z4 / N_f,Z1  =  M1_Z1 / M1_Z4  =  0.890
```

**Conditional on the Syed form being the right form** — which the admissibility gate does *not*
establish — Z2 lives 1.56× as long as Z1 and Z4 0.89× as long, and those numbers depend only on
a metric ratio resolved at 5.8× its paired-perturbation spread.

![FIG-0J-E](FIGDIR/FIG_0J_E_model_form.png)
![FIG-0J-D](FIGDIR/FIG_0J_D_life_by_architecture.png)

## 8. Sec. 21/22 — uncertainty, with absolute and relative kept apart

Phase 0I-R established that architecture ratios share common-mode error. That principle is
retained: ratios are perturbed **in pairs**, absolute values are not (`lifetime_uncertainty.csv`).

| source | affects RELATIVE life | affects ABSOLUTE life |
|---|---|---|
| life-law constant `C` | **0 — cancels exactly** | factor **2.77** (C_I vs C_II) |
| life-law exponent | **0 — the Syed form fixes m = 1** | — |
| choice of `ε_acc` (EPC total vs EC creep-only) | small | **−38 %** |
| metric numerics (mesh, CETOL, corner band) | 6.2 pp, paired | 6.6 % |
| material parameters | 6.2 pp, paired | 8.9 % (E ±15 % alone) |
| **model form — no admissible law** | — | **UNBOUNDED** |
| **cycle incompatibility** | — | **UNBOUNDED** |

**The absolute life has two unbounded error sources and is not quotable. The relative life has
none of them.** That asymmetry is the single most useful result of this phase.

## 9. Sec. 13/14 — the required life

`N_required` = **OPEN**. No category-B field mission requirement exists
(`MISSION_REQUIREMENT_AUDIT.md`). The June-2026 reference paper discusses reliability
qualitatively and specifies no cycle count. jedec.org, the ANSI webstore and opencompute.org all
return HTTP 403.

What *was* found is correctly categorised and **not promoted**:

| category | finding |
|---|---|
| **A** qualification requirement | −40/+125 °C, **1000 cycles** board-level; −55/+125 °C, 1000 cycles package-level |
| **C** accelerated test condition | JESD22-A104-B: 45-min ramp, **15-min dwell**, 3.6 °C/min |
| **A** measured characteristic life | SAC305 256 I/O BGA, ENIG, −40/+185 °C: **η = 1390, β = 5.4** |
| **B** field mission requirement | **NONE** |

This is structural, not a search failure: **operating-life limits are set by customer-specific
qualification programmes and are not published.** A required life for this system must be
*declared by its owner*.

## 10. Sec. 25 — the mission-life crossover

Since no requirement exists, the sweep is **PARAMETRIC MISSION SENSITIVITY**, never
qualification (`mission_life_sensitivity.csv`). Conditional on the Syed form:

```
MISSION-LIFE CROSSOVER:  N_required in (4266, 6647]   ->  only Z2 feasible
  below 4266  : all three pass, pick Z1 on electrical loss
  above 6647  : all three fail, further architecture work required
```

**The band's POSITION is conditional on the unvalidated constant C. Its WIDTH — a factor of
1.558 — is not**, because C cancels. So the statement *"there exists a band of required lives,
1.56 decades-of-margin wide in ratio, in which reliability alone selects Z2"* survives even
though its location does not.

![FIG-0J-G](FIGDIR/FIG_0J_G_mission_sweep.png)

## 11. Sec. 26 — the electrical cost of reliability, replacing W per µm of warpage

| Z1 → Z2 | value |
|---|---|
| electrical penalty | **+1.688 W** (1.3 % of 126.09 W) |
| metric improvement | **−35.8 %** in M1, −35.7 % in M2, −37.7 % in M3 |
| life multiple (Syed form, m fixed at 1) | **1.56×** |
| exchange rate | **8.76 W per decade of N_f** |

> **+1.688 W buys 1.56× fatigue life.**

That sentence is the deliverable Sec. 26 asks for, and it supersedes *W per µm of warpage*,
which is hereby withdrawn for local-reliability decisions. **Z1 vs Z4 is not ranked
electrically**: Phase 0I-R established that difference is 0.14σ and unresolved, and Sec. 18
forbids reviving it.

![FIG-0J-F](FIGDIR/FIG_0J_F_electrical_cost.png)

## 12. Sec. 27 — temperature propagated to life

Phase 0I measured **+22.7 %** in the metric per +50 K mean-temperature shift with
temperature-dependent material physics, against **−0.2 %** with frozen properties. Propagated
through the Syed form (m fixed at 1): **−18.5 % life per +50 K**; at m = 3 it would be −45.9 %
(`temperature_shift_to_life.csv`).

**This must not be confused with the architecture comparison**, whose joint temperatures differ
by only 2.1 K with r = +0.017 against damage. The temperature sensitivity is a property of the
*material model*; the architecture difference is *mechanical*.

## 13. Sec. 28 — the word "damage"

Until an admissible law exists, **M1, M2 and M3 are RESPONSE METRICS**. None of them is called a
fatigue damage parameter in this phase, because no source uses them as one for this alloy,
joint and cycle. PEEQ is not "damage"; it is accumulated equivalent inelastic strain.

## 14. Sec. 23/24 — G2

| requirement | status |
|---|---|
| 1. defensible predicted fatigue life `N_f(x)` | **NOT MET** — 0 admissible laws; reproduction impossible |
| 2. defensible required life `N_required` | **NOT MET** — no category-B requirement exists |
| 3. an electrically attractive candidate fails while another passes | **NOT EVALUABLE** |
| 4. ranking survives uncertainty | **MET** at the metric level — 5.8×, and identical across all families |

```
G2 = NOT TESTED
```

Sec. 24 is explicit that G2 is not passed merely because lifetimes differ. They differ; nothing
establishes that the difference crosses a threshold, because there is no threshold.

**What changed.** Phase 0I-R ended with *"we have a validated metric and no allowable."*
Phase 0J ends with *"we have three natively-computed metrics whose ranking is model-form
independent, no transferable law, and no requirement"* — and, unlike before, **precise
statements of what each missing piece would have to look like.**

## 15. Sec. 37 — the optimizer gate

| condition | met? |
|---|---|
| 1. at least one life law admissible **and validated** | **NO** |
| 2. a defensible required life | **NO** |
| 3. one electrically attractive candidate fails while another passes | **NOT EVALUABLE** |
| 4. ranking survives uncertainty strongly | **YES** |

All four were required. **THE GLOBAL OPTIMIZER IS NOT RECOMMENDED AND WAS NOT BUILT.**

## 16. Sec. 35 — the twenty questions, answered

1. **What SAC305 life laws were found?** Ten candidates across four families — Coffin-Manson,
   Engelmaier, Syed 2004 (strain and energy), Darveaux, Schubert 2003 (strain and energy), a
   SnAgCu vibration law, and a high-lead die-attach recalibration.
2. **Which are admissible?** **None.** One (Syed 2004) is conditionally transferable.
3. **What metric does each require?** Tabulated in `SAC305_LIFE_LAW_DATABASE.csv`: plastic
   strain range; closed-form shear strain range; accumulated **creep** strain per cycle;
   viscoplastic SED over a 12.7 µm interface layer; cyclic plastic work.
4. **Is M1, M2 or M3 appropriate?** It depends entirely on the law, which is the point of
   Sec. 2. M1 suits the Syed family, M2 the Coffin-Manson family, M3 the Darveaux family — and
   Sec. 12 shows they disagree about creep, so the match must be exact.
5. **Can the selected law reproduce its own data?** **Cannot be tested** — the calibration data
   are unretrievable. The gate is therefore not passed.
6. **Are Z1/Z2/Z4 inside the calibration domain?** **Unknowable.** The domain is not stated in
   any accessible source, so interpolation vs extrapolation **cannot be classified** — recorded
   explicitly rather than guessed (Sec. 30).
7. **Predicted life of Z1?** No validated value. Conditional: 4266 cycles.
8. **Z2?** No validated value. Conditional: 6647 cycles.
9. **Z4?** No validated value. Conditional: 3795 cycles.
10. **Does Z2 retain a reliability advantage?** **Yes** — −35.8 % in M1, −35.7 % in M2, −37.7 %
    in M3, resolved at 5.8× its paired-perturbation spread.
11. **Does the answer depend on strain vs energy formulation?** **The ranking does not**
    (Z2 > Z1 > Z4 in every family and exponent). **The creep interpretation does**, strongly:
    −21.5…−32.0 % in strain against +115…+153 % in energy.
12. **Absolute life uncertainty?** **Unbounded** — two unbounded contributors (no admissible
    law, cycle incompatibility) on top of a factor 2.77 from the constant and −38 % from the
    `ε_acc` choice.
13. **Relative Z2/Z1 uncertainty?** **6.2 pp on a 35.8 % effect** — and zero contribution from
    the law constant or exponent, both of which cancel in the Syed form.
14. **Is a source-backed required life available?** **No.**
15. **What category are the things that were found?** **A** (qualification: 1000 cycles) and
    **C** (accelerated condition: −40/+125 °C, 15-min dwell). **No category B.**
16. **Does any architecture fail it?** Unanswerable — there is no requirement to fail.
17. **Does reliability change the feasible architecture set?** **Not demonstrated.** A crossover
    band exists whose width is parameter-free but whose position is not.
18. **Does G2 pass?** **No — G2 remains NOT TESTED.**
19. **Electrical cost of reliability?** **+1.688 W for 1.56× life**, 8.76 W per decade.
20. **Is the global optimizer now justified?** **No.** Two of four gate conditions fail
    outright and a third is not evaluable.

## 17. Sec. 36 — verdict, and the four that were rejected

**NO ADMISSIBLE SAC305 LIFE LAW FOUND FOR THE CURRENT METRIC / REGIME**

| rejected | why |
|---|---|
| **A** G2 passed | Both halves of the inequality are missing. |
| **B / C** law acquired, all pass / all fail | No law was acquired. |
| **D** architecture-dependent fatigue life **proven** | The *metric* difference is proven and resolved; *fatigue life* is not, because no admissible law converts one into the other. "Proven" would overstate it. |
| **E** ranking is model-form dependent | The opposite is true — the ranking is identical across all three families and every exponent. Reporting E would invert a genuine positive result. |
| **G** law found but loading outside its valid domain | The cycle *is* incompatible, but this is not the operative blocker and the domain is not even knowable. F names the primary cause. |

## 18. Sec. 24 — what Phase 0K would need

Exactly two things, and both are **acquisition, not modelling**:

1. **A SAC305 fatigue relation matched to one of M1/M2/M3**, with its constants, its averaging
   volume, its calibration ΔT/dwell, and its own calibration data so the Sec. 8 reproduction can
   actually be run. Institutional access to IEEE Xplore and ASME would supply all three
   canonical papers immediately; that is the cheapest possible unblock.
2. **A declared required life** — from the system's owner, not the literature.

If (1) arrives with a calibration cycle far from ours, the third requirement becomes a
**justified acceleration relation or a re-run on the calibration cycle** — and the Norton
surrogate's 7.5–16 MPa window must be re-validated first at whatever temperatures that cycle
uses.

## 19. Residuals unchanged by this phase

No life law, no mission profile. Displacement-driven submodel, one joint, one critical BGA.
Norton surrogate valid 7.5–16 MPa. E(T) slope, CTE and ρ·c_p remain assumptions. MLCC height
OPEN. Z1 vs Z4 electrically unresolved. Six of eight failure mechanisms uncomputed.
