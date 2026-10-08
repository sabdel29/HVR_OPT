# PHASE 0M PART 10 --- ROUTING SCOPE AUDIT

## The three levels

| level | what it covers | present in the framework before Phase 0M? |
|---|---|---|
| **LEVEL 1 --- intra-converter** | input pads, GaN switches, flying capacitors, intermediate rail, buck switches, inductors, output capacitors, output pads, and the metal between them | **NO. Absent entirely.** |
| **LEVEL 2 --- VR to package** | VR terminal to TSV field, RDL network, bump array, die terminal | YES --- the vertical tiers in `zpower.evaluate_z` |
| **LEVEL 3 --- package to POL** | VR outputs to load regions across the die | YES --- `stack.rdl_network_solve`, a multilayer resistive sheet |

## Every current loss term, and which level it belongs to

| loss term | where it is computed | level |
|---|---|---|
| `hs.R_DS_ON`, `ls.R_DS_ON` | upstream `compute_total_loss` | **inside the converter model, not routing** |
| inductor DCR `R_L_ESR` | upstream `compute_total_loss` | **inside the converter model** |
| capacitor `R_C_ESR` | upstream `compute_total_loss` | **inside the converter model** |
| hard-switching, gate-drive, C_OSS | upstream `compute_total_loss` | **inside the converter model** |
| `P_bga`, `P_c4`, `P_tsv`, `P_microbump` | `zpower._tier_loss_system` | LEVEL 2 |
| `P_rdl` | `stack.rdl_network_solve` | LEVEL 3 |
| metal between converter components | **nowhere** | **LEVEL 1, MISSING** |

**No double counting.** The upstream converter model contains every device and passive
parasitic and no metallization at all. Phase 0M adds only the metallization.

## The Level-1 model

Per-phase STACKED COLUMNS, not a planar grid. The first version of this model laid the
components side by side inside each layer and routed laterally between them; it returned
61 % of the load in intra-VR routing, because it forced a 6.8 A phase current down a 0.8 mm
lateral trace that does not exist in the real device. In the embedded architecture the
low-side switch, its flying capacitor and its inductor occupy DIFFERENT power layers at the
SAME footprint, so the phase connection is a via stack, not a trace.

The footprint arithmetic confirms the column reading: the compiled design reports
`total_area = 5.61 mm^2 = 3 x 1.87 mm^2 = K x (one high-side footprint)`, and the tile is
2.3685 mm square = 5.61 mm^2.

## Net-by-net, at the reference stack (10 um Cu, 1 layer, J = 1e8 A/m^2, area-optimal vias)

| net | rail | geometry | length | width | I_rms | R | P per VR | feasible |
|---|---|---|---|---|---|---|---|---|
| `vin_to_hs0` | HV | lateral | 1.342 mm | 159.5 um | 0.159 A | 17.9623 mOhm | 0.00046 W | True |
| `vin_to_hs1` | HV | lateral | 2.132 mm | 159.5 um | 0.159 A | 28.5283 mOhm | 0.00073 W | True |
| `vin_to_hs2` | HV | lateral | 2.921 mm | 159.5 um | 0.159 A | 39.0944 mOhm | 0.00099 W | True |
| `hs0_to_cf` | SC | lateral | 0.197 mm | 1014.9 um | 1.015 A | 0.4151 mOhm | 0.00043 W | True |
| `hs1_to_cf` | SC | lateral | 0.592 mm | 1014.9 um | 1.015 A | 1.2452 mOhm | 0.00128 W | True |
| `hs2_to_cf` | SC | lateral | 0.197 mm | 1014.9 um | 1.015 A | 0.4151 mOhm | 0.00043 W | True |
| `hs0_to_ls0` | MID | vertical | 0.645 mm | via field um | 0.478 A | 0.1400 mOhm | 0.00003 W | True |
| `hs1_to_ls1` | MID | vertical | 0.645 mm | via field um | 0.478 A | 0.1400 mOhm | 0.00003 W | True |
| `hs2_to_ls2` | MID | vertical | 0.645 mm | via field um | 0.478 A | 0.1400 mOhm | 0.00003 W | True |
| `ls0_to_L0` | SW | vertical | 0.823 mm | via field um | 6.803 A | 0.2440 mOhm | 0.01129 W | True |
| `ls1_to_L1` | SW | vertical | 0.823 mm | via field um | 6.803 A | 0.2440 mOhm | 0.01129 W | True |
| `ls2_to_L2` | SW | vertical | 0.823 mm | via field um | 6.803 A | 0.2440 mOhm | 0.01129 W | True |
| `L0_to_vout` | LV | vertical | 0.250 mm | via field um | 6.803 A | 0.0741 mOhm | 0.00343 W | True |
| `L1_to_vout` | LV | vertical | 0.250 mm | via field um | 6.803 A | 0.0741 mOhm | 0.00343 W | True |
| `L2_to_vout` | LV | vertical | 0.250 mm | via field um | 6.803 A | 0.0741 mOhm | 0.00343 W | True |
| `vout_plane` | LV | lateral | 0.790 mm | 2368.5 um | 20.408 A | 0.7114 mOhm | 0.29630 W | False |

## How much loss intra-VR routing adds

| | per VR | system (49 cells) | of the 1 kW load | of the 125.3 W converter loss |
|---|---|---|---|---|
| reference stack | 0.3449 W | **16.90 W** | 1.69 % | 13.5 % |

Across every stack, current density and via policy examined, the Level-1 term spans
**4.06 to 39.31 W system-wide**, i.e. 0.41 % to 3.93 % of the load.

## The binding constraint is current density, not resistance

At the reference stack the VR output plane needs **8.6x the available tile width** to stay
inside the sourced copper current-density envelope. The fix is more copper --- 9 RDL layers,
or 86 um of thickness --- and the framework never noticed because it has no Level-1 routing
to check.

## Fidelity: how much is enough

| level | output-net loss per VR | comment |
|---|---|---|
| R1 obstacle-aware Manhattan | 0.29630 W | analytic, microseconds |
| R2 2-D resistive sheet, 1 layer(s), 10 um | 0.21592 W | finite terminal footprints |

R1 is **conservative by about 37 %** against R2 on the output net. For design exploration R1
is adequate and R2 should be used to calibrate it; R3 (the Part-8 3-D extraction) is needed
only for the transitions.

## Does it change architecture ranking?

the converter cell is identical across Z1, Z2 and Z4, so the intra-VR metallization is a common additive term; it moves every total by the same watts and the electrical ordering is unchanged

**Ordering changed: False.** The intra-VR term is
common-mode across Z1, Z2 and Z4 because the converter cell is the same compiled design in
all three. It adds 4.06 W to every
architecture's total and reorders nothing. Its second-order path --- more heat, higher
temperature, more thermal strain --- is
0.41 % of the load.
