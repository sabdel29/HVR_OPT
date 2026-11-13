"""Fig. 4 (proposed): tier order is a realizability constraint.

(a) The same four component tiers in the reference order (HS, LS, C_f, L) and the
    repartitioned order (HS, C_f, LS, L), to scale in z with the selected-device heights
    (EPC2014C 685 um, EPC2057 638 um). The three vertical nets inside a cell are drawn
    where they must cross a whole tier (a build-up via of that depth) or only step
    through a 10-um interlayer RDL.
(b) Worst via aspect ratio per net at the assumed 120-um build-up via diameter
    (AR = crossed depth / diameter), against the ~1:1 practice limit for microvias.
Reference vs repartitioned use ink vs open marks (not the architecture colours).
"""
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import style as S

S.setup()
D_VIA = 120.0
T = {"HS": 685, "LS": 638, "Cf": 100, "L": 500}
RDL = 10
FILL = {"HS": S.MAT["gan"], "LS": S.MAT["gan"], "Cf": S.MAT["caps"], "L": S.MAT["inductor"]}
LAB = {"HS": "HS GaN 685 µm", "LS": "LS GaN 638 µm", "Cf": "$C_\\mathrm{f}$ 100 µm",
       "L": "$L$ + $C_\\mathrm{o}$ 500 µm"}
ORD = {"reference": ["HS", "LS", "Cf", "L"], "repartitioned": ["HS", "Cf", "LS", "L"]}
NETS = [("HS", "Cf", "HS → $C_\\mathrm{f}$"), ("HS", "LS", "HS → LS"), ("LS", "L", "SW → $L$")]

fig = plt.figure(figsize=(S.COL_W, 2.55))
ax = fig.add_axes([0.0, 0.03, 0.56, 0.86])
bx = fig.add_axes([0.66, 0.20, 0.33, 0.66])


def stack(x0, order):
    z, ext = 0.0, {}
    for k, t in enumerate(order):
        ax.add_patch(Rectangle((x0, z), 0.8, T[t], fc=FILL[t], ec="none"))
        ax.text(x0 + 0.4, z + T[t] / 2, LAB[t].split(" ")[0] if t != "Cf" else "",
                ha="center", va="center", fontsize=6.2, color="white")
        ext[t] = (z, z + T[t])
        z += T[t]
        if k < 3:
            ax.plot([x0, x0 + 0.8], [z + RDL / 2, z + RDL / 2], color=S.MAT["rdl"], lw=1.1)
            z += RDL
    return ext


res = {}
for i, (name, order) in enumerate(ORD.items()):
    x0 = i * 2.05
    ext = stack(x0, order)
    ax.add_patch(Rectangle((x0 + 0.02, 2035), 0.11, 70, fc=S.INK if i == 0 else "white", ec=S.INK, lw=0.6))
    ax.text(x0 + 0.18, 2070, name, ha="left", va="center", fontsize=7)
    res[name] = {}
    for j, (a, b, nl) in enumerate(NETS):
        za, zb = ext[a], ext[b]
        lo, hi = (za, zb) if za[0] < zb[0] else (zb, za)
        depth = hi[0] - lo[1] - 2 * RDL                   # dielectric between capture planes
        depth = max(depth, 0.0)
        ar = (depth if depth > 0 else RDL) / D_VIA
        res[name][nl] = ar
        if depth > 0:
            xv = x0 + 0.9
            ax.plot([xv, xv], [lo[1], hi[0]], color=S.INK, lw=1.6 if ar > 1 else 0.9,
                    solid_capstyle="butt")
            ax.plot([xv - 0.05, xv + 0.05], [lo[1]] * 2, color=S.INK, lw=0.6)
            ax.plot([xv - 0.05, xv + 0.05], [hi[0]] * 2, color=S.INK, lw=0.6)
            ax.text(xv + 0.07, (lo[1] + hi[0]) / 2, f"{nl}: {depth:.0f} µm",
                    ha="left", va="center", fontsize=5.6, color=S.INK)
    # C_f label beside its thin tier
    zc = ext["Cf"]
    ax.annotate(LAB["Cf"], (x0, (zc[0] + zc[1]) / 2), xytext=(x0 - 0.06, (zc[0] + zc[1]) / 2),
                ha="right", va="center", fontsize=5.8, color=S.INK2)
ax.set_xlim(-0.75, 3.95)
ax.set_ylim(-40, 2180)
ax.axis("off")
ax.plot([-0.62, -0.62], [0, 500], color=S.INK, lw=0.8)
ax.text(-0.57, 250, "500 µm", rotation=90, ha="left", va="center", fontsize=5.8)
S.panel(ax, "a", "Same tiers, two orders", x=0.02, y=1.0)

# (b) worst AR per net
nets = [n for _, _, n in NETS]
xs = range(len(nets))
bx.set_yscale("log")
bx.set_ylim(0.05, 9)
bx.axhline(1.0, color=S.MUTED, lw=0.6, ls=(0, (2, 2)))
bx.text(2.5, 6.0, "dashed: ~1:1 microvia practice", ha="right", va="center", fontsize=5.6,
        color=S.INK2)
w = 0.34
for k, name in enumerate(ORD):
    for i, n in enumerate(nets):
        v = res[name][n]
        x = i + (k - 0.5) * (w + 0.04)
        bx.bar(x, v, w, bottom=0.05 if False else None, color=S.INK if k == 0 else "white",
               edgecolor=S.INK, lw=0.7, zorder=2)
        bx.text(x, v * 1.12, f"{v:.2f}" if v < 1 else f"{v:.1f}", ha="center", va="bottom",
                fontsize=5.6, color=S.INK)
bx.set_xticks(list(xs), nets, fontsize=6.2)
bx.tick_params(axis="x", length=0)
bx.set_ylabel("Worst via aspect ratio", labelpad=1)
S.panel(bx, "b", f"AR at {D_VIA:.0f}-µm vias", x=-0.25, y=1.06)
S.save(fig, "fig4_realizability")
