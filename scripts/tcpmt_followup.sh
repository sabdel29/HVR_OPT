#!/usr/bin/env bash
# TCPMT revision, follow-up stages (replaces lane 1 of tcpmt_post_production.sh, which is
# left untouched because lanes 2 and 3 are executing from that file):
#
#   fields  (after the Z1/Z2 production mechanics): collect the converged Z1/Z2 fields;
#           matched MOOSE / AEDT thermal columns on the revised stacks
#   local   (after the Z3 production mechanics): collect Z3 fields; direct-feed crossover for
#           Z2 and Z3; local temporal -> cycle -> mesh study (amendment 6: Z1, Z2, Z3);
#           local solder HV-S0/S1/S2; in parallel, the Z3 top-cooling-only variant
#
# Usage:  nohup nice -n 10 scripts/tcpmt_followup.sh fields|local &
set -uo pipefail
cd "$(dirname "$0")/.."
export PATH=/home/beams0/MGHARIB/envs/etm/bin:$PATH
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export HVR_SCRATCH=/home/beams0/SABDELZAHER/ETM_project/scratch
export HVR_FIELDS=$HVR_SCRATCH/fields
export JOINT_BAND_FRAC=0.16666666666666666          # amendment 5/6: the fixed averaging band
export FC_THREADS=2 FC_POOL_MAX=8
export SOURCE_DATE_EPOCH=1793000000

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

fields() {
    local L=$HVR_SCRATCH/followup_fields.log
    run "$L" "collect fields Z1/Z2" python scripts/final_closure_collect_fields.py \
        Z1:HV_S0 Z2:HV_S0 Z1:HV_S1 Z2:HV_S1
    for a in Z1 Z2; do
        run "$L" "MOOSE thermal column $a" python scripts/reference_tools/moose_thermal_column.py "$a"
        run "$L" "AEDT thermal column $a" timeout 5400 \
            python scripts/reference_tools/thermal_column_benchmark.py "$a" HV_S0
    done
    echo "=== FIELDS COMPLETE $(date '+%F %T')" >> "$L"
}

local_chain() {
    local L=$HVR_SCRATCH/followup_local.log
    run "$L" "collect fields Z3" python scripts/final_closure_collect_fields.py Z3:HV_S0
    run "$L" "direct-feed crossover (Z2, Z3)" python scripts/final_closure_direct_feed.py
    ( FC_POOL_MAX=2 run "$L" "Z3 top-cooling-only variant" \
        python scripts/final_closure_sensitivity.py z3_top_only ) &
    run "$L" "local temporal study" python scripts/final_closure_local_mesh.py --temporal &&
    run "$L" "local cycle study" python scripts/final_closure_local_mesh.py --cycles &&
    run "$L" "local mesh study (pass 5, amendment 6)" python scripts/final_closure_local_mesh.py
    for s in HV_S0 HV_S1 HV_S2; do
        run "$L" "local solder $s" python scripts/final_closure_local_solder.py "$s"
    done
    wait
    echo "=== LOCAL COMPLETE $(date '+%F %T')" >> "$L"
}

case "${1:-}" in
    fields) fields ;;
    local) local_chain ;;
    *) echo "usage: $0 fields|local"; exit 2 ;;
esac
