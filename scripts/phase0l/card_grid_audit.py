#!/usr/bin/env python3
"""Phase-0L -- what the *CREEP temperature grid costs.

The solver interpolates A and n LINEARLY between *CREEP card rows and CLAMPS outside them
(Part III, section 7).  solder_model.norton_at() builds those rows on an Arrhenius basis.  The
two therefore agree only AT the rows.  This quantifies the disagreement for the production
card grid and for a proposed finer grid.
"""
from __future__ import annotations
import csv, sys
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0i"))
import solder_model as sm                                                   # noqa: E402

PROD = [-40., 0., 25., 50., 75., 100., 125.]
FINE = [-40., -20., 0., 20., 40., 45., 55., 65., 75., 80., 90., 100., 110.,
        115., 125., 135., 145., 150.]
SIGMAS = (20., 40., 60., 80., 100.)


def solver_An(T, rows):
    Ts = [r[0] for r in rows]
    if T <= Ts[0]:
        return rows[0][1], rows[0][2]
    if T >= Ts[-1]:
        return rows[-1][1], rows[-1][2]
    i = max(j for j, t in enumerate(Ts) if t <= T)
    if Ts[i] == T:
        return rows[i][1], rows[i][2]
    w = (T - Ts[i]) / (Ts[i + 1] - Ts[i])
    return (rows[i][1] + (rows[i + 1][1] - rows[i][1]) * w,
            rows[i][2] + (rows[i + 1][2] - rows[i][2]) * w)


def build(grid):
    return [(T,) + tuple(sm.norton_at(T)[k] for k in ("A", "n")) for T in grid]


def main():
    out, worst = [], {}
    for name, grid in (("production", PROD), ("proposed_fine", FINE)):
        rows = build(grid)
        for T in np.arange(-40., 150.1, 2.5):
            T = float(T)
            As, ns = solver_An(T, rows)
            f = sm.norton_at(T)
            clamped = T < min(grid) or T > max(grid)
            for s in SIGMAS:
                rs, ri = As * s ** ns, f["A"] * s ** f["n"]
                ratio = rs / ri
                out.append({"grid": name, "T_C": T, "sigma_MPa": s,
                            "A_solver": As, "n_solver": ns,
                            "A_intended": f["A"], "n_intended": f["n"],
                            "rate_solver": rs, "rate_intended": ri,
                            "ratio_solver_over_intended": ratio,
                            "clamped": clamped,
                            "inside_creep_data_T": 45.0 <= T <= 150.0})
                k = (name, clamped)
                if abs(np.log(ratio)) > abs(np.log(worst.get(k, (1.0,))[0])):
                    worst[k] = (ratio, T, s)
    p = R / "results" / "phase0l" / "card_temperature_grid_audit.csv"
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)
    print(f"wrote {p}  ({len(out)} rows)\n")
    print(f"{'grid':>14} {'region':>22} {'worst ratio':>12} {'at T':>8} {'at sigma':>9}")
    for (name, clamped), (r, T, s) in sorted(worst.items()):
        print(f"{name:>14} {'CLAMPED (outside rows)' if clamped else 'between rows':>22} "
              f"{r:12.4f} {T:8.1f} {s:9.1f}")
    for name in ("production", "proposed_fine"):
        sub = [o for o in out if o["grid"] == name and not o["clamped"]
               and o["inside_creep_data_T"]]
        rr = [o["ratio_solver_over_intended"] for o in sub]
        print(f"\n  {name}: within 45-150 C and between rows, "
              f"ratio spans {min(rr):.4f} to {max(rr):.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
