#!/usr/bin/env python3
"""
Sweep VR count while re-optimizing each HVR architecture at the per-VR load current,
then plot system efficiency vs VR count for each HVR topology (N, K, K_A).

This couples:
  1) Width-based HVR optimizer (per-VR conversion loss, constraints, optimal W_H/W_L/f_sw)
  2) Routing-loss model (system-level PPDN loss vs number of VRs)

Key convention:
  - Total system load current is fixed: I_system = P_load / V_out
  - For each VR count M: I_out_per_vr = I_system / M
  - The width-based HVR optimizer is called with I_out = I_out_per_vr
  - Per-VR optimized conversion loss is multiplied by M to get total VR conversion loss
  - Routing loss is computed at the system level for the given VR count AND topology
    because it depends on the optimized switching frequency via skin effect.

Patched changes:
  - Routing loss now depends on Manhattan distance + TSV + bumps + f_sw
  - Routing loss is recomputed for each topology result using res.optimized_f_sw
  - Feasibility check uses width-based optimizer outputs (optimized_w_h / optimized_w_l)
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from HVR_FULL_OPT_sizing import run_hvr_optimization


# ============================================================
# 1) Routing model
# ============================================================

@dataclass
class DieConfig:
    die_area_mm2: float = 400.0
    die_side_mm: float = 22.36
    n_pol_segments: int = 100
    rho_mohm_per_mm: float = 50   # DC-equivalent RDL path resistance per mm at f_ref_hz
    i_out_total_a: float = 1000.0
    v_out: float = 1.0


class DVPDRoutingModel:
    """
    Manhattan-distance routing model with compact electrical path resistance:
        R_branch = R_vertical + R_lateral(f_sw, d_MH)

    where:
        R_vertical = 2*R_bump + R_tsv
        R_lateral  = rho_dc * sqrt(f_sw/f_ref) * d_MH

    Multiple VRs feeding the same POL are treated as parallel conductance paths:
        R_eff_i = 1 / sum_j(1 / R_ij)

    This preserves the original Manhattan methodology while making routing loss:
      - dependent on VR count / placement
      - dependent on optimized switching frequency
      - inclusive of TSV and bump path resistance
    """

    def __init__(self, die: DieConfig):
        self.die = die
        self.pols = self._place_pols()

    def _place_pols(self) -> np.ndarray:
        side = int(np.ceil(np.sqrt(self.die.n_pol_segments)))
        dx = self.die.die_side_mm / side
        pols = []
        for r in range(side):
            for c in range(side):
                if len(pols) >= self.die.n_pol_segments:
                    break
                pols.append((dx * (c + 0.5), dx * (r + 0.5)))
        return np.array(pols[: self.die.n_pol_segments], dtype=float)

    @staticmethod
    def place_vrs_A2(n_vr: int, die_side: float) -> np.ndarray:
        cols = int(np.ceil(np.sqrt(n_vr)))
        rows = int(np.ceil(n_vr / cols))
        vrs = []
        for r in range(rows):
            for c in range(cols):
                if len(vrs) >= n_vr:
                    break
                x = die_side / (cols + 1) * (c + 1)
                y = die_side / (rows + 1) * (r + 1)
                vrs.append((x, y))
        return np.array(vrs[:n_vr], dtype=float)

    @staticmethod
    def place_vrs_A1(n_vr: int, die_side: float) -> np.ndarray:
        per_side = int(np.ceil(n_vr / 4))
        sp = die_side / (per_side + 1)
        offset = 1.5
        vrs = []
        for i in range(per_side):
            if len(vrs) < n_vr:
                vrs.append((sp * (i + 1), -offset))
        for i in range(per_side):
            if len(vrs) < n_vr:
                vrs.append((sp * (i + 1), die_side + offset))
        for i in range(per_side):
            if len(vrs) < n_vr:
                vrs.append((-offset, sp * (i + 1)))
        for i in range(per_side):
            if len(vrs) < n_vr:
                vrs.append((die_side + offset, sp * (i + 1)))
        return np.array(vrs[:n_vr], dtype=float)

    def compute_ppdn_loss(
        self,
        vr_positions: np.ndarray,
        f_sw_hz: float,
        r_bump_ohm: float = 0.08e-3,
        r_tsv_ohm: float = 0.04e-3,
        f_ref_hz: float = 1e6,
    ) -> Dict[str, float]:
        s = len(self.pols)
        n = len(vr_positions)
        i_per_pol = self.die.i_out_total_a / s

        # Frequency-dependent lateral resistance coefficient
        rho_dc_ohm_per_mm = self.die.rho_mohm_per_mm * 1e-3
        rho_ac_ohm_per_mm = rho_dc_ohm_per_mm * np.sqrt(max(float(f_sw_hz), 1.0) / f_ref_hz)

        # Fixed vertical path contribution
        r_vertical = 2.0 * r_bump_ohm + r_tsv_ohm

        dist_matrix = np.zeros((s, n), dtype=float)
        r_branch = np.zeros((s, n), dtype=float)

        for i in range(s):
            for j in range(n):
                d = abs(self.pols[i][0] - vr_positions[j][0]) + abs(self.pols[i][1] - vr_positions[j][1])
                d = max(d, 0.01)  # avoid singularity
                dist_matrix[i, j] = d
                r_branch[i, j] = r_vertical + rho_ac_ohm_per_mm * d

        g_branch = 1.0 / r_branch
        g_sum = g_branch.sum(axis=1)
        r_eff = 1.0 / g_sum

        p_per_pol = i_per_pol ** 2 * r_eff
        total_ppdn_loss = float(p_per_pol.sum())

        frac_matrix = g_branch / g_sum[:, np.newaxis]
        i_per_vr = (frac_matrix * i_per_pol).sum(axis=0)

        return {
            "total_ppdn_loss_w": total_ppdn_loss,
            "avg_nearest_dist_mm": float(dist_matrix.min(axis=1).mean()),
            "vr_current_imbalance": float(i_per_vr.std() / i_per_vr.mean()) if i_per_vr.mean() > 0 else 0.0,
            "rho_ac_mohm_per_mm": float(rho_ac_ohm_per_mm * 1e3),
        }


# ============================================================
# 2) System-level sweep
# ============================================================

@dataclass
class TopologyPoint:
    vr_count: int
    i_out_per_vr_a: float
    conv_loss_per_vr_w: float
    conv_loss_total_w: float
    routing_loss_w: float
    total_loss_w: float
    efficiency_pct: float
    f_sw_opt_hz: float
    w_h_opt: float
    w_l_opt: float
    area_mm2: float
    avg_nearest_dist_mm: float
    rho_ac_mohm_per_mm: float
    feasible: bool


def architecture_key(res) -> Tuple[int, int, int]:
    return (res.architecture.N, res.architecture.K, res.architecture.K_A)


def architecture_label(key: Tuple[int, int, int]) -> str:
    n, k, ka = key
    return f"(N={n}, K={k}, K_A={ka})"


def _is_width_optimizer_feasible(res) -> bool:
    return (
        getattr(res, "optimized_w_h", None) is not None
        and getattr(res, "optimized_w_l", None) is not None
        and getattr(res, "optimized_f_sw", None) is not None
        and np.isfinite(getattr(res, "optimized_loss", np.nan))
    )


def sweep_efficiency_vs_vr_count(
    vr_counts: List[int],
    p_load_w: float = 1000.0,
    v_out: float = 1.0,
    v_in: float = 48.0,
    i_target_density: float = 2.5,
    target_component_count: int = 15,
    routing_arch: str = "A2",
    die_area_mm2: float = 400.0,
    n_pol_segments: int = 100,
    rho_mohm_per_mm: float = 50,
    w_h_values: Optional[np.ndarray] = None,
    w_l_values: Optional[np.ndarray] = None,
    f_sw_values: Optional[np.ndarray] = None,
    default_w_h: float = 1.0,
    default_w_l: float = 1.0,
    hs_area_per_width_mm2: float = 1.0,
    ls_area_per_width_mm2: float = 1.0,
    r_bump_ohm: float = 0.08e-3,
    r_tsv_ohm: float = 0.04e-3,
    f_ref_hz: float = 1e6,
    verbose: bool = True,
):
    i_system = p_load_w / v_out
    die = DieConfig(
        die_area_mm2=die_area_mm2,
        die_side_mm=math.sqrt(die_area_mm2),
        n_pol_segments=n_pol_segments,
        rho_mohm_per_mm=rho_mohm_per_mm,
        i_out_total_a=i_system,
        v_out=v_out,
    )
    routing = DVPDRoutingModel(die)

    all_curves: Dict[Tuple[int, int, int], List[TopologyPoint]] = {}

    for m in vr_counts:
        i_out_per_vr = i_system / m
        if verbose:
            print(f"\n=== VR count = {m} | I_out_per_vr = {i_out_per_vr:.3f} A ===")

        # Re-run HVR optimization at the new per-VR current.
        results = run_hvr_optimization(
            target_component_count=target_component_count,
            V_in=v_in,
            V_out=v_out,
            I_out=i_out_per_vr,
            I_target_density=i_target_density,
            w_h_values=w_h_values,
            w_l_values=w_l_values,
            f_sw_values=f_sw_values,
            default_w_h=default_w_h,
            default_w_l=default_w_l,
            hs_area_per_width_mm2=hs_area_per_width_mm2,
            ls_area_per_width_mm2=ls_area_per_width_mm2,
            verbose=False,
        )

        if routing_arch.upper() == "A1":
            vr_positions = routing.place_vrs_A1(m, die.die_side_mm)
        else:
            vr_positions = routing.place_vrs_A2(m, die.die_side_mm)

        for res in results:
            key = architecture_key(res)
            feasible = _is_width_optimizer_feasible(res)

            if feasible:
                routing_info = routing.compute_ppdn_loss(
                    vr_positions=vr_positions,
                    f_sw_hz=float(res.optimized_f_sw),
                    r_bump_ohm=r_bump_ohm,
                    r_tsv_ohm=r_tsv_ohm,
                    f_ref_hz=f_ref_hz,
                )
                routing_loss = float(routing_info["total_ppdn_loss_w"])
                avg_nearest_dist = float(routing_info["avg_nearest_dist_mm"])
                rho_ac = float(routing_info["rho_ac_mohm_per_mm"])

                conv_loss_per_vr = float(res.optimized_loss)
                conv_loss_total = m * conv_loss_per_vr
                total_loss = conv_loss_total + routing_loss
                eff = 100.0 * p_load_w / (p_load_w + total_loss)
                f_sw_opt = float(res.optimized_f_sw)
                w_h_opt = float(res.optimized_w_h)
                w_l_opt = float(res.optimized_w_l)
                area_mm2 = float(res.total_area_mm2)
            else:
                routing_loss = np.nan
                avg_nearest_dist = np.nan
                rho_ac = np.nan
                conv_loss_per_vr = np.nan
                conv_loss_total = np.nan
                total_loss = np.nan
                eff = np.nan
                f_sw_opt = np.nan
                w_h_opt = np.nan
                w_l_opt = np.nan
                area_mm2 = np.nan

            point = TopologyPoint(
                vr_count=m,
                i_out_per_vr_a=i_out_per_vr,
                conv_loss_per_vr_w=conv_loss_per_vr,
                conv_loss_total_w=conv_loss_total,
                routing_loss_w=routing_loss,
                total_loss_w=total_loss,
                efficiency_pct=eff,
                f_sw_opt_hz=f_sw_opt,
                w_h_opt=w_h_opt,
                w_l_opt=w_l_opt,
                area_mm2=area_mm2,
                avg_nearest_dist_mm=avg_nearest_dist,
                rho_ac_mohm_per_mm=rho_ac,
                feasible=bool(feasible),
            )
            all_curves.setdefault(key, []).append(point)

    # Sort each topology curve by VR count.
    for key in all_curves:
        all_curves[key].sort(key=lambda p: p.vr_count)

    return all_curves

def print_loss_breakdown_by_topology(curves):
    print("\n" + "=" * 120)
    print("LOSS BREAKDOWN BY TOPOLOGY AND VR COUNT")
    print("=" * 120)

    for key in sorted(curves.keys()):
        print(f"\nTopology {architecture_label(key)}")
        print("-" * 120)
        print(f"{'VR_count':>8} | {'I_out/VR (A)':>12} | {'VR loss total (W)':>16} | {'Routing loss (W)':>16} | {'System loss (W)':>15} | {'Eff (%)':>9} | {'f_sw (MHz)':>10}")
        print("-" * 120)

        for p in curves[key]:
            if p.feasible:
                print(
                    f"{p.vr_count:8d} | "
                    f"{p.i_out_per_vr_a:12.3f} | "
                    f"{p.conv_loss_total_w:16.6f} | "
                    f"{p.routing_loss_w:16.6f} | "
                    f"{p.total_loss_w:15.6f} | "
                    f"{p.efficiency_pct:9.4f} | "
                    f"{p.f_sw_opt_hz/1e6:10.4f}"
                )
            else:
                print(
                    f"{p.vr_count:8d} | "
                    f"{p.i_out_per_vr_a:12.3f} | "
                    f"{'infeasible':>16} | "
                    f"{'infeasible':>16} | "
                    f"{'infeasible':>15} | "
                    f"{'nan':>9} | "
                    f"{'nan':>10}"
                )
# ============================================================
# 3) Plotting
# ============================================================

def plot_efficiency_vs_vr_count_by_topology(
    curves: Dict[Tuple[int, int, int], List[TopologyPoint]],
    save_path: str,
    p_load_w: float = 1000.0,
    routing_arch: str = "A2",
    top_n: Optional[int] = None,
    min_valid_points: int = 2,
):
    plt.rcParams.update({
        "figure.facecolor": "#F8FAFC",
        "axes.facecolor": "#FFFFFF",
        "axes.edgecolor": "#E2E8F0",
        "axes.labelcolor": "#1E293B",
        "xtick.color": "#64748B",
        "ytick.color": "#64748B",
        "axes.grid": True,
        "grid.color": "#E2E8F0",
        "grid.linewidth": 0.6,
        "font.size": 11,
    })

    items = []
    for key, pts in curves.items():
        valid_effs = [p.efficiency_pct for p in pts if p.feasible and np.isfinite(p.efficiency_pct)]
        if len(valid_effs) >= min_valid_points:
            items.append((key, pts, max(valid_effs)))
    items.sort(key=lambda x: x[2], reverse=True)
    if top_n is not None:
        items = items[:top_n]

    fig, ax = plt.subplots(figsize=(12, 7))
    cmap = plt.get_cmap("tab20", max(len(items), 1))

    for idx, (key, pts, _) in enumerate(items):
        xs = [p.vr_count for p in pts if p.feasible and np.isfinite(p.efficiency_pct)]
        ys = [p.efficiency_pct for p in pts if p.feasible and np.isfinite(p.efficiency_pct)]
        if len(xs) < min_valid_points:
            continue
        ax.plot(xs, ys, marker="o", linewidth=2.0, markersize=4.5,
                color=cmap(idx), label=architecture_label(key))

    ax.set_xlabel("VR count", fontweight="bold")
    ax.set_ylabel("System efficiency (%)", fontweight="bold")
    ax.set_title(
        f"System efficiency vs VR count for each HVR topology\n"
        f"({p_load_w/1000:.1f} kW load, routing architecture {routing_arch})",
        fontweight="bold"
    )
    ax.legend(loc="best", fontsize=8, ncol=2)
    ax.set_xlim(left=0)
    fig.tight_layout()

    save_dir = os.path.dirname(save_path)
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)

    fig.savefig(save_path, dpi=220, facecolor="#F8FAFC")
    plt.close(fig)

def plot_system_loss_vs_vr_count_by_topology(
    curves,
    save_path,
    p_load_w=1000.0,
    routing_arch="A2",
    top_n=None,
    min_valid_points=2,
):
    plt.rcParams.update({
        "figure.facecolor": "#F8FAFC",
        "axes.facecolor": "#FFFFFF",
        "axes.edgecolor": "#E2E8F0",
        "axes.labelcolor": "#1E293B",
        "xtick.color": "#64748B",
        "ytick.color": "#64748B",
        "axes.grid": True,
        "grid.color": "#E2E8F0",
        "grid.linewidth": 0.6,
        "font.size": 11,
    })

    items = []
    for key, pts in curves.items():
        valid_losses = [p.total_loss_w for p in pts if p.feasible and np.isfinite(p.total_loss_w)]
        if len(valid_losses) >= min_valid_points:
            items.append((key, pts, min(valid_losses)))

    items.sort(key=lambda x: x[2])  # lower loss is better
    if top_n is not None:
        items = items[:top_n]

    fig, ax = plt.subplots(figsize=(12, 7))
    cmap = plt.get_cmap("tab20", max(len(items), 1))

    for idx, (key, pts, _) in enumerate(items):
        xs = [p.vr_count for p in pts if p.feasible and np.isfinite(p.total_loss_w)]
        ys = [p.total_loss_w for p in pts if p.feasible and np.isfinite(p.total_loss_w)]
        if len(xs) < min_valid_points:
            continue

        ax.plot(
            xs, ys,
            marker="o",
            linewidth=2.0,
            markersize=4.5,
            color=cmap(idx),
            label=architecture_label(key)
        )

        # mark minimum-loss point for this topology
        min_idx = int(np.argmin(ys))
        ax.scatter(xs[min_idx], ys[min_idx], color=cmap(idx), s=50, zorder=5)

    ax.set_xlabel("VR count", fontweight="bold")
    ax.set_ylabel("System loss (W)", fontweight="bold")
    ax.set_title(
        f"System loss vs VR count for each HVR topology\n"
        f"({p_load_w/1000:.1f} kW load, routing architecture {routing_arch})",
        fontweight="bold"
    )
    ax.legend(loc="best", fontsize=8, ncol=2)
    ax.set_xlim(left=0)

    fig.tight_layout()

    save_dir = os.path.dirname(save_path)
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)

    fig.savefig(save_path, dpi=220, facecolor="#F8FAFC")
    plt.close(fig)

def export_curve_table(curves: Dict[Tuple[int, int, int], List[TopologyPoint]], save_path: str):
    import csv

    save_dir = os.path.dirname(save_path)
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)

    with open(save_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "N", "K", "K_A", "VR_count", "I_out_per_vr_A",
            "conv_loss_per_vr_W", "conv_loss_total_W", "routing_loss_W",
            "total_loss_W", "efficiency_pct", "f_sw_opt_Hz",
            "W_H_opt", "W_L_opt", "area_mm2",
            "avg_nearest_dist_mm", "rho_ac_mohm_per_mm", "feasible"
        ])
        for key, pts in sorted(curves.items()):
            for p in pts:
                writer.writerow([
                    key[0], key[1], key[2], p.vr_count, p.i_out_per_vr_a,
                    p.conv_loss_per_vr_w, p.conv_loss_total_w, p.routing_loss_w,
                    p.total_loss_w, p.efficiency_pct, p.f_sw_opt_hz,
                    p.w_h_opt, p.w_l_opt, p.area_mm2,
                    p.avg_nearest_dist_mm, p.rho_ac_mohm_per_mm, p.feasible,
                ])


if __name__ == "__main__":
    vr_counts = [4, 8, 12, 16, 20, 24, 32, 48, 64, 80, 96, 120, 140]

    curves = sweep_efficiency_vs_vr_count(
        vr_counts=vr_counts,
        p_load_w=1000.0,
        v_out=1.0,
        v_in=48.0,
        i_target_density=2.5,
        target_component_count=15,
        routing_arch="A2",
        die_area_mm2=400.0,
        n_pol_segments=100,
        rho_mohm_per_mm=50,
        # Optional tighter sweeps:
        # w_h_values=np.geomspace(0.2, 20.0, 40),
        # w_l_values=np.geomspace(0.2, 20.0, 40),
        verbose=True,
    )
    print_loss_breakdown_by_topology(curves)

    plot_efficiency_vs_vr_count_by_topology(
        curves,
        save_path="hvr_efficiency_vs_vrcount_by_topology.png",
        p_load_w=1000.0,
        routing_arch="A2",
        top_n=None,
    )
    plot_system_loss_vs_vr_count_by_topology(
        curves,
        save_path="hvr_system_loss_vs_vrcount_by_topology.png",
        p_load_w=1000.0,
        routing_arch="A2",
        top_n=None,
    )
    export_curve_table(curves, "hvr_efficiency_vs_vrcount_by_topology.csv")
    print("Saved plot and CSV.")
