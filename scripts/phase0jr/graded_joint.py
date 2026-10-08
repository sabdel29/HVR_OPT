#!/usr/bin/env python3
"""Phase-0J-R Sec.5/15 -- targeted local refinement to reproduce Syed's 25 um extraction.

Syed 2004 (author-corrected, and stated again in the appended ECTC deck) averages the creep
response over "25 micron thick layers of solder at package and board side", with "each layer
has two elements across the thickness", and says explicitly:

    "Life prediction model parameters are only valid for this thickness"

The Phase-0I local mesh is 8 uniform elements across a 300 um standoff = 37.5 um each, which
cannot resolve a 25 um layer, let alone two elements within it. This module builds a GRADED
mesh: 2 x 12.5 um at each solder face, the remainder graded in between. ONLY the local joint
submodel is refined; the global package model is untouched.
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0i"))
from joint import (BALL_H_UM, JointMesh, PAD_T_UM, PAD_UM, SOLDER_SIDE_UM,   # noqa: E402
                   _grid)

LAYER_UM = 25.0          # Syed's extraction layer thickness
N_IN_LAYER = 2           # Syed: "each layer has two elements across the thickness"


def solder_z(n_mid: int = 6, layer_um: float = LAYER_UM, n_lay: int = N_IN_LAYER):
    """Solder-local z stations (mm, measured from the solder bottom face)."""
    h = BALL_H_UM / 1e3
    t = layer_um / 1e3
    bot = np.linspace(0.0, t, n_lay + 1)
    top = np.linspace(h - t, h, n_lay + 1)
    # GEOMETRIC grading through the middle. A uniform mid-region puts a 5:1 thickness jump
    # next to the 12.5 um layer element, which made *VISCO cut back to the minimum increment
    # and stall. A smooth expansion from the layer size removes the jump.
    e0 = t / n_lay                                     # 12.5 um, the layer element size
    span = h - 2 * t
    lo, hi = 1.0, 4.0
    for _ in range(80):                                # solve for the expansion ratio
        r = 0.5 * (lo + hi)
        tot = e0 * (n_mid * (r ** 0.5) if abs(r - 1) < 1e-9 else 0)
        half = n_mid // 2
        tot = 2 * e0 * (r * (r ** half - 1) / (r - 1)) if abs(r - 1) > 1e-9 else 2 * e0 * half
        if n_mid % 2:
            tot += e0 * r ** (half + 1)
        if tot < span:
            lo = r
        else:
            hi = r
    r = 0.5 * (lo + hi)
    sizes, half = [], n_mid // 2
    for k in range(1, half + 1):
        sizes.append(e0 * r ** k)
    if n_mid % 2:
        sizes.append(e0 * r ** (half + 1))
    sizes += sizes[:half][::-1]
    sizes = [x * span / sum(sizes) for x in sizes]     # normalise exactly onto the span
    mid = [t]
    for x in sizes:
        mid.append(mid[-1] + x)
    mid[-1] = h - t                                   # snap exactly onto the top layer
    z = np.concatenate([bot, np.array(mid), top])
    # Tolerance-based unique. Plain np.unique leaves float-noise duplicates at the layer
    # boundaries, which become ZERO-THICKNESS elements and make *VISCO diverge at increment 1.
    z = np.sort(z)
    keep = [z[0]]
    for v in z[1:]:
        if v - keep[-1] > 1e-9:
            keep.append(v)
    return np.array(keep)


def build_joint_graded(n_xy: int = 6, n_mid: int = 6, n_z_pad: int = 1,
                       layer_um: float = LAYER_UM, n_lay: int = N_IN_LAYER) -> JointMesh:
    """Same construction as joint.build_joint, but with a GRADED solder z-grid."""
    hp, hs = PAD_UM / 2e3, SOLDER_SIDE_UM / 2e3
    tp, hsol = PAD_T_UM / 1e3, BALL_H_UM / 1e3
    n_in, n_out = max(2, n_xy), max(1, n_xy // 3)
    xs = np.unique(np.concatenate([_grid(-hp, -hs, n_out), _grid(-hs, hs, n_in),
                                   _grid(hs, hp, n_out)]))
    ys = xs.copy()
    zs = np.unique(np.concatenate([_grid(0.0, tp, n_z_pad),
                                   tp + solder_z(n_mid, layer_um, n_lay),
                                   _grid(tp + hsol, tp + hsol + tp, n_z_pad)]))
    nx, ny, nz = len(xs), len(ys), len(zs)
    nid = np.arange(1, nx * ny * nz + 1).reshape(nx, ny, nz)
    pts = np.zeros((nx * ny * nz, 3))
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                pts[nid[i, j, k] - 1] = (xs[i], ys[j], zs[k])
    elems, eid = [], 0
    for i in range(nx - 1):
        for j in range(ny - 1):
            xc, yc = .5 * (xs[i] + xs[i + 1]), .5 * (ys[j] + ys[j + 1])
            inside = abs(xc) < hs - 1e-12 and abs(yc) < hs - 1e-12
            for k in range(nz - 1):
                zc = .5 * (zs[k] + zs[k + 1])
                if zc < tp:
                    sn = "EPADB"
                elif zc < tp + hsol:
                    if not inside:
                        continue
                    sn = "ESOL"
                else:
                    sn = "EPADT"
                eid += 1
                elems.append((eid, [nid[i, j, k], nid[i + 1, j, k], nid[i + 1, j + 1, k],
                                    nid[i, j + 1, k], nid[i, j, k + 1], nid[i + 1, j, k + 1],
                                    nid[i + 1, j + 1, k + 1], nid[i, j + 1, k + 1]], sn))
    used = sorted({n for _, c, _ in elems for n in c})
    remap = {o: i + 1 for i, o in enumerate(used)}
    pts = pts[[o - 1 for o in used]]
    elems = [(e, [remap[n] for n in c], s) for e, c, s in elems]
    zb, zt = zs[0], zs[-1]
    m = JointMesh(pts, elems, {
        "NBOT": [remap[n] for n in used if abs(pts[remap[n] - 1, 2] - zb) < 1e-9],
        "NTOP": [remap[n] for n in used if abs(pts[remap[n] - 1, 2] - zt) < 1e-9]})
    dx = (2 * hs) / n_in
    t = layer_um / 1e3
    core, lay_b, lay_t, lay_both = [], [], [], []
    for e, c, s in elems:
        if s != "ESOL":
            continue
        ctr = pts[[n - 1 for n in c]].mean(axis=0)
        in_core = max(abs(ctr[0]), abs(ctr[1])) < hs - dx * 0.999
        if in_core:
            core.append(e)
        zloc = ctr[2] - tp
        if zloc < t - 1e-9:
            lay_b.append(e)
        elif zloc > hsol - t + 1e-9:
            lay_t.append(e)
    lay_both = sorted(lay_b + lay_t)
    m.sets["ESOLCORE"] = core
    m.sets["ESYED_BOT"] = lay_b            # 25 um board-side layer
    m.sets["ESYED_TOP"] = lay_t            # 25 um package-side layer
    m.sets["ESYED"] = lay_both             # both, as Syed averages
    m.sets["ESYEDCORE"] = sorted(set(lay_both) & set(core))
    m.sets["_dx_mm"] = dx
    return m


if __name__ == "__main__":
    for n_mid in (4, 6, 10):
        m = build_joint_graded(6, n_mid)
        sol = [e for e, _, s in m.elems if s == "ESOL"]
        z = solder_z(n_mid) * 1e3
        print(f"n_mid={n_mid:2}  nodes={m.n_nodes:6}  elems={len(m.elems):6}  "
              f"solder={len(sol):5}  Syed-layer elems={len(m.sets['ESYED']):4} "
              f"(core {len(m.sets['ESYEDCORE'])})")
        print(f"          solder z stations (um): {np.round(z,2).tolist()}")
