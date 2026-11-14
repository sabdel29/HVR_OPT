"""Fig. 7: converged fields of every integration at S0.

(a)-(c) Temperature on the vertical section y = 0 (middle row of cells), drawn element by
        element so voids (board opening, sidewall ring) stay empty; shared heat scale.
(d)-(f) Out-of-plane displacement of the die top surface relative to its lowest point
        (peak-to-valley = die warpage); shared scale.
(g)-(i) In-plane relative displacement across the ball layer at every legal BGA site;
        critical joint ringed; shared scale.
Data: converged production fields ($HVR_FIELDS/etm_*_HV_S0_r21), the case files and
architecture_geometry.json (die-top height).
"""
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib import colors as mcolors
import style as S
import frd

S.setup()
F = S.FIELDS
ARCHS = [a for a in ("Z1", "Z2", "Z3") if (F / f"etm_{a}_HV_S0_r21" / "structural.frd").exists()]
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
    dt = frd.read(F / f"etm_{a}_HV_S0_r21" / "thermal_converged.frd")
    ds = frd.read(F / f"etm_{a}_HV_S0_r21" / "structural.frd")
    case = json.loads((S.FC / f"etm_{a}_HV_S0_h1.1_r21.json").read_text())
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
cb = fig.colorbar(plt.cm.ScalarMappable(norm=tnorm, cmap=tcmap), cax=caxT)
cb.set_label("Temperature (°C)", labelpad=2)
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
