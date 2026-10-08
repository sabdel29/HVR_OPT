#!/usr/bin/env python3
"""Phase-0M Parts 1 and 5 artifacts: the parameter classification and the framework record."""
from __future__ import annotations
import csv, json, sys, time
from pathlib import Path
import yaml

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0m"))
from interconnect import PARAMS, CLASSES, TSVGeometry, rho_cu             # noqa: E402
import tsv_framework as TF                                                # noqa: E402

OUT = R / "results" / "phase0m"
CFG = R / "configs" / "phase0m"
OUT.mkdir(parents=True, exist_ok=True)
CFG.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- Part 1 artifacts
rows = [{"parameter": k, "class": c, "unit": u,
         "value": ("" if v is None else v), "status_and_source": src}
        for k, c, u, v, src in PARAMS]
with open(OUT / "interconnect_parameter_classification.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

by = {c: [r for r in rows if r["class"] == c] for c in CLASSES}
tbl = {c: "\n".join(f"| `{r['parameter']}` | {r['unit']} | "
                    f"{r['value'] if r['value'] != '' else '--'} | {r['status_and_source']} |"
                    for r in by[c]) for c in CLASSES}

PART1 = f"""# PHASE 0M PART 1 --- INTERCONNECT PARAMETER CLASSIFICATION

**Rule enforced by this phase: no resistance may remain a primitive parameter if geometry can
derive it.** Every interconnect quantity below belongs to exactly one of four classes, and
`scripts/phase0m/interconnect.py::classify()` raises on anything not in this table.

## MATERIAL CONSTANT --- a property of the material, never a design variable

| parameter | unit | value | status / source |
|---|---|---|---|
{tbl['MATERIAL']}

## PROCESS / TECHNOLOGY LIMIT --- a bound the design must respect, not a variable to optimize

| parameter | unit | value | status / source |
|---|---|---|---|
{tbl['PROCESS']}

## DESIGN VARIABLE --- what the eventual optimizer may move

| parameter | unit | nominal | status / source |
|---|---|---|---|
{tbl['DESIGN']}

## DERIVED --- computed, never entered

| parameter | unit | value | derivation |
|---|---|---|---|
{tbl['DERIVED']}

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
"""
(OUT / "INTERCONNECT_PARAMETER_CLASSIFICATION.md").write_text(PART1)

# ---------------------------------------------------------------- design-space YAML
DS = {
    "meta": {
        "phase": "0M",
        "purpose": "Geometry-resolved interconnect design space. Ranges are BOUNDS for "
                   "exploration, not a DOE and not an optimizer input set.",
        "rule": "No resistance appears here. Resistance is DERIVED from geometry by "
                "scripts/phase0m/interconnect.py.",
        "status_vocab": ["SOURCE_BACKED", "DERIVED_FROM_SOURCE", "ASSUMPTION", "OPEN"],
    },
    "material": {
        "rho_cu_20c_ohm_m": {"value": 17.0e-9, "status": "SOURCE_BACKED",
                             "src": "June-2026"},
        "alpha_cu_per_k": {"value": 3.93e-3, "status": "ASSUMPTION", "src": "bulk Cu TCR"},
        "rho_solder_20c_ohm_m": {"value": 130.0e-9, "status": "SOURCE_BACKED",
                                 "src": "June-2026"},
        "k_cu_w_mk": 385.0, "k_si_w_mk": 130.0, "k_sio2_w_mk": 1.4,
        "k_solder_w_mk": 57.0, "k_underfill_w_mk": 0.6, "k_organic_w_mk": 0.35,
    },
    "process_limits": {
        "tsv": {"aspect_ratio_max": {"value": 10.0, "status": "DERIVED_FROM_SOURCE",
                                     "src": "June-2026 Table III d=30 um at h=300 um"},
                "spacing_min_m": {"value": 30.0e-6, "status": "DERIVED_FROM_SOURCE",
                                  "src": "p=60 um at d=30 um implies s_min=30 um"},
                "liner_thickness_m": {"value": 0.5e-6, "status": "ASSUMPTION"},
                "koz_ratio": {"sweep": [0.0, 0.25, 0.5, 1.0, 1.5], "status": "ASSUMPTION",
                              "note": "keep-out radius as a multiple of r; never fixed"}},
        "rdl": {"space_min_m": {"value": 2.0e-6, "status": "SOURCE_BACKED",
                                "src": "ECTC-2024 Table I S = 2 um"},
                "width_min_m": {"value": 2.0e-6, "status": "DERIVED_FROM_SOURCE",
                                "src": "ISCAS-2024 quotes a 2 um RDL trace dimension"}},
        "current_density_a_per_m2": {
            "cu": {"lo": 1.0e8, "hi": 4.0e8, "status": "DERIVED_FROM_SOURCE",
                   "src": "June-2026 vs ECTC-2024; a 4x envelope, not an error"},
            "solder": {"lo": 1.74e7, "hi": 3.97e7, "status": "DERIVED_FROM_SOURCE"},
            "em_lifetime_limit": {"status": "OPEN",
                                  "why": "no primary EM study with its T, t_life and geometry "
                                         "was retrievable; feasibility is reported as a MAP "
                                         "over J, never as a verdict"}},
    },
    "design_variables": {
        "tsv": {"radius_m": {"lo": 2.5e-6, "hi": 50.0e-6, "nominal": 15.0e-6},
                "height_m": {"lo": 50.0e-6, "hi": 2000.0e-6, "nominal": 300.0e-6,
                             "note": "= substrate thickness minus any embedded cell"},
                "pitch_m": {"rule": "max(2r + s_min, 2r(1+koz_ratio))", "nominal": 60.0e-6},
                "n_allocated": {"rule": "set by allocation POLICY, see policies"},
                "pg_ratio": {"lo": 0.3, "hi": 0.7, "nominal": 0.5}},
        "rdl": {"t_cu_m": {"lo": 2.0e-6, "hi": 40.0e-6, "nominal": 10.0e-6,
                           "note": "ECTC-2024 value is a REFERENCE TECHNOLOGY, not a bound"},
                "width_m": {"lo": 2.0e-6, "hi": 100.0e-6, "nominal": 10.0e-6},
                "space_m": {"lo": 2.0e-6, "hi": 20.0e-6, "nominal": 2.0e-6},
                "n_vdd": {"lo": 1, "hi": 8, "nominal": 2},
                "n_gnd": {"lo": 1, "hi": 8, "nominal": 2},
                "occupancy": {"rule": "w/(w+s), DERIVED -- never a free parameter"}},
        "bump": {
            "bga": {"diameter_m": {"lo": 200e-6, "hi": 600e-6, "nominal": 400e-6},
                    "height_m": {"lo": 150e-6, "hi": 450e-6, "nominal": 300e-6},
                    "pitch_m": {"lo": 400e-6, "hi": 1200e-6, "nominal": 800e-6}},
            "c4": {"diameter_m": {"lo": 50e-6, "hi": 150e-6, "nominal": 100e-6},
                   "height_m": {"lo": 40e-6, "hi": 100e-6, "nominal": 70e-6},
                   "pitch_m": {"lo": 100e-6, "hi": 250e-6, "nominal": 150e-6}},
            "microbump": {"diameter_m": {"lo": 5e-6, "hi": 40e-6, "nominal": 10e-6},
                          "height_m": {"lo": 5e-6, "hi": 30e-6, "nominal": 10e-6},
                          "pitch_m": {"lo": 10e-6, "hi": 80e-6, "nominal": 20e-6}},
            "pad": {"pad_over_bump_ratio": {"lo": 1.0, "hi": 2.0, "nominal": 1.2},
                    "ubm_thickness_m": {"lo": 1e-6, "hi": 10e-6, "nominal": 3e-6}},
        },
    },
    "allocation_policies": {
        "A_min_capability": "n = ceil(I / (J_max A_c)). SOURCE_BACKED (June-2026 Sec. III-E). "
                            "R_field = rho h J_max / I -- the conductor cross-section cancels.",
        "B_fixed_count": "n fixed. R_field ~ 1/A_c. The only policy where radius is a lever.",
        "C_fixed_pitch": "n = A_f f / p^2 with p at the design rule.",
        "D_area_optimal": "n = n_available.",
        "E_fixed_cu_fraction": "n A_c = phi A_f. R_field = rho h/(phi A_f) -- cancels again.",
    },
    "derived_quantities": [
        "A_conductor = pi (r - t_liner)^2", "R_single = rho(T) h / A_conductor",
        "I_max_per_via = J_max A_conductor", "n_required = ceil(I / I_max_per_via)",
        "n_available = A_footprint pg_ratio / pitch^2", "R_field = R_single / n_allocated",
        "R_loop = R_field_supply + R_field_return", "P = I^2 R_loop",
        "phi_Cu = n_allocated A_conductor / A_footprint",
        "k_z, k_xy = effective-medium over (Cu, liner, Si)",
        "E_eff, CTE_eff = Voigt/Reuss + stiffness-weighted CTE",
        "K_crowd = R_3D_transition / R_bulk  (Part 8; NEVER a constant)",
        "sheet_conductance = N t occupancy / rho(T)",
    ],
}
(CFG / "interconnect_design_space.yaml").write_text(
    "# Phase-0M geometry-resolved interconnect design space.\n"
    "# Generated by scripts/phase0m/write_part1_5.py -- edit the generator, not this file.\n"
    + yaml.safe_dump(DS, sort_keys=False, default_flow_style=False, width=96))

# ---------------------------------------------------------------- Part 5 artifact
rec = TF.interface_record()
probe = []
if rec["available"]:
    for f in (1e0, 1e5, 1e6, 1e7, 1e8, 1e9):
        probe.append(TF.skin_resistance(15e-6, 300e-6, f))
    ind = [TF.loop_inductance(15e-6, 300e-6, p, n_parallel=8, third_via_pitch_m=2 * p)
           for p in (30e-6, 60e-6, 120e-6)]
    kt = [TF.k_tensor(r, 0.5e-6, max(2 * r + 30e-6, 4 * r), 22.36e-3)
          for r in (5e-6, 15e-6, 30e-6)]
else:
    ind = kt = []

with open(OUT / "tsv_framework_probe.csv", "w", newline="") as fh:
    if probe:
        w = csv.DictWriter(fh, fieldnames=list(probe[0])); w.writeheader(); w.writerows(probe)

PART5 = f"""# PHASE 0M PART 5 --- THE PRE-EXISTING TSV ELECTROTHERMAL FRAMEWORK

## Found. Not reimplemented.

| field | value |
|---|---|
| path | `{rec['path']}` |
| sha256 | `{(rec['sha256'] or '')[:32]}...` |
| size | {rec['bytes']} bytes |
| mtime | {time.strftime('%Y-%m-%d', time.localtime(rec['mtime'])) if rec['mtime'] else '--'} |
| version string | **none in the file** --- the sha256 above is the version handle |
| entry point | module-level functions; `main()` is `__name__`-guarded, so import is safe |
| SPICE backend | `/local/synopsys/hspice/W-2024.09-SP2-2/hspice/bin/hspice` |
| HFSS reference | `{rec['hfss_reference_dir']}` |
| HFSS error stats | `{rec['hfss_error_stats']}` |
| ML surrogate | `/home/beams0/MGHARIB/Model/tsv_surrogate_v3.pt` --- **NOT USED**, see below |

## What it contains

* **DC + skin resistance** --- `Z_in(r, f)`, the Bessel-function internal impedance
  `Z = (k/2 pi r sigma) J0(kr)/J1(kr)`, `k = sqrt(2 j pi f mu sigma)`.
* **Self and mutual partial inductance** --- via-to-via and through the depleted substrate.
* **Capacitance / conductance** --- MOS via capacitance with a depletion-thickness solve.
* **Multi-conductor S-parameters** --- an HSPICE netlist per frequency, N ports.
* **Anisotropic thermal homogenization** --- `thermal_conductivity()` returns
  `(k_x, k_y, k_z, rho c_p)` for a TSV ARRAY, which is exactly the quantity Parts 20 and 21
  need and which this project has never had.

## Interface used by Phase 0M

`scripts/phase0m/tsv_framework.py` wraps it. The framework is written for signal integrity
(per-unit-length outputs, micrometre locations, `(N, M)` array counts); the wrapper converts
to the power-delivery quantities and, importantly, **cross-checks rather than trusts**.

## Cross-check against the independent Phase-0M model

| quantity | framework | Phase-0M `interconnect.py` | agreement |
|---|---|---|---|
| `R_dc` of one TSV, r = 15 um, h = 300 um | {probe[0]['R_dc_ohm']*1e3:.4f} mOhm | 7.3175 mOhm | **exact** |
| June-2026 Table III quoted value | -- | 7.1 mOhm | +3.1 % (shape/liner convention) |
| skin ratio at 1 MHz | {probe[2]['skin_ratio']:.4f} | -- | `delta/r` = {probe[2]['delta_over_r']:.2f} |
| skin ratio at 1 GHz | {probe[5]['skin_ratio']:.4f} | -- | `delta/r` = {probe[5]['delta_over_r']:.2f} |
| `k_z`, full 60 um-pitch field | {kt[1]['k_z']:.2f} W/m.K | 178.18 W/m.K | **exact** |
| `k_xy`, same field | {kt[1]['k_x']:.2f} W/m.K | 158.3 W/m.K (Maxwell-Garnett) | **80 % apart** |

The last row is the important one. The two models are not two implementations of one theory:
the framework's transverse model puts the oxide liner **in series** with the copper, so all
transverse heat must cross a 1.4 W/m.K barrier; the Maxwell-Garnett form treats the lined via
as an inclusion that heat can flow **around**. Neither is obviously right, so Part 21 decides
it by explicit-geometry finite elements on a unit cell rather than by preference.

## Loop inductance --- the quantity Part 13 needs

| pitch | `L_loop` per P/G pair | 8 pairs, uncoupled | 8 pairs, coupled (k = {ind[1]['k_coupling']:.2f}) |
|---|---|---|---|
{chr(10).join(f"| {d['pitch_m']*1e6:.0f} um | {d['L_loop_nH']:.4f} nH | {d['L_parallel_uncoupled_nH']:.4f} nH | {d['L_parallel_coupled_nH']:.4f} nH |" for d in ind)}

Mutual coupling matters: eight parallel P/G pairs give 2.9x less inductance reduction than
the uncoupled 8x, so an inductance budget built by dividing by the via count is optimistic by
about a factor of three.

## What is deliberately NOT used

The trained surrogate `tsv_surrogate_v3.pt` is not used. It was trained on a
signal-integrity corpus (S-parameters of multi-conductor TSV bundles at GHz frequencies) and
has no established validity for a DC power via field at 1000 A. Using it here would be
exactly the transfer-without-evidence this project forbids elsewhere.

## Validation status of the framework itself

`{rec['hfss_error_stats']}` records the framework against HFSS over 786 reflection and
insertion-loss samples and ~14 000 coupling samples:

| category | n | mean abs error | p95 | mean rel error |
|---|---|---|---|---|
| insertion loss | 786 | 0.00409 | 0.00743 | **0.42 %** |
| reflection | 786 | 0.0329 | 0.0643 | 73 % (small-magnitude denominators) |
| near-end coupling | 13866 | 0.00318 | 0.00774 | 90 % (ditto) |

The insertion-loss column is the one that bears on a power path, and 0.42 % mean relative
error against HFSS is a strong result. The reflection and coupling relative errors are large
only because the quantities are near zero; their ABSOLUTE errors are 0.003 to 0.03.
"""
(OUT / "TSV_FRAMEWORK_INTERFACE.md").write_text(PART5)
print("wrote Part-1 and Part-5 artifacts")
print(f"  k_xy framework={kt[1]['k_x']:.2f}  k_z framework={kt[1]['k_z']:.2f}")
