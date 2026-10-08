#!/usr/bin/env python3
"""Phase-0M Part 42 (second half) -- Z5, thermal, cooling, partition, physics, levers."""
from __future__ import annotations
import csv, math, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0m"


def rd(n):
    p = OUT / n
    return list(csv.DictReader(p.open())) if p.is_file() else []


def f(x, d=4):
    try:
        return f"{float(x):.{d}f}"
    except (TypeError, ValueError):
        return str(x) if x not in (None, "") else "--"


def g(x, d=4):
    try:
        return f"{float(x):.{d}g}"
    except (TypeError, ValueError):
        return str(x) if x not in (None, "") else "--"


# ============================================================ Z5
def z5() -> None:
    dec = rd("z5_path_decomposition.csv")
    cmp_ = rd("z5_pcb_vs_rdl.csv")
    fam = rd("z5_architecture_comparison.csv")
    b = dec[0]
    stg = rd("z5_stage_losses.csv")
    one = [r for r in fam if r["n_die_edges_fed"] == "1"]
    md = f"""# PHASE 0M PARTS 17-19 --- Z5 RE-AUDIT FROM FIRST PRINCIPLES

Phase 0I reported ~768 W of RDL loss for `ARCH_Z5_2P5D_LATERAL` and read it as pricing 2.5D.
Phase 0I-R narrowed that to the tested LOW-VOLTAGE lateral topology. Phase 0M neither
preserves nor withdraws the number: it traces the code path, states the implied equivalent
loop resistance, checks every parameter against interposer rather than PCB geometry, and
evaluates a FAMILY of lateral architectures.

## 1. The code path, traced end to end

| step | value |
|---|---|
| rail voltage | 1.0 V (the LV rail crosses the interposer laterally) |
| lateral current | {f(b['i_lateral_a'], 1)} A |
| source position | x = {f(b['source_x_mm'], 3)} mm, {f(b['source_to_die_edge_mm'], 3)} mm clear of the die edge |
| destination | 100 POL cells on a {f(22.36, 2)} mm die |
| solve span | {f(b['span_mm'], 3)} mm |
| RDL thickness | {f(b['t_cu_um'], 1)} um |
| line / space | {f(b['width_um'], 1)} / {f(b['space_um'], 1)} um --> occupancy {f(b['occupancy'], 4)} |
| layer count | {b['n_vdd']} VDD + {b['n_gnd']} GND |
| rho at {f(b['T_c'], 0)} C | {g(b['rho_at_T_ohm_m'], 5)} Ohm.m |
| sheet R per net | VDD {f(b['sheet_R_vdd_mohm_sq'], 4)}, GND {f(b['sheet_R_gnd_mohm_sq'], 4)} mOhm/sq |
| **loop sheet R** | **{f(b['sheet_R_loop_mohm_sq'], 4)} mOhm per square** |
| **P = I^2 R** | **{f(b['P_loop_w'], 3)} W** (VDD {f(b['P_vdd_w'], 3)} + GND {f(b['P_gnd_w'], 3)}) |

## 2. The implied equivalent loop resistance

```
R_eq = P / I^2 = {f(b['P_loop_w'], 3)} / 1000^2 = {f(b['R_eq_mohm'], 5)} mOhm
IR drop = {f(b['IR_drop_v'], 4)} V on a 1 V rail
```

Against the stack's own {f(b['sheet_R_loop_mohm_sq'], 4)} mOhm per loop square, that is
**{f(b['loop_squares'], 4)} loop squares**. For a source line {f(b['source_to_die_edge_mm'], 2)} mm
clear of a {f(22.36, 2)} mm-wide die, a 1-D estimate gives
{f(float(b['source_to_die_edge_mm'])/22.36, 3)} squares before any spreading inside the die,
so 0.30 squares is geometrically consistent. **The number is what the geometry gives.**

| variation | P (W) | R_eq (mOhm) | loop squares |
|---|---|---|---|
{chr(10).join(f"| `{r['stack']}` | {f(r['P_loop_w'], 3)} | {f(r['R_eq_mohm'], 5)} | {f(r['loop_squares'], 4)} |" for r in dec)}

Grid-converged: 121 -> 201 moves the answer by 0.15 %. The loop-square count is invariant
across stacks, as it must be --- it is pure geometry --- and varies 0.27 to 0.34 with the gap.

## 3. Part 18 --- did Z5 inherit PCB routing assumptions? NO, AND THE REVERSE

| path | t_Cu | W / S | layers per net | occupancy | **loop R per square** |
|---|---|---|---|---|---|
{chr(10).join(f"| {r['path']} | {f(r['t_cu_um'], 1)} um | {f(r['width_um'], 0)} / {f(r['space_um'], 0)} um | {r['n_per_net']} | {f(r['occupancy'], 3)} | **{f(r['loop_R_mohm_per_sq'], 4)} mOhm/sq** |" for r in cmp_)}

The suspicion in the brief was that a PCB parameter had leaked into the interposer path. The
opposite is the case: **the PCB row is 4.56x MORE conductive per square than the RDL row**,
because 152 um of copper at 50 % occupancy beats 2 x 10 um at 83 %. Had Z5 inherited PCB
routing it would have reported ~169 W, not 768 W. **No defect is logged. The Z5 number is
computed on interposer geometry and it survives.**

The brief's expectation that "a shorter route with more/larger parallel RDL planes should be
recomputed from geometry" is tested and the answer is that the interposer RDL is THINNER than
the board, not thicker. Thin-film redistribution buys density and loses cross-section.

## 4. Part 19 --- the Z5 FAMILY, not one point

Both conversion stages are charged at their real modelled cost from the same upstream loss
model the rest of the project uses. Stage 1 converts 48 V to the lateral rail beside the die;
stage 2 converts the lateral rail to 1 V at the load.

| lateral V | die edges fed | P_lateral | P_stage1 | P_stage2 | **P_total** | eta | status |
|---|---|---|---|---|---|---|---|
{chr(10).join(f"| {f(r['v_lateral'], 1)} | {r['n_die_edges_fed']} | {f(r['P_lateral_w'], 3)} | {g(r['P_stage1_w'], 5)} | {g(r['P_stage2_w'], 5)} | **{f(r['P_total_w'], 2)}** | {f(r['efficiency_pct'], 2)} % | {r['total_is']} |" for r in fam)}

Rows marked LOWER BOUND are ones where the upstream optimizer could not compile a first
stage at that output voltage. **Those stages are not worth zero watts and are not counted as
zero**: the CSV carries two explicitly-labelled sensitivities,
`P_total_stage1_at_97pct_w` and `..._99pct_w`, for a switched-capacitor first stage at 97 %
and 99 % efficiency. Those are ASSUMPTIONS, clearly marked, not results.

### Distribution alone

Feeding the die from more than one edge was solved directly on the same resistive sheet, not
scaled. An earlier version of this analysis scaled the clustered loss as `I^2 R / nc^1.5` on
the argument that the lateral path shortens as `1/sqrt(nc)`; that is wrong twice for a
monolithic die --- a converter cannot sit inside the die, and the source-to-die gap is set by
the VR footprint and does not shrink.

| die edges fed | R_eq (mOhm) | loop squares | P at 1 V, 1000 A |
|---|---|---|---|
{chr(10).join(f"| {r['n_die_edges_fed']} | {f(r['R_eq_mohm'], 5)} | -- | {f(r['P_lateral_w'], 2)} W |" for r in one[:1] + [x for x in fam if x['v_lateral'] == '1.0'][1:])}

## 5. Verdict

* **The ~768 W result SURVIVES** for the topology Phase 0I actually tested: a 1 V rail fed
  laterally from ONE side of the die across a 2-layer, 10 um ECTC-2024 RDL. Equivalent loop
  resistance **{f(b['R_eq_mohm'], 5)} mOhm**, {f(b['loop_squares'], 4)} loop squares, IR drop
  {f(b['IR_drop_v'], 3)} V on a 1 V rail. Grid-converged, geometry-consistent, and not
  inherited from a PCB.
* **2.5D as a CLASS is NOT eliminated.** Feeding the same 1 V rail from four die edges cuts
  the lateral loss 4.5x. Raising the lateral rail to 12 V cuts it 144x. The penalty is a
  property of the low-voltage one-sided topology, not of lateral delivery.
* **But no lateral variant beats the vertical architectures.** The best complete row is
  48 V lateral with four-edge feeding at {f(min(float(r['P_total_w']) for r in fam if r['total_is'] == 'COMPLETE' and r['v_lateral'] == '48.0'), 2)} W, against
  126.09 W for Z1 --- and at 48 V "lateral distribution" means the input rail is routed
  laterally and the whole converter sits at the load, which is vertical delivery by another
  name. The family degenerates into the vertical architectures exactly where it becomes
  competitive.
"""
    (OUT / "Z5_REAUDIT.md").write_text(md)


# ============================================================ thermal homogenization
def thermal() -> None:
    rows = rd("effective_layer_properties.csv")
    tsv = [r for r in rows if r["layer"] == "TSV_array"]
    per = [r for r in rows if r["layer"] == "TSV_periodicity_check"]
    bmp = [r for r in rows if r["layer"] in ("microbump_underfill", "C4_underfill", "BGA_mold")]
    rdl = [r for r in rows if r["layer"] == "RDL_dielectric"]
    md = f"""# PHASE 0M PARTS 20-22 --- THERMAL HOMOGENIZATION AUDIT

## Predeclared acceptance, fixed before the RVEs were run

A homogenized tensor is **ACCEPTED** if it reproduces the explicit-geometry RVE within 10 %
on each axis, **CONDITIONAL** between 10 and 25 % with the error reported, and **REJECTED**
above 25 %. (`scripts/phase0m/homogenization.py`, `ACCEPT_PCT = 10.0`.)

## The unit cell is its own periodic cell

For a centred inclusion in a square cell, symmetry puts zero normal flux on every mid-plane,
so adiabatic side walls ARE the periodic boundary condition. Checked, not assumed:
a 1x1 cell and a 2x2 cell give **{f(per[0]['RVE_kxy'], 3) if per else '--'}** and
**{f(per[0]['framework_kxy'], 3) if per else '--'}** W/m.K --- identical to
{f(per[0]['err_framework_kxy_pct'], 3) if per else '--'} %.

## TSV + silicon + liner

| geometry | f_Cu | RVE k_z | RVE k_xy | Voigt k_z (err) | Maxwell k_xy (err) | existing framework k_xy (err) | k_z/k_xy |
|---|---|---|---|---|---|---|---|
{chr(10).join(f"| {r['geometry']} | {f(r['f_inclusion'], 4)} | **{f(r['RVE_kz'], 2)}** | **{f(r['RVE_kxy'], 2)}** | {f(r['voigt_kz'], 2)} ({f(r['err_voigt_kz_pct'], 2)} %) | {f(r['maxwell_kxy'], 2)} ({f(r['err_maxwell_kxy_pct'], 1)} %) | {f(r['framework_kxy'], 2)} ({f(r['err_framework_kxy_pct'], 1)} %) | {f(r['anisotropy_kz_over_kxy'], 3)} |" for r in tsv)}

Three findings:

1. **Along the vias, the rule of mixtures is essentially exact.** Voigt reproduces the RVE
   `k_z` to better than 0.5 % at every geometry. ACCEPTED.
2. **Across the vias, Maxwell-Garnett is CONDITIONAL and the pre-existing framework's
   transverse model is REJECTED at four of the five geometries and CONDITIONAL at the
   fifth --- never ACCEPTED.** Maxwell is 11 to 39 % high; the framework is 19 to 74 % LOW, and it gets worse as the array tightens, because it puts the oxide liner in SERIES
   with the copper so all transverse heat must cross a 1.4 W/m.K barrier. Heat can flow
   around the via; the series model does not let it.
3. **At fixed copper fraction, a SMALLER via is thermally worse in plane.** `r = 5 um` at
   `p = 20 um` and `r = 15 um` at `p = 60 um` have the same copper fraction (0.196) and the
   same `k_z`, but `k_xy` is {f(tsv[2]['RVE_kxy'], 1)} against {f(tsv[0]['RVE_kxy'], 1)} W/m.K
   --- because the liner fraction scales as `t_ox/r`. That is a coupled geometry-thermal
   lever nobody has priced.

## Bump and underfill layers

| layer | geometry | f | RVE k_z | RVE k_xy | Voigt k_z (err) | Maxwell k_xy (err) | k_z/k_xy |
|---|---|---|---|---|---|---|---|
{chr(10).join(f"| {r['layer']} | {r['geometry']} | {f(r['f_inclusion'], 4)} | **{f(r['RVE_kz'], 3)}** | **{f(r['RVE_kxy'], 3)}** | {f(r['voigt_kz'], 3)} ({f(r['err_voigt_kz_pct'], 2)} %) | {f(r['maxwell_kxy'], 3)} ({f(r['err_maxwell_kxy_pct'], 2)} %) | {f(r['anisotropy_kz_over_kxy'], 2)} |" for r in bmp)}

Bump layers are **13 to 22 times more conductive along z than in plane**, and both closed
forms are ACCEPTED there: Voigt for `k_z` to under 1 %, Maxwell for `k_xy` to under 0.5 %.
The contrast is larger than for TSVs and the inclusions are more dilute, which is exactly
where effective-medium theory is at its best.

## RDL and dielectric

| geometry | f_Cu | along the lines | across the lines | through the layer | anisotropy |
|---|---|---|---|---|---|
{chr(10).join(f"| {r['geometry']} | {f(r['f_inclusion'], 4)} | **{f(r['RVE_k_along_lines'], 2)}** | **{f(r['RVE_kxy'], 3)}** | {f(r['RVE_kz'], 2)} | **{f(r['anisotropy_kz_over_kxy'], 1)}x** |" for r in rdl)}

**The RDL is the most anisotropic layer in the package by two orders of magnitude** ---
153x to 276x between along-line and across-line conduction --- and the current framework
gives it a single isotropic conductivity. A caveat this audit must state itself: these cells
model parallel lines in ONE direction. A power PLANE at occupancy near 1, or an orthogonal
two-direction mesh, is much less anisotropic in plane. The ECTC-2024 stack is a TRACE stack
(W/S = 10/2), so for that stack the anisotropy is real.

## Part 22 --- what must NOT be homogenized

The local solder/current-crowding region keeps explicit geometry. Homogenizing it would
destroy exactly the gradients the reliability chain reads: the corner-joint shear, the
damage-weighted stress distribution, and the pad-to-trace constriction. Global/local
submodelling is retained: homogenized tensors in the package model, explicit geometry in the
joint and transition submodels.

## Literature seeds

The anisotropic-equivalent approach for TSV and bump arrays follows He Ma et al.,
*Microelectronics Reliability* 54 (2014), DOI 10.1016/j.microrel.2013.10.003, and
Chuanjun Nie et al., *Microelectronics Reliability* 137 (2022) 114790,
DOI 10.1016/j.microrel.2022.114790. Those papers motivate the form; the numbers here are
computed on this project's own geometry and are not taken from them.
"""
    (OUT / "THERMAL_HOMOGENIZATION_AUDIT.md").write_text(md)


# ============================================================ cooling
def cooling() -> None:
    rows = rd("cooling_architecture_sensitivity.csv")
    etm = rd("cooling_etm_sensitivity.csv")
    md = f"""# PHASE 0M PARTS 23-26 --- COOLING-BOUNDARY AUDIT

## What is in the model now

| use | value | where | status |
|---|---|---|---|
| `h_top` | **166 000 W/m2K** | `results/phase0f/cooling_1kw_calibration.json` | INVERSE-CALIBRATED so the 1-kW package reaches 84 C |
| `h_bottom` | 10 W/m2K | `configs/phase0b/package_stack.yaml` | ASSUMPTION, "natural convection under the package carrier" |
| `T_inf` (top and bottom) | 25 C, uniform | same | ASSUMPTION |
| cooled surface | the TIM top face | `etm/ccxio.py::top_film_faces` | choice, not derived |
| substrate-side variant | h_bottom = 398 672 W/m2K | Phase 0F Sec. 4 | DID NOT CONVERGE; residual +6.96 K |

A calibrated film coefficient is not a cooling technology. It cannot be transferred to
another architecture, it carries no pumping cost, and it cannot produce a streamwise
temperature gradient because its sink temperature is a single number.

## What physical cooler does 166 000 W/m2K represent?

Derived from geometry and flow with `Nu = Nu(alpha)` from Shah and London for laminar
rectangular ducts, straight-fin efficiency, the caloric resistance `1/(2 m_dot c_p)`, and the
laminar friction factor `f Re = C(alpha)`:

| architecture | flow | Re | regime | h_channel | area amp. | **h_effective** | vs 166k | dT_coolant | T_j | dp | pump |
|---|---|---|---|---|---|---|---|---|---|---|---|
{chr(10).join(f"| {r['architecture']} | {f(r['m_dot_g_s'], 1)} g/s | {f(r['Re'], 0)} | {r['regime']} | {f(r['h_channel_W_m2K'], 0)} | {f(r['area_amplification'], 2)} | **{f(r['h_effective_W_m2K'], 0)}** | {f(r['h_eff_over_calibrated'], 2)}x | {f(r['dT_fluid_K'], 1)} K | {f(r['T_j_C'], 1)} C | {f(r['dp_kPa'], 0)} kPa | {f(r['pump_W'], 2)} W |" for r in rows if r['m_dot_g_s'] in ('1.6', '27.0', '50.0'))}

Three results, all of which the Robin boundary hides:

1. **At the source's stated 1.6 g/s the coolant temperature rise is 168 K.** Water cannot
   carry 1125 W at that flow. The flow needed for a 10 K rise is **26.9 g/s, 16.8x** the
   stated value. Whatever 1.6 g/s refers to in the source, it is not the total flow that
   removes the whole package loss with a single-phase coolant.
2. **No laminar architecture reaches h = 166 000 W/m2K.** The best laminar case gets 0.70x.
   Reaching the calibrated value needs the transitional/turbulent regime at 50 g/s, which
   costs **74 W of pumping --- 7.4 % of the load --- and 1.46 MPa of pressure drop.** The
   framework charges neither anywhere.
3. **Two-sided cooling is the largest single lever.** At the same 1.6 g/s per side it reaches
   T_j = 74.3 C where one-sided reaches 123.6 C, because each side carries half the heat and
   the caloric term halves.

The caloric resistance `1/(2 m_dot c_p)` DOMINATES the thermal path at low flow: at 1.6 g/s
it is 0.0747 K/W against 0.013 K/W for convection and conduction combined. A single Robin
coefficient absorbs it into `h` and makes it look like a surface property.

## Part 25 --- can one uniform Robin coefficient represent embedded microchannels?

**No.** Three reasons, in order of size:

* the fluid warms along the channel, and a single sink temperature cannot represent that;
* entrance effects raise the local Nusselt number near the inlet, which a constant `h` cannot;
* the heat generation is spatially non-uniform (a 1 kW die plus 49 converter tiles), so the
  local `h (T_wall - T_f)` balance varies along the flow even at constant `h`.

## Part 26 --- does the cooling ARCHITECTURE change the mechanics?

The same global thermal/mechanical model was run four times, changing ONLY the sink-temperature
field: uniform, then a linear streamwise gradient equal to the coolant rise each mass flow
produces at 1125 W. Total heat removed is unchanged; the MEAN sink temperature is held, so
this isolates the gradient from the level.

| case | sink gradient | T_max | die warpage | vs uniform |
|---|---|---|---|---|
{chr(10).join(f"| {r['tag']} | {f(r['sink_gradient_K'], 2)} K | {f(r['T_max_C'], 3)} C | {f(r['die_warpage_pv_um'], 4)} um | {f(r['warpage_vs_uniform_pct'], 2)} % |" for r in etm)}

**A physically real coolant temperature rise moves the die warpage by 1.5 to 8.2 % and the
peak temperature by 2 to 11 K, and the uniform Robin boundary sets both to zero.** The
sensitivity is to a physical cooling variable --- mass flow --- not to `h`.

(The vehicle is the Phase-0B controlled case at its own load, so the absolute temperatures
are not the 1-kW operating point; the imposed sink gradients are the ones 1125 W produces at
each flow, and the warpage response to an imposed boundary gradient is what is being measured.)

## Part 24 --- the cooling design variables that should exist

`coolant inlet temperature`, `mass flow`, `channel width`, `channel height`, `channel pitch`,
`channel location (top / substrate / both)`, `cold-plate or lid thickness`, `TIM thickness`,
`TIM conductivity`. `h` is DERIVED from these, never chosen. `pressure drop` and `pumping
power` are charged, because at the calibrated operating point they are 7.4 % of the load.

## Icepak

Not revisited. The Phase-0E attempt converged but returned exactly 5000 K on every object ---
a solver clamp, meaning the external cooling boundary never took effect. **No Icepak
validation is claimed and none may be claimed until that setup is understood and repaired.**
"""
    (OUT / "COOLING_BOUNDARY_AUDIT.md").write_text(md)
    print("  wrote Z5_REAUDIT.md, THERMAL_HOMOGENIZATION_AUDIT.md, COOLING_BOUNDARY_AUDIT.md")


if __name__ == "__main__":
    z5(); thermal(); cooling()
