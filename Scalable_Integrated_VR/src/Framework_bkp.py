#!/usr/bin/env python3
"""
VPD Framework v3 — Integrated GLSVLSI'24 Routing Loss Model
=============================================================
Adds the exact PPDN routing model from:
  Krishnakumar, Popryho, Partin-Vaisband, "System Architecture Optimization
  for Vertical Power Delivery," GLSVLSI'24 (Best Poster Award)

Key equations implemented:
  - R_eff_i = ρ × (Σⱼ 1/d_ji)⁻¹           [parallel resistance to each POL]
  - I_j = (I_out/S) × Σᵢ (d_ji × Σₖ 1/d_ki)⁻¹  [current per VR]
  - A_LS ∝ L_min × (I_ds/V_ds) × √(1/(f_sw×C_j0)) [optimal switch sizing]
  - VR placement optimization (A1: periphery, A2: under-die)
  - Joint (topology × components × segments × frequency × placement) optimization
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.collections import LineCollection
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from itertools import product as cartesian
import copy, os, warnings
warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════════════════════════
#  SECTION 1: REAL COMPONENT LIBRARIES (from v2)
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class GaNFET:
    name: str; manufacturer: str; v_ds_max: float; r_ds_on: float; r_ds_on_hot: float
    q_g: float; q_gd: float; q_oss: float; q_rr: float; i_d_max: float
    c_oss: float; t_rise: float; t_fall: float; v_gate: float
    footprint_mm2: float; source: str
    # GaN junction capacitance per unit area (for Eq.1 switch sizing)
    c_j0_pf_per_mm2: float = 50.0  # Typical eGaN

GAN_LIBRARY = [
    GaNFET("EPC2367", "EPC", 100, 1.2, 1.8, 2.5, 0.6, 5.2, 0, 200,
           95, 0.5, 0.5, 5.0, 10.9, "EPC 2025 Gen5, 100V", 45),
    GaNFET("EPC2071", "EPC", 100, 1.7, 2.6, 3.4, 0.8, 7.3, 0, 467,
           130, 0.6, 0.6, 5.0, 10.2, "EPC 2022 Gen5, 48V DC-DC", 50),
    GaNFET("EPC2302", "EPC", 100, 1.8, 2.7, 3.0, 0.7, 5.0, 0, 133,
           85, 0.5, 0.5, 5.0, 7.0, "EPC 2021, ePower chipset", 55),
    GaNFET("EPC2218", "EPC", 100, 3.2, 4.8, 2.0, 0.5, 3.5, 0, 231,
           52, 0.4, 0.4, 5.0, 3.88, "EPC Gen5, small die", 60),
    GaNFET("EPC2065", "EPC", 40, 1.5, 2.3, 2.4, 0.5, 3.0, 0, 166,
           70, 0.4, 0.4, 5.0, 4.6, "EPC Gen5, 40V", 48),
    GaNFET("EPC2024", "EPC", 40, 0.9, 1.4, 4.5, 1.1, 5.8, 0, 400,
           140, 0.5, 0.5, 5.0, 11.4, "EPC Gen5, 40V high-I", 42),
    GaNFET("BSZ013NE2LS5I", "Infineon", 25, 1.3, 2.0, 12.0, 4.5, 18.0, 25, 40,
           900, 3.0, 3.0, 10.0, 9.0, "Si OptiMOS baseline", 200),
]

@dataclass
class Inductor:
    name: str; technology: str; l_nh: float; r_dcr_mohm: float; i_sat_a: float
    q_factor: float; footprint_mm2: float; height_um: float; f_max_mhz: float
    coupling_k: float; core_loss_k: float; core_loss_alpha: float; source: str

INDUCTOR_LIBRARY = [
    Inductor("GT-Solenoid-7nH", "embedded", 7.0, 10.0, 5.0, 20, 1.0, 500, 100,
             0.57, 0.008, 1.7, "Georgia Tech TCPMT 2017"),
    Inductor("GT-Coupled-MagCore", "embedded", 12.0, 8.0, 16.5, 25, 2.9, 500, 80,
             0.57, 0.006, 1.7, "Coupled magnetic core, ScienceDirect 2024"),
    Inductor("UIC-MLSS-High", "embedded", 15.0, 6.0, 8.0, 22, 1.0, 300, 120,
             0.70, 0.005, 1.7, "Rasheedi, GLSVLSI 2024, 440 nH/mm²"),
    Inductor("UIC-MLSS-Med", "embedded", 8.0, 4.0, 12.0, 28, 0.8, 300, 150,
             0.70, 0.004, 1.7, "Rasheedi, ECTC 2025"),
    Inductor("PCB-4ph-coupled", "pcb_embedded", 10.0, 3.1, 20.0, 15, 16.0, 1000, 40,
             0.85, 0.020, 1.6, "PCB-embedded 4-phase coupled"),
    Inductor("Vishay-IHLP-100nH", "discrete", 100.0, 0.3, 50.0, 40, 64.0, 4000, 10,
             0.0, 0.001, 1.5, "Discrete baseline"),
]

@dataclass
class Capacitor:
    name: str; technology: str; c_uf: float; esr_mohm: float; esl_ph: float
    v_max: float; footprint_mm2: float; source: str

CAPACITOR_LIBRARY = [
    Capacitor("Murata-0402-10uF", "MLCC", 10.0, 2.0, 200, 6.3, 0.5, "Murata GRM15"),
    Capacitor("Murata-0805-22uF", "MLCC", 22.0, 1.5, 400, 6.3, 2.0, "Murata GRM21"),
    Capacitor("SiCap-10uF", "silicon_trench", 10.0, 3.0, 30, 6.3, 5.0, "Murata Si Cap"),
    Capacitor("Nichicon-FPCAP", "discrete", 470.0, 7.0, 3000, 2.5, 64.0, "Discrete baseline"),
]


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 2: GLSVLSI'24 ROUTING LOSS MODEL
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class DieConfig:
    """Physical die and package configuration."""
    die_area_mm2: float = 500.0
    die_side_mm: float = 22.36       # √500
    n_pol_segments: int = 100        # S in the paper
    rho_mohm_per_mm: float = 0.5     # RDL trace resistance per unit length
    i_out_total_a: float = 1000.0    # Total output current
    v_out: float = 1.0               # POL voltage
    ambient_temp_c: float = 35.0


class DVPDRoutingModel:
    """
    Exact routing loss model from Krishnakumar et al. GLSVLSI'24.
    Implements the parallel-resistance PPDN model with Manhattan distances.
    """

    def __init__(self, die: DieConfig):
        self.die = die
        self.pols = self._place_pols()

    def _place_pols(self) -> np.ndarray:
        """Divide die into S equal POL segments with coordinates."""
        side = int(np.ceil(np.sqrt(self.die.n_pol_segments)))
        dx = self.die.die_side_mm / side
        pols = []
        for r in range(side):
            for c in range(side):
                if len(pols) >= self.die.n_pol_segments:
                    break
                pols.append((dx * (c + 0.5), dx * (r + 0.5)))
        return np.array(pols[:self.die.n_pol_segments])

    @staticmethod
    def place_vrs_A2(n_vr: int, die_side: float) -> np.ndarray:
        """Architecture A2: VRs distributed under the die (highest efficiency)."""
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
        return np.array(vrs[:n_vr])

    @staticmethod
    def place_vrs_A1(n_vr: int, die_side: float) -> np.ndarray:
        """Architecture A1: VRs along the die periphery."""
        per_side = int(np.ceil(n_vr / 4))
        sp = die_side / (per_side + 1)
        vrs = []
        offset = 1.5  # mm outside die edge
        for i in range(per_side):
            if len(vrs) < n_vr: vrs.append((sp * (i+1), -offset))       # top
        for i in range(per_side):
            if len(vrs) < n_vr: vrs.append((sp * (i+1), die_side + offset))  # bottom
        for i in range(per_side):
            if len(vrs) < n_vr: vrs.append((-offset, sp * (i+1)))       # left
        for i in range(per_side):
            if len(vrs) < n_vr: vrs.append((die_side + offset, sp * (i+1)))  # right
        return np.array(vrs[:n_vr])

    def compute_ppdn_loss(self, vr_positions: np.ndarray) -> Dict:
        """
        Compute PPDN routing loss using the parallel resistance model.

        For each POL i:
          R_eff_i = ρ × (Σⱼ 1/d_ji)⁻¹
          P_routing_i = (I_out/S)² × R_eff_i

        For each VR j, current delivered:
          I_j = (I_out/S) × Σᵢ (d_ji × Σₖ 1/d_ki)⁻¹
        """
        S = len(self.pols)
        N = len(vr_positions)
        rho = self.die.rho_mohm_per_mm * 1e-3  # Convert to Ohms/mm
        i_per_pol = self.die.i_out_total_a / S

        # Precompute Manhattan distance matrix: dist[i, j] = d(POL_i, VR_j)
        dist_matrix = np.zeros((S, N))
        for i in range(S):
            for j in range(N):
                d = abs(self.pols[i][0] - vr_positions[j][0]) + \
                    abs(self.pols[i][1] - vr_positions[j][1])
                dist_matrix[i, j] = max(d, 0.01)  # Avoid division by zero

        # Inverse distance matrix
        inv_dist = 1.0 / dist_matrix  # Shape: (S, N)

        # Sum of inverse distances for each POL (from all VRs)
        sum_inv_d = inv_dist.sum(axis=1)  # Shape: (S,)

        # ── Effective resistance at each POL ──
        # R_eff_i = ρ × (Σⱼ 1/d_ji)⁻¹
        r_eff = rho / sum_inv_d  # Shape: (S,)

        # ── PPDN loss per POL: P_i = I_per_pol² × R_eff_i ──
        p_per_pol = i_per_pol**2 * r_eff
        total_ppdn_loss = p_per_pol.sum()

        # ── Current per VR ──
        # Fraction of POL_i's current from VR_j = (1/d_ji) / (Σₖ 1/d_ki)
        frac_matrix = inv_dist / sum_inv_d[:, np.newaxis]  # Shape: (S, N)
        i_per_vr = (frac_matrix * i_per_pol).sum(axis=0)  # Shape: (N,)

        # ── Statistics ──
        avg_r_eff = r_eff.mean()
        max_r_eff = r_eff.max()
        avg_dist = dist_matrix.min(axis=1).mean()  # Average nearest-VR distance

        return {
            'total_ppdn_loss_w': total_ppdn_loss,
            'r_eff_per_pol': r_eff,
            'p_per_pol': p_per_pol,
            'i_per_vr': i_per_vr,
            'frac_matrix': frac_matrix,
            'dist_matrix': dist_matrix,
            'avg_nearest_dist_mm': avg_dist,
            'avg_r_eff_ohm': avg_r_eff,
            'max_r_eff_ohm': max_r_eff,
            'vr_current_imbalance': i_per_vr.std() / i_per_vr.mean(),
        }


class SwitchSizingModel:
    """
    Optimal VR switch sizing from Eq. 1 of GLSVLSI'24:
      A_LS ∝ L_min × (I_ds / V_ds) × √(1 / (f_sw × C_j0))

    Determines VR footprint, which constrains how many VRs fit under the die.
    """

    @staticmethod
    def optimal_ls_area_mm2(gan: GaNFET, i_ds: float, v_ds: float,
                             f_sw_hz: float, l_min_nm: float = 100.0) -> float:
        """Compute optimal low-side switch area."""
        c_j0 = gan.c_j0_pf_per_mm2 * 1e-12  # Convert to F/mm²
        l_min_mm = l_min_nm * 1e-6
        area = l_min_mm * (i_ds / v_ds) * np.sqrt(1.0 / (f_sw_hz * c_j0))
        return max(area, 0.5)  # Minimum practical area

    @staticmethod
    def vr_footprint_mm2(gan: GaNFET, i_per_vr: float, v_in: float,
                          f_sw_mhz: float, inductor: Inductor) -> float:
        """Total VR footprint including switches + inductor + caps."""
        f_sw_hz = f_sw_mhz * 1e6
        # LS switch area (dominates)
        a_ls = SwitchSizingModel.optimal_ls_area_mm2(gan, i_per_vr, v_in, f_sw_hz)
        # HS switch area (~1/4 of LS for high-ratio converters)
        a_hs = a_ls * 0.25
        # Inductor footprint
        a_ind = inductor.footprint_mm2
        # Cap footprint estimate
        a_cap = 1.0  # ~1 mm² for MLCC array
        return a_ls + a_hs + a_ind + a_cap

    @staticmethod
    def max_vrs_under_die(die_area_mm2: float, vr_footprint_mm2: float,
                           packing_efficiency: float = 0.7) -> int:
        """Maximum number of VRs that fit under the die."""
        return max(1, int(die_area_mm2 * packing_efficiency / vr_footprint_mm2))


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 3: VR CONVERSION LOSS MODELS (from v2, streamlined)
# ═══════════════════════════════════════════════════════════════════════

class ConversionLossModel:
    """Loss models for VR topologies using real component parameters."""

    @staticmethod
    def dsch_loss(gan: GaNFET, ind: Inductor, i_load_a: float,
                  n_seg: int, n_phases: int, f_sw_mhz: float,
                  v_in: float = 48.0, v_out: float = 1.0) -> Dict:
        """Double Series Capacitor Hybrid (DSCH) converter — from the paper's topology.
        Combines SC voltage division with inductive regulation."""
        i_seg = i_load_a / n_seg
        i_ph = i_seg / n_phases
        f = f_sw_mhz * 1e6
        n = n_seg * n_phases
        sc_ratio = 4  # Typical DSCH has 4:1 SC stage
        v_ind_in = v_in / sc_ratio  # 12V after SC division

        # SC stage loss (soft-charging)
        p_sc = 0.008 * i_seg * v_ind_in * n_seg

        # Inductive stage conduction
        p_cond = i_ph**2 * gan.r_ds_on_hot * 1e-3 * 2 * n

        # Switching loss (reduced voltage: v_ind_in not v_in)
        p_sw = 0.5 * v_ind_in * i_ph * (gan.t_rise + gan.t_fall) * 1e-9 * f * n * 2

        # Gate drive
        p_gate = gan.q_g * 1e-9 * gan.v_gate * f * 4 * n

        # Inductor losses
        coupling_factor = 1.0 / (1 + ind.coupling_k * (n_phases - 1)) if ind.coupling_k > 0 else 1.0
        p_ind_dc = i_ph**2 * ind.r_dcr_mohm * 1e-3 * n
        p_ind_core = ind.core_loss_k * ind.l_nh * (f_sw_mhz**ind.core_loss_alpha) * n * coupling_factor

        total = p_sc + p_cond + p_sw + p_gate + p_ind_dc + p_ind_core
        return {'sc': p_sc, 'cond': p_cond, 'sw': p_sw, 'gate': p_gate,
                'ind_dc': p_ind_dc, 'ind_core': p_ind_core, 'total': total,
                'topology': 'DSCH'}

    @staticmethod
    def fcml_loss(gan: GaNFET, ind: Inductor, i_load_a: float,
                  n_seg: int, n_phases: int, f_sw_mhz: float,
                  v_in: float = 48.0, v_out: float = 1.0, n_levels: int = 4) -> Dict:
        """FCML converter loss."""
        i_seg = i_load_a / n_seg
        i_ph = i_seg / n_phases
        f = f_sw_mhz * 1e6
        n = n_seg * n_phases
        v_sw = v_in / n_levels

        p_cond = i_ph**2 * gan.r_ds_on_hot * 1e-3 * 2 * n
        p_sw = 0.5 * v_sw * i_ph * (gan.t_rise + gan.t_fall) * 1e-9 * f * n_levels * n * 0.7
        p_gate = gan.q_g * 1e-9 * gan.v_gate * f * (2 * n_levels) * n
        coupling = 1.0 / (1 + ind.coupling_k * (n_phases - 1)) if ind.coupling_k > 0 else 1.0
        p_ind_dc = i_ph**2 * ind.r_dcr_mohm * 1e-3 * n
        p_ind_core = ind.core_loss_k * ind.l_nh * (f_sw_mhz**ind.core_loss_alpha) * n * coupling
        p_fc = 0.005 * i_seg * v_sw * n_seg

        total = p_cond + p_sw + p_gate + p_ind_dc + p_ind_core + p_fc
        return {'cond': p_cond, 'sw': p_sw, 'gate': p_gate, 'ind_dc': p_ind_dc,
                'ind_core': p_ind_core, 'fc': p_fc, 'total': total,
                'topology': f'FCML-{n_levels}L'}

    @staticmethod
    def two_stage_loss(gan_s1: GaNFET, gan_s2: GaNFET, ind: Inductor,
                       i_load_a: float, n_seg: int, n_phases: int, f_sw_mhz: float,
                       v_in: float = 48.0, v_mid: float = 5.0, v_out: float = 1.0) -> Dict:
        """Two-stage: LLC (48V→V_mid) + multiphase buck (V_mid→1V)."""
        f = f_sw_mhz * 1e6
        n = n_seg * n_phases
        i_ph = i_load_a / n_seg / n_phases

        # Stage 1: LLC at 97% efficiency
        p_llc = i_load_a * v_out * (1/0.97 - 1)

        # Stage 2: Buck from V_mid
        p_cond = i_ph**2 * gan_s2.r_ds_on_hot * 1e-3 * 1.5 * n
        p_sw = 0.5 * v_mid * i_ph * (gan_s2.t_rise + gan_s2.t_fall) * 1e-9 * f * n * 2
        p_gate = gan_s2.q_g * 1e-9 * gan_s2.v_gate * f * 2 * n
        p_ind_dc = i_ph**2 * ind.r_dcr_mohm * 1e-3 * n
        p_ind_core = ind.core_loss_k * ind.l_nh * (f_sw_mhz**ind.core_loss_alpha) * n

        total = p_llc + p_cond + p_sw + p_gate + p_ind_dc + p_ind_core
        return {'llc': p_llc, 'cond': p_cond, 'sw': p_sw, 'gate': p_gate,
                'ind_dc': p_ind_dc, 'ind_core': p_ind_core, 'total': total,
                'topology': f'TwoStage-LLC+Buck({v_mid:.0f}V)'}


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 4: FULL SYSTEM OPTIMIZER
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class SystemResult:
    """Complete evaluation of one VPD configuration."""
    name: str = ""
    n_vr: int = 0
    topology: str = ""
    gan_name: str = ""
    ind_name: str = ""
    architecture: str = "A2"  # A1 or A2
    f_sw_mhz: float = 0
    n_phases: int = 4
    # Losses
    conv_loss_w: float = 0
    ppdn_loss_w: float = 0
    total_loss_w: float = 0
    efficiency_pct: float = 0
    # Physical
    vr_footprint_mm2: float = 0
    max_vrs_possible: int = 0
    avg_nearest_dist_mm: float = 0
    vr_current_imbalance: float = 0
    max_temp_c: float = 0
    droop_mv: float = 0
    # Breakdown
    conv_breakdown: Dict = field(default_factory=dict)


class IntegratedOptimizer:
    """Joint optimization of topology, components, segments, frequency, and placement."""

    def __init__(self, v_in: float = 48.0, v_out: float = 1.0, p_load_w: float = 1000.0,
                 die_area_mm2: float = 500.0):
        self.v_in = v_in
        self.v_out = v_out
        self.p_load = p_load_w
        self.i_load = p_load_w / v_out
        self.die = DieConfig(die_area_mm2=die_area_mm2,
                             die_side_mm=np.sqrt(die_area_mm2),
                             i_out_total_a=self.i_load, v_out=v_out)
        self.routing = DVPDRoutingModel(self.die)

    def evaluate(self, topology: str, gan: GaNFET, ind: Inductor,
                 n_vr: int, f_sw_mhz: float, n_phases: int = 4,
                 arch: str = "A2", v_mid: float = 5.0,
                 gan_s2: GaNFET = None, n_levels: int = 4) -> SystemResult:
        """Evaluate a complete system configuration."""
        res = SystemResult()
        res.n_vr = n_vr
        res.topology = topology
        res.gan_name = gan.name
        res.ind_name = ind.name
        res.architecture = arch
        res.f_sw_mhz = f_sw_mhz
        res.n_phases = n_phases

        # ── 1. Check area feasibility (Eq. 1 from paper) ──
        i_per_vr = self.i_load / n_vr
        res.vr_footprint_mm2 = SwitchSizingModel.vr_footprint_mm2(
            gan, i_per_vr, self.v_in, f_sw_mhz, ind)
        res.max_vrs_possible = SwitchSizingModel.max_vrs_under_die(
            self.die.die_area_mm2, res.vr_footprint_mm2)

        if n_vr > res.max_vrs_possible and arch == "A2":
            res.efficiency_pct = 0  # Infeasible
            res.name = f"INFEASIBLE: {n_vr} VRs > {res.max_vrs_possible} max"
            return res

        # ── 2. VR placement ──
        if arch == "A2":
            vr_pos = DVPDRoutingModel.place_vrs_A2(n_vr, self.die.die_side_mm)
        else:
            vr_pos = DVPDRoutingModel.place_vrs_A1(n_vr, self.die.die_side_mm)

        # ── 3. PPDN routing loss (GLSVLSI'24 model) ──
        ppdn = self.routing.compute_ppdn_loss(vr_pos)
        res.ppdn_loss_w = ppdn['total_ppdn_loss_w']
        res.avg_nearest_dist_mm = ppdn['avg_nearest_dist_mm']
        res.vr_current_imbalance = ppdn['vr_current_imbalance']

        # ── 4. Conversion loss ──
        if topology == "DSCH":
            conv = ConversionLossModel.dsch_loss(
                gan, ind, self.i_load, n_vr, n_phases, f_sw_mhz, self.v_in, self.v_out)
        elif topology.startswith("FCML"):
            conv = ConversionLossModel.fcml_loss(
                gan, ind, self.i_load, n_vr, n_phases, f_sw_mhz,
                self.v_in, self.v_out, n_levels)
        elif topology == "TwoStage":
            g2 = gan_s2 or gan
            conv = ConversionLossModel.two_stage_loss(
                gan, g2, ind, self.i_load, n_vr, n_phases, f_sw_mhz,
                self.v_in, v_mid, self.v_out)
        else:
            raise ValueError(f"Unknown topology: {topology}")

        res.conv_loss_w = conv['total']
        res.conv_breakdown = conv

        # ── 5. Total system ──
        res.total_loss_w = res.conv_loss_w + res.ppdn_loss_w
        res.efficiency_pct = self.p_load / (self.p_load + res.total_loss_w) * 100

        # ── 6. Thermal (VR loss per segment) ──
        vr_loss_per_seg = res.conv_loss_w / max(n_vr, 1)
        r_th = 0.5 + 2.0 / max(n_vr, 1)
        res.max_temp_c = self.die.ambient_temp_c + vr_loss_per_seg * r_th

        # ── 7. Transient droop ──
        i_step = self.i_load * 0.5 / n_vr
        l_pkg_ph = 50e-12  # 50 pH for vertical
        v_ind = l_pkg_ph * 5e9 * 1e3  # 5 A/ns slew
        bw = f_sw_mhz * 1e6 / 8
        v_cap = i_step / bw / (10e-6 * n_vr) * 1e3
        res.droop_mv = v_ind + min(v_cap, 30)

        res.name = f"{topology}({gan.name}+{ind.name}) {n_vr}VR@{f_sw_mhz}MHz {arch}"
        return res

    def lateral_baseline(self) -> SystemResult:
        """Conventional lateral PDN baseline."""
        si = next(g for g in GAN_LIBRARY if "BSZ" in g.name)
        ind = next(i for i in INDUCTOR_LIBRARY if "Vishay" in i.name)
        # IBA (48V→12V, 97%) + multiphase buck (12V→1V)
        p_iba = self.p_load * (1/0.97 - 1)
        i_ph = self.i_load / 16
        f = 0.5e6
        p_cond = i_ph**2 * si.r_ds_on_hot * 1e-3 * 16
        p_sw = 0.5 * 12 * i_ph * (si.t_rise + si.t_fall) * 1e-9 * f * 16 * 2
        p_gate = si.q_g * 1e-9 * si.v_gate * f * 32
        p_ind = i_ph**2 * ind.r_dcr_mohm * 1e-3 * 16
        conv = p_iba + p_cond + p_sw + p_gate + p_ind
        # Lateral PPDN loss (I²R, ~200W at 1000A)
        ppdn = self.i_load**2 * 0.15e-3
        total = conv + ppdn
        res = SystemResult(name="Lateral Baseline (IBA+Si Buck)", conv_loss_w=conv,
                           ppdn_loss_w=ppdn, total_loss_w=total,
                           efficiency_pct=self.p_load / (self.p_load + total) * 100,
                           droop_mv=50 + self.i_load * 0.5 * 0.15e-3 * 1e3)
        return res

    def full_sweep(self, verbose=True) -> Dict:
        """Full design-space exploration."""
        topologies = [
            ("DSCH", [4]),            # Paper's topology
            ("FCML", [3, 4, 5, 6]),   # Multi-level FCML
            ("TwoStage", [4]),        # LLC + Buck
        ]
        vr_counts = [4, 8, 12, 16, 20, 24, 32, 48, 64, 80, 96]
        frequencies = [1, 2, 3.36, 5, 8, 10, 15, 20, 30]
        architectures = ["A1", "A2"]
        v_mids = [3, 5, 6, 8, 12]  # For TwoStage

        gans_100v = [g for g in GAN_LIBRARY if g.v_ds_max >= 80 and g.manufacturer == "EPC"]
        gans_40v = [g for g in GAN_LIBRARY if g.v_ds_max >= 30 and g.v_ds_max <= 60]
        inductors = [i for i in INDUCTOR_LIBRARY if i.technology != "discrete"]

        results = []
        count = 0

        if verbose:
            print("Running full design-space sweep...")

        for topo_name, level_opts in topologies:
            for nl in level_opts:
                for gan in gans_100v:
                    for ind in inductors:
                        for n_vr in vr_counts:
                            for f_sw in frequencies:
                                for arch in architectures:
                                    if topo_name == "TwoStage":
                                        for vm in v_mids:
                                            g2 = gans_40v[0] if gans_40v else gan
                                            r = self.evaluate(topo_name, gan, ind, n_vr, f_sw,
                                                              4, arch, vm, g2, nl)
                                            if r.efficiency_pct > 0 and r.max_temp_c < 110:
                                                results.append(r)
                                            count += 1
                                    else:
                                        r = self.evaluate(topo_name, gan, ind, n_vr, f_sw,
                                                          4, arch, n_levels=nl)
                                        if r.efficiency_pct > 0 and r.max_temp_c < 110:
                                            results.append(r)
                                        count += 1

        results.sort(key=lambda x: x.efficiency_pct, reverse=True)
        baseline = self.lateral_baseline()

        if verbose:
            print(f"  Evaluated: {count:,} configurations")
            print(f"  Feasible & cool: {len(results):,}")

        return {'all': results, 'top20': results[:20], 'baseline': baseline, 'count': count}


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 5: PUBLICATION PLOTS
# ═══════════════════════════════════════════════════════════════════════

COLORS = {
    'navy': '#0A1628', 'teal': '#0891B2', 'cyan': '#22D3EE',
    'gold': '#F59E0B', 'accent': '#3B82F6', 'red': '#EF4444',
    'green': '#10B981', 'purple': '#8B5CF6', 'orange': '#F97316',
    'bg': '#F8FAFC', 'text': '#1E293B', 'muted': '#64748B', 'grid': '#E2E8F0'
}

def setup_style():
    plt.rcParams.update({
        'figure.facecolor': COLORS['bg'], 'axes.facecolor': '#FFFFFF',
        'axes.edgecolor': COLORS['grid'], 'axes.labelcolor': COLORS['text'],
        'axes.grid': True, 'grid.color': COLORS['grid'], 'grid.linewidth': 0.5,
        'xtick.color': COLORS['muted'], 'ytick.color': COLORS['muted'],
        'text.color': COLORS['text'], 'font.family': 'sans-serif',
        'font.size': 11, 'figure.dpi': 200,
    })


def plot_paper_reproduction(opt: IntegratedOptimizer, save_path: str):
    """Reproduce Fig. 2 from GLSVLSI'24: Power loss vs. # of VRs for A1 and A2."""
    setup_style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    gan = GAN_LIBRARY[0]  # EPC2367
    ind = INDUCTOR_LIBRARY[3]  # UIC-MLSS-Med
    vr_range = [4, 8, 12, 16, 20, 24, 32, 48, 64, 80, 96]

    for ax, arch, title in [(ax1, "A1", "Architecture A₁ (periphery)"),
                             (ax2, "A2", "Architecture A₂ (under die)")]:
        conv_losses, ppdn_losses, totals = [], [], []
        annotations = []

        for n in vr_range:
            # Find best frequency for this segment count
            best_r = None
            for f in [1, 1.25, 1.68, 2.6, 3.36, 5, 8]:
                r = opt.evaluate("DSCH", gan, ind, n, f, 4, arch)
                if r.efficiency_pct > 0 and (best_r is None or r.total_loss_w < best_r.total_loss_w):
                    best_r = r
            if best_r is None:
                best_r = opt.evaluate("DSCH", gan, ind, n, 3.36, 4, arch)

            conv_losses.append(best_r.conv_loss_w)
            ppdn_losses.append(best_r.ppdn_loss_w)
            totals.append(best_r.total_loss_w)
            annotations.append(f"{best_r.f_sw_mhz:.1f} MHz\n{best_r.vr_footprint_mm2:.0f} mm²")

        ax.plot(vr_range, conv_losses, 's-', color=COLORS['teal'], linewidth=2,
                markersize=5, label='Converter loss')
        ax.plot(vr_range, ppdn_losses, 'D-', color=COLORS['gold'], linewidth=2,
                markersize=5, label='PPDN loss')
        ax.plot(vr_range, totals, 'o-', color=COLORS['red'], linewidth=2.5,
                markersize=6, label='Total loss')

        # Annotate key points
        for i in [2, 5, 8]:
            if i < len(vr_range):
                ax.annotate(annotations[i], (vr_range[i], totals[i]),
                            textcoords="offset points", xytext=(10, 10),
                            fontsize=7, color=COLORS['muted'],
                            bbox=dict(boxstyle='round,pad=0.3', fc='white', ec=COLORS['grid'], alpha=0.9))

        # 30% baseline
        ax.axhline(y=opt.p_load * 0.30, color=COLORS['red'], linestyle='--',
                    linewidth=1.5, alpha=0.5)
        ax.text(90, opt.p_load * 0.30 + 8, '>30% commercial', fontsize=8,
                color=COLORS['red'], alpha=0.7, ha='right')

        ax.set_xlabel('Number of VRs', fontweight='bold')
        ax.set_ylabel('Power loss (W)', fontweight='bold')
        ax.set_title(title, fontweight='bold', fontsize=13)
        ax.legend(loc='upper right', fontsize=9, framealpha=0.9)
        ax.set_ylim(bottom=0)
        ax.set_xlim(0, 100)

    fig.suptitle('Optimized DVPD power loss — GLSVLSI\'24 model with real GaN components',
                 fontsize=12, fontweight='bold', y=1.01)
    fig.tight_layout()
    fig.savefig(save_path, dpi=200, bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()


def plot_topology_comparison(opt: IntegratedOptimizer, save_path: str):
    """Compare DSCH vs FCML vs TwoStage across segment counts."""
    setup_style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    gan = GAN_LIBRARY[0]
    ind = INDUCTOR_LIBRARY[3]
    vr_range = list(range(4, 97, 4))
    baseline = opt.lateral_baseline()

    topo_configs = [
        ("DSCH", "DSCH (paper's topology)", COLORS['teal'], 's', {}),
        ("FCML", "FCML 4-Level", COLORS['accent'], 'D', {'n_levels': 4}),
        ("FCML", "FCML 6-Level", COLORS['purple'], '^', {'n_levels': 6}),
        ("TwoStage", "LLC+Buck (V_mid=5V)", COLORS['gold'], 'o', {'v_mid': 5.0}),
        ("TwoStage", "LLC+Buck (V_mid=8V)", COLORS['orange'], 'v', {'v_mid': 8.0}),
    ]

    for topo, label, color, marker, kwargs in topo_configs:
        effs, losses = [], []
        for n in vr_range:
            best = None
            for f in [3.36, 5, 8, 10, 15, 20]:
                nl = kwargs.get('n_levels', 4)
                vm = kwargs.get('v_mid', 5.0)
                g2 = GAN_LIBRARY[4] if topo == "TwoStage" else None
                r = opt.evaluate(topo, gan, ind, n, f, 4, "A2", vm, g2, nl)
                if r.efficiency_pct > 0 and (best is None or r.efficiency_pct > best.efficiency_pct):
                    best = r
            if best:
                effs.append(best.efficiency_pct)
                losses.append(best.total_loss_w)
            else:
                effs.append(0)
                losses.append(0)

        valid = [(n, e) for n, e in zip(vr_range, effs) if e > 0]
        if valid:
            ax1.plot([v[0] for v in valid], [v[1] for v in valid],
                     color=color, marker=marker, markersize=4, linewidth=1.8, label=label)

        valid_l = [(n, l) for n, l in zip(vr_range, losses) if l > 0]
        if valid_l:
            ax2.plot([v[0] for v in valid_l], [v[1] for v in valid_l],
                     color=color, marker=marker, markersize=4, linewidth=1.8, label=label)

    ax1.axhline(y=baseline.efficiency_pct, color=COLORS['red'], linestyle='--', linewidth=2, alpha=0.7)
    ax1.text(80, baseline.efficiency_pct + 0.5, f'Lateral {baseline.efficiency_pct:.1f}%',
             color=COLORS['red'], fontsize=9, fontweight='bold')

    ax1.set_xlabel('Number of VR segments', fontweight='bold')
    ax1.set_ylabel('System efficiency (%)', fontweight='bold')
    ax1.set_title('Efficiency comparison — all topologies\n(A₂ architecture, EPC2367 GaN, UIC inductor)', fontweight='bold')
    ax1.legend(fontsize=8, loc='lower right', framealpha=0.9)

    ax2.axhline(y=baseline.total_loss_w, color=COLORS['red'], linestyle='--', linewidth=2, alpha=0.7)
    ax2.set_xlabel('Number of VR segments', fontweight='bold')
    ax2.set_ylabel('Total power loss (W)', fontweight='bold')
    ax2.set_title('Total loss — converter + PPDN routing\n(Lower is better)', fontweight='bold')
    ax2.legend(fontsize=8, loc='upper right', framealpha=0.9)
    ax2.set_ylim(bottom=0)

    fig.tight_layout()
    fig.savefig(save_path, dpi=200, bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()


def plot_a1_vs_a2(opt: IntegratedOptimizer, save_path: str):
    """Compare A1 (periphery) vs A2 (under die) — reproducing paper's key finding."""
    setup_style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    gan = GAN_LIBRARY[0]
    ind = INDUCTOR_LIBRARY[3]
    vr_range = list(range(4, 97, 4))

    for arch, color, marker, label in [("A2", COLORS['teal'], 's', 'A₂ (under die)'),
                                        ("A1", COLORS['gold'], 'D', 'A₁ (periphery)')]:
        ppdn_vals, total_vals = [], []
        for n in vr_range:
            r = opt.evaluate("DSCH", gan, ind, n, 3.36, 4, arch)
            ppdn_vals.append(r.ppdn_loss_w)
            total_vals.append(r.total_loss_w if r.efficiency_pct > 0 else np.nan)

        ax1.plot(vr_range, ppdn_vals, color=color, marker=marker, markersize=4,
                 linewidth=2, label=f'{label} — PPDN loss')
        ax2.plot(vr_range, total_vals, color=color, marker=marker, markersize=4,
                 linewidth=2, label=f'{label} — Total loss')

    ax1.set_xlabel('Number of VRs', fontweight='bold')
    ax1.set_ylabel('PPDN routing loss (W)', fontweight='bold')
    ax1.set_title('PPDN routing loss: A₁ vs A₂\n(Paper finding: A₁ routing ≈ 2× A₂)', fontweight='bold')
    ax1.legend(fontsize=9)
    ax1.set_ylim(bottom=0)

    ax2.axhline(y=opt.p_load * 0.30, color=COLORS['red'], linestyle='--',
                linewidth=1.5, alpha=0.5, label='>30% commercial baseline')
    ax2.set_xlabel('Number of VRs', fontweight='bold')
    ax2.set_ylabel('Total loss (W)', fontweight='bold')
    ax2.set_title('Total system loss: A₁ vs A₂\n(Converter + PPDN routing)', fontweight='bold')
    ax2.legend(fontsize=9)
    ax2.set_ylim(bottom=0)

    fig.tight_layout()
    fig.savefig(save_path, dpi=200, bbox_inches='tight', facecolor=COLORS['bg'])
    plt.close()


def print_summary(results: Dict):
    bl = results['baseline']
    top = results['top20']

    print("\n" + "=" * 110)
    print("VPD FRAMEWORK v3 — INTEGRATED GLSVLSI'24 ROUTING MODEL + REAL COMPONENTS")
    print("=" * 110)
    print(f"System: {1000}W, 48V → 1V, I_load = {1000}A, Die = 500 mm²")
    print(f"Evaluated: {results['count']:,} configs | Feasible: {len(results['all']):,}")

    print(f"\nBASELINE: {bl.name}")
    print(f"  Eff: {bl.efficiency_pct:.1f}% | Loss: {bl.total_loss_w:.0f}W | "
          f"Conv: {bl.conv_loss_w:.0f}W | PDN: {bl.ppdn_loss_w:.0f}W | Droop: {bl.droop_mv:.0f}mV")

    print(f"\n{'#':<3} {'Eff%':<7} {'Loss':<7} {'Conv':<7} {'PPDN':<7} {'VRs':<5} "
          f"{'Arch':<5} {'f_sw':<7} {'Topology':<20} {'GaN':<10} {'Inductor':<18} {'Droop':<7}")
    print("-" * 110)

    for i, r in enumerate(top[:15]):
        print(f"{i+1:<3} {r.efficiency_pct:<7.1f} {r.total_loss_w:<7.0f} "
              f"{r.conv_loss_w:<7.0f} {r.ppdn_loss_w:<7.1f} {r.n_vr:<5} "
              f"{r.architecture:<5} {r.f_sw_mhz:<7.1f} {r.topology:<20} "
              f"{r.gan_name:<10} {r.ind_name:<18} {r.droop_mv:<7.1f}")

    if top:
        best = top[0]
        print(f"\n{'='*110}")
        print(f"BEST: {best.name}")
        print(f"  Efficiency: {best.efficiency_pct:.1f}% (baseline: {bl.efficiency_pct:.1f}%)")
        print(f"  Improvement: +{best.efficiency_pct - bl.efficiency_pct:.1f} pp")
        print(f"  Loss reduction: {(1 - best.total_loss_w / bl.total_loss_w)*100:.0f}%")
        print(f"  PPDN loss: {best.ppdn_loss_w:.1f}W (baseline: {bl.ppdn_loss_w:.0f}W) "
              f"→ {(1 - best.ppdn_loss_w / bl.ppdn_loss_w)*100:.0f}% reduction")
        print(f"  Avg nearest VR-to-POL: {best.avg_nearest_dist_mm:.1f} mm")
        print(f"  VR footprint: {best.vr_footprint_mm2:.1f} mm² | "
              f"Max possible: {best.max_vrs_possible} VRs under die")


# ═══════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║  VPD Framework v3                                                ║")
    print("╚══════════════════════════════════════════════════════════════════╝\n")

    opt = IntegratedOptimizer(v_in=48.0, v_out=1.0, p_load_w=1000.0, die_area_mm2=500.0)

    results = opt.full_sweep(verbose=True)
    print_summary(results)

    print("\nGenerating publication figures...")
    plot_paper_reproduction(opt, "v3_fig1_paper_reproduction.png")
    print("  [1/3] Paper Fig.2 reproduction (A1 vs A2 loss curves) ✓")

    plot_topology_comparison(opt, "v3_fig2_topology_comparison.png")
    print("  [2/3] Topology comparison (DSCH vs FCML vs TwoStage) ✓")

    plot_a1_vs_a2(opt, "v3_fig3_a1_vs_a2.png")
    print("  [3/3] A1 vs A2 routing loss comparison ✓")

    print("\n✅ All done!")