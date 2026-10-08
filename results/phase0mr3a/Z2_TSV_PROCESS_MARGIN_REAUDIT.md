# PHASE 0M-R3A SECTION 6 --- Z2 TSV DIAMETER RE-AUDIT

> **Phase 0M-R3 stated the direction backwards.** It wrote that a 34 um via costs
> "22.8 % MORE vias". Under fixed-current-density provisioning a larger via needs
> **22.8 % FEWER**. The magnitude was right; the sign and the framing as a cost were not.

## Which count?

"Via count" is ambiguous and the error hid inside the ambiguity. Four distinct quantities:

| quantity | meaning |
|---|---|
| `n_required` | vias needed to carry the rail at J_design: `ceil(I / (J * A_cu))` |
| `n_allocated` | vias the allocation policy actually places |
| `n_available` | vias the field footprint can hold at the legal pitch |
| total Cu area | `n_allocated * A_cu`, the conducting cross-section actually provided |

## The sweep

All at ARCH_Z2's span of 300 um, J_design = 1e+08 A/m2, liner 0.5 um,
pitch = max(d + 30, d), identical allocation policy and field footprint.

| d | pitch | AR | M_AR | modest bound | n_required | n_allocated | n_available | phi_Cu |
|---|---|---|---|---|---|---|---|---|
| 30 um | 60 um | 10.000 | 1.000 | **FAIL** | 15140 | 15140 | 69440 | 0.020002 |
| 32 um | 62 um | 9.375 | 1.067 | OK | 13250 | 13250 | 65032 | 0.020003 |
| 34 um | 64 um | 8.824 | 1.133 | OK | 11692 | 11692 | 61031 | 0.020002 |
| 36 um | 66 um | 8.333 | 1.200 | OK | 10394 | 10394 | 57388 | 0.020002 |

| quantity | 30 um | 34 um | change |
|---|---|---|---|
| n_required | 15140 | 11692 | **-22.8 %** |
| n_allocated | 15140 | 11692 | -22.8 % |
| n_available | 69440 | 61031 | -12.1 % |
| A_cu per via | 660.5 um2 | 855.3 um2 | +29.5 % |
| total Cu area | 10.0003 mm2 | 10.0002 mm2 | -0.00 % |
| phi_Cu | 0.020002 | 0.020002 | -0.001 % |
| R_field | 0.000640 mOhm | 0.000640 mOhm | +0.001 % |
| P_TSV | 1.2805 W | 1.2805 W | +0.001 % |
| k_z | 134.920 | 134.942 | +0.016 % |
| k_xy | 132.6379 | 132.6340 | -0.003 % |
| E_xy | 167182 MPa | 167222 MPa | +0.024 % |
| CTE_eff | 2.7996e-06 | 2.7997e-06 | +0.005 % |

`n_required` is verified against an independent hand calculation at every diameter:
`ceil(I / (J * pi * (d/2 - t_liner)^2))`. They agree exactly.

## Why the count falls

    n_required  ~  1 / A_cu  ~  1 / (d/2 - t_liner)^2

so `(14.5 / 16.5)^2 = 0.7723`, i.e. **22.8 % fewer**. The 22.8 % figure in the Phase-0M-R3
text is this number with its sign inverted and relabelled a cost.

## Why nothing else moves

`phi_Cu`, `R_field`, `P_TSV`, the thermal tensor, the modulus and the CTE change by well
under 0.1 %. That is the Phase-0M allocation law: under minimum-capability provisioning the
copper fraction is `I / (J_design * A_field)`, in which the via radius cancels identically.
A larger via means fewer vias and the same total copper. **The 34 um change is essentially
free in E/T/M terms** -- which was the correct conclusion in Phase 0M-R3, reached through
an incorrect statement about counts.

## Process margin

| d | AR | M_AR | under -2 % diameter, +2 % depth |
|---|---|---|---|
| 30 um | 10.000 | 1.000 | 10.408 -> **VIOLATES AR <= 10** |
| 32 um | 9.375 | 1.067 | 9.758 -> PASSES |
| 34 um | 8.824 | 1.133 | 9.184 -> PASSES |
| 36 um | 8.333 | 1.200 | 8.673 -> PASSES |

30 um fails the modest bound; 32 um and above pass. **32 um is the smallest diameter on
this grid with positive margin**, not 34 um -- Phase 0M-R3 swept 30/34/40/50/60 and never
evaluated 32.
