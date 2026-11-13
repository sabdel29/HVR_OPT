"""Fig. 3 (proposed): the two package constructions, to scale, from the solver mesh record.

Right half-sections (x = 0 is the package centre line) of Z1 and Z2 on one z-scale,
aligned at the PCB backside, vertical exaggeration VEX. Every z-extent and the tier
ORDER are read from architecture_geometry.json, so a re-run with a different stack
redraws the figure. 10-um RDL tiers are drawn as lines (true thickness < line width).
Rails: 48 V (red) and 1 V (violet) paths, schematic in x. Critical joint ringed.
"""
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Ellipse, FancyArrowPatch
import style as S

S.setup()
G = S.J("architecture_geometry.json")["architectures"]
VEX = 2.4
HALF, CELL, PITCH, GRID_HALF, DIE_HALF = 15.0, 2.3685, 3.1652, 10.68, 11.18
CUT_HALF = 11.68
CELL_X = [0.0, PITCH, 2 * PITCH, 3 * PITCH]          # centres of the middle row (x >= 0)
COLOR = {"hs": S.MAT["gan"], "ls": S.MAT["gan"], "caps": S.MAT["caps"],
         "ind": S.MAT["inductor"], "die": S.MAT["die"], "tim": S.MAT["tim"]}
NAME = {"hs": "HS GaN", "ls": "LS GaN", "caps": "$C_\\mathrm{f}$", "ind": "$L$ + $C_\\mathrm{o}$"}


def Z(z_um):
    return z_um / 1000.0 * VEX


def cells_and_fill(ax, z0, z1, col, fill_to, fill=S.MAT["fill"]):
    """cells inside |x| <= GRID_HALF on the middle row; encapsulant between them up to fill_to"""
    ax.add_patch(Rectangle((0, Z(z0)), fill_to, Z(z1) - Z(z0), fc=fill, ec="none", zorder=1))
    for xc in CELL_X:
        x0 = max(0.0, xc - CELL / 2)
        ax.add_patch(Rectangle((x0, Z(z0)), xc + CELL / 2 - x0, Z(z1) - Z(z0), fc=col,
                               ec="none", zorder=2))


def balls(ax, x_from, x_to, z0=-300, z1=0, pitch=0.8, ring_last=True):
    xs = np.arange(x_from + pitch / 2, x_to, pitch)
    for x in xs:
        ax.add_patch(Ellipse((x, Z((z0 + z1) / 2)), 0.5, Z(z1) - Z(z0), fc=S.MAT["solder"],
                             ec="#8d939b", lw=0.3, zorder=3))
    if ring_last and len(xs):
        ax.add_patch(Ellipse((xs[-1], Z((z0 + z1) / 2)), 0.95, (Z(z1) - Z(z0)) * 1.6,
                             fc="none", ec=S.INK, lw=0.9, zorder=6))
        return xs[-1]


def rail(ax, pts, col, lw=1.6):
    pts = [(x, Z(z)) for x, z in pts]
    for (xa, ya), (xb, yb) in zip(pts[:-2], pts[1:-1]):
        ax.plot([xa, xb], [ya, yb], color=col, lw=lw, solid_capstyle="butt", zorder=7)
    ax.add_patch(FancyArrowPatch(pts[-2], pts[-1], arrowstyle="-|>", mutation_scale=7,
                                 color=col, lw=lw, zorder=7, shrinkA=0, shrinkB=0))


def label(ax, z_um, text, x_edge, y_text=None):
    yt = Z(z_um) if y_text is None else y_text
    ax.annotate(text, (x_edge, Z(z_um)), xytext=(HALF + 1.2, yt), textcoords="data",
                ha="left", va="center", fontsize=6.3, color=S.INK,
                arrowprops=dict(arrowstyle="-", color=S.MUTED, lw=0.45,
                                shrinkA=0, shrinkB=0))


def draw(ax, a):
    A = G[a]
    L = {l["name"]: l for l in A["layers"]}
    conv = [l for l in A["layers"] if any(r in l["roles"] for r in ("hs", "ls", "caps", "ind"))]
    rdls = [l for l in A["layers"] if "rdl" in l["roles"]]
    z1 = a == "Z1"
    # board and BGA
    bx0 = 0.0 if z1 else CUT_HALF
    ax.add_patch(Rectangle((bx0, Z(-2700)), HALF - bx0, Z(-300) - Z(-2700), fc=S.MAT["pcb"],
                           ec="none", zorder=1))
    crit = balls(ax, bx0, HALF)
    # substrate (+ TSVs under the cells)
    ax.add_patch(Rectangle((0, Z(0)), HALF, Z(300) - Z(0), fc=S.MAT["silicon"], ec="none",
                           zorder=1))
    for xc in CELL_X:
        for xt in np.linspace(max(0.15, xc - CELL / 2 + 0.2), xc + CELL / 2 - 0.2, 6):
            ax.plot([xt, xt], [Z(0), Z(300)], color=S.MAT["tsv"], lw=0.5, zorder=2)
    # converter tiers
    fill_to = HALF if z1 else GRID_HALF
    for l in conv:
        role = next(r for r in ("hs", "ls", "caps", "ind") if r in l["roles"])
        cells_and_fill(ax, l["z0_um"], l["z1_um"], COLOR[role], fill_to)
    # attach (Z2)
    if not z1:
        at = L["conv_attach_vr_substrate"]
        cells_and_fill(ax, at["z0_um"], at["z1_um"], S.MAT["attach"], GRID_HALF)
    # RDL tiers as lines across the converter footprint
    for l in rdls:
        zc = 0.5 * (l["z0_um"] + l["z1_um"])
        ax.plot([0, fill_to], [Z(zc), Z(zc)], color=S.MAT["rdl"], lw=0.9, zorder=4)
    top_rdl = L.get("z2_top_rdl")
    if top_rdl:
        ax.plot([0, HALF], [Z(305), Z(305)], color=S.MAT["rdl"], lw=0.9, zorder=4)
    # die, TIM, cold plate
    for nm, col in (("interface", S.MAT["solder"]), ("die", S.MAT["die"]), ("tim", S.MAT["tim"])):
        l = L[nm]
        ax.add_patch(Rectangle((0, Z(l["z0_um"])), DIE_HALF, Z(l["z1_um"]) - Z(l["z0_um"]),
                               fc=col, ec="none", zorder=2))
    ztop = L["tim"]["z1_um"]
    ax.add_patch(Rectangle((0, Z(ztop)), DIE_HALF + 0.8, Z(ztop + 400) - Z(ztop),
                           fc=S.MAT["coldplate"], ec="none", zorder=2))
    for xc in np.arange(0.4, DIE_HALF + 0.6, 0.9):
        ax.add_patch(Rectangle((xc, Z(ztop + 90)), 0.35, Z(ztop + 310) - Z(ztop + 90),
                               fc="white", ec="none", zorder=3))
    # rails (schematic in x, true in z) through the outermost full cell
    xc = CELL_X[2]
    hs = next(l for l in conv if "hs" in l["roles"])
    ind = next(l for l in conv if "ind" in l["roles"])
    zdie = L["interface"]["z0_um"]
    if z1:
        xb = 12.4
        rail(ax, [(xb, -2700), (xb, -150), (xb, -40), (xc + 0.5, -40), (xc + 0.5, 150),
                  (xc + 0.5, hs["z0_um"] + 180)], S.V48)
        rail(ax, [(xc - 0.5, ind["z1_um"] - 120), (xc - 0.5, zdie + 200)], S.V1)
    else:
        rail(ax, [(xc + 0.5, -2700), (xc + 0.5, hs["z0_um"] + 180)], S.V48)
        rail(ax, [(xc - 0.5, ind["z0_um"] + 250), (xc - 0.5, zdie + 200)], S.V1)
    # conversion bracket
    zc0, zc1 = min(l["z0_um"] for l in conv), max(l["z1_um"] for l in conv)
    ax.plot([xc + 1.45] * 2, [Z(zc0) + 0.05, Z(zc1) - 0.05], color=S.INK2, lw=0.6, zorder=6)
    ax.text(xc + 1.62, Z((zc0 + zc1) / 2), "conversion", rotation=90, ha="left",
            va="center", fontsize=5.8, color=S.INK2, zorder=6)
    # labels (right side)
    edge = HALF if z1 else GRID_HALF
    labs = [(0.5 * (L["die"]["z0_um"] + L["die"]["z1_um"]), "die 300 µm", DIE_HALF)]
    for l in sorted(conv, key=lambda l: -l["z0_um"]):
        role = next(r for r in ("hs", "ls", "caps", "ind") if r in l["roles"])
        labs.append((0.5 * (l["z0_um"] + l["z1_um"]), f"{NAME[role]}  {l['t_um']:.0f} µm", edge))
    if not z1:
        labs.append((-15, "Cu-pillar attach 30 µm", GRID_HALF))
    labs += [(150, "Si substrate 300 µm, TSVs", HALF),
             (-150, "BGA 300 µm", HALF), (-1500 if z1 else -2350, "PCB 2.4 mm", HALF)]
    # spread label rows symmetrically (min gap d), keeping them near their targets
    tg = np.array([Z(z) for z, _, _ in labs])
    order = np.argsort(tg)[::-1]
    y = tg[order].copy()
    d = 0.62
    for _ in range(400):
        moved = False
        for i in range(len(y) - 1):
            gap = y[i] - y[i + 1]
            if gap < d:
                sh = (d - gap) / 2 + 1e-4
                y[i] += sh
                y[i + 1] -= sh
                moved = True
        if not moved:
            break
    for yi, i in zip(y, order):
        z, t, xe = labs[i]
        label(ax, z, t, xe, y_text=yi)
    ax.plot([0, 0], [Z(-2750), Z(ztop + 450)], color=S.MUTED, lw=0.5, ls=(0, (3, 2)))
    ax.set_xlim(-0.3, HALF + 7.6)
    ax.set_ylim(Z(-2800), Z(3200))
    ax.set_aspect("equal")
    ax.axis("off")
    return crit


fig, axes = plt.subplots(1, 2, figsize=(S.DBL_W, 2.75),
                         gridspec_kw={"wspace": 0.02, "left": 0.01, "right": 0.995,
                                      "bottom": 0.02, "top": 0.90})
for k, a in enumerate(("Z1", "Z2")):
    draw(axes[k], a)
    t = ("Z1 embedded: 48 V crosses the substrate" if a == "Z1" else
         "Z2 backside, in the PCB opening: 1 V crosses the substrate")
    S.panel(axes[k], "ab"[k], t, x=0.0, y=1.0)
# z scale bar (true thickness) and legend
ax = axes[0]
ax.plot([-0.2, -0.2], [Z(-2700), Z(-1700)], color=S.INK, lw=0.8)
ax.text(0.15, Z(-2200), "1 mm", ha="left", va="center", fontsize=6, color=S.INK,
        rotation=90)
fig.text(0.50, 0.005, "Half sections, $x \\geq 0$, to scale in $z$ (vertical ×%g); "
         "10-µm RDL tiers drawn as lines. Red: 48-V input path; violet: 1-V output path; "
         "ringed ball: critical joint." % VEX, ha="center", va="bottom", fontsize=6.4,
         color=S.INK2)
S.save(fig, "fig3_sections")
