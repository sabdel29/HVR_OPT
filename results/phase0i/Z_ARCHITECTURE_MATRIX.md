# Phase 0I Sec. 2/3 — Vertical-integration architecture matrix

## 1. Why z-placement is a variable, not a given

Phases 0B–0H modelled one integration option: the converter embedded inside the power
substrate. Phase 0H then sourced the GaN heights and concluded `h_sub,min` = 1.176–1.426 mm,
which makes the electrically preferred thin substrate unbuildable. That conclusion was never
labelled architecture-specific, and it is.

The reference system is explicit that both options exist. June-2026, Sec. I:

> "Section II describes the DVPD architecture featuring vertically stacked **in-substrate AND
> backside** VR components."

and Sec. II:

> "when fabricated as individual chiplets, VR components can be **vertically stacked on the
> backside of a substrate** and interconnected through TSVs."

The same section also records that the embedded multi-layer option is **not a demonstrated
technology**:

> "while chip embedding within a **single** substrate layer has been demonstrated, the
> fabrication of **vertically stacked substrate layers** that integrate both active and
> passive components **remains an open challenge**. Based on the findings of this work,
> advances in multi-substrate vertical stacking and chiplet embedding are identified as
> **critical enablers**"

So the architecture Phases 0B–0H treated as the only one is the one the source calls an open
fabrication challenge, and the one it names as an alternative was never modelled mechanically.

## 2. Source-backed technology geometry

June-2026 Table III, used unchanged:

| interface | type | d (µm) | h (µm) | pitch (µm) | R (mΩ) |
|---|---|---|---|---|---|
| Platform / package | BGA, solder | 400 | 300 | 800 | 0.30 |
| PL1 / PL2 / PL3 | TSV, Cu | 30 | 300 | 60 | 7.1 |
| RDL / chiplet | pad, Cu | 10 | 10 | 20 | 1.7 |

Two consequences that Phases 0B–0H never used:

1. **The reference substrate is implicitly ~900 µm** — three power layers at the 300 µm TSV
   height. That is a source-backed thickness.
2. **The selected components do not fit in a reference-thickness power layer.** The low-side
   EPC2090 is 606 µm and the inductor is 500 µm, against a 300 µm layer. Either the layers
   must be made 2–3× thicker than the source's own technology entry, or the components must
   change.

## 3. The architectures

| | Z1 EMBEDDED | Z2 BACKSIDE | Z3 TOPSIDE | Z4 POWER DIE | Z5 2.5D LATERAL |
|---|---|---|---|---|---|
| **source status** | described, **not demonstrated** | **source-backed** | not in the source | partially (chiplet framing) | not the source's, but cited |
| **converter z** | inside the substrate | below the substrate | above, beside the die | above the substrate, below the die | lateral on an interposer |
| **GaN HS** | flip-chipped below z = 0 | in the backside chiplet | topside | on the power die | lateral |
| **GaN LS / caps / inductor** | **in the substrate** | in the backside chiplet | topside | on the power die | lateral |
| **constrains h_sub?** | **YES** — all three | no | no | no | no |
| **TSV rail** | **HV**, 23.4 A | **LV, 1000 A** | HV | **HV**, 23.4 A | HV |
| **1 V path length** | short, under the die | **through the whole substrate** | long lateral | **shortest: 10 µm pads** | long lateral |
| **cooling** | substrate-embedded micro-channels | competes with the BGA field for the board side | consumes the die's cooling surface | sandwiched under the compute die | own top surface |
| **buildable** | CONDITIONAL | **YES** | **REJECTED** | CONDITIONAL | YES |

### Why Z3 is rejected

DVPD exists to put VR outputs *"just tens of microns from the on-chip POLs"* (June-2026
Sec. I). A topside-lateral VR puts the 1 V / 1000 A rail on a multi-millimetre lateral path,
which is exactly the loss DVPD is designed to remove, and it consumes the die's cooling
surface while doing it. It is a strictly worse form of Z5, which at least uses a purpose-built
interposer for the lateral run. Not carried forward.

### Why Z5 is carried but not competitive

Z5 is retained as the **lateral-path bound** — the architecture DVPD exists to beat. Sec. 4
prices it: delivering 1000 A at 1 V across the interposer costs **768 W of RDL loss**, giving
52.8 % system efficiency. It is eliminated on electrical grounds and quantifies why vertical
delivery exists.

## 4. Which components constrain h_sub — the mandatory split

| architecture | inside h_sub (constrains it) | outside h_sub (does not) |
|---|---|---|
| **Z1 EMBEDDED** | LS GaN 606 µm, MLCC (OPEN), inductor 500 µm, 2 × 10 µm interlayer RDL | HS GaN, BGA, board |
| **Z2 BACKSIDE** | *nothing* | HS GaN, LS GaN, MLCC, inductor, BGA, board |
| **Z4 POWER DIE** | *nothing* | all converter components, BGA, board |
| **Z5 2.5D** | *nothing* | all converter components |

**The Phase-0H bound `h_sub,min` = 1.176–1.426 mm is therefore relabelled
EMBEDDED-ARCHITECTURE-SPECIFIC.** It does not apply to Z2, Z4 or Z5.

## 5. Stress-free reference state

Unchanged from Phase 0G and applied identically to every architecture: 25 °C, so all
deformation reported is **incremental operational**, not total assembled. Phase 0G bounded the
effect of that choice at up to +54 % on magnitude with no change of ordering.

Machine-readable form: `configs/phase0i/z_architectures.yaml`.
