#!/usr/bin/env python3
"""Phase-0J figures (Sec.34). Only figures that carry a result."""
from __future__ import annotations
import csv, math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0j"
plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": .3,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
C = {"z1": "#1565c0", "z2": "#1b5e20", "z4": "#b71c1c", "grey": "#9e9e9e",
     "bad": "#c62828", "warn": "#ef6c00", "ok": "#2e7d32", "ink": "#37474f"}
rows = lambda p: list(csv.DictReader(open(OUT / p)))
F = lambda r, k: float(r[k])
SHORT = {"ARCH_Z1_EMBEDDED": "Z1 embedded", "ARCH_Z2_BACKSIDE": "Z2 backside",
         "ARCH_Z4_POWER_DIE": "Z4 power die"}
CC = {"ARCH_Z1_EMBEDDED": C["z1"], "ARCH_Z2_BACKSIDE": C["z2"], "ARCH_Z4_POWER_DIE": C["z4"]}


def fig_A():
    """Literature -> admissibility funnel."""
    db = rows("SAC305_LIFE_LAW_DATABASE.csv")
    n_raw = sum(1 for _ in open(OUT / "life_law_search_raw.csv")) - 1
    stages = [("works harvested\n(15 queries x 2 indices)", n_raw, C["grey"]),
              ("candidate life LAWS\nidentified", len(db), C["ink"]),
              ("primary calibration\npaper RETRIEVABLE", 0, C["bad"]),
              ("ADMISSIBLE\nfor this metric/regime", 0, C["bad"])]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.6, 4.4),
                                 gridspec_kw={"width_ratios": [1, 1.35]})
    y = np.arange(len(stages))[::-1]
    a1.barh(y, [s[1] for s in stages], color=[s[2] for s in stages], height=.6)
    for yy, (lab, n, _) in zip(y, stages):
        a1.text(max(n, 0) + n_raw * .02, yy, f"{n}", va="center", fontweight="bold")
    a1.set_yticks(y); a1.set_yticklabels([s[0] for s in stages], fontsize=8)
    a1.set_xlabel("count"); a1.set_xlim(0, n_raw * 1.15)
    a1.set_title("Sec.3-6 funnel: 0 admissible", fontweight="bold")
    # criteria failure tally
    crit = [c for c in db[0] if c[0].isdigit()]
    fails = [sum(1 for r in db if r[c] == "FAIL") for c in crit]
    a2.barh(np.arange(len(crit)), fails, color=C["warn"], height=.62)
    a2.set_yticks(np.arange(len(crit)))
    a2.set_yticklabels([c.split("_", 1)[1].replace("_", " ")[:38] for c in crit], fontsize=7.5)
    a2.invert_yaxis(); a2.set_xlabel("candidates failing (of 10)")
    a2.set_title("which admissibility criterion fails", fontweight="bold")
    a2.set_xlim(0, 10)
    for i, n in enumerate(fails):
        a2.text(n + .12, i, str(n), va="center", fontsize=8)
    fig.savefig(OUT / "FIG_0J_A_admissibility_funnel.png"); plt.close(fig)


def fig_B():
    """Sec.29 -- the calibration plot that CANNOT be drawn, drawn honestly."""
    lt = rows("lifetime_by_law_and_architecture.csv")
    r = lt[0]
    Cc = F(r, "C_constant")
    eps = np.logspace(-3.6, -1.4, 200)
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    ax.loglog(eps, 1 / (Cc * eps), color=C["ink"], lw=2,
              label=f"Syed 2004 SnAgCu form, $N_f=(C\\,\\varepsilon_{{acc}})^{{-1}}$, C={Cc}")
    ax.loglog(eps, 1 / (0.013 * eps), color=C["ink"], lw=1.2, ls="--",
              label="same form with $C_I$=0.013 (other mechanism)")
    nat = {x["arch"]: x for x in rows("native_metrics_by_architecture.csv")
           if (x["arch"], x["h_sub_mm"]) in [("ARCH_Z1_EMBEDDED", "1.3"),
                                             ("ARCH_Z2_BACKSIDE", "0.3"),
                                             ("ARCH_Z4_POWER_DIE", "0.3")]}
    for a, x in nat.items():
        e = F(x, "M1_accum_inelastic_path")
        ax.plot(e, 1 / (Cc * e), "o", ms=11, color=CC[a], mec="k", mew=.8, zorder=5)
        off = {"ARCH_Z2_BACKSIDE": (-16, 16), "ARCH_Z1_EMBEDDED": (14, 12),
               "ARCH_Z4_POWER_DIE": (12, -22)}[a]
        ax.annotate(f"{SHORT[a]}\n{1/(Cc*e):.0f}", (e, 1 / (Cc * e)),
                    textcoords="offset points", xytext=off, fontsize=8, color=CC[a],
                    fontweight="bold",
                    arrowprops=dict(arrowstyle="-", color=CC[a], lw=.8, shrinkA=0, shrinkB=7))
    ax.axvspan(eps[0], eps[-1], color=C["bad"], alpha=.05)
    ax.text(.03, .07, "NO EXPERIMENTAL CALIBRATION POINTS CAN BE PLOTTED.\n"
                      "The primary calibration papers (Syed 2004, Schubert 2003,\n"
                      "Darveaux 2002) are paywalled with no legal open-access copy,\n"
                      "and none of 139 open-access citing papers reprints their data.\n"
                      "The law's calibrated domain is therefore UNKNOWN, so whether\n"
                      "these three points interpolate or extrapolate CANNOT BE STATED.",
            transform=ax.transAxes, fontsize=8.2, va="bottom",
            bbox=dict(fc="#fff3e0", ec=C["bad"], lw=1.3, boxstyle="round,pad=0.5"))
    ax.set_xlabel("accumulated inelastic strain per stabilised cycle,  M1")
    ax.set_ylabel("cycles to failure $N_f$")
    ax.set_title("FIG-0J-B  Conditional life law and our operating points — "
                 "NOT a validated calibration", fontweight="bold", fontsize=10)
    ax.legend(fontsize=8, loc="upper right"); ax.grid(True, which="both", alpha=.25)
    fig.savefig(OUT / "FIG_0J_B_calibration_not_reproducible.png"); plt.close(fig)


def fig_C():
    """Native M1 / M2 / M3 by architecture, and the M1/M2 ratio."""
    nat = rows("native_metrics_by_architecture.csv")
    fig, ax = plt.subplots(1, 4, figsize=(13.4, 3.9))
    for k, (key, lab, sc) in enumerate((
            ("M1_accum_inelastic_path", "M1  accumulated inelastic path", 1e3),
            ("M2_strain_range", "M2  direct strain RANGE", 1e3),
            ("M3_inelastic_work_MJ_per_m3", "M3  inelastic work (MJ/m$^3$)", 1),
            ("M1_over_M2", "M1 / M2  ratio", 1))):
        for a in SHORT:
            rs = sorted([x for x in nat if x["arch"] == a], key=lambda x: F(x, "h_sub_mm"))
            ax[k].plot([F(x, "h_sub_mm") for x in rs], [F(x, key) * sc for x in rs],
                       "o-", color=CC[a], ms=5, label=SHORT[a])
        ax[k].set_xlabel("$h_{sub}$ (mm)")
        ax[k].set_title(lab + ("  [$\\times 10^{-3}$]" if sc == 1e3 else ""), fontsize=9)
    ax[3].axhline(3.72, color=C["bad"], ls="--", lw=1.4)
    ax[3].text(.55, 3.72, " Phase-0I-R 3.72\n (fully-reversed cycle)", color=C["bad"],
               fontsize=7.6, va="bottom")
    ax[3].set_ylim(1.6, 4.1)
    ax[3].text(.55, 2.09, " all 11 DVPD cases: 2.023-2.027", color=C["ok"], fontsize=7.8)
    ax[0].legend(fontsize=7.6)
    fig.suptitle("FIG-0J-C  The three metrics agree on ranking; the M1/M2 ratio is set by the "
                 "LOADING PATH, not the architecture", fontweight="bold", fontsize=10)
    fig.savefig(OUT / "FIG_0J_C_native_metrics.png"); plt.close(fig)


def fig_D():
    """Conditional life by architecture, with the two uncertainty classes separated."""
    lt = rows("lifetime_by_law_and_architecture.csv")
    base = lt[0]
    archs = list(SHORT)
    nf = [F(base, {"ARCH_Z1_EMBEDDED": "Z1_life", "ARCH_Z2_BACKSIDE": "Z2_life",
                   "ARCH_Z4_POWER_DIE": "Z4_life"}[a]) for a in archs]
    lo = [F(lt[1], k) for k in ("Z1_life", "Z2_life", "Z4_life")]     # creep-only eps_acc
    hi = [F(lt[2], k) for k in ("Z1_life", "Z2_life", "Z4_life")]     # C_I instead of C_II
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.8, 4.4),
                                 gridspec_kw={"width_ratios": [1.25, 1]})
    x = np.arange(3)
    a1.bar(x, nf, .5, color=[CC[a] for a in archs], zorder=3)
    a1.errorbar(x, nf, yerr=[np.array(nf) - np.array(lo), np.array(hi) - np.array(nf)],
                fmt="none", ecolor="k", capsize=6, lw=1.4, zorder=4)
    for i, (v, l, h) in enumerate(zip(nf, lo, hi)):
        a1.text(i, h * 1.04, f"{v:.0f}", ha="center", fontweight="bold", fontsize=9)
    a1.set_xticks(x); a1.set_xticklabels([SHORT[a] for a in archs], fontsize=8.5)
    a1.set_ylabel("cycles  (CONDITIONAL — not validated)")
    a1.set_title("absolute life: bars are conditional, error bars span only\n"
                 "the modelling choices INSIDE the law", fontsize=9, fontweight="bold")
    a1.set_ylim(0, max(hi) * 1.22)
    a1.text(.5, .93, "ABSOLUTE LEVEL IS NOT DEFENSIBLE\n(0 admissible laws; reproduction "
            "impossible)", transform=a1.transAxes, ha="center", fontsize=8, color=C["bad"],
            bbox=dict(fc="#ffebee", ec=C["bad"], boxstyle="round,pad=0.35"))
    # relative: the part that IS defensible
    rel = [1.0, F(base, "Z2_over_Z1"), F(base, "Z4_over_Z1")]
    a2.bar(x, rel, .5, color=[CC[a] for a in archs], zorder=3)
    a2.axhline(1, color="k", lw=1)
    for i, v in enumerate(rel):
        a2.text(i, v + .03, f"{v:.3f}", ha="center", fontweight="bold", fontsize=9)
    a2.set_xticks(x); a2.set_xticklabels([SHORT[a] for a in archs], fontsize=8.5)
    a2.set_ylabel("life relative to Z1")
    a2.set_title("relative life: C cancels AND the Syed form has\nNO free exponent",
                 fontsize=9, fontweight="bold")
    a2.set_ylim(0, 1.85)
    fig.suptitle("FIG-0J-D  Predicted life by architecture — absolute conditional, "
                 "relative parameter-free", fontweight="bold", fontsize=10)
    fig.savefig(OUT / "FIG_0J_D_life_by_architecture.png"); plt.close(fig)


def fig_E():
    """Model-form comparison across the three metric families."""
    mf = rows("lifetime_model_form_comparison.csv")
    fams = ["A_STRAIN_RANGE", "B_ENERGY", "C_CREEP_DAMAGE"]
    col = {"A_STRAIN_RANGE": C["z1"], "B_ENERGY": C["warn"], "C_CREEP_DAMAGE": C["z2"]}
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.6, 4.3))
    for f in fams:
        d = sorted([r for r in mf if r["law_family"] == f], key=lambda r: F(r, "assumed_exponent_m"))
        a1.plot([F(r, "assumed_exponent_m") for r in d], [F(r, "Z2_over_Z1_life") for r in d],
                "o-", color=col[f], label=f"{f}  ({d[0]['native_metric']})", ms=5)
        a2.plot([F(r, "assumed_exponent_m") for r in d], [F(r, "Z4_over_Z1_life") for r in d],
                "o-", color=col[f], ms=5)
    for a, t in ((a1, "Z2 / Z1"), (a2, "Z4 / Z1")):
        a.axhline(1, color="k", lw=1); a.set_xlabel("assumed fatigue exponent  m")
        a.set_ylabel("life ratio"); a.set_title(t, fontweight="bold")
    a1.plot(1.0, [F(r, "Z2_over_Z1_life") for r in mf
                  if r["law_family"] == "C_CREEP_DAMAGE" and F(r, "assumed_exponent_m") == 1][0],
            "*", ms=20, color=C["bad"], zorder=6,
            label="Syed form: m FIXED at 1, not assumed")
    a1.legend(fontsize=7.4, loc="upper left")
    a1.text(.97, .04, "ranking Z2 > Z1 > Z4 in EVERY family\nand at EVERY exponent",
            transform=a1.transAxes, ha="right", fontsize=8, color=C["ok"],
            bbox=dict(fc="#e8f5e9", ec=C["ok"], boxstyle="round,pad=0.35"))
    fig.suptitle("FIG-0J-E  Model-form comparison: the RANKING is robust, the MAGNITUDE is not",
                 fontweight="bold", fontsize=10)
    fig.savefig(OUT / "FIG_0J_E_model_form.png"); plt.close(fig)


def fig_F():
    """Electrical loss versus predicted fatigue life."""
    ec = rows("electrical_cost_of_reliability.csv")
    nat = {x["arch"]: x for x in rows("native_metrics_by_architecture.csv")
           if (x["arch"], x["h_sub_mm"]) in [("ARCH_Z1_EMBEDDED", "1.3"),
                                             ("ARCH_Z2_BACKSIDE", "0.3"),
                                             ("ARCH_Z4_POWER_DIE", "0.3")]}
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.8, 4.3))
    for a, x in nat.items():
        r = [e for e in ec if e["comparison"].startswith(a[5:7])]
        mult = 1.0 if a == "ARCH_Z1_EMBEDDED" else F(
            [e for e in r if "fixed" in e["law_family"]][0], "life_multiple_vs_Z1")
        a1.plot(F(x, "P_elec_total_w"), mult, "o", ms=13, color=CC[a], mec="k", mew=.8)
        a1.annotate(f"{SHORT[a]}\n{F(x,'P_elec_total_w'):.2f} W, {mult:.2f}x",
                    (F(x, "P_elec_total_w"), mult), textcoords="offset points",
                    xytext=(11, -4), fontsize=8, color=CC[a], fontweight="bold")
    a1.axhline(1, color="k", lw=1, ls=":")
    a1.set_xlabel("total electrical loss (W, SYSTEM)")
    a1.set_ylabel("life multiple vs Z1  (Syed form, m = 1)")
    a1.set_xlim(125.6, 128.6); a1.set_ylim(.8, 1.75)
    a1.set_title("the ETM trade, in life rather than warpage", fontweight="bold", fontsize=9)
    a1.text(.5, .06, "+1.688 W buys 1.56x life  —  supersedes W per um of warpage",
            transform=a1.transAxes, ha="center", fontsize=8.4, color=C["ink"],
            bbox=dict(fc="#eceff1", ec=C["ink"], boxstyle="round,pad=0.35"))
    d = [e for e in ec if e["comparison"].startswith("Z2") and e["W_per_decade_of_life"] != "n/a"]
    lab = [f"{e['native_metric']}\nm={e['exponent_m']}" for e in d]
    a2.bar(np.arange(len(d)), [F(e, "W_per_decade_of_life") for e in d], .55,
           color=[C["z2"] if "fixed" in e["law_family"] else C["grey"] for e in d])
    a2.set_xticks(np.arange(len(d))); a2.set_xticklabels(lab, fontsize=7)
    a2.set_ylabel("W per decade of $N_f$")
    a2.set_title("Z1 $\\rightarrow$ Z2 exchange rate (green = exponent fixed by the law form)",
                 fontweight="bold", fontsize=9)
    fig.suptitle("FIG-0J-F  Electrical cost of reliability", fontweight="bold", fontsize=10)
    fig.savefig(OUT / "FIG_0J_F_electrical_cost.png"); plt.close(fig)


def fig_G():
    """Mission-life sweep and the crossover band."""
    ms = rows("mission_life_sensitivity.csv")
    lt = rows("lifetime_by_law_and_architecture.csv")[0]
    nf = {a: F(lt, k) for a, k in zip(SHORT, ("Z1_life", "Z2_life", "Z4_life"))}
    fig, ax = plt.subplots(figsize=(9.6, 4.6))
    N = [F(r, "N_required_PARAMETRIC") for r in ms]
    for a in SHORT:
        ax.axhline(nf[a], color=CC[a], lw=2, label=f"{SHORT[a]}  $N_f$ = {nf[a]:.0f}")
    lo, hi = nf["ARCH_Z1_EMBEDDED"], nf["ARCH_Z2_BACKSIDE"]
    ax.axhspan(lo, hi, color=C["ok"], alpha=.18)
    ax.text(1.4e2, math.sqrt(lo * hi), "  MISSION-LIFE CROSSOVER\n  only Z2 feasible here\n"
            f"  width = {hi/lo:.3f}x (independent of C)", fontsize=8.6, va="center",
            color=C["ok"], fontweight="bold")
    ax.plot(N, N, "k--", lw=1.2, label="$N_{required}$ (parametric sweep)")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("$N_{required}$  — PARAMETRIC MISSION SENSITIVITY, not a qualification value")
    ax.set_ylabel("cycles")
    ax.set_title("FIG-0J-G  Where architecture feasibility would change — "
                 "position CONDITIONAL, width is not", fontweight="bold", fontsize=10)
    ax.legend(fontsize=8, loc="upper left")
    ax.text(.985, .04, "$N_{required}$ = OPEN — no source-backed field mission requirement exists",
            transform=ax.transAxes, ha="right", fontsize=8.2, color=C["bad"],
            bbox=dict(fc="#ffebee", ec=C["bad"], boxstyle="round,pad=0.35"))
    fig.savefig(OUT / "FIG_0J_G_mission_sweep.png"); plt.close(fig)


def fig_H():
    """Temperature -> metric -> life."""
    tp = rows("temperature_shift_to_life.csv")
    cr = rows("creep_effect_by_architecture.csv")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.8, 4.3))
    dep = [r for r in tp if "DEPENDENT" in r["model"] and "INDEPENDENT" not in r["model"]]
    ind = [r for r in tp if "INDEPENDENT" in r["model"]]
    for d, lab, c in ((dep, "temperature-DEPENDENT material model", C["z4"]),
                      (ind, "temperature-INDEPENDENT (frozen properties)", C["grey"])):
        d = sorted(d, key=lambda r: F(r, "exponent_m"))
        a1.plot([F(r, "exponent_m") for r in d], [F(r, "life_multiple") for r in d],
                "o-", color=c, ms=6, label=lab)
    a1.axhline(1, color="k", lw=1); a1.set_xlabel("fatigue exponent  m")
    a1.set_ylabel("life multiple after a +50 K mean-temperature shift")
    a1.legend(fontsize=7.6); a1.set_title("thermal $\\rightarrow$ material $\\rightarrow$ "
                                          "damage $\\rightarrow$ life", fontweight="bold",
                                          fontsize=9)
    a1.text(.5, .1, "m = 1 is fixed by the Syed form: $-$18.5 % life per +50 K",
            transform=a1.transAxes, ha="center", fontsize=8.2,
            bbox=dict(fc="#eceff1", ec=C["ink"], boxstyle="round,pad=0.3"))
    x = np.arange(3); w = .36
    for i, (key, lab, c) in enumerate((("M1_accum_inelastic_path_vs_EP_pct",
                                        "M1 strain path", C["z1"]),
                                       ("M3_inelastic_work_MJ_per_m3_vs_EP_pct",
                                        "M3 inelastic work", C["warn"]))):
        v = [F([r for r in cr if r["arch"] == a and r["model"] == "EPC"][0], key)
             for a in SHORT]
        a2.bar(x + (i - .5) * w, v, w, color=c, label=lab)
        for xx, vv in zip(x + (i - .5) * w, v):
            a2.text(xx, vv + (6 if vv > 0 else -14), f"{vv:+.0f}%", ha="center", fontsize=7.6)
    a2.axhline(0, color="k", lw=1); a2.set_xticks(x)
    a2.set_xticklabels([SHORT[a] for a in SHORT], fontsize=8.5)
    a2.set_ylabel("change when creep is ENABLED (vs EP), %")
    a2.legend(fontsize=7.8); a2.set_ylim(-60, 200)
    a2.set_title("Sec.12: the two law families disagree on the SIGN of creep",
                 fontweight="bold", fontsize=9)
    fig.suptitle("FIG-0J-H  Mean-temperature shift, and the creep question",
                 fontweight="bold", fontsize=10)
    fig.savefig(OUT / "FIG_0J_H_temperature_and_creep.png"); plt.close(fig)


if __name__ == "__main__":
    for f in (fig_A, fig_B, fig_C, fig_D, fig_E, fig_F, fig_G, fig_H):
        f(); print("  ok", f.__name__)
    for p in sorted(OUT.glob("FIG_0J_*.png")):
        print(f"  {p.name:46} {p.stat().st_size:>8} B")
