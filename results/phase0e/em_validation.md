# Phase-0E — Electromagnetic Validation

## 1. Solver availability (changed since Phase 0D-R)

The ANSYS licence server was restarted by the site administrator on 2026-09-06 and is now
reachable: `1055@pinback.xray.aps.anl.gov`, `lmgrd` + `ansyslmd` up, features issued.

| feature | issued | checkout tested | used here |
|---|---|---|---|
| `elec_solve_hfss` | 1 | **can be checked out** | **yes — EM-1** |
| `elec_solve_icepak` | 1 | can be checked out | yes — thermal (`thermal_validation.md`) |
| `electronics_desktop` | 2 | can be checked out | yes |
| `elec_solve_level1/level2` | 2 / 2 | can be checked out | yes (with HFSS) |
| **`elec_solve_q3d`** | **0** | **`UNSUPPORTED ... No such feature exists (-5,346)`** | **NOT AVAILABLE** |

Q3D Extractor — the natural tool for DC/AC resistance extraction — is **not licensed on this
server**. The evidence is a licence-manager record, not an inference:

```
14:41:23 (ansyslmd) UNSUPPORTED: "elec_solve_q3d" (PORT_AT_HOST_PLUS)
                    mgharib@pinback.xray.aps.anl.gov [3324693]
                    (No such feature exists. (-5,346))
```

Per the Phase-0E brief, DC conduction is therefore validated with a dedicated conduction FE
(MOOSE, `multilayer_rdl_validation.*`) and HFSS is used **only inside its valid regime**.

## 2. A full-wave solver must not be used at 286 kHz — demonstrated, not assumed

The first attempt extracted the series impedance of a two-port P/G TSV field as `Z11 - Z12`.
At 286 kHz the structure is ~3x10^-9 wavelengths long and HFSS returned

```
re(Z11) = -42 157 748.0377  ohm     re(Z12) = -42 157 748.0379  ohm
```

so the series resistance is the difference of two numbers agreeing in their first eleven
digits. That is textbook low-frequency breakdown of a full-wave formulation, and the result
was discarded rather than reported.

A second attempt with the far end **shorted** (one port, `Z11` *is* the loop impedance, no
cancellation) initially appeared to show `R ~ f` with `L` spanning 0.014-4.6 nH against an
analytic 0.166 nH. That turned out to be a **parsing defect on our side**, not solver
behaviour: AEDT wrote the exported columns as `im(Z)` *before* `re(Z)`, reversing the order of
the expression list handed to it, and a positional parse transposed R and X. Columns are now
matched by header name. This is recorded because it is exactly the kind of error that would
have produced a confident, wrong validation.

## 3. EM-1 — power/ground TSV loop, shorted one-port

Structure: VDD and GND copper TSVs (d = 30 um, h = 300 um, 60 um apart, June-2026 Table III
geometry), split landing pads, shorted at the far end, driven by one lumped port. The **return
path is inside the model**, because the compact model's quantity is `R_loop`, not `R_single`.
Copper is solved inside (`solve_inside = True`); with the default surface-impedance boundary
HFSS cannot represent a DC current distribution at all.

### R(f), L(f) — one VDD/GND pair

| f (MHz) | R (mΩ) | R/R(1 MHz) | L (nH) | δ/r |
|---:|---:|---:|---:|---:|
| 1.00 | 29.0505 | 1.0000 | 0.2250 | 4.37 |
| 2.37 | 29.0586 | 1.0003 | 0.2250 | 2.84 |
| 5.62 | 29.1041 | 1.0018 | 0.2249 | 1.84 |
| 13.34 | 29.3532 | 1.0104 | 0.2245 | 1.20 |
| 31.62 | 30.5806 | 1.0527 | 0.2224 | 0.78 |
| 74.99 | 35.0358 | 1.2060 | 0.2161 | 0.51 |
| 177.83 | 45.3928 | 1.5625 | 0.2061 | 0.33 |
| 421.70 | 62.3458 | 2.1461 | 0.1973 | 0.21 |
| 1000.00 | 90.7968 | 3.1255 | 0.1910 | 0.14 |

### Two VDD/GND pairs

| f (MHz) | R (mΩ) | R/R(1 MHz) | L (nH) | δ/r |
|---:|---:|---:|---:|---:|
| 1.00 | 20.8096 | 1.0000 | 0.1428 | 4.37 |
| 3.16 | 20.8230 | 1.0006 | 0.1427 | 2.46 |
| 10.00 | 20.9542 | 1.0069 | 0.1424 | 1.38 |
| 31.62 | 22.0463 | 1.0594 | 0.1402 | 0.78 |
| 100.00 | 26.9617 | 1.2956 | 0.1328 | 0.44 |
| 316.23 | 38.3777 | 1.8442 | 0.1242 | 0.25 |
| 1000.00 | 60.8720 | 2.9252 | 0.1185 | 0.14 |

## 4. What this validates

**(a) No AC correction at the switching frequency — verified rather than assumed.**
Skin depth equals the via radius at

    f_x = rho / (pi mu0 r^2) = 19.1 MHz          (r = 15 um)

At f_sw = 0.286 MHz, δ/r = 8.18. HFSS shows R varying by **0.18 %** between 1 and 5.6 MHz
(one pair) and **0.064 %** between 1 and 10 MHz (two pairs), then rising as the crossover is
passed — 3.1x and 2.9x respectively by 1 GHz. The DC model is the correct model at f_sw, and
the crossover that would invalidate it is two orders of magnitude away. **The compact model
needs no frequency-dependent term.**

**(b) Loop inductance is physical.** 0.225 nH (one pair) against an analytic two-wire loop
value of 0.166 nH plus the shorting-bar and pad loop area; 0.143 nH for two pairs, close to
the expected halving. `L` falls ~15 % from 1 MHz to 1 GHz as internal inductance is expelled —
the correct qualitative behaviour.

**(c) A 1-D series resistance UNDERSTATES a real connection.** Against a 1-D sum of the same
geometry (2 vias + shorting bar + 2 pad runs), HFSS gives

| geometry | R_1D (mΩ) | R_HFSS at 1 MHz (mΩ) | ratio |
|---|---:|---:|---:|
| 1 P/G pair | 21.91 | 29.05 | **1.326** |
| 2 P/G pairs | 10.62 | 20.81 | **1.960** |

The excess is geometric current crowding where a 30 µm via meets a wider pad and turns into
the bar. **The ratio is fixture-dependent (1.33-1.96), so it is carried as an uncertainty band,
not as a calibrated constant.** This directly supports the Phase-0E brief's warning in Sec. 8:
bulk-cylinder resistance is not total connection resistance. Its effect on the system answer is
small only because the vertical tiers contribute <1 % of package distribution loss once the
sourced RDL stack is used (see `PHASE0E_PHYSICAL_STACK_CLOSURE.md`).

## 5. Not done, and why

* **EM-2/EM-3/EM-4 as separate HFSS models.** EM-3 (RDL source→load) is a DC conduction
  problem and is validated against MOOSE at higher fidelity than a full-wave solver could
  provide at 286 kHz; EM-2 and EM-4 are the same vertical/lateral transition physics as EM-1
  and would inherit the same low-frequency limitation. The crowding band from EM-1 is applied
  to all vertical tiers.
* **PALACE.** Installed and functional, but it is also a frequency-domain full-wave solver and
  would meet the identical low-frequency breakdown demonstrated in Sec. 2. No PALACE result is
  claimed.

## 6. Artifacts

`results/phase0e/aedt/em1_hfss_np1_corrected.json`, `em1_hfss_np2.json`,
`em1_np1_Zsweep.csv`, `em1_np2_Zsweep.csv`, project `em1_hfss_np*.aedt`.
Driver: `scripts/phase0e/em_hfss.py`.
