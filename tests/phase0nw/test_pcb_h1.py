"""PHASE 0N-W --- PCB-H1 reduced multilayer board (brief section 7)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0nw", "scripts"):
    sys.path.insert(0, str(R / p))

import pcb_h1 as H1  # noqa: E402

NOM = json.loads((R / "research/phase0nv/pcb_homogenization.json").read_text())["nominal_tensor"]


def test_blocks_reproduce_the_published_layer_schedule():
    b = H1.blocks()
    assert sum(x["n_layers"] for x in b) == 18
    assert sum(x["copper_oz"] for x in b) == pytest.approx(22.0)   # 14x1oz + 4x2oz
    assert sum(x["t_mm"] for x in b) == pytest.approx(2.4, abs=1e-9)


def test_h1_is_a_refinement_of_h0_not_a_different_board():
    """1-D consistency: five blocks in series must reproduce H0's k_z, and in parallel
    its k_xy. If they did not, any H0/H1 difference would be the reduction's own error
    rather than a spreading effect.

    k_xy is exact (Voigt is linear). k_z agrees only to ~8e-7 because k_lam_z is a
    BRACKET whose midpoint H0 takes once globally and H1 takes per block, and Reuss is
    non-linear. The tolerance below is set to that known, explained residual -- not
    loosened until the test passed.
    """
    s = H1.summary()
    assert s["k_xy_rel_diff"] < 1e-12, f"parallel k_xy differs by {s['k_xy_rel_diff']:.2e}"
    assert s["k_z_rel_diff"] < 1e-5, f"series k_z differs from H0 by {s['k_z_rel_diff']:.2e}"
    assert s["k_z_rel_diff"] > 0.0, (
        "an exactly-zero k_z difference would mean the bracket reduction changed; "
        "re-derive before relaxing this")


def test_the_central_plane_block_is_the_copper_rich_one():
    b = {x["name"]: x for x in H1.blocks()}
    c = b["b3_central_planes"]
    others = [v for k, v in b.items() if k != "b3_central_planes"]
    assert all(c["f_cu"] > o["f_cu"] * 1.5 for o in others), (
        "the 4 x 2 oz plane block must be distinctly copper-rich")
    assert all(c["k_xy"] > o["k_xy"] for o in others)
    assert all(c["E_MPa"] > o["E_MPa"] for o in others)


def test_the_four_non_plane_blocks_are_compositionally_identical():
    """This board's schedule is uniform 1 oz outside the central planes. H1 must not be
    described as resolving a rich alternating structure that the schedule does not have."""
    b = [x for x in H1.blocks() if x["name"] != "b3_central_planes"]
    assert len({round(x["f_cu"], 12) for x in b}) == 1
    src = (R / "scripts/phase0nw/pcb_h1.py").read_text()
    assert "does not have one" in src, (
        "the module must state that the published schedule has no rich alternation")


def test_blocks_respond_to_the_coverage_sweep():
    lo, hi = H1.summary(eta=0.25), H1.summary(eta=0.75)
    b_lo = {x["name"]: x for x in lo["blocks"]}["b3_central_planes"]
    b_hi = {x["name"]: x for x in hi["blocks"]}["b3_central_planes"]
    assert b_hi["f_cu"] > b_lo["f_cu"] and b_hi["k_xy"] > b_lo["k_xy"]


@pytest.mark.parametrize("eta", [0.25, 0.50, 0.75])
def test_h1_stays_consistent_with_h0_across_the_sweep(eta):
    """The refinement property must not hold only at the nominal coverage."""
    import pcb_h1
    bs = pcb_h1.blocks(eta=eta)
    t = sum(b["t_mm"] for b in bs)
    kz = t / sum(b["t_mm"] / b["k_z"] for b in bs)
    sweep = json.loads((R / "research/phase0nv/pcb_homogenization.json").read_text())["sweep"]
    row = next(r for r in sweep if abs(r["eta"] - eta) < 1e-12)
    h0_kz = 0.5 * (row["k_z_bounds"][0] + row["k_z_bounds"][1])
    assert abs(kz - h0_kz) / h0_kz < 1e-5, f"eta={eta}: H1 {kz:.6f} vs H0 {h0_kz:.6f}"


def test_board_materials_carry_orthotropic_conductivity():
    mats = H1.board_materials()
    assert len(mats) == 5
    for name, m in mats.items():
        kx, ky, kz = m["k_ortho"]["value"]
        assert kx == ky and kx > kz * 50, f"{name} lost its anisotropy"


def test_bottom_layers_are_deepest_first_and_sum_to_the_board():
    ls = H1.bottom_layers()
    assert ls[0][0].endswith("b5_outer_bot"), "the stack must start at the PCB backside"
    assert sum(t for _n, t, _m, _z in ls) == pytest.approx(2.4, abs=1e-9)


def test_h1_thermal_validation_has_not_been_run():
    """The MODEL exists; the H0-vs-H1 solve does not. The gate must stay open."""
    g = json.loads((R / "research/phase0nw/physical_gates.json").read_text())
    row = next(r for r in g["gates"] if r["gate"] == "PCB-H1 thermal validation")
    assert row["status"] == "OPEN", (
        "do not close the H1 gate until an actual H0-vs-H1 thermal comparison exists")
