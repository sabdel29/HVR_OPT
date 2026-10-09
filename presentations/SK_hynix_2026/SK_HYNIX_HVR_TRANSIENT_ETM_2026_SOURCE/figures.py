#!/usr/bin/env python3
"""Presentation-scale figures for the SK hynix deck.

Figures are sized so that one matplotlib point equals one point on the slide:
each figure is inserted at its own figsize width, so fontsize=22 really is 22 pt
to the audience. Journal figures from the manuscript are NOT reused -- they are
6-7 pt and unreadable from the back of a room.

All numbers come from sources.py, which loads them from the frozen artifacts.
"""
from __future__ import annotations
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle, FancyArrowPatch
from pathlib import Path
import sources as S

import os
# In DECK mode the slide supplies the title, so in-figure titles are suppressed
# and the reserved space is reclaimed. Standalone mode keeps them.
DECK = os.environ.get("FIG_DECK_MODE") == "1"
OUT = Path(__file__).resolve().parent / ("figs/deck" if DECK else "figs")


def _sup(fig, *a, **k):
    if not DECK:
        fig.suptitle(*a, **k)


def _tit(ax, *a, **k):
    if not DECK:
        ax.set_title(*a, **k)

OUT.mkdir(parents=True, exist_ok=True)

BLU, ORA, GRN, RED, PUR, GRY = "#0072B2", "#D55E00", "#009E73", "#C1121F", "#7B5EA7", "#5A5A5A"
LIGHT = "#E8E8E8"

plt.rcParams.update({
    "figure.dpi": 200, "savefig.dpi": 200, "savefig.bbox": "tight",
    "savefig.pad_inches": 0.08, "font.family": "DejaVu Sans",
    "axes.linewidth": 1.6, "xtick.major.width": 1.6, "ytick.major.width": 1.6,
    "xtick.major.size": 7, "ytick.major.size": 7,
    "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 20, "axes.labelsize": 23, "xtick.labelsize": 21,
    "ytick.labelsize": 21, "legend.fontsize": 20, "axes.titlesize": 24,
    "lines.linewidth": 3.2, "lines.markersize": 13,
})


def save(fig, name, pad=None):
    fig.savefig(OUT / name, **({"pad_inches": pad} if pad else {}))
    plt.close(fig)
    print(f"  wrote figs/{name}")
    return name


# ---------------------------------------------------------------- 1 kW at 1 V
def f_current():
    fig, ax = plt.subplots(figsize=(12.4, 5.0))
    ax.axis("off")
    ax.set_xlim(0, 10); ax.set_ylim(0, 3.45 if DECK else 4.2)
    if not DECK:
        ax.text(0.0, 3.75, "1 kW delivered at 1 V", fontsize=30, weight="bold",
                color="#222")
    ax.annotate("", xy=(3.05, 2.55), xytext=(0.15, 2.55),
                arrowprops=dict(arrowstyle="-|>", lw=3.5, color=GRY, mutation_scale=28))
    ax.text(1.6, 2.78, "P / V", fontsize=24, ha="center", color=GRY)
    ax.add_patch(Rectangle((3.2, 1.75), 3.3, 1.6, fc=RED, ec="none", alpha=.14))
    ax.text(4.85, 2.55, "≈ 1000 A", fontsize=46, weight="bold", color=RED, ha="center", va="center")
    ax.text(4.85, 1.40, "into a %.1f × %.1f mm die" % (S.DIE_MM, S.DIE_MM),
            fontsize=18, color="#444", ha="center")
    ax.text(7.15, 3.0, "At that current the delivery network,", fontsize=22, color="#222")
    ax.text(7.15, 2.5, "not the converter, sets the ceiling:", fontsize=22, color="#222")
    ax.text(7.15, 1.85, "I²R in a 1 V rail crossing a few mm", fontsize=22, color=RED, weight="bold")
    ax.text(7.15, 1.35, "of package metal rivals the load itself.", fontsize=22, color=RED, weight="bold")
    ax.text(0.0, 0.45, "So the rail must be converted close to the load — and then "
                       "WHERE conversion happens starts to matter.",
            fontsize=22, color="#222", style="italic")
    return save(fig, "p_current.png")


# ------------------------------------------------------------ Z1 vs Z2 rails
def f_rail():
    """Topology is drawn as the frozen replay actually models it:

    Z1 EMBEDDED  - the cell is embedded in the substrate; the TSV is the sliver
                   BELOW it (h_sub - t_cell) and carries the 48 V INPUT.
    Z2 BACKSIDE  - the chiplet sits BELOW the substrate; the TSV crosses the FULL
                   substrate and carries the 1 V OUTPUT.
    Substrate thicknesses are drawn to a common scale.
    """
    fig = plt.figure(figsize=(13.6, 6.4))
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
    ax.set_xlim(0, 100); ax.set_ylim(0, 92 if DECK else 100)
    SC = 40.0 / (S.H_SUB_MM["Z1"] * 1e3)          # drawing units per micron
    YS, YD0, YD1 = 24.0, 68.0, 80.0               # substrate base, die bottom/top

    def panel(x0, w, case, col):
        hsub = S.H_SUB_MM[case] * 1e3
        htsv = S.H_TSV_UM[case]
        top = 64.0                                   # substrate top, common to both
        sb = top - hsub * SC                         # substrate underside
        ax.add_patch(Rectangle((x0 + 2, 8), w - 4, 7, fc="#D8D8D8", ec="k", lw=1.5))
        ax.text(x0 + w / 2, 11.5, "board", fontsize=16, ha="center", va="center")
        for i in range(5):
            bx = x0 + 5 + i * (w - 10) / 4.0
            ax.add_patch(Rectangle((bx - 1.1, 15), 2.2, 3.4, fc="#AAAAAA", ec="k", lw=1.0))
        ax.add_patch(Rectangle((x0 + 2, YD0), w - 4, YD1 - YD0, fc="#BFD9EE",
                               ec="k", lw=1.6))
        ax.text(x0 + w / 2, (YD0 + YD1) / 2, "compute die", fontsize=17,
                ha="center", va="center")
        for i in range(7):
            bx = x0 + 5 + i * (w - 10) / 6.0
            ax.add_patch(Rectangle((bx - .8, top), 1.6, YD0 - top, fc="#AAAAAA",
                                   ec="k", lw=0.9))

        if case == "Z1":
            ybt = sb + htsv * SC                             # top of the TSV sliver
            ax.add_patch(Rectangle((x0, sb), w, hsub * SC, fc=LIGHT, ec="k", lw=1.8))
            ax.add_patch(Rectangle((x0 + 3, ybt), w - 6, top - ybt - 1.5,
                                   fc=col, ec="k", lw=1.5, alpha=.85))
            ax.text(x0 + w / 2, (ybt + top) / 2 - 0.7, "HVR cell\nembedded in substrate",
                    fontsize=16, color="w", ha="center", va="center",
                    weight="bold", linespacing=1.3)
            for i in range(5):
                vx = x0 + 6 + i * (w - 12) / 4.0
                ax.annotate("", xy=(vx, ybt), xytext=(vx, sb),
                            arrowprops=dict(arrowstyle="-|>", lw=1.8, color=col,
                                            mutation_scale=11, shrinkA=0, shrinkB=0))
            ax.annotate("TSV = %.0f \u00b5m\nthe 48 V input" % htsv,
                        xy=(x0 + w - 4, sb + htsv * SC / 2),
                        xytext=(x0 + w + 2.0, sb - 8.0), fontsize=15.5, color=col,
                        weight="bold", ha="center", linespacing=1.3,
                        arrowprops=dict(arrowstyle="-", lw=1.5, color=col))
        else:
            ax.add_patch(Rectangle((x0 + 3, YS), w - 6, sb - YS - 1.5,
                                   fc=col, ec="k", lw=1.5, alpha=.85))
            ax.text(x0 + w / 2, (YS + sb) / 2 - 0.7, "HVR chiplet\non the backside",
                    fontsize=16, color="w", ha="center", va="center",
                    weight="bold", linespacing=1.3)
            ax.add_patch(Rectangle((x0, sb), w, hsub * SC, fc=LIGHT, ec="k", lw=1.8))
            for i in range(5):
                vx = x0 + 6 + i * (w - 12) / 4.0
                ax.annotate("", xy=(vx, top), xytext=(vx, sb),
                            arrowprops=dict(arrowstyle="-|>", lw=7.0, color=col,
                                            mutation_scale=10, shrinkA=0, shrinkB=0))
            ax.annotate("TSV = %.0f \u00b5m\nthe 1 V output" % htsv,
                        xy=(x0 + w - 1.5, sb + hsub * SC / 2),
                        xytext=(x0 + w + 1.0, sb - 11.0), fontsize=15.5, color=col,
                        weight="bold", ha="center", linespacing=1.3,
                        arrowprops=dict(arrowstyle="-", lw=1.5, color=col))

        ax.text(x0 - 2.6, sb + hsub * SC / 2, "$h_{sub}$ = %.2f mm" % S.H_SUB_MM[case],
                fontsize=15.5, rotation=90, ha="center", va="center", color="#444")
        r = S.RAIL[case]
        ax.text(x0 + w / 2, 88.5, {"Z1": "Z1  embedded", "Z2": "Z2  backside"}[case],
                fontsize=25, weight="bold", color=col, ha="center")
        ax.text(x0 + w / 2, 83.0, "%s   \u00b7   %.0f A system"
                % (r["rail"], r["I"]), fontsize=17, color=col, ha="center",
                weight="bold")
        p = S.PAIR[case]["P_tsv"]
        txt = ("$P_{TSV}$ = %.3f W" % p if p > 0.01
               else "$P_{TSV}$ below 0.2 mW\n(effectively zero)")
        ax.text(x0 + w / 2, 2.6, txt, fontsize=18, weight="bold", color=col,
                ha="center", va="center", linespacing=1.3)

    panel(8.0, 34.0, "Z1", BLU)
    panel(58.0, 34.0, "Z2", ORA)
    if not DECK:
        ax.text(50, 95.2, "Where the conversion sits decides which rail crosses "
                "the substrate", fontsize=23, weight="bold", ha="center",
                va="center", color="#111")
    return save(fig, "p_rail.png", pad=0.08)


# ------------------------------------------- the vertical loss follows the rail
def f_tsvloss():
    fig, ax = plt.subplots(figsize=(12.4, 5.6))
    fig.subplots_adjust(bottom=0.24, top=0.87)
    v = [abs(S.PAIR["Z1"]["P_tsv"]), S.PAIR["Z2"]["P_tsv"]]
    ax.bar([0, 1], v, 0.5, color=[BLU, ORA], ec="k", lw=1.6, zorder=3)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(
        ["Z1 \u2014 48 V input\n%.0f A through %.0f \u00b5m"
         % (S.RAIL["Z1"]["I"], S.H_TSV_UM["Z1"]),
         "Z2 \u2014 1 V output\n%.0f A through %.0f \u00b5m"
         % (S.RAIL["Z2"]["I"], S.H_TSV_UM["Z2"])], fontsize=19)
    ax.set_ylabel("vertical loss  (W)", fontsize=21)
    ax.set_ylim(0, 1.78)
    ax.text(0, 0.055, "below 0.2 mW", fontsize=25, weight="bold", color=BLU, ha="center")
    ax.text(1, v[1] + 0.045, "%.3f W" % v[1], fontsize=28, weight="bold",
            color=ORA, ha="center")
    ax.grid(axis="y", alpha=.25, zorder=0)
    _tit(ax, "The vertical loss follows the rail, not the via",
                 fontsize=25, weight="bold", pad=14)
    ax.text(0.5, 0.985, "Z1 carries %.0f\u00d7 less current through a %.1f\u00d7 shorter "
                        "path.\nGeometry \u00d7 assigned rail \u00d7 current \u00d7 "
                        "allocation \u2014 not \u201cTSV resistance\u201d \u2014 is the "
                        "architecture metric."
            % (S.RAIL["Z2"]["I"] / S.RAIL["Z1"]["I"],
               S.H_TSV_UM["Z2"] / S.H_TSV_UM["Z1"]),
            transform=ax.transAxes, va="top",
            fontsize=17.5, ha="center", color="#333", linespacing=1.35,
            bbox=dict(boxstyle="round,pad=0.5", fc="#FFF6E8", ec=ORA, lw=1.6))
    return save(fig, "p_tsvloss.png", pad=0.12)


# --------------------------------------------------- tier repartition and AR
def f_tiers():
    fig = plt.figure(figsize=(13.0, 5.8))
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 1.25], wspace=0.32)
    TIERS = [("HS GaN", 685, "#8C9196"), ("C_f", 100, "#9B7FBF"),
             ("LS GaN", 606, "#3C4A57"), ("L + C_o", 500, "#C0564B")]
    orders = [(["HS GaN", "LS GaN", "C_f", "L + C_o"], "reference", RED,
               S.AR["baseline_T1"]),
              (["HS GaN", "C_f", "LS GaN", "L + C_o"], "repartitioned", GRN,
               S.AR["repartition_C1"])]
    for k, (order, lab, col, ar) in enumerate(orders):
        ax = fig.add_subplot(gs[k]); ax.axis("off")
        ax.set_xlim(0, 3); ax.set_ylim(-520, 2150)
        z = 0
        for nm in order:
            t, c = next((t, c) for n, t, c in TIERS if n == nm)
            ax.add_patch(Rectangle((0.45, z), 2.1, t, fc=c, ec="k", lw=1.3, alpha=.9))
            ax.text(1.5, z + t / 2, nm, fontsize=17, color="w", ha="center",
                    va="center", weight="bold")
            z += t + 10
        _tit(ax, lab, fontsize=24, weight="bold", color=col, pad=10)
        ax.text(1.5, -120, f"worst via AR\n{ar:g}", fontsize=21, weight="bold",
                color=col, ha="center", va="top", linespacing=1.3)
    ax = fig.add_subplot(gs[2])
    nets = ["ls_to_L", "hs_to_ls", "hs_to_cf"]
    show = {"ls_to_L": "SW→L", "hs_to_ls": "HS→LS", "hs_to_cf": "HS→C$_f$"}
    b = [S.NETS["baseline_T1"][n]["ar"] for n in nets]
    r = [S.NETS["repartition_C1"][n]["ar"] for n in nets]
    x = np.arange(3)
    ax.bar(x - .2, b, .38, color=RED, ec="k", lw=1.2, label="reference", zorder=3)
    ax.bar(x + .2, r, .38, color=GRN, ec="k", lw=1.2, label="repartitioned", zorder=3)
    for i, (p, q) in enumerate(zip(b, r)):
        ax.text(i - .2, p * 1.18, f"{p:.2f}", ha="center", fontsize=16, color=RED, weight="bold")
        ax.text(i + .2, q * 1.18, f"{q:.2f}", ha="center", fontsize=16, color=GRN, weight="bold")
    ax.set_yscale("log"); ax.set_ylim(.035, 60)
    ax.set_xticks(x); ax.set_xticklabels([show[n] for n in nets], fontsize=21)
    ax.set_ylabel("worst via aspect ratio", fontsize=22)
    ax.axhline(1.0, color=GRY, ls="--", lw=2)
    ax.legend(fontsize=16, loc="upper left", frameon=False, handlelength=1.3,
              borderaxespad=0.2, labelspacing=0.3)
    ax.grid(axis="y", alpha=.25, zorder=0)
    _sup(fig, "Only the tier LOCATIONS were permuted — same parts, same area, same height",
                 fontsize=23, weight="bold", y=1.04)
    return save(fig, "p_tiers.png")


# ------------------------------------------------- the final cross-domain result
def f_final():
    fig, axes = plt.subplots(1, 4, figsize=(13.2, 5.6))
    fig.subplots_adjust(top=0.70, wspace=0.42)
    items = [("peak temperature\n\u00b0C", "T_max", "%.2f", ORA, "K"),
             ("die warpage\n\u00b5m", "die_warp", "%.2f", GRY, "%"),
             ("driver $\\Delta u_c$\n\u00b5m", "du_c", "%.4f", PUR, "%"),
             ("response $\\Delta\\varepsilon_{in}$\n\u00d710\u207b\u00b2 /cycle", "d_eps", "%.4f", PUR, "%")]
    for ax, (ttl, key, fmt, col, mode) in zip(axes, items):
        sc = 1e2 if key == "d_eps" else 1.0
        a, b = S.PAIR["Z1"][key] * sc, S.PAIR["Z2"][key] * sc
        ax.plot([0, 1], [a, b], "-", color=col, lw=3.5, zorder=2)
        ax.plot([0], [a], "o", color=BLU, ms=18, zorder=3, mec="k", mew=1.4)
        ax.plot([1], [b], "o", color=ORA, ms=18, zorder=3, mec="k", mew=1.4)
        lo, hi = min(a, b), max(a, b); sp = hi - lo
        ax.set_ylim(lo - .60 * sp, hi + .50 * sp)
        ax.set_xlim(-.45, 1.45)
        ax.set_xticks([0, 1]); ax.set_xticklabels(["Z1", "Z2"], fontsize=22)
        ax.text(0, a + (.14 if a > b else -.20) * sp, fmt % a, ha="center",
                fontsize=19, color=BLU, weight="bold")
        ax.text(1, b + (.14 if b > a else -.20) * sp, fmt % b, ha="center",
                fontsize=19, color=ORA, weight="bold")
        _tit(ax, ttl, fontsize=19, color="#333", pad=10, linespacing=1.3)
        ax.set_yticks([]); ax.spines["left"].set_visible(False)
        if mode == "K":
            lab, c = "\u25b2 +%.2f K" % (b - a), RED
        else:
            d = 100 * (b - a) / a
            lab = ("\u25b2 " if d > 0 else "\u25bc ") + "%.1f %%" % abs(d)
            c = RED if d > 0 else GRN
        ax.text(.5, .025, lab, transform=ax.transAxes, ha="center",
                fontsize=22, weight="bold", color=c)
    _sup(fig, "Z2 is the hotter architecture \u2014 and the one with the lower local response",
                 fontsize=25, weight="bold", y=0.99)
    return save(fig, "p_final.png")


# ---------------------------------------- why the response beats the driver
def f_decomp():
    fig, ax = plt.subplots(figsize=(12.2, 5.4))
    d = S.DECOMP
    base = d["z1"]
    bars = [("Z1\n(reference)", base, BLU),
            ("Z2 displacement\nat Z1 temperature", d["du_only"], GRN),
            ("Z1 displacement\nat Z2 temperature", d["T_only"], RED),
            ("Z2\n(both)", d["z2"], ORA)]
    x = np.arange(4)
    ax.bar(x, [b[1] * 1e2 for b in bars], .55, color=[b[2] for b in bars],
           ec="k", lw=1.4, zorder=3)
    for i, (_, v, c) in enumerate(bars):
        pct = 100 * (v / base - 1)
        lbl = f"{v*1e2:.3f}" + ("" if i == 0 else f"\n{pct:+.2f} %")
        ax.text(i, v * 1e2 + .025, lbl, ha="center", fontsize=19, weight="bold",
                color=c, linespacing=1.25)
    ax.set_xticks(x); ax.set_xticklabels([b[0] for b in bars], fontsize=18)
    ax.set_ylabel("$\\Delta\\varepsilon_{in}$  (×10⁻² /cycle)", fontsize=22)
    ax.set_ylim(0, 1.72)
    ax.grid(axis="y", alpha=.25, zorder=0)
    _tit(ax, "The displacement does the work; the hotter joint gives some back",
                 fontsize=24, weight="bold", pad=14)
    return save(fig, "p_decomp.png")


# ------------------------------------------------------------- CETOL ladder
def f_cetol():
    fig, ax = plt.subplots(figsize=(12.6, 5.6))
    fig.subplots_adjust(bottom=0.30, top=0.86)
    conv = [i for i, c in enumerate(S.CETOL) if c["converged"]]
    ax.bar(range(len(S.CETOL)), [1 if c["converged"] else 0.08 for c in S.CETOL], .5,
           color=[GRN if c["converged"] else "#BBBBBB" for c in S.CETOL],
           ec="k", lw=1.4, zorder=3)
    for i, c in enumerate(S.CETOL):
        if not c["converged"]:
            ax.text(i, 0.14, "does not\nconverge", ha="center", fontsize=17,
                    color="#777", linespacing=1.25)
    a, b = conv[0], conv[-1]
    ax.plot([a, a, b, b], [1.04, 1.11, 1.11, 1.04], color=GRN, lw=2.2, zorder=4)
    ax.text((a + b) / 2, 1.155, "identical", ha="center", va="bottom", fontsize=19,
            weight="bold", color=GRN)
    ax.text(-0.42, 1.50, "$D_\\varepsilon$ = %.6f at both\nsame %d increments, zero "
            "cutbacks\nidentical to all twelve printed digits"
            % (S.CETOL[a]["d_eps"], S.CETOL[a]["incr"]),
            ha="left", va="top", fontsize=18, color="#222", linespacing=1.35)
    ax.set_xticks(range(len(S.CETOL)))
    ax.set_xticklabels([f"{c['cetol']:g}" for c in S.CETOL], fontsize=21)
    ax.set_xlabel("creep strain-increment tolerance (CETOL)", fontsize=22)
    ax.set_yticks([]); ax.spines["left"].set_visible(False)
    ax.set_ylim(0, 1.58)
    _tit(ax, "Relaxing the tolerance changes the answer by exactly zero",
                 fontsize=24, weight="bold", pad=12)
    ax.text(.5, -.34, "Once CETOL is loose enough to start, the step schedule binds, not the "
                      "tolerance.\nNo tighter tolerance converges \u2014 the bracket is "
                      "ONE-SIDED, and the magnitude stays conditional.",
            transform=ax.transAxes, ha="center", va="top", fontsize=17.5,
            color="#111", linespacing=1.4,
            bbox=dict(fc="#FFF4F0", ec=RED, lw=1.8, boxstyle="round,pad=0.45"))
    return save(fig, "p_cetol.png", pad=0.14)


# ---------------------------------------------------------- converter topology
def f_converter():
    C = S.CONVERTER
    fig, ax = plt.subplots(figsize=(13.8, 5.4))
    ax.axis("off"); ax.set_xlim(0, 100); ax.set_ylim(-2, 42)
    YB, YT, YM = 14.0, 32.0, 23.0

    def box(x, w, lab, sub, col, fill=None):
        ax.add_patch(Rectangle((x, YB), w, YT - YB, fc=fill or col, ec="none",
                               alpha=.15, zorder=2))
        ax.add_patch(Rectangle((x, YB), w, YT - YB, fc="none", ec=col, lw=2.8, zorder=3))
        ax.text(x + w / 2, 26.6, lab, ha="center", va="center", fontsize=21,
                weight="bold", color=col, zorder=4)
        ax.text(x + w / 2, 18.6, sub, ha="center", va="center", fontsize=16.5,
                color="#333", zorder=4, linespacing=1.3)

    def rail(x, v, col):
        ax.plot([x, x], [11, 36], color=col, lw=3.4, zorder=1, solid_capstyle="round")
        ax.text(x, 38.2, v, ha="center", fontsize=22, weight="bold", color=col)

    def arrow(x0, x1):
        ax.add_patch(FancyArrowPatch((x0, YM), (x1, YM), arrowstyle="-|>",
                                     mutation_scale=22, lw=2.6, color="#333", zorder=5))

    rail(4.0, "48 V", BLU)
    arrow(5.6, 10.3)
    box(11.0, 25.0, "switched capacitor", "%d:1 charge transfer\nno magnetics"
        % (C["V_in"] / C["V_mid"]), BLU)
    rail(41.0, "16 V", PUR)
    arrow(36.6, 40.0)
    arrow(42.0, 45.8)
    box(46.5, 30.0, "%d-phase buck  × M" % C["N"],
        "D = %.4f      $f_{sw}$ = %.0f kHz" % (C["D"], C["f_sw_kHz"]), ORA)
    rail(81.0, "1 V", ORA)
    arrow(77.1, 80.0)
    arrow(82.0, 84.8)
    ax.add_patch(Rectangle((85.5, YB), 13.5, YT - YB, fc=GRY, ec="k", lw=2.4,
                           alpha=.30, zorder=2))
    ax.text(92.2, 26.6, "logic die", ha="center", va="center", fontsize=20,
            weight="bold", color="#222", zorder=4)
    ax.text(92.2, 18.8, "≈ 1000 A", ha="center", va="center", fontsize=18,
            weight="bold", color=RED, zorder=4)

    ax.text(50, 6.4, "M = %d cells   ·   %.3f A/cell   ·   %.2f mm²/cell"
            % (C["M"], C["I_cell"], C["A_cell"]),
            ha="center", fontsize=19, color="#222", weight="bold")
    ax.text(50, 0.0, "A single 48 V → 1 V stage would need an impractical duty ratio; "
                     "the 16 V intermediate rail is what makes D = %.4f reachable." % C["D"],
            ha="center", fontsize=18, color="#333")
    _sup(fig, "Hybrid converter: switched-capacitor pre-stage + multiphase buck",
                 fontsize=24, weight="bold", y=1.03)
    return save(fig, "p_converter.png")


# ------------------------------------------------------- where the watts move
def f_loss():
    GROUPS = [("switch conduction", ["P_switch_hs_conduction", "P_switch_ls_conduction"]),
              ("inductor DCR",      ["P_inductor_DCR"]),
              ("switching + gate",  ["P_switching_hard", "P_gate", "P_Coss"]),
              ("in-VR + pkg metal", ["P_intraVR_metal", "P_intraVR_vertical",
                                     "P_bumps", "P_pkg_RDL"]),
              ("capacitor ESR",     ["P_cap_ESR"]),
              ("TSV",               ["P_TSV"])]
    z1 = {g: sum(S.LOSS["Z1"][k] for k in ks) for g, ks in GROUPS}
    z2 = {g: sum(S.LOSS["Z2"][k] for k in ks) for g, ks in GROUPS}
    t1, t2 = sum(z1.values()), sum(z2.values())

    fig = plt.figure(figsize=(13.8, 5.9))
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.75], wspace=0.62)

    ax = fig.add_subplot(gs[0])
    ax.bar([0, 1], [t1, t2], .52, color=[BLU, ORA], ec="k", lw=1.5, zorder=3)
    ax.plot([-.42, 1.42], [t1, t1], ls="--", lw=2.0, color=GRY, zorder=4)
    for i, v in enumerate((t1, t2)):
        ax.text(i, v + 2.5, "%.1f W" % v, ha="center", fontsize=17.5, weight="bold",
                color=[BLU, ORA][i])
    ax.text(.5, t2 * 1.26, "+%.2f W\n(+%.1f %%)" % (t2 - t1, 100 * (t2 / t1 - 1)),
            ha="center", va="center", fontsize=19, weight="bold", color=RED,
            linespacing=1.25)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Z1\nembedded", "Z2\nbackside"], fontsize=18)
    ax.set_xlim(-.62, 1.62)
    ax.set_ylabel("converter loss  (W)", fontsize=21)
    ax.set_ylim(0, t2 * 1.44); ax.grid(axis="y", alpha=.25, zorder=0)
    _tit(ax, "total", fontsize=21, weight="bold", pad=8)

    ax = fig.add_subplot(gs[1])
    names = [g for g, _ in GROUPS]
    d = [z2[g] - z1[g] for g in names]
    order = np.argsort(d)
    y = np.arange(len(names))
    cols = [RED if names[i] == "TSV" else GRY for i in order]
    ax.barh(y, [d[i] for i in order], .58, color=cols, ec="k", lw=1.3, zorder=3)
    for j, i in enumerate(order):
        ax.text(d[i] + 0.035, j, "%+.3f W" % d[i], va="center", fontsize=17.5,
                weight="bold", color=cols[j])
    ax.set_yticks(y); ax.set_yticklabels([names[i] for i in order], fontsize=18)
    ax.set_xlabel("change in loss, Z2 − Z1  (W)", fontsize=21)
    ax.set_xlim(-0.05, max(d) * 1.40)
    ax.grid(axis="x", alpha=.25, zorder=0)
    ax.axvline(0, color="k", lw=1.6)
    _tit(ax, "where the difference comes from", fontsize=21, weight="bold", pad=8)

    tsv = z2["TSV"] - z1["TSV"]
    fig.text(.5, -.055, "The TSV carries %.0f %% of the change. The rest is thermal "
                        "feedback — the hotter architecture is the more resistive one."
             % (100 * tsv / (t2 - t1)),
             ha="center", va="top", fontsize=18.5, color="#111",
             bbox=dict(fc="#FFF4F0", ec=RED, lw=1.8, boxstyle="round,pad=0.45"))
    _sup(fig, "Moving the regulator costs about %.1f W out of about %.0f W"
                 % (t2 - t1, t1), fontsize=24, weight="bold", y=1.07)
    return save(fig, "p_loss.png", pad=0.22)


# ------------------------------------------------------------------- cooling
def f_cooling():
    C = S.COOLING
    fig = plt.figure(figsize=(13.8, 5.6))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.0], wspace=0.06,
                          left=0.015, right=0.985, top=0.87, bottom=0.03)

    ax = fig.add_subplot(gs[0]); ax.axis("off")
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    ax.add_patch(Rectangle((1.1, 6.6), 8.3, 1.6, fc=GRY, ec="k", lw=1.8, alpha=.45))
    ax.text(5.25, 7.4, "die", ha="center", va="center", fontsize=20, weight="bold")
    for i in range(9):
        x = 1.35 + i * 0.90
        ax.add_patch(Rectangle((x, 4.1), 0.42, 2.5, fc="#CFE8F5", ec=BLU, lw=1.8))
    ax.add_patch(Rectangle((1.1, 3.3), 8.3, 0.8, fc=GRY, ec="k", lw=1.8, alpha=.25))
    ax.annotate("", xy=(1.77, 2.75), xytext=(1.35, 2.75),
                arrowprops=dict(arrowstyle="<->", lw=2.0, color=BLU,
                                shrinkA=0, shrinkB=0))
    ax.text(2.05, 2.75, "w = %d \u00b5m" % C["w_um"], fontsize=17, va="center", color=BLU)
    ax.annotate("", xy=(0.92, 6.55), xytext=(0.92, 4.15),
                arrowprops=dict(arrowstyle="<->", lw=2.0, color=BLU,
                                shrinkA=0, shrinkB=0))
    ax.text(0.58, 5.35, "h = %d \u00b5m" % C["h_um"], fontsize=17, rotation=90,
            va="center", ha="center", color=BLU)
    ax.text(5.25, 1.55, "%d parallel microchannels" % C["channels"],
            ha="center", fontsize=20, weight="bold", color=BLU)
    ax.text(5.25, 0.55, "water, %.0f \u00b0C inlet, %.0f g/s"
            % (C["T_in_C"], C["m_dot_g_s"]), ha="center", fontsize=18, color="#333")

    ax = fig.add_subplot(gs[1]); ax.axis("off")
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    rows = [("Reynolds number", "%.0f" % C["Re"], "laminar (< 2300)"),
            ("effective coefficient", "%.1f kW/m\u00b2K" % C["h_eff_kW"], ""),
            ("coolant rise", "%.2f K" % C["dT_K"], ""),
            ("pressure drop", "%.3f MPa" % C["dp_MPa"], ""),
            ("pump power", "%.1f W" % C["P_pump_W"], "")]
    y = 9.4
    for k, v, note in rows:
        ax.text(0.15, y, k, fontsize=18, va="center", color="#333")
        ax.text(5.55, y, v, fontsize=19, va="center", weight="bold", color=BLU)
        if note:
            ax.text(5.55, y - 0.66, note, fontsize=15, va="center", color=GRN)
        y -= 1.60
    ax.text(0.15, 1.15, "Pump power is not free: about %.0f %% of\nthe converter loss "
                        "it is there to remove."
            % (100 * C["P_pump_W"] / S.PAIR["Z1"]["P_elec"]),
            fontsize=16.5, color="#222", linespacing=1.35, va="center",
            bbox=dict(fc="#F2F7FB", ec=BLU, lw=1.6, boxstyle="round,pad=0.42"))
    _sup(fig, "The cooling solution is fixed and identical for both architectures",
                 fontsize=24, weight="bold", y=0.99)
    return save(fig, "p_cooling.png", pad=0.10)


# --------------------------------------------- three different quantities
def f_mech_chain():
    fig = plt.figure(figsize=(13.8, 6.0))
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
    ax.set_xlim(0, 100); ax.set_ylim(0, 41 if DECK else 48)
    P = S.PAIR
    stages = [
        ("global warpage", "die-level shape of\nthe whole package",
         "%.2f → %.2f µm" % (P["Z1"]["die_warp"], P["Z2"]["die_warp"]),
         "not the driver", GRY),
        ("local driver  $\\Delta u_c$", "what the critical\njoint actually sees",
         "%.4f → %.4f µm" % (P["Z1"]["du_c"], P["Z2"]["du_c"]),
         "not the response", PUR),
        ("local response  $\\Delta\\varepsilon_{in}$", "how the solder\nresponds to that driver",
         "%.4f → %.4f" % (P["Z1"]["d_eps"] * 1e2, P["Z2"]["d_eps"] * 1e2),
         "not damage, not life", ORA)]
    w = 29.0
    for i, (ttl, sub, val, cav, col) in enumerate(stages):
        x = 1.5 + i * 34.0
        ax.add_patch(Rectangle((x, 13), w, 22, fc=col, ec="none", alpha=.14, zorder=2))
        ax.add_patch(Rectangle((x, 13), w, 22, fc="none", ec=col, lw=2.8, zorder=3))
        ax.text(x + w / 2, 31.0, ttl, ha="center", va="center", fontsize=20,
                weight="bold", color=col, zorder=4)
        ax.text(x + w / 2, 24.0, sub, ha="center", va="center", fontsize=16.5,
                color="#333", zorder=4, linespacing=1.3)
        ax.text(x + w / 2, 17.4, val, ha="center", va="center", fontsize=17.5,
                weight="bold", color="#111", zorder=4)
        ax.text(x + w / 2, 37.4, cav, ha="center", va="center", fontsize=16.5,
                color=RED, style="italic", zorder=4,
                weight="bold" if i == 2 else "normal")
        if i < 2:
            ax.add_patch(FancyArrowPatch((x + w + 0.7, 24.0), (x + 33.3, 24.0),
                                         arrowstyle="-|>", mutation_scale=24,
                                         lw=2.8, color="#333", zorder=5))
    ax.text(84.0, 14.4, "×10⁻² per cycle", ha="center", va="center",
            fontsize=14.5, color="#555", zorder=4)
    ax.text(50, 6.0, "A response is not damage, damage is not life, and life is not failure.\n"
                     "No fatigue model was run and no mechanical pass/fail is claimed.",
            ha="center", va="center", fontsize=18.5, color="#111", linespacing=1.4,
            weight="bold",
            bbox=dict(fc="#FFF4F0", ec=RED, lw=2.0, boxstyle="round,pad=0.5"))
    if not DECK:
        ax.text(50, 44.0, "Three quantities that are routinely conflated",
                ha="center", va="center", fontsize=25, weight="bold", color="#111")
    return save(fig, "p_mech_chain.png", pad=0.05)


# ------------------------------------------------- the bridge between halves
def f_bridge():
    fig = plt.figure(figsize=(13.8, 6.2))
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
    ax.set_xlim(0, 100); ax.set_ylim(0, 43 if DECK else 50)
    T = S.TRANSIENT

    def half(x, w, col, head, lines, foot):
        ax.add_patch(Rectangle((x, 12), w, 28, fc=col, ec="none", alpha=.13, zorder=2))
        ax.add_patch(Rectangle((x, 12), w, 28, fc="none", ec=col, lw=2.8, zorder=3))
        ax.text(x + w / 2, 36.4, head, ha="center", va="center", fontsize=22,
                weight="bold", color=col, zorder=4)
        y = 31.0
        for ln in lines:
            ax.text(x + w / 2, y, ln, ha="center", va="center", fontsize=17,
                    color="#222", zorder=4)
            y -= 3.9
        ax.plot([x + 4, x + w - 4], [20.6, 20.6], color=col, lw=1.6, alpha=.55, zorder=4)
        ax.text(x + w / 2, 16.4, foot, ha="center", va="center", fontsize=16.5,
                weight="bold", color=col, zorder=4, linespacing=1.4)

    half(2.0, 44.0, BLU, "milliseconds",
         ["power gating, workload steps", "the die heats and cools",
          "repeated transient stepping"],
         "%.1f\u00d7 faster matched stepping\n(%.0f s vs %.0f s, %d steps)"
         % (T["ratio_400"], T["fv_400_s"], T["moose_400_s"], T["crossover"]["steps"][-1]))
    half(54.0, 44.0, ORA, "architecture",
         ["where the regulator sits", "steady electrothermal state",
          "local mechanical response"],
         "Z1 \u2192 Z2 moves %.2f K,\n%.1f %% $\\Delta u_c$,   %.1f %% $\\Delta\\varepsilon_{in}$"
         % (S.DT, S.RED_U, S.RED_E))

    ax.add_patch(FancyArrowPatch((47.0, 26.0), (53.0, 26.0), arrowstyle="<|-|>",
                                 mutation_scale=24, lw=3.0, color="#333", zorder=5))
    ax.text(50, 5.2, "Both halves make the same point: a power delivery decision is only "
                     "meaningful\nwhen it is evaluated on the physical package, at the "
                     "timescale the system actually runs.",
            ha="center", va="center", fontsize=18.5, color="#111", linespacing=1.45,
            weight="bold",
            bbox=dict(fc="#F4F4F4", ec="#333", lw=2.0, boxstyle="round,pad=0.55"))
    if not DECK:
        ax.text(50, 46.2, "Two timescales, one design principle", ha="center",
                va="center", fontsize=25, weight="bold", color="#111")
    return save(fig, "p_bridge.png", pad=0.05)


# ------------------------------------------- what each modeling level resolves
def f_scope():
    fig = plt.figure(figsize=(13.4, 5.8))
    ax = fig.add_axes([0.012, 0.055, 0.976, 0.80]); ax.axis("off")
    rows = ["circuit-level VR model", "steady package thermal",
            "stand-alone mechanical FEA", "coupled evaluation (this work)"]
    cols = ["loss and\nefficiency", "package\ngeometry", "transient\nresponse",
            "solder\nresponse"]
    M = [[1, 0, 0, 0],
         [0, 1, 0, 0],
         [0, 1, 0, 1],
         [1, 1, 1, 1]]
    nr, nc = len(rows), len(cols)
    ax.set_xlim(-3.5, nc); ax.set_ylim(-2.0, nr + 0.30)
    for j, c in enumerate(cols):
        ax.text(j + .5, nr - 0.52, c, ha="center", va="bottom", fontsize=17,
                weight="bold", color="#222", linespacing=1.3)
    for i, r in enumerate(rows):
        yy = nr - 1.6 - i
        last = (i == nr - 1)
        ax.text(-3.42, yy + .5, r, ha="left", va="center", fontsize=18,
                weight="bold" if last else "normal", color=GRN if last else "#333")
        for j in range(nc):
            ok = M[i][j]
            ax.add_patch(Rectangle((j + .06, yy + .08), .88, .84,
                                   fc=(GRN if last else BLU) if ok else "#F0F0F0",
                                   ec="#BBBBBB", lw=1.2, alpha=.90 if ok else 1.0))
            ax.text(j + .5, yy + .50, "\u2713" if ok else "\u2014", ha="center",
                    va="center", fontsize=23, weight="bold",
                    color="w" if ok else "#999")
    ax.text(-3.42, -1.28, "Each row is useful. The point is that the rows answer "
                          "different questions,\nand the architecture question needs "
                          "more than one of them at a time.",
            ha="left", va="center", fontsize=17.5, color="#333", linespacing=1.35)
    _sup(fig, "What each level of model can and cannot answer",
                 fontsize=24, weight="bold", y=0.99)
    return save(fig, "p_scope.png", pad=0.10)


PAIR_TSV = {"Z1": abs(S.PAIR["Z1"]["P_tsv"]), "Z2": S.PAIR["Z2"]["P_tsv"]}

ALL = (f_current, f_rail, f_tsvloss, f_tiers, f_final, f_decomp, f_cetol,
       f_converter, f_loss, f_cooling, f_mech_chain, f_bridge, f_scope)

if __name__ == "__main__":
    for f in ALL:
        f()
