# PCB material property audit — IT-968G 18-layer 2.4 mm server board

Phase 0N-V. Replaces the unexplained isotropic board properties on the physical path.

**Nothing in this document is a measured whole-board property.** The constituent inputs
are sourced; the board-level numbers are *conditional derived estimates* at an assumed
copper coverage. Section 5 states which is which, and that distinction governs every
later use.

## 1. Why the historical values were replaced

`board.py` carried, with no stated basis:

| case | E | nu | CTE | k |
|---|---:|---:|---:|---:|
| `fr4_2p4mm` | 22 000 MPa | 0.20 | 16.0 ppm/K | 0.30 W/mK |
| `fr4_3p2mm` | 24 000 MPa | 0.20 | 15.0 ppm/K | 0.35 W/mK |

Two problems, and neither of them is "these numbers are impossible".

First, **none is sourced** — no laminate, no copper schedule, no measurement, no citation.
Second, the two cases differ in *material* as well as thickness, so any 2.4 → 3.2 mm
comparison built on them **confounds geometric stiffness with a material change that has
no stated basis**.

**The historical 22 GPa value was unsupported and was not tied to the actual
laminate/copper construction. It is not necessarily physically impossible.** A
copper-loaded PCB can legitimately be stiffer in plane than its bare laminate: this
model's own sweep passes through E_x ≈ 22.6 GPa at eta = 0.25. The objection is
provenance, not plausibility.

The same care applies to the other two. CTE = 16.0 ppm/K and k = 0.30 W/mK are
**unsupported, and inconsistent with the source-backed constituent model adopted here** —
0.30 W/mK sits below the pure-laminate lower bound used in this model, and 16.0 ppm/K is
above every alpha_x this model derives. That makes them incompatible with *this*
reconstruction; it is not a measurement that refutes them.

## 2. SOURCE_BACKED — ITEQ IT-968G, datasheet W-CTE-1002-55B

Fetched 2026-10-23 and read directly from the property table.

| property | value | direction | method | status |
|---|---|---|---|---|
| Young's modulus | **15 GPa** | warp | ASTM D3039 | SOURCE_BACKED |
| Young's modulus | **14 GPa** | fill | ASTM D3039 | SOURCE_BACKED |
| X/Y CTE, 40–125 °C | **12 / 14 ppm/K** | x / y | IPC **2.4.41** | SOURCE_BACKED (primary) |
| X/Y CTE, 40–125 °C | 11 / 12 ppm/K | x / y | IPC **2.4.24.5** | SOURCE_BACKED (method sensitivity) |
| Z CTE alpha-1 (pre-Tg) | **45 ppm/K** | z | IPC 2.4.24 | SOURCE_BACKED |
| Z CTE alpha-2 (post-Tg) | 260 ppm/K | z | IPC 2.4.24 | SOURCE_BACKED |
| Tg (TMA) | **175 °C** | — | IPC 2.4.24 | SOURCE_BACKED |
| Td (5 % W.L.) | 400 °C | — | IPC 2.4.24.6 | SOURCE_BACKED |
| **MOT** | **130 °C** | — | UL 746 | SOURCE_BACKED |
| Flexural strength | 415 / 355 N/mm² | length / cross | IPC 2.4.4 | SOURCE_BACKED |

**Explicitly NOT in the datasheet** — verified by searching the extracted text, zero hits
each: **Poisson ratio, thermal conductivity, E_z, any shear modulus, density.**

## 3. SOURCE_BACKED — board construction (UGPCB 18-layer server PCB)

Thickness **2.4 mm ± 10 %**; **18 layers**; **14 × 1 oz + 4 × 2 oz** finished copper;
laminate **ITEQ IT968G**; min hole 0.20 mm; min line/space 0.1/0.1 mm; ENIG; backdrilled;
RTF foil. Board outline, impedance targets and **copper artwork are not published**.

## 4. Copper constituent

The framework's own SOURCE_BACKED copper, for consistency with the rest of the model:
E = 110 GPa, nu = 0.34, CTE = 16.66 ppm/K, k = 400 W/mK. Cross-check against the C11000
figures supplied with the brief (117.0 GPa, 16.9 ppm/K, 391.0 W/mK): agreement within
6 %, 1.4 % and 2.3 %. **copper.org could not be reached on 2026-10-23**, so C11000 is a
corroborating cross-check, **not** a fetched source.

## 5. Status classification — what is sourced, derived, or assumed

This is the governing table for every number in the board model.

### SOURCE_BACKED (measured, cited)
IT-968G E_x / E_y; IT-968G X/Y CTE; IT-968G Z CTE; Tg; MOT; board thickness; 18-layer
count; copper weights per layer; copper constituent properties already in the framework.

### DERIVED (computed from the above by a stated rule)
The mixing-rule formulas themselves; effective E_x, E_y; effective CTE; effective thermal
conductivity.

### BOUNDED / ASSUMED (chosen, not known)
Copper areal coverage **eta**; laminate thermal conductivity; the E_z range; all shear
moduli; all Poisson ratios; the actual layer artwork and connectivity.

**Consequence.** Whole-board numbers such as `E_x = 30.15 GPa` and
`k_xy = 65.86 W/mK` are **conditional derived estimates at eta = 0.50**. They are not
measured board properties and must never be presented as "the IT-968G board modulus" or
"the IT-968G board conductivity". Every result that depends on them inherits the eta
condition.

## 6. Copper thickness is known; copper COVERAGE is not

`t_Cu,full = 14 × 34.8 + 4 × 69.6 = 765.6 µm`, i.e. **31.90 %** of 2.4 mm.
The 34.8 µm/oz conversion is the standard finished-foil figure, carried as **BOUNDED**.

**That is an upper bound on copper volume, not the board's copper volume.** Signal layers
are patterned and the artwork is unpublished, so coverage is **swept**:

| eta | f_Cu vol | E_x GPa | E_y GPa | alpha_x | alpha_y | alpha_z | k_xy | k_z |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.00 | 0.000 | 15.0 | 14.0 | 12.00 | 14.00 | 45.00 | 2.45 | 0.375 |
| 0.25 | 0.080 | 22.6 | 21.7 | 13.81 | 15.08 | 42.74 | 34.15 | 0.407 |
| 0.50 | 0.159 | 30.2 | 29.3 | 14.71 | 15.59 | 40.48 | 65.86 | 0.446 |
| 0.75 | 0.239 | 37.7 | 37.0 | 15.25 | 15.89 | 38.22 | 97.56 | 0.493 |
| 1.00 | 0.319 | 45.3 | 44.6 | 15.61 | 16.09 | 35.96 | 129.27 | 0.550 |

eta is a **mathematical bounding grid**, not a claim about typical server boards. eta = 0
and 1 are bounds only; **{0.25, 0.50, 0.75} is the retained physical sensitivity set** and
every final result must be reported across it (see Sec. 9).

## 7. DERIVED — homogenization rules

In-plane modulus and conductivity by Voigt (parallel), through-thickness by Reuss
(series), in-plane CTE modulus-weighted. Methodology references, none of which supply
IT-968G numbers:

- Fuchs *et al.*, Microelectron. Reliab. 52(11) 2012, `10.1016/j.microrel.2012.04.019`
- Atintoh *et al.*, Mater. Today Commun. 34 2023, `10.1016/j.mtcomm.2022.104968`
- Joo *et al.*, J. Micromech. Microeng. 26 2016, `10.1088/0960-1317/26/4/045006`
- Yoo *et al.*, Composites A 204 2026, `10.1016/j.compositesa.2026.109671`
- Thermal orthotropy, J. Mater. Res. Technol. 2026, `10.1016/j.jmrt.2026.01.011`
- Multilayer thermal homogenization, Solid-State Electron. 103 2015, `10.1016/j.sse.2014.09.004`

**Cited from the DOIs supplied with the brief; not fetched in full during this phase.**
Used for method, not for numbers.

## 8. OPEN / BOUNDED

| quantity | treatment |
|---|---|
| E_z of the laminate | **OPEN**; bracketed 3.75–9.0 GPa pending a source |
| G_xy, G_xz, G_yz | **OPEN** — absent from the datasheet, not derivable from E_warp/E_fill |
| nu_xy, nu_xz, nu_yz | **OPEN**; Isola 370HR's 0.177/0.171 is a *different* laminate, a bound only |
| k_lam,xy / k_lam,z | **BOUNDED** 0.4–4.5 / 0.35–0.4 W/mK |
| copper areal coverage eta | **BOUNDED**, swept; {0.25, 0.50, 0.75} retained for sensitivity |
| 1 oz → 34.8 µm | **BOUNDED** standard conversion |
| layer artwork / connectivity | **OPEN** — unpublished |

Isola 370HR is **never** substituted for a missing IT-968G property.

All brackets are stored **[lower, upper]**; `_mid()` raises if that is violated.

## 9. Retained sensitivity obligations

1. **Coverage.** Every final thermal and mechanical result is reported at
   eta = 0.25, 0.50, 0.75. If the Z1/Z2 ranking changes across eta, the manuscript must
   report that dependence rather than quoting the eta = 0.50 ranking.
2. **Board reduction.** PCB-H0 (one homogenized orthotropic board) is validated against
   PCB-H1 (reduced multilayer); see `PCB_IT968G_HOMOGENIZATION.md` Sec. 7.
3. **Thickness.** 2.4 vs 3.2 mm is a T-only study on an identical material tensor.

## 10. Temperature gate

IT-968G states **MOT = 130 °C** and **Tg = 175 °C**. After the physical electrothermal
solve, `T_PCB,max` must be reported against both. Exceeding 130 °C means the board
operates above the manufacturer-stated maximum operating temperature — **that is a
specification limit, not a sudden failure temperature**. Exceeding 175 °C would
additionally invalidate the pre-Tg alpha_z = 45 ppm/K used here. **That solve has not been
run**, so no verdict exists.

## 11. Status

The board material model is built and wired into two board cases. **No ETM solve has been
run with it**, so no mechanical or thermal consequence of the change is known yet.
