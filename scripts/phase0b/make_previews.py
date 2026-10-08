#!/usr/bin/env python3
"""Generate a placement preview image for every C01..C20 case.

Produced for all 20 cases even though only three are solved at this gate: it is an
immediate visual audit of the frozen DOE.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etm.config import load_stack, load_doe          # noqa: E402
from etm.placement import case_tiles                 # noqa: E402

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0b" / "placement_previews"


def draw(ax, case_id, case, tiles, stack, doe):
    g = stack["geometry"]
    Lx, Ly = g["power_substrate"]["size_x"]["value"], g["power_substrate"]["size_y"]["value"]
    Dx, Dy = g["functional_die"]["size_x"]["value"], g["functional_die"]["size_y"]["value"]
    ko = doe["placement_rules"]["edge_keepout_mm"]["value"]

    ax.add_patch(Rectangle((-Lx/2, -Ly/2), Lx, Ly, fc="#eef1f5", ec="#8a94a6", lw=1.2))
    ax.add_patch(Rectangle((-Dx/2, -Dy/2), Dx, Dy, fc="#dbe4ef", ec="#4a6fa5",
                           lw=1.4, ls="--"))
    ax.add_patch(Rectangle((-Dx/2+ko, -Dy/2+ko), Dx-2*ko, Dy-2*ko, fc="none",
                           ec="#b0b8c4", lw=0.7, ls=":"))
    for i, t in enumerate(tiles):
        ax.add_patch(Rectangle((t.x0, t.y0), t.ax, t.ay, fc="#d9534f", ec="#7d2b28",
                               lw=1.0, alpha=0.85))
        ax.text(t.cx, t.cy, f"{t.power_w:.1f}W", ha="center", va="center",
                fontsize=5.6, color="white", weight="bold")

    A = sum(t.area for t in tiles)
    P = sum(t.power_w for t in tiles)
    ax.set_title(f"{case_id}  N={case['n_vr']}  {case['placement']}\n"
                 f"tile {case['tile_ax']:.2f}x{case['tile_ay']:.2f} mm  "
                 f"h_sub={case['h_sub']*1000:.0f} um  A={A:.0f} mm$^2$  P={P:.1f} W",
                 fontsize=6.4)
    ax.set_xlim(-Lx/2-1, Lx/2+1); ax.set_ylim(-Ly/2-1, Ly/2+1)
    ax.set_aspect("equal"); ax.tick_params(labelsize=5)
    ax.set_xlabel("x (mm)", fontsize=5.5); ax.set_ylabel("y (mm)", fontsize=5.5)


def main():
    stack, doe = load_stack(), load_doe()
    OUT.mkdir(parents=True, exist_ok=True)
    ids = sorted(doe["cases"])

    for cid in ids:
        c = doe["cases"][cid]
        t = case_tiles(c, stack, doe)
        fig, ax = plt.subplots(figsize=(3.0, 3.2), dpi=170)
        draw(ax, cid, c, t, stack, doe)
        fig.tight_layout()
        fig.savefig(OUT / f"{cid}.png"); plt.close(fig)

    fig, axes = plt.subplots(4, 5, figsize=(15, 13), dpi=140)
    for ax, cid in zip(axes.ravel(), ids):
        draw(ax, cid, doe["cases"][cid], case_tiles(doe["cases"][cid], stack, doe), stack, doe)
    fig.suptitle("Phase-0B controlled DOE - frozen placement matrix C01-C20\n"
                 "red = HVR tile (label = per-tile heat), dashed blue = 22.36 mm functional die, "
                 "grey = 30 mm power substrate, dotted = legal region",
                 fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.955])
    fig.savefig(OUT / "ALL_CASES.png"); plt.close(fig)
    print(f"wrote {len(ids)} previews + ALL_CASES.png -> {OUT}")


if __name__ == "__main__":
    main()
