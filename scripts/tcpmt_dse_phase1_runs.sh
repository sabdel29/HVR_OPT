#!/usr/bin/env bash
# Regulator-count DSE, TCPMT revision phase 1: switch-voltage rule, corrected C_OSS, packing.
#
# Reuses the sweep driver of the published and corrected-capacitor runs
# (research/tcpmt_revision/dse_j35/sweep_etm.py, case D = re-synthesized topology + discrete
# 90-device EPC library) on a private snapshot of the engine (HVR_DSE_ENGINE; byte-identical
# copies of Scalable_Integrated_VR/src/{HVR_FULL_OPT_EPC_V2,HVR_FULL_OPT_sizing,
# Framework_w_HVR_OPT_sizing_v2}.py, HVR_capacitor_vendor_data.json and EPC-Product-Table.csv).
# Writes research/tcpmt_revision/dse_j35/data/{case_[A-D],all_architectures,meta}_<tag>.*;
# the summary is scripts/tcpmt_dse_phase1_summary.py.
#
# Engine defaults (authors' decisions): corrected capacitor rule, switch rule with derating 0.9,
# corrected C_OSS term, tier packing with a 50-um keep-out. Every flag below is explicit.
#   tag                        rules
#   etm35_p1_legacycheck       all four legacy flags                     (must equal etm35)
#   etm35_p1_swlegacy          corrected capacitor rule, other three legacy
#                                                                        (must equal etm35_caprule_full)
#   etm35_p1a_sw90             (a)  capacitor + switch rule 0.9
#   etm35_p1a_sw95             (a') capacitor + switch rule 0.95 (sensitivity)
#   etm35_p1b_coss             (b)  (a) + corrected C_OSS
#   etm35_p1c_full             (c)  (b) + packing = the full set (all defaults)
#   etm35_p1c_full_sw95        the full set with switch derating 0.95 (sensitivity)
#   *_m81                      the same at M = 81 (9 x 9; not in the 17-count list)
#
# Shared host: nice -n 10, single-threaded processes, at most PAR (default 4) at a time.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PY:-/home/beams0/MGHARIB/envs/etm/bin/python}"
ENG="${HVR_DSE_ENGINE:-/home/beams0/SABDELZAHER/ETM_project/scratch/dse_engine_phase1}"
LOGS="${LOGS:-/home/beams0/SABDELZAHER/ETM_project/scratch/logs_review}"
PAR="${PAR:-4}"
COUNTS=36,40,42,45,48,49,50,52,56,60,64,70,76,84,92,100,120
mkdir -p "$LOGS"
for f in HVR_FULL_OPT_EPC_V2.py HVR_FULL_OPT_sizing.py Framework_w_HVR_OPT_sizing_v2.py \
         HVR_capacitor_vendor_data.json; do
  cmp -s "$REPO/Scalable_Integrated_VR/src/$f" "$ENG/$f" || { echo "engine copy stale: $f"; exit 1; }
done
cmp -s "$REPO/Scalable_Integrated_VR/EPC-Product-Table.csv" "$ENG/EPC-Product-Table.csv"

LEG="HVR_CAP_RULE=legacy HVR_SW_RULE=legacy HVR_COSS_RULE=legacy HVR_PACK_RULE=off"
SWL="HVR_CAP_RULE=stress HVR_SW_RULE=legacy HVR_COSS_RULE=legacy HVR_PACK_RULE=off"
A90="HVR_CAP_RULE=stress HVR_SW_RULE=stress HVR_SW_DERATING=0.9 HVR_COSS_RULE=legacy HVR_PACK_RULE=off"
A95="HVR_CAP_RULE=stress HVR_SW_RULE=stress HVR_SW_DERATING=0.95 HVR_COSS_RULE=legacy HVR_PACK_RULE=off"
B90="HVR_CAP_RULE=stress HVR_SW_RULE=stress HVR_SW_DERATING=0.9 HVR_COSS_RULE=corrected HVR_PACK_RULE=off"
C90="HVR_CAP_RULE=stress HVR_SW_RULE=stress HVR_SW_DERATING=0.9 HVR_COSS_RULE=corrected HVR_PACK_RULE=on HVR_PACK_KEEPOUT_UM=50"
C95="HVR_CAP_RULE=stress HVR_SW_RULE=stress HVR_SW_DERATING=0.95 HVR_COSS_RULE=corrected HVR_PACK_RULE=on HVR_PACK_KEEPOUT_UM=50"

jobs_list() {   # tag|counts|environment  (longest first)
  cat <<EOF
etm35_p1c_full|$COUNTS|$C90
etm35_p1b_coss|$COUNTS|$B90
etm35_p1a_sw90|$COUNTS|$A90
etm35_p1_legacycheck|$COUNTS|$LEG
etm35_p1c_full_sw95|$COUNTS|$C95
etm35_p1a_sw95|$COUNTS|$A95
etm35_p1_swlegacy|$COUNTS|$SWL
etm35_p1c_full_m81|81|$C90
etm35_p1b_coss_m81|81|$B90
etm35_p1a_sw90_m81|81|$A90
etm35_p1a_sw95_m81|81|$A95
etm35_p1c_full_sw95_m81|81|$C95
etm35_p1_swlegacy_m81|81|$SWL
etm35_p1_legacycheck_m81|81|$LEG
EOF
}

run_one() {
  IFS='|' read -r tag counts envs <<<"$1"
  echo "start $tag $(date +%T)"
  ( cd "$REPO/research/tcpmt_revision/dse_j35" && \
    env -u HVR_CAP_RULE -u HVR_SW_RULE -u HVR_SW_DERATING -u HVR_COSS_RULE -u HVR_PACK_RULE \
        -u HVR_PACK_KEEPOUT_UM \
        HVR_DSE_ENGINE="$ENG" DSE_OUT="$REPO/research/tcpmt_revision/dse_j35" \
        OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
        $envs nice -n 10 "$PY" -B sweep_etm.py --counts "$counts" --tag "$tag" \
        > "$LOGS/dse_$tag.log" 2>&1 )
  echo "done  $tag $(date +%T) exit=$?"
}
export -f run_one
export REPO PY ENG LOGS
jobs_list | xargs -P "$PAR" -I{} bash -c 'run_one "$@"' _ {}
