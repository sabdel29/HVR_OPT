# Phase 0H Sec. 3 — Failure-mechanism map for the mounted DVPD architecture

## 1. Why this comes before any search for a limit

Phase 0G asked "is there a warpage limit?" and found none. That was the wrong first question.
Global warpage is an *architectural response*; it is not, on its own, a failure mechanism.
Phase 0H therefore enumerates the mechanisms that could actually end the life of this assembly,
and only then asks which of them the present model can evaluate.

## 2. What the mechanical model actually contains

The structural mesh (`scripts/phase0b/etm/mesh.py`, extended in Phase 0G) is, top to bottom:

| layer | material | discretisation | notes |
|---|---|---|---|
| `tim` | `tim` | continuum | thermal interface |
| `die` | `silicon` | continuum | functional die |
| `interface` | `underfill_homog` | **homogenised continuum** | stands for the die-attach joint layer — microbumps/C4 **and** underfill smeared together |
| `tile_band` | `silicon` + `hvr_effective` + `tsv_homog` inclusions | **homogenised inclusions** | the HVR cells and the via field |
| `sub_lower` | `silicon` | continuum | power substrate |
| `bga` *(mounted only)* | `bga_homog` | **homogenised continuum** | the whole ball array smeared into one layer |
| `board` *(mounted only)* | `board_fr4` | continuum | isotropic laminate |

**Three facts govern everything below.** There are **no discrete solder balls**, **no discrete
microbumps or C4 joints**, and **no RDL layer in the mechanical mesh at all** — the RDL exists
only in the electrical model. Every interconnect is a smeared continuum.

The constitutive model is **M0: linear thermoelastic**, operational load only, stress-free at
25 °C. There is no plasticity, no creep, no viscoelasticity, no cohesive zone and no cyclic
capability. **M1** in this project means only a shifted stress-free reference temperature
(Phase 0G Sec. 11); it is a sensitivity bound, not a pre-stress model.

## 3. The map

### A. Package / global bending
* **Location:** whole assembly; measured at the die top surface and the substrate underside.
* **Load type:** steady-state CTE mismatch under the operating temperature field.
* **State variable:** out-of-plane displacement field `u_z`.
* **Candidate metric:** peak-to-valley warpage `w_pv`; curvature `κ`.
* **Fidelity required:** M0 linear thermoelastic is adequate for the *response*.
* **Computable now?** **YES.** Mesh-converged to 0.50 %, sign-stable across 20 combinations of
  assembly model, reference state and thermal boundary (Phase 0G).
* **Is it a failure mechanism?** **No.** Global bending is a *driver*: it loads the joints. On
  its own it fails nothing. Treating it as the reliability metric is the assumption Sec. 7
  exists to test.

### B. BGA solder-joint fatigue
* **Location:** corner and perimeter balls of the package-to-board array, highest DNP.
* **Load type:** cyclic — power/thermal cycling drives shear across the standoff.
* **State variable:** inelastic (creep + plastic) strain in the joint.
* **Candidate metric:** accumulated inelastic **strain-energy density per cycle** `ΔW`, or
  inelastic strain range `Δγ_in`, mapped to `N_f` through a calibrated life law.
* **Fidelity required:** discrete ball geometry, a temperature-dependent **viscoplastic** solder
  model, a defined thermal excursion, and cycling to a stabilised hysteresis loop.
* **Computable now?** **NO.** The ball array is a single homogenised elastic layer, and M0 has
  no inelasticity. This is the mechanism most likely to actually limit a large mounted package,
  and it is exactly the one the present model cannot see.

### C. Microbump / C4 strain
* **Location:** die-to-substrate joints, again worst at greatest distance from neutral point.
* **Load type:** steady shear from in-plane CTE mismatch; cyclic in service.
* **State variable:** relative in-plane displacement across the joint layer; joint shear strain.
* **Candidate metric:** relative interface displacement `Δu`; smeared interface shear `τ`.
* **Fidelity required:** discrete bumps for a per-joint strain; a smeared layer gives only an
  average.
* **Computable now?** **PARTIALLY.** `interface_shear_MPa` and `rel_disp_max_um` exist and
  interface shear passed mesh convergence (8.7 %/9.3 % at M3→M4). But they are **smeared over
  the homogenised joint layer**, so they are a *loading indicator*, not a joint strain. No
  allowable exists for them.

### D. RDL dielectric or metal damage
* **Location:** redistribution layers carrying lateral current under the die.
* **Load type:** in-plane shear and thermal strain; the RDL is the stiffness discontinuity
  June-2026 names explicitly.
* **State variable:** in-plane strain in the RDL metal and dielectric; interfacial shear.
* **Candidate metric:** RDL interfacial shear; dielectric crack driving force.
* **Fidelity required:** the RDL must exist in the mechanical mesh, with layer-resolved metal
  and dielectric.
* **Computable now?** **NO.** The RDL is not in the structural model. This is a genuine
  asymmetry in the project: the RDL dominates the *electrical* result and is mechanically absent.

### E. Die / low-k chip-package interaction
* **Location:** die back-end stack, worst at die corners.
* **Load type:** in-plane stress transferred from the package.
* **State variable:** die first principal stress `σ₁`; back-end-of-line interfacial energy.
* **Candidate metric:** `σ₁` p99 in silicon; low-k delamination driving force.
* **Fidelity required:** for `σ₁` in bulk silicon, M0 is adequate *only if* the local geometry
  is resolved; for BEOL/low-k, a sub-model is required.
* **Computable now?** **NO, not defensibly.** `si_principal_MPa` is computed, but Phase 0B
  established that homogenisation is **invalid for local stress** (+82 to +97 % bias) while
  remaining valid for warpage. The number exists; it may not be used for decisions.

### F. Interface delamination
* **Location:** underfill free edge, die corner, and any bimaterial corner.
* **Load type:** peel and shear at a bimaterial corner — a theoretical stress singularity.
* **State variable:** energy release rate `G`, mode mixity `ψ`.
* **Candidate metric:** `G` against interface fracture toughness `G_c`.
* **Fidelity required:** fracture mechanics — VCCT or a cohesive zone. A stress metric at a
  singular corner cannot converge, by construction.
* **Computable now?** **NO.** Interface **peel** was measured and did **not** converge
  (19.2–20.1 % per refinement against a <10 % target) precisely because it is a corner
  singularity, and it was excluded from all decision logic in Phase 0C. Phase 0H does not
  resurrect it: a non-convergent stress is the wrong quantity, and the right one (`G`) is not
  implemented.

### G. TSV / landing-pad mechanical interaction
* **Location:** copper vias in the silicon substrate and their landing pads.
* **Load type:** CTE mismatch between copper (16.6 ppm/K) and silicon (2.6 ppm/K).
* **State variable:** near-via stress field; keep-out-zone criterion for adjacent devices.
* **Candidate metric:** von Mises in the via region; radial/hoop stress at the Si interface.
* **Fidelity required:** discrete via geometry; the KOZ criterion is device-specific.
* **Computable now?** **NO, not defensibly.** `tsv_region_vm_MPa` exists but is computed on a
  **homogenised** via field, and the same homogenisation bias that invalidates local silicon
  stress applies here.

### H. Mechanisms named by June-2026
The reference paper names three, in its own words (Sec. I): *"global package warpage,
delamination risk, and shear stress in the redistribution layer (RDL)"*.

| June-2026 mechanism | this map | computable? |
|---|---|---|
| global package warpage | **A** | YES — but it is a driver, not a failure |
| delamination risk | **F** | NO — needs fracture mechanics |
| RDL shear stress | **D** | NO — the RDL is not in the mechanical mesh |

**Two of the three mechanisms the reference system itself cares about are outside the present
model.** That is the single most important structural finding of this section.

## 4. Summary

| # | mechanism | computable at M0? | blocking requirement |
|---|---|---|---|
| A | global bending | **YES** | — (but it is a response, not a failure) |
| B | BGA solder fatigue | NO | discrete balls + viscoplasticity + cycling |
| C | microbump / C4 | PARTIAL (smeared) | discrete bumps for a true joint strain |
| D | RDL damage | NO | RDL absent from the mechanical mesh |
| E | die / low-k CPI | NO | homogenisation invalid for local stress |
| F | delamination | NO | fracture mechanics (VCCT / cohesive zone) |
| G | TSV interaction | NO | discrete vias; homogenisation bias |
| H | June's three | 1 of 3 | see above |

**One mechanism of eight is computable, and it is the one that is not a failure mechanism.**

This is the honest state of the model, and it sets the agenda for Sec. 8–10: any candidate
reliability metric must either be computable on the smeared model (C, weakly) or trigger an
explicit statement that the required fidelity does not exist. It also explains why Phase 0G
found no criterion: the project has been measuring the load, not the damage.
