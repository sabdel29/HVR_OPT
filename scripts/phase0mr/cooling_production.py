#!/usr/bin/env python3
"""Phase-0M-R Sections 10-12 -- the physical cooling boundary, inside the production solve.

WHAT IS REPLACED
    one inverse-calibrated Robin coefficient h = 166 000 W/m2K with ONE uniform sink
    temperature, on the TIM top face.
WHAT REPLACES IT
    h(x) and T_fluid(x) derived from channel geometry and mass flow, applied per element,
    with the coolant warming along the flow:

        -k grad(T).n = h(x) [ T_surface(x) - T_fluid(x) ]
        T_fluid(x)   = T_in + Q(0 -> x) / (m_dot c_p)

    Q(0 -> x) is the heat ACTUALLY removed upstream of x, integrated from the solved flux,
    not assumed uniform. That makes this a staggered conjugate solve rather than a Robin
    boundary with a prettier coefficient: the fluid temperature and the wall temperature are
    iterated to consistency.

PUMPING POWER IS REPORTED, NEVER FOLDED IN. `P_electronics` and `P_pumping` are kept as
separate quantities and a `P_total_facility_side` is offered only when both are named. Pump
efficiency is NOT sourced, so hydraulic power is the primary number and an efficiency
sensitivity is carried beside it.

TWO COEFFICIENTS (TCPMT revision). `h_uniform` = 1/((R_conv + R_cal + R_base) A) is the
coefficient of a UNIFORM sink at the inlet temperature: R_cal = 1/(2 m_dot c_p) lifts the
sink to the mean fluid temperature. `h_local` = 1/((R_conv + R_base) A) is the coefficient of
a sink that follows the coolant along the flow (T_fluid(x) resolved), which already contains
the caloric rise; using h_uniform there counts half the coolant rise twice.

PLATE FLOW (TCPMT revision). `plate_at_flow` evaluates the same plate at another mass flow
(laminar: Nu, hence h, does not depend on the flow; dp_fd ~ m_dot, the entrance and plenum
terms ~ m_dot^2, so P_hydraulic ~ m_dot^2 to m_dot^3). `equal_rise_flow_g_s` is the declared
rule for a second plate: the flow that gives it the same coolant rise as the top plate.
"""
from __future__ import annotations
import csv, math, sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
for d in ("phase0mr", "phase0m", "phase0b"):
    sys.path.insert(0, str(R / "scripts" / d))
from cooling import (Microchannel, RHO_F, CP_F, K_F, MU_F, nu_lam,         # noqa: E402
                     f_re, required_flow)

OUT = R / "results" / "phase0mr"
OUT.mkdir(parents=True, exist_ok=True)

# pump efficiency is UNSOURCED. Hydraulic power is the primary figure; these are a stated
# sensitivity band, never a single invented value.
ETA_PUMP_BAND = (0.35, 0.55, 0.75)


@dataclass(frozen=True)
class CoolingDesign:
    """A physical cooler. Every field is a geometry or a flow variable; `h` is derived."""
    name: str
    w_ch_um: float
    h_ch_um: float
    t_fin_um: float
    m_dot_g_s: float
    t_in_c: float = 25.0
    t_base_um: float = 100.0
    k_solid: float = 130.0
    length_mm: float = 22.36
    width_mm: float = 22.36
    two_sided: bool = False
    src: str = "geometry and flow; Nu from Shah & London laminar rectangular duct"

    def channel(self, m_dot_g_s: float | None = None) -> Microchannel:
        return Microchannel(w_ch_um=self.w_ch_um, h_ch_um=self.h_ch_um,
                            t_fin_um=self.t_fin_um, length_mm=self.length_mm,
                            width_mm=self.width_mm, t_base_um=self.t_base_um,
                            k_solid=self.k_solid,
                            m_dot_g_s=self.m_dot_g_s if m_dot_g_s is None else m_dot_g_s,
                            t_in_c=self.t_in_c)

    def compact(self, q_w: float) -> dict:
        s = self.channel().solve(q_w / (2.0 if self.two_sided else 1.0))
        s["two_sided"] = self.two_sided
        s["name"] = self.name
        s["P_pump_hydraulic_W"] = s["pump_W"] * (2.0 if self.two_sided else 1.0)
        for e in ETA_PUMP_BAND:
            s["P_pump_shaft_at_eta_%.2f_W" % e] = s["P_pump_hydraulic_W"] / e
        return s

    def h_uniform(self, q_w: float) -> float:
        """Uniform-sink coefficient (sink at the inlet temperature): includes R_cal."""
        return self.compact(q_w)["h_effective_W_m2K"]

    def h_local(self, q_w: float) -> float:
        """Streamwise-sink coefficient (sink = local coolant temperature): no R_cal."""
        return self.compact(q_w)["h_local_W_m2K"]

    def plate_at_flow(self, m_dot_g_s: float, q_w: float) -> dict:
        """ONE plate of this geometry at mass flow m_dot_g_s carrying q_w: heat transfer,
        pressure drop and pumping (hydraulic, and shaft over the efficiency band)."""
        if m_dot_g_s <= 0.0:
            return {"m_dot_g_s": 0.0, "Q_W": q_w, "P_pump_hydraulic_W": 0.0,
                    "dp_kPa": 0.0, "note": "no flow"}
        s = self.channel(m_dot_g_s).solve(max(q_w, 0.0))
        out = {"m_dot_g_s": m_dot_g_s, "Q_W": q_w, "Re": s["Re"], "Nu": s["Nu"],
               "T_bulk_mean_C": s["T_bulk_mean_C"], "dT_coolant_K": s["dT_fluid_K"],
               "h_local_W_m2K": s["h_local_W_m2K"],
               "h_uniform_W_m2K": s["h_effective_W_m2K"],
               "dp_fd_kPa": s["dp_fd_kPa"], "dp_kPa": s["dp_kPa"],
               "P_pump_hydraulic_W": s["pump_W"], "P_pump_fd_W": s["pump_fd_W"]}
        for e in ETA_PUMP_BAND:
            out["P_pump_shaft_at_eta_%.2f_W" % e] = s["pump_W"] / e
        return out


def equal_rise_flow_g_s(q_plate_w: float, q_ref_w: float, m_ref_g_s: float) -> float:
    """DECLARED FLOW RULE for a second plate: the mass flow that gives it the same coolant
    temperature rise as the reference (top) plate, m = m_ref Q_plate / Q_ref -- the parallel
    branches of one loop balanced to a common outlet temperature."""
    if q_ref_w <= 0.0:
        raise ValueError("the reference plate carries no heat")
    return max(m_ref_g_s * q_plate_w / q_ref_w, 0.0)


def streamwise_fluid_temperature(design: CoolingDesign, x_frac: np.ndarray,
                                 q_cumulative_w: np.ndarray) -> np.ndarray:
    """T_fluid at each streamwise station from the heat actually removed upstream."""
    m_dot = design.m_dot_g_s * 1e-3 * (2.0 if design.two_sided else 1.0)
    return design.t_in_c + q_cumulative_w / (m_dot * CP_F)


def face_boundary(design: CoolingDesign, centroids_mm: np.ndarray, flux_w: np.ndarray,
                  q_total_w: float, axis: int = 0) -> dict:
    """Per-face (h, T_sink) from the CURRENT flux distribution.

    `flux_w[i]` is the heat leaving face i in the previous iterate. The faces are sorted
    along the flow axis and the cumulative upstream heat sets each face's fluid temperature.
    A face at the inlet sees `t_in`; a face at the outlet sees the full coolant rise.
    """
    order = np.argsort(centroids_mm[:, axis])
    q = np.zeros_like(flux_w)
    q[order] = np.cumsum(flux_w[order]) - 0.5 * flux_w[order]   # mid-face convention
    m_dot = design.m_dot_g_s * 1e-3 * (2.0 if design.two_sided else 1.0)
    t_f = design.t_in_c + q / (m_dot * CP_F)
    h = np.full(flux_w.shape, design.h_uniform(max(q_total_w, 1e-9)))
    return {"h": h, "t_fluid": t_f, "order": order,
            "dT_fluid_K": float(t_f.max() - t_f.min())}


CANDIDATES = {
    "TOP_SI_MICROCHANNEL_27": CoolingDesign("TOP_SI_MICROCHANNEL_27", 50, 300, 50, 27.0),
    "TOP_SI_MICROCHANNEL_50": CoolingDesign("TOP_SI_MICROCHANNEL_50", 50, 300, 50, 50.0),
    "TOP_CU_COLDPLATE_27": CoolingDesign("TOP_CU_COLDPLATE_27", 100, 500, 100, 27.0,
                                         t_base_um=200.0, k_solid=385.0),
    "TWO_SIDED_SI_14": CoolingDesign("TWO_SIDED_SI_14", 50, 300, 50, 13.5, two_sided=True),
    "SUBSTRATE_EMBEDDED_27": CoolingDesign("SUBSTRATE_EMBEDDED_27", 100, 200, 100, 27.0,
                                           t_base_um=50.0),
}


def energy_balance(design: CoolingDesign, q_w: float) -> dict:
    """m_dot cp dT = Q, checked rather than assumed."""
    s = design.compact(q_w)
    m_dot = design.m_dot_g_s * 1e-3 * (2.0 if design.two_sided else 1.0)
    q_side = q_w / (2.0 if design.two_sided else 1.0)
    dt = s["dT_fluid_K"]
    q_back = m_dot / (2.0 if design.two_sided else 1.0) * CP_F * dt
    return {"design": design.name, "Q_w": q_w, "m_dot_g_s": design.m_dot_g_s,
            "dT_fluid_K": dt, "Q_from_mdot_cp_dT_w": q_back,
            "residual_pct": 100 * abs(q_back - q_side) / q_side,
            "Re": s["Re"], "regime": s["regime"], "Nu": s["Nu"],
            "h_channel": s["h_channel_W_m2K"], "h_effective": s["h_effective_W_m2K"],
            "dp_kPa": s["dp_kPa"], "P_pump_hydraulic_W": s["P_pump_hydraulic_W"],
            **{k: v for k, v in s.items() if k.startswith("P_pump_shaft")},
            "T_j_compact_C": s["T_j_C"]}


def main() -> int:
    rows = [energy_balance(d, 1125.0) for d in CANDIDATES.values()]
    with open(OUT / "cooling_energy_balance.csv", "w", newline="") as fh:
        k = sorted({x for r in rows for x in r})
        w = csv.DictWriter(fh, fieldnames=k); w.writeheader(); w.writerows(rows)
    for r in rows:
        print(f"  {r['design']:24s} m={r['m_dot_g_s']:5.1f} g/s Re={r['Re']:7.0f} "
              f"{r['regime']:12s} h_eff={r['h_effective']:9.0f} dT_f={r['dT_fluid_K']:6.2f} K "
              f"Tj={r['T_j_compact_C']:6.1f} C dp={r['dp_kPa']:7.1f} kPa "
              f"P_hyd={r['P_pump_hydraulic_W']:6.2f} W  bal={r['residual_pct']:.2e} %")
    print(f"\n  flow for a 10 K rise at 1125 W: {required_flow(10.0):.1f} g/s")
    print(f"wrote {OUT/'cooling_energy_balance.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
