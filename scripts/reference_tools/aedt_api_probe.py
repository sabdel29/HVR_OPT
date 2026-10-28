"""Which post-processing / image calls work in this AEDT Mechanical session?"""
import json, sys, time
sys.path.insert(0, __import__("os").path.dirname(__file__))
from ansys.aedt.core import Mechanical
import aedt_common as C
out = {}
me = C.launch(Mechanical, "api_probe", "bar", solution_type="Thermal")
me.modeler.model_units = "mm"
C.add_material(me, "cu_analog", k=58.0)
me.modeler.create_box([0, 0, 0], [1, 0.1, 0.01], name="bar", material="cu_analog")
f0 = me.modeler.get_faceid_from_position([0, 0.05, 0.005], assignment="bar")
f1 = me.modeler.get_faceid_from_position([1, 0.05, 0.005], assignment="bar")
me.assign_uniform_temperature([f1], 0)
try:
    me.assign_heat_flux([f0], heat_flux_type="Total Power", value="1W")
    out["heat_flux_total_power"] = True
except Exception as e:
    out["heat_flux_total_power"] = str(e)[:150]
me.create_setup("S1")
t = time.time(); ok = me.analyze_setup("S1"); out["solve_s"] = round(time.time() - t, 2)
out["solved"] = bool(ok)
for fn, kw in (("max_vol", dict(quantity="Temp", scalar_function="Maximum", object_name="bar", object_type="volume")),
               ("mean_face0", dict(quantity="Temp", scalar_function="Mean", object_name=f0, object_type="surface")),
               ("max_vol_T", dict(quantity="Temperature", scalar_function="Maximum", object_name="bar", object_type="volume"))):
    try:
        out[fn] = me.post.get_scalar_field_value(**kw)
    except Exception as e:
        out[fn] = "ERR " + str(e)[:120]
try:
    out["report_quantities"] = me.post.available_report_quantities()[:20]
except Exception as e:
    out["report_quantities"] = str(e)[:120]
out["model_image"] = C.try_image(me, C.WORK / "probe_model.png")
try:
    pl = me.post.create_fieldplot_volume(["bar"], "Temp", setup="S1 : LastAdaptive")
    out["fieldplot"] = bool(pl)
    out["field_image"] = C.try_image(me, C.WORK / "probe_field.png", plot=pl)
except Exception as e:
    out["fieldplot"] = "ERR " + str(e)[:150]
out["rhoLA_equivalent_K_per_W"] = 1e-3 / (58.0 * 0.1e-3 * 0.01e-3)
print(json.dumps(out, default=str), flush=True)
me.release_desktop(True, True)
