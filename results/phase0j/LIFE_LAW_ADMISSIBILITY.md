# Phase 0J Sec. 6 — Life-law admissibility gate

## Result

| classification | count |
|---|---|
| **ADMISSIBLE** | **0** |
| **CONDITIONALLY TRANSFERABLE** | **1** |
| **INADMISSIBLE** | **9** |

Ten candidates across all four families Sec. 4 requires. Full metadata in
`SAC305_LIFE_LAW_DATABASE.csv`; every field that could not be sourced is marked
`NOT_AVAILABLE` rather than filled in.

## The ten criteria, predeclared before the search concluded

1. alloy is SAC305 or demonstrably transferable to it
2. the mechanical input metric is reproducible by our solver
3. its metric definition is unambiguous
4. loading regime overlaps our temperature/stress regime sufficiently
5. joint/interconnect type is physically relevant
6. the law predicts a defined fatigue endpoint
7. calibration coefficients are actually available
8. dimensions/units can be reconciled
9. the source is experimental or experimentally calibrated
10. no undocumented conversion is necessary

## Candidate-by-candidate

| id | law | family | native metric | passed | verdict |
|---|---|---|---|---|---|
| L1 | Coffin-Manson | strain range | plastic strain range | 6/10 | INADMISSIBLE |
| L2 | Engelmaier (lead-free) | strain range | shear strain range, closed-form | 5/10 | INADMISSIBLE |
| L3 | Syed 2004, single mechanism | creep damage | accumulated creep strain/cycle | 5/10 | INADMISSIBLE |
| **L4** | **Syed 2004, two mechanisms** | **creep damage** | **accumulated creep strain/cycle** | **5/10** | **CONDITIONALLY TRANSFERABLE** |
| L5 | Syed 2004 energy | energy | creep strain energy density | 3/10 | INADMISSIBLE |
| L6 | Darveaux 2002 | energy | viscoplastic SED, 12.7 µm layer | 6/10 | INADMISSIBLE |
| L7 | Schubert 2003 strain | strain range | accumulated inelastic strain | 3/10 | INADMISSIBLE |
| L8 | Schubert 2003 energy | energy | inelastic SED | 3/10 | INADMISSIBLE |
| L9 | Hamasha variable-amplitude | energy | cyclic plastic work | 8/10 | INADMISSIBLE |
| L10 | Darveaux-form, PHM 2026 | energy | viscoplastic SED | 7/10 | INADMISSIBLE |

### Why each fails — the operative reason, not the count

**L1 Coffin-Manson.** No SAC305 `ε_f'` or `c` was obtainable from any retrieved source. Its
native metric is the **plastic** strain range; our M2 is **total inelastic**, and CalculiX
aliases `CEEQ`/`CE`/`PE` to `PEEQ` so the plastic part cannot be separated. Criteria 1, 2, 7, 10.

**L2 Engelmaier.** Two independent disqualifications. Its fatigue exponent is
`c = c0 + c1·T_sj + c2·ln(1 + 360/t_dwell)`; **our cycle has zero dwell, so the logarithm
diverges and the law is undefined** — not inaccurate, undefined. And `Δγ` is defined by a
closed-form distance-to-neutral-point expression, not by an FEA field, so its constants are
calibrated against a different quantity from anything we compute. Criteria 1, 2, 4, 7, 10.

**L3 / L4 / L5 Syed 2004.** This is the closest family: its native metric is **accumulated
creep strain per cycle**, which is the same *kind* of quantity as our M1 and is the reason M1
is worth having. Four blockers remain:

* the two-mechanism form needs `ε_acc` **partitioned between grain-boundary sliding and matrix
  creep by a double power law**. Our Norton card is a single power law and cannot produce that
  partition; the partition rule is in the primary, which is unretrievable;
* `ε_acc` in Syed's framework is the inelastic strain of a **unified viscoplastic** model, in
  which *all* inelastic strain is creep. Our model splits it into rate-independent plasticity
  plus Norton creep, so the correspondence is a modelling judgement, not an identity;
* the **averaging volume is not stated** in the accessible source — and Sec. 7 warns that an
  energy or strain constant calibrated against one averaging scheme does not transfer to
  another;
* the constants reach us **only through a review** (Yu et al. 2026). The primary is paywalled
  with no legal open-access copy (Unpaywall `is_oa=false`, Semantic Scholar `openAccessPdf=null`).

L4 is graded **CONDITIONALLY TRANSFERABLE** rather than inadmissible because it is the one
candidate with SnAgCu-specific numbers (`C_I = 0.013`, `C_II = 0.036`) and a form our metric can
feed. L3 and L5 are inadmissible outright for want of any constant.

**L6 Darveaux.** The most-used energy law in packaging, and the least transferable here. Its
`ΔW_ave` is **not** a whole-joint average: the method requires **three element layers each
0.0005 in (12.7 µm) thick at the pad interface**. Our M3 averages the whole solder core, and our
finest element is **37.5 µm — three times the required layer** — so the extraction cannot even
be reproduced at this mesh. The widely circulated `K1`–`K4` are for **eutectic SnPb**; no SAC305
set was obtainable. The retrieved IMAPS source states the penalty explicitly: relative
predictions ±25 %, and absolute predictions **"could be off by a factor of 7"** when the
modelling procedure is inconsistent with Darveaux's. Criteria 1, 2, 7, 10.

**L7 / L8 Schubert 2003.** Cited by eight of the retrieved sources; **not one reprints its
coefficients**. The primary is paywalled. Nothing to evaluate.

**L9 Hamasha.** Fully specified (`N_f = 7758.3·W^−1.036`) and SnAgCu — but calibrated for
**variable-amplitude mechanical vibration**, not thermal cycling. Sec. 4 forbids grouping laws
because they share the word "energy". Criterion 4 fails outright.

**L10 PHM 2026.** The best-documented candidate found: a Darveaux-form law calibrated on **20
devices** with primary constants (`K3 = 0.05321`, `K4 = 2.012`) and a stated crack length. It is
for **92.5Pb5Sn2.5Ag**, a high-lead **die-attach** solder. Rejected under the project's standing
no-alloy-mixing rule — the same rule that rejected SAC405 and SnAgCuCe Anand sets in Phase 0I.
Applying it would be exactly the error Sec. 40 forbids.

## Sec. 7 — constitutive/fatigue calibration mixing, audited

Our mechanics uses a **Norton surrogate fitted over 7.5–16 MPa**. The candidate laws were
calibrated with different constitutive models, and Sec. 7 requires asking whether each
correlation operates on a sufficiently model-independent quantity:

| law | calibration constitutive model | is its metric model-independent? |
|---|---|---|
| Coffin-Manson / Engelmaier | none (algebraic) or elastic-plastic | **No** — Engelmaier's Δγ is *defined* by its own closed-form expression |
| Syed 2004 | double power law / hyperbolic sine, **unified creep** | **Partly.** Accumulated inelastic strain per cycle is a physically measurable quantity, but its split into "creep" versus "plastic" is a model artefact, and Syed's model has no rate-independent plasticity to split off |
| Darveaux | Anand viscoplasticity + a fixed 12.7 µm extraction | **No** — the source itself says a consistent procedure is mandatory |

The general finding: **identical units do not imply identical meaning.** An energy density in
MJ/m³ averaged over a whole joint is not the same quantity as an energy density in MJ/m³
averaged over a 12.7 µm interface layer, and no dimensional check will reveal the difference.

## Consequence

With **zero admissible laws**, Sec. 9's model-form comparison cannot be run over admissible
laws, Sec. 8's reproduction cannot be attempted, and **no absolute lifetime is predicted
anywhere in this phase**. What Sec. 17–27 report instead is (a) the three native metrics for
every architecture, (b) the **relative** life implied by the conditional candidate, which is the
one quantity independent of the unvalidated constants, and (c) the parametric sweeps the brief
permits when a requirement is absent.
