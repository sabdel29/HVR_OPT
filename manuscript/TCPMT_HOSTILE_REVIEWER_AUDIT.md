# HOSTILE TCPMT REVIEWER AUDIT

Written adversarially, as a skeptical IEEE TCPMT reviewer looking for reasons to reject.
Each objection is stated in the form a reviewer would actually write it, then answered from
the manuscript as it stands. Where the manuscript does not answer, that is recorded as such.

Severity scale: **CRITICAL** (would sink the paper) · **MAJOR** (revision required) ·
**MODERATE** (clarification) · **MINOR** (editorial).

Status: **CLOSED** · **PARTIALLY CLOSED** · **OPEN BUT ACCEPTABLE LIMITATION** ·
**SUBMISSION BLOCKER**.

---

## R1 — The solder constitutive model is used an order of magnitude outside its fit

**Objection.** "The Norton card is fitted over 7.51–15.92 MPa. By the authors' own admission
the final joints run at 15–17 times yield, with an elastic trial shear near 195 MPa. A power
law with n ≈ 7 extrapolated an order of magnitude beyond its calibration is not a model, it
is an extrapolation. Why should any number derived from it be believed?"

**Why raised.** This is the single largest model-form risk in the paper, and the authors put
the number in the abstract.

**Severity: CRITICAL.**

**Manuscript answer.** The paper does not claim the magnitude. It claims the *ordering*, and
states the magnitude as an envelope. The extrapolation is quantified rather than hidden: §VIII-C
gives the trial shear (195 and 159 MPa), the yield stress at temperature (11.6 and 10.7 MPa),
the ratio (15–17×) and the fitted window. The ordering is shown to survive every constitutive
variant admitted, all three local metrics returned by the same solves (Δε_in 1.2260, strain
range 1.2257, inelastic work 1.1658 — Table II), and the complete geometric refinement
sequence (Fig. 7).

**Where.** §VIII-C first limitation; §VII-D; Table II; Fig. 7; abstract closing sentence.

**Status: OPEN BUT ACCEPTABLE LIMITATION.** The limitation is real, disclosed, quantified and
correctly scoped. A reviewer may still argue the 18.4 % should be removed from the abstract;
the counter is that the abstract attaches it to a named submodel and immediately qualifies it.

**Minimal action.** None required. **New science required: yes** — a SAC305 characterisation
at the stresses these packages generate, already listed as future work.

---

## R2 — The high-stress solution exists only because the tolerance was relaxed

**Objection.** "The final solves use CETOL = 5e-2, looser than the 1e-2 used elsewhere in the
authors' own work, and the paper admits tighter tolerances will not run. This is a solution
obtained by weakening the convergence criterion until something came out. How do we know the
18.4 % is not an integration artifact?"

**Why raised.** It is the obvious reading of "we loosened the tolerance and then it worked."

**Severity: CRITICAL.**

**Manuscript answer.** Measured directly and reported in full, including the failures. Five
tolerances spanning 1e-5 to 1e-1 were run with every other input fixed. Three tighter values
(1e-5, 1e-4, 1e-2) complete **zero** increments. The two that converge, 5e-2 and 1e-1, take
the same 336 increments with **zero** cutbacks and return Δε_in, its range and the inelastic
work **identical to twelve digits** for both architectures; D_ε is 1.226006 at both. Doubling
the tolerance moves the result by exactly nothing, which is the direct test: a
tolerance-driven solution would have moved.

**Where.** §IV-E (ladder, failures, identity); §V-D (zero against 1.9 % for the mesh);
§VIII-C (the one-sided bracket); `CETOL_FINAL_PAIR_ROBUSTNESS.md`; `cetol_final_pair.csv`.

**Status: PARTIALLY CLOSED.** The artifact hypothesis is refuted from above. The bracket is
one-sided — no tighter tolerance converges, so agreement with a tight-tolerance reference is
not demonstrated, and the manuscript says so in those words rather than implying two-sided
convergence.

**Minimal action.** None. **New science required: no.**

---

## R3 — Why ΔPEEQ, why is it not damage, and why is no life predicted?

**Objection.** "The paper reports an accumulated inelastic strain increment and calls it a
reliability response. Either it predicts something about reliability, in which case show the
life model, or it does not, in which case why is 'reliability' in the title?"

**Why raised.** The terminology promises more than the physics delivers.

**Severity: MAJOR.**

**Manuscript answer.** The hierarchy is explicit and maintained end to end: global warpage →
corner-joint displacement driver Δu_c → local inelastic response Δε_in → **stop**. §IV-E
states that converting the response to damage requires a damage law, damage to life requires
a life relation, and life to pass/fail requires an allowable, and that none of the three is
established or performed. Δε_in is defined as an inelastic *path length* per cycle, not a
strain range, and the distinction is verified by a creep-only experiment returning unity.
Global warpage is shown insufficient: it moves 6.5 % where the driver moves 16.3 % and the
response 18.4 %.

**Where.** §IV-D, §IV-E (Eq. 15–18), §VII-A, Table II, `ETM_DVPD_CLAIM_AUDIT.md`.

**Status: CLOSED on the physics; the title is a separate finding — see R11.**

**Minimal action.** Title change (R11). **New science required: no.**

---

## R4 — Hotter yet lower response looks like an artifact of the imposed displacement

**Objection.** "Z2 is 8.14 K hotter and has 18.4 % lower inelastic response. Since the
submodel is displacement-driven and Z2 is simply given a smaller displacement, the result is
arithmetic, not physics. The temperature never gets a chance to matter."

**Why raised.** A displacement-controlled submodel does look like it pre-determines the answer.

**Severity: MAJOR.**

**Manuscript answer.** The two effects are separated by cross cases through the same
submodel. Applying the backside displacement at the embedded joint temperature gives
**19.39 %** below the embedded response — *more* than the 16.3 % reduction in the driver
itself, because the response is nonlinear in displacement through Eq. (16). Applying the
embedded displacement at the backside joint temperature **raises** the response by 0.75 %.
The hotter joint therefore works *against* Z2 and returns part of its advantage; the net
18.43 % exceeds the driver separation despite the temperature, not because of it. Temperature
is inside the response model, not excluded from it.

**Where.** §VII-D; `local_response_decomposition.csv`; `FINAL_LOCAL_RESPONSE_AUDIT.md` §8.

**Status: CLOSED.** **New science required: no.**

---

## R5 — The converter loss model is incomplete

**Objection.** "No inductor core loss, no capacitor dielectric loss, no temperature
dependence on the switching terms, and α_GaN is a number with no source. The efficiency is
therefore unknown, and if the loss is wrong the temperatures are wrong and the mechanics
follows."

**Why raised.** Omissions plus an unsourced coefficient in the dominant loss path.

**Severity: MAJOR.**

**Manuscript answer.** The omissions are declared, not discovered: §III-B states that only
the winding resistance and ESR are consumed, that both omissions bias dissipation downward
and act on the same component set in both architectures, that the ordering is therefore *not
expected* to be altered — with exact cancellation explicitly not asserted, because the two
architectures run at different temperatures — and that the absolute efficiency remains
underestimated. Switching terms are left temperature-independent deliberately, and the paper
says nothing in the repository supports a temperature law for them. α_GaN is labelled an
**adopted calibration coefficient, not a sourced material constant**, with the reason (the
device tables carry no temperature columns), the measured sensitivity (±20 % → ∓5.8 % on
converter loss; ±33 % through the converged loop → ≤1.2 K on peak temperature) and the
finding that the Z1/Z2 loss ordering is preserved at every value tested.

**Where.** §III-B (both passages); `GAN_TEMP_COEFF_AUDIT.md`; `gan_alpha_sensitivity.csv`.

**Status: CLOSED for the ordering; OPEN BUT ACCEPTABLE for absolute efficiency**, which the
paper does not claim. **New science required: no.**

---

## R6 — No conjugate CFD, so the absolute temperatures are unsupported

**Objection.** "A 1 kW package is cooled by a correlation. Without conjugate CFD the peak
temperature is a guess, and the whole thermomechanical chain hangs on it."

**Why raised.** Correlation-based cooling under a kilowatt load invites suspicion.

**Severity: MAJOR.**

**Manuscript answer.** The operating point is shown to be *inside* the model's validated
domain rather than assumed to be: Re = 1264.8, laminar, against a validated ceiling of 2300;
the solid side agrees with an explicitly meshed fin solution to 3.78 %; a short thick fin
outside the adopted envelope disagreed by 10.11 % and was **rejected rather than accepted as
a tolerance**; the transitional band 2300–3000 is refused rather than interpolated because
the two neighbouring correlations differ there by a factor of 2.8. Conjugate CFD was
attempted, the run was discarded, and the paper states that no CFD validation is claimed and
that no number from that attempt appears anywhere. Absolute temperatures are declared
conditional; the architecture *difference* is argued to arise from where the 1 V rail runs,
not from the cooling correlation.

**Where.** §IV-B, §V-C, Table IV, Table V (last two rows), §VIII-C.

**Status: OPEN BUT ACCEPTABLE LIMITATION.** Correctly scoped and honestly reported.
**New science required: yes** for absolute temperatures — conjugate CFD, listed as future work.

---

## R7 — Are these architectures actually manufacturable?

**Objection.** "The paper claims a repartition that drops the aspect ratio from 5.05 to
0.833. Is that manufacturable, are the microvia limits sourced, and is n_required a real
process constraint?"

**Why raised.** Realizability claims are easy to overstate.

**Severity: MODERATE.**

**Manuscript answer.** The licensed verdict is **geometrically realizable and
process-conditional**, and the paper states in terms that neither architecture is qualified.
Four specific inputs are named as unavailable: the microvia current allowable, the
capture-pad diameter, a vendor design rule and two package clearance rules. n_req is stated
to be a conservative design-side provisioning quantity at J_d and is *never* presented as a
manufacturing requirement. The pitch is bounded by reported practice with citations.

**Where.** §III-E, §VII-E, Table II footer, Table VII rows on manufacturability.

**Status: CLOSED.** **New science required: no** (process qualification is future work).

---

## R8 — The prior-work table puts words in other authors' mouths

**Objection.** "Table VIII lists positions and then reports them 'invalidated' or 'reversed'.
Did the cited works actually claim these things, or has the comparison invented straw men?"

**Why raised.** The most common reason a comparison table draws a hostile response.

**Manuscript answer.** Every row is labelled by its standing in the cited work: two are
**published results** stated explicitly there, three are **implications of the formulation**
that follow from how those flows are set up without being claimed, and one is a **modelling
assumption** the cited model makes. The caption defines the three categories. §VI-B states
that two of six are explicit and the remaining four are not claimed in those words. Only
works read in full text are scored; capability is not inferred from titles or abstracts; four
further works that could not be obtained are cited for motivation and left unscored. Table VII
additionally carries four rows *below a rule* marking capabilities the present framework does
**not** have.

**Severity: MODERATE. Status: CLOSED.** **New science required: no.**

**Residual risk.** "Invalidated for one ordering" is the strongest phrase in the table. It is
defensible because it is scoped to one ordering and the mechanism is shown, but a reviewer
may still prefer softer wording.

---

## R9 — Is the validation actually independent, and are failures being hidden?

**Objection.** "MOOSE is used as the independent reference, but the same authors built both
models. HFSS and Icepak appear nowhere in the results. Are failed validations being quietly
dropped?"

**Why raised.** Selective reporting of validation is a standard reviewer suspicion.

**Manuscript answer.** MOOSE is an external multiphysics code used only as a reference and
never in the production path, and the build hash is given. The two failures are reported in
the validation table itself, in their own rows below a rule, marked *not claimed*: conjugate
CFD "discarded" and full-wave "did not converge". The body repeats both in prose, including
that no number from the discarded CFD attempt appears in the paper. The frequency-dependence
claim rests on an analytic skin-depth model checked against a Bessel solution, not on the
failed full-wave run.

**Severity: MODERATE. Status: CLOSED** — failures are more prominently reported than is
typical. **New science required: no.**

---

## R10 — The computational cost claim is thin

**Objection.** "134–204 s is quoted with no speedup. Against what? And the timing breakdown
must be wrong, because a coupled ETM solve cannot put mechanics outside the loop."

**Why raised.** Cost claims without a baseline look unfalsifiable.

**Manuscript answer.** No speedup is claimed, and the reason is given: no controlled
same-geometry, same-machine timing pair against a higher-fidelity reference exists, and the
two commercial attempts produced no valid reference, so reporting one would not be
defensible. The decomposition follows the code rather than intuition and is verified by an
assertion in the test suite: each fixed-point iteration contains thermal FE work only, the
thermal solve is itself fluid-coupled at 3–4 sub-solves per iteration (11 total), and the
single thermoelastic solve runs *after* convergence — which is exactly the one-way T→M
coupling the paper declares. The local solder submodel is entered once more per architecture.

**Where.** §V-A, §V-E, Table VI, Fig. 8(f), `FINAL_TIMING_BREAKDOWN.md`.

**Status: CLOSED.** **New science required: no.**

---

## R11 — "Reliability Response" in the title is not supported by the paper

**Objection.** "The title promises reliability. The paper computes an inelastic strain
increment and explicitly refuses to convert it to damage, life or failure. The title
therefore overstates the contribution."

**Why raised.** Found by direct audit: the phrase **"reliability response" appears in the
title and nowhere else in the manuscript.** The word "reliability" occurs three times in
total — once in the title, and twice in the body meaning something different ("peak
temperature as a reliability ranking", "an insufficient reliability metric on its own"). A
term in the title that is never defined and is used elsewhere only to describe what the paper
argues *against* is a legitimate target.

**Severity: MAJOR** — this is the most actionable finding in this audit.

**Status: SUBMISSION BLOCKER (editorial, not technical).** Recommended fix in §Title below.

**Minimal action.** Change the title. **New science required: no.**

---

# Additional risks inspected (beyond the mandatory ten)

| # | risk | finding | action |
|---|---|---|---|
| a | Table VII too broad / overloaded | 27 rows × 7 columns at `\scriptsize`. Dense but legible at print size, and the rule separating "capabilities this work lacks" is the feature that makes it fair. | none |
| b | 25 references enough for TCPMT? | Thin but defensible: six frameworks scored from full text, four more cited for motivation and explicitly left unscored with the reason. A reviewer may ask for more packaging-side literature. | flag only |
| c | Comparison with the June-2026 framework precise enough? | Yes — scored row by row in Table VII and discussed in §VI-A, distinguishing what it does from what this work adds. | none |
| d | Abstract overemphasises 18.4 %? | The figure is attached to a named submodel and followed by "the ordering is robust; its magnitude remains conditional on an extrapolated solder constitutive model, and no absolute life is claimed." Acceptable. | none |
| e | "1 kW / 1000 A" sourced? | Specification-level, stated as such in Table I with the source column reading "specification". | none |
| f | 49 cells, 5.61 mm²/cell motivated? | Derived from the synthesis at J_t = 3.5 A mm⁻², shown in Table I with "synthesis" as the source and the search described in §III-A. | none |
| g | Cold-plate geometry aggressive? | 50 × 300 µm channels at 8.17 m s⁻¹ and 0.538 MPa is aggressive but stated in full in Table IV, and the pumping power is carried in a separate facility ledger. | none |
| h | Pump power in the main architecture table? | Already present in Table II as a distinct facility-scope row. | none |
| i | T_ref = 25 °C justified? | Stated as an operational stress-free reference, explicitly *not* an assembly signoff temperature. | none |
| j | Board/PCB properties sourced? | Given in Table III; FR4 values are conventional and the assembly-state study spans five explicit board constructions, so the conclusion does not rest on one property set. | none |
| k | Explicit-board assembly model described? | Yes — §IV-D gives the mesh treatment, the three-point kinematic restraint and the withdrawal of the earlier clamp model. | none |
| l | RDL/bump effective properties reproducible? | §IV-A gives the parallel rule, the stiffness-weighted expansion and the RVE route, with the Maxwell–Garnett comparison and why the element result is adopted for via arrays. | none |

---

# Title recommendation

Current:

> Electrothermal–Mechanical Co-Design of Distributed Vertical Power Delivery:
> Architecture-Dependent **Reliability Response** and Physical Realizability

"Reliability response" is undefined in the manuscript and the paper refuses reliability
claims. Three alternatives, best first:

1. **Architecture-Dependent Inelastic Response and Physical Realizability**
   — precise, matches exactly what is computed, minimal change.
2. Architecture-Dependent Local Solder Response and Physical Realizability
3. Architecture-Dependent Thermomechanical Response and Physical Realizability

**Recommendation: adopt 1.** It costs one word, removes the only unsupported claim in the
paper's most visible sentence, and is consistent with the terminology ladder the rest of the
manuscript maintains.

---

# Summary

| status | count | objections |
|---|---:|---|
| CLOSED | 7 | R3, R4, R5, R7, R8, R9, R10 |
| PARTIALLY CLOSED | 1 | R2 — refuted from above, bracket one-sided |
| OPEN BUT ACCEPTABLE LIMITATION | 2 | R1 constitutive extrapolation, R6 absolute temperatures |
| SUBMISSION BLOCKER | 1 | R11 — title, editorial |
| **total** | **11** | ten mandatory topics plus the title finding |

R5 is counted CLOSED because the objection bears on a claim the paper does not make: the
ordering is closed, and absolute efficiency is declared bounded rather than asserted.

No objection requires new science to be *answered*. Two (R1, R6) require new science to be
*closed*, and both are already declared future work.
