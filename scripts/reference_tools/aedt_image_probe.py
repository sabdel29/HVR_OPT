"""Probe native AEDT image export and field plots in Mechanical (graphical, Xvfb)."""
import json, sys, time, os
sys.path.insert(0, os.path.dirname(__file__))
from ansys.aedt.core import Mechanical
import aedt_common as C
out = {}
me = C.launch(Mechanical, "img_probe", "bar", solution_type="Thermal")
me.modeler.model_units = "mm"
C.add_material(me, "cu_analog", k=58.0)
me.modeler.create_box([0, 0, 0], [1, 0.2, 0.05], name="bar", material="cu_analog")
f0 = me.modeler.get_faceid_from_position([0, 0.1, 0.025], assignment="bar")
f1 = me.modeler.get_faceid_from_position([1, 0.1, 0.025], assignment="bar")
me.assign_uniform_temperature([f1], 0)
me.assign_heat_flux([f0], heat_flux_type="Total Power", value="1W")
me.create_setup("S1"); me.analyze_setup("S1")
W = C.WORK
def tryit(tag, fn):
    try:
        r = fn(); out[tag] = (r if not isinstance(r, (bytes,)) else "bytes")
    except Exception as e:
        out[tag] = "ERR " + str(e)[:160]
p1 = str(W / "img_native_model.png")
tryit("native_model", lambda: me.modeler.oeditor.ExportModelImageToFile(
    p1, 1200, 700, ["NAME:SaveImageParams", "ShowAxis:=", "True", "ShowGrid:=", "False",
                    "ShowRuler:=", "True", "ShowRegion:=", "Default", "Selections:=", "",
                    "FieldPlotSelections:=", "", "Orientation:=", ""]))
out["native_model_exists"] = os.path.exists(p1)
tryit("design_preview", lambda: me.export_design_preview_to_jpg(str(W / "img_preview.jpg")))
out["design_preview_exists"] = os.path.exists(str(W / "img_preview.jpg"))
tryit("facelist", lambda: me.modeler.create_face_list([f0], name="fl0"))
tryit("mean_fl0", lambda: me.post.get_scalar_field_value("Temp", scalar_function="Mean", object_name="fl0", object_type="surface"))
tryit("fp_surface", lambda: bool(me.post.create_fieldplot_surface(["bar"], "Temp", plot_name="Tsurf")))
try:
    names = me.post.field_plot_names
    out["field_plot_names"] = list(names)
except Exception as e:
    out["field_plot_names"] = "ERR " + str(e)[:100]
p2 = str(W / "img_field.png")
tryit("native_field", lambda: me.post.ofieldsreporter.ExportPlotImageToFile(p2, "", "Tsurf", ""))
out["native_field_exists"] = os.path.exists(p2)
tryit("mesh_stats", lambda: me.export_mesh_stats("S1", output_file=str(W / "mesh_stats.ms")) if hasattr(me, "export_mesh_stats") else "n/a")
print(json.dumps(out, default=str), flush=True)
me.release_desktop(True, True)
