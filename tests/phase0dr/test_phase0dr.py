"""Phase-0D-R tests. The 79 Phase-0B/0C/0D tests are preserved untouched."""
from __future__ import annotations

import copy, csv, json, math, sys
from pathlib import Path

import numpy as np
import pytest

R = Path(__file__).resolve().parents[2]
for p in ("phase0b", "phase0d", "phase0dr"):
    sys.path.insert(0, str(R / "scripts" / p))

import ppdn
from ppdn import (Infeasible, load_paths, n_available, n_required, rail_currents,
                  rdl_sheet_solve, r_single, tier_area_m2, vertical_segment)
from architecture import evaluate

_v = ppdn._v
P0DR = R / "results" / "phase0dr"
Q4 = [(-5.59, -5.59), (5.59, -5.59), (-5.59, 5.59), (5.59, 5.59)]


@pytest.fixture(scope="module")
def P():
    return load_paths()


# ------------------------------------------------------- architecture -> rail mapping
def test_every_segment_has_a_rail(P):
    for a in P["architectures"].values():
        for s in a["segments"]:
            assert s["rail"] in ("HV", "LV", "CONV"), s


def test_rail_flips_exactly_at_the_converter(P):
    """Before the converter every segment is HV; after it, every segment is LV."""
    for name, a in P["architectures"].items():
        seen_conv = False
        for s in a["segments"]:
            if s["tier"] == "converter":
                seen_conv = True
                continue
            assert s["rail"] == ("LV" if seen_conv else "HV"), f"{name}/{s['id']}"


def test_arch_a_tsv_is_hv_and_arch_b_is_lv(P):
    assert P["architectures"]["ARCH_A"]["tsv_rail"] == "HV"
    assert P["architectures"]["ARCH_B"]["tsv_rail"] == "LV"
    assert P["architectures"]["ARCH_C"]["tsv_rail"] == "HV"


def test_no_global_tsv_rail_assumption():
    """The two architectures must actually produce different TSV currents."""
    a = evaluate("ARCH_A", Q4, 4.899, 0.500, 240.0, 20.0, 75.0)
    b = evaluate("ARCH_B", Q4, 4.899, 0.500, 240.0, 20.0, 75.0)
    assert b["I_tsv_a"] > 40 * a["I_tsv_a"], (a["I_tsv_a"], b["I_tsv_a"])
    assert b["P_by_tier_w"]["tsv"] > 10 * a["P_by_tier_w"]["tsv"]


# ---------------------------------------------------------------- rail currents
def test_input_current_from_actual_converter_loss():
    rc = rail_currents(60.0, 48.0, 1.0, 5.0)
    assert rc["P_in_w"] == pytest.approx(65.0)
    assert rc["I_in_a"] == pytest.approx(65.0 / 48.0)
    assert rc["eta_stage"] == pytest.approx(60.0 / 65.0)


def test_ideal_conversion_is_not_assumed():
    lossy = rail_currents(60.0, 48.0, 1.0, 10.0)
    ideal = rail_currents(60.0, 48.0, 1.0, 0.0)
    assert lossy["I_in_a"] > ideal["I_in_a"]


def test_lv_current_far_exceeds_hv():
    rc = rail_currents(60.0, 48.0, 1.0, 5.0)
    assert rc["I_out_a"] / rc["I_in_a"] > 40


# ---------------------------------------------------------------- tier models
def test_june_table_iii_reproduced(P):
    t = P["tiers"]
    assert abs(r_single(t["bga"], 20.0) - 0.3e-3) / 0.3e-3 < 0.05
    assert abs(r_single(t["tsv"], 20.0, 300e-6) - 7.1e-3) / 7.1e-3 < 0.03
    assert abs(r_single(t["microbump"], 20.0) - 1.7e-3) / 1.7e-3 < 0.01


def test_microbump_is_square_not_circular(P):
    """June's 100 um^2 pad area is a SQUARE 10x10; circular would overstate R by 27%."""
    t = P["tiers"]["microbump"]
    assert t["shape"] == "square"
    assert tier_area_m2(t) == pytest.approx(100e-12, rel=1e-12)
    circ = math.pi * (10e-6) ** 2 / 4
    assert abs(100e-12 / circ - 1.273) < 0.01


def test_c4_is_not_a_microbump(P):
    t = P["tiers"]
    assert _v(t["c4"]["d_m"]) >= 10 * _v(t["microbump"]["d_m"])
    assert r_single(t["c4"], 20.0) != r_single(t["microbump"], 20.0)


def test_tier_resistance_rises_with_temperature(P):
    for name in ("bga", "tsv", "microbump", "c4"):
        t = P["tiers"][name]
        h = 300e-6 if name == "tsv" else None
        assert r_single(t, 125.0, h) > r_single(t, 20.0, h)


# ---------------------------------------------------------------- loop resistance
def test_ground_return_doubles_the_loop(P):
    s = vertical_segment("x", "tsv", P["tiers"]["tsv"], "LV", 1.0, 24.0, 25.0, 300e-6, "tsv")
    assert s.r_loop_ohm == pytest.approx(2.0 * s.r_supply_ohm)
    assert s.p_loss_w == pytest.approx(1.0 ** 2 * s.r_loop_ohm)


# ---------------------------------------------------------------- feasibility gate
def test_overload_raises_instead_of_clipping(P):
    t = copy.deepcopy(P["tiers"]["tsv"])
    t["i_max_a"]["value"] = 0.001
    with pytest.raises(Infeasible):
        vertical_segment("x", "tsv", t, "LV", 60.0, 1.0, 25.0, 300e-6, "tsv")


def test_arch_b_infeasible_at_conservative_via_limit():
    p = copy.deepcopy(load_paths())
    p["tiers"]["tsv"]["i_max_a"]["value"] = 0.0048
    b = evaluate("ARCH_B", Q4, 4.899, 0.500, 240.0, 20.0, 75.0, paths=p)
    assert b["feasible"] is False
    assert any("parallel conductors" in m for m in b["infeasible_reasons"])
    a = evaluate("ARCH_A", Q4, 4.899, 0.500, 240.0, 20.0, 75.0, paths=p)
    assert a["feasible"] is True, "the HV architecture must remain feasible"


def test_parallel_count_scales_with_current(P):
    t = P["tiers"]["tsv"]
    assert n_required(t, 0.033) == 1
    assert n_required(t, 0.66) == 20
    assert n_available(t, 24.0) > n_available(t, 1.0)


# ---------------------------------------------------------------- RDL sheet model
def test_rdl_loss_grows_with_source_load_distance(P):
    q = (np.arange(6) + 0.5) / 6 * 22.36 - 11.18
    load = [(x, y) for x in q for y in q]
    near = rdl_sheet_solve([(-5.59, -5.59), (5.59, -5.59), (-5.59, 5.59), (5.59, 5.59)],
                           [60.] * 4, load, [240 / 36] * 36, P["tiers"]["rdl"], 25.0,
                           22.36, n=61, src_size_mm=4.9, load_size_mm=22.36 / 6)
    far = rdl_sheet_solve([(-9.5, -9.5), (-9.5, -6.0), (-9.5, 6.0), (-9.5, 9.5)],
                          [60.] * 4, load, [240 / 36] * 36, P["tiers"]["rdl"], 25.0,
                          22.36, n=61, src_size_mm=4.9, load_size_mm=22.36 / 6)
    assert far["p_loop_w"] > 2 * near["p_loop_w"], (near["p_loop_w"], far["p_loop_w"])


def test_rdl_loss_inversely_proportional_to_thickness(P):
    q = (np.arange(6) + 0.5) / 6 * 22.36 - 11.18
    load = [(x, y) for x in q for y in q]
    out = {}
    for t_um in (5, 10, 20):
        t = copy.deepcopy(P["tiers"]["rdl"])
        t["t_cu_m"]["value"] = t_um * 1e-6
        out[t_um] = rdl_sheet_solve(Q4, [60.] * 4, load, [240 / 36] * 36, t, 25.0,
                                    22.36, n=61, src_size_mm=4.9, load_size_mm=22.36 / 6)["p_loop_w"]
    assert out[10] == pytest.approx(out[5] / 2, rel=1e-6)
    assert out[20] == pytest.approx(out[5] / 4, rel=1e-6)


def test_rdl_energy_balance_closes(P):
    q = (np.arange(6) + 0.5) / 6 * 22.36 - 11.18
    load = [(x, y) for x in q for y in q]
    r = rdl_sheet_solve(Q4, [60.] * 4, load, [240 / 36] * 36, P["tiers"]["rdl"], 25.0,
                        22.36, n=61, src_size_mm=4.9, load_size_mm=22.36 / 6)
    assert r["balance_err_pct"] < 1e-6


def test_rdl_matches_moose():
    p = P0DR / "rdl_validation.json"
    if not p.exists():
        pytest.skip("MOOSE validation not run")
    v = json.loads(p.read_text())
    assert v["analytic_strip_check"]["err_pct"] < 1e-6
    best = min(x["err_P_pct"] for x in v["fd_grid_study"].values())
    assert best < 1.0, f"FD vs MOOSE dissipation disagreement {best:.2f}%"


def test_finite_area_injection_beats_point_injection(P):
    """A point source in a 2-D sheet is logarithmically singular; a real VR is not."""
    q = (np.arange(6) + 0.5) / 6 * 22.36 - 11.18
    load = [(x, y) for x in q for y in q]
    pt = rdl_sheet_solve(Q4, [60.] * 4, load, [240 / 36] * 36, P["tiers"]["rdl"], 25.0,
                         22.36, n=61, src_size_mm=0.0, load_size_mm=22.36 / 6)
    ar = rdl_sheet_solve(Q4, [60.] * 4, load, [240 / 36] * 36, P["tiers"]["rdl"], 25.0,
                         22.36, n=61, src_size_mm=4.9, load_size_mm=22.36 / 6)
    assert pt["p_loop_w"] > 3 * ar["p_loop_w"]


# ---------------------------------------------------------------- loss decomposition
def test_losses_are_reported_per_tier_not_lumped():
    e = evaluate("ARCH_C", Q4, 4.899, 0.500, 240.0, 20.0, 75.0, lateral_route_mm=8.0)
    for tier in ("bga", "c4", "tsv", "microbump", "rdl"):
        assert tier in e["P_by_tier_w"], tier
    assert e["P_pdn_w"] == pytest.approx(sum(e["P_by_tier_w"].values()), rel=1e-9)


def test_total_electrical_is_converter_plus_pdn():
    e = evaluate("ARCH_A", Q4, 4.899, 0.500, 240.0, 20.0, 75.0)
    assert e["P_elec_total_w"] == pytest.approx(e["P_conv_w"] + e["P_pdn_w"], rel=1e-12)


def test_voltage_drop_reported_per_tier():
    e = evaluate("ARCH_A", Q4, 4.899, 0.500, 240.0, 20.0, 75.0)
    assert set(e["dV_by_tier_v"]) >= {"bga", "tsv", "microbump", "rdl"}
    assert e["dV_total_v"] == pytest.approx(sum(e["dV_by_tier_v"].values()), rel=1e-9)


# ---------------------------------------------------------------- coupled results
def test_corrected_energy_balance():
    p = P0DR / "coupled_candidates_corrected.csv"
    if not p.exists():
        pytest.skip("corrected sweep not run")
    for r in csv.DictReader(p.open()):
        assert abs(float(r["energy_residual_pct"])) < 0.01, r["case"]


def test_placement_is_not_electrically_free():
    """Phase 0D claimed a 1.08% electrical spread across placements. Test it is far larger."""
    p = P0DR / "coupled_candidates_corrected.csv"
    if not p.exists():
        pytest.skip("corrected sweep not run")
    rows = [r for r in csv.DictReader(p.open())
            if r["arch"] == "ARCH_A" and r["j"] == "2.0" and r["h_sub_mm"] == "0.5"]
    if len(rows) < 4:
        pytest.skip("placement re-audit incomplete")
    v = [float(r["P_elec_total_w"]) for r in rows]
    spread = (max(v) - min(v)) / min(v)
    assert spread > 0.5, f"electrical spread only {100*spread:.2f}%"


def test_phase0d_artifacts_preserved():
    for f in ("results/phase0d/PHASE0D_ET_TO_ETM_REVERSAL_GATE.md",
              "results/phase0d/coupled_candidates.csv",
              "results/phase0d/reversal_analysis.json",
              "results/phase0c/PHASE0C_DVPD_MECHANICAL_LEVER_GATE.md",
              "results/phase0b/PHASE0B_FIRST_MECHANICAL_GATE.md"):
        assert (R / f).exists(), f


def test_no_unresolved_peel_used():
    for f in P0DR.glob("*.csv"):
        cols = next(csv.reader(f.open()), [])
        assert not any("peel" in c.lower() for c in cols), f.name
