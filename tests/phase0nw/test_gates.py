"""PHASE 0N-W --- the hard gate before any new ETM run (brief section 19)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0nw", "scripts/phase0mr", "scripts/phase0i", "scripts/phase0g",
          "scripts/phase0b", "scripts"):
    sys.path.insert(0, str(R / p))

GATES = R / "research" / "phase0nw" / "physical_gates.json"
DOC = R / "research" / "PHYSICAL_Z1_Z2_IMPLEMENTATION_AUDIT.md"


@pytest.fixture(scope="module")
def g():
    return json.loads(GATES.read_text())


def test_gate_table_is_regenerated_from_the_live_artifacts(g):
    """The table must be recomputed, not typed. DEFECT #57 shipped a hand-typed status
    table a full phase behind under a green audit."""
    import audit_physical_gates as A
    live = A.gates()[2]
    stored = g["gates"]
    assert len(live) == len(stored)
    for a, b in zip(live, stored):
        assert (a["area"], a["gate"], a["status"]) == (b["area"], b["gate"], b["status"]), (
            f"the stored gate table is stale: {b} vs live {a}")


def test_no_physical_result_lineage_exists_while_gates_are_open(g):
    """BLOCKING. results/phase0nw may not be created until every gate closes."""
    n_open = sum(1 for r in g["gates"] if r["status"] == "OPEN")
    assert n_open == g["n_open"]
    if n_open:
        lineage = R / "results" / "phase0nw"
        assert not lineage.exists(), (
            f"{n_open} gates are OPEN but a physical result lineage already exists at "
            f"{lineage} -- the brief forbids generating headline numbers before closure")


def test_the_open_gates_are_the_ones_we_say_they_are(g):
    """If this list shrinks, the closure must be demonstrated, not announced."""
    opens = {r["gate"] for r in g["gates"] if r["status"] == "OPEN"}
    assert opens == {
        "PCB-H1 thermal validation",
        "split VDD / GND TSV fields meshed",
        "per-tier material fidelity",
        "explicit supply/return",
        "physical ET result lineage",
    }, f"the open-gate set changed: {sorted(opens)}"


def test_closed_geometry_gates_are_backed_by_a_mesh_measurement(g):
    """Every IMPLEMENTED row must cite evidence, not merely assert a status."""
    for r in g["gates"]:
        if r["status"] == "IMPLEMENTED":
            assert r["evidence"] and r["evidence"] != "not implemented", r
            assert re.search(r"\d", r["evidence"]), (
                f"'{r['gate']}' is marked IMPLEMENTED with no measured evidence: "
                f"{r['evidence']}")


def test_audit_document_states_the_geometry_material_distinction():
    t = re.sub(r"\s+", " ", DOC.read_text())
    assert "It is **not** a material result." in t or "not** a material result" in t
    assert "OPEN" in t
    assert "49.6 %" in t and "69.5 %" in t, (
        "the audit must reconcile the out-of-cell fraction of the OPENING against the "
        "brief's substrate-footprint figure")


def test_audit_document_does_not_claim_the_package_is_closed():
    t = re.sub(r"\s+", " ", DOC.read_text()).lower()
    assert "physically closed" not in t
    assert re.search(r"no physical etm result lineage may be created|"
                     r"gates are open", t)
