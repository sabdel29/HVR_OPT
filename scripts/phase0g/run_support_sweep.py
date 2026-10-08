#!/usr/bin/env python3
"""Phase-0G Sec.5/6: where does the thickness sign reversal actually live?

Phase 0F's reversal rests on ONE provisional foundation stiffness, k_z = 1000 N/mm^3. A
physically interpretable board model puts that near the RIGID end of the plausible range:

    k_BGA  = E_solder * (pi d^2/4)/p^2 / h = 13 090 N/mm^3   (source-backed geometry)
    k_PCB  = D / span^4                    = 1e-4 .. 7 N/mm^3 for real FR-4 plates
    k_eff  = series(k_BGA, k_PCB)

so a free-standing board is nearer 1e-2 than 1e3. This script sweeps the foundation over the
whole plausible range and locates k* where

    S_h(k) = [W(h_thick) - W(h_thin)] / W(h_thin)

changes sign. The thermal problem does not depend on the foundation modulus, so the ET fixed
point is solved once per thickness and reused for every stiffness -- exact, and ~10x cheaper.
"""
from __future__ import annotations
import csv, json, math, sys, time
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0g"))
sys.path.insert(0, str(R / "scripts" / "phase0f"))
import kw1
from geometry import cell_stack
from etm.config import build_materials, load_doe, load_stack
from etm.mesh import build
from etm.placement import Tile
from etm import ccxio, metrics

OUT = R / "results" / "phase0g"
P0F = R / "results" / "phase0f"
T_SUP_MM = 0.400                    # support-layer thickness (Phase-0B BC_B card)
H_XY = 0.70
THREADS = 16

# Physically plausible foundation range, from the series model above.
K_LIST = [1e-3, 1e-2, 1e-1, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0, 3000.0, 13090.0]
K_LABEL = {1e-3: "free-floating board (thin FR-4, wide span)",
           1e-2: "free-floating board", 1e-1: "thick FR-4, wide span",
           1.0: "weakly supported", 3.0: "weakly supported",
           10.0: "moderately supported", 30.0: "moderately supported",
           100.0: "stiffened board", 300.0: "stiffened board",
           1000.0: "Phase-0F PROVISIONAL", 3000.0: "near-rigid backing",
           13090.0: "rigid backing (k_BGA limit)"}


def thermal_once(h_sub, h_top, stack, doe, wd):
    """ET fixed point with the support layer present; returns the converged T field + mesh."""
    des, g, why = kw1.design_1kw(kw1.M_VR, kw1.J_TARGET, h_sub)
    if des is None:
        raise RuntimeError(why)
    cs = cell_stack(des, "nominal")
    st = kw1._stack_with_tile(stack, cs.t_cell_mm)
    side = math.sqrt(des.area_mm2)
    xy = kw1.tiles_for("uniform", side, st, doe, kw1.M_VR)
    t_vr = [25.0] * len(xy)
    prev = None
    for it in range(20):
        per = [des.loss_at(t)["p_conv_w"] for t in t_vr]
        p_conv = float(sum(per))
        tiles = [Tile(cx, cy, side, side, per[k]) for k, (cx, cy) in enumerate(xy)]
        mats = build_materials(st)
        m = build(tiles, st, h_sub, h_xy=H_XY, z_scale=1.4, support_layer=True)
        if len(m.elems) > 40000:
            raise RuntimeError(f"{len(m.elems)} elements over the ceiling")
        wd.mkdir(parents=True, exist_ok=True)
        ti = wd / "th.inp"
        films = ccxio.write_thermal(m, mats, tiles, st, kw1.P_LOAD_W, h_top, ti)
        ccxio.run_ccx(ti, threads=THREADS)
        Tn = ccxio.read_frd(wd / "th.frd")["NDTEMP"]
        tm = metrics.thermal_metrics(m, Tn, films, st, kw1.P_LOAD_W + p_conv, h_top)
        Tnode = Tn[1:m.n_nodes + 1, 0]
        t_new = kw1.tile_temperatures(m, Tnode, len(tiles))
        if prev is not None and abs(tm["T_max_C"] - prev) < 0.002:
            break
        prev, t_vr = tm["T_max_C"], t_new
    return st, m, mats, Tnode, tiles, tm, cs


def structural(st, m, Tnode, k_z, wd, bc="BC_B"):
    """Re-solve structure only, with the foundation modulus set from k_z = E / t."""
    s2 = json.loads(json.dumps(st))
    if bc == "BC_B":
        s2["structural_bc"]["variants"]["BC_B"]["E"]["value"] = k_z * T_SUP_MM
    mats = build_materials(s2)
    si = wd / "st.inp"
    ccxio.write_structural(m, mats, Tnode, s2, bc, si, solver="")
    ccxio.run_ccx(si, threads=THREADS)
    s = ccxio.read_frd(wd / "st.frd")
    sm = metrics.structural_metrics(m, s["DISP"], s["STRESS"], s2)
    return {"die_warpage_pv_um": sm["die_warpage_pv_um"],
            "pkg_warpage_pv_um": sm["pkg_warpage_pv_um"],
            "curvature_um_per_mm2": kw1.curvature(m, s["DISP"]),
            "interface_shear_p99_MPa": sm.get("interface_shear_MPa", {}).get("p99", float("nan"))}


def main():
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((P0F / "cooling_1kw_calibration.json").read_text())["h_top_W_m2K"]
    wd = OUT / "runs_support"
    rows = []
    cache = {}
    for h_sub in (0.80, 1.00, 1.50, 2.00):
        t0 = time.time()
        st, m, mats, Tnode, tiles, tm, cs = thermal_once(h_sub, h_top, stack, doe, wd)
        cache[h_sub] = True
        print(f"  h={h_sub:.2f}  thermal converged T_max={tm['T_max_C']:.4f} C "
              f"({len(m.elems)} el, {time.time()-t0:.0f}s)", flush=True)
        for k in K_LIST:
            r = structural(st, m, Tnode, k, wd)
            rows.append({"h_sub_mm": h_sub, "k_z_N_per_mm3": k, "regime": K_LABEL[k],
                         "E_support_MPa": k * T_SUP_MM, "T_max_C": tm["T_max_C"], **r})
            print(f"      k_z={k:>9.4g}  w={r['die_warpage_pv_um']:9.5f} um  "
                  f"kappa={r['curvature_um_per_mm2']:+.4e}  "
                  f"shear99={r['interface_shear_p99_MPa']:7.3f}", flush=True)
        for pat in ("*.frd", "*.inp", "*.dat", "*.sta", "*.cvg", "*.12d"):
            for f in wd.glob(pat):
                f.unlink(missing_ok=True)

    with open(OUT / "support_stiffness_sweep.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    print("\n=== S_h(k) = [W(thick) - W(thin)] / W(thin) ===")
    for thin, thick in ((0.80, 1.50), (0.80, 2.00), (1.00, 2.00)):
        print(f"\n  pair {thin} -> {thick} mm")
        print(f"  {'k_z':>10s} {'regime':34s} {'W_thin':>9s} {'W_thick':>9s} {'S_h':>9s}")
        prev = None
        for k in K_LIST:
            a = next((r for r in rows if r["h_sub_mm"] == thin and r["k_z_N_per_mm3"] == k), None)
            b = next((r for r in rows if r["h_sub_mm"] == thick and r["k_z_N_per_mm3"] == k), None)
            if not (a and b):
                continue
            S = (b["die_warpage_pv_um"] - a["die_warpage_pv_um"]) / a["die_warpage_pv_um"]
            print(f"  {k:10.4g} {K_LABEL[k][:34]:34s} {a['die_warpage_pv_um']:9.5f} "
                  f"{b['die_warpage_pv_um']:9.5f} {S:+9.4f}")
            if prev and prev[1] * S < 0:
                kstar = math.exp(math.log(prev[0]) + (math.log(k) - math.log(prev[0]))
                                 * (0 - prev[1]) / (S - prev[1]))
                print(f"    --> SIGN CHANGE between {prev[0]:.4g} and {k:.4g}: "
                      f"k* = {kstar:.4g} N/mm^3")
            prev = (k, S)
    print(f"\nwrote {OUT/'support_stiffness_sweep.csv'}")


if __name__ == "__main__":
    main()
