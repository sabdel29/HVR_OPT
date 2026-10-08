#!/usr/bin/env python3
"""Phase-0D figures."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

R = Path(__file__).resolve().parents[2]
P0D = R / "results" / "phase0d"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_reversal import load_candidates, pareto_front       # noqa: E402

DV = "#c0392b"     # DVPD-specific
GEN = "#2c5f8a"


def fig_thickness(rows):
    """h_sub -> R_tsv / P_PDN / P_conv / T_max / warpage, the Phase-0D headline chain."""
    fig, axes = plt.subplots(1, 5, figsize=(21, 4.3), dpi=145)
    groups = {}
    for r in rows:
        groups.setdefault((r["n_vr"], r["j_target"], r["placement"]), {})[r["h_sub_mm"]] = r
    pairs = [(k, g) for k, g in groups.items() if 0.2 in g and 0.5 in g]

    series = [("R_TSV field (uOhm)", "r_tsv_field_uohm", "electrical PENALTY"),
              ("P_PDN (W)", "p_pdn_w", "electrical"),
              ("P_conv (W)", "p_conv_total_w", "electrical BENEFIT"),
              ("T_max (C)", "T_max_C", "thermal BENEFIT"),
              ("die warpage p-v (um)", "die_warpage_pv_um", "mechanical BENEFIT")]

    for ax, (lab, key, tag) in zip(axes, series):
        for k, g in pairs:
            n, j, pl = k
            ls = "-" if pl == "distributed_2x2" else "--"
            ax.plot([200, 500], [g[0.2][key], g[0.5][key]], ls, marker="o", ms=6,
                    alpha=0.8, label=f"N{int(n)} J{j:g} {pl[:11]}")
        ax.set_xlabel("$h_{sub}$ (um)", fontsize=10)
        ax.set_ylabel(lab, fontsize=10)
        ax.set_xticks([200, 500])
        col = DV if "PENALTY" in tag else ("#1a7a3c" if "BENEFIT" in tag else "0.3")
        ax.set_title(f"{lab}\n{tag}", fontsize=10, color=col)
        ax.grid(alpha=0.3)
    axes[0].legend(fontsize=6.0, ncol=2, loc="upper left")

    fig.suptitle("Phase 0D - substrate thickness propagated through the coupled model.  "
                 "h_sub raises TSV resistance (the only direct electrical penalty) but lowers "
                 "temperature, which lowers converter loss.\nThe thermal benefit outweighs the "
                 "resistive penalty, so thicker substrate is better ELECTRICALLY, THERMALLY and "
                 "MECHANICALLY - there is no tradeoff on this lever.", fontsize=11.5, y=1.06)
    fig.tight_layout()
    p = P0D / "PHASE0D_THICKNESS_TRADEOFF.png"
    fig.savefig(p, bbox_inches="tight"); plt.close(fig)
    print(f"wrote {p}")


def fig_pareto(rows):
    fig, axes = plt.subplots(1, 2, figsize=(15.5, 6.4), dpi=145)
    P = np.array([r["p_elec_total_w"] for r in rows])
    W = np.array([r["die_warpage_pv_um"] for r in rows])
    T = np.array([r["T_max_C"] for r in rows])
    A = np.array([r["a_hvr_total_mm2"] for r in rows])
    H = np.array([r["h_sub_mm"] for r in rows])

    et = pareto_front([(p, t) for p, t in zip(P, T)])
    etm = pareto_front([(p, t, w) for p, t, w in zip(P, T, W)])

    ax = axes[0]
    sc = ax.scatter(P, W, c=A, s=110, cmap="viridis", edgecolor="k", linewidth=0.7, zorder=3)
    for i in et:
        ax.scatter(P[i], W[i], s=330, facecolors="none", edgecolors="#2c5f8a", linewidth=2.6,
                   zorder=4, label="ET Pareto" if i == et[0] else None)
    for i in etm:
        ax.scatter(P[i], W[i], s=520, facecolors="none", edgecolors="#c0392b", linewidth=2.0,
                   linestyle="--", zorder=4, label="ETM Pareto" if i == etm[0] else None)
    for i, r in enumerate(rows):
        ax.annotate(r["cand"], (P[i], W[i]), textcoords="offset points", xytext=(7, -3),
                    fontsize=6.5)
    plt.colorbar(sc, ax=ax, label="total HVR footprint (mm$^2$)")
    ax.set_xlabel("$P_{elec,total}$ (W)  - ET objective, minimise", fontsize=11)
    ax.set_ylabel("die warpage p-v (um)  - mechanical objective, minimise", fontsize=11)
    ax.set_title("ET vs ETM Pareto fronts\ncolour = HVR footprint, the lever that opposes",
                 fontsize=11)
    ax.legend(fontsize=9); ax.grid(alpha=0.3)

    ax = axes[1]
    for h, mk, lab in ((0.200, "o", "$h_{sub}$ = 200 um"), (0.500, "s", "$h_{sub}$ = 500 um")):
        m = H == h
        ax.scatter(P[m], W[m], marker=mk, s=120, c=A[m], cmap="viridis",
                   edgecolor="k", linewidth=0.7, label=lab)
    for key, grp in {}.items():
        pass
    # connect footprint series at fixed h and placement
    byk = {}
    for i, r in enumerate(rows):
        byk.setdefault((r["n_vr"], r["h_sub_mm"], r["placement"]), []).append(i)
    for k, idx in byk.items():
        if len(idx) < 2:
            continue
        idx = sorted(idx, key=lambda i: A[i])
        ax.plot(P[idx], W[idx], "-", color="0.55", lw=1.0, alpha=0.8, zorder=1)
    ax.set_xlabel("$P_{elec,total}$ (W)", fontsize=11)
    ax.set_ylabel("die warpage p-v (um)", fontsize=11)
    ax.set_title("Grey lines follow the HVR-footprint sweep at fixed N, $h_{sub}$, placement\n"
                 "Down-right = larger footprint: lower loss, higher warpage", fontsize=11)
    ax.legend(fontsize=9); ax.grid(alpha=0.3)

    fig.suptitle("Phase 0D - ET vs ETM Pareto.  Adding warpage as a third objective cannot "
                 "dominate the ET optimum (it already holds minimum $P_{elec}$),\n"
                 "so the meaningful question is whether the PREFERRED LEVEL of a DVPD lever "
                 "changes - and for HVR footprint it does.", fontsize=12, y=1.02)
    fig.tight_layout()
    p = P0D / "PHASE0D_ET_VS_ETM_PARETO.png"
    fig.savefig(p, bbox_inches="tight"); plt.close(fig)
    print(f"wrote {p}")


def fig_rank(rows, rev):
    rows_s = sorted(rows, key=lambda r: r["p_elec_total_w"])
    for i, r in enumerate(rows_s, 1):
        r["_et"] = i
    for i, r in enumerate(sorted(rows_s, key=lambda r: r["die_warpage_pv_um"]), 1):
        r["_w"] = i

    fig, axes = plt.subplots(1, 2, figsize=(15.5, 7.2), dpi=145)
    ax = axes[0]
    for r in rows_s:
        col = DV if r["_w"] - r["_et"] < 0 else GEN
        ax.plot([0, 1], [r["_et"], r["_w"]], "-o", color=col, ms=5, alpha=0.75, lw=1.3)
        ax.annotate(f"{r['cand']}", (0, r["_et"]), textcoords="offset points",
                    xytext=(-34, -3), fontsize=7)
        ax.annotate(f"{r['cand']}", (1, r["_w"]), textcoords="offset points",
                    xytext=(6, -3), fontsize=7)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["rank by $P_{elec}$\n(ET only)", "rank by die warpage\n(mechanical)"],
                       fontsize=10)
    ax.invert_yaxis(); ax.set_ylabel("rank (1 = best)", fontsize=11)
    ax.set_title("Rank migration between the electrical and mechanical objectives",
                 fontsize=11)
    ax.grid(axis="y", alpha=0.3)

    ax = axes[1]
    lam = [x["lambda_W_per_um"] for x in rev["lambda_sweep"]]
    win = [x["winner"] for x in rev["lambda_sweep"]]
    uniq = sorted(set(win))
    ax.step(lam, [uniq.index(w) for w in win], where="post", lw=2.4, color=DV)
    ax.scatter(lam, [uniq.index(w) for w in win], s=70, color=DV, zorder=3)
    ax.set_yticks(range(len(uniq))); ax.set_yticklabels(uniq, fontsize=9)
    ax.set_xlabel("$\\lambda$  (W per um of warpage)", fontsize=11)
    ax.set_ylabel("scalarised winner", fontsize=11)
    ax.set_xscale("symlog", linthresh=0.01)
    ax.set_title("Scalarisation sensitivity (reported only; no claim rests on any $\\lambda$)\n"
                 f"winner changes with $\\lambda$: {rev['winner_changes_with_lambda']}",
                 fontsize=11)
    ax.grid(alpha=0.3)

    fig.suptitle("Phase 0D - rank comparison and scalarisation sensitivity", fontsize=12.5)
    fig.tight_layout()
    p = P0D / "PHASE0D_RANK_REVERSAL.png"
    fig.savefig(p, bbox_inches="tight"); plt.close(fig)
    print(f"wrote {p}")


def main():
    rows = [r for r in load_candidates() if r["ripple_ok"] and r["thermal_ok"]]
    rev = json.loads((P0D / "reversal_analysis.json").read_text())
    fig_thickness(rows)
    fig_pareto(rows)
    fig_rank(rows, rev)


if __name__ == "__main__":
    main()
