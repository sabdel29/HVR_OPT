"""PHASE 0N-AL --- the package RDL sheet on an ALIGNED, GRADED finite-volume grid.

WHY THE UNIFORM GRID COULD NOT CONVERGE Z1. Each VR cell contact is a 2.3685 mm
square coupled to the sheet through rho_c = 1e-5 Ohm.mm^2, i.e. about 1.8 uOhm
over the whole tile -- three orders below anything else in the path. Electrically
every tile is therefore a near-equipotential ISLAND in the sheet, and the current
leaving the sheet crowds into the island's perimeter within the transfer length
L_T = sqrt(rho_c / R_sq) ~ 30 um. On a uniform grid the island boundary falls
wherever the grid happens to put it: nodes straddling the edge receive a partial
overlap, so the island is fuzzy over one cell width h and the resistance error is
FIRST ORDER in h. Z2's balls sit on an annulus millimetres from any tile, so the
fuzz is a small fraction of a long sheet path and Z2 converged; Z1's balls sit
under or beside the tiles, the path is short, and the same fuzz is a large
fraction of it. Refining a uniform grid only shrinks a first-order error slowly,
and "1 % between the two finest levels" can then be passed while the true error
is several times larger.

WHAT THIS DOES INSTEAD. A cell-centred finite-volume discretisation on a tensor
grid whose control-volume FACES lie exactly on every tile edge, so each tile
covers whole control volumes at every refinement level and the island boundary
is exact rather than approximated. Spacing is graded down to h_fine near every
tile edge and every BGA disc edge, where the current crowds, and relaxes to
h_coarse elsewhere. Contacts are still stamped by exact area overlap (squares
exactly, discs by 64-point Gauss quadrature), so total contact conductance is
grid-independent as before.
"""
from __future__ import annotations

import math

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from pkg_rdl_network import (SUBSTRATE_MM, VR_TILE_SIDE_MM, _disc_rect_area,
                             sheet_resistance_ohm_sq, RHO_C_CASES)

#: refinement levels: (h_fine_mm, h_coarse_mm). Each level halves both.
LEVELS = {0: (0.040, 0.40), 1: (0.020, 0.20), 2: (0.010, 0.10), 3: (0.005, 0.05)}
GRADE = 0.30           # h grows by 30 % of the distance to the nearest feature


def axis_faces(lo, hi, mandatory, features, h_fine, h_coarse, grade=GRADE):
    """Control-volume faces on [lo, hi].

    `mandatory` faces are hit EXACTLY. Between them, faces equidistribute the size
    function h(x) = min(h_coarse, h_fine + grade * d(x)), d = distance to the
    nearest feature, so spacing grades smoothly and every segment ends exactly on
    its mandatory face.
    """
    feats = np.unique(np.asarray(list(features) + list(mandatory), float))

    def h(x):
        d = np.min(np.abs(feats[None, :] - np.asarray(x)[:, None]), axis=1)
        return np.minimum(h_coarse, h_fine + grade * d)

    stops = np.unique(np.clip(np.r_[lo, np.asarray(mandatory, float), hi], lo, hi))
    faces = [lo]
    for a, b in zip(stops[:-1], stops[1:]):
        if b - a < 1e-12:
            continue
        xs = np.linspace(a, b, 2001)
        dens = 1.0 / h(xs)
        cum = np.concatenate([[0.0], np.cumsum(0.5 * (dens[1:] + dens[:-1])
                                               * np.diff(xs))])
        n = max(1, int(math.ceil(cum[-1])))
        targets = np.linspace(0.0, cum[-1], n + 1)[1:]
        faces.extend(np.interp(targets, cum, xs).tolist())
        faces[-1] = b
    return np.asarray(faces)


class RefinedSheet:
    def __init__(self, fx, fy, r_sq):
        self.fx, self.fy, self.r_sq = np.asarray(fx), np.asarray(fy), r_sq
        self.cx = 0.5 * (self.fx[1:] + self.fx[:-1])
        self.cy = 0.5 * (self.fy[1:] + self.fy[:-1])
        self.dx = np.diff(self.fx)
        self.dy = np.diff(self.fy)
        self.nx, self.ny = len(self.cx), len(self.cy)
        self.n = self.nx * self.ny

    def node(self, i, j):
        return i * self.ny + j

    def laplacian(self):
        g0 = 1.0 / self.r_sq
        I, J = np.meshgrid(np.arange(self.nx), np.arange(self.ny), indexing="ij")
        rows, cols, vals = [], [], []
        # x-neighbours: conductance = g0 * dy_j / (cx_{i+1} - cx_i)
        gx = g0 * self.dy[None, :] / np.diff(self.cx)[:, None]
        a = (I[:-1, :] * self.ny + J[:-1, :]).ravel()
        b = (I[1:, :] * self.ny + J[1:, :]).ravel()
        g = gx.ravel()
        rows += [a, b, a, b]; cols += [a, b, b, a]; vals += [g, g, -g, -g]
        gy = g0 * self.dx[:, None] / np.diff(self.cy)[None, :]
        a = (I[:, :-1] * self.ny + J[:, :-1]).ravel()
        b = (I[:, 1:] * self.ny + J[:, 1:]).ravel()
        g = gy.ravel()
        rows += [a, b, a, b]; cols += [a, b, b, a]; vals += [g, g, -g, -g]
        return sp.coo_matrix((np.concatenate(vals),
                              (np.concatenate(rows), np.concatenate(cols))),
                             shape=(self.n, self.n)).tocsr()

    def overlap(self, x, y, size, shape):
        """Exact (square) or quadrature (disc) overlap with every control volume."""
        r = size / 2.0
        i0 = max(0, np.searchsorted(self.fx, x - r) - 1)
        i1 = min(self.nx, np.searchsorted(self.fx, x + r) + 1)
        j0 = max(0, np.searchsorted(self.fy, y - r) - 1)
        j1 = min(self.ny, np.searchsorted(self.fy, y + r) + 1)
        nodes, areas = [], []
        for i in range(i0, i1):
            x1, x2 = self.fx[i], self.fx[i + 1]
            for j in range(j0, j1):
                y1, y2 = self.fy[j], self.fy[j + 1]
                if shape == "square":
                    ox = min(x2, x + r) - max(x1, x - r)
                    oy = min(y2, y + r) - max(y1, y - r)
                    a = ox * oy if (ox > 0 and oy > 0) else 0.0
                else:
                    a = _disc_rect_area(x, y, r, x1, x2, y1, y2)
                if a > 1e-15:
                    nodes.append(self.node(i, j))
                    areas.append(a)
        return np.asarray(nodes, int), np.asarray(areas)


def build_grid(ball_xy, cell_xy, level, span=SUBSTRATE_MM, d_ball=0.400,
               tile=VR_TILE_SIDE_MM):
    h_fine, h_coarse = LEVELS[level]
    half = span / 2.0
    a = tile / 2.0
    tx = sorted({round(cx + s * a, 9) for cx, _ in cell_xy for s in (-1, 1)})
    ty = sorted({round(cy + s * a, 9) for _, cy in cell_xy for s in (-1, 1)})
    r = d_ball / 2.0
    bx = sorted({round(x + s * r, 9) for x, _ in ball_xy for s in (-1, 1)})
    by = sorted({round(y + s * r, 9) for _, y in ball_xy for s in (-1, 1)})
    fx = axis_faces(-half, half, tx, bx, h_fine, h_coarse)
    fy = axis_faces(-half, half, ty, by, h_fine, h_coarse)
    return fx, fy


class RefinedVoltageFedNetwork:
    """Same physics and API as pkg_rdl_network.VoltageFedNetwork, refined grid."""

    def __init__(self, fx, fy, r_sq):
        self.sheet = RefinedSheet(fx, fy, r_sq)
        self.ns = self.sheet.n

    def build(self, ball_xy, cell_xy, r_ball_ohm, rho_c_ball, rho_c_cell,
              d_ball_mm, d_cell_mm, cell_shape="square"):
        sh = self.sheet
        nb, nc = len(ball_xy), len(cell_xy)
        self.nb, self.nc = nb, nc
        self.i_ball, self.i_cell = self.ns, self.ns + nb
        self.i_rail = self.ns + nb + nc
        N = self.i_rail + 1
        L = sh.laplacian().tocoo()
        rows, cols, vals = [L.row], [L.col], [L.data]

        def stamp(a, nodes, g):
            k = len(nodes)
            rows.extend([np.full(k, a), nodes, np.full(k, a), nodes])
            cols.extend([np.full(k, a), nodes, nodes, np.full(k, a)])
            vals.extend([g, g, -g, -g])

        self.ball_meta, self.cell_meta = [], []
        for j, (x, y) in enumerate(ball_xy):
            bj = self.i_ball + j
            stamp(self.i_rail, np.array([bj]), np.array([1.0 / r_ball_ohm]))
            nd, ar = sh.overlap(x, y, d_ball_mm, "disc")
            stamp(bj, nd, ar / rho_c_ball)
            self.ball_meta.append({"a_contact_mm2": float(ar.sum()),
                                   "n_nodes": len(nd), "shape": "disc"})
        for m, (x, y) in enumerate(cell_xy):
            cm = self.i_cell + m
            nd, ar = sh.overlap(x, y, d_cell_mm, cell_shape)
            stamp(cm, nd, ar / rho_c_cell)
            self.cell_meta.append({"a_contact_mm2": float(ar.sum()),
                                   "n_nodes": len(nd), "shape": cell_shape})
        self.G = sp.coo_matrix((np.concatenate(vals),
                                (np.concatenate(rows), np.concatenate(cols))),
                               shape=(N, N)).tocsr()
        self.N = N
        self.r_ball_ohm = r_ball_ohm
        return self

    def solve(self, i_cells, v_rail=0.0):
        N = self.N
        rhs = np.zeros(N)
        rhs[self.i_cell:self.i_cell + self.nc] = -np.asarray(i_cells, float)
        free = np.ones(N, bool)
        free[self.i_rail] = False
        Gff = self.G[free][:, free].tocsc()
        gfr = np.asarray(self.G[free][:, [self.i_rail]].todense()).ravel()
        Vf = spla.spsolve(Gff, rhs[free] - gfr * v_rail, permc_spec="COLAMD")
        V = np.empty(N)
        V[free] = Vf
        V[self.i_rail] = v_rail
        return V

    def report(self, V, i_cells):
        i_cells = np.asarray(i_cells, float)
        i_tot = float(i_cells.sum())
        vb = V[self.i_ball:self.i_ball + self.nb]
        vc = V[self.i_cell:self.i_cell + self.nc]
        i_ball = (V[self.i_rail] - vb) / self.r_ball_ohm
        Gc = self.G.tocoo()
        up = Gc.row < Gc.col
        p = float(np.sum(-Gc.data[up] * (V[Gc.row[up]] - V[Gc.col[up]]) ** 2))
        p_vi = float(V[self.i_rail] * i_ball.sum() - np.dot(vc, i_cells))
        return {"i_total_a": i_tot, "p_loss_w": p, "p_loss_vi_w": p_vi,
                "energy_residual_rel": abs(p - p_vi) / max(abs(p), 1e-300),
                "r_eff_ohm": p / i_tot ** 2, "i_ball_a": i_ball,
                "i_ball_sum_a": float(i_ball.sum()),
                "i_ball_max_a": float(i_ball.max()),
                "ball_imax_over_imean": float(i_ball.max() / (i_tot / self.nb)),
                "max_cell_drop_v": float(V[self.i_rail] - vc.min()),
                "cell_drop_v": (V[self.i_rail] - vc),
                "n_unknowns": self.N}


# ===========================================================================
# Cell terminal geometry, traced from the converter's own layout model.
#
# routing.tile_layout() -- the layout the intra-VR resistance graph is built on --
# places the cell's 48 V input pad as a 0.200 x 0.200 mm square at (-0.45 s,
# -0.45 s) from the tile centre, s = 2.3685 mm. Earlier package networks used the
# WHOLE 2.3685 mm tile as the input contact, which was never traced to anything;
# it is now a sensitivity case. The layout defines no HV-return pad, so the
# return terminal is DECLARED as the same pad mirrored in x, (+0.45 s, -0.45 s):
# an assumption, labelled as one, and bracketed by the full-tile case.
# ===========================================================================
VIN_PAD_SIDE_MM = 0.200
VIN_PAD_OFFSET = (-0.45, -0.45)           # fraction of tile side, from routing.py
RETURN_PAD_OFFSET = (+0.45, -0.45)        # DECLARED mirror image
TERMINAL_MODES = {
    "VIN_PAD": "traced 0.2 mm input pad (return mirrored, declared)",
    "HALF_TILE": "corner-anchored square of side s/2 containing the traced pad",
    "FULL_TILE": "the whole 2.3685 mm tile -- the earlier, untraced assumption",
}


def cell_terminals(cells, rail, mode="VIN_PAD", tile=VR_TILE_SIDE_MM):
    """-> [(x, y, side)] for every cell, for the given rail and terminal mode."""
    s = tile
    out = []
    ox, oy = VIN_PAD_OFFSET if rail == "supply" else RETURN_PAD_OFFSET
    for cx, cy in cells:
        if mode == "VIN_PAD":
            out.append((cx + ox * s, cy + oy * s, VIN_PAD_SIDE_MM))
        elif mode == "HALF_TILE":
            c = s / 2.0
            sx = -1.0 if ox < 0 else 1.0
            out.append((cx + sx * (s / 2 - c / 2), cy - (s / 2 - c / 2), c))
        elif mode == "FULL_TILE":
            out.append((cx, cy, s))
        else:
            raise ValueError(f"unknown terminal mode {mode!r}")
    return out


def build_grid_general(ball_xy, squares, level, span=SUBSTRATE_MM, d_ball=0.400):
    """Faces aligned to EVERY terminal-square edge; grading near ball discs too."""
    h_fine, h_coarse = LEVELS[level]
    half = span / 2.0
    tx = sorted({round(x + k * c / 2, 9) for x, _, c in squares for k in (-1, 1)})
    ty = sorted({round(y + k * c / 2, 9) for _, y, c in squares for k in (-1, 1)})
    r = d_ball / 2.0
    bx = sorted({round(x + k * r, 9) for x, _ in ball_xy for k in (-1, 1)})
    by = sorted({round(y + k * r, 9) for _, y in ball_xy for k in (-1, 1)})
    return (axis_faces(-half, half, tx, bx, h_fine, h_coarse),
            axis_faces(-half, half, ty, by, h_fine, h_coarse))


def solve_rail(arch, rail, N, level, mode="VIN_PAD", t_cu_mm=5.0e-3, occupancy=0.30,
               rho_c=None, T_c=20.0, i_cells=None, candidate_override=None,
               allocation_rule="nearest_symmetric"):
    """One package HV sheet (supply OR return) at ball count N per rail."""
    import physical_coords as PCO
    import pad_interface as PI
    import pkg_rdl_network as K
    rho_c = RHO_C_CASES["CONTACT_N"] if rho_c is None else rho_c
    cells = PCO.physical_cell_coordinates()
    cand = (candidate_override if candidate_override is not None
            else PCO.bga_lattice_sites(K.architecture_cutout_mm(arch)))
    sel = PCO.select_power_sites(cand, cells, N, N, allocation_rule)[rail]
    sq = cell_terminals(cells, rail, mode)
    fx, fy = build_grid_general(sel, sq, level)
    rsq = sheet_resistance_ohm_sq(t_cu_mm, occupancy, T_c)
    net = RefinedVoltageFedNetwork(fx, fy, rsq)
    # every terminal in a mode has one side length
    net.build(sel, [(x, y) for x, y, _ in sq], PI.bga_ball_resistance_ohm(T_c),
              rho_c, rho_c, PI.BGA_D_UM * 1e-3, sq[0][2], cell_shape="square")
    i = (np.full(len(cells), 1.0 / len(cells)) if i_cells is None
         else np.asarray(i_cells, float))
    rep = net.report(net.solve(i), i)
    rep.update({"arch": arch, "rail": rail, "n_per_rail": N, "level": level,
                "terminal_mode": mode, "t_cu_mm": t_cu_mm, "occupancy": occupancy,
                "rho_c_ohm_mm2": rho_c, "T_c": T_c, "n_cv": net.sheet.n,
                "ball_xy": [list(p) for p in sel],
                "allocation_rule": allocation_rule})
    return rep


CONV_METRICS = ("r_eff_ohm", "p_loss_w", "max_cell_drop_v", "i_ball_max_a",
                "ball_imax_over_imean")
CONV_THRESH = 0.01


def converge(arch, rail, N, levels=(1, 2, 3), **kw):
    rows = [solve_rail(arch, rail, N, lv, **kw) for lv in levels]
    fine, mid = rows[-1], rows[-2]
    deltas = {m: abs(fine[m] - mid[m]) / abs(fine[m]) for m in CONV_METRICS}
    return {"arch": arch, "rail": rail, "n_per_rail": N, "levels": list(levels),
            "rows": rows, "deltas": deltas,
            "worst_metric": max(deltas, key=deltas.get),
            "worst_delta": max(deltas.values()),
            "converged": max(deltas.values()) < CONV_THRESH}
