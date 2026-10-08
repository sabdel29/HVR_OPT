#!/usr/bin/env python3
"""Phase-0K figures (Sec.28)."""
from __future__ import annotations
import csv, math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, Rectangle

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0k"
plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": .3,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
C = {"z1": "#1565c0", "z2": "#1b5e20", "z4": "#b71c1c", "grey": "#9e9e9e", "bad": "#c62828",
     "warn": "#ef6c00", "ok": "#2e7d32", "ink": "#37474f", "amb": "#fdd835"}
rows = lambda p: list(csv.DictReader(open(OUT / p)))
F = lambda r, k: float(r[k])
SH = {"Z1": "Z1 embedded", "Z2": "Z2 backside", "Z4": "Z4 power die"}
CC = {"Z1": C["z1"], "Z2": C["z2"], "Z4": C["z4"]}
LAWS = [("SYED_EQ14_STRAIN_POWERLAW", "Syed Eq.14 strain, power law", "-", C["ok"]),
        ("SYED_EQ16_STRAIN_SINH", "Syed Eq.16 strain, sinh", "--", C["ok"]),
        ("SYED_EQ15_ENERGY_POWERLAW", "Syed Eq.15 energy, power law", "-", C["warn"]),
        ("SYED_EQ17_ENERGY_SINH", "Syed Eq.17 energy, sinh", "--", C["warn"])]


def fig_A():
    dm = rows("g2_decision_map.csv")
    N = [F(r, "N_required") for r in dm]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10.6, 6.6), sharex=True,
                                 gridspec_kw={"height_ratios": [2.1, 1]})
    import matplotlib.lines as mlines
    for a in ("Z1", "Z2", "Z4"):
        for key, lab, ls, col in LAWS:
            v = F(dm[0], f"{a}_{key}")
            a1.axhline(v, color=CC[a], ls=ls, lw=1.5, alpha=.85)
    # group the four laws into the two families they actually form, and label the families
    for a in ("Z1", "Z2", "Z4"):
        st = [F(dm[0], f"{a}_{k}") for k in ("SYED_EQ14_STRAIN_POWERLAW", "SYED_EQ16_STRAIN_SINH")]
        en = [F(dm[0], f"{a}_{k}") for k in ("SYED_EQ15_ENERGY_POWERLAW", "SYED_EQ17_ENERGY_SINH")]
        a1.text(1.06e5, math.sqrt(st[0] * st[1]), f" {a}", fontsize=8, color=CC[a],
                va="center", fontweight="bold")
        a1.text(1.06e5, math.sqrt(en[0] * en[1]), f" {a}", fontsize=8, color=CC[a],
                va="center", fontweight="bold")
    a1.text(1.13e5, 2400, "STRAIN\nfamily", fontsize=8, color=C["ok"], va="center",
            fontweight="bold")
    a1.text(1.13e5, 560, "ENERGY\nfamily", fontsize=8, color=C["warn"], va="center",
            fontweight="bold")
    a1.legend(handles=[mlines.Line2D([], [], color="k", ls="-", label="double power law"),
                       mlines.Line2D([], [], color="k", ls="--", label="hyperbolic sine"),
                       mlines.Line2D([], [], color="k", ls=":", label="$N_{required}$")],
              fontsize=7.6, loc="lower right", framealpha=.93)
    lo = min(F(dm[0], f"{a}_{k}") for a in ("Z1", "Z2", "Z4") for k, *_ in LAWS)
    hi = max(F(dm[0], f"{a}_{k}") for a in ("Z1", "Z2", "Z4") for k, *_ in LAWS)
    a1.plot(N, N, "k:", lw=1.2)
    a1.axvspan(1e2, lo, color=C["ok"], alpha=.15)
    a1.axvspan(lo, hi, color=C["amb"], alpha=.30)
    a1.axvspan(hi, 1e5, color=C["bad"], alpha=.13)
    a1.set_xscale("log"); a1.set_yscale("log"); a1.set_xlim(1e2, 1e5); a1.set_ylim(300, 2e4)
    a1.set_ylabel("predicted $N_f$ (cycles) -- CONDITIONAL")
    a1.text(math.sqrt(1e2 * lo), 1.3e4, "ROBUST\nALL PASS", ha="center", fontsize=9,
            color=C["ok"], fontweight="bold")
    a1.text(math.sqrt(lo * hi), 1.3e4, "MODEL-FORM AMBIGUOUS\n"
            f"{lo:.0f} < $N_{{req}}$ $\\leq$ {hi:.0f}   (a factor of {hi/lo:.1f})",
            ha="center", fontsize=9, color="#8d6e00", fontweight="bold")
    a1.text(math.sqrt(hi * 1e5), 1.3e4, "ROBUST\nALL FAIL", ha="center", fontsize=9,
            color=C["bad"], fontweight="bold")
    a1.axvline(1000, color="#455a64", lw=1.4, ls="-.")
    a1.text(1020, 380, " JEDEC 1000-cycle QUALIFICATION\n (reference line only --\n"
            " NOT a field mission)", fontsize=7.2, color="#455a64")
    a1.set_title("FIG-0K-A  Architecture feasibility versus required life, under EVERY "
                 "admitted absolute-life law", fontweight="bold", fontsize=10)
    COL = {"ROBUST PASS": C["ok"], "ROBUST FAIL": C["bad"], "MODEL-FORM AMBIGUOUS": C["amb"]}
    for i, a in enumerate(("Z1", "Z2", "Z4")):
        for r in dm:
            a2.plot(F(r, "N_required"), i, "s", ms=3.2, color=COL[r[f"{a}_status"]])
    a2.set_yticks([0, 1, 2]); a2.set_yticklabels([SH[a] for a in ("Z1", "Z2", "Z4")], fontsize=8.5)
    a2.set_xscale("log"); a2.set_xlim(1e2, 1e5); a2.set_ylim(-.6, 2.6)
    a2.set_xlabel("$N_{required}$ (cycles)  --  PARAMETRIC: no project requirement exists")
    a2.text(.5, .06, "NO $N_{required}$ EXISTS AT WHICH ALL MODELS AGREE Z1 FAILS AND Z2 PASSES "
            "--- the conditions are disjoint (581 < 2499)",
            transform=a2.transAxes, ha="center", fontsize=8.4, color=C["bad"], fontweight="bold",
            bbox=dict(fc="#ffebee", ec=C["bad"], boxstyle="round,pad=0.35"))
    fig.savefig(OUT / "FIG_0K_A_g2_decision_map.png"); plt.close(fig)


def fig_B():
    dm = rows("g2_decision_map.csv")[0]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.6, 4.3))
    x = np.arange(3); w = .2
    for i, (key, lab, ls, col) in enumerate(LAWS):
        v = [F(dm, f"{a}_{key}") for a in ("Z1", "Z2", "Z4")]
        a1.bar(x + (i - 1.5) * w, v, w, color=col, alpha=1.0 if ls == "-" else .55,
               label=lab, edgecolor="k", lw=.4)
    a1.set_xticks(x); a1.set_xticklabels([SH[a] for a in ("Z1", "Z2", "Z4")], fontsize=8.5)
    a1.set_yscale("log"); a1.set_ylabel("predicted $N_f$ (cycles)")
    a1.legend(fontsize=7); a1.set_ylim(200, 6000)
    a1.set_title("absolute life: strain family sits ~4.1x above energy family",
                 fontweight="bold", fontsize=9)
    ec = rows("experiment_condition_metrics.csv")
    z1 = [r for r in ec if r["arch"] == "Z1"]
    we = [F(r, "w_over_eps_MPa") for r in z1]
    order = np.argsort(we)
    a2.barh(range(len(z1)), [we[i] for i in order], .6,
            color=[C["bad"] if we[i] > 180 else C["ink"] for i in order])
    a2.set_yticks(range(len(z1)))
    a2.set_yticklabels([z1[i]["condition"] for i in order], fontsize=7.8)
    a2.axvspan(28.8, 30.0, color=C["ok"], alpha=.35)
    a2.text(33, .3, "Syed's calibration locus\n28.8-30.0 MPa", fontsize=7.8, color=C["ok"])
    a2.set_xlabel("$w_{acc}/\\varepsilon_{acc}$  (MPa)")
    a2.set_title("the two laws differ ONLY through $w/\\varepsilon$\n"
                 "-- and every candidate condition is far off Syed's locus",
                 fontweight="bold", fontsize=9)
    fig.suptitle("FIG-0K-B  Strain-law versus energy-law absolute predictions",
                 fontweight="bold", fontsize=10)
    fig.savefig(OUT / "FIG_0K_B_strain_vs_energy.png"); plt.close(fig)


def fig_C():
    d = rows("experiment_condition_discrimination.csv")[:10][::-1]
    fig, ax = plt.subplots(figsize=(10.2, 5.0))
    y = np.arange(len(d))
    col = [C["ok"] if F(r, "sigma_beta6_n16") >= 3 else C["warn"] for r in d]
    ax.barh(y, [F(r, "D_discrimination") for r in d], .62, color=col)
    ax.axvline(1, color="k", lw=1.2)
    for i, r in enumerate(d):
        ax.text(F(r, "D_discrimination") + .012, i,
                f"  D={F(r,'D_discrimination'):.3f}   {F(r,'sigma_beta6_n16'):.1f}$\\sigma$ "
                f"(n=16, $\\beta$=6)", va="center", fontsize=7.6)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{r['cond_A']}  vs  {r['cond_B']}" for r in d], fontsize=7.8)
    ax.set_xlim(0.95, 2.25); ax.set_xlabel("discrimination power  "
                                           "$D = (w/\\varepsilon)_A / (w/\\varepsilon)_B$")
    ax.set_title("FIG-0K-C  Candidate experiment pairs ranked by MODEL-DISCRIMINATION power",
                 fontweight="bold", fontsize=10)
    ax.text(.98, .06, "two ARCHITECTURES at one profile give D = 1.063 -- essentially blind.\n"
            "Discrimination comes from spanning $w/\\varepsilon$, not from maximising damage.",
            transform=ax.transAxes, ha="right", fontsize=8.2, color=C["ink"],
            bbox=dict(fc="#eceff1", ec=C["ink"], boxstyle="round,pad=0.35"))
    fig.savefig(OUT / "FIG_0K_C_discrimination.png"); plt.close(fig)


def fig_D():
    ec = rows("experiment_condition_metrics.csv")
    by = {(r["arch"], r["condition"]): r for r in ec}
    conds = [c for c in dict.fromkeys(r["condition"] for r in ec)
             if ("Z1", c) in by and ("Z2", c) in by]
    fig, ax = plt.subplots(figsize=(10.0, 4.6))
    x = np.arange(len(conds)); w = .36
    rs = [F(by[("Z1", c)], "M4_creep_strain") / F(by[("Z2", c)], "M4_creep_strain")
          for c in conds]
    re_ = [F(by[("Z1", c)], "M5_creep_energy_MJ_per_m3")
           / F(by[("Z2", c)], "M5_creep_energy_MJ_per_m3") for c in conds]
    ax.bar(x - w / 2, rs, w, color=C["ok"], label="strain law  $N_{Z2}/N_{Z1}$")
    ax.bar(x + w / 2, re_, w, color=C["warn"], label="energy law  $N_{Z2}/N_{Z1}$")
    ax.axhline(1, color="k", lw=1.2)
    ax.axhspan(1.21, 1.38, color=C["z2"], alpha=.16)
    ax.text(len(conds) - .4, 1.295, " Phase-0J-R\n validated band\n 1.21-1.38",
            fontsize=7.8, color=C["z2"], va="center")
    ax.set_xticks(x); ax.set_xticklabels(conds, fontsize=7.6, rotation=18, ha="right")
    ax.set_ylabel("predicted Z2 / Z1 life ratio"); ax.set_ylim(0.95, 1.55)
    ax.legend(fontsize=8)
    ax.set_title("FIG-0K-D  Predicted Z2/Z1 life ratio under each candidate test profile",
                 fontweight="bold", fontsize=10)
    ax.text(.02, .05, "the Z2 advantage persists at EVERY candidate condition -- so any of them "
            "validates the relative claim", transform=ax.transAxes, fontsize=8.2,
            color=C["z2"], bbox=dict(fc="#e8f5e9", ec=C["z2"], boxstyle="round,pad=0.3"))
    fig.savefig(OUT / "FIG_0K_D_relative_ratio_by_profile.png"); plt.close(fig)


def fig_E():
    mp = rows("mission_vs_calibration_decision_map.csv")
    xs = sorted({F(r, "hypothetical_measured_Z1_life") for r in mp})
    ys = sorted({F(r, "N_required") for r in mp})
    idx = {v: i for i, v in enumerate(xs)}; idy = {v: i for i, v in enumerate(ys)}
    KEY = {"ALL PASS -- G2 NOT ACTIVE": 0, "G2 PASSED -- Z1 fails, Z2 passes": 1,
           "ALL FAIL -- architecture does not solve it": 2, "MODEL-FORM AMBIGUOUS": 3,
           "MIXED": 4}
    Z = np.full((len(ys), len(xs)), np.nan)
    for r in mp:
        Z[idy[F(r, "N_required")], idx[F(r, "hypothetical_measured_Z1_life")]] = \
            KEY[r["decision"]]
    from matplotlib.colors import ListedColormap, BoundaryNorm
    cm = ListedColormap([C["ok"], "#00897b", C["bad"], C["amb"], C["grey"]])
    fig, ax = plt.subplots(figsize=(8.8, 5.6))
    ax.pcolormesh(xs, ys, Z, cmap=cm, norm=BoundaryNorm(range(6), 5), shading="nearest")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("HYPOTHETICAL measured Z1 life at the operating cycle (cycles)")
    ax.set_ylabel("$N_{required}$ (cycles)")
    ax.set_title("FIG-0K-E  WHAT-IF: how one calibration plus a mission would decide G2",
                 fontweight="bold", fontsize=10)
    import matplotlib.patches as mp_
    ax.legend(handles=[mp_.Patch(color=C["ok"], label="ALL PASS -- G2 not active"),
                       mp_.Patch(color="#00897b", label="G2 PASSED -- Z1 fails, Z2 passes"),
                       mp_.Patch(color=C["bad"], label="ALL FAIL -- architecture no help")],
              fontsize=8, loc="upper left", framealpha=.92)
    ax.text(.97, .05, "after ONE calibration the AMBIGUOUS region VANISHES:\n"
            "Z1 is measured and Z2 follows to within 6.3 % under either law.\n"
            "But the G2-pass band is only ~17 % wide in $N_{required}$.",
            transform=ax.transAxes, ha="right", fontsize=8, color=C["ink"],
            bbox=dict(fc="#ffffff", ec=C["ink"], boxstyle="round,pad=0.4", alpha=.93))
    fig.savefig(OUT / "FIG_0K_E_calibration_vs_mission.png"); plt.close(fig)


def fig_F():
    fig, ax = plt.subplots(figsize=(12.4, 4.3))
    ax.axis("off")
    steps = [("TEST VEHICLE\nZ1 and Z2 packages\nSAC305, 400 µm ball\n800 µm pitch, no underfill",
              C["z1"]),
             ("THERMAL CYCLE\n2 conditions:\n$-$40/+25 °C and +55/+125 °C\n5-min dwells, 3 °C/min",
              C["warn"]),
             ("ELECTRICAL MONITORING\nin-situ daisy chain\n>300 $\\Omega$, confirmed by 10\n"
              "events within 10 % of t", C["ink"]),
             ("FAILURE DISTRIBUTION\n2-parameter Weibull\nestimate $\\eta$ AND $\\beta$\n"
              "right-censor survivors", C["ok"]),
             ("CALIBRATION\n$C$ from $\\eta$ and $\\varepsilon_{acc}$\n"
              "$W$ from $\\eta$ and $w_{acc}$\ntwo conditions $\\rightarrow$ model form", C["z2"])]
    n = len(steps); w = 1.0 / n
    for i, (txt, col) in enumerate(steps):
        x = i * w
        ax.add_patch(Rectangle((x + .012, .30), w - .034, .44, transform=ax.transAxes,
                               fc="white", ec=col, lw=2.2, zorder=2))
        ax.text(x + w / 2 - .005, .52, txt, transform=ax.transAxes, ha="center", va="center",
                fontsize=8.1, color=col, fontweight="bold", zorder=3)
        if i < n - 1:
            ax.add_patch(FancyArrowPatch((x + w - .020, .52), (x + w + .010, .52),
                                         transform=ax.transAxes, arrowstyle="-|>",
                                         mutation_scale=17, lw=1.8, color=C["grey"], zorder=1))
    ax.text(.5, .175, "MINIMUM IDENTIFIABLE DESIGN:  2 architectures  ×  2 conditions  ×  16 "
            "packages  =  64 units", transform=ax.transAxes, ha="center", fontsize=10,
            fontweight="bold", color=C["ink"],
            bbox=dict(fc="#eceff1", ec=C["ink"], boxstyle="round,pad=0.45"))
    ax.text(.5, .045, "ONE condition calibrates absolute life at that cycle but CANNOT identify "
            "the life law.  TWO conditions spanning $w/\\varepsilon$ discriminate at 6.2$\\sigma$.",
            transform=ax.transAxes, ha="center", fontsize=8.4, color=C["bad"])
    ax.set_title("FIG-0K-F  Minimal experimental workflow", fontweight="bold", fontsize=11)
    fig.savefig(OUT / "FIG_0K_F_workflow.png"); plt.close(fig)


if __name__ == "__main__":
    for f in (fig_A, fig_B, fig_C, fig_D, fig_E, fig_F):
        f(); print("  ok", f.__name__)
    for p in sorted(OUT.glob("FIG_0K_*.png")):
        print(f"  {p.name:42} {p.stat().st_size:>8} B")
