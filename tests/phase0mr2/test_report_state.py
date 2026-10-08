"""Phase 0M-R2 Section 15, categories R, S and T --- report regeneration, guard
self-test coverage, and PDF resource verification."""
from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0mr2"))

from claim_propagation import (audit, load_contract, split_sections)   # noqa: E402

import importlib.util as _ilu                                                 # noqa: E402
_spec = _ilu.spec_from_file_location(
    "_sa", Path(__file__).resolve().parents[2] / "scripts/phase0mr3/semantic_audit.py")
SA = _ilu.module_from_spec(_spec); _spec.loader.exec_module(SA)

OUT = R / "results" / "phase0mr2"
HIST = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
PDF = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.pdf"
CONTRACT = load_contract()


# ===================================================== R. report regeneration
class TestReportIsCurrent:
    def test_the_delivered_report_has_no_stale_current_facing_claims(self):
        _, stale = audit(HIST.read_text(), CONTRACT)
        assert stale == [], stale

    def test_every_required_placement_is_present(self):
        cov, _ = audit(HIST.read_text(), CONTRACT)
        missing = [c for c in cov if not c["present"]]
        assert missing == [], missing

    def test_exactly_one_chapter_claims_current_authority(self):
        heads = re.findall(r"(?m)^# (.+)$", HIST.read_text())
        auth = [h for h in heads if "(current authoritative)" in h]
        assert len(auth) == 1, auth
        assert auth[0].startswith("Phase 0M-R3"), auth[0]

    def test_the_gate_list_is_complete_and_in_order(self):
        body = re.sub(r"\s+", " ", HIST.read_text())
        # \w does not match the hyphen in "Twenty-one", so the original pattern
        # captured "one" and the guard fired on a correct report.
        m = re.search(r"([\w-]+) sequential falsification gates\s*\(([^)]*)\)", body)
        assert m, "no gate sentence"
        got = [x.strip() for x in m.group(2).split(",") if x.strip()]
        gates = CONTRACT["meta"]["gates"]
        assert got == gates, got
        # derived, not pinned: this test is the reason the count went stale twice
        assert m.group(1) == SA.NUMWORD[len(gates)]

    def test_the_report_date_is_not_older_than_its_newest_phase(self):
        m = re.search(r'(?m)^date: "(\d{4}-\d{2}-\d{2})"', HIST.read_text())
        assert m and m.group(1) >= "2026-09-17", m.group(1) if m else "no date"

    def test_the_builder_is_IDEMPOTENT(self):
        """A second run must not duplicate or corrupt anything. The Phase-0M-R2 builder
        failed this on its first attempt and the failure is pinned here."""
        # The unit of rebuild is the CHAIN, not any one builder. Each phase's builder
        # hard-codes its own "(current authoritative)" heading inside its sentinel block
        # and a later phase demotes it from outside, so running an older builder alone
        # restores a superseded chapter to current. Running one here also polluted the
        # other tests in this file, which is how that was found.
        before = HIST.read_text()
        r = subprocess.run([sys.executable,
                            str(R / "scripts/phase0mr3b/rebuild_reports.py")],
                           capture_output=True, text=True, cwd=str(R))
        assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-1500:]
        after = HIST.read_text()
        assert after == before, "rebuilding changed the report; the builder is not idempotent"

    def test_defect_rows_51_and_52_carry_a_supersession_qualifier(self):
        d = yaml.safe_load((R / "results/CURRENT_SCIENTIFIC_STATUS.yaml").read_text())
        rows = {x["id"]: x for x in d["phase0g_defects"]}
        for i in (51, 52):
            st = rows[i]["status"]
            assert "CLOSED IN PHASE" in st and "Status at discovery" in st, (i, st)

    def test_defect_53_was_registered_retroactively_and_54_55_exist(self):
        d = yaml.safe_load((R / "results/CURRENT_SCIENTIFIC_STATUS.yaml").read_text())
        ids = {x["id"] for x in d["phase0g_defects"]}
        assert {53, 54, 55, 56} <= ids, sorted(ids)


# ===================================================== S. guard self-test coverage
class TestGuardCoverage:
    def test_every_contract_claim_with_a_stale_sentence_is_negative_tested(self):
        rows = list(csv.DictReader((OUT / "negative_guard_tests.csv").open()))
        tested = {r["claim_id"] for r in rows}
        need = {c["claim_id"] for c in CONTRACT["claims"] if c.get("stale_wording")}
        assert need <= tested, need - tested

    def test_every_negative_test_actually_fired(self):
        rows = list(csv.DictReader((OUT / "negative_guard_tests.csv").open()))
        assert rows
        bad = [r for r in rows if r["fails_on_injection"] != "True"
               or r["passes_clean_report"] != "True"]
        assert bad == [], bad

    def test_every_claim_names_at_least_one_required_section(self):
        for c in CONTRACT["claims"]:
            assert c.get("required_in"), c["claim_id"]

    def test_every_required_section_exists_in_the_report(self):
        secs = split_sections(HIST.read_text())
        for c in CONTRACT["claims"]:
            for key in c["required_in"]:
                hit = key in secs or any(t.startswith(key + " ") for t in secs)
                assert hit, (c["claim_id"], key)

    def test_the_stale_before_and_after_records_both_exist(self):
        before = list(csv.DictReader((OUT / "stale_claims_before.csv").open()))
        after = list(csv.DictReader((OUT / "stale_claims_after.csv").open()))
        assert len(before) == 17, len(before)
        assert len(after) == 0, after


# ===================================================== T. PDF resources
class TestPDFResources:
    @pytest.mark.skipif(not PDF.is_file(), reason="PDF not built")
    def test_every_figure_the_report_references_exists_on_disk(self):
        missing = [p for p in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", HIST.read_text())
                   if not Path(p).is_file()]
        assert missing == [], missing

    @pytest.mark.skipif(not PDF.is_file(), reason="PDF not built")
    def test_the_pdf_records_the_phase_0mr2_verdict_as_history(self):
        """Phase 0M-R3A removed the stale current-state table that had been asserting the
        Phase-0M-R2 verdict as the PRESENT one (DEFECT #57). That verdict is still part of
        the record, so it must survive -- in the verdict ledger, marked as the finding of
        the gate that issued it, and not as the current verdict."""
        t = subprocess.run(["pdftotext", "-layout", str(PDF), "-"],
                           capture_output=True, text=True).stdout
        t1 = re.sub(r"\s+", " ", t)
        assert "PRODUCTION MODEL STILL NOT PHYSICALLY CLOSED" in t1
        assert "Phase 0M-R2" in t1
        assert "Verdict history" in t1
        # and it must not be the one presented as current
        i = t1.index("PRODUCTION MODEL STILL NOT PHYSICALLY CLOSED")
        assert "Phase 0M-R2" in t1[max(0, i - 120):i], \
            "the 0M-R2 verdict is not attributed to Phase 0M-R2"
        cur = re.search(r"current verdict[^.]{0,400}", t1, re.I)
        if cur:
            assert "PRODUCTION MODEL STILL NOT PHYSICALLY CLOSED" not in cur.group(0)

    @pytest.mark.skipif(not PDF.is_file(), reason="PDF not built")
    def test_the_pdf_does_not_carry_the_withdrawn_50_g_s_numbers_unqualified(self):
        """The 166 000 / 1.46 MPa / 74 W point is withdrawn; any mention must be
        retracted in the same sentence."""
        t = re.sub(r"\s+", " ", subprocess.run(
            ["pdftotext", "-layout", str(PDF), "-"],
            capture_output=True, text=True).stdout)
        RETRACT = re.compile(r"withdraw|retired|OUT_OF_MODEL_DOMAIN|not reachable|"
                             r"historical|no validated correlation|calibrated", re.I)
        for m in re.finditer(r"1\.46 MPa", t):
            sent = t[max(0, m.start() - 400):m.end() + 400]
            assert RETRACT.search(sent), sent[:220]

    @pytest.mark.skipif(not PDF.is_file(), reason="PDF not built")
    def test_the_pdf_never_says_temperature_does_not_matter_for_fatigue(self):
        t = re.sub(r"\s+", " ", subprocess.run(
            ["pdftotext", "-layout", str(PDF), "-"],
            capture_output=True, text=True).stdout)
        assert "temperature does not matter for fatigue" not in t.lower()
