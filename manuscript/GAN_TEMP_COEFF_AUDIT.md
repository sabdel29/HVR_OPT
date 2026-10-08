# alpha_GaN AUDIT --- PROVENANCE AND SENSITIVITY

Reproduce with `python scripts/phase0mr3c/gan_alpha_sensitivity.py`.

## 1. What the value is

    R_on(T) = R_on(25 C) * [1 + alpha_GaN * (T - 25)]        alpha_GaN = 7.5e-3 /K

## 2. Provenance --- traced, and it is not a sourced material constant

`scripts/phase0d/electrical.py:43` declares it in the source as

    ALPHA_GAN_RDSON = 7.5e-3    # 1/K     ASSUMPTION

and `results/phase0d/electrical_model_validation.md` records why:

> **The EPC product table in this repository carries no temperature data.** Its columns are
> PartNumber, VDSmax, VGSmax, MaxRDS(on)@5VGS, QG, QGS, QGD, QOSS, ID, PulsedID, Package,
> Stock, Price. alpha_GaN therefore cannot be sourced from repository data. 7.5e-3 /K gives
> ~1.75x at 125 C, consistent with the normalised R_DS(on) curves EPC publishes for eGaN
> parts.

**Verdict: adopted calibration coefficient, not a sourced constant.** The value was chosen so
that the normalised on-resistance rise reproduces the shape vendors publish for
enhancement-mode GaN; no numerical temperature coefficient for the two selected parts exists
in any source available to this work. The manuscript states it as such and cites no source
for the number itself, because there is none to cite. The device datasheets are cited for the
25 C on-resistance, which *is* sourced.

## 3. Sensitivity that already existed --- full electrical-thermal loop

`results/phase0d/robustness_0d.csv`, Phase-0D robustness study, alpha swept
0.005 / 0.0075 / 0.010 /K (+-33 %) through the **converged E-T loop**, so the temperature
feedback is included:

| candidate | dP_elec at -33 % | dP_elec at +33 % | dT_max at -33 % | dT_max at +33 % |
|---|---:|---:|---:|---:|
| small_fp | -6.85 % | +7.12 % | -1.15 K | +1.19 K |
| large_fp | -3.31 % | +3.34 % | -0.18 K | +0.19 K |
| et_best  | -2.81 % | +2.83 % | -0.12 K | +0.12 K |
| etm_alt  | -3.52 % | +3.56 % | -0.34 K | +0.35 K |

Peak temperature moves by at most 1.2 K over a +-33 % change.

## 4. Sensitivity added here --- the frozen R3C pair

Electrical only, evaluated at the frozen converged converter-layer temperature
(Z1 98.79 C, Z2 101.21 C). The temperature is held at its frozen value, so this is the
first-order electrical sensitivity; the E-T feedback is carried by section 3 above.

| case | alpha /K | P_converter (W) | dP |
|---|---:|---:|---:|
| Z1 | 0.0050 | 120.242 | -9.62 % |
| Z1 | 0.0060 | 125.359 | -5.77 % |
| Z1 | **0.0075** | **133.034** | reference |
| Z1 | 0.0090 | 140.710 | +5.77 % |
| Z1 | 0.0100 | 145.827 | +9.62 % |
| Z2 | 0.0050 | 121.186 | -9.83 % |
| Z2 | 0.0060 | 126.470 | -5.90 % |
| Z2 | **0.0075** | **134.397** | reference |
| Z2 | 0.0090 | 142.324 | +5.90 % |
| Z2 | 0.0100 | 147.609 | +9.83 % |

## 5. Effect on the Z1/Z2 ordering --- none

Z2 carries the higher converter loss at every value tested:

| alpha | P_conv(Z2) - P_conv(Z1) |
|---|---:|
| 0.0050 | +0.944 W |
| 0.0060 | +1.111 W |
| 0.0075 | +1.363 W |
| 0.0090 | +1.615 W |
| 0.0100 | +1.782 W |

**The ordering is preserved across the whole swept range**, and the separation widens with
alpha rather than closing. No mechanical replay was triggered: the largest peak-temperature
excursion in the full-loop Phase-0D sweep is 1.2 K, which does not approach the 8.14 K
separation between the two architectures.

## 6. What this does and does not license

* alpha_GaN is **electrically significant in magnitude**: a +-20 % change moves converter
  loss by about +-5.8 %, and the manuscript already identifies it as the input to which the
  electrical result is most sensitive.
* alpha_GaN is **not load-bearing for any ordering claim** reported in the paper.
* Absolute efficiency inferred from this work inherits the uncertainty of an adopted
  coefficient and should be read as such.
