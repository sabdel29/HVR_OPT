#!/usr/bin/env python3
"""Switching-frequency grid sensitivity of the regulator-count DSE (TCPMT revision).

The synthesis picks f_sw from a 50-point log grid defined in the engine's
run_hvr_optimization (HVR_FULL_OPT_EPC_V2.py:1293 and HVR_FULL_OPT_sizing.py:644):

    f_sw_values = np.logspace(np.log10(0.043e6), np.log10(200e6), 50)

This script builds a PRIVATE copy of the engine and of research/tcpmt_revision/dse_j35/sweep_etm.py
under $HVR_SCRATCH (default /home/beams0/SABDELZAHER/ETM_project/scratch_omitloss), changes
only (i) the grid size, read from HVR_FSW_NPTS, (ii) the engine/output paths and (iii) three
extra output columns (selected inductor, capacitor, grid size), and reruns the sweep. The
committed sweep_etm.py and the shared engine copy are never modified. 99, 197 and 785 points
are nested refinements (every original grid point is kept), so a refined optimum can only be
equal or lower.

    python scripts/tcpmt_omitted_losses_fsw_grid.py            # all stages
    python scripts/tcpmt_omitted_losses_fsw_grid.py --stage n99_sel
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCR = Path(os.environ.get("HVR_SCRATCH", "/home/beams0/SABDELZAHER/ETM_project/scratch_omitloss"))
ENGINE_SRC = Path("/home/beams0/SABDELZAHER/ETM_project/scratch/dse_engine")
ROUTING_SRC = Path("/home/beams0/SABDELZAHER/Salma_Thesis/analysis/system_partitioning_comparison/"
                   "scripts/paper_routing.py")
DRIVER = REPO / "research" / "tcpmt_revision" / "dse_j35" / "sweep_etm.py"
PY = sys.executable

GRID_OLD = "f_sw_values = np.logspace(np.log10(0.043e6), np.log10(200e6), 50)"
GRID_NEW = ("f_sw_values = np.logspace(np.log10(0.043e6), np.log10(200e6), "
            "int(__import__('os').environ.get('HVR_FSW_NPTS', '50')))  "
            "# scratch_omitloss patch: grid size from env")
ALL = "36,40,42,45,48,49,50,52,56,60,64,70,76,84,92,100,120"
STAGES = {  # tag: (grid points, counts)
    "n50_all": (50, ALL),
    "n99_sel": (99, "49,64,70,76"),
    "n197_sel": (197, "49,64,70,76"),
    "n197_all": (197, ALL),
    "n785_all": (785, "36,40,42,45,48,49,50,52,56,60,64,70,76"),
}


def _replace_once(text, old, new, what):
    if text.count(old) != 1:
        raise RuntimeError(f"{what}: expected exactly one occurrence of {old!r}")
    return text.replace(old, new)


def build_private_copy():
    eng = SCR / "engine"
    eng.mkdir(parents=True, exist_ok=True)
    for f in ("HVR_FULL_OPT_EPC_V2.py", "HVR_FULL_OPT_sizing.py",
              "Framework_w_HVR_OPT_sizing_v2.py", "EPC-Product-Table.csv"):
        shutil.copy2(ENGINE_SRC / f, eng / f)
    shutil.copy2(ROUTING_SRC, eng / "paper_routing.py")
    # the engine copy must match the vendored model before the grid patch
    a = (eng / "HVR_FULL_OPT_EPC_V2.py").read_bytes()
    b = (REPO / "Scalable_Integrated_VR" / "src" / "HVR_FULL_OPT_EPC_V2.py").read_bytes()
    if a != b:
        raise RuntimeError("engine HVR_FULL_OPT_EPC_V2.py differs from the vendored model")
    for f in ("HVR_FULL_OPT_EPC_V2.py", "HVR_FULL_OPT_sizing.py"):
        p = eng / f
        with open(p, newline="") as fh:          # keep the original (CRLF) line endings
            txt = fh.read()
        with open(p, "w", newline="") as fh:
            fh.write(_replace_once(txt, GRID_OLD, GRID_NEW, f))
    t = DRIVER.read_text()
    t = _replace_once(t, 'sys.path.insert(0, "/home/beams0/SABDELZAHER/ETM_project/scratch/dse_engine")',
                      f'sys.path.insert(0, "{eng}")', "driver engine path")
    t = _replace_once(t, 'os.chdir("/home/beams0/SABDELZAHER/ETM_project/scratch/dse_engine")',
                      f'os.chdir("{eng}")', "driver chdir")
    t = _replace_once(t, 'sys.path.insert(0, "/home/beams0/SABDELZAHER/Salma_Thesis/analysis/'
                         'system_partitioning_comparison/scripts")',
                      f'sys.path.insert(0, "{eng}")', "driver routing path")
    t = _replace_once(t, 'OUT = "/home/beams0/SABDELZAHER/ETM_project/scratch/dse_j35"',
                      'OUT = os.environ.get("HVR_SCRATCH", "%s") + "/dse_grid"' % SCR, "driver OUT")
    t = _replace_once(t, "        hs=dev(hs), ls=dev(ls),\n",
                      "        hs=dev(hs), ls=dev(ls),\n"
                      '        ind=(res.optimized_inductor.name if res.optimized_inductor is not None else ""),\n'
                      '        cap=(res.optimized_capacitor.name if res.optimized_capacitor is not None else ""),\n'
                      '        n_fsw=int(os.environ.get("HVR_FSW_NPTS", "50")),\n', "driver fields")
    (SCR / "sweep_etm_private.py").write_text(t)
    (SCR / "dse_grid").mkdir(parents=True, exist_ok=True)


def run(tag):
    n, counts = STAGES[tag]
    env = dict(os.environ, HVR_SCRATCH=str(SCR), HVR_FSW_NPTS=str(n), MPLBACKEND="Agg",
               OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    log = SCR / "dse_grid" / f"log_{tag}.txt"
    with open(log, "w") as fh:
        subprocess.run(["nice", "-n", "10", PY, "-B", str(SCR / "sweep_etm_private.py"),
                        "--counts", counts, "--tag", tag], env=env, stdout=fh,
                       stderr=subprocess.STDOUT, check=True)
    print("done", tag, "->", SCR / "dse_grid" / "data" / f"case_D_{tag}.csv")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=sorted(STAGES), action="append")
    ap.add_argument("--no-build", action="store_true")
    a = ap.parse_args()
    if not a.no_build:
        build_private_copy()
    for tag in (a.stage or list(STAGES)):
        run(tag)


if __name__ == "__main__":
    main()
