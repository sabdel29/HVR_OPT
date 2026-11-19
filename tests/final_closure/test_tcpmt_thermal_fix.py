"""TCPMT revision --- thermal-model corrections (cold plate, coolant, converter cards, die).

Guards on: the three-wall Nusselt fit with the SHORT wall adiabatic and its agreement with the
matched conjugate CFD; water properties at the bulk mean temperature; the caloric correction
in production; the equal-rise flow rule of a second plate and its pumping; the converter-tier
cards (bounds ordered, both designs evaluated, the record matching the code); the die
statistics; the legacy settings kept as variants."""
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
CARDS = R / "research" / "tcpmt_revision" / "converter_cards.json"


# ------------------------------------------------------------------ cold plate
def test_nusselt_is_the_short_wall_adiabatic_h1_fit():
    import cooling as C
    assert C.nu_h1_3wall_short_adiabatic(6.0) == pytest.approx(6.3226, abs=1e-3)
    assert C.nu_h1_3wall_short_adiabatic(1.0) == pytest.approx(3.556, abs=0.01)
    assert C.nu_h1_3wall_short_adiabatic(1e6) == pytest.approx(8.235, abs=1e-3)
    assert C.NU_MODEL == "H1_3wall_short_adiabatic"
    assert C.nu_lam(50 / 300) == pytest.approx(6.3226, abs=1e-3)
    # the superseded table is the LONG-wall-adiabatic family (limit 5.385), kept as an option
    assert C.nu_lam(0.0, model="legacy_3w_table") == pytest.approx(5.385)
    with pytest.raises(ValueError):
        C.nu_h1_3wall_short_adiabatic(0.5)


def test_friction_polynomial_limits():
    import cooling as C
    assert C.f_re(1.0) == pytest.approx(56.91, abs=0.02)
    assert C.f_re(0.0) == pytest.approx(96.0)


def test_water_at_the_bulk_mean_temperature():
    import cooling as C
    from cooling_production import CANDIDATES
    p = C.water_props(30.0)
    assert p["mu"] == pytest.approx(7.972e-4, rel=1e-3)
    assert p["k"] == pytest.approx(0.6154, rel=1e-3)
    s = CANDIDATES["TOP_SI_MICROCHANNEL_27"].channel().solve(1000.0)
    assert s["T_bulk_mean_C"] == pytest.approx(25.0 + 1000.0 / (2 * 27e-3 * 4180.0), abs=0.05)
    assert s["props"]["T_C"] == pytest.approx(s["T_bulk_mean_C"])
    assert s["h_channel_W_m2K"] == pytest.approx(s["Nu"] * s["props"]["k"]
                                                 / (s["D_h_um"] * 1e-6), rel=1e-12)
    assert s["Re"] < 2300
    # pressure drop = fully developed + entrance + plenum, pumping = dp V
    assert s["dp_kPa"] == pytest.approx(s["dp_fd_kPa"] + s["dp_entrance_kPa"]
                                        + s["dp_plenum_kPa"], rel=1e-12)
    assert s["pump_W"] == pytest.approx(s["dp_kPa"] * 1e3 * 27e-3 / s["props"]["rho"],
                                        rel=1e-12)


def test_cfd_agreement_of_the_corrected_correlation():
    import cooling as C
    cc = C.cfd_comparison()
    assert abs(cc["dT_base_mean_rel_diff"]) < 0.02, cc["dT_base_mean_rel_diff"]
    outlet = cc["along_channel"][-1]
    assert abs(outlet["rel_diff_corr_vs_cfd"]) < 0.10


def test_caloric_correction_is_production():
    import final_closure_physical_etm as E
    from cooling_production import CANDIDATES
    c = CANDIDATES[E.COOLER]
    assert E.TOP_PLATE_COEFF == "local"
    s = c.compact(1000.0)
    assert E.top_plate_h(c, 1000.0) == pytest.approx(
        1.0 / ((s["R_conv_K_W"] + s["R_base_K_W"]) * (22.36e-3) ** 2), rel=1e-9)
    assert c.h_local(1000.0) > c.h_uniform(1000.0)


def test_equal_rise_rule_and_pumping_per_plate():
    import final_closure_physical_etm as E
    from cooling_production import CANDIDATES, equal_rise_flow_g_s
    c = CANDIDATES[E.COOLER]
    assert E.BOTTOM_PLATE_RULE == "equal_rise"
    assert equal_rise_flow_g_s(180.0, 900.0, 27.0) == pytest.approx(5.4)
    lo, hi = c.plate_at_flow(5.0, 180.0), c.plate_at_flow(10.0, 360.0)
    ratio = hi["P_pump_hydraulic_W"] / lo["P_pump_hydraulic_W"]
    assert 4.0 <= ratio <= 8.0            # laminar: dp ~ m (+ m^2 minor terms), P ~ m dp
    assert lo["dT_coolant_K"] == pytest.approx(hi["dT_coolant_K"], rel=1e-3)
    rec = E.plate_records(c, 900.0, [({"plate": True, "rule": "equal_rise", "layer": "b",
                                       "label": "", "h_W_m2K": 1e5}, 180.0)])
    assert rec["plates"][1]["m_dot_g_s"] == pytest.approx(27.0 * 180.0 / 900.0)
    assert rec["P_pump_hydraulic_total_W"] == pytest.approx(
        rec["plates"][0]["P_pump_hydraulic_W"] + rec["plates"][1]["P_pump_hydraulic_W"])


def test_legacy_settings_are_variants():
    import final_closure_sensitivity as S
    for v in ("conv_k_legacy", "nu_legacy_table", "props_legacy_50C", "plate_caloric_legacy",
              "z1_bottom_plate_tim_fullflow", "z2_cooled_tim_fullflow",
              "z3_plate_tim_fullflow", "z2_cooled_fullflow", "z3_plate_fullflow",
              "wall_viscosity"):
        assert v in S.VARIANTS, v


# ------------------------------------------------------------------ converter cards
@pytest.fixture(scope="module")
def cards():
    return json.loads(CARDS.read_text())


def test_cards_record_both_designs_with_ordered_bounds(cards):
    assert set(cards["designs"]) == {"N3K3K_A2_49", "N4K4K_A2_36"}
    for key, d in cards["designs"].items():
        for name, c in d["cards"].items():
            b, mech = c["derivation"]["bounds"], c["derivation"]["mechanical"]
            kz = c["k_ortho"]["value"][2]
            assert b["kz_reuss"] - 1e-9 <= kz <= b["kz_voigt"] + 1e-9, (key, name)
            lo, up = b["kxy_series_parallel"]
            assert b["kxy_reuss"] - 1e-9 <= lo <= up <= b["kxy_voigt"] + 1e-9, (key, name)
            assert mech["E_reuss_MPa"] <= c["E"]["value"] <= mech["E_voigt_MPa"], (key, name)
            assert c["cte"]["value"] == pytest.approx(mech["cte_turner_per_K"])


def test_cards_are_functions_of_the_tier_contents(cards):
    d49, d36 = cards["designs"]["N3K3K_A2_49"], cards["designs"]["N4K4K_A2_36"]
    p49 = d49["cards"]["conv_gan_hs"]["derivation"]
    p36 = d36["cards"]["conv_gan_hs"]["derivation"]
    assert p49["dies_per_cell"] == 3 and p36["dies_per_cell"] == 4
    assert p36["part"] == "EPC2057"
    assert not p49["packing"]["fits"]                 # 3 x EPC2014C + 50 um: 2.89 mm > 2.37 mm
    assert p36["packing"]["fits"] and p36["packing"]["best_layout"] == "pinwheel"
    assert d36["cards"]["conv_ind_cout"]["derivation"]["area_fractions"]["inductors"] == \
        pytest.approx(4 * 1.0 / 7.94, rel=1e-6)
    # a real MLCC tier: k of a few W/mK, CTE ~ 10-13 ppm/K
    for d in (d49, d36):
        a1 = d["cards"]["conv_cfly_a1"]
        assert 2.0 < a1["k_ortho"]["value"][2] < 7.0
        assert 10e-6 < a1["cte"]["value"] < 13.5e-6


def test_cards_record_matches_the_code(cards):
    import tcpmt_converter_cards as CC
    live = CC.cards_for(CC.TierContents.from_design())
    for name, c in live.items():
        rec = cards["designs"]["N3K3K_A2_49"]["cards"][name]
        assert c["k_ortho"]["value"] == pytest.approx(rec["k_ortho"]["value"], rel=1e-12)
        assert c["E"]["value"] == pytest.approx(rec["E"]["value"], rel=1e-12)
        assert c["cte"]["value"] == pytest.approx(rec["cte"]["value"], rel=1e-12)


def test_inductor_geometry_reproduces_the_papers_dcr():
    import tcpmt_converter_cards as CC
    assert CC.inductor_envelope()["dcr_from_dimensions_mohm"] == pytest.approx(5.0, rel=0.1)


# ------------------------------------------------------------------ mesh-level checks
@pytest.fixture(scope="module")
def z1_build():
    import final_closure_physical_etm as E
    return E.build("Z1", 1.1, (1, 1))


def test_converter_tiers_carry_the_derived_cards(z1_build):
    m, mats, st, tiles, info = z1_build
    mat = np.array(m.elem_material, dtype=object)
    lay = np.array(m.elem_layer, dtype=object)
    for tier, card in (("gan_hs", "conv_gan_hs"), ("gan_ls", "conv_gan_ls"),
                       ("flying_caps", "conv_cfly_a0"), ("inductor_plus_cout", "conv_ind_cout")):
        sel = np.array([tier in str(x) for x in lay])
        assert set(mat[sel]) == {card, "underfill_homog"}, tier
        assert mats[card].k_ortho is not None


def test_die_statistics(z1_build):
    import final_closure_physical_etm as E
    m = z1_build[0]
    t = m.nodes[:, 2].copy()                           # T = z: the die top is its maximum
    d = E.die_stats(m, t, "Z1")
    die = [L for L in m.layers if L.name == "die"][0]
    assert d["die_T_max_C"] == pytest.approx(die.z1)
    assert die.z0 < d["die_T_mean_C"] < die.z1
