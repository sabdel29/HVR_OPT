"""Phase-0D-R: architecture-aware package power-distribution network.

Corrects three Phase-0D deficiencies:
  1. rail assignment was global ("TSV carries input"); it is now derived per segment from
     where conversion sits in the physical stack;
  2. only TSV + a lumped lateral term were modelled; BGA, C4, TSV, microbump and RDL are now
     modelled separately, each with its own geometry, shape and temperature dependence;
  3. the ground return was omitted entirely; R_loop = R_supply + R_ground is now enforced.

Feasibility is a hard gate: if the required parallel count exceeds what the footprint can
hold, the architecture is INFEASIBLE. It is never silently clipped.
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
CFG = REPO / "configs" / "phase0dr" / "power_path_graphs.yaml"


def load_paths(path: Path | None = None) -> dict:
    return yaml.safe_load((path or CFG).read_text())


def _v(node):
    return node["value"] if isinstance(node, dict) and "value" in node else node


class Infeasible(Exception):
    """Raised when a tier cannot carry its current within the available footprint."""


# ---------------------------------------------------------------------------
# tier resistance
# ---------------------------------------------------------------------------

def tier_area_m2(tier: dict) -> float:
    """Cross-section area. Shape matters: June-2026 uses circular BGA/TSV but a SQUARE
    10x10 um chiplet pad (100 um^2 reproduces their 1.7 mOhm exactly)."""
    d = _v(tier["d_m"])
    return (d * d) if tier.get("shape") == "square" else (math.pi * d * d / 4.0)


def rho_at(tier: dict, T_c: float, T_ref: float = 20.0) -> float:
    return _v(tier["rho_20c"]) * (1.0 + _v(tier["alpha"]) * (T_c - T_ref))


def r_single(tier: dict, T_c: float, h_m: float | None = None) -> float:
    h = h_m if h_m is not None else _v(tier["h_m"])
    if h is None or h <= 0:
        raise ValueError("segment length must be positive")
    r = rho_at(tier, T_c) * h / tier_area_m2(tier)
    return r + _v(tier.get("r_contact_ohm", 0.0) or 0.0)


def n_available(tier: dict, footprint_mm2: float) -> int:
    p = _v(tier["pitch_m"])
    return max(1, int(footprint_mm2 * 1e-6 / (p * p)))


def n_required(tier: dict, current_a: float) -> int:
    imax = _v(tier["i_max_a"])
    return max(1, math.ceil(abs(current_a) / imax)) if current_a else 1


@dataclass
class SegmentLoss:
    seg_id: str
    tier: str
    rail: str
    current_a: float
    n_required: int
    n_available: int
    r_single_ohm: float
    r_supply_ohm: float
    r_loop_ohm: float
    p_loss_w: float
    dv_v: float
    length_m: float
    heat_region: str


def vertical_segment(seg_id: str, tier_name: str, tier: dict, rail: str, current_a: float,
                     footprint_mm2: float, T_c: float, h_m: float | None,
                     heat_region: str, n_vr: int = 1) -> SegmentLoss:
    """One vertical tier, supply + identical ground return."""
    navail = n_available(tier, footprint_mm2)
    nreq = n_required(tier, current_a)
    if nreq > navail:
        raise Infeasible(
            f"{seg_id}/{tier_name}: needs {nreq} parallel conductors for {current_a:.3f} A "
            f"but the {footprint_mm2:.2f} mm^2 footprint holds only {navail} at "
            f"{_v(tier['pitch_m'])*1e6:.0f} um pitch")
    rs = r_single(tier, T_c, h_m)
    r_supply = rs / nreq
    r_loop = 2.0 * r_supply                      # supply + identical ground return
    p = current_a ** 2 * r_loop
    return SegmentLoss(seg_id, tier_name, rail, current_a, nreq, navail, rs, r_supply,
                       r_loop, p, current_a * r_loop, h_m if h_m is not None else _v(tier["h_m"]),
                       heat_region)


# ---------------------------------------------------------------------------
# 2-D resistive-sheet RDL solver
# ---------------------------------------------------------------------------

def rdl_sheet_solve(src_xy, src_i, load_xy, load_i, tier: dict, T_c: float,
                    span_mm: float, n: int = 61, src_size_mm: float = 0.0,
                    load_size_mm: float = 0.0, ground: str = "load") -> dict:
    """Finite-difference 2-D resistive sheet on a uniform n x n grid.

        div( sigma_s grad V ) = -J        sigma_s = t_cu * occupancy / rho(T)

    Sources INJECT over a finite footprint (`src_size_mm`), loads EXTRACT. Finite-area
    injection matters: a point source in a 2-D sheet has a logarithmically singular
    potential, so its value and the local dissipation are mesh-dependent in ANY solver.
    A real VR injects over its tile footprint (several mm^2), which removes the singularity.
    Validated against MOOSE (see results/phase0dr/rdl_validation.json).

    Replaces the Phase-0D lumped `R_per_mm = rho/(t*W_die)`, which assumed the full die width
    conducts independently for every source-load pair and therefore had no current sharing.
    """
    t_cu = _v(tier["t_cu_m"])
    occ = _v(tier["metal_occupancy"])
    rho = rho_at(tier, T_c)
    sigma_s = t_cu * occ / rho

    N = n * n
    idx = lambda i, j: i * n + j
    g = sigma_s
    h = span_mm / (n - 1)

    rows_i, cols_i, vals = [], [], []
    b = np.zeros(N)
    for i in range(n):
        for j in range(n):
            k = idx(i, j)
            d = 0.0
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ii, jj = i + di, j + dj
                if 0 <= ii < n and 0 <= jj < n:
                    d += g
                    rows_i.append(k); cols_i.append(idx(ii, jj)); vals.append(-g)
            rows_i.append(k); cols_i.append(k); vals.append(d)

    def node(xy):
        x, y = xy
        i = int(np.clip(round((x + span_mm / 2) / span_mm * (n - 1)), 0, n - 1))
        j = int(np.clip(round((y + span_mm / 2) / span_mm * (n - 1)), 0, n - 1))
        return i, j

    def spread(xy, I, size_mm):
        """Distribute I over a square footprint using EXACT CELL-OVERLAP AREA weights.

        Nearest-cell assignment makes the injected footprint snap to the grid, which
        introduces a discontinuous O(h) error and destroys grid convergence. Weighting by
        the true overlap of the footprint with each node's control area removes it.
        """
        x, y = xy
        if size_mm <= 0:
            i = int(np.clip(round((x + span_mm / 2) / span_mm * (n - 1)), 0, n - 1))
            j = int(np.clip(round((y + span_mm / 2) / span_mm * (n - 1)), 0, n - 1))
            return {idx(i, j): I}
        x0, x1 = x - size_mm / 2, x + size_mm / 2
        y0, y1 = y - size_mm / 2, y + size_mm / 2
        w = {}
        tot = 0.0
        for i in range(n):
            xc = -span_mm / 2 + i * h
            cx0, cx1 = xc - h / 2, xc + h / 2      # node control cell
            ox = max(0.0, min(cx1, x1) - max(cx0, x0))
            if ox <= 0:
                continue
            for j in range(n):
                yc = -span_mm / 2 + j * h
                cy0, cy1 = yc - h / 2, yc + h / 2
                oy = max(0.0, min(cy1, y1) - max(cy0, y0))
                if oy <= 0:
                    continue
                a = ox * oy
                w[idx(i, j)] = w.get(idx(i, j), 0.0) + a
                tot += a
        if tot <= 0:
            i = int(np.clip(round((x + span_mm / 2) / span_mm * (n - 1)), 0, n - 1))
            j = int(np.clip(round((y + span_mm / 2) / span_mm * (n - 1)), 0, n - 1))
            return {idx(i, j): I}
        return {k: I * a / tot for k, a in w.items()}

    for xy, I in zip(src_xy, src_i):
        for k, v in spread(xy, I, src_size_mm).items():
            b[k] += v
    for xy, I in zip(load_xy, load_i):
        for k, v in spread(xy, I, load_size_mm).items():
            b[k] -= v

    gnd = ([idx(0, j) for j in range(n)] if ground == "left_edge"
           else [idx(*node(load_xy[len(load_xy) // 2]))])
    gset = set(gnd)
    ri, ci, va = [], [], []
    for r_, c_, v_ in zip(rows_i, cols_i, vals):
        if r_ in gset:
            continue
        ri.append(r_); ci.append(c_); va.append(v_)
    for k in gnd:
        ri.append(k); ci.append(k); va.append(1.0)
        b[k] = 0.0
    A = coo_matrix((va, (ri, ci)), shape=(N, N)).tocsr()
    V = spsolve(A, b)

    p_res = 0.0
    for i in range(n):
        for j in range(n):
            k = idx(i, j)
            for di, dj in ((1, 0), (0, 1)):
                ii, jj = i + di, j + dj
                if ii < n and jj < n:
                    p_res += g * (V[k] - V[idx(ii, jj)]) ** 2
    p_iv = float(b @ V)

    return {"p_supply_w": p_res, "p_loop_w": 2.0 * p_res,
            "p_iv_check_w": p_iv,
            "balance_err_pct": 100 * abs(p_res - p_iv) / max(abs(p_iv), 1e-30),
            "v_max": float(V.max()), "v_min": float(V.min()),
            "dv_span_v": float(V.max() - V.min()), "sheet_conductance_S": sigma_s,
            "r_sheet_ohm_sq": 1.0 / sigma_s, "grid_n": n,
            "src_size_mm": src_size_mm, "load_size_mm": load_size_mm}


# ---------------------------------------------------------------------------
# architecture evaluation
# ---------------------------------------------------------------------------

def rail_currents(i_out_per_vr: float, v_in: float, v_out: float, p_conv_per_vr: float) -> dict:
    """Never assume ideal conversion: P_in = V_out*I_out + P_conv."""
    p_out = v_out * i_out_per_vr
    p_in = p_out + p_conv_per_vr
    return {"I_out_a": i_out_per_vr, "I_in_a": p_in / v_in,
            "P_out_w": p_out, "P_in_w": p_in,
            "eta_stage": p_out / p_in if p_in else float("nan")}
