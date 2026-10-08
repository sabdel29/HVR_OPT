# Cycle inelastic-energy integral — independent audit

**Phase 0L-R, Part 4.** The energy metric was audited from first principles, reimplemented
independently, and refined to convergence. It found a real defect.

Artifacts: `energy_integration_convergence.csv`, `scripts/phase0lr/energy_audit.py`,
`results/phase0lr/probe/shear.inp`.

## 1. What the production post-processor does

`scripts/phase0ir/cycle_audit.py :: cycle_quantities`:

$$ W_{in} \;=\; \sum_k \tfrac{1}{2}\left(\boldsymbol{\sigma}_k + \boldsymbol{\sigma}_{k-1}\right)
   : \left(\boldsymbol{\varepsilon}^{in}_k - \boldsymbol{\varepsilon}^{in}_{k-1}\right) $$

| ingredient | how it is obtained |
|---|---|
| stress σ | solver output `S`, integration-point averaged |
| total strain | solver output `E` |
| elastic strain | Hooke's law in Python at E(T), ν |
| thermal strain | **reconstructed in Python** as α(T − T_ref) |
| inelastic strain | total − elastic − thermal, i.e. **reconstructed, not read** |
| quadrature | trapezoidal over OUTPUT points |
| shear convention | factor 2 on off-diagonals |
| region | the two 25 μm Syed layers, volume-weighted |
| cycle | stabilised cycle 5 of 6 |

## 2. Conventions settled by probe, not by assumption

A single element under combined thermal load and shear (`probe/shear.inp`):

- **Tensor shear convention.** ME_xy = σ_xy/(2G) = 2.2324e−4, against σ_xy/G = 4.4648e−4. The
  double contraction therefore needs the factor 2 on off-diagonals, and **the production factor
  2 is correct.**
- **The solver exposes the mechanical strain directly.** `ME` satisfies E − ME = α(T − T_zero) to
  seven figures. Asking for `ME` removes the thermal reconstruction, and with it the need for a
  temperature at all, from the energy path.

## 3. The independent implementation

Identical region, cycle and weighting; different everywhere it matters:

- **ε_in = ME − ε_elastic**, using the solver's own mechanical strain. No α, no T_ref, no
  temperature parsing.
- three quadrature rules — trapezoidal, midpoint and Simpson — instead of one.

## 4. DEFECT #46 — the audit's finding

The two implementations disagreed by a stable **18.5 %**, far too consistent to be noise. The
cause is a step-boundary aliasing bug:

`parse_temperature` kept the **first** temperature block at a given printed time, while
`parse_tensors` keeps the **last**. CalculiX prints the same rounded time on both sides of a step
boundary, so the tensors and the temperature were taken from **opposite sides of every
boundary** — 11 of 690 time points, at which the parsed temperature was wrong by about 55 K.

The thermal strain is hydrostatic, so the error injected a spurious **volumetric** inelastic
strain of about 1.2e−3. Creep is isochoric, so the trace of ε_in must be zero; measured, the
contaminated reconstruction had a trace of 8.7e−4 against 2.9e−6 for the ME-based one. Multiplied
by a hydrostatic stress that peaks at 60 MPa, that produced the 18.5 % error — and it landed at
exactly the 11 instants where the joint deposits most of its damage (FIG-0LR-A).

**The deviatoric work was identical in both implementations (1.20011).** The entire discrepancy
was volumetric, which is how it was identified.

| | before the fix | after the fix |
|---|---|---|
| production W (MJ/m³) | 1.45725 | **1.19157** |
| independent W (MJ/m³) | 1.20067 | 1.20067 |
| production / independent | 1.185 | **0.992** |

**Δ PEEQ was unaffected**, because PEEQ is read from the solver rather than reconstructed. That
asymmetry explains why the strain metric has been numerically stable throughout the project while
the energy metric has not.

**Fix applied:** `parse_temperature` now keeps the last block at each time, matching
`parse_tensors`. Residual disagreement **0.76 %**, caused by about 26 increments sharing one
printed time key at a boundary — the solver prints time to only about seven digits, so tensors
and temperature can still come from neighbouring increments within that cluster. Measured on
the isochoric test, the worst spurious volumetric strain falls from 8.7e-4 to **1.8e-4**,
against **6.3e-6** for the ME-based reconstruction — still a factor of 29 apart, with 1.59 % of
element-increments exceeding 1e-4. The residual is bounded and is now pinned by a regression
test (`tests/phase0lr/test_phase0lr.py::test_inelastic_strain_is_isochoric`).

**Fix recommended:** request `ME` in the decks and compute ε_in = ME − ε_el. That removes the
temperature from the energy path entirely and would take the residual to zero. Not applied in
this phase because it requires re-running every deck.

## 5. Convergence

All at model M1, Z1, baseline, stabilised cycle. From `energy_integration_convergence.csv`,
recomputed after the fix:

| case | dt_max (s) | output freq | points/cycle | W production | W independent | Δ PEEQ |
|---|---|---|---|---|---|---|
| base (dt₀ = 1e−5) | 10 | 1 | 109 | 1.17978 | 0.96985 | 0.011646 |
| tight (dt₀ = 1e−8) | 10 | 1 | 109 | 1.45725 | 1.22975 | 0.011694 |
| dtmax 5 | 5 | 1 | 165 | 1.45803 | 1.23060 | 0.011705 |
| dtmax 2 | 2 | 1 | 341 | 1.45878 | 1.23144 | 0.011713 |
| dtmax 1 | 1 | 1 | 637 | 1.45903 | 1.23170 | 0.011716 |
| freq 2 | 1 | 2 | 321 | 1.43262 | 1.21439 | 0.011716 |
| freq 4 | 1 | 4 | 163 | 1.34197 | 1.14453 | 0.011716 |

(The W columns in this table are the pre-fix values, retained because they are what the
convergence study measured; the fix changes the level, not the convergence behaviour.)

Three things follow.

**Time-step refinement is converged.** From dt_max 10 s to 1 s, a six-fold refinement and a
six-fold increase in output points, W moves **0.12 %** and Δ PEEQ **0.19 %**. The tight control
is converged.

**The pre-0L starting increment was not.** `base` against `tight` is a **23 % / 27 %** difference
in W from the starting increment alone, with identical dt_max and output frequency. The starting
increment governs how finely the solver walks through the first transient of each half-cycle,
and that is where the work is.

**Output frequency matters independently of the time step.** At fixed dt_max = 1 s, printing
every second increment loses 1.8 % of W and every fourth loses 8.0 %, while Δ PEEQ is unchanged
to seven figures. The energy metric is a sampled integral; the strain metric is an endpoint
difference. Any comparison of energy-based results must therefore fix the output frequency as
well as the time step.

## 6. Consequence

- **Δ PEEQ / M1 is numerically trustworthy**: 0.19 % under time-step refinement, 0.0 % under
  output-frequency change, unaffected by DEFECT #46.
- **W / M3 is not, historically**: 18.5 % from DEFECT #46, 23–27 % from the starting increment,
  up to 8 % from output frequency. After the fix and at the tight control it is converged to
  0.12 %, but every energy number generated before this phase carries the defect.
- Part 13 downgrades the two energy-based life laws to **ranking-only use** on exactly this
  basis.
