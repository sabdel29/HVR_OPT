# INTEGRATION-TOLERANCE ROBUSTNESS OF THE FINAL LOCAL SOLDER RESPONSE

Reproduce with `python scripts/phase0mr3c/cetol_robustness.py`
(needs `PATH=/home/beams0/MGHARIB/envs/etm/bin:$PATH` so `ccx` resolves).
Raw result: `manuscript/cetol_final_pair.csv`.

## 1. The question

The final pair is integrated at a creep strain-increment tolerance of `CETOL = 5e-2`, looser
than the `1e-2` used for the earlier, lower-stress Phase-0I cases. A reviewer may reasonably
ask whether the reported Z2 < Z1 inelastic-response ordering exists only because the
tolerance was relaxed.

## 2. What was varied, and what was not

**Only CETOL.** Geometry, mesh (`n_xy = 6`, `n_z = 8`), exclusion band, material card,
boundary conditions, stress-free reference (25 °C), joint temperature, `du_c`, dwell
(300 s), cycle count (4) and extraction code are the frozen final model, unchanged.

Tolerance ladder, with the provenance of each value:

| CETOL | where the value comes from |
|---|---|
| 1e-5 | `scripts/phase0l/calculix_creep_probe.py`, single-element creep probes |
| 1e-4 | `scripts/phase0jr/probe_viscoplastic.py` |
| 1e-2 | `scripts/phase0i`, `scripts/phase0ir` — the Phase-0I production joint |
| **5e-2** | `scripts/phase0jr`, `0kr`, `0lr`, `0m` — later production joint, and the value used for the final pair |
| 1e-1 | **not historical.** One step looser than production, included only so the production point is bracketed from above as well as from below |

## 3. Results --- every attempt, including the failures

| CETOL | case | converged | increments | cutback attempts | wall (s) | Δε_in /cycle | strain range | inelastic work (MJ m⁻³) | last-cycle change |
|---|---|:--:|---:|---:|---:|---:|---:|---:|---:|
| 1e-5 | Z1 | **NO** | 0 | 1 | 0.2 | — | — | — | — |
| 1e-5 | Z2 | **NO** | 0 | 1 | 0.1 | — | — | — | — |
| 1e-4 | Z1 | **NO** | 0 | 1 | 0.1 | — | — | — | — |
| 1e-4 | Z2 | **NO** | 0 | 1 | 0.1 | — | — | — | — |
| 1e-2 | Z1 | **NO** | 0 | 4 | 0.5 | — | — | — | — |
| 1e-2 | Z2 | **NO** | 0 | 5 | 0.6 | — | — | — | — |
| **5e-2** | Z1 | YES | 336 | 0 | 35.5 | 1.407235458008e-02 | 6.897569360219e-03 | 1.085302226729 | 0.0418 % |
| **5e-2** | Z2 | YES | 336 | 0 | 35.7 | 1.147820656641e-02 | 5.627656574727e-03 | 0.9309435708136 | 0.0557 % |
| 1e-1 | Z1 | YES | 336 | 0 | 36.0 | 1.407235458008e-02 | 6.897569360219e-03 | 1.085302226729 | 0.0418 % |
| 1e-1 | Z2 | YES | 336 | 0 | 35.6 | 1.147820656641e-02 | 5.627656574727e-03 | 0.9309435708136 | 0.0557 % |

Derived:

| CETOL | D_ε = Δε_in,Z1 / Δε_in,Z2 | Z2 reduction |
|---|---:|---:|
| 1e-5, 1e-4, 1e-2 | nonconverged | nonconverged |
| **5e-2** | **1.226006** | **18.43 %** |
| **1e-1** | **1.226006** | **18.43 %** |

    converged tolerances      2 of 5
    absolute Δε_in spread     0.00 % (Z1), 0.00 % (Z2)
    D_epsilon spread          0.00 %  (1.226006 to 1.226006)
    ordering Z2 < Z1          holds at every converged tolerance

## 4. The two converged solutions are bit-identical

At 5e-2 and 1e-1 the solver takes the **same 336 increments**, makes **zero cutbacks**, and
returns Δε_in, the strain range and the inelastic work identical to all twelve printed
digits, for both architectures. Doubling the tolerance changes nothing whatsoever.

The reason is visible in the increment counts: once CETOL is loose enough for the solve to
start, it is no longer the binding step-size control — the step schedule is. Below that
threshold the tolerance binds absolutely: at 1e-2 the solver makes four or five cutback
attempts and completes **zero** increments, and at 1e-4 and 1e-5 it abandons the first
increment immediately.

## 5. Conclusion --- outcome A, with a one-sided bracket

**ORDERING AND D_epsilon ARE NUMERICALLY STABLE OVER THE CONVERGED CETOL RANGE.**

The answer to the reviewer's question is direct: the result is not an artifact of relaxing
the tolerance, because relaxing it **further** changes the answer by exactly zero. Had the
solution been tolerance-driven, a factor-of-two change would have moved it.

**The bracket is one-sided and this must not be overstated.** No tolerance tighter than the
production value converges for this operating point, so the converged range cannot be
approached from below. The evidence establishes insensitivity to further relaxation; it does
not establish agreement with a hypothetical tight-tolerance solution, because none exists
within the evaluated ladder. That limitation is a consequence of the constitutive
extrapolation recorded in `FINAL_LOCAL_RESPONSE_AUDIT.md` §6 — the joint operates at 15–17×
yield against a card fitted over 7.51–15.92 MPa — and not of the integration scheme.

For scale: the already-reported local mesh sensitivity is 1.9 % on the absolute metric
between the two finest levels, and the architecture *ratio* is converged an order better
because the residual error is largely common mode. The CETOL contribution measured here is
0.00 % on both the absolute metric and the ratio.

## 6. What this does and does not license

* Licensed: "the ordering and the ratio are insensitive to the integration tolerance over
  the range in which the high-stress problem is numerically admissible."
* Licensed: reporting that tighter tolerances do not converge, with the counts above.
* **Not licensed:** any claim that the magnitude has been verified against a tight-tolerance
  reference. It has not, and none is obtainable here.
* Unchanged: the response magnitude remains conditional on a constitutive model evaluated far
  outside its fitted stress window.
