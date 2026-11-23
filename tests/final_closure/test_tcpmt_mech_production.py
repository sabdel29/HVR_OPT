"""TCPMT round 3: the mechanics revision in the production state (tcpmt_mech_production and the
campaign pieces that keep it from reading a stale field)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/campaign"):
    if str(R / p) not in sys.path:
        sys.path.insert(0, str(R / p))

import tcpmt_mech_production as MP                                   # noqa: E402


def test_labels_cover_the_compared_cases():
    labs = MP.labels("SDEC")
    assert labs == ["SDEC_A_Z1", "SDEC_A_Z2", "SDEC_A_Z3", "SDEC_B_Z1", "SDEC_B_Z2",
                    "SDEC_B_Z3"]
    assert MP.parse("SDEC_B_Z3") == ("SDEC", "B", "Z3")
    assert MP.parse("Z1_S0") is None                       # a round-2 field case


def test_kinematics_registry_knows_the_state_cases():
    import tcpmt_mech_kinematics as KIN
    assert KIN.is_state_case("SDEC_A_Z2") and not KIN.is_state_case("B_Z1")
    assert KIN.CASES["SDEC_A_Z2"][:2] == ("Z2", "HV_SDEC")


def _case(arch, terms):
    return {"arch": arch, "ledger_rows": [{"term": t, "model": m, "note": n}
                                          for t, m, n in terms]}


def test_input_guard_refuses_a_stale_z3_ball_count(monkeypatch):
    monkeypatch.setattr(MP, "z3_balls_per_rail", lambda: 500)
    stale = _case("Z3", [("P_BGA_1V_VDD", "rho h / A", "667 per rail by the 1.5 A/ball "
                                                       "ENGINEERING criterion")])
    fresh = _case("Z3", [("P_BGA_1V_VDD", "rho h / A", "500 per rail by the 2 A/ball rule")])
    assert "667" in MP.input_issue("Z3", stale)
    assert MP.input_issue("Z3", fresh) is None


def test_input_guard_follows_the_adopted_48v_count(monkeypatch):
    monkeypatch.setattr(MP, "z1_adopted_per_rail", lambda: 168)
    old = _case("Z1", [("P_pkg_RDL_HV_supply", "voltage-fed refined FV sheet, N=220/rail", "")])
    new = _case("Z1", [("P_pkg_RDL_HV_supply", "voltage-fed refined FV sheet, N=168/rail", "")])
    assert MP.input_issue("Z1", old) and MP.input_issue("Z1", new) is None
    monkeypatch.setattr(MP, "z1_adopted_per_rail", lambda: None)   # no re-closure yet
    assert MP.input_issue("Z1", old) is None


def test_monotonicity_counts_dominated_sites_that_respond_more():
    import tcpmt_mech_critical as CR
    rows = [{"x_mm": 0, "y_mm": 0, "du_xy_um": 2.0, "T_C": 100.0, "d_eps": 5.0},
            {"x_mm": 1, "y_mm": 0, "du_xy_um": 1.0, "T_C": 90.0, "d_eps": 6.0},   # violation
            {"x_mm": 2, "y_mm": 0, "du_xy_um": 1.5, "T_C": 110.0, "d_eps": 4.0}]
    m = CR.monotonicity(rows)
    # sites 0 and 2 each dominate site 1, which responds more than both
    assert m["n_ordered_pairs"] == 2 and m["n_violations"] == 2
    assert abs(m["worst_violation"]["excess_rel"] - 0.5) < 1e-12
    assert m["n_pareto_solved"] == 2 and m["max_response_on_pareto_front"] is False


def test_larger_board_field_keeps_the_package_grid():
    import numpy as np
    import tcpmt_mech_board as B

    class M:
        def __init__(self, xs):
            self.nodes = np.array([(x, y, z) for x in xs for y in xs for z in (0.0, 1.0)])
            self.n_nodes = len(self.nodes)
    small = M([-1.0, 0.0, 1.0])
    big = M([-3.0, -1.0, 0.0, 1.0, 3.0])
    T = np.arange(small.n_nodes, dtype=float)
    hot, n = B.map_field_to_large(small, T, big, 2.0, 2.0, 25.0, "hot")
    cold, _ = B.map_field_to_large(small, T, big, 2.0, 2.0, 25.0, "cold")
    idx = {tuple(p): i for i, p in enumerate(small.nodes)}
    for i, p in enumerate(big.nodes):
        q = (min(max(p[0], -1.0), 1.0), min(max(p[1], -1.0), 1.0), p[2])
        assert hot[i] == T[idx[q]]
        if tuple(p) not in idx:
            assert cold[i] == 25.0
    assert n == big.n_nodes - small.n_nodes


def test_fresh_validator_detects_a_rewritten_input(tmp_path):
    import validators as V
    inp = tmp_path / "case.json"
    inp.write_text("{}")
    rec = tmp_path / "rec.json"
    rec.write_text(json.dumps({"inputs_sha1": MP.inputs_sha1([inp])}))
    assert V.check(rec, {"kind": "json", "fresh": True})[0]
    inp.write_text('{"rerun": 1}')
    ok, why = V.check(rec, {"kind": "json", "fresh": True})
    assert not ok and "stale" in why


def test_strict_deps_never_marks_a_dependency_valid(tmp_path):
    import run as RUN

    class Led:
        def event(self, *a, **k):
            raise AssertionError("strict mode must not write the ledger")

    class Camp:
        jobs = {"dep": {"id": "dep", "deps": [], "outputs": []}}
    st = {}
    assert RUN.dep_state(Camp(), Led(), st, set(), "dep", strict=True) == "wait"
    assert st == {}
    st = {"dep": {"status": "done"}}
    assert RUN.dep_state(Camp(), Led(), st, set(), "dep", strict=True) == "ok"


def test_a_stale_status_file_is_not_this_launchs_outcome():
    import run as RUN
    r = {"backend": "pbs", "pbs_id": "16188.pioneer.xray.aps.anl.gov"}
    assert RUN.status_of_launch(r, {"pbs_jobid": "16188.pioneer.xray.aps.anl.gov",
                                    "status": "done"})
    assert not RUN.status_of_launch(r, {"pbs_jobid": "15710.pioneer", "status": "done"})
    assert not RUN.status_of_launch(r, {"status": "done"})        # a previous local run's
    assert RUN.status_of_launch({"backend": "local", "pid": 42}, {"pid": 42})
    assert not RUN.status_of_launch({"backend": "local", "pid": 42}, {"pid": 7})


def _site(x, dudef, duz, T):
    """A lattice site with the three screening features (T on both faces)."""
    return {"x_mm": float(x), "y_mm": 0.0, "du_def_xy_um": dudef, "du_z_um": duz,
            "T_bot_C": T, "T_top_C": T, "du_xy_um": dudef}


def test_lattice_front_keeps_only_undominated_sites():
    import tcpmt_mech_critical as CR
    lat = [_site(0, 3.0, 1.0, 90.0), _site(1, 2.0, 0.5, 80.0),     # 1 dominated by 0
           _site(2, 1.0, -2.0, 85.0), _site(3, 1.0, 0.1, 100.0)]  # |du_z| counts
    fr = {k["x_mm"] for k in CR.lattice_front(lat)}
    assert fr == {0.0, 2.0, 3.0}


def test_screen_bounds_dominated_sites_and_asks_for_the_rest():
    import tcpmt_mech_critical as CR
    lat = [_site(0, 3.0, 1.0, 90.0), _site(1, 2.0, 0.5, 80.0), _site(2, 1.0, 0.2, 70.0),
           _site(3, 0.5, 2.0, 95.0)]
    f = {CR.key(k): CR.feat(k) for k in lat}
    # site 0 (the maximum) and site 1 solved; site 2 is dominated by site 1 (bound 1.1 x 4 =
    # 4.4 < 5: excluded); site 3 is dominated by no solved site: it must be solved
    solved = {CR.key(lat[0]): (f[CR.key(lat[0])], 5.0), CR.key(lat[1]): (f[CR.key(lat[1])], 4.0)}
    sc = CR.screen(lat, solved, 0.10)
    assert [k["x_mm"] for k in sc["need"]] == [3.0] and sc["n_unbounded"] == 1
    # with site 3 solved low, nothing is left; a margin that lifts site 1's bound over the
    # maximum (1.3 x 4 = 5.2 > 5) asks for site 2
    solved[CR.key(lat[3])] = (f[CR.key(lat[3])], 1.0)
    assert CR.screen(lat, solved, 0.10)["need"] == []
    assert [k["x_mm"] for k in CR.screen(lat, solved, 0.30)["need"]] == [2.0]
    del solved[CR.key(lat[1])]
    sc = CR.screen(lat, solved, 0.30)          # site 1 and 2: dominated by site 0 only
    assert sorted(k["x_mm"] for k in sc["need"]) == [1.0, 2.0]


def test_margin_is_twice_the_largest_reversal_but_at_least_the_floor(monkeypatch):
    import tcpmt_mech_critical as CR
    monkeypatch.setattr(CR, "ccfg", lambda: {"margin_min_rel": 0.10, "margin_factor": 2.0})
    rows = [{"x_mm": 0, "y_mm": 0, "du_def_xy_um": 2.0, "du_z_um": 1.0, "T_C": 90.0,
             "d_eps": 5.0},
            {"x_mm": 1, "y_mm": 0, "du_def_xy_um": 1.0, "du_z_um": 0.5, "T_C": 80.0,
             "d_eps": 5.4}]                                        # an 8 % reversal
    m, w = CR.margin_of(rows)
    assert abs(w - 0.08) < 1e-12 and abs(m - 0.16) < 1e-12
    rows[1]["d_eps"] = 4.0
    assert CR.margin_of(rows) == (0.10, 0.0)
