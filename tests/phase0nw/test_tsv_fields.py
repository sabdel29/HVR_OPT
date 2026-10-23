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
