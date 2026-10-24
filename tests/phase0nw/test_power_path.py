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
    """Per-architecture now: Z1 and Z2 do not share an HV current."""
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
                assert s.i_dc_a == pytest.approx(rails[arch]["hv_total_a"], rel=1e-9), (
                    f"{s.seg_id} puts {s.i_dc_a} A on the BGA")


def test_the_substrate_tsv_rail_differs_between_architectures(rails):
    """THE architectural distinction: Z1's TSVs carry 48 V, Z2's carry 1 V at ~1 kA."""
    z1 = [s for s in PP.graph("Z1") if s.owner in ("P_TSV_VDD", "P_TSV_GND")]
    z2 = [s for s in PP.graph("Z2") if s.owner in ("P_TSV_VDD", "P_TSV_GND")]
    assert z1 and z2
    assert all(s.rail_v == 48.0 for s in z1)
    assert all(s.rail_v == 1.0 for s in z2)
    assert all(s.i_dc_a == pytest.approx(rails["Z1"]["hv_total_a"], rel=1e-9) for s in z1)
    assert all(s.i_dc_a == pytest.approx(rails["Z2"]["lv_total_a"], rel=1e-9) for s in z2)


def test_no_segment_mixes_a_rail_with_the_wrong_current(rails):
    for arch in ("Z1", "Z2"):
        for s in PP.graph(arch):
            if s.rail_v == 48.0:
                assert s.i_dc_a <= rails[arch]["hv_total_a"] * 1.01, (
                    f"{s.seg_id}: {s.i_dc_a} A on a 48 V segment")
            if s.rail_v == 1.0:
                assert s.i_dc_a <= rails[arch]["lv_total_a"] * 1.01


def test_per_cell_currents_are_used_inside_the_cell(rails):
    """A cell carries I/49, not the system current."""
    for arch in ("Z1", "Z2"):
        for s in PP.graph(arch):
            if s.owner.startswith("P_intraVR") and s.count == rails[arch]["cells"]:
                assert s.i_dc_a < rails[arch]["lv_total_a"] / 10


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


# ============================ brief 6, 8, 9, 30: per-arch currents, material, continuity
def test_z1_and_z2_have_independent_hv_currents():
    """They do not have the same losses, so they cannot have the same input current."""
    rc = PP.rail_currents()
    assert rc["Z1"]["hv_total_a"] != rc["Z2"]["hv_total_a"]
    assert rc["Z1"]["hv_total_a"] == pytest.approx(23.6936, abs=1e-3)
    assert rc["Z2"]["hv_total_a"] == pytest.approx(23.7429, abs=1e-3)
    for a in ("Z1", "Z2"):
        assert rc[a]["p_input_w"] == pytest.approx(1000.0 + rc[a]["p_loss_w"], rel=1e-12)
        assert rc[a]["placeholder"] is True


def test_each_graph_uses_its_own_architecture_current():
    """NEGATIVE on the defect: Z2's BGA must not carry Z1's current."""
    rc = PP.rail_currents()
    for arch in ("Z1", "Z2"):
        for s in PP.graph(arch):
            if s.owner.startswith("P_BGA"):
                assert s.i_dc_a == pytest.approx(rc[arch]["hv_total_a"], rel=1e-12), (
                    f"{s.seg_id} carries {s.i_dc_a} A but {arch} draws "
                    f"{rc[arch]['hv_total_a']}")
                other = "Z2" if arch == "Z1" else "Z1"
                assert s.i_dc_a != pytest.approx(rc[other]["hv_total_a"], rel=1e-12)


def test_bga_is_solder_not_copper():
    """The Segment default is copper; leaving it there mislabels the BGA by ~7x in rho."""
    for arch in ("Z1", "Z2"):
        for s in PP.graph(arch):
            if s.owner.startswith("P_BGA"):
                assert s.conductor == PP.BGA_CONDUCTOR
                assert "solder" in s.conductor
                assert s.conductor != "copper"


def test_microbump_conductor_is_not_plain_copper():
    for arch in ("Z1", "Z2"):
        for s in PP.graph(arch):
            if s.owner.startswith("P_microbump"):
                assert s.conductor == PP.MICROBUMP_CONDUCTOR


@pytest.mark.parametrize("arch", ["Z1", "Z2"])
def test_return_chain_is_continuous_end_to_end(arch):
    segs = [s for s in PP.graph(arch) if s.seg_id.split("-")[1].startswith("R")]
    for a, b in zip(segs, segs[1:]):
        assert a.to == b.frm, f"{a.seg_id} -> {b.seg_id}: {a.to!r} != {b.frm!r}"
    assert "pcb ground" in segs[-1].to.lower()


def test_a_broken_return_node_is_detected(monkeypatch):
    """NEGATIVE: the return chain was previously only checked at its first node."""
    real = PP.z1_segments

    def broken():
        segs = list(real())
        i = next(k for k, s in enumerate(segs) if s.seg_id == "Z1-R03")
        from dataclasses import replace
        segs[i] = replace(segs[i], frm="somewhere else entirely")
        return segs

    monkeypatch.setattr(PP, "z1_segments", broken)
    r = PP.check("Z1")
    assert not r["ok"]
    assert any("return chain broken" in p for p in r["problems"])


def test_a_return_that_does_not_reach_pcb_ground_is_detected(monkeypatch):
    real = PP.z1_segments

    def broken():
        segs = list(real())
        from dataclasses import replace
        segs[-1] = replace(segs[-1], to="nowhere")
        return segs

    monkeypatch.setattr(PP, "z1_segments", broken)
    r = PP.check("Z1")
    assert not r["ok"]
    assert any("PCB ground" in p for p in r["problems"])


def test_there_are_nineteen_ledger_owners():
    """Stated as 20 in an earlier summary; it is 19."""
    assert len(PP.LEDGER_OWNERS) == 19
    assert len(set(PP.LEDGER_OWNERS)) == 19
    assert len(PP.CONVERTER_INTRINSIC) == 7


def test_p_other_does_not_exist_as_a_ledger_owner():
    assert not [o for o in PP.LEDGER_OWNERS if "other" in o.lower()]
