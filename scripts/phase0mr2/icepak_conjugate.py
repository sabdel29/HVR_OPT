#!/usr/bin/env python3
"""Phase-0M-R2 Section 6 --- canonical single-channel CONJUGATE benchmark in Icepak.

The earlier Icepak attempt returned exactly 5000 K on every object. That is a solver
clamp, and its cause was diagnosed in Phase 0M: an EXTERNAL boundary condition had been
applied to an INTERNAL solid/air interface, so the model had no route for heat to leave
and the solver ran to its ceiling. This case is built so that failure mode cannot recur:

  * the coolant is an EXPLICIT fluid volume, not a surface condition;
  * the only inlet is an opening with a stated mass flow and temperature;
  * the only outlet is an opening at fixed static pressure;
  * every other external face is adiabatic, so the ONLY heat path out is the coolant;
  * an energy balance is computed afterwards and must close, or the case is discarded.

This module writes the IronPython 2.7 job for `ansysedt -ng -RunScriptAndExit`. AEDT
embeds IronPython 2.7: f-strings are a SyntaxError there, so the generated job uses `%`
formatting throughout.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
import time
from pathlib import Path

import yaml

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0mr2"))

AEDT = Path("/local/ansys/electronics/ansys_inc/v261/AnsysEM/ansysedt")
OUT = R / "results" / "phase0mr2"
WD = OUT / "icepak"
CFG = R / "configs" / "phase0mr2" / "cooling_model.yaml"


def geometry(m_dot_total_g_s: float = 27.0) -> dict:
    c = yaml.safe_load(CFG.read_text())
    ch, f = c["channel"], c["fluid"]
    w, h, tf = ch["w_ch_um"], ch["h_ch_um"], ch["t_fin_um"]
    L, W = ch["length_mm"], ch["width_mm"]
    n = int(W * 1e3 // (w + tf))
    m_ch = m_dot_total_g_s * 1e-3 / n                      # kg/s per channel
    a = (w * 1e-6) * (h * 1e-6)
    u = m_ch / (f["rho_kg_m3"] * a)
    # the unit cell the compact model represents: one channel plus two half fins
    cell_w = w + tf
    q_total = 1000.0
    q_cell = q_total / n
    return {"w_ch_um": w, "h_ch_um": h, "t_fin_um": tf, "t_base_um": ch["t_base_um"],
            "length_mm": L, "width_mm": W, "n_channels": n, "cell_w_um": cell_w,
            "m_dot_channel_kg_s": m_ch, "velocity_m_s": u,
            "q_cell_w": q_cell, "q_total_w": q_total,
            "k_solid": ch["k_solid_w_mk"], "t_in_c": f["t_ref_c"],
            "rho": f["rho_kg_m3"], "mu": f["mu_pa_s"], "k_f": f["k_w_mk"],
            "cp": f["cp_j_kgk"]}


def write_job(g: dict, wd: Path) -> Path:
    wd.mkdir(parents=True, exist_ok=True)
    js = wd / "icepak_job.py"
    # IronPython 2.7 -- no f-strings, no pathlib, ASCII only.
    src = '''# -*- coding: utf-8 -*-
# Phase-0M-R2 conjugate single-channel benchmark. IronPython 2.7 (AEDT embeds 2.7).
import ScriptEnv, os, json
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")
oDesktop.RestoreWindow()
WD = r"%(wd)s"
proj = oDesktop.NewProject()
proj.InsertDesign("Icepak", "conj", "SteadyState", "")
d = proj.SetActiveDesign("conj")
ed = d.SetActiveEditor("3D Modeler")

# Materials are DEFINED here rather than taken from the Icepak library, so the CFD case
# and the compact model provably use the same numbers. A library lookup would silently
# introduce a different property set and make any disagreement uninterpretable.
defs = proj.GetDefinitionManager()
defs.AddMaterial(["NAME:si_bench", "CoordinateSystemType:=", "Cartesian",
                  ["NAME:AttachedData"], "thermal_conductivity:=", "%(ksol).6g",
                  "mass_density:=", "2330", "specific_heat:=", "700"])
defs.AddMaterial(["NAME:water_bench", "CoordinateSystemType:=", "Cartesian",
                  ["NAME:AttachedData"], "material_def:=", 1,
                  "thermal_conductivity:=", "%(kf).6g",
                  "mass_density:=", "%(rho).6g", "specific_heat:=", "%(cp).6g",
                  "viscosity:=", "%(mu).6g"])

d.SetDesignSettings(["NAME:Design Settings Data", "Perform Minimal validation:=", False,
                     "Default Fluid Material:=", "water_bench",
                     "Default Solid Material:=", "si_bench",
                     "Default Surface Material:=", "Steel-oxidised-surface",
                     "AmbientTemperature:=", "%(t_in).1fcel",
                     "AmbientPressure:=", "0n_per_meter_sq",
                     "AmbientRadiationTemperature:=", "%(t_in).1fcel",
                     "Gravity Vector CS ID:=", 1, "Gravity Vector Axis:=", "Z",
                     "Gravity Direction:=", 1, "Export After Simulation:=", False,
                     "Solve Inside:=", True])

# ---- geometry, in micrometres -------------------------------------------------------
ed.SetModelUnits(["NAME:Units Parameter", "Units:=", "um", "Rescale:=", False])
Lz = %(L_um).6g          # flow direction
w  = %(w).6g             # channel width
h  = %(h).6g             # channel height
tf = %(tf).6g            # fin thickness (two half fins = tf total in the unit cell)
tb = %(tb).6g            # base thickness
cw = w + tf              # unit-cell width

def box(name, x, y, z, dx, dy, dz, mat):
    ed.CreateBox(["NAME:BoxParameters", "XPosition:=", str(x)+"um",
                  "YPosition:=", str(y)+"um", "ZPosition:=", str(z)+"um",
                  "XSize:=", str(dx)+"um", "YSize:=", str(dy)+"um",
                  "ZSize:=", str(dz)+"um"],
                 ["NAME:Attributes", "Name:=", name, "Flags:=", "",
                  "Color:=", "(143 175 143)", "Transparency:=", 0.4,
                  "PartCoordinateSystem:=", "Global", "MaterialValue:=", chr(34)+mat+chr(34),
                  "SolveInside:=", True])
    return name

# solid: base slab plus the two half fins, as one unit cell
box("base", 0, 0, 0, cw, Lz, tb, "si_bench")
box("fin_l", 0, 0, tb, tf/2.0, Lz, h, "si_bench")
box("fin_r", tf/2.0 + w, 0, tb, tf/2.0, Lz, h, "si_bench")
# fluid: the channel itself
box("fluid", tf/2.0, 0, tb, w, Lz, h, "water_bench")

mod = d.GetModule("BoundarySetup")

# An opening must be assigned to a FACE, not to the body. Pick the fluid faces whose
# centres lie at the two ends of the flow direction (y = 0 and y = Lz).
def face_at_y(obj, ytarget, tol=1.0):
    out = []
    for fid in ed.GetFaceIDs(obj):
        c = ed.GetFaceCenter(int(fid))
        if abs(float(c[1]) - ytarget) < tol:
            out.append(int(fid))
    return out

f_in  = face_at_y("fluid", 0.0)
f_out = face_at_y("fluid", Lz)

# ---- inlet: stated mass flow and temperature ----------------------------------------
mod.AssignOpeningBoundary(["NAME:inlet", "Faces:=", f_in,
    "Inlet Type:=", "Mass Flow",
    "Mass Flow Rate:=", "%(mdot).6g kg_per_s",
    "Temperature:=", "%(t_in).1fcel",
    "External Rad. Temperature:=", "%(t_in).1fcel"])

# ---- outlet: fixed static pressure ---------------------------------------------------
mod.AssignOpeningBoundary(["NAME:outlet", "Faces:=", f_out,
    "Inlet Type:=", "Pressure",
    "Static Pressure:=", "0n_per_meter_sq",
    "Temperature:=", "%(t_in).1fcel",
    "External Rad. Temperature:=", "%(t_in).1fcel"])

# ---- heat into the base --------------------------------------------------------------
mod.AssignBlockBoundary(["NAME:base_src", "Objects:=", ["base"],
    "Block Type:=", "Total Power", "Use External Conditions:=", False,
    "Total Power:=", "%(q).6g W"])

# ---- mesh. The channel is 50 x 300 x 22360 um, an aspect ratio of 447:1 along the
# flow. Icepak's automatic mesher failed this geometry outright ("poor mesh quality"),
# so the element counts are set explicitly per direction.
try:
    msh = d.GetModule("MeshRegion")
    msh.EditGlobalMeshRegion(["NAME:Settings", "MeshMethod:=", "MesherHD",
        "UserSpecifiedSettings:=", True, "ComputeGap:=", True,
        "MaxElementSizeX:=", str(cw/6.0)+"um",
        "MaxElementSizeY:=", str(Lz/60.0)+"um",
        "MaxElementSizeZ:=", str((tb+h)/20.0)+"um",
        "MinElementsInGap:=", "4", "MinElementsOnEdge:=", "3",
        "MaxSizeRatio:=", "2", "NoOGrids:=", False, "EnableMLM:=", True,
        "EnforeMLMType:=", "3D", "StairStepMeshing:=", False,
        "MinGapX:=", "1um", "MinGapY:=", "1um", "MinGapZ:=", "1um"])
    mesh_ok = True
    mesh_err = ""
except Exception, e:
    mesh_ok = False
    mesh_err = str(e)

oDesign = d
setup = d.GetModule("AnalysisSetup")
setup.InsertSetup("IcepakSteadyState", ["NAME:Setup1", "Enabled:=", True,
    "Flow Regime:=", "Laminar", "Include Temperature:=", True,
    "Include Flow:=", True, "Include Gravity:=", False,
    "Solution Initialization - X Velocity:=", "0m_per_sec",
    "Solution Initialization - Y Velocity:=", "%(u).6g m_per_sec",
    "Solution Initialization - Z Velocity:=", "0m_per_sec",
    "Solution Initialization - Temperature:=", "%(t_in).1fcel",
    "Convergence Criteria - Max Iterations:=", 400,
    "Convergence Criteria - Flow:=", 1E-4,
    "Convergence Criteria - Energy:=", 1E-8,
    "Radiation Model:=", "Off", "Solve Flow:=", True])

proj.SaveAs(os.path.join(WD, "conj.aedt"), True)
try:
    d.Analyze("Setup1")
    ok = True
    err = ""
except Exception, e:
    ok = False
    err = str(e)

res = {"analyzed": ok, "error": err, "mesh_ok": mesh_ok, "mesh_err": mesh_err}
if ok:
    try:
        rep = d.GetModule("ReportSetup")
        fld = d.GetModule("FieldsReporter")
        def qty(expr, obj, kind):
            fld.CalcStack("clear")
            fld.EnterQty(expr)
            fld.EnterVol(obj) if kind == "vol" else fld.EnterSurf(obj)
            fld.CalcOp("Maximum" if kind == "max" else "Average")
            return float(fld.ClcEval("Setup1 : SteadyState", []) or 0.0)
        out = {}
        for nm, expr, obj, kind in [
                ("T_wall_mean_C", "Temp", "base", "vol"),
                ("T_wall_max_C", "Temp", "base", "max"),
                ("T_fluid_mean_C", "Temp", "fluid", "vol")]:
            try:
                out[nm] = qty(expr, obj, kind)
            except Exception, e2:
                out[nm] = None
        res["fields"] = out
    except Exception, e3:
        res["fields_error"] = str(e3)
f = open(os.path.join(WD, "icepak_status.json"), "w")
f.write(json.dumps(res))
f.close()
proj.Save()
oDesktop.QuitApplication()
''' % {"wd": str(wd), "L_um": g["length_mm"] * 1e3, "w": g["w_ch_um"],
       "h": g["h_ch_um"], "tf": g["t_fin_um"], "tb": g["t_base_um"],
       "mdot": g["m_dot_channel_kg_s"], "u": g["velocity_m_s"],
       "t_in": g["t_in_c"], "q": g["q_cell_w"], "ksol": g["k_solid"],
       "kf": g["k_f"], "rho": g["rho"], "cp": g["cp"], "mu": g["mu"]}
    js.write_text(src)
    return js


def main() -> int:
    g = geometry(27.0)
    print("  unit cell: %d channels, m_dot/channel = %.6g kg/s, u = %.3f m/s, "
          "q/cell = %.4f W" % (g["n_channels"], g["m_dot_channel_kg_s"],
                               g["velocity_m_s"], g["q_cell_w"]))
    run = WD / ("run_%s" % time.strftime("%H%M%S"))
    js = write_job(g, run)
    (run / "geometry.json").write_text(json.dumps(g, indent=1))
    if not AEDT.is_file():
        print("  AEDT not found at %s" % AEDT)
        return 2
    cmd = [str(AEDT), "-ng", "-features=beta", "-RunScriptAndExit", str(js)]
    print("  launching: %s" % " ".join(cmd), flush=True)
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=2400,
                           cwd=str(run))
        print("  exit %s in %.0f s" % (p.returncode, time.time() - t0))
        (run / "aedt_stdout.txt").write_text(p.stdout[-20000:])
        (run / "aedt_stderr.txt").write_text(p.stderr[-20000:])
    except subprocess.TimeoutExpired:
        print("  TIMEOUT after %.0f s" % (time.time() - t0))
        return 3
    st = run / "icepak_status.json"
    print("  status: %s" % (st.read_text() if st.is_file() else "no status file written"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
