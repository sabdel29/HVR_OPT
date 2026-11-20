"""Fig. 3: the three package constructions, to scale, from the solver mesh record.

Right half-sections (x = 0 is the package center line) of Z1, Z2 and Z3 on one z-scale,
aligned at the PCB backside, vertical exaggeration VEX. Every z-extent, the tier ORDER and the
plan geometry (package, die and opening half-widths, cell side and the cell centres of the row
nearest the center line) are read from architecture_geometry.json, so a re-run with a different
stack or cell grid redraws the figure. A converter tier holds the parts of the design record's
tier (mixed tiers: split by part footprint, labelled with their contents). 10-um RDL tiers are
drawn as lines (true thickness < line width). Rails: 48 V (red) and 1 V (violet) paths,
schematic in x, from the input-end tier (high side) and the output-end tier (inductors).
Critical joint ringed.
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Ellipse, FancyArrowPatch
import style as S

S.setup()
G = S.J("architecture_geometry.json")["architectures"]
VEX = 2.4
_G0 = G.get("Z1") or next(iter(G.values()))
HALF = 0.5 * float(_G0["substrate_mm"][0])                   # package (substrate) half width
DIE_HALF = 0.5 * float(_G0["die_mm"][0])
CUT_HALF = 0.5 * float((G.get("Z2") or {}).get("cutout_mm") or S.DR.pkg_cutout_mm())
CELL = float(_G0["cells"]["side_mm"])
_CX = sorted(float(x) for x in _G0["cells"]["centres_x_mm"])
GRID_HALF = max(_CX) + CELL / 2                               # outer edge of the cell grid
CELL_X = [x for x in _CX if x >= -1e-9]                       # the row nearest y = 0, x >= 0
#: the cell the rails are drawn through: the one nearest 60 % of the grid half width
XC_RAIL = min(CELL_X, key=lambda x: abs(x - 0.6 * GRID_HALF))
ROLES = ("hs", "ls", "caps", "ind")


def Z(z_um):
    return z_um / 1000.0 * VEX


def cells_and_fill(ax, z0, z1, col, fill_to, fill=S.MAT["fill"]):
    """cells inside |x| <= GRID_HALF on the row nearest y = 0; encapsulant between them up to
    fill_to"""
    ax.add_patch(Rectangle((0, Z(z0)), fill_to, Z(z1) - Z(z0), fc=fill, ec="none", zorder=1))
    for xc in CELL_X:
        x0 = max(0.0, xc - CELL / 2)
        ax.add_patch(Rectangle((x0, Z(z0)), xc + CELL / 2 - x0, Z(z1) - Z(z0), fc=col,
                               ec="none", zorder=2))


def tier_cells(ax, layer, fill_to, fill=S.MAT["fill"]):
    """a converter tier: every cell split by the part footprints of the record's tier"""
    z0, z1 = layer["z0_um"], layer["z1_um"]
    ax.add_patch(Rectangle((0, Z(z0)), fill_to, Z(z1) - Z(z0), fc=fill, ec="none", zorder=1))
    segs = S.tier_fill(S.layer_parts(layer))
    for xc in CELL_X:
        xa = xc - CELL / 2
        for c, f in segs:
            xb = xa + f * CELL
            x0 = max(0.0, xa)
            if xb > x0:
                ax.add_patch(Rectangle((x0, Z(z0)), xb - x0, Z(z1) - Z(z0),
                                       fc=S.CLASS_COLOR[c], ec="white", lw=0.3, zorder=2))
            xa = xb


def balls(ax, x_from, x_to, z0, z1, pitch=0.8, ring_last=True):
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
                ha="left", va="center", fontsize=6.1, color=S.INK,
                arrowprops=dict(arrowstyle="-", color=S.MUTED, lw=0.45,
                                shrinkA=0, shrinkB=0))


def mid(l):
    return 0.5 * (l["z0_um"] + l["z1_um"])


def thick(l):
    return float(l.get("t_um") or (l["z1_um"] - l["z0_um"]))


def draw(ax, a):
    A = G[a]
    L = {l["name"]: l for l in A["layers"]}
    conv = [l for l in A["layers"] if any(r in l["roles"] for r in ROLES)]
    rdls = [l for l in A["layers"] if "rdl" in l["roles"]]
    brd, bga = L["board"], L["bga"]
    sub = [l for l in A["layers"] if l["name"] in ("sub_lower", "tile_band")] or \
        [l for l in A["layers"] if "tsv" in l["roles"]]
    zs0, zs1 = min(l["z0_um"] for l in sub), max(l["z1_um"] for l in sub)
    z1 = a == "Z1"
    z3 = a == "Z3"
    # board and BGA (Z2: board and balls outside the opening only)
    bx0 = CUT_HALF if a == "Z2" else 0.0
    ax.add_patch(Rectangle((bx0, Z(brd["z0_um"])), HALF - bx0,
                           Z(brd["z1_um"]) - Z(brd["z0_um"]), fc=S.MAT["pcb"], ec="none",
                           zorder=1))
    crit = balls(ax, bx0, HALF, bga["z0_um"], bga["z1_um"])
    if z3:                                   # 1 V plated through-holes under the cells
        for xc in CELL_X:
            for xt in np.linspace(max(0.25, xc - CELL / 2 + 0.3), xc + CELL / 2 - 0.3, 5):
                ax.plot([xt, xt], [Z(brd["z0_um"]), Z(brd["z1_um"])], color="#c9a46a",
                        lw=0.55, zorder=2)
    # substrate (+ TSVs under the cells)
    ax.add_patch(Rectangle((0, Z(zs0)), HALF, Z(zs1) - Z(zs0), fc=S.MAT["silicon"], ec="none",
                           zorder=1))
    for xc in CELL_X:
        for xt in np.linspace(max(0.15, xc - CELL / 2 + 0.2), xc + CELL / 2 - 0.2, 6):
            ax.plot([xt, xt], [Z(zs0), Z(zs1)], color=S.MAT["tsv"], lw=0.5, zorder=2)
    # converter tiers (mixed: the record's contents, split by part footprint)
    fill_to = HALF if z1 else GRID_HALF
    for l in conv:
        tier_cells(ax, l, fill_to)
    # attach (Z2: Cu pillar to the substrate; Z3: solder bumps to the board)
    at = next((l for l in A["layers"] if "attach" in l["roles"]), None)
    if not z1 and at:
        cells_and_fill(ax, at["z0_um"], at["z1_um"], S.MAT["attach"], GRID_HALF)
    if z3:                                   # the converter's own cold plate underneath
        zb = min(l["z0_um"] for l in conv)
        ax.add_patch(Rectangle((0, Z(zb - 400)), GRID_HALF + 0.8, Z(zb) - Z(zb - 400),
                               fc=S.MAT["coldplate"], ec="none", zorder=2))
        for xc in np.arange(0.4, GRID_HALF + 0.6, 0.9):
            ax.add_patch(Rectangle((xc, Z(zb - 310)), 0.35, Z(zb - 90) - Z(zb - 310),
                                   fc="white", ec="none", zorder=3))
    # RDL tiers as lines across the converter footprint
    for l in rdls:
        ax.plot([0, fill_to], [Z(mid(l)), Z(mid(l))], color=S.MAT["rdl"], lw=0.9, zorder=4)
    top_rdl = L.get("z2_top_rdl")
    if top_rdl:
        ax.plot([0, HALF], [Z(mid(top_rdl))] * 2, color=S.MAT["rdl"], lw=0.9, zorder=4)
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
    # rails (schematic in x, true in z): 48 V into the input-end (high-side) tier, 1 V out of
    # the output-end (inductor) tier
    xc = XC_RAIL
    hs = min((l for l in conv if "hs" in l["roles"]), key=lambda l: l["z0_um"])
    ind = max((l for l in conv if "ind" in l["roles"]), key=lambda l: l["z1_um"])
    zdie = L["interface"]["z0_um"]
    if z1:
        xb = DIE_HALF + 0.35 * (HALF - DIE_HALF)
        zl = bga["z1_um"] - 40.0
        rail(ax, [(xb, brd["z0_um"]), (xb, zl), (xc + 0.5, zl), (xc + 0.5, hs["z0_um"] + 180)],
             S.V48)
        rail(ax, [(xc - 0.5, ind["z1_um"] - 120), (xc - 0.5, zdie + 200)], S.V1)
    elif z3:
        rail(ax, [(xc + 0.5, hs["z0_um"] - 500), (xc + 0.5, hs["z1_um"] - 180)], S.V48)
        rail(ax, [(xc - 0.5, ind["z0_um"] + 150), (xc - 0.5, zdie + 200)], S.V1)
    else:
        rail(ax, [(xc + 0.5, brd["z0_um"]), (xc + 0.5, hs["z0_um"] + 180)], S.V48)
        rail(ax, [(xc - 0.5, ind["z0_um"] + 250), (xc - 0.5, zdie + 200)], S.V1)
    # conversion bracket
    zc0, zc1 = min(l["z0_um"] for l in conv), max(l["z1_um"] for l in conv)
    ax.plot([xc + 1.45] * 2, [Z(zc0) + 0.05, Z(zc1) - 0.05], color=S.INK2, lw=0.6, zorder=6)
    ax.text(xc + 1.62, Z((zc0 + zc1) / 2), "conversion", rotation=90, ha="left",
            va="center", fontsize=5.8, color=S.INK2, zorder=6)
    # labels (right side): every thickness from the mesh record
    edge = HALF if z1 else GRID_HALF
    labs = [(mid(L["die"]), f"die {thick(L['die']):.0f} µm", DIE_HALF)]
    for l in sorted(conv, key=lambda l: -l["z0_um"]):
        labs.append((mid(l), f"{S.tier_label(S.layer_parts(l))}  {thick(l):.0f} µm", edge))
    if a == "Z2" and at:
        labs.append((mid(at), f"Cu pillar {thick(at):.0f} µm", GRID_HALF))
    if z3 and at:
        labs.append((mid(at), f"solder {thick(at):.0f} µm", GRID_HALF))
        labs.append((min(l["z0_um"] for l in conv) - 200, "cold plate", GRID_HALF + 0.8))
    tb = thick(brd)
    z_brd = (brd["z0_um"] + 0.15 * tb) if a == "Z2" else mid(brd)
    labs += [(0.5 * (zs0 + zs1), f"Si + TSVs {zs1 - zs0:.0f} µm", HALF),
             (mid(bga), f"BGA {thick(bga):.0f} µm", HALF),
             (z_brd, f"PCB {tb / 1000:.1f} mm" + (" + vias" if z3 else ""), HALF)]
    # spread label rows symmetrically (min gap d), keeping them near their targets
    tg = np.array([Z(z) for z, _, _ in labs])
    order = np.argsort(tg)[::-1]
    y = tg[order].copy()
    d = 0.82
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
    zlo = min(l["z0_um"] for l in A["layers"]) - (450 if z3 else 50)
    ax.plot([0, 0], [Z(zlo), Z(ztop + 450)], color=S.MUTED, lw=0.5, ls=(0, (3, 2)))
    ax.set_xlim(-0.3, HALF + 8.4)
    ax.set_ylim(Z(ZMIN), Z(ZTOP))
    ax.set_aspect("equal")
    ax.axis("off")
    return crit


ARCHS = [a for a in ("Z1", "Z2", "Z3") if a in G]
ZMIN = min(min(l["z0_um"] for l in G[a]["layers"]) for a in ARCHS) - 480
ZTOP = max(max(l["z1_um"] for l in G[a]["layers"]) for a in ARCHS) + 400 + 130
# the panels are drawn at equal aspect: the figure height follows the stacks' z range
_w_units = HALF + 8.7
_h_units = Z(ZTOP) - Z(ZMIN)
_panel_w = S.DBL_W * 0.985 / len(ARCHS)
FIG_H = min(max(2.62, _panel_w * _h_units / _w_units / 0.92 + 0.05), 4.2)
fig, axes = plt.subplots(1, len(ARCHS), figsize=(S.DBL_W, FIG_H),
                         gridspec_kw={"wspace": 0.02, "left": 0.01, "right": 0.995,
                                      "bottom": 0.01, "top": 1 - 0.19 / FIG_H})
TITLE = {"Z1": "Z1 embedded: 48 V crosses the substrate",
         "Z2": "Z2 package backside: 1 V crosses the substrate",
         "Z3": "Z3 board backside: 1 V crosses board and substrate"}
for k, a in enumerate(ARCHS):
    draw(axes[k], a)
    S.panel(axes[k], "abc"[k], TITLE[a], x=0.0, y=1.0)
# z scale bar (true thickness) under the first panel's stack
ax = axes[0]
_zb = min(l["z0_um"] for l in G[ARCHS[0]]["layers"])
ax.plot([-0.2, -0.2], [Z(_zb - 1200), Z(_zb - 200)], color=S.INK, lw=0.8)
ax.text(0.15, Z(_zb - 700), "1 mm", ha="left", va="center", fontsize=6, color=S.INK,
        rotation=90)
# (the caption carries the drawing conventions; nothing is printed under the panels)
S.save(fig, "fig3_sections")
