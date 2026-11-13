"""Z3: the package land-side 1 V redistribution that the Z3 ledger records as NOT_MODELLED.

In Z3 the 1 V output (1 kA per rail) enters the package through the BGA. At the 1.5-A-per-
ball criterion it needs 667 balls per rail, which fill 1334 of the 1369 sites of the 0.8-mm
lattice, while the TSV fields that carry it to the die sit only under the 49 cell
footprints. The current of every ball outside a footprint must therefore travel laterally
in a land-side copper plane of the substrate. This script bounds that loss with a 2-D
finite-volume solution of one rail's plane:

    div( (1/R_s) grad V ) = -(injection - sink),   R_s = rho_Cu(T) / (t_Cu * occupancy)

with equal sharing over the rail's balls (the Z3 ledger's own assumption), a uniform sink
over each cell footprint (the TSV field), Neumann edges, on a 0.1-mm grid over the 30-mm
substrate. Loss = sum over grid faces of dV^2 / R_s, for one rail; the total is twice that
(VDD and GND planes). Written to research/tcpmt_revision/z3_landside_spreading.json.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

R = Path(__file__).resolve().parents[1]
OUT = R / "research" / "tcpmt_revision" / "z3_landside_spreading.json"

L_MM, H_MM = 30.0, 0.1                 # substrate side, grid spacing
PITCH, N_SIDE = 0.8, 37                # centred BGA lattice (1369 sites)
CELL_PITCH, CELL_SIDE, N_CELL = 3.165243, 2.3685, 7
I_RAIL = 1000.0                        # A, P_load / V_out
RHO20, ALPHA_CU = 1.72e-8, 3.93e-3     # ohm m, 1/K
T_C = 90.0                             # land side ~ substrate temperature (Z2/Z3 die ~90 C)
OCC = 0.80                             # the framework's output-plane occupancy


def grid():
    n = int(round(L_MM / H_MM))
    xc = -L_MM / 2 + H_MM * (np.arange(n) + 0.5)
    return n, xc


def sources(n, xc, rail):
    """Net current into each grid cell (A): + ball injection, - footprint sink."""
    q = np.zeros((n, n))
    idx = np.arange(N_SIDE) - (N_SIDE - 1) / 2
    balls = [(i * PITCH, j * PITCH) for a, i in enumerate(idx) for b, j in enumerate(idx)
             if (a + b) % 2 == (0 if rail == "VDD" else 1)]
    ib = I_RAIL / len(balls)
    for x, y in balls:
        q[np.searchsorted(xc, x - 1e-9), np.searchsorted(xc, y - 1e-9)] += ib
    cidx = (np.arange(N_CELL) - (N_CELL - 1) / 2) * CELL_PITCH
    mask = np.zeros((n, n), bool)
    for cx in cidx:
        for cy in cidx:
            mx = np.abs(xc - cx) <= CELL_SIDE / 2
            my = np.abs(xc - cy) <= CELL_SIDE / 2
            mask |= np.outer(mx, my)
    q[mask] -= I_RAIL / mask.sum()
    inside = sum(1 for x, y in balls
                 if any(abs(x - cx) <= CELL_SIDE / 2 and abs(y - cy) <= CELL_SIDE / 2
                        for cx in cidx for cy in cidx))
    return q, len(balls), inside


def solve(q, r_s):
    n = q.shape[0]
    N = n * n
    k = np.arange(N).reshape(n, n)
    g = 1.0 / r_s                      # face conductance of a square grid cell (S)
    rows, cols, vals = [], [], []
    for a, b in ((k[:-1, :], k[1:, :]), (k[:, :-1], k[:, 1:])):
        a, b = a.ravel(), b.ravel()
        rows += [a, b, a, b]
        cols += [a, b, b, a]
        vals += [np.full(a.size, g), np.full(a.size, g), np.full(a.size, -g),
                 np.full(a.size, -g)]
    A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                      shape=(N, N))
    A = A.tolil()
    A[0, :] = 0
    A[0, 0] = 1.0                       # reference node (the net source sums to zero)
    rhs = q.ravel().copy()
    rhs[0] = 0.0
    v = spla.spsolve(A.tocsc(), rhs).reshape(n, n)
    p = g * (np.sum(np.diff(v, axis=0) ** 2) + np.sum(np.diff(v, axis=1) ** 2))
    return p, float(v.max() - v.min())


def main():
    n, xc = grid()
    rho = RHO20 * (1 + ALPHA_CU * (T_C - 20.0))
    out = {"model": __doc__.split("\n\n")[1].strip(), "grid_mm": H_MM, "T_C": T_C,
           "occupancy": OCC, "I_rail_A": I_RAIL, "cases": []}
    q, nb, inside = sources(n, xc, "VDD")
    out["balls_per_rail"], out["balls_inside_footprints"] = nb, inside
    for t_um in (10.0, 20.0, 40.0, 60.0):
        r_s = rho / (t_um * 1e-6 * OCC)
        p, dv = solve(q, r_s)
        out["cases"].append({"t_cu_um": t_um, "R_s_mohm_sq": 1e3 * r_s,
                             "P_one_rail_w": p, "P_two_rails_w": 2 * p,
                             "dV_one_rail_mV": 1e3 * dv})
        print(f"t_Cu {t_um:4.0f} um  R_s {1e3 * r_s:.3f} mOhm/sq  P(2 rails) {2 * p:7.2f} W  "
              f"dV {1e3 * dv:.1f} mV", flush=True)
    print(f"balls per rail {nb}, of which {inside} lie inside a cell footprint")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
