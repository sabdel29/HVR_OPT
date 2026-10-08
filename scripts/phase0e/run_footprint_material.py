#!/usr/bin/env python3
"""Phase-0E Sec.12: does the footprint electrical<->mechanical opposition survive a
physically plausible HVR material distribution?

Two mechanical variants of the SAME geometry, same placement, same converter power, same
thermal boundary conditions. The ONLY difference is the HVR tile material:

  homogeneous : the Phase-0B/0C/0D `hvr_effective` card (E 120 GPa, CTE 6 ppm/K, k 60),
                filling the entire electrical bounding box -- what every previous phase used.
  composite   : effective properties derived from the compiler's OWN component inventory
                (per-layer group areas -> fill fractions -> rule of mixtures).

Converter power is FROZEN at the Phase-0D-R operating temperature for both variants so the
comparison isolates the material model rather than re-converging the ET loop differently.
"""
from __future__ import annotations
import csv, json, math, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for p in ("phase0b", "phase0d", "phase0e"):
    sys.path.insert(0, str(R / "scripts" / p))

from etm.config import build_materials, load_doe, load_stack
from etm.mesh import build
from etm.placement import Tile, generate
from etm import ccxio, metrics
from electrical import compile_hvr
from hvr_material import compose, homogeneous_reference

OUT = R / "results" / "phase0e"
P0B = R / "results" / "phase0b"
T_FREEZE = 85.0
H_SUB = 0.5
P_DIE = 240.0
THREADS = 12


def tiles_for(side, stack, doe, n_vr=4):
    g, rules = stack["geometry"], doe["placement_rules"]
    return [(t.cx, t.cy) for t in generate(
        "distributed_2x2", n_vr, side, side,
        die_x=g["functional_die"]["size_x"]["value"],
        die_y=g["functional_die"]["size_y"]["value"],
        keepout=rules["edge_keepout_mm"]["value"],
        min_gap=rules["min_gap_mm"]["value"], p_total=1.0)]


def run_case(tiles, stack, overrides, h_top, p_extra, wd):
    wd.mkdir(parents=True, exist_ok=True)
    mats = build_materials(stack, overrides)
    m = build(tiles, stack, H_SUB, h_xy=0.32, z_scale=1.4)
    ti = wd / "th.inp"
    films = ccxio.write_thermal(m, mats, tiles, stack, p_extra, h_top, ti)
    ccxio.run_ccx(ti, threads=THREADS)
    T = ccxio.read_frd(wd / "th.frd")["NDTEMP"]
    tm = metrics.thermal_metrics(m, T, films, stack,
                                 p_extra + sum(t.power_w for t in tiles), h_top)
    si = wd / "st.inp"
    ccxio.write_structural(m, mats, T[1:m.n_nodes + 1, 0], stack, "BC_A", si, solver="")
    ccxio.run_ccx(si, threads=THREADS)
    s = ccxio.read_frd(wd / "st.frd")
    sm = metrics.structural_metrics(m, s["DISP"], s["STRESS"], stack)
    for pat in ("*.frd", "*.inp", "*.dat", "*.sta", "*.cvg", "*.12d"):
        for f in wd.glob(pat):
            f.unlink(missing_ok=True)
    return tm, sm


def main():
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((P0B / "cooling_calibration.json").read_text())["h_top_W_m2K"]
    ref = homogeneous_reference()
    rows = []
    for j in (1.5, 2.0, 4.0):
        des = compile_hvr(60.0, j)
        comp = compose(des, j)
        side = math.sqrt(des.area_mm2)
        xy = tiles_for(side, stack, doe)
        p_conv = 4 * des.loss_at(T_FREEZE)["p_conv_w"]
        tiles = [Tile(cx, cy, side, side, p_conv / 4) for cx, cy in xy]
        for variant in ("homogeneous", "composite"):
            ov = {} if variant == "homogeneous" else {"hvr_effective": {
                "E": comp.E_eff_mpa / ref["E"],
                "cte": comp.cte_eff / ref["cte"],
                "k": comp.k_eff / ref["k"],
                "nu": comp.nu_eff / ref["nu"]}}
            t0 = time.time()
            tm, sm = run_case(tiles, stack, ov, h_top, P_DIE, OUT / "runs_fp")
            rows.append({
                "j": j, "variant": variant, "A_HVR_per_vr_mm2": comp.a_hvr_mm2,
                "A_HVR_total_mm2": comp.a_hvr_mm2 * 4,
                "component_area_mm2": comp.component_area_mm2,
                "areal_fill": comp.areal_fill,
                "E_eff_MPa": comp.E_eff_mpa if variant == "composite" else ref["E"],
                "cte_eff": comp.cte_eff if variant == "composite" else ref["cte"],
                "k_eff": comp.k_eff if variant == "composite" else ref["k"],
                "P_conv_w": p_conv, "T_max_C": tm["T_max_C"],
                "die_warpage_pv_um": sm["die_warpage_pv_um"],
                "pkg_warpage_pv_um": sm["pkg_warpage_pv_um"],
                "energy_residual_pct": tm["energy_residual_pct"]})
            print(f"  j={j:4.1f} {variant:12s} A={comp.a_hvr_mm2:6.2f} fill={comp.areal_fill:.4f} "
                  f"E={rows[-1]['E_eff_MPa']/1e3:6.1f}GPa cte={rows[-1]['cte_eff']*1e6:5.3f} "
                  f"Tmax={tm['T_max_C']:6.2f} w={sm['die_warpage_pv_um']:7.3f}um ({time.time()-t0:.0f}s)",
                  flush=True)

    with open(OUT / "footprint_material_fe.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    print("\n=== FOOTPRINT WARPAGE TREND ===")
    for v in ("homogeneous", "composite"):
        s = [r for r in rows if r["variant"] == v]
        s.sort(key=lambda r: r["A_HVR_total_mm2"])
        w0, w1 = s[0]["die_warpage_pv_um"], s[-1]["die_warpage_pv_um"]
        print(f"  {v:12s} A {s[0]['A_HVR_total_mm2']:6.1f} -> {s[-1]['A_HVR_total_mm2']:6.1f} mm^2 : "
              f"warpage {w0:7.3f} -> {w1:7.3f} um   span {max(r['die_warpage_pv_um'] for r in s)/min(r['die_warpage_pv_um'] for r in s):6.3f}x"
              f"   d(w)/d(A) = {(w1-w0)/(s[-1]['A_HVR_total_mm2']-s[0]['A_HVR_total_mm2']):+.5f} um/mm^2")
    print(f"\nwrote {OUT/'footprint_material_fe.csv'}")


if __name__ == "__main__":
    main()
