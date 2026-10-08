#!/usr/bin/env python3
"""Phase-0B minimum decisive figure.

Communicates, for each gate case: architecture, temperature response, warpage,
silicon stress and interface response - so a reader can see at a glance whether
architecture produces a RESOLVED mechanical signal.

Every panel here is SOLVED under the controlled-heat DOE (fixed 42 W total HVR
heat). No electrically coupled ET/ETM ranking is shown, because the electrical
objective has not been evaluated consistently yet - that is the deferred replay.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etm.config import load_doe, load_stack          # noqa: E402
from etm.placement import case_tiles                 # noqa: E402

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0b"


def field_at_z(nodes, vals, z, tol=1e-6):
    m = np.abs(nodes[:, 2] - z) < tol
    return nodes[m, 0], nodes[m, 1], vals[m]


def panel_tiles(ax, tiles, stack, lw=1.0, ec="k"):
    for t in tiles:
        ax.add_patch(Rectangle((t.x0, t.y0), t.ax, t.ay, fc="none", ec=ec, lw=lw, ls="--"))


def main(cases: list[str], bc: str = "BC_A"):
    stack, doe = load_stack(), load_doe()
    g = stack["geometry"]
    Dx = g["functional_die"]["size_x"]["value"]
    t_if = g["interface_layer"]["thickness"]["value"]
    t_die = g["functional_die"]["thickness"]["value"]

    data = {}
    for c in cases:
        d = OUT / c / f"baseline_{bc}"
        data[c] = {
            "m": json.loads((d / "metrics.json").read_text()),
            "nodes": np.load(d / "nodes.npy"),
            "T": np.load(d / "temps.npy"),
            "U": np.load(d / "disp.npy"),
            "tiles": case_tiles(doe["cases"][c], stack, doe),
        }

    ncol = len(cases)
    fig = plt.figure(figsize=(4.1 * ncol, 13.6), dpi=150)
    gs = fig.add_gridspec(5, ncol, height_ratios=[1.0, 1.0, 1.0, 1.0, 0.95], hspace=0.34,
                          wspace=0.22)

    # shared colour scales so cases are visually comparable
    zdie = data[cases[0]]["m"]["spec"]["h_sub"] + t_if + t_die
    Ts, Ws, Ss = [], [], []
    for c in cases:
        d = data[c]
        _, _, tv = field_at_z(d["nodes"], d["T"], zdie)
        _, _, wv = field_at_z(d["nodes"], d["U"][:, 2] * 1000.0, zdie)
        Ts.append(tv); Ws.append(wv - wv.mean())
    tlo, thi = min(v.min() for v in Ts), max(v.max() for v in Ts)
    wlim = max(np.abs(v).max() for v in Ws)

    for j, c in enumerate(cases):
        d = data[c]; mm = d["m"]; sp = mm["spec"]

        ax = fig.add_subplot(gs[0, j])
        for t in d["tiles"]:
            ax.add_patch(Rectangle((t.x0, t.y0), t.ax, t.ay, fc="#d9534f", ec="#7d2b28", lw=1))
            ax.text(t.cx, t.cy, f"{t.power_w:.1f}W", ha="center", va="center",
                    fontsize=6, color="w", weight="bold")
        ax.add_patch(Rectangle((-Dx/2, -Dx/2), Dx, Dx, fc="none", ec="#4a6fa5", lw=1.3, ls="--"))
        ax.add_patch(Rectangle((-15, -15), 30, 30, fc="none", ec="#8a94a6", lw=1))
        ax.set_xlim(-16, 16); ax.set_ylim(-16, 16); ax.set_aspect("equal")
        ax.set_title(f"{c}  -  N={sp['n_vr']}, {sp['placement']}\n"
                     f"tile {sp['tile_ax']:.2f}x{sp['tile_ay']:.2f} mm, "
                     f"$h_{{sub}}$={sp['h_sub']*1000:.0f} um, "
                     f"$P_{{HVR}}$={mm['loads']['p_hvr_total_W']:.1f} W",
                     fontsize=8.5)
        ax.tick_params(labelsize=6)
        if j == 0: ax.set_ylabel("architecture\ny (mm)", fontsize=8)

        ax = fig.add_subplot(gs[1, j])
        x, y, v = field_at_z(d["nodes"], d["T"], zdie)
        cf = ax.tricontourf(x, y, v, levels=24, cmap="inferno", vmin=tlo, vmax=thi)
        panel_tiles(ax, d["tiles"], stack, ec="w", lw=0.8)
        ax.set_aspect("equal"); ax.tick_params(labelsize=6)
        ax.set_title(f"$T$ on die top:  max {mm['thermal']['T_max_C']:.2f} C, "
                     f"span {v.max()-v.min():.2f} K", fontsize=8)
        plt.colorbar(cf, ax=ax, shrink=0.82, label="T (C)")
        if j == 0: ax.set_ylabel("temperature\ny (mm)", fontsize=8)

        ax = fig.add_subplot(gs[2, j])
        x, y, v = field_at_z(d["nodes"], d["U"][:, 2] * 1000.0, zdie)
        v = v - v.mean()
        cf = ax.tricontourf(x, y, v, levels=24, cmap="RdBu_r", vmin=-wlim, vmax=wlim)
        panel_tiles(ax, d["tiles"], stack, ec="k", lw=0.8)
        ax.set_aspect("equal"); ax.tick_params(labelsize=6)
        ax.set_title(f"die out-of-plane $u_z$ (mean-removed)\n"
                     f"p-v = {mm['structural']['die_warpage_pv_um']:.3f} um", fontsize=8)
        plt.colorbar(cf, ax=ax, shrink=0.82, label="$u_z$ (um)")
        if j == 0: ax.set_ylabel("warpage\ny (mm)", fontsize=8)

        ax = fig.add_subplot(gs[3, j])
        x, y, v = field_at_z(d["nodes"], d["U"][:, 2] * 1000.0, 0.0)
        v = v - v.mean()
        cf = ax.tricontourf(x, y, v, levels=24, cmap="RdBu_r")
        panel_tiles(ax, d["tiles"], stack, ec="k", lw=0.8)
        ax.set_aspect("equal"); ax.tick_params(labelsize=6)
        ax.set_title(f"package underside $u_z$ (mean-removed)\n"
                     f"p-v = {mm['structural']['pkg_warpage_pv_um']:.3f} um", fontsize=8)
        plt.colorbar(cf, ax=ax, shrink=0.82, label="$u_z$ (um)")
        if j == 0: ax.set_ylabel("package warpage\ny (mm)", fontsize=8)

    # summary bars with uncertainty bands
    keys = [("die_warpage_pv_um", "die warp\n(um)"), ("pkg_warpage_pv_um", "pkg warp\n(um)"),
            ("si_principal_p99_MPa", "Si $\\sigma_1$ p99\n(MPa)"),
            ("interface_shear_p99_MPa", "iface shear\np99 (MPa)"),
            ("interface_peel_p99_MPa", "iface peel\np99 (MPa)"),
            ("T_max_C", "$T_{max}$\n(C)")]
    getters = {
        "die_warpage_pv_um": lambda m: m["structural"]["die_warpage_pv_um"],
        "pkg_warpage_pv_um": lambda m: m["structural"]["pkg_warpage_pv_um"],
        "si_principal_p99_MPa": lambda m: m["structural"]["si_principal_MPa"]["p99"],
        "interface_shear_p99_MPa": lambda m: m["structural"]["interface_shear_MPa"]["p99"],
        "interface_peel_p99_MPa": lambda m: m["structural"]["interface_peel_MPa"]["p99"],
        "T_max_C": lambda m: m["thermal"]["T_max_C"],
    }
    ma = json.loads((OUT / "materiality_analysis.json").read_text())
    ub = {"u_mesh_rel": ma.get("u_mesh_rel", {})}

    ax = fig.add_subplot(gs[4, :])
    w = 0.8 / len(cases)
    xs = np.arange(len(keys))
    colors = ["#3b6ea5", "#d9534f", "#4c9a52", "#8a63a8"]
    for i, c in enumerate(cases):
        mm = data[c]["m"]
        vals, errs = [], []
        for k, _ in keys:
            v = getters[k](mm)
            u = ub["u_mesh_rel"].get(k, 0.0) or 0.0
            base = getters[k](data[cases[0]]["m"])
            vals.append(v / abs(base) * 100.0)
            errs.append(u * 100.0 * v / abs(base))
        ax.bar(xs + i * w - 0.4 + w / 2, vals, w, yerr=errs, capsize=3,
               label=c, color=colors[i % len(colors)], edgecolor="k", linewidth=0.5)
    ax.axhline(100, color="k", lw=0.7, ls=":")
    ax.set_xticks(xs); ax.set_xticklabels([l for _, l in keys], fontsize=8)
    ax.set_ylabel(f"% of {cases[0]} value", fontsize=9)
    ax.set_title("Architectural spread, normalised to C05. Error bars = mesh convergence "
                 "uncertainty (1u). The spec resolves an effect only when the spread "
                 "exceeds 2u.", fontsize=9)
    ax.legend(fontsize=8, ncol=len(cases)); ax.tick_params(labelsize=7)
    ax.grid(axis="y", alpha=0.3)

    fig.suptitle(
        f"Phase-0B M0 first mechanical gate ({bc}) - controlled DOE: "
        f"240 W die, 42 W total HVR heat, 96 mm$^2$ total HVR footprint held CONSTANT\n"
        "Only architecture differs. SOLVED NOW: operational thermoelastic response. "
        "DEFERRED: electrically coupled HVR loss, assembly pre-stress, ET/ETM ranking.",
        fontsize=11, y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.975])
    p = OUT / f"PHASE0B_DECISIVE_FIGURE_{bc}.png"
    fig.savefig(p, bbox_inches="tight"); plt.close(fig)
    print(f"wrote {p}")


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("BC")]
    bc = next((x for x in sys.argv[1:] if x.startswith("BC")), "BC_A")
    main(a or ["C05", "C07"], bc)
