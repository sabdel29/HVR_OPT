"""Manuscript figures of the physical lineage, read from the artifacts.

fig9_physical.pdf: small multiples, one quantity per panel (no second y-axis): (a) loss,
(b) peak temperature, (c) die warpage, (d) critical-joint displacement driver, (e) local
inelastic strain per cycle with its measured discretisation uncertainty, per named scenario;
(f) the joint driver at every legal site at HV-S0.
fig10_crossover.pdf: the direct-feed crossover (direct_feed_crossover.json): total loss,
system efficiency and feed loss against the swept external loop resistance, one panel each.
fig11_power_path.pdf, fig12_package_sections.pdf: the presentation's generated
architecture SVGs (measured layer order), converted to vector PDF by rsvg-convert.
No value is typed here; a rerun redraws every figure.
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
OUT_X = R / "manuscript" / "figs" / "fig10_crossover.pdf"
SVG_PDF = {"fig11_power_path.pdf": "z1_z2_power_path_final.svg",
           "fig12_package_sections.pdf": "z1_z2_package_comparison.svg"}
PRES_FIGS = R / "presentation" / "prelim_hvr" / "figs"
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
    crossover_figure()
    svg_figures()


def crossover_figure():
    """Total loss, efficiency and feed loss vs R_Z2_direct_feed_loop, shared log x. Z2 lines
    per scenario; Z1's converged loss as a horizontal reference; R* marked. A scenario whose
    Z1 operating point is inadmissible has no valid reference and is not drawn."""
    cx = J("direct_feed_crossover.json")
    sty = {"HV_S0": "-", "HV_S1": "--", "HV_S2": ":"}
    fig, ax = plt.subplots(3, 1, figsize=(3.5, 4.6), sharex=True)
    drawn, p_lo, p_hi, e_lo, e_hi = [], [], [], [], []
    for s_, c in cx["scenarios"].items():
        if c.get("Z1_operating_point_inadmissible"):
            continue
        sw = [p for p in c["sweep"] if p.get("feasible", True)]   # none above R_max
        r = np.array([p["R_mohm"] for p in sw])
        ax[0].plot(r, [p["P_total_w"] for p in sw], sty[s_], color=COL["Z2"], lw=1.0,
                   label=f"Z2, {LAB[s_]}")
        ax[0].axhline(c["P_Z1_w"], ls=sty[s_], color=COL["Z1"], lw=0.8,
                      label=f"Z1, {LAB[s_]}")
        ax[1].plot(r, [100 * p["efficiency"] for p in sw], sty[s_], color=COL["Z2"], lw=1.0)
        ax[1].axhline(100 * c["efficiency_Z1"], ls=sty[s_], color=COL["Z1"], lw=0.8)
        ax[2].plot(r, [p["P_feed_w"] for p in sw], sty[s_], color=COL["Z2"], lw=1.0)
        p_lo += [c["P_Z1_w"], sw[0]["P_total_w"]]
        p_hi.append(c["P_Z1_w"])
        e_lo.append(100 * c["efficiency_Z1"])
        e_hi.append(100 * sw[0]["efficiency"])
        if c.get("R_star_mohm"):
            for a_ in ax[:2]:
                a_.axvline(c["R_star_mohm"], color="0.55", lw=0.6, ls=sty[s_])
            ax[0].plot(c["R_star_mohm"], c["P_Z1_w"], "o", ms=3.5, mfc="white",
                       mec="k", mew=0.7)
            # left of its R* line, above (HV-S1) or below (HV-S0) its Z1 reference, on a
            # white ground so no line runs through the text
            up = s_ != "HV_S0"
            ax[0].annotate(f"$R^*$ = {c['R_star_mohm']:.3g} m$\\Omega$ ({LAB[s_]})",
                           (c["R_star_mohm"], c["P_Z1_w"]), xytext=(-5, 6 if up else -7),
                           textcoords="offset points", fontsize=6.5, ha="right",
                           va="bottom" if up else "top",
                           bbox=dict(boxstyle="square,pad=0.15", fc="white", ec="none"))
        drawn.append(s_)
    if p_lo:                       # scaled to the crossover region; curves leave the frame
        lo, hi = min(p_lo), max(p_hi)
        ax[0].set_ylim(lo - 0.45 * (hi - lo) - 5, hi + 0.9 * (hi - lo) + 10)   # room for labels
        ax[1].set_ylim(min(e_lo) - 6, max(e_hi) + 2)
    ax[2].set_xscale("log")
    ax[2].set_yscale("log")
    ax[0].set_ylabel("loss (W)")
    ax[1].set_ylabel("efficiency (%)")
    ax[2].set_ylabel("feed loss (W)")
    ax[2].set_xlabel(r"$R_{\mathrm{Z2,\,direct\ feed\ loop}}$ (m$\Omega$)")
    for a_, t_ in zip(ax, ("(a) platform-to-load loss (crossover region)",
                           "(b) system efficiency", "(c) external feed loss")):
        a_.set_title(t_, loc="left")
    # the legend sits in the empty upper-left corner of (c), clear of the R* labels in (a)
    h, lab = ax[0].get_legend_handles_labels()
    ax[2].legend(h, lab, frameon=False, fontsize=6, ncol=2, loc="upper left")
    fig.tight_layout()
    fig.savefig(OUT_X)
    plt.close(fig)
    print("wrote", OUT_X, "scenarios", drawn)


def svg_figures():
    import shutil
    import subprocess
    exe = shutil.which("rsvg-convert")
    if exe is None:
        raise SystemExit("rsvg-convert not found: cannot convert the architecture figures")
    for pdf, svg in SVG_PDF.items():
        src = PRES_FIGS / svg
        subprocess.run([exe, "-f", "pdf", "-o", str(OUT.parent / pdf), str(src)], check=True)
        print("wrote", OUT.parent / pdf, "from", src.name)


if __name__ == "__main__":
    main()
