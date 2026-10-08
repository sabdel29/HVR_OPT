#!/usr/bin/env python3
"""BC-B support-model calibration and sensitivity envelope.

Phase 0B's BC-B foundation stiffness was PROVISIONAL and uncalibrated. The spec asks for
calibration "from an explicit BGA unit-cell model or package/board data", and searching the
repository DOES turn up source-backed geometry: June-2026 Table III gives the BGA as
solder, 400 um diameter / 300 um height / 800 um pitch. Solder elastic properties are taken
from the STAMP-2.5D material table (Tin-Lead 60-40, E = 20 GPa, CTE 20.5 ppm/K); Poisson's
ratio is NOT given there and is an ASSUMPTION.

STEP 1  Explicit unit-cell FEA of one solder column in an 800 um cell -> upper-bound
        normal and shear foundation stiffness per unit area.
STEP 2  Sweep the BC-B support-layer modulus across an envelope anchored at that upper
        bound and extending downward, because a real barrel-shaped ball with limited pad
        contact is MORE compliant than a straight column. Report whether the Phase-0C
        architectural ordering survives the whole envelope.

No solder-ball barrel profile is invented. The column is an explicit upper bound and is
labelled as such.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase0b"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from etm.ccxio import read_frd, run_ccx                    # noqa: E402
from etm.config import load_doe, load_stack                # noqa: E402
from etm.run_case import run_case                          # noqa: E402
from homogenization import _grid                           # noqa: E402

R = Path(__file__).resolve().parents[2]
P0B = R / "results" / "phase0b"
OUT = R / "results" / "phase0c" / "support"

# SOURCE_BACKED (June-2026 Table III)
BGA_D_MM, BGA_H_MM, BGA_P_MM = 0.400, 0.300, 0.800
# STAMP-2.5D material table; nu is ASSUMPTION (STAMP omits Poisson ratio entirely)
SOLDER_E_MPA, SOLDER_NU = 20000.0, 0.35


def bga_column_stiffness(workdir: Path) -> dict:
    """Explicit FEA of one equal-area square solder column, base fixed, top loaded.
    Returns foundation stiffness per unit CELL area (N/mm^3) - an upper bound."""
    workdir.mkdir(parents=True, exist_ok=True)
    a = math.sqrt(math.pi * BGA_D_MM ** 2 / 4.0)          # equal-area square side
    n = 6
    xs = _grid([0.0, a], n); ys = xs.copy(); zs = _grid([0.0, BGA_H_MM], n)
    nx, ny, nz = len(xs), len(ys), len(zs)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    nodes = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    nid = lambda i, j, k: (i * ny + j) * nz + k + 1
    elems = [[nid(i, j, k), nid(i+1, j, k), nid(i+1, j+1, k), nid(i, j+1, k),
              nid(i, j, k+1), nid(i+1, j, k+1), nid(i+1, j+1, k+1), nid(i, j+1, k+1)]
             for i in range(nx-1) for j in range(ny-1) for k in range(nz-1)]

    res = {"cell_pitch_mm": BGA_P_MM, "ball_d_mm": BGA_D_MM, "ball_h_mm": BGA_H_MM,
           "equal_area_square_side_mm": a,
           "area_fraction": a * a / (BGA_P_MM ** 2),
           "solder_E_MPa": SOLDER_E_MPA, "solder_nu": SOLDER_NU,
           "geometry_status": "SOURCE_BACKED (June-2026 Table III)",
           "solder_E_status": "SOURCE_BACKED (STAMP-2.5D material table)",
           "solder_nu_status": "ASSUMPTION (not given by STAMP-2.5D)"}

    for tag, dof in (("normal", 3), ("shear", 1)):
        L = ["*NODE"] + [f"{i+1},{p[0]:.9f},{p[1]:.9f},{p[2]:.9f}" for i, p in enumerate(nodes)]
        L.append("*ELEMENT, TYPE=C3D8I, ELSET=EALL")
        for e, row in enumerate(elems, 1):
            L.append(f"{e}," + ",".join(str(v) for v in row))
        L += ["*NSET, NSET=NALL, GENERATE", f"1,{len(nodes)}",
              "*MATERIAL, NAME=SOLDER", "*ELASTIC", f"{SOLDER_E_MPA},{SOLDER_NU}",
              "*SOLID SECTION, ELSET=EALL, MATERIAL=SOLDER"]
        base = np.nonzero(np.abs(nodes[:, 2]) < 1e-9)[0] + 1
        top = np.nonzero(np.abs(nodes[:, 2] - BGA_H_MM) < 1e-9)[0] + 1
        d = 1e-4
        L.append("*BOUNDARY")
        L += [f"{int(nn)},1,3" for nn in base]                 # bonded pad
        L += [f"{int(nn)},{dof},{dof},{d:.9g}" for nn in top]  # rigid pad displacement
        if dof == 1:                                            # shear: hold top plane flat
            L += [f"{int(nn)},3,3,0.0" for nn in top]
        L += ["*NSET, NSET=NTOP"] + [",".join(str(int(v)) for v in top[i:i+8])
                                     for i in range(0, len(top), 8)]
        L += ["*STEP", "*STATIC", "*NODE PRINT, NSET=NTOP", "RF", "*END STEP"]
        job = workdir / f"bga_{tag}.inp"
        job.write_text("\n".join(L) + "\n")
        run_ccx(job, threads=4)
        dat = (workdir / f"bga_{tag}.dat").read_text()
        blk = dat.split("forces")[-1].strip().splitlines()
        rows = [l.split() for l in blk if l.strip() and l.split()[0].lstrip("-").isdigit()]
        F = sum(float(r[dof]) for r in rows)
        k = abs(F) / (d * BGA_P_MM ** 2)                        # N/mm per mm^2 of cell
        res[f"k_{tag}_N_per_mm3"] = float(k)
        res[f"k_{tag}_analytic_N_per_mm3"] = float(
            (SOLDER_E_MPA if dof == 3 else SOLDER_E_MPA / (2 * (1 + SOLDER_NU)))
            * res["area_fraction"] / BGA_H_MM)
    return res


def main():
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((P0B / "cooling_calibration.json").read_text())["h_top_W_m2K"]
    OUT.mkdir(parents=True, exist_ok=True)

    cal = bga_column_stiffness(OUT / "unit_cell")
    print(json.dumps(cal, indent=2))
    (OUT / "bga_unit_cell.json").write_text(json.dumps(cal, indent=2))

    # BC-B support layer of thickness t behaves as k_z ~ E/t. Anchor the envelope at the
    # column upper bound and extend downward, since a real ball is more compliant.
    t_sup = BGA_H_MM
    E_upper = cal["k_normal_N_per_mm3"] * t_sup
    envelope = [("E/64_very_compliant", E_upper / 64), ("E/16_compliant", E_upper / 16),
                ("E/4_moderate", E_upper / 4), ("E_upper_bound_column", E_upper)]
    print(f"\nBC-B support-layer modulus envelope (t = {t_sup} mm):")
    for tag, E in envelope:
        print(f"  {tag:24s} E = {E:9.1f} MPa   -> k_z = {E/t_sup:9.1f} N/mm^3")

    cases = ["C05", "C07", "C13", "C08"]
    rows = []
    for tag, E in envelope:
        st = json.loads(json.dumps(stack))
        st["structural_bc"]["variants"]["BC_B"]["E"]["value"] = float(E)
        st["structural_bc"]["variants"]["BC_B"]["thickness"]["value"] = t_sup
        for cid in cases:
            r = run_case(cid, st, doe, OUT / f"{tag}_{cid}", h_top=h_top, bc="BC_B",
                         threads=32, solver="", h_xy=0.45, z_scale=1.0, h_max_factor=4.0)
            rows.append({"envelope": tag, "E_support_MPa": round(E, 2),
                         "k_z_N_per_mm3": round(E / t_sup, 2), "case": cid,
                         "die_warpage_pv_um": r["structural"]["die_warpage_pv_um"],
                         "pkg_warpage_pv_um": r["structural"]["pkg_warpage_pv_um"],
                         "si_principal_p99_MPa": r["structural"]["si_principal_MPa"]["p99"],
                         "interface_shear_p99_MPa": r["structural"]["interface_shear_MPa"]["p99"],
                         "T_max_C": r["thermal"]["T_max_C"], "n_elems": r["mesh"]["n_elems"]})
            print(f"  {tag:24s} {cid}  die_w={rows[-1]['die_warpage_pv_um']:8.4f}um  "
                  f"si99={rows[-1]['si_principal_p99_MPa']:7.3f}  "
                  f"tau99={rows[-1]['interface_shear_p99_MPa']:6.3f}", flush=True)

    p = OUT.parent / "support_envelope_runs.csv"
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    print(f"\n{'envelope':26s}{'placement S %':>15s}{'order C05<C07':>15s}"
          f"{'thickness S %':>16s}{'order C08<C05':>15s}")
    print("-" * 90)
    summary = []
    for tag, _ in envelope:
        g = {r["case"]: r for r in rows if r["envelope"] == tag}
        a, b, c8 = (g["C05"]["die_warpage_pv_um"], g["C07"]["die_warpage_pv_um"],
                    g["C08"]["die_warpage_pv_um"])
        s_pl = 100 * (b - a) / a
        s_th = 100 * (a - c8) / a
        summary.append({"envelope": tag, "placement_S_pct": round(s_pl, 2),
                        "placement_order_ok": bool(b > a),
                        "thickness_S_pct": round(s_th, 2),
                        "thickness_order_ok": bool(c8 < a)})
        print(f"{tag:26s}{s_pl:14.2f}%{str(b > a):>15s}{s_th:15.2f}%{str(c8 < a):>15s}")

    (OUT.parent / "support_envelope_summary.json").write_text(json.dumps(
        {"calibration": cal, "envelope": summary}, indent=2))
    print(f"\nwrote {p}")


if __name__ == "__main__":
    main()
