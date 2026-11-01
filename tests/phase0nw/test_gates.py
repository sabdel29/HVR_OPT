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
    # elec.z2_pkg_hv_rdl_geometry is SUPERSEDED, not closed: the primary Z2 is direct-fed and
    # has no package 48 V RDL (the BGA-fed sheet belongs to the control only)
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
    # --- Phase 0N-AI: the package network. Listed here deliberately, because
    # --- this test exists to stop a gate closing without someone saying so.
    "elec.bga_voltage_fed_network",          # sharing is now an output
    "elec.pkg_rdl_return_solved",            # return sheet solved, not discarded
    "elec.pkg_rdl_network_converged",        # SPECIFIED only: Z1 still fails
    "elec.z1_network_nonconvergence_diagnosed",
    # --- Phase 0N-AJ: gate-consistency pass against HEAD
    "elec.bga_network_sharing",   # the network now solves the split
    "elec.rdl_loss_recomputed",   # SPECIFIED: closed for Z2, open for Z1
    "elec.bga_lattice_mirror_closed",
    "elec.bga_count_closed",
    "elec.pad_count_admissible_region",
    "elec.intravr_fidelity_ladder",
    "elec.package_rdl_hv_recomputed",   # SPECIFIED: recomputed for Z2
    # --- Final closure: the physical lineage. Each closes on a measured artifact in
    # --- research/final_closure; listed so that none closes without being named.
    "results.physical_etm_lineage",
    "therm.et_fixed_point_converged",
    "therm.tier_aware_heat_map",
    "therm.bc_selected",                       # SPECIFIED: one declared boundary
    "therm.z2_passive",                        # counted: no film inside the cutout
    "elec.energy_conservation_verified",
    "elec.loss_audit_frozen",
    "elec.tsv_resistance_temperature_dependent",
    "mech.bga_528_site_search",
    "mech.mesh_convergence",                   # IMPLEMENTED converged / SPECIFIED bounded
    "local.solder_rerun_at_new_critical_site",
    "tsv.fe_copper_representation",
    "mat.rdl_tensor_transfer_validated",
    "elec.intravr_horizontal_recomputed",      # SPECIFIED
    "elec.intravr_vertical_recomputed",        # SPECIFIED
    "elec.package_rdl_lv_recomputed",          # SPECIFIED: absent, alternative quantified
    "elec.bga_loss_recomputed",                # SPECIFIED: scenario-defined RMS
    # --- Final closure, class B: each closes on a run on the production mesh at HV-S0
    # --- (or a network bound) recorded in research/final_closure/classB_resolution.csv.
    # --- The material gates mat.gan/mlcc/inductor_tier_bounded deliberately stay OPEN:
    # --- an assumed bracket resolves the paper's dependence, it does not bound the property.
    "board.h1_meshed",
    "board.h1_thermal_validated",              # only on H1 vs H0 same grid within 2 %
    "board.eta_sensitivity_run",
    "board.t_only_comparison_run",
    "therm.h0_h1_compared",
    "therm.z2_cooled",
    "tsv.density_sensitivity_run",
    "mech.f1_f2_bracket_run",
    "mech.t_only_mechanical",
    "elec.contact_resistance_bounded",         # SPECIFIED: network sweep
    "elec.rdl10um_electrical_model",           # SPECIFIED: network sweep
    "elec.pad_loss_closed",                    # SPECIFIED: B2, magnitude bounded by a run
    # --- Direct-fed Z2 (Z2_DIRECT_FEED_ARCHITECTURE.md): each closes on the corrected
    # --- lineage's mesh, ledger, crossover sweep or a class-B run on the production mesh.
    "arch.z2_direct_feed_power_path",          # no package 48 V term in any primary Z2 case
    "elec.direct_feed_crossover",              # swept R*, a requirement, never a value
    "elec.direct_feed_heat_location",          # class B: feed loss deposited in the package
    "geom.sidewall_clearance_baseline",        # measured: 0 converter elements in the ring
    "geom.sidewall_clearance",                 # class B: sidewall-filled construction run
    "geom.vr_attach_explicit",                 # measured attach tier, 30 um
    "geom.vr_attach_height",                   # class B: 20 / 40 um attach
    "geom.vr_attach_density",                  # class B: published 15/30 and 30/80 um lattices
    "mech.bga_population",                     # class B: 420/528 Z2 BGA field
    "therm.backside_interface",                # class B: backside plate behind a TIM
    "therm.cooling_model_form",                # class B: Icepak-equivalent coefficient
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


# ===================================================================
# Phase 0N-AJ: a gate must describe HEAD, not the phase it was written in.
# ===================================================================

#: phrases that assert something does NOT exist. Any gate carrying one is
#: making a claim about HEAD that can be checked against HEAD.
NONEXISTENCE = (
    "does not exist", "no artifact exists", "not run", "has NOT been built",
    "no package rdl network", "cannot be solved", "is assumed",
)

#: things that DID NOT exist in an earlier phase and DO exist now. A gate may
#: not claim otherwise, whatever its status.
NOW_EXISTS = {
    "the voltage-fed package network": "research/phase0nai/voltage_fed_network.json",
    "the Z1 convergence diagnostic": "research/phase0nai/z1_convergence_diagnostic.json",
    "the intra-VR resistance graph": "results/phase0m/intra_vr_routing_nets.csv",
}


def test_every_named_artifact_that_now_exists_really_does(g):
    for what, rel in NOW_EXISTS.items():
        assert (R / rel).exists(), f"{what} is missing: {rel}"


def test_no_gate_claims_a_model_absent_that_now_exists(g):
    """The exact contradiction this phase was asked to resolve: one gate said
    'no package RDL network exists to produce the real split' while another
    said the voltage-fed network was IMPLEMENTED. Both cannot describe HEAD."""
    bad = []
    for r in g["gates"]:
        e = r["evidence"].lower()
        if "no package rdl network" in e and "supersedes" not in e:
            bad.append(r["id"])
        # equal sharing is DISPROVEN at HEAD; no gate may present it as the
        # framework's current behaviour
        if "equal sharing is assumed" in e and "supersedes" not in e:
            bad.append(r["id"])
    assert not bad, f"gates describing a superseded model as current: {bad}"


def test_nonexistence_claims_are_either_true_or_marked_superseded(g):
    """A closed gate may not rest on 'not run' / 'no artifact exists'."""
    offenders = []
    for r in g["gates"]:
        e = r["evidence"].lower()
        if r["status"] in ("IMPLEMENTED", "VALIDATED") and \
                any(p in e for p in NONEXISTENCE) and "supersedes" not in e:
            offenders.append((r["id"], r["status"]))
    assert not offenders, (
        "closed gates whose evidence says the thing does not exist: %s"
        % offenders)


def test_bga_sharing_gate_describes_the_solved_split(g):
    row = {r["id"]: r for r in g["gates"]}["elec.bga_network_sharing"]
    assert row["status"] == "IMPLEMENTED"
    e = row["evidence"]
    assert "SUPERSEDES" in e, "the retracted wording must be named, not deleted"
    assert "DISPROVEN" in e, (
        "equal sharing is not merely unproven here -- the network disproves it, "
        "which is what invalidates I_total/N_ball as a sizing criterion")


def test_package_rdl_geometry_gates_do_not_quote_the_withdrawn_ratio(g):
    """5.13x and 0.55x were withdrawn; they may be NAMED as withdrawn but must
    never read as a current result."""
    for gid in ("elec.z1_pkg_hv_rdl_geometry", "elec.z2_pkg_hv_rdl_geometry"):
        e = {r["id"]: r for r in g["gates"]}[gid]["evidence"]
        for bad in ("5.13x", "0.55", "-0.351"):
            if bad in e:
                assert any(w in e for w in ("WITHDRAWN", "SUPERSEDED",
                                            "HISTORICAL")), (gid, bad)


def test_status_counts_sum_to_the_gate_total(g):
    import collections
    c = collections.Counter(r["status"] for r in g["gates"])
    assert sum(c.values()) == len(g["gates"])
    md = (R / "research/PHYSICAL_Z1_Z2_IMPLEMENTATION_AUDIT.md").read_text()
    # every status that occurs must appear as its own row, SUPERSEDED included
    for k, v in c.items():
        assert f"| {k} | {v} |" in md, f"status {k}={v} missing from the table"
    assert f"| **total** | **{len(g['gates'])}** |" in md


# ===================================================================
# Phase 0N-AK: contradictions between a gate and the gates it depends on.
# ===================================================================

def test_no_gate_blocks_on_a_dependency_that_is_already_closed(g):
    """elec.bga_loss_recomputed said it waited on 'RMS-current AND
    network-sharing closure' while elec.bga_network_sharing was IMPLEMENTED."""
    by = {r["id"]: r for r in g["gates"]}
    closed = {"IMPLEMENTED", "VALIDATED", "SPECIFIED"}
    deps = {
        "network-sharing": "elec.bga_network_sharing",
        "network sharing": "elec.bga_network_sharing",
    }
    bad = []
    for r in g["gates"]:
        e = r["evidence"].lower()
        for phrase, dep in deps.items():
            if phrase in e and "supersedes" not in e:
                if by.get(dep, {}).get("status") in closed:
                    bad.append((r["id"], phrase, dep))
    assert not bad, f"gates blocking on an already-closed dependency: {bad}"


def _strip_retractions(text):
    """Remove the wording a gate explicitly says it SUPERSEDES, so quoting a
    retracted phrase is not mistaken for asserting it."""
    return re.sub(r"SUPERSEDES[^.]*?'[^']*'", " ", text)


def test_no_gate_calls_the_hv_scenarios_a_bracket(g):
    """HV-S0/S1/S2 are named scenarios. From an average current alone there is
    no finite RMS upper bound, so 'bracket' is not loose here, it is wrong.

    A material or geometry range legitimately IS a bracket; only the HV RMS
    scenarios may not be called one.
    """
    bad = []
    for r in g["gates"]:
        e = _strip_retractions(r["evidence"])
        for m in re.finditer(r"bracket", e, re.I):
            window = e[max(0, m.start() - 160):m.end() + 160]
            about_hv = re.search(r"\bRMS\b|HV-S[012]", window, re.I)
            negated = re.search(r"not a bracket|NAMED SCENARIOS", window, re.I)
            if about_hv and not negated:
                bad.append((r["id"], window.strip()[:90]))
    assert not bad, f"gates calling the HV RMS scenarios a bracket: {bad}"


def test_no_gate_says_only_the_old_R3C_value_exists_when_one_was_recomputed(g):
    import json
    led = json.loads(
        (R / "research/phase0nab/interconnect_loss.json").read_text())
    hv_live = any(led[a]["terms"]["P_pkg_RDL_HV_supply"]["maturity"]["loss"]
                  != "OPEN" for a in ("Z1", "Z2"))
    by = {r["id"]: r for r in g["gates"]}
    row = by["elec.package_rdl_hv_recomputed"]
    if hv_live:
        assert "SUPERSEDES" in row["evidence"], (
            "the retracted wording must be named, not deleted")
        live = _strip_retractions(row["evidence"]).lower()
        assert "still has only the phase-0m-r3c value" not in live
        assert by["elec.package_rdl_hv_recomputed"]["status"] != "OPEN"


def test_historical_gates_are_superseded_not_open(g):
    """A gate kept only to stop an old claim returning is not 'work to do'."""
    for r in g["gates"]:
        if r["id"].endswith("_HISTORICAL"):
            assert r["status"] == "SUPERSEDED", (r["id"], r["status"])


def test_superseded_gates_exist_and_are_counted(g):
    import collections
    c = collections.Counter(r["status"] for r in g["gates"])
    assert c["SUPERSEDED"] >= 3
    assert sum(c.values()) == len(g["gates"])
