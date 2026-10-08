#!/usr/bin/env python3
"""Phase-0D-R figures B, C, F, G, H."""
from __future__ import annotations
import csv, json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0dr"
DV, GEN, OLD = "#c0392b", "#2c5f8a", "#95a5a6"


def load():
    rows = list(csv.DictReader((OUT / "coupled_candidates_corrected.csv").open()))
    for r in rows:
        for k, v in r.items():
            if k not in ("case", "arch", "fam", "placement", "tsv_rail", "feasible"):
                try: r[k] = float(v)
                except (TypeError, ValueError): pass
    return rows


def pick(rows, **kw):
    for r in rows:
        if all(str(r[k]) == str(v) for k, v in kw.items()):
            return r
    return None


def fig_B(rows):
    """Interconnect loss decomposition."""
    sel = [("distributed", "ARCH_A", 2.0, 0.5), ("edge", "ARCH_A", 2.0, 0.5),
           ("compact", "ARCH_A", 2.0, 0.5), ("asymmetric", "ARCH_A", 2.0, 0.5),
           ("distributed", "ARCH_B", 2.0, 0.5)]
    labs, data = [], []
    for fam, arch, j, h in sel:
        r = pick(rows, fam=fam, arch=arch, j=j, h_sub_mm=h)
        if not r: continue
        labs.append(f"{arch.replace('ARCH_','')}\n{fam}")
        data.append([r["P_conv_w"], r["P_rdl_w"], r["P_microbump_w"],
                     r["P_tsv_w"], r["P_bga_w"], r["P_c4_w"]])
    data = np.array(data).T
    names = ["converter", "RDL (lateral sheet)", "micro-bump", "TSV", "BGA", "C4"]
    cols = ["#d9534f", "#2c5f8a", "#f0ad4e", "#5cb85c", "#8e6cb0", "#7f8c8d"]
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.6), dpi=150)
    x = np.arange(len(labs)); bot = np.zeros(len(labs))
    for d, nm, c in zip(data, names, cols):
        axes[0].bar(x, d, 0.62, bottom=bot, label=nm, color=c, edgecolor="k", lw=0.5)
        bot += d
    for i, t in enumerate(bot):
        axes[0].text(i, t + 1.5, f"{t:.1f} W", ha="center", fontsize=8.5, weight="bold")
    axes[0].set_xticks(x); axes[0].set_xticklabels(labs, fontsize=8.5)
    axes[0].set_ylabel("power loss (W)", fontsize=10)
    axes[0].set_title("B1. Where the power actually goes\n"
                      "Lateral RDL, not the TSV, dominates package distribution", fontsize=10.5)
    axes[0].legend(fontsize=8, ncol=2); axes[0].grid(axis="y", alpha=0.3)

    ax = axes[1]
    tiers = ["RDL", "micro-bump", "TSV (ARCH_A, HV)", "TSV (ARCH_B, LV)", "BGA", "C4"]
    a = pick(rows, fam="distributed", arch="ARCH_A", j=2.0, h_sub_mm=0.5)
    b = pick(rows, fam="distributed", arch="ARCH_B", j=2.0, h_sub_mm=0.5)
    vals = [a["P_rdl_w"], a["P_microbump_w"], a["P_tsv_w"], b["P_tsv_w"], a["P_bga_w"], a["P_c4_w"]]
    vals = [max(v, 1e-9) for v in vals]
    c = [GEN, "#f0ad4e", "#5cb85c", DV, "#8e6cb0", "#7f8c8d"]
    ax.barh(range(len(tiers)), vals, color=c, edgecolor="k", lw=0.6)
    for i, v in enumerate(vals):
        ax.text(v * 1.4, i, f"{v*1e3:.2f} mW" if v < 1 else f"{v:.2f} W", va="center", fontsize=8.5)
    ax.set_yticks(range(len(tiers))); ax.set_yticklabels(tiers, fontsize=9)
    ax.set_xscale("log"); ax.invert_yaxis()
    ax.set_xlabel("loss (W, log scale)", fontsize=10)
    ax.set_title("B2. Per-tier loss spans five decades\n"
                 "The LV-rail TSV is 45x the HV-rail TSV, still far below RDL", fontsize=10.5)
    ax.grid(axis="x", alpha=0.3)
    fig.suptitle("Figure B - Phase-0D-R interconnect loss decomposition (240 W load, J=2, "
                 "h$_{sub}$=500 um).  Source: coupled_candidates_corrected.csv", fontsize=11.5)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(OUT / "FIG_B_loss_decomposition.png", bbox_inches="tight"); plt.close(fig)


def fig_C(rows):
    """HV vs LV TSV thickness chain."""
    fig, axes = plt.subplots(1, 5, figsize=(20, 4.2), dpi=145)
    series = [("R$_{TSV}$ loop", "P_tsv_w", 1e3, "mW"), ("P$_{TSV}$", "P_tsv_w", 1e3, "mW"),
              ("P$_{elec,total}$", "P_elec_total_w", 1, "W"),
              ("T$_{max}$", "T_max_C", 1, "°C"), ("die warpage", "die_warpage_pv_um", 1, "um")]
    for ax, (lab, key, sc, unit) in zip(axes, series):
        for arch, col, mk in (("ARCH_A", "#c0392b", "o"), ("ARCH_B", "#2c5f8a", "s")):
            xs, ys = [], []
            for h in (0.2, 0.5):
                r = pick(rows, fam="distributed", arch=arch, j=2.0, h_sub_mm=h)
                if r: xs.append(h * 1000); ys.append(r[key] * sc)
            rail = "48 V (HV)" if arch == "ARCH_A" else "1 V (LV)"
            ax.plot(xs, ys, mk + "-", color=col, lw=2.2, ms=8, label=f"{arch} - TSV {rail}")
        ax.set_xlabel("$h_{sub}$ (um)", fontsize=10); ax.set_ylabel(f"{lab} ({unit})", fontsize=10)
        ax.set_xticks([200, 500]); ax.grid(alpha=0.3); ax.set_title(lab, fontsize=10)
    axes[0].legend(fontsize=8)
    fig.suptitle("Figure C - HV-TSV vs LV-TSV thickness chain.  The LV-rail TSV penalty is 45x "
                 "larger (0.76 -> 34.2 mW) yet total electrical loss still FALLS with thickness "
                 "in both architectures.\nNo architecture-dependent three-domain tradeoff at this "
                 "scale.  Source: coupled_candidates_corrected.csv", fontsize=11.5, y=1.06)
    fig.tight_layout()
    fig.savefig(OUT / "FIG_C_hv_lv_thickness.png", bbox_inches="tight"); plt.close(fig)


def fig_F(rows):
    """Footprint tradeoff."""
    js = [4.0, 2.0, 1.5]
    r = [pick(rows, fam="distributed", arch="ARCH_A", j=j, h_sub_mm=0.5) for j in js]
    A = [x["a_hvr_total_mm2"] for x in r]
    fig, axes = plt.subplots(1, 4, figsize=(17, 4.2), dpi=145)
    for ax, (key, lab, col) in zip(axes, [("P_elec_total_w", "P$_{elec,total}$ (W)", DV),
                                          ("efficiency_pct", "efficiency (%)", DV),
                                          ("T_max_C", "T$_{max}$ (°C)", "#1a7a3c"),
                                          ("die_warpage_pv_um", "die warpage (um)", GEN)]):
        ax.plot(A, [x[key] for x in r], "o-", color=col, lw=2.2, ms=9)
        for a, x in zip(A, r):
            ax.annotate(f"J={x['j']:g}", (a, x[key]), textcoords="offset points",
                        xytext=(6, -12), fontsize=8)
        ax.set_xlabel("total HVR footprint (mm$^2$)", fontsize=10)
        ax.set_ylabel(lab, fontsize=10); ax.grid(alpha=0.3)
    axes[0].set_title("larger footprint -> lower loss", fontsize=10, color=DV)
    axes[3].set_title("...but higher warpage", fontsize=10, color=GEN)
    fig.suptitle("Figure F - HVR footprint tradeoff after the PPDN correction.  Larger footprint "
                 "now improves converter loss, RDL spreading loss AND temperature, while worsening "
                 "warpage:\n-54% loss for +84% warpage = 17.0 W/um.  Source: coupled_candidates_corrected.csv",
                 fontsize=11.5, y=1.06)
    fig.tight_layout()
    fig.savefig(OUT / "FIG_F_footprint.png", bbox_inches="tight"); plt.close(fig)


def fig_G(rows):
    """Corrected ET vs ETM Pareto."""
    rev = json.loads((OUT / "reversal_corrected.json").read_text())
    P = np.array([r["P_elec_total_w"] for r in rows])
    W = np.array([r["die_warpage_pv_um"] for r in rows])
    fig, ax = plt.subplots(figsize=(9.5, 7), dpi=150)
    sc = ax.scatter(P, W, c=[r["a_hvr_total_mm2"] for r in rows], s=150, cmap="viridis",
                    edgecolor="k", lw=0.8, zorder=3)
    for r, p, w in zip(rows, P, W):
        ax.annotate(r["case"].replace("ARCH_", "").replace("_distributed", "/dist")
                    .replace("_asymmetric", "/asym").replace("_edge", "/edge")
                    .replace("_compact", "/comp"), (p, w),
                    textcoords="offset points", xytext=(7, -4), fontsize=6.8)
    for c in rev["etm_pareto"]:
        r = pick(rows, case=c)
        ax.scatter(r["P_elec_total_w"], r["die_warpage_pv_um"], s=460, facecolors="none",
                   edgecolors=DV, lw=2.2, ls="--", zorder=4)
    r = pick(rows, case=rev["et_best"])
    ax.scatter(r["P_elec_total_w"], r["die_warpage_pv_um"], s=300, facecolors="none",
               edgecolors=GEN, lw=2.8, zorder=5)
    ax.annotate("", xy=(57.18, 1.846), xytext=(25.11, 3.831),
                arrowprops=dict(arrowstyle="->", lw=2.0, color="k", ls=":"))
    ax.text(41, 2.5, "+32.07 W (+128 %)\n-1.985 um (-52 %)\n= 16.2 W/um\n(Phase 0D said 2.03)",
            fontsize=9, ha="center",
            bbox=dict(fc="w", ec="k", alpha=0.9, boxstyle="round,pad=0.4"))
    plt.colorbar(sc, ax=ax, label="total HVR footprint (mm$^2$)")
    ax.set_xlabel("$P_{elec,total}$ (W)  -  ET objective", fontsize=11)
    ax.set_ylabel("die warpage p-v (um)  -  mechanical objective", fontsize=11)
    ax.set_title("Figure G - corrected ET vs ETM Pareto.\nBlue ring = ET optimum (single point); "
                 "red dashed = ETM Pareto front (4 members, all $h_{sub}$=500 um)", fontsize=11)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "FIG_G_pareto_corrected.png", bbox_inches="tight"); plt.close(fig)


def fig_H(rows):
    """Phase 0D vs Phase 0D-R conclusion changes."""
    items = [("Lateral RDL loss\n(distributed)", 0.17, 12.13, "W", True),
             ("Electrical spread\nacross placements", 1.08, 188.8, "%", True),
             ("ET->min-warpage\nexchange rate", 2.03, 16.2, "W/um", True),
             ("TSV thickness penalty\n(LV rail, ARCH_B)", 0.76, 34.2, "mW", True),
             ("Thickness benefit\n(warpage)", 57.0, 56.5, "%", False)]
    fig, ax = plt.subplots(figsize=(12.5, 6.2), dpi=150)
    y = np.arange(len(items)); w = 0.36
    old = [i[1] for i in items]; new = [i[2] for i in items]
    ax.barh(y - w/2, old, w, color=OLD, edgecolor="k", lw=0.6, label="Phase 0D")
    ax.barh(y + w/2, new, w, color=DV, edgecolor="k", lw=0.6, label="Phase 0D-R (corrected)")
    for i, (lab, o, n, u, changed) in enumerate(items):
        ax.text(o * 1.15 + 0.4, i - w/2, f"{o:g} {u}", va="center", fontsize=8.5)
        ax.text(n * 1.15 + 0.4, i + w/2, f"{n:g} {u}", va="center", fontsize=8.5,
                weight="bold" if changed else "normal")
    ax.set_yticks(y); ax.set_yticklabels([i[0] for i in items], fontsize=9.5)
    ax.set_xscale("symlog", linthresh=0.5); ax.invert_yaxis()
    ax.set_xlabel("value (log scale; units differ per row)", fontsize=10)
    ax.set_title("Figure H - what Phase 0D-R changed.  Four of five headline quantities moved by "
                 "an order of magnitude;\nonly the thickness benefit is unchanged.", fontsize=11.5)
    ax.legend(fontsize=10); ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "FIG_H_phase0d_vs_0dr.png", bbox_inches="tight"); plt.close(fig)


if __name__ == "__main__":
    rows = load()
    fig_B(rows); fig_C(rows); fig_F(rows); fig_G(rows); fig_H(rows)
    for f in ("FIG_B_loss_decomposition", "FIG_C_hv_lv_thickness", "FIG_F_footprint",
              "FIG_G_pareto_corrected", "FIG_H_phase0d_vs_0dr"):
        print(f"wrote {OUT/(f+'.png')}")
