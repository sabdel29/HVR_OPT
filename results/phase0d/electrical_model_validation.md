# Phase-0D Electrical Model Upgrade — Specification and Validation

Closes the three electrical gaps that Phase 0C left open, the first of which
(`h_sub` having no path into the electrical objective) was the critical path.

**Provenance tags:** `SOURCE_BACKED` · `MODEL_DERIVED` · `ASSUMPTION` · `OPEN`

---

## 0. Where the code lives, and why not upstream

`Scalable_Integrated_VR/` is a **separate git repository** holding a large body of untracked
work — the Phase-0A audit found one commit (`Starting_point`) with both engines, all drivers
and all results untracked. Editing it in place would put that at risk. Phase 0D therefore:

- **reuses** the upstream converter loss formula `HVR_FULL_OPT_EPC_V2.compute_total_loss`
  and the upstream architecture/device optimizer `run_hvr_optimization`, both unmodified;
- **re-implements** the lateral PDN network in `scripts/phase0d/electrical.py`, and proves it
  numerically identical to `DVPDRoutingModel.compute_ppdn_loss` by unit test.

### Upstream patch that should eventually be merged

```python
# Framework_w_HVR_OPT_sizing_v2.py :: DVPDRoutingModel.compute_ppdn_loss
- r_bump_ohm: float = 0.08e-3,
- r_tsv_ohm:  float = 0.04e-3,
+ tsv_field: TSVField,          # geometry: d, pitch, per-via current limit
+ h_sub_m: float,               # substrate thickness -> TSV length
+ T_c: float = 25.0,            # temperature for rho_Cu(T)
...
- r_vertical = 2.0 * r_bump_ohm + r_tsv_ohm
+ # the TSV field is a SERIES element per VR carrying that VR's full current, not a
+ # per-branch term; compute it outside the branch network (see vertical_tsv_loss)
+ r_vertical = 2.0 * r_bump_ohm
...
- rho_dc_ohm_per_mm = self.die.rho_mohm_per_mm * 1e-3
+ rho_dc_ohm_per_mm = rdl_rho_per_mm(T_c) * 1e-3      # geometry-derived, not 50 mOhm/mm
```

---

## 1. Geometry-derived TSV resistance

```
R_single(h, d, T) = rho_Cu(T) * h / A ,      A = pi d^2 / 4
R_field(h, d, n, T) = R_single / n_parallel
n_parallel = min( ceil(I / I_via_max) , n_available(footprint, pitch) )
```

| Parameter | Value | Status |
|---|---:|---|
| Cu resistivity at 20 °C | 17 nΩ·m | **SOURCE_BACKED** — June-2026 Table III |
| TSV diameter | 30 µm | **SOURCE_BACKED** — June-2026 Table III |
| TSV pitch | 60 µm | **SOURCE_BACKED** — June-2026 Table III |
| Cu temperature coefficient α_Cu | 3.93e-3 /K | **ASSUMPTION** — standard bulk Cu; same value as `configs/phase0b` |
| per-via current limit | 33 mA | **OPEN** — see §1.2 |

### 1.1 Baseline validation

| | model | June-2026 Table III | error |
|---|---:|---:|---:|
| R of one 300 µm TSV (Cu, d = 30 µm, 20 °C) | **7.215 mΩ** | **7.1 mΩ** | **+1.62 %** |

The residual is consistent with June quoting ρ_Cu rounded to 17 nΩ·m; ρ = 16.73 nΩ·m
reproduces 7.10 mΩ exactly. Within the tolerance any of these models carries.

Full check table: `tsv_resistance_validation.csv` — 23 checks, maximum deviation from the
closed form **2.8e-14 %** (machine precision) for every scaling law:

| law | verified |
|---|---|
| R ∝ h | R(600 µm)/R(300 µm) = 2.000000 |
| R ∝ 1/d² | R(60 µm)/R(30 µm) = 0.250000 |
| R ∝ 1/n | R_field(n=4)/R_field(n=1) = 0.250000 |
| R(T) rising | ρ(125 °C)/ρ(20 °C) = 1.41265 = 1 + α·105 |
| positivity | R > 0 and finite for h ∈ [50 µm, 1 mm]; h ≤ 0 raises |

### 1.2 OPEN — per-via current limit

Not stated in any source available here. June-2026 Table III reports 30 202 TSVs on PL1 for
a 1 kA load, which implies **≈33 mA/via if PL1 carries output current**, or **≈4.8 mA/via if
it carries input-side RMS current** (I_in,rms = I_out·√(V_out/V_in) ≈ 144 A). Both are swept
in the robustness study. The choice changes `n_parallel` and hence R_field linearly, but
Phase 0D finds the TSV term to be a negligible fraction of total loss either way (§4).

### 1.3 Which current the TSV field carries — a consequential modelling finding

In the **validated Phase-0B/0C stack** the HVR tile is embedded at the **top** of the power
substrate (`embed_from: top`) and the TSV field spans from the board side up to the tile
underside. The field therefore carries **converter INPUT current at 48 V**, not the 1 V
output current:

```
I_in = I_out * (V_out / V_in) / eta  =  60 A * (1/48) / 0.85  =  1.47 A per VR   (41x smaller)
```

Consequence, at the sizes used here:

| path | n_via | R_field (200 µm) | R_field (500 µm) | P_TSV (200 → 500 µm) |
|---|---:|---:|---:|---:|
| **input (validated stack)** | 45 | 107 µΩ | 267 µΩ | **0.23 → 0.58 mW** |
| output (June-like variant) | 1 819 | 2.6 µΩ | 6.6 µΩ | 9.5 → 23.8 mW |

Both are small, because sizing vias by current density makes `P = I²·ρh/(A·n)` scale as
`I·ρ·h·I_via_max/A` — linear, not quadratic, in current. **This is reported as a finding, not
hidden:** the direct resistive cost of substrate thickness is negligible in this vehicle.

---

## 2. Temperature dependence

| Quantity | Model | Coefficient | Status |
|---|---|---:|---|
| Cu resistivity (TSV, RDL, inductor DCR) | ρ(T) = ρ₂₀·[1 + α_Cu(T−20)] | 3.93e-3 /K | **ASSUMPTION** (standard bulk Cu) |
| GaN R_DS(on) | R(T) = R₂₅·[1 + α_GaN(T−25)] | 7.5e-3 /K | **ASSUMPTION** — see below |
| Inductor DCR | copper winding → α_Cu | 3.93e-3 /K | **MODEL_DERIVED** |
| Capacitor ESR | not temperature-dependent | — | **OPEN** — direction is dielectric-dependent and unsupported here |
| Gate charge Q_G, Q_GD, C_OSS, C_G | not temperature-dependent | — | **OPEN** — weak for GaN and no data available |

**The EPC product table in this repository carries no temperature data.** Its columns are
PartNumber, VDSmax, VGSmax, MaxRDS(on)@5VGS, QG, QGS, QGD, QOSS, ID, PulsedID, Package,
Stock, Price. α_GaN therefore cannot be sourced from repository data. 7.5e-3 /K gives ≈1.75×
at 125 °C, consistent with the normalised R_DS(on) curves EPC publishes for eGaN parts. It is
**swept (0.005 / 0.0075 / 0.010 /K) in the Phase-0D robustness study.**

Only conduction-path resistances are made temperature-dependent. Switching loss terms are
left alone because nothing in the repository supports a temperature law for them — inventing
one would be unsupported. This is a deliberate partial-coupling choice, stated as such.

**Magnitude:** for the reference design at ~73 °C, converter loss rises from 16.99 W (25 °C)
to 20.58 W — a **+21 %** temperature penalty. Temperature coupling is not a second-order
detail in this system.

---

## 3. Lateral RDL resistance — a second uncalibrated default found and fixed

The upstream `DieConfig.rho_mohm_per_mm = 50` was flagged by the Phase-0A audit as
"not derived from trace width/thickness/sheet resistance". Phase 0D is the first phase to
exercise the electrical objective at load, and it exposed the value as **unphysical**:

| | upstream default | geometry-derived |
|---|---:|---:|
| lateral R per mm | 50 mΩ/mm | **0.155 mΩ/mm** (25 °C) |
| IR drop, 60 A over 7 mm, 1 V rail | 21 000 mV (2100 %) | 64 mV (6.4 %) |

Replaced by `R_per_mm = ρ_Cu(T) / (t_Cu · W_eff)` with t_Cu = 5 µm (**ASSUMPTION**,
Phase-0A recorded "RDL Cu thickness 5 µm, UNSPECIFIED default") and W_eff = 22.36 mm
(**MODEL_DERIVED** — the die width; power is delivered on a plane, not a trace).
June-2026 reports steady-state IR drop < 2.7 % at 1 kA, so the corrected value is the right
order and the default is not.

**How it was found:** candidate D02 (asymmetric placement) produced P_PDN = 2781 W against a
240 W load and an ET fixed point at 569 °C. That is a model-validity failure, not a design
result. A validity guard now rejects any candidate whose P_PDN exceeds 50 % of the die load.

The POL segmentation was also refined from 4 to **100 segments**, matching June-2026's load
segmentation; a 4-point grid concentrates the load artificially and exaggerates routing loss
for offset placements.

---

## 4. HVR footprint geometry

The upstream optimizer returns `total_area_mm2` (scalar) plus `area_budget_mm2` and
`area_feasible`. Its internal geometry is limited to `EPCDevice.footprint_mm2` (parsed from
the Package column, area only — no width/length) and `Inductor.footprint_mm2` + `height_um`.
`_compute_area` reduces these to `max(N·fp_hs, K·fp_ls, K·fp_ind, (N−1)·fp_cap)` — a single
scalar.

**No physically meaningful rectangular footprint can be derived from what the compiler
actually holds**, because no component carries a width and a length separately. Per the
Phase-0D brief's instruction not to invent an aspect ratio, the **square-tile approximation
is retained and made explicit** in `HVRDesign.footprint_xy_mm`:

```
A_x = A_y = sqrt(total_area_mm2)
```

This is consistent with Phase 0C's finding that tile aspect ratio is mechanically **inert**
(−1.76 %, below band), so the approximation does not affect the Phase-0D conclusions. The
closure remains: emitting real A_x × A_y requires per-component width/length in the device
and passive libraries, which is a library task, not a solver task.

**What the compiler does supply, and Phase 0D does use:** the area budget `A_budget = I_out/J`
sets both the footprint and the achievable switch sizing, so footprint and converter loss are
**physically coupled outputs of one design decision** rather than independent knobs:

| J (A/mm²) | A_budget/VR | chosen area | loss @25 °C | architecture |
|---:|---:|---:|---:|---|
| 4.0 | 15.0 mm² | 15.00 mm² | 6.592 W | N=4, K=4, K_A=2 |
| 2.0 | 30.0 mm² | 25.74 mm² | 4.248 W | N=3, K=3, K_A=2 |
| 1.5 | 40.0 mm² | 34.32 mm² | 3.420 W | N=4, K=4, K_A=2 |

This is the June per-layer-area-budget mechanism in action, and it is what makes the
footprint lever a genuine ET-vs-ETM tension: more area buys lower loss but costs warpage.

---

## 5. Electrical–thermal fixed point

```
T -> R_DS(on)(T), DCR(T), rho_Cu(T) -> P_conv, P_PDN -> heat sources -> FEA thermal -> T
```

The **validated Phase-0B/0C FEA thermal model** is used inside the loop (not a compact
surrogate), at the SENS mesh for iteration speed; the final mechanical replay then runs at
the production mesh. Mechanics is deliberately outside the loop: M0 linear thermoelasticity
has no back-action on the electrical or thermal problem.

Convergence: `|ΔT_max| < 0.05 K` **and** `|ΔP_elec|/P_elec < 1e-3`, max 20 iterations.
A candidate that does not converge is **rejected**, never reported at its last iterate.

Typical behaviour (reference design, C05 geometry, h_sub = 200 µm) — 4 iterations:

| iter | T_max (°C) | P_conv (W) | P_lat (W) | P_TSV (W) | P_elec (W) | ΔT (K) |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 70.719 | 16.993 | 6.2101 | 0.000943 | 23.204 | — |
| 1 | 72.627 | 20.457 | 6.8725 | 0.001102 | 27.330 | 1.9088 |
| 2 | 72.694 | 20.577 | 6.8955 | 0.001108 | 27.473 | 0.0663 |
| 3 | 72.696 | 20.581 | 6.8963 | 0.001108 | 27.478 | 0.0023 |

Energy balance closes to **±0.0000 %** at every iteration.

*(Note: this history predates the RDL correction of §3 and is shown to illustrate convergence
behaviour only; the production candidate histories are in `fixed_point_histories/`.)*

---

## 6. Validation summary

| Requirement | Status |
|---|---|
| geometry-derived TSV resistance | **DONE** — R(h,d,n,T), 23 checks, machine-precision scaling |
| unit-safe | **DONE** — SI internally; mΩ/mm and µΩ only at reporting boundaries |
| temperature-aware | **DONE** — ρ_Cu(T), R_DS(on)(T), DCR(T); switching terms left alone and tagged OPEN |
| validated against June baseline | **DONE** — 7.215 vs 7.1 mΩ, +1.62 % |
| no hidden hard-coded h_sub dependence | **DONE** — h_sub enters only as TSV length; unit-tested that 200 vs 500 µm changes R_TSV, P_TSV and P_elec |
| lateral network fidelity | **DONE** — reimplementation matches upstream to 0.00e+00 relative error on three configurations |
| HVR footprint A_x × A_y | **PARTIAL** — square-tile approximation retained and documented; the library lacks per-component width/length |
