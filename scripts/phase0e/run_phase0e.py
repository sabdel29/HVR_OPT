#!/usr/bin/env python3
"""Phase-0E decisive coupled re-run.

Differences from the Phase-0D-R sweep, all of them physical rather than numerical:
  * sourced ECTC-2024 RDL stack, solved as an explicit VDD + GND pair;
  * n_required / n_allocated / n_available separated, R_field uses n_ALLOCATED;
  * per-via limit from the source-backed current-density envelope;
  * HFSS-measured current-crowding factor on the vertical tiers;
  * PER-VR LOCAL TEMPERATURE drives each converter, not the global package maximum,
    so an asymmetric layout is allowed to produce unequal converter losses (Sec. 14).

The converter designs themselves are re-compiled identically to Phase 0D-R, so every
difference below is attributable to the stack and allocation corrections.
"""
from __future__ import annotations
import csv, json, math, sys, time
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parents[2]
for p in ("phase0b", "phase0d", "phase0dr", "phase0e"):
    sys.path.insert(0, str(R / "scripts" / p))

from etm.config import build_materials, load_doe, load_stack
from etm.mesh import build
from etm.placement import Tile, generate
from etm import ccxio, metrics
from electrical import compile_hvr
from architecture0e import evaluate, CROWDING_DEFAULT
from stack import stacks_from_cfg

P0B, OUT = R / "results" / "phase0b", R / "results" / "phase0e"
OUT.mkdir(parents=True, exist_ok=True)
I_TOTAL, P_DIE = 240.0, 240.0
PLACE = {"distributed": "distributed_2x2", "asymmetric": "asymmetric_left",
         "edge": "edge_corner_biased", "compact": "compact_2x2_central"}


def tiles_for(fam, side, stack, doe, n_vr=4):
    g, rules = stack["geometry"], doe["placement_rules"]
    return [(t.cx, t.cy) for t in generate(
        PLACE[fam], n_vr, side, side, die_x=g["functional_die"]["size_x"]["value"],
        die_y=g["functional_die"]["size_y"]["value"],
        keepout=rules["edge_keepout_mm"]["value"],
        min_gap=rules["min_gap_mm"]["value"], p_total=1.0)]


def tile_temperatures(m, T, n_tiles: int) -> list[float]:
    """Volume-weighted mean temperature of each HVR tile's own elements.

    Sec. 14 requires the converter to see its LOCAL temperature. Using the global package
    maximum gives every VR the same loss by construction and hides layout asymmetry.
    """
    nodes = m.nodes
    out = []
    for k in range(n_tiles):
        sel = np.where(m.elem_tile == k)[0]
        if sel.size == 0:
            out.append(float(np.max(T)))
            continue
        conn = m.elems[sel] - 1
        xyz = nodes[conn]                                   # (E,8,3)
        vol = (xyz[:, :, 0].max(1) - xyz[:, :, 0].min(1)) * \
              (xyz[:, :, 1].max(1) - xyz[:, :, 1].min(1)) * \
              (xyz[:, :, 2].max(1) - xyz[:, :, 2].min(1))
        te = T[conn].mean(axis=1)
        out.append(float((te * vol).sum() / vol.sum()))
    return out


def thermal_structural(tiles, stack, h_sub, h_top, p_die_extra, wd, threads=32):
    wd.mkdir(parents=True, exist_ok=True)
    mats = build_materials(stack)
    m = build(tiles, stack, h_sub, h_xy=0.32, z_scale=1.4)
    tinp = wd / "th.inp"
    films = ccxio.write_thermal(m, mats, tiles, stack, p_die_extra, h_top, tinp)
    ccxio.run_ccx(tinp, threads=threads)
    Tn = ccxio.read_frd(wd / "th.frd")["NDTEMP"]
    tm = metrics.thermal_metrics(m, Tn, films, stack,
                                 p_die_extra + sum(t.power_w for t in tiles), h_top)
    Tnode = Tn[1:m.n_nodes + 1, 0]
    t_tiles = tile_temperatures(m, Tnode, len(tiles))
    sinp = wd / "st.inp"
    ccxio.write_structural(m, mats, Tnode, stack, "BC_A", sinp, solver="")
    ccxio.run_ccx(sinp, threads=threads)
    s = ccxio.read_frd(wd / "st.frd")
    sm = metrics.structural_metrics(m, s["DISP"], s["STRESS"], stack)
    for pat in ("*.frd", "*.inp", "*.dat", "*.sta", "*.cvg", "*.12d"):
        for f in wd.glob(pat):
            f.unlink(missing_ok=True)
    return tm, sm, t_tiles


def coupled(arch, fam, j, h_sub, stack, doe, h_top, wd, rdl_stack, policy="A_min_capability",
            j_cu=None, crowding=CROWDING_DEFAULT, tol=0.05, max_it=15):
    des = compile_hvr(I_TOTAL / 4, j)
    if des is None:
        return None
    side = math.sqrt(des.area_mm2)
    xy = tiles_for(fam, side, stack, doe)
    n_vr = len(xy)
    t_vr = [25.0] * n_vr
    hist, prev = [], None
    for it in range(max_it):
        per_vr = [des.loss_at(t)["p_conv_w"] for t in t_vr]
        p_conv = float(sum(per_vr))
        e = evaluate(arch, xy, side, h_sub, I_TOTAL, p_conv, float(np.mean(t_vr)),
                     rdl_stack, policy=policy, j_cu=j_cu, crowding=crowding, strict=False)
        tiles = [Tile(cx, cy, side, side, per_vr[k]) for k, (cx, cy) in enumerate(xy)]
        tm, sm, t_tiles = thermal_structural(tiles, stack, h_sub, h_top,
                                             P_DIE + e["P_pdn_w"], wd)
        Tn = tm["T_max_C"]
        hist.append({"it": it, "T_max_C": Tn, "T_vr_C": t_tiles, "P_conv_w": p_conv,
                     "P_conv_per_vr_w": per_vr, "P_pdn_w": e["P_pdn_w"]})
        if prev is not None and abs(Tn - prev) < tol:
            break
        prev, t_vr = Tn, t_tiles
    t = e["P_by_tier_w"]
    return {"arch": arch, "fam": fam, "placement": PLACE[fam], "j": j, "h_sub_mm": h_sub,
            "feasible": e["feasible"], "infeasible": "; ".join(e["infeasible"])[:200],
            "tsv_rail": e["tsv_rail"], "tile_side_mm": side,
            "a_hvr_total_mm2": des.area_mm2 * n_vr, "f_sw_MHz": des.f_sw_hz / 1e6,
            "I_tsv_a": e["I_tsv_a"], "n_tsv_req": e["n_tsv_req"],
            "n_tsv_alloc": e["n_tsv_alloc"], "n_tsv_avail": e["n_tsv_avail"],
            "i_per_tsv_ma": e["i_per_tsv_ma"], "policy": policy,
            "P_conv_w": e["P_conv_w"], "P_conv_spread_pct":
                100 * (max(hist[-1]["P_conv_per_vr_w"]) - min(hist[-1]["P_conv_per_vr_w"]))
                / (sum(hist[-1]["P_conv_per_vr_w"]) / n_vr),
            "T_vr_min_C": min(hist[-1]["T_vr_C"]), "T_vr_max_C": max(hist[-1]["T_vr_C"]),
            "P_bga_w": t.get("bga", 0.0), "P_c4_w": t.get("c4", 0.0),
            "P_tsv_w": t.get("tsv", 0.0), "P_microbump_w": t.get("microbump", 0.0),
            "P_rdl_w": t.get("rdl", 0.0), "P_pdn_w": e["P_pdn_w"],
            "P_elec_total_w": e["P_elec_total_w"],
            "efficiency_pct": 100 * P_DIE / (P_DIE + e["P_elec_total_w"]),
            "T_max_C": tm["T_max_C"], "energy_residual_pct": tm["energy_residual_pct"],
            "die_warpage_pv_um": sm["die_warpage_pv_um"],
            "pkg_warpage_pv_um": sm["pkg_warpage_pv_um"],
            "et_iters": len(hist), "history": hist}


def main():
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((P0B / "cooling_calibration.json").read_text())["h_top_W_m2K"]
    rdl = stacks_from_cfg()["ectc2024_primary"]
    wd = OUT / "runs"
    cases = []
    # placement re-audit (Sec. 11) at the reference point
    for fam in ("distributed", "asymmetric", "edge", "compact"):
        cases.append(("ARCH_A", fam, 2.0, 0.5))
    # thickness re-audit (Sec. 7), both architectures
    for arch in ("ARCH_A", "ARCH_B"):
        for h in (0.2, 0.5):
            cases.append((arch, "distributed", 2.0, h))
    # footprint sweep (Sec. 12 electrical side)
    for j in (1.5, 4.0):
        for h in (0.2, 0.5):
            cases.append(("ARCH_A", "distributed", j, h))

    seen, rows = set(), []
    for arch, fam, j, h in cases:
        k = (arch, fam, j, h)
        if k in seen:
            continue
        seen.add(k)
        t0 = time.time()
        r = coupled(arch, fam, j, h, stack, doe, h_top, wd, rdl)
        if r is None:
            print(f"  {arch:7s} {fam:11s} j={j} h={h}  NO DESIGN")
            continue
        rows.append(r)
        print(f"  {arch:7s} {fam:11s} j={j:4.1f} h={h:.1f}  "
              f"P_rdl={r['P_rdl_w']:7.3f} P_pdn={r['P_pdn_w']:7.3f} "
              f"P_el={r['P_elec_total_w']:7.2f} eta={r['efficiency_pct']:5.2f}% "
              f"Tmax={r['T_max_C']:6.2f} w={r['die_warpage_pv_um']:7.3f}um "
              f"n_alloc={r['n_tsv_alloc']:5d} ({time.time()-t0:.0f}s)")

    (OUT / "phase0e_runs.json").write_text(json.dumps(rows, indent=2, default=float))
    cols = [c for c in rows[0] if c != "history"]
    with open(OUT / "phase0e_candidates.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    print(f"\nwrote {len(rows)} rows -> results/phase0e/phase0e_candidates.csv")


if __name__ == "__main__":
    main()
