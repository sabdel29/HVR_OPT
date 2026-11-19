#!/usr/bin/env bash
# Regulator-count DSE, TCPMT revision phase 2: datasheet gate resistance, capacitor body
# footprints, mixed tiers with a tier limit, and the count range extended downward.
#
# Same driver as phases 0-1 (research/tcpmt_revision/dse_j35/sweep_etm.py, case D) on a private
# snapshot of the engine (HVR_DSE_ENGINE; byte-identical copies of Scalable_Integrated_VR/src/
# {HVR_FULL_OPT_EPC_V2,HVR_FULL_OPT_sizing,Framework_w_HVR_OPT_sizing_v2}.py,
# HVR_capacitor_vendor_data.json, HVR_epc_device_data.json and EPC-Product-Table.csv).
#   tag                    rules
#   etm35_p2_legacycheck   the six legacy flags (17 counts)          must equal etm35
#   etm35_p2_t4            full set, at most 4 tiers (the current stack depth)
#   etm35_p2_tinf          full set, no tier limit (the stack height is reported)
#   etm35_p2_t5            full set, at most 5 tiers
# Full set = corrected capacitor rule + switch rule (derating 0.9) + corrected C_OSS + packing
# (50-um keep-out) + datasheet R_G + capacitor body footprints + mixed tiers.
# Shared host: nice -n 10, single-threaded processes, at most PAR (default 4) at a time.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PY:-/home/beams0/MGHARIB/envs/etm/bin/python}"
ENG="${HVR_DSE_ENGINE:-/home/beams0/SABDELZAHER/ETM_project/scratch/dse_engine_phase2}"
LOGS="${LOGS:-/home/beams0/SABDELZAHER/ETM_project/scratch/logs_review}"
PAR="${PAR:-4}"
C17=36,40,42,45,48,49,50,52,56,60,64,70,76,84,92,100,120
C27=16,20,25,28,30,32,33,34,35,36,40,42,45,48,49,50,52,56,60,64,70,76,81,84,92,100,120
mkdir -p "$LOGS"
for f in HVR_FULL_OPT_EPC_V2.py HVR_FULL_OPT_sizing.py Framework_w_HVR_OPT_sizing_v2.py \
         HVR_capacitor_vendor_data.json HVR_epc_device_data.json; do
  cmp -s "$REPO/Scalable_Integrated_VR/src/$f" "$ENG/$f" || { echo "engine copy stale: $f"; exit 1; }
done
cmp -s "$REPO/Scalable_Integrated_VR/EPC-Product-Table.csv" "$ENG/EPC-Product-Table.csv"

LEG="HVR_CAP_RULE=legacy HVR_SW_RULE=legacy HVR_COSS_RULE=legacy HVR_PACK_RULE=off HVR_RG_RULE=legacy HVR_FOOTPRINT_RULE=legacy"
FULL="HVR_CAP_RULE=stress HVR_SW_RULE=stress HVR_SW_DERATING=0.9 HVR_COSS_RULE=corrected HVR_PACK_RULE=on HVR_PACK_KEEPOUT_UM=50 HVR_RG_RULE=datasheet HVR_FOOTPRINT_RULE=body HVR_TIER_RULE=mixed"

jobs_list() {   # tag|counts|environment
  cat <<EOF
etm35_p2_t4|$C27|$FULL HVR_MAX_TIERS=4
etm35_p2_tinf|$C27|$FULL HVR_MAX_TIERS=0
etm35_p2_t5|$C27|$FULL HVR_MAX_TIERS=5
etm35_p2_legacycheck|$C17|$LEG
EOF
}

run_one() {
  IFS='|' read -r tag counts envs <<<"$1"
  echo "start $tag $(date +%T)"
  ( cd "$REPO/research/tcpmt_revision/dse_j35" && \
    env -u HVR_CAP_RULE -u HVR_SW_RULE -u HVR_SW_DERATING -u HVR_COSS_RULE -u HVR_PACK_RULE \
        -u HVR_PACK_KEEPOUT_UM -u HVR_RG_RULE -u HVR_FOOTPRINT_RULE -u HVR_TIER_RULE \
        -u HVR_MAX_TIERS \
        HVR_DSE_ENGINE="$ENG" DSE_OUT="$REPO/research/tcpmt_revision/dse_j35" \
        OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
        $envs nice -n 10 "$PY" -B sweep_etm.py --counts "$counts" --tag "$tag" \
        > "$LOGS/dse_$tag.log" 2>&1 )
  echo "done  $tag $(date +%T) exit=$?"
}
export -f run_one
export REPO PY ENG LOGS
jobs_list | xargs -P "$PAR" -I{} bash -c 'run_one "$@"' _ {}
