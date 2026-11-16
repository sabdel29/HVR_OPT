
#!/usr/bin/env python3
"""
HVR width-based switch sizing optimizer.

This module keeps the architecture generation and passive libraries from
HVR_FULL_OPT_EPC_V2, but replaces EPC GaN device enumeration with width
sweeps for high-side and low-side switches.

Key idea:
  - electrical parasitics scale linearly with width W
  - ON-resistance and gate resistance scale as 1/W
  - the optimizer sweeps W_H and W_L instead of picking discrete EPC parts
"""

import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Optional, List

from HVR_FULL_OPT_EPC_V2 import (
    VRArchitecture,
    Inductor,
    Capacitor,
    INDUCTOR_LIBRARY,
    CAPACITOR_LIBRARY,
    default_capacitor_library,
    generate_architectures,
    filter_candidate_inductors,
    filter_candidate_capacitors,
    _setup_style,
    _C,
)

# ------------------------------------------------------------
# Unit-width switch model parameters (provided by user)
# ------------------------------------------------------------

R_S_H_o = 3e-5
R_S_L_o = 6.9e-6
R_g_o = 6e-4

Q_gd_o = 1.083333333e-7
Q_g_o = 7.25e-7
C_G_HS_o = 8.16666667e-8
C_G_LS_o = 2e-7
C_OSS_HS_o = 5.5e-8
C_OSS_LS_o = 1.363636e-7


@dataclass
class SwitchSizing:
    part_number: str
    switch_type: str
    width_mm: float
    width_m: float
    R_DS_ON: float
    Q_G: float
    Q_GD: float
    C_G: float
    C_OSS: float
    R_g_int: float
    footprint_mm2: float


def make_switch(
    switch_type: str,
    width_mm: float,
    area_per_width_mm2: float = 1.0,
) -> SwitchSizing:
    """Create a width-scaled switch object.

    Public width inputs are interpreted in mm. The provided unit parameters
    are treated as *per-meter* quantities, so width is converted to meters
    for all electrical calculations. This keeps the optimizer interface in mm
    while avoiding a 1000x error in charges/capacitances and a 1/1000x error
    in resistances.
    """
    if width_mm <= 0:
        raise ValueError("width_mm must be > 0")

    width_m = width_mm * 1e-3

    if switch_type.upper() == "HS":
        return SwitchSizing(
            part_number=f"HS_W={width_mm:.4g}mm",
            switch_type="HS",
            width_mm=width_mm,
            width_m=width_m,
            R_DS_ON=R_S_H_o / width_m,
            Q_G=Q_g_o * width_m,
            Q_GD=Q_gd_o * width_m,
            C_G=C_G_HS_o * width_m,
            C_OSS=C_OSS_HS_o * width_m,
            R_g_int=R_g_o / width_m,
            footprint_mm2=area_per_width_mm2 * width_mm,
        )

    if switch_type.upper() == "LS":
        return SwitchSizing(
            part_number=f"LS_W={width_mm:.4g}mm",
            switch_type="LS",
            width_mm=width_mm,
            width_m=width_m,
            R_DS_ON=R_S_L_o / width_m,
            Q_G=0.0,
            Q_GD=0.0,
            C_G=C_G_LS_o * width_m,
            C_OSS=C_OSS_LS_o * width_m,
            R_g_int=0.0,
            footprint_mm2=area_per_width_mm2 * width_mm,
        )

    raise ValueError("switch_type must be 'HS' or 'LS'")


@dataclass
class LossResult:
    total_loss: float
    delta_i_out: float
    delta_v_out: float
    p_cond: float
    p_sw: float
    p_sw_hs: float
    p_sw_gd: float
    p_sw_coss: float
    coupling_boost: float


@dataclass
class LossModelInputs:
    hs_device: SwitchSizing
    ls_device: SwitchSizing
    inductor: Inductor
    capacitor: Capacitor
    I_out: float
    V_out: float
    V_in: float
    f_sw: float
    V_gs_drive: float


def compute_total_loss(arch: VRArchitecture, inp: LossModelInputs) -> LossResult:
    N, K, K_A, B_array, D = arch.N, arch.K, arch.K_A, arch.B_array, arch.D
    hs, ls = inp.hs_device, inp.ls_device
    I_out = inp.I_out
    L = inp.inductor.l_nh * 1e-9
    R_L_ESR = inp.inductor.r_dcr_mohm * 1e-3
    R_C_ESR = inp.capacitor.esr_mohm * 1e-3
    V_out, V_in, f_sw = inp.V_out, inp.V_in, inp.f_sw
    B_k = B_array[-1]

    coupling_boost = 1.0 + inp.inductor.coupling_k * max(K - 1, 0)
    delta_i_raw = (D / (f_sw * L)) * (V_in / N * K_A - V_out * K)
    delta_i_eff = delta_i_raw / coupling_boost

    I_out_rms = np.sqrt(I_out**2 + (delta_i_eff**2) / 12.0)
    C_out = inp.capacitor.c_uf * 1e-6
    delta_v_out = abs(delta_i_eff) / (8.0 * f_sw * C_out)

    # conduction loss (user-provided corrected model)
    B_sum = sum(b**2 for b in B_array)
    P_cond = (V_out / V_in) * (I_out_rms ** 2) * (
        hs.R_DS_ON
        + 2 * (1 - 1 / N) * R_C_ESR
        + ((V_in / (N ** 2 * V_out)) * (R_L_ESR + ls.R_DS_ON)
           + (2 * ls.R_DS_ON) / N) * B_sum
        - (4 * B_k - 1) * (ls.R_DS_ON / N)
    )

    # switching loss (user-provided corrected model)
    V_gs_drive = inp.V_gs_drive
    V_th = 1.0
    V_pl = 1.6
    R_drv = 0.7
    I_g = (V_gs_drive - 0.5 * (V_th + V_pl)) / (hs.R_g_int + R_drv)

    P_sw_HS = f_sw * (V_in / N - V_out) * I_out_rms * ((hs.Q_GD + hs.Q_G) / I_g)
    P_sw_GD = f_sw * (N * hs.C_G + K * ls.C_G) * V_gs_drive ** 2
    P_sw_COSS = (f_sw / 2.0) * (
        N * hs.C_OSS * ((V_in / N - V_out) ** 2) + K * ls.C_OSS * (V_out ** 2)
    )
    P_sw = P_sw_HS + P_sw_GD + P_sw_COSS

    return LossResult(
        total_loss=P_cond + P_sw,
        delta_i_out=delta_i_eff,
        delta_v_out=delta_v_out,
        p_cond=P_cond,
        p_sw=P_sw,
        p_sw_hs=P_sw_HS,
        p_sw_gd=P_sw_GD,
        p_sw_coss=P_sw_COSS,
        coupling_boost=coupling_boost,
    )


def _compute_area(
    arch: VRArchitecture,
    hs: SwitchSizing,
    ls: SwitchSizing,
    ind: Inductor,
    cap: Capacitor,
) -> float:
    """Vertical stacking model: total footprint is the max across layers."""
    return max(
        arch.N * hs.footprint_mm2,
        arch.K * ls.footprint_mm2,
        arch.K * ind.footprint_mm2,
        (arch.N - 1) * cap.footprint_mm2,
    )


@dataclass
class OptimizationResult:
    architecture: VRArchitecture
    default_loss: float
    optimized_hs_device: Optional[SwitchSizing] = None
    optimized_ls_device: Optional[SwitchSizing] = None
    optimized_inductor: Optional[Inductor] = None
    optimized_capacitor: Optional[Capacitor] = None
    optimized_f_sw: Optional[float] = None
    optimized_loss: float = float("inf")
    ripple_satisfied: bool = False
    total_area_mm2: float = np.nan
    area_budget_mm2: float = np.nan
    area_feasible: bool = False
    delta_i_out_opt: float = np.nan
    delta_v_out_opt: float = np.nan
    coupling_boost_opt: float = 1.0
    p_cond_opt: float = np.nan
    p_sw_opt: float = np.nan
    p_sw_hs_opt: float = np.nan
    p_sw_gd_opt: float = np.nan
    p_sw_coss_opt: float = np.nan
    optimized_w_h: float = np.nan
    optimized_w_l: float = np.nan


def optimize_architecture(
    arch: VRArchitecture,
    w_h_values: np.ndarray,
    w_l_values: np.ndarray,
    inductor_library,
    capacitor_library,
    f_sw_values: np.ndarray,
    default_w_h: float,
    default_w_l: float,
    default_inductor,
    default_capacitor,
    default_f_sw: float,
    I_out: float,
    V_out: float,
    V_in: float,
    V_gs_drive: float,
    ripple_factor: float = 0.4,
    v_ripple_frac: float = 0.25,
    area_budget_mm2: float = np.inf,
    hs_area_per_width_mm2: float = 1.0,
    ls_area_per_width_mm2: float = 1.0,
) -> OptimizationResult:
    default_hs = make_switch("HS", default_w_h, hs_area_per_width_mm2)
    default_ls = make_switch("LS", default_w_l, ls_area_per_width_mm2)

    default_lr = compute_total_loss(
        arch,
        LossModelInputs(
            hs_device=default_hs,
            ls_device=default_ls,
            inductor=default_inductor,
            capacitor=default_capacitor,
            I_out=I_out,
            V_out=V_out,
            V_in=V_in,
            f_sw=default_f_sw,
            V_gs_drive=V_gs_drive,
        ),
    )

    inds = filter_candidate_inductors(inductor_library, arch, I_out)
    caps = filter_candidate_capacitors(capacitor_library, arch, V_in)

    base = OptimizationResult(
        architecture=arch,
        default_loss=default_lr.total_loss,
        area_budget_mm2=area_budget_mm2,
    )
    if len(w_h_values) == 0 or len(w_l_values) == 0 or not inds or not caps:
        return base

    best_loss = float("inf")
    best_hs = best_ls = best_ind = best_cap = best_fsw = None
    best_delta_i = best_delta_v = np.nan
    best_boost = 1.0
    best_p_cond = best_p_sw = best_p_sw_hs = best_p_sw_gd = best_p_sw_coss = np.nan
    any_ripple = False

    v_ripple_limit = v_ripple_frac * V_out
    i_ripple_limit = ripple_factor * I_out

    for w_h in w_h_values:
        hs = make_switch("HS", float(w_h), hs_area_per_width_mm2)
        for w_l in w_l_values:
            ls = make_switch("LS", float(w_l), ls_area_per_width_mm2)
            for ind in inds:
                f_valid = f_sw_values[f_sw_values <= ind.f_max_mhz * 1e6]
                if len(f_valid) == 0:
                    continue
                for cap in caps:
                    area = _compute_area(arch, hs, ls, ind, cap)
                    if area > area_budget_mm2:
                        continue
                    for f_sw in f_valid:
                        lr = compute_total_loss(
                            arch,
                            LossModelInputs(
                                hs_device=hs,
                                ls_device=ls,
                                inductor=ind,
                                capacitor=cap,
                                I_out=I_out,
                                V_out=V_out,
                                V_in=V_in,
                                f_sw=float(f_sw),
                                V_gs_drive=V_gs_drive,
                            ),
                        )

                        if abs(lr.delta_i_out) >= i_ripple_limit:
                            continue
                        if lr.delta_v_out >= v_ripple_limit:
                            continue
                        any_ripple = True

                        if lr.total_loss < best_loss:
                            best_loss = lr.total_loss
                            best_hs, best_ls = hs, ls
                            best_ind, best_cap = ind, cap
                            best_fsw = float(f_sw)
                            best_delta_i = lr.delta_i_out
                            best_delta_v = lr.delta_v_out
                            best_boost = lr.coupling_boost
                            best_p_cond = lr.p_cond
                            best_p_sw = lr.p_sw
                            best_p_sw_hs = lr.p_sw_hs
                            best_p_sw_gd = lr.p_sw_gd
                            best_p_sw_coss = lr.p_sw_coss

    if best_hs is None:
        return base

    area_opt = _compute_area(arch, best_hs, best_ls, best_ind, best_cap)
    return OptimizationResult(
        architecture=arch,
        default_loss=default_lr.total_loss,
        optimized_hs_device=best_hs,
        optimized_ls_device=best_ls,
        optimized_inductor=best_ind,
        optimized_capacitor=best_cap,
        optimized_f_sw=best_fsw,
        optimized_loss=best_loss,
        ripple_satisfied=any_ripple,
        total_area_mm2=area_opt,
        area_budget_mm2=area_budget_mm2,
        area_feasible=(area_opt <= area_budget_mm2),
        delta_i_out_opt=best_delta_i,
        delta_v_out_opt=best_delta_v,
        coupling_boost_opt=best_boost,
        p_cond_opt=best_p_cond,
        p_sw_opt=best_p_sw,
        p_sw_hs_opt=best_p_sw_hs,
        p_sw_gd_opt=best_p_sw_gd,
        p_sw_coss_opt=best_p_sw_coss,
        optimized_w_h=best_hs.width_mm,
        optimized_w_l=best_ls.width_mm,
    )


def optimize_all_architectures(
    architectures,
    w_h_values,
    w_l_values,
    inductor_library,
    capacitor_library,
    f_sw_values,
    default_w_h,
    default_w_l,
    default_inductor,
    default_capacitor,
    default_f_sw,
    I_out,
    V_out,
    V_in,
    V_gs_drive,
    ripple_factor=0.4,
    v_ripple_frac=0.25,
    area_budget_mm2=np.inf,
    hs_area_per_width_mm2=1.0,
    ls_area_per_width_mm2=1.0,
    verbose=True,
):
    results = []
    for idx, arch in enumerate(architectures, 1):
        if verbose:
            inds = filter_candidate_inductors(inductor_library, arch, I_out)
            caps = filter_candidate_capacitors(capacitor_library, arch, V_in)
            print(f"\nOptimising arch {idx}/{len(architectures)}: "
                  f"N={arch.N}, K={arch.K}, K_A={arch.K_A}")
            print(f"  HS width sweep: {len(w_h_values)} candidates")
            print(f"  LS width sweep: {len(w_l_values)} candidates")
            print(f"  Isat≥{max(arch.B_array) * I_out / arch.N:.1f}A | inds:{len(inds)}")
            print(f"  Cap V_max>{V_in / arch.N:.1f}V | caps:{len(caps)}")
            print(f"  Area budget: {area_budget_mm2:.1f} mm²")

        res = optimize_architecture(
            arch=arch,
            w_h_values=w_h_values,
            w_l_values=w_l_values,
            inductor_library=inductor_library,
            capacitor_library=capacitor_library,
            f_sw_values=f_sw_values,
            default_w_h=default_w_h,
            default_w_l=default_w_l,
            default_inductor=default_inductor,
            default_capacitor=default_capacitor,
            default_f_sw=default_f_sw,
            I_out=I_out,
            V_out=V_out,
            V_in=V_in,
            V_gs_drive=V_gs_drive,
            ripple_factor=ripple_factor,
            v_ripple_frac=v_ripple_frac,
            area_budget_mm2=area_budget_mm2,
            hs_area_per_width_mm2=hs_area_per_width_mm2,
            ls_area_per_width_mm2=ls_area_per_width_mm2,
        )
        results.append(res)
    return results


def print_optimization_results(
    results,
    V_out=1.0,
    I_out=20.0,
    v_ripple_frac=0.25,
    ripple_factor=0.4,
):
    print("\n" + "=" * 78)
    print("HVR OPTIMISATION RESULTS (WIDTH-BASED SWITCH SIZING)")
    print("=" * 78)
    for res in results:
        arch = res.architecture
        print(f"\nArch (N={arch.N}, K={arch.K}, K_A={arch.K_A}) "
              f"| comps={arch.component_count} | B={arch.B_array}")
        print(f"  Default loss : {res.default_loss:.4f} W")
        if res.optimized_hs_device is None:
            print("  → No feasible combination (constraints too tight)")
            continue
        ind = res.optimized_inductor
        cap = res.optimized_capacitor
        print(f"  W_H,opt      : {res.optimized_w_h:.6g}")
        print(f"  W_L,opt      : {res.optimized_w_l:.6g}")
        print(f"  Inductor     : {ind.name} "
              f"({ind.l_nh:.0f} nH, R_DCR={ind.r_dcr_mohm:.2f} mΩ, "
              f"Isat={ind.i_sat_a:.1f} A, k_c={ind.coupling_k:.2f})")
        print(f"  Capacitor    : {cap.name} "
              f"({cap.c_uf:.3g} µF, ESR={cap.esr_mohm:.1f} mΩ, "
              f"Vmax={cap.v_max:.1f} V)")
        print(f"  f_sw         : {res.optimized_f_sw / 1e6:.3f} MHz")
        print(f"  Loss         : {res.optimized_loss:.4f} W")
        print(f"    P_cond     : {res.p_cond_opt:.4f} W  "
              f"({100 * res.p_cond_opt / res.optimized_loss:.1f}%)")
        print(f"    P_sw       : {res.p_sw_opt:.4f} W  "
              f"({100 * res.p_sw_opt / res.optimized_loss:.1f}%)")
        print(f"      P_sw_HS  : {res.p_sw_hs_opt:.4f} W")
        print(f"      P_sw_GD  : {res.p_sw_gd_opt:.4f} W")
        print(f"      P_sw_COSS: {res.p_sw_coss_opt:.4f} W")
        print(f"  ΔI_out       : {res.delta_i_out_opt:.3f} A "
              f"(limit {ripple_factor * I_out:.1f} A) "
              f"{'✓' if abs(res.delta_i_out_opt) < ripple_factor * I_out else '✗'}")
        print(f"  ΔV_out       : {res.delta_v_out_opt * 1e3:.2f} mV "
              f"(limit {v_ripple_frac * V_out * 1e3:.0f} mV) "
              f"{'✓' if res.delta_v_out_opt < v_ripple_frac * V_out else '✗'}")
        print(f"  Coupling K   : {res.coupling_boost_opt:.2f}× ripple reduction")
        print(f"  Area         : {res.total_area_mm2:.2f} mm² "
              f"(budget {res.area_budget_mm2:.1f} mm²) "
              f"{'✓' if res.area_feasible else '✗'}")


def plot_default_vs_optimized(results, save_path=None):
    _setup_style()
    valid = [r for r in results if np.isfinite(r.optimized_loss)]
    if not valid:
        print("No valid results to plot.")
        return
    labels = [f"(N={r.architecture.N},K={r.architecture.K})\n"
              f"#{r.architecture.component_count}" for r in valid]
    fig, ax = plt.subplots(figsize=(max(10, len(valid) * 1.4), 6))
    x = range(len(valid))
    ax.plot(x, [r.default_loss for r in valid], 'ro-', label='Default loss', lw=2)
    ax.plot(x, [r.optimized_loss for r in valid], 'bs-', label='Optimised loss', lw=2)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=45, ha='right')
    ax.set_xlabel('Architecture (N, K, K_A) / Component Count')
    ax.set_ylabel('Loss (W)')
    ax.set_title('HVR — Default vs Optimised Loss\n(width-based HS/LS sizing)')
    ax.legend()
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor=_C['bg'])
    plt.close()


def plot_constraint_overview(results, V_out=1.0, I_out=20.0,
                             v_ripple_frac=0.25, ripple_factor=0.4,
                             save_path=None):
    _setup_style()
    valid = [r for r in results if r.optimized_hs_device is not None]
    if not valid:
        print("No feasible results for constraint overview.")
        return

    labels = [f"N={r.architecture.N}\nK={r.architecture.K}" for r in valid]
    x = np.arange(len(valid))

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    fig.suptitle('HVR — Constraint Satisfaction Overview\n'
                 '(width-based HS/LS sizing)',
                 fontweight='bold', fontsize=12)

    ax = axes[0, 0]
    bars = ax.bar(x, [r.optimized_loss for r in valid], color=_C['teal'], alpha=0.85)
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                f'{bar.get_height():.2f}W', ha='center', va='bottom', fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel('Optimised loss (W)'); ax.set_title('Conversion loss')

    ax = axes[0, 1]
    util = [r.total_area_mm2 / r.area_budget_mm2 if np.isfinite(r.area_budget_mm2)
            else np.nan for r in valid]
    colors = [_C['green'] if u <= 1.0 else _C['red'] for u in util]
    ax.bar(x, util, color=colors, alpha=0.85)
    ax.axhline(1.0, color=_C['red'], ls='--', lw=1.5, label='Budget limit')
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel('Area / budget'); ax.set_title('Area utilisation')
    ax.legend(fontsize=8)

    ax = axes[1, 0]
    i_util = [abs(r.delta_i_out_opt) / (ripple_factor * I_out) for r in valid]
    colors = [_C['green'] if u < 1.0 else _C['red'] for u in i_util]
    ax.bar(x, i_util, color=colors, alpha=0.85)
    ax.axhline(1.0, color=_C['red'], ls='--', lw=1.5, label='50% I_out limit')
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel('|ΔI_out| / limit'); ax.set_title('Current ripple utilisation')
    ax.legend(fontsize=8)
    for xi, val in zip(x, i_util):
        ax.text(xi, val + 0.02, 'k×1.0', ha='center', fontsize=7, color=_C['purple'])

    ax = axes[1, 1]
    v_util = [r.delta_v_out_opt / (v_ripple_frac * V_out) for r in valid]
    colors = [_C['green'] if u < 1.0 else _C['red'] for u in v_util]
    ax.bar(x, v_util, color=colors, alpha=0.85)
    ax.axhline(1.0, color=_C['red'], ls='--', lw=1.5, label='25% V_out limit')
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel('ΔV_out / limit'); ax.set_title('Voltage ripple utilisation')
    ax.legend(fontsize=8)

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor=_C['bg'])
    plt.close()


def plot_pareto_loss_vs_area(results, save_path=None):
    _setup_style()
    valid = [r for r in results if r.optimized_hs_device is not None]
    if not valid:
        return

    fig, ax = plt.subplots(figsize=(9, 6))
    N_vals = sorted(set(r.architecture.N for r in valid))
    cmap = plt.get_cmap('tab10', len(N_vals))
    for color_idx, N in enumerate(N_vals):
        pts = [r for r in valid if r.architecture.N == N]
        xs = [r.total_area_mm2 for r in pts]
        ys = [r.optimized_loss for r in pts]
        ax.scatter(xs, ys, color=cmap(color_idx), s=80, zorder=3, label=f'N={N}')
        for r in pts:
            ax.annotate(f"K={r.architecture.K}",
                        (r.total_area_mm2, r.optimized_loss),
                        textcoords='offset points', xytext=(5, 3), fontsize=7,
                        color=_C['muted'])

    budgets = [r.area_budget_mm2 for r in valid if np.isfinite(r.area_budget_mm2)]
    if budgets:
        ax.axvline(budgets[0], color=_C['red'], ls='--', lw=1.5,
                   label=f'Area budget ({budgets[0]:.0f} mm²)')

    ax.set_xlabel('Total component area (mm²)', fontweight='bold')
    ax.set_ylabel('Optimised conversion loss (W)', fontweight='bold')
    ax.set_title('HVR — Loss vs Area Pareto Front\n(width-based HS/LS sizing)',
                 fontweight='bold')
    ax.legend(fontsize=9, loc='upper right')
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor=_C['bg'])
    plt.close()


def run_hvr_optimization(
    hs_weight: int = 1,
    ls_weight: int = 1,
    inductor_weight: int = 1,
    capacitor_weight: int = 1,
    target_component_count: int = 15,
    V_in: float = 48.0,
    V_out: float = 1.0,
    I_out: float = 20.0,
    V_gs_drive: float = 5.0,
    ripple_factor: float = 0.4,
    v_ripple_frac: float = 0.25,
    I_target_density: float = 2.0,
    f_sw_values: Optional[np.ndarray] = None,
    w_h_values: Optional[np.ndarray] = None,
    w_l_values: Optional[np.ndarray] = None,
    default_w_h: float = 1.0,
    default_w_l: float = 1.0,
    hs_area_per_width_mm2: float = 1.0,
    ls_area_per_width_mm2: float = 1.0,
    inductor_library: Optional[List[Inductor]] = None,
    capacitor_library: Optional[List[Capacitor]] = None,
    verbose: bool = True,
) -> List[OptimizationResult]:
    """Full HVR optimization with continuous HS/LS sizing sweeps.

    Width arrays are interpreted in mm. Internally the electrical model
    converts mm to meters before applying the user-provided per-unit values.
    Area per width remains configurable in mm^2/mm.
    """
    if f_sw_values is None:
        f_sw_values = np.logspace(np.log10(0.043e6), np.log10(200e6), 50)
    if w_h_values is None:
        w_h_values = np.geomspace(0.2, 20.0, 60)
    if w_l_values is None:
        w_l_values = np.geomspace(0.2, 20.0, 60)
    if inductor_library is None:
        inductor_library = INDUCTOR_LIBRARY
    if capacitor_library is None:
        capacitor_library = default_capacitor_library()

    area_budget = I_out / I_target_density
    architectures = generate_architectures(
        hs_weight,
        ls_weight,
        inductor_weight,
        capacitor_weight,
        target_component_count,
        V_out,
        V_in,
    )

    if verbose:
        print(f"Generated {len(architectures)} architectures")
        print(f"Area budget: {area_budget:.1f} mm²  "
              f"(I_out={I_out} A / density={I_target_density} A/mm²)")
        print(f"HS width sweep: {len(w_h_values)} points "
              f"[{float(np.min(w_h_values)):.4g}, {float(np.max(w_h_values)):.4g}] mm")
        print(f"LS width sweep: {len(w_l_values)} points "
              f"[{float(np.min(w_l_values)):.4g}, {float(np.max(w_l_values)):.4g}] mm")

    first_arch = architectures[0] if architectures else None
    default_ind = (filter_candidate_inductors(inductor_library, first_arch, I_out)
                   or inductor_library)[0]
    default_cap = (filter_candidate_capacitors(capacitor_library, first_arch, V_in)
                   or capacitor_library)[0]

    results = optimize_all_architectures(
        architectures=architectures,
        w_h_values=np.asarray(w_h_values, dtype=float),
        w_l_values=np.asarray(w_l_values, dtype=float),
        inductor_library=inductor_library,
        capacitor_library=capacitor_library,
        f_sw_values=np.asarray(f_sw_values, dtype=float),
        default_w_h=default_w_h,
        default_w_l=default_w_l,
        default_inductor=default_ind,
        default_capacitor=default_cap,
        default_f_sw=500e3,
        I_out=I_out,
        V_out=V_out,
        V_in=V_in,
        V_gs_drive=V_gs_drive,
        ripple_factor=ripple_factor,
        v_ripple_frac=v_ripple_frac,
        area_budget_mm2=area_budget,
        hs_area_per_width_mm2=hs_area_per_width_mm2,
        ls_area_per_width_mm2=ls_area_per_width_mm2,
        verbose=verbose,
    )
    results.sort(key=lambda r: r.optimized_loss)
    return results


if __name__ == "__main__":
    results = run_hvr_optimization(
        target_component_count=15,
        V_in=48.0,
        V_out=1.0,
        I_out=32.0,
        V_gs_drive=5.0,
        ripple_factor=0.4,
        v_ripple_frac=0.25,
        I_target_density=1.5,
        verbose=True,
    )
    print_optimization_results(results, V_out=1.0, I_out=32.0,
                               v_ripple_frac=0.25, ripple_factor=0.4)
    plot_default_vs_optimized(results, save_path="hvr_width_fig1_loss_comparison.png")
    plot_constraint_overview(results, V_out=1.0, I_out=32.0,
                             v_ripple_frac=0.25, ripple_factor=0.4,
                             save_path="hvr_width_fig2_constraints.png")
    plot_pareto_loss_vs_area(results, save_path="hvr_width_fig3_pareto.png")
    print("\nDone.")
