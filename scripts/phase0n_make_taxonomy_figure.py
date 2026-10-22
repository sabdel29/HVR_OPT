#!/usr/bin/env python3
"""PHASE 0N SECTION G -- LPD -> lumped VPD -> DVPD.

The discriminating variable is the LOW-VOLTAGE lateral path that survives after
conversion. Source-supported by Krishnakumar 2026 (TCPMT 10.1109/TCPMT.2026.3724907,
held in full) and Sriharini ECTC 2024 (10.1109/ECTC51529.2024.00364, held in full).
"""
from __future__ import annotations
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "research" / "phase0n"
OUT.mkdir(parents=True, exist_ok=True)

HV, LV, DIE, VR, PCB = "#0072B2", "#C1121F", "#BFD9EE", "#D55E00", "#D8D8D8"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})

Y_PCB, Y_PKG, Y_RDL, Y_POL, Y_DIE = 11.0, 24.0, 35.0, 41.0, 43.0
H_PCB, H_PKG_LO, H_RDL, H_DIE = 6.0, 11.0, 6.0, 9.0


def panel(ax, title, vrs, hv_txt, lv_txt, caption, lv_len, board_vrm=False):
    ax.set_xlim(0, 100); ax.set_ylim(0, 72); ax.axis("off")
    ax.text(50, 70, title, ha="center", va="top", fontsize=11.5, weight="bold")

    ax.add_patch(Rectangle((4, Y_PCB), 92, H_PCB, fc=PCB, ec="k", lw=1.0))
    ax.text(50, Y_PCB + H_PCB / 2, "PCB", ha="center", va="center", fontsize=8.5)
    if board_vrm:
        ax.add_patch(Rectangle((6, Y_PCB + H_PCB), 14, 5.0, fc=VR, ec="k", lw=1.0))
        ax.text(13, Y_PCB + H_PCB + 2.5, "VRM", ha="center", va="center",
                fontsize=8, color="w", weight="bold")

    # package: lower band carries the VR cells, upper band is the RDL
    ax.add_patch(Rectangle((8, Y_PKG), 84, H_PKG_LO, fc="#EFEFEF", ec="k", lw=1.0))
    ax.text(10.5, Y_PKG + 1.3, "package / interposer", fontsize=7.4, color="#555")
    ax.add_patch(Rectangle((8, Y_RDL), 84, H_RDL, fc="#F7F7F7", ec="k", lw=1.0))
    ax.text(10.5, Y_RDL + H_RDL / 2, "RDL", fontsize=8, color="#555", va="center")

    for x0, w in vrs:
        ax.add_patch(Rectangle((x0, Y_PKG + 3.8), w, H_PKG_LO - 4.8,
                               fc=VR, ec="k", lw=1.0, alpha=.95))
    if len(vrs) == 1:
        ax.text(vrs[0][0] + vrs[0][1] / 2, Y_PKG + H_PKG_LO / 2 + 1.1, "VR",
                ha="center", va="center", fontsize=8.5, color="w", weight="bold")
    elif vrs:
        ax.text(50, Y_PKG - 3.6, f"{len(vrs)} distributed VR cells", ha="center",
                fontsize=8, color=VR, weight="bold")

    for px in (20, 35, 50, 65, 80):
        ax.add_patch(Rectangle((px - 2.2, Y_POL), 4.4, 2.0, fc="#333", ec="none"))
    ax.text(94.5, Y_POL + 1.0, "POLs", fontsize=7.4, color="#333", va="center")

    ax.add_patch(Rectangle((14, Y_DIE), 72, H_DIE, fc=DIE, ec="k", lw=1.2))
    ax.text(50, Y_DIE + H_DIE / 2, "compute die", ha="center", va="center",
            fontsize=9.5, weight="bold")

    # the LOW-VOLTAGE lateral path, drawn inside the RDL band -- the whole point
    x_lo = max(50 - lv_len / 2, 21.0)
    ax.add_patch(FancyArrowPatch((x_lo, Y_RDL + H_RDL / 2),
                                 (max(x_lo + 6, 50 + lv_len / 2), Y_RDL + H_RDL / 2),
                                 arrowstyle="-|>", mutation_scale=11, lw=3.2,
                                 color=LV, zorder=5))
    # the HIGH-VOLTAGE lateral path, above the package
    ax.add_patch(FancyArrowPatch((6, 59.5), (94, 59.5), arrowstyle="-|>",
                                 mutation_scale=9, lw=1.4, color=HV))
    ax.text(50, 61.3, hv_txt, ha="center", va="bottom", fontsize=8, color=HV)

    ax.text(50, 10.4, lv_txt, ha="center", va="top", fontsize=8.2, color=LV,
            weight="bold", linespacing=1.3)
    ax.text(50, 2.0, caption, ha="center", va="bottom", fontsize=7.8, color="#333")


fig, axes = plt.subplots(1, 3, figsize=(11.0, 3.6))
fig.subplots_adjust(left=0.008, right=0.992, top=0.90, bottom=0.02, wspace=0.05)

panel(axes[0], "(a)  lateral power delivery (LPD)", [],
      "48 V distributed on the board",
      "1 V traverses the full board-to-POL path",
      "conversion on the board; longest low-voltage path", 84, board_vrm=True)
panel(axes[1], "(b)  lumped / integrated VPD", [(44, 12)],
      "48 V reaches the package vertically",
      "1 V still crosses the package RDL to distant POLs\n"
      "(up to a quarter of the system perimeter)",
      "conversion below the die, but a single VR", 56)
panel(axes[2], "(c)  distributed VPD (DVPD)",
      [(15, 10), (30, 10), (45, 10), (60, 10), (75, 10)],
      "48 V distributed laterally at LOW current",
      "1 V path is short, local and vertical",
      "conversion partitioned; per-VR current $I_o/M$", 10)

fig.suptitle("The discriminating variable is the LOW-VOLTAGE lateral path that survives "
             "conversion — not proximity alone", fontsize=10.5, weight="bold",
             y=0.985)
for ext in ("png", "pdf"):
    fig.savefig(OUT / f"fig_vpd_dvpd_taxonomy.{ext}", dpi=220, bbox_inches="tight")
print(f"wrote {OUT/'fig_vpd_dvpd_taxonomy.png'}")
