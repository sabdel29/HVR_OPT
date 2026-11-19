"""Switch-voltage rule, output-capacitance loss and tier packing (TCPMT revision, phase 1).

Same pattern as the flying-capacitor rule (test_capacitor_rule.py): the corrected rules are the
engine defaults (switch derating 0.9, corrected C_OSS, tier packing with a 50-um keep-out), each
published behaviour stays behind its flag (HVR_SW_RULE=legacy, HVR_COSS_RULE=legacy,
HVR_PACK_RULE=off; with HVR_CAP_RULE=legacy they reproduce the published results), and the
production lineage pins all of them to the published behaviour.
"""
import csv
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

R = Path(__file__).resolve().parents[2]
SIVR = R / "Scalable_Integrated_VR"
sys.path.insert(0, str(SIVR / "src"))
sys.path.insert(0, str(R / "scripts" / "phase0d"))

import HVR_FULL_OPT_EPC_V2 as H  # noqa: E402

V_IN, V_OUT = 48.0, 1.0
F49 = 805170.3343770516               # the 49-cell design's switching frequency
I49 = 1000.0 / 49


@pytest.fixture(scope="module")
def table():
    cwd = os.getcwd()
    os.chdir(SIVR)
    try:
        return H.load_epc_devices("EPC-Product-Table.csv", V_gs_op=5.0)
    finally:
        os.chdir(cwd)


@pytest.fixture(scope="module")
def dev(table):
    return {r["PartNumber"]: H.row_to_device(r) for _, r in table.iterrows()}


def _arch(n, k):
    ka = math.ceil(k / 2)
    return H.VRArchitecture(N=n, K=k, K_A=ka, B_array=H.generate_B_array(n, k, ka),
                            D=n * V_OUT / V_IN, component_count=2 * n + 2 * k - 1)


def _synthetic(vds):
    """A one-row device table with the given V_DS,max (ample current and gate rating)."""
    return pd.DataFrame({"PartNumber": [f"X{vds}"], "VDSmax": [vds], "VGSmax": [6.0],
                         "R_DS_ON": [0.01], "Q_G": [1e-9], "Q_GD": [1e-10], "Q_OSS": [1e-9],
                         "C_G": [2e-10], "C_OSS": [1e-11], "ID_A": [100.0],
                         "footprint_mm2": [1.0]})


# ---------------------------------------------------------------- switch stress per N
@pytest.mark.parametrize("n, s1, stacked", [(2, 24.0, 48.0), (3, 16.0, 32.0), (4, 12.0, 36.0),
                                            (5, 9.6, 38.4), (6, 8.0, 40.0)])
def test_stress_values_per_n(n, s1, stacked):
    v1, vs, vls = H.switch_stresses(n, V_IN)
    assert v1 == pytest.approx(s1) and vls == pytest.approx(s1)       # S1 and low side: V_in/N
    assert vs == pytest.approx(stacked)                               # max(N-1, 2) V_in/N
    assert H.stacked_swing(n, V_IN) == pytest.approx(2 * V_IN / n)    # ladder node swing


def _with_derating(d, fn):
    old = H.SW_V_DERATING
    try:
        H.SW_V_DERATING = d
        return fn()
    finally:
        H.SW_V_DERATING = old


@pytest.mark.parametrize("derating, rated", [(0.8, 40.0),          # EPC2014C at 32 V
                                             (0.9, 32.0 / 0.9),    # the default derating
                                             (0.95, 32.0 / 0.95)])
def test_rating_exactly_at_threshold_passes_n3(derating, rated):
    # the stacked stress at N = 3 is 2 V_in/3 = 32 V; a rating exactly at 32 V / derating passes
    a = _arch(3, 3)
    hs = _with_derating(derating, lambda: H.filter_candidate_devices(
        _synthetic(rated), a, V_IN, V_OUT, 5.0, I49, 1, rule="stress")[0])
    assert len(hs) == 1
    hs = _with_derating(derating, lambda: H.filter_candidate_devices(
        _synthetic(rated - 1e-6), a, V_IN, V_OUT, 5.0, I49, 1, rule="stress")[0])
    assert hs == []


@pytest.mark.parametrize("derating", [0.8, 0.9, 0.95])
def test_real_parts_per_n(table, derating):
    names = lambda devs: {d.part_number for d in devs}          # noqa: E731
    flt = lambda a, i, rule="stress": _with_derating(            # noqa: E731
        derating, lambda: H.filter_candidate_devices(table, a, V_IN, V_OUT, 5.0, i, 1, rule=rule))
    i = 1000.0 / 76                                             # the published N=2 optimum
    hs2, ls2 = flt(_arch(2, 2), i)
    assert "EPC2014C" not in names(hs2)                         # 48 V stacked stress, 40-V part
    assert min(d.VDSmax for d in hs2) * derating >= 48.0
    assert min(d.VDSmax for d in ls2) * derating >= 24.0
    assert "EPC2014C" in names(flt(_arch(2, 2), i, "legacy")[0])    # the published admission
    hs3, ls3 = flt(_arch(3, 3), I49)
    assert {"EPC2014C"} <= names(hs3) and {"EPC2057"} <= names(ls3)   # the 49-cell parts
    hs4, _ = flt(_arch(4, 4), I49)                              # 3 V_in/4 = 36 V
    assert ("EPC2014C" in names(hs4)) is (derating >= 0.9)      # 40 V x 0.9 = 36 V exactly


def test_low_side_rule():
    a = _arch(3, 3)                                             # V_in/N = 16 V -> 20 V rating
    for vds, ok in ((20.0, True), (15.0, False)):
        _, ls = H.filter_candidate_devices(_synthetic(vds), a, V_IN, V_OUT, 5.0, I49, 1,
                                           rule="stress")
        assert bool(ls) is ok
    _, ls = H.filter_candidate_devices(_synthetic(15.0), a, V_IN, V_OUT, 5.0, I49, 1,
                                       rule="legacy")
    assert ls                                                   # legacy: V_DS,max >= V_out


def test_derating_override():
    old = H.SW_V_DERATING
    try:
        H.SW_V_DERATING = 1.0
        for vds, ok in ((48.0, True), (40.0, False)):
            hs, _ = H.filter_candidate_devices(_synthetic(vds), _arch(2, 2), V_IN, V_OUT, 5.0,
                                               10.0, 1, rule="stress")
            assert bool(hs) is ok
    finally:
        H.SW_V_DERATING = old


def test_legacy_filter_reproduces_published_expression(table):
    for n, k in ((2, 2), (3, 2), (3, 3), (4, 2), (4, 4), (5, 3), (6, 4)):
        a = _arch(n, k)
        for i in (8.33, 13.16, 20.41, 27.78):
            mb = max(a.B_array)
            hs, ls = H.filter_candidate_devices(table, a, V_IN, V_OUT, 5.0, i, mb,
                                                rule="legacy")
            ref_hs = table[(table["VDSmax"] >= V_IN / n) & (table["VGSmax"] >= 5.0)
                           & (table["ID_A"] >= i / n)]["PartNumber"].tolist()
            ref_ls = table[(table["VDSmax"] >= V_OUT) & (table["VGSmax"] >= 5.0)
                           & (table["ID_A"] >= i * mb / n)]["PartNumber"].tolist()
            assert [d.part_number for d in hs] == ref_hs
            assert [d.part_number for d in ls] == ref_ls


def test_engine_defaults():
    """The corrected rules are the defaults (authors' decision); each legacy one is a flag."""
    if "HVR_SW_RULE" not in os.environ:
        assert H.SW_RULE == "stress"
    if "HVR_SW_DERATING" not in os.environ:
        assert H.SW_V_DERATING == 0.9
    if "HVR_CAP_DERATING" not in os.environ:
        assert H.CAP_V_DERATING == 0.8
    if "HVR_COSS_RULE" not in os.environ:
        assert H.COSS_RULE == "corrected"
    if "HVR_PACK_RULE" not in os.environ:
        assert H.pack_enabled() and H.PACK_KEEPOUT_UM == 50.0
    assert not H.pack_enabled("off") and H.pack_enabled("on")


# ---------------------------------------------------------------- output capacitance
def test_qoss_table_value_at_half_rating_and_sqrt_law(dev):
    for p in ("EPC2014C", "EPC2057", "EPC2090"):
        d = dev[p]
        assert H.q_oss_at(d, 0.5 * d.VDSmax) == pytest.approx(d.Q_OSS)
        assert H.q_oss_at(d, 2.0 * d.VDSmax) == pytest.approx(2.0 * d.Q_OSS)   # sqrt(4)
        v = 16.0
        vg = np.linspace(0.0, v, 20001)
        q = np.array([H.q_oss_at(d, x) for x in vg])
        e_num = float(np.sum(0.5 * (vg[1:] + vg[:-1]) * np.diff(q)))          # int v dQ
        assert H.e_oss_at(d, v) == pytest.approx(e_num, rel=1e-3)
        assert H.e_oss_at(d, v) == pytest.approx(H.q_oss_at(d, v) * v / 3.0)
    # table values against the datasheets (Q_OSS at V_DS = V_DS,max / 2)
    assert (dev["EPC2014C"].VDSmax, dev["EPC2014C"].Q_OSS) == (40.0, pytest.approx(4e-9))
    assert (dev["EPC2057"].VDSmax, dev["EPC2057"].Q_OSS) == (50.0, pytest.approx(7.9e-9))


def _loss49(dev, rule):
    old = H.COSS_RULE
    try:
        H.COSS_RULE = rule
        ind = [i for i in H.INDUCTOR_LIBRARY if i.name == "Shared_Core_UIC_250_nH"][0]
        cap = [c for c in H.CAPACITOR_LIBRARY if c.name == "Murata-GCM21-10uF-25V"][0]
        return H.compute_total_loss(_arch(3, 3), H.LossModelInputs(
            hs_device=dev["EPC2014C"], ls_device=dev["EPC2057"], inductor=ind, capacitor=cap,
            I_out=I49, V_out=V_OUT, V_in=V_IN, f_sw=F49))
    finally:
        H.COSS_RULE = old


def test_coss_legacy_hand_case(dev):
    # f/2 [N (Q_OSS/V_DSmax)_HS (V_in/N - V_out)^2 + K (Q_OSS/V_DSmax)_LS V_out^2]
    hand = F49 / 2 * (3 * (4e-9 / 40) * 15.0 ** 2 + 3 * (7.9e-9 / 50) * 1.0 ** 2)
    assert hand == pytest.approx(0.0273653, rel=1e-5)
    assert _loss49(dev, "legacy").p_sw_coss == pytest.approx(hand, rel=1e-12)


def test_coss_corrected_hand_case(dev):
    # N = 3, K = 3, EPC2014C (4 nC at 20 V) / EPC2057 (7.9 nC at 25 V), v1 = 16 V, v2 = 32 V
    q16, q32 = 4e-9 * math.sqrt(16 / 20), 4e-9 * math.sqrt(32 / 20)        # 3.5777, 5.0596 nC
    e16, e32 = q16 * 16 / 3, q32 * 32 / 3                                   # 19.081, 53.970 nJ
    ql = 7.9e-9 * math.sqrt(16 / 25)                                        # 6.32 nC
    e_hs = 3 * e16                                                          # 57.243 nJ
    e_node = 3 * (ql * 16 - ql * 16 / 3)                                    # 202.240 nJ
    e_stk = 2 * (32 * (q32 - q16) - (e32 - e16))                            # 25.067 nJ
    e = e_hs + e_node + e_stk
    assert e == pytest.approx(284.5504e-9, rel=1e-6)
    parts = H.coss_energy_per_period(_arch(3, 3), dev["EPC2014C"], dev["EPC2057"], V_IN)
    assert parts["hs_turn_on"] == pytest.approx(e_hs)
    assert parts["switch_node"] == pytest.approx(e_node)
    assert parts["stacked"] == pytest.approx(e_stk)
    new, old = _loss49(dev, "corrected"), _loss49(dev, "legacy")
    assert new.p_sw_coss == pytest.approx(F49 * e, rel=1e-12)              # 0.2291 W per cell
    assert 49 * new.p_sw_coss == pytest.approx(11.226, abs=2e-3)
    assert new.total_loss - old.total_loss == pytest.approx(new.p_sw_coss - old.p_sw_coss)
    assert new.p_cond == old.p_cond and new.p_sw_hs == old.p_sw_hs


def test_coss_stacked_term_n2_reaches_vin(dev):
    a = _arch(2, 2)
    d = dev["EPC2212"]                                                      # 100 V, 18 nC at 50 V
    e = H.coss_energy_per_period(a, d, d, V_IN)
    q24, q48 = H.q_oss_at(d, 24.0), H.q_oss_at(d, 48.0)
    ref = 1 * (48.0 * (q48 - q24) - (H.e_oss_at(d, 48.0) - H.e_oss_at(d, 24.0)))
    assert e["stacked"] == pytest.approx(ref)
    assert e["hs_turn_on"] == pytest.approx(2 * H.e_oss_at(d, 24.0))


# ---------------------------------------------------------------- packing
def test_epc2057_and_epc2014c_dimensions(dev):
    assert H.part_dims_mm(dev["EPC2057"]) == (1.5, 1.2)        # datasheet die 1500 x 1200 um
    assert H.part_dims_mm(dev["EPC2014C"]) == (1.7, 1.1)       # datasheet die 1702 x 1087 um
    rated = [c for c in H.default_capacitor_library("stress")
             if c.name == "Murata-GRM188D72A105KE01-1uF-100V"][0]
    assert H.part_dims_mm(rated) == (1.6, 0.8)                 # 0603
    ind = [i for i in H.INDUCTOR_LIBRARY if i.name == "Shared_Core_UIC_250_nH"][0]
    assert H.part_dims_mm(ind) == (1.0, 1.0)                   # square of the 1-mm2 footprint


@pytest.mark.parametrize("keep", [0.0, 0.05])
def test_three_epc2014c_do_not_fit_the_49_cell(keep):
    for side in (math.sqrt(5.61), math.sqrt(I49 / 3.5)):        # 2.37 mm; 2.41 mm (budget)
        assert not H.pack_identical(3, 1.7, 1.1, side, keep)
        assert not H.pack_identical(3, 1.5, 1.2, side, keep)     # 3 x EPC2057 neither
        assert H.pack_identical(2, 1.7, 1.1, side, keep)
    # smallest square for three EPC2014C with 50-um keep-out: (1.7 + 0.05) + (1.1 + 0.05)
    assert H.pack_identical(3, 1.7, 1.1, 2.90, 0.05)
    assert not H.pack_identical(3, 1.7, 1.1, 2.89, 0.05)


def test_known_grids_and_keepout():
    assert H.pack_identical(4, 1.0, 1.0, 2.10, 0.05)             # 2 x 1.05
    assert not H.pack_identical(4, 1.0, 1.0, 2.09, 0.05)
    assert H.pack_identical(2, 1.6, 0.8, 1.70, 0.05)             # two 0603 stacked
    assert not H.pack_identical(2, 1.6, 0.8, 1.69, 0.05)
    assert H.pack_identical(0, 9.0, 9.0, 1.0)
    assert not H.pack_identical(1, 2.5, 0.1, 2.4)                # longer than the cell


def test_pinwheel_needs_the_exact_search():
    # four 2.0 x 1.2 parts fit a 3.2 square only as a pinwheel (non-guillotine)
    assert H._guillotine_count(2.0, 1.2, 3.2) == 3
    n0 = H.PACK_STATS["exact_searches"]
    assert H.pack_identical(4, 2.0, 1.2, 3.2, 0.0)
    assert H.PACK_STATS["exact_searches"] == n0 + 1
    assert not H.pack_identical(4, 2.0, 1.2, 3.19, 0.0)


def test_49_cell_tier_verdict(dev):
    a = _arch(3, 3)
    ind = [i for i in H.INDUCTOR_LIBRARY if i.name == "Shared_Core_UIC_250_nH"][0]
    for cap_name, lib in (("Murata-GCM21-10uF-25V", H.CAPACITOR_LIBRARY),
                          ("Murata-GRM188D72A105KE01-1uF-100V",
                           H.default_capacitor_library("stress"))):
        cap = [c for c in lib if c.name == cap_name][0]
        v = H.tier_report(a, dev["EPC2014C"], dev["EPC2057"], ind, cap, math.sqrt(I49 / 3.5))
        assert v["gan_hs"] is False and v["gan_ls"] is False and v["inductor"] is True
        assert v["cap_fly"] is (cap_name.startswith("Murata-GRM188"))   # 0805 pair: 2.6 mm
    assert H._compute_area(a, dev["EPC2014C"], dev["EPC2057"], ind, cap) == pytest.approx(5.61)


def test_pack_screen_inside_the_optimizer(dev):
    """With PACK_RULE on, the 49-cell parts are screened out of N3K3 at M = 49."""
    a = _arch(3, 3)
    ind = [i for i in H.INDUCTOR_LIBRARY if i.name == "Shared_Core_UIC_250_nH"][0]
    cap = [c for c in H.default_capacitor_library("stress")
           if c.name == "Murata-GRM188D72A105KE01-1uF-100V"][0]
    df = pd.DataFrame([{**vars(dev[p]), "PartNumber": p} for p in ("EPC2014C", "EPC2057")])
    old = H.PACK_RULE
    try:
        for rule, feasible in (("off", True), ("on", False)):
            H.PACK_RULE = rule
            r = H.optimize_architecture(
                a, df, [ind], [cap], np.array([F49]), dev["EPC2014C"], dev["EPC2057"], ind, cap,
                F49, I49, V_OUT, V_IN, 5.0, ripple_factor=0.5, v_ripple_frac=0.25,
                area_budget_mm2=I49 / 3.5)
            assert bool(np.isfinite(r.optimized_loss)) is feasible
    finally:
        H.PACK_RULE = old


# ---------------------------------------------------------------- legacy reproduction
def _published_row(tag, m):
    p = R / "research" / "tcpmt_revision" / "dse_j35" / "data" / f"case_D_{tag}.csv"
    return [r for r in csv.DictReader(p.open()) if int(float(r["M"])) == m][0]


@pytest.mark.parametrize("cap_rule, tag", [("legacy", "etm35"), ("stress", "etm35_caprule_full")])
def test_legacy_flags_reproduce_the_49_cell_selection(cap_rule, tag):
    """cc = 15 at M = 49 with the switch, C_OSS, packing, gate-resistance and footprint flags at
    their legacy values returns the DSE row of the published (capacitor rule legacy too) /
    corrected-capacitor sweep bit for bit."""
    row = _published_row(tag, 49)
    old = (H.CAP_RULE, H.SW_RULE, H.COSS_RULE, H.PACK_RULE, H.RG_RULE, H.FOOTPRINT_RULE)
    cwd = os.getcwd()
    try:
        (H.CAP_RULE, H.SW_RULE, H.COSS_RULE, H.PACK_RULE, H.RG_RULE,
         H.FOOTPRINT_RULE) = cap_rule, "legacy", "legacy", "off", "legacy", "legacy"
        os.chdir(SIVR)
        rr = H.run_hvr_optimization(target_component_count=15, V_in=V_IN, V_out=V_OUT,
                                    I_out=I49, V_gs_drive=5.0, ripple_factor=0.5,
                                    v_ripple_frac=0.25, I_target_density=3.5, verbose=False)
    finally:
        os.chdir(cwd)
        H.CAP_RULE, H.SW_RULE, H.COSS_RULE, H.PACK_RULE, H.RG_RULE, H.FOOTPRINT_RULE = old
    r = [x for x in rr if (x.architecture.N, x.architecture.K, x.architecture.K_A) == (3, 3, 2)][0]
    assert repr(float(r.optimized_loss)) == repr(float(row["conv_loss_per_vr_W"]))
    assert repr(float(r.optimized_f_sw)) == repr(float(row["f_sw_Hz"]))
    assert (r.optimized_hs_device.part_number, r.optimized_ls_device.part_number) == \
        (row["hs"], row["ls"])


# ---------------------------------------------------------------- production pin
def test_production_pin_sets_and_restores_rules():
    import electrical as E
    old = (H.CAP_RULE, H.SW_RULE, H.COSS_RULE, H.PACK_RULE)
    try:
        H.SW_RULE, H.COSS_RULE, H.PACK_RULE = "stress", "corrected", "on"
        prev = E._pin_production_rules(H)
        if not any(k.startswith("HVR_PRODUCTION_") for k in os.environ):
            assert (H.CAP_RULE, H.SW_RULE, H.COSS_RULE, H.PACK_RULE) == \
                ("legacy", "legacy", "legacy", "off")
        E._restore_rules(H, prev)
        assert (H.SW_RULE, H.COSS_RULE, H.PACK_RULE) == ("stress", "corrected", "on")
    finally:
        H.CAP_RULE, H.SW_RULE, H.COSS_RULE, H.PACK_RULE = old


def test_production_loss_at_keeps_the_published_coss_term(dev):
    import electrical as E
    a = _arch(3, 3)
    ind = [i for i in H.INDUCTOR_LIBRARY if i.name == "Shared_Core_UIC_250_nH"][0]
    cap = [c for c in H.CAPACITOR_LIBRARY if c.name == "Murata-GCM21-10uF-25V"][0]
    d = E.HVRDesign(label="t", arch=a, hs=dev["EPC2014C"], ls=dev["EPC2057"], inductor=ind,
                    capacitor=cap, f_sw_hz=F49, i_out_a=I49, v_in=V_IN, v_out=V_OUT,
                    area_mm2=5.61, area_budget_mm2=I49 / 3.5, loss_25c_w=0.0, j_target=3.5)
    old = H.COSS_RULE
    try:
        H.COSS_RULE = "corrected"
        p = d.loss_at(25.0)["p_conv_w"]
        assert H.COSS_RULE == "corrected"                       # restored
    finally:
        H.COSS_RULE = old
    if not any(k in os.environ for k in ("HVR_PRODUCTION_COSS_RULE", "HVR_PRODUCTION_RG_RULE")):
        old_rg = H.RG_RULE
        try:
            H.RG_RULE = "legacy"                                # production: published terms
            ref = _loss49(dev, "legacy").total_loss
        finally:
            H.RG_RULE = old_rg
        assert p == pytest.approx(ref, rel=1e-12)
