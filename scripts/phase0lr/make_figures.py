#!/usr/bin/env python3
"""Phase-0L-R figures FIG-0LR-A .. FIG-0LR-G."""
from __future__ import annotations
import csv, math, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle, FancyBboxPatch, FancyArrowPatch

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0lr"
for d in ("phase0i", "phase0lr"):
    sys.path.insert(0, str(R / "scripts" / d))
import solder_model as sm                                                   # noqa: E402
from candidate_families import anand_rate, norton_m1                        # noqa: E402

plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": .3,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
C = {"z1": "#1565c0", "z2": "#1b5e20", "grey": "#9e9e9e", "bad": "#c62828",
     "warn": "#ef6c00", "ok": "#2e7d32", "ink": "#37474f", "purp": "#6a1b9a", "old": "#8d6e63"}
CLOSED, COND, OPEN = "#2e7d32", "#ef6c00", "#c62828"
rows = lambda p: list(csv.DictReader(open(OUT / p)))
F = lambda r, k: float(r[k])
S_LO, S_HI = 7.51, 15.92


def fig_A():
    h = rows("z1_z2_cycle_histories.csv")
    fig, ax = plt.subplots(4, 1, figsize=(10.4, 10.2), sharex=True)
    for arch, col in (("Z1", C["z1"]), ("Z2", C["z2"])):
        s = sorted([r for r in h if r["arch"] == arch], key=lambda r: F(r, "t_frac"))
        x = [F(r, "t_frac") for r in s]
        ax[0].plot(x, [F(r, "T_C") for r in s], "-", color=col, lw=1.6, label=arch)
        ax[1].plot(x, [F(r, "sigma_vm_MPa") for r in s], "-", color=col, lw=1.6, label=arch)
        ax[2].plot(x, [F(r, "hydrostatic_MPa") for r in s], "-", color=col, lw=1.6, label=arch)
        tot = F(s[-1], "peeq_accum_in_cycle")
        ax[3].plot(x, [100*F(r, "peeq_accum_in_cycle")/tot for r in s], "-", color=col, lw=1.8,
                   label=f"{arch}  (total {tot:.4g})")
    ax[1].axhspan(S_LO, S_HI, color=C["ok"], alpha=.30, zorder=0)
    ax[1].text(0.02, 22, "creep calibration window 7.51-15.92 MPa", fontsize=7.5,
               color="#1b5e20")
    ax[1].axhline(100, color=C["bad"], ls=":", lw=1.2)
    ax[1].text(0.80, 104, "100 MPa", fontsize=7.5, color=C["bad"])
    for a, lab in zip(ax, ("temperature (°C)", "Syed-layer mean σ$_{vm}$ (MPa)",
                           "hydrostatic stress (MPa)", "cumulative % of cycle damage")):
        a.set_ylabel(lab, fontsize=8.5); a.legend(fontsize=7.5, loc="best")
    ax[3].set_xlabel("fraction through the stabilised cycle (heat-up, hot dwell, cool, cold dwell)")
    ax[0].set_title("FIG-0LR-A   Z1 and Z2 through one stabilised cycle, aligned.\n"
                    "Same cycle shape and same damage timing; Z2's advantage is a lower PEAK.",
                    fontsize=10)
    fig.savefig(OUT / "FIG_0LR_A_histories.png"); plt.close(fig)
    print("  FIG-0LR-A")


def fig_B():
    d = rows("high_stress_damage_fraction.csv")
    labs = [r["stress_bin_MPa"] for r in d if r["arch"] == "Z1"]
    x = np.arange(len(labs))
    fig, ax = plt.subplots(figsize=(10.0, 4.8))
    for k, (arch, col) in enumerate((("Z1", C["z1"]), ("Z2", C["z2"]))):
        v = [100*F(r, "damage_fraction") for r in d if r["arch"] == arch]
        ax.bar(x + (k - .5)*.38, v, .36, color=col, label=arch)
        for xi, vi in zip(x + (k - .5)*.38, v):
            ax.text(xi, vi + .5, f"{vi:.1f}", ha="center", fontsize=7)
    ax.axvspan(-0.5, 0.5, color=C["ok"], alpha=.25, zorder=0)
    ax.text(0, 30, "inside the\ncalibration\nwindow", ha="center", fontsize=8, color="#1b5e20")
    ax.set_xticks(x); ax.set_xticklabels(labs)
    ax.set_xlabel("von Mises stress bin (MPa)"); ax.set_ylabel("% of per-cycle damage")
    ax.legend()
    ax.set_title("FIG-0LR-B   Where each architecture's damage is generated.\n"
                 "99.8 % of it lies above the window the creep law was fitted in, for both.",
                 fontsize=10)
    fig.savefig(OUT / "FIG_0LR_B_damage_bins.png"); plt.close(fig)
    print("  FIG-0LR-B")


def fig_C():
    dist = {r["arch"]: r for r in rows("damage_weighted_stress_distribution.csv")}
    fig, ax = plt.subplots(figsize=(10.6, 6.0))
    ax.add_patch(Rectangle((45, S_LO), 105, S_HI - S_LO, fc=CLOSED, alpha=.35, ec=CLOSED,
                           lw=2.2, zorder=4))
    for (T, s, _e) in sm.CREEP_DATA:
        ax.plot(T, s, "o", ms=5, color="#1b5e20", zorder=6)
    ax.annotate("THE ONLY CREEP-RATE DATA\n45-150 °C, 7.51-15.92 MPa\nalloy Sn3.9Ag0.6Cu",
                (97, 10.9), ha="center", fontsize=8, zorder=7,
                bbox=dict(fc="white", ec=CLOSED, lw=1, alpha=.94, pad=3))
    ax.add_patch(Rectangle((25, 12), 100, 40 - 12, fc="#1565c0", alpha=.14, ec="#1565c0",
                           lw=1.6, ls="--", zorder=2))
    ax.annotate("SAC305 Anand (Yamin/Motalab)\n25-125 °C, tensile flow stresses,\n"
                "strain rates 1e-5…1e-3 /s — RIGHT ALLOY,\nwrong rate regime",
                (27, 30), fontsize=7.6, color="#1565c0", zorder=7, va="center")
    for arch, col in (("Z1", C["z1"]), ("Z2", C["z2"])):
        r = dist[arch]
        lo, hi = F(r, "sigma_vm_p10_MPa"), F(r, "sigma_vm_p90_MPa")
        med = F(r, "sigma_vm_median_MPa")
        y0 = 25.0 if arch == "Z1" else 25.0
        ax.plot([F(r, "T_min_C"), F(r, "T_max_C")], [med, med], "-", color=col, lw=3,
                zorder=8, label=f"{arch} damage-weighted median {med:.0f} MPa")
        ax.add_patch(Rectangle((F(r, "T_min_C"), lo), F(r, "T_max_C") - F(r, "T_min_C"),
                               hi - lo, fc=col, alpha=.15, ec=col, lw=1.4, zorder=5))
    ax.set_yscale("log"); ax.set_ylim(4, 400); ax.set_xlim(15, 160)
    ax.set_xlabel("temperature (°C)"); ax.set_ylabel("von Mises stress (MPa)")
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(alpha=.3, which="both")
    ax.set_title("FIG-0LR-C   Source-data domains against where the package actually operates.\n"
                 "Shaded bands are the p10-p90 damage-weighted stress range of each architecture.",
                 fontsize=10)
    fig.savefig(OUT / "FIG_0LR_C_domain.png"); plt.close(fig)
    print("  FIG-0LR-C")


def fig_D():
    d = rows("numerics_vs_constitutive_decomposition.csv")
    g = {(r["constitutive_model"], r["integration_control"]): r for r in d}
    seq = [("M0_COARSE", "DEFAULT", "incumbent model\nold integration\n(Phase 0K-R)", C["old"]),
           ("M0_COARSE", "TIGHT", "SAME model\nresolved integration", C["warn"]),
           ("M1", "TIGHT", "corrected model\nresolved integration", C["z1"])]
    have = [(m, c, lab, col) for m, c, lab, col in seq if (m, c) in g]
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.4))
    for ax, key, lab, fmt in ((axes[0], "D", "D  (law discrimination)", "{:.4f}"),
                              (axes[1], "n_per_cell", "specimens per cell", "{:.0f}"),
                              (axes[2], "Z2_Z1_strain", "Z2/Z1 strain ratio", "{:.4f}")):
        v = [float(g[(m, c)][key]) for m, c, _l, _k in have]
        x = np.arange(len(v))
        ax.bar(x, v, .55, color=[k for _m, _c, _l, k in have])
        for xi, vi in zip(x, v):
            ax.text(xi, vi * 1.02, fmt.format(vi), ha="center", fontsize=8.5)
        ax.set_xticks(x); ax.set_xticklabels([l for _m, _c, l, _k in have], fontsize=7)
        ax.set_title(lab, fontsize=9.5)
        ax.set_ylim(0, max(v) * 1.22)
        if key == "n_per_cell":
            ax.axhline(34, color=C["bad"], ls="--", lw=1.4)
            ax.text(0.02, 36, "Phase-0K-R design: 34", fontsize=7.5, color=C["bad"])
    d0 = float(g[("M0_COARSE", "DEFAULT")]["D"]); d1 = float(g[("M0_COARSE", "TIGHT")]["D"])
    d2 = float(g[("M1", "TIGHT")]["D"])
    fig.suptitle("FIG-0LR-D   One factor changed at a time. Middle bar is the SAME constitutive "
                 f"model with the integration resolved.\nOf the move in D from {d0:.4f} to "
                 f"{d2:.4f}, {100*(d1-d0)/(d2-d0):.0f} % is numerics and "
                 f"{100*(d2-d1)/(d2-d0):.0f} % is the material model.", fontsize=9.5)
    fig.savefig(OUT / "FIG_0LR_D_decomposition.png"); plt.close(fig)
    print("  FIG-0LR-D")


def fig_E():
    d = rows("model_form_robustness.csv")
    gate = rows("model_form_gate_result.csv")
    fig, ax = plt.subplots(figsize=(10.6, 5.0))
    ms = [r["model"] for r in d]
    x = np.arange(len(ms))
    for k, (key, lab, col) in enumerate((("r_strain", "creep strain", C["z1"]),
                                         ("r_energy", "inelastic energy", C["ok"]),
                                         ("r_range", "within-cycle range", C["warn"]))):
        ax.bar(x + (k - 1) * .26, [F(r, key) for r in d], .24, color=col, label=lab)
    ax.axhline(1.0, color=C["bad"], lw=1.8)
    ax.text(len(ms) - .55, 1.005, "parity — below this Z2 would be WORSE", fontsize=7.5,
            color=C["bad"], ha="right")
    for xi, r in zip(x, d):
        ax.text(xi, 0.93, r["family"], ha="center", fontsize=7.5, color=C["ink"])
    ax.set_xticks(x); ax.set_xticklabels([m.replace("_", "\n") for m in ms], fontsize=8)
    ax.set_ylabel("Z1 response / Z2 response   (>1 means Z2 is better)")
    ax.set_ylim(0.9, 1.42); ax.legend(fontsize=8, loc="upper left")
    cls = gate[0]["gate_classification"]
    ax.set_title("FIG-0LR-E   Architecture ratio under every constitutive model that could be "
                 f"integrated.\nAll 12 ratios exceed 1. Predeclared gate result: {cls} "
                 "(only two model FAMILIES, three required).", fontsize=9.5)
    fig.savefig(OUT / "FIG_0LR_E_ratios.png"); plt.close(fig)
    print("  FIG-0LR-E")


def fig_F():
    fig, ax = plt.subplots(figsize=(12.0, 6.4))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    def box(x, y, w, h, t, fc, ec, fs=7.8, bold=False):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.008,rounding_size=0.015",
                                    fc=fc, ec=ec, lw=1.6, zorder=3))
        ax.text(x + w/2, y + h/2, t, ha="center", va="center", fontsize=fs, zorder=4,
                fontweight="bold" if bold else "normal", linespacing=1.35)
    def arr(p, q, col=C["ink"], ls="-"):
        ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=12, lw=1.2,
                                     color=col, linestyle=ls, zorder=2))
    ax.text(0.25, 0.965, "Sn3.9Ag0.6Cu   (3.9 wt% Ag)", ha="center", fontsize=10.5,
            fontweight="bold", color=C["bad"])
    ax.text(0.75, 0.965, "SAC305   (3.0 wt% Ag)", ha="center", fontsize=10.5,
            fontweight="bold", color=C["ok"])
    ax.plot([0.5, 0.5], [0.02, 0.94], color=C["grey"], lw=1.4, ls="--")
    box(0.03, 0.78, 0.44, 0.12, "Xiao & Armstrong 2005\nbulk tensile CREEP, 45-150 °C,\n"
        "7.51-15.92 MPa, 1e-9…8e-7 /s", "#ffebee", C["bad"])
    box(0.53, 0.78, 0.44, 0.12, "Motalab et al.\nuniaxial TENSILE, 25-125 °C,\n"
        "1e-5…1e-3 /s", "#e8f5e9", C["ok"])
    box(0.03, 0.58, 0.20, 0.11, "Yuan 2023 T5\n19 points", "#ffebee", C["bad"])
    box(0.26, 0.58, 0.21, 0.11, "Yuan 2023 T6\nGarofalo", "#ffebee", C["bad"])
    box(0.53, 0.58, 0.20, 0.11, "Yuan 2023 T7/T9\nAnand (EINN+BI)", "#e8f5e9", C["ok"])
    box(0.76, 0.58, 0.21, 0.11, "Yamin 2025 T1\nAnand", "#e8f5e9", C["ok"])
    box(0.53, 0.40, 0.20, 0.11, "Yuan 2023 T10\nChaboche σ$_0$(T)", "#e8f5e9", C["ok"])
    arr((0.20, 0.78), (0.13, 0.695)); arr((0.30, 0.78), (0.36, 0.695))
    arr((0.70, 0.78), (0.63, 0.695)); arr((0.80, 0.78), (0.86, 0.695))
    arr((0.63, 0.58), (0.63, 0.515))
    box(0.03, 0.20, 0.44, 0.13, "CREEP HALF of the current card\nNorton A(T), n(T)  —  M1\n"
        "label: SnAgCu surrogate, NOT SAC305", "#ffcdd2", C["bad"], bold=True)
    box(0.53, 0.20, 0.44, 0.13, "YIELD HALF of the current card\n*PLASTIC σ$_y$(T)\n"
        "SAC305, but two model layers out", "#c8e6c9", C["ok"], bold=True)
    arr((0.13, 0.58), (0.20, 0.335)); arr((0.63, 0.40), (0.68, 0.335))
    ax.add_patch(FancyArrowPatch((0.47, 0.265), (0.53, 0.265), arrowstyle="<|-|>",
                                 mutation_scale=14, lw=2.0, color=C["purp"], zorder=5))
    ax.text(0.50, 0.30, "the overstress law\nSUBTRACTS one from the other", ha="center",
            fontsize=8.5, color=C["purp"], fontweight="bold", zorder=6,
            bbox=dict(fc="white", ec=C["purp"], lw=1, pad=2.5))
    ax.text(0.5, 0.075, "Phase 0L-R re-admits the Anand FAMILY on the Yamin parameterisation "
            "(right-hand branch, correct alloy)\nand rejects the Yuan EINN+BI parameterisation, "
            "which misses the only creep data by 1240x where Yamin's misses by 1.76x.",
            ha="center", fontsize=8.2, va="center",
            bbox=dict(fc="#fffde7", ec="#fbc02d", pad=4))
    ax.set_title("FIG-0LR-F   Parameter provenance. The current card straddles the dashed line.",
                 fontsize=10.5)
    fig.savefig(OUT / "FIG_0LR_F_provenance.png"); plt.close(fig)
    print("  FIG-0LR-F")


def fig_G():
    rungs = [
        ("solver implementation", CLOSED,
         "law traced in source, confirmed to 1.2e-5 over 7603 increments"),
        ("metric numerical convergence", COND,
         "STRAIN converged to 0.27 %; ENERGY moves 11-24 % with the time step"),
        ("constitutive source domain", OPEN,
         "fitted 7.51-15.92 MPa; 99.8 % of damage above it; creep alloy is Sn3.9Ag0.6Cu"),
        ("life-law mapping", COND,
         "Syed/Schubert admitted for RATIOS; constants cancel, exponents do not"),
        ("absolute calibration", OPEN, "no package-specific calibration exists; 4.1x spread"),
        ("mission criterion", OPEN, "N_required has no source anywhere in the project"),
    ]
    fig, ax = plt.subplots(figsize=(11.6, 6.0))
    ax.set_xlim(0, 1); ax.set_ylim(-0.5, len(rungs) - 0.3); ax.axis("off")
    for i, (name, col, note) in enumerate(rungs):
        y = len(rungs) - 1 - i
        ax.add_patch(FancyBboxPatch((0.06, y - 0.30), 0.36, 0.60,
                                    boxstyle="round,pad=0.006,rounding_size=0.02",
                                    fc="white", ec=col, lw=2.2, zorder=3))
        ax.add_patch(Rectangle((0.06, y - 0.30), 0.016, 0.60, fc=col, ec="none", zorder=4))
        ax.text(0.24, y, name, ha="center", va="center", fontsize=9.5, zorder=5)
        ax.text(0.45, y, note, ha="left", va="center", fontsize=8.2, color=C["ink"])
        lab = {CLOSED: "CLOSED", COND: "CONDITIONAL", OPEN: "OPEN"}[col]
        ax.text(0.035, y, lab, ha="right", va="center", fontsize=8, color=col,
                fontweight="bold")
        if i < len(rungs) - 1:
            ax.add_patch(FancyArrowPatch((0.24, y - 0.31), (0.24, y - 0.70),
                                         arrowstyle="-|>", mutation_scale=11, lw=1.2,
                                         color=C["ink"], zorder=2))
    ax.set_title("FIG-0LR-G   The reliability evidence ladder.\nEach rung depends on the one "
                 "above it; the chain is only as strong as its lowest CLOSED rung.", fontsize=10.5)
    fig.savefig(OUT / "FIG_0LR_G_ladder.png"); plt.close(fig)
    print("  FIG-0LR-G")


if __name__ == "__main__":
    for w in (sys.argv[1:] or list("ABCDEFG")):
        globals()[f"fig_{w}"]()
