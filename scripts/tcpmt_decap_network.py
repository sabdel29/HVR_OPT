"""TCPMT revision -- the Z1 cells sharing the package 48 V network: port model.

TCPMT round 3: the cells are those of the design in force (the design record: 36 on a 6 x 6
grid in production) and the interleaving patterns are built for any n x n grid (phases()).

The one-cell circuit (tcpmt_decap_circuit) gives each cell 1/N of the network, which is
exact only when every cell sees the same path and all switch in phase. This module keeps the
real network: the production supply and return sheets of package_network.json (refined FV
grid, 5 um Cu at 30 %, the traced 0.2 mm VIN pads, the 54 + 54 BGA balls nearest the centre,
rho_c contacts, ball resistance) are Kron-reduced onto their PORTS

    rail   the BGA balls' board side (one node per sheet)
    cells  the N cell terminals (VIN pad on the supply sheet, mirrored pad on the return)
    ring   one contact per ring capacitor (through-substrate vias to the land-side sheets)

and every harmonic of the cells' input current is solved on the reduced network with:
the board loop inductance between the supply rail and the board node, the ring capacitors
between supply-ring and return-ring ports, local capacitors across each cell's two
terminals, and an arbitrary phase per cell (interleaving). The sheet loss (balls included)
at DC and at each harmonic gives the loss-equivalent k of the package network:

    k_eq^2 = (P_DC + sum_n P_n) / P_DC

which is exactly the factor by which the ledger's package 48 V terms (I_rms^2 R) grow.

Check: with no capacitors and all cells in phase k_eq equals the cell waveform's own k, and
the DC loss per A^2 reproduces package_network.json (R_supply + R_return = 2.262 mOhm).
"""
from __future__ import annotations

import json
import os
import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

R = Path(__file__).resolve().parents[1]
for _p in ("scripts/phase0nw", "scripts/phase0mr", "scripts/phase0m", "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))

NETWORK = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "final_closure" / "package_network.json"
sys.path.insert(0, str(R / "scripts"))
from hvr_scratch import path as _scratch                            # noqa: E402
#: regenerable in ~20 s; kept out of the repository
CACHE = _scratch("tcpmt_decap") / "port_matrices.npz"
LEVEL = 1
RING_SIDE_MM = 0.30          # TSV landing under each ring-capacitor terminal
GRID_HALF_MM = 10.68         # measured cell-grid half span (configs/phase0nz)
PKG_HALF_MM = 15.0
RING_CLEAR_MM = 0.30         # clearance to the cell grid and to the package edge
CAP_1206 = (3.2, 1.6)
CAP_GAP_MM = 0.30


# ------------------------------------------------------------------ geometry
@lru_cache(maxsize=1)
def cells():
    import physical_coords as PCO
    return [tuple(c) for c in PCO.physical_cell_coordinates()]


#: (supply, return) ball centres replacing the network's (a diagnostic at another BGA count,
#: tcpmt_decap_placement limits); the port reduction of such a geometry is cached apart
BALLS_OVERRIDE = None


def balls(rail):
    if BALLS_OVERRIDE is not None:
        return [tuple(p) for p in BALLS_OVERRIDE[0 if rail == "supply" else 1]]
    pn = json.loads(NETWORK.read_text())
    return [tuple(p) for p in pn["convergence"][f"Z1_{rail}"]["ball_xy"]]


def ring_layout(cap=CAP_1206, gap=CAP_GAP_MM, clear=RING_CLEAR_MM):
    """1206 capacitors packed in the ring between the cell grid and the package edge, long
    axis parallel to the nearest edge, in as many rows as the ring width allows. Returns the
    capacitor centres (mm) and the packing summary."""
    inner = GRID_HALF_MM + clear
    outer = PKG_HALF_MM - clear
    w = outer - inner
    pitch_l, pitch_w = cap[0] + gap, cap[1] + gap
    n_rows = int(math.floor((w + gap) / pitch_w))
    xy = []
    for r in range(n_rows):
        off = inner + cap[1] / 2 + r * pitch_w
        # top/bottom strips span the full width (corners included)
        n_tb = int(math.floor((2 * outer + gap) / pitch_l))
        x0 = -(n_tb * pitch_l - gap) / 2 + cap[0] / 2
        for k in range(n_tb):
            for s in (1, -1):
                xy.append((x0 + k * pitch_l, s * off))
        # left/right strips between them
        span = 2 * (inner)                              # clear of the top/bottom strips
        n_lr = int(math.floor((span + gap) / pitch_l))
        y0 = -(n_lr * pitch_l - gap) / 2 + cap[0] / 2
        for k in range(n_lr):
            for s in (1, -1):
                xy.append((s * off, y0 + k * pitch_l))
    area = (2 * PKG_HALF_MM) ** 2 - (2 * GRID_HALF_MM) ** 2
    return xy, {"n_caps": len(xy), "rows": n_rows, "ring_width_mm": w,
                "ring_area_mm2": area, "cap_LxW_mm": list(cap), "spacing_mm": gap,
                "clearance_mm": clear}


# ------------------------------------------------------------------ Kron reduction
def reduce_sheet(rail, ring_xy, level=LEVEL):
    """Kron-reduced conductance (S) of one 20-C sheet over ports [rail, cells, ring]."""
    import pkg_rdl_refined as RF
    import pkg_rdl_network as K
    import pad_interface as PI
    cl = cells()
    bl = balls(rail)
    sq = RF.cell_terminals(cl, rail, "VIN_PAD")
    rsq = [(x, y, RING_SIDE_MM) for x, y in ring_xy]
    fx, fy = RF.build_grid_general(bl, sq + rsq, level)
    sh = RF.RefinedSheet(fx, fy, K.sheet_resistance_ohm_sq(5.0e-3, 0.30, 20.0))
    rho_c = K.RHO_C_CASES["CONTACT_N"]
    ns, nb, nc, nr = sh.n, len(bl), len(cl), len(rsq)
    # node numbering: sheet [0, ns), balls [ns, ns+nb), ports: rail, cells, ring
    i_rail = ns + nb
    i_cell = i_rail + 1
    i_ring = i_cell + nc
    N = i_ring + nr
    L = sh.laplacian().tocoo()
    rows, cols, vals = [L.row], [L.col], [L.data]

    def stamp(a, nodes, g):
        k = len(nodes)
        rows.extend([np.full(k, a), nodes, np.full(k, a), nodes])
        cols.extend([np.full(k, a), nodes, nodes, np.full(k, a)])
        vals.extend([g, g, -g, -g])

    r_ball = PI.bga_ball_resistance_ohm(20.0)
    for j, (x, y) in enumerate(bl):
        stamp(i_rail, np.array([ns + j]), np.array([1.0 / r_ball]))
        nd, ar = sh.overlap(x, y, PI.BGA_D_UM * 1e-3, "disc")
        stamp(ns + j, nd, ar / rho_c)
    for m, (x, y, s) in enumerate(sq):
        nd, ar = sh.overlap(x, y, s, "square")
        stamp(i_cell + m, nd, ar / rho_c)
    for q, (x, y, s) in enumerate(rsq):
        nd, ar = sh.overlap(x, y, s, "square")
        stamp(i_ring + q, nd, ar / rho_c)
    G = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                      shape=(N, N)).tocsr()
    P = np.arange(i_rail, N)
    I = np.arange(0, i_rail)
    Gii = G[I][:, I].tocsc()
    Gip = G[I][:, P].toarray()
    Gpp = G[P][:, P].toarray()
    lu = spla.splu(Gii, permc_spec="COLAMD")
    X = lu.solve(Gip)
    Gred = Gpp - Gip.T @ X
    # the ball nodes' voltages from the port voltages (Kron back-substitution: internal
    # nodes carry no injection, so V_int = -Gii^-1 Gip V_ports) and the ball conductance:
    # the ball currents of any port solution (ball_rms)
    return 0.5 * (Gred + Gred.T), {"n_sheet": ns, "n_balls": nb, "n_ports": len(P),
                                    "level": level, "ball_map": -X[ns:ns + nb, :],
                                    "g_ball_S": 1.0 / r_ball}


def _geometry_key():
    """The cells and balls the reduction depends on (TCPMT round 3: a cached reduction of
    another design's cells or another network's balls must never be reused)."""
    import hashlib
    h = hashlib.sha256()
    for arr in (np.array(cells(), float).round(6), np.array(balls("supply"), float).round(6),
                np.array(balls("return"), float).round(6)):
        h.update(arr.tobytes())
    return h.hexdigest()


def port_matrices(ring_xy, refresh=False):
    key = np.array(ring_xy, float).round(6)
    gk = _geometry_key()
    cache = CACHE if BALLS_OVERRIDE is None else CACHE.with_name(f"port_matrices_{gk[:16]}.npz")
    if cache.exists() and not refresh:
        z = np.load(cache)
        if (z["ring"].shape == key.shape and np.allclose(z["ring"], key)
                and "geometry" in z.files and str(z["geometry"]) == gk):
            return z["Gs"], z["Gr"]
    Gs, _ = reduce_sheet("supply", ring_xy)
    Gr, _ = reduce_sheet("return", ring_xy)
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, Gs=Gs, Gr=Gr, ring=key, geometry=np.array(gk))
    return Gs, Gr


# ------------------------------------------------------------------ AC solve
class Branch:
    """Two-terminal capacitor branch: z(f) = esr(f) + j w l + 1/(j w c)."""

    def __init__(self, c_f, esr_fn, l_h):
        self.c, self.esr_fn, self.l = c_f, esr_fn, l_h

    def y(self, f):
        w = 2 * np.pi * f
        return 1.0 / (self.esr_fn(np.array([f]))[0] + 1j * w * self.l + 1.0 / (1j * w * self.c))


def solve_harmonic(Gs, Gr, I_cells, f, l_loop_h, ring_branch=None, local_branch=None,
                   r_scale=1.0):
    """Node voltages and the two sheets' losses for one harmonic (f > 0) or DC (f = 0).
    Ports per sheet: [rail, N cells, nr ring]; the return rail is the reference."""
    Gs, Gr = Gs / r_scale, Gr / r_scale
    nc = len(I_cells)
    npt = Gs.shape[0]
    nr = npt - 1 - nc
    # unknowns: supply ports (npt) + return ports without the rail (npt - 1)
    n = npt + npt - 1
    Y = np.zeros((n, n), complex)
    Y[:npt, :npt] += Gs
    Y[npt:, npt:] += Gr[1:, 1:]
    J = np.zeros(n, complex)
    sc = 1 + np.arange(nc)                     # supply cell ports
    rc = npt + np.arange(nc)                   # return cell ports (rail removed)
    J[sc] -= I_cells
    J[rc] += I_cells
    if f == 0.0:
        Y[0, :] = 0.0
        Y[:, 0] = 0.0
        Y[0, 0] = 1.0                          # supply rail tied to the board node
        J[0] = 0.0
    else:
        Y[0, 0] += 1.0 / (1j * 2 * np.pi * f * l_loop_h)
        if ring_branch is not None and nr:
            y = ring_branch.y(f)
            ss = 1 + nc + np.arange(nr)
            rr = npt + nc + np.arange(nr)
            Y[ss, ss] += y
            Y[rr, rr] += y
            Y[ss, rr] -= y
            Y[rr, ss] -= y
        if local_branch is not None:
            y = local_branch.y(f)
            Y[sc, sc] += y
            Y[rc, rc] += y
            Y[sc, rc] -= y
            Y[rc, sc] -= y
    V = np.linalg.solve(Y, J)
    vs = V[:npt]
    vr = np.concatenate([[0.0], V[npt:]])
    p_s = 0.5 * float(np.real(np.conj(vs) @ Gs @ vs))
    p_r = 0.5 * float(np.real(np.conj(vr) @ Gr @ vr))
    if f == 0.0:
        p_s, p_r = 2 * p_s, 2 * p_r            # DC phasor convention
    out = {"P_sheets_W": p_s + p_r, "V_s": vs, "V_r": vr}
    if ring_branch is not None and nr and f > 0:
        dv = vs[1 + nc:] - vr[1 + nc:]
        out["I_ring"] = dv * ring_branch.y(f)
    if local_branch is not None and f > 0:
        dv = vs[sc] - vr[1:1 + nc]
        out["I_local"] = dv * local_branch.y(f)
    out["V_cell_diff"] = vs[sc] - vr[1:1 + nc]
    return out


#: Latin-square interleavings of an n x n grid: phase = (row + s col) mod n is a Latin square
#: whenever gcd(s, n) = 1; the multipliers tried per grid (7 x 7: s = 3, the round-2 design)
LATIN_S = {5: (1, 2), 6: (1, 5), 7: (3, 1, 2), 8: (1, 3)}


def grid_n():
    return int(round(math.sqrt(len(cells()))))


def phase_names():
    """The interleaving patterns defined for the grid of the design in force: rows<n>,
    latin<n>[_s<k>] (one per Latin multiplier), latin<n>z (n = 6: the Z2 x Z3 product square
    3 ((r + c) mod 2) + ((r + 2 c) mod 3)), raster<N>, spread<N> (N = n^2); and (review round
    3, more clock phases on a grid whose side is a multiple of 3 or 6) blk9 (9 phases, every
    3 x 3 block holds all nine), dual6 (12 phases: two interleaved 6-phase groups on the
    checkerboard, 30 deg apart) and dual9 (18 phases: two interleaved blk9 groups)."""
    n = grid_n()
    out = ["sync", f"rows{n}"]
    for k, s_ in enumerate(LATIN_S.get(n, (1,))):
        out.append(f"latin{n}" if k == 0 else f"latin{n}_s{s_}")
    if n == 6:
        out.append("latin6z")
    if n % 3 == 0:
        out.append("blk9")
    if n % 6 == 0:
        out += ["dual6", "dual9"]
    out += [f"raster{n * n}", f"spread{n * n}"]
    return out


#: phase count of the multi-group clock plans (phase_names)
GROUP_PLANS = {"blk9": 9, "dual6": 12, "dual9": 18}


def _spread_step(n):
    """Multiplier of the spread pattern: coprime with n^2, horizontal neighbours ~0.37 of a
    period apart (18 for 7 x 7, the round-2 value)."""
    N = n * n
    return min((k for k in range(2, N) if math.gcd(k, N) == 1),
               key=lambda k: (abs(k / N - 0.367), k))


def phases(name):
    """Per-cell switching phase (rad) on the n x n grid of the design in force, cells in
    coordinate order. Patterns: sync; rows<n> (one phase per row); latin<n>[_s<k>] ((row +
    s col) mod n, a Latin square: every row and column holds all n phases); latin6z (the
    Z2 x Z3 product Latin square, 6 x 6); raster<N> (row-major N phases); spread<N>."""
    cl = np.array(cells())
    n = grid_n()
    xs = np.unique(np.round(cl[:, 0], 6))
    ys = np.unique(np.round(cl[:, 1], 6))
    col = np.searchsorted(xs, np.round(cl[:, 0], 6))
    row = np.searchsorted(ys, np.round(cl[:, 1], 6))
    N = n * n
    if name == "sync":
        p, P = np.zeros(len(cl)), 1
    elif name == f"rows{n}":
        p, P = row, n
    elif name.startswith(f"latin{n}") and name != "latin6z":
        s_ = int(name.split("_s")[1]) if "_s" in name else LATIN_S.get(n, (1,))[0]
        if math.gcd(s_, n) != 1:
            raise ValueError(f"{name}: (row + {s_} col) mod {n} is not a Latin square")
        p, P = (row + s_ * col) % n, n
    elif name == "latin6z" and n == 6:
        p, P = 3 * ((row + col) % 2) + ((row + 2 * col) % 3), 6
    elif name in GROUP_PLANS and name in phase_names():
        b9 = 3 * ((row + col) % 3) + ((row + 2 * col) % 3)         # all 9 in every 3 x 3 block
        chk = (row + col) % 2                                       # the two groups
        p, P = {"blk9": (b9, 9), "dual6": (2 * ((row + 2 * col) % 6) + chk, 12),
                "dual9": (2 * b9 + chk, 18)}[name]
        cnt = np.bincount(np.asarray(p, int), minlength=P)
        if cnt.min() != cnt.max():
            raise ValueError(f"{name}: unequal phase use on the {n} x {n} grid {cnt.tolist()}")
    elif name == f"raster{N}":
        p, P = row * n + col, N
    elif name == f"spread{N}":
        p, P = ((row * n + col) * _spread_step(n)) % N, N
    else:
        raise ValueError(f"{name}: not a pattern of the {n} x {n} grid ({phase_names()})")
    return 2 * np.pi * np.asarray(p, float) / P


def phase_denominator(name):
    """Number of distinct phase steps of a pattern (time-domain sample counts must be
    divisible by it)."""
    n = grid_n()
    if name == "sync":
        return 1
    if name.startswith(("raster", "spread")):
        return n * n
    if name in GROUP_PLANS:
        return GROUP_PLANS[name]
    return n


def evaluate(I_harm, f_sw, l_loop_h, ring_branch=None, local_branch=None, phase="sync",
             ring_xy=None, r_scale=1.0, n_harm=128, n_t=2048):
    """Sum the harmonics: k_eq of the package network, capacitor currents and ESR losses,
    and the band-limited (<= 20 f_sw) input ripple of the worst cell."""
    ring_xy = ring_xy if ring_xy is not None else []
    Gs, Gr = port_matrices(ring_xy)
    nc = len(cells())
    ph = phases(phase)
    I0 = float(np.real(I_harm[0]))
    dc = solve_harmonic(Gs, Gr, np.full(nc, I0), 0.0, l_loop_h, r_scale=r_scale)
    p_ac, p_ring, p_loc = 0.0, 0.0, 0.0
    i2_ring = np.zeros(len(ring_xy))
    i2_loc = np.zeros(nc)
    vh = []
    for n in range(1, n_harm + 1):
        f = n * f_sw
        Ic = I_harm[n] * np.exp(-1j * n * ph)
        s = solve_harmonic(Gs, Gr, Ic, f, l_loop_h, ring_branch, local_branch, r_scale)
        p_ac += s["P_sheets_W"]
        if "I_ring" in s:
            i2 = np.abs(s["I_ring"]) ** 2 / 2
            i2_ring += i2
            p_ring += float(np.sum(i2) * ring_branch.esr_fn(np.array([f]))[0])
        if "I_local" in s:
            i2 = np.abs(s["I_local"]) ** 2 / 2
            i2_loc += i2
            p_loc += float(np.sum(i2) * local_branch.esr_fn(np.array([f]))[0])
        if n <= 20:
            vh.append(s["V_cell_diff"])
    vh = np.array(vh)                                   # (20, nc)
    t = np.arange(n_t) / n_t / f_sw
    nn = np.arange(1, vh.shape[0] + 1)
    E = np.exp(1j * 2 * np.pi * f_sw * np.outer(t, nn))
    v_t = np.real(E @ vh)                               # (n_t, nc)
    rip = v_t.max(0) - v_t.min(0)
    res = {"phase": phase, "P_DC_W": dc["P_sheets_W"], "P_AC_W": p_ac,
           "k_eq": math.sqrt((dc["P_sheets_W"] + p_ac) / dc["P_sheets_W"]),
           "R_dc_per_A2_ohm": dc["P_sheets_W"] / (nc * I0) ** 2 * r_scale,
           "ripple_pp_V_max_cell": float(rip.max()), "ripple_pp_V_mean": float(rip.mean())}
    if ring_branch is not None and len(ring_xy):
        res.update({"I_ring_rms_A_max": float(np.sqrt(i2_ring.max())),
                    "I_ring_rms_A_mean": float(np.sqrt(i2_ring.mean())),
                    "P_ring_esr_W": p_ring})
    if local_branch is not None:
        res.update({"I_local_rms_A_max": float(np.sqrt(i2_loc.max())),
                    "I_local_rms_A_mean": float(np.sqrt(i2_loc.mean())),
                    "P_local_esr_W": p_loc})
    return res


def loss_matrices(f_sw, l_loop_h, ring_branch=None, ring_xy=None, r_scale=1.0, n_harm=128,
                  local_branch=None):
    """The port model as quadratic forms (review round 3): M[n-1] (nc x nc, Hermitian) with
    the sheets' loss at harmonic n P_n = 1/2 I^H M[n-1] I for the cells' current phasors I,
    and Md with P_DC = I0^2 1^T Md 1 -- the same network, capacitors and loop inductance as
    solve_harmonic, so any clock plan is evaluated by k_eq_from without new solves."""
    ring_xy = ring_xy if ring_xy is not None else []
    Gs, Gr = port_matrices(ring_xy)
    Gs, Gr = Gs / r_scale, Gr / r_scale
    nc = len(cells())
    npt = Gs.shape[0]
    nr = npt - 1 - nc
    n = 2 * npt - 1
    sc, rc = 1 + np.arange(nc), npt + np.arange(nc)
    A = np.zeros((n, nc))
    A[sc, np.arange(nc)] = -1.0
    A[rc, np.arange(nc)] = 1.0
    G = np.zeros((n, n))
    G[:npt, :npt] += Gs
    G[npt:, npt:] += Gr[1:, 1:]
    Ms = []
    for h in range(1, n_harm + 1):
        f = h * f_sw
        Y = G.astype(complex)
        Y[0, 0] += 1.0 / (1j * 2 * np.pi * f * l_loop_h)
        for br, (p, q) in ((ring_branch, (1 + nc + np.arange(nr), npt + nc + np.arange(nr))),
                           (local_branch, (sc, rc))):
            if br is None or (br is ring_branch and not nr):
                continue
            y = br.y(f)
            Y[p, p] += y
            Y[q, q] += y
            Y[p, q] -= y
            Y[q, p] -= y
        X = np.linalg.solve(Y, A)
        M = X.conj().T @ G @ X
        Ms.append(0.5 * (M + M.conj().T))
    Yd = G.copy()
    Yd[0, :], Yd[:, 0], Yd[0, 0] = 0.0, 0.0, 1.0          # supply rail tied to the board node
    Ad = A.copy()
    Ad[0, :] = 0.0
    Xd = np.linalg.solve(Yd, Ad)
    return np.array(Ms), Xd.T @ G @ Xd


def k_eq_from(Ms, Md, I_harm, ph):
    """(k_eq, P_DC, P_AC, P_n) of the clock plan `ph` (rad per cell) on loss_matrices."""
    I0 = float(np.real(I_harm[0]))
    one = np.ones(len(ph))
    p_dc = float(one @ Md @ one) * I0 ** 2
    per = np.array([0.5 * float(np.real(np.conj(v) @ Ms[h - 1] @ v))
                    for h in range(1, len(Ms) + 1)
                    for v in (I_harm[h] * np.exp(-1j * h * np.asarray(ph)),)])
    return math.sqrt((p_dc + per.sum()) / p_dc), p_dc, float(per.sum()), per


def ball_rms(I_harm, f_sw, l_loop_h, ring_branch=None, phase="sync", ring_xy=None,
             r_scale=1.0, n_harm=128):
    """RMS current of every BGA ball over DC and the harmonics, on the same reduced network
    and port solution as evaluate() (each ball's current from its sheet-side node voltage,
    recovered by Kron back-substitution, and its conductance). The ball-level counterpart of
    k_eq: k_eq is LOSS-equivalent over the whole network, and with the cells interleaved most
    of its AC part circulates cell to cell in the sheets rather than through the balls.
    TCPMT round 3: a diagnostic recorded beside the count closure, which still takes
    k_eq x I as the production ball current."""
    ring_xy = ring_xy if ring_xy is not None else []
    Gs, Gr = port_matrices(ring_xy)
    maps = {rail: reduce_sheet(rail, ring_xy)[1] for rail in ("supply", "return")}
    nc = len(cells())
    ph = phases(phase)
    I0 = float(np.real(I_harm[0]))

    def currents(s):
        out = {}
        for rail, V in (("supply", s["V_s"]), ("return", s["V_r"])):
            m = maps[rail]
            out[rail] = (m["g_ball_S"] / r_scale) * (V[0] - m["ball_map"] @ V)
        return out
    dc = currents(solve_harmonic(Gs, Gr, np.full(nc, I0), 0.0, l_loop_h, r_scale=r_scale))
    i2 = {r: np.abs(v) ** 2 for r, v in dc.items()}
    ac2 = {r: np.zeros(len(v)) for r, v in dc.items()}
    for n in range(1, n_harm + 1):
        Ic = I_harm[n] * np.exp(-1j * n * ph)
        c = currents(solve_harmonic(Gs, Gr, Ic, n * f_sw, l_loop_h, ring_branch, None,
                                    r_scale))
        for r in c:
            ac2[r] += np.abs(c[r]) ** 2 / 2
    res = {"I_total_dc_A": nc * I0}
    for r in dc:
        tot = i2[r] + ac2[r]
        j = int(np.argmax(tot))
        res[r] = {"n_balls": int(len(tot)), "sum_dc_A": float(np.real(np.sum(dc[r]))),
                  "I_dc_max_A": float(np.sqrt(i2[r].max())),
                  "I_rms_max_A": float(np.sqrt(tot.max())),
                  "k_ball_at_max": float(np.sqrt(tot[j] / i2[r][j])) if i2[r][j] > 0 else None,
                  "I_ac_rms_max_A": float(np.sqrt(ac2[r].max())),
                  "peak_fraction_dc": float(np.sqrt(i2[r].max()) / (nc * I0))}
    res["I_rms_max_A"] = max(res[r]["I_rms_max_A"] for r in dc)
    return res


def td_verify(i_period, f_sw, l_loop_h, c_ring, esr_ring, l_ring, phase=None,
              periods=20, r_scale=1.0, ring_xy=None):
    """Time-domain check of the port model: trapezoidal MNA on the reduced sheets with the
    board inductor (rail -> board node) and every ring branch (series ESR-L-C, constant ESR)
    as companion models, the cells as phase-shifted current sources. Returns the
    loss-equivalent k of the sheets over the last period. `i_period` must have a sample count
    divisible by the phase denominator (phase_denominator) so the shifts are exact."""
    ring_xy = ring_xy if ring_xy is not None else ring_layout()[0]
    phase = phase or f"latin{grid_n()}"
    Gs, Gr = port_matrices(ring_xy)
    Gs, Gr = Gs / r_scale, Gr / r_scale
    nc = len(cells())
    npt = Gs.shape[0]
    nr = npt - 1 - nc
    n = 2 * npt - 1
    n_t = len(i_period)
    dt = 1.0 / f_sw / n_t
    Y = np.zeros((n, n))
    Y[:npt, :npt] += Gs
    Y[npt:, npt:] += Gr[1:, 1:]
    gL = dt / (2.0 * l_loop_h)
    Y[0, 0] += gL
    geq = 1.0 / (esr_ring + 2.0 * l_ring / dt + dt / (2.0 * c_ring))
    ss = 1 + nc + np.arange(nr)
    rr = npt + nc + np.arange(nr)
    Y[ss, ss] += geq
    Y[rr, rr] += geq
    Y[ss, rr] -= geq
    Y[rr, ss] -= geq
    import scipy.linalg as sla
    lu = sla.lu_factor(Y)
    sc = 1 + np.arange(nc)
    rc = npt + np.arange(nc)
    shift = np.round(phases(phase) / (2 * np.pi) * n_t).astype(int)
    I0 = float(np.mean(i_period))
    # DC operating point: rail tied, rings open
    dc = solve_harmonic(Gs * r_scale, Gr * r_scale, np.full(nc, I0), 0.0, l_loop_h,
                        r_scale=r_scale)
    vs, vr = dc["V_s"].real, dc["V_r"].real
    V = np.concatenate([vs, vr[1:]])
    i_b = nc * I0
    i_k = np.zeros(nr)
    v_c = vs[1 + nc:] - vr[1 + nc:]
    v_l = np.zeros(nr)
    p_last = np.empty(n_t)
    for p in range(periods):
        for k in range(n_t):
            J = np.zeros(n)
            icell = i_period[(k + 1 - shift) % n_t]
            J[sc] -= icell
            J[rc] += icell
            J[0] += i_b - gL * V[0]                      # inductor history (into the rail)
            hist = -(2 * l_ring / dt) * i_k - v_l + v_c + (dt / (2 * c_ring)) * i_k
            J[ss] += geq * hist                          # series RLC companion
            J[rr] -= geq * hist
            Vn = sla.lu_solve(lu, J)
            dv = Vn[ss] - Vn[rr]
            i_new = geq * (dv - hist)
            v_c_new = v_c + (dt / (2 * c_ring)) * (i_new + i_k)
            v_l = (2 * l_ring / dt) * (i_new - i_k) - v_l
            i_b = i_b - gL * (V[0] + Vn[0])
            i_k, v_c, V = i_new, v_c_new, Vn
            if p == periods - 1:
                vs_t = V[:npt]
                vr_t = np.concatenate([[0.0], V[npt:]])
                p_last[k] = float(vs_t @ Gs @ vs_t + vr_t @ Gr @ vr_t)
    return {"k_eq_td": math.sqrt(float(np.mean(p_last)) / dc["P_sheets_W"]),
            "P_DC_W": dc["P_sheets_W"], "P_mean_W": float(np.mean(p_last)),
            "dt_ns": dt * 1e9, "periods": periods}


def self_check():
    """DC resistance of the reduced sheets against package_network.json, and k_eq = k_open
    with no capacitors (all cells in phase)."""
    pn = json.loads(NETWORK.read_text())["loop"]["Z1"]
    xy, _ = ring_layout()
    Gs, Gr = port_matrices(xy)
    nc = len(cells())
    dc = solve_harmonic(Gs, Gr, np.full(nc, 1.0 / nc), 0.0, 1e-10)
    return {"R_loop_reduced_ohm": dc["P_sheets_W"], "R_loop_package_network_ohm":
            pn["r_loop_ohm"], "rel_diff": dc["P_sheets_W"] / pn["r_loop_ohm"] - 1.0,
            "note": f"level {LEVEL} reduction vs the level-3 converged production value"}


if __name__ == "__main__":
    print(json.dumps(ring_layout()[1]))
    print(json.dumps(self_check(), default=float))
