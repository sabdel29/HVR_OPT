"""
diag_hs_sweep.py
----------------
Diagnostic: for Arch N=3, K=2, K_A=1, sweep every qualifying HS device
(sorted by RDS_on ascending) and show the minimum achievable total loss
along with its breakdown into P_cond / P_sw_HS / P_sw_GD / P_sw_COSS.

All other choices (LS device, inductor, capacitor, f_sw) are co-optimised
by an inner loop so the comparison is fair — we find the best possible
result for each HS candidate.

No files are modified by this script.
"""
import sys
import io
import numpy as np

# Force UTF-8 output on Windows so Unicode symbols print correctly
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, ".")
from HVR_FULL_OPT_EPC_V2 import (
    VRArchitecture, generate_B_array,
    load_epc_devices, row_to_device,
    LossModelInputs, compute_total_loss,
    filter_candidate_devices, filter_candidate_inductors,
    filter_candidate_capacitors,
    INDUCTOR_LIBRARY, CAPACITOR_LIBRARY,
)

# ── Parameters (match your last run) ──────────────────────────────────────────
V_IN        = 48.0
V_OUT       = 1.0
I_OUT       = 20.0
V_GS_DRIVE  = 5.0
RIPPLE_FACTOR  = 0.5        # |ΔI_out| < 50% × I_out
V_RIPPLE_FRAC  = 0.25       # ΔV_out   < 25% × V_out
I_TARGET_DENSITY = 1.0      # A/mm²
CSV_PATH    = "EPC-Product-Table.csv"
F_SW_VALUES = np.logspace(np.log10(0.043e6), np.log10(200e6), 50)

# ── Architecture under study ──────────────────────────────────────────────────
N, K, K_A = 2, 2, 1
B_array = generate_B_array(N, K, K_A)
D       = (V_OUT * N) / V_IN
arch    = VRArchitecture(N=N, K=K, K_A=K_A, B_array=B_array, D=D,
                         component_count=N + K + K + (N - 1))

area_budget   = I_OUT / I_TARGET_DENSITY
i_ripple_lim  = RIPPLE_FACTOR * I_OUT
v_ripple_lim  = V_RIPPLE_FRAC * V_OUT

# ── Load devices & passives ───────────────────────────────────────────────────
df = load_epc_devices(CSV_PATH, V_gs_op=V_GS_DRIVE)

all_hs, ls_pool = filter_candidate_devices(df, arch, V_IN, V_OUT, V_GS_DRIVE, I_OUT)
inds = filter_candidate_inductors(INDUCTOR_LIBRARY, arch, I_OUT)
caps = filter_candidate_capacitors(CAPACITOR_LIBRARY, arch, V_IN)

print(f"\nArch  N={N}, K={K}, K_A={K_A}  |  D={D:.4f}  |  area_budget={area_budget:.1f} mm²")
print(f"HS candidates : {len(all_hs)}  (VDSmax≥{V_IN/N:.0f}V, ID≥{I_OUT/N:.1f}A)")
print(f"LS candidates : {len(ls_pool)}  (VDSmax≥{V_OUT:.0f}V, ID≥{I_OUT*max(B_array)/N:.1f}A)")
print(f"Inductors     : {len(inds)}")
print(f"Capacitors    : {len(caps)}")
print(f"f_sw points   : {len(F_SW_VALUES)}")
print()

# Sort HS candidates by RDS_on ascending so the table reads low → high
all_hs_sorted = sorted(all_hs, key=lambda d: d.R_DS_ON)

# Print the f_sw sweep values so the user can see what's being tested
print(f"f_sw sweep (MHz): {', '.join(f'{f/1e6:.3f}' for f in F_SW_VALUES)}")
print()

# ── P_cond breakdown weights (for the notes section) ─────────────────────────
# P_cond = (V_out/V_in) * I²_rms * [R_HS + 2*(1-1/N)*R_C_ESR
#           + (V_in/(N²*V_out)*(R_L+R_LS) + 2*R_LS/N)*B_sum - correction]
# V_in/(N²*V_out) = 48/(9*1) = 5.33 → LS resistance is amplified 5.33x
LS_AMPLIFICATION = V_IN / (N**2 * V_OUT)

# ── Header ────────────────────────────────────────────────────────────────────
HDR = (f"{'HS Part':<16} {'RDSon_HS':>9} {'QG_HS':>7}"
       f" {'LS Part':<14} {'RDSon_LS':>9}"
       f" {'f_sw_MHz':>9}"
       f" {'TotalLoss':>10} {'P_cond':>8} {'P_sw':>8}"
       f" {'P_swHS':>7} {'P_swGD':>7} {'P_swCSS':>8}"
       f" {'Area_mm2':>9} {'Feasible':>8}")
SEP = "=" * len(HDR)
print(SEP)
print(HDR)
print(SEP)

# ── Sweep ─────────────────────────────────────────────────────────────────────
for hs in all_hs_sorted:
    best_loss   = float("inf")
    best_row    = None          # (lr, f_sw, ls, ind, cap, area)

    for ls in ls_pool:
        for ind in inds:
            f_valid = F_SW_VALUES[F_SW_VALUES <= ind.f_max_mhz * 1e6]
            if len(f_valid) == 0:
                continue
            for cap in caps:
                fp_hs = hs.footprint_mm2 if not (isinstance(hs.footprint_mm2, float)
                                                  and np.isnan(hs.footprint_mm2)) else 2.0
                fp_ls = ls.footprint_mm2 if not (isinstance(ls.footprint_mm2, float)
                                                  and np.isnan(ls.footprint_mm2)) else 2.0
                area = max(N * fp_hs,
                           K * fp_ls,
                           K * ind.footprint_mm2,
                           (N - 1) * cap.footprint_mm2)
                if area > area_budget:
                    continue

                for f_sw in f_valid:
                    lr = compute_total_loss(arch, LossModelInputs(
                        hs_device=hs, ls_device=ls,
                        inductor=ind, capacitor=cap,
                        I_out=I_OUT, V_out=V_OUT,
                        V_in=V_IN, f_sw=f_sw,
                    ))
                    if abs(lr.delta_i_out) >= i_ripple_lim:
                        continue
                    if lr.delta_v_out >= v_ripple_lim:
                        continue
                    if lr.total_loss < best_loss:
                        best_loss = lr.total_loss
                        best_row  = (lr, f_sw, ls, ind, cap, area)

    if best_row is None:
        print(f"{hs.part_number:<16} {hs.R_DS_ON*1e3:>8.2f}m {hs.Q_G*1e9:>6.2f}n"
              f"  -- NO FEASIBLE COMBINATION (area or ripple constraint)")
        continue

    lr, fsw, ls, ind, cap, area = best_row
    feasible = "YES" if area <= area_budget else "NO"
    print(f"{hs.part_number:<16} {hs.R_DS_ON*1e3:>8.2f}m {hs.Q_G*1e9:>6.2f}n"
          f" {ls.part_number:<14} {ls.R_DS_ON*1e3:>8.2f}m"
          f" {fsw/1e6:>9.3f}"
          f" {lr.total_loss:>10.4f} {lr.p_cond:>8.4f} {lr.p_sw:>8.4f}"
          f" {lr.p_sw_hs:>7.4f} {lr.p_sw_gd:>7.4f} {lr.p_sw_coss:>8.4f}"
          f" {area:>9.2f} {feasible:>8}")

print(SEP)
print()
print("Notes on P_cond:")
print(f"  Formula: P_cond = (V_out/V_in) * I_rms^2 * [R_HS  +  (V_in/(N^2*V_out)) * R_LS * B_sum  + ...]")
print(f"  V_out/V_in      = {V_OUT/V_IN:.4f}  (scales everything down — HS R_DS_ON has low weight)")
print(f"  V_in/(N^2*V_out)= {LS_AMPLIFICATION:.2f}   (LS R_DS_ON is amplified {LS_AMPLIFICATION:.1f}x vs HS R_DS_ON)")
print(f"  => Even though HS RDS_on differs by 5x, the LS device chosen by the optimizer")
print(f"     changes too, and its {LS_AMPLIFICATION:.1f}x-amplified resistance dominates P_cond.")
print()
print(f"Ripple gates : |DI| < {i_ripple_lim:.1f} A,  DV < {v_ripple_lim*1e3:.0f} mV")
print(f"Area budget  : {area_budget:.0f} mm²  (= I_out / I_target_density = {I_OUT}/{I_TARGET_DENSITY})")
print(f"f_sw range   : {F_SW_VALUES[0]/1e6:.3f} MHz  to  {F_SW_VALUES[-1]/1e6:.1f} MHz  ({len(F_SW_VALUES)} log-spaced points)")
