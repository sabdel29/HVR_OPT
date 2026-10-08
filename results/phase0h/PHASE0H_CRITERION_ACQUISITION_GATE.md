# Phase 0H — Mechanical Failure-Mechanism and Criterion Acquisition Gate

**Verdict: NO ADMISSIBLE MECHANICAL CRITERION FOUND — RESPONSE COUPLING ONLY**
**Falsification gate G2: NOT TESTED (unchanged since Phase 0B).**
**Recommendation: reframe the publication. Do not build the optimizer.**

---

## 1. What this phase was asked to settle

Not "find a warpage number that makes mechanics relevant", but: **does the physically mounted
DVPD system have any defensible mechanical inequality that can constrain the electrical
design?**

The answer is no, and Phase 0H can now say *why* rather than only *that*. Three findings, in
increasing order of how much they change the project:

1. **No admissible criterion exists.** Nine candidates, six admissibility conditions, zero
   admitted. Every published package-warpage allowable located is a manufacturing limit.
2. **The model can only see one of eight failure mechanisms**, and that one is a driver rather
   than a failure. Two of the three mechanisms the reference paper itself names are absent
   from the mechanical model entirely.
3. **Global warpage — the quantity this project measures best — does not predict the local
   loading, and inverts sign between assembly states.** The project has been measuring the
   load, not the damage.

## 2. Report-state repair first (DEFECT #32)

Phase 0G brought the *claims ledger* under `CURRENT_SCIENTIFIC_STATUS.yaml` and declared
DEFECT #29 closed. It was not. The Executive Summary, governing equations, validation status,
novelty statement, limitations, publication claims and next steps were still hand-written, and
the Phase-0G ledger deliberately exonerates a withdrawn claim whenever its heading names a
historical phase — correct for narrative, wrong for present tense.

Seven current-facing statements were stale behind a green build:

| stale statement | corrected to |
|---|---|
| "substrate thickness is win/win/win and survived every correction" | electrically thinner vs mechanically thicker, over a *narrowed* realizable band |
| "no architecture-dependent thickness tradeoff exists" | a robust, sign-stable thickness opposition |
| the Phase-0F ARCH_B interior optimum | withdrawn by DEFECT #30 |
| footprint as *the* ETM opposition novelty | withdrawn for mounted assemblies; the disciplines agree |
| `R_field = R_single / n_req`, no `n_alloc` in the symbol table | `n_req ≤ n_alloc ≤ n_avail`, resistance on `n_alloc`, symbol added |
| "**Not done:** MOOSE cross-check of the full 3-D package model" | done in Phase 0E as TH-1…TH-5, ordering preserved, max 1.66 % |
| "BC-B is a compliant support layer" | BC-B is a three-DOF **clamp**, withdrawn as a mounted model |

All seven are now **generated** from the YAML into sentinel-delimited blocks, the report is
checked to carry each block verbatim, and a **current-facing section audit** forbids nine
stale-claim signatures inside present-tense sections. Verified both ways: the clean report
passes, and nine injected stale claims are each caught.

### A guard that could not fail, again

While negative-testing those nine guards, **two were found incapable of matching**: their
patterns had been corrupted when written to disk — a lost backslash in one, and `\b`
interpreted as literal backspace bytes in the other. They reported PASS on text they existed to
reject. This is DEFECT #31 in a new form: not faulty logic, but a faulty *source*. A
control-character scan of the guard source is now part of every build, and is itself
negative-tested.

## 3. DEFECT #30 made structural, and propagated

Phase 0G fixed the arithmetic and wrote a comment. A comment cannot fail a build.
`scripts/phase0h/scope.py` now gives every electrical quantity a scope:

```
Q(value, units, scope: PER_REGULATOR | SYSTEM, tier, rail)
```

Adding across scopes raises `ScopeError` naming DEFECT #30; `total()` rejects bare floats and
wrong-scope terms; scalar multiplication deliberately does **not** change scope, so the old
`p_w * n_vr` spelling cannot launder one into the other. Seventeen tests, and two mutations
confirmed they fail when the protection is removed.

**Propagating it changed a published conclusion.** Replaying the eleven Phase-0E 240-W
candidates moves **three ranking positions**. The correction is architecture-selective: ARCH_A
cases shift 16–25 mW, ARCH_B at `h = 0.5 mm` shifts **+356.83 mW (+1.58 %)** and falls from
third-best to worst. DEFECT #30 flattered ARCH_B at 240 W as well as at the reference scale.

The 1-kW decomposition also reclassifies a Phase-0D-R claim: *"RDL dominates distribution
loss"* holds for ARCH_A at every thickness (0.642 W vs 0.010–0.163 W) and **fails for ARCH_B**
above ~0.9 mm, where the via field exceeds the RDL by up to 11×.

## 4. Failure mechanisms: the model sees one of eight

| # | mechanism | computable at M0? | blocking requirement |
|---|---|---|---|
| A | global package bending | **YES** | — but it is a response, not a failure |
| B | BGA solder fatigue | NO | discrete balls + viscoplasticity + cycling |
| C | microbump / C4 | PARTIAL | smeared layer; no per-joint strain |
| D | RDL damage | NO | **the RDL is not in the mechanical mesh at all** |
| E | die / low-k CPI | NO | homogenisation invalid for local stress (+82 to +97 %) |
| F | delamination | NO | fracture mechanics; peel is a corner singularity |
| G | TSV interaction | NO | homogenised via field |

June-2026 names three mechanisms — *"global package warpage, delamination risk, and shear
stress in the redistribution layer"*. **Two of those three are outside the model.**

## 5. Standards: category-1 limits, and one that is not a limit at all

`jedec.org` and the ANSI webstore return HTTP 403 here, so **IPC-9641 was read directly** and
the JEDEC family characterised from peer-reviewed open-access work that applies it. No standard
is cited from memory.

* **IPC-9641** — read in full. *"the purpose of this **test method** is to measure the shape …
  **of printed boards** through a range of temperatures typical during surface mount"*, aimed
  at *"open or bridging joints"*. It governs the **board**, references **reflow**, and contains
  **no allowable**.
* **JESD22-B112C** is a **measurement method** (thermal shadow moiré, DIC, laser reflection),
  not an allowable. The allowables live in **JEP95** (80 µm room-temperature ball-plane
  coplanarity, ≤21 mm body) and **SPP-024** (−120/+170 µm at peak reflow, >15 mm body).
* A 2025 review supplies the only package-level warpage numbers found anywhere: **0.2 mm
  maximum, 0.1 mm preferred** — explicitly *"for high yields"* during wafer-level packaging.
  The same review lists *"Need for Materials Data and Failure Criteria"* as an open challenge
  for the field.

Every one is **category 1: manufacturing and solderability**. None is a category-4 operational
design allowable, and that is structural: operating-life limits are set by product
qualification, not by package-outline documents.

## 6. Admissibility: nine candidates, zero admitted

| candidate | conditions met | verdict |
|---|---|---|
| JEP95 room-temperature coplanarity, 80 µm | 1 / 6 | REJECTED |
| SPP-024 peak-reflow warpage, −120/+170 µm | 2 / 6 | REJECTED |
| Wafer-level-packaging yield guidance, 0.2 / 0.1 mm | 1 / 6 | REJECTED |
| IPC-9641 board flatness | 0 / 6 | REJECTED |
| Accelerated thermal-cycling life N63.2 (12 alloys) | 3 / 6 | REJECTED as a design constraint |
| Solder strain-energy density ΔW → N_f | 2 / 6 | REJECTED as a design constraint |
| smeared interface shear τ₉₉ (this project) | 3 / 6 | NOT A CRITERION |
| relative interface displacement Δu (this project) | 3 / 6 | NOT A CRITERION |
| global die warpage P-V (this project) | 3 / 6 | NOT A CRITERION |

The **SPP-024** row deserves emphasis: at −120/+170 µm for a comparable body size it is the
closest published number to this project's computed range, and it is measuring a different
quantity, in a different package state, at a different temperature, for a different failure
mechanism. Proximity in magnitude is not admissibility.

## 7. Global warpage is not the reliability quantity

Seventy paired runs spanning assembly model, board case, thickness, footprint, reference
temperature and thermal boundary:

| subset | n | vs interface shear τ₉₉ | vs relative displacement Δu |
|---|---|---|---|
| all cases | 70 | ρ = **0.112** | ρ = 0.680 |
| mounted | 42 | ρ = **0.349** | ρ = 0.738 |
| free | 17 | ρ = **−0.793** | ρ = −0.177 |
| clamped | 11 | ρ = **−0.022** | ρ = 0.288 |

Across the mounted thickness sweep, **warpage varies 3.0× (9.66 → 29.23 µm) while shear stays
within ±9 %.** And the sign inverts between assembly states: in the free package a design that
raises warpage *lowers* interface shear.

**Global warpage is an architectural response metric, not a reliability quantity.** Phase 0G's
"below 40 µm" therefore carries no margin information — the second, independent reason the
Sec. 18 retraction was required.

## 8. Neither local metric is fit to replace it

Revalidated on the explicit board at `h_sub = 1.50 mm`:

| metric | mesh convergence | material-corner spread | singularity | usable? |
|---|---|---|---|---|
| die warpage P-V | **+0.02 %** | **4.00 %** | n/a | numerically yes — **but Sec. 7 disqualifies it** |
| interface shear τ₉₉ | +2.50 %, **non-monotone** (7.6 % spread) | 14.14 % | **samples a bimaterial corner** | no |
| relative displacement Δu | −1.22 %, monotone | **26.52 %** | not singular | no |

The dominant sensitivity is the **underfill modulus**, which the stack flags `PROVISIONAL …
UNSPECIFIED and HIGH-RISK`. The closing shape of the mechanical side of this project is:
**the quantity that is trustworthy is not meaningful, and the quantities that are meaningful
are not trustworthy.**

## 9. Geometry closure — and the electrical optimum becomes unbuildable

Phase 0F recorded GaN and MLCC heights as OPEN and invented a 0/100/250 µm envelope. The EPC
*product table* has no heights, but the **datasheets do**, and this environment can reach them:

| device | role | height |
|---|---|---|
| EPC2212 | high side | **685 µm nominal, 815 µm max** |
| EPC2090 | low side | **606 µm** (518 ± 25 die + 50 Cu + 3 Ni + 35 solder) |

Six to eight times the assumed nominal, and 2.4–3.3× the assumed *pessimistic* bound. June-2026
states which devices are embedded: *"low-side switches (bottom layer), flying capacitors
(middle layer), and inductors (top layer) are embedded within the subsequent substrate power
layers"*, with the high side flip-chipped to the RDL below.

| MLCC (still OPEN) | t_cell | **h_sub,min** |
|---|---|---|
| 0 µm | 1126 µm | **1.176 mm** |
| 100 µm | 1226 µm | **1.276 mm** |
| 250 µm | 1376 µm | **1.426 mm** |

Against Phase 0F's 0.770 mm. **The corrected ARCH_B electrical optimum at `h = 0.80 mm` is
infeasible by 376–626 µm**, as are 0.90 and 1.00 mm.

*Caveat carried with the result:* datasheet heights are as-supplied. Die thinning before
embedding is a normal packaging step and the reference system does not say whether it is used.
The as-supplied value is the conservative, sourced choice; a thinned variant is not modelled
because no source specifies one.

## 10. The thickness response, on the buildable band

MLCC-nominal band, 1.30 → 2.00 mm:

| quantity | change | resolved against its own uncertainty? |
|---|---|---|
| ΔP_elec, ARCH_B | **+4042.6 mW** (thinner better) | yes, overwhelmingly |
| ΔP_elec, ARCH_A | +77.7 mW | yes |
| ΔT_max | +0.127 K | — |
| Δ die warpage | **−5.824 µm (−29.3 %)** (thicker better) | **YES** — 7× the 4.00 % floor |
| Δ interface shear τ₉₉ | +0.156 MPa (**+1.96 %**) | **NO** — 7× *below* its 14.14 % floor |

So the opposition survives, and it is resolved **only in global warpage** — the quantity Sec. 7
disqualified. In the one local metric available, the thickness effect cannot be resolved at all.

That is a sharper statement than Phase 0G's, and a less comfortable one.

## 11. Footprint — frozen

Phase 0G's mounted result stands: larger footprint is electrically better by 6.633 W and
mechanically better on all five boards (`S_A` = −0.166 to −0.290). Nothing in Phase 0H changes
the physical model enough to justify re-running it.

**FROZEN: NO MOUNTED FOOTPRINT ETM OPPOSITION.** The free-package footprint opposition is no
longer advertised as the system-design novelty anywhere in the current-facing text.

## 12. Verdict, and why not the alternatives

**NO ADMISSIBLE MECHANICAL CRITERION FOUND — RESPONSE COUPLING ONLY.**

| alternative | why not |
|---|---|
| MECHANICAL CRITERION ACQUIRED — G2 PASSES | 0 of 9 admitted |
| MECHANICAL CRITERION ACQUIRED — NON-BINDING | nothing was acquired; every candidate failed admissibility |
| LOCAL RELIABILITY METRIC REPLACES GLOBAL WARPAGE | global warpage *is* disqualified, but neither local candidate survived validation. Nothing replaces it, and claiming otherwise would overstate the result. |
| INSUFFICIENT MATERIAL / ASSEMBLY DATA | true as a sub-finding — mechanism B is NOT TESTABLE WITH PRESENT DATA — but the dominant fact is admissibility. Criteria were found; none applies to the operational mounted state. |

## 13. Recommendation: reframe, do not optimize

Sec. 17 of the brief applies. The search covered the standards family and 479 primary works and
returned zero admissible criteria for a structural reason, so continuing is not expected to
converge.

**Reframe from "ETM co-synthesis optimizer" to "AUDITED CROSS-DOMAIN DVPD MODELLING AND
FALSIFICATION".** The contribution is unusually well evidenced and includes:

* physical realizability as a first-class coupling, now with **sourced** component heights that
  exclude the entire previously-swept thickness range;
* rail-aware vertical interconnect modelling (~1960× loss difference by rail);
* allocation-policy-dependent via-field loss scaling;
* an electrothermal fixed point with per-regulator local temperature;
* mounted package mechanics continuous with its own free limit, unlike a compact clamp;
* a demonstrated, sign-stable thickness response opposition;
* **NEGATIVE:** footprint opposition disappears once the package is mounted — in the direction
  the reference paper itself asserts;
* **NEGATIVE:** global warpage does not predict local loading and inverts sign between
  assembly states;
* **NEGATIVE:** no admissible mechanical criterion exists, with the reason categorised;
* four defects, each caught by a named discipline rather than by luck.

### What would unblock a constrained optimizer

1. An operational-state allowable for **this** stack — a qualification specification or
   measurement, not a literature value from a different package state.
2. Discrete-joint geometry, a viscoplastic solder model, and a mission profile.
3. A sourced underfill modulus, without which the best local metric carries 26.5 % uncertainty.
4. MLCC height and a board specification, to turn envelopes into predictions.

**The global ETM optimizer was not built and is not recommended.**

## 14. Artifacts

| artifact | section |
|---|---|
| `DEFECT30_GLOBAL_PROPAGATION_AUDIT.md` | 2 |
| `FAILURE_MECHANISM_MAP.md` | 3 |
| `STANDARDS_APPLICABILITY_AUDIT.md` | 4, 5 |
| `MECHANICAL_CRITERION_LITERATURE_DATABASE.csv` (6 examined, 473 metadata) | 6 |
| `local_metric_selection.md` | 7, 8, 9, 10 |
| `warpage_local_correlation.csv`, `warpage_local_pairs.csv` | 7 |
| `local_metric_convergence.csv` | 10 |
| `board_stack_closure.md` | 11 |
| `geometry_height_closure.md` | 12 |
| `thickness_response_final.csv` | 13 |
| `criterion_admissibility.csv` | 15 |
| `replay240_candidates.csv`, `interconnect_decomposition_1kw.csv` | 2 |
| `../CURRENT_SCIENTIFIC_STATUS.yaml` | 1, 19 |
| `PHASE0H_CRITERION_ACQUISITION_GATE.md` (this document) | 19, 20 |

Figures `FIG_0H_A` … `FIG_0H_F` (6).

### Known residuals

* **MLCC height remains OPEN** — Murata is unreachable here — so `h_sub,min` is a 250 µm band.
* **Board laminate remains an envelope**; the reference framework is platform-agnostic by
  design, so no specification exists to find.
* **Underfill modulus remains PROVISIONAL** and dominates local-metric uncertainty.
* **Interface peel remains excluded**; the convergent replacement (energy release rate) is not
  implemented.
* **Icepak remains unusable**; the 5000 K clamped solution is never used.
* The corrected 240-W ranking is a corrected ranking of designs that **cannot be built** —
  reported because the question was whether the correction changes a published conclusion.
