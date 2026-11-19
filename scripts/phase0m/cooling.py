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

CORRELATIONS, all for the laminar regime these channels are in (Re < 2300):
  Nu   fully developed laminar, H1 boundary condition (axially uniform heat input,
       peripherally uniform wall temperature), THREE walls heated with one SHORT wall
       adiabatic -- the plate's geometry: a channel w wide and H tall (H >= w) heated
       through its base and both fin walls under an adiabatic cover. Shah & London (1978),
       "Laminar Flow Forced Convection in Ducts", Academic Press, the three-wall H1 fit
           Nu = 8.235 (1 - 1.883/b + 3.767/b^2 - 5.814/b^3 + 5.361/b^4 - 2/b^5),  b = H/w,
       as used for microchannel heat sinks by Qu & Mudawar, Int. J. Heat Mass Transfer 45
       (2002) 2549. b -> inf gives 8.235 (parallel plates, both heated), b = 1 gives 3.55
       (the tabulated square value 3.556), b = 6 gives 6.32.
       H1, not T: the heat input is uniform along the flow and the silicon walls (k = 130
       W/mK) hold the periphery nearly isothermal. The T table of the same family has the
       alpha -> 0 limit 7.541. The superseded table (_NU_3W_LEGACY, alpha -> 0 limit 5.385)
       is the variant with a LONG wall adiabatic, i.e. the wrong wall; kept only as the
       NU_MODEL = "legacy_3w_table" option.
  f    Darcy f Re of the same duct family, Shah & London polynomial
           f Re = 96 (1 - 1.3553 a + 1.9467 a^2 - 1.7012 a^3 + 0.9564 a^4 - 0.2537 a^5),
       a = short/long side (56.91 for a square duct, 96 for parallel plates)
  dp   fully developed f (L/D_h) rho u^2/2, plus the developing-flow increment K(inf) and
       the plenum contraction/expansion losses (declared coefficients K_INF, K_CONTRACTION,
       K_EXPANSION) times rho u^2/2
  fin  straight-fin efficiency eta = tanh(mL)/(mL), m = sqrt(2 h / (k_s t_fin)), adiabatic
       tip (the cover)
  cal  caloric resistance R_cal = 1/(2 m_dot c_p) for the MEAN fluid temperature: it belongs
       to a UNIFORM-sink coefficient only (h_effective); a boundary whose sink temperature
       follows the coolant along the flow uses R_conv + R_base alone (h_local)
  props water at the BULK MEAN temperature T_in + Q/(2 m_dot c_p), from the IAPWS
       formulations as tabulated by the NIST Chemistry WebBook (SRD 69) at 0.1013 MPa:
       IAPWS-95 (rho, c_p), IAPWS 2008 (mu), IAPWS 2011 (k). Optional wall-viscosity
       correction for laminar heating of a liquid (WALL_VISCOSITY): Nu (mu_b/mu_w)^0.14 and
       f (mu_w/mu_b)^0.58 (Kakac, Shah & Aung, Handbook of Single-Phase Convective Heat
       Transfer, Wiley 1987, ch. 3, after Deissler), with the mean wetted-wall temperature
       from the compact model.
  The previous constant property set (water at ~50 C) is kept as LEGACY_PROPS: it is the
  set the conjugate CFD reference (research/final_closure/reference_cooling_icepak.json) was
  solved with, so the CFD comparison evaluates the correlation with it (cfd_comparison()).

MANIFOLD PLATE (TCPMT round 3, approved by the authors). Microchannel.n_zones = n splits the
  plate into n streamwise zones fed by ALTERNATING inlet and outlet headers in a manifold layer
  over the channels (headers at x = 0, L/n, 2L/n, ... : in, out, in, out, ...; zone k flows +x
  for even k, -x for odd k). Every zone is one pass of length L/n carrying m_dot/n through all
  the channels, so per pass:
       u, Re  -> 1/n          fully developed laminar Nu, hence h: unchanged
       dp_fd  = f (L/n) / D_h rho u^2/2  -> 1/n^2  (f Re fixed)
       entrance K(inf) and plenum terms  -> 1/n^2  (on the zone's dynamic pressure)
       coolant rise per zone (Q/n)/((m_dot/n) c_p) = Q/(m_dot c_p): unchanged
       bulk mean temperature, caloric resistance R_cal = 1/(2 m_dot c_p): unchanged
  plus a DECLARED header estimate (manifold only): two 90-degree turns header -> channel ->
  header (K_TURN each, on the channel dynamic pressure) and the dividing / combining header
  losses (K_HEADER_IN + K_HEADER_OUT on the header dynamic pressure of an interior header,
  which feeds or collects two zones, 2 m_dot/n, through a slot HEADER_SLOT_FRAC x L/n wide and
  HEADER_DEPTH_MM deep) -- typical sharp-turn and dividing/combining-flow coefficients of the
  order tabulated by Idelchik (Handbook of Hydraulic Resistance), not a manifold CFD.
  Developing flow: L_h and L_th scale with Re, so L_th/L_zone and x* = L_zone/(D_h Re Pr) are
  the SAME as for the single pass (L/n and m_dot/n leave L/(Re D_h) unchanged): each short
  zone is thermally developing over the same fraction as the single-pass channel and the fully
  developed Nu stays a lower bound on the pass-mean Nu (developing_flow_check()).
  PLATE_MODEL selects the PRODUCTION plate's construction ("manifold": MANIFOLD_ZONES zones;
  "single_pass": the pre-round-3 plate, variant plate_single_pass); it acts only on designs
  that ask for the production construction (cooling_production.CoolingDesign n_zones=None).
  A bare Microchannel is single pass unless n_zones is given.
"""
from __future__ import annotations
import csv, json, math, sys
from dataclasses import dataclass
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0m"
OUT.mkdir(parents=True, exist_ok=True)

# LEGACY constant property set: water at ~50 C. The CFD reference was solved with exactly
# these values; module constants keep their historical meaning for every importer.
RHO_F, CP_F, K_F, MU_F = 988.0, 4181.0, 0.644, 5.47e-4
LEGACY_PROPS = {"T_C": 50.0, "rho": RHO_F, "cp": CP_F, "k": K_F, "mu": MU_F,
                "source": "legacy constant set, water at ~50 C (the CFD reference's set)"}
K_SI = 130.0
DIE_MM = 22.36
A_DIE_M2 = (DIE_MM * 1e-3) ** 2
Q_TOTAL_W = 1125.0                 # Phase-0F converged 1-kW heat load
H_CALIBRATED = 166000.0            # the incumbent Robin coefficient
T_TARGET_C = 84.0

# Liquid water, NIST Chemistry WebBook SRD 69: IAPWS-95 (rho, cp), IAPWS 2008 viscosity,
# IAPWS 2011 thermal conductivity; 10-80 C at 0.101325 MPa, 90-150 C saturated liquid (a
# pressurized loop; liquid properties barely depend on pressure). Linear interpolation; the
# 5-K steps of the operating range reproduce the formulations to < 0.1 % in rho, cp, k and
# < 0.3 % in mu.
_WATER_T_C = (10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0, 55.0, 60.0, 70.0, 80.0,
              90.0, 100.0, 120.0, 150.0)
_WATER = {
    "rho": (999.70, 999.10, 998.21, 997.05, 995.65, 994.03, 992.22, 990.21, 988.04,
            985.69, 983.20, 977.76, 971.79, 965.31, 958.35, 943.11, 917.01),
    "cp": (4195.5, 4188.0, 4184.1, 4181.3, 4179.8, 4178.6, 4178.5, 4179.6, 4180.6,
           4182.3, 4184.3, 4189.5, 4196.3, 4205.0, 4215.7, 4244.8, 4310.8),
    "k": (0.5800, 0.5894, 0.5984, 0.6071, 0.6154, 0.6233, 0.6305, 0.6372, 0.6435,
          0.6492, 0.6543, 0.6631, 0.6700, 0.6753, 0.6791, 0.6831, 0.6820),
    "mu": (1.3059e-3, 1.1375e-3, 1.0016e-3, 0.8900e-3, 0.7972e-3, 0.7191e-3, 0.6527e-3,
           0.5958e-3, 0.5465e-3, 0.5036e-3, 0.4660e-3, 0.4035e-3, 0.3544e-3, 0.3145e-3,
           0.2818e-3, 0.2321e-3, 0.1826e-3),
}
WATER_SOURCE = ("NIST Chemistry WebBook SRD 69: IAPWS-95 (rho, c_p), IAPWS 2008 (mu), "
                "IAPWS 2011 (k); 0.1013 MPa to 80 C, saturated liquid 90-150 C; linear in T")

#: production model choices (variants set these in their own process)
PROPS_MODEL = "bulk_mean"            # "bulk_mean" | "legacy_50C"
NU_MODEL = "H1_3wall_short_adiabatic"  # | "legacy_3w_table"
WALL_VISCOSITY = False               # Sieder-Tate/Deissler-type correction (optional)
#: developing-flow increment for a rectangular duct of aspect ratio 1/6 (Shah & London 1978,
#: interpolated between 0.125 and 0.25) and the plenum losses: sudden contraction into and
#: expansion out of the channel array (declared, typical values)
K_INF, K_CONTRACTION, K_EXPANSION = 0.85, 0.5, 1.0
NU_WALL_EXP, F_WALL_EXP = 0.14, 0.58
#: production plate construction (TCPMT round 3): "manifold" (MANIFOLD_ZONES streamwise zones,
#: alternating inlet/outlet headers) | "single_pass" (variant plate_single_pass)
PLATE_MODEL = "manifold"
MANIFOLD_ZONES = 4
#: DECLARED manifold header estimate: a 90-degree turn into and out of the channels (each on the
#: channel dynamic pressure); dividing (inlet) and combining (outlet, incl. the exit) header
#: losses on the dynamic pressure of an interior header slot (HEADER_SLOT_FRAC of the zone
#: length wide, HEADER_DEPTH_MM deep, carrying two zones' flow)
K_TURN = 1.0
K_HEADER_IN, K_HEADER_OUT = 1.0, 1.5
HEADER_SLOT_FRAC = 0.5
HEADER_DEPTH_MM = 2.0
PLATE_MODELS = ("manifold", "single_pass")


def production_zones() -> int:
    """Streamwise zones of the PRODUCTION plate under PLATE_MODEL."""
    if PLATE_MODEL == "manifold":
        return int(MANIFOLD_ZONES)
    if PLATE_MODEL == "single_pass":
        return 1
    raise ValueError(f"unknown PLATE_MODEL {PLATE_MODEL!r} (known {PLATE_MODELS})")


def nu_mean_developing_ratio(x_star: float) -> float:
    """Pass-mean over fully developed Nu for thermally developing laminar flow, H boundary
    condition, at x* = L/(D_h Re Pr): Shah's circular-duct fit (Shah & London 1978),
    Nu_m = 1.953 x*^(-1/3) (x* <= 0.03), 4.364 + 0.0722/x* (x* > 0.03), divided by 4.364.
    INDICATIVE for the rectangular channel (the ratio, not the level, is transferred)."""
    if x_star <= 0.0:
        return float("inf")
    nu_m = 1.953 * x_star ** (-1.0 / 3.0) if x_star <= 0.03 else 4.364 + 0.0722 / x_star
    return nu_m / 4.364


def water_props(t_c: float) -> dict:
    """rho, cp, k, mu of liquid water at t_c (10-150 C), with the source."""
    if not (_WATER_T_C[0] <= t_c <= _WATER_T_C[-1]):
        raise ValueError(f"water properties tabulated for 10-150 C, asked {t_c:.2f} C")
    p = {k: float(np.interp(t_c, _WATER_T_C, v)) for k, v in _WATER.items()}
    p.update(T_C=float(t_c), source=WATER_SOURCE)
    return p


# Shah & London tabulated families, kept for the legacy option and the regression record.
_ALPHA = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0]
_NU_4W = [7.541, 5.858, 4.803, 4.114, 3.670, 3.391, 3.114, 2.976]          # 4 walls, T
_NU_3W_LEGACY = [5.385, 4.990, 4.409, 3.914, 3.538, 3.279, 3.018, 2.910]   # LONG wall adiabatic
_NU_3W = _NU_3W_LEGACY             # historical name
_FRE_LEGACY = [96.0, 84.68, 76.28, 70.55, 66.79, 64.00, 60.55, 56.91]      # f Re table


def nu_h1_3wall_short_adiabatic(b: float) -> float:
    """Shah & London three-wall H1 fit, one SHORT wall adiabatic, b = H/w >= 1."""
    if b < 1.0 - 1e-12:
        raise ValueError(f"short-wall-adiabatic fit needs H >= w (b = {b:.3f})")
    return 8.235 * (1 - 1.883 / b + 3.767 / b ** 2 - 5.814 / b ** 3 + 5.361 / b ** 4
                    - 2.0 / b ** 5)


def nu_h1_4wall(alpha: float) -> float:
    """Shah & London four-wall H1 polynomial, alpha = short/long."""
    a = min(alpha, 1.0)
    return 8.235 * (1 - 2.0421 * a + 3.0853 * a ** 2 - 2.4765 * a ** 3 + 1.0578 * a ** 4
                    - 0.1861 * a ** 5)


def nu_lam(alpha: float, walls: int = 3, model: str | None = None,
           long_wall_heated_only: bool = False) -> float:
    """Fully developed laminar Nu. alpha = short/long side. walls = 3: base and both fin
    walls heated, cover adiabatic; with H >= w the cover is a SHORT wall (the production
    plate). `long_wall_heated_only` flags a channel wider than tall (cover = long wall)."""
    model = model or NU_MODEL
    if model == "legacy_3w_table":
        return float(np.interp(min(alpha, 1.0), _ALPHA, _NU_3W_LEGACY if walls == 3 else _NU_4W))
    if walls == 4:
        return nu_h1_4wall(alpha)
    if long_wall_heated_only:
        # cover on a LONG wall: the long-wall-adiabatic family (tabulated, legacy table)
        return float(np.interp(min(alpha, 1.0), _ALPHA, _NU_3W_LEGACY))
    return nu_h1_3wall_short_adiabatic(1.0 / max(min(alpha, 1.0), 1e-12))


def f_re(alpha: float, model: str | None = None) -> float:
    """Darcy f Re, fully developed laminar rectangular duct."""
    model = model or NU_MODEL
    a = min(alpha, 1.0)
    if model == "legacy_3w_table":
        return float(np.interp(a, _ALPHA, _FRE_LEGACY))
    return 96.0 * (1 - 1.3553 * a + 1.9467 * a ** 2 - 1.7012 * a ** 3 + 0.9564 * a ** 4
                   - 0.2537 * a ** 5)


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
    #: streamwise manifold zones (1 = single pass; see MANIFOLD PLATE in the module notes)
    n_zones: int = 1

    @property
    def zones(self) -> int:
        return max(int(self.n_zones), 1)

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

    def props(self, q_w: float, props: dict | None = None) -> dict:
        """Fluid properties for this heat load: an explicit set, the legacy set, or water at
        the bulk mean temperature T_in + q/(2 m_dot c_p) (fixed point; c_p barely moves)."""
        if props is not None:
            return dict(props)
        if PROPS_MODEL == "legacy_50C":
            return dict(LEGACY_PROPS)
        m_dot = self.m_dot_g_s * 1e-3
        t_b = self.t_in_c
        for _ in range(4):
            p = water_props(t_b)
            t_new = self.t_in_c + q_w / (2.0 * m_dot * p["cp"])
            if abs(t_new - t_b) < 1e-6:
                break
            t_b = t_new
        p = water_props(t_b)
        p["basis"] = "bulk mean temperature"
        return p

    def solve(self, q_w: float = Q_TOTAL_W, props: dict | None = None,
              wall_viscosity: bool | None = None) -> dict:
        wall_viscosity = WALL_VISCOSITY if wall_viscosity is None else wall_viscosity
        p = self.props(q_w, props)
        rho, cp, kf, mu = p["rho"], p["cp"], p["k"], p["mu"]
        w, h = self.w_ch_um * 1e-6, self.h_ch_um * 1e-6
        tf, L = self.t_fin_um * 1e-6, self.length_mm * 1e-3
        n = self.n_channels
        a_foot = (self.width_mm * 1e-3) * L
        m_dot = self.m_dot_g_s * 1e-3
        a_flow = n * w * h
        # one pass: the whole channel (single pass) or one manifold zone (L/nz, m_dot/nz)
        nz = self.zones
        L_pass, m_pass = L / nz, m_dot / nz
        u = m_pass / (rho * a_flow)
        re = rho * u * self.d_h_m / mu
        pr = mu * cp / kf
        regime = "laminar" if re < 2300 else ("transitional" if re < 4000 else "turbulent")
        if re < 2300:
            nu0 = nu_lam(self.alpha, self.walls_heated,
                         long_wall_heated_only=(self.h_ch_um < self.w_ch_um))
            f0 = f_re(self.alpha) / max(re, 1e-9)
        else:                                  # Gnielinski / Petukhov, reported as such
            fd = (0.79 * math.log(re) - 1.64) ** -2
            nu0 = ((fd / 8) * (re - 1000) * pr
                   / (1 + 12.7 * math.sqrt(fd / 8) * (pr ** (2 / 3) - 1)))
            f0 = fd
        r_cal = 1.0 / (2 * m_dot * cp)             # mean-fluid convention
        r_base = (self.t_base_um * 1e-6) / (self.k_solid * a_foot)
        t_bulk = self.t_in_c + q_w * r_cal
        mu_w, t_w, nu, f = mu, t_bulk, nu0, f0

        def thermal(nu_):
            h_ch_ = nu_ * kf / self.d_h_m
            m_fin = math.sqrt(2 * h_ch_ / (self.k_solid * max(tf, 1e-9)))
            eta_ = math.tanh(m_fin * h) / (m_fin * h) if m_fin * h > 1e-12 else 1.0
            a_wet_ = n * L * (w + 2 * eta_ * h)      # base + two fin flanks
            a_tot_ = n * L * (w + 2 * h)
            return h_ch_, eta_, a_wet_, a_tot_
        h_ch, eta_f, a_wet, a_tot = thermal(nu)
        if wall_viscosity and re < 2300:
            for _ in range(20):
                # mean wetted-wall excess over the bulk: q / (h A_total) (fin flanks colder
                # than the base by the fin efficiency)
                t_w_new = t_bulk + q_w / (h_ch * a_tot)
                mu_w = water_props(min(max(t_w_new, 10.0), 150.0))["mu"]
                nu = nu0 * (mu / mu_w) ** NU_WALL_EXP
                f = f0 * (mu_w / mu) ** F_WALL_EXP
                h_ch, eta_f, a_wet, a_tot = thermal(nu)
                if abs(t_w_new - t_w) < 1e-4:
                    t_w = t_w_new
                    break
                t_w = t_w_new
        r_conv = 1.0 / (h_ch * a_wet)
        r_tot = r_conv + r_cal + r_base
        r_loc = r_conv + r_base
        dt_fluid = q_w / (m_dot * cp)
        h_eff = 1.0 / (r_tot * a_foot)
        h_loc = 1.0 / (r_loc * a_foot)
        # pressure drop and pumping power: one pass (the zones are in parallel)
        q_dyn = 0.5 * rho * u ** 2
        dp_fd = f * (L_pass / self.d_h_m) * q_dyn
        dp_ent = K_INF * q_dyn if re < 2300 else 0.0
        dp_pl = (K_CONTRACTION + K_EXPANSION) * q_dyn
        hdr = self.header_estimate(rho, q_dyn) if nz > 1 else None
        dp_turn = hdr["dp_turns_Pa"] if hdr else 0.0
        dp_hdr = hdr["dp_headers_Pa"] if hdr else 0.0
        dp = dp_fd + dp_ent + dp_pl + dp_turn + dp_hdr
        v_dot = m_dot / rho
        p_pump = dp * v_dot
        return {"w_ch_um": self.w_ch_um, "h_ch_um": self.h_ch_um,
                "t_fin_um": self.t_fin_um, "m_dot_g_s": self.m_dot_g_s,
                "n_channels": n, "aspect_ratio": self.alpha, "D_h_um": self.d_h_m * 1e6,
                "velocity_m_s": u, "Re": re, "Pr": pr, "regime": regime,
                "Nu": nu, "Nu_isoviscous": nu0, "nu_model": NU_MODEL,
                "fRe": f * re, "fRe_isoviscous": f0 * re,
                "props": {k: p[k] for k in ("T_C", "rho", "cp", "k", "mu")},
                "props_basis": p.get("basis", p.get("source")),
                "T_bulk_mean_C": t_bulk, "wall_viscosity": bool(wall_viscosity),
                "T_wall_mean_C": t_w if wall_viscosity else None,
                "mu_wall_Pa_s": mu_w if wall_viscosity else None,
                "h_channel_W_m2K": h_ch, "fin_efficiency": eta_f,
                "area_amplification": a_wet / a_foot,
                "R_conv_K_W": r_conv, "R_caloric_K_W": r_cal, "R_base_K_W": r_base,
                "R_total_K_W": r_tot, "R_local_K_W": r_loc,
                "h_effective_W_m2K": h_eff, "h_local_W_m2K": h_loc,
                "h_eff_over_calibrated": h_eff / H_CALIBRATED,
                "dT_fluid_K": dt_fluid, "dT_junction_K": q_w * r_tot,
                "T_j_C": self.t_in_c + q_w * r_tot,
                "dp_fd_kPa": dp_fd / 1e3, "dp_entrance_kPa": dp_ent / 1e3,
                "dp_plenum_kPa": dp_pl / 1e3, "dp_turns_kPa": dp_turn / 1e3,
                "dp_header_kPa": dp_hdr / 1e3, "dp_kPa": dp / 1e3,
                "K_inf": K_INF, "K_contraction": K_CONTRACTION, "K_expansion": K_EXPANSION,
                "pump_fd_W": dp_fd * v_dot, "pump_W": p_pump,
                "V_dot_ml_min": v_dot * 6e7,
                "pump_frac_of_load_pct": 100 * p_pump / 1000.0,
                "L_hydrodynamic_entrance_mm": 0.05 * re * self.d_h_m * 1e3,
                "L_thermal_entrance_mm": 0.05 * re * pr * self.d_h_m * 1e3,
                "n_zones": nz, "pass_length_mm": L_pass * 1e3,
                "m_dot_per_pass_g_s": m_pass * 1e3,
                "header": ({k: v for k, v in hdr.items() if not k.endswith("_Pa")}
                           if hdr else None),
                "developing_flow": self.developing_flow_check(re, pr),
                "q_w": q_w}

    def header_estimate(self, rho: float, q_dyn_channel: float) -> dict:
        """DECLARED header losses of the manifold (module notes): two 90-degree turns on the
        channel dynamic pressure, and the dividing/combining losses of an interior header slot
        (two zones' flow) on its own dynamic pressure."""
        nz = self.zones
        m_hdr = self.m_dot_g_s * 1e-3 * min(2.0, float(nz)) / nz
        w_slot = HEADER_SLOT_FRAC * self.length_mm / nz
        a_hdr = w_slot * 1e-3 * HEADER_DEPTH_MM * 1e-3
        u_hdr = m_hdr / (rho * a_hdr)
        q_hdr = 0.5 * rho * u_hdr ** 2
        return {"K_turn": K_TURN, "K_header_in": K_HEADER_IN, "K_header_out": K_HEADER_OUT,
                "slot_width_mm": w_slot, "depth_mm": HEADER_DEPTH_MM,
                "m_dot_interior_header_g_s": m_hdr * 1e3, "u_header_m_s": u_hdr,
                "q_dyn_header_kPa": q_hdr / 1e3,
                "dp_turns_Pa": 2.0 * K_TURN * q_dyn_channel,
                "dp_headers_Pa": (K_HEADER_IN + K_HEADER_OUT) * q_hdr,
                "basis": "declared: 90-degree turns + dividing/combining interior header "
                         "(Idelchik-order coefficients), not a manifold CFD"}

    def developing_flow_check(self, re: float, pr: float) -> dict:
        """Entrance lengths against ONE pass (the zone for a manifold): the fraction of the pass
        that is still developing and the indicative pass-mean Nu enhancement over the fully
        developed value used in production."""
        L_pass = self.length_mm / self.zones
        dh_mm = self.d_h_m * 1e3
        l_h, l_th = 0.05 * re * dh_mm, 0.05 * re * pr * dh_mm
        x_star = L_pass / (dh_mm * re * pr) if re > 0 else float("inf")
        return {"pass_length_mm": L_pass, "L_h_mm": l_h, "L_th_mm": l_th,
                "L_h_over_pass": l_h / L_pass, "L_th_over_pass": l_th / L_pass,
                "x_star": x_star, "Graetz_pass": 1.0 / x_star if x_star else float("inf"),
                "Nu_mean_developing_over_fd": nu_mean_developing_ratio(x_star),
                "production_h": "fully developed Nu (a lower bound on the pass mean)"}


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
    t_f = mc.t_in_c + q_w * x / (m_dot * s["props"]["cp"])
    dt_wall_local = q_w * s["R_conv_K_W"]
    t_w = t_f + dt_wall_local + q_w * s["R_base_K_W"]
    return {"x_frac": x, "T_fluid_C": t_f, "T_wall_C": t_w,
            "streamwise_gradient_K": float(t_w[-1] - t_w[0]),
            "streamwise_gradient_K_per_mm": float((t_w[-1] - t_w[0]) / mc.length_mm)}


ICEPAK_REF = R / "research" / "final_closure" / "reference_cooling_icepak.json"


def cfd_comparison(path: Path = ICEPAK_REF) -> dict:
    """The correlation against the matched conjugate CFD (Icepak, one half pitch, uniform
    flux, constant properties = LEGACY_PROPS) at the CFD's exact loading: mean base rise,
    the along-channel wall-minus-bulk difference and the pressure drop. Evaluated with the
    CFD's property set and without the wall-viscosity correction, so only the heat-transfer
    model differs. The Nu model is the one in force (NU_MODEL)."""
    j = json.loads(Path(path).read_text())
    inp = j["inputs"]
    mc = Microchannel(w_ch_um=inp["w_ch_um"], h_ch_um=inp["h_ch_um"],
                      t_fin_um=inp["t_fin_um"], t_base_um=inp["t_base_um"],
                      k_solid=inp["k_solid"], length_mm=inp["length_mm"],
                      width_mm=inp["width_mm"], m_dot_g_s=inp["m_dot_total_g_s"],
                      t_in_c=inp["t_in_c"])
    q = inp["Q_W"]
    s = mc.solve(q, props=LEGACY_PROPS, wall_viscosity=False)
    # the CFD loads one pitch with Q*pitch/width, the correlation divides Q by n channels:
    # rescale every per-channel term to the CFD's exact loading
    pitch_mm = (inp["w_ch_um"] + inp["t_fin_um"]) * 1e-3
    q_ch_cfd = q * pitch_mm / inp["width_mm"]
    q_ch_cor = q / s["n_channels"]
    lf = q_ch_cfd / q_ch_cor
    dt_mean = q * lf * (s["R_conv_K_W"] + s["R_base_K_W"] + s["R_caloric_K_W"])
    wmb = q * lf * (s["R_conv_K_W"] + s["R_base_K_W"])
    lv = {k: v for k, v in j["levels"].items() if v.get("solved")}
    fin = max(lv, key=lambda k: lv[k]["cells"])
    cfd = lv[fin]
    along = j.get("along_channel_check", {})
    st = [{"x_mm": x["x_mm"], "cfd_wall_minus_bulk_K": x["wall_minus_bulk_K"],
           "correlation_K": wmb,
           "rel_diff_corr_vs_cfd": (wmb - x["wall_minus_bulk_K"]) / x["wall_minus_bulk_K"]}
          for x in along.get("stations", [])]
    # implied developing-flow number of the CFD on top of the fully developed f Re
    q_dyn = 0.5 * LEGACY_PROPS["rho"] * s["velocity_m_s"] ** 2
    k_inf_cfd = (cfd["dp_kPa"] * 1e3 - s["dp_fd_kPa"] * 1e3) / q_dyn
    return {"cfd_level": fin, "cfd_cells": cfd["cells"], "nu_model": NU_MODEL,
            "Nu": s["Nu"], "h_channel_W_m2K": s["h_channel_W_m2K"],
            "fin_efficiency": s["fin_efficiency"], "loading_factor": lf,
            "dT_base_mean_cfd_K": cfd["dT_base_mean_K"],
            "dT_base_mean_correlation_K": dt_mean,
            "dT_base_mean_rel_diff": (dt_mean - cfd["dT_base_mean_K"]) / cfd["dT_base_mean_K"],
            "wall_minus_bulk_fully_developed_K": wmb, "along_channel": st,
            "dp_cfd_kPa": cfd["dp_kPa"], "dp_fd_correlation_kPa": s["dp_fd_kPa"],
            "dp_fd_plus_entrance_correlation_kPa": s["dp_fd_kPa"] + s["dp_entrance_kPa"],
            "K_inf_implied_by_cfd": k_inf_cfd, "K_inf_declared": K_INF,
            "props": "LEGACY_PROPS (the CFD's constant set)", "source": str(path.name)}


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
            s = {k: v for k, v in s.items() if not isinstance(v, dict)}
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
