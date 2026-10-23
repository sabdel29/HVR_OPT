# IT-968G board homogenization — method, numbers, and what is NOT modelled

Phase 0N-V companion to `PCB_MATERIAL_PROPERTY_AUDIT.md`. That document establishes the
*inputs* and their provenance. This one states the *rules*, the resulting tensor, and —
most importantly — the parts of the real board's anisotropy that the solver does not carry.

**Every number below is generated from `research/phase0nv/pcb_homogenization.json`
→ `nominal_tensor`, which is also what `scripts/phase0g/board.py` reads at import.**
There is one reduction and both consumers use it; a guard asserts they agree. An earlier
draft of this file picked `k_xy` out of the sweep independently and printed 67.58 W/mK
while the code used 65.86 — that is the failure mode this structure removes.

Generator: `scripts/phase0nv_pcb_homogenization.py`.

## 1. Mixing rules

18 copper layers interleaved with IT-968G prepreg/core, treated as a layered two-phase
medium with copper volume fraction `f = eta · t_Cu,full / t_board`:

| quantity | rule | reason |
|---|---|---|
| E_x, E_y | **Voigt** (parallel) | layers strain together in plane — iso-strain |
| E_z | **Reuss** (series) | layers stack in series through thickness — iso-stress |
| alpha_x, alpha_y | **modulus-weighted** | constrained in-plane expansion |
| alpha_z | volume-weighted | unconstrained through thickness |
| k_xy | **Voigt** | parallel heat paths |
| k_z | **Reuss** | series heat paths |

Classical lamination theory; methodology DOIs in the audit, Sec. 6.

## 2. The reduction

`nominal_tensor` = **nominal eta; arithmetic midpoint of each bounded bracket**. Bracketed quantities keep their bracket alongside the
value, so no consumer has to pretend the number is exact.

| component | value | basis |
|---|---:|---|
| E_x | **30152.5 MPa** | Voigt at eta = 0.50 |
| E_y | 29312.0 MPa | Voigt, fill direction |
| E_z | 7.49 GPa | midpoint of 4.43–10.54 GPa — **not used, see Sec. 5** |
| nu | 0.20 | **ASSUMPTION**, not an IT-968G property |
| alpha_x | **14.712 ppm/K** | modulus-weighted |
| alpha_y | 15.592 ppm/K | modulus-weighted |
| alpha_z | 40.48 ppm/K | volume-weighted, **pre-Tg only** |
| k_xy | **65.859 W/mK** | midpoint of 64.14–67.58 |
| k_z | **0.4461 W/mK** | midpoint of 0.416–0.476 |

Thermal anisotropy is **148×**. The retired `fr4_*` cases modelled the board as
thermally isotropic at 0.30 W/mK — below even the pure-laminate lower bound, and wrong by
more than two orders of magnitude in plane.

## 3. Coverage sensitivity

| eta | E_x GPa | alpha_x | alpha_z | k_xy | k_z |
|---:|---:|---:|---:|---:|---:|
| 0.00 |   15.0 | 12.00 | 45.00 |    2.45 | 0.375 |
| 0.25 |   22.6 | 13.81 | 42.74 |   34.15 | 0.407 |
| 0.50 |   30.2 | 14.71 | 40.48 |   65.86 | 0.446 |
| 0.75 |   37.7 | 15.25 | 38.22 |   97.56 | 0.493 |
| 1.00 |   45.3 | 15.61 | 35.96 |  129.27 | 0.550 |

E_x spans 15 → 45 GPa across the grid. **Copper coverage is the single largest
uncertainty in the board model**, larger than every laminate property uncertainty
combined, and it is unpublished for this board.

## 4. What IS wired

`k_ortho = [65.859, 65.859, 0.4461]` W/mK reaches CalculiX as a first-class card.
Verified on the built deck:

```
it968g_2p4mm   ['*CONDUCTIVITY, TYPE=ORTHO', '0.0658592,0.0658592,0.000446083']
fr4_1p6mm      ['*CONDUCTIVITY', '0.0003']              <- legacy path untouched
```

The legacy card is byte-identical to before, which is what keeps the frozen Phase-0M-R3C
replay valid; a guard asserts it.

In-plane spreading is the dominant board thermal mechanism, so this is the half of the
anisotropy that matters most for `T_PCB,max`, and it is now modelled rather than assumed
away.

## 5. What is NOT wired — elastic anisotropy

**The board is elastically ISOTROPIC at E_x.** Two independent blockers:

1. **The solver cannot express it.** `scripts/phase0b/etm/config.py` emits
   `*ELASTIC, TYPE=ORTHO` as `c11,c12,c11,c12,c12,c11,c44,c44,c44` — D1111 = D2222 =
   D3333 from a single constant. That is **cubic** symmetry. A laminate is transversely
   isotropic (5 constants, E_xy ≫ E_z); the card cannot represent it.
2. **Three of the five constants are OPEN anyway.** E_z, G_xz and nu_xz are absent from
   the datasheet and not derivable from E_warp/E_fill. A transversely-isotropic card would
   mean inventing them.

So E_z and G_xz are **unmodelled, not modelled-as-equal**, and the omission is not free.

**Magnitude.** The first-order shear-deformation correction to plate bending scales as
`(t/L)^2 · E_x/G_xz`. With L ≈ 30 mm and E_x/G_xz in 10–30:

| t | (t/L)^2 · E_x/G_xz |
|---|---|
| 2.4 mm | 0.064 – 0.192 |
| 3.2 mm | 0.114 – 0.341 |

That is a **10 %-order effect, not a negligible one**, and — the part that matters — it
**grows with thickness**. The 2.4 → 3.2 mm T-only study is therefore biased by an
unmodelled term that is larger for the thicker board, in the direction of making the thick
board look stiffer than it is. **Any warpage difference between the two thicknesses must
carry this caveat**, and a difference below ~10 % should not be treated as resolved by
this model. Status: **OPEN**.

## 6. Other limitations

- **alpha_z is pre-Tg (40 ppm/K).** Above Tg = 175 °C the datasheet gives 260 ppm/K, a
  5.8× jump. The model has no Tg transition, so it is valid only while T < 175 °C
  everywhere — which the ET solve must confirm, and **has not been run**.
- **Symmetric-laminate assumption.** CLT gives no bend–stretch coupling (B = 0) only for a
  symmetric stack. The UGPCB schedule (14 × 1 oz + 4 × 2 oz) is *consistent* with symmetry
  but the layer order is unpublished; an asymmetric stack would produce intrinsic warpage
  this model cannot show. Status: **OPEN**.
- **No cure/lamination residual stress.** The stress-free temperature is the solver's
  global reference, not a measured laminate value.
- **nu = 0.20 is carried from the legacy cases.** Isola 370HR's 0.171–0.177 is a different
  laminate and bounds it only.

## 7. Status

Material model built, thermal tensor wired, elastic anisotropy documented as OPEN with its
magnitude estimated. **No ETM solve has been run on this board model**, so no thermal or
mechanical consequence of replacing the old properties is known.
