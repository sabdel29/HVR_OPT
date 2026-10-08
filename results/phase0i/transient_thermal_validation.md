# Phase 0I Sec. 7 — Transient thermal validation

## 1. What was added, and how

Every thermal solve from Phase 0B to 0H was steady state, so the stack carried thermal
conductivity but no `rho·cp`. Transient capability was added **without touching shared code**:
`etm.ccxio.write_thermal()` is used by every phase and by 189 tests, so the validated
steady-state deck it produces is transformed in `scripts/phase0i/transient.py`:

* `*DENSITY` and `*SPECIFIC HEAT` appended to each `*MATERIAL` block,
* `*HEAT TRANSFER, STEADY STATE` → a time-stepped `*HEAT TRANSFER`,
* output on an explicit `*TIME POINTS` list.

`FREQUENCY` was tried first and is wrong here: it counts *increments*, and with adaptive
stepping it produced a single frame at the end.

`rho·cp` values are **declared handbook assumptions**
(`configs/phase0i/thermal_transient.yaml`), not values from the reference system. They set how
fast the field arrives and never where it arrives.

## 2. Validation: the transient must reproduce the steady solver

Package: ARCH_Z1_EMBEDDED, `h_sub` = 1.30 mm, 1000 W die + 125.3 W converter, 20 203 elements.
Validated steady solver: **T_max = 85.0753 °C**, energy residual −3.06 × 10⁻⁵ %.

| run | end time | frames | T_max at end | **error vs steady** | fitted τ | t₉₅ |
|---|---|---|---|---|---|---|
| A | 60 s | 40 | 54.78 °C | −35.615 % | 14.9 s | 48.2 s |
| B | 900 s | 40 | 78.75 °C | −7.433 % | 261.8 s | 723 s |
| C | 6000 s | 40 | **84.98 °C** | **−0.110 %** | 606.2 s | 1618 s |

**The transient converges to the steady-state field to 0.110 %.** The added `rho·cp` changes
the path and not the destination, which is the only property required of it here.

## 3. The response is two-mode, and one τ would misreport it

The fitted time constant grows with the observation window — 14.9 s over the first minute,
261.8 s over fifteen, 606.2 s over the full approach. That is not a fitting artefact: there
are two thermal masses in series, a fast silicon package mode of order 15 s and a slow FR-4
board mode of order 10 minutes. Quoting a single τ would be wrong, so both are reported.

## 4. What this licenses, and what it does not

**Licenses:** the dwell length used in the damage cycles. The joint needs roughly **t₉₅ ≈
1600 s** to reach its steady temperature. Sec. 16 applies the full steady-state temperature
difference, which is the `t → ∞` limit and therefore the **largest** thermal swing the joint
can see in a power cycle. A shorter dwell gives a smaller swing, not a larger one, so the
damage numbers are the conservative end of the dwell axis.

**Does not license:** any claim about cycle *count*, ramp rate, or a mission profile. None of
those exists for the reference system and none is invented. Sec. 20 sweeps the required life
parametrically instead.

Artifact: `transient_thermal.json` (full T_max history for all three runs).
