"""manuscript/figs/fig9_physical.pdf -- the physical lineage, read from the artifacts.

Small multiples, one quantity per panel (no second y-axis): (a) loss, (b) peak temperature,
(c) die warpage, (d) critical-joint displacement driver, (e) local inelastic strain per
cycle with its measured discretisation uncertainty, per named scenario; (f) the joint
driver at every legal site at HV-S0. No value is typed here; a rerun redraws the figure.
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
    od = J("ordering.json")["orderings"]
    g = lambda a, s_, k: next(x.get(k) for x in fin if x["arch"] == a and x["scenario"] == s_)
    plt.rcParams.update({"font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
                         "legend.fontsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(2, 3, figsize=(7.16, 4.7))
    x = np.arange(len(SCEN))
    w = 0.36
    panels = (("P_loss_w", "(a) loss (W)"), ("T_max_C", r"(b) peak temperature ($^\circ$C)"),
              ("die_warpage_pv_um", r"(c) die warpage ($\mu$m)"),
              ("du_c_um", r"(d) joint driver $\Delta u_c$ ($\mu$m)"))
    for a_, (k, title) in zip(ax.ravel()[:4], panels):
        for n, a in enumerate(("Z1", "Z2")):
            v = [g(a, s_, k) for s_ in SCEN]
            u = [(od[k].get("uncertainty_rel") or {}).get(s_) or 0.0 for s_ in SCEN]
            # an operating point at or above the solder melting onset is an infeasibility
            # result, not an operating comparison: drawn pale and hatched, never ranked
            melt = [bool(g(a, s_, "T_joint_at_or_above_solder_solidus")) for s_ in SCEN]
            bars = a_.bar(x + (n - 0.5) * w, v, w, color=COL[a], label=a,
                          yerr=[vi * ui for vi, ui in zip(v, u)], capsize=1.5,
                          error_kw={"lw": 0.6})
            for b, m in zip(bars, melt):
                if m:
                    b.set_facecolor("white")
                    b.set_edgecolor(COL[a])
                    b.set_hatch("////")
                    b.set_linewidth(0.6)
        a_.set_xticks(x, [LAB[s_] for s_ in SCEN])
        a_.set_title(title, loc="left")
    ax[0, 0].legend(frameon=False, loc="upper left")
    a4 = ax[1, 1]
    for n, a in enumerate(("Z1", "Z2")):
        for j_, s_ in enumerate(SCEN):
            v = g(a, s_, "d_eps_in_per_cycle")
            xx = j_ + (n - 0.5) * w
            if v is None:
                a4.plot(xx, 0.4, "x", color=COL[a], ms=5)
                continue
            u = g(a, s_, "local_mesh_U_rel") or 0.0
            ext = g(a, s_, "T_joint_outside_norton_calibration")
            a4.errorbar(xx, 1e3 * v, yerr=1e3 * v * u, fmt="o", ms=4, color=COL[a],
                        mfc="white" if ext else COL[a], capsize=1.5, lw=0.7)
    a4.set_xticks(x, [LAB[s_] for s_ in SCEN])
    a4.set_ylim(0, None)
    a4.set_title(r"(e) local $\Delta\varepsilon_{\mathrm{in}}$ ($10^{-3}$/cycle)", loc="left")
    a2 = ax[1, 2]
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
        sc = a2.scatter(xy[:, 0] + off, xy[:, 1], c=du, s=0.6, cmap="magma_r", vmin=0,
                        vmax=vmax)
        c = js["critical"]
        a2.plot(c["x_mm"] + off, c["y_mm"], "o", ms=4, mfc="none", mec="k", mew=0.8)
        a2.text(off, -17.5, a, ha="center", va="top", fontsize=7)
    a2.set_aspect("equal")
    a2.set_xticks([])
    a2.set_yticks([])
    for sp in a2.spines.values():
        sp.set_visible(False)
    a2.set_title(r"(f) $\Delta u$ at every legal site, HV-S0", loc="left")
    fig.colorbar(sc, ax=a2, label=r"$\Delta u$ ($\mu$m)", shrink=0.8, pad=0.16,
                 orientation="horizontal")
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT)
    plt.close(fig)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
