# Why Z2 beats Z1 — the mechanism, not the ratio

**Phase 0L-R, Parts 11 and 12.** A ratio with no mechanical explanation is fragile to any change
of model. A ratio whose cause is identified can be argued about on physical grounds. This
section identifies the cause.

Artifacts: `z1_z2_cycle_histories.csv`, `damage_weighted_stress_distribution.csv`,
`high_stress_damage_fraction.csv`, `scripts/phase0lr/mechanism_audit.py`. All values are model
M1 at the operating baseline, stabilised cycle 5, volume-averaged over the 25 μm Syed layers.

## 1. The causal chain

| link | quantity | Z1 | Z2 | ratio Z1/Z2 | where it is computed |
|---|---|---|---|---|---|
| 1 | imposed corner shear Δu (μm) | 2.7486 | 2.0796 | **1.322** | **GLOBAL** thermoelastic model |
| 2 | peak σ_vm in the cycle (MPa) | 151.61 | 128.73 | 1.178 | local viscoplastic model |
| 3 | per-cycle Δ PEEQ | 0.011646 | 0.009727 | **1.197** | local viscoplastic model |

**The ordering is set in link 1, which contains no solder constitutive law at all.** Z2's
substrate is 0.30 mm against Z1's 1.30 mm; the thinner, less stiff stack warps into a smaller
relative displacement at the corner joint, and the global model that computes it is linear
thermoelastic. Links 2 and 3 then *compress* 1.322 to 1.197 — creep relaxation is sub-linear, so
a 32 % larger imposed displacement produces only a 18 % higher peak stress and a 20 % higher
per-cycle damage.

## 2. Why Z2 wins: lower peak, not lower mean

| quantity | Z1 | Z2 |
|---|---|---|
| peak σ_vm in cycle (MPa) | 151.61 | **128.73** |
| mean σ_vm over cycle (MPa) | 43.69 | 42.83 |
| peak hydrostatic stress (MPa) | 59.87 | **63.41** |
| fraction of cycle above 100 MPa | 8.3 % | **5.5 %** |
| damage accumulated in the first half-cycle | 45.2 % | 45.5 % |

Read together these rule out most of the candidate explanations:

- **Not a mean-stress effect.** The cycle-mean stresses differ by 2 %, the damage by 20 %.
- **Not a constraint or triaxiality effect.** Z2's hydrostatic stress is *higher*, which if
  anything works against it.
- **Not a temperature effect.** The joint temperatures differ by 1.0 K and the damage-versus-
  temperature correlation across the architecture set is r = +0.017.
- **Not a different cycle shape.** Both deposit 45 % of their damage in the first half-cycle and
  both peak at the same instant, the cold transition at t_frac = 0.500.

What is left is the peak and its duration: Z2's peak is 15 % lower and it spends **34 % less of
the cycle above 100 MPa**. With a stress exponent near 8, the high-stress excursions dominate the
integral, so a lower and shorter peak is exactly the lever that matters.

![FIG-0LR-A](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0lr/FIG_0LR_A_histories.png)

## 3. Do the two architectures occupy the same extrapolation region? — yes, closely

Damage-weighted stress distribution, weighting every element-increment by the solver's own PEEQ
increment (never by a reconstructed rate):

| percentile of damage-weighted σ_vm | Z1 (MPa) | Z2 (MPa) |
|---|---|---|
| p10 | 35.88 | 33.24 |
| p25 | 59.97 | 53.14 |
| **median** | **81.85** | **80.63** |
| p75 | 110.29 | 109.01 |
| p90 | 144.87 | 143.38 |
| p95 | 173.59 | 170.38 |
| max | 184.19 | 183.46 |

Damage fraction by stress bin:

| bin (MPa) | Z1 | Z2 |
|---|---|---|
| < 16 (the calibration window) | **0.22 %** | **0.18 %** |
| 16–30 | 5.92 % | 7.23 % |
| 30–50 | 12.73 % | 15.31 % |
| 50–75 | 21.44 % | 23.09 % |
| 75–100 | 23.82 % | 21.28 % |
| > 100 | 35.88 % | 32.90 % |

**This corrects a Phase-0L statement.** Phase 0L reported damage-weighted medians of 78 MPa (Z1)
and 72 MPa (Z2) and concluded that "Z1 and Z2 do not extrapolate identically", offering that as
the mechanism for incomplete cancellation. Those figures came from weighting a *layer-averaged*
stress by a *layer-averaged* damage increment. Weighted properly, element by element, the
medians are **81.85 and 80.63 MPa — 1.5 % apart**, and every percentile from p10 to the maximum
agrees within 12 %. The two architectures occupy very nearly the same extrapolation region, and
the earlier 78-versus-72 separation was an artifact of the coarser weighting.

What does differ is the top of the distribution: Z1 puts 35.9 % of its damage above 100 MPa
against Z2's 32.9 %. That is the same peak-stress effect as section 2, seen in the distribution.

**99.8 % of the damage in both architectures is generated above the 15.92 MPa top of the
calibration window.** Phase 0L's "100 %" was right to one significant figure.

## 4. Why this makes the ordering robust in a way a ratio alone is not

The ordering does not rest on the spread of a replay. It rests on two structural facts:

1. **The driver is upstream of the constitutive model.** Δu is produced by geometry and linear
   thermoelasticity. Within the current global/local decomposition the local solder law cannot
   change it, because the global model does not contain that law.
2. **Damage rises with imposed strain in every law tested.** Every viscoplastic law replayed
   here, and every candidate form retrieved from the literature, gives more accumulated
   inelastic strain for a larger imposed cyclic displacement at the same temperature and cycle
   shape. Reversing Z1 and Z2 would require a law that is *anti-monotone* in imposed
   displacement. No such candidate was found --- which is an absence of counterexamples over the
   laws this solver can integrate, not a proof over all laws.

So the question "could a different constitutive law reverse the ordering?" has a structural
answer: the global package supplies a constitutive-law-independent deformation driver favoring Z2, and every presently testable constitutive/life-law combination preserves that ordering. That is stronger than the
bare empirical answer "the four models we ran all agreed", and weaker than a theorem.

**The condition on that argument, stated plainly.** Fact 1 holds *by construction* in this
framework, not as established physics. The global model represents the BGA joints as linear
elastic, so the solder creep law genuinely cannot feed back into Δu. In reality a softer solder
would relax the global constraint and reduce Δu — for **both** architectures, since both have
the same joint material. A feedback that acts on both in the same direction shrinks the
difference but does not invert it. Establishing that quantitatively would need a global model
carrying the viscoplastic law, which this framework does not have and Phase 0L-R did not build.
