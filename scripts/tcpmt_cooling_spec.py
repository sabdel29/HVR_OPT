"""Cold-plate specification, hydraulics and cooling overhead (TCPMT review MC10/MC16).

Everything the production cooling model uses, from the same objects the solver uses
(phase0mr/cooling_production.CANDIDATES[E.COOLER] and phase0m/cooling.Microchannel), plus
what the review asked for and the model did not report:

  * the Nusselt number: the Shah & London three-wall H1 fit with one SHORT wall adiabatic
    (the plate's adiabatic cover over a 50 x 300 um channel), Nu = 6.32 at H/w = 6; the
    superseded table (long wall adiabatic, alpha -> 0 limit 5.385) is recorded under "legacy"
  * water properties at the BULK MEAN temperature (IAPWS formulations, NIST WebBook), the
    wall-viscosity correction as a sensitivity
  * regime and entrance checks: Re, Pr, hydrodynamic and thermal entrance lengths
    (L_h = 0.05 Re D_h, L_th = 0.05 Re Pr D_h), Graetz number
  * pressure drop: fully developed (Shah & London f Re polynomial), the developing-flow
    increment K(inf) and the plenum contraction/expansion losses (declared coefficients)
  * pumping power: hydraulic, and shaft power over the declared efficiency band
  * the caloric convention: the production top plate uses the streamwise-sink coefficient
    1/((R_conv + R_base) A); h_uniform (with R_cal) belongs to a uniform sink only
  * the matched conjugate CFD (reference_cooling_icepak.json), re-compared with this model at
    the CFD's loading and properties: mean base rise and along-channel wall-minus-bulk
  * thermal interface: 50 um at k = 3 W/mK, its conductance
  * per cooling tier and case: every plate's heat, mass flow (cooling B: the bottom plate at
    the flow that gives it the top plate's coolant rise), coolant rise and pumping, read from
    the case file's thermal.cooling record when present

    python tcpmt_cooling_spec.py   -> research/tcpmt_revision/cooling_spec.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
for d in ("scripts", "scripts/phase0mr", "scripts/phase0m", "scripts/phase0b"):
    sys.path.insert(0, str(R / d))
import cooling as C                                                       # noqa: E402
from cooling_production import CANDIDATES, ETA_PUMP_BAND                  # noqa: E402
from cooling import K_INF, K_CONTRACTION, K_EXPANSION                     # noqa: E402

COOLER = "TOP_SI_MICROCHANNEL_27"
OUT = R / "research" / "tcpmt_revision" / "cooling_spec.json"
SENS = R / "research" / "final_closure" / "sensitivity"
FC = R / "research" / "final_closure"
TIM_UM, TIM_K = 50.0, 3.0
Q_REF_W = 1000.0
TIER_CASES = {
    "A": {"Z1": FC / "etm_Z1_HV_S0_h1.1_r21.json", "Z2": FC / "etm_Z2_HV_S0_h1.1_r21.json",
          "Z3": SENS / "etm_Z3_HV_S0__z3_land_t40_A_fvmap.json"},
    "B": {"Z1": SENS / "etm_Z1_HV_S0__z1_bottom_plate_tim.json",
          "Z2": SENS / "etm_Z2_HV_S0__z2_cooled_tim.json",
          "Z3": SENS / "etm_Z3_HV_S0__z3_land_t40_B_fvmap.json"},
}
NU_SOURCE = ("Shah & London (1978), Laminar Flow Forced Convection in Ducts: three-wall H1 fit, "
             "one short wall adiabatic, Nu = 8.235(1 - 1.883/b + 3.767/b^2 - 5.814/b^3 + "
             "5.361/b^4 - 2/b^5), b = H/w (as used by Qu & Mudawar, IJHMT 45 (2002) 2549)")


def _plate_record(s, c, q_w):
    a_foot = (c.width_mm * 1e-3) * (c.length_mm * 1e-3)
    p = s["props"]
    return {
        "name": COOLER,
        "geometry": {"channels": s["n_channels"], "w_ch_um": c.w_ch_um, "h_ch_um": c.h_ch_um,
                     "t_fin_um": c.t_fin_um, "t_base_um": c.t_base_um,
                     "length_mm": c.length_mm, "width_mm": c.width_mm,
                     "k_solid_W_mK": c.k_solid, "aspect_ratio": s["aspect_ratio"],
                     "D_h_um": s["D_h_um"]},
        "fluid": {"medium": f"water, properties at {s['props_basis']} "
                            f"({p['T_C']:.1f} C at {q_w:.0f} W)",
                  "rho_kg_m3": p["rho"], "cp_J_kgK": p["cp"], "k_W_mK": p["k"],
                  "mu_Pa_s": p["mu"], "Pr": s["Pr"], "T_bulk_mean_C": s["T_bulk_mean_C"],
                  "T_inlet_C": c.t_in_c, "m_dot_g_s": c.m_dot_g_s,
                  "V_dot_ml_min": s["V_dot_ml_min"], "source": C.WATER_SOURCE,
                  "flow_distribution": "uniform over the channels (ideal plenum)"},
        "regime": {"velocity_m_s": s["velocity_m_s"], "Re": s["Re"], "regime": s["regime"],
                   "L_hydrodynamic_entrance_mm": s["L_hydrodynamic_entrance_mm"],
                   "L_thermal_entrance_mm": s["L_thermal_entrance_mm"],
                   "Graetz_number_at_outlet": s["Re"] * s["Pr"] * s["D_h_um"] * 1e-6
                                              / (c.length_mm * 1e-3),
                   "note": "thermally developing over most of the channel: the fully "
                           "developed Nu is a lower bound on the local Nu near the inlet"},
        "heat_transfer": {"Nu_fully_developed_3walls": s["Nu"], "nu_model": s["nu_model"],
                          "nu_source": NU_SOURCE, "boundary_condition": "H1",
                          "h_channel_W_m2K": s["h_channel_W_m2K"],
                          "fin_efficiency": s["fin_efficiency"],
                          "area_amplification_Lambda": s["area_amplification"],
                          "R_conv_K_W": s["R_conv_K_W"], "R_caloric_K_W": s["R_caloric_K_W"],
                          "R_base_K_W": s["R_base_K_W"], "R_total_K_W": s["R_total_K_W"],
                          "h_eff_uniform_sink_W_m2K": s["h_effective_W_m2K"],
                          "h_eff_streamwise_sink_W_m2K": s["h_local_W_m2K"],
                          "caloric_double_count_K_per_kW": 1000.0 * s["R_caloric_K_W"],
                          "production_note": "production top plate: the streamwise-sink "
                                             "coefficient (no caloric double count); the "
                                             "uniform-sink form is variant "
                                             "plate_caloric_legacy"},
        "hydraulics": {"dp_fully_developed_kPa": s["dp_fd_kPa"],
                       "dp_entrance_kPa": s["dp_entrance_kPa"],
                       "dp_plenum_kPa": s["dp_plenum_kPa"],
                       "dp_with_entrance_and_plenum_kPa": s["dp_kPa"],
                       "fRe": s["fRe"], "K_inf": K_INF, "K_contraction": K_CONTRACTION,
                       "K_expansion": K_EXPANSION,
                       "P_hydraulic_fd_W": s["pump_fd_W"], "P_hydraulic_W": s["pump_W"],
                       **{f"P_shaft_eta_{e:.2f}_W": s["pump_W"] / e for e in ETA_PUMP_BAND}},
        "tim": {"thickness_um": TIM_UM, "k_W_mK": TIM_K,
                "R_m2K_W": TIM_UM * 1e-6 / TIM_K, "h_W_m2K": TIM_K / (TIM_UM * 1e-6)},
        "dT_fluid_K_per_kW": 1000.0 / (c.m_dot_g_s * 1e-3 * p["cp"]),
        "A_foot_m2": a_foot,
    }


def plate():
    c = CANDIDATES[COOLER]
    s = c.channel().solve(Q_REF_W)
    rec = _plate_record(s, c, Q_REF_W)
    # sensitivities and the superseded settings, same objects
    sw = c.channel().solve(Q_REF_W, wall_viscosity=True)
    rec["wall_viscosity_sensitivity"] = {
        "T_wall_mean_C": sw["T_wall_mean_C"], "Nu": sw["Nu"], "fRe": sw["fRe"],
        "h_eff_streamwise_sink_W_m2K": sw["h_local_W_m2K"], "dp_kPa": sw["dp_kPa"],
        "P_hydraulic_W": sw["pump_W"]}
    nu0, pr0 = C.NU_MODEL, C.PROPS_MODEL
    try:
        C.NU_MODEL, C.PROPS_MODEL = "legacy_3w_table", "legacy_50C"
        sl = c.channel().solve(Q_REF_W)
    finally:
        C.NU_MODEL, C.PROPS_MODEL = nu0, pr0
    rec["legacy"] = {"Nu": sl["Nu"], "props": "water at ~50 C",
                     "Re": sl["Re"], "h_channel_W_m2K": sl["h_channel_W_m2K"],
                     "h_eff_uniform_sink_W_m2K": sl["h_effective_W_m2K"],
                     "h_eff_streamwise_sink_W_m2K": sl["h_local_W_m2K"],
                     "production_coefficient_was": "h_eff_uniform_sink (caloric double count)",
                     "dp_fd_kPa": sl["dp_fd_kPa"], "dp_kPa": sl["dp_kPa"],
                     "P_hydraulic_fd_W": sl["pump_fd_W"]}
    rec["cfd_comparison"] = C.cfd_comparison()
    return rec


def tiers(p):
    out = {}
    for t, cases in TIER_CASES.items():
        out[t] = {"plates": 1 if t == "A" else 2,
                  "rule": ("top plate only" if t == "A" else
                           "top plate at the production flow; bottom plate at the flow that "
                           "gives it the top plate's coolant rise (equal_rise)"),
                  "cases": {}}
        for a, f in cases.items():
            f = Path(f)
            if not f.is_file():
                out[t]["cases"][a] = {"file": f.name, "missing": True}
                continue
            c = json.loads(f.read_text())
            th = c["thermal"]
            q_bottom = th.get("q_bottom_plate_W", th.get("q_extra_W")) or 0.0
            q_top = th["q_top_W"]
            cool = th.get("cooling")
            rec = {"file": f.name, "P_loss_W": c["P_loss_w"],
                   "Q_total_W": th["Q_ledger_W"], "q_top_plate_W": q_top,
                   "q_bottom_plate_W": q_bottom if t == "B" else 0.0,
                   "q_board_natural_W": th["q_bot_W"],
                   "q_converter_underside_natural_W": (q_bottom if (t == "A" and a == "Z3")
                                                       else 0.0),
                   "energy_residual_rel": th["energy_residual_rel"],
                   "die_T_max_C": th.get("die_T_max_C"),
                   "die_T_mean_C": th.get("die_T_mean_C")}
            if cool:
                pl = cool["plates"]
                rec.update({"plates": pl, "case_records_plates": True,
                            "dT_fluid_top_K": pl[0]["dT_coolant_K"],
                            "dT_fluid_bottom_K": pl[1]["dT_coolant_K"] if len(pl) > 1 else 0.0,
                            "m_dot_bottom_g_s": pl[1]["m_dot_g_s"] if len(pl) > 1 else 0.0,
                            "P_pump_hydraulic_W": cool["P_pump_hydraulic_total_W"],
                            "P_shaft_W": cool["P_pump_shaft_total_W"]})
            else:                 # a case file of the superseded lineage: every plate full
                n = 1 if t == "A" else 2
                hy = p["hydraulics"]
                rec.update({"case_records_plates": False,
                            "note": "case file predates the per-plate record: every plate "
                                    "charged at the full flow",
                            "dT_fluid_top_K": q_top / (p["fluid"]["m_dot_g_s"] * 1e-3
                                                       * p["fluid"]["cp_J_kgK"]),
                            "dT_fluid_bottom_K": 0.0,
                            "P_pump_hydraulic_W": n * hy["P_hydraulic_W"],
                            "P_shaft_W": {f"{e:.2f}": n * hy["P_hydraulic_W"] / e
                                          for e in ETA_PUMP_BAND}})
            out[t]["cases"][a] = rec
    return out


def main():
    p = plate()
    res = {"plate": p, "tiers": tiers(p),
           "rule": "cooling A: one top plate; cooling B: the top plate plus an identical "
                   "plate under the cell grid through the same 50-um TIM, its mass flow "
                   "sized so its coolant rises as much as the top plate's (equal_rise); "
                   "pumping counts every plate at its own flow"}
    OUT.write_text(json.dumps(res, indent=1, default=float))
    h, ht, cc = p["hydraulics"], p["heat_transfer"], p["cfd_comparison"]
    print(f"Nu={ht['Nu_fully_developed_3walls']:.3f} Re={p['regime']['Re']:.0f} "
          f"Pr={p['fluid']['Pr']:.2f} T_b={p['fluid']['T_bulk_mean_C']:.1f} C "
          f"dp_fd={h['dp_fully_developed_kPa']:.0f} kPa dp={h['dp_with_entrance_and_plenum_kPa']:.0f} kPa "
          f"P_hyd={h['P_hydraulic_W']:.1f} W h_uni={ht['h_eff_uniform_sink_W_m2K']:.0f} "
          f"h_loc={ht['h_eff_streamwise_sink_W_m2K']:.0f}")
    print(f"CFD mean base rise {cc['dT_base_mean_cfd_K']:.2f} K vs correlation "
          f"{cc['dT_base_mean_correlation_K']:.2f} K ({100 * cc['dT_base_mean_rel_diff']:+.1f} %)")
    for t, v in res["tiers"].items():
        for a, c in v["cases"].items():
            print(t, a, {k: round(x, 2) if isinstance(x, float) else x for k, x in c.items()
                         if k != "plates"})
    return res


if __name__ == "__main__":
    main()
