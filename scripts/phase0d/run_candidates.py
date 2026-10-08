#!/usr/bin/env python3
"""Phase-0D coupled candidate replay.

For each candidate architecture:
  1. compile a REAL converter with the upstream optimizer at (I_out, J_target)
     -> the area budget sets BOTH the HVR footprint and the converter loss, which is the
        physical footprint<->loss coupling the June framework encodes. Converter loss is
        therefore an OUTCOME, never a manually swept knob.
  2. run the ET fixed point (temperature-dependent R_DS(on), DCR, rho_Cu, geometry-derived
     TSV field) to convergence
  3. replay the converged heat sources through the validated M0 thermal+structural model at
     production mesh to obtain die warpage

The ET objective was frozen in results/phase0d/ET_OBJECTIVE_DEFINITION.md before this ran.
"""
from __future__ import annotations

import csv
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0b"))
sys.path.insert(0, str(R / "scripts" / "phase0d"))

from etm.config import build_materials, load_doe, load_stack     # noqa: E402
from etm.placement import PlacementError, Tile, generate         # noqa: E402
from etm import ccxio, metrics                                   # noqa: E402
from etm.mesh import build                                       # noqa: E402
from electrical import compile_hvr, rdl_rho_per_mm               # noqa: E402
from coupled import solve_et                                     # noqa: E402

P0B, OUT = R / "results" / "phase0b", R / "results" / "phase0d"
I_TOTAL, P_DIE = 240.0, 240.0
T_ALLOW = 100.0

GRID_N = [4, 6]
GRID_J = [4.0, 2.0, 1.5]              # A/mm^2 area-budget target -> footprint AND loss
GRID_H = [0.200, 0.500]               # mm
# Placement classes are count-specific, so the grid names a FAMILY and the concrete class is
# resolved per VR count. (A first pass used "distributed_2x2" for every count and silently
# skipped all N=6 distributed candidates.)
PLACEMENT_BY_N = {4: {"distributed": "distributed_2x2", "asymmetric": "asymmetric_left",
                      "compact": "compact_2x2_central", "edge": "edge_corner_biased"},
                  6: {"distributed": "distributed_3x2", "asymmetric": "asymmetric_left",
                      "compact": "distributed_3x2", "edge": "perimeter_ring"}}
GRID_P = ["distributed", "asymmetric"]
EXTRA_P = ["compact", "edge"]              # N=4, J=2.0 only


N_POL_SIDE = 10          # 100 POL segments, matching the June-2026 load segmentation


def pol_grid(die_x: float, die_y: float) -> np.ndarray:
    """100 POL segments over the die, as in June-2026. A coarse 4-point grid concentrates the
    load artificially and exaggerates routing loss for offset placements."""
    xs = (np.arange(N_POL_SIDE) + 0.5) / N_POL_SIDE * die_x - die_x / 2
    ys = (np.arange(N_POL_SIDE) + 0.5) / N_POL_SIDE * die_y - die_y / 2
    return np.array([(x, y) for x in xs for y in ys])


def place(n_vr, placement, side, stack, doe):
    g, rules = stack["geometry"], doe["placement_rules"]
    return generate(placement, n_vr, side, side,
                    die_x=g["functional_die"]["size_x"]["value"],
                    die_y=g["functional_die"]["size_y"]["value"],
                    keepout=rules["edge_keepout_mm"]["value"],
                    min_gap=rules["min_gap_mm"]["value"], p_total=1.0)


def mechanical_replay(tiles, stack, h_sub, h_top, p_die_extra, workdir, threads=32):
    """Thermal + structural at production mesh using the CONVERGED heat sources."""
    workdir.mkdir(parents=True, exist_ok=True)
    mats = build_materials(stack)
    m = build(tiles, stack, h_sub, h_xy=0.32, z_scale=1.4)
    tinp = workdir / "thermal.inp"
    films = ccxio.write_thermal(m, mats, tiles, stack, p_die_extra, h_top, tinp)
    ccxio.run_ccx(tinp, threads=threads)
    T = ccxio.read_frd(workdir / "thermal.frd")["NDTEMP"]
    tm = metrics.thermal_metrics(m, T, films, stack,
                                 p_die_extra + sum(t.power_w for t in tiles), h_top)
    sinp = workdir / "structural.inp"
    binfo = ccxio.write_structural(m, mats, T[1:m.n_nodes + 1, 0], stack, "BC_A", sinp,
                                   solver="")
    ccxio.run_ccx(sinp, threads=threads)
    s = ccxio.read_frd(workdir / "structural.frd")
    sm = metrics.structural_metrics(m, s["DISP"], s["STRESS"], stack)
    for pat in ("*.frd", "*.inp", "*.dat", "*.sta", "*.cvg", "*.12d"):
        for f in workdir.glob(pat):
            f.unlink(missing_ok=True)
    return tm, sm, m.n_elems


def main():
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((P0B / "cooling_calibration.json").read_text())["h_top_W_m2K"]
    g = stack["geometry"]
    pol = pol_grid(g["functional_die"]["size_x"]["value"], g["functional_die"]["size_y"]["value"])
    (OUT / "fixed_point_histories").mkdir(parents=True, exist_ok=True)

    combos = [(n, j, h, p) for n in GRID_N for j in GRID_J for h in GRID_H for p in GRID_P]
    combos += [(4, 2.0, h, p) for h in GRID_H for p in EXTRA_P]
    print(f"candidate grid: {len(combos)} combinations\n")

    designs, rows, t0 = {}, [], time.time()
    for idx, (n_vr, j, h_sub, fam) in enumerate(combos, 1):
        cid = f"D{idx:02d}"
        placement = PLACEMENT_BY_N[n_vr][fam]
        i_out = I_TOTAL / n_vr
        key = (n_vr, j)
        if key not in designs:
            designs[key] = compile_hvr(i_out, j)
        des = designs[key]
        if des is None:
            print(f"  {cid}: N={n_vr} J={j} -> NO FEASIBLE CONVERTER, skipped", flush=True)
            continue
        side = math.sqrt(des.area_mm2)
        try:
            tiles_xy = [(t.cx, t.cy) for t in place(n_vr, placement, side, stack, doe)]
        except PlacementError as e:
            print(f"  {cid}: N={n_vr} J={j} {placement} side={side:.2f} -> {e}", flush=True)
            continue

        wd = OUT / "candidates" / cid
        et = solve_et(des, tiles_xy, stack, doe, wd, h_sub_mm=h_sub, h_top=h_top,
                      p_die_w=P_DIE, i_total_a=I_TOTAL, tile_ax=side, tile_ay=side,
                      pol_xy=pol, rho_mohm_per_mm=rdl_rho_per_mm(), threads=32)
        (OUT / "fixed_point_histories" / f"{cid}.json").write_text(json.dumps(et.history, indent=2))
        if et.converged and et.p_pdn_w > 0.5 * P_DIE:
            print(f"  {cid}: P_PDN = {et.p_pdn_w:.1f} W exceeds 50% of the {P_DIE:.0f} W load "
                  f"- outside the model's valid regime, REJECTED", flush=True)
            rows.append({"cand": cid, "n_vr": n_vr, "j_target": j, "h_sub_mm": h_sub,
                         "placement": placement, "converged": False,
                         "reject_reason": "P_PDN exceeds 50% of load"})
            continue
        if not et.converged:
            print(f"  {cid}: ET FIXED POINT DID NOT CONVERGE after {et.iterations} "
                  f"iterations - REJECTED", flush=True)
            rows.append({"cand": cid, "n_vr": n_vr, "j_target": j, "h_sub_mm": h_sub,
                         "placement": placement, "converged": False})
            continue

        p_per_tile = et.p_conv_total_w / n_vr
        tiles = [Tile(cx, cy, side, side, p_per_tile) for cx, cy in tiles_xy]
        tm, sm, nel = mechanical_replay(tiles, stack, h_sub, h_top, P_DIE + et.p_pdn_w, wd)

        rows.append({
            "cand": cid, "converged": True, "n_vr": n_vr, "j_target": j,
            "h_sub_mm": h_sub, "placement": placement, "design": des.label,
            "arch_N": des.arch.N, "arch_K": des.arch.K, "arch_KA": des.arch.K_A,
            "f_sw_MHz": des.f_sw_hz / 1e6, "i_out_per_vr_a": i_out,
            "tile_side_mm": side, "a_hvr_per_vr_mm2": des.area_mm2,
            "a_hvr_total_mm2": des.area_mm2 * n_vr,
            "p_conv_25c_w": des.loss_25c_w * n_vr,
            "p_conv_total_w": et.p_conv_total_w, "p_lateral_w": et.p_lateral_w,
            "p_tsv_w": et.p_tsv_w, "p_pdn_w": et.p_pdn_w,
            "p_elec_total_w": et.p_elec_total_w, "efficiency_pct": et.efficiency_pct,
            "r_tsv_field_uohm": et.r_tsv_field_ohm * 1e6, "n_via_per_vr": et.n_via_per_vr,
            "T_max_C": tm["T_max_C"], "T_max_et_C": et.T_max_c,
            "die_warpage_pv_um": sm["die_warpage_pv_um"],
            "pkg_warpage_pv_um": sm["pkg_warpage_pv_um"],
            "interface_shear_p99_MPa": sm["interface_shear_MPa"]["p99"],
            "energy_residual_pct": tm["energy_residual_pct"],
            "et_iterations": et.iterations, "ripple_ok": et.ripple_ok,
            "thermal_ok": bool(tm["T_max_C"] <= T_ALLOW), "n_elems": nel,
        })
        r_ = rows[-1]
        print(f"  {cid}: N={n_vr} J={j:<4g} h={h_sub*1000:3.0f}u {placement:20s} "
              f"A={r_['a_hvr_total_mm2']:6.1f}mm2 Pconv={r_['p_conv_total_w']:6.2f} "
              f"Ppdn={r_['p_pdn_w']:5.2f} Pel={r_['p_elec_total_w']:6.2f}W "
              f"eta={r_['efficiency_pct']:6.3f}% Tmax={r_['T_max_C']:6.2f} "
              f"w={r_['die_warpage_pv_um']:7.3f}um ({et.iterations}it)", flush=True)

    p = OUT / "coupled_candidates.csv"
    keys = sorted({k for r_ in rows for k in r_})
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["cand", "converged"] +
                           [k for k in keys if k not in ("cand", "converged")])
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {p}  ({len(rows)} candidates, {time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
