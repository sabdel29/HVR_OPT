#!/usr/bin/env python3
"""Phase-0M -- the mechanics audit, the coupling matrix and the PHASE 0M GATE document."""
from __future__ import annotations
import csv, math
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0m"


def rd(n):
    p = OUT / n
    return list(csv.DictReader(p.open())) if p.is_file() else []


def f(x, d=4):
    try:
        return f"{float(x):.{d}f}"
    except (TypeError, ValueError):
        return str(x) if x not in (None, "") else "--"


def g(x, d=4):
    try:
        return f"{float(x):.{d}g}"
    except (TypeError, ValueError):
        return str(x) if x not in (None, "") else "--"


# ============================================================ mechanics audit
def mechanics_audit() -> None:
    poly = rd("polymer_modulus_screen.csv")
    pre = rd("assembly_prestress_test.csv")
    mat = rd("PHYSICS_PRIORITY_MATRIX.csv")
    fb = rd("etm_feedback_magnitudes.csv")
    pre_ok = [r for r in pre if r.get("status") == "OK" and r["arch"] in ("Z1", "Z2")]
    ratio_row = next((r for r in pre if r["arch"] == "RATIO"), None)
    worst = max((r for r in poly if r["case"] != "baseline"),
                key=lambda r: abs(float(r["ratio_shift_pct"])), default=None)
    md = f"""# PHASE 0M PARTS 27-33 --- MISSING-MECHANICS PHYSICS AUDIT

## What each term means, for a reader who is not a mechanician

**RATE-INDEPENDENT PLASTICITY.** Permanent deformation set by how hard you push, not how
long. Push past the yield stress and the metal takes a permanent set immediately; hold the
load and nothing more happens.

**CREEP / VISCOPLASTICITY.** Time- and temperature-dependent irreversible deformation. Hold
a solder joint at 85 C under load and it keeps deforming. This is what the project models.

**VISCOELASTICITY.** Time-dependent deformation that can RECOVER. A polymer loaded and then
unloaded springs back slowly rather than instantly. It is not damage and it is not
plasticity; it changes how much load a stiff member passes to a soft one, and how that
changes with dwell time.

**ASSEMBLY PRESTRESS / RESIDUAL STRESS.** Stress already present before the product is ever
switched on, left over from reflow, cure, cool-down and board attach. The joint does not
start at zero.

**DAMAGE.** Progressive degradation of stiffness or strength: the material gets weaker as it
is cycled, before anything visibly breaks.

**COHESIVE DELAMINATION.** Two bonded surfaces separating, governed by a traction-separation
law and a fracture energy rather than by a stress limit.

**CONTACT.** An interface that can open, close, slide, or conduct differently depending on
how hard it is pressed together.

**MOISTURE.** Water diffusing into polymers, swelling them, softening them, and degrading
adhesion; at reflow it can flash to steam and blow an interface apart.

## The physics matrix

| | mechanism | status | priority | effect size |
|---|---|---|---|---|
{chr(10).join(f"| {r['id']} | {r['physics']} | **{r['status']}** | **{r['priority']}** | {r['effect_size']} |" for r in mat)}

Ten of twelve mechanisms are NOT MODELLED. That is not a scandal --- most of them should not
be modelled yet --- but it must be stated plainly and it is, in both reports.

## Part 30 measured --- does polymer stiffness matter?

The organic board, the underfill and the TIM are linear elastic with one modulus each. If
their stiffness is wrong or time-dependent, the displacement TRANSFERRED to the solder joint
is wrong, and that displacement is the single input the whole reliability chain reads.

| case | du Z1 | du Z2 | Z1/Z2 ratio | du Z1 shift | ratio shift |
|---|---|---|---|---|---|
{chr(10).join(f"| `{r['case']}` | {f(r['du_Z1_um'], 4)} um | {f(r['du_Z2_um'], 4)} um | {f(r['du_ratio_Z1_over_Z2'], 4)} | {f(r['du_Z1_shift_pct'], 2)} % | {f(r['ratio_shift_pct'], 2)} % |" for r in poly)}

**The board dominates and the underfill and TIM do not.** Halving the board modulus moves
the Z1 corner shear by about 12 % and the Z1/Z2 ratio by about 3 %; halving the underfill
modulus moves the ratio by less than 0.05 %. The TIM is nearly irrelevant because it is
already two orders of magnitude softer than everything around it.

Three percent on the ratio is not negligible against a relative-life envelope of 1.19 to
1.22, which itself spans 2.5 %. So **board stiffness is a first-order input to the driver**,
and a linear-elastic laminate at one temperature is an approximation the framework has never
tested. It is classified **P1** rather than P0 for one reason: the effect is common-mode ---
both architectures move the same way and the ORDERING is untouched at every modulus tried.

What is NOT settled is the TIME dependence. Modulus scaling is a proxy for it and a
conservative one; a real Prony series would also change the DWELL response, which is where
the creep strain accumulates. No DMA data for the specific laminate is available in this
repository, so a Prony series cannot be fitted here.

## Part 31 measured --- does assembly prestress change the stabilised cycle?

The operational model is stress-free at the cycle minimum. The real joint is stress-free near
reflow, about 217 C, and arrives at room temperature already loaded. Tested by prepending a
reflow cool-down and comparing the STABILISED cycle, which is the only thing the life law
reads.

| architecture | reference state | d(PEEQ)/cycle | inelastic work | stabilisation | shift |
|---|---|---|---|---|---|
{chr(10).join(f"| {r['arch']} | {'reflow 217 C' if r['reflow'] in ('True', True) else 'cycle minimum'} | {f(r.get('d_peeq_per_cycle'), 6)} | {f(r.get('inelastic_work_MJ_per_m3'), 5)} | {f(r.get('stab_pct'), 3)} % | {f(r.get('dpeeq_shift_pct'), 2) if r.get('dpeeq_shift_pct') else '--'} % |" for r in pre_ok)}

{"**The Z1/Z2 ratio moves from " + f(ratio_row['d_peeq_per_cycle'], 4) + " to " + f(ratio_row['inelastic_work_MJ_per_m3'], 4) + ", a shift of " + f(ratio_row['dpeeq_shift_pct'], 2) + " %.**" if ratio_row else "**Ratio comparison unavailable.**"}

## Part 29 --- is rate-independent plasticity needed?

**No, and adding it would double-count.** The selected model M1 is a pure overstress
viscoplastic law with the yield surface removed; Anand and Norton both represent the TOTAL
inelastic strain, with no separate rate-independent branch to add. A unified law that already
reproduces the measured creep data cannot also be given an independent plastic strain without
counting the same deformation twice.

Classification: **LOW PRIORITY FOR CURRENT RANKING.** It becomes relevant only if a life law
is adopted whose calibration separates the two branches, in which case the model form must
match the law's, not the other way round.

## Part 32 --- moisture

**OUT OF SCOPE, stated explicitly.** The publication claim is DRY STEADY OPERATING ETM. No
humidity, storage or MSL requirement exists in any supplied source or in this repository.
Moisture becomes **P1 the moment such a requirement appears**, and the branch is named here
so that it is a decision rather than an omission.

## Part 33 --- damage, crack growth and delamination

Fatigue-life CORRELATION and explicit DAMAGE SIMULATION are different things and the project
does the first. The correlation ranks architectures without propagating a crack. Explicit
damage becomes necessary only if the framework must predict a crack path, a delamination
area, a stiffness knockdown, an electrical open or a thermal-contact degradation. The
first-order sizes are in `etm_feedback_magnitudes.csv`:

| mechanism | at | effect |
|---|---|---|
{chr(10).join(f"| {r['mechanism']} | {r['quantity']} | {g(r['value'], 4)} ({r['verdict']}) |" for r in fb if 'crack' in r['mechanism'] or 'delam' in r['mechanism'])}

25 % of a joint's area lost is worth a 33 % resistance rise --- 1.5x the whole
resistivity-versus-temperature effect. 25 % of the die delaminated is worth 12.5 K. Both are
large. Neither exists before damage does.

**Cohesive zones are NOT added**, because the brief's own rule bites: the traction-separation
laws and interface fracture energies for these interfaces are not sourced, and inventing them
would put a fabricated parameter at the centre of a failure prediction.
"""
    (OUT / "MISSING_MECHANICS_PHYSICS_AUDIT.md").write_text(md)


# ============================================================ coupling matrix
def coupling_matrix() -> None:
    fb = rd("etm_feedback_magnitudes.csv")
    lv = rd("etm_coupling_levels.csv")
    md = f"""# PHASE 0M PARTS 34-37 --- THE ETM COUPLING MATRIX

## The matrix

| from \\ to | ELECTRICAL | THERMAL | MECHANICAL | DAMAGE |
|---|---|---|---|---|
| **ELECTRICAL** | -- | **PRESENT** loss -> heat, iterated to a fixed point | indirect, through T | absent |
| **THERMAL** | **PRESENT** rho(T), R_DS(on)(T), DCR(T) | -- | **PRESENT** thermal strain drives the global and local mechanics | indirect, through M |
| **MECHANICAL** | **ABSENT** --- measured at 0.16 % of R | **ABSENT** --- measured at 1.5 K for a 4 % bond-line change | -- | **ABSENT** no damage variable exists |
| **DAMAGE** | **ABSENT** --- would be +33 % R at 25 % joint area lost | **ABSENT** --- would be +12.5 K at 25 % delaminated | **ABSENT** | -- |

## Every absent arrow, with a number

| direction | mechanism | quantity | value | against | ratio | verdict |
|---|---|---|---|---|---|---|
{chr(10).join(f"| {r['direction']} | {r['mechanism']} | {r['quantity']} | {g(r['value'], 4)} | {g(r['ref_value'], 4)} | {g(r['ratio'], 3)} | **{r['verdict']}** |" for r in fb)}

## Part 35 --- when does mechanics feed back electrically?

**Not before damage, by more than two orders of magnitude.** A free thermal expansion of
9.7e-4 over the operating excursion changes a conductor's resistance by
`eps (1 + 2 nu) = 0.16 %`. Over the same excursion `rho(T)` changes it by **22.8 %**, and
that term IS modelled. The geometric feedback is 0.7 % of a term already in the loop, and
far below the 2.4x spread in the current-crowding factor measured in Part 8.

Contact-pressure feedback does not apply: every current-carrying interface in this package is
metallurgical. There is no pressure contact in the power path.

Electromigration voiding is **OPEN, not negligible** --- the EM current-density limit itself
could not be sourced, so its resistance drift cannot be estimated and must not be invented.

**Conclusion: retain ONE-WAY mechanics. An iterative M -> E loop would consume solver time
to chase a term 137x smaller than one already present.**

## Part 36 --- when does mechanics feed back thermally?

**Second order, but not zero, and for a reason worth recording.** At the calibrated
`h = 166 kW/m2K` the convective resistance is 0.0121 K/W while the 50 um TIM contributes
0.0333 K/W: **the compliant polymer layer, not the cooler, dominates the junction-to-coolant
path.** A 4 % change in the bond line is therefore worth 1.5 K, or 2.9 % of the junction rise.

Not enough to justify an iterative loop for the intact package. Enough that TIM bond-line
thickness belongs in the cooling design-variable set, which Part 24 places it in.

With damage it is a different question: 25 % delamination is 12.5 K, which would change the
converter loss, the temperature, and the mechanics in turn.

## Part 37 --- "fully coupled ETM", defined

| level | definition | status | necessary for |
|---|---|---|---|
{chr(10).join(f"| **{r['level']}** | `{r['definition']}` | {r['status']} | {r['sufficient_for']} |" for r in lv)}

**Where this project is: ETM-L1.** E and T are iterated to a fixed point; T drives M; M
returns nothing.

**What each goal needs:**

* **architecture RANKING --- ETM-L1 is sufficient.** The absent arrows are 0.7 % and 2.9 % of
  terms already present, and they are common-mode across architectures.
* **absolute LIFETIME --- ETM-L1 is sufficient for the mechanics, and insufficient for other
  reasons.** The blockers are the high-stress constitutive response, the absence of a
  required life, and process history --- not the coupling direction.
* **failure PROGRESSION --- ETM-L3 is required.** Predicting what happens after a crack
  starts needs damage feeding back into conductance and stiffness. Nothing less will do, and
  nothing in this project currently does any of it.

A staggered iterative solution would be acceptable at L2 or L3; a monolithic multiphysics
solve is not required, and would be a poor use of effort given the feedback magnitudes above.
"""
    (OUT / "ETM_COUPLING_MATRIX.md").write_text(md)
    print("  wrote MISSING_MECHANICS_PHYSICS_AUDIT.md, ETM_COUPLING_MATRIX.md")


if __name__ == "__main__":
    mechanics_audit(); coupling_matrix()
