#!/usr/bin/env python3
"""Phase-0M Parts 23-26 -- from a free Robin coefficient to a physical cooling architecture.

WHAT IS THERE NOW
  h_top = 166 000 W/m2K, INVERSE-CALIBRATED in Phase 0F so the 1-kW package reaches the
  reference junction temperature of 84 C. h_bottom = 10 W/m2K (natural convection),
  T_coolant uniform. A calibrated film coefficient is not a cooling technology: it cannot
  be transferred to another architecture, it has no pumping cost, and it cannot produce a
  streamwise temperature gradient because its sink temperature is a single number.

WHAT THIS MODULE DOES
  Derives h from geometry and flow with source-backed correlations, charges the pressure
  drop and the pumping power, and computes the coolant temperature rise along the channel.
  Then it asks the only question that matters for the Robin boundary: can ONE coefficient
  and ONE sink temperature represent the result?

CORRELATIONS, all for the laminar regime these channels are in (Re < 2300):
  Nu   Shah & London fully-developed laminar Nusselt number for a rectangular duct, as a
       function of aspect ratio, 3 or 4 walls heated (tabulated below, interpolated)
  f    laminar friction factor f Re = C(alpha) for the same duct family
  fin  straight-fin efficiency eta = tanh(mL)/(mL), m = sqrt(2 h / (k_s t_fin))
  cal  caloric resistance R_cal = 1/(2 m_dot c_p) for the MEAN fluid temperature
"""
from __future__ import annotations
import csv, math, sys
from dataclasses import dataclass
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0m"
OUT.mkdir(parents=True, exist_ok=True)

# water at ~50 C
RHO_F, CP_F, K_F, MU_F = 988.0, 4181.0, 0.644, 5.47e-4
K_SI = 130.0
DIE_MM = 22.36
A_DIE_M2 = (DIE_MM * 1e-3) ** 2
Q_TOTAL_W = 1125.0                 # Phase-0F converged 1-kW heat load
H_CALIBRATED = 166000.0            # the incumbent Robin coefficient
T_TARGET_C = 84.0

# Shah & London, laminar fully-developed rectangular duct, constant wall temperature (T),
# aspect ratio alpha = short/long side.
_ALPHA = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0]
_NU_4W = [7.541, 5.858, 4.803, 4.114, 3.670, 3.391, 3.114, 2.976]   # 4 walls heated
_NU_3W = [5.385, 4.990, 4.409, 3.914, 3.538, 3.279, 3.018, 2.910]   # 3 walls heated
_FRE = [96.0, 84.68, 76.28, 70.55, 66.79, 64.00, 60.55, 56.91]      # f Re


def nu_lam(alpha: float, walls: int = 3) -> float:
    return float(np.interp(min(alpha, 1.0), _ALPHA, _NU_3W if walls == 3 else _NU_4W))


def f_re(alpha: float) -> float:
    return float(np.interp(min(alpha, 1.0), _ALPHA, _FRE))


@dataclass(frozen=True)
class Microchannel:
    """A microchannel cold plate over a square footprint."""
    w_ch_um: float
    h_ch_um: float
    t_fin_um: float
    length_mm: float = DIE_MM
    width_mm: float = DIE_MM
    t_base_um: float = 100.0
    k_solid: float = K_SI
    m_dot_g_s: float = 1.6
    t_in_c: float = 25.0
    walls_heated: int = 3

    @property
    def n_channels(self) -> int:
        return max(int(self.width_mm * 1e3 / (self.w_ch_um + self.t_fin_um)), 1)

    @property
    def d_h_m(self) -> float:
        w, h = self.w_ch_um * 1e-6, self.h_ch_um * 1e-6
        return 2 * w * h / (w + h)

    @property
    def alpha(self) -> float:
        return min(self.w_ch_um, self.h_ch_um) / max(self.w_ch_um, self.h_ch_um)

    def solve(self, q_w: float = Q_TOTAL_W) -> dict:
        w, h = self.w_ch_um * 1e-6, self.h_ch_um * 1e-6
        tf, L = self.t_fin_um * 1e-6, self.length_mm * 1e-3
        n = self.n_channels
        a_foot = (self.width_mm * 1e-3) * L
        m_dot = self.m_dot_g_s * 1e-3
        a_flow = n * w * h
        u = m_dot / (RHO_F * a_flow)
        re = RHO_F * u * self.d_h_m / MU_F
        regime = "laminar" if re < 2300 else ("transitional" if re < 4000 else "turbulent")
        if re < 2300:
            nu = nu_lam(self.alpha, self.walls_heated)
            f = f_re(self.alpha) / max(re, 1e-9)
        else:                                  # Gnielinski / Petukhov, reported as such
            pr = MU_F * CP_F / K_F
            fd = (0.79 * math.log(re) - 1.64) ** -2
            nu = ((fd / 8) * (re - 1000) * pr
                  / (1 + 12.7 * math.sqrt(fd / 8) * (pr ** (2 / 3) - 1)))
            f = fd
        h_ch = nu * K_F / self.d_h_m
        # fin efficiency: two fin halves of height h_ch, thickness tf
        m_fin = math.sqrt(2 * h_ch / (self.k_solid * max(tf, 1e-9)))
        eta_f = math.tanh(m_fin * h) / (m_fin * h) if m_fin * h > 1e-12 else 1.0
        a_wet = n * L * (w + 2 * eta_f * h)          # base + two fin flanks
        r_conv = 1.0 / (h_ch * a_wet)
        r_cal = 1.0 / (2 * m_dot * CP_F)             # mean-fluid convention
        r_base = (self.t_base_um * 1e-6) / (self.k_solid * a_foot)
        r_tot = r_conv + r_cal + r_base
        dt_fluid = q_w / (m_dot * CP_F)
        h_eff = 1.0 / (r_tot * a_foot)
        # pressure drop and pumping power
        dp = f * (L / self.d_h_m) * 0.5 * RHO_F * u ** 2
        v_dot = m_dot / RHO_F
        p_pump = dp * v_dot
        return {"w_ch_um": self.w_ch_um, "h_ch_um": self.h_ch_um,
                "t_fin_um": self.t_fin_um, "m_dot_g_s": self.m_dot_g_s,
                "n_channels": n, "aspect_ratio": self.alpha, "D_h_um": self.d_h_m * 1e6,
                "velocity_m_s": u, "Re": re, "regime": regime, "Nu": nu,
                "h_channel_W_m2K": h_ch, "fin_efficiency": eta_f,
                "area_amplification": a_wet / a_foot,
                "R_conv_K_W": r_conv, "R_caloric_K_W": r_cal, "R_base_K_W": r_base,
                "R_total_K_W": r_tot, "h_effective_W_m2K": h_eff,
                "h_eff_over_calibrated": h_eff / H_CALIBRATED,
                "dT_fluid_K": dt_fluid, "dT_junction_K": q_w * r_tot,
                "T_j_C": self.t_in_c + q_w * r_tot,
                "dp_kPa": dp / 1e3, "pump_W": p_pump,
                "pump_frac_of_load_pct": 100 * p_pump / 1000.0,
                "q_w": q_w}


def required_flow(dt_fluid_target_k: float, q_w: float = Q_TOTAL_W) -> float:
    """Mass flow, in g/s, that limits the coolant temperature rise to the target."""
    return 1e3 * q_w / (CP_F * dt_fluid_target_k)


def streamwise_profile(mc: Microchannel, q_w: float = Q_TOTAL_W, n: int = 40) -> dict:
    """Wall temperature along the flow, for the uniform-heat-flux case.

    A single Robin boundary with ONE sink temperature cannot produce a streamwise gradient.
    The real wall temperature rises by the full coolant temperature rise from inlet to
    outlet, and that gradient is in-plane -- exactly the kind that drives warpage.
    """
    s = mc.solve(q_w)
    m_dot = mc.m_dot_g_s * 1e-3
    x = np.linspace(0, 1, n)
    t_f = mc.t_in_c + q_w * x / (m_dot * CP_F)
    dt_wall_local = q_w * (s["R_conv"] if "R_conv" in s else s["R_conv_K_W"])
    t_w = t_f + dt_wall_local + q_w * s["R_base_K_W"]
    return {"x_frac": x, "T_fluid_C": t_f, "T_wall_C": t_w,
            "streamwise_gradient_K": float(t_w[-1] - t_w[0]),
            "streamwise_gradient_K_per_mm": float((t_w[-1] - t_w[0]) / mc.length_mm)}


ARCHITECTURES = {
    "TOP_MICROCHANNEL_SI": dict(w_ch_um=50, h_ch_um=300, t_fin_um=50, t_base_um=100,
                                k_solid=K_SI,
                                note="silicon microchannels etched in a lid over the die"),
    "TOP_MICROCHANNEL_CU": dict(w_ch_um=100, h_ch_um=500, t_fin_um=100, t_base_um=200,
                                k_solid=385.0, note="copper cold plate on a TIM"),
    "SUBSTRATE_EMBEDDED": dict(w_ch_um=100, h_ch_um=200, t_fin_um=100, t_base_um=50,
                               k_solid=K_SI,
                               note="June-2026 Sec. IV-D: channels inside the substrate "
                                    "adjacent to the GaN switch layer"),
    "TWO_SIDED": dict(w_ch_um=50, h_ch_um=300, t_fin_um=50, t_base_um=100, k_solid=K_SI,
                      note="top and substrate channels; each carries half the heat"),
    "AGGRESSIVE_TUCKERMAN": dict(w_ch_um=50, h_ch_um=302, t_fin_um=50, t_base_um=100,
                                 k_solid=K_SI,
                                 note="Tuckerman & Pease 1981 geometry, the canonical "
                                      "microchannel reference point"),
}


def main() -> int:
    rows = []
    for name, kw in ARCHITECTURES.items():
        note = kw.pop("note")
        for m_dot in (1.6, 5.0, 10.0, 27.0, 50.0):
            q = Q_TOTAL_W / 2 if name == "TWO_SIDED" else Q_TOTAL_W
            mc = Microchannel(m_dot_g_s=m_dot, **kw)
            s = mc.solve(q)
            sp = streamwise_profile(mc, q)
            s.update(architecture=name, note=note,
                     streamwise_gradient_K=sp["streamwise_gradient_K"],
                     streamwise_gradient_K_per_mm=sp["streamwise_gradient_K_per_mm"],
                     meets_84C=(s["T_j_C"] <= T_TARGET_C))
            rows.append(s)
            print(f"  {name:22s} m={m_dot:5.1f} g/s  Re={s['Re']:7.1f} {s['regime']:12s} "
                  f"h_ch={s['h_channel_W_m2K']:9.0f}  amp={s['area_amplification']:5.2f}  "
                  f"h_eff={s['h_effective_W_m2K']:10.0f} ({s['h_eff_over_calibrated']:5.2f}x) "
                  f"dT_f={s['dT_fluid_K']:7.1f}K  Tj={s['T_j_C']:7.1f}C  "
                  f"dp={s['dp_kPa']:8.1f}kPa  pump={s['pump_W']:7.3f}W", flush=True)
        kw["note"] = note
    keys = sorted({k for r in rows for k in r})
    with open(OUT / "cooling_architecture_sensitivity.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
    print(f"\n  flow needed for dT_fluid = 10 K: {required_flow(10.0):.1f} g/s "
          f"({required_flow(10.0)/1.6:.1f}x the stated 1.6 g/s)")
    print(f"  dT_fluid at the stated 1.6 g/s: {Q_TOTAL_W/(1.6e-3*CP_F):.1f} K")
    print(f"wrote {OUT/'cooling_architecture_sensitivity.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
