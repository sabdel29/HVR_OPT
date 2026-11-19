"""TCPMT review round 3 --- the manifold cold plate, the unified comparison rule and the ladder
rungs of the variant drivers.

Guards on: the 4-zone manifold as the production plate (dp about 1/16, the same h and coolant
rise, the developing fraction of a pass unchanged) with the single pass kept as variant
plate_single_pass; the 1-D zone sink (one temperature per column, alternating directions); the
GCI-type rule (asymptotic Fs = 1.25 with the observed order, else Fs = 3), the law band in the
joint response, no transfer without a check; the uncertainty record built on it; the refinement
rung of the variant drivers (its own case name, never the production file)."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

R = Path(__file__).resolve().parents[2]
for _p in ("scripts", "scripts/phase0m", "scripts/phase0mr"):
    sys.path.insert(0, str(R / _p))


# ------------------------------------------------------------------ manifold plate
@pytest.fixture()
def plate():
    import cooling as C
    from cooling_production import CANDIDATES
    p0 = C.PLATE_MODEL
    yield C, CANDIDATES["TOP_SI_MICROCHANNEL_27"]
    C.PLATE_MODEL = p0


def test_manifold_is_production_single_pass_is_a_variant(plate):
    C, c = plate
    import final_closure_sensitivity as S
    assert C.PLATE_MODEL == "manifold" and C.MANIFOLD_ZONES == 4
    assert c.zones() == 4
    assert "plate_single_pass" in S.VARIANTS
    S.v_cooling_model(plate="single_pass")
    assert c.zones() == 1
    with pytest.raises(ValueError):
        S.v_cooling_model(plate="three_pass")
    # the other candidates stay single pass whatever the production construction
    from cooling_production import CANDIDATES
    C.PLATE_MODEL = "manifold"
    assert CANDIDATES["TOP_SI_MICROCHANNEL_50"].zones() == 1


def test_manifold_hydraulics_and_heat_transfer(plate):
    C, c = plate
    C.PLATE_MODEL = "single_pass"
    sp = c.channel().solve(1000.0)
    C.PLATE_MODEL = "manifold"
    mf = c.channel().solve(1000.0)
    # one pass: L/4 with m/4 -> fully developed dp exactly 1/16 (f Re fixed), Re 1/4
    assert sp["dp_fd_kPa"] / mf["dp_fd_kPa"] == pytest.approx(16.0, rel=1e-9)
    assert sp["Re"] / mf["Re"] == pytest.approx(4.0, rel=1e-9)
    assert sp["dp_entrance_kPa"] / mf["dp_entrance_kPa"] == pytest.approx(16.0, rel=1e-9)
    # the same h, coolant rise per zone, bulk temperature and caloric resistance
    for k in ("Nu", "h_channel_W_m2K", "h_local_W_m2K", "dT_fluid_K", "T_bulk_mean_C",
              "R_caloric_K_W"):
        assert mf[k] == pytest.approx(sp[k], rel=1e-12), k
    # header estimate only for the manifold; the total about 13x below the single pass
    assert sp["dp_header_kPa"] == 0.0 and sp["dp_turns_kPa"] == 0.0
    assert mf["dp_header_kPa"] > 0.0 and mf["dp_turns_kPa"] > 0.0
    assert 800.0 < sp["dp_kPa"] < 900.0 and 50.0 < mf["dp_kPa"] < 75.0
    assert mf["pump_W"] == pytest.approx(mf["dp_kPa"] * 1e3 * 27e-3 / mf["props"]["rho"])
    # developing-length check: the same fraction of each pass is developing
    a, b = sp["developing_flow"], mf["developing_flow"]
    assert a["L_th_over_pass"] == pytest.approx(b["L_th_over_pass"], rel=1e-9)
    assert a["x_star"] == pytest.approx(b["x_star"], rel=1e-9)
    assert b["Nu_mean_developing_over_fd"] > 1.0      # fully developed Nu: a lower bound
    assert mf["pass_length_mm"] == pytest.approx(22.36 / 4)


def test_bottom_plate_keeps_its_flow_rule_under_the_manifold(plate):
    C, c = plate
    import final_closure_physical_etm as E
    rec = E.plate_records(c, 900.0, [({"plate": True, "rule": "equal_rise", "layer": "b",
                                       "label": "", "h_W_m2K": 1e5}, 180.0)])
    assert rec["plate_model"] == "manifold" and rec["n_zones"] == 4
    top, bot = rec["plates"]
    assert bot["m_dot_g_s"] == pytest.approx(27.0 * 180.0 / 900.0)
    assert bot["n_zones"] == 4 and top["n_zones"] == 4
    assert bot["dT_coolant_K"] == pytest.approx(top["dT_coolant_K"], rel=1e-3)


def test_streamwise_cumulative_columns_and_sawtooth():
    from cooling_production import streamwise_cumulative, zone_relaxation, zone_of
    x = np.repeat(np.arange(0.5, 22.0, 1.0), 3)          # 22 columns of 3 faces, L = 22
    q = np.ones(len(x))
    one = streamwise_cumulative(x, q, 1, (0.0, 22.0))
    # one value per column, mid-column convention, rising in +x
    cols = one.reshape(-1, 3)
    assert np.all(cols == cols[:, :1])
    assert cols[0, 0] == pytest.approx(1.5) and np.all(np.diff(cols[:, 0]) > 0)
    four = streamwise_cumulative(x, q, 4, (0.0, 22.0)).reshape(-1, 3)[:, 0]
    z = zone_of(x, 4, (0.0, 22.0)).reshape(-1, 3)[:, 0]
    for k in range(4):
        t = four[z == k]
        assert np.all(np.diff(t) > 0) if k % 2 == 0 else np.all(np.diff(t) < 0)
        assert t.max() == pytest.approx(3 * (z == k).sum() - 1.5)   # outlet column
    w = zone_relaxation(x, np.ones(len(x)), 1e5, 4, (0.0, 22.0), 3.5)
    assert np.all((w > 0) & (w <= 1))


# ------------------------------------------------------------------ the rule
def test_gci_classes_and_bias():
    import tcpmt_resolution as RULE
    # an exactly second-order ladder: asymptotic, Fs = 1.25, bias to the exact value
    y = lambda h: 10.0 + 3.0 * h ** 2
    g = RULE.gci(y(1.0), y(0.5), y(1 / 3))
    assert g["class"] == "asymptotic" and g["Fs"] == 1.25
    assert g["p_obs"] == pytest.approx(2.0, abs=1e-6)
    assert g["y_corrected"] == pytest.approx(10.0, abs=1e-9)
    assert g["U"] == pytest.approx(1.25 * abs(g["beta"]))
    # first order: not asymptotic, Fs = 3 at the observed order (within [0.5, 2])
    y1 = lambda h: 10.0 + 3.0 * h
    g1 = RULE.gci(y1(1.0), y1(0.5), y1(1 / 3))
    assert g1["class"] == "not asymptotic" and g1["Fs"] == 3.0
    assert g1["p"] == pytest.approx(1.0, abs=1e-6)
    assert g1["y_corrected"] == pytest.approx(10.0, abs=1e-9)
    # oscillatory: no signed estimate, Fs/2 x range
    go = RULE.gci(1.0, 1.2, 1.1)
    assert go["class"] == "oscillatory" and go["beta"] == 0.0
    assert go["U"] == pytest.approx(3.0 * 0.5 * 0.2)
    # two rungs (through-thickness): Fs = 3 at the formal order, the coarse value's error
    tt = RULE.gci_two_rung(1.0, 1.3)
    assert tt["beta"] == pytest.approx(0.4) and tt["U"] == pytest.approx(1.2)


def test_judge_law_band_and_transfer_check():
    import tcpmt_resolution as RULE
    j = RULE.judge(1.0, -0.4, 0.5)
    assert j["D_corrected"] == pytest.approx(0.6) and j["resolved"]
    assert not RULE.judge(1.0, -0.6, 0.5)["resolved"]
    lb = RULE.law_band({"a": (2.0, 1.0), "b": (1.5, 1.0)}, "a")
    assert lb["verdict"] == RULE.RESOLVED
    lb = RULE.law_band({"a": (2.0, 1.0), "b": (0.5, 1.0)}, "a")
    assert lb["verdict"] == RULE.LAW_CONDITIONAL
    lb = RULE.law_band({"a": (0.5, 1.0), "b": (2.0, 1.0)}, "a")
    assert lb["verdict"] == RULE.NOT_RESOLVED
    m = (100, 200, 1.1, (2, 1))
    assert RULE.transfer_check(m, m)["ok"]
    assert "pending" in RULE.transfer_check(m, m)["status"]
    assert not RULE.transfer_check((101, 200, 1.1, (2, 1)), m)["ok"]
    assert not RULE.transfer_check(m, m, case_r11_step=1.0, ref_r11_step=0.0,
                                   ref_u_mesh=0.5)["ok"]


def test_uncertainty_ladders_and_reference_pairs():
    import tcpmt_uncertainty as TU
    f = TU.ladder_files(TU.FC / "etm_Z1_HV_S0_h1.1_r21.json")
    assert f["r11"].name == "etm_Z1_HV_S0_h1.1.json"
    assert f["r31"].name == "etm_Z1_HV_S0_h1.1_r31.json"
    v = TU.ladder_files(TU.SENS / "etm_Z1_HV_SDEC__sdec_B.json")
    assert v["r21"].name == "etm_Z1_HV_SDEC__sdec_B.json"
    assert v["r31"] == TU.SENS / "ladder" / "etm_Z1_HV_SDEC__sdec_B_r31.json"
    pairs = TU.reference_pairs()
    z = pairs["Z1/Z2"]
    if not z["own_ladders"]:
        pytest.skip("the S0 production ladders are not in this checkout")
    for y in TU.OBS:
        o = z["outputs"][y]
        assert o["U_mesh"] >= 0 and o["Fs"] in (1.25, 3.0)
    # the reference pair compared on its own ladders: not provisional
    a, b = TU.reference_path("Z1"), TU.reference_path("Z2")
    va, vb = TU.obs(TU.J(a)), TU.obs(TU.J(b))
    r = TU.compare("A", "Z1", "Z2", "T", a, b, va["T"], vb["T"])
    assert r["basis"] == "own ladders" and r["provisional"] is False
    assert r["U95"] > 0 and r["verdict"] in ("resolved", "not resolved")
    # a variant pair on another mesh is pending, on the same mesh provisional
    mz1, mz2 = TU.mesh_signature(TU.J(a)), TU.mesh_signature(TU.J(b))
    ok = TU.variant_judgement("Z1", "Z2", "T", va["T"], vb["T"], mz1, mz2, pairs)
    assert ok["provisional"] is True and ok["verdict"] in ("Z1 lower", "Z2 lower", "unresolved")
    bad = TU.variant_judgement("Z1", "Z2", "T", va["T"], vb["T"],
                               (1, 1, 1.1, (2, 1)), mz2, pairs)
    assert bad["verdict"] == "pending"


def test_committed_uncertainty_record_uses_the_rule():
    d = json.loads((R / "research" / "tcpmt_revision" / "uncertainty.json").read_text())
    assert "U95" in d["rule"] and d["coverage"].startswith("about 95")
    for c in d["comparisons"]:
        assert c["verdict"] in ("resolved", "not resolved", "law-conditional", "pending")
        if c["verdict"] != "pending":
            assert c["resolved"] == (abs(c["D_corrected"]) > c["U95"]) or c["output"] == "eps"
    assert isinstance(d["ladder_runs_needed"], list)
    for r in d["ladder_runs_needed"]:
        assert r["rung"] in ("r11", "r31", "r12") and r["command"].startswith("python ")


# ------------------------------------------------------------------ ladder rungs
def test_variant_rungs_get_their_own_case_names():
    import final_closure_sensitivity as S
    try:
        assert S.set_refine(None) == (2, 1) and S.is_production_level()
        prod = S.variant_file("Z1", "z1_bottom_plate_tim")
        assert prod == S.case_file("Z1", "z1_bottom_plate_tim")
        S.set_refine("r31")
        assert S.mesh_level() == (3, 1) and not S.is_production_level()
        f = S.variant_file("Z1", "z1_bottom_plate_tim")
        assert f.parent.name == "ladder" and f.name.endswith("__z1_bottom_plate_tim_r31.json")
        assert S.work_name("z1_bottom_plate_tim") == "z1_bottom_plate_tim_r31"
        S.set_refine("r21")                      # the production rung is the production file
        assert S.variant_file("Z1", "x") == S.case_file("Z1", "x")
        with pytest.raises(ValueError):
            S.parse_refine("r3")
    finally:
        S.set_refine(None)


def test_review_variant_rung_token_and_z3land_scratch_dir():
    import tcpmt_review_variants as RV
    import final_closure_sensitivity as S
    rest, rung = RV._split_rung(["sdec", "Z1", "B", "r11"])
    assert rest == ["sdec", "Z1", "B"] and rung == "r11"
    import tcpmt_z3land_variants as ZL
    try:
        S.set_refine("r31")
        d = ZL.scratch_dir("z3_land_t40_A_fvmap")
        assert d.parent.name == "z3_land_t40_A_fvmap_r31" and d.name.endswith("_r31")
    finally:
        S.set_refine(None)
