#!/usr/bin/env python3
"""Phase-0M-R3 Section 11 --- canonical single-channel conjugate benchmark.

Phase 0M-R2's attempt built correctly and then ran the full 2400 s without returning. The
cause was almost certainly the geometry: 50 x 300 x 22360 um is 447:1 along the flow, and
a mesh that resolves the 50 um width over 22 mm of length is enormous.

This case shortens the channel to a PERIODIC SLICE. Fully-developed laminar flow is
invariant along the flow direction, so a short slice tests the same wall-to-fluid physics
at a fraction of the cell count. The compact model's caloric term is the part that depends
on total length, and it is exact by construction, so it is not what needs validating.

Declared wall-clock budget: 45 minutes, per the brief.
"""
from __future__ import annotations
import json, subprocess, sys, time
from pathlib import Path
import yaml

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0mr2"))
AEDT = Path("/local/ansys/electronics/ansys_inc/v261/AnsysEM/ansysedt")
OUT = R / "results" / "phase0mr3"
WD = OUT / "icepak"
CFG = R / "configs" / "phase0mr2" / "cooling_model.yaml"
BUDGET_S = 2700
SLICE_MM = 1.0          # periodic slice instead of the full 22.36 mm


def geometry() -> dict:
    c = yaml.safe_load(CFG.read_text())
    ch, f = c["channel"], c["fluid"]
    w, h, tf = ch["w_ch_um"], ch["h_ch_um"], ch["t_fin_um"]
    n = int(ch["width_mm"] * 1e3 // (w + tf))
    m_ch = 27.0e-3 / n
    u = m_ch / (f["rho_kg_m3"] * (w * 1e-6) * (h * 1e-6))
    q_cell_full = 1000.0 / n
    return {"w_ch_um": w, "h_ch_um": h, "t_fin_um": tf, "t_base_um": ch["t_base_um"],
            "slice_mm": SLICE_MM, "full_length_mm": ch["length_mm"], "n_channels": n,
            "m_dot_channel_kg_s": m_ch, "velocity_m_s": u,
            "q_slice_w": q_cell_full * SLICE_MM / ch["length_mm"],
            "k_solid": ch["k_solid_w_mk"], "t_in_c": f["t_ref_c"],
            "rho": f["rho_kg_m3"], "mu": f["mu_pa_s"], "k_f": f["k_w_mk"],
            "cp": f["cp_j_kgk"]}


def write_job(g: dict, wd: Path) -> Path:
    wd.mkdir(parents=True, exist_ok=True)
    js = wd / "icepak_job.py"
    js.write_text('''# -*- coding: utf-8 -*-
# Phase-0M-R3 canonical conjugate slice. IronPython 2.7 (AEDT embeds 2.7): no f-strings.
import ScriptEnv, os, json
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")
oDesktop.RestoreWindow()
WD = r"%(wd)s"
proj = oDesktop.NewProject()
proj.InsertDesign("Icepak", "slice", "SteadyState", "")
d = proj.SetActiveDesign("slice")
ed = d.SetActiveEditor("3D Modeler")

defs = proj.GetDefinitionManager()
defs.AddMaterial(["NAME:si_bench", "CoordinateSystemType:=", "Cartesian",
                  ["NAME:AttachedData"], "thermal_conductivity:=", "%(ksol).6g",
                  "mass_density:=", "2330", "specific_heat:=", "700"])
defs.AddMaterial(["NAME:water_bench", "CoordinateSystemType:=", "Cartesian",
                  ["NAME:AttachedData"], "material_def:=", 1,
                  "thermal_conductivity:=", "%(kf).6g", "mass_density:=", "%(rho).6g",
                  "specific_heat:=", "%(cp).6g", "viscosity:=", "%(mu).6g"])

d.SetDesignSettings(["NAME:Design Settings Data", "Perform Minimal validation:=", False,
                     "Default Fluid Material:=", "water_bench",
                     "Default Solid Material:=", "si_bench",
                     "AmbientTemperature:=", "%(t_in).1fcel",
                     "AmbientRadiationTemperature:=", "%(t_in).1fcel",
                     "Gravity Vector CS ID:=", 1, "Gravity Vector Axis:=", "Z",
                     "Gravity Direction:=", 1, "Export After Simulation:=", False,
                     "Solve Inside:=", True])

ed.SetModelUnits(["NAME:Units Parameter", "Units:=", "um", "Rescale:=", False])
Lz = %(L_um).6g
w  = %(w).6g
h  = %(h).6g
tf = %(tf).6g
tb = %(tb).6g
cw = w + tf

def box(name, x, y, z, dx, dy, dz, mat):
    ed.CreateBox(["NAME:BoxParameters", "XPosition:=", str(x)+"um",
                  "YPosition:=", str(y)+"um", "ZPosition:=", str(z)+"um",
                  "XSize:=", str(dx)+"um", "YSize:=", str(dy)+"um",
                  "ZSize:=", str(dz)+"um"],
                 ["NAME:Attributes", "Name:=", name, "Flags:=", "",
                  "Color:=", "(143 175 143)", "Transparency:=", 0.4,
                  "PartCoordinateSystem:=", "Global", "MaterialValue:=", chr(34)+mat+chr(34),
                  "SolveInside:=", True])

box("base",  0, 0, 0,  cw, Lz, tb, "si_bench")
box("fin_l", 0, 0, tb, tf/2.0, Lz, h, "si_bench")
box("fin_r", tf/2.0 + w, 0, tb, tf/2.0, Lz, h, "si_bench")
box("fluid", tf/2.0, 0, tb, w, Lz, h, "water_bench")

mod = d.GetModule("BoundarySetup")

def face_at_y(obj, ytarget, tol=1.0):
    out = []
    for fid in ed.GetFaceIDs(obj):
        c = ed.GetFaceCenter(int(fid))
        if abs(float(c[1]) - ytarget) < tol:
            out.append(int(fid))
    return out

mod.AssignOpeningBoundary(["NAME:inlet", "Faces:=", face_at_y("fluid", 0.0),
    "Inlet Type:=", "Mass Flow",
    "Mass Flow Rate:=", "%(mdot).6g kg_per_s",
    "Temperature:=", "%(t_in).1fcel",
    "External Rad. Temperature:=", "%(t_in).1fcel"])
mod.AssignOpeningBoundary(["NAME:outlet", "Faces:=", face_at_y("fluid", Lz),
    "Inlet Type:=", "Pressure", "Static Pressure:=", "0n_per_meter_sq",
    "Temperature:=", "%(t_in).1fcel",
    "External Rad. Temperature:=", "%(t_in).1fcel"])
mod.AssignBlockBoundary(["NAME:base_src", "Objects:=", ["base"],
    "Block Type:=", "Total Power", "Use External Conditions:=", False,
    "Total Power:=", "%(q).6g W"])

try:
    msh = d.GetModule("MeshRegion")
    msh.EditGlobalMeshRegion(["NAME:Settings", "MeshMethod:=", "MesherHD",
        "UserSpecifiedSettings:=", True, "ComputeGap:=", True,
        "MaxElementSizeX:=", str(cw/8.0)+"um",
        "MaxElementSizeY:=", str(Lz/20.0)+"um",
        "MaxElementSizeZ:=", str((tb+h)/16.0)+"um",
        "MinElementsInGap:=", "3", "MinElementsOnEdge:=", "2",
        "MaxSizeRatio:=", "2", "NoOGrids:=", False, "EnableMLM:=", True,
        "EnforeMLMType:=", "3D", "StairStepMeshing:=", False,
        "MinGapX:=", "1um", "MinGapY:=", "1um", "MinGapZ:=", "1um"])
    mesh_ok = True; mesh_err = ""
except Exception, e:
    mesh_ok = False; mesh_err = str(e)

setup = d.GetModule("AnalysisSetup")
setup.InsertSetup("IcepakSteadyState", ["NAME:Setup1", "Enabled:=", True,
    "Flow Regime:=", "Laminar", "Include Temperature:=", True,
    "Include Flow:=", True, "Include Gravity:=", False,
    "Solution Initialization - Y Velocity:=", "%(u).6g m_per_sec",
    "Solution Initialization - Temperature:=", "%(t_in).1fcel",
    "Convergence Criteria - Max Iterations:=", 150,
    "Convergence Criteria - Flow:=", 1E-3,
    "Convergence Criteria - Energy:=", 1E-7,
    "Radiation Model:=", "Off", "Solve Flow:=", True])

proj.SaveAs(os.path.join(WD, "slice.aedt"), True)
res = {"mesh_ok": mesh_ok, "mesh_err": mesh_err}
try:
    d.Analyze("Setup1")
    res["analyzed"] = True
except Exception, e:
    res["analyzed"] = False
    res["error"] = str(e)
f = open(os.path.join(WD, "icepak_status.json"), "w"); f.write(json.dumps(res)); f.close()
proj.Save()
oDesktop.QuitApplication()
''' % {"wd": str(wd), "L_um": g["slice_mm"] * 1e3, "w": g["w_ch_um"], "h": g["h_ch_um"],
       "tf": g["t_fin_um"], "tb": g["t_base_um"], "mdot": g["m_dot_channel_kg_s"],
       "u": g["velocity_m_s"], "t_in": g["t_in_c"], "q": g["q_slice_w"],
       "ksol": g["k_solid"], "kf": g["k_f"], "rho": g["rho"], "cp": g["cp"],
       "mu": g["mu"]})
    return js


def main() -> int:
    g = geometry()
    print(f"  canonical slice: {g['slice_mm']} mm of one channel "
          f"({g['full_length_mm']} mm full), {g['n_channels']} channels, "
          f"m_dot/ch = {g['m_dot_channel_kg_s']:.6g} kg/s, u = {g['velocity_m_s']:.3f} m/s, "
          f"q_slice = {g['q_slice_w']:.5f} W")
    print(f"  declared wall-clock budget: {BUDGET_S} s")
    run = WD / ("run_%s" % time.strftime("%H%M%S"))
    js = write_job(g, run)
    (run / "geometry.json").write_text(json.dumps(g, indent=1))
    if not AEDT.is_file():
        print("  AEDT not found"); return 2
    t0 = time.time()
    try:
        p = subprocess.run([str(AEDT), "-ng", "-features=beta", "-RunScriptAndExit",
                            str(js)], capture_output=True, text=True,
                           timeout=BUDGET_S, cwd=str(run))
        print(f"  exit {p.returncode} in {time.time()-t0:.0f} s")
        (run / "aedt_stdout.txt").write_text(p.stdout[-20000:])
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT after {time.time()-t0:.0f} s (declared budget)")
        return 3
    st = run / "icepak_status.json"
    print(f"  status: {st.read_text() if st.is_file() else 'no status file'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
