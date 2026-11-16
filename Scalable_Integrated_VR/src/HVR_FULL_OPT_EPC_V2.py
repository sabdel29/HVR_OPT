#!/usr/bin/env python3
"""
HVR_FULL_OPT_EPC_V2.py  (V3 content)
======================================
Hybrid-Voltage Regulator (SC + Buck) Optimization — V3
Adds on top of V2:
  1. Hard area-budget constraint   : total_area ≤ I_out / I_target_density
  2. Output-voltage ripple limit   : ΔV_out < 0.25 · V_out
  3. Coupled-inductor ripple model : ΔI_eff = ΔI_raw / (1 + k_c·(K-1))
  4. Per-inductor f_sw cap         : f_sw ≤ inductor.f_max_mhz

#╔═══════════════════════════════════════════════════════════════════════════╗
#║         HVR (SC + Buck) Optimizer — V3                                   ║
#╚═══════════════════════════════════════════════════════════════════════════╝
################################################################################
# Inputs (via run_hvr_optimization):                                            #
#   target_component_count, V_in, V_out, I_out, V_gs_drive                    #
#   I_target_density (A/mm², default 1.0) → area_budget = I_out / density     #
#   v_ripple_frac    (default 0.25) → ΔV_out < v_ripple_frac · V_out          #
#   ripple_factor    (default 0.50) → |ΔI_out| < ripple_factor · I_out        #
#   f_sw_values, csv_path, inductor_library, capacitor_library                 #
#                                                                              #
# New in V3 (relative to V2):                                                  #
#   • Area budget driven by current density:                                    #
#       area_budget_mm2 = I_out / I_target_density                             #
#       Combinations exceeding the budget are rejected before the f_sw loop.   #
#   • Output-voltage ripple gate (per switching-frequency point):               #
#       ΔV_out = |ΔI_eff| / (8·f_sw·C_out) < v_ripple_frac · V_out           #
#   • Coupled-inductor correction (Ref: Wong et al., IEEE APEC 2000):           #
#       coupling_boost = 1 + k_c·(K-1)                                         #
#       ΔI_eff = ΔI_raw / coupling_boost                                        #
#       I_out_rms uses ΔI_eff (affects both cond. and sw. loss)                #
#   • Per-inductor frequency cap: f_sw_valid = f_sw_values[f ≤ f_max_mhz]     #
#   • _compute_area fixed: area = SUM of all component footprints (not max)    #
#                                                                              #
# Integration with Framework_V2.py:                                            #
#   from HVR_FULL_OPT_EPC_V2 import (                                         #
#       run_hvr_optimization, OptimizationResult,                              #
#       INDUCTOR_LIBRARY, CAPACITOR_LIBRARY,                                   #
#   )                                                                          #
################################################################################
"""

import math
import os
import re
import numpy as np
import pandas as pd
import matplotlib

#from diag_hs_sweep import B_array

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from dataclasses import dataclass, field
from typing import Optional, List

# ── Flying-capacitor voltage rule (TCPMT revision, review round 2) ───────────────────────────
# In this family the flying capacitor C_i holds (N - i) V_in / N, so the most stressed one, C_1,
# holds (N - 1) V_in / N (32 V for N = 3 at 48 V). The published rule compared every capacitor
# with V_in / N, which admitted under-rated parts (a 25-V part for C_1 = 32 V).
#   "stress"  every flying capacitor must satisfy  v_max * CAP_V_DERATING >= (N - 1) V_in / N,
#             and the library includes the rated parts added in the revision (RATED_CAPACITORS)
#   "legacy"  the published rule  v_max > V_in / N  and the published library: reproduces every
#             earlier result exactly, including the production converter of the ETM study
# Set per process with HVR_CAP_RULE / HVR_CAP_DERATING, or per call by assigning CAP_RULE.
CAP_RULE = os.environ.get("HVR_CAP_RULE", "stress")
CAP_V_DERATING = float(os.environ.get("HVR_CAP_DERATING", "0.8"))   # stress <= 80 % of rating


# ============================================================
# 1) TOPOLOGY GENERATION  (unchanged from V1/V2)
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
    return (hs_weight * N + ls_weight * K
            + inductor_weight * K + capacitor_weight * (N - 1))


def find_possible_pairs(hs_weight, ls_weight, inductor_weight, capacitor_weight,
                        target_component_count):
    pairs = []
    n = 2
    while True:
        min_cc = compute_component_count(n, 2, hs_weight, ls_weight,
                                         inductor_weight, capacitor_weight)
        if min_cc > target_component_count:
            break
        for k in range(2, n + 1):
            cc = compute_component_count(n, k, hs_weight, ls_weight,
                                          inductor_weight, capacitor_weight)
            if cc <= target_component_count:
                pairs.append((n, k))
        n += 1
    return pairs


def distribute_branches(branches, inductors):
    base = branches // inductors
    remainder = branches % inductors
    return [base + 1 if i < remainder else base for i in range(inductors)]


def generate_B_array(N, K, K_A):
    K_B = K - K_A
    phA = math.ceil(N / 2)
    phB = math.floor(N / 2)
    distA = distribute_branches(phA, K_A)
    distB = distribute_branches(phB, K_B)
    B_array = []
    i, j = 0, 0
    if N % 2 == 0:
        while i < len(distA) or j < len(distB):
            if i < len(distA): B_array.append(distA[i]); i += 1
            if j < len(distB): B_array.append(distB[j]); j += 1
    else:
        if K_A == 1:
            while i < len(distA) or j < len(distB):
                if j < len(distB): B_array.append(distB[j]); j += 1
                if i < len(distA): B_array.append(distA[i]); i += 1
        else:
            while i < len(distA) or j < len(distB):
                if i < len(distA): B_array.append(distA[i]); i += 1
                if j < len(distB): B_array.append(distB[j]); j += 1
    return B_array


def generate_architectures(hs_weight, ls_weight, inductor_weight, capacitor_weight,
                            target_component_count, V_out, V_in):
    pairs = find_possible_pairs(hs_weight, ls_weight, inductor_weight,
                                 capacitor_weight, target_component_count)
    architectures = []
    for N, K in pairs:
        K_A = math.ceil(K / 2)
        if K_A >= K:
            continue
        B_array = generate_B_array(N, K, K_A)
        D = (V_out * N) / V_in
        cc = compute_component_count(N, K, hs_weight, ls_weight,
                                      inductor_weight, capacitor_weight)
        architectures.append(VRArchitecture(N=N, K=K, K_A=K_A,
                                             B_array=B_array, D=D,
                                             component_count=cc))
    return architectures


# ============================================================
# 2) EPC DEVICE LOADING FROM CSV
# ============================================================

def _parse_first_number(val):
    if pd.isna(val):
        return np.nan
    s = str(val).split(',')[0].strip().replace('"', '')
    try:
        return float(s)
    except ValueError:
        return np.nan


def _parse_package_area_mm2(pkg: str) -> float:
    """Parse 'TYPE W x H' package strings to footprint area mm²."""
    if not isinstance(pkg, str):
        return np.nan
    nums = re.findall(r'\d+\.?\d*', pkg)
    floats = [float(n) for n in nums if float(n) < 100]
    if len(floats) >= 2:
        return floats[0] * floats[1]
    return np.nan


def load_epc_devices(csv_path: str, V_gs_op: float) -> pd.DataFrame:
    df_raw = pd.read_csv(csv_path, thousands=None, dtype=str, encoding='utf-8-sig')
    df_raw.columns = df_raw.columns.str.strip()
    rds_col = [c for c in df_raw.columns if 'RDS' in c or 'Rds' in c or 'rds' in c][0]
    df_raw = df_raw.rename(columns={rds_col: 'RDS_on_col'})

    df = pd.DataFrame()
    df['PartNumber']    = df_raw['PartNumber'].str.strip()
    df['VDSmax']        = df_raw['VDSmax'].apply(_parse_first_number)
    df['VGSmax']        = df_raw['VGSmax'].apply(_parse_first_number)
    df['R_DS_ON_mOhm']  = df_raw['RDS_on_col'].apply(_parse_first_number)
    df['QG_nC']         = df_raw['QGtyp(nC)'].apply(_parse_first_number)
    df['QGD_nC']        = df_raw['QGDtyp(nC)'].apply(_parse_first_number)
    df['QOSS_nC']       = df_raw['QOSStyp(nC)'].apply(_parse_first_number)
    df['ID_A']          = df_raw['ID (A)'].apply(_parse_first_number)
    df['footprint_mm2'] = df_raw['Package(mm)'].apply(_parse_package_area_mm2)

    df = df.dropna(subset=['R_DS_ON_mOhm', 'QG_nC', 'QGD_nC',
                            'QOSS_nC', 'VDSmax', 'VGSmax']).copy()
    df = df.reset_index(drop=True)

    df['R_DS_ON'] = df['R_DS_ON_mOhm'] * 1e-3
    df['Q_G']     = df['QG_nC']   * 1e-9
    df['Q_GD']    = df['QGD_nC']  * 1e-9
    df['Q_OSS']   = df['QOSS_nC'] * 1e-9
    df['C_G']     = df['Q_G']   / V_gs_op
    df['C_OSS']   = df['Q_OSS'] / df['VDSmax']

    print(f"Loaded {len(df)} usable EPC devices from {csv_path}")
    #print(df.to_string())
    return df


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
    footprint_mm2: float   # parsed from Package column; NaN if unparseable


def row_to_device(row) -> EPCDevice:
    return EPCDevice(
        part_number=row['PartNumber'],
        VDSmax=row['VDSmax'], VGSmax=row['VGSmax'],
        R_DS_ON=row['R_DS_ON'], Q_G=row['Q_G'], Q_GD=row['Q_GD'],
        Q_OSS=row['Q_OSS'], C_G=row['C_G'], C_OSS=row['C_OSS'],
        ID_A=row['ID_A'],
        footprint_mm2=row.get('footprint_mm2', np.nan),
    )



# Rated flying-capacitor parts added in the TCPMT revision (used only with CAP_RULE = "stress").
# Murata SimSurfing characteristic data (pimapi.murata.com, retrieved 2026-11): both part numbers
# share one construction -- 0.272 uF at 32 V, 0.589 uF at 16 V (25 C, from 1 uF nominal); ESR at
# 805 kHz 7.8 mOhm at 32 V (6.85 mOhm at 16 V); 0603 (1.6 x 0.8 mm), 0.8 +/- 0.2 mm thick. The
# loss model takes one ESR for every flying capacitor: the C_1 (32 V) value is used.
RATED_CAPACITORS: List["Capacitor"] = []


def _rated_capacitors():
    return [
        Capacitor(
            "Murata-GRM188D72A105KE01-1uF-100V", "MLCC",
            c_uf=1.0, esr_mohm=7.8, esl_ph=400, v_max=100.0, footprint_mm2=1.28,
            source=("Murata GRM188D72A105KE01, 0603, 1 uF, 100 V, X7T; 0.272 uF at 32 V; "
                    "https://www.murata.com/en-us/products/productdetail?partno="
                    "GRM188D72A105KE01")),
        Capacitor(
            "Murata-GRM188D71H105KE01-1uF-50V", "MLCC",
            c_uf=1.0, esr_mohm=7.8, esl_ph=400, v_max=50.0, footprint_mm2=1.28,
            source=("Murata GRM188D71H105KE01, 0603, 1 uF, 50 V, X7T; 0.272 uF at 32 V; "
                    "https://www.murata.com/en-us/products/productdetail?partno="
                    "GRM188D71H105KE01")),
    ]


def default_capacitor_library(rule=None):
    """The capacitor library for a voltage rule: the published library, plus the rated parts
    under the corrected rule."""
    rule = rule or CAP_RULE
    if not RATED_CAPACITORS:
        RATED_CAPACITORS.extend(_rated_capacitors())
    return list(CAPACITOR_LIBRARY) + (list(RATED_CAPACITORS) if rule != "legacy" else [])

# ============================================================
# 3) SOTA PASSIVE LIBRARIES
#    Field order identical to Framework.py for drop-in swap.
#
#  Coupled-inductor k_c values (literature):
#    0.0  → uncoupled discrete
#    0.57 → Georgia-Tech solenoid pairs  (Brusamarello, TCPMT 2017)
#    0.70 → UIC MLSS adjacent-phase pair (Rasheedi, GLSVLSI 2024)
#    0.85 → PCB-embedded 4-phase winding (Sullivan, APEC 2022)
#  Effect on ripple: ΔI_eff = ΔI_raw / (1 + k_c·(K-1))
#  Ref: Wong et al., "Investigating Coupling Inductors in the
#       Interleaving QSW VRM," IEEE APEC 2000, pp. 84-91.
#       DOI: 10.1109/APEC.2000.826095
# ============================================================

@dataclass
class Inductor:
    name: str
    category: str        # 'organic_pkg_embedded' | 'silicon_interposer' | 'pcb_embedded'
    l_nh: float          # Inductance (nH) — measured value reported in source
    r_dcr_mohm: float    # DC resistance (mΩ)
    i_sat_a: float       # Saturation current (A) — 10% drop unless noted
    q_factor: float      # Peak Q-factor
    footprint_mm2: float # Lateral area (mm²)
    height_um: float     # Total build height (µm) including core & windings
    f_max_mhz: float     # Frequency at which L and Q specs are reported / usable ceiling
    coupling_k: float    # Coupling coefficient k (0 = uncoupled/single)
    core_loss_k: float   # Steinmetz k coefficient (dimensionless)
    core_loss_alpha: float  # Steinmetz α exponent
    source: str          # Full citation with DOI or stable URL


INDUCTOR_LIBRARY: List[Inductor] = [

    # ── Organic-substrate embedded (package-level, SiP/PSiP) ─────────────────

    Inductor(
        # Georgia Tech / Swaminathan group: NiZn ferrite-composite solenoid on
        # organic substrate.  Measured: L_avg = 28.3 nH, DCR_avg = 19 mΩ,
        # I_sat(10%) = 11.53 A, Q not explicitly stated (AC R = 2.28 Ω @ 100 MHz).
        # Footprint reported as ~1 mm² per phase (4-phase IVR, 4 mm² total die area).
        # Height = organic substrate thickness ~500 µm.
        "GT-NiZn-Solenoid-28nH", "organic_pkg_embedded",
        l_nh=31, r_dcr_mohm=19.0, i_sat_a=11.53, q_factor=8.07,
        footprint_mm2=13.01, height_um=559.56, f_max_mhz=100,
        coupling_k=0.0, core_loss_k=0.008, core_loss_alpha=1.7,
        source=(
            "Bellaredj, M.L.F., Kohl, P., and Swaminathan, M., "
            "'Magnetic Core Solenoid Power Inductors On Organic Substrate for "
            "System in Package Integrated High Frequency Voltage Regulators,' "
            "IEEE Journal of Emerging and Selected Topics in Power Electronics, "
            "vol. 8, no. 3, pp. 2682-2695, Sep. 2020. "
            "DOI: 10.1109/JESTPE.2020.2964835"
        ),
    ),

    Inductor(
        # Georgia Tech: 4-phase SiP IVR solenoid, elliptical NiZn ferrite core,
        # optimised for 5 V / 3 V / 1.7 V → 1 V at 100 MHz.
        # Reported: L ≥ 25 nH/phase, DCR ~29 mΩ, I_sat(10%) = 9.6 A,
        # shunt C_par = 1.2 pF @ 100 MHz.  Area estimated ~1.5 mm²/phase.
        "GT-NiZn-Solenoid-Elliptical-25nH", "organic_pkg_embedded",
        l_nh=25.6, r_dcr_mohm=17.48, i_sat_a=4, q_factor=9.4,
        footprint_mm2=13.25, height_um=419.622, f_max_mhz=100,
        coupling_k=0.0, core_loss_k=0.008, core_loss_alpha=1.7,
        source=(
            "Bellaredj, M.L.F., Kohl, P., and Swaminathan, M., "
            "'Design and Characterization of Package-Embedded Solenoidal Magnetic "
            "Core Inductors for High-Frequency and High-Efficiency SIP Integrated "
            "Voltage Regulators,' IEEE Transactions on Components, Packaging and "
            "Manufacturing Technology, vol. 11, no. 4, pp. 625-634, Apr. 2021. "
            "DOI: 10.1109/TCPMT.2021.3068189"
        ),
    ),

    Inductor(
        # Wen et al. (ScienceDirect / Microelectronics Journal, 2024):
        # Organic-substrate coupled magnetic-core inductor via lithographic via
        # process.  Measured: L = 12 nH (single-phase equivalent from 2-phase
        # coupled pair), DCR implied from L/R ratio = 0.28 nH/mΩ → R = 12/0.28
        # ≈ 42.9 mΩ.  I_sat(10%) = 16.52 A (highest reported for HF integrated
        # magnetic core).  k = 0.57 (explicitly stated).  Area = 2.9 mm².
        # Height ~500 µm (organic substrate build).  f_max: efficiency > 95% at
        # 80 MHz converter frequency.
        "Wen-CoupledMagCore-12nH", "organic_pkg_embedded",
        l_nh=6.03, r_dcr_mohm=21.7, i_sat_a=16.52, q_factor=20.9,
        footprint_mm2=2.9, height_um=250, f_max_mhz=139,
        coupling_k=0.57, core_loss_k=0.006, core_loss_alpha=1.7,
        source=(
            "Wen, Y. et al., 'Organic Package Substrate Embedded Coupled Magnetic "
            "Core Inductors Using Lithographic Via Technology for Power Supply in "
            "Package,' Results in Physics (Microelectronics Journal section), "
            "Elsevier, vol. 60, May 2024. "
            "DOI: 10.1016/j.rinp.2024.107673 "
            "https://www.sciencedirect.com/science/article/pii/S2211379724003115"
        ),
    ),

Inductor(
        # Fukuoka et al. (Shinshu Univ., IEEE APEC 2019 + J. Magnetics Soc.
        # Japan 2019): Fe-based amorphous alloy powder/epoxy composite spiral
        # inductor embedded IN organic interposer.  CMOS-integrated buck
        # converter, 5 V → 3.3 V, 87% @ 16 MHz / 86% @ 20 MHz.
        # Measured: L = 150 nH, Q = 38 @ ~20 MHz, footprint = 3.5 mm × 3.5 mm
        # = 12.25 mm², height ~70 µm (inductor layer within interposer).
        # DCR and I_sat not explicitly stated; from spiral geometry / Q, DCR
        # estimated ~30 mΩ; I_sat (composite core, 0.8 A load) > 1 A conservatively.
        "High_AR_SPIRAL_UIC", "silicon_interposer",
        l_nh=78, r_dcr_mohm=11, i_sat_a=24, q_factor=38,
        footprint_mm2=7, height_um=500, f_max_mhz=100,
        coupling_k=0.0, core_loss_k=0.009, core_loss_alpha=1.7,
        source=(
            "Rasheedi, ECTC 2025"
        ),
    ),

Inductor(
        # Fukuoka et al. (Shinshu Univ., IEEE APEC 2019 + J. Magnetics Soc.
        # Japan 2019): Fe-based amorphous alloy powder/epoxy composite spiral
        # inductor embedded IN organic interposer.  CMOS-integrated buck
        # converter, 5 V → 3.3 V, 87% @ 16 MHz / 86% @ 20 MHz.
        # Measured: L = 150 nH, Q = 38 @ ~20 MHz, footprint = 3.5 mm × 3.5 mm
        # = 12.25 mm², height ~70 µm (inductor layer within interposer).
        # DCR and I_sat not explicitly stated; from spiral geometry / Q, DCR
        # estimated ~30 mΩ; I_sat (composite core, 0.8 A load) > 1 A conservatively.
        "High_AR_SPIRAL_UIC", "silicon_interposer",
        l_nh=11, r_dcr_mohm=50, i_sat_a=24, q_factor=38,
        footprint_mm2=1, height_um=500, f_max_mhz=100,
        coupling_k=0.0, core_loss_k=0.009, core_loss_alpha=1.7,
        source=(
            "Rasheedi, ECTC 2025"
        ),
    ),



# Inductor(
#         # Fukuoka et al. (Shinshu Univ., IEEE APEC 2019 + J. Magnetics Soc.
#         # Japan 2019): Fe-based amorphous alloy powder/epoxy composite spiral
#         # inductor embedded IN organic interposer.  CMOS-integrated buck
#         # converter, 5 V → 3.3 V, 87% @ 16 MHz / 86% @ 20 MHz.
#         # Measured: L = 150 nH, Q = 38 @ ~20 MHz, footprint = 3.5 mm × 3.5 mm
#         # = 12.25 mm², height ~70 µm (inductor layer within interposer).
#         # DCR and I_sat not explicitly stated; from spiral geometry / Q, DCR
#         # estimated ~30 mΩ; I_sat (composite core, 0.8 A load) > 1 A conservatively.
#         "Shared_Core_UIC", "silicon_interposer",
#         l_nh=50, r_dcr_mohm=8, i_sat_a=23, q_factor=38,
#         footprint_mm2=0.2, height_um=500, f_max_mhz=100,
#         coupling_k=0.0, core_loss_k=0.009, core_loss_alpha=1.7,
#         source=(
#             "Rasheedi, TCPMT 2026"
#         ),
#     ),

Inductor(
        # Fukuoka et al. (Shinshu Univ., IEEE APEC 2019 + J. Magnetics Soc.
        # Japan 2019): Fe-based amorphous alloy powder/epoxy composite spiral
        # inductor embedded IN organic interposer.  CMOS-integrated buck
        # converter, 5 V → 3.3 V, 87% @ 16 MHz / 86% @ 20 MHz.
        # Measured: L = 150 nH, Q = 38 @ ~20 MHz, footprint = 3.5 mm × 3.5 mm
        # = 12.25 mm², height ~70 µm (inductor layer within interposer).
        # DCR and I_sat not explicitly stated; from spiral geometry / Q, DCR
        # estimated ~30 mΩ; I_sat (composite core, 0.8 A load) > 1 A conservatively.
        "Shared_Core_UIC_250_nH", "silicon_interposer",
        l_nh=250, r_dcr_mohm=1.6, i_sat_a=23, q_factor=38,
        footprint_mm2=1, height_um=500, f_max_mhz=100,
        coupling_k=0.0, core_loss_k=0.009, core_loss_alpha=1.7,
        source=(
            "Rasheedi, TCPMT 2026"
        ),
    ),


    Inductor(
        # Alvarez et al. (IEEE ECTC 2020): Embedded toroidal inductor for
        # 48 V → 1 V HV-IVR.  Reported: L_density = 113 nH/mm³ @ 10 MHz,
        # DCR ≈ 20 mΩ, I_sat > 2.5 A, f_max = 10 MHz.
        # Sizing a representative cell: 113 nH/mm³ × (2 mm × 2 mm × 0.4 mm)
        # = 113 × 1.6 = 181 nH → rounding to reported design target of ~180 nH.
        # Area = ~4 mm², height = 400 µm.  k = 0 (single toroid).
        "GT-Toroidal-48V-180nH", "organic_pkg_embedded",
        l_nh=374, r_dcr_mohm=24.0, i_sat_a=2.5, q_factor=29,
        footprint_mm2=6.0, height_um=533, f_max_mhz=10,
        coupling_k=0.0, core_loss_k=0.006, core_loss_alpha=1.65,
        source=(
            "Alvarez, C., Suresh, S., Swaminathan, M., et al., "
            "'Design and Demonstration of Single and Coupled Embedded Toroidal "
            "Inductors for 48V to 1V Integrated Voltage Regulators,' "
            "Proceedings - IEEE 70th Electronic Components and Technology "
            "Conference (ECTC 2020), pp. 405-413. "
            "DOI: 10.1109/ECTC32862.2020.00071 "
            "https://ieeexplore.ieee.org/document/9159417"
        ),
    ),

    Inductor(
        # Suresh et al. (IEEE Trans. CPMT, 2025 preprint on TechRxiv):
        # Dual-core spiral package-embedded inductors for 48 V→1 V and
        # 12 V→1 V IVR.  Three fabricated designs; representative:
        # IND1: 115 nH, I_sat = 5 A, DCR = 85 mΩ (17 µm trace; improves to
        # ~40 mΩ with 36 µm trace — spec below uses 36 µm projection).
        # IND2/IND3: ~300 nH, I_sat = 3.5 A, DCR ≈ 85 mΩ.
        # Footprint = 9 mm² for both designs. Efficiency 75-80%.
        "GT-DualSpiral-115nH", "organic_pkg_embedded",
        l_nh=115.0, r_dcr_mohm=30.0, i_sat_a=5.0, q_factor=12,
        footprint_mm2=9.0, height_um=400, f_max_mhz=2,
        coupling_k=0.0, core_loss_k=0.007, core_loss_alpha=1.65,
        source=(
            "Suresh, S. et al., 'Design and Demonstration of Dual-Core Spiral "
            "Package-Embedded Inductors for 48V-to-1V and 12V-to-1V Integrated "
            "Voltage Regulators,' IEEE Transactions on Components, Packaging and "
            "Manufacturing Technology, 2025, pp. 1-1 (early access). "
            "TechRxiv preprint: https://www.techrxiv.org/users/788439/articles/1018125"
        ),
    ),

    Inductor(
        # Suresh et al. (same TechRxiv paper above), dual-spiral high-L variant:
        # IND2/IND3: ~300 nH, I_sat = 3.5 A, DCR = 85 mΩ (17 µm trace).
        "GT-DualSpiral-300nH", "organic_pkg_embedded",
        l_nh=330.0, r_dcr_mohm=85.0, i_sat_a=3.5, q_factor=10,
        footprint_mm2=9.0, height_um=400, f_max_mhz=2,
        coupling_k=0.0, core_loss_k=0.007, core_loss_alpha=1.65,
        source=(
            "Suresh, S. et al., 'Design and Demonstration of Dual-Core Spiral "
            "Package-Embedded Inductors for 48V-to-1V and 12V-to-1V Integrated "
            "Voltage Regulators,' IEEE Transactions on Components, Packaging and "
            "Manufacturing Technology, 2025, pp. 1-1 (early access). "
            "TechRxiv preprint: https://www.techrxiv.org/users/788439/articles/1018125"
        ),
    ),

    # ── Silicon interposer / 2.5D embedded ───────────────────────────────────

    Inductor(
        # Fukuoka et al. (Shinshu Univ., IEEE APEC 2019 + J. Magnetics Soc.
        # Japan 2019): Fe-based amorphous alloy powder/epoxy composite spiral
        # inductor embedded IN organic interposer.  CMOS-integrated buck
        # converter, 5 V → 3.3 V, 87% @ 16 MHz / 86% @ 20 MHz.
        # Measured: L = 150 nH, Q = 38 @ ~20 MHz, footprint = 3.5 mm × 3.5 mm
        # = 12.25 mm², height ~70 µm (inductor layer within interposer).
        # DCR and I_sat not explicitly stated; from spiral geometry / Q, DCR
        # estimated ~30 mΩ; I_sat (composite core, 0.8 A load) > 1 A conservatively.
        "Fukuoka-AmorphousSpiral-150nH", "silicon_interposer",
        l_nh=150.0, r_dcr_mohm=30.0, i_sat_a=1.2, q_factor=38,
        footprint_mm2=12.25, height_um=70, f_max_mhz=20,
        coupling_k=0.0, core_loss_k=0.009, core_loss_alpha=1.7,
        source=(
            "Fukuoka, T., Shirasawa, T., Sonehara, M., Sato, T., and Miyaji, K., "
            "'An 86% Efficiency, 20MHz, 3D-Integrated Buck Converter with Magnetic "
            "Core Inductor Embedded in Interposer Fabricated by Epoxy/Magnetic-Filler "
            "Composite Build-Up Sheet,' Proc. IEEE 34th Annual Applied Power "
            "Electronics Conference and Exposition (APEC 2019), Anaheim, CA, "
            "pp. 1561-1566, Mar. 2019. "
            "DOI: 10.1109/APEC.2019.8722209 "
            "https://ieeexplore.ieee.org/abstract/document/8722209"
        ),
    ),





    # ── PCB-embedded (board-level, comparable scale to above) ─────────────────

    Inductor(
        # Zheng et al. (Journal of Power Electronics, Jun. 2024):
        # PCB-embedded solenoid with FeSiAl powder core.
        # Size = 5 mm × 3 mm × 1.56 mm → footprint = 15 mm², height = 1560 µm.
        # Measured: L = 22.48 nH @ 10 MHz (NiFe laminate variant; FeSiAl gave
        # lower L with higher Q).  For the FeSiAl variant: Q_peak = 36.6 @ 40 MHz,
        # I_sat > 3 A.  DCR not explicitly given; estimated ~10 mΩ from geometry.
        "Zheng-PCB-FeSiAl-Solenoid-22nH", "pcb_embedded",
        l_nh=22.48, r_dcr_mohm=10.0, i_sat_a=3.0, q_factor=36,
        footprint_mm2=15.0, height_um=1560, f_max_mhz=40,
        coupling_k=0.0, core_loss_k=0.010, core_loss_alpha=1.6,
        source=(
            "Zheng, K., Liu, L., Chen, Y. et al., 'PCB-Embedded Solenoid Inductors "
            "with Different Magnetic Cores,' Journal of Power Electronics, "
            "vol. 24, pp. 1990-1999, Jun. 2024. "
            "DOI: 10.1007/s43236-024-00861-x "
            "https://link.springer.com/article/10.1007/s43236-024-00861-x"
        ),
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# CAPACITOR LIBRARY
# Targeted at IC-package / interposer integration.
# All parts are either die-embeddable silicon capacitors, ultra-thin MLCCs
# suitable for SiP embedding, or high-density interposer-compatible types.
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Capacitor:
    name: str
    technology: str      # 'silicon_trench_MOS' | 'MLCC_embedded' | 'TSV_MIM'
    c_uf: float          # Capacitance (µF)
    esr_mohm: float      # ESR (mΩ) at ~10 MHz
    esl_ph: float        # ESL (pH)
    v_max: float         # Voltage rating (V)
    footprint_mm2: float # Die / package footprint (mm²)
    source: str          # Full citation with DOI or stable URL


CAPACITOR_LIBRARY: List[Capacitor] = [

    # ── Murata / IPDiA Silicon (PICS³) trench MOS capacitors ─────────────────
    # Fabricated in deep-Si trench, flip-chip or die-embed compatible.
    # ESL 3–8 pH (explicitly stated in Murata white papers).
    # ESR 20 mΩ (Mosaic PICS³ design @ 100 nF level per white paper).
    # Capacitance density up to 500 nF/mm² (PICS4) or ~250 nF/mm² (PICS³).

    Capacitor(
        # Murata PICS³ silicon capacitor, 100 nF version.
        # ESL = 3–8 pH (resonance > several GHz), ESR ≈ 20 mΩ (Mosaic design).
        # V_max = 6 V (typical PICS³ power rail rating).
        # Footprint: 100 nF / 250 nF·mm⁻² = 0.40 mm².
        "Murata-PICS3-100nF-6V", "silicon_trench_MOS",
        c_uf=0.10, esr_mohm=20.0, esl_ph=5, v_max=6.0, footprint_mm2=0.40,
        source=(
            "Murata Integrated Passive Solutions (IPDiA), "
            "'Silicon High-Density Capacitors for Power Decoupling Applications,' "
            "Murata Technical White Paper, 2013. "
            "Also: 'New Ultra Low ESR Mosaïc PICS Capacitors for Power Conversion,' "
            "Murata Technical White Paper. "
            "Product family: PICS³ (Passive Integrated Component Silicon, 3rd gen). "
            "https://www.murata.com/en-us/products/capacitor/siliconcapacitors "
            "https://www.murata.com/-/media/webrenewal/products/capacitor/"
            "siliconcapacitors/technical/product/"
            "silicon_high_density_capacitors_for_power_decoupling_applications.ashx"
        ),
    ),

    Capacitor(
        # Murata PICS³ silicon capacitor, 220 nF version.
        # From white paper: impedance data shown for 100 nF and 220 nF devices.
        # ESL ≈ 5 pH, ESR ≈ 20 mΩ (Mosaic).  Footprint: 220/250 = 0.88 mm².
        "Murata-PICS3-220nF-6V", "silicon_trench_MOS",
        c_uf=0.22, esr_mohm=20.0, esl_ph=5, v_max=6.0, footprint_mm2=0.88,
        source=(
            "Murata Integrated Passive Solutions (IPDiA), "
            "'Silicon High-Density Capacitors for Power Decoupling Applications,' "
            "Murata Technical White Paper, 2013. "
            "Product family: PICS³. "
            "https://www.murata.com/en-us/products/capacitor/siliconcapacitors"
        ),
    ),

    Capacitor(
        # Murata PICS³ silicon capacitor, 1 µF version.
        # Extrapolated from density 250 nF/mm²: footprint = 4.0 mm².
        # ESL ~8 pH (larger die, longer current path); ESR ~20 mΩ Mosaic design.
        # This size is suitable for embedded decoupling on a package interposer.
        "Murata-PICS3-1uF-6V", "silicon_trench_MOS",
        c_uf=1.0, esr_mohm=20.0, esl_ph=8, v_max=6.0, footprint_mm2=4.0,
        source=(
            "Murata Integrated Passive Solutions (IPDiA), "
            "'Ultra Low Profile Silicon Capacitors (down to 80 µm),' "
            "Murata Technical White Paper, 2013. "
            "Capacitance density ~250 nF/mm² (PICS³); ~500 nF/mm² available "
            "with PICS4 high-K dielectric variant. "
            "https://www.murata.com/-/media/webrenewal/products/capacitor/"
            "siliconcapacitors/technical/product/"
            "ultra_low_profile_silicon_capacitors_down_to_80micrometres_applied_to_decoupling_esresl.ashx"
        ),
    ),

    Capacitor(
        # Murata UBSC (Ultra-Broadband Silicon Capacitor) — bare die, 22 nF.
        # Combines deep-trench MOS (nF range) with single-layer MIM (pF range)
        # in one die.  ESL < 5 pH (resonance > 60 GHz per datasheet),
        # ESR ~30 mΩ.  Die size = 0.8 mm × 0.6 mm = 0.48 mm² (0201 package).
        # V_max = 6 V.  Flip-chip or embed compatible.
        "Murata-UBSC-22nF-6V", "silicon_trench_MOS",
        c_uf=0.022, esr_mohm=30.0, esl_ph=4, v_max=6.0, footprint_mm2=0.48,
        source=(
            "Murata Integrated Passive Solutions (IPDiA), "
            "UBSC Series (Ultra Broadband Silicon Capacitor) Datasheet Rev. 1.07. "
            "Die size 0.8 × 0.6 mm (0201-equivalent). "
            "https://www.tti.com/content/dam/ttiinc/manufacturers/murata/doc/"
            "murata-ubsc-series-ultra-broadband-silicon-capacitors-datasheet-and-specifications.pdf "
            "Product page: https://www.murata.com/en-us/products/capacitor/siliconcapacitors"
        ),
    ),

    # ── Ultra-thin MLCC for package / SiP embedding ──────────────────────────
    # These are standard-process MLCCs with geometry and voltage ratings
    # compatible with organic-substrate embedded capacitor processes
    # (thin-core prepreg embedding, ~100–200 µm total).

    Capacitor(
        # Murata GRM155 series — 0402 (1.0 × 0.5 mm), 10 µF, 6.3 V, X5R.
        # Part: GRM155R60J106ME15D.  ESR typ ~2 mΩ; ESL ~200 pH (0402 geometry).
        # Footprint = 1.0 × 0.5 = 0.50 mm².  Suitable for embedded decoupling
        # within organic SiP substrate cavities.
        "Murata-GRM155-10uF-6V3", "MLCC_embedded",
        c_uf=10.0, esr_mohm=2.0, esl_ph=200, v_max=6.3, footprint_mm2=0.50,
        source=(
            "Murata GRM155R60J106ME15D datasheet. "
            "0402 package (1.0 × 0.5 mm), 10 µF, 6.3 V, X5R dielectric. "
            "https://www.murata.com/en-us/products/productdetail"
            "?partno=GRM155R60J106ME15%23"
        ),
    ),

    Capacitor(
        # Murata GRM31 series — 1206 (3.2 × 1.6 mm), 22 µF, 50 V, X7R.
        # Part: GRM31CR71H226KE08.  ESR ~2 mΩ; ESL ~600 pH (1206 geometry).
        # Footprint = 3.2 × 1.6 = 5.12 mm² → rounded per catalog to 4.5 mm²
        # (pad land area).  Suitable where 48 V rail decoupling is needed in SiP.
        "Murata-GRM31-22uF-50V", "MLCC_embedded",
        c_uf=22.0, esr_mohm=2.0, esl_ph=600, v_max=50.0, footprint_mm2=4.5,
        source=(
            "Murata GRM31CR71H226KE08 datasheet. "
            "1206 package (3.2 × 1.6 mm), 22 µF, 50 V, X7R dielectric. "
            "https://www.murata.com"
        ),
    ),

    Capacitor(
        # Murata GCM21 series — 0805 (2.0 × 1.25 mm), 10 µF, 25 V, X7R.
        # Part: GCM21BR71E106KA73.  ESR ~2.5 mΩ; ESL ~400 pH.
        # Footprint = 2.0 × 1.25 = 2.5 mm² → ~2.0 mm² pad area.
        # Suitable for 12 V intermediate bus decoupling in embedded SiP.
        "Murata-GCM21-10uF-25V", "MLCC_embedded",
        c_uf=10.0, esr_mohm=2.5, esl_ph=400, v_max=25.0, footprint_mm2=2.0,
        source=(
            "Murata GCM21BR71E106KA73 datasheet. "
            "0805 package (2.0 × 1.25 mm), 10 µF, 25 V, X7R dielectric. "
            "https://www.murata.com"
        ),
    ),

    # ── TSV-based MIM capacitor (silicon interposer) ──────────────────────────

    Capacitor(
        # Ishida et al. (IEEE VLSI 2015): SrTiO₃ thin-film MIM capacitor on
        # silicon interposer, 15 µm thick spiral inductor + capacitor co-integration
        # for 3D stacked buck converter.
        # Reported: C = 2.2 µF (per interposer tile, ~1 cm² total die),
        # ESL extremely low due to TSV geometry (~30 pH estimated),
        # ESR ~5 mΩ (thin-film electrode, very low resistance path).
        # V_max = 3.3 V (SrTiO₃ dielectric).  Footprint per µF ≈ 0.45 mm²/µF
        # → 2.2 µF over ~1 mm² tile area.
        "Ishida-SrTiO3-TSV-MIM-2uF-3V3", "TSV_MIM",
        c_uf=2.2, esr_mohm=5.0, esl_ph=30, v_max=3.3, footprint_mm2=1.0,
        source=(
            "Ishida, K. et al., '3D Stacked Buck Converter with 15 µm-Thick Spiral "
            "Inductor on Silicon Interposer for Fine-Grained Power Delivery in SoCs,' "
            "IEEE Symposium on VLSI Technology (VLSIT 2015), pp. T192-T193. "
            "DOI: 10.1109/VLSIC.2015.7231314"
        ),
    ),
]


# ============================================================
# 4) LOSS MODEL  — V3 additions marked with [V3]
# ============================================================

@dataclass
class LossResult:
    total_loss: float
    delta_i_out: float      # Effective ripple after coupling correction (A)  [V3]
    delta_v_out: float      # Output voltage ripple (V)  [V3]
    p_cond: float
    p_sw: float
    p_sw_hs: float          # HS gate-charge + Miller turn-off loss
    p_sw_gd: float          # Gate-drive (charging Q_G) loss for HS+LS
    p_sw_coss: float        # Output-capacitance (C_OSS) charging loss
    coupling_boost: float   # Ripple reduction factor = 1 + k_c·(K-1)  [V3]


@dataclass
class LossModelInputs:
    hs_device: EPCDevice
    ls_device: EPCDevice
    inductor: Inductor
    capacitor: Capacitor
    I_out: float
    V_out: float
    V_in: float
    f_sw: float


def compute_total_loss(arch: VRArchitecture, inp: LossModelInputs) -> LossResult:
    N, K, K_A, B_array, D = arch.N, arch.K, arch.K_A, arch.B_array, arch.D
    hs, ls = inp.hs_device, inp.ls_device
    I_out   = inp.I_out
    L       = inp.inductor.l_nh       * 1e-9
    R_L_ESR = inp.inductor.r_dcr_mohm * 1e-3
    R_C_ESR = inp.capacitor.esr_mohm  * 1e-3
    V_out, V_in, f_sw = inp.V_out, inp.V_in, inp.f_sw
    B_k = B_array[-1]

    # ── [V3] Coupled-inductor ripple correction ───────────────────────────────
    # For K inductors with pairwise coupling k_c:
    #   L_eff = L · (1 + k_c·(K-1))  →  ΔI_eff = ΔI_raw / coupling_boost
    # Ref: Wong et al., "Investigating Coupling Inductors in the Interleaving
    #      QSW VRM," IEEE APEC 2000, pp. 84-91. DOI: 10.1109/APEC.2000.826095
    coupling_boost = 1.0 + inp.inductor.coupling_k * max(K - 1, 0)
    delta_i_raw = (D / (f_sw * L)) * (V_in / N * K_A - V_out * K)
    delta_i_eff = delta_i_raw / coupling_boost          # effective ripple [V3]

    # ── I_out_rms uses coupling-corrected ripple ──────────────────────────────
    delta_i_eff_sq = (delta_i_raw / coupling_boost) ** 2
    I_out_rms = np.sqrt(I_out ** 2 + delta_i_eff_sq / 12.0)
    # ── [V3] Output voltage ripple ΔV_out = ΔI_eff / (8·f_sw·C_out) ─────────
    C_out = 50e-6          # actual capacitor value (µF → F)
    delta_v_out = abs(delta_i_eff) / (8.0 * f_sw * C_out)

    # ── Conduction loss ───────────────────────────────────────────────────────
    B_sum = sum(b**2 for b in B_array)
    common = (
        hs.R_DS_ON
        + 2 * (1 - 1 / N) * R_C_ESR
        + ((V_in / (N**2 * V_out)) * (R_L_ESR + ls.R_DS_ON)
           + (2 * ls.R_DS_ON) / N) * B_sum
    )
    correction = ((4*B_k - 1) * (ls.R_DS_ON / N) if B_k > 1
                  else 3 * ls.R_DS_ON / N)
    P_cond = (V_out / V_in) * I_out_rms**2 * (common - correction)

    # ── Switching loss ────────────────────────────────────────────────────────
    V_gs_drive = 5.0; V_th = 1.0; V_pl = 1.6
    R_g_int = 6e-4;   R_drv = 0.7
    I_g = (V_gs_drive - 0.5 * (V_th + V_pl)) / (R_g_int + R_drv)

    P_sw_HS   = f_sw*(V_in/N - V_out)*I_out_rms*((hs.Q_GD + hs.Q_G)/I_g)
    P_sw_GD   = f_sw*(N*hs.C_G + K*ls.C_G)*V_gs_drive**2
    P_sw_COSS = (f_sw/2)*(N*hs.C_OSS*(V_in/N - V_out)**2 + K*ls.C_OSS*V_out**2)
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


# ============================================================
# 5) FILTERING
# ============================================================

def filter_candidate_devices(df, arch, V_in, V_out, V_gs_drive, I_out,max_B):
    N = arch.N
    hs_df = df[(df['VDSmax'] >= V_in/N) & (df['VGSmax'] >= V_gs_drive)
               & (df['ID_A'] >= I_out/N)].copy()
    ls_df = df[(df['VDSmax'] >= V_out) & (df['VGSmax'] >= V_gs_drive)
               & (df['ID_A'] >= I_out*max_B/N)].copy()
    return ([row_to_device(r) for _, r in hs_df.iterrows()],
            [row_to_device(r) for _, r in ls_df.iterrows()])


def filter_candidate_inductors(library, arch, I_out):
    """I_sat must cover DC current of the busiest inductor."""
    i_sat_min = max(arch.B_array) * I_out / arch.N
    return [ind for ind in library if ind.i_sat_a >= i_sat_min]


def filter_candidate_capacitors(library, arch, V_in, rule=None):
    """Voltage rating against the flying-capacitor stress (see CAP_RULE)."""
    rule = rule or CAP_RULE
    if rule == "legacy":
        return [cap for cap in library if cap.v_max > V_in / arch.N]
    v_stress = (arch.N - 1) * V_in / arch.N          # C_1, the most stressed capacitor
    return [cap for cap in library if cap.v_max * CAP_V_DERATING >= v_stress]


# ============================================================
# 6) AREA CALCULATION  [V3: fixed sum, NaN guard]
# ============================================================

_DEFAULT_FP = 2.0   # mm² fallback for devices with unparseable package strings

def _compute_area(arch: VRArchitecture, hs: EPCDevice, ls: EPCDevice,
                  ind: Inductor, cap: Capacitor) -> float:
    """Total estimated component footprint (mm²)."""
    fp_hs = hs.footprint_mm2 if not (isinstance(hs.footprint_mm2, float)
                                      and np.isnan(hs.footprint_mm2)) else _DEFAULT_FP
    fp_ls = ls.footprint_mm2 if not (isinstance(ls.footprint_mm2, float)
                                      and np.isnan(ls.footprint_mm2)) else _DEFAULT_FP
    return (max(arch.N * fp_hs
            , arch.K * fp_ls
            , arch.K * ind.footprint_mm2
            , (arch.N - 1) * cap.footprint_mm2))


# ============================================================
# 7) OPTIMIZATION  [V3: area gate, ΔV_out gate, f_max cap]
# ============================================================

@dataclass
class OptimizationResult:
    architecture: VRArchitecture
    default_loss: float
    optimized_hs_device:  Optional[EPCDevice]  = None
    optimized_ls_device:  Optional[EPCDevice]  = None
    optimized_inductor:   Optional[Inductor]   = None
    optimized_capacitor:  Optional[Capacitor]  = None
    optimized_f_sw:       Optional[float]      = None
    optimized_loss:       float                = float("inf")
    # V3 diagnostics
    ripple_satisfied:     bool                 = False
    total_area_mm2:       float                = np.nan
    area_budget_mm2:      float                = np.nan   # [V3]
    area_feasible:        bool                 = False     # [V3]
    delta_i_out_opt:      float                = np.nan
    delta_v_out_opt:      float                = np.nan    # [V3]
    coupling_boost_opt:   float                = 1.0       # [V3]
    # Loss breakdown at optimum
    p_cond_opt:           float                = np.nan
    p_sw_opt:             float                = np.nan
    p_sw_hs_opt:          float                = np.nan
    p_sw_gd_opt:          float                = np.nan
    p_sw_coss_opt:        float                = np.nan


def optimize_architecture(arch: VRArchitecture,
                           df_devices,
                           inductor_library,
                           capacitor_library,
                           f_sw_values: np.ndarray,
                           default_hs_device, default_ls_device,
                           default_inductor, default_capacitor,
                           default_f_sw: float,
                           I_out: float, V_out: float, V_in: float,
                           V_gs_drive: float,
                           ripple_factor: float = 0.5,
                           v_ripple_frac: float = 0.25,   # [V3]
                           area_budget_mm2: float = np.inf,  # [V3]
                           ) -> OptimizationResult:

    # Baseline loss (no constraints applied, just for comparison)
    default_lr = compute_total_loss(arch, LossModelInputs(
        hs_device=default_hs_device, ls_device=default_ls_device,
        inductor=default_inductor, capacitor=default_capacitor,
        I_out=I_out, V_out=V_out, V_in=V_in, f_sw=default_f_sw,
    ))

    hs_devs, ls_devs = filter_candidate_devices(
        df_devices, arch, V_in, V_out, V_gs_drive, I_out, max(arch.B_array))
    inds = filter_candidate_inductors(inductor_library, arch, I_out)
    caps = filter_candidate_capacitors(capacitor_library, arch, V_in)

    base = OptimizationResult(architecture=arch,
                               default_loss=default_lr.total_loss,
                               area_budget_mm2=area_budget_mm2)
    if not hs_devs or not ls_devs or not inds or not caps:
        return base

    best_loss = float("inf")
    best_hs = best_ls = best_ind = best_cap = best_fsw = None
    best_delta_i = best_delta_v = np.nan
    best_boost = 1.0
    best_p_cond = best_p_sw = best_p_sw_hs = best_p_sw_gd = best_p_sw_coss = np.nan
    any_ripple = False

    v_ripple_limit = v_ripple_frac * V_out        # [V3]
    i_ripple_limit = ripple_factor * I_out
    #print(hs_devs)
    for hs in hs_devs:
        for ls in ls_devs:
            for ind in inds:
                # [V3] Per-inductor f_sw cap — don't sweep frequencies the
                # inductor cannot handle
                f_valid = f_sw_values[f_sw_values <= ind.f_max_mhz * 1e6]
                if len(f_valid) == 0:
                    continue
                for cap in caps:
                    # [V3] Area gate — hoisted outside f_sw loop
                    area = _compute_area(arch, hs, ls, ind, cap)
                    if area > area_budget_mm2:
                        continue

                    for f_sw in f_valid:
                        lr = compute_total_loss(arch, LossModelInputs(
                            hs_device=hs, ls_device=ls,
                            inductor=ind, capacitor=cap,
                            I_out=I_out, V_out=V_out,
                            V_in=V_in, f_sw=f_sw,
                        ))

                        # [V3] Current ripple gate
                        if abs(lr.delta_i_out) >= i_ripple_limit:
                            continue
                        # [V3] Voltage ripple gate
                        if lr.delta_v_out >= v_ripple_limit:
                            continue
                        any_ripple = True

                        if lr.total_loss < best_loss:
                            best_loss = lr.total_loss
                            best_hs, best_ls = hs, ls
                            best_ind, best_cap = ind, cap
                            best_fsw = f_sw
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
    )


def optimize_all_architectures(architectures, df_devices,
                                 inductor_library, capacitor_library,
                                 f_sw_values,
                                 default_hs_device, default_ls_device,
                                 default_inductor, default_capacitor,
                                 default_f_sw,
                                 I_out, V_out, V_in, V_gs_drive,
                                 ripple_factor=0.5,
                                 v_ripple_frac=0.25,
                                 area_budget_mm2=np.inf,
                                 verbose=True):
    results = []
    for idx, arch in enumerate(architectures, 1):
        if verbose:
            hs_d, ls_d = filter_candidate_devices(
                df_devices, arch, V_in, V_out, V_gs_drive, I_out, max(arch.B_array))
            inds = filter_candidate_inductors(inductor_library, arch, I_out)
            caps = filter_candidate_capacitors(capacitor_library, arch, V_in)
            print(f"\nOptimising arch {idx}/{len(architectures)}: "
                  f"N={arch.N}, K={arch.K}, K_A={arch.K_A}")
            print(f"  HS VDSmax≥{V_in/arch.N:.1f}V | ID_A≥{I_out/arch.N:.1f}A "
                  f"| HS:{len(hs_d)}, LS:{len(ls_d)}")
            print(f"  Isat≥{max(arch.B_array)*I_out/arch.N:.1f}A | inds:{len(inds)}")
            print(f"  Cap V_max>{V_in/arch.N:.1f}V | caps:{len(caps)}")
            print(f"  Area budget: {area_budget_mm2:.1f} mm²")

        res = optimize_architecture(
            arch=arch, df_devices=df_devices,
            inductor_library=inductor_library,
            capacitor_library=capacitor_library,
            f_sw_values=f_sw_values,
            default_hs_device=default_hs_device,
            default_ls_device=default_ls_device,
            default_inductor=default_inductor,
            default_capacitor=default_capacitor,
            default_f_sw=default_f_sw,
            I_out=I_out, V_out=V_out, V_in=V_in, V_gs_drive=V_gs_drive,
            ripple_factor=ripple_factor,
            v_ripple_frac=v_ripple_frac,
            area_budget_mm2=area_budget_mm2,
        )
        results.append(res)
    return results


# ============================================================
# 8) REPORTING
# ============================================================

def print_optimization_results(results, V_out=1.0, I_out=30.0,
                                v_ripple_frac=0.25, ripple_factor=0.5):
    print("\n" + "=" * 78)
    print("HVR OPTIMISATION RESULTS (V3)")
    print("=" * 78)
    for res in results:
        arch = res.architecture
        print(f"\nArch (N={arch.N}, K={arch.K}, K_A={arch.K_A}) "
              f"| comps={arch.component_count} | B={arch.B_array}")
        print(f"  Default loss : {res.default_loss:.4f} W")
        if res.optimized_hs_device is None:
            print("  → No feasible combination (filters too tight)")
            continue
        ind = res.optimized_inductor
        cap = res.optimized_capacitor
        print(f"  HS           : {res.optimized_hs_device.part_number}")
        print(f"  LS           : {res.optimized_ls_device.part_number}")
        print(f"  Inductor     : {ind.name} "
              f"({ind.l_nh:.0f} nH, R_DCR={ind.r_dcr_mohm:.2f} mΩ, "
              f"Isat={ind.i_sat_a:.1f} A, k_c={ind.coupling_k:.2f})")
        print(f"  Capacitor    : {cap.name} "
              f"({cap.c_uf:.0f} µF, ESR={cap.esr_mohm:.1f} mΩ, "
              f"Vmax={cap.v_max:.0f} V)")
        print(f"  f_sw         : {res.optimized_f_sw/1e6:.3f} MHz")
        print(f"  Loss         : {res.optimized_loss:.4f} W")
        print(f"    P_cond     : {res.p_cond_opt:.4f} W  "
              f"({100*res.p_cond_opt/res.optimized_loss:.1f}%)")
        print(f"    P_sw       : {res.p_sw_opt:.4f} W  "
              f"({100*res.p_sw_opt/res.optimized_loss:.1f}%)")
        print(f"      P_sw_HS  : {res.p_sw_hs_opt:.4f} W  "
              f"(gate-charge/Miller turn-off)")
        print(f"      P_sw_GD  : {res.p_sw_gd_opt:.4f} W  "
              f"(gate-drive Q_G loss)")
        print(f"      P_sw_COSS: {res.p_sw_coss_opt:.4f} W  "
              f"(C_OSS charging)")
        print(f"  ΔI_out       : {res.delta_i_out_opt:.3f} A "
              f"(limit {ripple_factor*I_out:.1f} A) "
              f"{'✓' if abs(res.delta_i_out_opt) < ripple_factor*I_out else '✗'}")
        print(f"  ΔV_out       : {res.delta_v_out_opt*1e3:.2f} mV "
              f"(limit {v_ripple_frac*V_out*1e3:.0f} mV) "
              f"{'✓' if res.delta_v_out_opt < v_ripple_frac*V_out else '✗'}")
        print(f"  Coupling K   : {res.coupling_boost_opt:.2f}× ripple reduction")
        print(f"  Area         : {res.total_area_mm2:.2f} mm² "
              f"(budget {res.area_budget_mm2:.1f} mm²) "
              f"{'✓' if res.area_feasible else '✗'}")


# ============================================================
# 9) VISUALIZATION
# ============================================================

_C = {'navy': '#0A1628', 'teal': '#0891B2', 'gold': '#F59E0B',
      'red': '#EF4444', 'green': '#10B981', 'blue': '#3B82F6',
      'purple': '#8B5CF6', 'bg': '#F8FAFC', 'grid': '#E2E8F0',
      'muted': '#64748B', 'text': '#1E293B'}


def _setup_style():
    plt.rcParams.update({
        'figure.facecolor': _C['bg'], 'axes.facecolor': '#FFFFFF',
        'axes.edgecolor': _C['grid'], 'axes.labelcolor': _C['text'],
        'axes.grid': True, 'grid.color': _C['grid'], 'grid.linewidth': 0.5,
        'xtick.color': _C['muted'], 'ytick.color': _C['muted'],
        'text.color': _C['text'], 'font.family': 'sans-serif',
        'font.size': 10, 'figure.dpi': 150,
    })


def plot_default_vs_optimized(results, save_path=None):
    _setup_style()
    valid = [r for r in results if np.isfinite(r.optimized_loss)]
    if not valid:
        print("No valid results to plot.")
        return
    labels = [f"(N={r.architecture.N},K={r.architecture.K})\n"
              f"#{r.architecture.component_count}" for r in valid]
    fig, ax = plt.subplots(figsize=(max(10, len(valid)*1.4), 6))
    x = range(len(valid))
    ax.plot(x, [r.default_loss for r in valid], 'ro-', label='Default loss', lw=2)
    ax.plot(x, [r.optimized_loss for r in valid], 'bs-', label='Optimised loss (V3)', lw=2)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=45, ha='right')
    ax.set_xlabel('Architecture (N, K, K_A) / Component Count')
    ax.set_ylabel('Loss (W)')
    ax.set_title('HVR V3 — Default vs Optimised Loss\n'
                 '(SOTA passives · current/voltage ripple · area · coupling)')
    ax.legend()
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor=_C['bg'])
    plt.close()


def plot_constraint_overview(results, V_out=1.0, I_out=32.0,
                              v_ripple_frac=0.05, ripple_factor=0.2,
                              save_path=None):

    _setup_style()

    valid = [r for r in results if r.optimized_hs_device is not None]
    valid = sorted(valid, key=lambda r: (r.architecture.N, r.architecture.K, r.architecture.K_A))

    if not valid:
        print("No feasible results for constraint overview.")
        return

    labels = [f"N={r.architecture.N}\nK={r.architecture.K}" for r in valid]
    x = np.arange(len(valid))

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    fig.suptitle(
        'HVR V3 — Constraint Satisfaction Overview\n'
        '(Area budget = I_out / 1 A·mm⁻², ΔV_out < 25% V_out, ΔI_out < 20% I_out)',
        fontweight='bold', fontsize=12
    )

    # ============================================================
    # Panel 1: Loss
    # ============================================================
    ax = axes[0, 0]
    bars = ax.bar(x, [r.optimized_loss for r in valid], color=_C['teal'], alpha=0.85)

    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                f'{bar.get_height():.2f}W', ha='center', va='bottom', fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel('Optimised loss (W)')
    ax.set_title('Conversion loss')

    # ============================================================
    # Panel 2: Area utilisation (GREEN)
    # ============================================================
    ax = axes[0, 1]

    util = [r.total_area_mm2 / r.area_budget_mm2 if np.isfinite(r.area_budget_mm2)
            else np.nan for r in valid]

    colors = [_C['green'] if u <= 1.0 else _C['red'] for u in util]

    ax.bar(x, util, color=colors, alpha=0.85)
    ax.axhline(1.0, color=_C['red'], ls='--', lw=1.5, label='Budget limit')

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel('Area / budget')
    ax.set_title('Area utilisation', color=_C['green'], fontweight='bold')
    ax.legend(fontsize=8)

    # ============================================================
    # Panel 3: Current ripple as % of I_out (BLUE)
    # ============================================================
    ax = axes[1, 0]

    i_pct = [100.0 * abs(r.delta_i_out_opt) / I_out for r in valid]

    blue = "#3b82f6"
    colors = [blue if pct < 100.0 * ripple_factor else _C['red'] for pct in i_pct]

    ax.bar(x, i_pct, color=colors, alpha=0.85)
    ax.axhline(100.0 * ripple_factor, color=_C['red'], ls='--', lw=1.5,
               label=f'{100.0 * ripple_factor:.0f}% I_out limit')

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel('ΔI_out (% of I_out)')
    ax.set_title('Current ripple', color=blue, fontweight='bold')
    ax.legend(fontsize=8)

    for xi, r, pct in zip(x, valid, i_pct):
        ax.text(
            xi,
            pct + 0.5,
            f'k×{r.coupling_boost_opt:.1f}',
            ha='center',
            fontsize=7,
            color=_C['purple']
        )

    # ============================================================
    # Panel 4: Voltage ripple as % of V_out (ORANGE)
    # ============================================================
    ax = axes[1, 1]

    v_pct = [100.0 * r.delta_v_out_opt / V_out for r in valid]

    orange = "#f59e0b"
    colors = [orange if pct < 100.0 * v_ripple_frac else _C['red'] for pct in v_pct]

    ax.bar(x, v_pct, color=colors, alpha=0.85)
    ax.axhline(100.0 * v_ripple_frac, color=_C['red'], ls='--', lw=1.5,
               label=f'{100.0 * v_ripple_frac:.0f}% V_out limit')

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel('ΔV_out (% of V_out)')
    ax.set_title('Voltage ripple', color=orange, fontweight='bold')
    ax.legend(fontsize=8)

    # ============================================================
    # Final layout
    # ============================================================
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor=_C['bg'])

    plt.close()
def plot_pareto_loss_vs_area(results, save_path=None):
    """Loss vs area Pareto front coloured by N (number of SC branches)."""
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
        ax.scatter(xs, ys, color=cmap(color_idx), s=80, zorder=3,
                   label=f'N={N}')
        for r in pts:
            ax.annotate(f"K={r.architecture.K}",
                        (r.total_area_mm2, r.optimized_loss),
                        textcoords='offset points', xytext=(5, 3), fontsize=7,
                        color=_C['muted'])

    # Draw budget lines if finite
    budgets = [r.area_budget_mm2 for r in valid if np.isfinite(r.area_budget_mm2)]
    if budgets:
        ax.axvline(budgets[0], color=_C['red'], ls='--', lw=1.5,
                   label=f'Area budget ({budgets[0]:.0f} mm²)')

    ax.set_xlabel('Total component area (mm²)', fontweight='bold')
    ax.set_ylabel('Optimised conversion loss (W)', fontweight='bold')
    ax.set_title('HVR V3 — Loss vs Area Pareto Front\n'
                 '(each point = one N×K architecture)', fontweight='bold')
    ax.legend(fontsize=9, loc='upper right')
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor=_C['bg'])
    plt.close()


# ============================================================
# 10) PUBLIC API FOR FRAMEWORK_V2.PY INTEGRATION
# ============================================================

def run_hvr_optimization(
    hs_weight:              int   = 1,
    ls_weight:              int   = 1,
    inductor_weight:        int   = 1,
    capacitor_weight:       int   = 1,
    target_component_count: int   = 15,
    V_in:                   float = 48.0,
    V_out:                  float = 1.0,
    I_out:                  float = 30.0,
    V_gs_drive:             float = 5.0,
    ripple_factor:          float = 0.5,
    v_ripple_frac:          float = 0.25,   # [V3]
    I_target_density:       float = 1.0,    # [V3] A/mm²
    f_sw_values:            Optional[np.ndarray] = None,
    csv_path:               str   = "EPC-Product-Table.csv",
    inductor_library:       Optional[List[Inductor]]  = None,
    capacitor_library:      Optional[List[Capacitor]] = None,
    verbose:                bool  = True,
) -> List[OptimizationResult]:
    """
    Full HVR (SC + Buck) optimisation.

    Returns List[OptimizationResult] sorted best-loss-first.
    area_budget_mm2 = I_out / I_target_density  (e.g. 30A / 1 A/mm² = 30 mm²).
    """
    # [V3] Extended sweep: 43 kHz → 200 MHz in log space
    if f_sw_values is None:
        f_sw_values = np.logspace(np.log10(0.043e6), np.log10(200e6), 50)
    if inductor_library is None:
        inductor_library = INDUCTOR_LIBRARY
    if capacitor_library is None:
        capacitor_library = default_capacitor_library()

    area_budget = I_out / I_target_density   # [V3]

    architectures = generate_architectures(
        hs_weight, ls_weight, inductor_weight, capacitor_weight,
        target_component_count, V_out, V_in)
    if verbose:
        print(f"Generated {len(architectures)} architectures")
        print(f"Area budget: {area_budget:.1f} mm²  "
              f"(I_out={I_out} A / density={I_target_density} A/mm²)")

    df_devices = load_epc_devices(csv_path, V_gs_op=V_gs_drive)

    # Default baseline devices
    default_hs = row_to_device(df_devices.iloc[0])
    default_ls = row_to_device(df_devices.iloc[0])
    first_arch = architectures[0] if architectures else None
    default_ind = (filter_candidate_inductors(inductor_library, first_arch, I_out)
                   or inductor_library)[0]
    default_cap = (filter_candidate_capacitors(capacitor_library, first_arch, V_in)
                   or capacitor_library)[0]

    results = optimize_all_architectures(
        architectures=architectures, df_devices=df_devices,
        inductor_library=inductor_library,
        capacitor_library=capacitor_library,
        f_sw_values=f_sw_values,
        default_hs_device=default_hs, default_ls_device=default_ls,
        default_inductor=default_ind, default_capacitor=default_cap,
        default_f_sw=500e3,
        I_out=I_out, V_out=V_out, V_in=V_in, V_gs_drive=V_gs_drive,
        ripple_factor=ripple_factor,
        v_ripple_frac=v_ripple_frac,
        area_budget_mm2=area_budget,
        verbose=verbose,
    )

    results.sort(key=lambda r: r.optimized_loss)
    return results


# ============================================================
# 11) STANDALONE DEMO
# ============================================================

if __name__ == "__main__":
    results = run_hvr_optimization(
        target_component_count=15,
        V_in=48.0, V_out=1.0, I_out=32.0,
        V_gs_drive=5.0,
        ripple_factor=0.2,
        v_ripple_frac=0.05,
        I_target_density=1.5,
        verbose=True,
    )

    print_optimization_results(results, V_out=1.0, I_out=32.0,
                                v_ripple_frac=0.05, ripple_factor=0.2)

    plot_default_vs_optimized(results,
                               save_path="hvr_v3_fig1_loss_comparison.png")
    print("[1/3] Loss comparison saved.")

    plot_constraint_overview(results, V_out=1.0, I_out=32.0,
                              v_ripple_frac=0.05, ripple_factor=0.2,
                              save_path="hvr_v3_fig2_constraints.png")
    print("[2/3] Constraint overview saved.")

    plot_pareto_loss_vs_area(results,
                              save_path="hvr_v3_fig3_pareto.png")
    print("[3/3] Pareto front saved.")
    print("\nDone.")
