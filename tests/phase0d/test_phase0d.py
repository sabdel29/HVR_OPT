"""Phase-0D tests. The 49 Phase-0B/0C tests are preserved untouched."""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0b"))
sys.path.insert(0, str(R / "scripts" / "phase0d"))

from electrical import (ALPHA_CU, ALPHA_GAN_RDSON, RHO_CU_20C, TSVField,  # noqa: E402
                        dcr_at, lateral_pdn, rdson_at, rho_cu)
from etm.config import load_doe, load_stack                               # noqa: E402

P0C, P0D = R / "results" / "phase0c", R / "results" / "phase0d"


# ------------------------------------------------------- geometry-derived TSV resistance
def test_tsv_reproduces_june_reference():
    """R = rho*h/A at the June Table III geometry must land on the quoted 7.1 mOhm."""
    v = TSVField().validate_against_june()
    assert abs(v["error_pct"]) < 3.0, v
    assert 7.0e-3 < v["R_model_Ohm"] < 7.4e-3


def test_tsv_scales_linearly_with_height():
    f = TSVField()
    assert f.r_single(600e-6) / f.r_single(300e-6) == pytest.approx(2.0, rel=1e-12)
    assert f.r_single(150e-6) / f.r_single(300e-6) == pytest.approx(0.5, rel=1e-12)


def test_tsv_scales_as_inverse_diameter_squared():
    a, b = TSVField(d_m=30e-6), TSVField(d_m=60e-6)
    assert b.r_single(300e-6) / a.r_single(300e-6) == pytest.approx(0.25, rel=1e-12)


def test_tsv_scales_as_inverse_parallel_count():
    f = TSVField(i_via_max_a=1.0)
    r1, n1 = f.r_field(300e-6, 1.0)
    r4, n4 = f.r_field(300e-6, 4.0)
    assert n1 == 1 and n4 == 4
    assert r4 / r1 == pytest.approx(0.25, rel=1e-12)


def test_tsv_resistance_is_positive_and_finite():
    f = TSVField()
    for h in (50e-6, 200e-6, 300e-6, 500e-6, 1e-3):
        r = f.r_single(h)
        assert r > 0 and math.isfinite(r)
    with pytest.raises(ValueError):
        f.r_single(0.0)


def test_via_count_from_current_and_area_cap():
    f = TSVField(i_via_max_a=0.033)
    assert f.n_required(0.0) == 1
    assert f.n_required(0.033) == 1
    assert f.n_required(0.034) == 2
    assert f.n_required(3.3) == 100
    # area cap: a 1 mm^2 tile at 60 um pitch holds ~277 sites
    assert f.n_available(1.0) == pytest.approx(277, abs=2)
    r, n = f.r_field(300e-6, 1000.0, footprint_mm2=1.0)
    assert n <= f.n_available(1.0), "via count must be capped by available area"


# ------------------------------------------------------------- temperature coefficients
def test_copper_temperature_coefficient():
    assert rho_cu(20.0) == pytest.approx(RHO_CU_20C, rel=1e-12)
    assert rho_cu(120.0) / rho_cu(20.0) == pytest.approx(1 + ALPHA_CU * 100, rel=1e-9)
    assert rho_cu(120.0) > rho_cu(20.0), "copper resistivity must rise with temperature"


def test_tsv_resistance_rises_with_temperature():
    f = TSVField()
    assert f.r_single(300e-6, 125.0) > f.r_single(300e-6, 25.0)
    ratio = f.r_single(300e-6, 125.0) / f.r_single(300e-6, 20.0)
    assert ratio == pytest.approx(1 + ALPHA_CU * 105, rel=1e-9)


def test_gan_rdson_temperature_model():
    r25 = 10e-3
    assert rdson_at(r25, 25.0) == pytest.approx(r25, rel=1e-12)
    assert rdson_at(r25, 125.0) == pytest.approx(r25 * (1 + ALPHA_GAN_RDSON * 100), rel=1e-12)
    assert rdson_at(r25, 125.0) > rdson_at(r25, 25.0)


def test_inductor_dcr_uses_copper_coefficient():
    assert dcr_at(10.0, 125.0) == pytest.approx(10.0 * (1 + ALPHA_CU * 100), rel=1e-12)


# --------------------------------------------------------------- h_sub propagation
def test_h_sub_changes_tsv_resistance():
    """The whole point of Phase 0D: h_sub must reach the electrical model."""
    f = TSVField()
    r200 = f.r_single(200e-6)
    r500 = f.r_single(500e-6)
    assert r500 > r200
    assert r500 / r200 == pytest.approx(2.5, rel=1e-12)


def test_h_sub_changes_pdn_and_electrical_objective():
    """If 200 and 500 um give identical electrical results the coupling is still broken."""
    p = P0D / "coupled_candidates.csv"
    if not p.exists():
        pytest.skip("candidate sweep not yet run")
    rows = [r for r in csv.DictReader(p.open()) if r.get("converged") == "True"]
    pairs = {}
    for r in rows:
        key = (r["n_vr"], r["j_target"], r["placement"])
        pairs.setdefault(key, {})[r["h_sub_mm"]] = r
    checked = 0
    for key, g in pairs.items():
        if "0.2" in g and "0.5" in g:
            a, b = g["0.2"], g["0.5"]
            assert float(b["r_tsv_field_uohm"]) > float(a["r_tsv_field_uohm"]), key
            assert float(b["p_tsv_w"]) != float(a["p_tsv_w"]), key
            assert float(b["p_elec_total_w"]) != float(a["p_elec_total_w"]), key
            checked += 1
    assert checked >= 4, f"only {checked} matched thickness pairs found"


# ------------------------------------------------------- lateral PDN equivalence
def test_lateral_pdn_matches_upstream_formulation():
    """Reimplementation must be numerically identical to the upstream model."""
    pol = np.array([(x, y) for x in (-5.0, 5.0) for y in (-5.0, 5.0)])
    vr = np.array([(-4.0, -4.0), (4.0, -4.0), (-4.0, 4.0), (4.0, 4.0)])
    out = lateral_pdn(pol, vr, 240.0, 50.0, 1e6, r_bump_ohm=0.08e-3,
                      r_series_ohm=0.04e-3, temp_aware=False)
    # hand-computed reference for this symmetric layout
    rho_ac = 50.0 * 1e-3 * math.sqrt(1e6 / 1e6)
    d = 2.0                                     # Manhattan distance, every pair symmetric
    r_b = 0.04e-3 + 2 * 0.08e-3 + rho_ac * d
    # each POL sees one branch at d=2, two at d=10, one at d=18
    ds = [2.0, 10.0, 10.0, 18.0]
    g = sum(1.0 / (0.04e-3 + 2 * 0.08e-3 + rho_ac * x) for x in ds)
    r_eff = 1.0 / g
    expect = 4 * (240.0 / 4) ** 2 * r_eff
    assert out["p_lateral_w"] == pytest.approx(expect, rel=1e-9)


def test_lateral_pdn_temperature_raises_loss():
    pol = np.array([(0.0, 0.0)])
    vr = np.array([(3.0, 0.0)])
    cold = lateral_pdn(pol, vr, 100.0, 50.0, 1e6, 0.08e-3, T_c=25.0)
    hot = lateral_pdn(pol, vr, 100.0, 50.0, 1e6, 0.08e-3, T_c=125.0)
    assert hot["p_lateral_w"] > cold["p_lateral_w"]


# ------------------------------------------------------------- power conservation
def test_candidate_energy_balance_closes():
    p = P0D / "coupled_candidates.csv"
    if not p.exists():
        pytest.skip("candidate sweep not yet run")
    for r in csv.DictReader(p.open()):
        if r.get("converged") != "True":
            continue
        assert abs(float(r["energy_residual_pct"])) < 0.01, r["cand"]


def test_candidate_loss_decomposition_sums():
    p = P0D / "coupled_candidates.csv"
    if not p.exists():
        pytest.skip("candidate sweep not yet run")
    for r in csv.DictReader(p.open()):
        if r.get("converged") != "True":
            continue
        tot = float(r["p_conv_total_w"]) + float(r["p_pdn_w"])
        assert tot == pytest.approx(float(r["p_elec_total_w"]), rel=1e-9), r["cand"]
        pdn = float(r["p_lateral_w"]) + float(r["p_tsv_w"])
        assert pdn == pytest.approx(float(r["p_pdn_w"]), rel=1e-9), r["cand"]


def test_fixed_point_converged_or_rejected():
    p = P0D / "coupled_candidates.csv"
    if not p.exists():
        pytest.skip("candidate sweep not yet run")
    for r in csv.DictReader(p.open()):
        # a non-converged candidate must carry no physical results
        if r.get("converged") != "True":
            assert not r.get("die_warpage_pv_um"), f"{r['cand']} reported results unconverged"


def test_fixed_point_history_is_monotone_in_temperature():
    d = P0D / "fixed_point_histories"
    if not d.exists() or not list(d.glob("*.json")):
        pytest.skip("no fixed-point histories yet")
    for f in sorted(d.glob("*.json"))[:6]:
        hist = json.loads(f.read_text())
        deltas = [h["dT_max_K"] for h in hist if h.get("dT_max_K") is not None]
        if len(deltas) >= 2:
            assert deltas[-1] < deltas[0], f"{f.name}: temperature increments not shrinking"


# -------------------------------------------------------------- HVR footprint emission
def test_hvr_design_emits_rectangular_footprint():
    from electrical import HVRDesign
    d = HVRDesign(label="t", arch=None, hs=None, ls=None, inductor=None, capacitor=None,
                  f_sw_hz=1e6, i_out_a=60.0, v_in=48.0, v_out=1.0, area_mm2=25.0,
                  area_budget_mm2=30.0, loss_25c_w=4.0, j_target=2.0)
    ax, ay = d.footprint_xy_mm
    assert ax * ay == pytest.approx(25.0, rel=1e-12)
    assert ax == pytest.approx(ay), "square-tile approximation is explicit"


# ------------------------------------------------------------------- C07_THICK
def test_c07_thick_definition_matches_c07_except_thickness():
    from run_c07_thick import C07_THICK
    doe = load_doe()
    c07 = doe["cases"]["C07"]
    for k in ("n_vr", "placement", "tile_ax", "tile_ay", "p_hvr_total_w"):
        assert C07_THICK[k] == c07[k], k
    assert C07_THICK["h_sub"] == 0.500 and c07["h_sub"] == 0.200


def test_frozen_doe_not_renumbered():
    doe = load_doe()
    assert sorted(doe["cases"]) == [f"C{i:02d}" for i in range(1, 21)]
    assert "C07_THICK" not in doe["cases"], "the frozen DOE must not be modified on disk"


def test_c07_thick_interaction_closed():
    p = P0D / "c07_thick_result.json"
    if not p.exists():
        pytest.skip("C07_THICK not yet run")
    d = json.loads(p.read_text())
    assert abs(d["interaction_residual_pp"]) < 3.0
    assert d["separable"] is True
    assert abs(d["energy_residual_pct"]) < 0.01


# ------------------------------------------------------------ ranking discipline
def test_et_objective_frozen_before_mechanics():
    """The ET definition file must predate the candidate results on disk."""
    obj = P0D / "ET_OBJECTIVE_DEFINITION.md"
    cand = P0D / "coupled_candidates.csv"
    assert obj.exists(), "ET objective must be written before ranking"
    if cand.exists():
        assert obj.stat().st_mtime < cand.stat().st_mtime, \
            "ET objective must be frozen BEFORE the candidate sweep produced results"


def test_et_ranking_uses_only_electrical_thermal_columns():
    p = P0D / "et_ranking.csv"
    if not p.exists():
        pytest.skip("ET ranking not yet produced")
    cols = set(next(csv.reader(p.open())))
    banned = {"die_warpage_pv_um", "pkg_warpage_pv_um", "interface_shear_p99_MPa",
              "interface_peel_p99_MPa", "si_principal_p99_MPa"}
    assert not (cols & banned), f"ET ranking contaminated by mechanical columns: {cols & banned}"


def test_no_unresolved_peel_in_any_phase0d_output():
    """Phase-0C declared interface peel UNRESOLVED AT M0; it must not reappear."""
    for f in P0D.glob("*.csv"):
        cols = set(next(csv.reader(f.open()), []))
        assert not any("peel" in c.lower() for c in cols), f"{f.name} uses a peel metric"


def test_no_h0_local_stress_in_ranking():
    for name in ("et_ranking.csv", "etm_ranking.csv", "pareto_et.csv", "pareto_etm.csv"):
        p = P0D / name
        if not p.exists():
            continue
        cols = set(next(csv.reader(p.open())))
        assert "si_principal_p99_MPa" not in cols, f"{name} ranks on invalid H0 local stress"


# --------------------------------------------------------------- Pareto machinery
def test_pareto_front_is_correct_on_a_known_set():
    from analyze_reversal import pareto_front
    pts = [(1.0, 1.0), (2.0, 2.0), (1.0, 3.0), (3.0, 0.5), (2.0, 0.4)]
    front = sorted(pareto_front(pts))
    assert front == [0, 4], f"got {front}"


def test_pareto_front_single_point():
    from analyze_reversal import pareto_front
    assert pareto_front([(1.0, 2.0)]) == [0]


# ------------------------------------------------------ Phase 0B/0C preservation
def test_phase0b_0c_artifacts_intact():
    for f in ("results/phase0b/PHASE0B_FIRST_MECHANICAL_GATE.md",
              "results/phase0b/gate_runs.csv",
              "results/phase0c/PHASE0C_DVPD_MECHANICAL_LEVER_GATE.md",
              "results/phase0c/full_doe_results.csv",
              "results/phase0c/robustness_results.csv"):
        assert (R / f).exists(), f"{f} was removed"


def test_phase0c_reproduced():
    p = P0D / "phase0c_reproduction.json"
    if not p.exists():
        pytest.skip("reproduction not yet run")
    v = json.loads(p.read_text())
    assert v["reproduced"] is True
    for c in v["cases"]:
        assert c["delta_pct"] < 0.5, c
