"""PHASE 0N-W --- the complete physical Z1 and Z1/Z2 inventory equality (brief 17, 18)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0nw", "scripts/phase0mr", "scripts/phase0i", "scripts/phase0g",
          "scripts/phase0b", "scripts"):
    sys.path.insert(0, str(R / p))

import inventory_audit as INV           # noqa: E402
import z1_package as Z1P                # noqa: E402
from physical_package import (build_physical_package, build_physical_z1,  # noqa: E402
                              load_physical_package_config, measure_layers)

CFG = R / "configs/phase0nt/z2_2p4mm_cutout.yaml"

# research/Z1_Z2_PHYSICALLY_SPECIFIED_STACKS.md section 1, PCB-backside frame.
SPEC_Z1 = {
    "bottom_substrate_rdl": (3000.0, 3010.0),
    "gan_hs_EPC2014C":      (3010.0, 3695.0),
    "gan_ls_EPC2057":       (3705.0, 4343.0),
    "flying_caps":          (4353.0, 4453.0),
    "inductor_plus_cout":   (4463.0, 4963.0),
    "output_rdl":           (4963.0, 4973.0),
}


@pytest.fixture(scope="module")
def z1():
    cfg = load_physical_package_config(CFG)
    m = build_physical_z1(cfg)[0]
    lay = measure_layers(m)
    return cfg, m, lay, lay["board"]["z0_um"]


@pytest.mark.parametrize("tier,z", sorted(SPEC_Z1.items()))
def test_each_z1_tier_sits_at_its_specified_depth(z1, tier, z):
    _cfg, m, _lay, off = z1
    r = next(r for r in Z1P.tier_report(m) if r["tier"].endswith(tier))
    assert r["z0_um"] - off == pytest.approx(z[0], abs=0.5), f"{tier} bottom"
    assert r["z1_um"] - off == pytest.approx(z[1], abs=0.5), f"{tier} top"


def test_z1_package_top_matches_the_specification(z1):
    """5333 um. An extra microbump layer put it at 5343 on the first build."""
    _cfg, _m, lay, off = z1
    assert lay["tim"]["z1_um"] - off == pytest.approx(5333.0, abs=0.5)
    assert lay["die"]["z0_um"] - off == pytest.approx(4983.0, abs=0.5)


def test_z1_substrate_is_300um_not_the_1p3mm_embedded_proxy(z1):
    _cfg, _m, lay, off = z1
    t = lay["sub_lower"]["t_um"] + lay["tile_band"]["t_um"]
    assert t == pytest.approx(300.0, abs=0.5), (
        f"the physical Z1 substrate is {t:.0f} um; the 1300 um embedded proxy is back")


def test_z1_has_no_homogenised_converter_band(z1):
    """The 1226 um `hvr_effective` tile band is the proxy that EXCLUDES the high side."""
    _cfg, m, _lay, _off = z1
    band = [v for l, v, t in zip(m.elem_layer, m.elem_material, m.elem_tile)
            if l == "tile_band" and t >= 0]
    assert "hvr_effective" not in set(band), (
        "the physical Z1 still carries the homogenised embedded-cell band")


def test_z1_high_side_is_explicitly_present(z1):
    _cfg, m, _lay, off = z1
    hs = next((r for r in Z1P.tier_report(m) if "gan_hs" in r["tier"]), None)
    assert hs is not None and hs["mesh_um"] == pytest.approx(685.0, abs=1e-6), (
        "EPC2014C is absent from the physical Z1 geometry")


def test_z1_converter_is_discrete_cells_not_a_slab(z1):
    cfg, m, _lay, _off = z1
    names = {t[0] for t in Z1P.mid_layers()}
    sel = np.array([l in names for l in m.elem_layer])
    mat = np.array(m.elem_material)[sel]
    tile = np.array(m.elem_tile)[sel]
    assert sel.sum() > 0
    stray = sorted(set(mat[(mat != "underfill_homog") & (tile < 0)]))
    assert not stray, f"Z1 converter media outside a cell footprint: {stray}"
    assert len(set(tile[tile >= 0])) == cfg.cells


# ------------------------------------------------------------------ inventory (brief 18)
@pytest.fixture(scope="module")
def inv():
    return INV.audit()


def test_both_architectures_have_49_cells(inv):
    assert inv["cells_z1"] == inv["cells_z2"] == 49


@pytest.mark.parametrize("comp,per_cell,total", [
    ("hs", 3, 147), ("ls", 3, 147), ("inductor", 3, 147), ("flying_cap", 2, 98)])
def test_component_counts_match_the_specified_inventory(inv, comp, per_cell, total):
    c = next(c for c in inv["components"] if c["component"] == comp)
    assert (c["count_per_cell"], c["count_total"]) == (per_cell, total)


@pytest.mark.parametrize("comp", ["hs", "ls", "inductor", "flying_cap"])
def test_active_component_volumes_are_equal_between_z1_and_z2(inv, comp):
    """A warpage difference must not be a difference in how much hardware got meshed."""
    c = next(c for c in inv["components"] if c["component"] == comp)
    assert c["equal"], (
        f"{comp}: Z1 {c['z1_volume_mm3']:.6f} mm3 vs Z2 {c['z2_volume_mm3']:.6f} mm3 "
        f"(relative {c['rel_delta']:.2e})")


def test_total_active_converter_volume_is_equal(inv):
    assert inv["active_equal"], (
        f"Z1 {inv['active_volume_z1_mm3']:.6f} vs Z2 {inv['active_volume_z2_mm3']:.6f} mm3")


def test_the_rdl_difference_is_the_only_one_and_is_justified(inv):
    """Z1 1973 um vs Z2 1963 um. The 10 um is one RDL, and the reason is recorded."""
    j = inv["rdl_justified_difference"]
    assert (j["z1_rdl_count"], j["z2_rdl_count"]) == (5, 4)
    assert inv["z1_total_converter_um"] - inv["z2_total_converter_um"] == 10.0
    assert inv["rdl_volume_z1_mm3"] > inv["rdl_volume_z2_mm3"]
    assert "sandwiched" in j["reason"] and "interconnect" in j["reason"]


def test_z1_and_z2_sit_on_the_same_board(inv):
    cfg = load_physical_package_config(CFG)
    l1 = measure_layers(build_physical_z1(cfg)[0])
    l2 = measure_layers(build_physical_package(cfg)[0])
    assert l1["board"]["t_um"] == pytest.approx(l2["board"]["t_um"], abs=1e-9), (
        "the architectures are not being compared on the same board")
    assert l1["board"]["t_um"] == pytest.approx(cfg.board_thickness_um, abs=1e-6)
    assert l1["board"]["z0_um"] == pytest.approx(l2["board"]["z0_um"], abs=1e-9)
