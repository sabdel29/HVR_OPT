#!/usr/bin/env python3
"""Phase-0M-R3 figures. Each answers a question; none is decorative."""
from __future__ import annotations
import csv, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                          # noqa: E402
import numpy as np                                                       # noqa: E402
import yaml                                                              # noqa: E402

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3"
BASE = OUT / "_baseline_phase0mr2"
for _p in ("scripts/phase0mr3", "scripts/phase0mr2", "scripts/phase0mr", "scripts/phase0m", "scripts"):
    sys.path.insert(0, str(R / _p))
plt.rcParams.update({"figure.dpi": 150, "savefig.bbox": "tight", "font.size": 8,
                     "axes.grid": True, "grid.alpha": .3})
C1, C2 = "#1b6ca8", "#c0392b"


def rd(p, n):
    q = Path(p) / n
    return list(csv.DictReader(q.open())) if q.is_file() else []


def ff(r, k, d=float("nan")):
    try:
        return float(r[k])
    except (KeyError, TypeError, ValueError):
        return d


# ------------------------------------------------------------------ A
def fig_a():
    rows = [r for r in rd(OUT, "realizability_failure_matrix.csv")
            if r["corner"] == "BEST" and r["template"] == "T1_EMBEDDED_4LAYER"
            and r["arch"] in ("ARCH_Z1_EMBEDDED", "ARCH_Z2_BACKSIDE")]
    names = ["area", "height", "routing", "current\ndensity", "TSV\ncount", "TSV AR"]
    keys = ["area_ratio", "height_ratio", "routing_ratio", "current_density_ratio",
            "tsv_count_ratio", "tsv_AR_ratio"]
    fig, ax = plt.subplots(figsize=(8.4, 4.0))
    x = np.arange(len(names))
    for i, r in enumerate(rows):
        v = [ff(r, k) for k in keys]
        lab = r["arch"].replace("ARCH_", "")
        b = ax.bar(x + (i - .5) * .36, v, .34, label=lab, color=[C1, C2][i])
        for xi, vi in zip(x + (i - .5) * .36, v):
            ax.text(xi, vi + .03, f"{vi:.3f}", ha="center", fontsize=6,
                    color=C2 if vi > 1 else "black")
    ax.axhline(1.0, color="k", lw=1.6)
    ax.text(len(names) - .4, 1.03, "feasibility limit", fontsize=7, ha="right")
    ax.set_xticks(x); ax.set_xticklabels(names, fontsize=7)
    ax.set(ylabel="required / available", ylim=(0, 2.1),
           title="FIG-0MR3-A  why the original Z1 and Z2 templates failed\n"
                 "T1_EMBEDDED_4LAYER at the most favourable clearance corner; "
                 "only routing exceeds 1.0")
    ax.legend(fontsize=7)
    fig.savefig(OUT / "FIG_0MR3_A_failure_margins.png"); plt.close(fig)


# ------------------------------------------------------------------ C
def fig_c():
    rows = rd(OUT, "tsv_margin_sweep.csv")
    fig, ax = plt.subplots(1, 2, figsize=(10.6, 3.9))
    for a_, arch, col in ((ax[0], "ARCH_Z1_EMBEDDED", C1), (ax[1], "ARCH_Z2_BACKSIDE", C2)):
        for case, ls in (("none", "-"), ("modest", "--"), ("loose", ":")):
            sub = sorted((r for r in rows if r["arch"] == arch
                          and r["tolerance_case"] == case),
                         key=lambda r: float(r["d_nominal_um"]))
            a_.plot([ff(r, "d_nominal_um") for r in sub],
                    [ff(r, "M_AR_worst") for r in sub], ls, color=col, marker="o",
                    ms=3, label=f"{case} bound")
        a_.axhline(1.0, color="k", lw=1.5)
        a_.text(31, 1.03, "M_AR = 1.000 is the boundary, not margin", fontsize=6.5)
        a_.axvline(30, color="#7f8c8d", lw=.9)
        a_.text(30.4, a_.get_ylim()[1] * .92, "30 um\nreference", fontsize=6)
        a_.set(xlabel="TSV diameter (um)", ylabel="design margin  M_AR = AR_max / AR",
               title=arch.replace("ARCH_", ""))
        a_.legend(fontsize=6.5)
    ax[1].axvline(34, color="#27ae60", lw=1.2, ls="--")
    ax[1].text(34.4, 1.25, "34 um restores\npositive margin", fontsize=6.5, color="#27ae60")
    fig.suptitle("FIG-0MR3-C  TSV process margin. The hard rule AR <= 10 and the design "
                 "margin are different questions.\nZ2 at 30 um has M_AR = 1.000 and fails "
                 "under a modest tolerance bound.", fontsize=9)
    fig.savefig(OUT / "FIG_0MR3_C_tsv_margin.png"); plt.close(fig)


# ------------------------------------------------------------------ D
def fig_d():
    import cooling_regime as CR
    c = CR.cfg()
    md = np.logspace(np.log10(0.5), np.log10(120), 200)
    Re, h, dom = [], [], []
    for m in md:
        r = CR.evaluate(float(m), c, strict=False)
        Re.append(r["Re"]); h.append(r.get("h_effective_W_m2K", np.nan))
        dom.append(r["in_domain"])
    Re = np.array(Re); h = np.array(h, float); dom = np.array(dom)
    fig, ax = plt.subplots(1, 2, figsize=(10.6, 3.9))
    for a_ in ax:
        a_.axvspan(2300, 3000, color=C2, alpha=.18, zorder=0)
    ax[0].plot(md, Re, color=C1, lw=1.7)
    ax[0].axhline(2300, ls="--", c="#e67e22"); ax[0].axhline(3000, ls="--", c=C2)
    ax[0].set(xscale="log", yscale="log", xlabel="total mass flow (g/s)", ylabel="Re",
              title="D1  regime map")
    ax[1].plot(md[dom], h[dom], color="#27ae60", lw=1.7, label="validated correlation")
    ax[1].plot(md[~dom], h[~dom], color=C2, lw=1.7, ls=":", label="OUT_OF_MODEL_DOMAIN")
    ax[1].set(xscale="log", yscale="log", xlabel="total mass flow (g/s)",
              ylabel="h_effective (W/m2K)", title="D2  effective h")
    ax[1].legend(fontsize=6.5, loc="upper left")
    for a_ in ax:
        a_.axvline(27.0, color="#27ae60", lw=1.4)
        a_.text(27, a_.get_ylim()[0] * 1.4, " production\n 27 g/s, Re 1265",
                fontsize=6.5, color="#27ae60")
        a_.axvline(50.0, color=C2, lw=1.2, ls="--")
        a_.text(50, a_.get_ylim()[0] * 1.4, " 50 g/s\n Re 2342", fontsize=6.5, color=C2)
    fig.suptitle("FIG-0MR3-D  cooling correlation validity. The shaded band 2300 < Re < 3000 "
                 "has NO sourced correlation;\nthe production design space is capped below "
                 "it and the production point is far inside the validated domain.",
                 fontsize=9)
    fig.savefig(OUT / "FIG_0MR3_D_cooling_validity.png"); plt.close(fig)


# ------------------------------------------------------------------ F
def fig_f():
    new = {r["case"]: r for r in rd(OUT, "final_Z1_Z2_comparison.csv")}
    old = {r["case"]: r for r in rd(BASE, "architecture_replay_0mr2.csv")}
    metrics = [("P_total_electronics_w", "P_electronics (W)"),
               ("T_max_C", "T_max (C)"), ("die_warpage_pv_um", "die warpage (um)")]
    fig, ax = plt.subplots(1, 4, figsize=(13, 3.5))
    for j, (k, lab) in enumerate(metrics):
        x = np.arange(2)
        a = [ff(old[t], k) for t in ("Z1", "Z2")]
        b = [ff(new[t], k) for t in ("Z1", "Z2")]
        ax[j].bar(x - .2, a, .38, label="0M-R2 (not buildable)", color="#95a5a6")
        ax[j].bar(x + .2, b, .38, label="0M-R3 (realizable)", color=C2)
        ax[j].set_xticks(x); ax[j].set_xticklabels(["Z1", "Z2"])
        ax[j].set(ylabel=lab, title=lab)
        if j == 0:
            ax[j].legend(fontsize=6)
    a = [ff(old[t], "du_corner_um") for t in ("Z1", "Z2")]
    b = [ff(new[t], "response_driver_um") for t in ("Z1", "Z2")]
    x = np.arange(2)
    ax[3].bar(x - .2, a, .38, color="#95a5a6")
    ax[3].bar(x + .2, b, .38, color=C2)
    for i, v in enumerate(b):
        ax[3].text(i + .2, v, f"{v:.4f}", ha="center", va="bottom", fontsize=6.5)
    ax[3].set_xticks(x); ax[3].set_xticklabels(["Z1", "Z2"])
    ax[3].set(ylabel="response driver (um)",
              title="local fatigue-relevant\ninelastic response")
    fig.suptitle("FIG-0MR3-F  Phase-0M-R2 designs against the repaired realizable pair. "
                 "The repair is one via radius; the responses barely move.", fontsize=9)
    fig.savefig(OUT / "FIG_0MR3_F_before_after.png"); plt.close(fig)


# ------------------------------------------------------------------ G
def fig_g():
    new = {r["case"]: r for r in rd(OUT, "final_Z1_Z2_comparison.csv")}
    old = {r["case"]: r for r in rd(BASE, "architecture_replay_0mr2.csv")}
    fig, ax = plt.subplots(figsize=(6.6, 5.0))
    for t, col in (("Z1", C1), ("Z2", C2)):
        ax.scatter(ff(new[t], "T_max_C"), ff(new[t], "response_driver_um"), s=170, c=col,
                   edgecolor="k", zorder=3, label=f"{t} realizable")
        ax.annotate(t, (ff(new[t], "T_max_C"), ff(new[t], "response_driver_um")),
                    textcoords="offset points", xytext=(11, 5), fontsize=9)
        ax.scatter(ff(old[t], "T_max_C"), ff(old[t], "du_corner_um"), s=70, c="none",
                   edgecolor=col, zorder=2, alpha=.8)
        ax.annotate("0M-R2", (ff(old[t], "T_max_C"), ff(old[t], "du_corner_um")),
                    textcoords="offset points", xytext=(7, -12), fontsize=6, alpha=.85)
    t1, d1 = ff(new["Z1"], "T_max_C"), ff(new["Z1"], "response_driver_um")
    t2, d2 = ff(new["Z2"], "T_max_C"), ff(new["Z2"], "response_driver_um")
    ax.annotate("", xy=(t2, d2), xytext=(t1, d1),
                arrowprops=dict(arrowstyle="<|-|>", color=C2, lw=1.5, ls="--"))
    ax.text((t1 + t2) / 2, (d1 + d2) / 2 + .07,
            f"Z2 is {t2-t1:.1f} K HOTTER\nand carries {100*(d1-d2)/d1:.1f} % LESS "
            f"response\nD_driver = {d1/d2:.4f}", fontsize=7.5, color=C2, ha="center")
    ax.set(xlabel="package peak temperature (C)",
           ylabel="local fatigue-relevant inelastic response driver (um)",
           title="FIG-0MR3-G  the realizable pair: ranking by T_max is not ranking by the\n"
                 "fatigue-relevant response. Filled = realizable, hollow = Phase 0M-R2.")
    ax.legend(fontsize=7, loc="lower left")
    fig.savefig(OUT / "FIG_0MR3_G_decoupling.png"); plt.close(fig)


if __name__ == "__main__":
    only = sys.argv[1:] or ["a", "c", "d", "f", "g"]
    for k in only:
        fn = globals().get("fig_" + k)
        if fn is None:
            raise SystemExit("no figure " + k)
        fn(); print("  FIG-0MR3-" + k.upper())
    print("done")


# ------------------------------------------------------------------ B
def fig_b():
    """Repaired Z1 and Z2 component stacks, and the routing that gates them."""
    import yaml as _y
    routes = rd(OUT, "routing_feasibility_candidates.csv")
    fig, ax = plt.subplots(1, 3, figsize=(13, 4.4),
                           gridspec_kw={"width_ratios": [1, 1, 1.5]})
    for a_, tag, arch in ((ax[0], "Z1", "ARCH_Z1_EMBEDDED"),
                          (ax[1], "Z2", "ARCH_Z2_BACKSIDE")):
        c = _y.safe_load((R / f"configs/phase0mr3/frozen_realizable_{tag}.yaml").read_text())
        space = c["geometry"]["cell_space_um"]
        used = c["margins_at_worst_corner"]["height_ratio"] * space
        a_.add_patch(plt.Rectangle((0, 0), 1, space, fc="#ecf0f1", ec="k", lw=1.2))
        a_.add_patch(plt.Rectangle((0, 0), 1, used, fc="#e74c3c", alpha=.55, ec="k"))
        a_.text(.5, used / 2, f"converter cell\n{used:.0f} um", ha="center",
                va="center", fontsize=7.5)
        a_.text(.5, used + (space - used) / 2,
                f"headroom\n{space - used:.0f} um\n({100*(1-used/space):.1f} %)",
                ha="center", va="center", fontsize=7, color="#27ae60")
        a_.axhline(space, color="k", lw=1.5)
        a_.set(xlim=(-.1, 1.1), ylim=(0, space * 1.12), xticks=[],
               ylabel="height in the cell envelope (um)" if tag == "Z1" else "",
               title=f"{arch.replace('ARCH_','')}\n{c['verdict']}")
        a_.text(.5, space * 1.05, f"envelope {space:.0f} um", ha="center", fontsize=6.5)
    rs = [r for r in routes if r["arch"] == "ARCH_Z1_EMBEDDED"]
    if rs:
        names = [r["net"] for r in rs]
        vals = [ff(r, "ratio") for r in rs]
        cols = ["#c0392b" if r["geom"] == "vertical" else "#1b6ca8" for r in rs]
        y = np.arange(len(names))
        ax[2].barh(y, vals, .6, color=cols)
        for yi, v in zip(y, vals):
            ax[2].text(v + .02, yi, f"{v:.3f}", va="center", fontsize=7)
        ax[2].axvline(1.0, color="k", lw=1.6)
        ax[2].set_yticks(y); ax[2].set_yticklabels(names, fontsize=7)
        ax[2].invert_yaxis()
        ax[2].set(xlabel="required / available", xlim=(0, 1.35),
                  title="every route after the repair\n"
                        "red = vertical via stack, blue = lateral trace")
    fig.suptitle("FIG-0MR3-B  the repaired realizable pair: component stack headroom and "
                 "the routing gate.\nThe binding net was the vertical ls_to_L via stack; "
                 "a 20 um via at 70 um pitch clears it.", fontsize=9)
    fig.savefig(OUT / "FIG_0MR3_B_repaired_stacks.png"); plt.close(fig)
