"""Phase-0D electrical model upgrade: geometry-derived TSV resistance, temperature
dependence, and the electrical-thermal fixed point.

WHY THIS MODULE EXISTS RATHER THAN AN EDIT UPSTREAM
---------------------------------------------------
`Scalable_Integrated_VR/` is a separate git repository holding a large body of untracked
work (Phase-0A audit: one commit, everything else untracked). Editing it in place risks that
work. The lateral PDN network is therefore RE-IMPLEMENTED here and proven numerically
identical to the upstream `DVPDRoutingModel.compute_ppdn_loss` by unit test, while the
converter loss reuses the upstream `compute_total_loss` formula unmodified. The exact
upstream patch that should eventually be merged is recorded in
`results/phase0d/electrical_model_validation.md`.

PROVENANCE TAGS: SOURCE_BACKED | MODEL_DERIVED | ASSUMPTION | OPEN
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Sequence

import numpy as np

REPO = Path(__file__).resolve().parents[2]
SIVR = REPO / "Scalable_Integrated_VR"
if str(SIVR / "src") not in sys.path:
    sys.path.insert(0, str(SIVR / "src"))

# ---------------------------------------------------------------------------
# Material / geometry constants
# ---------------------------------------------------------------------------
RHO_CU_20C = 17.0e-9        # Ohm.m   SOURCE_BACKED - June-2026 Table III ("Cu resistivity 17 nOhm.m")
ALPHA_CU = 3.93e-3          # 1/K     ASSUMPTION - standard bulk Cu TCR; same value as configs/phase0b
T_REF_RHO = 20.0            # degC    the temperature RHO_CU_20C refers to

# GaN R_DS(on) temperature coefficient. The EPC product table in this repository carries NO
# temperature data (columns: PartNumber, VDSmax, VGSmax, MaxRDS(on)@5VGS, QG, QGS, QGD, QOSS,
# ID, PulsedID, Package, Stock, Price), so this cannot be sourced from repository data.
# 0.0075/K gives ~1.75x at 125 degC, consistent with the normalised R_DS(on) curves EPC
# publishes for eGaN parts. Swept in the Phase-0D robustness study.
ALPHA_GAN_RDSON = 7.5e-3    # 1/K     ASSUMPTION (legacy single value, kept for old lineages)
# TCPMT revision: device-specific coefficients SOURCED from the datasheets' typical
# normalized R_DS(on) vs T_J curves, linear-equivalent over 25-125 degC:
#   EPC2014C (high side), Fig. 8, rev. May 2021: 1.60x at 125 C  -> 6.0e-3 /K
#   EPC2057  (low side),  Fig. 9, rev. Apr. 2025: 1.80x at 125 C -> 8.0e-3 /K
ALPHA_GAN_HS = 6.0e-3       # 1/K     SOURCE_BACKED (EPC2014C datasheet Fig. 8)
ALPHA_GAN_LS = 8.0e-3       # 1/K     SOURCE_BACKED (EPC2057 datasheet Fig. 9)
T_REF_DEVICE = 25.0         # degC    datasheet reference for R_DS(on) and inductor DCR

# June-2026 Table III TSV geometry - SOURCE_BACKED
TSV_D_M = 30.0e-6
TSV_PITCH_M = 60.0e-6
TSV_H_REF_M = 300.0e-6
TSV_R_REF_OHM = 7.1e-3      # June Table III quoted resistance at the reference geometry


# RDL lateral resistance. The upstream DieConfig default of 50 mOhm/mm is an UNCALIBRATED
# ASSUMPTION (Phase-0A audit: "not derived from trace width/thickness/sheet resistance").
# Phase 0D is the first phase to exercise the electrical objective at load, and it exposed
# that default as unphysical: it puts ~2100% IR drop on a 1 V / 60 A branch and drove the ET
# fixed point to 569 degC. Replaced by a geometry-derived plane resistance.
RDL_T_CU_M = 5.0e-6         # m  ASSUMPTION - Phase-0A recorded "RDL Cu thickness 5 um, UNSPECIFIED default"
RDL_W_EFF_M = 22.36e-3      # m  MODEL_DERIVED - full die width; power is delivered on a plane, not a trace


def rdl_rho_per_mm(T_c: float = 25.0, t_cu_m: float = RDL_T_CU_M,
                   w_eff_m: float = RDL_W_EFF_M) -> float:
    """Lateral RDL resistance per mm of Manhattan path, in mOhm/mm.

    R_per_mm = rho_Cu(T) / (t_cu * W_eff).
    """
    return rho_cu(T_c) / (t_cu_m * w_eff_m) * 1e-3 * 1e3


def rho_cu(T_c: float) -> float:
    """Copper resistivity at T (degC). rho = rho_20 * [1 + alpha (T - 20)]."""
    return RHO_CU_20C * (1.0 + ALPHA_CU * (T_c - T_REF_RHO))


def rdson_at(r25_ohm: float, T_c: float, alpha: float = ALPHA_GAN_RDSON) -> float:
    """GaN on-resistance at T. R(T) = R(25) * [1 + alpha (T - 25)]."""
    return r25_ohm * (1.0 + alpha * (T_c - T_REF_DEVICE))


def dcr_at(r25_ohm: float, T_c: float) -> float:
    """Inductor DC resistance at T - copper winding, so the Cu TCR applies."""
    return r25_ohm * (1.0 + ALPHA_CU * (T_c - T_REF_DEVICE))


# ---------------------------------------------------------------------------
# Geometry-derived TSV field
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TSVField:
    """A parallel field of cylindrical Cu through-substrate vias.

    R_single = rho(T) * h / A ,  A = pi d^2 / 4
    R_field  = R_single / n_parallel
    """
    d_m: float = TSV_D_M
    pitch_m: float = TSV_PITCH_M
    i_via_max_a: float = 0.033      # OPEN - see note in n_required()

    @property
    def area_m2(self) -> float:
        return math.pi * self.d_m ** 2 / 4.0

    def r_single(self, h_m: float, T_c: float = 25.0) -> float:
        if h_m <= 0:
            raise ValueError("TSV height must be positive")
        return rho_cu(T_c) * h_m / self.area_m2

    def n_required(self, current_a: float) -> int:
        """Vias needed to carry `current_a` at the per-via current limit.

        OPEN: the per-via limit is not stated in any source available here. June-2026
        Table III reports 30 202 TSVs on PL1 for a 1 kA load, which implies ~33 mA/via IF
        PL1 carries output current. If PL1 instead carries input-side RMS current
        (I_in,rms = I_out*sqrt(V_out/V_in) ~ 144 A) the implied limit is ~4.8 mA. Both are
        swept in the Phase-0D sensitivity study.
        """
        if current_a <= 0:
            return 1
        return max(1, math.ceil(current_a / self.i_via_max_a))

    def n_available(self, footprint_mm2: float) -> int:
        """Via sites physically available in a footprint at this pitch."""
        return max(1, int(footprint_mm2 * 1e-6 / self.pitch_m ** 2))

    def r_field(self, h_m: float, current_a: float, T_c: float = 25.0,
                footprint_mm2: float | None = None) -> tuple[float, int]:
        """Effective field resistance and via count, capped by available area."""
        n = self.n_required(current_a)
        if footprint_mm2 is not None:
            n = min(n, self.n_available(footprint_mm2))
        return self.r_single(h_m, T_c) / n, n

    def validate_against_june(self) -> dict:
        r = self.r_single(TSV_H_REF_M, T_REF_RHO)
        return {"h_m": TSV_H_REF_M, "d_m": self.d_m, "rho_Ohm_m": RHO_CU_20C,
                "area_m2": self.area_m2, "R_model_Ohm": r,
                "R_june_Ohm": TSV_R_REF_OHM,
                "error_pct": 100.0 * (r - TSV_R_REF_OHM) / TSV_R_REF_OHM}


# ---------------------------------------------------------------------------
# Lateral PDN network (numerically identical to the upstream implementation)
# ---------------------------------------------------------------------------

def lateral_pdn(pol_xy: np.ndarray, vr_xy: np.ndarray, i_total_a: float,
                rho_mohm_per_mm: float, f_sw_hz: float, r_bump_ohm: float,
                r_series_ohm: float = 0.0, f_ref_hz: float = 1e6,
                T_c: float = 25.0, temp_aware: bool = True) -> dict:
    """Manhattan parallel-conductance PDN.

        R_branch(i,j) = r_series + 2*R_bump + rho_ac(T) * d_ij
        rho_ac        = rho_dc(T) * sqrt(f_sw / f_ref)
        R_eff(i)      = 1 / sum_j 1/R_branch(i,j)

    With temp_aware=False and r_series=0 this reproduces the upstream
    `DVPDRoutingModel.compute_ppdn_loss` exactly.
    """
    s, n = len(pol_xy), len(vr_xy)
    i_per_pol = i_total_a / s
    scale = (1.0 + ALPHA_CU * (T_c - T_REF_RHO)) if temp_aware else 1.0
    rho_dc = rho_mohm_per_mm * 1e-3 * scale
    rho_ac = rho_dc * math.sqrt(max(float(f_sw_hz), 1.0) / f_ref_hz)

    dx = np.abs(pol_xy[:, None, 0] - vr_xy[None, :, 0])
    dy = np.abs(pol_xy[:, None, 1] - vr_xy[None, :, 1])
    dist = np.maximum(dx + dy, 0.01)
    r_branch = r_series_ohm + 2.0 * r_bump_ohm + rho_ac * dist

    g = 1.0 / r_branch
    g_sum = g.sum(axis=1)
    r_eff = 1.0 / g_sum
    p_lateral = float((i_per_pol ** 2 * r_eff).sum())
    frac = g / g_sum[:, None]
    i_per_vr = (frac * i_per_pol).sum(axis=0)

    return {"p_lateral_w": p_lateral, "i_per_vr_a": i_per_vr,
            "avg_nearest_dist_mm": float(dist.min(axis=1).mean()),
            "rho_ac_mohm_per_mm": rho_ac * 1e3,
            "vr_current_imbalance": float(i_per_vr.std() / i_per_vr.mean())
            if i_per_vr.mean() > 0 else 0.0}


def vertical_tsv_loss(i_per_vr_a: Sequence[float], h_sub_m: float, T_c: float,
                      field: TSVField, footprint_mm2: float,
                      path: str = "input", v_in: float = 48.0, v_out: float = 1.0,
                      efficiency: float = 0.85) -> dict:
    """Loss in the substrate TSV field, as a lumped series element per VR.

    The TSV field is a SHARED vertical element carrying one VR's full current, so it is
    modelled as a series term outside the lateral branch network rather than being
    duplicated into every branch (which would over-count it).

    `path` selects which current the field carries:
      'input'  - the validated Phase-0B/0C stack. The HVR tile is embedded at the TOP of
                 the substrate (`embed_from: top`) and the TSV field spans from the board
                 side up to the tile underside, so it carries CONVERTER INPUT current at
                 48 V: I_in = I_out * (V_out/V_in) / eta.
      'output' - a June-like architecture variant in which the vertical field instead
                 carries the 1 V output current. Reported as a labelled variant, NOT as the
                 validated vehicle.
    """
    out = {"path": path, "per_vr": []}
    total = 0.0
    for i_out in i_per_vr_a:
        i_v = i_out if path == "output" else i_out * (v_out / v_in) / efficiency
        r, n = field.r_field(h_sub_m, i_v, T_c, footprint_mm2)
        p = i_v ** 2 * r
        total += p
        out["per_vr"].append({"i_out_a": float(i_out), "i_via_path_a": float(i_v),
                              "n_via": int(n), "r_field_ohm": float(r), "p_w": float(p)})
    out["p_tsv_total_w"] = float(total)
    return out


# ---------------------------------------------------------------------------
# HVR converter design with temperature-dependent loss
# ---------------------------------------------------------------------------

@dataclass
class HVRDesign:
    """A converter design chosen at 25 degC, whose loss can be re-evaluated at any T.

    The architecture and the discrete device/passive selection are DESIGN-TIME choices made
    once by the upstream optimizer. Only the temperature-dependent resistances are updated,
    and the loss is recomputed with the upstream `compute_total_loss` formula unmodified.
    """
    label: str
    arch: object
    hs: object
    ls: object
    inductor: object
    capacitor: object
    f_sw_hz: float
    i_out_a: float
    v_in: float
    v_out: float
    area_mm2: float
    area_budget_mm2: float
    loss_25c_w: float
    j_target: float

    def loss_at(self, T_c: float, alpha_gan: float = ALPHA_GAN_RDSON) -> dict:
        from HVR_FULL_OPT_EPC_V2 import LossModelInputs, compute_total_loss
        hs_t = replace(self.hs, R_DS_ON=rdson_at(self.hs.R_DS_ON, T_c, alpha_gan))
        ls_t = replace(self.ls, R_DS_ON=rdson_at(self.ls.R_DS_ON, T_c, alpha_gan))
        ind_t = replace(self.inductor,
                        r_dcr_mohm=dcr_at(self.inductor.r_dcr_mohm, T_c))
        r = compute_total_loss(self.arch, LossModelInputs(
            hs_device=hs_t, ls_device=ls_t, inductor=ind_t, capacitor=self.capacitor,
            I_out=self.i_out_a, V_out=self.v_out, V_in=self.v_in, f_sw=self.f_sw_hz))
        return {"p_conv_w": r.total_loss, "p_cond_w": r.p_cond, "p_sw_w": r.p_sw,
                "delta_i_out_a": r.delta_i_out, "delta_v_out_v": r.delta_v_out,
                "T_c": T_c}

    @property
    def footprint_xy_mm(self) -> tuple[float, float]:
        """Square-tile approximation - see electrical_model_validation.md section 3.3."""
        a = math.sqrt(self.area_mm2)
        return a, a


def compile_hvr(i_out_a: float, j_target: float, v_in: float = 48.0, v_out: float = 1.0,
                target_component_count: int = 15,
                inductor_library=None, capacitor_library=None) -> HVRDesign | None:
    """Run the upstream optimizer and wrap the best feasible design.

    `inductor_library` / `capacitor_library` are pass-throughs added in Phase 0F so a
    HEIGHT-CONSTRAINED subset can be supplied; leaving them None reproduces every earlier
    phase exactly, because the upstream optimizer then falls back to its own full libraries.
    """
    import os
    from HVR_FULL_OPT_EPC_V2 import run_hvr_optimization
    cwd = os.getcwd()
    os.chdir(SIVR)                     # the optimizer opens EPC-Product-Table.csv by bare name
    try:
        res = run_hvr_optimization(I_out=i_out_a, V_in=v_in, V_out=v_out,
                                   I_target_density=j_target, verbose=False,
                                   target_component_count=target_component_count,
                                   inductor_library=inductor_library,
                                   capacitor_library=capacitor_library)
    finally:
        os.chdir(cwd)
    feas = [r for r in res if r.area_feasible and r.ripple_satisfied
            and np.isfinite(r.optimized_loss)]
    if not feas:
        return None
    b = min(feas, key=lambda r: r.optimized_loss)
    return HVRDesign(label=f"N{b.architecture.N}K{b.architecture.K}KA{b.architecture.K_A}"
                           f"_J{j_target:g}",
                     arch=b.architecture, hs=b.optimized_hs_device, ls=b.optimized_ls_device,
                     inductor=b.optimized_inductor, capacitor=b.optimized_capacitor,
                     f_sw_hz=b.optimized_f_sw, i_out_a=i_out_a, v_in=v_in, v_out=v_out,
                     area_mm2=b.total_area_mm2, area_budget_mm2=b.area_budget_mm2,
                     loss_25c_w=b.optimized_loss, j_target=j_target)
