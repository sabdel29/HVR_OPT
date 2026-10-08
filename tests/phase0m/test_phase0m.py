"""Phase-0M tests.

Every guard added in this phase is NEGATIVE-tested: the offending input is injected and the
guard must fire. A guard that has only ever been seen to pass has not been tested.
"""
from __future__ import annotations
import csv, math, re, sys
from pathlib import Path

import numpy as np
import pytest
import yaml

R = Path(__file__).resolve().parents[2]
for d in ("phase0m", "phase0i", "phase0ir", "phase0e", "phase0dr"):
    sys.path.insert(0, str(R / "scripts" / d))

RES = R / "results" / "phase0m"
CFG = R / "configs" / "phase0m"


def rd(name):
    p = RES / name
    assert p.is_file(), f"missing artifact {name}"
    return list(csv.DictReader(p.open()))


# --------------------------------------------------------------- Part 1 classification
def test_classify_covers_every_used_parameter():
    from interconnect import classify, CLASSES
    for k in ("rho_Cu_20C", "tsv_radius", "R_field", "J_max_Cu", "rdl_t_cu"):
        assert classify(k) in CLASSES


def test_classify_raises_on_unclassified_parameter():
    """NEGATIVE: an unclassified parameter must not silently pass."""
    from interconnect import classify
    with pytest.raises(KeyError):
        classify("some_parameter_nobody_declared")


# --------------------------------------------------------------- Part 3 the radius law
def test_policy_A_field_resistance_is_independent_of_cross_section():
    """R_field = rho h J / I must not depend on the conductor area at all."""
    from interconnect import TSVGeometry, evaluate, rho_cu, r_field_policy_A_analytic
    foot, I, j, T = (22.36e-3) ** 2, 1000.0, 1.0e8, 85.0
    target = r_field_policy_A_analytic(rho_cu(T), 300e-6, j, I)
    for r_um in (5.0, 10.0, 15.0, 25.0, 40.0):
        g = TSVGeometry(r_m=r_um * 1e-6, h_m=300e-6)
        e = evaluate(g, I, j, foot, "A_min_capability", T_c=T)
        rel = abs(e["R_field_mohm"] / 1e3 - target) / target
        # the identity holds whether or not the geometry is BUILDABLE -- it is a property of
        # the allocation rule, not of feasibility
        assert rel < 1e-3, f"r={r_um}: {rel:.3e} -- the cancellation must be exact"
    # and feasibility must still be reported honestly: r = 5 um is aspect-ratio 30
    assert not TSVGeometry(r_m=5e-6, h_m=300e-6).ar_ok
    assert evaluate(TSVGeometry(r_m=15e-6, h_m=300e-6), I, j, foot,
                    "A_min_capability", T_c=T)["feasible"]


def test_policy_B_field_resistance_does_depend_on_radius():
    """NEGATIVE CONTROL: the cancellation is a property of the POLICY, not of the code."""
    from interconnect import TSVGeometry, evaluate
    foot, I, j = (22.36e-3) ** 2, 1000.0, 1.0e8
    a = evaluate(TSVGeometry(r_m=5e-6, h_m=300e-6), I, j, foot, "B_fixed_count",
                 n_fixed=15000)
    b = evaluate(TSVGeometry(r_m=25e-6, h_m=300e-6), I, j, foot, "B_fixed_count",
                 n_fixed=15000)
    assert a["R_field_mohm"] / b["R_field_mohm"] > 20.0


def test_copper_fraction_is_radius_independent_under_policy_A():
    from interconnect import TSVGeometry, evaluate
    foot, I, j = (22.36e-3) ** 2, 1000.0, 1.0e8
    phis = [evaluate(TSVGeometry(r_m=r * 1e-6, h_m=300e-6), I, j, foot,
                     "A_min_capability")["phi_cu"] for r in (5, 15, 30)]
    assert max(phis) / min(phis) < 1.01


def test_pitch_rule_is_enforced():
    from interconnect import TSVGeometry
    g = TSVGeometry(r_m=15e-6, h_m=300e-6, p_m=20e-6)
    assert not g.pitch_legal
    assert TSVGeometry(r_m=15e-6, h_m=300e-6).pitch_m == pytest.approx(60e-6)


def test_aspect_ratio_gate():
    from interconnect import TSVGeometry
    assert TSVGeometry(r_m=15e-6, h_m=300e-6).ar_ok
    assert not TSVGeometry(r_m=5e-6, h_m=300e-6).ar_ok


# --------------------------------------------------------------- Part 7 the solver
def test_fv_solver_is_exact_on_a_uniform_bar():
    from conduction3d import FVConduction
    sig, L, a = 5.8e7, 100e-6, 20e-6
    for n in (6, 12):
        m = FVConduction(np.linspace(0, L, n + 1), np.linspace(0, a, n + 1),
                         np.linspace(0, a, n + 1))
        m.assign(lambda X, Y, Z: np.full_like(X, sig))
        inj = np.zeros((n, n, n), bool); inj[0, :, :] = True
        gnd = np.zeros((n, n, n), bool); gnd[-1, :, :] = True
        m.solve(inj, 1.0, gnd, axis_in=0, axis_gnd=0)
        assert m.resistance() == pytest.approx(L / (sig * a * a), rel=1e-9)
        assert m.resistance_from_power() == pytest.approx(m.resistance(), rel=1e-9)
        assert abs(m.current_out() - 1.0) < 1e-9


def test_fv_solver_rejects_a_zero_width_cell():
    """NEGATIVE: the real offending grid -- two coincident nodes -- must raise."""
    from conduction3d import FVConduction
    with pytest.raises(ValueError, match="non-positive cell width"):
        FVConduction(np.array([0.0, 1e-6, 1e-6, 2e-6]), np.array([0.0, 1e-6]),
                     np.array([0.0, 1e-6]))


def test_snapped_merges_coincident_interface_planes():
    """NEGATIVE: without tolerance-based dedup this grid carries a zero-width cell."""
    from conduction3d import snapped, refined
    base = refined(-10e-6, 10e-6, 2e-6, -10e-6, 10e-6)
    a = 5e-6
    b = a * (1 + 2 ** -50)          # one ULP apart, np.unique keeps both
    out = snapped(base, [-a, -b, 0.0, b, a], 2e-6)
    assert np.all(np.diff(out) > 0), "snapped() left a zero-width cell"
    assert np.unique(np.round(out * 1e9, 3)).size == out.size


def test_crowding_validity_gate_rejects_an_unbalanced_solve(monkeypatch):
    """NEGATIVE: an unbalanced solve must be REPORTED, never returned as a K_crowd.

    The gate is exercised directly by making the solver under-deliver current, which is the
    symptom the real zero-width-cell fault produced. A geometry that simply disconnects the
    via instead trips an EARLIER guard (`the injection set is entirely outside the conducting
    region`), which is also correct but tests a different line."""
    import crowding as CR
    from conduction3d import FVConduction
    monkeypatch.setattr(FVConduction, "current_out", lambda self: 0.5)
    r = CR.solve_cell(CR.build("TSV_pad_RDL"), refine=0.6)
    assert r["status"].startswith("CURRENT BALANCE FAILED")
    assert "K_crowd" not in r


def test_crowding_rejects_a_disconnected_injection_region():
    """NEGATIVE: the earlier guard, on its own offending input."""
    import crowding as CR
    c = CR.build("TSV_pad_RDL")
    bad = CR.Cell(name="disconnected", r_via=c.r_via, h_via=c.h_via, r_pad=c.r_pad,
                  w_trace=c.w_trace, t_rdl=c.t_rdl, l_trace=c.l_trace,
                  sigma_via=c.sigma_via * 1e-12, sigma_metal=c.sigma_metal)
    with pytest.raises(ValueError, match="injection set"):
        CR.solve_cell(bad, refine=0.6)


def test_crowding_factor_is_not_a_constant():
    rows = [r for r in rd("current_crowding_transition_sweep.csv") if r["status"] == "OK"]
    ks = [float(r["K_crowd"]) for r in rows]
    assert len(rows) > 80
    assert max(ks) / min(ks) > 2.0, "the whole point is that 1.326 is not one number"
    for r in rows:
        assert float(r["current_balance_err"]) < 1e-3
        assert float(r["power_vs_terminal_pct"]) < 1e-6


def test_crowding_excess_resistance_is_length_independent():
    rows = [r for r in rd("current_crowding_transition_sweep.csv")
            if r["status"] == "OK" and r["factor"] == "trace_length"
            and r["cell"] == "microbump_UBM_pad_RDL"]
    dr = [float(r["dR_excess_mohm"]) for r in rows]
    k = [float(r["K_crowd"]) for r in rows]
    assert len(dr) >= 3
    assert (max(dr) - min(dr)) / abs(min(dr)) < 0.02, "dR must be length-independent"
    assert (max(k) - min(k)) / min(k) > 0.02, "K_crowd must NOT be, or dR is not the point"


# --------------------------------------------------------------- Part 0-F ME reconstruction
def test_me_parser_keeps_mechanical_strain_separate_from_total_strain():
    """NEGATIVE: with the regex alternation reversed, 'mechanical strains' matches the
    'strains' branch and ME silently overwrites E."""
    from me_energy import parse_tensors_me
    import tempfile
    txt = (" stresses (elem, integ.pnt.,sxx,...) for set E and time  0.1000000E+01\n"
           "       1   1  1.0  2.0  3.0  4.0  5.0  6.0\n"
           " strains (elem, integ.pnt.,exx,...) for set E and time  0.1000000E+01\n"
           "       1   1  0.11  0.12  0.13  0.14  0.15  0.16\n"
           " mechanical strains (elem, integ.pnt.,exx,...) for set E and time  0.1000000E+01\n"
           "       1   1  0.21  0.22  0.23  0.24  0.25  0.26\n")
    with tempfile.NamedTemporaryFile("w", suffix=".dat", delete=False) as fh:
        fh.write(txt); p = Path(fh.name)
    d = parse_tensors_me(p, {1})[1.0][1]
    assert d["E"][0] == pytest.approx(0.11)
    assert d["ME"][0] == pytest.approx(0.21)
    p.unlink()


def test_temperature_recovered_from_the_solvers_own_thermal_strain():
    from me_energy import temperature_from_fields
    from decompose import CTE_SAC305
    t0, t = 25.0, 82.8604875
    th = CTE_SAC305 * (t - t0)
    E = [0.001 + th, 0.002 + th, -0.003 + th, 0.004, 0.0, 0.0]
    ME = [0.001, 0.002, -0.003, 0.004, 0.0, 0.0]
    assert temperature_from_fields(E, ME, t0) == pytest.approx(t, rel=1e-9)


def test_me_route_is_isochorically_cleaner_than_the_python_route():
    rows = rd("me_energy_reconstruction.csv")
    assert len(rows) >= 8
    for r in rows:
        if r["status"] != "OK":
            continue
        me_, py = float(r["isochoric_residual_ME"]), float(r["isochoric_residual_python"])
        assert me_ < 5e-3, "inelastic flow must be isochoric"
        assert py / me_ > 5.0, "the solver-coherent route must be measurably cleaner"
        assert abs(float(r["me_over_production"]) - 1.0) < 0.05


# --------------------------------------------------------------- Parts 10-13 routing
def test_intra_vr_model_does_not_double_count_device_parasitics():
    """The Level-1 net list must contain metallization only."""
    import routing as RT
    names = {n.name for n in RT.nets()}
    for forbidden in ("rdson", "esr", "dcr", "switching", "coss", "gate"):
        assert not any(forbidden in n.lower() for n in names)


def test_intra_vr_loss_is_common_mode_across_architectures():
    rows = rd("intra_vr_ranking_effect.csv")
    assert rows[0]["ordering_changed"] == "False"
    assert float(rows[0]["p_intra_vr_system_w"]) > 0.0


def test_output_plane_current_density_infeasibility_is_reported_not_clipped():
    import routing as RT
    r = RT.route_loss("R1", t_cu_m=10e-6, j_max=1.0e8, n_layers=1)
    assert r["n_infeasible"] >= 1
    assert "vout_plane" in r["infeasible"]


# --------------------------------------------------------------- Parts 20-22 homogenization
def test_voigt_is_exact_for_through_thickness_conduction():
    rows = rd("effective_layer_properties.csv")
    tsv = [r for r in rows if r["layer"] == "TSV_array"]
    assert tsv
    for r in tsv:
        assert float(r["err_voigt_kz_pct"]) < 1.0
        assert r["verdict_voigt_kz"] == "ACCEPTED"


def test_the_pre_existing_transverse_model_is_never_accepted():
    """It is REJECTED at four of five geometries and CONDITIONAL at the fifth -- never
    ACCEPTED. The first version of this test asserted REJECTED everywhere, which was one
    geometry too strong and is the reason the artifacts quoted 38 to 74 % instead of the
    measured 19 to 74 %."""
    rows = [r for r in rd("effective_layer_properties.csv") if r["layer"] == "TSV_array"]
    assert len(rows) == 5
    v = [r["verdict_framework_kxy"] for r in rows]
    assert v.count("REJECTED") == 4 and v.count("CONDITIONAL") == 1
    assert "ACCEPTED" not in v
    errs = [float(r["err_framework_kxy_pct"]) for r in rows]
    assert 18.0 < min(errs) < 20.0 and 73.0 < max(errs) < 75.0


def test_unit_cell_periodicity():
    r = next(r for r in rd("effective_layer_properties.csv")
             if r["layer"] == "TSV_periodicity_check")
    assert float(r["err_framework_kxy_pct"]) < 0.5


# --------------------------------------------------------------- Parts 23-26 cooling
def test_derived_h_matches_the_nusselt_definition():
    from cooling import Microchannel, K_F
    mc = Microchannel(w_ch_um=50, h_ch_um=300, t_fin_um=50, m_dot_g_s=10.0)
    s = mc.solve()
    assert s["h_channel_W_m2K"] == pytest.approx(s["Nu"] * K_F / mc.d_h_m, rel=1e-9)
    assert s["Re"] < 2300 and s["regime"] == "laminar"


def test_stated_flow_cannot_carry_the_stated_heat():
    from cooling import required_flow, Microchannel
    s = Microchannel(w_ch_um=50, h_ch_um=300, t_fin_um=50, m_dot_g_s=1.6).solve()
    assert s["dT_fluid_K"] > 100.0
    assert required_flow(10.0) / 1.6 > 10.0


def test_cooling_gradient_changes_the_mechanics():
    rows = rd("cooling_etm_sensitivity.csv")
    base = next(r for r in rows if r["tag"] == "uniform")
    assert float(base["warpage_vs_uniform_pct"]) == pytest.approx(0.0, abs=1e-9)
    assert max(abs(float(r["warpage_vs_uniform_pct"])) for r in rows) > 1.0


# --------------------------------------------------------------- Parts 14-16 partition
def test_single_level_vr_does_not_fit_the_die_shadow():
    rows = {r["template"]: r for r in rd("component_partition_templates.csv")}
    assert rows["T0_SINGLE_LEVEL"]["fits_die_shadow"] == "False"
    assert float(rows["T0_SINGLE_LEVEL"]["die_shadow_utilisation"]) > 1.5
    assert rows["T1_EMBEDDED_4LAYER"]["fits_die_shadow"] == "True"


def test_summed_footprint_exceeds_the_reported_tile_area():
    r = rd("component_partition_templates.csv")[0]
    assert float(r["summed_component_area_mm2"]) / 5.61 > 3.0


# --------------------------------------------------------------- Parts 17-19 Z5
def test_z5_equivalent_resistance_is_consistent_and_grid_converged():
    rows = rd("z5_path_decomposition.csv")
    b = rows[0]
    assert float(b["R_eq_mohm"]) == pytest.approx(float(b["P_loop_w"]) / 1e6 * 1e3, rel=1e-9)
    grids = [r for r in rows if "grid" in r["stack"]]
    ps = [float(r["P_loop_w"]) for r in grids]
    assert (max(ps) - min(ps)) / min(ps) < 0.005


def test_z5_loop_square_count_is_stack_independent():
    rows = [r for r in rd("z5_path_decomposition.csv")
            if r["stack"] in ("ectc2024_primary", "ectc2024_one_per_net",
                              "iscas2024_variant")]
    sq = [float(r["loop_squares"]) for r in rows]
    assert (max(sq) - min(sq)) / min(sq) < 1e-6, "squares are geometry, not stack"


def test_pcb_row_is_more_conductive_than_the_rdl_row():
    rows = {r["path"]: r for r in rd("z5_pcb_vs_rdl.csv")}
    assert (float(rows["RDL"]["loop_R_mohm_per_sq"])
            / float(rows["PCB"]["loop_R_mohm_per_sq"])) > 4.0


def test_z5_missing_stage_is_not_counted_as_zero():
    rows = rd("z5_architecture_comparison.csv")
    lb = [r for r in rows if r["total_is"].startswith("LOWER BOUND")]
    assert lb, "some stage-1 conversions do not compile; that must be visible"
    for r in lb:
        assert float(r["P_total_stage1_at_97pct_w"]) > float(r["P_total_w"])


# --------------------------------------------------------------- coupling
def test_m_to_e_feedback_is_negligible_against_a_modelled_term():
    rows = {r["mechanism"]: r for r in rd("etm_feedback_magnitudes.csv")}
    r = rows["elastic deformation changes conductor geometry"]
    assert float(r["ratio"]) < 0.02
    assert r["verdict"] == "NEGLIGIBLE"


def test_damage_feedback_is_flagged_material():
    rows = [r for r in rd("etm_feedback_magnitudes.csv")
            if "crack" in r["mechanism"] or "delamination" in r["mechanism"]]
    assert rows
    assert all(r["verdict"] == "MATERIAL ONLY WITH DAMAGE" for r in rows)


# --------------------------------------------------------------- Part 0 closure
def test_retired_wording_is_absent_from_both_reports():
    for name in ("ETM_DVPD_FULL_TECHNICAL_REPORT.md",
                 "ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.md"):
        t = (R / "results" / name).read_text()
        for bad in ("must reproduce it.", "must rank Z1 worse",
                    "must therefore rank Z1 worse", "Eleven sequential falsification gates"):
            assert bad not in t, f"{name}: {bad!r} survives"


def test_licensed_structural_wording_is_present():
    t = (R / "results" / "ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.md").read_text()
    assert "constitutive-law-independent deformation driver favoring Z2" in t


def test_specimen_provenance_distinguishes_four_counts():
    rows = rd("specimen_count_provenance.csv")
    assert {r["n_per_cell"] for r in rows} == {"34", "68", "48", "16"}
    cur = [r for r in rows if r["status"].startswith("CURRENT")]
    assert len(cur) == 1 and cur[0]["packages"] == "192"


def test_status_yaml_records_what_PHASE_0M_established():
    """DEFECT #53 class. This is a PHASE-0M test, so it asserts what Phase 0M concluded --
    which is permanent -- and NOT what the current phase happens to be, which is not. A test
    that pins `current_phase` to its own phase fails the moment the project moves on, and
    tempts whoever sees it red into editing the YAML back rather than the test."""
    d = yaml.safe_load((R / "results" / "CURRENT_SCIENTIFIC_STATUS.yaml").read_text())
    assert d["phase0m_verdict"]["option_letter"] == "G"
    assert d["verdict"]["phase0m"].startswith("MULTIPLE MISSING PHYSICAL COUPLINGS")
    assert len(d["verdict"]["basis_phase0m"]) == 6
    assert d["etm_coupling"]["current_level"].startswith("ETM-L1")
    assert d["optimizer"]["allowed"] is False
    assert "0L --" not in d["next_gate"]["id"]


def test_phase0m_level1_routing_statement_is_superseded_not_deleted():
    """Phase 0M said Level 1 was modelled but absent from the total. Phase 0M-R put it in.
    The old wording must survive as a `_superseded_note`, never be silently overwritten."""
    d = yaml.safe_load((R / "results" / "CURRENT_SCIENTIFIC_STATUS.yaml").read_text())
    rs = d["routing_scope"]
    assert rs["level_1_intra_converter"].startswith("IN PRODUCTION")
    assert "ABSENT before Phase 0M" in rs["level_1_intra_converter_superseded_note"]


def test_anand_wording_distinguishes_parameterized_from_integrated():
    d = yaml.safe_load((R / "results" / "CURRENT_SCIENTIFIC_STATUS.yaml").read_text())
    t = d["constitutive_model"]["admitted_models"]
    assert "PARAMETERIZED" in t and "INTEGRATED" in t
    assert "TWO constitutive families" in t


def test_every_required_phase0m_artifact_exists():
    for n in ("PHASE0M_PHYSICAL_ARCHITECTURE_GATE.md",
              "INTERCONNECT_PARAMETER_CLASSIFICATION.md",
              "TSV_RADIUS_ALLOCATION_LAW.md", "tsv_geometry_sensitivity.csv",
              "CURRENT_CROWDING_SOLVER_AUDIT.md", "current_crowding_transition_sweep.csv",
              "ROUTING_SCOPE_AUDIT.md", "intra_vr_routing_model.csv",
              "COMPONENT_PARTITION_AUDIT.md", "Z5_REAUDIT.md",
              "z5_architecture_comparison.csv", "THERMAL_HOMOGENIZATION_AUDIT.md",
              "effective_layer_properties.csv", "COOLING_BOUNDARY_AUDIT.md",
              "cooling_architecture_sensitivity.csv",
              "MISSING_MECHANICS_PHYSICS_AUDIT.md", "ETM_COUPLING_MATRIX.md",
              "PHYSICS_PRIORITY_MATRIX.csv", "NEW_ETM_LEVERS.md",
              "SPECIMEN_COUNT_PROVENANCE.md", "me_energy_reconstruction.csv",
              "TSV_FRAMEWORK_INTERFACE.md"):
        assert (RES / n).is_file(), f"missing {n}"
    assert (CFG / "interconnect_design_space.yaml").is_file()
    assert (CFG / "component_partition_templates.yaml").is_file()
    for k in "ABCDEFGHIJ":
        assert list(RES.glob(f"FIG_0M_{k}_*.png")), f"missing FIG-0M-{k}"


def test_design_space_yaml_contains_no_resistance_primitive():
    d = yaml.safe_load((CFG / "interconnect_design_space.yaml").read_text())
    flat = yaml.safe_dump(d["design_variables"]) + yaml.safe_dump(d["process_limits"])
    for bad in ("r_ref_ohm", "i_max_a", "resistance", "_ohm:"):
        assert bad not in flat, f"a resistance primitive leaked into the design space: {bad}"


# --------------------------------------------------------------- propagation re-check
def test_no_unadjudicated_stale_current_claim_survives():
    """The DEFECT-#44 scanner still fires on retractions, definitions and a quoted defect.
    Every surviving hit is adjudicated by excerpt in scripts/phase0m/propagation_recheck.py,
    and the set is PINNED: a hit that is not on that list fails here, so a genuinely new
    stale claim cannot hide among the known-benign ones."""
    import subprocess
    r = subprocess.run([sys.executable,
                        str(R / "scripts" / "phase0m" / "propagation_recheck.py")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_the_adjudication_list_is_not_a_blanket_suppression():
    """NEGATIVE: the pinning must be per-EXCERPT, not per-claim-id. Injecting a genuinely
    stale sentence under an already-adjudicated claim id must still fail."""
    sys.path.insert(0, str(R / "scripts" / "phase0m"))
    import importlib
    pr = importlib.import_module("propagation_recheck")
    fake = {"report": "STANDALONE", "claim_id": "C11", "status": "STALE-CURRENT",
            "section": "25. Current claims", "excerpt": "the extrapolation cancels entirely"}
    key = next((k for k in pr.ADJUDICATED
                if k[0] == fake["report"] and k[1] == fake["claim_id"]
                and k[2] in fake["excerpt"]), None)
    assert key is None, "a new sentence must not inherit another sentence's adjudication"


def test_built_pdfs_carry_the_phase0m_conclusions():
    """Do not trust the source Markdown. Re-extract the text from the BUILT PDFs and check
    that every Phase-0M conclusion a reader must find is actually there."""
    import subprocess
    r = subprocess.run([sys.executable,
                        str(R / "scripts" / "phase0m" / "pdf_text_inspect.py")],
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
