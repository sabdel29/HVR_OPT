#!/usr/bin/env python3
"""Phase-0I Sec.16/18/19 -- compare Z-architectures on electrical, thermal, global mechanical
and LOCAL RELIABILITY, at each architecture's own realizable thicknesses.

Flow per (architecture, thickness):
    Sec.4 electrical  ->  converter loss and rail-aware interconnect loss
    Sec.6 global FE   ->  joint temperature and corner-BGA relative displacement
    Sec.13 local FE   ->  cyclic viscoplastic joint response
    Sec.10 metric     ->  volume-averaged inelastic strain increment per stabilised cycle

The thermal excursion is the system's own OFF -> ON -> OFF power cycle: the joint sits at the
25 C ambient when the system is off and at its computed steady temperature when the system is
at full load. That is a physically defined excursion and requires no invented mission profile.
The NUMBER of such cycles a product must survive is unknown and is swept parametrically.
"""
from __future__ import annotations
import csv, json, sys, time
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
for p in ("phase0i", "phase0h", "phase0g", "phase0f", "phase0e", "phase0dr", "phase0b"):
    sys.path.insert(0, str(R / "scripts" / p))
from joint import build_joint, write_inp, run as run_joint, read_dat, cycle_metric  # noqa
from solder_model import inp_material                                                # noqa
from zarch import realizable                                                         # noqa
from zglobal import corner_joint_response                                            # noqa
from zpower import evaluate_z                                                        # noqa
from electrical import compile_hvr                                                   # noqa
from geometry import fitting_inductors, inductor_library                             # noqa

OUT = R / "results" / "phase0i"
WDJ = OUT / "zjoint"
WDJ.mkdir(parents=True, exist_ok=True)
MAT = inp_material("SAC305", [-40., 0., 25., 50., 75., 100., 125.])
CASES = [("ARCH_Z1_EMBEDDED", [1.30, 1.50, 2.00]),
         ("ARCH_Z2_BACKSIDE", [0.30, 0.80, 1.50, 2.00]),
         ("ARCH_Z4_POWER_DIE", [0.30, 0.80, 1.50, 2.00])]
N_CYC, DWELL, T_OFF = 4, 300.0, 25.0
M_VR, J = 49, 3.5


def design_for(arch, h):
    if arch == "ARCH_Z1_EMBEDDED":
        fit, _ = fitting_inductors(h, "nominal")
        return compile_hvr(1000.0 / M_VR, J, inductor_library=fit) if fit else None
    return compile_hvr(1000.0 / M_VR, J, inductor_library=inductor_library())


def joint_damage(tag, du_um, t_hot, standoff_mm=0.3, n_xy=6, n_z=8):
    """Drive the validated local submodel with the global model's du and T."""
    m = build_joint(n_xy, n_z, 1)
    du = du_um / 1000.0
    cyc, ends, t = [], [], 0.0
    for k in range(N_CYC):
        cyc.append((f"c{k}on", t_hot, du, DWELL)); t += DWELL
        cyc.append((f"c{k}off", T_OFF, 0.0, DWELL)); t += DWELL
        ends.append(t)
    p = WDJ / f"{tag}.inp"
    write_inp(m, p, MAT, cyc, cetol=1e-2)
    run_joint(p, threads=4)
    d = WDJ / f"{tag}.dat"
    if not (d.is_file() and d.stat().st_size > 1000):
        return None
    inc, vals = cycle_metric(read_dat(d), [0.0] + ends)
    if not inc or not np.isfinite(inc[-1]) or inc[-1] <= 0:
        return None
    stab = 100 * abs(inc[-1] - inc[-2]) / inc[-2] if len(inc) > 1 and inc[-2] > 0 else float("nan")
    return {"d_eps_in_stab": inc[-1], "n_cycles": len(inc), "stab_change_pct": stab,
            "per_cycle": inc}


def main():
    h_top = json.loads((R / "results/phase0f/cooling_1kw_calibration.json").read_text())["h_top_W_m2K"]
    rows = []
    print(f"{'arch':20s} {'h mm':>5s} {'P_el W':>9s} {'Tjoint C':>9s} {'du um':>7s} "
          f"{'gam %':>7s} {'warp um':>8s} {'d_eps_in':>11s} {'stab %':>7s}")
    for arch, hs in CASES:
        for h in hs:
            if not realizable(arch, h).feasible:
                print(f"{arch:20s} {h:5.2f}  not realizable"); continue
            des = design_for(arch, h)
            if des is None:
                print(f"{arch:20s} {h:5.2f}  no converter"); continue
            p_conv = des.loss_at(85.0)["p_conv_w"] * M_VR
            t0 = time.time()
            try:
                e = evaluate_z(arch, h, p_conv, T_c=85.0, hvr_area_mm2=des.area_mm2 * M_VR)
                g = corner_joint_response(arch, h, p_conv, 1000.0, h_top)
            except Exception as ex:
                print(f"{arch:20s} {h:5.2f}  GLOBAL FAILED: {str(ex)[:56]}"); continue
            j = joint_damage(f"{arch[7:11]}_{h:.2f}".replace(".", "p"),
                             g["du_corner_um"], g["T_joint_C"])
            row = {"arch": arch, "h_sub_mm": h, "P_elec_total_w": e["P_elec_total_w"],
                   "P_conv_w": p_conv, "P_tsv_w": e["P_by_tier_w"].get("tsv", 0.0),
                   "P_rdl_w": e["P_by_tier_w"].get("rdl", 0.0), "P_pdn_w": e["P_pdn_w"],
                   "efficiency_pct": e["efficiency_pct"], "tsv_rail": e["tsv_rail"],
                   "tsv_current_a": e["tsv_current_a"],
                   "conv_placement": g["conv_placement"], "T_max_C": g["T_max_C"],
                   "T_joint_C": g["T_joint_C"], "du_corner_um": g["du_corner_um"],
                   "shear_strain_pct": g["shear_strain_pct"],
                   "die_warpage_pv_um": g["die_warpage_pv_um"],
                   "pkg_warpage_pv_um": g["pkg_warpage_pv_um"],
                   "n_elem_global": g["n_elem"], "scope": "SYSTEM"}
            if j:
                row.update({"d_eps_in_stab": j["d_eps_in_stab"],
                            "cycle_stab_change_pct": j["stab_change_pct"],
                            "n_cycles": j["n_cycles"]})
            rows.append(row)
            print(f"{arch:20s} {h:5.2f} {e['P_elec_total_w']:9.3f} {g['T_joint_C']:9.2f} "
                  f"{g['du_corner_um']:7.3f} {g['shear_strain_pct']:7.3f} "
                  f"{g['die_warpage_pv_um']:8.3f} "
                  f"{(j['d_eps_in_stab'] if j else float('nan')):11.4e} "
                  f"{(j['stab_change_pct'] if j else float('nan')):7.2f}  "
                  f"({time.time()-t0:.0f}s)", flush=True)
    with open(OUT / "z_architecture_comparison.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for r in rows for k in r}))
        w.writeheader(); w.writerows(rows)
    print(f"\nwrote {OUT/'z_architecture_comparison.csv'} ({len(rows)} rows)")

    print("\n=== best point per architecture, by ELECTRICAL loss ===")
    for arch, _ in CASES:
        sel = [r for r in rows if r["arch"] == arch and r.get("d_eps_in_stab")]
        if not sel:
            continue
        b = min(sel, key=lambda r: r["P_elec_total_w"])
        w = min(sel, key=lambda r: r["d_eps_in_stab"])
        print(f"  {arch:20s} P-best h={b['h_sub_mm']:.2f} ({b['P_elec_total_w']:.3f} W, "
              f"d_eps={b['d_eps_in_stab']:.3e}) | damage-best h={w['h_sub_mm']:.2f} "
              f"({w['P_elec_total_w']:.3f} W, d_eps={w['d_eps_in_stab']:.3e})"
              + ("   <-- SAME" if b['h_sub_mm'] == w['h_sub_mm'] else "   <-- OPPOSED"))


if __name__ == "__main__":
    main()
