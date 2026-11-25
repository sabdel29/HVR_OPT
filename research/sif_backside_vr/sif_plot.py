#!/usr/bin/env python3
"""Si-IF backside VR study -- efficiency vs backside current density (Pareto fronts).

Reads results_summary.json (sif_report.py) and writes fig_eff_vs_density.png: one panel per
input voltage, converter efficiency against the achieved system current density (A per mm^2 of
backside) on the non-dominated designs of every packing variant.
"""
from __future__ import annotations

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
# reference categorical palette (light mode), fixed slot order
SERIES = [("power_ko100", "square cell, 100 um keep-out (baseline)", "#2a78d6", "o"),
          ("power_ko50", "square cell, 50 um", "#eb6834", "s"),
          ("power_ko200", "square cell, 200 um", "#1baf7a", "^"),
          ("rect_ko100", "rectangular cell (aspect <= 3), 100 um", "#eda100", "D"),
          ("overhead_ko100", "+ drivers and decoupling, 100 um", "#e87ba4", "v")]
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"

def open_text(path):
    """Open a result file, or its gzip copy (path + ".gz") when only that is present."""
    import gzip
    if os.path.isfile(path):
        return open(path)
    return gzip.open(path + ".gz", "rt")



def step_front(pts):
    """Pareto points sorted by density -> step coordinates (efficiency held to the next point)."""
    pts = sorted(pts, key=lambda p: p[0])
    return [p[0] for p in pts], [100 * p[1] for p in pts]


def main():
    s = json.load(open(os.path.join(HERE, "results_summary.json")))["results"]
    vins = sorted(s, key=lambda v: -float(v.rstrip("V")))
    plt.rcParams.update({"font.size": 10, "axes.edgecolor": INK2, "axes.labelcolor": INK,
                         "xtick.color": INK2, "ytick.color": INK2, "text.color": INK})
    fig, axes = plt.subplots(1, len(vins), figsize=(6.2 * len(vins), 4.6), facecolor=SURFACE)
    if len(vins) == 1:
        axes = [axes]
    for ax, v in zip(axes, vins):
        ax.set_facecolor(SURFACE)
        ax.grid(True, color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ymin = 100.0
        for key, label, color, mk in SERIES:
            rec = s[v]["by_mode"].get(key)
            if not rec or not rec.get("pareto"):
                continue
            x, y = step_front([(p["J_achieved"], p["efficiency"]) for p in rec["pareto"]])
            ax.plot(x, y, color=color, lw=2, marker=mk, ms=4.5, label=label,
                    drawstyle="steps-post" if False else "default")
            ymin = min(ymin, min(y))
            md = rec.get("max_density")
            if md:
                ax.plot([md["J_achieved"]], [100 * md["efficiency"]], marker=mk, ms=9,
                        color=color, mec=SURFACE, mew=1.5, ls="none")
        ax.axvline(1.0, color=INK2, lw=1, ls="--")
        ax.text(1.0, 0.98, " 1 A/mm$^2$", transform=ax.get_xaxis_transform(), color=INK2,
                fontsize=9, va="top")
        ax.set_xlabel("system current density (A per mm$^2$ of wafer backside)")
        ax.set_ylabel("converter efficiency (%)")
        ax.set_title(f"{v} -> 1 V, 1 kA: catalog parts side by side (one tier)", fontsize=10.5,
                     color=INK, loc="left")
        ax.set_xlim(left=0)
        ax.set_ylim(max(ymin - 1.5, 50.0), 100.0)
    axes[0].legend(loc="lower left", fontsize=8.5, frameon=False)
    fig.text(0.01, 0.005, "Curves: non-dominated designs (efficiency vs achieved density); large "
             "markers: maximum density. Efficiency = conversion loss only.", fontsize=8,
             color=INK2)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(os.path.join(HERE, "fig_eff_vs_density.png"), dpi=160, facecolor=SURFACE)
    print("wrote fig_eff_vs_density.png")


KIND_COLOR = [("HS ", "HS FET", "#2a78d6"), ("LS ", "LS FET", "#eb6834"),
              ("L ", "inductor", "#1baf7a"), ("C ", "flying C", "#eda100"),
              ("uP1966E", "driver", "#e87ba4"), ("0402", "bootstrap C", "#008300"),
              ("GRM21", "input C", "#6250d6")]


def _kind(names):
    """Part kind(s) of a placement class from its part names (prefix match only); a class that
    merges identical bodies of several kinds gets a combined label (e.g. HS + LS FET)."""
    hits = [(label, c) for prefix, label, c in KIND_COLOR if any(n.startswith(prefix)
                                                                  for n in names)]
    if not hits:
        return "?", "#888888"
    if len(hits) == 1:
        return hits[0]
    return " + ".join(h[0] for h in hits), hits[0][1]


def layouts(keys=("power_ko100", "rect_ko100", "overhead_ko100")):
    """Cell layouts of the maximum-density designs (bodies drawn inside their keep-out
    envelopes), one row per input voltage."""
    s = json.load(open(os.path.join(HERE, "results_summary.json")))["results"]
    full = {}
    for tag in ("v48", "v12"):
        p = os.path.join(HERE, f"sweep_{tag}_best.json")
        if os.path.isfile(p) or os.path.isfile(p + ".gz"):
            d = json.load(open_text(p))
            full[d["meta"]["V_in"]] = d["jmax"]
    vins = sorted(s, key=lambda v: -float(v.rstrip("V")))
    fig, axes = plt.subplots(len(vins), len(keys), figsize=(4.2 * len(keys), 4.2 * len(vins)),
                             facecolor=SURFACE, squeeze=False)
    for i, v in enumerate(vins):
        for j, key in enumerate(keys):
            ax = axes[i][j]
            ax.set_facecolor(SURFACE)
            ax.set_aspect("equal")
            md = s[v]["by_mode"].get(key, {}).get("max_density")
            if not md:
                ax.axis("off")
                continue
            rec = next((r for r in full.get(float(v.rstrip("V")), [])
                        if r["mode"] == md["mode"] and r["keepout_um"] == md["keepout_um"]
                        and r["M"] == md["M"] and r["topology"] == md["topology"]
                        and abs(r["J_target"] - md["J_target"]) < 1e-9), None)
            if not rec or not rec.get("placement_mm"):
                ax.axis("off")
                continue
            W, Hh = rec["cell_min_WH_mm"]
            ko = rec["keepout_um"] * 1e-3
            ax.add_patch(plt.Rectangle((0, 0), max(W, Hh), min(W, Hh), fill=False, ec=INK2,
                                       lw=1.2, ls="--"))
            seen = set()
            for x, y, w, h, c in rec["placement_mm"]:
                kind, col = _kind(rec["placement_class_parts"][c])
                ax.add_patch(plt.Rectangle((x + ko / 2, y + ko / 2), w - ko, h - ko, fc=col,
                                           ec=SURFACE, lw=1.0,
                                           label=None if kind in seen else kind))
                seen.add(kind)
            ax.set_xlim(-0.2, max(W, Hh) + 0.2)
            ax.set_ylim(-0.2, min(W, Hh) + 0.2)
            ax.set_title(f"{v} {key.replace('_ko', ', ').replace('100', '100 um')}: "
                         f"{rec['topology']}, {rec['I_cell_A']:.1f} A/cell\n"
                         f"{rec['J_achieved']:.2f} A/mm$^2$, eff {100*rec['efficiency']:.1f} %",
                         fontsize=9, loc="left", color=INK)
            ax.tick_params(labelsize=8)
            ax.set_xlabel("mm", fontsize=8)
            ax.legend(fontsize=7, frameon=False, loc="upper center", ncol=3,
                      bbox_to_anchor=(0.5, -0.16))
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "fig_max_density_cells.png"), dpi=150, facecolor=SURFACE)
    print("wrote fig_max_density_cells.png")


if __name__ == "__main__":
    main()
    layouts()
