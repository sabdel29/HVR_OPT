# Phase 0I Sec. 5 — Realizability, per architecture (DEFECT #33)

## 1. The defect

`kw1.design_1kw()` takes no architecture argument:

```
design_1kw(m_vr=49, j=3.5, h_sub_mm=1.5, bound='nominal')
coupled_1kw(arch, ...)  ->  des, g, why = design_1kw(m_vr, j, h_sub_mm)
```

The embedded rule `t_cell + h_tsv ≤ h_sub` was therefore applied to **every** architecture.
Demonstrated directly:

```
h_sub = 0.30 mm -> "no inductor fits h_sub=300 um (budget 30 um)"
h_sub = 0.50 mm -> "no converter from the 1 fitting inductors"
h_sub = 0.80 mm -> "realizable"
```

identical for ARCH_A, ARCH_B and ARCH_C. But **ARCH_B converts below the substrate and
ARCH_C converts beside the die** — neither puts the inductor inside `h_sub`. The electrical
model has varied the converter's vertical position since Phase 0D-R; the geometric and
mechanical models never did.

**Every "unbuildable" verdict Phase 0H issued against a thin substrate is
embedded-specific.** This is **DEFECT #33**.

## 2. The architecture-aware rule

**Embedded (Z1).** Unchanged: `h_sub ≥ t_cell + h_tsv,min`, with `t_cell` the summed
component stack. With the Phase-0H sourced heights, `t_cell` = 1126 / 1226 / 1376 µm for the
optimistic / nominal / pessimistic MLCC bound, giving `h_sub,min` = **1.176 / 1.276 /
1.426 mm**.

**Everything else.** The converter is not in the substrate, so the substrate only has to carry
a TSV field and the binding constraint is TSV manufacturability. June-2026 Table III gives
`d` = 30 µm at `h` = 300 µm, a **demonstrated aspect ratio of 10:1 at a 300 µm layer**.
`h_sub,min` = **300 µm** is therefore adopted for non-embedded architectures. Going thinner
would be an extrapolation *below* the source's own demonstrated geometry, which is the safe
direction to refuse.

## 3. Result

| h_sub (mm) | Z1 EMBEDDED | Z2 BACKSIDE | Z4 POWER DIE | Z5 2.5D |
|---|---|---|---|---|
| 0.20 | no | no | no | no |
| **0.30** | no | **yes** | **yes** | **yes** |
| 0.50 | no | yes | yes | yes |
| 0.80 | no | yes | yes | yes |
| 1.00 | no | yes | yes | yes |
| 1.20 | no | yes | yes | yes |
| **1.30** | **yes** | yes | yes | yes |
| 1.50 | yes | yes | yes | yes |
| 2.00 | yes | yes | yes | yes |

The non-embedded architectures reach **0.30 mm against the embedded 1.276 mm** — a **4.3×
wider** thickness range, and it includes the region the corrected electrical model prefers.

## 4. Does moving the HVR out of the substrate restore thin-substrate designs?

**Yes geometrically, and it matters less electrically than expected.**

| architecture | best realizable point | P_elec | vs Z1 |
|---|---|---|---|
| Z1 EMBEDDED | h = 1.30 mm (its floor) | **126.090 W** | — |
| Z4 POWER DIE | h = 0.30 mm | 126.120 W | +0.030 W |
| Z2 BACKSIDE | h = 0.30 mm | 127.778 W | +1.688 W |
| Z5 2.5D LATERAL | h = 0.30 mm | 893.547 W | +767 W |

Z1 remains marginally best **because its embedded cell shortens the via field**: at
`h_sub` = 1.30 mm and `t_cell` = 1.226 mm the TSVs are only 74 µm long. Z4 gets to 0.30 mm but
must run its 48 V rail through the full 300 µm, and the two effects nearly cancel — a 30 mW
difference on a 126 W budget, which is 0.024 %.

So the honest answer to Sec. 5's question is: **moving the HVR out of the substrate does
restore thin substrates, but thin substrates are not worth much electrically here.** What they
buy is a different mechanical stack, and that is where the architectures actually separate
(Sec. 16).

## 5. Other realizability constraints, checked

| constraint | Z1 | Z2 | Z4 | Z5 |
|---|---|---|---|---|
| component stack fits the substrate | **binding** | n/a | n/a | n/a |
| TSV aspect ratio ≤ source-demonstrated 10:1 | satisfied (74 µm at d = 30 µm) | binding at 300 µm | binding at 300 µm | binding at 300 µm |
| total package thickness | 1.30 mm sub + die | 0.30 sub + 1.23 converter below | 0.30 sub + 1.23 power die above + die | 0.30 sub + interposer |
| converter in the die-to-cooler thermal path | no | no | **YES** | no |
| converter competes for a cooling surface | no | **YES** (board side) | no | no |

Z4's 1.23 mm power die sits between the substrate and a 1 kW compute die. That is a
realizability question about the *thermal* path rather than the geometric one, and Sec. 6
takes it up.
