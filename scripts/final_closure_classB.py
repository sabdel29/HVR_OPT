"""Resolve every open Class-B gate: classify, then run or bound it, then judge the ordering.

Subtypes (declared in the brief, applied here per gate):
  B1  ORDERING-RELEVANT  could move a Z1/Z2 ordering; must be run or quantitatively
                         bounded before PAPER_READY
  B2  MAGNITUDE-ONLY     moves magnitudes but provably not an ordering; proved or bounded
  B3  RECLASSIFY -> C    a qualification quantity that limits claims, not comparisons

A run-based gate is judged on the sensitivity cases written by final_closure_sensitivity.py
(production mesh, HV-S0): for every observable the variant's Z1/Z2 verdict is formed with
THE SAME rule as ordering.json (gap > 2 x the measured discretisation uncertainty) and
compared with the production verdict. A gate is RESOLVED when every case it needs exists
and has a verdict; whether the ordering survives is reported, never assumed. A declared
B2 gate whose runs DO move an ordering is promoted to B1 automatically.

Writes research/final_closure/classB_resolution.{csv,json}.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
D = R / "research" / "final_closure"
SENS = D / "sensitivity"
sys.path.insert(0, str(R / "scripts"))

OBS = {"P_loss_w": "loss", "T_max_C": "peak temperature",
       "die_warpage_pv_um": "die warpage", "du_c_um": "joint displacement driver",
       "d_eps_in_per_cycle": "local inelastic response"}
GLOBAL = ("P_loss_w", "T_max_C", "die_warpage_pv_um", "du_c_um", "d_eps_in_per_cycle")
THERMAL = ("P_loss_w", "T_max_C")
MECH = ("die_warpage_pv_um", "du_c_um", "d_eps_in_per_cycle")
SCEN = "HV_S0"
H01 = ["board_h1", "board_h0_h1grid"]
#: variants that exist only for Z2 (no PCB opening, no backside converter in Z1): Z1 keeps
#: its production values
Z2_ONLY = ("z2_cooled", "f1_clearance")
CONV = ["conv_k_tenth", "conv_E80_a4", "conv_E80_a10", "conv_E160_a4", "conv_E160_a10"]
WAVE = ("named 48 V scenarios HV-S0 / HV-S1 / HV-S2 (rms_currents definitions): each "
        "scenario solved through the full lineage")

#: gate -> (subtype, observables, range / source, method, cases, rationale)
GATES = {
    "board.h1_meshed": ("B1", GLOBAL, "PCB-H1: the 18-layer schedule as five depth blocks "
                        "(pcb_h1.py), against H0 on the same z grid", "runs", H01,
                        "the board is the bottom heat path and the mechanical support"),
    "board.h1_thermal_validated": ("B1", THERMAL, "H1 vs H0 on the H1 z grid", "runs", H01,
                                   "thermal half of the H0 model-form check"),
    "therm.h0_h1_compared": ("B1", THERMAL, "H1 vs H0 on the H1 z grid", "runs", H01,
                             "thermal half of the H0 model-form check"),
    "board.eta_sensitivity_run": ("B1", GLOBAL, "copper coverage eta 0.25 / 0.50 / 0.75 "
                                  "(config eta_sensitivity)", "runs",
                                  ["board_eta025", "board_eta075"],
                                  "board k_xy spans 34-98 W/mK and E 23-38 GPa over eta"),
    "board.t_only_comparison_run": ("B1", THERMAL, "PCB 2.4 vs 3.2 mm, one material dict",
                                    "runs", ["board_t3p2"], "board thickness, thermal"),
    "mech.t_only_mechanical": ("B1", MECH, "PCB 2.4 vs 3.2 mm, one material dict", "runs",
                               ["board_t3p2"], "board thickness, mechanical"),
    "tsv.density_sensitivity_run": ("B1", GLOBAL, "TSV sizing study: 64 / 729 / 1444 vias "
                                    "per cell, in the FE substrate AND the ledger", "runs",
                                    ["tsv_min", "tsv_mid"],
                                    "the adopted field is the maximum-density end"),
    "mech.f1_f2_bracket_run": ("B1", GLOBAL, "out-of-cell converter volume encapsulated "
                               "(F1, production: fills the PCB opening to the sidewall) vs "
                               "void (F2), and F1 with the specified 1 mm sidewall clearance "
                               "open (DEFECT #66)", "runs", ["f2_void", "f1_clearance"],
                               "the fill carries heat and load between the cells"),
    "therm.z2_cooled": ("B1", GLOBAL, "bounding Z2-COOLED: a top-type cold plate on the Z2 "
                        "converter underside; Z1 unchanged", "runs", ["z2_cooled"],
                        "an extra Z2 heat path could move any thermal ordering"),
    "mat.gan_bounded": ("B1", GLOBAL, "GaN tiers at half the Si carrier conductivity "
                        "(stress bound on the unresolved epi)", "runs", ["gan_k_half"],
                        "the device tiers sit in the converter heat path"),
    "mat.mlcc_bounded": ("B1", GLOBAL, "converter medium k/10, and the card's own E 80-160 "
                         "GPa x CTE 4-10 ppm/K corners", "runs", CONV,
                         "flying-cap tier on a generic PROVISIONAL card"),
    "mat.inductor_tier_bounded": ("B1", GLOBAL, "converter medium k/10, and the card's own "
                                  "E 80-160 GPa x CTE 4-10 ppm/K corners", "runs", CONV,
                                  "inductor/Cout tier on the same generic card"),
    "elec.contact_resistance_bounded": ("B1", ("P_loss_w",), "rho_c 1e-6 / 1e-5 / 1e-4 "
                                        "ohm mm^2 on the package 48 V RDL (package_network "
                                        "sensitivity)", "network", ["rho_c"],
                                        "unsourced contact resistance in the 48 V path"),
    "elec.rdl10um_electrical_model": ("B1", ("P_loss_w",), "package 48 V RDL t_Cu 2 / 5 / 10 "
                                      "um x occupancy 0.3 / 0.8 (package_network "
                                      "sensitivity)", "network", ["t_cu", "occupancy"],
                                      "the 10 um tier's sheet resistance is undefined"),
    "elec.hv_input_waveform": ("B1", tuple(OBS), WAVE, "scenarios", [],
                               "the 48 V waveform is not derivable from the pinned model"),
    "elec.hv_waveform_determination": ("B1", tuple(OBS), WAVE, "scenarios", [],
                                       "determined unresolvable from available sources"),
    "elec.z1_hv_rms_current": ("B1", tuple(OBS), WAVE, "scenarios", [],
                               "the 48 V RMS follows the scenario"),
    "elec.bga_rms_current": ("B1", tuple(OBS), WAVE, "scenarios", [],
                             "the BGA RMS follows the scenario"),
    "elec.individual_branch_waveforms": ("B2", ("P_loss_w",), "converter-internal branch "
                                         "RMS: identical converter model in both "
                                         "architectures", "common_mode", [],
                                         "the converter terms depend on T_conv only"),
    "elec.pad_count_criterion": ("B2", GLOBAL, "pad sweep end: the voltage-drop floor, 4 "
                                 "pads per rail per cell (vs 2040)", "runs", ["pad_drop"],
                                 "same pad field and current in both architectures"),
    "elec.pad_loss_closed": ("B2", GLOBAL, "pad sweep end: the voltage-drop floor, 4 pads "
                             "per rail per cell (vs 2040)", "runs", ["pad_drop"],
                             "same pad field and current in both architectures"),
}


def J(p):
    return json.loads(Path(p).read_text()) if Path(p).exists() else None


def _vals(case):
    if case is None or "mechanics" not in case:
        return None
    m, c = case["mechanics"], case["mechanics"]["joint_search"]["critical"]
    return {"P_loss_w": case["P_loss_w"], "T_max_C": case["thermal"]["T_max_C"],
            "die_warpage_pv_um": m["die_warpage_pv_um"], "du_c_um": c["du_um"],
            "T_joint_C": c["T_C"], "d_eps_in_per_cycle": (case.get("local") or {}).get(
                "d_peeq_per_cycle")}


def _verdict(a, b, u):
    if a is None or b is None:
        return "not rankable", None
    gap = abs(a - b) / max(abs(a), abs(b))
    if u is None:
        return "unresolved", gap
    return ("Z1 lower" if a < b else "Z2 lower") if gap > 2 * u else "unresolved", gap


def _uncertainty(od):
    return {k: (o.get("uncertainty_rel") or {}).get(SCEN) for k, o in od.items()}


def base_case(arch):
    import final_closure_physical_etm as E
    return J(E.case_path(arch, SCEN))


def judge_runs(cases, observables, od, unc):
    """Variant verdicts against the production verdicts, per observable."""
    import final_closure_physical_etm as E                         # noqa: F401
    base = {a: _vals(base_case(a)) for a in ("Z1", "Z2")}
    lm = (J(D / "local_mesh_study.json") or {}).get("cases", {})
    for a in base:      # production local response at the variants' level and settings
        if base[a] is not None:
            base[a]["d_eps_in_per_cycle"] = (((lm.get(f"{a}_{SCEN}") or {}).get("levels")
                                              or {}).get("L0") or {}).get("d_peeq_per_cycle")
    rows, missing = [], []
    for v in cases:
        var = {}
        for a in ("Z1", "Z2"):
            f = SENS / f"etm_{a}_{SCEN}__{v}.json"
            c = J(f)
            if c is None and v in Z2_ONLY and a == "Z1":
                var[a] = base[a]                         # Z1 is unchanged by definition
                continue
            var[a] = _vals(c)
            if var[a] is None:
                missing.append(f.name)
        for k in observables:
            if any(var[a] is None for a in var):
                continue
            va, vb = var["Z1"].get(k), var["Z2"].get(k)
            if k == "d_eps_in_per_cycle" and (va is None or vb is None):
                continue
            u = unc.get(k)
            verdict, gap = _verdict(va, vb, u)
            prod = (od.get(k) or {}).get("per_scenario", {}).get(SCEN)
            ch = {a: ((var[a][k] - base[a][k]) / base[a][k]
                      if base[a] and base[a].get(k) else None) for a in ("Z1", "Z2")}
            rows.append({"case": v, "observable": k, "Z1": va, "Z2": vb,
                         "change_rel": ch, "gap_rel": gap, "uncertainty_rel": u,
                         "verdict": verdict, "production_verdict": prod,
                         "robust": verdict == prod})
    return rows, missing


def h1_vs_control(observables):
    """PCB-H1 against the H0 card on the SAME five-block z grid: the material
    representation alone. (Against production, H1 also differs by its z resolution, and in
    Z2 the block boundaries re-slice the converter tiers that share the board's z range.)"""
    out = []
    for k in observables:
        ch = {}
        for a in ("Z1", "Z2"):
            h1, h0 = (_vals(J(SENS / f"etm_{a}_{SCEN}__{v}.json")) for v in H01)
            ch[a] = ((h1[k] - h0[k]) / h0[k]) if (h1 and h0 and h0.get(k)) else None
        if any(v is None for v in ch.values()):
            continue
        out.append({"case": "board_h1 vs board_h0_h1grid", "observable": k,
                    "change_rel": ch, "verdict": "material effect only",
                    "within_mesh_tolerance": all(abs(v) < 0.02 for v in ch.values()),
                    "robust": None})
    return out


def judge_network(params, od):
    """Package 48 V RDL loss over the package-network sensitivity rows, at HV-S0."""
    pn = J(D / "package_network.json")
    led = (J(D / "electrical_ledger.json") or {}).get("rows", [])
    fin = {(r["arch"], r["scenario"]): r for r in J(D / "final_results.json") or []}
    prod = {"rho_c_ohm_mm2": 1e-5, "t_cu_mm": 0.005, "occupancy": 0.3}
    key = {"rho_c": "rho_c_ohm_mm2", "t_cu": "t_cu_mm", "occupancy": "occupancy"}
    rows = []
    p_hv = {a: sum(r["P_w"] for r in led if r["arch"] == a and r["scenario"] == SCEN
                   and r["term"].startswith("P_pkg_RDL_HV")) for a in ("Z1", "Z2")}
    r0 = {a: pn["loop"][a]["r_loop_ohm"] for a in ("Z1", "Z2")}
    sens = [s for s in pn["sensitivity"] if s["terminal_mode"] == "VIN_PAD"]
    combos = sorted({tuple(s[key[p]] for p in params) for s in sens
                     if all(s[k] == prod[k] for k in prod if k not in [key[p] for p in params])})
    for combo in combos:
        sel = {s["arch"]: s for s in sens
               if tuple(s[key[p]] for p in params) == combo
               and all(s[k] == prod[k] for k in prod if k not in [key[p] for p in params])}
        if set(sel) != {"Z1", "Z2"}:
            continue
        dp = {a: p_hv[a] * (sel[a]["r_loop_ohm"] / r0[a] - 1.0) for a in ("Z1", "Z2")}
        loss = {a: fin[(a, SCEN)]["P_loss_w"] + dp[a] for a in ("Z1", "Z2")}
        u = (od.get("P_loss_w") or {}).get("uncertainty_rel", {}).get(SCEN)
        verdict, gap = _verdict(loss["Z1"], loss["Z2"], u)
        rows.append({"case": ", ".join(f"{p}={c:g}" for p, c in zip(params, combo)),
                     "observable": "P_loss_w", "Z1": loss["Z1"], "Z2": loss["Z2"],
                     "change_rel": {a: dp[a] / fin[(a, SCEN)]["P_loss_w"] for a in dp},
                     "delta_W": dp, "gap_rel": gap, "uncertainty_rel": u,
                     "verdict": verdict,
                     "production_verdict": (od.get("P_loss_w") or {}).get(
                         "per_scenario", {}).get(SCEN),
                     "robust": verdict == (od.get("P_loss_w") or {}).get(
                         "per_scenario", {}).get(SCEN),
                     "method": "first order: the 48 V RDL rows scale with the swept loop "
                               "resistance at the solved HV-S0 current; the thermal "
                               "feedback of a <= 2 W change is second order"})
    return rows


def judge_common_mode():
    """The converter terms are one architecture-independent model evaluated at each
    architecture's own converter temperature, so any common rescaling k of them (which is
    what an unknown branch waveform does) keeps the sign of their Z1 - Z2 difference."""
    led = (J(D / "electrical_ledger.json") or {}).get("rows", [])
    conv = ("P_conv_hs", "P_conv_ls", "P_conv_inductor_dcr", "P_conv_cap_esr",
            "P_intraVR_metal", "P_intraVR_vertical")
    tot = {a: sum(r["P_w"] for r in led if r["arch"] == a and r["scenario"] == SCEN)
           for a in ("Z1", "Z2")}
    c = {a: sum(r["P_w"] for r in led if r["arch"] == a and r["scenario"] == SCEN
                and r["term"] in conv) for a in ("Z1", "Z2")}
    d_conv, d_rest = c["Z1"] - c["Z2"], (tot["Z1"] - c["Z1"]) - (tot["Z2"] - c["Z2"])
    k_flip = (-d_rest / d_conv) if d_conv and (d_rest / d_conv) < 0 else None
    return [{"case": "common rescaling k of the converter terms", "observable": "P_loss_w",
             "converter_terms_W": c, "delta_converter_W": d_conv, "delta_rest_W": d_rest,
             "k_at_which_order_flips": k_flip,
             "verdict": ("Z2 lower for every k > %.3f" % k_flip) if k_flip else
             ("Z2 lower for every k > 0" if d_conv > 0 and d_rest >= 0 else "see deltas"),
             "robust": (k_flip is None and d_conv > 0 and d_rest >= 0)
             or (k_flip is not None and k_flip < 0.5),
             "method": "ledger rows at the converged HV-S0 temperatures: the converter "
                       "and intra-VR rows are the same functions of T_conv in Z1 and Z2"}]


def judge_scenarios(od, sc):
    rows = []
    for k, o in od.items():
        # scenario dependence is REPORTED per scenario, not a sensitivity moving an
        # ordering: robust is not applicable here
        rows.append({"case": "per scenario", "observable": k,
                     "per_scenario": o.get("per_scenario"),
                     "scenario_classes": {s: c["class"] for s, c in sc.items()},
                     "verdict": o.get("statement"),
                     "robust_across_scenarios": o.get("robust_across_scenarios"),
                     "robust": None})
    return rows


def main():
    oj = J(D / "ordering.json") or {}
    od, sc = oj.get("orderings", {}), oj.get("scenario_classes", {})
    unc = _uncertainty(od)
    out = []
    for gid, (sub, obs, rng, method, cases, why) in GATES.items():
        missing = []
        if method == "runs":
            rows, missing = judge_runs(cases, obs, od, unc)
            if cases == H01:
                rows += h1_vs_control(obs)
        elif method == "network":
            rows = judge_network(cases, od)
        elif method == "common_mode":
            rows = judge_common_mode()
        else:
            rows = judge_scenarios(od, sc)
        complete = (not missing) and bool(rows)
        moved = [r for r in rows if r.get("robust") is False]
        new_sub = sub
        if sub == "B2" and moved:
            new_sub = "B1"                           # the B2 assumption failed: promote
        if not complete:
            status = "PENDING -- " + (f"missing {', '.join(sorted(set(missing)))}"
                                      if missing else "no evidence rows")
        elif method == "scenarios":
            status = ("RESOLVED -- scenario-conditioned: every named scenario is solved and "
                      "each ordering is stated per scenario")
        elif not moved:
            status = ("RESOLVED -- ordering robust" if new_sub == "B1"
                      else "BOUNDED -- magnitude only")
        else:
            status = ("RESOLVED -- ordering changes in: " + "; ".join(
                f"{r['observable']} under {r['case']} ({r.get('production_verdict')} -> "
                f"{r['verdict']})" for r in moved) + " -- the claim is narrowed accordingly")
        mx = max((abs(x) for r in rows for x in (r.get("change_rel") or {}).values()
                  if isinstance(x, (int, float))), default=None)
        gaps = [r["gap_rel"] for r in rows if isinstance(r.get("gap_rel"), (int, float))]
        out.append({"gate": gid, "old_class": "B", "new_subtype": new_sub,
                    "declared_subtype": sub, "observable": ", ".join(obs),
                    "range_source": rng, "rationale": why, "method": method,
                    "cases_run": cases, "max_change_rel": mx,
                    "architecture_gap_rel_min": min(gaps) if gaps else None,
                    "ordering_robust": complete and not moved, "final_status": status,
                    "resolved": complete,
                    "evidence_path": ("research/final_closure/sensitivity/" if method == "runs"
                                      else "research/final_closure/package_network.json"
                                      if method == "network" else
                                      "research/final_closure/electrical_ledger.json"
                                      if method == "common_mode" else
                                      "research/final_closure/ordering.json"),
                    "rows": rows})
    b1 = [g for g in out if g["new_subtype"] == "B1"]
    summary = {"n_gates": len(out),
               "subtypes": {s: sum(g["new_subtype"] == s for g in out) for s in ("B1", "B2", "B3")},
               "b1_resolved": sum(g["resolved"] for g in b1), "b1_total": len(b1),
               "all_b1_resolved": all(g["resolved"] for g in b1),
               "orderings_that_move": sorted({f"{r['observable']} under {r['case']}"
                                             for g in out for r in g["rows"]
                                             if r.get("robust") is False})}
    (D / "classB_resolution.json").write_text(json.dumps(
        {"rule": "a B1 gate is resolved when every case it needs exists and carries a "
                 "verdict formed with the ordering.json rule; PAPER_READY requires every "
                 "B1 gate resolved", "summary": summary, "gates": out},
        indent=1, default=float))
    cols = ["gate", "old_class", "new_subtype", "observable", "range_source", "cases_run",
            "max_change_rel", "architecture_gap_rel_min", "ordering_robust", "final_status",
            "evidence_path"]
    with (D / "classB_resolution.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for g in out:
            w.writerow(dict(g, cases_run="; ".join(g["cases_run"])))
    print(json.dumps(summary, indent=1))
    for g in out:
        print(f"{g['gate']:36s} {g['new_subtype']} {g['final_status'][:110]}")


if __name__ == "__main__":
    main()
