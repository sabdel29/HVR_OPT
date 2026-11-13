"""Fig. (proposed, capability 3): converter design-space exploration over regulator count.

Conversion + routing loss against regulator count M at the paper's specification
(1 kW, 48 V -> 1 V, 500 mm2, J = 3.5 A/mm2, 90-device discrete library, ripple 0.5),
with the converter architecture RE-SYNTHESIZED at every M (solid) versus held at the
N=3, K=3 architecture of the integration study (dashed). Marker shape = selected
architecture (identity never by colour alone). Data: scratch/dse_j35/data/case_{C,D}_etm35.csv
(partition_sweep_v2 at J = 3.5, run 2026-11-13).
"""
import csv
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from pathlib import Path
import style as S

S.setup()
D = S.SRC / "research" / "tcpmt_revision" / "dse_j35" / "data"


def load(case):
    rows = list(csv.DictReader(open(D / f"case_{case}_etm35.csv")))
    out = []
    for r in rows:
        ok = r["feasible"] == "True"
        out.append(dict(M=int(r["M"]), ok=ok, tot=float(r["total_loss_W"]) if ok else None,
                        arch=r["arch"] if ok else None,
                        fsw=float(r["f_sw_Hz"]) / 1e3 if ok else None))
    return out


Dd, Cc = load("D"), load("C")
MK = {"N=3,K=3,K_A=2": ("o", "N3K3K$_A$2"), "N=2,K=2,K_A=1": ("s", "N2K2K$_A$1"),
      "N=4,K=4,K_A=2": ("^", "N4K4K$_A$2")}
fig, ax = plt.subplots(figsize=(S.COL_W, 2.45))
fig.subplots_adjust(left=0.15, right=0.97, bottom=0.17, top=0.86)
ax.set_xlim(33, 123)
ax.set_ylim(82, 122)
# infeasible region for the re-synthesized discrete design
m_inf = min(r["M"] for r in Dd if not r["ok"])
ax.axvspan(m_inf - 3, 123, color=S.LIGHT, lw=0, zorder=0)
ax.text((m_inf - 3 + 123) / 2, 119.5, "no feasible design\n(discrete library)", ha="center",
        va="top", fontsize=6.3, color=S.INK2)
# fixed architecture (dashed)
xc = [r["M"] for r in Cc if r["ok"]]
yc = [r["tot"] for r in Cc if r["ok"]]
ax.plot(xc, yc, ls=(0, (3, 2)), color=S.MUTED, lw=1.0, zorder=2)
ax.text(xc[-1] + 1.0, yc[-1] - 0.4, "fixed N3K3", ha="left", va="top", fontsize=6.3,
        color=S.INK2)
# re-synthesized (solid, markers by architecture)
xd = [r["M"] for r in Dd if r["ok"]]
yd = [r["tot"] for r in Dd if r["ok"]]
ax.plot(xd, yd, color=S.INK, lw=1.1, zorder=3)
for r in Dd:
    if r["ok"]:
        m, _ = MK[r["arch"]]
        ax.plot(r["M"], r["tot"], m, ms=4.6, mfc="white", mec=S.INK, mew=0.9, zorder=4)
# design point of the integration study and the optimum
p49 = next(r for r in Dd if r["M"] == 49)
best = min((r for r in Dd if r["ok"]), key=lambda r: r["tot"])
ax.plot(49, p49["tot"], "o", ms=7.5, mfc="none", mec=S.INK, mew=1.0, zorder=5)
ax.annotate(f"integration-study design\nM = 49, {p49['tot']:.1f} W", (49, p49["tot"]),
            xytext=(-4, -24), textcoords="offset points", ha="center", va="top",
            fontsize=6.4, color=S.INK, arrowprops=dict(arrowstyle="-", lw=0.5,
                                                         color=S.MUTED))
ax.annotate(f"optimum M = {best['M']}\n{best['tot']:.1f} W", (best["M"], best["tot"]),
            xytext=(-9, 0), textcoords="offset points", ha="right", va="center",
            fontsize=6.4, color=S.INK)
ax.set_xlabel("Regulator count $M$ (at $J$ = 3.5 A/mm$^2$)")
ax.set_ylabel("Conversion + routing loss (W)")
handles = [Line2D([], [], color=S.INK, lw=1.1, label="architecture re-synthesized"),
           Line2D([], [], color=S.MUTED, lw=1.0, ls=(0, (3, 2)), label="architecture fixed")]
handles += [Line2D([], [], marker=m, ls="none", mfc="white", mec=S.INK, ms=4.6, label=l)
            for m, l in MK.values()]
fig.legend(handles=handles, loc="upper center", ncol=3, bbox_to_anchor=(0.55, 1.01),
           fontsize=6.3, columnspacing=0.9, handletextpad=0.4)
S.save(fig, "fig_dse")
