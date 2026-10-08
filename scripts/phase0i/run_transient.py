#!/usr/bin/env python3
"""Phase-0I Sec.7 -- transient thermal validation.

Two things must be shown:
  1. the transient converges to the SAME steady state the validated steady solver gives, so
     the added rho*cp has not changed the physics, only the path;
  2. the package thermal time constant, which is what justifies (or refuses) a dwell length.
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
for p in ("phase0i", "phase0h", "phase0g", "phase0f", "phase0b"):
    sys.path.insert(0, str(R / "scripts" / p))
import board as BRD, kw1                                             # noqa: E402
from etm import ccxio, metrics                                       # noqa: E402
from etm.config import build_materials, load_doe, load_stack         # noqa: E402
from etm.mesh import build                                           # noqa: E402
from etm.placement import Tile                                       # noqa: E402
from transient import make_transient, read_history, run, time_constant   # noqa: E402
from zglobal import stack_for                                        # noqa: E402

WD = R / "results" / "phase0i" / "trans"
WD.mkdir(parents=True, exist_ok=True)


def main():
    import math
    h_top = json.loads((R / "results/phase0f/cooling_1kw_calibration.json").read_text())["h_top_W_m2K"]
    doe = load_doe()
    arch, h_sub, p_conv, p_die = "ARCH_Z1_EMBEDDED", 1.30, 125.3, 1000.0
    st, extra, _ = stack_for(arch, h_sub)
    side = math.sqrt(274.89 / 49)
    xy = kw1.tiles_for("uniform", side, st, doe, 49)
    tiles = [Tile(cx, cy, side, side, p_conv / 49) for cx, cy in xy]
    m = build(tiles, st, h_sub, h_xy=0.95, z_scale=1.4, support_layer=False,
              extra_bottom_layers=extra)
    mats = build_materials(st)
    print(f"mesh: {len(m.elems)} elements")

    ss = WD / "ss.inp"
    films = ccxio.write_thermal(m, mats, tiles, st, p_die, h_top, ss)
    ccxio.run_ccx(ss, threads=8)
    Tn = ccxio.read_frd(WD / "ss.frd")["NDTEMP"]
    tm = metrics.thermal_metrics(m, Tn, films, st, p_die + p_conv, h_top)
    Tss = tm["T_max_C"]
    print(f"steady state (validated solver): T_max = {Tss:.4f} C, "
          f"energy residual {tm.get('energy_residual_pct', float('nan')):.2e} %")

    out = {"steady_T_max_C": Tss, "runs": []}
    for t_end, dt0 in ((60.0, 1e-3), (900.0, 1e-2), (6000.0, 1e-2)):
        tr = make_transient(ss, WD / f"tr{t_end:g}.inp", t_end=t_end, dt0=dt0, t_init=25.0)
        t0 = time.time()
        run(tr)
        frd = WD / f"tr{t_end:g}.frd"
        if not frd.is_file():
            print(f"  t_end={t_end}s FAILED"); continue
        hist = read_history(frd)
        tc = time_constant(hist)
        err = 100 * (hist[-1][1] - Tss) / Tss if hist else float("nan")
        print(f"  t_end={t_end:5.1f} s: {len(hist):3d} output times, "
              f"T_max(end) = {hist[-1][1]:8.4f} C ({err:+.3f} % vs steady), "
              f"tau = {tc['tau_s']:.4g} s, t95 = {tc['t_95_s']:.4g} s "
              f"({time.time()-t0:.0f} s wall)", flush=True)
        out["runs"].append({"t_end_s": t_end, "dt0_s": dt0, "n_times": len(hist),
                            "T_end_C": hist[-1][1], "err_vs_steady_pct": err, **tc,
                            "history": [[float(a), float(b)] for a, b, _ in hist]})
    (R / "results/phase0i/transient_thermal.json").write_text(json.dumps(out, indent=2))
    print(f"\nwrote results/phase0i/transient_thermal.json")


if __name__ == "__main__":
    main()
