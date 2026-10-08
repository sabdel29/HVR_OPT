# Audit of the original 19-point SAC305 creep fit

**Phase 0L, Part V.** What the 19 points are, where they came from, what variable they were
regressed in, and whether that variable is the one the solver consumes.

Artifacts: `results/phase0l/original_19point_fit.csv`,
`scripts/phase0l/original_fit_audit.py`, and the retrieved source paper under
`results/phase0l/lit/`.

## 1. Provenance — the cited table does not exist

`scripts/phase0i/solder_model.py:61-62` attributes the 19 points to

> PRIMARY EXPERIMENTAL DATA, Yuan (2023) Materials 16(14):4922, **Table 26**.

That paper was retrieved in full (Europe PMC full-text XML for PMC10381129, cached as
`results/phase0l/lit/yuan2023_epmc.xml`; Crossref confirms the DOI, title, authors, volume,
issue and page). **It contains eleven tables. There is no Table 26.**

The 19 points are its **Table 5**, "The ratios applied to the data pair to emphasize the
preference", whose columns are Data ID / Temperature (°C) / Plastic Strain Rate (ε̇_p, 10⁻⁹ 1/s)
/ Stress (MPa) / Ratio. All nineteen (T, σ, ε̇) triples in `CREEP_DATA` match that table exactly,
including the 10⁻⁹ scaling.

Two further citations in the same file are also wrong by the same kind of error, and in both
cases the *values* are right while the *table number* is not:

| `solder_model.py` says | Actually | Values |
|---|---|---|
| Table 26 → 19 creep points | **Table 5** | match exactly |
| Table 27 → Garofalo constants | **Table 6** | match exactly (0.184/0.221/2.89/62000 and 0.539/0.473/1.055/65000) |
| Table 31 → Chaboche σ₀(T) | **Table 10** | match exactly (39.32/33.80/21.35/15.43/10.50) |

## 2. Provenance — the alloy is not SAC305

Yuan 2023 §4.1 states plainly:

> The experimental dataset is drawn from **Xiao and Armstrong [10]**.

and its own introduction describes that work as

> Xiao and Armstrong [10] performed tensile tests on both eutectic PbSn and **Sn3.9Ag0.6Cu**
> solder.

Reference [10] is *Xiao Q., Armstrong W.D., "Tensile creep and microstructural characterization
of bulk **Sn3.9Ag0.6Cu** lead-free solder", J. Electron. Mater. 34 (2005) 196–211,
doi:10.1007/s11664-005-0233-z.*

**The creep half of the material card is calibrated on Sn3.9Ag0.6Cu, not on SAC305
(Sn3.0Ag0.5Cu).** Ag content differs by 0.9 wt % — 30 % relative — and Ag content is the
principal control on Ag₃Sn precipitate strengthening and therefore on creep rate in this alloy
family. Yuan 2023 is itself internally inconsistent on this point: its title and conclusion say
"SAC305" while its introduction and its own reference list say Sn3.9Ag0.6Cu. Where a paper
contradicts itself, the cited primary title governs.

The Phase-0L brief forbids transplanting "high-Ag SAC … parameter sets without explicit
transferability evidence". No such evidence was found (Part VII). The transplant is already in
place and was not previously recorded.

**The two halves of the card are different alloys.** The yield surface traces to Motalab et al.
SAC305 measurements (Motalab → Anand fit → synthetic stress–strain curves → Chaboche fit →
Yuan Table 10), which is genuinely SAC305 but two model layers removed from any measurement.
The creep law traces to Xiao & Armstrong Sn3.9Ag0.6Cu. The overstress formulation then
*subtracts one from the other*: a SAC305 yield stress is subtracted from the stress driving
Sn3.9Ag0.6Cu creep.

## 3. Definitions of the tabulated quantities

| Quantity | Definition in the source |
|---|---|
| Stress | **total applied uniaxial stress** in a constant-load tensile creep test. Not an effective stress, not an overstress |
| Rate | steady-state ("plastic") strain rate; Table 5 column is in units of 10⁻⁹ s⁻¹ |
| Temperature | 45, 80, 115, 150 °C (318, 353, 388, 423 K) |
| Stress window | 7.51 – 15.92 MPa |

## 4. What variable the fit used

`scripts/phase0i/solder_model.py:84-96`:

```python
def fit_norton_data(T_c: float) -> dict:
    """Power-law fit to the MEASURED points at one temperature."""
    pts = [(s, e) for (t, s, e) in CREEP_DATA if abs(t - T_c) < 1e-9]
    xs = np.log([s for s, _ in pts]); ys = np.log([e for _, e in pts])
    n, lnA = np.polyfit(xs, ys, 1)
    A = math.exp(lnA)
```

`xs` is `log(σ_applied)`. There is no yield subtraction anywhere in the function, in
`norton_at()`, or in `calculix_cards()`. **The regression is ε̇ = A·σ_applied^n.**

In its own variable the fit is good: max error 14.8 %, rms 8.3 % over the 19 points.

## 5. What variable the solver uses

Part III, confirmed by probe to five significant figures:

> ε̇ = A · (σ_vm − σ_y(ε̄_in))^n, and ε̇ ≡ 0 whenever σ_vm ≤ σ_y.

## 6. DEFECT #40 — CONFIRMED

The fit variable is σ_applied. The solver variable is σ_vm − σ_y. **They are different
variables, so DEFECT #40 is confirmed.**

The consequence is not a modest bias. Evaluating σ_y(T) at the four calibration temperatures:

| T (°C) | σ_y0 (MPa) | data σ range (MPa) | overstress range (MPa) |
|---|---|---|---|
| 45 | 20.61 | 10.54 – 15.92 | **−10.07 … −4.69** |
| 80 | 15.43 | 10.43 – 14.46 | **−5.00 … −0.97** |
| 115 | 11.32 | 8.73 – 12.41 | −2.59 … **+1.09** |
| 150 | 10.50 | 7.51 – 11.52 | −2.99 … **+1.02** |

**The overstress is negative at 16 of the 19 calibration points.** In the solver's own variable
the calibration experiment lies entirely inside the elastic domain, where the model produces no
inelastic strain at all. The card therefore cannot reproduce the data it was fitted to — not
approximately, but identically zero at 16 points. Solver probe TEST F confirms this directly:
16 of 19 give exactly 0.0, and the three with positive overstress are low by factors of
4.7×10⁷, 1.8×10¹² and 2.4×10⁵. **0 of 19 reproduced.**

This also means the fit residual quoted in §4 is not a measure of model quality. It measures
how well a curve fits the data in a variable the solver never evaluates.

## 7. Scope of the defect

DEFECT #40 is a *variable* inconsistency (Part II question A). It is separate from, and
compounds with, the *domain* inconsistency (question B): the card is fitted over 7.51–15.92 MPa
and evaluated at damage-weighted stresses of roughly 54–91 MPa. The overstress formulation
partially masks the extrapolation, because σ_vm − σ_y is smaller than σ_vm, but it does so by
the wrong mechanism and by a temperature-dependent amount.

Two further card-construction defects found while probing are recorded in
`CALCULIX_CREEP_IMPLEMENTATION_AUDIT.md` §10: the production temperature grid gives a
0.83–3.88× error between rows over 45–150 °C, and clamps above 125 °C with errors to 8.70×.
