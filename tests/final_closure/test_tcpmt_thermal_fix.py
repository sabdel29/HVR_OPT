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
    # pressure drop = fully developed + entrance + plenum (+ the manifold's turns and headers,
    # round 3), pumping = dp V
    assert s["dp_kPa"] == pytest.approx(s["dp_fd_kPa"] + s["dp_entrance_kPa"]
                                        + s["dp_plenum_kPa"] + s["dp_turns_kPa"]
                                        + s["dp_header_kPa"], rel=1e-12)
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
              "wall_viscosity", "conv_gap_legacy"):
        assert v in S.VARIANTS, v


# ------------------------------------------------------------------ converter cards
@pytest.fixture(scope="module")
def cards():
    return json.loads(CARDS.read_text())


def test_cards_record_every_design_with_ordered_bounds(cards):
    """TCPMT round 3: one card per MIXED tier for every design of the design record."""
    import design_record as DR
    assert set(cards["designs"]) == set(DR.keys())
    for key, d in cards["designs"].items():
        assert set(d["cards"]) == {"conv_" + t["name"].split("_")[0] for t in DR.tiers(key)}
        for name, c in d["cards"].items():
            b, mech = c["derivation"]["bounds"], c["derivation"]["mechanical"]
            kz = c["k_ortho"]["value"][2]
            assert b["kz_reuss"] - 1e-9 <= kz <= b["kz_voigt"] + 1e-9, (key, name)
            lo, up = b["kxy_series_parallel"]
            assert b["kxy_reuss"] - 1e-9 <= lo <= up <= b["kxy_voigt"] + 1e-9, (key, name)
            assert mech["E_reuss_MPa"] <= c["E"]["value"] <= mech["E_voigt_MPa"], (key, name)
            assert c["cte"]["value"] == pytest.approx(mech["cte_turner_per_K"])


def test_cards_are_functions_of_the_tier_contents(cards):
    """A tier card follows what the tier holds: the parts it lists, their areas in the cell,
    the gap above shorter parts, and the capacitor height (thin vs rated)."""
    import design_record as DR
    d = cards["designs"]["m36"]
    for t in DR.tiers("m36"):
        der = d["cards"]["conv_" + t["name"].split("_")[0]]["derivation"]
        assert der["parts"] == t["parts"] and der["tier_um"] == t["height_um"]
        assert set(der["prisms"]) == set(t["parts"])
    t1 = d["cards"]["conv_tier1"]["derivation"]                 # 2 x EPC2014C + 2 x 0603
    assert t1["prisms"]["gan_hs"]["gap_um"] == pytest.approx(1000.0 - 685.0)
    assert t1["prisms"]["cap_fly"]["gap_um"] == pytest.approx(1000.0 - 830.0)
    # the thin-capacitor sensitivity: the same contents in a 685-um tier, no gap above the
    # dies; with the legacy encapsulant gap it conducts better than the rated 1000-um tier
    thin = cards["designs"]["m36thin"]["cards"]["conv_tier1"]
    assert thin["derivation"]["tier_um"] == 685.0
    assert thin["derivation"]["prisms"]["gan_hs"]["gap_um"] == 0.0
    leg = {k: cards["designs"][k]["legacy_gap_encapsulant_summary"]["conv_tier1"]["kz"]
           for k in ("m36", "m36thin")}
    assert leg["m36thin"] > leg["m36"]
    # inductor tiers carry their output posts; a tier without inductors has none
    t4 = d["cards"]["conv_tier4"]["derivation"]
    assert t4["area_fractions"]["posts"] > 0 and t1["area_fractions"]["posts"] == 0


def test_gap_posts_bridge_parts_shorter_than_their_tier(cards):
    """Review round 3: a part shorter than its tier is bridged to the RDLs by copper posts on
    its terminals (production: the die's datasheet land pattern, the MLCC's electrode bands,
    the inductor's current at J_POST); the range over the post bases is ordered and recorded
    for the uncertainty step; the encapsulant cap is the legacy card."""
    import tcpmt_converter_cards as CC
    land = {p: CC.pad_area_mm2(CC.DEVICES[p], "land_um") / (CC.DEVICES[p]["die_mm"][0]
                                                             * CC.DEVICES[p]["die_mm"][1])
            for p in ("EPC2014C", "EPC2055")}
    assert land["EPC2014C"] == pytest.approx((3 * 180 * 814 + 2 * 180 * 296) * 1e-6
                                             / (1.702 * 1.087))
    assert land["EPC2055"] == pytest.approx((230 * 280 + 230 * 805 + 2 * 230 * 1155
                                             + 2 * 230 * 1330) * 1e-6 / 3.75)
    assert cards["gap_model"] == "posts" and cards["post_basis"] == "land"
    for key, d in cards["designs"].items():
        for name, c in d["cards"].items():
            der, b = c["derivation"], c["derivation"]["bounds"]
            kz, kxy = c["k_ortho"]["value"][2], c["k_ortho"]["value"][0]
            lo, hi = b["kz_post_range"]
            assert lo - 1e-9 <= kz <= hi + 1e-9, (key, name)
            assert b["kxy_post_range"][0] - 1e-9 <= kxy <= b["kxy_post_range"][1] + 1e-9
            assert b["kz_gap_encapsulant_legacy"] <= lo + 1e-9, (key, name)
            for cls, g in der["gap_posts"].items():
                assert g["gap_um"] > 0 and g["post_fraction_of_part"] > 0, (key, name, cls)
            if not der["gap_posts"]:            # nothing shorter than the tier: no change
                assert b["kz_gap_encapsulant_legacy"] == pytest.approx(kz)
    t1 = cards["designs"]["m36"]["cards"]["conv_tier1"]["derivation"]["gap_posts"]
    assert t1["gan_hs"]["post_fraction_of_part"] == pytest.approx(land["EPC2014C"])
    assert t1["cap_fly"]["post_mm2_per_part"] == pytest.approx(
        2 * CC.CF_0603["W_mm"] * CC.CF_0603["band_mm"])


def test_legacy_gap_cards_are_the_cards_before_review_round_3(cards):
    """GAP_MODEL 'encapsulant' (variant conv_gap_legacy) reproduces the recorded legacy
    summary, and on a tier with no gap equals the production card."""
    import tcpmt_converter_cards as CC
    import design_record as DR
    for key in DR.keys():
        leg = CC.mixed_cards(key, gap="encapsulant")
        for name, c in leg.items():
            rec = cards["designs"][key]["legacy_gap_encapsulant_summary"][name]
            assert c["k_ortho"]["value"][2] == pytest.approx(rec["kz"], rel=1e-12)
            assert c["k_ortho"]["value"][0] == pytest.approx(rec["kx"], rel=1e-12)
    m36 = cards["designs"]["m36"]["legacy_gap_encapsulant_summary"]
    assert m36["conv_tier1"]["kz"] == pytest.approx(1.83, abs=0.01)   # the smoke-test card


def test_cards_record_matches_the_code(cards):
    """The committed record equals the live cards of every design (the record's tiers)."""
    import tcpmt_converter_cards as CC
    import design_record as DR
    for key in DR.keys():
        live = CC.mixed_cards(key)
        for name, c in live.items():
            rec = cards["designs"][key]["cards"][name]
            assert c["k_ortho"]["value"] == pytest.approx(rec["k_ortho"]["value"], rel=1e-12)
            assert c["E"]["value"] == pytest.approx(rec["E"]["value"], rel=1e-12)
            assert c["cte"]["value"] == pytest.approx(rec["cte"]["value"], rel=1e-12)


def test_inductor_geometry_reproduces_the_papers_dcr():
    import tcpmt_converter_cards as CC
    assert CC.inductor_envelope()["dcr_from_dimensions_mohm"] == pytest.approx(5.0, rel=0.1)


def test_pqfn_is_modelled_as_published(cards):
    """Review round 3: the EPC2366 (m25) is a PQFN with its die EXPOSED on top (datasheet
    p. 9), not a die under a mould cap: two parallel columns over the package (leadframe +
    joint + silicon under the 2.5 x 1.8 mm die, leadframe + mould beside it), the published
    land pattern for the terminals and posts, the silicon path at the published R_thJC and the
    bottom path checked against R_thJB."""
    import tcpmt_converter_cards as CC
    dev = CC.DEVICES["EPC2366"]
    q = CC.qfn_construction("EPC2366")
    assert dev["qfn"]["exposed_die_mm"] == (2.5, 1.8) and q["leadframe_um"] == 200.0
    assert q["leadframe_um"] + q["joint_um"] + q["silicon_um"] == dev["overall_um"] == 700.0
    # the published land pattern: 0.45 x 2.90 bars (x2) and the rest of the five pads
    assert q["land_mm2"] == pytest.approx(6.2727, abs=1e-3)
    assert q["land_in_outline_mm2"] < q["land_mm2"] < q["A_package_mm2"]
    assert CC.pad_area_mm2(dev, "land_um") == pytest.approx(q["land_mm2"], rel=1e-9)
    p = CC._qfn_prism("EPC2366", 700.0)
    chk = p["qfn"]["check_vs_datasheet"]
    assert chk["R_top_card_K_W"] == pytest.approx(dev["qfn"]["R_jc_K_W"], rel=1e-9)
    assert chk["R_bottom_card_K_W"] == pytest.approx(dev["qfn"]["R_jb_K_W"], rel=0.15)
    assert p["kz_layers"]["column_under_die"] > 50 * p["kz_layers"]["column_beside_die"]
    assert "qfn_body" not in CC.PHASES and "mould" in CC.PHASES
    m25 = cards["designs"]["m25"]["cards"]
    for name, c in m25.items():
        der = c["derivation"]
        if der["parts"] == {"gan_ls": 1}:              # the EPC2366 tiers (no gap above it)
            assert der["prisms"]["gan_ls"]["qfn"]["construction"].startswith("exposed die")
            assert c["k_ortho"]["value"][2] > 20.0      # the mould-cap body gave 1.62 W/mK
            assert der["bounds"]["kz_gap_encapsulant_legacy"] == pytest.approx(
                c["k_ortho"]["value"][2])
    # in a taller tier the posts go on its published land pattern
    tall = CC._qfn_prism("EPC2366", 1000.0, CC.post_area_mm2(
        "gan_ls", CC.MixedContents.from_record("m25"), "EPC2366", "land")[0])
    assert tall["post_mm2"] == pytest.approx(q["land_mm2"])


def test_tier_orders_follow_the_declared_rule():
    """Review round 3: every design's tier order is the declared rule's choice on the post
    cards (a sensitivity keeps its base design's order), with the runner-up and the
    single-face sensitivity recorded; tier names follow the order."""
    import design_record as DR
    to = json.loads((R / "research" / "tcpmt_revision" / "tier_order.json").read_text())
    for k in DR.keys():
        e = DR.get(k)
        t = e["tier_order"]
        rec = to["designs"][k]
        rank = rec["rule_ranking"]
        assert [r["rank"] for r in rank] == list(range(1, len(rank) + 1))
        assert t["n_orders"] == len(rank) == rec["n_decided_orders"]
        if e["role"] != "sensitivity":
            assert t["rank_by_rule"] == 1 and t["order_input_to_output"] == rank[0]["order"]
        ru = t["runner_up"]
        assert ru["order_input_to_output"] != t["order_input_to_output"]
        assert ru["heat_path_above_chosen_K"] == pytest.approx(
            ru["heat_path_K"] - t["heat_path_K"])
        sf = t["single_face_sensitivity"]
        assert sf["chosen_order_worst_via_ar"] == t["worst_via_ar_single_face"]
        assert sf["rule_choice_worst_via_ar"] <= sf["chosen_order_worst_via_ar"] + 1e-12
        assert [x["name"] for x in e["tiers"]] == [DR.tier_name(i, x["parts"]) for i, x
                                                   in enumerate(e["tiers"], start=1)]
    # the production design: the post cards swap the record's earlier T2 / T3
    assert DR.get("m36")["tier_order"]["order_input_to_output"] == (
        "2gan_hs+2cap_fly | 1gan_ls+1inductor | 1gan_hs+1gan_ls | 1gan_ls+2inductor")


# ------------------------------------------------------------------ mesh-level checks
@pytest.fixture(scope="module")
def z1_build():
    import final_closure_physical_etm as E
    return E.build("Z1", 1.1, (1, 1))


def test_converter_tiers_carry_the_derived_cards(z1_build):
    """Every mixed tier of the mesh carries its own card inside the cells (TCPMT round 3)."""
    import design_record as DR
    m, mats, st, tiles, info = z1_build
    mat = np.array(m.elem_material, dtype=object)
    lay = np.array(m.elem_layer, dtype=object)
    for t in DR.tiers():
        card = "conv_" + t["name"].split("_")[0]
        sel = np.array([str(x).endswith("_" + t["name"]) for x in lay])
        assert sel.any(), t["name"]
        assert set(mat[sel]) == {card, "underfill_homog"}, t["name"]
        assert mats[card].k_ortho is not None


def test_die_statistics(z1_build):
    import final_closure_physical_etm as E
    m = z1_build[0]
    t = m.nodes[:, 2].copy()                           # T = z: the die top is its maximum
    d = E.die_stats(m, t, "Z1")
    die = [L for L in m.layers if L.name == "die"][0]
    assert d["die_T_max_C"] == pytest.approx(die.z1)
    assert die.z0 < d["die_T_mean_C"] < die.z1
