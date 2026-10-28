"""Maxwell 3D DC conduction licence probe via the conductance matrix."""
import json, sys, time
from pathlib import Path
from ansys.aedt.core import Maxwell3d
from ansys.aedt.core.modules.boundary.maxwell_boundary import MatrixElectric
work = Path(sys.argv[1]); work.mkdir(parents=True, exist_ok=True)
L, W, T = 1.0, 0.1, 0.01
t0 = time.time()
m = Maxwell3d(project=str(work / "mx3.aedt"), design="dc", solution_type="DCConduction",
              non_graphical=True, new_desktop=True, version="2026.1", close_on_exit=True)
print("solution type:", m.solution_type, flush=True)
m.modeler.model_units = "mm"
m.modeler.create_box([0, 0, 0], [L, W, T], name="bar", material="copper")
f0 = m.modeler.get_faceid_from_position([0, W/2, T/2], assignment="bar")
f1 = m.modeler.get_faceid_from_position([L, W/2, T/2], assignment="bar")
m.assign_voltage([f0], amplitude=1.0, name="V1")
m.assign_voltage([f1], amplitude=0.0, name="V0")
m.assign_matrix(MatrixElectric(signal_sources=["V1"], ground_sources=["V0"],
                               matrix_name="M1"))
s = m.create_setup("S1")
t1 = time.time(); ok = m.analyze_setup("S1"); t2 = time.time()
res = {"solved": bool(ok), "build_s": round(t1 - t0, 1), "solve_s": round(t2 - t1, 2)}
try:
    q = m.post.available_report_quantities(quantities_category="Conductance")
    res["conductance_quantities"] = q
    if q:
        d = m.post.get_solution_data(expressions=q[0])
        res["G_S"] = d.data_real()[0] if d else None
        res["R_ohm"] = (1.0 / res["G_S"]) if res.get("G_S") else None
except Exception as e:
    res["post_error"] = str(e)[:200]
sig = float(m.materials["copper"].conductivity.value)
res["rhoLA_ohm"] = (L * 1e-3) / (sig * W * 1e-3 * T * 1e-3)
try:
    res["licence_messages"] = sum("licen" in x.lower() for x in
                                  m.odesktop.GetMessages(m.project_name, m.design_name, 0))
except Exception:
    pass
print(json.dumps(res), flush=True)
(work / "probe3.json").write_text(json.dumps(res, indent=2))
m.release_desktop(True, True)
