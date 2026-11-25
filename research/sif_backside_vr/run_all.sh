#!/usr/bin/env bash
# Si-IF backside VR study: main sweeps and sensitivities, then the report and the figure.
# Shared host: nice -n 10, at most 16 worker processes, one sweep at a time.
#   main        48 V and 12 V; packing modes power (keep-out 50/100/200 um), overhead and
#               rectangular cells (100 um)
#   sensitivity power mode, 100 um: core loss x0.5 and x2, typical DCR, minimum on-time 20 ns,
#               engine gates only (no peak-current / RMS-current gates), I_sat at 20 % drop
set -euo pipefail
cd "$(dirname "$0")"
PY="${PY:-/home/beams0/MGHARIB/envs/etm/bin/python}"
PROCS="${PROCS:-16}"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
run() { echo "start $1 $(date +%T)"; nice -n 10 "$PY" -B sif_sweep.py --procs "$PROCS" "${@:2}" \
          > "log_$1.txt" 2>&1; echo "done  $1 $(date +%T)"; }

if [ "${1:-main}" = "main" ] || [ "${1:-}" = "all" ]; then
  run v48 --vin 48 --tag v48
  run v12 --vin 12 --tag v12
  "$PY" -B sif_report.py --tags v48,v12
  "$PY" -B sif_plot.py
fi
if [ "${1:-}" = "sens" ] || [ "${1:-}" = "all" ]; then
  for V in 48 12; do
    run "v${V}_core05" --vin $V --tag "v${V}_core05" --modes power --ko 100 --core-scale 0.5
    run "v${V}_core2"  --vin $V --tag "v${V}_core2"  --modes power --ko 100 --core-scale 2.0
    run "v${V}_dcrtyp" --vin $V --tag "v${V}_dcrtyp" --modes power --ko 100 --dcr typ
    run "v${V}_ton20"  --vin $V --tag "v${V}_ton20"  --modes power --ko 100 --ton-min-ns 20
    run "v${V}_enggates" --vin $V --tag "v${V}_enggates" --modes power --ko 100 \
        --no-peak-isat --no-irms
    run "v${V}_isat20" --vin $V --tag "v${V}_isat20" --modes power --ko 100 --isat 20
  done
  "$PY" -B sif_sensitivity.py
fi
