# PHASE 0M PARTS 20-22 --- THERMAL HOMOGENIZATION AUDIT

## Predeclared acceptance, fixed before the RVEs were run

A homogenized tensor is **ACCEPTED** if it reproduces the explicit-geometry RVE within 10 %
on each axis, **CONDITIONAL** between 10 and 25 % with the error reported, and **REJECTED**
above 25 %. (`scripts/phase0m/homogenization.py`, `ACCEPT_PCT = 10.0`.)

## The unit cell is its own periodic cell

For a centred inclusion in a square cell, symmetry puts zero normal flux on every mid-plane,
so adiabatic side walls ARE the periodic boundary condition. Checked, not assumed:
a 1x1 cell and a 2x2 cell give **147.724** and
**147.724** W/m.K --- identical to
0.000 %.

## TSV + silicon + liner

| geometry | f_Cu | RVE k_z | RVE k_xy | Voigt k_z (err) | Maxwell k_xy (err) | existing framework k_xy (err) | k_z/k_xy |
|---|---|---|---|---|---|---|---|
| r_cu=15.0 t_ox=0.5 p=60.0 um | 0.1963 | **178.32** | **142.40** | 178.36 (0.02 %) | 158.43 (11.3 %) | 87.74 (38.4 %) | 1.252 |
| r_cu=15.0 t_ox=0.5 p=40.0 um | 0.4418 | **239.79** | **162.42** | 238.80 (0.41 %) | 204.09 (25.7 %) | 57.66 (64.5 %) | 1.476 |
| r_cu=5.0 t_ox=0.3 p=20.0 um | 0.1963 | **177.02** | **94.90** | 176.95 (0.04 %) | 158.66 (67.2 %) | 77.17 (18.7 %) | 1.865 |
| r_cu=25.0 t_ox=1.0 p=100.0 um | 0.1963 | **178.23** | **142.10** | 178.01 (0.12 %) | 158.49 (11.5 %) | 84.25 (40.7 %) | 1.254 |
| r_cu=15.0 t_ox=0.5 p=35.0 um | 0.5770 | **272.32** | **169.45** | 272.11 (0.07 %) | 236.01 (39.3 %) | 44.31 (73.9 %) | 1.607 |

Three findings:

1. **Along the vias, the rule of mixtures is essentially exact.** Voigt reproduces the RVE
   `k_z` to better than 0.5 % at every geometry. ACCEPTED.
2. **Across the vias, Maxwell-Garnett is CONDITIONAL and the pre-existing framework's
   transverse model is REJECTED at four of the five geometries and CONDITIONAL at the
   fifth --- never ACCEPTED.** Maxwell is 11 to 39 % high; the framework is 19 to 74 % LOW, and it gets worse as the array tightens, because it puts the oxide liner in SERIES
   with the copper so all transverse heat must cross a 1.4 W/m.K barrier. Heat can flow
   around the via; the series model does not let it.
3. **At fixed copper fraction, a SMALLER via is thermally worse in plane.** `r = 5 um` at
   `p = 20 um` and `r = 15 um` at `p = 60 um` have the same copper fraction (0.196) and the
   same `k_z`, but `k_xy` is 94.9 against 142.4 W/m.K
   --- because the liner fraction scales as `t_ox/r`. That is a coupled geometry-thermal
   lever nobody has priced.

## Bump and underfill layers

| layer | geometry | f | RVE k_z | RVE k_xy | Voigt k_z (err) | Maxwell k_xy (err) | k_z/k_xy |
|---|---|---|---|---|---|---|---|
| microbump_underfill | r=5.0 p=20.0 h=10.0 um | 0.1963 | **11.567** | **0.885** | 11.674 (0.93 %) | 0.886 (0.07 %) | 13.07 |
| C4_underfill | r=50.0 p=150.0 h=70.0 um | 0.3491 | **20.096** | **1.227** | 20.287 (0.95 %) | 1.223 (0.28 %) | 16.38 |
| BGA_mold | r=200.0 p=800.0 h=300.0 um | 0.1963 | **11.365** | **0.518** | 11.473 (0.95 %) | 0.518 (0.06 %) | 21.94 |

Bump layers are **13 to 22 times more conductive along z than in plane**, and both closed
forms are ACCEPTED there: Voigt for `k_z` to under 1 %, Maxwell for `k_xy` to under 0.5 %.
The contrast is larger than for TSVs and the inclusions are more dilute, which is exactly
where effective-medium theory is at its best.

## RDL and dielectric

| geometry | f_Cu | along the lines | across the lines | through the layer | anisotropy |
|---|---|---|---|---|---|
| t=10.0 W=10.0 S=2.0 um | 0.8333 | **320.89** | **2.090** | 320.89 | **153.5x** |
| t=10.0 W=2.0 S=2.0 um | 0.5000 | **192.68** | **0.699** | 192.67 | **275.5x** |
| t=5.0 W=10.0 S=2.0 um | 0.8333 | **320.89** | **2.090** | 320.89 | **153.5x** |

**The RDL is the most anisotropic layer in the package by two orders of magnitude** ---
153x to 276x between along-line and across-line conduction --- and the current framework
gives it a single isotropic conductivity. A caveat this audit must state itself: these cells
model parallel lines in ONE direction. A power PLANE at occupancy near 1, or an orthogonal
two-direction mesh, is much less anisotropic in plane. The ECTC-2024 stack is a TRACE stack
(W/S = 10/2), so for that stack the anisotropy is real.

## Part 22 --- what must NOT be homogenized

The local solder/current-crowding region keeps explicit geometry. Homogenizing it would
destroy exactly the gradients the reliability chain reads: the corner-joint shear, the
damage-weighted stress distribution, and the pad-to-trace constriction. Global/local
submodelling is retained: homogenized tensors in the package model, explicit geometry in the
joint and transition submodels.

## Literature seeds

The anisotropic-equivalent approach for TSV and bump arrays follows He Ma et al.,
*Microelectronics Reliability* 54 (2014), DOI 10.1016/j.microrel.2013.10.003, and
Chuanjun Nie et al., *Microelectronics Reliability* 137 (2022) 114790,
DOI 10.1016/j.microrel.2022.114790. Those papers motivate the form; the numbers here are
computed on this project's own geometry and are not taken from them.
