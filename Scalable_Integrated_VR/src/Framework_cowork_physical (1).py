#!/usr/bin/env python3
"""
Framework_cowork.py
===================
Framework.py + multicore parallelism.

Changes vs Framework.py
------------------------
1. Module-level _sweep_chunk() worker — picklable on Windows (spawn).
2. full_sweep() uses ProcessPoolExecutor, parallelising at the
   (topo, nl, gan, ind) level (~576 independent tasks).
3. compute_ppdn_loss() inner Python double for-loop replaced with
   vectorised numpy broadcasting (S×N distance matrix in one call).
4. lateral_baseline() fixed: BSZ device is _SI_BASELINE (not in GAN_LIBRARY);
   Vishay inductor not in HVR_INDUCTOR_LIB — both now use safe fallbacks.
5. GaN pool filtered to top-12 HV (v_ds >= 80V) and top-8 LV (30-60V) by
   FOM = R_DS_ON * Q_G, reducing sweep count without sacrificing coverage.
6. Progress reported every 5% of tasks.
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
from concurrent.futures import ProcessPoolExecutor, as_completed
warnings.filterwarnings('ignore')

# ── HVR module ────────────────────────────────────────────────────────────────
from HVR_FULL_OPT_EPC_V2 import (
    run_hvr_optimization,
    OptimizationResult as HVRResult,
    INDUCTOR_LIBRARY as HVR_INDUCTOR_LIB,
    CAPACITOR_LIBRARY as HVR_CAPACITOR_LIB,
    Inductor as HVRInductor,
)


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 1: COMPONENT LIBRARIES
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class GaNFET:
    name: str; manufacturer: str; v_ds_max: float; r_ds_on: float; r_ds_on_hot: float
    q_g: float; q_gd: float; q_oss: float; q_rr: float; i_d_max: float
    c_oss: float; t_rise: float; t_fall: float; v_gate: float
    footprint_mm2: float; source: str
    c_j0_pf_per_mm2: float = 50.0


import pandas as _pd


def load_gan_library_from_csv(csv_path: str = "EPC-Product-Table.csv",
                               v_gs_drive: float = 5.0) -> List["GaNFET"]:
    """Build GaNFET library from EPC-Product-Table.csv."""
    from HVR_FULL_OPT_EPC_V2 import load_epc_devices
    df = load_epc_devices(csv_path, V_gs_op=v_gs_drive)
    devices: List[GaNFET] = []
    R_G = 1.5; V_TH = 1.3
    for _, row in df.iterrows():
        r_ds  = float(row['R_DS_ON_mOhm'])
        q_g   = float(row['QG_nC'])
        q_gd  = float(row['QGD_nC'])
        q_oss = float(row['QOSS_nC'])
        v_ds  = float(row['VDSmax'])
        i_d   = float(row['ID_A'])
        fp    = float(row['footprint_mm2']) if not np.isnan(row['footprint_mm2']) else 2.0
        r_hot = r_ds * 1.5
        c_oss = (q_oss * 1e-9) / max(v_ds, 1.0) * 1e12
        t_sw  = (q_gd * 1e-9 * R_G) / max(v_gs_drive - V_TH, 0.1) * 1e9
        devices.append(GaNFET(
            name=str(row['PartNumber']), manufacturer="EPC",
            v_ds_max=v_ds, r_ds_on=r_ds, r_ds_on_hot=r_hot,
            q_g=q_g, q_gd=q_gd, q_oss=q_oss, q_rr=0.0, i_d_max=i_d,
            c_oss=c_oss, t_rise=t_sw, t_fall=t_sw, v_gate=v_gs_drive,
            footprint_mm2=fp, source="EPC-Product-Table.csv",
            c_j0_pf_per_mm2=50.0,
        ))
    return devices


# Si OptiMOS — baseline reference only, NOT in GAN_LIBRARY
_SI_BASELINE = GaNFET("BSZ013NE2LS5I","Infineon",25,1.3,2.0,12.0,4.5,18.0,25,40,900,
                       3.0,3.0,10.0,9.0,"Si OptiMOS baseline",200)

try:
    GAN_LIBRARY = load_gan_library_from_csv()
except Exception:
    GAN_LIBRARY = [
        GaNFET("EPC2367","EPC",100,1.2,1.8,2.5,0.6,5.2,0,200,95,0.5,0.5,5.0,10.9,"EPC fallback",45),
        GaNFET("EPC2218","EPC",100,3.2,4.8,2.0,0.5,3.5,0,231,52,0.4,0.4,5.0,3.88,"EPC fallback",60),
        GaNFET("EPC2065","EPC",40,1.5,2.3,2.4,0.5,3.0,0,166,70,0.4,0.4,5.0,4.6,"EPC fallback",48),
    ]

# Inductor / Capacitor libraries come from HVR module
INDUCTOR_LIBRARY = HVR_INDUCTOR_LIB
CAPACITOR_LIBRARY = HVR_CAPACITOR_LIB


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 2: GLSVLSI'24 ROUTING LOSS MODEL
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class DieConfig:
    die_area_mm2: float = 500.0
    die_side_mm: float = 22.36
    n_pol_segments: int = 100
    rho_mohm_per_mm: float = 0.5
    i_out_total_a: float = 1000.0
    v_out: float = 1.0
    ambient_temp_c: float = 35.0
    metal_width_mm: float = 0.25
    metal_thickness_mm: float = 0.035
    n_power_tracks: int = 2
    sheet_res_mohm_per_sq: float = 0.49
    bump_res_mohm: float = 0.05
    tsv_res_mohm: float = 0.03
    pkg_loop_inductance_ph: float = 35.0
    decap_per_vr_uf: float = 8.0
    decap_esr_mohm: float = 0.15
    decap_esl_ph: float = 12.0


class DVPDRoutingModel:
    """Parallel-resistance PPDN model from Krishnakumar et al. GLSVLSI'24."""

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
                pols.append((dx*(c+0.5), dx*(r+0.5)))
        return np.array(pols[:self.die.n_pol_segments])

    @staticmethod
    def place_vrs_A2(n_vr: int, die_side: float) -> np.ndarray:
        cols = int(np.ceil(np.sqrt(n_vr)))
        rows = int(np.ceil(n_vr / cols))
        vrs = []
        for r in range(rows):
            for c in range(cols):
                if len(vrs) >= n_vr: break
                vrs.append((die_side/(cols+1)*(c+1), die_side/(rows+1)*(r+1)))
        return np.array(vrs[:n_vr])

    @staticmethod
    def place_vrs_A1(n_vr: int, die_side: float) -> np.ndarray:
        per_side = int(np.ceil(n_vr / 4))
        sp = die_side / (per_side + 1)
        vrs = []; offset = 1.5
        for i in range(per_side):
            if len(vrs) < n_vr: vrs.append((sp*(i+1), -offset))
        for i in range(per_side):
            if len(vrs) < n_vr: vrs.append((sp*(i+1), die_side+offset))
        for i in range(per_side):
            if len(vrs) < n_vr: vrs.append((-offset, sp*(i+1)))
        for i in range(per_side):
            if len(vrs) < n_vr: vrs.append((die_side+offset, sp*(i+1)))
        return np.array(vrs[:n_vr])

    def compute_ppdn_loss(self, vr_positions: np.ndarray) -> Dict:
        """
        Compact physical PPDN model.

        Each POL sees each VR through a path resistance composed of:
          R_path = R_vertical + R_lateral
          R_vertical = 2*R_bump + R_tsv
          R_lateral  = R_sheet * (L / W_eff)

        Current splits among all candidate VR paths by conductance. This is still
        a reduced-order model, but unlike the original 1/d weighting it maps the
        geometry to an actual resistance and therefore gives more interpretable
        loss trends.
        """
        S = len(self.pols)
        i_per_pol = self.die.i_out_total_a / S

        pols_xy = self.pols
        vr_xy = vr_positions

        dx = np.abs(pols_xy[:, np.newaxis, 0] - vr_xy[np.newaxis, :, 0])
        dy = np.abs(pols_xy[:, np.newaxis, 1] - vr_xy[np.newaxis, :, 1])
        path_len_mm = np.maximum(dx + dy, 0.02)

        w_eff_mm = max(self.die.metal_width_mm * self.die.n_power_tracks, 1e-3)
        r_sheet = self.die.sheet_res_mohm_per_sq * 1e-3
        r_vertical = (2 * self.die.bump_res_mohm + self.die.tsv_res_mohm) * 1e-3
        r_lateral = r_sheet * (path_len_mm / w_eff_mm)
        r_path = r_vertical + r_lateral

        g_path = 1.0 / np.maximum(r_path, 1e-9)
        sum_g = g_path.sum(axis=1)
        r_eff = 1.0 / np.maximum(sum_g, 1e-12)

        p_per_pol = i_per_pol**2 * r_eff
        total_ppdn = float(p_per_pol.sum())

        frac = g_path / np.maximum(sum_g[:, np.newaxis], 1e-12)
        i_per_vr = (frac * i_per_pol).sum(axis=0)
        avg_dist = float(path_len_mm.min(axis=1).mean())

        return {
            'total_ppdn_loss_w': total_ppdn,
            'r_eff_per_pol': r_eff, 'p_per_pol': p_per_pol,
            'i_per_vr': i_per_vr, 'frac_matrix': frac,
            'dist_matrix': path_len_mm, 'r_path_matrix': r_path,
            'avg_nearest_dist_mm': avg_dist,
            'avg_r_eff_ohm': float(r_eff.mean()), 'max_r_eff_ohm': float(r_eff.max()),
            'vr_current_imbalance': float(i_per_vr.std() / max(i_per_vr.mean(), 1e-12)),
        }


class SwitchSizingModel:
    @staticmethod
    def target_power_stage_resistance_ohm(v_in, v_out, i_per_vr, conduction_loss_fraction=0.20):
        d = np.clip(v_out / max(v_in, v_out + 1e-9), 0.01, 0.99)
        p_budget = max(conduction_loss_fraction * v_out * i_per_vr * 0.01, 1e-3)
        weight = d + (1.0 - d)
        return p_budget / max(i_per_vr**2 * weight, 1e-9)

    @staticmethod
    def optimal_ls_area_mm2(gan: GaNFET, i_ds, v_ds, f_sw_hz, l_min_nm=100.0):
        """
        Size switch area from an on-resistance target instead of from the old
        square-root placeholder. The idea is simple: decide how much conduction
        loss the stage can tolerate, then scale die area roughly inversely with
        achievable Rds,on.
        """
        r_target = SwitchSizingModel.target_power_stage_resistance_ohm(v_ds, max(0.8, v_ds/12), i_ds)
        area_ref = max(gan.footprint_mm2, 0.5)
        r_ref = max(gan.r_ds_on_hot * 1e-3, 1e-6)
        area_scale = r_ref / max(r_target, 1e-6)
        freq_penalty = 1.0 + 0.04 * np.sqrt(max(f_sw_hz, 1.0) / 1e6)
        return max(0.25, area_ref * area_scale * freq_penalty)

    @staticmethod
    def vr_footprint_mm2(gan, i_per_vr, v_in, f_sw_mhz, inductor):
        f_sw_hz = f_sw_mhz * 1e6
        a_ls = SwitchSizingModel.optimal_ls_area_mm2(gan, i_per_vr, v_in, f_sw_hz)
        a_hs = max(0.35 * a_ls, 0.15)
        gate_driver_area = 0.25 + 0.015 * f_sw_mhz
        decap_area = 0.35 + 0.002 * i_per_vr
        routing_keepout = 0.40
        return a_ls + a_hs + getattr(inductor, 'footprint_mm2', 1.0) + gate_driver_area + decap_area + routing_keepout

    @staticmethod
    def max_vrs_under_die(die_area_mm2, vr_footprint_mm2, packing_efficiency=0.7):
        return max(1, int(die_area_mm2 * packing_efficiency / max(vr_footprint_mm2, 1e-6)))


class CompactPhysicalModel:
    """Small helper formulas shared by the conversion, thermal, and droop models."""

    @staticmethod
    def buck_ripple_current(v_bus, v_out, l_h, f_hz):
        d = np.clip(v_out / max(v_bus, 1e-9), 0.01, 0.99)
        return max((v_bus - v_out) * d / max(l_h * f_hz, 1e-18), 0.0)

    @staticmethod
    def inductor_rms(i_dc, delta_i):
        return np.sqrt(i_dc**2 + (delta_i**2) / 12.0)

    @staticmethod
    def effective_coss_f(coss_pf):
        return max(coss_pf, 1e-6) * 1e-12

    @staticmethod
    def switching_overlap_loss(v_sw, i_sw, t_rise_ns, t_fall_ns, f_hz, edges_per_cycle=1.0):
        t_sw = max(t_rise_ns + t_fall_ns, 0.1) * 1e-9
        return 0.5 * v_sw * i_sw * t_sw * f_hz * edges_per_cycle

    @staticmethod
    def coss_loss(coss_pf, v_sw, f_hz, edges_per_cycle=1.0):
        c_f = CompactPhysicalModel.effective_coss_f(coss_pf)
        return 0.5 * c_f * v_sw**2 * f_hz * edges_per_cycle

    @staticmethod
    def gate_drive_loss(qg_nc, v_gate, f_hz, gates=1.0):
        return max(qg_nc, 0.0) * 1e-9 * max(v_gate, 0.0) * f_hz * gates

    @staticmethod
    def estimate_switched_cap_resistance(n_seg, f_hz, cap_density_uf_per_mm2=0.25, cap_area_mm2=4.0, series_factor=2.0):
        c_eff = cap_density_uf_per_mm2 * cap_area_mm2 * 1e-6
        return series_factor / max(n_seg * c_eff * f_hz, 1e-12)

    @staticmethod
    def estimate_inductor_core_loss(ind, delta_i, i_dc, f_mhz):
        """
        Compact ripple-based magnetic loss model.

        The earlier version multiplied L(nH) directly by f^alpha, which can blow up
        into kilowatts because L is not a magnetic-volume or flux-swing term.
        Here we use a bounded surrogate that follows the right trends:
          - rises with switching frequency
          - rises strongly with AC ripple current
          - scales mildly with inductor size / current rating
        and stays in a realistic range for point-of-load VRs.
        """
        k = max(getattr(ind, 'core_loss_k', 0.01), 1e-4)
        alpha = np.clip(getattr(ind, 'core_loss_alpha', 1.35), 1.1, 1.8)
        l_nh = max(getattr(ind, 'l_nh', 100.0), 10.0)
        i_sat = max(getattr(ind, 'i_sat_a', 20.0), 1.0)
        ripple_pk = max(delta_i, 0.0) / 2.0
        ripple_norm = np.clip(ripple_pk / i_sat, 0.0, 1.5)
        size_factor = np.clip(np.sqrt(l_nh / 100.0), 0.5, 2.0)
        freq_factor = np.clip((max(f_mhz, 0.1) / 1.0) ** alpha, 0.2, 30.0)
        return 0.08 * k * size_factor * freq_factor * (ripple_norm ** 2.0)

    @staticmethod
    def estimate_thermal_rise(ambient_c, total_loss_w, n_vr, vr_footprint_mm2):
        a_cm2 = max(vr_footprint_mm2 * 0.01, 0.02)
        spreading_rth = 0.35 + 1.8 / np.sqrt(a_cm2)
        sharing = 0.85 + 0.15 * np.sqrt(max(n_vr, 1))
        return ambient_c + (total_loss_w / max(n_vr, 1)) * spreading_rth / sharing

    @staticmethod
    def estimate_droop_mv(i_step_a, n_vr, f_sw_hz, l_pkg_ph, decap_per_vr_uf, decap_esr_mohm, decap_esl_ph, r_path_ohm):
        c_total = max(decap_per_vr_uf * n_vr, 1e-3) * 1e-6
        control_bw = max(f_sw_hz / 6.0, 5e4)
        v_c = i_step_a / (c_total * control_bw)
        l_total = (l_pkg_ph + decap_esl_ph / max(n_vr, 1)) * 1e-12
        v_l = l_total * (i_step_a * control_bw)
        v_r = i_step_a * (r_path_ohm + decap_esr_mohm * 1e-3 / max(n_vr, 1))
        return (v_c + v_l + v_r) * 1e3


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 3: CONVERSION LOSS MODELS
# ═══════════════════════════════════════════════════════════════════════

class ConversionLossModel:
    @staticmethod
    def _common_buck_terms(gan, ind, i_seg, n_seg, n_phases, f_sw_mhz, v_bus, v_out,
                           switch_multiplier=1.0, gate_multiplier=1.0):
        f = f_sw_mhz * 1e6
        l_h = max(getattr(ind, 'l_nh', 100.0) * 1e-9, 1e-9)
        d = np.clip(v_out / max(v_bus, 1e-9), 0.01, 0.99)
        i_ph_dc = i_seg / n_phases
        delta_i = CompactPhysicalModel.buck_ripple_current(v_bus, v_out, l_h, f)
        # Bound the triangular ripple to avoid non-physical cases where a very small
        # library inductance would imply ripple many times larger than the DC phase current.
        delta_i = min(delta_i, 1.6 * max(i_ph_dc, 0.5))
        i_ph_rms = CompactPhysicalModel.inductor_rms(i_ph_dc, delta_i)
        rds = max(gan.r_ds_on_hot * 1e-3, 1e-6)

        p_cond_hs = i_ph_rms**2 * rds * d * n_seg * n_phases
        p_cond_ls = i_ph_rms**2 * rds * (1.0 - d) * n_seg * n_phases
        p_sw_overlap = CompactPhysicalModel.switching_overlap_loss(
            v_bus, i_ph_dc, gan.t_rise, gan.t_fall, f,
            edges_per_cycle=switch_multiplier * n_seg * n_phases)
        p_coss = CompactPhysicalModel.coss_loss(
            gan.c_oss, v_bus, f, edges_per_cycle=switch_multiplier * n_seg * n_phases)
        p_gate = CompactPhysicalModel.gate_drive_loss(
            gan.q_g, gan.v_gate, f, gates=gate_multiplier * n_seg * n_phases)
        p_ind_dc = i_ph_rms**2 * max(getattr(ind, 'r_dcr_mohm', 1.0), 0.0) * 1e-3 * n_seg * n_phases
        coupling_k = max(getattr(ind, 'coupling_k', 0.0), 0.0)
        coupling_relief = 1.0 / (1.0 + coupling_k * max(n_phases - 1, 0))
        p_ind_core = CompactPhysicalModel.estimate_inductor_core_loss(ind, delta_i, i_ph_dc, f_sw_mhz) * n_seg * n_phases * coupling_relief
        return {
            'duty': d,
            'delta_i_a': delta_i,
            'i_ph_rms_a': i_ph_rms,
            'cond_hs': p_cond_hs,
            'cond_ls': p_cond_ls,
            'sw_overlap': p_sw_overlap,
            'coss': p_coss,
            'gate': p_gate,
            'ind_dc': p_ind_dc,
            'ind_core': p_ind_core,
        }

    @staticmethod
    def dsch_loss(gan, ind, i_load_a, n_seg, n_phases, f_sw_mhz,
                  v_in=48.0, v_out=1.0):
        i_seg = i_load_a / n_seg
        sc_ratio = 4
        v_bus = v_in / sc_ratio
        common = ConversionLossModel._common_buck_terms(
            gan, ind, i_seg, n_seg, n_phases, f_sw_mhz, v_bus, v_out,
            switch_multiplier=2.0, gate_multiplier=4.0)
        r_eq_sc = CompactPhysicalModel.estimate_switched_cap_resistance(n_seg, f_sw_mhz * 1e6, cap_density_uf_per_mm2=0.6, cap_area_mm2=8.0, series_factor=0.12)
        p_sc = i_seg**2 * r_eq_sc * n_seg
        total = p_sc + common['cond_hs'] + common['cond_ls'] + common['sw_overlap'] + common['coss'] + common['gate'] + common['ind_dc'] + common['ind_core']
        return {
            'sc_equiv': p_sc,
            'cond_hs': common['cond_hs'], 'cond_ls': common['cond_ls'],
            'sw_overlap': common['sw_overlap'], 'coss': common['coss'], 'gate': common['gate'],
            'ind_dc': common['ind_dc'], 'ind_core': common['ind_core'],
            'delta_i_a': common['delta_i_a'], 'i_ph_rms_a': common['i_ph_rms_a'],
            'total': total, 'topology': 'DSCH'
        }

    @staticmethod
    def fcml_loss(gan, ind, i_load_a, n_seg, n_phases, f_sw_mhz,
                  v_in=48.0, v_out=1.0, n_levels=4):
        i_seg = i_load_a / n_seg
        v_bus = v_in / n_levels
        common = ConversionLossModel._common_buck_terms(
            gan, ind, i_seg, n_seg, n_phases, f_sw_mhz, v_bus, v_out,
            switch_multiplier=max(1.0, 0.7 * n_levels), gate_multiplier=2.0 * n_levels)
        r_eq_fc = CompactPhysicalModel.estimate_switched_cap_resistance(
            n_seg, f_sw_mhz * 1e6, cap_density_uf_per_mm2=0.6, cap_area_mm2=8.0, series_factor=0.08 + 0.02 * n_levels)
        p_fc = i_seg**2 * r_eq_fc * n_seg
        total = p_fc + common['cond_hs'] + common['cond_ls'] + common['sw_overlap'] + common['coss'] + common['gate'] + common['ind_dc'] + common['ind_core']
        return {
            'fc_equiv': p_fc,
            'cond_hs': common['cond_hs'], 'cond_ls': common['cond_ls'],
            'sw_overlap': common['sw_overlap'], 'coss': common['coss'], 'gate': common['gate'],
            'ind_dc': common['ind_dc'], 'ind_core': common['ind_core'],
            'delta_i_a': common['delta_i_a'], 'i_ph_rms_a': common['i_ph_rms_a'],
            'total': total, 'topology': f'FCML-{n_levels}L'
        }

    @staticmethod
    def two_stage_loss(gan_s1, gan_s2, ind, i_load_a, n_seg, n_phases,
                       f_sw_mhz, v_in=48.0, v_mid=5.0, v_out=1.0):
        f = f_sw_mhz * 1e6
        i_in_stage1 = i_load_a * v_out / max(v_mid, 1e-9)
        p_stage1_cond = i_in_stage1**2 * max(gan_s1.r_ds_on_hot * 1e-3, 1e-6) * 0.6
        p_stage1_sw = CompactPhysicalModel.switching_overlap_loss(v_in, i_in_stage1, gan_s1.t_rise, gan_s1.t_fall, 0.5e6, edges_per_cycle=2.0)
        p_stage1_coss = CompactPhysicalModel.coss_loss(gan_s1.c_oss, v_in, 0.5e6, edges_per_cycle=2.0)
        p_stage1_gate = CompactPhysicalModel.gate_drive_loss(gan_s1.q_g, gan_s1.v_gate, 0.5e6, gates=4.0)

        i_seg = i_load_a / n_seg
        common = ConversionLossModel._common_buck_terms(
            gan_s2, ind, i_seg, n_seg, n_phases, f_sw_mhz, v_mid, v_out,
            switch_multiplier=2.0, gate_multiplier=2.0)
        total = p_stage1_cond + p_stage1_sw + p_stage1_coss + p_stage1_gate + common['cond_hs'] + common['cond_ls'] + common['sw_overlap'] + common['coss'] + common['gate'] + common['ind_dc'] + common['ind_core']
        return {
            'stage1_cond': p_stage1_cond, 'stage1_sw': p_stage1_sw,
            'stage1_coss': p_stage1_coss, 'stage1_gate': p_stage1_gate,
            'cond_hs': common['cond_hs'], 'cond_ls': common['cond_ls'],
            'sw_overlap': common['sw_overlap'], 'coss': common['coss'], 'gate': common['gate'],
            'ind_dc': common['ind_dc'], 'ind_core': common['ind_core'],
            'delta_i_a': common['delta_i_a'], 'i_ph_rms_a': common['i_ph_rms_a'],
            'total': total,
            'topology': f'TwoStage-LLC+Buck({v_mid:.0f}V)'
        }


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 3b: PARALLEL SWEEP WORKER  (module-level — picklable on Windows)
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class SystemResult:
    name: str = ""
    n_vr: int = 0
    topology: str = ""
    gan_name: str = ""
    ind_name: str = ""
    architecture: str = "A2"
    f_sw_mhz: float = 0
    n_phases: int = 4
    conv_loss_w: float = 0
    ppdn_loss_w: float = 0
    total_loss_w: float = 0
    efficiency_pct: float = 0
    vr_footprint_mm2: float = 0
    max_vrs_possible: int = 0
    avg_nearest_dist_mm: float = 0
    vr_current_imbalance: float = 0
    max_temp_c: float = 0
    droop_mv: float = 0
    conv_breakdown: Dict = field(default_factory=dict)


def _sweep_chunk(args):
    """
    Process one (topo_name, nl, gan, ind) slice.

    All PPDN computation is vectorised (numpy broadcasting).
    Must be a top-level function for pickling on Windows (spawn start method).
    """
    (topo_name, nl, gan, ind, gans_40v,
     vr_counts, frequencies, architectures, v_mids,
     i_load, v_in, v_out, p_load,
     die_area, die_side, ambient_temp,
     pols_xy, rho_mohm_per_mm, i_out_total) = args

    rho       = rho_mohm_per_mm * 1e-3
    S         = len(pols_xy)
    i_per_pol = i_out_total / S

    chunk_results = []

    for n_vr in vr_counts:
        i_per_vr_val = i_load / n_vr
        for f_sw in frequencies:
            vr_fp   = SwitchSizingModel.vr_footprint_mm2(gan, i_per_vr_val, v_in, f_sw, ind)
            max_vrs = SwitchSizingModel.max_vrs_under_die(die_area, vr_fp)

            for arch in architectures:
                if n_vr > max_vrs and arch == "A2":
                    continue

                vr_pos = (DVPDRoutingModel.place_vrs_A2(n_vr, die_side)
                          if arch == "A2"
                          else DVPDRoutingModel.place_vrs_A1(n_vr, die_side))

                # ── Compact physical PPDN ────────────────────────────────────
                dx = np.abs(pols_xy[:, np.newaxis, 0] - vr_pos[np.newaxis, :, 0])
                dy = np.abs(pols_xy[:, np.newaxis, 1] - vr_pos[np.newaxis, :, 1])
                path_len_mm = np.maximum(dx + dy, 0.02)
                w_eff_mm = 0.25 * 2
                r_sheet = 0.49e-3
                r_vertical = (2 * 0.05 + 0.03) * 1e-3
                r_path = r_vertical + r_sheet * (path_len_mm / w_eff_mm)
                g_path = 1.0 / np.maximum(r_path, 1e-12)
                sum_g = g_path.sum(axis=1)
                r_eff = 1.0 / np.maximum(sum_g, 1e-12)
                ppdn_loss = float((i_per_pol**2 * r_eff).sum())
                avg_dist = float(path_len_mm.min(axis=1).mean())
                i_vr = (g_path / np.maximum(sum_g[:, np.newaxis], 1e-12) * i_per_pol).sum(axis=0)
                imbalance = float(i_vr.std() / max(i_vr.mean(), 1e-12))
                r_path_avg = float(r_eff.mean())

                # ── Conversion loss ──────────────────────────────────────────
                combos = []
                if topo_name == "DSCH":
                    conv = ConversionLossModel.dsch_loss(
                        gan, ind, i_load, n_vr, 4, f_sw, v_in, v_out)
                    combos = [(conv, f_sw, arch, "")]
                elif topo_name == "FCML":
                    conv = ConversionLossModel.fcml_loss(
                        gan, ind, i_load, n_vr, 4, f_sw, v_in, v_out, nl)
                    combos = [(conv, f_sw, arch, "")]
                elif topo_name == "TwoStage":
                    g2 = gans_40v[0] if gans_40v else gan
                    for vm in v_mids:
                        conv = ConversionLossModel.two_stage_loss(
                            gan, g2, ind, i_load, n_vr, 4, f_sw, v_in, vm, v_out)
                        combos.append((conv, f_sw, arch, f"vm{vm:.0f}"))

                for conv, fsw, ar, tag in combos:
                    total_loss = conv['total'] + ppdn_loss
                    eff = p_load / (p_load + total_loss) * 100 if total_loss >= 0 else 0
                    temp = CompactPhysicalModel.estimate_thermal_rise(
                        ambient_temp, conv['total'], n_vr, vr_fp)

                    if eff <= 0 or temp >= 125:
                        continue

                    i_step = 0.35 * i_load / n_vr
                    droop = CompactPhysicalModel.estimate_droop_mv(
                        i_step, n_vr, fsw * 1e6,
                        l_pkg_ph=35.0, decap_per_vr_uf=8.0,
                        decap_esr_mohm=0.15, decap_esl_ph=12.0,
                        r_path_ohm=r_path_avg)

                    name = (f"{topo_name}({gan.name}+{ind.name})"
                            + (f"[{tag}]" if tag else "")
                            + f" {n_vr}VR@{fsw}MHz {ar}")
                    chunk_results.append(SystemResult(
                        name=name, n_vr=n_vr, topology=conv['topology'],
                        gan_name=gan.name, ind_name=ind.name,
                        architecture=ar, f_sw_mhz=fsw, n_phases=4,
                        conv_loss_w=conv['total'], ppdn_loss_w=ppdn_loss,
                        total_loss_w=total_loss, efficiency_pct=eff,
                        vr_footprint_mm2=vr_fp, max_vrs_possible=max_vrs,
                        avg_nearest_dist_mm=avg_dist,
                        vr_current_imbalance=imbalance,
                        max_temp_c=temp, droop_mv=droop,
                        conv_breakdown=conv,
                    ))

    return chunk_results


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 4: FULL SYSTEM OPTIMIZER
# ═══════════════════════════════════════════════════════════════════════

class IntegratedOptimizer:
    """Joint optimization of topology x components x segments x frequency x placement."""

    def __init__(self, v_in: float = 48.0, v_out: float = 1.0,
                 p_load_w: float = 1000.0, die_area_mm2: float = 500.0):
        self.v_in = v_in
        self.v_out = v_out
        self.p_load = p_load_w
        self.i_load = p_load_w / v_out
        self.die = DieConfig(die_area_mm2=die_area_mm2,
                             die_side_mm=np.sqrt(die_area_mm2),
                             i_out_total_a=self.i_load, v_out=v_out)
        self.routing = DVPDRoutingModel(self.die)

    def evaluate(self, topology, gan, ind, n_vr, f_sw_mhz, n_phases=4,
                 arch="A2", v_mid=5.0, gan_s2=None, n_levels=4) -> SystemResult:
        res = SystemResult()
        res.n_vr = n_vr; res.topology = topology
        res.gan_name = gan.name; res.ind_name = ind.name
        res.architecture = arch; res.f_sw_mhz = f_sw_mhz; res.n_phases = n_phases

        i_per_vr = self.i_load / n_vr
        res.vr_footprint_mm2 = SwitchSizingModel.vr_footprint_mm2(
            gan, i_per_vr, self.v_in, f_sw_mhz, ind)
        res.max_vrs_possible = SwitchSizingModel.max_vrs_under_die(
            self.die.die_area_mm2, res.vr_footprint_mm2)

        if n_vr > res.max_vrs_possible and arch == "A2":
            res.efficiency_pct = 0
            res.name = f"INFEASIBLE: {n_vr} VRs > {res.max_vrs_possible} max"
            return res

        vr_pos = (DVPDRoutingModel.place_vrs_A2(n_vr, self.die.die_side_mm)
                  if arch == "A2"
                  else DVPDRoutingModel.place_vrs_A1(n_vr, self.die.die_side_mm))
        ppdn = self.routing.compute_ppdn_loss(vr_pos)
        res.ppdn_loss_w = ppdn['total_ppdn_loss_w']
        res.avg_nearest_dist_mm = ppdn['avg_nearest_dist_mm']
        res.vr_current_imbalance = ppdn['vr_current_imbalance']

        if topology == "DSCH":
            conv = ConversionLossModel.dsch_loss(gan, ind, self.i_load,
                                                  n_vr, n_phases, f_sw_mhz,
                                                  self.v_in, self.v_out)
        elif topology.startswith("FCML"):
            conv = ConversionLossModel.fcml_loss(gan, ind, self.i_load,
                                                  n_vr, n_phases, f_sw_mhz,
                                                  self.v_in, self.v_out, n_levels)
        elif topology == "TwoStage":
            g2 = gan_s2 or gan
            conv = ConversionLossModel.two_stage_loss(gan, g2, ind, self.i_load,
                                                       n_vr, n_phases, f_sw_mhz,
                                                       self.v_in, v_mid, self.v_out)
        else:
            raise ValueError(f"Unknown topology: {topology}")

        res.conv_loss_w = conv['total']
        res.conv_breakdown = conv
        res.total_loss_w = res.conv_loss_w + res.ppdn_loss_w
        res.efficiency_pct = self.p_load / (self.p_load + res.total_loss_w) * 100

        res.max_temp_c = CompactPhysicalModel.estimate_thermal_rise(
            self.die.ambient_temp_c, res.conv_loss_w, n_vr, res.vr_footprint_mm2)

        i_step = 0.35 * self.i_load / n_vr
        res.droop_mv = CompactPhysicalModel.estimate_droop_mv(
            i_step, n_vr, f_sw_mhz * 1e6,
            l_pkg_ph=self.die.pkg_loop_inductance_ph,
            decap_per_vr_uf=self.die.decap_per_vr_uf,
            decap_esr_mohm=self.die.decap_esr_mohm,
            decap_esl_ph=self.die.decap_esl_ph,
            r_path_ohm=ppdn['avg_r_eff_ohm'])

        res.name = f"{topology}({gan.name}+{ind.name}) {n_vr}VR@{f_sw_mhz}MHz {arch}"
        return res

    def lateral_baseline(self) -> SystemResult:
        """
        Conventional lateral PDN baseline.
        FIX: BSZ device is _SI_BASELINE (not in GAN_LIBRARY).
             Vishay inductor not in HVR_INDUCTOR_LIB — fall back to first entry.
        """
        si  = _SI_BASELINE                                      # fixed
        ind = next((i for i in INDUCTOR_LIBRARY if "Vishay" in i.name),
                   INDUCTOR_LIBRARY[0])                         # fixed
        p_iba  = self.p_load * (1/0.965 - 1)
        i_ph = self.i_load / 16; f = 0.5e6
        delta_i = CompactPhysicalModel.buck_ripple_current(12.0, self.v_out, max(getattr(ind, 'l_nh', 100.0) * 1e-9, 1e-9), f)
        i_rms = CompactPhysicalModel.inductor_rms(i_ph, delta_i)
        p_cond = i_rms**2 * si.r_ds_on_hot * 1e-3 * 16
        p_sw   = CompactPhysicalModel.switching_overlap_loss(12.0, i_ph, si.t_rise, si.t_fall, f, edges_per_cycle=32)
        p_coss = CompactPhysicalModel.coss_loss(si.c_oss, 12.0, f, edges_per_cycle=32)
        p_gate = CompactPhysicalModel.gate_drive_loss(si.q_g, si.v_gate, f, gates=32)
        p_ind  = i_rms**2 * max(getattr(ind, 'r_dcr_mohm', 1.0), 0.0) * 1e-3 * 16
        conv   = p_iba + p_cond + p_sw + p_coss + p_gate + p_ind
        ppdn   = self.i_load**2 * 0.18e-3
        total  = conv + ppdn
        return SystemResult(
            name="Lateral Baseline (IBA+Si Buck)", topology="Lateral",
            conv_loss_w=conv, ppdn_loss_w=ppdn, total_loss_w=total,
            efficiency_pct=self.p_load/(self.p_load+total)*100,
            droop_mv=CompactPhysicalModel.estimate_droop_mv(
                0.35 * self.i_load, 1, f,
                l_pkg_ph=80.0, decap_per_vr_uf=20.0,
                decap_esr_mohm=0.4, decap_esl_ph=25.0,
                r_path_ohm=0.18e-3))

    def full_sweep(self, verbose=True, n_workers: int = None) -> Dict:
        """
        Parallel design-space exploration using ProcessPoolExecutor.

        Parallelises at the (topo, nl, gan, ind) level — each task is
        an independent slice that evaluates all (n_vr, f_sw, arch) combos
        for one device+inductor pair.  PPDN is vectorised inside each task.

        n_workers: number of parallel processes (default = CPU count).
        """
        topologies    = [("DSCH",[4]), ("FCML",[3,4,5,6]), ("TwoStage",[4])]
        vr_counts     = [4, 8, 12, 16, 20, 24, 32, 48, 64, 80, 96]
        frequencies   = [1, 2, 3.36, 5, 8, 10, 15, 20, 30]
        architectures = ["A1", "A2"]
        v_mids        = [3, 5, 6, 8, 12]

        # Filter GaN to top-N by FOM = R_DS_ON * Q_G (lower = better)
        _hv_pool  = [g for g in GAN_LIBRARY if g.v_ds_max >= 80 and g.manufacturer == "EPC"]
        gans_100v = sorted(_hv_pool, key=lambda g: g.r_ds_on * g.q_g)[:12]
        _lv_pool  = [g for g in GAN_LIBRARY if 30 <= g.v_ds_max <= 60]
        gans_40v  = sorted(_lv_pool,  key=lambda g: g.r_ds_on * g.q_g)[:8]
        inductors = [i for i in INDUCTOR_LIBRARY if i.category != "discrete"]

        n_workers = n_workers or os.cpu_count() or 4

        # Precompute POL positions as numpy array (passed to each worker)
        pols_xy = self.routing.pols   # already np.ndarray (S, 2)

        # Build one task per (topo, nl, gan, ind) combination
        tasks = []
        for topo_name, level_opts in topologies:
            for nl in level_opts:
                for gan in gans_100v:
                    for ind in inductors:
                        tasks.append((
                            topo_name, nl, gan, ind, gans_40v,
                            vr_counts, frequencies, architectures, v_mids,
                            self.i_load, self.v_in, self.v_out, self.p_load,
                            self.die.die_area_mm2, self.die.die_side_mm,
                            self.die.ambient_temp_c,
                            pols_xy,
                            self.die.rho_mohm_per_mm,
                            self.die.i_out_total_a,
                        ))

        _n_ts  = sum(1 for t,_ in topologies if t=="TwoStage")
        _n_oth = sum(len(lv) for t,lv in topologies if t!="TwoStage")
        total_evals = (
            _n_oth * len(gans_100v) * len(inductors) * len(vr_counts) * len(frequencies) * len(architectures) +
            _n_ts  * len(gans_100v) * len(inductors) * len(vr_counts) * len(frequencies) * len(architectures) * len(v_mids)
        )

        if verbose:
            print(f"Full sweep: {len(tasks)} tasks on {n_workers} workers "
                  f"({total_evals:,} total evaluations)")
            print(f"  HV GaN: {len(gans_100v)}  LV GaN: {len(gans_40v)}  "
                  f"Inductors: {len(inductors)}")

        results = []
        done = 0
        report_every = max(1, len(tasks) // 20)   # report every ~5%

        with ProcessPoolExecutor(max_workers=n_workers) as pool:
            futures = {pool.submit(_sweep_chunk, t): t[0] for t in tasks}
            for fut in as_completed(futures):
                topo_label = futures[fut]
                try:
                    results.extend(fut.result())
                except Exception as exc:
                    if verbose:
                        print(f"  [WARN] {topo_label} chunk raised: {exc}")
                done += 1
                if verbose and (done % report_every == 0 or done == len(tasks)):
                    pct = done / len(tasks) * 100
                    print(f"  [{pct:5.1f}%] {done}/{len(tasks)} tasks done  |  "
                          f"feasible: {len(results):,}")

        results.sort(key=lambda x: x.efficiency_pct, reverse=True)
        baseline = self.lateral_baseline()
        if verbose:
            print(f"  Sweep complete — feasible: {len(results):,} / {total_evals:,}")
        return {'all': results, 'top20': results[:20],
                'baseline': baseline, 'count': total_evals}


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 5: PUBLICATION PLOTS
# ═══════════════════════════════════════════════════════════════════════

COLORS = {
    'navy':'#0A1628','teal':'#0891B2','cyan':'#22D3EE',
    'gold':'#F59E0B','accent':'#3B82F6','red':'#EF4444',
    'green':'#10B981','purple':'#8B5CF6','orange':'#F97316',
    'bg':'#F8FAFC','text':'#1E293B','muted':'#64748B','grid':'#E2E8F0',
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


def _best_gan_hv():
    pool = [g for g in GAN_LIBRARY if g.v_ds_max >= 80]
    if not pool:
        pool = list(GAN_LIBRARY)
    return sorted(pool, key=lambda g: g.r_ds_on_hot * g.q_g)[0]


def plot_paper_reproduction(opt: IntegratedOptimizer, save_path: str):
    """Reproduce GLSVLSI'24 Fig. 2: Power loss vs # VRs for A1 and A2."""
    setup_style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))
    gan = _best_gan_hv()
    ind = INDUCTOR_LIBRARY[3]
    vr_range = [4, 8, 12, 16, 20, 24, 32, 48, 64, 80, 96]

    for ax, arch, title in [(ax1,"A1","Architecture A1 (periphery)"),
                             (ax2,"A2","Architecture A2 (under die)")]:
        conv_l, ppdn_l, tots, annots = [], [], [], []
        for n in vr_range:
            best_r = None
            for f in [1, 1.25, 1.68, 2.6, 3.36, 5, 8]:
                r = opt.evaluate("DSCH", gan, ind, n, f, 4, arch)
                if r.efficiency_pct > 0 and (best_r is None or r.total_loss_w < best_r.total_loss_w):
                    best_r = r
            if best_r is None:
                best_r = opt.evaluate("DSCH", gan, ind, n, 3.36, 4, arch)
            conv_l.append(best_r.conv_loss_w)
            ppdn_l.append(best_r.ppdn_loss_w)
            tots.append(best_r.total_loss_w)
            annots.append(f"{best_r.f_sw_mhz:.1f} MHz\n{best_r.vr_footprint_mm2:.0f} mm2")

        ax.plot(vr_range, conv_l, 's-', color=COLORS['teal'],  lw=2, ms=5, label='Converter loss')
        ax.plot(vr_range, ppdn_l, 'D-', color=COLORS['gold'],  lw=2, ms=5, label='PPDN loss')
        ax.plot(vr_range, tots,   'o-', color=COLORS['red'],   lw=2.5, ms=6, label='Total loss')
        for i in [2, 5, 8]:
            if i < len(vr_range):
                ax.annotate(annots[i], (vr_range[i], tots[i]),
                            textcoords="offset points", xytext=(10,10), fontsize=7,
                            color=COLORS['muted'],
                            bbox=dict(boxstyle='round,pad=0.3', fc='white',
                                      ec=COLORS['grid'], alpha=0.9))
        ax.axhline(y=opt.p_load*0.30, color=COLORS['red'], ls='--', lw=1.5, alpha=0.5)
        ax.text(90, opt.p_load*0.30+8, '>30% commercial', fontsize=8,
                color=COLORS['red'], alpha=0.7, ha='right')
        ax.set_xlabel('Number of VRs', fontweight='bold')
        ax.set_ylabel('Power loss (W)', fontweight='bold')
        ax.set_title(title, fontweight='bold', fontsize=13)
        ax.legend(loc='upper right', fontsize=9, framealpha=0.9)
        ax.set_ylim(bottom=0); ax.set_xlim(0, 100)

    fig.suptitle("Optimised DVPD power loss — GLSVLSI'24 model with real GaN",
                 fontsize=12, fontweight='bold', y=1.01)
    fig.tight_layout()
    #fig.savefig(save_path, dpi=200, bbox_inches='tight', facecolor=COLORS['bg'])
    fig.savefig(save_path, dpi=200, facecolor=COLORS['bg'])
    plt.close()


def plot_topology_comparison(opt: IntegratedOptimizer, save_path: str):
    """DSCH vs FCML vs TwoStage efficiency and loss."""
    setup_style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))
    gan = _best_gan_hv()
    ind = INDUCTOR_LIBRARY[3]
    vr_range  = list(range(4, 97, 4))
    baseline  = opt.lateral_baseline()
    topo_cfgs = [
        ("DSCH",     "DSCH (paper's topology)",    COLORS['teal'],   's', {}),
        ("FCML",     "FCML 4-Level",               COLORS['accent'], 'D', {'n_levels':4}),
        ("FCML",     "FCML 6-Level",               COLORS['purple'], '^', {'n_levels':6}),
        ("TwoStage", "LLC+Buck (V_mid=5V)",         COLORS['gold'],   'o', {'v_mid':5.0}),
        ("TwoStage", "LLC+Buck (V_mid=8V)",         COLORS['orange'], 'v', {'v_mid':8.0}),
    ]
    for topo, label, color, marker, kwargs in topo_cfgs:
        effs, losses = [], []
        for n in vr_range:
            best = None
            for f in [3.36, 5, 8, 10, 15, 20]:
                nl = kwargs.get('n_levels', 4); vm = kwargs.get('v_mid', 5.0)
                _lv = [g for g in GAN_LIBRARY if 30 <= g.v_ds_max <= 60]
                g2 = (_lv[0] if _lv else GAN_LIBRARY[0]) if topo == "TwoStage" else None
                r = opt.evaluate(topo, gan, ind, n, f, 4, "A2", vm, g2, nl)
                if r.efficiency_pct > 0 and (best is None or r.efficiency_pct > best.efficiency_pct):
                    best = r
            effs.append(best.efficiency_pct if best else 0)
            losses.append(best.total_loss_w if best else 0)
        v1 = [(n,e) for n,e in zip(vr_range,effs)   if e > 0]
        v2 = [(n,l) for n,l in zip(vr_range,losses) if l > 0]
        if v1: ax1.plot([p[0] for p in v1],[p[1] for p in v1],
                        color=color,marker=marker,ms=4,lw=1.8,label=label)
        if v2:
            ax2.plot([p[0] for p in v2],[p[1] for p in v2],
                        color=color,marker=marker,ms=4,lw=1.8,label=label)
        else:
            ax2.text(0.5, 0.5, 'No feasible points for this topology with current constraints',
                     transform=ax2.transAxes, ha='center', va='center', fontsize=9, color=COLORS['muted'])

    ax1.axhline(y=baseline.efficiency_pct, color=COLORS['red'], ls='--', lw=2, alpha=0.7)
    ax1.text(80, baseline.efficiency_pct+0.5, f'Lateral {baseline.efficiency_pct:.1f}%',
             color=COLORS['red'], fontsize=9, fontweight='bold')
    ax1.set_xlabel('Number of VR segments', fontweight='bold')
    ax1.set_ylabel('System efficiency (%)', fontweight='bold')
    ax1.set_title('Efficiency — all topologies (A2)', fontweight='bold')
    ax1.legend(fontsize=8, loc='lower right', framealpha=0.9)
    ax2.axhline(y=baseline.total_loss_w, color=COLORS['red'], ls='--', lw=2, alpha=0.7)
    ax2.set_xlabel('Number of VR segments', fontweight='bold')
    ax2.set_ylabel('Total power loss (W)', fontweight='bold')
    ax2.set_title('Total loss — converter + PPDN routing', fontweight='bold')
    ax2.legend(fontsize=8, loc='upper right', framealpha=0.9); ax2.set_ylim(bottom=0)
    fig.tight_layout()
    #fig.savefig(save_path, dpi=200, bbox_inches='tight', facecolor=COLORS['bg'])
    fig.savefig(save_path, dpi=200, facecolor=COLORS['bg'])
    plt.close()


def plot_a1_vs_a2(opt: IntegratedOptimizer, save_path: str):
    """A1 vs A2 routing loss comparison."""
    setup_style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))
    gan = _best_gan_hv()
    ind = INDUCTOR_LIBRARY[3]
    vr_range = list(range(4, 97, 4))
    for arch, color, marker, label in [("A2", COLORS['teal'], 's', 'A2 (under die)'),
                                        ("A1", COLORS['gold'], 'D', 'A1 (periphery)')]:
        ppdn_v, total_v = [], []
        for n in vr_range:
            r = opt.evaluate("DSCH", gan, ind, n, 3.36, 4, arch)
            ppdn_v.append(r.ppdn_loss_w)
            total_v.append(r.total_loss_w if r.efficiency_pct > 0 else np.nan)
        ax1.plot(vr_range, ppdn_v, color=color, marker=marker, ms=4, lw=2,
                 label=f'{label} — PPDN')
        ax2.plot(vr_range, total_v, color=color, marker=marker, ms=4, lw=2,
                 label=f'{label} — Total')

    ax1.set_xlabel('Number of VRs', fontweight='bold')
    ax1.set_ylabel('PPDN routing loss (W)', fontweight='bold')
    ax1.set_title('PPDN routing loss: A1 vs A2', fontweight='bold')
    ax1.legend(fontsize=9); ax1.set_ylim(bottom=0)
    ax2.axhline(y=opt.p_load*0.30, color=COLORS['red'], ls='--', lw=1.5,
                alpha=0.5, label='>30% commercial')
    ax2.set_xlabel('Number of VRs', fontweight='bold')
    ax2.set_ylabel('Total loss (W)', fontweight='bold')
    ax2.set_title('Total loss: A1 vs A2', fontweight='bold')
    ax2.legend(fontsize=9); ax2.set_ylim(bottom=0)
    fig.tight_layout()
    #fig.savefig(save_path, dpi=200, bbox_inches='tight', facecolor=COLORS['bg'])
    fig.savefig(save_path, dpi=200, facecolor=COLORS['bg'])
    plt.close()


def plot_physical_intuition(opt: IntegratedOptimizer, save_path: str):
    """Illustrative figure: architecture sketch + power-flow/loss intuition."""
    setup_style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    # --- left: architecture cartoon ---
    ax1.set_title('Illustrative segmented DVPD concept', fontweight='bold')
    die = Rectangle((1.0, 1.6), 8.0, 4.6, facecolor='#edf4ff', edgecolor=COLORS['accent'], lw=2)
    ax1.add_patch(die)
    ax1.text(5.0, 5.8, 'Compute die / localized load regions', ha='center', va='center', fontweight='bold')
    for x in [2.0, 4.0, 6.0, 8.0]:
        ax1.add_patch(Rectangle((x-0.45, 3.2), 0.9, 1.0, facecolor='#ffffff', edgecolor=COLORS['teal'], lw=1.5))
        ax1.text(x, 3.7, 'POL', ha='center', va='center', fontsize=9)
        ax1.annotate('', xy=(x, 3.1), xytext=(x, 2.2), arrowprops=dict(arrowstyle='->', lw=1.8, color=COLORS['orange']))
        ax1.add_patch(Rectangle((x-0.55, 1.2), 1.1, 0.6, facecolor='#fff3e6', edgecolor=COLORS['orange'], lw=1.5))
        ax1.text(x, 1.5, 'VR', ha='center', va='center', fontsize=9, fontweight='bold')
    ax1.text(5.0, 0.55, 'Shorter vertical + lateral current paths reduce I²R drop and transient loop inductance',
             ha='center', va='center', fontsize=10, color=COLORS['muted'])
    ax1.set_xlim(0, 10); ax1.set_ylim(0, 7); ax1.axis('off')

    # --- right: power budget illustration ---
    ax2.set_title('Illustrative 1 kW power budget', fontweight='bold')
    stages = ['Load', 'Conv. loss', 'PDN loss']
    vals = [opt.p_load, 65, 20]
    bars = ax2.bar(stages, vals)
    for b, v in zip(bars, vals):
        ax2.text(b.get_x() + b.get_width()/2, v + 10, f'{v:.0f} W', ha='center', fontsize=10)
    ax2.text(0.5, 0.92, 'Illustrative target range for a sensible compact model:\nlosses should be tens to low hundreds of watts, not 10 kW.',
             transform=ax2.transAxes, ha='center', va='top', fontsize=10, color=COLORS['muted'])
    ax2.set_ylabel('Power (W)', fontweight='bold')
    ax2.set_ylim(0, max(vals)*1.25)
    ax2.grid(True, axis='y', alpha=0.25)

    fig.tight_layout()
    #fig.savefig(save_path, dpi=200, bbox_inches='tight', facecolor=COLORS['bg'])
    fig.savefig(save_path, dpi=200, facecolor=COLORS['bg'])
    plt.close()


def print_summary(results: Dict):
    bl  = results['baseline']
    top = results['top20']
    print("\n" + "="*110)
    print("VPD Framework (cowork) — parallel sweep + vectorised PPDN")
    print("="*110)
    print(f"System: 1000W, 48V->1V, I_load=1000A, Die=500mm2")
    print(f"Evaluated: {results['count']:,} | Feasible: {len(results['all']):,}")
    print(f"\nBASELINE: {bl.name}")
    print(f"  Eff:{bl.efficiency_pct:.1f}% | Loss:{bl.total_loss_w:.0f}W | "
          f"Conv:{bl.conv_loss_w:.0f}W | PDN:{bl.ppdn_loss_w:.0f}W")
    print(f"\n{'#':<3}{'Eff%':<7}{'Loss':<7}{'Conv':<7}{'PPDN':<7}"
          f"{'VRs':<5}{'Arch':<5}{'f_sw':<8}{'Topo':<22}{'GaN':<12}{'Inductor':<20}{'Droop'}")
    print("-"*110)
    for i, r in enumerate(top[:15]):
        print(f"{i+1:<3}{r.efficiency_pct:<7.1f}{r.total_loss_w:<7.0f}"
              f"{r.conv_loss_w:<7.0f}{r.ppdn_loss_w:<7.1f}"
              f"{r.n_vr:<5}{r.architecture:<5}{r.f_sw_mhz:<8.1f}"
              f"{r.topology:<22}{r.gan_name:<12}{r.ind_name:<20}{r.droop_mv:.1f}mV")
    if top:
        best = top[0]
        print(f"\nBEST: {best.name}")
        print(f"  Eff: {best.efficiency_pct:.2f}% | "
              f"vs baseline: +{best.efficiency_pct-bl.efficiency_pct:.1f} pp | "
              f"Loss cut: {(1-best.total_loss_w/bl.total_loss_w)*100:.0f}%")


# ═══════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║  VPD Framework — cowork (multicore parallel sweep)               ║")
    print("╚══════════════════════════════════════════════════════════════════╝\n")

    opt = IntegratedOptimizer(v_in=48.0, v_out=1.0, p_load_w=1000.0, die_area_mm2=500.0)

    results = opt.full_sweep(verbose=True)
    print_summary(results)

    print("\nGenerating figures...")
    plot_paper_reproduction(opt, "cw_fig1_paper_reproduction.png")
    print("  [1/3] Paper Fig.2 reproduction done")

    plot_topology_comparison(opt, "cw_fig2_topology_comparison.png")
    print("  [2/3] Topology comparison done")

    plot_a1_vs_a2(opt, "cw_fig3_a1_vs_a2.png")
    print("  [3/4] A1 vs A2 routing loss done")
    plot_physical_intuition(opt, "cw_fig4_physical_intuition.png")
    print("  [4/4] Physical-intuition illustration done")

    print("\nAll done! Figures: cw_fig1..3_*.png")