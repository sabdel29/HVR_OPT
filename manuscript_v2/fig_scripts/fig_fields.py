"""Fig. 7: converged fields of every integration at S0 under cooling A (the same top plate).

(a)-(c) Temperature on the vertical section y = 0 (middle row of cells), drawn element by
        element so voids (board opening, sidewall ring) stay empty; shared heat scale.
(d)-(f) Out-of-plane displacement of the die top surface relative to its lowest point
        (peak-to-valley = die warpage); shared scale.
(g)-(i) In-plane relative displacement across the ball layer at every legal BGA site;
        critical joint ringed; shared scale.
Z3 under cooling A is the coupled land-side case z3_land_t40_A_fvmap: its fields are read from
the solver scratch (last E-T iteration's thermal deck and the structural run, located as in
scripts/tcpmt_z3land_variants.py: scratch_dir / last_thermal_frd) and checked against the
case file's T_max; if they are missing or do not match, the top-only Z3 fields are used and
the panel says so. The 150-C GaN-rating isotherm is drawn on every section.
Data: converged production fields ($HVR_FIELDS/etm_*_HV_S0_r21), the case files and
architecture_geometry.json (die-top height).
"""
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib import colors as mcolors
import matplotlib.tri as mtri
import style as S
import frd

S.setup()
_g = S.macro("GanTjMax")
GAN = float(_g) if _g else None
iso_drawn = False
F = S.FIELDS
#: cooling A (the same top cold plate): production fields for Z1/Z2, the top-only case for Z3
from pathlib import Path


def _pair(dirname):
    return (F / dirname / "thermal_converged.frd", F / dirname / "structural.frd")


def _scratch_pair(variant):
    """last E-T thermal deck and the structural run of a Z3 land-side variant"""
    import os
    roots = [Path(os.environ["HVR_SCRATCH"])] if os.environ.get("HVR_SCRATCH") else []
    roots += [Path.home() / "claude_scratch" / "hvr_work",
              Path("/home/beams0/SABDELZAHER/ETM_project/scratch_z3land"),
              Path("/home/beams0/SABDELZAHER/ETM_project/scratch")]
    for r in roots:
        wd = r / "fc_sens" / variant / "Z3_HV_S0_h1.1_r21"
        its = sorted(wd.glob("et*"), key=lambda p: int(p.name[2:])) if wd.is_dir() else []
        if its and (wd / "structural.frd").is_file():
            ths = sorted(its[-1].glob("th_*.frd"), key=lambda p: int(p.stem.split("_")[1]))
            if ths:
                return ths[-1], wd / "structural.frd"
    return None


SRC_FIELD = {"Z1": (_pair("etm_Z1_HV_S0_r21"), "etm_Z1_HV_S0_h1.1_r21.json"),
             "Z2": (_pair("etm_Z2_HV_S0_r21"), "etm_Z2_HV_S0_h1.1_r21.json"),
             "Z3": (_pair("etm_Z3_HV_S0__z3_top_only"),
                    "sensitivity/etm_Z3_HV_S0__z3_top_only.json")}
Z3_NOTE = "top-only Z3 (land-side fields not found)"
_land = _scratch_pair("z3_land_t40_A_fvmap")
_lcase = "sensitivity/etm_Z3_HV_S0__z3_land_t40_A_fvmap.json"
if _land and (S.FC / _lcase).is_file():
    _tl = frd.read(_land[0])["NDTEMP"][:, 0].max()
    _tc = json.loads((S.FC / _lcase).read_text())["thermal"]["T_max_C"]
    if abs(_tl - _tc) < 0.05:
        SRC_FIELD["Z3"] = (_land, _lcase)
        Z3_NOTE = None
    else:
        Z3_NOTE = f"top-only Z3 (land-side field T_max {_tl:.1f} != case {_tc:.1f})"
if Z3_NOTE:
    print("NOTE:", Z3_NOTE)
ARCHS = [a for a in ("Z1", "Z2", "Z3") if SRC_FIELD[a][0][1].exists()]
N = len(ARCHS)
VEX = 2.0                                   # vertical exaggeration of the sections
GEO = (S.J("architecture_geometry.json") or {}).get("architectures", {})
LET = "abcdefghi"


def die_top_mm(a):
    lay = {L["name"]: L for L in GEO[a]["layers"]}
    return lay["die"]["z1_um"] / 1e3


def section(d, field, y0=1e-6):
    xyz, con = d["xyz"], d["econ"]
    idx = {n: i for i, n in enumerate(d["nid"])}
    ci = np.vectorize(idx.get)(con)
    ys = xyz[ci, 1]
    sel = (ys.min(1) < y0) & (ys.max(1) >= y0)
    ci = ci[sel]
    xs, zs = xyz[ci, 0], xyz[ci, 2]
    polys = [((x0, z0 * VEX), (x1, z0 * VEX), (x1, z1 * VEX), (x0, z1 * VEX))
             for x0, x1, z0, z1 in zip(xs.min(1), xs.max(1), zs.min(1), zs.max(1))]
    return polys, field[ci].mean(1), zs.min(), zs.max()


def die_top(ds, a):
    xyz = ds["xyz"]
    uz = ds["DISP"][:, 2] * 1e3            # mm -> um
    zt = die_top_mm(a)
    m = (np.abs(xyz[:, 2] - zt) < 1e-6) & (np.abs(xyz[:, 0]) <= 11.18 + 1e-6) & \
        (np.abs(xyz[:, 1]) <= 11.18 + 1e-6)
    return xyz[m, 0], xyz[m, 1], uz[m] - uz[m].min()


data = {}
for a in ARCHS:
    dt = frd.read(SRC_FIELD[a][0][0])
    ds = frd.read(SRC_FIELD[a][0][1])
    case = json.loads((S.FC / SRC_FIELD[a][1]).read_text())
    T = dt["NDTEMP"][:, 0]
    data[a] = dict(sec=section(dt, T), tmax=float(T.max()), die=die_top(ds, a),
                   js=case["mechanics"]["joint_search"])
zlo = min(d["sec"][2] for d in data.values())
zhi = max(d["sec"][3] for d in data.values())

# layout: the section row is sized from its true aspect (31.2 mm wide, shared z range)
gap = 0.012
wS = (0.905 - 0.055 - (N - 1) * gap) / N
sec_h_in = wS * S.DBL_W * ((zhi - zlo + 0.3) * VEX) / 31.2
map_w = 0.112
map_in = map_w * S.DBL_W
H = sec_h_in + map_in + 1.25
fig = plt.figure(figsize=(S.DBL_W, H))
y_map = 0.42 / H
y_sec = (map_in + 0.42 + 0.78) / H
axS = [fig.add_axes([0.055 + k * (wS + gap), y_sec, wS, sec_h_in / H]) for k in range(N)]
caxT = fig.add_axes([0.928, y_sec + 0.1 * sec_h_in / H, 0.011, 0.8 * sec_h_in / H])
x0D, x0J = 0.055, 0.535
axD = [fig.add_axes([x0D + k * (map_w + 0.012), y_map, map_w, map_in / H]) for k in range(N)]
caxD = fig.add_axes([x0D + N * (map_w + 0.012) + 0.002, y_map + 0.06 * map_in / H, 0.009,
                     0.88 * map_in / H])
axJ = [fig.add_axes([x0J + k * (map_w + 0.012), y_map, map_w, map_in / H]) for k in range(N)]
caxJ = fig.add_axes([x0J + N * (map_w + 0.012) + 0.002, y_map + 0.06 * map_in / H, 0.009,
                     0.88 * map_in / H])
fig.text(x0D, y_map + map_in / H + 0.22 / H, "Die top surface relative to its lowest point",
         ha="left", va="bottom", fontsize=7, color=S.INK)
fig.text(x0J, y_map + map_in / H + 0.22 / H, "Relative displacement across the ball layer",
         ha="left", va="bottom", fontsize=7, color=S.INK)

tnorm = mcolors.Normalize(25, max(125, 5 * np.ceil(max(d["tmax"] for d in data.values()) / 5)))
tcmap = plt.get_cmap("YlOrRd")
for k, a in enumerate(ARCHS):
    ax = axS[k]
    polys, val, _, _ = data[a]["sec"]
    ax.add_collection(PolyCollection(polys, array=val, cmap=tcmap, norm=tnorm,
                                     edgecolors="face", linewidths=0.05))
    # GaN-rating isotherm, on the element-centre values of the section
    if GAN and val.max() > GAN:
        pc = np.array([[sum(p[i][0] for i in range(4)) / 4, sum(p[i][1] for i in range(4)) / 4]
                       for p in polys])
        tri = mtri.Triangulation(pc[:, 0], pc[:, 1])
        ed = np.array([[np.hypot(*(pc[t[i]] - pc[t[(i + 1) % 3]])) for i in range(3)]
                       for t in tri.triangles])
        tri.set_mask(ed.max(1) > 1.6)                 # no contour across voids
        ax.tricontour(tri, val, levels=[GAN], colors=S.INK, linewidths=0.7,
                      linestyles="--")
        iso_drawn = True
    ax.set_xlim(-15.6, 15.6)
    ax.set_ylim((zlo - 0.15) * VEX, (zhi + 0.15) * VEX)
    ax.set_aspect("equal")
    ax.grid(False)
    zt = np.arange(np.ceil(zlo), np.floor(zhi) + 1, 1.0)
    ax.set_yticks(zt * VEX, [f"{v:.0f}".replace("-", "−") for v in zt] if k == 0 else [])
    ax.set_xlabel("$x$ (mm)", labelpad=1)
    if k == 0:
        ax.set_ylabel(f"$z$ (mm), vertical ×{VEX:g}", labelpad=1)
    S.panel(ax, LET[k], f"{a}, $T_\\max$ = {data[a]['tmax']:.1f} °C", y=1.02)
    if a == "Z3":
        ax.text(1.0, 1.02, "coupled land side" if not Z3_NOTE else Z3_NOTE, transform=ax.transAxes,
                ha="right", va="bottom", fontsize=6.5, color=S.INK2)
cb = fig.colorbar(plt.cm.ScalarMappable(norm=tnorm, cmap=tcmap), cax=caxT)
cb.set_label("Temperature (°C)", labelpad=2)
if GAN:
    cb.ax.axhline(GAN, color=S.INK, lw=0.7, ls=(0, (3, 1.5)))
    if iso_drawn:
        axS[0].text(0.0, -0.32, f"dashed: {GAN:.0f}-°C GaN-rating isotherm",
                    transform=axS[0].transAxes, ha="left", va="top", fontsize=6.5,
                    color=S.INK2)
cb.outline.set_linewidth(0.4)

vmax_d = max(d["die"][2].max() for d in data.values())
dnorm = mcolors.Normalize(0, vmax_d)
dcmap = plt.get_cmap("Blues")
for k, a in enumerate(ARCHS):
    x, y, u = data[a]["die"]
    ax = axD[k]
    ax.tricontourf(x, y, u, levels=np.linspace(0, vmax_d, 15), cmap=dcmap, norm=dnorm)
    ax.set_aspect("equal")
    ax.set_xlim(-11.2, 11.2)
    ax.set_ylim(-11.2, 11.2)
    ax.grid(False)
    ax.set_xticks([-10, 0, 10], ["−10", "0", "10"])
    ax.set_yticks([-10, 0, 10] if k == 0 else [], ["−10", "0", "10"] if k == 0 else [])
    ax.set_xlabel("$x$ (mm)", labelpad=1)
    if k == 0:
        ax.set_ylabel("$y$ (mm)", labelpad=0)
    S.panel(ax, LET[N + k], f"{a}: {u.max():.1f} µm", y=1.02)
cb = fig.colorbar(plt.cm.ScalarMappable(norm=dnorm, cmap=dcmap), cax=caxD)
cb.set_label("$u_z - u_{z,\\min}$ (µm)", labelpad=2)
cb.outline.set_linewidth(0.4)

vmax_j = max(d["js"]["critical"]["du_um"] for d in data.values())
jnorm = mcolors.Normalize(0, vmax_j)
jcmap = plt.get_cmap("Purples")
for k, a in enumerate(ARCHS):
    js = data[a]["js"]
    xy = np.array([[r["x_mm"], r["y_mm"]] for r in js["ranked"]])
    du = np.array([r["du_um"] for r in js["ranked"]])
    ax = axJ[k]
    ax.scatter(xy[:, 0], xy[:, 1], c=du, s=1.1, cmap=jcmap, norm=jnorm, lw=0)
    c = js["critical"]
    ax.plot(c["x_mm"], c["y_mm"], "o", ms=5.0, mfc="none", mec=S.INK, mew=0.8, clip_on=False)
    ax.set_aspect("equal")
    ax.set_xlim(-15.3, 15.3)
    ax.set_ylim(-15.3, 15.3)
    ax.grid(False)
    ax.set_xticks([-10, 0, 10], ["−10", "0", "10"])
    ax.set_yticks([-10, 0, 10] if k == 0 else [], ["−10", "0", "10"] if k == 0 else [])
    ax.set_xlabel("$x$ (mm)", labelpad=1)
    if k == 0:
        ax.set_ylabel("$y$ (mm)", labelpad=0)
    S.panel(ax, LET[2 * N + k], f"{a}: {c['du_um']:.2f} µm", y=1.02)
cb = fig.colorbar(plt.cm.ScalarMappable(norm=jnorm, cmap=jcmap), cax=caxJ)
cb.set_label("$\\Delta u$ across balls (µm)", labelpad=2)
cb.outline.set_linewidth(0.4)
S.save(fig, "fig7_fields")
