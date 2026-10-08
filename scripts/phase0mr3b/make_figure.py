#!/usr/bin/env python3
"""Phase-0M-R3B, one figure: the physical cross-section of `ls_to_L`.

What the model measured against what the interconnect actually has to cross.
"""
from __future__ import annotations
import csv, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                          # noqa: E402
from matplotlib.patches import Rectangle, FancyArrowPatch                # noqa: E402

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0mr3b"))
from ls_to_l_topology import tier_extents, layer_stack                   # noqa: E402

OUT = R / "results" / "phase0mr3b"
plt.rcParams.update({"figure.dpi": 150, "savefig.bbox": "tight", "font.size": 8})
C_DIE, C_CAP, C_IND, C_DIE2 = "#34495e", "#8e6aa8", "#c0392b", "#7f8c8d"
C_BU, C_VIA, C_PAD = "#ecf0f1", "#b8860b", "#1b6ca8"


def main() -> int:
    ext = tier_extents()
    segs = layer_stack()
    fig, (ax, az) = plt.subplots(1, 2, figsize=(9.6, 4.6),
                                 gridspec_kw={"width_ratios": [1.45, 1.0]})
    W = 10.0
    names = ["gan_hs (tier 0)", "gan_ls (tier 1)", "cap_fly (tier 2)",
             "inductor / cap_out (tier 3)"]
    cols = [C_DIE2, C_DIE, C_CAP, C_IND]
    # build-up background
    ax.add_patch(Rectangle((0, 0), W, ext[-1][1], fc=C_BU, ec="none", zorder=0))
    for (z0, z1), nm, c in zip(ext, names, cols):
        ax.add_patch(Rectangle((0.8, z0), W - 1.6, z1 - z0, fc=c, ec="k", lw=.6, alpha=.75))
        ax.text(W / 2, (z0 + z1) / 2, f"{nm}   {z1 - z0:.0f} um",
                ha="center", va="center", color="w", fontsize=7.5, weight="bold")
    # the physical via chain, one column, in the free lane beside the components
    xv = 1.55
    for i, s in enumerate(segs):
        ax.add_patch(Rectangle((xv - .28, s["z_bot_um"]), .56,
                               s["thickness_um"], fc=C_VIA, ec="k", lw=.5, zorder=4))
        if i < len(segs) - 1:
            ax.add_patch(Rectangle((xv - .62, s["z_top_um"] - 2), 1.24, 4,
                                   fc=C_PAD, ec="k", lw=.5, zorder=5))
    # the two spans
    ax.add_patch(FancyArrowPatch((W - 0.45, ext[1][1]), (W - 0.45, ext[3][0]),
                                 arrowstyle="<->", color="#1b6ca8", lw=1.6,
                                 mutation_scale=11, zorder=6))
    ax.text(W - 0.30, (ext[1][1] + ext[3][0]) / 2,
            f"PHYSICAL\n{ext[3][0]-ext[1][1]:.0f} um", color="#1b6ca8",
            fontsize=8, va="center", weight="bold")
    mid1 = (ext[1][0] + ext[1][1]) / 2
    mid3 = (ext[3][0] + ext[3][1]) / 2
    ax.add_patch(FancyArrowPatch((0.35, mid1), (0.35, mid3), arrowstyle="<->",
                                 color="#c0392b", lw=1.6, mutation_scale=11, zorder=6))
    ax.text(0.20, (mid1 + mid3) / 2, f"AS MODELLED\n{mid3-mid1:.0f} um", color="#c0392b",
            fontsize=8, va="center", ha="right", weight="bold", rotation=90)
    for y in (mid1, mid3):
        ax.plot([0.25, 1.1], [y, y], color="#c0392b", lw=.8, ls=":")
    ax.set_xlim(-1.5, W + 1.6); ax.set_ylim(-40, ext[-1][1] + 60)
    ax.set_ylabel("z through the converter cell (um)")
    ax.set_xticks([])
    ax.set_title("`ls_to_L`: the modelled span runs mid-plane to mid-plane, through the "
                 "die bodies.\nThe interconnect crosses only the 120 um of build-up "
                 "between them.", fontsize=8.5)
    fig.tight_layout(); fig.text(0.5, -0.02, "one via column shown; the field needs n_required of them side "
             "by side in the free area of the flying-capacitor layer",
             ha="center", fontsize=6.5, color="#555")
    # ---- zoom on the 120 um the chain actually crosses ------------------------------
    z0, z1 = ext[1][1], ext[3][0]
    az.add_patch(Rectangle((0, z0 - 18), W, (z1 - z0) + 36, fc=C_BU, ec="none"))
    az.add_patch(Rectangle((0.8, z0 - 18), W - 1.6, 18, fc=C_DIE, ec="k", lw=.6, alpha=.75))
    az.text(W / 2 + 1.6, z0 - 9, "gan_ls  (terminal face)", ha="center", va="center",
            color="w", fontsize=7.5, weight="bold")
    az.add_patch(Rectangle((0.8, z1), W - 1.6, 18, fc=C_IND, ec="k", lw=.6, alpha=.75))
    az.text(W / 2 + 1.6, z1 + 9, "inductor  (terminal face)", ha="center", va="center",
            color="w", fontsize=7.5, weight="bold")
    xz = 2.2
    for i, s in enumerate(segs):
        az.add_patch(Rectangle((xz - .75, s["z_bot_um"]), 1.5, s["thickness_um"],
                               fc=C_VIA, ec="k", lw=.7, zorder=4))
        az.text(xz + 1.3, (s["z_bot_um"] + s["z_top_um"]) / 2,
                f"microvia {i+1}\n{s['thickness_um']:.0f} um",
                fontsize=7.2, va="center")
        if i < len(segs) - 1:
            az.add_patch(Rectangle((xz - 1.35, s["z_top_um"] - 1.6), 2.7, 3.2,
                                   fc=C_PAD, ec="k", lw=.6, zorder=5))
            az.text(xz - 1.6, s["z_top_um"], "land", fontsize=6.8, color=C_PAD,
                    va="center", ha="right")
    # embedded MLCC blocking the middle layer
    az.add_patch(Rectangle((xz + 5.3, segs[1]["z_bot_um"]), 2.6, segs[1]["thickness_um"],
                           fc=C_CAP, ec="k", lw=.6, alpha=.8, zorder=3))
    az.text(xz + 6.6, (segs[1]["z_bot_um"] + segs[1]["z_top_um"]) / 2,
            "embedded\nMLCC", ha="center", va="center", color="w",
            fontsize=7, weight="bold")
    az.set_xlim(-2.2, W + 1.2); az.set_ylim(z0 - 24, z1 + 24)
    az.set_xticks([]); az.set_ylabel("z (um)")
    az.set_title("the 120 um, resolved: three build-up layers,\n"
                 "so three microvia levels in series", fontsize=8.5)
    # link the two panels
    ax.add_patch(Rectangle((0.6, z0), W - 1.2, z1 - z0, fill=False, ec="#1b6ca8",
                           lw=1.2, ls="--", zorder=8))

    p = OUT / "FIG_0MR3B_ls_to_L_cross_section.png"
    fig.savefig(p); plt.close(fig)
    print(f"wrote {p.relative_to(R)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
