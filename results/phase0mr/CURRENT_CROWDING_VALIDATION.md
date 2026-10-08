# PHASE 0M-R SECTION 4 --- INDEPENDENT VALIDATION OF THE TRANSITION MODEL

## Predeclared acceptance, fixed before any cross-solver run

| class of case | ACCEPTED | CONDITIONAL | else |
|---|---|---|---|
| canonical bulk | <= 2 % | -- | REJECTED |
| realistic transition resistance | <= 5 % | <= 10 % | REJECTED |

If validation had failed, the transition model would have stayed OUT of production.

## Reference planes, stated once and imposed identically in both solvers

| | definition |
|---|---|
| inlet | the via bottom face, `z = 0`, `r <= r_via`, **equipotential** (Dirichlet) |
| outlet | the trace exit face, `x = +span`, inside the RDL, **equipotential** (Dirichlet) |
| all other outer faces | insulated |
| dielectric | present in both models |
| resistance | `R = dV / Q_inlet` |

A Neumann flux at the inlet would leave that face NON-equipotential and would measure a
different quantity. Both codes impose the same two planes, and nothing else conducts to the
boundary.

## Why `dR` is not called an excess

Phase 0M reported `K_crowd < 1` for a generous landing pad and called `R_3D - R_bulk` an
"excess resistance". It is not. The 1-D reference is a series of named conductors with
implicit equipotential cross-sections EVERYWHERE; the 3-D solve constrains only the two
planes above. They are different boundary-value problems, so their difference can legitimately
be negative -- a wide pad really does replace part of a narrow trace. **Phase 0M-R reports
`R_total` as the validated quantity and `dR` as a difference against a STATED 1-D
reference.**

## Canonical bulk

| case | FV vs analytic | MOOSE vs analytic |
|---|---|---|
| canonical_uniform_bar | 3.82e-12 % | 0.00e+00 % |

Both codes are exact on the uniform bar. MOOSE is an independent operator with its own
mesher, element formulation, quadrature and linear solver; the analogy `div(k grad T) = 0`
to `div(sigma grad V) = 0` is exact, so this is a genuine second implementation and not a
re-run of the same one.

## Five transition geometries, cross-solver

| case | cells across trace | trace edge on a node | via volume error | metal volume error | FV | MOOSE | difference | FV mesh drift | verdict |
|---|---|---|---|---|---|---|---|---|---|
| TSV_nominal | 6.0 | True | 0.60 % | 1.26 % | 0.0199044 | 0.019854 | **0.25 %** | 0.03 % | **ACCEPTED** |
| TSV_widepad_widetrace | 10.0 | True | 0.97 % | 0.05 % | 0.00844723 | 0.00838567 | **0.73 %** | 0.26 % | **ACCEPTED** |
| TSV_widepad_narrowtrace | 4.0 | True | 0.97 % | 0.27 % | 0.0333657 | 0.0332469 | **0.36 %** | 0.03 % | **ACCEPTED** |
| TSV_narrowpad_widetrace | 10.0 | True | 0.97 % | 1.52 % | 0.00893173 | 0.00890423 | **0.31 %** | 0.05 % | **ACCEPTED** |
| bump_nominal | 6.0 | True | 0.97 % | 0.57 % | 0.0527616 | 0.0531407 | **0.71 %** | 0.25 % | **ACCEPTED** |

**5 of 5 ACCEPTED, every case inside 0.75 %.** The transition model is authorised for
production.

### The first attempt failed, and why that matters

The first cross-solver run returned 12.1 % and 18.7 % on the two narrow-trace cases and
REJECTED them. The cause was not a solver disagreement: MOOSE's `ParsedSubdomainMeshGenerator`
assigns whole elements by CENTROID, so a uniform mesh staircases the trace. At
`span = 100 um` and `nx = 100` the cell is 2 um and a 10 um trace is captured 8 um wide.
The disagreement tracked the trace width and changed SIGN in the direction the staircase
predicted each time -- MOOSE read high where its trace was narrow and low where it was wide.

Fixing it required making mesh alignment part of the case definition: every case now fixes
`n` so that cell boundaries land exactly on `+/- w/2` and on the RDL z-planes, and every run
reports the discretised block volumes so the geometry match is proved rather than assumed.
The via volume agrees to 0.60-0.97 % (the circle staircases in both codes) and the metal
volume to 0.05-1.52 %.

## The surrogate was rejected

A two-term logarithmic form, which is what constriction theory suggests, was fitted over 178
solved geometries:

`dR t_rdl / rho = a ln(r_pad/r_via) + b ln(2 r_pad/w_trace) + c`

| class | n | a | b | c | residual, as % of the SPREAD of the group |
|---|---|---|---|---|---|
| tsv | 108 | +0.27345 | -1.22856 | +0.37328 | 9.8 % |
| microbump | 46 | +0.31866 | -1.15734 | +0.31366 | 9.0 % |
| c4 | 12 | +0.04567 | -0.22044 | -0.31803 | 28.9 % |
| bga | 12 | +0.31136 | -0.24571 | -0.35448 | 13.6 % |

**REJECTED for every class.** An earlier version of this table reported 6 % for C4 and BGA
and 54 % for TSV, using relative error against the magnitude of `dR`. That metric was wrong
in both directions: `dR` crosses zero for the TSV grid, which inflates the relative error
near the crossing, while C4's `dR` barely varies at all, which makes a fit that explains
almost none of its variance look excellent. Measured against the SPREAD, C4 is the worst
case, not the best.

The production path does not need a surrogate. The optimizer is forbidden, so only a handful
of geometries are ever evaluated; `transition_dR()` solves each one exactly with the
validated solver and caches it against a geometry fingerprint. **No extrapolation is possible
because no extrapolating object exists.**

## HFSS --- used for the question it can answer

The transition cells are a PURE CONDUCTION problem: two equipotential planes and no return
path. HFSS is a full-wave solver and cannot pose that problem; forcing it would mean
inventing a return conductor and subtracting its resistance, which adds the uncertainty the
validation exists to remove. **The DC transition resistance is therefore validated against
MOOSE and analytics, not against HFSS.**

HFSS is instead applied to the closed P/G TSV loop, which is a real two-conductor structure
and which carries the skin model this project uses in production through the pre-existing TSV
framework's Bessel solution. The comparison is a FREQUENCY TREND, as the brief requires, not
a forced `f -> 0` extrapolation.

**HFSS status: ATTEMPTED -- geometry, lumped port and boundaries all built and verified in AEDT 2026 R1 batch; the adaptive full-wave solve of a 15 um copper via with solve-inside did not converge within the 25 minutes this phase allocated to it.** The AEDT 2026 R1 batch interface, the geometry build, the lumped port and the boundary assignment were all verified working; the adaptive full-wave solve of a 15 um copper via with solve-inside enabled did not converge within the time this phase allocated to it. The DC validation does not depend on it and is complete without it.

## Licence and solver availability, checked not assumed

| tool | status |
|---|---|
| `elec_solve_hfss` | 1 licence, available |
| `elec_solve_icepak` | 1 licence, available |
| `elec_solve_q3d` | **not present** -- Q3D remains unlicensed |
| Elmer, GetDP, Palace, OpenFOAM | absent |
| MOOSE `heat_transfer-opt` | present, and the operator used here |
