"""Matched thermal benchmark: CalculiX (production) vs MOOSE 3-D FEM, same unit cell.

The problem is column_spec() of thermal_column_benchmark: one interior cell of the
physical package with every layer, the tile and gap materials, the converged heat map,
the cold-plate film (and board film for Z1) and adiabatic symmetry sides. MOOSE solves it
on its OWN structured hex meshes at two resolutions, so the comparison is code-to-code
and shows the reference's own mesh dependence. Units: mm, W, K.

Timing follows the declared methodology: one untimed warm-up solve, then three timed
repeats on the same machine; the median and range are reported together with the load
average, because this host is shared.
"""
from __future__ import annotations

import csv
import json
import math
import os
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import thermal_column_benchmark as TC                               # noqa: E402

R = TC.R
OUT = R / "research" / "final_closure"
MOOSE = Path("/home/beams0/LPOPRYHO/projects/moose/modules/heat_transfer/heat_transfer-opt")
EVID = R / "presentation" / "prelim_hvr" / "tool_evidence"
REPEATS = 3
CCX_MESH = (6, 24, 0.04)                       # production-fine column of the AEDT benchmark
MOOSE_MESHES = {"m1": (5, 20, 0.05), "m2": (8, 32, 0.025)}


def _axes(spec, n_gap, n_tile, dz_max, cap):
    p, s = spec["pitch_mm"], spec["tile_mm"]
    xs = np.unique(np.concatenate([np.linspace(-p / 2, -s / 2, n_gap + 1),
                                   np.linspace(-s / 2, s / 2, n_tile + 1),
                                   np.linspace(s / 2, p / 2, n_gap + 1)]))
    zs, zl = [spec["layers"][0]["z0"]], []
    for i, L in enumerate(spec["layers"]):
        n = max(1, min(cap, int(math.ceil((L["z1"] - L["z0"]) / dz_max))))
        zs += np.linspace(L["z0"], L["z1"], n + 1)[1:].tolist()
        zl += [i] * n
    return xs, np.array(zs), zl


def write_msh(spec, path, n_gap, n_tile, dz_max):
    """gmsh 2.2 hex mesh; one block per (layer, tile|gap); sidesets top/bottom."""
    s = spec["tile_mm"]
    xs, zs, zl = _axes(spec, n_gap, n_tile, dz_max, cap=12)
    nx, nz = len(xs), len(zs)
    nid = lambda i, j, k: 1 + i + nx * (j + nx * k)
    groups, elems, quads, used = {}, [], [], set()
    for k in range(nz - 1):
        L = spec["layers"][zl[k]]
        for j in range(nx - 1):
            for i in range(nx - 1):
                xc, yc = 0.5 * (xs[i] + xs[i + 1]), 0.5 * (xs[j] + xs[j + 1])
                tile = abs(xc) < s / 2 and abs(yc) < s / 2
                if (L["mat_tile"] if tile else L["mat_gap"]) is None:
                    continue
                key = f"{L['name']}__{'tile' if tile else 'gap'}"
                gid = groups.setdefault(key, len(groups) + 3)
                lo = [nid(i, j, k), nid(i + 1, j, k), nid(i + 1, j + 1, k), nid(i, j + 1, k)]
                hi = [n + nx * nx for n in lo]
                elems.append((gid, lo + hi))
                used.update(lo + hi)
                if k == nz - 2:
                    quads.append((1, hi))
                if k == 0:
                    quads.append((2, [lo[0], lo[3], lo[2], lo[1]]))
    new = {n: q + 1 for q, n in enumerate(sorted(used))}     # drop orphan nodes
    out = ["$MeshFormat", "2.2 0 8", "$EndMeshFormat", "$PhysicalNames",
           str(2 + len(groups)), '2 1 "top"', '2 2 "bottom"']
    out += [f'3 {g} "{k}"' for k, g in groups.items()]
    out += ["$EndPhysicalNames", "$Nodes", str(len(new))]
    for n in sorted(used):
        q = n - 1
        i, j, k = q % nx, (q // nx) % nx, q // (nx * nx)
        out.append(f"{new[n]} {xs[i]:.9g} {xs[j]:.9g} {zs[k]:.9g}")
    out += ["$EndNodes", "$Elements", str(len(quads) + len(elems))]
    e = 0
    for g, nn in quads:
        e += 1
        out.append(f"{e} 3 2 {g} {g} " + " ".join(str(new[n]) for n in nn))
    for g, nn in elems:
        e += 1
        out.append(f"{e} 5 2 {g} {g} " + " ".join(str(new[n]) for n in nn))
    out += ["$EndElements"]
    path.write_text("\n".join(out) + "\n")
    return groups, len(elems), len(new)


def moose_input(spec, groups, msh_name):
    p, s = spec["pitch_mm"], spec["tile_mm"]
    lay = {L["name"]: L for L in spec["layers"]}

    def vol(key):
        lname, reg = key.split("__")
        L = lay[lname]
        return (s * s if reg == "tile" else p * p - s * s) * (L["z1"] - L["z0"])

    mats, pps, ks = [], [], []
    for key in groups:
        lname, reg = key.split("__")
        mm = spec["materials"][lay[lname]["mat_tile" if reg == "tile" else "mat_gap"]]
        kx, ky, kz = ([v * 1e-3 for v in mm["k_ortho"]] if mm["k_ortho"]
                      else [mm["k"] * 1e-3] * 3)
        mats.append(f"""  [m_{key}]
    type = AnisoHeatConductionMaterial
    block = '{key}'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '{kx:.12e} 0 0 0 {ky:.12e} 0 0 0 {kz:.12e}'
  []""")
        pps.append(f"""  [avg_{key}]
    type = ElementAverageValue
    variable = T
    block = '{key}'
  []""")
    deposited = 0.0
    for q, sr in enumerate(spec["sources"]):
        blocks = [k for k in groups if k.split("__")[0] in sr["layers"]
                  and (k.endswith("__tile") or not sr["in_tile"])]
        if not blocks:
            continue
        V = sum(vol(b) for b in blocks)
        deposited += sr["W"]
        ks.append(f"""  [src{q}]
    type = BodyForce
    variable = T
    value = {sr['W'] / V:.12e}
    block = '{" ".join(blocks)}'
  []""")
    bcs = [f"""  [top]
    type = ConvectiveHeatFluxBC
    variable = T
    boundary = top
    T_infinity = {spec['T_fluid_C']:.9g}
    heat_transfer_coefficient = {spec['h_top'] * 1e-6:.12e}
  []"""]
    if spec["bottom_film"]:
        bcs.append(f"""  [bot]
    type = ConvectiveHeatFluxBC
    variable = T
    boundary = bottom
    T_infinity = {spec['T_amb_C']:.9g}
    heat_transfer_coefficient = {spec['h_bot'] * 1e-6:.12e}
  []""")
    nl = "\n"
    return deposited, f"""[Mesh]
  [f]
    type = FileMeshGenerator
    file = {msh_name}
  []
[]
[Variables]
  [T]
    initial_condition = {spec['T_fluid_C']:.6g}
  []
[]
[Kernels]
  [cond]
    type = AnisoHeatConduction
    variable = T
  []
{nl.join(ks)}
[]
[Materials]
{nl.join(mats)}
[]
[BCs]
{nl.join(bcs)}
[]
[Executioner]
  type = Steady
  solve_type = NEWTON
  line_search = none
  petsc_options_iname = '-pc_type -pc_hypre_type'
  petsc_options_value = 'hypre boomeramg'
  l_tol = 1e-11
  l_max_its = 300
  nl_rel_tol = 1e-9
  nl_abs_tol = 1e-30
  nl_max_its = 5
[]
[Postprocessors]
  [Tmax]
    type = NodalExtremeValue
    variable = T
  []
{nl.join(pps)}
[]
[Outputs]
  csv = true
  exodus = true
[]
"""


def _load():
    return [round(x, 1) for x in os.getloadavg()]


def _stats(walls):
    return {"median_s": statistics.median(walls), "min_s": min(walls), "max_s": max(walls),
            "repeats": len(walls), "walls_s": walls}


def run_moose(spec, wd, mesh):
    wd.mkdir(parents=True, exist_ok=True)
    groups, n_el, n_nd = write_msh(spec, wd / "column.msh", *mesh)
    deposited, inp = moose_input(spec, groups, "column.msh")
    (wd / "column.i").write_text(inp)
    walls, last = [], None
    for rep in range(REPEATS + 1):                        # rep 0 = warm-up, untimed
        for f in wd.glob("column_out*"):
            f.unlink()
        t0 = time.time()
        r = subprocess.run([str(MOOSE), "-i", "column.i"], cwd=wd, capture_output=True,
                           text=True)
        dt = time.time() - t0
        csvs = sorted(wd.glob("column_out*.csv"))
        if r.returncode != 0 or not csvs:
            raise RuntimeError(r.stdout[-2000:] + r.stderr[-1000:])
        if rep:
            walls.append(dt)
        last = list(csv.DictReader(csvs[-1].open()))[-1]
        (wd / "log_tail.txt").write_text(r.stdout[-3000:])
    means = {k[4:].replace("__", ":"): float(v) for k, v in last.items()
             if k.startswith("avg_")}
    return {"T_max_C": float(last["Tmax"]), "means": means, "n_elems": n_el,
            "n_nodes": n_nd, "mesh": list(mesh), "deposited_W": deposited,
            "timing": _stats(walls)}


def run_ccx(spec, wd):
    walls, res = [], None
    for rep in range(REPEATS + 1):
        res = TC.ccx_column(spec, *CCX_MESH, wd)
        if rep:
            walls.append(res["wall_s"])
    res["timing"] = _stats(walls)
    res["mesh"] = list(CCX_MESH)
    res["threads"] = TC.CCX_THREADS
    return res


def main():
    arch = sys.argv[1] if len(sys.argv) > 1 else "Z2"
    stage = f"thermal_column_moose_{arch}"
    spec = TC.column_spec(arch, "HV_S0")
    load0 = _load()
    ccx = run_ccx(spec, Path(f"/tmp/col_ccx_{arch}_f"))
    mo = {tag: run_moose(spec, Path(f"/tmp/col_moose_{arch}_{tag}"), mesh)
          for tag, mesh in MOOSE_MESHES.items()}
    ref = mo["m2"]
    common = sorted(set(ccx["means"]) & set(ref["means"]))
    errs = {k: ccx["means"][k] - ref["means"][k] for k in common}
    rise = ref["T_max_C"] - spec["T_fluid_C"]
    res = {"stage": stage, "scenario": "HV_S0",
           "spec": {k: v for k, v in spec.items() if k != "materials"},
           "ccx": ccx, "moose": mo,
           "T_max_err_K": ccx["T_max_C"] - ref["T_max_C"],
           "T_rise_rel_err": (ccx["T_max_C"] - ref["T_max_C"]) / rise,
           "moose_mesh_change_K": mo["m2"]["T_max_C"] - mo["m1"]["T_max_C"],
           "layer_mean_err_K": errs,
           "max_abs_layer_err_K": max(abs(v) for v in errs.values()) if errs else None,
           "speedup_ccx_vs_moose_median": ref["timing"]["median_s"] / ccx["timing"]["median_s"],
           "cores": {"ccx_threads": TC.CCX_THREADS, "moose_mpi_ranks": 1},
           "load_average": {"before": load0, "after": _load()},
           "timing_method": f"1 warm-up + {REPEATS} timed repeats, median and range"}
    (OUT / f"reference_{stage}.json").write_text(json.dumps(res, indent=1, default=float))
    d = EVID / stage
    d.mkdir(parents=True, exist_ok=True)
    wd = Path(f"/tmp/col_moose_{arch}_m2")
    for f in ("column.i", "log_tail.txt"):
        shutil.copy(wd / f, d / f)
    print(json.dumps({k: res[k] for k in ("T_max_err_K", "T_rise_rel_err",
                                          "moose_mesh_change_K", "max_abs_layer_err_K",
                                          "speedup_ccx_vs_moose_median")}, default=float))
    print("ccx %.4f  moose m1 %.4f  m2 %.4f" % (ccx["T_max_C"], mo["m1"]["T_max_C"],
                                                mo["m2"]["T_max_C"]))


if __name__ == "__main__":
    main()
