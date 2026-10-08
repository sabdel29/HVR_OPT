# Phase-0B Material and Parameter Assumptions Ledger

Every numeric input to the M0 model, with its provenance. Generated against
`configs/phase0b/package_stack.yaml`; the YAML is the machine-readable master and this
file is the human-readable audit.

**Status vocabulary**

| Status | Meaning |
|---|---|
| `SOURCE_BACKED` | traceable to a primary source named in `NOVELTY_BOUNDARY_ETM_PHASE0B.md` |
| `DERIVED` | computed from SOURCE_BACKED inputs by a documented formula in code |
| `ASSUMPTION` | chosen for this benchmark; defensible but not sourced |
| `PROVISIONAL` | placeholder that MUST be replaced before publication |
| `OPEN_DECISION` | unresolved; blocks any publication-grade reliability claim |

---

## 1. Geometry

| Parameter | Value | Status | Source / rationale |
|---|---:|---|---|
| Functional die | 22.36 × 22.36 mm | SOURCE_BACKED | 22.36² = 500.0 mm², the June-2026 reference footprint |
| Die thickness | 300 µm | ASSUMPTION | spec: "UNSPECIFIED default" |
| Power substrate | 30 × 30 mm | ASSUMPTION | spec-recommended reduced test vehicle |
| h_sub | 200 / 500 µm | ASSUMPTION | required Phase-0B sweep; June nominal TSV height 300 µm is SOURCE_BACKED |
| TSV diameter | 30 µm | SOURCE_BACKED | June-2026 Table III |
| TSV pitch | 60 µm | SOURCE_BACKED | June-2026 Table III |
| Interface layer | 10 µm | ASSUMPTION | spec: ~10 µm vertical scale at 20 µm pitch |
| TIM | 50 µm | ASSUMPTION | spec: "UNSPECIFIED default" |
| **HVR tile thickness** | **150 µm** | **PROVISIONAL** | **Not given anywhere in the spec.** Held constant while h_sub varies so the thickness sweep is not confounded by tile volume. Must be replaced by the HVR compiler stack height. |

## 2. Loads

| Parameter | Value | Status | Notes |
|---|---:|---|---|
| Die power | 240 W | ASSUMPTION | Phase-0B load parity (1 V / 240 A) |
| Total HVR heat | 42 W | PROVISIONAL | **Controlled mechanical experiment, NOT the HVR compiler output.** Held constant across geometry cases so an N_VR effect cannot be caused by changing total heat. |
| HVR heat sweep | 31.5 / 42 / 52.5 W | PROVISIONAL | 0.75× / 1× / 1.25× (cases C19 / nominal / C20) |
| Total HVR footprint | 96 mm² | ASSUMPTION | normalized footprint rule; C11/C12 deliberately violate it (72 / 120 mm²) |

## 3. Materials

### Well-founded

| Material | Property | Value | Status |
|---|---|---:|---|
| Silicon | C11 / C12 / C44 | 166 / 64 / 79.6 GPa | SOURCE_BACKED (cubic single crystal) |
| Silicon | CTE | 2.6 ppm/K @ 300 K | SOURCE_BACKED |
| Silicon | k | 130 W/mK | SOURCE_BACKED (spec range 130–150; lower bound taken) |
| Copper | E / ν | 110 GPa / 0.34 | SOURCE_BACKED |
| Copper | CTE | 16.66 ppm/K | SOURCE_BACKED |
| Copper | k | 400 W/mK | SOURCE_BACKED |

Silicon is modelled with its **cubic elastic tensor**, per spec, not as an isotropic metal.

### Derived

| Material | Basis | Result |
|---|---|---|
| `tsv_homog` | Cu area fraction f = πd²/(4p²) = **0.19635** from the SOURCE_BACKED 30 µm / 60 µm geometry. Stiffness and CTE by Voigt / stiffness-weighted rule of mixtures; k_z by Voigt (exact for parallel conduction); k_xy by Maxwell-Garnett for cylinders. | E = 126.1 GPa, ν = 0.312, CTE = 5.01 ppm/K, k_xy = 158.9, k_z = 183.0 W/mK |

The **formula** is the record, implemented in `etm.config.derive_tsv_homog()` and
bounded-checked by `test_tsv_homogenisation_bounds`. The numbers are a consequence.

### High-risk provisional — these dominate the uncertainty

| Material | Property | Value | Status | Risk |
|---|---|---:|---|---|
| Underfill | E | 8 GPa | PROVISIONAL | spec flags as **UNSPECIFIED and HIGH-RISK** |
| Underfill | ν | 0.32 | PROVISIONAL | |
| Underfill | CTE | 30 ppm/K | PROVISIONAL | drives interface shear/peel directly |
| Underfill | k | 0.7 W/mK | PROVISIONAL | |
| HVR tile (effective) | E | 120 GPa | PROVISIONAL | spec: UNSPECIFIED surrogate; sweep 80–160 GPa |
| HVR tile (effective) | CTE | 6 ppm/K | PROVISIONAL | spec: sweep 4–10 ppm/K |
| HVR tile (effective) | k | 60 W/mK | PROVISIONAL | |
| TIM | E / ν | 0.2 GPa / 0.45 | PROVISIONAL | mid-range of the spec's 0.05–0.5 GPa |
| TIM | **CTE** | 200 ppm/K | **OPEN_DECISION** | spec marks TIM CTE UNSPECIFIED. Compliance should make it a weak stress driver — verified by sensitivity, not assumed. |
| TIM | k | 3 W/mK | PROVISIONAL | spec says "from actual TIM" |

**Per the spec's INCONCLUSIVE rule: any design reversal that disappears under a modest
underfill or HVR-tile property perturbation must be reported as INCONCLUSIVE, not GO.**

### Not modelled at this rung

| Item | Why | Consequence |
|---|---|---|
| SiO₂ TSV liner | absorbed into the homogenized `tsv_homog` block | local liner stress unavailable; needs the M1 explicit submodel |
| Discrete BGA balls | spec: "do not initially resolve thousands of balls globally" | BC-B uses a distributed foundation instead |
| Explicit GaN / inductor / capacitor regions inside the tile | M0 uses the homogenized tile | M1 explicit-component tile deferred |
| Plasticity, creep, fatigue, delamination | M0 is linear thermoelastic by definition | no lifetime claim is possible from this rung |

## 4. Boundary conditions

| Item | Value | Status | Notes |
|---|---:|---|---|
| Coolant / ambient | 25 °C | ASSUMPTION | Phase-0B reference |
| **h_top** | **17 522 W/m²K** | **DERIVED** | **Calibrated, not chosen.** Secant-solved so the reference architecture (C05) reaches the June-2026 cooled baseline of 84 °C; residual −0.49 K; then FROZEN for the whole DOE. See `results/phase0b/cooling_calibration.json`. |
| h_bottom | 10 W/m²K | ASSUMPTION | natural convection under the carrier (same value STAMP-2.5D uses beneath its substrate) |
| Sides | adiabatic | ASSUMPTION | |
| T_ref (stress-free) | 25 °C | ASSUMPTION | **M0 operational-only.** Not an assembly signoff temperature. |
| T_cure / attach | — | **OPEN_DECISION** | Required for the M1 rung. Spec: "Do not invent a universal cure temperature." |
| BC-A | 3-2-1 RBM suppression | ASSUMPTION | primary global-warpage model; 6 DOF removed |
| BC-B | elastic foundation kz = 1000, kxy = 100 N/mm³ | PROVISIONAL | spec requires calibration from a BGA unit cell or board data — **not yet done** |

### Note on the cooling calibration target

The Phase-0B load (282 W total over 500 mm²) is ≈4.3× below June's 1 kW case. Calibrating
to June's *hardware* (its h) would leave this vehicle near 39 °C and would test mechanics at
an unrepresentatively small ΔT — biasing the experiment toward a false NO-GO. The
calibration therefore targets a representative *operating temperature* (84 °C), which is the
quantity the mechanical response actually depends on. This is recorded as a deliberate
methodological choice, not an oversight.

## 5. What would most change the results

Ranked by expected leverage on the Phase-0B verdict:

1. **HVR tile effective E and CTE** — the tile is the architecture-dependent inclusion; its stiffness/CTE contrast against silicon is the primary mechanism by which placement can matter at all.
2. **Underfill E and CTE** — sits directly between die and substrate and sets interface shear/peel.
3. **Mechanical BC family** — BC-A vs BC-B changes whether the package is free to bow.
4. **h_top** — sets the absolute ΔT and therefore scales all thermal strain roughly linearly.
5. **HVR tile thickness** — currently PROVISIONAL at 150 µm and directly sets the inclusion volume.
