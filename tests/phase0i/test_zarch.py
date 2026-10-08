"""Phase-0I -- guards for architecture-aware realizability and the reliability material model.

DEFECT #33 was that one geometric rule was applied to every architecture. These tests are
written so that reinstating that behaviour makes them fail.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest
import yaml

R = Path(__file__).resolve().parents[2]
for p in ("phase0i", "phase0h", "phase0f", "phase0e", "phase0dr"):
    sys.path.insert(0, str(R / "scripts" / p))

from solder_model import (CREEP_DATA, DATA_TEMPS, GAROFALO, fit_norton_data,   # noqa: E402
                          norton_at, sat_stress_of_T, sigma0_of_T)
from zarch import (GAN_HS_UM, GAN_LS_UM, TSV_DEMONSTRATED_AR, embedded_cell_um,  # noqa: E402
                   path_for, realizable, tsv_current, tsv_rail)

NON_EMBEDDED = ["ARCH_Z2_BACKSIDE", "ARCH_Z4_POWER_DIE", "ARCH_Z5_2P5D_LATERAL"]


# ------------------------------------------------------------------ DEFECT #33
def test_embedded_is_the_only_architecture_component_height_constrains():
    """The heart of DEFECT #33. If one rule is applied to all, this fails."""
    thin = 0.30
    assert not realizable("ARCH_Z1_EMBEDDED", thin).feasible
    for a in NON_EMBEDDED:
        assert realizable(a, thin).feasible, a


def test_embedded_bound_matches_the_sourced_component_stack():
    t = embedded_cell_um("nominal")
    assert t == pytest.approx(500.0 + GAN_LS_UM + 100.0 + 20.0)
    assert realizable("ARCH_Z1_EMBEDDED", 1.5).h_sub_min_um == pytest.approx(t + 50.0)
    assert realizable("ARCH_Z1_EMBEDDED", 1.276).feasible
    assert not realizable("ARCH_Z1_EMBEDDED", 1.275).feasible


def test_non_embedded_bound_is_the_source_demonstrated_tsv_layer():
    for a in NON_EMBEDDED:
        r = realizable(a, 1.0)
        assert r.h_sub_min_um == pytest.approx(300.0), a
        assert r.components_in_substrate == [], a
    assert TSV_DEMONSTRATED_AR == pytest.approx(10.0)


def test_the_two_rules_are_actually_different():
    """A regression that quietly unified the rules would make these equal."""
    a = realizable("ARCH_Z1_EMBEDDED", 1.5).h_sub_min_um
    b = realizable("ARCH_Z2_BACKSIDE", 1.5).h_sub_min_um
    assert a > 4 * b


def test_high_side_gan_is_not_counted_inside_the_substrate():
    """June-2026: the HS device is flip-chipped to the RDL BELOW the substrate."""
    assert GAN_HS_UM > 0
    assert embedded_cell_um("nominal") < 500.0 + GAN_LS_UM + GAN_HS_UM


# ------------------------------------------------------------------ rail assignment
def test_the_tsv_rail_is_architecture_specific():
    assert tsv_rail("ARCH_Z2_BACKSIDE") == "LV"
    for a in ("ARCH_Z1_EMBEDDED", "ARCH_Z4_POWER_DIE", "ARCH_Z5_2P5D_LATERAL"):
        assert tsv_rail(a) == "HV", a


def test_backside_puts_the_full_load_current_on_the_vias():
    assert tsv_current("ARCH_Z2_BACKSIDE") == pytest.approx(1000.0)
    assert tsv_current("ARCH_Z1_EMBEDDED") == pytest.approx(1000.0 / 48.0 / 0.889, rel=1e-3)
    assert tsv_current("ARCH_Z2_BACKSIDE") / tsv_current("ARCH_Z1_EMBEDDED") > 40


@pytest.mark.parametrize("arch", ["ARCH_Z1_EMBEDDED", "ARCH_Z2_BACKSIDE",
                                  "ARCH_Z4_POWER_DIE", "ARCH_Z5_2P5D_LATERAL"])
def test_every_path_converts_exactly_once_and_ends_low_voltage(arch):
    segs = path_for(arch)
    assert sum(1 for s in segs if s.tier == "converter") == 1, arch
    i = next(k for k, s in enumerate(segs) if s.tier == "converter")
    assert all(s.rail == "HV" for s in segs[:i]), arch
    assert all(s.rail == "LV" for s in segs[i + 1:]), arch


def test_rejected_architectures_have_no_power_path():
    with pytest.raises(ValueError):
        path_for("ARCH_Z3_TOPSIDE")


# ------------------------------------------------------------------ material model
def test_creep_card_is_fitted_to_measured_points_not_to_a_fitted_law():
    for T in DATA_TEMPS:
        f = fit_norton_data(T)
        assert f["n_points"] >= 4, T
        assert f["rms_rel_error_pct"] < 15.0, (T, f["rms_rel_error_pct"])


def test_fitted_card_reproduces_the_published_activation_energy():
    """The independent cross-check: literature Garofalo Q is 62-65 kJ/mol."""
    q = norton_at(100.0)["arrhenius_Q_J_per_mol"] / 1000.0
    lit = [GAROFALO[k]["Q"] / 1000.0 for k in GAROFALO]
    assert min(lit) - 8 < q < max(lit) + 8, q


def test_yield_cross_check_against_an_independent_measurement():
    """Paska et al. 2024 measured SAC305 Rp0.2 = 23.3-25.6 MPa at room temperature."""
    assert 23.3 <= sigma0_of_T(25.0) <= 25.6


def test_yield_and_creep_move_the_physically_correct_way_with_temperature():
    assert sigma0_of_T(25.0) > sigma0_of_T(125.0)
    assert sat_stress_of_T(25.0) > sigma0_of_T(25.0)          # hardening is positive
    r25 = norton_at(25.0); r125 = norton_at(125.0)
    assert r125["A"] * 10 ** r125["n"] > 100 * r25["A"] * 10 ** r25["n"]


def test_material_card_is_single_alloy():
    d = yaml.safe_load((R / "results/phase0i/reliability_material_model.yaml").read_text())
    assert "SAC305" in d["meta"]["alloy"]
    rej = d["creep"]["rejected_alternatives"]
    assert any("SnAgCuCe" in k for k in rej)
    assert any("SAC405" in k for k in rej)


def test_creep_validity_window_is_declared_and_matches_the_data():
    d = yaml.safe_load((R / "results/phase0i/reliability_material_model.yaml").read_text())
    lo, hi = d["creep"]["measured_stress_range_MPa"]
    assert lo == pytest.approx(min(s for _, s, _ in CREEP_DATA))
    assert hi == pytest.approx(max(s for _, s, _ in CREEP_DATA))


def test_no_lifetime_is_claimed_anywhere():
    """Sec.20: no N_f may be predicted without an admissible life law."""
    d = yaml.safe_load((R / "results/phase0i/reliability_material_model.yaml").read_text())
    assert any("fatigue LIFE law" in o or "N_f" in o for o in d["open_items"])
    st = yaml.safe_load((R / "results/CURRENT_SCIENTIFIC_STATUS.yaml").read_text())
    assert st["mechanical_layer_status"]["lifetime_criterion"]["status"] == "NOT_AVAILABLE"


def test_metric_predeclaration_exists_and_forbids_a_corner_maximum():
    t = (R / "results/phase0i/local_metric_predeclaration.md").read_text()
    assert "NONE ADMITTED" in t
    assert "corner exclusion band" in t
    assert "volume" in t.lower()
