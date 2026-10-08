# Phase 0J-R Sec. 22 — What the system owner must supply

Phase 0J-R closes the **left** side of `N_f(x) ≥ N_required`. The right side cannot be closed by
any amount of further modelling or literature work: it is a **property of the product**, not of
the physics. This is the minimal set of inputs that would turn a predicted fatigue capability
into a pass/fail constraint.

**Nothing below is assumed, defaulted or invented anywhere in this project.**

---

## A. Required life — the one blocking input

| # | input | units | why it is needed | if unknown |
|---|---|---|---|---|
| A1 | **Expected service lifetime** | years | sets the horizon | no substitute |
| A2 | **Required survival probability at that lifetime** | % of population | Syed's models predict **MEAN** life; a B1 or B10 target needs the Weibull slope (his data average β ≈ 11, range 6–20) | state the target; β can be taken from his dataset with the spread reported |
| A3 | **Is the target a field mission or a qualification gate?** | category | Phase 0H category B vs A. They are not interchangeable and this project will not convert one into the other silently | must be stated |

## B. The load spectrum — what actually cycles the joint

The damage metric is per **thermal excursion of the joint**, so the count that matters is the
number of excursions, not hours of operation.

| # | input | units | why it is needed |
|---|---|---|---|
| B1 | **Cold boots per day** (full OFF → ON, ambient → operating) | count/day | the largest-ΔT cycle; dominates damage |
| B2 | **Workload power cycles per day** and their **depth** | count/day and ΔP or ΔT | the many-small-cycles population; Syed explicitly warns that for small field ΔT the low-stress creep mechanism can become significant, which the total-strain form does not resolve |
| B3 | **Typical high-power dwell** | s or min | measured here to change M4 by only +17–22 % over 30 s → 900 s, so a coarse estimate suffices |
| B4 | **Typical low-power (idle) dwell** | s or min | as above |
| B5 | **Duty-cycle profile** if B1/B2 vary seasonally or by deployment | histogram | otherwise a single representative spectrum |

## C. The temperature environment

| # | input | units | why it is needed |
|---|---|---|---|
| C1 | **Inlet / ambient air temperature distribution** | °C | sets T_min of every cycle; currently assumed 25 °C |
| C2 | **Operating junction or case temperature target** | °C | sets T_max; currently computed as 81.1–83.2 °C at the joint |
| C3 | **Whether the system is ever fully powered down** | yes/no | if not, the true ΔT is far smaller than 58 K and the damage is far lower |
| C4 | **Shipping / storage excursions** | °C, count | often the largest ΔT a datacenter part ever sees |

## D. Qualification context, if any

| # | input | units | why it is needed |
|---|---|---|---|
| D1 | Applicable qualification spec and condition | e.g. JESD22-A104 −40/+125 °C, 1000 cycles | can be converted onto the operating cycle using the **Vasudevan & Fan 2008** SAC acceleration model (m = 0.33, n = 1.9, Ea/k = 1414 K, <6 % on 17 pairs), which is in hand |
| D2 | Whether qualification passing is sufficient, or field life must be shown separately | policy | determines whether D1 is the requirement or merely a gate |

---

## What can be delivered the moment A1–A3 and B1–B2 arrive

1. `N_required` in **joint thermal cycles**, from the spectrum.
2. `N_f` for Z1, Z2 and Z4 — **relative** values are already validated; **absolute** values
   would remain conditional for the reasons in `SYED_TRANSFERABILITY_AUDIT.md`.
3. A G2 evaluation: whether the reliability inequality changes the feasible architecture set.
4. The **mission-life crossover**: the band of `N_required` in which Z2's +1.688 W buys
   feasibility rather than merely margin.

## What would still be missing

An **absolute** pass/fail would additionally need one of:

* a SAC305 (not SAC405/SAC387) calibration, **or**
* a calibration on a package whose `w_acc/ε_acc` is near our 124–136 MPa rather than Syed's
  28.8–30.0 MPa, **or**
* one measured life for **this** joint at **one** condition, which would fix the constant
  directly and make every relative result absolute at a stroke.

The third is by far the cheapest. **A single board-level thermal-cycle test of the actual DVPD
package would convert the whole of this phase's relative result into an absolute one.**
