# PAPER FIGURE AND TABLE PLAN

Frozen at the close of Phase 0M-R3C. 8 main figures, 4 main tables. No new decorative figures.

| id | scientific question | source artifact | status | exact claim it supports |
|---|---|---|---|---|
| **Fig. 1** | What does the framework couple, and in what order? | `results/phase0m/FIG_0M_*, phase0f diagrams` | CURRENT | the framework is a closed E<->T loop with one-way T->M, at ETM-L1 |
| **Fig. 2** | What is the physical stack and where does each rail run? | `results/phase0mr3c/FIG_0MR3C_* and the 0M-R3B cross-section` | CURRENT | rail-aware vertical paths; the converter cell resolved into tiers |
| **Fig. 3** | Which assumptions were falsified, and did the answer move? | `results/phase0g generated_status_sections (defect register)` | CURRENT | 22 gates, 64 registered defects, ordering unchanged throughout |
| **Fig. 4** | Does assembly state change the mechanical conclusion? | `results/phase0f, results/phase0e` | CURRENT | the footprint opposition reverses between free and mounted |
| **Fig. 5** | Is the local solder response metric convergent and verified? | `results/phase0i, results/phase0ir` | CURRENT | PEEQ is the inelastic path length; mesh- and cycle-converged |
| **Fig. 6** | What does physical routing do to a numerically good architecture? | `results/phase0mr3b/FIG_0MR3B_ls_to_L_cross_section.png + 0M-R3C repartition` | CURRENT | worst AR 5.05 -> 0.83 by permutation alone |
| **Fig. 7** | Final Z1 vs Z2 on the frozen repartitioned pair. | `results/phase0mr3c/final_etm_replay.csv` | CURRENT | D_driver = 1.1947; Z2 lower response and hotter |
| **Fig. 8** | What is claimed, what is conditional, what is excluded? | `results/PAPER_CLAIM_MATRIX.csv` | CURRENT | the claim ladder: response -> damage -> life -> failure, with the cut line |
| **Tab. I** | The system specification and the converter design point. | `configs/phase0mr3c/frozen_pair_*.yaml` | CURRENT | 1 kW, 48->1 V, 49 cells, N3K3 |
| **Tab. II** | Governing-equation status: current form, superseded form. | `results/phase0h/generated_current_facing.md` | CURRENT | each equation's current form and what it replaced |
| **Tab. III** | Realizability contract and where each candidate stands. | `results/phase0mr3c/final_pair_status.csv` | CURRENT | geometry closes; four process inputs OPEN |
| **Tab. IV** | Open items and their effect on the claims. | `results/phase0mr3c/final_open_items or phase0mr3b` | CURRENT | none of the open items blocks the response-ordering claim |

## Story order

1. framework, architecture and coupling flow (Fig. 1, Tab. I)
2. rail-aware electrical path and the physical stack (Fig. 2)
3. the falsification ladder and the major corrected assumptions (Fig. 3, Tab. II)
4. assembly state and the mechanical-response result (Fig. 4)
5. the local solder-response model and its verification (Fig. 5)
6. the physical routing and realizability correction (Fig. 6, Tab. III)
7. the final Z1/Z2 comparison on the frozen repartitioned pair (Fig. 7)
8. claims, conditionals and limitations (Fig. 8, Tab. IV)

## Excluded from the manuscript

Every absolute-life figure, the withdrawn 35.8 %/12.4 % architecture comparison, the retired calibrated cooling boundary, the 50 g/s cooler point (OUT_OF_MODEL_DOMAIN), and all ARCH_Z4 rankings, which remain conditional on an unsourced power-die construction.
