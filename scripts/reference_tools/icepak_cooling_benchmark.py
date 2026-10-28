"""Matched Icepak conjugate benchmark of the production cold-plate correlation.

PRODUCTION MODEL. scripts/phase0mr/cooling_production.py CoolingDesign
"TOP_SI_MICROCHANNEL_27" -> scripts/phase0m/cooling.py Microchannel.solve(): silicon
(k = 130 W/mK) plate, channels 50 um wide x 300 um tall, fins 50 um, base 100 um,
22.36 x 22.36 mm footprint, n = floor(22360 / 100) = 223 channels, water at the constant
properties RHO_F, CP_F, K_F, MU_F of cooling.py, 27 g/s total, 25 C inlet. Laminar
fully-developed Nu (Shah & London, 3 heated walls), straight-fin efficiency,
R_total = R_conv + R_caloric (mean fluid, 1/(2 m cp)) + R_base, h_eff = 1/(R_total A_foot).

MATCHED CFD PROBLEM (Icepak, steady, laminar, gravity and radiation off):
  domain   one HALF channel pitch: half fin (25 um) + half channel (25 um), full 22.36 mm
           length, silicon base 100 um under fins 300 um tall; the fluid is the region
           (water with exactly cooling.py's constants) bounded by the silicon.
  sides    symmetry walls on y = 0 (fin mid-plane) and y = 50 um (channel mid-plane);
           together they make the domain one period of the 223-channel array.
  top      adiabatic no-slip wall over fin tip and channel (the lid; 3 heated walls).
  ends     inlet sheet over the channel cross-section only: mass flow
           27 g/s / 223 / 2 at 25 C; outlet sheet: static gauge pressure 0;
           silicon end faces adiabatic.
  bottom   uniform heat flux q'' = Q / A_foot on the base underside (stationary wall),
           Q = converged Z1 HV-S0 Q_ledger_W from etm_Z1_HV_S0_h1.1_r21.json.
Constant properties and no buoyancy make the energy equation linear in Q for the given
flow: the CFD temperature rise scales exactly with Q, and both the CFD h_eff and the
correlation's h_eff are independent of Q.

COMPARED: mean base-underside temperature rise above inlet (CFD, area mean from Icepak's
field summary) vs Q R_total (correlation) and the implied h_eff = q''/dT_mean.
The correlation is FULLY DEVELOPED; at Re ~ 1265, Pr ~ 3.6 the thermal entry length
0.05 Re Pr D_h is ~19 mm, comparable to the 22.36 mm channel, so the CFD includes a
developing-flow enhancement the correlation does not.

    python icepak_cooling_benchmark.py driver [levels...]   # solves + outputs
    python icepak_cooling_benchmark.py solve <level>        # one AEDT session (internal)
    python icepak_cooling_benchmark.py image <level>        # graphical, under xvfb-run
    python icepak_cooling_benchmark.py report               # rewrite outputs from results
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import math
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
sys.path.insert(0, str(HERE))
for _p in ("scripts/phase0mr", "scripts/phase0m"):
    sys.path.insert(0, str(R / _p))
WORK = Path(os.environ.get("AEDT_WORK", Path.home() / "claude_scratch" / "aedt_work"))
WD = WORK / "icepak"
OUT = R / "research" / "final_closure" / "reference_cooling_icepak.json"
EVID = R / "presentation" / "prelim_hvr" / "tool_evidence" / "cooling_icepak"
CORES = 4
DESIGN = "channel"

# mesh levels: max element sizes (um) along x (flow), y (span), z (height).
# baseline -> fine -> finer halve dy and dz each time (2x finer ACROSS the channel
# cross-section per step, ratio 2: a three-level sequence); baseline_x and fine_x halve
# dx at the baseline / fine cross-section (streamwise resolution of the entrance region).
LEVELS = {
    "smoke": {"dx": 400.0, "dy": 25.0 / 4, "dz": 20.0, "iters": 60},
    "baseline": {"dx": 200.0, "dy": 25.0 / 6, "dz": 10.0, "iters": 5000},
    "fine": {"dx": 200.0, "dy": 25.0 / 12, "dz": 5.0, "iters": 6000},
    "finer": {"dx": 200.0, "dy": 25.0 / 24, "dz": 2.5, "iters": 4000},
    "baseline_x": {"dx": 100.0, "dy": 25.0 / 6, "dz": 10.0, "iters": 5000},
    "fine_x": {"dx": 100.0, "dy": 25.0 / 12, "dz": 5.0, "iters": 4000},
}
CRIT_FLOW, CRIT_ENERGY = "1e-06", "1e-12"
MONITOR_X_MM = (0.5, 2.0, 6.0, 11.18, 21.5)


def inputs():
    from cooling_production import CANDIDATES
    import cooling as C
    et = json.loads((R / "research" / "final_closure" / "etm_Z1_HV_S0_h1.1_r21.json").read_text())
    Q = float(et["thermal"]["Q_ledger_W"])
    cd = CANDIDATES["TOP_SI_MICROCHANNEL_27"]
    mc = cd.channel()
    n = mc.n_channels
    L, Wd = mc.length_mm * 1e-3, mc.width_mm * 1e-3
    a_foot = L * Wd
    q_flux = Q / a_foot
    half_pitch = 0.5 * (mc.w_ch_um + mc.t_fin_um) * 1e-6
    return {"Q_W": Q, "Q_source": "research/final_closure/etm_Z1_HV_S0_h1.1_r21.json "
                                  "thermal.Q_ledger_W (Z1 HV-S0, converged)",
            "design": cd.name, "w_ch_um": mc.w_ch_um, "h_ch_um": mc.h_ch_um,
            "t_fin_um": mc.t_fin_um, "t_base_um": mc.t_base_um, "k_solid": mc.k_solid,
            "length_mm": mc.length_mm, "width_mm": mc.width_mm, "n_channels": n,
            "m_dot_total_g_s": mc.m_dot_g_s, "t_in_c": mc.t_in_c,
            "rho": C.RHO_F, "cp": C.CP_F, "k_f": C.K_F, "mu": C.MU_F,
            "A_foot_m2": a_foot, "q_flux_W_m2": q_flux,
            "m_dot_half_channel_kg_s": mc.m_dot_g_s * 1e-3 / n / 2.0,
            "P_half_pitch_W": q_flux * half_pitch * L,
            "u_mean_m_s": mc.m_dot_g_s * 1e-3 / n / (C.RHO_F * mc.w_ch_um * mc.h_ch_um * 1e-12),
            "Q_Z2_HV_S0_W": float(json.loads((R / "research" / "final_closure" /
                                              "etm_Z2_HV_S0_h1.1_r21.json").read_text())
                                  ["thermal"]["Q_ledger_W"])}


def correlation(inp):
    from cooling_production import CANDIDATES
    s = CANDIDATES["TOP_SI_MICROCHANNEL_27"].channel().solve(inp["Q_W"])
    return s


# ======================================================================== solve ====
def build(ip, inp, lev, graphical=False):
    um = inp
    L = um["length_mm"] * 1e3
    hp = 0.5 * (um["w_ch_um"] + um["t_fin_um"])          # 50 um half pitch
    hf = 0.5 * um["t_fin_um"]                            # 25 um half fin
    tb, hc = um["t_base_um"], um["h_ch_um"]
    ip.modeler.model_units = "um"
    si = ip.materials.add_material("si_k130")
    si.thermal_conductivity = um["k_solid"]
    si.mass_density = 2329.0
    si.specific_heat = 703.0
    w = ip.materials.duplicate_material("Water(@320K)", "water_corr")   # keeps 'Fluid'
    w.thermal_conductivity = um["k_f"]
    w.mass_density = um["rho"]
    w.specific_heat = um["cp"]
    w.viscosity = um["mu"]
    ip.edit_design_settings(ambient_temperature=um["t_in_c"], default_fluid="water_corr",
                            default_solid="si_k130", radiation_temperature=um["t_in_c"],
                            export_directory=str(WD))
    base = ip.modeler.create_box([0, 0, 0], [L, hp, tb], name="si_base", material="si_k130")
    fin = ip.modeler.create_box([0, 0, tb], [L, hf, hc], name="si_fin", material="si_k130")
    names = ip.modeler.object_names
    if "Region" in names:
        reg = ip.modeler["Region"]
        ip.modeler.edit_region_dimensions([0, 0, 0, 0, 0, 0])
    else:
        reg = ip.modeler.create_region(0, "Absolute Offset")
    reg.material_name = "water_corr"
    bb = [round(v, 6) for v in reg.bounding_box]
    if bb != [0, 0, 0, round(L, 6), hp, tb + hc]:
        raise RuntimeError(f"region not tight: {bb}")
    inlet = ip.modeler.create_rectangle("YZ", [0, hf, tb], [hp - hf, hc], name="inlet_sheet")
    outlet = ip.modeler.create_rectangle("YZ", [L, hf, tb], [hp - hf, hc], name="outlet_sheet")
    for o, x in ((inlet, 0.0), (outlet, L)):
        b = [round(v, 6) for v in o.bounding_box]
        if b != [x, hf, tb, x, hp, tb + hc]:
            raise RuntimeError(f"opening sheet misplaced: {b}")
    ip.assign_mass_flow_free_opening(inlet.name, boundary_name="inlet_mflow",
                                     temperature=f"{um['t_in_c']}cel",
                                     mass_flow_rate=f"{um['m_dot_half_channel_kg_s']:.9g}kg_per_s",
                                     inflow=True)
    ip.assign_pressure_free_opening(outlet.name, boundary_name="outlet_p",
                                    temperature=f"{um['t_in_c']}cel", pressure="0pascal")
    fy0 = ip.modeler.get_faceid_from_position([L / 2, 0, (tb + hc) / 2], assignment="Region")
    fy1 = ip.modeler.get_faceid_from_position([L / 2, hp, (tb + hc) / 2], assignment="Region")
    # the flux goes on the SILICON's own underside: a wall boundary on the coincident
    # region face is overridden by the solid face (zero area in the solved mesh; found
    # in the smoke run, where no heat entered and the energy residual stayed ~1e-16)
    fz0 = ip.modeler.get_faceid_from_position([L / 2, hp / 2, 0], assignment="si_base")
    if not all((fy0, fy1, fz0)):
        raise RuntimeError(f"faces not found {fy0} {fy1} {fz0}")
    ip.assign_symmetry_wall([fy0, fy1], boundary_name="sym_y")
    # 'Surface Heat' is silently stored as the default 'Total Power = 0W' by this
    # AEDT/PyAEDT pairing (second smoke run): give the face its total power instead; a
    # face source spreads it uniformly by area, i.e. exactly q'' = Q / A_foot here.
    a_face = L * hp * 1e-12                                   # m^2
    p_face = um["q_flux_W_m2"] * a_face
    ip.assign_source(fz0, "Total Power", f"{p_face:.9g}W", boundary_name="q_base")
    qb = next(b for b in ip.boundaries if b.name == "q_base")
    tc, tp = qb.props.get("Thermal Condition"), str(qb.props.get("Total Power"))
    if tc != "Total Power" or abs(float(tp.rstrip("W")) - p_face) > 1e-6 * p_face:
        raise RuntimeError(f"heat source not stored as intended: {tc} {tp}")
    # temperature monitors on the heated underside (1 um inside the base): their
    # iteration histories show whether the solution has stopped changing
    mon = {}
    for xm in MONITOR_X_MM:
        nm = f"T_x{xm:g}mm".replace(".", "p")
        try:
            mon[nm] = ip.monitor.assign_point_monitor([xm * 1e3, hp / 2, 1.0],
                                                      monitor_quantity="Temperature",
                                                      monitor_name=nm)
        except Exception as e:
            mon[nm] = f"failed: {type(e).__name__}"
    # mesh: manual global settings
    g = ip.mesh.global_mesh_region
    g.manual_settings = True
    g.settings["MaxElementSizeX"] = f"{lev['dx']}um"
    g.settings["MaxElementSizeY"] = f"{lev['dy']:.6g}um"
    g.settings["MaxElementSizeZ"] = f"{lev['dz']}um"
    g.settings["MinElementsInGap"] = "3"
    g.settings["MinElementsOnEdge"] = "2"
    g.settings["MaxSizeRatio"] = "2"
    g.settings["EnableMLM"] = False
    g.settings["MinGapX"] = "1um"
    g.settings["MinGapY"] = "1um"
    g.settings["MinGapZ"] = "1um"
    g.update()
    s = ip.create_setup("S1")
    s.props["Flow Regime"] = "Laminar"
    s.props["Include Flow"] = True
    s.props["Include Temperature"] = True
    s.props["Include Gravity"] = False
    s.props["Radiation Model"] = "Off"
    s.props["Solution Initialization - X Velocity"] = f"{um['u_mean_m_s']:.6g}m_per_sec"
    s.props["Solution Initialization - Temperature"] = f"{um['t_in_c']}cel"
    s.props["Convergence Criteria - Max Iterations"] = int(lev["iters"])
    s.props["Convergence Criteria - Flow"] = CRIT_FLOW
    s.props["Convergence Criteria - Energy"] = CRIT_ENERGY
    s.props["Discretization Scheme - Momentum"] = "Second"
    s.props["Discretization Scheme - Temperature"] = "Second"
    s.update()
    return {"faces": {"y0": fy0, "y1": fy1, "z0": fz0}, "region_bbox_um": bb,
            "objects": ip.modeler.object_names, "q_base_stored": [tc, tp],
            "q_base_face_area_m2": a_face, "q_base_total_power_W": p_face, "monitors": mon}


def parse_profile(results_dir):
    """Cell count and solver elapsed time from AEDT's own .profile (numbers only)."""
    out = {}
    for f in sorted(glob.glob(str(Path(results_dir) / "**" / "*.profile"), recursive=True)):
        txt = Path(f).read_text(errors="replace")
        for key in ("Total Cells", "Total Nodes", "Total Faces"):
            m = re.findall(rf"{key}\\?', (\d+)", txt)
            if m:
                out[key.lower().replace(" ", "_")] = int(m[-1])
        m = re.findall(r"'Elapsed Time', '(\d+):(\d+):(\d+)'", txt)
        if m:
            h, mi, se = map(int, m[0])
            out["profile_total_elapsed_s"] = 3600 * h + 60 * mi + se
        m = re.findall(r"'Iterations?', (\d+)", txt)
        if m:
            out["iterations"] = int(m[-1])
        out["profile_file"] = Path(f).name
    return out


SOLUTION = "S1 : SteadyState"


def field_summary(ip, path, row):
    """Native Icepak field summary (PyAEDT's FieldSummary.export_csv fails here: its
    nominal_sweep lookup returns None for this design). Returns the CSV rows as dicts."""
    import csv
    osol = ip.odesign.GetModule("Solutions")
    calc = list(row) + ["", "Default", "All", "AmbientTemp", False]
    osol.EditFieldsSummarySetting(["SolutionName:=", SOLUTION, "Variation:=", "",
                                   "Calculation:=", calc])
    osol.ExportFieldsSummary(["SolutionName:=", SOLUTION, "DesignVariationKey:=", "",
                              "ExportFileName:=", str(path), "IntrinsicValue:=", ""])
    lines = Path(path).read_text(errors="replace").splitlines()
    hdr_i = next(i for i, ln in enumerate(lines) if ln.lower().startswith("entity"))
    out = []
    for r in csv.DictReader(lines[hdr_i:]):
        r = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items() if k}
        q = r.get("Quantity", "")
        r["quantity_name"] = q.split("[")[0]
        r["unit"] = q[q.find("[") + 1:q.find("]")] if "[" in q else ""
        out.append(r)
    return out


def solve(level):
    from ansys.aedt.core import Icepak
    inp = inputs()
    lev = LEVELS[level]
    wd = WD / level
    wd.mkdir(parents=True, exist_ok=True)
    res = {"level": level, "mesh_settings_um": lev, "started": dt.datetime.now().isoformat()}
    t0 = time.perf_counter()
    ip = Icepak(project=str(wd / f"cooling_{level}.aedt"), design=DESIGN,
                non_graphical=True, new_desktop=True, version="2026.1", close_on_exit=True)
    try:
        res["build"] = build(ip, inp, lev)
        ip.save_project()
        res["build_s"] = time.perf_counter() - t0
        try:
            res["validate"] = bool(ip.odesign.ValidateDesign())
        except Exception as e:
            res["validate"] = f"failed: {type(e).__name__}"
        t1 = time.perf_counter()
        ok = ip.analyze_setup("S1", cores=CORES)
        res["solve_wall_s"] = time.perf_counter() - t1
        res["solved"] = bool(ok)
        res["load_average_after_solve"] = [round(x, 1) for x in os.getloadavg()]
        ip.save_project()
        if ok:
            rows = [("Boundary", "Surface", "q_base", "Temperature"),
                    ("Boundary", "Surface", "q_base", "HeatFlowRate"),
                    ("Boundary", "Surface", "outlet_p", "Temperature"),
                    ("Boundary", "Surface", "outlet_p", "MassFlowRate"),
                    ("Boundary", "Surface", "inlet_mflow", "MassFlowRate"),
                    ("Boundary", "Surface", "outlet_p", "HeatFlowRate"),
                    ("Boundary", "Surface", "inlet_mflow", "HeatFlowRate"),
                    ("Boundary", "Surface", "outlet_p", "Ux"),
                    ("Boundary", "Surface", "inlet_mflow", "Ux"),
                    ("Boundary", "Surface", "inlet_mflow", "Pressure"),
                    ("Boundary", "Surface", "outlet_p", "Pressure"),
                    ("Object", "Volume", "si_base", "Temperature"),
                    ("Object", "Volume", "si_fin", "Temperature"),
                    ("Object", "Volume", "Region", "Temperature"),
                    ("Object", "Volume", "Region", "Speed"),
                    ("Object", "Surface", "si_fin", "HeatFlowRate"),
                    ("Object", "Surface", "si_base", "HeatFlowRate"),
                    ("Object", "Surface", "si_fin", "ConvectiveHeatFlow"),
                    ("Object", "Surface", "si_base", "ConvectiveHeatFlow"),
                    ("Object", "Surface", "Region", "ConvectiveHeatFlow")]
            got = []
            for r in rows:                     # one at a time: a bad row must not hide others
                try:
                    got += field_summary(ip, wd / f"fs_{r[2]}_{r[3]}.csv", r)
                except Exception as e:
                    got.append({"request": list(r), "error": f"{type(e).__name__}: {str(e)[:120]}"})
            res["field_summary"] = got
            res["residual_history_file"] = None
            for f in glob.glob(str(wd / f"cooling_{level}.aedtresults" / "**" / "*_MON0_V0.sd"),
                               recursive=True):
                if Path(f).stat().st_size > 1000:
                    res["residual_history_file"] = f
                    hist = []
                    for ln in Path(f).read_text(errors="replace").splitlines():
                        m = re.match(r"\s*([0-9.eE+-]+)\s+(.*)", ln)
                        if not m or float(m.group(1)) < 0:
                            continue
                        vals = dict(re.findall(r"([A-Za-z]+)\(([0-9.eE+-]+)\)", m.group(2)))
                        hist.append([float(m.group(1))] + [float(vals.get(k, "nan")) for k in
                                    ("Continuity", "XVelocity", "YVelocity", "ZVelocity",
                                     "Energy")])
                    res["residuals_first_last"] = {"columns": ["iter", "continuity", "x_vel",
                                                               "y_vel", "z_vel", "energy"],
                                                   "first": hist[:3], "last": hist[-3:],
                                                   "n_iterations": len(hist)}
                    # point-monitor histories: MON1.. in creation order (MONITOR_X_MM)
                    mons = {}
                    for k_, xm in enumerate(MONITOR_X_MM, start=1):
                        fm = Path(f.replace("_MON0_", f"_MON{k_}_"))
                        if not fm.exists():
                            continue
                        tt = [float(v) for v in re.findall(r"Temperature\(([0-9.eE+-]+)\)",
                                                           fm.read_text(errors="replace"))]
                        if tt:
                            n_ = len(tt)
                            i90 = max(0, int(0.9 * n_) - 1)
                            mons[f"x={xm:g}mm"] = {"final_C": tt[-1], "n": n_,
                                                   "change_last_10pct_K": tt[-1] - tt[i90],
                                                   "change_last_100_K": tt[-1] - tt[max(0, n_ - 101)]}
                    res["monitors_underside"] = mons
        res["profile"] = parse_profile(wd / f"cooling_{level}.aedtresults")
        try:
            msf = wd / "mesh_stats.ms"
            ip.export_mesh_stats("S1", output_file=str(msf))
            if msf.exists():
                txt = msf.read_text(errors="replace")
                res["mesh_stats_excerpt"] = [ln.strip() for ln in txt.splitlines()
                                             if re.search(r"(?i)cells|elements|nodes|faces", ln)][:12]
        except Exception as e:
            res["mesh_stats_error"] = type(e).__name__
        try:
            msgs = ip.odesktop.GetMessages(ip.project_name, ip.design_name, 0)
            res["aedt_messages"] = {"errors": sum("[error]" in m.lower() for m in msgs),
                                    "warnings": sum("[warning]" in m.lower() for m in msgs)}
            (wd / "aedt_messages_scratch_only.txt").write_text("\n".join(msgs))
        except Exception:
            pass
    finally:
        res["session_s"] = time.perf_counter() - t0
        (wd / "result.json").write_text(json.dumps(res, indent=2, default=str))
        ip.release_desktop(close_projects=True, close_desktop=True)
    print(json.dumps({k: res.get(k) for k in ("level", "solved", "solve_wall_s")}, default=str))


# ======================================================================== image ====
def image(level):
    from ansys.aedt.core import Icepak, settings
    settings.desktop_launch_timeout = 400          # GUI start is slow on a loaded host
    wd = WD / level
    ip = Icepak(project=str(wd / f"cooling_{level}.aedt"), design=DESIGN,
                non_graphical=False, new_desktop=True, version="2026.1", close_on_exit=True)
    out = {}
    try:
        for tag, orient in (("01_geometry", ""), ("01_geometry_inlet_end", "right"),
                            ("01_geometry_inlet_end_b", "front")):
            p = WD / f"{tag}.png"
            if p.exists():
                p.unlink()
            try:
                ip.modeler.fit_all()
            except Exception:
                pass
            try:
                ip.modeler.oeditor.ExportModelImageToFile(
                    str(p), 1400, 900,
                    ["NAME:SaveImageParams", "ShowAxis:=", "True", "ShowGrid:=", "False",
                     "ShowRuler:=", "True", "ShowRegion:=", "Default", "Selections:=", "",
                     "FieldPlotSelections:=", "", "Orientation:=", orient])
                out[tag] = p.exists()
            except Exception as e:
                out[tag] = f"failed: {type(e).__name__}"
    finally:
        ip.release_desktop(close_projects=True, close_desktop=True)
    (WD / "image_result.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out))


# ======================================================================= driver ====
def driver(levels):
    from aedt_proc import run_tracked, scratch_env
    env = scratch_env(WORK)
    WD.mkdir(parents=True, exist_ok=True)
    runs = {}
    for lv in levels:
        runs[lv] = run_tracked(["/home/beams0/MGHARIB/envs/etm/bin/python", __file__,
                                "solve", lv], WD / f"solve_{lv}.log",
                               timeout_s=float(os.environ.get("ICEPAK_TIMEOUT_S", 3 * 3600)),
                               env=env, cwd=str(WD))
        (WD / f"run_{lv}.json").write_text(json.dumps(runs[lv], indent=2))
        print(lv, {k: runs[lv][k] for k in ("rc", "wall_s", "timed_out")}, flush=True)


def fs_get(res, entity, quantity):
    for r in res.get("field_summary", []):
        if r.get("error"):
            continue
        nm = r.get("Entity") or r.get("entity") or ""
        q = r.get("quantity_name") or (r.get("Quantity") or "").split("[")[0]
        if nm == entity and q.lower() == quantity.lower():
            return r
    return None


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def report():
    inp = inputs()
    cor = correlation(inp)
    levels = {}
    for lv in ("baseline", "fine", "finer", "baseline_x", "fine_x", "smoke"):
        f = WD / lv / "result.json"
        if f.exists():
            levels[lv] = json.loads(f.read_text())
            run = WD / f"run_{lv}.json"
            levels[lv]["tracked_run"] = json.loads(run.read_text()) if run.exists() else None
    dT_cor = inp["Q_W"] * cor["R_total_K_W"]
    # the correlation evaluated for EXACTLY the CFD per-pitch loading (q'' over pitch x L,
    # per-channel flow): differs from Q R_total only through n*pitch = 22.30 mm vs 22.36 mm
    q2 = inp["q_flux_W_m2"]
    pitch = (inp["w_ch_um"] + inp["t_fin_um"]) * 1e-6
    Lm = inp["length_mm"] * 1e-3
    Qp = q2 * pitch * Lm
    mch = inp["m_dot_total_g_s"] * 1e-3 / inp["n_channels"]
    hch, eta = cor["h_channel_W_m2K"], cor["fin_efficiency"]
    w, hh = inp["w_ch_um"] * 1e-6, inp["h_ch_um"] * 1e-6
    dT_cor_matched = (q2 * inp["t_base_um"] * 1e-6 / inp["k_solid"]
                      + Qp / (hch * Lm * (w + 2 * eta * hh)) + Qp / (2 * mch * inp["cp"]))
    rows = {}
    for lv, r in levels.items():
        if lv == "smoke":
            continue
        e = {"solved": r.get("solved"), "mesh_settings_um": r.get("mesh_settings_um"),
             "cells": (r.get("profile") or {}).get("total_cells"),
             "solve_wall_s": r.get("solve_wall_s"), "session_s": r.get("session_s"),
             "profile": r.get("profile"),
             "iterations": (r.get("residuals_first_last") or {}).get("n_iterations"),
             "iteration_cap": (r.get("mesh_settings_um") or {}).get("iters"),
             "final_scaled_residuals": dict(zip(
                 ["iter", "continuity", "x_vel", "y_vel", "z_vel", "energy"],
                 ((r.get("residuals_first_last") or {}).get("last") or [[None] * 6])[-1])),
             "underside_monitors": r.get("monitors_underside"),
             "load_average_after_solve": r.get("load_average_after_solve"),
             "heat_source_stored": (r.get("build") or {}).get("q_base_stored")}
        for key, ent, qty in (("Q_conv_fin_to_fluid_W", "si_fin", "ConvectiveHeatFlow"),
                              ("Q_conv_base_to_fluid_W", "si_base", "ConvectiveHeatFlow"),
                              ("Q_conv_region_W", "Region", "ConvectiveHeatFlow"),
                              ("Q_heatflow_fin_W", "si_fin", "HeatFlowRate"),
                              ("Q_heatflow_base_W", "si_base", "HeatFlowRate")):
            rr = fs_get(r, ent, qty)
            e[key] = num(rr.get("Total")) if rr else None
        tb = fs_get(r, "q_base", "Temperature")
        if r.get("solved") and tb:
            Tm, Tx = num(tb.get("Mean")), num(tb.get("Max"))
            dTm = Tm - inp["t_in_c"]
            e.update({"T_base_mean_C": Tm, "T_base_max_C": Tx, "dT_base_mean_K": dTm,
                      "h_eff_cfd_W_m2K": q2 / dTm,
                      "dT_rel_diff_cfd_vs_correlation": (dTm - dT_cor) / dT_cor,
                      "dT_rel_diff_cfd_vs_correlation_matched_loading":
                          (dTm - dT_cor_matched) / dT_cor_matched})
            for key, ent, qty in (("Q_into_base_W", "q_base", "HeatFlowRate"),
                                  ("T_outlet_area_mean_C", "outlet_p", "Temperature"),
                                  ("m_dot_outlet_kg_s", "outlet_p", "MassFlowRate"),
                                  ("m_dot_inlet_kg_s", "inlet_mflow", "MassFlowRate"),
                                  ("p_inlet_mean_Pa", "inlet_mflow", "Pressure"),
                                  ("p_outlet_mean_Pa", "outlet_p", "Pressure")):
                rr = fs_get(r, ent, qty)
                if rr:
                    e[key] = num(rr.get("Total")) if qty in ("HeatFlowRate", "MassFlowRate") \
                        and num(rr.get("Total")) is not None else num(rr.get("Mean"))
            if e.get("p_inlet_mean_Pa") is not None and e.get("p_outlet_mean_Pa") is not None:
                e["dp_kPa"] = (e["p_inlet_mean_Pa"] - e["p_outlet_mean_Pa"]) / 1e3
        rows[lv] = e
    status = ("EXECUTED" if rows and all(v.get("dT_base_mean_K") for v in rows.values())
              else "FAILED" if levels else "NOT_RUN")
    out = {"stage": "cooling_icepak", "status": status,
           "date": dt.date.today().isoformat(),
           "production_model": "scripts/phase0mr/cooling_production.py CoolingDesign "
                               "TOP_SI_MICROCHANNEL_27 -> scripts/phase0m/cooling.py "
                               "Microchannel.solve()",
           "reference_tool": "Ansys Electronics Desktop 2026 R1 Icepak (steady, laminar "
                             "conjugate CFD), PyAEDT 1.1",
           "inputs": inp, "correlation": cor,
           "correlation_dT_K": dT_cor,
           "correlation_dT_matched_loading_K": dT_cor_matched,
           "matched_loading_note": ("Q/A_foot over one pitch carries Q*pitch/width = "
                                    "Q/223.6 per channel whereas the correlation divides Q "
                                    "by n = 223 (n*pitch = 22.30 mm < 22.36 mm); the "
                                    "'matched loading' value evaluates the same correlation "
                                    "terms for exactly the CFD loading."),
           "levels": rows,
           "cfd_problem": {"domain": "half pitch (25 um half fin + 25 um half channel), "
                                     "symmetry walls on both sides, full 22.36 mm length",
                           "fluid": "water, constant rho, cp, k, mu = cooling.py values",
                           "solid": "silicon k = 130 W/mK (base 100 um + fin 300 um)",
                           "inlet": "mass flow per half channel, 25 C, normal to the sheet",
                           "outlet": "static gauge pressure 0",
                           "heat": "uniform flux q'' = Q/A_foot on the base underside",
                           "walls": "lid (top) adiabatic no-slip; silicon end faces "
                                    "adiabatic", "flow": "laminar, steady, no gravity, "
                                                         "no radiation",
                           "discretisation": "second-order momentum and energy",
                           "convergence_criteria": {"flow": float(CRIT_FLOW),
                                                    "energy": float(CRIT_ENERGY)}},
           "caveats": [
               "The correlation is fully developed (Shah & London Nu, constant along the "
               "channel). At Re ~ 1265 and Pr ~ 3.6 the hydrodynamic entry length "
               "0.05 Re D_h is ~5.4 mm and the thermal entry length 0.05 Re Pr D_h is "
               "~19 mm, i.e. most of the 22.36 mm channel is thermally developing; the "
               "CFD includes that entrance enhancement and the correlation does not.",
               "Fin efficiency in the correlation assumes a uniform h on the fin flanks; "
               "the CFD resolves the true conjugate distribution.",
               "Constant fluid properties at the correlation's values (no temperature "
               "dependence of viscosity), so the comparison isolates the heat-transfer "
               "model, not property variation.",
               "One periodic channel with uniform flux: manifold maldistribution, header "
               "losses and the non-uniform heat map of the package are outside this test."],
           "timing_method": ("wall clock (time.perf_counter) around PyAEDT analyze_setup "
                             "on 4 cores, including Icepak meshing and the solver; one solve "
                             "per mesh level (no repeats: each is a long CFD run); the "
                             "machine was shared with CalculiX jobs, load average recorded"),
           "hardware": None, "generator": "scripts/reference_tools/icepak_cooling_benchmark.py",
           "project_files": {lv: str(WD / lv / f"cooling_{lv}.aedt") for lv in levels}}
    try:
        import aedt_common as C
        out["hardware"] = C.hardware()
    except Exception:
        pass
    # convergence-criteria sensitivity: the same levels solved first with flow 1e-5 /
    # energy 1e-10 (archived in the scratch tree) and then with the final criteria
    r1 = WD / "round1_crit1e-5"
    crit = {}
    for k_, v_ in rows.items():
        f1 = r1 / k_ / "result.json"
        if f1.exists() and v_.get("dT_base_mean_K"):
            tb1 = fs_get(json.loads(f1.read_text()), "q_base", "Temperature")
            if tb1:
                d1 = num(tb1.get("Mean")) - inp["t_in_c"]
                crit[k_] = {"dT_K_crit_1e-5": d1, "dT_K_final": v_["dT_base_mean_K"],
                            "rel_change": (v_["dT_base_mean_K"] - d1) / v_["dT_base_mean_K"]}
    if crit:
        out["convergence_criteria_sensitivity"] = {
            "first_pass": {"flow": 1e-5, "energy": 1e-10},
            "final": {"flow": float(CRIT_FLOW), "energy": float(CRIT_ENERGY)},
            "per_level": crit}
    # local view along the channel from the underside point monitors (y = 25 um, 1 um
    # above the heated face) of the finest available level: wall-to-bulk difference vs
    # the correlation's fully developed value for the same loading
    best = next((k_ for k_ in ("fine_x", "fine", "baseline_x", "baseline")
                 if (rows.get(k_) or {}).get("underside_monitors")), None)
    if best:
        dtf = Qp / (mch * inp["cp"])                       # bulk rise per pitch
        fd = (q2 * inp["t_base_um"] * 1e-6 / inp["k_solid"]
              + Qp / (hch * Lm * (w + 2 * eta * hh)))     # conv + base, fully developed
        prof = []
        for key_, v_ in sorted(rows[best]["underside_monitors"].items(),
                               key=lambda kv: float(kv[0][2:-2])):
            xm = float(key_[2:-2])
            tb_ = inp["t_in_c"] + dtf * xm / inp["length_mm"]
            prof.append({"x_mm": xm, "T_underside_C": v_["final_C"],
                         "T_bulk_energy_balance_C": tb_,
                         "wall_minus_bulk_K": v_["final_C"] - tb_,
                         "vs_fully_developed_rel": (v_["final_C"] - tb_ - fd) / fd})
        out["along_channel_check"] = {
            "level": best, "correlation_fully_developed_wall_minus_bulk_K": fd,
            "bulk_rise_per_pitch_K": dtf, "stations": prof,
            "note": ("point monitors, not face means; T_bulk(x) from the energy balance with "
                     "uniform heating. The correlation's wall-to-bulk difference is constant "
                     "along the channel; the CFD value grows from the inlet and is still "
                     "below it at the outlet end, so the CFD-correlation gap is not only the "
                     "entrance effect; this points to the fully developed model itself (Nu "
                     "table and its wall boundary condition, uniform-h fin efficiency) for the "
                     "remainder. This benchmark does not separate those terms.")}
    nr = [k_ for k_ in ("finer",) if k_ not in rows]
    if nr:
        out["levels_defined_not_run"] = {
            "finer": {"mesh_settings_um": LEVELS["finer"],
                      "cells_expected": 112 * 48 * 160,
                      "reason": "stopped before launch to bound runtime: ~860k cells at the "
                                "measured ~2.4 us per cell-iteration (4 cores) and ~2x the "
                                "fine level's iterations is an estimated 80 min, for a "
                                "refinement of a baseline-to-fine change already below "
                                "0.4 %; the observed order of convergence is therefore "
                                "not estimated"}}
    seq = [rows.get(k, {}).get("dT_base_mean_K") for k in ("baseline", "fine", "finer")]
    if all(seq):
        f1, f2, f3 = seq
        rich = {"levels": ["baseline", "fine", "finer"], "refinement_ratio": 2.0,
                "dT_K": seq, "note": "cross-section refinement only (dx fixed at 200 um)"}
        if (f1 - f2) * (f2 - f3) > 0 and abs(f2 - f3) > 0:
            p_obs = math.log(abs(f1 - f2) / abs(f2 - f3)) / math.log(2.0)
            rich["observed_order"] = p_obs
            if p_obs > 0.5:
                fe = f3 + (f3 - f2) / (2.0 ** p_obs - 1.0)
                rich["extrapolated_dT_K"] = fe
                rich["finer_minus_extrapolated_rel"] = (f3 - fe) / fe
                rich["extrapolated_h_eff_W_m2K"] = inp["q_flux_W_m2"] / fe
                rich["extrapolated_rel_diff_vs_correlation"] = (fe - dT_cor) / dT_cor
        else:
            rich["observed_order"] = None
            rich["note"] += "; changes not monotonic, no extrapolation"
        out["richardson_cross_section"] = rich
    if len([v for v in rows.values() if v.get("dT_base_mean_K")]) >= 2:
        a, b = rows.get("baseline", {}), rows.get("fine", {})
        if a.get("dT_base_mean_K") and b.get("dT_base_mean_K"):
            out["mesh_change_baseline_to_fine_rel"] = (b["dT_base_mean_K"] - a["dT_base_mean_K"]) \
                / b["dT_base_mean_K"]
        f = rows.get("finer", {})
        if f.get("dT_base_mean_K") and b.get("dT_base_mean_K"):
            out["mesh_change_fine_to_finer_rel"] = (f["dT_base_mean_K"] - b["dT_base_mean_K"]) \
                / f["dT_base_mean_K"]
        fx = rows.get("fine_x", {})
        if fx.get("dT_base_mean_K") and b.get("dT_base_mean_K"):
            out["mesh_change_fine_to_fine_x_rel"] = (fx["dT_base_mean_K"] - b["dT_base_mean_K"]) \
                / fx["dT_base_mean_K"]
        c = rows.get("baseline_x", {})
        if c.get("dT_base_mean_K") and a.get("dT_base_mean_K"):
            out["mesh_change_baseline_to_baseline_x_rel"] = (c["dT_base_mean_K"]
                                                             - a["dT_base_mean_K"]) \
                / c["dT_base_mean_K"]
    OUT.write_text(json.dumps(out, indent=2, default=str) + "\n")
    return out


def evidence():
    """tool_evidence/cooling_icepak/: setup, result, runtime, README and the native AEDT
    image if the graphical export produced one (nothing is substituted if it did not)."""
    import shutil
    out = json.loads(OUT.read_text())
    EVID.mkdir(parents=True, exist_ok=True)
    inp, cor, lv = out["inputs"], out["correlation"], out["levels"]

    def dump(name, obj):
        (EVID / name).write_text(json.dumps(obj, indent=2, default=str) + "\n")

    dump("setup.json", {"production_model": out["production_model"],
                        "reference_tool": out["reference_tool"],
                        "cfd_problem": out["cfd_problem"], "inputs": inp,
                        "mesh_levels_um": {k: v.get("mesh_settings_um") for k, v in lv.items()},
                        "cells": {k: v.get("cells") for k, v in lv.items()},
                        "project_files_scratch": out.get("project_files")})
    res = {"status": out["status"],
           "correlation": {k: cor[k] for k in ("Re", "Nu", "h_channel_W_m2K", "fin_efficiency",
                                               "R_conv_K_W", "R_caloric_K_W", "R_base_K_W",
                                               "R_total_K_W", "h_effective_W_m2K", "dp_kPa")},
           "correlation_dT_K": out["correlation_dT_K"],
           "correlation_dT_matched_loading_K": out["correlation_dT_matched_loading_K"],
           "cfd": {k: {kk: v.get(kk) for kk in (
               "dT_base_mean_K", "T_base_mean_C", "T_base_max_C", "h_eff_cfd_W_m2K",
               "dT_rel_diff_cfd_vs_correlation",
               "dT_rel_diff_cfd_vs_correlation_matched_loading", "dp_kPa",
               "Q_conv_fin_to_fluid_W", "Q_conv_base_to_fluid_W", "iterations",
               "final_scaled_residuals", "underside_monitors")} for k, v in lv.items()},
           "mesh_change": {k: out[k] for k in out if k.startswith("mesh_change")},
           "richardson_cross_section": out.get("richardson_cross_section"),
           "convergence_criteria_sensitivity": out.get("convergence_criteria_sensitivity"),
           "levels_defined_not_run": out.get("levels_defined_not_run")}
    dump("result.json", res)
    dump("runtime.json", {"timing_method": out["timing_method"], "cores": CORES,
                          "per_level": {k: {"solve_wall_s": v.get("solve_wall_s"),
                                            "session_s": v.get("session_s"),
                                            "cells": v.get("cells"),
                                            "iterations": v.get("iterations"),
                                            "load_average_after_solve":
                                                v.get("load_average_after_solve")}
                                        for k, v in lv.items()},
                          "hardware": out.get("hardware")})
    imgs = []
    ir = WD / "image_result.json"
    img_status = json.loads(ir.read_text()) if ir.exists() else None
    # 'right' (end-on) is not shipped: AEDT's fit-all zoom is set by the 22.36 mm length,
    # so the 50 x 400 um cross-section is a few pixels and the image shows only the axes
    for tag, name in (("01_geometry", "01_geometry.png"),
                      ("01_geometry_inlet_end_b", "01_geometry_side.png")):
        src = WD / f"{tag}.png"
        if src.exists() and src.stat().st_size > 0:
            shutil.copy(src, EVID / name)
            imgs.append(name)
    rows = []
    for k in ("baseline", "fine", "finer", "baseline_x", "fine_x"):
        v = lv.get(k)
        if not v:
            continue
        ms = v.get("mesh_settings_um") or {}
        rows.append(f"| {k} | {ms.get('dx'):g} / {ms.get('dy'):.3g} / {ms.get('dz'):g} | "
                    f"{v.get('cells')} | {v.get('iterations')} | "
                    + (f"{v['dT_base_mean_K']:.3f} | {v['h_eff_cfd_W_m2K']:,.0f} | "
                       f"{100 * v['dT_rel_diff_cfd_vs_correlation']:+.2f} % | "
                       if v.get("dT_base_mean_K") else "not solved | - | - | ")
                    + f"{(v.get('solve_wall_s') or 0) / 60:.1f} |")
    mesh_lines = []
    for k_, txt in (("mesh_change_baseline_to_fine_rel", "baseline -> fine (dy, dz halved)"),
                    ("mesh_change_baseline_to_baseline_x_rel", "baseline -> baseline_x (dx halved)"),
                    ("mesh_change_fine_to_fine_x_rel", "fine -> fine_x (dx halved)"),
                    ("mesh_change_fine_to_finer_rel", "fine -> finer (dy, dz halved)")):
        if out.get(k_) is not None:
            mesh_lines.append(f"- Mesh change of the mean underside dT, {txt}: "
                              f"{100 * out[k_]:+.3f} %.")
    cs = out.get("convergence_criteria_sensitivity")
    if cs:
        worst = max(abs(v["rel_change"]) for v in cs["per_level"].values())
        mesh_lines.append(f"- Tightening the convergence criteria from flow 1e-5 / energy "
                          f"1e-10 to {CRIT_FLOW} / {CRIT_ENERGY} changed dT by at most "
                          f"{100 * worst:.3f} % (per level in result.json).")
    fin_lv = next((k_ for k_ in ("fine_x", "fine") if lv.get(k_, {}).get("dT_base_mean_K")), None)
    if fin_lv:
        v_ = lv[fin_lv]
        qsum = (v_.get("Q_conv_fin_to_fluid_W") or 0) + (v_.get("Q_conv_base_to_fluid_W") or 0)
        mesh_lines.append(f"- Energy check ({fin_lv}): convective heat from the silicon into "
                          f"the water {qsum:.6f} W (fin flanks {v_.get('Q_conv_fin_to_fluid_W'):.5f}"
                          f" W, channel floor {v_.get('Q_conv_base_to_fluid_W'):.5f} W) against "
                          f"{inp['P_half_pitch_W']:.6f} W applied.")
        if v_.get("dp_kPa"):
            mesh_lines.append(f"- Pressure drop ({fin_lv}): CFD {v_['dp_kPa']:.1f} kPa vs the "
                              f"correlation's fully developed {cor['dp_kPa']:.1f} kPa "
                              f"({100 * (v_['dp_kPa'] - cor['dp_kPa']) / cor['dp_kPa']:+.1f} %; "
                              "developing-flow pressure loss is included in the CFD).")
    ac = out.get("along_channel_check")
    if ac:
        st = ac["stations"]
        mesh_lines.append(f"- Along the channel ({ac['level']}, underside point monitors): "
                          "wall-to-bulk difference "
                          + ", ".join(f"{s_['wall_minus_bulk_K']:.2f} K at {s_['x_mm']:g} mm"
                                      for s_ in st)
                          + f", against the correlation's constant fully developed "
                            f"{ac['correlation_fully_developed_wall_minus_bulk_K']:.2f} K. The "
                            "CFD value levels off over the second half of the channel yet stays "
                            "below it at the outlet end, so the gap is not only the entrance "
                            "effect; this points to the fully developed model itself (Nu table "
                            "and its wall boundary condition, uniform-h fin efficiency) for the "
                            "rest. This test does not separate those terms.")
    if out.get("levels_defined_not_run"):
        mesh_lines.append("- A third cross-section level ('finer', ~860k cells) was defined "
                          "but not run, to bound runtime; no order of convergence is claimed.")
    md = [f"# cooling_icepak: matched conjugate CFD of the cold-plate correlation", "",
          f"Status: **{out['status']}**. Reference: {out['reference_tool']}.", "",
          "Production model: the compact laminar microchannel correlation "
          "(`cooling_production.py` TOP_SI_MICROCHANNEL_27 -> `cooling.py` "
          "`Microchannel.solve()`): Shah & London fully developed Nu with three heated "
          "walls, straight-fin efficiency, R_total = R_conv + R_caloric + R_base.", "",
          "Matched Icepak problem: one half pitch (25 um half fin + 25 um half channel) with "
          "symmetry walls on both sides, the full 22.36 mm length, silicon base 100 um under "
          "300 um fins (k = 130 W/mK), water with exactly the correlation's constant "
          "properties, laminar steady flow, inlet mass flow 27 g/s / 223 / 2 at 25 C, outlet "
          f"at gauge pressure 0, uniform heat flux Q/A_foot = {inp['q_flux_W_m2'] / 1e6:.4f} "
          f"MW/m2 on the base underside (Q = {inp['Q_W']:.2f} W, Z1 HV-S0 converged ledger), "
          "adiabatic lid and end faces.", "",
          f"Correlation: dT = Q R_total = {out['correlation_dT_K']:.3f} K, h_eff = "
          f"{cor['h_effective_W_m2K']:,.0f} W/m2K (R_conv {cor['R_conv_K_W']:.5f}, R_caloric "
          f"{cor['R_caloric_K_W']:.5f}, R_base {cor['R_base_K_W']:.5f} K/W; Re "
          f"{cor['Re']:.0f}, Nu {cor['Nu']:.3f}). For exactly the CFD loading (Q/A_foot over "
          f"one 100 um pitch) the same terms give {out['correlation_dT_matched_loading_K']:.3f} K.",
          "", "| level | dx / dy / dz (um) | cells | iterations | CFD mean underside dT (K) "
              "| CFD h_eff (W/m2K) | CFD vs Q R_total | solve wall (min) |",
          "|---|---|---|---|---|---|---|---|"] + rows + [
          "", "dT is the area-mean temperature of the heated underside minus the 25 C inlet "
              "(Icepak field summary). Mesh change and convergence details are in "
              "result.json; timings (wall clock around analyze_setup, 4 cores, one solve per "
              "level, shared machine) in runtime.json.", ""] + mesh_lines + [
          "",
          "## Caveats", ""] + [f"- {c}" for c in out["caveats"]] + [
          "", "## Images", "",
          (f"{', '.join(imgs)}: exported from an AEDT Icepak session that opened the solved "
           "baseline project (native ExportModelImageToFile under a virtual display): "
           "01_geometry.png is the default isometric view of the whole half-pitch domain, "
           "01_geometry_side.png the side elevation (x-z). At AEDT's fit-all zoom the "
           "22.36 mm length dominates, so the 50 um x 400 um cross-section is only a few "
           "pixels; an end-on export showed nothing but the axes and is not included."
           if imgs else
           "No geometry image: the native export under a virtual display did not produce a "
           f"file ({img_status if img_status else 'export not run'}). Nothing is substituted."),
          "Field plots are not exported (field-plot creation fails over this PyAEDT/gRPC "
          "pairing); none is synthesised.", ""]
    (EVID / "README.md").write_text("\n".join(md) + "\n")
    return imgs


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "driver"
    if cmd == "solve":
        solve(sys.argv[2])
    elif cmd == "image":
        image(sys.argv[2])
    elif cmd == "driver":
        driver(sys.argv[2:] or ["baseline", "fine"])
        report()
    elif cmd == "report":
        print(json.dumps(report().get("levels"), indent=1, default=str))
    elif cmd == "evidence":
        print(evidence())
    elif cmd == "images":
        from aedt_proc import run_tracked, scratch_env
        env = scratch_env(WORK)
        env["AEDT_GRAPHICAL"] = "1"
        # the first Xvfb on this host's PATH is a vendor build that exits at once
        # (display never opens); the system Xvfb works
        env["PATH"] = "/usr/bin:/bin:" + env["PATH"]
        r = run_tracked(["xvfb-run", "-a", "-s", "-screen 0 1600x1200x24",
                         "/home/beams0/MGHARIB/envs/etm/bin/python", __file__,
                         "image", sys.argv[2] if len(sys.argv) > 2 else "baseline"],
                        WD / "image.log", timeout_s=1500, env=env, cwd=str(WD))
        print({k: r[k] for k in ("rc", "wall_s", "timed_out", "leftovers_terminated")})
    elif cmd == "inputs":
        print(json.dumps(inputs(), indent=1))
