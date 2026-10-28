"""Licence/automation smoke test: one copper bar, Q3D DC resistance vs rho*L/A."""
import json, sys, time
from pathlib import Path
from ansys.aedt.core import Q3d

work = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/aedt_work")
work.mkdir(parents=True, exist_ok=True)
t0 = time.time()
q = Q3d(project=str(work / "smoke.aedt"), design="bar", non_graphical=True,
        new_desktop=True, version="2026.1", close_on_exit=True)
L, W, T = 1.0, 0.1, 0.01                      # mm
q.modeler.model_units = "mm"
bar = q.modeler.create_box([0, 0, 0], [L, W, T], name="bar", material="copper")
q.auto_identify_nets()
fx0 = q.modeler.get_faceid_from_position([0, W / 2, T / 2], assignment="bar")
fx1 = q.modeler.get_faceid_from_position([L, W / 2, T / 2], assignment="bar")
q.source(fx0, name="src")
q.sink(fx1, name="snk")
s = q.create_setup("S1")
s.props["AC"]["Enabled"] = False
s.props["Cap"]["Enabled"] = False
s.props["DC"]["Enabled"] = True
s.update()
t1 = time.time()
q.analyze_setup("S1")
t2 = time.time()
cats = q.post.available_report_quantities(quantities_category="DCR Matrix")
print("DCR quantities:", cats)
expr = cats[0] if cats else "DCR(bar:src,bar:src)"
d = q.post.get_solution_data(expressions=expr, setup_sweep_name="S1 : LastAdaptive")
val = d.data_real()[0] if d else None
units = d.units_data.get(expr) if d else None
sigma = q.materials["copper"].conductivity.value
out = {"expr": expr, "value": val, "units": units, "copper_sigma_S_per_m": sigma,
       "build_s": round(t1 - t0, 1), "solve_s": round(t2 - t1, 2)}
print(json.dumps(out))
(work / "smoke_result.json").write_text(json.dumps(out, indent=2))
q.release_desktop(close_projects=True, close_desktop=True)
