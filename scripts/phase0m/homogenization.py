#!/usr/bin/env python3
"""Phase-0M Parts 20-22 -- anisotropic thermal homogenization, validated on explicit RVEs.

Three candidate models disagree by up to 80 % on the SAME TSV array, so the question is
settled by explicit-geometry finite volumes on a unit cell rather than by preference:

  VOIGT/REUSS   parallel along z, series in-plane
  MAXWELL       Maxwell-Garnett / Hashin-Shtrikman for cylinders transverse to the flow
  FRAMEWORK     the pre-existing TSV framework's `thermal_conductivity()`, which puts the
                oxide liner IN SERIES with the copper for transverse flow
  RVE           this module: div(k grad T) = 0 on the explicit geometry

THE UNIT CELL IS ITS OWN PERIODIC CELL. For a centred inclusion in a square cell, symmetry
puts zero normal flux on every mid-plane, so adiabatic side walls ARE the periodic boundary
condition and no special treatment is needed. That is checked by refining the cell to 2x2
periods and confirming the same answer.

Predeclared acceptance (Part 21), fixed BEFORE the RVEs were run:
  a homogenized tensor is ACCEPTED if it reproduces the RVE within 10 % on each axis;
  10-25 % is CONDITIONAL and must be reported with the error; >25 % is REJECTED.
"""
from __future__ import annotations
import csv, json, math, sys
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0m"))
from conduction3d import FVConduction, refined, snapped                    # noqa: E402
import tsv_framework as TF                                                 # noqa: E402

OUT = R / "results" / "phase0m"
OUT.mkdir(parents=True, exist_ok=True)

ACCEPT_PCT = 10.0
CONDITIONAL_PCT = 25.0

K_CU, K_SIO2, K_SI = 385.0, 1.4, 130.0
K_SOLDER, K_UNDERFILL = 57.0, 0.6
K_ORG = 0.35
RCP_CU, RCP_SIO2, RCP_SI = 8933 * 385.0, 2220 * 745.0, 2330 * 712.0


def _k_eff(cell_fn, xn, yn, zn, axis: int) -> dict:
    """Effective conductivity along `axis` from a two-terminal conduction solve."""
    m = FVConduction(xn, yn, zn)
    m.assign(cell_fn)
    X, Y, Z = np.meshgrid(m.xc, m.yc, m.zc, indexing="ij")
    C = (X, Y, Z)[axis]
    c = (m.xc, m.yc, m.zc)[axis]
    inj = C <= c[0] + 1e-18
    gnd = C >= c[-1] - 1e-18
    m.solve(inj, 1.0, gnd, axis_in=axis, axis_gnd=axis, active_tol=1e-12)
    n = (m.xn, m.yn, m.zn)[axis]
    L = n[-1] - n[0]
    side = [(m.xn[-1] - m.xn[0]), (m.yn[-1] - m.yn[0]), (m.zn[-1] - m.zn[0])]
    A = math.prod(s for i, s in enumerate(side) if i != axis)
    r_th = m.resistance()
    return {"k_eff": L / (A * r_th), "R_th": r_th, "balance_err": abs(m.current_out() - 1),
            "n_cells": m.n}


def tsv_cell(r_cu, t_ox, pitch, height, nper=1, nfine=14):
    """One (or nper x nper) TSV unit cell: Cu core, oxide annulus, silicon matrix."""
    r_out = r_cu + t_ox
    span = pitch * nper
    h = min(r_cu / nfine, pitch / (3 * nfine))
    centres = [(-span / 2 + (i + 0.5) * pitch, -span / 2 + (j + 0.5) * pitch)
               for i in range(nper) for j in range(nper)]
    man = sorted({c + d for c, _ in centres for d in (-r_out, -r_cu, 0, r_cu, r_out)}
                 | {c + d for _, c in centres for d in (-r_out, -r_cu, 0, r_cu, r_out)})
    xn = snapped(refined(-span / 2, span / 2, h, -span / 2, span / 2), man, h)
    yn = xn.copy()
    zn = np.linspace(0, height, max(int(height / (pitch / 4)), 4) + 1)

    def fn(X, Y, Z):
        k = np.full(X.shape, K_SI)
        for cx, cy in centres:
            rr = (X - cx) ** 2 + (Y - cy) ** 2
            k[rr <= r_out ** 2] = K_SIO2
            k[rr <= r_cu ** 2] = K_CU
        return k
    f_cu = len(centres) * math.pi * r_cu ** 2 / span ** 2
    f_ox = len(centres) * math.pi * (r_out ** 2 - r_cu ** 2) / span ** 2
    return fn, xn, yn, zn, f_cu, f_ox


def bump_cell(r_bump, pitch, height, k_bump=K_SOLDER, k_fill=K_UNDERFILL, nfine=12):
    """A solder bump in underfill: no liner, a much larger conductivity contrast."""
    span = pitch
    h = min(r_bump / nfine, pitch / (3 * nfine))
    man = [-r_bump, 0.0, r_bump]
    xn = snapped(refined(-span / 2, span / 2, h, -span / 2, span / 2), man, h)
    yn = xn.copy()
    zn = np.linspace(0, height, max(int(height / (pitch / 5)), 4) + 1)

    def fn(X, Y, Z):
        k = np.full(X.shape, k_fill)
        k[X ** 2 + Y ** 2 <= r_bump ** 2] = k_bump
        return k
    return fn, xn, yn, zn, math.pi * r_bump ** 2 / span ** 2, 0.0


def rdl_cell(t_cu, w, s, k_diel=K_ORG, nfine=10):
    """An RDL layer: parallel Cu lines of width w on pitch w+s in a dielectric.

    This layer is anisotropic in ALL THREE axes -- along the lines, across them, and
    through the stack -- and the current framework uses one isotropic value for it.
    """
    p = w + s
    h = min(w / nfine, s / max(nfine // 2, 2))
    span = p
    man = [-w / 2, 0.0, w / 2]
    yn = snapped(refined(-span / 2, span / 2, h, -span / 2, span / 2), man, h)
    xn = np.linspace(-span / 2, span / 2, 6)          # uniform along the line
    zn = np.linspace(0, t_cu, max(int(t_cu / h), 4) + 1)

    def fn(X, Y, Z):
        k = np.full(X.shape, k_diel)
        k[np.abs(Y) <= w / 2] = K_CU
        return k
    return fn, xn, yn, zn, w / p, 0.0


def models(f_cu, f_ox, k_i=K_CU, k_o=K_SIO2, k_m=K_SI, r_cu=None, r_out=None) -> dict:
    """The three closed-form candidates, on the same volume fractions."""
    f_m = max(1.0 - f_cu - f_ox, 0.0)
    voigt = f_cu * k_i + f_ox * k_o + f_m * k_m
    reuss = 1.0 / (f_cu / k_i + (f_ox / k_o if f_ox else 0.0) + f_m / k_m)
    f_i = f_cu + f_ox
    if r_out and r_cu:
        k_incl = (k_i * r_cu ** 2 + k_o * (r_out ** 2 - r_cu ** 2)) / r_out ** 2
    else:
        k_incl = k_i
    mg = (k_m * (k_incl * (1 + f_i) + k_m * (1 - f_i))
          / (k_incl * (1 - f_i) + k_m * (1 + f_i))) if f_i < 1 else k_incl
    return {"voigt_kz": voigt, "reuss_kxy": reuss, "maxwell_kxy": mg}


def verdict(err_pct: float) -> str:
    return ("ACCEPTED" if err_pct <= ACCEPT_PCT else
            "CONDITIONAL" if err_pct <= CONDITIONAL_PCT else "REJECTED")


def main() -> int:
    rows = []
    # ---- TSV arrays -------------------------------------------------------------------
    for r_cu_um, t_ox_um, pitch_um in ((15.0, 0.5, 60.0), (15.0, 0.5, 40.0),
                                       (5.0, 0.3, 20.0), (25.0, 1.0, 100.0),
                                       (15.0, 0.5, 35.0)):
        r_cu, t_ox, p = r_cu_um * 1e-6, t_ox_um * 1e-6, pitch_um * 1e-6
        fn, xn, yn, zn, f_cu, f_ox = tsv_cell(r_cu, t_ox, p, p)
        kz = _k_eff(fn, xn, yn, zn, 2)
        kx = _k_eff(fn, xn, yn, zn, 0)
        md = models(f_cu, f_ox, r_cu=r_cu, r_out=r_cu + t_ox)
        fw = TF.k_tensor(r_cu, t_ox, p, p * 40) if TF.available() else {"k_x": float("nan"),
                                                                        "k_z": float("nan")}
        rows.append({
            "layer": "TSV_array", "geometry": f"r_cu={r_cu_um} t_ox={t_ox_um} p={pitch_um} um",
            "f_inclusion": f_cu, "f_liner": f_ox,
            "RVE_kz": kz["k_eff"], "RVE_kxy": kx["k_eff"],
            "voigt_kz": md["voigt_kz"], "reuss_kxy": md["reuss_kxy"],
            "maxwell_kxy": md["maxwell_kxy"],
            "framework_kz": fw["k_z"], "framework_kxy": fw["k_x"],
            "err_voigt_kz_pct": 100 * abs(md["voigt_kz"] - kz["k_eff"]) / kz["k_eff"],
            "err_maxwell_kxy_pct": 100 * abs(md["maxwell_kxy"] - kx["k_eff"]) / kx["k_eff"],
            "err_reuss_kxy_pct": 100 * abs(md["reuss_kxy"] - kx["k_eff"]) / kx["k_eff"],
            "err_framework_kxy_pct": 100 * abs(fw["k_x"] - kx["k_eff"]) / kx["k_eff"],
            "anisotropy_kz_over_kxy": kz["k_eff"] / kx["k_eff"],
            "rho_cp_eff": f_cu * RCP_CU + f_ox * RCP_SIO2 + (1 - f_cu - f_ox) * RCP_SI,
            "n_cells_z": kz["n_cells"], "n_cells_x": kx["n_cells"],
            "balance_err": max(kz["balance_err"], kx["balance_err"])})
        print(f"  TSV r={r_cu_um} p={pitch_um}: RVE kz={kz['k_eff']:.2f} kxy={kx['k_eff']:.2f}"
              f" | voigt {md['voigt_kz']:.2f} | maxwell {md['maxwell_kxy']:.2f}"
              f" | framework {fw['k_x']:.2f}", flush=True)

    # ---- periodicity check: 1x1 against 2x2 -------------------------------------------
    r_cu, t_ox, p = 15e-6, 0.5e-6, 60e-6
    fn1, x1, y1, z1, fc1, fo1 = tsv_cell(r_cu, t_ox, p, p, nper=1, nfine=10)
    fn2, x2, y2, z2, fc2, fo2 = tsv_cell(r_cu, t_ox, p, p, nper=2, nfine=10)
    k1 = _k_eff(fn1, x1, y1, z1, 0)["k_eff"]
    k2 = _k_eff(fn2, x2, y2, z2, 0)["k_eff"]
    rows.append({"layer": "TSV_periodicity_check", "geometry": "1x1 vs 2x2 cell",
                 "RVE_kxy": k1, "framework_kxy": k2,
                 "err_framework_kxy_pct": 100 * abs(k2 - k1) / k1})
    print(f"  periodicity 1x1 {k1:.3f} vs 2x2 {k2:.3f}  "
          f"({100*abs(k2-k1)/k1:.3f} %)", flush=True)

    # ---- bump / underfill --------------------------------------------------------------
    for tag, r_um, p_um, h_um, kb, kf in (
            ("microbump_underfill", 5.0, 20.0, 10.0, K_SOLDER, K_UNDERFILL),
            ("C4_underfill", 50.0, 150.0, 70.0, K_SOLDER, K_UNDERFILL),
            ("BGA_mold", 200.0, 800.0, 300.0, K_SOLDER, K_ORG)):
        fn, xn, yn, zn, f_b, _ = bump_cell(r_um * 1e-6, p_um * 1e-6, h_um * 1e-6, kb, kf)
        kz = _k_eff(fn, xn, yn, zn, 2)
        kx = _k_eff(fn, xn, yn, zn, 0)
        md = models(f_b, 0.0, k_i=kb, k_m=kf)
        rows.append({"layer": tag, "geometry": f"r={r_um} p={p_um} h={h_um} um",
                     "f_inclusion": f_b, "f_liner": 0.0,
                     "RVE_kz": kz["k_eff"], "RVE_kxy": kx["k_eff"],
                     "voigt_kz": md["voigt_kz"], "reuss_kxy": md["reuss_kxy"],
                     "maxwell_kxy": md["maxwell_kxy"],
                     "err_voigt_kz_pct": 100 * abs(md["voigt_kz"] - kz["k_eff"]) / kz["k_eff"],
                     "err_maxwell_kxy_pct": 100 * abs(md["maxwell_kxy"] - kx["k_eff"]) / kx["k_eff"],
                     "err_reuss_kxy_pct": 100 * abs(md["reuss_kxy"] - kx["k_eff"]) / kx["k_eff"],
                     "anisotropy_kz_over_kxy": kz["k_eff"] / kx["k_eff"],
                     "n_cells_z": kz["n_cells"], "n_cells_x": kx["n_cells"],
                     "balance_err": max(kz["balance_err"], kx["balance_err"])})
        print(f"  {tag}: RVE kz={kz['k_eff']:.3f} kxy={kx['k_eff']:.3f} "
              f"| voigt {md['voigt_kz']:.3f} | maxwell {md['maxwell_kxy']:.3f}", flush=True)

    # ---- RDL / dielectric ---------------------------------------------------------------
    for t_um, w_um, s_um in ((10.0, 10.0, 2.0), (10.0, 2.0, 2.0), (5.0, 10.0, 2.0)):
        fn, xn, yn, zn, f_cu, _ = rdl_cell(t_um * 1e-6, w_um * 1e-6, s_um * 1e-6)
        k_along = _k_eff(fn, xn, yn, zn, 0)      # along the lines
        k_across = _k_eff(fn, xn, yn, zn, 1)     # across the lines
        k_thru = _k_eff(fn, xn, yn, zn, 2)       # through the layer
        md = models(f_cu, 0.0, k_i=K_CU, k_m=K_ORG)
        rows.append({"layer": "RDL_dielectric", "geometry": f"t={t_um} W={w_um} S={s_um} um",
                     "f_inclusion": f_cu, "f_liner": 0.0,
                     "RVE_kz": k_thru["k_eff"], "RVE_kxy": k_across["k_eff"],
                     "RVE_k_along_lines": k_along["k_eff"],
                     "voigt_kz": md["voigt_kz"], "reuss_kxy": md["reuss_kxy"],
                     "maxwell_kxy": md["maxwell_kxy"],
                     "err_voigt_kz_pct": 100 * abs(md["voigt_kz"] - k_along["k_eff"]) / k_along["k_eff"],
                     "err_reuss_kxy_pct": 100 * abs(md["reuss_kxy"] - k_across["k_eff"]) / k_across["k_eff"],
                     "err_maxwell_kxy_pct": 100 * abs(md["maxwell_kxy"] - k_across["k_eff"]) / k_across["k_eff"],
                     "anisotropy_kz_over_kxy": k_along["k_eff"] / k_across["k_eff"],
                     "n_cells_z": k_thru["n_cells"], "n_cells_x": k_across["n_cells"],
                     "balance_err": max(k_thru["balance_err"], k_across["balance_err"])})
        print(f"  RDL t={t_um} W/S={w_um}/{s_um}: along={k_along['k_eff']:.2f} "
              f"across={k_across['k_eff']:.3f} through={k_thru['k_eff']:.3f} "
              f"anis={k_along['k_eff']/k_across['k_eff']:.1f}x", flush=True)

    for r in rows:
        for m_ in ("voigt_kz", "maxwell_kxy", "reuss_kxy", "framework_kxy"):
            e = r.get(f"err_{m_}_pct")
            if e is not None and np.isfinite(e):
                r[f"verdict_{m_}"] = verdict(e)
    keys = sorted({k for r in rows for k in r})
    with open(OUT / "effective_layer_properties.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
    print(f"\nwrote {OUT/'effective_layer_properties.csv'} ({len(rows)} layers)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
