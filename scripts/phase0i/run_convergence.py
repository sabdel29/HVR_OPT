#!/usr/bin/env python3
"""Phase-0I Sec.11 -- mesh and tolerance convergence of the predeclared damage metric.

The metric is a VOLUME AVERAGE with a corner exclusion band, precisely because Phase 0C
watched interface peel diverge at a bimaterial corner and Phase 0H watched a p99 shear go
non-monotone for the same reason. This script demonstrates that the averaged quantity does
what those did not.

Three axes:
  * in-plane / through-thickness refinement of the joint
  * the creep integration tolerance CETOL
  * the width of the corner exclusion band (regularisation stability)
"""
from __future__ import annotations
import csv, sys, time
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0i"))
from joint import build_joint, write_inp, run, read_dat, cycle_metric, BALL_H_UM  # noqa
from solder_model import inp_material                                             # noqa

WD = R / "results" / "phase0i" / "conv"
WD.mkdir(parents=True, exist_ok=True)
MAT = inp_material("SAC305", [-40., 0., 25., 50., 75., 100., 125.])
N_CYC = 4
T_HOT, T_COLD, DWELL = 100.0, 0.0, 300.0
GAMMA = 0.004                       # nominal shear across the standoff


def one(tag, n_xy, n_z, cetol, excl_frac=1.0):
    m = build_joint(n_xy, n_z, 1)
    if excl_frac != 1.0:                       # widen/narrow the exclusion band
        hs = 0.5 * 0.35449
        dx = m.sets["_dx_mm"] * excl_frac
        core = []
        for e, c, s in m.elems:
            if s != "ESOL":
                continue
            ctr = m.nodes[[n - 1 for n in c]].mean(axis=0)
            if max(abs(ctr[0]), abs(ctr[1])) < hs - dx * 0.999:
                core.append(e)
        m.sets["ESOLCORE"] = core
    du = GAMMA * BALL_H_UM / 1e3
    cyc, ends, t = [], [], 0.0
    for k in range(N_CYC):
        cyc.append((f"c{k}h", T_HOT, du, DWELL)); t += DWELL
        cyc.append((f"c{k}c", T_COLD, -du, DWELL)); t += DWELL
        ends.append(t)
    p = WD / f"{tag}.inp"
    write_inp(m, p, MAT, cyc, cetol=cetol)
    t0 = time.time()
    run(p, threads=4)
    d = WD / f"{tag}.dat"
    if not (d.is_file() and d.stat().st_size > 1000):
        return None
    inc, vals = cycle_metric(read_dat(d), [0.0] + ends)
    # a run that stalls part-way returns short or zero increments; treat that as a failure
    # rather than dividing by it
    if not inc or not np.isfinite(inc[-1]) or inc[-1] <= 0:
        return {"tag": tag, "n_xy": n_xy, "n_z": n_z, "cetol": cetol, "excl_frac": excl_frac,
                "n_elem": len(m.elems), "n_core": len(m.sets["ESOLCORE"]),
                "d_eps_in_stab": float("nan"), "prev_cycle": float("nan"),
                "stab_change_pct": float("nan"), "incomplete": True,
                "wall_s": round(time.time() - t0, 1)}
    prev_c = inc[-2] if len(inc) > 1 and inc[-2] > 0 else float("nan")
    return {"tag": tag, "n_xy": n_xy, "n_z": n_z, "cetol": cetol, "excl_frac": excl_frac,
            "n_elem": len(m.elems), "n_core": len(m.sets["ESOLCORE"]),
            "d_eps_in_stab": inc[-1],
            "prev_cycle": prev_c,
            "stab_change_pct": (100 * abs(inc[-1] - prev_c) / prev_c)
                               if np.isfinite(prev_c) else float("nan"),
            "wall_s": round(time.time() - t0, 1)}


def main():
    rows = []
    print("A. MESH REFINEMENT (CETOL = 1e-2, exclusion band = 1 element)")
    print(f"{'n_xy':>5s} {'n_z':>4s} {'elems':>7s} {'core':>6s} {'d_eps_in':>12s} "
          f"{'vs prev mesh':>13s} {'s':>6s}")
    prev = None
    for n_xy, n_z in ((4, 5), (5, 6), (6, 8), (8, 10)):
        r = one(f"m{n_xy}_{n_z}", n_xy, n_z, 1e-2)
        if not r or r.get("incomplete"):
            print(f"{n_xy:5d} {n_z:4d}  INCOMPLETE (solver stalled)"); continue
        if not r:
            print(f"{n_xy:5d} {n_z:4d}  FAILED"); continue
        d = f"{100*abs(r['d_eps_in_stab']-prev)/prev:12.2f} %" if prev else " " * 13
        print(f"{n_xy:5d} {n_z:4d} {r['n_elem']:7d} {r['n_core']:6d} "
              f"{r['d_eps_in_stab']:12.5e} {d} {r['wall_s']:6.0f}", flush=True)
        r["vs_prev_mesh_pct"] = (100 * abs(r["d_eps_in_stab"] - prev) / prev) if prev else None
        rows.append(r); prev = r["d_eps_in_stab"]

    print("\nB. CREEP TOLERANCE (mesh 6x8)")
    prevc = None
    for cet in (5e-2, 1e-2, 5e-3):
        r = one(f"c{cet:g}", 6, 8, cet)
        if not r or r.get("incomplete"):
            print(f"  CETOL={cet:g}  INCOMPLETE"); continue
        if not r:
            print(f"  CETOL={cet:g}  FAILED"); continue
        d = f"{100*abs(r['d_eps_in_stab']-prevc)/prevc:.2f} %" if prevc else ""
        print(f"  CETOL={cet:<8g} d_eps_in={r['d_eps_in_stab']:.5e}  {d}", flush=True)
        r["vs_prev_cetol_pct"] = (100 * abs(r["d_eps_in_stab"] - prevc) / prevc) if prevc else None
        rows.append(r); prevc = r["d_eps_in_stab"]

    print("\nC. CORNER EXCLUSION BAND (mesh 6x8, CETOL = 1e-2)")
    for f in (0.0, 1.0, 2.0):
        r = one(f"x{f:g}", 6, 8, 1e-2, excl_frac=f)
        if not r or r.get("incomplete"):
            print(f"  band={f:g}  INCOMPLETE"); continue
        if not r:
            print(f"  band={f:g} elem  FAILED"); continue
        print(f"  band={f:g} element(s): core={r['n_core']:3d} elems, "
              f"d_eps_in={r['d_eps_in_stab']:.5e}", flush=True)
        rows.append(r)

    with open(R / "results/phase0i/local_metric_convergence.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=sorted({k for r in rows for k in r}))
        w.writeheader(); w.writerows(rows)
    print(f"\nwrote results/phase0i/local_metric_convergence.csv ({len(rows)} rows)")


if __name__ == "__main__":
    main()
