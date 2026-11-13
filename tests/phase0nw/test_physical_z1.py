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
from physical_package import (PhysicalConfigError,  # noqa: E402
                              build_physical_package, build_physical_z1,
                              load_physical_package_config, load_z1_package_config,
                              measure_layers)

CFG = R / "configs/phase0nt/z2_2p4mm_cutout.yaml"

# research/Z1_Z2_PHYSICALLY_SPECIFIED_STACKS.md section 1, PCB-backside frame, with the
# TCPMT-revision REPARTITIONED tier order (HS -> C_f -> LS -> L, configs/phase0nx).
SPEC_Z1 = {
    "bottom_substrate_rdl": (3000.0, 3010.0),
    "gan_hs_EPC2014C":      (3010.0, 3695.0),
    "flying_caps":          (3705.0, 3805.0),
    "gan_ls_EPC2057":       (3815.0, 4453.0),
    "inductor_plus_cout":   (4463.0, 4963.0),
    "output_rdl":           (4963.0, 4973.0),
}


@pytest.fixture(scope="module")
def z1():
    cfg = load_z1_package_config()          # Z1's OWN config, not Z2's
    m = build_physical_z1(cfg)[0]
    lay = measure_layers(m)
    return cfg, m, lay, lay["board"]["z0_um"]


@pytest.mark.parametrize("tier,z", sorted(SPEC_Z1.items()))
def test_each_z1_tier_sits_at_its_specified_depth(z1, tier, z):
    _cfg, m, _lay, off = z1
    cfg = _cfg
    r = next(r for r in Z1P.tier_report(m, cfg) if r["tier"].endswith(tier))
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
    hs = next((r for r in Z1P.tier_report(m, _cfg) if "gan_hs" in r["tier"]), None)
    assert hs is not None and hs["mesh_um"] == pytest.approx(685.0, abs=1e-6), (
        "EPC2014C is absent from the physical Z1 geometry")


def test_z1_converter_is_discrete_cells_not_a_slab(z1):
    cfg, m, _lay, _off = z1
    names = {t[0] for t in Z1P.mid_layers(cfg)}
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
    l1 = measure_layers(build_physical_z1(load_z1_package_config())[0])
    cfg = load_physical_package_config(CFG)
    l2 = measure_layers(build_physical_package(cfg)[0])
    assert l1["board"]["t_um"] == pytest.approx(l2["board"]["t_um"], abs=1e-9), (
        "the architectures are not being compared on the same board")
    assert l1["board"]["t_um"] == pytest.approx(cfg.board_thickness_um, abs=1e-6)
    assert l1["board"]["z0_um"] == pytest.approx(l2["board"]["z0_um"], abs=1e-9)


# ------------------------------------------------- Z1 is config-driven (brief section 3)
Z1CFG = R / "configs" / "phase0nx" / "z1_physical.yaml"


def _tmp_z1(tmp_path, **edits):
    import yaml
    c = yaml.safe_load(Z1CFG.read_text())
    for dotted, val in edits.items():
        node = c
        *path, leaf = dotted.split(".")
        for k in path:
            node = node[k]
        node[leaf] = val
    p = tmp_path / "z1_edited.yaml"
    p.write_text(yaml.safe_dump(c, sort_keys=False))
    return p


def test_z1_has_its_own_physical_config():
    c = Z1P.load_z1_config()
    assert c["architecture"] == "ARCH_Z1_EMBEDDED"
    assert c["board"]["case"] == "it968g_2p4mm"
    assert len(c["converter"]["tiers_from_substrate_upward"]) == 9
    assert c["supply_return"]["rail_v"] == 48.0, (
        "Z1's through-substrate field carries the 48 V input, not the 1 V output")
    assert c["cutout"]["present"] is False


def test_z1_stack_is_not_a_python_constant():
    """The tiers must come from the YAML, not from a literal in the module."""
    src = (R / "scripts/phase0nw/z1_package.py").read_text()
    assert "tiers_from_substrate_upward" in src
    assert '("gan_hs_EPC2014C",     685.0)' not in src, (
        "the hard-coded tier table is back")


def test_editing_the_z1_config_changes_the_mesh(tmp_path):
    """LOAD-BEARING. The previous version of this test edited YAML and checked PARSING.

    It never built a mesh, so it would have passed even while build_physical_z1() was
    reading Z2's board case and substrate thickness -- which is exactly what it was
    doing. A config test that does not reach the mesh proves nothing about whether the
    config drives anything.
    """
    base = load_z1_package_config()
    m0 = build_physical_z1(base)[0]
    l0 = measure_layers(m0)
    t0 = l0["sub_lower"]["t_um"] + l0["tile_band"]["t_um"]
    assert t0 == pytest.approx(300.0, abs=0.5)

    edited = load_z1_package_config(_tmp_z1(
        tmp_path, **{"substrate.thickness_um": 400.0,
                     "expected.package_top_um": 5433.0}))
    m1 = build_physical_z1(edited)[0]
    l1 = measure_layers(m1)
    t1 = l1["sub_lower"]["t_um"] + l1["tile_band"]["t_um"]

    assert t1 == pytest.approx(400.0, abs=0.5), (
        f"the Z1 config said 400 um and the mesh built {t1:.0f} um")
    assert t1 != t0
    assert (l1["tim"]["z1_um"] - l1["board"]["z0_um"]) == pytest.approx(5433.0, abs=0.5)


def test_z1_refuses_to_be_built_from_the_z2_config():
    """Z1 reading Z2's board case and substrate is invisible while the two agree."""
    z2 = load_physical_package_config(CFG)
    with pytest.raises(PhysicalConfigError, match="Z2 PhysicalPackage"):
        build_physical_z1(z2)


def test_z1_config_object_carries_its_own_geometry():
    c = load_z1_package_config()
    assert c.board_case == "it968g_2p4mm"
    assert (c.substrate_um, c.cells, c.conv_total_um) == (300.0, 49, 1973.0)
    assert (c.interface_um, c.die_um, c.tim_um) == (10.0, 300.0, 50.0)
    assert c.rail_v == 48.0 and c.package_top_um == 5333.0
    assert len(c.tiers) == 9


def test_z1_loader_rejects_an_inconsistent_tier_sum(tmp_path):
    import yaml
    c = yaml.safe_load(Z1CFG.read_text())
    c["converter"]["tiers_from_substrate_upward"][0]["um"] = 20.0
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.safe_dump(c, sort_keys=False))
    with pytest.raises(ValueError, match="tiers sum to"):
        Z1P.load_z1_config(p)


def test_z1_loader_rejects_a_package_height_that_does_not_add_up(tmp_path):
    """NEGATIVE: the 5343-vs-5333 defect, caught at load time."""
    with pytest.raises(ValueError, match="package_top_um"):
        Z1P.load_z1_config(_tmp_z1(tmp_path, **{"die.thickness_um": 310.0}))


def test_z1_loader_rejects_a_legacy_board(tmp_path):
    with pytest.raises(ValueError, match="forbidden"):
        Z1P.load_z1_config(_tmp_z1(tmp_path, **{"board.case": "fr4_2p4mm"}))


def test_z1_and_z2_declare_the_same_board_and_cells():
    import yaml
    z1 = yaml.safe_load(Z1CFG.read_text())
    z2 = yaml.safe_load((R / "configs/phase0nt/z2_2p4mm_cutout.yaml").read_text())
    assert z1["board"]["case"] == z2["board"]["case"]
    assert z1["board"]["thickness_um"] == z2["board"]["thickness_um"]
    assert z1["converter"]["cells"] == z2["converter"]["cells"]
    assert z1["converter"]["cell_side_mm"] == z2["converter"]["cell_side_mm"]
    assert z1["supply_return"]["rail_v"] != 1.0, "Z1 must not be on the 1 V rail"
