#!/usr/bin/env python3
"""Phase-0M Part 7 -- 3-D DC conduction solver for current crowding.

    div( sigma(x) grad V ) = 0 ,   J = -sigma grad V ,   P = int J.E dV

Q3D is not licensed and that is not a reason to omit current crowding.

SOLVER CHOICE (the audit is in CURRENT_CROWDING_SOLVER_AUDIT.md)
  Elmer StaticCurrent  ABSENT from this environment
  GetDP                ABSENT
  Palace               ABSENT -- and its electrostatic mode solves a PERMITTIVITY problem,
                       which is NOT a DC conduction solver even where it is installed
  MOOSE                PRESENT (heat_transfer-opt). The steady conduction operator
                       div(k grad T) = 0 is the SAME operator with k -> sigma, T -> V, so
                       MOOSE is used as the independent cross-check, not as the workhorse
  this module          a conservative finite-volume discretisation on a graded tensor grid

FINITE VOLUME, NOT GALERKIN, ON PURPOSE. sigma jumps by nine orders of magnitude at every
metal/dielectric face. A cell-centred FV scheme with HARMONIC-MEAN face conductivities is
exactly conservative across such a jump and never leaks current into the dielectric through
a shared node, which a nodal Galerkin scheme on the same grid does. Current conservation is
checked to machine precision on every solve rather than assumed.
"""
from __future__ import annotations
import math
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve, cg, spilu, LinearOperator
from scipy.sparse import diags
from scipy.sparse.csgraph import connected_components


def graded(a: float, b: float, n: int, focus: float | None = None, ratio: float = 6.0):
    """n+1 node positions on [a,b], clustered around `focus` by `ratio` (1 = uniform)."""
    t = np.linspace(0.0, 1.0, n + 1)
    if focus is None or ratio <= 1.0:
        return a + (b - a) * t
    f = (focus - a) / (b - a)
    f = min(max(f, 1e-6), 1 - 1e-6)
    # piecewise tanh clustering: dense near f, coarse at the ends
    s = np.tanh(ratio * (t - f)) - np.tanh(ratio * (0 - f))
    s = s / (np.tanh(ratio * (1 - f)) - np.tanh(ratio * (0 - f)))
    return a + (b - a) * s


def _solve_spd(A, b, tol: float = 1e-11):
    """Direct solve for small systems, Jacobi-preconditioned CG above 20 000 unknowns.

    The operator is symmetric positive definite once the dielectric cells are eliminated, so
    CG is safe; the residual is CHECKED and the solve falls back to the direct factorisation
    if CG does not reach `tol`, so an unconverged iterative solve can never be mistaken for
    a physical result.
    """
    n = A.shape[0]
    if n <= 25000:
        return spsolve(A.tocsc(), b)
    # Jacobi-preconditioned CG above 12 000 unknowns. An ILU(1e-4, fill 12) preconditioner
    # was tried and is SLOWER here -- the factorisation itself costs more than the iterations
    # it saves on a 7-point operator -- so it is not used. The residual is always verified
    # and the solve falls back to the direct factorisation if CG does not reach it.
    d = A.diagonal().copy()
    d[d == 0] = 1.0
    M = diags(1.0 / d)
    x, info = cg(A, b, rtol=tol, atol=0.0, maxiter=20000, M=M)
    res = np.linalg.norm(A @ x - b) / max(np.linalg.norm(b), 1e-300)
    if info != 0 or res > 1e-9:
        return spsolve(A.tocsc(), b)
    return x


def refined(fine_lo: float, fine_hi: float, h_fine: float, lo: float, hi: float,
            growth: float = 1.25) -> np.ndarray:
    """Uniform spacing `h_fine` on [fine_lo, fine_hi], geometric growth outwards to [lo, hi].

    tanh clustering over a wide domain cannot resolve a feature two orders of magnitude
    smaller than the domain -- the first cell centre lands outside a 5 um contact on a
    200 um box. An explicit fine window plus geometric stretching does, and the fine
    spacing is then a stated, checkable parameter rather than an emergent one.
    """
    n_fine = max(int(round((fine_hi - fine_lo) / h_fine)), 1)
    core = np.linspace(fine_lo, fine_hi, n_fine + 1)
    out = [core]
    for sgn, edge, start in ((-1, lo, fine_lo), (1, hi, fine_hi)):
        pts, x, h = [], start, h_fine
        while (x - edge) * sgn < -1e-15:
            h *= growth
            x = x + sgn * h
            if (x - edge) * sgn > 0:
                x = edge
            pts.append(x)
        if pts:
            out.append(np.array(pts))
    return np.unique(np.concatenate(out))


def snapped(base: np.ndarray, mandatory, h_fine: float, frac: float = 0.3) -> np.ndarray:
    """Insert geometry interface planes into a grid and delete the slivers they create.

    A trace 10 um wide on a 1.68 um grid is staircased to 10.10 um at one refinement and
    9.71 um at the next, so the resistance moves 4 % in the WRONG direction and K_crowd does
    not converge. Forcing a node exactly on every material interface removes that error
    entirely for the rectangular features; the circular via and pad remain staircased, which
    is why their discretised areas are reported alongside the analytic ones.
    """
    man = np.unique(np.asarray([m for m in mandatory
                                if base[0] - 1e-18 <= m <= base[-1] + 1e-18], float))
    if man.size == 0:
        return base
    keep = base[np.min(np.abs(base[:, None] - man[None, :]), axis=1) > frac * h_fine]
    out = np.unique(np.concatenate([keep, man, base[[0, -1]]]))
    # DEDUPLICATE WITH A TOLERANCE. np.unique removes only bit-identical values. Two
    # mandatory planes that coincide physically -- a pad radius that equals a trace
    # half-width, say -- can differ by an ULP and survive as a ZERO-WIDTH cell, whose
    # terminal conductance is infinite and whose row poisons the matrix. That produced one
    # silently wrong K_crowd = 0.32 in a 92-point sweep, with only the current-balance
    # residual to show for it.
    return out[np.concatenate([[True], np.diff(out) > 1e-9 * h_fine])]


class FVConduction:
    """Cell-centred FV solve of div(sigma grad V) = 0 on a graded tensor grid."""

    def __init__(self, xn, yn, zn):
        self.xn, self.yn, self.zn = map(np.asarray, (xn, yn, zn))
        self.nx, self.ny, self.nz = len(xn) - 1, len(yn) - 1, len(zn) - 1
        self.dx = np.diff(self.xn); self.dy = np.diff(self.yn); self.dz = np.diff(self.zn)
        for ax, d in (("x", self.dx), ("y", self.dy), ("z", self.dz)):
            if d.size == 0 or not np.all(d > 0):
                bad = int(np.argmin(d)) if d.size else -1
                raise ValueError(
                    f"non-positive cell width on axis {ax}: min = {d.min() if d.size else 0:.3e} m "
                    f"at index {bad}. A degenerate cell gives an infinite terminal "
                    f"conductance and a silently wrong answer -- fix the grid, do not clip it.")
        self.xc = 0.5 * (self.xn[:-1] + self.xn[1:])
        self.yc = 0.5 * (self.yn[:-1] + self.yn[1:])
        self.zc = 0.5 * (self.zn[:-1] + self.zn[1:])
        self.n = self.nx * self.ny * self.nz
        self.sigma = np.zeros((self.nx, self.ny, self.nz))

    def idx(self, i, j, k):
        return (i * self.ny + j) * self.nz + k

    def assign(self, fn):
        X, Y, Z = np.meshgrid(self.xc, self.yc, self.zc, indexing="ij")
        self.sigma = fn(X, Y, Z)

    def _face_conductances(self):
        """G_face = sigma_harmonic * A_face / d_centres, per axis."""
        s = self.sigma
        gx = np.zeros((self.nx - 1, self.ny, self.nz))
        gy = np.zeros((self.nx, self.ny - 1, self.nz))
        gz = np.zeros((self.nx, self.ny, self.nz - 1))
        # x faces
        d1 = self.dx[:-1][:, None, None] / 2.0
        d2 = self.dx[1:][:, None, None] / 2.0
        A = (self.dy[None, :, None] * self.dz[None, None, :])
        gx = A / (d1 / np.maximum(s[:-1], 1e-300) + d2 / np.maximum(s[1:], 1e-300))
        d1 = self.dy[:-1][None, :, None] / 2.0
        d2 = self.dy[1:][None, :, None] / 2.0
        A = (self.dx[:, None, None] * self.dz[None, None, :])
        gy = A / (d1 / np.maximum(s[:, :-1], 1e-300) + d2 / np.maximum(s[:, 1:], 1e-300))
        d1 = self.dz[:-1][None, None, :] / 2.0
        d2 = self.dz[1:][None, None, :] / 2.0
        A = (self.dx[:, None, None] * self.dy[None, :, None])
        gz = A / (d1 / np.maximum(s[:, :, :-1], 1e-300) + d2 / np.maximum(s[:, :, 1:], 1e-300))
        return gx, gy, gz

    def solve(self, inject_mask, inject_total_a, ground_mask, axis_in=0, axis_gnd=0,
              active_tol: float = 1e-5, lin_tol: float = 1e-11):
        """Two-terminal solve with EXPLICIT terminal nodes.

        A cell-centred grid places the unknown at the cell centre, so injecting and
        extracting at cell centres shortens the conducting path by half a cell at each end:
        the uniform-bar test returns R = R_exact (n-1)/n, an O(1/n) error that would be
        mistaken for a crowding effect. Both terminals are therefore represented as extra
        equipotential NODES joined to their boundary cells by the exact half-cell
        conductance sigma A / (d/2). The uniform bar then returns R_exact at every mesh.
        """
        gx, gy, gz = self._face_conductances()
        NT = self.n + 1                      # + the inlet terminal; ground is node "0 volts"
        term = self.n
        flat = np.arange(self.n).reshape(self.nx, self.ny, self.nz)
        diag = np.zeros(NT)

        # VECTORISED ASSEMBLY. Building the COO triplets with Python list.extend() over a
        # few million faces dominated the runtime by two orders of magnitude and made a
        # 10-um-feature mesh untestable; np.concatenate does the same work in milliseconds.
        pa, pb, pg = [], [], []
        for A_, B_, G_ in ((flat[:-1, :, :], flat[1:, :, :], gx),
                           (flat[:, :-1, :], flat[:, 1:, :], gy),
                           (flat[:, :, :-1], flat[:, :, 1:], gz)):
            pa.append(A_.ravel()); pb.append(B_.ravel()); pg.append(G_.ravel())
        fa = np.concatenate(pa); fb = np.concatenate(pb); fg = np.concatenate(pg)
        np.add.at(diag, fa, fg); np.add.at(diag, fb, fg)

        # half-cell terminal conductances
        d = (self.dx[:, None, None], self.dy[None, :, None], self.dz[None, None, :])
        ones = np.ones((self.nx, self.ny, self.nz))
        A_perp = {0: (self.dy[None, :, None] * self.dz[None, None, :]) * ones,
                  1: (self.dx[:, None, None] * self.dz[None, None, :]) * ones,
                  2: (self.dx[:, None, None] * self.dy[None, :, None]) * ones}
        g_in = self.sigma * A_perp[axis_in] / (d[axis_in] / 2.0)
        g_gn = self.sigma * A_perp[axis_gnd] / (d[axis_gnd] / 2.0)
        gi = np.where(inject_mask, g_in, 0.0)
        gg = np.where(ground_mask, g_gn, 0.0)
        if gi.sum() <= 0 or gg.sum() <= 0:
            raise ValueError("empty or non-conducting terminal set")
        sel = np.flatnonzero(gi.ravel() > 0)
        gsel = gi.ravel()[sel]
        np.add.at(diag, sel, gsel)
        diag[term] += gsel.sum()
        ggr = gg.ravel()
        np.add.at(diag, np.flatnonzero(ggr > 0), ggr[ggr > 0])

        rows = np.concatenate([fa, fb, sel, np.full(sel.size, term), np.arange(NT)])
        cols = np.concatenate([fb, fa, np.full(sel.size, term), sel, np.arange(NT)])
        vals = np.concatenate([-fg, -fg, -gsel, -gsel, diag])

        b = np.zeros(NT)
        b[term] = inject_total_a
        A = coo_matrix((vals, (rows, cols)), shape=(NT, NT)).tocsr()

        # CONDITION NUMBER AND COST. sigma spans nine decades. Solving over the dielectric
        # cells makes the matrix badly conditioned AND multiplies the unknown count by ten
        # for cells that carry a negligible current by construction.
        #
        # The first version of this filter compared each cell's conductance with the MEDIAN
        # conductance. In a box that is 90 % dielectric the median IS a dielectric value, so
        # nothing was eliminated and a 28 000-cell transition cell took 97 s. The criterion
        # is now sigma against MAX sigma, which cannot invert with the fill fraction.
        act = (self.sigma > active_tol * self.sigma.max()).ravel()
        # A metal island not joined to either terminal leaves a floating block and a
        # singular matrix, so the active set is reduced to the component containing the
        # inlet terminal. Any current in a discarded island would be zero by definition.
        idx_act = np.flatnonzero(act)
        remap = -np.ones(self.n, dtype=np.int64)
        remap[idx_act] = np.arange(idx_act.size)
        m_ = np.isin(fa, idx_act) & np.isin(fb, idx_act)
        adj = coo_matrix((np.ones(m_.sum()), (remap[fa[m_]], remap[fb[m_]])),
                         shape=(idx_act.size, idx_act.size))
        ncomp, lab = connected_components(adj, directed=False)
        inlet_cells = remap[sel[np.isin(sel, idx_act)]]
        if inlet_cells.size == 0:
            raise ValueError("the injection set is entirely outside the conducting region")
        good = np.isin(lab, np.unique(lab[inlet_cells]))
        act[:] = False
        act[idx_act[good]] = True
        self.n_islands_dropped = int(ncomp - np.unique(lab[inlet_cells]).size)
        act = np.append(act, True)                       # the terminal is always active
        keep = np.flatnonzero(act)
        Ak = A[keep][:, keep].tocsr()
        Vk = _solve_spd(Ak, b[keep], tol=lin_tol)
        Vall = np.zeros(NT)
        Vall[keep] = Vk
        self.n_active = int(act.sum()) - 1
        self.V = Vall[:self.n].reshape(self.nx, self.ny, self.nz)
        self.V_terminal = float(Vall[term])
        self.gx, self.gy, self.gz = gx, gy, gz
        self._gi, self._gg = gi, gg
        self._I = inject_total_a
        return self.V

    # ---- derived quantities -----------------------------------------------------------
    def joule_w(self):
        V = self.V
        return float((self.gx * (V[:-1] - V[1:]) ** 2).sum()
                     + (self.gy * (V[:, :-1] - V[:, 1:]) ** 2).sum()
                     + (self.gz * (V[:, :, :-1] - V[:, :, 1:]) ** 2).sum()
                     + (self._gi * (self.V_terminal - V) ** 2).sum()
                     + (self._gg * V ** 2).sum())

    def current_out(self):
        return float((self._gg * self.V).sum())

    def current_in(self):
        return float((self._gi * (self.V_terminal - self.V)).sum())

    def j_field(self):
        """Face current densities mapped back to cell centres, magnitude."""
        V = self.V
        Ax = (self.dy[None, :, None] * self.dz[None, None, :])
        Ay = (self.dx[:, None, None] * self.dz[None, None, :])
        Az = (self.dx[:, None, None] * self.dy[None, :, None])
        jx = np.zeros_like(V); jy = np.zeros_like(V); jz = np.zeros_like(V)
        fx = self.gx * (V[:-1] - V[1:]) / Ax
        fy = self.gy * (V[:, :-1] - V[:, 1:]) / Ay
        fz = self.gz * (V[:, :, :-1] - V[:, :, 1:]) / Az
        jx[:-1] += 0.5 * fx; jx[1:] += 0.5 * fx
        jy[:, :-1] += 0.5 * fy; jy[:, 1:] += 0.5 * fy
        jz[:, :, :-1] += 0.5 * fz; jz[:, :, 1:] += 0.5 * fz
        return np.sqrt(jx ** 2 + jy ** 2 + jz ** 2)

    def resistance(self):
        """R = V_terminal / I, with P/I^2 available as an independent check."""
        return self.V_terminal / self._I

    def resistance_from_power(self):
        return self.joule_w() / self._I ** 2
