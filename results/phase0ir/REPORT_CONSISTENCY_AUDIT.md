# Phase 0I-R Sec. 18 — Report Consistency Audit (DEFECT #35)

Every current-facing statement in the full technical report, re-read against the Phase-0I
evidence rather than against the Phase-0H text it was written from. Eight items were specified
(A–H); all eight were confirmed present and all eight are repaired. Two further findings arose
during the audit and are recorded as I and J.

Every repair was made at `results/CURRENT_SCIENTIFIC_STATUS.yaml` and regenerated into the
report by `scripts/phase0g/generate_status_sections.py`, so no repaired sentence exists as
hand-edited prose that could drift from the source of truth.

---

## A. Executive Summary framed the answer as Phase 0H

**Was:** *"Phases 0G and 0H find..."* — the summary answered the programme's central question as
though Phase 0I had not added reliability physics.

**Now:** the finding is attributed through Phase 0I, and the sentence states what Phase 0I
actually added — vertical placement as a design variable, and a validated M2 reliability-physics
chain producing a resolved architecture-dependent damage response with no active constraint.

**Status: FIXED.**

## B. "of eight failure mechanisms only ONE is computable"

**Was:** literally the Phase-0H count. It ceased to be true when Phase 0I brought solder
fatigue into computability at M2.

**Now**, stated as a three-way split rather than a count:

| | status |
|---|---|
| global bending / warpage | available at **M0** (linear thermoelastic) |
| solder fatigue, cyclic inelastic response | available at **M2** (T-dependent elastic/plastic/Norton creep) |
| the remaining six mechanisms | **still open** — RDL fracture, delamination, via fatigue, dielectric cracking, pad cratering, EM-assisted damage |

The guard `only one mechanical failure mechanism modelled` now fails the build if the old
phrasing returns to a current-facing section. **Status: FIXED.**

## C. "Neither local metric is fit for decisions"

**Was:** true when written, and false by the time Phase 0I ended. It referred to the two
**rejected Phase-0H proxies** — interface peel/shear (mesh-divergent, 19–20 % over the final
refinement) and relative displacement — but read as a blanket statement about all local metrics,
including the new one.

**Now** the limitation distinguishes them explicitly:

> **The two Phase-0H proxies remain rejected** — interface peel does not converge and relative
> displacement is not a damage measure. **The Phase-0I M2 metric is different in kind and
> passes every numerical test applied to it:** mesh 1.90 % over the final refinement, creep
> tolerance 0.02 %, corner-exclusion band 6.4 % across 0–2 elements, and stabilisation to
> 0.48–2.00 % by cycle 4. What it still lacks is not numerical quality but a life law and a
> mission requirement.

**Status: FIXED.**

## D. "GaN and MLCC heights are open"

**Was:** a stale conjunction. GaN heights were sourced during Phase 0I (DEFECT #33 work:
HS 685 µm, LS 606 µm from the EPC product table).

**Now** split three ways:

| quantity | status |
|---|---|
| GaN device height | **SOURCE_BACKED** — 685 µm HS / 606 µm LS |
| MLCC height | **OPEN** — the 250 µm band in `h_sub >= 1.276 mm` |
| complete non-embedded package clearance | **OPEN** — backside clearance, die attach, cooler, lid, bump stack, handling |

The third row is the one that matters for the 0.300 mm claim, and it did not exist before this
audit. **Status: FIXED.**

## E. "Exact next work" recommended publication reframing

**Was:** the Phase-0H recommendation, written when no admissible mechanical criterion existed
and there was nothing further to compute.

**Now: PHASE 0J — LIFE-LAW AND MISSION ACQUISITION**, and the report says explicitly that this
next step was conditional on Phase-0I-R metric closure. The condition was tested, not assumed:
all five Sec. 24 conditions are recorded as met, and the YAML `next_gate.gated_on` field records
why. Had closure failed, the recommendation would have been metric repair, not Phase 0J.

**Status: FIXED.**

## F. Validation Status described the mechanics as M0 only

**Was:** *"M0 — no plasticity, creep or fatigue"*, describing a model that by then contained all
three at the joint scale. This is the item that made the report **understate its own
capability** — the opposite direction from every previous consistency defect in this programme.

**Now** split into two rungs that are separately labelled everywhere:

**GLOBAL M0** — linear thermoelastic package mechanics; temperature-independent properties; one
stress-free reference; no failure physics. Used for warpage and for driving the submodel.

**LOCAL M2** — temperature-dependent elastic/plastic/Norton-creep solder submodel, displacement-
driven from the global solution; Chaboche-sourced yield, measured-creep-fit Norton surrogate
valid 7.5–16 MPa; four thermal cycles to stabilisation.

**Status: FIXED.**

## G. Governing Equations stopped at M0 thermoelasticity

**Was:** the equation list ended at the linear thermoelastic constitutive relation, so a reader
could not reconstruct the damage number from the report.

**Now** four M2 entries are added:

1. **constitutive law** — additive decomposition ε = ε_el + ε_th + ε_pl + ε_cr, with
   σ_y(T) from Chaboche data and Norton ε̇ = A(T)·σⁿ⁽ᵀ⁾ fitted to 19 measured SAC305 points;
2. **damage-metric definition** — Δε_in(k) = PEEQ(t_k) − PEEQ(t_k−1), volume-averaged over the
   solder core with a one-element corner exclusion band, **with the explicit statement that this
   is an accumulated path length and not a strain range** (ratio 3.72);
3. **stabilised-cycle definition** — first cycle differing from its predecessor by < 5 %;
4. **`no_life_equation`** — an explicit negative entry recording that **no lifetime equation is
   current**, so the absence cannot be mistaken for an omission.

Item G's instruction *"do not imply a lifetime equation is current"* is enforced structurally by
that fourth entry plus the `relative life called parameter-free` guard. **Status: FIXED.**

## H. Method / phase count / roadmap

**Was:** eight gates.

**Now:** the roadmap runs through Phase 0I and Phase 0I-R, the gate count and phase list agree
with the verdict block, and Phase 0I is labelled **"(rescoped by Phase 0I-R)"** wherever it is
referenced as authoritative. **Status: FIXED.**

---

## I. Additional finding — the guard could not see the live section

Not in the specified list; found while verifying A–H.

The current-facing guards were scoped to a fixed list of section titles. The **live phase
narrative was not in it**, even though Phase 0I's section is headed *"(current authoritative)"*.
Three over-claims sat inside that section, unchecked, for the whole of Phase 0I:

- *"Z5 is eliminated"* — should be scoped to the tested low-voltage-lateral topology;
- *"1.9–3.8× relative life"* — an unsourced exponent presented as a result;
- *"Z1 keeps a 30 mW edge"* — a 0.14σ difference presented as a preference.

All three are corrected in `scripts/phase0i/build_report_0i.py`, and the guard scope now
includes `"current authoritative"`. **This was the same class of failure as DEFECT #31: a check
that had never been seen to fail because it could not reach the text it was written for.**

**Status: FIXED.**

## J. Additional finding — the report build was not idempotent

Splicing the new `reliability_metric` fragment anchored it on the `# Publication-Defensible
Claims` heading, which the `publication_claims` splice consumes — so a second build placed the
block differently from the first. Fixed by splicing `publication_claims` first and anchoring the
new block on its stable BEGIN sentinel. A repeat build now produces a byte-identical Markdown
source. **Status: FIXED.**

---

## Verification

All six Phase-0I-R semantic guards were negative-tested per Sec. 20: each deliberate violation
was injected into a current-facing section, the build was run, and each guard failed on its own
injection with the suite reporting `PDF VERIFICATION FAILED`. Correct content was restored and
the suite returns `PDF VERIFIED`.

| injected violation | guard that fired |
|---|---|
| "Relative life is parameter-free" | `current-facing: relative life called parameter-free` |
| "total inelastic … plastic-only and excludes creep" | `current-facing: total inelastic claimed without creep` |
| "2.5D is eliminated as an integration class" | `current-facing: 2.5D eliminated as a class` |
| "0.300 mm is fully manufacturable" | `current-facing: 0.300 mm called manufacturable` |
| "Z1 is electrically better than Z4" | `current-facing: Z1 claimed electrically preferred over Z4` |
| "only one of eight failure mechanisms is computable" | `current-facing: only one mechanical failure mechanism modelled` |

## Pattern across DEFECT #29, #32 and #35

The same failure in three directions, and worth stating because it predicts the next one:

- **#29 — stale withdrawal.** A claim was withdrawn; the current-facing text still asserted it.
- **#32 — stale scope.** A claim was narrowed; the current-facing text still stated it broadly.
- **#35 — stale capability.** A capability was *added*; the current-facing text still denied it.

The first two are the failures an honesty-focused review looks for. **The third is the one that
review misses**, because understating your own model never trips a scepticism check. A phase
that adds capability must audit the current-facing text exactly as carefully as a phase that
withdraws a claim.
