"""Fig. 7: converged fields of every integration in the production state (implemented
decoupling: two interleaved 6-phase clock groups and a ring of input capacitors) under
cooling A (the same top cold plate).

(a)-(c) Temperature on the vertical section y = 0 (middle row of cells), drawn element by
        element so voids (board opening, sidewall ring) stay empty; shared heat scale.
(d)-(f) Out-of-plane displacement of the die top surface relative to its lowest point
        (peak-to-valley = die warpage); shared scale.
(g)-(i) In-plane relative displacement across the ball layer at every legal BGA site; the
        joint of largest du ringed and, where it lies elsewhere, the critical joint (largest
        joint response of the production local model, solder_critical_v2.json) marked by a
        cross; shared scale.
Fields: the production-state runs of the case registry (scripts/tcpmt_cases.py, state SDEC,
cooling A), read from the campaign solver scratch -- the last E-T iteration's last thermal
deck (et<N>/th_<k>.frd) and the structural run (structural.frd) of
<scratch>/fc_sens/sdec_A/<arch>_HV_SDEC_h1.1_r21 -- and accepted only when the deck's peak
temperature matches the case file's T_max (0.05 K). Z3 is the coupled land-side case. The
scratch root is $HVR_SCRATCH, else scratch_campaign/<name of $ETM_RESULTS_ROOT>. A field that
is missing or does not match is reported and its panels are left out (never replaced by
another state's field). The 150-C GaN-rating isotherm is drawn on every section it crosses.
Data: the solver scratch above, the case files (joint search) and architecture_geometry.json
(die-top height).
"""
import json
import os
from pathlib import Path
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
TIER = "A"                                  # cooling A: the same top cold plate
STATE = S.PROD                              # the production input state (implemented decoupling)
SCEN = S.TC.SCEN[STATE]


def _scratch_roots():
    roots = [Path(os.environ["HVR_SCRATCH"])] if os.environ.get("HVR_SCRATCH") else []
    rr = os.environ.get("ETM_RESULTS_ROOT")
    if rr:
        roots.append(Path("/home/beams0/SABDELZAHER/ETM_project/scratch_campaign")
                     / Path(rr).resolve().name)
    return roots


def _field_pair(arch, variant):
    """(last thermal deck, structural run) of one production-state run, or None"""
    for r in _scratch_roots():
        wd = r / "fc_sens" / variant / f"{arch}_{SCEN}_h1.1_r21"
        its = sorted(wd.glob("et*"), key=lambda p: int(p.name[2:])) if wd.is_dir() else []
        if its and (wd / "structural.frd").is_file():
            ths = sorted(its[-1].glob("th_*.frd"), key=lambda p: int(p.stem.split("_")[1]))
            if ths:
                return ths[-1], wd / "structural.frd"
    return None


SRC_FIELD, NOTES = {}, []
for _a in ("Z1", "Z2", "Z3"):
    _cp = S.TC.case_path(STATE, TIER, _a)
    if _cp is None:
        NOTES.append(f"{_a}: no production-state case for cooling {TIER}")
        continue
    _case = json.loads(Path(_cp).read_text())
    _variant = (_case.get("variant") or {}).get("name") or f"sdec_{TIER}"
    _pair = _field_pair(_a, _variant)
    if _pair is None:
        NOTES.append(f"{_a}: fields of {_variant} not found in {[str(r) for r in _scratch_roots()]}")
        continue
    _tl = float(frd.read(_pair[0])["NDTEMP"][:, 0].max())
    _tc = float(_case["thermal"]["T_max_C"])
    if abs(_tl - _tc) >= 0.05:
        NOTES.append(f"{_a}: field T_max {_tl:.2f} C does not match the case {_tc:.2f} C")
        continue
    SRC_FIELD[_a] = (_pair, _case)
for _n in NOTES:
    print("NOTE:", _n)
ARCHS = [a for a in ("Z1", "Z2", "Z3") if a in SRC_FIELD]
if not ARCHS:
    raise SystemExit("no production-state field matches its case file: " + "; ".join(NOTES))
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
    case = SRC_FIELD[a][1]
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
        ax.text(1.0, 1.02, "coupled land side", transform=ax.transAxes,
                ha="right", va="bottom", fontsize=6.5, color=S.INK2)
cb = fig.colorbar(plt.cm.ScalarMappable(norm=tnorm, cmap=tcmap), cax=caxT)
cb.set_label("Temperature (°C)", labelpad=2)
if GAN:
    cb.ax.axhline(GAN, color=S.INK, lw=0.7, ls=(0, (3, 1.5)))
    if iso_drawn:
        # in the empty lower part of the first section panel (its section is the shallowest),
        # clear of the row titles below the sections
        axS[0].text(0.03, 0.04, f"dashed: {GAN:.0f}-°C GaN-rating isotherm",
                    transform=axS[0].transAxes, ha="left", va="bottom", fontsize=6.5,
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
#: the critical joint of the production local model (largest response over the lattice)
_CRIT = (S.JP(S.TR / "solder_critical_v2.json") or {}).get("cases") or {}


def crit_site(a):
    r = (_CRIT.get(f"{STATE}_{TIER}_{a}") or {}).get("max_response_site") or {}
    return (r["x_mm"], r["y_mm"]) if r.get("x_mm") is not None else None


def mirror(p, q, tol=1e-6):
    return (abs(sorted((abs(p[0]), abs(p[1])))[0] - sorted((abs(q[0]), abs(q[1])))[0]) < tol and
            abs(sorted((abs(p[0]), abs(p[1])))[1] - sorted((abs(q[0]), abs(q[1])))[1]) < tol)
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
    cs = crit_site(a)
    if cs is not None and not mirror(cs, (c["x_mm"], c["y_mm"])):
        ax.plot(cs[0], cs[1], "x", ms=4.6, mec=S.INK, mew=1.0, clip_on=False, zorder=8)
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
