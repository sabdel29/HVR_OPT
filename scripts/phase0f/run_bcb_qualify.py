#!/usr/bin/env python3
"""Phase-0F Sec.6: qualify a board-mounted mechanical metric BEFORE using it for design.

Two configurations that the free-package state separates strongly (thin vs thick substrate at
1 kW) are run under BC-B across:
  * three interface through-thickness refinements  -> convergence
  * five material corners                          -> robustness
For every candidate metric the question is the same: does the ORDERING of the two
configurations stay the same, and is the difference resolved (> 2 u_m = 1 %)?

A metric that fails either test may not be used for synthesis. Interface peel is excluded
throughout: it never converged and stays demoted.
"""
from __future__ import annotations
import csv, json, math, sys, time
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0f"))
import kw1
from metrics0f import relative_interface_displacement, shear_family
from placement0f import build as build0f
from etm.config import build_materials, load_doe, load_stack
from etm.mesh import build
from etm.placement import Tile
from etm import ccxio, metrics

OUT = R / "results" / "phase0f"
U_M_PCT = 0.5
CONFIGS = [("thin", 0.8), ("thick", 1.5)]
CORNERS = {
    "ref": {},
    "uf_E_lo": {"underfill_homog": {"E": 0.7}},
    "uf_E_hi": {"underfill_homog": {"E": 1.3}},
    "uf_cte_lo": {"underfill_homog": {"cte": 0.7}},
    "uf_cte_hi": {"underfill_homog": {"cte": 1.3}},
    "hvr_E_lo": {"hvr_effective": {"E": 0.7}},
    "hvr_E_hi": {"hvr_effective": {"E": 1.3}},
    "hvr_cte_lo": {"hvr_effective": {"cte": 0.7}},
    "hvr_cte_hi": {"hvr_effective": {"cte": 1.3}},
}


def one(h_sub, h_top, stack, doe, wd, inz=None, overrides=None, h_xy=0.70):
    des, g, why = kw1.design_1kw(kw1.M_VR, kw1.J_TARGET, h_sub)
    if des is None:
        raise RuntimeError(why)
    st = kw1._stack_with_tile(stack, g.t_cell_um * 1e-3)
    side = math.sqrt(des.area_mm2)
    xy = kw1.tiles_for("uniform", side, st, doe, kw1.M_VR)
    p_conv = kw1.M_VR * des.loss_at(84.0)["p_conv_w"]
    tiles = [Tile(cx, cy, side, side, p_conv / len(xy)) for cx, cy in xy]
    mats = build_materials(st, overrides or {})
    m = build(tiles, st, h_sub, h_xy=h_xy, z_scale=1.4, support_layer=True,
              interface_nz=inz)
    if len(m.elems) > 40000:
        raise RuntimeError(f"{len(m.elems)} elements over the 40 000 C3D8I ceiling")
    wd.mkdir(parents=True, exist_ok=True)
    ti = wd / "th.inp"
    films = ccxio.write_thermal(m, mats, tiles, st, kw1.P_LOAD_W, h_top, ti)
    ccxio.run_ccx(ti, threads=16)
    T = ccxio.read_frd(wd / "th.frd")["NDTEMP"]
    tm = metrics.thermal_metrics(m, T, films, st, kw1.P_LOAD_W + p_conv, h_top)
    si = wd / "st.inp"
    ccxio.write_structural(m, mats, T[1:m.n_nodes + 1, 0], st, "BC_B", si, solver="")
    ccxio.run_ccx(si, threads=16)
    s = ccxio.read_frd(wd / "st.frd")
    sm = metrics.structural_metrics(m, s["DISP"], s["STRESS"], st)
    rd = relative_interface_displacement(m, s["DISP"])
    out = {"h_sub_mm": h_sub, "interface_nz": inz or 1, "n_elem": len(m.elems),
           "T_max_C": tm["T_max_C"], "die_warpage_pv_um": sm["die_warpage_pv_um"],
           "curvature_um_per_mm2": kw1.curvature(m, s["DISP"]),
           "energy_residual_pct": tm["energy_residual_pct"]}
    out.update(shear_family(sm)); out.update(rd)
    for pat in ("*.frd", "*.inp", "*.dat", "*.sta", "*.cvg", "*.12d"):
        for f in wd.glob(pat):
            f.unlink(missing_ok=True)
    return out


METRICS = ["die_warpage_pv_um", "curvature_um_per_mm2", "shear_p99_MPa", "shear_p95_MPa",
           "shear_raw_max_MPa", "shear_excl050_p99_MPa", "rel_disp_p99_um",
           "rel_disp_max_um", "rel_disp_p95_um"]


def main():
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((OUT / "cooling_1kw_calibration.json").read_text())["h_top_W_m2K"]
    wd = OUT / "runs_bcbq"
    rows = []
    for tag, h in CONFIGS:
        for inz in (1, 2, 4):
            t0 = time.time()
            r = one(h, h_top, stack, doe, wd, inz=inz)
            r.update({"config": tag, "corner": "ref", "study": "convergence"})
            rows.append(r)
            print(f"  conv  {tag:5s} inz={inz}  shear99={r.get('shear_p99_MPa',float('nan')):7.3f} "
                  f"reldisp99={r.get('rel_disp_p99_um',float('nan')):7.4f} "
                  f"kappa={r['curvature_um_per_mm2']:+.3e} ({time.time()-t0:.0f}s)", flush=True)
        for cname, ov in CORNERS.items():
            if cname == "ref":
                continue
            t0 = time.time()
            r = one(h, h_top, stack, doe, wd, inz=2, overrides=ov)
            r.update({"config": tag, "corner": cname, "study": "robustness"})
            rows.append(r)
            print(f"  corn  {tag:5s} {cname:11s} shear99={r.get('shear_p99_MPa',float('nan')):7.3f} "
                  f"reldisp99={r.get('rel_disp_p99_um',float('nan')):7.4f} "
                  f"({time.time()-t0:.0f}s)", flush=True)

    keys = sorted({k for r in rows for k in r})
    with open(OUT / "bcb_metric_qualification.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)

    print("\n=== QUALIFICATION: does each metric converge AND keep its ordering? ===")
    verdicts = []
    for mt in METRICS:
        conv = []
        for tag, _ in CONFIGS:
            v = [next((r[mt] for r in rows if r["config"] == tag and r["study"] == "convergence"
                       and r["interface_nz"] == i), float("nan")) for i in (1, 2, 4)]
            conv.append(v)
        c_ok, c_txt = True, []
        for tag, v in zip([c[0] for c in CONFIGS], conv):
            if any(not np.isfinite(x) for x in v) or abs(v[-1]) < 1e-12:
                c_ok = False; c_txt.append(f"{tag}:n/a"); continue
            d = 100 * abs(v[2] - v[1]) / abs(v[2])
            c_txt.append(f"{tag}:{d:.1f}%")
            c_ok &= d <= 10.0
        ords, res = [], []
        for cname in CORNERS:
            a = next((r[mt] for r in rows if r["config"] == "thin"
                      and r["corner"] == cname and (r["study"] == "robustness" or cname == "ref")
                      and r["interface_nz"] == 2), None)
            b = next((r[mt] for r in rows if r["config"] == "thick"
                      and r["corner"] == cname and (r["study"] == "robustness" or cname == "ref")
                      and r["interface_nz"] == 2), None)
            if a is None or b is None or not (np.isfinite(a) and np.isfinite(b)) or abs(a) < 1e-12:
                continue
            ords.append(np.sign(b - a)); res.append(abs(100 * (b - a) / abs(a)))
        o_ok = len(set(ords)) == 1 and len(ords) >= 5
        r_ok = all(x > 2 * U_M_PCT for x in res) if res else False
        ok = c_ok and o_ok and r_ok
        verdicts.append({"metric": mt, "converged": c_ok, "convergence": "; ".join(c_txt),
                         "ordering_stable": o_ok, "n_corners": len(ords),
                         "min_separation_pct": min(res) if res else float("nan"),
                         "resolved_everywhere": r_ok, "QUALIFIED": ok})
        print(f"  {mt:26s} conv[{'; '.join(c_txt):22s}] ord={'stable' if o_ok else 'UNSTABLE':8s} "
              f"min_sep={min(res) if res else float('nan'):7.2f}%  "
              f"{'QUALIFIED' if ok else 'REJECTED'}")
    with open(OUT / "bcb_metric_verdicts.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(verdicts[0])); w.writeheader(); w.writerows(verdicts)
    q = [v["metric"] for v in verdicts if v["QUALIFIED"]]
    print(f"\nQUALIFIED mounted metrics: {q if q else 'NONE'}")


if __name__ == "__main__":
    main()
