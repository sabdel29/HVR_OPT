# Phase 0I-R Sec. 2 — What CalculiX's inelastic output variables actually are

## 1. Why this had to be done from first principles

Phase 0I justified its metric by quoting a CalculiX warning:

> `*WARNING reading *NODE/EL/CONTACT FILE: selection of CEEQ or CE or PE is converted into
> PEEQ; no distinction is made between PEEQ, CEEQ, CE and PE`

and inferred from it that "PEEQ aggregates plastic and creep". That inference does not follow
from the text. The warning says the output **request** is aliased — ask for CEEQ and you get
PEEQ — which is equally consistent with PEEQ being plastic-only and the creep request being
silently discarded. Phase 0I read a statement about request handling as a statement about
physical content.

The question is therefore settled here by experiment, not by reading.

## 2. The decisive experiments

Four single-element C3D8 probes, clean uniaxial (symmetry planes on x=0, y=0, z=0), in
`results/phase0ir/ccx_audit/`. In each the equivalent inelastic strain is computed
independently of the solver by decomposing the solver's own tensors:

```
eps_inelastic = eps_total - eps_elastic(Hooke, from the solver's stress) - eps_thermal
eq(e) = sqrt( 2/3 * e'_ij e'_ij )     on the deviatoric part
```

and compared against the solver's `PEEQ`.

| case | material | driving | PEEQ | eq(ε_inelastic) | **PEEQ / eq** |
|---|---|---|---|---|---|
| `u_creep` | elastic + **creep only, NO `*PLASTIC` card** | 10 MPa held 3000 s | 6.2510e−5 | 6.2510e−5 | **1.0000** |
| `d_plast` | elastic + **plastic only, NO `*CREEP`** | ramped displacement | 7.7348e−4 | 7.7348e−4 | **1.0000** |
| `d_both` | elastic + plastic + creep | ramped displacement | 4.2313e−5 | 4.2313e−5 | **1.0000** |
| `d_both_hold` | elastic + plastic + creep | displacement held 3000 s, stress relaxing 35.7 → 17.8 MPa | 5.0559e−4 | 5.0559e−4 | **1.0000** |

**The creep-only case is decisive.** With no `*PLASTIC` card in the deck at all, PEEQ is
non-zero and equals the equivalent creep strain to five figures. **PEEQ includes creep.**

## 3. Variable table

| solver variable | physical meaning | plastic included? | creep included? | tensor / scalar | signed / accumulated | used by Phase 0I? |
|---|---|---|---|---|---|---|
| **`PEEQ`** | equivalent **inelastic** strain, accumulated along the deformation path | **YES** | **YES** (verified above) | scalar | **accumulated**, monotone non-decreasing | **YES — the whole metric** |
| `CEEQ`, `CE`, `PE` | aliased by the solver to `PEEQ`; no separate field is produced | — | — | — | — | no |
| `S` | Cauchy stress, 6 components | n/a | n/a | tensor | signed | yes, for the audit decomposition |
| `E` | **total** strain, 6 components (elastic + thermal + inelastic) | included in the total | included in the total | tensor | signed, reversible | yes, for the audit decomposition |
| `ENER` | internal energy density | — | — | scalar | accumulated | no (Phase 0I did not use it) |
| `EVOL` | element volume | n/a | n/a | scalar | — | yes, for volume weighting |
| `NT` | nodal temperature | n/a | n/a | scalar | — | **not by Phase 0I** — see §4 |

## 4. A defect in this audit's own first attempt, and what it revealed

The decomposition initially returned **negative inelastic dissipation**, which is
thermodynamically impossible. The cause was in the audit, not the solver: **CalculiX ramps
`*TEMPERATURE` linearly across a step** unless `AMPLITUDE=STEP` is given, so reconstructing
the temperature analytically from the step schedule is wrong mid-step and corrupts the
thermal-strain subtraction. Reading the solver's own `NT` output fixed it, and the
volume-averaged inelastic work became positive in every case.

The same fix sharpened the identity check: with the true temperature history the ratio
PEEQ / eq(ε_inelastic) at the **first** output is 1.0035, 1.0033, 1.0029 for the three joint
material variants — the identity holds in the multiaxial, temperature-varying joint too, not
only in the single-element probes.

## 5. The one thing PEEQ is NOT

**PEEQ is a path length, not a state.** It accumulates monotonically and never decreases, so
under cyclic loading it diverges from the instantaneous equivalent inelastic strain, which
oscillates. In the Phase-0I joint the ratio PEEQ / eq(ε_inelastic) grows from 1.00 at the
first output to about 21 by the fourth cycle.

This matters because Phase 0I's metric is **not** PEEQ itself. It is

```
Δε_in(cycle k) = PEEQ(t_end of cycle k) − PEEQ(t_end of cycle k−1)
```

which is the **inelastic path length traversed during one cycle**. Differencing removes the
accumulation, so the metric is a legitimate per-cycle quantity and is not contaminated by
total accumulated creep. Sec. 7 of the closure report quantifies how it relates to a strain
*range*: at stabilisation the ratio is **3.72 (EP) / 3.72 (EPC)**, not the factor of 2 a
fully-reversed uniaxial cycle would give, because the OFF→ON→OFF cycle traverses a
multi-reversal path in strain space.

## 6. Conclusion

`PEEQ` is the **accumulated equivalent inelastic strain, plastic and creep together**. The
label Phase 0I used — Δε_in — is therefore *physically* correct in content. It is
*dimensionally* misleading in one respect: it is a per-cycle **accumulated path length**, not
a **range**, and the two differ by a factor of ~3.7 here. Sec. 4 of the closure report fixes
the naming.
