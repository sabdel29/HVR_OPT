# Phase 0I Sec. 12/13/14 — Solver audit, submodel, and validation

## 1. Sec. 12 — solver capability, verified rather than assumed

CalculiX 2.23 was inspected and then **tested**, because the brief forbids assuming support:

| capability | present? | evidence |
|---|---|---|
| `*PLASTIC` with temperature-dependent tables | **yes** | ran |
| `*CREEP, LAW=NORTON`, temperature-dependent | **yes** | ran |
| `*VISCO` step procedure | **yes** | ran |
| `*CYCLIC HARDENING`, `*RATE DEPENDENT` | present | not used |
| `*SUBMODEL` | present | not needed — displacement-driven submodelling used instead |
| **Anand viscoplasticity** | **NO** | not in the keyword set |
| **user creep subroutine** | **NO** | would need the solver recompiled |
| **cohesive-zone fracture** | **NO** | — |

**Capability probe.** A single C3D8 solder cube under cyclic shear in `*VISCO` steps:
stress reversed **+90.73 / −91.51 MPa**, PEEQ accumulated **monotonically** from 9.85 × 10⁻⁵
to 1.82 × 10⁻², and stress **relaxed 38.0 % during a constant-strain hold**. Hysteresis,
plastic accumulation and creep relaxation all present. The reliability branch is not blocked.

`results/phase0i/solver_audit/`.

## 2. Sec. 13 — the global → local flow

```
GLOBAL package model (architecture-specific stack, mounted on the explicit board)
        |
        |  du(t)  relative in-plane displacement across the corner-BGA standoff
        |  T(t)   joint temperature
        v
LOCAL joint submodel: Cu pad / SAC305 / Cu pad, explicit
        |
        v
Delta-eps_in per stabilised cycle, volume-averaged with a corner exclusion band
```

The local geometry is June-2026's own BGA — 400 µm ball, 300 µm standoff, 800 µm pitch —
represented by an **equal-area square prism** of side 354.49 µm, the same convention Phase 0G
used to homogenise the ball array, so the local and global models describe the same amount of
solder. Pads are 400 µm and overhang the solder, so the solder free edge is a genuine
bimaterial corner. That is deliberate: the metric has to survive a corner, not avoid one.

## 3. Sec. 14 — validation, all four checks

| # | check | result | verdict |
|---|---|---|---|
| 1 | **free thermal expansion** — solder-only block on 3-2-1 supports, ΔT = 100 K | u_x = 6.450000 × 10⁻⁴ mm against α·ΔT·L = 6.450000 × 10⁻⁴ mm, **0.000 % error**; PEEQ = 0 | **PASS** |
| 2 | **monotonic temperature dependence** | creep rate at 10 MPa rises **535×** over 25→125 °C; yield falls 24.5 → 10.5 MPa; E falls 45 → 33 GPa | **PASS** |
| 3 | **creep relaxation at constant strain** | mean \|σ_xz\| falls 5.587 → 2.816 MPa over a 600 s hold, **−49.6 %** | **PASS** |
| 4 | **cycle stabilisation** | per-cycle Δε_in = 4.975e−3, 6.269e−3, 6.117e−3, 6.051e−3, 6.025e−3 — last-to-previous change **0.4 %** | **PASS** |

A note on check 1: its first version heated the *full* pad/solder/pad joint with the bottom
face clamped and "failed" with PEEQ = 3.4 × 10⁻³. That was a defective test, not a defective
model — a clamped assembly of two materials with different CTEs *should* yield. The check is
only meaningful on unconstrained single-material solder, and it is exact there.

## 4. Sec. 11 — convergence of the metric

| axis | levels | result |
|---|---|---|
| **mesh** | 152 → 248 → 488 elements | Δε_in = 6.139e−3 → 6.051e−3 → 5.937e−3; final step **1.90 %** (target < 10 %) |
| **creep tolerance** | CETOL 5e−2 → 1e−2 | **0.02 %** change — the tolerance is not controlling the answer |
| **corner exclusion band** | 0, 1, 2 elements | 5.799e−3 → 5.937e−3 → 6.170e−3, a **6.4 %** span |

Two things to record honestly:

* The finest mesh attempted (8 × 10, ~900 elements) **stalled**, so convergence is demonstrated
  over three levels rather than four. The trend is monotone and the final step is well inside
  target, but the fourth level is missing.
* Including the corner elements gives a *lower* value than excluding them, so this metric is
  **not** dominated by the corner — the opposite of the peel metric Phase 0C had to exclude
  (19–20 % per refinement) and the p99 shear Phase 0H found non-monotone (7.6 % spread).

**This is the first local mechanical metric in the project that passes mesh convergence,
tolerance insensitivity and regularisation stability together.**

## 5. Sec. 15 — the thermal → damage chain, demonstrated

The chain the brief requires is explicit, and every link is exercised:

`T(x,y,z)` → `E(T)`, `σ_y(T)`, `A(T)`, `n(T)` → cyclic viscoplastic deformation → `Δε_in`

Temperature does not merely enter as `α·ΔT`. It sets the stiffness, the flow stress and the
creep rate, the last through an Arrhenius factor worth **535×** over the operating range.
Sec. 17 isolates how much that matters.

## 6. Residual limitations

* The submodel is **displacement-driven**, so the correlation between the imposed `du` and the
  resulting damage is near-perfect **by construction** (r = 1.000). What is informative is
  whether *global warpage* predicts `du`, not whether `du` predicts damage.
* A single joint is modelled, at the worst location. Joint-to-joint variation is not captured.
* The Norton surrogate is valid over **7.5–16 MPa**; work occurring outside that window is not
  faithfully represented.
* No intermetallic layer, no voids, no aging.
