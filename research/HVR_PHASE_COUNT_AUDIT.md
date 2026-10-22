# HVR topology audit — what N, K, K_A and B actually mean

Phase 0N-R. **This document supersedes the previous version, whose central conclusion
("K = buck phase count") was WRONG.** The error and its correction are recorded in §1 so
the mistake is not repeated.

Everything below is derived from the implementation
(`Scalable_Integrated_VR/src/HVR_FULL_OPT_EPC_V2.py`, pinned at `ed56ae6`) and verified
numerically against it.

---

## 1. The previous conclusion, and why it was wrong

The earlier audit argued:

> `compute_component_count(N,K,...) = hs·N + ls·K + inductor·K + cap·(N−1)`, therefore
> K multiplies both the low-side device count and the inductor count, therefore
> **K is the number of buck phases.**

The premise is correct and the conclusion does not follow. **K counts physical parallel
branches — one low-side device and one inductor each. It does not count temporal switching
states.** A converter can have K parallel inductor branches and any number of switching
phases; the component-count function cannot distinguish them, because it counts hardware,
not time.

The giveaway was in plain sight and was missed: the same architecture record carries
`K_A`, described upstream as "how many of those inductors sit in **phase A**". If K were
the phase count, "how many inductors sit in phase A" would be meaningless — each inductor
would be its own phase. The presence of a **phase A** implies a **phase B**, hence **two**
phase groups.

**The buck stage is two-phase. K = 3 is the number of inductor branches, not phases.**

---

## 2. Decisive evidence: the ripple equation

The implementation computes

```python
delta_i_raw = (D / (f_sw * L)) * (V_in / N * K_A - V_out * K)
```

Reconstruct it physically. Let `V_mid = V_in/N` = 16 V be the intermediate
switched-capacitor rail. During the modelled ON interval of length `D/f_sw`:

* **K_A inductors are driven** from the intermediate rail, each seeing `V_mid − V_out`;
* the **remaining K − K_A inductors freewheel**, each seeing `−V_out`.

The output current is the sum of all K inductor currents, so

```
dI_out/dt = [ K_A·(V_mid − V_out) + (K − K_A)·(−V_out) ] / L
          = [ K_A·V_in/N − K·V_out ] / L
```

and `ΔI_out = (dI_out/dt)·(D/f_sw)` — **algebraically identical to the code**, verified
numerically to machine precision (9.004306 A both ways for the selected design).

This is conclusive. `K_A` appears multiplied by `V_in/N` because **K_A branches are
connected to the intermediate rail in that state**; `K` appears multiplied by `V_out`
because **all K inductors sustain the output voltage in every state**. Two conduction
states, K branches.

It also fixes a second error: Eq. (ripple) is the **summed output-current ripple**, not a
"per-phase inductor ripple" as the manuscript called it.

## 3. K_B

`generate_B_array` opens with `K_B = K - K_A`, and the ripple derivation independently
requires the freewheeling count to be `K − K_A`. **K_B = K − K_A = 1**, confirmed twice
by independent routes.

## 4. How the SC branches map onto the groups

```python
def generate_B_array(N, K, K_A):
    K_B  = K - K_A
    phA  = math.ceil(N / 2)      # SC branches assigned to phase A
    phB  = math.floor(N / 2)     # SC branches assigned to phase B
    distA = distribute_branches(phA, K_A)
    distB = distribute_branches(phB, K_B)
    ...                           # interleaved into B_array
```

So the **N switched-capacitor branches** are split `ceil(N/2)` / `floor(N/2)` between the
two phase groups, and each group's branches are spread over that group's inductors.
`sum(B_array) = ceil(N/2) + floor(N/2) = N` **always** — every SC branch lands on exactly
one inductor.

`B_i` is therefore **the number of SC branches feeding inductor i**, not a conversion
ratio.

## 5. Current sharing — and why "I_cell/K" was the wrong name

With `B_i` branches feeding inductor i out of `sum(B) = N` total, the branch current is

```
I_branch,i = I_cell · B_i / N
```

The conduction-loss expression confirms this independently: it carries
`V_in/(N**2 · V_out) · (R_L_ESR + R_DS_ON,LS) · B_sum` with `B_sum = Σ B_i²` — the `1/N²`
with `Σ B_i²` is exactly what `I_i = I_cell·B_i/N` produces when summing `Σ I_i² R`.

The manuscript's own device-filter equation already states it correctly:
`I_D^LS ≥ I_cell·B_max/N`.

For the selected design all `B_i = 1` and `K = N = 3`, so

```
I_branch = I_cell/N = 20.4082/3 = 6.8027 A
```

which numerically equals `I_cell/K`. **That coincidence is what made the wrong name look
right.** It is a property of this design point, not of the architecture. A counterexample
from the same generator:

| N | K | K_A | K_B | B_array | branch currents |
|---:|---:|---:|---:|---|---|
| 3 | 3 | 2 | 1 | `[1, 1, 1]` | all equal, `I/3` |
| 4 | 3 | 2 | 1 | `[1, 2, 1]` | `I/4, I/2, I/4` — **unequal, and none is `I/K`** |
| 5 | 3 | 2 | 1 | `[2, 2, 1]` | `2I/5, 2I/5, I/5` |

So **6.8027 A is the per-inductor branch current**, and the phrase "per-phase current" must
not be used for it. Whether the two phase *groups* carry equal current depends on the
`B_i` distribution, not on K.

## 6. Is K_A free or derived?

Both, depending on where you look:

* `generate_B_array(N, K, K_A)` accepts **any** `K_A` — in the formulation it is a genuine
  architectural degree of freedom.
* `generate_architectures` **fixes** `K_A = ceil(K/2)` and skips `K_A ≥ K`, so the search
  as implemented explores only the balanced split.

For K = 3 that gives K_A = 2, K_B = 1. This should be stated as a **search
restriction**, not as a property of the topology.

## 7. The selected design

| quantity | correct physical meaning | value |
|---|---|---:|
| N | switched-capacitor branches; also the SC division ratio, `D = N·V_out/V_in` | 3 |
| K | **parallel inductor/low-side branches** (NOT phases) | 3 |
| K_A | inductor branches driven from the intermediate rail in **phase A** | 2 |
| K_B | inductor branches freewheeling in that state — **phase B** group | 1 |
| B_i | SC branches feeding inductor i; `Σ B_i = N` | `[1, 1, 1]` |
| **temporal switching phases** | **two** | **2** |
| HS devices | one per SC branch | 3 |
| LS devices | one per inductor branch | 3 |
| inductors | one per branch | 3 |
| flying capacitors | `N − 1` | 2 |
| intermediate rail | `V_in/N` | 16 V |
| duty ratio | `D = N·V_out/V_in` | 0.0625 |
| branch current | `I_cell·B_i/N` | 6.8027 A |

## 8. The two switching states

**Phase A** (duration `D/f_sw`, the modelled ON interval)
* the `ceil(N/2)` = 2 phase-A SC branches are ON, their high-side devices conducting;
* the `K_A` = 2 inductors fed by those branches are connected to the 16 V intermediate node and
  see `V_mid − V_out` = 15 V, so their current ramps **up**;
* the other `K_B` = 1 inductor(s) freewheel through their low-side device, seeing `−V_out`, so
  their current ramps **down**;
* the flying capacitors in the conducting branches transfer charge toward the intermediate node.

**Phase B**
* the complementary `floor(N/2)` = 1 SC branch(es) conduct;
* the `K_B` = 1 inductor(s) of group B are driven and the `K_A` = 2 group-A inductors freewheel;
* the flying capacitors reverse their charge/discharge roles, which is what balances them
  over a full cycle.

**What the implementation does NOT contain.** There is no time-domain model: no explicit
state sequence, no phase displacement, no dead time, and no per-state capacitor-voltage
solve. The two states are encoded only through the **multiplicities** `K_A` and `K − K_A`
in the ripple expression and through `B_sum` in the conduction loss. The A/B description
above is therefore the reading those multiplicities force, not a simulated waveform. Any
statement about the switching *sequence* or its timing is outside what this code supports.

## 9. Interleaving

The earlier audit asked whether "the three phases" are interleaved. The question was built
on the wrong premise. The correct question is whether the **two** phase groups are
interleaved, complementary, or merely two conduction states.

Evidence: no phase-shift variable, no timing, no dead time anywhere. The only
ripple-cancellation mechanism is coupled inductors,
`coupling_boost = 1 + k_c·(K−1)`, and the selected inductor has `k_c = 0.0`, so even
that is inactive.

**Allowed:** "two switching states", "two phase groups", "phase A / phase B".
**Not allowed:** "interleaved", "120-degree", "3-phase", "multiphase" as a temporal claim.

## 10. Correct naming

`D = N·V_out/V_in` with `N − 1` flying capacitors and two conduction states is the
**series-capacitor (Dickson-type) hybrid** relation, consistent with the cited
`DSCH`/`DPMIH44` family.

**Recommended wording:**

> a 3:1 switched-capacitor stage feeding a **two-phase buck stage with K = 3 parallel
> inductor branches**, of which K_A = 2 are driven in phase A and the remaining
> K_B = 1 in phase B

**Forbidden:** "3-phase buck", "three-phase buck", "phase count K", "per-phase current",
"auxiliary-branch count K_A", "interleaved".

## 11. parameter → meaning → evidence → wording

| parameter | meaning | evidence | allowed wording |
|---|---|---|---|
| N = 3 | SC branches / division ratio | `D = V_out·N/V_in`; `V_DS,max^HS ≥ V_in/N` | "a 3:1 switched-capacitor stage" |
| K = 3 | parallel inductor branches | `ls·K + inductor·K`; ripple `V_out·K` term | "K = 3 parallel inductor branches" |
| K_A = 2 | branches driven in phase A | ripple `V_in/N·K_A` term, verified exactly | "K_A = 2 branches driven in phase A" |
| K_B = 1 | branches freewheeling then | `K_B = K − K_A`; ripple derivation | "the remaining branch operates in phase B" |
| B_i | SC branches per inductor, `ΣB_i = N` | `generate_B_array`; `B_sum` in `P_cond` | "one SC branch per inductor" |
| phases | **2** | two multiplicity groups; `ceil/floor(N/2)` split | "two switching phases" |
| 6.8027 A | **branch** current `I_cell·B_i/N` | `I_D^LS ≥ I_cell·B_max/N` | "per-inductor branch current" |
