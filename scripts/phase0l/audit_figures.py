#!/usr/bin/env python3
"""AUDIT-FIG-1 .. AUDIT-FIG-13 for results/ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.md.

These are explanatory figures for a reader who understands power delivery and packaging but
not necessarily nonlinear solid mechanics. Each must be readable without prior knowledge of
this project.
"""
from __future__ import annotations
import csv, math, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle, Circle

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0l" / "auditfig"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(R / "scripts" / "phase0i"))

plt.rcParams.update({"font.size": 9, "figure.dpi": 150, "savefig.bbox": "tight",
                     "axes.grid": False})
CLOSED, COND, OPEN = "#2e7d32", "#ef6c00", "#c62828"
INK, GREY, BLUE, PURP = "#263238", "#b0bec5", "#1565c0", "#6a1b9a"


def box(ax, x, y, w, h, text, fc="white", ec=INK, fs=8, lw=1.3, bold=False, tc=None):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02",
                                fc=fc, ec=ec, lw=lw, zorder=3))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, zorder=4,
            color=tc or INK, fontweight="bold" if bold else "normal", linespacing=1.35)


def arrow(ax, p, q, text="", fs=6.6, col=INK, rad=0.0, ls="-", off=(0, 0)):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=11, lw=1.1,
                                 color=col, linestyle=ls, zorder=2,
                                 connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((p[0] + q[0]) / 2 + off[0], (p[1] + q[1]) / 2 + off[1], text, fontsize=fs,
                ha="center", va="center", color=col, zorder=5,
                bbox=dict(fc="white", ec="none", alpha=.88, pad=0.9))


def blank(figsize):
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    return fig, ax


def fig1():
    """The whole ETM dataflow, with each block marked CLOSED / CONDITIONAL / OPEN."""
    fig, ax = blank((10.6, 13.6))
    steps = [
        ("DESIGN VARIABLES\narchitecture, geometry, f$_{sw}$, device, n$_{TSV}$", CLOSED),
        ("CONVERTER SYNTHESIS\n48 V → intermediate → 1 V; device + inductor selection", CLOSED),
        ("RAIL-AWARE CURRENT PATH\nwhich rail crosses which interconnect", CLOSED),
        ("PDN / INTERCONNECT LOSSES\nTSV, BGA, C4, pad, RDL sheet", CLOSED),
        ("ELECTRICAL–THERMAL FIXED POINT\nR(T) ↔ P ↔ T, iterated to convergence", CLOSED),
        ("SPATIALLY MAPPED HEAT SOURCES\nexact cell-overlap weighting onto the mesh", CLOSED),
        ("THERMAL SOLVER  (CalculiX; MOOSE cross-check)\n∇·(K∇T) = −q, Robin surfaces", CLOSED),
        ("T(x, y, z, t)", CLOSED),
        ("GLOBAL THERMOELASTIC PACKAGE\nσ = C : (ε − α ΔT), equilibrium, BC-A", CLOSED),
        ("BOUNDARY DISPLACEMENT HISTORY\nΔu(t) and T(t) at the critical joint", CLOSED),
        ("LOCAL SOLDER SUBMODEL\ngraded joint mesh, 25 µm Syed layers", CLOSED),
        ("CREEP / INELASTIC METRICS\nM1 path, M2 range, M3 energy", COND),
        ("FATIGUE LIFE LAW\nSyed 2004 / Schubert 2003", COND),
        ("MISSION / N$_{required}$", OPEN),
        ("PASS–FAIL  /  G2", OPEN),
    ]
    n = len(steps)
    top, bot = 0.955, 0.075           # leave room for the title and the legend strip
    gap = 0.0145                      # visible gap so the arrows are not hidden by the boxes
    h = (top - bot - (n - 1) * gap) / n
    y = top - h
    ys = []
    for text, col in steps:
        box(ax, 0.085, y, 0.775, h, text, fc="white", ec=col, lw=1.9, fs=7.5)
        ax.add_patch(Rectangle((0.085, y), 0.014, h, fc=col, ec="none", zorder=5))
        ys.append(y)
        y -= h + gap
    for i in range(n - 1):
        arrow(ax, (0.4725, ys[i]), (0.4725, ys[i + 1] + h))
    # the fixed-point feedback: T (step 8) back into the loss models (step 5)
    ax.add_patch(FancyArrowPatch((0.868, ys[7] + h / 2), (0.868, ys[4] + h / 2),
                                 arrowstyle="-|>", mutation_scale=12, lw=1.4, color=BLUE,
                                 connectionstyle="arc3,rad=-0.9", zorder=6))
    ax.text(0.975, (ys[4] + ys[7]) / 2 + h / 2,
            "T feeds back:\nR$_{DS(on)}$(T), DCR(T), ρ$_{Cu}$(T)",
            fontsize=7.0, color=BLUE, rotation=90, ha="center", va="center")
    for lab, col, x in (("CLOSED", CLOSED, 0.085), ("CONDITIONAL", COND, 0.335),
                        ("OPEN", OPEN, 0.64)):
        ax.add_patch(Rectangle((x, 0.022), 0.015, 0.020, fc=col, ec="none"))
        ax.text(x + 0.023, 0.032, lab, fontsize=8, va="center", color=col, fontweight="bold")
    ax.set_title("AUDIT-FIG-1   The ETM dataflow, end to end.\nEvery arrow is a quantity handed "
                 "from one solver to the next.", fontsize=10, pad=8)
    fig.savefig(OUT / "AUDIT_FIG_01_dataflow.png"); plt.close(fig)
    print("  AUDIT-FIG-1")


def fig2():
    """Z1 / Z2 / Z4 cross-sections, to scale in z."""
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 5.6))
    LAY = {"board": ("#795548", "PCB"), "bga": ("#9e9e9e", "BGA"), "sub": ("#26a69a", "substrate"),
           "die": ("#1565c0", "compute die"), "vr": ("#c62828", "HVR / VR"),
           "rdl": ("#fdd835", "RDL"), "pd": ("#6a1b9a", "power die")}
    defs = {
        "Z1  EMBEDDED": [("board", -1900, -300), ("bga", -300, 0), ("sub", 0, 900),
                         ("vr", 130, 630), ("die", 900, 1680)],
        "Z2  BACKSIDE": [("board", -3000, -1400), ("bga", -1400, -1100),
                         ("vr", -1100, 0), ("sub", 0, 300), ("die", 300, 1080)],
        "Z4  POWER DIE": [("board", -2200, -600), ("bga", -600, -300), ("sub", 0, 900),
                          ("pd", 900, 1200), ("die", 1200, 1980)],
    }
    notes = {
        "Z1  EMBEDDED": "converter INSIDE the substrate power layers\nTSV rail: 48 V  (≈ 21 A)\n"
                        "substrate must be ≥ 900 µm to contain the cell\nPROJECT BASELINE",
        "Z2  BACKSIDE": "VR chiplets stacked BELOW the substrate\nTSV rail: 1 V  (1000 A)\n"
                        "substrate free to thin to 300 µm\n≈ 1960× the TSV I²R of Z1",
        "Z4  POWER DIE": "dedicated VR die bonded beneath the compute die\nTSV rail: 48 V\n"
                         "shortest 1 V path, but VR heat sits\ndirectly under the die",
    }
    for ax, (name, layers) in zip(axes, defs.items()):
        for key, z0, z1 in layers:
            col, lab = LAY[key]
            inset = key in ("vr", "pd") and name.startswith(("Z1", "Z4"))
            w = 0.52 if inset else (0.62 if key in ("vr", "pd") else 1.0)
            x = 0.24 if inset else (0.19 if key in ("vr", "pd") else 0.0)
            ax.add_patch(Rectangle((x, z0), w, z1 - z0, fc=col, ec="k", lw=.7,
                                   alpha=.88, zorder=3 if inset else 2))
            if z1 - z0 > 150:
                # an embedded/inset block is labelled inside it; its host layer is labelled
                # off to the left so the two never collide
                tx = x + w / 2 if not inset else x + w / 2
                ax.text(tx, (z0 + z1) / 2, f"{lab}\n{z1-z0:.0f} µm", ha="center",
                        va="center", fontsize=7, color="white", fontweight="bold", zorder=4)
        if name.startswith("Z1"):        # relabel the host substrate clear of the embedded cell
            ax.text(0.11, 760, "substrate\n900 µm", ha="center", va="center", fontsize=7,
                    color="white", fontweight="bold", zorder=4)
        ax.axhline(0, color="k", lw=1.4, ls="--", zorder=5)
        ax.text(0.50, 90, "z = 0  substrate underside", fontsize=6.4, va="bottom",
                ha="center", zorder=6,
                bbox=dict(fc="white", ec="none", alpha=.85, pad=.8))
        ax.set_ylim(-4400, 2300); ax.set_xlim(0, 1.0)
        ax.set_xticks([]); ax.set_ylabel("z (µm)")
        ax.set_yticks([-3000, -2000, -1000, 0, 1000, 2000])
        ax.set_title(name, fontsize=10, fontweight="bold")
        ax.text(0.5, -4300, notes[name], fontsize=7, va="bottom", ha="center",
                bbox=dict(fc="#eceff1", ec=GREY, pad=2.5))
    fig.suptitle("AUDIT-FIG-2   The three live architectures. Dimensions from "
                 "configs/phase0i/z_architectures.yaml.", fontsize=10)
    fig.savefig(OUT / "AUDIT_FIG_02_cross_sections.png"); plt.close(fig)
    print("  AUDIT-FIG-2")


def fig3():
    """Why the rail that crosses the TSV field decides everything."""
    fig, ax = blank((11.6, 5.4))
    ax.text(0.5, 0.955, "The same 1 kW crosses the substrate either as 48 V or as 1 V.",
            ha="center", fontsize=10, fontweight="bold")
    for x0, v, i, col, name in ((0.045, 48, 20.83, BLUE, "Z1 / Z4:  48 V crosses the TSVs"),
                                (0.545, 1, 1000.0, OPEN, "Z2:  1 V crosses the TSVs")):
        box(ax, x0, 0.70, 0.41, 0.12, f"{name}\nP = 1000 W,  V = {v} V  →  I = {i:.2f} A",
            fc="white", ec=col, lw=2, fs=8.4, bold=True, tc=col)
        box(ax, x0 + 0.05, 0.44, 0.31, 0.19,
            f"I = P / V = 1000 / {v}\n= {i:.2f} A\n\n"
            f"P$_{{TSV}}$ = I² R$_{{field}}$\n∝ {i:.2f}² = {i*i:,.0f} A²", fc="#f5f5f5",
            ec=GREY, fs=8)
        for k in range(7):
            ax.add_patch(Rectangle((x0 + 0.075 + k * 0.042, 0.19), 0.018, 0.18,
                                   fc=col, ec="k", lw=.6, alpha=.75))
        ax.text(x0 + 0.205, 0.145, "TSV field", ha="center", fontsize=7.5)
    arrow(ax, (0.47, 0.30), (0.535, 0.30), "", col=INK)
    ax.text(0.5, 0.055,
            "Current ratio 48 : 1  →  I² R ratio  48² = 2304 : 1 for the same field.\n"
            "With Z2's larger allocated via count the realised penalty is ≈ 1960×, and Z2 pays "
            "+1.688 W (≈ +1.3 %) of total system loss.\n"
            "That is the entire electrical price of moving the converter below the substrate — "
            "and it buys a 300 µm substrate instead of 900 µm.",
            ha="center", fontsize=8, va="bottom",
            bbox=dict(fc="#fffde7", ec="#fbc02d", pad=3.5))
    ax.set_title("AUDIT-FIG-3   Rail-aware power path", fontsize=10)
    fig.savefig(OUT / "AUDIT_FIG_03_rail.png"); plt.close(fig)
    print("  AUDIT-FIG-3")


def fig4():
    """The electrical-thermal fixed point."""
    fig, ax = blank((9.6, 6.4))
    nodes = [(0.38, 0.80, 0.24, 0.10, "guess T", "#eceff1"),
             (0.66, 0.60, 0.30, 0.11, "converter loss P$_{conv}$(T)\nR$_{DS(on)}$(T), DCR(T)",
              "#e3f2fd"),
             (0.66, 0.38, 0.30, 0.11, "interconnect loss P$_{PDN}$(T)\nρ$_{Cu}$(T) in TSV, BGA, RDL",
              "#e3f2fd"),
             (0.34, 0.20, 0.32, 0.11, "map heat onto the mesh\n(exact cell overlap)", "#f１f8e9"
              .replace("１", "1")),
             (0.02, 0.38, 0.30, 0.11, "thermal FE solve\n∇·(K∇T) = −q", "#fff3e0"),
             (0.02, 0.60, 0.30, 0.11, "updated T field", "#eceff1")]
    for x, y, w, h, t, c in nodes:
        box(ax, x, y, w, h, t, fc=c, ec=INK, fs=8)
    arrow(ax, (0.50, 0.80), (0.72, 0.71))
    arrow(ax, (0.81, 0.60), (0.81, 0.49))
    arrow(ax, (0.72, 0.38), (0.55, 0.31))
    arrow(ax, (0.34, 0.255), (0.32, 0.38))
    arrow(ax, (0.17, 0.49), (0.17, 0.60))
    ax.add_patch(FancyArrowPatch((0.17, 0.71), (0.42, 0.80), arrowstyle="-|>",
                                 mutation_scale=12, lw=1.3, color=BLUE,
                                 connectionstyle="arc3,rad=0.3", zorder=2))
    ax.text(0.22, 0.79, "iterate", fontsize=8, color=BLUE, fontweight="bold")
    ax.text(0.5, 0.045,
            "Convergence test: max |ΔT| between successive iterates < tolerance, on EVERY\n"
            "monitored component temperature — not on the mean, and not on total power.\n"
            "A candidate that does not converge is REJECTED, never reported at its last iterate.\n"
            "Mechanics sits OUTSIDE this loop: linear thermoelasticity has no back-action on\n"
            "the electrical or thermal problem, so the order is  ET fixed point → structural solve.",
            ha="center", va="bottom", fontsize=7.8,
            bbox=dict(fc="#fffde7", ec="#fbc02d", pad=3.5))
    ax.set_title("AUDIT-FIG-4   The electrical↔thermal fixed point\n"
                 "(scripts/phase0d/coupled.py :: solve_et)", fontsize=10)
    fig.savefig(OUT / "AUDIT_FIG_04_fixed_point.png"); plt.close(fig)
    print("  AUDIT-FIG-4")


def fig5():
    """Spatial heat-source map."""
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.9))
    ax = axes[0]
    d = 22.36
    ax.add_patch(Rectangle((0, 0), d, d, fc="#bbdefb", ec=BLUE, lw=1.6))
    ax.text(d / 2, d * 0.93, "compute die  22.36 mm square, 500 mm²", ha="center", fontsize=8,
            color=BLUE)
    rng = np.random.default_rng(3)
    for i in range(7):
        for j in range(7):
            x, y = 1.4 + i * 2.95, 1.4 + j * 2.95
            ax.add_patch(Rectangle((x, y), 1.9, 1.9, fc="#ef5350", ec="#b71c1c", lw=.6,
                                   alpha=.85))
    ax.text(d / 2, -1.7, "49 HVR tiles beneath the load", ha="center", fontsize=8, color=OPEN)
    ax.set_xlim(-1, d + 1); ax.set_ylim(-3, d + 1); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("where the heat is generated", fontsize=9)

    ax = axes[1]
    nx = 60
    X, Y = np.meshgrid(np.linspace(0, d, nx), np.linspace(0, d, nx))
    Z = np.zeros_like(X) + 3.0
    for i in range(7):
        for j in range(7):
            cx, cy = 2.35 + i * 2.95, 2.35 + j * 2.95
            Z += 9.0 * np.exp(-(((X - cx) ** 2 + (Y - cy) ** 2) / 4.0))
    Z += 12.0 * np.exp(-(((X - d / 2) ** 2 + (Y - d / 2) ** 2) / 120.0))
    im = ax.contourf(X, Y, Z, 22, cmap="inferno")
    ax.set_aspect("equal"); ax.set_xlabel("x (mm)"); ax.set_ylabel("y (mm)")
    ax.set_title("resulting temperature rise above coolant (illustrative)", fontsize=9)
    fig.colorbar(im, ax=ax, label="ΔT (K)")
    fig.suptitle("AUDIT-FIG-5   Heat-source mapping. Tile power is distributed onto mesh cells "
                 "by EXACT area overlap,\nso the integral of the mapped source equals the "
                 "electrical loss to machine precision.", fontsize=9)
    fig.savefig(OUT / "AUDIT_FIG_05_heat_map.png"); plt.close(fig)
    print("  AUDIT-FIG-5")


def fig6():
    """CTE mismatch -> warpage -> joint shear, explained from scratch."""
    fig, axes = plt.subplots(1, 3, figsize=(13.4, 4.4))
    ax = axes[0]
    ax.add_patch(Rectangle((0, 1.0), 6, 0.55, fc="#26a69a", ec="k", alpha=.85))
    ax.add_patch(Rectangle((0, 0.4), 6, 0.55, fc="#795548", ec="k", alpha=.85))
    ax.text(3, 1.28, "substrate   α ≈ 16 ppm/K", ha="center", fontsize=8, color="w")
    ax.text(3, 0.68, "PCB   α ≈ 18 ppm/K", ha="center", fontsize=8, color="w")
    ax.annotate("", (6.9, 1.28), (6.05, 1.28), arrowprops=dict(arrowstyle="-|>", color="#00695c"))
    ax.annotate("", (7.4, 0.68), (6.05, 0.68), arrowprops=dict(arrowstyle="-|>", color="#4e342e"))
    ax.text(7.5, 1.0, "different\nfree expansion\nε$_{th}$ = α ΔT", fontsize=7.5, va="center")
    ax.set_xlim(-.3, 9.6); ax.set_ylim(0, 2.0); ax.axis("off")
    ax.set_title("1. heat the stack: each layer WANTS a different length", fontsize=8.5)

    ax = axes[1]
    x = np.linspace(0, 6, 200)
    w = 0.30 * np.cos(np.pi * (x - 3) / 6) ** 2
    ax.fill_between(x, 1.0 + w, 1.55 + w, color="#26a69a", ec="k", alpha=.85)
    ax.fill_between(x, 0.4 + w * .55, 0.95 + w * .55, color="#795548", ec="k", alpha=.85)
    ax.text(3, 1.95, "they are BONDED, so they cannot each have their own length.\n"
                     "The stack bends instead — this is WARPAGE.", ha="center", fontsize=7.8)
    ax.set_xlim(-.3, 6.3); ax.set_ylim(0, 2.4); ax.axis("off")
    ax.set_title("2. bonded layers must compromise → curvature", fontsize=8.5)

    ax = axes[2]
    ax.add_patch(Rectangle((0, 1.3), 6, 0.5, fc="#26a69a", ec="k", alpha=.85))
    ax.add_patch(Rectangle((0, 0.1), 6, 0.5, fc="#795548", ec="k", alpha=.85))
    for cx in (0.7, 2.2, 3.8, 5.3):
        sh = (cx - 3) * 0.055
        ax.add_patch(plt.Polygon([[cx - .22, 0.6], [cx + .22, 0.6],
                                  [cx + .22 + sh, 1.3], [cx - .22 + sh, 1.3]],
                                 fc="#9e9e9e", ec="k", lw=.8))
    ax.annotate("", (5.55, 1.36), (5.30, 1.36),
                arrowprops=dict(arrowstyle="-|>", color=OPEN, lw=1.6))
    ax.text(5.0, 1.62, "Δu", color=OPEN, fontsize=9, fontweight="bold")
    ax.text(3, -0.32, "The solder joints span the gap, so the mismatch appears across them\n"
                      "as a SHEAR displacement Δu. That Δu, cycled, is what fatigues the joint.",
            ha="center", fontsize=7.8, va="top")
    ax.set_xlim(-.3, 6.3); ax.set_ylim(-1.15, 2.0); ax.axis("off")
    ax.set_title("3. the joints carry the difference", fontsize=8.5)
    fig.suptitle("AUDIT-FIG-6   Why a temperature change loads a solder joint at all", fontsize=10)
    fig.savefig(OUT / "AUDIT_FIG_06_cte.png"); plt.close(fig)
    print("  AUDIT-FIG-6")


def fig7():
    """Global -> local submodelling."""
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.8),
                             gridspec_kw={"width_ratios": [1.45, 1]})
    ax = axes[0]
    ax.add_patch(Rectangle((0, 1.0), 10, 0.9, fc="#26a69a", ec="k", alpha=.8))
    ax.add_patch(Rectangle((2.6, 1.9), 4.8, 0.8, fc="#1565c0", ec="k", alpha=.8))
    ax.add_patch(Rectangle((0, -0.9), 10, 0.9, fc="#795548", ec="k", alpha=.8))
    for cx in np.arange(0.45, 10, 0.62):
        ax.add_patch(Circle((cx, 0.5), 0.23, fc="#9e9e9e", ec="k", lw=.5))
    ax.add_patch(Circle((0.45, 0.5), 0.33, fc="none", ec=OPEN, lw=2.2))
    ax.annotate("critical joint\n(outermost corner —\nlargest distance from\nthe neutral point)",
                (0.45, 0.5), (1.6, -1.75), fontsize=7.5, color=OPEN,
                arrowprops=dict(arrowstyle="-|>", color=OPEN))
    ax.text(5, 2.95, "GLOBAL PACKAGE MODEL — every layer, no joint resolved individually",
            ha="center", fontsize=8.5, fontweight="bold")
    ax.set_xlim(-.4, 10.4); ax.set_ylim(-2.6, 3.3); ax.axis("off")

    ax = axes[1]
    ax.add_patch(Rectangle((0, 2.35), 4, 0.5, fc="#26a69a", ec="k", alpha=.8))
    ax.add_patch(Rectangle((0, -0.35), 4, 0.5, fc="#795548", ec="k", alpha=.8))
    ax.add_patch(Rectangle((0.6, 0.15), 2.8, 2.2, fc="#bdbdbd", ec="k", lw=1))
    for y0, lab in ((2.05, "package-side 25 µm layer"), (0.15, "board-side 25 µm layer")):
        ax.add_patch(Rectangle((0.6, y0), 2.8, 0.30, fc="#ffab91", ec="#bf360c", lw=1.2))
        ax.text(3.55, y0 + 0.15, lab, fontsize=7, va="center", color="#bf360c")
        for k in range(1, 2):
            ax.plot([0.6, 3.4], [y0 + 0.15, y0 + 0.15], color="#bf360c", lw=.5, ls=":")
    ax.text(2.0, 1.3, "solder\nbulk", ha="center", fontsize=8)
    ax.annotate("", (3.9, 2.6), (3.4, 2.6), arrowprops=dict(arrowstyle="-|>", color=OPEN, lw=1.8))
    ax.text(3.95, 2.6, "Δu(t)", color=OPEN, fontsize=9, va="center", fontweight="bold")
    ax.text(2.0, 3.35, "LOCAL SUBMODEL — driven by Δu(t) and T(t)", ha="center", fontsize=8.5,
            fontweight="bold")
    ax.text(2.0, -1.5, "Each 25 µm layer is TWO elements thick (12.5 µm each),\n"
                       "because Syed's fatigue constants are calibrated on exactly\n"
                       "that averaging volume and are not valid on any other.",
            ha="center", fontsize=7.4, va="center",
            bbox=dict(fc="#fffde7", ec="#fbc02d", pad=2.6))
    ax.set_xlim(-.3, 6.4); ax.set_ylim(-2.3, 3.8); ax.axis("off")
    fig.suptitle("AUDIT-FIG-7   Global→local submodelling. The global model cannot afford to "
                 "resolve every joint,\nso it hands the critical joint's displacement and "
                 "temperature history to a refined local model.", fontsize=9.5)
    fig.savefig(OUT / "AUDIT_FIG_07_submodel.png"); plt.close(fig)
    print("  AUDIT-FIG-7")


def fig8():
    """Elastic vs plastic vs creep, and what THIS model actually contains."""
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.3))
    ax = axes[0]
    e = np.linspace(0, 0.01, 100)
    ax.plot(e, 45000 * e, color=BLUE, lw=2)
    ax.annotate("", (0.006, 270), (0.006, 0), arrowprops=dict(arrowstyle="<->", color=GREY))
    ax.text(0.0063, 140, "remove the load\nand this strain\ngoes away", fontsize=7.5)
    ax.set_xlabel("strain"); ax.set_ylabel("stress (MPa)")
    ax.set_title("ELASTIC — reversible, instantaneous", fontsize=9)
    ax.grid(alpha=.3)

    ax = axes[1]
    e1 = np.linspace(0, 0.0005, 40); e2 = np.linspace(0.0005, 0.004, 60)
    ax.plot(e1, 45000 * e1, color=BLUE, lw=2)
    ax.plot(e2, 22.5 + (e2 - 0.0005) * 1500, color=OPEN, lw=2)
    ax.plot([0.004, 0.0035], [27.8, 5.3], color=BLUE, lw=2, ls="--")
    ax.annotate("", (0.0035, -2.5), (0.0, -2.5), arrowprops=dict(arrowstyle="<->", color=OPEN))
    ax.text(0.0017, -7.5, "permanent", fontsize=7.5, color=OPEN, ha="center")
    ax.set_xlabel("strain"); ax.set_ylim(-11, 40)
    ax.set_title("RATE-INDEPENDENT PLASTIC — permanent,\nhappens only above a yield stress",
                 fontsize=9)
    ax.grid(alpha=.3)

    ax = axes[2]
    t = np.linspace(0, 100, 200)
    ax.plot(t, 0.0012 * (1 - np.exp(-t / 12)) + 2.2e-5 * t, color="#6a1b9a", lw=2)
    ax.set_xlabel("time at CONSTANT stress (s)"); ax.set_ylabel("strain")
    ax.set_title("CREEP — permanent, and it keeps going\nwhile the load is simply HELD",
                 fontsize=9)
    ax.grid(alpha=.3)
    fig.text(0.5, -0.09,
             "WHAT THIS FRAMEWORK ACTUALLY CONTAINS (proved by solver probe, Phase 0L Part IV):\n"
             "in a *VISCO step CalculiX integrates ONE inelastic strain, ε̇ = A (σ − σ_y)$^n$. "
             "There is NO rate-independent plastic strain — the middle panel does not occur.\n"
             "The yield stress σ_y appears only as a THRESHOLD in the creep law: below it the "
             "computed creep rate is exactly zero.",
             ha="center", fontsize=8, bbox=dict(fc="#ffebee", ec=OPEN, pad=4))
    fig.suptitle("AUDIT-FIG-8   Three ways a metal deforms", fontsize=10)
    fig.savefig(OUT / "AUDIT_FIG_08_deformation.png"); plt.close(fig)
    print("  AUDIT-FIG-8")


def fig9():
    """PEEQ = odometer, not displacement."""
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.4))
    t = np.linspace(0, 4, 800)
    shear = 0.004 * np.sin(2 * np.pi * t)
    ax = axes[0]
    ax.plot(t, shear * 1e3, color=BLUE, lw=1.8)
    ax.axhline(0, color=GREY, lw=.8)
    ax.annotate("", (3.25, 4.0), (3.25, -4.0), arrowprops=dict(arrowstyle="<->", color=OPEN,
                                                               lw=1.6))
    ax.text(3.33, 0, "M2:\nthe RANGE\nwithin one cycle", fontsize=8, color=OPEN, va="center")
    ax.set_xlabel("cycles"); ax.set_ylabel("joint shear strain (×10⁻³)")
    ax.set_title("the joint returns to where it started every cycle", fontsize=9)
    ax.grid(alpha=.3)

    ax = axes[1]
    peeq = np.cumsum(np.abs(np.gradient(shear))) * 0.85
    ax.plot(t, peeq * 1e3, color="#6a1b9a", lw=2)
    for k in range(1, 5):
        ax.axvline(k, color=GREY, lw=.6, ls=":")
    ax.annotate("", (4.05, peeq[-1] * 1e3), (4.05, peeq[int(len(t) * .75)] * 1e3),
                arrowprops=dict(arrowstyle="<->", color="#6a1b9a", lw=1.6))
    ax.text(3.0, peeq[-1] * 1e3 * .86, "M1: the increment\nadded per cycle", fontsize=8,
            color="#6a1b9a")
    ax.set_xlabel("cycles"); ax.set_ylabel("PEEQ  (×10⁻³)")
    ax.set_title("PEEQ only ever goes UP", fontsize=9)
    ax.grid(alpha=.3)
    fig.text(0.5, -0.10,
             "PEEQ behaves like an ODOMETER, not like a displacement. Irreversible deformation "
             "accumulated while the solder moves through a cycle is\nadded to it even when the "
             "joint later returns to its starting position — just as a car's odometer advances "
             "on a round trip that ends at home.\n"
             "M1 (the odometer increment per cycle) and M2 (the within-cycle range) are "
             "therefore different physical quantities, and a fatigue law\ncalibrated on one may "
             "not be used with the other.",
             ha="center", fontsize=8, bbox=dict(fc="#f3e5f5", ec="#6a1b9a", pad=4))
    fig.suptitle("AUDIT-FIG-9   Accumulated path (M1) versus within-cycle range (M2)",
                 fontsize=10)
    fig.savefig(OUT / "AUDIT_FIG_09_peeq.png"); plt.close(fig)
    print("  AUDIT-FIG-9")


def fig10():
    """Response metric -> life law -> N_f -> N_required -> pass/fail."""
    fig, ax = blank((12.6, 4.6))
    items = [("RESPONSE METRIC\nΔε$_{acc}$ or Δw$_{acc}$\nper stabilised cycle\n\n"
              "what the FE model\ncomputes", CLOSED, "CLOSED"),
             ("FATIGUE LIFE LAW\nN$_f$ = (0.0468 ε$_{acc}$)$^{-1}$\nor (0.0015 w$_{acc}$)$^{-1}$\n\n"
              "Syed 2004 / Schubert 2003", COND, "CONDITIONAL"),
             ("N$_f$\ncycles the package\ncan survive\n\n2499 or 610 (Z1)\ndepending on the law",
              COND, "CONDITIONAL"),
             ("N$_{required}$\ncycles the product\nMUST survive\n\nnot defined anywhere\n"
              "in this project", OPEN, "OPEN"),
             ("G2:  N$_f$ ≥ N$_{required}$ ?\n\ncannot be evaluated\nwhile either side\n"
              "is unknown", OPEN, "OPEN")]
    w, gap = 0.172, 0.035
    for i, (t, col, tag) in enumerate(items):
        x = 0.012 + i * (w + gap)
        box(ax, x, 0.30, w, 0.44, t, fc="white", ec=col, lw=2.1, fs=7.6)
        ax.add_patch(Rectangle((x, 0.755), w, 0.052, fc=col, ec="none"))
        ax.text(x + w / 2, 0.781, tag, ha="center", va="center", color="white", fontsize=7.6,
                fontweight="bold")
        if i < len(items) - 1:
            arrow(ax, (x + w, 0.52), (x + w + gap, 0.52))
    ax.text(0.5, 0.14,
            "The three quantities are independent. A RATIO of response metrics between two "
            "architectures is defensible even when the\nabsolute life is not, because the life "
            "law's constant cancels: N$_{f,Z2}$/N$_{f,Z1}$ = (ε$_{Z1}$/ε$_{Z2}$)$^{k}$ does not "
            "contain the prefactor.\nWhat does NOT cancel is the EXPONENT k and the choice of "
            "metric family — and those differ between the admitted laws.",
            ha="center", fontsize=8, va="center",
            bbox=dict(fc="#e8f5e9", ec=CLOSED, pad=4))
    ax.set_title("AUDIT-FIG-10   The fatigue-life bridge, and where it is broken today",
                 fontsize=10)
    fig.savefig(OUT / "AUDIT_FIG_10_life_bridge.png"); plt.close(fig)
    print("  AUDIT-FIG-10")


def fig11():
    """Toolchain responsibility."""
    fig, ax = blank((12.4, 6.2))
    tools = [
        (0.02, 0.62, "Python 3.12", "orchestration, converter synthesis,\nPDN networks, all "
         "post-processing", CLOSED),
        (0.27, 0.62, "Gmsh 4.15.2", "geometry and meshing support", CLOSED),
        (0.52, 0.62, "CalculiX 2.23", "thermal FE, global thermoelastic FE,\nlocal solder "
         "nonlinear FE", CLOSED),
        (0.77, 0.62, "MOOSE", "independent conduction / RDL\ncross-checks  (heat_transfer only)",
         COND),
        (0.02, 0.24, "HFSS / AEDT 2026 R1", "frequency-domain loop impedance,\nAC current "
         "crowding factor", CLOSED),
        (0.27, 0.24, "Icepak", "attempted package thermal cross-check\nRESULT DISCARDED", OPEN),
        (0.52, 0.24, "PALACE", "installed and functional;\nNO validation result claimed", OPEN),
        (0.77, 0.24, "pandoc + xelatex", "report build (Markdown → PDF)", CLOSED),
    ]
    for x, y, name, role, col in tools:
        box(ax, x, y, 0.21, 0.30, f"{name}\n\n{role}", fc="white", ec=col, lw=2, fs=7.4)
        ax.add_patch(Rectangle((x, y + 0.245), 0.21, 0.055, fc=col, ec="none"))
        ax.text(x + 0.105, y + 0.272, name, ha="center", va="center", color="white",
                fontsize=8.2, fontweight="bold")
    ax.text(0.5, 0.115,
            "Q3D is NOT licensed on this system and no Q3D result exists anywhere in the "
            "project.\nIcepak produced a package thermal result that failed cross-validation "
            "and was discarded; it is not used for any current claim.\n"
            "PALACE is installed and runs, but has not produced a validation result, so none is "
            "claimed.",
            ha="center", fontsize=8, va="center",
            bbox=dict(fc="#ffebee", ec=OPEN, pad=4))
    ax.set_title("AUDIT-FIG-11   Which tool is responsible for what", fontsize=10)
    fig.savefig(OUT / "AUDIT_FIG_11_toolchain.png"); plt.close(fig)
    print("  AUDIT-FIG-11")


def fig12():
    """The validation ladder: how far up each block has climbed."""
    fig, ax = plt.subplots(figsize=(11.8, 6.2))
    rungs = ["asserted", "internally\nconsistent", "cross-checked\nvs 2nd tool",
             "reproduces\nSOURCE data", "validated vs\nindependent\nEXPERIMENT"]
    blocks = [("converter loss model", 2), ("vertical interconnect  R = ρL/A", 3),
              ("RDL multilayer sheet PDE", 3), ("HFSS AC / crowding factor", 3),
              ("thermal conduction FE", 3), ("global thermoelastic FE", 2),
              ("local solder submodel (mesh)", 3),
              ("SAC305 creep implementation", 4), ("SAC305 creep CARD", 1),
              ("fatigue life law (relative)", 3), ("fatigue life law (absolute)", 1),
              ("mission requirement", 0)]
    cols = [OPEN, "#ef6c00", "#f9a825", "#7cb342", CLOSED]
    y = np.arange(len(blocks))
    for i, (name, lvl) in enumerate(blocks):
        for k in range(5):
            ax.add_patch(Rectangle((k, i - .34), .94, .68,
                                   fc=cols[k] if k <= lvl else "#eceff1",
                                   ec="white", lw=1.4, alpha=.92 if k <= lvl else 1))
        ax.text(-0.18, i, name, ha="right", va="center", fontsize=8.2)
    ax.set_xticks(np.arange(5) + .47); ax.set_xticklabels(rungs, fontsize=8)
    ax.set_yticks([]); ax.set_xlim(-4.6, 5.05); ax.set_ylim(-.7, len(blocks) - .3)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("AUDIT-FIG-12   Validation ladder. A block is coloured only as far as the "
                 "evidence actually reaches.\n'SAC305 creep CARD' stops at rung 1 because "
                 "Phase 0L showed it does not reproduce its own source data.", fontsize=9.5)
    fig.savefig(OUT / "AUDIT_FIG_12_validation_ladder.png"); plt.close(fig)
    print("  AUDIT-FIG-12")


def fig13():
    """Source-data domain vs package operating trajectory, updated with Phase 0L."""
    import solder_model as sm
    fig, ax = plt.subplots(figsize=(11.0, 6.2))
    ax.add_patch(Rectangle((45, 7.51), 105, 15.92 - 7.51, fc=CLOSED, alpha=.35, ec=CLOSED,
                           lw=2.2, zorder=4))
    for (T, s, _e) in sm.CREEP_DATA:
        ax.plot(T, s, "o", ms=5, color="#1b5e20", zorder=6)
    ax.annotate("THE ONLY CREEP DATA\n45–150 °C,  7.51–15.92 MPa\n19 points\n"
                "alloy Sn3.9Ag0.6Cu — NOT SAC305", (97, 10.6), ha="center", fontsize=8,
                zorder=7, bbox=dict(fc="white", ec=CLOSED, lw=1, alpha=.94, pad=3))
    ax.add_patch(Rectangle((-40, 0.5), 162, 60, fc=BLUE, alpha=.09, ec=BLUE, lw=1.2, ls="--",
                           zorder=1))
    ax.annotate("SAC305 Anand set (Motalab, via Yuan Tables 7/9): right alloy, right stresses,\n"
                "but calibrated at strain rates 1e−3…1e−5 /s — it overlaps the creep data in\n"
                "NO regime, and misses it by ×1240 where they are compared.",
                (-37, 2.1), fontsize=7.6, color=BLUE, zorder=7, va="bottom")
    prof = [("operating baseline  25→83 °C", 25, 82.9, 20.5, 216.9, OPEN, 1.85),
            ("experiment  45→125 °C", 45, 125, 20.7, 178.8, "#ef6c00", 1.33),
            ("experiment  110→150 °C", 110, 150, 19.9, 147.1, PURP, 1.05)]
    for lab, t0, t1, s0, s1, col, yf in prof:
        ax.add_patch(Rectangle((t0, s0), t1 - t0, s1 - s0, fc="none", ec=col, lw=2.2, zorder=5))
        ax.annotate(lab, (t0 + 1.5, s1 * yf), fontsize=8, color=col, zorder=8, va="center",
                    bbox=dict(fc="white", ec=col, lw=.8, alpha=.94, pad=1.8))
    ax.axhspan(54, 91, color=OPEN, alpha=.13, zorder=0)
    ax.text(163, 70, "damage-weighted\nstresses\n54–91 MPa", fontsize=7.6, color=OPEN,
            va="center", ha="left")
    ax.set_yscale("log"); ax.set_ylim(1.5, 900); ax.set_xlim(-45, 162)
    ax.set_xlabel("temperature (°C)"); ax.set_ylabel("von Mises stress (MPa)")
    ax.grid(alpha=.3, which="both")
    ax.set_title("AUDIT-FIG-13   Where the material data is, and where the package actually "
                 "operates.\nThe green patch is the whole of the evidence. Everything outside "
                 "it is extrapolation.", fontsize=9.5)
    fig.savefig(OUT / "AUDIT_FIG_13_domain.png"); plt.close(fig)
    print("  AUDIT-FIG-13")


if __name__ == "__main__":
    which = sys.argv[1:] or [str(i) for i in range(1, 14)]
    for w in which:
        globals()[f"fig{w}"]()
