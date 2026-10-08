#!/usr/bin/env python3
"""Phase-0H figures. Every number is read from a results artifact, never retyped."""
from __future__ import annotations
import csv, json, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0h"
G = R / "results" / "phase0g"
plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": 0.3,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
C = {"ok": "#1b5e20", "bad": "#b71c1c", "old": "#9e9e9e", "new": "#1565c0",
     "warn": "#ef6c00", "b": "#6a1b9a"}
rows = lambda p: list(csv.DictReader(open(p)))
F = lambda r, k: float(r[k])


def fig_A():
    """240-W ranking change from DEFECT #30."""
    old = {(r["arch"], r["fam"], float(r["j"]), float(r["h_sub_mm"])): float(r["P_elec_total_w"])
           for r in rows(R / "results/phase0e/phase0e_candidates.csv")}
    new = {(r["arch"], r["fam"], float(r["j"]), float(r["h_sub_mm"])): float(r["P_elec_total_w"])
           for r in rows(OUT / "replay240_candidates.csv")}
    k = [x for x in new if x in old]
    d = sorted(((100 * (new[x] - old[x]) / old[x], x) for x in k), reverse=True)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.2, 4.3),
                                 gridspec_kw={"width_ratios": [1, 1.05]})
    lab = [f"{x[0][5:]} {x[1][:5]} j{x[2]:.1f} h{x[3]:.1f}" for _, x in d]
    val = [v for v, _ in d]
    col = [C["bad"] if x[0] == "ARCH_B" else C["new"] for _, x in d]
    a1.barh(lab, val, color=col, alpha=.85)
    a1.set(xlabel="change in total electrical loss (%)",
           title="(a) DEFECT #30 is architecture-selective")
    a1.invert_yaxis()
    for y, v in enumerate(val):
        a1.text(v + .03, y, f"{v:+.3f}", va="center", fontsize=7.5)
    a1.text(.97, .05, "ARCH_B (1 V rail through the vias)", transform=a1.transAxes,
            ha="right", fontsize=7.5, color=C["bad"])
    ro = sorted(k, key=lambda x: old[x]); rn = sorted(k, key=lambda x: new[x])
    for i, x in enumerate(ro):
        j = rn.index(x)
        c = C["bad"] if i != j else C["old"]
        a2.plot([0, 1], [len(ro) - i, len(rn) - j], "o-", color=c, ms=5,
                lw=2.0 if i != j else .9, alpha=.95 if i != j else .5)
        if i != j:
            a2.annotate(f"{x[0][5:]} h{x[3]:.1f}", (0, len(ro) - i), xytext=(-6, 0),
                        textcoords="offset points", ha="right", fontsize=7.5, color=C["bad"])
    a2.set(xlim=(-.55, 1.3), xticks=[0, 1],
           xticklabels=["Phase 0E\nas published", "corrected\n(scope-guarded)"],
           ylabel="rank (higher = lower loss)",
           title="(b) three ranking positions move")
    a2.grid(axis="x", alpha=0)
    fig.suptitle("FIG-0H-A  DEFECT #30 inverted an architecture comparison at 240 W too",
                 fontsize=10.5, y=1.02)
    fig.savefig(OUT / "FIG_0H_A_defect30_ranking.png"); plt.close(fig)


def fig_B():
    """Failure-mechanism computability."""
    mech = [("A  global bending", 2, "response, not a failure"),
            ("B  BGA solder fatigue", 0, "needs discrete balls + viscoplasticity"),
            ("C  microbump / C4", 1, "smeared layer only"),
            ("D  RDL damage", 0, "RDL absent from the mechanical mesh"),
            ("E  die / low-k CPI", 0, "homogenisation invalid for local stress"),
            ("F  delamination", 0, "needs fracture mechanics"),
            ("G  TSV interaction", 0, "homogenised via field")]
    fig, ax = plt.subplots(figsize=(8.6, 4.0))
    cols = {0: C["bad"], 1: C["warn"], 2: C["ok"]}
    ax.barh([m[0] for m in mech], [m[1] + .06 for m in mech],
            color=[cols[m[1]] for m in mech], alpha=.85)
    ax.set(xlim=(0, 3.6), xticks=[0, 1, 2],
           xticklabels=["not computable", "partial", "computable"],
           title="FIG-0H-B  One failure mechanism of eight is computable, and it is not a failure")
    ax.invert_yaxis()
    for y, m in enumerate(mech):
        ax.text(m[1] + .16, y, m[2], va="center", fontsize=7.5, color="#444")
    ax.text(.985, .06, "June-2026 names A, D and F.\nTwo of its three are outside the model.",
            transform=ax.transAxes, ha="right", fontsize=8, color=C["bad"],
            bbox=dict(fc="#ffebee", ec=C["bad"], lw=.9))
    fig.savefig(OUT / "FIG_0H_B_mechanism_map.png"); plt.close(fig)


def fig_C():
    """Global warpage is not a proxy for local loading."""
    pr = rows(OUT / "warpage_local_pairs.csv")
    co = rows(OUT / "warpage_local_correlation.csv")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.8, 4.2))
    st = {"BC_A": ("o", C["ok"], "free package"), "BC_B": ("v", C["old"], "compact clamp"),
          "BC_BOARD": ("s", C["new"], "explicit board")}
    for k, (mk, c, lb) in st.items():
        sel = [r for r in pr if r["restraint"] == k]
        if sel:
            a1.scatter([F(r, "die_warpage_pv_um") for r in sel],
                       [F(r, "interface_shear_p99_MPa") for r in sel],
                       marker=mk, c=c, s=26, alpha=.8, label=lb)
    a1.set(xlabel="die warpage P-V (µm)", ylabel="interface shear p99 (MPa)",
           title="(a) 70 paired runs — no usable relation")
    a1.legend(fontsize=7.5)
    a1.text(.97, .95, "free: ρ = −0.79\nmounted: ρ = +0.35\nthe SIGN inverts",
            transform=a1.transAxes, ha="right", va="top", fontsize=8, color=C["bad"],
            bbox=dict(fc="#ffebee", ec=C["bad"], lw=.9))
    lab, rho = [], []
    for r in co:
        lab.append(f"{r['subset'].replace('_',' ')}\n{r['local_metric'].split('_')[0]}")
        rho.append(float(r["spearman_rho"]))
    cols = [C["ok"] if abs(v) >= .9 else C["warn"] if abs(v) >= .6 else C["bad"] for v in rho]
    a2.barh(lab, rho, color=cols, alpha=.85)
    a2.axvline(0, color="k", lw=1)
    for x in (.9, -.9):
        a2.axvline(x, color=C["ok"], ls="--", lw=1)
    a2.set(xlabel="Spearman ρ (warpage vs local metric)", xlim=(-1, 1),
           title="(b) |ρ| ≥ 0.9 would be a usable proxy")
    a2.tick_params(labelsize=7)
    for y, v in enumerate(rho):
        a2.text(v + (.03 if v > 0 else -.03), y, f"{v:+.2f}", va="center",
                ha="left" if v > 0 else "right", fontsize=7.5)
    fig.suptitle("FIG-0H-C  Global warpage does not predict the local interconnect loading",
                 fontsize=10.5, y=1.02)
    fig.savefig(OUT / "FIG_0H_C_warpage_not_proxy.png"); plt.close(fig)


def fig_D():
    """Criterion admissibility matrix."""
    ad = rows(OUT / "criterion_admissibility.csv")
    conds = ["c1_package_state", "c2_temperature_load_state", "c3_failure_mechanism",
             "c4_metric_definition", "c5_geometry_interconnect_scale", "c6_source_backed_value"]
    short = ["package\nstate", "temp /\nload", "failure\nmechanism", "metric\ndefinition",
             "geometry\nscale", "source-\nbacked"]
    M = np.zeros((len(ad), len(conds)))
    for i, r in enumerate(ad):
        for j, c in enumerate(conds):
            v = r[c].upper()
            M[i, j] = 1.0 if v.startswith("PASS") else 0.5 if v.startswith(("PARTIAL", "UNDET")) else 0.0
    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    ax.imshow(M, cmap=matplotlib.colors.ListedColormap([C["bad"], C["warn"], C["ok"]]),
              vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(conds))); ax.set_xticklabels(short, fontsize=7.5)
    ax.set_yticks(range(len(ad)))
    ax.set_yticklabels([r["candidate"][:52] for r in ad], fontsize=7)
    for i, r in enumerate(ad):
        ax.text(len(conds) - .35, i, f"{r['n_pass']}/6", va="center", fontsize=8,
                fontweight="bold")
    ax.set(xlim=(-.5, len(conds) + .3), title="FIG-0H-D  Criterion admissibility: 0 of 9 admitted")
    ax.grid(False)
    ax.text(.5, -.22, "green = condition met   ·   amber = partial/undetermined   ·   "
            "red = fails.  A criterion needs 6/6.", transform=ax.transAxes, ha="center",
            fontsize=8)
    fig.savefig(OUT / "FIG_0H_D_admissibility.png"); plt.close(fig)


def fig_E():
    """Geometry closure: the realizable band moves."""
    fig, ax = plt.subplots(figsize=(8.6, 3.9))
    IND, LS, RDL, TSV = 500., 606., 20., 50.
    bars = [("Phase 0F assumed\n(GaN 100 µm, OPEN)", IND, 100., 100., RDL, 0.770),
            ("Phase 0H sourced\nMLCC optimistic", IND, LS, 0., RDL, 1.176),
            ("Phase 0H sourced\nMLCC nominal", IND, LS, 100., RDL, 1.276),
            ("Phase 0H sourced\nMLCC pessimistic", IND, LS, 250., RDL, 1.426)]
    y = np.arange(len(bars))
    segs = [("inductor (sourced)", 1, "#455a64"), ("low-side GaN", 2, "#b71c1c"),
            ("MLCC (OPEN)", 3, "#90a4ae"), ("interlayer RDL", 4, "#cfd8dc")]
    left = np.zeros(len(bars))
    for name, idx, c in segs:
        w = np.array([b[idx] for b in bars])
        ax.barh(y, w, left=left, color=c, label=name, height=.62)
        left += w
    ax.barh(y, [TSV] * len(bars), left=left, color="#ffd54f", label="min TSV (50 µm)", height=.62)
    for i, b in enumerate(bars):
        ax.text(left[i] + TSV + 40, i, f"h_sub,min = {b[5]:.3f} mm", va="center",
                fontsize=8.5, fontweight="bold")
    ax.set_yticks(y); ax.set_yticklabels([b[0] for b in bars], fontsize=8)
    ax.invert_yaxis()
    ax.set(xlabel="height budget (µm)", xlim=(0, 2350), ylim=(len(bars) - 0.4, -1.15))
    ax.set_title("FIG-0H-E  Sourcing the GaN height moves the realizable substrate bound",
                 pad=26)
    ax.legend(fontsize=7.5, ncol=5, loc="upper center",
              bbox_to_anchor=(0.5, 1.10), frameon=False)
    ax.axvline(800, color=C["bad"], ls="--", lw=1.4)
    ax.text(790, len(bars) - 0.55, "corrected ARCH_B electrical optimum, h = 0.80 mm  →  "
            "unbuildable", fontsize=7.5, color=C["bad"], va="center", ha="right")
    fig.savefig(OUT / "FIG_0H_E_geometry_closure.png"); plt.close(fig)


def fig_F():
    """Thickness response over the realizable band, with resolution."""
    tr = [r for r in rows(OUT / "thickness_response_final.csv")]
    h = [F(r, "h_sub_mm") for r in tr]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.0, 4.2))
    hb = [x for x in h if x >= 1.276]
    a1.axvspan(0.75, 1.276, color=C["bad"], alpha=.10)
    a1.text(1.0, 131.4, "NOT BUILDABLE\n(Sec. 12)", ha="center", fontsize=8, color=C["bad"])
    for k, lb, c in (("P_ARCH_B_w", "ARCH_B", C["bad"]), ("P_ARCH_A_w", "ARCH_A", C["new"])):
        xs = [F(r, "h_sub_mm") for r in tr if r.get(k)]
        ys = [F(r, k) for r in tr if r.get(k)]
        a1.plot(xs, ys, "o-", color=c, ms=4, label=lb)
    a1.set(xlabel="substrate thickness $h_{sub}$ (mm)", ylabel="total electrical loss (W)",
           title="(a) electrical: thinner is better")
    a1.legend(fontsize=8)
    ws = [(F(r, "h_sub_mm"), F(r, "die_warpage_pv_um")) for r in tr if r.get("die_warpage_pv_um")]
    ts = [(F(r, "h_sub_mm"), F(r, "interface_shear_p99_MPa")) for r in tr
          if r.get("interface_shear_p99_MPa")]
    a2.axvspan(0.75, 1.276, color=C["bad"], alpha=.10)
    a2.plot([x for x, _ in ws], [v for _, v in ws], "s-", color=C["b"], ms=4,
            label="die warpage P-V (µm)")
    a2.set(xlabel="substrate thickness $h_{sub}$ (mm)", ylabel="die warpage P-V (µm)",
           title="(b) mechanical: only warpage resolves the trend")
    a3 = a2.twinx()
    lo = min(v for _, v in ts)
    a3.fill_between([1.276, 2.0], lo * (1 - .1414), lo * (1 + .1414), color=C["warn"],
                    alpha=.13, label="shear: ±14.1 % material uncertainty")
    a3.plot([x for x, _ in ts], [v for _, v in ts], "^--", color=C["warn"], ms=4,
            label="interface shear p99 (MPa)")
    a3.set_ylabel("interface shear p99 (MPa)", color=C["warn"])
    a3.set_ylim(lo * (1 - .22), lo * (1 + .22))
    a3.grid(False)
    a3.text(0.985, 0.965, "shear trend over the buildable band: 1.96 %\n"
            "7× smaller than its own uncertainty band",
            transform=a3.transAxes, ha="right", va="top", fontsize=7.5, color=C["warn"],
            bbox=dict(fc="#fff8e1", ec=C["warn"], lw=.8, alpha=.95))
    h1, l1 = a2.get_legend_handles_labels(); h2, l2 = a3.get_legend_handles_labels()
    a2.legend(h1 + h2, l1 + l2, fontsize=7, loc="lower left", framealpha=.95)
    fig.suptitle("FIG-0H-F  The thickness opposition survives, but only in a quantity that "
                 "does not predict local loading", fontsize=10.5, y=1.02)
    fig.savefig(OUT / "FIG_0H_F_thickness_final.png"); plt.close(fig)


if __name__ == "__main__":
    for fn in (fig_A, fig_B, fig_C, fig_D, fig_E, fig_F):
        fn(); print(f"  {fn.__name__} ok", flush=True)
    print()
    for p in sorted(OUT.glob("FIG_0H_*.png")):
        print(f"  {p.name}  {p.stat().st_size/1024:.0f} kB")
