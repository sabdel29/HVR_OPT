#!/usr/bin/env python3
"""Targeted robustness: material corners applied to the strongest DVPD-specific levers only.

Per the Phase-0C brief, the nine-corner suite is NOT repeated for all 20 cases. It is run
for the candidate levers that survived the nominal ranking, because a perturbation is a
SYSTEMATIC uncertainty and the decision-relevant question is whether the LEVER's effect
size and ordering survive it - not whether absolute values move.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase0b"))
from etm.config import load_doe, load_stack          # noqa: E402
from etm.run_case import run_case                    # noqa: E402

R = Path(__file__).resolve().parents[2]
P0B = R / "results" / "phase0b"
OUT = R / "results" / "phase0c"
SENS = dict(h_xy=0.45, z_scale=1.0)

PERTURB = {
    "ref":        dict(),
    "uf_E_lo":    dict(overrides={"underfill_homog": {"E": 0.7}}),
    "uf_E_hi":    dict(overrides={"underfill_homog": {"E": 1.3}}),
    "uf_cte_lo":  dict(overrides={"underfill_homog": {"cte": 0.7}}),
    "uf_cte_hi":  dict(overrides={"underfill_homog": {"cte": 1.3}}),
    "hvr_E_lo":   dict(overrides={"hvr_effective": {"E": 80.0 / 120.0}}),
    "hvr_E_hi":   dict(overrides={"hvr_effective": {"E": 160.0 / 120.0}}),
    "hvr_cte_lo": dict(overrides={"hvr_effective": {"cte": 4.0 / 6.0}}),
    "hvr_cte_hi": dict(overrides={"hvr_effective": {"cte": 10.0 / 6.0}}),
    "tsv_off":    dict(tsv_enabled=False),
}

# lever -> (cases in sweep order, human label). Baseline is the FIRST case.
LEVERS = {
    "substrate thickness 200->500 um": (["C05", "C08"], True),
    "HVR footprint 72->96->120 mm2":   (["C11", "C05", "C12"], True),
    "HVR heat 31.5->42->52.5 W":       (["C19", "C07", "C20"], True),
    "placement asymmetry (reference)": (["C05", "C07"], False),
}

MET = {"die_warpage_pv_um": lambda r: r["structural"]["die_warpage_pv_um"],
       "pkg_warpage_pv_um": lambda r: r["structural"]["pkg_warpage_pv_um"],
       "T_max_C": lambda r: r["thermal"]["T_max_C"],
       "si_principal_p99_MPa": lambda r: r["structural"]["si_principal_MPa"]["p99"]}


def main():
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((P0B / "cooling_calibration.json").read_text())["h_top_W_m2K"]
    cases = sorted({c for v, _ in LEVERS.values() for c in v})
    print(f"cases: {cases}\ncorners: {list(PERTURB)}\n")

    rows = []
    for tag, kw in PERTURB.items():
        for cid in cases:
            r = run_case(cid, stack, doe, OUT / "robustness" / f"{tag}_{cid}", h_top=h_top,
                         bc="BC_A", threads=32, solver="", **SENS, **kw)
            d = {"corner": tag, "case": cid, "n_elems": r["mesh"]["n_elems"]}
            d.update({k: f(r) for k, f in MET.items()})
            rows.append(d)
        print(f"  corner {tag:12s} done  " +
              "  ".join(f"{c}={next(x['die_warpage_pv_um'] for x in rows if x['corner']==tag and x['case']==c):7.4f}"
                        for c in cases), flush=True)

    p = OUT / "robustness_results.csv"
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    get = lambda t, c, m: next(x[m] for x in rows if x["corner"] == t and x["case"] == c)
    summary = {}
    print(f"\n{'='*118}\nLEVER ROBUSTNESS ACROSS MATERIAL CORNERS (die warpage)\n{'='*118}")
    print(f"{'lever':34s}{'S_ref %':>9s}{'S_min %':>9s}{'S_max %':>9s}{'worst corner':>14s}"
          f"{'order stable':>14s}{'monotonic':>11s}{'verdict':>13s}")
    print("-" * 118)
    for name, (cl, dvpd) in LEVERS.items():
        s_by, order_ref, order_ok, mono_ok = {}, None, True, True
        for t in PERTURB:
            v = [get(t, c, "die_warpage_pv_um") for c in cl]
            med = float(np.median(v))
            s_by[t] = (max(v) - min(v)) / abs(med)
            o = tuple(np.argsort(v))
            if t == "ref":
                order_ref = o
            elif o != order_ref:
                order_ok = False
            if len(v) == 3 and not (v[0] < v[1] < v[2] or v[0] > v[1] > v[2]):
                mono_ok = False
        s_min, s_max = min(s_by.values()), max(s_by.values())
        worst = min(s_by, key=lambda k: s_by[k])
        verdict = "ROBUST" if (s_min > 0.02 and order_ok) else (
            "ORDER FLIPS" if not order_ok else "NOT ROBUST")
        summary[name] = {"cases": cl, "dvpd_specific": dvpd,
                         "S_ref_pct": 100 * s_by["ref"], "S_min_pct": 100 * s_min,
                         "S_max_pct": 100 * s_max, "worst_corner": worst,
                         "order_stable": order_ok, "monotonic": mono_ok,
                         "verdict": verdict, "by_corner_pct": {k: 100 * v for k, v in s_by.items()}}
        print(f"{name:34s}{100*s_by['ref']:9.2f}{100*s_min:9.2f}{100*s_max:9.2f}"
              f"{worst:>14s}{str(order_ok):>14s}{str(mono_ok):>11s}{verdict:>13s}")

    (OUT / "robustness_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nwrote {p}")


if __name__ == "__main__":
    main()
