"""TCPMT revision --- Z1 input decoupling and flying capacitors (scripts/tcpmt_decap_*.py).

Guards on the committed results and on the models that produced them: the port model must
reproduce the production package network, the ledger at the S0 temperatures must reproduce
the recorded S0 loss, the frequency- and time-domain circuit solutions must agree, the
charge balance must match its closed form, the recommended decoupling must lie between the
smooth and the undecoupled limits, and no thin flying capacitor may be claimed."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts"))
sys.path.insert(0, str(R / "scripts" / "phase0nw"))
#: the results root in force (a campaign root through ETM_RESULTS_ROOT), as the scripts read it
ROOT = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research")
DEC = ROOT / "tcpmt_revision" / "input_decoupling.json"
NET = ROOT / "final_closure" / "package_network.json"
FLY = R / "research" / "tcpmt_revision" / "flying_caps.json"


def _of_design_in_force(dec_doc):
    """True when the decoupling record and the package network are of the design in force
    (TCPMT round 3: the frozen research/ artifacts are the round-2 49-cell design's until the
    campaign regenerates them; a model-vs-artifact check needs both of the same design)."""
    import design_record as DR
    d = (dec_doc.get("circuit") or {}).get("design") or {}
    pn = json.loads(NET.read_text())
    pd = ((pn.get("meta") or {}).get("design") or {}).get("design")
    return (d.get("n_cell", 49) == DR.n_vr() and d.get("design_record") == DR.name()
            and pd == DR.name())


def _require_design_in_force(dec_doc):
    if not _of_design_in_force(dec_doc):
        pytest.skip("the decoupling record / package network in the results root are of "
                    "another design than the record in force (frozen round-2 artifacts): "
                    "run with ETM_RESULTS_ROOT at a root regenerated for the design")


@pytest.fixture(scope="module")
def dec():
    return json.loads(DEC.read_text())


@pytest.fixture(scope="module")
def fly():
    return json.loads(FLY.read_text())


def test_port_model_reproduces_package_network(dec):
    _require_design_in_force(dec)
    import tcpmt_decap_network as NW
    assert abs(NW.self_check()["rel_diff"]) < 5e-3


def test_s0_ledger_reproduced(dec):
    led = dec["framework"]["ledger_at_S0_temperatures"]
    assert abs(led["S0_reproduction_rel"]) < 1e-9


def test_frequency_and_time_domain_agree(dec):
    v = dec["circuit"]["verification"]
    assert v["rel_diff_k"] < 1e-2 and v["rel_diff_ripple"] < 1e-2 and v["rel_diff_Icap"] < 1e-2


def test_charge_balance_closed_form(dec):
    cb = dec["circuit"]["charge_balance"]
    for m in ("ramp_deff", "rect_D"):
        assert abs(cb[m]["Q_pp_C"] / cb[m]["closed_form_Q_C"] - 1.0) < 1e-2


def test_no_decoupling_recovers_the_waveform_k(dec):
    o = dec["placement"]["options"]["none_sync"]
    k_open = dec["circuit"]["waveform"]["ramp_deff"]["k_open"]
    assert abs(o["k_eq_nominal"] / k_open - 1.0) < 1e-2


def test_recommended_between_limits(dec):
    s = dec["summary"]["recommended"]
    k_open = dec["circuit"]["waveform"]["ramp_deff"]["k_open"]
    assert 1.0 < s["k_eq_band"][0] <= s["k_eq"] <= s["k_eq_band"][1] < k_open


def test_ring_parts_fit_the_converter_layer(dec):
    r = dec["summary"]["recommended"]
    assert r["height_mm"][1] < 1.973 and r["rating"].startswith("100 V")


def test_variant_hooks_reproduce_the_ledger_consequence(dec):
    """The coupled variant's ledger hooks, evaluated at the S0 temperatures, give the recorded
    fixed-temperature package-internal loss of the recommended design."""
    _require_design_in_force(dec)
    import tcpmt_decap_circuit as CI
    import tcpmt_decap_framework as F
    rk = F.recommended_k()
    FL = F._register(rk["k_eq"], F.k_open(), rk["P_ring_esr_W"], key="HV_TEST_DEC")
    import replay_production as RPX
    import electrical as EL
    # the committed artifact belongs to the lineage of the S0 case it was computed from
    with EL.pinned_rules(EL.rules_of(json.loads(CI.CASE_S0.read_text()))):
        RPX._DESIGN_CACHE.clear()
        p = FL.self_consistent("Z1", "HV_TEST_DEC", CI.s0_temperatures())["P_loss_w"]
        rec = dec["framework"]["ledger_at_S0_temperatures"]["cases"][F.RECOMMENDED]
        assert abs(p - rec["P_package_internal_W"]) < 1e-6
        assert abs(FL.self_consistent("Z1", "HV_S0", CI.s0_temperatures())["P_loss_w"]
                   - json.loads(CI.CASE_S0.read_text())["P_loss_w"]) < 1e-9
    RPX._DESIGN_CACHE.clear()


def test_recommend_rule_reproduces_the_round2_choice():
    """The declared rule (the n-phase interleavings + ring, least nominal k_eq; the
    one-phase-per-cell spread is the limit, not a candidate) returns the round-2
    recommendation on the frozen round-2 7 x 7 options."""
    import tcpmt_decap_placement as PL
    frozen = json.loads((R / "research" / "tcpmt_revision" / "input_decoupling.json")
                        .read_text())
    if ((frozen.get("circuit") or {}).get("design") or {}).get("n_cell", 49) != 49:
        pytest.skip("the frozen decoupling record is no longer the round-2 7 x 7 one")
    assert (PL.recommend(frozen["placement"]["options"], 7)
            == frozen["summary"]["recommended"]["option"] == "i_latin7+c_ring")


def test_clock_plans_use_every_phase_equally():
    """Every clock plan of the grid in force (review round 3: 9, 12 and 18 phases on the 6 x
    6 grid besides the 6-phase Latin squares) drives each of its phases from the same number
    of cells, and the new plans are reported options, not candidates of the declared rule."""
    import numpy as np
    import tcpmt_decap_network as NW
    import tcpmt_decap_placement as PL
    n = NW.grid_n()
    for p in NW.phase_names():
        if p == "sync":
            continue
        idx = np.round(NW.phases(p) / (2 * np.pi) * NW.phase_denominator(p)).astype(int)
        cnt = np.bincount(idx % NW.phase_denominator(p), minlength=NW.phase_denominator(p))
        assert cnt.min() == cnt.max() > 0, p
    if n == 6:
        assert {"blk9", "dual6", "dual9"} <= set(NW.phase_names())
        fake = {f"i_{p}+c_ring": {"k_eq_nominal": 3.0 - 0.1 * j}
                for j, p in enumerate(NW.phase_names())}
        assert not PL.recommend(fake, n).startswith(("i_blk", "i_dual", "i_spread"))


def test_loss_matrices_reproduce_the_port_model(dec):
    """The quadratic-form port model (limits) gives the k_eq of evaluate() for a clock plan
    with the ring on the network in force."""
    _require_design_in_force(dec)
    import tcpmt_decap_circuit as CI
    import tcpmt_decap_network as NW
    import tcpmt_decap_placement as PL
    f = CI.design()["f_sw_hz"]
    _t, i = CI.phase_a_current("ramp_deff")
    I = CI.harmonics(i)
    l_nom = CI.loop_inductance_estimate()["nominal_pH"] * 1e-12
    r_scale = CI.network_resistance()["loop_hot_ohm"] / NW.self_check()["R_loop_reduced_ohm"]
    xy, _ = NW.ring_layout()
    br, _ = PL.part_branch_params("GRM31CC72A475KE11", 1, PL.L_CONN_NH["c"])
    Ms, Md = NW.loss_matrices(f, l_nom, br, xy, r_scale)
    ph = f"latin{NW.grid_n()}"
    k = NW.k_eq_from(Ms, Md, I, NW.phases(ph))[0]
    ev = NW.evaluate(I, f, l_nom, ring_branch=br, phase=ph, ring_xy=xy, r_scale=r_scale)
    assert k == pytest.approx(ev["k_eq"], rel=1e-9)


def test_no_thin_flying_capacitor_claimed(fly):
    assert fly["thin_options"]["any_thin_option_meets_C1_at_32V"] is False
    r = fly["recommended"]["10pct"]
    assert r["C1"]["V_rated"] >= 50 and r["C2"]["V_rated"] >= 25
    assert max(r["ripple_pct"].values()) <= 10.0
    assert r["tier_height"]["nominal"]["via_AR_at_120um"] > 1.0
