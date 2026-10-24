"""PHASE 0N-Y --- one owner per conductor, and correct rail assignment (brief E, M, V, W)."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0nw", "scripts/phase0mr", "scripts/phase0i", "scripts/phase0g",
          "scripts/phase0b", "scripts"):
    sys.path.insert(0, str(R / p))

import power_path as PP  # noqa: E402


@pytest.fixture(scope="module")
def rails():
    return PP.rail_currents()


@pytest.mark.parametrize("arch", ["Z1", "Z2"])
def test_graph_has_no_ownership_or_chain_problems(arch):
    r = PP.check(arch)
    assert r["ok"], f"{arch}: {r['problems']}"


@pytest.mark.parametrize("arch", ["Z1", "Z2"])
def test_every_interconnect_owner_has_at_least_one_segment(arch):
    """An owner with no segment means a real conductor whose loss is silently zero."""
    used = {s.owner for s in PP.graph(arch)}
    missing = [o for o in PP.INTERCONNECT_OWNERS if o not in used]
    assert not missing, f"{arch}: unowned conductors for {missing}"


@pytest.mark.parametrize("arch", ["Z1", "Z2"])
def test_no_segment_is_owned_twice(arch):
    ids = [s.seg_id for s in PP.graph(arch)]
    assert len(ids) == len(set(ids))
    # a segment carries exactly one owner by construction; assert the dataclass enforces it
    for s in PP.graph(arch):
        assert s.owner in PP.LEDGER_OWNERS


@pytest.mark.parametrize("arch", ["Z1", "Z2"])
def test_converter_intrinsic_terms_never_own_a_conductor(arch):
    """Device and passive losses must not absorb interconnect, or it is counted twice."""
    bad = [s.seg_id for s in PP.graph(arch) if s.owner in PP.CONVERTER_INTRINSIC]
    assert not bad, f"{arch}: {bad} assign a conductor to a converter-intrinsic term"


def test_an_unknown_owner_is_rejected():
    """NEGATIVE: a new ledger term cannot appear beside an old one unnoticed."""
    with pytest.raises(ValueError, match="not a ledger owner"):
        PP.Segment("X", "a", "b", "Z1", "bga", "vertical", 48.0, 1.0,
                   "P_made_up_term", "OPEN")


def test_a_bad_loss_status_is_rejected():
    with pytest.raises(ValueError, match="bad loss_status"):
        PP.Segment("X", "a", "b", "Z1", "bga", "vertical", 48.0, 1.0,
                   "P_BGA_supply", "DONE")


# ------------------------------------------------------- rail assignment (brief W)
def test_bga_carries_the_48v_rail_in_both_architectures(rails):
    """1000 A must never appear on a BGA or 48 V HVR input segment."""
    for arch in ("Z1", "Z2"):
        for s in PP.graph(arch):
            if s.owner.startswith("P_BGA"):
                assert s.rail_v == 48.0
                assert s.i_dc_a == pytest.approx(rails["hv_total_a"], rel=1e-9), (
                    f"{s.seg_id} puts {s.i_dc_a} A on the BGA")


def test_the_substrate_tsv_rail_differs_between_architectures(rails):
    """THE architectural distinction: Z1's TSVs carry 48 V, Z2's carry 1 V at ~1 kA."""
    z1 = [s for s in PP.graph("Z1") if s.owner in ("P_TSV_VDD", "P_TSV_GND")]
    z2 = [s for s in PP.graph("Z2") if s.owner in ("P_TSV_VDD", "P_TSV_GND")]
    assert z1 and z2
    assert all(s.rail_v == 48.0 for s in z1)
    assert all(s.rail_v == 1.0 for s in z2)
    assert all(s.i_dc_a == pytest.approx(rails["hv_total_a"], rel=1e-9) for s in z1)
    assert all(s.i_dc_a == pytest.approx(rails["lv_total_a"], rel=1e-9) for s in z2)


def test_no_segment_mixes_a_rail_with_the_wrong_current(rails):
    for arch in ("Z1", "Z2"):
        for s in PP.graph(arch):
            if s.rail_v == 48.0:
                assert s.i_dc_a <= rails["hv_total_a"] * 1.01, (
                    f"{s.seg_id}: {s.i_dc_a} A on a 48 V segment")
            if s.rail_v == 1.0:
                assert s.i_dc_a <= rails["lv_total_a"] * 1.01


def test_per_cell_currents_are_used_inside_the_cell(rails):
    """A cell carries I/49, not the system current."""
    for arch in ("Z1", "Z2"):
        for s in PP.graph(arch):
            if s.owner.startswith("P_intraVR") and s.count == rails["cells"]:
                assert s.i_dc_a < rails["lv_total_a"] / 10


def test_intravr_vertical_is_not_merged_with_the_substrate_tsv():
    """Different physical structures: inter-tier vias vs the package through-substrate."""
    for arch in ("Z1", "Z2"):
        segs = PP.graph(arch)
        v = [s for s in segs if s.owner == "P_intraVR_vertical"]
        t = [s for s in segs if s.owner in ("P_TSV_VDD", "P_TSV_GND")]
        assert v and t
        assert not ({s.location for s in v} & {s.location for s in t})


# ------------------------------------------------------------------ provenance
@pytest.mark.parametrize("arch", ["Z1", "Z2"])
def test_no_segment_claims_a_recomputed_physical_loss_yet(arch):
    """Phase-0M-R3C values are references, never physical results."""
    r = PP.check(arch)
    assert r["n_recomputed"] == 0, (
        "a segment claims RECOMPUTED, but no physical loss recomputation has been run")
    assert r["n_historical"] > 0 and r["n_open"] > 0


@pytest.mark.parametrize("arch", ["Z1", "Z2"])
def test_segment_csv_round_trips(arch, tmp_path):
    PP.write_csv(tmp_path)
    rows = list(csv.DictReader((tmp_path / f"power_path_{arch}.csv").open()))
    assert len(rows) == len(PP.graph(arch))
    for row in rows:
        assert row["owner"] in PP.LEDGER_OWNERS
        assert row["loss_status"] in PP.LOSS_STATUS
        assert row["orientation"] in ("vertical", "horizontal")


def test_both_horizontal_and_vertical_intra_cell_loss_are_present():
    """The brief's central requirement: BOTH directions inside each HVR cell."""
    for arch in ("Z1", "Z2"):
        segs = PP.graph(arch)
        h = [s for s in segs if s.owner == "P_intraVR_metal"]
        v = [s for s in segs if s.owner == "P_intraVR_vertical"]
        assert h and v, f"{arch} is missing intra-cell {'horizontal' if not h else 'vertical'}"
        assert all(s.orientation == "horizontal" for s in h)
        assert all(s.orientation == "vertical" for s in v)
