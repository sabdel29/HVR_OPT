"""
Design Space Exploration for two packaging scenarios:
  Case 1: Planar (no stacking)     — area = sum of all component footprints ≤ 20 mm²
  Case 2: Vertical stacking        — area = footprint of largest component layer ≤ 20 mm²
 
System: 48V → 1V, I_out = 20 A, target J = 1 A/mm²
Ripple: ΔI < 40% × I_out,  ΔV < 5% × V_out  (C_out = 100 µF assumed)
"""
 
import sys, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from matplotlib.patches import FancyBboxPatch
from dataclasses import dataclass
from typing import Optional
 
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from HVR_FULL_OPT_EPC import (
    VRArchitecture, EPCDevice, LossModelInputs,
    compute_total_loss, generate_B_array, generate_architectures,
    load_epc_devices, filter_candidate_devices_for_architecture,
)
 
# ═══════════════════════════════════════════════════════════════════════════════
# 0.  SYSTEM PARAMETERS
# ═══════════════════════════════════════════════════════════════════════════════
V_IN        = 48.0
V_OUT       = 1.0
I_OUT       = 20.0
V_GS_DRIVE  = 5.0
C_OUT       = 100e-6      # F — output capacitor (assumed)
AREA_BUDGET = 20.0        # mm²  → J_target = 20/20 = 1 A/mm²
 
RI_MAX = 0.40 * I_OUT     # A   — max current ripple (40%)
RV_MAX = 0.05 * V_OUT     # V   — max voltage ripple (5%)
 
L_VALUES    = [440e-9, 220e-9, 100e-9, 47e-9, 22e-9]          # inductor sweep
F_SW_VALUES = np.logspace(np.log10(200e3), np.log10(10e6), 60) # 200kHz – 10MHz
 
# ═══════════════════════════════════════════════════════════════════════════════
# 1.  FOOTPRINT MODELS
# ═══════════════════════════════════════════════════════════════════════════════
EPC_FP = {
    'EPC2040': 0.90, 'EPC2045': 0.90, 'EPC2065': 0.90, 'EPC2101': 0.90,
    'EPC2108': 0.90, 'EPC2204': 0.90, 'EPC2302': 0.90, 'EPC2361': 0.90,
    'EPC2012': 1.44, 'EPC2015': 1.44, 'EPC2019': 1.44, 'EPC2023': 1.44,
    'EPC2047': 1.44, 'EPC2066': 1.44, 'EPC2100': 1.44, 'EPC2200': 1.44,
    'EPC2207': 1.44, 'EPC2218': 1.44, 'EPC2306': 1.44, 'EPC2362': 1.44,
    'EPC2366': 1.44,
    'EPC2007C': 1.96, 'EPC2016C': 1.96, 'EPC2033': 1.96, 'EPC2034': 1.96,
    'EPC2014C': 2.10, 'EPC2024': 2.10, 'EPC2036': 2.10, 'EPC2038': 2.10,
    'EPC2056': 2.10, 'EPC2214': 2.10, 'EPC2363': 2.10,
    'EPC2010': 3.63, 'EPC2029': 3.63, 'EPC2052': 3.63, 'EPC2111': 3.63,
    'EPC2152': 3.63, 'EPC2162': 3.63, 'EPC2216': 3.63, 'EPC2308': 3.63,
    'EPC2364': 3.63, 'EPC2367': 3.63,
    'EPC2021': 3.64, 'EPC2057': 3.64,
    'EPC2001C': 6.63, 'EPC2020': 6.63, 'EPC2050': 6.63,
    'EPC2055': 6.63, 'EPC2212': 6.63,
}
DEF_FP  = 1.44   # fallback for unlisted parts
CAP_FP  = 0.50   # mm² per flying capacitor (0603 ceramic)
 
def dev_fp(pn):
    return EPC_FP.get(pn, DEF_FP)
 
def ind_fp(L):
    """Embedded inductor footprint: 3.0 mm² per 100 nH (integrated magnetics model)."""
    return 3.0 * (L / 100e-9)
 
def area_planar(arch, hs_pn, ls_pn, L):
    """Case 1: total area = sum of all component footprints."""
    return (arch.N * dev_fp(hs_pn)
            + arch.K * dev_fp(ls_pn)
            + arch.K * ind_fp(L)
            + (arch.N - 1) * CAP_FP)
 
def area_stacked(arch, hs_pn, ls_pn, L):
    """Case 2: area = footprint of widest component layer (vertical stacking)."""
    layers = [
        arch.N * dev_fp(hs_pn),           # HS switch layer
        arch.K * dev_fp(ls_pn),           # LS switch layer
        arch.K * ind_fp(L),               # Inductor layer (usually dominant)
        max((arch.N - 1) * CAP_FP, 0.01), # Flying cap layer
    ]
    return max(layers)
 
# ═══════════════════════════════════════════════════════════════════════════════
# 2.  ARCHITECTURE GENERATION & DEVICE LOADING
# ═══════════════════════════════════════════════════════════════════════════════
architectures = generate_architectures(
    hs_weight=1, ls_weight=1, inductor_weight=1, capacitor_weight=1,
    target_component_count=20, V_out=V_OUT, V_in=V_IN,
)
df_dev = load_epc_devices('EPC-Product-Table.csv', V_gs_op=V_GS_DRIVE)
 
print(f"Generated {len(architectures)} architectures to evaluate")
 
# ═══════════════════════════════════════════════════════════════════════════════
# 3.  DSE CORE — find best design per topology per area model
# ═══════════════════════════════════════════════════════════════════════════════
@dataclass
class DSEResult:
    arch:       object
    hs:         str
    ls:         str
    L:          float
    f_sw:       float
    area:       float
    loss:       float
    p_cond:     float   # conduction loss fraction
    eff:        float
    di_pct:     float   # ΔI / I_out × 100
    dv_pct:     float   # ΔV / V_out × 100
    feasible:   bool
    reason:     str     # why infeasible (if applicable)
 
def run_dse_arch(arch, area_fn, area_budget):
    N, K, KA, D = arch.N, arch.K, arch.K_A, arch.D
    hs_c, ls_c = filter_candidate_devices_for_architecture(
        df_dev, arch, V_IN, V_OUT, V_GS_DRIVE, I_OUT)
 
    if not hs_c or not ls_c:
        return DSEResult(
            arch=arch, hs='—', ls='—', L=0, f_sw=0,
            area=0, loss=0, p_cond=0, eff=0,
            di_pct=0, dv_pct=0,
            feasible=False, reason='No qualified devices')
 
    best = None
    bl   = float('inf')
    any_area_ok   = False
    any_ripple_ok = False
 
    for hs in hs_c:
        for ls in ls_c:
            for L in L_VALUES:
                a = area_fn(arch, hs.part_number, ls.part_number, L)
                if a > area_budget:
                    continue
                any_area_ok = True
 
                for f in F_SW_VALUES:
                    di = abs(D / (f * L) * ((V_IN / N) * KA - V_OUT * K))
                    if di > RI_MAX:
                        continue
                    dv = di / (8 * f * C_OUT)
                    if dv > RV_MAX:
                        continue
                    any_ripple_ok = True
 
                    inp  = LossModelInputs(hs, ls, I_OUT, L, V_OUT, V_IN, f, V_GS_DRIVE)
                    loss = compute_total_loss(arch, inp)
                    eff  = V_OUT * I_OUT / (V_OUT * I_OUT + loss) * 100
 
                    if loss < bl:
                        bl = loss
                        # Estimate conduction fraction from duty-cycle scaling
                        from HVR_FULL_OPT_EPC import compute_total_loss as ctl
                        best = DSEResult(
                            arch=arch,
                            hs=hs.part_number, ls=ls.part_number,
                            L=L, f_sw=f, area=a,
                            loss=loss,
                            p_cond=0.0,   # filled below
                            eff=eff,
                            di_pct=di / I_OUT * 100,
                            dv_pct=dv / V_OUT * 100,
                            feasible=True, reason='',
                        )
 
    if best is None:
        reason = ('Area > budget' if not any_area_ok
                  else 'Ripple constraints unmet')
        return DSEResult(
            arch=arch, hs='—', ls='—', L=0, f_sw=0,
            area=0, loss=0, p_cond=0, eff=0,
            di_pct=0, dv_pct=0,
            feasible=False, reason=reason)
 
    return best
 
 
def run_dse(area_fn, area_budget, label):
    print(f"\n{'='*62}")
    print(f"  {label}")
    print(f"  Area budget: {area_budget} mm²  |  J_target: "
          f"{I_OUT/area_budget:.1f} A/mm²")
    print(f"{'='*62}")
    results = []
    for arch in architectures:
        r = run_dse_arch(arch, area_fn, area_budget)
        results.append(r)
        status = f"eff={r.eff:.2f}%  loss={r.loss:.3f}W  area={r.area:.1f}mm²  " \
                 f"DI={r.di_pct:.1f}%  DV={r.dv_pct:.2f}%  " \
                 f"HS={r.hs}  LS={r.ls}  L={r.L*1e9:.0f}nH  f={r.f_sw/1e6:.2f}MHz" \
                 if r.feasible else f"INFEASIBLE ({r.reason})"
        print(f"  N={arch.N},K={arch.K}: {status}")
    feasible = [r for r in results if r.feasible]
    if feasible:
        best = max(feasible, key=lambda r: r.eff)
        print(f"\n  BEST: N={best.arch.N},K={best.arch.K}  "
              f"eff={best.eff:.2f}%  area={best.area:.1f}mm²  "
              f"HS={best.hs}/LS={best.ls}  f={best.f_sw/1e6:.2f}MHz")
    return results
 
 
results1 = run_dse(area_planar,  AREA_BUDGET, "Case 1: Planar (No Stacking)")
results2 = run_dse(area_stacked, AREA_BUDGET, "Case 2: Vertical Stacking")
 
# ═══════════════════════════════════════════════════════════════════════════════
# 4.  FIGURE GENERATION
# ═══════════════════════════════════════════════════════════════════════════════
COLORS = {
    'bg':       '#F0F4F8',
    'panel':    '#FFFFFF',
    'text':     '#1E293B',
    'muted':    '#64748B',
    'grid':     '#CBD5E1',
    'infeas':   '#E2E8F0',
    'infeas_t': '#94A3B8',
    'accent':   '#2563EB',
    'green':    '#10B981',
    'orange':   '#F59E0B',
    'red':      '#EF4444',
    'ripple_i': '#3B82F6',
    'ripple_v': '#8B5CF6',
    'best':     '#F59E0B',
}
 
EFF_NORM = mcolors.Normalize(vmin=80, vmax=100)
EFF_MIN  = 80   # x-axis start for efficiency panel
EFF_CMAP = matplotlib.colormaps['RdYlGn']
 
def eff_color(eff):
    return EFF_CMAP(EFF_NORM(eff))
 
 
def plot_case(ax_main, ax_ripple, results, case_title, case_subtitle):
    """Draw one DSE case as two side-by-side panels."""
 
    # Sort: feasible first (by efficiency desc), then infeasible
    feasible   = sorted([r for r in results if r.feasible],
                        key=lambda r: r.eff, reverse=True)
    infeasible = [r for r in results if not r.feasible]
    ordered    = feasible + infeasible
 
    if not ordered:
        return
 
    labels     = [f"N={r.arch.N}, K={r.arch.K}" for r in ordered]
    n          = len(ordered)
    y_pos      = np.arange(n)
    bar_h      = 0.62
    best_eff   = feasible[0].eff if feasible else 0
 
    # ── Main panel: efficiency bars ───────────────────────────────────────────
    ax_main.set_facecolor(COLORS['panel'])
    ax_main.set_xlim(EFF_MIN, 101)
    ax_main.set_ylim(-0.7, n - 0.3)
    ax_main.grid(axis='x', color=COLORS['grid'], linewidth=0.7, zorder=0)
    ax_main.spines['top'].set_visible(False)
    ax_main.spines['right'].set_visible(False)
 
    for i, r in enumerate(ordered):
        yi = n - 1 - i   # bottom-to-top ordering
 
        if r.feasible:
            col = eff_color(r.eff)
            # Efficiency bar
            bar = ax_main.barh(yi, r.eff - EFF_MIN, left=EFF_MIN, height=bar_h,
                               color=col, edgecolor='white', linewidth=0.5,
                               zorder=3)
            # Efficiency label on bar
            ax_main.text(r.eff + 0.15, yi,
                         f'{r.eff:.1f}%',
                         va='center', ha='left', fontsize=8.5,
                         fontweight='bold',
                         color=COLORS['text'], zorder=5)
            # Loss inside bar
            ax_main.text(EFF_MIN + 0.5, yi,
                         f'{r.loss:.2f} W',
                         va='center', ha='left', fontsize=7.5,
                         color='white', fontweight='bold', zorder=5)
            # Star for best
            if r.eff == best_eff:
                ax_main.text(EFF_MIN - 0.4, yi, '★',
                             va='center', ha='center', fontsize=11,
                             color=COLORS['best'], zorder=6)
        else:
            # Grey bar for infeasible
            ax_main.barh(yi, 2.5, left=EFF_MIN, height=bar_h,
                         color=COLORS['infeas'],
                         edgecolor=COLORS['infeas_t'],
                         linewidth=0.8, zorder=3,
                         hatch='////')
            ax_main.text(EFF_MIN + 1.2, yi,
                         r.reason,
                         va='center', ha='left', fontsize=7.5,
                         color=COLORS['infeas_t'], style='italic', zorder=5)
 
    ax_main.set_yticks(np.arange(n))
    ax_main.set_yticklabels(list(reversed(labels)),
                            fontsize=9, fontweight='bold')
    ax_main.set_xlabel('Efficiency (%)', fontsize=10, fontweight='bold',
                       labelpad=6)
    ax_main.set_title(case_title, fontsize=11, fontweight='bold', pad=10,
                      color=COLORS['text'])
    ax_main.text(0.5, 1.02, case_subtitle,
                 transform=ax_main.transAxes,
                 ha='center', va='bottom', fontsize=8.5,
                 color=COLORS['muted'], style='italic')
    ax_main.tick_params(axis='x', labelsize=8.5)
    ax_main.tick_params(axis='y', labelsize=9)
 
    # ── Ripple panel — both series normalised to their constraint limit ────────
    # x-axis = % of budget consumed (100% = at the constraint boundary)
    # ΔI util = (ΔI / ΔI_max) × 100,   ΔV util = (ΔV / ΔV_max) × 100
    ax_ripple.set_facecolor(COLORS['panel'])
    ax_ripple.set_xlim(0, 115)
    ax_ripple.set_ylim(-0.7, n - 0.3)
    ax_ripple.grid(axis='x', color=COLORS['grid'], linewidth=0.7, zorder=0)
    ax_ripple.spines['top'].set_visible(False)
    ax_ripple.spines['right'].set_visible(False)
    ax_ripple.set_yticks([])
 
    DI_LIMIT_PCT = 40.0   # % of I_out
    DV_LIMIT_PCT = 5.0    # % of V_out
 
    for i, r in enumerate(ordered):
        yi = n - 1 - i
        if not r.feasible:
            continue
        # Normalised utilisation (0–100 = 0–limit, >100 = over budget)
        di_util = (r.di_pct / DI_LIMIT_PCT) * 100   # % of ΔI budget
        dv_util = (r.dv_pct / DV_LIMIT_PCT) * 100   # % of ΔV budget
 
        # Current ripple bar (blue)
        ax_ripple.barh(yi + 0.16, di_util, height=bar_h * 0.42,
                       color=COLORS['ripple_i'], alpha=0.85,
                       edgecolor='white', linewidth=0.4, zorder=3)
        ax_ripple.text(min(di_util + 1.5, 112), yi + 0.16,
                       f'ΔI={r.di_pct:.1f}%',
                       va='center', ha='left', fontsize=7.5,
                       color=COLORS['ripple_i'], fontweight='bold')
        # Voltage ripple bar (purple)
        ax_ripple.barh(yi - 0.16, dv_util, height=bar_h * 0.42,
                       color=COLORS['ripple_v'], alpha=0.85,
                       edgecolor='white', linewidth=0.4, zorder=3)
        ax_ripple.text(min(dv_util + 1.5, 112), yi - 0.16,
                       f'ΔV={r.dv_pct:.2f}%',
                       va='center', ha='left', fontsize=7.5,
                       color=COLORS['ripple_v'], fontweight='bold')
 
    # Single constraint line at 100% (= at the limit for both series)
    ax_ripple.axvline(100, color=COLORS['red'],
                      linewidth=2.0, linestyle='--', alpha=0.9, zorder=5)
    ax_ripple.text(101, n - 0.55, 'Limit',
                   va='top', ha='left', fontsize=7.5,
                   color=COLORS['red'], fontweight='bold')
 
    ax_ripple.set_xlabel('Ripple Budget Used (%)', fontsize=10,
                         fontweight='bold', labelpad=6)
    ax_ripple.set_title('Ripple Constraint Utilisation\n'
                        '(100% = at limit)',
                        fontsize=10, fontweight='bold', pad=10,
                        color=COLORS['text'])
    ax_ripple.tick_params(axis='x', labelsize=8.5)
 
    # ── Details box for best design ───────────────────────────────────────────
    if feasible:
        b = feasible[0]
        detail = (f"Optimal: N={b.arch.N}, K={b.arch.K}\n"
                  f"HS: {b.hs}  LS: {b.ls}\n"
                  f"L = {b.L*1e9:.0f} nH  "
                  f"f$_{{sw}}$ = {b.f_sw/1e6:.2f} MHz\n"
                  f"Area = {b.area:.1f} mm²  "
                  f"J = {I_OUT/b.area:.2f} A/mm²")
        ax_ripple.text(0.98, 0.02, detail,
                       transform=ax_ripple.transAxes,
                       va='bottom', ha='right', fontsize=7.5,
                       color=COLORS['text'],
                       bbox=dict(facecolor='#FEF9C3', edgecolor=COLORS['best'],
                                 boxstyle='round,pad=0.4', linewidth=1.5))
 
 
def generate_figures(results1, results2):
    """Generate two separate figures — one per case."""
 
    # ── Shared colorbar figure element ────────────────────────────────────────
    def add_colorbar(fig):
        ax_cb = fig.add_axes([0.92, 0.15, 0.012, 0.70])
        sm    = cm.ScalarMappable(cmap=EFF_CMAP, norm=EFF_NORM)
        sm.set_array([])
        cb    = fig.colorbar(sm, cax=ax_cb)
        cb.set_label('Efficiency (%)', fontsize=8.5, fontweight='bold',
                     rotation=270, labelpad=14)
        cb.ax.tick_params(labelsize=8)
 
    for case_idx, (results, case_label, case_sub, fname) in enumerate([
        (results1,
         'Case 1: Planar Integration — No Vertical Stacking',
         'Area = Σ component footprints ≤ 20 mm²  |  '
         '48V→1V, 20A, ΔI<40%, ΔV<5%, C$_{out}$=100µF',
         'dse_case1_planar.png'),
        (results2,
         'Case 2: 3D Vertical Stacking (Embedded Package)',
         'Area = max component layer footprint ≤ 20 mm²  |  '
         '48V→1V, 20A, ΔI<40%, ΔV<5%, C$_{out}$=100µF',
         'dse_case2_stacked.png'),
    ]):
        n = len(results)
        fig = plt.figure(figsize=(13, max(5.5, n * 0.7 + 2.0)))
        fig.patch.set_facecolor(COLORS['bg'])
 
        # Title
        fig.text(0.5, 0.97, case_label,
                 ha='center', va='top',
                 fontsize=13, fontweight='bold', color=COLORS['text'])
 
        # System specs box
        specs = (f"System: V$_{{in}}$=48V, V$_{{out}}$=1V, I$_{{out}}$=20A  |  "
                 f"Target J = {I_OUT/AREA_BUDGET:.0f} A/mm²  |  "
                 f"Ripple: ΔI<40%, ΔV<5%")
        fig.text(0.5, 0.93, specs,
                 ha='center', va='top',
                 fontsize=8.5, color=COLORS['muted'], style='italic')
 
        # Two panels: main (efficiency) + ripple
        ax_main   = fig.add_axes([0.14, 0.10, 0.54, 0.78])
        ax_ripple = fig.add_axes([0.70, 0.10, 0.20, 0.78])
 
        plot_case(ax_main, ax_ripple, results, '', '')
 
        # Update title (already in fig.text)
        ax_main.set_title('Efficiency & Loss per Topology',
                          fontsize=10, fontweight='bold', pad=6)
 
        # Legend
        legend_handles = [
            mpatches.Patch(facecolor=eff_color(99), label='High efficiency'),
            mpatches.Patch(facecolor=eff_color(93), label='Mid efficiency'),
            mpatches.Patch(facecolor=eff_color(88), label='Low efficiency'),
            mpatches.Patch(facecolor=COLORS['infeas'],
                           hatch='////', edgecolor=COLORS['infeas_t'],
                           label='Infeasible'),
            mpatches.Patch(facecolor=COLORS['ripple_i'],
                           alpha=0.85, label='ΔI current ripple'),
            mpatches.Patch(facecolor=COLORS['ripple_v'],
                           alpha=0.85, label='ΔV voltage ripple'),
        ]
        fig.legend(handles=legend_handles,
                   loc='lower center', ncol=6,
                   fontsize=8, bbox_to_anchor=(0.50, 0.00),
                   framealpha=0.9, edgecolor=COLORS['grid'])
 
        # Star note
        fig.text(0.01, 0.97, '★ = Optimal topology',
                 va='top', fontsize=8, color=COLORS['best'],
                 fontweight='bold')
 
        fig.savefig(fname, dpi=260, bbox_inches='tight',
                    facecolor=COLORS['bg'])
        print(f"Saved: {fname}")
 
        # ── PPTX export ───────────────────────────────────────────────────────
        import io
        from pptx import Presentation
        from pptx.util import Inches
        from pptx.dml.color import RGBColor as PPTXColor
 
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=260, bbox_inches='tight',
                    facecolor=COLORS['bg'])
        buf.seek(0)
 
        prs = Presentation()
        prs.slide_width  = Inches(13.33)
        prs.slide_height = Inches(7.5)
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        bg = slide.background.fill
        bg.solid()
        bg.fore_color.rgb = PPTXColor(0xF0, 0xF4, 0xF8)
        slide.shapes.add_picture(buf, Inches(0.10), Inches(0.15),
                                 Inches(13.10), Inches(7.15))
        pptx_fname = fname.replace('.png', '.pptx')
        prs.save(pptx_fname)
        print(f"Saved: {pptx_fname}")
 
        plt.close(fig)
 
 
generate_figures(results1, results2)
