# PHASE 0M-R3 SECTION 11 --- CANONICAL CONJUGATE CFD VALIDATION

**Verdict: CFD UNAVAILABLE / NOT COMPLETED.**

## Acceptance bands, declared before the run

| quantity | band |
|---|---|
| energy balance | <= 1 % |
| outlet coolant temperature | <= 3 % |
| pressure drop | <= 10 % |
| mean wall temperature rise | <= 5 % |
| effective thermal resistance | <= 7 % |

## What changed from the Phase-0M-R2 attempt

That attempt built correctly and then ran the full 2400 s without returning. The cause was
the geometry: the production channel is 50 x 300 x 22360 um, an aspect ratio of 447:1 along
the flow, and a mesh that resolves a 50 um width over 22 mm of length is enormous.

This case uses a **periodic slice** of 1.0 mm instead of the full
22.36 mm. Fully-developed laminar flow is invariant along the
flow direction, so a short slice tests the same wall-to-fluid physics at a fraction of the
cell count. The length-dependent part of the compact model is the caloric term, which is
exact by construction and is not what needs validating.

| | |
|---|---|
| channels in the full cooler | 223 |
| mass flow per channel | 0.000121076 kg/s |
| velocity | 8.170 m/s |
| heat into the slice | 0.20055 W |
| declared wall-clock budget | 2700 s (45 min, per the brief) |

Materials are DEFINED in the deck rather than taken from the Icepak library, so the CFD
case and the compact model provably use the same numbers.

## Outcome

**The benchmark did not produce a field result.** Specifically, the solver ran for the full declared budget without returning and the job was terminated at that limit.

Mesh construction succeeded (mesh status not reported),
as did geometry, materials, boundaries and the analysis setup. The failure is in the solve,
not in the case definition.

This is recorded as **CFD UNAVAILABLE / NOT COMPLETED** and is NOT upgraded. **No Icepak validation is claimed.**
No compact-model constant was tuned toward any CFD number, which the brief explicitly
forbids and which would in any case be meaningless without a converged reference.

## Why no open-source substitute was used

The MOOSE build here is `heat_transfer-opt`, which has no Navier-Stokes module and cannot
run a conjugate flow case. Fluent is not installed: `/local/ansys/ansys_inc/v251/` holds
only `commonfiles`, `installer` and package metadata. No OpenFOAM is present. Installing a
new CFD stack for one benchmark would distort the project, which the brief cautions against.

## Section 12 --- the cooling claim, scoped honestly

| aspect | status |
|---|---|
| physically parameterized | **YES** --- h from a Nusselt correlation for the duct, fin efficiency, area amplification, caloric resistance, streamwise coolant rise |
| correlation-domain valid | **YES** at the production point --- Re = 1264.8, inside the SOURCE_BACKED laminar range, and the design space is now capped at Re <= 2300 |
| solid-side cross-validated | **YES** --- MOOSE with explicit fins, 3.78 % at the production geometry |
| fluid-side CFD validated | **NO** |

The cooler is therefore **PHYSICALLY PARAMETERIZED, CORRELATION-DOMAIN VALID and SOLID-SIDE
CROSS-VALIDATED, with the FLUID SIDE NOT CFD-VALIDATED.** It is not called fully validated.

## The compact model's numbers at the production point, for whoever completes this

| quantity | value |
|---|---|
| Re | 1264.8 (laminar) |
| outlet coolant temperature | 33.86 C |
| coolant rise | 8.86 K |
| pressure drop | 537.8 kPa |
| hydraulic pumping | 14.70 W |
| total thermal resistance | 0.01731 K/W |
| effective h | 115553 W/m2K |

The deck is saved at `results/phase0mr3/icepak/run_014636`.
