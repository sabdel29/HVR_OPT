#!/usr/bin/env python3
"""Phase-0D: add exactly one controlled mechanical case to close the thickness x asymmetry
interaction that the frozen C01-C20 DOE could not isolate.

C07_THICK == C07 in every respect except h_sub = 500 um. The frozen DOE is NOT renumbered;
the case is defined here as an addendum and run through the unmodified Phase-0C flow.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase0b"))
from etm.config import load_doe, load_stack          # noqa: E402
from etm.run_case import run_case                    # noqa: E402

R = Path(__file__).resolve().parents[2]
P0B, P0C, OUT = R / "results" / "phase0b", R / "results" / "phase0c", R / "results" / "phase0d"

C07_THICK = {"n_vr": 4, "placement": "asymmetric_left", "tile_ax": 4.8990,
             "tile_ay": 4.8990, "h_sub": 0.500, "p_hvr_total_w": 42.0,
             "question": "thickness x asymmetry interaction closure (Phase-0D addendum)"}


def main():
    stack, doe = load_stack(), load_doe()
    doe = json.loads(json.dumps(doe))
    doe["cases"]["C07_THICK"] = C07_THICK              # addendum only, in-memory
    h_top = json.loads((P0B / "cooling_calibration.json").read_text())["h_top_W_m2K"]

    r = run_case("C07_THICK", stack, doe, OUT / "C07_THICK", h_top=h_top, bc="BC_A",
                 threads=32, solver="", h_xy=0.32, z_scale=1.4)

    prev = {x["case"]: x for x in
            __import__("csv").DictReader((P0C / "full_doe_results.csv").open())}
    w = {c: float(prev[c]["die_warpage_pv_um"]) for c in ("C05", "C07", "C08")}
    t = {c: float(prev[c]["T_max_C"]) for c in ("C05", "C07", "C08")}
    w["C07_THICK"] = r["structural"]["die_warpage_pv_um"]
    t["C07_THICK"] = r["thermal"]["T_max_C"]

    eff_dist = 100 * (w["C08"] - w["C05"]) / w["C05"]          # distributed placement
    eff_asym = 100 * (w["C07_THICK"] - w["C07"]) / w["C07"]    # asymmetric placement
    residual = eff_asym - eff_dist

    out = {
        "case": "C07_THICK", "definition": C07_THICK,
        "die_warpage_pv_um": w["C07_THICK"], "T_max_C": t["C07_THICK"],
        "pkg_warpage_pv_um": r["structural"]["pkg_warpage_pv_um"],
        "si_principal_p99_MPa": r["structural"]["si_principal_MPa"]["p99"],
        "energy_residual_pct": r["thermal"]["energy_residual_pct"],
        "n_elems": r["mesh"]["n_elems"],
        "thickness_effect_distributed_pct": eff_dist,
        "thickness_effect_asymmetric_pct": eff_asym,
        "interaction_residual_pp": residual,
        "separable": bool(abs(residual) < 3.0),
        "warpages_um": w, "T_max_C_all": t,
    }
    (OUT / "c07_thick_result.json").write_text(json.dumps(out, indent=2))

    print(f"  C07_THICK: die warpage {w['C07_THICK']:.4f} um, T_max {t['C07_THICK']:.3f} C, "
          f"E-balance {r['thermal']['energy_residual_pct']:+.4f}%")
    print(f"\n  thickness effect, distributed  (C05 -> C08)        : {eff_dist:+.2f} %")
    print(f"  thickness effect, asymmetric   (C07 -> C07_THICK)  : {eff_asym:+.2f} %")
    print(f"  interaction residual                               : {residual:+.2f} pp")
    print(f"  separable (|residual| < 3 pp)                      : {out['separable']}")
    print(f"\n  warpage table: " + "  ".join(f"{k}={v:.4f}" for k, v in w.items()))


if __name__ == "__main__":
    main()
