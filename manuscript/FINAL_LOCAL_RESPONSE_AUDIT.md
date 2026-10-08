# FINAL LOCAL SOLDER RESPONSE ON THE FROZEN R3C PAIR

Reproduce with
`python scripts/phase0mr3c/trace_local_inputs.py` then
`python scripts/phase0mr3c/run_final_local_response.py`
(both need `PATH=/home/beams0/MGHARIB/envs/etm/bin:$PATH` so that `ccx` resolves).
Result: `results/phase0mr3c/final_local_response.csv`.

## 1. Why this was run

The manuscript reported a single local number, $\Delta u_c$, and described the 16.3 % Z1/Z2
separation as a "local fatigue-relevant inelastic response". $\Delta u_c$ is a
**displacement in micrometres**; it is the *driver* of the local submodel, not its output.
The response is $\Delta\varepsilon_{in}$, the dimensionless per-cycle increment of
accumulated equivalent inelastic strain. The two had never been evaluated on the same
frozen pair, so the headline quantity was the wrong one.

## 2. Entry state --- frozen, and unchanged by this work

| | Z1 embedded | Z2 backside |
|---|---:|---:|
| P_electronics (W) | 137.292 | 139.659 |
| T_max (C) | 118.32 | 126.46 |
| die warpage P-V (um) | 41.616 | 38.916 |
| du_c (um) | 4.6252 | 3.8714 |
| D_u | **1.1947** | |

`results/phase0mr3c/final_etm_replay.csv`, sha256 `bfa2e09d...`, mtime predates this work.
Configuration hashes: `frozen_pair_Z1.yaml` `98ab2464...`, `frozen_pair_Z2.yaml` `508a8bd5...`.
Entry test suite: **797 passed, 0 failed**.

## 3. Submodel inputs --- traced, not assumed

`scripts/phase0mr3c/trace_local_inputs.py` reads back the converged thermal field
(`it2/th_3.frd`, the last fluid sub-solve of the last E-T iteration) and the displacement
field (`structural.frd`) written by the frozen replay, and **reproduces every frozen global
value before deriving anything**:

| quantity | Z1 | Z2 | against frozen |
|---|---:|---:|---|
| T_max (C) | 118.320000 | 126.463000 | exact |
| T_mean (C) | 93.409907 | 95.411697 | exact |
| die warpage P-V (um) | 41.615600 | 38.915500 | exact |
| du_c (um) | 4.625234 | 3.871386 | exact |

The two architecture-supplied inputs then follow, with the same corner-band node selection
the production metric uses (BGA layer, r > 0.92 r_max, 32 joints):

| input | Z1 | Z2 |
|---|---:|---:|
| du_c applied to the upper pad (um) | 4.6252 | 3.8714 |
| T_joint, mean corner-band joint temperature (C) | 112.751 | 120.303 |
| T_joint max (C) | 116.626 | 124.507 |
| BGA standoff (mm) | 0.300 | 0.300 |
| nominal shear du_c / h (%) | 1.542 | 1.290 |

T_joint is defined exactly as in `scripts/phase0i/zglobal.py`: the mean over the corner band
of the half-sum of the BGA bottom- and top-face nodal temperatures. **Z2's joint runs 7.55 K
hotter while carrying the smaller displacement**, so the two effects oppose and the solve,
not intuition, decides the ordering.

## 4. Everything else is the existing production model

| | value | source |
|---|---|---|
| geometry | ball d 400 um, h 300 um, pitch 800 um; equal-area square prism side 354.49 um | `scripts/phase0i/joint.py` |
| pads | 400 um square, 20 um thick, copper | same |
| mesh | `build_joint(n_xy=6, n_z_solder=8, n_z_pad=1)`, C3D8, 488 elements, 128 in the core | same |
| exclusion band | one element from the solder free edge (`ESOLCORE`, excl_frac = 1.0) | same |
| constitutive card | `material("EPC")`: elastic + plastic + `*CREEP, LAW=NORTON`, SAC305, tabulated at -40/0/25/50/75/100/125 C | `scripts/phase0ir/decompose.py` |
| solver / procedure | CalculiX 2.23, `*VISCO` | `scripts/phase0i/joint.py` |
| boundary conditions | NBOT fixed 1-3; NTOP constrained 2,2 and 3,3; NTOP driven in x by du_c | same |
| stress-free reference | 25 C | same |
| cycle | 4 cycles of (T_joint, du_c, 300 s) then (25 C, 0, 300 s) | `scripts/phase0ir/arch_both_metrics.py` |
| stabilisation rule | last cycle, compared against the previous cycle | `scripts/phase0ir/cycle_audit.py` |
| extraction | `cycle_quantities`: volume-averaged over `ESOLCORE` | same |

The joint temperature 112.8-120.3 C lies inside the tabulated 100-125 C interval, so the
material is interpolated, not extrapolated in temperature.

## 5. One solver setting changed, and it is characterised

At the R3C operating point the time integrator cannot satisfy the Phase-0I value
`CETOL = 1e-2`. The failure is **not** loss of equilibrium: the force residual falls to
machine zero within five Newton iterations and stays there for forty. It is the creep
strain-increment tolerance: the step is cut repeatedly until it falls below the minimum.
Neither a 1e-14 time floor (six orders lower) nor a tenfold Newton iteration budget changes
this.

`CETOL = 5e-2` converges. It is not a new setting: four later production scripts already use
it --- `phase0jr/dwell_sensitivity.py`, `phase0kr/within_domain_search.py`,
`phase0lr/replay_lr.py`, `phase0m/me_energy.py`. Its effect on this metric was measured in
the Phase-0I convergence study: tags `c0.01` and `c0.05` in
`results/phase0i/local_metric_convergence.csv` differ by **0.015 %** on `d_eps_in_stab` at
the same mesh.

**The setting is validated here, not assumed.** `run_final_local_response.py` re-runs the
published Phase-0I architecture case at `CETOL = 5e-2` before it accepts the R3C numbers:

| | this run | published `architecture_metric_agreement.csv` | deviation |
|---|---:|---:|---:|
| d_eps_in per cycle | 6.513193434e-03 | 6.513193434e-03 | **0.0000 %** |

CETOL is a time-integration accuracy control, not a material or loading property, and at this
tolerance it moves the control result by nothing at all.

## 6. Where the model is being used --- the real limitation

| case | du_c (um) | T (C) | shear (%) | elastic trial tau (MPa) | sigma_y (MPa) | tau / sigma_y | converges at CETOL 1e-2 |
|---|---:|---:|---:|---:|---:|---:|---|
| Phase-0I convergence study | 1.200 | 100.00 | 0.400 | 52.9 | 13.08 | 4.0 | yes |
| Phase-0I control Z1 | 2.749 | 82.86 | 0.916 | 128.2 | 15.09 | 8.5 | yes |
| R3C Z1, displacement only | 4.625 | 82.86 | 1.542 | 215.7 | 15.09 | 14.3 | **no** |
| R3C Z1, temperature only | 2.749 | 112.75 | 0.916 | 116.1 | 11.59 | 10.0 | **no** |
| **R3C Z1 final** | 4.6252 | 112.75 | 1.542 | 195.4 | 11.59 | **16.9** | **no** |
| **R3C Z2 final** | 3.8714 | 120.30 | 1.290 | 159.2 | 10.70 | **14.9** | not tested |

Either input change alone is enough to break `CETOL = 1e-2` for Z1; the Z2 case at that
tolerance was never reached, because the run aborts at Z1, so it is recorded as not tested
rather than assumed to fail. The frozen pair sits at 15-17
times the yield stress, and the Norton card it is being evaluated with was fitted over
**7.51-15.92 MPa**. This is the constitutive extrapolation the manuscript already declares,
now with a number attached: the final pair is roughly an order of magnitude above the top of
the fitted window. It is why the magnitude is reported as an envelope and the ordering as the
result.

## 7. Results --- one solve per architecture, no sweep

| quantity | Z1 embedded | Z2 backside | ratio Z1/Z2 |
|---|---:|---:|---:|
| **d_eps_in per stabilised cycle** | **1.407235e-02** | **1.147821e-02** | **1.2260** |
| equivalent inelastic strain range | 6.897569e-03 | 5.627657e-03 | 1.2257 |
| inelastic work (MJ/m3) | 1.085302e+00 | 9.309436e-01 | 1.1658 |
| cycle-to-cycle change, last pair | 0.042 % | 0.056 % | --- |
| wall time (s) | 45.0 | 35.1 | --- |

    D_eps        = 1.2260
    reduction    = 18.43 %      Z2 lower
    D_u          = 1.1947       (displacement driver, frozen, unchanged)

All three local metrics rank the pair the same way, and the two independent strain measures
agree to 0.03 % on the ratio.

## 8. Reading

* **The ordering agrees with the driver.** Z2 carries the lower local inelastic response, as
  it carries the lower displacement driver.
* **The magnitude does not.** 18.43 % on the response against 16.3 % on the driver. The two
  are different quantities and must not be quoted interchangeably. Two cross cases, run
  through the same submodel, separate the causes
  (`results/phase0mr3c/local_response_decomposition.csv`):

  | case | du_c (um) | T_joint (C) | d_eps_in | against Z1 |
  |---|---:|---:|---:|---:|
  | Z1 | 4.6252 | 112.751 | 1.407235e-02 | --- |
  | Z2 displacement at Z1 temperature | 3.8714 | 112.751 | 1.134431e-02 | **-19.39 %** |
  | Z1 displacement at Z2 temperature | 4.6252 | 120.303 | 1.417783e-02 | **+0.75 %** |
  | Z2 | 3.8714 | 120.303 | 1.147821e-02 | **-18.43 %** |

  The displacement reduction alone would give 19.39 %, more than the 16.3 % reduction in the
  driver itself, because the accumulated inelastic strain depends nonlinearly on the imposed
  displacement --- the Norton exponent is about 7 at these temperatures. Z2's joint running
  7.55 K hotter works in the opposite direction and adds 0.75 % back. The net is 18.43 %.
  The response separation is therefore larger than the driver separation despite the hotter
  joint, not because of it.
* **Z2 is still the hotter architecture.** +8.14 K at the die and +7.55 K at the joint, with
  18.43 % lower local inelastic response. The temperature-versus-response decoupling that the
  paper reports is unchanged, and is now stated in the quantity that actually measures
  response.
* **Cycle stabilisation is better than the Phase-0I cases**, 0.04-0.06 % against 0.80-2.00 %,
  because the larger imposed shear reaches a stabilised cycle sooner.

## 9. What is still not claimed

Response is not damage, damage is not life, life is not failure. No damage law, life relation
or admissible allowable is established here and none is applied. The magnitude remains
conditional on a Norton surrogate evaluated far outside its fitted stress window, as
quantified in section 6. G2 remains not tested.
