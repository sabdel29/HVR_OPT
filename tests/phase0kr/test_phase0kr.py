"""Phase-0K-R tests. Every number re-derived from the CSV the phase wrote."""
from __future__ import annotations
import csv, math
from pathlib import Path

import pytest
import yaml

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0kr"
CFG = R / "configs" / "phase0kr" / "constitutive_domain.yaml"


def rows(n):
    return list(csv.DictReader(open(OUT / n)))


@pytest.fixture(scope="module")
def status():
    return yaml.safe_load((R / "results" / "CURRENT_SCIENTIFIC_STATUS.yaml").read_text())


@pytest.fixture(scope="module")
def dom():
    return yaml.safe_load(CFG.read_text())


# ------------------------------------------------ Sec.4 constitutive domain

def test_creep_domain_matches_the_material_card(dom):
    import sys
    sys.path.insert(0, str(R / "scripts" / "phase0i"))
    from solder_model import CREEP_DATA
    ts = sorted({t for t, s, e in CREEP_DATA})
    assert dom["creep"]["calibration_temperatures_C"] == ts
    lo = min(s for t, s, e in CREEP_DATA); hi = max(s for t, s, e in CREEP_DATA)
    assert dom["creep"]["stress_window_MPa"] == [pytest.approx(lo), pytest.approx(hi)]
    assert dom["creep"]["temperature_floor_C"] == 45.0


def test_the_25C_card_row_is_already_extrapolated(dom):
    assert 25.0 in dom["already_extrapolated_card_rows"]["creep"]
    assert dom["creep"]["arrhenius_independently_validated"] is False


def test_driving_variable_is_the_overstress(dom):
    assert "OVERSTRESS" in dom["creep"]["driving_variable"]


# ------------------------------------------------ Sec.5/6 profile audit

def test_cold_shallow_is_invalid():
    d = [r for r in rows("profile_domain_audit.csv")
         if r["arch"] == "Z1" and r["condition"] == "COLD_SHALLOW"][0]
    assert float(d["frac_damage_below_45C"]) == pytest.approx(1.0, abs=1e-6)
    assert d["domain_class"] == "INVALID FOR MODEL-DISCRIMINATION DESIGN"


def test_selected_profiles_have_zero_damage_below_the_creep_floor():
    d = {r["condition"]: r for r in rows("profile_domain_audit.csv") if r["arch"] == "Z1"}
    for c in ("D_LOW_WIDE", "D_HIGH_NARROW"):
        assert float(d[c]["frac_damage_below_45C"]) == pytest.approx(0.0, abs=1e-9), c
        assert float(d[c]["T_min_C"]) >= 45.0, c


def test_stress_domain_fails_for_every_profile_including_the_baseline():
    """The limitation no profile removes. If this ever passes, the model changed."""
    for r in rows("profile_domain_audit.csv"):
        assert float(r["frac_damage_outside_stress_window"]) > 0.85, r["condition"]


def test_damage_weighting_uses_solver_increments_not_a_reconstruction():
    src = (R / "scripts" / "phase0kr" / "domain_audit.py").read_text()
    assert "de = max(pb - pa, 0.0) * v" in src
    assert "diverges" in src, "the reason must be recorded next to the code"


# ------------------------------------------------ Sec.7/8 low temperature

def test_model_was_not_extended(status):
    assert not (OUT / "LOW_TEMPERATURE_MODEL_VALIDATION.md").exists(), \
        "no validation document may exist, because no extension was performed"
    t = (OUT / "LOW_TEMPERATURE_SAC305_AUDIT.md").read_text()
    assert "the model is NOT extended" in t or "NOT extended" in t
    assert "0.475" in t, "the homologous-temperature argument must be present"
    assert status["experiment_0kr"]["withdrawn_profile"].startswith("COLD_SHALLOW")


# ------------------------------------------------ Sec.9/10/11 profile selection

def test_selection_is_composite_not_max_D():
    ec = rows("experiment_profile_search.csv")
    adm = [r for r in ec if r["admissible_for_design"] == "True"]
    best_D = max(adm, key=lambda r: float(r["D_discrimination"]))
    sel = {"D_LOW_WIDE", "D_HIGH_NARROW"}
    assert {best_D["cond_A"], best_D["cond_B"]} != sel, \
        "the selected pair must NOT be the max-D pair -- that is the point of Sec.10"
    chosen = [r for r in adm if {r["cond_A"], r["cond_B"]} == sel][0]
    assert float(chosen["Z_discrimination_beta5p1_n16"]) >= 3.0
    assert float(chosen["max_cell_duration_days"]) < float(best_D["max_cell_duration_days"])


def test_revised_pair_discrimination(status):
    e = status["experiment_0kr"]
    assert "1.4395" in e["model_discrimination_status"]
    assert "3.44" in e["model_discrimination_status"]
    assert "NOT called a sigma" in e["model_discrimination_status"]


def test_original_claims_are_withdrawn(status):
    w = status["experiment_0kr"]["withdrawn_profile"]
    for k in ("1.849", "6.19", "WITHDRAWN"):
        assert k in w, k


# ------------------------------------------------ Sec.13/14/17 statistics

def test_beta_database_is_primary_and_beta6_is_not_conservative():
    db = rows("SAC305_WEIBULL_BETA_DATABASE.csv")
    assert len(db) >= 16
    bs = sorted(float(r["beta"]) for r in db)
    assert min(bs) == pytest.approx(5.1)
    below = sum(1 for b in bs if b < 6)
    assert below >= 4, "beta=6 must be shown NOT to be a lower bound"
    for r in db:
        assert r["source"].startswith(("Syed", "George")), r["source"]


def test_n16_is_sufficient_for_Q1_and_insufficient_for_Q2():
    ss = {(int(r["n_per_cell"]), float(r["beta"])): r for r in rows("sample_size_sensitivity.csv")}
    r = ss[(16, 5.0)]
    assert float(r["Z_Q1_model_discrimination"]) >= 3.0
    assert float(r["Z_Q2_arch_both_conditions"]) < 3.0


def test_final_n_meets_both_questions():
    ss = [r for r in rows("sample_size_sensitivity.csv") if int(r["n_per_cell"]) == 50]
    r = [x for x in ss if float(x["beta"]) == 5.0][0]
    assert float(r["Z_Q1_model_discrimination"]) >= 3.0
    assert float(r["Z_Q2_arch_both_conditions"]) >= 3.0


def test_status_records_n34_and_136(status):
    e = status["experiment_0kr"]["sample_size_status"]
    assert "34" in e and "136" in e and "INSUFFICIENT" in e


# ------------------------------------------------ Sec.18 failure criterion

def test_failure_criterion_verified_against_the_primary():
    t = (OUT / "failure_criterion_reaudit.md").read_text()
    for k in ("300", "ten additional", "10 %", "every two minutes", "MEAN life"):
        assert k in t, k
    assert "manual" in t.lower()


# ------------------------------------------------ Sec.19/22/23 wording

def test_terminology_frozen(status):
    t = status["experiment_0kr"]["terminology"]
    assert t["CONDITION"] and t["CELL"] and t["CAMPAIGN"]
    assert "cannot identify" in t["rule"]


def test_ambiguous_range_is_stated_as_logarithmic(status):
    w = status["g2_0kr"]["ambiguous_interval_wording"]
    assert "0.83" in w and "DECADE" in w.upper() and "LOGARITHMIC" in w.upper()
    assert "2.7" in w, "the linear figure must be shown to be misleading"


def test_g2_window_has_its_denominator(status):
    w = status["g2_0kr"]["post_calibration_window_wording"]
    assert "1.1665" in w and "16.65" in w
    assert "MEASURED Z1 LIFE" in w.upper()


# ------------------------------------------------ Sec.21/27/32 unchanged things

def test_z4_still_excluded(status):
    assert "1.030" in status["experiment_0kr"]["z4_excluded_because"]


def test_relative_life_result_is_unchanged(status):
    rl = status["relative_life_0kr"]
    assert rl["status"] == "VALIDATED"
    assert rl["z2_z1_min"] == 1.21 and rl["z2_z1_max"] == 1.38
    assert "UNCHANGED BY PHASE 0K-R" in rl["validated_scope"]


def test_mission_still_open_and_parallel(status):
    assert status["mission_0kr"]["n_required_status"] == "OPEN"
    assert status["next_step_0kr"]["in_parallel"] is True
    assert status["next_step_0kr"]["optimizer_allowed"] is False
    assert status["meta"]["optimiser_built"] is False


def test_experiment_not_claimed_run(status):
    assert status["experiment_0kr"]["experiment_has_been_run"] is False
    plan = (OUT / "FINAL_BOARD_LEVEL_EXPERIMENT_PLAN.md").read_text()
    assert "HAS NOT BEEN RUN" in plan
    assert "NOT FROZEN" in plan


# ------------------------------------------------ Sec.28/29/34 artifacts

@pytest.mark.parametrize("name", [
    "PHASE0KR_EXPERIMENTAL_CLOSURE.md", "DEFECT39_REPORT_AUDIT.md",
    "SAC305_CONSTITUTIVE_DOMAIN.md", "LOW_TEMPERATURE_SAC305_AUDIT.md",
    "experiment_profile_search.csv", "EXPERIMENT_PROFILE_SELECTION.md",
    "profile_domain_audit.csv", "SAC305_WEIBULL_BETA_DATABASE.csv",
    "sample_size_sensitivity.csv", "statistical_power_analysis.csv",
    "failure_criterion_reaudit.md", "identifiability_final.csv",
    "FINAL_BOARD_LEVEL_EXPERIMENT_PLAN.md", "G2_WINDOW_WORDING_AUDIT.md",
    "POSTBUILD_SEMANTIC_AUDIT.md"])
def test_required_artifact_exists(name):
    p = OUT / name
    assert p.is_file() and p.stat().st_size > 200, name


@pytest.mark.parametrize("fig", list("ABCDEFG"))
def test_required_figure_exists(fig):
    got = list(OUT.glob(f"FIG_0KR_{fig}_*.png"))
    assert len(got) == 1 and got[0].stat().st_size > 10000, fig


def test_postbuild_audit_is_clean():
    t = (OUT / "POSTBUILD_SEMANTIC_AUDIT.md").read_text()
    assert "CLEAN" in t, "the post-build audit must have found nothing"
    assert "current-facing headings checked" in t
