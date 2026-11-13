"""Fig. 5 (proposed): rail assignment and the loss swap.

(a) Current carried by each class of vertical connection inside one regulator cell,
    coloured by rail (48 V red, 16 V neutral, 1 V violet) - the substrate field carries
    the 48-V input in Z1 but the 1-V output in Z2.
(b,c) Package-internal loss difference Z2 - Z1, decomposed term by term (waterfall), at
    S0 and S1: what the backside regulator removes (the 48-V package path) and adds (the
    1-V attach and TSV field), plus the electrothermal knock-on in the converter devices.
Data: electrical_ledger.json (converged E-T state, per scenario). Rail colours only;
no architecture colours in this figure (the two pairs fail together under CVD).
"""
import json
import numpy as np
import matplotlib.pyplot as plt
import style as S

S.setup()
L = S.J("electrical_ledger.json")["rows"]


def tot(a, s, pred):
    return sum(r["P_w"] for r in L if r["arch"] == a and r["scenario"] == s and pred(r))


GROUPS = [
    ("48-V package path\n(RDL, balls, TSVs)", lambda r: r["rail"] == "48V", S.V48),
    ("1-V Cu-pillar attach", lambda r: r["term"].startswith("P_VR_attach"), S.V1),
    ("1-V TSV field", lambda r: r["term"].startswith("P_TSV") and r["rail"] == "1V", S.V1),
    ("Converter devices", lambda r: r["rail"] == "converter", S.NEUTRAL),
    ("Intra-cell metal, vias", lambda r: r["rail"] == "mixed", S.NEUTRAL),
]


def deltas(s):
    out = []
    for name, pred, col in GROUPS:
        out.append((name, tot("Z2", s, pred) - tot("Z1", s, pred), col))
    net = tot("Z2", s, lambda r: True) - tot("Z1", s, lambda r: True)
    return out, net


fig = plt.figure(figsize=(S.COL_W, 3.55))
axA = fig.add_axes([0.40, 0.745, 0.56, 0.205])
axB = fig.add_axes([0.40, 0.10, 0.255, 0.42])
axC = fig.add_axes([0.705, 0.10, 0.255, 0.42])

# ---------------------------------------------------------------- (a) segment currents
seg = [("48-V input bus", 0.478, S.V48), ("16-V high side to $C_\\mathrm{f}$", 1.015, S.NEUTRAL),
       ("16-V intermediate rail", 1.435, S.NEUTRAL),
       ("1-V switch node to $L$", 20.408, S.V1)]
axA.set_xscale("log")
axA.set_xlim(0.2, 60)
axA.set_ylim(len(seg) - 0.45, -0.55)
axA.grid(axis="x", which="major", color=S.GRID, lw=0.5)
axA.grid(axis="y", visible=False)
for i, (lab, v, col) in enumerate(seg):
    axA.barh(i, v, left=0.2, height=0.62, color=col, lw=0, zorder=2)
    axA.text(v * 1.28, i, f"{v:.2f} A" if v < 10 else f"{v:.1f} A", va="center", ha="left",
             fontsize=6.6, color=S.INK)
axA.set_yticks(range(len(seg)), [s[0] for s in seg])
axA.tick_params(axis="y", length=0, labelsize=6.8)
axA.set_xlabel("Current per regulator cell (A)", labelpad=1.5)
axA.spines["left"].set_visible(False)
S.panel(axA, "a", "Rail currents in one cell", x=-0.70, y=1.06)
axA.text(1.0, -0.40, "×49 cells: 23.9 A at 48 V vs 1.0 kA at 1 V", transform=axA.transData,
         ha="left", va="bottom", fontsize=6.2, color=S.INK2)

# ---------------------------------------------------------------- (b,c) loss swap
for k, (ax, s, name, xl) in enumerate(((axB, "HV_S0", "S0 smoothed", (-2.2, 1.25)),
                                       (axC, "HV_S1", "S1 pulsed", (-40, 17)))):
    ds, net = deltas(s)
    rows = ds + [("Net, Z2 $-$ Z1", net, S.INK)]
    ax.set_xlim(*xl)
    ax.set_ylim(len(rows) - 0.4, -0.6)
    ax.axvline(0, color=S.AXIS, lw=0.6, zorder=1)
    ax.grid(axis="x", color=S.GRID, lw=0.5)
    ax.grid(axis="y", visible=False)
    cum = 0.0
    for i, (lab, d, col) in enumerate(rows):
        if i < len(rows) - 1:
            left = cum if d >= 0 else cum + d
            ax.barh(i, abs(d), left=left, height=0.6, color=col, lw=0, zorder=2)
            if i < len(rows) - 2:
                ax.plot([cum + d, cum + d], [i + 0.3, i + 0.7], color=S.MUTED, lw=0.5,
                        zorder=1)
            cum += d
            ax.text(xl[1], i, (f"{d:+.2f}" if abs(d) < 10 else f"{d:+.1f}").replace("-", "\u2212"), va="center",
                    ha="right", fontsize=6.2, color=S.INK)
        else:
            ax.barh(i, d, left=0, height=0.6, color=col, lw=0, zorder=2)
            ax.text(xl[1], i, (f"{d:+.2f}" if abs(d) < 10 else f"{d:+.1f}").replace("-", "\u2212"), va="center",
                    ha="right", fontsize=6.4, color=S.INK, fontweight="bold")
    ax.set_yticks(range(len(rows)), [r[0] for r in rows] if k == 0 else [])
    ax.tick_params(axis="y", length=0, labelsize=6.6)
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("$\\Delta P$ (W)", labelpad=1.5)
    S.panel(ax, "bc"[k], name, y=1.02)
fig.text(0.40, 0.575, "Package-internal loss difference, Z2 $-$ Z1", ha="left",
         va="bottom", fontsize=7, color=S.INK)
S.save(fig, "fig5_loss_swap")
