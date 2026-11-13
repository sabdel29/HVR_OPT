"""Fig. 1: the question and the method.

(a)-(c) Three integrations of the same 49 regulator cells: embedded between substrate and
        die (Z1), on the substrate backside inside a board opening (Z2), and on the
        underside of an uncut board (Z3). The integration decides which rail crosses the
        substrate and the board (48 V at ~24 A or 1 V at ~1 kA) and which joints carry the
        deformation.
(d)     The framework: what each stage hands to the next, the electrothermal fixed point,
        and the three modes of use (evaluate, compare, explore).
Schematic, not to scale (the to-scale sections are Fig. 3). Rail colours only.
"""
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, FancyArrowPatch, Ellipse
import style as S

S.setup()
fig = plt.figure(figsize=(S.DBL_W, 2.78))
W_ARCH = 0.158
axs = [fig.add_axes([k * W_ARCH, 0.0, W_ARCH, 0.93]) for k in range(3)]
axd = fig.add_axes([3 * W_ARCH + 0.012, 0.0, 1 - 3 * W_ARCH - 0.012, 0.93])
for ax in axs + [axd]:
    ax.axis("off")
FS = 5.9


def blk(ax, x, y, w, h, fc, txt=None, tc="white", fs=FS):
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec="none"))
    if txt:
        ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center", fontsize=fs, color=tc)


def arrow(ax, pts, col, lw=1.4):
    for (xa, ya), (xb, yb) in zip(pts[:-2], pts[1:-1]):
        ax.plot([xa, xb], [ya, yb], color=col, lw=lw, solid_capstyle="butt")
    ax.add_patch(FancyArrowPatch(pts[-2], pts[-1], arrowstyle="-|>", mutation_scale=7,
                                 color=col, lw=lw, shrinkA=0, shrinkB=0))


def cells(ax, x0, x1, y, h, n=4, flip=False):
    """Encapsulated converter tier: n cells of device (violet) + inductor (brown) tiers."""
    w = (x1 - x0) / (1.5 * n + 0.1)
    blk(ax, x0, y, x1 - x0, h, S.MAT["fill"])
    for k in range(n):
        xc = x0 + 0.3 * w + k * 1.5 * w
        if not flip:
            blk(ax, xc, y + 0.62 * h, w, 0.38 * h, S.MAT["inductor"])
            blk(ax, xc, y, w, 0.62 * h, S.MAT["gan"])
        else:
            blk(ax, xc, y, w, 0.38 * h, S.MAT["inductor"])
            blk(ax, xc, y + 0.38 * h, w, 0.62 * h, S.MAT["gan"])


def balls(ax, xs, y, h, wd=0.36):
    for x in xs:
        ax.add_patch(Ellipse((x, y + h / 2), wd, h, fc=S.MAT["solder"], ec="#8d939b", lw=0.3))


def bumps(ax, x0, x1, y, h, n):
    for k in range(n):
        x = x0 + (k + 0.5) * (x1 - x0) / n
        ax.add_patch(Rectangle((x - 0.09, y), 0.18, h, fc=S.MAT["attach"], ec="none"))


def ring(ax, xy):
    ax.add_patch(Ellipse(xy, 0.8, 1.05, fc="none", ec=S.INK, lw=0.8))


def note(ax, txt):
    ax.text(5.0, 0.15, txt, ha="center", va="bottom", fontsize=FS, color=S.INK,
            linespacing=1.05)


def common_top(ax, die_y):
    blk(ax, 2.0, die_y + 0.85, 6.0, 0.7, S.MAT["coldplate"])
    ax.text(5.0, die_y + 1.2, "cold plate", ha="center", va="center", fontsize=FS, color=S.INK)
    blk(ax, 2.0, die_y, 6.0, 0.8, S.MAT["die"], "die")


for ax in axs:
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12.4)

# ---- (a) Z1 embedded: converter between substrate and die, full BGA, uncut board
ax = axs[0]
common_top(ax, 9.9)
cells(ax, 0.6, 9.4, 7.45, 2.4)
blk(ax, 0.6, 6.8, 8.8, 0.6, S.MAT["silicon"])
ax.text(3.3, 7.1, "substrate", ha="center", va="center", fontsize=FS, color=S.INK)
balls(ax, [0.95 + 0.62 * k for k in range(14)], 6.15, 0.6)
blk(ax, 0.3, 3.4, 9.4, 2.7, S.MAT["pcb"], "board")
arrow(ax, [(7.3, 2.35), (7.3, 6.45), (6.2, 6.45), (6.2, 7.9)], S.V48)
arrow(ax, [(3.6, 9.3), (3.6, 10.2)], S.V1)
ax.text(7.5, 2.6, "48 V", ha="left", va="center", fontsize=FS)
note(ax, "48 V (≈24 A) crosses\nboard, BGA, substrate")
ring(ax, (9.0, 6.45))
S.panel(ax, "a", "Z1 embedded", x=0.04, y=0.975)

# ---- (b) Z2 package backside: converter in a board opening, BGA ring, direct 48-V feed
ax = axs[1]
common_top(ax, 9.9)
blk(ax, 0.6, 9.3, 8.8, 0.6, S.MAT["silicon"])
ax.text(3.6, 9.6, "substrate", ha="center", va="center", fontsize=FS, color=S.INK)
bumps(ax, 1.7, 8.3, 9.05, 0.25, 14)
cells(ax, 1.7, 8.3, 6.55, 2.5, flip=True)
balls(ax, [0.85 + 0.5 * k for k in range(2)] + [8.65 + 0.5 * k for k in range(2)], 8.65, 0.6,
      wd=0.32)
blk(ax, 0.3, 3.4, 1.0, 5.2, S.MAT["pcb"])
blk(ax, 8.7, 3.4, 1.0, 5.2, S.MAT["pcb"])
ax.text(0.8, 5.9, "board", ha="center", va="center", fontsize=FS, color="white", rotation=90)
ax.text(6.35, 5.3, "board\nopening", ha="center", va="center", fontsize=FS, color=S.INK2,
        linespacing=1.0)
arrow(ax, [(3.3, 2.35), (3.3, 7.4)], S.V48)
arrow(ax, [(6.4, 8.6), (6.4, 10.2)], S.V1)
ax.text(3.5, 2.6, "48 V direct", ha="left", va="center", fontsize=FS)
note(ax, "1 V (≈1 kA) crosses\nattach, substrate")
ring(ax, (9.15, 8.95))
S.panel(ax, "b", "Z2 pkg. backside", x=0.04, y=0.975)

# ---- (c) Z3 board backside: converter under an uncut board, its own cold plate
ax = axs[2]
common_top(ax, 9.9)
blk(ax, 0.6, 9.3, 8.8, 0.6, S.MAT["silicon"])
ax.text(3.6, 9.6, "substrate", ha="center", va="center", fontsize=FS, color=S.INK)
balls(ax, [0.95 + 0.62 * k for k in range(14)], 8.65, 0.6)
blk(ax, 0.3, 5.6, 9.4, 3.0, S.MAT["pcb"])
ax.text(2.2, 7.1, "board", ha="center", va="center", fontsize=FS, color="white")
for x in (4.4, 5.0, 5.6, 6.2, 6.8):                                # via field under the cells
    ax.plot([x, x], [5.65, 8.55], color="#c9a46a", lw=0.6)
bumps(ax, 1.7, 8.3, 5.35, 0.25, 14)
cells(ax, 1.7, 8.3, 2.95, 2.4, flip=True)
blk(ax, 1.7, 2.2, 6.6, 0.7, S.MAT["coldplate"])
ax.text(5.0, 2.55, "cold plate", ha="center", va="center", fontsize=FS, color=S.INK)
arrow(ax, [(0.15, 4.1), (2.3, 4.1)], S.V48)
arrow(ax, [(6.4, 5.4), (6.4, 10.2)], S.V1)
ax.text(0.2, 4.55, "48 V", ha="left", va="center", fontsize=FS)
note(ax, "1 V (≈1 kA) crosses\nboard, BGA, substrate")
ring(ax, (9.0, 8.95))
S.panel(ax, "c", "Z3 board backside", x=0.04, y=0.975)
axs[2].text(9.95, 1.95, "ringed:\ncritical joint", ha="right", va="top", fontsize=5.3,
            color=S.INK2, linespacing=1.0)

# ---------------------------------------------------------------- (d) framework
ax = axd
ax.set_xlim(0, 20)
ax.set_ylim(0, 12.4)
BOX = dict(fc="#f3f2ee", ec=S.AXIS, lw=0.6)
COLX = (1.0, 7.85, 14.7)
BW = 5.1


def box(x, y, w, h, title, sub):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.25",
                                **BOX))
    ax.text(x + w / 2, y + h * 0.67, title, ha="center", va="center", fontsize=6.4,
            color=S.INK, fontweight="bold")
    ax.text(x + w / 2, y + h * 0.29, sub, ha="center", va="center", fontsize=5.6,
            color=S.INK2, linespacing=1.0)


def link(p0, p1, lab=None, at=None, ha="center", va="center", ls="-", col=S.INK, rad=0.0):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=7, color=col,
                                 lw=0.8, shrinkA=1, shrinkB=1, linestyle=ls,
                                 connectionstyle=f"arc3,rad={rad}"))
    if lab:
        ax.text(at[0], at[1], lab, ha=ha, va=va, fontsize=5.6, color=S.INK2, linespacing=1.0)


Y1, Y2, H = 8.95, 5.0, 2.25
box(COLX[0], Y1, BW, H, "Converter synthesis", "spec. + 90-device library\n$N$, $K$, $K_A$, parts, $f_\\mathrm{sw}$")
box(COLX[1], Y1, BW, H, "Package stack", "tiers, cells, integration\n(a)–(c), cooling")
box(COLX[2], Y1, BW, H, "Realizability", "conductor planes, via\naspect ratio, provisioning")
box(COLX[0], Y2, BW, H, "Rail-aware ledger", "every conductor, its rail,\nits current, $R(T)$")
box(COLX[1], Y2, BW, H, "Package thermal", "anisotropic layers +\nmicrochannel cold plate")
box(COLX[2], Y2, BW, H, "Thermoelastic", "mounted package,\nall-site joint search")
box(COLX[2], 1.05, BW, H, "Local solder joint", "viscoplastic,\n$\\Delta\\varepsilon_\\mathrm{in}$ per cycle")
# arrows between stages
link((COLX[0] + BW, Y1 + H / 2), (COLX[1], Y1 + H / 2), "cells", (6.97, Y1 + H / 2 + 0.42))
link((COLX[1] + BW, Y1 + H / 2), (COLX[2], Y1 + H / 2))
link((3.55, Y1), (3.55, Y2 + H), "losses", (3.8, (Y1 + Y2 + H) / 2), ha="left")
link((10.4, Y1), (10.4, Y2 + H), "geometry", (10.65, (Y1 + Y2 + H) / 2), ha="left")
link((COLX[0] + BW, Y2 + 1.55), (COLX[1], Y2 + 1.55), "$q'''$", (6.97, Y2 + 1.95))
link((COLX[1], Y2 + 0.7), (COLX[0] + BW, Y2 + 0.7), "$T$", (6.97, Y2 + 0.3))
ax.text(6.97, Y2 - 0.55, "E–T fixed point", ha="center", va="center", fontsize=5.6,
        color=S.INK)
link((COLX[1] + BW, Y2 + H / 2), (COLX[2], Y2 + H / 2), "$T(\\mathbf{x})$",
     (13.82, Y2 + H / 2 + 0.42))
link((17.25, Y2), (17.25, 1.05 + H), "$\\Delta u_\\mathrm{c}$, $T_\\mathrm{j}$", (17.5, 4.15),
     ha="left")
# modes of use
mx0, mx1, my0, my1 = COLX[0], COLX[1] + BW, 1.0, 3.55
ax.add_patch(FancyBboxPatch((mx0, my0), mx1 - mx0, my1 - my0,
                            boxstyle="round,pad=0.02,rounding_size=0.25", fc="white",
                            ec=S.INK2, lw=0.7))
modes = (("Evaluate", "one design vs.\npackage rules"),
         ("Compare", "integrations,\nside by side"),
         ("Explore", "count, topology,\npackage decisions"))
cw = (mx1 - mx0) / 3
for k, (t, sub) in enumerate(modes):
    cx = mx0 + (k + 0.5) * cw
    ax.text(cx, 2.85, t, ha="center", va="center", fontsize=6.4, color=S.INK,
            fontweight="bold")
    ax.text(cx, 1.75, sub, ha="center", va="center", fontsize=5.6, color=S.INK2,
            linespacing=1.0)
    if k:
        ax.plot([mx0 + k * cw] * 2, [my0 + 0.35, my1 - 0.35], color=S.GRID, lw=0.6)
link((COLX[2], 2.2), (mx1, 2.2))
# the exploration loop: from Explore back into synthesis along the bottom and left margin
ex = mx0 + 2.5 * cw
lp = [(ex, my0), (ex, 0.35), (0.35, 0.35), (0.35, Y1 + H / 2), (COLX[0], Y1 + H / 2)]
for (xa, ya), (xb, yb) in zip(lp[:-2], lp[1:-1]):
    ax.plot([xa, xb], [ya, yb], color=S.INK2, lw=0.7, ls=(0, (2.2, 1.6)))
ax.add_patch(FancyArrowPatch(lp[-2], lp[-1], arrowstyle="-|>", mutation_scale=7,
                             color=S.INK2, lw=0.7, shrinkA=0, shrinkB=0))
ax.text(0.12, (0.35 + Y1 + H / 2) / 2, "repeat over design inputs", rotation=90, ha="right",
        va="center", fontsize=5.6, color=S.INK2)
S.panel(ax, "d", "Device-to-joint framework on one geometry", x=0.0, y=0.975)
S.save(fig, "fig1_concept_framework")
