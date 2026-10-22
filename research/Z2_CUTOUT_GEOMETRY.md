# Z2-CUTOUT geometry

Phase 0N-R Tasks B and C. **Land-side distributed VR cells with a PCB through-cutout.**
Topology precedent in `research/Z2_CUTOUT_SOURCE_AUDIT.md`; **no dimension below comes
from a patent** — all are our sourced component heights and the framework's own BGA/PCB
values.

## 1. The correction that forced this document

Phase 0N-R's first pass called the Z2 backside cell **1258 µm**. That is wrong, and the
error is structural rather than arithmetic.

`CONV_CELL_MM = inductor + GaN LS + MLCC + 2 × RDL` is the **embedded-cell** quantity. Its
own docstring justifies excluding the high-side device because, in Z1, "the HIGH-SIDE
device is flip-chipped to the RDL of the **bottom substrate**". **Z2 has no bottom
substrate — it *is* the thing below the substrate.** There is nowhere to offload the high
side to, so Z2 must carry all four tiers.

`zglobal.stack_for` nevertheless hands the same `CONV_CELL_MM` to Z2's `conv` layer.
**The frozen Z2 model therefore understates its own converter height by 695 µm**
(1226 µm modelled against 1921 µm of frozen-device components).

| | frozen devices | corrected devices |
|---|---:|---:|
| what the model gives Z2 | 1226 µm | — |
| four-tier component stack | 1921 µm | **1953 µm** |
| understatement | **695 µm** | — |

## 2. Where the high-side device is in Z2

**In the cell, deepest into the cutout.** It cannot be anywhere else: Z1's justification
depends on a bottom substrate that Z2 does not have, and no source places a Z2 high side
elsewhere.

This also **inverts the tier order**. Krishnakumar 2026 puts the inductor in the top power
layer "near the POLs". Z2 hangs below the substrate, so keeping the inductor nearest the
die means the inductor is nearest the substrate and the high-side device is furthest from
it — i.e. deepest into the board.

## 3. The cell stack, from the substrate underside downward

| layer | t (µm) | z (µm) | note |
|---|---:|---|---|
| land-side attach RDL | 10 | 0 → 10 | 1 V collection + 48 V distribution plane |
| inductor + output cap | 500 | 10 → 510 | nearest the substrate, so nearest the POL |
| interlayer RDL | 10 | 510 → 520 | — |
| LS GaN EPC2057 | 638 | 520 → 1158 | 518 +-25 die + 120 +-12 bump |
| interlayer RDL | 10 | 1158 → 1168 | — |
| flying capacitors | 100 | 1168 → 1268 | BOUNDED 0/100/250 um, OPEN |
| interlayer RDL | 10 | 1268 → 1278 | — |
| HS GaN EPC2014C | 685 | 1278 → 1963 | deepest into the cutout; 685 nom / 815 max |
| **serial total** | **1963** | | four-tier stack is 1953 µm without the land-side RDL |

All **11 components per cell** are placed: 3 × HS EPC2014C, 3 × LS EPC2057, 3 inductors,
2 flying capacitors. Output capacitance shares the inductor tier, exactly as the frozen
partition template `T1C_REORDERED` does (`inductor+cap_out` is one tier). The four tiers
are **serial in z**; the routing/tier model allocates one component class per tier and the
per-tier area bound (max 5.61 mm²) is what makes that possible.

## 4. Height closure

| quantity | value | status |
|---|---:|---|
| BGA ball height | 300 µm | **SOURCE_BACKED** (Krishnakumar 2026 Table III) |
| PCB thickness | 1600 µm | **ASSUMPTION** (`board.py` FR-4 envelope) |
| substrate underside → PCB backside | **1900 µm** | available through-cutout depth |
| cell serial stack | 1963 µm | derived from sourced device heights |
| **protrusion past the PCB backside** | **+63 µm** | |

**Without a cutout** the only gap is the ball height, and the shortfall is
**1663 µm** — not the 958 µm the first pass reported, because that figure used the
HS-excluding 1258 µm.

So a through-cutout **very nearly closes the height**: the stack ends 63 µm proud of the
board backside. That is a first-order closure only. Still unaccounted, and each additive:

- land-side attach solder/underfill between cell top and substrate RDL;
- cutout **sidewall** clearance (lateral, §5) and any bottom keep-out;
- a bottom thermal interface and heat sink if used (ARM FIG. 3) — this alone would exceed 63 µm;
- tolerance stack: the HS is 685 µm **nominal but 815 µm max**, which alone adds 130 µm and
  pushes the protrusion to **193 µm** at the device-maximum corner.

**Verdict: dimensionally plausible, not yet closed.** At nominal heights the deficit is 63 µm;
at the EPC2014C maximum it is 193 µm; with any bottom heat sink it is larger. Closing it
needs one of: a thinner land-side attach, a recessed cutout step, a thinner board under the
cutout, or accepting a protrusion the system can package around.

## 5. Cutout footprint and remaining BGA sites

49 cells of 2.3685 mm side; the cell grid bounding box is
21.360 × 21.360 mm.

| sidewall clearance (mm) | cutout (mm) | BGA sites remaining | removed |
|---:|---|---:|---:|
| 0.0 | 21.36 × 21.36 | 640 | 729 |
| 0.5 | 22.36 × 22.36 | 585 | 784 |
| 1.0 | 23.36 × 23.36 | 528 | 841 |

of 1369 sites on the 0.8 mm lattice over 30 × 30 mm. **No clearance value is
sourced**; 0.5–1.0 mm is carried as a bounded engineering range, consistent in spirit with
the already-OPEN `cavity_sidewall_um` ledger entry.

## 6. What remains unsourced

- the cutout itself (patent precedent only, **no dimensions in either patent**);
- sidewall clearance;
- land-side attach stack;
- bottom thermal interface;
- PCB thickness (already an ASSUMPTION) and whether a board can be locally thinned;
- whether a 21.4 mm square hole is acceptable in a server board's stiffness and
  routing budget — **ARM and Intel both show cutouts but neither sizes one**.
