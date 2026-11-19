# Review round 3 — work log (lead)

## Author decisions (2026-11-18)
- Inductor: keep 250 nH / 1.6 mOhm / 1 mm^2. Cite [31] only; no coupling boost; no discussion of coupling.
- Switch stress:
  - S1 blocks Vin/N; stacked high-side switches block max(N-1,2)*Vin/N; low-side switches block Vin/N.
  - Switch derating 0.9 (0.95 as a sensitivity). Capacitor derating stays 0.8.
- Corrected C_oss and the packing check (50-um keep-out) are ADOPTED.
- Die limit is 105 C. Die terminals are assumed on both faces; state this in the paper and give a single-face sensitivity in one sentence.
- Use the rated capacitor everywhere. A0 keeps only the 100-um tier thickness as its assumption.
- Do all review fixes now. Page cuts come later.
- Compute: local cap 30 cores; califone via pioneer, queue cpu_only. See the memory note reference-califone-pbs.

## Supplement S-number map (commit ef390dd), for the main-text pointers
- S2 = converter at each count (new).
- S3 to S6 = material cards / layer stacks / cold plate / heat balance (old "S1-S4").
- S7 = capacitor evidence (main text wrongly says S9).
- S8 = 49-cell flying capacitors.
- S9 to S15 = solder card (sources and ranges in S10).
- S16 = meshes / solvers / runtimes (old S3).
- S17 = verification matrix.
- S18 = uncertainty.
- S19 = feasibility (old S5).
- S20 = scenarios.
- S21 = coupled Z3.
- S22 = capacitor-rule screen (old S15).
- S23 = robustness variants.
- S24 = omitted losses (new; main text wrongly says S7).
- S25 = review-round variants.

## Stale items to regenerate
- Z3 rows in S19, S20, S12, S15, S24 and S25 come from uncoupled cases; Table V R* and board mean are also stale.
- omitted_losses.json was computed with the legacy capacitor.
- The main text cites Paska for E, nu and CTE values, but the solder card lists them as assumptions.
- "steps when ... the capacitor ... changes (Table S2)" is false under the corrected rule.

## Agents and branches
- Converter rules and DSE: main tree, uncommitted.
- Thermal, mechanical, electrical/feasibility and campaign: each in its own worktree branch. Merge them when they report.

## Agent results to merge
- Electrical/feasibility (DONE): branch worktree-agent-a2a7404bcab6b25af, worktree
  .claude/worktrees/agent-a2a7404bcab6b25af, commits a8b0dfc..4e1c62b (already based on 3682fab).
  - Production state is HV_SDEC (k=1.65). BGA count at k=1.65: Z1 128 balls/rail, Z2 ring 102 (S0 was 54/36).
  - Z3 R* = none. 2-oz planes leave a 3.6 W gap against a 6.3 W threshold (unresolved).
  - Static drop: Z3 72/82 mV against the 30-mV limit, so Z3 fails under both coolings.
  - Feasibility filter covers all 107 case files; 55 are infeasible.
  - Z2/Z3 builders support only M=49 for now.
  - electrical.py edits sit in one separated block; reconcile with the converter agent's
    HVR_PRODUCTION_*_RULE flags when merging.
- Converter phase 1 (DONE, main tree uncommitted).
  - Full rules make M=49 infeasible (packing); optimum is M=36 N4K4K_A2 at 115.1 W.
  - Phase 2 running: R_g fix, cap footprints, counts below 36, mixed tiers.
- Supplement (DONE, committed ef390dd).
- Pending: thermal, mechanical, campaign; user decision A/B/C on the design point.
- Campaign (DONE): branch worktree-agent-aa56ec40c1d26e6da, commits f5dd128 (ETM_RESULTS_ROOT hooks, 47 files) and
  85a9b0d (scripts/campaign/).
  - Manifest: 262 jobs, 548 core-h, about 12 h wall time on 8 califone jobs plus 30 local cores.
  - MOOSE runs local-only (no libhdf5 on califone).
  - Blocked: cooling-B and Z3 ladders, A1 for Z2/Z3, Z2/Z3 at M != 49 (hard-coded 49 tiles, N_VR, layer names, TSV count).
- Thermal (DONE, but background work still running): branch worktree-agent-ab32d4fbb7c992915, commits 55a484e..9b55e6b.
  - Nu 6.32 (H1, short wall adiabatic); CFD agrees within -0.3 %. Bulk properties at 29.4 C: Re 857, dp 862 kPa (!).
  - Caloric fix is now production; bottom-plate flow uses the equal-rise rule.
  - Converter cards in research/tcpmt_revision/converter_cards.json (49- and 36-cell). die_T fields added.
  - Hot-spot variant die_hotmap: die max 157 C.
  - Z1-A coarse result: 138.6 W, 107.5 C, die 88.3 C.
- Proposal awaiting the user: a 4-zone manifold plate to bring dp to about 55 kPa.

## Decisions (2026-11-19, user: "yes to all")
1. Design point M=36 (6x6), the best square grid: N3K3, EPC2014C/EPC2055, 805 kHz, at most 4 mixed tiers, 2.99 mm,
   102.4 W screen.
2. Also run the 5-tier version through the chain as the co-design comparison: M=36, N4K4, EPC2014C/EPC2055,
   957 kHz, 91.5 W, 3.73 mm.
3. The rated Murata 0603 GRM188D72A105KE01 is the main capacitor reference; the thin-capacitor A0 is a sensitivity only.
4. Manifold cold plate with 4 streamwise zones, to bring dp from 862 kPa to about 55 kPa.

Merges so far:
- a784d6f converter
- 52e8aa5 thermal
- 95e1eda mechanical
Electrical and campaign merges are being done by the merge agent. Next: generalize Z1/Z2/Z3 for M=36 with mixed tiers,
add the manifold plate, redo the tier order for the new stack, update the manifest, then run the campaign.
