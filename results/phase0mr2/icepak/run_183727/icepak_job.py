# -*- coding: utf-8 -*-
# Phase-0M-R2 conjugate single-channel benchmark. IronPython 2.7 (AEDT embeds 2.7).
import ScriptEnv, os, json
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")
oDesktop.RestoreWindow()
WD = r"/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0mr2/icepak/run_183727"
proj = oDesktop.NewProject()
proj.InsertDesign("Icepak", "conj", "SteadyState", "")
d = proj.SetActiveDesign("conj")
ed = d.SetActiveEditor("3D Modeler")

# Materials are DEFINED here rather than taken from the Icepak library, so the CFD case
# and the compact model provably use the same numbers. A library lookup would silently
# introduce a different property set and make any disagreement uninterpretable.
defs = proj.GetDefinitionManager()
defs.AddMaterial(["NAME:si_bench", "CoordinateSystemType:=", "Cartesian",
                  ["NAME:AttachedData"], "thermal_conductivity:=", "130",
                  "mass_density:=", "2330", "specific_heat:=", "700"])
defs.AddMaterial(["NAME:water_bench", "CoordinateSystemType:=", "Cartesian",
                  ["NAME:AttachedData"], "material_def:=", 1,
                  "thermal_conductivity:=", "0.644",
                  "mass_density:=", "988", "specific_heat:=", "4181",
                  "viscosity:=", "0.000547"])

d.SetDesignSettings(["NAME:Design Settings Data", "Perform Minimal validation:=", False,
                     "Default Fluid Material:=", "water_bench",
                     "Default Solid Material:=", "si_bench",
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
    "Mass Flow Rate:=", "0.000121076 kg_per_s",
    "Temperature:=", "25.0cel",
    "External Rad. Temperature:=", "25.0cel"])

# ---- outlet: fixed static pressure ---------------------------------------------------
mod.AssignOpeningBoundary(["NAME:outlet", "Faces:=", f_out,
    "Inlet Type:=", "Pressure",
    "Static Pressure:=", "0n_per_meter_sq",
    "Temperature:=", "25.0cel",
    "External Rad. Temperature:=", "25.0cel"])

# ---- heat into the base --------------------------------------------------------------
mod.AssignBlockBoundary(["NAME:base_src", "Objects:=", ["base"],
    "Block Type:=", "Total Power", "Use External Conditions:=", False,
    "Total Power:=", "4.4843 W"])

oDesign = d
setup = d.GetModule("AnalysisSetup")
# AEDT 2026 R1 routes every string tried so far to the Optimetrics setup factory. Probe
# the module for the names it will actually accept and record them, so the failure is
# diagnosable rather than a guess.
try:
    names = list(setup.GetSetups())
except Exception, e:
    names = ["GetSetups failed: " + str(e)]
fdbg = open(os.path.join(WD, "setup_probe.txt"), "w")
fdbg.write("existing setups: " + repr(names) + chr(10))
for cand in ["IcepakSteadyState", "SteadyState", "Transient", "TemperatureAndFlow",
             "SteadyTemperatureAndFlow", "TemperatureOnly", "FlowOnly"]:
    try:
        setup.InsertSetup(cand, ["NAME:probe_" + cand, "Enabled:=", True])
        fdbg.write("ACCEPTED: " + cand + chr(10))
        setup.DeleteSetups(["probe_" + cand])
    except Exception, e:
        fdbg.write("rejected: " + cand + " -- " + str(e)[:120] + chr(10))
fdbg.close()
setup.InsertSetup("IcepakSteadyState", ["NAME:Setup1", "Enabled:=", True,
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
