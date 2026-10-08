# -*- coding: utf-8 -*-
# Phase-0M-R3 canonical conjugate slice. IronPython 2.7 (AEDT embeds 2.7): no f-strings.
import ScriptEnv, os, json
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")
oDesktop.RestoreWindow()
WD = r"/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0mr3/icepak/run_014636"
proj = oDesktop.NewProject()
proj.InsertDesign("Icepak", "slice", "SteadyState", "")
d = proj.SetActiveDesign("slice")
ed = d.SetActiveEditor("3D Modeler")

defs = proj.GetDefinitionManager()
defs.AddMaterial(["NAME:si_bench", "CoordinateSystemType:=", "Cartesian",
                  ["NAME:AttachedData"], "thermal_conductivity:=", "130",
                  "mass_density:=", "2330", "specific_heat:=", "700"])
defs.AddMaterial(["NAME:water_bench", "CoordinateSystemType:=", "Cartesian",
                  ["NAME:AttachedData"], "material_def:=", 1,
                  "thermal_conductivity:=", "0.644", "mass_density:=", "988",
                  "specific_heat:=", "4181", "viscosity:=", "0.000547"])

d.SetDesignSettings(["NAME:Design Settings Data", "Perform Minimal validation:=", False,
                     "Default Fluid Material:=", "water_bench",
                     "Default Solid Material:=", "si_bench",
                     "AmbientTemperature:=", "25.0cel",
                     "AmbientRadiationTemperature:=", "25.0cel",
                     "Gravity Vector CS ID:=", 1, "Gravity Vector Axis:=", "Z",
                     "Gravity Direction:=", 1, "Export After Simulation:=", False,
                     "Solve Inside:=", True])

ed.SetModelUnits(["NAME:Units Parameter", "Units:=", "um", "Rescale:=", False])
Lz = 1000
w  = 50
h  = 300
tf = 50
tb = 100
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
    "Mass Flow Rate:=", "0.000121076 kg_per_s",
    "Temperature:=", "25.0cel",
    "External Rad. Temperature:=", "25.0cel"])
mod.AssignOpeningBoundary(["NAME:outlet", "Faces:=", face_at_y("fluid", Lz),
    "Inlet Type:=", "Pressure", "Static Pressure:=", "0n_per_meter_sq",
    "Temperature:=", "25.0cel",
    "External Rad. Temperature:=", "25.0cel"])
mod.AssignBlockBoundary(["NAME:base_src", "Objects:=", ["base"],
    "Block Type:=", "Total Power", "Use External Conditions:=", False,
    "Total Power:=", "0.20055 W"])

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
    "Solution Initialization - Y Velocity:=", "8.16979 m_per_sec",
    "Solution Initialization - Temperature:=", "25.0cel",
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
