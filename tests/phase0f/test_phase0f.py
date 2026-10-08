"""Phase-0F tests: geometry realizability, large-M placement, and 1-kW scaling."""
from __future__ import annotations
import csv, json, math, sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
for p in ("phase0b", "phase0d", "phase0e", "phase0f"):
    sys.path.insert(0, str(R / "scripts" / p))

import geometry as G
from placement0f import build as build0f, max_compaction, square_lattice
from metrics0f import relative_interface_displacement
from etm.placement import PlacementError

OUT = R / "results" / "phase0f"
DIE, KEEP, GAP = 22.36, 0.5, 0.5


class FakeInd:
    def __init__(self, h, name="ind", cat="silicon_interposer"):
        self.height_um, self.name, self.category = h, name, cat


class FakeDesign:
    def __init__(self, h_um=500.0):
        self.inductor = FakeInd(h_um)


# ------------------------------------------------------------------ geometry realizability
def test_cell_height_is_the_sum_of_its_layers():
    cs = G.cell_stack(FakeDesign(500.0), "nominal")
    assert cs.inductor_h_um == 500.0
    assert cs.t_cell_um == pytest.approx(500 + G.GAN_H_UM["nominal"] + G.MLCC_H_UM["nominal"]
                                         + 2 * G.INTERLAYER_RDL_H_UM)
    assert cs.h_sub_min_um == pytest.approx(cs.t_cell_um + G.H_TSV_MIN_UM)


def test_the_phase0b_to_0e_thicknesses_are_infeasible():
    """The whole reason Phase 0F exists: a 500 um inductor cannot live in a 200 um substrate."""
    d = FakeDesign(500.0)
    for h in (0.2, 0.5):
        r = G.check(d, h, "nominal")
        assert not r.feasible, f"h_sub={h} should be infeasible"
        assert "does not fit" in r.reason or "below the" in r.reason


def test_infeasibility_is_robust_to_the_open_heights():
    """GaN and MLCC heights are OPEN; they can only make things worse, never better."""
    d = FakeDesign(500.0)
    assert not G.check(d, 0.2, "optimistic").feasible
    assert not G.check(d, 0.2, "nominal").feasible
    assert not G.check(d, 0.2, "pessimistic").feasible


def test_realizable_range_starts_near_800_um():
    d = FakeDesign(500.0)
    assert not G.check(d, 0.75, "nominal").feasible
    assert G.check(d, 0.8, "nominal").feasible
    assert G.check(d, 1.5, "nominal").feasible


def test_tsv_length_is_what_is_left_over():
    r = G.check(FakeDesign(500.0), 1.5, "nominal")
    assert r.h_tsv_um == pytest.approx(1500.0 - r.t_cell_um)
    assert r.h_tsv_um >= G.H_TSV_MIN_UM


def test_taller_inductor_needs_a_thicker_substrate():
    a = G.cell_stack(FakeDesign(70.0), "nominal").h_sub_min_um
    b = G.cell_stack(FakeDesign(1560.0), "nominal").h_sub_min_um
    assert b - a == pytest.approx(1560.0 - 70.0)


def test_fitting_inductor_set_shrinks_as_the_substrate_thins():
    n15 = len(G.fitting_inductors(1.5, "nominal")[0])
    n08 = len(G.fitting_inductors(0.8, "nominal")[0])
    n02 = len(G.fitting_inductors(0.2, "nominal")[0])
    assert n15 >= n08 > n02 == 0


def test_no_inductor_fits_a_200_um_substrate_under_the_nominal_bound():
    fit, budget = G.fitting_inductors(0.2, "nominal")
    assert fit == [] and budget < 0


# --------------------------------------------------------------------- large-M placement
def test_lattice_respects_keepout_and_gap():
    tiles, meta = build0f("uniform", 49, 2.369, DIE, KEEP, GAP)
    assert len(tiles) == 49
    half = DIE / 2 - KEEP
    for t in tiles:
        assert abs(t.cx) + t.ax / 2 <= half + 1e-9
        assert abs(t.cy) + t.ay / 2 <= half + 1e-9


def test_compaction_headroom_falls_as_regulators_are_added():
    h16 = 1 - max_compaction(16, 3.873, DIE, KEEP, GAP)
    h36 = 1 - max_compaction(36, 2.683, DIE, KEEP, GAP)
    h49 = 1 - max_compaction(49, 2.369, DIE, KEEP, GAP)
    assert h16 > h36 > h49
    assert h49 < 0.12, "at 1 kW placement freedom should be nearly exhausted"


def test_compact_is_tighter_than_uniform():
    u, mu = build0f("uniform", 49, 2.369, DIE, KEEP, GAP)
    c, mc = build0f("compact", 49, 2.369, DIE, KEEP, GAP)
    ru = sum(math.hypot(t.cx, t.cy) for t in u) / len(u)
    rc = sum(math.hypot(t.cx, t.cy) for t in c) / len(c)
    assert rc < ru and mc["scale"] < mu["scale"]


def test_a_tile_too_big_to_place_raises():
    with pytest.raises(PlacementError):
        build0f("uniform", 49, 12.0, DIE, KEEP, GAP)


# --------------------------------------------------------------- non-breaking compile_hvr
def test_compile_hvr_without_a_library_is_unchanged():
    """Phase 0F added pass-through kwargs; omitting them must reproduce earlier phases."""
    from electrical import compile_hvr
    import inspect
    sig = inspect.signature(compile_hvr)
    assert sig.parameters["inductor_library"].default is None
    assert sig.parameters["capacitor_library"].default is None


# ------------------------------------------------------------------------- 1-kW results
@pytest.mark.skipif(not (OUT / "1kw_candidates.csv").exists(), reason="sweep not run")
def test_every_simulated_1kw_case_is_geometrically_realizable():
    for r in csv.DictReader(open(OUT / "1kw_candidates.csv")):
        if str(r.get("feasible")).lower() not in ("true", "1"):
            continue
        assert float(r["h_sub_mm"]) * 1e3 - float(r["t_tile_mm"]) * 1e3 >= G.H_TSV_MIN_UM - 1e-6


@pytest.mark.skipif(not (OUT / "1kw_candidates.csv").exists(), reason="sweep not run")
def test_energy_balance_holds_at_1kw():
    for r in csv.DictReader(open(OUT / "1kw_candidates.csv")):
        if str(r.get("feasible")).lower() not in ("true", "1"):
            continue
        assert abs(float(r["energy_residual_pct"])) <= 0.01


@pytest.mark.skipif(not (OUT / "1kw_candidates.csv").exists(), reason="sweep not run")
def test_archB_thickness_optimum_is_interior_and_archA_is_not():
    rows = [r for r in csv.DictReader(open(OUT / "thickness_crossover.csv"))]
    for arch, want_interior in (("ARCH_A", False), ("ARCH_B", True)):
        s = sorted([r for r in rows if r["arch"] == arch], key=lambda r: float(r["h_sub_mm"]))
        i = next(k for k, r in enumerate(s) if r["is_electrical_optimum"] == "True")
        assert (i != len(s) - 1) == want_interior, arch


@pytest.mark.skipif(not (OUT / "tsv_1kw_feasibility.csv").exists(), reason="not run")
def test_no_architecture_is_tsv_infeasible_at_1kA():
    rows = list(csv.DictReader(open(OUT / "tsv_1kw_feasibility.csv")))
    assert rows and all(str(r["feasible"]).lower() == "true" for r in rows)
    assert max(float(r["utilisation"]) for r in rows) < 1.0


@pytest.mark.skipif(not (OUT / "tsv_1kw_feasibility.csv").exists(), reason="not run")
def test_allocation_invariant_holds_at_1kw():
    for r in csv.DictReader(open(OUT / "tsv_1kw_feasibility.csv")):
        assert int(r["n_required"]) <= int(r["n_allocated"]) <= int(r["n_available"])


@pytest.mark.skipif(not (OUT / "cooling_1kw_calibration.json").exists(), reason="not run")
def test_1kw_cooling_is_not_the_phase0b_value():
    c = json.loads((OUT / "cooling_1kw_calibration.json").read_text())
    assert c["converged"] and abs(c["residual_K"]) < 0.5
    assert c["ratio_vs_phase0b"] > 5.0, "the 1-kW boundary must not be the Phase-0B one"


@pytest.mark.skipif(not (OUT / "bcb_metric_verdicts.csv").exists(), reason="not run")
def test_a_mounted_metric_was_qualified_before_use():
    v = list(csv.DictReader(open(OUT / "bcb_metric_verdicts.csv")))
    q = [r for r in v if r["QUALIFIED"] == "True"]
    assert q, "no mounted metric qualified"
    assert any(r["metric"] == "die_warpage_pv_um" for r in q)
    assert all(r["metric"] != "interface_peel_MPa" for r in v), "peel must stay excluded"


@pytest.mark.skipif(not (OUT / "bca_bcb_comparison.csv").exists(), reason="not run")
def test_thickness_reverses_between_assembly_states():
    rows = {(r["arch"], r["h_sub_mm"]): r for r in
            csv.DictReader(open(OUT / "bca_bcb_comparison.csv"))}
    a, b = rows.get(("ARCH_A", "0.800")), rows.get(("ARCH_A", "1.500"))
    assert a and b
    d_free = float(b["BCA_warpage_um"]) - float(a["BCA_warpage_um"])
    d_mount = float(b["BCB_warpage_um"]) - float(a["BCB_warpage_um"])
    assert d_free < 0 < d_mount, "free prefers thick, mounted prefers thin"


@pytest.mark.skipif(not (OUT / "mechanical_epsilon_sweep.csv").exists(), reason="not run")
def test_epsilon_sweep_is_monotone_and_labelled_parametric():
    rows = list(csv.DictReader(open(OUT / "mechanical_epsilon_sweep.csv")))
    n = [int(r["n_feasible"]) for r in rows]
    assert n == sorted(n), "admissible count must not fall as the limit is relaxed"
    assert any(r["et_optimum_admissible"] == "False" for r in rows)
    assert any(r["et_optimum_admissible"] == "True" for r in rows)


# ---------------------------------------------- Phase-0G defect #30: unit consistency
def test_vertical_tiers_are_system_wide_not_per_regulator():
    """Vertical tiers are evaluated per regulator; they must be scaled to the system before
    being summed with the system-wide RDL term. Phases 0D-R/0E/0F understated them by n_vr."""
    import math
    sys.path.insert(0, str(R / "scripts" / "phase0dr"))
    sys.path.insert(0, str(R / "scripts" / "phase0e"))
    from architecture0e import evaluate
    from stack import stacks_from_cfg
    import kw1
    from etm.config import load_stack, load_doe
    st, doe = load_stack(), load_doe()
    rdl = stacks_from_cfg()["ectc2024_primary"]
    side, t_cell, M = 2.369, 0.720, 49
    stt = kw1._stack_with_tile(st, t_cell)
    xy = kw1.tiles_for("uniform", side, stt, doe, M)
    e = evaluate("ARCH_B", xy, side, 1.5, 1000.0, 124.38, 84.17, rdl, t_tile_mm=t_cell)
    assert e["P_by_tier_w"]["tsv"] == pytest.approx(M * e["P_by_tier_per_vr_w"]["tsv"], rel=1e-9)
    # and the system TSV loss must match a first-principles calculation
    assert e["P_by_tier_w"]["tsv"] == pytest.approx(4.399, rel=0.02)
