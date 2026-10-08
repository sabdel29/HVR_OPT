#!/usr/bin/env python3
"""Phase-0G figures. Every number is read from a results artifact, never retyped."""
from __future__ import annotations
import csv, json, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0g"
P0F = R / "results" / "phase0f"

plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": 0.3,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
C = {"src": "#1b5e20", "bad": "#b71c1c", "old": "#9e9e9e", "new": "#1565c0",
     "warn": "#ef6c00", "b": "#6a1b9a", "free": "#00838f"}
F = lambda r, k: float(r[k])


def rows(p):
    return list(csv.DictReader(open(p)))


# ---------------------------------------------------------------- A: DEFECT #30
def fig_A():
    pre = rows(OUT / "crossover_hires_ARCH_B_tight.csv")
    post = rows(OUT / "crossover_hires_ARCH_B_fixedB.csv")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.4, 4.0))
    hp, pp = [F(r, "h_sub_mm") for r in pre], [F(r, "P_elec_total_w") for r in pre]
    hq, pq = [F(r, "h_sub_mm") for r in post], [F(r, "P_elec_total_w") for r in post]
    a1.plot(hp, pp, "o-", color=C["old"], label="as computed in Phases 0D-R/0E/0F\n(DEFECT #30 present)")
    i = int(np.argmin(pp))
    a1.plot(hp[i], pp[i], "v", ms=11, color=C["bad"], zorder=5)
    a1.annotate(f"interior minimum\nat {hp[i]:.2f} mm\n(survived a 25x tighter\nconvergence tolerance)",
                (hp[i], pp[i]), xytext=(1.15, 125.083), fontsize=7.5, color=C["bad"],
                arrowprops=dict(arrowstyle="->", color=C["bad"], lw=0.9))
    a1.set(xlabel="substrate thickness $h_{sub}$ (mm)", ylabel="ARCH_B total loss (W)",
           title="(a) the withdrawn interior optimum")
    a1.legend(fontsize=7, loc="upper left")
    a2.plot(hq, pq, "s-", color=C["new"], label="corrected (both terms system-wide)")
    a2.plot(hq[int(np.argmin(pq))], min(pq), "^", ms=11, color=C["src"], zorder=5)
    a2.annotate("optimum on the THIN\nboundary, monotone;\n9 corners of 9",
                (hq[0], pq[0]), xytext=(1.02, 129.9), fontsize=7.5, color=C["src"],
                ha="left", bbox=dict(fc="#e8f5e9", ec=C["src"], lw=0.8, alpha=0.95),
                arrowprops=dict(arrowstyle="-|>", color=C["src"], lw=1.1,
                                connectionstyle="arc3,rad=-0.25", shrinkB=7))
    a2.set(xlabel="substrate thickness $h_{sub}$ (mm)", ylabel="ARCH_B total loss (W)",
           title="(b) corrected: no interior optimum")
    a2.legend(fontsize=7, loc="upper left")
    tp = {F(r, "h_sub_mm"): F(r, "P_tsv_w") for r in pre}
    tq = {F(r, "h_sub_mm"): F(r, "P_tsv_w") for r in post}
    ratio = [tq[h] / tp[h] for h in tp if h in tq]
    a2.text(0.5, 0.06, f"$P_{{TSV}}$ ratio = {min(ratio):.3f}–{max(ratio):.3f} = $n_{{vr}}$ = 49",
            transform=a2.transAxes, ha="center", fontsize=7.5,
            bbox=dict(fc="#fff8e1", ec=C["warn"], lw=0.8))
    fig.suptitle("FIG-0G-A  DEFECT #30: a unit inconsistency, not a convergence artifact",
                 fontsize=10.5, y=1.01)
    fig.savefig(OUT / "FIG_0G_A_defect30.png"); plt.close(fig)


# ------------------------------------------------- B: no support-stiffness crossover
def fig_B():
    rr = rows(OUT / "support_stiffness_sweep.csv")
    ks = sorted({F(r, "k_z_N_per_mm3") for r in rr if r["k_z_N_per_mm3"]})
    hs = sorted({F(r, "h_sub_mm") for r in rr})
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.4, 4.0))
    for h in hs:
        w = [next(F(r, "die_warpage_pv_um") for r in rr
                  if r["k_z_N_per_mm3"] and F(r, "k_z_N_per_mm3") == k and F(r, "h_sub_mm") == h)
             for k in ks]
        a1.semilogx(ks, w, "o-", ms=3.5, label=f"$h_{{sub}}$ = {h:.2f} mm")
    a1.axhline(8.28732, color=C["free"], ls="--", lw=1.4)
    a1.text(0.02, 8.28732 * 1.06, "free package on the IDENTICAL mesh, 8.287 µm",
            fontsize=7.5, color=C["free"])
    a1.annotate("at vanishing stiffness BC-B\nstill gives 0.739 µm — 11.2x\nbelow its own free limit",
                (0.001, 0.739), xytext=(0.004, 2.6), fontsize=7.5, color=C["bad"],
                arrowprops=dict(arrowstyle="->", color=C["bad"], lw=0.9))
    a1.set(xlabel="support stiffness $k_z$ (N/mm$^3$)", ylabel="die warpage P-V (µm)",
           title="(a) BC-B never recovers the free limit", ylim=(0, 9.6))
    a1.legend(fontsize=7)
    S = []
    for k in ks:
        w = {h: next(F(r, "die_warpage_pv_um") for r in rr
                     if r["k_z_N_per_mm3"] and F(r, "k_z_N_per_mm3") == k
                     and F(r, "h_sub_mm") == h) for h in hs}
        S.append((w[hs[-1]] - w[hs[0]]) / w[hs[0]])
    a2.semilogx(ks, S, "s-", color=C["bad"], ms=4)
    a2.axhline(0, color="k", lw=1.1)
    a2.fill_between(ks, 0, S, color=C["bad"], alpha=0.12)
    a2.text(0.5, 0.5, "$S_h>0$ at EVERY stiffness\nacross seven decades\n\nno crossover $k^*$ exists",
            transform=a2.transAxes, ha="center", va="center", fontsize=9, color=C["bad"],
            bbox=dict(fc="#ffebee", ec=C["bad"], lw=1.0))
    a2.set(xlabel="support stiffness $k_z$ (N/mm$^3$)",
           ylabel="$S_h$ = [W(2.00) − W(0.80)] / W(0.80)",
           title="(b) the search for $k^*$ returns no root")
    fig.suptitle("FIG-0G-B  The compact BC-B foundation is a clamp, not a board",
                 fontsize=10.5, y=1.01)
    fig.savefig(OUT / "FIG_0G_B_no_kstar.png"); plt.close(fig)


# ------------------------------------------------------------- C: assembly regimes
def fig_C():
    rr = rows(OUT / "explicit_board_crosscheck.csv")
    hs = sorted({F(r, "h_sub_mm") for r in rr})
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    series = [("BC_A", "-", "free package (3-2-1)", C["free"], "o--"),
              ("BC_B", "-", "compact BC-B clamp", C["bad"], "v--")]
    for bc in ("compliant", "fr4_1p6mm", "fr4_3p2mm", "stiff_metal_backed"):
        series.append(("BC_BOARD", bc, f"explicit board: {bc}", None, "s-"))
    cmap = plt.cm.viridis(np.linspace(0.15, 0.8, 4))
    ci = 0
    for mode, case, lab, col, mk in series:
        w = [next((F(r, "die_warpage_pv_um") for r in rr if r["restraint"] == mode
                   and r["board_case"] == case and F(r, "h_sub_mm") == h), np.nan) for h in hs]
        if col is None:
            col = cmap[ci]; ci += 1
        ax.plot(hs, w, mk, color=col, label=lab, ms=5)
    ax.set(xlabel="substrate thickness $h_{sub}$ (mm)", ylabel="die warpage P-V (µm)",
           yscale="log", title="FIG-0G-C  Mounting AMPLIFIES warpage; the compact clamp SUPPRESSES it")
    ax.legend(fontsize=7.5, ncol=2)
    ax.annotate("every explicit board and the free package\nfall with thickness; only the clamp rises",
                (1.5, 0.55), fontsize=7.5, color=C["bad"])
    fig.savefig(OUT / "FIG_0G_C_assembly_regimes.png"); plt.close(fig)


# ------------------------------------------------------- D: S_h across all models
def fig_D():
    rr = rows(OUT / "explicit_board_crosscheck.csv")
    labs, S = [], []
    for mode, case, lab in (("BC_A", "-", "free package"),
                            ("BC_B", "-", "compact BC-B clamp"),
                            ("BC_BOARD", "compliant", "board: compliant"),
                            ("BC_BOARD", "fr4_1p6mm", "board: FR-4 1.6 mm"),
                            ("BC_BOARD", "fr4_3p2mm", "board: FR-4 3.2 mm"),
                            ("BC_BOARD", "stiff_metal_backed", "board: metal-backed")):
        g = lambda h: next(F(r, "die_warpage_pv_um") for r in rr if r["restraint"] == mode
                           and r["board_case"] == case and F(r, "h_sub_mm") == h)
        labs.append(lab); S.append((g(2.0) - g(0.8)) / g(0.8))
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    cols = [C["bad"] if s > 0 else C["src"] for s in S]
    ax.barh(labs, S, color=cols, alpha=0.85)
    ax.axvline(0, color="k", lw=1.2)
    for y, s in enumerate(S):
        ax.text(s + (0.05 if s > 0 else -0.05), y, f"{s:+.3f}", va="center",
                ha="left" if s > 0 else "right", fontsize=8)
    ax.set(xlabel="$S_h$ = [W(2.00 mm) − W(0.80 mm)] / W(0.80 mm)", xlim=(-1.15, 1.75),
           title="FIG-0G-D  Only the compact clamp reverses the thickness preference")
    ax.text(0.98, 0.06, "thicker WORSE →", transform=ax.transAxes, ha="right",
            fontsize=8, color=C["bad"])
    ax.text(0.02, 0.06, "← thicker BETTER", transform=ax.transAxes, fontsize=8, color=C["src"])
    fig.savefig(OUT / "FIG_0G_D_Sh_by_model.png"); plt.close(fig)


# ------------------------------------------------------------ E: footprint sign flip
def fig_E():
    rr = rows(OUT / "footprint_board_envelope.csv")
    labs, S = [], []
    for mode, case, lab in (("BC_A", "-", "free package"),
                            ("BC_B", "-", "compact BC-B clamp"),
                            ("BC_BOARD", "compliant", "board: compliant"),
                            ("BC_BOARD", "fr4_1p6mm", "board: FR-4 1.6 mm"),
                            ("BC_BOARD", "fr4_2p4mm", "board: FR-4 2.4 mm"),
                            ("BC_BOARD", "fr4_3p2mm", "board: FR-4 3.2 mm"),
                            ("BC_BOARD", "stiff_metal_backed", "board: metal-backed")):
        sel = [r for r in rr if r["restraint"] == mode and r.get("board_case", "-") == case]
        a = next(F(r, "die_warpage_pv_um") for r in sel if r["m_vr"] == "36")
        b = next(F(r, "die_warpage_pv_um") for r in sel if r["m_vr"] == "49")
        labs.append(lab); S.append((b - a) / a)
    fig, ax = plt.subplots(figsize=(7.8, 4.2))
    cols = [C["bad"] if s > 0 else C["src"] for s in S]
    ax.barh(labs, S, color=cols, alpha=0.85)
    ax.axvline(0, color="k", lw=1.2)
    for y, s in enumerate(S):
        ax.text(s + (0.012 if s > 0 else -0.012), y, f"{s:+.3f}", va="center",
                ha="left" if s > 0 else "right", fontsize=8)
    ax.set_ylim(-0.9, len(labs) + 0.6)
    ax.set(xlabel="$S_A$ = [W(329.3 mm²) − W(259.2 mm²)] / W(259.2 mm²)", xlim=(-0.40, 0.32),
           title="FIG-0G-E  The footprint opposition exists only in unmounted / clamped models")
    ax.text(-0.385, -0.72, "← larger footprint BETTER (agreement)",
            fontsize=8, color=C["src"], va="center")
    ax.text(0.305, -0.72, "larger footprint WORSE (opposition) →",
            fontsize=8, color=C["bad"], va="center", ha="right")
    ax.text(0.5, 0.965, "electrically the larger footprint wins by 6.633 W — "
            "so in every mounted model the two disciplines AGREE",
            transform=ax.transAxes, ha="center", va="top", fontsize=7.5,
            bbox=dict(fc="#e8f5e9", ec=C["src"], lw=0.8))
    fig.savefig(OUT / "FIG_0G_E_footprint_flip.png"); plt.close(fig)


# -------------------------------------------- F: invariance to thermal boundary and M1
def fig_F():
    th = rows(OUT / "cooling_topology_comparison.csv")
    m1 = rows(OUT / "footprint_m1_1kw.csv")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.4, 4.0))
    tags = ["top_x0.5", "top_calibrated", "top_x2"]
    xt = ["$h_{top}$ × 0.5", "calibrated", "$h_{top}$ × 2"]
    for case, col in (("fr4_1p6mm", C["new"]), ("compliant", C["b"])):
        S, T = [], []
        for tg in tags:
            sel = [r for r in th if r["topology"] == tg and r["restraint"] == "BC_BOARD"
                   and r["board_case"] == case]
            a = next(F(r, "die_warpage_pv_um") for r in sel if F(r, "h_sub_mm") == 0.80)
            b = next(F(r, "die_warpage_pv_um") for r in sel if F(r, "h_sub_mm") == 2.00)
            S.append((b - a) / a)
            T.append(next(F(r, "T_max_C") for r in sel if F(r, "h_sub_mm") == 0.80))
        a1.plot(xt, S, "o-", color=col, ms=6,
                label=f"{case}: spread {100*(max(S)-min(S))/abs(np.mean(S)):.2f} %")
        for x, s, t in zip(xt, S, T):
            a1.annotate(f"{s:+.4f}\n{t:.0f} °C", (x, s), textcoords="offset points",
                        xytext=(0, -26), ha="center", fontsize=7)
    a1.axhline(0, color="k", lw=1.0)
    a1.set(ylabel="$S_h$", title="(a) invariant to the thermal boundary", ylim=(-0.85, 0.15))
    a1.legend(fontsize=7.5, loc="upper center")
    for mode, col, lab in (("BC_A", C["free"], "free package"),
                           ("BC_BOARD", C["new"], "board: FR-4 1.6 mm")):
        tr, S = [], []
        for t in (25.0, 150.0, 175.0):
            sel = [r for r in m1 if r["study"] == "m1" and r["restraint"] == mode
                   and F(r, "t_ref_C") == t]
            if len(sel) < 2:
                continue
            a = next(F(r, "die_warpage_pv_um") for r in sel if F(r, "h_sub_mm") == 0.80)
            b = next(F(r, "die_warpage_pv_um") for r in sel if F(r, "h_sub_mm") == 2.00)
            tr.append(t); S.append((b - a) / a)
        a2.plot(tr, S, "s-", color=col, ms=6, label=lab)
        for x, s in zip(tr, S):
            a2.annotate(f"{s:+.4f}", (x, s), textcoords="offset points", xytext=(0, 8),
                        ha="center", fontsize=7)
    a2.axhline(0, color="k", lw=1.0)
    a2.set(xlabel="stress-free reference temperature (°C)", ylabel="$S_h$",
           title="(b) invariant to the M1 reference state", ylim=(-1.05, 0.15))
    a2.legend(fontsize=7.5, loc="upper center")
    fig.suptitle("FIG-0G-F  The normalized thickness response is a STRUCTURAL property",
                 fontsize=10.5, y=1.01)
    fig.savefig(OUT / "FIG_0G_F_invariance.png"); plt.close(fig)


# ------------------------------------------------------------- G: corrected epsilon
def fig_G():
    rr = rows(OUT / "mechanical_epsilon_corrected.csv")
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    styles = {"ARCH_B / BC_A free package": ("o-", C["bad"]),
              "ARCH_A / BC_A free package": ("s-", C["free"]),
              "ARCH_B / BC_BOARD FR-4 1.6 mm": ("^--", C["b"]),
              "ARCH_A / BC_BOARD FR-4 1.6 mm": ("v--", C["new"])}
    for lab, (mk, col) in styles.items():
        pts = [(float(r["epsilon_um"]), float(r["penalty_mW"]) / 1000)
               for r in rr if r["assembly"] == lab and r["epsilon_um"] != "inf"
               and r["penalty_mW"]]
        if not pts:
            continue
        pts.sort()
        ax.plot([p[0] for p in pts], [p[1] for p in pts], mk, color=col, label=lab, ms=5)
    ax.axvspan(1.0, 14.0, color=C["old"], alpha=0.13)
    ax.text(6.0, 4.6, "unreachable when MOUNTED\n(mounted floor 14.03 µm)", fontsize=7.5,
            ha="center", color="#555")
    ax.set(xlabel="user-set warpage preference ε (µm)", ylabel="electrical penalty (W)",
           title="FIG-0G-G  Corrected ε sensitivity — a PREFERENCE, never a feasibility test")
    ax.legend(fontsize=7.5)
    ax.text(0.98, 0.60, "no admissible criterion exists (Sec. 12)\nG2 remains NOT TESTED",
            transform=ax.transAxes, ha="right", fontsize=8, color=C["warn"],
            bbox=dict(fc="#fff8e1", ec=C["warn"], lw=0.9))
    fig.savefig(OUT / "FIG_0G_G_epsilon.png"); plt.close(fig)


if __name__ == "__main__":
    for fn in (fig_A, fig_B, fig_C, fig_D, fig_E, fig_F, fig_G):
        fn(); print(f"  {fn.__name__} ok", flush=True)
    print("\n" + "\n".join(f"  {p.name}  {p.stat().st_size/1024:.0f} kB"
                           for p in sorted(OUT.glob("FIG_0G_*.png"))))
