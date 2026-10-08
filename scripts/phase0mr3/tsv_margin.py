#!/usr/bin/env python3
"""Phase-0M-R3 Section 7 --- TSV process margin, not just AR <= 10.000.

Phase 0M-R2 found ARCH_Z2, Z4 and Z5 at AR = 10.000 exactly. That passes the hard rule
and has M_AR = AR_max / AR = 1.000, which is no margin at all. The two questions are
separated here, and a bounded tolerance sweep asks whether the 30 um via survives even
modest variation.

No distribution is invented. No source in this repository gives a TSV fabrication
tolerance, so the sweep is a clearly-labelled PARAMETRIC BOUND, not a statistical model.
"""
from __future__ import annotations
import csv, sys
from pathlib import Path
import yaml

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0mr3", "scripts/phase0mr2", "scripts/phase0mr", "scripts/phase0m",
          "scripts"):
    sys.path.insert(0, str(R / p))

import arch_geometry as AG                                              # noqa: E402
from interconnect import TSVGeometry                                    # noqa: E402
import tsv_production as TP                                             # noqa: E402

OUT = R / "results" / "phase0mr3"
DS = yaml.safe_load((R / "configs/phase0m/interconnect_design_space.yaml").read_text())
AR_MAX = 10.0
R_LO = DS["design_variables"]["tsv"]["radius_m"]["lo"] * 1e6
R_HI = DS["design_variables"]["tsv"]["radius_m"]["hi"] * 1e6
S_MIN = DS["process_limits"]["tsv"]["spacing_min_m"]["value"] * 1e6

# PARAMETRIC BOUND, not a sourced tolerance and not a distribution.
TOL = [("none", 0.0, 0.0, 0.0),
       ("modest", 0.02, 0.10, 0.02),
       ("loose", 0.05, 0.20, 0.05)]


def evaluate(arch: str, d_um: float, tol_d: float, tol_lin: float, tol_h: float) -> dict:
    """Worst-corner AR: smallest diameter with the deepest via."""
    sp = AG.span(arch)
    L = sp.length_um * (1.0 + tol_h)
    d = d_um * (1.0 - tol_d)
    ar = L / d
    pitch = max(d + S_MIN, d)
    g = TSVGeometry(r_m=d_um / 2 * 1e-6, h_m=sp.length_um * 1e-6, p_m=pitch * 1e-6,
                    t_liner_m=0.5e-6 * (1.0 + tol_lin))
    try:
        e = TP.evaluate(g, 1000.0 if sp.rail == "LV" else 1000.0 / 0.889 / 48.0, TP.BUDGET)
        ok = True
    except Exception:                                                   # noqa: BLE001
        e, ok = {}, False
    return {"arch": arch, "d_nominal_um": d_um, "tol_d_frac": tol_d,
            "tol_liner_frac": tol_lin, "tol_depth_frac": tol_h,
            "L_worst_um": L, "d_worst_um": d, "pitch_um": pitch,
            # AR at THIS diameter, not the contract's reference diameter. Reading
            # sp.aspect_ratio here reported 10.000 for every swept diameter.
            "AR_nominal": sp.length_um / d_um, "AR_worst": ar, "AR_max": AR_MAX,
            "AR_at_reference_d": sp.aspect_ratio,
            "M_AR_nominal": AR_MAX / (sp.length_um / d_um), "M_AR_worst": AR_MAX / ar,
            "feasible_worst": ar <= AR_MAX,
            "in_sourced_radius_range": R_LO <= d_um / 2 <= R_HI,
            "n_required": e.get("n_required"), "n_available": e.get("n_available"),
            "phi_cu": e.get("phi_cu"), "R_field_mohm": e.get("R_field_mohm"),
            "k_z": e.get("k_z"), "k_xy": e.get("k_xy"),
            "E_xy_MPa": e.get("E_xy_MPa"), "CTE_eff": e.get("CTE_eff"),
            "evaluated": ok}


def main() -> int:
    rows = []
    for arch in ("ARCH_Z1_EMBEDDED", "ARCH_Z2_BACKSIDE", "ARCH_Z4_POWER_DIE"):
        for d in (30.0, 34.0, 40.0, 50.0, 60.0):
            for name, td, tl, th in TOL:
                r = evaluate(arch, d, td, tl, th)
                r["tolerance_case"] = name
                rows.append(r)
    with open(OUT / "tsv_margin_sweep.csv", "w", newline="") as fh:
        k = sorted({x for r in rows for x in r})
        w = csv.DictWriter(fh, fieldnames=k); w.writeheader(); w.writerows(rows)

    print("  hard rule AR <= 10 vs DESIGN MARGIN M_AR = AR_max / AR_actual\n")
    print("  %-14s %6s %10s %10s %10s %10s" %
          ("arch", "d_um", "AR_nom", "M_AR_nom", "AR_worst", "M_AR_worst"))
    for arch in ("ARCH_Z1_EMBEDDED", "ARCH_Z2_BACKSIDE"):
        for d in (30.0, 34.0, 40.0):
            n = next(r for r in rows if r["arch"] == arch and r["d_nominal_um"] == d
                     and r["tolerance_case"] == "none")
            m = next(r for r in rows if r["arch"] == arch and r["d_nominal_um"] == d
                     and r["tolerance_case"] == "modest")
            print("  %-14s %6.0f %10.3f %10.3f %10.3f %10.3f  %s" %
                  (arch.replace("ARCH_", ""), d, n["AR_nominal"], n["M_AR_nominal"],
                   m["AR_worst"], m["M_AR_worst"],
                   "OK" if m["feasible_worst"] else "FAILS under modest tolerance"))
    z2 = [r for r in rows if r["arch"] == "ARCH_Z2_BACKSIDE"
          and r["tolerance_case"] == "modest"]
    smallest = min((r for r in z2 if r["feasible_worst"]),
                   key=lambda r: r["d_nominal_um"], default=None)
    print(f"\n  smallest sourced diameter with POSITIVE margin under the modest bound: "
          f"{smallest['d_nominal_um']:.0f} um (M_AR = {smallest['M_AR_worst']:.3f})"
          if smallest else "\n  no sourced diameter keeps margin under the modest bound")
    if smallest:
        base = next(r for r in rows if r["arch"] == "ARCH_Z2_BACKSIDE"
                    and r["d_nominal_um"] == 30.0 and r["tolerance_case"] == "none")
        print("\n  effect of moving Z2 from 30 um to that diameter, at nominal:")
        s2 = next(r for r in rows if r["arch"] == "ARCH_Z2_BACKSIDE"
                  and r["d_nominal_um"] == smallest["d_nominal_um"]
                  and r["tolerance_case"] == "none")
        for k, lab in (("n_required", "vias required"), ("phi_cu", "copper fraction"),
                       ("R_field_mohm", "field resistance mOhm"),
                       ("k_z", "k_z W/mK"), ("E_xy_MPa", "E_xy MPa"),
                       ("CTE_eff", "CTE_eff 1/K")):
            a, b = base.get(k), s2.get(k)
            if isinstance(a, (int, float)) and isinstance(b, (int, float)) and a:
                print(f"    {lab:24s} {a:12.5g} -> {b:12.5g}   ({100*(b-a)/a:+7.2f} %)")
    print(f"\nwrote {OUT/'tsv_margin_sweep.csv'} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
