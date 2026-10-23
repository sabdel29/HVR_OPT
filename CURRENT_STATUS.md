# CURRENT STATUS

**Date of this snapshot:** 2026-10-08
**State:** PAPER-FROZEN at Phase 0M-R3C, plus the final TCPMT reviewer-hardening pass.
**Tag:** `paper-freeze-r3c`

Every number below was re-verified against its source artifact at snapshot time, not copied
from notes. Reproduce the verification with the commands in section 7.

---

## 1. Manuscript

**Title**

> Electrothermal–Mechanical Co-Design of Distributed Vertical Power Delivery:
> Architecture-Dependent Inelastic Response and Physical Realizability

`manuscript/ETM_DVPD_JOURNAL_MANUSCRIPT.tex` → `.pdf`
15 pages · 0 LaTeX errors · 0 undefined references · 0 overfull boxes · 25 references
8 figures · 9 tables · target venue IEEE TCPMT

Readiness: **ready for coauthor / advisor technical review**. Not submitted. The open items
are human decisions (author list, venue formatting and page limit, ratifying the title
change, two reference page ranges) — see `manuscript/TCPMT_PRE_SUBMISSION_STATUS.md`.

---

## 2. The frozen final pair

1 kW, 48 V → 1 V, 49 regulator cells, hybrid 3:1 switched-capacitor + **two-phase** buck with K=3 parallel inductor branches (K_A=2 driven in phase A, K_B=1 freewheeling).

| quantity | Z1 embedded | Z2 backside |
|---|---:|---:|
| P_electronics (W) | 137.292 | 139.659 |
| T_max (°C) | 118.32 | 126.46 |
| mean die T (°C) | 93.41 | 95.41 |
| die warpage, P–V (µm) | 41.616 | 38.916 |
| package warpage, P–V (µm) | 77.024 | 72.039 |
| corner-joint temperature (°C) | 112.75 | 120.30 |
| Δu_c, displacement driver (µm) | 4.6252 | 3.8714 |
| Δε_in, inelastic response (/cycle) | 1.4072×10⁻² | 1.1478×10⁻² |

    D_u = 1.1947      displacement-driver ratio
    D_ε = 1.2260      inelastic-response ratio

**Reading — and its limits.** On the frozen geometry Z2 runs 8.14 K hotter, carries 16.3 %
lower displacement driver and 18.43 % lower local inelastic response. **None of these is an
architecture-level result**: the frozen pair does not isolate placement, because Z2's
backside is a full-area converter slab (1103.40 mm³) against Z1's 337.02 mm³. Over the three
surrogate backside fills tested the Δu_c reduction spans 3.6–65.6 % and **ΔT changes sign**.
Peak temperature is therefore not sufficient to infer local mechanical response — the
surrogates include cases where the two rankings diverge — but whether the physically closed
Z1/Z2 implementations show that reversal is **unresolved**.

Source: `results/phase0mr3c/final_etm_replay.csv`, `final_local_response.csv`,
`local_submodel_inputs.csv`.

---

## 3. Physical realizability

| tier ordering | worst build-up via aspect ratio |
|---|---:|
| reference | **5.05** |
| repartitioned | **0.833** |

Only the tier *locations* of existing components were permuted. Component set, component
count, per-tier area budget and total stack height are unchanged. The stack height is
1921 µm with the frozen device heights and **1953 µm** with the selected devices
(EPC2014C 685 µm, EPC2057 638 µm); the baseline worst AR correspondingly becomes **5.32**,
because that net crosses the low-side tier. The repartitioned 0.833 is unaffected.

Status: the **VERTICAL INTERCONNECT** is GEOMETRICALLY REALIZABLE / PROCESS-CONDITIONAL.
Explicitly **not** manufacturing-qualified — the microvia current allowable, the capture-pad
diameter, a vendor design rule and two package clearance rules remain unavailable.

**This status does NOT extend to the package.** Component-stack and board-assembly
realizability are **NOT ESTABLISHED** for either architecture: Z1's 1.30 mm substrate is
8 µm short with the corrected low-side height and omits its 685 µm high-side device; Z2's
land-side stack is 1963 µm and needs a PCB through-cutout that is patent-precedented but
dimensionally unsourced. See `research/Z2_CUTOUT_GEOMETRY.md`.

Source: `results/phase0mr3c/routing_feasibility.csv`, `repartition_candidates.csv`.

---

## 4. Integration-tolerance robustness (CETOL)

Five tolerances tested on the final pair, everything else held fixed:

| CETOL | converged | D_ε |
|---|---|---|
| 1e-5 | no — zero increments | — |
| 1e-4 | no — zero increments | — |
| 1e-2 | no — zero increments | — |
| **5e-2** | yes | **1.226006** |
| **1e-1** | yes | **1.226006** |

The two converged solves are identical to twelve digits on Δε_in, its range and the inelastic
work, for both architectures, with the same increment count and zero cutbacks. Doubling the
tolerance moves the result by nothing.

**The bracket is one-sided.** No tighter tolerance converges at this operating point, so
agreement with a tight-tolerance reference is not demonstrated and is not claimed.

Source: `results/phase0mr3c/cetol_final_pair.csv`,
`manuscript/CETOL_FINAL_PAIR_ROBUSTNESS.md`.

---

## 5. What is proven, conditional, and not claimed

**Proven (ordering-level):**
* Rail assignment, not via geometry alone, governs vertical interconnect loss. The same
  through-substrate field dissipates ≈0 W carrying 48 V and 0.991 W carrying 1 V.
* Physical realizability is an **active architecture/synthesis constraint**: two tier orders
  equivalent in component set, area and stack height differ 6× in worst via aspect ratio.
* Peak temperature is **not sufficient** to infer local mechanical response: the response
  depends additionally on geometry, stiffness distribution, boundary conditions and local
  joint loading, and the surrogate set includes cases where the two rankings diverge.
* The **method** — global thermoelastic field driving a local displacement-driven solder
  submodel, with response, damage, life and failure kept separate.

**Conditional:**
* **Every Z1/Z2 number below is geometry-conditional, and the geometry they were produced
  on has since been replaced.** The numbers in this document come from the Phase-0M-R3C
  lineage, in which Z1 omits its 685 µm high-side device entirely (its 1226 µm homogenized
  band structurally excludes it) and Z2's backside construction, lateral cell extent and
  board interface are undefined.

  Phase 0N-W has now built both architectures physically — 49 discrete cells, the full
  1963 µm Z2 and 1973 µm Z1 tier stacks with the high-side device explicitly present, on a
  source-backed IT-968G board — but **no electrothermal or mechanical result has been run
  on that geometry**. The live gate table, regenerated from the config and the meshes on
  every run, is `research/PHYSICAL_Z1_Z2_IMPLEMENTATION_AUDIT.md`; it is the single source
  for which gates are closed, and no gate count is repeated here precisely because a
  second copy would go stale. Until that table shows zero OPEN gates and a physical result
  lineage exists, **every Z1/Z2 number in this document remains the old-geometry result**.
* Δu_c remained lower for Z2 across all three surrogate backside treatments; whether that
  ordering survives a physically closed backside package **remains to be established**.
* The **magnitude** of the 18.43 % separation. The solder Norton card is fitted over
  7.51–15.92 MPa while the final joints operate at 15–17× yield — roughly an order of
  magnitude above the top of the fitted window. Ordering robust, magnitude an envelope.
* Absolute temperatures: the cooling model is validated at its laminar operating point only.
* Absolute efficiency: inductor core loss and capacitor dielectric loss are not evaluated.
* α_GaN = 7.5×10⁻³ /K is an **adopted calibration coefficient**, not a sourced constant.

**Explicitly NOT claimed:**
* No damage, no fatigue life, no cycles-to-failure, no failure probability, no mechanical
  pass/fail. Δε_in is a **response**, not damage.
* No claim that either architecture is manufacturable or qualified.
* No claim that mechanics changes the system optimum — no admissible mechanical allowable
  exists, so mechanics is design-relevant but not an established synthesis constraint.
  (Physical realizability **is** established as one.)
* No conjugate CFD validation — attempted, discarded.
* No converged full-wave (HFSS) result — attempted, did not converge.
* No optimizer result. The framework is an evaluator, not an optimizer.

---

## 6. Open research items

* SAC305 characterisation at the stresses these packages actually generate — the single
  change that would convert the response magnitude from envelope to result.
* An admissible mechanical allowable, and with it a damage law and life relation.
* Conjugate CFD for absolute temperatures.
* Microvia current allowable, capture-pad geometry and a vendor design rule — required
  before any manufacturability claim.
* Inductor core loss and capacitor dielectric loss for absolute efficiency.

---

## 7. Verification commands

    export PATH=/home/beams0/MGHARIB/envs/etm/bin:$PATH
    cd <repo root>

    # manuscript audit: 82 numerical values against frozen artifacts
    python scripts/phase0mr3c/audit_manuscript.py          # → MANUSCRIPT AUDIT PASSED

    # regenerate the generated claim audit
    python scripts/phase0mr3c/write_claim_audit.py

    # framework-level audits
    python scripts/phase0mr3/semantic_audit.py             # → 0 findings
    python scripts/phase0lr/cross_report_consistency.py    # → 58/58
    python scripts/phase0m/pdf_text_inspect.py             # → ALL PDF TEXT CHECKS PASS

    # rebuild the manuscript
    cd manuscript && pdflatex ETM_DVPD_JOURNAL_MANUSCRIPT && bibtex ETM_DVPD_JOURNAL_MANUSCRIPT \
      && pdflatex ETM_DVPD_JOURNAL_MANUSCRIPT && pdflatex ETM_DVPD_JOURNAL_MANUSCRIPT

    # tests — run these ONE AT A TIME, never concurrently
    python -m pytest tests/phase0mr3c -q
