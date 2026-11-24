#!/usr/bin/env python3
"""The regulator-count screen on a 16x finer switching-frequency grid, under the FULL synthesis
rules of the paper (rated capacitor at its own voltage, switch stress at 0.9 derating,
corrected C_oss, datasheet R_g, body footprints, two-dimensional packing with mixed tiers, at
most four tiers: the environment of the campaign's dse.etm35_p2_t4 job).

The synthesis picks f_sw on a 50-point log grid inside the engine (HVR_FULL_OPT_EPC_V2.py and
HVR_FULL_OPT_sizing.py: np.logspace(log10(0.043e6), log10(200e6), 50)). 785 points split every
interval of that grid into 16 (784 = 49 x 16), so the fine grid is nested: every original
point is kept and a refined optimum can only be equal or lower. This driver

  build  copies the campaign's engine (HVR_DSE_ENGINE, built by scripts/campaign/
         build_dse_engine.py) and research/tcpmt_revision/dse_j35/sweep_etm.py into a private
         directory and changes only (i) the grid size, read from HVR_FSW_NPTS (default 50),
         and (ii) in the driver, the continuous-sizing run of cases A/B, skipped when
         HVR_DSE_DISCRETE_ONLY=1 (the screen is case D, the discrete library); the committed
         engine and driver are never modified;
  check  runs the private copy at 50 points for CHECK_COUNTS and requires the case-D rows of
         the committed screen (case_D_etm35_p2_t4.csv) to be reproduced exactly;
  run    runs every count of the screen at --npts points, one process per count;
  summarize  merges the counts and compares the selection at every count with the 50-point
         screen -> tcpmt_revision/dse_fsw_fine.json.

    python scripts/tcpmt_dse_fsw_grid.py all [--npts 785] [--workers 14]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import multiprocessing as mp
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get("ETM_RESULTS_ROOT") or REPO / "research")      # campaign hook
DATA = ROOT / "tcpmt_revision" / "dse_j35" / "data"
OUT = ROOT / "tcpmt_revision" / "dse_fsw_fine.json"
SCR = Path(os.environ.get("HVR_SCRATCH", "/home/beams0/SABDELZAHER/ETM_project/scratch_campaign"
                                         "/campaign_v3"))
ENGINE_SRC = Path(os.environ.get("HVR_DSE_ENGINE", str(SCR / "dse_engine")))
PRIV = SCR / "dse_engine_fsw"
DRIVER = REPO / "research" / "tcpmt_revision" / "dse_j35" / "sweep_etm.py"
REF_TAG = "etm35_p2_t4"
#: the counts of the round-3 screen (scripts/campaign/build_manifest.py c27)
COUNTS = [16, 20, 25, 28, 30, 32, 33, 34, 35, 36, 40, 42, 45, 48, 49, 50, 52, 56, 60, 64, 70,
          76, 81, 84, 92, 100, 120]
CHECK_COUNTS = [25, 36]
#: the full synthesis rules of the screen (dse.etm35_p2_t4)
RULES = {"HVR_CAP_RULE": "stress", "HVR_SW_RULE": "stress", "HVR_SW_DERATING": "0.9",
         "HVR_COSS_RULE": "corrected", "HVR_PACK_RULE": "on", "HVR_PACK_KEEPOUT_UM": "50",
         "HVR_RG_RULE": "datasheet", "HVR_FOOTPRINT_RULE": "body", "HVR_TIER_RULE": "mixed",
         "HVR_MAX_TIERS": "4"}
GRID_OLD = "f_sw_values = np.logspace(np.log10(0.043e6), np.log10(200e6), 50)"
GRID_NEW = ("f_sw_values = np.logspace(np.log10(0.043e6), np.log10(200e6), "
            "int(__import__('os').environ.get('HVR_FSW_NPTS', '50')))  "
            "# tcpmt_dse_fsw_grid patch: grid size from HVR_FSW_NPTS")
LOOP_OLD = ('                ("discrete",   run_discrete,   ("C", "D"))):\n'
            '            res, used_cc, errs = [], None, []\n')
LOOP_NEW = ('                ("discrete",   run_discrete,   ("C", "D"))):\n'
            '            if switch_mode == "continuous" and os.environ.get('
            '"HVR_DSE_DISCRETE_ONLY") == "1":\n'
            '                for case in (fixed_case, var_case):\n'
            '                    rows[case].append(dict(M=m, I_vr_A=i_vr, feasible=False,\n'
            '                                           reason="not run (discrete library '
            'only: tcpmt_dse_fsw_grid)"))\n'
            '                continue\n'
            '            res, used_cc, errs = [], None, []\n')
KEYS = ("arch", "hs", "ls", "inductor", "capacitor", "f_sw_Hz", "total_loss_W",
        "conv_loss_total_W", "routing_loss_W", "component_count", "feasible")


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def _replace_once(text, old, new, what):
    if text.count(old) != 1:
        raise RuntimeError(f"{what}: expected exactly one occurrence of {old!r}")
    return text.replace(old, new)


def build():
    PRIV.mkdir(parents=True, exist_ok=True)
    rec = {"engine_src": str(ENGINE_SRC), "files": {}}
    for f in ("HVR_FULL_OPT_EPC_V2.py", "HVR_FULL_OPT_sizing.py",
              "Framework_w_HVR_OPT_sizing_v2.py", "HVR_capacitor_vendor_data.json",
              "EPC-Product-Table.csv"):
        src = ENGINE_SRC / f
        shutil.copy2(src, PRIV / f)
        rec["files"][f] = {"src_md5": md5(src)}
    for f in ("HVR_FULL_OPT_EPC_V2.py", "HVR_FULL_OPT_sizing.py"):
        p = PRIV / f
        with open(p, newline="") as fh:             # keep the original line endings
            txt = fh.read()
        with open(p, "w", newline="") as fh:
            fh.write(_replace_once(txt, GRID_OLD, GRID_NEW, f))
        rec["files"][f]["patched_md5"] = md5(p)
    t = DRIVER.read_text()
    t = _replace_once(t, LOOP_OLD, LOOP_NEW, "driver loop")
    (PRIV / "sweep_etm_fsw.py").write_text(t)
    rec["driver"] = {"src": str(DRIVER), "src_md5": md5(DRIVER),
                     "patched_md5": md5(PRIV / "sweep_etm_fsw.py")}
    eng = ENGINE_SRC / "ENGINE.json"
    if eng.is_file():
        rec["engine_record"] = json.loads(eng.read_text())
    (PRIV / "FSW_ENGINE.json").write_text(json.dumps(rec, indent=1))
    return rec


def _run_one(args):
    m, npts, tag = args
    out = SCR / "dse_fsw" / tag
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, HVR_DSE_ENGINE=str(PRIV), DSE_OUT=str(out), HVR_FSW_NPTS=str(npts),
               HVR_DSE_DISCRETE_ONLY="1", MPLBACKEND="Agg", OMP_NUM_THREADS="1",
               OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", **RULES)
    log = out / f"log_m{m}.txt"
    with open(log, "w") as fh:
        r = subprocess.run([sys.executable, "-B", str(PRIV / "sweep_etm_fsw.py"),
                            "--counts", str(m), "--tag", f"{tag}_m{m}"], env=env, stdout=fh,
                           stderr=subprocess.STDOUT)
    return m, r.returncode, str(log)


def _rows(path):
    return {int(r["M"]): r for r in csv.DictReader(open(path))}


def run(npts, tag, counts, workers):
    with mp.get_context("fork").Pool(min(workers, len(counts))) as pool:
        res = pool.map(_run_one, [(m, npts, tag) for m in counts], chunksize=1)
    bad = [(m, rc, log) for m, rc, log in res if rc != 0]
    if bad:
        raise SystemExit(f"failed counts: {bad}")
    merged = []
    for m in counts:
        merged += list(_rows(SCR / "dse_fsw" / tag / "data" / f"case_D_{tag}_m{m}.csv")
                       .values())
    keys = sorted({k for r in merged for k in r})
    DATA.mkdir(parents=True, exist_ok=True)
    with open(DATA / f"case_D_{tag}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(sorted(merged, key=lambda r: int(r["M"])))
    return DATA / f"case_D_{tag}.csv"


def _same(a, b):
    for k in KEYS:
        x, y = a.get(k, ""), b.get(k, "")
        try:
            if abs(float(x) - float(y)) > 1e-9 * max(1.0, abs(float(y))):
                return False, k
        except ValueError:
            if str(x) != str(y):
                return False, k
    return True, None


def check():
    """The private copy at 50 points must reproduce the committed screen's case-D rows."""
    run(50, "f50_check", CHECK_COUNTS, len(CHECK_COUNTS))
    ref = _rows(DATA / f"case_D_{REF_TAG}.csv")
    new = _rows(DATA / "case_D_f50_check.csv")
    out = {}
    for m in CHECK_COUNTS:
        ok, k = _same(new[m], ref[m])
        out[m] = {"reproduced": ok, "first_difference": k}
        if not ok:
            raise SystemExit(f"M = {m}: the 50-point private copy differs in {k}: "
                             f"{new[m].get(k)} vs {ref[m].get(k)}")
    return out


def _sel(r):
    if r.get("feasible") not in ("True", True):
        return None
    return {"topology": r["arch"], "hs": r["hs"], "ls": r["ls"], "inductor": r["inductor"],
            "capacitor": r["capacitor"], "f_sw_kHz": float(r["f_sw_Hz"]) / 1e3,
            "total_loss_W": float(r["total_loss_W"]),
            "conversion_W": float(r["conv_loss_total_W"]),
            "routing_W": float(r["routing_loss_W"])}


def summarize(npts, tag, chk=None):
    ref = _rows(DATA / f"case_D_{REF_TAG}.csv")
    new = _rows(DATA / f"case_D_{tag}.csv")
    per = {}
    for m in sorted(ref):
        a, b = _sel(ref[m]), _sel(new.get(m, {}))
        same_parts = (a is not None and b is not None and all(
            a[k] == b[k] for k in ("topology", "hs", "ls", "inductor", "capacitor")))
        per[m] = {"grid50": a, "fine": b,
                  "same_parts_and_topology": same_parts if (a and b) else (a is None and
                                                                           b is None),
                  "same_f_sw": (a is not None and b is not None and
                                abs(a["f_sw_kHz"] - b["f_sw_kHz"]) < 1e-6),
                  "loss_change_W": (b["total_loss_W"] - a["total_loss_W"]) if (a and b) else None,
                  "feasibility_same": (a is None) == (b is None)}
    feas = {m: v for m, v in per.items() if v["fine"]}
    opt = min(feas, key=lambda m: feas[m]["fine"]["total_loss_W"])
    opt0 = min((m for m, v in per.items() if v["grid50"]),
               key=lambda m: per[m]["grid50"]["total_loss_W"])
    ranked = sorted(feas, key=lambda m: feas[m]["fine"]["total_loss_W"])
    sq = [m for m in ranked if int(round(m ** 0.5)) ** 2 == m]
    ch = [v["loss_change_W"] for v in per.values() if v["loss_change_W"] is not None]
    out = {"what": "regulator-count screen (case D: architecture re-synthesis from the discrete "
                   "library) on a nested 16x finer switching-frequency grid under the full "
                   "synthesis rules, against the 50-point screen",
           "rules": RULES, "n_grid_points": npts, "n_grid_points_screen": 50,
           "grid": "np.logspace(log10(0.043e6), log10(200e6), n): 785 points split each of the "
                   "49 intervals into 16 (nested)",
           "reference": f"case_D_{REF_TAG}.csv", "fine": f"case_D_{tag}.csv",
           "check_50_points": chk, "engine": json.loads((PRIV / "FSW_ENGINE.json").read_text())
           if (PRIV / "FSW_ENGINE.json").is_file() else None,
           "counts": per, "optimum_fine": opt, "optimum_grid50": opt0,
           "optimum_unchanged": opt == opt0,
           "optimum_selection_unchanged": per[opt]["same_parts_and_topology"] and opt == opt0,
           "optimum_f_sw_unchanged": per[opt]["same_f_sw"] and opt == opt0,
           "runner_up_fine": ranked[1] if len(ranked) > 1 else None,
           "margin_to_runner_up_W": (feas[ranked[1]]["fine"]["total_loss_W"]
                                     - feas[opt]["fine"]["total_loss_W"]) if len(ranked) > 1
           else None,
           "square_ranking_fine": sq,
           "n_counts_selection_changed": sum(1 for v in per.values()
                                             if v["grid50"] and v["fine"]
                                             and not v["same_parts_and_topology"]),
           "n_counts_f_sw_changed": sum(1 for v in per.values()
                                        if v["grid50"] and v["fine"] and not v["same_f_sw"]),
           "n_counts_feasibility_changed": sum(1 for v in per.values()
                                               if not v["feasibility_same"]),
           "loss_change_range_W": [min(ch), max(ch)] if ch else None}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=("build", "check", "run", "summarize", "all"))
    ap.add_argument("--npts", type=int, default=785)
    ap.add_argument("--tag", default="")
    ap.add_argument("--workers", type=int, default=int(os.environ.get("FC_WORKERS", "8")))
    ap.add_argument("--counts", default="")
    a = ap.parse_args()
    tag = a.tag or f"f{a.npts}_t4"
    counts = [int(x) for x in a.counts.split(",")] if a.counts else COUNTS
    chk = None
    if a.stage in ("build", "all"):
        build()
    if a.stage in ("check", "all"):
        chk = check()
        print("50-point check:", chk, flush=True)
    if a.stage in ("run", "all"):
        print("merged:", run(a.npts, tag, counts, a.workers), flush=True)
    if a.stage in ("summarize", "all"):
        s = summarize(a.npts, tag, chk)
        print(json.dumps({k: s[k] for k in ("optimum_fine", "optimum_grid50", "optimum_unchanged",
                                            "optimum_selection_unchanged",
                                            "optimum_f_sw_unchanged", "runner_up_fine",
                                            "margin_to_runner_up_W",
                                            "n_counts_selection_changed",
                                            "n_counts_f_sw_changed", "loss_change_range_W")},
                         indent=1))


if __name__ == "__main__":
    main()
