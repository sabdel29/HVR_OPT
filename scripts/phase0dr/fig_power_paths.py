#!/usr/bin/env python3
"""Figure A - architecture-aware power paths. Which rail traverses which interconnect."""
from __future__ import annotations
import sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0dr"
HV, LV = "#c0392b", "#1f6fb4"          # 48 V, 1 V


def stack_panel(ax, title, layers, vr_z, vr_x, tsv_rail, segs, note):
    for (y0, h, lab, col) in layers:
        ax.add_patch(Rectangle((0, y0), 10, h, fc=col, ec="k", lw=0.8))
        ax.text(10.25, y0 + h / 2, lab, va="center", fontsize=7.4)
    ax.add_patch(Rectangle((vr_x, vr_z[0]), 2.2, vr_z[1] - vr_z[0],
                           fc="#d9534f", ec="k", lw=1.2))
    ax.text(vr_x + 1.1, (vr_z[0] + vr_z[1]) / 2, "HVR", ha="center", va="center",
            fontsize=7, color="w", weight="bold")
    for (x, y0, y1, rail, lab) in segs:
        c = HV if rail == "HV" else LV
        ax.add_patch(FancyArrowPatch((x, y0), (x, y1), arrowstyle="-|>", mutation_scale=11,
                                     lw=2.4, color=c,
                                     linestyle="-" if rail == "HV" else (0, (4, 1.6))))
        ax.text(x + 0.28, (y0 + y1) / 2, lab, fontsize=6.6, color=c, weight="bold")
    ax.set_title(f"{title}\nTSV carries {tsv_rail}", fontsize=9.5,
                 color=HV if tsv_rail.startswith("48") else LV)
    ax.text(5, -1.15, note, ha="center", fontsize=7, style="italic", wrap=True)
    ax.set_xlim(-0.5, 15.5); ax.set_ylim(-1.6, 9.4); ax.axis("off")


def main():
    fig, axes = plt.subplots(1, 3, figsize=(16.5, 6.2), dpi=150)

    # y0, height, label, colour  (bottom -> top)
    base = [(0.0, 0.7, "board / BGA", "#cfd8dc"),
            (0.7, 2.4, "power substrate (h$_{sub}$)", "#b0bec5"),
            (3.1, 0.35, "micro-bump + underfill", "#ffe0b2"),
            (3.45, 1.9, "functional Si die (POLs)", "#90caf9"),
            (5.35, 0.5, "TIM", "#e0e0e0"),
            (5.85, 0.5, "cold plate", "#b3e5fc")]

    stack_panel(axes[0], "ARCH_A  -  HVR at substrate TOP", base, (2.4, 3.1), 3.8, "48 V (HV)",
                [(1.3, 0.0, 0.7, "HV", "BGA"), (1.3, 0.7, 2.4, "HV", "TSV"),
                 (7.0, 3.1, 3.45, "LV", "ubump"), (7.0, 3.45, 4.4, "LV", "RDL")],
                "TSV is UPSTREAM of conversion.\nValidated Phase-0B/0C vehicle; the case Phase 0D analysed.")

    stack_panel(axes[1], "ARCH_B  -  HVR at substrate BOTTOM", base, (0.7, 1.4), 3.8, "1 V (LV)",
                [(1.3, 0.0, 0.7, "HV", "BGA"), (7.6, 1.4, 3.1, "LV", "TSV"),
                 (7.0, 3.1, 3.45, "LV", "ubump"), (7.0, 3.45, 4.4, "LV", "RDL")],
                "TSV is DOWNSTREAM of conversion:\nthe full 1 V output crosses the substrate.")

    c_base = [(0.0, 0.7, "board / BGA", "#cfd8dc"),
              (0.7, 0.4, "package + C4", "#eceff1"),
              (1.1, 2.0, "interposer (h$_{sub}$)", "#b0bec5"),
              (3.1, 0.35, "micro-bump", "#ffe0b2"),
              (3.45, 1.9, "functional Si die (POLs)", "#90caf9"),
              (5.35, 0.5, "TIM", "#e0e0e0"),
              (5.85, 0.5, "cold plate", "#b3e5fc")]
    ax = axes[2]
    stack_panel(ax, "ARCH_C  -  2.5D lateral HVR", c_base, (3.1, 3.9), 0.6, "48 V (HV)",
                [(1.9, 0.0, 0.7, "HV", "BGA"), (1.9, 0.7, 1.1, "HV", "C4"),
                 (1.9, 1.1, 3.1, "HV", "TSV"),
                 (7.0, 3.1, 3.45, "LV", "ubump")],
                "TSV is UPSTREAM, but the 1 V output must\ncross a LONG lateral interposer route.")
    ax.add_patch(FancyArrowPatch((2.9, 3.55), (6.6, 3.55), arrowstyle="-|>", mutation_scale=12,
                                 lw=2.8, color=LV, linestyle=(0, (4, 1.6))))
    ax.text(4.7, 3.85, "RDL lateral (1 V, 240 A)", fontsize=6.8, color=LV,
            weight="bold", ha="center")

    h = [plt.Line2D([], [], color=HV, lw=2.6, label="48 V rail  -  I = 1.354 A/VR  (upstream of conversion)"),
         plt.Line2D([], [], color=LV, lw=2.6, ls=(0, (4, 1.6)),
                    label="1 V rail  -  I = 60 A/VR  (downstream)  -  44.3x the current, ~1960x the $I^2R$")]
    fig.legend(handles=h, loc="lower center", ncol=2, fontsize=9.5, frameon=False,
               bbox_to_anchor=(0.5, -0.015))
    fig.suptitle("Figure A  -  Phase-0D-R architecture-aware power paths.  Which rail traverses "
                 "each interconnect is set by WHERE conversion sits in the stack.\n"
                 "Phase 0D applied a single global rule (TSV = input current); it is correct for "
                 "ARCH_A and wrong for ARCH_B.", fontsize=11.5, y=1.03)
    fig.tight_layout(rect=[0, 0.045, 1, 0.97])
    p = OUT / "FIG_A_power_paths.png"
    fig.savefig(p, bbox_inches="tight"); plt.close(fig)
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
