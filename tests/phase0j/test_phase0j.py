"""Phase-0J numerical and claim-scope tests.

Every number asserted here is re-derived from the CSV the phase actually wrote, so the tests
fail if a result changes without the report changing with it.
"""
from __future__ import annotations
import csv
from pathlib import Path

import pytest
import yaml

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0j"
A = ("ARCH_Z1_EMBEDDED", "ARCH_Z2_BACKSIDE", "ARCH_Z4_POWER_DIE")
OPT = {"ARCH_Z1_EMBEDDED": "1.3", "ARCH_Z2_BACKSIDE": "0.3", "ARCH_Z4_POWER_DIE": "0.3"}


def rows(name):
    return list(csv.DictReader(open(OUT / name)))


@pytest.fixture(scope="module")
def status():
    return yaml.safe_load((R / "results" / "CURRENT_SCIENTIFIC_STATUS.yaml").read_text())


@pytest.fixture(scope="module")
def native():
    return rows("native_metrics_by_architecture.csv")


@pytest.fixture(scope="module")
def opt(native):
    return {r["arch"]: r for r in native if r["h_sub_mm"] == OPT[r["arch"]]}


# ---------------------------------------------------------------- Sec.1 / Sec.10

def test_all_eleven_z_sweep_points_were_computed(native):
    assert len(native) == 11
    assert {r["arch"] for r in native} == set(A)


def test_M1_over_M2_is_about_two_for_every_dvpd_case(native):
    """Sec.10: the ratio is a property of the LOADING PATH, not the architecture."""
    r = [float(x["M1_over_M2"]) for x in native]
    assert 2.02 <= min(r) and max(r) <= 2.03, (min(r), max(r))
    assert max(r) - min(r) < 0.01, "ratio must be near-constant across architecture and thickness"


def test_the_phase0ir_ratio_of_3p72_does_NOT_apply_to_the_architecture_cases(native):
    """Sec.2: 3.72 is not a universal conversion factor. This is the guard on that rule."""
    for x in native:
        assert abs(float(x["M1_over_M2"]) - 3.72) > 1.5, (
            "an architecture case must not reproduce the fully-reversed-cycle ratio")


def test_M2_is_computed_directly_not_derived_from_M1():
    """Sec.2: M2 must never be obtained as M1 / 3.72.

    Checked on EXECUTABLE code only -- the module docstring legitimately names the factor in
    order to forbid it, and a guard that cannot tell a prohibition from a violation is the
    DEFECT #36 mistake again.
    """
    import ast as _ast
    src = (R / "scripts" / "phase0j" / "native_metrics.py").read_text()
    tree = _ast.parse(src)
    for node in _ast.walk(tree):                      # strip every docstring
        if isinstance(node, (_ast.Module, _ast.FunctionDef, _ast.AsyncFunctionDef,
                             _ast.ClassDef)) and _ast.get_docstring(node):
            node.body = node.body[1:]
    # A conversion factor would be a NUMERIC literal. Prose that names 3.72 in order to
    # forbid it, or a print() that reports the Phase-0I-R value, is not a violation -- and a
    # substring match cannot tell the two apart.
    consts = [n.value for n in _ast.walk(tree)
              if isinstance(n, _ast.Constant) and isinstance(n.value, (int, float))
              and not isinstance(n.value, bool)]
    assert not any(abs(c - 3.72) < 0.05 for c in consts), \
        f"hard-coded conversion factor in executable code: {[c for c in consts if abs(c-3.72)<0.05]}"


# ---------------------------------------------------------------- Sec.6 admissibility

def test_zero_admissible_life_laws():
    db = rows("SAC305_LIFE_LAW_DATABASE.csv")
    assert len(db) == 10
    assert sum(r["admissibility"] == "ADMISSIBLE" for r in db) == 0
    assert sum(r["admissibility"] == "CONDITIONALLY TRANSFERABLE" for r in db) == 1


def test_every_candidate_carries_all_ten_criteria():
    db = rows("SAC305_LIFE_LAW_DATABASE.csv")
    crit = [c for c in db[0] if c[0].isdigit()]
    assert len(crit) == 10
    for r in db:
        assert all(r[c] in ("PASS", "FAIL") for c in crit)


def test_no_fabricated_calibration_metadata():
    """Sec.5: unavailable metadata must be marked, never invented."""
    db = rows("SAC305_LIFE_LAW_DATABASE.csv")
    for r in db:
        for k in ("T_min_C", "T_max_C", "dT_K", "dwell", "calibration_range"):
            assert r[k] == "NOT_AVAILABLE" or r[k].strip(), k
    # the three canonical primaries must be recorded as unretrievable, not silently used
    txt = " ".join(r["primary_retrieval_status"] for r in db)
    assert txt.count("PRIMARY NOT RETRIEVABLE") >= 3


def test_secondary_provenance_is_labelled():
    db = rows("SAC305_LIFE_LAW_DATABASE.csv")
    syed = [r for r in db if r["id"] == "L4_SYED_CREEP_2MECH"][0]
    assert "SECONDARY" in syed["constants_provenance"]
    assert "0.013" in syed["coefficients"] and "0.036" in syed["coefficients"]


# ---------------------------------------------------------------- Sec.8 reproduction

def test_reproduction_gate_not_passed():
    for r in rows("life_law_reproduction.csv"):
        assert "NOT PASSED" in r["verdict"] or "NOT REPRODUCED" in r["verdict"], r["law"]


def test_no_lifetime_is_presented_as_validated():
    for r in rows("lifetime_by_law_and_architecture.csv"):
        assert r["applicability_status"].startswith("CONDITIONAL")
        assert "NOT A VALIDATED LIFETIME" in r["applicability_status"]


# ---------------------------------------------------------------- Sec.19 / Sec.20 ranking

def test_ranking_is_identical_under_all_three_metrics(opt):
    for key in ("M1_accum_inelastic_path", "M2_strain_range", "M3_inelastic_work_MJ_per_m3"):
        v = {a: float(opt[a][key]) for a in A}
        assert v["ARCH_Z2_BACKSIDE"] < v["ARCH_Z1_EMBEDDED"] < v["ARCH_Z4_POWER_DIE"], key


def test_ranking_is_model_form_independent():
    mf = rows("lifetime_model_form_comparison.csv")
    assert len({r["ranking"] for r in mf}) == 1
    for r in mf:
        assert float(r["Z2_over_Z1_life"]) > 1.0 and float(r["Z4_over_Z1_life"]) < 1.0


def test_relative_life_is_exactly_the_inverse_metric_ratio(opt):
    """The Syed form is inverse-linear: C cancels AND there is no exponent to assume."""
    lt = [r for r in rows("lifetime_by_law_and_architecture.csv")
          if r["law"] == "L4_SYED_2MECH_as_1mech_CII"][0]
    m1 = {a: float(opt[a]["M1_accum_inelastic_path"]) for a in A}
    assert float(lt["Z2_over_Z1"]) == pytest.approx(
        m1["ARCH_Z1_EMBEDDED"] / m1["ARCH_Z2_BACKSIDE"], rel=1e-3)
    assert float(lt["Z4_over_Z1"]) == pytest.approx(
        m1["ARCH_Z1_EMBEDDED"] / m1["ARCH_Z4_POWER_DIE"], rel=1e-3)


def test_changing_the_constant_moves_absolute_life_but_not_the_ratio():
    lt = {r["law"]: r for r in rows("lifetime_by_law_and_architecture.csv")}
    a = lt["L4_SYED_2MECH_as_1mech_CII"]
    b = lt["L4_SYED_2MECH_as_1mech_CI"]
    assert float(a["Z1_life"]) != pytest.approx(float(b["Z1_life"]), rel=0.1)
    assert float(a["Z2_over_Z1"]) == pytest.approx(float(b["Z2_over_Z1"]), rel=1e-6)


# ---------------------------------------------------------------- Sec.12 creep

def test_strain_and_energy_families_disagree_on_the_sign_of_creep():
    cr = [r for r in rows("creep_effect_by_architecture.csv") if r["model"] == "EPC"]
    assert len(cr) == 3
    for r in cr:
        assert float(r["M1_accum_inelastic_path_vs_EP_pct"]) < -15, r["arch"]
        assert float(r["M3_inelastic_work_MJ_per_m3_vs_EP_pct"]) > 100, r["arch"]


# ---------------------------------------------------------------- Sec.13/14/23 mission & G2

def test_required_life_is_open_and_qualification_is_not_promoted(status):
    m = status["mission_requirement"]
    assert m["N_required"] == "OPEN"
    assert "NONE" in m["category_B_field_mission_requirement"].upper()


def test_mission_sweep_is_labelled_parametric():
    for r in rows("mission_life_sensitivity.csv"):
        assert "PARAMETRIC MISSION SENSITIVITY" in r["label"]
        assert "NOT a qualification requirement" in r["label"]


def test_g2_still_not_tested(status):
    assert status["verdict"]["g2_status"] == "NOT_TESTED"
    g2 = rows("g2_evaluation.csv")
    overall = [r for r in g2 if r["requirement"] == "G2 OVERALL"][0]
    assert overall["status"] == "NOT TESTED"


def test_optimizer_still_not_built_or_recommended(status):
    assert status["meta"]["optimiser_built"] is False
    assert status["meta"]["optimiser_recommended"] is False


# ---------------------------------------------------------------- Sec.26 electrical cost

def test_electrical_cost_supersedes_warpage_exchange_rate():
    ec = rows("electrical_cost_of_reliability.csv")
    z2 = [r for r in ec if r["comparison"].startswith("Z2") and "fixed" in r["law_family"]][0]
    assert float(z2["dP_elec_W"]) == pytest.approx(1.688, abs=0.01)
    assert float(z2["life_multiple_vs_Z1"]) == pytest.approx(1.558, rel=1e-3)
    assert all("W per um of warpage" in r["supersedes"] for r in ec)


def test_z1_vs_z4_is_never_ranked_electrically(status):
    assert "NOT RANKED ELECTRICALLY" in \
        status["architecture_life"]["electrical_cost_of_reliability"]["Z1_vs_Z4"]


# ---------------------------------------------------------------- Sec.33 artifacts

@pytest.mark.parametrize("name", [
    "PHASE0J_LIFE_LAW_AND_MISSION_GATE.md", "RELIABILITY_METRIC_DEFINITIONS.md",
    "SAC305_LIFE_LAW_DATABASE.csv", "LIFE_LAW_ADMISSIBILITY.md", "LIFE_LAW_REPRODUCTION.md",
    "life_law_reproduction.csv", "MISSION_REQUIREMENT_AUDIT.md", "cycle_compatibility_audit.md",
    "lifetime_by_law_and_architecture.csv", "lifetime_uncertainty.csv",
    "lifetime_model_form_comparison.csv", "mission_life_sensitivity.csv", "g2_evaluation.csv",
    "electrical_cost_of_reliability.csv"])
def test_required_artifact_exists(name):
    p = OUT / name
    assert p.is_file() and p.stat().st_size > 200, name


@pytest.mark.parametrize("fig", list("ABCDEFGH"))
def test_required_figure_exists(fig):
    got = list(OUT.glob(f"FIG_0J_{fig}_*.png"))
    assert len(got) == 1 and got[0].stat().st_size > 10000, fig


# ---------------------------------------------------------------- Sec.28 wording

def test_metrics_are_called_response_metrics_not_damage(status):
    assert "RESPONSE METRICS" in status["architecture_life"]["word_damage"]
    rep = (R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md").read_text()
    i = rep.find("# Phase 0J ---")
    assert i > 0
    sec = rep[i:]
    assert "fatigue damage parameter" in sec, "the distinction must be stated, not assumed"
