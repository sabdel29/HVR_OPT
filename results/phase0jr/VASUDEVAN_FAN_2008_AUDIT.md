# Phase 0J-R Sec. 17 — Vasudevan & Fan 2008: what it can and cannot do

## What it is

A **3-parameter modified Norris–Landzberg acceleration-factor model for lead-free SAC solder**,
fitted simultaneously to 17 pairs of thermal-cycle tests from Intel and published sources:

```
AF = N1/N2 = (f1/f2)^(-m) · (ΔT1/ΔT2)^(-n) · exp[ (Ea/k) · (1/T_max,1 − 1/T_max,2) ]

        m = 0.33        n = 1.9        Ea/k = 1414 K
```

| field | value |
|---|---|
| alloys | **SAC105, SAC305, SAC405** — includes our alloy |
| packages | FCBGA, socket, die-side capacitor, and published sets |
| dataset | **17 test pairs** |
| **reported error** | **average deviation < 6 %** |
| time variable | cyclic **frequency**, not dwell explicitly; an extended-cycle-time study to 480 min is reported separately |
| authors' own note | the fitted coefficients come out "very similar to the original values of the Norris-Landzberg model for Sn/Pb" |

## Sec. 17 — can it help with A, B or C?

| | question | answer |
|---|---|---|
| **A** | absolute lifetime | **NO.** It contains no mechanical metric. It relates one life to another life; it cannot turn an FEA strain or energy into a number of cycles. Confusing it with an FEA damage model is precisely what Sec. 17 warns against. |
| **B** | test-to-field acceleration | **YES, and this is its real value here.** Given a requirement stated at one condition, it converts that requirement to another condition with a SAC-specific, 17-pair, <6 %-deviation calibration that includes SAC305. |
| **C** | mission sensitivity | **YES.** It makes the parametric mission sweep physically meaningful rather than arbitrary, because a cycle count at one ΔT/frequency can be mapped to another. |

## The concrete use, and why it is held back

The single qualification datum Phase 0J found — **1000 cycles at −40/+125 °C** — is a
**category-A qualification requirement**, not a field mission. Sec. 21 forbids promoting it, and
it is not promoted. But this model now makes it possible to state, *if and when the system owner
supplies a real requirement*, exactly how to move it onto our cycle:

```
our cycle : ΔT = 57.9 K, T_max = 356.0 K, f = 144 cycles/day
JEDEC TC  : ΔT = 165 K,  T_max = 398.2 K, f = 24 cycles/day (1 h cycle)
```

That mapping is deliberately **not** evaluated into a number in this phase, because doing so
would create a pass/fail threshold out of a qualification count — the exact substitution Sec. 14
and Sec. 21 prohibit. The tool is documented, its parameters recorded, and it is handed to
Phase 0K together with the mission template.

## Verdict

**ADMISSIBLE, for its own purpose only.** It is not a life law and is not used as one. It is the
correct instrument for the *second* missing half of G2 — converting a stated requirement between
conditions — and it is the only supplied source whose alloy set explicitly includes SAC305.
