#!/usr/bin/env python3
"""Phase-0M Parts 16, 39, 40 -- partition audit, focused sensitivities, new ETM levers."""
from __future__ import annotations
import csv, math
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


def partition() -> None:
    rows = rd("component_partition_templates.csv")
    md = f"""# PHASE 0M PARTS 14-16 --- COMPONENT-PARTITION AUDIT

## 1. Was component-level z partitioning previously modelled?

**Implicitly, in exactly one place, and nowhere it could be checked.**

```
Scalable_Integrated_VR/src/HVR_FULL_OPT_EPC_V2.py::_compute_area
    return max(arch.N * fp_hs,
               arch.K * fp_ls,
               arch.K * ind.footprint_mm2,
               (arch.N - 1) * cap.footprint_mm2)
```

`max`, not `sum`. The sibling implementation in `HVR_FULL_OPT_sizing.py` is explicit about
what that means --- its docstring reads *"Vertical stacking model: total footprint is the
max across layers"*. The V2 docstring says only *"Total estimated component footprint"* and
the V2 file header claims the function was *"fixed: area = SUM of all component footprints
(not max)"*. **It is a max.**

Consequences for the compiled 1-kW design (N = 3, K = 3):

| | value |
|---|---|
| reported `total_area_mm2` | 5.61 mm2 |
| = `N x fp_hs` = 3 x 1.87 | 5.61 mm2 |
| **summed component footprint** | **{f(rows[0]['summed_component_area_mm2'], 2)} mm2** |
| ratio | **{f(float(rows[0]['summed_component_area_mm2']) / 5.61, 2)}x** |

So four-layer vertical stacking is **already assumed by the converter area model** and by
nothing else. The electrical model places the whole VR as one terminal; the thermal model as
one heat-generating block; the mechanical model as one `hvr_effective` solid with one
modulus and one CTE. Nothing verifies that the four layers the area model presumes exist in
a given architecture, and no model knows WHICH component sits WHERE.

## 2. Template library

`configs/phase0m/component_partition_templates.yaml`. Checks applied to each: component
height, per-level footprint, whole-array footprint against the 500 mm2 die shadow,
voltage-isolation (does a level mix the 48 V and 1 V domains), thermal path, interconnect
density, manufacturing plausibility.

| template | levels | stack height | max level area | array footprint | fits die shadow | mixed-V levels |
|---|---|---|---|---|---|---|
{chr(10).join(f"| `{r['template']}` | {r['n_levels']} | {f(r['stack_height_um'], 0)} um | {f(r['max_level_area_mm2'], 2)} mm2 | {f(r['area_all_cells_mm2'], 1)} mm2 | **{r['fits_die_shadow']}** ({f(r['die_shadow_utilisation'], 2)}) | {r['levels_with_mixed_voltage_domain']} |" for r in rows)}

## 3. Which partitions are physically credible

* **`T1_EMBEDDED_4LAYER` --- credible on geometry, NOT demonstrated.** It is the only
  template that both fits the die shadow comfortably (55 %) and puts no voltage-domain
  boundary inside a level. It needs a 2.07 mm stack, which is why the Phase-0H substrate
  bound is what it is. The source itself calls multi-layer substrates integrating active and
  passive components *"an open challenge"*.
* **`T4_SPLIT_SC_BUCK` --- credible, and the most interesting result here.** Splitting by
  VOLTAGE DOMAIN (high-side switches plus flying capacitors on one tier, low-side switches
  plus inductors on the other) is the only TWO-level template that fits (94 % utilisation)
  and the only one besides T1 with no mixed-voltage level. Two levels instead of four is a
  large manufacturing simplification. The architecture class is named by Krishnakumar and
  Partin-Vaisband, SoCC 2023, DOI 10.1109/SOCC58585.2023.10256973.
* **`T2_BACKSIDE_CHIPLET` and `T3_POWER_DIE` --- do NOT fit as three-level stacks.** Putting
  both switch banks on one active tier needs 11.01 mm2 per cell, 539.5 mm2 for the array
  against a 500 mm2 die: **8 % over**. Z2 and Z4 as currently conceived need a fourth level
  or a larger footprint. That is new and it was invisible while the VR was one lumped block.
* **`T0_SINGLE_LEVEL` --- INFEASIBLE by 1.76x.** A one-level VR at 1 kW needs 882.5 mm2
  against a 500 mm2 die. **Vertical component partitioning is not an optimization; it is a
  precondition.**
* **`T5` and `T7` --- do not fit** (147 %), because they put three component classes on one
  tier.

## 4. Does any partition change rail assignment or electrical ranking?

**Rail assignment: YES, for `T4_SPLIT_SC_BUCK` and only for it.** Every other template keeps
the whole converter between one input terminal and one output terminal, so the rail crossing
the substrate is set purely by where that block sits --- which is what `zarch.path_for`
already encodes. T4 puts a THIRD rail on the stack boundary: the intermediate
`V_in / N = 16 V` node now crosses between tiers, carrying `I = P_in / 16 = 1.44 A` per cell
instead of either 0.48 A (48 V) or 20.4 A (1 V). That is a rail the power-path graph has no
representation for.

**Electrical ranking: NO, on the present evidence.** The intra-VR metallization is
common-mode across Z1, Z2 and Z4 (the same compiled cell), and the T4 intermediate rail
carries 1.44 A, whose loss over a 0.65 mm via stack is below 1 mW per cell. What the
partition changes decisively is **feasibility**, not ranking: three of the eight templates do
not fit the die shadow at all.
"""
    (OUT / "COMPONENT_PARTITION_AUDIT.md").write_text(md)


def levers() -> None:
    tsv = rd("tsv_geometry_sensitivity.csv")
    eff = rd("effective_layer_properties.csv")
    crowd = [r for r in rd("current_crowding_transition_sweep.csv") if r["status"] == "OK"]
    cool = rd("cooling_architecture_sensitivity.csv")
    etm = rd("cooling_etm_sensitivity.csv")
    route = [r for r in rd("intra_vr_routing_model.csv") if r.get("level") == "R1"]
    ks = [float(r["K_crowd"]) for r in crowd]
    ps = [float(r["p_system_w"]) for r in route]
    small = next((r for r in eff if r["geometry"].startswith("r_cu=5")), None)
    big = next((r for r in eff if r["geometry"].startswith("r_cu=15") and "p=60" in r["geometry"]), None)
    md = f"""# PHASE 0M PART 40 --- NEW CROSS-DOMAIN ETM DESIGN LEVERS

A lever qualifies here only if it moves at least two domains in OPPOSITE or non-obvious
directions, and only if Phase 0M measured it.

## 1. TSV allocation POLICY, not TSV radius

The radius is not a loss lever for a minimum-provisioned field: `R_field = rho h J_max / I`
contains no geometry at all, and `phi_Cu = I / (J_max A_field)` contains neither the radius
nor the height, so the thermal and mechanical effective properties do not move either.
The lever is the POLICY and the provisioning current density.

| what moves | electrical | thermal | mechanical | feasibility |
|---|---|---|---|---|
| radius, policy A | **nothing** (0.07 % over r = 2.5 to 50 um) | nothing | nothing | improves |
| radius, policy B | `1/r^2`, 314 % | `phi ~ r^2` | `phi ~ r^2` | worsens |
| provisioning `J_max` | `R ~ J_max` | `phi ~ 1/J_max` | `phi ~ 1/J_max` | improves |

**Derating harder LOWERS the loss.** Halving `J_max` halves the field resistance and doubles
the copper fraction, at twice the area. No part of the current framework can express that,
because `J_max` enters only as a feasibility check.

## 2. Liner fraction, which is `t_ox / r` and not a thickness

At the SAME copper fraction (0.196) and the same `k_z`, a 5 um via at 20 um pitch gives
`k_xy = {f(small['RVE_kxy'], 1) if small else '--'}` W/m.K against
`{f(big['RVE_kxy'], 1) if big else '--'}` for a 15 um via at 60 um pitch --- a
{f(float(big['RVE_kxy'])/float(small['RVE_kxy']), 2) if small and big else '--'}x difference
caused entirely by the liner occupying a larger fraction of a smaller via. Fine-pitch TSV
fields are thermally worse in plane at equal copper. Electrically they are identical.

## 3. RDL copper: three domains, three different signs

More RDL copper lowers the electrical loss, raises lateral thermal spreading and raises the
copper fraction of a layer whose CTE sits between silicon and organic. Phase 0M adds the
quantity that was missing: the RDL is **153x to 276x anisotropic** in plane, so "more copper"
is direction-dependent and the framework's single isotropic `k` cannot express it.

## 4. Transition geometry, which is worth more than the transition

`K_crowd` spans **{f(min(ks), 3)} to {f(max(ks), 3)}** over {len(crowd)} converged geometries
against the single constant 1.326 in use. More usefully, the EXCESS resistance `dR` is
length-INDEPENDENT to five decimals while `K_crowd` is not, so `dR` is the transferable
quantity and `K_crowd` is an artifact of how much bulk conductor one attaches to the
transition. A generous landing pad can make `K_crowd < 1`.

## 5. Component z placement changes feasibility before it changes loss

Three of eight partition templates do not fit the 500 mm2 die shadow; a single-level VR
misses by 1.76x. The `T4_SPLIT_SC_BUCK` template puts an intermediate 16 V rail across a
tier boundary --- a rail the power-path graph cannot currently represent.

## 6. Cooling mass flow, which is a MECHANICAL variable

The coolant temperature rise is an IN-PLANE gradient across the die. Measured on the global
model with only the sink field changed:

| coolant rise across the die | T_max shift | die warpage shift |
|---|---|---|
{chr(10).join(f"| {f(r['sink_gradient_K'], 2)} K | {f(r['Tmax_vs_uniform_K'], 2)} K | {f(r['warpage_vs_uniform_pct'], 2)} % |" for r in etm)}

A uniform Robin boundary sets both to zero by construction. Flow rate is therefore a
mechanical design variable, and pumping power is a real cost: reaching the calibrated
`h = 166 kW/m2K` needs about 74 W, **7.4 % of the load**, which nothing in the framework
charges.

## 7. Intra-VR metallization, which is a loss term nobody has

{f(min(ps), 2)} to {f(max(ps), 2)} W system-wide depending on the RDL stack and the via
allocation policy --- {f(100*min(ps)/1000, 2)} % to {f(100*max(ps)/1000, 2)} % of the load,
against a converter loss of 125.3 W. It is common-mode across architectures, so it does not
reorder them, but it is not small and it is currently zero.

## Summary: what should become an optimizer variable

| variable | why it qualifies | measured effect |
|---|---|---|
| TSV allocation policy | sets whether radius matters at all | 0.07 % vs 314 % on field R |
| provisioning `J_max` | inverts the usual area/loss trade | `R ~ J_max` exactly |
| `t_ox / r` (liner fraction) | thermal-only, invisible electrically | 1.5x on in-plane k |
| RDL `t x N_layers` | electrical, thermal spreading, stiffness | 4.06 to 39.31 W intra-VR |
| pad / trace transition geometry | 2.4x on a factor now held constant | `K_crowd` 0.61 to 1.48 |
| component partition template | decides FEASIBILITY, not loss | 3 of 8 do not fit |
| coolant mass flow | thermal AND mechanical | 8.2 % warpage, 74 W pumping |
| lateral rail voltage (Z5 family) | 2.5D is not one point | 768 W to 0.33 W |
"""
    (OUT / "NEW_ETM_LEVERS.md").write_text(md)
    print("  wrote COMPONENT_PARTITION_AUDIT.md, NEW_ETM_LEVERS.md")


if __name__ == "__main__":
    partition(); levers()
