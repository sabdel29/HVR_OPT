"""Shared visual language for the revised ETM-DVPD manuscript figures.

IEEE T-CPMT print figures: Times New Roman (matches the IEEEtran body), 8 pt labels,
7 pt ticks, vector PDF. Column width 3.5 in, double column 7.16 in.

Colour roles (validated with the dataviz validator, light surface #ffffff, --pairs all):
  architecture identity  Z1 #2a78d6 (blue), Z2 #eb6834 (orange), Z3 #1baf7a (aqua) -> charts only
                         (the first three categorical slots; validated all-pairs: worst CVD
                         dE 9.2, normal-vision 24.0; aqua is 2.7:1 on white, so it is always
                         direct-labelled)
  rail identity          48 V #e34948 (red), 1 V #6250d6 (violet) -> schematics/ledger only
  The two pairs FAIL together (red~orange, violet~blue), so they never share a figure.
Text is always ink (never series colour); identity comes from the mark beside it.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("SOURCE_DATE_EPOCH", "1793000000")   # byte-stable PDFs
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

# ------------------------------------------------------------------ paths
SRC = Path("/home/beams0/SABDELZAHER/ETM_project/HVR_OPT_work")      # revised lineage (working copy)
FC = Path(os.environ.get("TCPMT_RESULTS_DIR", SRC / "research" / "final_closure"))
FIELDS = Path("/home/beams0/SABDELZAHER/ETM_project/scratch/fields")
OUT = SRC / "manuscript_v2" / "figs"
OUT.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------ geometry
COL_W = 3.5      # in, single column
DBL_W = 7.16     # in, double column

# ------------------------------------------------------------------ colours
Z1, Z2, Z3 = "#2a78d6", "#eb6834", "#1baf7a"
ARCH = {"Z1": Z1, "Z2": Z2, "Z3": Z3}
ARCH_NAME = {"Z1": "Z1 embedded", "Z2": "Z2 package backside", "Z3": "Z3 board backside"}
V48, V1 = "#e34948", "#6250d6"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#8a8983"
NEUTRAL = "#c9c8c1"          # converter terms / de-emphasis
LIGHT = "#f0efec"            # diverging midpoint / 'preserved'

# materials for stack diagrams (always paired with a text label)
MAT = {
    "pcb": "#5f8a68", "solder": "#c3c7ce", "silicon": "#a3aec0", "tsv": "#c4783c",
    "rdl": "#d9893f", "gan": "#7a68b3", "caps": "#d9b85a", "inductor": "#9a7a56",
    "fill": "#efe7d6", "die": "#55667a", "tim": "#e9cf7d", "coldplate": "#bcd8ee",
    "attach": "#b98a5a", "air": "#ffffff",
}


def setup():
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Nimbus Roman", "STIX", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
        "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
        "axes.linewidth": 0.6, "axes.edgecolor": AXIS, "axes.labelcolor": INK,
        "xtick.color": INK2, "ytick.color": INK2,
        "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "xtick.major.size": 2.5, "ytick.major.size": 2.5,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID,
        "grid.linewidth": 0.5, "grid.linestyle": "-", "axes.axisbelow": True,
        "legend.frameon": False, "legend.handlelength": 1.2,
        "lines.linewidth": 1.2, "lines.markersize": 4,
        "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.dpi": 600,
        "figure.dpi": 150, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
    })


def panel(ax, letter, title=None, x=0.0, y=1.02):
    """IEEE-style panel label '(a) title' at the top-left, in ink."""
    s = f"({letter})" + (f" {title}" if title else "")
    ax.text(x, y, s, transform=ax.transAxes, ha="left", va="bottom", fontsize=8,
            color=INK)


def _aspect(ax):
    """data-y units per data-x unit that render as equal lengths on the page."""
    fig = ax.figure
    fig.canvas.draw()
    bb = ax.get_window_extent()
    xr = ax.get_xlim()[1] - ax.get_xlim()[0]
    yr = ax.get_ylim()[1] - ax.get_ylim()[0]
    return (yr / bb.height) / (xr / bb.width)


def rbar(ax, x, h, w, color, y0=0.0, r_frac=0.16, zorder=2, horizontal=False):
    """A bar drawn as ONE path: square at the baseline, rounded at the data end.

    Axis limits must be set before calling (the radius is aspect-corrected so the
    corners are circular on the page). horizontal=True draws a horizontal bar of length
    h starting at y0 (x is then the bar centre on the y-axis)."""
    from matplotlib.path import Path
    from matplotlib.patches import PathPatch
    if h == 0:
        return
    k = 0.5523                      # cubic Bezier quarter-circle constant
    a = _aspect(ax)
    if not horizontal:
        rx = w * r_frac
        ry = rx * a
        ry = min(ry, abs(h) / 2)
        x0, x1 = x - w / 2, x + w / 2
        sgn = 1 if h > 0 else -1
        b, t = y0, y0 + h
        tr = t - sgn * ry
        V = [(x0, b), (x0, tr), (x0, tr + sgn * ry * k), (x0 + rx * (1 - k), t), (x0 + rx, t),
             (x1 - rx, t), (x1 - rx * (1 - k), t), (x1, tr + sgn * ry * k), (x1, tr),
             (x1, b), (x0, b)]
    else:
        ry = w * r_frac
        rx = ry / a
        rx = min(rx, abs(h) / 2)
        yb, yt = x - w / 2, x + w / 2
        sgn = 1 if h > 0 else -1
        l, r = y0, y0 + h
        rr = r - sgn * rx
        V = [(l, yb), (rr, yb), (rr + sgn * rx * k, yb), (r, yb + ry * (1 - k)), (r, yb + ry),
             (r, yt - ry), (r, yt - ry * (1 - k)), (rr + sgn * rx * k, yt), (rr, yt),
             (l, yt), (l, yb)]
    C = [Path.MOVETO, Path.LINETO, Path.CURVE4, Path.CURVE4, Path.CURVE4, Path.LINETO,
         Path.CURVE4, Path.CURVE4, Path.CURVE4, Path.LINETO, Path.CLOSEPOLY]
    ax.add_patch(PathPatch(Path(V, C), fc=color, ec="none", lw=0, zorder=zorder))


def J(name):
    return json.loads((FC / name).read_text())


def save(fig, stem):
    pdf = OUT / f"{stem}.pdf"
    png = OUT / f"{stem}.png"
    fig.savefig(pdf)
    fig.savefig(png, dpi=220)
    plt.close(fig)
    print("wrote", pdf)
