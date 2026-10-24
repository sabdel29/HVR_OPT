"""PHASE 0N-W --- explicit VDD/GND TSV field guards (brief section 16)."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0nw", "scripts"):
    sys.path.insert(0, str(R / p))

from tsv_fields import (D_TSV_MM, P_TSV_MM, cell_report,  # noqa: E402
                        field_resistance, spreading_resistance, system_report)

CELLS, CELL_SIDE, H_TSV, I_TOTAL = 49, 2.3685, 0.300, 1000.0


@pytest.fixture(scope="module")
def sys_r():
    return system_report(CELLS, CELL_SIDE, H_TSV, I_TOTAL)


def test_per_cell_current_is_the_system_current_divided_by_the_cells(sys_r):
    """A local cell field does NOT carry 1 kA. The brief is explicit about this."""
    assert sys_r["i_cell_a"] == pytest.approx(I_TOTAL / CELLS, rel=1e-12)
    assert sys_r["i_cell_a"] == pytest.approx(20.408, abs=1e-3)
    assert sys_r["per_cell"]["i_cell_a"] < 25.0, (
        "a per-cell figure anywhere near the kiloamp aggregate is a unit error")


def test_the_kiloamp_figure_is_only_an_aggregate(sys_r):
    assert sys_r["i_total_a"] == pytest.approx(
        sys_r["i_cell_a"] * sys_r["cells"], rel=1e-12)


def test_vdd_and_gnd_are_separate_and_near_equal(sys_r):
    c = sys_r["per_cell"]
    assert c["n_vdd"] > 0 and c["n_gnd"] > 0
    assert abs(c["n_vdd"] - c["n_gnd"]) <= 1, (
        f"checkerboard interleaving should balance the rails: {c['n_vdd']}/{c['n_gnd']}")
    assert c["n_vdd"] + c["n_gnd"] == c["n_total"] == c["lattice_n"] ** 2


def test_both_fields_are_symmetric_about_the_cell_centre(sys_r):
    """An off-centre rail biases its own thermal and mechanical environment."""
    for k in ("first_moment_vdd_mm", "first_moment_gnd_mm"):
        mx, my = sys_r["per_cell"][k]
        assert abs(mx) < 1e-9 and abs(my) < 1e-9, f"{k} = ({mx}, {my})"


def test_loop_resistance_is_not_simply_twice_the_field(sys_r):
    """The brief forbids relying on R_loop = 2 R_field; the spreading term is reported."""
    c = sys_r["per_cell"]
    assert c["r_loop_ohm"] > c["r_loop_naive_2rfield_ohm"], (
        "the loop must include constriction at the via mouths")
    assert c["spreading_share_pct"] > 0.0
    assert c["r_spread_vdd_ohm"] > 0.0 and c["r_spread_gnd_ohm"] > 0.0


def test_spreading_term_magnitude_is_reported_not_assumed(sys_r):
    """It is small here (~1 %). That is a result, and it must be stated, not assumed
    either way -- the point is that it was computed."""
    c = sys_r["per_cell"]
    assert 0.0 < c["spreading_share_pct"] < 25.0
    # naive_error_pct is SIGNED and must be negative: ignoring constriction
    # UNDER-predicts the loop resistance.
    assert c["naive_error_pct"] < 0.0
    assert c["naive_error_pct"] == pytest.approx(
        100 * (c["r_loop_naive_2rfield_ohm"] - c["r_loop_ohm"]) / c["r_loop_ohm"], rel=1e-9)


def test_geometry_is_the_source_backed_table_iii_values(sys_r):
    c = sys_r["per_cell"]
    assert (c["diameter_um"], c["pitch_um"]) == (30.0, 60.0)
    assert c["h_tsv_um"] == 300.0


def test_copper_area_fraction_is_below_the_ideal_lattice_bound(sys_r):
    """The realized lattice cannot beat the infinite-lattice fraction pi d^2/4p^2."""
    ideal = math.pi * D_TSV_MM ** 2 / (4 * P_TSV_MM ** 2)
    c = sys_r["per_cell"]
    assert c["cu_area_fraction_total"] < ideal, (
        f"realized {c['cu_area_fraction_total']:.4f} exceeds the ideal {ideal:.4f}")
    assert c["cu_area_fraction_total"] > 0.5 * ideal


def test_resistance_scales_as_one_over_count_and_with_length():
    r1 = field_resistance(100, 0.300, D_TSV_MM)
    assert field_resistance(200, 0.300, D_TSV_MM) == pytest.approx(r1 / 2, rel=1e-12)
    assert field_resistance(100, 0.600, D_TSV_MM) == pytest.approx(2 * r1, rel=1e-12)


def test_resistance_rises_with_temperature():
    cold = field_resistance(100, 0.300, D_TSV_MM, T_C=20.0)
    hot = field_resistance(100, 0.300, D_TSV_MM, T_C=120.0)
    assert hot > cold * 1.3, "copper resistivity must carry its temperature coefficient"


def test_power_is_consistent_with_the_reported_resistances(sys_r):
    c = sys_r["per_cell"]
    assert c["p_loop_w"] == pytest.approx(c["i_cell_a"] ** 2 * c["r_loop_ohm"], rel=1e-12)
    assert sys_r["p_tsv_total_w"] == pytest.approx(c["p_loop_w"] * CELLS, rel=1e-12)


def test_cell_too_small_for_a_lattice_is_rejected():
    with pytest.raises(ValueError, match="no TSV lattice"):
        cell_report(0.10, 0.300, 1.0)


# ============================== brief 4, 5, 6: rails, sizing, spreading ends
import sys as _sys  # noqa: E402

_sys.path.insert(0, str(R / "scripts/phase0nw"))
from physical_package import load_physical_package_config  # noqa: E402
import tsv_fields as TSV  # noqa: E402

CFG = R / "configs/phase0nt/z2_2p4mm_cutout.yaml"


@pytest.fixture(scope="module")
def cfg():
    return load_physical_package_config(CFG)


# ---------------------------------------------------------------- section 6: both ends
def test_spreading_counts_two_interfaces_per_rail():
    """Current converges INTO the bundle at one end and OUT of it at the other."""
    one = TSV.spreading_resistance(100, TSV.D_TSV_MM, TSV.P_TSV_MM, ends=1)
    two = TSV.spreading_resistance(100, TSV.D_TSV_MM, TSV.P_TSV_MM, ends=2)
    assert two == pytest.approx(2 * one, rel=1e-12)
    with pytest.raises(ValueError, match="ends must be"):
        TSV.spreading_resistance(100, TSV.D_TSV_MM, TSV.P_TSV_MM, ends=3)


def test_cell_report_uses_two_ends(sys_r):
    c = sys_r["per_cell"]
    assert c["spreading_ends_per_rail"] == 2
    one_end = TSV.spreading_resistance(c["n_vdd"], TSV.D_TSV_MM, TSV.P_TSV_MM, ends=1)
    assert c["r_spread_vdd_ohm"] == pytest.approx(2 * one_end, rel=1e-12), (
        "the rail is being charged only one constriction")


def test_two_ended_spreading_raises_the_loop_above_the_one_ended_value(sys_r):
    """The correction is modest (~2.7 % of the loop) and is reported as modest."""
    c = sys_r["per_cell"]
    assert 2.0 < c["spreading_share_pct"] < 4.0
    assert -4.0 < c["naive_error_pct"] < -2.0


# ---------------------------------------------------------- section 4: distinct rails
def test_z1_rail_is_48v_and_low_current(cfg):
    r = TSV.z1_rail_report(cfg)
    assert r["rail_v"] == 48.0
    assert r["i_total_a"] == pytest.approx(r["p_in_w"] / 48.0, rel=1e-12)
    assert r["i_total_a"] < 20.0, "Z1's 48 V input current is amps, not kiloamps"


def test_z2_rail_is_1v_and_high_current(cfg):
    r = TSV.z2_rail_report(cfg)
    assert r["rail_v"] == 1.0
    assert r["i_total_a"] == pytest.approx(1000.0)
    assert r["i_cell_a"] == pytest.approx(1000.0 / 49, rel=1e-9)


def test_the_two_architectures_do_not_share_a_tsv_current(cfg):
    """This is a core physical distinction of the paper; one shared 1000 A erased it."""
    z1, z2 = TSV.z1_rail_report(cfg), TSV.z2_rail_report(cfg)
    assert z2["i_total_a"] / z1["i_total_a"] > 50.0, (
        f"Z1 {z1['i_total_a']:.2f} A vs Z2 {z2['i_total_a']:.0f} A -- the rails have "
        f"collapsed onto one current")
    assert z2["p_tsv_total_w"] > 100 * z1["p_tsv_total_w"]


def test_z1_current_is_flagged_as_a_placeholder_until_a_physical_solve_exists(cfg):
    r = TSV.z1_rail_report(cfg)
    assert r["placeholder"] is True
    assert "PLACEHOLDER" in r["source"]
    explicit = TSV.z1_rail_report(cfg, p_in_w=150.0)
    assert explicit["placeholder"] is False
    assert explicit["i_total_a"] == pytest.approx(150.0 / 48.0)


# -------------------------------------------------------- section 5: sizing is a choice
def test_tsv_count_is_bracketed_not_just_maximum(cfg):
    s = TSV.sizing_study(cfg)
    assert s["min_drop"]["n_total"] < s["mid"]["n_total"] < s["max_density"]["n_total"]
    assert s["min_drop"]["meets_budget"]


def test_no_current_density_allowable_is_invented(cfg):
    s = TSV.sizing_study(cfg)
    assert s["current_density_allowable"] is None, (
        "an EM allowable was asserted; none is available for this via geometry")
    assert "BOUNDED" in s["budget_status"]


def test_the_adopted_field_is_labelled_maximum_density(cfg):
    """685/684 must not silently become 'the physical TSV count'."""
    s = TSV.sizing_study(cfg)
    assert s["adopted"] == "max_density"
    assert "MAXIMUM-DENSITY" in s["adopted_rationale"]
    assert "not a minimum-required one" in s["adopted_rationale"]


def test_a_much_smaller_field_would_still_meet_the_drop_budget(cfg):
    """The adopted field is ~17x the electrically required count, and that is stated."""
    s = TSV.sizing_study(cfg)
    assert s["max_density"]["n_total"] / s["min_drop"]["n_total"] > 5.0
