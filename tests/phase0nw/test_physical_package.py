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


import design_record as DR  # noqa: E402


def _tmp_cfg(tmp_path, **edits):
    """Write a copy of the physical config with nested edits applied. An edit of the
    converter block makes the copy a free-standing config (no design-record restatement), so
    the loader's OWN cross-checks are what is tested."""
    c = yaml.safe_load(CFG.read_text())
    if any(k.startswith("converter.") for k in edits):
        c["converter"].pop("design", None)
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
        _tmp_cfg(tmp_path, **{"board.case": "it968g_2p4mm", "board.thickness_um": 2400.0}))
    m1, *_ = build_physical_package(edited)
    t1 = measure_layers(m1)["board"]["t_um"]

    assert t1 == pytest.approx(2400.0, abs=1e-6), (
        f"the config said 2400 um and the mesh built {t1:.0f} um -- the YAML is not "
        f"driving the solver")
    assert t1 != t0
    # TCPMT round 3: the four-tier converter does not fit the 2.4-mm board + BGA; the loader
    # records the protrusion instead of hiding it
    assert edited.cutout_fit_margin_um < 0 < base.cutout_fit_margin_um


def test_cutout_width_in_the_config_changes_the_mesh(tmp_path):
    """The opening is the 21.36 mm cell grid plus a clearance on each side, so a consistent
    edit changes both: a 2.0 mm clearance makes a 25.36 mm opening."""
    base = load_physical_package_config(CFG)
    n0 = build_physical_package(base)[0].n_elems
    edited = load_physical_package_config(_tmp_cfg(tmp_path, **{
        "cutout.width_mm": 25.36, "cutout.sidewall_clearance_mm": 2.0,
        "cutout.breakpoints_mm": [-12.68, 12.68]}))
    n1 = build_physical_package(edited)[0].n_elems
    assert n1 != n0, "widening the cutout changed no element; the config is inert"
    assert edited.cutout_mm == 25.36


def test_an_opening_that_cannot_hold_the_cells_and_the_clearance_is_refused(tmp_path):
    """NEGATIVE, with the edit this test used to make before the clearance became the
    baseline: an 18 mm opening cannot hold the 21.36 mm cell grid and two 1.0 mm rings."""
    edited = load_physical_package_config(_tmp_cfg(tmp_path, **{"cutout.width_mm": 18.0}))
    with pytest.raises(ValueError, match="clearance"):
        build_physical_package(edited)


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
    c["converter"].pop("design", None)        # a free-standing config: the loader's own check
    c["converter"]["tiers_from_substrate_downward"][0]["um"] = 20.0   # 10 -> 20
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.safe_dump(c, sort_keys=False))
    with pytest.raises(PhysicalConfigError, match="sum to"):
        load_physical_package_config(p)


@pytest.mark.parametrize("proxy", FORBIDDEN_CONV_TOTAL_UM)
def test_loader_refuses_the_embedded_cell_proxy_as_a_z2_total(tmp_path, proxy):
    c = yaml.safe_load(CFG.read_text())
    c["converter"].pop("design", None)        # a free-standing config: the loader's own check
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
    """TCPMT round 3: the converter block restates THE design record's production entry
    (36 cells, four mixed tiers, 3001 um with the land-side RDL) on the 3.2-mm board."""
    assert cfg.architecture == "ARCH_Z2_BACKSIDE"
    assert cfg.board_case == "it968g_3p2mm"
    assert cfg.board_thickness_um == 3200.0
    assert cfg.cutout_mm == 23.36
    assert cfg.cells == DR.n_vr() == 36 and cfg.cell_grid_n == 6
    assert cfg.design == DR.production_key()
    want = DR.converter_tiers("Z2")
    assert [(t.name, t.um) for t in cfg.tiers] == want
    assert cfg.conv_total_um == pytest.approx(sum(u for _n, u in want)) == 3001.0
    # the converter and its attach fit the 3.2-mm board + BGA (3500 um)
    assert cfg.cutout_fit_margin_um == pytest.approx(3200.0 + 300.0 - 30.0 - 3001.0)


def test_high_side_device_is_present_in_the_tier_list(cfg):
    """Every class of the cell sits in some tier, the high side explicitly (its absence is
    what made 1226/1258 um wrong as a Z2 total); the deepest tier is the input end."""
    parts = DR.tier_parts()
    held = {c for t in cfg.tier_names() for c in parts.get(t, {})}
    assert held == {"gan_hs", "gan_ls", "inductor", "cap_fly"}
    assert parts[cfg.tier_names()[-1]].get("gan_hs"), "the deepest tier holds no high side"


def test_mesh_matches_the_configured_converter_total(cfg):
    """The config states 1963 um; the mesh must deliver exactly that.

    This replaces a guard that read a hand-maintained `implemented:` flag. The flag is
    gone -- implementation state belongs to the gate registry, not to configuration --
    and the invariant that actually matters is config-against-mesh, which cannot be
    satisfied by editing a boolean.
    """
    import z2_converter as _Z2C
    m = build_physical_package(cfg)[0]
    total = sum(r["mesh_um"] or 0.0 for r in _Z2C.tier_report(cfg, m))
    assert total == pytest.approx(cfg.conv_total_um, abs=1e-6), (
        f"config says {cfg.conv_total_um:.1f} um, mesh built {total:.1f} um")


def test_config_carries_no_implementation_state(cfg):
    """Configuration describes the package; the gate registry owns progress."""
    import yaml as _y
    c = _y.safe_load(CFG.read_text())
    assert "open_gates" not in c, "the handwritten open-gate list is back"
    assert "implemented" not in c["converter"]
    flat = _y.safe_dump(c).lower()
    for word in ("still open", "not yet implemented", "gate --"):
        assert word not in flat, f"status bookkeeping leaked back into config: {word!r}"


def test_material_mapping_is_declared_with_status(cfg):
    """The geometry gate must not be read as a material claim."""
    import yaml as _y
    c = _y.safe_load(CFG.read_text())
    mm = c["converter"]["material_mapping"]
    assert mm["mixed_tiers"]["status"] == "BOUNDED", (
        "the mixed-tier cards rest on declared inputs; they must stay BOUNDED")
    # per-tier material fidelity remains open -- asserted against the GATE REGISTRY,
    # which owns that state, not against a config field
    import json as _j
    reg = _j.loads((R / "research/phase0nw/physical_gates.json").read_text())
    opens = {r["id"] for r in reg["gates"] if r["status"] == "OPEN"}
    assert {"mat.mlcc_bounded", "mat.gan_bounded"} <= opens


def test_out_of_cell_is_declared_with_every_case(cfg):
    """Production: encapsulant between the cells with the specified 1.0 mm clearance ring
    VOID (F1_clearance). The sidewall-filled F1_encapsulated (the earlier, mistaken
    baseline) and F2 void are sensitivities."""
    import yaml as _y
    o = _y.safe_load(CFG.read_text())["out_of_cell"]
    assert set(o["cases"]) == {"F1_clearance", "F1_encapsulated", "F2_void"}
    assert o["primary"] == "F1_clearance"
    assert o["cases"]["F1_clearance"]["ring"] == "VOID"
    assert "SENSITIVITY ONLY" in o["cases"]["F1_encapsulated"]["note"]
    assert o["bracket_required"] is True
    # the governing fraction is of the OPENING, not of the substrate
    assert abs(o["fraction_of_opening_pct"]
               - 100 * (1 - DR.n_vr() * DR.cell_area_mm2() / 23.36 ** 2)) < 0.2


# ===================================================== the converter (brief 13, 14, 15)
import numpy as np  # noqa: E402

import z2_converter as Z2C  # noqa: E402

# The converter hangs from the substrate underside (z = 0) through the explicit 30 um
# VR-to-substrate attach (Z2_DIRECT_FEED_ARCHITECTURE.md section 4), tier by tier in the
# order the design record states (TCPMT round 3: output end against the attach, input end
# deepest); the expected depths are derived from the record, never retyped.
ATTACH_UM = 30.0


def _spec_z():
    z, out = -ATTACH_UM, {}
    for i, (n, um) in enumerate(DR.converter_tiers("Z2")):
        out[f"conv_{i}_{n}"] = (z, z - um)
        z -= um
    return out


SPEC_Z = _spec_z()


@pytest.fixture(scope="module")
def built(cfg):
    m, mats, st, tiles = build_physical_package(cfg)
    return cfg, m, tiles


def _pcb_backside(cfg):
    return -cfg.board_thickness_um - 300.0      # board z0 in the mesh frame (unused: depths
                                                # are measured from the substrate underside)


def test_full_area_converter_slab_is_gone(built):
    cfg, m, _ = built
    assert "conv" not in set(m.elem_layer), (
        "the full-area 1226 um converter slab is still in the physical mesh")


def test_converter_totals_the_record_in_the_mesh(built):
    cfg, m, _ = built
    rows = Z2C.tier_report(cfg, m)
    assert len(rows) == len(DR.converter_tiers("Z2"))
    for r in rows:
        assert r["mesh_um"] == pytest.approx(r["spec_um"], abs=1e-6), (
            f"{r['tier']}: config {r['spec_um']} um, mesh {r['mesh_um']} um")
    assert sum(r["mesh_um"] for r in rows) == pytest.approx(
        sum(u for _n, u in DR.converter_tiers("Z2")), abs=1e-6)


@pytest.mark.parametrize("tier,z", sorted(SPEC_Z.items()))
def test_each_tier_sits_at_its_specified_depth(built, tier, z):
    """Totalling right is not enough: the tiers must be in the record's ORDER. An inverted
    stack totals the same but puts the high side against the substrate."""
    cfg, m, _ = built
    r = next(r for r in Z2C.tier_report(cfg, m) if r["tier"] == tier)
    assert r["z1_um"] == pytest.approx(z[0], abs=0.5), f"{tier} top"
    assert r["z0_um"] == pytest.approx(z[1], abs=0.5), f"{tier} bottom"


def test_high_side_is_deepest_and_clears_the_pcb_backside(built):
    cfg, m, _ = built
    off = _pcb_backside(cfg)
    rows = Z2C.tier_report(cfg, m)
    deepest = min(rows, key=lambda r: r["z0_um"])
    first = DR.tiers()[0]["name"]
    assert deepest["tier"].endswith(first), (
        f"the deepest tier is {deepest['tier']}, not the input-end tier {first}")
    assert deepest["z0_um"] > off, "the converter protrudes below the PCB backside"


def test_the_attach_tier_sits_between_the_converter_and_the_substrate(built):
    """The converter no longer touches the substrate: the explicit attach fills 0..-30 um."""
    cfg, m, _ = built
    lay = measure_layers(m)
    a = lay["conv_attach_vr_substrate"]
    assert a["z1_um"] == pytest.approx(0.0, abs=1e-6)
    assert a["z0_um"] == pytest.approx(-ATTACH_UM, abs=1e-6)
    assert cfg.attach_um == pytest.approx(ATTACH_UM)


def test_converter_descends_into_the_cutout_not_in_series_below_the_bga(built):
    """The HVR shares the board's z range; it does not push the board further down."""
    cfg, m, _ = built
    lay = measure_layers(m)
    assert lay["board"]["z0_um"] == pytest.approx(-cfg.board_thickness_um - 300.0, abs=1e-6)
    assert lay["board"]["z1_um"] == pytest.approx(-300.0, abs=1e-6)
    assert lay["bga"]["z1_um"] == pytest.approx(0.0, abs=1e-6)
    conv_bottom = min(r["z0_um"] for r in Z2C.tier_report(cfg, m))
    assert conv_bottom > lay["board"]["z0_um"], (
        "the converter extends below the PCB backside")
    assert conv_bottom < lay["board"]["z1_um"], (
        "the converter does not reach into the board's z range -- it is in series again")


def test_no_converter_medium_outside_a_cell_footprint(built):
    cfg, m, _ = built
    names = {t[0] for t in Z2C.converter_layers(cfg)}
    sel = np.array([l in names for l in m.elem_layer])
    mat = np.array(m.elem_material)[sel]
    tile = np.array(m.elem_tile)[sel]
    stray = sorted(set(mat[(mat != "underfill_homog") & (tile < 0)]))
    assert not stray, f"converter media outside a cell footprint: {stray}"


def test_out_of_cell_region_is_declared_and_present(built):
    cfg, m, _ = built
    names = {t[0] for t in Z2C.converter_layers(cfg)}
    sel = np.array([l in names for l in m.elem_layer])
    mat = np.array(m.elem_material)[sel]
    assert (mat == "underfill_homog").any(), "F1 encapsulant is absent from the opening"
    assert "hvr_effective" not in set(mat[np.array(m.elem_tile)[sel] < 0])


def test_void_variant_removes_the_out_of_cell_material(cfg):
    """F2: 'void' must mean no element, not an air-property relabel."""
    m_void = build_physical_package(cfg, out_of_cell="F2_void")[0]
    names = {t[0] for t in Z2C.converter_layers(cfg)}
    sel = np.array([l in names for l in m_void.elem_layer])
    assert sel.sum() > 0
    assert not (np.array(m_void.elem_material)[sel] == "underfill_homog").any()
    assert m_void.n_elems < build_physical_package(cfg)[0].n_elems


def test_overlapping_geometry_is_rejected(cfg):
    """NEGATIVE: the no-overlap gate must actually fire.

    Two layers sharing a z slab AND a lateral region would interpenetrate. Emitting two
    coincident elements instead of raising is how a converter could be built through the
    board without anything going red.
    """
    from etm.mesh import build as mesh_build
    st = build_physical_package(cfg)[2]
    with pytest.raises(ValueError, match="overlapping geometry"):
        mesh_build([], st, 0.30, h_xy=6.0,
                   explicit_bottom_layers=[("a", -0.1, 0.0, "silicon", 1, "all"),
                                           ("b", -0.1, 0.0, "silicon", 1, "all")])
