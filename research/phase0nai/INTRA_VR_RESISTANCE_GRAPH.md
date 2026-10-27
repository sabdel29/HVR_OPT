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

## 2. Defects: two fixed in Phase 0N-AJ, two still open

**R1 was never charging a detour --- FIXED, and the level is now RETIRED.** The
ladder advertised R1 as "obstacle-aware Manhattan: components are blockages,
routes detour around them", yet all 16 nets had identical R0 and R1 lengths in
all 28 parameter combinations. The cause was a split geometric criterion:
blockage was tested against each component's **extent**, while the detour
magnitude was sized only from blockers whose **centre** fell inside the route
bounding box, so a component could block a route and contribute a zero-length
detour. Two further errors sat underneath it --- a component *containing* a
terminal was counted as obstructing the route that starts inside it, and the
`vout_plane` self-net (src == dst, Manhattan length 0) was fed to a
point-to-point router at all.

The router now applies one geometric test to both decisions and falls back to
offset Z-routes drawn from the blockers' own edges. It detours correctly on a
synthetic obstruction (+0.48 mm on a deliberately walled test case, asserted in
`tests/phase0naj`), and with that capability proven, **zero of the 16 physical
nets are obstructed**. R1 therefore reproduces R0 for a real reason rather than
a broken one, and is **retired** as a fidelity level instead of having a
difference manufactured for it.

**R2 was computed and never compared --- FIXED.** `r2_sheet()` had been
emitting 16 rows into `results/phase0m/intra_vr_routing_model.csv` all along,
but nothing compared them with R0, so the ladder's own question --- "the
cheapest level that reproduces R2 is what the optimizer should use" --- had no
answer anywhere. It does now
(`research/phase0naj/fidelity_ladder.json`), and the answer is that **R0 is not
good enough for the output net**:

| t_Cu | layers | R0 (W/VR) | R2 (W/VR) | R0 error vs R2 |
|---|---|---|---|---|
| 5 um | 1 | 0.59260 | 0.43185 | +37.2 % |
| 10 um | 1 | 0.29630 | 0.21592 | +37.2 % |
| 10 um | 2 | 0.14815 | 0.10796 | +37.2 % |
| 10 um | 4 | 0.10581 | 0.05398 | +96.0 % |
| 10 um | 9 | 0.08597 | 0.02399 | +258.3 % |
| 20 um | 1 | 0.14815 | 0.10796 | +37.2 % |
| 40 um | 1 | 0.10581 | 0.05398 | +96.0 % |

At the nominal single layer of 10 um Cu the width-rule Manhattan estimate
overstates the output-net loss by **+37.2 %**, and the error grows to
**+258.3 %** at nine layers because R0's conductor width saturates against the
available tile width while R2's sheet keeps conducting. R2 is the
higher-fidelity model here, not the truth: it solves the same 2-D sheet physics
with real terminal footprints, so agreement with it is model consistency, never
validation.

**The geometry is still frozen R3C.** Every length derives from the `DESIGN`
dict. Tile-internal lengths should be unaffected by the cell-pitch correction
because the tile did not move, but that remains an argument rather than a
check, and no test asserts it.

**It is still not wired into the Phase-0N ledger.** `interconnect_loss.ledger()`
lists `P_intraVR_metal` and `P_intraVR_vertical` as `MAT(OPEN, OPEN, OPEN)`
while the manuscript reports `Intra-cell metal` as 3.601 W (Z1) and 3.627 W
(Z2) from this model, and `Vertical transitions` as 0.011 W. The ledger is the
stricter of the two and stays OPEN; the manuscript must label those values
historical frozen R3C rather than current physical results.

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
