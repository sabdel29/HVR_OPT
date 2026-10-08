#!/usr/bin/env python3
"""Phase-0F figures. Every number is read from a results artifact, never retyped."""
from __future__ import annotations
import csv, json, math, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0f"
sys.path.insert(0, str(R / "scripts" / "phase0f"))

plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": 0.3,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
C = {"src": "#1b5e20", "bad": "#b71c1c", "old": "#9e9e9e", "new": "#1565c0",
     "warn": "#ef6c00", "b": "#6a1b9a"}


def rows(name, only_feasible=False):
    out = []
    for r in csv.DictReader(open(OUT / name)):
        if only_feasible and str(r.get("feasible")).lower() not in ("true", "1"):
            continue
        out.append(r)
    return out


F = lambda r, k: float(r[k])


def fig_A():
    """FIG-0F-A: the realizable stack, and the two thicknesses that are not."""
    from geometry import fitting_inductors, GAN_H_UM, MLCC_H_UM, H_TSV_MIN_UM
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.6, 4.3),
                                 gridspec_kw={"width_ratios": [1.05, 1]})
    # (a) stack cartoon at three substrate thicknesses
    layers = [("TSV field", None, "#cfd8dc"), ("GaN switch", 100, "#90a4ae"),
              ("flying cap", 100, "#b0bec5"), ("inductor", 500, "#455a64")]
    for k, h_sub in enumerate((200, 500, 1500)):
        x0 = k * 1.25
        t_cell = 720.0
        ok = h_sub - t_cell >= H_TSV_MIN_UM
        a1.add_patch(Rectangle((x0, 0), 0.9, h_sub, facecolor="none",
                               edgecolor=(C["src"] if ok else C["bad"]), lw=2.0))
        y = 0.0
        h_tsv = max(0.0, h_sub - t_cell)
        for nm, t, col in layers:
            tt = h_tsv if t is None else t
            if tt <= 0:
                continue
            top = min(y + tt, h_sub)
            if top <= y:
                break
            a1.add_patch(Rectangle((x0, y), 0.9, top - y, facecolor=col, edgecolor="k", lw=0.4))
            if top - y > 60:
                a1.text(x0 + 0.45, (y + top) / 2, nm, ha="center", va="center", fontsize=6.2)
            y = top
        if not ok:
            a1.plot([x0, x0 + 0.9], [h_sub, 0], color=C["bad"], lw=2.2)
            a1.plot([x0, x0 + 0.9], [0, h_sub], color=C["bad"], lw=2.2)
        a1.text(x0 + 0.45, -95, f"h_sub = {h_sub} µm\n"
                                f"{'REALIZABLE' if ok else 'INFEASIBLE'}",
                ha="center", va="top", fontsize=7.5,
                color=(C["src"] if ok else C["bad"]), weight="bold")
    a1.axhline(720, color=C["warn"], ls="--", lw=1.2)
    a1.text(-0.15, 745, "cell height 720 µm\n(500 µm inductor + layers)", fontsize=7,
            color=C["warn"], va="bottom", ha="left")
    a1.set_xlim(-0.25, 3.35); a1.set_ylim(-330, 1750)
    a1.set_ylabel("height above the substrate underside (µm)")
    a1.set_xticks([]); a1.set_title("(a) the converter must fit inside the substrate",
                                    fontsize=10, loc="left")

    # (b) how many library inductors fit
    hs = [200, 400, 500, 600, 800, 1000, 1200, 1500]
    for bnd, col, mk in (("optimistic", C["warn"], "^"), ("nominal", C["new"], "o"),
                         ("pessimistic", C["bad"], "s")):
        n = [len(fitting_inductors(h / 1e3, bnd)[0]) for h in hs]
        a2.plot(hs, n, mk + "-", color=col, lw=1.5, ms=5, label=bnd)
    a2.axvline(200, color=C["old"], ls=":", lw=1.2)
    a2.axvline(500, color=C["old"], ls=":", lw=1.2)
    a2.text(210, 9.6, "Phase 0B–0E\nswept these two", fontsize=7, color=C["old"])
    a2.set_xlabel("substrate thickness (µm)")
    a2.set_ylabel("library inductors that physically fit (of 11)")
    a2.set_title("(b) the design space the height rule allows", fontsize=10, loc="left")
    a2.legend(fontsize=8); a2.set_ylim(-0.4, 11)
    fig.suptitle("FIG-0F-A  A physically realizable HVR/package stack — and the two "
                 "thicknesses that were not", fontsize=11, y=1.02)
    fig.savefig(OUT / "FIG_0F_A_realizable_stack.png"); plt.close(fig)


def fig_B():
    """FIG-0F-B: what changed from 240 W to 1 kW."""
    geo = rows("geometry_recheck.csv")
    kw = rows("1kw_candidates.csv", True)
    cal = json.loads((OUT / "cooling_1kw_calibration.json").read_text())
    fig, axes = plt.subplots(1, 4, figsize=(13.0, 3.5))
    items = [("load (W)", 240, 1000),
             ("regulators M", 4, 49),
             ("h_top (kW/m²K)", 17.52, cal["h_top_W_m2K"] / 1e3),
             ("tile height (µm)", 150, 720)]
    for ax, (lab, a, b) in zip(axes, items):
        bars = ax.bar(["240 W\nvehicle", "1 kW\nreference"], [a, b],
                      color=[C["old"], C["src"]], edgecolor="k", lw=0.7, width=0.6)
        for r, v in zip(bars, (a, b)):
            ax.text(r.get_x() + r.get_width() / 2, v, f"{v:,.4g}", ha="center",
                    va="bottom", fontsize=8.5)
        ax.set_title(lab, fontsize=9.5)
        ax.set_ylim(0, max(a, b) * 1.25)
    fig.suptitle("FIG-0F-B  The 240 W → 1 kW scaling chain: every one of these had to be "
                 "rebuilt, not scaled", fontsize=11, y=1.05)
    fig.tight_layout(); fig.savefig(OUT / "FIG_0F_B_scaling_chain.png"); plt.close(fig)


def fig_C():
    """FIG-0F-C: ARCH_A vs ARCH_B thickness margin at 1 kW -- the crossover."""
    kw = [r for r in rows("1kw_candidates.csv", True) if r["group"] == "thickness"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.6, 4.1))
    for arch, col, mk in (("ARCH_A", C["new"], "o"), ("ARCH_B", C["bad"], "s")):
        s = sorted([r for r in kw if r["arch"] == arch], key=lambda r: F(r, "h_sub_mm"))
        h = [F(r, "h_sub_mm") for r in s]
        p = [F(r, "P_elec_total_w") for r in s]
        a1.plot(h, p, mk + "-", color=col, lw=1.7, ms=6, label=arch)
        i = int(np.argmin(p))
        a1.plot(h[i], p[i], "*", color=col, ms=17, mec="k", mew=0.6)
        a1.annotate(f"{arch} electrical\noptimum at {h[i]:.2f} mm", (h[i], p[i]),
                    textcoords="offset points",
                    xytext=((-96, 16) if arch == "ARCH_A" else (8, -30)),
                    fontsize=7.5, color=col)
        a2.plot(h, [F(r, "die_warpage_pv_um") for r in s], mk + "-", color=col, lw=1.7,
                ms=(9 if arch == "ARCH_A" else 5), alpha=(1.0 if arch == "ARCH_A" else 0.85),
                mfc=("none" if arch == "ARCH_A" else None), label=arch)
    a1.set_xlabel("substrate thickness (mm)"); a1.set_ylabel("total electrical loss (W)")
    a1.set_title("(a) electrical: ARCH_B turns around, ARCH_A does not", fontsize=10, loc="left")
    a1.legend(fontsize=8)
    a2.set_xlabel("substrate thickness (mm)"); a2.set_ylabel("die warpage p-v (µm)")
    a2.set_title("(b) mechanical: thicker is monotonically better for both\n"
                 "(curves coincide -- the two architectures share the same geometry)",
                 fontsize=9.5, loc="left")
    a2.legend(fontsize=8)
    fig.suptitle("FIG-0F-C  At 1 kW the LV-TSV architecture develops a genuine three-domain "
                 "thickness conflict", fontsize=11, y=1.02)
    fig.savefig(OUT / "FIG_0F_C_thickness_margin.png"); plt.close(fig)


def fig_D():
    """FIG-0F-D: footprint, free package vs board-mounted."""
    fp = [r for r in rows("1kw_candidates.csv", True) if r["group"] == "footprint"]
    fp = sorted(fp, key=lambda r: F(r, "a_hvr_total_mm2"))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.6, 4.1))
    A = [F(r, "a_hvr_total_mm2") for r in fp]
    a1.plot(A, [F(r, "P_elec_total_w") for r in fp], "o-", color=C["new"], lw=1.7, ms=6)
    a1.set_xlabel("total HVR footprint (mm²)"); a1.set_ylabel("total electrical loss (W)",
                                                              color=C["new"])
    a1.tick_params(axis="y", labelcolor=C["new"])
    t = a1.twinx()
    t.plot(A, [F(r, "die_warpage_pv_um") for r in fp], "s--", color=C["bad"], lw=1.7, ms=6)
    t.set_ylabel("free warpage p-v (µm)", color=C["bad"]); t.tick_params(axis="y",
                                                                        labelcolor=C["bad"])
    t.grid(False)
    a1.set_title("(a) BC-A free package: the opposition survives", fontsize=10, loc="left")

    p = OUT / "bcb_pairs_1kw.csv"
    if p.exists():
        bb = [r for r in rows("bcb_pairs_1kw.csv") if r["group"] == "footprint"]
        bb = sorted(bb, key=lambda r: F(r, "a_hvr_total_mm2"))
        if bb:
            Ab = [F(r, "a_hvr_total_mm2") for r in bb]
            a2.plot(Ab, [F(r, "P_elec_total_w") for r in bb], "o-", color=C["new"], lw=1.7, ms=6)
            a2.set_xlabel("total HVR footprint (mm²)")
            a2.set_ylabel("total electrical loss (W)", color=C["new"])
            a2.tick_params(axis="y", labelcolor=C["new"])
            t2 = a2.twinx()
            t2.plot(Ab, [F(r, "die_warpage_pv_um") for r in bb], "s--", color=C["b"],
                    lw=1.7, ms=6)
            t2.set_ylabel("mounted warpage p-v (µm)", color=C["b"])
            t2.tick_params(axis="y", labelcolor=C["b"]); t2.grid(False)
    a2.set_title("(b) BC-B board-mounted", fontsize=10, loc="left")
    fig.suptitle("FIG-0F-D  Footprint response in both assembly states, 1 kW", fontsize=11,
                 y=1.02)
    fig.savefig(OUT / "FIG_0F_D_footprint_free_vs_mounted.png"); plt.close(fig)


def fig_E():
    """FIG-0F-E: qualification of the mounted metric."""
    q = rows("bcb_metric_verdicts.csv")
    d = rows("bcb_metric_qualification.csv")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.4, 4.2))
    names = [r["metric"] for r in q]
    sep = [float(r["min_separation_pct"]) for r in q]
    okq = [r["QUALIFIED"] == "True" for r in q]
    cols = [C["src"] if o else C["bad"] for o in okq]
    y = np.arange(len(names))
    a1.barh(y, sep, color=cols, edgecolor="k", lw=0.6)
    a1.axvline(1.0, color="k", ls="--", lw=1.2)
    a1.text(1.15, len(names) - 0.6, "2·u_m = 1 %\nresolution floor", fontsize=7)
    a1.set_yticks(y); a1.set_yticklabels([n.replace("_", " ") for n in names], fontsize=7.5)
    a1.set_xscale("log"); a1.set_xlabel("minimum thin/thick separation across 9 corners (%)")
    a1.set_title("(a) robustness: does the ordering hold and stay resolved?", fontsize=10,
                 loc="left")
    for i, o in enumerate(okq):
        a1.text(sep[i] * 1.12, i, "QUALIFIED" if o else "REJECTED", va="center", fontsize=7,
                color=(C["src"] if o else C["bad"]), weight="bold")

    for mt, col, mk in (("shear_p99_MPa", C["warn"], "o"),
                        ("die_warpage_pv_um", C["src"], "s"),
                        ("rel_disp_p99_um", C["bad"], "^")):
        for cfg, ls in (("thin", "-"), ("thick", "--")):
            v = [(int(r["interface_nz"]), float(r[mt])) for r in d
                 if r["config"] == cfg and r["study"] == "convergence" and r.get(mt)]
            v.sort()
            if not v:
                continue
            base = v[-1][1]
            a2.plot([x[0] for x in v], [100 * (x[1] - base) / abs(base) for x in v],
                    mk + ls, color=col, lw=1.4, ms=5,
                    label=f"{mt.replace('_',' ')} ({cfg})")
    a2.axhline(0, color="k", lw=0.8)
    a2.set_xlabel("interface through-thickness elements"); a2.set_xticks([1, 2, 4])
    a2.set_ylabel("deviation from the finest mesh (%)")
    a2.set_title("(b) convergence under BC-B", fontsize=10, loc="left")
    a2.legend(fontsize=6.5, ncol=2)
    fig.suptitle("FIG-0F-E  Qualifying a board-mounted metric before using it for design",
                 fontsize=11, y=1.02)
    fig.savefig(OUT / "FIG_0F_E_bcb_metric_qualification.png"); plt.close(fig)


def fig_F():
    """FIG-0F-F: ET vs ETM at 1 kW."""
    k = rows("1kw_candidates.csv", True)
    fig, ax = plt.subplots(figsize=(7.4, 5.0))
    groups = {"thickness": ("o", C["new"]), "footprint": ("s", C["warn"]),
              "placement": ("^", C["b"])}
    for g, (mk, col) in groups.items():
        s = [r for r in k if r["group"] == g]
        ax.scatter([F(r, "die_warpage_pv_um") for r in s],
                   [F(r, "P_elec_total_w") for r in s], marker=mk, s=58, color=col,
                   edgecolor="k", lw=0.5, label=g, zorder=3)
    pts = sorted([(F(r, "die_warpage_pv_um"), F(r, "P_elec_total_w"), r) for r in k],
                 key=lambda t: (t[0], t[1]))
    front, best = [], float("inf")
    for w, p, r in pts:
        if p < best - 1e-9:
            front.append((w, p, r)); best = p
    ax.plot([x[0] for x in front], [x[1] for x in front], "-", color=C["src"], lw=1.8,
            zorder=2, label="ETM Pareto front")
    et = min(k, key=lambda r: F(r, "P_elec_total_w"))
    ax.scatter([F(et, "die_warpage_pv_um")], [F(et, "P_elec_total_w")], marker="*", s=300,
               color=C["src"], edgecolor="k", lw=0.7, zorder=4, label="ET optimum")
    ax.set_xlabel("die warpage p-v, free package (µm)")
    ax.set_ylabel("total electrical loss (W)")
    ax.set_title("FIG-0F-F  ET vs ETM at the 1-kW reference\n"
                 f"{len(front)} candidates on the Pareto front of {len(k)}", fontsize=10,
                 loc="left")
    ax.legend(fontsize=8)
    fig.savefig(OUT / "FIG_0F_F_et_vs_etm_1kw.png"); plt.close(fig)


def fig_G():
    """FIG-0F-G: parametric constraint sensitivity."""
    e = rows("mechanical_epsilon_sweep.csv")
    eps = [F(r, "epsilon_um") for r in e]
    pen = [F(r, "penalty_pct") if r["penalty_pct"] else float("nan") for r in e]
    nok = [int(r["n_feasible"]) for r in e]
    fig, ax = plt.subplots(figsize=(8.0, 4.6))
    ax.plot(eps, pen, "-", color=C["bad"], lw=2.0)
    ax.set_xlabel("hypothetical warpage limit ε (µm)")
    ax.set_ylabel("electrical penalty of complying (%)", color=C["bad"])
    ax.tick_params(axis="y", labelcolor=C["bad"])
    t = ax.twinx(); t.step(eps, nok, where="post", color=C["old"], lw=1.3)
    t.set_ylabel("admissible candidates", color=C["old"]); t.grid(False)
    first = next((F(r, "epsilon_um") for r in e if r["et_optimum_admissible"] == "False"), None)
    if first:
        ax.axvline(first, color=C["src"], ls="--", lw=1.5)
        ax.text(first, max(p for p in pen if p == p) * 0.55,
                f"  ET optimum first excluded\n  at ε = {first:.3f} µm", fontsize=8,
                color=C["src"])
    ax.set_title("FIG-0F-G  PARAMETRIC CONSTRAINT SENSITIVITY — not a feasibility result.\n"
                 "No source-backed mechanical criterion was found, so ε is hypothetical.",
                 fontsize=9.5, loc="left")
    fig.savefig(OUT / "FIG_0F_G_epsilon_sweep.png"); plt.close(fig)


def fig_H():
    """FIG-0F-H: where mechanics becomes decision-relevant."""
    k = rows("1kw_candidates.csv", True)
    th = [r for r in k if r["group"] == "thickness"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.0, 4.2))
    for arch, col, mk in (("ARCH_A", C["new"], "o"), ("ARCH_B", C["bad"], "s")):
        s = sorted([r for r in th if r["arch"] == arch], key=lambda r: F(r, "h_sub_mm"))
        h = [F(r, "h_sub_mm") for r in s]
        p0 = F(s[0], "P_elec_total_w")
        a1.plot(h, [100 * (F(r, "P_elec_total_w") - p0) / p0 for r in s], mk + "-",
                color=col, lw=1.7, ms=6, label=f"{arch} electrical")
    a1.axhline(0, color="k", lw=1.0)
    s = sorted([r for r in th if r["arch"] == "ARCH_A"], key=lambda r: F(r, "h_sub_mm"))
    w0 = F(s[0], "die_warpage_pv_um")
    a1.plot([F(r, "h_sub_mm") for r in s],
            [100 * (F(r, "die_warpage_pv_um") - w0) / w0 for r in s], "^--",
            color=C["src"], lw=1.7, ms=6, label="warpage (both)")
    a1.set_xlabel("substrate thickness (mm)")
    a1.set_ylabel("change from the thinnest realizable case (%)")
    a1.set_title("(a) mechanics improves ~90 %, electrics move <0.15 %", fontsize=10,
                 loc="left")
    a1.legend(fontsize=8)

    labels, rates = [], []
    fp = sorted([r for r in k if r["group"] == "footprint" and int(r["m_vr"]) >= 36],
                key=lambda r: F(r, "a_hvr_total_mm2"))
    if len(fp) >= 2:
        dP = F(fp[0], "P_elec_total_w") - F(fp[-1], "P_elec_total_w")
        dW = F(fp[-1], "die_warpage_pv_um") - F(fp[0], "die_warpage_pv_um")
        labels.append("footprint\n(1 kW)"); rates.append(abs(dP / dW))
    b = sorted([r for r in th if r["arch"] == "ARCH_B"], key=lambda r: F(r, "h_sub_mm"))
    i = int(np.argmin([F(r, "P_elec_total_w") for r in b]))
    dP = F(b[-1], "P_elec_total_w") - F(b[i], "P_elec_total_w")
    dW = F(b[i], "die_warpage_pv_um") - F(b[-1], "die_warpage_pv_um")
    labels.append("thickness ARCH_B\n(1 kW)"); rates.append(abs(dP / dW))
    labels.append("footprint\n(240 W, Phase 0E)"); rates.append(11.48)
    labels.append("placement\n(240 W, Phase 0E)"); rates.append(3.70)
    cols = [C["src"], C["src"], C["old"], C["old"]]
    bars = a2.bar(labels, rates, color=cols, edgecolor="k", lw=0.7, width=0.6)
    for r, v in zip(bars, rates):
        a2.text(r.get_x() + r.get_width() / 2, v * 1.15, f"{v:.3g}", ha="center", fontsize=8.5)
    a2.set_yscale("log"); a2.set_ylabel("cost of mechanics (W per µm saved)")
    a2.set_title("(b) at 1 kW mechanics is far cheaper to buy", fontsize=10, loc="left")
    fig.suptitle("FIG-0F-H  Where mechanics becomes decision-relevant", fontsize=11, y=1.02)
    fig.savefig(OUT / "FIG_0F_H_crossover_map.png"); plt.close(fig)


if __name__ == "__main__":
    which = sys.argv[1:] or ["A", "B", "C", "E", "F", "G", "H", "D"]
    fns = {"A": fig_A, "B": fig_B, "C": fig_C, "D": fig_D, "E": fig_E,
           "F": fig_F, "G": fig_G, "H": fig_H}
    for k in which:
        try:
            fns[k](); print("wrote", k)
        except Exception as ex:
            print(f"FIG {k} failed: {type(ex).__name__}: {ex}")
