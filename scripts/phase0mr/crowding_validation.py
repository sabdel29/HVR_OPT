#!/usr/bin/env python3
"""Phase-0M-R Section 4 -- independent validation of the transition-resistance model.

PREDECLARED ACCEPTANCE, fixed before any cross-solver run (brief Section 4):
    canonical bulk cases            <= 2 %
    realistic transition resistance <= 5 % ACCEPTED, <= 10 % CONDITIONAL, else REJECTED
If validation fails, the transition model stays OUT of production.

REFERENCE PLANES, stated once and used identically by both solvers:
    inlet   the via bottom face, z = 0, r <= r_via          EQUIPOTENTIAL (Dirichlet)
    outlet  the trace exit face, x = +span, inside the RDL  EQUIPOTENTIAL (Dirichlet)
    all other outer faces insulated; the dielectric is present in both models
    R = dV / Q_inlet
Both terminals equipotential in BOTH codes. Nothing else conducts to the boundary.

WHY THAT MATTERS FOR SIGN. Phase 0M reported K_crowd < 1 for a generous landing pad and
called `dR = R_3D - R_bulk` an "excess". `dR` is only an excess if `R_bulk` uses the SAME
terminals. It does not: `R_bulk` is a 1-D series of named conductors with implicit
equipotential cross-sections everywhere, while `R_3D` constrains only the two planes above.
Section 4 therefore reports `R_total` as the validated quantity and treats `dR` as a
DIFFERENCE AGAINST A STATED 1-D REFERENCE, not as a physical excess.
"""
from __future__ import annotations
import csv, math, sys, time
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
for d in ("phase0mr", "phase0m"):
    sys.path.insert(0, str(R / "scripts" / d))
import crowding as CR                                                      # noqa: E402
import moose_conduction as MC                                             # noqa: E402
from conduction3d import FVConduction                                      # noqa: E402
from interconnect import rho_cu, rho_solder                                # noqa: E402

OUT = R / "results" / "phase0mr"
OUT.mkdir(parents=True, exist_ok=True)
T_C = 85.0
SIG_CU = 1.0 / rho_cu(T_C)
SIG_SN = 1.0 / rho_solder(T_C)

ACCEPT_BULK_PCT = 2.0
ACCEPT_TRANS_PCT = 5.0
CONDITIONAL_TRANS_PCT = 10.0

# five geometries spanning the pad/trace space, plus the two nominal technology cells
# Five geometries spanning the pad/trace space plus the two nominal technology cells.
#
# MESH ALIGNMENT IS PART OF THE CASE DEFINITION. MOOSE's ParsedSubdomainMeshGenerator assigns
# whole elements by CENTROID, so a uniform mesh staircases the trace: at span = 100 um and
# nx = 100 the cell is 2 um and a 10 um trace is captured 8 um wide, 20 % narrow, which alone
# moved the first run by 12 %. Each case therefore fixes `n` so that cell boundaries land
# EXACTLY on +/- w/2 and on the RDL z-planes, and every run reports the discretised block
# volume so the geometry match is proved rather than assumed.
CASES = {
    "TSV_nominal": dict(r_via=15e-6, h_via=30e-6, r_pad=18e-6, w_trace=10e-6,
                        t_rdl=10e-6, l_trace=100e-6, sigma_via=SIG_CU, sigma_metal=SIG_CU),
    "TSV_widepad_widetrace": dict(r_via=15e-6, h_via=30e-6, r_pad=30e-6, w_trace=25e-6,
                                  t_rdl=10e-6, l_trace=100e-6, sigma_via=SIG_CU,
                                  sigma_metal=SIG_CU),
    "TSV_widepad_narrowtrace": dict(r_via=15e-6, h_via=30e-6, r_pad=30e-6, w_trace=5e-6,
                                    t_rdl=10e-6, l_trace=100e-6, sigma_via=SIG_CU,
                                    sigma_metal=SIG_CU),
    "TSV_narrowpad_widetrace": dict(r_via=15e-6, h_via=30e-6, r_pad=15e-6, w_trace=25e-6,
                                    t_rdl=10e-6, l_trace=100e-6, sigma_via=SIG_CU,
                                    sigma_metal=SIG_CU),
    "bump_nominal": dict(r_via=5e-6, h_via=10e-6, r_pad=6e-6, w_trace=5e-6,
                         t_rdl=5e-6, l_trace=40e-6, sigma_via=SIG_SN, sigma_metal=SIG_CU),
}
# (nx, ny, nz) chosen so 2*span/nx divides w/2 exactly and z_top/nz divides h_via exactly
MESH = {"TSV_nominal": (120, 120, 24),
        "TSV_widepad_widetrace": (80, 80, 16),
        "TSV_widepad_narrowtrace": (160, 160, 32),
        "TSV_narrowpad_widetrace": (80, 80, 16),
        "bump_nominal": (96, 96, 18)}


def mesh_alignment(name: str) -> dict:
    """Prove the MOOSE mesh lands on the geometry before trusting the comparison."""
    c = CASES[name]
    nx, ny, nz = MESH[name]
    span, w = c["l_trace"], c["w_trace"]
    z_top = c["h_via"] + c["t_rdl"]
    dx, dz = 2 * span / nx, z_top / nz
    return {"cell_xy_um": dx * 1e6, "cell_z_um": dz * 1e6,
            "cells_across_trace": w / dx,
            "trace_edge_on_node": abs((w / 2) / dx - round((w / 2) / dx)) < 1e-9,
            "rdl_plane_on_node": abs(c["h_via"] / dz - round(c["h_via"] / dz)) < 1e-9}


def fv_cell(name: str) -> CR.Cell:
    return CR.Cell(name=name, **CASES[name])


def moose_geometry(c: CR.Cell) -> dict:
    return {"span": c.l_trace, "z_top": c.z_top, "r_via": c.r_via, "r_pad": c.r_pad,
            "w_trace": c.w_trace, "z_ubm0": c.z_ubm0, "z_rdl0": c.z_rdl0}


def fv_resistance(c: CR.Cell, refine: float) -> dict:
    """Same reference planes as the MOOSE model: inlet = via bottom, outlet = +x trace exit."""
    xn, yn, zn = c.mesh(refine=refine)
    m = FVConduction(xn, yn, zn)
    m.assign(c.sigma_fn())
    X, Y, Z = np.meshgrid(m.xc, m.yc, m.zc, indexing="ij")
    inj = (X ** 2 + Y ** 2 <= c.r_via ** 2) & (Z <= m.zc[0] + 1e-18)
    gnd = (X >= m.xc[-1] - 1e-18) & (m.sigma > c.sigma_metal * 0.5)
    if not inj.any() or not gnd.any():
        return {"status": "DEGENERATE"}
    m.solve(inj, 1.0, gnd, axis_in=2, axis_gnd=0)
    ib = abs(m.current_out() - 1.0)
    if ib > 1e-3:
        return {"status": f"CURRENT BALANCE FAILED ({ib:.2e})"}
    return {"status": "OK", "R_ohm": m.resistance(),
            "R_from_power_ohm": m.resistance_from_power(),
            "balance_err": ib, "n_cells": m.n, "n_active": m.n_active}


def main() -> int:
    rows = []
    # ---- 1. canonical bulk, both solvers ------------------------------------------------
    sig, L, a = 5.8e7, 100e-6, 20e-6
    m = FVConduction(np.linspace(0, L, 13), np.linspace(0, a, 13), np.linspace(0, a, 13))
    m.assign(lambda X, Y, Z: np.full_like(X, sig))
    inj = np.zeros((12, 12, 12), bool); inj[0, :, :] = True
    gnd = np.zeros((12, 12, 12), bool); gnd[-1, :, :] = True
    m.solve(inj, 1.0, gnd, axis_in=0, axis_gnd=0)
    an = L / (sig * a * a)
    fvb = m.resistance()
    mb = MC.uniform_bar(sig, L, a) if MC.available() else {"status": "MOOSE ABSENT"}
    rows.append({"case": "canonical_uniform_bar", "kind": "bulk",
                 "R_fv_ohm": fvb, "R_moose_ohm": mb.get("R_ohm"), "R_analytic_ohm": an,
                 "fv_vs_analytic_pct": 100 * abs(fvb - an) / an,
                 "moose_vs_analytic_pct": (100 * abs(mb["R_ohm"] - an) / an
                                           if mb.get("R_ohm") else float("nan")),
                 "fv_vs_moose_pct": (100 * abs(fvb - mb["R_ohm"]) / mb["R_ohm"]
                                     if mb.get("R_ohm") else float("nan")),
                 "accept_pct": ACCEPT_BULK_PCT, "status": mb.get("status", "OK")})
    print(f"  canonical bar: FV {fvb:.6e}  MOOSE {mb.get('R_ohm', float('nan')):.6e}  "
          f"analytic {an:.6e}", flush=True)

    # ---- 2. transition cells, both solvers ----------------------------------------------
    for name in CASES:
        c = fv_cell(name)
        fv = fv_resistance(c, refine=1.3)
        fv_c = fv_resistance(c, refine=1.7)
        mo = (MC.run(name, moose_geometry(c), *MESH[name], c.sigma_via, c.sigma_metal)
              if MC.available() else {"status": "MOOSE ABSENT"})
        rb = c.r_bulk()
        al = mesh_alignment(name)
        v_analytic = (math.pi * c.r_via ** 2 * c.h_via)
        v_metal_analytic = (math.pi * c.r_pad ** 2 * c.t_rdl
                            + max(c.l_trace - c.r_pad, 0.0) * c.w_trace * c.t_rdl)
        row = {"case": name, "kind": "transition", **al,
               "vol_via_analytic_m3": v_analytic,
               "vol_via_moose_m3": mo.get("vol_via_m3"),
               "vol_via_err_pct": (100 * abs(mo["vol_via_m3"] - v_analytic) / v_analytic
                                   if mo.get("vol_via_m3") else None),
               "vol_metal_analytic_m3": v_metal_analytic,
               "vol_metal_moose_m3": mo.get("vol_metal_m3"),
               "vol_metal_err_pct": (100 * abs(mo["vol_metal_m3"] - v_metal_analytic)
                                     / v_metal_analytic if mo.get("vol_metal_m3") else None),
               "r_via_um": c.r_via * 1e6, "r_pad_um": c.r_pad * 1e6,
               "w_trace_um": c.w_trace * 1e6, "t_rdl_um": c.t_rdl * 1e6,
               "l_trace_um": c.l_trace * 1e6,
               "R_fv_ohm": fv.get("R_ohm"), "R_fv_refined_ohm": fv_c.get("R_ohm"),
               "fv_mesh_drift_pct": (100 * abs(fv_c["R_ohm"] - fv["R_ohm"]) / fv["R_ohm"]
                                     if fv.get("R_ohm") and fv_c.get("R_ohm") else None),
               "R_moose_ohm": mo.get("R_ohm"),
               "moose_balance_err": mo.get("balance_err"),
               "R_1d_reference_ohm": rb,
               "fv_status": fv.get("status"), "moose_status": mo.get("status"),
               "moose_wall_s": mo.get("wall_s"), "accept_pct": ACCEPT_TRANS_PCT}
        if fv.get("R_ohm") and mo.get("R_ohm"):
            e = 100 * abs(fv["R_ohm"] - mo["R_ohm"]) / mo["R_ohm"]
            row["fv_vs_moose_pct"] = e
            row["verdict"] = ("ACCEPTED" if e <= ACCEPT_TRANS_PCT else
                              "CONDITIONAL" if e <= CONDITIONAL_TRANS_PCT else "REJECTED")
            row["dR_vs_1d_ohm"] = fv["R_ohm"] - rb
            row["R_over_1d"] = fv["R_ohm"] / rb
        rows.append(row)
        print(f"  {name:26s} FV {fv.get('R_ohm', float('nan')):.5e}  "
              f"MOOSE {mo.get('R_ohm', float('nan')):.5e}  "
              f"diff {row.get('fv_vs_moose_pct', float('nan')):.2f} %  "
              f"{row.get('verdict', mo.get('status'))}", flush=True)

    keys = sorted({k for r in rows for k in r})
    with open(OUT / "current_crowding_validation.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
    tr = [r for r in rows if r["kind"] == "transition" and r.get("verdict")]
    bad = [r for r in tr if r["verdict"] == "REJECTED"]
    print(f"\n{len(tr)}/{len(CASES)} transition cells cross-validated; "
          f"{sum(1 for r in tr if r['verdict'] == 'ACCEPTED')} ACCEPTED, "
          f"{sum(1 for r in tr if r['verdict'] == 'CONDITIONAL')} CONDITIONAL, "
          f"{len(bad)} REJECTED")
    print(f"wrote {OUT/'current_crowding_validation.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
