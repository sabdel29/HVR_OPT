"""Phase-0E: physical metal stack, multilayer VDD/GND RDL, and TSV allocation.

THREE CORRECTIONS TO PHASE 0D-R
  1. The RDL sheet is no longer a single assumed layer. `RDLStack` carries an explicit
     per-layer VDD/GND metal stack whose occupancy is DERIVED from the line/space design
     rule rather than assumed, and the loop is solved as VDD + load + GND return instead of
     multiplying the supply loss by two.
  2. `n_required`, `n_allocated` and `n_available` are separate quantities. Electrical
     resistance uses n_ALLOCATED. Phase 0D-R divided by n_required, which silently made
     P_TSV proportional to I -- that is a consequence of one allocation POLICY, not a law.
  3. The per-via current limit is expressed as J * A_conductor with J taken from a
     source-backed envelope, and feasibility is reported as a map over J rather than as a
     single verdict.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve

REPO = Path(__file__).resolve().parents[2]
CFG = REPO / "configs" / "phase0e" / "physical_stack.yaml"

RHO_CU_20C = 17.0e-9
ALPHA_CU = 3.93e-3


def load_cfg(path: Path | None = None) -> dict:
    return yaml.safe_load((path or CFG).read_text())


def rho_cu(T_c: float) -> float:
    return RHO_CU_20C * (1.0 + ALPHA_CU * (T_c - 20.0))


# ---------------------------------------------------------------------------
# metal stack
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RDLStack:
    """A physical redistribution stack: N_VDD + N_GND metal layers of stated thickness,
    with metal occupancy DERIVED from the line/space rule (not assumed)."""
    name: str
    t_cu_m: float
    n_vdd: int
    n_gnd: int
    width_m: float | None = None
    space_m: float | None = None
    occupancy_override: float | None = None
    status: str = "ASSUMPTION"

    @property
    def occupancy(self) -> float:
        if self.occupancy_override is not None:
            return self.occupancy_override
        if self.width_m is None or self.space_m is None:
            raise ValueError(f"{self.name}: need line/space or an explicit occupancy")
        return self.width_m / (self.width_m + self.space_m)

    def sigma_s_layer(self, T_c: float = 20.0) -> float:
        """Sheet conductance of ONE metal layer [S per square]."""
        return self.t_cu_m * self.occupancy / rho_cu(T_c)

    def sigma_s_net(self, net: str, T_c: float = 20.0) -> float:
        """Sheet conductance of a whole network, assuming ideal inter-layer stitching."""
        n = self.n_vdd if net == "vdd" else self.n_gnd
        return n * self.sigma_s_layer(T_c)

    def r_sheet_net(self, net: str, T_c: float = 20.0) -> float:
        s = self.sigma_s_net(net, T_c)
        return float("inf") if s <= 0 else 1.0 / s

    # --- the source's own analytic form, used as an independent cross-check -----------
    def ectc_r_h_eff(self, area_l_m2: float, T_c: float = 20.0, net: str = "vdd") -> float:
        """ECTC-2024 eq. (1): R'_Heff = (R/l) / (n * N_Hmax), N_Hmax = sqrt(A_L)/(W+S)."""
        if self.width_m is None:
            raise ValueError("analytic form needs a line/space rule")
        r_per_l = rho_cu(T_c) / (self.width_m * self.t_cu_m)
        n_hmax = math.sqrt(area_l_m2) / (self.width_m + self.space_m)
        n = self.n_vdd if net == "vdd" else self.n_gnd
        return r_per_l / (n * n_hmax)


def stacks_from_cfg(cfg: dict | None = None) -> dict[str, RDLStack]:
    c = cfg or load_cfg()
    out = {}
    for k, s in c["rdl_stacks"].items():
        out[k] = RDLStack(name=k, t_cu_m=s["t_cu_m"], n_vdd=s["n_vdd"], n_gnd=s["n_gnd"],
                          width_m=s.get("width_m"), space_m=s.get("space_m"),
                          occupancy_override=s.get("occupancy_override"),
                          status=s.get("status", "ASSUMPTION"))
    return out


# ---------------------------------------------------------------------------
# TSV / bump allocation:  n_required <= n_allocated <= n_available
# ---------------------------------------------------------------------------

class Infeasible(Exception):
    """n_required exceeds n_available: the connection cannot be built in the footprint."""


@dataclass
class Allocation:
    tier: str
    current_a: float
    i_max_per_via_a: float
    n_required: int
    n_available: int
    n_allocated: int
    policy: str
    j_a_per_m2: float
    j_actual_a_per_m2: float
    feasible: bool
    reason: str = ""

    @property
    def utilisation(self) -> float:
        """n_required / n_available: 1.0 means the via field is exactly saturated."""
        return self.n_required / self.n_available if self.n_available else float("inf")


def i_max_per_via(area_m2: float, j_a_per_m2: float) -> float:
    """The source's own provisioning rule inverted: I_via = J * A_conductor."""
    return j_a_per_m2 * area_m2


def n_required(current_a: float, i_max_a: float) -> int:
    if i_max_a <= 0:
        raise ValueError("per-via current limit must be positive")
    return max(1, math.ceil(abs(current_a) / i_max_a))


def n_available(footprint_m2: float, pitch_m: float, pg_fraction: float = 1.0) -> int:
    return max(1, int(footprint_m2 * pg_fraction / (pitch_m * pitch_m)))


def allocate(tier: str, current_a: float, area_m2: float, pitch_m: float,
             footprint_m2: float, j_a_per_m2: float, policy: str = "A_min_capability",
             pg_fraction: float = 0.5, strict: bool = True) -> Allocation:
    """Separate the three counts and choose n_allocated by an explicit POLICY.

    Policy A reproduces the June framework ("the number of parallel VICs per connection is
    sized based on the connection current and per-via current limit"). Policy B provisions
    geometrically and is INDEPENDENT of current, which breaks the apparent P ~ I law.
    """
    imax = i_max_per_via(area_m2, j_a_per_m2)
    nreq = n_required(current_a, imax)
    navail = n_available(footprint_m2, pitch_m)
    feasible = nreq <= navail
    if not feasible and strict:
        raise Infeasible(
            f"{tier}: needs {nreq} vias for {current_a:.3f} A at {imax*1e3:.1f} mA/via "
            f"but only {navail} sites exist at {pitch_m*1e6:.0f} um pitch")

    if policy == "A_min_capability":
        nalloc = nreq
    elif policy == "B_geometric":
        nalloc = max(nreq, n_available(footprint_m2, pitch_m, pg_fraction))
    elif policy == "C_area_optimal":
        nalloc = navail                      # loss is monotone decreasing in n_alloc
    else:
        raise ValueError(f"unknown allocation policy {policy!r}")
    nalloc = min(max(nalloc, nreq), navail) if feasible else nreq

    return Allocation(tier, current_a, imax, nreq, navail, nalloc, policy, j_a_per_m2,
                      abs(current_a) / (nalloc * area_m2), feasible,
                      "" if feasible else f"n_req {nreq} > n_avail {navail}")


def r_field(r_single_ohm: float, alloc: Allocation) -> float:
    """Electrical resistance of the via FIELD. Uses n_ALLOCATED, never n_required."""
    return r_single_ohm / alloc.n_allocated


# ---------------------------------------------------------------------------
# coupled multilayer VDD / GND resistive network
# ---------------------------------------------------------------------------

def _lap_indices(nlay: int, n: int):
    return lambda L, i, j: L * n * n + i * n + j


def multilayer_sheet_solve(sigma_per_layer: list[float], src_xy, src_i, load_xy, load_i,
                           span_mm: float, n: int = 61, src_size_mm: float = 0.0,
                           load_size_mm: float = 0.0, stitch_s_per_node: float | None = None,
                           inject_layer: int = 0, extract_layer: int | None = None,
                           ground_xy: tuple[float, float] | None = None,
                           ground_size_mm: float = 0.0) -> dict:
    """Coupled L-layer resistive network.

    Each layer is a 2-D sheet of conductance `sigma_per_layer[L]`; adjacent layers are tied
    at every node by `stitch_s_per_node` (None = ideal stitching, which collapses exactly to
    a single sheet of conductance sum(sigma) -- that limit is unit-tested).

    Current is injected into `inject_layer` and extracted from `extract_layer`, so a stack
    whose layers are poorly stitched correctly shows the extra vertical drop.
    """
    L = len(sigma_per_layer)
    if L < 1:
        raise ValueError("need at least one metal layer")
    extract_layer = L - 1 if extract_layer is None else extract_layer
    N = L * n * n
    idx = _lap_indices(L, n)
    h = span_mm / (n - 1)

    rows, cols, vals = [], [], []
    diag = np.zeros(N)

    for lay in range(L):
        g = sigma_per_layer[lay]
        for i in range(n):
            for j in range(n):
                k = idx(lay, i, j)
                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ii, jj = i + di, j + dj
                    if 0 <= ii < n and 0 <= jj < n:
                        diag[k] += g
                        rows.append(k); cols.append(idx(lay, ii, jj)); vals.append(-g)

    if L > 1:
        gv = float("inf") if stitch_s_per_node is None else stitch_s_per_node
        if math.isinf(gv):
            gv = 1e6 * max(sigma_per_layer)          # numerically "ideal"
        for lay in range(L - 1):
            for i in range(n):
                for j in range(n):
                    a, b = idx(lay, i, j), idx(lay + 1, i, j)
                    diag[a] += gv; diag[b] += gv
                    rows.append(a); cols.append(b); vals.append(-gv)
                    rows.append(b); cols.append(a); vals.append(-gv)

    for k in range(N):
        rows.append(k); cols.append(k); vals.append(diag[k])

    def spread(xy, I, size_mm, lay):
        """Exact cell-overlap area weighting (Phase-0D-R fix, retained)."""
        x, y = xy
        if size_mm <= 0:
            i = int(np.clip(round((x + span_mm / 2) / span_mm * (n - 1)), 0, n - 1))
            j = int(np.clip(round((y + span_mm / 2) / span_mm * (n - 1)), 0, n - 1))
            return {idx(lay, i, j): I}
        x0, x1 = x - size_mm / 2, x + size_mm / 2
        y0, y1 = y - size_mm / 2, y + size_mm / 2
        w, tot = {}, 0.0
        for i in range(n):
            xc = -span_mm / 2 + i * h
            ox = max(0.0, min(xc + h / 2, x1) - max(xc - h / 2, x0))
            if ox <= 0:
                continue
            for j in range(n):
                yc = -span_mm / 2 + j * h
                oy = max(0.0, min(yc + h / 2, y1) - max(yc - h / 2, y0))
                if oy <= 0:
                    continue
                a = ox * oy
                w[idx(lay, i, j)] = w.get(idx(lay, i, j), 0.0) + a
                tot += a
        if tot <= 0:
            i = int(np.clip(round((x + span_mm / 2) / span_mm * (n - 1)), 0, n - 1))
            j = int(np.clip(round((y + span_mm / 2) / span_mm * (n - 1)), 0, n - 1))
            return {idx(lay, i, j): I}
        return {k: I * a / tot for k, a in w.items()}

    b = np.zeros(N)
    for xy, I in zip(src_xy, src_i):
        for k, v in spread(xy, I, src_size_mm, inject_layer).items():
            b[k] += v
    for xy, I in zip(load_xy, load_i):
        for k, v in spread(xy, I, load_size_mm, extract_layer).items():
            b[k] -= v

    # Reference potential. A SINGLE pinned node discards that node's prescribed current,
    # and the size of that discarded share depends on the mesh (0.037 A at n=81 vs 0.006 A
    # at n=201), so two solvers pinned at a point disagree by a mesh-dependent amount.
    # Grounding a finite footprint -- physically, one POL contact pad held at the reference
    # -- removes both the point singularity and the mesh dependence.
    mid = ground_xy if ground_xy is not None else load_xy[len(load_xy) // 2]
    if ground_size_mm > 0:
        half = ground_size_mm / 2
        gnd = set()
        for i in range(n):
            xc = -span_mm / 2 + i * h
            if abs(xc - mid[0]) > half:
                continue
            for j in range(n):
                yc = -span_mm / 2 + j * h
                if abs(yc - mid[1]) <= half:
                    gnd.add(idx(extract_layer, i, j))
        if not gnd:
            gnd = {idx(extract_layer,
                       int(np.clip(round((mid[0] + span_mm / 2) / span_mm * (n - 1)), 0, n - 1)),
                       int(np.clip(round((mid[1] + span_mm / 2) / span_mm * (n - 1)), 0, n - 1)))}
    else:
        gi = int(np.clip(round((mid[0] + span_mm / 2) / span_mm * (n - 1)), 0, n - 1))
        gj = int(np.clip(round((mid[1] + span_mm / 2) / span_mm * (n - 1)), 0, n - 1))
        gnd = {idx(extract_layer, gi, gj)}

    ri, ci, va = [], [], []
    for r_, c_, v_ in zip(rows, cols, vals):
        if r_ in gnd:
            continue
        ri.append(r_); ci.append(c_); va.append(v_)
    for k in gnd:
        ri.append(k); ci.append(k); va.append(1.0); b[k] = 0.0

    V = spsolve(coo_matrix((va, (ri, ci)), shape=(N, N)).tocsr(), b)

    p_lat = 0.0
    for lay in range(L):
        g = sigma_per_layer[lay]
        for i in range(n):
            for j in range(n):
                k = idx(lay, i, j)
                for di, dj in ((1, 0), (0, 1)):
                    ii, jj = i + di, j + dj
                    if ii < n and jj < n:
                        p_lat += g * (V[k] - V[idx(lay, ii, jj)]) ** 2
    p_iv = float(b @ V)
    return {"p_w": p_lat, "p_iv_check_w": p_iv,
            "balance_err_pct": 100 * abs(p_lat - p_iv) / max(abs(p_iv), 1e-30),
            "dv_span_v": float(V.max() - V.min()), "n_layers": L, "grid_n": n,
            "sigma_per_layer": list(sigma_per_layer)}


def rdl_network_solve(stack: RDLStack, src_xy, src_i, load_xy, load_i, span_mm: float,
                      T_c: float = 20.0, n: int = 61, src_size_mm: float = 0.0,
                      load_size_mm: float = 0.0, stitch_s_per_node: float | None = None,
                      ground_xy=None, ground_size_mm: float = 0.0) -> dict:
    """Solve the full power loop: VDD network + load + GND return network.

    Phase 0D-R multiplied the supply loss by 2. That is only correct when the ground network
    is identical to the supply network. Here each network is solved with its OWN layer count
    and conductance, so an asymmetric stack gives an asymmetric split.
    """
    out = {}
    tot = 0.0
    for net in ("vdd", "gnd"):
        nl = stack.n_vdd if net == "vdd" else stack.n_gnd
        if nl <= 0:
            out[net] = {"p_w": 0.0, "n_layers": 0, "skipped": "no layers in this network"}
            continue
        sig = [stack.sigma_s_layer(T_c)] * nl
        r = multilayer_sheet_solve(sig, src_xy, src_i, load_xy, load_i, span_mm, n=n,
                                   src_size_mm=src_size_mm, load_size_mm=load_size_mm,
                                   stitch_s_per_node=stitch_s_per_node,
                                   ground_xy=ground_xy, ground_size_mm=ground_size_mm)
        out[net] = r
        tot += r["p_w"]
    out["p_loop_w"] = tot
    out["p_vdd_w"] = out["vdd"]["p_w"]
    out["p_gnd_w"] = out["gnd"]["p_w"]
    out["symmetric_return_would_give_w"] = 2.0 * out["vdd"]["p_w"]
    out["stack"] = stack.name
    out["r_sheet_vdd_ohm_sq"] = stack.r_sheet_net("vdd", T_c)
    out["r_sheet_gnd_ohm_sq"] = stack.r_sheet_net("gnd", T_c)
    return out
