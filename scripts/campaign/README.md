# TCPMT result campaign

Regenerates every computed result the TCPMT manuscript reads (manuscript_v2 macros, tables,
supplement and figures) into a **campaign root**, locally and on the `califone` PBS node,
without touching the frozen results in `research/`.

| file | role |
|---|---|
| `build_manifest.py` | generates `manifest.yaml` (edit the generator, never the YAML) |
| `manifest.yaml` | 282 jobs (design m36): command, env, deps, outputs, validation, ncpus/mem/walltime, cost evidence |
| `run.py` | runner: `plan`, `seed`, `run`, `status`, `validate`, `reset`, `audit-hooks`, `exec-job` |
| `validators.py` | output checks (`etm`, `feedback`, `json`, `csv`, `frd`, `exists`) |
| `guard/sitecustomize.py` | write guard + frozen-read log, injected into every job via PYTHONPATH |
| `build_dse_engine.py` | builds the DSE engine directory from this checkout (was a hand copy) |
| `trace_reads.py` | records every file a script opens/stats (how the inventory was taken) |

## 1. Output root: `ETM_RESULTS_ROOT`

One variable selects the campaign. When it is set, it **stands in for `research/`**:
`research/final_closure/x.json` is read from and written to `$ETM_RESULTS_ROOT/final_closure/x.json`,
`research/tcpmt_revision/...` to `$ETM_RESULTS_ROOT/tcpmt_revision/...`. The consumers' own outputs
(`results_macros.tex`, `tab_compare.tex`, `tab_uncertainty.tex`, `supplement/*.tex`, `figs/*.pdf`, the
`.frd` parse cache, MOOSE evidence) go to `$ETM_RESULTS_ROOT/manuscript_v2/...` and
`$ETM_RESULTS_ROOT/presentation/...`. Unset, every script behaves exactly as before.
The default campaign root is `research/campaign_v3` (the runner exports it as an absolute path).

The runner also sets, per job, the variables the code already honoured:
`HVR_SCRATCH=<scratch_root>` (solver work trees, `/home/beams0/SABDELZAHER/ETM_project/scratch_campaign/<campaign>`),
`HVR_FIELDS=$HVR_SCRATCH/fields` (collected converged fields), `TCPMT_SRC=<repo>`; it unsets
`TCPMT_RESULTS_DIR` (which still wins over `ETM_RESULTS_ROOT` when set by hand).

**Hooks** (path resolution only; 47 files, +145/-103 lines, one to four lines each, of the form
`Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / ...`, `import os` added where missing):

* producers: `final_closure_{physical_etm, sensitivity, local_mesh, local_solder, direct_feed,
  results, classB, accuracy_matrix, pkg_network, vr_attach, architecture_spec, literature_rules,
  solver_check, countopt}.py`; `tcpmt_{review_variants, collect_variant_fields, z3land_fv,
  z3_landside_estimate, z3land_report, solder_common, solder_z3land, layer_temperatures, tier_feed,
  cooling_spec, dse_caprule_summary, fullpkg_verify, decap_circuit, decap_network, decap_framework,
  decap_flying_caps, decap_parts, omitted_losses}.py`; `phase0nw/z1_design.py`
  (`DEFAULT_PACKAGE_NETWORK`, and `_results_path()` for a design config's `results.dir` /
  `package_network.file`); `reference_tools/{moose_thermal_column, thermal_column_benchmark,
  moose_pkg_rdl_reference}.py`; `research/tcpmt_revision/countopt/{physical_cell, candidate_dse}.py`
* consumers: `tcpmt_{manuscript_macros, review_macros, supplement, capacitor_evidence, uncertainty,
  feasibility, platform}.py`; `manuscript_v2/fig_scripts/style.py` (FC, TR, OUT, MACROS, FIELDS now
  honours `HVR_FIELDS`), `fig_scripts/frd.py` (parse cache under the root: the field-file cache key is
  path-independent, so a campaign would otherwise read the frozen field from the cache)
* `tcpmt_layer_temperatures.py` hard-coded the main checkout as its repo root; it now uses its own
  checkout (`Path(__file__).parents[1]`).
* `research/tcpmt_revision/dse_j35/sweep_etm.py` needed none: `DSE_OUT` / `HVR_DSE_ENGINE` exist.

Reads of **static** inputs (hand-written spec, constants, ANSYS references) stay on the frozen
tree; `run.py audit-hooks` lists them and fails on any unhooked research/ path in a job script.

**Guard.** Every job runs with `guard/sitecustomize.py` on PYTHONPATH. With `ETM_RESULTS_ROOT` set it
raises `PermissionError` on any write, remove, truncate or rename inside the frozen `research/`,
`results/`, `manuscript_v2/` or `presentation/` trees (the campaign root itself excepted; creating an
empty directory is allowed), so an unhooked writer fails instead of overwriting. Every read of a frozen
`research/`/`results/` file is logged to `<root>/_campaign/frozen_reads/<job>.txt`; when a job reads
the frozen copy of an artifact that another manifest job regenerates, the runner records a
**lineage warning** in the ledger and in `status`.

**Seeding.** `run.py seed` copies the static inputs (manifest `static_inputs`: hand-written spec and
mesh policy, ANSYS AEDT/Icepak references, web/PDF-derived vendor data, `z3_land_isothermal.json`)
into the root. `seed --upstream-of GLOB` also copies the frozen outputs of the dependencies of the
selected jobs and marks those jobs `seeded`, so a subset (a smoke test) runs on frozen upstream data.
Seeding never overwrites: files placed in the root beforehand (e.g. a development run of the design's
own upstream results) win over the frozen copies.

**Designs (TCPMT round 3).** The design record (`configs/design_points.yaml`, selector `HVR_DESIGN`)
fixes the regulator count, converter, tiers, routing and the committed production k. The production
design (m36) runs in the root; a job carrying `design: <key>` runs in `<root>/designs/<key>` with its
own scratch and `HVR_DESIGN=<key>` (m36t5: the 5-tier co-design comparison; m36thin: the thin-capacitor
sensitivity; m25 / m49: the count neighbours). `seed` copies the static inputs into every design subroot.
The frozen `research/` artifacts are the round-2 49-cell design's: a model-vs-artifact test reads the
root in force (`ETM_RESULTS_ROOT`) and skips when the artifact is of another design.

## 2. Runner

    PY=/home/beams0/MGHARIB/envs/etm/bin/python
    $PY scripts/campaign/build_manifest.py                 # design m36 (default) -> manifest.yaml
    $PY scripts/campaign/run.py plan [-v]                  # stages, core-h, makespan
    $PY scripts/campaign/run.py seed
    nohup $PY scripts/campaign/run.py run --backend both > campaign.log 2>&1 &   # local + califone
    $PY scripts/campaign/run.py status -v                  # done/valid/running/queued/failed, ETA
    $PY scripts/campaign/run.py run --backend local --stage dse_sweeps --only 'dse.*'
    $PY scripts/campaign/run.py --results-root /path/scratch_root ...             # a test root

**LAUNCH (TCPMT round 3, design m36; ready, not launched).** From the checkout that holds this
branch (the committed manifest is current; regenerate it only if the generator changes), with
`TCPMT_BGA_POLICY` unset (the feasibility stage then reads the per-ball target -- 2 A, with 1.5 A
as a sensitivity -- as a stated requirement; both policies' verdicts are stored either way,
section 4c):

    cd /home/beams0/SABDELZAHER/ETM_project/HVR_OPT_work
    PY=/home/beams0/MGHARIB/envs/etm/bin/python
    $PY scripts/campaign/run.py audit-hooks        # 63 job scripts, 0 unhooked path(s)
    $PY scripts/campaign/run.py plan               # 282 jobs, 0 blocked, 717 core-h, ~13.8 h
    $PY scripts/campaign/run.py seed               # static inputs -> research/campaign_v3
    mkdir -p research/campaign_v3/_campaign
    nohup $PY scripts/campaign/run.py run --backend both > research/campaign_v3/_campaign/runner.log 2>&1 &
    $PY scripts/campaign/run.py status -v          # progress, ETA

* **Dependency-ordered, idempotent, resumable.** A job starts only when its dependencies are `done`,
  `valid` or `seeded`. Before launching, its declared outputs are validated; valid outputs are recorded
  as `valid` and never recomputed unless `--force`. A dependency outside the selection is accepted when
  its outputs validate. State lives in `<root>/_campaign/state.json` (flock-protected, shared by several
  runner processes) and every event in `ledger.jsonl`; each attempt writes `status/<job>.aN.json`
  (rc, validation, wall, max RSS, frozen reads, lineage warnings). Killing and restarting the runner
  loses nothing: local jobs are detached and re-polled by pid, PBS jobs by qstat.
* **Validation** (`validators.py`): ETM cases need `et_converged`, |thermal.energy_residual_rel| <= 1e-4,
  |deposit_residual_rel| <= 1e-6, mechanics without `mechanics_error` (optionally a local response
  without error); feedback cases need `converged` or a recorded, explained runaway
  (`non_convergence.kind` = runaway, with its reason and last iterates; a loop stopped by the pass
  limit still fails: it needs more passes); fields must end with the frd 9999 record; the local
  time study must fix a production first increment (`nonempty: production_dt0_s`).
* **CalculiX job names**: CalculiX refuses an input-deck name over 127 characters (rc 201,
  nothing written). Every solver call runs `ccx` on the deck's bare stem in the deck's directory;
  an absolute name under the campaign scratch tree is longer than that (campaign_v3's first local
  time study failed all 72 solves so, silently, until the local harness was fixed).
* **Local backend**: at most 30 cores summed over all local campaign jobs (from the ledger, so it holds
  across runner processes), every job under `nice -n 10`.
* **PBS backend** (`califone`): `ssh -o BatchMode=yes pioneer /opt/pbs/bin/qsub|qstat|qdel`, queue
  `cpu_only`, `select=1:ncpus=N:mem=Mgb:host=califone`; keeps the user's jobs in the queue at <= 50
  (counted from qstat, so jobs outside the campaign count too; PBS enforces <= 8 running); walltime
  <= 96 h, ncpus <= 112, mem <= 512 GB; scripts and logs in
  `/home/beams/SABDELZAHER/pbs_jobs/etm/<campaign>/{scripts,logs}`. A failed attempt is resubmitted once
  (`--retries`). A job that leaves the queue without a final status is given 4 min for NFS to catch up
  before it is called failed.
* **Threads**: `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `NUMEXPR_NUM_THREADS` =
  ncpus / workers of the job (pool jobs get 1 per worker); CalculiX gets `FC_THREADS` / its argv;
  pooled local-solder studies get `LOCAL_THREADS` and `FC_POOL_MAX` so the total equals ncpus.
* **Memory** (`build_manifest.mem_for`): an ETM job requests its element count x the measured peak
  RSS per 1000 elements of its mesh rung (campaign_v3, E-T + mechanics: r11/r12 0.022 GB, r21
  0.058 GB, r31 0.127 GB; a measured mesh peak where larger: the 49-cell r21 mesh, 11.3 GB) x 1.5,
  at least 6 GB: r31 52 GB, m36 r21 11 GB, m49 r21 17 GB. The earlier flat 0.023 GB per 1000
  elements x 2.5 asked 16 GB for the r31 rungs (peaks 27-32 GB) and 7 GB for the m49 cases, and
  califone killed them at the limit (rc -9). The local-study, solder, MOOSE and DSE requests come
  from the logged model sizes.

## 3. Stages, cost and order

Costs are the frozen runs' own `et_wall_s + mechanics.wall_s (+ local.wall_s)` (or the sum of the
feedback passes), or an analog for a job with no frozen artifact; the frozen runs used 2 threads per
CalculiX solve on a host loaded to ~85 of 96 cores, so the estimates are conservative. `plan` gives the
dependency-aware makespan (longest-path-first list schedule) for 8 concurrent califone jobs + 30
local cores. Proposed priority order (the runner follows the manifest order within what is ready):

Design m36 (TCPMT round 3; `plan` on the generated manifest, 0 blocked):

| # | stage | jobs | core-h | longest job | notes |
|---|---|---:|---:|---:|---|
| 1 | prep | 17 | 25 | 0.6 h | package network of each design, Z3 land sheets, attach lattices, rules, tier order, DSE engine |
| 2 | production | 35 | 141 | 2.4 h | Z1/Z2/Z3 x A/B in the production state (HV_SDEC) + S0/S1 references, Z3 on the coupled land-side bases, field copies, local chain |
| 3 | z3_landside | 10 | 24 | 1.4 h | FV sheets, coupled land-side cases, report |
| 4 | interface_feedback | 6 | 35 | 4.2 h | TIM warpage feedback Z1/Z2/Z3 x A/B |
| 5 | hotspots | 6 | 20 | 1.8 h | die power map Z1/Z2/Z3 x A/B (production state) |
| 6 | count_study | 6 | 18 | 1.6 h | count neighbours m25 / m49: own network + decoupling, Z1 x A/B |
| 7 | thin_cap | 7 | 22 | 1.6 h | m36thin (100-um capacitor), Z1/Z2/Z3 x A/B |
| 8 | co_design | 7 | 22 | 1.6 h | m36t5 (5 tiers, N4K4 at 957 kHz), Z1/Z2/Z3 x A/B |
| 9 | refinement_ladders | 20 | 158 | 5.1 h | production-state rungs r11 (smoke tests) and r31, S0 rungs, solver checks |
| 10 | robustness_map | 110 | 198 | 3.3 h | class-B runs (incl. the gap-post range conv_posts_lower/upper and the mechanics-revision variants encap_* / bga_card_local), local responses, caloric (HV_SDEC) |
| 11 | solder_submodels | 3 | 31 | 2.5 h | constitutive/critical/cycles/band/units, parameters, Z3 land |
| 12 | moose_checks | 5 | 17 | 1.5 h | **local only**: MOOSE does not load on califone |
| 13 | dse_sweeps | 5 | 1 | 0.4 h | p2_t4 / t5 / tinf sweeps + phase-2 summary |
| 14 | derived | 31 | 5 | 0.3 h | results, class B, decoupling chain (+ limits study), design comparison, k check, BGA re-closure, ... |
| 15 | manuscript | 14 | 1 | 0.1 h | macros, supplement, figures under the root |
|  | **total** | **282** | **717** | | |

Makespan (dependency-aware list schedule): **~13.8 h** with 8 califone jobs + 30 local cores
(califone alone 32.9 h, local alone 28.7 h).

Round-2 (m49) table, for reference: 262 jobs (22 blocked), 548 core-h (+161), ~11.7 h; critical
path package network -> Z3 production -> local temporal -> cycles -> mesh study -> solder studies
-> solder Z3 land -> uncertainty -> macros. The round-2 smoke tests ran 3.6x (califone) and 1.9x (local, at
load ~80) faster than the frozen walls the estimates use, so these are upper bounds for the compute
itself; but califone is heavily booked (106/112 cpus and 1.6 of 2 TB assigned when checked), so
queue waits come on top. The runner launches ready jobs longest-remaining-path first; in
`--backend both` it keeps at most `hybrid_buffer` (4) campaign jobs waiting in the PBS queue and
runs the rest locally, and jobs shorter than 15 min prefer the local cores.

## 4. Smoke tests, design m36 (2026-11-19, root `/home/beams0/SABDELZAHER/ETM_project/scratch_campaign/m36smoke/root`)

The production state (HV_SDEC: i_latin6z + ring, k_eq 2.787; package network at the fallback count
of 220 balls per rail) of Z1/Z2/Z3 x A/B on the coarse rung r11. The root was pre-populated with the
development run's M = 36 upstream results (package network, decoupling record, Z3 land sheets, the Z1
S0 case at r11 under the decoupling chain's S0 name), then seeded and run:

    run.py --campaign m36smoke --results-root $ROOT seed --upstream-of 'ladder.*.sdec_*.r11'
    run.py --campaign m36smoke --results-root $ROOT run --backend both --max-cores 6 --only 'ladder.*.sdec_*.r11'

| job | where | wall | P_loss (W) | T_max (C) | die max (C) | energy residual | E-T it |
|---|---|---:|---:|---:|---:|---:|---:|
| `ladder.Z1.sdec_A.r11` | local | 343 s | 140.59 | 135.64 | 88.33 | 8.6e-8 | 4 |
| `ladder.Z1.sdec_B.r11` | local | 534 s | 139.08 | 120.46 | 87.61 | 1.2e-7 | 4 |
| `ladder.Z2.sdec_A.r11` | local | 409 s | 138.93 | 141.69 | 86.71 | 8.1e-8 | 4 |
| `ladder.Z2.sdec_B.r11` | califone PBS 15792 | 234 s | 130.99 | 98.56 | 83.41 | -1.4e-7 | 3 |
| `ladder.Z3.sdec_A.r11` | local (2nd run) | 434 s | 206.66 | 213.36 | 91.81 | 9.6e-8 | 6 |
| `ladder.Z3.sdec_B.r11` | local (2nd run) | 488 s | 181.17 | 127.57 | 86.06 | -4.0e-8 | 5 |

All converged with mechanics and validated. The peak sits in the input-end tier (2 HS + 2 C_fly, card
k_z 1.83 W/m K) everywhere. Z3 under cooling A is as hot as round 2's Z3 A (233 W, 194 C at 49 cells).
The first Z3 attempts (califone) failed in 10 s: the Z3 land-side deposit wrapper did not forward the
manifold plate's keywords (fixed in 717a36c); after `reset` the runner relaunched them.

## 4b. Smoke tests with the gap-post converter cards (2026-11-19, root `/home/beams0/SABDELZAHER/ETM_project/scratch_campaign/m36fix/smoke/root`)

The same six jobs, upstream inputs and decoupling (k_eq 2.787, 220 balls per rail, NOT_CLOSED) as
section 4; only the mixed-tier cards changed: a part shorter than its tier is bridged to the RDLs by
copper posts on its terminals (`tcpmt_converter_cards.py` GAP_MODEL 'posts', production post basis
'land'; the old encapsulant cap is variant `conv_gap_legacy`). m36 cards k_z / k_xy (W/m K): T1 41.6
/ 5.66 (was 1.83 / 5.38), T2 51.6 / 4.09 (21.2), T3 44.2 / 2.83 (38.3), T4 54.5 / 4.37 (43.3).

    run.py --campaign m36posts --results-root $ROOT seed --upstream-of 'ladder.*.sdec_*.r11'
    run.py --campaign m36posts --results-root $ROOT run --backend both --max-cores 6 --only 'ladder.*.sdec_*.r11'

| job | where | wall | P_loss (W) | T_max (C) | peak at | die max (C) | energy residual | E-T it |
|---|---|---:|---:|---:|---|---:|---:|---:|
| `ladder.Z1.sdec_A.r11` | local | 356 s | 138.73 (-1.87) | 110.38 (-25.3) | T1 | 87.94 | -1.7e-7 | 4 |
| `ladder.Z1.sdec_B.r11` | local | 543 s | 137.94 (-1.14) | 107.49 (-13.0) | T1 | 87.44 | -1.5e-7 | 4 |
| `ladder.Z2.sdec_A.r11` | local | 495 s | 137.48 (-1.44) | 117.55 (-24.1) | T1 | 86.61 | -3.2e-7 | 4 |
| `ladder.Z2.sdec_B.r11` | califone PBS 15800 | 287 s | 120.83 (-10.15) | 77.08 (-21.5) | die (T4 74.7) | 77.08 | -2.3e-8 | 4 |
| `ladder.Z3.sdec_A.r11` | califone PBS 15801 | 211 s | 204.78 (-1.88) | 186.09 (-27.3) | T1 | 91.70 | -2.0e-7 | 6 |
| `ladder.Z3.sdec_B.r11` | califone PBS 15802 | 206 s | 157.10 (-24.08) | 79.71 (-47.9) | BGA / board (T4 73.6) | 79.40 | 1.6e-7 | 4 |

All converged with mechanics and validated (differences against section 4 in brackets). Under cooling A
the peak stays in the input-end tier T1 but drops 24-27 K; under cooling B the converter tiers now pass
their heat to the second plate (T1 becomes the coolest tier, 52 C) and the peak moves to the die (Z2)
or the 1 V BGA (Z3), which also lowers the loss of Z2-B and Z3-B by 10 and 24 W (the R_on tempco).

Two consequences for the campaign (both resolved in section 4c). (i) The tier-order rule breaks its ties (every order has the
worst via AR 8.33) by the heat path, which uses these cards: with the posts it prefers T2 and T3
swapped for m36 (21.40 vs 21.71 K for the recorded order, 1.4 %), and reorders m36t5 and m49; the
design record kept its order then, so `prep.tier_order` would have reported a chosen
order different from the record. (ii) The Z1 BGA stays NOT_CLOSED: `tcpmt_decap_placement.py limits`
(on the 220-ball network) gives 2.635 for 12 clock phases (dual6, Z1 1.73 A per ball), 2.61 at the
interleaving limit and < 0.03 from any ring, against the 2.29 Z1 needs; only about 2.9 uF at every
cell (which the stack cannot hold) reaches 1.9.

## 4c. Final preparation before launch (2026-11-19, development root `/home/beams0/SABDELZAHER/ETM_project/scratch_campaign/m36rev/dev`)

**Decoupling (production state).** Adopted the best implementable clock plan of the study: 12
clock phases in two interleaved 6-phase groups (`dual6`, the second group offset by half a phase
step) with the existing ring of 56 x 1206 100-V X7S capacitors. The declared rule
(`tcpmt_decap_placement.RECOMMEND_RULE`) is now: the implementable plan + ring of least nominal
k_eq, implementable = one n-phase clock (rows, Latin squares) or two interleaved n-phase clocks
(`dual<n>`); the 9- and 18-phase plans are alternatives and the spread is the limit (on the
round-2 7 x 7 grid it still returns `i_latin7+c_ring`). k is recomputed on the production rung:
the Z1 S0 case at r21 (112,256 elements, 140.51 W, T_max 112.67 C, 4 E-T iterations, no mechanics) gives **k_eq = 2.629** (2.612-2.651 over the loop-inductance band;
the r11-based study gave 2.635), k_open 3.78, ring ESR 0.046 W. Committed by `commit-k` to
`research/tcpmt_revision/decoupling_by_design.json` -> the record's `decoupling` block. In the
campaign the chain re-derives k on the campaign's own r21 S0 case, `derived.k_check` compares it
with the committed value, and `derived.bga_reclose` re-closes at the derived k (`k_source`).

**48-V BGA** (the authors' decision of 2026-11-19, round3_worklog). At most 220 balls per rail
(`final_closure_pkg_network.N_MAX_PER_RAIL`, legal counts and screen alike), and the count stays
at the network's, the MODELLED ARRANGEMENT (220 per rail for Z1 and Z2; no reallocation). ONE
rule for every integration: the per-ball current is the verified DC peak x k_eq, checked against
the feasibility stage's target (`tcpmt_feasibility.LIMITS`: 2 A per ball, Kuan et al. ASQED 2015;
1.5 A as a conservative sensitivity, also recorded). Z1's worst-ball RMS of the harmonic port
model (`tcpmt_decap_placement.ball_rms_at_counts`, DC + harmonics of every ball with the adopted
plan and ring, all balls tied to an ideal board node) is reported as an idealized bound, not
used for the verdict (Z2 and Z3 have no such model). `derived.bga_reclose` records the verdict
(`bga_count_production.json` `ball_currents_at_count`, rule `RECLOSE_RULE`); the count minima at
the target (`matched_count_dc_rule`, `closure`) are a provisioning sensitivity, not adopted.
campaign_v3 (k_eq 2.641 from the campaign's own decoupling chain, 220 per rail):

| | DC peak x k_eq (verified, level 2) | worst-ball RMS (port model, idealized bound) | vs 2 A | vs 1.5 A (sensitivity) |
|---|---:|---:|---|---|
| Z1 | 1.73 A | 2.20 A | **passes** | above |
| Z2 | 1.63 A | n/a (no port model of the Z2 feed) | **passes** | above |

Status CLOSED at the 2-A target and NOT_CLOSED at the 1.5-A sensitivity (`status_at_sensitivity`);
the smallest common count passing 2 A on the screen and the verification level would be 168 per
rail (recorded, not adopted).

**Feasibility: BGA policy.** `tcpmt_feasibility.BGA_POLICY` (env `TCPMT_BGA_POLICY`): `hard` = the
per-ball check (peak per-ball current vs the 2-A target; 1.5 A recorded as the sensitivity,
`ok_at_sensitivity_1p5A`) is a filter; `requirement` (DEFAULT) = a stated requirement on the
package (`bga_requirement` of each record: the current each ball must carry), reported, not a
filter. Every integration takes the same DC peak x k rule (Z1 at its BGA-fed 48-V balls, Z2 at
its ring feed, Z3 at its 1-V balls at DC with equal sharing); Z1's port-model RMS, scaled to the
case's 48-V current, is reported as the bound `I_ball_rms_max_A`. Every record carries `by_bga_policy` (verdict, fails,
unresolved under both), `rankings_by_bga_policy` holds both rankings, and
`apply_bga_policy(doc, policy)` re-derives verdicts, rankings and summary of a stored
`feasibility.json` without rerunning. The site budget (`bga_sites`) stays a filter under both.

**Tier orders: the rule counts routing loss** (the coordinator's decision: the framework's
objective is loss). Every order of the decided tiers takes its part assignment of least
intra-VR routing loss (among the assignments of its best worst-via AR); among the orders tied
on the via criterion the production order is the one of least routing loss, the heat path
deciding only between orders within 0.1 W (`tcpmt_tier_order.RULE`). Routing loss =
`final_closure_ledger.intra_vr`'s model (R0 lateral runs, R0 via stacks, output-plane R2) at
25 C with the 48-V nets at the hot-loop k_open 3.78, all cells (`RoutingModel`, equal to the
ledger to machine precision; a test checks it on the production record). Every order ties on
vias (worst AR 8.33, thin 5.71, m25 5.83, both- and single-face):

| design | chosen order (input end first) | routing (W) | H (K) | runner-up | routing (W) | H (K) |
|---|---|---:|---:|---|---:|---:|
| m36 | 2HS+2Cf / HS+LS / LS+L / LS+2L | 5.35 | 21.71 | 2HS+2Cf / HS+LS / LS+2L / LS+L | 5.34 | 22.47 |
| m36t5 | HS+LS / HS+L+3Cf / HS+LS / LS+2L / HS+LS+L | 2.80 | 24.53 | HS+LS / HS+L+3Cf / HS+LS / HS+LS+L / LS+2L | 2.73 | 24.83 |
| m36thin | m36's (its own choice: HS+LS / 2HS+2Cf / LS+L / LS+2L) | 5.31 | 21.47 | HS+LS / 2HS+2Cf / LS+L / LS+2L | 5.12 | 22.36 |
| m25 | 3HS / LS / LS / HS+2L+3Cf | 14.69 | 26.54 | LS / 3HS / LS / HS+2L+3Cf | 15.19 | 25.86 |
| m49 | 2HS / LS+Cf / LS+Cf / HS+2L | 7.24 | 28.88 | LS+Cf / 2HS / LS+Cf / HS+2L | 7.41 | 31.57 |

The m36 and m36t5 runners-up are 0.006 and 0.069 W cheaper, inside the 0.1-W band, so the heat
path picks the chosen order. The single-face rule picks the same order for every design but
m36thin (whose record keeps m36's order). The heat-path tie-break of the first pass had chosen
m36 2HS+2Cf / LS+L / HS+LS / LS+2L (routing 6.28 W with its best assignment, 12.41 W with the
depth-based assignment it was recorded with), m36t5 3.44 W, m25 16.68 W, m49 10.97 W. m36 is
back on the order of the earlier record (its configs unchanged), now with the least-loss part
assignment (`tier_order.assignment`). Every order with its routing loss (and range over
assignments), heat path, worst via AR and assignment is in `tier_order.json` (`rule_ranking`).
The committed k (above) was derived on the S0 case of the first-pass order; the order enters k
only through the 48-V current and the network temperature (latin6z moved 0.001 between the r11
case of the earlier order and the r21 case of the first-pass order), and the campaign's chain
re-derives it on the production order (`derived.k_check`).

**m25 card.** The EPC2366 is modelled as published (PQFN, die exposed on top, 200-um leadframe at
the published land pattern, silicon path at R_thJC 0.6 K/W, bottom path 1.62 vs R_thJB 1.8 K/W):
its tiers go from k_z 1.62 (the declared mould cap) to 28.25 W/m K (k_xy 1.88 -> 4.41).

**Class-B gates.** `mat.encapsulant_card` and `mat.bga_card_consistency` (named by the
`tcpmt_mech_variants` variants) are registered in `final_closure_classB.GATES` (B1, mechanical
observables, cases from `configs/tcpmt_mech`), and the robustness map runs their cases
(`encap_uf_tg`, `encap_emc_lowcte`, `encap_emc_lowcte_const`, `bga_card_local` x Z1/Z2 + local
responses: +12 jobs). **audit-hooks** passes: `tcpmt_dse_phase2_summary.py` now writes under the
root (it would have written `research/` during the campaign), and the committed
`decoupling_by_design.json` (read and written only by the development step `commit-k`) is listed
as static. New job `derived.decap_limits` (the alternatives of the adopted plan, its own file).

**Smoke** (`ladder.Z1.sdec_A.r11`, `ladder.Z2.sdec_B.r11`, the coarse rung, through the runner
into `/home/beams0/SABDELZAHER/ETM_project/scratch_campaign/m36rev/smoke2/root`, local, 6 cores,
nice 10; upstream: the development network (220/rail) and the dual6 decoupling record above;
the record's routing-loss tier orders):

    run.py --campaign m36rev_smoke2 --results-root $ROOT seed --upstream-of 'ladder.Z1.sdec_A.r11' --upstream-of 'ladder.Z2.sdec_B.r11'
    run.py --campaign m36rev_smoke2 --results-root $ROOT run --backend local --max-cores 6 --only 'ladder.Z1.sdec_A.r11' --only 'ladder.Z2.sdec_B.r11'

| job | wall (E-T + mech) | P_loss (W) | T_max (C) | peak at | die max (C) | energy residual | E-T it | intra-VR (W) | vs 4b (W / K) |
|---|---:|---:|---:|---|---:|---:|---:|---:|---|
| `ladder.Z1.sdec_A.r11` | 206 + 114 s | 134.44 | 109.24 | T1 (caps, HS) | 87.66 | 2.5e-08 | 4 | 6.88 | -4.29 / -1.14 |
| `ladder.Z2.sdec_B.r11` | 289 + 205 s | 117.68 | 76.98 | die | 76.98 | 4.4e-08 | 4 | 6.09 | -3.15 / -0.10 |

Both converged with mechanics and validated. Against section 4b (same order, depth-based part
assignment, latin6z): the intra-VR loss falls 10.35 -> 6.88 W (Z1) and 9.15 -> 6.09 W (Z2) with
the least-loss assignment, Z1's 48-V package terms 0.40 W and the ring ESR 0.07 W with dual6.
The first smoke of this preparation (root `m36rev/smoke`, the heat-path order T2/T3 swapped with
its depth-based assignment) gave 144.18 W / 111.33 C and 126.04 W / 77.28 C (intra-VR 16.03 and
14.16 W): it is what led to the routing-loss rule.

## 4a. Smoke tests, round 2 (2026-11-18, scratch root `/home/beams0/SABDELZAHER/ETM_project/scratch_campaign/smoke`)

    run.py --campaign smoke --results-root $ROOT seed --upstream-of 'ladder.Z1.r11' --upstream-of 'ladder.Z2.r11'
    run.py --campaign smoke --results-root $ROOT run --backend local --only ladder.Z1.r11
    run.py --campaign smoke --results-root $ROOT run --backend pbs   --only ladder.Z2.r11
    scripts/campaign/compare_case.py $ROOT final_closure/etm_Z1_HV_S0_h1.1.json final_closure/etm_Z2_HV_S0_h1.1.json

| job | where | wall | max RSS | vs frozen `research/final_closure/...` |
|---|---|---:|---:|---|
| `ladder.Z1.r11` (Z1 HV-S0, coarse mesh 36,128 el, E-T 4 it + mechanics) | pinback, nice 10, 2 cpu | 460 s (frozen 863 s) | 833 MB | identical: 0 of all numeric leaves differ (P_loss 141.8825 W, T_max 111.328 C, du_c 2.17931 um, residual -3.55e-8) |
| `ladder.Z2.r11` (Z2 HV-S0, 36,280 el, 5 it + mechanics) | califone PBS 15710, 2 cpu / 8 GB | 352 s (frozen 1,256 s) | 832 MB | identical: 0 numeric leaves differ (P_loss 145.1018 W, T_max 121.02 C, du_c 3.14686 um) |

Both read only the expected static inputs from the frozen tree (`pcb_homogenization.json`,
`final_etm_replay.csv`, and for Z2 `z2_direct_feed_architecture.json`): no lineage warnings.
A runner self-test also passed on both backends (dependency order, validation, guard refusing a
write into `research/final_closure/`), and a PBS probe showed MOOSE cannot load on califone.

## 5. Known gaps (no reproducible producer, or not reproducible as committed)

* **ANSYS-only** (seeded as static): `reference_rve.json`, `reference_rve_timing.json`,
  `reference_attach_rve.json`, `reference_thermal_column_{Z1,Z2}.json`, `reference_mech_bilayer.json`,
  `reference_cooling_icepak.json` (AEDT / Icepak, host-local licence; PyAEDT not in the etm env).
  `mech_bilayer_benchmark.py` overwrites its AEDT result with `solved: false` when AEDT is missing.
* **Hand-written inputs** (by design): `z2_direct_feed_architecture.json`, `local_mesh_policy.json`.
* **No producer**: `z3_land_isothermal.json` (recipe: `isothermal_macros` with the t40 land patch);
  `count_optimum_etm.json` (dead probe in `tcpmt_review_macros.agents()`).
* **Web / PDF derived** (static): `capacitor_datasheet_data.json`, `flying_cap_vendor_data.json`
  (Murata API), `omitted_losses_inputs.json` (digitized datasheets).
* **Not runnable at HEAD**: `tcpmt_omitted_losses_fsw_grid.py` (engine md5 check and stale patch
  patterns) -> the f_sw-grid section of `omitted_losses.json` is written `available: false`
  (`\FswFine*` macros become `--`).
* **Out-of-repo code**: `sweep_etm.py` imports `paper_routing.py` from `Salma_Thesis/analysis/...`.
* **Stale/inconsistent on rerun**: `tier_feed_crossover.json` (Z3 tiers point at land-coupled cases,
  ledger unpatched); `direct_feed_crossover.json` and `vr_attach_density_study.json` gain the
  `attach_dense`/wave-5/6 entries they predate; `solver_check/*h0.8*` needs a superseded h0.8 case.
* **Legacy lineage**: `results/phase0mr3c/final_etm_replay.csv` (read at import by `tsv_fields`)
  needs `HVR_LEGACY_ALPHA=1` and writes into `results/`; kept static.
* **Blocked jobs** (22): ladders for cooling B and Z3 land side (sensitivity drivers only solve at
  `E.PRODUCTION_REFINE`), A1 for Z2/Z3 (`run_ratedcf` is Z1-only), count study under B and for Z2/Z3
  (see design point).
* Benign: concurrent sensitivity jobs append to `sensitivity/run_log.json` without a lock (no reader).
* **Class-B gate `geom.tier_order`** (pre-existing): its case `z1_tier_reference` swaps the
  single-class tiers of the 49-cell stack and refuses mixed tiers, so for m36 the gate stays
  PENDING in `classB_resolution.json` (`all_b1_resolved` false); the alternative orders are
  evaluated by `tcpmt_tier_order.py` instead (runner-up and heat path in the design record).

## 6. Design point (M and the synthesized design)

`build_manifest.py --design m49|m36`. The production `m49` is N3K3K_A2, 49 x 5.61 mm2. `m36`
(N4K4K_A2) compiles in `kw1.design_1kw(m_vr=36, topology=(4,4,2))`: EPC2057 high **and** low side,
480.11 kHz, 7.20 mm2 / 2.6833 mm cell (budget 7.94 mm2), 91.39 W at 25 C. What is missing to run it:

* **Z1**: only data -- a `configs/phase0nx/z1_physical_m36.yaml` (design block reproducing the compiled
  design, `cells: 36`, 7.20 mm2 / 2.6833 mm, a tier list with `gan_hs_EPC2057`, `package_network.file`,
  `results.dir`) and its realizable tier order (`countopt/physical_cell.py`); then `final_closure_countopt.py
  net|etm|local|compare` run it as they ran M = 64.
* **Z2/Z3**: code. No design selector (configs fixed: `physical_coords.py:34`, `final_closure_ledger.py:87,
  216,608`); `production_et.build_global` meshes `N_VR=49` tiles of `sqrt(274.89/49)` whatever
  `converter.cells` says (`production_et.py:45-46,134`) -- checked: a 36-cell Z2 config loads, validates
  and still meshes 49 tiles; ledger `N_VR=49`, `RT.DESIGN`, `PAD.size_for_cell(5.61)`, the S1 duty 1/16,
  and the `gan_hs_EPC2014C` layer names are production constants (`final_closure_ledger.py:37-60,145,
  318`); `TSV_N_PER_CELL=1444` (`final_closure_physical_etm.py:119`); conversion loss from the production
  design (`replay_production.compiled_design`); `require_z1` refuses Z2/Z3 under `HVR_Z1_CONFIG`.
  Z3 additionally requires a `gan_hs_EPC2014C` deepest tier and cells/area/side equal to the fixed Z2
  config (`physical_package.py:474-487`).
* **All**: sensitivity, review and land-side drivers write untagged case names and the macro/figure
  scripts read production names, so a non-49 lineage needs its own campaign root (and the consumers
  pointed at the tagged Z1 file).
