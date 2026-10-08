# Phase 0I Sec. 6/7 — Thermal topology and transient response, per architecture

## 1. Heat is mapped to where the architecture actually puts it

Moving the converter in z moves its dissipation. Each architecture is meshed with the
converter as a distinct material layer in its own position, so the temperature field is solved
for that geometry rather than inherited:

| architecture | converter layer position | die heat | converter heat |
|---|---|---|---|
| Z1 EMBEDDED | tile band **inside** the substrate | 1000 W at the die | 125.3 W inside the substrate |
| Z2 BACKSIDE | layer **below** z = 0, between the BGA field and the substrate | 1000 W at the die | 125.3 W below the substrate |
| Z4 POWER DIE | layer **above** the substrate, beneath the compute die | 1000 W at the die | 125.3 W in the die-to-cooler path |

June-2026 supplies the split that makes this matter: *"more than 70 % of conversion losses
originate from power switches, making them the primary source of heat dissipation, with
temperatures exceeding 100 °C"*. The converter is a concentrated source, not a diffuse one.

## 2. Cooling, per architecture

| architecture | cooling surface | conflict |
|---|---|---|
| Z1 EMBEDDED | substrate-embedded micro-channels (June-2026 Sec. IV-D), modelled as the Phase-0F calibrated Robin boundary on the TIM top surface | none |
| Z2 BACKSIDE | same top boundary. A backside cold plate is **not** available: the converter occupies the board side, where the BGA field already is | the converter has no independent cooling access once the package is mounted |
| Z4 POWER DIE | same top boundary, but the converter now sits **inside the die-to-cooler path** | its heat must pass through the compute die to reach the cooler |

The same calibrated top boundary is used for all three so that the architectures are compared
on geometry rather than on a cooling assumption that differs between them. Phase 0H already
bounded the cooling-topology model form: swapping to substrate-side cooling changes magnitudes
by up to 45 % and flips no sign.

## 3. Result: the architectures barely differ in joint temperature

| architecture | h* (mm) | T_max (°C) | **T_joint (°C)** |
|---|---|---|---|
| Z1 EMBEDDED | 1.30 | 84.97 | **82.86** |
| Z2 BACKSIDE | 0.30 | — | **81.85** |
| Z4 POWER DIE | 0.30 | — | **81.10** |

Across every architecture and thickness run, the corner-BGA joint temperature spans only
**81.10–83.21 °C**. Two things follow, and the second is the important one:

1. Z4's converter-in-the-thermal-path concern does **not** materialise at the joint. The
   converter is 125 W against the die's 1000 W, and the BGA joint is thermally far from both.
2. **Temperature is not the discriminator between these architectures.** The correlation
   between joint temperature and the damage metric across all 11 runs is **r = +0.017**. The
   architectures separate on *mechanics*, not on *temperature*.

That is a negative result worth stating plainly, because the phase was set up expecting
z-placement to move the thermal field, and at the joint it does not.

## 4. Transient capability (Sec. 7)

Transient thermal was added **without modifying shared code**: `etm.ccxio.write_thermal()` is
used by every phase since 0B and by 189 tests, so the validated steady-state deck it produces
is transformed in `scripts/phase0i/transient.py` instead — `*DENSITY` and `*SPECIFIC HEAT`
appended per material, `*HEAT TRANSFER, STEADY STATE` replaced by a time-stepped
`*HEAT TRANSFER`, output on an explicit `*TIME POINTS` list.

`rho·cp` is a **declared handbook assumption** (`configs/phase0i/thermal_transient.yaml`). It
changes how fast the field arrives and never where it arrives.

### Validation

| run | end time | output frames | T_max at end | vs the validated steady solver | fitted τ | t₉₅ |
|---|---|---|---|---|---|---|
| A | 60 s | 40 | 54.78 °C | −35.6 % | 14.9 s | 48.2 s |
| B | 900 s | 40 | 78.75 °C | −7.43 % | 261.8 s | 723 s |
| C | **6000 s** | 40 | **84.98 °C** | **−0.110 %** | 606.2 s | 1618 s |

**The transient converges to the steady-state answer to 0.110 %**, which is the check that
matters: the added `rho·cp` has not altered the physics, only the path to it.

### The response is two-mode

The fitted time constant grows with the observation window — 14.9 s over the first minute,
606 s over the full approach — because there are two thermal masses: a fast silicon
package mode of order 15 s and a slow FR-4 board mode of order 10 minutes. A single
exponential does not describe it, and reporting one τ would be wrong.

**Consequence for the damage assessment:** a dwell must exceed roughly **1600 s (t₉₅)** for
the joint to be at its steady temperature. The cycles used in Sec. 16 apply the full
steady-state temperature difference directly, which is the `t → ∞` limit of that excursion and
therefore the **worst case** for the thermal component of the load. Shorter dwells would see
a smaller temperature swing at the joint, not a larger one.

## 5. Thermal cycle definition, and what is NOT claimed

The excursion used is the system's own **power cycle**: OFF at the 25 °C ambient, ON at the
computed steady joint temperature. No mission profile is invented, and none exists for the
reference system. The **number** of such cycles a product must survive is unknown, so Sec. 20
sweeps it parametrically rather than declaring a requirement.

Accelerated-test profiles (0/100 °C, −40/125 °C and similar) are deliberately **not** used as
operating conditions. They are qualification conditions and Sec. 29 forbids treating them as
mission profiles.
