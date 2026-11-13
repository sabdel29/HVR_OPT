"""Fig. 1 (proposed): the question and the method.

(a,b) The two placements of the same 49-cell regulator: embedded between substrate and
      die (Z1) or on the substrate backside inside a PCB opening (Z2). Moving the regulator
      changes which rail crosses the substrate (48 V at ~24 A vs 1 V at ~1 kA).
(c)   The coupled framework and what each stage hands to the next.
Schematic, not to scale (the to-scale sections are Fig. 3). Rail colours only.
"""
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, FancyArrowPatch, Ellipse
import style as S

S.setup()
fig = plt.figure(figsize=(S.DBL_W, 2.62))
axa = fig.add_axes([0.0, 0.0, 0.205, 0.93])
axb = fig.add_axes([0.205, 0.0, 0.205, 0.93])
axc = fig.add_axes([0.425, 0.0, 0.575, 0.93])
for ax in (axa, axb, axc):
    ax.axis("off")


def blk(ax, x, y, w, h, fc, txt=None, tc="white", fs=6.3):
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec="none"))
    if txt:
        ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center", fontsize=fs, color=tc)


def arrow(ax, pts, col, lw=1.5):
    for (xa, ya), (xb, yb) in zip(pts[:-2], pts[1:-1]):
        ax.plot([xa, xb], [ya, yb], color=col, lw=lw, solid_capstyle="butt")
    ax.add_patch(FancyArrowPatch(pts[-2], pts[-1], arrowstyle="-|>", mutation_scale=8,
                                 color=col, lw=lw, shrinkA=0, shrinkB=0))


def cells(ax, x0, x1, y, h):
    w = (x1 - x0) / 7.6
    blk(ax, x0, y, x1 - x0, h, S.MAT["fill"])
    for k in range(5):
        xc = x0 + 0.35 * w + k * 1.5 * w
        blk(ax, xc, y + 0.62 * h, w, 0.38 * h, S.MAT["inductor"])
        blk(ax, xc, y, w, 0.62 * h, S.MAT["gan"])


def balls(ax, xs, y, h):
    for x in xs:
        ax.add_patch(Ellipse((x, y + h / 2), 0.32, h, fc=S.MAT["solder"], ec="#8d939b", lw=0.3))


for ax, a in ((axa, "Z1"), (axb, "Z2")):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 11)
    blk(ax, 2.0, 9.6, 6.0, 0.7, S.MAT["coldplate"])
    ax.text(5.0, 9.95, "cold plate", ha="center", va="center", fontsize=6, color=S.INK)
    if a == "Z1":
        blk(ax, 2.0, 8.75, 6.0, 0.8, S.MAT["die"], "die")
        cells(ax, 0.6, 9.4, 6.3, 2.35)
        ax.text(9.55, 7.5, "converter", rotation=90, ha="left", va="center", fontsize=6)
        blk(ax, 0.6, 5.65, 8.8, 0.6, S.MAT["silicon"])
        ax.text(5.0, 5.95, "substrate", ha="center", va="center", fontsize=6, color=S.INK)
        balls(ax, [0.95 + 0.62 * k for k in range(14)], 5.0, 0.6)
        blk(ax, 0.3, 2.3, 9.4, 2.65, S.MAT["pcb"], "PCB")
        arrow(ax, [(7.4, 1.2), (7.4, 5.3), (6.2, 5.3), (6.2, 6.7)], S.V48)
        arrow(ax, [(4.2, 8.35), (4.2, 9.0)], S.V1)
        ax.text(7.6, 1.45, "48 V in", ha="left", va="center", fontsize=6.3)
        ax.text(5.0, 0.35, "48 V crosses the substrate\n(≈24 A)", ha="center", va="bottom",
                fontsize=6.4, color=S.INK)
        crit = (9.0, 5.3)
    else:
        blk(ax, 2.0, 7.75, 6.0, 0.8, S.MAT["die"], "die")
        blk(ax, 0.6, 7.15, 8.8, 0.6, S.MAT["silicon"])
        ax.text(5.0, 7.45, "substrate", ha="center", va="center", fontsize=6, color=S.INK)
        cells(ax, 1.7, 8.3, 4.6, 2.5)
        ax.text(5.0, 4.25, "converter in PCB opening", ha="center", va="center", fontsize=6)
        balls(ax, [0.85 + 0.55 * k for k in range(2)] + [8.6 + 0.55 * k for k in range(2)],
              6.5, 0.6)
        blk(ax, 0.3, 3.0, 1.1, 3.45, S.MAT["pcb"])
        blk(ax, 8.6, 3.0, 1.1, 3.45, S.MAT["pcb"])
        ax.text(0.85, 4.7, "PCB", ha="center", va="center", fontsize=6, color="white",
                rotation=90)
        arrow(ax, [(3.2, 1.6), (3.2, 5.2)], S.V48)
        arrow(ax, [(6.2, 6.4), (6.2, 8.0)], S.V1)
        ax.text(3.4, 1.85, "48 V in (direct feed)", ha="left", va="center", fontsize=6.3)
        ax.text(5.0, 0.35, "1 V crosses the substrate\n(≈1 kA)", ha="center", va="bottom",
                fontsize=6.4, color=S.INK)
        crit = (9.15, 6.8)
    ax.add_patch(Ellipse(crit, 0.75, 1.1, fc="none", ec=S.INK, lw=0.8))
    S.panel(ax, "ab"[a == "Z2"], "Z1 embedded" if a == "Z1" else "Z2 backside", x=0.06, y=0.97)
axb.text(9.7, 9.05, "ringed: critical\nsolder joint", ha="right", va="center", fontsize=5.6,
         color=S.INK2)

# ---------------------------------------------------------------- (c) framework
ax = axc
ax.set_xlim(0, 20)
ax.set_ylim(0, 11)
BOX = dict(fc="#f3f2ee", ec=S.AXIS, lw=0.6)


def box(x, y, w, h, title, sub, bold=True):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.25",
                                **BOX))
    ax.text(x + w / 2, y + h * 0.64, title, ha="center", va="center", fontsize=6.8,
            color=S.INK, fontweight="bold" if bold else "normal")
    ax.text(x + w / 2, y + h * 0.27, sub, ha="center", va="center", fontsize=5.9,
            color=S.INK2)


def link(p0, p1, lab=None, off=(0, 0), ha="center", rad=0.0, ls="-"):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=7, color=S.INK,
                                 lw=0.8, connectionstyle=f"arc3,rad={rad}", shrinkA=1,
                                 shrinkB=1, linestyle=ls))
    if lab:
        ax.text((p0[0] + p1[0]) / 2 + off[0], (p0[1] + p1[1]) / 2 + off[1], lab, ha=ha,
                va="center", fontsize=5.8, color=S.INK2)


box(0.3, 8.3, 5.6, 2.0, "Converter synthesis", "90-device library, $N$/$K$/$K_A$, $f_\\mathrm{sw}$")
box(7.2, 8.3, 5.6, 2.0, "Explicit package stack", "tiers, heights, 49 cells")
box(14.1, 8.3, 5.6, 2.0, "Realizability", "conductor planes, via AR")
box(0.3, 4.6, 5.6, 2.3, "Rail-aware ledger", "every conductor, its rail\nand its current")
box(7.2, 4.6, 5.6, 2.3, "Package thermal", "anisotropic layers +\nmicrochannel cold plate")
box(14.1, 4.6, 5.6, 2.3, "Thermoelastic package", "board, BGA, all-site\njoint search")
box(14.1, 0.9, 5.6, 2.3, "Local solder joint", "viscoplastic, per-cycle\n$\\Delta\\varepsilon_\\mathrm{in}$")
box(0.3, 0.9, 12.5, 2.3, "Matched-reference verification", "AEDT, MOOSE, Icepak, closed forms — "
    "error and runtime per stage", bold=True)
link((5.9, 9.3), (7.2, 9.3))
link((12.8, 9.3), (14.1, 9.3))
link((3.1, 8.3), (3.1, 6.9), "devices, losses", off=(0.25, 0), ha="left")
link((10.0, 8.3), (10.0, 6.9), "geometry", off=(0.25, 0), ha="left")
link((5.9, 6.15), (7.2, 6.15), "$q'''$", off=(0, 0.40))
link((7.2, 5.25), (5.9, 5.25), "$R(T)$", off=(0, -0.42))
ax.text(6.55, 7.62, "E–T\nfixed point", ha="center", va="center", fontsize=5.9,
        color=S.INK, linespacing=0.95)
link((12.8, 5.75), (14.1, 5.75), "$T(\\mathbf{x})$", off=(0, 0.45))
link((16.9, 4.6), (16.9, 3.2), "$\\Delta u_\\mathrm{c}$, $T_\\mathrm{joint}$", off=(0.25, 0),
     ha="left")
for x in (3.1, 10.0):
    link((x, 3.2), (x, 4.6), ls=(0, (2, 2)))
link((12.8, 2.05), (14.1, 2.05), ls=(0, (2, 2)))
S.panel(ax, "c", "Coupled framework (one geometry, one converged field)", x=0.0, y=0.97)
S.save(fig, "fig1_concept_framework")
