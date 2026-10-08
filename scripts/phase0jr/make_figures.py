#!/usr/bin/env python3
"""Phase-0J-R figures (Sec.29). Only figures that carry a result."""
from __future__ import annotations
import csv, math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0jr"
plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": .3,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
C = {"z1": "#1565c0", "z2": "#1b5e20", "z4": "#b71c1c", "grey": "#9e9e9e",
     "bad": "#c62828", "warn": "#ef6c00", "ok": "#2e7d32", "ink": "#37474f",
     "orig": "#8d6e63", "corr": "#00695c"}
rows = lambda p: list(csv.DictReader(open(OUT / p)))
F = lambda r, k: float(r[k])
SH = {"Z1": "Z1 embedded", "Z2": "Z2 backside", "Z4": "Z4 power die"}
CC = {"Z1": C["z1"], "Z2": C["z2"], "Z4": C["z4"]}
C_PL, W_PL = 0.0468, 0.0015
C_PL_O, W_PL_O = 0.0358, 0.0012


def fig_A():
    """Syed original vs author-corrected constants and the life they imply."""
    labs = ["$C'$ total creep\nstrain (Eq.14)", "$W'$ creep energy\n(Eq.15)",
            "$C'$ sinh (Eq.16)", "$W'$ sinh (Eq.17)", "$C_{II}$ partitioned"]
    orig = [0.0358, 0.0012, 0.0405, 0.0014, 0.036]
    corr = [0.0468, 0.0015, 0.0513, 0.0019, 0.045]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.8, 4.3),
                                 gridspec_kw={"width_ratios": [1.25, 1]})
    x = np.arange(len(labs)); w = .36
    a1.bar(x - w / 2, orig, w, color=C["orig"], label="IEEE ECTC original")
    a1.bar(x + w / 2, corr, w, color=C["corr"], label="author-CORRECTED")
    for i, (o, c) in enumerate(zip(orig, corr)):
        a1.text(i + w / 2, c * 1.03, f"×{c/o:.2f}", ha="center", fontsize=7.8,
                color=C["corr"], fontweight="bold")
    a1.set_xticks(x); a1.set_xticklabels(labs, fontsize=7.4)
    a1.set_yscale("log"); a1.set_ylabel("life-model constant")
    a1.legend(fontsize=8); a1.set_title("constants: every one RAISED by 1.25–1.43×",
                                        fontweight="bold", fontsize=9)
    a1.text(.5, .06, "root cause (author's slides): original fit used FIRST-CYCLE values;\n"
                     "SnAgCu stabilises after cycle 2 with a 20–30 % reduction",
            transform=a1.transAxes, ha="center", fontsize=7.6,
            bbox=dict(fc="#fff8e1", ec=C["orig"], boxstyle="round,pad=0.35"))
    eps = np.logspace(-3, -1.2, 100)
    a2.loglog(eps, 1 / (C_PL_O * eps), color=C["orig"], lw=2, ls="--",
              label=f"original  $C'$={C_PL_O}")
    a2.loglog(eps, 1 / (C_PL * eps), color=C["corr"], lw=2, label=f"corrected $C'$={C_PL}")
    nat = {r["short"]: r for r in rows("syed_layer_metrics.csv") if r["n_mid"] == "10"}
    for s, r in nat.items():
        e = F(r, "M4_syed_layer")
        a2.plot(e, 1 / (C_PL * e), "o", ms=10, color=CC[s], mec="k", mew=.7, zorder=5)
    a2.set_xlabel("$\\varepsilon_{acc}$ per cycle"); a2.set_ylabel("$N_f$ (cycles)")
    a2.set_title("using the ORIGINAL constants would over-predict life by 31 %",
                 fontweight="bold", fontsize=9)
    a2.legend(fontsize=8); a2.grid(True, which="both", alpha=.25)
    fig.suptitle("FIG-0JR-A  Syed 2004: original versus author-corrected calibration",
                 fontweight="bold", fontsize=10)
    fig.savefig(OUT / "FIG_0JR_A_syed_version_audit.png"); plt.close(fig)


def fig_B():
    """Reproduction of Syed's own calibration and validation."""
    rp = [r for r in rows("syed_reproduction.csv") if r["set"] == "Table 3 VALIDATION"]
    cal = [r for r in rows("syed_reproduction.csv") if r["set"] == "Table 2b CALIBRATION"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.8, 4.4))
    meas = [F(r, "reported_Nf_measured") for r in rp]
    ps = [F(r, "reported_Nf_powerlaw_creep") for r in rp]
    pe = [F(r, "reported_Nf_powerlaw_energy") for r in rp]
    lim = [300, 1600]
    a1.plot(lim, lim, "k-", lw=1)
    for f, lab in ((1.25, "±25 % (the paper's claim)"), (0.8, None)):
        a1.plot(lim, [f * x for x in lim], "k--", lw=.9, alpha=.6, label=lab)
    a1.plot(lim, [0.75 * x for x in lim], "k--", lw=.9, alpha=.6)
    a1.plot(meas, ps, "o", ms=10, color=C["corr"], mec="k", mew=.7,
            label="Eq.14 accumulated creep strain")
    a1.plot(meas, pe, "s", ms=9, color=C["warn"], mec="k", mew=.7, label="Eq.15 creep energy")
    a1.set_xlim(lim); a1.set_ylim(lim)
    a1.set_xlabel("measured mean life (cycles)"); a1.set_ylabel("predicted (cycles)")
    a1.set_title("(a) Table 3 independent validation package\nworst error 11.7 %  →  PASSES",
                 fontweight="bold", fontsize=9)
    a1.legend(fontsize=7.6, loc="upper left")
    wo = [F(r, "implied_w_over_eps_MPa") for r in rp]
    ours = [F(r, "M5_syed_layer_MJ_per_m3") / F(r, "M4_syed_layer")
            for r in rows("syed_layer_metrics.csv") if r["n_mid"] == "10"]
    a2.bar(range(len(wo)), wo, .55, color=C["corr"], label="Syed's 4 validation configs")
    a2.bar(range(len(wo), len(wo) + len(ours)), ours, .55, color=C["bad"],
           label="OUR three architectures")
    a2.axhspan(min(wo), max(wo), color=C["corr"], alpha=.15)
    a2.set_xticks(range(len(wo) + len(ours)))
    a2.set_xticklabels(["no/1S", "no/2S", "st/1S", "st/2S", "Z1", "Z2", "Z4"], fontsize=8)
    a2.set_ylabel("$w_{acc} / \\varepsilon_{acc}$  (MPa)")
    a2.set_title("(b) the two constants agree to 4.2 % on HIS data\n"
                 "— and ours sits 4.3× off that locus", fontweight="bold", fontsize=9)
    a2.legend(fontsize=7.8); a2.set_ylim(0, 150)
    a2.text(.5, .55, "INTERPOLATION on each metric separately,\nEXTRAPOLATION on the pair",
            transform=a2.transAxes, ha="center", fontsize=8, color=C["bad"],
            bbox=dict(fc="#ffebee", ec=C["bad"], boxstyle="round,pad=0.35"))
    fig.suptitle("FIG-0JR-B  Reproduction of Syed's published calibration "
                 "(no digitisation: printed table values only)", fontweight="bold", fontsize=10)
    fig.savefig(OUT / "FIG_0JR_B_syed_reproduction.png"); plt.close(fig)


def fig_C():
    """M1/M2/M3 (Phase-0I core) versus M4/M5 (Syed-matched 25 um layers)."""
    arch = rows("architecture_after_metric_matching.csv")
    fig, ax = plt.subplots(1, 3, figsize=(12.6, 4.1))
    keys = [("M1_total_inelastic_path_core", "M4_accum_creep_strain_syed25um",
             "strain metric", 1e3, "[$\\times 10^{-3}$]"),
            ("M3_total_inelastic_energy_core", "M5_creep_energy_syed25um_MJ_per_m3",
             "energy metric (MJ/m$^3$)", 1, "")]
    x = np.arange(3); w = .36
    for k, (ka, kb, lab, sc, sfx) in enumerate(keys):
        va = [F(r, ka) * sc for r in arch]; vb = [F(r, kb) * sc for r in arch]
        ax[k].bar(x - w / 2, va, w, color=C["grey"], label="Phase-0I core, uniform mesh")
        ax[k].bar(x + w / 2, vb, w, color=C["corr"], label="Syed 25 µm layers, graded mesh")
        for i, (p, q) in enumerate(zip(va, vb)):
            ax[k].text(i + w / 2, q * 1.02, f"×{q/p:.2f}", ha="center", fontsize=7.6,
                       color=C["corr"], fontweight="bold")
        ax[k].set_xticks(x); ax[k].set_xticklabels([SH[r["arch"][5:7]] for r in arch], fontsize=8)
        ax[k].set_title(lab + "  " + sfx, fontsize=9, fontweight="bold")
    ax[0].legend(fontsize=7.4, loc="upper center")
    ax[0].set_ylabel("per stabilised cycle")
    r0 = [F(r, "rel_life_vs_Z1_syed_strain") for r in arch]
    ax[2].bar(x - w / 2, [1.558, 1.0, 0.890][0:1] + [0, 0], w, color="none")
    ax[2].bar([0, 1, 2], r0, .5, color=[CC[r["arch"][5:7]] for r in arch], zorder=3)
    ax[2].axhline(1, color="k", lw=1)
    ax[2].plot([1], [1.558], "v", ms=12, color=C["bad"], zorder=5)
    ax[2].annotate("Phase-0J value 1.558\n(unmatched volume)\nWITHDRAWN", (1, 1.558),
                   textcoords="offset points", xytext=(-6, 12), fontsize=7.6, color=C["bad"],
                   ha="center", fontweight="bold")
    for i, v in enumerate(r0):
        ax[2].text(i, v + .02, f"{v:.3f}", ha="center", fontsize=8.5, fontweight="bold")
    ax[2].set_xticks(x); ax[2].set_xticklabels([SH[r["arch"][5:7]] for r in arch], fontsize=8)
    ax[2].set_ylim(0, 1.85); ax[2].set_ylabel("relative life vs Z1")
    ax[2].set_title("matching the averaging volume\nMOVES the relative result",
                    fontsize=9, fontweight="bold")
    fig.suptitle("FIG-0JR-C  Metric definitions and architecture values: the extraction volume "
                 "is not a detail", fontweight="bold", fontsize=10)
    fig.savefig(OUT / "FIG_0JR_C_metric_definitions.png"); plt.close(fig)


def fig_D():
    """Dwell-time sensitivity."""
    dw = rows("dwell_sensitivity.csv")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.6, 4.3))
    for s in ("Z1", "Z2"):
        d = sorted([r for r in dw if r["short"] == s], key=lambda r: F(r, "dwell_s"))
        a1.semilogx([F(r, "dwell_s") for r in d], [F(r, "M4_creep_strain") * 1e3 for r in d],
                    "o-", color=CC[s], ms=6, label=f"{SH[s]}  M4")
        a1.semilogx([F(r, "dwell_s") for r in d],
                    [F(r, "M5_creep_energy_MJ_per_m3") * 1e3 / 130 for r in d],
                    "s--", color=CC[s], ms=5, alpha=.55,
                    label=f"{SH[s]}  M5 (scaled)")
    a1.axvline(300, color=C["ink"], ls=":", lw=1.4)
    a1.text(310, a1.get_ylim()[0] * 1.02, " the ACTUAL Phase-0I dwell", fontsize=7.8,
            color=C["ink"], rotation=90, va="bottom")
    a1.set_xlabel("dwell at each extreme (s)  —  DWELL-TIME SENSITIVITY, not a mission")
    a1.set_ylabel("metric  [$\\times 10^{-3}$]"); a1.legend(fontsize=7.2)
    a1.set_title("absolute metric: only +17–22 % over a 30× dwell change",
                 fontweight="bold", fontsize=9)
    z1 = {F(r, "dwell_s"): r for r in dw if r["short"] == "Z1"}
    z2 = {F(r, "dwell_s"): r for r in dw if r["short"] == "Z2"}
    ds = sorted(z1)
    a2.semilogx(ds, [F(z1[d], "M4_creep_strain") / F(z2[d], "M4_creep_strain") for d in ds],
                "o-", color=C["corr"], ms=7, lw=2, label="strain-based life ratio Z2/Z1")
    a2.semilogx(ds, [F(z1[d], "M5_creep_energy_MJ_per_m3")
                     / F(z2[d], "M5_creep_energy_MJ_per_m3") for d in ds],
                "s-", color=C["warn"], ms=7, lw=2, label="energy-based life ratio Z2/Z1")
    a2.axhline(1, color="k", lw=1); a2.set_ylim(0.95, 1.5)
    a2.set_xlabel("dwell at each extreme (s)"); a2.set_ylabel("Z2 / Z1 relative life")
    a2.legend(fontsize=8)
    a2.set_title("RELATIVE result is dwell-insensitive: 1.20–1.32 throughout",
                 fontweight="bold", fontsize=9)
    a2.text(.5, .08, "Phase-0J feared a zero-dwell incompatibility.\n"
                     "There is a 300 s dwell, and it barely matters.",
            transform=a2.transAxes, ha="center", fontsize=8, color=C["ok"],
            bbox=dict(fc="#e8f5e9", ec=C["ok"], boxstyle="round,pad=0.35"))
    fig.suptitle("FIG-0JR-D  Dwell-time sensitivity of creep strain and creep energy",
                 fontweight="bold", fontsize=10)
    fig.savefig(OUT / "FIG_0JR_D_dwell_sensitivity.png"); plt.close(fig)


def fig_E():
    """Our three architectures on Syed's native calibration plot."""
    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    lives = [3520, 3960, 4570, 3103, 417, 1047, 1890, 2868, 2720, 10027, 6381, 275]
    eps = [1 / (C_PL * L) for L in lives]
    ax.loglog(eps, lives, "o", ms=8, color=C["grey"], mec="k", mew=.6,
              label="Syed 12-point calibration set (implied $\\varepsilon_{acc}$)")
    xs = np.logspace(-3.1, -0.9, 100)
    ax.loglog(xs, 1 / (C_PL * xs), color=C["corr"], lw=2,
              label="$N_f=(0.0468\\,\\varepsilon_{acc})^{-1}$  author-corrected")
    lo, hi = min(eps), max(eps)
    ax.axvspan(lo, hi, color=C["corr"], alpha=.10)
    ax.text(lo * 1.15, 1.4e4, "Syed's calibrated domain", fontsize=8.5, color=C["corr"])
    for r in rows("syed_layer_metrics.csv"):
        if r["n_mid"] != "10":
            continue
        s = r["short"]; e = F(r, "M4_syed_layer")
        ax.plot(e, 1 / (C_PL * e), "*", ms=20, color=CC[s], mec="k", mew=.8, zorder=6)
        ax.annotate(f"{SH[s]}\n{1/(C_PL*e):.0f}", (e, 1 / (C_PL * e)),
                    textcoords="offset points", xytext=(12, 8), fontsize=8.2,
                    color=CC[s], fontweight="bold")
    ax.set_xlabel("accumulated creep strain per cycle, $\\varepsilon_{acc}$  "
                  "(25 µm layers, both faces)")
    ax.set_ylabel("mean cycles to failure")
    ax.set_title("FIG-0JR-E  Z1/Z2/Z4 on Syed's native calibration — INTERPOLATION, not "
                 "extrapolation", fontweight="bold", fontsize=10)
    ax.legend(fontsize=8, loc="lower left"); ax.grid(True, which="both", alpha=.25)
    ax.text(.985, .93, "on $\\varepsilon_{acc}$ alone our points interpolate;\n"
                       "on the PAIR ($w/\\varepsilon$) they sit 4.3× off the locus",
            transform=ax.transAxes, ha="right", va="top", fontsize=8, color=C["bad"],
            bbox=dict(fc="#ffebee", ec=C["bad"], boxstyle="round,pad=0.35"))
    fig.savefig(OUT / "FIG_0JR_E_on_syed_calibration.png"); plt.close(fig)


def fig_F():
    """Life prediction by admissible primary law."""
    lw = [r for r in rows("lifetime_by_primary_law.csv") if r["Z2_over_Z1"] != ""]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.0, 4.4),
                                 gridspec_kw={"width_ratios": [1, 1.15]})
    ab = [r for r in lw if r["Z1"] != ""]
    x = np.arange(len(ab)); w = .26
    for i, (s, c) in enumerate((("Z1", C["z1"]), ("Z2", C["z2"]), ("Z4", C["z4"]))):
        a1.bar(x + (i - 1) * w, [F(r, s) for r in ab], w, color=c, label=SH[s])
    a1.set_xticks(x)
    a1.set_xticklabels(["Syed\nstrain\n(Eq.14)", "Syed\nenergy\n(Eq.15)",
                        "Syed sinh\nstrain\n(Eq.16)", "Syed sinh\nenergy\n(Eq.17)"][:len(ab)],
                       fontsize=7.6)
    a1.set_ylabel("predicted $N_f$ (cycles)  — CONDITIONAL"); a1.legend(fontsize=8)
    a1.set_title("ABSOLUTE life: the two metric families\ndisagree by 4.1×",
                 fontweight="bold", fontsize=9)
    a1.text(.5, .88, "NOT VALIDATED", transform=a1.transAxes, ha="center", fontsize=9,
            color=C["bad"], fontweight="bold",
            bbox=dict(fc="#ffebee", ec=C["bad"], boxstyle="round,pad=0.3"))
    y = np.arange(len(lw))
    a2.barh(y, [F(r, "Z2_over_Z1") for r in lw], .42, color=C["z2"], label="Z2 / Z1")
    a2.barh(y + .42, [F(r, "Z4_over_Z1") for r in lw], .42, color=C["z4"], label="Z4 / Z1")
    a2.axvline(1, color="k", lw=1.2)
    a2.set_yticks(y + .21)
    a2.set_yticklabels([r["law"].split(",")[0].replace("Syed 2004 corrected", "Syed")
                        + ("\n" + r["law"].split("(")[-1].rstrip(")") if "(" in r["law"] else "")
                        for r in lw], fontsize=7.2)
    a2.invert_yaxis(); a2.set_xlabel("relative life vs Z1"); a2.legend(fontsize=8)
    a2.set_xlim(0, 1.65)
    rr = [F(r, "Z2_over_Z1") for r in lw]
    a2.axvspan(min(rr), max(rr), color=C["ok"], alpha=.13)
    a2.set_title(f"RELATIVE life: ROBUST across every law\nZ2/Z1 = {min(rr):.2f}–{max(rr):.2f}",
                 fontweight="bold", fontsize=9)
    fig.suptitle("FIG-0JR-F  Life prediction by admissible primary law",
                 fontweight="bold", fontsize=10)
    fig.savefig(OUT / "FIG_0JR_F_life_by_primary_law.png"); plt.close(fig)


def fig_G():
    """Electrical penalty versus experimentally mapped relative life."""
    arch = {r["arch"][5:7]: r for r in rows("architecture_after_metric_matching.csv")}
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.8, 4.3))
    for s, r in arch.items():
        a1.plot(F(r, "P_elec_total_w"), F(r, "rel_life_vs_Z1_syed_strain"), "o", ms=13,
                color=CC[s], mec="k", mew=.8)
        a1.annotate(f"{SH[s]}\n{F(r,'P_elec_total_w'):.2f} W\n"
                    f"{F(r,'rel_life_vs_Z1_syed_strain'):.3f}×",
                    (F(r, "P_elec_total_w"), F(r, "rel_life_vs_Z1_syed_strain")),
                    textcoords="offset points", xytext=(12, -6), fontsize=8,
                    color=CC[s], fontweight="bold")
    a1.axhline(1, color="k", ls=":", lw=1)
    a1.set_xlim(125.5, 128.9); a1.set_ylim(.88, 1.45)
    a1.set_xlabel("total electrical loss (W, SYSTEM)")
    a1.set_ylabel("relative fatigue life vs Z1")
    a1.set_title("the ETM trade, on a primary-source calibration", fontweight="bold", fontsize=9)
    ec = [r for r in rows("electrical_cost_revised.csv") if r["comparison"].startswith("Z2")]
    x = np.arange(len(ec))
    a2.bar(x, [F(r, "life_multiple") for r in ec], .5,
           color=[C["corr"], C["warn"], C["z1"]])
    a2.axhline(1, color="k", lw=1)
    for i, r in enumerate(ec):
        a2.text(i, F(r, "life_multiple") + .012, f"{F(r,'life_multiple'):.3f}", ha="center",
                fontsize=8.6, fontweight="bold")
    a2.set_xticks(x); a2.set_xticklabels([r["law"].replace(" (", "\n(") for r in ec], fontsize=7.4)
    a2.set_ylim(0, 1.55); a2.set_ylabel("life multiple for $+$1.688 W")
    a2.set_title("Z1 $\\rightarrow$ Z2: what 1.688 W actually buys",
                 fontweight="bold", fontsize=9)
    a2.text(.5, .08, "+1.688 W (1.3 % of 126.1 W) buys 1.21–1.38× fatigue life",
            transform=a2.transAxes, ha="center", fontsize=8.6, color=C["ink"],
            bbox=dict(fc="#eceff1", ec=C["ink"], boxstyle="round,pad=0.35"))
    fig.suptitle("FIG-0JR-G  Electrical penalty versus experimentally mapped relative life",
                 fontweight="bold", fontsize=10)
    fig.savefig(OUT / "FIG_0JR_G_electrical_vs_life.png"); plt.close(fig)


if __name__ == "__main__":
    for f in (fig_A, fig_B, fig_C, fig_D, fig_E, fig_F, fig_G):
        f(); print("  ok", f.__name__)
    for p in sorted(OUT.glob("FIG_0JR_*.png")):
        print(f"  {p.name:44} {p.stat().st_size:>8} B")
