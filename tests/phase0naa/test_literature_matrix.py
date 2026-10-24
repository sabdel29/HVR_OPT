"""PHASE 0N-AA --- literature provenance must not be overclaimed (brief 0, 5, 33)."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts"))

MATRIX = R / "research" / "phase0naa" / "interconnect_literature_matrix.csv"
SUMMARY = R / "research" / "phase0naa" / "literature_summary.json"
META = R / "research" / "phase0naa" / "doi_metadata.json"


@pytest.fixture(scope="module")
def rows():
    return list(csv.DictReader(MATRIX.open()))


def test_every_doi_resolved(rows):
    meta = {m["doi"]: m for m in json.loads(META.read_text())}
    for r in rows:
        m = meta.get(r["doi"])
        assert m and m.get("resolved"), f"{r['doi']} did not resolve"
        assert m.get("title"), f"{r['doi']} has no title"


def test_titles_in_the_matrix_come_from_crossref_not_from_us(rows):
    meta = {m["doi"]: m for m in json.loads(META.read_text())}
    for r in rows:
        assert r["paper_title"] == meta[r["doi"]]["title"], (
            f"{r['doi']}: matrix title differs from the resolved record")


def test_applicability_is_one_of_the_three_classes(rows):
    for r in rows:
        assert r["applicability"] in ("DIRECT", "CLOSE_ANALOG", "CONTEXT_ONLY")


def test_no_context_only_source_sets_a_parameter(rows):
    """CONTEXT_ONLY may motivate a bound; it may never establish an allowable."""
    for r in rows:
        if r["applicability"] == "CONTEXT_ONLY":
            assert not r["final_status"].startswith("SOURCE_BACKED"), r["doi"]
            assert "allowable =" not in r["what_it_establishes"]


def test_no_accelerated_condition_is_called_an_allowable(rows):
    """The central rule: accelerated EM stress is failure physics, not a design limit."""
    flat = MATRIX.read_text().lower()
    for bad in ("em-safe limit =", "allowable = 4600", "allowable = 1 ma",
                "design allowable of"):
        assert bad not in flat, f"the matrix asserts an allowable: {bad!r}"
    acc = [r for r in rows if "accelerated" in r["paper_conditions"].lower()]
    assert acc, "no accelerated-condition rows present"
    for r in acc:
        assert "NOT a design allowable" in r["transferability_caveat"]


def test_no_parameter_is_marked_source_backed_without_a_direct_source(rows):
    direct = [r for r in rows if r["applicability"] == "DIRECT"]
    backed = [r for r in rows if r["final_status"].startswith("SOURCE_BACKED")]
    assert len(backed) <= len(direct), (
        "a parameter claims SOURCE_BACKED with no DIRECT source behind it")


def test_the_bga_rule_remains_bounded_not_em_safe(rows):
    r = next(x for x in rows if x["parameter"].startswith("I_ball_max"))
    assert r["final_status"].startswith("BOUNDED")
    assert "NOT an EM-safe limit" in r["final_status"]
    assert r["applicability"] == "CLOSE_ANALOG"


def test_contact_resistance_remains_open(rows):
    r = next(x for x in rows if "contact resistance" in x["parameter"].lower())
    assert r["final_status"].startswith("OPEN")
    assert "not modelled" in r["what_it_establishes"].lower()


def test_tsv_allowable_is_explicitly_refused(rows):
    r = next(x for x in rows if x["parameter"] == "TSV J allowable")
    assert r["current_value_status"] == "none asserted"
    assert r["final_status"].startswith("OPEN")
    assert "category error" in r["what_it_establishes"]


def test_operating_point_is_computed_from_the_live_model():
    s = json.loads(SUMMARY.read_text())
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_lm", R / "scripts" / "phase0naa_literature_matrix.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    live = m.operating_points()
    for a in ("Z1", "Z2"):
        assert live[a]["j_nominal_ball_A_cm2"] == pytest.approx(
            s["operating_points"][a]["j_nominal_ball_A_cm2"], rel=1e-9)
        # the transferred crowding factor must stay gone
        assert live[a]["j_local_A_cm2"] is None


def test_our_bga_margin_against_the_mildest_accelerated_condition():
    """1178 A/cm2 against 2300 A/cm2 is under 2x. That is NOT a comfortable margin,
    and nothing in the repo may describe 1.5 A/ball as conservative without it."""
    s = json.loads(SUMMARY.read_text())
    j = s["operating_points"]["Z1"]["j_nominal_ball_A_cm2"]
    assert 2300.0 / j < 2.5, f"margin to the mildest accelerated condition is {2300/j:.2f}x"
