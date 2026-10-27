"""PHASE 0N-AI --- the package network must not dictate its own answer."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

R = Path(__file__).resolve().parents[2]
for _p in ("scripts/phase0nw", "scripts/phase0m", "scripts/phase0mr",
           "scripts/phase0e", "scripts/phase0dr", "scripts"):
    sys.path.insert(0, str(R / _p))
import pkg_rdl_network as K                                           # noqa: E402
import pad_interface as PI                                            # noqa: E402
import physical_coords as PCO                                         # noqa: E402

ART = R / "research" / "phase0nai" / "voltage_fed_network.json"
N_FAST = 151            # behavioural tests; the CONVERGED grid is much finer


@pytest.fixture(scope="module")
def art():
    if not ART.exists():
        pytest.skip("run scripts/phase0nai_voltage_fed_network.py first")
    return json.loads(ART.read_text())


@pytest.fixture(scope="module")
def cells():
    return PCO.physical_cell_coordinates()


@pytest.fixture(scope="module")
def net(cells):
    sel = PCO.select_power_sites(PCO.bga_lattice_sites(), cells, 16, 16,
                                 "nearest_symmetric")
    n = K.VoltageFedNetwork(N_FAST, K.sheet_resistance_ohm_sq(5.0e-3, 0.30))
    return n.build(sel["supply"], cells, PI.bga_ball_resistance_ohm(),
                   K.RHO_C_CASES["CONTACT_N"], K.RHO_C_CASES["CONTACT_N"],
                   PI.BGA_D_UM * 1e-3, K.VR_TILE_SIDE_MM)


# --- B.1 sharing is an OUTPUT -------------------------------------------

def test_ball_currents_are_unequal_even_under_a_uniform_load(net, cells):
    i = np.full(len(cells), 1.0 / len(cells))
    rep = net.report(net.solve(i), i)
    ib = np.asarray(rep["i_ball_a"])
    imposed = 1.0 / net.nb
    assert ib.std() / ib.mean() > 0.05, "sharing looks imposed, not solved"
    assert abs(ib.max() - imposed) / imposed > 0.10, (
        "the peak ball current is within 10 %% of the imposed value %g; the "
        "network is not deciding the split" % imposed)


def test_an_asymmetric_load_changes_the_split(net, cells):
    """I_BGA,1 != I_BGA,2, and the split MOVES when the load moves."""
    u = np.full(len(cells), 1.0 / len(cells))
    a = np.full(len(cells), 0.5 / (len(cells) - 1))
    a[int(np.argmax([x * x + y * y for x, y in cells]))] = 0.5
    iu = np.asarray(net.report(net.solve(u), u)["i_ball_a"])
    ia = np.asarray(net.report(net.solve(a), a)["i_ball_a"])
    assert iu[0] != iu[1]
    assert not np.allclose(iu, ia, rtol=1e-3), (
        "the ball split is insensitive to where the load sits")
    assert ia.max() / ia.mean() > iu.max() / iu.mean()


def test_the_imposed_model_CANNOT_pass_the_sharing_test():
    """Permanent negative test against the model this phase replaced.

    solve() divides i_total equally across sources in its right-hand side, so
    its per-source injection is exactly i_total/n whatever the load does. The
    guard above must be able to tell the two apart, or it proves nothing.
    """
    cells = PCO.physical_cell_coordinates()
    sel = PCO.select_power_sites(PCO.bga_lattice_sites(), cells, 16, 16,
                                 "nearest_symmetric")
    sheet = K.SheetNetwork(N_FAST, K.sheet_resistance_ohm_sq(5.0e-3, 0.30))
    src_groups = [sheet.footprint(x, y, 0.400) for x, y in sel["supply"]]
    injected = np.array([sum(1.0 / len(src_groups) / len(g) for _ in g)
                         for g in src_groups])
    assert np.allclose(injected, 1.0 / len(src_groups)), (
        "the historical model is being misquoted")
    assert injected.std() / injected.mean() < 1e-12, (
        "imposed injection is not uniform -- re-read solve()")


# --- B.4 the contact is finite and grid-independent ----------------------

@pytest.mark.parametrize("n", [41, 101, 201, 401])
@pytest.mark.parametrize("d", [0.400, 2.3685])
def test_overlap_areas_sum_to_the_physical_contact_area(n, d):
    sheet = K.SheetNetwork(n, 1.0)
    _, areas = K.contact_overlap(sheet, 1.234, -2.717, d)
    assert areas.sum() == pytest.approx(np.pi * (d / 2) ** 2, rel=1e-5)


def test_total_contact_conductance_does_not_drift_with_the_grid():
    g = []
    for n in (101, 201, 401):
        sheet = K.SheetNetwork(n, K.sheet_resistance_ohm_sq(5.0e-3, 0.30))
        _, gk, _ = K._contact_conductances(sheet, 0.0, 0.0, 0.400,
                                           K.RHO_C_CASES["CONTACT_N"])
        g.append(gk.sum())
    assert max(g) / min(g) - 1 < 1e-4


def test_the_withdrawn_spreading_correction_is_gone():
    """It was non-monotone in h and dominated the ball path; see the docstring."""
    src = (R / "scripts/phase0nw/pkg_rdl_network.py").read_text()
    assert "NO ANALYTIC SPREADING CORRECTION" in src
    sheet = K.SheetNetwork(201, K.sheet_resistance_ohm_sq(5.0e-3, 0.30))
    _, _, meta = K._contact_conductances(sheet, 0.0, 0.0, 0.400,
                                         K.RHO_C_CASES["CONTACT_N"])
    assert "r_spread_ohm" not in meta


# --- B.7 the identities actually close -----------------------------------

def test_energy_and_charge_identities(net, cells):
    i = np.full(len(cells), 1.0 / len(cells))
    rep = net.report(net.solve(i), i)
    assert rep["i_ball_sum_a"] == pytest.approx(rep["i_total_a"], abs=1e-10)
    assert rep["energy_residual_rel"] < 1e-9           # sum g dV^2 == sum V I
    assert rep["r_eff_ohm"] == pytest.approx(
        rep["p_loss_w"] / rep["i_total_a"] ** 2, rel=1e-12)


def test_loss_scales_as_current_squared(net, cells):
    base = np.full(len(cells), 1.0 / len(cells))
    p1 = net.report(net.solve(base), base)["p_loss_w"]
    p3 = net.report(net.solve(3 * base), 3 * base)["p_loss_w"]
    assert p3 / p1 == pytest.approx(9.0, rel=1e-9)


# --- B.2 the return conductor exists -------------------------------------

def test_supply_and_return_are_separate_solves_and_both_count(art):
    for arch in ("Z1", "Z2"):
        L = art["loop"][arch]
        assert L["r_return_ohm"] > 0.0
        assert L["r_loop_ohm"] == pytest.approx(
            L["r_supply_ohm"] + L["r_return_ohm"], rel=1e-12)
        # the return leg is not a rounding correction to the supply leg
        assert L["r_return_ohm"] / L["r_supply_ohm"] > 0.05


def test_return_sites_differ_from_supply_sites(cells):
    sel = PCO.select_power_sites(PCO.bga_lattice_sites(), cells, 16, 16,
                                 "nearest_symmetric")
    assert not (set(sel["supply"]) & set(sel["return"]))


# --- B.6 convergence, on every metric ------------------------------------

#: WHICH networks converge, pinned. Z1 fails and Z2 passes; see
#: research/phase0nai/z1_convergence_diagnostic.json. Pinned rather than
#: relaxed so that FIXING Z1 also fails this test and forces the documents to
#: be updated with it.
CONVERGED_NETWORKS = {"Z2_supply", "Z2_return"}
UNCONVERGED_NETWORKS = {"Z1_supply", "Z1_return"}


def test_convergence_is_declared_on_all_five_metrics(art):
    assert set(K.VF_CONV_METRICS) == {
        "r_eff_ohm", "p_loss_w", "max_cell_drop_v", "i_ball_max_a",
        "ball_imax_over_imean"}
    assert set(art["convergence"]) == CONVERGED_NETWORKS | UNCONVERGED_NETWORKS
    for key, c in art["convergence"].items():
        assert set(c["deltas"]) == set(K.VF_CONV_METRICS), key
        assert c["converged"] == (key in CONVERGED_NETWORKS), (
            key, c["worst_metric"], c["worst_delta"])


def test_no_Z1_result_is_presented_as_converged(art):
    """The threshold was declared before inspection and is NOT relaxed to let
    Z1 through. Z1 has now failed in three successive phases."""
    for key in UNCONVERGED_NETWORKS:
        assert art["convergence"][key]["worst_delta"] > K.VF_CONV_THRESH
    assert K.VF_CONV_THRESH == 0.01
    doc = (R / "research/phase0nai/PHASE_0NAI_NETWORK.md").read_text()
    assert "no Z1 loop resistance" in doc or "not reportable" in doc


def test_the_Z1_diagnostic_isolates_a_cause_and_admits_what_it_does_not(art):
    d = json.loads(
        (R / "research/phase0nai/z1_convergence_diagnostic.json").read_text())
    # Z2's cutout geometrically prevents the overlap; Z1's placement does not
    assert d["overlapping_balls_of_16"]["Z2"] == {"supply": 0, "return": 0}
    assert d["overlapping_balls_of_16"]["Z1"]["supply"] > 0
    assert d["overlapping_balls_of_16"]["Z1"]["return"] > 0
    # removing ONLY the overlapping sites must IMPROVE both rails
    for rail in ("supply", "return"):
        assert d["no_overlap"][f"Z1_{rail}"]["worst_delta"] < \
            d["baseline"][f"Z1_{rail}"]["worst_delta"], rail
    # the verdict wording must be DERIVED from the numbers, not asserted: an
    # earlier version hard-coded "crossing the 1 % threshold" and "still
    # failing", and after the lattice fix the two rails swapped roles and the
    # prose contradicted its own data.
    import pkg_rdl_network as _K
    for rail in ("supply", "return"):
        f = d["finding"][f"Z1_{rail}"]
        conv = d["no_overlap"][f"Z1_{rail}"]["converged"]
        delta = d["no_overlap"][f"Z1_{rail}"]["worst_delta"]
        assert conv == (delta < _K.VF_CONV_THRESH)
        assert ("CAUSE CONFIRMED" in f) == conv, (rail, f)
        if not conv:
            assert "does NOT reach" in f or "NOT A CAUSE" in f, f
    # whatever remains open must be named, not glossed
    assert "second_cause" in d["finding"]


def test_the_converged_grid_actually_resolves_the_ball(art):
    """h <= d/4 at the finest level. The old study stopped at h = 0.3 mm with a
    0.4 mm ball -- a sub-grid contact declared converged on R_eff alone."""
    for key, c in art["convergence"].items():
        assert c["levels"][-1]["min_ball_d_over_h"] >= 4.0, key
        assert c["levels"][-1]["min_ball_contact_nodes"] >= 8, key


def test_the_extra_metrics_actually_change_a_verdict(art):
    """R_eff alone was the old criterion. The five-metric set is justified only
    if some metric other than R_eff binds -- otherwise it is decoration.

    Concretely at HEAD: Z1_return drifts 0.849 % on r_eff_ohm (which would
    PASS) but 1.069 % on max_cell_drop_v (which FAILS). Checking R_eff alone
    would have declared that network converged.
    """
    thr = K.VF_CONV_THRESH
    # the worst metric is, by construction, at least as large as R_eff's
    for key, c in art["convergence"].items():
        assert c["worst_delta"] >= c["deltas"]["r_eff_ohm"] - 1e-15, key
    # some network must be decided by a metric other than R_eff
    non_reff = [k for k, c in art["convergence"].items()
                if c["worst_metric"] != "r_eff_ohm"]
    assert non_reff, (
        "every network's worst metric is R_eff again; if that is genuinely "
        "stable, re-justify carrying five metrics instead of one")
    # and at least one verdict must actually FLIP between the two criteria
    flipped = [k for k, c in art["convergence"].items()
               if c["deltas"]["r_eff_ohm"] < thr <= c["worst_delta"]]
    assert flipped, (
        "no network is passed by R_eff alone and failed by the full set, so "
        "the multi-metric criterion changed no verdict at HEAD -- re-justify "
        "it or record that it is now precautionary only")


# --- C the controls must be real controls --------------------------------

def test_inner_edge_is_withdrawn_not_silently_duplicated(cells):
    cand = PCO.bga_lattice_sites(23.36)
    with pytest.raises(NotImplementedError, match="alias of 'nearest_symmetric'"):
        PCO.select_power_sites(cand, cells, 16, 16, "inner_edge")
    a = PCO.select_power_sites(cand, cells, 16, 16, "nearest_symmetric")
    b = PCO.select_power_sites(cand, cells, 16, 16, "outer_perimeter")
    assert a["supply"] != b["supply"], "the two surviving rules must differ"


def test_cutout_and_placement_are_reported_separately(art):
    c = art["controlled"]
    assert c["includes_return"] and c["feed"] == "VOLTAGE_FED"
    assert set(c["cases"]) == {"CTRL_FULL", "CTRL_CUTOUT", "CTRL_CUTOUT_OUTER"}
    # the two cutout cases must differ ONLY in candidate count
    assert c["cases"]["CTRL_FULL"]["n_candidate_sites"] == 1369
    assert c["cases"]["CTRL_CUTOUT"]["n_candidate_sites"] == 528
    assert c["cases"]["CTRL_CUTOUT_OUTER"]["n_candidate_sites"] == 528
    assert c["delta_R_cutout_ohm"] != c["delta_R_placement_ohm"]


def test_artifact_matches_the_current_module_constants(art):
    m = art["meta"]
    assert m["resolved_grid"] == K.VF_RESOLVED_GRID
    assert m["conv_threshold"] == K.VF_CONV_THRESH
    assert list(m["conv_metrics"]) == list(K.VF_CONV_METRICS)
    assert m["r_ball_ohm"] == pytest.approx(PI.bga_ball_resistance_ohm())
    assert m["feed"] == "VOLTAGE_FED"


def test_rho_c_is_declared_as_ours_not_the_sources(art):
    assert "BOUNDED_ENGINEERING" in art["meta"]["rho_c_status"]
    assert "NO contact term" in art["meta"]["r_ball_provenance"]
    span = {r["contact_case"]: r["r_loop_ohm"]
            for r in art["contact_sensitivity"] if r["arch"] == "Z1"}
    assert len(span) == 3


# --- the cell contact is a SQUARE tile, not a disc of that width ---------

def test_square_tile_is_stamped_as_a_square():
    """Stamping the 2.3685 mm VR tile as a disc loses 21.5 % of its area --
    the same square-vs-circle slip already recorded for the Table III pad."""
    side = K.VR_TILE_SIDE_MM
    for n in (101, 301, 601):
        sheet = K.SheetNetwork(n, 1.0)
        _, sq = K.contact_overlap(sheet, 1.234, -2.717, side, "square")
        assert sq.sum() == pytest.approx(side ** 2, rel=1e-12)
        _, dk = K.contact_overlap(sheet, 1.234, -2.717, side, "disc")
        assert dk.sum() == pytest.approx(np.pi * (side / 2) ** 2, rel=1e-5)
        assert dk.sum() < 0.80 * sq.sum()      # the 21.5 % the disc would lose


def test_cells_use_the_square_stamp_and_balls_the_disc(net):
    assert all(m["shape"] == "square" for m in net.cell_meta)
    assert all(m["shape"] == "disc" for m in net.ball_meta)
    assert net.cell_meta[0]["a_contact_mm2"] == pytest.approx(
        K.VR_TILE_SIDE_MM ** 2, rel=1e-9)
    assert net.ball_meta[0]["a_contact_mm2"] == pytest.approx(
        PI.BGA_A_UM2 * 1e-6, rel=1e-4)


def test_unknown_contact_shape_is_rejected():
    with pytest.raises(ValueError, match="unknown contact shape"):
        K.contact_overlap(K.SheetNetwork(41, 1.0), 0.0, 0.0, 1.0, "hexagon")


# --- E: the electrical contact geometry must agree with the FE geometry ---

def test_cell_contact_matches_the_compiled_tile_and_fits_the_FE_pitch():
    """The electrical cell contact is the VR tile, and the tile must fit inside
    the FE placement pitch. If either moves independently the network would be
    stamping a footprint the mesh does not have."""
    import routing as RT                                    # the compiled design
    assert K.VR_TILE_SIDE_MM == pytest.approx(RT.DESIGN["tile_side_mm"], rel=1e-15)
    cells = PCO.physical_cell_coordinates()
    xs = sorted({round(x, 6) for x, _ in cells})
    pitch = min(b - a for a, b in zip(xs, xs[1:]))
    assert K.VR_TILE_SIDE_MM < pitch, (
        "the VR tile is wider than the cell pitch; tiles would overlap")
    # tiles must not touch: the stamped squares have to stay disjoint
    assert pitch - K.VR_TILE_SIDE_MM > 0.5
