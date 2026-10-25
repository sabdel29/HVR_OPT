"""PHASE 0N-AH --- the computational story must not overclaim."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts"))

D = R / "research" / "phase0nah"


@pytest.fixture(scope="module")
def hier():
    return list(csv.DictReader((D / "model_hierarchy.csv").open()))


@pytest.fixture(scope="module")
def claims():
    return list(csv.DictReader((D / "computational_claim_matrix.csv").open()))


def test_thermal_and_mechanical_are_labelled_FEM(hier):
    """VERIFIED AGAINST HEAD: ccxio writes C3D8 / C3D8I and runs CalculiX."""
    by = {h["stage"]: h for h in hier}
    assert by["package thermal field"]["type"] == "FEM"
    assert by["global mechanics"]["type"] == "FEM"
    assert "nonlinear" in by["local solder"]["type"].lower()
    src = (R / "scripts/phase0b/etm/ccxio.py").read_text()
    assert "C3D8" in src and "C3D8I" in src


def test_no_stage_claims_analytical_when_it_runs_an_fe_solver(hier):
    for h in hier:
        if "thermal field" in h["stage"] or "mechanic" in h["stage"] or \
                "solder" in h["stage"]:
            assert "ANALYTICAL" not in h["type"]


def test_evidence_classes_distinguish_validation_from_convergence(hier):
    classes = {h["evidence_class"] for h in hier}
    assert classes <= {"VALIDATION", "VERIFICATION", "CONVERGENCE"}
    conv = [h for h in hier if h["evidence_class"] == "CONVERGENCE"]
    assert conv, "some stages have no external reference and must say so"
    for h in conv:
        assert "none" in h["independent_reference"].lower() or not h["error"] or \
            "convergence" in h["error"].lower() or "%" in h["error"]


def test_no_commercial_speedup_is_claimed():
    s = json.loads((D / "model_hierarchy_summary.json").read_text())
    assert s["commercial_speedup"] is None
    assert "NOT ESTABLISHED" in s["commercial_status"]
    md = (D / "commercial_benchmark_status.md").read_text()
    assert "No controlled commercial speedup has been established" in md
    assert "No speedup against a higher-fidelity reference is claimed." in md


def test_the_speedup_claim_is_marked_unsupported(claims):
    by = {c["claim"]: c for c in claims}
    bad = [c for c in claims if "faster than commercial" in c["claim"]]
    assert bad and bad[0]["classification"] == "NOT_SUPPORTED"
    single = [c for c in claims if "single accuracy percentage" in c["claim"]]
    assert single and single[0]["classification"] == "NOT_SUPPORTED"


def test_literature_speedups_are_not_transferred(claims):
    lit = [c for c in claims if c["classification"] == "LITERATURE_CONTEXT"]
    assert lit
    for c in lit:
        assert "NOT transferred" in c["evidence"] or "not transferred" in c["evidence"]


def test_runtime_is_flagged_historical():
    rows = list(csv.DictReader((D / "runtime_breakdown.csv").open()))
    assert rows
    for r in rows:
        assert r["provenance"] == "HISTORICAL_FROZEN_R3C_RUNTIME"
    s = json.loads((D / "model_hierarchy_summary.json").read_text())
    assert "has NOT been re-benchmarked" in s["runtime_caveat"]


def test_measured_claims_point_at_real_numbers(claims):
    for c in claims:
        if c["classification"] == "MEASURED":
            assert any(ch.isdigit() for ch in c["evidence"])


def test_generality_audit_separates_spec_from_hardcoding():
    rows = list(csv.DictReader((D / "architecture_generality_audit.csv").open()))
    kinds = {r["classification"] for r in rows}
    assert kinds <= {"SYSTEM_SPECIFICATION", "MODEL_LIMITATION",
                     "ACCIDENTAL_HARDCODING", "DERIVED"}
    hard = [r for r in rows if r["classification"] == "ACCIDENTAL_HARDCODING"]
    assert hard, "the audit must name what is actually hard-coded"
    lim = [r for r in rows if r["classification"] == "MODEL_LIMITATION"]
    assert any("topology" in r["note"] for r in lim), (
        "a different converter topology needs a new model, not a config change")


def test_the_framework_is_not_described_as_replacing_fem():
    import re as _re
    # markdown wraps, so a phrase can straddle a newline -- compare flattened, the same
    # trap the Phase-0N-V prose guards hit
    md = _re.sub(r"\s+", " ", (D / "MODEL_HIERARCHY.md").read_text().replace("**", ""))
    assert "not an analytical framework that replaces FEM" in md
    assert "Convergence is not accuracy" in md
    assert "no single framework accuracy percentage" in md.lower()
    assert "both are finite element" in md.lower()
