"""PHASE 0N-AG --- pad count is a scenario, and coordinates have one source."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0nw", "scripts/phase0m", "scripts/phase0mr", "scripts"):
    sys.path.insert(0, str(R / p))

import pad_interface as PAD        # noqa: E402
import physical_coords as PCO      # noqa: E402
import rms_currents as RMS         # noqa: E402


@pytest.fixture(scope="module")
def sysrep():
    return PAD.system(RMS.cell_currents()["i_cell_out_rms_a"])


def test_no_adopted_pad_count_is_selected(sysrep):
    """min(n_geom, max(n_drop, n_geom)) is identically n_geom -- a tautology, not a rule."""
    assert sysrep["per_cell"]["adopted"] is None
    assert "no physical criterion" in sysrep["per_cell"]["adopted_status"].lower()
    import re as _re
    src = (R / "scripts/phase0nw/pad_interface.py").read_text()
    # the expression may appear in the docstring that EXPLAINS the bug, but never as
    # live code -- so require a withdrawal note nearby, as the stale-wording guards do
    for m in _re.finditer(_re.escape("min(n_geom, max("), src):
        ctx = src[max(0, m.start() - 300):m.start()].upper()
        assert "TAUTOLOGY" in ctx or "PREVIOUS LOGIC" in ctx, (
            "the auto-max-density selector is live code again")
    assert "adopted" in src and 'return {"n_adopt' not in src


def test_the_old_selector_really_was_a_tautology():
    """NEGATIVE: demonstrate it, so nobody reintroduces it believing it chose."""
    for n_drop in (1, 4, 100, 10_000):
        assert min(4908, max(n_drop, 4908)) == 4908


def test_pad_loss_is_a_count_scenario_not_closed(sysrep):
    assert sysrep["loss_maturity"] == "SCENARIO"
    assert sysrep["count_maturity"] == "OPEN"
    assert sysrep["p_pad_vdd_w"] is None and sysrep["p_pad_gnd_w"] is None
    assert sysrep["geometry_maturity"] == "CLOSED"   # one pad IS closed
    assert sysrep["current_maturity"] == "CLOSED"


def test_the_count_span_is_enormous_and_reported(sysrep):
    s = sysrep["sensitivity"]
    # TCPMT round 3: the design record's cell (36 cells of 7.94 mm2 at 27.9 A RMS)
    assert s["n_drop"] == 5 and s["n_geom_max"] > 4000
    assert s["loss_span_factor"] > 900, "the hidden sensitivity is about three decades"
    lo = next(r for r in s["counts"] if r["is_drop_floor"])
    hi = next(r for r in s["counts"] if r["is_geom_ceiling"])
    assert lo["p_system_both_rails_w"] > 17.0      # ~19.1 W
    assert hi["p_system_both_rails_w"] < 0.02      # ~0.019 W


def test_keepout_is_actually_swept(sysrep):
    k = sysrep["sensitivity"]["keepout_cases"]
    assert set(k) == {"KO_LOW", "KO_NOM", "KO_HIGH"}
    assert len({v["n_geom_per_rail"] for v in k.values()}) == 3


def test_em_context_is_a_warning_not_an_allowable(sysrep):
    s = sysrep["sensitivity"]
    assert s["em_context_doi"] == "10.3390/ma14216394"
    assert "not an allowable" in s["em_context_status"]
    assert s["n_drop"] in s["counts_in_multi_MA_regime"], (
        "the drop-floor count sits above 1e6 A/cm2 and must be flagged")
    assert "does not set a limit" in s["em_context_note"]


def test_pad_shape_is_source_effective_not_asserted_square():
    assert PAD.PAD_SHAPE == "source_effective_area"
    assert "CONSISTENT with" in PAD.PAD_SHAPE_STATUS
    assert "does not assert a shape" in PAD.PAD_SHAPE_STATUS


# ---------------------------------------------------- coordinates have ONE source
def test_cell_coordinates_come_from_the_fe_placement():
    c = PCO.physical_cell_coordinates()
    assert len(c) == 36                     # the design record's cells (6 x 6)
    assert PCO.cell_pitch_mm(c) == pytest.approx(3.708564, abs=1e-5), (  # 6 x 6, record
        "the RDL solver had hard-coded 3.0 mm")
    xs = sorted({round(x, 6) for x, _ in c})
    assert xs[0] == pytest.approx(-9.27141, abs=1e-5)       # -(21.36 - 2.817) / 2


def test_bga_sites_are_on_the_centred_lattice():
    sup, ret = PCO.annulus_supply_return()
    for p in sup + ret:
        assert PCO.is_on_bga_lattice(*p), f"{p} is not a legal 0.8 mm lattice site"
    assert len(PCO.bga_lattice_sites()) == 1369
    assert len(PCO.bga_lattice_sites(23.36)) == 528


def test_the_synthetic_offset_sources_are_rejected():
    """NEGATIVE: the +0.4 mm offsets used for Z1 were not lattice positions."""
    c = PCO.physical_cell_coordinates()[0]
    assert not PCO.is_on_bga_lattice(c[0] + 0.4, c[1] + 0.4)
    src = (R / "scripts/phase0nw/pkg_rdl_network.py").read_text()
    assert "offset half a ball pitch" not in src or "0.4" not in src.split(
        "offset half a ball pitch")[0][-200:]
