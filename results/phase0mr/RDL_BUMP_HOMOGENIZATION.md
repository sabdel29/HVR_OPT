# PHASE 0M-R SECTION 8 --- RDL AND BUMP EFFECTIVE PROPERTIES FROM THE ACTUAL STACK

## The Phase-0M number must not be assigned to the production package

Phase 0M measured **153x to 276x anisotropy** on a SINGLE-DIRECTION LINE CELL and said so.
Assigning it to the production stack would be wrong, because a power distribution stack is
not one line layer. Four organisations, all on explicit unit cells:

| organisation | t_diel | f_Cu | k_x | k_y | k_z | in-plane x/y | max/min |
|---|---|---|---|---|---|---|---|
| LINES_1D | 2.0 um | 0.7246 | 279.08 | 1.98 | 2.48 | **141.129** | 141.1 |
| LINES_1D | 5.0 um | 0.6061 | 233.47 | 1.76 | 1.24 | **132.545** | 188.8 |
| LINES_1D | 10.0 um | 0.4762 | 183.52 | 1.47 | 0.80 | **124.705** | 229.0 |
| ORTHOGONAL | 2.0 um | 0.7246 | 140.59 | 140.59 | 2.46 | **1.000** | 57.2 |
| ORTHOGONAL | 5.0 um | 0.6061 | 117.63 | 117.63 | 1.24 | **1.000** | 95.2 |
| ORTHOGONAL | 10.0 um | 0.4762 | 92.49 | 92.49 | 0.80 | **1.000** | 115.4 |
| MESH | 2.0 um | 0.8454 | 311.68 | 311.68 | 2.64 | **1.000** | 118.0 |
| MESH | 5.0 um | 0.7071 | 260.74 | 260.74 | 1.27 | **1.000** | 204.6 |
| MESH | 10.0 um | 0.5556 | 204.94 | 204.94 | 0.81 | **1.000** | 251.8 |
| PLANE | 2.0 um | 0.8696 | 334.83 | 334.83 | 2.67 | **1.000** | 125.5 |
| PLANE | 5.0 um | 0.7273 | 280.10 | 280.10 | 1.28 | **1.000** | 218.8 |
| PLANE | 10.0 um | 0.5714 | 220.15 | 220.15 | 0.82 | **1.000** | 269.9 |

**The in-plane anisotropy collapses to exactly 1.00 for every realistic organisation.**
Orthogonal routing, a mesh and a solid plane are all in-plane isotropic; only the
single-direction stack is not. Phase 0M's 153x is real for the cell it describes and is not
a property of the production stack.

**But a larger anisotropy appears, in the other direction and in the opposite sense.**
Through-thickness against in-plane runs **57x to 270x**, because the inter-layer dielectric
sits in series through the stack while the copper is in parallel across it. The RDL is an
excellent lateral spreader (92 to 335 W/m.K) and a poor vertical conductor (0.8 to 2.7).

That matters more than the original finding, because the production model gives this layer
**one isotropic value of 0.7 W/m.K**. It is roughly right through thickness by accident and
**two to three orders of magnitude too low in plane**, so the model is missing a major
lateral heat-spreading path.

## Mechanical tensor

| organisation | t_diel | E_x | E_z | CTE_x | CTE_z | in-plane isotropic |
|---|---|---|---|---|---|---|
| LINES_1D | 2.0 um | 90.3 GPa | 50.1 GPa | 17.79 | 17.79 ppm/K | False |
| LINES_1D | 5.0 um | 78.8 GPa | 40.2 GPa | 18.30 | 18.30 ppm/K | False |
| LINES_1D | 10.0 um | 66.2 GPa | 33.0 GPa | 19.06 | 19.06 ppm/K | False |
| ORTHOGONAL | 2.0 um | 66.5 GPa | 50.1 GPa | 20.01 | 17.79 ppm/K | True |
| ORTHOGONAL | 5.0 um | 57.3 GPa | 40.2 GPa | 20.67 | 18.30 ppm/K | True |
| ORTHOGONAL | 10.0 um | 48.4 GPa | 33.0 GPa | 21.60 | 19.06 ppm/K | True |
| MESH | 2.0 um | 78.8 GPa | 66.9 GPa | 19.46 | 17.39 ppm/K | True |
| MESH | 5.0 um | 65.0 GPa | 48.3 GPa | 20.10 | 17.86 ppm/K | True |
| MESH | 10.0 um | 53.7 GPa | 37.1 GPa | 21.00 | 18.56 ppm/K | True |
| PLANE | 2.0 um | 104.3 GPa | 71.7 GPa | 17.32 | 17.32 ppm/K | True |
| PLANE | 5.0 um | 90.5 GPa | 50.4 GPa | 17.78 | 17.78 ppm/K | True |
| PLANE | 10.0 um | 75.4 GPa | 38.0 GPa | 18.48 | 18.48 ppm/K | True |

The production model gives that layer **E = 8 GPa**. The real stack is **48 to 104 GPa in
plane** --- six to thirteen times stiffer, directly under the die.

## Bump and interface layers --- NOT the TSV formula

A bump layer is low-conductivity solder in a low-conductivity matrix, a completely different
contrast from copper in silicon, so the TSV transverse model is not reused. Computed
separately on its own cells:

| layer | f | k_z | k_xy | anisotropy | Voigt error on k_z | Maxwell error on k_xy |
|---|---|---|---|---|---|---|
| microbump_underfill | 0.1963 | 11.739 | 0.891 | 13.2x | 0.55 % | 0.61 % |
| C4_underfill | 0.3491 | 20.403 | 1.242 | 16.4x | 0.57 % | 1.49 % |
| BGA_mold | 0.1963 | 11.538 | 0.522 | 22.1x | 0.56 % | 0.63 % |
| microbump_dense | 0.5454 | 31.432 | 2.080 | 15.1x | 0.22 % | 5.04 % |

Both closed forms are ACCEPTED for bump layers (under 1.5 %), with one CONDITIONAL case: at
the densest microbump pitch Maxwell-Garnett drifts to 5.0 %, which is where the dilute
assumption starts to fail at `f = 0.55`.
