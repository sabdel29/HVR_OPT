"""PHASE 0N-Z --- Z3, the regulator on the PCB BACKSIDE (configs/phase0nz/z3_board_backside.yaml).

Every guard reads the MESH and the LEDGER the solver actually uses, never the YAML alone:
the tier order and z extents are measured on the built mesh, the board and BGA are checked
as full slabs, the joint search is run over the lattice, the direct-fed Z3 must never
acquire a package 48 V term, the three new 1 V conductors must each appear with their own
deposit region, and every ledger watt must be deposited."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

R = Path(__file__).resolve().parents[2]
CFG = R / "configs" / "phase0nz" / "z3_board_backside.yaml"
sys.path.insert(0, str(R / "scripts"))
for _p in ("scripts/phase0nw", "scripts/phase0mr", "scripts/phase0m", "scripts/phase0i",
           "scripts/phase0g", "scripts/phase0b"):
    sys.path.insert(0, str(R / _p))

TEMPS = {"conv": 100.0, "hs": 100.0, "ls": 100.0, "ind": 100.0, "caps": 100.0, "bga": 70.0,
         "sub": 90.0, "interface": 90.0, "attach": 95.0, "pcb_via": 80.0}
#: which ledger temperature key sets each Z3 term's resistance
KEY_OF = {"P_conv_hs": "hs", "P_conv_ls": "ls", "P_conv_inductor_dcr": "ind",
          "P_conv_cap_esr": "caps", "P_intraVR_metal": "conv", "P_intraVR_vertical": "conv",
          "P_VR_PCB_attach_VDD": "attach", "P_VR_PCB_attach_GND": "attach",
          "P_PCB_via_VDD": "pcb_via", "P_PCB_via_GND": "pcb_via",
          "P_BGA_1V_VDD": "bga", "P_BGA_1V_GND": "bga", "P_TSV_VDD": "sub",
          "P_TSV_GND": "sub", "P_pad_VDD": "interface", "P_pad_GND": "interface"}


@pytest.fixture(scope="module")
def z3():
    import final_closure_physical_etm as E
    import physical_package as PP
    m, mats, st, tiles, info = E.build("Z3", 1.1, (1, 1))
    return {"m": m, "mats": mats, "st": st, "tiles": tiles, "info": info,
            "cfg": PP.load_z3_package_config()}


@pytest.fixture(scope="module")
def led():
    import final_closure_ledger as FL
    return FL.ledger("Z3", "HV_S0", TEMPS, 23.7)


# ------------------------------------------------------------------ geometry, from the mesh
def test_tier_order_and_z_extents_are_measured_on_the_mesh(z3):
    import final_closure_ledger as FL
    import z3_package as Z3P
    from physical_package import measure_layers
    m, cfg = z3["m"], z3["cfg"]
    lay = measure_layers(m)
    ex = yaml.safe_load(CFG.read_text())["expected"]
    # walking DOWN from the board: the attach, then the tiers in config order, HS deepest
    z = -(cfg.bga_height_um + cfg.board_thickness_um)
    expect = [(Z3P.attach_layer(cfg), cfg.attach_um)] + [
        (f"z3conv_{i}_{t.name}", t.um) for i, t in enumerate(cfg.tiers)]
    for name, t in expect:
        assert lay[name]["z1_um"] == pytest.approx(z, abs=1e-6), name
        assert lay[name]["z0_um"] == pytest.approx(z - t, abs=1e-6), name
        z -= t
    assert [n for n, _ in expect][-1] == FL.LAYERS["Z3"]["hs"] == "z3conv_7_gan_hs_EPC2014C"
    assert min(m.layers, key=lambda L: L.z0).name == FL.LAYERS["Z3"]["hs"]
    assert [lay["board"]["z0_um"], lay["board"]["z1_um"]] == pytest.approx(ex["board_span_um"])
    assert [lay["bga"]["z0_um"], lay["bga"]["z1_um"]] == pytest.approx([-300.0, 0.0], abs=1e-6)
    conv = [lay[n] for n, _ in expect[1:]]
    assert [min(c["z0_um"] for c in conv), max(c["z1_um"] for c in conv)] == pytest.approx(
        ex["converter_span_um"])
    # the package above the board is Z2's: substrate, top RDL, microbumps, die, TIM
    for name, z0, z1 in (("sub_lower", 0.0, 280.0), ("tile_band", 280.0, 300.0),
                         ("z2_top_rdl", 300.0, 310.0), ("interface", 310.0, 320.0),
                         ("die", 320.0, 620.0), ("tim", 620.0, 670.0)):
        assert [lay[name]["z0_um"], lay[name]["z1_um"]] == pytest.approx([z0, z1], abs=1e-6)
    assert [float(m.zs.min()) * 1e3, float(m.zs.max()) * 1e3] == pytest.approx(
        [ex["z_min_um"], ex["z_max_um"]], abs=1e-6)
    # the ledger's layer map names exactly the meshed tiers, and the intra-VR routing reads
    # the same tier order as Z2's
    for k in ("hs", "ls", "caps", "ind", "attach", "pcb_via", "lv", "tsv", "pads", "bga"):
        assert FL.LAYERS["Z3"][k] in lay, k
    assert all(n in lay for n in FL.LAYERS["Z3"]["rdl"])
    assert FL.cell_tiers("Z3") == FL.cell_tiers("Z2")


def test_the_routing_reads_z3s_own_tier_list(tmp_path, monkeypatch):
    import final_closure_ledger as FL
    c = yaml.safe_load(CFG.read_text())
    c["converter"]["tiers_from_board_downward"].reverse()
    p = tmp_path / "z3_reordered.yaml"
    p.write_text(yaml.safe_dump(c, sort_keys=False))
    monkeypatch.setattr(FL, "Z3_CFG", p)
    assert FL.cell_tiers("Z3") == list(reversed(FL.cell_tiers("Z2")))


def test_a_tier_list_that_differs_from_z2s_is_refused(tmp_path):
    import physical_package as PP
    c = yaml.safe_load(CFG.read_text())
    t = c["converter"]["tiers_from_board_downward"]
    t[3], t[7] = t[7], t[3]                             # LS and HS swapped: same total
    p = tmp_path / "z3_swapped.yaml"
    p.write_text(yaml.safe_dump(c, sort_keys=False))
    with pytest.raises(PP.PhysicalConfigError):
        PP.load_z3_package_config(p)


def test_board_and_bga_are_full_slabs_without_a_cutout(z3):
    import pkg_rdl_network as K
    m, st, cfg = z3["m"], z3["st"], z3["cfg"]
    g = st["geometry"]["power_substrate"]
    area = g["size_x"]["value"] * g["size_y"]["value"]
    assert K.architecture_cutout_mm("Z3") is None and cfg.cutout_mm is None
    cen, vol = m.elem_centroids(), m.elem_volumes()
    lay = np.asarray(m.elem_layer, dtype=object)
    for name in ("board", "bga"):
        L = m.layer(name)
        sel = lay == name
        assert vol[sel].sum() == pytest.approx(area * (L.z1 - L.z0), rel=1e-9), name
        assert np.any(sel & (np.abs(cen[:, 0]) < 1.0) & (np.abs(cen[:, 1]) < 1.0)), name
    # the via fields are in the board exactly under the 49 cells, the board card elsewhere
    mat = np.asarray(m.elem_material, dtype=object)
    board = lay == "board"
    assert set(mat[board & (np.asarray(m.elem_tile) >= 0)]) == {"pcb_via_field"}
    assert set(mat[board & (np.asarray(m.elem_tile) < 0)]) == {"board_fr4"}
    # the converter tiers and the attach exist only inside the cell-grid bbox
    half = cfg.cell_grid_bbox_mm / 2.0
    for L in m.layers:
        if L.name.startswith("z3conv_") or L.name == "z3_attach_vr_pcb":
            c = cen[lay == L.name]
            assert np.abs(c[:, :2]).max() < half, L.name
            assert np.prod(np.ptp(m.nodes[np.unique(m.elems[lay == L.name]) - 1][:, :2],
                                  axis=0)) == pytest.approx(cfg.cell_grid_bbox_mm ** 2)


def test_joint_search_runs_over_the_full_bga_lattice(z3):
    import final_closure_physical_etm as E
    import physical_coords as PCO
    import pkg_rdl_network as K
    m = z3["m"]
    assert len(PCO.bga_lattice_sites(K.architecture_cutout_mm("Z3"))) == 1369
    assert z3["cfg"].bga_sites_total == 1369
    # a uniform shear across the standoff must be seen at EVERY one of the 1369 sites
    U = np.zeros((m.n_nodes + 1, 3))
    U[1:, 0] = 1e-3 * m.nodes[:, 2]
    js = E.joint_search(m, U, np.full(m.n_nodes, 50.0), "Z3", z3["tiles"])
    assert js["n_sites"] == js["n_evaluated"] == 1369
    du = np.array([r["du_um"] for r in js["ranked"]])
    assert du == pytest.approx(1e-3 * z3["cfg"].bga_height_um, rel=1e-6)


def test_bottom_films_cover_the_exposed_underside_exactly_once(z3):
    """Z3's converter hangs under the board, so the lowest layer is the HS tier: the plate
    must sit on its whole underside, the natural-convection film on the board underside
    where nothing covers it, and together they must be every downward face open to air."""
    import final_closure_ledger as FL
    import final_closure_physical_etm as E
    import production_et as PE
    m, cfg = z3["m"], z3["cfg"]
    bot = set(map(int, E.board_bottom_faces(m, "Z3")))
    plate = E.z3_converter_cold_plate(m, 1100.0)
    pl = set(map(int, plate["elems"]))
    assert plate["layer"] == FL.LAYERS["Z3"]["hs"] and not bot & pl
    tops = {tuple(sorted(r[4:])) for r in m.elems}
    exposed = {i + 1 for i, r in enumerate(m.elems) if tuple(sorted(r[:4])) not in tops}
    assert exposed == bot | pl
    area = lambda ids: sum(PE.ccxio.face_area(m, e) for e in ids)          # noqa: E731
    g = z3["st"]["geometry"]["power_substrate"]
    assert area(pl) == pytest.approx(cfg.cell_grid_bbox_mm ** 2)
    assert area(bot) == pytest.approx(g["size_x"]["value"] * g["size_y"]["value"]
                                      - cfg.cell_grid_bbox_mm ** 2)


# ------------------------------------------------------------------ ledger
def test_direct_fed_z3_carries_no_package_48v_term(led):
    import final_closure_ledger as FL
    terms = {r["term"] for r in led["rows"]}
    spec = yaml.safe_load(CFG.read_text())["ledger"]
    assert set(spec["forbidden_terms"]) == set(FL.FORBIDDEN_DIRECT_FEED_TERMS)
    assert not terms & set(FL.FORBIDDEN_DIRECT_FEED_TERMS)
    assert not [r["term"] for r in led["rows"] if r["rail"] == "48V"]
    assert set(spec["required_terms"]) <= terms, set(spec["required_terms"]) - terms
    assert FL.HV_FEED["Z3"] == "DIRECT_FEED" and FL.VARIANT["Z3"] == "Z3_BOARD_BACKSIDE"
    assert led["external_feed"]["in_package_internal_total"] is False
    with pytest.raises(RuntimeError, match="package 48 V terms"):
        FL.check_direct_feed("Z3", led["rows"] + [{"term": "P_BGA_supply"}])


def test_attach_pcb_via_and_bga_1v_rows_are_present_in_their_own_regions(led):
    import final_closure_ledger as FL
    import pad_interface as PAD
    import rms_currents as RMS
    from interconnect import rho_cu
    rows = {r["term"]: r for r in led["rows"]}
    lay = FL.LAYERS["Z3"]
    i_cell = RMS.cell_currents()["i_cell_out_rms_a"]
    n_att = {"VDD": 13, "GND": 12}          # the 5 x 5 legal lattice, checkerboard
    a_ann = np.pi / 4.0 * (250.0 ** 2 - 200.0 ** 2) * 1e-12
    for rail in ("VDD", "GND"):
        a, v, b = (rows[f"P_VR_PCB_attach_{rail}"], rows[f"P_PCB_via_{rail}"],
                   rows[f"P_BGA_1V_{rail}"])
        assert (a["deposit_layer"], v["deposit_layer"], b["deposit_layer"]) == (
            lay["attach"], "board", "bga")
        assert min(a["P_w"], v["P_w"], b["P_w"]) > 0 and {a["rail"], v["rail"], b["rail"]} == {"1V"}
        # PCB vias: rho_Cu(T) L / A_annulus, n in parallel per rail per cell, 49 cells
        r_via = rho_cu(TEMPS["pcb_via"]) * 2.4e-3 / a_ann
        assert v["P_w"] == pytest.approx(49 * i_cell ** 2 * r_via / n_att[rail], rel=1e-12)
        # BGA: 667 balls per rail, equal sharing, Table III ball at the BGA temperature
        assert b["P_w"] == pytest.approx((49 * i_cell) ** 2 * PAD.bga_ball_resistance_ohm(
            TEMPS["bga"]) / 667, rel=1e-12)
    d = led["z3_design"]
    assert d["vr_attach"]["bumps_per_rail_per_cell"] == n_att
    assert (d["pcb_via_field"]["n_vdd"], d["pcb_via_field"]["n_gnd"]) == (13, 12)
    assert d["pcb_via_field"]["cu_fraction_unit_cell"] == pytest.approx(0.1104, abs=1e-4)
    assert (d["bga_1v"]["n_per_rail"], d["bga_1v"]["n_total"]) == (667, 1334)
    # the spreading the model does not carry is RECORDED, never silently absent
    for t in ("P_PCB_plane_1V_spreading", "P_sub_land_1V_spreading"):
        assert rows[t]["P_w"] == 0.0 and rows[t]["maturity"] == "NOT_MODELLED"


def test_every_z3_term_is_evaluated_where_its_loss_is_deposited(led):
    import final_closure_ledger as FL
    import final_closure_physical_etm as E
    lay = FL.LAYERS["Z3"]
    tile_layers = set()
    for k in E.in_tile_keys("Z3"):
        if k in lay:
            tile_layers.update(lay[k] if isinstance(lay[k], list) else [lay[k]])
    regions = E.temperature_regions("Z3")
    for r in led["rows"]:
        if r["P_w"] <= 0:
            continue
        dep = tuple(r["deposit_layer"].split(","))
        layers, t_in = regions[KEY_OF[r["term"]]]
        assert set(dep) <= set(layers), r["term"]
        assert bool(t_in) == all(x in tile_layers for x in dep), r["term"]
    # and the per-region degree of freedom is free: heating only the via fields moves only
    # the via terms
    base = {r["term"]: r["P_w"] for r in led["rows"]}
    hot = {r["term"]: r["P_w"] for r in FL.ledger("Z3", "HV_S0", dict(TEMPS, pcb_via=120.0),
                                                  23.7)["rows"]}
    assert {k for k in base if abs(hot[k] - base[k]) > 1e-12} == {"P_PCB_via_VDD",
                                                                 "P_PCB_via_GND"}


def test_every_ledger_watt_is_deposited(z3, led, tmp_path):
    import final_closure_ledger as FL
    import final_closure_physical_etm as E
    import production_et as PE
    m, tiles = z3["m"], z3["tiles"]
    dep = E.deposits_from_ledger("Z3", led)
    total = FL.P_LOAD_W + led["P_loss_w"]
    assert sum(dep.values()) == pytest.approx(total, rel=1e-12)
    top = PE.ccxio.top_film_faces(m)
    info = E.write_thermal(m, z3["mats"], z3["st"], dep, np.full(len(top), 1e4),
                           np.full(len(top), 30.0), tmp_path / "th.inp", tiles, arch="Z3")
    assert abs(info["deposited_w"] - total) / total < 1e-6
    p = {r["term"]: r["P_w"] for r in led["rows"]}
    # the via-field loss sits ONLY in board elements under the cells, which are all via field;
    # the 1 V BGA loss over the whole BGA layer (equal sharing)
    assert dep[(("board",), True)] == pytest.approx(p["P_PCB_via_VDD"] + p["P_PCB_via_GND"])
    ids = E._region_elems(m, ("board",), True, tiles)
    assert set(np.asarray(m.elem_material, dtype=object)[ids - 1]) == {"pcb_via_field"}
    assert dep[(("bga",), False)] == pytest.approx(p["P_BGA_1V_VDD"] + p["P_BGA_1V_GND"])
    assert dep[(("z3_attach_vr_pcb",), True)] == pytest.approx(
        p["P_VR_PCB_attach_VDD"] + p["P_VR_PCB_attach_GND"])
