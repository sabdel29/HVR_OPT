# Phase 0G Sec. 12 — Search for a source-backed mechanical criterion, and the status of G2

## 1. Why this section exists

Phases 0C–0F repeatedly described the mechanical response as a "constraint". A constraint is
a statement that some design is **not allowed**. Nothing in this project has ever supplied a
threshold, so every such use was a description of a *response*, not of a constraint. Phase 0G
was required either to find a defensible criterion or to state plainly that none exists.

The admission standard applied here is the one set for this phase: a candidate limit is
usable only if its **package state, temperature, size, measurement definition and failure
mechanism** all match the system being analysed closely enough that exceeding it would mean
something. A number that is merely numerical is not a criterion.

## 2. What was searched

| source | status | mechanical criterion found |
|---|---|---|
| June-2026 DVPD framework (arXiv:2606.28837) | full text searched | **none numerical** — see §3 |
| ECTC-2024 RDL/packaging reference | full text searched | none |
| ISCAS-2024 reference | full text searched | none |
| STAMP-2.5D material tables | used for moduli/CTE | none — material data only |
| ATMPlace | used for placement | none |
| External standards (JEITA ED-7306, JESD22-B112, IPC-9641, JEDEC package outlines) | **not retrievable** | see §4 |

## 3. The reference system states a mechanical position, but not a limit

June-2026 makes an explicit and directly relevant *qualitative* mechanical claim (Sec. I):

> "Partitioning power conversion into multiple smaller VRs reduces peak stress concentration
> and prevents the formation of a single mechanically stiff region within the substrate. Each
> VR produces localized deformation rather than global package deflection. With symmetric VR
> placement localized mechanical effects can partially offset one another, reducing overall
> warpage sensitivity."

and identifies the failure mechanisms it cares about — "global package warpage, delamination
risk, and shear stress in the redistribution layer (RDL)". It attaches **no number** to any
of them: no allowable warpage, no allowable RDL shear, no delamination criterion, no
measurement definition, no temperature at which any limit would apply.

This is a *direction*, not a threshold. It cannot bound a feasible set. It is nonetheless
important evidence, and Sec. 14 treats it as such: the explicit-board model reproduces the
direction the reference paper asserts, while the free and clamped models contradict it.

## 4. External standards could not be retrieved, and are unlikely to help

Web retrieval is disabled in this environment, so no external standard was consulted, and
**no standard is cited here** — citing one from memory would be fabricating a reference.

Recording the limitation honestly also requires recording why closing it is unlikely to
change the answer. The relevant standards in this area (surface-mount package warpage
measurement at elevated temperature; package-outline coplanarity) define **measurement
methods and package-outline tolerances**. Coplanarity tolerances in package outlines are
tolerances on the *ball plane of a component as supplied*, at a defined measurement
temperature, for the purpose of assuring solderability at reflow. This project computes
**incremental operational warpage of a mounted assembly at steady-state operating
temperature, with a 25 °C stress-free reference** (Sec. 11). The package state differs, the
temperature differs, the measurement definition differs, and the failure mechanism differs —
solderability at reflow versus operational deformation. Under the admission standard set for
this phase, such a number would be **inadmissible even if retrieved**.

This is therefore not a gap that a single lookup closes. It requires a criterion defined for
the operational state, which the reference system does not publish.

## 5. Would any plausible criterion bind?

The question of whether a constraint is *active* can be partly answered without knowing the
threshold, by asking how large the computed response is.

| quantity | range across the entire Phase-0G design space | note |
|---|---|---|
| die warpage, free package | 1.27 – 11.17 µm | BC_A, h = 0.80–2.00 mm |
| die warpage, explicitly mounted | 9.66 – 29.23 µm | four board cases |
| die warpage, mounted, 175 °C reference | up to 38.71 µm | Sec. 11 M1 bound |
| package warpage, mounted | up to 37.08 µm | same runs |
| RDL interface shear, p99 | 5.02 – 9.97 MPa | all restraints |

Warpage stays **below 40 µm** everywhere, including the most pessimistic assembly and
reference-state combination examined. Package-level warpage tolerances for components of this
class are conventionally quoted in the **hundreds of micrometres**. The computed response is
one to two orders of magnitude below that band across the *whole* design space, which means
that even if an admissible criterion were supplied at a conventional magnitude, it would
**not discriminate between any two designs in this space** — it would be satisfied by all of
them, including the worst.

A criterion can only be *active* if it separates designs. Nothing in the computed range
suggests a conventional warpage limit would.

The one quantity that is not obviously far from engineering limits is **RDL interface shear
at 5–10 MPa**. Phase 0F qualified this metric and found it usable only in a restricted sense,
and interface **peel** was excluded outright in Phase 0C for failing mesh convergence
(19–20 % change M3→M4 against a <10 % target). Shear passed convergence (8.7 %/9.3 %) but no
allowable shear stress for this RDL stack exists in any source consulted, so it too cannot be
turned into a criterion.

## 6. Verdict

1. **No admissible mechanical criterion exists.** None is published by the reference system;
   none is derivable from the corpus; external standards are both unretrievable here and, on
   inspection of what they govern, inadmissible under this phase's matching requirement.
2. **Falsification gate G2 remains NOT TESTED.** It has been NOT TESTED since Phase 0B and
   Phase 0G does not change that. It is not "failed" — it has never been given a threshold to
   be tested against.
3. **The word "constraint" must not be used for the mechanical response** anywhere in this
   project's outputs. The defensible term is **response coupling**: thickness and footprint
   change warpage in a computable, sign-stable way, and that is the entire claim.
4. **No mechanical term may enter a feasibility test.** It may enter only as an objective
   component or as a user-set ε in a parametric sensitivity study, with ε declared as a
   *preference*, never as a physical limit (see `mechanical_epsilon_corrected.csv`).
5. Closing this gap requires an operational-state warpage or RDL-shear allowable for this
   specific stack — a measurement or a qualification specification, not a literature value.
   Until then, **the mechanical side of this project is a response model, not a constraint
   model**, and the ETM optimizer cannot be justified on the basis of a binding mechanical
   constraint.
