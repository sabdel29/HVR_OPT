#!/usr/bin/env python3
"""Phase-0D-R corrected coupled sweep: architecture-aware PPDN -> ET fixed point ->
spatially-mapped Joule heat -> thermal -> mechanics."""
from __future__ import annotations

import csv, json, math, sys, time
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parents[2]
for p in ("phase0b", "phase0d", "phase0dr"):
    sys.path.insert(0, str(R / "scripts" / p))

from etm.config import build_materials, load_doe, load_stack
from etm.mesh import build
from etm.placement import Tile, case_tiles, generate
from etm import ccxio, metrics
from electrical import compile_hvr
from architecture import evaluate

P0B, OUT = R / "results" / "phase0b", R / "results" / "phase0dr"
I_TOTAL, P_DIE, T_ALLOW = 240.0, 240.0, 100.0
PLACE = {"distributed": "distributed_2x2", "asymmetric": "asymmetric_left",
         "edge": "edge_corner_biased", "compact": "compact_2x2_central"}


def tiles_for(fam, side, stack, doe, n_vr=4):
    g, rules = stack["geometry"], doe["placement_rules"]
    return [(t.cx, t.cy) for t in generate(
        PLACE[fam], n_vr, side, side, die_x=g["functional_die"]["size_x"]["value"],
        die_y=g["functional_die"]["size_y"]["value"],
        keepout=rules["edge_keepout_mm"]["value"],
        min_gap=rules["min_gap_mm"]["value"], p_total=1.0)]


def thermal_structural(tiles, stack, h_sub, h_top, p_die_extra, wd, threads=32):
    """Heat sources: converter loss on the HVR tiles, distribution loss in the die/RDL layer."""
    wd.mkdir(parents=True, exist_ok=True)
    mats = build_materials(stack)
    m = build(tiles, stack, h_sub, h_xy=0.32, z_scale=1.4)
    tinp = wd / "th.inp"
    films = ccxio.write_thermal(m, mats, tiles, stack, p_die_extra, h_top, tinp)
    ccxio.run_ccx(tinp, threads=threads)
    T = ccxio.read_frd(wd / "th.frd")["NDTEMP"]
    tm = metrics.thermal_metrics(m, T, films, stack,
                                 p_die_extra + sum(t.power_w for t in tiles), h_top)
    sinp = wd / "st.inp"
    ccxio.write_structural(m, mats, T[1:m.n_nodes + 1, 0], stack, "BC_A", sinp, solver="")
    ccxio.run_ccx(sinp, threads=threads)
    s = ccxio.read_frd(wd / "st.frd")
    sm = metrics.structural_metrics(m, s["DISP"], s["STRESS"], stack)
    for pat in ("*.frd", "*.inp", "*.dat", "*.sta", "*.cvg", "*.12d"):
        for f in wd.glob(pat):
            f.unlink(missing_ok=True)
    return tm, sm


def coupled(arch, fam, j, h_sub, stack, doe, h_top, wd, tol=0.05, max_it=15):
    """ET fixed point with the corrected PPDN, then the mechanical replay."""
    des = compile_hvr(I_TOTAL / 4, j)
    if des is None:
        return None
    side = math.sqrt(des.area_mm2)
    xy = tiles_for(fam, side, stack, doe)
    T = 25.0
    hist, prev = [], None
    for it in range(max_it):
        p_conv = sum(des.loss_at(T)["p_conv_w"] for _ in range(4))
        e = evaluate(arch, xy, side, h_sub, I_TOTAL, p_conv, T)
        if not e["feasible"]:
            return {"arch": arch, "fam": fam, "j": j, "h_sub_mm": h_sub,
                    "feasible": False, "reason": "; ".join(e["infeasible_reasons"])[:200]}
        tiles = [Tile(cx, cy, side, side, p_conv / 4) for cx, cy in xy]
        tm, sm = thermal_structural(tiles, stack, h_sub, h_top, P_DIE + e["P_pdn_w"], wd)
        Tn = tm["T_max_C"]
        hist.append({"it": it, "T_max_C": Tn, "P_conv_w": p_conv,
                     "P_pdn_w": e["P_pdn_w"], "P_elec_w": e["P_elec_total_w"]})
        if prev is not None and abs(Tn - prev) < tol:
            break
        prev, T = Tn, Tn
    t = e["P_by_tier_w"]
    return {"arch": arch, "fam": fam, "placement": PLACE[fam], "j": j, "h_sub_mm": h_sub,
            "feasible": True, "tsv_rail": e["tsv_rail"], "tile_side_mm": side,
            "a_hvr_total_mm2": des.area_mm2 * 4, "f_sw_MHz": des.f_sw_hz / 1e6,
            "I_tsv_a": e["I_tsv_a"], "n_tsv_req": e["n_tsv_required"],
            "P_conv_w": e["P_conv_w"], "P_bga_w": t.get("bga", 0.0),
            "P_c4_w": t.get("c4", 0.0), "P_tsv_w": t.get("tsv", 0.0),
            "P_microbump_w": t.get("microbump", 0.0), "P_rdl_w": t.get("rdl", 0.0),
            "P_pdn_w": e["P_pdn_w"], "P_elec_total_w": e["P_elec_total_w"],
            "efficiency_pct": 100 * P_DIE / (P_DIE + e["P_elec_total_w"]),
            "dV_total_v": e["dV_total_v"], "dV_rdl_v": e["dV_by_tier_v"].get("rdl", 0.0),
            "T_max_C": tm["T_max_C"], "energy_residual_pct": tm["energy_residual_pct"],
            "die_warpage_pv_um": sm["die_warpage_pv_um"],
            "pkg_warpage_pv_um": sm["pkg_warpage_pv_um"],
            "et_iters": len(hist), "history": hist}


def main():
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((P0B / "cooling_calibration.json").read_text())["h_top_W_m2K"]
    OUT.mkdir(parents=True, exist_ok=True)

    combos = []
    for fam in ("distributed", "asymmetric", "edge", "compact"):      # placement re-audit
        combos.append(("ARCH_A", fam, 2.0, 0.500))
    for h in (0.200, 0.500):                                          # thickness, both rails
        for arch in ("ARCH_A", "ARCH_B"):
            combos.append((arch, "distributed", 2.0, h))
    for j in (4.0, 1.5):                                              # footprint re-audit
        for h in (0.200, 0.500):
            combos.append(("ARCH_A", "distributed", j, h))

    seen, rows = set(), []
    for arch, fam, j, h in combos:
        key = (arch, fam, j, h)
        if key in seen:
            continue
        seen.add(key)
        cid = f"{arch}_{fam}_J{j:g}_h{int(h*1000)}"
        r = coupled(arch, fam, j, h, stack, doe, h_top, OUT / "runs" / cid)
        if r is None:
            print(f"  {cid}: no feasible converter", flush=True); continue
        r["case"] = cid
        rows.append(r)
        if r["feasible"]:
            print(f"  {cid:34s} rail={r['tsv_rail']} P_conv={r['P_conv_w']:6.2f} "
                  f"P_rdl={r['P_rdl_w']:7.3f} P_tsv={r['P_tsv_w']*1e3:7.2f}mW "
                  f"P_el={r['P_elec_total_w']:7.2f}W eta={r['efficiency_pct']:6.2f}% "
                  f"Tmax={r['T_max_C']:6.2f} w={r['die_warpage_pv_um']:7.3f}um "
                  f"({r['et_iters']}it)", flush=True)
        else:
            print(f"  {cid:34s} INFEASIBLE: {r['reason'][:90]}", flush=True)

    (OUT / "corrected_runs.json").write_text(json.dumps(rows, indent=2))
    ok = [r for r in rows if r["feasible"]]
    cols = [k for k in ok[0] if k != "history"]
    with (OUT / "coupled_candidates_corrected.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(ok)
    print(f"\nwrote {OUT/'coupled_candidates_corrected.csv'} ({len(ok)} feasible / {len(rows)})")


if __name__ == "__main__":
    main()
