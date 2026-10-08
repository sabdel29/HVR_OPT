# PHASE 0M PART 7 --- DC CURRENT-CROWDING SOLVER AUDIT

Q3D is not licensed. That is not a reason to omit current crowding.

## Capability audit, this environment

| candidate | present | what it can and cannot do here |
|---|---|---|
| **Elmer** `StaticCurrentSolver` | **NO** | not installed; would have been the first choice for DC conduction |
| **GetDP** | **NO** | not installed |
| **Palace** | **NO** | not installed. Even where it is, its electrostatic mode solves a PERMITTIVITY problem, `div(eps grad V) = rho`. That is **not** a DC conduction solver and must not be described as one. Its driven mode is for AC field problems |
| **MOOSE** `heat_transfer-opt` | **YES** | present at `/home/beams0/LPOPRYHO/projects/moose/modules/heat_transfer/heat_transfer-opt`. Steady conduction `div(k grad T) = 0` is the SAME operator as `div(sigma grad V) = 0`, so MOOSE is a valid independent cross-check on the scalar conduction operator, already used that way in Phase 0D-R (FD vs MOOSE agreed to 0.33-0.45 %) |
| **gmsh** | **YES** | mesher available for an unstructured route; not needed, the transitions are box-like |
| **HFSS** | licensed | correct at the switching frequency and its harmonics. A DC extrapolation of a full-wave solve is ill-conditioned and is NOT used for DC here |
| **this module** | built | `scripts/phase0m/conduction3d.py`, a conservative finite-volume discretisation on a graded tensor grid |

**Chosen: a purpose-built finite-volume solver, cross-checked against analytic results.**
Finite volume rather than nodal Galerkin on purpose: `sigma` jumps nine orders of magnitude
at every metal/dielectric face, and a cell-centred FV scheme with harmonic-mean face
conductivities is exactly conservative across such a jump. Current conservation is verified
on every solve rather than assumed.

## Verification against closed-form results

| case | mesh | R computed | analytic | ratio | current balance |
|---|---|---|---|---|---|
| uniform_bar | n=8 | 0.00431034 | 0.00431034 | **1.0000** | 1.5e-14 |
| uniform_bar | n=16 | 0.00431034 | 0.00431034 | **1.0000** | 1.1e-13 |
| uniform_bar | n=24 | 0.00431034 | 0.00431034 | **1.0000** | 8.6e-12 |
| spreading_halfspace | h_fine=2.500um (2 cells per contact radius) | 0.00104038 | 0.000897989 | **1.1586** | 9.5e-12 |
| spreading_halfspace | h_fine=1.250um (4 cells per contact radius) | 0.000911739 | 0.000897989 | **1.0153** | 8.2e-12 |
| spreading_halfspace | h_fine=0.833um (6 cells per contact radius) | 0.000905985 | 0.000897989 | **1.0089** | 1.7e-11 |

The uniform bar is **exact at every mesh**, which is not automatic: the first version of the
solver injected and extracted at CELL CENTRES and returned `R_exact (n-1)/n`, an O(1/n) error
that would have been read as a crowding effect. Both terminals are now explicit equipotential
NODES joined to their boundary cells by the exact half-cell conductance.

The spreading resistance of a circular contact on a half-space, `rho/(4a)`, converges from
+15.9 % at 2 cells per contact radius to **+0.9 % at 6 cells per contact radius**. That is the
case where crowding is the entire answer, so it is the binding verification.

## Mesh convergence of the transition cell

| refinement | cells | active cells | K_crowd |
|---|---|---|---|
| 0.8 | 29952 | 3400 | 0.89435 |
| 1 | 50460 | 7100 | 0.89680 |
| 1.3 | 83300 | 12324 | 0.89464 |
| 1.6 | 121680 | 17776 | 0.89585 |
| 2 | 211968 | 38252 | 0.89450 |

## What the solver reports

`J(x,y,z)`, `J_peak/J_avg`, the terminal current, the effective resistance by two independent
routes (terminal potential and volume dissipation, which agree to 1e-10 relative), and the
Joule-heat density.

## Two faults of my own that this audit caught

1. **A zero-width cell.** `snapped()` deduplicated interface planes with `np.unique`, which
   removes only bit-identical values. A pad radius that coincides with a trace half-width
   produced two nodes an ULP apart, a zero-width cell, an infinite terminal conductance and a
   silently wrong `K_crowd = 0.32` in a 92-point sweep. The only symptom was the
   current-balance residual. Fixed three ways: tolerance-based deduplication, a hard
   assertion on non-positive cell widths, and a validity gate that rejects any solve whose
   current balance exceeds 1e-3. All three are negative-tested.
2. **Dead-ended traces.** Fanned traces at +/-60 degrees with the ground only on the +x face
   carried no current at all, and the three-trace case returned `K_crowd = 2.49`. Traces are
   now axis-aligned and every lateral face is grounded.

## Result

`K_crowd` spans **0.606 to 1.483** over 107 converged geometries --- a factor of
2.45 --- against the single global constant **1.326** the framework applies to BGA, C4,
TSV and microbump alike.
