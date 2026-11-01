"""Build accuracy_speed_matrix.{csv,json} from the reference-run artifacts.

One row per (stage, observable). A speedup is computed ONLY where the production
model and the reference solved the same problem on the same machine; elsewhere the
column is empty and the absolute runtimes stand alone. There is deliberately no
"overall framework accuracy" row: the stages have different observables, references
and error definitions, so a single number would average incommensurable things.
"""
from __future__ import annotations

import csv
import json
import platform
from pathlib import Path

R = Path(__file__).resolve().parents[1]
D = R / "research" / "final_closure"
import sys as _sys                                                    # noqa: E402
_sys.path.insert(0, str(R / "scripts"))
FIELDS = ["stage", "production_model", "model_type", "reference_tool", "reference_type",
          "observable", "production_value", "reference_value", "error_metric", "error",
          "production_runtime_s", "production_runtime_range_s", "reference_runtime_s",
          "reference_runtime_range_s", "speedup", "timing_method", "machine", "cores",
          "solver_version", "mesh_or_dof", "evidence_class", "status", "limitations",
          "runtime_ratio_kind"]
TIMING = "warm-up + 3 timed repeats, median (range); same machine, shared host"
CCX = "CalculiX 2.23"


def J(name):
    f = D / name
    return json.loads(f.read_text()) if f.exists() else None


def machine():
    cpu = "unknown"
    for line in open("/proc/cpuinfo"):
        if line.startswith("model name"):
            cpu = line.split(":", 1)[1].strip()
            break
    return cpu


def _tm(d):
    t = (d or {}).get("timing") or {}
    return t.get("median_s"), ([t["min_s"], t["max_s"]] if "min_s" in t else None)


def icepak_row():
    """The cold-plate correlation against the matched Icepak conjugate CFD of one channel
    half-pitch (research/final_closure/reference_cooling_icepak.json). Error convention as
    every other row: (production - reference) / reference, here on the mean base temperature
    rise above the inlet at the CFD's exact per-pitch loading; the reference is the finest
    CFD level. The correlation's runtime is measured here (warm-up + repeats)."""
    j = J("reference_cooling_icepak.json")
    if not j or not str(j.get("status", "")).upper().startswith("EXECUTED"):
        return {"stage": "cooling_icepak", "production_model": "microchannel h correlation",
                "reference_tool": "Ansys Icepak (licensed)", "status": "NOT_EXECUTED",
                "evidence_class": "UNVALIDATED",
                "limitations": "the matched conjugate-CFD benchmark of the cold plate was not "
                               "run; only the historical explicit-fin MOOSE check exists"}
    import statistics
    import time as _t
    _sys.path.insert(0, str(R / "scripts" / "phase0mr"))
    _sys.path.insert(0, str(R / "scripts" / "phase0m"))
    from cooling_production import CANDIDATES
    des = CANDIDATES["TOP_SI_MICROCHANNEL_27"]
    q = j["inputs"]["Q_W"]
    des.compact(q)                                         # warm-up
    walls = []
    for _ in range(3):
        t0 = _t.perf_counter()
        for _k in range(1000):
            des.compact(q)
        walls.append((_t.perf_counter() - t0) / 1000)
    lv = j["levels"]
    finest = max((k for k in lv if lv[k].get("solved")), key=lambda k: lv[k]["cells"])
    ref, prod = lv[finest]["dT_base_mean_K"], j["correlation_dT_matched_loading_K"]
    rt = lv[finest]["solve_wall_s"]
    return {"stage": "cooling_icepak",
            "production_model": "laminar microchannel correlation (Shah & London Nu, fin "
                                "efficiency, caloric + base resistance)",
            "reference_tool": "Ansys Icepak 2026 R1 conjugate CFD, one channel half-pitch "
                              f"({lv[finest]['cells']} cells, finest of {len(lv)} levels)",
            "status": "EXECUTED", "evidence_class": "INDEPENDENT_NUMERICAL_VALIDATION",
            "observable": "mean base temperature rise above the inlet",
            "production_value": prod, "reference_value": ref,
            "error": (prod - ref) / ref, "error_metric": "relative difference",
            "production_runtime_s": statistics.median(walls),
            "production_runtime_range_s": [min(walls), max(walls)],
            "reference_runtime_s": rt, "speedup": rt / statistics.median(walls),
            "timing_method": "correlation: warm-up + 3 timed repeats of 1000 evaluations, "
                             "median per call; CFD: n = 1 solve per mesh level (a long CFD "
                             "run), wall clock incl. meshing, 4 cores; shared host",
            # the CPU the Icepak run recorded, not assumed equal to this one
            "machine": (j.get("hardware") or {}).get("cpu"),
            "cores": "correlation 1 / Icepak 4",
            "mesh_sensitivity": {k: j.get(k) for k in j if k.startswith("mesh_change")},
            "limitations": "one channel half-pitch with symmetry walls; the correlation is "
                           "conservative (higher temperature rise) and part of the gap is the "
                           "developing-flow entrance region the fully developed Nu ignores; "
                           "constant water properties; no convergence order is claimed (two "
                           "cross-section levels)"}


def attach_rows(mach, aedt):
    """geom.vr_attach_density: the homogenised attach card against explicit AEDT unit cells
    (dense and sparse, k_z and k_xy), the electrical column model against its closed forms,
    and the mechanical card, which has no reference and is carried as two bounds."""
    out = []
    rve = J("reference_attach_rve.json") or {}
    for case in ("dense", "sparse"):
        for k in ("kz", "kxy"):
            st = f"vr_attach_{case}_{k}"
            r = rve.get(st) or {}
            pm = ("columns (Cu + solder in series) in parallel with underfill" if k == "kz"
                  else "Maxwell-Garnett per z-slice, slices in parallel")
            if not r.get("reference_value"):
                out.append({"stage": st, "production_model": pm,
                            "model_type": "REDUCED MATERIAL MODEL",
                            "reference_tool": aedt, "status": "NOT_EXECUTED",
                            "evidence_class": "UNVALIDATED",
                            "limitations": "no explicit attach unit cell solved"})
                continue
            g = r["geometry"]
            out.append({"stage": st, "production_model": pm,
                        "model_type": "REDUCED MATERIAL MODEL",
                        "reference_tool": aedt + " (thermal FEM, explicit unit cell)",
                        "reference_type": "INDEPENDENT COMMERCIAL FEM",
                        "observable": (f"attach {'k_z' if k == 'kz' else 'k_xy'} (W/mK); "
                                       f"{g['d_um']:g} um at {g['pitch_um']:g} um pitch, "
                                       f"{g['h_cu_um']:g} Cu + {g['h_cap_um']:g} cap"),
                        "production_value": r["production_value"],
                        "reference_value": r["reference_value"],
                        "error_metric": "(prod - ref) / ref", "error": r["rel_error"],
                        "production_runtime_s": r["production_timing_s"],
                        "reference_runtime_s": r["reference_wall_s"],
                        "speedup": r["reference_wall_s"] / r["production_timing_s"],
                        "timing_method": "production: median of repeated calls; AEDT: single "
                                         "solve (n = 1), 4 cores, shared host",
                        "machine": (r.get("hardware") or {}).get("cpu") or mach,
                        "cores": "prod 1 / AEDT 4", "solver_version": "AEDT 2026.1",
                        "mesh_or_dof": r.get("mesh"),
                        "mesh_sensitivity": {"auto_to_refined": r.get("mesh_change_rel")},
                        "evidence_class": "INDEPENDENT_NUMERICAL_VALIDATION",
                        "status": "EXECUTED",
                        "limitations": "infinite periodic lattice (the card is compared at the "
                                       "same f); contact and IMC layers not resolved"})
    st = J("vr_attach_density_study.json") or {}
    for case in ("dense", "sparse"):
        e = ((st.get("cases") or {}).get(case) or {}).get("electrical")
        if not e:
            continue
        # closed forms: the column is exactly 1-D (insulating underfill, prismatic); the
        # constriction's closed form is the equal-area annulus
        rs = e["R_bump_ohm"] - e["R_constriction_two_sides_ohm"]
        r_ann = rs + e["R_constriction_two_sides_ohm"] * (e["constriction_dimensionless_annulus"]
                                                          / e["constriction_dimensionless_fv"])
        out.append({"stage": f"vr_attach_{case}_electrical",
                    "production_model": "Cu + solder column in series + two-sided constriction "
                                        "(2-D finite-volume unit cell)",
                    "model_type": "ANALYTICAL",
                    "reference_tool": "closed forms (exact 1-D column; annulus constriction "
                                      "of the equal-area circular cell)",
                    "reference_type": "CLOSED FORM (model-form check)",
                    "observable": f"single-bump resistance at {e['T_attach_C']:.1f} C (Ohm)",
                    "production_value": e["R_bump_ohm"], "reference_value": r_ann,
                    "error_metric": "(prod - ref) / ref",
                    "error": (e["R_bump_ohm"] - r_ann) / r_ann,
                    "evidence_class": "CLOSED_FORM_VERIFICATION", "status": "EXECUTED",
                    "limitations": "no 3-D electrical field-solver reference (Q3D and Maxwell "
                                   "are not licensed); "
                                   "the constriction is "
                                   f"{100 * e['constriction_fraction']:.1f} % of the bump; "
                                   "contact/IMC resistance not resolved (all-solder bound); "
                                   "equal sharing is an upper bound "
                                   "(equal_sharing_assessment)"})
    if st:
        out.append({"stage": "vr_attach_mechanical", "production_model":
                    "underfill-dominated card (A) and column-stiffened Voigt card (B)",
                    "model_type": "REDUCED MATERIAL MODEL", "reference_tool": "none",
                    "status": "BOUNDED", "evidence_class": "UNVALIDATED",
                    "limitations": "no structural homogenisation reference; the attach "
                                   "mechanics are carried as two bounds, never as one card"})
    return out


def rows():
    out, mach = [], machine()
    AEDT = "Ansys Electronics Desktop 2026 R1, Mechanical"
    rve = J("reference_rve.json") or {}
    retime = J("reference_rve_timing.json") or {}
    meta = {
        "tsv_bulk": ("rho L / A", "ANALYTICAL", "single 30 um x 300 um TSV",
                     "DC resistance (Ohm), conduction analogy",
                     "AEDT meshes the circular section as facets; the square-bar probe "
                     "agreed to ~1e-9, so the residual is geometric discretisation"),
        "tsv_tile_kz": ("Voigt", "REDUCED MATERIAL MODEL", "Cu-via unit cell, 1444/tile",
                        "k_z (W/mK)", "unit cell with adiabatic sides = square-lattice symmetry"),
        "tsv_tile_kx": ("Maxwell-Garnett", "REDUCED MATERIAL MODEL", "Cu-via unit cell",
                        "k_xy (W/mK)", "MG is a dilute-limit form; error grows with Cu fraction"),
        "rdl_tier_kx": ("laminate, grid in-plane", "REDUCED MATERIAL MODEL",
                        "one 10 um tier, square Cu grid", "k_x (W/mK)",
                        "for the DECLARED grid pattern and occupancy; the production tensor "
                        "ADOPTS the RVE value"),
        "rdl_tier_kz": ("laminate, series", "REDUCED MATERIAL MODEL", "one 10 um tier",
                        "k_z (W/mK)", "for the DECLARED grid pattern and occupancy; the "
                        "production tensor ADOPTS the RVE value"),
    }
    for k, (pm, mt, geo, obs, lim) in meta.items():
        r = rve.get(k)
        if not r or r.get("error"):
            out.append({"stage": k, "production_model": pm, "model_type": mt,
                        "reference_tool": AEDT, "status": "NOT_EXECUTED",
                        "limitations": (r or {}).get("error", "no artifact")})
            continue
        pt = r["production_timing"]
        rt = retime.get(k) or {}
        if rt.get("median_s"):
            ref_s, ref_rng, how = rt["median_s"], [rt["min_s"], rt["max_s"]], TIMING
        else:
            ref_s, ref_rng = r["reference_wall_s"], None
            how = "production: median of repeated calls; AEDT: single solve (n = 1)"
        out.append({"stage": k, "production_model": pm, "model_type": mt,
                    "reference_tool": AEDT + " (thermal FEM)",
                    "reference_type": "INDEPENDENT COMMERCIAL FEM",
                    "observable": f"{obs}; {geo}",
                    "production_value": r["production_value"],
                    "reference_value": r["reference_value"],
                    "error_metric": "(prod - ref) / ref", "error": r["rel_error"],
                    "production_runtime_s": pt["median_s"],
                    "production_runtime_range_s": [pt["min_s"], pt["max_s"]],
                    "reference_runtime_s": ref_s, "reference_runtime_range_s": ref_rng,
                    "speedup": ref_s / pt["median_s"], "timing_method": how,
                    "machine": mach, "cores": "prod 1 / AEDT 4",
                    "solver_version": "AEDT 2026.1",
                    "evidence_class": "INDEPENDENT_NUMERICAL_VALIDATION",
                    "status": "EXECUTED", "limitations": lim})
    out += attach_rows(mach, AEDT)
    for arch in ("Z1", "Z2"):
        m = J(f"reference_pkg_rdl_moose_{arch}.json")
        if not m:
            continue
        ref = m["moose"]["m3"]
        ps, pr = _tm(m["production_L3"])
        rs, rr = _tm(ref)
        out.append({"stage": f"pkg_rdl_{arch}", "production_model":
                    "voltage-fed aligned graded FV sheet (L3)",
                    "model_type": "REDUCED PDE / RESISTOR NETWORK",
                    "reference_tool": "MOOSE heat_transfer-opt (2-D FEM, gmsh mesh)",
                    "reference_type": "INDEPENDENT OPEN-SOURCE FEM",
                    "observable": "R_eff and max pad drop at the matched count, "
                                  "distributed-ball formulation",
                    "production_value": m["production_L3"]["R_eff_ohm"],
                    "reference_value": ref["R_eff_ohm"],
                    "error_metric": "(prod - ref) / ref on R_eff",
                    "error": m["rel_err_R_eff"],
                    "production_runtime_s": ps, "production_runtime_range_s": pr,
                    "reference_runtime_s": rs, "reference_runtime_range_s": rr,
                    "speedup": m["speedup_L3_vs_moose_m3"], "timing_method": TIMING,
                    "machine": mach, "cores": "1 / 1 MPI rank",
                    "solver_version": "MOOSE heat_transfer (local build)",
                    "mesh_or_dof": f"FV {m['production_L3']['n_cv']} cells; "
                                   f"FE {ref['n_elements']} triangles",
                    "evidence_class": "INDEPENDENT_NUMERICAL_VALIDATION",
                    "status": "EXECUTED",
                    "limitations": f"max pad drop error {m['rel_err_max_drop']:+.3%}; "
                                   f"vs the extrapolated MOOSE value "
                                   f"{m.get('rel_err_R_eff_vs_extrapolated', float('nan')):+.3%}; "
                                   "both 2-D, so the runtime ratio is not a model-reduction "
                                   "speedup"})
    for arch in ("Z1", "Z2"):
        t = J(f"reference_thermal_column_{arch}.json")
        if t and t.get("aedt", {}).get("solved"):
            ps, pr = _tm(t["ccx_fine"])
            rs, rr = _tm(t["aedt"])
            out.append({"stage": f"thermal_column_aedt_{arch}", "production_model":
                        "CalculiX C3D8 structured hex", "model_type": "FEM",
                        "reference_tool": AEDT + " thermal", "reference_type":
                        "INDEPENDENT COMMERCIAL FEM",
                        "observable": "T_max and layer-mean temperatures, interior unit cell "
                                      "of the physical package, converged HV-S0 heat map",
                        "production_value": t["ccx_fine"]["T_max_C"],
                        "reference_value": t["aedt"]["T_max_C"],
                        "error_metric": "T_max difference / reference temperature rise",
                        "error": t["T_rise_rel_err"],
                        "production_runtime_s": ps, "production_runtime_range_s": pr,
                        "reference_runtime_s": rs, "reference_runtime_range_s": rr,
                        "speedup": t["speedup_ccx_fine_vs_aedt"], "timing_method": TIMING,
                        "machine": mach,
                        "cores": f"ccx {t['threads']['ccx']} / AEDT {t['threads']['aedt_cores']}",
                        "solver_version": f"{CCX} / AEDT 2026.1",
                        "mesh_or_dof": f"{t['ccx_fine']['n_elems']} hex",
                        "evidence_class": "INDEPENDENT_NUMERICAL_VALIDATION",
                        "status": "EXECUTED",
                        "limitations": f"max layer-mean difference {t['max_abs_layer_err_K']:.3f} K; "
                                       "unit cell with symmetry sides, not the full package; "
                                       "both are FE codes, so the runtime ratio is "
                                       "solver-to-solver, not model reduction"})
        elif t is not None:
            out.append({"stage": f"thermal_column_aedt_{arch}", "production_model":
                        "CalculiX C3D8 structured hex", "reference_tool": AEDT + " thermal",
                        "status": "REFERENCE_NOT_SOLVED", "evidence_class": "UNVALIDATED",
                        "limitations": "the AEDT unit-cell solve did not complete"})
        mo = J(f"reference_thermal_column_moose_{arch}.json")
        if mo:
            ps, pr = _tm(mo["ccx"])
            rs, rr = _tm(mo["moose"]["m2"])
            out.append({"stage": f"thermal_column_moose_{arch}", "production_model":
                        "CalculiX C3D8 structured hex", "model_type": "FEM",
                        "reference_tool": "MOOSE heat_transfer-opt (3-D FEM, own hex mesh)",
                        "reference_type": "INDEPENDENT OPEN-SOURCE FEM",
                        "observable": "T_max of the same interior unit cell, HV-S0 heat map",
                        "production_value": mo["ccx"]["T_max_C"],
                        "reference_value": mo["moose"]["m2"]["T_max_C"],
                        "error_metric": "T_max difference / reference temperature rise",
                        "error": mo["T_rise_rel_err"],
                        "production_runtime_s": ps, "production_runtime_range_s": pr,
                        "reference_runtime_s": rs, "reference_runtime_range_s": rr,
                        "speedup": mo["speedup_ccx_vs_moose_median"], "timing_method": TIMING,
                        "machine": mach, "cores": "ccx 8 threads / MOOSE 1 MPI rank",
                        "solver_version": f"{CCX} / MOOSE heat_transfer (local build)",
                        "mesh_or_dof": f"ccx {mo['ccx']['n_elems']} hex; MOOSE "
                                       f"{mo['moose']['m2']['n_elems']} hex",
                        "evidence_class": "INDEPENDENT_NUMERICAL_VALIDATION",
                        "status": "EXECUTED",
                        "limitations": f"T_max difference {mo['T_max_err_K']:+.3f} K is within "
                                       f"MOOSE's own mesh change {mo['moose_mesh_change_K']:+.3f} K"
                                       "; FE vs FE, so the runtime ratio is solver-to-solver"})
    mb = J("reference_mech_bilayer.json")
    if mb:
        c50 = mb.get("ccx_n50") or mb.get("ccx_n80")
        c30 = mb.get("ccx_n30") or mb.get("ccx_n40")
        prod = c50["warp_pv_mm"]
        tim = mb["timoshenko"]["warp_pv_mm"]
        ps, pr = _tm(c50)
        out.append({"stage": "mech_bilayer_closed_form", "production_model": "CalculiX C3D8I",
                    "model_type": "FEM", "reference_tool": "Timoshenko bimaterial curvature",
                    "reference_type": "CLOSED FORM",
                    "observable": "peak-to-valley warpage, Si-on-organic bilayer, dT = 100 K, "
                                  "minimal supports",
                    "production_value": prod, "reference_value": tim,
                    "error_metric": "(prod - ref) / ref", "error": (prod - tim) / tim,
                    "production_runtime_s": ps or c50["wall_s"],
                    "production_runtime_range_s": pr, "timing_method": TIMING if ps else "",
                    "machine": mach, "cores": "ccx 8", "solver_version": CCX,
                    "mesh_or_dof": f"{c50['n_elems']} C3D8I; coarse level differs "
                                   f"{100*abs(c30['warp_pv_mm']-prod)/prod:.3f} %",
                    "evidence_class": "CLOSED_FORM_VERIFICATION", "status": "EXECUTED",
                    "limitations": "the closed form ignores free-edge effects, so a few-tenths "
                                   "percent difference is expected, not identity"})
        a = mb.get("aedt") or {}
        if a.get("solved") and a.get("warp_pv_mm"):
            ref = a["warp_pv_mm"]
            rs, rr = _tm(a)
            out.append({"stage": "mech_bilayer_aedt", "production_model": "CalculiX C3D8I",
                        "model_type": "FEM", "reference_tool": AEDT + " structural",
                        "reference_type": "INDEPENDENT COMMERCIAL FEM",
                        "observable": "peak-to-valley warpage, same bilayer, dT = 100 K",
                        "production_value": prod, "reference_value": ref,
                        "error_metric": "(prod - ref) / ref", "error": (prod - ref) / ref,
                        "production_runtime_s": ps, "production_runtime_range_s": pr,
                        "reference_runtime_s": rs, "reference_runtime_range_s": rr,
                        "speedup": (rs / ps) if (rs and ps) else None,
                        "timing_method": TIMING, "machine": mach, "cores": "ccx 8 / AEDT 4",
                        "solver_version": f"{CCX} / AEDT 2026.1",
                        "evidence_class": "INDEPENDENT_NUMERICAL_VALIDATION",
                        "status": "EXECUTED",
                        "limitations": "AEDT warpage per kelvin from two solved temperature "
                                       "levels (reference-temperature independent); "
                                       f"read on the {a.get('extracted_on')} of the silicon; "
                                       "FE vs FE runtime ratio"})
        else:
            out.append({"stage": "mech_bilayer_aedt", "production_model": "CalculiX C3D8I",
                        "reference_tool": AEDT + " structural",
                        "status": "REFERENCE_NOT_SOLVED", "evidence_class": "UNVALIDATED",
                        "limitations": "the AEDT structural solve did not complete: "
                                       + str(a.get("error", "no result"))[:160]})
    sc = D / "solver_check"
    it = sc / "Z1_HV_S0_h1.1_ITERATIVE_CHOLESKY_t10.json"
    dr = sc / "Z1_HV_S0_h1.1_SPOOLES_t1.json"
    if it.exists() and dr.exists():
        a, b = json.loads(it.read_text()), json.loads(dr.read_text())
        if a.get("ok") and b.get("ok"):
            e_w = (a["die_warpage_pv_um"] - b["die_warpage_pv_um"]) / b["die_warpage_pv_um"]
            e_u = (a["du_c_um"] - b["du_c_um"]) / b["du_c_um"]
            out.append({"stage": "structural_solver_iterative_vs_direct",
                        "production_model": "CalculiX ITERATIVE CHOLESKY",
                        "model_type": "LINEAR SOLVER", "reference_tool":
                        "CalculiX SPOOLES (direct), same mesh and temperature field",
                        "reference_type": "DIRECT SOLVER",
                        "observable": "Z1 HV-S0 die warpage and critical-joint du, "
                                      f"{a['n_elems']} C3D8I",
                        "production_value": a["die_warpage_pv_um"],
                        "reference_value": b["die_warpage_pv_um"],
                        "error_metric": "(iterative - direct) / direct, die warpage",
                        "error": e_w, "machine": mach,
                        "evidence_class": "SOLVER_VERIFICATION", "status": "EXECUTED",
                        "limitations": f"du_c difference {e_u:+.4%}; needed because SPOOLES "
                                       "solves 38.6k C3D8I elements but segfaults at 43k in this build, "
                                       "so refined meshes use the iterative solver"})
    try:
        import final_closure_results as FR
        mc = FR.mesh_convergence()
    except Exception:
        mc = None
    for arch, c in ((mc or {}).get("cases") or {}).items():
        out.append({"stage": f"mesh_convergence_{arch}", "production_model":
                    "physical ETM at h_xy = 1.1 mm", "observable":
                    "T_max, die warpage, du_c, P_loss: base vs nested refinements "
                    + ", ".join(c["levels"]),
                    "error": c["worst"], "error_metric": "largest relative change",
                    "evidence_class": "MESH_CONVERGENCE",
                    "status": "EXECUTED" if c["complete"] else "INCOMPLETE",
                    "limitations": f"declared tolerance {mc['tolerance_rel']:.0%}; "
                                   f"pass = {c['pass']}; self-refinement says nothing about "
                                   "physical accuracy"})
    hist = [("tsv_transition", "compact end/spreading", "MOOSE", "0.25-0.73 %"),
            ("rdl_plane_historical", "2-D sheet (historical geometry)", "MOOSE",
             "power 0.45-1.10 %, IR 0.90-2.19 %"),
            ("cooling_compact", "fin/Nusselt correlation", "MOOSE explicit fins",
             "3.78 % in validated domain"),
            ("homogenised_k_historical", "effective tensor", "numerical RVE",
             "k_z ~1 %, bump k_xy ~1.5 %")]
    for st, pm, ref, err in hist:
        out.append({"stage": st, "production_model": pm, "reference_tool": ref,
                    "error": err, "evidence_class": "INDEPENDENT_NUMERICAL_VALIDATION",
                    "status": "HISTORICAL_REFERENCE_NOT_RERUN",
                    "limitations": "earlier geometry; carried as history, not re-run on the "
                                   "physical lineage"})
    out.append(icepak_row())
    out.append({"stage": "converter_waveform", "production_model": "closed-form loss model",
                "reference_tool": "none available", "status": "NOT_EXECUTED",
                "evidence_class": "UNVALIDATED",
                "limitations": "no circuit simulator installed and no switch-state schedule "
                               "exists; results are conditioned on named HV scenarios"})
    pn = J("package_network.json")
    if pn:
        w = max(c["worst_delta"] for c in pn["convergence"].values())
        out.append({"stage": "pkg_rdl_convergence", "production_model":
                    "aligned graded FV sheet", "observable": "worst of five metrics, "
                    "levels L2->L3, all four networks at N=%d" % pn["matched_count"],
                    "error": w, "error_metric": "relative change between finest levels",
                    "evidence_class": "MESH_CONVERGENCE", "status": "EXECUTED",
                    "limitations": "self-refinement; says nothing about physical accuracy"})
    return out


#: a production model that is a closed form, a homogenisation rule or a compact correlation
#: against a field solver: the runtime ratio is model reduction, not a solver speedup, and
#: is never printed as one (final-closure Part 35); both absolute runtimes are reported
MODEL_REDUCTION_TYPES = ("ANALYTICAL", "REDUCED MATERIAL MODEL")


def ratio_kind(x):
    if not isinstance(x.get("speedup"), (int, float)):
        return None
    if x.get("model_type") in MODEL_REDUCTION_TYPES or x["stage"] == "cooling_icepak":
        return "model_reduction"
    return "solver_to_solver"


def main():
    r = rows()
    for x in r:
        x["runtime_ratio_kind"] = ratio_kind(x)
    with (D / "accuracy_speed_matrix.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for x in r:
            w.writerow({k: x.get(k, "") for k in FIELDS})
    (D / "accuracy_speed_matrix.json").write_text(json.dumps(
        {"rows": r, "note": "no overall framework accuracy is defined",
         "host": platform.node() and "redacted"}, indent=1, default=str))
    for x in r:
        e = x.get("error")
        es = f"{e:+.3%}" if isinstance(e, float) else str(e)
        sp = x.get("speedup")
        print(f"  {x['stage']:26s} {x.get('status',''):30s} err={es:>14s} "
              f"speedup={sp if not isinstance(sp, float) else round(sp, 1)}")


if __name__ == "__main__":
    main()
