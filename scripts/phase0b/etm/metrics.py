"""Metric extraction with explicit singularity regularization.

The spec forbids reporting a single pathological corner element as the scientific
result. Every stress metric is therefore reported THREE ways:
    raw_max  - the unregularized nodal maximum (diagnostic only)
    p99      - 99th percentile over the region (headline metric)
    p95      - 95th percentile (robustness check)
Material-specific metrics are evaluated only on nodes INTERIOR to that material
(nodes touched exclusively by elements of that material), so interface averaging
does not contaminate a bulk metric.
"""
from __future__ import annotations

import numpy as np

from .mesh import Mesh


def interior_nodes(m: Mesh, material: str) -> np.ndarray:
    """Nodes touched only by elements of `material` (1-based)."""
    inside = np.zeros(m.n_nodes + 1, bool)
    outside = np.zeros(m.n_nodes + 1, bool)
    sel = m.elem_material == material
    for row in m.elems[sel]:
        inside[row] = True
    for row in m.elems[~sel]:
        outside[row] = True
    return np.nonzero(inside & ~outside)[0]


def region_nodes(m: Mesh, material: str) -> np.ndarray:
    inside = np.zeros(m.n_nodes + 1, bool)
    for row in m.elems[m.elem_material == material]:
        inside[row] = True
    return np.nonzero(inside)[0]


def principal_max(S: np.ndarray) -> np.ndarray:
    """Maximum principal stress from (N,6) [sxx,syy,szz,sxy,syz,szx]."""
    n = len(S)
    T = np.zeros((n, 3, 3))
    T[:, 0, 0], T[:, 1, 1], T[:, 2, 2] = S[:, 0], S[:, 1], S[:, 2]
    T[:, 0, 1] = T[:, 1, 0] = S[:, 3]
    T[:, 1, 2] = T[:, 2, 1] = S[:, 4]
    T[:, 0, 2] = T[:, 2, 0] = S[:, 5]
    return np.linalg.eigvalsh(T)[:, -1]


def von_mises(S: np.ndarray) -> np.ndarray:
    sxx, syy, szz, sxy, syz, szx = S.T
    return np.sqrt(0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
                   + 3.0 * (sxy ** 2 + syz ** 2 + szx ** 2))


def _band(v: np.ndarray) -> dict:
    v = v[np.isfinite(v)]
    if v.size == 0:
        return {"raw_max": float("nan"), "p99": float("nan"), "p95": float("nan"), "n": 0}
    return {"raw_max": float(v.max()), "p99": float(np.percentile(v, 99)),
            "p95": float(np.percentile(v, 95)), "n": int(v.size)}


def thermal_metrics(m: Mesh, T: np.ndarray, films: dict, stack: dict,
                    p_in: float, h_top: float) -> dict:
    """Thermal metrics plus a mandatory energy-balance check.

    Q_out is the Robin flux integrated over both cooled surfaces:
        Q = sum_faces  h[W/(mm^2 K)] * A[mm^2] * (T_face - T_sink)
    A converged steady-state solution must return Q_out == Q_in.
    """
    from .ccxio import face_area
    from .config import W_M2K_TO_W_MM2K

    tb = stack["thermal_bc"]
    t_cool, t_amb = tb["coolant_temp"]["value"], tb["ambient_bottom"]["value"]
    h_bot = tb["h_bottom"]["value"]
    h_top_mm, h_bot_mm = h_top * W_M2K_TO_W_MM2K, h_bot * W_M2K_TO_W_MM2K

    nt = T[1:m.n_nodes + 1, 0]
    imax = int(np.nanargmax(nt))

    q_out = 0.0
    for e in films["top_face_elems"]:
        f = m.elems[e - 1][4:]                     # top face node ids
        q_out += h_top_mm * face_area(m, e) * (float(np.nanmean(T[f, 0])) - t_cool)
    for e in films["bot_face_elems"]:
        f = m.elems[e - 1][:4]                     # bottom face node ids
        q_out += h_bot_mm * face_area(m, e) * (float(np.nanmean(T[f, 0])) - t_amb)

    return {
        "T_max_C": float(np.nanmax(nt)), "T_min_C": float(np.nanmin(nt)),
        "T_mean_C": float(np.nanmean(nt)),
        "hotspot_xyz_mm": [round(v, 4) for v in m.nodes[imax].tolist()],
        "Q_in_W": float(p_in), "Q_out_W": float(q_out),
        "energy_residual_pct": float(100.0 * (q_out - p_in) / p_in),
    }


def structural_metrics(m: Mesh, U: np.ndarray, S: np.ndarray, stack: dict) -> dict:
    g = stack["geometry"]
    Dx = g["functional_die"]["size_x"]["value"]

    uz = U[1:m.n_nodes + 1, 2]
    # Warpage planes referenced by NAME, never by layer index: the layer stack gains a
    # support layer under BC-B, so positional indexing would silently measure the wrong
    # surface. Package warpage is measured at the SUBSTRATE underside (z = 0) in both
    # BC families so the two are directly comparable.
    die_top = m.node_ids_at_z(m.layer("die").z1)
    pkg_bot = m.node_ids_at_z(0.0)

    def pv(ids):
        v = U[ids, 2]
        v = v[np.isfinite(v)]
        return float(v.max() - v.min()) if v.size else float("nan")

    out = {
        "die_warpage_pv_um": pv(die_top) * 1000.0,
        "pkg_warpage_pv_um": pv(pkg_bot) * 1000.0,
        "uz_max_um": float(np.nanmax(uz)) * 1000.0,
        "uz_min_um": float(np.nanmin(uz)) * 1000.0,
        "n_die_top_nodes": int(len(die_top)), "n_pkg_bot_nodes": int(len(pkg_bot)),
    }

    si = interior_nodes(m, "silicon")
    if si.size:
        out["si_principal_MPa"] = _band(principal_max(S[si]))
    tsv = interior_nodes(m, "tsv_homog")
    if tsv.size:
        out["tsv_region_vm_MPa"] = _band(von_mises(S[tsv]))
    hv = interior_nodes(m, "hvr_effective")
    if hv.size:
        out["hvr_tile_vm_MPa"] = _band(von_mises(S[hv]))

    uf = region_nodes(m, "underfill_homog")
    if uf.size:
        Suf = S[uf]
        out["interface_shear_MPa"] = _band(np.sqrt(Suf[:, 5] ** 2 + Suf[:, 4] ** 2))
        out["interface_peel_MPa"] = _band(Suf[:, 2])

        # Exclusion-radius variants. The underfill free edge is a bimaterial corner with a
        # theoretical stress singularity: peel there does not converge under refinement by
        # construction, which is exactly what Phase 0B measured (19.2 % at the final step).
        # The physically meaningful peel is in the bonded interior away from that corner, so
        # an exclusion band around the underfill perimeter is applied. This is a standard
        # remedy for a corner singularity, NOT a metric chosen to make a number converge -
        # the raw and p99 values are still reported alongside.
        pos = m.nodes[uf - 1]
        gx = g["functional_die"]["size_x"]["value"] / 2.0
        gy = g["functional_die"]["size_y"]["value"] / 2.0
        for r_excl in (0.25, 0.50, 1.00):
            keep = (np.abs(pos[:, 0]) < gx - r_excl) & (np.abs(pos[:, 1]) < gy - r_excl)
            if keep.sum() < 20:
                continue
            out[f"interface_peel_excl{int(r_excl*100):03d}_MPa"] = _band(Suf[keep, 2])
            out[f"interface_shear_excl{int(r_excl*100):03d}_MPa"] = _band(
                np.sqrt(Suf[keep, 5] ** 2 + Suf[keep, 4] ** 2))
        out["interface_excl_note"] = ("excl<NNN> = nodes at least NNN/100 mm inside the "
                                      "underfill perimeter, excluding the free-edge corner")
    return out
