# Z1 and Z2 physically closed stacks — specification

Phase 0N-S Tasks 5, 6, 14, 15, 23. **This is the specification the ETM implementation must
satisfy. It is NOT yet implemented** — see §6.

Both candidates use the **2.4 mm board** selected in `research/PCB_THICKNESS_Z2_AUDIT.md`
and the selected-device heights (EPC2014C 685 µm, EPC2057 638 µm).

## 1. Z1 — substrate-embedded, source-derived (SOCC 2023 family A2)

Stacked power layers per Krishnakumar 2026, with the high side flip-chipped to the bottom
substrate RDL. z = 0 at the PCB underside.

| element | t (µm) | z (µm) | class | electrical role |
|---|---:|---|---|---|
| PCB (2.4 mm, full slab) | 2400 | 0 → 2400 | ASSUMPTION/vendor | board |
| BGA field | 300 | 2400 → 2700 | SOURCE_BACKED | 48 V in + return |
| bottom substrate | 300 | 2700 → 3000 | SOURCE_BACKED | 48 V TSV field, supply + return |
| bottom-substrate RDL | 10 | 3000 → 3010 | SOURCE_BACKED | HS flip-chip landing |
| HS GaN EPC2014C | 685 | 3010 → 3695 | SOURCE_BACKED | high side |
| interlayer RDL | 10 | 3695 → 3705 | SOURCE_BACKED | PL1 |
| LS GaN EPC2057 | 638 | 3705 → 4343 | SOURCE_BACKED | low side |
| interlayer RDL | 10 | 4343 → 4353 | SOURCE_BACKED | PL2 |
| flying capacitors | 100 | 4353 → 4453 | BOUNDED | C_f x2 |
| interlayer RDL | 10 | 4453 → 4463 | SOURCE_BACKED | PL3 |
| inductors + output caps | 500 | 4463 → 4963 | SOURCE_BACKED | nearest the POLs |
| output RDL | 10 | 4963 → 4973 | SOURCE_BACKED | 1 V + ground plane |
| microbumps + underfill | 10 | 4973 → 4983 | SOURCE_BACKED | 1 V to die |
| compute die | 300 | 4983 → 5283 | SOURCE_BACKED | load |
| TIM | 50 | 5283 → 5333 | design choice | cooling |

Package above the board: **2933 µm**; total with board **5333 µm**.

## 2. Z2 — land-side distributed cells with a PCB through-cutout

Tier order **inverted** relative to Z1 so the inductor stays nearest the POL.

| element | t (µm) | z (µm) | class | electrical role |
|---|---:|---|---|---|
| PCB frame (2.4 mm, ANNULAR) | 2400 | 0 → 2400 | ASSUMPTION/vendor | cutout 23.36 mm sq |
| BGA field (peripheral only) | 300 | 2400 → 2700 | SOURCE_BACKED | 48 V in + return |
| land-side attach RDL | 10 | 2700 → 2710 | SOURCE_BACKED | 48 V distribution + 1 V collection |
| inductors + output caps | 500 | 2710 → 3210 | SOURCE_BACKED | nearest the substrate/POL |
| interlayer RDL | 10 | 3210 → 3220 | SOURCE_BACKED |  |
| LS GaN EPC2057 | 638 | 3220 → 3858 | SOURCE_BACKED | low side |
| interlayer RDL | 10 | 3858 → 3868 | SOURCE_BACKED |  |
| flying capacitors | 100 | 3868 → 3968 | BOUNDED | C_f x2 |
| interlayer RDL | 10 | 3968 → 3978 | SOURCE_BACKED |  |
| HS GaN EPC2014C | 685 | 3978 → 4663 | SOURCE_BACKED | deepest into the cutout |
| power substrate | 300 | 4663 → 4963 | SOURCE_BACKED | 1 V supply + return TSV fields |
| top RDL | 10 | 4963 → 4973 | SOURCE_BACKED | 1 V + ground plane |
| microbumps + underfill | 10 | 4973 → 4983 | SOURCE_BACKED | 1 V to die |
| compute die | 300 | 4983 → 5283 | SOURCE_BACKED | load |
| TIM | 50 | 5283 → 5333 | design choice | cooling |

Land-side protrusion below the substrate: **1963 µm** nominal,
**2093 µm** at the EPC2014C maximum. Available depth at the worst-case
2.4 mm board: **2460 µm**, leaving **+237 µm** at the device maximum.

## 3. Lateral construction (x/y)

| | Z1 | Z2 |
|---|---|---|
| substrate | 30 × 30 mm | 30 × 30 mm |
| cells | 49 × 2.3685 mm square = 274.89 mm² | identical |
| cell coverage | 30.5 % | 30.5 % |
| cell grid bbox | 21.36 × 21.36 mm | identical |
| **outside the cells** | substrate silicon | **must be explicitly defined** — underfill/mold around the land-side cells, BOUNDED design assumption, never `hvr_effective` |
| PCB | full 30 × 30 mm slab | **annular frame**, central through-cutout 23.36 × 23.36 mm at 1.0 mm sidewall clearance |
| BGA | full field | **peripheral only** — no ball inside the opening |

Cell coordinates must come from the optimizer/floorplanner (`kw1.tiles_for`), never
hard-coded.

## 4. Converter inventory — must be identical (Task 15)

| quantity | value | Z1 | Z2 |
|---|---:|:--:|:--:|
| cells | 49 | ✓ | ✓ |
| HS/cell | 3 | ✓ | ✓ |
| LS/cell | 3 | ✓ | ✓ |
| inductors/cell | 3 | ✓ | ✓ |
| flying caps/cell | 2 | ✓ | ✓ |
| components/cell | 11 | ✓ | ✓ |
| total cell footprint | 274.89 mm² | ✓ | ✓ |
| device models | EPC2014C / EPC2057 / 250 nH / 10 µF | ✓ | ✓ |
| component heights | 685 / 638 / 500 / 100 µm | ✓ | ✓ |

Only **location, support and cooling** may differ. A regression test enforces this.

## 5. Supply and return

Specified in `research/Z1_Z2_SUPPLY_RETURN_GEOMETRY.md`. Both architectures need
geometrically distinct supply and return fields; `R_loop = 2 R_field` is not acceptable
for a package claimed to be closed.

## 6. What is NOT implemented

| gate (Task G / 18) | status |
|---|---|
| component placement and z-closure | **specified** (this document) |
| lateral non-overlap, 49 discrete cells | specified; Z2 mesh still a full-area layer |
| board/package clearance | **established** for 2.4 mm |
| BGA capacity | power established; **package I/O out of model** |
| supply/return continuity | **specified, NOT implemented** |
| equal component inventory | specified; test added |
| explicit material outside cells | **undefined** |
| annular PCB mesh + surviving ball field | **NOT implemented** |
| thermal boundary definition | two cases specified, none selected |
| mesh convergence on the new geometry | **not done** |

**No ETM run may be made until every row above is closed.** No `results/phase0ns` lineage
exists, and a guard fails if one appears.
