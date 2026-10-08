#!/usr/bin/env python3
"""H0 vs H1 validation of the TSV homogenisation.

Phase 0B found the homogenised TSV field carries ~36% of die warpage, promoting the
homogenisation from a detail to a first-order scientific dependency. Two independent
checks are run, because they answer different questions.

H1a - UNIT-CELL NUMERICAL HOMOGENISATION (validates the CONSTANTS)
    A single 60 um square-pitch cell containing one explicit Cu via in a Si matrix.
    Mirror symmetry on all four side faces is exact for a centred square array, so
    symmetry BCs are equivalent to periodic BCs here. Effective E, nu, alpha and k are
    measured numerically and compared against the Voigt / stiffness-weighted-ROM /
    Maxwell-Garnett values that etm.config.derive_tsv_homog() supplies to the package
    model. The via is modelled as an equal-AREA square so that a structured conforming
    mesh represents it exactly; this preserves the volume fraction and the load path,
    and is a standard idealisation for an effective-property extraction.

H1b - PACKAGE-SCALE DISCRETE-INCLUSION MODEL (validates the ARCHITECTURAL SPREAD)
    Explicitly meshing 26 667 vias at 60 um pitch is computationally irrational, so H1b
    instead keeps the Cu volume fraction EXACTLY equal and coarsens the pitch until the
    inclusions are explicitly meshable (600 um pitch, equal-area square section). This is
    a scale-separation test: if the homogenisation is valid, global warpage and - far more
    importantly - the C05-vs-C07 architectural spread must be insensitive to whether the
    same Cu is smeared or resolved as discrete blocks.

What H1b does NOT establish: per-via local stress, liner effects, or the true 30 um
geometry's local field. Those need the M1 rung.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase0b"))
from etm.ccxio import read_frd, run_ccx              # noqa: E402
from etm.config import (MM_PER_M_INV, build_materials, derive_tsv_homog,  # noqa: E402
                        load_doe, load_stack)

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0c" / "homogenization"


# ---------------------------------------------------------------------------
# H1a: unit cell
# ---------------------------------------------------------------------------

def _grid(breaks, n_per):
    pts = [breaks[0]]
    for lo, hi in zip(breaks[:-1], breaks[1:]):
        pts.extend(np.linspace(lo, hi, n_per + 1)[1:])
    return np.array(pts)


def build_unit_cell(pitch_mm: float, d_mm: float, height_mm: float, n: int = 6):
    """Square-pitch cell, one equal-area square Cu inclusion centred, Si matrix."""
    a = math.sqrt(math.pi * d_mm * d_mm / 4.0)            # equal-area square side
    lo, hi = (pitch_mm - a) / 2.0, (pitch_mm + a) / 2.0
    xs = _grid([0.0, lo, hi, pitch_mm], n)
    ys = xs.copy()
    zs = _grid([0.0, height_mm], max(4, n))

    nx, ny, nz = len(xs), len(ys), len(zs)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    nodes = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    nid = lambda i, j, k: (i * ny + j) * nz + k + 1

    elems, mats = [], []
    xc, yc = 0.5 * (xs[:-1] + xs[1:]), 0.5 * (ys[:-1] + ys[1:])
    for i in range(len(xc)):
        for j in range(len(yc)):
            inside = (lo - 1e-12 < xc[i] < hi + 1e-12) and (lo - 1e-12 < yc[j] < hi + 1e-12)
            for k in range(len(zs) - 1):
                elems.append([nid(i, j, k), nid(i+1, j, k), nid(i+1, j+1, k), nid(i, j+1, k),
                              nid(i, j, k+1), nid(i+1, j, k+1), nid(i+1, j+1, k+1), nid(i, j+1, k+1)])
                mats.append("copper" if inside else "silicon")
    return nodes, np.array(elems, int), np.array(mats, object), xs, ys, zs, a


def _deck_common(nodes, elems, mats, materials, thermal: bool):
    L = ["*NODE"] + [f"{i+1},{p[0]:.9f},{p[1]:.9f},{p[2]:.9f}" for i, p in enumerate(nodes)]
    for m in sorted(set(mats)):
        ids = np.nonzero(mats == m)[0] + 1
        L.append(f"*ELEMENT, TYPE={'C3D8' if thermal else 'C3D8I'}, ELSET=E_{m.upper()}")
        for e in ids:
            L.append(f"{int(e)}," + ",".join(str(int(v)) for v in elems[e - 1]))
    L.append("*NSET, NSET=NALL, GENERATE")
    L.append(f"1,{len(nodes)}")
    for m in sorted(set(mats)):
        mm = materials[m]
        L.append(f"*MATERIAL, NAME={m.upper()}")
        L += mm.ccx_conductivity() if thermal else mm.ccx_elastic()
        if not thermal:
            L += ["*EXPANSION, ZERO=0.0", f"{mm.cte:.9g}"]
        L.append(f"*SOLID SECTION, ELSET=E_{m.upper()}, MATERIAL={m.upper()}")
    return L


def _planar(L, nodes, axis, val, dof, tol=1e-9):
    """Tie every node on a face to move together in `dof` (keeps the face planar,
    which is what a periodic neighbour enforces)."""
    ids = np.nonzero(np.abs(nodes[:, axis] - val) < tol)[0] + 1
    master = int(ids[0])
    for n in ids[1:]:
        L += ["*EQUATION", "2", f"{int(n)},{dof},1.0,{master},{dof},-1.0"]
    return master, ids


def unit_cell_properties(stack, workdir: Path, pitch=0.060, d=0.030, height=0.060, n=6):
    workdir.mkdir(parents=True, exist_ok=True)
    nodes, elems, mats, xs, ys, zs, a_sq = build_unit_cell(pitch, d, height, n)
    materials = build_materials(stack)
    P, H = pitch, height
    f_true = (a_sq * a_sq) / (P * P)
    out = {"cu_area_fraction_meshed": f_true,
           "cu_area_fraction_analytic": math.pi * d * d / (4 * P * P),
           "equal_area_square_side_mm": a_sq,
           "n_elems": len(elems), "n_nodes": len(nodes)}

    # ---- mechanical: uniaxial-stress test in x, plus free thermal expansion ----
    for tag, mode in (("E", "mech"), ("alpha", "therm")):
        L = _deck_common(nodes, elems, mats, materials, thermal=False)
        # symmetry on the three low faces
        for axis, dof in ((0, 1), (1, 2), (2, 3)):
            ids = np.nonzero(np.abs(nodes[:, axis]) < 1e-9)[0] + 1
            L.append("*BOUNDARY")
            L += [f"{int(nn)},{dof},{dof}" for nn in ids]
        # high faces stay planar (periodic neighbour)
        mx, _ = _planar(L, nodes, 0, P, 1)
        my, _ = _planar(L, nodes, 1, P, 2)
        mz, _ = _planar(L, nodes, 2, H, 3)

        if mode == "mech":
            eps = 1e-4
            L += ["*BOUNDARY", f"{mx},1,1,{eps*P:.12g}"]
            L += ["*INITIAL CONDITIONS, TYPE=TEMPERATURE", "NALL,0.0"]
            L += ["*STEP", "*STATIC", "*TEMPERATURE", "NALL,0.0"]
        else:
            dT = 100.0
            L += ["*INITIAL CONDITIONS, TYPE=TEMPERATURE", "NALL,0.0"]
            L += ["*STEP", "*STATIC", "*TEMPERATURE", f"NALL,{dT}"]

        L += ["*NODE FILE", "U", "*NODE PRINT, NSET=NALL", "RF", "*END STEP"]
        job = workdir / f"cell_{tag}.inp"
        job.write_text("\n".join(L) + "\n")
        run_ccx(job, threads=4)
        U = read_frd(workdir / f"cell_{tag}.frd")["DISP"]

        if mode == "mech":
            dat = (workdir / f"cell_{tag}.dat").read_text()
            blk = dat.split("forces")[-1].strip().splitlines()
            rows = [l.split() for l in blk if l.strip() and l.split()[0].lstrip("-").isdigit()]
            face = set(int(v) for v in np.nonzero(np.abs(nodes[:, 0] - P) < 1e-9)[0] + 1)
            Fx = sum(float(r[1]) for r in rows if int(r[0]) in face)
            sigma = Fx / (P * H)
            out["E_eff_num_MPa"] = float(sigma / eps)
            uy = U[np.nonzero(np.abs(nodes[:, 1] - P) < 1e-9)[0] + 1, 1]
            out["nu_eff_num"] = float(-np.nanmean(uy) / P / eps)
        else:
            ux = U[np.nonzero(np.abs(nodes[:, 0] - P) < 1e-9)[0] + 1, 0]
            uz = U[np.nonzero(np.abs(nodes[:, 2] - H) < 1e-9)[0] + 1, 2]
            out["alpha_xy_eff_num"] = float(np.nanmean(ux) / P / 100.0)
            out["alpha_z_eff_num"] = float(np.nanmean(uz) / H / 100.0)

    # ---- thermal: k_xx and k_zz by imposed gradient ----
    for tag, axis, span in (("kx", 0, P), ("kz", 2, H)):
        L = _deck_common(nodes, elems, mats, materials, thermal=True)
        lo_ids = np.nonzero(np.abs(nodes[:, axis]) < 1e-9)[0] + 1
        hi_ids = np.nonzero(np.abs(nodes[:, axis] - span) < 1e-9)[0] + 1
        L += ["*INITIAL CONDITIONS, TYPE=TEMPERATURE", "NALL,0.0"]
        L += ["*STEP", "*HEAT TRANSFER, STEADY STATE", "*BOUNDARY"]
        L += [f"{int(n_)},11,11,0.0" for n_ in lo_ids]
        L += [f"{int(n_)},11,11,1.0" for n_ in hi_ids]
        L += ["*NODE PRINT, NSET=NALL", "RFL", "*END STEP"]
        job = workdir / f"cell_{tag}.inp"
        job.write_text("\n".join(L) + "\n")
        run_ccx(job, threads=4)
        dat = (workdir / f"cell_{tag}.dat").read_text()
        blk = dat.split("heat generation")[-1].strip().splitlines()
        rows = [l.split() for l in blk if l.strip() and l.split()[0].lstrip("-").isdigit()]
        hs = set(int(v) for v in hi_ids)
        Q = sum(float(r[1]) for r in rows if int(r[0]) in hs)      # W
        area = (P * H) if axis == 0 else (P * P)
        # k in W/(mm.K) -> convert back to W/(m.K)
        out[f"{tag}_eff_num_W_mK"] = float(abs(Q) * span / (area * 1.0) / MM_PER_M_INV)

    # ---- analytic values actually used by the package model ----
    an = derive_tsv_homog(stack)
    out["analytic"] = {"E_MPa": an["E"]["value"], "nu": an["nu"]["value"],
                       "cte": an["cte"]["value"],
                       "k_xy_W_mK": an["k_ortho"]["value"][0],
                       "k_z_W_mK": an["k_ortho"]["value"][2]}
    out["error_pct"] = {
        "E": 100 * (out["E_eff_num_MPa"] - an["E"]["value"]) / an["E"]["value"],
        "nu": 100 * (out["nu_eff_num"] - an["nu"]["value"]) / an["nu"]["value"],
        "alpha_xy": 100 * (out["alpha_xy_eff_num"] - an["cte"]["value"]) / an["cte"]["value"],
        "alpha_z": 100 * (out["alpha_z_eff_num"] - an["cte"]["value"]) / an["cte"]["value"],
        "k_xy": 100 * (out["kx_eff_num_W_mK"] - an["k_ortho"]["value"][0]) / an["k_ortho"]["value"][0],
        "k_z": 100 * (out["kz_eff_num_W_mK"] - an["k_ortho"]["value"][2]) / an["k_ortho"]["value"][2],
    }
    return out


if __name__ == "__main__":
    stack = load_stack()
    OUT.mkdir(parents=True, exist_ok=True)
    res = unit_cell_properties(stack, OUT / "unit_cell")
    print(json.dumps(res, indent=2))
    (OUT / "unit_cell_properties.json").write_text(json.dumps(res, indent=2))
