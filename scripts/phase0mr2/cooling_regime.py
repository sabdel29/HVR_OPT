#!/usr/bin/env python3
"""Phase-0M-R2 Section 5 --- explicit correlation-regime dispatch with declared domains.

Phase 0M-R reported h = 166 000 W/m2K, dp = 1.46 MPa and 74 W of pumping at 50 g/s. That
point sits at Re = 2342, which is:

  * ABOVE the laminar correlation's ceiling of 2300, and
  * BELOW Gnielinski's floor of 3000.

`scripts/phase0m/cooling.py` labelled it `transitional` and evaluated Gnielinski anyway.
The jump is not small: Nu goes from 4.603 to 12.699 across the threshold, a factor of
2.76, so the reported h is set by the choice of correlation rather than by the flow.

This module refuses to extrapolate. A point with no valid correlation is returned as
OUT_OF_MODEL_DOMAIN, with both neighbouring values shown as a BRACKET so the size of the
ignorance is visible.
"""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

import yaml

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0mr", "scripts/phase0m", "scripts"):
    sys.path.insert(0, str(R / p))

import cooling as C                                                     # noqa: E402

CFG = R / "configs" / "phase0mr2" / "cooling_model.yaml"
OUT = R / "results" / "phase0mr2"

LAMINAR, TRANSITIONAL, TURBULENT = "laminar", "transitional", "turbulent"
OUT_OF_DOMAIN = "OUT_OF_MODEL_DOMAIN"


class ModelDomainError(Exception):
    """An operating point outside every validated correlation."""


def cfg() -> dict:
    return yaml.safe_load(CFG.read_text())


def classify(re: float, c: dict) -> str:
    lam, gni = c["correlations"]["nusselt_laminar_fd"], c["correlations"]["nusselt_gnielinski"]
    if re <= lam["re_max"]:
        return LAMINAR
    if re >= gni["re_min"]:
        return TURBULENT
    return TRANSITIONAL


def nu_laminar(alpha: float, walls: int) -> float:
    return C.nu_lam(alpha, walls)


def nu_gnielinski(re: float, pr: float) -> float:
    fd = (0.79 * math.log(re) - 1.64) ** -2
    return ((fd / 8) * (re - 1000) * pr
            / (1 + 12.7 * math.sqrt(fd / 8) * (pr ** (2 / 3) - 1)))


def evaluate(m_dot_g_s: float, c: dict | None = None, q_w: float = 1000.0,
             strict: bool = True) -> dict:
    """One operating point, with its regime, its correlation and that correlation's domain.

    `strict=True` (the default, and what production must use) raises rather than returning
    a number for a point no validated correlation covers.
    """
    c = c or cfg()
    ch_c, f = c["channel"], c["fluid"]
    ch = C.Microchannel(w_ch_um=ch_c["w_ch_um"], h_ch_um=ch_c["h_ch_um"],
                        t_fin_um=ch_c["t_fin_um"], length_mm=ch_c["length_mm"],
                        width_mm=ch_c["width_mm"], t_base_um=ch_c["t_base_um"],
                        k_solid=ch_c["k_solid_w_mk"], m_dot_g_s=m_dot_g_s,
                        t_in_c=f["t_ref_c"])
    n = ch.n_channels
    w, h = ch.w_ch_um * 1e-6, ch.h_ch_um * 1e-6
    L = ch.length_mm * 1e-3
    a_flow = n * w * h
    m_dot = m_dot_g_s * 1e-3
    u = m_dot / (f["rho_kg_m3"] * a_flow)
    d_h = ch.d_h_m
    re = f["rho_kg_m3"] * u * d_h / f["mu_pa_s"]
    pr = f["prandtl"]
    regime = classify(re, c)

    # thermal entrance length: the laminar table is the FULLY DEVELOPED value
    l_th = 0.05 * re * pr * d_h
    dev_frac = l_th / L

    rec = {"m_dot_total_g_s": m_dot_g_s, "m_dot_per_channel_g_s": m_dot_g_s / n,
           "n_channels": n, "w_ch_um": ch.w_ch_um, "h_ch_um": ch.h_ch_um,
           "D_h_um": d_h * 1e6, "flow_area_mm2": a_flow * 1e6,
           "velocity_m_s": u, "rho_kg_m3": f["rho_kg_m3"], "mu_Pa_s": f["mu_pa_s"],
           "k_W_mK": f["k_w_mk"], "cp_J_kgK": f["cp_j_kgk"], "Pr": pr, "Re": re,
           "regime": regime, "L_thermal_entry_mm": l_th * 1e3,
           "L_channel_mm": L * 1e3, "entry_fraction": dev_frac,
           "fully_developed": dev_frac < 0.1,
           "dT_coolant_K": q_w / (m_dot * f["cp_j_kgk"]),
           "T_coolant_max_C": f["t_ref_c"] + q_w / (m_dot * f["cp_j_kgk"])}

    nu_l = nu_laminar(ch.alpha, ch.walls_heated)
    nu_t = nu_gnielinski(re, pr) if re > 1000 else float("nan")
    if regime == LAMINAR:
        nu, f_d = nu_l, C.f_re(ch.alpha) / re
        rec.update(nu_correlation="Shah & London laminar FD",
                   nu_validity="Re <= 2300, fully developed",
                   friction_correlation="f Re = C(alpha) laminar",
                   friction_validity="Re <= 2300", in_domain=True)
    elif regime == TURBULENT:
        nu, f_d = nu_t, (0.79 * math.log(re) - 1.64) ** -2
        rec.update(nu_correlation="Gnielinski", nu_validity="3000 <= Re <= 5e6",
                   friction_correlation="Petukhov", friction_validity="3000 <= Re <= 5e6",
                   in_domain=True)
    else:
        rec.update(nu_correlation=OUT_OF_DOMAIN,
                   nu_validity="no validated correlation for 2300 < Re < 3000",
                   friction_correlation=OUT_OF_DOMAIN,
                   friction_validity="no validated correlation for 2300 < Re < 3000",
                   in_domain=False,
                   Nu_laminar_bracket=nu_l, Nu_turbulent_bracket=nu_t,
                   bracket_ratio=nu_t / nu_l)
        if strict:
            raise ModelDomainError(
                f"Re = {re:.1f} lies between the laminar ceiling (2300) and Gnielinski's "
                f"floor (3000). No validated correlation covers it. The two neighbours "
                f"give Nu = {nu_l:.3f} and Nu = {nu_t:.3f}, a factor of {nu_t/nu_l:.2f}, "
                f"so the answer would be set by the choice and not by the flow.")
        nu, f_d = float("nan"), float("nan")

    if rec["in_domain"]:
        h_ch = nu * f["k_w_mk"] / d_h
        tf = ch.t_fin_um * 1e-6
        m_fin = math.sqrt(2 * h_ch / (ch.k_solid * max(tf, 1e-9)))
        eta = math.tanh(m_fin * h) / (m_fin * h) if m_fin * h > 1e-12 else 1.0
        a_foot = (ch.width_mm * 1e-3) * L
        a_wet = n * L * (w + 2 * eta * h)
        r_conv = 1.0 / (h_ch * a_wet)
        r_cal = 1.0 / (2 * m_dot * f["cp_j_kgk"])
        r_base = (ch.t_base_um * 1e-6) / (ch.k_solid * a_foot)
        r_tot = r_conv + r_cal + r_base
        dp = f_d * (L / d_h) * 0.5 * f["rho_kg_m3"] * u ** 2
        rec.update(Nu=nu, friction_factor=f_d, h_channel_W_m2K=h_ch,
                   fin_efficiency=eta, area_amplification=a_wet / a_foot,
                   R_conv_K_W=r_conv, R_caloric_K_W=r_cal, R_base_K_W=r_base,
                   R_total_K_W=r_tot, h_effective_W_m2K=1.0 / (r_tot * a_foot),
                   dp_kPa=dp / 1e3, dp_MPa=dp / 1e6,
                   P_pump_hydraulic_W=dp * (m_dot / f["rho_kg_m3"]),
                   pump_pct_of_load=100.0 * dp * (m_dot / f["rho_kg_m3"]) / q_w)
    else:
        for k in ("Nu", "friction_factor", "h_channel_W_m2K", "h_effective_W_m2K",
                  "dp_kPa", "dp_MPa", "P_pump_hydraulic_W", "pump_pct_of_load",
                  "R_total_K_W"):
            rec[k] = float("nan")
    return rec


def main() -> int:
    c = cfg()
    rows = []
    for op in c["operating_points"]:
        try:
            r = evaluate(op["m_dot_g_s"], c, strict=True)
            r["status"] = "IN DOMAIN"
        except ModelDomainError as exc:
            r = evaluate(op["m_dot_g_s"], c, strict=False)
            r["status"] = f"OUT_OF_MODEL_DOMAIN: {exc}"
        r["point_id"] = op["id"]
        r["why"] = op["why"]
        rows.append(r)
        print(f"  {op['id']:20s} m={op['m_dot_g_s']:5.1f} g/s  Re={r['Re']:7.1f}  "
              f"{r['regime']:12s}  Nu={r.get('Nu', float('nan')):8.3f}  "
              f"h_eff={r.get('h_effective_W_m2K', float('nan')):10.1f}  "
              f"dp={r.get('dp_MPa', float('nan')):6.3f} MPa  "
              f"pump={r.get('P_pump_hydraulic_W', float('nan')):6.2f} W  "
              f"L_ent/L={r['entry_fraction']:.2f}  {r['status'][:30]}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    k = sorted({x for r in rows for x in r})
    with open(OUT / "cooling_regime_table.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=k); w.writeheader(); w.writerows(rows)
    print(f"wrote {OUT/'cooling_regime_table.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
