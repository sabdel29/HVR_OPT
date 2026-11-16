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


def test_production_lineage_pins_legacy_selection():
    if os.environ.get("HVR_PRODUCTION_CAP_RULE", "legacy") != "legacy":
        return
    sys.path.insert(0, str(R / "scripts" / "phase0f"))
    import kw1
    d, _g, why = kw1.design_1kw()
    assert d is not None, why
    assert d.capacitor.name == "Murata-GCM21-10uF-25V"
    assert (d.hs.part_number, d.ls.part_number) == ("EPC2014C", "EPC2057")
    assert (d.arch.N, d.arch.K, d.arch.K_A) == (3, 3, 2)
    assert H.CAP_RULE == os.environ.get("HVR_CAP_RULE", "stress")   # restored after the call
