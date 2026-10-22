#!/usr/bin/env python3
"""PHASE 0N-R SECTION 15 -- separate K physical branches from the 2 switching phases.

Built so that K = 3 inductor branches can never be mistaken for 3 temporal phases.
Semantics derived in research/HVR_PHASE_COUNT_AUDIT.md.
"""
from __future__ import annotations
import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, Circle

R = Path(__file__).resolve().parent.parent
for d in ("phase0mr", "phase0m", "phase0i", "phase0h", "phase0g", "phase0f",
          "phase0e", "phase0dr", "phase0b", "phase0d"):
    sys.path.insert(0, str(R / "scripts" / d))
import kw1                                                              # noqa: E402

OUT = R / "research" / "phase0n"
OUT.mkdir(parents=True, exist_ok=True)
D_, _g, _w = kw1.design_1kw()
A = D_.arch
N, K, KA, B = A.N, A.K, A.K_A, A.B_array
KB = K - KA
VMID = D_.v_in / N
IB = D_.i_out_a * B[0] / sum(B)

HV, LV, OFFC, ONC, CAP = "#0072B2", "#C1121F", "#C8C8C8", "#009E73", "#7B5EA7"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8})

# branch i -> phase group. generate_B_array interleaves A,B,A for odd N with K_A>1.
GROUP = ["A", "B", "A"]


def draw(ax, title, active, note):
    """active: None = topology only; 'A' or 'B' = highlight that group's conduction."""
    ax.set_xlim(0, 100); ax.set_ylim(0, 74); ax.axis("off")
    ax.text(50, 73, title, ha="center", va="top", fontsize=10.5, weight="bold")

    ax.plot([4, 96], [64, 64], color=HV, lw=2.2)
    ax.text(2, 64, "48 V", fontsize=8, color=HV, ha="right", va="center", weight="bold")
    ax.plot([4, 96], [36, 36], color=CAP, lw=2.2)
    ax.text(2, 36, f"{VMID:.0f} V", fontsize=8, color=CAP, ha="right", va="center",
            weight="bold")
    ax.plot([4, 96], [6, 6], color="#333", lw=2.0)
    ax.text(2, 6, "GND", fontsize=8, color="#333", ha="right", va="center")

    xs = [20, 50, 80]
    for i, x in enumerate(xs):
        g = GROUP[i]
        on = (active is None) or (g == active)
        col = ONC if (active and on) else (OFFC if active else "#777")
        hs_fc = ONC if (active and on) else ("#EEE" if active else "#E8E8E8")
        # high-side device of SC branch i
        ax.add_patch(Rectangle((x - 5, 54), 10, 7, fc=hs_fc, ec=col if active else "#333",
                               lw=1.6))
        ax.text(x, 57.5, f"HS{i+1}", ha="center", va="center", fontsize=7.6,
                weight="bold")
        ax.plot([x, x], [64, 61], color=HV, lw=1.4)
        ax.plot([x, x], [54, 44], color=col if active else "#555", lw=1.8 if on else 1.0)
        # flying capacitors sit BETWEEN adjacent branches: N-1 of them
        if i < N - 1:
            cx = (xs[i] + xs[i + 1]) / 2
            ax.plot([x, cx], [49, 49], color=CAP, lw=1.2)
            ax.plot([cx, xs[i + 1]], [49, 49], color=CAP, lw=1.2)
            ax.plot([cx - 2.6, cx - 2.6], [46.4, 51.6], color=CAP, lw=2.0)
            ax.plot([cx + 0.4, cx + 0.4], [46.4, 51.6], color=CAP, lw=2.0)
            ax.text(cx - 1, 53.4, f"C$_{{f{i+1}}}$", ha="center", fontsize=7.4,
                    color=CAP)
        # low-side device + inductor = one BRANCH
        ax.add_patch(Rectangle((x - 5, 26), 10, 7, fc=hs_fc, ec=col if active else "#333",
                               lw=1.6))
        ax.text(x, 29.5, f"LS{i+1}", ha="center", va="center", fontsize=7.6,
                weight="bold")
        ax.plot([x, x], [26, 6], color="#333", lw=1.0)
        ax.plot([x, x], [44, 36], color=col if active else "#555", lw=1.8 if on else 1.0)
        for k in range(3):                                   # inductor coil
            ax.add_patch(Circle((x, 21.5 - k * 3.0), 1.9, fill=False,
                                ec=col if active else "#333", lw=1.5))
        ax.plot([x, x], [26, 23.4], color=col if active else "#333", lw=1.4)
        ax.plot([x, x], [12.6, 11], color=col if active else "#333", lw=1.4)
        ax.text(x + 4.5, 17, f"L{i+1}", fontsize=7.6, weight="bold",
                color=col if active else "#333")
        ax.plot([x, x], [11, 11], color=LV, lw=1.4)
        ax.text(x, 40.4, f"branch {i+1}", ha="center", fontsize=7.0, color="#555")
        ax.text(x, 3.0, f"phase {g}", ha="center", fontsize=7.4, weight="bold",
                color=ONC if (active and on) else "#888")
        if active:
            ax.text(x - 5.6, 17.0, "driven" if on else "free", ha="right",
                    fontsize=7.0, weight="bold", color=ONC if on else "#999")
    ax.plot([xs[0], xs[-1]], [11, 11], color=LV, lw=2.4)
    ax.add_patch(FancyArrowPatch((xs[-1], 11), (96, 11), arrowstyle="-|>",
                                 mutation_scale=9, lw=2.4, color=LV))
    ax.text(97, 11, "1 V", fontsize=8, color=LV, ha="left", va="center", weight="bold")
    ax.text(50, -1.5, note, ha="center", va="top", fontsize=7.6, color="#222",
            linespacing=1.35)


fig, axes = plt.subplots(1, 3, figsize=(13.0, 4.5))
fig.subplots_adjust(left=0.035, right=0.975, top=0.84, bottom=0.17, wspace=0.26)
draw(axes[0], f"Physical topology:  N={N} SC branches, K={K} inductor branches", None,
     f"{N} HS · {N-1} flying caps · {K} LS · {K} inductors = {A.component_count}\n"
     f"$B$ = {B}: one SC branch per inductor, $\\sum B_i = N$")
draw(axes[1], f"Phase A  —  $K_A$ = {KA} branches driven", "A",
     f"{KA} inductors on the {VMID:.0f} V rail, seeing $V_{{mid}}-V_{{out}}$;\n"
     f"the other {KB} freewheels at $-V_{{out}}$")
draw(axes[2], f"Phase B  —  $K_B = K-K_A$ = {KB} branch driven", "B",
     f"roles reverse, balancing the flying\ncapacitors over a cycle")

fig.suptitle(f"K = {K} is the number of PARALLEL INDUCTOR BRANCHES.  The buck stage has "
             f"TWO switching phases, not {K}.",
             fontsize=11, weight="bold", y=0.975)
fig.text(0.5, 0.012,
         f"Branch current $I_{{cell}}B_i/N$ = {IB:.3f} A (not \"per-phase current\").  "
         f"No phase displacement, dead time or per-state capacitor solve is modelled, so "
         f"no interleaving is claimed.",
         ha="center", va="bottom", fontsize=8, color="#333")
for ext in ("png", "pdf"):
    fig.savefig(OUT / f"fig_hvr_topology_two_phase.{ext}", dpi=210, bbox_inches="tight")
print(f"wrote {OUT/'fig_hvr_topology_two_phase.png'}")
