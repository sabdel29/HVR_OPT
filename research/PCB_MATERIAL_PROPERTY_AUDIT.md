# PCB material property audit — IT-968G 18-layer 2.4 mm server board

Phase 0N-V. Replaces the unexplained isotropic board properties on the physical path.

## 1. Why the historical values had to go

`board.py` carried, with no stated basis:

| case | E | nu | CTE | k |
|---|---:|---:|---:|---:|
| `fr4_2p4mm` | 22 000 MPa | 0.20 | 16.0 ppm/K | 0.30 W/mK |
| `fr4_3p2mm` | 24 000 MPa | 0.20 | 15.0 ppm/K | 0.35 W/mK |

Two problems. First, **none of those numbers is sourced**. Second, the two cases differ in
*material* as well as thickness, so any 2.4 → 3.2 mm comparison built on them **confounds
geometric stiffness with a material change that has no demonstrated physical basis**.

Measured against the actual laminate, all three 2.4 mm values are wrong in direction:

- E = 22 GPa **exceeds the laminate's own 15 GPa** and implies about 23 % copper coverage;
- CTE = 16.0 ppm/K is **above every derived alpha_x** across the whole coverage sweep;
- k = 0.30 W/mK is **below even the pure-laminate lower bound** of 0.4 W/mK.

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
each: **Poisson ratio, thermal conductivity, E_z, any shear modulus, density.** These are
derived or bounded below and are never presented as IT-968G measurements.

## 3. SOURCE_BACKED — board construction (UGPCB 18-layer server PCB)

Thickness **2.4 mm ± 10 %**; **18 layers**; finished copper
`1/1/1/1/1/1/1/2/2/2/2/1/1/1/1/1/1/1 oz`
= **14 × 1 oz + 4 × 2 oz**; laminate **ITEQ IT968G**; min hole 0.20 mm;
min line/space 0.1/0.1 mm; ENIG; backdrilled; RTF foil. Board outline, impedance targets
and **copper artwork are not published**.

## 4. Copper constituent

The framework's own SOURCE_BACKED copper is used for consistency with the rest of the
model: E = 110 GPa, nu = 0.34, CTE = 16.66 ppm/K, k = 400 W/mK.

Cross-check against the C11000 figures supplied with the brief (E ≈ 117.0 GPa,
CTE ≈ 16.9 ppm/K, k ≈ 391.0 W/mK): they agree to within 6 %, 1.4 %
and 2.3 %. **copper.org could not be reached on 2026-10-23** — the CDA alloy database
returns a site-maintenance page — so the C11000 values are recorded as a corroborating
cross-check, **not** as a fetched source.

## 5. Copper thickness is known; copper COVERAGE is not

`t_Cu,full = 14 × 34.8 + 4 × 69.6 = 765.6 µm`, i.e. **31.90 %** of 2.4 mm.
The 34.8 µm/oz conversion is the standard finished-foil figure and is carried as
**BOUNDED**, not taken from the product page.

**This is an upper bound on copper volume, not the board's copper volume.** Signal layers
are patterned and the artwork is unpublished. Coverage is therefore **swept**:

| eta (areal coverage) | f_Cu vol | E_x GPa | E_y GPa | alpha_x | alpha_y | alpha_z | k_xy W/mK |
|---:|---:|---:|---:|---:|---:|---:|---|
| 0.00 | 0.000 | 15.0 | 14.0 | 12.00 | 14.00 | 45.00 | 0.40 – 4.50 |
| 0.25 | 0.080 | 22.6 | 21.7 | 13.81 | 15.08 | 42.74 | 32.27 – 36.04 |
| 0.50 | 0.159 | 30.2 | 29.3 | 14.71 | 15.59 | 40.48 | 64.14 – 67.58 |
| 0.75 | 0.239 | 37.7 | 37.0 | 15.25 | 15.89 | 38.22 | 96.00 – 99.12 |
| 1.00 | 0.319 | 45.3 | 44.6 | 15.61 | 16.09 | 35.96 | 127.87 – 130.66 |

eta is a **mathematical bounding grid**, not a claim about typical server boards.

## 6. DERIVED — homogenization rules

In-plane modulus and conductivity by Voigt (parallel), through-thickness by Reuss
(series), in-plane CTE modulus-weighted. Methodology references, none of which supply
IT-968G numbers:

- Fuchs *et al.*, Microelectron. Reliab. 52(11) 2012, `10.1016/j.microrel.2012.04.019`
- Atintoh *et al.*, Mater. Today Commun. 34 2023, `10.1016/j.mtcomm.2022.104968`
- Joo *et al.*, J. Micromech. Microeng. 26 2016, `10.1088/0960-1317/26/4/045006`
- Yoo *et al.*, Composites A 204 2026, `10.1016/j.compositesa.2026.109671`
- Thermal orthotropy, J. Mater. Res. Technol. 2026, `10.1016/j.jmrt.2026.01.011` — k_xy ≈ 3.4–4.5 vs k_z ≈ 0.35–0.38 W/mK **for a different FR4**, a bound only
- Multilayer thermal homogenization, Solid-State Electron. 103 2015, `10.1016/j.sse.2014.09.004`

**These papers were cited from the DOIs supplied with the brief and were not fetched in
full during this phase.** They are used for method, not for numbers.

## 7. OPEN / BOUNDED

| quantity | treatment |
|---|---|
| E_z of the laminate | **OPEN**; bracketed at 3.75–9.0 GPa pending a source |
| G_xy, G_xz, G_yz | **OPEN** — absent from the datasheet, not uniquely derivable from E_warp/E_fill |
| nu_xy, nu_xz, nu_yz | **OPEN**; Isola 370HR gives nu ≈ 0.177/0.171 for a *different* high-Tg FR4, a bound only |
| k_lam,xy / k_lam,z | **BOUNDED** 0.4–4.5 / 0.35–0.4 W/mK |
| copper areal coverage eta | **BOUNDED**, swept 0–1 |
| 1 oz → 34.8 µm | **BOUNDED** standard conversion |

Isola 370HR is **never** substituted for a missing IT-968G property.

## 8. Temperature gate

IT-968G states **MOT = 130 °C** and **Tg = 175 °C**. After the physical electrothermal
solve, `T_PCB,max` must be reported against both. If it exceeds 130 °C the board is
operating outside the manufacturer's stated maximum and the pre-Tg property set must be
re-examined. **That solve has not been run**, so no verdict exists.

## 9. Controlled thickness study

`it968g_2p4mm` and `it968g_3p2mm` share **one identical material tensor** and differ only
in thickness, so a 2.4 → 3.2 mm comparison isolates geometric stiffness (Case **T-only**).
The historical `fr4_*` pair is retained for reproducibility and **must not be used for the
physical comparison**. Case **T-stack** — rehomogenizing at constant copper for a thicker
dielectric — is **not implemented**.

## 10. Status

The board material model is built and wired into two board cases. **No ETM solve has been
run with it**, so no mechanical or thermal consequence of the change is known yet.
