#!/usr/bin/env python3
"""Phase-0K-R figures (Sec.29)."""
from __future__ import annotations
import csv, math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, Rectangle

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0kr"
plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": .3,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
C = {"z1": "#1565c0", "z2": "#1b5e20", "grey": "#9e9e9e", "bad": "#c62828", "warn": "#ef6c00",
     "ok": "#2e7d32", "ink": "#37474f", "amb": "#fdd835", "old": "#8d6e63"}
rows = lambda p: list(csv.DictReader(open(OUT / p)))
F = lambda r, k: float(r[k])
T_LO, T_HI, S_LO, S_HI = 45.0, 150.0, 7.51, 15.92


def fig_A():
    """Calibration domain in temperature x stress, with profiles overlaid."""
    dom = {r["condition"]: r for r in rows("profile_domain_audit.csv") if r["arch"] == "Z1"}
    fig, ax = plt.subplots(figsize=(9.8, 5.8))
    ax.add_patch(Rectangle((T_LO, S_LO), T_HI - T_LO, S_HI - S_LO, fc=C["ok"], alpha=.30,
                           ec=C["ok"], lw=2, zorder=2))
    ax.annotate("CREEP CALIBRATION\n45-150 °C,  7.51-15.92 MPa\n19 measured points",
                xy=(120, 11), xytext=(60, 4.9), fontsize=8.6, color="#14532d",
                fontweight="bold", zorder=7, ha="center",
                arrowprops=dict(arrowstyle="->", color="#14532d", lw=1.4))
    pts = [(t, s, e) for t, s, e in
           [(45, 10.54, 15.92), (80, 10.43, 14.46), (115, 8.73, 12.41), (150, 7.51, 11.52)]]
    for t, lo, hi in pts:
        ax.plot([t, t], [lo, hi], "o-", color="#14532d", ms=4, lw=2, zorder=4)
    SEL = {"D_LOW_WIDE", "D_HIGH_NARROW"}
    for k, r in dom.items():
        tmin, tmax = F(r, "T_min_C"), F(r, "T_max_C")
        d = r["driving_overstress_range_MPa"].split("-")
        lo, hi = float(d[0]), float(d[1])
        inv = "INVALID" in r["domain_class"]
        col = C["bad"] if inv else (C["z2"] if k in SEL else C["grey"])
        lw = 2.6 if k in SEL else 1.4
        ax.add_patch(Rectangle((tmin, lo), tmax - tmin, hi - lo, fc="none", ec=col, lw=lw,
                               ls="-" if k in SEL else (":" if inv else "--"), zorder=5,
                               alpha=1.0 if (k in SEL or inv) else .45))
        # label only the decisive boxes -- the rest read as the grey envelope they are
        if k in SEL or inv:
            ax.text(tmin + 2, hi * 1.10, k, fontsize=7.6, color=col, fontweight="bold",
                    zorder=6)
    ax.axvline(T_LO, color=C["bad"], lw=1.6, ls="-.")
    ax.text(T_LO - 3, 420, "creep floor 45 °C", rotation=90, fontsize=8, color=C["bad"],
            ha="right", va="top")
    ax.set_yscale("log"); ax.set_xlim(-60, 168); ax.set_ylim(4, 900)
    ax.set_xlabel("joint temperature (°C)")
    ax.set_ylabel("DRIVING overstress  $\\sigma_{eq}-\\sigma_y$  (MPa)")
    ax.set_title("FIG-0KR-A  Constitutive calibration domain versus every proposed profile",
                 fontweight="bold", fontsize=10)
    ax.text(.985, .95, "NO profile lies inside the STRESS window. That is a property of how\n"
            "hard this package loads its joints, not of the thermal profile.",
            transform=ax.transAxes, ha="right", va="top", fontsize=8.2, color=C["bad"],
            bbox=dict(fc="#ffebee", ec=C["bad"], boxstyle="round,pad=0.35"))
    fig.savefig(OUT / "FIG_0KR_A_domain.png"); plt.close(fig)


def fig_B():
    """Original pair versus best within-domain pair."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.8, 4.5))
    labs = ["D", "separation %", "damage below\n45 °C floor %", "Z (β=5.1, n=16)"]
    orig = [1.849, 84.9, 100.0, 5.99]
    new = [1.4395, 44.0, 0.0, 3.44]
    x = np.arange(4); w = .36
    a1.bar(x - w / 2, orig, w, color=C["old"], label="ORIGINAL  −40/+25 + 55/125  (WITHDRAWN)")
    a1.bar(x + w / 2, new, w, color=C["z2"], label="REVISED  45/125 + 110/150")
    for i, (o, n) in enumerate(zip(orig, new)):
        a1.text(i - w / 2, o + 2, f"{o:g}", ha="center", fontsize=7.8, color=C["old"])
        a1.text(i + w / 2, n + 2, f"{n:g}", ha="center", fontsize=7.8, color=C["z2"],
                fontweight="bold")
    a1.set_xticks(x); a1.set_xticklabels(labs, fontsize=8)
    a1.set_ylim(0, 118); a1.legend(fontsize=7.6, loc="upper center")
    a1.axhline(3, color=C["bad"], ls=":", lw=1.2)
    a1.text(3.42, 4.5, "Z = 3 bar", fontsize=7, color=C["bad"])
    a1.set_title("the redesign costs 41 % of D and buys validity",
                 fontweight="bold", fontsize=9)
    ec = rows("experiment_profile_search.csv")
    adm = [r for r in ec if r["admissible_for_design"] == "True"]
    a2.scatter([F(r, "max_cell_duration_days") for r in adm],
               [F(r, "D_discrimination") for r in adm], s=60, c=C["grey"], zorder=3)
    sel = [r for r in adm if {r["cond_A"], r["cond_B"]} == {"D_LOW_WIDE", "D_HIGH_NARROW"}]
    if sel:
        a2.scatter([F(sel[0], "max_cell_duration_days")], [F(sel[0], "D_discrimination")],
                   s=230, marker="*", c=C["z2"], zorder=5, edgecolors="k")
        a2.annotate("SELECTED", (F(sel[0], "max_cell_duration_days"),
                                 F(sel[0], "D_discrimination")),
                    textcoords="offset points", xytext=(10, 8), fontsize=9, color=C["z2"],
                    fontweight="bold")
    alt = [r for r in adm if {r["cond_A"], r["cond_B"]} == {"D_LOW_WIDE", "D_HIGH_LONG"}]
    if alt:
        a2.annotate("higher D, +46 days/cell\n-> rejected on the predeclared rule",
                    (F(alt[0], "max_cell_duration_days"), F(alt[0], "D_discrimination")),
                    textcoords="offset points", xytext=(-14, 10), fontsize=7.4,
                    color=C["warn"], ha="right")
    a2.axhline(1.30, color=C["bad"], ls=":", lw=1.2)
    a2.text(60, 1.315, "D needed for Z = 3 at β=5.1, n=16", fontsize=7.4, color=C["bad"])
    a2.set_xlabel("longest cell duration to 63 % failures (days)")
    a2.set_ylabel("discrimination power D")
    a2.set_title("selection is composite, not max-D", fontweight="bold", fontsize=9)
    fig.suptitle("FIG-0KR-B  Original Phase-0K pair versus the best within-domain pair",
                 fontweight="bold", fontsize=10)
    fig.savefig(OUT / "FIG_0KR_B_pair_comparison.png"); plt.close(fig)


def fig_C():
    """Discrimination score over candidate pairs."""
    ec = sorted(rows("experiment_profile_search.csv"), key=lambda r: F(r, "D_discrimination"))
    fig, ax = plt.subplots(figsize=(10.4, 5.4))
    y = np.arange(len(ec))
    col = [C["bad"] if r["admissible_for_design"] != "True" else
           (C["z2"] if F(r, "Z_discrimination_beta5p1_n16") >= 3 else C["warn"]) for r in ec]
    ax.barh(y, [F(r, "D_discrimination") for r in ec], .68, color=col)
    ax.axvline(1, color="k", lw=1.2)
    ax.axvline(1.30, color=C["bad"], ls=":", lw=1.5)
    for i, r in enumerate(ec):
        ax.text(F(r, "D_discrimination") + .006, i,
                f"  Z={F(r,'Z_discrimination_beta5p1_n16'):.2f}", va="center", fontsize=7)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{r['cond_A'].replace('D_','')} / {r['cond_B'].replace('D_','')}"
                        for r in ec], fontsize=7.4)
    ax.set_xlim(1.0, 1.60)
    ax.set_xlabel("D = $(w/\\varepsilon)_A/(w/\\varepsilon)_B$   "
                  "(dotted: D needed for Z = 3 at β = 5.1, n = 16)")
    ax.set_title("FIG-0KR-C  Model-discrimination score over within-domain condition pairs",
                 fontweight="bold", fontsize=10)
    import matplotlib.patches as mp
    ax.legend(handles=[mp.Patch(color=C["z2"], label="meets the Z = 3 bar"),
                       mp.Patch(color=C["warn"], label="admissible, below the bar")],
              fontsize=8, loc="lower right")
    fig.savefig(OUT / "FIG_0KR_C_discrimination.png"); plt.close(fig)


def fig_D():
    """Weibull beta evidence and its effect on required n."""
    db = rows("SAC305_WEIBULL_BETA_DATABASE.csv")
    ss = rows("sample_size_sensitivity.csv")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.8, 4.5))
    bs = sorted(F(r, "beta") for r in db)
    sac = sorted(F(r, "beta") for r in db if r["alloy"] == "SAC305")
    a1.hist(bs, bins=np.arange(4, 22, 1.5), color=C["grey"], edgecolor="k", label="all SnAgCu")
    a1.hist(sac, bins=np.arange(4, 22, 1.5), color=C["z1"], edgecolor="k", label="SAC305 only")
    a1.axvline(6, color=C["bad"], lw=2.2, ls="--")
    a1.text(6.15, 3.4, "Phase-0K assumed\nβ = 6 'pessimistic'", fontsize=8, color=C["bad"])
    a1.axvline(min(bs), color=C["ok"], lw=2.2)
    a1.text(min(bs) - .15, 3.4, f"observed\nminimum {min(bs)}", fontsize=8, color=C["ok"],
            ha="right")
    a1.set_xlabel("Weibull slope β"); a1.set_ylabel("primary cells")
    a1.legend(fontsize=8)
    a1.set_title(f"β = 6 is the {100*sum(1 for b in bs if b<6)//len(bs)}th percentile of "
                 f"{len(bs)} primary cells\n— NOT a conservative bound",
                 fontweight="bold", fontsize=9)
    for key, lab, col in (("Z_Q1_model_discrimination", "Q1 model discrimination", C["z2"]),
                          ("Z_Q2_arch_both_conditions", "Q2 Z2/Z1 architecture", C["z1"])):
        for n, ls in ((16, "--"), (34, "-")):
            d = sorted([r for r in ss if int(r["n_per_cell"]) == n], key=lambda r: F(r, "beta"))
            if d:
                a2.plot([F(r, "beta") for r in d], [F(r, key) for r in d], ls, color=col,
                        marker="o", ms=4, label=f"{lab}, n={n}")
    a2.axhline(3, color=C["bad"], ls=":", lw=1.5)
    a2.axvline(5.1, color=C["ok"], lw=1.6)
    a2.text(5.2, .6, "observed worst β = 5.1", fontsize=7.6, color=C["ok"], rotation=90)
    a2.set_xlabel("Weibull slope β"); a2.set_ylabel("expected discrimination Z-score")
    a2.legend(fontsize=7.2); a2.set_ylim(0, 5)
    a2.set_title("n = 16 clears Q1 at every plausible β;\nQ2 needs n = 34",
                 fontweight="bold", fontsize=9)
    fig.suptitle("FIG-0KR-D  Weibull β evidence and its effect on required specimens",
                 fontweight="bold", fontsize=10)
    fig.savefig(OUT / "FIG_0KR_D_beta.png"); plt.close(fig)


def fig_E():
    """Power versus n for both questions."""
    ss = rows("sample_size_sensitivity.csv")
    fig, ax = plt.subplots(figsize=(9.6, 5.2))
    for beta, col in ((5.1, C["bad"]), (6, C["warn"]), (8, C["ok"])):
        b = min((F(r, "beta") for r in ss), key=lambda x: abs(x - beta))
        d = sorted([r for r in ss if F(r, "beta") == b], key=lambda r: int(r["n_per_cell"]))
        ax.plot([int(r["n_per_cell"]) for r in d], [F(r, "Z_Q1_model_discrimination") for r in d],
                "-o", color=col, ms=5, label=f"Q1 model discrimination, β={b:g}")
        ax.plot([int(r["n_per_cell"]) for r in d],
                [F(r, "Z_Q2_arch_both_conditions") for r in d],
                "--s", color=col, ms=4, alpha=.75, label=f"Q2 Z2/Z1 architecture, β={b:g}")
    ax.axhline(3, color="k", ls=":", lw=1.6)
    ax.text(50, 3.06, "adequacy bar Z = 3", fontsize=8)
    ax.axvline(16, color=C["old"], ls="-.", lw=1.4)
    ax.text(16.5, .35, "Phase-0K\nn = 16", fontsize=8, color=C["old"])
    ax.axvline(34, color=C["z2"], lw=1.8)
    ax.text(34.5, .35, "Phase-0K-R\nn = 34", fontsize=8, color=C["z2"], fontweight="bold")
    ax.set_xlabel("specimens per cell"); ax.set_ylabel("expected discrimination Z-score")
    ax.set_ylim(0, 5); ax.legend(fontsize=7.4, ncol=2, loc="lower right")
    ax.set_title("FIG-0KR-E  Statistical power versus specimens, for BOTH experimental questions",
                 fontweight="bold", fontsize=10)
    ax.text(.02, .95, "n = 16 answers Q1 but NOT Q2. A single campaign answering both needs "
            "n = 34.", transform=ax.transAxes, va="top", fontsize=8.4, color=C["ink"],
            bbox=dict(fc="#eceff1", ec=C["ink"], boxstyle="round,pad=0.35"))
    fig.savefig(OUT / "FIG_0KR_E_power.png"); plt.close(fig)


def fig_F():
    """Final test matrix."""
    idf = rows("identifiability_final.csv")
    fig, ax = plt.subplots(figsize=(10.6, 4.6))
    ax.axis("off")
    conds = ["D_LOW_WIDE", "D_HIGH_NARROW"]
    hdr = ["", "45 → 125 °C\n5-min dwells, 3 °C/min\n1.06 h/cycle",
           "110 → 150 °C\n5-min dwells, 3 °C/min\n0.61 h/cycle"]
    for j, h in enumerate(hdr):
        ax.text(.16 + j * .30, .86, h, ha="center", va="center", fontsize=8.6,
                fontweight="bold", transform=ax.transAxes,
                color=C["ink"] if j else "white")
    for i, arch in enumerate(("Z1", "Z2")):
        col = C["z1"] if arch == "Z1" else C["z2"]
        ax.text(.16, .60 - i * .22, f"{arch}\n{'embedded' if arch=='Z1' else 'backside'}",
                ha="center", va="center", fontsize=9.5, fontweight="bold", color=col,
                transform=ax.transAxes)
        for j, c in enumerate(conds):
            r = [x for x in idf if x["condition"] == c and x["arch"] == arch]
            if not r:
                continue
            r = r[0]
            ax.add_patch(Rectangle((.30 + j * .30, .50 - i * .22), .27, .17,
                                   transform=ax.transAxes, fc="white", ec=col, lw=2))
            ax.text(.435 + j * .30, .585 - i * .22,
                    f"n = 34 packages\n$N_f$ {F(r,'Nf_energy_Eq15'):.0f}–{F(r,'Nf_strain_Eq14'):.0f}"
                    f"   {F(r,'days_to_63pct_energy'):.0f}–{F(r,'days_to_63pct_strain'):.0f} d",
                    ha="center", va="center", fontsize=8, color=col, transform=ax.transAxes)
    ax.text(.5, .12, "4 CELLS  ×  34 PACKAGES  =  136 UNITS     ·     "
            "failure: >300 Ω + 10 events within 10 % of t     ·     Z4 EXCLUDED",
            ha="center", fontsize=9.4, fontweight="bold", color=C["ink"],
            transform=ax.transAxes,
            bbox=dict(fc="#eceff1", ec=C["ink"], boxstyle="round,pad=0.45"))
    ax.set_title("FIG-0KR-F  Final test matrix", fontweight="bold", fontsize=11)
    fig.savefig(OUT / "FIG_0KR_F_matrix.png"); plt.close(fig)


def fig_G():
    """Final workflow and outputs."""
    fig, ax = plt.subplots(figsize=(12.6, 4.2))
    ax.axis("off")
    steps = [("BUILD\nZ1 + Z2 vehicles\nSAC305, 400 µm ball\n800 µm pitch, no underfill", C["z1"]),
             ("CYCLE\n45→125 °C  and\n110→150 °C\n5-min dwells, 3 °C/min", C["warn"]),
             ("MONITOR\nin-situ daisy chain\n>300 Ω + 10 events\nwithin 10 % of t", C["ink"]),
             ("FIT\n2-par Weibull per cell\nestimate η AND β\nright-censor survivors", C["ok"]),
             ("DECIDE\nQ1 which law (D=1.44)\nQ2 Z2/Z1 ratio\n→ absolute life", C["z2"])]
    n = len(steps); w = 1.0 / n
    for i, (t, col) in enumerate(steps):
        x = i * w
        ax.add_patch(Rectangle((x + .012, .32), w - .034, .42, transform=ax.transAxes,
                               fc="white", ec=col, lw=2.2, zorder=2))
        ax.text(x + w / 2 - .005, .53, t, transform=ax.transAxes, ha="center", va="center",
                fontsize=8.1, color=col, fontweight="bold", zorder=3)
        if i < n - 1:
            ax.add_patch(FancyArrowPatch((x + w - .020, .53), (x + w + .010, .53),
                                         transform=ax.transAxes, arrowstyle="-|>",
                                         mutation_scale=17, lw=1.8, color=C["grey"], zorder=1))
    ax.text(.5, .175, "DELIVERS: which fatigue law · absolute life for this package · "
            "the Z2/Z1 advantage measured", transform=ax.transAxes, ha="center", fontsize=9,
            fontweight="bold", color=C["ink"],
            bbox=dict(fc="#eceff1", ec=C["ink"], boxstyle="round,pad=0.4"))
    ax.text(.5, .045, "DOES NOT DELIVER: a required life (system owner) · validity outside "
            "45–150 °C · the six uncomputed failure mechanisms",
            transform=ax.transAxes, ha="center", fontsize=8.2, color=C["bad"])
    ax.set_title("FIG-0KR-G  Final experiment workflow", fontweight="bold", fontsize=11)
    fig.savefig(OUT / "FIG_0KR_G_workflow.png"); plt.close(fig)


if __name__ == "__main__":
    for f in (fig_A, fig_B, fig_C, fig_D, fig_E, fig_F, fig_G):
        f(); print("  ok", f.__name__)
    for p in sorted(OUT.glob("FIG_0KR_*.png")):
        print(f"  {p.name:38} {p.stat().st_size:>8} B")
