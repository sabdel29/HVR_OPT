"""Cut-boundary kinematics of the interconnect layers from the global thermoelastic field
(TCPMT round 3, findings 2, 4 and 9).

GLOBAL -> LOCAL, FULL KINEMATICS (finding 2)
  The round-1/2 transfer kept only |du_xy| across the BGA layer and held both pad faces at
  u_z = 0 while the joint heated. Here each face of an interconnect layer (its bottom face on
  the board / converter side, its top face on the substrate / board side) is sampled over the
  pad footprint of a site on the structured global grid (bilinear on the element faces of the
  layer itself, never across a void) and fitted by a linear field
        u(x, y) = u0 + G (x - x_s, y - y_s),      G = du/d(x, y), 3 x 2,
  which carries the translation, the in-plane stretch and shear of the surface and its
  rotation (the u_z gradient). The local submodel imposes exactly that on its pad faces.

ALL INTERCONNECT LAYERS (finding 4)
  The driver is the relative in-plane displacement over the layer height (an engineering
  shear strain), evaluated at the legal 0.8-mm lattice for the BGA and at every global mesh
  node of the fine-pitch layers (their pitch is below the mesh size, so the mesh nodes are the
  resolution the global solve has).

MEMBRANE / BENDING SPLIT (finding 9)
  At a site, the in-plane displacement of the board and of the package is fitted linearly
  through the thickness of each (u(z) = a + b z on the nodal column): the value at the plate's
  stiffness-weighted neutral plane is its membrane displacement, b (z_face - z_n) its bending
  (rotation x lever arm) part. du across the joint = membrane difference + bending difference
  + a residual (through-thickness shear and non-linearity). The free-expansion estimate
  (alpha_eff dT r) is reported beside it, so 'plate bending, not temperature, drives the joint'
  is a number, not a claim.

    python tcpmt_mech_kinematics.py CASE [...]   site kinematics of the stored fields
        -> research/tcpmt_revision/site_kinematics/<CASE>.json
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import tcpmt_mech_laws as LAW                                       # noqa: E402

OUT = R / "research" / "tcpmt_revision" / "site_kinematics"
FIELDS = Path(os.environ.get("HVR_FIELDS",
                             "/home/beams0/SABDELZAHER/ETM_project/scratch/fields"))
FC = R / "research" / "final_closure"
#: the stored fields of the round-2 cases (production r21 mesh, HV-S0 unless named)
CASES = {
    "Z1_S0": ("Z1", "HV_S0", None, FIELDS / "etm_Z1_HV_S0_r21"),
    "Z2_S0": ("Z2", "HV_S0", None, FIELDS / "etm_Z2_HV_S0_r21"),
    "Z3_S0": ("Z3", "HV_S0", None, FIELDS / "etm_Z3_HV_S0_r21"),
    "Z1_S1": ("Z1", "HV_S1", None, FIELDS / "etm_Z1_HV_S1_r21"),
    "Z2_S1": ("Z2", "HV_S1", None, FIELDS / "etm_Z2_HV_S1_r21"),
    "A_Z3": ("Z3", "HV_S0", "z3_top_only", FIELDS / "etm_Z3_HV_S0__z3_top_only"),
    "B_Z1": ("Z1", "HV_S0", "z1_bottom_plate_tim", FIELDS / "etm_Z1_HV_S0__z1_bottom_plate_tim"),
    "B_Z2": ("Z2", "HV_S0", "z2_cooled_tim", FIELDS / "etm_Z2_HV_S0__z2_cooled_tim"),
    "B_Z3": ("Z3", "HV_S0", "z3_plate_tim", FIELDS / "etm_Z3_HV_S0__z3_plate_tim"),
}
#: the coupled land-side Z3 tier cases the paper's Z3 row uses (their own scratch tree)
Z3LAND = Path(os.environ.get("HVR_Z3LAND",
                             "/home/beams0/SABDELZAHER/ETM_project/scratch_z3land/fc_sens"))
for _t in ("A", "B"):
    CASES[f"{_t}_Z3land"] = ("Z3", "HV_S0", f"z3_land_t40_{_t}_fvmap",
                             Z3LAND / f"z3_land_t40_{_t}_fvmap" / "Z3_HV_S0_h1.1_r21")


def case_file(case):
    arch, scen, var, _ = CASES[case]
    if var is None:
        return FC / f"etm_{arch}_{scen}_h1.1_r21.json"
    return FC / "sensitivity" / f"etm_{arch}_{scen}__{var}.json"


# ---------------------------------------------------------------------- face sampling
class Face:
    """One horizontal surface of a layer on the structured grid: the nodal values of a
    field there, and the cells that are faces of that layer's elements."""

    def __init__(self, m, layer, side):
        L = next(l for l in m.layers if l.name == layer)
        self.z = L.z0 if side == "bot" else L.z1
        self.xs, self.ys = np.asarray(m.xs), np.asarray(m.ys)
        ids = m.elem_set(layer=layer)
        if not len(ids):
            raise ValueError(f"layer {layer} has no elements")
        el = m.elems[ids - 1]
        loc = el[:, :4] if side == "bot" else el[:, 4:]
        p = m.nodes[loc[:, 0] - 1]
        zf = m.nodes[loc[:, 0] - 1, 2]
        if np.max(np.abs(zf - self.z)) > 1e-9:
            # several element rows through the layer: keep the face row only
            keep = np.abs(zf - self.z) < 1e-9
            el, loc, p = el[keep], loc[keep], p[keep]
        ix = np.searchsorted(self.xs, p[:, 0] - 1e-9)
        iy = np.searchsorted(self.ys, p[:, 1] - 1e-9)
        nx, ny = len(self.xs), len(self.ys)
        self.cell = np.zeros((nx - 1, ny - 1), bool)
        self.cell[ix, iy] = True
        self.nid = np.zeros((nx, ny), int)
        # element nodes 0..3 (bottom) / 4..7 (top) run (i,j) (i+1,j) (i+1,j+1) (i,j+1)
        for k, (di, dj) in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
            self.nid[ix + di, iy + dj] = loc[:, k]
        self.layer, self.side = layer, side

    def sample(self, F, x, y):
        """Bilinear value of nodal field F (indexed by node id, rows) at (x, y); NaN off
        the layer's faces."""
        i = int(np.searchsorted(self.xs, x) - 1)
        j = int(np.searchsorted(self.ys, y) - 1)
        if i < 0 or j < 0 or i >= len(self.xs) - 1 or j >= len(self.ys) - 1 \
                or not self.cell[i, j]:
            return None
        x0, x1, y0, y1 = self.xs[i], self.xs[i + 1], self.ys[j], self.ys[j + 1]
        s, t = (x - x0) / (x1 - x0), (y - y0) / (y1 - y0)
        n = self.nid[i:i + 2, j:j + 2]
        f = [np.asarray(F[n[a, b]], float) for a in (0, 1) for b in (0, 1)]
        return ((1 - s) * (1 - t) * f[0] + (1 - s) * t * f[1] + s * (1 - t) * f[2]
                + s * t * f[3])

    def fit(self, F, xs, ys, half, n=5):
        """u0 (k,), G (k,2), samples used: least-squares linear field over the square
        footprint [xs +- half] x [ys +- half]."""
        pts, vals = [], []
        for a in np.linspace(-half, half, n):
            for b in np.linspace(-half, half, n):
                v = self.sample(F, xs + a, ys + b)
                if v is not None and np.all(np.isfinite(v)):
                    pts.append((a, b))
                    vals.append(np.atleast_1d(v))
        if len(pts) < 3:
            return None, None, len(pts)
        A = np.column_stack([np.ones(len(pts)), np.array(pts)])
        coef, *_ = np.linalg.lstsq(A, np.array(vals), rcond=None)
        return coef[0], coef[1:].T, len(pts)


def site_kinematics(m, U, Tn, layer, sites, half, n_fit=5):
    """Per site: the fitted face fields of the layer's bottom and top surfaces (mm, C)."""
    fb, ft = Face(m, layer, "bot"), Face(m, layer, "top")
    h = ft.z - fb.z
    Tcol = node_indexed(m, Tn)
    out = []
    for (x, y) in sites:
        ub, Gb, nb = fb.fit(U, x, y, half, n_fit)
        ut, Gt, nt = ft.fit(U, x, y, half, n_fit)
        if ub is None or ut is None:
            continue
        tb = fb.sample(Tcol, x, y) if Tcol is not None else None
        tt = ft.sample(Tcol, x, y) if Tcol is not None else None
        du = ut[:3] - ub[:3]
        # rigid rotation of the joint from the mean tilt of its two faces: u_x = theta_y z,
        # u_z = -theta_y x  =>  du_rot = -h grad(u_z); it moves the faces without straining
        # the joint, so the |du_xy| transfer of round 2 imposed it as spurious shear
        du_rot = -h * 0.5 * (Gb[2, :2] + Gt[2, :2])
        du_def = du[:2] - du_rot
        out.append({"x_mm": float(x), "y_mm": float(y), "h_mm": float(h),
                    "du_rot_um": (du_rot * 1e3).tolist(),
                    "du_def_xy_um": float(math.hypot(*du_def) * 1e3),
                    # = h (du_x/dz + du_z/dx): the layer's engineering transverse shear strain
                    "gamma_def": float(math.hypot(*du_def) / h),
                    "u_bot_mm": ub[:3].tolist(), "G_bot": Gb[:3].tolist(),
                    "u_top_mm": ut[:3].tolist(), "G_top": Gt[:3].tolist(),
                    "T_bot_C": None if tb is None else float(tb[0]),
                    "T_top_C": None if tt is None else float(tt[0]),
                    "du_mm": du.tolist(), "du_xy_um": float(math.hypot(du[0], du[1]) * 1e3),
                    "du_z_um": float(du[2] * 1e3),
                    "gamma": float(math.hypot(du[0], du[1]) / h),
                    "eps_z": float(du[2] / h),
                    "tilt_rel": [float(Gt[2][0] - Gb[2][0]), float(Gt[2][1] - Gb[2][1])],
                    "n_fit": [nb, nt]})
    return out


def node_indexed(m, Tn):
    """A nodal temperature array indexed by node id (row 0 unused), from either the
    0-based T_node of the solvers or an already node-indexed array."""
    if Tn is None:
        return None
    t = np.asarray(Tn, float).ravel()
    if len(t) == m.n_nodes:
        t = np.concatenate([[np.nan], t])
    return t.reshape(-1, 1)


def site_T(k):
    tb, tt = k.get("T_bot_C"), k.get("T_top_C")
    v = [t for t in (tb, tt) if t is not None]
    return float(np.mean(v)) if v else None


def layer_sites(m, layer, kind, cutout_mm=None):
    """The evaluation sites of one layer: the legal BGA lattice, or every node of the
    layer's bottom face that has the layer above it."""
    if kind == "bga_lattice":
        import physical_coords as PCO
        return PCO.bga_lattice_sites(cutout_mm)
    f = Face(m, layer, "bot")
    i, j = np.nonzero(f.cell)
    # cell centres keep every sample inside the layer (a node sits on a free edge)
    return [(0.5 * (f.xs[a] + f.xs[a + 1]), 0.5 * (f.ys[b] + f.ys[b + 1]))
            for a, b in zip(i, j)]


# ---------------------------------------------------------------------- per layer search
def interconnect_search(m, U, Tn, arch, cutout_mm=None, top_k=None, layers=None):
    """Finding 4: every configured interconnect layer, ranked by du_xy / h; the critical
    site of each with its full kinematics (the local submodel's boundary conditions)."""
    cfg = LAW.cfg()
    top_k = top_k or int(cfg["interconnects"].get("top_k", 10))
    geo = cfg["geometries"]
    have = {L.name for L in m.layers}
    res = {}
    for ent in (layers or cfg["interconnects"].get(arch, [])):
        lay = ent["layer"]
        if lay not in have:
            res[lay] = {"error": f"layer {lay} not in the mesh"}
            continue
        g = geo[ent["geometry"]]
        half = 0.5 * float(g["pad"]) / 1e3
        sites = layer_sites(m, lay, ent["sites"], cutout_mm)
        kin = site_kinematics(m, U, Tn, lay, sites, half,
                              int(cfg["local"].get("pad_fit_samples", 5)))
        if not kin:
            res[lay] = {"error": "no site could be evaluated"}
            continue
        kin.sort(key=lambda k: -k["gamma"])
        crit = kin[0]
        cand = candidate_sites(kin) if ent["sites"] == "bga_lattice" else kin[:top_k]
        res[lay] = {"label": ent["label"], "geometry": ent["geometry"],
                    "h_um": crit["h_mm"] * 1e3, "sites": ent["sites"],
                    "n_sites": len(sites), "n_evaluated": len(kin),
                    "driver": "gamma = |du_xy| / h (relative in-plane displacement over "
                              "the layer height)",
                    "critical": dict(crit, T_C=site_T(crit)),
                    "top": [dict(k, T_C=site_T(k)) for k in kin[:top_k]],
                    "candidates": compact_sites(cand),
                    "gamma_max": crit["gamma"],
                    "critical_by_shear_strain": (lambda k: dict(k, T_C=site_T(k)))(
                        max(kin, key=lambda k: k["gamma_def"])),
                    "gamma_def_max": max(k["gamma_def"] for k in kin),
                    "du_xy_um_max": max(k["du_xy_um"] for k in kin),
                    "eps_z_range": [min(k["eps_z"] for k in kin), max(k["eps_z"] for k in kin)]}
    return res


def candidate_sites(kin, n_top=30):
    """Sites a local critical-joint check must cover once the transfer is the full
    kinematics: the top n_top by |du_xy|, by |relative tilt|, by |eps_z| and by the
    deforming (rotation-free) in-plane du, the strict Pareto front in (|du_xy|, T) and the
    four lattice corners."""
    if not kin:
        return []
    key = lambda k: (round(k["x_mm"], 6), round(k["y_mm"], 6))              # noqa: E731
    pick = {}
    for f in (lambda k: k["du_xy_um"], lambda k: math.hypot(*k.get("tilt_rel", (0, 0))),
              lambda k: abs(k["eps_z"]), lambda k: k.get("du_def_xy_um", 0.0)):
        for k in sorted(kin, key=f, reverse=True)[:n_top]:
            pick[key(k)] = k
    T = {key(k): site_T(k) or 0.0 for k in kin}
    for k in kin:
        if not any(o["du_xy_um"] > k["du_xy_um"] and T[key(o)] > T[key(k)] for o in kin):
            pick[key(k)] = k
    xm = max(abs(k["x_mm"]) for k in kin)
    ym = max(abs(k["y_mm"]) for k in kin)
    for k in kin:
        if abs(abs(k["x_mm"]) - xm) < 1e-9 and abs(abs(k["y_mm"]) - ym) < 1e-9:
            pick[key(k)] = k
    return sorted(pick.values(), key=lambda k: -k["du_xy_um"])


def compact_sites(kin):
    """Column arrays of a kinematics list (case files keep every BGA site this way)."""
    keys = ("x_mm", "y_mm", "du_xy_um", "du_z_um", "T_bot_C", "T_top_C")
    out = {k: [None if r[k] is None else round(float(r[k]), 7) for r in kin] for k in keys}
    out["u_bot_mm"] = [[round(v, 9) for v in r["u_bot_mm"]] for r in kin]
    out["u_top_mm"] = [[round(v, 9) for v in r["u_top_mm"]] for r in kin]
    out["G_bot"] = [[[round(v, 9) for v in row] for row in r["G_bot"]] for r in kin]
    out["G_top"] = [[[round(v, 9) for v in row] for row in r["G_top"]] for r in kin]
    out["h_mm"] = kin[0]["h_mm"] if kin else None
    return out


def expand_sites(c):
    """Inverse of compact_sites."""
    n = len(c["x_mm"])
    out = []
    for i in range(n):
        ub, ut = np.array(c["u_bot_mm"][i]), np.array(c["u_top_mm"][i])
        du = ut - ub
        Gb, Gt = np.array(c["G_bot"][i]), np.array(c["G_top"][i])
        du_rot = -c["h_mm"] * 0.5 * (Gb[2] + Gt[2])
        out.append({"x_mm": c["x_mm"][i], "y_mm": c["y_mm"][i], "h_mm": c["h_mm"],
                    "du_rot_um": (du_rot * 1e3).tolist(),
                    "du_def_xy_um": float(math.hypot(*(du[:2] - du_rot)) * 1e3),
                    "gamma_def": float(math.hypot(*(du[:2] - du_rot)) / c["h_mm"]),
                    "tilt_rel": (Gt[2] - Gb[2]).tolist(),
                    "u_bot_mm": c["u_bot_mm"][i], "u_top_mm": c["u_top_mm"][i],
                    "G_bot": c["G_bot"][i], "G_top": c["G_top"][i],
                    "T_bot_C": c["T_bot_C"][i], "T_top_C": c["T_top_C"][i],
                    "du_mm": du.tolist(), "du_xy_um": c["du_xy_um"][i],
                    "du_z_um": c["du_z_um"][i],
                    "gamma": c["du_xy_um"][i] / 1e3 / c["h_mm"],
                    "eps_z": c["du_z_um"][i] / 1e3 / c["h_mm"]})
    return out


# ---------------------------------------------------------------------- finding 9
def _column(m, F, x, y, z_lo, z_hi):
    """Bilinear samples of nodal field F on every grid plane z_lo <= z <= z_hi at (x, y),
    using whatever nodes exist on that plane (None where the cell is incomplete)."""
    xs, ys = np.asarray(m.xs), np.asarray(m.ys)
    i = int(np.searchsorted(xs, x) - 1)
    j = int(np.searchsorted(ys, y) - 1)
    s = (x - xs[i]) / (xs[i + 1] - xs[i])
    t = (y - ys[j]) / (ys[j + 1] - ys[j])
    key = {}
    sel = ((np.abs(m.nodes[:, 0] - xs[i]) < 1e-9) | (np.abs(m.nodes[:, 0] - xs[i + 1]) < 1e-9)) & \
          ((np.abs(m.nodes[:, 1] - ys[j]) < 1e-9) | (np.abs(m.nodes[:, 1] - ys[j + 1]) < 1e-9))
    for nid in np.nonzero(sel)[0] + 1:
        p = m.nodes[nid - 1]
        a = 0 if abs(p[0] - xs[i]) < 1e-9 else 1
        b = 0 if abs(p[1] - ys[j]) < 1e-9 else 1
        key[(round(float(p[2]), 9), a, b)] = nid
    zs = sorted({k[0] for k in key if z_lo - 1e-9 <= k[0] <= z_hi + 1e-9})
    out = []
    for z in zs:
        ids = [key.get((z, a, b)) for a in (0, 1) for b in (0, 1)]
        if None in ids:
            continue
        f = [np.asarray(F[n], float) for n in ids]
        v = (1 - s) * (1 - t) * f[0] + (1 - s) * t * f[1] + s * (1 - t) * f[2] + s * t * f[3]
        out.append((z, v))
    return out


def _cell_material(m, x, y, z):
    """Material of the element containing (x, y, z), or None (void)."""
    xs, ys, zs = np.asarray(m.xs), np.asarray(m.ys), np.asarray(m.zs)
    i, j, k = (int(np.searchsorted(a, v) - 1) for a, v in ((xs, x), (ys, y), (zs, z)))
    c = m.elem_centroids() if not hasattr(m, "_cen") else m._cen
    m._cen = c
    hit = np.nonzero((np.abs(c[:, 0] - 0.5 * (xs[i] + xs[i + 1])) < 1e-9)
                     & (np.abs(c[:, 1] - 0.5 * (ys[j] + ys[j + 1])) < 1e-9)
                     & (np.abs(c[:, 2] - 0.5 * (zs[k] + zs[k + 1])) < 1e-9))[0]
    return m.elem_material[hit[0]] if len(hit) else None


def free_strain(m, mats, Tcol, x, y, z_lo, z_hi, t_ref=25.0):
    """Free membrane strain of the laminate column at (x, y) between z_lo and z_hi:
    sum E_i t_i alpha_i (T_i - T_ref) / sum E_i t_i over its element slabs (voids skipped)."""
    col = _column(m, Tcol, x, y, z_lo, z_hi)
    num = den = 0.0
    for (za, ta), (zb, tb) in zip(col, col[1:]):
        mat = _cell_material(m, x, y, 0.5 * (za + zb))
        if mat is None:
            continue
        E = mats[mat].E if mats[mat].E else (mats[mat].C11 or 0.0) * 0.78
        num += E * (zb - za) * mats[mat].cte * (0.5 * (ta[0] + tb[0]) - t_ref)
        den += E * (zb - za)
    return num / den if den else None


def free_mismatch_um(m, mats, Tcol, x, y, z_bot, z_top, t_ref=25.0, n=24):
    """In-plane free-expansion mismatch (package minus board) at the site, integrated
    along the ray from the package centre: u = int eps_free ds, directed along the ray."""
    r = math.hypot(x, y)
    if r == 0:
        return [0.0, 0.0]
    z_min, z_max = float(np.min(m.zs)), float(np.max(m.zs))
    d = []
    for k in range(n):
        f = (k + 0.5) / n
        xp, yp = f * x, f * y
        ep = free_strain(m, mats, Tcol, xp, yp, z_top, z_max, t_ref)
        eb = free_strain(m, mats, Tcol, xp, yp, z_min, z_bot, t_ref)
        if ep is not None and eb is not None:       # a ring (Z2 opening) expands about
            d.append(ep - eb)                       # its centre too: average where present
    if not d:
        return None
    acc = float(np.mean(d)) * r
    return [acc * x / r * 1e3, acc * y / r * 1e3]


def decompose_site(m, U, Tn, mats, x, y, layer="bga", t_ref=25.0):
    """Finding 9: split du across `layer` at (x, y) into membrane and bending parts of the
    plate below (board side) and the plate above (package side)."""
    L = next(l for l in m.layers if l.name == layer)
    z_bot, z_top = L.z0, L.z1
    z_min, z_max = float(np.min(m.zs)), float(np.max(m.zs))
    below = [(z, v) for z, v in _column(m, U, x, y, z_min, z_bot)]
    above = [(z, v) for z, v in _column(m, U, x, y, z_top, z_max)]
    Tcol = node_indexed(m, Tn)
    out = {"x_mm": x, "y_mm": y, "layer": layer}

    def plate(col, z_face):
        z = np.array([c[0] for c in col])
        u = np.array([c[1][:2] for c in col])
        if len(z) < 2:
            return None
        A = np.column_stack([np.ones(len(z)), z])
        coef, res, *_ = np.linalg.lstsq(A, u, rcond=None)
        # stiffness-weighted neutral plane over the column's element slabs
        num = den = 0.0
        ae = ae_den = 0.0
        tz = []
        for za, zb in zip(z[:-1], z[1:]):
            mat = _cell_material(m, x, y, 0.5 * (za + zb))
            if mat is None:
                continue
            E = mats[mat].E if mats[mat].E else (mats[mat].C11 or 0.0) * 0.78
            num += E * (zb - za) * 0.5 * (za + zb)
            den += E * (zb - za)
            ae += E * (zb - za) * mats[mat].cte
            ae_den += E * (zb - za)
            tz.append(0.5 * (za + zb))
        z_n = num / den if den else 0.5 * (z[0] + z[-1])
        T = [c[1][0] for c in _column(m, Tcol, x, y, z[0], z[-1])]
        u_n = coef[0] + coef[1] * z_n
        bend = coef[1] * (z_face - z_n)
        fit_face = coef[0] + coef[1] * z_face
        actual_face = u[np.argmin(np.abs(z - z_face))]
        return {"z_range_mm": [float(z[0]), float(z[-1])], "z_neutral_mm": float(z_n),
                "slope_rad": coef[1].tolist(), "membrane_mm": u_n.tolist(),
                "bending_mm": bend.tolist(), "face_fit_mm": fit_face.tolist(),
                "face_actual_mm": actual_face.tolist(),
                "linear_residual_mm": (actual_face - fit_face).tolist(),
                "alpha_eff_per_K": ae / ae_den if ae_den else None,
                "T_mean_C": float(np.mean(T)) if T else None}

    pb, pt = plate(below, z_bot), plate(above, z_top)
    if pb is None or pt is None:
        out["error"] = "column incomplete"
        return out
    du = np.array(pt["face_actual_mm"]) - np.array(pb["face_actual_mm"])
    mem = np.array(pt["membrane_mm"]) - np.array(pb["membrane_mm"])
    ben = np.array(pt["bending_mm"]) - np.array(pb["bending_mm"])
    res = du - mem - ben
    half = 0.5 * float(LAW.cfg()["geometries"]["bga"]["pad"]) / 1e3
    sk = site_kinematics(m, U, Tn, layer, [(x, y)], half)
    if sk:
        out["rigid_rotation_um"] = sk[0]["du_rot_um"]
        out["deforming_xy_um"] = sk[0]["du_def_xy_um"]
        out["rotation_note"] = ("rigid rotation of the joint = -h x the mean tilt of its two "
                                "faces; it moves the faces without straining the joint")
    fm = free_mismatch_um(m, mats, Tcol, x, y, z_bot, z_top, t_ref)
    free = None if fm is None else np.array(fm) / 1e3
    nrm = float(np.hypot(*du))
    proj = lambda v: float(np.dot(v, du) / nrm) if nrm else float("nan")   # noqa: E731
    out.update({
        "board_side": pb, "package_side": pt,
        "du_um": (du * 1e3).tolist(), "du_xy_um": nrm * 1e3,
        "membrane_um": (mem * 1e3).tolist(), "bending_um": (ben * 1e3).tolist(),
        "residual_um": (res * 1e3).tolist(),
        "share_along_du": {"membrane": proj(mem) / nrm if nrm else None,
                           "bending": proj(ben) / nrm if nrm else None,
                           "residual": proj(res) / nrm if nrm else None},
        "free_expansion_estimate_um": None if free is None else (free * 1e3).tolist(),
        "free_over_du": None if free is None or not nrm else float(np.hypot(*free) / nrm),
        "definition": "membrane = in-plane displacement of each plate at its stiffness-"
                      "weighted neutral plane (linear fit through the nodal column); bending "
                      "= fitted slope x (joint face - neutral plane); residual = du - "
                      "membrane - bending (through-thickness shear and non-linearity); "
                      "free = free-expansion mismatch package - board, the laminate free "
                      "strain sum(E t alpha dT)/sum(E t) of each column integrated along "
                      "the ray from the package centre (no bending, no mutual restraint)"})
    return out


# ---------------------------------------------------------------------- stored fields
def read_frd_nodes(path):
    """Node coordinates of a CalculiX .frd ('    2C' block), 1-based rows."""
    rows, mx = {}, 0
    with open(path) as fh:
        on = False
        for line in fh:
            if line.startswith("    2C"):
                on = True
                continue
            if on:
                if line.startswith(" -3"):
                    break
                if line.startswith(" -1"):
                    nid = int(line[3:13])
                    rows[nid] = (float(line[13:25]), float(line[25:37]), float(line[37:49]))
                    mx = max(mx, nid)
    out = np.full((mx + 1, 3), np.nan)
    for k, v in rows.items():
        out[k] = v
    return out


def load_case(case, refine=(2, 1)):
    """(mesh, U, T_node, mats, case_json) of a stored round-2 case; asserts that the stored
    structural field's node coordinates are the rebuilt mesh's."""
    import final_closure_physical_etm as E
    import production_et as PE
    arch, scen, var, d = CASES[case]
    m, mats, st, tiles, _ = E.build(arch, 1.1, refine)
    st_frd = d / "structural.frd"
    th = d / "thermal_converged.frd"
    if not th.exists():                     # a case work tree: the last E-T iteration
        its = sorted(d.glob("et*"), key=lambda p: int(p.name[2:]))
        th = sorted(its[-1].glob("th_*.frd"), key=lambda p: int(p.stem.split("_")[1]))[-1]
    xyz = read_frd_nodes(st_frd)
    if len(xyz) - 1 != m.n_nodes or np.nanmax(np.abs(xyz[1:] - m.nodes)) > 1e-5:
        raise RuntimeError(f"{case}: stored field mesh differs from the rebuilt mesh")
    U = PE.ccxio.read_frd(st_frd)["DISP"][:, :3]
    T = PE.ccxio.read_frd(th)["NDTEMP"][1:m.n_nodes + 1, 0]
    cj = json.loads(case_file(case).read_text()) if case_file(case).exists() else None
    if cj and abs(float(np.nanmax(T)) - cj["thermal"]["T_max_C"]) > 1e-4:
        raise RuntimeError(f"{case}: thermal field is not the case's converged field")
    return m, U, T, mats, cj


def case_kinematics(case):
    """Every configured interconnect layer of one stored case, plus the BGA site list in
    compact form and the finding-9 decomposition at the BGA critical site."""
    import final_closure_physical_etm  # noqa: F401  (puts the builders on sys.path)
    import pkg_rdl_network as K
    m, U, T, mats, cj = load_case(case)
    arch = CASES[case][0]
    cut = K.architecture_cutout_mm(arch) if arch != "Z3" else None
    res = interconnect_search(m, U, T, arch, cut)
    c = res["bga"]["critical"]
    dec = decompose_site(m, U, T, mats, c["x_mm"], c["y_mm"])
    legacy = (cj or {}).get("mechanics", {}).get("joint_search", {}).get("critical")
    return {"case": case, "arch": arch, "field": str(CASES[case][3]),
            "case_file": case_file(case).relative_to(R).as_posix(),
            "legacy_critical": legacy, "interconnects": res,
            "decomposition_bga_critical": dec,
            "decomposition_legacy_critical": (decompose_site(
                m, U, T, mats, legacy["x_mm"], legacy["y_mm"]) if legacy else None)}


def load_kinematics(case):
    f = OUT / f"{case}.json"
    return json.loads(f.read_text()) if f.exists() else None


SUMMARY = R / "research" / "tcpmt_revision" / "interconnect_drivers.json"
LADDER = R / "research" / "tcpmt_revision" / "interconnect_mesh_ladder.json"
FC_WORK = Path(os.environ.get("HVR_FC_WORK",
                              "/home/beams0/SABDELZAHER/ETM_project/scratch/fc_etm"))


def ladder(arch, scen="HV_S0", levels=((1, 1), (2, 1), (3, 1))):
    """Per-layer drivers of one case on the production mesh ladder (the case work trees of
    the mesh study): is the critical-site driver of each interconnect layer mesh-converged?
    A bimaterial corner (the die edge over the microbump row) is not, by construction."""
    import final_closure_physical_etm as E
    import production_et as PE
    import pkg_rdl_network as K
    cut = K.architecture_cutout_mm(arch) if arch != "Z3" else None
    out = {}
    for ref in levels:
        d = FC_WORK / f"{arch}_{scen}_h1.1{E.refine_tag(ref)}"
        sf = d / "structural.frd"
        if not sf.exists():
            continue
        m, mats, st, tiles, _ = E.build(arch, 1.1, ref)
        its = sorted(d.glob("et*"), key=lambda p: int(p.name[2:]))
        th = sorted(its[-1].glob("th_*.frd"), key=lambda p: int(p.stem.split("_")[1]))[-1]
        U = PE.ccxio.read_frd(sf)["DISP"][:, :3]
        T = PE.ccxio.read_frd(th)["NDTEMP"][1:m.n_nodes + 1, 0]
        res = interconnect_search(m, U, T, arch, cut)
        out[f"r{ref[0]}{ref[1]}"] = {
            k: {"gamma_max": v.get("gamma_max"), "critical_mm": [v["critical"]["x_mm"],
                                                                  v["critical"]["y_mm"]],
                "du_xy_um": v["critical"]["du_xy_um"],
                "du_def_xy_um": v["critical"].get("du_def_xy_um"),
                "n_elems": m.n_elems} for k, v in res.items() if "critical" in v}
    d = json.loads(LADDER.read_text()) if LADDER.exists() else {}
    d[f"{arch}_{scen}"] = out
    LADDER.write_text(json.dumps(d, indent=1, default=float) + "\n")
    return out


def summary():
    """Findings 4 and 9 across the stored cases: the critical site of every interconnect
    layer, and the split of the BGA corner du (membrane / bending / residual; rigid joint
    rotation / deforming part)."""
    out = {"what": "interconnect drivers per layer (finding 4) and the composition of the "
                   "BGA joint driver (finding 9), from the stored global fields",
           "generator": "scripts/tcpmt_mech_kinematics.py --summary", "cases": {}}
    n_bend_adds = n_bend_opposes = 0
    for case in CASES:
        k = load_kinematics(case)
        if not k:
            continue
        lay = {}
        for name, v in k["interconnects"].items():
            if "critical" not in v:
                continue
            c = v["critical"]
            lay[name] = {"label": v["label"], "h_um": v["h_um"], "x_mm": c["x_mm"],
                         "y_mm": c["y_mm"], "gamma": c["gamma"], "du_xy_um": c["du_xy_um"],
                         "du_z_um": c["du_z_um"], "eps_z": c["eps_z"], "T_C": c.get("T_C"),
                         "du_def_xy_um": c.get("du_def_xy_um"), "n_sites": v["n_sites"],
                         "gamma_def_max": v.get("gamma_def_max"),
                         "critical_by_shear_strain_mm": (
                             [v["critical_by_shear_strain"]["x_mm"],
                              v["critical_by_shear_strain"]["y_mm"]]
                             if v.get("critical_by_shear_strain") else None)}
        d = k.get("decomposition_bga_critical") or {}
        sh = d.get("share_along_du") or {}
        if sh.get("bending") is not None:
            n_bend_adds += sh["bending"] > 0
            n_bend_opposes += sh["bending"] < 0
        nrm = lambda v: float(np.hypot(*v)) if v else None              # noqa: E731
        out["cases"][case] = {
            "layers": lay,
            "governing_layer_by_gamma": max(lay, key=lambda n: lay[n]["gamma"]) if lay else None,
            "bga_split": {"x_mm": d.get("x_mm"), "y_mm": d.get("y_mm"),
                          "du_xy_um": d.get("du_xy_um"),
                          "membrane_um": nrm(d.get("membrane_um")),
                          "bending_um": nrm(d.get("bending_um")),
                          "residual_um": nrm(d.get("residual_um")), "share_along_du": sh,
                          "free_mismatch_um": nrm(d.get("free_expansion_estimate_um")),
                          "rigid_rotation_um": nrm(d.get("rigid_rotation_um")),
                          "deforming_xy_um": d.get("deforming_xy_um")}}
    out["claim_test"] = {
        "claim": "plate bending, not temperature, drives the joint",
        "cases_where_bending_adds_to_du": n_bend_adds,
        "cases_where_bending_opposes_du": n_bend_opposes,
        "reading": "membrane = in-plane thermal-expansion mismatch at the neutral planes; the "
                   "bending (rotation x lever-arm) part opposes it where its share is "
                   "negative. The joint's rigid rotation (mean face tilt x height) is part of "
                   "|du_xy| but strains nothing: the deforming part is what the joint sees."}
    SUMMARY.write_text(json.dumps(out, indent=1, default=float) + "\n")
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if "--summary" in sys.argv:
        s = summary()
        print(json.dumps(s["claim_test"], indent=1))
        return
    if "--ladder" in sys.argv:
        for a in [x for x in sys.argv[1:] if x in ("Z1", "Z2", "Z3")] or ["Z1", "Z2"]:
            print(a, json.dumps(ladder(a), indent=1, default=float))
        return
    for case in (sys.argv[1:] or list(CASES)):
        if not (CASES[case][3] / "structural.frd").exists():
            print(case, "no stored structural field, skipped", flush=True)
            continue
        r = case_kinematics(case)
        (OUT / f"{case}.json").write_text(json.dumps(r, default=float) + "\n")
        c = r["interconnects"]["bga"]["critical"]
        d = r["decomposition_bga_critical"]
        print(f"{case}: BGA crit ({c['x_mm']}, {c['y_mm']}) du_xy {c['du_xy_um']:.3f} um "
              f"du_z {c['du_z_um']:.3f} um; bending share {d['share_along_du']['bending']:.2f}"
              + "".join(f"; {k}: gamma {v['gamma_max']:.2e}" for k, v in
                        r["interconnects"].items() if "gamma_max" in v), flush=True)


if __name__ == "__main__":
    main()
