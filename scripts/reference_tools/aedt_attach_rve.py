"""Explicit AEDT Mechanical (thermal FEM) unit cells of the VR-to-substrate attach.

The production model homogenises the attach as Cu-pillar + solder-cap columns in underfill:
through thickness each column is Cu and solder in SERIES and the columns are in PARALLEL with
the underfill, k_z = f k_col + (1 - f) k_uf; in plane each z-slice is a Maxwell-Garnett array
of its own inclusion and the slices act in parallel (scripts/phase0nw/z2_converter.py
vr_attach_material). This file solves the SAME unit cell explicitly -- one column of the
periodic lattice, p x p x 30 um, Cu 0-14 um under solder 14-30 um, underfill around it --
for both published densities (dense 15/30 um, sparse 30/80 um) and both directions, on two
meshes (AEDT's default and a length-refined one), and records value, error and wall time.

The unit cell is the INFINITE periodic lattice, so the homogenised value it is compared with
is evaluated at the same f = pi d^2 / (4 p^2); the finite-lattice metal fraction a variant
uses differs from it only by the cell-edge strip, which is a lattice fact, not an accuracy
question. Effective conductivity is extracted as in aedt_rve_references.py: an electrode slab
on the loaded face, 1 W into it, T = 0 on the opposite face, k = Q L / (A dT_max).
"""
from __future__ import annotations

import json
import math
import sys
import time
import timeit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aedt_common as C                                              # noqa: E402

R = C.R
for _p in ("scripts/phase0nw", "scripts"):
    sys.path.insert(0, str(R / _p))
import z2_converter as Z2C                                          # noqa: E402

OUT = R / "research" / "final_closure" / "reference_attach_rve.json"
K_ELEC = 1.0e5
H_CU, H_CAP = 14.0, 16.0
CASES = {"dense": (15.0, 30.0), "sparse": (30.0, 80.0)}


def production(d, p):
    """The homogenised card at the infinite-lattice fraction of this unit cell."""
    c = Z2C.vr_attach_material({"cu_height_um": H_CU, "cap_height_um": H_CAP,
                                "diameter_um": d, "pitch_um": p})
    kxy, _, kz = c["k_ortho"]["value"]
    return {"kz": kz, "kxy": kxy, "f": c["geometry"]["f"]}


def solve(name, direction, refined):
    from ansys.aedt.core import Mechanical
    d, p = CASES[name]
    h, r = H_CU + H_CAP, d / 2.0
    tag = f"{name}_{direction}_{'fine' if refined else 'auto'}"
    me = C.launch(Mechanical, f"ref_attach_{tag}", "cell", solution_type="Thermal")
    me.modeler.model_units = "um"
    C.add_material(me, "uf_k", k=Z2C.K_UNDERFILL)
    C.add_material(me, "cu_k", k=Z2C.K_COPPER)
    C.add_material(me, "sn_k", k=Z2C.K_SOLDER)
    me.modeler.create_box([-p / 2, -p / 2, 0], [p, p, h], name="uf", material="uf_k")
    me.modeler.create_cylinder("Z", [0, 0, 0], r, H_CU, name="cu", material="cu_k")
    me.modeler.create_cylinder("Z", [0, 0, H_CU], r, H_CAP, name="sn", material="sn_k")
    me.modeler.subtract("uf", ["cu", "sn"], keep_originals=True)
    if direction == "kz":
        elec = (-p / 2, -p / 2, h, p, p, 0.5, [0, 0, h + 0.5])
        L, A = h, p * p
        cold_pts = [([p / 2 - 0.5, p / 2 - 0.5, 0], "uf"), ([0, 0, 0], "cu")]
    else:
        elec = (p / 2, -p / 2, 0, 0.5, p, h, [p / 2 + 0.5, 0, h / 2])
        L, A = p, p * h
        cold_pts = [([-p / 2, 0, h / 2], "uf")]
    ex0, ey0, ez0, dx, dy, dz, outer = elec
    C.add_material(me, "electrode", k=K_ELEC)
    me.modeler.create_box([ex0, ey0, ez0], [dx, dy, dz], name="electrode", material="electrode")
    me.assign_heat_flux([me.modeler.get_faceid_from_position(outer, assignment="electrode")],
                        heat_flux_type="Total Power", value="1W")
    faces = []
    for pt, nm in cold_pts:
        fid = me.modeler.get_faceid_from_position(pt, assignment=nm)
        if fid and fid not in faces:
            faces.append(fid)
    me.assign_uniform_temperature(faces, 0)
    mesh_note = "AEDT default (auto) mesh"
    if refined:
        try:
            me.mesh.assign_length_mesh(["cu", "sn"], maximum_length=f"{d / 8:g}um",
                                       maximum_elements=None, name="L_columns")
            me.mesh.assign_length_mesh(["uf"], maximum_length=f"{min(p / 16, h / 6):g}um",
                                       maximum_elements=None, name="L_underfill")
            mesh_note = (f"length-refined: columns <= {d / 8:g} um, underfill <= "
                         f"{min(p / 16, h / 6):g} um")
        except Exception as e:                      # recorded, never silently dropped
            mesh_note = f"refinement FAILED ({str(e)[:120]}); default mesh"
    me.create_setup("S1")
    t0 = time.time()
    ok = me.analyze_setup("S1", cores=4)
    wall = time.time() - t0
    tmax = me.post.get_scalar_field_value("Temp", scalar_function="Maximum",
                                          object_name="electrode", object_type="volume")
    img = C.try_image(me, C.EVID / "attach_rve" / f"01_geometry_{tag}.png")
    me.release_desktop(True, True)
    k_fe = 1.0 * (L * 1e-6) / ((A * 1e-12) * float(tmax))
    return {"solved": bool(ok), "reference_value": k_fe, "dT_max_K": float(tmax),
            "reference_wall_s": wall, "mesh": mesh_note, "image": img}


def main(names):
    res = json.loads(OUT.read_text()) if OUT.exists() else {}
    for name in names:
        d, p = CASES[name]
        pr = production(d, p)
        t = timeit.repeat(lambda: production(d, p), number=200, repeat=5)
        ptime = sorted(x / 200 for x in t)[2]
        for direction in ("kz", "kxy"):
            key = f"vr_attach_{name}_{direction}"
            runs = {}
            for refined in (False, True):
                try:
                    runs["fine" if refined else "auto"] = solve(name, direction, refined)
                except Exception as e:
                    runs["fine" if refined else "auto"] = {"error": str(e)[-300:]}
            best = runs.get("fine") if runs.get("fine", {}).get("reference_value") else runs.get("auto")
            k_p = pr[direction]
            row = {"stage": key, "observable": f"attach effective {direction} (W/mK)",
                   "production_model": ("columns (Cu + solder in series) in parallel with "
                                        "underfill" if direction == "kz" else
                                        "Maxwell-Garnett per z-slice, slices in parallel"),
                   "production_value": k_p, "f_unit_cell": pr["f"],
                   "geometry": {"d_um": d, "pitch_um": p, "h_cu_um": H_CU, "h_cap_um": H_CAP},
                   "reference_tool": "AEDT 2026 R1 Mechanical (thermal FEM, explicit unit cell)",
                   "runs": runs, "production_timing_s": ptime, "hardware": C.hardware()}
            if best and best.get("reference_value"):
                row.update(reference_value=best["reference_value"],
                           rel_error=(k_p - best["reference_value"]) / best["reference_value"],
                           reference_wall_s=best["reference_wall_s"], mesh=best["mesh"])
                a, b = runs.get("auto", {}), runs.get("fine", {})
                if a.get("reference_value") and b.get("reference_value"):
                    row["mesh_change_rel"] = ((b["reference_value"] - a["reference_value"])
                                              / b["reference_value"])
            res[key] = row
            OUT.write_text(json.dumps(res, indent=1, default=str))
            print(json.dumps({key: {k: row.get(k) for k in ("production_value",
                                                            "reference_value", "rel_error",
                                                            "mesh_change_rel")}}), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or list(CASES))
