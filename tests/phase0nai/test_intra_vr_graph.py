"""PHASE 0N-AI --- the intra-VR resistance graph exists; its defects are named."""
from __future__ import annotations

import collections
import csv
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


def test_R1_is_still_numerically_identical_to_R0(rows):
    """A declared fidelity level that duplicates its baseline is not a level.

    If this test starts FAILING, obstacle routing has begun to do something and
    INTRA_VR_RESISTANCE_GRAPH.md must be updated -- the failure is the signal,
    not a regression.
    """
    key = lambda r: (r["n_layers"], r["t_cu_um"], r["via_policy"], r["j_max"])
    g = collections.defaultdict(lambda: collections.defaultdict(dict))
    for r in rows:
        g[key(r)][r["level"]][r["net"]] = float(r["length_mm"])
    assert len(g) >= 20
    for k, byl in g.items():
        if "R0" in byl and "R1" in byl:
            assert byl["R0"] == byl["R1"], (
                "R1 now differs from R0 at %s -- update the phase document" % (k,))


def test_the_obstacle_detour_can_detect_a_block_and_charge_nothing():
    """Blockage uses component EXTENT; the detour size uses component CENTRE."""
    import routing as RT
    comps = RT.tile_layout(RT.DESIGN["tile_side_mm"])
    by = {c.name: c for c in comps}
    blocked_but_free = 0
    for nt in RT.nets():
        a, b = by.get(nt.src), by.get(nt.dst)
        if a is None or b is None:
            continue
        blks = [c for c in comps if c.blocks(nt.layer)
                and c.name not in (a.name, b.name)]
        p, q = (a.x_mm, a.y_mm), (b.x_mm, b.y_mm)

        def clear(p0, p1, m=0.02):
            for c in blks:
                x0, x1 = sorted((p0[0], p1[0]))
                y0, y1 = sorted((p0[1], p1[1]))
                if (x0 - m <= c.x_mm + c.w_mm / 2 and x1 + m >= c.x_mm - c.w_mm / 2
                        and y0 - m <= c.y_mm + c.h_mm / 2
                        and y1 + m >= c.y_mm - c.h_mm / 2):
                    return False
            return True

        corners_blocked = not any(clear(p, c) and clear(c, q)
                                  for c in ((q[0], p[1]), (p[0], q[1])))
        if corners_blocked and RT.obstacle_manhattan(
                a, b, comps, nt.layer) == pytest.approx(RT.manhattan(a, b)):
            blocked_but_free += 1
    assert blocked_but_free > 0, (
        "the centre/extent inconsistency appears fixed -- update the document")


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
