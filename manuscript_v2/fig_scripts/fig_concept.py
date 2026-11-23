"""Fig. 1: the question and the method.

(a)-(c) Three integrations of the same regulator cells (the design record's count): embedded
        between substrate and die (Z1), on the substrate backside inside a board opening
        (Z2), and on the underside of an uncut board (Z3). The integration decides which rail
        crosses the substrate and the board (48 V at the production Z1 case's input current,
        or 1 V at the load current) and which joints carry the deformation.
(d)     The framework: what each stage hands to the next, the electrothermal fixed point,
        and the three modes of use (evaluate, compare, explore).
Schematic, not to scale (the to-scale sections are Fig. 3); the converter cells show the design
record's tiers (input end at the bottom in every integration). Rail colours only. The bottom
plate of cooling B is drawn faded with a dotted outline (it is absent under cooling A).
"""
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, FancyArrowPatch, Ellipse
import style as S

S.setup()
#: rail currents: the 48-V input of the production Z1 case (cooling A), the 1-V load current
_p48, _c48 = S.load_case(S.PROD, "A", "Z1")
I48_TXT = f" (≈{_c48['i_hv_avg_a']:.0f} A)" if _c48 and _c48.get("i_hv_avg_a") else ""
_i1 = S.DR.P_LOAD_W / S.DR.V_OUT
I1_TXT = f" (≈{_i1 / 1e3:.0f} kA)" if _i1 >= 1e3 else f" (≈{_i1:.0f} A)"
TIERS = S.DR.tiers()                       # input end first: drawn bottom-up
fig = plt.figure(figsize=(S.DBL_W, 3.05))
W_ARCH = 0.158
axs = [fig.add_axes([k * W_ARCH, 0.05, W_ARCH, 0.89]) for k in range(3)]
axd = fig.add_axes([3 * W_ARCH + 0.012, 0.0, 1 - 3 * W_ARCH - 0.012, 0.94])
for ax in axs + [axd]:
    ax.axis("off")
FS = 6.5


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
    """Encapsulated converter: n cells, each the design record's tiers (input end at the
    bottom in every integration: Z1 stacks them up from the substrate, Z2/Z3 hang them down
    with the output end against the attach), heights in proportion, a mixed tier split by part
    footprint (GaN violet, flying capacitors ochre, inductors brown). `flip` is kept for the
    callers; the tier order is the same in all three drawings."""
    w = (x1 - x0) / (1.5 * n + 0.1)
    blk(ax, x0, y, x1 - x0, h, S.MAT["fill"])
    tot = sum(float(t["height_um"]) for t in TIERS)
    gap = 0.04 * h / max(len(TIERS) - 1, 1)
    hh = (h - gap * (len(TIERS) - 1)) / tot
    for k in range(n):
        xc = x0 + 0.3 * w + k * 1.5 * w
        z = y
        for t in TIERS:
            th = float(t["height_um"]) * hh
            xs = xc
            for c, f in S.tier_fill(t["parts"]):
                blk(ax, xs, z, w * f, th, S.CLASS_COLOR[c])
                xs += w * f
            z += th + gap


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


def boundary(ax, x0, y0, x1, y1):
    """The package-internal loss boundary (dashed)."""
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="none", ec=S.INK2, lw=0.8,
                           ls=(0, (3, 2)), zorder=6))


def boundary_poly(ax, pts):
    from matplotlib.patches import Polygon
    ax.add_patch(Polygon(pts, closed=True, fc="none", ec=S.INK2, lw=0.8, ls=(0, (3, 2)),
                         zorder=6))


def plate_b(ax, x0, y0, w, h=0.7, gap=None):
    """The bottom cold plate of cooling B: faded fill, dotted outline, labelled. `gap` = (xa, xb)
    leaves an opening (the direct 48-V feed of Z2 passes through it)."""
    spans = [(x0, x0 + w)] if gap is None else [(x0, gap[0]), (gap[1], x0 + w)]
    for xa, xb in spans:
        ax.add_patch(Rectangle((xa, y0), xb - xa, h, fc=S.MAT["coldplate"], ec=S.INK2, lw=0.6,
                               ls=(0, (1, 1.2)), alpha=0.55, zorder=3))
    xa, xb = max(spans, key=lambda s_: s_[1] - s_[0])
    ax.text((xa + xb) / 2, y0 + h / 2, "plate (B)", ha="center", va="center", fontsize=FS,
            color=S.INK, zorder=4)


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
arrow(ax, [(7.3, 3.75), (7.3, 6.45), (6.2, 6.45), (6.2, 7.9)], S.V48)
arrow(ax, [(3.6, 9.3), (3.6, 10.2)], S.V1)
ax.text(7.5, 4.05, "48 V", ha="left", va="center", fontsize=FS, color="white")
plate_b(ax, 2.0, 2.55, 6.0)
note(ax, f"48 V{I48_TXT} crosses\nboard, BGA, substrate")
ring(ax, (9.0, 6.45))
boundary(ax, 0.35, 6.0, 9.65, 10.8)
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
ax.text(6.35, 4.55, "board\nopening", ha="center", va="center", fontsize=FS, color=S.INK2,
        linespacing=1.0)
plate_b(ax, 1.7, 5.5, 6.6, gap=(3.0, 3.6))
arrow(ax, [(3.3, 2.35), (3.3, 7.4)], S.V48)
arrow(ax, [(6.4, 8.6), (6.4, 10.2)], S.V1)
ax.text(3.5, 2.6, "48 V direct", ha="left", va="center", fontsize=FS)
note(ax, f"1 V{I1_TXT} crosses\nattach, substrate")
ring(ax, (9.15, 8.95))
boundary_poly(ax, [(0.35, 8.5), (1.5, 8.5), (1.5, 6.35), (8.5, 6.35), (8.5, 8.5), (9.65, 8.5),
                   (9.65, 10.8), (0.35, 10.8)])
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
plate_b(ax, 1.7, 2.2, 6.6)
arrow(ax, [(0.05, 4.1), (2.3, 4.1)], S.V48)
arrow(ax, [(6.4, 5.4), (6.4, 10.2)], S.V1)
ax.text(0.05, 4.65, "48 V", ha="left", va="center", fontsize=FS, zorder=7,
        bbox=dict(fc="white", ec="none", pad=0.3))
note(ax, f"1 V{I1_TXT} crosses\nboard, BGA, substrate")
ring(ax, (9.0, 8.95))
boundary(ax, 1.05, 2.85, 9.85, 10.8)
S.panel(ax, "c", "Z3 board backside", x=0.04, y=0.975)
fig.text(1.5 * W_ARCH, 0.008, "ringed: critical joint  ·  dashed box: package-internal "
         "loss boundary  ·  faded plate: cooling B only", ha="center", va="bottom", fontsize=FS,
         color=S.INK2)

# ---------------------------------------------------------------- (d) framework
ax = axd
ax.set_xlim(0, 20.5)
YT = 14.6
ax.set_ylim(0, YT)
BOX = dict(fc="#f3f2ee", ec=S.AXIS, lw=0.6)
COLX = (1.0, 7.85, 14.7)
BW = 5.1
FT, FSUB = 7.0, 6.5


def box(x, y, w, h, title, sub, fc=None):
    kw = dict(BOX)
    if fc:
        kw["fc"] = fc
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.25",
                                **kw))
    ax.text(x + w / 2, y + h * 0.72, title, ha="center", va="center", fontsize=FT,
            color=S.INK, fontweight="bold")
    ax.text(x + w / 2, y + h * 0.33, sub, ha="center", va="center", fontsize=FSUB,
            color=S.INK2, linespacing=1.0)


def link(p0, p1, lab=None, at=None, ha="center", va="center", ls="-", col=S.INK, rad=0.0,
         style="-|>", lw=0.8):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle=style, mutation_scale=7, color=col,
                                 lw=lw, shrinkA=1, shrinkB=1, linestyle=ls,
                                 connectionstyle=f"arc3,rad={rad}"))
    if lab:
        ax.text(at[0], at[1], lab, ha=ha, va=va, fontsize=FSUB, color=S.INK2, linespacing=1.0)


H = 2.35
Y1, Y2, Y3 = 10.9, 7.15, 3.4
box(COLX[0], Y1, BW, H, "Converter synthesis",
    "spec. + part library\n$M$, $N$, $K$, parts, $f_\\mathrm{sw}$, tiers")
box(COLX[1], Y1, BW, H, "Package stack", "tiers, cells, integration\n(a)–(c), cooling")
box(COLX[2], Y1, BW, H, "Realizability", "planes, via aspect\nratio, provisioning")
box(COLX[0], Y2, BW, H, "Rail-aware ledger", "every conductor, its\nrail, current, $R(T)$")
box(COLX[1], Y2, BW, H, "Package thermal", "anisotropic layers,\ncold plates")
box(COLX[2], Y2, BW, H, "Thermoelastic", "mounted package,\nall interconnect sites")
box(COLX[2], Y3, BW, H, "Local solder joint",
    "viscoplastic,\n$\\Delta\\varepsilon_\\mathrm{in}$ per cycle")
box(COLX[0], Y3, COLX[1] + BW - COLX[0], H, "Feasibility filter",
    "part, material and die limits, solder-law range,\nstatic drop, ball current and sites", fc="white")
# one-way transfers (single arrows)
link((COLX[0] + BW, Y1 + H / 2), (COLX[1], Y1 + H / 2), "design\nrecord",
     (6.97, Y1 + H / 2 + 0.75))
link((COLX[1] + BW, Y1 + H / 2), (COLX[2], Y1 + H / 2))
link((3.55, Y1), (3.55, Y2 + H), "losses", (3.8, (Y1 + Y2 + H) / 2), ha="left")
link((10.4, Y1), (10.4, Y2 + H), "geometry", (10.65, (Y1 + Y2 + H) / 2), ha="left")
link((COLX[1] + BW, Y2 + 0.7 * H), (COLX[2], Y2 + 0.7 * H), "$T(\\mathbf{x})$",
     (13.82, Y2 + 0.7 * H + 0.5))
link((17.25, Y2), (17.25, Y3 + H), "$\\Delta u_\\mathrm{c}$, $T_\\mathrm{sj}$",
     (17.5, (Y2 + Y3 + H) / 2), ha="left")
link((COLX[2], Y3 + H / 2), (COLX[1] + BW, Y3 + H / 2))
# realizability -> feasibility (interconnect rules), down the right margin and under the joint
rx, ry = COLX[2] + BW + 0.35, Y3 - 0.42
ax.plot([COLX[2] + BW, rx, rx, 9.4], [Y1 + 0.55, Y1 + 0.55, ry, ry], color=S.INK, lw=0.8)
link((9.4, ry), (9.4, Y3))
# the electrothermal fixed point: ONE double arrow
link((COLX[0] + BW, Y2 + H / 2), (COLX[1], Y2 + H / 2), style="<|-|>", lw=1.1)
ax.text(6.97, Y2 + H / 2 + 0.5, "$q'''$, $T$", ha="center", va="center", fontsize=FSUB,
        color=S.INK2)
ax.text(6.97, Y2 - 0.5, "E–T fixed point", ha="center", va="center", fontsize=FSUB,
        color=S.INK)
# optional mechanical-to-thermal feedback through the top interface (dotted)
link((COLX[2], Y2 + 0.28 * H), (COLX[1] + BW, Y2 + 0.28 * H), ls=(0, (1, 1.2)))
ax.text(13.82, Y2 - 0.55, "interface gap\n(optional)", ha="center", va="center",
        fontsize=FSUB, color=S.INK2, linespacing=1.0)
# modes of use
mx0, mx1, my0, my1 = COLX[0], COLX[2] + BW, 0.55, 2.5
ax.add_patch(FancyBboxPatch((mx0, my0), mx1 - mx0, my1 - my0,
                            boxstyle="round,pad=0.02,rounding_size=0.25", fc="white",
                            ec=S.INK2, lw=0.7))
modes = (("Evaluate", "one design vs. package rules"),
         ("Compare", "integrations side by side"),
         ("Explore", "count, topology, decisions"))
cw = (mx1 - mx0) / 3
for k, (t, sub) in enumerate(modes):
    cx = mx0 + (k + 0.5) * cw
    ax.text(cx, 1.98, t, ha="center", va="center", fontsize=FT, color=S.INK,
            fontweight="bold")
    ax.text(cx, 1.08, sub, ha="center", va="center", fontsize=FSUB, color=S.INK2)
    if k:
        ax.plot([mx0 + k * cw] * 2, [my0 + 0.3, my1 - 0.3], color=S.GRID, lw=0.6)
link((5.0, Y3), (5.0, my1))
# the exploration loop (dashed): from Explore back into synthesis along the bottom and left
ex = mx0 + 2.5 * cw
lp = [(ex, my0), (ex, 0.12), (0.35, 0.12), (0.35, Y1 + H / 2), (COLX[0], Y1 + H / 2)]
for (xa, ya), (xb, yb) in zip(lp[:-2], lp[1:-1]):
    ax.plot([xa, xb], [ya, yb], color=S.INK2, lw=0.7, ls=(0, (3, 2)))
ax.add_patch(FancyArrowPatch(lp[-2], lp[-1], arrowstyle="-|>", mutation_scale=7,
                             color=S.INK2, lw=0.7, shrinkA=0, shrinkB=0))
ax.text(0.12, (Y3 + Y1) / 2 + 0.6, "repeat over design inputs", rotation=90, ha="right",
        va="center", fontsize=FSUB, color=S.INK2)
S.panel(ax, "d", "Device-to-joint framework on one geometry", x=0.0, y=0.975)
S.save(fig, "fig1_concept_framework")
