"""
sota_model_vs_optimizer.py
 
Apple-to-apple comparison: SOTA designs re-evaluated through the same
analytical loss model, then compared against the optimizer's best output
for the same topology and footprint budget.
 
Case 1: DSCH   (N=3, K=2)  — HS: EPC2216,        LS: EPC2014C
Case 2: DPMIH  (N=4, K=4)  — HS: 2×EPC2015C ∥,   LS: 2×EPC2023 ∥
 
For parallel devices:  R_DS_ON → R/2,  all charges/capacitances → ×2
"""
 
import sys, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
 
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
 
from HVR_FULL_OPT_EPC import (
    VRArchitecture, EPCDevice, LossModelInputs,
    compute_total_loss, generate_B_array,
    load_epc_devices, filter_candidate_devices_for_architecture,
    row_to_device,
)
 
V_GS_DRIVE = 5.0
 
# ── Helper: build an EPCDevice from raw datasheet values ─────────────────────
def make_device(pn, vds, rds_mohm, qg_nc, qgd_nc, qoss_nc, id_a,
                parallel=1):
    """
    parallel=N means N devices in parallel:
      R_DS_ON  → /N
      Q_G, Q_GD, Q_OSS → ×N   (more charge, same time → more gate-drive loss)
      C_OSS    → ×N            (more stored energy)
      I_D      → ×N
    """
    r  = (rds_mohm * 1e-3) / parallel
    qg  = (qg_nc  * 1e-9) * parallel
    qgd = (qgd_nc * 1e-9) * parallel
    qoss= (qoss_nc* 1e-9) * parallel
    coss= qoss / vds          # linear approx at rated voltage
    cg  = qg  / V_GS_DRIVE
    return EPCDevice(
        part_number=pn if parallel==1 else f'{parallel}x{pn}',
        VDSmax=vds, VGSmax=6.0,
        R_DS_ON=r,
        Q_G=qg, Q_GD=qgd, Q_OSS=qoss,
        C_G=cg, C_OSS=coss,
        ID_A=id_a * parallel,
    )
 
# ── Device footprint lookup (mm²) ─────────────────────────────────────────────
EPC_FP = {
    'EPC2216': 0.57*2,  # BGA 0.85×1.2 — package area ≈ 1.02 mm², use 1.14 for margin
    'EPC2014C': 0.63,   # LGA 1.7×1.1
    'EPC2015C': 2.29,   # LGA 4.1×1.6
    'EPC2023':  4.32,   # LGA 6.05×2.3  (note: large device)
}
DEFAULT_FP = 3.63
 
def dev_fp(pn_base, parallel=1):
    return EPC_FP.get(pn_base, DEFAULT_FP) * parallel
 
def total_fp(hs_pn, ls_pn, n_hs, n_ls, n_ind,
             hs_par=1, ls_par=1, ind_fp=10.0):
    return (dev_fp(hs_pn, hs_par) * n_hs
            + dev_fp(ls_pn, ls_par) * n_ls
            + ind_fp * n_ind)
 
# ═══════════════════════════════════════════════════════════════════════════════
#  OPTIMIZER helper
# ═══════════════════════════════════════════════════════════════════════════════
def run_optimizer(arch, df_devices, V_IN, V_OUT, I_OUT,
                  area_budget, L_values, f_sw_values,
                  hs_par_fixed=None, ls_par_fixed=None):
    """
    Brute-force optimizer. Returns (best_loss, best_eff, best_cfg).
    hs_par_fixed / ls_par_fixed: if set, force a specific parallel count
    for the optimal devices (use None to let it search freely).
    """
    N, K, K_A = arch.N, arch.K, arch.K_A
    D = arch.D
 
    hs_cands, ls_cands = filter_candidate_devices_for_architecture(
        df=df_devices, arch=arch,
        V_in=V_IN, V_out=V_OUT,
        V_gs_drive=V_GS_DRIVE, I_out=I_OUT,
    )
 
    best_loss = float('inf')
    best_eff  = 0.0
    best_cfg  = {}
 
    for hs_base in hs_cands:
        for ls_base in ls_cands:
            for L in L_values:
                ind_fp_val = 10.0 * (L / 440e-9) ** 0.5
                for f_sw in f_sw_values:
                    # CCM ripple constraint
                    Delta_I = (D / (f_sw * L)) * (
                        (V_IN / N) * K_A - V_OUT * K)
                    if abs(Delta_I) > 0.5 * I_OUT:
                        continue
 
                    # Footprint check (1 device per switch position)
                    fp = total_fp(
                        hs_base.part_number, ls_base.part_number,
                        N, K, K,
                        hs_par=1, ls_par=1,
                        ind_fp=ind_fp_val,
                    )
                    if fp > area_budget:
                        continue
 
                    inp = LossModelInputs(
                        hs_device=hs_base, ls_device=ls_base,
                        I_out=I_OUT, L=L,
                        V_out=V_OUT, V_in=V_IN,
                        f_sw=f_sw, V_gs_drive=V_GS_DRIVE,
                    )
                    loss = compute_total_loss(arch, inp)
                    eff  = V_OUT * I_OUT / (V_OUT * I_OUT + loss) * 100
 
                    if loss < best_loss:
                        best_loss = loss
                        best_eff  = eff
                        best_cfg  = {
                            'hs':      hs_base.part_number,
                            'ls':      ls_base.part_number,
                            'hs_Rds':  hs_base.R_DS_ON,
                            'ls_Rds':  ls_base.R_DS_ON,
                            'f_sw':    f_sw,
                            'L':       L,
                            'fp':      fp,
                            'Delta_I': Delta_I,
                        }
 
    return best_loss, best_eff, best_cfg
 
 
# ═══════════════════════════════════════════════════════════════════════════════
#  CASE 1 — DSCH (N=3, K=2)
#  SOTA switches: EPC2216 (HS), EPC2014C (LS)
#  From CSV: EPC2216 → VDS=15V, Rds=26mΩ, QG=0.87nC, QGD=0.13nC, QOSS=0.53nC, ID=3.4A
#             EPC2014C→ VDS=40V, Rds=16mΩ, QG=2.0nC,  QGD=0.3nC,  QOSS=4.0nC,  ID=10A
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*65)
print("  CASE 1: DSCH (N=3, K=2)  |  48V→1V  |  20A")
print("="*65)
 
V_IN_1, V_OUT_1, I_OUT_1 = 48.0, 1.0, 20.0
AREA_1   = 139.2   # mm²
SOTA_EXP_1 = 89.0  # % experimental (from paper)
SOTA_FSW_1 = 500e3
SOTA_L_1   = 440e-9
 
N1, K1, KA1 = 3, 2, 1
B1   = generate_B_array(N1, K1, KA1)
D1   = (V_OUT_1 * N1) / V_IN_1
arch1 = VRArchitecture(N=N1, K=K1, K_A=KA1, B_array=B1, D=D1,
                       component_count=2*N1+2*K1-1)
 
# SOTA DSCH actual switches (from datasheet supplied by user)
# HS: R_DS_ON=19mΩ, Q_G=5nC, Q_GD=1.5nC, Q_OSS=2nC, VDS=40V, ID=20A
# LS: R_DS_ON=4.4mΩ, Q_G=13.6nC, Q_GD=2.6nC, Q_OSS=16nC, VDS=30V, ID=25A
sota_hs_1 = make_device('DSCH_HS', 40, 19.0, 5.0,  1.5,  2.0,  20.0)
sota_ls_1 = make_device('DSCH_LS', 30,  4.4, 13.6, 2.6, 16.0,  25.0)
 
sota_inp_1 = LossModelInputs(
    hs_device=sota_hs_1, ls_device=sota_ls_1,
    I_out=I_OUT_1, L=SOTA_L_1,
    V_out=V_OUT_1, V_in=V_IN_1,
    f_sw=SOTA_FSW_1, V_gs_drive=V_GS_DRIVE,
)
sota_loss_1 = compute_total_loss(arch1, sota_inp_1)
sota_eff_model_1 = V_OUT_1 * I_OUT_1 / (V_OUT_1 * I_OUT_1 + sota_loss_1) * 100
 
print(f"\n  SOTA (model re-evaluation):")
print(f"    HS: EPC2216  Rds={sota_hs_1.R_DS_ON*1e3:.1f} mΩ  "
      f"QG={sota_hs_1.Q_G*1e9:.2f} nC  QGD={sota_hs_1.Q_GD*1e9:.2f} nC")
print(f"    LS: EPC2014C Rds={sota_ls_1.R_DS_ON*1e3:.1f} mΩ  "
      f"QG={sota_ls_1.Q_G*1e9:.2f} nC  QGD={sota_ls_1.Q_GD*1e9:.2f} nC")
print(f"    L={SOTA_L_1*1e9:.0f} nH   f_sw={SOTA_FSW_1/1e3:.0f} kHz")
print(f"    Loss (model)      : {sota_loss_1:.3f} W")
print(f"    Efficiency (model): {sota_eff_model_1:.2f}%")
print(f"    Efficiency (exp.) : {SOTA_EXP_1:.1f}%  [published]")
 
# Optimizer
df1 = load_epc_devices('EPC-Product-Table.csv', V_gs_op=V_GS_DRIVE)
L_vals_1   = [440e-9, 220e-9, 100e-9]
f_sw_vals_1 = np.logspace(np.log10(50e3), np.log10(5e6), 50)
 
opt_loss_1, opt_eff_1, opt_cfg_1 = run_optimizer(
    arch1, df1, V_IN_1, V_OUT_1, I_OUT_1,
    AREA_1, L_vals_1, f_sw_vals_1,
)
 
print(f"\n  OPTIMIZER output:")
print(f"    HS: {opt_cfg_1['hs']}  Rds={opt_cfg_1['hs_Rds']*1e3:.2f} mΩ")
print(f"    LS: {opt_cfg_1['ls']}  Rds={opt_cfg_1['ls_Rds']*1e3:.2f} mΩ")
print(f"    L={opt_cfg_1['L']*1e9:.0f} nH   f_sw={opt_cfg_1['f_sw']/1e6:.3f} MHz")
print(f"    Footprint : {opt_cfg_1['fp']:.1f} mm²  (budget: {AREA_1} mm²)")
print(f"    DeltaI    : {opt_cfg_1['Delta_I']:.2f} A "
      f"({abs(opt_cfg_1['Delta_I'])/I_OUT_1*100:.1f}% of I_out)")
print(f"    Loss (model)      : {opt_loss_1:.3f} W")
print(f"    Efficiency (model): {opt_eff_1:.2f}%")
 
delta_model_1 = opt_eff_1 - sota_eff_model_1
delta_exp_1   = opt_eff_1 - SOTA_EXP_1
 
print(f"\n  ── Comparison (apple-to-apple, model vs model) ──")
print(f"    SOTA  model eff : {sota_eff_model_1:.2f}%")
print(f"    OPT   model eff : {opt_eff_1:.2f}%")
print(f"    Gain (model)    : +{delta_model_1:.2f} pp")
print(f"    SOTA  exp.  eff : {SOTA_EXP_1:.1f}%   [published, for context]")
print(f"    Gain (vs exp.)  : +{delta_exp_1:.2f} pp  [includes routing etc.]")
 
 
# ═══════════════════════════════════════════════════════════════════════════════
#  CASE 2 — DPMIH (N=4, K=4)
#  SOTA switches: 2×EPC2015C ∥ (HS),  2×EPC2023 ∥ (LS)
#  EPC2015C: VDS=40V, Rds=4mΩ,  QG=8.7nC, QGD=1.2nC, QOSS=19nC, ID=53A
#  EPC2023:  VDS=30V, Rds=1.45mΩ,QG=19nC, QGD=3.2nC, QOSS=30nC, ID=90A
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*65)
print("  CASE 2: DPMIH (N=4, K=4)  |  48V→1V  |  25A")
print("="*65)
 
V_IN_2, V_OUT_2, I_OUT_2 = 48.0, 1.0, 25.0
# DPMIH SOTA component footprint (computed from datasheets):
#   HS: 4 positions × 2×EPC2015C (2.29 mm² each) = 4×2×2.29  =   18.32 mm²
#   LS: 4 positions × 2×EPC2023  (4.32 mm² each) = 4×2×4.32  =   34.56 mm²
#   Inductors: 4 × 486 mm²                                    = 1944.00 mm²
#   Flying caps: 3 × 5.12 mm²                                 =   15.36 mm²
#   Total SOTA footprint                                       = 2012.24 mm²
AREA_2   = 2012.24
SOTA_EXP_2 = 91.5
SOTA_FSW_2 = 500e3
SOTA_L_2   = 440e-9
 
N2, K2, KA2 = 4, 4, 2
B2   = generate_B_array(N2, K2, KA2)
D2   = (V_OUT_2 * N2) / V_IN_2
arch2 = VRArchitecture(N=N2, K=K2, K_A=KA2, B_array=B2, D=D2,
                       component_count=2*N2+2*K2-1)
 
# SOTA devices: 2 in parallel
sota_hs_2 = make_device('EPC2015C', 40, 4.0,  8.7, 1.2, 19.0, 53.0, parallel=2)
sota_ls_2 = make_device('EPC2023',  30, 1.45, 19.0, 3.2, 30.0, 90.0, parallel=2)
 
sota_inp_2 = LossModelInputs(
    hs_device=sota_hs_2, ls_device=sota_ls_2,
    I_out=I_OUT_2, L=SOTA_L_2,
    V_out=V_OUT_2, V_in=V_IN_2,
    f_sw=SOTA_FSW_2, V_gs_drive=V_GS_DRIVE,
)
sota_loss_2 = compute_total_loss(arch2, sota_inp_2)
sota_eff_model_2 = V_OUT_2 * I_OUT_2 / (V_OUT_2 * I_OUT_2 + sota_loss_2) * 100
 
print(f"\n  SOTA (model re-evaluation):")
print(f"    HS: 2×EPC2015C  Rds_eff={sota_hs_2.R_DS_ON*1e3:.2f} mΩ  "
      f"QG_eff={sota_hs_2.Q_G*1e9:.1f} nC  QGD_eff={sota_hs_2.Q_GD*1e9:.1f} nC")
print(f"    LS: 2×EPC2023   Rds_eff={sota_ls_2.R_DS_ON*1e3:.3f} mΩ  "
      f"QG_eff={sota_ls_2.Q_G*1e9:.1f} nC  QGD_eff={sota_ls_2.Q_GD*1e9:.1f} nC")
print(f"    L={SOTA_L_2*1e9:.0f} nH   f_sw={SOTA_FSW_2/1e3:.0f} kHz")
print(f"    Loss (model)      : {sota_loss_2:.3f} W")
print(f"    Efficiency (model): {sota_eff_model_2:.2f}%")
print(f"    Efficiency (exp.) : {SOTA_EXP_2:.1f}%  [published]")
 
# Optimizer
df2 = load_epc_devices('EPC-Product-Table.csv', V_gs_op=V_GS_DRIVE)
L_vals_2    = [440e-9, 220e-9, 100e-9, 47e-9]
f_sw_vals_2 = np.logspace(np.log10(50e3), np.log10(5e6), 50)
 
opt_loss_2, opt_eff_2, opt_cfg_2 = run_optimizer(
    arch2, df2, V_IN_2, V_OUT_2, I_OUT_2,
    AREA_2, L_vals_2, f_sw_vals_2,
)
 
print(f"\n  OPTIMIZER output:")
print(f"    HS: {opt_cfg_2['hs']}  Rds={opt_cfg_2['hs_Rds']*1e3:.2f} mΩ")
print(f"    LS: {opt_cfg_2['ls']}  Rds={opt_cfg_2['ls_Rds']*1e3:.2f} mΩ")
print(f"    L={opt_cfg_2['L']*1e9:.0f} nH   f_sw={opt_cfg_2['f_sw']/1e6:.3f} MHz")
print(f"    Footprint : {opt_cfg_2['fp']:.1f} mm²  (budget: {AREA_2} mm²)")
print(f"    DeltaI    : {opt_cfg_2['Delta_I']:.2f} A "
      f"({abs(opt_cfg_2['Delta_I'])/I_OUT_2*100:.1f}% of I_out)")
print(f"    Loss (model)      : {opt_loss_2:.3f} W")
print(f"    Efficiency (model): {opt_eff_2:.2f}%")
 
delta_model_2 = opt_eff_2 - sota_eff_model_2
delta_exp_2   = opt_eff_2 - SOTA_EXP_2
 
print(f"\n  ── Comparison (apple-to-apple, model vs model) ──")
print(f"    SOTA  model eff : {sota_eff_model_2:.2f}%")
print(f"    OPT   model eff : {opt_eff_2:.2f}%")
print(f"    Gain (model)    : +{delta_model_2:.2f} pp")
print(f"    SOTA  exp.  eff : {SOTA_EXP_2:.1f}%   [published, for context]")
print(f"    Gain (vs exp.)  : +{delta_exp_2:.2f} pp  [includes routing etc.]")
 
 
# ═══════════════════════════════════════════════════════════════════════════════
#  FIGURE — side-by-side for both cases
# ═══════════════════════════════════════════════════════════════════════════════
COLORS = {
    'sota_exp':   '#6B7280',   # grey   — experimental (context only)
    'sota_model': '#C00000',   # red    — SOTA re-evaluated by model
    'opt':        '#2563EB',   # blue   — optimizer
    'bg':         '#F8FAFC',
    'panel':      '#FFFFFF',
    'text':       '#1E293B',
    'grid':       '#CBD5E1',
}
 
fig, axes = plt.subplots(1, 2, figsize=(13, 6.0))
fig.patch.set_facecolor(COLORS['bg'])
fig.suptitle('Apple-to-Apple Efficiency Comparison: SOTA (Model) vs. Optimizer',
             fontsize=13, fontweight='bold', y=1.01)
 
cases = [
    {
        'ax':         axes[0],
        'title':      'DSCH (N=3, K=2)\n48V→1V | 20A | Budget: 139 mm²',
        'sota_exp':   SOTA_EXP_1,
        'sota_model': sota_eff_model_1,
        'opt_eff':    opt_eff_1,
        'delta_m':    delta_model_1,
        'sota_lbl':   f'SOTA model: DSCH HS (19mΩ) / DSCH LS (4.4mΩ)\n500 kHz, 440 nH',
        'opt_lbl':    f'Opt: {opt_cfg_1["hs"]}/{opt_cfg_1["ls"]}\n'
                      f'{opt_cfg_1["L"]*1e9:.0f} nH, '
                      f'{opt_cfg_1["f_sw"]/1e6:.2f} MHz, '
                      f'{opt_cfg_1["fp"]:.0f} mm²',
    },
    {
        'ax':         axes[1],
        'title':      'DPMIH (N=4, K=4)\n48V→1V | 25A | Budget: 2012 mm²',
        'sota_exp':   SOTA_EXP_2,
        'sota_model': sota_eff_model_2,
        'opt_eff':    opt_eff_2,
        'delta_m':    delta_model_2,
        'sota_lbl':   f'SOTA model: 2×EPC2015C / 2×EPC2023\n500 kHz, 440 nH',
        'opt_lbl':    f'Opt: {opt_cfg_2["hs"]}/{opt_cfg_2["ls"]}\n'
                      f'{opt_cfg_2["L"]*1e9:.0f} nH, '
                      f'{opt_cfg_2["f_sw"]/1e6:.2f} MHz, '
                      f'{opt_cfg_2["fp"]:.0f} mm²',
    },
]
 
for c in cases:
    ax = c['ax']
    ax.set_facecolor(COLORS['panel'])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', color=COLORS['grid'], linewidth=0.8, zorder=0)
 
    labels = ['SOTA\n(Experimental)', 'SOTA\n(Model)', 'Optimized\n(Model)']
    vals   = [c['sota_exp'], c['sota_model'], c['opt_eff']]
    cols   = [COLORS['sota_exp'], COLORS['sota_model'], COLORS['opt']]
    hatch  = ['///', '\\\\\\', '']
 
    bars = ax.bar(labels, vals, color=cols, width=0.42,
                  edgecolor='white', linewidth=0.8,
                  hatch=hatch, zorder=3)
 
    for bar, val, col in zip(bars, vals, cols):
        ax.text(bar.get_x() + bar.get_width()/2,
                bar.get_height() + 0.08,
                f'{val:.1f}%',
                ha='center', va='bottom',
                fontsize=12, fontweight='bold', color=col)
 
    # Arrow: SOTA model → Optimizer (the fair comparison)
    ax.annotate('',
        xy=(2, c['opt_eff']), xytext=(2, c['sota_model']),
        arrowprops=dict(arrowstyle='<->', color=COLORS['opt'],
                        lw=2.2, mutation_scale=16))
    ax.text(2.28, (c['sota_model'] + c['opt_eff'])/2,
            f'+{c["delta_m"]:.2f} pp\n(model)',
            ha='left', va='center',
            fontsize=10, fontweight='bold', color=COLORS['opt'])
 
    ax.set_ylabel('Efficiency (%)', fontsize=12, fontweight='bold')
    ax.set_title(c['title'], fontsize=11, fontweight='bold', pad=10)
 
    y_lo = min(vals) - 2.5
    y_hi = max(vals) + 2.5
    ax.set_ylim(y_lo, y_hi)
    ax.tick_params(labelsize=10)
 
    # Footnote
    ax.text(0.5, -0.18, c['sota_lbl'] + '\n' + c['opt_lbl'],
            transform=ax.transAxes,
            ha='center', va='top', fontsize=8, color=COLORS['text'])
 
fig.tight_layout(pad=1.8)
fig.savefig('sota_model_vs_optimizer.png', dpi=250,
            bbox_inches='tight', facecolor=COLORS['bg'])
print("\nSaved: sota_model_vs_optimizer.png")
