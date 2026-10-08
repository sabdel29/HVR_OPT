#!/usr/bin/env python3
"""Phase-0H Sec.10 -- validate the candidate LOCAL metrics in the MOUNTED configuration.

Sec.8 shortlists two computable local quantities, both tied to failure mechanism C
(microbump / C4 shear):

    rel_disp_max_um          the relative in-plane displacement imposed across the die-attach
                             joint layer -- the kinematic driver of joint shear
    interface_shear_p99_MPa  the p99 smeared shear stress in that layer

Both were previously characterised only in the FREE or CLAMPED models. Phase 0G withdrew BC-B,
so any metric that is going to carry decision weight must be revalidated where the conclusion
lives: on the explicit BGA + board assembly.

Three tests, and the project has been burned by all three before:
  * MESH CONVERGENCE  -- interface PEEL failed this (19-20 %/step) and was excluded.
  * SINGULARITY       -- the underfill free edge is a bimaterial corner. A p99 over the whole
                         layer samples it. Exclusion-radius variants say whether the metric is
                         reporting the corner or the bonded interior.
  * MATERIAL CORNERS  -- interface shear was previously found material-sensitive.
"""
from __future__ import annotations
import csv, json, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for p in ("phase0h", "phase0g", "phase0f", "phase0b"):
    sys.path.insert(0, str(R / "scripts" / p))

import board as BRD                                   # noqa: E402
import kw1                                            # noqa: E402
import run_explicit_board as REB                      # noqa: E402
REB.THREADS = 8      # the machine is shared and already at load ~150
from etm.config import load_doe, load_stack           # noqa: E402

OUT = R / "results" / "phase0h"
CASE = "fr4_1p6mm"
H_SUB = 1.50


def one(h_xy, stack, doe, h_top, wd, tag, extra=None):
    old = REB.H_XY
    REB.H_XY = h_xy
    try:
        r = REB.run_case(H_SUB, "BC_BOARD", CASE, stack, doe, h_top, wd)
    finally:
        REB.H_XY = old
    r["study"] = tag
    r["h_xy_mm"] = h_xy
    r.update(extra or {})
    return r


def main():
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((R / "results/phase0f/cooling_1kw_calibration.json").read_text())["h_top_W_m2K"]
    wd, rows = OUT / "runs_localval", []

    print("Sec.10a  MESH CONVERGENCE of the local metrics, mounted (BC_BOARD, FR-4 1.6 mm)")
    print(f"{'h_xy':>6s} {'n_elem':>8s} {'die w um':>10s} {'tau99 MPa':>11s} {'rel disp um':>12s} {'s':>5s}")
    for h_xy in (0.95, 0.80, 0.70, 0.60):
        t0 = time.time()
        try:
            r = one(h_xy, stack, doe, h_top, wd, "mesh")
        except Exception as e:
            print(f"{h_xy:6.2f}  FAILED: {str(e)[:70]}", flush=True); continue
        rows.append(r)
        print(f"{h_xy:6.2f} {r['n_elem']:8d} {r['die_warpage_pv_um']:10.4f} "
              f"{r['interface_shear_p99_MPa']:11.4f} {r['rel_disp_max_um']:12.5f} "
              f"{time.time()-t0:5.0f}", flush=True)

    print("\nSec.10b  MATERIAL CORNERS at the finest affordable mesh")
    base = json.dumps(stack)
    corners = {
        "ref": {},
        "uf_E_lo": ("underfill_homog", "E", 0.75), "uf_E_hi": ("underfill_homog", "E", 1.25),
        "uf_cte_lo": ("underfill_homog", "cte", 0.80), "uf_cte_hi": ("underfill_homog", "cte", 1.20),
        "hvr_E_lo": ("hvr_effective", "E", 0.75), "hvr_E_hi": ("hvr_effective", "E", 1.25),
    }
    for name, spec in corners.items():
        st = json.loads(base)
        if spec:
            mat, key, k = spec
            m = st["materials"][mat]
            for cand in (key, key + "_pa", "youngs_modulus", "cte_per_k", "alpha"):
                if cand in m and isinstance(m[cand], dict) and "value" in m[cand]:
                    m[cand]["value"] *= k
                    break
            else:
                print(f"  {name:10s} SKIPPED -- no key {key} in {mat}: {sorted(m)}")
                continue
        t0 = time.time()
        try:
            r = one(0.70, st, doe, h_top, wd, "corner", {"corner": name})
        except Exception as e:
            print(f"  {name:10s} FAILED: {str(e)[:60]}", flush=True); continue
        rows.append(r)
        print(f"  {name:10s} tau99={r['interface_shear_p99_MPa']:8.4f} "
              f"rel_disp={r['rel_disp_max_um']:9.5f} w={r['die_warpage_pv_um']:9.4f} "
              f"({time.time()-t0:.0f}s)", flush=True)

    with open(OUT / "local_metric_convergence.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for r in rows for k in r}))
        w.writeheader(); w.writerows(rows)

    mesh = [r for r in rows if r["study"] == "mesh"]
    print("\n=== convergence: change over the FINAL refinement step, target < 10 % ===")
    if len(mesh) >= 2:
        a, b = mesh[-2], mesh[-1]
        for k in ("die_warpage_pv_um", "interface_shear_p99_MPa", "rel_disp_max_um"):
            d = 100 * (b[k] - a[k]) / a[k]
            print(f"  {k:26s} {a[k]:10.5f} -> {b[k]:10.5f}  {d:+7.2f} %  "
                  f"{'CONVERGED' if abs(d) < 10 else 'NOT CONVERGED'}")
    cor = [r for r in rows if r["study"] == "corner"]
    if cor:
        print("\n=== material-corner spread ===")
        for k in ("interface_shear_p99_MPa", "rel_disp_max_um", "die_warpage_pv_um"):
            v = [r[k] for r in cor]
            ref = next((r[k] for r in cor if r.get("corner") == "ref"), v[0])
            print(f"  {k:26s} {min(v):9.5f} - {max(v):9.5f}   "
                  f"spread {100*(max(v)-min(v))/ref:6.2f} % of ref")
    print(f"\nwrote {OUT/'local_metric_convergence.csv'}")


if __name__ == "__main__":
    main()
