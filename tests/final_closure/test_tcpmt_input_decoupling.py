"""TCPMT revision --- Z1 input decoupling and flying capacitors (scripts/tcpmt_decap_*.py).

Guards on the committed results and on the models that produced them: the port model must
reproduce the production package network, the ledger at the S0 temperatures must reproduce
the recorded S0 loss, the frequency- and time-domain circuit solutions must agree, the
charge balance must match its closed form, the recommended decoupling must lie between the
smooth and the undecoupled limits, and no thin flying capacitor may be claimed."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts"))
DEC = R / "research" / "tcpmt_revision" / "input_decoupling.json"
FLY = R / "research" / "tcpmt_revision" / "flying_caps.json"


@pytest.fixture(scope="module")
def dec():
    return json.loads(DEC.read_text())


@pytest.fixture(scope="module")
def fly():
    return json.loads(FLY.read_text())


def test_port_model_reproduces_package_network():
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


def test_no_thin_flying_capacitor_claimed(fly):
    assert fly["thin_options"]["any_thin_option_meets_C1_at_32V"] is False
    r = fly["recommended"]["10pct"]
    assert r["C1"]["V_rated"] >= 50 and r["C2"]["V_rated"] >= 25
    assert max(r["ripple_pct"].values()) <= 10.0
    assert r["tier_height"]["nominal"]["via_AR_at_120um"] > 1.0
