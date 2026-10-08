#!/usr/bin/env python3
"""Phase-0D robustness: does the ET-vs-ETM conclusion survive the model uncertainties?

Two families are swept, because Phase 0D has BOTH an electrical and a mechanical model:

ELECTRICAL (new in Phase 0D)
  alpha_GaN   0.005 / 0.0075 / 0.010 /K   the ASSUMPTION with no repository source
  I_via_max   4.8 mA / 33 mA              the OPEN per-via current limit

MECHANICAL (carried from Phase 0C)
  HVR tile E and CTE corners, underfill E and CTE corners, TSV field off,
  and the H0 -> H1 homogenisation bias correction (+12.59 % on tsv_homog CTE)

Only the candidates involved in the claimed conclusion are re-run, per the brief.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0b"))
sys.path.insert(0, str(R / "scripts" / "phase0d"))

from etm.config import load_doe, load_stack                      # noqa: E402
from etm.placement import generate                               # noqa: E402
from electrical import compile_hvr, rdl_rho_per_mm               # noqa: E402
from coupled import solve_et                                     # noqa: E402
from run_candidates import PLACEMENT_BY_N, mechanical_replay, pol_grid  # noqa: E402
from etm.placement import Tile                                   # noqa: E402

P0B, P0D = R / "results" / "phase0b", R / "results" / "phase0d"
I_TOTAL, P_DIE = 240.0, 240.0

ELEC_CORNERS = {
    "ref":            dict(),
    "alphaGaN_lo":    dict(alpha_gan=0.005),
    "alphaGaN_hi":    dict(alpha_gan=0.010),
    "ivia_4p8mA":     dict(i_via_max_a=0.0048),
}
MECH_CORNERS = {
    "ref":            dict(),
    "hvr_E_lo":       dict(overrides={"hvr_effective": {"E": 80.0 / 120.0}}),
    "hvr_E_hi":       dict(overrides={"hvr_effective": {"E": 160.0 / 120.0}}),
    "hvr_cte_lo":     dict(overrides={"hvr_effective": {"cte": 4.0 / 6.0}}),
    "hvr_cte_hi":     dict(overrides={"hvr_effective": {"cte": 10.0 / 6.0}}),
    "uf_cte_lo":      dict(overrides={"underfill_homog": {"cte": 0.7}}),
    "uf_cte_hi":      dict(overrides={"underfill_homog": {"cte": 1.3}}),
    "H0_bias_corr":   dict(overrides={"tsv_homog": {"cte": 1.1259}}),
    "tsv_off":        dict(tsv_enabled=False),
}


def build_candidate(spec, stack, doe, h_top, elec_kw, mech_kw, wd):
    n_vr, j, h_sub, fam = spec
    placement = PLACEMENT_BY_N[n_vr][fam]
    des = compile_hvr(I_TOTAL / n_vr, j)
    side = math.sqrt(des.area_mm2)
    g, rules = stack["geometry"], doe["placement_rules"]
    tiles0 = generate(placement, n_vr, side, side,
                      die_x=g["functional_die"]["size_x"]["value"],
                      die_y=g["functional_die"]["size_y"]["value"],
                      keepout=rules["edge_keepout_mm"]["value"],
                      min_gap=rules["min_gap_mm"]["value"], p_total=1.0)
    xy = [(t.cx, t.cy) for t in tiles0]
    pol = pol_grid(g["functional_die"]["size_x"]["value"],
                   g["functional_die"]["size_y"]["value"])
    et = solve_et(des, xy, stack, doe, wd, h_sub_mm=h_sub, h_top=h_top, p_die_w=P_DIE,
                  i_total_a=I_TOTAL, tile_ax=side, tile_ay=side, pol_xy=pol,
                  rho_mohm_per_mm=rdl_rho_per_mm(), threads=32, **elec_kw)
    if not et.converged:
        return None
    tiles = [Tile(cx, cy, side, side, et.p_conv_total_w / n_vr) for cx, cy in xy]
    st = json.loads(json.dumps(stack))
    if mech_kw.get("tsv_enabled") is False:
        st["geometry"]["tsv_field"]["enabled"]["value"] = False
    tm, sm, _ = mechanical_replay_ov(tiles, st, h_sub, h_top, P_DIE + et.p_pdn_w, wd,
                                     mech_kw.get("overrides"))
    return {"p_elec_total_w": et.p_elec_total_w, "T_max_C": tm["T_max_C"],
            "die_warpage_pv_um": sm["die_warpage_pv_um"],
            "a_hvr_total_mm2": des.area_mm2 * n_vr}


def mechanical_replay_ov(tiles, stack, h_sub, h_top, p_extra, wd, overrides):
    from etm.config import build_materials
    from etm.mesh import build
    from etm import ccxio, metrics
    wd.mkdir(parents=True, exist_ok=True)
    mats = build_materials(stack, overrides)
    m = build(tiles, stack, h_sub, h_xy=0.45, z_scale=1.0)
    tinp = wd / "rb_thermal.inp"
    films = ccxio.write_thermal(m, mats, tiles, stack, p_extra, h_top, tinp)
    ccxio.run_ccx(tinp, threads=32)
    T = ccxio.read_frd(wd / "rb_thermal.frd")["NDTEMP"]
    tm = metrics.thermal_metrics(m, T, films, stack,
                                 p_extra + sum(t.power_w for t in tiles), h_top)
    sinp = wd / "rb_struct.inp"
    ccxio.write_structural(m, mats, T[1:m.n_nodes + 1, 0], stack, "BC_A", sinp, solver="")
    ccxio.run_ccx(sinp, threads=32)
    s = ccxio.read_frd(wd / "rb_struct.frd")
    sm = metrics.structural_metrics(m, s["DISP"], s["STRESS"], stack)
    for pat in ("rb_*.frd", "rb_*.inp", "rb_*.dat", "rb_*.sta", "rb_*.cvg", "rb_*.12d"):
        for f in wd.glob(pat):
            f.unlink(missing_ok=True)
    return tm, sm, m.n_elems


def main(specs: dict[str, tuple]):
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((P0B / "cooling_calibration.json").read_text())["h_top_W_m2K"]
    rows = []

    for tag, kw in ELEC_CORNERS.items():
        for name, spec in specs.items():
            r = build_candidate(spec, stack, doe, h_top, kw, {},
                                P0D / "robustness" / f"E_{tag}_{name}")
            if r:
                rows.append({"family": "electrical", "corner": tag, "cand": name, **r})
        print(f"  electrical corner {tag:14s} done", flush=True)

    for tag, kw in MECH_CORNERS.items():
        if tag == "ref":
            continue
        for name, spec in specs.items():
            r = build_candidate(spec, stack, doe, h_top, {}, kw,
                                P0D / "robustness" / f"M_{tag}_{name}")
            if r:
                rows.append({"family": "mechanical", "corner": tag, "cand": name, **r})
        print(f"  mechanical corner {tag:14s} done", flush=True)

    p = P0D / "robustness_0d.csv"
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"\nwrote {p}  ({len(rows)} runs)")

    # conclusion stability: does the footprint direction and the thickness direction hold?
    out = {}
    for tag in sorted({r["corner"] for r in rows}):
        g = {r["cand"]: r for r in rows if r["corner"] == tag}
        if not {"small_fp", "large_fp"} <= set(g):
            continue
        s, l = g["small_fp"], g["large_fp"]
        entry = {
            "loss_favours_large_footprint": bool(l["p_elec_total_w"] < s["p_elec_total_w"]),
            "warpage_favours_small_footprint": bool(s["die_warpage_pv_um"] < l["die_warpage_pv_um"]),
            "d_loss_W": l["p_elec_total_w"] - s["p_elec_total_w"],
            "d_warp_um": l["die_warpage_pv_um"] - s["die_warpage_pv_um"],
            "tradeoff_rate_W_per_um": (s["p_elec_total_w"] - l["p_elec_total_w"]) /
                                      max(l["die_warpage_pv_um"] - s["die_warpage_pv_um"], 1e-9),
        }
        if {"et_best", "etm_alt"} <= set(g):
            e, a = g["et_best"], g["etm_alt"]
            entry["reversal_pair"] = {
                "et_best_P_W": e["p_elec_total_w"], "et_best_warp_um": e["die_warpage_pv_um"],
                "etm_alt_P_W": a["p_elec_total_w"], "etm_alt_warp_um": a["die_warpage_pv_um"],
                "et_best_still_lower_loss": bool(e["p_elec_total_w"] < a["p_elec_total_w"]),
                "etm_alt_still_lower_warp": bool(a["die_warpage_pv_um"] < e["die_warpage_pv_um"]),
                "switch_lambda_W_per_um": (a["p_elec_total_w"] - e["p_elec_total_w"]) /
                                          max(e["die_warpage_pv_um"] - a["die_warpage_pv_um"], 1e-9),
            }
        out[tag] = entry
    (P0D / "robustness_0d_summary.json").write_text(json.dumps(out, indent=2))
    print(f"\n{'corner':16s}{'loss favours LARGE':>22s}{'warp favours SMALL':>22s}"
          f"{'dLoss W':>10s}{'dWarp um':>11s}{'W per um':>11s}")
    for k, v in out.items():
        print(f"{k:16s}{str(v['loss_favours_large_footprint']):>22s}"
              f"{str(v['warpage_favours_small_footprint']):>22s}"
              f"{v['d_loss_W']:10.3f}{v['d_warp_um']:11.3f}{v['tradeoff_rate_W_per_um']:11.4f}")


if __name__ == "__main__":
    # small_fp / large_fp isolate the HVR-FOOTPRINT lever (same N, placement, h_sub).
    # et_best / etm_alt are the actual ET optimum and the ETM alternative it trades against.
    main({"small_fp": (4, 4.0, 0.500, "distributed"),    # D03,  60.0 mm^2
          "large_fp": (4, 1.5, 0.500, "distributed"),    # D11, 137.3 mm^2
          "et_best":  (6, 1.5, 0.500, "distributed"),    # D23, ET optimum
          "etm_alt":  (4, 2.0, 0.500, "edge")})          # D28, ETM alternative
