"""Cold-plate specification, hydraulics and cooling overhead (TCPMT review MC10/MC16).

Everything the production cooling model uses, from the same objects the solver uses
(phase0mr/cooling_production.CANDIDATES[E.COOLER] and phase0m/cooling.Microchannel), plus
what the review asked for and the model did not report:

  * regime and entrance checks: Re, Pr, hydrodynamic and thermal entrance lengths
    (L_h = 0.05 Re D_h, L_th = 0.05 Re Pr D_h), Graetz number; the fully developed Nu is
    conservative where the flow is still developing (consistent with the Icepak check)
  * pressure drop: fully developed (f Re of Shah & London) and with the developing-flow
    increment K(inf) and plenum contraction/expansion losses (declared coefficients)
  * pumping power: hydraulic, and shaft power over the declared efficiency band
  * the caloric convention: h_uniform includes R_cal = 1/(2 m_dot c_p); the coefficient
    consistent with a streamwise sink is 1/((R_conv + R_base) A)
  * thermal interface: 50 um at k = 3 W/mK, its conductance
  * per cooling tier: plates, mass flow, heat to each plate (from the case files), coolant
    rise, and the cooling overhead that enters the platform-inclusive loss

    python tcpmt_cooling_spec.py   -> research/tcpmt_revision/cooling_spec.json
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
for d in ("scripts", "scripts/phase0mr", "scripts/phase0m", "scripts/phase0b"):
    sys.path.insert(0, str(R / d))
from cooling_production import CANDIDATES, ETA_PUMP_BAND                  # noqa: E402
from cooling import RHO_F, CP_F, K_F, MU_F                                # noqa: E402

COOLER = "TOP_SI_MICROCHANNEL_27"
OUT = R / "research" / "tcpmt_revision" / "cooling_spec.json"
SENS = R / "research" / "final_closure" / "sensitivity"
FC = R / "research" / "final_closure"
#: developing-flow incremental pressure-drop number for a rectangular duct of aspect ratio
#: 1/6 (Shah & London 1978, interpolated between 0.125 and 0.25), and plenum losses:
#: sudden contraction into and expansion out of the channel array (declared, typical)
K_INF, K_CONTRACTION, K_EXPANSION = 0.85, 0.5, 1.0
TIM_UM, TIM_K = 50.0, 3.0
TIER_CASES = {
    "A": {"Z1": FC / "etm_Z1_HV_S0_h1.1_r21.json", "Z2": FC / "etm_Z2_HV_S0_h1.1_r21.json",
          "Z3": SENS / "etm_Z3_HV_S0__z3_top_only.json"},
    "B": {"Z1": SENS / "etm_Z1_HV_S0__z1_bottom_plate_tim.json",
          "Z2": SENS / "etm_Z2_HV_S0__z2_cooled_tim.json",
          "Z3": SENS / "etm_Z3_HV_S0__z3_plate_tim.json"},
}


def plate():
    c = CANDIDATES[COOLER]
    mc = c.channel()
    s = mc.solve(1000.0)
    pr = MU_F * CP_F / K_F
    re, dh = s["Re"], s["D_h_um"] * 1e-6
    L = c.length_mm * 1e-3
    u = s["velocity_m_s"]
    q_dyn = 0.5 * RHO_F * u ** 2
    dp_fd = s["dp_kPa"] * 1e3
    dp_minor = (K_INF + K_CONTRACTION + K_EXPANSION) * q_dyn
    v_dot = c.m_dot_g_s * 1e-3 / RHO_F
    a_foot = (c.width_mm * 1e-3) * L
    h_local = 1.0 / ((s["R_conv_K_W"] + s["R_base_K_W"]) * a_foot)
    return {
        "name": COOLER,
        "geometry": {"channels": s["n_channels"], "w_ch_um": c.w_ch_um, "h_ch_um": c.h_ch_um,
                     "t_fin_um": c.t_fin_um, "t_base_um": c.t_base_um,
                     "length_mm": c.length_mm, "width_mm": c.width_mm,
                     "k_solid_W_mK": c.k_solid, "aspect_ratio": s["aspect_ratio"],
                     "D_h_um": s["D_h_um"]},
        "fluid": {"medium": "water (properties at ~50 C)", "rho_kg_m3": RHO_F,
                  "cp_J_kgK": CP_F, "k_W_mK": K_F, "mu_Pa_s": MU_F, "Pr": pr,
                  "T_inlet_C": c.t_in_c, "m_dot_g_s": c.m_dot_g_s,
                  "V_dot_ml_min": v_dot * 1e6 * 60.0,
                  "flow_distribution": "uniform over the channels (ideal plenum)"},
        "regime": {"velocity_m_s": u, "Re": re, "regime": s["regime"],
                   "L_hydrodynamic_entrance_mm": 0.05 * re * dh * 1e3,
                   "L_thermal_entrance_mm": 0.05 * re * pr * dh * 1e3,
                   "Graetz_number_at_outlet": re * pr * dh / L,
                   "note": "thermally developing over most of the channel: the fully "
                           "developed Nu is a lower bound on the mean Nu (conservative)"},
        "heat_transfer": {"Nu_fully_developed_3walls": s["Nu"],
                          "h_channel_W_m2K": s["h_channel_W_m2K"],
                          "fin_efficiency": s["fin_efficiency"],
                          "area_amplification_Lambda": s["area_amplification"],
                          "R_conv_K_W": s["R_conv_K_W"], "R_caloric_K_W": s["R_caloric_K_W"],
                          "R_base_K_W": s["R_base_K_W"], "R_total_K_W": s["R_total_K_W"],
                          "h_eff_uniform_sink_W_m2K": s["h_effective_W_m2K"],
                          "h_eff_streamwise_sink_W_m2K": h_local,
                          "caloric_double_count_K_per_kW": 1000.0 * s["R_caloric_K_W"],
                          "production_note": "production uses h_eff_uniform_sink with the "
                                             "streamwise sink (conservative by Q R_cal); "
                                             "variant plate_local_h_* quantifies it"},
        "hydraulics": {"dp_fully_developed_kPa": dp_fd / 1e3,
                       "dp_with_entrance_and_plenum_kPa": (dp_fd + dp_minor) / 1e3,
                       "K_inf": K_INF, "K_contraction": K_CONTRACTION,
                       "K_expansion": K_EXPANSION,
                       "P_hydraulic_fd_W": dp_fd * v_dot,
                       "P_hydraulic_W": (dp_fd + dp_minor) * v_dot,
                       **{f"P_shaft_eta_{e:.2f}_W": (dp_fd + dp_minor) * v_dot / e
                          for e in ETA_PUMP_BAND}},
        "tim": {"thickness_um": TIM_UM, "k_W_mK": TIM_K,
                "R_m2K_W": TIM_UM * 1e-6 / TIM_K, "h_W_m2K": TIM_K / (TIM_UM * 1e-6)},
        "dT_fluid_K_per_kW": 1000.0 / (c.m_dot_g_s * 1e-3 * CP_F),
    }


def tiers(p):
    out = {}
    hyd = p["hydraulics"]
    for t, cases in TIER_CASES.items():
        n_plates = 1 if t == "A" else 2
        out[t] = {"plates": n_plates,
                  "m_dot_per_plate_g_s": p["fluid"]["m_dot_g_s"],
                  "P_hydraulic_W": n_plates * hyd["P_hydraulic_W"],
                  "P_shaft_W": {k.split("_eta_")[1][:-2]: n_plates * v
                                for k, v in hyd.items() if k.startswith("P_shaft")},
                  "cases": {}}
        for a, f in cases.items():
            c = json.loads(Path(f).read_text())
            th = c["thermal"]
            q_bottom = th.get("q_bottom_plate_W", th.get("q_extra_W")) or 0.0
            q_top = th["q_top_W"]
            out[t]["cases"][a] = {
                "file": Path(f).name, "P_loss_W": c["P_loss_w"],
                "Q_total_W": th["Q_ledger_W"], "q_top_plate_W": q_top,
                "q_bottom_plate_W": q_bottom if n_plates == 2 else 0.0,
                "q_board_natural_W": th["q_bot_W"],
                "q_converter_underside_natural_W": (q_bottom if (n_plates == 1 and a == "Z3")
                                                    else 0.0),
                "energy_residual_rel": th["energy_residual_rel"],
                "dT_fluid_top_K": q_top / (p["fluid"]["m_dot_g_s"] * 1e-3 * CP_F),
                "dT_fluid_bottom_K": (q_bottom / (p["fluid"]["m_dot_g_s"] * 1e-3 * CP_F)
                                      if n_plates == 2 else 0.0)}
    return out


def main():
    p = plate()
    res = {"plate": p, "tiers": tiers(p),
           "rule": "cooling A: one top plate; cooling B: the top plate plus an identical "
                   "plate (same geometry and mass flow) under the cell grid through the "
                   "same 50-um TIM; pumping power counts every plate"}
    OUT.write_text(json.dumps(res, indent=1, default=float))
    h = p["hydraulics"]
    print(f"Re={p['regime']['Re']:.0f} L_th={p['regime']['L_thermal_entrance_mm']:.1f} mm "
          f"dp_fd={h['dp_fully_developed_kPa']:.0f} kPa dp={h['dp_with_entrance_and_plenum_kPa']:.0f} kPa "
          f"P_hyd={h['P_hydraulic_W']:.1f} W h_uni={p['heat_transfer']['h_eff_uniform_sink_W_m2K']:.0f} "
          f"h_loc={p['heat_transfer']['h_eff_streamwise_sink_W_m2K']:.0f}")
    for t, v in res["tiers"].items():
        for a, c in v["cases"].items():
            print(t, a, {k: round(x, 2) if isinstance(x, float) else x for k, x in c.items()})
    return res


if __name__ == "__main__":
    main()
