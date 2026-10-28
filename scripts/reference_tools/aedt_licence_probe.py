"""Probe which AEDT 2026 R1 solvers are actually licensed, on a trivial copper bar.

Prints one JSON line per solver. Licence-server details are never written: only
whether the solve ran and what it returned.
"""
import json, sys, time, traceback
from pathlib import Path

work = Path(sys.argv[1]); work.mkdir(parents=True, exist_ok=True)
which = sys.argv[2:] or ["maxwell_dc", "icepak", "mech_thermal", "mech_struct"]
L, W, T = 1.0, 0.1, 0.01          # mm
out = {}


def done(tag, **kw):
    out[tag] = kw
    print(json.dumps({tag: kw}), flush=True)


def licence_failed(app):
    try:
        msgs = app.odesktop.GetMessages(app.project_name, app.design_name, 0)
        return any("license" in m.lower() for m in msgs)
    except Exception:
        return None


if "maxwell_dc" in which:
    from ansys.aedt.core import Maxwell3d
    try:
        t0 = time.time()
        m = Maxwell3d(project=str(work / "probe_mx.aedt"), design="dc",
                      solution_type="DCConduction", non_graphical=True,
                      new_desktop=True, version="2026.1", close_on_exit=True)
        m.modeler.model_units = "mm"
        m.modeler.create_box([0, 0, 0], [L, W, T], name="bar", material="copper")
        f0 = m.modeler.get_faceid_from_position([0, W/2, T/2], assignment="bar")
        f1 = m.modeler.get_faceid_from_position([L, W/2, T/2], assignment="bar")
        m.assign_current([f0], amplitude=1.0, name="I1")
        m.assign_voltage([f1], amplitude=0.0, name="V0")
        m.create_setup("S1")
        t1 = time.time(); ok = m.analyze_setup("S1"); t2 = time.time()
        p = m.post.get_scalar_field_value("Ohmic_Loss", scalar_function="Integrate",
                                          solution="S1 : LastAdaptive",
                                          object_name="bar", object_type="volume")
        sig = float(m.materials["copper"].conductivity.value)
        done("maxwell_dc", solved=bool(ok), licence_error=licence_failed(m),
             R_ohm=p, rhoLA_ohm=(L*1e-3)/(sig*W*1e-3*T*1e-3),
             build_s=round(t1-t0, 1), solve_s=round(t2-t1, 2))
        m.release_desktop(True, True)
    except Exception as e:
        done("maxwell_dc", solved=False, error=str(e)[:300])

if "icepak" in which:
    from ansys.aedt.core import Icepak
    try:
        t0 = time.time()
        ip = Icepak(project=str(work / "probe_ip.aedt"), design="cond",
                    non_graphical=True, new_desktop=True, version="2026.1",
                    close_on_exit=True)
        ip.modeler.model_units = "mm"
        ip.modeler.create_box([0, 0, 0], [10, 10, 1], name="blk", material="Al-Extruded")
        ip.create_source_block("blk", "1W", assign_material=False)
        s = ip.create_setup("S1")
        s.props["Flow Regime"] = "Laminar"
        s.props["Include Flow"] = False
        s.props["Include Gravity"] = False
        s.update()
        t1 = time.time(); ok = ip.analyze_setup("S1"); t2 = time.time()
        done("icepak", solved=bool(ok), licence_error=licence_failed(ip),
             build_s=round(t1-t0, 1), solve_s=round(t2-t1, 2))
        ip.release_desktop(True, True)
    except Exception as e:
        done("icepak", solved=False, error=str(e)[:300])

for tag, sol in (("mech_thermal", "Thermal"), ("mech_struct", "Structural")):
    if tag not in which:
        continue
    from ansys.aedt.core import Mechanical
    try:
        t0 = time.time()
        me = Mechanical(project=str(work / f"probe_{tag}.aedt"), design=tag,
                        solution_type=sol, non_graphical=True, new_desktop=True,
                        version="2026.1", close_on_exit=True)
        me.modeler.model_units = "mm"
        me.modeler.create_box([0, 0, 0], [10, 10, 1], name="blk", material="copper")
        if sol == "Thermal":
            me.assign_uniform_temperature(
                me.modeler.get_faceid_from_position([5, 5, 0], assignment="blk"), 25)
            me.assign_heat_generation("blk", value="1W")
        else:
            me.assign_fixed_support(
                me.modeler.get_faceid_from_position([5, 5, 0], assignment="blk"))
        me.create_setup("S1")
        t1 = time.time(); ok = me.analyze_setup("S1"); t2 = time.time()
        done(tag, solved=bool(ok), licence_error=licence_failed(me),
             build_s=round(t1-t0, 1), solve_s=round(t2-t1, 2))
        me.release_desktop(True, True)
    except Exception as e:
        done(tag, solved=False, error=str(e)[:300])

(work / "probe.json").write_text(json.dumps(out, indent=2))
