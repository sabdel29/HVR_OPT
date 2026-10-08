"""Phase-0L-R regression tests.

These pin the FINDINGS to their artifacts, so a later change that silently reverses one fails
the build rather than quietly rewriting the conclusion.
"""
from __future__ import annotations
import csv, hashlib, json, math, re, sys
from pathlib import Path

import pytest
import yaml

R = Path(__file__).resolve().parents[2]
LR = R / "results" / "phase0lr"
sys.path.insert(0, str(R / "scripts" / "phase0ir"))


def rows(name):
    p = LR / name
    if not p.is_file():
        pytest.skip(f"{name} not generated")
    return list(csv.DictReader(open(p)))


F = lambda r, k: float(r[k])


# ----------------------------------------------------------------- DEFECT #46 --------------
def test_defect46_parser_keeps_the_last_block_at_each_time():
    """The two parsers must stand on the SAME side of a step boundary."""
    src = (R / "scripts" / "phase0ir" / "decompose.py").read_text()
    assert "DEFECT #46" in src, "the defect-46 explanation has been removed from decompose.py"
    # the guard that caused it must be gone
    assert 'and tm not in out:\n            out[tm] = float(p[1])' not in src


def test_defect46_temperature_matches_the_solver_thermal_strain():
    """parse_temperature must agree with the solver's own E - ME on a real run."""
    import numpy as np
    from decompose import parse_temperature
    sys.path.insert(0, str(R / "scripts" / "phase0i"))
    sys.path.insert(0, str(R / "scripts" / "phase0jr"))
    sys.path.insert(0, str(R / "scripts" / "phase0lr"))
    dat = LR / "wd" / "E_tight.dat"
    if not dat.is_file():
        pytest.skip("energy-audit .dat not retained")
    import solder_model as sm
    import energy_audit as EA
    from graded_joint import build_joint_graded
    ids = set(build_joint_graded(6, 6).sets["ESYED"])
    data = EA.parse(dat, ids)
    temps = parse_temperature(dat)
    bad = 0
    for t in sorted(data):
        T = temps.get(t)
        d = next((v for v in data[t].values() if "E" in v and "ME" in v), None)
        if d is None or T is None:
            continue
        implied = 25.0 + (np.array(d["E"]) - np.array(d["ME"]))[0] / sm.CTE_SAC305
        if abs(implied - T) > 5.0:
            bad += 1
    assert bad == 0, f"{bad} time points still disagree with the solver's thermal strain"


def test_inelastic_strain_is_isochoric():
    """Creep is volume-preserving; a spurious volumetric part is how DEFECT #46 was found.

    Two facts are asserted, because they are different:
      * the ME-based reconstruction IS isochoric to 1e-5 -- that is the standard, and it is why
        reading the solver's mechanical strain is the recommended permanent fix;
      * the Python reconstruction has a BOUNDED residual after the DEFECT #46 fix. It is not
        zero, because about 26 increments share one printed time key at a step boundary and the
        solver prints time to only about seven digits, so tensors and temperature can still come
        from neighbouring increments. The bound is asserted so that a regression enlarges it and
        fails, rather than passing quietly.
    """
    import numpy as np
    sys.path.insert(0, str(R / "scripts" / "phase0i"))
    sys.path.insert(0, str(R / "scripts" / "phase0jr"))
    sys.path.insert(0, str(R / "scripts" / "phase0lr"))
    dat = LR / "wd" / "E_tight.dat"
    if not dat.is_file():
        pytest.skip("energy-audit .dat not retained")
    import energy_audit as EA
    from decompose import decompose, parse_temperature
    from graded_joint import build_joint_graded
    ids = set(build_joint_graded(6, 6).sets["ESYED"])
    data = EA.parse(dat, ids)
    temps = parse_temperature(dat)
    import energy_audit as EA
    worst_py = worst_me = 0.0
    for t in sorted(data)[::17]:
        T = temps.get(t)
        for e, d in data[t].items():
            if not all(k in d for k in ("S", "E", "ME")) or T is None:
                continue
            worst_py = max(worst_py, abs(np.array(decompose(d["S"], d["E"], T)[2])[:3].sum()))
            me = np.array(d["ME"]) - np.array(EA.elastic(d["S"], T))
            worst_me = max(worst_me, abs(me[:3].sum()))
    assert worst_me < 1e-5, (
        f"the ME-based reconstruction is no longer isochoric ({worst_me:.2e}); "
        "the solver's mechanical-strain output has changed meaning")
    assert worst_py < 5e-4, (
        f"the Python reconstruction's volumetric residual grew to {worst_py:.2e}; "
        "DEFECT #46 may have regressed")
    assert worst_me < worst_py / 5, (
        "the ME-based route is no longer clearly better than the reconstruction, which is the "
        "evidence for the recommended permanent fix")


# --------------------------------------------------------- predeclared gate ----------------
def test_robustness_gate_was_predeclared_and_is_unmodified():
    doc = LR / "PART10_PREDECLARED_ROBUSTNESS_GATE.md"
    rec = LR / "PART10_PREDECLARED_ROBUSTNESS_GATE.sha256"
    assert doc.is_file() and rec.is_file()
    assert hashlib.sha256(doc.read_bytes()).hexdigest() == rec.read_text().split()[0], \
        "the predeclared robustness gate has been edited after the fact"


def test_gate_classification_follows_its_own_rule():
    g = rows("model_form_gate_result.csv")
    mf = rows("model_form_robustness.csv")
    fams = {r["family"] for r in mf}
    allr = [F(r, k) for r in mf for k in ("r_strain", "r_energy", "r_range")]
    want = ("MODEL-FORM DEPENDENT" if any(x <= 1 for x in allr)
            else "INSUFFICIENT EVIDENCE" if len(fams) < 3 else None)
    if want:
        assert all(r["gate_classification"] == want for r in g), \
            f"gate says {g[0]['gate_classification']}, its own rule says {want}"


def test_ordering_survives_every_model_and_metric():
    mf = rows("model_form_robustness.csv")
    bad = [(r["model"], k, F(r, k)) for r in mf
           for k in ("r_strain", "r_energy", "r_range") if F(r, k) <= 1.0]
    assert not bad, f"an admitted model reverses the Z2/Z1 ordering: {bad[:3]}"


# ---------------------------------------------------------------- mechanism ----------------
def test_the_two_architectures_share_an_extrapolation_region():
    """Phase 0L claimed 78 vs 72 MPa; properly weighted they are within a few per cent."""
    d = {r["arch"]: r for r in rows("damage_weighted_stress_distribution.csv")}
    m1, m2 = F(d["Z1"], "sigma_vm_median_MPa"), F(d["Z2"], "sigma_vm_median_MPa")
    assert abs(m1 / m2 - 1) < 0.05, f"medians {m1:.1f} and {m2:.1f} differ by more than 5 %"


def test_almost_all_damage_is_outside_the_calibration_window():
    f = rows("high_stress_damage_fraction.csv")
    for arch in ("Z1", "Z2"):
        inside = sum(F(r, "damage_fraction") for r in f
                     if r["arch"] == arch and r["stress_bin_MPa"] == "<16")
        assert inside < 0.01, f"{arch}: {100*inside:.2f} % inside the window -- check the model"


def test_z1_peak_exceeds_z2_peak():
    h = rows("z1_z2_cycle_histories.csv")
    pk = {a: max(F(r, "sigma_vm_MPa") for r in h if r["arch"] == a) for a in ("Z1", "Z2")}
    assert pk["Z1"] > pk["Z2"], "the peak-stress mechanism has reversed"


# --------------------------------------------------------- report consistency --------------
def test_cross_report_consistency_passes():
    p = LR / "cross_report_claims.json"
    if not p.is_file():
        pytest.skip("cross-report audit not run")
    d = json.loads(p.read_text())
    assert d["n_failures"] == 0, f"{d['n_failures']} cross-report disagreements"


def test_no_placeholders_survive_in_the_contract():
    s = (R / "results" / "CURRENT_SCIENTIFIC_STATUS.yaml").read_text()
    assert "@@" not in s, "an unfilled placeholder remains in the status contract"


def test_status_yaml_records_the_phase0lr_contract():
    d = yaml.safe_load((R / "results" / "CURRENT_SCIENTIFIC_STATUS.yaml").read_text())
    for blk, keys in (("solder_material", ("creep_source_alloy", "intended_target_alloy",
                                           "alloy_match_status")),
                      ("calculix_visco", ("exact_rate_law", "stress_variable",
                                          "interpolation_rule", "plastic_behavior_in_visco",
                                          "source_verified")),
                      ("creep_calibration", ("temperature_domain", "source_stress_domain",
                                             "package_stress_domain", "extrapolation_status")),
                      ("constitutive_model", ("admitted_models", "rejected_models",
                                              "current_model_status", "high_stress_status")),
                      ("relative_reliability", ("ranking", "z2_z1_min", "z2_z1_max",
                                                "magnitude_status", "common_mode_status")),
                      ("absolute_life", ("status",)),
                      ("experiment", ("status", "sample_count_status",
                                      "n_per_cell_max_current", "package_count_max_current",
                                      "blocker")),
                      ("mission", ("n_required",)), ("g2", ("status",)),
                      ("optimizer", ("allowed",)),
                      ("reports", ("historical_report_status", "standalone_report_status"))):
        assert blk in d, f"contract block {blk} missing"
        for k in keys:
            assert k in d[blk] and d[blk][k] not in (None, ""), f"{blk}.{k} missing or empty"
    assert d["optimizer"]["allowed"] is False
    assert {44, 45, 46} <= {e["id"] for e in d["phase0g_defects"]}


def test_alloy_is_never_silently_promoted():
    d = yaml.safe_load((R / "results" / "CURRENT_SCIENTIFIC_STATUS.yaml").read_text())
    assert "Sn3.9Ag0.6Cu" in d["solder_material"]["creep_source_alloy"]
    assert "SAC305" in d["solder_material"]["intended_target_alloy"]
    assert "MISMATCH" in d["solder_material"]["alloy_match_status"].upper()
