#!/usr/bin/env python3
"""Phase-0E Sec.13: full-package thermal cross-check in ANSYS Icepak.

Phase 0D-R validated the conduction OPERATOR against MOOSE on a 2-D sheet. It never checked
the complete 3-D package thermal model. Icepak is licensed here (elec_solve_icepak), so the
same stack, the same materials, the same spatially distributed heat and the same convective
boundaries are rebuilt in an independent commercial solver.

Conduction-only: the CalculiX model has no fluid, so Icepak is run with problem_type
"TemperatureOnly" and Robin (HTC) walls, which is the identical mathematical problem.
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0b"))
sys.path.insert(0, str(R / "scripts" / "phase0e"))
from etm.config import load_stack, load_doe, build_materials
from etm.placement import generate

OUT = R / "results" / "phase0e" / "aedt"
OUT.mkdir(parents=True, exist_ok=True)

DIE = 22.36
SUB = 30.0
T_AMB = 25.0
H_BOT = 10.0


def tiles_for(place, side, stack, doe, n_vr=4):
    g, rules = stack["geometry"], doe["placement_rules"]
    return [(t.cx, t.cy) for t in generate(
        place, n_vr, side, side, die_x=g["functional_die"]["size_x"]["value"],
        die_y=g["functional_die"]["size_y"]["value"],
        keepout=rules["edge_keepout_mm"]["value"],
        min_gap=rules["min_gap_mm"]["value"], p_total=1.0)]


def build_and_solve(case: str, place: str, side_mm: float, h_sub: float, p_conv_total: float,
                    p_die: float, h_top: float, ng=True, mesh_level=3) -> dict:
    from ansys.aedt.core import Icepak
    stack, doe = load_stack(), load_doe()
    mats = build_materials(stack)
    tiles = tiles_for(place, side_mm, stack, doe)

    ipk = Icepak(project=str(OUT / f"icepak_{case}.aedt"), design=case, version="2026.1",
                 non_graphical=ng, new_desktop=True, solution_type="SteadyState")
    ipk.modeler.model_units = "mm"
    ipk.problem_type = "TemperatureOnly"

    def mat(name, m):
        if name in ipk.materials.material_keys:
            return name
        mm = ipk.materials.add_material(name)
        mm.thermal_conductivity = m.k
        mm.mass_density = 2330.0
        mm.specific_heat = 700.0
        return name

    m_si = mat("si_p0e", mats["silicon"])
    m_uf = mat("uf_p0e", mats["underfill_homog"])
    m_tim = mat("tim_p0e", mats["tim"])
    m_hvr = mat("hvr_p0e", mats["hvr_effective"])

    t_if = stack["geometry"]["interface_layer"]["thickness"]["value"]
    t_die = stack["geometry"]["functional_die"]["thickness"]["value"]
    t_tim = stack["geometry"]["tim"]["thickness"]["value"]
    t_tile = stack["geometry"]["hvr_tile"]["thickness"]["value"]

    z0 = 0.0
    sub = ipk.modeler.create_box([-SUB / 2, -SUB / 2, z0], [SUB, SUB, h_sub],
                                 name="substrate", material=m_si)
    # HVR tiles embedded flush with the substrate TOP surface
    tile_objs = []
    for k, (cx, cy) in enumerate(tiles):
        b = ipk.modeler.create_box([cx - side_mm / 2, cy - side_mm / 2, h_sub - t_tile],
                                   [side_mm, side_mm, t_tile], name=f"hvr{k}", material=m_hvr)
        tile_objs.append(b)
    ipk.modeler.subtract(sub, tile_objs, keep_originals=True)

    z = h_sub
    itf = ipk.modeler.create_box([-DIE / 2, -DIE / 2, z], [DIE, DIE, t_if],
                                 name="interface", material=m_uf); z += t_if
    die = ipk.modeler.create_box([-DIE / 2, -DIE / 2, z], [DIE, DIE, t_die],
                                 name="die", material=m_si); z += t_die
    tim = ipk.modeler.create_box([-DIE / 2, -DIE / 2, z], [DIE, DIE, t_tim],
                                 name="tim", material=m_tim); z += t_tim
    z_top = z

    ipk.assign_solid_block(die.name, f"{p_die}W", boundary_name="src_die")
    for k, b in enumerate(tile_objs):
        ipk.assign_solid_block(b.name, f"{p_conv_total/len(tile_objs)}W",
                               boundary_name=f"src_hvr{k}")

    f_top = max(tim.faces, key=lambda f: f.center[2])
    f_bot = min(sub.faces, key=lambda f: f.center[2])
    ipk.assign_stationary_wall_with_htc(f_top.id, name="cool_top",
                                        htc=f"{h_top}w_per_m2kel", thickness="0mm",
                                        ref_temperature=f"{T_AMB}cel")
    ipk.assign_stationary_wall_with_htc(f_bot.id, name="cool_bot",
                                        htc=f"{H_BOT}w_per_m2kel", thickness="0mm",
                                        ref_temperature=f"{T_AMB}cel")

    su = ipk.create_setup("s1")
    su.props["Convergence Criteria - Max Iterations"] = 200
    su.update()
    ipk.mesh.global_mesh_region.settings["MeshRegionResolution"] = mesh_level
    try:
        ipk.mesh.global_mesh_region.update()
    except Exception:
        pass

    t0 = time.time()
    ok = ipk.analyze_setup("s1")
    el = time.time() - t0
    res = {"case": case, "placement": place, "h_sub_mm": h_sub, "tile_side_mm": side_mm,
           "P_die_w": p_die, "P_conv_w": p_conv_total, "h_top": h_top,
           "ok": bool(ok), "solve_s": el, "mesh_level": mesh_level}
    if ok:
        for nm, obj in (("die", die), ("hvr0", tile_objs[0]), ("substrate", sub)):
            try:
                v = ipk.post.get_scalar_field_value("Temperature", scalar_function="Maximum",
                                                    object_name=obj.name, object_type="volume")
                res[f"Tmax_{nm}_C"] = float(v)
                v2 = ipk.post.get_scalar_field_value("Temperature", scalar_function="Mean",
                                                     object_name=obj.name, object_type="volume")
                res[f"Tmean_{nm}_C"] = float(v2)
            except Exception as e:
                res[f"Tmax_{nm}_C"] = f"ERR {e}"
    for m in (ipk.logger.messages.design_level or [])[-8:]:
        print("   DES:", m)
    ipk.save_project(); ipk.release_desktop(close_projects=False, close_desktop=True)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="TH1")
    ap.add_argument("--place", default="distributed_2x2")
    ap.add_argument("--side", type=float, default=5.0735)
    ap.add_argument("--hsub", type=float, default=0.5)
    ap.add_argument("--pconv", type=float, default=20.6)
    ap.add_argument("--mesh", type=int, default=3)
    a = ap.parse_args()
    h_top = json.loads((R / "results/phase0b/cooling_calibration.json").read_text())["h_top_W_m2K"]
    r = build_and_solve(a.case, a.place, a.side, a.hsub, a.pconv, 240.0, h_top,
                        mesh_level=a.mesh)
    print(json.dumps(r, indent=2))
    (OUT / f"icepak_{a.case}.json").write_text(json.dumps(r, indent=2))
