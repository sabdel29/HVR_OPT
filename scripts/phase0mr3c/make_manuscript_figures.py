#!/usr/bin/env python3
"""TCPMT manuscript figures. All data read from frozen artifacts; nothing is re-solved.

A single figure system is used throughout: serif type matching the manuscript, 6.2-7.6 pt
text, colourblind-safe palette, grayscale-distinguishable markers and line styles, SI units,
no boxes or backgrounds, vector PDF output.
"""
from __future__ import annotations
import csv, math, re, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                          # noqa: E402
import numpy as np                                                       # noqa: E402
from matplotlib.patches import Rectangle, FancyArrowPatch, FancyBboxPatch  # noqa: E402

R = Path(__file__).resolve().parents[2]
C3 = R / "results" / "phase0mr3c"
FIG = R / "manuscript" / "figs"
FIG.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 240, "savefig.bbox": "tight", "savefig.pad_inches": 0.015,
    "font.size": 7.0, "font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "axes.grid": True, "grid.alpha": .25, "grid.linewidth": .45, "grid.linestyle": "-",
    "axes.linewidth": .6, "axes.labelsize": 7.2, "axes.titlesize": 7.4,
    "xtick.labelsize": 6.6, "ytick.labelsize": 6.6, "legend.fontsize": 6.4,
    "xtick.major.width": .6, "ytick.major.width": .6,
    "xtick.major.size": 2.4, "ytick.major.size": 2.4,
    "lines.linewidth": 1.2, "lines.markersize": 3.4,
    "legend.frameon": False, "axes.axisbelow": True,
})
# colourblind-safe (Okabe-Ito), ordered for grayscale separation too
BLU, VER, GRN, ORA, PUR, GRY, YEL = ("#0072B2", "#D55E00", "#009E73", "#E69F00",
                                     "#CC79A7", "#5A5A5A", "#F0E442")


def rd(n, base=C3):
    return list(csv.DictReader((Path(base) / n).open()))


def panel(ax, tag, x=-0.135, y=1.06):
    ax.text(x, y, tag, transform=ax.transAxes, fontsize=7.6, weight="bold", va="top")


def nogrid(ax):
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks([]); ax.set_yticks([])


# ============================================================ FIG 1 system + HVR + flow
def fig1():
    fig = plt.figure(figsize=(7.16, 2.62))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.00, 1.28, 1.16], wspace=0.14)
    a, b, c = (fig.add_subplot(gs[i]) for i in range(3))

    # (a) DVPD system cross-section
    nogrid(a)
    a.add_patch(Rectangle((0.10, 0.74), 0.80, 0.11, fc="#BFD9EE", ec="k", lw=.6))
    a.text(0.50, 0.795, "compute die, 1 kW @ 1 V", ha="center", va="center", fontsize=6.3)
    a.add_patch(Rectangle((0.10, 0.855), 0.80, 0.075, fc="#EAF4FB", ec="k", lw=.6))
    for i in range(16):
        a.add_patch(Rectangle((0.115 + i * 0.0485, 0.862), 0.022, 0.061,
                              fc="#9EC9E8", ec="none"))
    a.text(0.50, 0.958, "microchannel cold plate, 27 g s$^{-1}$", ha="center",
           va="center", fontsize=6.0)
    for i in range(7):
        x = 0.135 + i * 0.109
        a.add_patch(Rectangle((x, 0.52), 0.085, 0.175, fc="#FBE3CF", ec="k", lw=.5))
        a.text(x + .0425, 0.607, "VR", ha="center", va="center", fontsize=5.4)
        a.annotate("", xy=(x + .0425, 0.735), xytext=(x + .0425, 0.697),
                   arrowprops=dict(arrowstyle="-|>", color=VER, lw=.9, mutation_scale=6))
    a.text(0.50, 0.455, r"$M=49$ cells, $20.4$ A each", ha="center", fontsize=6.0, color=VER)
    a.add_patch(Rectangle((0.10, 0.33), 0.80, 0.105, fc="#E8E8E8", ec="k", lw=.6))
    a.text(0.50, 0.382, "package substrate", ha="center", va="center", fontsize=6.3)
    a.add_patch(Rectangle((0.10, 0.20), 0.80, 0.085, fc="#DCDCDC", ec="k", lw=.6))
    a.text(0.50, 0.242, "board", ha="center", va="center", fontsize=6.3)
    a.annotate("", xy=(0.10, 0.375), xytext=(-0.03, 0.375),
               arrowprops=dict(arrowstyle="-|>", color=BLU, lw=1.5, mutation_scale=7))
    a.text(-0.035, 0.425, "48 V", fontsize=6.4, color=BLU, weight="bold")
    a.set_xlim(-0.10, 1.0); a.set_ylim(0.14, 1.03)
    a.set_title("(a)  distributed vertical power delivery", fontsize=7.2, loc="left")

    # (b) HVR topology
    nogrid(b)
    def dev(x, y, lab, col):
        b.add_patch(Rectangle((x - .038, y - .030), .076, .060, fc=col, ec="k", lw=.55))
        b.text(x, y, lab, ha="center", va="center", fontsize=5.2, color="w", weight="bold")
    def wire(p, q, col="k", lw=.7, ls="-"):
        b.plot([p[0], q[0]], [p[1], q[1]], color=col, lw=lw, ls=ls, solid_capstyle="round")
    b.text(0.02, 0.945, "48 V", fontsize=6.6, color=BLU, weight="bold")
    wire((0.09, 0.925), (0.90, 0.925), BLU, 1.5)
    for i in range(3):                                      # N = 3 SC branches
        x = 0.20 + i * 0.27
        dev(x, 0.80, "HS", "#0072B2")
        wire((x, 0.925), (x, 0.830))
        if i < 2:
            b.add_patch(Rectangle((x + .105, .755), .022, .09, fc="none", ec=PUR, lw=1.1))
            b.text(x + .116, .715, r"$C_{f}$", ha="center", fontsize=5.6, color=PUR)
            wire((x, 0.770), (x + .116, 0.770), PUR, .8)
            wire((x + .116, .755), (x + .116, .700), PUR, .8)
        wire((x, 0.770), (x, 0.660))
    b.text(0.955, 0.655, "16 V", fontsize=6.2, color=ORA, weight="bold", ha="right")
    wire((0.13, 0.615), (0.90, 0.615), ORA, 1.3)
    for i in range(3):                                      # K = 3 buck phases
        x = 0.20 + i * 0.27
        wire((x, 0.615), (x, 0.520))
        dev(x, 0.485, "LS", "#D55E00")
        wire((x, 0.455), (x, 0.360))
        b.plot([x - .03, x + .03], [0.360, 0.360], color="k", lw=.7)
        for k in range(4):                                  # inductor coil
            b.add_patch(plt.Circle((x - .022 + k * .015, 0.345), .0085,
                                   fill=False, ec=GRN, lw=.9))
        b.text(x, 0.300, r"$L$", ha="center", fontsize=5.8, color=GRN)
        wire((x, 0.336), (x, 0.240), GRN, .9)
        b.text(x + .045, 0.487, r"SW", fontsize=5.2, color=VER)
    b.text(0.955, 0.283, "1 V", fontsize=6.6, color=VER, weight="bold", ha="right")
    wire((0.13, 0.240), (0.90, 0.240), VER, 1.8)
    b.add_patch(Rectangle((0.60, .130), .022, .075, fc="none", ec=PUR, lw=1.1))
    b.text(0.611, .095, r"$C_{o}$", ha="center", fontsize=5.6, color=PUR)
    wire((0.611, .240), (0.611, .205), PUR, .8)
    b.add_patch(Rectangle((0.79, .120), .105, .085, fc="#BFD9EE", ec="k", lw=.6))
    b.text(0.842, .162, "POL", ha="center", va="center", fontsize=5.6)
    wire((0.842, .240), (0.842, .205), VER, 1.4)
    b.plot([0.13, 0.90], [0.055, 0.055], color="k", lw=1.0)
    for x in (0.20, 0.47, 0.74, 0.611, 0.842):
        wire((x, 0.120 if x in (0.611, 0.842) else 0.455), (x, 0.055), "k", .55, ":")
    b.set_xlim(0.0, 1.0); b.set_ylim(0.02, 1.0)
    b.set_title(r"(b)  hybrid regulator, $N{=}3$, $K{=}3$, $f_{\rm sw}{=}805$ kHz",
                fontsize=7.2, loc="left")

    # (c) framework flow
    nogrid(c)
    nodes = {
        "syn":  (0.20, 0.885, "converter\nsynthesis", BLU),
        "stk":  (0.20, 0.630, "physical stack:\ntiers, heights, area", "#1b6ca8"),
        "pdn":  (0.20, 0.375, "rail-aware PPDN\nRDL / via / bump", VER),
        "thm":  (0.72, 0.375, "package thermal\n+ cold plate", ORA),
        "mec":  (0.72, 0.630, "thermoelastic\npackage", GRN),
        "loc":  (0.72, 0.885, "local solder\nresponse", "#145a32"),
        "rlz":  (0.20, 0.120, "realizability:\nAR, landing area", PUR),
    }
    for x, y, t, col in nodes.values():
        c.text(x, y, t, ha="center", va="center", color="w", fontsize=5.6, weight="bold",
               linespacing=1.28, zorder=4,
               bbox=dict(boxstyle="round,pad=0.36", fc=col, ec="k", lw=.55))
    def arr(p, q, rad=0.0, col=GRY, lw=.9):
        c.annotate("", xy=nodes[q][:2], xytext=nodes[p][:2], zorder=2,
                   arrowprops=dict(arrowstyle="-|>", color=col, lw=lw, mutation_scale=6.5,
                                   shrinkA=14, shrinkB=14,
                                   connectionstyle=f"arc3,rad={rad}"))
    for p, q in (("syn", "stk"), ("stk", "pdn"), ("thm", "mec"), ("mec", "loc")):
        arr(p, q)
    arr("stk", "rlz", 0.0, PUR)
    c.annotate("", xy=(0.585, 0.375), xytext=(0.355, 0.375), zorder=3,
               arrowprops=dict(arrowstyle="<|-|>", color=VER, lw=1.2, mutation_scale=6.5))
    c.text(0.470, 0.247, "E–T fixed point, $\\Delta T<0.25$ K", fontsize=5.4,
           color=VER, ha="center", linespacing=1.22)
    c.text(0.815, 0.762, "one-way", fontsize=5.4, color=GRY, ha="left")
    c.set_xlim(-0.02, 1.0); c.set_ylim(0.0, 1.0)
    c.set_title("(c)  framework information flow", fontsize=7.2, loc="left")
    fig.savefig(FIG / "fig1_system.pdf"); plt.close(fig)
    return "fig1_system.pdf"


# ============================================================ FIG 2 physical stack
TIERS = [("gan_hs", 685, "#7f8c8d", "HS GaN"), ("cap_fly", 100, "#8e6aa8", r"$C_f$"),
         ("gan_ls", 606, "#34495e", "LS GaN"), ("ind", 500, "#c0392b", r"$L+C_o$")]


def _cell(ax, x0, w, order, z0=0.0):
    z = z0
    for name in order:
        t, col, lab = next((t, c, l) for n, t, c, l in TIERS if n == name)
        ax.add_patch(Rectangle((x0, z), w, t, fc=col, ec="k", lw=.45, alpha=.85))
        ax.text(x0 + w / 2, z + t / 2, lab, ha="center", va="center", color="w",
                fontsize=5.4, weight="bold")
        z += t + 10
    return z - 10


def fig2():
    """Physical stack and power path. Vertical scale is schematic; layer thicknesses are
    labelled rather than drawn to scale, because the converter cell (1921 um) and the thin
    backside substrate (300 um) cannot share one linear axis legibly."""
    fig, ax = plt.subplots(1, 2, figsize=(7.16, 2.75))
    order = ["gan_hs", "cap_fly", "gan_ls", "ind"]
    CELL_H = sum(t for _, t, _, _ in TIERS) + 30

    for a, ttl, embedded in ((ax[0], r"(a)  embedded (Z1): $h_{\rm sub}=1.30$ mm, "
                              r"TSV field carries 48 V", True),
                             (ax[1], r"(b)  backside (Z2): $h_{\rm sub}=0.30$ mm, "
                              r"TSV field carries 1 V", False)):
        nogrid(a)
        W, XL, XR = 9.4, 0.30, 9.70
        # cold plate
        a.add_patch(Rectangle((XL, 4520), W, 210, fc="#EAF4FB", ec="k", lw=.55))
        for i2 in range(19):
            a.add_patch(Rectangle((XL + 0.14 + i2 * 0.47, 4545), 0.21, 160,
                                  fc="#9EC9E8", ec="none"))
        a.text(XL + W / 2, 4800, r"microchannel cold plate, 27 g s$^{-1}$",
               ha="center", fontsize=6.0)
        # die
        a.add_patch(Rectangle((XL, 4180), W, 300, fc="#BFD9EE", ec="k", lw=.55))
        a.text(XL + W / 2, 4330, "compute die + POL", ha="center", va="center", fontsize=6.3)
        # bumps
        a.add_patch(Rectangle((XL, 4080), W, 70, fc="#F2F2F2", ec="k", lw=.45))
        a.text(XR + 0.12, 4115, "bumps", fontsize=5.5, va="center")

        if embedded:
            sub0, sub1 = 4080 - (CELL_H + 240), 4080
            a.add_patch(Rectangle((XL, sub0), W, sub1 - sub0, fc="#EDEDED", ec="k", lw=.55))
            a.text(XR + 0.12, (sub0 + sub1) / 2, "substrate", fontsize=5.5,
                   va="center", rotation=90, ha="center")
            for jj in range(3):
                _cell(a, XL + 0.55 + jj * 2.95, 1.95, order, z0=sub0 + 120)
            for jj in range(4):                                   # 48 V TSVs in free lanes
                xv = XL + 0.34 + jj * 2.96
                a.annotate("", xy=(xv, sub1 - 15), xytext=(xv, sub0 + 15),
                           arrowprops=dict(arrowstyle="-|>", color=BLU, lw=1.4,
                                           mutation_scale=6))
            a.text(XL + 0.05, sub0 - 190, "49 converter cells embedded in the substrate",
                   fontsize=6.0)
            board_y = sub0 - 560
        else:
            sub0, sub1 = 3760, 4080
            a.add_patch(Rectangle((XL, sub0), W, sub1 - sub0, fc="#EDEDED", ec="k", lw=.55))
            a.text(XR + 0.12, (sub0 + sub1) / 2, "substrate", fontsize=5.5, va="center")
            for jj in range(4):                                   # 1 V TSVs, thick arrows
                xv = XL + 0.34 + jj * 2.96
                a.annotate("", xy=(xv, sub1 - 10), xytext=(xv, sub0 + 10),
                           arrowprops=dict(arrowstyle="-|>", color=VER, lw=3.0,
                                           mutation_scale=8))
            top = sub0 - 200
            for jj in range(3):
                _cell(a, XL + 0.55 + jj * 2.95, 1.95, order, z0=top - CELL_H)
            a.text(XL + 0.05, top + 45, "49 converter cells on the substrate underside",
                   fontsize=6.0)
            board_y = top - CELL_H - 520
        a.add_patch(Rectangle((XL, board_y), W, 150, fc="#DCDCDC", ec="k", lw=.55))
        a.text(XL + W / 2, board_y + 75, "board", ha="center", va="center", fontsize=6.0)
        a.set_xlim(-0.35, 11.5); a.set_ylim(board_y - 130, 4960)
        a.set_title(ttl, fontsize=7.0, loc="left")

    # a shared key
    ax[0].annotate("", xy=(10.70, 2900), xytext=(10.70, 2450),
                   arrowprops=dict(arrowstyle="-|>", color=BLU, lw=1.4, mutation_scale=6))
    ax[0].text(10.55, 2675, "48 V,\n0.48 A", fontsize=5.5, color=BLU, ha="right",
               va="center", linespacing=1.25)
    ax[1].annotate("", xy=(10.70, 3600), xytext=(10.70, 3150),
                   arrowprops=dict(arrowstyle="-|>", color=VER, lw=3.0, mutation_scale=8))
    ax[1].text(10.52, 3375, "1 V,\n20.4 A", fontsize=5.5, color=VER, ha="right",
               va="center", linespacing=1.25)
    fig.text(0.5, -0.02, "Arrow width indicates segment current. The two architectures share "
             "the same converter cell but not the same vertical rail; the vertical scale is "
             "schematic.", ha="center", fontsize=6.0, color=GRY)
    fig.tight_layout()
    fig.savefig(FIG / "fig2_stack.pdf"); plt.close(fig)
    return "fig2_stack.pdf"


# ============================================================ FIG 3 loss model
def fig3():
    e = {r["case"]: r for r in rd("final_etm_replay.csv")}
    z1, z2 = e["Z1"], e["Z2"]
    fig = plt.figure(figsize=(7.16, 2.30))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.12, 1.0], wspace=0.40)
    a, b, c = (fig.add_subplot(gs[i]) for i in range(3))

    # (a) per-cell converter mechanisms
    M = 49
    mech = [("LS conduction", "L_P_switch_ls_conduction", "#0072B2"),
            ("inductor DCR", "L_P_inductor_DCR", "#009E73"),
            ("HS conduction", "L_P_switch_hs_conduction", "#56B4E9"),
            ("switching", "L_P_switching_hard", "#D55E00"),
            ("gate drive", "L_P_gate", "#E69F00"),
            (r"$C_{\rm oss}$", "L_P_Coss", "#CC79A7"),
            ("cap ESR", "L_P_cap_ESR", "#5A5A5A")]
    v = [float(z1[k]) / M * 1e3 for _, k, _ in mech]
    y = np.arange(len(mech))[::-1]
    a.barh(y, v, 0.64, color=[c_ for _, _, c_ in mech], zorder=3)
    for yy, vv in zip(y, v):
        a.text(vv * 1.06, yy, f"{vv:.0f}", va="center", fontsize=5.9)
    a.set_yticks(y); a.set_yticklabels([m[0] for m in mech], fontsize=6.2)
    a.set_xscale("log"); a.set_xlim(4, 5200)
    a.set_xlabel("loss per cell (mW)")
    a.grid(axis="y", visible=False)
    panel(a, "(a)", -0.52)
    a.set_title("converter mechanisms", fontsize=7.2)

    # (b) system loss breakdown, stacked
    groups = [("semiconductor", ["L_P_switch_hs_conduction", "L_P_switch_ls_conduction",
                                 "L_P_switching_hard", "L_P_gate", "L_P_Coss"], BLU),
              ("inductor", ["L_P_inductor_DCR"], GRN),
              ("capacitor", ["L_P_cap_ESR"], PUR),
              ("intra-cell metal", ["L_P_intraVR_metal", "L_P_intraVR_vertical"], ORA),
              ("through-substrate", ["L_P_TSV"], VER),
              ("bumps + pkg RDL", ["L_P_bumps", "L_P_pkg_RDL"], GRY)]
    xs = np.arange(2)
    bot = np.zeros(2)
    for lab, keys, col in groups:
        val = np.array([sum(max(float(r[k]), 0.0) for k in keys) for r in (z1, z2)])
        b.bar(xs, val, 0.52, bottom=bot, color=col, label=lab, zorder=3, lw=.4, ec="w")
        bot += val
    for i, r in enumerate((z1, z2)):
        b.text(i, bot[i] + 2.0, f"{float(r['P_total_electronics_w']):.1f} W",
               ha="center", fontsize=6.4, weight="bold")
    b.set_xticks(xs); b.set_xticklabels(["Z1\nembedded", "Z2\nbackside"], fontsize=6.4)
    b.set_ylabel("electronics-scope loss (W)")
    b.set_ylim(0, 152)
    b.grid(axis="x", visible=False)
    b.legend(fontsize=5.6, loc="upper center", ncol=3, bbox_to_anchor=(0.5, -0.19),
             handlelength=0.9, columnspacing=0.7, labelspacing=0.22, handletextpad=0.4)
    panel(b, "(b)")
    b.set_title("system loss breakdown", fontsize=7.2)

    # (c) rail-dependent vertical loss
    segs = [("input bus\n48 V", 0.478, BLU), (r"HS$\to C_f$" + "\n16 V", 1.015, "#56B4E9"),
            (r"HS$\to$LS" + "\n16 V", 1.435, "#56B4E9"),
            (r"SW$\to L$" + "\n1 V", 20.408, VER)]
    x = np.arange(len(segs))
    c.bar(x, [s[1] for s in segs], 0.56, color=[s[2] for s in segs], zorder=3)
    for i, s in enumerate(segs):
        c.text(i, s[1] * 1.18, f"{s[1]:.2f} A", ha="center", fontsize=5.9)
    c.set_yscale("log")
    c.set_xticks(x); c.set_xticklabels([s[0] for s in segs], fontsize=5.8)
    c.set_ylabel("segment current (A)")
    c.grid(axis="x", visible=False)
    c.set_ylim(0.2, 260)
    c.text(1.5, 95, "same TSV field:\n48 V " + r"$\to\ \approx$0 W" + "\n1 V "
           + r"$\to$ 0.991 W", fontsize=5.9, color=VER, ha="center", va="center",
           bbox=dict(boxstyle="round,pad=0.3", fc="w", ec=VER, lw=.6), linespacing=1.3)
    panel(c, "(c)")
    c.set_title("rail-dependent vertical loss", fontsize=7.2)
    fig.savefig(FIG / "fig3_loss.pdf"); plt.close(fig)
    return "fig3_loss.pdf"


# ============================================================ FIG 4 validation
def fig5():
    fig, ax = plt.subplots(1, 4, figsize=(7.16, 1.92))
    a, b, c, d = ax

    # (a) parity: framework against MOOSE
    rdl = rd("multilayer_rdl_validation.csv", R / "results" / "phase0e")
    xr = [float(r["P_moose_w"]) for r in rdl]
    yr = [float(r["P_compact_w"]) for r in rdl]
    tr_err = [0.25, 0.38, 0.51, 0.66, 0.73]              # five transition geometries
    lo, hi = 0.5, 12.0
    a.plot([lo, hi], [lo, hi], color=GRY, lw=.7, ls="--", zorder=1)
    a.fill_between([lo, hi], [lo * .98, hi * .98], [lo * 1.02, hi * 1.02],
                   color=GRN, alpha=.14, zorder=0, label=r"$\pm2\,\%$")
    a.plot(xr, yr, "o", mfc=BLU, mec="k", mew=.4, ms=4.2, zorder=3,
           label="RDL plane, 3 cases")
    a.set_xscale("log"); a.set_yscale("log"); a.set_xlim(lo, hi); a.set_ylim(lo, hi)
    a.set_xlabel("MOOSE (W)"); a.set_ylabel("framework (W)")
    a.legend(loc="upper left", fontsize=5.6, handlelength=1.1)
    panel(a, "(a)", -0.34, 1.13)
    a.set_title("RDL plane power", fontsize=7.0)

    # (b) error bars across electrical checks
    lbl = ["RDL", "transition", "uniform", "spreading"]
    lows = [0.45, 0.25, 0.0, 0.9]
    highs = [1.10, 0.73, 0.0, 0.9]
    xs = np.arange(len(lbl))
    b.bar(xs, highs, 0.5, color=[BLU, GRN, GRY, ORA], zorder=3)
    for i, (l_, h_) in enumerate(zip(lows, highs)):
        b.plot([i, i], [l_, h_], color="k", lw=.8, zorder=4)
        b.text(i, h_ + 0.13, (f"{l_:.2f}–{h_:.2f}" if l_ != h_ else
                              ("exact" if h_ == 0 else f"{h_:.1f}")),
               ha="center", fontsize=5.6)
    b.axhline(2.0, color=VER, lw=.8, ls="--")
    b.text(3.45, 2.12, "2 % band", fontsize=5.6, color=VER, ha="right")
    b.set_xticks(xs); b.set_xticklabels(lbl, fontsize=5.9, rotation=30, ha="right")
    b.set_ylabel("deviation (%)"); b.set_ylim(0, 2.65)
    b.grid(axis="x", visible=False)
    panel(b, "(b)", -0.34, 1.13)
    b.set_title("electrical checks", fontsize=7.0)

    # (c) cooling solid side
    cl = ["production\ngeometry", "short thick fin\n(off-envelope)"]
    cv = [3.78, 10.11]
    c.bar([0, 1], cv, 0.5, color=[GRN, VER], zorder=3)
    c.text(0.0, 1.70, f"{cv[0]:.2f} %", ha="center", fontsize=5.9, color="w")
    c.text(1.0, 10.46, f"{cv[1]:.2f} %", ha="center", fontsize=5.9)
    c.axhline(5.0, color=GRY, lw=.8, ls="--")
    c.text(-0.42, 5.30, "acceptance", fontsize=5.6, color=GRY, ha="left")
    c.text(1.0, 11.45, "REJECTED", fontsize=5.9, color=VER, ha="center", weight="bold")
    c.text(0.0, 4.30, "ACCEPTED", fontsize=5.9, color=GRN, ha="center", weight="bold")
    c.set_xticks([0, 1]); c.set_xticklabels(cl, fontsize=5.7)
    c.set_ylabel("deviation from explicit fins (%)"); c.set_ylim(0, 12.6)
    c.grid(axis="x", visible=False)
    panel(c, "(c)", -0.44, 1.13)
    c.set_title("cooling solid side", fontsize=7.0)

    # (d) local metric convergence
    mesh = rd("local_metric_convergence.csv", R / "results" / "phase0i")
    seen, m = set(), []
    for r in mesh:
        if (re.match(r"^m\d+_\d+$", r["tag"] or "") and r["tag"] not in seen
                and r["excl_frac"] == "1.0" and r["cetol"] == "0.01"):
            seen.add(r["tag"]); m.append(r)
    ne = [int(r["n_elem"]) for r in m]
    dv = [float(r["d_eps_in_stab"]) * 1e3 for r in m]
    d.plot(ne, dv, "-o", color=BLU, ms=4.0, mec="k", mew=.4, zorder=3)
    for x, y, r in zip(ne, dv, m):
        d.annotate(f"{r['n_xy']}$\\times${r['n_z']}", (x, y), textcoords="offset points",
                   xytext=(0, 7), ha="center", fontsize=5.6)
    drift = 100 * abs(dv[-1] - dv[-2]) / dv[-1]
    d.axhspan(dv[-1] * .99, dv[-1] * 1.01, color=GRN, alpha=.15, zorder=0)
    d.text(ne[0] * 1.03, dv[-1] * .9845, f"{drift:.1f} % on the finest pair",
           fontsize=5.7, color=GRN)
    d.set_xscale("log"); d.set_ylim(dv[-1] * .975, dv[0] * 1.024)
    d.set_xlim(ne[0] * 0.78, ne[-1] * 1.30)
    d.set_xticks(ne); d.set_xticklabels([f"{n:,}" for n in ne], fontsize=6.0)
    d.set_xticks([], minor=True)
    d.set_xlabel("solder elements")
    d.set_ylabel(r"$\Delta\varepsilon_{\rm in}$ / cycle ($\times10^{-3}$)")
    panel(d, "(d)", -0.40, 1.13)
    d.set_title("local metric convergence", fontsize=7.0)
    fig.tight_layout(w_pad=1.4)
    fig.savefig(FIG / "fig5_validation.pdf"); plt.close(fig)
    return "fig5_validation.pdf"


# ============================================================ FIG 5 assembly state
def fig6():
    import collections
    rows = rd("footprint_board_envelope.csv", R / "results" / "phase0g")
    g = collections.defaultdict(dict)
    for r in rows:
        if r["restraint"] == "BC_B":          # withdrawn clamp model, excluded
            continue
        key = "free" if r["board_case"] == "-" else r["board_case"]
        g[key][float(r["hvr_area_mm2"])] = float(r["die_warpage_pv_um"])
    order = ["free", "compliant", "fr4_1p6mm", "fr4_2p4mm", "fr4_3p2mm",
             "stiff_metal_backed"]
    nice = {"free": "free", "compliant": "compliant", "fr4_1p6mm": "FR4\n1.6 mm",
            "fr4_2p4mm": "FR4\n2.4 mm", "fr4_3p2mm": "FR4\n3.2 mm",
            "stiff_metal_backed": "metal-\nbacked"}
    delta = [100 * (list(sorted(g[k].items()))[1][1] - list(sorted(g[k].items()))[0][1])
             / list(sorted(g[k].items()))[0][1] for k in order]
    fig = plt.figure(figsize=(7.16, 2.22))
    gs = fig.add_gridspec(1, 5, width_ratios=[1.0, 1.0, 0.075, 0.30, 1.46],
                          wspace=0.28, left=0.055, right=0.985, bottom=0.21, top=0.88)
    fa, fb = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
    cax, ax = fig.add_subplot(gs[2]), fig.add_subplot(gs[4])

    # (a)(b) die-surface out-of-plane displacement of the frozen pair, shared scale
    F = {}
    for c in ("Z1", "Z2"):
        rr = rd(f"die_surface_field_{c}.csv")
        F[c] = (np.array([float(r["x_mm"]) for r in rr]),
                np.array([float(r["y_mm"]) for r in rr]),
                np.array([float(r["uz_um"]) for r in rr]))
    allz = np.concatenate([F[c][2] for c in F])
    lo, hi = allz.min(), allz.max()
    lv = np.linspace(lo, hi, 13)
    e = {r["case"]: r for r in rd("final_etm_replay.csv")}
    for a, c, ttl in ((fa, "Z1", "(a)  Z1 embedded"), (fb, "Z2", "(b)  Z2 backside")):
        x, y, z = F[c]
        nx = int(round(np.sqrt(len(x))))
        X, Y, Z = (v.reshape(nx, nx) for v in
                   (x[np.lexsort((x, y))], y[np.lexsort((x, y))], z[np.lexsort((x, y))]))
        cf = a.contourf(X, Y, Z, levels=lv, cmap="RdBu_r", extend="neither")
        a.contour(X, Y, Z, levels=lv[::3], colors="k", linewidths=.28)
        a.set_aspect("equal")
        a.set_xlabel("$x$ (mm)", fontsize=6.6); a.grid(False)
        if c == "Z1":
            a.set_ylabel("$y$ (mm)", fontsize=6.6)
        else:
            a.set_yticklabels([])
        a.tick_params(labelsize=6.0)
        a.set_title(ttl, fontsize=7.0, loc="left")
        a.text(0.5, -0.30, f"P--V = {float(e[c]['die_warpage_pv_um']):.2f} µm",
               transform=a.transAxes, ha="center", fontsize=6.3)
    cb = fig.colorbar(cf, cax=cax)
    cb.ax.set_title(r"$u_z$ (µm)", fontsize=6.4, pad=3.5)
    cb.set_ticks(np.arange(-70, -25, 10))
    cb.ax.tick_params(labelsize=5.9, length=2.0)
    cb.outline.set_linewidth(.5)

    cols = [VER] + [GRN] * 5
    hatch = ["//"] + [""] * 5
    ax.bar(range(len(order)), delta, 0.6, color=cols, hatch=hatch, zorder=3,
           ec="k", lw=.45)
    for i, d_ in enumerate(delta):
        ax.text(i, d_ + (1.7 if d_ > 0 else -3.0), f"{d_:+.1f}", ha="center",
                fontsize=6.0, color=cols[i])
    ax.axhline(0, color="k", lw=.7)
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([nice[k] for k in order], fontsize=6.0)
    ax.set_ylabel("change in die warpage for a\nlarger converter footprint (%)")
    ax.set_ylim(-37, 42)
    ax.grid(axis="x", visible=False)
    ax.text(0.40, 40.5, "free package:\nwarpage increases", fontsize=6.0, color=VER,
            linespacing=1.25, ha="left", va="top")
    ax.text(5.45, 40.5, "explicitly mounted:\nwarpage decreases", fontsize=6.0, color=GRN,
            ha="right", linespacing=1.25, va="top")
    ax.set_title("(c)  assembly state", fontsize=7.0, loc="left")
    fig.savefig(FIG / "fig6_assembly.pdf"); plt.close(fig)
    return "fig6_assembly.pdf"


# ============================================================ FIG 6 sensitivity
def fig7():
    steps = [("baseline\ncoupled", 1.3225), ("production\ncoupling", 1.2552),
             ("corrected\nmaterials", 1.1942), ("interconnect\nrepair", 1.1943),
             ("topology +\nrepartition", 1.1947)]
    val = [s[1] for s in steps]
    fig, ax = plt.subplots(figsize=(3.46, 2.15))
    x = np.arange(len(val))
    ax.plot(x, val, "-o", color=BLU, ms=4.2, mec="k", mew=.4, zorder=3)
    ax.axhline(1.0, color=VER, lw=.8, ls="--")
    ax.text(len(val) - 1, 1.006, "ordering reversal", color=VER, ha="right",
            va="bottom", fontsize=6.0)
    ax.fill_between([-0.45, len(val) - 0.55], 1.190, 1.200, color=GRN, alpha=.15, zorder=0)
    ax.text(0.03, 1.209, "converged band, $\\pm$0.05 %", color=GRN, fontsize=6.0)
    for i, v in enumerate(val):
        ax.annotate(f"{v:.4f}", (i, v), textcoords="offset points",
                    xytext=(0, 8 if i < 2 else -12), ha="center", fontsize=6.0)
    ax.set_xticks(x); ax.set_xticklabels([s[0] for s in steps], fontsize=5.9)
    ax.set_xlim(-0.45, len(val) - 0.55); ax.set_ylim(0.985, 1.375)
    ax.set_ylabel(r"$D_u=\Delta u_{\rm c}^{\rm Z1}/\Delta u_{\rm c}^{\rm Z2}$")
    ax.grid(axis="x", visible=False)
    fig.savefig(FIG / "fig7_sensitivity.pdf"); plt.close(fig)
    return "fig7_sensitivity.pdf"


# ============================================================ FIG 7 realizability
def fig4():
    feas = rd("routing_feasibility.csv")
    base = {r["net"]: r for r in feas
            if r["candidate"] == "baseline_T1" and r["pitch_um"] == "150.0"}
    rep = {r["net"]: r for r in feas
           if r["candidate"] == "repartition_C1" and r["pitch_um"] == "150.0"}
    cp = [r for r in rd("conductor_plane_topology.csv")
          if r["template"] == "T1_EMBEDDED_4LAYER" and r["net"] == "ls_to_L"]
    fig = plt.figure(figsize=(7.16, 2.45))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.02, 1.05, 1.18], wspace=0.30)
    a, b, c = (fig.add_subplot(gs[i]) for i in range(3))

    # (a) conductor-plane sequence
    nogrid(a)
    col = {"TERMINAL PLANE": "#34495e", "CONDUCTOR PLANE": BLU,
           "DIELECTRIC REGION": "#DCDCDC"}
    for r in cp:
        z0, z1_ = float(r["z_start_um"]), float(r["z_end_um"])
        h = z1_ - z0
        if h < 1e-9:
            a.plot([0.10, 0.62], [z0, z0], color=col["TERMINAL PLANE"], lw=2.2, zorder=6)
            lab = "gan_ls" if z0 < 1350 else "inductor"
            a.text(0.66, z0 + (-7.0 if z0 < 1350 else 7.0), f"{lab} terminal face",
                   va="center", fontsize=5.7, color="#34495e")
            continue
        a.add_patch(Rectangle((0.10, z0), 0.52, h, fc=col[r["kind"]], ec="k", lw=.45))
        if r["needs_via"] == "True":
            a.add_patch(Rectangle((0.31, z0), 0.10, h, fc="#B8860B", ec="k", lw=.45,
                                  zorder=4))
            a.text(0.66, z0 + h / 2, f"flying-capacitor tier, {h:.0f} µm\n"
                   "ONE build-up via level", va="center", fontsize=5.7, color="#7D6608")
        else:
            a.text(0.66, z0 + h / 2, "interlayer RDL —\ncapture plane", va="center",
                   fontsize=5.7, color=BLU)
    a.set_xlim(0.0, 2.15); a.set_ylim(1286, 1436)
    a.set_yticks([1300, 1350, 1400]); a.set_yticklabels(["1300", "1350", "1400"],
                                                        fontsize=6.2)
    a.tick_params(left=True, labelleft=True, length=2.2)
    for sp in ("left",):
        a.spines[sp].set_visible(True); a.spines[sp].set_linewidth(.6)
    a.set_ylabel(r"$z$ (µm)", fontsize=7.0)
    a.set_title(r"(a)  conductor planes, SW$\to L$", fontsize=7.0, loc="left")

    # (b) tier order before / after
    nogrid(b)
    for xoff, tiers in ((0.20, ["gan_hs", "gan_ls", "cap_fly", "ind"]),
                        (1.62, ["gan_hs", "cap_fly", "gan_ls", "ind"])):
        _cell(b, xoff, 0.92, tiers)
    b.add_patch(Rectangle((0.20, 1301), 0.92, 120, fc="none", ec=VER, lw=1.5, zorder=7))
    b.plot([1.56, 2.60], [1416, 1416], color=GRN, lw=1.9, solid_capstyle="butt", zorder=7)
    b.text(0.66, 2020, "reference", fontsize=6.4, ha="center")
    b.text(2.08, 2020, "repartitioned", fontsize=6.4, ha="center")
    b.text(0.66, -110, r"SW$\to L$ crosses" + "\n" + r"the 100 µm $C_f$ tier",
           ha="center", va="top", fontsize=5.8, color=VER, linespacing=1.25)
    b.text(2.08, -110, r"SW$\to L$ is a 10 µm" + "\n" + "adjacent-tier RDL step",
           ha="center", va="top", fontsize=5.8, color=GRN, linespacing=1.25)
    b.set_xlim(-0.30, 2.78); b.set_ylim(-620, 2150)
    b.set_yticks([0, 500, 1000, 1500, 1921])
    b.set_yticklabels(["0", "500", "1000", "1500", "1921"], fontsize=6.2)
    b.tick_params(left=True, labelleft=True, length=2.2)
    b.spines["left"].set_visible(True); b.spines["left"].set_linewidth(.6)
    b.spines["left"].set_bounds(0, 1921)
    b.set_ylabel(r"$z$ (µm)", fontsize=7.0)
    b.set_title("(b)  component tier order", fontsize=7.0, loc="left")

    # (c) aspect ratio per net
    nets = ["ls_to_L", "hs_to_ls", "hs_to_cf"]
    show = {"ls_to_L": r"SW$\to L$", "hs_to_ls": r"HS$\to$LS", "hs_to_cf": r"HS$\to C_f$"}
    w, xs = 0.34, np.arange(3)
    ab = [float(base[n]["AR_worst"]) for n in nets]
    ar = [float(rep[n]["AR_worst"]) for n in nets]
    c.bar(xs - w / 2, ab, w, color=VER, zorder=3, label="reference", ec="k", lw=.4)
    c.bar(xs + w / 2, ar, w, color=GRN, zorder=3, label="repartitioned", ec="k", lw=.4)
    for i, (p_, q_) in enumerate(zip(ab, ar)):
        bb = dict(boxstyle="square,pad=0.05", fc="w", ec="none")
        c.text(i - w / 2, p_ * 1.36, f"{p_:.2f}", ha="center", fontsize=5.9, color=VER,
               bbox=bb, zorder=6)
        c.text(i + w / 2, q_ * 1.36, f"{q_:.2f}", ha="center", fontsize=5.9, color=GRN,
               bbox=bb, zorder=6)
    c.axhline(1.0, color=GRY, lw=.8, ls="--", zorder=1)
    c.text(2.47, 1.10, "AR = 1", fontsize=5.9, color=GRY, ha="right")

    c.set_yscale("log"); c.set_ylim(0.045, 16)
    c.set_xticks(xs); c.set_xticklabels([show[n] for n in nets], fontsize=6.2)
    c.set_ylabel("worst via aspect ratio")
    c.grid(axis="x", visible=False)
    lg = c.legend(fontsize=5.9, loc="upper left", handlelength=1.0,
                  title="150 µm microvia pitch")
    lg.get_title().set_fontsize(5.7)
    c.set_title("(c)  vertical-interconnect aspect ratio", fontsize=7.0, loc="left")
    fig.savefig(FIG / "fig4_realizability.pdf"); plt.close(fig)
    return "fig4_realizability.pdf"


# ============================================================ FIG 8 final + cost
def fig8():
    e = {r["case"]: r for r in rd("final_etm_replay.csv")}
    z1, z2 = e["Z1"], e["Z2"]
    d = float(z1["response_driver_um"]) / float(z2["response_driver_um"])
    # the local submodel result: a different quantity from the driver, so its own panel
    lr = {r["case"]: r for r in rd("final_local_response.csv")}
    for c in ("Z1", "Z2"):
        e[c]["d_eps_in_stab"] = lr[c]["d_eps_in_stab"]
    z1, z2 = e["Z1"], e["Z2"]
    d_eps = float(z1["d_eps_in_stab"]) / float(z2["d_eps_in_stab"])
    fig = plt.figure(figsize=(7.16, 1.95))
    gs = fig.add_gridspec(1, 6, width_ratios=[1, 1, 1, 1, 1, 1.72])
    ax = [fig.add_subplot(gs[i]) for i in range(6)]
    spec = [("(a)", r"$P_{\rm elec}$ (W)", "P_total_electronics_w", "%.1f", 0.46),
            ("(b)", r"$T_{\max}$ ($^\circ$C)", "T_max_C", "%.2f", 0.82),
            ("(c)", "warpage (µm)", "die_warpage_pv_um", "%.2f", 0.46),
            ("(d)", r"$\Delta u_{\rm c}$ (µm)", "response_driver_um", "%.4f", 1.05),
            ("(e)", r"$\Delta\varepsilon_{\rm in}$ ($10^{-2}$)",
             "d_eps_in_stab", "%.4f", 1.05)]
    for k, (tag, ttl, key, fmt, head) in enumerate(spec):
        a = ax[k]
        sc = 1e2 if key == "d_eps_in_stab" else 1.0
        v = [float(z1[key]) * sc, float(z2[key]) * sc]
        a.bar([0, 1], v, 0.56, color=[BLU, VER], zorder=3, ec="k", lw=.4)
        lo, hi = min(v), max(v); span = hi - lo
        a.set_ylim(lo - 0.34 * span, hi + head * span)
        for i, vv in enumerate(v):
            a.text(i, vv + 0.045 * span, fmt % vv, ha="center", va="bottom", fontsize=6.2)
        a.set_xticks([0, 1]); a.set_xticklabels(["Z1", "Z2"], fontsize=6.4)
        a.set_title(f"{tag} {ttl}", fontsize=6.7, loc="left")
        a.grid(axis="x", visible=False)
        a.tick_params(labelsize=6.0)
        for dy in (0.008, 0.030):          # truncated-ordinate break glyph
            a.plot([-0.023, 0.023], [dy, dy + 0.026], transform=a.transAxes,
                   color="k", lw=.7, clip_on=False, zorder=9)
    dT = float(z2["T_max_C"]) - float(z1["T_max_C"])
    ax[1].text(0.5, 0.975, f"$+${dT:.2f} K", transform=ax[1].transAxes, ha="center",
               va="top", fontsize=6.0, color=VER,
               bbox=dict(boxstyle="round,pad=0.16", fc="w", ec=VER, lw=.45))
    pct = 100 * (float(z1["response_driver_um"]) - float(z2["response_driver_um"])) \
        / float(z1["response_driver_um"])
    ax[3].text(0.5, 0.975, f"$-${pct:.1f} %\n$D_u$ {d:.4f}", transform=ax[3].transAxes,
               ha="center", va="top", fontsize=5.8, color=GRY, linespacing=1.2,
               bbox=dict(boxstyle="round,pad=0.16", fc="w", ec=GRY, lw=.45))
    pe = 100 * (float(z1["d_eps_in_stab"]) - float(z2["d_eps_in_stab"])) \
        / float(z1["d_eps_in_stab"])
    ax[4].text(0.5, 0.975, f"$-${pe:.1f} %\n$D_\\varepsilon$ {d_eps:.4f}",
               transform=ax[4].transAxes, ha="center", va="top", fontsize=5.8, color=GRN,
               linespacing=1.2,
               bbox=dict(boxstyle="round,pad=0.16", fc="w", ec=GRN, lw=.45))
    # (e) cost
    a = ax[5]
    rows = rd("runtime_benchmark.csv")
    t = {r["stage"].split(" (")[0]: float(r["wall_s"]) for r in rows}
    lbl = ["converter\nsynthesis", "PPDN +\nrouting", "cooling\ncorrelation",
           "full ETM\nZ1", "full ETM\nZ2"]
    val = [t["converter synthesis"], t["rail-aware PPDN + intra-VR routing"],
           t["cooling boundary"],
           [float(r["wall_s"]) for r in rows if r["case"] == "Z1"][0],
           [float(r["wall_s"]) for r in rows if r["case"] == "Z2"][0]]
    cols = [GRY, GRY, GRY, BLU, VER]
    y = np.arange(len(lbl))[::-1]
    a.barh(y, val, 0.6, color=cols, zorder=3, ec="k", lw=.4)
    for yy, vv in zip(y, val):
        a.text(vv * 1.9, yy, (f"{vv*1e3:.1f} ms" if vv < 1 else f"{vv:.1f} s"),
               va="center", fontsize=5.8)
    a.set_yticks(y); a.set_yticklabels(lbl, fontsize=6.0)
    a.set_ylim(-0.62, len(lbl) - 0.38)
    a.set_xscale("log"); a.set_xlim(4e-5, 4e4)
    a.set_xticks([1e-4, 1e-2, 1e0, 1e2])
    a.set_xlabel("wall time (s), 48 cores")
    a.grid(axis="y", visible=False)
    a.set_title("(f) computational cost", fontsize=6.7, loc="left")
    fig.tight_layout(w_pad=1.1)
    fig.savefig(FIG / "fig8_final.pdf"); plt.close(fig)
    return "fig8_final.pdf"


def main() -> int:
    for f in (fig1, fig2, fig3, fig4, fig5, fig6, fig7, fig8):
        print("  wrote figs/" + f())
    return 0


if __name__ == "__main__":
    sys.exit(main())
