# Phase 0J Sec. 0 — Baseline recorded before any Phase-0J change

| item | value |
|---|---|
| verification suite | **75 / 75 PASS, 0 FAIL, 0 SKIP** |
| PDF | `PDF VERIFIED`, 90 pages, 5.34 MB, 46 figures all embedded |
| `ETM_DVPD_FULL_TECHNICAL_REPORT.md` | md5 `6d62354c8d7dada6262c46c5e9f32e99` |
| `ETM_DVPD_FULL_TECHNICAL_REPORT.pdf` | md5 `73685baf04a98cf633d85751a32cf6ef` |
| `CURRENT_SCIENTIFIC_STATUS.yaml` | md5 `11cc19e4dcc7c8d32fec67c0a45f6bb3` |
| current phase / verdict | 0I-R — PHASE-0I METRIC VALID AFTER REDEFINITION |
| defects logged | 29, 30, 31, 32, 33, 34, 35, 36 |
| G2 | NOT_TESTED |
| optimiser built / recommended | false / false |

## Network access — re-probed, not assumed

Phase 0I recorded that publisher access was uneven and that both candidate SAC305 life-law
sources returned HTTP 403. **The environment has changed.** Probed at the start of Phase 0J:

| endpoint | result |
|---|---|
| `api.crossref.org` | **HTTP 200** |
| `api.openalex.org` | **HTTP 200** |
| `api.semanticscholar.org` | HTTP 429 (rate-limited, reachable) |
| `doi.org` resolver | reachable |

The Phase-0I blocker on life-law acquisition is therefore worth re-testing rather than
inherited. This is the premise of Phase 0J.

## The simulated cycle, read out of the deck rather than assumed

Recovered from `scripts/phase0i/run_zcompare.py` and a generated
`results/phase0i/zjoint/*.inp`:

| property | value |
|---|---|
| T_min (`T_OFF`) | **25.0 °C** |
| T_max (`t_hot`, architecture-dependent) | **81.10 – 83.21 °C** |
| ΔT | **56.1 – 58.2 K** |
| T_mean | **53.1 – 54.1 °C** |
| half-cycle duration (`DWELL`) | 300 s |
| period | **600 s = 10 min** |
| cycles simulated | 4, stabilised by cycle 4 |

**The waveform has NO dwell.** `write_inp` emits `*TEMPERATURE` with **no `AMPLITUDE=STEP`**,
and Phase 0I-R Sec. 4 established that CalculiX then **ramps temperature linearly across the
step**. The 300 s named `DWELL` in the driver is therefore a 300 s linear *ramp*, not a hold.
The applied waveform is a **symmetric triangle**: 25 → 82.9 °C over 300 s (≈ 11.6 K/min), then
back, with **zero hold at either extreme**.

This is recorded here because Sec. 15 forbids assuming one simulated cycle equals one
experimental fatigue cycle, and dwell time is the dominant creep-damage variable in solder
thermal-cycling fatigue. It is audited in `cycle_compatibility_audit.md`.
