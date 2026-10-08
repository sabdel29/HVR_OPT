# Phase 0I Sec. 8/9 — Failure mechanism selected, and its constitutive model sourced

## 1. Which mechanism, and which joint

**Mechanism: solder / bump thermomechanical fatigue.** Selected per Sec. 8 because it
directly experiences package deformation, its material response is strongly temperature
dependent, it can be tied to a local strain measure, and it is the mechanism with the deepest
packaging literature.

**Which joint?** Determined per architecture rather than assumed:

| candidate | Z1 | Z2 | Z4 | why |
|---|---|---|---|---|
| **BGA (package → board)** | **critical** | **critical** | **critical** | 400 µm solder ball at up to 15 mm from the neutral point, between silicon (2.6 ppm/K) and FR-4 (~18 ppm/K) — the largest CTE mismatch and the largest distance in the assembly |
| microbump / chiplet pad | no | no | no | 10 µm Cu pad between silicon and silicon; the mismatch is small and the standoff tiny |
| Cu pillar (GaN attach) | no | no | no | inside the converter cell, short DNP |
| hybrid bond (Z4 power die → compute die) | n/a | n/a | no | silicon-to-silicon, essentially no mismatch |

The BGA is critical in all three, so the same joint is compared across architectures — which
is what makes the comparison meaningful.

## 2. What was searched, and what was reachable

479 works were harvested through OpenAlex across ten targeted queries (Anand parameters,
Garofalo creep, Norton creep, temperature-dependent modulus, Darveaux, strain-energy life
laws, Coffin-Manson, microbump fatigue, submodelling, volume averaging). Publisher access in
this environment is uneven: MDPI, IOP, Elsevier, OUP and MATEC return HTTP 403; PMC, Hindawi,
Springer, Frontiers and institutional repositories serve.

## 3. The parameter set actually adopted — SAC305 only

**No parameter is taken from a different alloy.** SnAgCuCe and SAC405 Anand sets were found
and **rejected on that basis alone**.

| property | value | status | source |
|---|---|---|---|
| creep law | Garofalo `ε̇ = C1[sinh(C2σ)]^C3 exp(−Q/RT)`, Q = 62 000 J/mol, C1 = 0.184, C2 = 0.221 /MPa, C3 = 2.89 | **SOURCED** | Xiao & Armstrong, tabulated by Yuan (2023) *Materials* 16(14):4922 Table 27 |
| creep data | 19 measured steady-state points at 45, 80, 115, 150 °C, 7.51–15.92 MPa | **PRIMARY DATA** | Yuan (2023) Table 26 |
| yield σ₀(T) | 39.32 / 33.80 / 21.35 / 15.43 / 10.50 MPa at −40 / −20 / 40 / 80 / 122 °C | **SOURCED** | Yuan (2023) Table 31, Chaboche fit |
| hardening | Chaboche C, γ; saturation stress σ₀ + C/γ | **SOURCED** | same table |
| E(25 °C) | 40–50 GPa band, 45 GPa adopted | **SOURCED range** | Paska et al. (2024) *Appl. Sci.* 14(2):604 |
| dE/dT | −120 MPa/K | **ASSUMPTION** | no temperature dependence found in an accessible source |
| CTE | 21.5 ppm/K | **ASSUMPTION** | not sourced in this phase |

### Cross-checks that were available, and passed

* **Yield.** Paska et al. measured SAC305 Rp0.2 = 23.3–25.6 MPa at room temperature. This
  model gives σ₀(25 °C) = **24.46 MPa**.
* **Activation energy.** Fitting the solver's own Norton law to the raw creep points and then
  extracting the apparent activation energy at fixed stress returns **64.4 kJ/mol at 10 MPa**
  (71.7 at 8 MPa, 58.5 at 12 MPa), against the published Garofalo **62.0** (Xiao & Armstrong)
  and **65.0** (Yuan's re-fit). The independently fitted card reproduces the literature value.

## 4. Why Anand was not used, although a SAC305 set exists

Yuan (2023) Tables 28 and 30 give SAC305 Anand coefficients. **CalculiX 2.23 has no Anand
model**, and a user creep subroutine would require recompiling the solver. Sec. 9 forbids
using a model because it is popular; the reverse also applies — a parameter set that the
solver cannot evaluate is of no use, and importing it would have meant pretending.

## 5. Why the Norton card is fitted to data rather than to Garofalo

CalculiX implements `*CREEP, LAW=NORTON`, `ε̇ = A σⁿ tᵐ`. A single power law cannot represent
Garofalo across a wide stress range: the effective exponent of the sourced law runs from
**3.1 at 2 MPa to 19.2 at 30 MPa**, and a global fit over 1–30 MPa has **253 % RMS error**.
Narrowing helps only when the window is very tight (≤ 18 % RMS at a 1.5× stress span).

The resolution is to fit the solver's law **directly to the 19 measured points**, whose stress
range 7.51–15.92 MPa is exactly where a joint operates once rate-independent plasticity has
capped the stress at σ₀ + C/γ (30.3 MPa at 25 °C falling to 13.0 MPa at 125 °C):

| T (°C) | points | window (MPa) | A | n | max err | **RMS err** |
|---|---|---|---|---|---|---|
| 45 | 4 | 10.54–15.92 | 4.113e−18 | 8.295 | 13.03 % | **12.17 %** |
| 80 | 5 | 10.43–14.46 | 2.723e−17 | 8.186 | 14.80 % | **9.75 %** |
| 115 | 5 | 8.73–12.41 | 1.934e−15 | 7.240 | 6.17 % | **4.11 %** |
| 150 | 5 | 7.51–11.52 | 3.059e−12 | 5.075 | 7.90 % | **5.71 %** |

Intermediate temperatures are obtained by Arrhenius interpolation **of the creep rate at a
reference stress**, with the exponent interpolated separately. Interpolating `ln A` against
`1/T` directly is wrong here because `A` absorbs the temperature-dependent exponent as well as
the Arrhenius factor; doing so returns an apparent 139 kJ/mol against a literature 62–65.

**Validity is bounded and stated: 7.5–16 MPa.** Outside that window the Norton surrogate is
not claimed to represent SAC305.

## 6. Life relation: NOT ADMITTED

No SAC305 `N_f = f(Δε_in)` or `N_f = f(ΔW)` relation could be read. The two candidate
open-access sources — a MATEC creep-strain-energy-density study and an accelerated-cycling
characteristic-life dataset — both return HTTP 403 to publisher servers here.

Consequently **no lifetime is predicted anywhere in this phase**. Sec. 20 reports the damage
metric and sweeps the life exponent parametrically, which is what the brief permits when no
mission requirement exists.

Machine-readable card: `reliability_material_model.yaml`.
Search record: `solder_literature_raw.csv` (479 works).
