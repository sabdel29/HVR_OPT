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
            final.append({
                "arch": arch, "scenario": scen,
                "P_loss_w": r["P_loss_w"], "I_48_avg_a": r["i_hv_avg_a"],
                "T_max_C": th["T_max_C"], "T_die_mean_C": h["T_die_mean_C"],
                "T_conv_mean_C": h["T_conv_C"],
                "die_warpage_pv_um": mm["die_warpage_pv_um"],
                "pkg_warpage_pv_um": mm.get("pkg_warpage_pv_um"),
                "critical_joint_xy_mm": [crit["x_mm"], crit["y_mm"]],
                "du_c_um": crit["du_um"], "T_joint_C": crit["T_C"],
                "d_eps_in_per_cycle": resp.get("d_peeq_per_cycle"),
                "inelastic_strain_range": resp.get("range_eq_inelastic"),
                "inelastic_work_MJ_m3": resp.get("inelastic_work_MJ_per_m3"),
                "local_stab_change_pct": resp.get("stab_change_pct"),
                "local_mesh_change_pct": lc.get("mesh_change_pct"),
                "T_joint_outside_norton_calibration": crit["T_C"] > NORTON_T_MAX_C,
                "T_joint_at_or_above_solder_solidus": crit["T_C"] >= SAC305_SOLIDUS_C,
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
    (D / "ordering.json").write_text(json.dumps(ordering(final, mc), indent=1, default=float))
    write_decision(final, audit_pass)
    for f in final:
        print("%s %s P=%.3f Tmax=%.2f warp=%.2f du=%.4f d_eps=%s" % (
            f["arch"], f["scenario"], f["P_loss_w"], f["T_max_C"],
            f["die_warpage_pv_um"], f["du_c_um"], f["d_eps_in_per_cycle"]))


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
        temps = {"conv": h["T_conv_C"], "bga": h["T_bga_C"], "sub": h["T_sub_C"],
                 "interface": h["T_interface_C"]}
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
    if prev.get("mesh_refine") == list(E.PRODUCTION_REFINE):
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
              "adiabatic": inside == 0, "mesh_refine": list(E.PRODUCTION_REFINE)}
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
    cases = {}
    for arch in ("Z1", "Z2"):
        lv = {}
        for r in set(E.INPLANE_SEQUENCE) | set(E.THROUGH_THICKNESS):
            f = E.case_path(arch, "HV_S0", 1.1, r)
            if f.exists():
                lv[tag(r)] = _q(json.loads(f.read_text()))
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
            "production_refine": list(P), "production_label": E.production_label(),
            "production_reason": reason,
            "method": "nested refinement of the h_xy = 1.1 mm grid: rN1 splits every in-plane "
                      "interval in N, r12 every layer's elements in two through the thickness; "
                      "every coarser node survives",
            "structural_solver_checks": checks, "cases": cases}


def ordering(final, mc):
    """Per-scenario Z1/Z2 ordering of each observable. A scenario's ordering is
    'unresolved' where the Z1/Z2 gap does not exceed twice the measured discretisation
    change (or declared bound) of that observable on the production mesh."""
    out = {}
    for key in ("P_loss_w", "T_max_C", "die_warpage_pv_um", "du_c_um", "d_eps_in_per_cycle"):
        mesh = None
        if key in MESH_KEYS and mc.get("cases"):
            mesh = max([(c["checks"][t].get(key) or 0.0) for c in mc["cases"].values()
                        for t in c["checks"]]
                       + [c.get("uncertainty_bound_rel", {}).get(key, 0.0)
                          for c in mc["cases"].values()])
        per, gaps = {}, {}
        for s in SCEN:
            try:
                b, va, vb = _order(final, key, s)
            except StopIteration:
                continue
            if b == "n/a":
                per[s] = "n/a"
                continue
            gap = abs(va - vb) / max(abs(va), abs(vb))
            gaps[s] = gap
            per[s] = ("unresolved" if (mesh is not None and gap <= 2 * mesh)
                      else f"{b} lower")
        resolved = [v for v in per.values() if v.endswith("lower")]
        fav = sorted({v.split()[0] for v in resolved})
        out[key] = {"per_scenario": per, "relative_gap": gaps, "mesh_change": mesh,
                    "favoured": fav,
                    "robust_across_scenarios": len(fav) == 1 and len(resolved) == len(per),
                    "favoured_where_resolved": fav[0] if len(fav) == 1 else None,
                    "unresolved": [s for s, v in per.items() if v == "unresolved"],
                    "hv_s0_within_mesh_uncertainty": per.get("HV_S0") == "unresolved"}
    return {"orderings": out,
            "rule": "a scenario's ordering is claimed only where the Z1/Z2 gap exceeds twice "
                    "the largest measured mesh change (or declared bound) of that observable"}


def _order(final, key, scen, lower_is_better=True):
    a = next(x for x in final if x["arch"] == "Z1" and x["scenario"] == scen)
    b = next(x for x in final if x["arch"] == "Z2" and x["scenario"] == scen)
    va, vb = a[key], b[key]
    if va is None or vb is None:
        return "n/a", va, vb
    better = "Z1" if (va < vb) == lower_is_better else "Z2"
    return better, va, vb


def write_decision(final, audit_pass):
    acc = J("accuracy_speed_matrix.json") or {"rows": []}
    pn = J("package_network.json") or {}
    lines = ["# Final paper decision", "",
             "Generated by `scripts/final_closure_results.py` from the run artifacts. "
             "Do not edit by hand.", ""]
    lines += ["## Electrical", "",
              f"Matched BGA construction: **{pn.get('matched_count')} balls per rail** for both "
              "architectures (smallest legal count passing the 1.5 A/ball ENGINEERING "
              "criterion at HV-S0 for both, verified on the resolved grid).", ""]
    if pn:
        for a, L in pn["loop"].items():
            lines.append(f"- {a}: R_supply {L['r_supply_ohm']*1e3:.4f} + R_return "
                         f"{L['r_return_ohm']*1e3:.4f} = R_loop {L['r_loop_ohm']*1e3:.4f} mOhm "
                         f"(20 C), converged on all five metrics: {L['converged']}")
        lines.append("")
    lines += ["| arch | scenario | P_loss (W) | T_max (C) | die warp (um) | du_c (um) | "
              "T_joint (C) | d_eps_in / cycle |", "|---|---|---|---|---|---|---|---|"]
    for f in final:
        de = f["d_eps_in_per_cycle"]
        lines.append(f"| {f['arch']} | {f['scenario']} | {f['P_loss_w']:.3f} | "
                     f"{f['T_max_C']:.2f} | {f['die_warpage_pv_um']:.2f} | {f['du_c_um']:.4f} | "
                     f"{f['T_joint_C']:.1f}{' (extrap.)' if f['T_joint_outside_norton_calibration'] else ''} | "
                     f"{'%.4e' % de if de else 'n/a'} |")
    lines += ["", "## Architecture ordering per scenario", "",
              "| scenario | loss | T_max | die warpage | joint driver | local response |",
              "|---|---|---|---|---|---|"]
    robust = {}
    for s in SCEN:
        cells = []
        for key in ("P_loss_w", "T_max_C", "die_warpage_pv_um", "du_c_um",
                    "d_eps_in_per_cycle"):
            try:
                b, va, vb = _order(final, key, s)
            except StopIteration:
                b, va, vb = "n/a", None, None
            robust.setdefault(key, set()).add(b)
            cells.append(f"{b} lower" if b != "n/a" else "n/a")
        lines.append(f"| {s} | " + " | ".join(cells) + " |")
    lines += ["", "## Robustness", ""]
    for key, s in robust.items():
        lines.append(f"- `{key}`: favoured architecture across scenarios = {sorted(s)} -> "
                     + ("ORDERING HOLDS IN EVERY SCENARIO" if len(s - {'n/a'}) == 1
                        else "ORDERING IS SCENARIO-DEPENDENT"))
    lines += ["", "## Accuracy and runtime (stage by stage)", "",
              "| stage | reference | error | speedup | status |", "|---|---|---|---|---|"]
    for r in acc["rows"]:
        e = r.get("error")
        sp = r.get("speedup")
        lines.append(f"| {r['stage']} | {r.get('reference_tool', '')} | "
                     f"{('%+.3f %%' % (100 * e)) if isinstance(e, float) else e} | "
                     f"{('%.1fx' % sp) if isinstance(sp, float) else ''} | {r.get('status', '')} |")
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
    ready = audit_pass and manuscript_on_lineage and mesh_ok and \
        all(f["et_converged"] for f in final) and \
        all(L["converged"] for L in pn.get("loop", {}).values())
    lines += ["## Decision", "",
              f"**{'PAPER_READY' if ready else 'PAPER_NOT_READY'}** -- "
              + ("the active manuscript must carry this lineage; the decision is re-evaluated "
                 "by the manuscript stale-number guard." if ready else
                 "a convergence or conservation check failed; see above."), ""]
    (D / "FINAL_PAPER_DECISION.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
