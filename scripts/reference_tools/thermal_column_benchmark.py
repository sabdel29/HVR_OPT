"""Matched thermal benchmark: CalculiX (production) vs AEDT Mechanical thermal (FEM).

THE PROBLEM, IDENTICAL IN BOTH SOLVERS. One interior unit cell of the physical
package -- the 3.165 mm cell pitch, the 2.3685 mm converter tile at its centre, and
every layer of the physical stack with the materials the production mesh assigns in
the tile and in the gap. Sources are the converged E-T heat map of the named case
divided by 49, deposited in the same tiers. The top carries the cold-plate film
(uniform h and fluid temperature), the board underside its film for Z1, and the four
sides are adiabatic (symmetry for an interior cell). Z2's interior cell has no board
below it -- it sits in the cutout -- so its underside is adiabatic, exactly as in the
full package.

What this establishes: that the production conduction FE (CalculiX C3D8 on a
structured hex mesh) reproduces an independent commercial FE solver (AEDT 2026 R1
Mechanical, tetrahedral) on the same layered, heterogeneous, source-carrying problem.
It is solver verification on a matched problem, not experimental validation.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aedt_common as C                                              # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hvr_scratch import path as scratch                             # noqa: E402

R = C.R
for _p in ("scripts/phase0nw", "scripts/phase0m", "scripts/phase0mr", "scripts/phase0i",
           "scripts/phase0g", "scripts/phase0b", "scripts"):
    sys.path.insert(0, str(R / _p))
OUT = R / "research" / "final_closure"
CCX_THREADS = 8
AEDT_CORES = 4            # >4 cores needs HPC licences: 8-core solves fail


def column_spec(arch, scen):
    import final_closure_physical_etm as E
    import final_closure_ledger as FL
    import physical_coords as PCO
    m, mats, st, tiles, _ = E.build(arch)
    et = json.loads((OUT / f"etm_{arch}_{scen}_h1.1.json").read_text())
    p = PCO.cell_pitch_mm() if hasattr(PCO, "cell_pitch_mm") else 3.165243
    s = tiles[0].ax
    t0 = min(tiles, key=lambda t: t.cx ** 2 + t.cy ** 2)
    cen = m.elem_centroids()
    layers = sorted(m.layers, key=lambda L: L.z0)
    seen, spec = set(), []
    for L in layers:
        if L.name in seen:
            continue
        seen.add(L.name)
        ids = m.elem_set(layer=L.name)
        c = cen[ids - 1]
        def mat_at(dx, dy):
            d = np.hypot(c[:, 0] - (t0.cx + dx), c[:, 1] - (t0.cy + dy))
            j = int(np.argmin(d))
            return str(m.elem_material[ids[j] - 1]) if d[j] < 0.6 else None
        z0 = min(LL.z0 for LL in m.layers if LL.name == L.name)
        z1 = max(LL.z1 for LL in m.layers if LL.name == L.name)
        spec.append({"name": L.name, "z0": z0, "z1": z1,
                     "mat_tile": mat_at(0.0, 0.0),
                     "mat_gap": mat_at(0.46 * p, 0.46 * p)})
    spec = [r for r in spec if r["mat_tile"] or r["mat_gap"]]
    # sources per cell, in the same tiers as the full-package deposition. A tier absent
    # from an interior cell (Z2's BGA field lies outside the cutout) carries no source
    # here -- in the package that loss is deposited at the periphery, not in this cell --
    # and it is listed, never silently dropped.
    dep = E.deposits_from_ledger(arch, {"rows": et["ledger_rows"]})
    have = {r["name"]: r for r in spec}
    src, omitted = [], []
    for (lays, in_tiles), w in dep.items():
        hosts = [n for n in lays if n in have
                 and (have[n]["mat_tile"] or (not in_tiles and have[n]["mat_gap"]))]
        (src if hosts else omitted).append(
            {"layers": list(lays), "in_tile": bool(in_tiles), "W": w / 49.0})
    from cooling_production import CANDIDATES
    cooler = CANDIDATES["TOP_SI_MICROCHANNEL_27"]
    Q = sum(dep.values())
    import production_et as PE
    m_dot = cooler.m_dot_g_s * 1e-3
    t_f = cooler.t_in_c + 0.5 * Q / (m_dot * PE.CP_F)
    tb = st["thermal_bc"]
    return {"arch": arch, "scenario": scen, "pitch_mm": p, "tile_mm": s,
            "layers": spec, "sources": src, "omitted_sources": omitted,
            "Q_cell_W": sum(x["W"] for x in src),
            "h_top": cooler.h_uniform(Q), "T_fluid_C": t_f,
            "h_bot": tb["h_bottom"]["value"], "T_amb_C": tb["ambient_bottom"]["value"],
            "bottom_film": arch == "Z1",
            "materials": {k: {"k": v.k, "k_ortho": v.k_ortho} for k, v in mats.items()}}


# ------------------------- CalculiX on a structured column ---------------------
def ccx_column(spec, n_gap=3, n_tile=12, dz_max=0.08, wd=None):
    wd = wd or scratch("col_ccx")
    wd.mkdir(parents=True, exist_ok=True)
    p, s = spec["pitch_mm"], spec["tile_mm"]
    xs = np.unique(np.concatenate([np.linspace(-p / 2, -s / 2, n_gap + 1),
                                   np.linspace(-s / 2, s / 2, n_tile + 1),
                                   np.linspace(s / 2, p / 2, n_gap + 1)]))
    zs, zlay = [spec["layers"][0]["z0"]], []
    for i, L in enumerate(spec["layers"]):
        n = max(1, min(10, int(math.ceil((L["z1"] - L["z0"]) / dz_max))))
        zz = np.linspace(L["z0"], L["z1"], n + 1)[1:]
        zs.extend(zz.tolist())
        zlay.extend([i] * n)
    zs = np.array(zs)
    nx = ny = len(xs); nz = len(zs)
    nid = lambda i, j, k: 1 + i + nx * (j + ny * k)
    nodes = [(nid(i, j, k), xs[i], xs[j], zs[k]) for k in range(nz)
             for j in range(ny) for i in range(nx)]
    elems, emat, elay, intile, vol = [], [], [], [], []
    e = 0
    for k in range(nz - 1):
        L = spec["layers"][zlay[k]]
        for j in range(ny - 1):
            for i in range(nx - 1):
                xc, yc = 0.5 * (xs[i] + xs[i + 1]), 0.5 * (xs[j] + xs[j + 1])
                inside = abs(xc) < s / 2 and abs(yc) < s / 2
                mat = L["mat_tile"] if inside else L["mat_gap"]
                if mat is None:
                    continue
                e += 1
                n1, n2 = nid(i, j, k), nid(i + 1, j, k)
                n3, n4 = nid(i + 1, j + 1, k), nid(i, j + 1, k)
                elems.append((e, n1, n2, n3, n4, n1 + nx * ny, n2 + nx * ny,
                              n3 + nx * ny, n4 + nx * ny))
                emat.append(mat); elay.append(L["name"]); intile.append(inside)
                vol.append((xs[i + 1] - xs[i]) * (xs[j + 1] - xs[j]) * (zs[k + 1] - zs[k]))
    emat, elay, intile, vol = map(np.array, (emat, elay, intile, vol))
    lines = ["*NODE"] + [f"{n},{x:.9g},{y:.9g},{z:.9g}" for n, x, y, z in nodes]
    for mat in sorted(set(emat)):
        lines.append(f"*ELEMENT, TYPE=C3D8, ELSET=E_{mat.upper()}")
        lines += [",".join(map(str, el)) for el, mm in zip(elems, emat) if mm == mat]
    for mat in sorted(set(emat)):
        mm = spec["materials"][mat]
        lines.append(f"*MATERIAL, NAME={mat.upper()}")
        if mm["k_ortho"]:
            kx, ky, kz = (v * 1e-3 for v in mm["k_ortho"])
            lines += ["*CONDUCTIVITY, TYPE=ORTHO", f"{kx:.9g},{ky:.9g},{kz:.9g}"]
        else:
            lines += ["*CONDUCTIVITY", f"{mm['k'] * 1e-3:.9g}"]
        lines.append(f"*SOLID SECTION, ELSET=E_{mat.upper()}, MATERIAL={mat.upper()}")
    dflux, dep = [], 0.0
    for q, sr in enumerate(spec["sources"]):
        sel = np.isin(elay, sr["layers"]) & (intile if sr["in_tile"] else True)
        ids = [elems[i][0] for i in np.where(sel)[0]]
        V = vol[sel].sum()
        lines.append(f"*ELSET, ELSET=E_SRC_{q}")
        lines += [",".join(map(str, ids[a:a + 16])) for a in range(0, len(ids), 16)]
        dflux.append(f"E_SRC_{q},BF,{sr['W'] / V:.9g}")
        dep += sr["W"]
    top = [el[0] for el in elems if el[5] > nx * ny * (nz - 1)]     # nodes 5-8 on z_top
    bot = [el[0] for el in elems if el[1] <= nx * ny]
    lines += ["*STEP", "*HEAT TRANSFER, STEADY STATE", "*DFLUX"] + dflux + ["*FILM"]
    lines += [f"{e_},F2,{spec['T_fluid_C']:.6f},{spec['h_top'] * 1e-6:.9g}" for e_ in top]
    if spec["bottom_film"]:
        lines += [f"{e_},F1,{spec['T_amb_C']:.6f},{spec['h_bot'] * 1e-6:.9g}" for e_ in bot]
    lines += ["*NODE FILE", "NT", "*END STEP"]
    inp = wd / "col.inp"
    inp.write_text("\n".join(lines) + "\n")
    env = dict(os.environ, OMP_NUM_THREADS=str(CCX_THREADS))
    t0 = time.time()
    subprocess.run(["ccx", "col"], cwd=wd, env=env, capture_output=True, check=True)
    wall = time.time() - t0
    import production_et as PE
    T = PE.ccxio.read_frd(wd / "col.frd")["NDTEMP"][1:len(nodes) + 1, 0]
    el_T = np.array([T[np.array(el[1:]) - 1].mean() for el in elems])
    means = {}
    for name in sorted(set(elay)):
        for tag, mask in (("tile", intile), ("gap", ~intile)):
            sel = (elay == name) & mask
            if sel.any():
                means[f"{name}:{tag}"] = float(np.sum(el_T[sel] * vol[sel]) / vol[sel].sum())
    return {"T_max_C": float(T.max()), "means": means, "wall_s": wall,
            "n_elems": len(elems), "n_nodes": len(nodes), "deposited_W": dep}


# ------------------------------ AEDT reference ---------------------------------
def aedt_column(spec, stage):
    from ansys.aedt.core import Mechanical
    me = C.launch(Mechanical, f"col_{spec['arch']}_{spec['scenario']}", "column",
                  solution_type="Thermal")
    me.modeler.model_units = "mm"
    p, s = spec["pitch_mm"], spec["tile_mm"]
    made = set()
    for name, mm in spec["materials"].items():
        if name in {L["mat_tile"] for L in spec["layers"]} | {L["mat_gap"] for L in spec["layers"]}:
            mat = me.materials.add_material(f"m_{name}")
            if mm["k_ortho"]:
                mat.thermal_conductivity = [float(v) for v in mm["k_ortho"]]
            else:
                mat.thermal_conductivity = float(mm["k"])
            made.add(name)
    bodies = {}
    for i, L in enumerate(spec["layers"]):
        t = L["z1"] - L["z0"]
        if L["mat_tile"] == L["mat_gap"]:
            b = me.modeler.create_box([-p / 2, -p / 2, L["z0"]], [p, p, t],
                                      name=f"L{i}_all", material=f"m_{L['mat_tile']}")
            bodies[(L["name"], "all")] = b.name
            continue
        if L["mat_tile"]:
            b = me.modeler.create_box([-s / 2, -s / 2, L["z0"]], [s, s, t],
                                      name=f"L{i}_tile", material=f"m_{L['mat_tile']}")
            bodies[(L["name"], "tile")] = b.name
        if L["mat_gap"]:
            g = me.modeler.create_box([-p / 2, -p / 2, L["z0"]], [p, p, t],
                                      name=f"L{i}_gap", material=f"m_{L['mat_gap']}")
            cut = me.modeler.create_box([-s / 2, -s / 2, L["z0"]], [s, s, t], name=f"L{i}_cut")
            me.modeler.subtract(g.name, cut.name, keep_originals=False)
            bodies[(L["name"], "gap")] = g.name
    # thin tiers (10 um over a 3.165 mm cell) need an explicit length-based mesh
    thin = [b for (ln, tag), b in bodies.items()
            if next(L["z1"] - L["z0"] for L in spec["layers"] if L["name"] == ln) < 0.05]
    if thin:
        try:
            me.mesh.assign_length_mesh(thin, maximum_length=0.15, maximum_elements=None,
                                       name="thin_tiers")
        except Exception as e:
            print("length mesh failed:", str(e)[:150])
    for q, sr in enumerate(spec["sources"]):
        names = []
        for ln in sr["layers"]:
            for tag in (("tile",) if sr["in_tile"] else ("tile", "gap", "all")):
                if (ln, tag) in bodies:
                    names.append(bodies[(ln, tag)])
                elif (ln, "all") in bodies and sr["in_tile"]:
                    names.append(bodies[(ln, "all")])
        # split W by body volume so the volumetric density matches the CalculiX deck
        vols = {nm: me.modeler[nm].volume for nm in names}
        Vt = sum(vols.values())
        for nm in names:
            me.assign_heat_generation([nm], value=f"{sr['W'] * vols[nm] / Vt:.9g}W")
    ztop = spec["layers"][-1]["z1"]
    top_faces = [me.modeler.get_faceid_from_position([0.1, 0.1, ztop], assignment=b)
                 for (ln, tag), b in bodies.items() if ln == spec["layers"][-1]["name"]]
    me.assign_uniform_convection([f for f in top_faces if f], convection_value=spec["h_top"],
                                 temperature=f"{spec['T_fluid_C']:.6f}cel")
    if spec["bottom_film"]:
        zb = spec["layers"][0]["z0"]
        bf = [me.modeler.get_faceid_from_position([0.1, 0.1, zb], assignment=b)
              for (ln, tag), b in bodies.items() if ln == spec["layers"][0]["name"]]
        me.assign_uniform_convection([f for f in bf if f], convection_value=spec["h_bot"],
                                     temperature=f"{spec['T_amb_C']:.6f}cel")
    C.try_image(me, C.EVID / stage / "01_geometry.png")
    me.create_setup("S1")
    me.save_project()
    diag = {"validate": None, "errors": []}
    try:
        diag["validate"] = bool(me.odesign.ValidateDesign())
        diag["errors"] = [m_[:240] for m_ in me.odesktop.GetMessages(
            me.project_name, me.design_name, 0) if "[error]" in m_.lower()
            and "license" not in m_.lower()]
    except Exception as e:
        diag["errors"].append("diag failed: " + str(e)[:120])
    print("AEDT_DIAG", json.dumps(diag), flush=True)
    t0 = time.time()
    ok = me.analyze_setup("S1", cores=AEDT_CORES)          # warm-up solve, also the result
    wall = time.time() - t0
    tmax = me.post.get_scalar_field_value("Temp", scalar_function="Maximum",
                                          object_name="AllObjects", object_type="volume")
    means = {}
    for (ln, tag), b in bodies.items():
        try:
            means[f"{ln}:{tag}"] = float(me.post.get_scalar_field_value(
                "Temp", scalar_function="Mean", object_name=b, object_type="volume"))
        except Exception:
            pass
    walls = []
    for _ in range(3):                    # timed repeats: mesh and solution cleared first
        me.cleanup_solution()
        t1 = time.time()
        me.analyze_setup("S1", cores=AEDT_CORES)
        walls.append(time.time() - t1)
    tmax_repeat = me.post.get_scalar_field_value("Temp", scalar_function="Maximum",
                                                 object_name="AllObjects",
                                                 object_type="volume")
    fp = C.try_field_plot(me, list(bodies.values()))
    if fp:
        C.try_image(me, C.EVID / stage / "04_field.png", plot=fp)
    me.release_desktop(True, True)
    return {"T_max_C": float(tmax), "means": means, "wall_s": wall, "solved": bool(ok),
            "cores": AEDT_CORES, "T_max_repeat_C": float(tmax_repeat),
            "timing": {"median_s": float(np.median(walls)), "min_s": min(walls),
                       "max_s": max(walls), "repeats": len(walls), "walls_s": walls,
                       "includes": "meshing + solve, solution cleared before each"}}


def main():
    arch, scen = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("Z2", "HV_S0")
    stage = f"thermal_column_{arch}"
    spec = column_spec(arch, scen)
    coarse = ccx_column(spec, 3, 12, 0.08, scratch(f"col_ccx_{arch}_c"))
    walls, fine = [], None
    for rep in range(4):                                   # warm-up + 3 timed repeats
        fine = ccx_column(spec, 6, 24, 0.04, scratch(f"col_ccx_{arch}_f"))
        if rep:
            walls.append(fine["wall_s"])
    fine["timing"] = {"median_s": float(np.median(walls)), "min_s": min(walls),
                      "max_s": max(walls), "repeats": len(walls), "walls_s": walls}
    load0 = [round(x, 1) for x in os.getloadavg()]
    ref = aedt_column(spec, stage)
    common = sorted(set(fine["means"]) & set(ref["means"]))
    errs = {k: fine["means"][k] - ref["means"][k] for k in common}
    res = {"stage": stage, "spec": {k: v for k, v in spec.items() if k != "materials"},
           "ccx_coarse": coarse, "ccx_fine": fine, "aedt": ref,
           "T_max_err_K": fine["T_max_C"] - ref["T_max_C"],
           "T_rise_rel_err": (fine["T_max_C"] - ref["T_max_C"])
                             / (ref["T_max_C"] - spec["T_fluid_C"]),
           "layer_mean_err_K": errs,
           "max_abs_layer_err_K": max(abs(v) for v in errs.values()) if errs else None,
           "ccx_mesh_change_K": fine["T_max_C"] - coarse["T_max_C"],
           "speedup_ccx_fine_vs_aedt": (ref["timing"]["median_s"]
                                        / fine["timing"]["median_s"]),
           "load_average": {"before_aedt": load0,
                            "after": [round(x, 1) for x in os.getloadavg()]},
           "threads": {"ccx": CCX_THREADS, "aedt_cores": AEDT_CORES},
           "hardware": C.hardware()}
    (OUT / f"reference_{stage}.json").write_text(json.dumps(res, indent=1, default=float))
    C.write_evidence(stage, res["spec"], {"ccx_fine": fine["timing"],
                                          "aedt": ref["timing"],
                                          "cores": res["threads"],
                                          "load_average": res["load_average"],
                                          "hardware": C.hardware()},
                     {k: res[k] for k in ("T_max_err_K", "T_rise_rel_err",
                                          "max_abs_layer_err_K", "ccx_mesh_change_K")},
                     f"# {stage}\n\nMatched unit-cell thermal problem, CalculiX C3D8 vs AEDT "
                     f"2026 R1 Mechanical thermal. Same layers, materials, sources, films; "
                     f"adiabatic sides. Images are exported from the AEDT session itself.\n")
    print(json.dumps({k: res[k] for k in ("T_max_err_K", "T_rise_rel_err",
                                          "max_abs_layer_err_K", "ccx_mesh_change_K",
                                          "speedup_ccx_fine_vs_aedt")}, default=float))
    print("ccx fine Tmax %.3f  aedt Tmax %.3f" % (fine["T_max_C"], ref["T_max_C"]))


if __name__ == "__main__":
    main()
