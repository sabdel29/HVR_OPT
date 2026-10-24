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
        assert b["i_rms_a"] >= abs(b["i_avg_a"]) - 1e-12
        assert b["i_peak_a"] >= b["i_rms_a"] - 1e-12
    d = s["design"]
    assert d["i_cell_out_rms_a"] >= d["i_cell_out_avg_a"]
    assert d["i_mid_rms_a"] >= d["i_mid_avg_a"]


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


def test_phase_a_and_phase_b_branches_have_different_ripple(s):
    a = [b for b in s["branches"] if b["phase"] == "A"]
    bb = [b for b in s["branches"] if b["phase"] == "B"]
    assert len(a) == 2 and len(bb) == 1
    assert a[0]["ripple_pp_a"] > bb[0]["ripple_pp_a"] * 10, (
        "phase A sees V_mid - V_out, phase B sees -V_out; the ripples cannot match")
    assert a[0]["i_rms_a"] > bb[0]["i_rms_a"]


def test_branch_ripples_reproduce_the_frameworks_output_ripple(s):
    """The per-branch split must sum back to the ledger's own expression."""
    d = s["design"]
    total = d["K_A"] * d["ripple_A_pp_a"] - (d["K"] - d["K_A"]) * d["ripple_B_pp_a"]
    assert total == pytest.approx(d["ripple_out_pp_a"], rel=1e-9)


# -------------------------------------------------- brief 1, 7: the 48 V rail is OPEN
def test_the_48v_rms_is_a_bracket_not_a_value(s):
    for arch in ("Z1", "Z2"):
        h = s["architectures"][arch]["hv"]
        assert h["i_rms_lower_a"] == pytest.approx(h["i_avg_a"], rel=1e-12)
        assert h["i_rms_upper_a"] > h["i_avg_a"] * 3.5
        assert h["status"].startswith("OPEN")
        assert "charge-transfer waveform is not in the framework" in h["status"]


def test_eq5_is_a_sanity_check_not_our_value(s):
    for arch in ("Z1", "Z2"):
        h = s["architectures"][arch]["hv"]
        assert "SANITY" in h["why_not_eq5"]
        assert "3:1 SC stage" in h["why_not_eq5"]
        ref = s["architectures"][arch]["eq5_reference_total_a"]
        assert ref != pytest.approx(h["i_rms_lower_a"], rel=0.1)


def test_the_1v_rail_ripple_is_quantified_not_assumed(s):
    """Z2's substrate rail is close to DC, and that is demonstrated, not asserted."""
    for arch in ("Z1", "Z2"):
        v = s["architectures"][arch]
        assert 1.0 < v["lv_rms_over_avg_worst"] < 1.02
        assert v["lv_rms_worst_a"] > v["lv_avg_a"]


# ----------------------------------------------- the loss consequence (brief 8, 9, 31)
def test_48v_conductor_losses_carry_a_sixteen_fold_span():
    import interconnect_loss as IL
    L = IL.ledger("Z1")
    for k in ("P_BGA_supply", "P_BGA_return"):
        lo, hi = L["terms"][k]["bracket_w"]
        assert hi / lo == pytest.approx(16.0, rel=0.02), (
            "a 4x RMS bracket must appear as 16x in I^2 R")
        assert L["terms"][k]["status"] == "DC_LOWER_BOUND"


def test_z2_substrate_tsv_is_rms_closed():
    """The 1 V rail's ripple IS derivable, so Z2's TSV loss is not a bracket."""
    import interconnect_loss as IL
    L = IL.ledger("Z2")
    t = L["terms"]["P_TSV_VDD"]
    assert t["status"] == "RECOMPUTED_RMS"
    lo, hi = t["bracket_w"]
    assert hi == pytest.approx(lo, rel=1e-9)
    assert t["w"] * 1e3 == pytest.approx(213.0, abs=1.0)


def test_the_old_dc_numbers_are_the_lower_bounds_not_the_answers():
    import interconnect_loss as IL
    L = IL.ledger("Z1")
    assert L["terms"]["P_BGA_supply"]["bracket_w"][0] * 1e3 == pytest.approx(
        10.889, abs=0.02), "the DC figure must survive as the lower bound"
