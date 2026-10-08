#!/usr/bin/env python3
"""PHASE0C_DVPD_LEVER_FIGURE - is the dominant mechanical lever generic placement,
or a DVPD-specific design variable?"""
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
P0C = R / "results" / "phase0c"

DVPD_C = "#c0392b"      # DVPD-specific
GEN_C = "#2c5f8a"       # generic floorplanning
NULL_C = "#95a5a6"


def load(p):
    rows = list(csv.DictReader((P0C / p).open()))
    for r in rows:
        for k, v in r.items():
            try:
                r[k] = float(v)
            except (TypeError, ValueError):
                pass
    return rows


def main():
    doe = {r["case"]: r for r in load("full_doe_results.csv")}
    mech = json.loads((P0C / "mechanism_analysis.json").read_text())
    u_die = 0.005                                     # mesh 1u on die warpage (0.50 %)

    fig = plt.figure(figsize=(17, 13.5), dpi=145)
    gs = fig.add_gridspec(3, 6, height_ratios=[1.32, 1.0, 1.0], hspace=0.42, wspace=0.62)

    # ---------------- Panel A: the headline ranking -------------------------
    ax = fig.add_subplot(gs[0, :])
    levers = [
        ("placement: distributed -> compact central", 100.52, False),
        ("placement: distributed -> asymmetric",       60.59, False),
        ("SUBSTRATE THICKNESS: 200 -> 500 um",        -57.01, True),
        ("placement: distributed -> edge/corner",     -34.70, False),
        ("HVR FOOTPRINT: 96 -> 120 mm2 (+25%)",        20.60, True),
        ("HVR FOOTPRINT: 96 -> 72 mm2 (-25%)",        -21.18, True),
        ("HVR HEAT: 42 -> 52.5 W (+25%)",              10.78, True),
        ("VR COUNT: 4 -> 8",                           -4.07, True),
        ("HVR ASPECT RATIO: 1 -> 2",                   -1.76, True),
        ("VR COUNT: 4 -> 6",                            0.02, True),
    ]
    levers.sort(key=lambda t: -abs(t[1]))
    y = np.arange(len(levers))
    vals = [abs(v) for _, v, _ in levers]
    cols = [DVPD_C if d else GEN_C for _, _, d in levers]
    cols = [NULL_C if abs(v) < 10 else c for (_, v, _), c in zip(levers, cols)]
    ax.barh(y, vals, color=cols, edgecolor="k", linewidth=0.6, height=0.68)
    for i, (name, v, d) in enumerate(levers):
        ax.text(abs(v) + 1.6, i, f"{v:+.2f}%", va="center", fontsize=9,
                weight="bold" if abs(v) > 10 else "normal")
    ax.axvline(100 * 2 * u_die, color="k", ls="--", lw=1.2)
    ax.text(100 * 2 * u_die + 0.6, len(levers) - 0.35,
            "2u (mesh) = 1.0%", fontsize=8.5, rotation=90, va="top")
    ax.axvspan(0, 10, color="0.85", alpha=0.55, zorder=0)
    ax.text(5, -0.85, "below the 10% materiality band", fontsize=8, ha="center", style="italic")
    ax.set_yticks(y); ax.set_yticklabels([n for n, _, _ in levers], fontsize=9.5)
    ax.invert_yaxis()
    ax.set_xlabel("| change in die peak-to-valley warpage |  (%)", fontsize=10.5)
    ax.set_xlim(0, 118)
    ax.set_title("A.  Which design variable is the dominant mechanical lever?\n"
                 "Controlled DOE: only the named variable changes. "
                 "Red = DVPD-specific power-delivery variable, blue = generic floorplanning, "
                 "grey = below the materiality band.",
                 fontsize=11.5, loc="left")
    ax.grid(axis="x", alpha=0.3)
    h = [plt.Rectangle((0, 0), 1, 1, fc=DVPD_C, ec="k"), plt.Rectangle((0, 0), 1, 1, fc=GEN_C, ec="k"),
         plt.Rectangle((0, 0), 1, 1, fc=NULL_C, ec="k")]
    ax.legend(h, ["DVPD-specific", "generic placement", "below band"],
              loc="lower right", fontsize=9.5)

    # ---------------- Panel B: thickness response ---------------------------
    ax = fig.add_subplot(gs[1, 0:2])
    fam = [("N=2 compact", ["C01", "C03"], "o-"), ("N=4 distributed", ["C05", "C08"], "s-"),
           ("N=6 distributed", ["C13", "C16"], "^-")]
    for lab, cs, st in fam:
        h = [doe[c]["h_sub_mm"] * 1000 for c in cs]
        w = [doe[c]["die_warpage_pv_um"] for c in cs]
        ax.plot(h, w, st, label=lab, lw=2, ms=8)
    n = mech["thickness_scaling"]["mean_exponent"]
    ax.set_xlabel("power-substrate thickness $h_{sub}$ (um)", fontsize=10)
    ax.set_ylabel("die warpage p-v (um)", fontsize=10)
    ax.set_title(f"B.  Substrate thickness  -  DVPD-SPECIFIC\n"
                 f"$w \\propto h_{{total}}^{{{n:.2f}}}$, identical across placement families "
                 f"(spread 0.72 pp)", fontsize=10, color=DVPD_C)
    ax.legend(fontsize=8.5); ax.grid(alpha=0.3); ax.set_ylim(0, 17)

    # ---------------- Panel C: footprint ------------------------------------
    ax = fig.add_subplot(gs[1, 2:4])
    cs = ["C11", "C05", "C12"]
    a = [doe[c]["a_vr_total_mm2"] for c in cs]
    w = [doe[c]["die_warpage_pv_um"] for c in cs]
    ax.plot(a, w, "o-", color=DVPD_C, lw=2, ms=9)
    for x, yy, c in zip(a, w, cs):
        ax.annotate(c, (x, yy), textcoords="offset points", xytext=(6, -12), fontsize=8)
    ax.set_xlabel("total HVR footprint (mm$^2$)", fontsize=10)
    ax.set_ylabel("die warpage p-v (um)", fontsize=10)
    ax.set_title("C.  HVR footprint  -  DVPD-SPECIFIC\nnear-linear, +-21% for -+25% area",
                 fontsize=10, color=DVPD_C)
    ax.grid(alpha=0.3)

    # ---------------- Panel D: HVR heat -------------------------------------
    ax = fig.add_subplot(gs[1, 4:6])
    cs = ["C19", "C07", "C20"]
    q = [doe[c]["p_hvr_total_W"] for c in cs]
    w = [doe[c]["die_warpage_pv_um"] for c in cs]
    ax.plot(q, w, "o-", color=DVPD_C, lw=2, ms=9)
    for x, yy, c in zip(q, w, cs):
        ax.annotate(c, (x, yy), textcoords="offset points", xytext=(6, -12), fontsize=8)
    ax.set_xlabel("total HVR heat (W)   [die load fixed at 240 W]", fontsize=10)
    ax.set_ylabel("die warpage p-v (um)", fontsize=10)
    ax.set_title("D.  HVR converter loss  -  DVPD-SPECIFIC\nexactly linear; +-10.8% for +-25% loss",
                 fontsize=10, color=DVPD_C)
    ax.grid(alpha=0.3)

    # ---------------- Panel E: the two nulls --------------------------------
    ax = fig.add_subplot(gs[2, 0:2])
    cs = ["C05", "C13", "C17"]
    nvr = [doe[c]["n_vr"] for c in cs]
    w = [doe[c]["die_warpage_pv_um"] for c in cs]
    ax.plot(nvr, w, "o-", color=NULL_C, lw=2, ms=9, label="die warpage")
    base = w[0]
    ax.axhspan(base * (1 - 2 * u_die), base * (1 + 2 * u_die), color="k", alpha=0.15,
               label="+-2u (mesh)")
    ax.set_xlabel("number of VRs (symmetric distributed, area & heat fixed)", fontsize=10)
    ax.set_ylabel("die warpage p-v (um)", fontsize=10)
    ax.set_ylim(6.8, 8.6); ax.set_xticks([4, 6, 8])
    ax.set_title("E.  VR count  -  NULL RESULT CONFIRMED\n0.02% (4->6), -4.07% (4->8)",
                 fontsize=10, color="0.35")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)

    # ---------------- Panel F: aspect ratio ---------------------------------
    ax = fig.add_subplot(gs[2, 2:4])
    cs = ["C10", "C05", "C09"]
    ar = [doe[c]["aspect_ratio"] for c in cs]
    w = [doe[c]["die_warpage_pv_um"] for c in cs]
    ax.plot(ar, w, "o-", color=NULL_C, lw=2, ms=9)
    ax.axhspan(doe["C05"]["die_warpage_pv_um"] * (1 - 2 * u_die),
               doe["C05"]["die_warpage_pv_um"] * (1 + 2 * u_die), color="k", alpha=0.15)
    for x, yy, c in zip(ar, w, cs):
        ax.annotate(c, (x, yy), textcoords="offset points", xytext=(4, 8), fontsize=8)
    ax.set_xscale("log"); ax.set_xticks([0.5, 1, 2]); ax.set_xticklabels(["0.5", "1", "2"])
    ax.set_xlabel("HVR tile aspect ratio $A_x/A_y$ (area fixed)", fontsize=10)
    ax.set_ylabel("die warpage p-v (um)", fontsize=10)
    ax.set_title("F.  Tile aspect ratio  -  NULL\n-1.76%; AR 2 and 0.5 identical by 90-deg symmetry",
                 fontsize=10, color="0.35")
    ax.grid(alpha=0.3)

    # ---------------- Panel G: placement reference scale --------------------
    ax = fig.add_subplot(gs[2, 4:6])
    cs = ["C06", "C05", "C07", "C04"]
    lab = ["edge/\ncorner", "distributed\n2x2", "asymmetric\nleft", "compact\ncentral"]
    w = [doe[c]["die_warpage_pv_um"] for c in cs]
    ax.bar(range(4), w, color=GEN_C, edgecolor="k", lw=0.6)
    for i, (v, c) in enumerate(zip(w, cs)):
        ax.text(i, v + 0.3, f"{v:.2f}\n{c}", ha="center", fontsize=8)
    ax.set_xticks(range(4)); ax.set_xticklabels(lab, fontsize=8.5)
    ax.set_ylabel("die warpage p-v (um)", fontsize=10)
    ax.set_ylim(0, 18.5)
    ax.set_title("G.  Placement family (N=4)  -  GENERIC reference scale\n"
                 "spans 3.1x; the effect STAMP-2.5D / ATMPlace already exploit",
                 fontsize=10, color=GEN_C)
    ax.grid(axis="y", alpha=0.3)

    fig.suptitle(
        "Phase 0C - DVPD-specific mechanical lever gate.   M0 operational thermoelastic, "
        "CalculiX C3D8I direct solver, BC-A, converged production mesh.\n"
        "Controlled DOE: 240 W die load and frozen cooling calibration in every case; "
        "only the named variable changes within each comparison.",
        fontsize=12.5, y=0.985)
    fig.tight_layout(rect=[0, 0, 1, 0.965])
    p = P0C / "PHASE0C_DVPD_LEVER_FIGURE.png"
    fig.savefig(p, bbox_inches="tight"); plt.close(fig)
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
