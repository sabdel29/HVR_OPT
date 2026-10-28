"""Second licence probe: Maxwell 3D DC conduction (matrix route) and Icepak conduction."""
import json, sys, time
from pathlib import Path
work = Path(sys.argv[1]); work.mkdir(parents=True, exist_ok=True)
out = {}
L, W, T = 1.0, 0.1, 0.01


def msgs(app):
    try:
        return [m for m in app.odesktop.GetMessages(app.project_name, app.design_name, 0)
                if "error" in m.lower()]
    except Exception:
        return []


from ansys.aedt.core import Maxwell3d
try:
    t0 = time.time()
    m = Maxwell3d(project=str(work / "mx2.aedt"), design="dc", solution_type="DCConduction",
                  non_graphical=True, new_desktop=True, version="2026.1", close_on_exit=True)
    m.modeler.model_units = "mm"
    m.modeler.create_box([0, 0, 0], [L, W, T], name="bar", material="copper")
    f0 = m.modeler.get_faceid_from_position([0, W / 2, T / 2], assignment="bar")
    f1 = m.modeler.get_faceid_from_position([L, W / 2, T / 2], assignment="bar")
    m.assign_current([f0], amplitude=1.0, name="I1")
    m.assign_voltage([f1], amplitude=0.0, name="V0")
    try:
        m.assign_matrix(assignment=["I1"], matrix_name="M1")
    except Exception as e:
        print("matrix assign failed:", str(e)[:120])
    m.create_setup("S1")
    t1 = time.time(); ok = m.analyze_setup("S1"); t2 = time.time()
    q = {}
    for cat in ("Matrix", "Conductance", "Resistance", "Loss"):
        try:
            q[cat] = m.post.available_report_quantities(quantities_category=cat)
        except Exception as e:
            q[cat] = str(e)[:80]
    errs = [e for e in msgs(m) if "licen" in e.lower()]
    out["maxwell_dc"] = {"solved": bool(ok), "licence_errors": len(errs),
                         "quantities": q, "build_s": round(t1 - t0, 1),
                         "solve_s": round(t2 - t1, 2)}
    print(json.dumps(out["maxwell_dc"])[:600], flush=True)
    m.release_desktop(True, True)
except Exception as e:
    out["maxwell_dc"] = {"solved": False, "error": str(e)[:300]}
    print(json.dumps(out["maxwell_dc"]), flush=True)

from ansys.aedt.core import Icepak
try:
    t0 = time.time()
    ip = Icepak(project=str(work / "ip2.aedt"), design="cond", non_graphical=True,
                new_desktop=True, version="2026.1", close_on_exit=True)
    ip.modeler.model_units = "mm"
    ip.modeler.create_box([0, 0, 0], [10, 10, 1], name="blk", material="Al-Extruded")
    ip.assign_solid_block("blk", power_assignment="1W")
    s = ip.create_setup("S1")
    s.props["Include Flow"] = False
    s.props["Include Gravity"] = False
    s.update()
    t1 = time.time(); ok = ip.analyze_setup("S1"); t2 = time.time()
    errs = [e for e in msgs(ip) if "licen" in e.lower()]
    out["icepak"] = {"solved": bool(ok), "licence_errors": len(errs),
                     "build_s": round(t1 - t0, 1), "solve_s": round(t2 - t1, 2)}
    print(json.dumps(out["icepak"]), flush=True)
    ip.release_desktop(True, True)
except Exception as e:
    out["icepak"] = {"solved": False, "error": str(e)[:300]}
    print(json.dumps(out["icepak"]), flush=True)
(work / "probe2.json").write_text(json.dumps(out, indent=2))
