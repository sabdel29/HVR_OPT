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
- Manifold / uncertainty / ladders / device table (merged ff, 4349327).
  - Manifold plate: dp 65 kPa (was 862); pumping 1.77 W per plate.
  - Unified rule: |D+beta| > U95(D) from a GCI on D's own ladder. 26 of 180 robustness verdicts change
    (24 pending: mesh-differing variants; 2 reversals withdrawn).
  - Ladder rungs are in the drivers; the campaign must run 18 + 12 + 64 rungs.
  - Device table has 11 parts.
  - OPEN: the electrical model uses EPC2057's R_on tempco (8e-3/K) for EPC2055 (datasheet 6e-3/K) -> fix per device.
  - OPEN: verification.tex / compare.tex text and ordering.json still use the old rule.
- Generalization to M=36 (agent running in a worktree based on 31a846c).
- M=36 generalization (merged ff, d506e04).
  - Design record configs/design_points.yaml (HVR_DESIGN, production m36).
  - Mixed-tier cards; per-device R_on tempco.
  - Tier order: all 24 orders AR 8.33 (the 1-mm T1 is always crossed). Chosen order:
    [2HS+2Cf]|[HS+LS]|[LS+L]|[LS+2L].
  - Decoupling: latin6z + 56x1206, k_eq 2.79. Z1 BGA does NOT close at 1.5 A (fallback 220/rail, 1.83 A);
    Z2 closes at 202.
  - Boards: Z1/Z2/Z3 on the 3.2-mm board. The m36t5 design protrudes 273 um below the Z2 board.
  - Smoke r11 results (Z1A/Z1B/Z2A/Z2B/Z3A/Z3B, W / C):
    140.6/135.6, 139.1/120.5, 138.9/141.7, 131.0/98.6, 206.7/213.4, 181.2/127.6.
    The peaks sit in T1 (card kz 1.83: encapsulant gap over the dies).
  - Manifest m36: 263 jobs, 693 core-h, about 13 h.
- Fix agent running: copper posts across the die-to-tier gap; decoupling change to close the Z1 BGA (k_eq <= 2.29).

## Campaign launched 2026-11-19 18:32 (HEAD 53e9390, design m36)
- Fixes before launch:
  - copper-post tier cards (T1 kz 1.83 -> 41.6);
  - dual6 12-phase decoupling, k_eq 2.629;
  - BGA not closed at 1.5 A: Z1 worst-ball 2.20 A (RMS), Z2 1.63 A. TCPMT_BGA_POLICY defaults to "requirement",
    and apply_bga_policy switches policy in post-processing (the user's decision is still pending);
  - routing-aware tier order: m36 = 2HS+2Cf / HS+LS / LS+L / LS+2L, intra-VR routing 5.35 W.
- Smoke r11: Z1-A 134.4 W / 109.2 C; Z2-B 117.7 W / 77.0 C.
- Manifest: 282 jobs, 717 core-h, ETA about 13.8 h on 8 califone jobs + 30 local cores.
- Results root: research/campaign_v3. Log: research/campaign_v3/_campaign/runner.log.
- Status: PY=/home/beams0/MGHARIB/envs/etm/bin/python; $PY scripts/campaign/run.py status -v
- Resume after a crash or kill: rerun `$PY scripts/campaign/run.py run --backend both` (idempotent).
- Next: when the campaign is done, run the macros with ETM_RESULTS_ROOT=research/campaign_v3, then rewrite the
  manuscript and letter.

## 2026-11-19 evening
- BGA decision (user): 2 A per ball nominal (Kuan et al. ASQED 2015, refs.bib Kuan2015Imax); 1.5 A as a
  conservative sensitivity.
  - Ball counts stay fixed at the modelled arrangement (220/rail Z1 and Z2; Z3 685/rail): no reallocation.
  - One rule for all integrations: DC peak x k. The Z1 port-model worst-ball RMS (about 2.2 A) is reported as
    an idealized bound.
  - Paper text: the Z2 ring balls are the 48-V feed balls (same 0.4-mm SAC); Z2 has no 1-V balls; the Cu
    pillars are not counted.
- Campaign runner: 35 local cores at nice 0; local-first; no califone buffer (PBS limits only). Commit f762af1.
- Do not git-stash while the campaign runs: jobs read scripts from this tree.

## 2026-11-22: campaign complete (281/281), rewrite started
- Production (SDEC):
  - Z1 A 135.7 W / 112.1 C (feasible); Z1 B 134.8 W / 108.9 C (feasible)
  - Z2 A 134.8 / 118.5; Z2 B 118.1 / 77.0 (failed bga_sites at 220/rail: artifact, being re-closed at 2 A)
  - Z3 A 200.9 / 184.9 infeasible; Z3 B 154.8 / 80.0 infeasible (sites, IR drop)
  - Die 77-91 C.
- User approved: re-close the 48-V BGA at 2 A (smallest legal count, site fraction <= 0.75). Electrical only; ball layout unchanged.
- Regenerated artifacts copied into manuscript_v2 (6c13a1e). Per-writer macro files (macros_front/methods/results.tex)
  and refs_*.bib (ecdf2cd).
- Running:
  - BGA re-close agent;
  - writer FRONT: abstract, intro, framework, converter_dse, Table I, fig1, fig2, fig_dse;
  - writer METHODS: architectures_models, verification, Table IV gen, fig3, fig4, fig10;
  - writer RESULTS: evaluate, compare, explore, discussion (owns IX-B caveats), conclusion, Table V gen, fig5-9.
- Next: final consistency and number audit; supplement pointers and wrapper; response letter and revision notes;
  then page reduction.
- 2026-11-23: methods writer DONE (Sec. IV-V, Table IV, Figs. 3/4/10; commits f6653ee, 39de107, 9a15acb, 9d82fac).
  - GAP found: the campaign ran only the OLD local solder model on the ideal-decoupling cases. A mechanics agent is now
    running the v2 model (self-consistent law and band, full-displacement submodel, ramp) on the production-state
    joints, plus reflow, board/clamp, encapsulant and interconnect-layer outputs.
  - BGA agent told: rerun the Z1/Z2 production cases (Z1-A +1.17 W from the re-close) and apply 2 A to Z3's 1-V balls
    (667 -> about 500/rail), rerunning the Z3 coupled cases.
  - The results writer must add \label{sec:limits} and the IX-B items (13 % solver warpage difference, no
    through-thickness rung, no manifold CFD, no transient).
- 2026-11-23: results writer DONE (Sec. VI-X, Table V generator, Figs. 5-9; commits 38c8c6b..c1940ec). Comparative
  words are data-driven (\Wr* macros).
  - Research question: "which integration should a kilowatt processor use once converter, package, cooling and
    joints are solved together?"
  - Key statements (before the reruns):
    - neighbours M=25/49: +25.6/+36.6 W, and they fail under cooling A;
    - cooling A: Z1 and Z2 0.9 W apart, Z2's feed +7.6 W, so "neither leads"; rigid plate: only Z1 feasible
      (1.1 K R_on margin);
    - cooling B: Z2 -16.7 W and -31.8 K, Z1 smaller warpage and joint driver;
    - Z3 infeasible in both coolings;
    - the 5-tier design saves 20.9 W but protrudes 273 um under Z2;
    - hot-spot map: the die exceeds 105 C except Z2 under B;
    - 1.5 A per ball never closes.
  - Regeneration order after the reruns: writer macros script, then Table V, then figures.
- The macro generator was verified intact after the results writer's accidental truncation and restore.
- 2026-11-23: front writer DONE (abstract, intro, framework, converter, Tables I/II/S1, Figs. 1/3/4/dse; commits
  55ecdcf..9ff8ed8; Fr* macros).
  - NOTE: 2606.28837v1-3.pdf is [1] Krishnakumar, NOT [17] Choi; the [17] column was filled from [1]'s description
    plus [17]'s abstract. Ask the user for the [17] full text.
  - Final-pass items:
    - k_rms 2.64 vs 2.629;
    - IV-B repeats the 5-tier protrusion;
    - the supp_tables "?" sentence (tcpmt_supplement.py);
    - IV-F must describe the full-displacement drive once the mechanics reruns are in;
    - notation (N4K4 italic vs upright; heading case);
    - hot-spot = core-heavy map 108.5 C (the 157 C coarse run is not in campaign_v3).
- Waiting on: the BGA reruns (agent in background) and the mechanics v2 runs.
- 2026-11-23: mechanics v2 DONE (commits c8236cf..bb36d7c; campaign 341/341 valid; paper 22 pp, supplement 21 pp).
  - Joint response (x1e-3/cycle; Schubert production law, band Xiao/measured Norton):
    - cooling A: Z1 6.80, Z2 3.35, Z3 3.10;
    - cooling B: Z1 5.59, Z2 1.55, Z3 2.13;
    - orderings the same under all laws: A Z3<Z2<Z1, B Z2<Z3<Z1. Z1 now WORST in joint response.
  - Warpage: A Z1 17.5 < Z3 46.9 < Z2 58.1 um; B 5.2 < 7.2 < 17.1. Z1 still best in warpage.
  - The critical-site monotonicity FAILS (7801 of 16107 pairs); Z2's worst joint is an inner site (1.80x under A).
    Asked the agent to make the reported response the max over the candidate sites.
  - Reflow at 245 C: PV 80/127/81 um vs the 80-um coplanarity limit (Z2 1.58x). TCB bonding gap: Z1 148 and Z2 62 um
    vs 8 um (FAIL); Z3 12 vs 50 (pass). Low-CTE EMC brings Z1 to 46 um.
  - Board/clamp and encapsulant: moderate effects; low-CTE EMC gives 4 resolved reversals. Cooling-B robustness:
    86/99 orderings kept, 1 resolved reversal.
  - Writers' \WrEps* and \SchubertRatio are legacy; replace them with \MvEps*. compare.tex:140 "independent" Schubert
    is wrong; classB eps base is legacy.
