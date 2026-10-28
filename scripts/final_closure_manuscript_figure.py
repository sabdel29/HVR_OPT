"""manuscript/figs/fig9_physical.pdf -- the physical lineage, read from the artifacts.

(a) loss and peak temperature per named scenario, (b) die warpage and critical-joint
displacement driver per scenario, (c) the all-site joint driver map at HV-S0, (d) each
production model's error against its matched reference versus the runtime ratio.
No value is typed here; a rerun of the lineage redraws the figure.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                      # noqa: E402
import numpy as np                                                   # noqa: E402

R = Path(__file__).resolve().parents[1]
D = R / "research" / "final_closure"
OUT = R / "manuscript" / "figs" / "fig9_physical.pdf"
sys.path.insert(0, str(R / "scripts"))
COL = {"Z1": "#1f6feb", "Z2": "#d1442f"}
SCEN = ("HV_S0", "HV_S1", "HV_S2")
LAB = {"HV_S0": "HV-S0", "HV_S1": "HV-S1", "HV_S2": "HV-S2"}


def J(n):
    return json.loads((D / n).read_text())


def main():
    import final_closure_physical_etm as E
    fin = J("final_results.json")
    g = lambda a, s, k: next(x[k] for x in fin if x["arch"] == a and x["scenario"] == s)
    plt.rcParams.update({"font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
                         "legend.fontsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7})
    fig, ax = plt.subplots(2, 2, figsize=(7.16, 5.4))
    x = np.arange(len(SCEN))
    w = 0.38
    a0, a0b = ax[0, 0], ax[0, 0].twinx()
    for k, a in enumerate(("Z1", "Z2")):
        a0.bar(x + (k - 0.5) * w, [g(a, s, "P_loss_w") for s in SCEN], w, color=COL[a],
               alpha=0.35, label=f"{a} loss")
        a0b.plot(x + (k - 0.5) * w, [g(a, s, "T_max_C") for s in SCEN], "o-", color=COL[a],
                 label=f"{a} $T_{{\\max}}$")
    a0.set_xticks(x, [LAB[s] for s in SCEN])
    a0.set_ylim(0, 1.5 * max(g(a, s, "P_loss_w") for a in ("Z1", "Z2") for s in SCEN))
    tv = [g(a, s, "T_max_C") for a in ("Z1", "Z2") for s in SCEN]
    a0b.set_ylim(min(tv) - 0.1 * (max(tv) - min(tv)), max(tv) + 0.6 * (max(tv) - min(tv)))
    a0.set_ylabel("loss (W)")
    a0b.set_ylabel(r"$T_{\max}$ ($^\circ$C)")
    a0.set_title("(a) loss and peak temperature")
    h1, l1 = a0.get_legend_handles_labels()
    h2, l2 = a0b.get_legend_handles_labels()
    a0.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False, ncol=2)
    a1, a1b = ax[0, 1], ax[0, 1].twinx()
    for k, a in enumerate(("Z1", "Z2")):
        a1.bar(x + (k - 0.5) * w, [g(a, s, "die_warpage_pv_um") for s in SCEN], w,
               color=COL[a], alpha=0.35, label=f"{a} die warpage")
        a1b.plot(x + (k - 0.5) * w, [g(a, s, "du_c_um") for s in SCEN], "s-", color=COL[a],
                 label=f"{a} $\\Delta u_c$")
    a1.set_xticks(x, [LAB[s] for s in SCEN])
    a1.set_ylim(0, 1.5 * max(g(a, s, "die_warpage_pv_um") for a in ("Z1", "Z2") for s in SCEN))
    dv = [g(a, s, "du_c_um") for a in ("Z1", "Z2") for s in SCEN]
    a1b.set_ylim(min(dv) - 0.1 * (max(dv) - min(dv)), max(dv) + 0.6 * (max(dv) - min(dv)))
    a1.set_ylabel(r"die warpage ($\mu$m)")
    a1b.set_ylabel(r"$\Delta u_c$ ($\mu$m)")
    a1.set_title("(b) die warpage and joint displacement driver")
    h1, l1 = a1.get_legend_handles_labels()
    h2, l2 = a1b.get_legend_handles_labels()
    a1.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False, ncol=2)
    a2 = ax[1, 0]
    vmax = 0.0
    maps = {}
    for a in ("Z1", "Z2"):
        js = json.loads(E.case_path(a, "HV_S0").read_text())["mechanics"]["joint_search"]
        maps[a] = js
        vmax = max(vmax, js["critical"]["du_um"])
    for a, off in (("Z1", -16.0), ("Z2", 16.0)):
        js = maps[a]
        xy = np.array([[r["x_mm"], r["y_mm"]] for r in js["ranked"]])
        du = np.array([r["du_um"] for r in js["ranked"]])
        sc = a2.scatter(xy[:, 0] + off, xy[:, 1], c=du, s=2.0, cmap="magma_r", vmin=0,
                        vmax=vmax)
        c = js["critical"]
        a2.plot(c["x_mm"] + off, c["y_mm"], "o", ms=6, mfc="none", mec="k", mew=1)
        a2.text(off, -18.5, f"{a} ({js['n_sites']} sites)", ha="center", va="top", fontsize=7)
    a2.set_aspect("equal")
    a2.set_ylim(-22, 16)
    a2.set_xticks([])
    a2.set_ylabel("y (mm)")
    a2.set_title("(c) joint driver at every legal site, HV-S0")
    fig.colorbar(sc, ax=a2, label=r"$\Delta u$ ($\mu$m)", shrink=0.8)
    a3 = ax[1, 1]
    acc = J("accuracy_speed_matrix.json")["rows"]
    pts = [r for r in acc if r.get("status") == "EXECUTED"
           and isinstance(r.get("error"), float) and isinstance(r.get("speedup"), float)]
    for r in pts:
        moose = "MOOSE" in r.get("reference_tool", "")
        a3.scatter(r["speedup"], 100 * abs(r["error"]), s=14,
                   color="#6639ba" if moose else "#1f6feb", zorder=3)
    a3.scatter([], [], color="#1f6feb", s=14, label="commercial FE reference")
    a3.scatter([], [], color="#6639ba", s=14, label="open-source FE reference")
    a3.set_xscale("log")
    a3.set_xlabel("runtime ratio, reference / production")
    a3.set_ylabel("|error| vs reference (%)")
    a3.set_title("(d) matched-reference error vs runtime ratio")
    a3.legend(frameon=False, loc="upper center")
    for a_ in (a0, a1, a3):
        a_.grid(alpha=0.25)
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT)
    plt.close(fig)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
