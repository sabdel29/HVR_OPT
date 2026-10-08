#!/usr/bin/env python3
"""Phase-0G Sec.7: explicit BGA + board assembly against the compact BC-B foundation.

For each substrate thickness the same converged temperature field is applied to:
  BC_A      free package (3-2-1)
  BC_B      compact clamped-plane foundation, k_z = 1000 (the Phase-0F assembly model)
  BC_BOARD  explicit homogenised BGA field + FR-4 board, restrained only by 3-2-1
across a board envelope from a compliant thin board to a metal-backed one.

The question is whether the Phase-0F thickness sign reversal is a property of a real mounted
assembly or of the compact model's in-plane clamping.
"""
from __future__ import annotations
import csv, json, math, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0g"))
sys.path.insert(0, str(R / "scripts" / "phase0f"))
import board as BRD
import kw1
from geometry import cell_stack
from etm.config import build_materials, load_doe, load_stack
from etm.mesh import build
from etm.placement import Tile
from etm import ccxio, metrics
from metrics0f import relative_interface_displacement

OUT = R / "results" / "phase0g"
P0F = R / "results" / "phase0f"
H_XY, THREADS = 0.70, 16


def run_case(h_sub, mode, case, stack, doe, h_top, wd):
    des, g, why = kw1.design_1kw(kw1.M_VR, kw1.J_TARGET, h_sub)
    if des is None:
        raise RuntimeError(why)
    cs = cell_stack(des, "nominal")
    side = math.sqrt(des.area_mm2)
    if mode == "BC_BOARD":
        st = BRD.stack_with_board(stack, cs.t_cell_mm, case)
        extra, sup = BRD.bottom_layers(case), False
    else:
        st = kw1._stack_with_tile(stack, cs.t_cell_mm)
        extra, sup = None, (mode == "BC_B")
    xy = kw1.tiles_for("uniform", side, st, doe, kw1.M_VR)
    t_vr = [25.0] * len(xy)
    prev = None
    for it in range(20):
        per = [des.loss_at(t)["p_conv_w"] for t in t_vr]
        tiles = [Tile(cx, cy, side, side, per[k]) for k, (cx, cy) in enumerate(xy)]
        mats = build_materials(st)
        m = build(tiles, st, h_sub, h_xy=H_XY, z_scale=1.4, support_layer=sup,
                  extra_bottom_layers=extra)
        if len(m.elems) > 40000:
            raise RuntimeError(f"{len(m.elems)} elements over the ceiling")
        wd.mkdir(parents=True, exist_ok=True)
        ti = wd / "th.inp"
        films = ccxio.write_thermal(m, mats, tiles, st, kw1.P_LOAD_W, h_top, ti)
        ccxio.run_ccx(ti, threads=THREADS)
        Tn = ccxio.read_frd(wd / "th.frd")["NDTEMP"]
        tm = metrics.thermal_metrics(m, Tn, films, st, kw1.P_LOAD_W + sum(per), h_top)
        Tnode = Tn[1:m.n_nodes + 1, 0]
        t_new = kw1.tile_temperatures(m, Tnode, len(tiles))
        if prev is not None and abs(tm["T_max_C"] - prev) < 0.002:
            break
        prev, t_vr = tm["T_max_C"], t_new
    si = wd / "st.inp"
    ccxio.write_structural(m, mats, Tnode, st, mode, si, solver="")
    ccxio.run_ccx(si, threads=THREADS)
    s = ccxio.read_frd(wd / "st.frd")
    sm = metrics.structural_metrics(m, s["DISP"], s["STRESS"], st)
    rd = relative_interface_displacement(m, s["DISP"])
    out = {"h_sub_mm": h_sub, "restraint": mode, "board_case": case,
           "T_max_C": tm["T_max_C"], "n_elem": len(m.elems),
           "die_warpage_pv_um": sm["die_warpage_pv_um"],
           "pkg_warpage_pv_um": sm["pkg_warpage_pv_um"],
           "curvature_um_per_mm2": kw1.curvature(m, s["DISP"]),
           "interface_shear_p99_MPa": sm.get("interface_shear_MPa", {}).get("p99", float("nan")),
           "rel_disp_max_um": rd.get("rel_disp_max_um", float("nan")),
           "energy_residual_pct": tm["energy_residual_pct"]}
    for pat in ("*.frd", "*.inp", "*.dat", "*.sta", "*.cvg", "*.12d"):
        for f in wd.glob(pat):
            f.unlink(missing_ok=True)
    return out


def main():
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((P0F / "cooling_1kw_calibration.json").read_text())["h_top_W_m2K"]
    wd = OUT / "runs_board"
    rows = []
    cases = [("BC_A", "-"), ("BC_B", "-")]
    cases += [("BC_BOARD", c) for c in
              ("compliant", "fr4_1p6mm", "fr4_3p2mm", "stiff_metal_backed")]
    for h_sub in (0.80, 1.50, 2.00):
        for mode, case in cases:
            t0 = time.time()
            try:
                r = run_case(h_sub, mode, case, stack, doe, h_top, wd)
            except Exception as e:
                print(f"  h={h_sub} {mode:9s} {case:20s} FAILED: {str(e)[:70]}", flush=True)
                continue
            rows.append(r)
            print(f"  h={h_sub:.2f} {mode:9s} {case:20s} w={r['die_warpage_pv_um']:9.5f} um  "
                  f"kappa={r['curvature_um_per_mm2']:+.3e}  "
                  f"shear99={r['interface_shear_p99_MPa']:7.3f}  ({time.time()-t0:.0f}s)",
                  flush=True)
    with open(OUT / "explicit_board_crosscheck.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for r in rows for k in r}))
        w.writeheader(); w.writerows(rows)

    print("\n=== S_h = [W(thick) - W(thin)] / W(thin), by assembly model ===")
    for thin, thick in ((0.80, 1.50), (0.80, 2.00)):
        print(f"\n  {thin} -> {thick} mm")
        for mode, case in cases:
            a = next((r for r in rows if r["h_sub_mm"] == thin and r["restraint"] == mode
                      and r["board_case"] == case), None)
            b = next((r for r in rows if r["h_sub_mm"] == thick and r["restraint"] == mode
                      and r["board_case"] == case), None)
            if not (a and b):
                continue
            S = (b["die_warpage_pv_um"] - a["die_warpage_pv_um"]) / a["die_warpage_pv_um"]
            tag = "thicker BETTER" if S < 0 else "thicker WORSE"
            print(f"    {mode:9s} {case:20s} W {a['die_warpage_pv_um']:8.4f} -> "
                  f"{b['die_warpage_pv_um']:8.4f}   S_h = {S:+8.4f}   {tag}")
    print(f"\nwrote {OUT/'explicit_board_crosscheck.csv'}")


if __name__ == "__main__":
    main()
