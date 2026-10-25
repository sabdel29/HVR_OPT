# Commercial benchmark status

**No controlled commercial speedup has been established, and none is claimed.**

## What would be required

A speedup `S = T_reference / T_framework` is only meaningful when all of the following
hold simultaneously:

| requirement | status |
|---|---|
| same physical geometry | not attempted |
| same material properties | not attempted |
| same heat-source map | not attempted |
| same boundary conditions and ambient | not attempted |
| same total deposited power | not attempted |
| comparable accuracy on the same observable | not attempted |
| same hardware, or absolute times reported per machine | not attempted |

None has been attempted, so no `S` exists. A number produced without these would
measure the mismatch between two different problems, not the framework.

## What the commercial tools actually are

Identified by numerical method only, from vendor documentation, and used for nothing
else:

* **Ansys Icepak** — control-volume (finite-volume) discretization through the Fluent
  solver.
* **Ansys Mechanical / Mechanical APDL** — finite-element analysis.

Vendor statements about accuracy are marketing and are not used as validation evidence.

## Why a careless comparison would be wrong

The framework's thermal stage solves **conduction only**. Icepak in its normal mode
solves **conjugate heat transfer with a flow field**. Timing one against the other and
reporting the ratio as a speedup would compare a conduction solve against a CFD solve
and attribute the difference to the framework. If a comparison is ever run it must use
a conduction-only matched case, with the conjugate case reported separately.

## What exists instead

* **Absolute runtime**, stage by stage — `runtime_breakdown.csv`, flagged
  `HISTORICAL_FROZEN_R3C_RUNTIME` because it belongs to the frozen geometry and the
  physical pair has since changed substantially.
* **Independent open-source validation** against MOOSE for the RDL sheet, transition
  resistance, spreading and the cooling correlation.
* **Mesh and iteration convergence** for the thermal, mechanical and local stages.

MOOSE is an open-source finite-element framework. It is **not** a commercial tool, and
agreement with it is validation of physics, not a competitive timing result. The
existing MOOSE comparisons were also not timed under matched conditions, so they do not
support a speedup claim either.

## Required manuscript wording

> No speedup against a higher-fidelity reference is claimed.

This sentence stays until a controlled experiment exists. A defensible "not established"
is worth more than an unsupported multiplier.
