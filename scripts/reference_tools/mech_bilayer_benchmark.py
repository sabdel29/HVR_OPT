"""Matched thermoelastic benchmark: CalculiX C3D8I (production) vs AEDT Mechanical.

The mechanism every warpage result in the paper rests on is CTE-mismatch bending of
bonded layers. This solves the same quarter-symmetric silicon-on-organic bilayer in
both solvers -- same geometry, E, nu, CTE, stress-free temperature, uniform
temperature change, and the same MINIMAL supports (symmetry on x=0 and y=0, one
small patch restrained in z), so the supports remove rigid-body motion without
suppressing thermal bending -- and compares the peak-to-valley warpage of the top
surface. The Timoshenko bimaterial curvature is reported as a third, closed-form
check (it ignores free-edge effects, so agreement within a few percent is expected,
not identity).
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
OUT = R / "research" / "final_closure"
L_HALF = 5.0                 # mm, quarter of a 10 x 10 mm plate
H1, H2 = 0.300, 0.300        # mm: silicon on organic
E1, NU1, A1 = 169e3, 0.28, 2.6e-6      # silicon (MPa)
E2, NU2, A2 = 20e3, 0.30, 30.0e-6      # organic build-up (interconnect.py constants)
T_REF, T_HOT = 22.0, 122.0
PATCH = 0.10                 # mm, z-restrained patch at the plate centre


def timoshenko_warp():
    e1, e2 = E1 / (1 - NU1), E2 / (1 - NU2)          # biaxial moduli
    m, n = H1 / H2, e1 / e2
    h = H1 + H2
    k = (6 * (A2 - A1) * (T_HOT - T_REF) * (1 + m) ** 2
         / (h * (3 * (1 + m) ** 2 + (1 + m * n) * (m ** 2 + 1 / (m * n)))))
    r2 = 2 * L_HALF ** 2                              # centre to corner, squared
    return {"curvature_per_mm": k, "warp_pv_mm": k * r2 / 2.0}


def ccx_bilayer(n_xy=40, n_z=8, wd=None):
    wd = wd or scratch("mech_ccx")
    wd.mkdir(parents=True, exist_ok=True)
    xs = np.linspace(0, L_HALF, n_xy + 1)
    zs = np.unique(np.concatenate([np.linspace(0, H2, n_z + 1),
                                   np.linspace(H2, H2 + H1, n_z + 1)]))
    nx, nz = len(xs), len(zs)
    nid = lambda i, j, k: 1 + i + nx * (j + nx * k)
    L = ["*NODE"]
    for k in range(nz):
        for j in range(nx):
            for i in range(nx):
                L.append(f"{nid(i, j, k)},{xs[i]:.9g},{xs[j]:.9g},{zs[k]:.9g}")
    e, sets = 0, {"SI": [], "ORG": []}
    els = []
    for k in range(nz - 1):
        mat = "SI" if 0.5 * (zs[k] + zs[k + 1]) > H2 else "ORG"
        for j in range(nx - 1):
            for i in range(nx - 1):
                e += 1
                n1, n2, n3, n4 = nid(i, j, k), nid(i + 1, j, k), nid(i + 1, j + 1, k), nid(i, j + 1, k)
                els.append((mat, f"{e},{n1},{n2},{n3},{n4},{n1+nx*nx},{n2+nx*nx},{n3+nx*nx},{n4+nx*nx}"))
                sets[mat].append(e)
    for mat in ("SI", "ORG"):
        L.append(f"*ELEMENT, TYPE=C3D8I, ELSET=E_{mat}")
        L += [s for m_, s in els if m_ == mat]
    L.append("*NSET, NSET=NALL, GENERATE"); L.append(f"1,{nx*nx*nz},1")
    x0 = [nid(0, j, k) for k in range(nz) for j in range(nx)]
    y0 = [nid(i, 0, k) for k in range(nz) for i in range(nx)]
    pz = [nid(i, j, 0) for j in range(nx) for i in range(nx)
          if xs[i] <= PATCH + 1e-9 and xs[j] <= PATCH + 1e-9]
    for nm, ids in (("X0", x0), ("Y0", y0), ("PZ", pz)):
        L.append(f"*NSET, NSET={nm}")
        L += [",".join(map(str, ids[a:a + 16])) for a in range(0, len(ids), 16)]
    for mat, (E, nu, a) in (("SI", (E1, NU1, A1)), ("ORG", (E2, NU2, A2))):
        L += [f"*MATERIAL, NAME={mat}", "*ELASTIC", f"{E},{nu}",
              f"*EXPANSION, ZERO={T_REF}", f"{a}",
              f"*SOLID SECTION, ELSET=E_{mat}, MATERIAL={mat}"]
    L += ["*BOUNDARY", "X0,1,1", "Y0,2,2", "PZ,3,3",
          "*INITIAL CONDITIONS, TYPE=TEMPERATURE", f"NALL,{T_REF}",
          "*STEP", "*STATIC", "*TEMPERATURE", f"NALL,{T_HOT}",
          "*NODE FILE", "U", "*END STEP"]
    (wd / "bil.inp").write_text("\n".join(L) + "\n")
    t0 = time.time()
    subprocess.run(["ccx", "bil"], cwd=wd, capture_output=True, check=True,
                   env=dict(os.environ, OMP_NUM_THREADS="8"))
    wall = time.time() - t0
    sys.path.insert(0, str(R / "scripts" / "phase0b"))
    from etm import ccxio
    U = ccxio.read_frd(wd / "bil.frd")["DISP"]
    top = [nid(i, j, nz - 1) for j in range(nx) for i in range(nx)]
    uz = U[top, 2]
    return {"warp_pv_mm": float(uz.max() - uz.min()), "wall_s": wall,
            "n_elems": e, "n_xy": n_xy, "n_z_per_layer": n_z}


def _uz_extreme(sm, fn, where):
    """Max or min of the z displacement from AEDT's own fields calculator; the raw value
    is returned as written by CalculatorWrite (SI)."""
    fr = sm.ofieldsreporter
    sol = sm.existing_analysis_sweeps[0]
    last = None
    for qty in ("Displacement", "Deformation"):
        try:
            fr.CalcStack("clear")
            fr.EnterQty(qty)
            fr.CalcOp("ScalarZ")
            if where[0] == "surf":
                fr.EnterSurf(where[1])
            else:
                fr.EnterVol(where[1])
            fr.CalcOp(fn)
            f = Path(sm.working_directory) / f"uz_{fn}.fld"
            fr.CalculatorWrite(str(f), ["Solution:=", sol], [])
            v = float(f.read_text().strip().splitlines()[-1])
            f.unlink()
            fr.CalcStack("clear")
            return v, qty
        except Exception as e:                     # try the next quantity name
            last = e
    raise RuntimeError(f"no displacement quantity: {last}")


def aedt_bilayer(stage="mech_bilayer"):
    """Structural design only. The temperature is a UNIFORM thermal condition on both
    bodies (the thermal-map link to a separate thermal design failed to solve). Two
    temperature levels are solved and the warpage per kelvin is taken from their
    difference, so the result cannot depend on AEDT's stress-free reference temperature;
    alternating the level also forces a genuine re-solve for every timed repeat."""
    from ansys.aedt.core import Mechanical
    sm = C.launch(Mechanical, "mech_bilayer2", "structural", solution_type="Structural")
    sm.modeler.model_units = "mm"
    for nm, (E, nu, a, rho) in (("si_m", (E1, NU1, A1, 2329.0)),
                                ("org_m", (E2, NU2, A2, 1800.0))):
        C.add_material(sm, nm, k=100.0, E=E * 1e6, nu=nu, cte=a, rho=rho)
    sm.modeler.create_box([0, 0, 0], [L_HALF, L_HALF, H2], name="org", material="org_m")
    sm.modeler.create_box([0, 0, H2], [L_HALF, L_HALF, H1], name="si", material="si_m")
    sm.modeler.create_rectangle("XY", [0, 0, 0], [PATCH, PATCH], name="patch")
    sm.modeler.imprint(["org"], ["patch"])
    pf = sm.modeler.get_faceid_from_position([PATCH / 2, PATCH / 2, 0], assignment="org")
    patch_area = float(sm.modeler.get_face_area(pf))
    if abs(patch_area - PATCH ** 2) > 1e-6:          # a whole-face support kills bending
        raise RuntimeError(f"support patch area {patch_area} mm2, expected {PATCH ** 2}")
    faces = [sm.modeler.get_faceid_from_position(xyz, assignment=b) for xyz, b in (
        ([0, L_HALF / 2, H2 / 2], "org"), ([0, L_HALF / 2, H2 + H1 / 2], "si"),
        ([L_HALF / 2, 0, H2 / 2], "org"), ([L_HALF / 2, 0, H2 + H1 / 2], "si"))]
    sm.assign_frictionless_support(faces + [pf])
    top = sm.modeler.get_faceid_from_position([L_HALF / 2, L_HALF / 2, H1 + H2],
                                              assignment="si")
    where = ("vol", "si")
    try:
        sm.modeler.create_face_list([top], "topface")
        where = ("surf", "topface")
    except Exception:
        pass
    # AEDT keeps a uniform thermal condition's temperature in the property named
    # 'ThermalCondition'; any other key is ignored and the bodies stay at 'EnvTemp'.
    # The level is a design variable: editing the boundary property in place did NOT
    # invalidate the solution (later "solves" took 4 s and returned the first field).
    sm["Tcond"] = f"{T_HOT}cel"
    sm._create_boundary("uniform_T", {"Objects": ["org", "si"], "Uniform": True,
                                      "ThermalCondition": "Tcond"}, "ThermalCondition")
    sm.mesh.assign_length_mesh(["org", "si"], maximum_length=0.1, maximum_elements=None,
                               name="len01")
    C.try_image(sm, C.EVID / stage / "01_geometry.png")
    sm.create_setup("S1")
    levels = (T_HOT, T_HOT - 50.0)
    solves = []
    for rep in range(4):                     # rep 0 = warm-up; then 3 timed, alternating
        t_c = levels[rep % 2]
        sm["Tcond"] = f"{t_c}cel"
        sm.cleanup_solution()              # every solve is a genuine re-mesh and re-solve
        t0 = time.time()
        ok = sm.analyze_setup("S1", cores=4)
        wall = time.time() - t0
        mx, qty = _uz_extreme(sm, "Maximum", where)
        mn, _ = _uz_extreme(sm, "Minimum", where)
        solves.append({"T_C": t_c, "solved": bool(ok), "wall_s": wall, "uz_max_raw": mx,
                       "uz_min_raw": mn, "quantity": qty})
    try:
        info = sm.mesh.get_mesh_stats() if hasattr(sm.mesh, "get_mesh_stats") else None
    except Exception:
        info = None
    fp = C.try_field_plot(sm, ["org", "si"], quantity="Displacement")
    if fp:
        C.try_image(sm, C.EVID / stage / "04_field.png", plot=fp)
    sm.save_project()
    sm.release_desktop(True, True)
    hot = [x for x in solves if x["T_C"] == T_HOT]
    cold = [x for x in solves if x["T_C"] != T_HOT]
    pv_hot = hot[-1]["uz_max_raw"] - hot[-1]["uz_min_raw"]
    pv_cold = cold[-1]["uz_max_raw"] - cold[-1]["uz_min_raw"]
    walls = [x["wall_s"] for x in solves[1:]]
    return {"solved": all(x["solved"] for x in solves), "solves": solves,
            "extracted_on": where[0], "patch_area_mm2": patch_area,
            "pv_per_K_raw": (pv_hot - pv_cold) / 50.0, "pv_hot_raw": pv_hot,
            "timing": {"median_s": float(np.median(walls)), "min_s": min(walls),
                       "max_s": max(walls), "repeats": len(walls), "walls_s": walls},
            "cores": 4, "mesh": info}


def _resolve_units(raw_per_K, tim_per_K):
    """CalculatorWrite reports SI metres; the factor-1000 alternative (mm) is rejected
    against the closed form, which is independent of both FE codes."""
    for unit, scale in (("m", 1e3), ("mm", 1.0)):
        if 1 / 3 < raw_per_K * scale / tim_per_K < 3:
            return unit, scale
    raise RuntimeError(f"AEDT warpage {raw_per_K} per K matches neither unit")


def main():
    import statistics
    t = timoshenko_warp()
    f = OUT / "reference_mech_bilayer.json"
    old = json.loads(f.read_text()) if f.exists() else {}
    if os.environ.get("BILAYER_REUSE_CCX") == "1" and (old.get("ccx_n50") or {}).get("timing"):
        c30, c50 = old["ccx_n30"], old["ccx_n50"]       # deterministic; already timed
        reused = True
    else:
        c30 = ccx_bilayer(30, 6)
        walls, c50 = [], None
        for rep in range(4):                          # warm-up + 3 timed repeats
            c50 = ccx_bilayer(50, 8, scratch("mech_ccx_f"))   # production-comparison level
            if rep:
                walls.append(c50["wall_s"])
        c50["timing"] = {"median_s": statistics.median(walls), "min_s": min(walls),
                         "max_s": max(walls), "repeats": len(walls), "walls_s": walls}
        reused = False
    res = {"stage": "mech_bilayer", "timoshenko": t, "ccx_n30": c30, "ccx_n50": c50,
           "ccx_reused_from_previous_run": reused,
           "hardware": C.hardware(), "load_average": [round(x, 1) for x in os.getloadavg()]}
    a = {}
    try:
        a = aedt_bilayer()
        dT = T_HOT - T_REF
        unit, scale = _resolve_units(a["pv_per_K_raw"], t["warp_pv_mm"] / dT)
        a["unit_raw"] = unit
        a["warp_pv_mm"] = a["pv_per_K_raw"] * scale * dT     # same 100 K as the others
        a["warp_pv_hot_absolute_mm"] = a["pv_hot_raw"] * scale
        res["aedt"] = a
    except Exception as e:      # a failed reference is reported as such, raw data kept
        res["aedt"] = dict(a, solved=False, error=str(e)[-500:])
    f.write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps({"timoshenko_mm": t["warp_pv_mm"], "ccx30": c30["warp_pv_mm"],
                      "ccx50": c50["warp_pv_mm"],
                      "aedt_mm": res["aedt"].get("warp_pv_mm"),
                      "aedt_error": res["aedt"].get("error")}, default=float))


if __name__ == "__main__":
    main()
