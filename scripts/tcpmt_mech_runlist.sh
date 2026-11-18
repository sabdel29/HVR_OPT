#!/usr/bin/env bash
# TCPMT round 3 -- mechanics / solder campaign run list (findings 1-11).
#
# Order matters: the global cases first (they now store every interconnect layer's site
# kinematics and the membrane/bending split), then the local model (law band -> critical
# check -> checks), then the variants, board, reflow, uncertainty. Run AFTER the thermal
# agent's homogenised tier cards are merged into the stack configs: every card below is
# read from config, so nothing here needs editing for them.
#
# Thread budget: each line states its parallelism; FC_THREADS / LOCAL_THREADS x
# TCPMT_SOLDER_SLOTS is the CalculiX thread count. Steps marked [DONE-ON-CURRENT-FIELDS] were
# run once on the round-2 fields to validate the code; they must be re-run on the new fields.
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH=/home/beams0/MGHARIB/envs/etm/bin:$PATH
export OPENBLAS_NUM_THREADS=1
export HVR_SCRATCH=${HVR_SCRATCH:-/home/beams0/SABDELZAHER/ETM_project/scratch_mech}
export HVR_FIELDS=${HVR_FIELDS:-/home/beams0/SABDELZAHER/ETM_project/scratch/fields}
PY=python

step() { echo; echo "=== $*"; }

# ---------------------------------------------------------------------------- 1. global
step "1a. production cases (all three architectures, S0/S1/S2, production mesh r21): the"
step "    campaign's E-T + mechanics; mechanics() now adds interconnects + decomposition"
# FC_THREADS=4 $PY scripts/final_closure_physical_etm.py Z1:HV_S0:1.1:r21:ITERATIVE\ CHOLESKY:1 ...
step "1b. cooling-tier cases (A: Z3 land-side; B: all three) with the same code"
# $PY scripts/final_closure_sensitivity.py z1_bottom_plate_tim z2_cooled_tim
# $PY scripts/tcpmt_z3land_variants.py run z3_land_t40_A_fvmap ; ... z3_land_t40_B_fvmap
step "1c. collect the converged fields (production and variant cases) into \$HVR_FIELDS"
# $PY scripts/final_closure_collect_fields.py ; $PY scripts/tcpmt_collect_variant_fields.py Z1:z1_bottom_plate_tim Z2:z2_cooled_tim Z3:z3_top_only Z3:z3_plate_tim

# ---------------------------------------------------------------------------- 2. kinematics
step "2. site kinematics of every stored case (all interconnect layers, candidates, split)"
#    1 process, ~20 s per case                                         [DONE-ON-CURRENT-FIELDS]
$PY scripts/tcpmt_mech_kinematics.py

# ---------------------------------------------------------------------------- 3. local model
step "3a. law band: self-consistent window per law at the six tier joints (finding 1)"
#    2-3 slots x 2 threads, ~20 min                                    [DONE-ON-CURRENT-FIELDS]
LOCAL_THREADS=2 TCPMT_SOLDER_SLOTS=3 $PY scripts/tcpmt_mech_law_band.py --run
step "3b. critical-joint check with the v2 model (finding 2): top 30 per measure"
#    ~60 candidates x 11 cases, ~55 s each; 3 slots x 2 threads, ~3 h  [REDUCED RUN DONE: --top 5]
LOCAL_THREADS=2 TCPMT_SOLDER_SLOTS=3 $PY scripts/tcpmt_mech_critical.py --run --top 30
$PY scripts/tcpmt_mech_critical.py --summarize --top 30
step "3c. if a case's maximum-response joint is not its maximum-du joint, the law band is"
step "    re-run at the confirmed joints (joint_site reads solder_critical_v2.json)"
LOCAL_THREADS=2 TCPMT_SOLDER_SLOTS=3 $PY scripts/tcpmt_mech_law_band.py --run
step "3d. local checks: R2->v2 attribution chain, dwell 60/900 s, ramp 30 s, C3D8I/C3D8R,"
step "    L1-L3, 8 cycles, the critical fine-pitch joints (findings 2-4, 11b)"
LOCAL_THREADS=2 TCPMT_SOLDER_SLOTS=3 $PY scripts/tcpmt_mech_local_checks.py --run
$PY scripts/tcpmt_mech_local_checks.py --summarize
step "3e. the law record and the Table S6 source"
$PY scripts/tcpmt_mech_laws.py --record
$PY scripts/tcpmt_solder_parameters.py

# ---------------------------------------------------------------------------- 4. variants
step "4a. new production-mesh variants (findings 6, 7, 11a): mechanics-only on the A field"
FC_POOL_MAX=3 $PY scripts/final_closure_sensitivity.py encap_uf_tg encap_emc_lowcte \
    encap_emc_lowcte_const bga_card_local
step "4b. board-bottom h on all three architectures (full E-T + mechanics)"
FC_POOL_MAX=2 $PY scripts/final_closure_sensitivity.py board_hbot60 board_hbot520 \
    board_hbot100:Z3 board_hbot500:Z3
step "4c. cooling B in the robustness map (finding 8): every mechanics-only variant @B"
FC_POOL_MAX=3 $PY scripts/final_closure_sensitivity.py \
    encap_uf_tg@B encap_emc_lowcte@B encap_emc_lowcte_const@B bga_card_local@B \
    attach_stiff@B:Z2 attach_uf_soft@B:Z2 attach_uf_stiff@B:Z2 \
    conv_E80_a4@B:Z1 conv_E80_a4@B:Z2 conv_E80_a10@B:Z1 conv_E80_a10@B:Z2 \
    conv_E160_a4@B:Z1 conv_E160_a4@B:Z2 conv_E160_a10@B:Z1 conv_E160_a10@B:Z2
step "4d. local responses of every variant (v2 harness, stored kinematics)"
LOCAL_THREADS=2 $PY scripts/final_closure_sensitivity.py --local

# ---------------------------------------------------------------------------- 5. board
step "5. larger board (3x), mounting and clamp, one coarse case per architecture (finding 6)"
#    2 threads each; Z1 ~40 min, Z2 ~60 min, Z3 ~45 min               [DONE: coarse r11]
for A in Z1 Z2 Z3; do FC_THREADS=2 $PY scripts/tcpmt_mech_board.py run $A --factor 3; done
FC_THREADS=2 $PY scripts/tcpmt_mech_board.py run Z1 --factor 3 --hbot 520 --only free
$PY scripts/tcpmt_mech_board.py summarize

# ---------------------------------------------------------------------------- 6. reflow
step "6. reflow / bonding warpage per architecture, production and Tg encapsulants (finding 5)"
for A in Z1 Z2 Z3; do
    FC_THREADS=2 $PY scripts/tcpmt_mech_reflow.py run $A
    for V in encap_uf_tg encap_emc_lowcte; do FC_THREADS=2 $PY scripts/tcpmt_mech_reflow.py run $A --encap $V; done
done
$PY scripts/tcpmt_mech_reflow.py summarize

# ---------------------------------------------------------------------------- 7. closure
step "7. uncertainty (reads the law band; the law spread is model form), bookkeeping, tests"
$PY scripts/tcpmt_uncertainty.py
$PY scripts/phase0mr3c/repartition_search.py --bookkeeping
$PY -m pytest -q -p no:cacheprovider tests/final_closure/test_tcpmt_mech_revision.py
