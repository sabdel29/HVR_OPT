#!/usr/bin/env bash
# TCPMT revision: every solver stage that follows the seven production cases (r21), in
# dependency order, in two lanes so the shared host never carries more than ~24 of our
# threads at once.
#
#   lane 1 (local response, fixed 59-um averaging band, amendment 5):
#       collect fields -> direct-feed crossover -> local temporal -> local cycles ->
#       local mesh study (pass 5) -> local solder HV-S0/S1/S2
#   lane 2 (package mesh ladder): r11 / r12 / r31 of Z1 and Z2 at HV-S0
#   lane 3 (class-B sensitivity set, waves of <= 6 concurrent runs): waves 1..7, then the
#       local response at each variant's own critical joint
#
# Usage:  nohup nice -n 10 scripts/tcpmt_post_production.sh [lane1|lane2|lane3|all] &
# Log:    $HVR_SCRATCH/post_production_<lane>.log ; a failed stage is logged and the lane
#         continues with the stages that do not depend on it.
set -uo pipefail
cd "$(dirname "$0")/.."
export PATH=/home/beams0/MGHARIB/envs/etm/bin:$PATH
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export HVR_SCRATCH=/home/beams0/SABDELZAHER/ETM_project/scratch
export HVR_FIELDS=$HVR_SCRATCH/fields
export JOINT_BAND_FRAC=0.16666666666666666          # amendment 5: the fixed averaging band
export FC_THREADS=2 FC_POOL_MAX=8
export SOURCE_DATE_EPOCH=1793000000

LANE=${1:-all}

run() {   # run LOG "label" cmd...
    local log=$1 label=$2; shift 2
    echo "=== $(date '+%F %T') START $label" >> "$log"
    if "$@" >> "$log" 2>&1; then
        echo "=== $(date '+%F %T') DONE  $label" >> "$log"
    else
        echo "!!! $(date '+%F %T') FAILED $label (exit $?)" >> "$log"
        return 1
    fi
}

lane1() {
    local L=$HVR_SCRATCH/post_production_lane1.log
    run "$L" "collect fields" python scripts/final_closure_collect_fields.py \
        Z1:HV_S0 Z2:HV_S0 Z1:HV_S1 Z2:HV_S1
    run "$L" "direct-feed crossover" python scripts/final_closure_direct_feed.py
    # matched thermal references on the revised stacks (the Z1 tier order changed); the
    # AEDT reference needs a licence feature and is logged, not fatal, when unavailable
    for a in Z1 Z2; do
        run "$L" "MOOSE thermal column $a" python scripts/reference_tools/moose_thermal_column.py "$a"
        run "$L" "AEDT thermal column $a" timeout 5400 python scripts/reference_tools/thermal_column_benchmark.py "$a" HV_S0
    done
    run "$L" "local temporal study" python scripts/final_closure_local_mesh.py --temporal &&
    run "$L" "local cycle study" python scripts/final_closure_local_mesh.py --cycles &&
    run "$L" "local mesh study (pass 5)" python scripts/final_closure_local_mesh.py
    for s in HV_S0 HV_S1 HV_S2; do
        run "$L" "local solder $s" python scripts/final_closure_local_solder.py "$s"
    done
    echo "=== LANE 1 COMPLETE $(date '+%F %T')" >> "$L"
}

lane2() {
    local L=$HVR_SCRATCH/post_production_lane2.log
    # nested ladder around production r21: r11 (coarser), r12 (through-thickness), r31
    run "$L" "mesh ladder" python scripts/final_closure_physical_etm.py \
        "Z1:HV_S0:1.1:r11:ITERATIVE CHOLESKY:1" "Z2:HV_S0:1.1:r11:ITERATIVE CHOLESKY:1" \
        "Z1:HV_S0:1.1:r12:ITERATIVE CHOLESKY:1" "Z2:HV_S0:1.1:r12:ITERATIVE CHOLESKY:1" \
        "Z1:HV_S0:1.1:r31:ITERATIVE CHOLESKY:2" "Z2:HV_S0:1.1:r31:ITERATIVE CHOLESKY:2"
    echo "=== LANE 2 COMPLETE $(date '+%F %T')" >> "$L"
}

lane3() {
    local L=$HVR_SCRATCH/post_production_lane3.log
    export FC_POOL_MAX=6
    # class-B sensitivities, most decision-relevant first (robustness map rows)
    local W=(
        "tsv_min f2_void z2_cooled attach_sparse z1_tier_reference"
        "icepak_equivalent board_hbot100 board_hbot500 board_h1"
        "gan_k_half board_t3p2 board_eta025 board_eta075"
        "tsv_mid board_h0_h1grid conv_k_tenth pad_drop"
        "z2_cooled_tim bga_depop f1_sidewall_filled attach_h20 attach_h40 attach_sn attach_dense attach_sparse_stiff"
        "attach_stiff feed_heat_at_crossover attach_uf_soft attach_uf_stiff attach_eng_p34 attach_eng_p37 attach_eng_p41"
        "conv_E80_a4 conv_E80_a10 conv_E160_a4 conv_E160_a10"
    )
    local k=1
    for w in "${W[@]}"; do
        # shellcheck disable=SC2086
        run "$L" "sensitivity wave $k: $w" python scripts/final_closure_sensitivity.py $w
        k=$((k + 1))
    done
    run "$L" "sensitivity local responses" python scripts/final_closure_sensitivity.py --local
    echo "=== LANE 3 COMPLETE $(date '+%F %T')" >> "$L"
}

case "$LANE" in
    lane1) lane1 ;;
    lane2) lane2 ;;
    lane3) lane3 ;;
    all) lane1 & lane2 & lane3 & wait ;;
    *) echo "usage: $0 [lane1|lane2|lane3|all]"; exit 2 ;;
esac
