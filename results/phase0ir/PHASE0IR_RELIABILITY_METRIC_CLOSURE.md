# Phase 0I-R — Reliability-Metric, Claim-Scope and Report-Consistency Closure

**Verdict: PHASE-0I METRIC VALID AFTER REDEFINITION — READY FOR LIFE-LAW ACQUISITION**

**The creep-omission failure mode did NOT occur.** No Phase-0I result required replay.
**The life interpretation IS withdrawn.** **Z1 vs Z4 is NOT electrically resolved.**

---

## 1. What exactly is Δε_in?

Phase 0I justified its metric by quoting a CalculiX warning — *"selection of CEEQ or CE or PE
is converted into PEEQ; no distinction is made"* — and inferring that PEEQ aggregates plastic
and creep. **That inference does not follow.** The warning describes how the output *request*
is aliased, which is equally consistent with PEEQ being plastic-only and the creep request
being silently discarded. The question was settled here by experiment.

### The decisive experiment

Four single-element probes, each comparing the solver's `PEEQ` against an equivalent inelastic
strain computed independently from the solver's own tensors:

| case | material | **PEEQ / eq(ε_inelastic)** |
|---|---|---|
| creep only, **no `*PLASTIC` card at all** | elastic + Norton creep | **1.0000** |
| plastic only, no `*CREEP` | elastic + plastic | **1.0000** |
| both, ramped | elastic + plastic + creep | **1.0000** |
| both, 3000 s hold with stress relaxing 35.7 → 17.8 MPa | elastic + plastic + creep | **1.0000** |

The creep-only row settles it: with no plasticity in the deck, PEEQ is non-zero and equals the
equivalent creep strain to five figures.

The identity was then re-established in the **actual multiaxial, temperature-varying joint**:
PEEQ / eq(ε_inelastic) = **1.0029–1.0035 at the first output** for all three material variants.

### The answer

```
PEEQ = accumulated equivalent inelastic strain,  plastic AND creep together
     = eq( ε_total − ε_elastic − ε_thermal ),  integrated along the deformation path

Δε_in(cycle k) = PEEQ(t_end,k) − PEEQ(t_end,k−1)
               = the inelastic PATH LENGTH traversed in one cycle,
                 volume-averaged over the solder core with a 1-element corner exclusion band
```

### The one thing Phase 0I got wrong about it

**PEEQ is a path length, not a state.** It accumulates monotonically; the instantaneous
equivalent inelastic strain oscillates. Phase 0I described its metric as an *"inelastic strain
range"*. It is not a range:

| quantity, stabilised cycle | EP | EPC |
|---|---|---|
| Δ(PEEQ) per cycle — **the Phase-0I metric** | 8.524e−3 | 5.980e−3 |
| range of eq(ε_in) within the cycle | 2.254e−3 | 1.609e−3 |
| **ratio** | **3.78** | **3.72** |

A fully-reversed uniaxial cycle would give 2.0; this OFF→ON→OFF cycle is a multi-reversal path
in strain space, so it gives 3.7. **A future life law calibrated against a strain *range* would
be misapplied by that factor** if fed this metric directly. That is the redefinition the
verdict refers to: the **values are correct and stand**, the **label was wrong**.

## 2. Sec. 5 — did creep get omitted? No.

The failure mode this audit was commissioned to find — creep relaxes stress, plastic strain
falls, a plastic-only parser reports "damage decreased", and the creep deformation is invisible
— **did not occur**. PEEQ contains creep, proven above.

Independent confirmation from the joint: the creep-only variant **EC** returns
Δε_in = 6.664e−3, plainly non-zero, from a deck with no `*PLASTIC` card.

**The Phase-0I −27.2 % result therefore survives as a statement about the strain-based
metric.** No replay of any Phase-0I number was required and none was performed.

## 3. Sec. 6 — but the energy diagnostic points the other way

Sec. 6 asked whether strain-based damage falls while dissipated energy rises, and instructed
that if so it must be reported and not hidden. **It does, emphatically.** Same three solves,
both quantities from the same output:

| model | Δε_in per cycle | vs EP | dissipated inelastic work (MJ/m³) | vs EP |
|---|---|---|---|---|
| **EP** elastic + plastic, no creep | 8.524e−3 | — | 0.2064 | — |
| **EC** elastic + creep, no plasticity | 6.664e−3 | −21.8 % | 0.5773 | **+179.7 %** |
| **EPC** full (Phase 0I) | 5.980e−3 | **−29.8 %** | 0.5461 | **+164.6 %** |

Creep relaxes stress and so suppresses plastic strain accumulation, yet it deforms at sustained
stress throughout every dwell and dissipates far more energy. **The sign of "does the new
physics increase or decrease damage" depends on which measure you choose.**

Consequence, and it is binding on Phase 0J: **no direction-of-change statement about creep may
be written without naming the measure**, and the life law acquired in Phase 0J must be matched
to the measure it was calibrated against — a Coffin-Manson-type law to the strain form, a
Darveaux-type law to the energy form.

### A defect found in this audit's own first attempt

The energy integral initially returned **negative dissipation**, which is impossible. The cause
was in the audit, not the solver: **CalculiX ramps `*TEMPERATURE` linearly across a step**
unless `AMPLITUDE=STEP` is given, so reconstructing temperature from the step schedule is wrong
mid-step and corrupts the thermal-strain subtraction. Reading the solver's own `NT` output
fixed it — all dissipation became positive, and the PEEQ identity check sharpened from 0.9467
to 1.0029.

## 4. Does the metric choice change the ARCHITECTURE conclusion? No.

This is the question that decides whether Phase 0I's architecture claims survive Sec. 6. All
three inelastic measures, computed from the same solves:

| architecture | Δ(PEEQ)/cycle vs Z1 | strain range vs Z1 | inelastic work vs Z1 |
|---|---|---|---|
| Z1 embedded | — | — | — |
| **Z2 backside** | **−35.8 %** | **−35.7 %** | **−37.7 %** |
| **Z4 power die** | **+12.4 %** | **+12.6 %** | **+13.0 %** |

**All three agree on ranking and on magnitude to within 2 pp.** The architecture conclusion is
metric-independent. Only the creep-inclusion question is metric-dependent.

## 5. Sec. 7 — stabilised-cycle extraction is correct

| model | cycle 3 | cycle 4 | change |
|---|---|---|---|
| EP | 8.586e−3 | 8.524e−3 | 0.72 % |
| EPC | 6.046e−3 | 5.980e−3 | **1.08 %** |
| Z1 / Z2 / Z4 architecture runs | — | — | 0.80 / 2.00 / 0.48 % |

The metric is a **per-cycle difference of an accumulated quantity**, so it is not contaminated
by total accumulated creep — the differencing removes the accumulation. The ratio to the
within-cycle range is stable at 3.72–3.78 by cycle 3, confirming a settled loop shape and not
merely a settled number.

## 6. Sec. 15 — is the damage difference resolved?

Adding the RMS uncertainties would have been wrong: the three architectures share the same
material card, mesh, exclusion band and solver tolerance, so those errors are **common mode**
and largely cancel in a ratio. The uncertainty was therefore measured **on the ratio**, with
each perturbation applied to all three architectures at once:

| perturbation | Z2/Z1 | Z4/Z1 |
|---|---|---|
| reference | 0.6418 | 1.1238 |
| Norton A ±12 % (worst fit residual) | 0.6433 / 0.6402 | 1.1233 / 1.1244 |
| E(T) ±15 % (the slope is an ASSUMPTION) | 0.6667 / 0.6043 | 1.1144 / 1.1385 |
| yield ±10 % | 0.6312 / 0.6522 | 1.1280 / 1.1198 |
| coarser mesh | 0.6394 | 1.1251 |
| 2-element exclusion band | 0.6413 | 1.1200 |

| comparison | effect | spread over ALL perturbations | ratio | verdict |
|---|---|---|---|---|
| Z2 / Z1 | −36.0 % | 6.2 pp | **5.8×** | **RESOLVED** |
| Z4 / Z1 | +12.4 % | 2.4 pp | **5.1×** | **RESOLVED** |

Note that the absolute damage moves a lot under these perturbations (E ×1.15 raises Z1 by 9 %)
while the ratios barely move. That is the common-mode cancellation working, and it is why the
architecture claim is stronger than the absolute numbers are.

## 7. Sec. 14 — Z1 vs Z4 is NOT electrically resolved

Every electrical tier except `P_TSV` is **bit-identical** between architectures — converter
125.2644 W, RDL 0.6451 W, BGA 0.1139 W, microbump 0.0566 W — so those model errors cancel
exactly and the entire Z4−Z1 difference of 29.93 mW is the via-field term.

That looked resolved until the dominant term was identified: **the electrical sweep evaluated
every architecture at a frozen `T_c` = 85.0 °C**, forcing the converter loss identical. The
global model shows the two packages differ by **1.444 K in T_max**. At `dP_conv/dT` = 148 mW/K
that is **213.8 mW — 7.1× the claimed difference, and of the opposite sign**: Z4 runs *cooler*,
so its converter would dissipate *less*, more than erasing its 30 mW via penalty.

| comparison | difference | dominant uncertainty | σ | verdict |
|---|---|---|---|---|
| **Z4 − Z1** | +29.93 mW (0.024 % of total) | 213.8 mW neglected temperature coupling | **0.14** | **UNRESOLVED** |
| **Z2 − Z1** | +1688.11 mW (1.3 % of total) | 282.1 mW combined | **5.98** | **RESOLVED** |

**Z1 AND Z4 ARE ELECTRICALLY INDISTINGUISHABLE AT CURRENT FIDELITY.** Z1 must not be described
as electrically preferred. The Z2 penalty stands.

## 8. Sec. 9/10 — the relative-life claim was wrong in kind

Phase 0I wrote that relative life is *"parameter-free in the life-law constant"*. Literally
true of `C`; **misleading as written**, because it invites the reading that the ratio is
parameter-free. For `N_f = C·Δε_in^(−m)`:

```
N_f,2 / N_f,1 = (Δε_in,1 / Δε_in,2)^m      C cancels.  m does NOT.
```

**Provenance of the exponent, traced:** the range `m = 1.5–3` appears exactly once in the
Phase-0I codebase — as a figure annotation reading *"typical solder k is 1.5–3"* in
`make_figures.py`. It was written from general knowledge, appears in **no retrieved source**,
and was never labelled. It is the sole basis of the headline "1.9–3.8× relative life".

**Status: UNSOURCED.**

| m | Z2/Z1 | Z4/Z1 |
|---|---|---|
| 0.5 | 1.25 | 0.94 |
| 1.5 | 1.94 | 0.84 |
| 3.0 | 3.78 | 0.70 |
| 5.0 | **9.18** | 0.56 |

Over m = 0.5–5 the Z2/Z1 ratio spans **1.25 to 9.18 — a factor of 7.4 from the exponent
alone**. All life ratios are now labelled **PARAMETRIC LIFE-LAW SENSITIVITY**.

**What may be claimed** is the metric ratio, which is a model output: Z2 is 35.8 % below Z1 and
Z4 is 12.4 % above it, both resolved.

## 9. Sec. 11/13 — claim scope

**Retained in full (DEFECT #33):** the Phase-0H bound was not universal. Component height
constrains `h_sub` **only** for the embedded architecture.

**Scoped:** 0.300 mm is **COMPONENT-HEIGHT-REALIZABLE UNDER THE CURRENT Z-ARCHITECTURE MODEL**
and a source-demonstrated TSV-layer thickness. It is **not** a manufacturability guarantee —
backside clearance, power-die attach, cooler and board clearance, bump-stack budget, cavity and
lid rules, handling and the full design-rule set are all unmodelled.

**Scoped:** only **the tested Z5 low-voltage-lateral topology** is electrically eliminated, by
~768 W of modelled RDL loss. Not 2.5D as a class.

## 10. Sec. 16/17 — two reframings

**Warpage.** Phase 0I reported Spearman 1.000 within each architecture and read it as warpage
tracking damage. Within a single architecture the thickness sweep is monotonic and *both*
quantities move monotonically with it, so ρ = 1.000 is close to guaranteed by construction. The
defensible statement is **directional only**: warpage tracks the *direction* of local damage
but not its magnitude, changing 29.7–52.6 % where damage changes 5.6–17.2 % — **exaggerating
the apparent reliability benefit by 3–5×**. Global warpage is **not** a calibrated surrogate.

**Temperature.** Two true statements that must not be conflated:
**(A)** temperature-dependent material physics matters — a frozen-property model moves −0.2 %
across a 50 K shift in cycle mean where the full model moves +22.7 %;
**(B)** these particular architectures happen to have near-identical joint temperatures
(81.10–83.21 °C, r = +0.017 against damage), so **their** reliability difference is mechanical,
not thermal.

## 11. Sec. 18 — DEFECT #35, and the guard that could not see the live section

Seven current-facing statements were still in the Phase-0H state after Phase 0I: the summary
framed the answer as "Phases 0G and 0H find"; the limitations said "Neither local metric is fit
for decisions" (true of the two *rejected* Phase-0H proxies, false of the new M2 metric);
"GaN and MLCC layer heights are still open" when GaN is sourced; next work still recommended
publication reframing; validation still said "M0 — no plasticity, creep or fatigue"; the
governing equations stopped at M0; and the method still counted eight gates. All repaired at
the single source of truth, with **GLOBAL M0** and **LOCAL M2** now split explicitly and four
M2 equations added.

A second finding: **the guard scope excluded the live phase narrative.** Phase 0I's section is
headed *"(current authoritative)"* yet was not in the current-facing list, so its over-claims —
"Z5 is eliminated", "1.9–3.8× relative life", "Z1 keeps a 30 mW edge" — were never checked.
Scope widened; all six new Sec. 20 guards negative-tested and each one fails the build on its
own injection.

## 12. Sec. 24 — conditions for Phase 0J

| condition | status |
|---|---|
| 1. the local metric is exactly defined | **MET** — §1, with the path-length/range distinction stated |
| 2. plastic and creep contributions correctly represented | **MET** — proven by experiment, ratio 1.0000 |
| 3. stabilised-cycle extraction correct | **MET** — 0.48–2.00 % at cycle 4, loop shape settled |
| 4. Z2 architecture separation resolved | **MET** — 5.8× its perturbation spread |
| 5. compatible in principle with a known class of SAC305 fatigue law | **MET, with a caveat** — the accumulated-path-length form suits damage-accumulation formulations directly, and converts to a range by the measured factor 3.72. Phase 0J must match the law to the form, or convert explicitly. |

**All five met. Phase 0J is recommended**, to acquire exactly two things: a SAC305 fatigue
relation matched to this metric (with its exponent, constant, temperature and package
applicability), and a source-backed or explicitly declared mission requirement.

## 13. Artifacts

`CALCULIX_INELASTIC_OUTPUT_AUDIT.md` · `strain_component_decomposition.csv` ·
`strain_vs_energy_damage_diagnostic.csv` · `stabilized_cycle_audit.csv` ·
`architecture_metric_agreement.csv` · `relative_life_exponent_sensitivity.csv` ·
`REALIZABILITY_CLAIM_SCOPE_AUDIT.md` · `electrical_architecture_resolution.csv` ·
`damage_uncertainty_resolution.csv` · `REPORT_CONSISTENCY_AUDIT.md` ·
figures `FIG_0IR_A`–`FIG_0IR_E` · `ccx_audit/` (the single-element probes).

### Residuals unchanged by this audit

No life law, no mission profile; displacement-driven submodel, one joint; Norton surrogate
valid 7.5–16 MPa; E(T) slope and CTE assumed; MLCC height OPEN; ρ·c_p a handbook assumption.
