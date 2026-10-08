# Phase 0D-R — Architecture-Aware PPDN + Independent-Solver Validation Gate

**Date:** 2026-09-05 · **Supersedes:** `results/phase0d/PHASE0D_ET_TO_ETM_REVERSAL_GATE.md` where they disagree
**Solvers:** CalculiX 2.23 C3D8I (thermal + structural) · MOOSE `heat_transfer-opt` (independent FE cross-check) · upstream `compute_total_loss` (converter, unmodified)
**ANSYS:** installed but **licence unavailable** — see §10

---

## 1. Executive Verdict

# PHASE-0D CONCLUSION CHANGED BY CURRENT-PATH AND PPDN CORRECTION

Two Phase-0D conclusions do not survive. One does. The net effect is that the ETM case is
**weaker, not stronger**, than Phase 0D reported.

### Sub-verdicts

| Lever | Phase-0D conclusion | Phase-0D-R conclusion | status |
|---|---|---|---|
| **Substrate thickness** | thicker better on all 3 domains | **unchanged** — −1.0 % electrical, −2.75 K, −56.5 % warpage | **CONFIRMED** |
| **Placement** | "ET is blind to placement" (1.08 % electrical spread) | **electrical spread is 189 %, not 1.08 %** | **OVERTURNED** |
| **HVR footprint** | larger → lower loss, higher warpage | opposition survives, but RDL now co-determines it | **QUALIFIED** |
| **Converter loss** | outcome of area budget, ±10.8 % warpage leverage | unchanged | CONFIRMED |
| **RDL** | lumped `ρ/(t·W_die)`, P ≈ 0.17 W | 2-D sheet solve, **P ≈ 12–73 W** — the dominant PDN term | **OVERTURNED** |
| **Vertical interconnect architecture** | global "TSV carries input current" | **architecture-dependent**; ARCH_B carries 1 V and can be **infeasible** | **CORRECTED** |

### What changed and why it matters

**1. The RDL model was wrong by ~65×, and it dominates.** Phase 0D used
`R_per_mm = ρ/(t·W_die)` inside a parallel-branch network, which gives every source–load pair
its own full-die-width conductor and no current sharing. Replacing it with a 2-D resistive
sheet solve — **validated against MOOSE to 0.33–0.45 %** — raises lateral loss from 0.17 W to
**12.1 W** for the best placement and **73.0 W** for the worst. Lateral RDL, not the TSV, is
the dominant package distribution term.

**2. "ET is blind to placement" is withdrawn.** With the corrected sheet model, total
electrical loss across four placements at identical converter, footprint and thickness spans
**32.73 → 94.53 W (189 %)**, not 1.08 %. The electrical objective discriminates placement
strongly — and it *agrees* with mechanics that compact and asymmetric layouts are bad.

**3. The cheap mechanical win evaporates.** Phase 0D priced the best mechanical placement at
2.03 W/µm. Corrected, moving from the electrically optimal (distributed) to the mechanically
optimal (edge-biased) costs **+24.45 W (+75 %) for −1.157 µm (−39 %) = 21.1 W/µm** — an order
of magnitude worse. The ETM tradeoff is real but far more expensive than reported.

**4. The rail assumption was architecture-specific.** Phase 0D's "the TSV carries converter
input current" is correct for ARCH_A (the validated vehicle) and **wrong for ARCH_B**, where
the HVR sits on the substrate underside and the full 1 V output crosses the substrate. Under
the conservative reading of the per-via current limit, **ARCH_B is electrically infeasible**:
it needs 12 501 vias where the tile footprint holds 6 666.

**5. Thickness survives every correction.** Even with rail-aware currents, the ground return,
and the corrected RDL, thicker substrate remains better electrically, thermally and
mechanically. In ARCH_B the TSV thickness penalty grows 46× (0.76 → 34.7 mW) but is still two
orders of magnitude below the converter saving from running cooler.

**Bottom line for the thesis.** The corrected model makes the electrical objective *more*
discriminating, not less. Placement, which Phase 0D presented as the case where "mechanics
decides what electrical analysis cannot", is now a domain where ET and mechanics largely
**agree** — and where they disagree, the mechanical option is expensive. The strongest
remaining DVPD-specific ETM content is HVR footprint and the architecture-dependent
feasibility of the LV-TSV stack.

---

## 2. Regression / Reproduction

Baseline test suite before any modification: **79 passed, 0 failed, 0 skipped** — matching the
Phase-0D close-out. `results/phase0b/`, `results/phase0c/` and `results/phase0d/` are
preserved bit-for-bit; all Phase-0D-R output is under `results/phase0dr/`.

The Phase-0D report remains a valid historical artifact describing the first coupled
implementation. It is not rewritten.

---

## 3. Architecture Power-Path Audit

Full detail: `POWER_PATH_AUDIT.md`, `current_path_by_architecture.csv` (16 segments),
`configs/phase0dr/power_path_graphs.yaml`, Figure A (`FIG_A_power_paths.png`).

The global rule is replaced by a per-segment rule:

```
rail = HV  <=>  upstream of the converter    ->  I = I_in = P_in / V_in
rail = LV  <=>  downstream of the converter  ->  I = I_out
P_in = V_out*I_out + P_conv     (actual converter loss; never assumed ideal)
```

| architecture | HVR position | HV traverses | LV traverses | TSV rail |
|---|---|---|---|---|
| **ARCH_A** | substrate **top** (validated Phase-0B/0C vehicle) | BGA, TSV | microbump, RDL | **48 V** |
| **ARCH_B** | substrate **bottom** (land-side) | BGA | **TSV**, microbump, RDL | **1 V** |
| **ARCH_C** | lateral, beside the die (2.5D) | BGA, C4, TSV | RDL (long lateral), microbump | 48 V |

---

## 4. Rail-Aware Current Derivation

At the Phase-0B/0C operating point (I_out = 60 A/VR, 48 → 1 V, P_conv ≈ 5 W/VR):

| rail | current per VR | relative |
|---|---:|---:|
| LV (1 V) | 60.000 A | — |
| HV (48 V) | 1.354 A | **44.3× smaller** |

Because `P = I²R`, an identical segment dissipates **≈1960×** more on the LV rail. Stage
efficiency 92.3 % is taken from the converter model, not assumed.

---

## 5–8. Interconnect Tier Models and Validation

Each tier has its own geometry, **cross-section shape**, material, temperature dependence,
parallel count and current limit. A C4 is not a microbump.

| tier | shape | geometry | model R (20 °C) | June Table III | error | status |
|---|---|---|---:|---:|---:|---|
| BGA | circular | d 400 µm, h 300 µm, p 800 µm, solder | 0.3104 mΩ | 0.3 mΩ | +3.45 % | SOURCE_BACKED |
| TSV | circular | d 30 µm, h variable, p 60 µm, Cu | 7.2150 mΩ @300 µm | 7.1 mΩ | +1.62 % | SOURCE_BACKED |
| microbump | **square** | 10 × 10 µm, h 10 µm, p 20 µm, Cu | **1.7000 mΩ** | **1.7 mΩ** | **−0.00 %** | SOURCE_BACKED |
| C4 | circular | d 100 µm, h 70 µm, p 150 µm, solder | 1.1586 mΩ | absent | — | **ASSUMPTION** |
| RDL | 2-D sheet | t_Cu 5 µm, occupancy 0.60 | 5.667 mΩ/sq | absent | — | ASSUMPTION |

**Cross-section shape was recovered from the source, not assumed.** June's 100 µm² pad area
implies a **square** 10 × 10 µm pad; assuming circular would overstate that tier by 27 %.
BGA (125 663 µm²) and TSV (707 µm²) are circular. Using the square reproduces June's 1.7 mΩ
exactly.

**Ground return.** Phase 0D modelled supply only. `R_loop = R_supply + R_ground`, modelled as
a symmetric return, so **every Phase-0D interconnect loss was understated by 2×**.

**Feasibility is a hard gate**, `n_required = ceil(I/I_max)`; if it exceeds what the pitch
allows in the footprint the architecture is INFEASIBLE — never clipped with `min()`:

| I_via_max | ARCH_A (HV) | ARCH_B (LV) |
|---|---|---|
| 33 mA | 42 / 6 666 — feasible | 1 819 / 6 666 — feasible |
| **4.8 mA** | 283 / 6 666 — feasible | **12 501 / 6 666 — INFEASIBLE** |

The per-via limit is **OPEN**: June's 30 202 TSVs for 1 kA implies ≈33 mA/via if PL1 carries
output current, ≈4.8 mA if input RMS. Under the conservative reading the LV-TSV architecture
**cannot be built** at this current density — a constraint invisible to any loss optimisation.

---

## 9. RDL Model — the dominant correction

Phase 0D: `R_per_mm = ρ/(t_Cu·W_die)` = 0.155 mΩ/mm, used inside a parallel-branch network.
That gives each of the 400 source–load pairs an independent full-width conductor, so there is
no current sharing and no spreading resistance.

Phase 0D-R: a **2-D resistive sheet** solved by finite differences,
`∇·(σ_s ∇V) = −J` with `σ_s = t_Cu·occupancy/ρ(T)`, sources injecting over the **tile
footprint** and loads extracting over each **POL segment area**.

Two numerical points that materially affect the answer:

- **Point injection is wrong and expensive.** A point source in a 2-D sheet has a
  logarithmically singular potential. Injecting at a point rather than over the 4.9 mm tile
  overstates the loss by **776 %**. Real VRs inject over their footprint.
- **Footprint snapping destroys convergence.** Assigning a footprint to the nearest grid cell
  gives a discontinuous O(h) error; exact cell-overlap area weighting was required. With it,
  the solve converges to **≤0.72 %** over n = 41→121 (Richardson estimate 5.554 W at 25 °C).

### Independent validation against MOOSE

| check | result |
|---|---|
| analytic uniform-strip conductance | MOOSE 173.0704 S vs analytic 173.0704 S — **5.8e-12 %** |
| distributed 4-source/100-load sheet, total dissipation | FD **5.51 W** vs MOOSE **5.4915 W** — **0.33–0.45 %** |
| peak potential | FD 0.04614 V vs MOOSE 0.04484 V — 2.9 % (node-centred vs nodal max) |

*Source: `rdl_validation.json`.* The 2-D sheet model is validated by an independent finite-element
solver on the same problem.

### Consequence

| quantity | Phase 0D | Phase 0D-R | factor |
|---|---:|---:|---:|
| lateral RDL loss, distributed placement | 0.17 W | **12.13 W** | **71×** |
| lateral RDL loss, asymmetric placement | ~0.20 W | **73.00 W** | **365×** |
| P_PDN share of total electrical loss | 0.25–1.15 % | **37–77 %** | — |

**RDL Cu thickness is an ASSUMPTION and it dominates.** Sensitivity at fixed geometry:

| t_Cu | P_rdl | % of 240 W load | ΔV |
|---:|---:|---:|---:|
| 5 µm | 13.21 W | 5.50 % | 60.5 mV |
| 10 µm | 6.60 W | 2.75 % | 30.3 mV |
| 20 µm | 3.30 W | 1.38 % | 15.1 mV |
| 40 µm | 1.65 W | 0.69 % | 7.6 mV |

At the recorded 5 µm the design drops 60 mV on a 1 V rail (6 %), against June's reported
< 2.7 % at 1 kA — so **5 µm single-layer Cu is marginal for this delivery problem**, and the
absolute RDL numbers should be read as an upper bound pending a sourced metal stack.

---

## 10. Full-Wave EM Validation — status

**ANSYS HFSS could not be run.** AEDT v261 launches (`ansysedt -ng` returns rc = 0) and 6.3 GB
of previously solved projects exist at
`tessera-master_2/revision/aedt_projects` (HFSS 1–100 GHz on a 9×9 TSV array, Icepak, and a
coupled HFSS↔Mechanical project, solved 18 May – 2 Jun 2026). But **no licence can be checked
out today**: every attempt returns FlexNet −5,234 including the `electronics_desktop` feature
that those runs used; ports 1055/2325/27005 are closed on localhost and on pinback; no `lmgrd`
process is running; the only reachable licence port is 164.54.169.144:27020, which is the
Synopsys server and carries no ANSYS features. The licence file is `-rw------- amiceli`.
All 197 September entries in `~/.ansys/ansyscl.pinback.log` are failures.

**The existing runs cannot substitute for the missing validation**, and this is a physics
limitation rather than a bookkeeping one: they are TSV **signal-integrity** studies
(r = 3–3.5 µm, h = 100 µm, 1–100 GHz), whereas this phase needs **power delivery** at
DC–1 MHz on a BGA/C4/TSV/RDL/µbump stack with 30 µm TSVs.

**Why an AC correction is nevertheless not needed at the operating point.** Skin depth in
copper is `δ = sqrt(ρ/(π f µ))`:

| f | δ in Cu | vs 15 µm TSV radius | vs 5 µm RDL |
|---|---:|---|---|
| f_sw = 0.286 MHz | **123 µm** | 8.2× larger — no skin effect | 25× larger — none |
| 10 MHz (35th harmonic) | 20.7 µm | 1.4× larger — onset | 4× larger — none |
| 1 GHz (existing HFSS data) | 2.1 µm | 7× smaller — deep skin effect | comparable |

At the converter switching frequency every conductor is electrically thin, so `R_ac ≈ R_dc`
and the DC model is the correct one. The existing 1–100 GHz HFSS data sits in a regime where
the physics is qualitatively different and therefore validates the extraction *method*, not
this phase's operating point. **PALACE is installed and functional** as a full-wave
alternative; a targeted low-frequency PALACE study is recommended in §22 but was not run in
this phase.

---

## 11. Independent Thermal / Conduction Validation (MOOSE)

MOOSE `heat_transfer-opt` was used as the independent FE cross-check, exploiting the exact
correspondence between DC conduction and heat conduction (`∇·σ∇V ≡ ∇·k∇T`).

| test | MOOSE | reference | agreement |
|---|---:|---:|---:|
| 3-D bar conductance, `kA/L` | 0.020000 | 0.020000 | exact |
| 2-D sheet conductance, analytic strip | 173.0704 S | 173.0704 S | 5.8e-12 % |
| distributed source/load sheet dissipation | 5.4915 W | FD 5.5095 W | **0.33 %** |

This validates the electrical sheet model. A MOOSE cross-check of the **package thermal**
model (TH-1…TH-4) was **not completed in this phase** and is carried to §22.

---

## 12. Spatial Joule-Heat Mapping

Losses are attributed to the physical region that dissipates them, not lumped onto the
converter: converter loss on the HVR tiles, distribution loss into the die/RDL plane where the
routing sits. Conservation is checked automatically each iteration; the energy-balance
residual is **±0.000 %** on all 11 corrected runs (`coupled_candidates_corrected.csv`).

This matters more than it did in Phase 0D: distribution loss is now **12–73 W**, not 0.17 W,
so where it is deposited materially changes the temperature field and therefore the warpage.

---

## 13. Local-Temperature ET Fixed Point

Each candidate runs to `|ΔT_max| < 0.05 K`; all converged in **3–5 iterations**. Converter
resistances (`R_DS(on)`, inductor DCR) and every interconnect resistivity are evaluated at the
converged temperature.

**Re-evaluating the Phase-0D "−146 mW" claim.** With the corrected PPDN the converter saving
from thickening the substrate is **−0.22 W** (20.81 → 20.59 W for ARCH_A distributed at
J = 2), larger than Phase 0D's −146 mW because the added RDL heat raises the baseline
temperature. The direction is unchanged and the mechanism is the same.

---

## 14. Thickness Re-Audit — the decisive architecture test

ARCH_A distributed, J = 2 (`coupled_candidates_corrected.csv`):

| architecture | TSV rail | h_sub | P_TSV | P_RDL | P_elec | η | T_max | die warpage |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| ARCH_A | 48 V | 200 µm | 0.13 mW | 12.238 W | 33.05 W | 87.89 % | 73.31 °C | 6.907 µm |
| ARCH_A | 48 V | 500 µm | 0.89 mW | 12.129 W | **32.73 W** | 88.00 % | 70.56 °C | **3.003 µm** |
| ARCH_B | **1 V** | 200 µm | 5.76 mW | 12.238 W | 33.06 W | 87.89 % | 73.31 °C | 6.908 µm |
| ARCH_B | **1 V** | 500 µm | **39.94 mW** | 12.129 W | **32.77 W** | 87.99 % | 70.57 °C | **3.004 µm** |

**The hypothesis this phase was built to test is NOT confirmed.**

- The LV-TSV thickness penalty is **45× larger** than the HV-TSV one (+34.2 mW vs +0.76 mW),
  exactly as predicted by the rail argument.
- But it remains **an order of magnitude below** the thermal benefit. Total electrical loss
  still *falls* with thickness in **both** architectures (−0.97 % for ARCH_A, −0.88 % for
  ARCH_B), and warpage falls **−56.5 %** in both.

So there is **no architecture-dependent three-domain thickness tradeoff** at this scale.
Thicker substrate is better electrically, thermally and mechanically regardless of which rail
crosses it. The reason is structural: sizing vias by current density makes
`P_TSV = I·ρ·h·I_via,max/A` — *linear* in current, not quadratic — so provisioning enough vias
caps the penalty. It would take h ≈ 2.8 mm, or a via count far below the current-density
requirement, for the penalty to overtake the thermal benefit.

**Where architecture-dependence does appear is feasibility, not loss.** At the conservative
per-via limit ARCH_B needs 12 501 vias in a footprint holding 6 666 and is simply not
buildable (§5–8).

---

## 15. Footprint Re-Audit

ARCH_A distributed, h = 500 µm:

| J | A_HVR total | P_conv | P_RDL | P_elec | η | T_max | die warpage |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4.0 | 60.0 mm² | 35.17 W | 19.72 W | 54.89 W | 81.39 % | 80.26 °C | **2.083 µm** |
| 2.0 | 103.0 mm² | 20.59 W | 12.13 W | 32.73 W | 88.00 % | 70.56 °C | 3.003 µm |
| 1.5 | 137.3 mm² | 16.36 W | 8.75 W | **25.11 W** | **90.53 %** | **67.74 °C** | 3.831 µm |

**The opposition survives, and it is now stronger on the electrical side.** Phase 0D had RDL
loss essentially independent of footprint; with the sheet model a larger tile injects over a
larger area and therefore has **lower spreading resistance too** (19.72 → 8.75 W). So growing
the footprint improves the converter *and* the distribution *and* the temperature, while
worsening warpage.

J = 4 → J = 1.5: **−29.78 W (−54 %) for +1.748 µm (+84 %) = 17.0 W/µm.**

---

## 16. Placement Re-Audit — Phase-0D claim withdrawn

ARCH_A, J = 2, h = 500 µm — identical converter, footprint and thickness; only placement differs:

| placement | P_RDL | P_elec | η | T_max | die warpage |
|---|---:|---:|---:|---:|---:|
| distributed 2×2 | **12.13 W** | **32.73 W** | **88.00 %** | **70.56 °C** | 3.003 µm |
| edge / corner biased | 36.15 W | 57.18 W | 80.76 % | 76.07 °C | **1.846 µm** |
| compact 2×2 central | 43.13 W | 64.40 W | 78.84 % | 79.01 °C | 6.490 µm |
| asymmetric left | 73.00 W | 94.53 W | 71.74 % | 82.34 °C | 5.623 µm |

| quantity | Phase 0D | **Phase 0D-R** |
|---|---:|---:|
| electrical spread across placements | 1.08 % | **188.8 %** |
| warpage spread | 240 % | 251.6 % |
| conclusion | "ET is blind to placement" | **withdrawn** |

**ET is not blind to placement — it discriminates it by nearly 3×**, and it largely *agrees*
with mechanics: compact and asymmetric are bad on both counts and are Pareto-dominated. The
only genuine disagreement is distributed (electrically best) versus edge-biased (mechanically
best), and that now costs **+24.45 W (+75 %) for −1.157 µm (−39 %) = 21.1 W/µm**.

---

## 17–18. Corrected ET and ETM Rankings

The ET objective was frozen as in Phase 0D (`minimise P_elec_total`, Pareto on
`(P_elec, T_max)`) before mechanics was consulted.

**ET Pareto front: a single point** — `ARCH_A_distributed_J1.5_h500`
(25.11 W, η 90.53 %, T_max 67.74 °C), which simultaneously minimises loss and temperature.

**ETM Pareto front (adds die warpage): 4 members, all at h_sub = 500 µm**

| case | P_elec | T_max | warpage | ET rank |
|---|---:|---:|---:|---:|
| ARCH_A_distributed_J1.5_h500 | 25.11 W | 67.74 °C | 3.831 µm | 1 |
| ARCH_A_distributed_J2_h500 | 32.73 W | 70.56 °C | 3.003 µm | 2 |
| ARCH_A_distributed_J4_h500 | 54.89 W | 80.26 °C | 2.083 µm | 6 |
| ARCH_A_edge_J2_h500 | 57.18 W | 76.07 °C | **1.846 µm** | 7 |

| quantity | Phase 0D | **Phase 0D-R** |
|---|---:|---:|
| ET front size | 1 | 1 |
| ETM front size | 6 | 4 |
| ET optimum → minimum-warpage cost | 2.03 W/µm | **16.2 W/µm** |
| relative price of the mechanical option | — | **8.0× more expensive** |

Per §25 of the brief this is a **Pareto-front expansion**, not a reversal: the ET optimum is
never dominated (it holds minimum `P_elec` by construction), and no source-backed selection
rule changes the selected design. **Terminology: ROBUST ETM PARETO TRADEOFF, NO UNIQUE
REVERSAL.**

---

## 19. BC-B

Not run in this phase. Every Phase-0D-R result is **BC-A (free warpage)**, inheriting the
Phase-0C limitation unchanged: under a board-restrained support all architecture effects fall
toward the model's numerical floor. Carried to §22.

---

## 20. G2 — Reliability Constraint

# NOT TESTED

Unchanged from Phase 0D. The only numeric warpage figure anywhere in the project is the
Phase-0A `w_allow = 50 µm`, explicitly labelled "NOT A PUBLICATION-GRADE RELIABILITY LIMIT".
All corrected candidates lie between **1.846 and 8.632 µm**, far inside it, so no feasibility
reversal is reachable at this power scale by any computation. The brief's alternative
constraint quantities (coplanarity, microbump relative displacement, solder strain, interface
shear) have no source-backed limit in the repository either.

---

## 21. Uncertainty and Robustness

**Parameter uncertainty** (distinct from model ablation):

| parameter | status | effect on the conclusions |
|---|---|---|
| RDL t_Cu (5 µm) | ASSUMPTION | **dominant.** 5→40 µm takes P_RDL from 13.2 W to 1.65 W. All absolute RDL numbers are upper bounds. |
| RDL metal occupancy (0.60) | ASSUMPTION | linear on P_RDL, same direction as t_Cu |
| I_via,max (33 vs 4.8 mA) | **OPEN** | decides whether ARCH_B is buildable at all |
| C4 geometry | ASSUMPTION | P_C4 ≈ 0.74 mW — negligible either way |
| α_GaN (7.5e-3 /K) | ASSUMPTION | Phase-0D showed a 2× change moves the tradeoff rate ~12 % |
| ground-return symmetry | ASSUMPTION | factor-2 on every interconnect tier |

**Model-form uncertainty**: the RDL sheet is 2-D and single-layer; a real stack has multiple
metal layers and explicit P/G interdigitation. **Numerical uncertainty**: sheet solve ≤0.72 %
(grid), mechanics 0.50 % (Phase-0C mesh study), MOOSE cross-check 0.33–0.45 %.

The **ordering** conclusions (distributed < edge < compact < asymmetric electrically; edge <
distributed mechanically; thicker better on all domains) are insensitive to t_Cu and occupancy
because those scale all placements identically. The **magnitudes** are not.

---

## 22. Exact Next Gate

**Not started. Recommendation only.**

The corrected model weakens rather than strengthens the ETM case, so the priority is no longer
to build a synthesis framework but to settle the two inputs that now dominate the answer.

# PHASE 0E — METAL-STACK CLOSURE AND INDEPENDENT VALIDATION

1. **Source the RDL metal stack.** It is now the dominant electrical term and the largest
   single uncertainty: thickness, layer count, and P/G occupancy change P_RDL by an order of
   magnitude and therefore change every efficiency number in this report. Until it is sourced,
   the placement and footprint magnitudes are upper bounds.
2. **Resolve `I_via,max`.** It alone decides whether the LV-TSV architecture exists. This is a
   literature/process question, not a computation.
3. **Independent EM validation with PALACE** at DC and f_sw on the vertical stack and a
   bump/RDL transition, to confirm the bulk-resistance model and quantify current crowding.
   PALACE is installed and functional; the analytic skin-depth argument (§10) says AC
   correction should be negligible at 0.286 MHz, and that deserves one confirming run.
4. **MOOSE thermal cross-check** of the package model (TH-1…TH-4), extending the conduction
   validation already done here to the full 3-D stack with spatially mapped Joule heat.
5. **BC-B**, as carried from Phase 0C.

**Do not start the global ETM optimiser.** Two of its three inputs — the metal stack and any
mechanical constraint — are still unsourced, and the corrected exchange rate (16.2 W/µm) makes
the mechanical option markedly less attractive than Phase 0D suggested. Optimising now would
encode an arbitrary metal stack into the answer.
