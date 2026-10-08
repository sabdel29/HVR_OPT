# TCPMT STRENGTHENING PASS --- REVISION LOG

What the manuscript was missing, what was added, the evidence each addition rests on, and
where it now lives. No frozen science changed: the converter design point, the Z1/Z2
configurations, the loss ledger, the thermal and mechanical models and every numerical
conclusion are identical to the paper-freeze state at the close of the last technical gate.
Every number added here was already in a frozen artifact or was measured by timing the
frozen configurations without altering them.

Manuscript: 8 pages before, **15 pages after**. 8 figures, 9 tables, 25 cited references (28 entries in the bibliography file).

---

## 1. HVR electrical model

**Was missing.** The regulator appeared as a design point. The topology was never drawn, the
loss model was summarised rather than written, and a reader could not tell which loss
mechanisms the production code evaluates.

**Added.**

| addition | evidence | where |
|---|---|---|
| Full hybrid-regulator schematic: 48 V rail, three high-side devices, flying capacitors, 16 V intermediate rail, three low-side devices with switch nodes, three inductors, 1 V rail, output capacitor, point-of-load | `HVR_FULL_OPT_EPC_V2.py`, synthesised `N3K3K_A2` | Fig. 1(b) |
| Synthesis statement: enumeration over stage count, phase count, auxiliary-branch count and conversion-ratio vector, device filtering by blocking voltage and current capability, frequency selection at the ripple constraint | `compute_total_loss`, synthesis search | §III-A, Eq. (1) |
| Ripple and RMS current, written in the implemented form including the inter-inductor coupling factor | `compute_total_loss` | §III-B, Eq. (2) |
| Conduction loss written as the implemented common-term-minus-correction expression, with the branch-dependent correction | `compute_total_loss` | Eq. (3)--(4) |
| Per-mechanism loss decomposition, checked against the aggregate to machine precision on every evaluation, with the run rejected on mismatch | `scripts/phase0mr/ledger.py` | §III-B |
| The three switching terms in the implemented form, with the plateau-voltage gate-drive current | `compute_total_loss`; method cited to the plateau-voltage application note | Eq. (5)--(7) |
| Explicit statement of the two deliberate omissions --- inductor core loss and capacitor dielectric loss --- with the direction of their bias | component library carries Steinmetz coefficients that the synthesis model does not consume | §III-B, closing paragraph |
| Per-cell loss mechanisms on a log scale, showing low-side conduction dominance at D = 0.0625 | frozen loss ledger | Fig. 3(a) |
| System loss breakdown separating converter losses from package losses | `final_etm_replay.csv` ledger columns | Fig. 3(b) |

Only mechanisms the production code evaluates are shown. No textbook term was added for
completeness.

---

## 2. Thermal model and boundary conditions

**Was missing.** The governing equation, the anisotropy, the homogenisation rules, the
deposition policy and the cooling correlation domain were compressed into a few sentences.

**Added.**

| addition | evidence | where |
|---|---|---|
| Steady conduction with an orthotropic tensor and a volumetric source, written out | production thermal path | §IV-A, Eq. (12) |
| Deposition policy: every loss term of §III is deposited in the layer that generates it, checked against the electrical total to 10^-6 relative on every solve | production thermal path | §IV-A |
| Homogenisation rules: parallel rule through thickness, stiffness-weighted expansion, explicitly meshed representative volume element in plane, with the Maxwell--Garnett comparison and why the element result is adopted for via arrays | RVE cross-checks | §IV-A |
| Statement that treating the redistribution layer as isotropic shifts absolute temperatures by several kelvin | anisotropy sensitivity | §IV-A |
| Unheated faces adiabatic on the sides, 10 W m^-2 K^-1 natural convection beneath the carrier at 25 C | production boundary set | §IV-A |
| Complete material table: modulus, Poisson ratio, expansion coefficient and conductivity for all eight layers, with the cubic silicon constants | frozen material set | Tab. III |
| Complete cold-plate table: channel geometry, count, hydraulic diameter, coolant, mass flow, velocity, Reynolds, Prandtl, Nusselt, thermal entry length, channel coefficient, area amplification, fin efficiency, effective coefficient, coolant rise, pressure drop and pump power | `cooling_regime.evaluate(27.0)` | Tab. IV |
| The effective-coefficient definition and the correlation-domain rule, with the transitional band declared out of model domain | Shah--London and Gnielinski bounds in the production cooling model | §IV-B, Eq. (13) |
| Pump power carried in a facility ledger, separate from the electronics ledger, and excluded from the deposited heat | ledger scope separation | §IV-B, Tab. IV |

---

## 3. Mechanical setup

**Was missing.** The element types, the restraint scheme, the assembly state, the
submodelling chain and the distinction between the global driver and the local response
were under-described, and the previous version conflated the two.

**Added.**

| addition | evidence | where |
|---|---|---|
| Global thermoelastic model: incompatible-mode hexahedral elements, cubic-orthotropic silicon, the explicit board and ball-grid-array field, statically determinate restraint only | production structural path | §IV-D |
| Explicit statement that the clamp-type restraint was withdrawn as an artifact and that the reported assembly state carries an explicit board | assembly-state study | §IV-D, Fig. 6 |
| The corner-joint driver defined as the maximum relative in-plane displacement across the interconnect layer over the outer radial band, in micrometres | `replay_production.py::_corner_shear` | §IV-D, Eq. (17) |
| The local joint submodel: displacement-driven, viscoplastic, its own mesh, and the per-cycle equivalent inelastic strain increment it returns, dimensionless | local submodel builder | §IV-E, Eq. (18) |
| The two quantities separated throughout --- the driver is a displacement in micrometres, the response is dimensionless --- correcting a units error in the previous version | both artifacts | §IV-D, §IV-E, Fig. 8 |
| The terminology ladder from response through damage to life, with the cut line stated | claim matrix | §IV-E |
| The computed deformation field itself: die-surface out-of-plane displacement for both architectures on one shared scale | the frozen replay's own displacement output, re-read by `scripts/phase0mr3c/extract_die_field.py`, which asserts the field reproduces the frozen peak-to-valley before writing anything | Fig. 6(a)(b) |
| Coupling level declared: closed electrical--thermal loop, one-way thermal-to-mechanical | framework structure | §IV-F, Fig. 1(c) |

---

## 4. Solvers, validation setup and numerical settings

**Was missing.** Solver names, versions, mesh sizes, tolerances and iteration counts were
largely absent, and the validation evidence was asserted rather than tabulated.

**Added.**

| addition | evidence | where |
|---|---|---|
| The three solvers on the production path, named and versioned, with what each one does | platform record | §V-A |
| The independent reference solver named with its build hash, and the statement that it is never on the production path | platform record | §V-A |
| A validation matrix of 27 rows: quantity, production model, reference, and measured error | `VALIDATION_MATRIX.md`, all rows from frozen artifacts | Tab. V |
| The electrical validation written out: three regulator placements on a 300x300 mesh, five transition geometries, the uniform-conductor and spreading-resistance limits, the via-chain land correction and its convergence | `multilayer_rdl_validation.csv`, transition cross-checks | §V-B, Fig. 5(a)(b) |
| Thermal validation: the fin-efficiency check against an explicitly meshed fin solution, the accepted and rejected geometries, and the three-dimensional field comparison | cooling solid-side check | §V-C, Fig. 5(c) |
| Mechanical convergence: three mesh levels with element counts and the drift on the finest pair, and the cycle-stabilisation result | `local_metric_convergence.csv` filtered to genuine mesh refinements, `stabilized_cycle_audit.csv` | §V-D, Fig. 5(d) |
| The electrical--thermal fixed point: Picard iteration, 0.25 K tolerance, six-iteration cap, three achieved, zero energy residual | `final_etm_replay.csv` | §IV-C, Tab. II |
| Two attempts that produced no usable result, reported as attempted and not used rather than omitted or counted as validation | `hfss_tsv_loop.csv` status field; the discarded conjugate-CFD attempt | Tab. V, last two rows |

The full-wave and conjugate-CFD attempts are reported with their failure mode. Neither is
presented as validation. The invalid conjugate-CFD case is not used as a comparison point.

---

## 5. Computational platform and cost

**Was missing.** No platform, no runtime, no cost structure.

**Added.**

| addition | evidence | where |
|---|---|---|
| Platform: two 24-core processors, 48 physical cores, 2.0 TiB, the operating system, the solver version and the Python stack, with the statement that no accelerator is used | `results/phase0mr3c/platform.json` | §V-A, Tab. VI |
| Measured wall time per stage: converter synthesis over the device library, rail-aware network and routing, cooling correlation, and one complete evaluation per architecture | `results/phase0mr3c/runtime_benchmark.csv`, produced by timing the frozen configurations | Tab. VI, Fig. 8(e) |
| Confirmation that the timing run reproduced the frozen results exactly | benchmark script asserts against `final_etm_replay.csv` | Tab. VI caption, §V-E |
| Why the two architectures differ in cost --- the backside stack resolves a via field the embedded stack does not | element counts | §V-E |
| The cost structure argument: the expensive part is entered once per candidate, not once per design variable | measured times | §V-E |
| **Speedup: reported as not available, with the reason.** No controlled same-geometry, same-machine timing pair against a higher-fidelity reference was recorded, and the two commercial attempts produced no valid reference | `RUNTIME_BENCHMARK.md` | §V-E, Tab. VI note |

A speedup figure was not manufactured. The absence is stated with its cause.

---

## 6. Comparison with prior frameworks

**Was missing.** Prior work was cited but not compared, and no capability was scored.

**Added.**

| addition | evidence | where |
|---|---|---|
| A 27-row capability matrix across six prior works and this one | `PRIOR_FRAMEWORK_COMPARISON.md`; only works read in full text are scored. The markdown copy is now generated from the manuscript table by `scripts/phase0mr3c/sync_prior_comparison.py`, so the two cannot diverge | Tab. VII |
| Four rows placed below a rule for capabilities the present framework does **not** provide: load-dependent operating point, regulator activation, explicit ripple and regulation constraints, and a manufacturing-cost objective | the prior works themselves, read in full | Tab. VII, §VI-A |
| Two further frameworks obtained in full text from arXiv and scored: the architecture study that defines the vertical-integration family used here, and a load-aware power-management methodology | arXiv:2309.10141 and arXiv:2605.24874, both read in full | Tab. VII, §VI-A |
| Explicit statement that capability is not inferred from titles or abstracts, and that works unobtainable in full text from this host are cited for motivation but left unscored | reading record | §VI-A |
| A fair reading of the baseline framework's own scope and what this work adds to it, rather than a deficiency list | the baseline work, read in full | §VI-A |
| The 2.5-D electrothermal study's reported validation errors and cost objective, stated as its strengths | that work, read in full | §VI-A |
| Four new references added: two resolved against Crossref, two obtained as full texts from arXiv | ISCAS 2024 DVPD design considerations; the 2.5-D TTSV study; the 2023 architecture study; the 2026 power-management methodology | bibliography |

---

## 7. Published assumptions reproduced and tested

**Was missing.** Prior positions were neither reproduced nor tested.

**Added.** Six positions taken in the DVPD literature were reproduced inside the framework
and tested. The purpose stated in the manuscript is to identify the conditions under which
each holds, not to contest it.

| position | outcome | evidence | where |
|---|---|---|---|
| Vertical interconnect loss is small relative to lateral routing | **rail-dependent.** The same via field dissipates essentially nothing carrying 48 V and 0.991 W carrying 1 V | `final_etm_replay.csv` loss ledger | Tab. VIII, §VI-B, Fig. 3(c) |
| 1 V lateral delivery across the package is prohibitively lossy | **reproduced** | production network model | Tab. VIII |
| A larger converter footprint is favourable | **reverses with assembly state.** +20.3 % free against -16.6 to -29.0 % mounted | `footprint_board_envelope.csv` | Tab. VIII, Fig. 6 |
| Peak temperature ranks architectures for reliability | **not equivalent** to the local mechanical-response ranking on the frozen pair | `final_etm_replay.csv` | Tab. VIII, §VII-D, Fig. 8 |
| A numerically attractive tier order is realizable | **invalidated by physical routing** for the reference order: aspect ratio 5.05 | `routing_feasibility.csv` | Tab. VIII, Fig. 4 |
| Vertical via counts follow from the material-layer stack | **corrected to conductor-plane topology**, which gives one build-up level where the layer count suggests three | `conductor_plane_topology.csv` | Tab. VIII, §III-E, Fig. 4(a) |

---

## 8. Figures

**Was missing.** The figures were simplistic: single-panel, default styling, and several
carried a single number each.

**Rebuilt.** All eight figures were regenerated from frozen artifacts through one figure
system.

| property | before | after |
|---|---|---|
| format | mixed | vector PDF throughout, no raster, no terminal capture |
| type | serif, matching the manuscript body | unchanged, at 6.2--7.6 pt |
| palette | matplotlib defaults | a colourblind-safe eight-colour set, also separable in grayscale |
| scientific fields | --- | no rainbow map is used anywhere |
| panels | mostly single | multi-panel, 3 to 5 panels each, each panel answering one question |
| bar charts | the common case | used only for genuinely categorical comparisons; the others are a parity plot, a convergence curve, a log-scale current ladder, two annotated cross-sections and a circuit schematic |
| legends | default, oversized | small, outside the data area, or replaced by direct labelling |
| truncated axes | unmarked | axis-break glyphs drawn and declared in the caption |

| figure | what it now carries |
|---|---|
| Fig. 1 | (a) system cross-section; (b) the full regulator schematic; (c) the framework information flow with the electrical--thermal fixed point marked |
| Fig. 2 | the two physical stacks side by side, with arrow width encoding segment current on a log scale, and the rail each via field carries |
| Fig. 3 | (a) per-cell loss mechanisms on a log scale; (b) stacked system breakdown for both architectures; (c) the rail-dependent vertical loss with the 48 V against 1 V contrast |
| Fig. 4 | (a) the conductor-plane sequence on a real z axis; (b) tier order before and after, with the crossed region marked on each; (c) worst aspect ratio per vertical net |
| Fig. 5 | (a) parity against the reference solver; (b) electrical deviations against a 2 % band; (c) the accepted and rejected cooling geometries; (d) mesh convergence with element counts |
| Fig. 6 | (a), (b) the computed die-surface displacement field for both architectures on one shared scale; (c) the assembly-state reversal: free package against five explicit boards |
| Fig. 7 | the response-ratio ladder across five recorded model states, with the converged band and the ordering-reversal line |
| Fig. 8 | the final comparison across four quantities plus the measured computational cost |

Every figure was inspected at final two-column size in the typeset PDF, not only as a
standalone file.

---

## 9. Corrections made during this pass

Three defects in the previous manuscript, all fixed at source:

1. **A units error.** The corner-joint driver, a displacement in micrometres, was labelled
   as a strain. The driver and the dimensionless local response are now distinct quantities
   with distinct symbols and equations.
2. **A missing ablation state.** The physics-block table listed four model states while the
   text and the sensitivity figure describe five. The intra-cell interconnect-repair state
   was restored to the table, so the ratio ladder in the table now matches the figure.
3. **A direction error.** Two omitted loss mechanisms were described as conservative. They
   bias the reported dissipation downward, which is the opposite direction; the text now
   says so.

Two solver citations and one method citation that the text relied on but never cited were
added. One duplicate-key check and one uncited-float check were run over the whole document.

---

## 9b. Final correction pass --- the local solder response

**Was wrong.** The headline separation, 16.3 %, was described in several places as a "local
fatigue-relevant inelastic response". It is $\Delta u_c$, the corner-joint relative in-plane
**displacement** in micrometres. It is the *driver* of the local viscoplastic submodel, not
its output. The response, $\Delta\varepsilon_{in}$, had never been evaluated on the final
frozen pair at all, so the paper reported a displacement under the name of a strain.

**What was done.** The existing production submodel --- same mesh, exclusion band,
constitutive card, solver, boundary conditions, cycle schedule, stabilisation rule and
extraction code --- was run once per architecture on the frozen pair.

| addition | evidence | where |
|---|---|---|
| Both local-submodel inputs traced from the frozen fields, with every frozen global value reproduced exactly first | `scripts/phase0mr3c/trace_local_inputs.py`, `results/phase0mr3c/local_submodel_inputs.csv` | §IV-E, Tab. II |
| Corner-joint temperature, derived with the same corner-band node selection as the driver: 112.75 °C and 120.30 °C | same | §IV-E, Tab. II |
| $\Delta\varepsilon_{in}$ per stabilised cycle: **1.4072×10⁻²** and **1.1478×10⁻²**, $D_\varepsilon$ = **1.2260**, Z2 **18.4 %** lower | `results/phase0mr3c/final_local_response.csv` | Abstract, §VII-D, Tab. II, Fig. 8(e) |
| Two further metrics from the same solves, ranking the pair identically: strain range 1.2257, inelastic work 1.1658 | same | §VII-D, Tab. II |
| Cycle stabilisation on the final pair, 0.04 % and 0.06 % | same | Tab. II |
| A measured decomposition of the response separation: the displacement reduction alone gives 19.39 %, the hotter joint returns 0.75 %, netting 18.43 % | two cross cases through the same submodel, `results/phase0mr3c/local_response_decomposition.csv` | §VII-D |
| The driver and the response separated everywhere: distinct symbols, distinct rows, distinct panels, distinct ratios $D_u$ and $D_\varepsilon$ | --- | throughout |

**One solver setting changed, and it is validated rather than assumed.** At the R3C operating
point the time integrator cannot satisfy the Phase-0I creep tolerance of 1×10⁻²: force
equilibrium converges to machine zero within five Newton iterations, but the step is cut
until it falls below the minimum. Neither a 1×10⁻¹⁴ time floor nor a tenfold Newton budget
helps. The tolerance 5×10⁻² converges; it is the value four later production scripts already
use, its effect on this metric was measured at 0.015 % in the Phase-0I convergence study, and
the run script re-runs the published Phase-0I control at that tolerance before accepting the
R3C numbers --- reproducing it to **0.0000 %**.

**What the result means.** The ordering is unchanged and the paper's central finding survives
in the correct quantity: Z2 runs 8.14 K hotter at the die and 7.55 K hotter at the joint, and
carries 18.4 % lower local inelastic response. The driver and the response do **not** agree on
magnitude, 16.3 % against 18.4 %, which is precisely why they must not be quoted
interchangeably. The reason is measured rather than asserted: the accumulated inelastic strain
depends nonlinearly on the imposed displacement, so the 16.3 % driver reduction alone produces
19.39 %, and the hotter backside joint returns 0.75 % of it.

**A limitation sharpened.** The frozen pair drives the joint to 15--17 times the solder yield
stress, against a Norton card fitted over 7.51--15.92 MPa. §VIII-C now carries that number.

## 9c. Other corrections in the same pass

| was | now | evidence |
|---|---|---|
| "dominated by the two finite-element solves inside each of the three fixed-point iterations" | the mechanical solve is **outside** the loop; each iteration runs 3--4 fluid-coupled thermal sub-solves, 11 in total, then one thermoelastic solve after convergence | code inspection of `replay_production.run_case`; `results/phase0mr3c/timing_breakdown.json`, `manuscript/FINAL_TIMING_BREAKDOWN.md` |
| tier orders "electrically and thermally indistinguishable" | "equivalent at the component-selection and stack-budget level"; the routing parasitics differ, and that difference is not separated from the conductor-plane correction in Tab. IX | frozen ablation states |
| α_GaN described as adopted to reproduce published behaviour | labelled an **adopted calibration coefficient, not a sourced material constant**, with ±20 % → ∓5.8 % on converter loss and the Z1/Z2 ordering preserved at every value | `manuscript/GAN_TEMP_COEFF_AUDIT.md`, `results/phase0mr3c/gan_alpha_sensitivity.csv`, `results/phase0d/robustness_0d.csv` |
| every row of Tab. VIII headed "prior position" | each row labelled by its standing in the cited work: two **published results**, three **implications of the formulation**, one **modelling assumption** | the cited works, read in full |
| Fig. 8, five panels, driver shown as the mechanical result | six panels: the chain $P_{elec}$ → $T_{max}$ → warpage → driver → response → cost, with driver and response visually distinguished | regenerated vector PDF |

---

## 9d. Reviewer-hardening pass

**Integration-tolerance robustness.** A reviewer can reasonably ask whether the final
response exists only because the creep tolerance was relaxed. Measured over a five-value
ladder (1e-5, 1e-4, 1e-2, 5e-2, 1e-1) with every other input fixed: three tighter tolerances
complete **zero** increments; the two that converge take the same 336 increments with zero
cutbacks and return Δε_in, its range and the inelastic work **identical to twelve digits**
for both architectures, leaving D_ε at 1.226006. Doubling the tolerance moves the result by
nothing. The bracket is one-sided and the manuscript says so.
Added to §IV-E, §V-D and §VIII-C; recorded in `CETOL_FINAL_PAIR_ROBUSTNESS.md` and
`cetol_final_pair.csv`; guarded in `audit_manuscript.py` (82/82 values).

**Omitted-loss wording narrowed.** "act in the same direction for both architectures and
therefore **do not affect** the comparison" overstated what is supported, because the two
architectures run at different temperatures. Both occurrences now read that the omissions
bias dissipation downward, act on the same component set, and are therefore **not expected
to alter the reported ordering**, with exact cancellation explicitly not asserted. A sweep
for `does not affect` / `cannot affect` / `has no effect` found no other instance.

**Title changed.** "Reliability Response" appeared in the title and **nowhere else in the
manuscript**; "reliability" occurs three times in total, twice in the body meaning something
the paper argues against. The paper declines damage, life and failure claims throughout, so
the title promised more than the work delivers. Now "Architecture-Dependent **Inelastic
Response** and Physical Realizability", with the keyword list updated to match. Reasoning in
`TCPMT_HOSTILE_REVIEWER_AUDIT.md` R11; a coauthor may revert it.

**Hostile reviewer audit.** Eleven objections written adversarially and answered from the
manuscript: 7 closed, 1 partially closed (the one-sided tolerance bracket), 2 acceptable
declared limitations (constitutive extrapolation, absolute temperatures), 1 editorial blocker
(the title, now fixed). Fourteen further risks inspected; none required content changes.
`TCPMT_HOSTILE_REVIEWER_AUDIT.md`.

**`\balance` disabled.** With the present reference list it balanced the final two columns at
the cost of a 2.46 pt overfull box on the last page. Disabled with an explanatory comment so
the choice is visible and reversible; the build is now 0 overfull.

---

## 10. What was not done

* No new architecture search, optimizer, physical model, constitutive model or design of
  experiments. No configuration changed. Nothing was re-solved: the displacement field in
  Fig. 6(a)(b) is read back from the output the frozen replay already wrote, and the
  extractor refuses to write a field whose peak-to-valley differs from the frozen result.
* No comparison requiring new science. Where a comparison could not be made from evidence
  already in hand, it is marked not available with its reason, in the manuscript itself.
* Four further relevant works could **not** be obtained in full text from this host --- IEEE
  Xplore answers HTTP 418 to scripted retrieval even for items indexed as open access. They
  are cited where they motivate the problem and are left out of the capability matrix rather
  than scored from their abstracts. They are listed by name, with the reason, at the end of
  `PRIOR_FRAMEWORK_COMPARISON.md`.
* Page limits and venue formatting were **not verified** from the publisher's own pages,
  which are unreachable from this host. The manuscript uses a generic IEEE journal class
  and is 15 pages. This must be checked against the author instructions before submission.

---

## 11. Verification after the pass

| check | result |
|---|---|
| manuscript build | 0 errors, 0 undefined references, 0 overfull boxes, 15 pages |
| manuscript audit | passes; see the generated table in `ETM_DVPD_CLAIM_AUDIT.md` |
| negative test of the historical-value guard | fires on the real offending sentence, restored cleanly |
| negative tests of the numeric guard | eight real value corruptions, all caught, manuscript restored each time |
| plotted deformation field against the frozen result | reproduces the peak-to-valley exactly for both architectures |
| frozen global pair after the local-response work | every value bit-identical, asserted in the test suite |
| local-submodel input trace | T_max, T_mean, warpage and du_c all reproduced exactly from the frozen fields before any input was derived |
| local solder integration tolerance | published Phase-0I control reproduced to 0.0000 % at the tolerance used |
| negative tests of the driver/response conflation guard | three real defect wordings, all caught, manuscript restored each time |
| alpha_GaN | provenance traced to an explicit assumption; ordering preserved across a +-33 % sweep |
| timing workflow against the code | mechanics confirmed outside the E-T loop by code inspection and asserted in the test suite |
| framework semantic audit | 0 findings |
| cross-report consistency | 58/58 |
| report PDF text checks | all pass |

Reproduce with `python scripts/phase0mr3c/audit_manuscript.py` and
`python -m pytest tests/phase0mr3c`.
