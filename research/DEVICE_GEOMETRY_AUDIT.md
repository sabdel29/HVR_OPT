# Selected-device geometry audit

Phase 0N-R Section 7. Phase 0N found that the package geometry used heights attributed to
**EPC2212 / EPC2090** while the electrical model selects **EPC2014C / EPC2057**. The
official datasheets were retrieved and read.

Source: `https://epc-co.com/epc/documents/datasheets/EPC2014C_datasheet.pdf` and
`..._EPC2057_datasheet.pdf`, retrieved 2026-10-22. The PDFs are publisher documents and
are **not committed** (the repository `.gitignore` excludes publisher PDFs); the extracted
dimensions and their exact location in each document are recorded below so every number
is traceable without redistributing the files.

## Convention

**Overall mounted height to the seating plane, including the solder terminal.** Both
datasheets dimension their Side View that way, and it is the height an embedded-component
cavity must actually clear. Applied identically to both devices.

## What the datasheets say

| | EPC2014C (high side) | EPC2057 (low side) |
|---|---|---|
| die size | 1.7 × 1.1 mm (`A` = 1702, `B` = 1087 µm nom.) | 1.5 × 1.2 mm (`A` = 1500, `B` = 1200 µm nom.) |
| die thickness | not dimensioned separately | **518 ± 25 µm** |
| terminal | **100 ± 20 µm** solder bar | **120 ± 12 µm** solder bump |
| **overall height** | **685 µm nominal, 815 µm max** | **638 µm nominal** (= 518 + 120) |
| where | DIE OUTLINE, Side View | DIE OUTLINE, Side View |

## Resolution

**High side — no change, the comment was wrong.** The frozen code carried
`GAN_HS_UM = 685.0  # EPC2212 datasheet Side View, nominal (815 max)`. Both the nominal
**and** the max match the **EPC2014C** datasheet exactly. The height was always the
selected device's height; only the part number in the comment was wrong. Comment
corrected; value unchanged.

**Low side — a real 32 µm error.** The frozen code carried
`GAN_LS_UM = 606.0  # EPC2090 datasheet: 518 +/- 25 die + 50 Cu + 3 Ni + 35 solder`.
The 518 ± 25 die is right, but the 88 µm terminal build-up (50 Cu + 3 Ni + 35 solder) is
**not** what EPC2057 specifies: its Side View gives a **120 ± 12 µm** bump and a **638 µm**
overall. **606 → 638 µm.**

So there was never a genuine two-device-set inconsistency in the *values*; there was one
mislabelled comment and one incorrect terminal stack.

## Recomputed geometry

| quantity | frozen | corrected | rule |
|---|---:|---:|---|
| embedded cell | 1226 µm | **1258 µm** | inductor 500 + GaN LS + MLCC 100 + 2 × 10 RDL |
| component stack | 1921 µm | **1953 µm** | HS 685 + MLCC 100 + LS + inductor 500 + 3 × 10 RDL |
| Z1 TSV span at h_sub = 1.30 mm | 74 µm | **42 µm** | h_sub − cell |
| minimum closing h_sub | 1276 µm | **1308 µm** | cell + `H_TSV_MIN_UM` = 50 µm (ASSUMPTION) |

## Consequence: the frozen Z1 substrate no longer closes

`zarch.realizable("ARCH_Z1_EMBEDDED", 1.30)` with the corrected height returns

> **feasible = False** — "embedded cell is 1258 µm and needs 50 µm of TSV beneath it, so
> h_sub must be ≥ 1308 µm; got 1300 µm"

**The frozen 1.30 mm substrate is 8 µm short.** It becomes feasible at 1.308 mm
(AR 1.67) and comfortably so at 1.35 mm (AR 3.07).

This is small in absolute terms and decisive in kind: Phase 0N already found that Z1's
substrate closed *exactly*, with zero slack. Any correction that lengthens the cell must
therefore break it, and this one does.

## Why this is opt-in rather than the default

Making 638 µm the default would change `CONV_CELL_MM`, hence the mesh, hence every number
in `results/phase0mr3c/`, which must stay reproducible. Per the Phase-0N-R brief no new
pair may be frozen until both architectures are physically closed. The corrected geometry
is therefore selected with `PHASE0NR_DEVICE_GEOM=selected` and reported; the default path
is unchanged and byte-identical.

## Still open

- `H_TSV_MIN_UM = 50 µm` is an **ASSUMPTION**, and the 8 µm verdict depends on it. At a
  42 µm minimum the frozen substrate would close. The verdict is "infeasible against the
  framework's own stated minimum", not "infeasible against a process rule".
- MLCC height remains **OPEN**, bounded 0 / 100 / 250 µm. At the 250 µm bound the cell is
  1408 µm and h_sub must be ≥ 1458 µm.
- The inductor's 500 µm is sourced from the part, not from a mounted-height dimension, so
  it may not follow the same convention as the two GaN devices.
