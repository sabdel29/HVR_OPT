#!/usr/bin/env python3
"""Phase-0M-R3B Section 5 --- 3-D DC extraction of one physical via chain.

The analytical model is R = rho*L/A per segment in series. The real path is not a straight
bar: current spreads into a capture pad at each level and re-converges into the next via,
so the analytical series value is a LOWER bound. This solves the actual geometry.

One representative column of the ls_to_L chain is modelled: microvia - pad - microvia -
pad - microvia, across the three build-up layers, with the dielectric explicitly present.
Solver is the framework's own conservative finite-volume DC conduction code; current
conservation is checked on every solve and a uniform-bar case is run first as a control.
"""
from __future__ import annotations
import csv, math, sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0m"))
from conduction3d import FVConduction, refined                           # noqa: E402

OUT = R / "results" / "phase0mr3b"
RHO_85 = 1.72e-8 * (1 + 0.00393 * (85.0 - 20.0))
SIG_CU = 1.0 / RHO_85
SIG_DIE = 1e-14                          # build-up dielectric
T_LINER_UM = 0.5
LAYERS = [("RDL above gan_ls", 10.0), ("flying-capacitor layer", 100.0),
          ("RDL below inductor", 10.0)]


def grid_1d(lo, hi, hmax):
    n = max(2, int(math.ceil((hi - lo) / hmax)))
    return np.linspace(lo, hi, n + 1)


def build(d_um: float, pad_um: float, nxy: int, nz_scale: float):
    """One via column with a capture pad between each pair of levels."""
    half = pad_um / 2.0 * 1e-6 * 1.6            # lateral domain: pad plus surround
    xs = np.linspace(-half, half, nxy + 1)
    ys = np.linspace(-half, half, nxy + 1)
    zs, zcur, marks = [], 0.0, []
    t_pad_um = 10.0                              # capture pad = one RDL copper thickness
    for i, (_, t) in enumerate(LAYERS):
        zs.append(grid_1d(zcur * 1e-6, (zcur + t) * 1e-6, max(2.0, t / nz_scale) * 1e-6))
        marks.append(("via", zcur, zcur + t)); zcur += t
        if i < len(LAYERS) - 1:
            zs.append(grid_1d(zcur * 1e-6, (zcur + t_pad_um) * 1e-6, 2e-6))
            marks.append(("pad", zcur, zcur + t_pad_um)); zcur += t_pad_um
    zn = np.unique(np.concatenate(zs))
    fv = FVConduction(xs, ys, zn)
    r_via = (d_um / 2.0 - T_LINER_UM) * 1e-6
    r_pad = pad_um / 2.0 * 1e-6

    def sigma(X, Y, Z):
        s = np.full(X.shape, SIG_DIE)
        rr = np.sqrt(X ** 2 + Y ** 2)
        for kind, z0, z1 in marks:
            sel = (Z >= z0 * 1e-6) & (Z <= z1 * 1e-6)
            rad = r_via if kind == "via" else r_pad
            s = np.where(sel & (rr <= rad), SIG_CU, s)
        return s

    fv.assign(sigma)
    return fv, zcur


def run(d_um: float, pad_um: float, i_a: float, nxy: int, nz_scale: float):
    fv, ztot = build(d_um, pad_um, nxy, nz_scale)
    rr = np.sqrt(fv.xc[:, None, None] ** 2 + fv.yc[None, :, None] ** 2)
    r_via = (d_um / 2.0 - T_LINER_UM) * 1e-6
    top = np.zeros((fv.nx, fv.ny, fv.nz), bool)
    bot = np.zeros_like(top)
    top[:, :, -1] = (rr[:, :, 0] <= r_via)
    bot[:, :, 0] = (rr[:, :, 0] <= r_via)
    fv.solve(top, i_a, bot, axis_in=2, axis_gnd=2)
    return fv, ztot


def analytical(d_um: float) -> float:
    a = math.pi * ((d_um / 2.0 - T_LINER_UM) * 1e-6) ** 2
    return sum(RHO_85 * (t * 1e-6) / a for _, t in LAYERS)


def main() -> int:
    # control: a uniform copper bar must return rho*L/A
    xs = np.linspace(-25e-6, 25e-6, 9); ys = xs.copy()
    zs = np.linspace(0, 120e-6, 25)
    bar = FVConduction(xs, ys, zs)
    bar.assign(lambda X, Y, Z: np.full(X.shape, SIG_CU))
    t = np.zeros((bar.nx, bar.ny, bar.nz), bool); b = np.zeros_like(t)
    t[:, :, -1] = True; b[:, :, 0] = True
    bar.solve(t, 1.0, b, axis_in=2, axis_gnd=2)
    r_exact = RHO_85 * 120e-6 / (50e-6 * 50e-6)
    err_bar = 100 * (bar.resistance() - r_exact) / r_exact
    print(f"control uniform bar: FV {bar.resistance():.6e}  exact {r_exact:.6e}  "
          f"err {err_bar:+.3f} %")

    rows = [{"case": "control_uniform_bar", "d_um": "", "pad_um": "", "nxy": 8,
             "R_analytical_ohm": r_exact, "R_fv_ohm": bar.resistance(),
             "error_pct": round(err_bar, 4), "current_error_pct": "",
             "note": "rho*L/A on a plain copper bar"}]

    I = 20.408163265306122 / 19.0     # one column of the 19-column sourced-pitch field
    for d_um, pad_um in ((120.0, 180.0), (70.0, 110.0)):
        prev = None
        for nxy, nzs in ((16, 4.0), (24, 3.0), (32, 2.5), (48, 2.0), (64, 1.5)):
            fv, _ = run(d_um, pad_um, I, nxy, nzs)
            r_fv = fv.resistance()
            r_an = analytical(d_um)
            ce = 100 * abs(fv.current_out() - fv.current_in()) / max(I, 1e-30)
            print(f"d {d_um:5.1f} pad {pad_um:5.1f} nxy {nxy:3d}: "
                  f"R_analytical {r_an:.4e}  R_3D {r_fv:.4e}  "
                  f"ratio {r_fv/r_an:6.3f}  dI {ce:.2e} %")
            rows.append({"case": f"via_chain_d{d_um:.0f}_pad{pad_um:.0f}",
                         "d_um": d_um, "pad_um": pad_um, "nxy": nxy,
                         "R_analytical_ohm": r_an, "R_fv_ohm": r_fv,
                         "error_pct": round(100 * (r_fv - r_an) / r_an, 3),
                         "current_error_pct": f"{ce:.3e}",
                         "note": "microvia-pad-microvia-pad-microvia across 120 um"})
            prev = r_fv
    p = OUT / "substrate_via_dc_validation.csv"
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    # convergence: the two finest meshes must agree, or the ratio is a mesh artifact
    for case in sorted({r["case"] for r in rows if r["case"] != "control_uniform_bar"}):
        g = [r for r in rows if r["case"] == case]
        f1, f2 = g[-2], g[-1]
        drift = 100 * abs(f2["R_fv_ohm"] - f1["R_fv_ohm"]) / f2["R_fv_ohm"]
        print(f"{case}: finest two meshes differ by {drift:.2f} %  -> "
              f"R_3D / R_analytical = {f2['R_fv_ohm']/f2['R_analytical_ohm']:.4f}"
              f"{'' if drift < 1.0 else '   NOT CONVERGED'}")
    print(f"\nwrote {p.relative_to(R)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
