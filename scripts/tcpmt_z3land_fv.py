"""Z3 1 V spreading shape factors for the coupled ledger (TCPMT revision).

The Z3 ledger records two lateral 1 V spreading conductors as NOT_MODELLED zero rows
(final_closure_ledger.z3_rows). Both are 2-D sheet problems of the same form,

    div( (1/R_s) grad V ) = -(injection - sink),       R_s = rho_Cu(T) / (t_Cu occupancy),

so on a fixed geometry the loss of one rail is P = kappa I^2 R_s and its static spread is
dV = kappa_V I R_s, with dimensionless shape factors kappa, kappa_V that do not depend on
t_Cu, T or I. This module supplies both pairs.

LAND SIDE (P_sub_land_1V_spreading). kappa is DERIVED from the committed finite-volume
result (scripts/tcpmt_z3_landside_estimate.py -> research/tcpmt_revision/
z3_landside_spreading.json) at its solved point: kappa = P_one_rail / (I^2 R_s),
kappa_V = dV_one_rail / (I R_s). The solver below re-solves that problem only to check that
it reproduces the committed numbers and to split the loss between the cell footprints and
the rest of the substrate (the coupled run deposits it uniformly over the whole land side).

BOARD PLANES (P_PCB_plane_1V_spreading). The same FV approach on the board's 1 V planes:
the current enters each plane at the plated through-holes of the via-in-pad field under
every cell (the 5 x 5 legal attach lattice of configs/phase0nz, VDD/GND checkerboard: 13 VDD
and 12 GND vias per cell, each a disk of the drilled diameter) and leaves at the rail's BGA
balls -- the same balls (the design record's count per rail on the 0.8 mm checkerboard,
nearest the cell footprints) and EQUAL sharing as the land-side estimate and the ledger's BGA
rows. DECLARED board allocation (not in the Z3 design record, stated here):
2 planes x 35 um (1 oz) Cu per rail at 80 % occupancy, i.e. four of the fourteen 1-oz layers
of the framework's 18-layer schedule (pcb_h1: 14 x 1 oz + 4 x 2 oz). The loss scales as
1 / (copper per rail): giving the 1 V rails the four 2-oz central planes instead halves it.

    python tcpmt_z3land_fv.py   -> research/tcpmt_revision/z3_board_plane_spreading.json
"""
from __future__ import annotations

import json
import os
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

R = Path(__file__).resolve().parents[1]
for _p in ("scripts/phase0nw", "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))
import tcpmt_z3_landside_estimate as LS                              # noqa: E402

LAND_JSON = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision" / "z3_landside_spreading.json"
OUT = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision" / "z3_board_plane_spreading.json"

#: land-side plane occupancy -- the value the committed FV result was solved at
LAND_OCC = LS.OCC
#: DECLARED board 1 V plane allocation (see the module docstring)
BOARD_PLANES_PER_RAIL = 2
BOARD_T_PLANE_UM = 35.0
BOARD_OCC = 0.80
BOARD_T_PER_RAIL_UM = BOARD_PLANES_PER_RAIL * BOARD_T_PLANE_UM
#: the shape factors used in the coupled ledger come from the committed grid (0.1 mm)
GRID_MM = LS.H_MM
GRID_CHECK_MM = 0.05


# ------------------------------------------------------------------ land side (committed)
@lru_cache(maxsize=1)
def land_shape():
    """kappa and kappa_V of ONE land-side rail, from the committed FV result at its solved
    points. The problem is linear in R_s and I, so every solved thickness must give the same
    pair; refused if they do not."""
    j = json.loads(LAND_JSON.read_text())
    i_a = float(j["I_rail_A"])
    ks, kv = [], []
    for c in j["cases"]:
        r_s = c["R_s_mohm_sq"] * 1e-3
        ks.append(c["P_one_rail_w"] / (i_a ** 2 * r_s))
        kv.append(c["dV_one_rail_mV"] * 1e-3 / (i_a * r_s))
    for v in (ks, kv):
        if max(v) - min(v) > 1e-9 * max(v):
            raise RuntimeError(f"land-side shape factor differs between solved points: {v}")
    c10 = min(j["cases"], key=lambda c: c["t_cu_um"])
    return {"kappa_one_rail": float(np.mean(ks)), "kappa_V_one_rail": float(np.mean(kv)),
            "source": (LAND_JSON.relative_to(R).as_posix() if LAND_JSON.is_relative_to(R) else LAND_JSON.as_posix()),
            "solved_point": {"t_cu_um": c10["t_cu_um"], "T_C": j["T_C"],
                             "occupancy": j["occupancy"], "I_rail_A": i_a,
                             "R_s_mohm_sq": c10["R_s_mohm_sq"],
                             "P_one_rail_w": c10["P_one_rail_w"],
                             "dV_one_rail_mV": c10["dV_one_rail_mV"]},
            "grid_mm": j["grid_mm"], "occupancy": j["occupancy"],
            "balls_per_rail": j["balls_per_rail"],
            "balls_inside_footprints": j["balls_inside_footprints"],
            "P_two_rails_x_t_W_um_at_solved_point": 2 * c10["P_one_rail_w"] * c10["t_cu_um"],
            "dV_one_rail_x_t_mV_um_at_solved_point": c10["dV_one_rail_mV"] * c10["t_cu_um"]}


# ------------------------------------------------------------------ FV machinery
def grid(h_mm):
    n = int(round(LS.L_MM / h_mm))
    return n, -LS.L_MM / 2 + h_mm * (np.arange(n) + 0.5)


def ball_sites(rail):
    """The rail's 1 V balls: exactly the set tcpmt_z3_landside_estimate.sources uses
    (power_ball_sites: the design record's n_per_rail of the rail's checkerboard sites,
    nearest the cell footprints; review round 3: 500 per rail at the 2-A target)."""
    return LS.power_ball_sites(rail)


def cell_centres():
    c = (np.arange(LS.N_CELL) - (LS.N_CELL - 1) / 2) * LS.CELL_PITCH
    return [(x, y) for x in c for y in c]


def footprint_mask(n, xc):
    mask = np.zeros((n, n), bool)
    for cx, cy in cell_centres():
        mask |= np.outer(np.abs(xc - cx) <= LS.CELL_SIDE / 2, np.abs(xc - cy) <= LS.CELL_SIDE / 2)
    return mask


def point_into(q, xc, x, y, amps):
    """One ball: its current into the single grid cell that holds it (the land-side rule)."""
    q[np.searchsorted(xc, x - 1e-9), np.searchsorted(xc, y - 1e-9)] += amps


@lru_cache(maxsize=1)
def via_lattice():
    """The PCB via-in-pad field of ONE cell from the Z3 config: one plated through-hole
    under every legal attach bump (z3_package.via_field / attach_lattice)."""
    import physical_package as PPK
    import z3_package as Z3P
    cfg = PPK.load_z3_package_config()
    lat = Z3P.attach_lattice(cfg)
    vf = Z3P.via_field(cfg)
    xs, ys = np.meshgrid(lat["x_um"] * 1e-3, lat["y_um"] * 1e-3, indexing="ij")
    return {"x_mm": xs.ravel(), "y_mm": ys.ravel(), "vdd": lat["vdd_mask"].ravel(),
            "r_mm": vf["d_drill_um"] / 2e3, "n_vdd": vf["n_vdd"], "n_gnd": vf["n_gnd"],
            "pitch_um": vf["pitch_um"], "d_drill_um": vf["d_drill_um"]}


def disk_into(q, xc, x, y, r, amps):
    """One via: its current spread evenly over the grid cells whose centres lie inside its
    drilled disk (the nearest cell if none does)."""
    ix = np.flatnonzero(np.abs(xc - x) <= r + 1e-12)
    iy = np.flatnonzero(np.abs(xc - y) <= r + 1e-12)
    cells = [(i, j) for i in ix for j in iy if (xc[i] - x) ** 2 + (xc[j] - y) ** 2 <= r * r]
    if not cells:
        cells = [(int(np.argmin(np.abs(xc - x))), int(np.argmin(np.abs(xc - y))))]
    for i, j in cells:
        q[i, j] += amps / len(cells)
    return len(cells)


def land_sources(n, xc, rail="VDD", i_a=1.0, with_balls=True):
    """The committed land-side problem: equal ball injection, uniform footprint sink
    (with_balls=False: the footprint sink alone, for the network check)."""
    q = np.zeros((n, n))
    balls = ball_sites(rail)
    if with_balls:
        for x, y in balls:
            point_into(q, xc, x, y, i_a / len(balls))
    mask = footprint_mask(n, xc)
    q[mask] -= i_a / mask.sum()
    return q


def board_sources(n, xc, rail="VDD", i_a=1.0, with_balls=True):
    """Board planes: injection at the rail's vias under every cell, equal sink at its balls
    (with_balls=False: the via injection alone, for the network check)."""
    q = np.zeros((n, n))
    vl = via_lattice()
    sel = vl["vdd"] if rail == "VDD" else ~vl["vdd"]
    vias = [(cx + x, cy + y) for cx, cy in cell_centres()
            for x, y in zip(vl["x_mm"][sel], vl["y_mm"][sel])]
    ncell = [disk_into(q, xc, x, y, vl["r_mm"], i_a / len(vias)) for x, y in vias]
    balls = ball_sites(rail)
    if with_balls:
        for x, y in balls:
            point_into(q, xc, x, y, -i_a / len(balls))
    return q, {"n_vias": len(vias), "n_balls": len(balls),
               "grid_cells_per_via": [int(min(ncell)), int(max(ncell))]}


def solve(q, r_s=1.0):
    """tcpmt_z3_landside_estimate.solve, returning the potential as well: square cells
    (face conductance 1/R_s), Neumann edges, node 0 pinned (the net source is zero)."""
    n = q.shape[0]
    g = 1.0 / r_s
    d1 = np.full(n, 2.0)
    d1[0] = d1[-1] = 1.0
    L1 = sp.diags([d1, -np.ones(n - 1), -np.ones(n - 1)], [0, -1, 1], format="csr")
    eye = sp.identity(n, format="csr")
    A = (g * (sp.kron(L1, eye) + sp.kron(eye, L1))).tolil()
    A[0, :] = 0
    A[0, 0] = 1.0
    rhs = q.ravel().copy()
    rhs[0] = 0.0
    v = spla.spsolve(A.tocsc(), rhs).reshape(n, n)
    fx, fy = g * np.diff(v, axis=0) ** 2, g * np.diff(v, axis=1) ** 2
    cell = np.zeros((n, n))                    # each face's loss split between its two cells
    cell[:-1, :] += fx / 2
    cell[1:, :] += fx / 2
    cell[:, :-1] += fy / 2
    cell[:, 1:] += fy / 2
    return float(fx.sum() + fy.sum()), float(v.max() - v.min()), cell, v


def shape(problem, rail, h_mm):
    """kappa, kappa_V of one rail at R_s = 1 Ohm/sq, I = 1 A, and the loss share inside the
    cell footprints of the design in force."""
    n, xc = grid(h_mm)
    extra = {}
    if problem == "land":
        q = land_sources(n, xc, rail)
    else:
        q, extra = board_sources(n, xc, rail)
    if abs(q.sum()) > 1e-9:
        raise RuntimeError(f"net source {q.sum()} A is not zero")
    p, dv, cell, _v = solve(q)
    mask = footprint_mask(n, xc)
    return {"kappa": p, "kappa_V": dv, "loss_fraction_in_footprints": float(cell[mask].sum() / p),
            "area_fraction_footprints": float(mask.mean()), "grid_mm": h_mm, **extra}


def network_check(t_land_um=(10.0, 20.0, 40.0, 100.0), t_land_c=79.0, t_board_c=72.0,
                  t_bga_c=78.0, h_mm=GRID_MM):
    """CONTEXT for the equal-sharing assumption, not used in the ledger. Both FV terms, like
    the ledger's BGA rows, prescribe EQUAL ball currents. Solved instead as one network --
    the board plane and the land-side plane coupled through each ball's resistance, the via
    field injecting and the TSV footprints drawing -- the current divides by Kirchhoff, which
    by Thomson's principle dissipates the least of all divisions: the equal-sharing sum
    (board plane + BGA + land side) is an upper bound on it, and the free division loads the
    balls unevenly. One rail (VDD), temperatures of the reference Z3-B case."""
    import pad_interface as PAD
    import rms_currents as RMS
    from interconnect import rho_cu, rho_solder
    i_a = RMS.cell_currents()["i_cell_out_rms_a"] * LS.N_CELL ** 2   # every cell of the grid
    n, xc = grid(h_mm)
    N = n * n
    r_ball = PAD.bga_ball_resistance_ohm(20.0) * rho_solder(t_bga_c) / rho_solder(20.0)
    r_sb = rho_cu(t_board_c) / (BOARD_T_PER_RAIL_UM * 1e-6 * BOARD_OCC)
    d1 = np.full(n, 2.0)
    d1[0] = d1[-1] = 1.0
    L1 = sp.diags([d1, -np.ones(n - 1), -np.ones(n - 1)], [0, -1, 1], format="csr")
    eye = sp.identity(n, format="csr")
    L2 = (sp.kron(L1, eye) + sp.kron(eye, L1)).tocsr()
    G = 1.0 / r_ball
    k_l = land_shape()["kappa_one_rail"]
    fp = footprint_mask(n, xc).ravel()
    out = {"I_rms_A": i_a, "R_ball_mohm": r_ball * 1e3,
           "T_C": {"land": t_land_c, "board": t_board_c, "bga": t_bga_c},
           "board_R_s_mohm_sq": r_sb * 1e3, "grid_mm": h_mm, "cases": []}
    for t_um in t_land_um:
        r_sl = rho_cu(t_land_c) / (t_um * 1e-6 * LAND_OCC)
        case = {"t_land_um": t_um, "land_R_s_mohm_sq": r_sl * 1e3, "rails": {}}
        for rail in ("VDD", "GND"):
            qb, _ = board_sources(n, xc, rail, i_a, with_balls=False)   # vias inject
            ql = land_sources(n, xc, rail, i_a, with_balls=False)       # TSV footprints draw
            balls = ball_sites(rail)
            kb = np.array([np.searchsorted(xc, x - 1e-9) * n + np.searchsorted(xc, y - 1e-9)
                           for x, y in balls])
            cpl = sp.csr_matrix(
                (np.concatenate([np.full(len(kb), G)] * 2 + [np.full(len(kb), -G)] * 2),
                 (np.concatenate([kb, kb + N, kb, kb + N]),
                  np.concatenate([kb, kb + N, kb + N, kb]))), shape=(2 * N, 2 * N))
            A = (sp.block_diag([L2 / r_sb, L2 / r_sl]) + cpl).tolil()
            A[0, :] = 0
            A[0, 0] = 1.0
            rhs = np.concatenate([qb.ravel(), ql.ravel()])
            rhs[0] = 0.0
            v = spla.spsolve(A.tocsc(), rhs)
            vb, vl = v[:N].reshape(n, n), v[N:].reshape(n, n)
            p_b = (np.sum(np.diff(vb, axis=0) ** 2) + np.sum(np.diff(vb, axis=1) ** 2)) / r_sb
            p_l = (np.sum(np.diff(vl, axis=0) ** 2) + np.sum(np.diff(vl, axis=1) ** 2)) / r_sl
            ib = (v[kb] - v[kb + N]) * G
            k_b = shape("board", rail, h_mm)["kappa"]
            eq = {"board_w": k_b * i_a ** 2 * r_sb, "bga_w": i_a ** 2 * r_ball / len(balls),
                  "land_w": k_l * i_a ** 2 * r_sl}
            eq["sum_w"] = sum(eq.values())
            free = {"board_w": float(p_b), "bga_w": float(np.sum(ib ** 2) * r_ball),
                    "land_w": float(p_l)}
            free["sum_w"] = sum(free.values())
            case["rails"][rail] = {
                "equal_sharing": eq, "free_network": free,
                "free_over_equal": free["sum_w"] / eq["sum_w"],
                "ball_current_A": {"equal": i_a / len(balls), "free_max": float(ib.max()),
                                   "free_min": float(ib.min()),
                                   "free_sum": float(ib.sum()),
                                   "free_n_above_1p5A": int((ib > 1.5).sum()),
                                   "n_balls": len(balls),
                                   "free_share_through_in_footprint_balls":
                                       float(ib[fp[kb]].sum() / ib.sum())}}
        r = case["rails"]
        case["two_rails"] = {k: {q: r["VDD"][k][q] + r["GND"][k][q]
                                 for q in ("board_w", "bga_w", "land_w", "sum_w")}
                             for k in ("equal_sharing", "free_network")}
        case["two_rails"]["free_over_equal"] = (case["two_rails"]["free_network"]["sum_w"]
                                                / case["two_rails"]["equal_sharing"]["sum_w"])
        out["cases"].append(case)
    return out


def main():
    ls = land_shape()
    # the re-solve must reproduce the committed land-side FV at its own grid
    chk = shape("land", "VDD", GRID_MM)
    rel = abs(chk["kappa"] / ls["kappa_one_rail"] - 1.0)
    rel_v = abs(chk["kappa_V"] / ls["kappa_V_one_rail"] - 1.0)
    if max(rel, rel_v) > 1e-6:
        raise RuntimeError(f"re-solve does not reproduce the committed land-side FV: "
                           f"{chk['kappa']} vs {ls['kappa_one_rail']}")
    land = {"committed": ls, "resolve_check_rel": {"kappa": rel, "kappa_V": rel_v},
            "loss_fraction_in_footprints": chk["loss_fraction_in_footprints"],
            "area_fraction_footprints": chk["area_fraction_footprints"],
            "grid_check": {}}
    g05 = shape("land", "VDD", GRID_CHECK_MM)
    land["grid_check"][str(GRID_CHECK_MM)] = {k: g05[k] for k in ("kappa", "kappa_V")}
    land["grid_check"]["kappa_change_rel"] = g05["kappa"] / ls["kappa_one_rail"] - 1.0
    board = {"allocation": {"planes_per_rail": BOARD_PLANES_PER_RAIL,
                            "t_plane_um": BOARD_T_PLANE_UM,
                            "t_cu_per_rail_um": BOARD_T_PER_RAIL_UM, "occupancy": BOARD_OCC,
                            "status": "DECLARED (not in the Z3 design record)",
                            "basis": "four of the fourteen 1-oz layers of the 18-layer "
                                     "schedule (pcb_h1: 14 x 1 oz + 4 x 2 oz) carry the two "
                                     "1 V rails; the four 2-oz central planes instead would "
                                     "halve the loss"},
             "via_field": {k: (v if not isinstance(v, np.ndarray) else None)
                           for k, v in via_lattice().items() if k not in ("x_mm", "y_mm", "vdd")},
             "rails": {}}
    for rail in ("VDD", "GND"):
        board["rails"][rail] = {str(h): shape("board", rail, h)
                                for h in (GRID_MM, GRID_CHECK_MM)}
    b = board["rails"]
    board["kappa_two_rails"] = b["VDD"][str(GRID_MM)]["kappa"] + b["GND"][str(GRID_MM)]["kappa"]
    board["kappa_V_VDD"] = b["VDD"][str(GRID_MM)]["kappa_V"]
    board["kappa_V_GND"] = b["GND"][str(GRID_MM)]["kappa_V"]
    board["kappa_two_rails_grid_check"] = (b["VDD"][str(GRID_CHECK_MM)]["kappa"]
                                           + b["GND"][str(GRID_CHECK_MM)]["kappa"])
    board["grid_check_change_rel"] = board["kappa_two_rails_grid_check"] / board[
        "kappa_two_rails"] - 1.0
    from interconnect import rho_cu
    for t_c in (70.0, 90.0):
        r_s = rho_cu(t_c) / (BOARD_T_PER_RAIL_UM * 1e-6 * BOARD_OCC)
        board[f"at_{t_c:.0f}C_1000A"] = {"R_s_mohm_sq": r_s * 1e3,
                                         "P_two_rails_w": board["kappa_two_rails"] * 1e6 * r_s,
                                         "dV_VDD_mV": board["kappa_V_VDD"] * 1e3 * r_s * 1e3}
    out = {"model": __doc__.split("\n\n")[0].strip(), "grid_mm": GRID_MM,
           "land_side": land, "board_planes": board,
           "used_in_coupled_ledger": {"land_kappa_one_rail": ls["kappa_one_rail"],
                                      "land_kappa_V_one_rail": ls["kappa_V_one_rail"],
                                      "board_kappa_two_rails": board["kappa_two_rails"],
                                      "board_kappa_V_VDD": board["kappa_V_VDD"],
                                      "board_kappa_V_GND": board["kappa_V_GND"]}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["used_in_coupled_ledger"], indent=1))
    print("land: in-footprint loss share %.3f (area %.3f); 0.05 mm grid changes kappa by %+.2f %%"
          % (land["loss_fraction_in_footprints"], land["area_fraction_footprints"],
             100 * land["grid_check"]["kappa_change_rel"]))
    print("board: kappa VDD %.5f GND %.5f; in-footprint share VDD %.3f; 0.05 mm grid %+.2f %%"
          % (b["VDD"][str(GRID_MM)]["kappa"], b["GND"][str(GRID_MM)]["kappa"],
             b["VDD"][str(GRID_MM)]["loss_fraction_in_footprints"],
             100 * board["grid_check_change_rel"]))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
