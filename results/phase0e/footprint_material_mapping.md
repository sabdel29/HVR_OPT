# Phase-0E Sec.12 — HVR Footprint → Physical Material Mapping

## 1. What was assumed before

Phase 0B/0C/0D modelled the HVR tile as a homogeneous block of `hvr_effective`
(E = 120 GPa, ν = 0.28, CTE = 6.0 ppm/K, k = 60 W/mK) filling the **entire electrical
bounding box** at a fixed 150 µm thickness. Every mechanical footprint result in this project
rests on that. The stack file flags it itself: *"MUST be replaced by the HVR compiler stack
height"*, and all four properties are tagged PROVISIONAL.

The strongest DVPD-specific novelty candidate is footprint. If the material model that
produces its mechanical half is wrong, the novelty is wrong. Hence this section.

## 2. What the compiler actually builds

The HVR optimiser's own area rule (`HVR_FULL_OPT_EPC_V2._compute_area`) is

```python
return max( arch.N * fp_hs ,  arch.K * fp_ls ,
            arch.K * ind.footprint_mm2 ,  (arch.N - 1) * cap.footprint_mm2 )
```

a **maximum**, not a sum — components sit on separate layers and the tile footprint is set by
the largest layer. That matches June-2026: *"all VR components are vertically aligned within a
single cell footprint"*, and *"the overall VR footprint is primarily determined by the low-side
switches and the embedded inductors"*. Every other layer is therefore only partially filled.

### Component inventory across the footprint sweep

| j (A/mm²) | A_HVR (mm²) | N,K | hs GaN | ls GaN | inductor | capacitor | Σ component | areal fill |
|---:|---:|---|---:|---:|---:|---:|---:|---:|
| 1.5 | 34.32 | 4,4 | 15.00 | 34.32 | 4.00 | 13.50 | 66.82 | 0.4867 |
| 2.0 | 25.74 | 3,3 | 11.25 | 25.74 | 3.00 | 9.00 | 48.99 | 0.4758 |
| 4.0 | 15.00 | 4,4 | 15.00 | 15.00 | 4.00 | 13.50 | 47.50 | 0.7917 |

Parts: high-side EPC2055 (3.75 mm²), low-side EPC2366 (8.58 mm²) or EPC2055, inductor
`Shared_Core_UIC_250_nH` (1 mm², **500 µm tall**, category `silicon_interposer`), capacitor
Murata GRM31 22 µF/50 V 1206 (4.5 mm², MLCC).

### The headline geometric fact

    A_HVR              spans 34.32 -> 15.00 mm^2   = 2.288x
    total component area spans 66.82 -> 47.50 mm^2 = 1.407x

**The CTE-mismatched material does not scale with the bounding box.** Between j = 2.0 and
j = 4.0 the bounding box shrinks 42 % while the component area shrinks 3 %: the parts do not
get smaller, they pack more densely (areal fill 0.476 → 0.792).

## 3. The composite tile

Constituents (silicon SOURCE_BACKED from `package_stack.yaml`; ceramic and mould flagged):

| constituent | E (GPa) | ν | CTE (ppm/K) | k (W/mK) | status |
|---|---:|---:|---:|---:|---|
| silicon (GaN-on-Si devices, Si-interposer inductor) | 130 | 0.28 | 2.6 | 130 | SOURCE_BACKED |
| ceramic (X7R MLCC) | 110 | 0.30 | 10.0 | 3 | ASSUMPTION |
| mould / dielectric fill | 8 | 0.32 | 30.0 | 0.7 | PROVISIONAL (underfill card) |

Voigt mixture for E and k; stiffness-weighted (Levin/Turner) CTE, because a volume-weighted
CTE would over-credit the compliant mould, which is the phase least able to transmit the
mismatch. Layer thicknesses are taken equal: only the inductor height (500 µm) is sourced, and
the GaN/MLCC heights are OPEN — but the footprint *trend* depends on the ratio of layer areas,
not on the common thickness.

| j | φ_silicon | φ_ceramic | φ_mould | E_eff (GPa) | CTE_eff (ppm/K) | k_eff |
|---:|---:|---:|---:|---:|---:|---:|
| 1.5 | 0.3884 | 0.0983 | 0.5133 | 65.4 | 5.544 | 51.15 |
| 2.0 | 0.3884 | 0.0874 | 0.5242 | 64.3 | 5.493 | 51.12 |
| 4.0 | 0.5667 | 0.2250 | 0.2083 | 100.1 | 4.886 | 74.49 |
| *homogeneous card* | — | — | — | *120.0* | *6.000* | *60.0* |

The homogeneous card overstates stiffness by up to 1.87x and CTE by 8-23 %.

## 4. FE result — the question actually answered

Both variants: identical geometry, placement, converter power (frozen at 85 °C), thermal
boundary conditions, mesh and solver. The **only** difference is the tile material.

| j | A_HVR total (mm²) | homogeneous w (µm) | composite w (µm) | ratio |
|---:|---:|---:|---:|---:|
| 4.0 | 60.00 | 2.009 | 2.128 | 1.0590 |
| 2.0 | 102.96 | 2.926 | 3.109 | 1.0624 |
| 1.5 | 137.28 | 3.756 | 3.976 | 1.0585 |

| variant | warpage span over A = 60 → 137 mm² | dw/dA (µm/mm²) |
|---|---:|---:|
| homogeneous | **1.8696x** | +0.02261 |
| composite | **1.8685x** | +0.02391 |

## 5. Verdict

# FOOTPRINT ETM OPPOSITION: ROBUST

The physical material distribution shifts warpage **uniformly by +5.9 to +6.2 %** and changes
the footprint **sensitivity by 0.06 %** (1.8696x → 1.8685x). The opposition survives intact.

### Why — and why a scaling argument would have got this wrong

A naive drive metric `E_eff * CTE_eff * A_HVR` predicts the footprint span weakening from
2.288x to 1.697x, a 26 % reduction. **The FE run shows no weakening at all.** The reason is
that the tile plays two opposing mechanical roles: it *drives* bending through CTE mismatch,
and it *resists* bending as a local stiffener. Softening it (120 → 65 GPa) increases warpage
through the second mechanism while the reduced CTE decreases it through the first, and the two
nearly cancel — which is also why warpage went *up* slightly when the tile got softer.

What survives is that the footprint dependence is **geometric**: it is set by how much of the
package area is occupied by a dissimilar inclusion, not by that inclusion's precise moduli.
That makes it robust to the single largest material uncertainty in the model, which is the
strongest thing that can be said for a mechanism resting on PROVISIONAL cards.

## 6. Still open

* **Tile height.** The selected inductor is 500 µm tall on its own, while the mechanical model
  uses a 150 µm tile inside a 200-500 µm substrate. **The chosen converter does not physically
  fit the modelled stack.** This does not affect the footprint *trend* (all cases share the
  same tile height) but it means absolute warpage magnitudes are not design values. This is now
  the largest single geometric inconsistency in the vehicle and is carried to the next gate.
* GaN and MLCC layer heights are OPEN, so per-layer volumes rest on the equal-thickness choice.
* The ceramic card is an ASSUMPTION; no primary MLCC elastic data was retrieved.
