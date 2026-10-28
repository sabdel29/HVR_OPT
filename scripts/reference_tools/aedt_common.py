"""Shared helpers for the AEDT reference runs (AEDT 2026 R1 via PyAEDT 1.1).

Q3D and Maxwell DC conduction are NOT licensed here (FlexNet 'no such feature' on
solve, recorded in tool_evidence/README.md). AEDT Mechanical (thermal and structural)
and Icepak ARE licensed. Steady conduction div(k grad T) = 0 is the same operator as
div(sigma grad V) = 0, so AEDT Mechanical thermal is used as the commercial FEM
reference for every DC-conduction stage under the exact analogy
    k <-> sigma (scaled by K_SCALE),  T <-> V,  heat flow <-> current.
"""
from __future__ import annotations

import json
import sys
import os
import platform
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hvr_scratch import path as scratch                             # noqa: E402

R = Path(__file__).resolve().parents[2]
EVID = R / "presentation" / "prelim_hvr" / "tool_evidence"
WORK = Path(os.environ["AEDT_WORK"]) if "AEDT_WORK" in os.environ else scratch("aedt_ref")
VERSION = "2026.1"
#: sigma [S/m] is mapped to k [W/mK] = sigma * K_SCALE, so copper (5.8e7 S/m) maps
#: to 58 W/mK. R_electrical = R_thermal * K_SCALE exactly, because the problem is linear.
K_SCALE = 1.0e-6


def hardware():
    cpu = "unknown"
    try:
        for line in open("/proc/cpuinfo"):
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    return {"cpu": cpu, "logical_cpus": os.cpu_count(), "host_os": platform.platform()}


def launch(cls, project, design, **kw):
    graphical = os.environ.get("AEDT_GRAPHICAL", "0") == "1"
    WORK.mkdir(parents=True, exist_ok=True)
    return cls(project=str(WORK / f"{project}.aedt"), design=design,
               non_graphical=not graphical, new_desktop=True, version=VERSION,
               close_on_exit=True, **kw)


def add_material(app, name, k=None, E=None, nu=None, cte=None, rho=None):
    """rho (kg/m^3): AEDT structural designs refuse a material without mass density;
    with no body force it does not enter a static thermal-stress solution."""
    m = app.materials.add_material(name)
    if k is not None:
        m.thermal_conductivity = k
    if rho is not None:
        m.mass_density = rho
    if E is not None:
        m.youngs_modulus = E
    if nu is not None:
        m.poissons_ratio = nu
    if cte is not None:
        m.thermal_expansion_coefficient = cte
    return name


def try_image(app, path, plot=None, width=1400, height=900):
    """Export an image from the actual AEDT session (native oEditor call; the PyAEDT
    wrappers fail in this AEDT/PyAEDT pairing). Requires a graphical session (Xvfb)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        app.modeler.fit_all()
    except Exception:
        pass
    try:
        app.modeler.oeditor.ExportModelImageToFile(
            str(path), width, height,
            ["NAME:SaveImageParams", "ShowAxis:=", "True", "ShowGrid:=", "False",
             "ShowRuler:=", "True", "ShowRegion:=", "Default", "Selections:=", "",
             "FieldPlotSelections:=", plot or "", "Orientation:=", ""])
    except Exception as e:                                    # pragma: no cover
        print("image export failed:", str(e)[:160])
    return path.exists()


def try_field_plot(app, obj_names, quantity="Temp", setup="S1 : LastAdaptive",
                   name="FieldPlot1"):
    """Native volume field plot; returns the plot name or None."""
    try:
        fr = app.odesign.GetModule("FieldsReporter")
        fr.CreateFieldPlot(
            ["NAME:" + name, "SolutionName:=", setup, "UserSpecifyName:=", 0,
             "UserSpecifyFolder:=", 0, "QuantityName:=", quantity,
             "PlotFolder:=", quantity, "StreamlinePlot:=", False,
             "AdjacentSidePlot:=", False, "FullModelPlot:=", False,
             "IntrinsicVar:=", "", "PlotGeomInfo:=",
             [1, "Volume", "ObjList", len(obj_names)] + list(obj_names),
             "FilterBoxes:=", [0]], "Volume")
        return name
    except Exception as e:
        print("field plot failed:", str(e)[:160])
        return None


def write_evidence(stage, setup, runtime, result, readme):
    d = EVID / stage
    d.mkdir(parents=True, exist_ok=True)
    (d / "setup.json").write_text(json.dumps(setup, indent=2, default=str))
    (d / "runtime.json").write_text(json.dumps(runtime, indent=2, default=str))
    (d / "result.json").write_text(json.dumps(result, indent=2, default=str))
    (d / "README.md").write_text(readme)
    return d
