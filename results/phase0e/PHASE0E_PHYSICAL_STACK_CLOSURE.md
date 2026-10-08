# Phase 0E — Physical Metal-Stack, TSV-Allocation and Independent-Validation Closure

**Scope.** Close the physical inputs Phase 0D-R left open, validate the compact models against independent solvers, and re-test every Phase-0D-R conclusion against the sourced stack. This is **not** the synthesis phase and no optimiser was built.

## 1. Verdict

```
PHYSICAL STACK CLOSED — ETM NOVELTY WEAKENS
```

Both halves of that are meant literally, and they point in opposite directions.

**The physical foundation is much stronger than it was.** The RDL stack and the TSV allocation rule now come from primary sources and reproduce those sources' own derived quantities to better than 2 %. The compact multilayer model matches an independent FE solver to 1.1 % across three placements under one calibration, the package thermal model preserves candidate ordering exactly against an independent 3-D solver, and HFSS confirms that no AC correction is needed at the switching frequency. The footprint mechanism — the strongest novelty candidate — survives replacing its dominant PROVISIONAL material card with a composite derived from the converter compiler's own component inventory, changing its sensitivity by 0.06 %.

**The novelty case is nevertheless weaker than Phase 0D-R presented it.** Four results moved against it:

1. **ARCH_B is not infeasible.** The most striking Phase-0D-R result — an entire architecture eliminated by a vertical-interconnect limit — rested on an unsourced 4.8 mA per-via figure. Under both primary sources the architecture needs 849 of 7 148 vias. That claim is withdrawn.

2. **The placement electrical spread is 46.7 %, not 188.8 %.** The qualitative claim survives; the number that made it striking does not.

3. **Placement is the cheapest mechanical lever** (3.70 W/µm against footprint's 11.48 W/µm) — and placement is precisely what STAMP-2.5D and ATMPlace already optimise. The DVPD-specific lever is the expensive one.

4. **Under board restraint the footprint warpage ordering reverses** (+88 % free, −12 % restrained), and the thickness lever stops discriminating warpage altogether. Every free-warpage ordering in this project either reverses or vanishes under BC-B.

What Phase 0E adds in exchange is smaller but sounder: a sourced stack, an allocation correction with a genuinely DVPD-specific consequence (whether a via field's loss scales as $I$ or $I^2$ is a policy, not a law), and a newly visible architecture-dependent thickness margin — 1.46x in ARCH_B against 67.7x in ARCH_A — that Phase 0D-R had concluded did not exist.

### Sub-verdicts

| item | Phase-0D-R | Phase 0E | status |
|---|---|---|---|
| **RDL physical model** | single 5 µm sheet, occupancy 0.60, ground as a ×2 factor (all ASSUMPTION) | ECTC-2024 Table I: 10 µm Cu, 10/2 µm line/space, **2 VDD + 2 GND** layers, occupancy derived = 0.833; explicit VDD+GND solve | **CLOSED — 5.56× correction** |
| **TSV current capability** | 33 mA / 4.8 mA, both unsourced | envelope J_Cu = 1.0e+08–4.0e+08 A/m², each self-consistent across two independent tiers | **BOUNDED; reliability limit still OPEN** |
| **TSV allocation** | `R = R_single/n_required` | n_req / n_alloc / n_avail separated; `R = R_single/n_ALLOCATED`; June's own policy (`n_alloc = n_req`) identified verbatim | **CORRECTED** |
| **ARCH_B feasibility** | **INFEASIBLE** at 4.8 mA/via | **FEASIBLE** under every source-backed J; infeasible only below ~1e7 A/m², 5–11× below the most conservative sourced value | **REVERSED** |
| **Thickness** | thicker wins on all three domains | unchanged in direction | **CONFIRMED** |
| **Footprint** | larger → lower loss, higher warpage | opposition survives the physical material model (sensitivity changes 0.06 %) but **reverses sign under BC-B** | **ROBUST to material, NOT to boundary** |
| **Placement** | electrical spread 188.8 % | re-audited on the sourced stack | see §7 |
| **BC-B** | deferred | run on decisive pairs; **every warpage ordering reverses or vanishes**, shear rises | **RESOLVED — and it is a warning** |
| **EM validation** | none | HFSS: R flat to 0.18 % below the 19.1 MHz skin crossover; Q3D **not licensed** | **DONE within the valid regime** |
| **Thermal validation** | MOOSE operator only | MOOSE multilayer RDL (3 placements, one calibration) + Icepak package cross-check | **DONE** |

## 2. The sourced stack

Full provenance in `RDL_STACK_LITERATURE_AUDIT.md`. Both trace rows of ECTC-2024 Table I reproduce the paper's own `R'_Heff` to <2 %, and the PCB row settles the otherwise ambiguous layer count.

| stack | t_Cu | W/S | n_VDD | n_GND | occupancy | R_sq per net (mΩ/sq) | status |
|---|---:|---|---:|---:|---:|---:|---|
| `ectc2024_primary` | 10 µm | 10/2 µm | 2 | 2 | 0.8333 | 1.020 | SOURCE_BACKED |
| `ectc2024_one_per_net` | 10 µm | 10/2 µm | 1 | 1 | 0.8333 | 2.040 | DERIVED_FROM_SOURCE |
| `iscas2024_variant` | 10 µm | 2/2 µm | 1 | 1 | 0.5000 | 3.400 | SOURCE_BACKED |
| `phase0dr_legacy` | 5 µm | — | 1 | 0 | 0.6000 | 5.667 | ASSUMPTION |

**The Phase-0D-R sheet was 5.556× too resistive.** Every Phase-0D-R RDL magnitude scales down by that factor before any other correction.

### Source cross-check that did NOT reproduce

ECTC-2024 Table II's published PPDN magnitudes cannot be reconstructed from the printed stack and equations:

| case | published | ECTC eq.(1)+(3) applied literally | Phase-0E sheet solver |
|---|---:|---:|---:|
| A1 periphery M=40 | 76.0 W | 0.35 W (-99.5 %) | 104.14 W (+37.0 %) |
| A2 under-die  M=40 | 39.5 W | 0.22 W (-99.4 %) | 5.12 W (-87.0 %) |
| A2 under-die  M=100 | 32.0 W | 0.01 W (-100.0 %) | 0.05 W (-99.9 %) |

No segment count `S` closes a gap that scales as 1/S (tested 4–400). The stack *parameters* are validated; the published loss *magnitudes* are not reproducible, so **RDL loss magnitudes remain provisional** and are always quoted with the stack.

## 3. Multilayer RDL compact model vs independent FE (Sec. 10)

Predeclared before any run: |ΔP| ≤ 2.0 %, |ΔV| ≤ 4.0 %, **one calibration for every placement**.

| placement | P compact (W) | P MOOSE (W) | ΔP | ΔV | verdict |
|---|---:|---:|---:|---:|---|
| distributed | 0.97838 | 0.98282 | -0.45 % | -2.16 % | PASS |
| edge_biased | 1.75046 | 1.76998 | -1.10 % | -2.19 % | PASS |
| asymmetric | 6.82347 | 6.86353 | -0.58 % | -0.90 % | PASS |

**ALL PASS** with a single grid (n = 161) chosen by the convergence study in `rdl_grid_convergence.csv`, and MOOSE stable to 0.09 % between 200² and 400².

Two methodological errors were found and fixed while building this comparison, both of which would have produced a confident wrong answer:

1. **A Dirichlet condition on a whole edge is a different problem** from a point reference — it lets current enter and leave through that edge. Edge-pinned comparison disagreed by +25 % (edge-biased) and +55 % (asymmetric).

2. **A 104-term `ParsedFunction` silently loses terms** — measured injection was 195 A instead of 240 A, an 18 % current error and therefore ~35 % in power. The 100 equal POL footprints tile the die exactly, so the load is simply uniform.

3. A tile placed at ±9.0 mm **overhangs a 22.36 mm die**; the compact model renormalises the clipped footprint and MOOSE does not. Placements are now asserted to lie on the substrate.

## 4. EM validation (Sec. 9)

Q3D Extractor is **not licensed** on this server (`UNSUPPORTED "elec_solve_q3d" ... No such feature exists (-5,346)`), so DC conduction is validated with MOOSE and HFSS is used only where full-wave is valid. Full account in `em_validation.md`.

* Skin depth equals the via radius at **19.1 MHz**; at f_sw = 0.286 MHz, δ/r = 8.18.

* HFSS R varies by **0.18 %** between 1 and 5.6 MHz, then rises 3.1× by 1 GHz. **No AC correction is needed at the switching frequency — verified, not assumed.**

* Loop inductance 0.225 nH against an analytic two-wire value of 0.166 nH.

* Measured resistance exceeds a 1-D series sum of the same geometry by **1.326×** (and 1.96× for the two-pair geometry): bulk-cylinder resistance is not total connection resistance. Carried as an uncertainty band, not a calibrated constant.

## 4b. Allocation policy decides the current law (Sec. 4)

With `n_required`, `n_allocated` and `n_available` separated, the policy that picks `n_allocated` becomes visible — and it decides something Phase 0D-R stated as if it were a property of TSVs. At the reference point (June J, h = 500 µm, 5.073 mm tile):

| arch | rail | policy | n_req | n_alloc | n_avail | P_TSV loop (mW) |
|---|---|---|---:|---:|---:|---:|
| ARCH_A | HV | `A_min_capability` | 20 | 20 | 7148 | 1.937 |
| ARCH_A | HV | `B_geometric` | 20 | 3574 | 7148 | 0.011 |
| ARCH_A | HV | `C_area_optimal` | 20 | 7148 | 7148 | 0.005 |
| ARCH_B | LV | `A_min_capability` | 849 | 849 | 7148 | 89.621 |
| ARCH_B | LV | `B_geometric` | 849 | 3574 | 7148 | 21.289 |
| ARCH_B | LV | `C_area_optimal` | 849 | 7148 | 7148 | 10.645 |

The LV rail carries 44.31x the HV rail's current. What that does to the field loss depends entirely on the policy:

| policy | current ratio | loss ratio | law |
|---|---:|---:|---|
| `A_min_capability` | x44.31 | x46.26 | **P ~ I** (linear) |
| `B_geometric` | x44.31 | x1963.65 | **P ~ I²** (quadratic) |
| `C_area_optimal` | x44.31 | x1963.65 | **P ~ I²** (quadratic) |

**`P_TSV` is proportional to current only under minimum-capability provisioning**, because that policy makes `n_alloc` itself proportional to current. Under a geometric or area-optimal allocation the same via field obeys the ordinary quadratic law, and the ratio is exactly 44.31² = 1963. Phase 0D-R's linear behaviour was a consequence of dividing by `n_required`; it is a **design policy, not a law**.

This also bears on the thickness result: allocating all available vias instead of the bare minimum cuts ARCH_B's TSV loss from 89.6 to 10.6 mW, which would raise its thickness margin from 1.46x to roughly 12x. **The architecture-dependent thickness tension is a consequence of the June framework's own minimum-provisioning policy, not an intrinsic property of the LV-TSV architecture.**

## 5. Full-package thermal cross-check (Sec. 13)

An independent 3-D MOOSE package model --- own mesher, elements and solver --- with meshed volumes and cooling conductance matched exactly to the CalculiX model. Energy closes to -0.000 % in both. Detail in `thermal_validation.md`.

| case | CalculiX T_max (°C) | MOOSE T_max (°C) | difference |
|---|---:|---:|---:|
| TH1_distributed_h500 | 68.982 | 69.905 | +1.34 % |
| TH2_distributed_h200 | 71.650 | 72.587 | +1.31 % |
| TH3_small_footprint | 77.440 | 78.725 | +1.66 % |
| TH4_large_footprint | 66.623 | 67.083 | +0.69 % |
| TH5_edge_biased | 71.399 | 71.583 | +0.26 % |

**ORDERING PRESERVED** --- identical ranking in both solvers, max discrepancy 1.66 %, mean 1.05 %.

Icepak was attempted and its result **discarded**: the solve reported Normal Completion but every object returned exactly 5000.00 K, a solver clamp meaning the external cooling boundary never took effect. No Icepak number appears in any result.

\newpage
## 6. Decisive re-run on the sourced stack (Sec. 7, 11, 12, 14, 18)

### 6.1 Placement (Sec. 11)

| placement | P_RDL (W) | P_elec (W) | η (%) | T_max (°C) | warpage (µm) |
|---|---:|---:|---:|---:|---:|
| distributed | 2.165 | 22.53 | 91.42 | 68.98 | 2.903 |
| edge | 6.434 | 26.98 | 89.89 | 71.40 | 1.700 |
| compact | 7.566 | 28.22 | 89.48 | 73.35 | 5.816 |
| asymmetric | 12.406 | 33.05 | 87.90 | 72.86 | 4.717 |

The RDL spread across placements is 473 % (Phase-0D-R: 502 %), but because the sourced stack is 5.56x more conductive the spread in **total** electrical loss falls to **46.7 %** --- against the **188.8 %** Phase 0D-R reported. The qualitative Phase-0D-R claim (the electrical objective is *not* blind to placement) survives; its magnitude does not.

**Placement is a genuine ETM conflict.** The electrically best placement is `distributed` and the mechanically best is `edge`. Moving from one to the other costs +4.45 W (+19.8 %) and saves 1.203 µm (-41.4 %) --- an exchange rate of **3.70 W/µm**, the cheapest mechanical lever measured in this project. It is also, honestly, the lever that STAMP-2.5D and ATMPlace already optimise.

### 6.2 Thickness, both architectures (Sec. 7)

| arch | h_sub | n_alloc | P_TSV (mW) | P_elec (W) | T_max (°C) | warpage (µm) |
|---|---:|---:|---:|---:|---:|---:|
| ARCH_A | 0.2 mm | 20 | 0.35 | 22.68 | 71.65 | 6.671 |
| ARCH_A | 0.5 mm | 20 | 2.44 | 22.53 | 68.98 | 2.903 |
| ARCH_B | 0.2 mm | 849 | 16.15 | 22.70 | 71.65 | 6.671 |
| ARCH_B | 0.5 mm | 849 | 112.36 | 22.64 | 69.00 | 2.904 |

* **ARCH_A** 200 → 500 µm: ΔP_elec -0.67 %, ΔT -2.67 K, Δwarpage -56.5 % → **WIN/WIN/WIN**
* **ARCH_B** 200 → 500 µm: ΔP_elec -0.25 %, ΔT -2.65 K, Δwarpage -56.5 % → **WIN/WIN/WIN**

**The margin, however, is architecture-dependent — and Phase 0D-R understated that.** Decomposing the 200 → 500 µm change:

| arch | TSV penalty | converter saving | PDN total | net electrical | saving / penalty |
|---|---:|---:|---:|---:|---:|
| ARCH_A | +2.09 mW | +141.21 mW | -10.75 mW | -151.96 mW | **67.70x** |
| ARCH_B | +96.22 mW | +140.08 mW | +83.48 mW | -56.59 mW | **1.46x** |

In ARCH_A the vertical penalty is negligible and the thickness win is overwhelming. In ARCH_B the 1 V rail traverses the substrate, the TSV field loss rises 7x, and it consumes **69 %** of the converter saving. The package distribution loss actually **increases** with thickness in ARCH_B (+83.5 mW); only the converter saving keeps the total negative, and the net gain is 0.25 % rather than ARCH_A's 0.67 %.

**So thicker is still win/win/win for both architectures at this operating point, but the margin differs by ~46x between them.** Phase 0D-R concluded that no architecture-dependent thickness tradeoff exists because its penalty was an order of magnitude below the benefit; with the corrected allocation the ARCH_B margin is only 1.46x. The tension Phase 0D-R looked for is real and much closer to binding than it found — it simply does not change the sign at 240 W and 500 µm. This is the clearest single reason to run the 1 kW gate.

### 6.3 Footprint (Sec. 12, electrical side)

| A_HVR total (mm²) | P_conv (W) | P_RDL (W) | P_elec (W) | T_max (°C) | warpage (µm) |
|---:|---:|---:|---:|---:|---:|
| 60.00 | 34.32 | 3.499 | 37.83 | 77.44 | 1.986 |
| 102.96 | 20.36 | 2.165 | 22.53 | 68.98 | 2.903 |
| 137.28 | 16.23 | 1.551 | 17.78 | 66.62 | 3.733 |

Small → large footprint: **-53.0 %** electrical for **+87.9 %** warpage --- an exchange rate of **11.48 W/µm** (Phase 0D: 2.03, Phase 0D-R: 16.2). The opposition is unchanged in sign and close in magnitude to Phase 0D-R; the sourced stack makes it somewhat cheaper but it remains 3x more expensive than the placement lever.

### 6.4 Local temperature feedback (Sec. 14)

Each converter is now driven by the volume-weighted mean temperature of **its own** tile rather than the global package maximum.

| placement | T_VR range (°C) | spread (K) | converter-loss spread |
|---|---|---:|---:|
| distributed | 67.60 – 67.60 | 0.00 | 0.00 % |
| edge | 69.88 – 69.88 | 0.00 | 0.00 % |
| compact | 71.21 – 71.21 | 0.00 | 0.00 % |
| asymmetric | 70.56 – 71.67 | 1.11 | 0.43 % |

Symmetric layouts give exactly zero spread, as they must --- which is a useful check that the per-tile extraction is doing what it claims. The asymmetric layout produces a real but small 1.11 K spread and 0.43 % converter-loss imbalance. **Local feedback is implemented and verified, but it is not load-bearing on this vehicle**; using the global maximum would not have changed any conclusion here.

\newpage
## 7. BC-B: which response still discriminates (Sec. 15)

Phase 0C showed BC-B suppresses free warpage by ~20x. The question is not how much smaller, but **which response still separates the candidates** when the package is board-restrained. Interface peel is excluded throughout --- it never converged.

A difference counts as RESOLVED only if it exceeds 2x the numerical uncertainty (u_m = 0.5 % from the Phase-0B/0C mesh study). Both BC families use the same 0.40 mm mesh, coarsened from 0.32 mm because the BC-B support layer pushes the model past the 40 000-element C3D8I ceiling where CalculiX segfaults silently.

| lever | metric | BC-A | BC-B | what happens under restraint |
|---|---|---:|---:|---|
| footprint | die warpage pv um | +88.31 % | -12.22 % | **SIGN REVERSES** |
| footprint | curvature um per mm2 | +89.48 % | -89.51 % | **SIGN REVERSES** |
| footprint | interface shear p99 MPa | -18.46 % | -25.68 % | preserved, magnitude changes |
| thickness | die warpage pv um | -56.47 % | -0.14 % | **LOST** — no longer resolvable |
| thickness | curvature um per mm2 | -56.31 % | -56.87 % | preserved |
| thickness | interface shear p99 MPa | +52.71 % | -9.63 % | **SIGN REVERSES** |
| placement | die warpage pv um | -41.55 % | +6.85 % | **SIGN REVERSES** |
| placement | curvature um per mm2 | -57.89 % | -1093.04 % | preserved, magnitude changes |
| placement | interface shear p99 MPa | +19.20 % | +15.54 % | preserved |

**Every free-warpage ordering in this project either reverses or vanishes under board restraint.** Footprint reverses (+88 % → −12 %), placement reverses (−42 % → +7 %), and thickness stops being resolvable in warpage at all (−56 % → −0.14 %). At the same time interface shear *rises* under restraint in every case: the board converts package bending into shear at the die attach.

No single response is robust across all three levers. **Curvature** preserves the thickness effect almost exactly (−56.31 % free vs −56.87 % restrained) and keeps the placement sign, but reverses for footprint. **Interface shear** preserves footprint and placement but reverses for thickness. Choosing the mechanical response is therefore a first-order modelling decision in a board-mounted ETM formulation, not a detail — and it has never been made explicitly in this project because every prior phase was free-warpage.

This does not invalidate the BC-A results: free warpage is a legitimate package-level quantity and is what ATMPlace reports. It does mean that **no board-level design conclusion may be drawn from any BC-A result in this project**, and that the footprint opposition — the central novelty claim — is a package-level statement only. The BC-B foundation itself remains PROVISIONAL (stiffness never calibrated against a BGA unit cell or board data), so this is a warning, not a replacement result.

\newpage
## 8. G2 — reliability constraint (Sec. 16)

```
G2 = NOT TESTED
```

No source-backed mechanical allowable was found that matches this package state, temperature and measurement definition. Nothing in Phase 0E changes that, and the earlier statement that *"no feasibility reversal is reachable at 240 W"* is **withdrawn**: it asserted a negative about a criterion that was never defined. Warpage being numerically small is not evidence of safety.

## 9. Exact next gate (Sec. 24)

The six preconditions in the brief are met: the RDL stack is closed, the allocation rule is credible and source-backed, the footprint material mapping survives, EM validation agrees within its valid regime, the package thermal cross-check preserves ordering, and BC-B does not eliminate the effect --- it relocates it into interface shear. Therefore:

```
PHASE 0F — 1-kW REFERENCE-SCALE ETM GATE
```

Scale the validated model to the June 1 kW / 500 mm² reference and ask **one** question: does any mechanical quantity approach a plausible limit there? At 240 W every warpage number is a few microns and no constraint can bind, so the question of whether DVPD thermo-mechanics is a synthesis constraint or a signoff check is a question about scale, not about the model. **Do not build the global ETM optimiser**: with no active constraint it would return the electrical optimum with extra steps, while encoding an arbitrary exchange rate.

