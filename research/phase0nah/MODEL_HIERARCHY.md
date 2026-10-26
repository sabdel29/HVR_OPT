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

Every analytical and reduced stage together costs **under 5 s**.

The FE cost is **not one number**, and an earlier version of this file got it wrong. The
frozen R3C benchmark row `full ETM evaluation (E-T fixed point + mechanics)` is
**134.62 s (Z1) / 204.23 s (Z2)** on 48 threads, and that interval covers the eleven
thermal sub-solves (75.1 / 121.4 s), the single global thermoelastic solve entered once
after convergence (49.5 / 67.6 s), and the remaining mesh construction, material
assembly, input writing and result parsing. It **excludes** the critical-joint local
solder submodel, which is a *further* **44.99 s (Z1) / 35.14 s (Z2)** measured on **128
cores**, not 48.

The retracted wording is kept here so the error is legible rather than erased:

> [RETRACTED] *"The three FE stages cost 135 s (Z1) and 204 s (Z2)."* [/RETRACTED]

That sentence folded a third stage into a figure that does not contain it, and silently
attributed a 128-core run to a 48-thread budget.

| quantity | Z1 | Z2 | cores | status |
|---|---|---|---|---|
| ETM evaluation (E-T fixed point + global thermoelastic + overhead) | 134.62 s | 204.23 s | 48 | `MEASURED` |
| critical-joint local solder submodel (entered once, outside the above) | 44.99 s | 35.14 s | 128 | `MEASURED` |
| arithmetic total | 179.61 s | 239.37 s | mixed | `DERIVED_SERIAL_SUM` |

The arithmetic total is labelled `DERIVED_SERIAL_SUM` because no benchmark measured that
wall interval, and because its two parts did not run on the same core count — it is a
bookkeeping sum, not a timing.

So the honest statement is not that the framework is analytical, but:

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

An earlier version of this file counted **6 VALIDATION** stages. That number was too
generous, because one label was doing three different jobs. Split properly, over the
twelve stages:

| class | stages | what the evidence actually is |
|---|---|---|
| `INDEPENDENT_NUMERICAL_VALIDATION` | 4 | checked against a separate solver (MOOSE, numerical RVE) |
| `CLOSED_FORM_VERIFICATION` | 1 | checked against an exact expression |
| `CONSERVATION_VERIFICATION` | 2 | an identity closes; nothing external was consulted |
| `SOURCE_REPRODUCTION` | 1 | we recomputed the source's OWN rho, L and A and got its own table back |
| `MESH_CONVERGENCE` | 2 | self-refinement only |
| `ITERATION_CONVERGENCE` | 1 | the fixed point settles; nothing external |
| `UNVALIDATED` | 1 | no external reference exists for this stage |

Only **4** of twelve stages carry evidence from an independent solver. The DVPD Table III
check is *not* one of them: it recomputes the source's own rho, L and A and recovers the
source's own numbers, which demonstrates that the published table is internally
consistent with plain rho L / A and nothing more. Calling that validation would let a
paper validate itself.

Convergence is not accuracy. A mesh-converged warpage figure says the discretization has
stopped moving, not that it matches reality. There is therefore **no single framework
accuracy percentage**, and the claim matrix marks any such statement `NOT_SUPPORTED`.

## Runtime provenance

All timings above are `HISTORICAL_FROZEN_R3C_RUNTIME`. They belong to the frozen R3C
geometry. The physical pair has changed substantially — new converter tiers, a new
interface, a package RDL network that did not previously exist — and has **not** been
re-benchmarked. They must not be presented as timing of the corrected physical model.
