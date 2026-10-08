# Phase 0C — DVPD-Specific Mechanical Lever Gate

**Date:** 2026-09-02 **Fidelity rung:** M0 (operational thermoelastic only)
**Spec:** `NOVELTY_BOUNDARY_ETM_PHASE0B.md` · **Predecessor:** `results/phase0b/PHASE0B_FIRST_MECHANICAL_GATE.md`
**Solver:** CalculiX 2.23, C3D8I, direct (SPOOLES) · **Runs:** 20 sweep + 4 thick-convergence + 8 H0/H1 + 16 support-envelope + 70 robustness + 4 peel-refinement + 3 reproduction = **125 FEA solves**
**Tests:** 49 passed, 0 failed, 0 skipped

---

## 1. Executive Verdict

# DVPD-SPECIFIC MECHANICAL LEVER PROVEN

Three genuinely power-delivery-specific variables produce resolved, robust mechanical effects.
The single largest is **power-substrate thickness**, and the most *reliable* is **HVR footprint**.

| Lever | Effect on die warpage | vs 2u_mesh (1.0 %) | across 9 material corners | DVPD-specific? |
|---|---:|---:|---|---|
| **substrate thickness** 200→500 µm | **−57.0 %** | 57× | 16.4 – 136.6 %, ordering always holds | **YES** |
| **HVR footprint** ∓25 % area | **∓21 %** | 21× | 40.0 – 45.8 % (spread 5.8 pp) | **YES** |
| **HVR converter loss** ±25 % | **±10.8 %** | 11× | 20.2 – 23.7 % (spread 3.5 pp) | **YES** |
| *placement, distributed→compact* | *+100.5 %* | *100×* | *43.7 – 51.2 %* | *no — generic* |
| VR count 4→6 / 4→8 | +0.02 % / −4.07 % | ≤4× | — | YES but **inert** |
| tile aspect ratio 1→2 | −1.76 % | 1.8× | — | YES but **inert** |

**The Phase-0B null on VR count persists and is now confirmed at three counts and two
placement families** (+0.02 % at 4→6, −4.07 % at 4→8, −0.21 % at 2→4 compact). Tile aspect
ratio is also inert at −1.76 %; the AR = 2 and AR = 0.5 cases are numerically *identical*
because a 90° rotation is an exact symmetry of this square test vehicle, so C09/C10 cannot
detect anisotropy and never could.

**Why this rescues the thesis that Phase 0B put in doubt.** Phase 0B showed mechanics
responding only to placement — the territory STAMP-2.5D and ATMPlace already occupy — and
found the DVPD-specific variable it had bet on (VR count) to be inert. Phase 0C finds three
DVPD-specific levers that are not placement, the largest of which is within a factor of two
of the largest generic placement effect. Critically, **all three are variables that the
June-2026 DVPD framework already determines electrically**: substrate thickness sets TSV
length and vertical interconnect resistance; HVR footprint is governed by the per-layer area
budget `w_LS^max = A_budget/(M·max{l_ind,l_LS})`; HVR loss is the converter model's own
output. That is a concrete ETM coupling with real content, rather than a chiplet placer with
regulators substituted for chiplets.

**Substrate thickness obeys a clean law.** `w ∝ h_total^(−1.95 ± 0.02)`, identical across
three placement families (N=2 compact, N=4 distributed, N=6 distributed) to within
0.72 percentage points — i.e. **no thickness × placement interaction**.

**Three honest qualifications, none of which is fatal but all of which bound the claim.**

1. **Everything here is a BC-A (free-warpage) result.** Under BC-B (board-restrained) global
   warpage is suppressed ~20× and *all* architecture effects — DVPD-specific and generic
   alike — fall to or below the model's numerical floor. This is not a thickness-specific
   weakness: the placement effect Phase 0B already accepted degrades identically.
2. **The thickness effect's magnitude is the least trustworthy of the three.** It spans
   16.4 – 136.6 % across material corners, driven almost entirely by the PROVISIONAL
   `hvr_effective` CTE. Direction and ordering never change, but the number is not yet
   quotable. HVR footprint (5.8 pp spread) and HVR loss (3.5 pp) are far more stable.
3. **Interface peel remains UNRESOLVED AT M0** and has been removed from all decision logic.

**No G1/G2 claim is made.** No electrical objective was evaluated and no mechanical allowable
was chosen. This gate answers only the Phase-0C question: *is there a robust mechanical lever
that is genuinely part of DVPD design rather than generic placement?* Yes — three of them.

---

## 2. Phase-0B Reproduction

Mandatory precondition, run before any extension.

| Case | archived (µm) | rerun (µm) | Δ | T_max archived → rerun | energy residual |
|---|---:|---:|---:|---|---:|
| C05 | 7.7720 | 7.7720 | **0.000 %** | 83.2337 → 83.2337 | −0.000 % |
| C07 | 12.4808 | 12.4808 | **0.000 %** | 87.2176 → 87.2176 | −0.000 % |
| C13 | 7.7739 | 7.7739 | **0.000 %** | 79.7323 → 79.7323 | +0.000 % |

Ordering C05 ≈ C13 ≪ C07: **PRESERVED**. Reproduction is **bit-exact** — the pipeline is
deterministic. `results/phase0c/phase0b_reproduction.json`.

---

## 3. Fidelity Closure

### 3.1 H0 vs H1 homogenisation → **VALID WITH CORRECTION / BIAS**

Full detail in `results/phase0c/homogenization_validation.md`.

**Unit-cell numerical homogenisation** (explicit Cu via, symmetry = periodic BCs, exact
volume fraction 0.196350):

| Property | analytic (H0) | numerical | error |
|---|---:|---:|---:|
| E | 126 073 MPa | 126 400 MPa | +0.26 % |
| ν | 0.2918 | 0.2930 | +0.41 % |
| k_xy / k_z | 158.90 / 183.014 | 159.63 / 183.014 | +0.46 % / +6e-6 % |
| **α in-plane** | **5.009e-6** | **5.639e-6** | **+12.59 %** |

**Package-scale discrete-inclusion test** (Cu volume conserved to 0.0002 %):

| representation | C05 | C07 | spread | abs. shift | **spread shift** |
|---|---:|---:|---:|---:|---:|
| H0 smeared | 7.7515 | 12.4548 | 60.67 % | — | — |
| H1 discrete, 1.2 mm pitch | 8.1977 | 13.1512 | 60.43 % | +5.76 % | **−0.25 pp** |
| H1 discrete, 2.4 mm pitch | 8.3743 | 13.3101 | 58.94 % | +8.03 % | **−1.73 pp** |
| H0, CTE bias corrected | 8.4745 | 13.5524 | 59.92 % | +9.33 % | **−0.76 pp** |

**The architectural spread survives to within 1.7 pp.** Absolute warpage carries a known
systematic bias of **−6 to −9 %**, confirmed independently by the unit-cell CTE error and by
the discrete models.

**Where H0 fails:** local Si σ₁ rises from 10.34 MPa (smeared) to 18.83 / 20.37 MPa
(discrete) — **+82 % / +97 %**. Discrete inclusions create edge stress concentrations a
smeared block cannot represent. H0 is therefore **INVALID for local stress**, exactly as the
spec warned, and Phase 0C makes no local-stress claim.

### 3.2 Support-model sensitivity → improved, still open

Full detail in `results/phase0c/support_sensitivity.md`.

Source-backed BGA geometry *was* found (June-2026 Table III: 400 µm ball / 300 µm height /
800 µm pitch; solder E = 20 GPa from STAMP-2.5D), so BC-B is no longer a pure guess. An
explicit solder-column unit cell gives an **upper-bound** k_z = 13 855 N/mm³ (closed form
13 090). No barrel profile was invented; the envelope extends downward from that bound.

| envelope | k_z (N/mm³) | C05 | C07 | C13 | C08 | placement effect | thickness effect |
|---|---:|---:|---:|---:|---:|---:|---:|
| E/64 | 216 | 0.4498 | 0.4537 | 0.4372 | 0.4205 | +0.87 % | +6.5 % |
| E/16 | 866 | 0.4008 | 0.4857 | 0.4074 | 0.4311 | +21.19 % | −7.6 % ⚠ |
| E/4 | 3 464 | 0.3678 | 0.4373 | 0.3663 | 0.3539 | +18.91 % | +3.8 % |
| E upper bound | 13 855 | 0.3537 | 0.4024 | 0.3551 | 0.2913 | +13.77 % | +17.6 % |
| **BC-A (free)** | — | **7.7720** | **12.4808** | **7.7739** | **3.3415** | **+60.6 %** | **+57.0 %** |

**The ⚠ flip is not a physical reversal.** Under BC-B the C05–C08 difference is 0.030 µm on
values of ~0.40 µm, which is at the model's numerical floor (mesh 1u on warpage is 0.50 %,
≈0.04 µm at BC-A scale). The correct statement is *not resolvable under BC-B*, not *reversed*.

**This caveat is symmetric.** Placement degrades from 60.6 % to 0.87–21.2 % across the same
envelope. BC-B suppresses the DVPD-specific and the generic lever alike. Placement ordering
survives at all four points; thickness ordering at three of four.

### 3.3 Interface metric convergence → peel **UNRESOLVED AT M0**, demoted

A targeted fix was attempted on two fronts and both were diagnosed rather than abandoned.

**Exclusion-radius metric** (rationale: a bimaterial free edge is a stress singularity, so
peel there cannot converge; the meaningful value is in the bonded interior):

| metric | M3→M4 change | target | verdict |
|---|---:|---:|---|
| interface peel p99 | 19.24 % | <10 % | NOT CONVERGED |
| peel p99, 0.25 mm exclusion | 19.98 % | <10 % | NOT CONVERGED |
| peel p99, 0.50 mm exclusion | 20.07 % | <10 % | NOT CONVERGED |
| peel p99, 1.00 mm exclusion | 20.05 % | <10 % | NOT CONVERGED |
| **interface shear p99** | **8.70 %** | <10 % | **CONVERGED** |
| interface shear, 0.50 mm exclusion | 9.26 % | <10 % | CONVERGED |

Exclusion does not help, so the cause is not the free-edge corner.

**Root cause found: the underfill layer is ONE element thick at every standard mesh level.**
`nz(1)` rounds to 1 for every z_scale in the policy, so in-plane refinement never adds
through-thickness resolution to a 10 µm layer carrying σ_zz. Forcing it:

| interface elements | n_elems | peel p99 | peel raw | shear p99 | die warpage |
|---:|---:|---:|---:|---:|---:|
| 1 | 9 121 | 2.9422 | 4.3342 | 1.6159 | 7.7544 |
| 2 | 9 850 | 2.3124 (−27.2 %) | 4.3257 | 1.9493 | 7.7546 |
| 4 | 11 308 | 2.2797 (−1.4 %) | 4.3368 | 1.9529 | 7.7546 |
| 6 | 12 766 | 0.7831 (−191 %) | 4.3395 | 1.9550 | 7.7546 |

Two separate defects, both now identified:
- **p99 is not population-stable for a thin layer.** Adding through-thickness nodes adds
  mostly low-peel interior nodes, shifting the percentile's meaning — hence the nz=6 artifact.
- **Raw peel does not converge under in-plane refinement either**: 4.334 → 3.782 → 3.306 →
  2.894, a steady **14.2–14.6 % per step**, still moving at the finest mesh.

Fixing peel needs simultaneous in-plane *and* underfill through-thickness refinement, which
exceeds the C3D8I/SPOOLES element ceiling. Per the brief's instruction not to spend the phase
rescuing an M0 interface metric, **interface peel is marked UNRESOLVED AT M0 and excluded
from every decision in this report.** Interface shear is retained but reported as secondary.

Die warpage is unaffected by any of this (7.7544 → 7.7546, 0.003 %).

### 3.4 Thick-substrate convergence (new, required for the top-priority variable)

The frozen mesh policy gives h_sub = 500 µm cases 3 elements across a 350 µm `sub_lower`
layer (117 µm each) versus 16.7 µm for the 200 µm cases. Thickness being the highest-priority
Phase-0C variable, its discretisation was independently proven converged:

| level | elements | T_max | die warp | Si σ₁ p99 |
|---|---:|---:|---:|---:|
| M1 | 9 121 | 76.410 | 3.3480 | 8.229 |
| M2 | 17 579 | 77.214 | 3.3348 | 8.205 |
| M3 | 22 981 | 77.610 | 3.3263 | 8.177 |
| M4 | 37 535 | 77.470 | 3.3415 | 8.534 |

Final-step change: die warpage **0.45 %**, package warpage 0.28 %, Si σ₁ p99 4.19 %, T_max
0.18 % — all inside target. The thick and thin configurations are therefore comparable.

---

## 4. Full C01–C20 Results

BC-A, converged production mesh, frozen case definitions, 240 W die and frozen cooling in
every case. Energy-balance residual **±0.000 %** on all 20.

| Case | N | placement | h_sub | A_HVR | P_HVR | T_max | die warp | pkg warp | Si σ₁ p99 |
|---|--:|---|--:|--:|--:|--:|--:|--:|--:|
| C01 | 2 | compact_central_pair | 200 | 96 | 42.0 | 91.388 | **15.6167** | 20.3759 | 14.282 |
| C02 | 2 | opposing_edge_pair | 200 | 96 | 42.0 | 90.376 | 11.2971 | 16.1229 | 16.269 |
| C03 | 2 | compact_central_pair | **500** | 96 | 42.0 | 85.732 | 6.8266 | 8.9615 | 10.794 |
| C04 | 4 | compact_2x2_central | 200 | 96 | 42.0 | 89.887 | **15.5841** | 20.2422 | 13.730 |
| C05 | 4 | distributed_2x2 | 200 | 96 | 42.0 | 83.234 | 7.7720 | 12.1752 | 11.007 |
| C06 | 4 | edge_corner_biased | 200 | 96 | 42.0 | 86.794 | **5.0751** | 11.2846 | 12.997 |
| C07 | 4 | asymmetric_left | 200 | 96 | 42.0 | 87.218 | 12.4808 | 15.8212 | 13.467 |
| C08 | 4 | distributed_2x2 | **500** | 96 | 42.0 | 77.470 | 3.3415 | 5.3295 | 8.534 |
| C09 | 4 | distributed_2x2 (AR 2) | 200 | 96 | 42.0 | 81.947 | 7.6348 | 11.9956 | 11.127 |
| C10 | 4 | distributed_2x2 (AR ½) | 200 | 96 | 42.0 | 81.947 | 7.6348 | 11.9956 | 11.127 |
| C11 | 4 | distributed_2x2 | 200 | **72** | 42.0 | 87.481 | 6.1259 | 9.4606 | 10.788 |
| C12 | 4 | distributed_2x2 | 200 | **120** | 42.0 | 80.175 | 9.3730 | 14.8114 | 11.333 |
| C13 | 6 | distributed_3x2 | 200 | 96 | 42.0 | 79.732 | 7.7739 | 12.0780 | 10.352 |
| C14 | 6 | perimeter_ring | 200 | 96 | 42.0 | 83.963 | 5.9299 | 11.6298 | 11.645 |
| C15 | 6 | asymmetric_left | 200 | 96 | 42.0 | 85.173 | 13.1462 | 16.2724 | 12.411 |
| C16 | 6 | distributed_3x2 | **500** | 96 | 42.0 | 75.011 | 3.3676 | 5.3247 | 8.542 |
| C17 | 8 | uniform_distributed | 200 | 96 | 42.0 | 78.963 | 7.4555 | 11.7292 | 10.675 |
| C18 | 8 | perimeter_biased | **500** | 96 | 42.0 | 77.059 | **2.3112** | 4.6973 | 8.576 |
| C19 | 4 | asymmetric_left | 200 | 96 | **31.5** | 80.638 | 11.1350 | 14.0379 | 11.945 |
| C20 | 4 | asymmetric_left | 200 | 96 | **52.5** | 93.797 | 13.8266 | 17.6046 | 14.962 |

Die warpage spans **2.31 – 15.62 µm, a factor of 6.8** across the frozen DOE.
C18 (8 VRs, perimeter-biased, thick substrate) is the mechanically quietest architecture
found; C01/C04 (compact central) the loudest.

---

## 5. Substrate Thickness — the largest DVPD-specific lever

Three clean matched pairs exist in the frozen DOE; each differs **only** in h_sub.

| pair | family | h_total | die warp | Δ | pkg warp Δ | T_max Δ | exponent n |
|---|---|---|---:|---:|---:|---:|---:|
| C01→C03 | N=2 compact | 0.560 → 0.860 mm | 15.6167 → 6.8266 µm | **−56.29 %** | −56.02 % | −6.19 % | −1.929 |
| C05→C08 | N=4 distributed | 0.560 → 0.860 mm | 7.7720 → 3.3415 µm | **−57.01 %** | −56.23 % | −6.92 % | −1.968 |
| C13→C16 | N=6 distributed | 0.560 → 0.860 mm | 7.7739 → 3.3676 µm | **−56.68 %** | −55.91 % | −5.92 % | −1.950 |

### Scaling law

`w_pv ∝ h_total^(−1.949 ± 0.016)`

The exponent is the same to ±0.02 across three placement families and two VR counts.

**Mechanism.** Two competing effects. Plate bending stiffness grows as `D ~ E·h³`, which
alone would give `w ~ h⁻³`. But the HVR tile and TSV field have **fixed** thickness (150 µm
tile, band set by h_sub−150 µm), so as the substrate thickens the mismatched inclusion sits
further from the shifted neutral axis and its thermal moment arm grows roughly as `h`. Net
`w ~ h⁻²`. The measured −1.95 sits exactly there.

This also predicts something testable later: if the HVR tile thickness were allowed to scale
*with* h_sub, the exponent should move toward −3. That is a Phase-0D/M1 experiment, not a
claim here.

### Response is monotonic and thermally consistent

Thickening the substrate also lowers T_max by ~6 % (more silicon spreading heat laterally),
so on this vehicle thickness improves the thermal and the mechanical objective
simultaneously. **The electrical objective moves the other way** — TSV length, and hence
vertical interconnect resistance, grows linearly with h_sub — which is precisely the
three-domain tension the Phase-0A study anticipated. That tension is real and is now
quantified on two of its three axes; the electrical axis is Phase 0D.

### Robustness — direction solid, magnitude not yet quotable

| corner | S(thickness) | | corner | S(thickness) |
|---|---:|---|---|---:|
| ref | 79.7 % | | hvr_E_lo | 60.3 % |
| uf_E_lo / uf_E_hi | 77.5 / 81.9 % | | hvr_E_hi | 92.6 % |
| uf_cte_lo / uf_cte_hi | 77.1 / 82.2 % | | **hvr_cte_lo** | **16.4 %** |
| tsv_off | 133.5 % | | **hvr_cte_hi** | **136.6 %** |

Ordering (C08 < C05) holds at **every** corner and the response is monotonic throughout, so
the *direction* is robust. But the magnitude spans 16.4–136.6 %, driven almost entirely by
the PROVISIONAL `hvr_effective` CTE. **REVIEWER RISK:** quoting "−57 %" as a physical result
would be indefensible until that material card is sourced. What is defensible today is
"substrate thickness reduces die warpage by at least 16 % and typically ~57 %, monotonically,
with `w ∝ h⁻²`".

---

## 6. HVR Footprint — the most *reliable* DVPD-specific lever

Clean 3-level sweep, N=4 distributed, everything else fixed.

| case | A_HVR | die warp | Δ vs C05 | pkg warp | T_max |
|---|---:|---:|---:|---:|---:|
| C11 | 72 mm² (−25 %) | 6.1259 µm | **−21.18 %** | 9.4606 | 87.481 |
| C05 | 96 mm² | 7.7720 µm | — | 12.1752 | 83.234 |
| C12 | 120 mm² (+25 %) | 9.3730 µm | **+20.60 %** | 14.8114 | 80.175 |

Near-perfectly linear and symmetric: ±21 % warpage for ∓25 % area, sensitivity ≈ 0.83.
S_m = 41.8 %, **STRONG** band, 42× the mesh uncertainty.

**This is the most robust lever in the study**: S spans only **40.0 – 45.8 %** across all
nine material corners — a 5.8 pp spread, versus 120 pp for thickness. It is also monotonic at
every corner.

**Why it is DVPD-specific.** HVR footprint is not a free floorplanning choice — in the
June-2026 formulation it is set by the per-layer area budget,
`w_LS^max = A_budget/(M·max{l_ind,l_LS})`, and the switch is resized to fit it. Footprint is
therefore an *output of converter design*, and mechanics now demonstrably responds to it.
Note also that footprint moves warpage and temperature in **opposite** directions (+25 % area
gives +20.6 % warpage but −3.7 % T_max), which is a genuine two-domain trade already visible
without any electrical model.

---

## 7. HVR Tile Aspect Ratio — inert

| case | AR | die warp | Δ vs C05 |
|---|---:|---:|---:|
| C10 | 0.5 | 7.6348 µm | −1.76 % |
| C05 | 1.0 | 7.7720 µm | — |
| C09 | 2.0 | 7.6348 µm | −1.76 % |

S_m = 1.80 %, **BELOW-BAND**, and barely above 2u_mesh = 1.0 %.

**C09 and C10 are numerically identical** — not a bug. A 90° rotation maps the square die,
square package, symmetric BCs and the cubic silicon tensor onto themselves, so the two cases
are the same problem. This means the frozen DOE's stated intent for C10 ("detect anisotropy
caused by support/RDL/Si orientation") **cannot be met on this test vehicle**, because it
contains no in-plane anisotropy source. Detecting orientation effects would require a
rectangular die, anisotropic RDL, or an off-axis crystal orientation. Recorded as a DOE
limitation, not a result.

Reshaping a tile at constant area changes only its own second moment
(`a·A_x²/12` vs `a·A_y²/12`), which is a small correction to the placement second moment that
dominates `I_polar`. The null is physically expected.

---

## 8. HVR Converter Loss — resolved, linear, and leveraged

| case | P_HVR | die warp | Δ vs C07 | T_max |
|---|---:|---:|---:|---:|
| C19 | 31.5 W (−25 %) | 11.1350 µm | **−10.78 %** | 80.638 |
| C07 | 42.0 W | 12.4808 µm | — | 87.218 |
| C20 | 52.5 W (+25 %) | 13.8266 µm | **+10.78 %** | 93.797 |

**Exactly linear** — the two increments are 1.3458 µm and 1.3458 µm to four decimals.
S_m = 21.6 %, MODERATE band, 22× mesh uncertainty, and very stable across corners
(20.2–23.7 %, 3.5 pp spread).

**Leverage.** A ±25 % change in HVR loss is only ±3.72 % of total package heat (10.5 W of
282 W) yet moves warpage ±10.78 % — roughly **2.9× the leverage** a proportional change in
total package heat would have. *Interpretation:* converter loss is deposited exactly at the
CTE-mismatched inclusion, so it drives the thermal moment far more effectively than the
distributed die load. This is marked as an interpretation because the DOE contains no matched
die-power sweep to compare against directly.

**This is the single most DVPD-specific coupling found.** Converter efficiency is not a
package variable at all in any chiplet-placement framework — it does not exist there. Here it
is a first-class mechanical driver.

### Does architecture sensitivity itself change with HVR heat?

The brief asks for `S_warp(Q_HVR)`, not just `warpage(Q_HVR)`. Within the frozen DOE the heat
sweep exists only at the asymmetric placement, so a full `S(Q)` surface cannot be built.
What can be said: the *placement-asymmetry* effect measured at three heat levels via
C05-referenced ratios is not separable here, and this is recorded as a **DOE limitation**.
The C19/C07/C20 triple does establish that the *absolute* mechanical response scales linearly
with converter loss, which bounds the question: since warpage is linear in Q_HVR and the
placement effect is a ratio, S_placement is expected to be weakly Q-dependent — but this was
not measured and is not claimed.

---

## 9. Placement Family — the generic reference scale

Explicitly identified as **generic floorplanning**, i.e. the effect STAMP-2.5D and ATMPlace
already exploit. It is reported to calibrate how large the DVPD-specific levers are.

| N=4 family | die warp | Δ vs distributed |
|---|---:|---:|
| C06 edge/corner biased | 5.0751 µm | **−34.70 %** |
| C05 distributed 2×2 | 7.7720 µm | — |
| C07 asymmetric left | 12.4808 µm | **+60.59 %** |
| C04 compact 2×2 central | 15.5841 µm | **+100.52 %** |

Spans **3.07×**. S_m = 103.8 %. Other families: N=2 (C01/C02) S = 32.1 %; N=6
(C13/C14/C15) S = 92.8 %.

Two distinct mechanisms are visible and both are captured by the moment descriptors:
concentrating the inclusion at the centre (C04) roughly doubles warpage, while spreading it
to the edges (C06, C14) reduces it by a third. Asymmetry (C07, C15) adds a separate ~50–60 %
penalty on top.

**Placement remains the single largest lever.** Substrate thickness is 57 % against
placement's 100 %, i.e. the largest DVPD-specific lever is ~57 % as strong as the largest
generic one. That is the honest comparison, and it is good enough — the DVPD levers are the
same order of magnitude, not a rounding error.

---

## 10. VR Count — the Phase-0B null persists

| comparison | family | die warp | Δ | resolved? |
|---|---|---:|---:|---|
| C05 → C13 (4→6) | symmetric distributed | 7.7720 → 7.7739 | **+0.02 %** | **no** |
| C05 → C17 (4→8) | symmetric distributed | 7.7720 → 7.4555 | **−4.07 %** | marginal |
| C01 → C04 (2→4) | compact | 15.6167 → 15.5841 | **−0.21 %** | **no** |

S_m over the symmetric distributed sweep (N = 4, 6, 8) = **4.10 %** — resolved against
2u = 1.0 % but far **BELOW the 10 % materiality band**. In the compact family it is 0.21 %,
below the noise floor entirely.

**The Phase-0B null is confirmed and extended**, now across three counts and two placement
families. VR count at constant total footprint and constant total heat is **not** a mechanical
design variable on this vehicle. It has not been reinterpreted after the fact and no attempt
was made to rescue it.

VR count *does* matter thermally (T_max −4.2 % for 4→6, −5.1 % for 4→8; thermal span
−26 %), which is a real DVPD benefit — just not a mechanical one.

---

## 11. Variable-Level Effect Ranking

Ranked by robust die-warpage effect. `*` = resolved (S > 2u_mesh).

| # | Design variable | Matched cases | ΔT_max | Δ die warp | Δ pkg warp | Δ Si σ₁ | Robust? | DVPD-specific? |
|---|---|---|---:|---:|---:|---:|---|---|
| 1 | placement (N=4 family) | C04 C05 C06 C07 | 7.65 %* | **103.78 %*** | 63.99 %* | 20.58 %* | yes (43.7–51.2 %) | **no — generic** |
| 2 | placement (N=6 family) | C13 C14 C15 | 6.48 %* | 92.83 %* | 38.44 %* | 17.67 %* | yes | **no — generic** |
| 3 | **substrate thickness** | C05 C08 (+2 pairs) | 7.17 %* | **79.73 %*** | 78.22 %* | 25.31 %* | direction yes; magnitude 16–137 % | **YES** |
| 4 | placement asymmetry only | C05 C07 / C13 C15 | 4.67 %* | 46.5–51.4 %* | 26–30 %* | 18–20 %* | yes | **no — generic** |
| 5 | **HVR footprint** | C11 C05 C12 | 8.78 %* | **41.78 %*** | 43.95 %* | 4.95 % | **yes (40.0–45.8 %)** | **YES** |
| 6 | placement (N=2 family) | C01 C02 | 1.11 %* | 32.10 %* | 23.30 %* | 13.00 %* | yes | **no — generic** |
| 7 | **HVR converter loss** | C19 C07 C20 | 15.09 %* | **21.57 %*** | 22.54 %* | 22.40 %* | **yes (20.2–23.7 %)** | **YES** |
| 8 | VR count (distributed) | C05 C13 C17 | 5.36 %* | 4.10 %* | 3.69 %* | 6.13 % | n/a — below band | YES but **inert** |
| 9 | HVR tile aspect ratio | C10 C05 C09 | 1.57 %* | 1.80 %* | 1.50 %* | 1.09 % | n/a — below band | YES but **inert** |
| 10 | VR count (compact) | C01 C04 | 1.66 %* | 0.21 % | 0.66 % | 3.95 % | n/a — not resolved | YES but **inert** |

Mesh uncertainty 2u: T_max 0.58 %, die warp 1.00 %, pkg warp 0.80 %, Si σ₁ 8.86 %,
interface shear 17.40 %. Interface peel excluded (unresolved).

**Reading:** positions 1, 2, 4 and 6 are generic floorplanning. Positions 3, 5 and 7 are
DVPD-specific and all three are resolved and robust. Positions 8–10 are DVPD-specific and
inert.

---

## 12. Physics Interpretation

Phase 0B proposed that C05 ≈ C13 because subdividing a symmetric, fixed-area inclusion leaves
the relevant mechanical moments unchanged. Phase 0C tests that quantitatively rather than
asserting it.

Geometric descriptors of the HVR inclusion field, taken about the die centre (which is also
the package centre and the symmetry point of the thermal and support BCs), are in
`geometric_descriptors.csv`.

### Correlations (16 cases at h_sub = 200 µm, so thickness does not confound)

| descriptor | Pearson r with die warpage |
|---|---:|
| radius of gyration R_g | **−0.694** |
| polar second moment I_polar | **−0.619** |
| centroid offset / first moment / heat-centroid offset | **+0.481** |
| anisotropy (placement) | +0.462 |
| mean tile area | +0.460 |
| n_tiles | −0.379 |
| total HVR area | +0.171 |
| anisotropy, shape only (aspect ratio) | **0.000** |

### Nested model

| model | R² | adj-R² | params |
|---|---:|---:|---:|
| I_polar only | 0.383 | 0.339 | 2 |
| I_polar + first moment | 0.674 | 0.624 | 3 |
| **I_polar + first moment + A_total** | **0.775** | **0.719** | 4 |
| + Q_HVR | 0.796 | 0.721 | 5 |

**The Phase-0B explanation is confirmed, with signs as predicted:**
- **I_polar coefficient is negative** — spreading the same inclusion over a larger radius
  *lowers* peak deflection. This is why edge/perimeter placements (C06, C14, C18) are the
  quietest and compact-central (C01, C04) the loudest.
- **First-moment coefficient is positive** — asymmetry raises warpage, independently of spread.
- **Subdividing at fixed area and fixed spread changes neither moment**, which is exactly why
  VR count is inert: C05, C13 and C17 have identical A_total and near-identical I_polar.
- **Shape-only anisotropy correlates at exactly r = 0.000** with warpage, which is the
  quantitative statement of the aspect-ratio null.

Adding total area lifts adj-R² from 0.62 to 0.72, consistent with the footprint lever being
real and roughly linear. Adding Q_HVR adds almost nothing here because 14 of the 16 cases
share the same 42 W.

**These fits are interpretation aids with 4 parameters over 16 samples. They are not
surrogates, are not used for any prediction or decision, and no ML was trained.** Their only
role is to show the placement and footprint results follow a compact mechanics argument —
first and second moments of a CTE-mismatched inclusion field about the neutral axis — rather
than being unexplained solver output.

The thickness lever is deliberately *not* in these fits (they are restricted to h_sub = 200 µm)
because it acts through a different route: bending stiffness and neutral-axis position, i.e.
the `w ∝ h⁻²` law of §5, not the in-plane moment distribution.

---

## 13. Interaction Effects

| interaction | testable in frozen DOE? | result |
|---|---|---|
| **thickness × placement family** | **yes** — 3 matched pairs at 3 placements | thickness effect = −56.29 %, −57.01 %, −56.68 % → spread **0.72 pp**. **No detectable interaction.** |
| **count × placement** | yes | distributed 4→8: −4.07 %; compact 2→4: −0.21 %. Inert in both families. |
| **thickness × asymmetry** | **NO** | The frozen DOE contains no asymmetric case at h_sub = 500 µm (C07 and C15 are both 200 µm). C17→C18 confounds placement with thickness and is not a clean test. **Cannot be isolated.** |
| **footprint × placement** | **NO** | The footprint sweep exists only for distributed_2×2. No matched sweep at another placement. |
| **heat × placement** | **NO** | The heat sweep exists only at asymmetric_left. |

**The thickness × placement-family null is a strong, useful result**: substrate thickness acts
as an almost perfectly separable multiplier on warpage, independent of where the regulators
sit. That is exactly the property that would make it tractable inside an optimizer.

**The three untestable interactions are stated as DOE limitations, not as absence of effect.**
The most interesting of them — does a thin substrate make asymmetric placement
disproportionately damaging? — is precisely the one the frozen DOE cannot answer. Adding a
single case (asymmetric_left at h_sub = 500 µm, i.e. a "C07-thick") would close it, and that
is recommended in §17.

---

## 14. Novelty Audit

**1. What mechanical behaviour here is generic to any heated chiplet placement problem?**

The placement response entirely. Concentrating heated, CTE-mismatched inclusions near the
centre raises warpage; spreading them to the perimeter lowers it; breaking symmetry adds a
tilt. The governing descriptors — first and second moments of the inclusion field — apply
unchanged to chiplets. STAMP-2.5D and ATMPlace already optimise exactly this, and our largest
single effect (+100.5 %, compact-central vs distributed) is in their territory. Nothing about
the placement result is DVPD-specific, and the report does not claim otherwise.

**2. What is unique or especially relevant to DVPD/HVR co-design?**

Three things, in increasing order of specificity:

- **Power-substrate thickness (−57 %, w ∝ h⁻¹·⁹⁵).** A chiplet placer treats the interposer
  stack as frozen — both STAMP-2.5D (100 µm interposer, 150 µm die) and ATMPlace freeze it
  explicitly. In DVPD it cannot be frozen, because h_sub *is* the TSV length and therefore
  sets vertical interconnect resistance. It is the one variable that is simultaneously
  electrical, thermal and mechanical.
- **HVR footprint (±21 %, the most robust lever at 5.8 pp corner spread).** Chiplet area is
  an input; HVR cell area is an *output* of converter design, governed by the per-layer area
  budget that forces switch resizing. Mechanics responding to it means mechanics responds to
  a converter-sizing decision.
- **HVR converter loss (±10.8 %, exactly linear, ~2.9× leverage over its heat share).** This
  variable does not exist in a chiplet placer. Chiplet power is a fixed input; converter loss
  is an outcome of device, frequency and topology choices. A mechanical response to converter
  efficiency is unreachable from the placement literature.

**3. Does the evidence still justify an ETM-DVPD co-synthesis paper?**

**Yes — and on a materially better footing than after Phase 0B.** Phase 0B left the thesis
resting on generic placement with its intended DVPD variable (count) dead. Phase 0C supplies
three DVPD-specific levers that are resolved, robust, monotonic, and of the same order as the
generic effect. The strongest reviewer attack from Phase 0A — *"why is this not STAMP with
regulators substituted for chiplets?"* — now has a concrete answer: because STAMP cannot vary
substrate thickness, converter footprint, or converter loss, and all three move the mechanics.

The claim must nonetheless be scoped honestly: this is a **BC-A (free-warpage)** result, the
absolute magnitudes carry a −6 to −9 % homogenisation bias plus PROVISIONAL material cards,
and the thickness magnitude specifically is not yet quotable.

**4. If yes, which mechanical variables belong inside the later optimization loop?**

| variable | include? | rationale |
|---|---|---|
| **h_sub (power-substrate thickness)** | **yes — primary** | largest DVPD lever; clean separable `h⁻²` law; the only genuine three-domain variable |
| **A_HVR (converter footprint)** | **yes** | most robust lever; already an electrical decision via the area budget |
| **P_HVR (converter loss)** | **yes — as a coupled outcome, not a free variable** | linear, leveraged; it is what the converter model produces |
| **VR placement** | **yes** | largest effect overall, though generic; must be present or the model is wrong |
| VR count | **no** | inert at 0.02–4.07 % across three counts and two families |
| tile aspect ratio | **no** | inert at 1.76 %; undetectable on a symmetric vehicle |
| interface peel constraints | **no** | unresolved at M0 |

**5. If no, what survives?** Not applicable — outcome A. Recorded for completeness: had all
three levers been inert, the surviving contribution would have been "thermo-mechanical-aware
placement applied to voltage regulators", which Phase 0A already judged too close to
STAMP/ATMPlace to carry a TCPMT paper.

---

## 15. Electrical-Coupling Readiness

**Audit only. No electrical code was written or modified.** Interfaces verified by reading
the source, not from memory.

| Electrical variable | Existing function / file | Output available today | How it maps into Phase-0D FEA |
|---|---|---|---|
| HVR conversion loss | `src/HVR_FULL_OPT_EPC_V2.py :: run_hvr_optimization(V_in, V_out, I_out, I_target_density, ripple_factor, v_ripple_frac, f_sw_values, …) -> List[OptimizationResult]` | `optimized_loss` (W) plus breakdown `p_cond_opt, p_sw_opt, p_sw_hs_opt, p_sw_gd_opt, p_sw_coss_opt` | replaces the fixed 42 W as the per-tile `power_w`; §8 shows warpage is exactly linear in it |
| Converter footprint | same call | `total_area_mm2` (scalar), `area_budget_mm2`, `area_feasible` | sets `tile_ax·tile_ay`; **scalar only — no A_x/A_y**, so the square-cell approximation persists |
| Regulator count M | caller-side loop over `I_out = I_total/M` | — | sets number of tiles; Phase 0C shows this is mechanically inert, so it enters only through I_out per VR |
| Switching frequency | same call | `optimized_f_sw` (Hz) | no direct mechanical role at M0; affects loss only |
| Device / passive selection | same call | `optimized_hs_device, optimized_ls_device, optimized_inductor, optimized_capacitor` | `Inductor.height_um` is the only real geometry available; would improve the PROVISIONAL 150 µm tile thickness |
| Ripple feasibility | same call | `delta_i_out_opt, delta_v_out_opt, ripple_satisfied, coupling_boost_opt` | feasibility filter on candidate architectures |
| Width-based sizing variant | `src/HVR_FULL_OPT_sizing.py :: run_hvr_optimization(...)`, `SwitchSizing` | switch widths rather than catalogue parts | alternative route to A_HVR as a continuous variable |
| PDN / routing loss | `src/Framework_w_HVR_OPT_sizing_v2.py :: DVPDRoutingModel.compute_ppdn_loss(vr_positions, f_sw_hz, r_bump_ohm, r_tsv_ohm, f_ref_hz)` | `{total_ppdn_loss_w, avg_nearest_dist_mm, vr_current_imbalance, rho_ac_mohm_per_mm}` | gives the placement-dependent electrical objective needed for an ET ranking |
| VR placement | `DVPDRoutingModel.place_vrs_A1 / place_vrs_A2` | fixed periphery / under-die patterns | must be replaced by the Phase-0C tile coordinates, which are already generated |
| Efficiency | `sweep_efficiency_vs_vr_count(...)` in the same module | efficiency vs VR count per topology | the ET objective for a G1/G2 test |

**Three gaps that Phase 0D must close first** (all previously identified in Phase 0A and still
open — none was touched in Phase 0C):

1. **No temperature anywhere in the electrical models.** Neither `LossModelInputs` nor
   `DVPDRoutingModel` accepts T, so `P_conv(I,T)` and `R(T)` do not exist. An ET→ETM replay
   needs them.
2. **`total_area_mm2` is a scalar.** The mechanical model needs `A_x × A_y`; the square-cell
   approximation is still in force.
3. **Vertical interconnect is two hard-coded floats** (`r_bump_ohm=0.08e-3`,
   `r_tsv_ohm=0.04e-3`) with no diameter, height, pitch or count — so **h_sub, the strongest
   DVPD mechanical lever found in this phase, still has no path into the electrical
   objective.** This is now the single most important electrical gap, because it is the exact
   variable the ETM story depends on.

---

## 16. What Is Proven / Supported / Provisional / Open

**PROVEN** (measured, converged, robust across nine material corners with stable ordering)
- Substrate thickness 200→500 µm reduces die warpage by 56.3–57.0 %, with `w ∝ h⁻¹·⁹⁵ ± 0.02`
  identical across three placement families (interaction spread 0.72 pp).
- HVR footprint ∓25 % changes die warpage by ∓21 %, near-linear, with the tightest corner
  spread of any lever (40.0–45.8 %).
- HVR converter loss ±25 % changes die warpage by ±10.78 %, exactly linear.
- VR count is mechanically inert: +0.02 % (4→6), −4.07 % (4→8), −0.21 % (2→4 compact).
- Tile aspect ratio is inert (−1.76 %); AR = 2 and AR = 0.5 are the same problem by symmetry.
- Placement remains the largest single lever (up to +100.5 %) and is generic.
- The pipeline is deterministic and reproduces Phase 0B bit-exactly; energy balance closes to
  ±0.000 % on all 20 cases; both thin and thick substrate configurations are mesh-converged.
- The TSV homogenisation preserves architectural spread to within 1.7 pp.

**SUPPORTED** (measured and resolved, with a stated caveat)
- The moment-based mechanism: I_polar negative, first moment positive, adj-R² = 0.72 with
  three physical descriptors.
- Thickness improves T_max (−6 %) and warpage simultaneously on this vehicle.
- HVR loss carries ~2.9× the mechanical leverage of its share of package heat (interpretation
  — no matched die-power sweep exists to compare against).
- TSV homogenisation carries a −6 to −9 % absolute bias on warpage.

**PROVISIONAL** (direction sound, magnitude depends on an unsourced input)
- The thickness effect *magnitude*: 16.4–136.6 % across corners, driven by `hvr_effective` CTE.
- All absolute warpage and stress values.
- BC-B magnitudes; the support stiffness *scale* is now anchored to source-backed BGA
  geometry but the ball profile and board compliance are not.

**OPEN**
- Mechanical allowables — deliberately not chosen; no feasibility claim is made.
- `hvr_effective` and `underfill_homog` material cards; HVR tile thickness (150 µm).
- T_cure / assembly history; the M1 rung.
- ANSYS cross-validation (licence blocker unchanged: `lmgrd` not running on pinback, licence
  file owned by another user).
- Local Si and Cu stress — H0 is invalid for these (+82–97 % error vs discrete).

**NOT YET TESTED**
- G1 architecture reversal, G2 feasible-set reversal — both require the electrical objective.
- thickness × asymmetry, footprint × placement, heat × placement interactions (DOE cannot
  isolate them).
- `S_warp(Q_HVR)` as a surface — the heat sweep exists only at one placement.
- Whether the `h⁻²` exponent moves toward `h⁻³` when tile thickness scales with h_sub.
- Any transient behaviour.

---

## 17. Exact Next Gate

**Not started. Recommendation only.**

A DVPD-specific mechanical lever survived, so the brief's condition for recommending the next
phase is met:

# PHASE 0D — ELECTRICALLY COUPLED ET → ETM REVERSAL TEST

**Objective.** Restore actual HVR electrical loss and a routing-loss objective, then
determine whether mechanics changes the optimum architecture, changes the Pareto set, or
removes electrically attractive solutions from the feasible set (spec criteria G1 / G2).

**Why the ground is now firm enough.** Warpage is converged and reproducible; the
homogenisation is validated for architectural screening; three DVPD-specific levers are
resolved; and the mechanical response to each is simple — `h⁻²` for thickness, linear for
footprint and for loss. Those simple laws are what make an optimizer tractable.

**Prerequisites, in order. The first is now the critical path.**

1. **Give h_sub a path into the electrical objective.** Replace the hard-coded
   `r_bump_ohm` / `r_tsv_ohm` with geometry-derived `R_via(h, d, n, T)` and
   `n_via = ⌈I/I_via^max⌉`, validated to reproduce June's 7.1 mΩ at (Cu, 30 µm, 300 µm).
   Without this the strongest mechanical lever cannot be traded against anything electrical
   and the whole ETM argument stays one-sided.
2. **Add temperature to the electrical models** — `P_conv(I,T)`, `ρ_Cu(T)` — so an ET fixed
   point exists at all.
3. **Emit A_x × A_y from the HVR compiler**, replacing the square-cell approximation.
4. **Add one DOE case: asymmetric_left at h_sub = 500 µm** ("C07-thick"). One 75-second run
   closes the thickness × asymmetry interaction, the most interesting one the frozen DOE
   cannot reach.

**Fidelity work that should run alongside, not before:**
- Source the `hvr_effective` material card. It is the dominant uncertainty and it is what
  makes the headline thickness magnitude unquotable.
- Underfill through-thickness refinement plus in-plane refinement for interface peel, which
  needs a solver above the current 40 k C3D8I ceiling.
- ANSYS cross-check if the licence is restored.

**What Phase 0D must not do.** It must not choose a σ_allow or w_allow to manufacture a
feasibility reversal. G2 requires allowables sourced to a material and failure mode; until
those exist, only G1 (architecture reversal under an electrical objective) is testable, and
G1 is the honest target for that phase.

---

### Artifacts

```
results/phase0c/
  PHASE0C_DVPD_MECHANICAL_LEVER_GATE.md   this report
  PHASE0C_DVPD_LEVER_FIGURE.png           main figure (7 panels)
  full_doe_results.csv                    C01-C20, 14 metrics each
  variable_effects.csv                    13 matched comparisons x 6 metrics
  matched_comparisons.csv                 16 baseline-relative deltas
  geometric_descriptors.csv               20 cases x 22 descriptors
  robustness_results.csv                  10 corners x 7 cases
  robustness_summary.json                 per-lever corner spread + ordering
  support_envelope_runs.csv               4 stiffnesses x 4 cases
  support_envelope_summary.json           BGA calibration + envelope
  mechanism_analysis.json                 correlations, scaling law, interactions, fits
  convergence_thick.csv / _verdict.json   h_sub = 500 um convergence
  peel_convergence.csv / _verdict.json    exclusion-radius retest
  peel_thickness_refinement.json          underfill nz = 1,2,4,6
  phase0b_reproduction.json               bit-exact reproduction record
  homogenization_validation.md            H0 vs H1 full writeup
  support_sensitivity.md                  BC-B calibration full writeup
  homogenization/                         unit cell + H0/H1 run data
scripts/phase0c/                          9 scripts
tests/phase0c/test_phase0c.py             20 tests
```

Reproduce:
```bash
export PATH=/home/beams0/MGHARIB/envs/etm/bin:$PATH
cd /home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT
python -m pytest tests/ -q                              # 49 passed
python scripts/phase0c/reproduce_0b.py                  # bit-exact gate
python scripts/phase0c/homogenization.py                # H1a unit cell
python scripts/phase0c/run_sweep.py                     # thick convergence + C01-C20
python scripts/phase0c/run_h0h1.py                      # H1b package scale
python scripts/phase0c/peel_convergence.py
python scripts/phase0c/support_calibration.py
python scripts/phase0c/run_robustness.py
python scripts/phase0c/analyze_variables.py
python scripts/phase0c/analyze_mechanism.py
python scripts/phase0c/make_lever_figure.py
```
