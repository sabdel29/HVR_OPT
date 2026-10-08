#!/usr/bin/env python3
"""Phase-0I-R figures. Only figures that materially help the closure audit."""
from __future__ import annotations
import csv, json, math, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0ir"
P0I = R / "results" / "phase0i"
plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": .3,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
C = {"tot": "#37474f", "el": "#1565c0", "th": "#00838f", "in": "#b71c1c",
     "peeq": "#6a1b9a", "ok": "#1b5e20", "warn": "#ef6c00", "grey": "#9e9e9e"}
rows = lambda p: list(csv.DictReader(open(p)))
F = lambda r, k: float(r[k])


def fig_A():
    """Strain decomposition through the cycles."""
    d = [r for r in rows(OUT / "strain_component_decomposition.csv") if r["model"] == "EPC"]
    d.sort(key=lambda r: F(r, "time_s"))
    t = [F(r, "time_s") for r in d]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10.2, 6.2), sharex=True,
                                 gridspec_kw={"height_ratios": [2, 1]})
    for k, lab, c in (("eq_total", "total  eq($\\varepsilon$)", C["tot"]),
                      ("eq_elastic", "elastic", C["el"]),
                      ("eq_thermal", "thermal  $|\\alpha\\Delta T|$", C["th"]),
                      ("eq_inelastic_from_decomposition",
                       "inelastic (total $-$ elastic $-$ thermal)", C["in"])):
        a1.plot(t, [F(r, k) for r in d], "-", color=c, lw=1.5, label=lab)
    a1.plot(t, [F(r, "PEEQ_solver") for r in d], "--", color=C["peeq"], lw=1.6,
            label="PEEQ (solver, ACCUMULATED)")
    a1.set(ylabel="equivalent strain", yscale="log",
           title="FIG-0I-R-A  Strain decomposition, full model (EPC), volume-averaged over the "
                 "solder core")
    a1.legend(fontsize=7.5, ncol=2, loc="lower right")
    rat = [F(r, "PEEQ_solver") / F(r, "eq_inelastic_from_decomposition")
           if F(r, "eq_inelastic_from_decomposition") > 1e-12 else np.nan for r in d]
    a2.plot(t, rat, "-", color=C["peeq"], lw=1.4)
    a2.axhline(1.0, color="k", ls="--", lw=1)
    a2.set(xlabel="time (s)", ylabel="PEEQ / eq($\\varepsilon_{in}$)", yscale="log")
    a2.text(.015, .88, "= 1.003 at the FIRST output -- the identity holds.\n"
            "It then grows because PEEQ ACCUMULATES while the\n"
            "instantaneous state oscillates. PEEQ is a PATH LENGTH.",
            transform=a2.transAxes, va="top", fontsize=7.5, color=C["peeq"])
    for k in range(1, 8):
        for ax in (a1, a2):
            ax.axvline(300 * k, color=C["grey"], lw=.5, alpha=.6)
    fig.savefig(OUT / "FIG_0IR_A_strain_decomposition.png"); plt.close(fig)


def fig_B():
    """Plastic-only vs creep-inclusive: the two metrics disagree in DIRECTION."""
    d = rows(OUT / "strain_vs_energy_damage_diagnostic.csv")
    order = ["EP", "EC", "EPC"]
    d = sorted(d, key=lambda r: order.index(r["model"]))
    lab = {"EP": "EP\nelastic+plastic\nNO creep", "EC": "EC\nelastic+creep\nNO plasticity",
           "EPC": "EPC\nfull\n(Phase 0I)"}
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.6, 4.4))
    x = np.arange(3)
    s = [F(r, "d_peeq_per_cycle") for r in d]
    w = [F(r, "inelastic_work_MJ_per_m3") for r in d]
    a1.bar(x, s, color=[C["grey"], C["warn"], C["in"]], alpha=.9)
    for i, v in enumerate(s):
        a1.text(i, v * 1.02, f"{v:.3e}", ha="center", fontsize=8)
        if i:
            a1.text(i, v * .5, f"{100*(v-s[0])/s[0]:+.1f} %", ha="center", fontsize=10,
                    color="w", fontweight="bold")
    a1.set(xticks=x, xticklabels=[lab[r["model"]] for r in d], ylim=(0, max(s) * 1.18),
           ylabel="$\\Delta\\varepsilon_{in}$ per stabilised cycle",
           title="(a) STRAIN-based metric: creep makes it FALL")
    a2.bar(x, w, color=[C["grey"], C["warn"], C["in"]], alpha=.9)
    for i, v in enumerate(w):
        a2.text(i, v * 1.02, f"{v:.3f}", ha="center", fontsize=8)
        if i:
            a2.text(i, v * .5, f"{100*(v-w[0])/w[0]:+.1f} %", ha="center", fontsize=10,
                    color="w", fontweight="bold")
    a2.set(xticks=x, xticklabels=[lab[r["model"]] for r in d], ylim=(0, max(w) * 1.18),
           ylabel="dissipated inelastic work (MJ/m$^3$)",
           title="(b) ENERGY-based metric: creep makes it RISE")
    fig.suptitle("FIG-0I-R-B  The same three solves. Enabling creep moves the strain metric "
                 "$-$29.8 % and the energy metric $+$164.6 %.\n"
                 "\"Damage decreased\" is only true of the strain measure and must never be "
                 "written without naming it.", fontsize=10, y=1.06)
    fig.savefig(OUT / "FIG_0IR_B_strain_vs_energy.png"); plt.close(fig)


def fig_C():
    """Relative life vs the assumed exponent."""
    d = rows(OUT / "relative_life_exponent_sensitivity.csv")
    m = [F(r, "m_fatigue_exponent") for r in d]
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    ax.axvspan(1.5, 3.0, color=C["warn"], alpha=.12)
    ax.plot(m, [F(r, "relative_life_Z2_over_Z1") for r in d], "o-", color=C["ok"],
            ms=5, label="Z2 backside / Z1 embedded")
    ax.plot(m, [F(r, "relative_life_Z4_over_Z1") for r in d], "s-", color=C["in"],
            ms=5, label="Z4 power die / Z1 embedded")
    ax.axhline(1.0, color="k", lw=1)
    ax.set(xlabel="assumed fatigue exponent $m$  in  $N_f = C\\,\\Delta\\varepsilon_{in}^{-m}$",
           ylabel="relative life vs Z1", yscale="log",
           title="FIG-0I-R-C  Relative life is NOT parameter-free.\n"
                 "$C$ cancels in a ratio; the exponent $m$ does not.")
    ax.legend(fontsize=9)
    ax.text(2.25, .55, "the range Phase 0I used\nto claim '1.9-3.8x'\nUNSOURCED",
            ha="center", fontsize=8.5, color=C["warn"])
    ax.text(.985, .96, "over $m$ = 0.5 to 5 the Z2/Z1 ratio spans 1.25 to 9.18\n"
            "-- a factor of 7.4 from the exponent alone",
            transform=ax.transAxes, ha="right", va="top", fontsize=8.5,
            bbox=dict(fc="#fff8e1", ec=C["warn"], lw=.9))
    fig.savefig(OUT / "FIG_0IR_C_relative_life_exponent.png"); plt.close(fig)


def fig_D():
    """Electrical differences against uncertainty."""
    d = rows(OUT / "electrical_architecture_resolution.csv")
    fig, ax = plt.subplots(figsize=(9.2, 4.4))
    y = np.arange(len(d))
    diff = [abs(F(r, "difference_mW")) for r in d]
    unc = [F(r, "uncertainty_mW") for r in d]
    ax.barh(y, diff, color=[C["ok"] if F(r, "sigma") >= 3 else C["in"] for r in d],
            alpha=.85, height=.5, label="modelled difference")
    ax.errorbar(diff, y, xerr=unc, fmt="none", ecolor="k", elinewidth=2, capsize=6,
                label="combined uncertainty")
    ax.set(yticks=y, yticklabels=[r["comparison"] for r in d], xscale="log",
           xlabel="electrical difference (mW, log scale)",
           title="FIG-0I-R-D  Is the architecture electrical difference resolved?")
    for i, r in enumerate(d):
        ax.text(diff[i] * 1.06, i + .22,
                f"{F(r,'sigma'):.2f}$\\sigma$ -> {r['verdict']}", fontsize=9,
                color=C["ok"] if F(r, "sigma") >= 3 else C["in"], va="center")
    ax.legend(fontsize=8, loc="lower right")
    ax.text(.015, .06, "Every tier except P$_{TSV}$ is bit-identical, so those errors cancel.\n"
            "The dominant term is one the sweep SET TO ZERO: T$_c$ was frozen at 85 C, yet\n"
            "Z4 runs 1.444 K cooler -- 214 mW at 148 mW/K, and of the opposite sign.",
            transform=ax.transAxes, fontsize=7.8, color="#333")
    fig.savefig(OUT / "FIG_0IR_D_electrical_resolution.png"); plt.close(fig)


def fig_E():
    """Warpage vs local damage: same direction, very different sensitivity."""
    d = [r for r in rows(P0I / "thickness_by_architecture.csv")]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.0, 4.3))
    col = {"ARCH_Z1_EMBEDDED": "#1565c0", "ARCH_Z2_BACKSIDE": "#1b5e20",
           "ARCH_Z4_POWER_DIE": "#b71c1c"}
    sh = {k: k[7:].replace("_", " ").title() for k in col}
    for a in col:
        s = sorted([r for r in d if r["arch"] == a], key=lambda r: F(r, "h_sub_mm"))
        if not s:
            continue
        a1.plot([F(r, "die_warpage_pv_um") for r in s], [F(r, "d_eps_in_stab") for r in s],
                "o-", color=col[a], ms=5, label=sh[a])
        w0, d0 = F(s[0], "die_warpage_pv_um"), F(s[0], "d_eps_in_stab")
        a2.plot([100 * (F(r, "die_warpage_pv_um") - w0) / w0 for r in s],
                [100 * (F(r, "d_eps_in_stab") - d0) / d0 for r in s],
                "o-", color=col[a], ms=5, label=sh[a])
    a1.set(xlabel="die warpage P-V (µm)", ylabel="$\\Delta\\varepsilon_{in}$ per cycle",
           title="(a) same direction within each sweep")
    a1.legend(fontsize=8)
    lim = [-60, 5]
    a2.plot(lim, lim, "--", color="k", lw=1, label="1:1 (a calibrated surrogate)")
    a2.set(xlabel="change in warpage (%)", ylabel="change in local damage (%)",
           xlim=lim, ylim=(-25, 5), title="(b) but a 3-5x different SENSITIVITY")
    a2.legend(fontsize=8, loc="lower right")
    a2.text(.5, .1, "warpage moves 29.7-52.6 % where damage moves 5.6-17.2 %:\n"
            "warpage EXAGGERATES the reliability benefit of a thicker substrate",
            transform=a2.transAxes, ha="center", fontsize=8, color=C["warn"])
    fig.suptitle("FIG-0I-R-E  Global warpage tracks the DIRECTION of local damage, not its "
                 "magnitude. It is not a calibrated surrogate.", fontsize=10.5, y=1.02)
    fig.savefig(OUT / "FIG_0IR_E_warpage_vs_damage.png"); plt.close(fig)


if __name__ == "__main__":
    for fn in (fig_A, fig_B, fig_C, fig_D, fig_E):
        try:
            fn(); print(f"  {fn.__name__} ok", flush=True)
        except Exception as e:
            print(f"  {fn.__name__} FAILED: {type(e).__name__}: {e}", flush=True)
    print()
    for p in sorted(OUT.glob("FIG_0IR_*.png")):
        print(f"  {p.name}  {p.stat().st_size/1024:.0f} kB")
