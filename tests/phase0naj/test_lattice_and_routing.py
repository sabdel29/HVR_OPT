"""PHASE 0N-AJ --- two defects that silently shrank the design space."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
for _p in ("scripts/phase0nw", "scripts/phase0m", "scripts/phase0e",
           "scripts/phase0dr", "scripts/phase0mr", "scripts"):
    sys.path.insert(0, str(R / _p))
import physical_coords as PCO                                        # noqa: E402
import routing as RT                                                 # noqa: E402


# --- defect 1: the BGA lattice was not closed under negation -------------

@pytest.mark.parametrize("cutout", [None, 23.36])
def test_lattice_is_exactly_closed_under_negation(cutout):
    """`-14.4 + i*0.8` drifts, so (14.4, 12.8) existed as
    (14.4, 12.800000000000002). select_power_sites tests `mirror not in cand`
    with exact tuple equality, so 1080 of 1369 full-lattice sites (and 408 of
    528 annulus sites) were invisible to the mirror-symmetric placement rule --
    roughly 79 % of the legal design space, chosen by floating-point luck."""
    sites = PCO.bga_lattice_sites(cutout)
    st = set(sites)
    missing = [p for p in sites if (-p[0] + 0.0, -p[1] + 0.0) not in st]
    assert not missing, (
        "%d of %d sites have no EXACT mirror, e.g. %r"
        % (len(missing), len(sites), missing[:1]))


def test_every_lattice_site_is_on_the_declared_lattice():
    for p in PCO.bga_lattice_sites():
        assert PCO.is_on_bga_lattice(*p), p


def test_snapping_does_not_move_a_site_physically():
    """A picometre snap must not change the geometry it is cleaning up."""
    n = int(round(2 * PCO.BGA_HALF_SPAN_MM / PCO.BGA_PITCH_MM)) + 1
    raw = [(-PCO.BGA_HALF_SPAN_MM + i * PCO.BGA_PITCH_MM,
            -PCO.BGA_HALF_SPAN_MM + j * PCO.BGA_PITCH_MM)
           for i in range(n) for j in range(n)]
    for (ax, ay), (bx, by) in zip(raw, PCO.bga_lattice_sites()):
        assert abs(ax - bx) < 1e-9 and abs(ay - by) < 1e-9


@pytest.mark.parametrize("arch,cut,n", [("Z1", None, 240), ("Z2", 23.36, 240)])
def test_large_counts_are_placeable_after_the_fix(arch, cut, n):
    """Z2 previously capped at 48 per rail -- an artefact, not the cutout."""
    cells = PCO.physical_cell_coordinates()
    sel = PCO.select_power_sites(PCO.bga_lattice_sites(cut), cells, n, n,
                                 "nearest_symmetric")
    assert len(sel["supply"]) == n and len(sel["return"]) == n
    assert not (set(sel["supply"]) & set(sel["return"]))


# --- defect 2: R1 obstacle routing never charged a detour ----------------

def test_obstacle_router_detours_when_genuinely_blocked():
    """Capability test on a synthetic blocker. Without this, 'R1 == R0 on the
    real tile' could equally mean the router is broken."""
    a = RT.Comp("A", -0.8, 0.0, 0.0, 0.05, 0.05, "HS_RDL", "t")
    b = RT.Comp("B", 0.8, 0.6, 0.0, 0.05, 0.05, "HS_RDL", "t")
    wall = RT.Comp("BLOCK", 0.0, 0.30, 0.0, 2.0, 0.20, "HS_RDL", "test")
    base = RT.manhattan(a, b)
    assert RT.obstacle_manhattan(a, b, [a, b], "HS_RDL") == pytest.approx(base)
    blocked = RT.obstacle_manhattan(a, b, [a, b, wall], "HS_RDL")
    assert blocked > base, "the router cannot detour; R1 == R0 proves nothing"
    assert blocked != float("inf"), "an unroutable net must not poison the loss"


def test_a_terminal_is_not_blocked_by_what_it_sits_inside():
    """hs1_to_cf starts exactly on CF0's boundary. Counting that as an
    obstruction made the net look enclosed and returned infinity."""
    a = RT.Comp("A", 0.0, 0.0, 0.0, 0.05, 0.05, "PL2", "t")
    b = RT.Comp("B", 1.0, 0.0, 0.0, 0.05, 0.05, "PL2", "t")
    around = RT.Comp("AROUND", 0.0, 0.0, 0.0, 1.0, 1.0, "PL2", "t")
    L = RT.obstacle_manhattan(a, b, [a, b, around], "PL2")
    assert L == pytest.approx(RT.manhattan(a, b))


def test_a_self_net_has_no_manhattan_detour():
    a = RT.Comp("P", 0.0, 0.0, 0.0, 2.0, 2.0, "PL3", "plane")
    assert RT.obstacle_manhattan(a, a, [a], "PL3") == 0.0


def test_no_real_net_is_obstructed_so_R1_is_retired():
    """With the router fixed and capable (above), zero of the 16 physical nets
    detour. R1 is therefore retired as a fidelity level rather than having a
    difference manufactured for it. If this ever fails, a net HAS become
    obstructed and R1 must be reinstated and the phase document updated."""
    comps = RT.tile_layout(RT.DESIGN["tile_side_mm"])
    by = {c.name: c for c in comps}
    detoured = []
    for nt in RT.nets():
        a, b = by.get(nt.src), by.get(nt.dst)
        if a is None or b is None:
            continue
        if abs(RT.obstacle_manhattan(a, b, comps, nt.layer)
               - RT.manhattan(a, b)) > 1e-12:
            detoured.append(nt.name)
    assert not detoured, (
        "R1 now differs from R0 for %s -- reinstate R1 and update "
        "research/phase0nai/INTRA_VR_RESISTANCE_GRAPH.md" % detoured)


# --- generality: geometry must follow a spec, not a literal name ---------

def test_architecture_geometry_is_not_keyed_to_the_literal_strings():
    """A third architecture must be expressible without touching the solver."""
    import pkg_rdl_network as K
    assert K.architecture_cutout_mm("Z1") is None
    assert K.architecture_cutout_mm("Z2") == 23.36
    K.register_architecture("Z9_TEST", 10.0)
    try:
        cells = PCO.physical_cell_coordinates()
        sup9, _, where9 = K._supply_sites("Z9_TEST", cells, 16, 16)
        sup1, _, _ = K._supply_sites("Z1", cells, 16, 16)
        sup2, _, _ = K._supply_sites("Z2", cells, 16, 16)
        n9 = len(PCO.bga_lattice_sites(10.0))
        assert n9 == len(PCO.bga_lattice_sites()) - \
            sum(1 for x, y in PCO.bga_lattice_sites()
                if abs(x) < 5.0 and abs(y) < 5.0)
        # a genuinely different opening must give a genuinely different field
        assert set(sup9) != set(sup1) or set(sup9) != set(sup2)
        assert str(n9) in where9
    finally:
        K.ARCHITECTURE_CUTOUT_MM.pop("Z9_TEST", None)


def test_an_unknown_architecture_is_an_error_not_a_silent_Z1():
    import pkg_rdl_network as K
    with pytest.raises(KeyError, match="unknown architecture"):
        K.architecture_cutout_mm("Z2_typo")
