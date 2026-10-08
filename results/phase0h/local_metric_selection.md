# Phase 0H Sec. 7/8/9 — Global warpage is not the reliability quantity, and what replaces it

## 1. Sec. 7 — does global warpage predict the local loading?

Phase 0G reported mounted warpage below ~40 µm and stopped there. Sec. 7 forbids inferring a
large reliability margin from that, and requires an explicit test: **does global die/package
warpage correlate well enough with the local quantity to stand in for it?**

The test uses every paired observation Phase 0G produced — 70 runs spanning assembly model,
board case, substrate thickness, footprint, stress-free reference temperature and thermal
boundary — and correlates die warpage against the two computable local quantities.

| subset | n | local metric | local range | Pearson r | Spearman ρ | verdict |
|---|---|---|---|---|---|---|
| all cases | 70 | interface shear p99 (MPa) | 3.65 – 12.71 | 0.176 | 0.112 | **NOT A PROXY** |
| all cases | 70 | relative displacement (µm) | 0.048 – 0.161 | 0.674 | 0.680 | WEAK |
| mounted (BC_BOARD) | 42 | interface shear p99 | 5.48 – 12.71 | 0.430 | 0.349 | **NOT A PROXY** |
| mounted (BC_BOARD) | 42 | relative displacement | 0.050 – 0.161 | 0.623 | 0.738 | WEAK |
| free (BC_A) | 17 | interface shear p99 | 3.65 – 11.86 | **−0.726** | **−0.793** | WEAK, **and inverted** |
| free (BC_A) | 17 | relative displacement | 0.048 – 0.084 | 0.354 | −0.177 | **NOT A PROXY** |
| clamped (BC_B) | 11 | interface shear p99 | 5.61 – 10.14 | 0.128 | −0.022 | **NOT A PROXY** |

The mounted thickness sweep shows it most plainly: across the five board cases and three
thicknesses, **die warpage varies 3.0× (9.66 → 29.23 µm) while interface shear stays inside
7.04 – 8.45 MPa, a band of ±9 %.**

**Two findings, and the second is the serious one.**

1. **No subset reaches a usable correlation.** The best is ρ = 0.738 (mounted, relative
   displacement), which is a trend, not a surrogate.
2. **The sign is not even stable.** Warpage-versus-shear is ρ = −0.79 in the free package and
   +0.35 mounted. A design change that *increases* free warpage *decreases* the interface
   shear there. Using warpage as a reliability surrogate would not merely be imprecise; in the
   free configuration it would point the wrong way.

**Conclusion (Sec. 7): global warpage is an architectural RESPONSE METRIC and is not a
reliability quantity for this architecture.** Phase 0G's "below 40 µm" statement carries no
margin information, which is the second, independent reason the Sec. 18 retraction was needed.

Artifacts: `warpage_local_correlation.csv`, `warpage_local_pairs.csv`.

## 2. Sec. 8 — the two candidate local quantities

Sec. 3's map leaves very little to choose from: of eight failure mechanisms, one is computable
(A, global bending) and it is not a failure mechanism; one is partially computable (C,
microbump/C4 shear) on a smeared layer; the other six are outside the model.

The two candidates are therefore both from mechanism C:

### Candidate 1 — relative interface displacement `Δu`
* **Mechanism:** C, microbump/C4 shear.
* **What it is:** the maximum relative in-plane displacement imposed across the die-attach
  joint layer — the kinematic quantity a joint actually experiences.
* **Why it is a candidate:** it is a *displacement*, so it does not inherit the corner
  singularity that destroyed interface peel, and it is the natural input to any joint-level
  sub-model.
* **Against it:** the joint layer is homogenised, so `Δu` is the *imposed* deformation, not a
  joint strain. No allowable exists.

### Candidate 2 — smeared interface shear `τ₉₉`
* **Mechanism:** C.
* **What it is:** the p99 shear stress in the homogenised die-attach layer.
* **Why it is a candidate:** it passed mesh convergence in Phase 0C (8.70 % / 9.26 % at M3→M4,
  target < 10 %) where peel did not (19.2–20.1 %).
* **Against it:** a p99 over the whole layer samples the bimaterial free edge; it was
  previously found material-sensitive; and it is a smeared stress in a homogenised medium, so
  it is a *loading indicator*, not a joint stress. No allowable exists.

### Explicitly not selected
* **Interface peel** — excluded in Phase 0C for non-convergence at a corner singularity, and
  Sec. 10's rule forbids resurrecting it without revalidation. The convergent replacement is an
  energy release rate, which is not implemented.
* **Die principal stress `σ₁`** — homogenisation is invalid for local stress (+82 to +97 %
  bias, Phase 0B).
* **TSV region von Mises** — same homogenisation objection.
* **Global warpage** — Sec. 7 above.

Neither candidate was chosen because it produces a trade-off. Both were chosen because they are
the only quantities tied to a documented failure mechanism that this model can compute at all,
and both are reported with the reason they remain insufficient.

## 3. Sec. 9 — required fidelity, and the honest verdict on it

The criterion that the literature actually supports for mechanism B — accumulated **inelastic
strain-energy density per cycle** `ΔW` mapped to `N_f` — needs all of:

| requirement | present model |
|---|---|
| discrete solder joints | **NO** — the ball array is one homogenised elastic layer |
| temperature-dependent viscoplastic solder constitutive model (creep + plasticity) | **NO** — M0 is linear thermoelastic |
| defined thermal excursion / mission profile | **NO** — not published for the reference system |
| cycling to a stabilised hysteresis loop | **NO** — no cyclic capability |
| a calibrated `ΔW → N_f` life law for this alloy, joint scale and geometry | **NO** — the literature examined provides alloy comparisons and characteristic lives from accelerated cycling, not a transferable design allowable |

Every one of the five is missing, and the last two are missing **data**, not missing code.
Implementing viscoplastic solder and discrete joints would still leave the criterion untestable
because there is no mission profile and no transferable life law for this stack.

**Criterion status for mechanism B: NOT TESTABLE WITH PRESENT DATA.**

Sec. 9 instructs implementing only the minimum higher-fidelity model necessary to test a
criterion. Since no criterion for mechanism B is admissible even in principle here, **no
higher-fidelity mechanical model was built.** Building a viscoplastic discrete-joint model that
could not be compared against anything would add cost and no falsifiability.

## 4. What the two candidates are used for

They are **not** promoted to constraints. They are used exactly twice:

1. In Sec. 7, to demonstrate that global warpage does not predict local loading.
2. In Sec. 10, to establish whether either is numerically trustworthy in the mounted
   configuration — so that a future phase with a criterion knows which quantity it may use.

That is the whole of their role in Phase 0H.

## 5. Sec. 10 — validating the two candidates in the mounted configuration

Both candidates were previously characterised only in the free or clamped models. Phase 0G
withdrew BC-B, so they were revalidated on the explicit BGA + board assembly at
`h_sub = 1.50 mm`, FR-4 1.6 mm.

### Mesh convergence

| `h_xy` (mm) | elements | die warpage (µm) | τ₉₉ (MPa) | Δu (µm) |
|---|---|---|---|---|
| 0.95 | 20,203 | 17.9354 | 8.4557 | 0.09815 |
| 0.80 | 23,459 | 17.9288 | 8.6533 | 0.09475 |
| 0.70 | 32,075 | 17.9815 | 8.0420 | 0.09277 |
| 0.60 | 32,075 | 17.9842 | 8.2432 | 0.09164 |

| metric | final-step change | target | verdict |
|---|---|---|---|
| die warpage P-V | **+0.02 %** | < 10 % | CONVERGED |
| interface shear τ₉₉ | **+2.50 %** | < 10 % | CONVERGED |
| relative displacement Δu | **−1.22 %** | < 10 % | CONVERGED |

Two things are recorded rather than glossed:

* **`h_xy` = 0.70 and 0.60 produce the same element count (32,075) but different node
  distributions**, verified by rebuilding both meshes and comparing coordinates. They are
  genuinely different discretisations, not a repeated run, so the final step is a real
  refinement step. `h_xy = 0.50` was also built and gives 57,499 elements — beyond the 40,000
  ceiling this CalculiX build handles with the direct solver — so 0.60 is the finest usable
  mesh for the mounted model.
* **τ₉₉ is not monotone** (8.46 → 8.65 → 8.04 → 8.24, a 7.6 % spread) even though its final
  step is inside target. That is the signature of a p99 sampling the underfill free edge, which
  is a bimaterial corner. Δu is monotone throughout.

### Material-corner robustness

Seven corners at `h_xy = 0.70`, perturbing the two PROVISIONAL materials by ±25 %:

| metric | range | **spread, % of reference** |
|---|---|---|
| die warpage P-V | 17.6659 – 18.3848 µm | **4.00 %** |
| interface shear τ₉₉ | 7.3983 – 8.5359 MPa | **14.14 %** |
| relative displacement Δu | 0.08231 – 0.10691 µm | **26.52 %** |

The dominant sensitivity is the **underfill modulus**, which the stack itself flags
`PROVISIONAL ... UNSPECIFIED and HIGH-RISK`. Δu, the better-converged metric, is the *worse*
on material robustness — it moves 15 % for a 25 % change in a modulus nobody has sourced.

### Verdict on the two candidates

| | mesh convergence | material robustness | singularity | usable for decisions? |
|---|---|---|---|---|
| die warpage P-V | **0.02 %** | **4.00 %** | not applicable | numerically yes — **but Sec. 7 disqualifies it as a reliability quantity** |
| τ₉₉ | 2.50 %, **non-monotone** | 14.14 % | **samples a bimaterial corner** | no |
| Δu | 1.22 %, monotone | **26.52 %** | not singular | no |

**Neither local candidate is fit to carry decision weight**, and for different reasons: τ₉₉
oscillates because it samples a singular corner, and Δu inherits 26.5 % uncertainty from a
material the project has never sourced. The most numerically trustworthy quantity in the whole
model is global warpage — and Sec. 7 shows it is not a reliability quantity.

That is the closing shape of the mechanical side of this project: **the quantity that is
trustworthy is not meaningful for reliability, and the quantities that are meaningful are not
trustworthy.** Closing either gap requires data the project does not have — a sourced underfill
modulus for Δu, discrete joints and fracture mechanics for the rest.

Artifact: `local_metric_convergence.csv`.
