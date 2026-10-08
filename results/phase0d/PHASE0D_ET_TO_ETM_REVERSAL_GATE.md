# Phase 0D — ET → ETM Reversal Gate

**Date:** 2026-09-03 · **Fidelity rung:** M0 (operational thermoelastic) + coupled ET fixed point
**Predecessors:** `results/phase0c/PHASE0C_DVPD_MECHANICAL_LEVER_GATE.md`, `results/phase0b/PHASE0B_FIRST_MECHANICAL_GATE.md`
**Solvers:** CalculiX 2.23 C3D8I direct (mechanics + thermal) · upstream `compute_total_loss` (converter, unmodified)
**Runs:** 7 reproduction + 1 C07_THICK + 28 coupled candidates (each with a 4–5 iteration ET fixed point) + 48 robustness = **~200 FEA solves**

---

## 1. Executive Verdict

# CONDITIONAL ET→ETM REVERSAL

Mechanics **materially changes the design choice**, but it does not overturn the electrically
optimal architecture, and converting the change into a definite decision requires a warpage
valuation or allowable that does not exist in sourced form.

**What changed.** Adding die warpage as a third objective expands the Pareto set from
**1 architecture to 6**, and the preferred *level* of three design variables changes:

| Variable | ET Pareto front | ETM Pareto front | changed? |
|---|---|---|---|
| **h_sub** | {500 µm} | {500 µm} | **no — outright agreement** |
| HVR footprint (total) | {154.4 mm²} | {45.0, 103.0, 137.3, 154.4 mm²} | **yes** |
| converter operating point J | {1.5} | {1.5, 2.0, 4.0} | **yes** |
| placement class | {distributed_3×2} | {distributed_2×2, distributed_3×2, edge_corner_biased} | **yes** |
| VR count | {6} | {4, 6} | **yes** |

**Why it is conditional and not proven.** With warpage entering as a *pure additional
objective*, the ET optimum holds the minimum P_elec by construction and therefore **can never
be Pareto-dominated**. A dominance reversal is structurally unreachable in this formulation.
Moving from the ET optimum (D23) to the best mechanical alternative on the front (D28) costs
**+5.30 W (+34.5 %) to gain −2.61 µm (−61 %)** — a rate of **2.03 W/µm**. The scalarised
winner only changes above **λ ≈ 1.8 W/µm**, and nothing in the repository or the sourced
literature values a micron of warpage in watts. The strongest form of the test (G2, feasible-set
reversal) needs an allowable and is therefore **NOT TESTED**.

**Three findings that matter more than the verdict label.**

1. **Substrate thickness shows no tradeoff at all — ET and ETM agree.** Closing the h_sub
   electrical path was the entire critical-path task of this phase, and the answer is that
   200 → 500 µm costs **+1.6 mW** of TSV resistance but saves **−146 mW** of converter loss by
   running 2.8 K cooler. Net electrical **−0.62 %**, thermal **−2.8 K**, mechanical **−57 %**.
   Thicker is better on all three axes. *The mechanical benefit is not overwhelmed
   electrically; it is reinforced.* Every member of both Pareto fronts uses 500 µm.

2. **Placement is nearly free electrically and dominant mechanically.** At identical
   converter, identical footprint and identical thickness, four placement classes span
   **1.08 % in electrical loss** but **240 % in die warpage** (1.670 → 5.678 µm). Package
   distribution loss is only **0.25–1.15 %** of total electrical loss once the RDL resistance
   is derived from geometry. The ET objective therefore cannot discriminate placement at all —
   the spread is inside model uncertainty — while mechanics discriminates it by 3.4×.
   **This is the cleanest ETM statement the project has produced**, and it is the one case
   where ET is genuinely indifferent and mechanics is decisive.

3. **Two uncalibrated defaults were exposed by actually running the electrical objective.**
   `r_tsv_ohm`/`r_bump_ohm` (the Phase-0C critical path) and `rho_mohm_per_mm = 50`. The latter
   is unphysical — it puts 2100 % IR drop on a 1 V / 60 A branch and drove one ET fixed point
   to 569 °C before it was replaced by a geometry-derived plane resistance. Phase 0D is the
   first phase to exercise the electrical objective at load, which is why it surfaced now.

**Caveat that bounds everything:** the decision change is largest on **placement**, which
Phase 0C classified as the *generic floorplanning* lever, not a DVPD-specific one. On the
DVPD-specific levers the picture is weaker: thickness agrees outright, and footprint requires
λ > 1.8 W/µm to change the winner.

---

## 2. Regression / Reproduction Check

Run before any code was modified.

**Baseline test suite:** 49 passed, 0 failed, 0 skipped — matches the Phase-0C close-out.

**Phase-0C mechanical reproduction** — all seven required cases **bit-exact**:

| Case | archived (µm) | rerun (µm) | Δ | T_max | energy residual |
|---|---:|---:|---:|---:|---:|
| C05 | 7.7720 | 7.7720 | 0.000 % | 83.234 | −0.000 % |
| C07 | 12.4808 | 12.4808 | 0.000 % | 87.218 | −0.000 % |
| C08 | 3.3415 | 3.3415 | 0.000 % | 77.470 | +0.000 % |
| C11 | 6.1259 | 6.1259 | 0.000 % | 87.481 | +0.000 % |
| C12 | 9.3730 | 9.3730 | 0.000 % | 80.175 | +0.000 % |
| C19 | 11.1350 | 11.1350 | 0.000 % | 80.638 | +0.000 % |
| C20 | 13.8266 | 13.8266 | 0.000 % | 93.797 | +0.000 % |

**Phase-0C effects** — all five reproduced to <0.5 pp:

| effect | Phase 0D | Phase 0C |
|---|---:|---:|
| substrate thickness C05→C08 | −57.01 % | −57.0 % |
| footprint C11 vs C05 | −21.18 % | −21.2 % |
| footprint C12 vs C05 | +20.60 % | +20.6 % |
| HVR heat C19 vs C07 | −10.78 % | −10.8 % |
| HVR heat C20 vs C07 | +10.78 % | +10.8 % |

VR count remains inert (C05 vs C13 = +0.02 %, unchanged). **REPRODUCTION VERIFIED.**

---

## 3. Electrical Model Upgrade

Full specification and validation in `electrical_model_validation.md`. Summary:

### 3.1 TSV resistance — geometry-derived

```
R_single(h,d,T) = rho_Cu(T) * h / (pi d^2/4)      R_field = R_single / n_parallel
n_parallel = min( ceil(I / I_via_max), n_available(footprint, pitch) )
```

| check | result |
|---|---|
| **June-2026 Table III baseline** (Cu, d=30 µm, h=300 µm, 20 °C) | **7.215 mΩ vs 7.1 mΩ quoted → +1.62 %** |
| R ∝ h | exact (2.000000 for 2×) |
| R ∝ 1/d² | exact (0.250000 for 2×) |
| R ∝ 1/n | exact (0.250000 for 4 parallel) |
| ρ_Cu(T) | ρ(125)/ρ(20) = 1.41265 = 1 + α·105 |
| positivity / h ≤ 0 rejected | pass |

23 checks in `tsv_resistance_validation.csv`; max deviation from closed form **2.8e-14 %**.

**A consequential modelling finding.** In the validated Phase-0B/0C stack the HVR tile is
embedded at the **top** of the substrate, so the TSV field spans the board side up to the tile
underside and carries **converter INPUT current at 48 V** — 41× smaller than the output
current. The resulting TSV loss is **0.23 mW at 200 µm and 0.58 mW at 500 µm**. Even under a
June-like *output-side* variant it is only 9.5 → 23.8 mW. Sizing vias by current density makes
`P = I·ρ·h·I_via_max/A` — linear, not quadratic, in current — so the term stays small either
way. **Reported, not hidden: the direct resistive cost of substrate thickness is negligible in
this architecture.**

### 3.2 Temperature dependence

| Quantity | Law | Coefficient | Status |
|---|---|---:|---|
| ρ_Cu (TSV, RDL, inductor DCR) | ρ₂₀[1+α(T−20)] | 3.93e-3 /K | ASSUMPTION (bulk Cu, same as `configs/phase0b`) |
| GaN R_DS(on) | R₂₅[1+α(T−25)] | 7.5e-3 /K | **ASSUMPTION** — the EPC table in this repo has **no temperature columns**; swept 0.005/0.0075/0.010 |
| Inductor DCR | copper winding | α_Cu | MODEL_DERIVED |
| Capacitor ESR, gate charges, C_OSS | not made T-dependent | — | **OPEN** — unsupported here, deliberately not invented |

Magnitude: converter loss rises **+21 %** from 25 °C to the ~73 °C operating point. Temperature
coupling is a first-order effect, not a refinement.

### 3.3 HVR footprint geometry — PARTIAL, and why

The compiler's internal geometry is `EPCDevice.footprint_mm2` (area only, parsed from the
Package string) and `Inductor.footprint_mm2` + `height_um`. **No component carries a width and
a length separately**, so no physically meaningful rectangle can be derived. Per the brief's
instruction not to invent an aspect ratio, the **square-tile approximation is retained and made
explicit** in `HVRDesign.footprint_xy_mm` (`A_x = A_y = √A`). This is consistent with Phase 0C's
finding that aspect ratio is mechanically inert (−1.76 %, below band), so it does not affect the
conclusions. Emitting real A_x × A_y is a component-library task, not a solver task.

**What the compiler does supply and Phase 0D does use:** the area budget `A_budget = I_out/J`
sets both footprint and achievable switch sizing, so footprint and converter loss are coupled
outputs of one decision — the June per-layer-area-budget mechanism:

| J (A/mm²) | A_budget/VR | chosen area | loss @25 °C | architecture |
|---:|---:|---:|---:|---|
| 4.0 | 15.0 mm² | 15.00 mm² | 6.592 W | N=4, K=4, K_A=2 |
| 2.0 | 30.0 mm² | 25.74 mm² | 4.248 W | N=3, K=3, K_A=2 |
| 1.5 | 40.0 mm² | 34.32 mm² | 3.420 W | N=4, K=4, K_A=2 |

### 3.4 A second uncalibrated default, found by running the objective

`DieConfig.rho_mohm_per_mm = 50` was flagged by Phase 0A as "not derived from trace geometry".
It is **unphysical**: 2100 % IR drop on a 1 V / 60 A / 7 mm branch. Candidate D02 produced
P_PDN = 2781 W against a 240 W load and an ET fixed point at 569 °C. Replaced by

```
R_per_mm = rho_Cu(T) / (t_Cu * W_eff)  =  0.155 mOhm/mm at 25 degC
```

with t_Cu = 5 µm (ASSUMPTION, the Phase-0A recorded RDL thickness) and W_eff = 22.36 mm
(MODEL_DERIVED, die width — power is delivered on a plane, not a trace). This gives 6.4 % IR
drop for 60 A over 7 mm, the right order against June's reported <2.7 % at 1 kA. POL
segmentation was also refined from 4 to **100 segments**, matching June. A validity guard now
rejects any candidate with P_PDN > 50 % of the die load.

### 3.5 Lateral PDN fidelity

The lateral network was re-implemented in the Phase-0D layer (leaving the separate
`Scalable_Integrated_VR` git repository and its large untracked body of work untouched) and is
**numerically identical to the upstream `DVPDRoutingModel.compute_ppdn_loss`** — relative
difference **0.00e+00** on three independent configurations. The exact upstream patch that
should eventually be merged is recorded in `electrical_model_validation.md` §0.

---

## 4. C07-Thick Interaction Closure

Phase 0C could not isolate thickness × asymmetry because no asymmetric case existed at
h_sub = 500 µm. Exactly one case was added — **C07_THICK ≡ C07 with h_sub = 500 µm** — run
through the unmodified Phase-0C flow. **The frozen C01–C20 DOE was not renumbered**; the case
is an in-memory addendum, and a test asserts the on-disk DOE still contains exactly C01–C20.

| quantity | value |
|---|---:|
| C07_THICK die warpage | **5.4638 µm** |
| C07_THICK T_max | 82.312 °C |
| energy-balance residual | +0.0000 % |

| comparison | thickness effect |
|---|---:|
| distributed placement, C05 → C08 | **−57.01 %** |
| asymmetric placement, C07 → C07_THICK | **−56.22 %** |
| **interaction residual** | **+0.78 pp** |

**Separable.** The Phase-0C separability result is *strengthened*: the thickness effect is now
measured across four placement configurations (N=2 compact, N=4 distributed, N=6 distributed,
N=4 asymmetric) and spans only **0.79 pp** (−56.22 % to −57.01 %). Substrate thickness acts as
an almost perfect multiplier on warpage, independent of where the regulators sit — the property
that makes it tractable inside an optimizer.

---

## 5. ET Fixed-Point Formulation

```
T -> R_DS(on)(T), DCR(T), rho_Cu(T) -> P_conv, P_PDN -> heat sources -> FEA thermal -> T
```

The **validated Phase-0B/0C FEA thermal model** runs inside the loop — not a compact surrogate —
at the SENS mesh for iteration speed, with the final mechanical replay at the production mesh.
Mechanics sits **outside** the loop because M0 linear thermoelasticity has no back-action on the
electrical or thermal problem.

Convergence: `|ΔT_max| < 0.05 K` **and** `|ΔP_elec|/P_elec < 1e-3`, max 20 iterations. A
candidate that fails to converge is **rejected**, never reported at its last iterate. All 28
candidates converged in **4–5 iterations**; energy balance closes to **±0.000 %** throughout.
Histories archived in `fixed_point_histories/`.

---

## 6. Candidate Architecture Set

28 candidates spanning the three Phase-0C DVPD levers plus placement. Converter loss is **never
swept manually** — it is an outcome of the area budget through the real optimizer.

| dimension | levels |
|---|---|
| VR count N | 4, 6 |
| area budget J (→ footprint **and** converter loss) | 4.0, 2.0, 1.5 A/mm² → 45–154 mm² total |
| substrate thickness h_sub | 200, 500 µm |
| placement | distributed (2×2 / 3×2), asymmetric_left; plus compact_2×2_central and edge_corner_biased at N=4, J=2.0 |

Placement classes are count-specific, so the grid names a *family* resolved per count. (A first
pass used `distributed_2x2` for every count and silently skipped all N=6 distributed candidates;
caught by inspecting the run log, fixed, and the full set re-run.)

**Feasibility:** 28 converged, **27 pass** the frozen ET filter. D14 (N=6, J=4, h=200 µm,
asymmetric) is excluded on **T_max = 102.11 °C > 100 °C**.

---

## 7. ET-Only Results

Ranking frozen in `ET_OBJECTIVE_DEFINITION.md` **before** any mechanical evaluation (file mtime
precedes the candidate results; a test asserts the ordering). Objective: minimise
`P_elec_total = P_conv + P_PDN`; Pareto on `(P_elec, T_max)`.

| rk | cand | N | J | h_sub | placement | A_tot mm² | P_conv W | P_PDN W | P_elec W | η % | T_max °C | ET front |
|---:|---|--:|--:|--:|---|--:|--:|--:|--:|--:|--:|:-:|
| 1 | **D23** | 6 | 1.5 | 500 | distributed_3×2 | 154.4 | 15.24 | 0.14 | **15.37** | **93.980** | **65.34** | **★** |
| 2 | D21 | 6 | 1.5 | 200 | distributed_3×2 | 154.4 | 15.27 | 0.13 | 15.41 | 93.968 | 66.46 | |
| 3 | D24 | 6 | 1.5 | 500 | asymmetric_left | 154.4 | 15.30 | 0.15 | 15.46 | 93.949 | 66.85 | |
| 4 | D22 | 6 | 1.5 | 200 | asymmetric_left | 154.4 | 15.33 | 0.15 | 15.48 | 93.940 | 67.62 | |
| 5 | D11 | 4 | 1.5 | 500 | distributed_2×2 | 137.3 | 16.21 | 0.17 | 16.39 | 93.608 | 66.41 | |
| 6 | D09 | 4 | 1.5 | 200 | distributed_2×2 | 137.3 | 16.27 | 0.17 | 16.45 | 93.586 | 67.98 | |
| 7 | D12 | 4 | 1.5 | 500 | asymmetric_left | 137.3 | 16.28 | 0.19 | 16.47 | 93.577 | 67.67 | |
| 8 | D10 | 4 | 1.5 | 200 | asymmetric_left | 137.3 | 16.34 | 0.19 | 16.53 | 93.558 | 68.94 | |
| 9 | D19 | 6 | 2 | 500 | distributed_3×2 | 103.0 | 18.94 | 0.10 | 19.04 | 92.650 | 67.38 | |
| 13 | D07 | 4 | 2 | 500 | distributed_2×2 | 103.0 | 20.34 | 0.18 | 20.51 | 92.126 | 68.68 | |
| 15 | D28 | 4 | 2 | 500 | edge_corner_biased | 103.0 | 20.47 | 0.20 | 20.67 | 92.071 | 70.43 | |
| 17 | D27 | 4 | 2 | 500 | compact_2×2_central | 103.0 | 20.55 | 0.18 | 20.73 | 92.048 | 72.20 | |
| 21 | D03 | 4 | 4 | 500 | distributed_2×2 | 60.0 | 34.26 | 0.18 | 34.44 | 87.452 | 76.91 | |
| 25 | D15 | 6 | 4 | 500 | distributed_3×2 | 45.0 | 42.04 | 0.11 | 42.15 | 85.062 | 80.23 | |
| 27 | D16 | 6 | 4 | 500 | asymmetric_left | 45.0 | 43.94 | 0.14 | 44.07 | 84.485 | 91.80 | |

*(abridged; full 27 rows in `et_ranking.csv`)*

**The ET Pareto front is a single point, D23** — it simultaneously holds the minimum
`P_elec` and the minimum `T_max`, so nothing else is non-dominated. ET alone therefore
prescribes exactly one architecture: 6 VRs, largest available footprint (154.4 mm²), 500 µm
substrate, distributed 3×2.

Two structural observations from the ET table alone:

- **Footprint dominates the electrical objective.** J = 4 → 1.5 (45 → 154 mm²) improves
  efficiency from 84.5 % to 94.0 %. Nothing else comes close.
- **P_PDN is 0.25–1.15 % of P_elec.** After the geometry-derived RDL correction, package
  distribution loss is almost negligible, so the electrical objective is essentially the
  converter loss. This is why placement barely registers electrically.

---

## 8. Mechanical Replay

Converged heat sources from each ET fixed point replayed through the validated M0 model at the
production mesh, BC-A. **Only die warpage is admitted as the mechanical objective.** Per
Phase 0C: interface peel is UNRESOLVED AT M0 and excluded; H0 local Si/Cu stress is invalid
(+82–97 % vs discrete) and excluded. Package warpage and interface shear are recorded as
secondary but do not enter any ranking — enforced by unit test.

Die warpage across the 27 feasible candidates spans **1.575 – 14.332 µm (9.1×)**.

The H0 → H1 absolute-bias correction (**−6 to −9 %** on warpage) from Phase 0C was **not
applied**, because it is a systematic multiplier common to every candidate and therefore cannot
change any ranking or Pareto membership. Applying it would only shift all warpages together;
doing so to improve a result would be exactly the manipulation the brief forbids. It is carried
as a stated bias on absolute values.

---

## 9. ET vs ETM Ranking

**ETM Pareto front** — `(P_elec, T_max, die warpage)`, 6 members:

| cand | N | J | h_sub | placement | P_elec W | T_max °C | warpage µm | ET rank | on ET front? |
|---|--:|--:|--:|---|--:|--:|--:|--:|:-:|
| **D23** | 6 | 1.5 | 500 | distributed_3×2 | 15.37 | 65.34 | 4.281 | 1 | **yes** |
| D11 | 4 | 1.5 | 500 | distributed_2×2 | 16.39 | 66.41 | 3.714 | 5 | no |
| D19 | 6 | 2 | 500 | distributed_3×2 | 19.04 | 67.38 | 2.895 | 9 | no |
| D07 | 4 | 2 | 500 | distributed_2×2 | 20.51 | 68.68 | 2.884 | 13 | no |
| D28 | 4 | 2 | 500 | edge_corner_biased | 20.67 | 70.43 | **1.670** | 15 | no |
| D15 | 6 | 4 | 500 | distributed_3×2 | 42.15 | 80.23 | **1.575** | 25 | no |

**Mechanics expands the Pareto set from 1 to 6.** Five architectures that ET alone would never
surface become non-dominated once warpage is counted — including D28 at ET rank 15 and D15 at
ET rank 25.

Tradeoff rates against the ET optimum:

| alternative | ΔP_elec | Δwarpage | rate |
|---|---:|---:|---:|
| D11 | +1.02 W (+6.6 %) | −0.566 µm (−13.2 %) | 1.79 W/µm |
| D28 | +5.30 W (+34.5 %) | −2.610 µm (−61.0 %) | 2.03 W/µm |
| D19 | +3.67 W (+23.9 %) | −1.386 µm (−32.4 %) | 2.65 W/µm |
| D07 | +5.14 W (+33.4 %) | −1.397 µm (−32.6 %) | 3.68 W/µm |
| D15 | +26.78 W (+174.2 %) | −2.706 µm (−63.2 %) | 9.90 W/µm |

**Scalarisation sensitivity** (reported only; no claim rests on any λ). The λ that equalises the
two objective spans is 2.25 W/µm.

| λ (W/µm) | 0 | 0.01 | 0.05 | 0.1 | 0.25 | 0.5 | 1.0 | **2.0** | **5.0** |
|---|---|---|---|---|---|---|---|---|---|
| winner | D23 | D23 | D23 | D23 | D23 | D23 | D23 | **D11** | **D28** |

The winner is stable up to λ ≈ 1.8 W/µm and only then switches. **The conclusion does depend on
λ, which is precisely why the verdict is conditional rather than proven.**

---

## 10. G1 Architecture-Reversal Test

### Result: **PASS in the level-change sense, FAIL in the dominance sense**

The frozen definition admitted two forms of reversal. They give different answers, and both are
reported.

**Form (a) — the ET optimum becomes Pareto-dominated: FAIL, and structurally so.**
D23 holds the minimum P_elec among all candidates. With warpage added as a *pure additional
objective*, no candidate can dominate it. This is not a property of the data — it is a property
of the formulation. **A dominance reversal is unreachable unless warpage enters as a
constraint**, which is G2 and requires an allowable. This is the single most important
structural finding of Phase 0D for how the eventual paper must be framed.

**Form (b) — the preferred level of a DVPD variable or placement class differs: PASS.**

| variable | ET front | ETM front | verdict |
|---|---|---|---|
| h_sub | {500 µm} | {500 µm} | **no change — agreement** |
| HVR footprint | {154.4} | {45.0, 103.0, 137.3, 154.4} mm² | **changed** |
| converter operating point J | {1.5} | {1.5, 2.0, 4.0} | **changed** |
| placement class | {distributed_3×2} | {distributed_2×2, distributed_3×2, edge_corner_biased} | **changed** |
| VR count | {6} | {4, 6} | **changed** |

Is the change *material* rather than a rank shuffle? Yes: D28 sits at **ET rank 15 of 27** and
D15 at **rank 25 of 27**. These are not near-ties being reordered — they are architectures the
electrical objective actively disfavours, which mechanics promotes to non-dominated.

**But the honest qualifier:** the level change on the strongest DVPD lever (h_sub) is *absent*,
and acting on the footprint change requires λ > 1.8 W/µm. **G1 therefore passes conditionally.**

---

## 11. G2 Feasible-Set Test

# NOT TESTED

A repository-wide search for a defensible warpage or stress allowable returns exactly one
numeric value: `w_allow = 50 µm`, recorded in `NOVELTY_BOUNDARY_ETM.md` and explicitly labelled
**"ASSUMPTION — NOT A PUBLICATION-GRADE RELIABILITY LIMIT"**. No source-backed die-warpage
limit, assembly flatness limit, or package-level warpage requirement exists in the collected
literature or configuration.

Per the brief, G2 stops there. Two further observations, so the omission is understood rather
than merely recorded:

1. Every candidate in this study lies between **1.575 and 14.332 µm**, far inside even the
   unsourced 50 µm figure. **No design would be excluded**, so a feasibility reversal is
   structurally impossible on this vehicle at this power scale regardless of which plausible
   allowable were chosen.
2. Consequently, obtaining a G2 result is not a matter of computation but of **either sourcing a
   real allowable or scaling the benchmark to the kW regime** where warpage grows enough to
   approach one. That is a scoping decision, recorded in §16.

---

## 12. Lever-by-Lever Coupled Tradeoffs

### 12.1 Substrate thickness — no tradeoff exists

The chain this phase was created to close: `h_sub → TSV length → R_TSV → P_PDN → η → heat → T → warpage`.

| quantity | 200 µm | 500 µm | change |
|---|---:|---:|---|
| R_TSV field (per VR) | 128.1 µΩ | 318.2 µΩ | **+148 %** (the only direct penalty) |
| P_TSV | 1.11 mW | 2.75 mW | +1.64 mW |
| T_max | 72.70 °C | 69.87 °C | −2.83 K |
| P_conv | 20.581 W | 20.436 W | **−0.146 W** |
| **P_elec total** | 27.478 W | 27.307 W | **−0.62 %** |
| efficiency | — | — | **+0.058 pp** |
| die warpage | — | — | **−57 %** |

**The TSV penalty is real but is outweighed 89× by the temperature-mediated converter benefit.**
Thicker substrate is better electrically, thermally and mechanically. Every Pareto member at
either level uses 500 µm. `PHASE0D_THICKNESS_TRADEOFF.png`.

This is a clean negative result for the "three-domain tension" hypothesis on this lever: the
tension was expected, it was looked for with the physics properly coupled, and it is not there
in this architecture. It would only appear if the vertical field carried output current *and*
the via count were area-limited rather than current-limited.

### 12.2 HVR footprint — the one genuine opposition

| J | A_total | P_conv | P_elec | η | T_max | warpage |
|---:|---:|---:|---:|---:|---:|---:|
| 4.0 | 60.0 mm² | 34.26 W | 34.44 W | 87.45 % | 76.91 °C | **1.969 µm** |
| 2.0 | 103.0 mm² | 20.34 W | 20.51 W | 92.13 % | 68.68 °C | 2.884 µm |
| 1.5 | 137.3 mm² | 16.21 W | 16.39 W | 93.61 % | 66.41 °C | **3.714 µm** |

*(N=4, distributed, h_sub = 500 µm)*

Larger footprint buys **+6.2 pp of efficiency** and **−10.5 K** but costs **+89 % warpage**.
This is the only lever where the electrical and mechanical objectives point in opposite
directions, and it is genuinely DVPD-specific: footprint is not a free floorplanning choice but
the per-layer area budget that sets switch sizing.

### 12.3 Converter loss — an outcome, not a knob

Converter loss is produced by the optimizer from the area budget, so it is not independently
swept in Phase 0D. Its coupling is visible along the footprint sweep above: P_conv falls
34.26 → 16.21 W as area grows, and warpage rises with the inclusion volume that buys it. The
Phase-0C direct sensitivity (±25 % HVR heat → ±10.8 % warpage, exactly linear) was reproduced
bit-exactly in §2 and remains the calibration for this path.

### 12.4 Placement — nearly free electrically, dominant mechanically

At **identical** converter, footprint and substrate thickness (N=4, J=2.0, h=500 µm):

| placement | P_elec | Δ vs best | warpage | Δ vs worst |
|---|---:|---:|---:|---:|
| edge_corner_biased (D28) | 20.67 W | +0.76 % | **1.670 µm** | −70.6 % |
| distributed_2×2 (D07) | **20.51 W** | — | 2.884 µm | −49.2 % |
| asymmetric_left (D08) | 20.69 W | +0.85 % | 4.536 µm | −20.1 % |
| compact_2×2_central (D27) | 20.73 W | +1.08 % | **5.678 µm** | — |

**Electrical spread 1.08 %. Mechanical spread 240 %.**

The electrical spread is inside the model's own uncertainty, so the ET objective cannot
meaningfully rank these four. Mechanics ranks them decisively. This is the strongest
demonstration in the project that a coupled formulation decides something an ET formulation
cannot — with the caveat that placement is the *generic* lever, the one STAMP-2.5D and ATMPlace
already optimise.

---

## 13. Robustness

48 runs across 12 corners — 4 electrical (new in Phase 0D) and 8 mechanical (carried from
Phase 0C) — applied only to the architectures involved in the conclusion, per the brief.

**Electrical corners:** α_GaN ∈ {0.005, 0.0075, 0.010} /K (the ASSUMPTION with no repository
source) and I_via_max ∈ {4.8, 33} mA (the OPEN per-via limit).
**Mechanical corners:** HVR tile E and CTE, underfill CTE, TSV field off, and the H0→H1
homogenisation bias correction (+12.59 % on tsv_homog CTE).

### 13.1 The reversal pair — D23 (ET optimum) vs D28 (ETM alternative)

| corner | ET P_elec | ET warp | alt P_elec | alt warp | ET cheaper? | alt flatter? | switch λ (W/µm) |
|---|---:|---:|---:|---:|:-:|:-:|---:|
| ref | 15.37 | 4.279 | 20.67 | 1.659 | ✓ | ✓ | 2.021 |
| α_GaN lo (0.005) | 14.94 | 4.262 | 19.94 | 1.637 | ✓ | ✓ | 1.905 |
| α_GaN hi (0.010) | 15.81 | 4.296 | 21.41 | 1.681 | ✓ | ✓ | 2.141 |
| I_via 4.8 mA | 15.37 | 4.279 | 20.67 | 1.659 | ✓ | ✓ | 2.021 |
| HVR E lo / hi | 15.37 | 4.424 / 4.147 | 20.67 | 1.726 / 1.597 | ✓ | ✓ | 1.963 / 2.077 |
| HVR CTE lo / hi | 15.37 | 4.640 / 3.556 | 20.67 | 1.831 / 1.317 | ✓ | ✓ | 1.885 / 2.365 |
| underfill CTE lo / hi | 15.37 | 4.343 / 4.214 | 20.67 | 1.704 / 1.614 | ✓ | ✓ | 2.007 / 2.037 |
| **H0 bias corrected** | 15.37 | 5.717 | 20.67 | 2.225 | ✓ | ✓ | **1.517** |
| TSV field off | 15.37 | 1.261 | 20.67 | 0.633 | ✓ | ✓ | 8.430 |

**Ordering preserved at 12/12 corners.** Switch-λ median **2.021 W/µm**; range
**1.517 – 2.365** excluding the `tsv_off` case (8.43), which is an architecture variant rather
than an uncertainty — removing the copper collapses the warpage difference the lever acts on.

Notably the **α_GaN sweep barely moves the answer** (1.905 → 2.141 W/µm across a 2× change in
the coefficient), so the one electrical ASSUMPTION with no repository source is not load-bearing.

### 13.2 The footprint lever direction

| test | result |
|---|---|
| electrical objective favours LARGE footprint | **12 / 12 corners** |
| mechanical objective favours SMALL footprint | **12 / 12 corners** |
| tradeoff rate (60 → 137 mm² pair), excl. tsv_off | 7.79 – 12.21 W/µm |

The opposition is unconditional across every corner tested. Only its *price* moves.

### 13.3 Classification

# CONDITIONAL REVERSAL

Not `NUMERICALLY FRAGILE` — the ordering survives 12/12 corners and the switch threshold is
tightly bounded. Not `ROBUST REVERSAL` — the ET optimum is never dominated, and acting on the
change requires valuing warpage above ~1.5–2.4 W/µm, which nothing in the sourced material
supports.

**Not tested here:** the BC-B support envelope. Phase 0C established that under a
board-restrained support all architecture effects — DVPD-specific and generic alike — fall to
the model's numerical floor. Every Phase-0D conclusion is therefore a **BC-A (free-warpage)
result**, exactly as in Phase 0C, and inherits that limitation unchanged.

---

## 14. Novelty Consequence

**1. Does mechanics change the preferred DVPD architecture?**
Partly. It expands the Pareto set from 1 to 6 and changes the preferred level of HVR footprint,
converter operating point, VR count and placement class. It does **not** overturn the
electrically optimal architecture, and it cannot: with warpage as a pure additional objective
the minimum-loss design is non-dominated by construction. The honest statement is that
mechanics **converts a single-point electrical optimum into a genuine tradeoff curve**, and
decides a placement question the electrical objective cannot resolve at all.

**2. Which DVPD variable causes the change?**
**HVR footprint**, and only it among the DVPD-specific levers. Larger footprint buys +6.2 pp
efficiency and −10.5 K but costs +89 % warpage, and this opposition holds at 12/12 corners.
Substrate thickness — the largest Phase-0C mechanical lever — produces **no tension at all**
once coupled: it improves all three domains simultaneously. Converter loss acts through
footprint rather than independently.

**3. Is the change impossible to obtain from an ET-only formulation?**
For footprint, yes in the sense that ET alone drives it monotonically to the maximum the area
budget allows, with no interior optimum; only a mechanical objective creates a reason to stop
short. For placement the answer is stronger: at fixed converter, footprint and thickness the
four placement classes differ by **1.08 % electrically — inside model uncertainty — and 240 %
mechanically**. An ET formulation is genuinely blind there. That is the cleanest case in the
project of mechanics deciding something electrical analysis cannot.

**4. Is this stronger than adding chiplet warpage to STAMP/ATMPlace?**
Partially, and the honest answer is uncomfortable. The *largest* decision change is on
placement, which is precisely what STAMP-2.5D and ATMPlace already do — our contribution there
is applying it to regulators. What they cannot do is the footprint lever: chiplet area is a
fixed input, whereas HVR cell area is an output of converter sizing through the per-layer area
budget, and its dissipation changes with it. So the DVPD-specific content is real but narrower
than Phase 0C's ranking suggested, because thickness — the lever that looked most promising —
turned out to have no electrical opposition.

**5. What exact claim is now defensible?**

> In distributed vertical power delivery, converter footprint is simultaneously an electrical
> design variable (it sets the per-layer area budget and hence switch sizing and conversion
> loss) and a mechanical one (it sets the CTE-mismatched inclusion volume and hence package
> warpage), and the two point in opposite directions. An electrical/thermal-only formulation
> drives footprint monotonically to its maximum; including warpage turns it into a bounded
> tradeoff whose Pareto set contains six architectures rather than one. Placement, by contrast,
> is nearly free electrically (1.08 % spread, within model uncertainty) while spanning 240 % in
> warpage, so it is decidable only under a coupled formulation.

What is **not** defensible: that mechanics overturns the electrically optimal design; that
substrate thickness creates a three-domain tension (it does not — it is win/win/win); or any
feasibility claim, since no allowable exists.

---

## 15. What Is Proven / Supported / Provisional / Open

**PROVEN** (measured, converged, robust across the corners tested)
- Substrate thickness improves all three domains: 200 → 500 µm gives −0.62 % electrical loss,
  −2.83 K, −57 % warpage. The TSV penalty (+1.6 mW) is outweighed 89× by the temperature-driven
  converter saving (−146 mW).
- Thickness × asymmetry is separable: −56.22 % (asymmetric) vs −57.01 % (distributed),
  residual +0.78 pp; now measured across four placement configurations spanning 0.79 pp.
- HVR footprint opposition: electrical favours large and mechanical favours small at **12/12**
  material and electrical corners.
- At fixed converter/footprint/thickness, placement spans 1.08 % electrically and 240 %
  mechanically; PDN loss is 0.25–1.15 % of total electrical loss.
- Mechanics expands the Pareto set from 1 to 6 architectures; the added members sit at ET ranks
  5, 9, 13, 15 and 25 of 27.
- The geometry-derived TSV model reproduces June-2026's 7.1 mΩ to +1.62 % and every scaling law
  to machine precision.
- Phase-0C reproduces bit-exactly; all ET fixed points converge in 4–5 iterations with energy
  balance ±0.000 %.

**SUPPORTED** (measured, with a stated caveat)
- The ET optimum cannot be Pareto-dominated by a pure added objective — a structural property of
  the formulation, demonstrated here but not specific to this data.
- Switch-λ ≈ 1.5–2.4 W/µm (median 2.02) for the D23 → D28 decision.
- Temperature raises converter loss ~21 % from 25 °C to the operating point.
- α_GaN is not load-bearing: a 2× change moves switch-λ by only 12 %.

**PROVISIONAL**
- All absolute warpage values (H0 bias −6 to −9 %, PROVISIONAL `hvr_effective` card).
- α_GaN = 7.5e-3 /K, RDL t_Cu = 5 µm, W_eff = die width.
- The square-tile footprint approximation.

**OPEN**
- Any mechanical allowable — hence G2.
- Per-via current limit (33 mA vs 4.8 mA); shown not to matter here, but unresolved.
- Capacitor ESR and gate-charge temperature dependence.
- ANSYS cross-validation (licence blocker unchanged: `lmgrd` not running on pinback, licence
  file owned by another user).
- BC-B behaviour of the coupled model — Phase 0D is BC-A only.
- Real A_x × A_y from the component libraries.

**NOT TESTED**
- G2 feasible-set reversal.
- kW-scale behaviour, where warpage may approach a real allowable.
- Transient response; assembly pre-stress (M1 rung).

---

## 16. Exact Next Gate

**Not started. Recommendation only.**

A conditional — not robust — reversal was found. Per the brief's next-gate logic, that calls for
**targeted closure before** committing to a full ETM synthesis framework. Building a global
optimizer now would be optimising a tradeoff whose exchange rate is unknown.

# PHASE 0E — TARGETED CLOSURE OF THE CONDITIONAL REVERSAL

Three closures, in priority order. Each converts a specific "conditional" into a decision.

1. **Source a die-warpage allowable, or scale to the kW regime.** This is the single highest
   -value action and it unlocks G2. Every candidate here sits at 1.6–14.3 µm, far inside any
   plausible limit, so **no feasibility reversal is reachable at 240 W regardless of computation**.
   Either (a) obtain a source-backed allowable for this package class, or (b) scale the benchmark
   to the 1 kW / 500 mm² June reference where warpage grows roughly with dissipation and may
   actually approach one. Option (b) also aligns the vehicle with the baseline the paper must
   compare against.

2. **Close the exchange rate, or reformulate to avoid needing it.** The verdict hinges on
   whether 2 W/µm is a good trade, and nothing sources that. Two routes: derive a warpage cost
   from an interconnect-reliability model (turning µm into failure risk), or reformulate warpage
   as an ε-constraint so the answer becomes "what is the cheapest design meeting a warpage cap"
   — which needs (1) but avoids a scalar valuation entirely. **The ε-constraint route is
   preferred** and is the natural formulation for the eventual synthesis problem.

3. **Extend to BC-B.** Every Phase-0C and Phase-0D conclusion is a free-warpage result. Phase 0C
   showed a board-restrained support collapses all architecture effects toward the numerical
   floor. If the intended product is board-mounted, the entire mechanical argument needs
   re-establishing under that support, and interface shear rather than warpage becomes the
   discriminating observable.

**Supporting work that should run alongside, not before:** source the `hvr_effective` material
card (still the dominant magnitude uncertainty); emit real A_x × A_y from the component
libraries; restore ANSYS for an independent cross-check.

**Do NOT yet build the full ETM Pareto/synthesis framework (the original Phase-0E scope).** The
coupling is now credible and instrumented — that is what Phase 0D established — but the
objective that a synthesis framework would optimise is not yet well-posed, because the
mechanical side has neither a constraint nor a price. Building the optimizer before closing
item 1 or 2 would produce a framework whose answer is set by an arbitrary λ, which is precisely
the failure mode the Phase-0A reviewer audit warned about.

---

### Artifacts

```
results/phase0d/
  PHASE0D_ET_TO_ETM_REVERSAL_GATE.md    this report
  ET_OBJECTIVE_DEFINITION.md            frozen BEFORE the mechanical replay (mtime-checked by test)
  electrical_model_validation.md        TSV / temperature / footprint / RDL specification
  tsv_resistance_validation.csv         23 checks, max deviation 2.8e-14 %
  phase0c_reproduction.json             7 cases bit-exact + 5 effects
  c07_thick_result.json                 thickness x asymmetry closure
  coupled_candidates.csv                28 candidates, full ET + mechanical results
  coupled_candidates_firstpass.csv      earlier pass, retained for provenance
  et_ranking.csv / pareto_et.csv        ET-only, mechanically uncontaminated (test-enforced)
  etm_ranking.csv / pareto_etm.csv      ETM
  reversal_analysis.json                G1 test, lever levels, lambda sweep
  robustness_0d.csv / _summary.json     48 runs, 12 corners
  fixed_point_histories/                per-candidate ET convergence traces
  PHASE0D_THICKNESS_TRADEOFF.png
  PHASE0D_ET_VS_ETM_PARETO.png
  PHASE0D_RANK_REVERSAL.png
scripts/phase0d/                        8 modules
tests/phase0d/test_phase0d.py           25 tests
```

Reproduce:
```bash
export PATH=/home/beams0/MGHARIB/envs/etm/bin:$PATH
cd /home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT
python -m pytest tests/ -q
python scripts/phase0d/reproduce_0c.py
python scripts/phase0d/run_c07_thick.py
python scripts/phase0d/run_candidates.py
python scripts/phase0d/analyze_reversal.py
python scripts/phase0d/run_robustness_0d.py
python scripts/phase0d/make_figures.py
```
