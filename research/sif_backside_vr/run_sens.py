#!/usr/bin/env python3
"""Si-IF backside VR study -- sensitivity sweeps under a shared-host process budget.

Launches the sensitivity sweeps (power mode, 100-um keep-out) as worker budget allows: a job of
JOB_PROCS workers starts only when the workers of all running sif_sweep.py runs of this study
plus the new job stay within BUDGET, and when other users' load (1-min load average minus our
workers) is below OTHER_MAX; otherwise it waits. Normal priority. Then writes sensitivity.json.

    python run_sens.py [--budget 60] [--job-procs 15] [--other-max 30]
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
JOBS = []
for V in ("48", "12"):
    JOBS += [(f"v{V}_core05", ["--vin", V, "--core-scale", "0.5"]),
             (f"v{V}_core2", ["--vin", V, "--core-scale", "2.0"]),
             (f"v{V}_dcrtyp", ["--vin", V, "--dcr", "typ"]),
             (f"v{V}_ton20", ["--vin", V, "--ton-min-ns", "20"]),
             (f"v{V}_enggates", ["--vin", V, "--no-peak-isat", "--no-irms"]),
             (f"v{V}_isat20", ["--vin", V, "--isat", "20"])]


def our_workers():
    """Workers of every running sif_sweep.py of this study (from each main's --procs)."""
    out = subprocess.run(["ps", "-eo", "pid,ppid,args"], capture_output=True, text=True).stdout
    procs = {}
    for line in out.splitlines()[1:]:
        parts = line.split(None, 2)
        if len(parts) == 3 and "sif_sweep.py" in parts[2]:
            procs[int(parts[0])] = (int(parts[1]), parts[2])
    total = 0
    for pid, (ppid, args) in procs.items():
        if ppid not in procs:                                # a main process
            m = re.search(r"--procs\s+(\d+)", args)
            total += int(m.group(1)) if m else 16
    return total


def other_load():
    load1 = float(open("/proc/loadavg").read().split()[0])
    return load1 - our_workers()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=60)
    ap.add_argument("--job-procs", type=int, default=15)
    ap.add_argument("--other-max", type=float, default=30.0)
    args = ap.parse_args()
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
               PYTHONDONTWRITEBYTECODE="1")
    running = []
    for tag, extra in JOBS:
        while True:
            running = [(t, p) for t, p in running if p.poll() is None]
            if (our_workers() + args.job_procs <= args.budget
                    and other_load() < args.other_max):
                break
            time.sleep(20)
        cmd = [PY, "-B", "sif_sweep.py", "--procs", str(args.job_procs), "--tag", tag,
               "--modes", "power", "--ko", "100"] + extra
        log = open(os.path.join(HERE, f"log_{tag}.txt"), "w")
        p = subprocess.Popen(cmd, cwd=HERE, stdout=log, stderr=subprocess.STDOUT, env=env)
        running.append((tag, p))
        print(time.strftime("%H:%M:%S"), "start", tag, "| our workers now", our_workers() + 0,
              flush=True)
        time.sleep(30)                                       # let its workers start
    for tag, p in running:
        p.wait()
        print(time.strftime("%H:%M:%S"), "done", tag, "exit", p.returncode, flush=True)
    subprocess.run([PY, "-B", "sif_sensitivity.py"], cwd=HERE)


if __name__ == "__main__":
    main()
