# Phase 0F — 1-kW Reference-Scale ETM Materiality / Constraint Gate

**Question.** At the actual June-2026 1 kW / 500 mm² reference, does thermo-mechanics produce any architecture-dependent design constraint or ET↔M opposition that survives the relevant assembly state?

This is **not** the synthesis phase. No optimiser was built.

## 1. The geometry had to be fixed first (Sec. 1)

Phase 0E left a 500 µm inductor inside a 150 µm tile and recorded that it *"does not affect trends"*. That was an assumption. Tested, it is half wrong.

The converter the compiler selects needs a **720 µm** cell (nominal bound). Therefore:

```
h_sub = 200 um : GEOMETRICALLY INFEASIBLE under every height bound
h_sub = 500 um : GEOMETRICALLY INFEASIBLE under the nominal and pessimistic bounds
```

**Both endpoints of the thickness sweep that produced "thicker is win/win/win" across four phases are unbuildable with the converter that sweep assumed.** Under the optimistic bound a 500 µm substrate does admit a converter, but the best one available costs 27.4 W/VR at 25 °C against 4.2 W — 6.4× worse. The realizable range begins near **800 µm**.

Re-running the decisive 240 W comparisons on realizable geometry:

| comparison | Phase 0B–0E (unbuildable) | Phase 0F (realizable) | direction |
|---|---:|---:|---|
| thickness thin→thick | −56.5 % | **-81.9 %** | survives, stronger |
| footprint small→large | +87.9 % | **+108.3 %** | survives, stronger |
| placement dist→edge | −41.5 % | **-49.4 %** | survives, stronger |

The **directions** survive; the **magnitudes** were all wrong by tens of percent and the thicknesses were impossible. Full account in `GEOMETRY_REALIZABILITY_AUDIT.md`.

## 2. The cooling boundary had to be recalibrated (Sec. 2)

Carrying the Phase-0B `h_top = 17 521.6 W/m²K` to a 1 kW load would have put the package near 130 °C rather than 84 °C. Recalibrated to the June target:

* **h_top = 166,000 W/m²K**, **9.47× the Phase-0B value**

* T_max = 84.071 °C against the 84 °C June target (residual +0.071 K)

* at that point: converter 124.38 W, distribution 0.64 W, total heat 1125 W, efficiency 88.89 %


June cools with substrate-embedded micro-channels *adjacent to the GaN switch layer*, not above the die. That topology was calibrated too and **cannot reach the target**: it flattens at 90.96 °C (+6.96 K) even at 398,672 W/m²K. The die holds 1000 W of the ~1100 W total and sits on the far side of the package from the coolant, so the intervening conduction resistance sets a floor near 91 °C. **A 1-kW DVPD package cannot be cooled from the substrate side alone.** Detail in `COOLING_1KW_CALIBRATION.md`.

## 3. The 1-kW electrical system was rebuilt, not scaled (Sec. 3)

| quantity | value | note |
|---|---:|---|
| load | 1000 W at 1 V | June reference |
| regulators M | **49** | June's optimum is 70; **70 tiles of this footprint cannot be placed** under this project's own 0.5 mm keepout and gap rules |
| current density target | 3.5 A/mm² | chosen so areal utilisation matches June's stated 54 % |
| A_HVR total | 274.9 mm² | 55.0 % of the 500 mm² die (June: 54 %) |
| tile side | 2.369 mm | |
| cell height | 720 µm | set by the 500 µm inductor |
| f_sw | 0.805 MHz | |
| efficiency | 88.89 % | June: 82.6 % end-to-end (theirs includes front-end conversion, this does not) |

## 4. Architectures and the thickness crossover (Sec. 4)

| arch | h_sub (mm) | P_elec (W) | P_TSV (mW) | T_max (°C) | warpage (µm) | |
|---|---:|---:|---:|---:|---:|---|
| ARCH_A | 0.80 | 125.076 | 0.21 | 84.54 | 11.163 | |
| ARCH_A | 1.00 | 125.043 | 0.73 | 84.30 | 6.775 | |
| ARCH_A | 1.25 | 125.028 | 1.38 | 84.21 | 4.048 | |
| ARCH_A | 1.50 | 125.022 | 2.03 | 84.17 | 2.619 | |
| ARCH_A | 2.00 | 125.014 | 3.33 | 84.13 | 1.272 | ← electrical optimum |
| ARCH_B | 0.80 | 125.085 | 9.19 | 84.54 | 11.163 | |
| ARCH_B | 1.00 | 125.075 | 32.16 | 84.30 | 6.776 | ← electrical optimum |
| ARCH_B | 1.25 | 125.089 | 60.86 | 84.21 | 4.049 | |
| ARCH_B | 1.50 | 125.112 | 89.57 | 84.17 | 2.619 | |
| ARCH_B | 2.00 | 125.162 | 146.98 | 84.13 | 1.272 | |

**ARCH_A: the electrical optimum is the thickest substrate — no conflict.** Electrics and mechanics want the same thing.

**ARCH_B: the electrical optimum is INTERIOR, at h = 1.00 mm.** Mechanics wants the thickest substrate; electrics do not. Going from the electrical optimum to the thickest costs **+0.0873 W** and saves **5.504 µm** — an exchange rate of **0.0159 W/µm**.

This is the three-domain result Phase 0E predicted would appear at scale: the LV rail's TSV loss grows with substrate thickness fast enough to turn the electrical curve around, while warpage keeps falling. **The conflict is real in sign.** It is also almost free: at 0.016 W/µm a designer buys the mechanical improvement for 0.07 % of system loss, which is not a tradeoff anyone would agonise over.

## 5. TSV feasibility at 1 kA (Sec. 5)

| J basis | arch | rail | I/VR (A) | I_max/via (mA) | n_req | n_avail | utilisation | feasible |
|---|---|---|---:|---:|---:|---:|---:|---|
| june2026 | ARCH_A | HV | 0.478 | 70.7 | 7 | 1558 | 0.0045 | True |
| june2026 | ARCH_B | LV | 20.408 | 70.7 | 289 | 1558 | 0.1855 | True |
| june2026 | ARCH_C | HV | 0.478 | 70.7 | 7 | 1558 | 0.0045 | True |
| ectc2024 | ARCH_A | HV | 0.478 | 282.7 | 2 | 1558 | 0.0013 | True |
| ectc2024 | ARCH_B | LV | 20.408 | 282.7 | 73 | 1558 | 0.0469 | True |
| ectc2024 | ARCH_C | HV | 0.478 | 282.7 | 2 | 1558 | 0.0013 | True |

**No architecture becomes infeasible at 1 kA.** Worst-case via-field utilisation across all 90 combinations of architecture, policy, thickness and current density is **18.5%**; all feasible = True. Distributing to 49 regulators means each via field carries only 20.4 A.

An independent check on the allocation model: ARCH_B needs 289 vias per tile, so **49 × 289 = 14 161 TSVs** for the system. June's own Table III allocates **14 148** to PL3. The two agree to **0.09 %**, from completely different directions.

The provisioning current density is kept distinct from an electromigration lifetime limit throughout. **No lifetime claim is made.**

## 6. A board-mounted metric was qualified before use (Sec. 6)

7 of 9 candidate metrics pass convergence (interface mesh 1/2/4) **and** ordering stability across nine material corners **and** resolution (> 2u_m = 1 %). Interface peel remains excluded.

| metric | ordering | min separation | verdict |
|---|---|---:|---|
| `die_warpage_pv_um` | stable | 72.31 % | QUALIFIED |
| `curvature_um_per_mm2` | stable | 60.18 % | QUALIFIED |
| `shear_p99_MPa` | stable | 2.83 % | QUALIFIED |
| `shear_p95_MPa` | stable | 13.30 % | QUALIFIED |
| `shear_raw_max_MPa` | stable | 1.18 % | QUALIFIED |
| `shear_excl050_p99_MPa` | stable | 2.82 % | QUALIFIED |
| `rel_disp_p99_um` | **UNSTABLE** | 4.71 % | REJECTED |
| `rel_disp_max_um` | stable | 2.58 % | QUALIFIED |
| `rel_disp_p95_um` | **UNSTABLE** | 3.63 % | REJECTED |

**Free die warpage itself qualifies as a mounted metric at 1 kW** (0.0 % convergence, stable in all nine corners, 72.3 % separation). That is a change from Phase 0E, where at 240 W the thickness lever lost warpage resolution entirely under BC-B (−56 % free became −0.14 % mounted). The difference is scale. Detail in `bcb_metric_validation.md`.

## 7-8. Footprint, in both assembly states (Sec. 7, 8)

**Package level (BC-A, free warpage):**

| A_HVR total (mm²) | M | P_elec (W) | T_max (°C) | free warpage (µm) |
|---:|---:|---:|---:|---:|
| 187.5 | 25 | 188.81 | 92.38 | 2.274 |
| 259.2 | 36 | 126.43 | 84.19 | 2.530 |
| 274.9 | 49 | 125.02 | 84.17 | 2.619 |
| 329.3 | 49 | 119.83 | 83.77 | 3.043 |

Over the comparable points (M >= 36): **-5.2 %** electrical for **+20.3 %** warpage, an exchange rate of **12.86 W/µm** against Phase 0E's 11.48 W/µm at 240 W. **The footprint opposition survives at the reference scale, at essentially the same price.**

One caveat is structural: at 1 kW only two current-density levels are placeable at fixed M, so the footprint axis had to be swept by varying M as well. Phase 0B established that regulator count is mechanically inert at constant total footprint, which is what licenses that substitution, but footprint and count are not fully separated here.

**Board-mounted (BC-B, qualified metric):**

| A_HVR total (mm²) | P_elec (W) | mounted warpage (µm) | curvature | shear p99 (MPa) |
|---:|---:|---:|---:|---:|
| 259.2 | 126.42 | 0.6703 | -2.434e-03 | 10.153 |
| 329.3 | 119.83 | 0.7091 | -2.863e-03 | 7.036 |

**The mounted ordering AGREES WITH the free-package ordering.**

## 9. Placement (Sec. 9)

| placement | scale | P_RDL (W) | P_elec (W) | T_max (°C) | free warpage (µm) |
|---|---:|---:|---:|---:|---:|
| uniform | 1.000 | 0.642 | 125.02 | 84.17 | 2.619 |
| compact | 0.907 | 4.836 | 129.66 | 86.33 | 2.901 |
| asymmetric | 0.907 | 8.735 | 133.75 | 86.61 | 3.000 |

Electrical spread **7.0 %** (Phase 0E at 240 W: 46.7 %); warpage spread 14.6 %. Electrically best = `uniform`, mechanically best = `uniform` -> **they AGREE — no conflict**.

The deeper result is that **placement has almost stopped being a variable**. At 1 kW the regulators occupy 55 % of the die and the lattice can be compacted by only **9.4 %** before the minimum-gap rule is violated (25 % at M = 16, 14.8 % at M = 36). The ETM placement conflict Phase 0E found at 240 W — the cheapest mechanical lever in the project at 3.70 W/µm — **does not exist at the reference scale, because there is no room left to move the regulators.**

## 10. No criterion was found; parametric sensitivity instead (Sec. 10)

The search for a source-backed mechanical criterion is recorded and it failed:

* June-2026, ECTC-2024, ISCAS-2024 and the internal deep-research report contain no numerical warpage, coplanarity, bump-displacement or strain limit.

* `WebSearch` is disabled by organisation policy in this environment.

* The Semantic Scholar API returned HTTP 429 on every attempt; the arXiv API surfaces no quantitative package-warpage specification.


```
G2 = NOT TESTED
```

**No criterion is invented, and safety is not inferred from a warpage magnitude.** Instead the question is inverted.

### PARAMETRIC CONSTRAINT SENSITIVITY (not feasibility)

* Candidate warpage spans **1.27 – 11.16 µm**.

* The electrically optimal candidate carries **3.043 µm**, so it is first excluded once **ε < 3.04 µm**.

* Complying then costs **+5.19 W (+4.33 %)** — the best admissible candidate becomes the thickest substrate.

* Below **ε ≈ 1.27 µm** the entire 1-kW candidate set is empty.


So a hypothetical limit only changes the answer if it falls inside the narrow band **1.27 – 3.04 µm**. Above it nothing is excluded; below it nothing is buildable. That is a substantive statement about how much room a criterion has to matter, and it is made **without** asserting where a real criterion would sit.

## 11. Crossover map (Sec. 11)

The load at which ARCH_B's thickness preference changes sign cannot be located by an electrical-only sweep: freezing temperature removes the converter-loss reduction that makes thickening attractive in the first place, and every load then prefers thin. The authoritative statement comes from the full ET fixed points:

* at **240 W** (Phase 0E, corrected geometry) ARCH_B still prefers the thickest substrate — margin 1.46× over its TSV penalty;

* at **1 kW** the electrical optimum moves to the **interior**, h ≈ 1.0 mm.


So the sign change occurs **between 240 W and 1 kW**. It is not resolved more finely here because each point costs a full ET fixed point with 49 regulators, and the answer would not change any Phase-0F conclusion: at 1 kW the conflict exists and costs 0.016 W/µm.

## 12-14. ET fixed point, validation and energy (Sec. 12, 13, 14)

* **ET fixed point**: every 1-kW candidate iterates electrical loss -> spatially mapped heat -> temperature -> per-VR local temperature -> updated loss to a 0.05 K tolerance, 4-4 iterations. Converter loss is driven by each tile's own volume-weighted temperature, never a single global maximum.

* **Independent thermal validation (MOOSE, 1 kW)**:


| case | CalculiX T_max (°C) | MOOSE T_max (°C) | difference | MOOSE energy residual |
|---|---:|---:|---:|---:|
| KW1_thin_h800 | 84.542 | 87.442 | +3.43 % | -0.000 % |
| KW1_thick_h1500 | 84.168 | 86.432 | +2.69 % | -0.000 % |

  Ordering (thin warmer than thick) is preserved in both solvers.

* **Icepak** was not used. Its Phase-0E failure (every object returning exactly 5000 K, a solver clamp caused by applying an external convective boundary to an internal solid/air interface) was not re-attempted, because MOOSE already provides an independent 3-D thermal solver and the gate must not depend on Icepak.

* **HFSS** was not re-run. The Phase-0E result — loop resistance flat to 0.18 % below the 19.1 MHz skin crossover — depends on via geometry and frequency, and neither changed: the TSV geometry is identical and f_sw moved from 0.286 to 0.805 MHz, still 24× below the crossover.

* **Heat-source scaling**: converter, BGA, C4, TSV, microbump, RDL and functional die heat are mapped separately and summed. Max |FE energy residual| across all 17 1-kW cases is **0.00003 %** against the 0.01 % acceptance criterion, and the source identity closes exactly.

\newpage
## 15. The nine questions (Sec. 15)

**Q1. Does any mechanical response become large and robust at 1 kW?** **Yes.** Free warpage reaches 11.16 µm, roughly 4× the 240 W vehicle, and — unlike at 240 W — it **qualifies as a board-mounted metric**, converging to 0.0 % and holding its ordering across all nine material corners with 72.3 % separation.

**Q2. Does it change the preferred substrate thickness?** For ARCH_A, no: electrics already prefer the thickest substrate. For **ARCH_B, yes** — electrics prefer 1.0 mm, mechanics prefers 2.0 mm.

**Q3. Does it change the preferred HVR footprint?** Only if a constraint binds. The opposition is real (12.86 W/µm) and electrics prefer the largest footprint while mechanics prefers the smallest, but with no criterion nothing forces the choice.

**Q4. Does it change placement preference?** **No.** Uniform placement is best both electrically and mechanically, and placement freedom has collapsed to 9.4 % compaction headroom.

**Q5. Does ARCH_B develop a real electrical/mechanical thickness conflict?** **Yes** — an interior electrical optimum at h ≈ 1.0 mm against a monotone mechanical preference. It costs 0.0873 W (0.07 %) to overrule, i.e. 0.016 W/µm.

**Q6. Do results survive BC-B / mounted conditions?** **Yes.** The qualified mounted metric preserves the free-package orderings; see Sec. 7-8.

**Q7. Does any source-backed criterion exclude the ET optimum?** **Unanswerable — no criterion exists.** G2 remains NOT TESTED.

**Q8. At what hypothetical ε would the ET optimum first be excluded?** **ε = 3.04 µm**, at a compliance cost of +5.19 W (+4.33 %). Below ε ≈ 1.27 µm nothing is admissible.

### The assembly state decides the sign

| arch | h_sub | BC-A free warpage (µm) | BC-B mounted warpage (µm) |
|---|---:|---:|---:|
| ARCH_A | 0.80 mm | 11.1626 | 0.3724 |
| ARCH_A | 1.50 mm | 2.6189 | 0.6765 |
| ARCH_B | 0.80 mm | 11.1627 | 0.3724 |
| ARCH_B | 2.00 mm | 1.2718 | 0.8893 |

* **ARCH_A, thin → thick:** free warpage **-76.5 %**, mounted warpage **+81.6 %** — **the sign REVERSES**.
* **ARCH_B, thin → thick:** free warpage **-88.6 %**, mounted warpage **+138.8 %** — **the sign REVERSES**.

**But not every lever reverses.** Taking each lever between its two extremes:

| lever | BC-A free | BC-B mounted | |
|---|---:|---:|---|
| thickness ARCH_A 0.8→1.5 mm | -76.54 % | +81.65 % | **SIGN REVERSES** |
| thickness ARCH_B 0.8→2.0 mm | -88.61 % | +138.77 % | **SIGN REVERSES** |
| footprint 259→329 mm² | +20.30 % | +5.79 % | preserved |
| placement uniform→compact | +10.78 % | +6.72 % | preserved |

**Only thickness reverses.** Footprint and placement keep their sign in both assembly states, merely compressed by the board restraint. That is the sharpest form of the Phase-0F result: the reversal is specific to the one lever that acts through the substrate's bending stiffness, which is exactly the quantity a board foundation overrides.


The mechanical preference for thickness is therefore **not a property of the design** — it is a property of the design **and its assembly state**. A framework that optimises free-package warpage and then mounts the package will move the substrate thickness in the wrong direction.

\newpage
## 16. Verdict (Sec. 16)

```
ASSEMBLY-STATE-DEPENDENT ETM CONSTRAINT
```

Warpage grew fourfold at the reference scale, and the brief is explicit that growth alone does not license a positive verdict. It does not. What licenses this verdict is something else: **the mechanical preference and the electrical preference change places depending on how the package is mounted, and both states are well resolved.**

* In the **free package**, thicker is strongly better mechanically. ARCH_A's electrics agree; ARCH_B's do not, giving an interior electrical optimum and a genuine three-domain conflict.

* In the **board-mounted** package, the mechanical preference **inverts** — the restrained thick substrate deforms the die *more*, not less — and the conflict swaps architectures. ARCH_B's electrical preference for a thinner substrate now agrees with mechanics, while ARCH_A acquires the conflict it did not have.

* Both states are **qualified**: mounted warpage converges to 0.0 %, holds its ordering across nine material corners, and separates candidates by 72 %. This is not numerical noise, and it is not the Phase-0E situation at 240 W where the mounted signal vanished below the resolution floor.


**Why this is not the stronger verdict.** Mechanics is not a *synthesis constraint* at 1 kW, because nothing binds: no source-backed criterion exists, and the mechanical improvement is so cheap in the free state (0.016 W/µm for ARCH_B thickness) that no designer would trade against it. A constraint that changes no decision is not a constraint.

**Why this is not the weaker verdict.** Mechanics is not merely a signoff quantity either, because the *direction* of the correct design move depends on an assembly-state choice that an electrical/thermal framework does not model at all. A DVPD framework that optimises the free package and then mounts the result will move the substrate thickness the wrong way. That is a design-relevant coupling, and it is invisible without the mechanical model.

**What would settle it.** A calibrated board foundation and one source-backed mechanical criterion. The BC-B stiffness is still PROVISIONAL and G2 is still NOT TESTED, so the reversal is established but its consequences cannot yet be priced.

## 17. Recommended next work — and it is not the optimiser

Phase 0F did not build the global ETM optimiser, and the case for building it has not improved. Two things are now clearly worth more:

1. **Calibrate the board foundation.** The single largest unknown in the mounted state, and the entire assembly-state reversal rests on it. A BGA unit-cell or board-level model would settle whether the reversal is a real design effect or an artifact of a PROVISIONAL stiffness.

2. **Obtain one mechanical criterion.** Without it G2 stays untested through a fourth phase and no feasibility statement is possible at any scale. The ε-band 1.27–3.04 µm says exactly how much precision is needed for a criterion to matter.


The remaining open items are unchanged from Phase 0E: GaN and MLCC layer heights, the RDL dielectric stack and stitching density, the electromigration lifetime limit, and assembly pre-stress (M1).

