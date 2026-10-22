# Physically supported Z1 and Z2 package constructions

Phase 0N-R Sections 8–10. The question is not "what would make the figures plausible" but
"what construction does a source actually describe, and does it close with **our** selected
components?"

## 1. Literature access, updated

Phase 0N could read 3 of 9 sources in full. One more was located open-access in this pass:

| source | DOI | access |
|---|---|---|
| Krishnakumar 2026, design framework for VPD | `10.1109/TCPMT.2026.3724907` | **FULL** (arXiv 2606.28837) |
| Sriharini ECTC 2024, buck-derived VPD | `10.1109/ECTC51529.2024.00364` | **FULL** |
| ISCAS 2024, DVPD design considerations | `10.1109/ISCAS58744.2024.10558456` | **FULL** |
| **SOCC 2023, VPD for emerging packaging platforms** | `10.1109/SOCC58585.2023.10256973` | **FULL — newly obtained** (arXiv 2309.10141, confirmed open access via OpenAlex) |
| EV-PDN, >1 kW FC-BGA, >1 mm thick core | `10.1109/ECTC51687.2025.00176` | **NOT OA**, not reachable |
| ECTC 2024, 1 kW IVR CCM-DCM | `10.1109/ECTC51529.2024.00054` | not reachable |
| TPEL 2025, VPD architecture | `10.1109/TPEL.2025.3531414` | not reachable |
| TPEL 2025, vertically stacked dual-bus | `10.1109/TPEL.2025.3532833` | **NOT OA**, not reachable |
| TCPMT 2026, integrated VPD review | `10.1109/TCPMT.2026.3716987` | not reachable |

OpenAlex was queried for open-access copies of every unreachable DOI; only the SOCC paper
had one. **Five remain unread and nothing is inferred from their abstracts.**

## 2. The four VPD architectures of SOCC 2023, and where Z1/Z2 fall

Read from the paper (Fig. 4 caption and Sec. II):

| | construction | VR component location |
|---|---|---|
| **A0** | reference | 48 V→1 V conversion at PCB level |
| **A1** | single-step high-ratio | **on-interposer** power transistors, discrete caps and inductors **embedded in-interposer**; transistors distributed **along the die periphery** |
| **A2** | single-step high-ratio | power transistors, capacitors **and** inductors **all embedded in-interposer**; converters **below the centre of the die** |
| **A3** | multi-stage | embedded passives + an HV regulator with on-interposer transistors + an LV regulator **below the functional die, e.g. on a dedicated stacked die** (variants A3@12V, A3@6V) |

**Z1 maps onto A2**: all converter components embedded in the interposer/substrate below the
die. That is a real correspondence and it is the first literature classification this work
has for Z1.

**Z2 maps onto none of them.** A3's "below the functional die" means on a stacked die *above*
the interposer, not on the package-substrate **backside** facing the board. None of A0–A3
places converter components between the package substrate and the PCB. The one accessible
architecture taxonomy therefore **does not contain a Z2-like construction**.

The only textual support for Z2 remains one sentence in Krishnakumar 2026 — "when fabricated
as individual chiplets, VR components can be vertically stacked on the backside of a
substrate and interconnected through TSVs" — which gives **no dimensions, no BGA
relationship, no board interface and no cavity**. That is not enough to build from.

## 3. A physically closed Z1 candidate

Built **only** from what Krishnakumar 2026 describes, with layer thicknesses set by our
selected components:

> "high-side GaN switches ... flip-chipped to the RDL of the bottom substrate, while
> low-side switches (bottom layer), flying capacitors (middle layer), and inductors (top
> layer near the POLs) are embedded within the subsequent substrate power layers."

z = 0 at the bottom-substrate underside; EPC2014C 685 µm, EPC2057 **638 µm** (corrected).

| # | element | t (µm) | z0 → z1 | role | provenance |
|---:|---|---:|---|---|---|
| 1 | PCB | 1600 | −1600 → 0 | board | ASSUMPTION (FR-4 envelope) |
| 2 | BGA field | 300 | 0 → 300 | package-to-board attach, 48 V in / return | **sourced** (Table III: 400/300/800 µm) |
| 3 | **bottom substrate** | 300 | 300 → 600 | hosts the 48 V TSV field | **sourced** (Table III power-layer TSV h = 300 µm) |
| 4 | bottom-substrate RDL | 10 | 600 → 610 | the RDL the HS is flip-chipped to | **sourced** (ECTC-2024 10 µm) |
| 5 | **HS GaN (EPC2014C)** | 685 | 610 → 1295 | high side, flip-chipped | **sourced** (datasheet Side View) |
| 6 | interlayer RDL | 10 | 1295 → 1305 | PL1 interconnect | sourced |
| 7 | **LS GaN (EPC2057)** | 638 | 1305 → 1943 | low side, PL1 | **sourced** (datasheet, 518+120) |
| 8 | interlayer RDL | 10 | 1943 → 1953 | PL2 interconnect | sourced |
| 9 | **flying capacitors** | 100 | 1953 → 2053 | PL2 | **BOUNDED** (0/100/250 µm, OPEN) |
| 10 | interlayer RDL | 10 | 2053 → 2063 | PL3 interconnect | sourced |
| 11 | **inductors + output caps** | 500 | 2063 → 2563 | PL3, nearest the POLs | sourced (Rasheedi part) |
| 12 | output RDL | 10 | 2563 → 2573 | 1 V collection plane | sourced |
| 13 | microbumps + underfill | 10 | 2573 → 2583 | 1 V to die | sourced |
| 14 | compute die | 300 | 2583 → 2883 | load | sourced |
| 15 | TIM | 50 | 2883 → 2933 | cooling interface | design choice |

**This closes.** Total package above the board = **2933 µm**; the substrate assembly
(items 3–12) is **2273 µm**. Every component has a place, nothing intersects the BGA, and
the high-side device is inside the assembly rather than protruding into the ball gap.

**Supply and return.** 48 V enters through the BGA, rises through the bottom-substrate TSV
field (item 3) to the RDL (item 4) and into the HS devices. Conversion occurs across items
5–11. 1 V leaves the output RDL (item 12) through microbumps into the die. Return follows
the mirrored path: die → microbumps → output RDL ground plane → interlayer RDL grounds →
bottom-substrate TSV field → BGA → PCB. **Return vias are not yet separate geometry**; see
§5.

**How this differs from the frozen Z1.** The frozen model has ONE 1.30 mm substrate with a
1226 µm band and no high-side device. This candidate has a 300 µm bottom substrate plus a
stack of component-sized power layers totalling 2273 µm, and it *contains* the high side.
They are different packages, not refinements of each other.

**Where it departs from the source, and why.** The source's power layers are 300 µm each
(three of them, ≈900 µm implied). **Our components do not fit in 300 µm**: the low side is
638 µm and the inductor 500 µm. The layer thicknesses above are therefore set by the
components, not by the source. That is a documented departure, not an invention — but it
means the source's own 3 × 300 µm geometry is **incompatible with the selected device set**,
which is itself a finding.

## 4. Z2 — superseded by Z2-CUTOUT

> **CORRECTION (Phase 0N-R, second pass).** This section originally gave the Z2 backside
> cell as **1258 µm** and the shortfall as **958 µm**. Both were wrong. 1258 µm is the
> *embedded-cell* quantity, which structurally **excludes the 685 µm high-side device** —
> an exclusion justified only by Z1's bottom substrate, which Z2 does not have. Z2 must
> carry all four tiers: **1953 µm** with the corrected devices, and the no-cutout shortfall
> against a 300 µm ball is **1653 µm**, not 958 µm. The same error is in the frozen model
> itself, which gives Z2's `conv` layer 1226 µm and so understates its converter height by
> **695 µm**.

With that corrected, a land-side construction with a **PCB through-cutout** becomes
dimensionally plausible: the substrate underside to PCB backside distance is
300 + 1600 = **1900 µm**, and the 1963 µm stack (with its land-side attach RDL) ends only
**63 µm** proud of the board backside at nominal device heights.

A candidate is now developed in:

- `research/Z2_CUTOUT_SOURCE_AUDIT.md` — every source classified; the cutout is
  **patent-precedented (ARM US20260059645A1, Intel US20250233088A1), not demonstrated**,
  and **neither patent gives a single dimension**;
- `research/Z2_CUTOUT_GEOMETRY.md` — the stack, the closure arithmetic and the cutout size;
- `research/Z2_CUTOUT_BGA_POWER_RETURN.md` — BGA capacity, the power path and return;
- `research/Z2_CUTOUT_THERMOMECH_PLAN.md` — what the cutout does to stiffness and cooling.

**Z2 is still not closed.** At the EPC2014C maximum height the protrusion is 193 µm, a
backside heat sink would add more, the land-side attach and sidewall clearance are
unsourced, and return is still a loop factor rather than geometry. It is now a *specified*
gap rather than an unspecified one.

## 5. Supply and return in a closed model

The present electrical model accounts return as `R_loop = 2 × R_field` — a factor, not
geometry. A physically closed package needs supply vias, return vias, a ground plane in each
RDL, and a board return. For the Z1 candidate the defensible interim treatment is a
**homogenised bidirectional via field** that preserves copper volume and areal fraction: the
TSV field already carries both polarities in the loop resistance, so representing it as one
field with the full copper fraction keeps the mechanical effect (stiffness, CTE) correct even
though the two polarities are not individually resolved. **This must be stated wherever the
candidate is used, and it is not a substitute for explicit return geometry.**

## 6. Lateral representation

Both architectures must resolve the 49 cells laterally. Z1 already does (converter medium
only inside the 274.89 mm² of cell footprints, 30.5 % of 900 mm²). **Z2 does not** — it is a
full-area slab. Any closed Z2 must represent VR-cell regions, the non-VR region, the
board-attach regions and whatever fills the rest, separately.
