"""TCPMT round 3 -- mechanics and solder model revision (no solver runs; seconds).

Guards the pieces whose silent change would move every local number: the v2 submodel mesh
is the legacy joint mesh, the boundary conditions and the ramp are written as stated, the
laws are zero-yield and self-consistent, the face kinematics reproduce a linear field
exactly, the defaults of the shared mesh / deck writers are unchanged, and the tier-order
bookkeeping counts what the paper states.
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import numpy as np
import pytest

R = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/phase0i", "scripts/phase0mr3c"):
    sys.path.insert(0, str(R / p))

import tcpmt_mech_laws as LAW                                       # noqa: E402
import tcpmt_mech_submodel as SUB                                   # noqa: E402


def test_v2_mesh_is_the_legacy_joint_mesh():
    import importlib
    os.environ["JOINT_BAND_FRAC"] = repr(SUB.BAND_FRAC)
    import joint
    importlib.reload(joint)
    for n_xy, n_z in ((6, 8), (12, 16)):
        a = joint.build_joint(n_xy, n_z, 1)
        b = SUB.build_mesh(SUB.geometry("bga"), n_xy, n_z, 1)
        assert np.allclose(a.nodes, b.nodes, atol=1e-12)
        assert [(e, c, s) for e, c, s in a.elems] == [(e, c, s) for e, c, s in b.elems]
        for k in ("NBOT", "NTOP", "ESOLCORE"):
            assert sorted(a.sets[k]) == sorted(b.sets[k])


def _kin(du=(2e-3, 0.0, 4e-4), Gb=None, Gt=None, T=100.0):
    z = [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]
    return {"du_mm": list(du), "G_bot": Gb or z, "G_top": Gt or z, "T_bot_C": T,
            "T_top_C": T}


def test_global_bc_without_gradients_equals_uz_mode():
    m = SUB.build_mesh(SUB.geometry("bga"), 6, 8, 1)
    k = _kin()
    g, u = SUB.bc_values(m, k, "global"), SUB.bc_values(m, k, "uz")
    for n in m.sets["NTOP"] + m.sets["NBOT"]:
        assert np.allclose(g[n], u[n], atol=1e-15)
    leg = SUB.bc_values(m, k, "legacy")
    assert all(leg[n][2] == 0.0 for n in m.sets["NTOP"])      # legacy holds u_z = 0


def test_frame_puts_inplane_du_on_local_x():
    m = SUB.build_mesh(SUB.geometry("bga"), 6, 8, 1)
    d = 1e-3
    k = _kin(du=(-d, -d, 0.0))
    v = SUB.bc_values(m, k, "global")
    n = m.sets["NTOP"][0]
    assert math.isclose(v[n][0], math.hypot(d, d), rel_tol=1e-12) and abs(v[n][1]) < 1e-15


def test_global_bc_carries_the_face_gradients():
    m = SUB.build_mesh(SUB.geometry("bga"), 6, 8, 1)
    Gt = [[1e-3, 0.0], [0.0, 1e-3], [2e-3, 0.0]]              # stretch + tilt about y
    k = _kin(du=(1e-3, 0.0, 0.0), Gt=Gt)
    v = SUB.bc_values(m, k, "global")
    for n in m.sets["NTOP"]:
        x, y = m.nodes[n - 1, :2]
        assert math.isclose(v[n][0], 1e-3 + 1e-3 * x, rel_tol=1e-9, abs_tol=1e-15)
        assert math.isclose(v[n][2], 2e-3 * x, rel_tol=1e-9, abs_tol=1e-15)


def test_ramp_and_legacy_schedules(tmp_path):
    m = SUB.build_mesh(SUB.geometry("bga"), 6, 8, 1)
    segs, half = SUB.schedule(110.0, 2, 3.0, 300.0, 25.0)
    assert half == 303.0 and len(segs) == 8
    txt = SUB.write_deck(m, tmp_path / "r.inp", LAW.card("schubert2003")[0], segs,
                         SUB.bc_values(m, _kin(), "global"))
    steps = txt.split("*STEP")[1:]
    assert sum("AMPLITUDE=RAMP" in s.splitlines()[0] for s in steps) == 4
    assert all(("AMPLITUDE=RAMP" in s.splitlines()[0]) == (k % 2 == 0)
               for k, s in enumerate(steps))
    segs, half = SUB.schedule(110.0, 1, 0.0, 300.0, 25.0)
    txt = SUB.write_deck(m, tmp_path / "l.inp", LAW.legacy_card(), segs,
                         SUB.bc_values(m, _kin(), "legacy"))
    assert "AMPLITUDE" not in txt and "0.002, 3, 1e-09, 3" in txt and "0.5, 297, 1e-09, 15" in txt


def test_laws_are_zero_yield_and_fit_their_window():
    y0 = float(LAW.solder_cfg()["yield_zero_MPa"])
    win = {"hot": [8.0, 30.0], "cold": [15.0, 50.0]}
    for law in LAW.solder_cfg()["band_laws"]:
        text, rows = LAW.card(law, win)
        plast = text.split("*PLASTIC\n")[1].split("*CREEP")[0].strip().splitlines()
        assert all(float(l.split(",")[0]) == y0 for l in plast)
        assert len(rows) == len(LAW.rows_C())
    _t, rows = LAW.card("schubert2003", win)
    hot = [r for r in rows if r["T_C"] >= 75.0]
    assert max(r["max_rate_err_rel"] for r in hot) < 0.25


def test_measured_norton_reproduces_its_calibration_data():
    import solder_model as SM
    for T in SM.DATA_TEMPS:
        f = SM.fit_norton_data(T)
        for t, s, e in SM.CREEP_DATA:
            if t == T:
                r = float(LAW.rate("xa_measured_norton", s, T))
                assert abs(r / e - 1) <= f["max_rel_error_pct"] / 100 + 1e-9


def test_face_kinematics_reproduce_a_linear_field():
    import final_closure_physical_etm as E
    import tcpmt_mech_kinematics as KIN
    m, *_ = E.build("Z1", 1.1, (1, 1))
    a = np.array([1e-3, -2e-3, 5e-4])
    B = np.array([[1e-4, 2e-5], [-3e-5, 4e-4], [6e-4, -7e-4]])
    U = np.zeros((m.n_nodes + 1, 3))
    U[1:] = a + m.nodes[:, :2] @ B.T
    T = np.full(m.n_nodes, 80.0)
    k = KIN.site_kinematics(m, U, T, "bga", [(14.4, 14.4), (0.0, 0.8)], 0.2)
    for r in k:
        assert np.allclose(r["G_bot"], B, atol=1e-12) and np.allclose(r["G_top"], B, atol=1e-12)
        assert np.allclose(r["u_bot_mm"], a + B @ [r["x_mm"], r["y_mm"]], atol=1e-12)
        assert abs(r["du_xy_um"]) < 1e-9 and r["T_bot_C"] == pytest.approx(80.0)


def test_board_extent_default_is_the_coupon():
    import final_closure_physical_etm as E
    os.environ.pop("HVR_BOARD_EXTENT_FACTOR", None)
    m0, *_ = E.build("Z3", 1.1, (1, 1))
    os.environ["HVR_BOARD_EXTENT_FACTOR"] = "1"
    m1, *_ = E.build("Z3", 1.1, (1, 1))
    os.environ["HVR_BOARD_EXTENT_FACTOR"] = "2"
    m2, *_ = E.build("Z3", 1.1, (1, 1))
    os.environ.pop("HVR_BOARD_EXTENT_FACTOR")
    assert m0.n_elems == m1.n_elems and np.array_equal(m0.elems, m1.elems)
    assert m2.xs.max() == pytest.approx(30.0)
    keep = (m2.xs >= -15 - 1e-9) & (m2.xs <= 15 + 1e-9)
    assert np.allclose(m2.xs[keep], m0.xs)
    grown = {L for L in set(m2.elem_layer) if (m2.elem_layer == L).sum() != (m0.elem_layer == L).sum()}
    assert grown == {"board"}


def test_structural_deck_defaults_unchanged(tmp_path):
    import final_closure_physical_etm as E
    import production_et as PE
    m, mats, st, tiles, _ = E.build("Z1", 1.1, (1, 1))
    T = np.full(m.n_nodes, 60.0)
    PE.ccxio.write_structural(m, mats, T, st, "BC_BOARD", tmp_path / "a.inp", solver="")
    s = (tmp_path / "a.inp").read_text()
    assert "*DLOAD" not in s
    blk = s.split("*EXPANSION, ZERO=25.0\n")[1].split("\n")
    assert blk[1].startswith("*SOLID SECTION")                # one constant CTE line


def test_encapsulant_secant_cte():
    import tcpmt_mech_variants as MV
    v = LAW.cfg()["encapsulant"]["variants"]["encap_uf_tg"]
    E_T, sec = MV.encap_tables(v, 25.0, rows=[0.0, 60.0, 130.0, 250.0])
    s = dict(sec)
    assert s[60.0] == pytest.approx(v["alpha1_per_K"], rel=0.02)
    # the secant strain at 250 C is alpha1 to Tg plus alpha2 above it (sharp limit)
    sharp = v["alpha1_per_K"] * (130 - 25) + v["alpha2_per_K"] * (250 - 130)
    assert s[250.0] * (250 - 25) == pytest.approx(sharp, rel=0.03)
    assert dict(E_T)[250.0] < 0.1 * v["E_g_MPa"]


def test_tier_order_bookkeeping_counts():
    import repartition_search as RS
    n = {k: sum(1 for _ in RS.partitions(RS.COMPS, k)) for k in (2, 3, 4, 5)}
    assert n == {2: 30, 3: 150, 4: 240, 5: 120}
    passing = sum(1 for k in (2, 3, 4, 5) for t in RS.partitions(RS.COMPS, k)
                  if max(RS.geometry(t)[1]) <= RS.CELL_MM2 + 1e-9)
    assert passing == 144
    ref = [["gan_hs"], ["gan_ls"], ["cap_fly"], ["cap_out", "inductor"]]
    rep = [["gan_hs"], ["cap_fly"], ["gan_ls"], ["cap_out", "inductor"]]
    h = dict(RS.RP.H_UM, gan_ls=638.0)
    assert RS.net_levels(rep, "gan_hs", "cap_fly", "both", h) == []
    assert RS.net_levels(rep, "gan_hs", "cap_fly", "single", h) == [685.0]
    assert RS.net_levels(ref, "gan_hs", "cap_fly", "both", h) == [638.0]
