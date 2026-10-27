"""PHASE 0N-AJ --- BGA count and pad count as solved design variables."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
for _p in ("scripts/phase0nw", "scripts/phase0m", "scripts/phase0mr", "scripts"):
    sys.path.insert(0, str(R / _p))

BGA = R / "research/phase0naj/bga_count_closure.json"
PADF = R / "research/phase0naj/pad_count_closure.json"


@pytest.fixture(scope="module")
def bga():
    if not BGA.exists():
        pytest.skip("run scripts/phase0naj_bga_count_closure.py")
    return json.loads(BGA.read_text())


@pytest.fixture(scope="module")
def pad():
    if not PADF.exists():
        pytest.skip("run scripts/phase0naj_pad_count_closure.py")
    return json.loads(PADF.read_text())


# --- BGA count ----------------------------------------------------------

def test_the_criterion_is_classified_and_unsourced(bga):
    m = bga["meta"]
    assert m["criterion_classification"] == "ENGINEERING_CRITERION"
    assert "no source" in m["criterion_provenance"].lower()
    assert "not a source_requirement" in m["criterion_provenance"].lower()
    assert "CONTEXT_ONLY" in m["em_literature_status"]


def test_peak_ball_current_exceeds_equal_share_everywhere(bga):
    """If this ever came out at 1.0, I_total/N would be adequate after all."""
    legal = [r for r in bga["rows"] if r.get("legal")]
    assert legal
    for r in legal:
        assert r["peak_over_equal_share"] > 1.0, r
    assert max(r["peak_over_equal_share"] for r in legal) > 1.5


def test_the_adopted_16_fails_its_own_criterion(bga):
    """The headline: 16+16 was sized by I_total/N <= 1.5 A, and the solved
    network puts the PEAK ball above 1.5 A even at the DC average."""
    for arch in ("Z1", "Z2"):
        c = bga["closure"][f"{arch}__DC_AVERAGE"]
        assert c["peak_at_adopted_16"] is not None
        assert c["peak_at_adopted_16"] > c["criterion_A"], arch
        assert c["adopted_16_passes"] is False, arch


def test_required_count_is_larger_than_the_adopted_one(bga):
    for arch in ("Z1", "Z2"):
        c = bga["closure"][f"{arch}__DC_AVERAGE"]
        if c["required_n_per_rail"] is not None:
            assert c["required_n_per_rail"] > 16, arch


def test_scenarios_are_never_merged_into_a_bracket(bga):
    keys = set(bga["closure"])
    for arch in ("Z1", "Z2"):
        for s in ("DC_AVERAGE", "HV_S0", "HV_S1", "HV_S2"):
            assert f"{arch}__{s}" in keys
    txt = json.dumps(bga)
    for bad in ("lower bound", "upper bound", "nominal bracket"):
        assert bad not in txt.lower(), bad


def test_unsatisfiable_scenarios_say_so_rather_than_picking_a_count(bga):
    for k, v in bga["closure"].items():
        if v["required_n_per_rail"] is None:
            assert v["status"] == "NOT_SATISFIABLE_IN_SWEPT_RANGE"
            assert v["best_achievable_peak_A"] > v["criterion_A"]


def test_crowding_is_declared_open_not_invented(bga):
    assert "OPEN" in bga["meta"]["crowding"]
    assert "AVERAGE" in bga["meta"]["crowding"]
    assert "no crowding multiplier is invented" in bga["meta"]["crowding"]


# --- pad count ----------------------------------------------------------

def test_pad_result_is_a_region_not_an_adopted_count(pad):
    assert pad["meta"]["selection_status"] == "ADMISSIBLE_REGION_ONLY"
    assert "adopted" not in json.dumps(pad["admissible_region"]).lower()
    assert "tautology" in pad["meta"]["why_no_single_count"]


def test_the_voltage_drop_floor_is_non_physical(pad):
    """N=4 satisfies the drop budget at ~5e6 A/cm^2 -- above the ACCELERATED
    Cu-Cu EM test regime. Drop was never the binding constraint."""
    assert pad["meta"]["drop_floor_current_density_A_cm2"] > 1.0e6
    assert "NON-PHYSICAL" in pad["meta"]["drop_floor_verdict"]
    assert "not the binding constraint" in pad["meta"]["drop_floor_verdict"]


def test_current_density_cases_are_context_only(pad):
    s = pad["meta"]["j_cases_status"]
    assert "CONTEXT_ONLY" in s
    assert "not a safe operating limit" in s
    assert "never as a rating" in s


def test_tighter_current_density_shrinks_the_region_from_below(pad):
    a = pad["admissible_region"]
    assert a["J_NONE"]["n_min"] < a["J_1e6"]["n_min"] <= a["J_1e5"]["n_min"] \
        <= a["J_1e4"]["n_min"]
    # the ceiling is geometric and must not move with a current constraint
    tops = {k: v["n_max"] for k, v in a.items() if v["n_max"]}
    assert len(set(tops.values())) == 1


def test_loss_span_is_still_reported(pad):
    assert pad["meta"]["loss_span_factor"] > 1000


# --- superseded results must not reappear as current --------------------

SUPERSEDED_PKG_RDL = {
    "-0.351": "imposed-current, supply-only cutout term",
    "5.13": "unconverged wrong-pitch Z1/Z2 package-RDL ratio",
    "0.55": "halved-Z1-ball-count package-RDL ratio",
}


def test_superseded_package_rdl_values_are_not_current_results():
    """Each was reported once and withdrawn. They may be NAMED as withdrawn,
    never presented as a result."""
    import re
    doc = (R / "research/phase0nai/PHASE_0NAI_NETWORK.md").read_text()
    for val, what in SUPERSEDED_PKG_RDL.items():
        for m in re.finditer(re.escape(val), doc):
            window = doc[max(0, m.start() - 400):m.end() + 400].lower()
            assert any(w in window for w in
                       ("artefact", "withdraw", "supersed", "historical",
                        "wrong twice", "imposed-current")), (val, what)


def test_the_manuscript_marks_the_frozen_loss_table_as_historical():
    tex = " ".join((R / "manuscript"
                    / "ETM_DVPD_JOURNAL_MANUSCRIPT.tex").read_text().split())
    assert "none of it is a current physical result" in tex
    assert "frozen Phase-0M-R3C result" in tex
    for stale in ("Intra-cell metal", "Vertical transitions",
                  "Bumps + package RDL"):
        assert stale in tex


def test_no_cutout_penalty_is_frozen_as_final():
    doc = (R / "research/phase0nai/PHASE_0NAI_NETWORK.md").read_text()
    assert "No cutout penalty is frozen here." in doc
    assert "magnitude is provisional" in doc
