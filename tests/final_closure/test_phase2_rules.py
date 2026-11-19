"""Gate resistance, capacitor body footprints and mixed tiers (TCPMT revision, phase 2).

Defaults: datasheet R_G per part (HVR_RG_RULE=legacy restores 6e-4 Ohm), capacitor body areas in
the area rule (HVR_FOOTPRINT_RULE=legacy restores the library values), mixed tiers with at most
HVR_MAX_TIERS (4; 0 = no limit) when the packing check is on. The production converter pins
its own values (electrical: the corrected rules, packing off for now; HVR_PRODUCTION_RULES=legacy
the published behaviour).
"""
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
I49, F49 = 1000.0 / 49, 805170.3343770516
SIDE49 = math.sqrt(I49 / 3.5)


@pytest.fixture(scope="module")
def dev():
    df = H.load_epc_devices(str(SIVR / "EPC-Product-Table.csv"), V_gs_op=5.0)
    return {r["PartNumber"]: H.row_to_device(r) for _, r in df.iterrows()}


def _arch(n, k):
    ka = math.ceil(k / 2)
    return H.VRArchitecture(N=n, K=k, K_A=ka, B_array=H.generate_B_array(n, k, ka),
                            D=n * V_OUT / V_IN, component_count=2 * n + 2 * k - 1)


def _ind():
    return [i for i in H.INDUCTOR_LIBRARY if i.name == "Shared_Core_UIC_250_nH"][0]


def _cap(name="Murata-GRM188D72A105KE01-1uF-100V"):
    return [c for c in H.default_capacitor_library("stress") if c.name == name][0]


class _Rules:
    """Set engine rule switches for a block and restore them."""
    def __init__(self, **kw):
        self.kw, self.old = kw, {}

    def __enter__(self):
        for k, v in self.kw.items():
            self.old[k] = getattr(H, k)
            setattr(H, k, v)

    def __exit__(self, *a):
        for k, v in self.old.items():
            setattr(H, k, v)


def test_defaults():
    if "HVR_RG_RULE" not in os.environ:
        assert H.RG_RULE == "datasheet"
    if "HVR_FOOTPRINT_RULE" not in os.environ:
        assert H.FOOTPRINT_RULE == "body"
    if "HVR_TIER_RULE" not in os.environ:
        assert H.TIER_RULE == "mixed"
    if "HVR_MAX_TIERS" not in os.environ:
        assert H.MAX_TIERS == 4
    assert H.RDL_UM == 10.0


# ---------------------------------------------------------------- gate resistance
def test_datasheet_gate_resistance(dev):
    # datasheets: EPC2014C 0.4, EPC2057 0.8, EPC2090 0.4, EPC2214 0.65 Ohm; no value -> median
    exp = {"EPC2014C": 0.4, "EPC2057": 0.8, "EPC2090": 0.4, "EPC2214": 0.65, "EPC7002": 0.4}
    with _Rules(RG_RULE="datasheet"):
        for p, r in exp.items():
            assert H.gate_resistance(dev[p]) == pytest.approx(r)
    with _Rules(RG_RULE="legacy"):
        assert H.gate_resistance(dev["EPC2014C"]) == 6e-4


def test_overlap_term_scales_with_gate_current(dev):
    a, ind, cap = _arch(3, 3), _ind(), _cap()

    def p_hs(rule):
        with _Rules(RG_RULE=rule):
            return H.compute_total_loss(a, H.LossModelInputs(dev["EPC2014C"], dev["EPC2057"], ind,
                                                             cap, I49, V_OUT, V_IN, F49)).p_sw_hs
    ig = lambda rg: (5.0 - 0.5 * (1.0 + 1.6)) / (rg + 0.7)       # noqa: E731
    assert p_hs("datasheet") / p_hs("legacy") == pytest.approx(ig(6e-4) / ig(0.4), rel=1e-12)


def test_qoss_test_voltage_from_datasheet(dev):
    d = dev["EPC2204A"]                       # 80 V part, Q_OSS 25 nC specified at 50 V
    assert d.QOSS_V_test == 50.0
    assert H.q_oss_at(d, 50.0) == pytest.approx(d.Q_OSS)
    assert dev["EPC2014C"].QOSS_V_test == 20.0            # datasheet: 4 nC at 20 V
    assert H.q_oss_at(dev["EPC2014C"], 20.0) == pytest.approx(4e-9)
    assert np.isnan(dev["EPC7003"].QOSS_V_test)           # datasheet Q_OSS disagrees with table
    assert H.q_oss_at(dev["EPC7003"], 50.0) == pytest.approx(dev["EPC7003"].Q_OSS)  # V_DS,max/2


# ---------------------------------------------------------------- capacitor footprints
def test_body_footprints():
    lib = {c.name: c for c in H.default_capacitor_library("stress")}
    with _Rules(FOOTPRINT_RULE="body"):
        assert H.cap_footprint_mm2(lib["Murata-GRM188D72A105KE01-1uF-100V"]) == 1.28
        assert H.cap_footprint_mm2(lib["Murata-GCM21-10uF-25V"]) == 2.5
        assert H.cap_footprint_mm2(lib["Murata-GRM31-22uF-50V"]) == 5.12
    with _Rules(FOOTPRINT_RULE="legacy"):
        assert H.cap_footprint_mm2(lib["Murata-GCM21-10uF-25V"]) == 2.0
        assert H.cap_footprint_mm2(lib["Murata-GRM31-22uF-50V"]) == 4.5


def test_footprint_rule_in_area(dev):
    a = _arch(4, 2)                                   # 3 flying caps: the cap tier can lead
    gcm = _cap("Murata-GCM21-10uF-25V")
    small = dev["EPC2040"]
    with _Rules(FOOTPRINT_RULE="legacy"):
        assert H._compute_area(a, small, small, _ind(), gcm) == pytest.approx(6.0)
    with _Rules(FOOTPRINT_RULE="body"):
        assert H._compute_area(a, small, small, _ind(), gcm) == pytest.approx(7.5)


# ---------------------------------------------------------------- mixed tiers
def test_heterogeneous_placement_and_pinwheel():
    # one EPC2014C + one EPC2057 (grown by 50 um) share a 2.41-mm tier; two EPC2057 do not
    assert H.place_items([(1.75, 1.15, "hs"), (1.55, 1.25, "ls")], SIDE49) is not None
    assert H.place_items([(1.55, 1.25, "ls"), (1.55, 1.25, "ls")], SIDE49) is None
    # four 2.0 x 1.2 parts in a 3.2 square only as a pinwheel (exact search)
    p = H.place_items([(2.0, 1.2, i) for i in range(4)], 3.2)
    assert p is not None and len(p) == 4
    for i in range(4):
        for j in range(i + 1, 4):
            assert not H._overlap(p[i][:4], p[j][:4])
        assert all(-1e-9 <= c <= 3.2 + 1e-9 for c in (p[i][0] + p[i][2], p[i][1] + p[i][3]))


def test_49_cell_design_needs_five_tiers(dev):
    a, ind, cap = _arch(3, 3), _ind(), _cap()
    sp = H.stack_plan(a, dev["EPC2014C"], dev["EPC2057"], ind, cap, SIDE49, placement=True)
    assert sp["tiers"] == 5 and sp["height_known"]
    # three HS+LS tiers (685 um), the inductor tier (500 um), the capacitor tier (1000 um), RDL
    assert sp["height_um"] == pytest.approx(3 * 685 + 500 + 1000 + 4 * 10.0)
    kinds = sorted(tuple(sorted(k for k in t if k not in ("height_um", "placement_mm")))
                   for t in sp["plan"])
    assert kinds == sorted([("gan_hs", "gan_ls")] * 3 + [("inductor",), ("cap_fly",)])
    assert H.tier_bounds(a, dev["EPC2014C"], dev["EPC2057"], ind, cap, SIDE49) == (4, 7)
    assert not H.tiers_within(a, dev["EPC2014C"], dev["EPC2057"], ind, cap, SIDE49, 4)
    assert H.tiers_within(a, dev["EPC2014C"], dev["EPC2057"], ind, cap, SIDE49, 5)
    assert H.tiers_within(a, dev["EPC2014C"], dev["EPC2057"], ind, cap, SIDE49, 0)


def test_class_tiers_are_a_mixed_solution(dev):
    """The phase-1 one-class-per-tier layout is one admissible mixed stack, so the minimum
    mixed tier count never exceeds the class count when each class fits one tier."""
    a = _arch(4, 4)
    side = math.sqrt(1000 / 36 / 3.5)
    sp = H.stack_plan(a, dev["EPC2057"], dev["EPC2057"], _ind(), _cap(), side)
    assert sp["tiers"] <= 4


def test_mixed_selection_matches_brute_force(dev):
    """The separable A(hs) + B(ls) + C selection equals an exhaustive compute_total_loss search
    over the same parts with the same tier limit."""
    a, ind, cap = _arch(3, 3), _ind(), _cap()
    names = ["EPC2014C", "EPC2057", "EPC2090", "EPC2214", "EPC2045", "EPC2212"]
    df = pd.DataFrame([{**vars(dev[p]), "PartNumber": p} for p in names])
    f_vals = np.array([677703.2536788285, F49, 956612.2987334634])
    for mt in (0, 4, 5):
        with _Rules(PACK_RULE="on", TIER_RULE="mixed", MAX_TIERS=mt, COSS_RULE="corrected",
                    RG_RULE="datasheet", SW_RULE="stress", SW_V_DERATING=0.9, CAP_RULE="stress"):
            r = H.optimize_architecture(a, df, [ind], [cap], f_vals, dev["EPC2014C"],
                                        dev["EPC2057"], ind, cap, F49, I49, V_OUT, V_IN, 5.0,
                                        ripple_factor=0.5, v_ripple_frac=0.25,
                                        area_budget_mm2=I49 / 3.5)
            hs_l, ls_l = H.filter_candidate_devices(df, a, V_IN, V_OUT, 5.0, I49, 1)
            best = float("inf")
            for h in hs_l:
                for l_ in ls_l:
                    if not H.tiers_within(a, h, l_, ind, cap, SIDE49, mt):
                        continue
                    for f in f_vals:
                        if H.flying_cap_ripple(a, cap, I49, V_IN, V_OUT, f) > H.CAP_RIPPLE_MAX:
                            continue
                        from dataclasses import replace
                        cf = replace(cap, esr_mohm=H.cap_esr_mohm(cap, f, 32.0))
                        lr = H.compute_total_loss(a, H.LossModelInputs(h, l_, ind, cf, I49, V_OUT,
                                                                       V_IN, f))
                        if abs(lr.delta_i_out) < 0.5 * I49 and lr.delta_v_out < 0.25:
                            best = min(best, lr.total_loss)
            assert r.optimized_loss == pytest.approx(best, rel=1e-12), mt
            if np.isfinite(best):
                assert (mt == 0 or r.n_tiers <= mt) and r.area_feasible


def test_tier_limit_is_monotone(dev):
    a, ind, cap = _arch(3, 3), _ind(), _cap()
    side = math.sqrt(1000 / 40 / 3.5)
    t = H.stack_plan(a, dev["EPC2014C"], dev["EPC2057"], ind, cap, side)["tiers"]
    for mt in range(1, 9):
        assert H.tiers_within(a, dev["EPC2014C"], dev["EPC2057"], ind, cap, side, mt) is (mt >= t)


# ---------------------------------------------------------------- legacy and production
def test_production_pin_covers_phase2_rules(monkeypatch):
    """The production pin (electrical, one mechanism) sets the phase-2 switches: the corrected
    datasheet R_g and body footprints by default (merge decision, review round 3), the published
    values under HVR_PRODUCTION_RULES=legacy; the engine's own values come back afterwards."""
    import electrical as E
    for k in E.PRODUCTION_ENV:
        monkeypatch.delenv(k, raising=False)
    old = {k: getattr(H, k) for k in ("RG_RULE", "FOOTPRINT_RULE", "COSS_RULE")}
    try:
        for env, want in ((None, ("datasheet", "body")), ("legacy", ("legacy", "legacy"))):
            if env:
                monkeypatch.setenv("HVR_PRODUCTION_RULES", env)
            H.RG_RULE, H.FOOTPRINT_RULE = "engine-rg", "engine-fp"
            prev = E._pin_production_rules(H)
            assert (H.RG_RULE, H.FOOTPRINT_RULE) == want
            E._restore_rules(H, prev)
            assert (H.RG_RULE, H.FOOTPRINT_RULE) == ("engine-rg", "engine-fp")
    finally:
        for k, v in old.items():
            setattr(H, k, v)
