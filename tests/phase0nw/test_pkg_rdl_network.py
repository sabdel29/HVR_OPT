"""PHASE 0N-AF --- the package RDL 2-D network (brief 13, 14, 17, 19, 22, 23, 26)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0nw", "scripts/phase0m", "scripts/phase0mr", "scripts"):
    sys.path.insert(0, str(R / p))

import pkg_rdl_network as NET  # noqa: E402

ART = R / "research" / "phase0naf" / "pkg_rdl_network.json"


@pytest.fixture(scope="module")
def art():
    return json.loads(ART.read_text())


def test_a_continuous_conductor_now_joins_bga_to_the_cells():
    """The physical mesh had cell-local RDL and nothing linking it to the BGA ring."""
    c = NET.solve_case("Z2", 41, NET.T_CU_CASES["RDL_T2"], NET.OCCUPANCY_CASES["RDL_M"])
    assert c["n_sources"] == 16 and c["n_sinks"] == 49
    assert c["r_eff_ohm"] > 0 and c["v_drop_at_1A"] != 0


def test_sheet_resistance_is_electrical_not_the_thermal_tensor():
    r = NET.sheet_resistance_ohm_sq(5.0e-3, 0.30)
    import interconnect as IC
    assert r == pytest.approx(IC.RHO_CU_20C / (5.0e-6 * 0.30), rel=1e-12)
    src = (R / "scripts/phase0nw/pkg_rdl_network.py").read_text()
    assert "rdl_effective_tensor" not in src, "the thermal tensor must not set R_sq"


def test_resistance_scales_inversely_with_copper():
    thin = NET.solve_case("Z2", 41, 2.0e-3, 0.30)["r_eff_ohm"]
    thick = NET.solve_case("Z2", 41, 10.0e-3, 0.30)["r_eff_ohm"]
    assert thick == pytest.approx(thin / 5.0, rel=0.02)
    plane = NET.solve_case("Z2", 41, 5.0e-3, 0.80)["r_eff_ohm"]
    mesh = NET.solve_case("Z2", 41, 5.0e-3, 0.30)["r_eff_ohm"]
    assert mesh > plane


def test_z1_and_z2_have_architecturally_different_supply_paths(art):
    """Z2's 48 V must cross the 23.36 mm opening; Z1's need not."""
    k = "RDL_T2_RDL_M"
    z1 = art["architectures"]["Z1"]["cases"][k]
    z2 = art["architectures"]["Z2"]["cases"][k]
    assert "annulus" in z2["source_placement"]
    assert "no cutout" in z1["source_placement"]
    assert z2["r_eff_ohm"] > z1["r_eff_ohm"] * 3, (
        f"Z2 {z2['r_eff_ohm']*1e3:.3f} vs Z1 {z1['r_eff_ohm']*1e3:.3f} mOhm")


def test_losses_are_named_scenarios_scaled_from_one_linear_solve(art):
    for arch in ("Z1", "Z2"):
        a = art["architectures"][arch]
        for c in a["cases"].values():
            s = c["scenario_loss_w"]
            assert set(s) == {"HV_S0", "HV_S1", "HV_S2"}
            # P = I^2 R exactly, from the single normalized solve
            for k, i in a["scenarios_a"].items():
                assert s[k] == pytest.approx(i ** 2 * c["r_eff_ohm"], rel=1e-9)
            assert "bracket" not in json.dumps(c).lower()


def test_the_network_is_not_converged_and_says_so(art):
    """The 1 % threshold was declared before any result was read. It was not met.

    Reporting the failure is the point: a solver that is tuned until it passes its own
    test has not been converged, it has been argued with.
    """
    for arch in ("Z1", "Z2"):
        cv = art["architectures"][arch]["convergence"]
        assert cv["threshold"] == 0.01
        assert "before any result was inspected" in cv["threshold_declared"]
        assert cv["converged"] is False, (
            "if this now passes, the grid or the model changed -- re-read the numbers")
        assert cv["delta_r_eff"] > 0.01
        assert len(cv["levels"]) >= 3


def test_point_injection_singularity_is_handled_by_finite_contacts():
    """A point source in a 2-D sheet is log-singular and cannot converge at all."""
    src = (R / "scripts/phase0nw/pkg_rdl_network.py").read_text()
    assert "logarithmic singularity" in src
    net = NET.SheetNetwork(41, 1.0)
    assert len(net.footprint(0.0, 0.0, 2.3685)) > 1, "a cell pad must cover many nodes"


def test_rdl_construction_cases_are_declared_not_sourced(art):
    st = art["case_status"]
    assert "BOUNDED_FROM_LITERATURE" in st["t_cu"]
    assert "BOUNDED_ENGINEERING" in st["occupancy"]
    assert "not given by any source" in st["t_cu"]
