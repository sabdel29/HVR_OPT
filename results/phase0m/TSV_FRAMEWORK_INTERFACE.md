# PHASE 0M PART 5 --- THE PRE-EXISTING TSV ELECTROTHERMAL FRAMEWORK

## Found. Not reimplemented.

| field | value |
|---|---|
| path | `/home/beams0/MGHARIB/Model/TSVs_Framework_MultiGND_new_3_HSPICE.py` |
| sha256 | `eaf21b1f1adc1b678e930bb56201c42b...` |
| size | 43377 bytes |
| mtime | 2025-11-09 |
| version string | **none in the file** --- the sha256 above is the version handle |
| entry point | module-level functions; `main()` is `__name__`-guarded, so import is safe |
| SPICE backend | `/local/synopsys/hspice/W-2024.09-SP2-2/hspice/bin/hspice` |
| HFSS reference | `/home/beams0/MGHARIB/tessera-master` |
| HFSS error stats | `/home/beams0/MGHARIB/tessera-master/error_stats_global.csv` |
| ML surrogate | `/home/beams0/MGHARIB/Model/tsv_surrogate_v3.pt` --- **NOT USED**, see below |

## What it contains

* **DC + skin resistance** --- `Z_in(r, f)`, the Bessel-function internal impedance
  `Z = (k/2 pi r sigma) J0(kr)/J1(kr)`, `k = sqrt(2 j pi f mu sigma)`.
* **Self and mutual partial inductance** --- via-to-via and through the depleted substrate.
* **Capacitance / conductance** --- MOS via capacitance with a depletion-thickness solve.
* **Multi-conductor S-parameters** --- an HSPICE netlist per frequency, N ports.
* **Anisotropic thermal homogenization** --- `thermal_conductivity()` returns
  `(k_x, k_y, k_z, rho c_p)` for a TSV ARRAY, which is exactly the quantity Parts 20 and 21
  need and which this project has never had.

## Interface used by Phase 0M

`scripts/phase0m/tsv_framework.py` wraps it. The framework is written for signal integrity
(per-unit-length outputs, micrometre locations, `(N, M)` array counts); the wrapper converts
to the power-delivery quantities and, importantly, **cross-checks rather than trusts**.

## Cross-check against the independent Phase-0M model

| quantity | framework | Phase-0M `interconnect.py` | agreement |
|---|---|---|---|
| `R_dc` of one TSV, r = 15 um, h = 300 um | 7.3175 mOhm | 7.3175 mOhm | **exact** |
| June-2026 Table III quoted value | -- | 7.1 mOhm | +3.1 % (shape/liner convention) |
| skin ratio at 1 MHz | 1.0001 | -- | `delta/r` = 4.41 |
| skin ratio at 1 GHz | 3.8517 | -- | `delta/r` = 0.14 |
| `k_z`, full 60 um-pitch field | 178.18 W/m.K | 178.18 W/m.K | **exact** |
| `k_xy`, same field | 87.84 W/m.K | 158.3 W/m.K (Maxwell-Garnett) | **80 % apart** |

The last row is the important one. The two models are not two implementations of one theory:
the framework's transverse model puts the oxide liner **in series** with the copper, so all
transverse heat must cross a 1.4 W/m.K barrier; the Maxwell-Garnett form treats the lined via
as an inclusion that heat can flow **around**. Neither is obviously right, so Part 21 decides
it by explicit-geometry finite elements on a unit cell rather than by preference.

## Loop inductance --- the quantity Part 13 needs

| pitch | `L_loop` per P/G pair | 8 pairs, uncoupled | 8 pairs, coupled (k = 0.25) |
|---|---|---|---|
| 30 um | 0.0832 nH | 0.0104 nH | 0.0104 nH |
| 60 um | 0.1664 nH | 0.0208 nH | 0.0572 nH |
| 120 um | 0.2495 nH | 0.0312 nH | 0.1040 nH |

Mutual coupling matters: eight parallel P/G pairs give 2.9x less inductance reduction than
the uncoupled 8x, so an inductance budget built by dividing by the via count is optimistic by
about a factor of three.

## What is deliberately NOT used

The trained surrogate `tsv_surrogate_v3.pt` is not used. It was trained on a
signal-integrity corpus (S-parameters of multi-conductor TSV bundles at GHz frequencies) and
has no established validity for a DC power via field at 1000 A. Using it here would be
exactly the transfer-without-evidence this project forbids elsewhere.

## Validation status of the framework itself

`/home/beams0/MGHARIB/tessera-master/error_stats_global.csv` records the framework against HFSS over 786 reflection and
insertion-loss samples and ~14 000 coupling samples:

| category | n | mean abs error | p95 | mean rel error |
|---|---|---|---|---|
| insertion loss | 786 | 0.00409 | 0.00743 | **0.42 %** |
| reflection | 786 | 0.0329 | 0.0643 | 73 % (small-magnitude denominators) |
| near-end coupling | 13866 | 0.00318 | 0.00774 | 90 % (ditto) |

The insertion-loss column is the one that bears on a power path, and 0.42 % mean relative
error against HFSS is a strong result. The reflection and coupling relative errors are large
only because the quantities are near zero; their ABSOLUTE errors are 0.003 to 0.03.
