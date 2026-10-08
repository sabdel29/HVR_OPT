#!/usr/bin/env python3
"""Phase-0F Sec.1: re-run the key 240 W comparisons on a REALIZABLE geometry.

Phase 0B-0E used t_tile = 150 um (PROVISIONAL) with h_sub in {200, 500} um. The converter
the compiler selects contains a 500 um inductor, so:

  * h_sub = 200 um is geometrically infeasible under EVERY height bound;
  * h_sub = 500 um is infeasible under the nominal bound, and under the optimistic bound the
    only fitting converter costs 27.4 W per VR at 25 C against 4.2 W -- 6.4x worse.

The realizable substrate range for the selected converter starts near 800 um. This script
rebuilds the tile at its true stack height and repeats the three decisive comparisons there,
so the question "do the previous trend directions survive?" is answered rather than assumed.
"""
from __future__ import annotations
import csv, json, math, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for p in ("phase0b", "phase0d", "phase0e", "phase0f"):
    sys.path.insert(0, str(R / "scripts" / p))

from etm.config import build_materials, load_doe, load_stack
from etm.mesh import build
from etm.placement import Tile, generate
from etm import ccxio, metrics
from electrical import compile_hvr
from geometry import cell_stack, check, fitting_inductors, H_TSV_MIN_UM

OUT = R / "results" / "phase0f"
OUT.mkdir(parents=True, exist_ok=True)
P0B = R / "results" / "phase0b"
P_DIE, T_FREEZE, THREADS = 240.0, 85.0, 16
BOUND = "nominal"


def tiles_for(place, side, stack, doe, n_vr=4):
    g, rules = stack["geometry"], doe["placement_rules"]
    return [(t.cx, t.cy) for t in generate(
        place, n_vr, side, side, die_x=g["functional_die"]["size_x"]["value"],
        die_y=g["functional_die"]["size_y"]["value"],
        keepout=rules["edge_keepout_mm"]["value"],
        min_gap=rules["min_gap_mm"]["value"], p_total=1.0)]


def run(place, side, h_sub, t_tile, stack, doe, h_top, p_conv, wd, h_xy=0.40):
    """Mechanical+thermal at an explicit tile thickness."""
    st = json.loads(json.dumps(stack))                     # deep copy; never mutate the source
    st["geometry"]["hvr_tile"]["thickness"]["value"] = t_tile
    wd.mkdir(parents=True, exist_ok=True)
    mats = build_materials(st)
    tiles = [Tile(cx, cy, side, side, p_conv / 4)
             for cx, cy in tiles_for(place, side, st, doe)]
    m = build(tiles, st, h_sub, h_xy=h_xy, z_scale=1.4)
    if len(m.elems) > 40000:
        raise RuntimeError(f"{len(m.elems)} C3D8I elements exceeds the 40 000 ceiling")
    ti = wd / "th.inp"
    films = ccxio.write_thermal(m, mats, tiles, st, P_DIE, h_top, ti)
    ccxio.run_ccx(ti, threads=THREADS)
    T = ccxio.read_frd(wd / "th.frd")["NDTEMP"]
    tm = metrics.thermal_metrics(m, T, films, st, P_DIE + p_conv, h_top)
    si = wd / "st.inp"
    ccxio.write_structural(m, mats, T[1:m.n_nodes + 1, 0], st, "BC_A", si, solver="")
    ccxio.run_ccx(si, threads=THREADS)
    s = ccxio.read_frd(wd / "st.frd")
    sm = metrics.structural_metrics(m, s["DISP"], s["STRESS"], st)
    for pat in ("*.frd", "*.inp", "*.dat", "*.sta", "*.cvg", "*.12d"):
        for f in wd.glob(pat):
            f.unlink(missing_ok=True)
    return {"T_max_C": tm["T_max_C"], "die_warpage_pv_um": sm["die_warpage_pv_um"],
            "pkg_warpage_pv_um": sm["pkg_warpage_pv_um"],
            "energy_residual_pct": tm["energy_residual_pct"], "n_elem": len(m.elems)}


def main():
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((P0B / "cooling_calibration.json").read_text())["h_top_W_m2K"]
    wd = OUT / "runs_geom"
    rows = []

    # realizable thin / thick pair for the selected converter, plus the legacy pair for
    # explicit comparison (flagged, not simulated where infeasible)
    CASES = [
        ("legacy_thin",  "distributed_2x2", 2.0, 0.2, 0.150),
        ("legacy_thick", "distributed_2x2", 2.0, 0.5, 0.150),
        ("real_thin",    "distributed_2x2", 2.0, 0.8, None),
        ("real_thick",   "distributed_2x2", 2.0, 1.5, None),
        ("real_small_fp", "distributed_2x2", 4.0, 1.5, None),
        ("real_large_fp", "distributed_2x2", 1.5, 1.5, None),
        ("real_edge",    "edge_corner_biased", 2.0, 1.5, None),
        ("real_dist",    "distributed_2x2", 2.0, 1.5, None),
    ]
    for tag, place, j, h_sub, t_forced in CASES:
        fit, budget = fitting_inductors(h_sub, BOUND)
        des = compile_hvr(60.0, j, inductor_library=fit) if fit else None
        des_free = compile_hvr(60.0, j)                      # unconstrained, for reference
        if t_forced is not None:
            # legacy geometry: report realizability of the UNCONSTRAINED design at that h_sub
            r = check(des_free, h_sub, BOUND)
            rows.append({"case": tag, "placement": place, "j": j, "h_sub_mm": h_sub,
                         "t_tile_mm": t_forced, "geometry": "LEGACY(150 um tile)",
                         "realizable": r.feasible, "reason": r.reason,
                         "inductor": r.inductor_name, "inductor_h_um": r.inductor_h_um,
                         "t_cell_required_um": r.t_cell_um, "h_sub_min_um": r.h_sub_min_um,
                         "n_fitting_inductors": len(fit),
                         "P_conv_1vr_25C_w": des_free.loss_25c_w,
                         "tile_side_mm": math.sqrt(des_free.area_mm2),
                         "T_max_C": None, "die_warpage_pv_um": None,
                         "pkg_warpage_pv_um": None, "energy_residual_pct": None,
                         "simulated": False})
            print(f"  {tag:14s} h={h_sub:.1f} LEGACY   realizable={r.feasible}  {r.reason}",
                  flush=True)
            continue
        if des is None:
            rows.append({"case": tag, "placement": place, "j": j, "h_sub_mm": h_sub,
                         "t_tile_mm": None, "geometry": "REALIZABLE", "realizable": False,
                         "reason": "no converter can be built from the fitting inductor set",
                         "inductor": None, "inductor_h_um": None, "t_cell_required_um": None,
                         "h_sub_min_um": None, "n_fitting_inductors": len(fit),
                         "P_conv_1vr_25C_w": None, "tile_side_mm": None, "T_max_C": None,
                         "die_warpage_pv_um": None, "pkg_warpage_pv_um": None,
                         "energy_residual_pct": None, "simulated": False})
            print(f"  {tag:14s} h={h_sub:.1f} NO FEASIBLE DESIGN ({len(fit)} inductors fit)",
                  flush=True)
            continue
        cs = cell_stack(des, BOUND)
        t_tile = cs.t_cell_mm
        side = math.sqrt(des.area_mm2)
        p_conv = 4 * des.loss_at(T_FREEZE)["p_conv_w"]
        t0 = time.time()
        m = run(place, side, h_sub, t_tile, stack, doe, h_top, p_conv, wd)
        rows.append({"case": tag, "placement": place, "j": j, "h_sub_mm": h_sub,
                     "t_tile_mm": t_tile, "geometry": "REALIZABLE", "realizable": True,
                     "reason": "realizable", "inductor": des.inductor.name,
                     "inductor_h_um": des.inductor.height_um,
                     "t_cell_required_um": cs.t_cell_um,
                     "h_sub_min_um": cs.h_sub_min_um, "n_fitting_inductors": len(fit),
                     "P_conv_1vr_25C_w": des.loss_25c_w, "tile_side_mm": side,
                     "P_conv_4vr_85C_w": p_conv, "simulated": True, **m})
        print(f"  {tag:14s} h={h_sub:.1f} t_tile={t_tile*1e3:.0f}um side={side:.3f} "
              f"Tmax={m['T_max_C']:6.2f} w={m['die_warpage_pv_um']:7.3f}um "
              f"Ebal={m['energy_residual_pct']:+.3f}% ({time.time()-t0:.0f}s)", flush=True)

    keys = sorted({k for r in rows for k in r})
    with open(OUT / "geometry_recheck.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
    print(f"\nwrote {OUT/'geometry_recheck.csv'}")

    sim = [r for r in rows if r.get("simulated")]
    def g(tag):
        return next((r for r in sim if r["case"] == tag), None)
    print("\n=== DO THE PREVIOUS TREND DIRECTIONS SURVIVE? ===")
    for lab, a, b, prev in (("thickness 800->1500 um", "real_thin", "real_thick",
                             "thicker lowers warpage (-56.5 % at 200->500)"),
                            ("footprint small->large", "real_small_fp", "real_large_fp",
                             "larger raises warpage (+87.9 %)"),
                            ("placement dist->edge", "real_dist", "real_edge",
                             "edge lowers warpage (-41.5 %)")):
        ra, rb = g(a), g(b)
        if not (ra and rb):
            print(f"  {lab:26s} incomplete"); continue
        dw = 100 * (rb["die_warpage_pv_um"] - ra["die_warpage_pv_um"]) / ra["die_warpage_pv_um"]
        dt = rb["T_max_C"] - ra["T_max_C"]
        print(f"  {lab:26s} dwarp {dw:+7.2f} %   dT {dt:+6.2f} K   | previously: {prev}")


if __name__ == "__main__":
    main()
