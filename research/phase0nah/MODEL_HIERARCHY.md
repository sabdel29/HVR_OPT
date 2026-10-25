# Model hierarchy and computational strategy

The framework is **not** an analytical framework that replaces FEM/FVM. It is a
**hierarchical analytical + reduced + numerical multiphysics framework**: different
physics are solved at different fidelities, and the expensive solves are kept out of the
inner architecture loop rather than eliminated.

Verified against HEAD rather than assumed: the production thermal path writes `C3D8`
elements and runs CalculiX (`scripts/phase0b/etm/ccxio.py:88`), and the structural path
writes `C3D8I` (line 143). **Both are finite element.** Describing either as analytical
would be false.

## Fidelity ladder

```
converter synthesis            ANALYTICAL              ~4.6 s
        v
rail-aware power path          NETWORK / ALGEBRAIC     ~0.1 ms
        v
BGA / pad / TSV bulk R         ANALYTICAL              < 1 ms
        v
package RDL sheet              REDUCED PDE (G V = I)   ~1 s
        v
detailed current crowding      FVM                     (on demand)
        v
electrothermal fixed point     PICARD COUPLING         3 iterations
        v
package thermal field          FEM  (CalculiX C3D8)    75-121 s
        v
global thermoelastic           FEM  (CalculiX C3D8I)   50-68 s
        v
critical-joint local response  FEM, nonlinear          35-45 s
```

Counts by type across the twelve stages: 3 analytical, 1 analytical/compact, 1
network/algebraic, 1 reduced PDE, 1 reduced material model, 1 FVM, 1 iterative coupling,
3 FEM (one nonlinear).

## Where the time actually goes

Every analytical and reduced stage together costs **under 5 s**. The three FE stages cost
**135 s (Z1) and 204 s (Z2)**. So the honest statement is not that the framework is
analytical, but:

> Analytical and reduced models remove expensive high-fidelity calculation from the inner
> architecture loop where it is not needed, while FE is retained for the global thermal
> and mechanical fields and for the local nonlinear response, where spatial resolution is
> required.

## What makes it efficient, mechanism by mechanism

1. converter loss is evaluated in closed form rather than by switching-time simulation;
2. rail allocation is a network solve, not 3-D EM;
3. BGA/TSV/pad bulk terms are `rho L / A`;
4. the package RDL is collapsed to a 2-D sheet instead of meshing 3-D conductors;
5. microstructure uses validated effective properties instead of meshing every feature;
6. cooling uses a correlation inside a declared validity domain instead of conjugate CFD
   per evaluation;
7. mechanics runs **once after** E-T convergence, not inside the fixed point — 1 solve
   per architecture against 3 E-T iterations;
8. the nonlinear solder model runs only at the critical joint, not at every joint.

Items 7 and 8 are architectural choices whose avoided cost has **not** been separately
timed, and are classified `INFERENCE` rather than `MEASURED` in the claim matrix.

## Evidence classes are not interchangeable

Of the twelve stages: **6 VALIDATION** (against MOOSE, an independent closed form, or the
DVPD source), **2 VERIFICATION** (conservation/implementation), **4 CONVERGENCE only**
(mesh or iteration independence against no external reference).

Convergence is not accuracy. A mesh-converged warpage figure says the discretization has
stopped moving, not that it matches reality. There is therefore **no single framework
accuracy percentage**, and the claim matrix marks any such statement `NOT_SUPPORTED`.

## Runtime provenance

All timings above are `HISTORICAL_FROZEN_R3C_RUNTIME`. They belong to the frozen R3C
geometry. The physical pair has changed substantially — new converter tiers, a new
interface, a package RDL network that did not previously exist — and has **not** been
re-benchmarked. They must not be presented as timing of the corrected physical model.
