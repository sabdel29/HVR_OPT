# PHASE 0M PARTS 14-16 --- COMPONENT-PARTITION AUDIT

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
| **summed component footprint** | **18.01 mm2** |
| ratio | **3.21x** |

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
| `T0_SINGLE_LEVEL` | 1 | 685 um | 18.01 mm2 | 882.5 mm2 | **False** (1.76) | L0 |
| `T1_EMBEDDED_4LAYER` | 4 | 2071 um | 5.61 mm2 | 274.9 mm2 | **True** (0.55) | none |
| `T2_BACKSIDE_CHIPLET` | 3 | 1455 um | 11.01 mm2 | 539.5 mm2 | **False** (1.08) | chip1 |
| `T3_POWER_DIE` | 3 | 1455 um | 11.01 mm2 | 539.5 mm2 | **False** (1.08) | pd_active |
| `T4_SPLIT_SC_BUCK` | 2 | 1301 um | 9.61 mm2 | 470.9 mm2 | **True** (0.94) | none |
| `T5_SWITCH_INTERPOSER_IND_EMBEDDED` | 2 | 1195 um | 15.01 mm2 | 735.5 mm2 | **False** (1.47) | interposer |
| `T6_CAPS_NEAR_DIE` | 3 | 1455 um | 11.01 mm2 | 539.5 mm2 | **False** (1.08) | mid |
| `T7_IND_SUBSTRATE_ACTIVE_BACKSIDE` | 2 | 1195 um | 15.01 mm2 | 735.5 mm2 | **False** (1.47) | backside |

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
