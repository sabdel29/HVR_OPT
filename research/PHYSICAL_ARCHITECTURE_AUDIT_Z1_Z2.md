# Physical architecture audit — Z1 and Z2

Phase 0N. Evidence-driven reconstruction of what the code **builds**, not what the
figures depict. Every number below is measured from the production mesh by
`scripts/phase0n_reconstruct_stack.py` or produced by
`scripts/phase0n_conv_extent_experiment.py`.

Baseline: branch `main`, HEAD `e893264` before this phase. Submodule
`Scalable_Integrated_VR` pinned at `ed56ae6`.

---

## 1. Verdict up front

| question | verdict |
|---|---|
| Does the 1921 µm converter fit inside Z1's 1.30 mm substrate? | **No, and the code never tries.** It embeds 1226 µm and places the remaining 695 µm (high-side GaN + one RDL) nowhere. |
| Is Z1 dimensionally closed as modelled? | **Yes, exactly** — 74 + 1226 = 1300 µm, with zero slack — **but only because the high-side device is absent from the mesh.** |
| Is Z2 dimensionally closed as modelled? | **Yes as a layer stack, but the construction is not physical.** The 1226 µm converter is a full-area slab stacked on top of a 300 µm BGA. |
| Is the Z1/Z2 comparison a comparison of PLACEMENT? | **No.** Z1 carries 337.02 mm³ of converter medium, Z2 carries 1103.40 mm³ — a factor of 3.27. |
| Do the headline mechanical/thermal numbers survive correcting that? | **The Δu_c ordering survives; the magnitude and the temperature ordering do not.** See §6. |

**Overall classification (Section E scale): C — physically inconsistent as currently
modelled**, for Z2. Z1 is category B: geometrically consistent but with an unmodelled
high-side device and an unsourced substrate thickness.

---

## 2. What the code actually builds

Measured from the production mesh (`production_et.build_global`), substrate
30 × 30 mm = 900 mm², 49 VR cells of 5.61 mm² = 274.9 mm² (**30.5 % areal coverage**).
z = 0 is the substrate underside; +z is towards the compute die.

### Z1 — `ARCH_Z1_EMBEDDED`, h_sub = 1.30 mm, z ∈ [−1.900, +1.660] mm

| layer | material | z0 (mm) | z1 (mm) | t (µm) | volume (mm³) |
|---|---|---:|---:|---:|---:|
| `board` | board_fr4 | -1.9000 | -0.3000 | 1600 | 1440.00 |
| `bga` | bga_homog | -0.3000 | -0.0000 | 300 | 270.00 |
| `sub_lower` | silicon | -0.0000 | +0.0740 | 74 | 46.26 |
| `sub_lower` | tsv_homog | -0.0000 | +0.0740 | 74 | 20.34 |
| `tile_band` | silicon | +0.0740 | +1.3000 | 1226 | 766.38 |
| `tile_band` | hvr_effective | +0.0740 | +1.3000 | 1226 | 337.02 |
| `interface` | underfill_homog | +1.3000 | +1.3100 | 10 | 5.00 |
| `die` | silicon | +1.3100 | +1.6100 | 300 | 149.99 |
| `tim` | tim | +1.6100 | +1.6600 | 50 | 25.00 |

### Z2 — `ARCH_Z2_BACKSIDE`, h_sub = 0.30 mm, z ∈ [−3.126, +0.660] mm

| layer | material | z0 (mm) | z1 (mm) | t (µm) | volume (mm³) |
|---|---|---:|---:|---:|---:|
| `board` | board_fr4 | -3.1260 | -1.5260 | 1600 | 1440.00 |
| `bga` | bga_homog | -1.5260 | -1.2260 | 300 | 270.00 |
| `conv` | underfill_homog | -1.2260 | +0.0000 | 1226 | 766.38 |
| `conv` | hvr_effective | -1.2260 | +0.0000 | 1226 | 337.02 |
| `sub_lower` | silicon | +0.0000 | +0.2800 | 280 | 175.03 |
| `sub_lower` | tsv_homog | +0.0000 | +0.2800 | 280 | 76.97 |
| `tile_band` | silicon | +0.2800 | +0.3000 | 20 | 12.50 |
| `tile_band` | tsv_homog | +0.2800 | +0.3000 | 20 | 5.50 |
| `interface` | underfill_homog | +0.3000 | +0.3100 | 10 | 5.00 |
| `die` | silicon | +0.3100 | +0.6100 | 300 | 149.99 |
| `tim` | tim | +0.6100 | +0.6600 | 50 | 25.00 |

### Provenance of every dimension

| dimension | value | class | source |
|---|---|---|---|
| substrate footprint | 30 × 30 mm | **design choice** | `package_stack.yaml`, "reduced test vehicle", status ASSUMPTION |
| compute die | 22.36 × 22.36 × 0.300 mm | **sourced** | June-2026 reference footprint (500 mm²) |
| h_sub, Z1 | 1.30 mm | **design choice** | Phase 0H: component-height-limited interval 1.176–1.426 mm. **Not** the reference system's substrate |
| h_sub, Z2 | 0.30 mm | **sourced** | June-2026 Table III: power-layer TSV height h = 300 µm |
| TSV diameter / pitch | 30 / 60 µm | **sourced** | June-2026 Table III |
| Z1 TSV span | 74 µm | **derived** | h_sub − t_cell = 1300 − 1226 |
| Z2 TSV span | 300 µm | **derived** | full substrate |
| embedded cell | 1226 µm | **derived** | 500 (L) + 606 (GaN LS) + 100 (MLCC) + 2×10 (RDL), `zarch.embedded_cell_um()` |
| converter template stack | 1921 µm | **derived** | 685 + 100 + 606 + 500 + 3×10 RDL, four-tier partition template |
| GaN HS height | 685 µm | **sourced** | EPC2212 datasheet — **but the electrical model uses EPC2014C** (§4) |
| GaN LS height | 606 µm | **sourced** | EPC2090 datasheet — **but the electrical model uses EPC2057** (§4) |
| inductor height | 500 µm | **sourced** | Shared_Core_UIC_250_nH (Rasheedi, TCPMT 2026) |
| MLCC height | 100 µm | **unsourced, bounded** | `MLCC_H_UM`, envelope 0 / 100 / 250 µm; manufacturer page unreachable |
| interlayer RDL | 10 µm | **sourced** | ECTC-2024 Table I |
| BGA ball d / h / p | 400 / 300 / 800 µm | **sourced** | June-2026 Table III |
| PCB | 1.6 mm FR-4 | **design choice** | `board.py` BOARD_CASES envelope; "no board data exists for this vehicle" |
| interface (microbump) | 10 µm | **sourced** | microbump field, r = 5 µm, pitch 20 µm |
| TIM | 50 µm | **design choice** | package stack |
| die-to-component gap | — | **unsourced** | `package_clearances.yaml`, OPEN, bounded 10/25/50 µm |
| cavity sidewall | — | **unsourced** | OPEN, bounded 15/30/60 µm |
| cooler standoff | — | **unsourced** | OPEN, bounded 0/50/100 µm |
| **Z2 package-to-PCB standoff** | **absent** | **not modelled** | no entry exists; see §5 |

---

## 3. The 1921 µm vs 1.30 mm question, resolved

The two numbers appear in **adjacent rows of the same manuscript table** (Table I:
"Substrate thickness, Z1 / Z2 — 1.30 / 0.30 mm" and "Converter stack height — 1921 µm")
and the Fig. 2 caption says the cells are "built into the 1.30 mm substrate". A reader
necessarily concludes that 1921 µm of converter sits inside 1300 µm of substrate. That
is impossible, and it is **not what the code does**.

What the numbers actually mean:

- **1921 µm** is the **four-tier partition-template height**, and identically the
  `ARCH_Z4` power-die stack total in `configs/phase0mr2/z4_stack.yaml`:
  `10 (RDL) + 685 (GaN HS) + 606 (GaN LS) + 500 (inductor) + 100 (MLCC) + 10 (RDL) + 10 (bond) = 1921`.
  It is the serial height of the **component set**, used by routing/realizability.
- **1226 µm** is the **Z1 embedded cell**: `500 + 606 + 100 + 2×10`. It **excludes the
  685 µm high-side device**, because `zarch.embedded_cell_um()` follows June-2026 Sec. II,
  which flip-chips the high-side GaN to the RDL of the **bottom** substrate, below z = 0.

**Dimensional closure for Z1:** `74 µm (TSV span) + 1226 µm (embedded cell) = 1300 µm`.
Exact, with **zero slack** — no core, no build-up, no capture-pad allowance beyond the
two 10 µm RDLs already inside the 1226.

**Therefore 695 µm of the converter (685 µm HS + 10 µm RDL) is outside the 1.30 mm
substrate, and is present nowhere in the Z1 mesh.** Below z = 0 the Z1 mesh contains only
`bga` (300 µm) and `board` (1600 µm). The high-side device has **no geometry**: no
thickness, no stiffness, no CTE, no thermal mass. Its loss (10.736 W, `P_switch_hs_conduction`)
is nonetheless deposited into the embedded-cell band via `converter_total()`, i.e. **above**
z = 0 rather than below it.

Consequences, stated plainly:

1. Z1's modelled package is **695 µm shorter** than the converter it claims to contain.
2. If the high-side device really is flip-chipped below z = 0, it protrudes 685 µm into a
   gap the model gives 300 µm of BGA — a **385 µm interference** — unless a bottom
   substrate exists, which the model does not have.
3. The manuscript's "built into the 1.30 mm substrate" is true of 1226/1921 = **63.8 %**
   of the converter by height, and false of the rest.

---

## 4. Device identity inconsistency

| role | electrical model (`kw1.design_1kw()`) | geometric height |
|---|---|---|
| high side | **EPC2014C**, 16 mΩ, 1.87 mm² | **EPC2212**, 685 µm |
| low side | **EPC2057**, 8.5 mΩ, 1.80 mm² | **EPC2090**, 606 µm |

Four different part numbers. The manuscript's Table I lists the **electrical** pair
(EPC2014C / EPC2057) and the stack height derived from the **geometric** pair. No
statement in the repository reconciles them. The loss model, the device areas and the
EPC2057 drain-bar landing area all follow the electrical pair; the 1226 µm and 1921 µm
heights follow the geometric pair.

This is **unresolved** and is not fixed in this phase: changing either pair changes either
the loss ledger or the stack height, and both are paper-frozen.

---

## 5. Z2 — connectivity and the PCB/cavity question

What the code builds, bottom to top:

```
board  [-3.126, -1.526]   1600 µm  FR-4
bga    [-1.526, -1.226]    300 µm  homogenised solder-ball field
conv   [-1.226,  0.000]   1226 µm  hvr_effective, FULL AREA (900 mm²)
substrate [0.000, 0.300]   300 µm  silicon, TSV field over the full thickness
```

So in the model the **BGA balls land on the bottom face of the converter**, and the
converter's top face is the substrate underside. There is **no cavity, no standoff, and
no peripheral BGA field**. The converter is effectively a full-area interposer inserted
into the BGA-to-substrate path.

This is dimensionally closed but it is **not a construction any source in this repository
demonstrates**, and it has two physical problems:

1. **Every package I/O and every power/return ball must pass through or around a 1226 µm
   stack of GaN dice, inductors and MLCCs.** The model gives that stack one homogeneous
   medium and no routing, so the question never arises numerically.
2. **The manuscript describes something different.** "The cells are mounted on the
   substrate underside" is a *discrete, laterally distributed* picture: 49 cells of
   5.61 mm² occupying 30.5 % of the backside, with the remaining 69.5 % available for the
   BGA field. The model instead fills 100 % of the backside with converter medium.

**If Z2 is read the way the manuscript describes it** — discrete backside cells with a
surrounding BGA field — then the balls must span the cell height:

```
required ball height  ≥ 1226 µm (cell) + die-to-component gap
sourced ball height   =   300 µm      (June-2026 Table III)
shortfall             ≥   926 µm
```

That shortfall must be absorbed by one of: a **BGA ≈ 4× taller than the sourced geometry**,
a **PCB cavity ≥ 0.93 mm deep**, a **package-substrate cavity**, or a **secondary
interposer/socket**. **None of these is in the model, and none is sourced.** The
`package_clearances.yaml` ledger has entries for the die-to-component gap, the cavity
sidewall and the cooler standoff, but **no entry for a package-to-PCB standoff or a
backside protrusion** — the one clearance Z2 actually needs.

---

## 6. The lateral-extent defect and its consequences

`zglobal.stack_for` gives Z2 its converter as `("conv", CONV_CELL_MM, "hvr_effective", 2)`
— a **full-area layer**. `mesh.build` then assigns `hvr_effective` to every element in it.
Z1's converter, by contrast, lives in `tile_band`, where `hvr_effective` is applied **only
inside a VR-cell footprint** and the rest stays silicon.

Measured converter medium:

| architecture | converter volume | out-of-cell area |
|---|---:|---|
| Z1 | **337.02 mm³** | silicon (substrate) |
| Z2 (frozen) | **1103.40 mm³** | **hvr_effective — i.e. more converter** |

A factor of **3.27**. The two architectures do not carry the same converter, so the frozen
comparison is **not** a comparison of placement alone. This matters doubly because the
primary source motivates DVPD precisely on the grounds that one should *not* form "a single
mechanically stiff region within the substrate" — yet the model gives Z2 exactly that
(a continuous 1226 µm, 120 GPa plate) while giving Z1 the distributed treatment.

### The experiment

`scripts/phase0n_conv_extent_experiment.py` reruns the frozen pipeline unchanged, then
reruns Z2 with the out-of-cell backside area filled with a non-converter medium, so that
both architectures carry an identical **337.02 mm³** of converter. Z1 is unaffected.

| variant | out-of-cell medium | P_elec (W) | T_max (°C) | die warpage (µm) | Δu_c (µm) | D_u | Δu_c vs Z1 | ΔT vs Z1 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Z1 | silicon | 137.292 | 118.32 | 41.616 | 4.6252 | — | — | — |
| **Z2 frozen** | hvr_effective | 139.659 | 126.46 | 38.916 | 3.8714 | **1.1947** | **16.30 %** | **+8.14 K** |
| Z2 cell-only | underfill (8 GPa) | 146.422 | 171.24 | 51.855 | 1.5930 | 2.9035 | 65.56 % | +52.92 K |
| Z2 cell-only | silicon (130 GPa) | 137.945 | 115.55 | 36.924 | 4.4591 | 1.0373 | 3.59 % | -2.77 K |

The frozen row reproduces `results/phase0mr3c/final_etm_replay.csv` **exactly**
(137.292 / 139.659 W, 118.32 / 126.46 °C, 41.616 / 38.916 µm, 4.6252 / 3.8714 µm,
D_u = 1.1947), confirming the instrumentation is non-invasive.

### What this means

1. **The Δu_c ordering is robust in DIRECTION.** D_u > 1 in all three variants: Z2 carries
   the lower displacement driver however the backside is filled.
2. **The MAGNITUDE is not a result.** It ranges from **3.59 % to 65.56 %** — a factor of
   18 — across defensible fills. The frozen **16.30 %** is one point inside that range and
   carries no more authority than the others.
3. **The temperature ordering REVERSES.** The frozen model reports Z2 **+8.14 K hotter**;
   with a silicon fill Z2 is **2.77 K cooler**. The claim "Z2 is the hotter architecture"
   is therefore **not established**.
4. The frozen pair's "+8.14 K hotter yet 16.3 % lower response" headline — the central
   decoupling claim — **rests on an unsourced choice of what occupies 69.5 % of the
   backside**, not on architecture placement.

The local solder response (Δε_in, D_ε = 1.2260) was **not** rerun for the variants. It is
driven by Δu_c and T_joint, both of which move by large factors here, so **D_ε = 1.2260
and the 18.43 % figure must be treated as conditional on the frozen backside fill**.

### Which fill is right?

**None of the three.** A physically correct Z2 is laterally structured: VR cells over
30.5 % of the backside, BGA balls and package fill over the rest, with the balls spanning
the cell height. The model cannot represent that, because the BGA is a separate full-area
layer **below** the converter rather than coexisting with it. Fixing this properly requires
a backside construction that no source in this repository supplies — see §5.

---

## 7. Connectivity as modelled

From `scripts/phase0i/zarch.py::path_for`, which is the authoritative power path:

**Z1 EMBEDDED**
1. board → substrate underside — `bga`, HV 48 V, 23.43 A system
2. underside → embedded cell — `tsv`, HV 48 V, through h_sub − t_cell = **74 µm**
3. conversion in the power layers — inside the substrate
4. cell → die POL — `microbump`, LV 1 V, 1000 A, 10 µm pads
5. lateral spreading under the die — package RDL

**Z2 BACKSIDE**
1. board → backside VR — `bga`, HV 48 V, short
2. conversion on the backside chiplet — below the substrate
3. backside VR → die — `tsv`, LV 1 V, **1000 A**, through the **full 300 µm**
4. substrate top → die POL — `microbump`, LV
5. lateral spreading under the die — package RDL

The **return path is not represented as geometry** in either architecture. The electrical
model uses a loop resistance (`R_loop = 2 × R_field` in `tier_resistance`), i.e. return is
accounted as a factor of two on the supply resistance. There is no distinct ground
structure, no return-via field and no return plane in the mesh.

---

## 8. What remains unsourced or open

| item | status |
|---|---|
| Z1 bottom substrate hosting the high-side device | **absent from the model** |
| Z2 package-to-PCB standoff / backside protrusion clearance | **absent from the model and from the clearance ledger** |
| Z2 out-of-cell backside medium | **unsourced; the result depends on it at the factor-of-18 level** |
| device identity (EPC2014C/2057 electrical vs EPC2212/2090 geometric) | **unreconciled** |
| die-to-component gap, cavity sidewall, cooler standoff | OPEN, bounded, already ledgered |
| MLCC height | OPEN, bounded 0/100/250 µm |
| substrate footprint 30 × 30 mm | ASSUMPTION |
| PCB stackup | ASSUMPTION (FR-4 envelope) |
| microvia current allowable, capture-pad diameter, vendor design rule | OPEN |
| return-path geometry | not modelled (loop factor of 2 only) |

---

## 9. Literature comparison matrix

**Access rule applied:** a construction column is filled **only** from a source read in
full. Where only metadata was reachable the row says `NOT ACCESSIBLE` and **nothing is
inferred from the title or abstract**, per the audit brief.

| source | DOI | access | architecture type | VR location | VR count / distribution | substrate / interposer | converter→die path | PCB→converter path | cavity? | backside? | built or conceptual | relevance to Z1/Z2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Krishnakumar *et al.* 2026, "Comprehensive Design Framework for VPD in HPC" | `10.1109/TCPMT.2026.3724907` | **FULL** | DVPD | VR components **vertically stacked across multiple power layers**; HS GaN **flip-chipped to the RDL of the bottom substrate**; LS bottom layer, flying caps middle layer, inductors top layer near the POLs | fine-pitch network of horizontally distributed VRs; per-VR current `I_o/M` | **three stacked substrate power layers**, each 300 µm (Table III: PL1/PL2/PL3 TSV h = 300 µm) ⇒ **≈900 µm implied** | VR outputs "just tens of microns from the on-chip POLs" | BGA 400 µm dia / **300 µm high** / 800 µm pitch (Table III) | not stated | **yes, as an alternative**: "when fabricated as individual chiplets, VR components can be vertically stacked on the **backside** of a substrate and interconnected through TSVs" | conceptual framework + models | **THE source for both Z1 and Z2.** Z1 is its multi-substrate option; Z2 is its backside-chiplet sentence |
| Sriharini *et al.* ECTC 2024, "VPD for HPC with Buck-Derived Regulators" | `10.1109/ECTC51529.2024.00364` | **FULL** | VPD → DVPD | "multiple VRs ... distributed **below and/or along the periphery** of the functional die" | multiple, on/in-interposer | interposer | shortened VR-to-POL high-current paths | not detailed | not stated | not stated | conceptual + analysis | confirms the VPD/DVPD distinction; no cross-section for Z1/Z2 |
| "Design Considerations for DC-DC VRs in DVPD Systems", ISCAS 2024 | `10.1109/ISCAS58744.2024.10558456` | **FULL** | DVPD | distributed | optimal **number and placement** of VRs is the paper's subject | not detailed | not detailed | not detailed | no | no | analysis | supports VR-count scaling only |
| "Embedded Vertical PDN (EV-PDN) incl. VR for Over-1 kW FC-BGA on Over-1 mm Thick-Core Organic Substrate", ECTC 2025 | `10.1109/ECTC51687.2025.00176` | metadata only | NOT ACCESSIBLE | NOT ACCESSIBLE | NOT ACCESSIBLE | NOT ACCESSIBLE | NOT ACCESSIBLE | NOT ACCESSIBLE | NOT ACCESSIBLE | NOT ACCESSIBLE | NOT ACCESSIBLE | **Topically the closest potential precedent for Z1** (>1 kW, embedded VR, >1 mm thick-core organic substrate). **Not verified.** Our substrate is modelled as *silicon*, not organic, so equivalence must not be asserted. |
| "VPD for Emerging Packaging and Integration Platforms", SOCC 2023 | `10.1109/SOCC58585.2023.10256973` | metadata only | NOT ACCESSIBLE | NOT ACCESSIBLE | NOT ACCESSIBLE | NOT ACCESSIBLE | NOT ACCESSIBLE | NOT ACCESSIBLE | NOT ACCESSIBLE | NOT ACCESSIBLE | NOT ACCESSIBLE | four VPD architecture families claimed by the brief; **cannot be used to classify Z1/Z2 without the full text** |
| "Package Power Delivery ... 1 kW IVR in CCM-DCM Boundary Mode", ECTC 2024 | `10.1109/ECTC51529.2024.00054` | metadata only | NOT ACCESSIBLE | NOT ACCESSIBLE | NOT ACCESSIBLE | NOT ACCESSIBLE | NOT ACCESSIBLE | NOT ACCESSIBLE | NOT ACCESSIBLE | NOT ACCESSIBLE | NOT ACCESSIBLE | cited in the manuscript as `Ramin_VPD`; cross-section not verified here |
| "A VPD Architecture for HPC", TPEL 2025 | `10.1109/TPEL.2025.3531414` | metadata only | NOT ACCESSIBLE | — | — | — | — | — | — | — | — | cited as `VPD_transactions_...`; not verified |
| "Vertically Stacked Dual-Bus DC–DC Converter", TPEL 2025 | `10.1109/TPEL.2025.3532833` | metadata only | NOT ACCESSIBLE | — | — | — | — | — | — | — | hardware per the brief | would be the reference for real vertical converter assembly; **not verified** |
| "Integrated VPD – Review & Challenges", TCPMT 2026 | `10.1109/TCPMT.2026.3716987` | metadata only | NOT ACCESSIBLE | — | — | — | — | — | — | — | review | taxonomy **cannot be adopted** without the full text |

All nine DOIs were resolved against Crossref and the titles match the brief. Six of nine
could not be read in full from this environment (no open copy; WebSearch is blocked here,
as already recorded in `configs/phase0mr2/package_clearances.yaml`).

### What the one fully-readable architecture source actually supports

| our model | the source | match? |
|---|---|---|
| Z1: **one** 1.30 mm substrate, 1226 µm contiguous embedded band | **three** stacked power layers of 300 µm (≈900 µm), one component class per layer | **NO** |
| Z1: high-side device absent from geometry | high-side GaN **flip-chipped to the RDL of the bottom substrate** | **NO** — the source places it; we do not model it |
| Z1: inductor in the top tier nearest the die | "inductors (top layer near the POLs)" | **YES** |
| Z1: LS below, flying caps between | "low-side switches (bottom layer), flying capacitors (middle layer)" | **ordering matches**, but ours are stacked inside one band, not one per power layer |
| Z2: converter chiplet below the substrate, 1 V across the substrate via TSVs | "when fabricated as individual chiplets, VR components can be vertically stacked on the backside of a substrate and interconnected through TSVs" | **YES in concept** — but the source gives **no** backside dimensions, no BGA relationship and no cavity |
| Z2: converter as a continuous full-area layer | source says *distributed* cells, and argues against "a single mechanically stiff region" | **NO** |
| substrate material: silicon | source is a substrate/power-layer stack; material not established here | unverified |
| BGA 400/300/800 µm | Table III, verbatim | **YES** |

The source also states plainly that the Z1 family is **not demonstrated**:

> "while chip embedding within a single substrate layer has been demonstrated, the
> fabrication of **vertically stacked substrate layers that integrate both active and
> passive components remains an open challenge**."

which `configs/phase0i/z_architectures.yaml` already records.

---

## 10. Package height and board-clearance audit (Section E)

Thicknesses measured from the mesh. "Modelled" means the element set exists; "required" means the construction needs it and the model does not have it.

### Z1

| element | t (µm) | cumulative (µm) | status |
|---|---:|---:|---|
| board | 1600 | 1600 | modelled (ASSUMPTION: FR-4 envelope) |
| bga | 300 | 1900 | modelled |
| sub_lower | 74 | 1974 | modelled |
| tile_band | 1226 | 3200 | modelled (converter in 30.5 % of area) |
| interface | 10 | 3210 | modelled |
| die | 300 | 3510 | modelled |
| tim | 50 | 3560 | modelled |
| **total modelled** | **3560** | | |
| **package only (excl. PCB)** | **1960** | | |
| high-side GaN below z = 0 | 685 | — | **REQUIRED, NOT MODELLED** |
| **total if the source construction is honoured** | **4245** | | |

### Z2

| element | t (µm) | cumulative (µm) | status |
|---|---:|---:|---|
| board | 1600 | 1600 | modelled (ASSUMPTION: FR-4 envelope) |
| bga | 300 | 1900 | modelled |
| conv | 1226 | 3126 | modelled (converter in 100 % of area — see §6) |
| sub_lower | 280 | 3406 | modelled |
| tile_band | 20 | 3426 | modelled |
| interface | 10 | 3436 | modelled |
| die | 300 | 3736 | modelled |
| tim | 50 | 3786 | modelled |
| **total modelled** | **3786** | | |
| **package only (excl. PCB)** | **2186** | | |

### Clearance findings

| architecture | clearance | required | available | verdict |
|---|---|---:|---:|---|
| Z1 | high-side device below the substrate | 685 µm | 300 µm (BGA) | **interference of 385 µm** unless a bottom substrate is added |
| Z1 | die-to-component gap | 10–50 µm (OPEN) | 10 µm `interface` layer | satisfied ONLY at the 10 µm bound, and only by re-using a functional microbump layer as a clearance |
| Z1 | substrate budget | 1226 + 74 = 1300 µm | 1300 µm | closed with **zero slack** |
| Z2 | package-to-PCB standoff for discrete cells | ≥ 1226 µm | 300 µm (BGA) | **shortfall of 926 µm**; no entry exists in the clearance ledger |
| Z2 | converter / PCB intersection as modelled | — | — | none (the converter is stacked serially on the BGA) |
| both | cooler standoff | 0–100 µm (OPEN) | 0 µm | at the 0 µm bound only |

### Verdict

- **Z1 — category B**, geometrically consistent but dependent on explicitly identified unsourced values, **and** with one required element (the high-side device) absent from the model entirely. Its substrate closes exactly, with no room for the die-to-component gap at any bound above 10 µm.
- **Z2 — category C**, physically inconsistent as currently modelled. The construction the manuscript describes (discrete backside cells) cannot be assembled with the sourced 300 µm BGA, and the construction the code builds (a full-area converter interposer carrying every ball) is not demonstrated by any source available here.

**Terminology consequence.** "Geometrically realizable" must not be used for the package as a whole. The evidence supports only the narrowest of the four levels:

| level | Z1 | Z2 |
|---|---|---|
| vertical-interconnect realizability (microvia topology, AR) | **GEOMETRICALLY REALIZABLE / PROCESS-CONDITIONAL** (worst AR 0.833 at a source-bounded 150 µm pitch) | same |
| component / package-stack realizability | **NOT ESTABLISHED** — the high-side device has no place in the stack | **NOT ESTABLISHED** — the backside construction is undefined |
| board / package assembly realizability | **NOT ESTABLISHED** — 385 µm interference | **NOT ESTABLISHED** — 926 µm shortfall |
| manufacturing qualification | **NOT CLAIMED** (3 process inputs OPEN) | **NOT CLAIMED** |
---

## 11. What Z1 and Z2 should be called (Section I)

Names must describe the construction that exists, not the one the figures suggest.

| | recommended name | why | names REJECTED, and why |
|---|---|---|---|
| **Z1** | **substrate-embedded distributed VR cells (single-layer, high-side external)** | The 49 cells are embedded in a single package substrate; the low side, flying capacitors and inductors are inside it; the high side is declared external and is not modelled. | *"multi-layer stacked-substrate embedded VR"* — the source's construction, but **not ours**: ours is one 1.30 mm substrate, not three 300 µm power layers. *"cavity-embedded VR"* — no cavity geometry exists; only an unsourced `cavity_sidewall_um` bound. *"EV-PDN / thick-core FC-BGA embedded VR"* — the ECTC 2025 precedent is **unverified** and uses an *organic* core, where ours is modelled as silicon. |
| **Z2** | **package-backside distributed VR cells (board interface undefined)** | The cells sit below the substrate and the 1 V output crosses it through TSVs, which matches the source sentence. Everything between the cells and the PCB is undefined, and the name must say so. | *"PMIC in a cavity"* — **no.** There is no cavity anywhere in the model, and no PMIC: the converter is 49 cells of discrete GaN dice, inductors and MLCCs, not a packaged power-management IC or module. *"PCB-cavity VR"* — a PCB cavity is one way to resolve the 926 µm shortfall, but it is **not modelled and not sourced**; naming it after a fix we have not made would assert the fix. *"backside VR module"* — "module" implies a packaged assembly with its own substrate and terminals; none is defined. |

**On "PMIC" specifically.** The term should not be used anywhere for this work. A PMIC is a
packaged integrated circuit. Our regulator is a synthesised cell of **{N=3 EPC2014C
high-side dice, K=3 EPC2057 low-side dice, 3 inductors, 2 flying capacitors}** — eleven
discrete components per cell, 49 cells. Neither the implementation nor any source
available to this audit packages them as a PMIC.

**If the honest answer is that the construction is an abstraction, say so.** It is: for
Z2 the model places a converter medium below the substrate without defining how it
attaches to, or coexists with, the board interface. That is a legitimate modelling
abstraction for a placement study, but it is not a package, and the manuscript must not
imply otherwise.

---

## 12. Commit record

| # | SHA | subject |
|---|---|---|
| 1 | `0f43fa8` | audit: reconstruct Z1 Z2 physical stack and connectivity |
| 2 | `314f2d7` | research: validate VPD vs DVPD terminology and architecture precedents |
| 3 | `6649058` | test: add physical stack and topology regression guards |
| 4 | `4e089e2` | audit: package height, clearance, naming and architecture claim matrix |
| 5 | `12ad496` | docs: correct ETM manuscript architecture definitions and claim scope |

Baseline before this phase: `e893264` on `main`. Submodule `Scalable_Integrated_VR`
unchanged at `ed56ae6` throughout (its working tree carries pre-existing local IDE
files, which were not touched and not committed).

**No commit in this phase modified any frozen artifact under `results/phase0mr3c/`.**
The commit that would have been #7 in the suggested progression --- `results: rerun
corrected ETM frozen pair` --- was **deliberately not made**: a corrected rerun requires
choosing a backside construction, and no source available to this work supplies one.
Producing a new "authoritative" pair from an invented construction would replace a
documented conditionality with an undocumented one. The bracket in section 6 is reported
instead.
