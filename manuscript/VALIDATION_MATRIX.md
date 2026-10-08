# VALIDATION MATRIX

Every entry is an independent check that produced a number. Entries that did not produce a
number are listed in the second table and are not presented as validation anywhere in the
manuscript.

## Checks that produced a quantitative result

| # | Quantity | Production model | Independent reference | Case / geometry | Metric | Error | Status |
|---|---|---|---|---|---|---|---|
| 1 | RDL plane resistance and IR drop | sheet PDE on a 121–201 node grid | MOOSE, 300×300 finite-element mesh | three VR placements: distributed, edge-biased, asymmetric, 49 sources | dissipated power / IR drop | 0.45 / 1.10 / 0.58 % on power; 0.90–2.19 % on drop | ACCEPTED, 3/3 |
| 2 | Interconnect transition resistance | analytic series + spreading | MOOSE, 3-D conduction | five transition geometries (via-to-pad, pad-to-plane) | ΔR | 0.25–0.73 % | ACCEPTED, 5/5 |
| 3 | 3-D DC conduction, uniform conductor | conservative finite-volume, harmonic-mean faces | closed form ρL/A | copper bar, 4 mesh levels | R | exact at every level | ACCEPTED |
| 4 | 3-D DC conduction, spreading | same | closed form ρ/(4a) | disc source on a half-space | R | +0.9 % at 6 cells per radius | ACCEPTED |
| 5 | Physical via-chain resistance | analytic series of segments | conservative finite-volume, 5 mesh levels | microvia–land–microvia–land–microvia over 120 µm | R | 3-D is 1.16× the series value; land spreading, converged to 0.13 % | ACCEPTED as a correction |
| 6 | TSV single-via DC resistance | geometry-derived | independent re-implementation | 30 µm via, 300 µm span | R | exact | ACCEPTED |
| 7 | TSV AC ratio at 1 MHz | analytic skin-depth model | Bessel-function solution | 15 µm-radius copper via | R_ac/R_dc | δ/r = 4.41, ratio 1.0001 | ACCEPTED |
| 8 | Effective k_z, all layers | Voigt rule on the homogenised layer | explicit-geometry representative volume element | every homogenised layer | k_z | within 1 % | ACCEPTED |
| 9 | Effective k_xy, bump layers | Maxwell–Garnett | explicit-geometry RVE | bump/underfill field | k_xy | within 1.5 % | ACCEPTED |
| 10 | Effective k_xy, TSV arrays | explicit-geometry RVE adopted | Maxwell–Garnett; earlier lumped model | 30 µm / 60 µm via array | k_xy | Maxwell 11–39 % high; the earlier model 19–74 % low | RVE ADOPTED, both closed forms REJECTED |
| 11 | Unit-cell periodicity | 1×1 periodic cell | 2×2 periodic cell | homogenisation RVE | k, E | 0.000 % | ACCEPTED |
| 12 | Cooling, fluid side | analytic energy balance | closed form ṁ c_p ΔT | 27 g/s, 223 channels | coolant ΔT | exact | ACCEPTED |
| 13 | Cooling, solid side | fin efficiency + Shah–London Nu | MOOSE with explicitly meshed fins | production channel geometry | R_conv | 3.78 % | ACCEPTED |
| 14 | Cooling, solid side, short thick fins | same | MOOSE, explicit fins | off-design fin aspect ratio | R_conv | 10.11 % | REJECTED, outside the adopted geometry envelope |
| 15 | Converter loss decomposition | per-term closed form | upstream aggregate p_cond, p_sw | frozen N3K3K_A2 design | Σ terms − aggregate | machine precision; the ledger refuses to total otherwise | ACCEPTED |
| 16 | Spatial heat deposition | per-layer volumetric source | electrical loss total | full package mesh | Σ q‴V − P_elec | < 1×10⁻⁶ relative, guarded | ACCEPTED |
| 17 | Package thermal field | in-house conduction solver | MOOSE, full 3-D | 1 kW package, two substrate thicknesses | T_max ordering | ordering preserved | ACCEPTED (ordering) |
| 18 | Accumulated inelastic strain identity | CalculiX PEEQ output | creep-only material experiment, no plastic card | corner joint | PEEQ / eq(ε_in) | 1.0000 | ACCEPTED |
| 19 | Inelastic energy route | solver mechanical strain | independent integration route | corner joint | dissipated energy | 0.79–1.56 %; 16–21× cleaner on the isochoric test | ACCEPTED |
| 20 | Local response mesh convergence | C3D8 joint submodel | mesh refinement, 3 genuine levels | 4×5 → 6×8 solder mesh | ΔPEEQ per cycle | 1.9 % between the two finest levels | ACCEPTED |
| 21 | Local response cycle stabilisation | *VISCO, four cycles | cycle-to-cycle change | corner joint | Δ per cycle | 15.9 → 1.9 → 0.7 %, below the 5 % criterion by cycle 4 | ACCEPTED |
| 22 | E–T fixed point | Picard iteration on layer temperature | successive-iterate difference | both architectures | ΔT between iterations | converged below 0.25 K in 3 iterations | ACCEPTED |
| 23 | Fluid coupling | inner iteration on coolant temperature | successive-iterate difference | production cooler | ΔT_fluid | below 0.02 K | ACCEPTED |
| 24 | Global warpage mesh convergence | C3D8I package model | four graded mesh levels | full package | die warpage P–V | 0.50 % | ACCEPTED |
| 25 | Local submodel integration tolerance | *VISCO, CETOL 5e-2 | published Phase-0I architecture case at the same tolerance | corner joint | Δε_in per stabilised cycle | 0.0000 % against the published value | ACCEPTED |
| 26 | Local response cycle stabilisation, final pair | *VISCO, four cycles | cycle-to-cycle change on the frozen R3C pair | corner joint | Δε_in per cycle | 0.04 % (Z1), 0.06 % (Z2) | ACCEPTED |
| 27 | Local metric agreement, final pair | same solves | three independent local metrics | corner joint | ratio Z1/Z2 | 1.2260 strain, 1.2257 range, 1.1658 work — same ordering | ACCEPTED |

## Attempted, and not used as validation

| Quantity | Tool | Outcome | How it is reported |
|---|---|---|---|
| Package thermal field against conjugate CFD | ANSYS Icepak | the conjugate run did not produce a physically admissible field and was discarded | the manuscript states that conjugate CFD validation has **not** been completed; no Icepak number appears anywhere |
| TSV loop AC resistance | ANSYS HFSS, AEDT 2026 R1 batch | geometry, lumped port and boundaries were built and verified, but the adaptive full-wave solve of a 15 µm copper via with solve-inside did not converge within the allotted budget | the frequency dependence is reported from the analytic skin-depth model checked against the Bessel solution (row 7); **no HFSS result is claimed** |
| Full-wave electromagnetic extraction | Palace | not part of the validated chain | not mentioned in the manuscript |

## Reading the matrix

Rows 1–7 establish the electrical path from the redistribution plane down to a single via
transition. Rows 8–11 establish the homogenisation used by the thermal and mechanical
models, and record two closed forms that were tested and rejected in favour of an
explicit-geometry RVE. Rows 12–14 bound the cooling model and state the geometry envelope
in which it is accepted. Rows 15–16 are conservation checks that fail the run rather than
warn. Rows 17–27 establish the mechanical chain and the convergence of both the fixed
point and the local metric.

The two omissions that matter are stated in the manuscript rather than left to inference: a
conjugate CFD validation of the cooled package has not been completed, and no full-wave
confirmation of the via AC resistance was obtained.
