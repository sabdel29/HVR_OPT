# HVR switch-state source audit

Phase 0N-AD. Evidence taken from PRIMARY CODE, not from
`research/HVR_PHASE_COUNT_AUDIT.md`, which is an audit artifact.

Source: `Scalable_Integrated_VR/src/HVR_FULL_OPT_EPC_V2.py` at pinned submodule
`ed56ae6ec2d28c58a2c3dfca627043a57732af50`.

## 1. What the code actually defines

`generate_B_array(N, K, K_A)` (line 101):

```python
K_B = K - K_A
phA = math.ceil(N / 2)      # SC branches in phase A
phB = math.floor(N / 2)     # SC branches in phase B
distA = distribute_branches(phA, K_A)
distB = distribute_branches(phB, K_B)
```

and `generate_architectures` (line 131):

```python
K_A = math.ceil(K / 2)
D   = (V_out * N) / V_in
```

So for the selected N=3, K=3, K_A=2:

| symbol | meaning IN CODE | value |
|---|---|---|
| N | series-capacitor stages | 3 |
| K | parallel inductor branches | 3 |
| K_A | inductors serving phase A | 2 |
| K_B = K - K_A | inductors serving phase B | 1 |
| phA = ceil(N/2) | SC branches in phase A | 2 |
| phB = floor(N/2) | SC branches in phase B | 1 |
| B_array | SC branches assigned PER INDUCTOR | [1, 1, 1] |
| D = V_out·N/V_in | duty | 0.0625 |

**B_i is a count of SC branches feeding inductor i**, produced by
`distribute_branches`, which is integer division with a remainder spread. It is not an
independently chosen current-sharing weight.

## 2. What the code does NOT contain

Searched for time-domain machinery: `t_on`, `t_off`, `dead_time`, `switch_state`,
`timestep`, waveform integration. **None is present.** The six textual matches are
comments describing ripple GATES, e.g. `ΔV_out = |ΔI_eff|/(8·f_sw·C_out)`.

Therefore the source provides **no**:

- switch-state sequence;
- explicit phase-A / phase-B durations;
- phase displacement between the two groups;
- flying-capacitor charge-transfer solution;
- dead time;
- any representation of a full switching period.

The converter model is algebraic. It yields aggregate quantities and ripple gates, not
waveforms.

**Consequence: RMS-L2 cannot be reconstructed from this source, and individual branch
RMS currents are OPEN.**

## 3. The error this audit corrects

Phase 0N-AC decomposed the model's summed output ripple

    ΔI_out = (D/(f·L)) · (V_in/N·K_A − V_out·K)

into `K_A(V_mid − V_out)` and `(K − K_A)(−V_out)` and treated each term, taken over the
on-interval D·T, as that branch's **full-cycle ripple**. That gave

    phase A: 4.6574 A      phase B: 0.3105 A

The algebra is right; the interpretation is not. A term's contribution to the summed
ripple during one interval is not the periodic waveform of the inductor it belongs to.

**Volt-second balance on a conventional buck branch** makes the gap visible:

    up-ramp   (V_mid − V_out)·D·T/L   = 4.6574 A
    down-ramp  V_out·(1 − D)·T/L      = 4.6574 A

equal to machine precision, as balance requires. So a conventional branch at this
operating point would ripple 4.6574 A, not 0.3105 A — a factor of
15. The 0.3105 A figure used `(1−D)` nowhere and so described no
complete cycle at all.

This is a **sanity check, not an imposition**: whether our phase-B inductors behave as
conventional buck branches depends on the switching sequence, which the source does not
give. Both the old 0.310 A and the conventional 4.657 A are therefore withdrawn as
established branch ripples.

Principle reference: Wong, Xu, Yang & Lee, "Performance Improvements of Interleaving
VRMs with Coupling Inductors", IEEE TPEL 2001, `10.1109/63.931059` — individual phase
ripple and summed output ripple are distinct quantities related by the temporal phase
displacement. CONTEXT_ONLY / PRINCIPLE: used for the distinction, not for any equation.

## 4. What survives

| quantity | status |
|---|---|
| branch AVERAGE current I_cell·B_i/ΣB = 6.8027 A | KNOWN |
| aggregate output ripple ΔI_out from the model | KNOWN (the model's own output) |
| per-cell output RMS from that aggregate | KNOWN |
| individual branch ripple | **OPEN** |
| individual branch RMS | **OPEN** |
| 16 V mid-rail RMS | **OPEN** |
| 48 V input RMS | **OPEN** |
