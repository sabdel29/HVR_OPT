#!/usr/bin/env python3
"""Phase-0G Sec.3: is the ARCH_B interior optimum robust, or an artifact of one parameter set?

The curve is P_total(h) = g(h) + P_TSV(h). Near the minimum

    dP_TSV/dh  ~  +115 mW/mm        (grows linearly with substrate thickness)
    dg/dh      ~  -100 mW/mm        (converter loss falling as the package cools)

They nearly cancel, which is exactly why the minimum sits where it does and why it is only
0.36 mW deep between 0.90 and 1.00 mm. Anything that scales P_TSV therefore moves or removes
the minimum.

Corners that change ONLY P_TSV are evaluated exactly by recomputing the via term on the
tightly converged g(h) -- P_TSV is at most 147 mW of a 1125 W heat load, so the thermal
feedback of changing it is under 0.01 K. Corners that change g(h) itself need a full ET
re-run and are marked as such.
"""
from __future__ import annotations
import csv, json, math, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for p in ("phase0dr", "phase0e", "phase0f", "phase0g"):
    sys.path.insert(0, str(R / "scripts" / p))
import kw1
import ppdn as P0
from stack import allocate, load_cfg, r_field
from geometry import cell_stack

OUT = R / "results" / "phase0g"
TIERS = P0.load_paths()["tiers"]
TSV = TIERS["tsv"]
A_VIA = P0.tier_area_m2(TSV)
PITCH = P0._v(TSV["pitch_m"])
CD = load_cfg()["current_density"]["cu"]
J_JUNE, J_ECTC = CD["june2026"]["value"], CD["ectc2024"]["value"]

I_OUT_VR = kw1.P_LOAD_W / kw1.M_VR
TILE_SIDE_MM = 2.369
T_CELL_MM = 0.720
CROWD_NOM, CROWD_LO, CROWD_HI = 1.326, 1.0, 1.96


def p_tsv(h_sub, T_c, j_cu=J_JUNE, crowd=CROWD_NOM, policy="A_min_capability",
          rho_scale=1.0):
    """LV-rail via-field loss for the whole 1-kW system, at one substrate thickness."""
    al = allocate("tsv", I_OUT_VR, A_VIA, PITCH, (TILE_SIDE_MM * 1e-3) ** 2, j_cu,
                  policy=policy, strict=False)
    h_m = (h_sub - T_CELL_MM) * 1e-3
    rs = P0.r_single(TSV, T_c, h_m) * crowd * rho_scale
    return I_OUT_VR ** 2 * 2.0 * r_field(rs, al) * kw1.M_VR


def main():
    base = list(csv.DictReader(open(OUT / "crossover_hires_ARCH_B_tight.csv")))
    hs = [float(r["h_sub_mm"]) for r in base]
    g = {float(r["h_sub_mm"]): float(r["P_elec_total_w"]) - float(r["P_tsv_w"]) for r in base}
    T = {float(r["h_sub_mm"]): float(r["T_max_C"]) for r in base}

    CORNERS = [
        ("nominal", dict()),
        ("J_ectc_4e8", dict(j_cu=J_ECTC)),
        ("crowding_1.00", dict(crowd=CROWD_LO)),
        ("crowding_1.96", dict(crowd=CROWD_HI)),
        ("policy_B_geometric", dict(policy="B_geometric")),
        ("policy_C_area_optimal", dict(policy="C_area_optimal")),
        ("rho_cu_+10pct", dict(rho_scale=1.10)),
        ("rho_cu_-10pct", dict(rho_scale=0.90)),
        ("J_ectc_x_crowd_1.96", dict(j_cu=J_ECTC, crowd=CROWD_HI)),
    ]
    rows, summary = [], []
    print(f"{'corner':24s} {'h_opt':>6s} {'interior?':>10s} "
          + " ".join(f"{'P('+f'{h:.2f}'+')':>10s}" for h in (0.8, 1.0, 1.2, 1.5, 2.0)))
    for name, kw in CORNERS:
        curve = []
        for h in hs:
            pt = p_tsv(h, T[h], **kw)
            curve.append((h, g[h] + pt, pt))
            rows.append({"corner": name, "h_sub_mm": h, "P_total_w": g[h] + pt,
                         "P_tsv_w": pt, "g_h_w": g[h], "T_max_C": T[h],
                         "kind": "exact_tsv_recompute", **{k: str(v) for k, v in kw.items()}})
        i = min(range(len(curve)), key=lambda k: curve[k][1])
        h_opt = curve[i][0]
        interior = 0 < i < len(curve) - 1
        vals = {h: v for h, v, _ in curve}
        summary.append({"corner": name, "h_opt_mm": h_opt, "interior": interior,
                        "P_at_h_opt_w": curve[i][1],
                        **{f"P_{h:.2f}mm_w": vals[h] for h in (0.8, 1.0, 1.2, 1.5, 2.0)},
                        "depth_vs_0.80_mW": 1e3 * (vals[0.8] - curve[i][1]),
                        "depth_vs_2.00_mW": 1e3 * (vals[2.0] - curve[i][1])})
        print(f"{name:24s} {h_opt:6.2f} {str(interior):>10s} "
              + " ".join(f"{vals[h]:10.4f}" for h in (0.8, 1.0, 1.2, 1.5, 2.0)))

    with open(OUT / "electrical_crossover_robustness.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for r in rows for k in r}))
        w.writeheader(); w.writerows(rows)
    with open(OUT / "electrical_crossover_summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0])); w.writeheader(); w.writerows(summary)

    print("\n=== classification ===")
    hopts = sorted({s["h_opt_mm"] for s in summary})
    n_int = sum(1 for s in summary if s["interior"])
    depths = [s["depth_vs_0.80_mW"] for s in summary if s["interior"]]
    print(f"  interior optimum in {n_int} of {len(summary)} corners")
    print(f"  h_opt spans {min(hopts):.2f} - {max(hopts):.2f} mm")
    if depths:
        print(f"  depth below the thinnest point: {min(depths):.2f} - {max(depths):.2f} mW")
    print(f"\nwrote {OUT/'electrical_crossover_robustness.csv'}")


if __name__ == "__main__":
    main()
