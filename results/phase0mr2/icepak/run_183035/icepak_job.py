# -*- coding: utf-8 -*-
# Phase-0M-R2 conjugate single-channel benchmark. IronPython 2.7 (AEDT embeds 2.7).
import ScriptEnv, os, json
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")
oDesktop.RestoreWindow()
WD = r"/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0mr2/icepak/run_183035"
proj = oDesktop.NewProject()
proj.InsertDesign("Icepak", "conj", "SteadyState", "")
d = proj.SetActiveDesign("conj")
ed = d.SetActiveEditor("3D Modeler")

d.SetDesignSettings(["NAME:Design Settings Data", "Perform Minimal validation:=", False,
                     "Default Fluid Material:=", "water_liquid",
                     "Default Solid Material:=", "Si",
                     "Default Surface Material:=", "Steel-oxidised-surface",
                     "AmbientTemperature:=", "25.0cel",
                     "AmbientPressure:=", "0n_per_meter_sq",
                     "AmbientRadiationTemperature:=", "25.0cel",
                     "Gravity Vector CS ID:=", 1, "Gravity Vector Axis:=", "Z",
                     "Gravity Direction:=", 1, "Export After Simulation:=", False,
                     "Solve Inside:=", True])

# ---- geometry, in micrometres -------------------------------------------------------
ed.SetModelUnits(["NAME:Units Parameter", "Units:=", "um", "Rescale:=", False])
Lz = 22360          # flow direction
w  = 50             # channel width
h  = 300             # channel height
tf = 50            # fin thickness (two half fins = tf total in the unit cell)
tb = 100            # base thickness
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
box("base", 0, 0, 0, cw, Lz, tb, "Si")
box("fin_l", 0, 0, tb, tf/2.0, Lz, h, "Si")
box("fin_r", tf/2.0 + w, 0, tb, tf/2.0, Lz, h, "Si")
# fluid: the channel itself
box("fluid", tf/2.0, 0, tb, w, Lz, h, "water_liquid")

mod = d.GetModule("BoundarySetup")

# ---- inlet: stated mass flow and temperature ----------------------------------------
mod.AssignOpeningBoundary(["NAME:inlet", "Faces:=", [],
    "Objects:=", ["fluid"], "Type:=", "Mass Flow",
    "MassFlowRate:=", "0.000121076 kg_per_s",
    "Temperature:=", "25.0cel",
    "External Rad. Temperature:=", "25.0cel",
    "Inlet Type:=", "Mass Flow", "X Velocity:=", "0m_per_sec",
    "Y Velocity:=", "8.16979 m_per_sec", "Z Velocity:=", "0m_per_sec"])

# ---- heat into the base --------------------------------------------------------------
mod.AssignBlockBoundary(["NAME:base_src", "Objects:=", ["base"],
    "Block Type:=", "Total Power", "Use External Conditions:=", False,
    "Total Power:=", "4.4843 W"])

oDesign = d
setup = d.GetModule("AnalysisSetup")
setup.InsertSetup("SteadyState", ["NAME:Setup1", "Enabled:=", True,
    "Flow Regime:=", "Laminar", "Include Temperature:=", True,
    "Include Flow:=", True, "Include Gravity:=", False,
    "Solution Initialization - X Velocity:=", "0m_per_sec",
    "Solution Initialization - Y Velocity:=", "8.16979 m_per_sec",
    "Solution Initialization - Z Velocity:=", "0m_per_sec",
    "Solution Initialization - Temperature:=", "25.0cel",
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

res = {"analyzed": ok, "error": err}
f = open(os.path.join(WD, "icepak_status.json"), "w")
f.write(json.dumps(res))
f.close()
proj.Save()
oDesktop.QuitApplication()
