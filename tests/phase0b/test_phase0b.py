"""Phase-0B harness tests: DOE parsing, geometry legality, conservation, units, parsing.

These guard the properties that make the DOE a CONTROLLED experiment. If any fails,
a C05-vs-C07 comparison is not measuring architecture.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0b"))

from etm import ccxio, metrics                                        # noqa: E402
from etm.config import (MM_PER_M_INV, W_M2K_TO_W_MM2K, build_materials,  # noqa: E402
                        derive_tsv_homog, load_doe, load_stack, open_decisions)
from etm.mesh import build                                            # noqa: E402
from etm.placement import PlacementError, Tile, case_tiles, generate, validate  # noqa: E402


@pytest.fixture(scope="module")
def cfg():
    return load_stack(), load_doe()


# --------------------------------------------------------------------- DOE parsing
def test_all_20_cases_present(cfg):
    _, doe = cfg
    assert sorted(doe["cases"]) == [f"C{i:02d}" for i in range(1, 21)]


def test_execution_gating_declared(cfg):
    _, doe = cfg
    eo = doe["execution_order"]
    assert eo["gate_1"] == ["C05", "C07"]
    assert eo["gate_2"] == ["C13"]
    all_ids = set(eo["gate_1"]) | set(eo["gate_2"]) | set(eo["deferred"])
    assert all_ids == set(doe["cases"]), "every case must be assigned to a gate"


def test_every_case_carries_required_fields(cfg):
    _, doe = cfg
    for cid, c in doe["cases"].items():
        for k in ("n_vr", "placement", "tile_ax", "tile_ay", "h_sub", "p_hvr_total_w"):
            assert k in c, f"{cid} missing {k}"


# --------------------------------------------------------------- tile area / footprint
def test_tile_area_matches_normalized_footprint_rule(cfg):
    """A_tile * N must equal the case's declared total footprint."""
    stack, doe = cfg
    for cid, c in doe["cases"].items():
        want = c.get("a_vr_total_mm2", doe["defaults"]["a_vr_total_mm2"])
        got = c["tile_ax"] * c["tile_ay"] * c["n_vr"]
        assert math.isclose(got, want, rel_tol=2e-4), f"{cid}: A_total {got} != {want}"


def test_constant_footprint_across_count_sweep(cfg):
    """The count sweep must not conflate 'more VRs' with 'more embedded material'."""
    stack, doe = cfg
    sweep = ["C01", "C05", "C13", "C17"]           # N = 2, 4, 6, 8
    areas = {c: sum(t.area for t in case_tiles(doe["cases"][c], stack, doe)) for c in sweep}
    # Tile dimensions are specified to 4 dp in the DOE, so total areas agree to ~1e-3 mm^2
    # (1 part in 1e5). That is far below any mechanically meaningful difference.
    spread = max(areas.values()) - min(areas.values())
    assert spread < 0.01, f"footprint spread {spread:.6f} mm^2 across the count sweep: {areas}"


# ------------------------------------------------------------ coordinate generation
def test_all_cases_generate_and_validate(cfg):
    stack, doe = cfg
    for cid, c in doe["cases"].items():
        tiles = case_tiles(c, stack, doe)
        assert len(tiles) == c["n_vr"], cid


def test_no_tile_overlap(cfg):
    stack, doe = cfg
    for cid, c in doe["cases"].items():
        tiles = case_tiles(c, stack, doe)
        for i in range(len(tiles)):
            for j in range(i + 1, len(tiles)):
                a, b = tiles[i], tiles[j]
                ox = min(a.x1, b.x1) - max(a.x0, b.x0)
                oy = min(a.y1, b.y1) - max(a.y0, b.y0)
                assert ox <= 1e-9 or oy <= 1e-9, f"{cid}: tiles {i},{j} overlap"


def test_edge_legality(cfg):
    """Every tile edge stays inside the die footprint minus the keep-out."""
    stack, doe = cfg
    Dx = stack["geometry"]["functional_die"]["size_x"]["value"]
    Dy = stack["geometry"]["functional_die"]["size_y"]["value"]
    ko = doe["placement_rules"]["edge_keepout_mm"]["value"]
    for cid, c in doe["cases"].items():
        for t in case_tiles(c, stack, doe):
            assert t.x0 >= -Dx / 2 + ko - 1e-9 and t.x1 <= Dx / 2 - ko + 1e-9, cid
            assert t.y0 >= -Dy / 2 + ko - 1e-9 and t.y1 <= Dy / 2 - ko + 1e-9, cid


def test_overlap_detector_actually_rejects():
    """The validator must fail on a known-bad layout (guards against a vacuous check)."""
    bad = [Tile(0, 0, 4, 4, 10.0), Tile(1, 0, 4, 4, 10.0)]
    with pytest.raises(PlacementError, match="gap"):
        validate(bad, die_x=22.36, die_y=22.36, keepout=0.5, min_gap=0.5,
                 p_total=20.0, n_vr=2)


def test_edge_detector_actually_rejects():
    far = [Tile(50, 0, 4, 4, 10.0), Tile(-50, 0, 4, 4, 10.0)]
    with pytest.raises(PlacementError, match="legal region"):
        validate(far, die_x=22.36, die_y=22.36, keepout=0.5, min_gap=0.5,
                 p_total=20.0, n_vr=2)


def test_oversized_tile_rejected():
    with pytest.raises(PlacementError, match="cannot fit"):
        generate("distributed_2x2", 4, 30.0, 30.0, die_x=22.36, die_y=22.36,
                 keepout=0.5, min_gap=0.5, p_total=42.0)


def test_asymmetric_left_is_actually_asymmetric(cfg):
    """C07/C15 must break mirror symmetry, otherwise the discrimination case is void."""
    stack, doe = cfg
    for cid in ("C07", "C15"):
        tiles = case_tiles(doe["cases"][cid], stack, doe)
        assert all(t.cx < 0 for t in tiles), f"{cid} must lie entirely left of centre"
        cx = sum(t.cx * t.power_w for t in tiles) / sum(t.power_w for t in tiles)
        assert cx < -1.0, f"{cid} heat centroid {cx} is not meaningfully offset"


def test_symmetric_cases_are_symmetric(cfg):
    """C05/C13 heat centroid must sit at the origin - the control against C07."""
    stack, doe = cfg
    for cid in ("C05", "C13", "C17"):
        tiles = case_tiles(doe["cases"][cid], stack, doe)
        P = sum(t.power_w for t in tiles)
        cx = sum(t.cx * t.power_w for t in tiles) / P
        cy = sum(t.cy * t.power_w for t in tiles) / P
        assert abs(cx) < 1e-9 and abs(cy) < 1e-9, f"{cid} centroid ({cx},{cy})"


# --------------------------------------------------------------- power conservation
def test_heat_source_integral_conserved(cfg):
    stack, doe = cfg
    for cid, c in doe["cases"].items():
        want = c.get("p_hvr_total_w", doe["defaults"]["p_hvr_total_w"])
        got = sum(t.power_w for t in case_tiles(c, stack, doe))
        assert math.isclose(got, want, rel_tol=1e-12), f"{cid}: {got} != {want}"


def test_hvr_heat_sensitivity_cases_bracket_nominal(cfg):
    _, doe = cfg
    assert doe["cases"]["C19"]["p_hvr_total_w"] == pytest.approx(0.75 * 42.0)
    assert doe["cases"]["C20"]["p_hvr_total_w"] == pytest.approx(1.25 * 42.0)


def test_mesh_conserves_volumes(cfg):
    """Discretised tile / TSV / underfill / TIM volumes must equal the analytic values."""
    stack, doe = cfg
    c = doe["cases"]["C05"]
    tiles = case_tiles(c, stack, doe)
    m = build(tiles, stack, c["h_sub"], h_xy=0.9, z_scale=0.6)
    V = m.elem_volumes()
    g = stack["geometry"]
    t_tile = g["hvr_tile"]["thickness"]["value"]
    a_die = g["functional_die"]["size_x"]["value"] * g["functional_die"]["size_y"]["value"]

    assert V[m.elem_material == "hvr_effective"].sum() == pytest.approx(
        sum(t.area for t in tiles) * t_tile, rel=1e-6)
    assert V[m.elem_material == "tsv_homog"].sum() == pytest.approx(
        sum(t.area for t in tiles) * (c["h_sub"] - t_tile), rel=1e-6)
    assert V[m.elem_material == "underfill_homog"].sum() == pytest.approx(
        a_die * g["interface_layer"]["thickness"]["value"], rel=1e-6)
    assert V[m.elem_material == "tim"].sum() == pytest.approx(
        a_die * g["tim"]["thickness"]["value"], rel=1e-6)


def test_mesh_resolves_required_through_thickness_elements(cfg):
    """Spec: >=4-6 elements through the Si substrate, 3-4 through the die."""
    stack, doe = cfg
    c = doe["cases"]["C05"]
    m = build(case_tiles(c, stack, doe), stack, c["h_sub"], h_xy=0.6, z_scale=1.0)
    assert m.layers[0].nz + m.layers[1].nz >= 4
    assert m.layers[3].nz >= 3


def test_mesh_elements_all_positive_volume(cfg):
    stack, doe = cfg
    c = doe["cases"]["C07"]
    m = build(case_tiles(c, stack, doe), stack, c["h_sub"], h_xy=0.9, z_scale=0.6)
    assert (m.elem_volumes() > 0).all()


def test_c05_c07_are_a_controlled_comparison(cfg):
    """C05 vs C07 must differ ONLY in placement.

    Element counts are NOT required to match: the in-plane grid conforms to tile
    edges, so moving a tile changes where breakpoints fall and hence the division
    count. What must match exactly is the physics content - identical material
    volumes, identical through-thickness discretisation, identical z-planes - with
    both meshes independently demonstrated converged. A residual difference in
    element count is absorbed by the convergence uncertainty band.
    """
    stack, doe = cfg
    ms = {}
    for cid in ("C05", "C07"):
        c = doe["cases"][cid]
        ms[cid] = build(case_tiles(c, stack, doe), stack, c["h_sub"], h_xy=0.6, z_scale=1.0)

    assert np.allclose(ms["C05"].zs, ms["C07"].zs), "z-planes must be identical"
    assert [l.nz for l in ms["C05"].layers] == [l.nz for l in ms["C07"].layers]

    for mat in ("hvr_effective", "tsv_homog", "silicon", "tim", "underfill_homog"):
        a = ms["C05"].elem_volumes()[ms["C05"].elem_material == mat].sum()
        b = ms["C07"].elem_volumes()[ms["C07"].elem_material == mat].sum()
        assert a == pytest.approx(b, rel=1e-6), f"{mat}: {a} vs {b}"

    # Element counts legitimately differ (graded grid conforms to tile edges, which
    # sit at different coordinates). This is absorbed by the convergence uncertainty
    # band, which is why the convergence study is a precondition for the comparison.
    d = abs(ms["C05"].n_elems - ms["C07"].n_elems) / ms["C05"].n_elems
    assert d < 0.20, f"element counts differ by {d:.1%}, beyond the convergence band"


# ------------------------------------------------------------------ material cards
def test_tsv_homogenisation_bounds(cfg):
    """Effective properties must lie between the Si and Cu endpoints."""
    stack, _ = cfg
    t = derive_tsv_homog(stack)
    f = t["cu_area_fraction"]
    assert f == pytest.approx(math.pi * 0.030 ** 2 / (4 * 0.060 ** 2), rel=1e-9)
    assert 0.19 < f < 0.20
    assert 130000.0 < t["E"]["value"] < 110000.0 or 110000.0 < t["E"]["value"] < 130000.0
    assert 2.6e-6 < t["cte"]["value"] < 16.66e-6
    kxy, _, kz = t["k_ortho"]["value"]
    assert 130.0 < kxy < 400.0 and 130.0 < kz < 400.0
    assert kz > kxy, "vias must conduct better along their axis than across"


def test_material_unit_conversion_to_mm_system(cfg):
    """W/(m.K) -> W/(mm.K): getting this wrong scales every temperature by 1000x."""
    stack, _ = cfg
    mats = build_materials(stack)
    line = mats["silicon"].ccx_conductivity()[1]
    assert float(line.split(",")[0]) == pytest.approx(130.0 * MM_PER_M_INV)
    assert W_M2K_TO_W_MM2K == pytest.approx(1e-6)


def test_silicon_uses_anisotropic_elasticity(cfg):
    stack, _ = cfg
    mats = build_materials(stack)
    card = mats["silicon"].ccx_elastic()
    assert "ORTHO" in card[0], "spec prefers the cubic tensor for single-crystal Si"
    assert "166000" in card[1] and "64000" in card[1] and "79600" in card[1]


def test_material_override_scales_property(cfg):
    stack, _ = cfg
    base = build_materials(stack)["underfill_homog"].cte
    hi = build_materials(stack, {"underfill_homog": {"cte": 1.3}})["underfill_homog"].cte
    assert hi == pytest.approx(base * 1.3)


def test_provisional_values_are_declared(cfg):
    """Unknowns must stay labelled - the ledger is a hard artifact, not prose."""
    stack, _ = cfg
    od = open_decisions(stack)
    joined = "\n".join(od)
    for expected in ("underfill_homog", "hvr_effective", "t_cure", "h_top"):
        assert expected in joined, f"{expected} must be flagged OPEN/PROVISIONAL"


# ---------------------------------------------------------------- result parsing
def test_frd_parser_roundtrip(tmp_path):
    frd = tmp_path / "x.frd"
    frd.write_text(
        "    1C\n"
        " -4  DISP        4    1\n"
        " -5  D1          1    2    1    0\n"
        " -5  D2          1    2    2    0\n"
        " -5  D3          1    2    3    0\n"
        " -1         1 1.00000E+00 2.00000E+00 3.00000E+00\n"
        " -1         2-1.50000E+00 0.00000E+00 4.25000E-01\n"
        " -3\n 9999\n")
    r = ccxio.read_frd(frd)
    assert "DISP" in r
    assert r["DISP"][1].tolist() == pytest.approx([1.0, 2.0, 3.0])
    assert r["DISP"][2].tolist() == pytest.approx([-1.5, 0.0, 0.425])


def test_von_mises_uniaxial():
    S = np.array([[100.0, 0, 0, 0, 0, 0]])
    assert metrics.von_mises(S)[0] == pytest.approx(100.0)


def test_von_mises_hydrostatic_is_zero():
    S = np.array([[50.0, 50.0, 50.0, 0, 0, 0]])
    assert metrics.von_mises(S)[0] == pytest.approx(0.0, abs=1e-9)


def test_principal_max_known_tensor():
    S = np.array([[10.0, -5.0, 2.0, 0.0, 0.0, 0.0]])
    assert metrics.principal_max(S)[0] == pytest.approx(10.0)
    S2 = np.array([[0.0, 0.0, 0.0, 7.0, 0.0, 0.0]])       # pure shear -> +/-tau
    assert metrics.principal_max(S2)[0] == pytest.approx(7.0)


def test_interior_nodes_exclude_interfaces(cfg):
    """A silicon-interior node must not touch any non-silicon element."""
    stack, doe = cfg
    c = doe["cases"]["C05"]
    m = build(case_tiles(c, stack, doe), stack, c["h_sub"], h_xy=0.9, z_scale=0.6)
    si = set(metrics.interior_nodes(m, "silicon").tolist())
    other = set()
    for row in m.elems[m.elem_material != "silicon"]:
        other.update(int(v) for v in row)
    assert not (si & other)
