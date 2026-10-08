#!/usr/bin/env python3
"""Phase-0E Sec.15: BC-B under the corrected model, decisive pairs only.

Phase 0C showed BC-B suppresses free warpage by roughly 20x, leaving the levers
unresolvable in that metric. The question Phase 0E must answer is not "how much smaller",
it is WHICH RESPONSE STILL DISCRIMINATES when the package is board-restrained.

Tracked: die warpage (p-v), package warpage, die-plane curvature, and interface SHEAR.
Interface PEEL is deliberately excluded -- it never converged (19-20 % at the final
refinement step, a bimaterial-corner singularity) and remains demoted.

A difference is called RESOLVED only if it exceeds 2x the numerical uncertainty
(u_m = 0.5 % on warpage from the Phase-0B/0C mesh convergence study).
"""
from __future__ import annotations
import csv, json, math, sys, time
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parents[2]
for p in ("phase0b", "phase0d", "phase0e"):
    sys.path.insert(0, str(R / "scripts" / p))

from etm.config import build_materials, load_doe, load_stack
from etm.mesh import build
from etm.placement import Tile, generate
from etm import ccxio, metrics
from electrical import compile_hvr

OUT = R / "results" / "phase0e"
P0B = R / "results" / "phase0b"
P_DIE, T_FREEZE, THREADS = 240.0, 85.0, 12
U_M_PCT = 0.5                      # numerical uncertainty on warpage, Phase-0B/0C


def tiles_for(place, side, stack, doe, n_vr=4):
    g, rules = stack["geometry"], doe["placement_rules"]
    return [(t.cx, t.cy) for t in generate(
        place, n_vr, side, side, die_x=g["functional_die"]["size_x"]["value"],
        die_y=g["functional_die"]["size_y"]["value"],
        keepout=rules["edge_keepout_mm"]["value"],
        min_gap=rules["min_gap_mm"]["value"], p_total=1.0)]


def curvature_um_per_mm2(m, U) -> float:
    """Least-squares paraboloid curvature of the die top surface.

    Warpage p-v is a max-minus-min statistic and therefore sensitive to a single node;
    a fitted curvature uses the whole surface and is the more stable response under a
    restraint that flattens the package.
    """
    ids = m.node_ids_at_z(m.layer("die").z1)
    xyz = m.nodes[ids - 1]
    uz = U[ids, 2] * 1000.0
    x, y = xyz[:, 0], xyz[:, 1]
    A = np.column_stack([x**2 + y**2, x, y, np.ones_like(x)])
    c, *_ = np.linalg.lstsq(A, uz, rcond=None)
    return float(c[0])


def run(place, side, h_sub, bc, stack, doe, h_top, p_conv, wd):
    wd.mkdir(parents=True, exist_ok=True)
    mats = build_materials(stack)
    tiles = [Tile(cx, cy, side, side, p_conv / 4)
             for cx, cy in tiles_for(place, side, stack, doe)]
    # BC-B inserts a compliant support layer, which pushes the 0.32 mm mesh to 45 472
    # C3D8I elements -- past the 40 000 ceiling documented in Phase 0B, where the solver
    # SEGFAULTS SILENTLY. run_case.py guards this; this driver calls ccxio directly, so the
    # guard is repeated here and the mesh is coarsened to 0.40 mm for BOTH BC families so the
    # two are compared on the same discretisation.
    m = build(tiles, stack, h_sub, h_xy=0.40, z_scale=1.4,
              support_layer=(bc == "BC_B"))
    if len(m.elems) > 40000:
        raise RuntimeError(
            f"{bc} {place} h={h_sub}: {len(m.elems)} C3D8I elements exceeds the 40 000 "
            "ceiling; CalculiX would segfault without reporting an error")
    ti = wd / "th.inp"
    films = ccxio.write_thermal(m, mats, tiles, stack, P_DIE, h_top, ti)
    ccxio.run_ccx(ti, threads=THREADS)
    T = ccxio.read_frd(wd / "th.frd")["NDTEMP"]
    tm = metrics.thermal_metrics(m, T, films, stack, P_DIE + p_conv, h_top)
    si = wd / "st.inp"
    ccxio.write_structural(m, mats, T[1:m.n_nodes + 1, 0], stack, bc, si, solver="")
    ccxio.run_ccx(si, threads=THREADS)
    s = ccxio.read_frd(wd / "st.frd")
    sm = metrics.structural_metrics(m, s["DISP"], s["STRESS"], stack)
    kap = curvature_um_per_mm2(m, s["DISP"])
    for pat in ("*.frd", "*.inp", "*.dat", "*.sta", "*.cvg", "*.12d"):
        for f in wd.glob(pat):
            f.unlink(missing_ok=True)
    return {"T_max_C": tm["T_max_C"], "die_warpage_pv_um": sm["die_warpage_pv_um"],
            "pkg_warpage_pv_um": sm["pkg_warpage_pv_um"],
            "curvature_um_per_mm2": kap,
            "interface_shear_p99_MPa": sm.get("interface_shear_MPa", {}).get("p99", float("nan")),
            "si_principal_p99_MPa": sm.get("si_principal_MPa", {}).get("p99", float("nan"))}


PAIRS = {
    "A_footprint": [("small_j4.0", "distributed_2x2", 4.0, 0.5),
                    ("large_j1.5", "distributed_2x2", 1.5, 0.5)],
    "B_thickness": [("h200", "distributed_2x2", 2.0, 0.2),
                    ("h500", "distributed_2x2", 2.0, 0.5)],
    "C_placement": [("distributed", "distributed_2x2", 2.0, 0.5),
                    ("edge_biased", "edge_corner_biased", 2.0, 0.5)],
}
METRICS = ["die_warpage_pv_um", "pkg_warpage_pv_um", "curvature_um_per_mm2",
           "interface_shear_p99_MPa", "si_principal_p99_MPa"]


def main():
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((P0B / "cooling_calibration.json").read_text())["h_top_W_m2K"]
    wd = OUT / "runs_bcb"
    rows = []
    for pair, members in PAIRS.items():
        for label, place, j, h in members:
            des = compile_hvr(60.0, j)
            side = math.sqrt(des.area_mm2)
            p_conv = 4 * des.loss_at(T_FREEZE)["p_conv_w"]
            for bc in ("BC_A", "BC_B"):
                t0 = time.time()
                r = run(place, side, h, bc, stack, doe, h_top, p_conv, wd)
                r.update({"pair": pair, "member": label, "bc": bc, "placement": place,
                          "j": j, "h_sub_mm": h, "tile_side_mm": side, "P_conv_w": p_conv})
                rows.append(r)
                print(f"  {pair:12s} {label:12s} {bc}  w={r['die_warpage_pv_um']:8.4f}um "
                      f"kappa={r['curvature_um_per_mm2']:+.3e} shear99={r['interface_shear_p99_MPa']:7.3f}MPa "
                      f"({time.time()-t0:.0f}s)", flush=True)

    with open(OUT / "bcb_corrected_results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    print("\n=== DOES THE LEVER STILL DISCRIMINATE UNDER BC-B? ===")
    print(f"(resolved iff |delta| > 2*u_m = {2*U_M_PCT} %)")
    summary = []
    for pair in PAIRS:
        for bc in ("BC_A", "BC_B"):
            sel = [r for r in rows if r["pair"] == pair and r["bc"] == bc]
            if len(sel) != 2:
                continue
            print(f"\n  {pair}  {bc}")
            for mt in METRICS:
                a, b = sel[0][mt], sel[1][mt]
                if not (np.isfinite(a) and np.isfinite(b)) or abs(a) < 1e-12:
                    continue
                d = 100 * (b - a) / abs(a)
                res = "RESOLVED" if abs(d) > 2 * U_M_PCT else "not resolved"
                print(f"    {mt:26s} {a:11.4f} -> {b:11.4f}   {d:+8.2f} %   {res}")
                summary.append({"pair": pair, "bc": bc, "metric": mt, "a": a, "b": b,
                                "delta_pct": d, "resolved": abs(d) > 2 * U_M_PCT})
    with open(OUT / "bcb_discrimination.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0])); w.writeheader(); w.writerows(summary)
    print(f"\nwrote {OUT/'bcb_corrected_results.csv'} and bcb_discrimination.csv")


if __name__ == "__main__":
    main()
