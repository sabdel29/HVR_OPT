"""The flying-capacitor voltage rule (TCPMT revision, review round 2).

C_i of the generalized hybrid family holds (N - i) V_in / N; the corrected rule checks the most
stressed capacitor, C_1, against the derated rating, and the legacy rule (published) is kept so
earlier results stay reproducible. The production lineage pins the legacy rule.
"""
import os
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
SIVR = R / "Scalable_Integrated_VR" / "src"
sys.path.insert(0, str(SIVR))
sys.path.insert(0, str(R / "scripts" / "phase0d"))

import HVR_FULL_OPT_EPC_V2 as H  # noqa: E402


def _arch(n, k):
    return H.VRArchitecture(N=n, K=k, K_A=(k + 1) // 2, B_array=H.generate_B_array(n, k, (k + 1) // 2),
                            D=n / 48.0, component_count=2 * n + 2 * k - 1)


def test_corrected_rule_rejects_underrated_parts():
    lib = H.default_capacitor_library("stress")
    for n in (2, 3, 4):
        ok = H.filter_candidate_capacitors(lib, _arch(n, 2), 48.0, rule="stress")
        v_stress = (n - 1) * 48.0 / n
        assert ok, f"no admissible capacitor for N={n}"
        assert all(c.v_max * H.CAP_V_DERATING >= v_stress for c in ok)
        assert "Murata-GCM21-10uF-25V" not in {c.name for c in ok}


def test_legacy_rule_and_library_unchanged():
    lib = H.default_capacitor_library("legacy")
    assert [c.name for c in lib] == [c.name for c in H.CAPACITOR_LIBRARY]
    ok = H.filter_candidate_capacitors(lib, _arch(3, 3), 48.0, rule="legacy")
    assert "Murata-GCM21-10uF-25V" in {c.name for c in ok}      # the published admission


def test_rated_parts_only_under_corrected_rule():
    names = {c.name for c in H.default_capacitor_library("stress")}
    assert "Murata-GRM188D72A105KE01-1uF-100V" in names
    assert not ({"Murata-GRM188D72A105KE01-1uF-100V"}
                & {c.name for c in H.default_capacitor_library("legacy")})


def test_production_lineage_selection(monkeypatch):
    """Review round 2: the production converter uses the corrected rule (rated part); the
    published selection stays reachable with HVR_PRODUCTION_RULES=legacy."""
    sys.path.insert(0, str(R / "scripts" / "phase0f"))
    import kw1
    for k in ("HVR_PRODUCTION_RULES", "HVR_PRODUCTION_CAP_RULE"):
        monkeypatch.delenv(k, raising=False)
    d, _g, why = kw1.design_1kw()
    assert d is not None, why
    assert d.capacitor.name == "Murata-GRM188D72A105KE01-1uF-100V"
    assert (d.hs.part_number, d.ls.part_number) == ("EPC2014C", "EPC2057")
    assert (d.arch.N, d.arch.K, d.arch.K_A) == (3, 3, 2)
    monkeypatch.setenv("HVR_PRODUCTION_RULES", "legacy")
    d, _g, why = kw1.design_1kw()
    assert d is not None, why
    assert d.capacitor.name == "Murata-GCM21-10uF-25V"
    assert (d.arch.N, d.arch.K, d.arch.K_A) == (3, 3, 2)
    assert H.CAP_RULE == os.environ.get("HVR_CAP_RULE", "stress")   # restored after the call


# --- effective-capacitance ripple, ESR(f), height (Option A completion) ---------------------
from dataclasses import replace as _rep  # noqa: E402


def _rated():
    return [c for c in H.default_capacitor_library("stress")
            if c.name == "Murata-GRM188D72A105KE01-1uF-100V"][0]


def test_unequal_stresses_n3_and_n2():
    # N=3: C1 32 V, C2 16 V; N=2: C1 24 V -- the rule checks C1 (the largest)
    c = _rated()
    assert abs(H.cap_c_eff_uf(c, 32.0, 25.0) - H.cap_c_eff_uf(c, 16.0, 25.0)) > 0.1
    for n, v1 in ((3, 32.0), (2, 24.0)):
        a = _arch(n, n)
        assert abs((a.N - 1) * 48.0 / a.N - v1) < 1e-9


def test_rating_exactly_at_threshold_passes():
    v_stress = 2 * 48.0 / 3                       # C1 of N=3
    cap = _rep(_rated(), v_max=v_stress / H.CAP_V_DERATING, name="threshold")
    assert H.filter_candidate_capacitors([cap], _arch(3, 3), 48.0, rule="stress")
    below = _rep(cap, v_max=cap.v_max - 1e-6, name="below")
    assert not H.filter_candidate_capacitors([below], _arch(3, 3), 48.0, rule="stress")


def test_passes_voltage_but_fails_effective_capacitance():
    # a 100-V silicon part (no bias dependence) of only 10 nF: rated, but the ripple fails
    tiny = H.Capacitor("tiny-Si-10nF-100V", "silicon_trench_MOS", c_uf=0.010, esr_mohm=100.0,
                       esl_ph=30, v_max=100.0, footprint_mm2=0.64, source="test")
    a = _arch(3, 3)
    assert H.filter_candidate_capacitors([tiny], a, 48.0, rule="stress")
    assert H.flying_cap_ripple(a, tiny, 1000.0 / 49, 48.0, 1.0, 805170.0) > H.CAP_RIPPLE_MAX
    # the rated 0603 passes at 105 and 125 C (with tolerance)
    for t in (105.0, 125.0):
        assert H.flying_cap_ripple(a, _rated(), 1000.0 / 49, 48.0, 1.0, 805170.0, t) < 0.10


def test_mlcc_without_vendor_data_has_unknown_ceff():
    lib = {c.name: c for c in H.CAPACITOR_LIBRARY}
    assert H.cap_c_eff_uf(lib["Murata-GRM31-22uF-50V"], 32.0, 105.0) is None


def test_esr_interpolation_at_fsw():
    c = _rated()
    r = H.cap_esr_mohm(c, 805170.0, 32.0)
    assert 7.0 < r < 8.6                           # vendor ESR(f) at 32 V near 805 kHz
    assert H.cap_esr_mohm(H.CAPACITOR_LIBRARY[0], 805170.0, 32.0) == H.CAPACITOR_LIBRARY[0].esr_mohm


def test_height_limit_admits_no_rated_part_at_100um():
    old = H.CAP_MAX_HEIGHT_UM
    try:
        H.CAP_MAX_HEIGHT_UM = 100.0
        ok = H.filter_candidate_capacitors(H.default_capacitor_library("stress")
                                           + H.research_capacitor_library(), _arch(3, 3), 48.0,
                                           rule="stress")
        assert ok == []                            # the WLSC part is rated 32 V only
    finally:
        H.CAP_MAX_HEIGHT_UM = old
