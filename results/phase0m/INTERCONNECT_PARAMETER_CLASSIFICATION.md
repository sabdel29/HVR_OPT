# PHASE 0M PART 1 --- INTERCONNECT PARAMETER CLASSIFICATION

**Rule enforced by this phase: no resistance may remain a primitive parameter if geometry can
derive it.** Every interconnect quantity below belongs to exactly one of four classes, and
`scripts/phase0m/interconnect.py::classify()` raises on anything not in this table.

## MATERIAL CONSTANT --- a property of the material, never a design variable

| parameter | unit | value | status / source |
|---|---|---|---|
| `rho_Cu_20C` | Ohm.m | 1.7e-08 | SOURCE_BACKED June-2026 |
| `alpha_Cu` | 1/K | 0.00393 | ASSUMPTION bulk Cu TCR |
| `rho_solder_20C` | Ohm.m | 1.3e-07 | SOURCE_BACKED June-2026 |
| `k_Cu` | W/m.K | 385.0 | handbook |
| `k_Si` | W/m.K | 130.0 | handbook |
| `k_SiO2` | W/m.K | 1.4 | handbook |
| `E_Cu, nu_Cu, CTE_Cu` | MPa,-,1/K | -- | handbook |

## PROCESS / TECHNOLOGY LIMIT --- a bound the design must respect, not a variable to optimize

| parameter | unit | value | status / source |
|---|---|---|---|
| `tsv_liner_thickness` | m | 5e-07 | ASSUMPTION typical SiO2 liner |
| `tsv_aspect_ratio_max` | - | 10.0 | DERIVED_FROM_SOURCE June-2026 Table III demonstrates d=30 um at h=300 um |
| `tsv_spacing_min` | m | 3e-05 | DERIVED_FROM_SOURCE June-2026 p=60 um at d=30 um implies s_min = p - d = 30 um |
| `tsv_koz_ratio` | - | 1.0 | ASSUMPTION keep-out radius expressed as a multiple of r; swept, never fixed |
| `J_max_Cu` | A/m^2 | -- | DERIVED_FROM_SOURCE envelope 1.0e8 (June-2026) to 4.0e8 (ECTC-2024); the EM-lifetime limit itself remains OPEN |
| `J_max_solder` | A/m^2 | -- | DERIVED_FROM_SOURCE envelope 1.74e7 to 3.97e7 |
| `rdl_line_space_min` | m | 2e-06 | SOURCE_BACKED ECTC-2024 Table I S=2 um |
| `bump_pitch_min` | m | -- | tier-specific, see design space |

## DESIGN VARIABLE --- what the eventual optimizer may move

| parameter | unit | nominal | status / source |
|---|---|---|---|
| `tsv_radius` | m | 1.5e-05 | June-2024 nominal d=30 um |
| `tsv_pitch` | m | 6e-05 | June-2026 nominal; constrained p >= 2r + s_min |
| `tsv_height` | m | 0.0003 | = substrate thickness variable |
| `tsv_n_allocated` | - | -- | set by allocation POLICY |
| `tsv_field_footprint` | m^2 | -- | die shadow or tile footprint |
| `tsv_pg_ratio` | - | 0.5 | supply/ground split |
| `rdl_t_cu` | m | 1e-05 | ECTC-2024 REFERENCE, not a fixed constant |
| `rdl_width` | m | 1e-05 | ECTC-2024 REFERENCE |
| `rdl_space` | m | 2e-06 | ECTC-2024 REFERENCE, >= process min |
| `rdl_n_vdd, rdl_n_gnd` | - | 2 | ECTC-2024 REFERENCE |
| `bump_diameter` | m | -- | tier-specific |
| `bump_height` | m | -- | tier-specific |
| `bump_pitch` | m | -- | tier-specific |
| `pad_diameter` | m | -- | landing pad, promoted in Part 8 |
| `trace_width_at_pad` | m | -- | promoted in Part 8 |
| `source_footprint` | m^2 | -- | VR tile footprint |
| `load_footprint` | m^2 | -- | POL cell footprint |

## DERIVED --- computed, never entered

| parameter | unit | value | derivation |
|---|---|---|---|
| `A_conductor` | m^2 | -- | pi (r - t_liner)^2 |
| `R_single` | Ohm | -- | rho(T) h / A_conductor |
| `I_max_per_via` | A | -- | J_max A_conductor |
| `n_required` | - | -- | ceil(I / I_max_per_via) |
| `n_available` | - | -- | footprint pg_ratio / pitch^2 |
| `R_field` | Ohm | -- | R_single / n_allocated |
| `P_joule` | W | -- | I^2 R_loop |
| `phi_Cu` | - | -- | n_alloc A_conductor / footprint |
| `k_z_eff, k_xy_eff` | W/m.K | -- | effective-medium, Part 20 |
| `E_eff, CTE_eff` | MPa,1/K | -- | Voigt/Reuss + Levin, Part 20 |
| `K_crowd` | - | -- | R_3D_transition / R_bulk, Part 8 |
| `sheet_conductance` | S | -- | N t occupancy / rho(T) |

## What was already geometry-derived, and what was not

Phases 0D-R and 0E were better than the brief assumes. `r_single()` has computed
`rho(T) h / A` from geometry since Phase 0D-R, and `RDLStack.occupancy` has been derived
from the line/space rule rather than assumed since Phase 0E. Three things were **not**
geometry-derived and are corrected here:

1. **`i_max_a` is a primitive per-via current in amperes**
   (`configs/phase0dr/power_path_graphs.yaml`: BGA 0.5 A, C4 0.2 A, TSV 0.033 A, microbump
   0.02 A). It is the ONLY remaining primitive that sets field resistance, because under
   minimum-capability allocation `R_field = rho h J_max / I` depends on `J_max` and on
   nothing else geometric (Part 3). It is replaced by `J_max * A_conductor`, with `J_max` a
   PROCESS limit and `A_conductor` DERIVED. **Defect #47.**

2. **The current-crowding factor was one global constant**, `CROWDING_DEFAULT = 1.326`,
   applied identically to BGA, C4, TSV and microbump
   (`scripts/phase0e/architecture0e.py`). It was measured in HFSS on ONE P/G TSV loop. Part 8
   replaces it with a geometry-dependent `K_crowd`. **Defect #48.**

3. **The TSV liner was absent entirely.** `tier_area_m2()` uses the full drilled diameter as
   conductor, which overstates the conducting area by
   `[r/(r-t_ox)]^2 = 7.0 %` at r = 15 um and t_ox = 0.5 um. It does not change `R_field`
   under policy A (Part 3 shows the cross-section cancels) but it does change the per-via
   current, the copper fraction and therefore every thermal and mechanical effective
   property. **Defect #49.**

## Coupled, not independent

`r` and `p` are NOT independent. The binding rule is
`p >= max(2r + s_min, 2r(1 + k_KOZ))`, and `h/2r <= AR_max`. Both are enforced in
`TSVGeometry` and both are checked before any electrical number is returned.
