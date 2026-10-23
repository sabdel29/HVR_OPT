# IT-968G board homogenization — method, numbers, and what is NOT modelled

Phase 0N-V companion to `PCB_MATERIAL_PROPERTY_AUDIT.md`. That document establishes the
*inputs* and their provenance. This one states the *rules*, the resulting tensor, and the
parts of the real board the solver does not carry.

**The board-level numbers below are conditional derived estimates at eta = 0.50, not
measured board properties.** See the audit, Sec. 5.

**Every number is generated from `research/phase0nv/pcb_homogenization.json`
→ `nominal_tensor`, which `scripts/phase0g/board.py` also reads at import.** One
reduction, three consumers, guards asserting they agree. An earlier draft picked `k_xy`
out of the sweep independently and printed 67.58 W/mK while the code used 65.86 — that is
the failure mode this structure removes.

Generator: `scripts/phase0nv_pcb_homogenization.py`.

## 1. Mixing rules

18 copper layers interleaved with IT-968G prepreg/core, as a layered two-phase medium with
copper volume fraction `f = eta · t_Cu,full / t_board`:

| quantity | rule | reason |
|---|---|---|
| E_x, E_y | **Voigt** (parallel) | layers strain together in plane — iso-strain |
| E_z | **Reuss** (series) | layers stack in series through thickness — iso-stress |
| alpha_x, alpha_y | **modulus-weighted** | constrained in-plane expansion |
| alpha_z | volume-weighted | unconstrained through thickness |
| k_xy | **Voigt** | parallel heat paths |
| k_z | **Reuss** | series heat paths |

## 2. The reduction

`nominal_tensor` = **nominal eta; arithmetic midpoint of each bounded bracket**. Bracketed quantities keep their bracket, stored
**[lower, upper]**; the reduction helper raises if that ordering is violated.

| component | value at eta = 0.50 | basis |
|---|---:|---|
| E_x | **30152.5 MPa** | DERIVED, conditional on eta |
| E_y | 29312.0 MPa | DERIVED, conditional on eta |
| E_z | 7.49 GPa | midpoint of [4.43, 10.54] GPa — **not used, Sec. 5** |
| nu | 0.20 | **ASSUMPTION**, not an IT-968G property |
| alpha_x | **14.712 ppm/K** | DERIVED, conditional on eta |
| alpha_y | 15.592 ppm/K | DERIVED, conditional on eta |
| alpha_z | 40.48 ppm/K | DERIVED, **pre-Tg only** |
| k_xy | **65.859 W/mK** | midpoint of [64.14, 67.58] |
| k_z | **0.4461 W/mK** | midpoint of [0.416, 0.476] |

## 3. The model is thermally orthotropic, mechanically isotropic

The correct name for what is implemented is a
**thermally orthotropic, mechanically isotropic reduced model**. It must not be called
"an orthotropic board model" — the elastic half is isotropic.

| | modelled | discarded |
|---|---|---|
| thermal | k_xy ≠ k_z, ratio 148× | — |
| elastic | E = E_x isotropic | E_x ≠ E_y, **and** everything through-thickness |

**Known in-plane anisotropy that the isotropic elastic card discards**, at eta = 0.50:

- E_x = 30.15 GPa vs **E_y = 29.31 GPa** (2.9 % difference)
- alpha_x = 14.71 ppm/K vs **alpha_y = 15.59 ppm/K** (6.0 % difference)

Both descend from the laminate's own measured warp/fill anisotropy (15 vs 14 GPa,
12 vs 14 ppm/K), so this is **sourced anisotropy being thrown away**, not unknown
anisotropy. The alpha difference is the larger of the two and runs opposite in sign to the
modulus difference. Status: **OPEN**.

## 4. Coverage sensitivity — E and CTE

| eta | E_x GPa | E_y GPa | alpha_x | alpha_y | alpha_z |
|---:|---:|---:|---:|---:|---:|
| 0.00 |   15.0 |   14.0 | 12.00 | 14.00 | 45.00 |
| 0.25 |   22.6 |   21.7 | 13.81 | 15.08 | 42.74 |
| 0.50 |   30.2 |   29.3 | 14.71 | 15.59 | 40.48 |
| 0.75 |   37.7 |   37.0 | 15.25 | 15.89 | 38.22 |
| 1.00 |   45.3 |   44.6 | 15.61 | 16.09 | 35.96 |

E_x spans 15 → 45 GPa. **Copper coverage is the single largest uncertainty in
the board model**, larger than every laminate property uncertainty combined, and it is
unpublished for this board. eta = 0 and 1 are mathematical bounds; **{0.25, 0.50, 0.75}
is the retained sensitivity set for every final result.**

## 5. What IS wired — thermal

`k_ortho = [65.859, 65.859, 0.4461]` W/mK reaches CalculiX as a first-class card:

```
it968g_2p4mm   ['*CONDUCTIVITY, TYPE=ORTHO', '0.0658592,0.0658592,0.000446083']
fr4_1p6mm      ['*CONDUCTIVITY', '0.0003']              <- legacy path untouched
```

The legacy card is byte-identical to before, which keeps the frozen Phase-0M-R3C replay
valid; a guard asserts it.

**65.86 W/mK is a nominal PCB-H0 homogenized estimate at 50 % areal copper
coverage.** It is not "the IT-968G board conductivity" and it is not measured. Across the
sweep:

| eta | k_xy W/mK | k_z W/mK | ratio |
|---:|---:|---:|---:|
| 0.00 |     2.45 | 0.375 |      7 |
| 0.25 |    34.15 | 0.407 |     84 |
| 0.50 |    65.86 | 0.446 |    148 |
| 0.75 |    97.56 | 0.493 |    198 |
| 1.00 |   129.27 | 0.550 |    235 |

k_xy varies by more than an order of magnitude across the grid, so any thermal conclusion
that depends on in-plane spreading must be reported against eta.

## 6. What is NOT wired — elastic anisotropy

Two independent blockers:

1. **The emitter cannot express it.** `scripts/phase0b/etm/config.py` writes
   `*ELASTIC, TYPE=ORTHO` as `c11,c12,c11,c12,c12,c11,c44,c44,c44` — D1111 = D2222 =
   D3333 from one constant, i.e. **cubic** symmetry. A laminate is orthotropic (9
   constants); the card as emitted cannot represent it. Whether CalculiX itself is the
   limitation is addressed in Sec. 8.
2. **Most of the constants are OPEN anyway.** E_z, G_xy, G_xz, G_yz, nu_xy, nu_xz, nu_yz
   are absent from the datasheet and not derivable from E_warp/E_fill. Writing the card
   would mean inventing them.

So E_z and the shear moduli are **unmodelled, not modelled-as-equal**.

## 7. Transverse shear — a scaling argument, not an error bar

The first-order plate scaling `(t/L)^2 · E_x/G_xz`, with L ≈ 30 mm and E_x/G_xz in 10–30:

| t | (t/L)^2 · E_x/G_xz |
|---|---|
| 2.4 mm | 0.064 – 0.192 |
| 3.2 mm | 0.114 – 0.341 |

**A first-order plate scaling suggests transverse-shear effects can be O(10 %) for this
geometry**, and the group **grows with thickness**, so it is larger for the 3.2 mm board.

**This is a scaling argument, not a validated uncertainty bound, and it is not an error
bar.** It does not license a "±10 %" on any reported number. Its only legitimate use is
caution: a 2.4 vs 3.2 mm difference below this scale should not be treated as decisive
without a model that actually carries transverse shear. Status: **OPEN**.

## 8. Board reduction level: PCB-H0 vs PCB-H1

**PCB-H0** — one 2.4 mm homogenized orthotropic board, `k_x = k_y = k_xy`, `k_z`. This is
the reduced-order baseline and is what the cases above implement.

**PCB-H1** — a reduced multilayer board preserving the alternating Cu-rich / dielectric
structure from the 18-layer schedule, without meshing individual traces.

The cited multilayer-PCB thermal literature warns that a single homogeneous
effective-conductivity board can be insufficient for 3-D spreading, so H0 must be
*validated*, not assumed. Criterion and results: Sec. 9 of the implementation audit once
H1 is run. **Until then no thermal claim rests on H0 alone.**

## 9. Other limitations

- **alpha_z is pre-Tg (40 ppm/K).** Above Tg = 175 °C the datasheet gives 260 ppm/K.
  The model has no Tg transition, so it is valid only while T < 175 °C everywhere — which
  the ET solve must confirm, and **has not been run**.
- **Symmetric-laminate assumption.** CLT gives no bend–stretch coupling (B = 0) only for a
  symmetric stack. The UGPCB schedule is *consistent* with symmetry but the layer order is
  unpublished; an asymmetric stack would produce intrinsic warpage this model cannot show.
  Status: **OPEN**.
- **No cure/lamination residual stress.**
- **nu = 0.20 is carried from the legacy cases**, an ASSUMPTION.

## 10. Status

Material model built, thermal tensor wired, elastic anisotropy documented as OPEN with its
scale estimated. **No ETM solve has been run on this board model.**
