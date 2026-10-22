#!/usr/bin/env python3
"""PHASE 0N SECTION J -- a physically explicit cross-section of Z1 and Z2.

Band thicknesses are taken FROM the measured mesh
(research/phase0n/stack_reconstruction.json). Both panels use one common
micron scale. The 1.6 mm PCB is truncated and marked. Anything the model does
not contain is drawn hatched and labelled NOT MODELLED; unsourced items are TBD.
"""
from __future__ import annotations
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
from pathlib import Path

R = Path(__file__).resolve().parent.parent
OUT = R / "research" / "phase0n"
REC = json.loads((OUT / "stack_reconstruction.json").read_text())

HV, LV, RET, BAD = "#0072B2", "#C1121F", "#5A5A5A", "#C1121F"
C_PCB, C_BGA, C_SUB, C_TSV = "#D8D8D8", "#AAAAAA", "#E4E4E4", "#F0C98A"
C_CONV, C_DIE, C_TIM, C_UF = "#D55E00", "#BFD9EE", "#C9C9C9", "#EFEFEF"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8})

PCB_SHOWN = 300.0
W = 100.0


def t_of(tag, layer):
    return next(L["t_um"] for L in REC[tag]["layers"] if L["layer"] == layer)


def band(ax, y, h, fc, label, dim, *, cells=0, tsv=False, hatch=None, ec="k",
         txt=None, txtc="k", lw=0.9, ls="solid"):
    ax.add_patch(Rectangle((0, y), W, h, fc=fc, ec=ec, lw=lw, ls=ls, hatch=hatch))
    if cells:
        cw = W * 0.305 / cells
        for i in range(cells):
            cx = (i + 0.5) * W / cells - cw / 2
            ax.add_patch(Rectangle((cx, y + h * 0.04), cw, h * 0.92,
                                   fc=C_CONV, ec="k", lw=0.7))
    if tsv:
        for i in range(9):
            ax.add_patch(Rectangle((4 + i * 10.6, y), 3.2, h, fc=C_TSV, ec="k", lw=0.5))
    if label:
        ax.text(-3, y + h / 2, label, ha="right", va="center", fontsize=7.6)
    if dim:
        ax.text(W + 3, y + h / 2, dim, ha="left", va="center", fontsize=7.2,
                color="#333")
    if txt:
        ax.text(W / 2, y + h / 2, txt, ha="center", va="center", fontsize=7.2,
                color=txtc, weight="bold", linespacing=1.3)
    return y + h


def panel(ax, tag, title):
    ax.axis("off")
    ax.set_xlim(-46, 172)
    y = 0.0
    y = band(ax, y, PCB_SHOWN, C_PCB, "PCB (FR-4)", "1600 µm\n(truncated)")
    ax.plot([0, W], [PCB_SHOWN * 0.55] * 2, color="#888", lw=0.8, ls=(0, (6, 3)))

    if tag == "Z1":
        hs = 685.0
        y_bga = y
        y = band(ax, y, t_of("Z1", "bga"), C_BGA, "BGA field", "300 µm")
        # the high-side device the source places below z = 0 and the model omits,
        # drawn BESIDE the stack as required-vs-available so nothing is obscured
        ax.add_patch(Rectangle((W + 34, y_bga), 16, hs, fc="none", ec=HV, lw=1.4,
                               ls=(0, (4, 2)), hatch="///"))
        ax.text(W + 42, y_bga + hs + 70,
                "high-side GaN\nNOT MODELLED\n685 µm needed,\n300 µm available",
                ha="center", va="bottom", fontsize=6.8, color=HV, weight="bold",
                linespacing=1.35)
        y = band(ax, y, t_of("Z1", "sub_lower"), C_SUB, "substrate", "74 µm", tsv=True)
        y = band(ax, y, t_of("Z1", "tile_band"), C_SUB, "embedded cell band",
                 "1226 µm", cells=4)
        ax.text(W / 2, y - 620, "49 cells × 5.61 mm²\n= 30.5 % of 30×30 mm",
                ha="center", va="center", fontsize=6.9, color="#222", linespacing=1.3)
    else:
        y = band(ax, y, t_of("Z2", "bga"), C_BGA, "BGA field", "300 µm")
        y0c = y
        y = band(ax, y, t_of("Z2", "conv"), C_CONV, "backside converter", "1226 µm")
        ax.text(W / 2, y0c + 760, "modelled FULL-AREA\n1103.40 mm³",
                ha="center", va="center", fontsize=7.4, color="w", weight="bold",
                linespacing=1.3)
        ax.text(W / 2, y0c + 470,
                "physically 49 cells\n= 337.02 mm³ (30.5 %);\n"
                "the rest is package fill — TBD",
                ha="center", va="center", fontsize=6.9, color="w", linespacing=1.3)
        y = band(ax, y, 300.0, C_SUB, "substrate", "300 µm", tsv=True)

    y = band(ax, y, 10.0, C_UF, "microbump + underfill", "10 µm")
    y = band(ax, y, 300.0, C_DIE, "compute die", "300 µm")
    y = band(ax, y, 50.0, C_TIM, "TIM / cooler", "50 µm")
    ax.text(W / 2, 2560, title, ha="center", va="bottom", fontsize=11,
            weight="bold")
    return y


def paths(ax, tag):
    """48 V (blue) and 1 V (red), drawn inside the stack where they run."""
    def arr(x, y0, y1, col, lw, lab):
        ax.add_patch(FancyArrowPatch((x, y0), (x, y1), arrowstyle="-|>",
                                     mutation_scale=8, lw=lw, color=col, zorder=6))
        ax.text(x - 2.5 if x > 50 else x + 2.5, (y0 + y1) / 2, lab, fontsize=6.9,
                color=col, rotation=90, va="center",
                ha="right" if x > 50 else "left", weight="bold", zorder=6)
    if tag == "Z1":
        arr(7, 300, 1674, HV, 1.8, "48 V  23.4 A")
        arr(93, 1600, 1910, LV, 3.0, "1 V")
    else:
        arr(7, 300, 600, HV, 1.8, "48 V")
        arr(86, 1826, 2136, LV, 3.0, "1 V  1000 A")


fig, axes = plt.subplots(1, 2, figsize=(12.6, 6.6))
fig.subplots_adjust(left=0.05, right=0.95, top=0.88, bottom=0.19, wspace=0.62)
top1 = panel(axes[0], "Z1", "Z1  EMBEDDED   h_sub = 1.30 mm")
top2 = panel(axes[1], "Z2", "Z2  BACKSIDE   h_sub = 0.30 mm")
paths(axes[0], "Z1"); paths(axes[1], "Z2")
for ax in axes:
    ax.set_ylim(-60, 2820)        # one common micron scale

fig.text(0.28, 0.150,
         "The source flip-chips the high-side device to the RDL of the BOTTOM\n"
         "substrate, below z = 0. No bottom substrate exists in the model, and\n"
         "685 µm would not clear the 300 µm BGA — a 385 µm interference.",
         ha="center", va="top", fontsize=7.6, color=HV, linespacing=1.45,
         bbox=dict(fc="#F2F7FB", ec=HV, lw=1.0, boxstyle="round,pad=0.38"))
fig.text(0.745, 0.150,
         "Read as DISCRETE backside cells with a surrounding BGA field, the balls\n"
         "must span the cell: ≥ 1226 µm required vs 300 µm sourced — a 926 µm\n"
         "shortfall needing a tall standoff or a PCB/substrate cavity. None is in\n"
         "the model and none is sourced.  TBD.",
         ha="center", va="top", fontsize=7.6, color=LV, linespacing=1.45,
         bbox=dict(fc="#FFF4F0", ec=LV, lw=1.0, boxstyle="round,pad=0.38"))
fig.text(0.5, 0.004,
         "Return path is NOT geometry in either architecture: it is accounted as "
         "R_loop = 2 × R_field.",
         ha="center", va="bottom", fontsize=7.6, color=RET)
fig.suptitle("Z1 and Z2 as the code actually builds them — one common vertical scale, "
             "PCB truncated.   Hatched = NOT MODELLED.",
             fontsize=11.5, weight="bold", y=0.975)
for ext in ("png", "pdf"):
    fig.savefig(OUT / f"fig_z1_z2_crosssection.{ext}", dpi=200, bbox_inches="tight")
print(f"wrote {OUT/'fig_z1_z2_crosssection.png'}")
