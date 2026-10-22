# HVR phase-count audit — what N, K and K_A actually mean

Phase 0N Section F. Everything below is read from the implementation
(`Scalable_Integrated_VR/src/HVR_FULL_OPT_EPC_V2.py`, pinned at `ed56ae6`) and from the
compiled design returned by `kw1.design_1kw()`, not from the manuscript text.

## 1. The compiled design

```
label            N3K3KA2_J3.5
N = 3   K = 3   K_A = 2   B_array = [1, 1, 1]
D = 0.0625        component_count = 11
f_sw             805,170.3 Hz
I_out per cell   20.408163 A
V_in / V_out     48 / 1 V
area per cell    5.61 mm2   (budget 5.831)
loss per cell    1.8663 W at 25 C
high side        EPC2014C  R_DS_ON 16.0 mOhm  ID 10.0 A  1.87 mm2
low side         EPC2057  R_DS_ON 8.5 mOhm  ID 9.6 A  1.80 mm2
inductor         Shared_Core_UIC_250_nH  250 nH  1.6 mOhm  h = 500 um  k_coupling = 0.0
capacitor        Murata-GCM21-10uF-25V  10.0 uF  2.5 mOhm
```

## 2. Semantic definitions, proven from code

The decisive evidence is the component-count function, which is what the architecture
search enumerates over:

```python
def compute_component_count(N, K, hs_weight, ls_weight, inductor_weight, capacitor_weight):
    return (hs_weight * N + ls_weight * K
            + inductor_weight * K + capacitor_weight * (N - 1))
```

`run_hvr_optimization` passes all four weights as **1** (defaults, never overridden by
`compile_hvr`). So for the selected design:

```
components = N + K + K + (N-1) = 3 + 3 + 3 + 2 = 11
```

which equals the compiled `component_count = 11`. The mapping is therefore exact:

| symbol | meaning | count here | implementation evidence |
|---|---|---:|---|
| **N** | high-side devices, and the SC division ratio | 3 | `hs_weight * N`; `D = V_out * N / V_in`; `P_sw_COSS` term `N*hs.C_OSS`; SC blocking voltage `V_in/N` |
| **K** | **buck phases** — low-side devices AND inductors, one of each per phase | 3 | `ls_weight * K + inductor_weight * K`; `P_sw_GD` term `K*ls.C_G`; `P_sw_COSS` term `K*ls.C_OSS` |
| **K_A** | size of phase group A in the two-group A/B split | 2 | `K_A = math.ceil(K / 2)` in `generate_architectures` — **derived, not free** |
| **B_array** | high-side branches feeding each inductor | [1, 1, 1] | `generate_B_array(N, K, K_A)`; `B_sum = sum(b**2)` enters the conduction loss |
| **N − 1** | flying capacitors | 2 | `capacitor_weight * (N - 1)` |

**K = number of buck phases is PROVEN**, not assumed: K multiplies the low-side device
count and the inductor count by the same weight in the same expression, and the compiled
component count matches exactly.

`D = V_out * N / V_in = 0.0625` confirms the N-fold pre-division: 48 V / 3 = 16 V
intermediate, then D = 1/16 = 0.0625.

## 3. Per-phase current, derived not assumed

`scripts/phase0mr3c/feasibility.py` computes the switch-node current as

```python
i_per = i_agg / K if net == "ls_to_L" else i_agg
```

with `i_agg = 20.4082` A (the per-cell output current). So

```
I_phase = I_cell / K = 20.4082 / 3 = 6.8027 A
```

which is the `i_per_device_a = 6.8027` recorded in
`results/phase0mr3c/routing_feasibility.csv` and quoted in the frozen pair config. It sits
inside the **EPC2057 continuous rating of 9.6 A** (71 % of rating).

This also confirms K is treated as the phase count in the *realizability* domain, not only
in the loss model: the `ls_to_L` net is explicitly described in
`configs/phase0mr3c/frozen_pair_*.yaml` as "an aggregate over K = 3 phases ... there are
three such dies each with their own drain bar".

## 4. Interleaving — NOT justified

Searched the whole implementation for any phase-displacement construct. Findings:

| looked for | found |
|---|---|
| `interleav*` | **only in two literature-reference comments** (APEC 2000 QSW interleaving; Wong et al. coupled inductors). No code. |
| phase-shift / 120 deg / phase offset variable | **none** |
| time-domain modulation or per-phase timing | **none** — the loss model is closed-form analytic |
| interleaved ripple cancellation | **none**. The only ripple-reduction mechanism is coupled inductors: `coupling_boost = 1 + coupling_k * (K-1)` |

and for the selected inductor **`coupling_k = 0.0`**, so
`coupling_boost = 1.0` — even that mechanism is inactive.

The ripple expression is

```python
delta_i_raw = (D / (f_sw * L)) * (V_in / N * K_A - V_out * K)
```

K and K_A appear as multiplicities in a closed-form expression. Nothing in it encodes a
phase displacement between the K branches.

**Conclusion:** the design has **three buck phases**, so "3-phase buck" is accurate.
**"3-phase interleaved buck" is NOT supported by the implementation** and must not be
written. If 120 deg interleaving is intended as a design assumption, it is currently
*unmodelled* and would have to be stated as an assumption, not as a property of the result.

## 5. The N = K = 3 ambiguity

Because N and K are both 3, a schematic with three vertical branches is genuinely
ambiguous: a reader cannot tell whether the three branches are the three high-side
SC branches or the three buck phases. They are **different sets of three**:

- 3 high-side devices (EPC2014C) on the SC side, blocking V_in/N = 16 V
- 3 low-side devices (EPC2057) + 3 inductors on the buck side, each carrying 6.803 A
- 2 flying capacitors between them

Any figure must therefore label the two groups separately and show **11 components**, not three branches.

## 6. parameter → meaning → evidence → allowed manuscript wording

| parameter | semantic meaning | implementation evidence | allowed wording |
|---|---|---|---|
| N = 3 | high-side device count; SC division ratio | `hs_weight*N`, `D = V_out*N/V_in` | "a 3:1 switched-capacitor stage" |
| K = 3 | buck phase count (LS devices = inductors = K) | `ls_weight*K + inductor_weight*K`; `i_per = i_agg/K` | "a 3-phase buck stage" |
| K_A = 2 | derived A-group size, `ceil(K/2)` | `generate_architectures` | do not present as an independent design variable |
| B_array = [1, 1, 1] | branches per inductor | `generate_B_array`, `B_sum` in `P_cond` | "one high-side branch per inductor" |
| I_phase | 6.8027 A | `i_agg / K` | "6.803 A per phase, within the EPC2057 9.6 A rating" |
| interleaving | **not modelled** | no phase-shift construct exists | **do not write "interleaved"** |
