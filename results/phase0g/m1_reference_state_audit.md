# Phase 0G Sec. 11 — The stress-free reference state (M1) and what it does to the results

## 1. What every warpage number in this project actually is

All mechanical results in Phases 0B–0G are **incremental operational warpage**: the
stress-free reference temperature is the 25 °C operating ambient, so the computed deformation
is the change produced by going from a uniform 25 °C to the operating temperature field. It
therefore **excludes** the residual deformation locked in during assembly — die attach,
underfill cure, mould cure, reflow and cooldown to room temperature.

A real package leaves the assembly line already deformed. The state this project computes is
"additional deformation caused by turning the system on", not "deformation of the part".

This has been true since Phase 0B. It was never wrong, but it was never audited, and it
matters here because Sec. 7's conclusion is about a *mounted* package — precisely the state
in which assembly pre-stress is largest.

## 2. The audit

The reference temperature was raised to two representative cure/reflow states and the
decisive thickness pair re-run in both the free and the mounted configuration. This is a
**sensitivity bound, not a lifetime model**: it asks only whether assembly pre-stress can
change the design *ordering*.

| T_ref | assembly | W(0.80 mm) µm | W(2.00 mm) µm | S_h | ordering |
|---|---|---|---|---|---|
| 25 °C (as used throughout) | BC_A free | 11.1708 | 1.2719 | −0.8861 | thicker BETTER |
| 150 °C | BC_A free | 7.7920 | 0.3681 | −0.9528 | thicker BETTER |
| 175 °C | BC_A free | 11.5845 | 0.6833 | −0.9410 | thicker BETTER |
| 25 °C | BC_BOARD FR-4 1.6 mm | 25.1482 | 14.0309 | −0.4421 | thicker BETTER |
| 150 °C | BC_BOARD FR-4 1.6 mm | 28.0636 | 15.7245 | −0.4397 | thicker BETTER |
| 175 °C | BC_BOARD FR-4 1.6 mm | 38.7059 | 21.6755 | −0.4400 | thicker BETTER |

## 3. Findings

**(a) The thickness ordering is invariant to the reference state.** `S_h < 0` in all six
combinations. No reference temperature examined reverses the mechanical thickness preference,
in either assembly state. The Sec. 7 conclusion does not depend on the choice of stress-free
reference.

**(b) The mounted normalized response is remarkably stable.** For the explicit board,
`S_h` = −0.4421, −0.4397, −0.4400 across a 150 K span of reference temperature — a spread of
**0.5 %**. The relative thickness response is essentially a property of the assembly's
stiffness and CTE architecture, not of the thermal history.

**(c) Magnitudes are strongly reference-dependent, and grow.** Mounted warpage at
`h = 0.80 mm` rises from 25.1 µm to **38.7 µm** — a 54 % increase — as the reference moves
from 25 °C to 175 °C. Any absolute warpage figure quoted from this project is therefore a
*lower bound* on what a real assembly would exhibit, and by a wide margin.

**(d) The free package is non-monotonic in reference temperature** (11.17 → 7.79 → 11.58 µm).
That is not a numerical defect: raising the reference reverses the sign of the thermal
increment in the cooler regions of the package while the hot converter tiles remain above
reference, so the deformation field changes shape, not merely scale. It is reported because
it demonstrates that reference-state effects are not a simple multiplicative rescaling and
cannot be applied as a correction factor to existing results.

## 4. Consequences for the rest of the project

1. **Sec. 7's conclusion stands** — the assembly-state reversal is a BC-B artifact, and this
   holds at every reference temperature tested.
2. **No absolute warpage number in this project may be quoted as a predicted package
   warpage.** They are incremental operational values with a 25 °C reference and are up to
   54 % below the pre-stressed equivalent.
3. **The ε sweep is affected in level but not in structure.** Its ordering is preserved, but
   an ε chosen against 25 °C-reference numbers would be satisfied far less easily by a real
   pre-stressed assembly.
4. **This remains an M1 sensitivity bound, not a validated pre-stress model.** A real
   reference state requires the actual cure schedule, cure shrinkage, viscoelastic relaxation
   of the underfill and mould compound, and the reflow profile. None of those are available
   for the reference system, and none are modelled here.
