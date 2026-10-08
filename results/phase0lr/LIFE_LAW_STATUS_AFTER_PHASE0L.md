# Fatigue-law status after the Phase-0L constitutive findings

**Phase 0L-R, Part 13.** Phase 0J-R admitted four SnAgCu formulations for relative life. Phase 0L
then showed the response metric they consume is produced by a constitutive model extrapolated
far outside its source domain, on partly the wrong alloy. A life law cannot be more trustworthy
than the metric it is fed, so every admission is re-examined here.

## The principle being applied

Cancellation of the life-law constant is necessary but **not sufficient**. Writing
\(N_f = (C\,X)^{-k}\) for a response metric \(X\),

$$ \frac{N_{f,Z2}}{N_{f,Z1}} = \left(\frac{X_{Z1}}{X_{Z2}}\right)^{k} $$

the constant \(C\) drops out. What does **not** drop out is the ratio \(X_{Z1}/X_{Z2}\) itself.
If that ratio is produced by an untrustworthy constitutive model, the cancellation of \(C\) has
bought nothing. Phase 0J-R established the first half; Phase 0L put the second half in doubt;
this section resolves it metric by metric.

## What Phase 0L-R establishes about each metric

| metric | numerically converged? | evidence |
|---|---|---|
| **M1 accumulated inelastic strain** | **YES** | changes 0.27 % between the pre-0L and resolved integration controls |
| **M3 inelastic energy density** | **NO** | changes **+17.8 %** with integration control alone, and its architecture RATIO moves 5.5 % |
| M2 within-cycle range | not separately tested | — |

That asymmetry is not incidental. Damage is deposited in two brief stress spikes at the thermal
transitions (FIG-0LR-A); the energy integral \(\oint \sigma : d\varepsilon_{in}\) is dominated by
those spikes, and a coarse time step walks over them. The accumulated-strain metric is a
difference of endpoint values and does not care.

## Reclassification

| law | form | Phase 0J-R status | **Phase 0L-R status** | why |
|---|---|---|---|---|
| **Syed 2004 Eq.14** — accumulated creep strain | \(N_f = (0.0468\,\varepsilon_{acc})^{-1}\) | admitted for relative life | **CONDITIONAL RELATIVE LIFE** | metric is numerically converged and its architecture ratio is stable to 0.2 % across both integrable families; conditional only on the constitutive source domain |
| **Schubert 2003 strain** — slope 1.3 | \(N_f \propto \varepsilon^{-1.3}\) | admitted for relative life | **CONDITIONAL RELATIVE LIFE** | same metric; the higher exponent amplifies the same ratio, so it inherits the same standing |
| **Syed 2004 Eq.15** — accumulated creep energy | \(N_f = (0.0015\,w_{acc})^{-1}\) | admitted for relative life | **RANKING-ONLY USE** | the metric is not numerically converged (17.8 %) and its ratio moves 5.5 % with integration control alone. The SIGN survives everywhere; the magnitude may not be quoted |
| **Schubert 2003 energy** — slope 1.0 | \(N_f \propto w^{-1.0}\) | admitted for relative life | **RANKING-ONLY USE** | same metric, same defect |
| Darveaux | SnPb, 12.7 μm layers | never admitted | **INADMISSIBLE** | wrong alloy, wrong averaging volume, source's own factor-of-7 warning |

**No law is promoted to VALIDATED RELATIVE LIFE.** That would require the response metric to be
trustworthy in the domain where it is evaluated, and 99.8 % of the damage is generated above the
creep calibration window on partly the wrong alloy.

**No law is declared INADMISSIBLE UNDER CURRENT CONSTITUTIVE UNCERTAINTY either.** That would
require the constitutive uncertainty to be able to reverse the ordering, and Part 11 shows it
cannot within this framework: the global package supplies a constitutive-law-independent deformation driver favoring Z2, and every presently testable constitutive/life-law combination preserves that ordering.

## Consequence for how results may be quoted

- A **ranking** statement — "Z2 accumulates less damage than Z1" — is supported by all four laws,
  both integrable constitutive families and all three metrics, 12 ratios of 12 above unity.
- A **magnitude** statement may be quoted only from the strain family, and only as a conditional
  envelope. The energy family may be used for direction, not for a number.
- An **absolute life** statement is supported by nothing and remains unavailable.

The strain-family envelope at the operating baseline, across both integrable families and their
parametric perturbations, is **Z2/Z1 = 1.19 to 1.22** on Syed Eq.14, widening to 1.15–1.30 if the
energy family is included. Because the energy family is ranking-only, the defensible quoted
envelope is the strain one, and Part 14 fixes the wording that goes with it.
