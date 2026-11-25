#!/usr/bin/env python3
"""Si-IF backside VR study -- sensitivity of the headline numbers.

Compares, for 48 V and 12 V (power mode, square cell, 100-um keep-out), the baseline sweep with
the sensitivity sweeps of run_all.sh (core loss x0.5 and x2, typical DCR, minimum on-time 20 ns,
engine gates only, 20 %-drop saturation current): maximum current density and the efficiency
there, maximum efficiency, and the best efficiency at 0.5 and 1 A/mm^2. Writes sensitivity.json.
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
VARIANTS = [("baseline", ""), ("core x0.5", "_core05"), ("core x2", "_core2"),
            ("typical DCR", "_dcrtyp"), ("t_on >= 20 ns", "_ton20"),
            ("engine gates only", "_enggates"), ("I_sat at 20 % drop", "_isat20")]


def open_text(path):
    """Open a result file, or its gzip copy (path + ".gz") when only that is present."""
    import gzip
    if os.path.isfile(path):
        return open(path)
    return gzip.open(path + ".gz", "rt")


def headline(path, mode="power", ko=100.0):
    if not (os.path.isfile(path) or os.path.isfile(path + ".gz")):
        return None
    d = json.load(open_text(path))
    grid = [r for r in d["best"] if r["mode"] == mode and r["keepout_um"] == ko]
    jm = [r for r in d["jmax"] if r["mode"] == mode and r["keepout_um"] == ko]
    if not grid or not jm:
        return None
    jbest = max(r["J_target"] for r in jm)
    top = min((r for r in jm if r["J_target"] >= jbest * (1 - 1e-6)),
              key=lambda r: r["loss_total_W"])
    eff = min(grid, key=lambda r: r["loss_total_W"])

    def at(J):
        g = [r for r in grid if abs(r["J_target"] - J) < 1e-9]
        return round(100 * g[0]["efficiency"], 2) if g else None
    return {"J_max": round(jbest, 3), "eff_at_J_max_pct": round(100 * top["efficiency"], 2),
            "design_at_J_max": f"{top['topology']} M={top['M']} {top['inductor']} "
                               f"{top['f_sw_Hz'] / 1e6:.2f} MHz",
            "eff_max_pct": round(100 * eff["efficiency"], 2),
            "J_achieved_at_eff_max": round(eff["J_achieved"], 3),
            "eff_at_0p5_pct": at(0.5), "eff_at_1p0_pct": at(1.0)}


def main():
    out = {}
    for v in ("48", "12"):
        out[f"{v}V"] = {}
        for name, suf in VARIANTS:
            h = headline(os.path.join(HERE, f"sweep_v{v}{suf}_best.json"))
            if h:
                out[f"{v}V"][name] = h
    json.dump(out, open(os.path.join(HERE, "sensitivity.json"), "w"), indent=1)
    for v, rows in out.items():
        for name, h in rows.items():
            print(f"{v} {name:20s} Jmax={h['J_max']:.3f} (eta {h['eff_at_J_max_pct']}%)  "
                  f"eta_max={h['eff_max_pct']}% @J_ach {h['J_achieved_at_eff_max']}  "
                  f"eta(0.5)={h['eff_at_0p5_pct']}  eta(1.0)={h['eff_at_1p0_pct']}")


if __name__ == "__main__":
    main()
