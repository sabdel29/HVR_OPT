"""PHASE 0N-AC --- avg vs RMS vs peak (brief 2, 5, 33)."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0nw", "scripts/phase0mr", "scripts/phase0f", "scripts/phase0d",
          "scripts/phase0i", "scripts/phase0m", "scripts"):
    sys.path.insert(0, str(R / p))

import rms_currents as RMS  # noqa: E402


@pytest.fixture(scope="module")
def s():
    return RMS.summary()


# ------------------------------------------------------- brief 33: ordering invariants
def test_rms_never_below_average_and_peak_never_below_rms(s):
    for b in s["branches"]:
        if b["i_rms_a"] is not None:        # branch RMS is withdrawn / OPEN
            assert b["i_rms_a"] >= abs(b["i_avg_a"]) - 1e-12
            assert b["i_peak_a"] >= b["i_rms_a"] - 1e-12
    d = s["design"]
    assert d["i_cell_out_rms_a"] >= d["i_cell_out_avg_a"]
    assert d["i_mid_rms_scenario_a"] >= d["i_mid_avg_a"]


def test_equality_only_for_zero_ripple():
    assert RMS.triangular_rms(10.0, 0.0) == pytest.approx(10.0, rel=1e-15)
    assert RMS.triangular_rms(10.0, 1.0) > 10.0


def test_analytic_triangular_rms_matches_numerical_integration():
    for i_dc, dpp in ((6.8027, 4.6574), (20.4082, 9.0043), (1.0, 0.05)):
        a = RMS.triangular_rms(i_dc, dpp)
        n = RMS._numeric_triangular_rms(i_dc, dpp)
        assert a == pytest.approx(n, rel=2e-5), f"{i_dc},{dpp}: {a} vs {n}"


def test_gated_square_rms_is_analytic():
    assert RMS.gated_square_rms(20.0, 0.25) == pytest.approx(10.0)
    assert RMS.gated_square_rms(20.4082, 0.0625) == pytest.approx(5.1020, abs=1e-3)


# ---------------------------------------------- brief 21, 29: branch currents, not rail
def test_branch_current_is_i_cell_over_three_not_the_cell_current(s):
    d = s["design"]
    assert d["K"] == 3 and d["K_A"] == 2 and d["K_B"] == 1
    for b in s["branches"]:
        assert b["i_avg_a"] == pytest.approx(d["i_cell_out_avg_a"] / 3, rel=1e-9)
        assert b["i_avg_a"] == pytest.approx(6.8027, abs=1e-3)
        assert b["i_avg_a"] < 10.0, "20.4 A must not be put through every branch"










# ============ brief F, G, E: the square-pulse value is NOT an upper bound ============
def test_square_pulse_at_D_is_a_minimum_not_a_maximum():
    """Cauchy-Schwarz: for support exactly D, I_rms >= I_avg/sqrt(D), equality only for
    a CONSTANT pulse. A more peaked waveform of the same average and support has
    strictly higher RMS."""
    i_avg, D = 23.6936, 0.0625
    square = i_avg / math.sqrt(D)
    # same average, same support fraction D, but concentrated into half of it
    peaked = (2 * i_avg / D) * math.sqrt(D / 2)
    more = (4 * i_avg / D) * math.sqrt(D / 4)
    assert peaked > square, "a 2x-amplitude half-width pulse must have higher RMS"
    assert more > peaked, "RMS must keep rising as the pulse narrows"
    assert more / square == pytest.approx(2.0, rel=1e-9)


def test_no_upper_bound_is_claimed_anywhere(s):
    for arch in ("Z1", "Z2"):
        h = s["architectures"][arch]["hv"]
        assert h["upper_bound_a"] is None
        assert "NONE EXISTS" in h["upper_bound_status"]
        assert "HV_S0" in h and "HV_S1" in h
        assert "NOT an upper bound" in h["HV_S1"]["rationale"]


def test_source_text_does_not_call_the_scenario_a_bound():
    src = (R / "scripts/phase0nw/rms_currents.py").read_text()
    low = src.lower()
    for bad in ("i_rms_upper_a", "rms bracket", "hv_input_bracket"):
        assert bad.lower() not in low, f"stale bound language: {bad}"


# ======================= brief B: branch RMS is withdrawn ==========================
def test_individual_branch_rms_is_open(s):
    for b in s["branches"]:
        assert b["i_rms_a"] is None and b["ripple_pp_a"] is None
        assert b["rms_status"].startswith("OPEN")
        assert b["i_avg_a"] == pytest.approx(6.8027, abs=1e-3)
        assert b["i_avg_status"].startswith("KNOWN")


def test_volt_second_balance_sanity_is_recorded_not_adopted(s):
    d = s["design"]
    assert d["conventional_branch_ripple_sanity_a"] == pytest.approx(4.6574, abs=1e-3)
    # the withdrawn 0.310 A value must not reappear as a branch ripple
    for b in s["branches"]:
        assert b["ripple_pp_a"] is None


# ============================ brief H: Eq.(5) is input-side =========================
def test_eq5_is_labelled_an_input_side_reference(s):
    for arch in ("Z1", "Z2"):
        v = s["architectures"][arch]
        assert "dvpd_eq5_input_rms_reference_a" in v
        assert v["dvpd_eq5_input_rms_reference_a"] == pytest.approx(144.34, abs=0.1)
    src = (R / "scripts/phase0nw/rms_currents.py").read_text()
    assert "eq5_reference(" not in src.replace("dvpd_eq5_input_rms_reference_a", "")


# ===================== brief L: Z2 TSV uses independent local fields ================
def test_z2_tsv_uses_per_cell_rms_with_no_cross_terms(s):
    for arch in ("Z1", "Z2"):
        v = s["architectures"][arch]
        assert v["inter_cell_phase_matters"] is False
        assert "no conductor is shared between cells" in v["inter_cell_phase_reason"]
        assert v["i_cell_rms_a"] == pytest.approx(20.5730, abs=1e-3)
        assert 1.0 < v["cell_rms_over_avg"] < 1.02
        # the aggregate 1000 + 49*di form must be gone
        assert "lv_rms_worst_a" not in v


# ================= brief O / AH: generated artifacts must not go stale ==============
@pytest.mark.parametrize("gen,artifact", [
    ("rms_currents", "research/phase0nac/current_waveforms.json"),
    ("interconnect_loss", "research/phase0nab/interconnect_loss.json"),
])
def test_committed_artifact_matches_regenerated_output(gen, artifact):
    """The checked-in interconnect_loss.json went stale against its own source once."""
    import importlib, json
    m = importlib.import_module(gen)
    live = (m.summary() if gen == "rms_currents"
            else {a: m.ledger(a) for a in ("Z1", "Z2")})
    stored = json.loads((R / artifact).read_text())
    assert json.loads(json.dumps(live, sort_keys=True)) == json.loads(
        json.dumps(stored, sort_keys=True)), (
        f"{artifact} is stale against {gen}.py -- regenerate it")


def test_the_two_scenarios_differ_by_sixteen_in_loss_but_are_not_a_span():
    """4x in RMS is 16x in I^2 R. That is a SCENARIO SEPARATION, not an uncertainty
    interval -- there is no upper bound to make an interval out of."""
    import interconnect_loss as IL
    L = IL.ledger("Z1")
    for k in ("P_BGA_supply", "P_BGA_return"):
        s0, s1 = L["terms"][k]["bracket_w"]
        assert s1 / s0 == pytest.approx(16.0, rel=0.02)
        assert L["terms"][k]["status"] == "SCENARIO_S0_S1"
    assert "NONE EXISTS" in L["rms"]["hv_upper_bound"]


def test_z2_substrate_tsv_is_rms_closed_from_local_cell_currents():
    import interconnect_loss as IL
    L = IL.ledger("Z2")
    t = L["terms"]["P_TSV_VDD"]
    assert t["status"] == "RECOMPUTED_RMS"
    lo, hi = t["bracket_w"]
    assert hi == pytest.approx(lo, rel=1e-9)
    assert t["w"] * 1e3 == pytest.approx(213.0, abs=1.0)   # 209.60 raw x 1.008078^2
    assert L["rms"]["i_cell_rms_a"] == pytest.approx(20.5730, abs=1e-3)
