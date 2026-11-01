# PDF Build Log --- ETM_DVPD_FULL_TECHNICAL_REPORT

Built (SOURCE_DATE_EPOCH 1793000000, 2026-10-26 07:33 UTC) by `scripts/phase0dr/build_pdf.py`.
Verification: **PASSED** (89/89 checks).

## Command

```
pandoc .report_pdf_source.md -o ETM_DVPD_FULL_TECHNICAL_REPORT.pdf --pdf-engine=xelatex --toc --toc-depth=2 -V geometry:margin=2.1cm -V fontsize=10pt -V colorlinks=true -V linkcolor=RoyalBlue -V urlcolor=RoyalBlue --resource-path /home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results
```

## Toolchain

| tool | version |
|:--|:--|
| pandoc | pandoc 2.0.6 |
| TeX | XeTeX 3.14159265-2.6-0.99999 (TeX Live 2018) |
| poppler | pdftotext version 20.11.0 |

## Sources

| file | role | sha256[:16] |
|:--|:--|:--|
| `results/ETM_DVPD_FULL_TECHNICAL_REPORT.md` | Markdown deliverable (4848 lines) | `913f3d0115c78c1f` |
| `scripts/phase0dr/build_full_report.py` | section generator | `46eb57b0307c4700` |
| `scripts/phase0dr/build_full_report2.py` | section generator | `0b785c4181c6a090` |
| `scripts/phase0dr/build_full_report3.py` | section generator | `9956abb8c1518a39` |
| `scripts/phase0dr/build_full_report4.py` | section generator | `c2d6b6a1f2c7f289` |
| `scripts/phase0dr/build_full_report5.py` | section generator | `2987282f3a168e58` |

## Figures embedded

| # | file | kB | caption |
|--:|:--|--:|:--|
| 1 | `results/phase0dr/FIG_H_phase0d_vs_0dr.png` | 84 | **Figure 1.** What the architecture-aware correction changed |
| 2 | `results/phase0b/PHASE0B_DECISIVE_FIGURE_BC_A.png` | 320 | **Figure 2.** Phase-0B decisive figure. Identical converter  |
| 3 | `results/phase0c/PHASE0C_DVPD_LEVER_FIGURE.png` | 383 | **Figure 3.** Phase-0C lever ranking. Red = DVPD-specific, b |
| 4 | `results/phase0d/PHASE0D_ET_VS_ETM_PARETO.png` | 200 | **Figure 4.** Phase-0D ET vs ETM Pareto fronts. Superseded b |
| 5 | `results/phase0dr/FIG_A_power_paths.png` | 128 | **Figure 5.** Architecture-aware power paths. Which rail tra |
| 6 | `results/phase0dr/FIG_C_hv_lv_thickness.png` | 159 | **Figure 6.** HV-TSV vs LV-TSV thickness chain. The LV penal |
| 7 | `results/phase0dr/FIG_B_loss_decomposition.png` | 95 | **Figure 7.** Interconnect loss decomposition. Lateral RDL,  |
| 8 | `results/phase0dr/FIG_F_footprint.png` | 134 | **Figure 8.** Footprint tradeoff after the PPDN correction.  |
| 9 | `results/phase0dr/FIG_G_pareto_corrected.png` | 104 | **Figure 9.** Corrected ET vs ETM Pareto. ET front is a sing |
| 10 | `results/phase0e/FIG_0E_A_metal_stack.png` | 80 | **Figure 10.** The sourced multilayer power stack replaces t |
| 11 | `results/phase0e/FIG_0E_D_rdl_validation.png` | 84 | **Figure 11.** Multilayer RDL compact model against an indep |
| 12 | `results/phase0e/FIG_0E_BC_allocation_feasibility.png` | 119 | **Figure 12.** TSV allocation and the current-capability env |
| 13 | `results/phase0e/FIG_0E_F_footprint_material.png` | 109 | **Figure 13.** Left: the CTE-mismatched material does not sc |
| 14 | `results/phase0e/FIG_0E_G_bcb.png` | 94 | **Figure 14.** Under board restraint warpage collapses while |
| 15 | `results/phase0f/FIG_0F_A_realizable_stack.png` | 125 | **Figure 15.** The height rule. Left: the converter cell mus |
| 16 | `results/phase0f/FIG_0F_B_scaling_chain.png` | 60 | **Figure 16.** Every element of the 240 W vehicle had to be  |
| 17 | `results/phase0f/FIG_0F_C_thickness_margin.png` | 113 | **Figure 17.** The LV-TSV architecture develops an interior  |
| 18 | `results/phase0f/FIG_0F_E_bcb_metric_qualification.png` | 119 | **Figure 18.** Qualifying a board-mounted metric: ordering s |
| 19 | `results/phase0f/FIG_0F_D_footprint_free_vs_mounted.png` | 120 | **Figure 19.** Footprint response in both assembly states at |
| 20 | `results/phase0f/FIG_0F_H_crossover_map.png` | 86 | **Figure 20.** Where mechanics becomes decision-relevant. Le |
| 21 | `results/phase0g/FIG_0G_A_defect30.png` | 97 | FIG-0G-A |
| 22 | `results/phase0g/FIG_0G_B_no_kstar.png` | 96 | FIG-0G-B |
| 23 | `results/phase0g/FIG_0G_C_assembly_regimes.png` | 79 | FIG-0G-C |
| 24 | `results/phase0g/FIG_0G_D_Sh_by_model.png` | 45 | FIG-0G-D |
| 25 | `results/phase0g/FIG_0G_E_footprint_flip.png` | 65 | FIG-0G-E |
| 26 | `results/phase0g/FIG_0G_F_invariance.png` | 70 | FIG-0G-F |
| 27 | `results/phase0g/FIG_0G_G_epsilon.png` | 75 | FIG-0G-G |
| 28 | `results/phase0h/FIG_0H_B_mechanism_map.png` | 62 | FIG-0H-B |
| 29 | `results/phase0h/FIG_0H_C_warpage_not_proxy.png` | 96 | FIG-0H-C |
| 30 | `results/phase0h/FIG_0H_D_admissibility.png` | 74 | FIG-0H-D |
| 31 | `results/phase0h/FIG_0H_E_geometry_closure.png` | 60 | FIG-0H-E |
| 32 | `results/phase0h/FIG_0H_A_defect30_ranking.png` | 102 | FIG-0H-A |
| 33 | `results/phase0h/FIG_0H_F_thickness_final.png` | 120 | FIG-0H-F |
| 34 | `results/phase0i/FIG_0I_A_cross_sections.png` | 81 | FIG-0I-A |
| 35 | `results/phase0i/FIG_0I_B_power_paths.png` | 68 | FIG-0I-B |
| 36 | `results/phase0i/FIG_0I_D_workflow.png` | 62 | FIG-0I-D |
| 37 | `results/phase0i/FIG_0I_F_hysteresis.png` | 105 | FIG-0I-F |
| 38 | `results/phase0i/FIG_0I_C_thermal.png` | 110 | FIG-0I-C |
| 39 | `results/phase0i/FIG_0I_H_loss_vs_damage.png` | 88 | FIG-0I-H |
| 40 | `results/phase0i/FIG_0I_I_relative_life.png` | 97 | FIG-0I-I |
| 41 | `results/phase0i/FIG_0I_G_damage_vs_thickness.png` | 117 | FIG-0I-G |
| 42 | `results/phase0ir/FIG_0IR_A_strain_decomposition.png` | 103 | FIG-0IR-A |
| 43 | `results/phase0ir/FIG_0IR_B_strain_vs_energy.png` | 84 | FIG-0IR-B |
| 44 | `results/phase0ir/FIG_0IR_D_electrical_resolution.png` | 47 | FIG-0IR-D |
| 45 | `results/phase0ir/FIG_0IR_C_relative_life_exponent.png` | 71 | FIG-0IR-C |
| 46 | `results/phase0ir/FIG_0IR_E_warpage_vs_damage.png` | 123 | FIG-0IR-E |
| 47 | `results/phase0j/FIG_0J_A_admissibility_funnel.png` | 74 | FIG-0J-A |
| 48 | `results/phase0j/FIG_0J_C_native_metrics.png` | 97 | FIG-0J-C |
| 49 | `results/phase0j/FIG_0J_B_calibration_not_reproducible.png` | 130 | FIG-0J-B |
| 50 | `results/phase0j/FIG_0J_H_temperature_and_creep.png` | 89 | FIG-0J-H |
| 51 | `results/phase0j/FIG_0J_E_model_form.png` | 110 | FIG-0J-E |
| 52 | `results/phase0j/FIG_0J_D_life_by_architecture.png` | 82 | FIG-0J-D |
| 53 | `results/phase0j/FIG_0J_G_mission_sweep.png` | 76 | FIG-0J-G |
| 54 | `results/phase0j/FIG_0J_F_electrical_cost.png` | 71 | FIG-0J-F |
| 55 | `results/phase0jr/FIG_0JR_A_syed_version_audit.png` | 105 | FIG-0JR-A |
| 56 | `results/phase0jr/FIG_0JR_C_metric_definitions.png` | 75 | FIG-0JR-C |
| 57 | `results/phase0jr/FIG_0JR_B_syed_reproduction.png` | 121 | FIG-0JR-B |
| 58 | `results/phase0jr/FIG_0JR_D_dwell_sensitivity.png` | 114 | FIG-0JR-D |
| 59 | `results/phase0jr/FIG_0JR_E_on_syed_calibration.png` | 92 | FIG-0JR-E |
| 60 | `results/phase0jr/FIG_0JR_F_life_by_primary_law.png` | 76 | FIG-0JR-F |
| 61 | `results/phase0jr/FIG_0JR_G_electrical_vs_life.png` | 87 | FIG-0JR-G |
| 62 | `results/phase0k/FIG_0K_A_g2_decision_map.png` | 122 | FIG-0K-A |
| 63 | `results/phase0k/FIG_0K_E_calibration_vs_mission.png` | 65 | FIG-0K-E |
| 64 | `results/phase0k/FIG_0K_C_discrimination.png` | 93 | FIG-0K-C |
| 65 | `results/phase0k/FIG_0K_F_workflow.png` | 92 | FIG-0K-F |
| 66 | `results/phase0kr/FIG_0KR_A_domain.png` | 99 | FIG-0KR-A |
| 67 | `results/phase0kr/FIG_0KR_B_pair_comparison.png` | 86 | FIG-0KR-B |
| 68 | `results/phase0kr/FIG_0KR_D_beta.png` | 92 | FIG-0KR-D |
| 69 | `results/phase0kr/FIG_0KR_E_power.png` | 108 | FIG-0KR-E |
| 70 | `results/phase0kr/FIG_0KR_F_matrix.png` | 50 | FIG-0KR-F |
| 71 | `results/phase0kr/FIG_0KR_G_workflow.png` | 83 | FIG-0KR-G |
| 72 | `results/phase0l/FIG_0L_G_ratios.png` | 16 | FIG-0L-G |
| 73 | `results/phase0l/FIG_0L_E_damage_weighted.png` | 107 | FIG-0L-E |
| 74 | `results/phase0l/FIG_0L_H_experiment.png` | 57 | FIG-0L-H |
| 75 | `results/phase0lr/FIG_0LR_A_histories.png` | 116 | FIG-0LR-A |
| 76 | `results/phase0lr/FIG_0LR_D_decomposition.png` | 72 | FIG-0LR-D |
| 77 | `results/phase0lr/FIG_0LR_E_ratios.png` | 58 | FIG-0LR-E |
| 78 | `results/phase0lr/FIG_0LR_G_ladder.png` | 103 | FIG-0LR-G |
| 79 | `results/phase0m/FIG_0M_A_tsv_allocation.png` | 141 | FIG-0M-A |
| 80 | `results/phase0m/FIG_0M_B_tsv_coupling.png` | 92 | FIG-0M-B |
| 81 | `results/phase0m/FIG_0M_C_crowding_map.png` | 51 | FIG-0M-C |
| 82 | `results/phase0m/FIG_0M_D_routing_graph.png` | 82 | FIG-0M-D |
| 83 | `results/phase0m/FIG_0M_E_partition_templates.png` | 69 | FIG-0M-E |
| 84 | `results/phase0m/FIG_0M_F_z5_decomposition.png` | 107 | FIG-0M-F |
| 85 | `results/phase0m/FIG_0M_G_k_tensors.png` | 119 | FIG-0M-G |
| 86 | `results/phase0m/FIG_0M_H_cooling.png` | 151 | FIG-0M-H |
| 87 | `results/phase0m/FIG_0M_I_coupling_matrix.png` | 71 | FIG-0M-I |
| 88 | `results/phase0m/FIG_0M_J_priority_ladder.png` | 87 | FIG-0M-J |
| 89 | `results/phase0mr/FIG_0MR_I_before_after.png` | 59 | FIG-0MR-I |
| 90 | `results/phase0mr/FIG_0MR_F_cooling.png` | 77 | FIG-0MR-F |
| 91 | `results/phase0mr/FIG_0MR_C_transition_decomposition.png` | 54 | FIG-0MR-C |
| 92 | `results/phase0mr/FIG_0MR_E_rdl_tensor.png` | 55 | FIG-0MR-E |
| 93 | `results/phase0mr/FIG_0MR_K_closure_ladder.png` | 103 | FIG-0MR-K |
| 94 | `results/phase0mr2/FIG_0MR2_A_zstacks.png` | 51 | FIG-0MR2-A |
| 95 | `results/phase0mr2/FIG_0MR2_E_three_phases.png` | 43 | FIG-0MR2-E |
| 96 | `results/phase0mr2/FIG_0MR2_F_decoupling.png` | 57 | FIG-0MR2-F |
| 97 | `results/phase0mr3/FIG_0MR3_A_failure_margins.png` | 47 | FIG-0MR3-A |
| 98 | `results/phase0mr3/FIG_0MR3_G_decoupling.png` | 72 | FIG-0MR3-G |
| 99 | `results/phase0mr3/FIG_0MR3_C_tsv_margin.png` | 111 | FIG-0MR3-C |
| 100 | `results/phase0mr3/FIG_0MR3_D_cooling_validity.png` | 78 | FIG-0MR3-D |
| 101 | `results/phase0mr3a/FIG_0MR3A_tsv_diameter_margin_and_count.png` | 81 | FIG-0MR3A |
| 102 | `results/phase0mr3b/FIG_0MR3B_ls_to_L_cross_section.png` | 93 | FIG-0MR3B |

## Output

```
Title:          Electrothermal–Mechanical Co-Design of Distributed Vertical Power Delivery: Model Development, Falsification Gates, and Coupled Architecture Results
Author:         HVR_Journal_System_Level / ETM-DVPD — HiPerCAS Lab, University of Illinois Chicago
Creator:        LaTeX with hyperref package
Producer:       XeTeX 0.99999
CreationDate:   Mon Oct 26 02:33:20 2026 CDT
Tagged:         no
UserProperties: no
Suspects:       no
Form:           none
JavaScript:     no
Pages:          173
Encrypted:      no
Page size:      612 x 792 pts (letter)
Page rot:       0
File size:      10422286 bytes
Optimized:      no
PDF version:    1.5
```

## Source repairs applied by the build

* blank line inserted before **0 headings** and **0 table header rows** --- without it pandoc (and GitHub) swallow the construct into the preceding paragraph and emit literal `#` / `|` text. The repair is written back to the Markdown, so both deliverables are correct.
* **16 Unicode glyphs** absent from Latin Modern (sigma, rho, eta, alpha, theta, nu, le, approx, subscript-1) replaced with math-mode equivalents for the PDF pass only; code fences, inline code and existing `$math$` are protected. Without this xelatex drops the characters **silently**.

## Verification checks

| check | result | detail |
|:--|:--|:--|
| pdf exists | PASS | -- |
| pdf non-trivial size | PASS | 10.42 MB |
| no glyphs dropped by the font | PASS | 0 dropped |
| every markdown heading typeset as a section | PASS | 265 in md, 265 in tex |
| no literal '#' heading leaked | PASS | -- |
| every markdown table typeset as a table | PASS | 109 in md, 109 in tex |
| no table rows leaked as literal pipes | PASS | 0 leaked cells |
| all figure files exist FROM PANDOC'S WORKING DIRECTORY | PASS | 102 figures; unresolvable [] |
| pandoc fetched every figure | PASS | 0 replaced by alt text: [] |
| figures embedded in pdf | PASS | 204 image objects / 102 figures |
| every figure has a caption | PASS | no empty alt text |
| page count plausible | PASS | 173 pages |
| text layer searchable | PASS | 339263 chars extracted |
| table of contents present | PASS | -- |
| no unresolved image markup | PASS | -- |
| no literal latex leaked into text | PASS | -- |
| expected result present: 'INFEASIBLE' | PASS | -- |
| expected result present: 'Phase-0D-R' | PASS | -- |
| expected result present: 'Phase 0E' | PASS | -- |
| expected result present: 'ECTC-2024' | PASS | -- |
| expected result present: '16.2' | PASS | -- |
| expected result present: '188.8' | PASS | -- |
| expected result present: '46.7' | PASS | -- |
| expected result present: '49.0' | PASS | -- |
| expected result present: '6.633' | PASS | -- |
| expected result present: '8.287' | PASS | -- |
| expected result present: '0.739' | PASS | -- |
| every current-facing guard rejects the sentence it was written for | PASS | -- |
| every current-facing guard has a self-test sentence | PASS | missing: [] |
| no control characters in the guard source | PASS | 0 byte(s) |
| current-facing: thickness called win/win/win | PASS | 0 hit(s) |
| current-facing: architecture-independent thickness asserted | PASS | 0 hit(s) |
| current-facing: ARCH_B interior optimum asserted as current | PASS | 0 hit(s) |
| current-facing: footprint opposition asserted as current | PASS | 0 hit(s) |
| current-facing: R_field still divided by n_req | PASS | 0 hit(s) |
| current-facing: MOOSE package validation still called undone | PASS | 0 hit(s) |
| current-facing: BC-B still called a compliant mounted support | PASS | 0 hit(s) |
| current-facing: unsourced conventional-limit comparison | PASS | 0 hit(s) |
| current-facing: relative life called parameter-free | PASS | 0 hit(s) |
| current-facing: total inelastic claimed without creep | PASS | 0 hit(s) |
| current-facing: 2.5D eliminated as a class | PASS | 0 hit(s) |
| current-facing: 0.300 mm called manufacturable | PASS | 0 hit(s) |
| current-facing: Z1 claimed electrically preferred over Z4 | PASS | 0 hit(s) |
| current-facing: only one mechanical failure mechanism modelled | PASS | 0 hit(s) |
| current-facing: Phase 0K named as the next work | PASS | 0 hit(s) |
| current-facing: -40 C test called validated by the current model | PASS | 0 hit(s) |
| current-facing: 16 specimens claimed sufficient for all scatter | PASS | 0 hit(s) |
| current-facing: one thermal condition claimed to identify the law | PASS | 0 hit(s) |
| current-facing: no lifetime predicted anywhere | PASS | 0 hit(s) |
| current-facing: relative life called exponent-limited | PASS | 0 hit(s) |
| current-facing: withdrawn 1.25-9.18 parametric life span | PASS | 0 hit(s) |
| current-facing: no SAC305 life law asserted | PASS | 0 hit(s) |
| current-facing: solder fatigue said to have no life law | PASS | 0 hit(s) |
| current-facing: N_required called the sole blocker | PASS | 0 hit(s) |
| current-facing: superseded Syed 2004 ORIGINAL constants | PASS | 0 hit(s) |
| current-facing: withdrawn 1.558 relative-life ratio | PASS | 0 hit(s) |
| current-facing: zero-dwell waveform asserted | PASS | 0 hit(s) |
| current-facing: superseded 1.96 % local-proxy thickness result | PASS | 0 hit(s) |
| current-facing: unsourced 1.9-3.8x relative-life ratio | PASS | 0 hit(s) |
| current-facing: mechanics asserted to bind | PASS | 0 hit(s) |
| report carries generated block 'exec_summary' verbatim | PASS | -- |
| report carries generated block 'governing_equations' verbatim | PASS | -- |
| report carries generated block 'validation_status' verbatim | PASS | -- |
| report carries generated block 'publication_claims' verbatim | PASS | -- |
| ANSYS licence is NOT unavailable | PASS | 1 mention(s), 0 unqualified |
| RDL stack is NOT open/assumed | PASS | 0 mention(s), 0 unqualified |
| BC-B is NOT untested | PASS | 0 mention(s), 0 unqualified |
| MOOSE package thermal is NOT untested | PASS | 0 mention(s), 0 unqualified |
| the assembly-state reversal is NOT a current claim | PASS | 3 mention(s), 0 unqualified |
| footprint opposition is NOT current for mounted assemblies | PASS | 17 mention(s), 0 unqualified |
| the ARCH_B interior optimum is NOT current | PASS | 2 mention(s), 0 unqualified |
| BC-B is NOT presented as a valid mounted model | PASS | 0 mention(s), 0 unqualified |
| vertical-tier losses are NOT still per-regulator | PASS | 1 mention(s), 0 unqualified |
| placement spread 188.8 % is NOT current | PASS | 5 mention(s), 0 unqualified |
| exchange rate 16.2 W/um is NOT current | PASS | 6 mention(s), 0 unqualified |
| exchange rate 2.03 W/um is NOT current | PASS | 3 mention(s), 0 unqualified |
| no-constraint-at-240-W is NOT asserted | PASS | 0 mention(s), 0 unqualified |
| RDL magnitudes are not called upper bounds | PASS | 0 mention(s), 0 unqualified |
| 150 um tile is NOT presented as buildable | PASS | 0 mention(s), 0 unqualified |
| the 150 um tile is not current | PASS | 0 mention(s), 0 unqualified |
| 200/500 um substrates are not a current sweep range | PASS | 2 mention(s), 0 unqualified |
| Phase-0B cooling coefficient is not current at 1 kW | PASS | 2 mention(s), 0 unqualified |
| the geometry mismatch is not called harmless | PASS | 3 mention(s), 0 unqualified |
| mechanics is not claimed to bind at 1 kW | PASS | 13 mention(s), 0 unqualified |
| the epsilon sweep is labelled parametric | PASS | 0 mention(s), 0 unqualified |
| withdrawn claim never stands unqualified: ARCH_B infeasibility | PASS | 2 mentions, 0 unqualified |
| withdrawn claim never stands unqualified: the 240 W feasibility negative | PASS | 0 mentions, 0 unqualified |
| stale quantity '2\\.03 W' never presented as final | PASS | 3 mentions, 0 without retraction context |
| stale quantity '1\\.08 %|1\\.08%' never presented as final | PASS | 3 mentions, 0 without retraction context |

## Warnings from the final pass

None.

## Defects this build step found and fixed

These were introduced by the report generators and caught by the checks above, not by reading the PDF:

1. **20 of 33 headings were not headings.** A `\newpage` or a paragraph directly above an ATX heading absorbed it; the TOC listed 13 entries and the text showed a literal `#`. Now checked by comparing heading counts in Markdown and LaTeX.
2. **4 of 16 tables were not tables** --- 142 cells rendered as literal `|` text. Same missing-blank-line cause. Now checked by comparing table counts and asserting zero `\textbar` leakage.
3. **9 glyph classes silently dropped** by Latin Modern. Now a hard failure.
4. **`$\le$0.72` was not parsed as math** --- pandoc ignores a closing `$` followed by a digit, so the raw macro reached the text layer. The sanitiser now inserts a separating space.
