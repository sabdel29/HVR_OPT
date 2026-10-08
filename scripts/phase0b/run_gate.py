#!/usr/bin/env python3
"""Phase-0B first mechanical gate: C05 / C07, then C13.

Executes the three gate cases on ONE frozen configuration (same stack, heat total,
cooling calibration, material cards, mesh policy and output definitions), then the
BC and material sensitivity sweeps needed to turn a raw difference into a
*resolved* difference.

Materiality metric (spec):     S_m = (m_max - m_min) / m_median
Resolution rule (spec):        an architectural effect is resolved only if S_m > 2 u_m
Magnitude bands (spec):        weak 10-15%, moderate 15-25%, strong >=25%
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etm.config import load_doe, load_stack           # noqa: E402
from etm.run_case import run_case                     # noqa: E402

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0b"

PROD = dict(h_xy=0.32, z_scale=1.4)      # production = convergence level M4 (37.5k el, converged)
SENS = dict(h_xy=0.45, z_scale=1.0)      # sensitivity mesh = M2: relative spreads converge faster than absolutes

def _s(r, key, sub=None):
    """Tolerant metric getter: the tsv_off variant has no TSV region at all."""
    v = r["structural"].get(key)
    if v is None:
        return float("nan")
    return v[sub] if sub else v


METRICS = {
    "T_max_C":                lambda r: r["thermal"]["T_max_C"],
    "die_warpage_pv_um":      lambda r: _s(r, "die_warpage_pv_um"),
    "pkg_warpage_pv_um":      lambda r: _s(r, "pkg_warpage_pv_um"),
    "si_principal_p99_MPa":   lambda r: _s(r, "si_principal_MPa", "p99"),
    "tsv_vm_p99_MPa":         lambda r: _s(r, "tsv_region_vm_MPa", "p99"),
    "interface_shear_p99_MPa": lambda r: _s(r, "interface_shear_MPa", "p99"),
    "interface_peel_p99_MPa": lambda r: _s(r, "interface_peel_MPa", "p99"),
    "si_principal_raw_MPa":   lambda r: _s(r, "si_principal_MPa", "raw_max"),
    "energy_residual_pct":    lambda r: r["thermal"]["energy_residual_pct"],
}

# material / model perturbations forming the model-uncertainty budget
PERTURBATIONS = {
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


def _row(cid, tag, r):
    d = {"case": cid, "variant": tag, "bc": r["bc"]["bc"],
         "n_elems": r["mesh"]["n_elems"], "runtime_s": r["runtime_s"]}
    d.update({k: f(r) for k, f in METRICS.items()})
    return d


def main(cases: list[str]) -> None:
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((OUT / "cooling_calibration.json").read_text())["h_top_W_m2K"]
    rows: list[dict] = []

    def show(cid, tag, r):
        print(f"  {cid} {tag:14s} Tmax={r['thermal']['T_max_C']:7.3f}C  "
              f"die_w={r['structural']['die_warpage_pv_um']:8.3f}um  "
              f"pkg_w={r['structural']['pkg_warpage_pv_um']:8.3f}um  "
              f"si99={r['structural']['si_principal_MPa']['p99']:7.3f}MPa  "
              f"tau99={r['structural']['interface_shear_MPa']['p99']:6.3f}MPa  "
              f"Ebal={r['thermal']['energy_residual_pct']:+.3f}%  "
              f"({r['mesh']['n_elems']}el, {r['runtime_s']:.0f}s)", flush=True)

    # ---- headline: BC-A on the converged production mesh ---------------------
    for cid in cases:
        wd = OUT / cid / "baseline_BC_A"
        r = run_case(cid, stack, doe, wd, h_top=h_top, bc="BC_A", threads=32,
                     solver='', **PROD)
        rows.append(_row(cid, "baseline_BC_A", r))
        show(cid, "BC_A/prod", r)

    # ---- BC sensitivity: matched pair on the SENS mesh -----------------------
    # BC-B adds an explicit compliant support layer, so at the production mesh it
    # exceeds the C3D8I/SPOOLES element ceiling. Both BC families are therefore run
    # at the SENS level so the comparison is like-for-like rather than confounded
    # by a mesh change.
    for cid in cases:
        for bc in ("BC_A", "BC_B"):
            wd = OUT / cid / f"bcsens_{bc}"
            r = run_case(cid, stack, doe, wd, h_top=h_top, bc=bc, threads=32,
                         solver='', **SENS)
            rows.append(_row(cid, f"bcsens_{bc}", r))
            show(cid, f"{bc}/sens", r)

    # ---- material / model perturbations (BC-A, sensitivity mesh) -------------
    for cid in cases:
        # matched-mesh reference so spreads are computed like-for-like
        wd = OUT / cid / "sens_ref"
        ref = run_case(cid, stack, doe, wd, h_top=h_top, bc='BC_A', threads=32, solver='', **SENS)
        rows.append(_row(cid, "sens_ref", ref))
        for tag, kw in PERTURBATIONS.items():
            wd = OUT / cid / f"sens_{tag}"
            r = run_case(cid, stack, doe, wd, h_top=h_top, bc="BC_A", threads=32,
                         solver="", **SENS, **kw)
            rows.append(_row(cid, f"sens_{tag}", r))
            show(cid, tag, r)

    fields = list(rows[0].keys())
    p = OUT / "gate_runs.csv"
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {p}  ({len(rows)} runs)")


if __name__ == "__main__":
    main(sys.argv[1:] or ["C05", "C07"])
