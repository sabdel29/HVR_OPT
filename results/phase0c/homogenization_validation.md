# H0 vs H1 — Validation of the TSV Homogenisation

**Question this answers.** Phase 0B found the homogenised TSV field carries ~36 % of the
reported die warpage, which promoted the homogenisation from a modelling detail to a
first-order scientific dependency. The decision-relevant question is **not** whether H0
predicts the exact absolute warpage — it is whether H0 preserves the *architectural
sensitivity and ordering* that the novelty claim rests on.

## 1. Method

Two independent checks, answering different questions.

### H1a — unit-cell numerical homogenisation (validates the CONSTANTS)

One 60 µm square-pitch cell containing a single explicit Cu via in a Si matrix. Mirror
symmetry on all four side faces is exact for a centred square array, so symmetry boundary
conditions are equivalent to periodic ones here; high faces are held planar by `*EQUATION`
constraints, which is what a periodic neighbour enforces. The via is modelled as an
**equal-area square** so a structured conforming mesh represents it exactly — this preserves
volume fraction and load path, and is a standard idealisation for effective-property
extraction. Effective E, ν, α and k are then measured numerically and compared against the
Voigt / stiffness-weighted-ROM / Maxwell-Garnett values that
`etm.config.derive_tsv_homog()` supplies to the package model.

Cu area fraction meshed = **0.196350**, analytic = 0.196350 (exact match).

### H1b — package-scale discrete-inclusion model (validates the ARCHITECTURAL SPREAD)

Explicitly meshing 26 667 vias at 60 µm pitch is computationally irrational. H1b instead
holds the Cu volume fraction **exactly** equal and coarsens the pitch until the inclusions
are explicitly meshable. This is a *scale-separation* test: if the homogenisation is valid
for global response, warpage and — far more importantly — the C05-vs-C07 architectural
spread must be insensitive to whether the same copper is smeared or resolved as discrete
blocks. Two discretisation levels were run (1.2 mm and 2.4 mm pitch) plus the smeared
reference, all at identical mesh settings.

Copper volume conservation: **0.0002 %** error against the smeared model.

## 2. H1a result — effective constants

| Property | analytic (used in H0) | numerical (unit cell) | error |
|---|---:|---:|---:|
| E | 126 073 MPa | 126 400 MPa | **+0.26 %** |
| ν | 0.2918 | 0.2930 | **+0.41 %** |
| k_xy | 158.90 W/mK | 159.63 W/mK | **+0.46 %** |
| k_z | 183.014 W/mK | 183.014 W/mK | **+6e-6 %** (Voigt is exact for parallel conduction) |
| **α (in-plane)** | **5.009e-6 /K** | **5.639e-6 /K** | **+12.59 %** |
| α (through-thickness) | 5.009e-6 /K | 5.226e-6 /K | +4.33 % |

**Finding.** Stiffness and conductivity are excellent. The **CTE is the weak constant**: the
stiffness-weighted rule of mixtures underestimates in-plane effective CTE by 12.6 %, because
it does not capture the transverse constraint the stiff Si matrix imposes on the expanding
Cu inclusion. CTE enters thermal strain linearly, so this is a systematic low bias on
everything the TSV field contributes.

## 3. H1b result — architectural spread

| representation | C05 (µm) | C07 (µm) | spread | abs. shift vs H0 | spread shift vs H0 |
|---|---:|---:|---:|---:|---:|
| **H0 smeared** (production model) | 7.7515 | 12.4548 | **60.67 %** | — | — |
| H1 discrete, 1.2 mm pitch | 8.1977 | 13.1512 | **60.43 %** | +5.76 % | **−0.25 pp** |
| H1 discrete, 2.4 mm pitch | 8.3743 | 13.3101 | **58.94 %** | +8.03 % | **−1.73 pp** |
| H0 with CTE bias corrected (×1.1259) | 8.4745 | 13.5524 | **59.92 %** | +9.33 % | **−0.76 pp** |

**The architectural spread is preserved to within 1.7 percentage points** across the smeared
model, two discrete-inclusion resolutions, and the CTE-corrected model. The absolute warpage
is biased **low by 6–9 %**, consistent in both sign and magnitude with the unit-cell CTE
finding.

## 4. Where H0 fails

| Quantity | H0 smeared | H1 discrete (1.2 mm) | H1 discrete (2.4 mm) |
|---|---:|---:|---:|
| die warpage | 7.75 µm | 8.20 µm (+5.8 %) | 8.37 µm (+8.0 %) |
| **Si σ₁ p99** | **10.34 MPa** | **18.83 MPa (+82 %)** | **20.37 MPa (+97 %)** |

Local silicon stress nearly **doubles** when the copper is resolved. This is expected and
physically correct: discrete inclusions create local stress concentrations at their edges
that a smeared block cannot represent by construction. It is also a direct confirmation of
the Phase-0B spec's warning that *local TSV/RDL stress cannot be claimed from a homogenised
block*.

## 5. Classification

> ## VALID WITH CORRECTION / BIAS — for global warpage and architectural screening
> ## INVALID — for local silicon or copper stress

**Valid for:** architectural screening on global warpage. The spread that carries the
Phase-0C conclusions moves by less than 1.7 pp under every representation tested, and the
C05 < C07 ordering never changes.

**Correction to apply:** absolute die warpage from the H0 model is **low by 6–9 %**. Two
independent routes give the same answer — the unit-cell CTE correction (+9.3 %) and the
discrete-inclusion models (+5.8 %, +8.0 %). Any absolute warpage quoted from the Phase-0B/0C
production model should carry this as a known systematic bias, not as random uncertainty.

**Invalid for:** local Si σ₁, TSV/Cu von Mises, and anything derived from them. Phase-0C
therefore makes no local-stress claim, and Si σ₁ is reported only as a secondary,
caveated quantity.

**What this does NOT establish:** per-via local fields at the true 30 µm geometry, liner
effects, or interface behaviour at the via scale. Those require the M1 explicit rung.
