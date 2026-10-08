# Phase 0I — Vertical-Integration Architecture and Reliability-Physics Gate

**Verdict: ARCHITECTURE-DEPENDENT RELIABILITY RESPONSE — NO ACTIVE CONSTRAINT**
**G2: testable in form for the first time, but still NOT TESTED — no admissible life law and
no mission requirement.**
**The global ETM optimizer was not built and is not recommended.**

---

## 1. What Phase 0I set out to do

Phase 0H concluded *no admissible mechanical criterion — response coupling only*, and was
explicit that this applied to the M0 thermoelastic model and the architectures actually
modelled. Two things were left open, and both turned out to matter:

1. **The converter does not have to be inside the substrate.** Its vertical position is an
   architecture variable that the project had never varied *mechanically*.
2. **The mechanical model contained no failure physics.** It computed elastic deformation, not
   damage.

Both are now closed. Neither produced an active constraint, but both changed what the project
can say.

## 2. DEFECT #33 — realizability was architecture-blind

`kw1.design_1kw()` takes no architecture argument, so the embedded rule
`t_cell + h_tsv ≤ h_sub` was applied to **every** architecture. At `h_sub` = 0.30 mm the code
answers *"no inductor fits h_sub=300 um (budget 30 um)"* for ARCH_A, ARCH_B and ARCH_C alike —
but ARCH_B converts *below* the substrate and ARCH_C *beside* the die. Neither puts the
inductor inside `h_sub`.

The electrical model has varied the converter's z-position since Phase 0D-R. The geometric and
mechanical models never did.

**Consequence: the Phase-0H bound `h_sub,min` = 1.176–1.426 mm is EMBEDDED-SPECIFIC.**

| | Z1 embedded | Z2 backside | Z4 power die | Z5 2.5D |
|---|---|---|---|---|
| `h_sub,min` | **1.276 mm** (MLCC nominal) | **0.300 mm** | **0.300 mm** | **0.300 mm** |
| rule | components must fit inside | source-demonstrated TSV layer (June Table III: d = 30 µm at h = 300 µm, AR 10:1) | same | same |

A **4.3× wider** thickness range for every non-embedded architecture, including exactly the
thin region the corrected electrical model prefers.

The reference paper supports this directly. It describes its architecture as *"vertically
stacked **in-substrate AND backside** VR components"*, states that chiplet VRs *"can be
vertically stacked on the **backside** of a substrate and interconnected through TSVs"*, and
records that the embedded multi-layer option *"**remains an open challenge**"*.

## 3. Which rail crosses the TSV is an architecture choice

| architecture | conversion relative to the substrate | TSV rail | TSV current | n_TSV |
|---|---|---|---|---|
| Z1 EMBEDDED | inside, above the via field | HV | 23.43 A | 332 |
| Z2 BACKSIDE | below | **LV** | **1000 A** | **14 148** |
| Z4 POWER DIE | above | HV | 23.43 A | 332 |
| Z5 2.5D | above, lateral | HV | 23.43 A | 332 |

A factor of 42.7 in current — 1822 in I² — decided purely by z-placement.

**An unplanned cross-check.** Z2 needs **14 148** TSVs to carry 1000 A under the source-backed
current density. June-2026 Table III independently reports **14 148** TSVs for PL3 in its own
optimised 48 V→1 V allocation. Two different pieces of machinery, exact agreement.

## 4. Electrical result

| architecture | best realizable h | P_TSV | P_RDL | **P_total** | η |
|---|---|---|---|---|---|
| Z1 EMBEDDED | 1.30 mm | 0.0098 W | 0.6451 W | **126.090 W** | 88.803 % |
| Z4 POWER DIE | 0.30 mm | 0.0397 W | 0.6451 W | **126.120 W** | 88.801 % |
| Z2 BACKSIDE | 0.30 mm | 1.6979 W | 0.6451 W | **127.778 W** | 88.670 % |
| Z5 2.5D LATERAL | 0.30 mm | 0.0397 W | **768.07 W** | **893.547 W** | 52.811 % |

Z1 keeps a **30 mW** edge over Z4 — 0.024 % — purely because its embedded cell shortens the
via field to 74 µm. Z5 is eliminated: 768 W of lateral loss is precisely the penalty DVPD
exists to avoid, and it quantifies the concept's value.

## 5. Reliability physics, built and validated

**Solver (Sec. 12).** CalculiX 2.23 has `*PLASTIC`, `*CREEP,LAW=NORTON` and `*VISCO`, and has
**no Anand model and no user-creep hook**. Verified by running: a solder cube under cyclic
shear reversed stress ±91 MPa, accumulated PEEQ monotonically, and relaxed **−38.0 %** during
a constant-strain hold.

**Material (Sec. 9).** SAC305 only; SnAgCuCe and SAC405 Anand sets found and rejected for
being different alloys. Yield σ₀(T) and Chaboche hardening from Yuan (2023) Table 31; creep
fitted **directly to 19 measured points** at 45/80/115/150 °C (Yuan Table 26) because a single
Norton power law cannot span Garofalo's curvature (effective exponent 3.1 at 2 MPa to 19.2 at
30 MPa; 253 % RMS over 1–30 MPa). Per-temperature fits: **4.1–12.2 % RMS**, valid 7.5–16 MPa.

Two independent cross-checks passed: yield σ₀(25 °C) = 24.46 MPa against a measured
23.3–25.6 MPa, and the fitted card's apparent activation energy **64.4 kJ/mol** against a
published 62.0 and 65.0.

**Validation (Sec. 14).** 4/4: free expansion exact to 0.000 % with zero inelastic strain;
creep rate ×535 and yield −57 % over the operating range; **−49.6 %** stress relaxation in a
600 s hold; cycle stabilisation to **0.4 %**.

**Convergence (Sec. 11).** Mesh **1.90 %** over the final step, CETOL **0.02 %**, corner
exclusion band **6.4 %** across 0–2 elements — and including the corner *lowers* the value, so
the metric is not corner-dominated. **This is the first local mechanical metric in the project
to pass mesh, tolerance and regularisation stability together**, against interface peel
(19–20 %/step, excluded in 0C) and p99 shear (non-monotone, rejected in 0H).

## 6. Does temperature-dependent physics change the damage? (Sec. 17)

| model | Δε_in per stabilised cycle | vs A |
|---|---|---|
| **A** temperature-INDEPENDENT (the Phase-0H class; still has α·ΔT) | 8.214 × 10⁻³ | — |
| **B** T-dependent E and yield, no creep | 8.524 × 10⁻³ | +3.8 % |
| **C** FULL: E(T), σ_y(T), thermally activated creep | **5.980 × 10⁻³** | **−27.2 %** |

**Yes, materially.** And the sharper result is the mean-temperature sweep at a fixed 100 K
swing:

| model | Δε_in at T_mean 25 °C → 75 °C | change |
|---|---|---|
| A temperature-independent | 8.217e−3 → 8.207e−3 | **−0.2 %** |
| C full physics | 5.463e−3 → 6.702e−3 | **+22.7 %** |

The old model class is **structurally blind** to where in temperature a cycle sits. The new one
is not. That is exactly the physics Phase 0H identified as missing.

## 7. Architecture comparison (Sec. 16)

At each architecture's own electrically best realizable point:

| architecture | h* | P_elec | ΔP vs Z1 | T_joint | Δu corner | **Δε_in** | vs Z1 |
|---|---|---|---|---|---|---|---|
| Z1 EMBEDDED | 1.30 mm | 126.090 W | — | 82.86 °C | 2.749 µm | 6.512e−3 | — |
| Z2 BACKSIDE | 0.30 mm | 127.778 W | **+1.688 W** | 81.85 °C | 2.080 µm | **4.179e−3** | **−35.8 %** |
| Z4 POWER DIE | 0.30 mm | 126.120 W | +0.030 W | 81.10 °C | 2.984 µm | **7.320e−3** | **+12.4 %** |

**There is a real, material, architecture-dependent reliability response, and it opposes the
electrical preference.** Z2 is the gentlest on the joint and the most expensive electrically;
Z4 is electrically almost free and the most damaging.

Relative life, parameter-free in the life-law constant (`N_f = C·Δε^{−k}`, C cancels):

| k | Z1 | Z2 | Z4 |
|---|---|---|---|
| 1.5 | 1.000 | **1.945** | 0.839 |
| 2.0 | 1.000 | **2.428** | 0.791 |
| 3.0 | 1.000 | **3.783** | 0.704 |

Z2 buys **1.9–3.8× life for 1.688 W** (1.3 % of the electrical budget). Whether that is a good
trade cannot be decided here — that requires a mission requirement, and none exists.

## 8. The twelve required answers

1. **Does component height constrain substrate thickness for every architecture?**
   **No.** Only for the embedded architecture. For Z2, Z4 and Z5 *nothing* the converter
   contains constrains `h_sub`.
2. **Which architectures permit thin substrates?** Z2, Z4 and Z5, all down to the
   source-demonstrated 0.30 mm — 4.3× thinner than the embedded floor of 1.276 mm.
3. **Which rail crosses the TSV?** HV (23.4 A) for Z1, Z4 and Z5; **LV (1000 A) for Z2**.
4. **Where is the dominant heat generated?** The compute die, 1000 W against the converter's
   125 W. June-2026 adds that >70 % of *converter* loss is in the switches.
5. **How does HVR z-location change the through-thickness temperature field?**
   **Far less than expected.** The corner-joint temperature spans only 81.10–83.21 °C across
   every architecture and thickness. Z4's converter-in-the-thermal-path concern does not
   materialise at the joint.
6. **How does thermal cycling change the local mechanical response?** It drives the whole
   damage process: each OFF→ON→OFF cycle produces a closed hysteresis loop with stress
   relaxing during every dwell and inelastic strain accumulating monotonically.
7. **Does temperature-dependent material behaviour materially change the damage metric?**
   **Yes: −27.2 % in magnitude, and it introduces a +22.7 %/50 K mean-temperature sensitivity
   that the previous model class could not represent at all (−0.2 %).**
8. **Which interconnect is mechanically most critical?** The **BGA**, in all three
   architectures — 400 µm ball at up to 15 mm from the neutral point across a silicon-to-FR-4
   mismatch. Microbumps, Cu pillars and hybrid bonds are all silicon-to-silicon or tiny-DNP.
9. **Does global warpage correlate with the local damage metric?**
   **Within an architecture, perfectly** (Spearman +1.000 in all three). **Pooled across
   architectures, +0.909 rank / +0.749 linear.** This partly *reverses* Phase 0H, which found
   no correlation — because Phase 0H's local metric was smeared shear in a homogenised layer,
   a poor proxy, whereas corner-BGA relative displacement is the actual kinematic driver.
   **But warpage systematically overstates the benefit**: over the same thickness range
   warpage changes 29.7–52.6 % while damage changes only 5.6–17.2 %, a 3–5× exaggeration.
10. **Does any architecture have a reliability disadvantage large enough to alter design
    preference?** **Yes, potentially.** Z2 offers 1.9–3.8× relative life for +1.688 W, and Z4
    loses 16–30 % of life for +0.030 W. Whether that alters the preference depends on a
    required life that does not exist yet — which is precisely why the verdict is *no active
    constraint* rather than *constraint proven*.
11. **Is substrate thickness electrically/mechanically opposed under local reliability?**
    **Yes, in all three architectures** — electrical prefers thin, damage prefers thick. But
    the opposition is **much weaker in damage than in warpage**: Z1 gains 5.6 % damage for
    +0.093 W, Z2 6.1 % for +9.622 W, Z4 17.2 % for +0.225 W.
12. **Can G2 finally be tested?** **In form, yes; in fact, no.** For the first time the
    project has a convergent, validated, failure-relevant local metric — the missing half of
    `g_mech(x) ≤ g_allow`. What is still missing is `g_allow`: no admissible SAC305 life law
    could be retrieved (publisher 403s) and no mission requirement exists for the reference
    system. **G2 remains NOT TESTED, but for a different and narrower reason than in Phase
    0H.**

## 9. Verdict, and why not the alternatives

**ARCHITECTURE-DEPENDENT RELIABILITY RESPONSE — NO ACTIVE CONSTRAINT**

| alternative | why not |
|---|---|
| RELIABILITY CONSTRAINT PROVEN — MECHANICS ENTERS SYNTHESIS | no admissible life law, no mission requirement. A constraint needs both halves of an inequality. |
| GLOBAL WARPAGE DOES NOT TRACK LOCAL DAMAGE | it *does* track — perfectly within an architecture, +0.909 pooled. The defensible statement is that it **overstates** the benefit 3–5×, not that it fails to track. |
| NO MATERIAL RELIABILITY EFFECT FOUND | there is one: 35.8 % in damage and 1.9–3.8× in relative life between architectures. |
| INSUFFICIENT MATERIAL / MISSION DATA | true of the *life law* and the *mission*, but the constitutive model **was** sourced, validated and cross-checked, and a real architecture-dependent response **was** measured. Reporting insufficiency would understate what the phase established. |

## 10. What would turn this into a constraint

1. **A SAC305 life law** — `N_f = f(Δε_in)` with its constants and metric definition. The two
   candidate open-access sources return HTTP 403 here.
2. **A mission requirement** — cycles-to-survive for the target product. Not published for the
   reference system, and inventing one is forbidden.

With both, `N_f(x) ≥ N_required` becomes writable, and Sec. 20's parametric sweep says the
answer would hinge on `k` and on how tight `N_required` is.

## 11. Recommended Phase-0J scope (Sec. 22 — do not start automatically)

The solder branch completed and produced a usable metric, so a second mechanism is now
justified. In priority order, from what this phase actually observed:

1. **Acquire the life law and mission profile.** Higher value than any new physics.
2. **RDL / interposer damage.** Still absent from the mechanical mesh entirely, and it is one
   of the three mechanisms June-2026 names. Z4 and Z5 load it hardest.
3. **Cohesive-zone delamination.** The remaining June-named mechanism, and the convergent
   replacement for the peel metric excluded since Phase 0C.
4. **Joint-to-joint variation.** Only the worst joint is modelled here.

## 12. Artifacts

| artifact | section |
|---|---|
| `Z_ARCHITECTURE_MATRIX.md`, `../configs/phase0i/z_architectures.yaml` | 2, 3 |
| `REALIZABILITY_BY_Z_ARCHITECTURE.md` | 5 |
| `POWER_PATHS_BY_Z_ARCHITECTURE.md`, `power_paths_by_architecture.csv` | 4 |
| `THERMAL_TOPOLOGY_BY_Z_ARCHITECTURE.md`, `transient_thermal.json` | 6, 7 |
| `SOLDER_RELIABILITY_LITERATURE_AUDIT.md`, `solder_literature_raw.csv` | 8, 9 |
| `reliability_material_model.yaml` | 9 |
| `local_metric_predeclaration.md` | 10, 11 |
| `local_submodel_validation.md`, `joint_validation.json`, `solver_audit/` | 12, 13, 14 |
| `local_metric_convergence.csv` | 11 |
| `transient_thermal_validation.md` | 7 |
| `z_architecture_electrical.csv`, `z_architecture_comparison.csv` | 4, 16 |
| `thickness_by_architecture.csv` | 19 |
| `temperature_dependent_damage_test.csv` | 17 |
| `reliability_constraint_sensitivity.csv` | 20 |

Figures `FIG_0I_A` … `FIG_0I_I` (9).

### Known residuals

* **No life law, no mission profile.** No `N_f` is predicted anywhere.
* **The submodel is displacement-driven**, so the Δu–damage correlation is near-perfect by
  construction; what is informative is warpage → Δu.
* **The Norton surrogate is valid over 7.5–16 MPa only**; Anand exists for SAC305 but the
  solver cannot evaluate it.
* **E(T) slope and CTE are assumptions**; only a room-temperature modulus range is sourced.
* **The finest mesh (8×10) stalled**, so convergence rests on three levels, not four.
* **One joint, worst location.** No joint-to-joint variation, no intermetallics, no voids, no
  aging.
* **`rho·cp` is a handbook assumption**, used only for the time constant.
* **MLCC height is still OPEN**, so the embedded bound remains a 250 µm band.
