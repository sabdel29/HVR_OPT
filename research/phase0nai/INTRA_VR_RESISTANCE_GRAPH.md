# The detailed intra-VR resistance graph: what exists, and what is actually missing

This item has been asked for across several briefs and reported as outstanding each
time. That framing was wrong. **The graph exists.** It is
`scripts/phase0m/routing.py`, and its output is
`results/phase0m/intra_vr_routing_nets.csv` (896 rows). What is missing is not the
graph but its *migration* onto the corrected physical geometry and its *connection*
to the Phase-0N physical ledger. Naming the gap precisely is the point of this file.

## 1. What the graph contains

Sixteen nets carry the converter from the cell input pad to the output plane, over
five rails and both lateral and vertical geometry. At the nominal case
(R0, one layer, 10 um Cu, `A_min_capability` via policy):

| net | rail | geom | layer | length mm | R mOhm | I_rms A | feasible |
|---|---|---|---|---|---|---|---|
| vin_to_hs0 | HV | lateral | HS_RDL | 1.3422 | 17.9623 | 0.1595 | yes |
| vin_to_hs1 | HV | lateral | HS_RDL | 2.1317 | 28.5283 | 0.1595 | yes |
| vin_to_hs2 | HV | lateral | HS_RDL | 2.9212 | 39.0944 | 0.1595 | yes |
| hs0_to_cf | SC | lateral | PL2 | 0.1974 | 0.4151 | 1.0149 | yes |
| hs1_to_cf | SC | lateral | PL2 | 0.5921 | 1.2452 | 1.0149 | yes |
| hs2_to_cf | SC | lateral | PL2 | 0.1974 | 0.4151 | 1.0149 | yes |
| hs0_to_ls0 | MID | vertical | — | 0.6455 | 2.6072 | 0.4784 | yes |
| hs1_to_ls1 | MID | vertical | — | 0.6455 | 2.6072 | 0.4784 | yes |
| hs2_to_ls2 | MID | vertical | — | 0.6455 | 2.6072 | 0.4784 | yes |
| ls0_to_L0 | SW | vertical | — | 0.8230 | 0.2582 | 6.8027 | yes |
| ls1_to_L1 | SW | vertical | — | 0.8230 | 0.2582 | 6.8027 | yes |
| ls2_to_L2 | SW | vertical | — | 0.8230 | 0.2582 | 6.8027 | yes |
| L0_to_vout | LV | vertical | — | 0.2500 | 0.0784 | 6.8027 | yes |
| L1_to_vout | LV | vertical | — | 0.2500 | 0.0784 | 6.8027 | yes |
| L2_to_vout | LV | vertical | — | 0.2500 | 0.0784 | 6.8027 | yes |
| **vout_plane** | LV | lateral | PL3 | 0.7895 | 0.7114 | 20.4082 | **NO** |

Twenty-eight parameter combinations are swept (Cu thickness, layer count, via
policy, current-density rule), so the artifact is a sensitivity study, not a point
estimate. Widths are DERIVED from the current-density rule and feasibility is
reported rather than clipped: the output plane needs 8.6x the width the tile can
give it at one layer of 10 um Cu, and only reaches feasibility at nine layers.

## 2. Four defects in the graph as it stands

**R1 is numerically identical to R0.** The fidelity ladder advertises R1 as
"obstacle-aware Manhattan: components are blockages, routes detour around them".
Across all 28 parameter combinations, all 16 nets have **identical** R0 and R1
lengths, so the R0 -> R1 step supplies no fidelity evidence whatever. Two of the
sixteen nets do have *both* L-corner routes blocked, so the blockage is detected —
but the detour magnitude is then computed only from blocking components whose
**centre** lies inside the route bounding box, while the blockage test uses each
component's **extent**. A component can therefore block the route and contribute a
zero-length detour. This is the same defect class as `allocation_rule='inner_edge'`
in the package network: a declared control that is numerically a duplicate of its
baseline. Until it is fixed, R1 must not be cited as an independent level.

**R2 and R3 are absent from the artifact.** The ladder declares four levels; the
CSV contains two. `r2_sheet()` exists in the module but its results are not in this
file, and R3 (the 3-D crowding extraction) is a separate module.

**The geometry is frozen R3C.** Every length derives from the `DESIGN` dict, whose
`tile_side_mm` is 2.3685438564654024. That is the VR tile, and it is still correct,
but the graph has not been re-derived since the cell pitch was corrected from a
hard-coded 3.0 mm to the actual 3.165243 mm, nor since the Z1/Z2 stacks were fixed.
Tile-internal lengths should be unaffected by the pitch correction — the tile did
not move — but that is an argument, not a check, and no test asserts it.

**It is not wired into the Phase-0N ledger.** `interconnect_loss.ledger()` lists
`P_intraVR_metal` and `P_intraVR_vertical` as `MAT(OPEN, OPEN, OPEN)` while the
manuscript reports `Intra-cell metal` as 3.601 W (Z1) and 3.627 W (Z2) from this
very model. The ledger and the manuscript therefore disagree about whether this
term is known. The ledger is the stricter of the two and should stay OPEN until the
migration above is done, but the disagreement must be visible rather than silent.

## 3. What closing this item requires

1. Fix the centre-versus-extent inconsistency in `obstacle_manhattan`, then re-run
   and show R1 differing from R0 — or show, with a test, that this layout genuinely
   has no obstructed net and retire R1 as a level.
2. Emit R2 into the same artifact so the ladder's own claim ("the cheapest level
   that reproduces R2 is what the optimizer should use") can be evaluated.
3. Re-derive on current geometry with an explicit assertion that tile-internal
   lengths are independent of the cell pitch.
4. Carry the result into `interconnect_loss` with an RMS scenario, as was done for
   the package RDL, so the ledger and the manuscript stop disagreeing.

None of that is done in this phase. The honest status is **OPEN, with the graph
built and four named defects**, not "no graph exists".
