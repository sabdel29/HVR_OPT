# PHASE 0M-R --- OPEN ITEMS

Every item here is OPEN in the strict sense: **not determined, and never silently
defaulted**. Where a value would be convenient, its absence is carried as an OPEN field
rather than filled with a plausible number.

## Blocking, in priority order

| item | why it is open | what it blocks | what would close it |
|---|---|---|---|
| **high-stress SAC305 constitutive response** | no primary data above about 16 MPa at 45 to 150 C could be retrieved; four P0 and five P1 papers sit behind institutional access | every absolute reliability number, and the MAGNITUDE of the relative one | coupon characterisation at 15 to 100+ MPa, or institutional access to the named papers |
| **required life `N_required`** | not published for the reference system, and inventing one is forbidden | the falsification gate G2 | a statement from the system owner |
| **mechanical allowable** | nine candidates tested against six admissibility conditions; none passed | turning the mechanical response into a constraint | a published allowable tied to a failure mode, with its conditions |
| **electromigration current-density allowable** | no primary study with its temperature, lifetime and geometry | a feasibility VERDICT on any via field; today it is a map over J | one primary EM study with its conditions |
| **package clearances** (die-to-component, cavity sidewall, cooler standoff) | no source in this repository gives them | calling any partition template buildable | a process design rule from a named vendor |
| **cohesive-zone parameters** | traction-separation laws and interface fracture energies unsourced | predicting delamination at all | interface fracture testing, or a sourced law for these material pairs |

## Non-blocking but unresolved

| item | status |
|---|---|
| polymer viscoelastic spectra | no DMA data for the specific laminate; a modulus sensitivity is carried instead of a Prony series. Measured effect on the driver ratio: about 3 % |
| Z4 power-die layer geometry | the global mesh has no such layer; Z4's converter heat is deposited in the interface layer and **the Z4 thermal and mechanical results are conditional on that substitution** |
| pump efficiency | unsourced; hydraulic power is primary and a 35/55/75 % band is carried |
| MLCC height | manufacturer page unreachable; a 100 um nominal / 250 um upper envelope is carried |
| conjugate CFD validation | the earlier Icepak attempt returned a solver clamp of exactly 5000 K and stays discarded. The licence is available and a canonical single-channel benchmark is the named next step |
| HFSS AC loop validation | the model built and the ports assigned; the adaptive full-wave solve did not converge in the time allocated. The DC validation does not depend on it |
| RDL as the production default | the fidelity ladder is built and measured; it is not yet the default mechanical and thermal representation |
| trace-level RDL stress | would need explicit redistribution geometry, a declared averaging volume and a convergence study. Not attempted, and no allowable exists for it anyway |

## What is NOT open, and should not be relitigated

* the ordering Z2 better than Z1 on solder fatigue --- robust, and now re-tested through the
  production path;
* the transition-resistance model --- cross-validated against an independent solver at 0.25
  to 0.73 % on five geometries;
* the cooling fluid-side energy balance --- exact;
* the loss ledger --- one owner per watt, enforced, with the decomposition checked against
  its own aggregate;
* that the framework is at ETM-L1 --- measured, not assumed.
