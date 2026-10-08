"""Phase-0M-R Section 2/25-I -- the current-state contract and DEFECT #53 guard.

Both directions are tested:
  MUTATION  change one contract field -> both reports must fail until regenerated
  INJECTION insert a REAL stale sentence from a prior artifact -> the build must fail
"""
from __future__ import annotations
import re, shutil, subprocess, sys
from pathlib import Path

import pytest
import yaml

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0mr"))
import state_contract as SC                                                # noqa: E402
import defect53_audit as D53                                              # noqa: E402

Y = R / "results" / "CURRENT_SCIENTIFIC_STATUS.yaml"
HIST = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
GEN = R / "results" / "phase0g" / "generated_status_sections.md"


def test_contract_exists_and_every_field_is_populated():
    c = SC.load()
    for f in SC.FIELDS:
        assert c[f]["state"].strip(), f
        assert c[f]["evidence"].strip(), f


def test_every_contract_evidence_path_exists():
    """The validator that caught the first draft's wrong path."""
    c = SC.load()
    for f in SC.FIELDS:
        p = R / c[f]["evidence"].split("::")[0].split(",")[0].strip()
        assert p.exists(), f"{f}: {p}"


def test_contract_rejects_a_missing_field(tmp_path, monkeypatch):
    """NEGATIVE: deleting a required field must raise, not default."""
    d = yaml.safe_load(Y.read_text())
    del d["current_state_contract"]["current_cooling_status"]
    p = tmp_path / "y.yaml"
    p.write_text(yaml.safe_dump(d))
    monkeypatch.setattr(SC, "Y", p)
    with pytest.raises(KeyError, match="missing required fields"):
        SC.load()


def test_contract_rejects_a_nonexistent_evidence_path(tmp_path, monkeypatch):
    """NEGATIVE: an evidence path that does not exist must raise."""
    d = yaml.safe_load(Y.read_text())
    d["current_state_contract"]["current_cooling_status"]["evidence"] = \
        "results/phase0mr/THIS_FILE_DOES_NOT_EXIST.md"
    p = tmp_path / "y.yaml"
    p.write_text(yaml.safe_dump(d))
    monkeypatch.setattr(SC, "Y", p)
    with pytest.raises(FileNotFoundError):
        SC.load()


def test_mutating_a_contract_field_makes_the_report_stale(tmp_path, monkeypatch):
    """MUTATION TEST. Change one contract field; the rendered table must change, so a
    report carrying the old table is detectably out of date."""
    before = SC.as_markdown()
    d = yaml.safe_load(Y.read_text())
    d["current_state_contract"]["current_cooling_status"]["state"] = \
        "MUTATED FOR TEST -- cooling is fully production-coupled"
    p = tmp_path / "y.yaml"
    p.write_text(yaml.safe_dump(d))
    monkeypatch.setattr(SC, "Y", p)
    after = SC.as_markdown()
    assert before != after
    assert "MUTATED FOR TEST" in after
    # the report on disk carries `before`; against the mutated contract it is stale
    assert before in HIST.read_text(), "the report must carry the contract table verbatim"
    assert after not in HIST.read_text()


def test_report_carries_the_contract_table_verbatim():
    assert SC.as_markdown() in HIST.read_text(), \
        "the historical report does not carry the current contract table -- regenerate"


def test_no_stale_current_facing_claim_anywhere():
    r = subprocess.run([sys.executable, str(R / "scripts" / "phase0mr" / "defect53_audit.py")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.parametrize("sid,frag,field,sup,src", D53.STALE)
def test_injection_of_each_real_stale_sentence_is_caught(tmp_path, sid, frag, field, sup, src):
    """INJECTION TEST, one per stale claim. The fragment is VERBATIM from the artifact named
    in `src` -- never a paraphrase -- and is injected into a real current-facing block."""
    md = GEN.read_text()
    m = re.search(r"## Current scientific status \(Phase [^)]+\)", md)
    assert m, "current-status heading not found"
    poisoned = md[:m.end()] + f"\n\nThe framework currently reports that {frag}.\n" + md[m.end():]
    p = tmp_path / "generated_status_sections.md"
    p.write_text(poisoned)
    hits = D53.scan(p, "TEST")
    assert any(h["id"] == sid for h in hits), \
        f"{sid} injected verbatim into a current-facing block and NOT caught"


@pytest.mark.parametrize("fid,pat,field", D53.FORBIDDEN_CURRENT)
def test_each_forbidden_current_claim_is_caught(tmp_path, fid, pat, field):
    """NEGATIVE: each Section-24 forbidden claim must be caught when stated unqualified."""
    sample = {
        "F1": "only one mechanical mechanism computable",
        "F2": "no SAC305 life law exists",
        "F3": "intra-VR routing is already included",
        "F4": "physical cooling is already active",
        "F5": "2.5D as a class is eliminated",
        "F6": "TSV radius is universally irrelevant",
        "F7": "the framework is fully bidirectionally ETM coupled",
        "F8": "CROWDING_DEFAULT = 1.326 is current",
    }[fid]
    md = GEN.read_text()
    m = re.search(r"## Current scientific status \(Phase [^)]+\)", md)
    poisoned = md[:m.end()] + f"\n\nIn the present framework {sample}.\n" + md[m.end():]
    p = tmp_path / "generated_status_sections.md"
    p.write_text(poisoned)
    hits = D53.scan(p, "TEST")
    assert any(h["id"] == fid for h in hits), f"{fid} not caught: {sample!r}"


def test_a_historical_marker_exonerates_a_quoted_defect(tmp_path):
    """The guard must let a defect report quote the defect it fixed, or it becomes
    unusable and someone will disable it."""
    md = GEN.read_text()
    m = re.search(r"## Current scientific status \(Phase [^)]+\)", md)
    frag = D53.STALE[0][1]
    ok = md[:m.end()] + (f"\n\nThe superseded Phase-0H text said {frag}, which Phase 0I "
                         f"falsified.\n") + md[m.end():]
    p = tmp_path / "generated_status_sections.md"
    p.write_text(ok)
    assert not D53.scan(p, "TEST")


def test_basis_is_phase_scoped():
    """DEFECT #53's mechanism: an unscoped `basis` printed Phase-0H bullets forever."""
    d = yaml.safe_load(Y.read_text())
    ph = d["meta"]["current_phase"]
    key = "basis_phase" + ph.lower().replace("-", "")
    # 0M-R inherits Phase 0M's basis until its own verdict is recorded
    assert "basis_phase0m" in d["verdict"], "the phase-scoped basis is missing"
    assert len(d["verdict"]["basis_phase0m"]) >= 5
    assert "ONE is computable" not in " ".join(d["verdict"]["basis_phase0m"])
