# Phase 0H Sec. 12 — Geometry closure: the GaN device heights are now sourced

## 1. What was open

Phase 0F built the realizability rule `t_cell + h_tsv ≤ h_sub`, `h_tsv ≥ 50 µm`, and used it
to prove the Phase-0B–0E thickness sweep unbuildable. But two of the three layer heights were
**OPEN** and carried as an invented envelope:

| layer | Phase-0F status | value used |
|---|---|---|
| inductor | **SOURCED** (upstream `INDUCTOR_LIBRARY`) | 500 µm |
| GaN device | **OPEN** — "not in the EPC product table, which gives `Package(mm)` as lateral dimensions only" | envelope 0 / 100 / 250 µm |
| MLCC / flying capacitor | **OPEN** — not in the capacitor library | envelope 0 / 100 / 250 µm |
| interlayer RDL | sourced, ECTC-2024 | 2 × 10 µm |

Phase 0F was right that the EPC *product table* has no heights. It does not follow that the
heights are unobtainable: the **manufacturer datasheets** carry them, and this environment can
reach `epc-co.com`.

## 2. What was retrieved

Both selected devices, from the manufacturer's own datasheet package-outline drawings:

| device | role | source | height |
|---|---|---|---|
| **EPC2212** | high-side | datasheet Side View, `EPC2212_datasheet.pdf` | **685 µm nominal, 815 µm max** |
| **EPC2090** | low-side | datasheet Side View, `EPC2090_datasheet.pdf` | **606 µm** = 518 ± 25 µm die + 50 µm Cu + 3 µm Ni + 35 µm solder cap |

Both are **6 to 8 times** the 100 µm Phase 0F assumed as nominal, and **2.4 to 3.3 times** its
pessimistic bound. The open envelope did not contain the true value.

The MLCC height could **not** be closed: Murata's part API returns HTTP 500 and its product
page returns an error to this environment. The capacitor library records only the part number
and lateral size (1206, 3.2 × 1.6 mm). **MLCC height remains OPEN**, with the same
0 / 100 / 250 µm envelope. It is not invented here.

## 3. Which devices sit in the substrate stack

This matters, and the reference system states it explicitly (June-2026 Sec. II, verbatim):

> "high-side GaN switches that are **flip-chipped to the RDL of the bottom substrate**, while
> **low-side switches (bottom layer), flying capacitors (middle layer), and inductors (top
> layer near the POLs) are embedded within the subsequent substrate power layers**."

So the substrate power-layer stack that the TSV field must traverse contains the **low-side
switch, the flying capacitor and the inductor**. The high-side device is attached to the RDL
*below* the substrate and does not consume substrate power-layer height.

The same passage endorses the coupling this project models:

> "the number of power layers is ultimately determined by the number and size of components in
> the chosen VR topology and constrained by the capabilities of advanced packaging
> technologies. This establishes a **direct link between VR topology selection and practical
> packaging limits**."

## 4. The revised realizability bound

`t_cell = h_inductor + h_LS_GaN + h_MLCC + 2 × h_interlayer_RDL`, and
`h_sub,min = t_cell + 50 µm`.

| MLCC (still OPEN) | t_cell | **h_sub,min** | realizable points of {0.80, 0.90, 1.00, 1.20, 1.50, 2.00} mm |
|---|---|---|---|
| 0 µm (optimistic) | 1126 µm | **1.176 mm** | 1.20, 1.50, 2.00 |
| 100 µm (nominal) | 1226 µm | **1.276 mm** | 1.50, 2.00 |
| 250 µm (pessimistic) | 1376 µm | **1.426 mm** | 1.50, 2.00 |

For comparison, Phase 0F's assumed nominal gave `t_cell = 720 µm` and `h_sub,min = 0.770 mm`.

**The minimum realizable substrate thickness rises from 0.770 mm to 1.176–1.426 mm.**

### Consequence: the corrected electrical optimum is not buildable

Phase 0G's corrected ARCH_B sweep is monotonically increasing with its optimum on the **thin
boundary at h_sub = 0.80 mm**, in 9 corners of 9. That point is now infeasible by **376–626 µm**
of substrate. So are 0.90 and 1.00 mm, and 1.20 mm survives only under the optimistic MLCC
bound.

This is the Phase-0F finding recurring one level up: an electrical optimum sitting on a
geometric boundary that had been placed with an unsourced number.

### What this does NOT change

* The **direction** of the electrical preference. ARCH_B is monotone over the whole swept
  range, so restricting the range moves the optimum to the smallest *realizable* thickness; it
  does not create an interior optimum.
* The **mechanical direction**. `S_h < 0` everywhere, so mechanically thicker remains better.
* The **thickness opposition** therefore survives — over a narrower feasible band.

## 5. Caveat that must travel with this result

Datasheet heights are **as supplied**. Die thinning before embedding is a normal advanced-
packaging step and would reduce the LS contribution substantially. The reference system does
not specify whether its devices are thinned, to what thickness, or with what yield. So:

* Using the as-supplied heights is the **conservative, source-backed** choice, and it is what
  is adopted.
* A thinned-die variant is **not modelled** because no source specifies it. If the reference
  system thins to, say, 100 µm, the Phase-0F bound would be approximately restored — and that
  possibility is exactly why this is reported as a *sourced bound with a named assumption*
  rather than as a proof that the design cannot exist.

## 6. Status change

| item | before | after |
|---|---|---|
| GaN device height | **OPEN**, invented envelope 0/100/250 µm | **SOURCED**: 685 µm (HS, EPC2212), 606 µm (LS, EPC2090), manufacturer datasheets |
| which devices are in the substrate stack | implicit | **SOURCED**: LS + caps + inductor embedded; HS flip-chipped to the RDL below |
| MLCC height | OPEN | **still OPEN** — Murata not retrievable; envelope retained |
| `h_sub,min` | 0.770 mm | **1.176–1.426 mm** |
| die thinning | not considered | **named assumption**: as-supplied heights used; thinning not specified by the source |

## Sources

1. EPC2212 eGaN FET datasheet, Efficient Power Conversion Corporation, Die Outline / Side View
   (`815 Max`, nominal `685`), retrieved from
   `https://epc-co.com/epc/Portals/0/epc/documents/datasheets/EPC2212_datasheet.pdf`.
2. EPC2090 eGaN FET datasheet, Side View (`606 µm` total = `518 ± 25 µm` die + `50 Cu + 3 µm
   Ni` + `35 µm solder`), retrieved from
   `https://epc-co.com/epc/Portals/0/epc/documents/datasheets/EPC2090_datasheet.pdf`.
3. June-2026 DVPD framework, Sec. II, on which components are embedded in the substrate power
   layers and which is flip-chipped to the RDL.
4. Non-retrieval: `murata.com` product API returns HTTP 500 and the product page an error page
   to this environment, recorded 2026-09-10. MLCC height remains OPEN.
