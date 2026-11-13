import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from dataclasses import dataclass
 
 
#╔═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
#║                  Hybrid-Voltage Regulators (SC + Buck) Optimization Framework                                       ║
#╚═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
#######################################################################################################################
# Inputs: target_component_count, V_in, V_out, I_out, L (Inductance), default_f_sw (switching frequency),             #
#         V_gs_drive (Gate drive volt for switches), f_sw_values (Swicthing freq sweep),                              #
#         df_devices (EPC GANs in market)                                                                             #
#                                                                                                                     #
# Outputs:                                                                                                            #
#          Architecture (N=3, K=2, K_A=1), where this conv. has N branches, K inductors, K_A inductors in phase A     #
#          Component count: 9, (N-1 Caps, K Inds, N High side switches, K Low side switches)                          #
#          B_array: [1, 2], (Branches count connected to each inductor)                                               #
#          Default loss: 16.3807 W, (Calculated loss at a random unoptimized point)                                   #
#          Optimized HS device: EPC2055, (Chosen HS device for optimized loss)                                        #
#          Optimized LS device: EPC2366, (Chosen LS device for optimized loss)                                        #
#          Optimized f_sw: 0.093 MHz, (Optimized switching Freq)                                                      #
#          Optimized loss: 0.9029 W, (Optimized loss value)                                                           #
#                                                                                                                     #
#This framework do the following:                                                                                     #
#          1) Generate different VR topologies with different N, K, K_A & B_array to be investigated                  #
#          2) Each VR is optimized for least power loss using nested loops for EPC GAN LS, EPC GAN HS, f_sw           #
#             to get each optimal value while fixing passives and input constraints (note that this optimization      #
#             isn't area constrained and ripple constrained (Delta_I_out))                                            #
#          3) GANs are captured from EPC-Product-Table.csv                                                            #
#                                                                                                                     #
# What needs to be added:
#          1) Delta_I_out < 50%*I_out (Add ripple constraint)
#          2) Area constraint: All this optimization should be done under the area constraint, so each component area #
#                              should be extracted from corresponding lookup-table/csv                                #
#          3) Passives should have lookup table inspired by industry and SOTA literature, so the code can choose      #
#                              Inductors: Will affect area, saturation current > max(B_array)*I_out/N,                #
#                              current ripple constraint and R_L ESR                                                  #
#                              Capacitors: Will affect area, R_C ESR, Voltage rating > V_in/N                         #
#                              Passives: All these passives must be able to be embedded                               #
#                                                                                                                     #
#          4) This now will be translated to 2 more nested sweeps, and more checks                                    #
#                                                                                                                     #
#                                                                                                                     #
#######################################################################################################################
 
# ============================================================
# 1) TOPOLOGY GENERATION
# ============================================================
 
@dataclass
class VRArchitecture:
    N: int
    K: int
    K_A: int
    B_array: list
    D: float
    component_count: int
 
 
def compute_component_count(N, K, hs_weight, ls_weight, inductor_weight, capacitor_weight):
    return (
        hs_weight * N
        + ls_weight * K
        + inductor_weight * K
        + capacitor_weight * (N - 1)
    )
 
 
def find_possible_pairs(hs_weight, ls_weight, inductor_weight, capacitor_weight, target_component_count):
    pairs = []
 
    n = 2
    while True:
        min_component_count = compute_component_count(
            N=n,
            K=2,
            hs_weight=hs_weight,
            ls_weight=ls_weight,
            inductor_weight=inductor_weight,
            capacitor_weight=capacitor_weight
        )
 
        if min_component_count > target_component_count:
            break
 
        for k in range(2, n + 1):
            component_count = compute_component_count(
                N=n,
                K=k,
                hs_weight=hs_weight,
                ls_weight=ls_weight,
                inductor_weight=inductor_weight,
                capacitor_weight=capacitor_weight
            )
            if component_count <= target_component_count:
                pairs.append((n, k))
 
        n += 1
 
    return pairs
 
 
def distribute_branches(branches, inductors):
    base = branches // inductors
    remainder = branches % inductors
    return [base + 1 if i < remainder else base for i in range(inductors)]
 
 
def generate_B_array(N, K, K_A):
    K_B = K - K_A
 
    phase_A_branches = math.ceil(N / 2)
    phase_B_branches = math.floor(N / 2)
 
    phase_A_distribution = distribute_branches(phase_A_branches, K_A)
    phase_B_distribution = distribute_branches(phase_B_branches, K_B)
 
    B_array = []
    i, j = 0, 0
 
    if N % 2 == 0:
        while i < len(phase_A_distribution) or j < len(phase_B_distribution):
            if i < len(phase_A_distribution):
                B_array.append(phase_A_distribution[i])
                i += 1
            if j < len(phase_B_distribution):
                B_array.append(phase_B_distribution[j])
                j += 1
    else:
        if K_A == 1:
            while i < len(phase_A_distribution) or j < len(phase_B_distribution):
                if j < len(phase_B_distribution):
                    B_array.append(phase_B_distribution[j])
                    j += 1
                if i < len(phase_A_distribution):
                    B_array.append(phase_A_distribution[i])
                    i += 1
        else:
            while i < len(phase_A_distribution) or j < len(phase_B_distribution):
                if i < len(phase_A_distribution):
                    B_array.append(phase_A_distribution[i])
                    i += 1
                if j < len(phase_B_distribution):
                    B_array.append(phase_B_distribution[j])
                    j += 1
 
    return B_array
 
 
def generate_architectures(hs_weight, ls_weight, inductor_weight, capacitor_weight,
                           target_component_count, V_out, V_in):
    pairs = find_possible_pairs(
        hs_weight=hs_weight,
        ls_weight=ls_weight,
        inductor_weight=inductor_weight,
        capacitor_weight=capacitor_weight,
        target_component_count=target_component_count
    )
 
    architectures = []
    for N, K in pairs:
        K_A = math.ceil(K / 2)
 
        if K_A >= K:
            continue
 
        B_array = generate_B_array(N, K, K_A)
        D = (V_out * N) / V_in
        component_count = compute_component_count(
            N=N,
            K=K,
            hs_weight=hs_weight,
            ls_weight=ls_weight,
            inductor_weight=inductor_weight,
            capacitor_weight=capacitor_weight
        )
 
        architectures.append(
            VRArchitecture(
                N=N,
                K=K,
                K_A=K_A,
                B_array=B_array,
                D=D,
                component_count=component_count
            )
        )
 
    return architectures
 
 
# ============================================================
# 2) EPC DEVICE TABLE LOADING
# ============================================================
 
def parse_first_number(val):
    """Extract the first numeric value from a cell that may have commas or spaces."""
    if pd.isna(val):
        return np.nan
    s = str(val).split(',')[0].strip().replace('"', '')
    try:
        return float(s)
    except ValueError:
        return np.nan
 
 
def load_epc_devices(csv_path, V_gs_op):
    df_raw = pd.read_csv(
        csv_path,
        thousands=None,
        dtype=str,
        encoding='utf-8-sig',
    )
 
    df_raw.columns = df_raw.columns.str.strip()
 
    rds_col = [c for c in df_raw.columns if 'RDS' in c or 'Rds' in c or 'rds' in c][0]
    df_raw = df_raw.rename(columns={rds_col: 'RDS_on_col'})
 
    df = pd.DataFrame()
    df['PartNumber'] = df_raw['PartNumber'].str.strip()
    df['VDSmax']     = df_raw['VDSmax'].apply(parse_first_number)
    df['VGSmax']     = df_raw['VGSmax'].apply(parse_first_number)
    df['R_DS_ON_mOhm'] = df_raw['RDS_on_col'].apply(parse_first_number)
    df['QG_nC']      = df_raw['QGtyp(nC)'].apply(parse_first_number)
    df['QGD_nC']     = df_raw['QGDtyp(nC)'].apply(parse_first_number)
    df['QOSS_nC']    = df_raw['QOSStyp(nC)'].apply(parse_first_number)
    df['ID_A']       = df_raw['ID (A)'].apply(parse_first_number)
 
    df = df.dropna(subset=['R_DS_ON_mOhm', 'QG_nC', 'QGD_nC', 'QOSS_nC', 'VDSmax', 'VGSmax']).copy()
    df = df.reset_index(drop=True)
 
    # Convert to SI units
    df['R_DS_ON'] = df['R_DS_ON_mOhm'] * 1e-3
    df['Q_G']     = df['QG_nC']   * 1e-9
    df['Q_GD']    = df['QGD_nC']  * 1e-9
    df['Q_OSS']   = df['QOSS_nC'] * 1e-9
 
    # Effective capacitances
    df['C_G']   = df['Q_G'] / V_gs_op
    df['C_OSS'] = df['Q_OSS'] / df['VDSmax']
 
    print(f"Loaded {len(df)} usable EPC devices")
    return df
 
 
# ============================================================
# 3) LOSS MODEL USING ACTUAL DEVICE PARAMETERS
# ============================================================
 
@dataclass
class EPCDevice:
    part_number: str
    VDSmax: float
    VGSmax: float
    R_DS_ON: float
    Q_G: float
    Q_GD: float
    Q_OSS: float
    C_G: float
    C_OSS: float
    ID_A: float
 
 
@dataclass
class LossModelInputs:
    hs_device: EPCDevice
    ls_device: EPCDevice
    I_out: float
    L: float
    V_out: float
    V_in: float
    f_sw: float
    V_gs_drive: float
 
 
def row_to_device(row):
    return EPCDevice(
        part_number=row['PartNumber'],
        VDSmax=row['VDSmax'],
        VGSmax=row['VGSmax'],
        R_DS_ON=row['R_DS_ON'],
        Q_G=row['Q_G'],
        Q_GD=row['Q_GD'],
        Q_OSS=row['Q_OSS'],
        C_G=row['C_G'],
        C_OSS=row['C_OSS'],
        ID_A=row['ID_A']
    )
 
 
def compute_total_loss(arch: VRArchitecture, inp: LossModelInputs):
    N = arch.N
    K = arch.K
    K_A = arch.K_A
    B_array = arch.B_array
    D = arch.D
 
    hs = inp.hs_device
    ls = inp.ls_device
 
    I_out = inp.I_out
    L = inp.L
    V_out = inp.V_out
    V_in = inp.V_in
    f_sw = inp.f_sw
    V_gs_drive = inp.V_gs_drive
 
    # Passive constants
    R_C_ESR = 3e-3
    R_L_ESR = 0.21e-3
 
    B_k = B_array[-1]
 
    # RMS output current
    I_out_rms_squared = (
        I_out ** 2
        + (D ** 2) / (12 * (f_sw ** 2) * (L ** 2))
        * (((V_in / N) * K_A - V_out * K) ** 2)
    )
    I_out_rms = np.sqrt(I_out_rms_squared)
    Delta_I_out = (D) / (f_sw * L) * ((V_in / N) * K_A - V_out * K)
    # Conduction loss
    B_sum = sum(b ** 2 for b in B_array)
 
    common_cond_term = (
        hs.R_DS_ON
        + 2 * (1 - 1 / N) * R_C_ESR
        + (
            (V_in / (N ** 2 * V_out)) * (R_L_ESR + ls.R_DS_ON)
            + (2 * ls.R_DS_ON) / N
        ) * B_sum
    )
 
    if B_k > 1:
        correction = (4 * B_k - 1) * (ls.R_DS_ON / N)
    else:
        correction = 3 * ls.R_DS_ON / N
 
    P_cond = (V_out / V_in) * (I_out_rms ** 2) * (common_cond_term - correction)
 
    # Switching constants
    V_th = 1.0
    V_pl = 1.6
    R_g_internal = 6e-4
    R_driver = 0.7
 
    I_g = (V_gs_drive - 0.5 * (V_th + V_pl)) / (R_g_internal + R_driver)
 
    P_sw_HS = (
        f_sw
        * (V_in / N - V_out)
        * I_out_rms
        * (hs.Q_GD / I_g)
    )
 
    P_sw_GD = f_sw * (N * hs.Q_G + K * ls.Q_G) * V_gs_drive
 
    P_sw_C_OSS = (f_sw / 2) * (
        N * hs.C_OSS * ((V_in / N) ** 2)
        + K * ls.C_OSS * ((V_in / N) ** 2)
    )
 
    P_sw = P_sw_HS + P_sw_GD + P_sw_C_OSS
 
    return P_cond + P_sw
 
 
# ============================================================
# 4) DEVICE FILTERING (ARCHITECTURE-AWARE)
# ============================================================
 
def filter_candidate_devices_for_architecture(df, arch, V_in, V_out, V_gs_drive, I_out):
    """
    Architecture-aware EPC filtering.
 
    Constraints:
    - HS voltage rating must satisfy VDSmax >= V_in / N
    - LS voltage rating must satisfy VDSmax >= V_out
    - Both HS and LS current ratings must satisfy ID_A >= I_out / N
    """
    N = arch.N
 
    hs_voltage_required = V_in / N
    ls_voltage_required = V_in / N
    current_required = I_out / N
 
    hs_df = df[df['VDSmax'] >= hs_voltage_required].copy()
    ls_df = df[df['VDSmax'] >= ls_voltage_required].copy()
 
    hs_df = hs_df[hs_df['VGSmax'] >= V_gs_drive]
    ls_df = ls_df[ls_df['VGSmax'] >= V_gs_drive]
 
    hs_df = hs_df[hs_df['ID_A'] >= current_required]
    ls_df = ls_df[ls_df['ID_A'] >= current_required]
 
    hs_devices = [row_to_device(row) for _, row in hs_df.iterrows()]
    ls_devices = [row_to_device(row) for _, row in ls_df.iterrows()]
 
    return hs_devices, ls_devices
 
 
# ============================================================
# 5) OPTIMIZATION: SEARCH HS DEVICE, LS DEVICE, f_sw
# ============================================================
 
@dataclass
class OptimizationResult:
    architecture: VRArchitecture
    default_loss: float
    optimized_hs_device: EPCDevice | None
    optimized_ls_device: EPCDevice | None
    optimized_f_sw: float | None
    optimized_loss: float
 
 
def compute_default_loss_for_architecture(arch, default_hs_device, default_ls_device, default_f_sw,
                                          I_out, L, V_out, V_in, V_gs_drive):
    default_inputs = LossModelInputs(
        hs_device=default_hs_device,
        ls_device=default_ls_device,
        I_out=I_out,
        L=L,
        V_out=V_out,
        V_in=V_in,
        f_sw=default_f_sw,
        V_gs_drive=V_gs_drive
    )
    return compute_total_loss(arch, default_inputs)
 
 
def optimize_architecture(arch, df_devices, f_sw_values,
                          default_hs_device, default_ls_device, default_f_sw,
                          I_out, L, V_out, V_in, V_gs_drive):
    default_loss = compute_default_loss_for_architecture(
        arch=arch,
        default_hs_device=default_hs_device,
        default_ls_device=default_ls_device,
        default_f_sw=default_f_sw,
        I_out=I_out,
        L=L,
        V_out=V_out,
        V_in=V_in,
        V_gs_drive=V_gs_drive
    )
 
    hs_devices, ls_devices = filter_candidate_devices_for_architecture(
        df=df_devices,
        arch=arch,
        V_in=V_in,
        V_out=V_out,
        V_gs_drive=V_gs_drive,
        I_out=I_out
    )
 
    if len(hs_devices) == 0 or len(ls_devices) == 0:
        print(f"No valid devices found for architecture N={arch.N}, K={arch.K}, K_A={arch.K_A}")
        return OptimizationResult(
            architecture=arch,
            default_loss=default_loss,
            optimized_hs_device=None,
            optimized_ls_device=None,
            optimized_f_sw=None,
            optimized_loss=float("inf")
        )
 
    best_loss = float("inf")
    best_hs = None
    best_ls = None
    best_f_sw = None
 
    for hs_device in hs_devices:
        for ls_device in ls_devices:
            for f_sw in f_sw_values:
                trial_inputs = LossModelInputs(
                    hs_device=hs_device,
                    ls_device=ls_device,
                    I_out=I_out,
                    L=L,
                    V_out=V_out,
                    V_in=V_in,
                    f_sw=f_sw,
                    V_gs_drive=V_gs_drive
                )
 
                loss = compute_total_loss(arch, trial_inputs)
 
                if loss < best_loss:
                    best_loss = loss
                    best_hs = hs_device
                    best_ls = ls_device
                    best_f_sw = f_sw
 
    return OptimizationResult(
        architecture=arch,
        default_loss=default_loss,
        optimized_hs_device=best_hs,
        optimized_ls_device=best_ls,
        optimized_f_sw=best_f_sw,
        optimized_loss=best_loss
    )
 
 
def optimize_all_architectures(architectures, df_devices, f_sw_values,
                               default_hs_device, default_ls_device, default_f_sw,
                               I_out, L, V_out, V_in, V_gs_drive):
    results = []
 
    for idx, arch in enumerate(architectures, start=1):
        print(f"Optimizing architecture {idx}/{len(architectures)}: N={arch.N}, K={arch.K}, K_A={arch.K_A}")
 
        hs_devices, ls_devices = filter_candidate_devices_for_architecture(
            df=df_devices,
            arch=arch,
            V_in=V_in,
            V_out=V_out,
            V_gs_drive=V_gs_drive,
            I_out=I_out
        )
 
        print(f"  Required HS VDSmax >= {V_in / arch.N:.2f} V")
        print(f"  Required device ID_A >= {I_out / arch.N:.2f} A")
        print(f"  Valid HS devices: {len(hs_devices)}")
        print(f"  Valid LS devices: {len(ls_devices)}")
 
        result = optimize_architecture(
            arch=arch,
            df_devices=df_devices,
            f_sw_values=f_sw_values,
            default_hs_device=default_hs_device,
            default_ls_device=default_ls_device,
            default_f_sw=default_f_sw,
            I_out=I_out,
            L=L,
            V_out=V_out,
            V_in=V_in,
            V_gs_drive=V_gs_drive
        )
        results.append(result)
 
    return results
 
 
# ============================================================
# 6) REPORTING
# ============================================================
 
def print_optimization_results(results):
    for res in results:
        arch = res.architecture
        print(f"\nArchitecture (N={arch.N}, K={arch.K}, K_A={arch.K_A})")
        print(f"Component count: {arch.component_count}")
        print(f"B_array: {arch.B_array}")
        print(f"Default loss: {res.default_loss:.4f} W")
 
        if res.optimized_hs_device is None or res.optimized_ls_device is None:
            print("No valid EPC device combination found under the applied constraints.")
            continue
 
        print(f"Optimized HS device: {res.optimized_hs_device.part_number}")
        print(f"Optimized LS device: {res.optimized_ls_device.part_number}")
        print(f"Optimized f_sw: {res.optimized_f_sw / 1e6:.3f} MHz")
        print(f"Optimized loss: {res.optimized_loss:.4f} W")
 
 
# ============================================================
# 7) VISUALIZATION
# ============================================================
 
def plot_default_vs_optimized(results):
    valid_results = [res for res in results if np.isfinite(res.optimized_loss)]
 
    if not valid_results:
        print("No valid optimization results to plot.")
        return
 
    x_labels = [
        f"({res.architecture.N},{res.architecture.K},{res.architecture.K_A})\n{res.architecture.component_count}"
        for res in valid_results
    ]
    default_losses = [res.default_loss for res in valid_results]
    optimized_losses = [res.optimized_loss for res in valid_results]
 
    plt.figure(figsize=(12, 7))
    plt.plot(range(len(valid_results)), default_losses, 'ro-', label='Default Loss')
    plt.plot(range(len(valid_results)), optimized_losses, 'bo-', label='Optimized Loss')
    plt.xticks(ticks=range(len(valid_results)), labels=x_labels, rotation=45, ha='right')
    plt.xlabel('Architecture (N,K,K_A) and Component Count')
    plt.ylabel('Loss (W)')
    plt.title('Loss Comparison: Default vs Optimized Architectures')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()
 
 
def plot_optimized_losses_with_params(results):
    valid_results = [
        res for res in results
        if res.optimized_hs_device is not None and res.optimized_ls_device is not None
    ]
 
    if not valid_results:
        print("No valid optimization results to plot.")
        return
 
    plt.figure(figsize=(14, 8))
 
    labels = [
        (f"N={res.architecture.N}, K={res.architecture.K}, K_A={res.architecture.K_A}\n"
         f"HS: {res.optimized_hs_device.part_number}, "
         f"LS: {res.optimized_ls_device.part_number}\n"
         f"f_sw: {res.optimized_f_sw / 1e6:.2f} MHz")
        for res in valid_results
    ]
 
    x_indices = np.arange(len(valid_results))
    bars = plt.bar(x_indices, [res.optimized_loss for res in valid_results])
 
    plt.xticks(x_indices, labels, rotation=90, ha='center', fontsize=8)
 
    for bar in bars:
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            height,
            f'{height:.2f} W',
            ha='center',
            va='bottom',
            rotation=45,
            fontsize=8
        )
 
    plt.ylabel('Optimized Loss (W)')
    plt.title('Optimized Losses with EPC Device Choices')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.subplots_adjust(bottom=0.4, top=0.95)
    plt.show()
# ============================================================
# 8) MAIN
# ============================================================
 
if __name__ == '__main__':
    # Topology-generation settings
    hs_weight = 1
    ls_weight = 1
    inductor_weight = 1
    capacitor_weight = 1
    target_component_count = 15
 
    # Electrical settings
    V_in = 48
    V_out = 1
    I_out = 30
    L = 440e-9
    default_f_sw = 500e3
    V_gs_drive = 5.0
 
    architectures = generate_architectures(
        hs_weight=hs_weight,
        ls_weight=ls_weight,
        inductor_weight=inductor_weight,
        capacitor_weight=capacitor_weight,
        target_component_count=target_component_count,
        V_out=V_out,
        V_in=V_in
    )
 
    print(f"Generated {len(architectures)} architectures")
 
    # Load EPC table
    df_devices = load_epc_devices(
        csv_path='EPC-Product-Table.csv',
        V_gs_op=V_gs_drive
    )
 
    # Frequency sweep
    f_sw_values = np.linspace(0.0430e6, 2e6, 40)
 
    # Default devices for baseline comparison
    default_hs_device = row_to_device(df_devices.iloc[0])
    default_ls_device = row_to_device(df_devices.iloc[0])
 
    results = optimize_all_architectures(
        architectures=architectures,
        df_devices=df_devices,
        f_sw_values=f_sw_values,
        default_hs_device=default_hs_device,
        default_ls_device=default_ls_device,
        default_f_sw=default_f_sw,
        I_out=I_out,
        L=L,
        V_out=V_out,
        V_in=V_in,
        V_gs_drive=V_gs_drive
    )
 
    print_optimization_results(results)
    plot_default_vs_optimized(results)
    plot_optimized_losses_with_params(results)
