"""Phase-0C tests. Phase-0B's 29 tests are preserved untouched in tests/phase0b/."""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0b"))
sys.path.insert(0, str(R / "scripts" / "phase0c"))

from descriptors import descriptors                          # noqa: E402
from etm.config import load_doe, load_stack                  # noqa: E402
from etm.mesh import build                                   # noqa: E402
from etm.placement import Tile, case_tiles                   # noqa: E402

P0B = R / "results" / "phase0b"
P0C = R / "results" / "phase0c"


@pytest.fixture(scope="module")
def cfg():
    return load_stack(), load_doe()


# ------------------------------------------------- Phase-0B preservation
def test_phase0b_configs_untouched():
    """Phase-0C must not have altered the frozen Phase-0B case definitions."""
    doe = load_doe()
    assert doe["cases"]["C05"]["placement"] == "distributed_2x2"
    assert doe["cases"]["C05"]["tile_ax"] == pytest.approx(4.8990)
    assert doe["cases"]["C07"]["placement"] == "asymmetric_left"
    assert doe["cases"]["C13"]["n_vr"] == 6
    assert doe["cases"]["C19"]["p_hvr_total_w"] == pytest.approx(31.5)
    assert doe["cases"]["C20"]["p_hvr_total_w"] == pytest.approx(52.5)


def test_phase0b_results_still_present():
    for f in ("gate_runs.csv", "mesh_convergence.csv", "cooling_calibration.json",
              "PHASE0B_FIRST_MECHANICAL_GATE.md"):
        assert (P0B / f).exists(), f"Phase-0B artifact {f} was removed"


def test_phase0b_reproduced_bit_exact():
    p = P0C / "phase0b_reproduction.json"
    if not p.exists():
        pytest.skip("reproduction not yet run")
    v = json.loads(p.read_text())
    assert v["reproduced"] is True
    assert v["ordering_preserved"] is True
    for c in v["cases"]:
        assert c["delta_pct"] < 0.5, c


# ------------------------------------------------- sweep completeness
def test_sweep_covers_exactly_c01_c20():
    p = P0C / "full_doe_results.csv"
    if not p.exists():
        pytest.skip("sweep not yet run")
    rows = list(csv.DictReader(p.open()))
    assert sorted(r["case"] for r in rows) == [f"C{i:02d}" for i in range(1, 21)]


def test_sweep_conserves_heat_and_area(cfg):
    p = P0C / "full_doe_results.csv"
    if not p.exists():
        pytest.skip("sweep not yet run")
    stack, doe = cfg
    for r in csv.DictReader(p.open()):
        c = doe["cases"][r["case"]]
        want_p = c.get("p_hvr_total_w", doe["defaults"]["p_hvr_total_w"])
        want_a = c.get("a_vr_total_mm2", doe["defaults"]["a_vr_total_mm2"])
        assert float(r["p_hvr_total_W"]) == pytest.approx(want_p, rel=1e-9), r["case"]
        assert float(r["a_vr_total_mm2"]) == pytest.approx(want_a, rel=2e-4), r["case"]


def test_sweep_energy_balance_closes():
    p = P0C / "full_doe_results.csv"
    if not p.exists():
        pytest.skip("sweep not yet run")
    for r in csv.DictReader(p.open()):
        assert abs(float(r["energy_residual_pct"])) < 0.01, f"{r['case']} energy balance"


# ------------------------------------------------- variable mapping
def test_thickness_pairs_differ_only_in_thickness(cfg):
    """The matched thickness comparisons must be genuinely matched."""
    _, doe = cfg
    for lo, hi in (("C01", "C03"), ("C05", "C08"), ("C13", "C16")):
        a, b = doe["cases"][lo], doe["cases"][hi]
        assert a["h_sub"] == 0.200 and b["h_sub"] == 0.500, (lo, hi)
        for k in ("n_vr", "placement", "tile_ax", "tile_ay", "p_hvr_total_w"):
            assert a[k] == b[k], f"{lo}/{hi} differ in {k} - not a clean thickness pair"


def test_footprint_sweep_differs_only_in_area(cfg):
    _, doe = cfg
    areas = {}
    for cid in ("C11", "C05", "C12"):
        c = doe["cases"][cid]
        assert c["n_vr"] == 4 and c["placement"] == "distributed_2x2" and c["h_sub"] == 0.200
        assert c["tile_ax"] == pytest.approx(c["tile_ay"]), f"{cid} must stay square"
        areas[cid] = c["tile_ax"] * c["tile_ay"] * c["n_vr"]
    assert areas["C11"] < areas["C05"] < areas["C12"]
    assert areas["C11"] == pytest.approx(72.0, rel=2e-4)
    assert areas["C12"] == pytest.approx(120.0, rel=2e-4)


def test_aspect_sweep_holds_area_constant(cfg):
    _, doe = cfg
    for cid in ("C05", "C09", "C10"):
        c = doe["cases"][cid]
        assert c["tile_ax"] * c["tile_ay"] * c["n_vr"] == pytest.approx(96.0, rel=2e-4), cid
    assert doe["cases"]["C09"]["tile_ax"] / doe["cases"]["C09"]["tile_ay"] == pytest.approx(2.0, rel=1e-3)
    assert doe["cases"]["C10"]["tile_ax"] / doe["cases"]["C10"]["tile_ay"] == pytest.approx(0.5, rel=1e-3)


def test_heat_sweep_holds_geometry_constant(cfg):
    _, doe = cfg
    for cid in ("C19", "C07", "C20"):
        c = doe["cases"][cid]
        assert c["placement"] == "asymmetric_left" and c["n_vr"] == 4
        assert c["tile_ax"] == pytest.approx(4.8990) and c["h_sub"] == 0.200


def test_count_sweep_is_symmetric_distributed(cfg):
    """The count control must compare like with like: symmetric distributed layouts."""
    stack, doe = cfg
    for cid in ("C05", "C13", "C17"):
        tiles = case_tiles(doe["cases"][cid], stack, doe)
        d = descriptors(tiles, 0.150)
        assert d["centroid_area_offset_mm"] < 1e-9, f"{cid} is not centred"
        assert d["A_total_mm2"] == pytest.approx(96.0, rel=2e-4)


# ------------------------------------------------- descriptors
def test_descriptor_symmetric_has_zero_first_moment(cfg):
    stack, doe = cfg
    for cid in ("C05", "C13", "C17", "C04", "C14"):
        d = descriptors(case_tiles(doe["cases"][cid], stack, doe), 0.150)
        assert d["first_moment_area_mm3"] == pytest.approx(0.0, abs=1e-9), cid
        assert d["first_moment_heat_Wmm"] == pytest.approx(0.0, abs=1e-9), cid


def test_descriptor_asymmetric_has_nonzero_first_moment(cfg):
    stack, doe = cfg
    for cid in ("C07", "C15"):
        d = descriptors(case_tiles(doe["cases"][cid], stack, doe), 0.150)
        assert d["centroid_area_offset_mm"] > 1.0, cid
        assert d["first_moment_area_mm3"] > 50.0, cid


def test_descriptor_aspect_ratio_flips_anisotropy_sign(cfg):
    stack, doe = cfg
    d9 = descriptors(case_tiles(doe["cases"]["C09"], stack, doe), 0.150)
    d10 = descriptors(case_tiles(doe["cases"]["C10"], stack, doe), 0.150)
    assert d9["anisotropy_shape_only"] > 0 > d10["anisotropy_shape_only"]
    assert d9["anisotropy_shape_only"] == pytest.approx(-d10["anisotropy_shape_only"], rel=1e-9)


def test_descriptor_area_conservation(cfg):
    stack, doe = cfg
    for cid, want in (("C11", 72.0), ("C05", 96.0), ("C12", 120.0)):
        d = descriptors(case_tiles(doe["cases"][cid], stack, doe), 0.150)
        assert d["A_total_mm2"] == pytest.approx(want, rel=2e-4), cid


def test_descriptor_second_moment_grows_with_spread(cfg):
    """Edge-biased placement must have a larger polar second moment than compact."""
    stack, doe = cfg
    compact = descriptors(case_tiles(doe["cases"]["C04"], stack, doe), 0.150)
    spread = descriptors(case_tiles(doe["cases"]["C05"], stack, doe), 0.150)
    edge = descriptors(case_tiles(doe["cases"]["C06"], stack, doe), 0.150)
    assert compact["I_polar_mm4"] < spread["I_polar_mm4"] < edge["I_polar_mm4"]


# ------------------------------------------------- discrete-TSV (H1b) machinery
def test_discrete_tsv_conserves_copper_volume(cfg):
    """H1b must contain exactly the same copper as H0, or the comparison is void."""
    stack, doe = cfg
    c = doe["cases"]["C05"]
    tiles = case_tiles(c, stack, doe)
    f_cu = math.pi * 0.030 ** 2 / (4 * 0.060 ** 2)

    m0 = build(tiles, stack, c["h_sub"], h_xy=0.45, z_scale=1.0, h_max_factor=5.0)
    v_homog = m0.elem_volumes()[m0.elem_material == "tsv_homog"].sum()

    for pitch in (1.2, 2.4):
        m1 = build(tiles, stack, c["h_sub"], h_xy=0.45, z_scale=1.0, h_max_factor=5.0,
                   tsv_discrete_pitch=pitch)
        v_cu = m1.elem_volumes()[m1.elem_material == "copper"].sum()
        assert v_cu == pytest.approx(v_homog * f_cu, rel=1e-4), f"pitch {pitch}"
        assert (m1.elem_material == "tsv_homog").sum() == 0, "H1b must not retain smeared blocks"


def test_discrete_tsv_off_by_default(cfg):
    stack, doe = cfg
    c = doe["cases"]["C05"]
    m = build(case_tiles(c, stack, doe), stack, c["h_sub"], h_xy=0.6, z_scale=0.8)
    assert (m.elem_material == "copper").sum() == 0
    assert (m.elem_material == "tsv_homog").sum() > 0


# ------------------------------------------------- materiality classification
def test_materiality_band_boundaries():
    sys.path.insert(0, str(R / "scripts" / "phase0c"))
    from analyze_variables import band
    assert band(0.05) == "BELOW-BAND"
    assert band(0.10) == "WEAK"
    assert band(0.149) == "WEAK"
    assert band(0.15) == "MODERATE"
    assert band(0.249) == "MODERATE"
    assert band(0.25) == "STRONG"
    assert band(-0.60) == "STRONG"


def test_resolution_rule_uses_two_sigma():
    from analyze_variables import resolved
    assert resolved(0.60, 0.005) is True          # 60% vs 1% -> resolved
    assert resolved(0.05, 0.05) is False          # 5% vs 10% -> not resolved
    assert resolved(0.0002, 0.005) is False       # the VR-count null
