"""Freeze the final physical lineage FROM the run artifacts.

Writes:
  electrical_ledger.{json,csv}   every conductor, every architecture and scenario,
                                 at the CONVERGED E-T temperatures
  energy_audit.json              the three conservation checks, kept apart
  final_results.json             one row per architecture and scenario
  FINAL_PAPER_DECISION.md        generated, never hand-edited

The three energy checks are NOT interchangeable and are reported separately:
  1. fixed-point consistency  P_in = 48 V x I_48 with I_48 solved from P_load + P_loss.
     DEFINITIONAL: it closes by construction and is reported as consistency only.
  2. heat-map deposition      sum of volumetric sources over meshed volume = ledger total.
  3. thermal heat balance     q_top + q_bottom (both COMPUTED from the solved field) = Q.
Only 2 and 3 can fail; they are the conservation evidence.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
D = R / "research" / "final_closure"
SCEN = ("HV_S0", "HV_S1", "HV_S2")
NORTON_T_MAX_C = 125.0
#: melting onset of the joint alloy (SAC305, near-eutectic Sn-Ag-Cu: about 217 C).
#: Context only: it flags an operating point as physically inadmissible, it ranks nothing.
SAC305_SOLIDUS_C = 217.0


def hottest_joint_C(mech):
    """The hottest of ALL searched joint sites. Admissibility is decided on it, not on the
    critical (largest-du) joint: one joint at the melting onset makes the operating point
    inadmissible whichever joint is critical."""
    js = mech["joint_search"]
    return max([r["T_C"] for r in js["ranked"]] + [js["critical"]["T_C"]])
import sys as _sys                                                    # noqa: E402
_sys.path.insert(0, str(R / "scripts"))
import final_closure_physical_etm as E                              # noqa: E402


def J(name):
    f = D / name
    return json.loads(f.read_text()) if f.exists() else None


def main():
    rows, final, audit = [], [], {}
    for scen in SCEN:
        loc = J(f"local_solder_{scen}.json")
        for arch in ("Z1", "Z2"):
            pf = E.case_path(arch, scen)
            r = json.loads(pf.read_text()) if pf.exists() else None
            if r is None or "mechanics" not in r:
                continue
            if not E.current_lineage(r):
                raise RuntimeError(f"{pf.name} is not of the corrected lineage (variant "
                                   f"{r.get('architecture_variant')}, no in-cell E-T "
                                   "temperatures): rerun it before any decision")
            for x in r["ledger_rows"]:
                rows.append(dict(x, T_converged=True))
            th, mm, h = r["thermal"], r["mechanics"], r["et_history"][-1]
            if tuple(E.PRODUCTION_REFINE) != (1, 1) and \
                    mm.get("structural_solver") != E.PRODUCTION_SOLVER:
                raise RuntimeError(f"{pf.name}: solved with {mm.get('structural_solver')}, "
                                   f"not the verified {E.PRODUCTION_SOLVER}")
            crit = mm["joint_search"]["critical"]
            lc = (loc or {}).get("cases", {}).get(arch, {})
            resp = lc.get("response") or {}
            lm = local_production(arch, scen, resp)
            final.append({
                "arch": arch, "scenario": scen,
                "architecture_variant": r.get("architecture_variant"),
                "hv_feed": r.get("hv_feed"),
                "forbidden_terms": sorted({x["term"] for x in r["ledger_rows"]}
                                          & {"P_pkg_RDL_HV_supply", "P_pkg_RDL_HV_return",
                                             "P_BGA_supply", "P_BGA_return"})
                if r.get("hv_feed") == "DIRECT_FEED" else [],
                # the legacy name stays for compatibility; the explicit fields say which
                # boundary the number belongs to (LOSS_BOUNDARY)
                "P_loss_w": r["P_loss_w"], "P_loss_package_internal_w": r["P_loss_w"],
                "loss_boundary": LOSS_BOUNDARY[arch],
                **platform_fields(arch, scen, r),
                "I_48_avg_a": r["i_hv_avg_a"],
                "T_max_C": th["T_max_C"], "T_die_mean_C": h["T_die_mean_C"],
                "T_conv_mean_C": h["T_conv_C"],
                "die_warpage_pv_um": mm["die_warpage_pv_um"],
                "pkg_warpage_pv_um": mm.get("pkg_warpage_pv_um"),
                "critical_joint_xy_mm": [crit["x_mm"], crit["y_mm"]],
                "du_c_um": crit["du_um"], "T_joint_C": crit["T_C"],
                "d_eps_in_per_cycle": lm["value"],
                "d_eps_in_L0": resp.get("d_peeq_per_cycle"),
                "local_mesh_level": lm["level"], "local_mesh_status": lm["status"],
                "local_mesh_U_rel": lm["U"],
                "inelastic_strain_range": resp.get("range_eq_inelastic"),
                "inelastic_work_MJ_m3": resp.get("inelastic_work_MJ_per_m3"),
                "local_stab_change_pct": resp.get("stab_change_pct"),
                "local_mesh_change_pct_L0_L1": lc.get("mesh_change_pct"),
                "T_joint_outside_norton_calibration": crit["T_C"] > NORTON_T_MAX_C,
                "T_joint_hottest_C": hottest_joint_C(mm),
                "T_joint_at_or_above_solder_solidus": (hottest_joint_C(mm)
                                                       >= SAC305_SOLIDUS_C),
                "et_iterations": len(r["et_history"]), "et_converged": r["et_converged"],
                "et_final_max_dT_K": h["max_dT_K"], "et_final_dP_rel": h["dP_rel"],
                "et_wall_s": r["et_wall_s"], "mech_wall_s": mm["wall_s"],
                "et_first_jump_w": (r["et_history"][1]["P_loss_w"]
                                    - r["et_history"][0]["P_loss_w"])
                if len(r["et_history"]) > 1 else None,
                "n_joint_sites": mm["joint_search"]["n_sites"],
                "n_elems": th["n_elems"], "threads": r["threads"],
                "case_file": pf.name, "mesh_label": E.production_label(),
                "structural_solver": mm.get("structural_solver", "SPOOLES")})
            audit[f"{arch}_{scen}"] = {
                "fixed_point_consistency_rel": r["energy_ledger"]["residual_rel"],
                "fixed_point_note": "DEFINITIONAL -- closes by construction",
                "deposition_residual_rel": th["deposit_residual_rel"],
                "thermal_balance_residual_rel": th["energy_residual_rel"],
                "q_top_W": th["q_top_W"], "q_bottom_W": th["q_bot_W"],
                "Q_ledger_W": th["Q_ledger_W"]}
    with (D / "electrical_ledger.csv").open("w", newline="") as fh:
        # union of keys: only the LV rows carry alternative_P_w
        w = csv.DictWriter(fh, fieldnames=list(dict.fromkeys(k for x in rows for k in x)),
                           restval="")
        w.writeheader(); w.writerows(rows)
    (D / "electrical_ledger.json").write_text(json.dumps(
        {"rows": rows, "note": "converged E-T temperatures; HV side per named scenario"},
        indent=1, default=float))
    tol = 1e-6
    audit_pass = all(abs(a["deposition_residual_rel"]) < tol
                     and abs(a["thermal_balance_residual_rel"]) < tol
                     for a in audit.values())
    (D / "energy_audit.json").write_text(json.dumps(
        {"tolerance_rel": tol, "pass": audit_pass, "cases": audit}, indent=1))
    mc = mesh_convergence()
    (D / "mesh_convergence.json").write_text(json.dumps(mc, indent=1, default=float))
    (D / "coupling_checks.json").write_text(json.dumps(coupling_checks(), indent=1,
                                                       default=float))
    (D / "final_results.json").write_text(json.dumps(final, indent=1, default=float))
    (D / "control_results.json").write_text(json.dumps(control_results(final), indent=1,
                                                       default=float))
    (D / "ordering.json").write_text(json.dumps(ordering(final, mc), indent=1, default=float))
    write_decision(final, audit_pass)
    for f in final:
        print("%s %s P=%.3f Tmax=%.2f warp=%.2f du=%.4f d_eps=%s" % (
            f["arch"], f["scenario"], f["P_loss_w"], f["T_max_C"],
            f["die_warpage_pv_um"], f["du_c_um"], f["d_eps_in_per_cycle"]))


def control_results(final):
    """CONTROLLED_BGA_FED_Z1_VS_Z2_EXPERIMENT: the BGA-fed Z2 control (same corrected
    geometry, only the 48 V path differs) against the direct-fed Z2 and Z1, at HV-S0."""
    out = {"statement": ("This controlled experiment isolates the effect of BGA placement/cutout "
                         "when both architectures are forced to use an identical package-level "
                         "48-V feed. It is not the primary Z2 construction."), "cases": {}}
    f = E.case_path("Z2BF", "HV_S0")
    if not f.exists():
        return out
    r = json.loads(f.read_text())
    if r.get("architecture_variant") != "Z2_BGA_FED_CONTROL" or not E.current_lineage(r):
        raise RuntimeError(f"{f.name} is not the BGA-fed control of the corrected lineage")
    mm = r.get("mechanics") or {}
    crit = (mm.get("joint_search") or {}).get("critical") or {}
    pkg = {x["term"]: x["P_w"] for x in r["ledger_rows"] if x["term"].startswith(("P_pkg_RDL_HV",
                                                                                "P_BGA_"))}
    out["cases"]["Z2BF_HV_S0"] = {
        "architecture_variant": r["architecture_variant"], "P_loss_w": r["P_loss_w"],
        "T_max_C": r["thermal"]["T_max_C"], "die_warpage_pv_um": mm.get("die_warpage_pv_um"),
        "du_c_um": crit.get("du_um"), "T_joint_C": crit.get("T_C"),
        "package_48v_terms_w": pkg, "case_file": f.name}
    ref = {x["arch"]: x for x in final if x["scenario"] == "HV_S0"}
    for a in ("Z1", "Z2"):
        if a in ref:
            out["cases"][f"{a}_HV_S0"] = {k: ref[a][k] for k in
                                          ("architecture_variant", "P_loss_w", "T_max_C",
                                           "die_warpage_pv_um", "du_c_um", "T_joint_C")}
    if "Z2" in ref:
        out["direct_feed_minus_control_w"] = ref["Z2"]["P_loss_w"] - r["P_loss_w"]
    return out


def _q(r):
    m = r.get("mechanics") or {}
    crit = (m.get("joint_search") or {}).get("critical") or {}
    return {"T_max_C": r["thermal"]["T_max_C"],
            "die_warpage_pv_um": m.get("die_warpage_pv_um"),
            "du_c_um": crit.get("du_um"), "P_loss_w": r["P_loss_w"],
            "n_elems": r["thermal"]["n_elems"],
            "structural_solver": m.get("structural_solver", "SPOOLES")}


MESH_KEYS = ("T_max_C", "die_warpage_pv_um", "du_c_um", "P_loss_w")


def coupling_checks():
    """Prove that the temperature coupling of the TSV resistance is live: re-evaluate the
    converged HV-S0 ledger with ONLY the substrate temperature reset to 20 C. A coupling
    that is wired but pinned would return the same TSV loss."""
    import sys as _sys
    _sys.path.insert(0, str(R / "scripts"))
    import final_closure_ledger as FL
    out = {}
    for arch in ("Z1", "Z2"):
        pf = E.case_path(arch, "HV_S0")
        if not pf.exists():
            continue
        r = json.loads(pf.read_text())
        h = r["et_history"][-1]
        temps = E.temps_from_history(h)          # every converged temperature held
        tsv = lambda rows: sum(x["P_w"] for x in rows if x["term"].startswith("P_TSV_"))
        hot = tsv(r["ledger_rows"])
        cold_rows = FL.ledger(arch, "HV_S0", dict(temps, sub=20.0), r["i_hv_avg_a"])
        cold_rows = cold_rows["rows"] if isinstance(cold_rows, dict) else cold_rows
        cold = tsv(cold_rows)
        out[arch] = {"T_sub_C": temps["sub"], "P_TSV_converged_W": hot,
                     "P_TSV_at_20C_W": cold, "ratio": hot / cold,
                     "expected_ratio_rho_cu": 1.0 + 0.00393 * (temps["sub"] - 20.0)}
    # Z2's converter column hangs in the board cutout: its underside must carry NO film
    # (Z2-PASSIVE). Counted on the production mesh, not asserted; the count is cached per
    # mesh level because building the production mesh takes minutes.
    prev = (J("coupling_checks.json") or {}).get("z2_cutout_underside") or {}
    z2c = E.case_path("Z2", "HV_S0")
    n_el = json.loads(z2c.read_text())["thermal"]["n_elems"] if z2c.exists() else None
    if prev.get("mesh_refine") == list(E.PRODUCTION_REFINE) and prev.get("n_elems") == n_el:
        zc = prev
    else:
        import numpy as np
        import production_et as PE
        m, *_ = E.build("Z2", E.PRODUCTION_H_XY, E.PRODUCTION_REFINE)
        bot = np.asarray(PE.ccxio.bottom_film_faces(m), int)
        c = m.elem_centroids()[bot - 1]
        half = 0.5 * 23.36
        inside = int(np.sum((np.abs(c[:, 0]) < half) & (np.abs(c[:, 1]) < half)))
        zc = {"bottom_film_faces": int(len(bot)), "faces_inside_cutout": inside,
              "adiabatic": inside == 0, "mesh_refine": list(E.PRODUCTION_REFINE),
              "n_elems": int(m.n_elems)}
    return {"tsv_temperature_coupling": out, "z2_cutout_underside": zc,
            "note": "only T_sub changed; every other temperature held at its converged value"}


def _rel(a, b):
    """Relative change from level a to the finer level b, per observable."""
    return {k: (abs(b[k] - a[k]) / abs(b[k]) if a.get(k) is not None and b.get(k) is not None
                else None) for k in MESH_KEYS}


def _richardson(t1, t2, t3, h=(1.0, 1 / 2, 1 / 3)):
    """Observed order and extrapolated value from three nested levels (h1 > h2 > h3)."""
    import math
    d1, d2 = t2 - t1, t3 - t2
    if d1 == 0 or d2 == 0 or d1 * d2 < 0:
        return None
    target = d1 / d2
    f = lambda p: (h[0] ** p - h[1] ** p) / (h[1] ** p - h[2] ** p) - target
    lo, hi = 0.2, 6.0
    if f(lo) * f(hi) > 0:
        return None
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if f(lo) * f(mid) > 0 else (lo, mid)
    p = 0.5 * (lo + hi)
    c = d1 / (h[1] ** p - h[0] ** p)
    return {"order": p, "extrapolated": t1 - c * h[0] ** p,
            "finest_error_estimate": c * h[2] ** p}


def mesh_convergence():
    """Nested refinement of the h_xy = 1.1 mm grid. The production level is
    E.PRODUCTION_REFINE; it is checked against the next finer in-plane level and against
    the measured through-thickness sensitivity. The h_xy 1.1 -> 0.8 re-meshing is kept
    only as a sensitivity because it is not nested."""
    tag = lambda r: "r11" if tuple(r) == (1, 1) else f"r{r[0]}{r[1]}"
    P = tuple(E.PRODUCTION_REFINE)
    cases, stale = {}, []
    for arch in ("Z1", "Z2"):
        lv = {}
        for r in set(E.INPLANE_SEQUENCE) | set(E.THROUGH_THICKNESS):
            f = E.case_path(arch, "HV_S0", 1.1, r)
            if f.exists():
                j = json.loads(f.read_text())
                if not E.current_lineage(j):        # an older lineage never enters a ladder
                    stale.append(f.name)
                    continue
                lv[tag(r)] = _q(j)
        if not lv:
            continue
        seq = [tag(r) for r in E.INPLANE_SEQUENCE if tag(r) in lv]
        steps = {f"{a}->{b}": _rel(lv[a], lv[b]) for a, b in zip(seq, seq[1:])}
        # In-plane: production against the next finer level where that level carries the
        # observable; otherwise the coarser -> production change, which bounds the
        # production error for any convergence order >= 1 (stated per observable).
        checks, basis = {}, {}
        seqt = [tag(r) for r in E.INPLANE_SEQUENCE]
        prod = tag(P)
        i = seqt.index(prod)
        nxt = seqt[i + 1] if i + 1 < len(seqt) else None
        prv = seqt[i - 1] if i > 0 else None
        if prod in lv:
            ip, bs = {}, {}
            for k in MESH_KEYS:
                ip[k] = None
                if nxt in lv and None not in (lv[nxt].get(k), lv[prod].get(k)):
                    ip[k] = abs(lv[nxt][k] - lv[prod][k]) / abs(lv[nxt][k])
                    bs[k] = f"{prod} -> {nxt}"
                elif prv in lv and None not in (lv[prv].get(k), lv[prod].get(k)):
                    ip[k] = abs(lv[prod][k] - lv[prv][k]) / abs(lv[prod][k])
                    bs[k] = f"{prv} -> {prod} (bounds the {prod} error, order >= 1)"
            checks["in-plane"], basis["in-plane"] = ip, bs
        if "r11" in lv and "r12" in lv:
            checks["through-thickness"] = _rel(lv["r11"], lv["r12"])
            basis["through-thickness"] = {k: "r11 -> r12 (base in-plane resolution)"
                                          for k in MESH_KEYS}
        vals = [v for d in checks.values() for v in d.values() if v is not None]
        complete = len(checks) == 2 and all(v is not None for d in checks.values()
                                            for v in d.values())
        worst = max(vals) if vals else None
        rich = {}
        if all(t in lv for t in ("r11", "r21", "r31")):
            for k in MESH_KEYS:
                if all(lv[t][k] is not None for t in ("r11", "r21", "r31")):
                    rich[k] = _richardson(*(lv[t][k] for t in ("r11", "r21", "r31")))
        # Rule declared in FINAL_PAPER_SCOPE.md (2026-10-27 18:36) before any r31
        # mechanical result existed: an observable whose production-level change exceeds
        # the tolerance is BOUNDED by Richardson over r11/r21/r31 (Fs = 1.25), or unbounded.
        status, bound = {}, {}
        for k in MESH_KEYS:
            ch = [d.get(k) for d in checks.values()]
            if not complete:
                status[k] = "incomplete"
            elif max(ch) < E.MESH_TOL_REL:
                status[k] = "converged"
            elif rich.get(k) and prod in ("r21", "r31"):
                ext = rich[k]["extrapolated"]
                bound[k] = 1.25 * abs(lv[prod][k] - ext) / abs(ext)
                status[k] = "bounded"
            else:
                status[k] = "unbounded"
        rm = J(f"etm_{arch}_HV_S0_h0.8.json")
        if rm and not E.current_lineage(rm):
            stale.append(f"etm_{arch}_HV_S0_h0.8.json")
            rm = None
        remesh = None
        if rm and "r11" in lv:
            qr = _q(rm)
            remesh = {"h_mm": list(E.MESH_LEVELS_MM), "values": qr,
                      "rel_change": _rel(lv["r11"], qr),
                      "note": "re-graded, not nested: NOT a refinement (for Z2 the grid keeps "
                              "38 lines per axis and its largest element grows)"}
        cases[arch] = {"levels": lv, "steps": steps, "checks": checks,
                       "check_basis": basis, "worst": worst,
                       "complete": complete,
                       "pass": bool(complete and worst is not None and worst < E.MESH_TOL_REL),
                       "observable_status": status, "uncertainty_bound_rel": bound,
                       "bounded_ok": bool(complete and all(v in ("converged", "bounded")
                                                           for v in status.values())),
                       "richardson": rich, "remesh_sensitivity": remesh}
    base_step = {a: (c["steps"].get("r11->r21") or {}) for a, c in cases.items()}
    reason = ""
    if P != (1, 1) and base_step:
        tm = {a: v.get("T_max_C") for a, v in base_step.items() if v.get("T_max_C") is not None}
        if tm:
            reason = ("The unrefined grid fails the declared tolerance: splitting its in-plane "
                      "intervals in two changed T_max by " +
                      " and ".join(f"{100 * v:.1f} % ({a})" for a, v in sorted(tm.items())) +
                      ", so production uses the split grid.")
    checks = {}
    for f in sorted((D / "solver_check").glob("*.json")):
        checks[f.stem] = json.loads(f.read_text())
    return {"tolerance_rel": E.MESH_TOL_REL, "declared_before_reading": True,
            "stale_lineage_files_skipped": stale,
            "production_refine": list(P), "production_label": E.production_label(),
            "production_reason": reason,
            "method": "nested refinement of the h_xy = 1.1 mm grid: rN1 splits every in-plane "
                      "interval in N, r12 every layer's elements in two through the thickness; "
                      "every coarser node survives",
            "structural_solver_checks": checks, "cases": cases}


def local_production(arch, scen, resp_L0):
    """Local response on the production local mesh of the DECLARED policy
    (local_mesh_study.json). A case outside the study keeps its single L0 value, labelled."""
    st = (J("local_mesh_study.json") or {}).get("cases", {}).get(f"{arch}_{scen}")
    if st and st.get("production_value"):
        return {"value": st["production_value"], "level": st["production_level"],
                "status": st["status"], "U": st["U"]}
    v = resp_L0.get("d_peeq_per_cycle")
    return {"value": v, "level": "L0" if v else None,
            "status": ("single mesh (L0): finer levels not available" if v else "no response"),
            "U": None}


OBS = (("P_loss_package_internal_w", "package-internal loss"), ("T_max_C", "peak temperature"),
       ("die_warpage_pv_um", "die warpage"), ("du_c_um", "joint displacement driver"),
       ("d_eps_in_per_cycle", "local inelastic response"))
#: the case files carry the package-internal loss under its legacy name
LEGACY_KEY = {"P_loss_package_internal_w": "P_loss_w"}
#: where each architecture's loss is counted from (the two boundaries the paper uses)
LOSS_BOUNDARY = {
    "Z1": ("package-internal = platform-inclusive: from the BGA pads on the PCB, where the board "
           "48 V node common to both architectures meets the package"),
    "Z2": ("package-internal: from the backside regulator's 48 V input terminals; the external "
           "direct-feed loop R_Z2_direct_feed_loop is OUTSIDE this boundary, so the platform-"
           "inclusive loss is a function of that unsourced resistance (direct_feed_crossover)"),
    "Z2BF": "package-internal from the BGA pads (BGA-fed control)"}
SCEN_LABEL = {"HV_S0": "HV-S0", "HV_S1": "HV-S1", "HV_S2": "HV-S2"}


def scenario_classes(final):
    """Evidentiary weight of each scenario, derived from the joint states."""
    out = {}
    for s in SCEN:
        rows = [x for x in final if x["scenario"] == s]
        melt = [x["arch"] for x in rows if x.get("T_joint_at_or_above_solder_solidus")]
        ext = [x["arch"] for x in rows if x.get("T_joint_outside_norton_calibration")]
        if melt:
            out[s] = {"class": "stress / inadmissible",
                      "statement": f"Under {SCEN_LABEL[s]}, {', '.join(melt)} exits the valid "
                                   "solid-solder operating domain under the assumed cooling."}
        elif ext:
            out[s] = {"class": "sensitivity",
                      "statement": f"{SCEN_LABEL[s]} is a sensitivity case: the "
                                   f"{', '.join(ext)} joint lies beyond the Norton card's "
                                   "temperature calibration, so its local response is "
                                   "EXTRAPOLATED."}
        elif len({x["arch"] for x in rows}) < 2:
            out[s] = {"class": "incomplete",
                      "statement": f"{SCEN_LABEL[s]} is incomplete: "
                                   f"{', '.join(sorted({'Z1', 'Z2'} - {x['arch'] for x in rows}))} "
                                   "has no production result, so no comparison is drawn."}
        else:
            out[s] = {"class": "headline",
                      "statement": f"{SCEN_LABEL[s]} is the headline comparison: both "
                                   "architectures solve, both critical joints lie inside the "
                                   "constitutive calibration and the solder stays solid."}
        out[s]["extrapolated"] = ext
        out[s]["inadmissible"] = melt
    return out


def platform_fields(arch, scen, r):
    """Platform-inclusive loss, only at NAMED feed resistances: Z1's boundary already starts
    at the common board node; Z2's depends on R_Z2_direct_feed_loop, so it is given at
    R = 0, 1 mOhm and R* (where it equals Z1's), never as one scalar."""
    if arch != "Z2" or r.get("hv_feed") != "DIRECT_FEED":
        return {"P_loss_platform_inclusive_w": r["P_loss_w"]}
    import final_closure_direct_feed as DF
    temps = DF.converged_temps(r)
    c = ((J("direct_feed_crossover.json") or {}).get("scenarios") or {}).get(scen) or {}
    out = {"P_loss_platform_inclusive_w": None,
           "P_loss_platform_inclusive_note": "a function of R_Z2_direct_feed_loop; see the "
                                             "named points"}
    for lab, r_ohm in (("Rfeed_0", 0.0), ("Rfeed_1mohm", 1e-3)):
        pt = DF.platform_point(scen, temps, r_ohm)
        out[f"P_loss_platform_inclusive_at_{lab}_w"] = pt["P_total_w"]
    if c.get("R_star_mohm") and not c.get("Z1_operating_point_inadmissible"):
        out["P_loss_platform_inclusive_at_Rstar_w"] = c["P_Z1_w"]
        out["R_star_mohm"] = c["R_star_mohm"]
    return out


def platform_cell(c):
    """The platform-inclusive verdict of one scenario: conditional on R_Z2_direct_feed_loop
    (direct_feed_crossover.json), never a single Z1/Z2 winner while that resistance is
    unknown."""
    if c.get("Z1_operating_point_inadmissible"):
        return "not rankable"
    if c.get("R_star_mohm"):
        return f"conditional: Z2 lower only below R* = {c['R_star_mohm']:.3g} mOhm"
    return "Z1 lower for any feed resistance"


def platform_ordering(internal, sc):
    cx = (J("direct_feed_crossover.json") or {}).get("scenarios", {})
    per = {s: platform_cell(c) for s, c in cx.items()}
    parts = []
    for s, c in cx.items():
        lab = SCEN_LABEL.get(s, s)
        if c.get("Z1_operating_point_inadmissible"):
            parts.append(f"{lab} is not rankable (the Z1 operating point is inadmissible)")
        elif c.get("R_star_mohm"):
            v = internal["per_scenario"].get(s)
            parts.append(f"in {lab} Z2 has the lower platform-inclusive loss only while the "
                         f"complete direct-feed loop stays below R* = {c['R_star_mohm']:.3g} "
                         f"mOhm, and Z1 above it" + (" (at zero feed the package-internal "
                                                     "difference is itself within the "
                                                     "uncertainty)" if v == "unresolved" else ""))
        else:
            parts.append(f"in {lab} Z1 has the lower platform-inclusive loss for any feed "
                         "resistance")
    return {"per_scenario": per, "favoured": [], "favoured_where_resolved": None,
            "robust_across_scenarios": False, "conditional_on": "R_Z2_direct_feed_loop",
            "R_star_mohm": {s: c.get("R_star_mohm") for s, c in cx.items()},
            "loss_boundary": "platform_inclusive",
            "statement": ("The platform-inclusive loss has no unconditional winner: "
                          + "; ".join(parts) + ". No value of that loop resistance is known, "
                          "so no platform-level ranking is claimed.") if parts else
            "No direct-feed crossover is available.",
            "unresolved": [], "not_rankable": [s for s, v in per.items() if v == "not rankable"]}


def ordering(final, mc):
    """THE single source of every Z1/Z2 ordering claim. Per observable and scenario the
    verdict is 'Z1 lower', 'Z2 lower', 'unresolved' (gap within twice the measured
    discretisation uncertainty) or 'not rankable' (one architecture has no valid value).
    'not rankable' and 'unresolved' never count for either architecture.

    A scenario in which either critical joint is at or above the solder melting onset is
    not rankable for EVERY observable, not only the local one: the electrical, thermal and
    structural models all carry solid-solder properties, so that operating point is an
    infeasibility result (brief Part 5), never a normal operating comparison."""
    rows = {(x["arch"], x["scenario"]): x for x in final}
    sc = scenario_classes(final)
    ls = (J("local_mesh_study.json") or {}).get("cases", {})
    out = {}
    for key, name in OBS:
        mesh = None
        mk = LEGACY_KEY.get(key, key)
        if mk in MESH_KEYS and mc.get("cases"):
            mesh = max([(c["checks"][t].get(mk) or 0.0) for c in mc["cases"].values()
                        for t in c["checks"]]
                       + [c.get("uncertainty_bound_rel", {}).get(mk, 0.0)
                          for c in mc["cases"].values()])
        per, gaps, unc, why = {}, {}, {}, {}
        for s in SCEN:
            a, b = rows.get(("Z1", s)), rows.get(("Z2", s))
            if not (a and b):
                continue
            va = a.get(key, a.get(LEGACY_KEY.get(key, key)))
            vb = b.get(key, b.get(LEGACY_KEY.get(key, key)))
            melt = [x["arch"] for x in (a, b) if x.get("T_joint_at_or_above_solder_solidus")]
            if melt or va is None or vb is None:
                per[s] = "not rankable"
                why[s] = (f"the {', '.join(melt)} operating point is physically inadmissible "
                          "for the solid-solder model" if melt else
                          "no converged response for one architecture")
                continue
            if key == "d_eps_in_per_cycle":
                us = [ls.get(f"{x}_{s}", {}).get("U") for x in ("Z1", "Z2")]
                u = max(us) if all(x is not None for x in us) else None
            else:
                u = mesh
            gap = abs(va - vb) / max(abs(va), abs(vb))
            gaps[s], unc[s] = gap, u
            fav = "Z1" if va < vb else "Z2"
            if u is None:
                per[s], why[s] = "unresolved", "no quantified discretisation uncertainty"
            elif gap > 2 * u:
                per[s] = f"{fav} lower"
            else:
                per[s] = "unresolved"
                why[s] = "the difference lies within the measured discretisation uncertainty"
        resolved = {k: v for k, v in per.items() if v.endswith("lower")}
        fav = sorted({v.split()[0] for v in resolved.values()})
        o = {"per_scenario": per, "relative_gap": gaps, "uncertainty_rel": unc,
             "mesh_change": mesh, "reasons": why, "favoured": fav,
             "robust_across_scenarios": len(fav) == 1 and len(resolved) == len(per),
             "favoured_where_resolved": fav[0] if len(fav) == 1 else None,
             "unresolved": [k for k, v in per.items() if v == "unresolved"],
             "not_rankable": [k for k, v in per.items() if v == "not rankable"],
             "hv_s0_within_mesh_uncertainty": per.get("HV_S0") == "unresolved"}
        o["statement"] = _statement(key, name, o, rows)
        o["loss_boundary"] = ("package_internal" if key == "P_loss_package_internal_w"
                              else None)
        out[key] = o
    out["P_loss_platform_inclusive_w"] = platform_ordering(out["P_loss_package_internal_w"], sc)
    return {"orderings": out, "scenario_classes": sc,
            "rule": "an ordering is claimed in a scenario only where the Z1/Z2 gap exceeds "
                    "twice the measured discretisation uncertainty of that observable; a "
                    "scenario in which either critical joint is at or above the solder melting "
                    "onset is not rankable for any observable (every model carries "
                    "solid-solder properties); 'unresolved' and 'not rankable' scenarios count "
                    "for neither architecture"}


def _statement(key, name, o, rows):
    """The one sentence set every text (decision, paper, slides) uses for an ordering.

    The brief's wordings are used where they are TRUE: 'in every scenario for which a valid
    two-architecture comparison can be made' only when every comparable scenario is
    resolved; the HV-S0 thermal sentence verbatim when HV-S0 is unresolved. When a
    comparable scenario is inside the uncertainty, the resolved scenarios are named instead,
    because the general sentence would then overstate the result."""
    per, fav = o["per_scenario"], o["favoured_where_resolved"]
    what = "response comparison" if key == "d_eps_in_per_cycle" else "comparison"
    resolved = [s for s, v in per.items() if v.endswith("lower")]
    unres = [s for s, v in per.items() if v == "unresolved"]
    notr = [s for s, v in per.items() if v == "not rankable"]
    lab = lambda xs: " and ".join(SCEN_LABEL[x] for x in xs)
    why_nr = [f"{SCEN_LABEL[s]} is not rankable because {o['reasons'].get(s)}" for s in notr]
    if o["robust_across_scenarios"]:
        head = f"{fav} has lower {name} in every named scenario."
    elif fav and not unres:
        head = (f"{fav} has lower {name} in every scenario for which a valid two-architecture "
                f"{what} can be made" + ("; " + "; ".join(why_nr) if why_nr else "") + ".")
        why_nr = []
    elif fav:
        head = (f"{fav} has lower {name} in {lab(resolved)}, where the gap exceeds twice the "
                "measured discretisation uncertainty.")
    elif not resolved:
        head = f"No {name} ranking can be drawn."
    else:                       # resolved in several scenarios, but not for the same design
        head = ("; ".join(f"{per[s].split()[0]} has lower {name} in {SCEN_LABEL[s]}"
                          for s in resolved)
                + f" (each gap exceeds twice the measured discretisation uncertainty): the "
                f"{name} ordering reverses with the scenario.")
    tail = []
    for s in unres:
        if key == "T_max_C":
            d = abs(rows[("Z1", s)]["T_max_C"] - rows[("Z2", s)]["T_max_C"])
            tail.append(f"The approximately {d:.0f} C difference lies within the measured "
                        "discretization uncertainty; therefore no thermal architecture "
                        f"ranking is drawn for {SCEN_LABEL[s]}.")
        else:
            ext = [a for a in ("Z1", "Z2") if key == "d_eps_in_per_cycle"
                   and rows[(a, s)].get("T_joint_outside_norton_calibration")]
            tail.append(f"In {SCEN_LABEL[s]} the difference lies within the measured "
                        "discretisation uncertainty" + (f" (and the {' and '.join(ext)} "
                        "response is extrapolated)" if ext else "") + ", so no ranking is "
                        "drawn.")
    tail += [w + "." for w in why_nr]
    return " ".join([head] + tail)


def _r31_contraction():
    """max |dT| per E-T iterate (it1 onward) of the r31 ladder cases, from their files."""
    out = []
    for arch in ("Z2", "Z1"):
        f = E.case_path(arch, "HV_S0", 1.1, (3, 1))
        r = json.loads(f.read_text()) if f.exists() else {}
        if r and E.current_lineage(r):
            out.append(", ".join(f"{h['max_dT_K']:.2g}" for h in r["et_history"][1:])
                       + f" K for {arch}")
    return "; ".join(out) or "r31 not yet available"


def write_decision(final, audit_pass):
    acc = J("accuracy_speed_matrix.json") or {"rows": []}
    pn = J("package_network.json") or {}
    lines = ["# Final paper decision", "",
             "Generated by `scripts/final_closure_results.py` from the run artifacts. "
             "Do not edit by hand.", ""]
    spec = J("z2_direct_feed_architecture.json") or {}
    ar = spec.get("architectures", {})
    lines += ["## Architecture (frozen before these results)", "",
              "`research/final_closure/Z2_DIRECT_FEED_ARCHITECTURE.md`.", ""]
    for a in ("Z1", "Z2"):
        x = ar.get(a) or {}
        lines.append(f"- **{a} ({x.get('variant')})**: 48 V {x.get('hv_input')}; crosses the "
                     f"substrate: {x.get('crosses_substrate')}; conversion "
                     f"{x.get('conversion')}. Path: " + " -> ".join(x.get("power_path", [])))
    va = spec.get("vr_attach") or {}
    att_n = lambda k: (((J("vr_attach_density_study.json") or {}).get("cases") or {})
                       .get("dense") or {}).get(k)
    sw = spec.get("sidewall") or {}
    lines += [f"- Z2 VR-to-substrate attach: {va.get('technology')}, {va.get('h_total_um')} um "
              f"({va.get('h_cu_um')} Cu + {va.get('h_cap_um')} cap), {va.get('d_um')} um at "
              f"{va.get('pitch_um')} um pitch, {att_n('n_vdd')} VDD + {att_n('n_gnd')} GND "
              "bumps/cell on the real lattice (CLOSE_ANALOG geometry); carries 1 V only.",
              f"- Z2 sidewall: {sw.get('clearance_mm')} mm clearance {sw.get('clearance_content')} "
              f"between the {sw.get('cell_grid_bbox_mm')} mm cell grid and the "
              f"{sw.get('cutout_mm')} mm opening ({sw.get('defect_resolved')} resolved).",
              "- BGA fields: Z1 mechanical %s sites, 48 V power %s; Z2 mechanical %s sites, 48 V "
              "power none." % ((ar.get("Z1") or {}).get("bga_mechanical_field_sites"),
                               (ar.get("Z1") or {}).get("bga_48v_power_field"),
                               (ar.get("Z2") or {}).get("bga_mechanical_field_sites")), ""]
    lines += ["## Electrical", "",
              f"Z1 package 48 V network: **{pn.get('matched_count')} balls per rail** (smallest "
              "legal count passing the 1.5 A/ball ENGINEERING criterion at HV-S0, verified on "
              "the resolved grid). The primary Z2 is direct-fed and has NO package 48 V network; "
              "the BGA-fed Z2 network belongs only to Z2_BGA_FED_CONTROL.", ""]
    if pn:
        name = {"Z1": "Z1 (production)", "Z2": "Z2_BGA_FED_CONTROL (controlled experiment only)"}
        for a, L in pn["loop"].items():
            lines.append(f"- {name.get(a, a)}: R_supply {L['r_supply_ohm']*1e3:.4f} + R_return "
                         f"{L['r_return_ohm']*1e3:.4f} = R_loop {L['r_loop_ohm']*1e3:.4f} mOhm "
                         f"(20 C), converged on all five metrics: {L['converged']}")
        lines.append("")
    cx = J("direct_feed_crossover.json") or {}
    if cx.get("scenarios"):
        lines += ["## Direct-feed crossover (R_Z2_direct_feed_loop, swept, never assumed)", "",
                  f"Boundary: {cx.get('boundary')}.", ""]
        for s_, c in cx["scenarios"].items():
            lines.append(f"- {s_}: P_Z1 {c['P_Z1_w']:.3f} W; P_Z2 at zero feed "
                         f"{c['P_Z2_internal_recomputed_w']:.3f} W (advantage "
                         f"{c['advantage_at_zero_feed_w']:+.3f} W); crossover R* = "
                         + (f"{c['R_star_mohm']:.4g} mOhm" if c.get("R_star_mohm") is not None
                            else "none in range")
                         + (" -- Z1 operating point inadmissible: no comparison drawn"
                            if c.get("Z1_operating_point_inadmissible") else
                            (f"; requirement: {c['requirement']}" if c.get("requirement") else "")))
        lines.append("")
    ctl = J("control_results.json") or {}
    if ctl.get("cases"):
        lines += ["## Controlled BGA-fed experiment (CONTROLLED_BGA_FED_Z1_VS_Z2_EXPERIMENT)", "",
                  ctl["statement"], ""]
        _fmt = lambda v, d: "n/a" if v is None else f"{v:.{d}f}"        # noqa: E731
        for k, c in ctl["cases"].items():
            lines.append(f"- {k} ({c.get('architecture_variant')}): package-internal loss {c['P_loss_w']:.3f} W, "
                         f"T_max {c['T_max_C']:.2f} C, warpage "
                         f"{_fmt(c.get('die_warpage_pv_um'), 2)} um, du_c {_fmt(c.get('du_c_um'), 4)} um")
        if "direct_feed_minus_control_w" in ctl:
            lines.append(f"- direct feed minus BGA-fed control: "
                         f"{ctl['direct_feed_minus_control_w']:+.3f} W (package-internal)")
        lines.append("")
    lines += ["| arch | scenario | package-internal loss (W) | T_max (C) | die warp (um) | du_c (um) | "
              "T_joint (C) | d_eps_in / cycle |", "|---|---|---|---|---|---|---|---|"]
    for f in final:
        de = f["d_eps_in_per_cycle"]
        lines.append(f"| {f['arch']} | {f['scenario']} | {f['P_loss_w']:.3f} | "
                     f"{f['T_max_C']:.2f} | {f['die_warpage_pv_um']:.2f} | {f['du_c_um']:.4f} | "
                     f"{f['T_joint_C']:.1f}{' (extrap.)' if f['T_joint_outside_norton_calibration'] else ''} | "
                     f"{'%.4e' % de if de else 'n/a'} |")
    od_all = J("ordering.json") or {}
    od = od_all.get("orderings", {})
    lines += ["", "## Scenario evidentiary weight", ""]
    for s_, c in (od_all.get("scenario_classes") or {}).items():
        lines.append(f"- **{s_}** ({c['class']}): {c['statement']}")
    lines += ["", "## Architecture ordering per scenario", "",
              "Rendered from `ordering.json`, the single source of every ordering claim.", "",
              "| scenario | package-internal loss | platform-inclusive loss | T_max | die warpage "
              "| joint driver | local response |",
              "|---|---|---|---|---|---|---|"]
    cols = [OBS[0][0], "P_loss_platform_inclusive_w"] + [k for k, _ in OBS[1:]]
    for s_ in SCEN:
        cells = [(od.get(k) or {}).get("per_scenario", {}).get(s_, "n/a") for k in cols]
        lines.append(f"| {s_} | " + " | ".join(cells) + " |")
    lines += ["", "## Robustness", ""]
    for k, name in list(OBS[:1]) + [("P_loss_platform_inclusive_w", "platform-inclusive loss")] \
            + list(OBS[1:]):
        if k in od:
            lines.append(f"- {name}: {od[k]['statement']}")
    lines += ["", "## Accuracy and runtime (stage by stage)", "",
              "Absolute runtimes on one machine; a runtime ratio is given only between field "
              "solvers. A closed form or compact correlation against a field solve is model "
              "reduction, not a speedup, and no ratio is printed for it.", "",
              "| stage | reference | error | production | reference | ratio (field solvers) "
              "| status |", "|---|---|---|---|---|---|---|"]
    tfmt = lambda v: ("" if not isinstance(v, (int, float)) else f"{v * 1e6:.1f} us"
                      if v < 1e-3 else f"{v * 1e3:.1f} ms" if v < 1 else f"{v:.1f} s")
    for r in acc["rows"]:
        e = r.get("error")
        sp = r.get("speedup")
        ratio = (f"{sp:.2f}x" if isinstance(sp, (int, float))
                 and r.get("runtime_ratio_kind") == "solver_to_solver" else "")
        lines.append(f"| {r['stage']} | {r.get('reference_tool', '')} | "
                     f"{('%+.3f %%' % (100 * e)) if isinstance(e, float) else e} | "
                     f"{tfmt(r.get('production_runtime_s'))} | "
                     f"{tfmt(r.get('reference_runtime_s'))} | {ratio} | {r.get('status', '')} |")
    lines += ["", "## Conservation", "",
              f"Heat-map deposition and computed thermal heat balance close to 1e-6 in every "
              f"case: **{audit_pass}**. The electrical fixed-point residual is definitional "
              f"and is not counted as conservation evidence.", "",
              "## What remains unqualified (does not invalidate the paper)", "",
              "- the 48 V input waveform: results are conditioned on named scenarios HV-S0/S1/S2;",
              "- the 1.5 A/ball criterion: an engineering provisioning rule, not an allowable;",
              "- absolute solder life: response only, per Darveaux (10.1115/1.1413764);",
              "- EM-safe current densities for balls, pads, TSVs: none claimed;",
              "- joint temperatures at or above the SAC305 melting onset (about 217 C) mark a "
              "physically inadmissible operating point, not a response: " +
              (", ".join(f"{f['arch']} {f['scenario']} ({f['T_joint_C']:.0f} C)" for f in final
                         if f["T_joint_at_or_above_solder_solidus"]) or "none") + ";",
              "- joint temperatures above the Norton card's 125 C calibration are flagged as "
              "extrapolation (" + (", ".join(f"{f['arch']} {f['scenario']}" for f in final
                                             if f["T_joint_outside_norton_calibration"])
                                   or "none") + ").", ""]
    tex = (R / "manuscript" / "ETM_DVPD_JOURNAL_MANUSCRIPT.tex")
    t = tex.read_text() if tex.exists() else ""
    manuscript_on_lineage = (r"\input{final_lineage_macros}" in t
                             and r"\label{sec:physical}" in t
                             and r"\PlossZone" in t[t.find(r"\begin{abstract}"):
                                                     t.find(r"\end{abstract}")])
    lines.append(f"Active manuscript carries the physical lineage (macros, physical-comparison "
                 f"section, abstract): **{manuscript_on_lineage}**.")
    lines.append("")
    mc = J("mesh_convergence.json") or {"cases": {}}
    od = (J("ordering.json") or {}).get("orderings", {})
    mesh_ok = bool(mc["cases"]) and all(c["complete"] and (c["pass"] or c.get("bounded_ok"))
                                        for c in mc["cases"].values())
    lines += ["## Mesh convergence (nested refinement)", "",
              f"Production mesh: {mc.get('production_label', 'n/a')}. "
              f"{mc.get('production_reason', '')}", ""]
    for arch, c in mc["cases"].items():
        for chk, rel in c["checks"].items():
            v = [x for x in rel.values() if x is not None]
            lines.append(f"- {arch}, {chk}: largest relative change "
                         f"{100 * max(v):.3f} % (declared {100 * mc['tolerance_rel']:.0f} %)"
                         if v else f"- {arch}, {chk}: n/a")
        for k, st in (c.get("observable_status") or {}).items():
            if st != "converged":
                u = (c.get("uncertainty_bound_rel") or {}).get(k)
                lines.append(f"  - `{k}`: {st}" + (f", Richardson bound U = {100 * u:.2f} % on "
                                                    f"the production grid" if u else ""))
        lines.append(f"- {arch}: " + ("PASS" if c["pass"] else
                                      "BOUNDED (declared rule)" if c.get("bounded_ok") else
                                      "NOT PASSED") + ("" if c["complete"] else " (INCOMPLETE)"))
    for key, o in od.items():
        if o.get("mesh_change") is not None:
            lines.append(f"- `{key}` (mesh change {100 * o['mesh_change']:.3f} %): " + ", ".join(
                f"{s} gap {100 * g:.2f} % -> {o['per_scenario'][s]}"
                for s, g in o["relative_gap"].items()))
    lines.append("")
    lm = J("local_mesh_study.json") or {}
    lines += ["## Local solder discretisation (declared policy)", "",
              f"Policy: `research/final_closure/local_mesh_policy.json` with amendments "
              f"{', '.join(str(a) for a in lm.get('amendments_applied', [])) or 'none'}; "
              f"pass {lm.get('pass', '?')}; first increment {lm.get('initial_increment_s')} s"
              f"{', load change as its own 3 s step' if lm.get('split_steps') else ''}; "
              f"extraction: {lm.get('extraction', 'time-keyed')}. Wording: "
              f"**{local_wording(lm)}**.", ""]
    for k, c in (lm.get("cases") or {}).items():
        u = c.get("U")
        lines.append(f"- {k}: {c.get('status')} ({c.get('rule', c.get('note', ''))}); "
                     f"production {c.get('production_level')} = "
                     + (f"{c['production_value']:.4e}" if c.get("production_value") else "n/a")
                     + (f"; U = {100 * u:.2f} % (mesh {100 * c['U_mesh']:.2f} + time "
                        f"{100 * c['U_time']:.2f} + cycles {100 * c['U_cyc']:.2f})"
                        if u is not None else "; U not quantified"))
    acc = lm.get("acceptance") or {}
    if acc:
        lines.append(f"- acceptance ({acc.get('rule')}): **{acc.get('pass')}**")
    lines.append("")
    lines += ["## Defects found in this closure", "",
              "- **DEFECT #65** (local solder post-processing): the validated .dat parser keyed "
              "output by its 7-significant-digit printed time and averaged blocks sharing a "
              "key; sub-millisecond increments at a load step biased the LAST cycle (up to "
              "-17 %). Found by the acceptance test of policy amendment 1; fixed by block-order "
              "extraction (scripts/final_closure_local_extract.py), which reproduces the "
              "published control to all ten printed digits and leaves every earlier production "
              "value unchanged (local_mesh_policy.json amendment 3).",
              "- **DEFECT #66** (Z2 out-of-cell construction), RESOLVED IN THE BASELINE: the "
              "earlier encapsulated model filled the PCB opening up to the board sidewall, "
              "bonding the backside converter to the board although the stack specifies a "
              "1.0 mm clearance. The production geometry now voids that ring "
              "(F1_clearance); the sidewall-filled construction survives only as the class-B "
              "variant f1_sidewall_filled.",
              "- **DEFECT #67** (BGA-fed control only): in Z2_BGA_FED_CONTROL the 48 V enters at "
              "the land-side RDL but the intra-VR model places VIN on the high-side RDL, so a "
              "~1.3 mm HV vertical traverse is not modelled. Z1 and the direct-fed Z2 take 48 V "
              "at the high-side RDL, where the model places it.",
              "- **DEFECT #68** (E-T coupling), FIXED IN EVERY CASE: the converter devices "
              "deposit their loss only inside the 49 cell footprints, but the loss model was "
              "fed the node mean of the WHOLE converter tiers, encapsulant included -- 7.8 K "
              "below the in-cell mean for the direct-fed Z2 and 1.2 K above it for Z1 at HV-S0 "
              "(found on the first corrected-lineage results). Every ledger temperature is now "
              "the mean over the region its terms deposit in, each device term at its own "
              "tier's in-cell temperature (final_closure_physical_etm.temperature_regions), "
              "and every case was re-run. The pre-fix HV-S0 cases and the diagnostic are in "
              "research/final_closure/superseded_pre_tile_temperature/.",
              "- **DEFECT #69** (solver harness), FIXED: the production local-solder runner "
              "accepted whatever a .dat held. When the per-user thread limit of the shared host "
              "was reached, CalculiX died mid-run; a control solve cut off at 1800.5 s of 2400 s "
              "returned d_eps = 2.695e-3 against its published 6.513e-3 (the control check "
              "stopped that run), and one production solve returned no response. A local solve "
              "is now accepted only if its last block sits at the schedule end, stale outputs "
              "are removed before every solve, and a solid-solder joint without a response "
              "stops the run. Every class-B and local solve that overlapped the exhaustion "
              "window was discarded and re-run. The two r31 ladder cases had one intermediate "
              "E-T iterate (it2) in it; their reported state comes from later solves, and the "
              "iterate changes contract geometrically through it (" + _r31_contraction() + ").",
              "- **Superseded primary Z2**: the earlier primary Z2 was BGA-fed (48 V through "
              "peripheral package balls and a package 48 V RDL), had no explicit VR attach and "
              "was sidewall-filled. Its case files not re-run here are kept in "
              "research/final_closure/superseded_bga_fed_z2/ for provenance only.", ""]
    cb = J("classB_resolution.json") or {}
    sm = cb.get("summary") or {}
    lines += ["## Class-B resolution", "",
              f"{sm.get('n_gates', 0)} open Class-B gates: subtypes {sm.get('subtypes')}; "
              f"B1 resolved {sm.get('b1_resolved')} / {sm.get('b1_total')}. Orderings that "
              f"move under a sensitivity: {', '.join(sm.get('orderings_that_move') or []) or 'none'}. "
              "Full table: `research/final_closure/classB_resolution.csv`.", ""]
    for g in cb.get("gates", []):
        lines.append(f"- `{g['gate']}` ({g['new_subtype']}): {g['final_status']}")
    lines.append("")
    lines += attach_density_lines(cb)
    ready, why = paper_ready(audit_pass, manuscript_on_lineage, mesh_ok,
                             all(f["et_converged"] for f in final),
                             all(L["converged"] for L in pn.get("loop", {}).values()),
                             cb, lm, final=final)
    lines += ["## Decision", "",
              f"**{'PAPER_READY' if ready else 'PAPER_NOT_READY'}** -- "
              + ("every generator-checkable criterion of the readiness rule holds (direct-fed "
                 "primary Z2, clearance and attach in the nominal mesh, no package 48 V term in "
                 "the Z2 ledger, crossover regenerated from the current cases, all B1 resolved "
                 "including the attach "
                 "density with its real-lattice study, explicit thermal RVE and mechanical "
                 "bounds, package-internal and platform-inclusive loss ordered separately, "
                 "active scope on the direct-fed Z2, E-T and conservation, mesh, local U, "
                 "provenance, manuscript on the lineage). The remaining criteria -- slides "
                 "match artifacts, tests pass on the exact final SHA -- are checked by the "
                 "test suite, which is run on the final pushed commit."
                 if ready else "not ready: " + "; ".join(why)), ""]
    (D / "FINAL_PAPER_DECISION.md").write_text("\n".join(lines))


def attach_density_lines(cb):
    """geom.vr_attach_density in the decision report: the two published lattices, the
    checks, and what the density does to the HV-S0 orderings and to R*."""
    st = J("vr_attach_density_study.json") or {}
    if not st:
        return ["## Attachment density", "", "no attach-density study", ""]
    out = ["## Attachment density (`geom.vr_attach_density`)", "",
           f"Allocation: {st['allocation_rule']}; legal site: {st['edge_rule']}. "
           "Production material and 30 um height held in both published cases.", ""]
    for name in ("dense", "sparse"):
        c = st["cases"][name]
        e = c["electrical"]
        out.append(f"- {name} ({c['source']}, {c['source_class']}): {c['d_um']:g} um at "
                   f"{c['pitch_um']:g} um pitch, {c['n_per_axis']} x {c['n_per_axis']} sites, "
                   f"{c['n_vdd']} VDD + {c['n_gnd']} GND per cell, metal "
                   f"{100 * c['area_fraction']:.2f} %; bump {1e3 * e['R_bump_ohm']:.3f} mOhm "
                   f"(constriction {100 * e['constriction_fraction']:.1f} %), attach loss "
                   f"{e['P_attach_total_w']:.4f} W at the production state; per-bump current "
                   f"{1e3 * e['VDD']['I_per_bump_A']:.2f} mA (output only); k_z "
                   f"{c['k_z_W_mK']:.2f}, k_xy {c['k_xy_W_mK']:.3f} W/mK (explicit AEDT unit "
                   f"cell: {100 * c.get('rve_kz_error', float('nan')):+.2f} / "
                   f"{100 * c.get('rve_kxy_error', float('nan')):+.2f} %); mechanics BOUNDED "
                   f"(E {c['mech_bound_A']['E_MPa'] / 1e3:.1f} to "
                   f"{c['mech_bound_B']['E_MPa'] / 1e3:.1f} GPa)")
    es = st.get("equal_sharing_assessment") or {}
    pen = (es.get("density_penalty_vs_dense") or {}).get("sparse") or {}
    if pen:
        out.append(f"- equal sharing: {es['verdict']}; dense-to-sparse penalty "
                   f"{pen['block_w']:.3f} W (ledger model) vs {pen['network_w']:.3f} W "
                   "(coupled network)")
    x = (cb.get("attach_density_crossover") or {}).get("crossover") or {}
    lc = x.get("P_loss_package_internal_w") or {}
    if lc:
        out.append(f"- package-internal loss vs density (ENGINEERING_SENSITIVITY sweep): "
                   f"{lc.get('status')}"
                   + (f"; crossover metal fraction {100 * lc['f_star']:.1f} % (15 um pillars "
                      f"at {lc['pitch_star_um_d15']:.1f} um pitch), "
                      f"{100 * (lc.get('f_star_network_penalty') or float('nan')):.1f} % with "
                      "the network penalty" if lc.get("f_star") else ""))
    ad = ((((J("direct_feed_crossover.json") or {}).get("scenarios") or {}).get("HV_S0") or {})
          .get("attach_density_R_star") or {})
    if ad.get("sparse"):
        out.append(f"- platform requirement at HV-S0: R* = "
                   f"{ad['dense']['R_star_mohm']:.3f} mOhm (dense) and "
                   f"{ad['sparse']['R_star_mohm']:.3f} mOhm (sparse)")
    ld = st.get("local_level_decision") or {}
    for name, c in (ld.get("cases") or {}).items():
        out.append(f"- local level, {name}: {c.get('decision')}")
    return out + [""]


def local_wording(lm):
    """The ONLY wording the paper may use for the local response, from the policy."""
    pol = json.loads((D / "local_mesh_policy.json").read_text())
    cases = [f"{a}_{s}" for a, s in local_cases(pol)]
    st = [((lm.get("cases") or {}).get(k) or {}).get("status") for k in cases]
    return pol["wording"]["converged" if st and all(x == "converged" for x in st)
                          else "bounded_or_unresolved"]


def local_cases(pol):
    """The local cases of the CURRENT pass: amendment 4 re-declares them for the corrected
    lineage; without it, the original declaration."""
    a4 = [a for a in pol.get("amendments", []) if a.get("id") == 4]
    return [tuple(c) for c in (a4[0]["cases"] if a4 else pol["cases"])]


#: the sentence the pre-direct-feed scope used for Z2 (FINAL_PAPER_SCOPE.md at 4cf83c7)
SUPERSEDED_Z2_SCOPE = "48 V reaches them laterally through the package RDL"


def attach_density_missing(gates):
    """geom.vr_attach_density (B1) needs its own evidence, not only a resolved row: the
    real-lattice study of both published endpoints and the explicit thermal RVE of both."""
    why = []
    if "geom.vr_attach_density" not in {g.get("gate") for g in gates}:
        why.append("the attach-density B1 gate is absent from the Class-B record")
    st = (J("vr_attach_density_study.json") or {}).get("cases") or {}
    for c in ("dense", "sparse"):
        r = st.get(c) or {}
        need = ("n_vdd", "n_gnd", "area_fraction", "k_z_W_mK", "k_xy_W_mK", "mech_bound_A",
                "mech_bound_B", "electrical")
        if any(k not in r for k in need):
            why.append(f"attach-density study lacks the {c} lattice/electrical/thermal/"
                       "mechanical evidence")
    rve = J("reference_attach_rve.json") or {}
    for k in ("vr_attach_dense_kz", "vr_attach_dense_kxy", "vr_attach_sparse_kz",
              "vr_attach_sparse_kxy"):
        if not (rve.get(k) or {}).get("reference_value"):
            why.append(f"no explicit attach RVE for {k}")
    return why


def loss_boundary_missing():
    """No generic 'loss' ordering: package-internal and platform-inclusive are separate."""
    od = (J("ordering.json") or {}).get("orderings") or {}
    why = []
    if "P_loss_w" in od:
        why.append("ordering.json still carries a generic loss ordering")
    if "P_loss_package_internal_w" not in od or "P_loss_platform_inclusive_w" not in od:
        why.append("package-internal and platform-inclusive loss are not both ordered")
    elif od["P_loss_platform_inclusive_w"].get("favoured"):
        why.append("a single platform-inclusive winner is stored although R_feed is unknown")
    return why


def crossover_stale():
    """'Direct-feed crossover regenerated': the internal losses the crossover is built from
    must be the CURRENT production cases', so a changed Z1 or Z2 case without a rerun of
    final_closure_direct_feed.py is caught here."""
    import final_closure_physical_etm as E
    cx = (J("direct_feed_crossover.json") or {}).get("scenarios") or {}
    why = []
    for s, c in cx.items():
        for a, k in (("Z1", "P_Z1_internal_w"), ("Z2", "P_Z2_internal_w")):
            f = E.case_path(a, s)
            if not f.exists():
                continue
            cur = json.loads(f.read_text())["P_loss_w"]
            if not isinstance(c.get(k), (int, float)) or abs(c[k] - cur) > 1e-9 * abs(cur):
                why.append(f"direct-feed crossover not regenerated for the current {a} {s} "
                           "case")
    return why


def active_scope_stale():
    f = D / "FINAL_PAPER_SCOPE.md"
    t = f.read_text() if f.exists() else ""
    why = []
    if "Z2_DIRECT_FEED" not in t and "direct-fed" not in t:
        why.append("the active paper scope does not define the direct-fed Z2")
    if SUPERSEDED_Z2_SCOPE in t:
        why.append("the active paper scope still describes the BGA-fed Z2 as the primary")
    return why


def paper_ready(audit_pass, manuscript_on_lineage, mesh_ok, et_ok, loops_ok, classb, lm,
                final=None):
    """PAPER_READY and, if not, every reason (final-closure readiness rule): the primary Z2
    is the direct-fed construction with the clearance and the attach in the nominal mesh
    and no package 48 V term; the direct-feed uncertainty is bounded by the crossover; every
    B1 gate resolved; E-T converged; conservation; mesh; the local study accepted with a
    quantified U for every declared case; tool provenance consistent; manuscript on the
    lineage."""
    why = []
    z2 = [f for f in (final or []) if f["arch"] == "Z2"]
    if not z2 or any(f.get("architecture_variant") != "Z2_DIRECT_FEED" for f in z2):
        why.append("primary Z2 is not the direct-fed construction in every case")
    if any(f.get("forbidden_terms") for f in z2):
        why.append("a package 48 V term in the primary Z2 ledger")
    pg = {r["id"]: r["status"] for r in (J("../phase0nw/physical_gates.json") or {}).get(
        "gates", [])} if (D.parent / "phase0nw" / "physical_gates.json").exists() else {}
    for gid, what in (("geom.sidewall_clearance_baseline", "1.0 mm sidewall clearance"),
                      ("geom.vr_attach_explicit", "explicit VR attach")):
        if pg.get(gid) != "IMPLEMENTED":
            why.append(f"{what} not measured in the nominal mesh ({gid})")
    cx = J("direct_feed_crossover.json") or {}
    s0x = (cx.get("scenarios") or {}).get("HV_S0") or {}
    if s0x.get("R_star_mohm") is None or not s0x.get("sweep"):
        why.append("direct-feed crossover not computed (direct-feed uncertainty unbounded)")
    try:
        import final_closure_provenance as _P
        tp = json.loads((D / "tool_provenance.json").read_text())["tools"]
        if _P.lane_violations(tp):
            why.append("tool provenance inconsistent")
    except FileNotFoundError:
        why.append("no tool provenance")
    if not audit_pass:
        why.append("conservation audit failed")
    if not manuscript_on_lineage:
        why.append("manuscript not on the physical lineage")
    if not mesh_ok:
        why.append("global mesh neither converged nor bounded")
    if not et_ok:
        why.append("an E-T fixed point did not converge")
    if not loops_ok:
        why.append("a package network did not converge")
    gates = (classb or {}).get("gates") or []
    b1 = [g for g in gates if g.get("new_subtype") == "B1"]
    if not gates:
        why.append("no Class-B resolution record")
    for g in b1:
        if not g.get("resolved"):
            why.append(f"B1 gate `{g['gate']}` unresolved")
    why += attach_density_missing(gates)
    why += loss_boundary_missing()
    why += crossover_stale()
    why += active_scope_stale()
    pol = json.loads((D / "local_mesh_policy.json").read_text())
    if not (lm or {}).get("acceptance", {}).get("pass"):
        why.append("local solder study not accepted")
    for a, s in local_cases(pol):
        c = ((lm or {}).get("cases") or {}).get(f"{a}_{s}") or {}
        if c.get("U") is None or not c.get("production_value"):
            why.append(f"local response {a} {s} has no quantified uncertainty")
    return (not why), why


if __name__ == "__main__":
    main()
