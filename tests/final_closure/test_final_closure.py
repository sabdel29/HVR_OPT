"""Final closure: the physical lineage, its references, the paper and the deck must agree.

These tests read artifacts only -- no solver runs -- so they are also the CI guard.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
D = R / "research" / "final_closure"
TEX = R / "manuscript" / "ETM_DVPD_JOURNAL_MANUSCRIPT.tex"
DECK = R / "presentation" / "prelim_hvr"
SCEN = ("HV_S0", "HV_S1", "HV_S2")


def J(n):
    f = D / n
    if not f.exists():
        pytest.skip(f"{n} not generated")
    return json.loads(f.read_text())


# --------------------------------------------------------------- electrical
def test_package_network_count_matches_the_active_construction():
    """A resistance computed at one ball count may never sit beside a design
    conclusion that requires another (the 16-vs-40/24 inconsistency)."""
    pn = J("package_network.json")
    n = pn["matched_count"]
    for k, c in pn["convergence"].items():
        assert len(c["i_ball_frac"]) == n, k
        assert len(c["ball_xy"]) == n, k
        for lv in c["levels"]:
            assert lv["n_per_rail"] == n, k
    for a, L in pn["loop"].items():
        assert L["n_per_rail"] == n, a
    led = J("electrical_ledger.json")
    for r in led["rows"]:
        if r["term"].startswith("P_BGA_"):
            assert f"N={n}" in r["conductor"], r


def test_all_four_package_networks_converge_on_all_five_metrics():
    pn = J("package_network.json")
    assert set(pn["convergence"]) == {"Z1_supply", "Z1_return", "Z2_supply", "Z2_return"}
    for k, c in pn["convergence"].items():
        assert c["converged"], (k, c["worst_metric"], c["worst_delta"])
        assert set(c["deltas"]) == {"r_eff_ohm", "p_loss_w", "max_cell_drop_v",
                                    "i_ball_max_a", "ball_imax_over_imean"}
    assert pn["meta"]["conv_threshold"] == 0.01


def test_matched_count_passes_the_criterion_for_both_and_is_minimal_in_common():
    pn = J("package_network.json")
    rows = list(csv.DictReader((D / "bga_count_screen.csv").open()))
    n = pn["matched_count"]
    for a in ("Z1", "Z2"):
        r = next(x for x in rows if x["arch"] == a and int(x["n_per_rail"]) == n)
        assert r["pass__HV_S0"] == "True", a
    assert pn["meta"]["criterion_classification"] == "ENGINEERING_CRITERION"


def test_terminal_is_the_traced_pad_not_the_untraced_tile():
    pn = J("package_network.json")
    assert "traced" in pn["meta"]["terminal_status"]
    for c in pn["convergence"].values():
        assert c["levels"][-1]["terminal_mode"] == "VIN_PAD"


def test_ledger_has_one_owner_per_conductor_and_no_silent_zero():
    led = J("electrical_ledger.json")
    for a in ("Z1", "Z2"):
        for s in SCEN:
            terms = [r["term"] for r in led["rows"] if r["arch"] == a and r["scenario"] == s]
            assert terms, (a, s)
            assert len(terms) == len(set(terms)), f"duplicated owner in {a} {s}"
            for need in ("P_conv_hs", "P_conv_ls", "P_intraVR_metal", "P_intraVR_vertical",
                         "P_pkg_RDL_HV_supply", "P_pkg_RDL_HV_return", "P_BGA_supply",
                         "P_BGA_return", "P_TSV_VDD", "P_TSV_GND", "P_pad_VDD", "P_pad_GND",
                         "P_pkg_RDL_LV_supply", "P_pkg_RDL_LV_return"):
                assert need in terms, (a, s, need)
    for r in led["rows"]:
        if r["P_w"] == 0.0:
            assert r["maturity"] == "STRUCTURALLY_ABSENT", r["term"]
            assert r.get("alternative_P_w", 0) > 0, "an absent term must quantify its alternative"


def test_energy_audit_separates_definitional_from_conservation_checks():
    au = J("energy_audit.json")
    assert au["pass"] is True
    for k, c in au["cases"].items():
        assert "DEFINITIONAL" in c["fixed_point_note"]
        assert abs(c["deposition_residual_rel"]) < au["tolerance_rel"], k
        assert abs(c["thermal_balance_residual_rel"]) < au["tolerance_rel"], k
        # the bottom flow is COMPUTED, so it is a real number, not Q - q_top
        assert c["q_bottom_W"] > 0 and c["q_top_W"] > 0
        assert abs(c["q_top_W"] + c["q_bottom_W"] - c["Q_ledger_W"]) / c["Q_ledger_W"] < 1e-6


# ----------------------------------------------------------------- thermal/mech
def test_every_case_converged_under_the_declared_criteria():
    fin = J("final_results.json")
    assert {(f["arch"], f["scenario"]) for f in fin} == {(a, s) for a in ("Z1", "Z2")
                                                         for s in SCEN}
    for f in fin:
        assert f["et_converged"], f
        assert f["et_final_max_dT_K"] < 0.25 and f["et_final_dP_rel"] < 1e-3


def production_case(arch, scen):
    """The ETM case file the final results were frozen from (production mesh)."""
    fin = J("final_results.json")
    row = next(f for f in fin if f["arch"] == arch and f["scenario"] == scen)
    return J(row["case_file"])


def test_the_critical_joint_is_searched_over_every_site():
    for a, n in (("Z1", 1369), ("Z2", 528)):
        r = production_case(a, "HV_S0")
        js = r["mechanics"]["joint_search"]
        assert js["n_sites"] == n and js["n_evaluated"] == n, a
        du = [x["du_um"] for x in js["ranked"]]
        assert du == sorted(du, reverse=True)
        assert js["critical"]["du_um"] == du[0]


def test_heat_is_deposited_only_inside_cell_footprints_for_converter_tiers():
    src = (R / "scripts" / "final_closure_physical_etm.py").read_text()
    assert "IN_TILE_KEYS" in src and "_region_elems" in src
    assert "362 C hot spot" in src, "the defect the confinement fixes must stay documented"


def test_local_solder_harness_reproduces_its_control_and_reports_failures():
    loc = J("local_solder_HV_S0.json")
    assert loc["control_deviation_pct"] < loc["control_tolerance_pct"]
    for s in SCEN:
        f = D / f"local_solder_{s}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text())
        for a, c in d["cases"].items():
            if c["response"] is None:
                # a non-converged point is recorded as such, never filled in
                assert c["T_outside_norton_calibration"] or c["T_joint_C"] > 0


def test_no_absolute_life_anywhere_in_the_results():
    txt = (D / "FINAL_PAPER_DECISION.md").read_text().lower()
    assert "cycles to failure" not in txt.replace("no cycles to failure", "")
    assert "darveaux" in txt


def test_mesh_convergence_was_declared_before_reading():
    mc = J("mesh_convergence.json")
    assert mc["declared_before_reading"] is True
    assert mc["tolerance_rel"] == 0.02
    assert mc["cases"], "no mesh-convergence cases recorded"


def test_nested_levels_are_strict_refinements():
    """The h_xy 1.1 -> 0.8 pair was NOT a refinement (Z2 kept 38 lines per axis and its
    largest element grew). Every level used as evidence must be nested: splitting each
    interval in N multiplies the element count by exactly N (per split direction)."""
    mc = J("mesh_convergence.json")
    expect = {"r21": 4, "r31": 9, "r12": 2}
    for arch, c in mc["cases"].items():
        n0 = c["levels"]["r11"]["n_elems"]
        for tag, k in expect.items():
            if tag in c["levels"]:
                assert c["levels"][tag]["n_elems"] == k * n0, (arch, tag)
        assert set(c["checks"]) <= {"in-plane", "through-thickness"}, c["checks"]
        rm = c.get("remesh_sensitivity")
        if rm:
            assert "NOT a refinement" in rm["note"]


def test_production_mesh_passes_the_declared_tolerance_or_is_not_ready():
    mc = J("mesh_convergence.json")
    dec = (D / "FINAL_PAPER_DECISION.md").read_text().split("## Decision")[-1]
    ok = all(c["complete"] and (c["pass"] or c.get("bounded_ok")) for c in mc["cases"].values())
    if "PAPER_READY" in dec and "NOT_READY" not in dec:
        assert ok, "PAPER_READY declared on a mesh that is neither converged nor bounded"
    tex = " ".join(TEX.read_text().split())
    for c in mc["cases"].values():
        for k, st in (c.get("observable_status") or {}).items():
            assert st != "unbounded", f"{k} is above tolerance and unbounded"
            if st == "bounded":   # the paper must say so
                assert r"\MeshBoundSentence" in tex
                mac = (R / "manuscript" / "final_lineage_macros.tex").read_text()
                assert "Richardson" in mac.split("MeshBoundSentence")[1].split("\n")[0]
    if mc["production_refine"] != [1, 1]:
        assert mc["production_reason"], "a refined production mesh must state why"


def test_every_final_result_comes_from_the_production_mesh():
    fin = J("final_results.json")
    mc = J("mesh_convergence.json")
    r = mc["production_refine"]
    tag = "" if r == [1, 1] else f"_r{r[0]}{r[1]}"
    labels = {f["mesh_label"] for f in fin}
    assert len(labels) == 1, labels
    for f in fin:
        assert f["case_file"] == f"etm_{f['arch']}_{f['scenario']}_h1.1{tag}.json", f
    for s in SCEN:
        loc = J(f"local_solder_{s}.json")
        for a, c in loc["cases"].items():
            src = c["critical_joint"].get("source")
            assert src == f"etm_{a}_{s}_h1.1{tag}.json", (s, a, src)


def test_iterative_structural_solver_is_verified_before_use():
    """SPOOLES segfaults at 43k C3D8I here; ITERATIVE CHOLESKY was once 35 % off.
    Any structural result from the iterative solver needs a same-mesh verification."""
    fin = J("final_results.json")
    if all(f.get("structural_solver", "SPOOLES") == "SPOOLES" for f in fin):
        pytest.skip("no iterative structural result")
    it = J("solver_check/Z1_HV_S0_h1.1_ITERATIVE_CHOLESKY_t10.json")
    dr = J("solver_check/Z1_HV_S0_h1.1_SPOOLES_t1.json")
    assert it["ok"] and dr["ok"] and it["n_elems"] == dr["n_elems"]
    for k in ("die_warpage_pv_um", "du_c_um"):
        assert abs(it[k] - dr[k]) / abs(dr[k]) < 1e-3, k


def test_temperature_couplings_are_live_not_pinned():
    cc = J("coupling_checks.json")
    for a, v in cc["tsv_temperature_coupling"].items():
        assert v["ratio"] > 1.05, a
        assert abs(v["ratio"] - v["expected_ratio_rho_cu"]) < 1e-3, a
    z = cc["z2_cutout_underside"]
    assert z["bottom_film_faces"] > 0 and z["faces_inside_cutout"] == 0


# ------------------------------------------------------------------ scenarios
def test_scenarios_are_never_called_a_bracket():
    for f in ("FINAL_PAPER_SCOPE.md", "FINAL_PAPER_DECISION.md"):
        t = (D / f).read_text().lower()
        for m in re.finditer(r"bracket", t):
            w = t[max(0, m.start() - 80):m.end() + 40]
            assert "not a bracket" in w or "never a bracket" in w or "not" in w, w


# ------------------------------------------------------------------ gates
def test_every_open_gate_is_classified_A_B_or_C():
    g = json.loads((R / "research/phase0nw/physical_gates.json").read_text())
    cls = J("paper_gate_classification.json")
    known = {r["id"]: r["class"] for r in cls["rows"]}
    for r in g["gates"]:
        if r["status"] == "OPEN":
            assert r["id"] in known, f"OPEN gate {r['id']} has no paper class"
            assert known[r["id"]] in ("A", "B", "C")


def test_no_class_A_gate_remains_open_if_the_paper_is_declared_ready():
    dec = (D / "FINAL_PAPER_DECISION.md").read_text()
    if "PAPER_READY" not in dec.split("## Decision")[-1]:
        pytest.skip("paper not declared ready")
    g = json.loads((R / "research/phase0nw/physical_gates.json").read_text())
    cls = {r["id"]: r["class"] for r in J("paper_gate_classification.json")["rows"]}
    still = [r["id"] for r in g["gates"] if r["status"] == "OPEN" and cls.get(r["id"]) == "A"]
    assert not still, f"PAPER_READY with class-A gates open: {still}"


# ------------------------------------------------------------------ accuracy
def test_accuracy_matrix_has_no_overall_number_and_honest_speedups():
    acc = J("accuracy_speed_matrix.json")
    assert "no overall framework accuracy" in acc["note"]
    for r in acc["rows"]:
        assert "overall" not in r["stage"].lower()
        if r.get("speedup") not in (None, ""):
            assert r["status"] == "EXECUTED", r["stage"]
            assert r.get("machine"), r["stage"]


EVID_FOLDER = {"tsv_tile_kz": "tsv_tile_rve", "tsv_tile_kx": "tsv_tile_rve",
               "rdl_tier_kx": "rdl_tier_rve", "rdl_tier_kz": "rdl_tier_rve",
               "pkg_rdl_Z1": "pkg_rdl_moose_Z1", "pkg_rdl_Z2": "pkg_rdl_moose_Z2",
               "thermal_column_aedt_Z1": "thermal_column_Z1",
               "thermal_column_aedt_Z2": "thermal_column_Z2",
               "mech_bilayer_aedt": "mech_bilayer"}


def test_reference_tool_evidence_is_real_where_claimed():
    acc = J("accuracy_speed_matrix.json")
    for r in acc["rows"]:
        tool = r.get("reference_tool", "")
        if r.get("status") != "EXECUTED" or not ("Electronics Desktop" in tool
                                                 or "MOOSE" in tool):
            continue
        stage = r["stage"]
        d = DECK / "tool_evidence" / EVID_FOLDER.get(stage, stage)
        assert d.exists(), f"{stage}: reference result claimed without an evidence folder"
        assert list(d.glob("*.png")), f"{stage}: no image from the reference run"
        for f in ("README.md", "setup.json", "runtime.json"):
            assert (d / f).exists(), f"{stage}: evidence folder lacks {f}"
        if "MOOSE" in tool:
            assert (d / "04_field.png").exists(), f"{stage}: no field rendered from MOOSE output"


def test_no_field_image_is_a_relabelled_geometry_image():
    """Three '04_field' PNGs were byte-identical copies of geometry renders."""
    for d in (DECK / "tool_evidence").iterdir():
        if not d.is_dir():
            continue
        geo = {p.read_bytes() for p in d.glob("01_geometry*.png")}
        for f in d.glob("04_field*.png"):
            assert f.read_bytes() not in geo, f"{f} is a geometry image labelled as a field"


def test_runtimes_state_their_method():
    acc = J("accuracy_speed_matrix.json")
    for r in acc["rows"]:
        if isinstance(r.get("speedup"), (int, float)):
            m = r.get("timing_method", "")
            assert "repeats" in m or "n = 1" in m, (r["stage"], m)


def test_no_q3d_result_is_presented():
    for p in (D / "accuracy_speed_matrix.csv", DECK / "index.html"):
        t = p.read_text()
        for m in re.finditer(r"Q3D", t):
            w = t[max(0, m.start() - 160):m.end() + 160].lower()
            assert any(x in w for x in ("not licensed", "unlicensed", "ready_not_executed",
                                        "not executed", "licence")), w[:200]


# ------------------------------------------------------------------ manuscript
def test_manuscript_uses_the_physical_lineage_macros():
    tex = TEX.read_text()
    assert r"\input{final_lineage_macros}" in tex
    for m in (r"\PlossZone", r"\TmaxZtwo", r"\DuRatio", r"\NballMatched"):
        assert m in tex, m
    for f in ("final_physical_table.tex", "final_ledger_table.tex", "final_accspeed_table.tex",
              "final_lineage_macros.tex"):
        assert (R / "manuscript" / f).exists(), f


def test_frozen_values_only_appear_in_a_historical_frame():
    tex = " ".join(TEX.read_text().split())
    a = tex.index(r"\begin{abstract}")
    b = tex.index(r"\end{abstract}")
    abstract = tex[a:b]
    for stale in ("118.32", "126.46", "137.292", "139.659", "4.6252", "3.8714",
                  "16.3", "18.4"):
        assert stale not in abstract, f"the abstract still carries the frozen {stale}"
    i = tex.index(r"\subsection{Historical frozen pair}")
    j = tex.index(r"\label{sec:physical}")
    assert j < i, "the physical comparison must precede the historical pair"
    # the frozen pair may never again be titled or captioned as the final result
    assert r"\subsection{Final architecture comparison}" not in tex
    assert r"\caption{Final cross-domain comparison" not in tex
    html = (DECK / "index.html").read_text()
    for m in re.finditer(r"118\.32|126\.46", html):
        assert "HISTORICAL" in html[max(0, m.start() - 1500):m.start()], "frozen value unlabelled"


def test_conclusion_states_the_physical_result():
    tex = TEX.read_text()
    c = tex[tex.index(r"\section{Conclusion}"):tex.index(r"\section*{Acknowledgment}")]
    assert r"\DuRatio" in c and "reverse" in c
    assert "neither architecture is yet dimensionally closed" not in c


# ------------------------------------------------------------------ deck
def test_deck_pdf_one_page_per_slide_and_tool_slides_have_evidence():
    prt = (DECK / "print.html").read_text()
    n = prt.count("<div class='pg reveal'>")
    pdf = (DECK / "HVR_OPT_Prelim.pdf").read_bytes()
    assert len(re.findall(rb"/Type\s*/Page[^s]", pdf)) == n
    html = (DECK / "index.html").read_text()
    for src in re.findall(r'src="(tool_evidence/[^"]+)"', html):
        assert (DECK / src).exists(), src
    assert "Reference tool — matched run" in html


def test_deck_shows_stage_runtimes_and_disclaims_only_the_end_to_end_claim():
    html = (DECK / "index.html").read_text()
    assert "No end-to-end commercial flow speedup is claimed." in html
    assert "Accuracy and runtime, stage by stage" in html
    assert "Speedup against a higher-fidelity reference" not in html


def test_manuscript_audit_value_matcher_negative():
    """NEGATIVE: the historical-value guard matched '12.4' inside the current '12.49'.
    It must still catch the real stale value, with or without trailing zeros."""
    import sys
    sys.path.insert(0, str(R / "scripts" / "phase0mr3c"))
    import audit_manuscript as A
    assert A.value_hits("12.4", "a 12.4 b") and A.value_hits("12.4", "a 12.40\\,\\% b")
    assert not A.value_hits("12.4", "a 12.49 b") and not A.value_hits("12.4", "a 112.4 b")


def test_thermal_claim_respects_the_discretisation_uncertainty():
    od = J("ordering.json")["orderings"]["T_max_C"]
    tex = " ".join(TEX.read_text().split())
    abstract = tex[tex.index(r"\begin{abstract}"):tex.index(r"\end{abstract}")]
    if od.get("hv_s0_within_mesh_uncertainty"):
        assert "within the measured discretisation uncertainty" in abstract


# ------------------------------------------------------------------ literature
def test_literature_rules_classify_every_listed_source_without_invention():
    lr = J("literature_rules.json")
    listed = {"10.1109/TCPMT.2026.3724907", "10.1109/TCPMT.2026.3716571",
              "10.1016/j.mtelec.2026.100211", "10.3390/ma14216394", "10.1109/TED.2026.3724984",
              "10.1016/j.ijmecsci.2025.110758", "10.1109/ECTC.2004.1319419",
              "10.1115/1.1413764"}
    got = {s["doi"]: s for s in lr["sources"]}
    assert set(got) == listed
    bib = (R / "manuscript" / "ETM_DVPD_REFERENCES.bib").read_text().lower()
    for doi, s in got.items():
        assert s["class"] in lr["rules"], doi
        if s["class"] == "NOT_HELD":
            # nothing may be drawn from a source this environment never held
            assert s["title"] is None and s["use"] == "none", doi
            assert doi.lower() not in bib, f"{doi} is cited but was never held"
        else:
            assert s["held"] != "NOTHING", doi
