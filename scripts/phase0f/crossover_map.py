#!/usr/bin/env python3
"""Phase-0F Sec.11: where does mechanics become decision-relevant?

The central question is the load at which ARCH_B's thickness preference changes sign:

    dP_total(h_thick) - dP_total(h_thin)  =  0

Below that load a thicker substrate is electrically free (or better) and mechanically better,
so there is no tension. Above it the LV rail's longer TSV costs more than the thicker, cooler
package saves, and thickness becomes a genuine three-domain conflict.

This is computed on the ELECTRICAL model alone at a frozen temperature, which is cheap enough
to sweep densely, and is then anchored against the two full ET fixed points (240 W and 1 kW)
that were run properly.
"""
from __future__ import annotations
import csv, json, math, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0f"))
sys.path.insert(0, str(R / "scripts" / "phase0e"))
sys.path.insert(0, str(R / "scripts" / "phase0d"))
import kw1
from architecture0e import evaluate as elec_eval, CROWDING_DEFAULT
from stack import stacks_from_cfg
from geometry import fitting_inductors, cell_stack
from electrical import compile_hvr
from placement0f import build as build0f
from etm.config import load_stack, load_doe

OUT = R / "results" / "phase0f"
DIE, KEEP, GAP = 22.36, 0.5, 0.5
T_FROZEN = 84.0


def design_for(load_w, m_vr, j, h_sub):
    fit, _ = fitting_inductors(h_sub, "nominal")
    if not fit:
        return None
    return compile_hvr(load_w / m_vr, j, inductor_library=fit)


def elec_at(load_w, m_vr, j, h_sub, arch, rdl, des=None):
    des = des or design_for(load_w, m_vr, j, h_sub)
    if des is None:
        return None
    side = math.sqrt(des.area_mm2)
    try:
        tiles, _ = build0f("uniform", m_vr, side, DIE, KEEP, GAP)
    except Exception:
        return None
    xy = [(t.cx, t.cy) for t in tiles]
    cs = cell_stack(des, "nominal")
    if h_sub * 1e3 - cs.t_cell_um < 50.0:
        return None
    p_conv = m_vr * des.loss_at(T_FROZEN)["p_conv_w"]
    e = elec_eval(arch, xy, side, h_sub, load_w, p_conv, T_FROZEN, rdl,
                  crowding=CROWDING_DEFAULT, strict=False, t_tile_mm=cs.t_cell_mm)
    return {"P_conv_w": p_conv, "P_tsv_w": e["P_by_tier_w"].get("tsv", 0.0),
            "P_rdl_w": e["P_by_tier_w"].get("rdl", 0.0), "P_pdn_w": e["P_pdn_w"],
            "P_elec_total_w": e["P_elec_total_w"], "side": side,
            "n_tsv_alloc": e["n_tsv_alloc"], "n_tsv_avail": e["n_tsv_avail"],
            "t_cell_um": cs.t_cell_um}


def main():
    rdl = stacks_from_cfg()["ectc2024_primary"]
    H_THIN, H_THICK = 0.8, 1.5
    rows = []
    loads = [120, 240, 400, 600, 800, 1000, 1400, 2000, 3000, 4000, 6000]
    print(f"{'load':>6s} {'M':>4s} {'arch':7s} {'P_el(thin)':>11s} {'P_el(thick)':>12s} "
          f"{'dP_thick-thin':>14s} {'dP_tsv':>9s} {'dP_conv':>9s} {'thickness pref':>15s}")
    for load in loads:
        # keep per-VR current near the 1-kW reference so the converter stays comparable
        m_vr = max(4, min(49, int(round(load / (1000.0 / kw1.M_VR)))))
        for cand in (m_vr, 49, 36, 25, 16, 9, 4):
            d = design_for(load, cand, kw1.J_TARGET, H_THICK)
            if d is None:
                continue
            try:
                build0f("uniform", cand, math.sqrt(d.area_mm2), DIE, KEEP, GAP)
                m_vr = cand; break
            except Exception:
                continue
        for arch in ("ARCH_A", "ARCH_B"):
            a = elec_at(load, m_vr, kw1.J_TARGET, H_THIN, arch, rdl)
            b = elec_at(load, m_vr, kw1.J_TARGET, H_THICK, arch, rdl)
            if not (a and b):
                continue
            d_tot = b["P_elec_total_w"] - a["P_elec_total_w"]
            rows.append({"load_w": load, "m_vr": m_vr, "arch": arch,
                         "h_thin_mm": H_THIN, "h_thick_mm": H_THICK,
                         "P_elec_thin_w": a["P_elec_total_w"],
                         "P_elec_thick_w": b["P_elec_total_w"],
                         "dP_total_w": d_tot,
                         "dP_tsv_w": b["P_tsv_w"] - a["P_tsv_w"],
                         "dP_conv_w": b["P_conv_w"] - a["P_conv_w"],
                         "dP_rdl_w": b["P_rdl_w"] - a["P_rdl_w"],
                         "thickness_electrically_preferred": bool(d_tot < 0),
                         "n_tsv_alloc_thick": b["n_tsv_alloc"],
                         "tile_side_mm": b["side"]})
            print(f"{load:6d} {m_vr:4d} {arch:7s} {a['P_elec_total_w']:11.3f} "
                  f"{b['P_elec_total_w']:12.3f} {d_tot:+14.4f} "
                  f"{b['P_tsv_w']-a['P_tsv_w']:+9.4f} {b['P_conv_w']-a['P_conv_w']:+9.4f} "
                  f"{'THICK' if d_tot < 0 else 'THIN':>15s}")

    with open(OUT / "crossover_map.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    print("\n=== ARCH_B thickness-preference crossover ===")
    b = sorted([r for r in rows if r["arch"] == "ARCH_B"], key=lambda r: r["load_w"])
    prev = None
    found = False
    for r in b:
        if prev and prev["dP_total_w"] * r["dP_total_w"] < 0:
            x0, y0 = prev["load_w"], prev["dP_total_w"]
            x1, y1 = r["load_w"], r["dP_total_w"]
            xc = x0 - y0 * (x1 - x0) / (y1 - y0)
            print(f"  sign change between {x0} W and {x1} W  ->  crossover at "
                  f"P_load = {xc:.0f} W")
            found = True
        prev = r
    if not found:
        s = {r["thickness_electrically_preferred"] for r in b}
        print(f"  no sign change over {b[0]['load_w']}-{b[-1]['load_w']} W; "
              f"thickness electrically preferred = {s}")
    a = sorted([r for r in rows if r["arch"] == "ARCH_A"], key=lambda r: r["load_w"])
    print(f"  ARCH_A: thickness preferred THICK at every load = "
          f"{all(r['thickness_electrically_preferred'] for r in a)}")
    print(f"\nwrote {OUT/'crossover_map.csv'}")


if __name__ == "__main__":
    main()
