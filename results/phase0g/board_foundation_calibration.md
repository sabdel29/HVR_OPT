# Phase 0G Sec. 5/6/7 — Calibrating the assembly boundary, and the withdrawal of the
# assembly-state reversal

## 1. The claim under audit

Phase 0F reported that the mechanical thickness preference **reverses** between assembly
states: a free package prefers a thicker substrate, a mounted package prefers a thinner one.
That reversal rested entirely on **BC-B**, a compact foundation whose stiffness was flagged
PROVISIONAL in Phase 0F. Phase 0G was required to determine whether the reversal is a
property of *board support* or a property of *that particular model*.

Three diagnostics were run, in increasing physical fidelity:

| model | underside treatment | what it represents |
|---|---|---|
| `BC_A` | 3-2-1 kinematic anchors only | free package |
| `BC_BZ` | vertical restraint on the plane + 3-2-1 in-plane | a true Winkler foundation |
| `BC_B` | `*BOUNDARY {n},1,3` on the plane — **all three DOF** | what Phases 0C–0F used |
| `BC_BOARD` | explicit BGA layer + explicit PCB, 3-2-1 only | a physically constructed assembly |

## 2. BC-B is a clamp, not a foundation

`BC_B` writes `*BOUNDARY` with `{n},1,3` across the underside plane. That restrains the
**in-plane** degrees of freedom as well as the vertical one. A BGA field does not: solder
balls are compliant in shear, so a mounted package retains in-plane freedom relative to its
board. The consequence is measurable and decisive.

Sweeping the support modulus over **seven decades** (`k_z` = 0.001 → 13,090 N/mm³) on an
identical 30,050-element mesh:

| k_z (N/mm³) | 0.80 mm | 1.00 mm | 1.50 mm | 2.00 mm | S_h(0.8→2.0) |
|---|---|---|---|---|---|
| 0.001 | 0.73914 | 0.87970 | 1.15341 | 1.37553 | +0.8610 |
| 0.01 | 0.73911 | 0.87968 | 1.15339 | 1.37552 | +0.8611 |
| 0.1 | 0.73876 | 0.87942 | 1.15324 | 1.37542 | +0.8618 |
| 1 | 0.73539 | 0.87680 | 1.15167 | 1.37434 | +0.8689 |
| 3 | 0.72817 | 0.87111 | 1.14823 | 1.37195 | +0.8841 |
| 10 | 0.70553 | 0.85248 | 1.13650 | 1.36369 | +0.9329 |
| 30 | 0.65711 | 0.80811 | 1.10543 | 1.34103 | +1.0408 |
| 100 | 0.57045 | 0.71174 | 1.01863 | 1.27132 | +1.2286 |
| 300 | 0.47881 | 0.59651 | 0.87196 | 1.12814 | +1.3561 |
| 1,000 | 0.37222 | 0.45555 | 0.67614 | 0.88867 | +1.3875 |
| 3,000 | 0.26699 | 0.33259 | 0.48515 | 0.65581 | +1.4563 |
| 13,090 | 0.14323 | 0.14332 | 0.25840 | 0.35876 | +1.5048 |

Two findings follow, and neither depends on any material choice:

**(a) There is no support-stiffness crossover `k*`.** `S_h > 0` at *every* stiffness across
seven decades. The reversal cannot be switched off by softening the foundation, so it is not
a stiffness effect. Sec. 6's search for `k*` returns **no root exists in the swept range**.

**(b) The model never recovers its own free limit.** At `k_z = 0.001 N/mm³` the foundation is
mechanically absent, so the result must approach the free package. On the identical mesh the
free package gives **8.28732 µm**; `BC_B` gives **0.73914 µm** — smaller by a factor of
**11.2**. A foundation with no stiffness is still suppressing 91 % of the warpage. That
residual suppression is the in-plane clamp, and it is present in every Phase-0C–0F BC-B
result.

The kinematically correct foundation confirms the diagnosis. `BC_BZ` (vertical restraint,
in-plane free) returns **0.19785 µm at h = 0.80 mm and is invariant to `k_z` to five decimal
places across all twelve stiffnesses** — the vertical restraint is rigid by construction, so
`k_z` never enters. `BC_BZ` is therefore a valid `k → ∞` vertical-only bound, not a
stiffness-parameterised model, and it is reported as such.

## 3. The explicit assembly: an opposite regime

An explicit BGA + PCB stack was constructed (`scripts/phase0g/board.py`) from source-backed
geometry — 0.4 mm balls on 0.8 mm pitch, area fraction `π(0.4)²/4/(0.8)² = 0.19635`,
`E_solder = 20 GPa` from the STAMP-2.5D material table — and five board cases spanning
compliant to metal-backed. The package is bonded to it and restrained only by 3-2-1 anchors,
so the assembly is free to bow as a whole.

| h_sub (mm) | BC_A free | BC_B compact | compliant | FR-4 1.6 mm | FR-4 3.2 mm | metal-backed |
|---|---|---|---|---|---|---|
| 0.80 | 11.1708 | 0.3722 | 29.2334 | 25.1482 | 13.8148 | 10.0521 |
| 1.50 | 2.6184 | 0.6761 | 14.8961 | 17.9815 | 12.4137 | 10.1317 |
| 2.00 | 1.2719 | 0.8887 | 9.8448 | 14.0309 | 11.1574 | 9.6630 |

Mounting the package on a real board **amplifies** warpage — to 29.2 µm, 2.6× the free
package — because silicon at 2.6 ppm/K is bonded to FR-4 at ~18 ppm/K and the assembly acts
as a bimetallic strip. The compact BC-B model **suppresses** warpage to 0.37 µm, 30× below
free. The two models are not in quantitative disagreement; they are in **opposite regimes**.

### The thickness ordering

| pair | BC_A | BC_B | compliant | FR-4 1.6 | FR-4 3.2 | metal-backed |
|---|---|---|---|---|---|---|
| S_h(0.8→1.5) | −0.7656 | **+0.8165** | −0.4904 | −0.2850 | −0.1014 | +0.0079 |
| S_h(0.8→2.0) | −0.8861 | **+1.3875** | −0.6632 | −0.4421 | −0.1924 | −0.0387 |

**Every physically constructed assembly gives `S_h < 0` — thicker is better — the same sign
as the free package.** Only the compact clamped foundation reverses it. The single positive
entry, metal-backed at 0.8→1.5 mm, is +0.79 % and reverts to −3.87 % on the wider 0.8→2.0
pair; it is a flat response, not a reversal.

### Limit validation of the explicit model

The compact model fails its own limit test (Sec. 2b). The explicit model passes a
corresponding one. Driving the board towards mechanical absence — 0.1 mm thick, 10 MPa, CTE
matched to silicon — returns the assembly to the free package:

| model at h = 0.80 mm | die warpage (µm) | vs free package |
|---|---|---|
| BC_A, free package (reference) | 11.1708 | — |
| BC_BOARD, vanishing board | 13.1968 | **+18.1 %** |
| BC_BOARD, CTE-matched FR-4 1.6 mm | 2.6729 | −76.1 % |
| BC_BOARD, compliant board | 29.2334 | +161.7 % |
| BC_B, compact foundation, `k → 0` | 0.7391 | **−93.4 %** |

The +18.1 % residual is the BGA layer's own contribution — it remains present, at 3.93 GPa
and 20.5 ppm/K over 0.3 mm, and is not part of the free package. The explicit model is
therefore **continuous with the free package**, and responds correctly to board stiffness
*and* board CTE (a stiff CTE-matched board flattens the package to 2.67 µm). The compact
model is discontinuous with it by a factor of 15.

## 4. Verdict on the assembly boundary

1. **BC-B is not a valid model of a mounted package.** It applies a three-DOF clamp, cannot
   reproduce the free limit as its stiffness vanishes, and sits in the opposite regime to
   every explicit assembly.
2. **There is no support-stiffness crossover `k*`.** The Sec. 6 search returns no root over
   seven decades, because the effect is kinematic, not elastic.
3. **The Phase-0F assembly-state reversal is WITHDRAWN.** It is an artifact of the compact
   foundation's in-plane clamping. It is not reproduced by any board in the calibrated
   envelope, from compliant through metal-backed.
4. **The mechanical thickness preference is thicker-is-better in every physical assembly
   state**, free or mounted, which is the same sign the free package always had.
5. Consequently the Phase-0F term **"ASSEMBLY-STATE-DEPENDENT RESPONSE REVERSAL" is not
   supported**, and the stronger term "ACTIVE MECHANICAL CONSTRAINT" is not supported either
   — see `mechanical_criterion_audit.md` for the separate criterion question.

### What remains PROVISIONAL

The explicit board model is calibrated in geometry and modulus from sources, but its **board
CTE (18 ppm/K), board modulus envelope, and the absence of a solder-mask/copper-plane
laminate structure** are engineering values, not measurements from the reference system. The
finding they support is a **sign and an ordering**, both of which are stable across the full
envelope from compliant to metal-backed; the **magnitudes (9.7–29.2 µm) are not validated**
and must not be quoted as predicted warpage for any real assembly.
