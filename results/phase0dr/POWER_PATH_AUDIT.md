# Phase-0D-R — Architecture Power-Path Audit

## 0. Why this audit exists

Phase 0D applied a **global** rule: the thickness-dependent TSV carries converter *input*
current. That rule is a property of one particular stack ordering, not of DVPD in general.
Where conversion sits in the physical stack determines which rail — and therefore which
current — traverses every interconnect segment. This audit traces the actual path for each
architecture and assigns rails segment by segment.

## 1. The rule that replaces the assumption

For every segment:

```
rail = HV  <=>  segment is UPSTREAM of the converter   ->  I = I_in  = P_in / V_in
rail = LV  <=>  segment is DOWNSTREAM of the converter ->  I = I_out
P_in = V_out * I_out + P_conv            (actual converter loss; never assumed ideal)
```

At the Phase-0B/0C operating point (I_out = 60 A/VR, 48 V → 1 V, P_conv ≈ 5 W/VR):

| rail | current per VR | ratio |
|---|---:|---:|
| LV (1 V) | 60.00 A | — |
| HV (48 V) | 1.354 A | **44.3× smaller** |

Since `P = I²R`, an identical physical segment dissipates **~1960×** more on the LV rail than
on the HV rail. Which side of the converter a segment sits on is therefore the single most
important electrical fact about it.

## 2. The three architectures

| | ARCH_A | ARCH_B | ARCH_C |
|---|---|---|---|
| description | HVR embedded at the **top** of the power substrate | HVR embedded at the **bottom** (land-side) | 2.5D lateral HVR beside the die |
| tile face | top | bottom | lateral |
| **rail through the thickness-dependent TSV** | **HV (48 V)** | **LV (1 V)** | **HV (48 V)** |
| HV traverses | BGA, TSV | BGA | BGA, C4, TSV |
| LV traverses | microbump, RDL | TSV, microbump, RDL | RDL (long lateral), microbump |
| mechanical geometry | the validated Phase-0B/0C vehicle | tile at the other substrate face | tile outside the die footprint |

**ARCH_A is the geometry Phase 0B/0C validated and Phase 0D analysed.** Its
`embed_from: top` places the tile flush with the substrate top, so the TSV field spans from
the board side up to the tile underside and is upstream of conversion. The Phase-0D
conclusion was therefore correct *for ARCH_A* — but it was stated as if general.

**ARCH_B is the architecture in which a genuine thickness tension can exist**: the BGA feeds
the converter input almost directly, and the entire 1 V output must cross the substrate
vertically.

## 3. Segment-by-segment (see `current_path_by_architecture.csv` for the full table)

```
ARCH_A:  board --BGA(48V,1.35A)--> substrate_bottom --TSV(48V,1.35A)--> [CONVERTER]
                                          --microbump(1V,60A)--> die
                                          --RDL sheet(1V,240A total)--> POLs

ARCH_B:  board --BGA(48V,1.35A)--> [CONVERTER] --TSV(1V,60A)--> substrate_top
                                          --microbump(1V,60A)--> die
                                          --RDL sheet(1V,240A total)--> POLs

ARCH_C:  board --BGA--> --C4(48V,1.35A)--> --TSV(48V,1.35A)--> [CONVERTER]
                                          --RDL long lateral(1V,240A)--> die edge
                                          --microbump(1V,60A)--> die
```

## 4. Interconnect library and its validation

Every tier is modelled separately with its own geometry, **cross-section shape**, material,
temperature dependence, parallel count and current limit. A C4 is not a microbump and is not
modelled as one.

| tier | shape | geometry | R model (20 °C) | June Table III | error | status |
|---|---|---|---:|---:|---:|---|
| BGA | circular | d 400 µm, h 300 µm, p 800 µm, solder | 0.3104 mΩ | 0.3 mΩ | +3.45 % | SOURCE_BACKED |
| TSV | circular | d 30 µm, h 300 µm, p 60 µm, Cu | 7.2150 mΩ | 7.1 mΩ | +1.62 % | SOURCE_BACKED |
| microbump | **square** | 10 × 10 µm, h 10 µm, p 20 µm, Cu | **1.7000 mΩ** | **1.7 mΩ** | **−0.00 %** | SOURCE_BACKED |
| C4 | circular | d 100 µm, h 70 µm, p 150 µm, solder | 1.1586 mΩ | — | — | **ASSUMPTION** (absent from June) |
| RDL | sheet | t_Cu 5 µm, occupancy 0.6 | 5.667 mΩ/sq | — | — | ASSUMPTION |

**Cross-section shape matters and was recovered from the source.** June's quoted 100 µm² pad
area corresponds to a **square** 10 × 10 µm pad, not a circle: assuming circular would give
2.165 mΩ and overstate that tier by 27 %. Using the square reproduces their 1.7 mΩ exactly.
BGA (125 663 µm²) and TSV (707 µm²) are circular, confirming the mixed convention.

## 5. Ground return — a Phase-0D omission

Phase 0D modelled only the supply. Every real path is a loop:

```
R_loop = R_supply + R_ground
```

Modelled as a symmetric return (identical parallel structure), so `R_loop = 2·R_supply` and
**every interconnect loss in Phase 0D was understated by a factor of 2**. Marked ASSUMPTION;
an asymmetric return would change the factor but not the conclusion that Phase 0D omitted it.

## 6. Feasibility is a hard gate

```
n_required = ceil(I / I_max)
if n_required > n_available(footprint, pitch):  ARCHITECTURE IS INFEASIBLE
```

Phase 0D used `n = min(n_required, n_available)` and continued, which silently overloads the
via field. The corrected gate produces an immediate architecture-dependent result:

| I_via_max | ARCH_A (HV rail) | ARCH_B (LV rail) |
|---|---|---|
| 33 mA | 42 vias required of 6 666 available — **feasible** | 1 819 of 6 666 — **feasible** |
| **4.8 mA** | 283 of 6 666 — feasible | **12 501 of 6 666 — INFEASIBLE** |

The per-via limit is **OPEN**: June reports 30 202 TSVs on PL1 for a 1 kA load, implying
≈33 mA/via if PL1 carries output current, or ≈4.8 mA if it carries input-side RMS current.
Under the conservative reading, **the LV-TSV architecture cannot be built at this current
density** — the via field physically cannot carry 60 A through a 4.9 mm tile footprint. This
is a real design constraint that only appears once feasibility is enforced rather than clipped.

## 7. What the audit changes

1. **Phase 0D's TSV-rail assumption is correct for ARCH_A and wrong for ARCH_B.** It was
   stated generally; it is architecture-specific.
2. **The dominant distribution loss is not the TSV at all — it is the lateral RDL sheet.**
   See the Phase-0D-R gate report §9.
3. **Ground return doubles every interconnect loss.**
4. **Feasibility can eliminate an architecture outright**, which no amount of loss
   optimisation would reveal.
