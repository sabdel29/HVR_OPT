"""Matched AEDT Mechanical (FEM) references for the closed-form / homogenised models.

Each case solves the SAME problem the production model solves, in the commercial FE
solver, on the same machine, and records value, error and wall time:

  tsv_bulk     one 30 um x 300 um Cu TSV: production rho L / A vs FE (conduction analogy)
  tsv_tile_kz  Cu-via array unit cell at the adopted tile density: Voigt k_z vs FE
  tsv_tile_kx  same cell, in-plane: Maxwell-Garnett k_xy vs FE
  rdl_tier_kx  one 10 um RDL tier, Cu grid in dielectric: laminate in-plane k vs FE
  rdl_tier_kz  same tier, through-thickness: laminate series k_z vs FE

Effective conductivity is extracted with an "electrode": a thin, very conductive slab
on the loaded face makes that face isothermal, so the single scalar AEDT returns
reliably (the maximum temperature) equals the temperature rise across the cell.
"""
from __future__ import annotations

import json
import os
import math
import sys
import time
import timeit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aedt_common as C                                              # noqa: E402

R = C.R
for _p in ("scripts/phase0nw", "scripts/phase0m", "scripts"):
    sys.path.insert(0, str(R / _p))

K_CU, K_SI, K_D = 400.0, 130.0, 0.35
K_ELEC = 1.0e5                     # electrode conductivity, W/mK
TSV_R_UM, TSV_P_UM = 15.0, 62.3105  # adopted tile: 1444 vias on 2.3685 mm -> 38 x 38
RDL_P_UM, RDL_T_UM, RDL_TCU_UM, RDL_OCC = 10.0, 10.0, 5.0, 0.30


def grid_line_fraction(occ):
    """Width fraction w/p of a square Cu grid whose area occupancy is `occ`."""
    return 1.0 - math.sqrt(1.0 - occ)


# ---------------- production (closed-form) models ----------------------------
def prod_tsv_bulk():
    from interconnect import rho_cu
    return rho_cu(20.0) * 300e-6 / (math.pi * (TSV_R_UM * 1e-6) ** 2)


def prod_tsv_tile():
    f = math.pi * TSV_R_UM ** 2 / TSV_P_UM ** 2
    kz = f * K_CU + (1 - f) * K_SI
    kxy = K_SI * (K_CU + K_SI + f * (K_CU - K_SI)) / (K_CU + K_SI - f * (K_CU - K_SI))
    return {"f": f, "kz": kz, "kxy": kxy}


def prod_rdl_tier():
    phi = RDL_TCU_UM / RDL_T_UM
    wp = grid_line_fraction(RDL_OCC)
    k_sub_x = wp * K_CU + (1 - wp) * (1.0 / (wp / K_CU + (1 - wp) / K_D))
    k_sub_z = RDL_OCC * K_CU + (1 - RDL_OCC) * K_D
    return {"w_over_p": wp, "kx": phi * k_sub_x + (1 - phi) * K_D,
            "kz": 1.0 / (phi / k_sub_z + (1 - phi) / K_D),
            "kx_voigt_upper": phi * (RDL_OCC * K_CU + (1 - RDL_OCC) * K_D) + (1 - phi) * K_D}


#: RVE_RETIME_REPEATS > 0 re-solves each case and times that many repeats after the first
#: (warm-up) solve, clearing mesh and solution before each, and writes ONLY
#: reference_rve_timing.json: the adopted values in reference_rve.json -- which the ETM's
#: tier tensor reads -- are never rewritten by a timing run.
RETIME_REPEATS = int(os.environ.get("RVE_RETIME_REPEATS", "0"))


_LAST_WALLS: list = []


def _repeat_solves(me, setup="S1", cores=4):
    walls = []
    for _ in range(RETIME_REPEATS):
        me.cleanup_solution()
        t0 = time.time()
        me.analyze_setup(setup, cores=cores)
        walls.append(time.time() - t0)
    return walls


def time_it(fn, n=7):
    t = timeit.repeat(fn, number=1000, repeat=n)
    s = sorted(x / 1000.0 for x in t)
    return {"median_s": s[len(s) // 2], "min_s": s[0], "max_s": s[-1], "repeats": n}


# ---------------- FE builders -------------------------------------------------
def _solve_cell(me, body_names, loaded_face_xyz, cold_face_xyz, electrode, q_w=1.0,
                cores=4):
    """Put an electrode on the loaded face, Q on its outer face, T = 0 on the cold face."""
    ex0, ey0, ez0, dx, dy, dz, outer = electrode
    C.add_material(me, "electrode", k=K_ELEC)
    me.modeler.create_box([ex0, ey0, ez0], [dx, dy, dz], name="electrode",
                          material="electrode")
    f_out = me.modeler.get_faceid_from_position(outer, assignment="electrode")
    me.assign_heat_flux([f_out], heat_flux_type="Total Power", value=f"{q_w}W")
    cold = []
    for nm in body_names:
        try:
            fid = me.modeler.get_faceid_from_position(cold_face_xyz, assignment=nm)
            if fid:
                cold.append(fid)
        except Exception:
            pass
    me.assign_uniform_temperature(cold, 0)
    me.create_setup("S1")
    t0 = time.time()
    ok = me.analyze_setup("S1", cores=cores)
    wall = time.time() - t0
    me._retime_walls = _repeat_solves(me, cores=cores)
    tmax = me.post.get_scalar_field_value("Temp", scalar_function="Maximum",
                                          object_name="electrode", object_type="volume")
    return bool(ok), float(tmax), wall


def case_tsv_bulk():
    from ansys.aedt.core import Mechanical
    from interconnect import rho_cu
    me = C.launch(Mechanical, "ref_tsv_bulk", "tsv", solution_type="Thermal")
    me.modeler.model_units = "um"
    k_an = (1.0 / rho_cu(20.0)) * C.K_SCALE
    C.add_material(me, "cu_analog", k=k_an)
    me.modeler.create_cylinder("Z", [0, 0, 0], TSV_R_UM, 300.0, name="tsv",
                               material="cu_analog")
    ok, tmax, wall = _solve_cell(me, ["tsv"], None, [0, 0, 0],
                                 (-20, -20, 300.0, 40, 40, 1.0, [0, 0, 301.0]))
    img = C.try_image(me, C.EVID / "tsv_bulk" / "01_geometry.png")
    fp = C.try_field_plot(me, ["tsv"])
    if fp:
        C.try_image(me, C.EVID / "tsv_bulk" / "04_field.png", plot=fp)
    _LAST_WALLS[:] = getattr(me, "_retime_walls", [])
    me.release_desktop(True, True)
    r_fe = tmax * C.K_SCALE           # electrode slab is 40x40 um: negligible series R
    r_p = prod_tsv_bulk()
    return {"stage": "tsv_bulk", "observable": "single-TSV DC resistance (Ohm)",
            "production_model": "rho L / A", "production_value": r_p,
            "reference_tool": "AEDT 2026 R1 Mechanical (thermal FEM, conduction analogy)",
            "reference_value": r_fe, "rel_error": (r_p - r_fe) / r_fe,
            "reference_wall_s": wall, "production_timing": time_it(prod_tsv_bulk),
            "solved": ok, "image": img}


def case_tsv_tile(direction):
    from ansys.aedt.core import Mechanical
    p, r = TSV_P_UM, TSV_R_UM
    h = p
    me = C.launch(Mechanical, f"ref_tsv_tile_{direction}", "cell", solution_type="Thermal")
    me.modeler.model_units = "um"
    C.add_material(me, "si_k", k=K_SI)
    C.add_material(me, "cu_k", k=K_CU)
    me.modeler.create_box([-p / 2, -p / 2, 0], [p, p, h], name="si", material="si_k")
    me.modeler.create_cylinder("Z", [0, 0, 0], r, h, name="cu", material="cu_k")
    me.modeler.subtract("si", "cu", keep_originals=True)
    if direction == "kz":
        elec = (-p / 2, -p / 2, h, p, p, 0.5, [0, 0, h + 0.5])
        cold, L, A = [0, p / 4 + r / 2, 0], h, p * p
        bodies = ["si", "cu"]
        cold_pts = [[p / 2 - 1, p / 2 - 1, 0], [0, 0, 0]]
    else:
        elec = (p / 2, -p / 2, 0, 0.5, p, h, [p / 2 + 0.5, 0, h / 2])
        L, A = p, p * h
        bodies = ["si"]
        cold_pts = [[-p / 2, 0, h / 2]]
    ex0, ey0, ez0, dx, dy, dz, outer = elec
    C.add_material(me, "electrode", k=K_ELEC)
    me.modeler.create_box([ex0, ey0, ez0], [dx, dy, dz], name="electrode", material="electrode")
    me.assign_heat_flux([me.modeler.get_faceid_from_position(outer, assignment="electrode")],
                        heat_flux_type="Total Power", value="1W")
    faces = []
    for pt in cold_pts:
        for nm in ("si", "cu"):
            try:
                fid = me.modeler.get_faceid_from_position(pt, assignment=nm)
                if fid and fid not in faces:
                    faces.append(fid)
            except Exception:
                pass
    me.assign_uniform_temperature(faces, 0)
    me.create_setup("S1")
    t0 = time.time(); ok = me.analyze_setup("S1", cores=4); wall = time.time() - t0
    me._retime_walls = _repeat_solves(me)
    tmax = me.post.get_scalar_field_value("Temp", scalar_function="Maximum",
                                          object_name="electrode", object_type="volume")
    img = C.try_image(me, C.EVID / "tsv_tile_rve" / f"01_geometry_{direction}.png")
    fp = C.try_field_plot(me, ["si", "cu"])
    if fp:
        C.try_image(me, C.EVID / "tsv_tile_rve" / f"04_field_{direction}.png", plot=fp)
    _LAST_WALLS[:] = getattr(me, "_retime_walls", [])
    me.release_desktop(True, True)
    k_fe = 1.0 * (L * 1e-6) / ((A * 1e-12) * float(tmax))
    pr = prod_tsv_tile()
    k_p = pr["kz"] if direction == "kz" else pr["kxy"]
    return {"stage": f"tsv_tile_{direction}", "observable": f"tile effective {direction} (W/mK)",
            "production_model": "Voigt" if direction == "kz" else "Maxwell-Garnett",
            "production_value": k_p, "reference_tool": "AEDT 2026 R1 Mechanical (thermal FEM)",
            "reference_value": k_fe, "rel_error": (k_p - k_fe) / k_fe,
            "reference_wall_s": wall, "production_timing": time_it(prod_tsv_tile),
            "cu_fraction": pr["f"], "solved": bool(ok), "image": img}


def case_rdl_tier(direction):
    from ansys.aedt.core import Mechanical
    p, t, tc = RDL_P_UM, RDL_T_UM, RDL_TCU_UM
    w = grid_line_fraction(RDL_OCC) * p
    me = C.launch(Mechanical, f"ref_rdl_{direction}", "tier", solution_type="Thermal")
    me.modeler.model_units = "um"
    C.add_material(me, "diel", k=K_D)
    C.add_material(me, "cu_k", k=K_CU)
    me.modeler.create_box([-p / 2, -p / 2, 0], [p, p, t], name="diel", material="diel")
    me.modeler.create_box([-p / 2, -w / 2, 0], [p, w, tc], name="cux", material="cu_k")
    me.modeler.create_box([-w / 2, -p / 2, 0], [w, p, tc], name="cuy", material="cu_k")
    me.modeler.unite(["cux", "cuy"])
    me.modeler.subtract("diel", "cux", keep_originals=True)
    if direction == "kx":
        outer = [p / 2 + 0.1, 0, t / 2]        # ON the electrode's outer face
        me.modeler.create_box([p / 2, -p / 2, 0], [0.1, p, t], name="electrode",
                              material=C.add_material(me, "electrode", k=K_ELEC))
        cold_pts = [[-p / 2, p / 4 + w / 4, t * 0.75], [-p / 2, 0, tc / 2]]
        L, A = p, p * t
    else:
        outer = [0, 0, t + 0.1]
        me.modeler.create_box([-p / 2, -p / 2, t], [p, p, 0.1], name="electrode",
                              material=C.add_material(me, "electrode", k=K_ELEC))
        cold_pts = [[p / 4 + w / 4, p / 4 + w / 4, 0], [0, 0, 0]]
        L, A = t, p * p
    me.assign_heat_flux([me.modeler.get_faceid_from_position(outer, assignment="electrode")],
                        heat_flux_type="Total Power", value="1W")
    faces = []
    for pt in cold_pts:
        for nm in ("diel", "cux"):
            try:
                fid = me.modeler.get_faceid_from_position(pt, assignment=nm)
                if fid and fid not in faces:
                    faces.append(fid)
            except Exception:
                pass
    me.assign_uniform_temperature(faces, 0)
    me.create_setup("S1")
    t0 = time.time(); ok = me.analyze_setup("S1", cores=4); wall = time.time() - t0
    me._retime_walls = _repeat_solves(me)
    tmax = me.post.get_scalar_field_value("Temp", scalar_function="Maximum",
                                          object_name="electrode", object_type="volume")
    img = C.try_image(me, C.EVID / "rdl_tier_rve" / f"01_geometry_{direction}.png")
    fp = C.try_field_plot(me, ["diel", "cux"])
    if fp:
        C.try_image(me, C.EVID / "rdl_tier_rve" / f"04_field_{direction}.png", plot=fp)
    _LAST_WALLS[:] = getattr(me, "_retime_walls", [])
    me.release_desktop(True, True)
    k_fe = (L * 1e-6) / ((A * 1e-12) * float(tmax))
    pr = prod_rdl_tier()
    return {"stage": f"rdl_tier_{direction}", "observable": f"tier effective {direction} (W/mK)",
            "production_model": "laminate (grid in-plane, series through-thickness)",
            "production_value": pr[direction], "reference_tool":
            "AEDT 2026 R1 Mechanical (thermal FEM)", "reference_value": k_fe,
            "rel_error": (pr[direction] - k_fe) / k_fe, "reference_wall_s": wall,
            "production_timing": time_it(prod_rdl_tier), "solved": bool(ok),
            "voigt_upper_bound": pr["kx_voigt_upper"], "image": img}


CASES = {"tsv_bulk": case_tsv_bulk,
         "tsv_tile_kz": lambda: case_tsv_tile("kz"),
         "tsv_tile_kx": lambda: case_tsv_tile("kx"),
         "rdl_tier_kx": lambda: case_rdl_tier("kx"),
         "rdl_tier_kz": lambda: case_rdl_tier("kz")}

def retime(names):
    """Re-solve and time; compare the re-solved value with the adopted one."""
    import statistics
    C.EVID = Path("/tmp/rve_retime_evidence")       # never overwrite the evidence images
    adopted = json.loads((R / "research" / "final_closure" / "reference_rve.json").read_text())
    out = R / "research" / "final_closure" / "reference_rve_timing.json"
    res = {}
    for n in names:
        try:
            r = CASES[n]()
            w = list(_LAST_WALLS)
            res[n] = {"warmup_s": r["reference_wall_s"], "walls_s": w,
                      "median_s": statistics.median(w), "min_s": min(w), "max_s": max(w),
                      "repeats": len(w), "cores": 4,
                      "includes": "meshing + solve, solution cleared before each repeat",
                      "re_solved_value": r["reference_value"],
                      "adopted_value": adopted[n]["reference_value"],
                      "re_solved_vs_adopted_rel": (r["reference_value"]
                                                   - adopted[n]["reference_value"])
                      / adopted[n]["reference_value"]}
        except Exception as e:
            res[n] = {"error": str(e)[-300:]}
        res[n]["load_average"] = [round(x, 1) for x in os.getloadavg()]
        out.write_text(json.dumps(res, indent=1, default=str))
        print("RETIME", n, json.dumps(res[n], default=str), flush=True)


if __name__ == "__main__":
    names = sys.argv[1:] or list(CASES)
    if RETIME_REPEATS:
        retime(names)
        sys.exit(0)
    out = R / "research" / "final_closure" / "reference_rve.json"
    res = json.loads(out.read_text()) if out.exists() else {}
    for n in names:
        try:
            r = CASES[n]()
        except Exception as e:
            r = {"stage": n, "error": str(e)[:300]}
        r["hardware"] = C.hardware()
        res[n] = r
        out.write_text(json.dumps(res, indent=1, default=str))
        print(json.dumps({n: {k: r.get(k) for k in ("production_value", "reference_value",
                                                   "rel_error", "reference_wall_s", "error")}}),
              flush=True)
