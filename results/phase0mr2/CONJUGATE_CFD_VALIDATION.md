# PHASE 0M-R2 SECTION 6 --- CONJUGATE CFD VALIDATION

**Verdict: CFD UNAVAILABLE / NOT COMPLETED.**

## Pass bands, declared before the run

They were written to `results/phase0mr2/cfd_pass_bands.md` before any solver was launched.

| quantity | band |
|---|---|
| outlet coolant temperature | <= 3 % |
| pressure drop | <= 10 % |
| mean wall temperature rise | <= 5 % |
| effective thermal resistance | <= 7 % |

## The case

The production channel as a single unit cell: 50 um wide, 300 um tall, 50 um fin, 100 um
base, 22.36 mm long, silicon at 130.0 W/mK, water at the declared reference
properties. 223 channels carry 27 g/s in total, so this cell carries
0.000121076 kg/s at 8.170 m/s and dissipates 4.4843 W in its base.

Materials were DEFINED in the deck rather than taken from the Icepak library, so the CFD
case and the compact model provably use the same numbers. A library lookup would have
introduced a different property set and made any disagreement uninterpretable.

The case was built so the earlier Icepak failure mode could not recur. That attempt
returned exactly 5000 K on every object -- a solver clamp caused by applying an external
boundary condition to an internal solid/air interface, leaving the model no route for heat
to leave. Here the coolant is an explicit fluid volume, the inlet is an opening with a
stated mass flow and temperature, the outlet is an opening at fixed static pressure, and
every other external face is adiabatic, so the only heat path out is the coolant.

## What happened

The batch API required five corrections before the solver would start, each diagnosed from
the job log rather than guessed:

| attempt | failure | fix |
|---|---|---|
| 1 | `Si is not a valid material` | materials defined explicitly in the deck |
| 2 | `SteadyState is not a valid solution type` | design type is `TemperatureAndFlow` |
| 3 | `Boundary 'inlet': can only be assigned on a sheet or face` | openings assigned to faces found by centre position, not to the body |
| 4 | every setup-type string rejected as "not a valid Optimetrics setup type" | probed the module: `IcepakSteadyState` is the accepted name |
| 5 | `Solver failed because of poor mesh quality` | explicit per-direction mesh controls for a 447:1 aspect channel |

After the fifth correction the geometry, materials, boundaries, mesh and setup all built
and the solver began iterating.

**The solve did not return usable field values within the time allotted to this gate.**
The analysis step reported: `Analyze(string simulationName, [bool isBlocking /*optional*/]) -> long(Setup1) - call failed. Logs or message window might have more details`

This is recorded as **CFD UNAVAILABLE / NOT COMPLETED** and is NOT upgraded. The brief states that a failed
benchmark is a scientifically acceptable outcome, and inventing a comparison would be
worse than having none.

**No Icepak validation is claimed.** The compact cooling model's validation status is
unchanged from Phase 0M-R: cross-validated on the SOLID side against MOOSE with explicit
fins -- 2 of 4 geometries ACCEPTED, 1 CONDITIONAL at 6.04 %, 1 REJECTED at 10.11 %, with
the production geometry in the accepted band at 3.78 % -- and exact on the fluid side by
construction. The conjugate question remains OPEN.

## Why an open-source alternative was not substituted

The MOOSE build available here is `heat_transfer-opt`, which has no Navier-Stokes module,
so it cannot do a conjugate flow case. Fluent is not installed: `/local/ansys/ansys_inc/v251/`
contains only `commonfiles`, `installer` and package metadata. Installing a new CFD stack
would distort the project for one benchmark, which the brief explicitly cautions against.

## What would close this

The case is built and its deck is saved at `results/phase0mr2/icepak/run_184111`. It needs a longer
wall-clock budget and, most likely, a shortened channel: the 447:1 flow-direction aspect
ratio is what defeated the automatic mesher, and a periodic slice of the channel would
test the same physics at a fraction of the cell count.

## The compact model's own numbers at the production point, for whoever completes this

| quantity | compact model |
|---|---|
| outlet coolant temperature | 33.86 C |
| coolant temperature rise | 8.86 K |
| pressure drop | 537.8 kPa |
| hydraulic pumping | 14.70 W |
| total thermal resistance | 0.01731 K/W |
| effective h | 115553 W/m2K |
| Re | 1264.8 (laminar) |
