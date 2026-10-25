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


# Gates we CLAIM are closed. Pinning the closed set is the safety-relevant direction:
# a gate must never close silently. New OPEN gates may appear freely.
CLOSED_IDS = {
    "board.h0_documented",
    "board.it968g_selected",
    "board.t_only_material_identical",
    "board.thickness_reaches_mesh",
    "config.z1_yaml_drives_mesh",
    "elec.aggregate_output_ripple",
    "elec.bga_bulk_dc_baseline",
    "elec.bga_power_ball_capacity",
    "elec.bga_rho_T_model",
    "elec.branch_average_currents",
    "elec.current_waveforms_defined",
    "elec.cutout_penalty_isolated",
    "elec.interface_primary_selected",
    "elec.microbump_series_resistance",
    "elec.one_owner_per_conductor",
    "elec.pad_density_sensitivity",
    "elec.phase_group_index_mapping",
    "elec.pkg_rdl_sheet_model",
    "elec.power_path_graph",
    "elec.rms_current_model",
    "elec.source_pad_count",
    "elec.source_pad_geometry",
    "elec.source_pad_loss",
    "elec.source_pad_resistance",
    "elec.tsv_conductor_geometry_consistent",
    "elec.tsv_count_justified",
    "elec.tsv_lattice_exact",
    "elec.tsv_transition_audited",
    "elec.z1_pkg_hv_rdl_geometry",
    "elec.z1_power_bookkeeping",
    "elec.z1_rail_model",
    "elec.z1_tsv_sizing",
    "elec.z2_lv_rms_current",
    "elec.z2_pkg_hv_rdl_geometry",
    "elec.z2_rail_model",
    "elec.z2_tsv_sizing",
    "geom.bga_lattice_single_source",
    "geom.bga_symmetric_feed",
    "geom.cell_coordinate_single_source",
    "geom.inventory_equal",
    "geom.stack_conservation",
    "geom.z1_complete_stack",
    "geom.z1_hs_present",
    "geom.z1_selected_devices",
    "geom.z2_49_cells",
    "geom.z2_cutout_conforming",
    "geom.z2_descends_into_cutout",
    "geom.z2_full_stack",
    "geom.z2_no_medium_outside_cells",
    "geom.z2_no_overlap",
    "geom.z2_no_slab",
    "geom.z2_out_of_cell_defined",
    "lit.bga_current_rule",
    "lit.interconnect_matrix",
    "mat.bga_alloy_provenance",
    "mat.copper_resistivity_canonical",
    "mat.microbump_separate",
    "mat.rdl_tier_tensor",
}


def test_registry_covers_every_required_gate(g):
    """The registry must not be able to say 'ready for ETM' by omitting a requirement."""
    import audit_physical_gates as A
    ids = {r["id"] for r in g["gates"]}
    assert set(A.ALL_REQUIRED) == ids, (
        f"missing {sorted(set(A.ALL_REQUIRED) - ids)}; "
        f"undeclared {sorted(ids - set(A.ALL_REQUIRED))}")


def test_removing_a_required_gate_definition_fails(monkeypatch):
    """NEGATIVE: drop a required gate and the registry must refuse to build.

    This is the regression the brief asks for. The previous registry reported
    '5 of 26 OPEN' while thermal BC selection, mesh convergence and the 528-site search
    were simply not in it -- an omission is indistinguishable from a pass unless the
    manifest is checked.
    """
    import audit_physical_gates as A
    patched = dict(A.REQUIRED_GATES)
    patched["thermal"] = list(patched["thermal"]) + ["therm.a_requirement_nobody_evaluates"]
    monkeypatch.setattr(A, "REQUIRED_GATES", patched)
    monkeypatch.setattr(
        A, "ALL_REQUIRED", [x for v in patched.values() for x in v])
    with pytest.raises(AssertionError, match="INCOMPLETE"):
        A.gates()


def test_no_gate_closes_without_being_listed_as_closed(g):
    closed = {r["id"] for r in g["gates"] if r["status"] in ("IMPLEMENTED", "SPECIFIED")}
    assert closed == CLOSED_IDS, (
        f"silently closed: {sorted(closed - CLOSED_IDS)}; "
        f"regressed: {sorted(CLOSED_IDS - closed)}")


def test_status_counts_are_reported_separately(g):
    """SPECIFIED is not IMPLEMENTED and neither is VALIDATED; "closed" hides that."""
    from collections import Counter
    c = Counter(r["status"] for r in g["gates"])
    assert c["VALIDATED"] == 0, (
        "a gate claims VALIDATED but no solve has been run in this package")
    assert c["SPECIFIED"] > 0 and c["IMPLEMENTED"] > 0
    doc = (R / "research" / "PHYSICAL_Z1_Z2_IMPLEMENTATION_AUDIT.md").read_text()
    assert "| VALIDATED |" in doc and "are VALIDATED" in doc


def test_every_open_gate_states_why(g):
    for r in g["gates"]:
        if r["status"] == "OPEN":
            assert r["evidence"] and len(r["evidence"]) > 8, r


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
