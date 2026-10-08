#!/usr/bin/env python3
"""Phase-0M Part 26 -- does the cooling ARCHITECTURE change the mechanics?

The incumbent boundary is one Robin coefficient with ONE sink temperature, so the coolant
is implicitly infinite: it cannot warm along the channel. A real microchannel warms by
Q / (m_dot c_p) from inlet to outlet, and that puts an IN-PLANE temperature gradient across
the die -- exactly the quantity warpage responds to.

This runs the SAME global thermal/mechanical model twice, changing only the sink-temperature
field, and measures the change in warpage and in the local solder driver. The sensitivity is
to a physical cooling variable (mass flow), not to h.
"""
from __future__ import annotations
import csv, json, shutil, sys
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parents[2]
for d in ("phase0b", "phase0f"):
    sys.path.insert(0, str(R / "scripts" / d))
sys.path.insert(0, str(R / "scripts" / "phase0m"))
from etm import ccxio, run_case as RC                                      # noqa: E402
from etm.config import load_stack, load_doe                                # noqa: E402
from cooling import CP_F, Q_TOTAL_W                                        # noqa: E402

OUT = R / "results" / "phase0m"
WD = OUT / "etm_cool"
OUT.mkdir(parents=True, exist_ok=True)

H_TOP_1KW = 166000.0
CASE = "C05"
_ORIG = ccxio.write_thermal


def patch_sink_gradient(dt_span_k: float, axis: int = 0):
    """Wrap write_thermal so the top-film SINK temperature varies linearly along `axis`.

    Total heat removed is unchanged -- the mean sink temperature is held at the nominal
    coolant temperature -- so this isolates the GRADIENT from the level.
    """
    def wrapped(m, mats, tiles, stack, p_die, h_top, path):
        info = _ORIG(m, mats, tiles, stack, p_die, h_top, path)
        if dt_span_k == 0.0:
            return info
        t0 = stack["thermal_bc"]["coolant_temp"]["value"]
        cen = m.elem_centroids()
        lo, hi = cen[:, axis].min(), cen[:, axis].max()
        lines, out = path.read_text().splitlines(), []
        for ln in lines:
            p = ln.split(",")
            if len(p) == 4 and p[1].strip() == "F2" and p[0].strip().isdigit():
                e = int(p[0])
                frac = (cen[e - 1, axis] - lo) / max(hi - lo, 1e-30)
                out.append(f"{e},F2,{t0 + dt_span_k * (frac - 0.5):.6f},{p[3]}")
            else:
                out.append(ln)
        path.write_text("\n".join(out) + "\n")
        info["sink_gradient_K"] = dt_span_k
        return info
    return wrapped


def run(dt_span_k: float, tag: str) -> dict:
    stack, doe = load_stack(), load_doe()
    wd = WD / tag
    if wd.exists():
        shutil.rmtree(wd)
    ccxio.write_thermal = patch_sink_gradient(dt_span_k)
    try:
        r = RC.run_case(CASE, stack, doe, wd, h_top=H_TOP_1KW, h_xy=0.9, z_scale=0.6,
                        solver="", threads=8)
    finally:
        ccxio.write_thermal = _ORIG
    st, th = r["structural"], r["thermal"]
    return {"tag": tag, "sink_gradient_K": dt_span_k,
            "T_max_C": th["T_max_C"], "T_min_C": th["T_min_C"],
            "T_mean_C": th["T_mean_C"], "T_span_C": th["T_max_C"] - th["T_min_C"],
            "energy_residual_pct": th["energy_residual_pct"],
            "die_warpage_pv_um": st["die_warpage_pv_um"],
            "pkg_warpage_pv_um": st["pkg_warpage_pv_um"],
            "si_principal_p99_MPa": (st.get("si_principal_MPa") or {}).get("p99"),
            "interface_shear_p99_MPa": (st.get("interface_shear_MPa") or {}).get("p99"),
            "runtime_s": r["runtime_s"], "n_elems": r["mesh"]["n_elems"]}


def main() -> int:
    rows = []
    # mass flows -> streamwise coolant temperature rise over the die
    for m_dot in (0.0, 27.0, 10.0, 5.0):
        dt = 0.0 if m_dot == 0 else Q_TOTAL_W / (m_dot * 1e-3 * CP_F)
        tag = "uniform" if m_dot == 0 else f"mdot{m_dot:g}"
        r = run(dt, tag)
        r["m_dot_g_s"] = m_dot
        rows.append(r)
        print(f"  {tag:10s} dT_sink={dt:7.2f} K  T_max={r['T_max_C']:.3f} C  "
              f"die warpage={r['die_warpage_pv_um']:.4f} um  "
              f"({r['runtime_s']:.0f}s)", flush=True)
    b = rows[0]
    for r in rows:
        r["warpage_vs_uniform_pct"] = (100 * (r["die_warpage_pv_um"]
                                              - b["die_warpage_pv_um"])
                                       / b["die_warpage_pv_um"])
        r["Tmax_vs_uniform_K"] = r["T_max_C"] - b["T_max_C"]
    keys = sorted({k for r in rows for k in r})
    with open(OUT / "cooling_etm_sensitivity.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
    print(f"wrote {OUT/'cooling_etm_sensitivity.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
