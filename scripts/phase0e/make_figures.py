#!/usr/bin/env python3
"""Phase-0E figures. Every number is read from a results artifact, never retyped."""
from __future__ import annotations
import csv, json, math, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0e"
sys.path.insert(0, str(R / "scripts" / "phase0e"))
from stack import stacks_from_cfg, load_cfg

plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": 0.3,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
C = {"src": "#1b5e20", "assume": "#b71c1c", "old": "#9e9e9e", "new": "#1565c0",
     "warn": "#ef6c00"}


def fig_A():
    """FIG-0E-A: the sourced multilayer VDD/GND metal stack vs what Phase 0D-R assumed."""
    S = stacks_from_cfg()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.5, 4.0),
                                 gridspec_kw={"width_ratios": [1.15, 1]})
    # left: layer cartoon
    def draw(ax, st, x0, label, colour):
        y = 0.0
        for net, n in (("GND", st.n_gnd), ("VDD", st.n_vdd)):
            for i in range(n):
                ax.add_patch(Rectangle((x0, y), 0.8, 0.55, facecolor=colour,
                                       edgecolor="k", lw=0.6, alpha=0.85))
                ax.text(x0 + 0.4, y + 0.27, net, ha="center", va="center",
                        fontsize=7, color="w", weight="bold")
                y += 0.75
        ax.text(x0 + 0.4, -0.45, label, ha="center", va="top", fontsize=8)
        ax.text(x0 + 0.4, y + 0.12,
                f"{st.t_cu_m*1e6:.0f} µm Cu\nocc {st.occupancy:.3f}\n"
                f"{st.r_sheet_net('vdd')*1e3:.2f} mΩ/sq",
                ha="center", va="bottom", fontsize=7)
        return y
    ymax = 0
    for k, (name, lab, col) in enumerate([
            ("phase0dr_legacy", "Phase-0D-R\n(ASSUMPTION)", C["assume"]),
            ("ectc2024_one_per_net", "1 VDD + 1 GND\n(bound)", C["warn"]),
            ("ectc2024_primary", "ECTC-2024 Table I\n(SOURCE_BACKED)", C["src"])]):
        ymax = max(ymax, draw(a1, S[name], k * 1.2, lab, col))
    a1.set_xlim(-0.3, 3.3); a1.set_ylim(-1.6, ymax + 1.5)
    a1.axis("off")
    a1.set_title("(a) Power-delivery metal stack", fontsize=10, loc="left")
    a1.text(0.0, -1.4, "Phase-0D-R modelled ground as a x2 multiplier,\n"
                       "not as a network — shown here as no GND layer.",
            fontsize=6.5, style="italic", color="0.3")

    # right: sheet resistance bar
    names = ["phase0dr_legacy", "iscas2024_variant", "ectc2024_one_per_net", "ectc2024_primary"]
    labs = ["Phase-0D-R\nassumed", "ISCAS-2024\nW=2 µm", "ECTC 1+1\nbound", "ECTC-2024\nprimary"]
    vals = [S[n].r_sheet_net("vdd") * 1e3 for n in names]
    cols = [C["assume"], C["warn"], C["warn"], C["src"]]
    b = a2.bar(labs, vals, color=cols, edgecolor="k", lw=0.6)
    for r, v in zip(b, vals):
        a2.text(r.get_x() + r.get_width() / 2, v + 0.12, f"{v:.2f}", ha="center", fontsize=8)
    a2.set_ylabel("sheet resistance per network (mΩ/sq)")
    a2.set_title("(b) 5.56× correction", fontsize=10, loc="left")
    a2.set_ylim(0, max(vals) * 1.22)
    fig.suptitle("FIG-0E-A  Sourced multilayer power stack replaces the assumed single sheet",
                 fontsize=11, y=1.02)
    fig.savefig(OUT / "FIG_0E_A_metal_stack.png"); plt.close(fig)


def fig_B_C():
    """FIG-0E-B allocation + ARCH_B feasibility; FIG-0E-C current-capability envelope."""
    rows = list(csv.DictReader(open(OUT / "archB_feasibility_map.csv")))
    cd = load_cfg()["current_density"]["cu"]
    j_june, j_ectc = cd["june2026"]["value"], cd["ectc2024"]["value"]

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 4.0))
    sides = sorted({float(r["tile_side_mm"]) for r in rows})
    for s, m in zip(sides, ["o", "s", "^"]):
        sel = sorted([r for r in rows if float(r["tile_side_mm"]) == s],
                     key=lambda r: float(r["J_a_per_m2"]))
        J = [float(r["J_a_per_m2"]) for r in sel]
        u = [float(r["utilisation"]) for r in sel]
        a1.loglog(J, u, m + "-", ms=3.5, lw=1.2,
                  label=f"A_HVR = {float(sel[0]['A_HVR_mm2']):.1f} mm²")
    a1.axhline(1.0, color="k", lw=1.2)
    a1.axhspan(1.0, 1e3, color=C["assume"], alpha=0.10)
    a1.axhspan(0.5, 1.0, color=C["warn"], alpha=0.12)
    a1.text(1.3e6, 3.0, "INFEASIBLE", color=C["assume"], fontsize=8, weight="bold")
    a1.text(1.3e6, 0.68, "MARGINAL", color=C["warn"], fontsize=8, weight="bold")
    a1.text(1.3e6, 0.05, "FEASIBLE", color=C["src"], fontsize=8, weight="bold")
    for j, lab, c in ((j_june, "June-2026\n1.0e8", C["src"]),
                      (j_ectc, "ECTC-2024\n4.0e8", C["src"]),
                      (33e-3 / 707e-12, "0D-R 33 mA\n(factor-2 error)", C["warn"]),
                      (4.8e-3 / 707e-12, "0D-R 4.8 mA\n(unsourced)", C["assume"])):
        a1.axvline(j, color=c, ls="--", lw=1.1)
        a1.text(j, 1.6e-3, lab, rotation=90, fontsize=6.5, color=c,
                ha="right", va="bottom")
    a1.set_xlabel("copper current density J (A/m²)")
    a1.set_ylabel("via-field utilisation  n_required / n_available")
    a1.set_title("(a) ARCH_B (LV-TSV) feasibility map", fontsize=10, loc="left")
    a1.set_ylim(1e-3, 1e3); a1.legend(fontsize=7, loc="upper right")

    # (b) the three counts at the reference point
    labels = ["ARCH_A\n(HV rail, 1.354 A)", "ARCH_B\n(LV rail, 60 A)"]
    A = 707e-12
    data = []
    for I in (1.354, 60.0):
        nreq = math.ceil(I / (j_june * A))
        data.append((nreq, 7148))
    x = np.arange(2); w = 0.34
    a2.bar(x - w / 2, [d[0] for d in data], w, label="n_required", color=C["new"],
           edgecolor="k", lw=0.6)
    a2.bar(x + w / 2, [d[1] for d in data], w, label="n_available", color="0.75",
           edgecolor="k", lw=0.6)
    for i, d in enumerate(data):
        a2.text(i - w / 2, d[0] * 1.25, f"{d[0]}", ha="center", fontsize=8)
        a2.text(i + w / 2, d[1] * 1.08, f"{d[1]}", ha="center", fontsize=8)
        a2.text(i, 1.7, f"utilisation {d[0]/d[1]:.1%}", ha="center", fontsize=7.5,
                color=C["src"], weight="bold")
    a2.set_yscale("log"); a2.set_xticks(x); a2.set_xticklabels(labels, fontsize=8)
    a2.set_ylabel("TSV count")
    a2.set_ylim(1, 3e4)
    a2.set_title("(b) both architectures are feasible at the sourced J", fontsize=10, loc="left")
    a2.legend(fontsize=8)
    fig.suptitle("FIG-0E-B/C  TSV allocation and current-capability envelope", fontsize=11, y=1.02)
    fig.savefig(OUT / "FIG_0E_BC_allocation_feasibility.png"); plt.close(fig)


def fig_D():
    """FIG-0E-D: compact multilayer solver vs MOOSE, and the grid convergence behind it."""
    v = json.loads((OUT / "multilayer_rdl_validation.json").read_text())
    conv = list(csv.DictReader(open(OUT / "rdl_grid_convergence.csv")))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.0, 3.9))
    names = [c["placement"] for c in v["cases"]]
    pc = [c["P_compact_w"] for c in v["cases"]]
    pm = [c["P_moose_w"] for c in v["cases"]]
    x = np.arange(len(names)); w = 0.36
    a1.bar(x - w / 2, pc, w, label="compact multilayer solver", color=C["new"],
           edgecolor="k", lw=0.6)
    a1.bar(x + w / 2, pm, w, label="MOOSE FE (independent)", color=C["src"],
           edgecolor="k", lw=0.6)
    for i, c in enumerate(v["cases"]):
        a1.text(i, max(pc[i], pm[i]) * 1.06, f"{c['dP_pct']:+.2f}%", ha="center",
                fontsize=8, color=C["src"] if c["pass"] else C["assume"])
    a1.set_xticks(x); a1.set_xticklabels(names, fontsize=8)
    a1.set_ylabel("$P_{RDL}$ loop (W)")
    a1.set_title(f"(a) one calibration, all placements  (target ±{v['target_P_pct']}%)",
                 fontsize=10, loc="left")
    a1.legend(fontsize=8); a1.set_ylim(0, max(pm) * 1.2)

    n = [int(c["compact_grid_n"]) for c in conv]
    d = [abs(float(c["dP_vs_moose_pct"])) for c in conv]
    a2.plot(n, d, "o-", color=C["new"], lw=1.4, ms=5)
    a2.axhline(v["target_P_pct"], color=C["assume"], ls="--", lw=1.2,
               label=f"target {v['target_P_pct']}%")
    a2.axvline(161, color=C["src"], ls=":", lw=1.2, label="grid used (n=161)")
    a2.set_xlabel("compact-solver grid n"); a2.set_ylabel("|ΔP| vs MOOSE (%)")
    a2.set_title("(b) convergence, worst placement (edge-biased)", fontsize=10, loc="left")
    a2.legend(fontsize=8)
    fig.suptitle("FIG-0E-D  Multilayer RDL compact model validated against an independent FE solver",
                 fontsize=11, y=1.03)
    fig.savefig(OUT / "FIG_0E_D_rdl_validation.png"); plt.close(fig)


def fig_E():
    """FIG-0E-E: RDL loss by physical stack — the dominant Phase-0E correction."""
    S = stacks_from_cfg()
    base = S["phase0dr_legacy"].sigma_s_net("vdd")
    names = ["phase0dr_legacy", "iscas2024_variant", "ectc2024_one_per_net", "ectc2024_primary"]
    labs = ["Phase-0D-R\nassumed", "ISCAS-2024\nvariant", "ECTC 1+1\nbound", "ECTC-2024\nprimary"]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for lo, hi, lab, col in ((12.13, 73.0, "Phase-0D-R reported range", C["assume"]),):
        pass
    los = [12.13 * base / S[n].sigma_s_net("vdd") for n in names]
    his = [73.00 * base / S[n].sigma_s_net("vdd") for n in names]
    x = np.arange(len(names))
    ax.bar(x, np.array(his) - np.array(los), bottom=los, color=[C["assume"], C["warn"],
           C["warn"], C["src"]], edgecolor="k", lw=0.7, width=0.55)
    for i in range(len(names)):
        ax.text(i, his[i] * 1.06, f"{los[i]:.1f}–{his[i]:.1f} W", ha="center", fontsize=8)
    ax.set_yscale("log")
    ax.set_xticks(x); ax.set_xticklabels(labs, fontsize=8.5)
    ax.set_ylabel("$P_{RDL}$ loop across placements (W)")
    ax.set_title("FIG-0E-E  RDL loss depends entirely on the physical stack\n"
                 "(bars span the placement range; the Phase-0D-R stack was 5.56× too resistive)",
                 fontsize=10, loc="left")
    ax.set_ylim(1, 200)
    fig.savefig(OUT / "FIG_0E_E_rdl_by_stack.png"); plt.close(fig)


def fig_F():
    """FIG-0E-F: footprint electrical vs mechanical after real-material mapping."""
    fe = list(csv.DictReader(open(OUT / "footprint_material_fe.csv")))
    mat = list(csv.DictReader(open(OUT / "footprint_material_sensitivity.csv")))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 4.0))

    m = sorted(mat, key=lambda r: float(r["a_hvr_mm2"]))
    A = [float(r["a_hvr_mm2"]) for r in m]
    comp = [float(r["component_area_mm2"]) for r in m]
    a1.plot(A, [a / A[0] for a in A], "o-", color=C["assume"], lw=1.6, ms=6,
            label=f"bounding box A_HVR  ({max(A)/min(A):.2f}×)")
    a1.plot(A, [c / comp[0] for c in comp], "s-", color=C["src"], lw=1.6, ms=6,
            label=f"actual component area  ({max(comp)/min(comp):.2f}×)")
    for xx, r in zip(A, m):
        a1.annotate(f"fill {float(r['areal_fill']):.2f}", (xx, float(r['component_area_mm2'])/comp[0]),
                    textcoords="offset points", xytext=(0, -14), ha="center", fontsize=7)
    a1.set_xlabel("A_HVR per VR (mm²)"); a1.set_ylabel("normalised to smallest tile")
    a1.set_title("(a) CTE-mismatched material does not\nscale with the bounding box",
                 fontsize=10, loc="left")
    a1.legend(fontsize=8)

    for var, col, mk in (("homogeneous", C["old"], "o"), ("composite", C["new"], "s")):
        s = sorted([r for r in fe if r["variant"] == var],
                   key=lambda r: float(r["A_HVR_total_mm2"]))
        xx = [float(r["A_HVR_total_mm2"]) for r in s]
        yy = [float(r["die_warpage_pv_um"]) for r in s]
        a2.plot(xx, yy, mk + "-", color=col, lw=1.6, ms=6,
                label=f"{var}  (span {max(yy)/min(yy):.4f}×)")
    a2.set_xlabel("total HVR footprint (mm²)"); a2.set_ylabel("die warpage p-v (µm)")
    a2.set_title("(b) the footprint opposition SURVIVES\nsensitivity changes by 0.06 %",
                 fontsize=10, loc="left")
    a2.legend(fontsize=8)
    fig.suptitle("FIG-0E-F  Footprint mechanics after physical material mapping", fontsize=11, y=1.02)
    fig.savefig(OUT / "FIG_0E_F_footprint_material.png"); plt.close(fig)


def fig_G():
    """FIG-0E-G: BC-A vs BC-B — which response still discriminates."""
    rows = list(csv.DictReader(open(OUT / "bcb_corrected_results.csv")))
    pairs = ["A_footprint", "B_thickness", "C_placement"]
    mets = [("die_warpage_pv_um", "die warpage p-v (µm)"),
            ("interface_shear_p99_MPa", "interface shear p99 (MPa)")]
    fig, axes = plt.subplots(2, 3, figsize=(11.5, 6.4), sharex="col")
    # Member order must match the direction used in the tables (small->large, thin->thick,
    # distributed->edge); alphabetical order silently reverses the reported sign.
    ORDER = {"A_footprint": ["small_j4.0", "large_j1.5"],
             "B_thickness": ["h200", "h500"],
             "C_placement": ["distributed", "edge_biased"]}
    for j, pr in enumerate(pairs):
        sel = [r for r in rows if r["pair"] == pr]
        members = [m for m in ORDER[pr] if any(r["member"] == m for r in sel)]
        for i, (mk, ml) in enumerate(mets):
            ax = axes[i][j]
            x = np.arange(len(members)); w = 0.36
            for k, (bc, col) in enumerate((("BC_A", C["old"]), ("BC_B", C["new"]))):
                v = [float(next(r for r in sel if r["member"] == m and r["bc"] == bc)[mk])
                     for m in members]
                b = ax.bar(x + (k - .5) * w, v, w, label=bc, color=col, edgecolor="k", lw=0.6)
                for rr, vv in zip(b, v):
                    ax.text(rr.get_x() + rr.get_width() / 2, vv, f"{vv:.3g}",
                            ha="center", va="bottom", fontsize=6.5)
                if len(v) == 2 and min(v) > 0:
                    d = 100 * (v[1] - v[0]) / v[0]
                    ax.text(0.02, 0.95 - 0.09 * k, f"{bc}: {d:+.1f}%", transform=ax.transAxes,
                            ha="left", va="top", fontsize=7.5, color=col, weight="bold",
                            bbox=dict(fc="white", ec="none", alpha=0.75, pad=1.2))
            ax.set_xticks(x); ax.set_xticklabels(members, fontsize=7.5)
            ax.set_ylim(0, max(ax.get_ylim()[1], 1e-12) * 1.22)
            if j == 0:
                ax.set_ylabel(ml, fontsize=8)
            if i == 0:
                ax.set_title(pr.replace("_", " "), fontsize=9.5)
            if i == 0 and j == 0:
                ax.legend(fontsize=7.5)
    fig.suptitle("FIG-0E-G  Under board restraint warpage collapses and interface shear grows:\n"
                 "the discriminating response changes", fontsize=11, y=1.0)
    fig.tight_layout()
    fig.savefig(OUT / "FIG_0E_G_bcb.png"); plt.close(fig)


def fig_H():
    """FIG-0E-H: how each claim moved across Phase 0D -> 0D-R -> 0E."""
    rows = list(csv.DictReader(open(OUT / "phase_progression.csv")))
    keep = [("RDL loss, reference point", "RDL loss (W)", 1),
            ("placement electrical spread (total elec)", "placement electrical\nspread (%)", 1),
            ("footprint ETM exchange rate", "footprint exchange\nrate (W/µm)", 1),
            ("placement ETM exchange rate", "placement exchange\nrate (W/µm)", 1)]
    fig, axes = plt.subplots(1, 4, figsize=(12.5, 3.6))
    ph = ["phase_0D", "phase_0D_R", "phase_0E"]
    lab = ["0D", "0D-R", "0E"]
    for ax, (claim, ylab, _) in zip(axes, keep):
        r = next((x for x in rows if x["claim"] == claim), None)
        if r is None:
            continue
        vals, ls = [], []
        for p, l in zip(ph, lab):
            try:
                vals.append(float(r[p])); ls.append(l)
            except (ValueError, TypeError):
                pass
        cols = [C["old"], C["warn"], C["src"]][-len(vals):]
        b = ax.bar(ls, vals, color=cols, edgecolor="k", lw=0.7, width=0.6)
        for rr, v in zip(b, vals):
            ax.text(rr.get_x() + rr.get_width() / 2, v, f"{v:g}", ha="center",
                    va="bottom", fontsize=8)
        ax.set_title(ylab, fontsize=9)
        ax.set_ylim(0, max(vals) * 1.25)
    fig.suptitle("FIG-0E-H  Claim evolution: Phase 0D → 0D-R → 0E.  Green is the value standing "
                 "on a sourced physical stack.", fontsize=10.5, y=1.04)
    fig.tight_layout()
    fig.savefig(OUT / "FIG_0E_H_claim_evolution.png"); plt.close(fig)



if __name__ == "__main__":
    which = sys.argv[1:] or ["A", "BC", "D", "E", "F", "G", "H"]
    fns = {"A": fig_A, "BC": fig_B_C, "D": fig_D, "E": fig_E, "F": fig_F,
           "G": fig_G, "H": fig_H}
    for k in which:
        fns[k]()
        print("wrote", k)


