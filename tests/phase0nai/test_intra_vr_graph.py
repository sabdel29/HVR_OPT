"""PHASE 0N-AI --- the intra-VR resistance graph exists; its defects are named."""
from __future__ import annotations

import collections
import csv
import json
import re
import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
for _p in ("scripts/phase0m", "scripts/phase0e", "scripts/phase0dr", "scripts"):
    sys.path.insert(0, str(R / _p))

NETS = R / "results/phase0m/intra_vr_routing_nets.csv"
DOC = R / "research/phase0nai/INTRA_VR_RESISTANCE_GRAPH.md"


@pytest.fixture(scope="module")
def rows():
    return list(csv.DictReader(NETS.open()))


def test_the_graph_exists_and_spans_the_whole_converter(rows):
    """It was repeatedly reported as missing. It is not missing."""
    assert len(rows) > 500
    nets = {r["net"] for r in rows}
    assert len(nets) == 16
    assert {r["rail"] for r in rows} == {"HV", "SC", "MID", "SW", "LV"}
    assert {r["geom"] for r in rows} == {"lateral", "vertical"}
    # input pad -> high side -> flying cap -> mid -> low side -> inductor -> out
    for stage in ("vin_to_hs0", "hs0_to_cf", "hs0_to_ls0", "ls0_to_L0",
                  "L0_to_vout", "vout_plane"):
        assert stage in nets, stage


def test_every_segment_carries_R_I_and_P(rows):
    for r in rows:
        assert float(r["R_mohm"]) >= 0.0
        assert float(r["i_rms_a"]) >= 0.0
        assert float(r["P_w_per_vr"]) >= 0.0
        assert r["feasible"] in ("True", "False")


def test_R1_reproduces_R0_in_the_committed_artifact(rows):
    """R1 adds nothing for this layout -- now a RETIRED level, not a defect.

    When written, R1 == R0 was a symptom: the obstacle router detected a
    blockage via component EXTENT but sized the detour from component CENTRE,
    so it could never charge one. That is fixed (tests/phase0naj proves the
    router detours on a synthetic blocker). With it fixed, still no physical
    net is obstructed, so R1 legitimately equals R0 and is retired rather than
    given a manufactured difference.
    """
    key = lambda r: (r["n_layers"], r["t_cu_um"], r["via_policy"], r["j_max"])
    g = collections.defaultdict(lambda: collections.defaultdict(dict))
    for r in rows:
        g[key(r)][r["level"]][r["net"]] = float(r["length_mm"])
    assert len(g) >= 20
    for k, byl in g.items():
        if "R0" in byl and "R1" in byl:
            assert byl["R0"] == byl["R1"], k


def test_the_router_defect_is_fixed_not_merely_documented():
    src = (R / "scripts/phase0m/routing.py").read_text()
    assert "THE DEFECT THIS REPLACES" in src
    assert "ONE geometric test for both decisions" in src
    import routing as RT
    a = RT.Comp("A", -0.8, 0.0, 0.0, 0.05, 0.05, "HS_RDL", "t")
    b = RT.Comp("B", 0.8, 0.6, 0.0, 0.05, 0.05, "HS_RDL", "t")
    wall = RT.Comp("W", 0.0, 0.30, 0.0, 2.0, 0.20, "HS_RDL", "t")
    assert RT.obstacle_manhattan(a, b, [a, b, wall], "HS_RDL") > RT.manhattan(a, b)


def test_the_fidelity_ladder_answers_its_own_question():
    """R2 was computed and never compared with anything."""
    L = json.loads((R / "research/phase0naj/fidelity_ladder.json").read_text())
    assert L["meta"]["R1_status"] == "RETIRED"
    assert L["R1_identical_to_R0_everywhere"] is True
    assert not L["nets_detouring_after_router_fix"]
    assert L["rows"], "no R0-vs-R2 comparison emitted"
    for r in L["rows"]:
        assert r["R2_w_per_vr"] > 0 and r["R0_w_per_vr"] > 0
    assert L["meta"]["R0_vs_R2_max_abs_err_pct"] > 30.0
    assert "never validation" in L["meta"]["R2_reference_status"]


def test_the_output_plane_is_reported_infeasible_not_clipped(rows):
    vp = [r for r in rows if r["net"] == "vout_plane"
          and r["n_layers"] == "1" and r["t_cu_um"] == "10.0"]
    assert vp and all(r["feasible"] == "False" for r in vp)
    assert all(float(r["i_rms_a"]) > 20.0 for r in vp)


def test_the_ledger_and_the_manuscript_disagree_and_the_doc_says_so():
    """The ledger calls intra-VR OPEN; the manuscript prints 3.601 / 3.627 W."""
    led = (R / "scripts/phase0nw/interconnect_loss.py").read_text()
    assert re.search(r'"P_intraVR_metal":\s*\{"w":\s*None', led)
    tex = " ".join((R / "manuscript"
                    / "ETM_DVPD_JOURNAL_MANUSCRIPT.tex").read_text().split())
    assert "Intra-cell metal (W) & $3.601$ & $3.627$" in tex
    doc = DOC.read_text()
    assert "3.601" in doc and "3.627" in doc
    assert "OPEN, with the graph" in doc


def test_the_document_does_not_claim_the_graph_is_missing():
    doc = " ".join(DOC.read_text().split())
    assert "The graph exists." in doc
    for bad in ("no graph exists\"", "has not been built", "does not exist yet"):
        assert bad not in doc.replace("not \"no graph exists\"", "")
