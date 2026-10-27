# Can the 48-V input current waveform be closed? Determination: **no**, and here is why

`P = I_rms^2 R` makes the 48-V waveform the largest single lever on every
HV-side conduction term, so this phase was asked to try to close it rather than
keep reporting scenarios. The attempt was made against the actual converter
source. **The outcome is case D of the four the brief allowed: the waveform is
not recoverable from the present model**, and the reason is structural, not a
matter of effort.

## What the converter source actually contains

The pinned generator is
`Scalable_Integrated_VR/src/HVR_FULL_OPT_EPC_V2.py`. Its electrical core is:

| line | content |
|---|---|
| 135 | `D = (V_out * N) / V_in` |
| 716 | unpacks `N, K, K_A, B_array, D` from the architecture |
| 736 | `I_out_rms = sqrt(I_out**2 + delta_i_eff_sq / 12.0)` |
| 751 | `P_cond = (V_out / V_in) * I_out_rms**2 * (common - correction)` |
| 758 | `P_sw_HS = f_sw * (V_in/N - V_out) * I_out_rms * ((Q_GD + Q_G)/I_g)` |

Everything electrical is built from **one scalar**, `I_out_rms`, obtained from
the standard triangular-ripple identity on the OUTPUT inductor current, and
then duty-weighted by `V_out/V_in`.

## What it does not contain

Searched across the whole generator and the repository:

- no switched-capacitor **state sequence** and no per-state conduction interval;
- no flying-capacitor **charge balance** (`q_factor` in that file is an
  inductor quality factor, not charge);
- no **input** current variable at all --- there is no `I_in`, no `P_in`, and
  no construction of a 48-V-side waveform anywhere;
- no dead-time or commutation model that would set the conducting fraction.

The 48-V average current is therefore obtained *downstream* by power balance
(`I_avg = P_in / 48`), which is the only thing power balance can give. It
cannot give an RMS: average current closes energy balance, RMS closes
conduction loss, and no amount of algebra converts one into the other.

## Why the four options resolve to D

**A. Another repository artifact holds the sequence.** No. The only files
mentioning charge balance are `z2_converter.py` and `inventory_audit.py`, and
in both it is prose about what is missing, not a model.

**B. Simulate the topology from its switch schedule.** Not possible from this
source, because the switch schedule is exactly what is absent. A simulation
would have to invent the conducting intervals, and an invented schedule would
produce an invented RMS that would then be reported as physics.

**C. The source literature contains the state sequence.** The DVPD source
(10.1109/TCPMT.2026.3724907) specifies the delivery architecture, not the
internal switching sequence of our adopted hybrid topology. Hybrid/SC RMS
papers such as 10.1109/OJSSCS.2026.3709735 derive input RMS correctly *for
their own topologies*; that is **methodology context**, and importing their
RMS ratio into ours would be transferring a different converter's waveform.

**D. Unresolvable from the present model.** This is the finding.

## What would close it

Any one of the following, and nothing less:

1. the per-state switch conduction table for the adopted 3:1 SC + two-phase
   buck (which switch conducts during which sub-interval, and for how long);
2. the flying-capacitor charge-transfer schedule with its charge balance, from
   which the input current pulse train follows;
3. a circuit-level netlist or simulation deck of the adopted topology.

## Consequence, held deliberately

`HV-S0`, `HV-S1` and `HV-S2` remain **named scenarios**. They are not a
lower/nominal/upper bracket, not a statistical range, and not bounds: from an
average current alone there is no finite RMS upper bound at all, because a
narrower and taller pulse of the same average has strictly higher RMS without
limit. Every HV-side `I^2 R` term in the ledger is reported per scenario and
never collapsed, and the BGA count closure reports a separate required count
for each scenario for the same reason.
