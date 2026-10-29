"""Tool provenance cannot contradict execution (final-closure Part 29), and the executed
Icepak benchmark is reproducible from the repository (Part 30). The guard also runs on
the REAL stale Icepak record that research/final_closure/tool_provenance.json carried at
commit abba03e."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
D = R / "research" / "final_closure"
sys.path.insert(0, str(R / "scripts"))
import final_closure_provenance as P                                # noqa: E402

#: the exact Icepak fields at abba03e: EXECUTED in a not-executed lane, "not run" version
STALE_ICEPAK = {"name": "Ansys Icepak", "status": "EXECUTED", "lane": "not_executed",
                "version_used": "installed and licensed with AEDT 2026 R1; not run for any "
                                "study result"}


def tools():
    return json.loads((D / "tool_provenance.json").read_text())["tools"]


def test_no_tool_is_executed_and_not_executed_at_once():
    assert P.lane_violations(tools()) == []


def test_lane_guard_catches_the_real_stale_icepak_record():
    bad = P.lane_violations([STALE_ICEPAK])
    assert any("lane 'not_executed'" in b for b in bad)
    assert any("not run" in b for b in bad)
    assert P.lane_violations([{"name": "Q3D", "status": "EXECUTED", "lane": "considered"}])


def test_icepak_record_names_its_result_and_project_artifacts():
    ic = next(t for t in tools() if t["name"] == "Ansys Icepak")
    assert ic["status"] == "EXECUTED" and ic["lane"] == "reference"
    assert "2026 R1" in ic["version_used"]
    for p in ic["evidence_paths"] + [ic["result_json"]]:
        assert (R / p).exists(), p
    ref = json.loads((R / ic["result_json"]).read_text())
    assert set(ic["mesh_levels"]) == set(ref["levels"])


def test_preserved_icepak_projects_match_their_manifest():
    man = json.loads((D / "reference_artifacts/icepak/MANIFEST.json").read_text())
    assert len(man["levels"]) == 4
    for lv, rec in man["levels"].items():
        f = R / rec["project"]["file"]
        assert hashlib.sha256(f.read_bytes()).hexdigest() == rec["project"]["sha256"], lv
        assert rec["cells"] and rec["solved"], lv
    for p in (D / "reference_artifacts/icepak").rglob("*"):
        if p.is_file():
            b = p.read_bytes()
            assert b"lmgrd" not in b and b"ansyslmd" not in b.lower(), p


def test_licence_unavailable_tools_stay_unexecuted():
    for t in tools():
        if "LICENSE UNAVAILABLE" in str(t.get("status")):
            assert t["lane"] == "not_executed", t["name"]


def test_tool_map_guards_catch_every_injected_violation():
    """The tool map reads its EXECUTED / NOT EXECUTED stamps from the provenance; each of
    its guards must still fail on a real offending input (incl. the unquoted font stack
    figstyle once carried), and the real table must pass."""
    import final_closure_tool_map as TM
    assert TM.selftest() == 0
