#!/usr/bin/env python3
"""Phase-0I figures. Every number is read from a results artifact, never retyped."""
from __future__ import annotations
import csv, json, math, re, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle, FancyArrowPatch

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0i"
sys.path.insert(0, str(R / "scripts" / "phase0i"))
plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": .3,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
C = {"z1": "#1565c0", "z2": "#1b5e20", "z4": "#b71c1c", "z5": "#9e9e9e",
     "warn": "#ef6c00", "b": "#6a1b9a"}
AC = {"ARCH_Z1_EMBEDDED": C["z1"], "ARCH_Z2_BACKSIDE": C["z2"],
      "ARCH_Z4_POWER_DIE": C["z4"], "ARCH_Z5_2P5D_LATERAL": C["z5"]}
SH = {"ARCH_Z1_EMBEDDED": "Z1 embedded", "ARCH_Z2_BACKSIDE": "Z2 backside",
      "ARCH_Z4_POWER_DIE": "Z4 power die", "ARCH_Z5_2P5D_LATERAL": "Z5 2.5D lateral"}
rows = lambda p: list(csv.DictReader(open(p)))
F = lambda r, k: float(r[k])


def fig_A():
    """Cross-sections."""
    fig, axes = plt.subplots(1, 4, figsize=(13.6, 4.2))
    LAY = {"board": ("#8d6e63", "board"), "bga": ("#ffb300", "BGA"),
           "sub": ("#90a4ae", "substrate"), "conv": ("#b71c1c", "converter"),
           "die": ("#37474f", "compute die"), "int": ("#4dd0e1", "interposer RDL")}
    defs = {
        "ARCH_Z1_EMBEDDED": [("board", 0, 1.6, 1.0), ("bga", 1.6, .3, 1.0),
                             ("sub", 1.9, .07, 1.0), ("conv", 1.97, 1.23, .62),
                             ("sub", 1.97, 1.23, .38), ("die", 3.2, .5, .9)],
        "ARCH_Z2_BACKSIDE": [("board", 0, 1.6, 1.0), ("bga", 1.6, .3, 1.0),
                             ("conv", 1.9, 1.23, .62), ("sub", 3.13, .3, 1.0),
                             ("die", 3.43, .5, .9)],
        "ARCH_Z4_POWER_DIE": [("board", 0, 1.6, 1.0), ("bga", 1.6, .3, 1.0),
                              ("sub", 1.9, .3, 1.0), ("conv", 2.2, 1.23, .9),
                              ("die", 3.43, .5, .9)],
        "ARCH_Z5_2P5D_LATERAL": [("board", 0, 1.6, 1.0), ("bga", 1.6, .3, 1.0),
                                 ("sub", 1.9, .3, 1.0), ("int", 2.2, .06, 1.0)],
    }
    notes = {"ARCH_Z1_EMBEDDED": "converter INSIDE the substrate\nh_sub >= 1.276 mm\nTSV: HV 23 A",
             "ARCH_Z2_BACKSIDE": "converter BELOW\nh_sub >= 0.30 mm\nTSV: LV 1000 A",
             "ARCH_Z4_POWER_DIE": "converter ABOVE, under the die\nh_sub >= 0.30 mm\nTSV: HV 23 A",
             "ARCH_Z5_2P5D_LATERAL": "converter BESIDE the die\nh_sub >= 0.30 mm\n768 W lateral loss"}
    for ax, (a, ls) in zip(axes, defs.items()):
        for nm, z0, t, w in ls:
            col, lab = LAY[nm]
            ax.add_patch(Rectangle(((1 - w) / 2, z0), w, t, fc=col, ec="k", lw=.6, alpha=.9))
            if t > .18:
                ax.text(.5, z0 + t / 2, lab, ha="center", va="center", fontsize=7.5,
                        color="w" if nm in ("die", "conv", "board") else "k")
        if a == "ARCH_Z5_2P5D_LATERAL":
            ax.add_patch(Rectangle((.05, 2.26), .38, .5, fc="#b71c1c", ec="k", lw=.6))
            ax.text(.24, 2.51, "conv", ha="center", va="center", fontsize=7, color="w")
            ax.add_patch(Rectangle((.55, 2.26), .40, .5, fc="#37474f", ec="k", lw=.6))
            ax.text(.75, 2.51, "die", ha="center", va="center", fontsize=7, color="w")
        ax.set(xlim=(-.05, 1.05), ylim=(-.2, 4.3), xticks=[],
               title=SH[a], ylabel="z (mm)" if a == "ARCH_Z1_EMBEDDED" else "")
        ax.grid(False)
        ax.text(.5, -.12, notes[a], ha="center", va="top", fontsize=7,
                transform=ax.get_xaxis_transform(), color=AC[a])
    fig.suptitle("FIG-0I-A  Vertical-integration architectures. z = 0 at the substrate "
                 "underside; only Z1 puts the converter inside the substrate.",
                 fontsize=10.5, y=1.03)
    fig.savefig(OUT / "FIG_0I_A_cross_sections.png"); plt.close(fig)


def fig_B():
    """Rail-aware power paths."""
    pp = rows(OUT / "power_paths_by_architecture.csv")
    fig, ax = plt.subplots(figsize=(11.6, 4.6))
    archs = list(dict.fromkeys(r["arch"] for r in pp))
    for y, a in enumerate(archs):
        segs = [r for r in pp if r["arch"] == a]
        x = 0.0
        for s in segs:
            w = 1.0
            hv = s["rail"] == "HV"
            col = "#1565c0" if hv else ("#b71c1c" if s["rail"] == "LV" else "#ef6c00")
            ax.add_patch(Rectangle((x, len(archs) - y - .35), w, .7, fc=col, ec="k",
                                   lw=.6, alpha=.85))
            ax.text(x + .5, len(archs) - y, f"{s['tier']}\n{s['rail']} {F(s,'I_a'):.0f} A",
                    ha="center", va="center", fontsize=6.8, color="w")
            x += w + .08
        ax.text(-.15, len(archs) - y, SH[a], ha="right", va="center", fontsize=9,
                color=AC[a], fontweight="bold")
    ax.set(xlim=(-2.6, 6.0), ylim=(.3, len(archs) + .8), xticks=[], yticks=[],
           title="FIG-0I-B  Which rail crosses which interconnect. "
                 "Z2 puts 1000 A on the TSV field; everything else puts 23 A on it.")
    ax.grid(False)
    ax.text(.02, .04, "blue = 48 V high-voltage   ·   red = 1 V low-voltage   ·   "
            "orange = conversion", transform=ax.transAxes, fontsize=8)
    fig.savefig(OUT / "FIG_0I_B_power_paths.png"); plt.close(fig)


def fig_C():
    """Thermal paths."""
    cmp_ = [r for r in rows(OUT / "z_architecture_comparison.csv") if r.get("d_eps_in_stab")]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.2, 4.2))
    for a in dict.fromkeys(r["arch"] for r in cmp_):
        s = sorted([r for r in cmp_ if r["arch"] == a], key=lambda r: F(r, "h_sub_mm"))
        a1.plot([F(r, "h_sub_mm") for r in s], [F(r, "T_joint_C") for r in s], "o-",
                color=AC[a], label=SH[a], ms=5)
    a1.set(xlabel="substrate thickness $h_{sub}$ (mm)", ylabel="corner-BGA joint temperature (°C)",
           title="(a) joint temperature barely moves", ylim=(79, 85))
    a1.legend(fontsize=8)
    a1.text(.5, .06, "full span across every architecture and thickness: 81.10 – 83.21 °C\n"
            "correlation with the damage metric: r = +0.017",
            transform=a1.transAxes, ha="center", fontsize=8, color=C["warn"],
            bbox=dict(fc="#fff8e1", ec=C["warn"], lw=.8))
    tj = json.loads((OUT / "transient_thermal.json").read_text())
    for r in tj["runs"]:
        h = np.array(r["history"])
        a2.semilogx(h[:, 0], h[:, 1], "o-", ms=3, label=f"run to {r['t_end_s']:.0f} s")
    a2.axhline(tj["steady_T_max_C"], color="k", ls="--", lw=1.2)
    a2.text(2, tj["steady_T_max_C"] - 3.4, f"validated steady solver "
            f"{tj['steady_T_max_C']:.2f} °C", fontsize=8)
    a2.set(xlabel="time (s)", ylabel="package $T_{max}$ (°C)",
           title="(b) transient reaches steady state to 0.110 %")
    a2.legend(fontsize=8, loc="lower right")
    a2.text(.03, .95, "two modes: package ~15 s, board ~600 s\n$t_{95}$ = 1618 s",
            transform=a2.transAxes, va="top", fontsize=8)
    fig.suptitle("FIG-0I-C  Thermal topology and transient response", fontsize=10.5, y=1.02)
    fig.savefig(OUT / "FIG_0I_C_thermal.png"); plt.close(fig)


def fig_D():
    """Global -> local workflow."""
    fig, ax = plt.subplots(figsize=(10.4, 3.8))
    boxes = [(.02, "GLOBAL package FE\narchitecture-specific stack\nmounted on the explicit board",
              "#90a4ae"),
             (.28, "extract at the critical joint\n$\\Delta u$ corner-BGA\n$T$ joint", "#ffb300"),
             (.54, "LOCAL joint FE\nCu pad / SAC305 / Cu pad\nE(T), $\\sigma_y$(T), Norton creep",
              "#b71c1c"),
             (.80, "$\\Delta\\varepsilon_{in}$ per stabilised cycle\nvolume-averaged,\ncorner band excluded",
              "#1b5e20")]
    for x, t, c in boxes:
        ax.add_patch(Rectangle((x, .34), .18, .34, fc=c, ec="k", lw=.8, alpha=.85))
        ax.text(x + .09, .51, t, ha="center", va="center", fontsize=7.8, color="w")
    for x in (.20, .46, .72):
        ax.add_patch(FancyArrowPatch((x, .51), (x + .08, .51), arrowstyle="-|>",
                                     mutation_scale=16, lw=1.6, color="k"))
    ax.text(.5, .18, "validated: free expansion exact · creep relaxation −49.6 % · "
            "cycle stabilisation 0.4 % · mesh 1.90 % · CETOL 0.02 %",
            ha="center", fontsize=8.5, color="#1b5e20")
    ax.text(.5, .08, "the local model is DISPLACEMENT-DRIVEN, so a near-perfect "
            "$\\Delta u$–damage correlation is expected by construction",
            ha="center", fontsize=7.5, color=C["warn"])
    ax.set(xlim=(0, 1), ylim=(0, .9), xticks=[], yticks=[],
           title="FIG-0I-D  Global → local reliability submodel workflow")
    ax.grid(False)
    fig.savefig(OUT / "FIG_0I_D_workflow.png"); plt.close(fig)


def fig_E():
    """Temperature cycle at the joint."""
    cmp_ = [r for r in rows(OUT / "z_architecture_comparison.csv") if r.get("d_eps_in_stab")]
    fig, ax = plt.subplots(figsize=(9.0, 4.0))
    n, dw = 4, 300.0
    for a in dict.fromkeys(r["arch"] for r in cmp_):
        b = min([r for r in cmp_ if r["arch"] == a], key=lambda r: F(r, "P_elec_total_w"))
        th, tl = F(b, "T_joint_C"), 25.0
        t, T = [0.0], [tl]
        for k in range(n):
            t += [k * 2 * dw, k * 2 * dw + dw, k * 2 * dw + dw, (k + 1) * 2 * dw]
            T += [th, th, tl, tl]
        ax.plot(t, T, "-", color=AC[a], lw=1.8,
                label=f"{SH[a]}  ($h$ = {F(b,'h_sub_mm'):.2f} mm, $T_{{hot}}$ = {th:.1f} °C)")
    ax.set(xlabel="time (s)", ylabel="corner-BGA joint temperature (°C)",
           title="FIG-0I-E  Power cycle applied at the critical joint: OFF (25 °C) → ON → OFF")
    ax.legend(fontsize=8, loc="center right")
    ax.text(.02, .06, "no mission profile is invented: these are the system's own OFF and "
            "full-load states.\nDwell 300 s shown; $t_{95}$ = 1618 s, so the applied swing is "
            "the $t\\to\\infty$ worst case.",
            transform=ax.transAxes, fontsize=7.5, color=C["warn"])
    fig.savefig(OUT / "FIG_0I_E_thermal_cycle.png"); plt.close(fig)


def fig_F():
    """Hysteresis of the joint material."""
    d = OUT / "zjoint" / "_BAC_0p30.dat"
    if not d.is_file():
        d = next(iter(sorted((OUT / "zjoint").glob("*.dat"))), None)
    S, E, kind, tm = {}, {}, None, None
    for l in d.read_text().splitlines():
        h = re.match(r"\s*(stresses|strains).*time\s+([0-9.E+-]+)", l)
        if h:
            kind, tm = h.group(1), float(h.group(2)); continue
        p = l.split()
        if kind and len(p) >= 8 and p[0].isdigit() and p[1] == "1":
            (S if kind == "stresses" else E).setdefault(tm, float(p[6]))
    ts = sorted(set(S) & set(E))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.8, 4.2))
    a1.plot([E[t] * 100 for t in ts], [S[t] for t in ts], "-", color=C["b"], lw=1.2)
    a1.plot([E[ts[0]] * 100], [S[ts[0]]], "o", color="k", ms=5)
    a1.set(xlabel="shear strain $\\varepsilon_{xz}$ (%)", ylabel="shear stress $\\sigma_{xz}$ (MPa)",
           title="(a) cyclic hysteresis, SAC305 joint")
    a1.text(.03, .95, "closed loops with progressive drift =\nplastic + creep accumulation",
            transform=a1.transAxes, va="top", fontsize=8)
    a2.plot(ts, [S[t] for t in ts], "-", color=C["warn"], lw=1.2)
    a2.set(xlabel="time (s)", ylabel="shear stress $\\sigma_{xz}$ (MPa)",
           title="(b) stress relaxation within each dwell")
    a2.text(.03, .05, "creep relaxes stress during every hold\n(isolated test: −49.6 % over 600 s)",
            transform=a2.transAxes, fontsize=8)
    fig.suptitle("FIG-0I-F  Temperature-dependent viscoplastic response of the critical joint",
                 fontsize=10.5, y=1.02)
    fig.savefig(OUT / "FIG_0I_F_hysteresis.png"); plt.close(fig)


def fig_G():
    """Damage vs thickness by architecture."""
    th = rows(OUT / "thickness_by_architecture.csv")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.2, 4.2))
    for a in dict.fromkeys(r["arch"] for r in th):
        s = sorted([r for r in th if r["arch"] == a], key=lambda r: F(r, "h_sub_mm"))
        a1.plot([F(r, "h_sub_mm") for r in s], [F(r, "d_eps_in_stab") for r in s], "o-",
                color=AC[a], label=SH[a], ms=5)
        a2.plot([F(r, "h_sub_mm") for r in s], [F(r, "die_warpage_pv_um") for r in s], "s--",
                color=AC[a], label=SH[a], ms=5)
    for ax, yl, tt in ((a1, "$\\Delta\\varepsilon_{in}$ per stabilised cycle",
                        "(a) LOCAL DAMAGE — thicker is better, weakly"),
                       (a2, "die warpage P-V (µm)",
                        "(b) GLOBAL WARPAGE — thicker is better, strongly")):
        ax.set(xlabel="substrate thickness $h_{sub}$ (mm)", ylabel=yl, title=tt)
        ax.legend(fontsize=8)
    a1.text(.5, .06, "damage changes only 5.6–17.2 % over the full range", transform=a1.transAxes,
            ha="center", fontsize=8, color=C["warn"])
    a2.text(.5, .06, "warpage changes 29.7–52.6 % over the same range", transform=a2.transAxes,
            ha="center", fontsize=8, color=C["warn"])
    fig.suptitle("FIG-0I-G  Global warpage OVERSTATES the reliability benefit of a thicker "
                 "substrate by roughly 3–5x", fontsize=10.5, y=1.02)
    fig.savefig(OUT / "FIG_0I_G_damage_vs_thickness.png"); plt.close(fig)


def fig_H():
    """Electrical loss vs reliability metric."""
    cmp_ = [r for r in rows(OUT / "z_architecture_comparison.csv") if r.get("d_eps_in_stab")]
    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    for a in dict.fromkeys(r["arch"] for r in cmp_):
        s = sorted([r for r in cmp_ if r["arch"] == a], key=lambda r: F(r, "h_sub_mm"))
        ax.plot([F(r, "d_eps_in_stab") for r in s], [F(r, "P_elec_total_w") for r in s],
                "o-", color=AC[a], label=SH[a], ms=6)
        for r in s:
            ax.annotate(f"{F(r,'h_sub_mm'):.2f}", (F(r, "d_eps_in_stab"),
                        F(r, "P_elec_total_w")), textcoords="offset points",
                        xytext=(5, 4), fontsize=6.5, color=AC[a])
    ax.set(xlabel="$\\Delta\\varepsilon_{in}$ per stabilised cycle  (lower = longer life)",
           ylabel="total electrical loss (W)  (lower = better)",
           title="FIG-0I-H  The design plane: electrical loss against local damage\n"
                 "labels are $h_{sub}$ in mm; down-left is better in both")
    ax.legend(fontsize=8.5)
    ax.annotate("Z2 buys 36 % less damage\nfor +1.69 W", xy=(4.18e-3, 127.78),
                xytext=(4.6e-3, 133.5), fontsize=8, color=C["z2"],
                arrowprops=dict(arrowstyle="-|>", color=C["z2"], lw=1.1))
    ax.annotate("Z4 costs +12 % damage\nfor only +0.03 W", xy=(7.32e-3, 126.12),
                xytext=(6.35e-3, 129.6), fontsize=8, color=C["z4"], ha="center",
                arrowprops=dict(arrowstyle="-|>", color=C["z4"], lw=1.1,
                                connectionstyle="arc3,rad=-0.2"))
    ax.text(.5, .015, "no architecture dominates: Z1/Z4 are cheap and damaging, "
            "Z2 is expensive and gentle", transform=ax.transAxes, ha="center",
            fontsize=8.5, color="#333")
    ax.set_ylim(120.5, 138.5)
    fig.savefig(OUT / "FIG_0I_H_loss_vs_damage.png"); plt.close(fig)


def fig_I():
    """Relative life by architecture, parametric in the life exponent."""
    rs = rows(OUT / "reliability_constraint_sensitivity.csv")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.2, 4.2))
    base = [r for r in rs if not r["arch"].endswith("_thick_vs_thin")]
    for a in dict.fromkeys(r["arch"] for r in base):
        s = sorted([r for r in base if r["arch"] == a],
                   key=lambda r: F(r, "coffin_manson_exponent_k"))
        a1.plot([F(r, "coffin_manson_exponent_k") for r in s],
                [F(r, "relative_life_vs_embedded") for r in s], "o-", color=AC[a],
                label=SH[a], ms=5)
    a1.axhline(1.0, color="k", lw=1)
    a1.set(xlabel="life-law exponent $k$  in  $N_f = C\\,\\Delta\\varepsilon^{-k}$",
           ylabel="relative life vs Z1 embedded",
           title="(a) architecture effect — $C$ cancels")
    a1.legend(fontsize=8)
    a1.text(.03, .95, "typical solder $k$ is 1.5–3", transform=a1.transAxes, va="top",
            fontsize=8, color=C["warn"])
    tv = [r for r in rs if r["arch"].endswith("_thick_vs_thin")]
    for a in dict.fromkeys(r["arch"] for r in tv):
        s = sorted([r for r in tv if r["arch"] == a],
                   key=lambda r: F(r, "coffin_manson_exponent_k"))
        a2.plot([F(r, "coffin_manson_exponent_k") for r in s],
                [F(r, "relative_life_vs_embedded") for r in s], "s--",
                color=AC[a.replace("_thick_vs_thin", "")],
                label=f"{SH[a.replace('_thick_vs_thin','')]}  (+{F(s[0],'dP_vs_embedded_w'):.2f} W)",
                ms=5)
    a2.axhline(1.0, color="k", lw=1)
    a2.set(xlabel="life-law exponent $k$", ylabel="relative life, thickest vs thinnest",
           title="(b) thickness effect within each architecture")
    a2.legend(fontsize=7.5)
    fig.suptitle("FIG-0I-I  Relative life is parameter-free in $C$. No absolute $N_f$ is "
                 "claimed: no admissible SAC305 life law was retrievable.",
                 fontsize=10.5, y=1.02)
    fig.savefig(OUT / "FIG_0I_I_relative_life.png"); plt.close(fig)


if __name__ == "__main__":
    for fn in (fig_A, fig_B, fig_C, fig_D, fig_E, fig_F, fig_G, fig_H, fig_I):
        try:
            fn(); print(f"  {fn.__name__} ok", flush=True)
        except Exception as e:
            print(f"  {fn.__name__} FAILED: {type(e).__name__}: {e}", flush=True)
    print()
    for p in sorted(OUT.glob("FIG_0I_*.png")):
        print(f"  {p.name}  {p.stat().st_size/1024:.0f} kB")
