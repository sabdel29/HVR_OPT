"""PHASE 0N-W --- the physical YAML must actually drive the solver.

The point of these guards is not that the loader parses. It is that changing a value in
the config changes the MESH, so the config cannot describe one package while the solver
builds another -- the defect commit 30f717b shipped.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0nw", "scripts/phase0mr", "scripts/phase0i", "scripts/phase0g",
          "scripts/phase0b", "scripts"):
    sys.path.insert(0, str(R / p))

from physical_package import (  # noqa: E402
    FORBIDDEN_BOARD_CASES, FORBIDDEN_CONV_TOTAL_UM, PhysicalConfigError,
    build_physical_package, load_physical_package_config, measure_layers)

CFG = R / "configs/phase0nt/z2_2p4mm_cutout.yaml"


@pytest.fixture(scope="module")
def cfg():
    return load_physical_package_config(CFG)


def _tmp_cfg(tmp_path, **edits):
    """Write a copy of the physical config with nested edits applied."""
    c = yaml.safe_load(CFG.read_text())
    for dotted, val in edits.items():
        node = c
        *path, leaf = dotted.split(".")
        for k in path:
            node = node[k]
        node[leaf] = val
    p = tmp_path / "edited.yaml"
    p.write_text(yaml.safe_dump(c, sort_keys=False))
    return p


# ------------------------------------------------------------------ the config drives it
def test_board_thickness_in_the_config_changes_the_meshed_board(tmp_path):
    """THE load-bearing test: edit the YAML, the mesh must follow."""
    base = load_physical_package_config(CFG)
    m0, *_ = build_physical_package(base)
    t0 = measure_layers(m0)["board"]["t_um"]
    assert t0 == pytest.approx(base.board_thickness_um, abs=1e-6)

    edited = load_physical_package_config(
        _tmp_cfg(tmp_path, **{"board.case": "it968g_3p2mm", "board.thickness_um": 3200.0}))
    m1, *_ = build_physical_package(edited)
    t1 = measure_layers(m1)["board"]["t_um"]

    assert t1 == pytest.approx(3200.0, abs=1e-6), (
        f"the config said 3200 um and the mesh built {t1:.0f} um -- the YAML is not "
        f"driving the solver")
    assert t1 != t0


def test_cutout_width_in_the_config_changes_the_mesh(tmp_path):
    base = load_physical_package_config(CFG)
    n0 = build_physical_package(base)[0].n_elems
    edited = load_physical_package_config(_tmp_cfg(tmp_path, **{"cutout.width_mm": 18.0}))
    n1 = build_physical_package(edited)[0].n_elems
    assert n1 != n0, "narrowing the cutout removed no elements; the config is inert"
    assert edited.cutout_mm == 18.0


def test_substrate_thickness_in_the_config_reaches_the_mesh(tmp_path):
    edited = load_physical_package_config(
        _tmp_cfg(tmp_path, **{"substrate.thickness_um": 400.0}))
    assert edited.substrate_mm == 0.4
    lay = measure_layers(build_physical_package(edited)[0])
    assert lay["sub_lower"]["t_um"] > measure_layers(
        build_physical_package(load_physical_package_config(CFG))[0])["sub_lower"]["t_um"]


# --------------------------------------------------------------- the loader refuses junk
@pytest.mark.parametrize("legacy", FORBIDDEN_BOARD_CASES)
def test_loader_refuses_a_legacy_board_case(tmp_path, legacy):
    with pytest.raises(PhysicalConfigError, match="forbidden|legacy"):
        load_physical_package_config(_tmp_cfg(tmp_path, **{"board.case": legacy}))


def test_loader_refuses_tiers_that_do_not_sum_to_the_stated_total(tmp_path):
    """NEGATIVE: a tier list and its total are two statements of one fact."""
    c = yaml.safe_load(CFG.read_text())
    c["converter"]["tiers_from_substrate_downward"][0]["um"] = 20.0   # 10 -> 20
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.safe_dump(c, sort_keys=False))
    with pytest.raises(PhysicalConfigError, match="sum to"):
        load_physical_package_config(p)


@pytest.mark.parametrize("proxy", FORBIDDEN_CONV_TOTAL_UM)
def test_loader_refuses_the_embedded_cell_proxy_as_a_z2_total(tmp_path, proxy):
    c = yaml.safe_load(CFG.read_text())
    c["converter"]["with_land_side_rdl_um"] = proxy
    c["converter"]["tiers_from_substrate_downward"] = [
        {"name": "bogus", "um": proxy, "status": "OPEN"}]
    p = tmp_path / "proxy.yaml"
    p.write_text(yaml.safe_dump(c, sort_keys=False))
    with pytest.raises(PhysicalConfigError, match="high-side"):
        load_physical_package_config(p)


def test_loader_refuses_inconsistent_cell_area_and_side(tmp_path):
    with pytest.raises(PhysicalConfigError, match="cell_area_mm2"):
        load_physical_package_config(_tmp_cfg(tmp_path, **{"converter.cell_side_mm": 3.0}))


# ------------------------------------------------------------------------- what it reads
def test_config_states_the_physical_package(cfg):
    assert cfg.architecture == "ARCH_Z2_BACKSIDE"
    assert cfg.board_case == "it968g_2p4mm"
    assert cfg.board_thickness_um == 2400.0
    assert cfg.cutout_mm == 23.36
    assert cfg.cells == 49 and cfg.cell_grid_n == 7
    assert cfg.conv_total_um == 1963.0
    assert len(cfg.tiers) == 8
    assert sum(t.um for t in cfg.tiers) == 1963.0


def test_high_side_device_is_present_in_the_tier_list(cfg):
    names = " ".join(cfg.tier_names()).lower()
    assert "hs" in names and "2014" in names, (
        "the EPC2014C high-side device must appear explicitly; its absence is what makes "
        "1226/1258 um wrong as a Z2 total")
    assert "2057" in names, "the EPC2057 low-side device must appear explicitly"


def test_converter_gate_is_honest_about_the_mesh(cfg):
    """implemented: true may only be set once the mesh actually contains the tiers."""
    lay = measure_layers(build_physical_package(cfg)[0])
    meshed = lay.get("conv", {}).get("t_um")
    if cfg.converter_implemented:
        assert meshed == pytest.approx(cfg.conv_total_um, abs=1.0), (
            f"config claims implemented but the mesh has a {meshed:.0f} um converter")
    else:
        assert meshed != pytest.approx(cfg.conv_total_um, abs=1.0), (
            "the mesh now matches the config -- flip converter.implemented to true")
