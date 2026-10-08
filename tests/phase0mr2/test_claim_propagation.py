"""Phase 0M-R2 Section 1 --- the section-scoped propagation guard, negative-tested.

DEFECT #54. Every `stale_wording` entry in the contract is a VERBATIM sentence recovered
from the delivered Phase-0M-R report. Each test below injects the real sentence into a
synthetic report and asserts the guard fires. A paraphrase would prove nothing: the
Phase-0M-R checker's forbidden patterns WERE paraphrases, which is one of the three
reasons it passed a report containing seventeen stale findings.
"""
from __future__ import annotations

import importlib.util as _ilu                                                 # noqa: E402
_sp = _ilu.spec_from_file_location(
    "_sa", __import__("pathlib").Path(__file__).resolve().parents[2]
    / "scripts/phase0mr3/semantic_audit.py")
SA = _ilu.module_from_spec(_sp); _sp.loader.exec_module(SA)

import csv
import re
import sys
from pathlib import Path

import pytest
import yaml

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0mr2"))

from claim_propagation import (audit, current_present, expected_gate_sentence,   # noqa: E402
                               is_historical, load_contract, split_sections)

CONTRACT = load_contract()
OUT = R / "results" / "phase0mr2"


def clean_report() -> str:
    """A minimal report that satisfies every claim, used as the PASS baseline."""
    word, lst = expected_gate_sentence(CONTRACT["meta"])
    return f"""---
title: "t"
date: "2026-09-17"
---

# Provenance and tool versions

CalculiX 2.23, MOOSE 09515f92aa.

# Executive Summary

**Method.** {word} sequential falsification gates ({lst}), each designed so that a
negative result would stop the project.

**Current authority.** Phase {CONTRACT['meta']['current_authoritative_phase']} is the current authoritative phase.

Under the physical cooler the architectures DO separate in temperature, and Z2 is the
hottest of the principal candidates.

**Exact next work.** The Phase {CONTRACT['meta']['current_authoritative_phase']} ranked follow-up.

# Electrical Model Validation

A per-class transition resistance Delta_R = R_3D - R_1D is in production.

# Thermal Model Validation

The production loop uses a physical microchannel cooler with a streamwise coolant rise.

# Mechanical Model Validation

x

# Coupled ETM Physics --- mechanisms, not just numbers

x

# Architecture Comparison

The architectures do separate in temperature; Z2 is hottest yet mechanically preferred.

# Model Defects Discovered and Fixed

intra-VR routing: CLOSED IN PHASE 0M-R. cooling: CLOSED IN PHASE 0M-R.

# Uncertainty and Fidelity Ladder

x

# Next Steps --- prioritised roadmap

x
"""


class TestBaselinePasses:
    def test_a_correct_report_produces_no_findings(self):
        cov, stale = audit(clean_report(), CONTRACT)
        assert stale == [], stale
        assert all(c["present"] for c in cov), [c for c in cov if not c["present"]]


def _stale_cases():
    for c in CONTRACT["claims"]:
        for k, sw in enumerate(c.get("stale_wording", [])):
            yield pytest.param(c["claim_id"], sw, id=f"{c['claim_id']}[{k}]")


class TestRealStaleSentencesAreCaught:
    @pytest.mark.parametrize("claim_id,sentence", list(_stale_cases()))
    def test_injecting_the_REAL_sentence_makes_the_guard_fire(self, claim_id, sentence):
        """Inject the verbatim recovered sentence into the section it really occupied."""
        body = clean_report()
        claim = next(c for c in CONTRACT["claims"] if c["claim_id"] == claim_id)
        target = claim["required_in"][0]
        if target == "__frontmatter__":
            body = body.replace('date: "2026-09-17"', sentence)
        else:
            body = body.replace(f"# {target}\n", f"# {target}\n\n{sentence}\n")
        cov, stale = audit(body, CONTRACT)
        assert any(s["claim_id"] == claim_id for s in stale), \
            f"{claim_id}: the real stale sentence did not trip its guard"

    def test_the_flat_matcher_that_MISSED_these_is_shown_to_miss_them(self):
        """The Phase-0M-R failure mode, reproduced: a phrase present anywhere passes.

        This is the whole defect. `microchannel` in one chapter satisfied a flat
        document-wide check while the Thermal Model Validation section was stale.
        """
        body = clean_report().replace(
            "The production loop uses a physical microchannel cooler with a streamwise "
            "coolant rise.",
            "The Robin coefficient h_top = 166 000 W/m2K is inverse-calibrated.")
        # a flat, document-wide search still finds 'microchannel' elsewhere...
        assert "microchannel" not in body.split("# Thermal Model Validation")[1].split("#")[0]
        body_with_elsewhere = body.replace(
            "# Architecture Comparison\n",
            "# Architecture Comparison\n\nThe production microchannel cooler is used.\n")
        assert re.search(r"microchannel", body_with_elsewhere) is not None, \
            "flat search finds it -> the old checker passed"
        # ...but the section-scoped checker still fails, which is the fix
        cov, stale = audit(body_with_elsewhere, CONTRACT)
        assert any(s["claim_id"] == "cooling_production_boundary" for s in stale)


class TestGateCount:
    def test_the_count_is_DERIVED_not_typed(self):
        word, lst = expected_gate_sentence(CONTRACT["meta"])
        # derived from the contract, never typed: the count and the last gate move
        # together as phases are added
        assert len(CONTRACT["meta"]["gates"]) == len(lst.split(","))
        assert lst.split(",")[-1].strip() == CONTRACT["meta"]["gates"][-1]
        assert word == SA.NUMWORD[len(CONTRACT["meta"]["gates"])]

    def test_omitting_a_later_phase_from_the_list_fails(self):
        """The real failure: the word was right for 17 gates, and two gates were missing."""
        last = CONTRACT["meta"]["gates"][-1]
        body = clean_report().replace(f", {last})", ")")
        cov, stale = audit(body, CONTRACT)
        assert any(s["claim_id"] == "gate_count" for s in stale)

    def test_right_list_but_wrong_word_fails(self):
        word, _ = expected_gate_sentence(CONTRACT["meta"])
        body = clean_report().replace(f"{word} sequential", "Seventeen sequential")
        cov, stale = audit(body, CONTRACT)
        assert any(s["claim_id"] == "gate_count" for s in stale)


class TestPhaseAuthority:
    def test_the_real_phase0M_heading_is_rejected_outside_a_historical_chapter(self):
        real = ("# Phase 0M --- Geometry-Resolved Power Delivery, Component-Level "
                "Architecture, Cooling and ETM-Coupling Audit (current authoritative)")
        body = clean_report().replace("# Executive Summary\n",
                                      f"# Executive Summary\n\n{real}\n")
        cov, stale = audit(body, CONTRACT)
        assert any(s["claim_id"] == "phase_authority" for s in stale)

    def test_a_superseded_phase_may_not_claim_authority(self):
        body = clean_report().replace(
            f"Phase {CONTRACT['meta']['current_authoritative_phase']} is the current "
            "authoritative phase.", "Phase 0M is the current authoritative phase.")
        cov, stale = audit(body, CONTRACT)
        assert any(s["claim_id"] == "phase_authority" for s in stale)


class TestDefectSupersessionQualifier:
    def test_a_defect_row_reading_as_live_is_caught(self):
        """The real Phase-0M-R rows, verbatim, with no 'superseded by' qualifier."""
        real = ("- *Status:* **CONFIRMED, MODEL BUILT, NOT YET WIRED INTO THE "
                "PRODUCTION LOSS TOTAL**")
        body = clean_report().replace(
            "intra-VR routing: CLOSED IN PHASE 0M-R. cooling: CLOSED IN PHASE 0M-R.", real)
        cov, stale = audit(body, CONTRACT)
        assert any(s["claim_id"] == "intravr_routing_production" for s in stale)

    def test_the_same_row_WITH_a_qualifier_is_accepted(self):
        """A historical status is fine when the row says which phase closed it."""
        ok = ("- *Status:* CLOSED IN PHASE 0M-R. Status at discovery (Phase 0M): CONFIRMED, "
              "MODEL BUILT, NOT YET WIRED INTO THE PRODUCTION LOSS TOTAL. intra-VR routing "
              "is now in the production ledger. cooling is in the loop.")
        body = clean_report().replace(
            "intra-VR routing: CLOSED IN PHASE 0M-R. cooling: CLOSED IN PHASE 0M-R.", ok)
        cov, stale = audit(body, CONTRACT)
        assert not any(s["claim_id"] == "intravr_routing_production" for s in stale), stale


class TestForbiddenPhrasing:
    def test_the_licensed_phrasing_rule_is_enforced(self):
        """The brief forbids 'temperature does not matter for fatigue'. It is false."""
        body = clean_report().replace(
            "Under the physical cooler the architectures DO separate in temperature, and Z2 "
            "is the\nhottest of the principal candidates.",
            "temperature does not matter for fatigue")
        cov, stale = audit(body, CONTRACT)
        assert any(s["claim_id"] == "thermal_separation" for s in stale)


class TestChapterSupersessionVocabulary:
    def test_rescoped_by_is_recognised_as_historical(self):
        """Phase-0M-R knew 'superseded by' and 'extended by' but not 'rescoped by',
        so the Phase 0I chapter was read as a current-facing section."""
        mk = CONTRACT["historical_chapter_markers"]
        title = ("Phase 0I --- Vertical Integration and Local Reliability Physics "
                 "(rescoped by Phase 0I-R)")
        assert is_historical(title, mk) is True

    def test_a_chapter_with_no_marker_is_NOT_historical(self):
        assert is_historical("Phase 0M-R --- production-coupling closure",
                             CONTRACT["historical_chapter_markers"]) is False


class TestSectionSplitter:
    def test_frontmatter_is_addressable(self):
        s = split_sections(clean_report())
        assert "__frontmatter__" in s and "Executive Summary" in s

    def test_sections_do_not_overlap_and_cover_the_body(self):
        body = clean_report()
        s = split_sections(body)
        spans = sorted(v for k, v in s.items())
        for (a1, b1), (a2, b2) in zip(spans, spans[1:]):
            assert b1 == a2, "section spans must tile the document"
        assert spans[-1][1] == len(body)


def test_emit_negative_guard_evidence():
    """Write the machine-readable record that every guard was negative-tested."""
    rows = []
    base = clean_report()
    for c in CONTRACT["claims"]:
        for sw in c.get("stale_wording", []):
            target = c["required_in"][0]
            if target == "__frontmatter__":
                b = base.replace('date: "2026-09-17"', sw)
            else:
                b = base.replace(f"# {target}\n", f"# {target}\n\n{sw}\n")
            _, stale = audit(b, CONTRACT)
            fired = any(s["claim_id"] == c["claim_id"] for s in stale)
            _, clean_stale = audit(base, CONTRACT)
            rows.append({
                "claim_id": c["claim_id"],
                "guard": "section-scoped current/historical wording",
                "real_sentence_injected": " ".join(sw.split())[:150],
                "recovered_from": "results/ETM_DVPD_FULL_TECHNICAL_REPORT.md (as delivered)",
                "passes_clean_report": not any(
                    s["claim_id"] == c["claim_id"] for s in clean_stale),
                "fails_on_injection": fired})
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "negative_guard_tests.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    assert all(r["fails_on_injection"] and r["passes_clean_report"] for r in rows), \
        [r for r in rows if not (r["fails_on_injection"] and r["passes_clean_report"])]
