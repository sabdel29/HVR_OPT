"""Coarse validation driver for the thermal-model corrections of the TCPMT revision.

    python tcpmt_thermal_fix_validate.py TREE LABEL ARCH SCEN [rXZ] [TOGGLE ...]

Runs the E-T fixed point (no mechanics) of one case from the code in TREE (a checkout of
this repository: the corrected tree or an unmodified copy for the "before" numbers) at
h_xy = 1.1 mm and the nested refinement rXZ (default r11, the coarse level), and writes
the case JSON and a summary.json under $HVR_VALIDATE/LABEL/ (default
~/claude_scratch/hvr_work/thermal_fix_validate/LABEL). Nothing under research/ is touched.

The die statistics (maximum and node mean over the processor-die layer) are computed here
from the solved nodal field, so the summary carries them for an unmodified tree too.

TOGGLEs, applied in order before the run:
    NAME                 a final_closure_sensitivity.VARIANTS entry (its apply())
    rv:FUNC              a tcpmt_review_variants function, called with no argument
    set:MODULE.ATTR=VAL  a module attribute (str/int/float/bool by the current type)
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path


def main(argv):
    tree, label, arch, scen = argv[1:5]
    rest = list(argv[5:])
    refine = (1, 1)
    if rest and len(rest[0]) == 3 and rest[0][0] == "r" and rest[0][1:].isdigit():
        refine = (int(rest[0][1]), int(rest[0][2]))
        rest = rest[1:]
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("FC_THREADS", "2")
    root = Path(os.environ.get("HVR_VALIDATE", Path.home() / "claude_scratch" / "hvr_work"
                               / "thermal_fix_validate"))
    out = root / label
    out.mkdir(parents=True, exist_ok=True)
    os.environ["FC_WORKDIR"] = str(root / "work" / label)
    os.environ["HVR_SCRATCH"] = str(root / "work" / f"{label}_scratch")
    sys.path.insert(0, str(Path(tree) / "scripts"))
    import numpy as np
    import final_closure_physical_etm as E
    import final_closure_sensitivity as S
    import final_closure_ledger as FL

    E.OUT = out
    E.WD = root / "work" / label
    die = {}
    orig = E.solve_thermal

    def solve_thermal(m, mats, st, deposits, wd, tiles, *a, **k):
        th = orig(m, mats, st, deposits, wd, tiles, *a, **k)
        import production_et as PE
        ids = PE._layer_elems(m, FL.LAYERS[arch]["die"])
        nodes = np.unique(m.elems[ids - 1].ravel())
        t = th["T_node"][nodes - 1]
        die.update({"die_T_max_C_driver": float(np.nanmax(t)),
                    "die_T_mean_C_driver": float(np.nanmean(t))})
        th.update(die)
        return th

    E.solve_thermal = solve_thermal
    applied = []
    for tg in rest:
        if tg.startswith("rv:"):
            import tcpmt_review_variants as RV
            applied.append({tg: getattr(RV, tg[3:])()})
        elif tg.startswith("set:"):
            lhs, val = tg[4:].split("=", 1)
            mod, attr = lhs.rsplit(".", 1)
            __import__(mod)
            cur = getattr(sys.modules[mod], attr)
            setattr(sys.modules[mod], attr,
                    (val == "True") if isinstance(cur, bool) else type(cur)(val))
            applied.append(tg)
        else:
            applied.append({tg: S.VARIANTS[tg]["apply"]()})
    t0 = time.time()
    r = E.run_case(arch, scen, 1.1, do_mech=False, refine=refine, solver="NONE")
    c = json.loads(Path(r["file"]).read_text())
    th, h = c["thermal"], c["et_history"][-1]
    summ = {"label": label, "tree": str(tree), "arch": arch, "scen": scen,
            "refine": list(refine), "toggles": rest, "applied": applied,
            "wall_s": time.time() - t0, "P_loss_w": c["P_loss_w"], "T_max_C": th["T_max_C"],
            "die_T_max_C": th.get("die_T_max_C", die.get("die_T_max_C_driver")),
            "die_T_mean_C": th.get("die_T_mean_C", die.get("die_T_mean_C_driver")),
            **die, **{k: h.get(k) for k in ("T_die_mean_C", "T_hs_C", "T_ls_C", "T_ind_C",
                                             "T_caps_C", "T_conv_C")},
            "q_top_W": th["q_top_W"], "q_bot_W": th["q_bot_W"],
            "q_extra_W": th.get("q_extra_W"), "q_bottom_plate_W": th.get("q_bottom_plate_W"),
            "energy_residual_rel": th["energy_residual_rel"],
            "et_iters": len(c["et_history"]), "et_converged": c["et_converged"],
            "cooling": th.get("cooling"), "file": r["file"]}
    (out / "summary.json").write_text(json.dumps(summ, indent=1, default=float))
    print(json.dumps({k: v for k, v in summ.items() if k not in ("applied", "cooling")},
                     indent=1, default=float))
    return summ


#: the coarse validation set (label -> (tree, arch, toggles, what)); "base" = an unmodified
#: copy of the tree before the corrections, "new" = the corrected tree
RUNS = {
    "base_Z1_A": ("base", "Z1", [], "before: Z1 cooling A"),
    "legacy_Z1_A": ("new", "Z1", ["conv_k_legacy", "nu_legacy_table", "props_legacy_50C",
                                  "plate_caloric_legacy"],
                    "corrected tree, every superseded setting back on (must equal before)"),
    "iso_nu_Z1_A": ("new", "Z1", ["conv_k_legacy", "props_legacy_50C", "plate_caloric_legacy"],
                    "Nu fit only"),
    "iso_props_Z1_A": ("new", "Z1", ["conv_k_legacy", "nu_legacy_table", "plate_caloric_legacy"],
                       "bulk-mean water properties only"),
    "iso_caloric_Z1_A": ("new", "Z1", ["conv_k_legacy", "nu_legacy_table", "props_legacy_50C"],
                         "caloric correction only"),
    "iso_cards_Z1_A": ("new", "Z1", ["nu_legacy_table", "props_legacy_50C",
                                     "plate_caloric_legacy"], "derived converter cards only"),
    "new_Z1_A": ("new", "Z1", [], "after: Z1 cooling A, every correction"),
    "hotmap_Z1_A": ("new", "Z1", ["rv:v_die_hotmap"], "after, die hot-spot map"),
    "base_Z1_B": ("base", "Z1", ["z1_bottom_plate_tim"], "before: Z1 cooling B"),
    "new_Z1_B": ("new", "Z1", ["z1_bottom_plate_tim"], "after: Z1 cooling B (equal-rise plate)"),
    "new_Z1_B_fullflow": ("new", "Z1", ["z1_bottom_plate_tim_fullflow"],
                          "after, bottom plate at the legacy full flow"),
    "new_Z1_B_final": ("new", "Z1", ["z1_bottom_plate_tim"],
                       "after, committed code: sized-plate sink by direct substitution "
                       "(new_Z1_B used 0.5 under-relaxation)"),
    "base_Z2_B": ("base", "Z2", ["z2_cooled_tim"], "before: Z2 cooling B"),
    "new_Z2_B": ("new", "Z2", ["z2_cooled_tim"], "after: Z2 cooling B (equal-rise plate)"),
    "new_Z2_B_fullflow": ("new", "Z2", ["z2_cooled_tim_fullflow"],
                          "after, bottom plate at the legacy full flow"),
}
KEYS = ("P_loss_w", "T_max_C", "die_T_max_C", "die_T_mean_C", "T_hs_C", "T_ls_C", "T_ind_C",
        "T_caps_C", "q_top_W", "q_extra_W", "energy_residual_rel", "et_iters", "et_converged",
        "wall_s")


def collect(out_json):
    """The coarse before/after record from the run summaries under $HVR_VALIDATE."""
    root = Path(os.environ.get("HVR_VALIDATE", Path.home() / "claude_scratch" / "hvr_work"
                               / "thermal_fix_validate"))
    rec = {"what": "coarse validation (h_xy 1.1 mm, r11, E-T only, HV-S0) of the TCPMT "
                   "thermal-model corrections; 'base' = the tree before the corrections",
           "driver": "scripts/tcpmt_thermal_fix_validate.py", "runs": {}, "deltas": {}}
    for lab, (tree, arch, tg, what) in RUNS.items():
        f = root / lab / "summary.json"
        if not f.is_file():
            rec["runs"][lab] = {"missing": True, "what": what}
            continue
        s = json.loads(f.read_text())
        r = {k: s.get(k) for k in KEYS}
        r.update(what=what, tree=tree, arch=arch, toggles=tg)
        case = Path(s["file"])
        if case.is_file():
            th = json.loads(case.read_text())["thermal"]
            r["coolant_passes_last_et_iteration"] = th.get("fluid_iters")
        if s.get("cooling"):
            r["plates"] = [{k: p.get(k) for k in ("name", "m_dot_g_s", "Q_W", "dT_coolant_K",
                                                  "Re", "dp_kPa", "P_pump_hydraulic_W",
                                                  "h_film_W_m2K")}
                           for p in s["cooling"]["plates"]]
            r["P_pump_hydraulic_total_W"] = s["cooling"]["P_pump_hydraulic_total_W"]
        for a in s.get("applied") or []:
            if isinstance(a, dict) and "rv:v_die_hotmap" in a:
                r["hotmap"] = {k: v for k, v in a["rv:v_die_hotmap"].items() if k != "spec"}
        rec["runs"][lab] = r

    def d(a, b):
        ra, rb = rec["runs"].get(a, {}), rec["runs"].get(b, {})
        if ra.get("missing") or rb.get("missing") or not ra or not rb:
            return None
        return {k: rb[k] - ra[k] for k in ("P_loss_w", "T_max_C", "die_T_max_C",
                                           "die_T_mean_C", "T_hs_C", "T_ls_C")
                if isinstance(ra.get(k), (int, float)) and isinstance(rb.get(k), (int, float))}
    for lab in ("legacy_Z1_A", "iso_nu_Z1_A", "iso_props_Z1_A", "iso_caloric_Z1_A",
                "iso_cards_Z1_A", "new_Z1_A"):
        rec["deltas"][f"{lab} - base_Z1_A"] = d("base_Z1_A", lab)
    rec["deltas"]["hotmap_Z1_A - new_Z1_A"] = d("new_Z1_A", "hotmap_Z1_A")
    rec["deltas"]["new_Z1_B - base_Z1_B"] = d("base_Z1_B", "new_Z1_B")
    rec["deltas"]["new_Z1_B - new_Z1_B_fullflow"] = d("new_Z1_B_fullflow", "new_Z1_B")
    rec["deltas"]["new_Z1_B_final - new_Z1_B"] = d("new_Z1_B", "new_Z1_B_final")
    rec["deltas"]["new_Z2_B - base_Z2_B"] = d("base_Z2_B", "new_Z2_B")
    rec["deltas"]["new_Z2_B - new_Z2_B_fullflow"] = d("new_Z2_B_fullflow", "new_Z2_B")
    Path(out_json).write_text(json.dumps(rec, indent=1, default=float))
    return rec


#: TCPMT round 3, the manifold plate: label -> (tree, arch, toggles, what); "base" = the tree
#: before round 3 (31a846c), "new" = this tree (production: the 4-zone manifold)
MANIFOLD_RUNS = {
    "base_Z1_A": ("base", "Z1", [], "before round 3: single pass, per-face argsort sink"),
    "sp_Z1_A": ("new", "Z1", ["plate_single_pass"],
                "variant plate_single_pass (one coolant temperature per streamwise column)"),
    "mf_Z1_A": ("new", "Z1", [], "production: 4-zone manifold"),
    "sp_Z1_B": ("new", "Z1", ["plate_single_pass", "z1_bottom_plate_tim"],
                "cooling B, both plates single pass"),
    "mf_Z1_B3": ("new", "Z1", ["z1_bottom_plate_tim"],
                 "cooling B, both plates 4-zone manifolds (bottom flow: equal rise)"),
}


def collect_manifold(out_json, root=None):
    """The coarse manifold-vs-single-pass record from the run summaries under $HVR_VALIDATE."""
    root = Path(root or os.environ.get("HVR_VALIDATE", Path.home() / "claude_scratch"
                                       / "hvr_work" / "thermal_fix_validate"))
    rec = {"what": "coarse check (h_xy 1.1 mm, r11, E-T only, HV-S0) of the round-3 manifold "
                   "plate against the single pass, same code otherwise",
           "driver": "scripts/tcpmt_thermal_fix_validate.py TREE LABEL Z1 HV_S0 [TOGGLES]",
           "runs": {}, "deltas": {}}
    for lab, (tree, arch, tg, what) in MANIFOLD_RUNS.items():
        f = root / lab / "summary.json"
        if not f.is_file():
            rec["runs"][lab] = {"missing": True, "what": what}
            continue
        s = json.loads(f.read_text())
        r = {k: s.get(k) for k in KEYS}
        r.update(what=what, tree=tree, arch=arch, toggles=tg)
        case = Path(s["file"])
        if case.is_file():
            th = json.loads(case.read_text())["thermal"]
            r["coolant_passes_last_et_iteration"] = th.get("fluid_iters")
            r["coolant_residual_last_pass_K"] = (th.get("fluid_hist") or [{}])[-1].get(
                "max_dT_fluid_K")
        cool = s.get("cooling") or {}
        r["plate_model"] = cool.get("plate_model", "single_pass")
        r["plates"] = [{k: p.get(k) for k in ("name", "n_zones", "m_dot_g_s", "Q_W",
                                              "dT_coolant_K", "Re", "dp_fd_kPa",
                                              "dp_entrance_kPa", "dp_plenum_kPa",
                                              "dp_turns_kPa", "dp_header_kPa", "dp_kPa",
                                              "P_pump_hydraulic_W")}
                       for p in cool.get("plates", [])]
        r["P_pump_hydraulic_total_W"] = cool.get("P_pump_hydraulic_total_W")
        rec["runs"][lab] = r

    def d(a, b):
        ra, rb = rec["runs"].get(a, {}), rec["runs"].get(b, {})
        if ra.get("missing") or rb.get("missing") or not ra or not rb:
            return None
        return {k: rb[k] - ra[k] for k in ("P_loss_w", "T_max_C", "die_T_max_C",
                                           "die_T_mean_C", "T_hs_C", "T_ls_C")
                if isinstance(ra.get(k), (int, float)) and isinstance(rb.get(k), (int, float))}
    rec["deltas"]["sp_Z1_A - base_Z1_A (sink discretization only)"] = d("base_Z1_A", "sp_Z1_A")
    rec["deltas"]["mf_Z1_A - sp_Z1_A (manifold, cooling A)"] = d("sp_Z1_A", "mf_Z1_A")
    rec["deltas"]["mf_Z1_B3 - sp_Z1_B (manifold, cooling B)"] = d("sp_Z1_B", "mf_Z1_B3")
    Path(out_json).write_text(json.dumps(rec, indent=1, default=float))
    return rec


if __name__ == "__main__":
    if sys.argv[1:2] == ["collect_manifold"]:
        collect_manifold(sys.argv[2] if len(sys.argv) > 2 else
                         Path(os.environ.get("ETM_RESULTS_ROOT")
                              or Path(__file__).resolve().parents[1] / "research")
                         / "tcpmt_revision" / "manifold_validation.json")
    elif sys.argv[1:2] == ["collect"]:
        collect(sys.argv[2] if len(sys.argv) > 2 else
                Path(os.environ.get("ETM_RESULTS_ROOT")
                     or Path(__file__).resolve().parents[1] / "research") / "tcpmt_revision"
                / "thermal_fix_validation.json")
    else:
        main(sys.argv)
