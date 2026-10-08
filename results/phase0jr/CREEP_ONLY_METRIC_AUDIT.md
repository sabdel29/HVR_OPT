# Phase 0J-R Sec. 4/6/7 — M4 (accumulated creep strain) and M5 (creep energy)

## Why a fourth and fifth metric were needed

Syed's `ε_acc` is **accumulated CREEP strain**, read from ANSYS `NL,CREQ`; his `w_acc` is
**creep** strain energy density from `SEND,CREEP`. Neither is plastic + creep. Sec. 6 forbids
feeding our PEEQ into his constant without proving the two are the same physical quantity.

## The proof — and it is an identity, not an approximation

A single-element probe (`scripts/phase0jr/probe_viscoplastic.py`) was run under **constant
uniaxial load** above the yield onset, with and without the `*PLASTIC` card:

| applied σ | `*PLASTIC`? | measured creep rate | `A·σⁿ` | `A·(σ−σ_y)ⁿ` | matches |
|---|---|---|---|---|---|
| 20 MPa | no | 4.6696e−06 | **4.6696e−06** | 4.9453e−11 | `A·σⁿ` |
| 20 MPa | **YES** | 4.9512e−11 | 4.6696e−06 | **4.9453e−11** | **overstress** |
| 25 MPa | no | 2.8002e−05 | **2.8002e−05** | 1.5222e−08 | `A·σⁿ` |
| 25 MPa | **YES** | 1.5154e−08 | 2.8002e−05 | **1.5222e−08** | **overstress** |
| 30 MPa | no | 1.2100e−04 | **1.2100e−04** | 4.1648e−07 | `A·σⁿ` |
| 30 MPa | **YES** | 3.8166e−07 | 1.2100e−04 | **4.1648e−07** | **overstress** |

and a second probe asked whether any **instantaneous** plastic strain appears at load
application, as a rate-independent model would require:

| applied σ | PEEQ at first output | PEEQ a rate-independent model would need | ratio |
|---|---|---|---|
| 25 MPa (σ_y = 15.2) | **1.52e−11** | 5.16e−02 | **0.0000** |
| 30 MPa (σ_y = 15.2) | **4.17e−10** | 7.79e−02 | **0.0000** |

**Conclusion: CalculiX's combined `*PLASTIC` + `*CREEP` is a pure viscoplastic OVERSTRESS
model.** The `*PLASTIC` card supplies only the threshold `σ_y(T, PEEQ)` in
`ε̇ = A(T)·(σ_eq − σ_y)^n(T)`. **There is no rate-independent plastic strain at all.** Every
increment of PEEQ is creep.

Therefore, for this constitutive model:

```
M4  ==  M1  ==  Δ(PEEQ) per stabilised cycle          identically, not approximately
M5  ==  M3  ==  the per-cycle inelastic work integral  identically
```

**M4 was computed, not estimated** — and the computation turned out to be an identity that the
probe established. That satisfies Sec. 4's "compute it, do not estimate" and Sec. 6's demand for
proof before PEEQ may be used.

### Independent corroboration from Syed himself

The appended ECTC deck reports the same conclusion for *his* model: with Wiese's law, creep
strain 0.4641 % vs 0.4629 %, **plastic contribution 0.125 % of strain and 0.225 % of energy**,
and the recommendation *"No need to model time independent plasticity for Thermal Cycle
simulations"*. Two different solvers and two different constitutive implementations agree that
the inelastic response of a SnAgCu joint under thermal cycling is creep.

### A cross-check that was tried and is reported as unusable

Before the probe, M4 was reconstructed by integrating the Norton law on the solver's own stress
and temperature output. In the Phase-0I core it validated at **M4/Δ(PEEQ) = 0.90–0.99** on the
creep-only decks and returned **exactly zero** on the plastic-only decks — both correct. In the
high-stress 25 µm interface layer the same integral **diverges by three orders of magnitude**,
because the rate goes as σ⁸ and the output-interval quadrature cannot resolve the initial
relaxation transient. The reconstruction is therefore kept as a corroborating check in the
core and **explicitly not used** for the reported numbers, which come from the solver directly.

## Two corrections to earlier phases

**1. "PEEQ = plastic + creep, inseparably" (Phase 0I-R) is refined.** True of the card contents;
misleading about the strain. There is nothing to separate — the inelastic strain is 100 % creep,
with the yield card acting only as the threshold.

**2. The Norton validity window is being used differently than Phase 0I assumed.** Phase 0I
bounded the card to the measured 7.5–16 MPa window and argued plasticity would cap σ_eq near
σ₀+C/γ. Measured here: the plastic-only deck caps **exactly** at 30.26 MPa, but the combined
deck sits at **median 55.8 MPa**, roughly twice its own yield surface — which is the correct
behaviour for an overstress model. The stress that enters the creep law is the **overstress**,
`σ_eq − σ_y ≈ 30 − 15 = 15 MPa` at the end of a hold, **inside** the fitted window. The card is
therefore being evaluated near its calibrated range, but the law has been re-purposed from a
total-stress creep law into an overstress law. **That is a model-form change relative to the
fit** and is recorded as a standing caveat.

## Values, with Syed's averaging volume

`creep_only_metric_by_architecture.csv`, stabilised cycle 5 of 6, mesh-converged (3.0–3.2 %
over the final refinement), stabilisation 0.32–0.56 %:

| architecture | **M4** (25 µm layers) | **M5** (MJ/m³) | M4 / Phase-0I core M1 |
|---|---|---|---|
| Z1 embedded | **8.5518e−3** | **1.0920** | 1.313 |
| Z2 backside | **6.6649e−3** | **0.9053** | 1.595 |
| Z4 power die | **8.9491e−3** | **1.1095** | 1.223 |

**Changing the averaging volume to Syed's changes the metric by 22–60 %, and it changes it
differently for each architecture.** That is why Sec. 5 required the match, and it is why the
Phase-0J relative-life figure moves (see `SYED_TRANSFERABILITY_AUDIT.md`).
