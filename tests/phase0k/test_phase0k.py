"""Phase-0K tests. Every number is re-derived from the CSV the phase actually wrote."""
from __future__ import annotations
import csv, math
from pathlib import Path

import pytest
import yaml

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0k"
CFG = R / "configs" / "phase0k" / "mission_profile.yaml"
ARCH = ("Z1", "Z2", "Z4")
LAWKEYS = ("SYED_EQ14_STRAIN_POWERLAW", "SYED_EQ15_ENERGY_POWERLAW",
           "SYED_EQ16_STRAIN_SINH", "SYED_EQ17_ENERGY_SINH")


def rows(n):
    return list(csv.DictReader(open(OUT / n)))


@pytest.fixture(scope="module")
def status():
    return yaml.safe_load((R / "results" / "CURRENT_SCIENTIFIC_STATUS.yaml").read_text())


@pytest.fixture(scope="module")
def dm():
    return rows("g2_decision_map.csv")


# ---------------------------------------------------- Sec.1 DEFECT #38

def test_defect38_stale_formulations_gone_from_current_facing():
    import re
    md = (R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md").read_text()
    CF = ("executive summary", "governing-equation status", "validation status",
          "publication-defensible claims", "claims that must not be made", "next steps",
          "current scientific status", "current authoritative")
    secs = [(m.start(), m.group(2).lower()) for m in re.finditer(r"^(#{1,3})\s+(.*)$", md, re.M)]

    def head(pos):
        h = ""
        for s, t in secs:
            if s <= pos:
                h = t
            else:
                break
        return h
    for pat in (r"[Nn]o lifetime is predicted (anywhere|in this project)",
                r"unsourced exponent",
                r"Solder fatigue[^.\n]{0,60}has no life law"):
        for m in re.finditer(pat, md):
            assert not any(c in head(m.start()) for c in CF), (pat, head(m.start()))


def test_relative_and_absolute_are_distinguished(status):
    al = status["architecture_life_0jr"]
    assert al["status"] == "RELATIVE LIFE VALIDATED; ABSOLUTE LIFE CONDITIONAL"
    assert status["mission_requirement_0k"]["N_required"] == "USER_INPUT_REQUIRED"
    assert status["verdict"]["g2_status"] == "NOT_TESTED"


# ---------------------------------------------------- Sec.2/3 decision map

def test_all_four_absolute_laws_are_applied(dm):
    r = dm[0]
    for a in ARCH:
        for k in LAWKEYS:
            assert f"{a}_{k}" in r


def test_no_robust_z1_fail_z2_pass_band_exists(dm):
    """The central Phase-0K result."""
    z1hi = max(float(dm[0][f"Z1_{k}"]) for k in LAWKEYS)
    z2lo = min(float(dm[0][f"Z2_{k}"]) for k in LAWKEYS)
    assert z2lo < z1hi, "if this ever reverses, a robust G2 band exists and the verdict changes"
    assert not any(r["architecture_decision"].startswith("ROBUST G2 REVERSAL") for r in dm)


def test_robust_regions(dm):
    lo = min(float(dm[0][f"{a}_{k}"]) for a in ARCH for k in LAWKEYS)
    hi = max(float(dm[0][f"{a}_{k}"]) for a in ARCH for k in LAWKEYS)
    assert 470 < lo < 480 and 3190 < hi < 3220
    for r in dm:
        n = float(r["N_required"])
        if n <= lo:
            assert all(r[f"{a}_status"] == "ROBUST PASS" for a in ARCH), n
        elif n > hi:
            assert all(r[f"{a}_status"] == "ROBUST FAIL" for a in ARCH), n


def test_model_form_spread_exceeds_architecture_separation(dm):
    """Why mission definition alone cannot decide G2."""
    spread = max(float(dm[0][f"Z1_{k}"]) for k in LAWKEYS) \
        / min(float(dm[0][f"Z1_{k}"]) for k in LAWKEYS)
    sep = min(float(dm[0][f"Z2_{k}"]) / float(dm[0][f"Z1_{k}"]) for k in LAWKEYS)
    assert spread > 5.0 and sep < 1.4
    assert spread > sep, "a 5.2x uncertainty cannot resolve a 1.3x effect"


def test_sole_blocker_claim_is_withdrawn(status):
    g = status["g2_decision_map"]["sole_blocker_claim"]
    assert "WITHDRAWN" in g and "TWO OPEN PIECES" in g
    assert "TWO OPEN PIECES" in status["verdict"]["g2_note_phase0jr"]


# ---------------------------------------------------- Sec.5/6/8 mission

def test_mission_contract_is_unpopulated_and_refuses_to_guess():
    cfg = yaml.safe_load(CFG.read_text())
    PH = {"USER_REQUIRED", "UNKNOWN", "NOT_APPLICABLE", "NOT_POPULATED", "UNPOPULATED"}
    for k in ("mission_source", "mission_type", "service_life_years",
              "cold_boots_per_day", "required_survival_fraction"):
        assert str(cfg[k]).strip() in PH, (k, cfg[k])
    import sys
    sys.path.insert(0, str(R / "scripts" / "phase0k"))
    from mission_requirement import evaluate
    n, why = evaluate(cfg)
    assert n is None and "mission_source" in why


def test_tool_refuses_a_qualification_count_as_mission():
    import sys
    sys.path.insert(0, str(R / "scripts" / "phase0k"))
    from mission_requirement import evaluate
    n, why = evaluate({"mission_source": "some spec", "mission_type": "QUALIFICATION",
                       "service_life_years": 5, "cold_boots_per_day": 1})
    assert n is None and "QUALIFICATION" in why


def test_tool_computes_when_properly_declared():
    import sys
    sys.path.insert(0, str(R / "scripts" / "phase0k"))
    from mission_requirement import evaluate
    n, why = evaluate({"mission_source": "owner memo X", "mission_type": "FIELD_MISSION",
                       "service_life_years": 5, "cold_boots_per_day": 1})
    assert n == pytest.approx(5 * 365.25, rel=1e-9)


def test_examples_are_labelled_illustrative():
    for r in rows("mission_requirement_examples.csv"):
        assert "ILLUSTRATIVE ONLY" in r["label"]


def test_no_mission_requirement_was_found_in_the_project(status):
    m = status["mission_requirement_0k"]
    assert "NOTHING found" in m["searched"]
    assert "TSV VIA COUNT" in m["searched"]
    assert "REFERENCE ONLY" in m["jedec_1000_cycles"]


# ---------------------------------------------------- Sec.9/10/29 identifiability

def test_one_condition_cannot_identify_the_law(status):
    a = status["absolute_life_identifiability"]
    assert "PROVEN ALGEBRAICALLY" in a["one_condition_cannot_identify_the_law"]
    assert "0" in a["one_condition_cannot_identify_the_law"]


def test_discrimination_is_governed_by_w_over_eps():
    d = rows("experiment_condition_discrimination.csv")
    for r in d:
        expect = max(float(r["w_over_eps_A"]), float(r["w_over_eps_B"])) \
            / min(float(r["w_over_eps_A"]), float(r["w_over_eps_B"]))
        assert float(r["D_discrimination"]) == pytest.approx(expect, rel=1e-3)


def test_best_pair_is_cold_versus_hot_and_is_resolvable():
    d = sorted(rows("experiment_condition_discrimination.csv"),
               key=lambda r: -float(r["D_discrimination"]))
    best = d[0]
    assert {best["cond_A"], best["cond_B"]} == {"COLD_SHALLOW", "HOT_SHALLOW"}
    assert float(best["D_discrimination"]) > 1.8
    assert float(best["sigma_beta6_n16"]) > 3.0          # resolvable at the pessimistic beta


def test_two_architectures_one_profile_does_not_discriminate():
    ec = {(r["arch"], r["condition"]): r for r in rows("experiment_condition_metrics.csv")}
    z1, z2 = ec[("Z1", "OP_BASELINE")], ec[("Z2", "OP_BASELINE")]
    rs = float(z1["M4_creep_strain"]) / float(z2["M4_creep_strain"])
    re_ = float(z1["M5_creep_energy_MJ_per_m3"]) / float(z2["M5_creep_energy_MJ_per_m3"])
    assert abs(rs / re_ - 1) < 0.10, "must be near-blind to model form"


def test_one_calibration_collapses_the_ambiguity():
    mp = rows("mission_vs_calibration_decision_map.csv")
    assert not any(r["decision"] == "MODEL-FORM AMBIGUOUS" for r in mp)
    assert any(r["decision"].startswith("G2 PASSED") for r in mp)
    for r in mp:
        assert "WHAT-IF" in r["label"]


def test_z4_excluded_by_value_of_information(status):
    v = status["absolute_life_identifiability"]["Z4_value_of_information"]
    assert "DO NOT FABRICATE" in v


# ---------------------------------------------------- Sec.33 no fake data

def test_no_experiment_is_claimed_to_have_been_run(status):
    assert "DESIGNED, NOT RUN" in status["absolute_life_identifiability"]["experiment_status"]
    plan = (OUT / "BOARD_LEVEL_CALIBRATION_PLAN.md").read_text()
    assert "HAS NOT BEEN RUN" in plan
    for r in rows("synthetic_calibration_sensitivity.csv"):
        assert "WHAT-IF" in r["label"]
        assert "NOT A MEASUREMENT" in r["label"]


# ---------------------------------------------------- Sec.25/31 claims and optimizer

def test_electrical_cost_is_not_overstated(status):
    e = status["electrical_cost_of_reliability_0k"]
    assert "RELATIVE" in e["current_statement"]
    assert "buys exactly X cycles" in e["forbidden"]
    assert "17 %" in e["honest_limit"]


def test_optimizer_still_not_built(status):
    assert status["meta"]["optimiser_built"] is False
    assert status["meta"]["optimiser_recommended"] is False


def test_priority_is_parallel(status):
    assert status["experimental_priority"]["recommendation"] == \
        "MISSION + EXPERIMENT IN PARALLEL"


# ---------------------------------------------------- Sec.27/28 artifacts

@pytest.mark.parametrize("name", [
    "PHASE0K_MISSION_AND_ABSOLUTE_LIFE_GATE.md", "DEFECT38_REPORT_PROPAGATION_AUDIT.md",
    "G2_DECISION_REGIONS.md", "g2_decision_map.csv", "SYSTEM_OWNER_MISSION_REQUEST.md",
    "ABSOLUTE_LIFE_IDENTIFIABILITY.md", "experiment_condition_discrimination.csv",
    "BOARD_LEVEL_CALIBRATION_PLAN.md", "sample_size_and_statistics.md",
    "failure_definition_alignment.md", "synthetic_calibration_sensitivity.csv",
    "mission_vs_calibration_decision_map.csv"])
def test_required_artifact_exists(name):
    p = OUT / name
    assert p.is_file() and p.stat().st_size > 200, name


@pytest.mark.parametrize("fig", list("ABCDEF"))
def test_required_figure_exists(fig):
    got = list(OUT.glob(f"FIG_0K_{fig}_*.png"))
    assert len(got) == 1 and got[0].stat().st_size > 10000, fig


def test_owner_request_asks_only_what_is_needed():
    t = (OUT / "SYSTEM_OWNER_MISSION_REQUEST.md").read_text()
    for k in ("service lifetime", "Survival target", "Cold boots", "workload thermal cycles",
              "high-power dwell", "fully powered down", "field mission or a qualification",
              "internal package-reliability target"):
        assert k in t, k
    assert "not** asking you for" in t
