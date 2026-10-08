# PHASE 0M-R2 SECTION 8 --- RDL PRODUCTION THERMAL AUDIT

## What the production model was using

The `interface` layer sits directly between the compute die and the substrate. Every watt
the package removes crosses it. It was modelled as **isotropic underfill, k = 0.70 W/mK**.

## What its own sourced geometry gives

The layer is a microbump field in underfill: r = 5 um, pitch 20 um, height 10 um, solder
inclusions. Homogenising that geometry with the method Phase 0M-R validated gives

| | k_x | k_y | k_z | anisotropy | bound check |
|---|---|---|---|---|---|
| derived tensor | 0.8910 | 0.8910 | **11.7390** | 13.2x | Voigt 0.55 %, Maxwell 0.61 % |
| production, before | 0.70 | 0.70 | 0.70 | 1.0x | --- |

The production value was **16.8x too resistive through thickness**, in the one layer
every watt must cross. This is a different quantity from the Phase-0M-R RDL result: that
one was about the in-plane anisotropy of a redistribution stack, and it moved the Z1/Z2
ratio by at most 0.11 %. This is the bump layer in the primary heat path.

## Measured effect on the frozen architectures

| architecture | interface model | T_max | die warpage | corner driver |
|---|---|---|---|---|
| Z1_EMBEDDED | isotropic_0p70 | 125.51 C | 44.503 um | 4.9803 um |
| Z1_EMBEDDED | anisotropic_derived | 118.80 C | 41.726 um | 4.6450 um |
| Z2_BACKSIDE | isotropic_0p70 | 134.23 C | 41.593 um | 4.1660 um |
| Z2_BACKSIDE | anisotropic_derived | 127.06 C | 39.031 um | 3.8896 um |

| quantity | isotropic | anisotropic | change |
|---|---|---|---|
| Z1 peak temperature | 125.51 C | 118.80 C | **-6.71 K** |
| Z2 peak temperature | 134.23 C | 127.06 C | **-7.17 K** |
| Z1 corner driver | 4.9803 um | 4.6450 um | -6.73 % |
| Z2 corner driver | 4.1660 um | 3.8896 um | -6.63 % |
| **Z1/Z2 driver ratio** | **1.1955** | **1.1942** | **-0.105 %** |

## Decision: PROMOTED to the production default

The tensor is derived from the layer's own sourced geometry by a method already validated
against the Voigt and Maxwell-Garnett bounds to under 1 %, and it moves peak temperature
by about 7 K. Both conditions the brief sets for promotion are met, so it is now the
production default. `PHASE0MR2_INTERFACE_KORTHO=iso` recovers the retired behaviour for
comparison.

**It changes no ordering.** The effect is almost exactly common mode: the ratio moves
-0.105 %. The promotion matters for absolute temperature and for nothing else, and
that is how it is reported.
