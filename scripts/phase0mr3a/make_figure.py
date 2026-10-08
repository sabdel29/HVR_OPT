#!/usr/bin/env python3
"""Phase-0M-R3A, one figure: what the TSV diameter actually buys ARCH_Z2.

Phase 0M-R3 evaluated 30/34/40/50/60 um and reported the move to 34 um as costing
22.8 % MORE vias. Both halves are answered here: the smallest passing diameter is 32 um,
and the count goes DOWN.
"""
from __future__ import annotations
import csv, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                          # noqa: E402

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3a"
plt.rcParams.update({"figure.dpi": 150, "savefig.bbox": "tight", "font.size": 8,
                     "axes.grid": True, "grid.alpha": .3})
C1, C2, C3 = "#1b6ca8", "#c0392b", "#6b7a8f"
R3_GRID = {30.0, 34.0, 40.0, 50.0, 60.0}


def main() -> int:
    rows = sorted((dict(r) for r in csv.DictReader(
        (OUT / "z2_tsv_diameter_sweep.csv").open())), key=lambda r: float(r["d_um"]))
    d = [float(r["d_um"]) for r in rows]
    m = [float(r["M_AR"]) for r in rows]
    nr = [int(r["n_required"]) for r in rows]
    na = [int(r["n_available"]) for r in rows]
    ok = [r["passes_modest_bound"] == "True" for r in rows]
    d_min = min(x for x, p in zip(d, ok) if p)

    fig, ax = plt.subplots(1, 2, figsize=(7.4, 2.9))

    ax[0].plot(d, m, "-o", color=C1, ms=3.5, lw=1.2, zorder=3)
    ax[0].axhline(1.0, color=C2, lw=1, ls="--")
    ax[0].text(d[-1], 1.005, "AR = 10 hard rule", color=C2, ha="right", va="bottom", fontsize=7)
    ax[0].axvspan(d[0], d_min, color=C2, alpha=.07, zorder=0)
    ax[0].axvline(d_min, color=C1, lw=1, ls=":")
    ax[0].text(d_min + .4, min(m) + .02, f"smallest passing\n{d_min:.0f} um",
               color=C1, fontsize=7, va="bottom")
    ax[0].plot([x for x, p in zip(d, ok) if not p], [y for y, p in zip(m, ok) if not p],
               "o", mfc="none", mec=C2, ms=7, lw=1, zorder=4)
    ax[0].set_xlabel("TSV diameter (um)"); ax[0].set_ylabel("AR margin  M_AR = 10 / AR")
    ax[0].set_title("(a) process margin: 30 um sits exactly on the limit", fontsize=8)

    ax[1].plot(d, nr, "-o", color=C1, ms=3.5, lw=1.2, label="n_required")
    ax[1].plot(d, na, "-s", color=C3, ms=3.5, lw=1.2, label="n_available")
    ax[1].set_yscale("log")
    for x in (30.0, 34.0):
        y = nr[d.index(x)]
        ax[1].annotate(f"{y:,}", (x, y), textcoords="offset points", xytext=(4, 6),
                       fontsize=7, color=C1)
    ax[1].annotate("", xy=(34, nr[d.index(34.0)]), xytext=(30, nr[d.index(30.0)]),
                   arrowprops=dict(arrowstyle="->", color=C2, lw=1.1))
    drop = 100 * (nr[d.index(30.0)] - nr[d.index(34.0)]) / nr[d.index(30.0)]
    ax[1].text(32, nr[d.index(30.0)] * 1.9, f"-{drop:.1f} %\n(0M-R3 said +22.8 %)",
               color=C2, fontsize=7, ha="center")
    ax[1].set_xlabel("TSV diameter (um)"); ax[1].set_ylabel("vias in the ARCH_Z2 field")
    ax[1].set_title("(b) n_required scales as 1/A_cu: bigger via, fewer vias", fontsize=8)
    ax[1].legend(fontsize=7, loc="center right")

    for a in ax:
        for x in sorted(set(d) - R3_GRID):
            a.axvline(x, color=C1, lw=.6, alpha=.35, zorder=0)
    fig.text(0.5, -0.06, "faint verticals mark diameters the Phase-0M-R3 grid never "
             "evaluated; phi_Cu = I/(J_design*A_field) is constant at 0.0200 across the "
             "whole sweep", ha="center", fontsize=6.5, color="#555")

    p = OUT / "FIG_0MR3A_tsv_diameter_margin_and_count.png"
    fig.savefig(p); plt.close(fig)
    print(f"wrote {p.relative_to(R)}  (smallest passing {d_min:.0f} um, "
          f"n_required {nr[d.index(30.0)]} -> {nr[d.index(34.0)]}, -{drop:.1f} %)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
