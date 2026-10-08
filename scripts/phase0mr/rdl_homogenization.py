#!/usr/bin/env python3
"""Phase-0M-R Section 8 -- RDL and bump effective properties from the ACTUAL stack.

PHASE-0M MEASURED 153x TO 276x ANISOTROPY. That was for a SINGLE-DIRECTION LINE CELL, and
Phase 0M said so. It must NOT be assigned to the production package, because the production
stack is not one line layer: the ECTC-2024 RDL is 2 VDD + 2 GND layers, and a power
distribution stack routes orthogonally or as planes. The whole point of this section is that
the number depends on the stack ORGANISATION, not on the line geometry alone.

Four organisations are computed on explicit unit cells:
    LINES_1D    all layers parallel            -- the Phase-0M extreme
    ORTHOGONAL  alternating x / y layers       -- a realistic routed stack
    MESH        orthogonal lines within one layer
    PLANE       solid metal, occupancy 1       -- the power-plane limit

Bump-rich interface layers are computed separately and are NOT given the TSV formula: the
inclusion is a low-conductivity solder in a low-conductivity matrix, a completely different
contrast from copper in silicon, and Phase 0M already showed the TSV transverse model fails
by 19 to 74 %.
"""
from __future__ import annotations
import csv, math, sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
for d in ("phase0mr", "phase0m"):
    sys.path.insert(0, str(R / "scripts" / d))
from conduction3d import FVConduction, refined, snapped                    # noqa: E402
from homogenization import _k_eff, K_CU, K_ORG, K_SOLDER, K_UNDERFILL      # noqa: E402

OUT = R / "results" / "phase0mr"
OUT.mkdir(parents=True, exist_ok=True)

# ECTC-2024 Table I
T_CU_UM, W_UM, S_UM, N_VDD, N_GND = 10.0, 10.0, 2.0, 2, 2
T_DIEL_UM = 5.0                    # inter-layer dielectric, ASSUMPTION, swept
E_CU, NU_CU, CTE_CU = 117e3, 0.34, 17.0e-6
E_ORG, NU_ORG, CTE_ORG = 20e3, 0.30, 30.0e-6


def stack_cell(org: str, t_cu=T_CU_UM * 1e-6, w=W_UM * 1e-6, s=S_UM * 1e-6,
               t_diel=T_DIEL_UM * 1e-6, n_layers=4, nfine=8):
    """A full RDL STACK unit cell: n_layers of metal separated by dielectric."""
    p = w + s
    h = min(w / nfine, s / max(nfine // 3, 2))
    span = p
    man = [-w / 2, 0.0, w / 2]
    xn = snapped(refined(-span / 2, span / 2, h, -span / 2, span / 2), man, h)
    yn = xn.copy()
    zs, z = [0.0], 0.0
    for i in range(n_layers):
        z += t_cu; zs.append(z)
        if i < n_layers - 1:
            z += t_diel; zs.append(z)
    zn = np.unique(np.concatenate([np.linspace(a, b, max(int((b - a) / h), 3) + 1)
                                   for a, b in zip(zs[:-1], zs[1:])]))
    z_metal = [(zs[2 * i], zs[2 * i + 1]) for i in range(n_layers)]

    def fn(X, Y, Z):
        k = np.full(X.shape, K_ORG)
        for i, (z0, z1) in enumerate(z_metal):
            lay = (Z > z0) & (Z <= z1)
            if org == "PLANE":
                k[lay] = K_CU
            elif org == "LINES_1D":
                k[lay & (np.abs(Y) <= w / 2)] = K_CU
            elif org == "ORTHOGONAL":
                if i % 2 == 0:
                    k[lay & (np.abs(Y) <= w / 2)] = K_CU
                else:
                    k[lay & (np.abs(X) <= w / 2)] = K_CU
            elif org == "MESH":
                k[lay & ((np.abs(Y) <= w / 2) | (np.abs(X) <= w / 2))] = K_CU
            else:
                raise ValueError(org)
        return k

    occ = {"PLANE": 1.0, "LINES_1D": w / p, "ORTHOGONAL": w / p,
           "MESH": 1 - (1 - w / p) ** 2}[org]
    f_cu = occ * n_layers * t_cu / zs[-1]
    return fn, xn, yn, zn, f_cu, zs[-1]


def mech_tensor(org: str, f_cu: float) -> dict:
    """Effective in-plane and through-thickness moduli and CTEs of the stack.

    In plane, metal that RUNS in the direction of loading acts in parallel (Voigt); metal
    transverse to it acts in series (Reuss). Through thickness every phase is in series.
    CTE follows the stiffness-weighted average, exact for two isotropic phases under uniform
    temperature.
    """
    frac_along = {"PLANE": 1.0, "LINES_1D": 1.0, "ORTHOGONAL": 0.5, "MESH": 0.5}[org]
    f_par = f_cu * frac_along
    f_ser = f_cu * (1 - frac_along)
    f_org = 1 - f_cu
    e_x = f_par * E_CU + (1 - f_par) * (1.0 / ((f_ser / E_CU + f_org / E_ORG)
                                               / max(f_ser + f_org, 1e-12)))
    e_z = 1.0 / (f_cu / E_CU + f_org / E_ORG)
    cte_x = (f_par * E_CU * CTE_CU + (1 - f_par) * E_ORG * CTE_ORG) / \
            (f_par * E_CU + (1 - f_par) * E_ORG)
    cte_z = (f_cu * E_CU * CTE_CU + f_org * E_ORG * CTE_ORG) / (f_cu * E_CU + f_org * E_ORG)
    return {"E_x_MPa": e_x, "E_y_MPa": e_x if org in ("ORTHOGONAL", "MESH", "PLANE")
            else 1.0 / (f_cu / E_CU + f_org / E_ORG),
            "E_z_MPa": e_z, "CTE_x": cte_x, "CTE_z": cte_z,
            "in_plane_isotropic": org in ("ORTHOGONAL", "MESH", "PLANE")}


def bump_layer(r_um: float, p_um: float, h_um: float, k_incl: float, k_mat: float,
               nfine: int = 10) -> dict:
    """A bump / underfill layer. NOT the TSV formula: the contrast and the matrix differ."""
    r, p, hh = r_um * 1e-6, p_um * 1e-6, h_um * 1e-6
    h = min(r / nfine, p / (3 * nfine))
    xn = snapped(refined(-p / 2, p / 2, h, -p / 2, p / 2), [-r, 0.0, r], h)
    yn = xn.copy()
    zn = np.linspace(0, hh, max(int(hh / (p / 5)), 4) + 1)

    def fn(X, Y, Z):
        k = np.full(X.shape, k_mat)
        k[X ** 2 + Y ** 2 <= r ** 2] = k_incl
        return k
    f = math.pi * r ** 2 / p ** 2
    kz = _k_eff(fn, xn, yn, zn, 2)
    kx = _k_eff(fn, xn, yn, zn, 0)
    voigt = f * k_incl + (1 - f) * k_mat
    mg = k_mat * (k_incl * (1 + f) + k_mat * (1 - f)) / (k_incl * (1 - f) + k_mat * (1 + f))
    return {"f_inclusion": f, "RVE_kz": kz["k_eff"], "RVE_kxy": kx["k_eff"],
            "voigt_kz": voigt, "maxwell_kxy": mg,
            "err_voigt_kz_pct": 100 * abs(voigt - kz["k_eff"]) / kz["k_eff"],
            "err_maxwell_kxy_pct": 100 * abs(mg - kx["k_eff"]) / kx["k_eff"],
            "anisotropy": kz["k_eff"] / kx["k_eff"]}


def main() -> int:
    rows = []
    for org in ("LINES_1D", "ORTHOGONAL", "MESH", "PLANE"):
        for t_d in (2.0, 5.0, 10.0):
            fn, xn, yn, zn, f_cu, h_tot = stack_cell(org, t_diel=t_d * 1e-6)
            kx = _k_eff(fn, xn, yn, zn, 0)
            ky = _k_eff(fn, xn, yn, zn, 1)
            kz = _k_eff(fn, xn, yn, zn, 2)
            m = mech_tensor(org, f_cu)
            rows.append({"organisation": org, "t_diel_um": t_d, "f_cu": f_cu,
                         "stack_height_um": h_tot * 1e6,
                         "k_x": kx["k_eff"], "k_y": ky["k_eff"], "k_z": kz["k_eff"],
                         "in_plane_anisotropy_x_over_y": kx["k_eff"] / ky["k_eff"],
                         "through_over_inplane": kz["k_eff"] / min(kx["k_eff"], ky["k_eff"]),
                         "max_anisotropy": max(kx["k_eff"], ky["k_eff"], kz["k_eff"])
                                           / min(kx["k_eff"], ky["k_eff"], kz["k_eff"]),
                         **m, "balance_err": max(kx["balance_err"], kz["balance_err"])})
            print(f"  {org:11s} t_diel={t_d:4.1f} f_cu={f_cu:.4f}  "
                  f"kx={kx['k_eff']:7.2f} ky={ky['k_eff']:7.2f} kz={kz['k_eff']:7.2f}  "
                  f"x/y={kx['k_eff']/ky['k_eff']:6.2f}  max/min="
                  f"{max(kx['k_eff'],ky['k_eff'],kz['k_eff'])/min(kx['k_eff'],ky['k_eff'],kz['k_eff']):7.1f}"
                  f"  E_x={m['E_x_MPa']/1e3:6.1f} GPa CTE_x={m['CTE_x']*1e6:5.2f}", flush=True)
    with open(OUT / "rdl_effective_tensor.csv", "w", newline="") as fh:
        k = sorted({x for r in rows for x in r})
        w = csv.DictWriter(fh, fieldnames=k); w.writeheader(); w.writerows(rows)

    brows = []
    for tag, r_um, p_um, h_um, ki, km in (
            ("microbump_underfill", 5.0, 20.0, 10.0, K_SOLDER, K_UNDERFILL),
            ("C4_underfill", 50.0, 150.0, 70.0, K_SOLDER, K_UNDERFILL),
            ("BGA_mold", 200.0, 800.0, 300.0, K_SOLDER, K_ORG),
            ("microbump_dense", 5.0, 12.0, 10.0, K_SOLDER, K_UNDERFILL)):
        b = bump_layer(r_um, p_um, h_um, ki, km)
        b.update(layer=tag, r_um=r_um, pitch_um=p_um, h_um=h_um,
                 k_inclusion=ki, k_matrix=km)
        brows.append(b)
        print(f"  {tag:22s} f={b['f_inclusion']:.4f} kz={b['RVE_kz']:7.3f} "
              f"kxy={b['RVE_kxy']:7.3f} anis={b['anisotropy']:5.1f}  "
              f"Voigt err {b['err_voigt_kz_pct']:.2f} %  Maxwell err "
              f"{b['err_maxwell_kxy_pct']:.2f} %", flush=True)
    with open(OUT / "bump_layer_effective_tensor.csv", "w", newline="") as fh:
        k = sorted({x for r in brows for x in r})
        w = csv.DictWriter(fh, fieldnames=k); w.writeheader(); w.writerows(brows)
    print(f"wrote {OUT/'rdl_effective_tensor.csv'} and bump_layer_effective_tensor.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
