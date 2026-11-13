"""Fig. 7 (proposed): converged fields of the two architectures at S0.

(a,b) Temperature on the vertical section y = 0 (middle row of cells), drawn element by
      element so voids (PCB opening, sidewall ring) stay empty; shared heat scale.
(c,d) Out-of-plane displacement of the die top surface relative to its lowest point
      (peak-to-valley = die warpage); shared scale.
(e)   In-plane relative displacement across the ball layer at every legal BGA site
      (Z1 full array, Z2 ring around the opening); critical joint circled; shared scale.
Data: converged production fields ($HVR_FIELDS/etm_*_HV_S0_r21) and the case files.
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
CASE = {"Z1": "etm_Z1_HV_S0_h1.1_r21.json", "Z2": "etm_Z2_HV_S0_h1.1_r21.json"}
VEX = 3.0                                   # vertical exaggeration of the sections


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
    val = field[ci].mean(1)
    return polys, val


def die_top(ds, dt, a):
    xyz = ds["xyz"]
    uz = ds["DISP"][:, 2] * 1e3            # mm -> um
    zt = 2.583 if a == "Z1" else 0.620      # die top (architecture_geometry.json)
    m = (np.abs(xyz[:, 2] - zt) < 1e-6) & (np.abs(xyz[:, 0]) <= 11.18 + 1e-6) & \
        (np.abs(xyz[:, 1]) <= 11.18 + 1e-6)
    return xyz[m, 0], xyz[m, 1], uz[m] - uz[m].min()


fig = plt.figure(figsize=(S.DBL_W, 4.30))
# row 1: sections
axS = [fig.add_axes([0.055, 0.545, 0.415, 0.42]), fig.add_axes([0.505, 0.545, 0.415, 0.42])]
caxT = fig.add_axes([0.935, 0.60, 0.011, 0.31])
# row 2: die maps and joint maps
axD = [fig.add_axes([0.055, 0.075, 0.17, 0.39]), fig.add_axes([0.235, 0.075, 0.17, 0.39])]
caxD = fig.add_axes([0.415, 0.10, 0.010, 0.33])
axJ = [fig.add_axes([0.535, 0.075, 0.17, 0.39]), fig.add_axes([0.715, 0.075, 0.17, 0.39])]
caxJ = fig.add_axes([0.895, 0.10, 0.010, 0.33])

tnorm = mcolors.Normalize(85, 125)
tcmap = plt.get_cmap("YlOrRd")
dd, jj = {}, {}
for a in ("Z1", "Z2"):
    dt = frd.read(F / f"etm_{a}_HV_S0_r21" / "thermal_converged.frd")
    ds = frd.read(F / f"etm_{a}_HV_S0_r21" / "structural.frd")
    T = dt["NDTEMP"][:, 0]
    polys, val = section(dt, T)
    ax = axS[0 if a == "Z1" else 1]
    pc = PolyCollection(polys, array=val, cmap=tcmap, norm=tnorm, edgecolors="face",
                        linewidths=0.05)
    ax.add_collection(pc)
    ax.set_xlim(-15.2, 15.2)
    ax.set_ylim(-2.75 * VEX, 2.70 * VEX)
    ax.set_aspect("equal")
    ax.grid(False)
    ax.set_yticks(np.array([-2, -1, 0, 1, 2]) * VEX, ["−2", "−1", "0", "1", "2"])
    ax.set_xlabel("$x$ (mm)", labelpad=1)
    if a == "Z1":
        ax.set_ylabel("$z$ (mm)", labelpad=1)
    tmax = T.max()
    S.panel(ax, "ab"[a == "Z2"], f"{'Z1 embedded' if a == 'Z1' else 'Z2 backside'}: "
            f"section $y$ = 0 (vertical ×{VEX:g}), $T_\\max$ = {tmax:.1f} °C", y=1.02)
    dd[a] = die_top(ds, dt, a)
    case = json.loads((S.FC / CASE[a]).read_text())
    jj[a] = case["mechanics"]["joint_search"]

# section labels (sparse, with halo)
def lab(ax, x, z, s, ha="center"):
    ax.text(x, z * VEX, s, ha=ha, va="center", fontsize=6.2, color=S.INK,
            bbox=dict(boxstyle="square,pad=0.1", fc="white", ec="none", alpha=0.75))
lab(axS[0], 0, 2.43, "die")
lab(axS[0], -13.2, 1.3, "encapsulant", ha="left")
lab(axS[0], 0, 0.95, "converter tiers (49 cells)")
lab(axS[0], 0, 0.15, "Si substrate + TSVs")
lab(axS[0], 0, -1.6, "PCB")
lab(axS[1], 0, 0.47, "die / substrate")
lab(axS[1], 0, -1.2, "converter in PCB opening")
lab(axS[1], -13.4, -1.6, "PCB", ha="left")
for ax in axS:
    pass
cb = fig.colorbar(plt.cm.ScalarMappable(norm=tnorm, cmap=tcmap), cax=caxT)
cb.set_label("Temperature (°C)", labelpad=2)
cb.ax.text(0.5, -0.06, "≤85", transform=cb.ax.transAxes, ha="center", va="top", fontsize=6, color=S.INK2)
cb.outline.set_linewidth(0.4)

# die warpage maps, shared scale
vmax_d = max(dd[a][2].max() for a in dd)
dnorm = mcolors.Normalize(0, vmax_d)
dcmap = plt.get_cmap("Blues")
for k, a in enumerate(("Z1", "Z2")):
    x, y, u = dd[a]
    ax = axD[k]
    ax.tricontourf(x, y, u, levels=np.linspace(0, vmax_d, 15), cmap=dcmap, norm=dnorm)
    ax.set_aspect("equal")
    ax.set_xlim(-11.2, 11.2)
    ax.set_ylim(-11.2, 11.2)
    ax.grid(False)
    ax.set_xticks([-10, 0, 10])
    ax.set_yticks([-10, 0, 10] if k == 0 else [])
    ax.set_xlabel("$x$ (mm)", labelpad=1)
    if k == 0:
        ax.set_ylabel("$y$ (mm)", labelpad=0)
    S.panel(ax, "cd"[k], f"{a} die, P–V {u.max():.1f} µm", y=1.02)
cb = fig.colorbar(plt.cm.ScalarMappable(norm=dnorm, cmap=dcmap), cax=caxD)
cb.set_label("$u_z - u_{z,\\min}$ (µm)", labelpad=2)
cb.outline.set_linewidth(0.4)

# joint driver at every legal site, shared scale
vmax_j = max(j["critical"]["du_um"] for j in jj.values())
jnorm = mcolors.Normalize(0, vmax_j)
jcmap = plt.get_cmap("Purples")
for k, a in enumerate(("Z1", "Z2")):
    js = jj[a]
    xy = np.array([[r["x_mm"], r["y_mm"]] for r in js["ranked"]])
    du = np.array([r["du_um"] for r in js["ranked"]])
    ax = axJ[k]
    ax.scatter(xy[:, 0], xy[:, 1], c=du, s=1.3, cmap=jcmap, norm=jnorm, lw=0)
    c = js["critical"]
    ax.plot(c["x_mm"], c["y_mm"], "o", ms=5.5, mfc="none", mec=S.INK, mew=0.8)
    ax.set_aspect("equal")
    ax.set_xlim(-15.3, 15.3)
    ax.set_ylim(-15.3, 15.3)
    ax.grid(False)
    ax.set_xticks([-10, 0, 10])
    ax.set_yticks([-10, 0, 10] if k == 0 else [])
    ax.set_xlabel("$x$ (mm)", labelpad=1)
    if k == 0:
        ax.set_ylabel("$y$ (mm)", labelpad=0)
    S.panel(ax, "ef"[k], f"{a} balls, max {c['du_um']:.2f} µm", y=1.02)
cb = fig.colorbar(plt.cm.ScalarMappable(norm=jnorm, cmap=jcmap), cax=caxJ)
cb.set_label("$\\Delta u$ across ball layer (µm)", labelpad=2)
cb.outline.set_linewidth(0.4)
S.save(fig, "fig7_fields")
