# ETM-DVPD JOURNAL MANUSCRIPT — BLUEPRINT

> **SUPERSEDED PLANNING DOCUMENT.** This is the blueprint written before the
> manuscript, kept as the record of the planning decisions. Its figure and table
> numbering (7 figures, 4 tables) is **not** the manuscript's: the built paper has 8
> figures and 9 tables, and the depth pass reordered them. For the current mapping of
> claims to floats, read `ETM_DVPD_CLAIM_AUDIT.md`, which is generated from the built
> `.aux` and cannot drift. For what the depth pass added, read `TCPMT_REVISION_LOG.md`.

Authority: `results/PAPER_CLAIM_MATRIX.csv` governs what may be claimed.
Style reference: Krishnakumar *et al.*, arXiv:2606.28837 (June 2026) — register only, no text reuse.

---

## 1. Candidate titles

1. **Electrothermal–Mechanical Co-Design of Distributed Vertical Power Delivery: Architecture-Dependent Reliability Response and Physical Realizability**
2. **A Physically Constrained Electrothermal–Mechanical Framework for Distributed Vertical Power Delivery in High-Performance Computing**
3. **When Thermal and Mechanical Rankings Disagree: Electrothermal–Mechanical Evaluation of Distributed Vertical Power Delivery Architectures**

Title 1 is preferred: it names the framework and both distinguishing results without
overclaiming a synthesis constraint.

## 2. One-sentence thesis

An electrothermal–mechanical framework is developed in which converter synthesis,
rail-aware power delivery, physical interconnect geometry, package thermal transport and
local solder inelastic response are evaluated on one consistent physical stack, and it is
shown that electrical and thermal ranking alone is insufficient to infer either mechanical
response or physical realizability.

## 3. Abstract skeleton (drafted last, 180–230 words)

1. *Problem.* 48 V-to-POL delivery at kW scale; DVPD; existing frameworks optimise
   electrically and thermally, with mechanics and package realizability treated separately.
2. *Framework.* Converter synthesis feeds a geometry-resolved package model; rail-aware
   PPDN; anisotropic thermal model with a physical microchannel boundary; thermoelastic
   package model; convergent local fatigue-relevant inelastic response metric.
3. *Contributions.* Geometry- and architecture-aware coupling; rail-aware vertical
   interconnect; realizability coupled to the same geometry; response metric.
4. *Results.* On a frozen, geometrically realizable repartitioned pair the backside
   architecture runs 8.14 K hotter yet carries 16.3 % lower local inelastic response
   (D = 1.1947).
5. *Interpretation.* The ordering is robust; the magnitude is conditional on an
   extrapolated constitutive model. Mechanics is established as a signoff-relevant
   response quantity, not as an active synthesis constraint.

## 4. Contribution bullets (manuscript language)

**C1.** A geometry- and architecture-aware electrothermal–mechanical framework for DVPD is
presented, in which converter-synthesis outputs — device selection, phase count, switching
frequency, component heights and cell footprint — are propagated into an explicit package
stack rather than into a lumped loss budget.

**C2.** A rail-aware power-delivery network model is developed in which each vertical
segment carries the rail actually assigned to it, and in which the interconnect resistance
is derived from via geometry, allocation policy, temperature-dependent resistivity and the
ground return, rather than from a single lumped crowding factor.

**C3.** Physical realizability is coupled to the same geometry that produces the
electrical and thermal results: component height, tier partition, routing width,
conductor-plane topology and via aspect ratio constrain the architecture, and a
feasibility state is reported separately from a manufacturing-qualification state.

**C4.** A mechanical formulation is developed that progresses from global package
deformation to a mesh- and cycle-converged local fatigue-relevant inelastic response
metric, with the terminology ladder from response to damage to life kept explicit.

**C5.** A system-level result is reported in which thermal and mechanical-response
rankings disagree on a physically realizable pair, and in which the response ordering is
preserved under a complete reconstruction of the vertical interconnect topology.

## 5. Section outline

| § | title | pages |
|---|---|---|
| I | Introduction | 1.25 |
| II | System Architectures and Design Problem (A DVPD; B hybrid VR; C Z1/Z2/Z4/Z5; D coupled variables) | 1.25 |
| III | Electrical and Interconnect Model (A converter loss; B rail-aware assignment; C vertical interconnects; D RDL network; E intra-converter routing and feasibility) | 2.0 |
| IV | Thermal and Mechanical Model (A anisotropic thermal; B cooling boundary; C thermoelastic; D local inelastic response; E coupling sequence) | 1.75 |
| V | Model Validation (A electrical/interconnect; B thermal; C mesh convergence; D cross-solver; E model-domain limits) | 1.25 |
| VI | Cross-Domain Design Analysis (A DVPD mechanical sensitivities; B assembly state; C interconnect geometry and routing feasibility; D architecture-dependent response) | 1.5 |
| VII | Physically Realizable Architecture Study (A repartition; B final Z1/Z2; C temperature–response decoupling; D process-conditional realizability) | 1.5 |
| VIII | Discussion (A when mechanics matters; B what is and is not a synthesis constraint; C scope and limitations) | 1.0 |
| IX | Conclusion | 0.4 |
| — | References | 0.8 |

Target ≈ 12–13 two-column pages.

## 6. Figure and table mapping

Adapted from `results/PAPER_FIGURE_TABLE_PLAN.md`. Two changes are made: the plan's Fig. 3
("which assumptions were falsified") and Fig. 8 ("claim ladder") are internal-audit
constructs. Fig. 3 is recast as a *model-correction sensitivity* figure, which carries the
same evidence as a general modelling result; Fig. 8 is demoted to a table.

| id | intended message | source artifact | § |
|---|---|---|---|
| Fig. 1 | What the framework couples and in what order: E↔T to a fixed point, T→M one-way | `results/phase0m/`, coupling flow | III–IV |
| Fig. 2 | The physical stack and the rail carried by each vertical segment | `results/phase0mr3c/conductor_plane_topology.csv`, `results/phase0mr3b/FIG_0MR3B_ls_to_L_cross_section.png` | III-B, III-E |
| Fig. 3 | Sensitivity of the deciding response ratio to successive model corrections — the ordering is insensitive, the magnitude is not | `results/phase0mr3c/final_etm_replay.csv` and the frozen historical ratios | VI-D |
| Fig. 4 | Assembly state reverses the sign of the footprint–mechanics interaction | `results/phase0e`, `results/phase0f` | VI-B |
| Fig. 5 | The local inelastic-response metric is mesh- and cycle-converged, and is a path length rather than a strain range | `results/phase0i`, `results/phase0ir` | IV-D, V-C |
| Fig. 6 | Conductor-plane topology and repartition: worst via aspect ratio 5.05 → 0.83 | `results/phase0mr3c/routing_feasibility.csv`, `repartition_candidates.csv` | VII-A |
| Fig. 7 | Final Z1/Z2: temperature and response rank oppositely | `results/phase0mr3c/final_etm_replay.csv` | VII-B, VII-C |
| Tab. I | System specification and converter design point | `configs/phase0mr3c/frozen_pair_*.yaml` | II |
| Tab. II | Governing relations of the framework | `results/phase0h/generated_current_facing.md` | III–IV |
| Tab. III | Final pair: losses, temperatures, deformation, response; realizability state | `results/phase0mr3c/final_etm_replay.csv`, `final_pair_status.csv` | VII-B |
| Tab. IV | Claim status: validated, conditional, not claimed | `results/PAPER_CLAIM_MATRIX.csv` | VIII-C |

## 7. Claim-to-evidence mapping

| claim | level | evidence | figure/table |
|---|---|---|---|
| Rail assignment changes vertical interconnect loss by orders of magnitude | 1 | `routing_production.template_loss`, per-template ledger | Fig. 2 |
| Vertical interconnect resistance is geometry-derived and cross-validated | 1 | ΔR against MOOSE, 0.25–0.73 %; 3-D DC column solve at 1.16× series | Tab. II, § V-A |
| Global warpage is not sufficient as a local-reliability metric | 1 | direction tracks, magnitude does not | § VI-A |
| Assembly state materially changes the mechanical conclusion | 1 | free vs mounted sign reversal | Fig. 4 |
| Physical realizability is architecture dependent | 1 | conductor-plane topology, per-net AR and routing ratio | Fig. 6, Tab. III |
| Z2 carries the lower local inelastic response | 1 | D = 1.1947 on the frozen pair | Fig. 7, Tab. III |
| Z2 is hotter while carrying the lower response | 1 | +8.14 K, −16.3 % | Fig. 7 |
| Ordering is preserved under the interconnect reconstruction | 1 | +0.04 % across the correction | Fig. 3 |
| Magnitude of the response advantage | 2 | conditional on a SnAgCu Norton surrogate outside its fitted window | Tab. IV |
| Geometric realizability of the frozen pair | 2 | conditional on a source-bounded microvia pitch | Tab. III |
| Absolute life, N_required, allowable, qualification | 3 | not claimed | Tab. IV |

## 8. Claims intentionally excluded

* mechanics changes the optimal DVPD architecture;
* any absolute lifetime, cycle count, or margin against a requirement;
* PROVEN_REALIZABLE, manufacturable, or process-qualified for either architecture;
* the FE output as damage, or the existence of a damage law, life model or allowable;
* the historical 35.8 % / 12.4 % architecture separation;
* ARCH_Z4 rankings (conditional on an unsourced power-die construction);
* the 50 g/s cooling point (outside the validated correlation domain);
* any optimizer or constrained-optimum result.

## 9. Language and vocabulary

Predominantly passive. No internal phase, gate, defect, checker or freeze vocabulary.
Corrections are presented as modelling results where they generalise — for example,
vertical-interconnect feasibility is evaluated from conductor-plane topology rather than
material-layer count, because redistribution layers act as capture planes — and are
otherwise absorbed into the method.
