"""Phase-0F additional mechanical responses for the board-mounted state.

Phase 0E showed BC-B suppresses free warpage and converts deformation into interface shear,
but interface shear was only marginally mesh-converged in Phase 0B/0C and its ordering was
material-sensitive. Sec. 6 requires a QUALIFIED mounted metric before any of it is used for
design, so alternatives are computed alongside it.

RELATIVE DIE-TO-SUBSTRATE DISPLACEMENT is the one added here. It is the in-plane displacement
difference ACROSS the underfill layer at matching (x, y) -- physically what shears a
microbump -- and unlike peel it involves no bimaterial-corner stress singularity, so it can
converge.
"""
from __future__ import annotations
import numpy as np


def relative_interface_displacement(m, U, tol=1e-9):
    """Max / p99 in-plane displacement difference across the underfill layer.

    Nodes are matched by (x, y) between the underfill's lower and upper faces, so this is a
    displacement DIFFERENCE, not a stress, and has no free-edge singularity.
    """
    lay = m.layer("interface")
    lo = m.node_ids_at_z(lay.z0)
    hi = m.node_ids_at_z(lay.z1)
    plo = m.nodes[lo - 1][:, :2]
    phi = m.nodes[hi - 1][:, :2]
    key = lambda p: (round(float(p[0]), 6), round(float(p[1]), 6))
    top = {key(p): i for p, i in zip(phi, hi)}
    d = []
    for p, i in zip(plo, lo):
        j = top.get(key(p))
        if j is None:
            continue
        d.append(np.hypot(U[j, 0] - U[i, 0], U[j, 1] - U[i, 1]))
    if not d:
        return {"n": 0}
    d = np.asarray(d) * 1000.0            # um
    return {"n": int(d.size),
            "rel_disp_max_um": float(d.max()),
            "rel_disp_p99_um": float(np.percentile(d, 99)),
            "rel_disp_p95_um": float(np.percentile(d, 95)),
            "rel_disp_mean_um": float(d.mean())}


def shear_family(sm):
    """All shear variants Phase 0B/0C computed, for a convergence comparison in one place."""
    out = {}
    b = sm.get("interface_shear_MPa", {})
    for k in ("p99", "p95", "raw_max", "max", "mean"):
        if k in b:
            out[f"shear_{k}_MPa"] = b[k]
    for r in ("025", "050", "100"):
        bb = sm.get(f"interface_shear_excl{r}_MPa", {})
        if "p99" in bb:
            out[f"shear_excl{r}_p99_MPa"] = bb["p99"]
    return out
