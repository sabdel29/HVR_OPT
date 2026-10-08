# PHASE 0M-R3 SECTION 6 --- Z1 (ARCH_Z1_EMBEDDED) ROUTING CLOSURE

Routing is a HARD GATE in the frozen realizability contract. A candidate whose losses are
calculable but whose conductors do not physically fit is NOT realizable, and Phase 0M's
finding that the output plane needed 8.6x the available tile width was reported only as a
loss number.

## The frozen candidate

| | |
|---|---|
| cells | 49 |
| current per cell | 20.408 A |
| inductor | `Shared_Core_UIC_250_nH`, 500.0 um, i_sat 23.00 A |
| high side / low side | EPC2014C / EPC2057 |
| switching frequency | 805.2 kHz |
| intra-VR via radius | **20.0 um** at 70.0 um pitch |

## Every route in the power path

| net | rail | geometry | I_dc | I_rms | required | available | ratio | fits |
|---|---|---|---|---|---|---|---|---|
| `vin_bus` | HV | lateral | 0.478 A | 0.478 A | 53.2 um width | tile side | **0.0166** | yes |
| `hs_to_cf` | SC | vertical | 0.000 A | 1.015 A | 183 vias | pad field | **0.0492** | yes |
| `hs_to_ls` | MID | vertical | 1.435 A | 1.435 A | 183 vias | pad field | **0.0710** | yes |
| `ls_to_L` | SW | vertical | 20.408 A | 20.408 A | 183 vias | pad field | **0.9344** | yes |
| `L_to_cout` | LV | lateral | 20.408 A | 20.408 A | 2267.6 um width | tile side | **0.7099** | yes |
| `vout_plane` | LV | lateral | 20.408 A | 20.408 A | 2267.6 um width | tile side | **0.7099** | yes |

The chain is continuous from package input to load: `vin_bus` (48 V in) ->
`hs_to_cf` (flying capacitors) -> `hs_to_ls` (the 16 V intermediate node) ->
`ls_to_L` (switch node to inductor) -> `L_to_cout` (output capacitor) ->
`vout_plane` (1 V to the package interconnect). No tier boundary is crossed without an
allocated via stack.

## What the repair changed, and why it was the only one needed

The binding net is **`ls_to_L`**, a vertical via stack carrying 20.408 A. At the
Phase-0M geometry it needed 1.236x the vias its pad provides.

Layers do not fix this: adding metal layers widens traces and adds no vias. Cells do not
fix it either -- splitting into more cells divides the current and the pad area together,
so the ratio is invariant. What does fix it is the via geometry, because the required
count goes as 1/r^2 while the available count goes as 1/p^2, and the framework's own
pitch rule `p = max(2r + s_min, 2r(1+koz))` with the SOURCE_BACKED `s_min = 30 um` makes
p grow more slowly than r:

| r | p | (p/r)^2 | ratio |
|---|---|---|---|
| 15 um | 60 um | 16.00 | 1.236 |
| **20 um** | **70 um** | **12.25** | **0.934** |
| 25 um | 80 um | 10.24 | 0.791 |

20 um is inside the sourced range `design_variables.tsv.radius_m = {lo 2.5, nominal 15,
hi 50} um`, so no new process is required. It is the smallest option in the enumeration
that clears the gate.

**Nothing else changed.** Same load, same package, same devices, same inductor, same cell
count, same substrate TSV geometry, same cooling, same RDL stack.
