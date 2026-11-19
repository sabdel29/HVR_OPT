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

MANIFOLD PLATE (TCPMT round 3). The production plate (CANDIDATES["TOP_SI_MICROCHANNEL_27"],
n_zones=None) takes its construction from cooling.PLATE_MODEL: production "manifold" = four
streamwise zones fed by alternating inlet/outlet headers (dp about 1/16 of the single pass,
same h and the same coolant rise per zone); "single_pass" is variant plate_single_pass. Every
plate of that design -- the top plate and any second plate under its own flow rule -- follows
the same construction. `streamwise_cumulative` is the 1-D coolant model of such a plate on the
FE faces: one coolant temperature per streamwise column of faces, rising from the zone's inlet
header in its own flow direction (a sawtooth/triangle wave over the plate for n > 1).
"""
from __future__ import annotations
import csv, math, sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
for d in ("phase0mr", "phase0m", "phase0b"):
    sys.path.insert(0, str(R / "scripts" / d))
import cooling as _C                                                     # noqa: E402
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
    #: streamwise manifold zones; None = the PRODUCTION construction (cooling.PLATE_MODEL)
    n_zones: int | None = 1

    def zones(self) -> int:
        """Streamwise zones of this plate (the production plate follows cooling.PLATE_MODEL)."""
        return _C.production_zones() if self.n_zones is None else max(int(self.n_zones), 1)

    def channel(self, m_dot_g_s: float | None = None) -> Microchannel:
        return Microchannel(w_ch_um=self.w_ch_um, h_ch_um=self.h_ch_um,
                            t_fin_um=self.t_fin_um, length_mm=self.length_mm,
                            width_mm=self.width_mm, t_base_um=self.t_base_um,
                            k_solid=self.k_solid,
                            m_dot_g_s=self.m_dot_g_s if m_dot_g_s is None else m_dot_g_s,
                            t_in_c=self.t_in_c, n_zones=self.zones())

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
               "n_zones": s["n_zones"], "dp_fd_kPa": s["dp_fd_kPa"],
               "dp_entrance_kPa": s["dp_entrance_kPa"], "dp_plenum_kPa": s["dp_plenum_kPa"],
               "dp_turns_kPa": s["dp_turns_kPa"], "dp_header_kPa": s["dp_header_kPa"],
               "dp_kPa": s["dp_kPa"],
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


def streamwise_cumulative(x_mm, w, n_zones: int = 1, x_range=None,
                          tol_mm: float = 1e-6) -> np.ndarray:
    """Upstream sum of `w` (heat, or area for a uniform first guess) seen by each face of a
    plate under the 1-D coolant model of an n-zone manifold (n = 1: the single pass).

    Faces at one streamwise position (centroid x within tol_mm) form a COLUMN with ONE coolant
    temperature: every face of a column gets the w of the columns upstream of it in its
    zone plus half the column's own w (mid-column convention). The plate's streamwise extent
    x_range = (x_lo, x_hi) (default: the face centroids' range) is cut into n equal zones; a
    face belongs to the zone of its centroid; zone k flows +x from its inlet header at its low
    end when k is even and -x from its high end when k is odd (alternating inlet and outlet
    headers). The coolant temperature of a face is then T_in + n cum / (m_dot c_p): each zone
    carries m_dot / n."""
    x = np.asarray(x_mm, float)
    w = np.asarray(w, float)
    n = max(int(n_zones), 1)
    lo, hi = ((float(x.min()), float(x.max())) if x_range is None
              else (float(x_range[0]), float(x_range[1])))
    if n == 1 or hi <= lo:
        zone = np.zeros(len(x), int)
    else:
        zone = np.clip(np.floor((x - lo) / (hi - lo) * n).astype(int), 0, n - 1)
    cum = np.zeros(len(x))
    for z in range(n):
        sel = np.flatnonzero(zone == z)
        if not len(sel):
            continue
        cols, inv = np.unique(np.round(x[sel] / tol_mm).astype(np.int64), return_inverse=True)
        qc = np.bincount(inv, weights=w[sel], minlength=len(cols))
        if z % 2:                                   # flows toward -x
            before = (np.cumsum(qc[::-1]) - qc[::-1])[::-1]
        else:
            before = np.cumsum(qc) - qc
        cum[sel] = before[inv] + 0.5 * qc[inv]
    return cum


def zone_of(x_mm, n_zones: int = 1, x_range=None) -> np.ndarray:
    """Manifold zone of each face (the assignment streamwise_cumulative uses)."""
    x = np.asarray(x_mm, float)
    n = max(int(n_zones), 1)
    lo, hi = ((float(x.min()), float(x.max())) if x_range is None
              else (float(x_range[0]), float(x_range[1])))
    if n == 1 or hi <= lo:
        return np.zeros(len(x), int)
    return np.clip(np.floor((x - lo) / (hi - lo) * n).astype(int), 0, n - 1)


def zone_relaxation(x_mm, area_mm2, h_w_m2k, n_zones, x_range, alpha_k_per_w) -> np.ndarray:
    """Per-face relaxation of a manifold plate's sink update, w = 1 / (1 + alpha G_zone).

    A zone's coolant rise is alpha q_zone (alpha = n dT / Q_plate for a sized plate,
    n / (m_dot c_p) at a fixed flow), and the heat it takes falls by at most G_zone = h A_zone
    per kelvin its sink rises (the film conductance: the bound reached when the solid behind
    the plate is laterally isothermal, e.g. a board of high in-plane conductivity). Direct
    substitution then has a loop gain up to alpha G_zone (about 18 for the Z1 cooling-B plate),
    and the linearized consistent update s_new = s + (s_target - s) / (1 + alpha G_zone) is
    stable for any smaller true sensitivity."""
    z = zone_of(x_mm, n_zones, x_range)
    a = np.asarray(area_mm2, float) * 1e-6
    g = np.bincount(z, weights=float(h_w_m2k) * a, minlength=max(int(n_zones), 1))
    return 1.0 / (1.0 + float(alpha_k_per_w) * g[z])


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
    # the PRODUCTION plate: its construction follows cooling.PLATE_MODEL (round 3: the 4-zone
    # manifold; variant plate_single_pass restores the single pass)
    "TOP_SI_MICROCHANNEL_27": CoolingDesign(
        "TOP_SI_MICROCHANNEL_27", 50, 300, 50, 27.0, n_zones=None,
        src="geometry and flow; Nu from Shah & London laminar rectangular duct; "
            "construction from cooling.PLATE_MODEL (production: 4-zone manifold)"),
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
