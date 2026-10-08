#!/usr/bin/env python3
"""Phase-0I Sec.4/5/19 -- rail-aware electrical sweep of every Z-architecture over its OWN
realizable thickness range.

Phase 0H swept 0.80-2.00 mm and applied one realizability bound to all architectures. That
bound is embedded-specific (DEFECT #33). Here each architecture is swept only where it is
actually buildable, which is a 4.3x wider band for everything except the embedded case.

The converter is also recompiled per architecture: the embedded case must choose an inductor
that FITS the substrate, and the non-embedded cases have no such restriction, so they are not
forced to the same part.
"""
from __future__ import annotations
import csv, json, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for p in ("phase0i", "phase0h", "phase0f", "phase0e", "phase0dr"):
    sys.path.insert(0, str(R / "scripts" / p))

import kw1                                                    # noqa: E402
from electrical import compile_hvr                            # noqa: E402
from geometry import fitting_inductors, inductor_library      # noqa: E402
from zarch import realizable                                  # noqa: E402
from zpower import evaluate_z                                 # noqa: E402

OUT = R / "results" / "phase0i"
ARCHS = ["ARCH_Z1_EMBEDDED", "ARCH_Z2_BACKSIDE", "ARCH_Z4_POWER_DIE", "ARCH_Z5_2P5D_LATERAL"]
HS = [0.30, 0.40, 0.50, 0.60, 0.80, 1.00, 1.20, 1.30, 1.40, 1.50, 1.75, 2.00]
M_VR, J = 49, 3.5


def design_for(arch: str, h_sub_mm: float):
    """Compile the converter with the inductor restriction that this architecture implies."""
    if arch == "ARCH_Z1_EMBEDDED":
        fit, budget = fitting_inductors(h_sub_mm, "nominal")
        if not fit:
            return None, f"no inductor fits the embedded budget ({budget:.0f} um)"
        d = compile_hvr(1000.0 / 1.0 / M_VR, J, inductor_library=fit)
        return d, ("realizable" if d else "no converter from the fitting inductors")
    # the converter is NOT inside the substrate: the whole library is available
    d = compile_hvr(1000.0 / 1.0 / M_VR, J, inductor_library=inductor_library())
    return d, ("realizable" if d else "no converter from the full library")


def main():
    rows = []
    print(f"{'arch':22s} {'h mm':>5s} {'build':>6s} {'inductor':>26s} {'P_conv':>8s} "
          f"{'P_tsv':>9s} {'P_rdl':>10s} {'P_pdn':>10s} {'P_tot':>10s} {'eta %':>7s}")
    for arch in ARCHS:
        for h in HS:
            rz = realizable(arch, h)
            des, why = design_for(arch, h)
            if not rz.feasible or des is None:
                rows.append({"arch": arch, "h_sub_mm": h, "realizable": False,
                             "reason": rz.reason if not rz.feasible else why,
                             "h_sub_min_um": rz.h_sub_min_um})
                print(f"{arch:22s} {h:5.2f} {'no':>6s}   {(rz.reason if not rz.feasible else why)[:60]}")
                continue
            p_conv = des.loss_at(85.0)["p_conv_w"] * M_VR
            try:
                e = evaluate_z(arch, h, p_conv, T_c=85.0,
                               hvr_area_mm2=des.area_mm2 * M_VR)
            except Exception as ex:
                print(f"{arch:22s} {h:5.2f}  EVAL FAILED: {str(ex)[:60]}"); continue
            by = e["P_by_tier_w"]
            rows.append({"arch": arch, "h_sub_mm": h, "realizable": True, "reason": "",
                         "h_sub_min_um": rz.h_sub_min_um,
                         "realizability_rule": rz.rule,
                         "inductor": des.inductor.name, "inductor_h_um": des.inductor.height_um,
                         "hvr_area_mm2": des.area_mm2 * M_VR,
                         "tsv_rail": e["tsv_rail"], "tsv_current_a": e["tsv_current_a"],
                         "n_tsv_req": e["n_tsv_req"], "n_tsv_alloc": e["n_tsv_alloc"],
                         "n_tsv_avail": e["n_tsv_avail"], "tsv_feasible": e["tsv_feasible"],
                         "P_conv_w": p_conv, "P_bga_w": by.get("bga", 0.0),
                         "P_tsv_w": by.get("tsv", 0.0), "P_rdl_w": by.get("rdl", 0.0),
                         "P_microbump_w": by.get("microbump", 0.0),
                         "P_pdn_w": e["P_pdn_w"], "P_elec_total_w": e["P_elec_total_w"],
                         "efficiency_pct": e["efficiency_pct"], "scope": "SYSTEM"})
            print(f"{arch:22s} {h:5.2f} {'yes':>6s} {des.inductor.name[:26]:>26s} "
                  f"{p_conv:8.3f} {by.get('tsv',0):9.4f} {by.get('rdl',0):10.4f} "
                  f"{e['P_pdn_w']:10.4f} {e['P_elec_total_w']:10.3f} {e['efficiency_pct']:7.3f}",
                  flush=True)
    with open(OUT / "z_architecture_electrical.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for r in rows for k in r}))
        w.writeheader(); w.writerows(rows)
    print(f"\nwrote {OUT/'z_architecture_electrical.csv'}  ({len(rows)} rows)")

    print("\n=== best realizable point per architecture ===")
    for arch in ARCHS:
        sel = [r for r in rows if r["arch"] == arch and r.get("realizable")]
        if not sel:
            print(f"  {arch:22s} NO REALIZABLE POINT"); continue
        b = min(sel, key=lambda r: r["P_elec_total_w"])
        print(f"  {arch:22s} h*={b['h_sub_mm']:.2f} mm  P={b['P_elec_total_w']:9.3f} W  "
              f"eta={b['efficiency_pct']:.3f} %  TSV={b['tsv_rail']}@{b['tsv_current_a']:.0f}A")


if __name__ == "__main__":
    main()
