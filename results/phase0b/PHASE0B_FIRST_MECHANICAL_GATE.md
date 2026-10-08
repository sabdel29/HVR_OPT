# Phase 0B — First Mechanical Gate

**Date:** 2026-09-02  **Fidelity rung:** M0 (operational thermoelastic only)
**Spec:** `NOVELTY_BOUNDARY_ETM_PHASE0B.md`  **Solver:** CalculiX 2.23, C3D8I, direct (SPOOLES)
**Cases solved:** C05, C07 (gate 1), C13 (gate 2) — 39 production runs + 4 convergence levels + 2 calibration iterations

---

## 1. Executive Verdict

# GATE PASSED — RESOLVED MECHANICAL SIGNAL

Architecture changes the mechanical response of this package by far more than the numerical
uncertainty, and the effect survives every material corner and both boundary-condition
families tested.

**The headline number.** Moving four identical VR tiles from a symmetric 2×2 distribution
(C05) to an asymmetric left-biased cluster (C07) — same tile size, same 96 mm² total
footprint, same 42 W total HVR heat, same 240 W die load, same mesh policy — changes die
peak-to-valley warpage by **+60.6 %** (7.772 → 12.481 µm) against a mesh-convergence
uncertainty of **0.50 %**. That is a 120× margin over numerical noise, it lands in the
spec's **STRONG materiality** band (≥25 %), and the ordering never flips across nine
material/model perturbations or across BC-A and BC-B.

**But the mechanism is not the one Phase 0A bet on, and this matters more than the pass.**
Decomposing the three cases separates two effects cleanly, because C05 and C13 differ only
in VR count while C05 and C07 differ only in placement:

| Effect isolated | Comparison | die warpage | pkg warpage | Si σ₁ p99 | T_max |
|---|---|---:|---:|---:|---:|
| **VR count** (4 → 6, both distributed, constant area & heat) | C05 → C13 | **0.02 %** | 0.80 % | 5.94 % | 4.21 % |
| **Placement asymmetry** (both N=4) | C05 → C07 | **60.59 %** | 29.95 % | 22.36 % | 4.79 % |

At constant total footprint and constant total heat, **VR count has no resolved mechanical
effect whatsoever** — 0.02 % on die warpage, three orders of magnitude below the placement
effect and well inside numerical noise. Everything mechanical in this experiment is driven by
**where the heat and stiffness sit**, not by how many pieces they are divided into.

**REVIEWER RISK — this is the central finding of Phase 0B.** "Mechanics responds to
placement" is precisely the territory STAMP-2.5D and ATMPlace already occupy. The Phase-0A
novelty argument rested on mechanics feeding back onto *power-delivery-specific* variables —
regulator count, cell sizing, per-layer area budget forcing switch resizing. The count
variable has now been measured, under a controlled experiment, and it does essentially
nothing mechanically. That does not sink the thesis, but it relocates it: the surviving
candidates are placement-coupled-to-assignment, tile aspect ratio, footprint (C11/C12), and
substrate thickness (C03/C08/C16/C18) — none of which have been run yet.

**Secondary findings.**
- **Only the warpage family is robustly resolved.** Interface shear (S=16.97 %) and peel
  (S=19.14 %) fall *below* twice their own mesh uncertainty (17.40 % and 38.47 %) and are
  **NOT resolved** at this fidelity.
- **BC-B collapses the magnitudes but preserves the die-warpage ordering.** Board-restrained
  support cuts die warpage from 7.8 µm to 0.52 µm and converts bending into interfacial
  shear (1.76 → 4.95 MPa). The C05 < C13 < C07 die-warpage ordering survives; most other
  orderings do not.
- **The homogenised TSV field is a first-order structural participant, not a detail.**
  Disabling it drops die warpage 36 % (7.75 → 4.99 µm) *and raises* Si σ₁ p99 54 %
  (10.3 → 15.9 MPa). Architecture-dependent Cu content is doing real mechanical work.

**No feasibility or reversal claim is made.** Mechanical allowables remain OPEN_DECISION and
the electrical objective has not been evaluated. Spec criteria **G1 (architecture reversal)**
and **G2 (feasible-set reversal)** are therefore **NOT YET TESTED**; only **G3 (robust
physical signal ≥15 % and >2u)** is satisfied. Under the spec's rule that GO requires
"at least one of G1/G2 **plus** G3", this gate delivers G3 and nothing more.

---

## 2. Repository / Implementation Audit

### 2.1 What existed before this phase

| Asset | Location | Status for this phase |
|---|---|---|
| Phase-0B specification | `NOVELTY_BOUNDARY_ETM_PHASE0B.md` (1599 lines) | authoritative input, read in full |
| Phase-0A novelty study | `NOVELTY_BOUNDARY_ETM.md` | context |
| HVR converter optimizer | `Scalable_Integrated_VR/src/HVR_FULL_OPT_EPC_V2.py :: run_hvr_optimization()` | **not used** — the controlled DOE deliberately fixes HVR heat at 42 W rather than taking compiler output |
| PDN routing model | `Scalable_Integrated_VR/src/Framework_w_HVR_OPT_sizing_v2.py :: DVPDRoutingModel` | not used at this rung (no electrical objective) |
| PyAEDT HFSS↔Mechanical harness | `tessera-master_2/revision/coupled_electrothermal_hfss_mechanical.py` (1456 lines) | **not usable** — see §2.3 |
| Homogenised-vs-explicit precedent | `tessera-master_2/FEM/HFSS_RUN_SINGLE_LINE_THERMAL_MECH_REGION_v2.py` (2091 lines) | methodological precedent only |
| Tests | none anywhere in the repository | no pre-existing tests were weakened or deleted |
| `tests/`, `configs/`, `scripts/`, `research/` | did not exist | created |

Confirming the Phase-0A audit: **no structural mechanics existed in either repository** —
`grep -riE "warpage|von_mises|static_structural|CTE"` over all Python returned zero hits.

### 2.2 What was added

```
configs/phase0b/package_stack.yaml        168 lines  stack + material cards, every value status-tagged
configs/phase0b/doe_cases.yaml             89 lines  C01-C20 frozen, execution gating declared
scripts/phase0b/etm/config.py                        config load, validation, TSV homogenisation, unit conversion
scripts/phase0b/etm/placement.py                     placement classes -> generated coordinates + hard validation
scripts/phase0b/etm/mesh.py                          graded structured hex mesher, conforming to every material edge
scripts/phase0b/etm/ccxio.py                         CalculiX deck generation, execution, .frd parsing
scripts/phase0b/etm/metrics.py                       metric extraction with singularity regularization
scripts/phase0b/etm/run_case.py                      end-to-end case + cooling calibration
scripts/phase0b/run_convergence.py                   mandatory mesh-convergence study
scripts/phase0b/run_gate.py                          gate cases + BC + material sensitivity
scripts/phase0b/analyze_gate.py                      materiality metric S_m, robustness, BC comparison
scripts/phase0b/make_previews.py                     placement preview for all 20 cases
scripts/phase0b/make_figure.py                       decisive figure
tests/phase0b/test_phase0b.py             29 tests
research/phase0b/MATERIAL_ASSUMPTIONS_LEDGER.md      human-readable provenance audit
```

**Test results: 29 passed, 0 failed, 0 skipped** (`pytest tests/phase0b/ -v`, 0.39 s).

Two tests failed on first write and both exposed real issues rather than test bugs:
`test_constant_footprint_across_count_sweep` (tile dimensions are specified to 4 dp, so
total areas agree only to ~1e-3 mm²) and `test_c05_c07_have_identical_discretisation` (a
conforming mesh necessarily produces different element counts when tiles move). Both were
corrected to assert the property that actually matters — identical *material volumes* and
identical through-thickness discretisation — rather than the property I first guessed at.

### 2.3 Execution environment — what could and could not run

**ANSYS was not usable.** Diagnosis, in order:

| Check | Result |
|---|---|
| `ansys.aedt.core` installed | yes, v1.1.0 |
| AEDT installed | yes, `/local/ansys/electronics/ansys_inc/v261/AnsysEM` |
| MAPDL / Workbench installed | **no** — `/local/ansys/ansys_inc/v251/` contains only installer and commonfiles |
| License config | `SERVER=1055@pinback.xray.aps.anl.gov` |
| Current host | `pinback.xray.aps.anl.gov` — we are ON the license server |
| Port 1055 | **connection refused** |
| `lmgrd` / `ansysli_server` process | **not running** |
| License file readable | **no** — owned by another user, permission denied |

**This is an environment blocker, not a scientific result.** To use ANSYS instead, the
license manager must be started on pinback:

```bash
/local/ansys/ansys_inc/shared_files/licensing/linx64/lmgrd \
    -c /local/ansys/Ansys_License.pinback.xray.aps.anl.gov.40a6b7a32d60.txt \
    -l /local/ansys/licserv.log
# then verify:
/local/ansys/ansys_inc/shared_files/licensing/linx64/lmutil lmstat -c 1055@localhost
```
Both the license file and the daemon are owned by another user, so this needs that user or
root. Note also that even with a license, only **AEDT Mechanical** is installed — narrower
structurally than the Workbench/MAPDL product STAMP-2.5D used.

**What was used instead.** CalculiX 2.23, which the spec explicitly names as a credible
open-source fallback for "static, heat-transfer and coupled/uncoupled temperature-displacement
analyses". Installed into a dedicated environment at `/home/beams0/MGHARIB/envs/etm`
(not the borrowed `AMICELI` interpreter Phase 0A flagged). Verified against an analytic
case before use: single-element free thermal expansion reproduced α·ΔT = 16.66e-6 × 100 K =
1.666e-3 mm exactly.

**PUBLICATION CRITICAL:** every number in this report is CalculiX. The spec's preferred
validation path is "fast reduced model → ANSYS high-fidelity signoff", and that signoff has
**not** been performed. Nothing here should be quoted as ANSYS-verified.

---

## 3. Frozen Phase-0B Model

### 3.1 Geometry (all coordinates: die centre at origin, z = 0 at substrate underside)

| Layer (bottom → top) | Footprint | Thickness | Material |
|---|---|---:|---|
| *(BC-B only)* compliant support | 30 × 30 mm | 400 µm | `support_foundation` |
| power substrate, lower | 30 × 30 mm | h_sub − 150 µm | silicon, or `tsv_homog` under tiles |
| HVR tile band | 30 × 30 mm | 150 µm | silicon, or `hvr_effective` in tiles |
| interface (µbump + underfill) | 22.36 × 22.36 mm | 10 µm | `underfill_homog` |
| functional die | 22.36 × 22.36 mm | 300 µm | silicon (cubic) |
| TIM | 22.36 × 22.36 mm | 50 µm | `tim` |

Die footprint 22.36² = 500.0 mm² exactly — the June-2026 reference. HVR tile thickness
(150 µm) is **PROVISIONAL**: it appears nowhere in the spec, and is held constant while
h_sub varies so the thickness sweep is not confounded by tile volume.

### 3.2 Materials

Silicon uses the **cubic elastic tensor** (C11/C12/C44 = 166/64/79.6 GPa), not an isotropic
approximation. The TSV field is homogenised by a documented formula rather than a guessed
number: Cu area fraction f = πd²/(4p²) = **0.19635** from the SOURCE_BACKED 30 µm/60 µm
geometry, giving E = 126.1 GPa, CTE = 5.01 ppm/K, k_xy = 158.9, k_z = 183.0 W/mK
(Voigt for z, Maxwell-Garnett in-plane; `etm.config.derive_tsv_homog`, bounds-tested).

Full provenance in `research/phase0b/MATERIAL_ASSUMPTIONS_LEDGER.md`. The high-risk
PROVISIONAL entries — underfill E/CTE, HVR-tile effective E/CTE, TIM CTE (OPEN_DECISION) —
are exactly the ones swept in §5.

### 3.3 Thermal boundary conditions — calibrated, not chosen

The spec forbids picking h because it looks reasonable. h_top was secant-solved so the
reference architecture reaches the June-2026 cooled baseline junction temperature:

| iteration | h_top (W/m²K) | T_max (°C) | residual (K) |
|---:|---:|---:|---:|
| 0 (1-D seed) | 14 339.9 | 91.143 | +7.143 |
| 1 | **17 521.6** | **83.514** | **−0.486** |

Converged in one secant step to within 0.5 K, then **FROZEN for the entire DOE**
(`results/phase0b/cooling_calibration.json`). h_bottom = 10 W/m²K, sides adiabatic,
coolant/ambient 25 °C.

**Deliberate methodological choice, recorded as such:** the Phase-0B load (282 W over
500 mm²) is ≈4.3× below June's 1 kW case. Calibrating to June's *hardware* would leave this
vehicle near 39 °C and would test mechanics at an unrepresentatively small ΔT — biasing the
experiment toward a false NO-GO. The calibration therefore targets a representative
*operating temperature*, which is what thermal strain actually depends on.

### 3.4 Structural boundary conditions

- **BC-A (primary):** 3-2-1 rigid-body suppression on the substrate underside; exactly 6 DOF
  removed; package otherwise free to warp.
- **BC-B:** explicit compliant support layer (E = 400 MPa, t = 400 µm → k_z ≈ 1000 N/mm³)
  with its underside fully restrained. Implemented with solid elements, not discrete springs.

**ASSUMPTION:** T_ref = 25 °C, operational-only. **OPEN_DECISION:** T_cure/attach — the M1
rung is not attempted and no total-package-stress claim is made.

---

## 4. C05 / C07 Results

All at BC-A on the converged production mesh (M4-equivalent, 33.8–37.5 k elements).

| Metric | C05 (4 distributed) | C07 (4 asymmetric) | Δ | mesh 1u |
|---|---:|---:|---:|---:|
| T_max (°C) | 83.234 | 87.218 | **+4.79 %** | 0.29 % |
| die-top thermal span (K) | 13.61 | 19.61 | +44 % | — |
| **die warpage p-v (µm)** | **7.772** | **12.481** | **+60.59 %** | **0.50 %** |
| package warpage p-v (µm) | 12.175 | 15.821 | +29.95 % | 0.40 % |
| Si σ₁ p99 (MPa) | 11.007 | 13.467 | +22.36 % | 4.43 % |
| TSV-region σ_vm p99 (MPa) | 16.123 | 17.795 | +10.37 % | 5.66 % |
| interface shear p99 (MPa) | 1.695 | 2.005 | +18.29 % | 8.70 % |
| interface peel p99 (MPa) | 1.570 | 1.889 | +20.32 % | 19.24 % |
| **energy-balance residual** | **−0.000 %** | **−0.000 %** | — | — |

The warpage *mode* changes, not just the magnitude: C05 produces a symmetric bowl; C07
produces a bowl displaced toward the loaded half (see the decisive figure, row 3). This is a
qualitative change in deformation shape, not a scaling.

**Is the difference larger than the numerical/model uncertainty? Yes, decisively, for
warpage.** Die warpage: 60.6 % against 0.50 % mesh uncertainty. Classification per the spec's
bands: **RESOLVED MECHANICAL SIGNAL, STRONG materiality**.

For interface metrics the honest answer is **no**: S = 16.97 % (shear) and 19.14 % (peel)
against 2u = 17.40 % and 38.47 %. Those are **NOT RESOLVED** and are reported as such.

---

## 5. Convergence and Numerical Uncertainty

### 5.1 Mesh convergence (C05, BC-A, graded meshes, four levels)

| level | elements | T_max (°C) | die warp (µm) | pkg warp (µm) | Si σ₁ p99 | Si σ₁ raw | iface shear p99 | E-balance |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| M1 | 9 121 | 81.698 | 7.7544 | 12.1384 | 9.975 | 12.026 | 1.616 | −0.000 % |
| M2 | 17 579 | 82.855 | 7.7515 | 12.1412 | 10.335 | 13.433 | 1.762 | +0.000 % |
| M3 | 22 981 | 83.474 | 7.7331 | 12.1264 | 10.519 | 14.306 | 1.843 | +0.000 % |
| M4 | 37 535 | 83.234 | 7.7720 | 12.1752 | 11.007 | 15.038 | 1.695 | −0.000 % |

**Final-step changes (M3 → M4) against the spec's acceptance targets:**

| Quantity | change | target | verdict |
|---|---:|---:|---|
| die warpage | 0.50 % | < 5 % | **PASS** |
| package warpage | 0.40 % | < 5 % | **PASS** |
| Si σ₁ **p99** (regularized) | 4.43 % | < 10 % | **PASS** |
| interface shear p99 | 8.70 % | < 10 % | PASS (marginal) |
| interface peel p99 | 19.24 % | < 10 % | **FAIL — not converged** |
| T_max | 0.29 % | — | PASS |

Interface peel is **not mesh-converged** and its Phase-0B values must not be used
quantitatively.

### 5.2 Singularity handling

The spec forbids reporting an unconverged singular maximum. Raw nodal maxima are tracked for
diagnosis only; every headline stress is the **99th percentile over the material region**,
evaluated on nodes *interior* to that material so interface averaging cannot contaminate a
bulk metric.

| Region | raw_max | p99 | p95 | raw/p99 | behaviour under refinement |
|---|---:|---:|---:|---:|---|
| Si σ₁ | 13.433 | 10.335 | 8.261 | 1.30 | raw grows 10.5 → 6.1 → 4.9 %; p99 grows 3.5 → 1.7 → 4.4 % |
| TSV-region σ_vm | 14.226 | 14.226 | 12.775 | 1.00 | — |
| interface shear | 1.784 | 1.762 | 1.316 | 1.01 | — |
| interface peel | 3.782 | 2.111 | 0.633 | 1.79 | strongly localized |

The Si raw maximum diverges faster than the p99 under refinement — the signature of a corner
singularity — which is exactly why the p99 is the reported quantity.

### 5.3 Structural verification

Reaction forces at the three BC-A anchor nodes: **|F| ≤ 4.3e-10 N**, sum
(1.6e-10, 2.8e-10, 6.4e-10) N. Thermal loading is self-equilibrated and the 3-2-1 constraint
introduces no artificial force — direct evidence that the support is not manufacturing stress.

### 5.4 Solver validation (and a rejected shortcut)

CalculiX's **ITERATIVE CHOLESKY** solver was measured against the direct solver on an
identical M2 model:

| quantity | direct (SPOOLES) | ITERATIVE CHOLESKY | difference |
|---|---:|---:|---:|
| die warpage | 7.763 µm | 6.819 µm | **12.2 %** |
| **package warpage** | **12.155 µm** | **7.859 µm** | **35.3 %** |
| Si σ₁ p99 | 9.530 MPa | 9.194 MPa | 3.5 % |

The iterative solver is **unusable for a warpage study** and was rejected. Because C3D8I with
the direct solver segfaults above ~40 k elements in this build (verified: 37.5 k solves,
48 k and 63.5 k crash), the mesh is **graded** — fine at every tile/die/package edge,
coarsening into the far field — and a hard guard refuses to run above 40 k elements rather
than silently falling back. Plain C3D8 survives at any size but shear-locks in bending and
was therefore not used.

---

## 6. Boundary-Condition Sensitivity

Matched pair, both BC families at the SENS mesh (BC-B's support layer exceeds the element
ceiling at production density, so running both at SENS keeps the comparison like-for-like).

| Metric | S(BC-A) | S(BC-B) | ordering | C05 → C07 → C13 under BC-A | under BC-B |
|---|---:|---:|---|---|---|
| T_max (°C) | 7.65 % | 8.35 % | **preserved** | 82.86 / 87.02 / 80.68 | 78.47 / 83.25 / 76.69 |
| **die warpage** | **60.17 %** | **17.68 %** | **preserved** | 7.75 / 12.45 / 7.82 | 0.52 / 0.61 / 0.53 |
| package warpage | 30.25 % | 33.94 % | changed | 12.14 / 15.79 / 12.11 | 0.55 / 0.74 / 0.57 |
| Si σ₁ p99 | 33.11 % | 8.49 % | changed | 10.34 / 13.20 / 9.78 | 4.90 / 4.49 / 4.86 |
| TSV σ_vm p99 | 24.88 % | 7.78 % | preserved | 14.23 / 15.91 / 12.37 | 66.63 / 70.04 / 64.86 |
| interface shear p99 | 10.99 % | 2.19 % | changed | 1.76 / 1.93 / 1.73 | 4.95 / 4.97 / 5.06 |
| interface peel p99 | 65.51 % | 3.54 % | changed | 2.11 / 3.23 / 1.85 | 6.81 / 6.87 / 7.06 |

**The support model changes the physics qualitatively.** Restraining the board suppresses
global bowing by ~15× and converts that bending into interfacial shear (1.76 → 4.95 MPa) and
a 4.7× rise in TSV-region von Mises. Under BC-B, architecture barely differentiates the
interface metrics at all (S = 2–4 %).

**Only die warpage keeps both a resolved spread and a stable ordering across both BC
families.** Every claim in this report is therefore restricted to die warpage plus, weakly,
T_max.

**REVIEWER RISK:** BC-B as implemented (fully restrained underside beneath a 400 MPa layer)
sits nearer the spec's restrictive "BC-C assembly-mounted envelope" than a genuinely
compliant BGA foundation, and its stiffness is **PROVISIONAL** — the spec requires calibration
from a BGA unit cell or board data, which has not been done. BC-A and BC-B should be read as
*bracketing* the real support, not as the real support.

---

## 7. C13 Results

C13 (6 VRs, distributed 3×2, 4.00 × 4.00 mm tiles) was run only after C05/C07 passed
convergence and energy balance, on the identical pipeline.

| Metric | C05 (N=4) | C13 (N=6) | Δ | mesh 1u | resolved? |
|---|---:|---:|---:|---:|---|
| T_max (°C) | 83.234 | 79.732 | −4.21 % | 0.29 % | yes |
| die-top thermal span (K) | 13.61 | 10.06 | −26 % | — | yes |
| **die warpage (µm)** | **7.772** | **7.774** | **+0.02 %** | 0.50 % | **no** |
| package warpage (µm) | 12.175 | 12.078 | −0.80 % | 0.40 % | marginal |
| Si σ₁ p99 (MPa) | 11.007 | 10.352 | −5.94 % | 4.43 % | marginal |
| interface shear p99 (MPa) | 1.695 | 1.828 | +7.85 % | 8.70 % | no |

Finer distribution at constant total area and heat is **thermally useful and mechanically
inert**: it flattens the temperature field (span 13.6 → 10.1 K, T_max −3.5 K) while leaving
die warpage unchanged to within 0.02 %.

That is physically coherent. Global curvature is set by the first moment of the CTE-mismatched
inclusion field about the neutral axis; subdividing the same total inclusion area into more,
smaller, still-symmetric pieces leaves that moment essentially unchanged. Breaking the
symmetry, as C07 does, changes it a great deal.

---

## 8. Three-Case Materiality Comparison

BC-A, converged production mesh. S_m = (max − min)/median per the spec.

| Metric | C05 | C07 | C13 | range | S_m | 2u_mesh | resolved | band |
|---|---:|---:|---:|---:|---:|---:|---|---|
| T_max (°C) | 83.234 | 87.218 | 79.732 | 7.486 | 8.99 % | 0.58 % | **yes** | below-band |
| **die warpage (µm)** | 7.772 | 12.481 | 7.774 | 4.709 | **60.57 %** | 1.00 % | **yes** | **STRONG** |
| package warpage (µm) | 12.175 | 15.821 | 12.078 | 3.743 | 30.74 % | 0.80 % | **yes** | **STRONG** |
| Si σ₁ p99 (MPa) | 11.007 | 13.467 | 10.352 | 3.115 | 28.30 % | 8.86 % | **yes** | **STRONG** |
| TSV σ_vm p99 (MPa) | 16.123 | 17.795 | 14.423 | 3.372 | 20.91 % | 11.31 % | yes | MODERATE |
| interface shear p99 (MPa) | 1.695 | 2.005 | 1.828 | 0.310 | 16.97 % | 17.40 % | **no** | moderate |
| interface peel p99 (MPa) | 1.570 | 1.889 | 1.665 | 0.319 | 19.14 % | 38.47 % | **no** | moderate |

### 8.1 Does the spread survive the material corners?

A material perturbation is a *systematic* uncertainty: it moves every architecture the same
way. Folding its full magnitude into u_m as if it were noise on the *difference* would be
wrong — absolute warpage here is far more sensitive to an unknown tile CTE (4.26 → 14.74 µm
across 4–10 ppm/K) than to placement. So every perturbation was applied to **every** case and
S_m recomputed under it:

| Metric | S_ref | S_min | S_max | worst corner | ordering stable | verdict |
|---|---:|---:|---:|---|---|---|
| T_max | 7.65 % | 7.58 % | 7.65 % | tsv_off | yes | RESOLVED |
| **die warpage** | **60.17 %** | **55.76 %** | **67.73 %** | hvr_cte_hi | **yes** | **RESOLVED** |
| package warpage | 30.25 % | 27.31 % | 36.01 % | hvr_cte_hi | **no** | ORDER FLIPS |
| Si σ₁ p99 | 33.11 % | 15.39 % | 38.00 % | tsv_off | **no** | ORDER FLIPS |
| TSV σ_vm p99 | 24.88 % | 6.39 % | 30.05 % | hvr_cte_lo | yes | NOT RESOLVED |
| interface shear p99 | 10.99 % | 10.79 % | 26.36 % | uf_cte_hi | **no** | ORDER FLIPS |
| interface peel p99 | 65.51 % | 17.64 % | 100.38 % | hvr_cte_lo | yes | NOT RESOLVED |

Perturbations: underfill E ±30 %, underfill CTE ±30 %, HVR-tile E 80–160 GPa, HVR-tile CTE
4–10 ppm/K, TSV field on/off (nine corners × three cases × two reference runs).

**Exactly one metric survives everything: die warpage.** Its spread never drops below 55.8 %
and the C05 ≈ C13 < C07 ordering never flips, under any material corner or either BC family.

Per the spec's INCONCLUSIVE rule, package warpage, Si σ₁ and both interface metrics — whose
ordering flips under a modest underfill or HVR-tile perturbation — must be reported as
**INCONCLUSIVE**, not as evidence.

---

## 9. Reviewer-Risk Audit

| Risk | Status | Evidence / mitigation |
|---|---|---|
| **Arbitrary supports manufacturing stress** | **Closed for BC-A** | 3-2-1 removes exactly 6 DOF; reaction forces ≤ 4.3e-10 N. BC-B stiffness is PROVISIONAL and uncalibrated — **open**. |
| **Guessed underfill properties** | **Open, but bounded** | E and CTE swept ±30 %. Die-warpage spread moves only 60.17 → 55.8–67.7 % and ordering holds; but interface-shear *ordering flips* under uf_cte_hi, so interface claims are withheld. |
| **Stress singularities** | **Closed** | p99/p95 regularization on material-interior nodes; raw maxima reported separately; Si raw/p99 = 1.30 and the raw value diverges faster under refinement, which is why it is not the headline. |
| **Fake homogenised HVR material** | **Open — the dominant uncertainty** | `hvr_effective` is entirely PROVISIONAL. CTE 4→10 ppm/K moves die warpage 4.26→14.74 µm (3.5×). Absolute magnitudes are therefore not trustworthy; only the *relative* architectural spread is, and that was explicitly re-tested under every corner. |
| **Unconverged mesh** | **Closed for warpage and Si p99; open for interface peel** | Four levels; die 0.50 %, pkg 0.40 %, Si p99 4.43 % — all inside target. Interface peel 19.24 % — **fails**, values withheld. |
| **Heat mismatch** | **Closed** | Energy-balance residual **−0.000 %** on every run, computed independently by integrating the Robin flux over both cooled surfaces. Mesh volumes verified against analytic values by unit test. |
| **Temperature-gradient-as-stress** | **Closed by construction** | Full thermoelastic solve, σ = C:(ε − αΔT), temperature entering only as a load. No gradient proxy anywhere in the code. |
| **Solver credibility** | **Partly open** | CalculiX validated against analytic free expansion; iterative solver measured and rejected. **No ANSYS cross-check performed** (license blocker) — required before publication. |
| **TSV homogenisation unvalidated** | **Open** | `tsv_homog` uses a documented, bounds-tested formula, but the spec's H0-vs-H1 explicit-geometry cross-check has **not** been run. The TSV field is a first-order participant (36 % of die warpage), so this validation is now higher priority than it looked. |
| **Cherry-picked cooling** | **Closed** | h_top calibrated by secant to a stated target, residual −0.49 K, frozen for the DOE, full iteration history archived. |
| **BC-B not a real BGA** | **Open** | Acknowledged in §6; k_z uncalibrated. |

---

## 10. What We Can Conclude

**PROVEN** (measured, converged, robust to every perturbation tested)
- Placement asymmetry at constant VR count, footprint and heat changes die peak-to-valley
  warpage by 55.8–67.7 % depending on material corner, against 0.50 % mesh uncertainty, with
  stable ordering across nine material corners and both BC families.
- VR count (4 → 6) at constant footprint and heat changes die warpage by 0.02 % — no resolved
  mechanical effect.
- The thermal-structural chain is numerically sound: energy balance closes to −0.000 %,
  reactions vanish to 1e-10 N, warpage is mesh-converged to 0.5 %.

**SUPPORTED** (measured and resolved, but with a caveat)
- Placement asymmetry raises T_max by 4.8 % and the die thermal span by 44 %.
- Finer distribution (N=6) lowers T_max by 4.2 % and flattens the thermal span by 26 %.
- Si σ₁ p99 spread of 28.3 % across architectures — resolved against mesh uncertainty, but the
  ordering flips when the TSV field is removed.
- The homogenised TSV field contributes ~36 % of die warpage and −54 % of Si σ₁.

**PROVISIONAL** (magnitude depends on an unsourced input)
- All absolute warpage and stress values, because `hvr_effective` CTE alone moves die warpage
  by 3.5×.
- All BC-B magnitudes (uncalibrated foundation stiffness).

**OPEN**
- Mechanical allowables (σ_allow, w_allow) — deliberately not chosen, so no feasibility claim.
- T_cure / assembly history — M1 rung not attempted.
- TIM CTE.
- ANSYS cross-validation.
- Explicit-geometry validation of the TSV and HVR-tile homogenisations.

**NOT YET TESTED**
- G1 architecture reversal and G2 feasible-set reversal — both need an electrical objective
  and credible allowables. **The spec's GO condition is not met by this gate alone.**
- Substrate thickness (C03, C08, C16, C18) — the h_sub three-domain coupling test, which is
  now among the most promising remaining candidates.
- Aspect ratio (C09, C10) and footprint (C11, C12).
- HVR heat sensitivity at the architecture level (C19, C20).
- Electrically coupled replay with real HVR loss.
- Transient response.

---

## 11. Exact Next Gate

**Not started. Recommendation below; no work has been initiated on it.**

**Proceed to the full C01–C20 controlled sweep — but reorder it.** The M0 model is validated
well enough (converged warpage, closed energy balance, verified reactions, rejected bad
solver) and each case costs 60–80 s, so the whole matrix is roughly 30 minutes of compute.
There is no fidelity work that must precede it.

The reordering matters because the count variable is now known to be mechanically inert. The
sweep should lead with the cases that probe what is still live:

1. **C03 / C08 / C16 / C18 — substrate thickness.** The only remaining variable the spec
   identifies as genuinely three-domain coupled, and the one Phase-0A named as most promising.
2. **C09 / C10 — aspect ratio; C11 / C12 — footprint.** Both change the inclusion's second
   moment without changing count; the C05/C13 result predicts these should matter more than
   count did.
3. **C02 / C06 / C14 / C15 / C17 / C18 — placement family.** Fills in the placement
   response surface, which is the one effect already proven resolved.
4. **C19 / C20 — HVR heat.** Confirms whether materiality depends on converter loss.
5. **C01 / C04 — remaining count/compactness controls.**

**Three fidelity items should run alongside, not before:**
- **H0-vs-H1 homogenisation check** on the TSV and HVR-tile blocks, at one central and one
  asymmetric location. This has been promoted from routine to important: the TSV field turned
  out to carry 36 % of the warpage, so a homogenisation error propagates directly into the
  headline number.
- **BC-B recalibration** from an explicit BGA unit cell, replacing the PROVISIONAL stiffness.
- **Interface-peel mesh refinement**, which failed its convergence target.

**Before any GO decision:** the spec requires G1 or G2 in addition to G3, and neither is
testable without (a) the electrically coupled HVR loss replay and (b) defensible
material-specific allowables. Both remain out of scope until the sweep is complete.

**One honest strategic note for the novelty argument.** This gate confirms mechanics responds
strongly to *placement* — which STAMP-2.5D and ATMPlace already do for chiplets — and shows no
response to *VR count*, which was the DVPD-specific variable the Phase-0A thesis leaned on. If
the thickness, aspect-ratio and footprint cases also come back inert, the surviving
contribution is "thermo-mechanical-aware placement, applied to voltage regulators", and
reviewer question 2 from Phase 0A ("why is this not STAMP with VRs substituted for chiplets?")
becomes very hard to answer. Those cases should therefore be treated as the real gate, and run
next.

---

### Artifacts

```
configs/phase0b/package_stack.yaml, doe_cases.yaml
research/phase0b/MATERIAL_ASSUMPTIONS_LEDGER.md
results/phase0b/cooling_calibration.json          calibration history + residual
results/phase0b/mesh_convergence.csv              4 levels x 9 tracked quantities
results/phase0b/convergence_verdict.json
results/phase0b/gate_runs.csv                     39 runs
results/phase0b/three_case_comparison.csv
results/phase0b/materiality_analysis.json         S_m, robustness, BC sensitivity
results/phase0b/PHASE0B_DECISIVE_FIGURE_BC_A.png
results/phase0b/placement_previews/               C01-C20 + ALL_CASES.png
results/phase0b/{C05,C07,C13}/<variant>/metrics.json, nodes.npy, temps.npy, disp.npy
tests/phase0b/test_phase0b.py                     29 passed, 0 failed, 0 skipped
```

Reproduce end to end:
```bash
export PATH=/home/beams0/MGHARIB/envs/etm/bin:$PATH
cd /home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT
python -m pytest tests/phase0b/ -q
python scripts/phase0b/make_previews.py
python -c "import sys;sys.path.insert(0,'scripts/phase0b');from pathlib import Path;\
from etm.config import load_stack,load_doe;from etm.run_case import calibrate_h_top;\
import json;print(json.dumps(calibrate_h_top(load_stack(),load_doe(),Path('results/phase0b')),indent=2))"
python scripts/phase0b/run_convergence.py C05
python scripts/phase0b/run_gate.py C05 C07 C13
python scripts/phase0b/analyze_gate.py C05 C07 C13
python scripts/phase0b/make_figure.py C05 C07 C13 BC_A
```
