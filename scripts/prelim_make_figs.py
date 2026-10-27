"""Generate every presentation chart FROM the repository artifacts as SVG."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                      # noqa: E402
import numpy as np                                                   # noqa: E402

R = Path(__file__).resolve().parents[1]
for _p in ("scripts/phase0nw", "scripts/phase0m", "scripts/phase0mr", "scripts"):
    sys.path.insert(0, str(R / _p))
FIG = R / "presentation" / "prelim_hvr" / "figs"
FIG.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.size": 15, "axes.labelsize": 16, "axes.titlesize": 17,
    "xtick.labelsize": 14, "ytick.labelsize": 14, "legend.fontsize": 13,
    "svg.fonttype": "none", "figure.facecolor": "white",
    "axes.spines.top": False, "axes.spines.right": False,
})
C = {"z1": "#1f6feb", "z2": "#d1442f", "ok": "#1a7f37", "warn": "#bf8700",
     "open": "#cf222e", "hist": "#8c959f", "accent": "#6639ba"}


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIG / name, format="svg", bbox_inches="tight", transparent=False)
    plt.close(fig)
    print("  ", name)


def jload(p):
    f = R / p
    return json.loads(f.read_text()) if f.exists() else None


# --- 1. BGA count vs solved peak ball current ---------------------------
def fig_bga_count():
    ex = jload("research/phase0nak/bga_exhaustive_closure.json")
    if ex and ex.get("screen"):
        rows, crit = ex["screen"], ex["meta"]["criterion_A_per_ball"]
        key = lambda r, s: r[f"i_ball_max_A__{s}"]
    else:
        aj = jload("research/phase0naj/bga_count_closure.json")
        if not aj:
            return
        rows = [r for r in aj["rows"] if r.get("legal")]
        crit = aj["meta"]["criterion_A_per_ball"]
        key = lambda r, s: r[f"i_ball_max_A__{s}"]
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.2), sharey=True)
    for ax, arch in zip(axes, ("Z1", "Z2")):
        sub = sorted([r for r in rows if r["arch"] == arch],
                     key=lambda r: r["n_per_rail"])
        for s, st, lab in (("HV_S0", "-", "HV-S0 (23.7 A)"),
                           ("HV_S1", "--", "HV-S1 (94.8 A)"),
                           ("HV_S2", ":", "HV-S2 (164 A)")):
            xs = [r["n_per_rail"] for r in sub if f"i_ball_max_A__{s}" in r]
            ys = [key(r, s) for r in sub if f"i_ball_max_A__{s}" in r]
            if xs:
                ax.plot(xs, ys, st, lw=2.2,
                        color=C["z1"] if arch == "Z1" else C["z2"], label=lab)
        ax.axhline(crit, color=C["open"], lw=2.4)
        ax.annotate("1.5 A ENGINEERING CRITERION\n(not a lifetime limit)",
                    xy=(0.5, crit), xycoords=ax.get_yaxis_transform(),
                    xytext=(0.5, 0.06), textcoords="axes fraction",
                    color=C["open"], fontsize=11.5, ha="center", va="bottom",
                    arrowprops=dict(arrowstyle="->", color=C["open"], lw=1.4),
                    bbox=dict(boxstyle="round,pad=.3", fc="white",
                              ec=C["open"], lw=1.4))
        ax.set_yscale("log")
        ax.set_xlabel("BGA balls per rail")
        ax.set_title(f"{arch} — solved peak ball current")
        ax.grid(alpha=.25)
        ax.legend(frameon=True, framealpha=.95, edgecolor="#d7dde4",
                  loc="upper right", fontsize=11.5)
    axes[0].set_ylabel("peak ball current (A)")
    save(fig, "bga_count.svg")


# --- 2. equal sharing vs solved sharing ---------------------------------
def fig_sharing():
    """Solved per-ball currents, re-solved here.

    An earlier version of this figure SYNTHESISED a distribution from the
    stored min/max/mean with a random generator. That would have put a
    fabricated shape on a results slide, so the network is re-solved instead
    and the real per-ball currents are plotted.
    """
    import pkg_rdl_network as K
    import pad_interface as PI
    import physical_coords as PCO
    cells = PCO.physical_cell_coordinates()
    sel = PCO.select_power_sites(PCO.bga_lattice_sites(), cells, 16, 16,
                                 "nearest_symmetric")
    net = K.VoltageFedNetwork(301, K.sheet_resistance_ohm_sq(5.0e-3, 0.30))
    net.build(sel["supply"], cells, PI.bga_ball_resistance_ohm(),
              K.RHO_C_CASES["CONTACT_N"], K.RHO_C_CASES["CONTACT_N"],
              PI.BGA_D_UM * 1e-3, K.VR_TILE_SIDE_MM, cell_shape="square")
    i = np.full(len(cells), 1.0 / len(cells))
    rep = net.report(net.solve(i), i)
    solved = np.sort(np.asarray(rep["i_ball_a"]))[::-1]
    n = len(solved)
    fig, ax = plt.subplots(figsize=(11.5, 4.8))
    x = np.arange(n)
    ax.bar(x - .2, [1.0 / n] * n, width=.4, color=C["hist"],
           label=f"assumed equal sharing   I/N = {1.0/n:.4f}")
    ax.bar(x + .2, solved, width=.4, color=C["z1"],
           label=f"solved sharing   {solved.min():.4f} – {solved.max():.4f}")
    ax.set_xlabel("BGA supply ball, sorted by solved current")
    ax.set_ylabel("fraction of total current")
    ax.set_title("A uniform load does NOT give uniform ball currents")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=.25)
    ax.set_ylim(0, solved.max() * 1.42)
    ax.text(.985, .70,
            f"peak = {solved.max()*n:.2f}× the equal-share value\n"
            f"spread = {100*(solved.max()-solved.min())/solved.mean():.0f} % of the mean",
            transform=ax.transAxes, fontsize=14, color=C["open"],
            ha="right", va="top",
            bbox=dict(boxstyle="round,pad=.35", fc="white", ec=C["open"], lw=1.6))
    save(fig, "sharing.svg")


# --- 3. cutout vs placement --------------------------------------------
def fig_cutout():
    vf = jload("research/phase0nai/voltage_fed_network.json")
    if not vf:
        return
    c = vf["controlled"]
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    vals = [c["delta_R_cutout_ohm"] * 1e3, c["delta_R_placement_ohm"] * 1e3]
    bars = ax.barh(["ΔR  cutout\n(geometry removed)",
                    "ΔR  placement\n(same sites, other rule)"], vals,
                   color=[C["z2"], C["accent"]], height=.55)
    for b, v in zip(bars, vals):
        ax.text(v + max(vals) * .02, b.get_y() + b.get_height() / 2,
                f"{v:+.4f} mΩ", va="center", fontsize=15)
    ax.set_xlabel("change in loop resistance (mΩ)")
    ax.set_xlim(0, max(vals) * 1.3)
    ax.set_title(f"Placement dominates the cutout by "
                 f"{c['placement_over_cutout']:.0f}×")
    ax.grid(axis="x", alpha=.25)
    save(fig, "cutout.svg")


# --- 4. pad count admissible region -------------------------------------
def fig_pads():
    pd_ = jload("research/phase0naj/pad_count_closure.json")
    if not pd_:
        return
    rows = pd_["rows"]
    n = [r["n_per_rail"] for r in rows]
    fig, ax = plt.subplots(figsize=(11.5, 5.0))
    ax.loglog(n, [r["p_system_both_rails_w"] for r in rows], "o-",
              color=C["z1"], lw=2.2, label="interface loss (W)")
    ax2 = ax.twinx()
    ax2.loglog(n, [r["j_per_pad_A_cm2"] for r in rows], "s--",
               color=C["open"], lw=2.2, label="average J (A/cm²)")
    ax2.axhline(1e6, color=C["warn"], lw=2)
    ax2.text(n[-1], 1.1e6, "1e6 A/cm²  accelerated-stress regime (CONTEXT ONLY)",
             ha="right", fontsize=11.5, color=C["warn"])
    lo = pd_["admissible_region"]["J_1e5"]["n_min"]
    ax.axvspan(lo, n[-1], color=C["ok"], alpha=.10)
    ax.text(lo * 1.3, max(r["p_system_both_rails_w"] for r in rows) * .4,
            f"admissible at 1e5 A/cm²\nN ≥ {lo}", color=C["ok"], fontsize=13)
    ax.axvline(pd_["meta"]["n_drop_floor"], color=C["hist"], ls=":", lw=2)
    ax.text(pd_["meta"]["n_drop_floor"] * 1.1, 1e-2,
            "voltage-drop floor N=4\nNON-PHYSICAL (5e6 A/cm²)",
            fontsize=12, color=C["hist"])
    ax.set_xlabel("source pads per rail per cell")
    ax.set_ylabel("system interface loss (W)", color=C["z1"])
    ax2.set_ylabel("average current density (A/cm²)", color=C["open"])
    ax.set_title("Voltage drop alone does not select a pad count")
    ax.grid(alpha=.25, which="both")
    save(fig, "pads.svg")


# --- 5. fidelity ladder --------------------------------------------------
def fig_ladder():
    fl = jload("research/phase0naj/fidelity_ladder.json")
    if not fl:
        return
    rows = fl["rows"]
    lab = [f"{r['t_cu_um']:.0f} µm\n×{r['n_layers']}" for r in rows]
    x = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(11.5, 4.8))
    ax.bar(x - .2, [r["R0_w_per_vr"] for r in rows], .4,
           color=C["hist"], label="R0  width-rule Manhattan")
    ax.bar(x + .2, [r["R2_w_per_vr"] for r in rows], .4,
           color=C["z1"], label="R2  2-D resistive sheet")
    for i, r in enumerate(rows):
        ax.text(i, max(r["R0_w_per_vr"], r["R2_w_per_vr"]) * 1.05,
                f"+{r['R0_err_vs_R2_pct']:.0f}%", ha="center", fontsize=12,
                color=C["open"])
    ax.set_xticks(x, lab)
    ax.set_ylabel("output-net loss per VR (W)")
    ax.set_title("R0 overstates the output plane — R1 retired, R2 required")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=.25)
    save(fig, "ladder.svg")


# --- 6. gate status ------------------------------------------------------
def fig_gates():
    g = jload("research/phase0nw/physical_gates.json")
    if not g:
        return
    import collections
    c = collections.Counter(r["status"] for r in g["gates"])
    order = ["IMPLEMENTED", "SPECIFIED", "OPEN", "SUPERSEDED", "VALIDATED"]
    ks = [k for k in order if c.get(k)]
    vals = [c[k] for k in ks]
    col = {"IMPLEMENTED": C["ok"], "SPECIFIED": C["warn"], "OPEN": C["open"],
           "SUPERSEDED": C["hist"], "VALIDATED": C["accent"]}
    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    b = ax.bar(ks, vals, color=[col[k] for k in ks], width=.6)
    for bb, v in zip(b, vals):
        ax.text(bb.get_x() + bb.get_width() / 2, v + .8, str(v),
                ha="center", fontsize=16, fontweight="bold")
    ax.set_ylabel("gates")
    ax.set_title(f"Physical gate state — {sum(vals)} gates, "
                 f"{c.get('VALIDATED', 0)} VALIDATED")
    ax.grid(axis="y", alpha=.25)
    save(fig, "gates.svg")


# --- 7. runtime breakdown (historical, clearly labelled) -----------------
def fig_runtime():
    import csv
    f = R / "research/phase0nah/runtime_breakdown.csv"
    if not f.exists():
        return
    rows = [r for r in csv.DictReader(f.open()) if r["wall_s"]]
    rows = [r for r in rows if "arithmetic total" not in r["stage"]]
    lab = [f"{r['stage'][:38]}\n({r['case']})" for r in rows]
    val = [float(r["wall_s"]) for r in rows]
    fig, ax = plt.subplots(figsize=(12.5, 5.4))
    bars = ax.barh(lab, val, color=C["hist"], height=.6)
    for b, v in zip(bars, val):
        ax.text(v * 1.08, b.get_y() + b.get_height() / 2, f"{v:g} s",
                va="center", fontsize=12)
    ax.set_xscale("log")
    ax.set_xlabel("wall time (s, log scale)")
    ax.set_title("Where the time goes — HISTORICAL FROZEN R3C RUNTIME")
    ax.grid(axis="x", alpha=.25, which="both")
    save(fig, "runtime.svg")


if __name__ == "__main__":
    print("figures ->", FIG)
    for fn in (fig_bga_count, fig_sharing, fig_cutout, fig_pads, fig_ladder,
               fig_gates, fig_runtime):
        try:
            fn()
        except Exception as exc:
            print("   SKIP", fn.__name__, exc)
