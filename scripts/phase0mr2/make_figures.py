#!/usr/bin/env python3
"""Phase-0M-R2 figures. Each answers a question; none is decorative."""
from __future__ import annotations
import csv, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                          # noqa: E402
import numpy as np                                                       # noqa: E402
import yaml                                                              # noqa: E402

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr2"
BASE = OUT / "_baseline_phase0mr"
sys.path.insert(0, str(R / "scripts" / "phase0mr2"))
plt.rcParams.update({"figure.dpi": 150, "savefig.bbox": "tight", "font.size": 8,
                     "axes.grid": True, "grid.alpha": 0.3})

C = {"Z1": "#1b6ca8", "Z2": "#c0392b", "Z4": "#27ae60"}


def rd(p, n=None):
    q = Path(p) / n if n else Path(p)
    return list(csv.DictReader(q.open())) if q.is_file() else []


def ff(r, k, d=float("nan")):
    try:
        return float(r[k])
    except (KeyError, TypeError, ValueError):
        return d


# ------------------------------------------------------------------ A: z-stacks
def fig_a():
    import arch_geometry as AG
    import production_et as PE
    fig, axes = plt.subplots(1, 3, figsize=(11, 5.2), sharey=True)
    for ax, (arch, h) in zip(axes, (("ARCH_Z1_EMBEDDED", 1.30),
                                    ("ARCH_Z2_BACKSIDE", 0.30),
                                    ("ARCH_Z4_POWER_DIE", 0.30))):
        m, _, _, _ = PE.build_global(arch, h)
        conv = PE.converter_layer(arch, m)
        conv = (conv,) if isinstance(conv, str) else conv
        s = AG.span(arch)
        for L in m.layers:
            col = ("#e74c3c" if L.name in conv else
                   "#95a5a6" if L.name in ("board", "bga") else
                   "#f39c12" if L.name == "die" else
                   "#3498db" if L.name == "tim" else "#ecf0f1")
            ax.add_patch(plt.Rectangle((0, L.z0), 1, L.z1 - L.z0, fc=col, ec="k", lw=.4))
            if L.z1 - L.z0 > 0.06:
                ax.text(.5, (L.z0 + L.z1) / 2, L.name, ha="center", va="center", fontsize=5.5)
        ax.add_patch(plt.Rectangle((1.05, s.z_start_um * 1e-3), .18,
                                   s.length_um * 1e-3, fc="#8e44ad", ec="k", lw=.5))
        ax.text(1.14, (s.z_start_um + s.length_um / 2) * 1e-3,
                "TSV\n%.0f um\nAR %.2f" % (s.length_um, s.aspect_ratio),
                ha="center", va="center", fontsize=5.5, rotation=90)
        top = max(L.z1 for L in m.layers)
        ax.axhline(top, color="#2980b9", lw=2)
        ax.text(.5, top + .06, "cooled face", ha="center", fontsize=6, color="#2980b9")
        ax.set(xlim=(-.05, 1.3), title=arch.replace("ARCH_", ""), xticks=[])
    axes[0].set_ylabel("z (mm)")
    fig.suptitle("FIG-0MR2-A  architecture z-stacks with the REAL TSV span and the cooled "
                 "face\nARCH_Z4's power die is explicit geometry, not a substituted heat "
                 "source", fontsize=9)
    fig.savefig(OUT / "FIG_0MR2_A_zstacks.png"); plt.close(fig)


# ------------------------------------------------------------------ B: TSV feasibility
def fig_b():
    g = rd(OUT, "tsv_geometry_by_architecture.csv")
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    names = [r["arch"].replace("ARCH_", "") for r in g]
    L = [ff(r, "length_um") for r in g]
    ar = [ff(r, "aspect_ratio") for r in g]
    x = np.arange(len(g))
    ax[0].bar(x, L, .55, color=["#1b6ca8", "#c0392b", "#27ae60", "#7f8c8d"][:len(g)])
    ax[0].axhline(1300, ls="--", c="k", lw=1)
    ax[0].text(len(g) - .5, 1320, "the 1300 um rung Phase 0M-R swept\nbelongs to NO "
               "architecture", ha="right", fontsize=6)
    for i, (l, n) in enumerate(zip(L, names)):
        ax[0].text(i, l + 30, "%.0f" % l, ha="center", fontsize=7)
    ax[0].set(ylabel="actual TSV span (um)", ylim=(0, 1500),
              title="B1  what each architecture really traverses")
    ax[0].set_xticks(x); ax[0].set_xticklabels(names, fontsize=6.5, rotation=12)
    ax[1].bar(x, ar, .55, color=["#1b6ca8", "#c0392b", "#27ae60", "#7f8c8d"][:len(g)])
    ax[1].axhline(10.0, color="#c0392b", lw=2)
    ax[1].text(.02, 10.5, "AR_max = 10:1 (June-2026 Table III)", fontsize=6.5,
               color="#c0392b", transform=ax[1].get_yaxis_transform())
    for i, a_ in enumerate(ar):
        ax[1].text(i, a_ + .3, "%.2f" % a_, ha="center", fontsize=7)
    ax[1].set(ylabel="aspect ratio L/d", ylim=(0, 13),
              title="B2  three of four sit EXACTLY on the limit")
    ax[1].set_xticks(x); ax[1].set_xticklabels(names, fontsize=6.5, rotation=12)
    fig.suptitle("FIG-0MR2-B  TSV vertical span and aspect-ratio feasibility, "
                 "by architecture", fontsize=9)
    fig.savefig(OUT / "FIG_0MR2_B_tsv_feasibility.png"); plt.close(fig)


# ------------------------------------------------------------------ C: cooling regime map
def fig_c():
    import cooling_regime as CR
    c = CR.cfg()
    md = np.logspace(np.log10(0.5), np.log10(120), 160)
    Re, h, dp, pw, dom = [], [], [], [], []
    for m in md:
        r = CR.evaluate(float(m), c, strict=False)
        Re.append(r["Re"]); h.append(r.get("h_effective_W_m2K", np.nan))
        dp.append(r.get("dp_MPa", np.nan)); pw.append(r.get("P_pump_hydraulic_W", np.nan))
        dom.append(r["in_domain"])
    Re = np.array(Re)
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))
    for a in ax:
        a.axvspan(2300, 3000, color="#c0392b", alpha=.18, zorder=0)
    ax[0].plot(md, Re, color="#1b6ca8", lw=1.6)
    ax[0].axhline(2300, ls="--", c="#e67e22"); ax[0].axhline(3000, ls="--", c="#c0392b")
    ax[0].text(.6, 2400, "laminar ceiling 2300", fontsize=6, color="#e67e22")
    ax[0].text(.6, 3150, "Gnielinski floor 3000", fontsize=6, color="#c0392b")
    ax[0].set(xscale="log", yscale="log", xlabel="total mass flow (g/s)", ylabel="Re",
              title="C1  regime map")
    for a, y, lab in ((ax[1], h, "h_effective (W/m2K)"),
                      (ax[2], pw, "hydraulic pumping (W)")):
        y = np.array(y, float)
        a.plot(md[np.array(dom)], y[np.array(dom)], color="#27ae60", lw=1.6,
               label="inside a validated correlation")
        a.plot(md[~np.array(dom)], y[~np.array(dom)], color="#c0392b", lw=1.6, ls=":",
               label="OUT_OF_MODEL_DOMAIN")
        a.set(xscale="log", yscale="log", xlabel="total mass flow (g/s)", ylabel=lab)
        a.legend(fontsize=5.5, loc="upper left")
    ax[1].axhline(166000, ls="--", c="k", lw=1)
    ax[1].text(.6, 175000, "retired calibrated h = 166 000", fontsize=6)
    ax[1].set_title("C2  effective h")
    ax[2].set_title("C3  pumping power")
    for a in ax:
        for mk, lab in ((1.6, "1.6"), (27.0, "27"), (50.0, "50")):
            a.axvline(mk, color="k", lw=.7, alpha=.55)
            a.text(mk, a.get_ylim()[1], lab, fontsize=6, ha="center", va="bottom")
    fig.suptitle("FIG-0MR2-C  cooling regime map. The shaded band is 2300 < Re < 3000, "
                 "where NO validated correlation exists.\nThe 50 g/s point Phase 0M-R "
                 "quoted lands inside it at Re = 2342.", fontsize=9)
    fig.savefig(OUT / "FIG_0MR2_C_cooling_regime.png"); plt.close(fig)


# ------------------------------------------------------------------ E: three phases
def fig_e():
    old = rd(BASE, "production_architecture_replay.csv")
    new = rd(OUT, "architecture_replay_0mr2.csv")

    def o(a, key):
        for r in old:
            if (r["arch"] == a and r["mode"] == "AFTER" and "27" in r.get("cooler", "")
                    and r.get("template") == "T1_EMBEDDED_4LAYER"):
                return ff(r, key)
        return np.nan

    def ob(a, key):
        for r in old:
            if r["arch"] == a and r["mode"] == "BEFORE":
                return ff(r, key)
        return np.nan

    def n(cid, key):
        return next((ff(r, key) for r in new if r["case"] == cid), np.nan)

    arches = [("ARCH_Z1_EMBEDDED", "Z1", "Z1"), ("ARCH_Z2_BACKSIDE", "Z2", "Z2"),
              ("ARCH_Z4_POWER_DIE", "Z4", "Z4_stacked")]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.0))
    for j, (key, lab) in enumerate((("T_max_C", "peak temperature (C)"),
                                    ("du_corner_um", "corner-joint driver (um)"))):
        x = np.arange(3)
        b0 = [ob(a, key) for a, _, _ in arches]
        b1 = [o(a, key) for a, _, _ in arches]
        b2 = [n(c, key) for _, _, c in arches]
        ax[j].bar(x - .26, b0, .25, label="Phase 0M", color="#bdc3c7")
        ax[j].bar(x, b1, .25, label="Phase 0M-R", color="#7f8c8d")
        ax[j].bar(x + .26, b2, .25, label="Phase 0M-R2", color="#c0392b")
        for i, v in enumerate(b2):
            ax[j].text(i + .26, v, "%.2f" % v, ha="center", va="bottom", fontsize=6)
        ax[j].set_xticks(x); ax[j].set_xticklabels([s for _, s, _ in arches])
        ax[j].set(ylabel=lab, title=lab)
        if j == 0:
            ax[j].legend(fontsize=6.5)
    fig.suptitle("FIG-0MR2-E  the frozen architectures through three successive "
                 "production paths", fontsize=9)
    fig.savefig(OUT / "FIG_0MR2_E_three_phases.png"); plt.close(fig)


# ------------------------------------------------------------------ F: the decoupling
def fig_f():
    new = rd(OUT, "architecture_replay_0mr2.csv")
    old = rd(BASE, "production_architecture_replay.csv")
    fig, ax = plt.subplots(figsize=(6.6, 5.2))
    for r in new:
        cid = r["case"]
        col = C.get(cid[:2], "#7f8c8d")
        mk = "o" if "planar" not in cid else "s"
        ax.scatter(ff(r, "T_max_C"), ff(r, "du_corner_um"), s=150, c=col, marker=mk,
                   edgecolor="k", zorder=3)
        ax.annotate(cid, (ff(r, "T_max_C"), ff(r, "du_corner_um")),
                    textcoords="offset points", xytext=(9, 5), fontsize=7)
    for r in old:
        if r["mode"] == "AFTER" and "27" in r.get("cooler", "") \
                and r.get("template") == "T1_EMBEDDED_4LAYER":
            ax.scatter(ff(r, "T_max_C"), ff(r, "du_corner_um"), s=70,
                       c="none", edgecolor=C.get(r["arch"].replace("ARCH_", "")[:2],
                                                 "#7f8c8d"),
                       marker="o", zorder=2, alpha=.75)
            ax.annotate("0M-R", (ff(r, "T_max_C"), ff(r, "du_corner_um")),
                        textcoords="offset points", xytext=(6, -11), fontsize=5.5,
                        alpha=.8)
    z1 = next((ff(r, "du_corner_um") for r in new if r["case"] == "Z1"), np.nan)
    z2 = next((ff(r, "du_corner_um") for r in new if r["case"] == "Z2"), np.nan)
    t1 = next((ff(r, "T_max_C") for r in new if r["case"] == "Z1"), np.nan)
    t2 = next((ff(r, "T_max_C") for r in new if r["case"] == "Z2"), np.nan)
    ax.annotate("", xy=(t2, z2), xytext=(t1, z1),
                arrowprops=dict(arrowstyle="<|-|>", color="#c0392b", lw=1.4, ls="--"))
    ax.text((t1 + t2) / 2, (z1 + z2) / 2 + .06,
            "Z2 is %.1f K HOTTER\nand carries %.1f %% LESS driver"
            % (t2 - t1, 100 * (z1 - z2) / z1), fontsize=7, color="#c0392b", ha="center")
    ax.set(xlabel="package peak temperature (C)",
           ylabel="corner-joint driver, $\\Delta u$ (um)",
           title="FIG-0MR2-F  ranking by T_max is not ranking by the fatigue driver\n"
                 "filled = Phase 0M-R2, hollow = Phase 0M-R; square = Z4 planar bound")
    fig.savefig(OUT / "FIG_0MR2_F_decoupling.png"); plt.close(fig)


if __name__ == "__main__":
    only = sys.argv[1:] or ["a", "b", "c", "e", "f"]
    for k in only:
        fn = globals().get("fig_" + k)
        if fn is None:
            raise SystemExit("no figure " + k)
        fn(); print("  FIG-0MR2-" + k.upper())
    print("done")
