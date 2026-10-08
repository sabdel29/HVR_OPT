"""Phase 0M-R3 Section 23 --- guards for semantics, structure and realizability.

Every hard guard is negative-tested: the failure it exists to catch is injected with the
REAL offending text recovered from the delivered report, and the guard must fire.
"""
from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0mr3", "scripts/phase0mr2", "scripts/phase0mr", "scripts/phase0i",
          "scripts/phase0f", "scripts/phase0m", "scripts"):
    sys.path.insert(0, str(R / p))

import semantic_audit as SA                                             # noqa: E402

OUT = R / "results" / "phase0mr3"
HIST = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
C = SA.load()
RC = yaml.safe_load((R / "configs/phase0mr3/realizability_contract.yaml").read_text())


def clean() -> str:
    """A minimal report satisfying every rule, used as the PASS baseline."""
    g = ", ".join(C["meta"]["gates"])
    return f"""---
title: "t"
date: "2026-09-19"
---

# Provenance and tool versions

| Item | Value |
|:--|:--|
| Report generated | 2026-09-19 |
| Repository baseline | 2026-09-08 |
| Phase completed | {C["meta"]["gates"][-1]}, 2026-09-19 |
| Full-wave EM available | PALACE NOT FOUND on this system |

# Executive Summary

**Method.** {SA.NUMWORD[len(C["meta"]["gates"])]} sequential falsification gates ({g}), each designed so a negative
result would stop the project.

G2 is blocked by three independent blockers: N_required, absolute N_f, and an admissible
mechanical allowable.

# Governing Equations

x

# Electrical Model Validation

x

# Thermal Model Validation

The model has a domain hole, but the production point is not in it: the production point
at 27 g/s sits at Re = 1264.8, inside the validated laminar domain. The 50 g/s comparison
point is the one inside the gap.

# Mechanical Model Validation

The FE output is a local fatigue-relevant inelastic response metric.

# Architecture Comparison

x

# Model Defects Discovered and Fixed

x

# Uncertainty and Fidelity Ladder

x

# Next Steps --- prioritised roadmap

x
"""


# ================================================= A/B semantics and stale sentences
class TestSemantics:
    def test_the_clean_baseline_passes_every_rule(self):
        assert SA.audit(clean(), C) == []

    @pytest.mark.parametrize("cid,sw", [
        (c["claim_id"], s) for c in C["claims"] for s in c.get("stale_wording", [])])
    def test_each_REAL_stale_sentence_is_caught(self, cid, sw):
        """Verbatim text recovered from the delivered Phase-0M-R2 report."""
        cl = next(c for c in C["claims"] if c["claim_id"] == cid)
        tgt = cl["required_in"][0]
        b = clean()
        b = (b.replace('date: "2026-09-19"', sw) if tgt == "__frontmatter__"
             else b.replace(f"# {tgt}\n", f"# {tgt}\n\n{sw}\n"))
        assert any(f["rule_id"] == cid for f in SA.audit(b, C)), cid

    def test_a_nearby_retraction_does_NOT_clear_a_self_contradiction(self):
        """The real failure: an unrelated 'WITHDRAWN' in the same paragraph cleared both
        the cooling and the 'measures DAMAGE' wordings in Phase 0M-R2."""
        sw = next(c for c in C["claims"]
                  if c["claim_id"] == "cooling_production_point_not_in_gap")["stale_wording"][0]
        b = clean().replace("# Thermal Model Validation\n",
                            f"# Thermal Model Validation\n\n{sw} Its numbers are WITHDRAWN.\n")
        assert any(f["rule_id"] == "cooling_production_point_not_in_gap"
                   for f in SA.audit(b, C))


# ================================================= cross-field invariants
class TestCrossField:
    def test_G2_single_blocker_wording_fails(self):
        b = clean().replace("# Executive Summary\n",
                            "# Executive Summary\n\nthis is the single blocking item "
                            "for G2 and for any constraint-based optimizer\n")
        assert any(f["rule_id"] == "g2_blocker_count_consistent" for f in SA.audit(b, C))

    def test_naming_the_hole_without_the_production_point_fails(self):
        b = clean().replace(
            "The model has a domain hole, but the production point is not in it: the "
            "production point\nat 27 g/s sits at Re = 1264.8, inside the validated "
            "laminar domain. The 50 g/s comparison\npoint is the one inside the gap.",
            "The cooling model has a domain hole.")
        assert any(f["rule_id"] == "cooling_hole_and_production_point"
                   for f in SA.audit(b, C))

    def test_calling_the_FE_output_damage_fails(self):
        b = clean().replace("# Mechanical Model Validation\n",
                            "# Mechanical Model Validation\n\nsince Phase 0I "
                            "it measures DAMAGE and not only load\n")
        assert any(f["rule_family"] == "cross_field" for f in SA.audit(b, C))

    def test_claiming_a_validated_relative_life_fails(self):
        b = clean().replace("# Executive Summary\n",
                            "# Executive Summary\n\nthe validated relative life is 1.19x\n")
        assert any(f["rule_id"] == "metric_terminology_ladder" for f in SA.audit(b, C))

    def test_authorising_the_optimizer_fails(self):
        b = clean().replace("# Executive Summary\n",
                            "# Executive Summary\n\nthe optimizer is now permitted\n")
        assert any(f["rule_id"] == "optimizer_state_consistent" for f in SA.audit(b, C))

    def test_claiming_an_absent_solver_fails(self):
        b = clean().replace("| Full-wave EM available | PALACE NOT FOUND on this system |",
                            "| Full-wave EM available | PALACE (built, functional) |")
        assert any(f["rule_id"] == "tool_availability_consistent" for f in SA.audit(b, C))


# ================================================= C/D structural
class TestStructural:
    def test_a_duplicated_paragraph_fails(self):
        """The real defect: four identical copies shipped in Phase 0M-R2."""
        para = ("**Scope of this section.** " + "x" * 260)
        b = clean().replace("# Model Defects Discovered and Fixed\n",
                            f"# Model Defects Discovered and Fixed\n\n{para}\n\n{para}\n")
        assert any(f["rule_id"] == "no_duplicate_paragraph" for f in SA.audit(b, C))

    def test_a_single_copy_passes(self):
        para = ("**Scope of this section.** " + "x" * 260)
        b = clean().replace("# Model Defects Discovered and Fixed\n",
                            f"# Model Defects Discovered and Fixed\n\n{para}\n")
        assert not any(f["rule_id"] == "no_duplicate_paragraph" for f in SA.audit(b, C))

    def test_a_duplicated_sentinel_block_fails(self):
        b = clean() + "\n<!-- BEGIN GENERATED: x -->\n<!-- END GENERATED: x -->\n" * 2
        assert any(f["rule_id"] == "sentinel_unique" for f in SA.audit(b, C))

    def test_a_bare_report_date_row_fails(self):
        b = clean().replace("| Report generated | 2026-09-19 |",
                            "| Report date | 2026-09-08 |")
        assert any(f["rule_id"] == "date_coherence" for f in SA.audit(b, C))

    def test_an_incomplete_gate_list_fails(self):
        # drop the last gate, whichever it is, rather than pinning its name
        b = clean().replace(", " + C["meta"]["gates"][-1] + ")", ")")
        assert any(f["rule_id"] == "gate_count" for f in SA.audit(b, C))

    def test_the_delivered_report_is_clean(self):
        assert SA.audit(HIST.read_text(), C) == []

    def test_the_repair_script_is_idempotent(self):
        before = HIST.read_text()
        r = subprocess.run([sys.executable, str(R / "scripts/phase0mr3/repair_report.py")],
                           capture_output=True, text=True, cwd=str(R))
        assert r.returncode == 0, r.stderr[-800:]
        assert HIST.read_text() == before


# ================================================= realizability contract
class TestRealizabilityContract:
    def test_the_contract_was_frozen_before_any_candidate(self):
        assert RC["meta"]["frozen_before"] == "any candidate evaluation"
        assert len(RC["conditions"]) >= 15

    def test_OPEN_inputs_cap_the_verdict_below_PROVEN(self):
        """Two conditions depend on OPEN clearances, so PROVEN is unreachable."""
        opens = [k for k, v in RC["conditions"].items() if v["provenance"] == "OPEN"]
        assert opens, "if nothing is OPEN the cap no longer applies and this must be revisited"
        for tag in ("Z1", "Z2"):
            c = yaml.safe_load(
                (R / f"configs/phase0mr3/frozen_realizable_{tag}.yaml").read_text())
            assert c["verdict"] == "CONDITIONAL_REALIZABLE", tag

    def test_OPEN_is_never_collapsed_into_PASS(self):
        assert "OPEN" in RC["verdict_levels"]
        assert "never" in RC["verdict_levels"]["OPEN"]["definition"].lower()

    def test_forbidden_repairs_are_declared(self):
        f = " ".join(RC["forbidden_repairs"]).lower()
        for must in ("inventing", "scaling", "1 kw", "package"):
            assert must in f, must


# ================================================= G-O feasibility guards
class TestFeasibilityGuards:
    def test_every_route_of_the_frozen_pair_fits(self):
        rows = list(csv.DictReader((OUT / "routing_feasibility_candidates.csv").open()))
        assert rows
        bad = [r for r in rows if r["feasible"] != "True"]
        assert bad == [], bad

    def test_the_binding_net_was_vertical_not_lateral(self):
        """Filtering the route list to lateral nets hid the only failing net."""
        rows = [r for r in csv.DictReader(
            (OUT / "realizability_failure_matrix.csv").open()) if r["corner"] == "BEST"]
        vert = [r for r in rows if r["routing_worst_geom"] == "vertical"]
        assert vert, "the worst routing net must be identified by geometry, not assumed"

    def test_area_height_and_routing_all_pass_for_the_frozen_pair(self):
        for tag in ("Z1", "Z2"):
            c = yaml.safe_load(
                (R / f"configs/phase0mr3/frozen_realizable_{tag}.yaml").read_text())
            m = c["margins_at_worst_corner"]
            for k in ("area_ratio", "height_ratio", "routing_ratio"):
                assert m[k] <= 1.0, (tag, k, m[k])

    def test_the_frozen_pair_passes_every_clearance_corner(self):
        for tag in ("Z1", "Z2"):
            c = yaml.safe_load(
                (R / f"configs/phase0mr3/frozen_realizable_{tag}.yaml").read_text())
            n, d = c["corners_passing"].split("/")
            assert n == d and int(d) == 27, c["corners_passing"]

    def test_tsv_aspect_ratio_passes_the_hard_rule(self):
        for tag in ("Z1", "Z2"):
            c = yaml.safe_load(
                (R / f"configs/phase0mr3/frozen_realizable_{tag}.yaml").read_text())
            assert c["geometry"]["tsv_AR"] <= 10.0 + 1e-12

    def test_Z2_has_NO_tsv_process_margin_and_this_is_recorded(self):
        """NEGATIVE against over-claiming: AR = 10.000 passes the rule with M_AR = 1.000,
        and fails under a modest tolerance bound. That must not be reported as comfort."""
        rows = list(csv.DictReader((OUT / "tsv_margin_sweep.csv").open()))
        z2 = next(r for r in rows if r["arch"] == "ARCH_Z2_BACKSIDE"
                  and r["d_nominal_um"] == "30.0" and r["tolerance_case"] == "modest")
        assert z2["feasible_worst"] == "False"
        assert float(z2["M_AR_worst"]) < 1.0
        ok = next(r for r in rows if r["arch"] == "ARCH_Z2_BACKSIDE"
                  and r["d_nominal_um"] == "34.0" and r["tolerance_case"] == "modest")
        assert ok["feasible_worst"] == "True" and float(ok["M_AR_worst"]) > 1.0

    def test_enlarging_the_via_does_not_move_the_ETM_properties(self):
        """The Phase-0M allocation law: copper fraction is radius-independent."""
        rows = list(csv.DictReader((OUT / "tsv_margin_sweep.csv").open()))
        a = next(r for r in rows if r["arch"] == "ARCH_Z2_BACKSIDE"
                 and r["d_nominal_um"] == "30.0" and r["tolerance_case"] == "none")
        b = next(r for r in rows if r["arch"] == "ARCH_Z2_BACKSIDE"
                 and r["d_nominal_um"] == "34.0" and r["tolerance_case"] == "none")
        for k in ("phi_cu", "k_z", "E_xy_MPa", "CTE_eff"):
            assert abs(float(b[k]) - float(a[k])) / float(a[k]) < 1e-3, k
        assert float(b["n_required"]) < float(a["n_required"]) * 0.9


# ================================================= P/Q cooling
class TestCooling:
    def test_the_production_point_is_inside_the_validated_domain(self):
        import cooling_regime as CR
        r = CR.evaluate(27.0, strict=True)
        assert r["in_domain"] and r["Re"] < 2300.0

    def test_an_unsupported_Re_raises(self):
        import cooling_regime as CR
        with pytest.raises(CR.ModelDomainError):
            CR.evaluate(50.0, strict=True)

    def test_the_registry_has_no_correlation_for_the_gap(self):
        reg = yaml.safe_load(
            (R / "configs/phase0mr3/cooling_correlation_registry.yaml").read_text())
        t = next(c for c in reg["correlations"]
                 if c["id"] == "TRANSITIONAL_RECTANGULAR_MICROCHANNEL")
        assert t["provenance"] == "OPEN" and t["in_production"] is False
        assert t["source"] == "NONE FOUND"

    def test_the_production_design_space_is_capped_below_the_gap(self):
        reg = yaml.safe_load(
            (R / "configs/phase0mr3/cooling_correlation_registry.yaml").read_text())
        assert "2300" in reg["meta"]["production_design_space"]


# ================================================= R/T/U ledger and energy
class TestLedgerAndEnergy:
    def test_pumping_is_facility_scope_and_not_in_the_mesh(self):
        rows = list(csv.DictReader((OUT / "final_loss_ledger.csv").open()))
        pump = [r for r in rows if r["term"] == "P_pump_hydraulic"]
        assert pump
        for p in pump:
            assert p["scope"] == "FACILITY" and p["in_thermal_mesh"] == "False"

    def test_facility_total_is_electronics_plus_pumping(self):
        rows = list(csv.DictReader((OUT / "final_Z1_Z2_comparison.csv").open()))
        for r in rows:
            assert abs(float(r["P_total_facility_w"])
                       - float(r["P_total_electronics_w"])
                       - float(r["P_pump_hydraulic_w"])) < 1e-9

    def test_every_case_closed_its_thermal_energy_balance(self):
        rows = list(csv.DictReader((OUT / "final_Z1_Z2_comparison.csv").open()))
        assert len(rows) == 2
        for r in rows:
            assert abs(float(r["energy_residual_pct"])) < 1e-4


# ================================================= S frozen-config immutability
class TestFrozenConfigs:
    def test_both_frozen_configs_declare_themselves_frozen(self):
        for tag in ("Z1", "Z2"):
            c = yaml.safe_load(
                (R / f"configs/phase0mr3/frozen_realizable_{tag}.yaml").read_text())
            assert c["frozen"] is True
            assert "before any ETM result was seen" in c["frozen_by"]

    def test_the_two_configs_differ_ONLY_in_architecture_and_its_geometry(self):
        a = yaml.safe_load((R / "configs/phase0mr3/frozen_realizable_Z1.yaml").read_text())
        b = yaml.safe_load((R / "configs/phase0mr3/frozen_realizable_Z2.yaml").read_text())
        assert a["repair_applied"]["what"] == b["repair_applied"]["what"]
        assert a["converter"]["m_vr"] == b["converter"]["m_vr"]
        assert a["converter"]["inductor"] == b["converter"]["inductor"]
        assert a["load_w"] == b["load_w"] == 1000.0
        assert a["architecture"] != b["architecture"]

    def test_the_repair_is_inside_the_sourced_range(self):
        c = yaml.safe_load((R / "configs/phase0mr3/frozen_realizable_Z1.yaml").read_text())
        assert "inside the sourced range" in c["repair_applied"]["legality"]
        assert c["repair_applied"]["nothing_else_changed"] is True


# ================================================= the deciding result
class TestDecidingResult:
    def test_Z2_still_carries_less_response_than_Z1(self):
        rows = {r["case"]: r for r in csv.DictReader(
            (OUT / "final_Z1_Z2_comparison.csv").open())}
        z1 = float(rows["Z1"]["response_driver_um"])
        z2 = float(rows["Z2"]["response_driver_um"])
        assert z2 < z1, (z1, z2)

    def test_the_ratio_is_resolved_against_numerical_error(self):
        rows = {r["case"]: r for r in csv.DictReader(
            (OUT / "final_Z1_Z2_comparison.csv").open())}
        ratio = (float(rows["Z1"]["response_driver_um"])
                 / float(rows["Z2"]["response_driver_um"]))
        assert ratio - 1.0 > 0.005, "0.5 % is the converged mesh error; the gap must exceed it"

    def test_Z2_is_hotter_and_still_mechanically_preferable(self):
        rows = {r["case"]: r for r in csv.DictReader(
            (OUT / "final_Z1_Z2_comparison.csv").open())}
        assert float(rows["Z2"]["T_max_C"]) > float(rows["Z1"]["T_max_C"])
        assert float(rows["Z2"]["response_driver_um"]) < float(rows["Z1"]["response_driver_um"])

    def test_the_realizability_repair_barely_moved_the_ratio(self):
        rows = list(csv.DictReader((OUT / "phase0mr2_vs_phase0mr3.csv").open()))
        r = next(x for x in rows if x["metric"] == "D_driver (Z1/Z2)")
        assert abs(float(r["pct"])) < 1.0, r["pct"]
