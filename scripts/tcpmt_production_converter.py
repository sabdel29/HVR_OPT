"""The production converter of the package chain, as one artifact (TCPMT review round 2).

Table II of the manuscript (synthesized design point: devices, inductor, flying capacitors,
cell footprint, loss per cell) must come from the SAME converter the package chain evaluates.
This script compiles that converter exactly as the chain does (replay_production.compiled_design,
the design point of the Z1 config in force, under electrical.production_rules) and records:

  rules          the engine rule switches it was synthesized under
  design point   regulator count, topology, B array, buck duty, f_sw
  devices        part, V_DS rating / operating stress, I_D, R_DS(on) at 25 C, per-cell count
  inductor       L, DCR, I_sat, peak branch current, height, footprint
  capacitors     part, rating / C_1 stress, C_eff at the C_i stresses (vendor C(V,T), less
                 tolerance) at 25 / 105 / 125 C, ESR at f_sw, height, footprint
  cell           synthesized footprint, side, current density against the target
  loss           per cell at 25 C: total, conduction, switching, and the ledger's split
                 (scripts/phase0mr/ledger.converter_decomposition); system total
and the same record for the published (legacy) lineage, so the change is explicit.

    python tcpmt_production_converter.py   -> research/tcpmt_revision/production_converter.json
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
for _p in ("scripts/phase0mr", "scripts/phase0nw", "scripts/phase0d", "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))

OUT = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision" / "production_converter.json"   # campaign hook
T_EVAL_C = (25.0, 105.0, 125.0)


def _f(x):
    return None if x is None else float(x)


def record():
    """The converter of the design in force under the rules of this process."""
    import replay_production as RPX
    import electrical as EL
    import z1_design as Z1D
    import rms_currents as RMS
    import HVR_FULL_OPT_EPC_V2 as H
    from ledger import converter_decomposition
    d = RPX.compiled_design()
    a = d.arch
    n_vr = Z1D.design_point()["n_vr"]
    lr25 = d.loss_at(25.0, alpha_gan=EL.ALPHA_GAN_RDSON)       # the 25 C point (alpha inert)
    prev = EL.pin_loss_rules(H, d)          # the loss terms of the design's own lineage
    try:
        lr = H.compute_total_loss(a, H.LossModelInputs(
            hs_device=d.hs, ls_device=d.ls, inductor=d.inductor, capacitor=d.capacitor,
            I_out=d.i_out_a, V_out=d.v_out, V_in=d.v_in, f_sw=d.f_sw_hz))
    finally:
        EL._restore_rules(H, prev)
    dec = converter_decomposition(a, d.hs, d.ls, d.inductor, d.capacitor, d.i_out_a,
                                  d.v_out, d.v_in, d.f_sw_hz, lr)
    cur = RMS.cell_currents()
    v_mid = d.v_in / a.N
    i_ph = d.i_out_a / a.K
    di = abs(float(dec["delta_i_a"]))
    # a conventional buck branch ripples (V_mid - V_out) D T / L on both ramps (rms_currents:
    # the per-branch decomposition of the summed ripple is withdrawn)
    di_br = (v_mid - d.v_out) * float(a.D) / (float(d.f_sw_hz) * float(d.inductor.l_nh) * 1e-9)
    cap = d.capacitor
    stresses = {f"C{i}": (a.N - i) * d.v_in / a.N for i in range(1, a.N)}
    c_eff = {}
    for t in T_EVAL_C:
        c_eff[f"{t:g}C"] = {k: _f(H.cap_c_eff_uf(cap, v, t)) if hasattr(H, "cap_c_eff_uf")
                           else None for k, v in stresses.items()}
    vend = (H._vendor(cap.vendor_part) if (getattr(cap, "vendor_part", None)
                                           and hasattr(H, "_vendor")) else None)
    c_bias = ({k: float(H._interp(v, vend["c_v_25c"])) for k, v in stresses.items()}
              if vend else None)
    ripple = (H.flying_cap_ripple(a, cap, d.i_out_a, d.v_in, d.v_out, d.f_sw_hz)
              if hasattr(H, "flying_cap_ripple") else None)
    # blocking voltages under the lineage's switch rule: per switch (S1 and the low side V_in/N,
    # the stacked high-side switches max(N-1, 2) V_in/N) under "stress", V_in/N under "legacy"
    rules = {**EL.LEGACY_RULES, **(d.rules or EL.production_rules())}
    v_sw = (H.switch_stresses(a.N, d.v_in) if rules["SW_RULE"] != "legacy"
            and hasattr(H, "switch_stresses") else (v_mid, v_mid, v_mid))
    dev = {}
    for key, x, n, v_st in (("high_side", d.hs, a.N, v_sw[1]), ("low_side", d.ls, a.K, v_sw[2])):
        dev[key] = {"part": x.part_number, "V_DS_max_V": _f(x.VDSmax),
                    "V_stress_V": float(v_st), "I_D_A": _f(x.ID_A),
                    "R_DS_on_25C_ohm": _f(x.R_DS_ON),
                    "per_cell": int(n), "footprint_mm2": _f(x.footprint_mm2)}
    dev["high_side"]["V_stress_S1_V"] = float(v_sw[0])
    ind = d.inductor
    side = math.sqrt(d.area_mm2)
    return {
        "rules": rules,
        "design_point": {"n_vr": n_vr, "label": d.label, "topology": [a.N, a.K, a.K_A],
                         "B_array": list(a.B_array), "D": float(a.D),
                         "f_sw_hz": float(d.f_sw_hz), "i_out_per_cell_A": float(d.i_out_a),
                         "j_target_A_mm2": float(d.j_target), "config": Z1D.design_point()},
        "devices": dev,
        "inductor": {"name": ind.name, "per_cell": int(a.K), "L_nH": _f(ind.l_nh),
                     "DCR_mohm": _f(ind.r_dcr_mohm), "I_sat_A": _f(ind.i_sat_a),
                     "I_branch_avg_A": i_ph, "I_branch_peak_A": i_ph + di_br / 2.0,
                     "delta_I_branch_A": di_br, "delta_I_out_A": di,
                     "height_um": _f(ind.height_um),
                     "footprint_mm2": _f(ind.footprint_mm2), "coupling_k": _f(ind.coupling_k)},
        "flying_capacitors": {"part": cap.name, "vendor_part": getattr(cap, "vendor_part", None),
                              "per_cell": int(a.N - 1), "V_max_V": _f(cap.v_max),
                              "stress_V": stresses, "C_nominal_uF": _f(cap.c_uf),
                              "C_bias_25C_uF": c_bias, "C_eff_uF": c_eff,
                              "C_eff_basis": "vendor C(V, 25 C) x f_T(V, T) x (1 - tolerance)",
                              "ESR_at_fsw_mohm": _f(cap.esr_mohm),
                              "ripple_worst_at_design_T": _f(ripple),
                              "height_um": _f(getattr(cap, "height_um", None)),
                              "footprint_mm2": _f(cap.footprint_mm2),
                              "source": getattr(cap, "source", "")},
        "output_capacitance_uF_per_cell": 50.0,
        "cell": {"area_mm2": float(d.area_mm2), "side_mm": side,
                 "area_budget_mm2": float(d.area_budget_mm2),
                 "current_density_A_mm2": float(d.i_out_a / d.area_mm2)},
        "loss_25C_per_cell_W": {"total": float(lr25["p_conv_w"]),
                                "conduction": float(lr25["p_cond_w"]),
                                "switching": float(lr25["p_sw_w"]),
                                "split": {k: float(v) for k, v in dec.items()
                                          if k.startswith("P_")},
                                "optimizer_W": float(d.loss_25c_w)},
        "loss_25C_system_W": float(lr25["p_conv_w"]) * n_vr,
        "cell_output_rms_A": float(cur["i_cell_out_rms_a"]),
    }


def macros(prod, legacy):
    dev, cf, ind, cell = (prod["devices"], prod["flying_capacitors"], prod["inductor"],
                          prod["cell"])
    lo = prod["loss_25C_per_cell_W"]
    dp = prod["design_point"]
    ce = cf["C_eff_uF"]["25C"]
    m = {"ConvM": str(dp["n_vr"]), "ConvTopo": "/".join(str(x) for x in dp["topology"]),
         "ConvFswKhz": f"{dp['f_sw_hz'] / 1e3:.0f}", "ConvDuty": f"{dp['D']:.4f}",
         "ConvHsPart": dev["high_side"]["part"], "ConvLsPart": dev["low_side"]["part"],
         "ConvHsVmax": f"{dev['high_side']['V_DS_max_V']:.0f}",
         "ConvLsVmax": f"{dev['low_side']['V_DS_max_V']:.0f}",
         "ConvVstress": f"{dev['high_side']['V_stress_V']:.0f}",
         "ConvIndL": f"{ind['L_nH']:.0f}", "ConvIndDcr": f"{ind['DCR_mohm']:.1f}",
         "ConvIndIsat": f"{ind['I_sat_A']:.0f}", "ConvIndIpk": f"{ind['I_branch_peak_A']:.1f}",
         "ConvCapPart": cf["vendor_part"] or cf["part"],
         "ConvCapVmax": f"{cf['V_max_V']:.0f}",
         "ConvCapEsr": f"{cf['ESR_at_fsw_mohm']:.1f}",
         "ConvCellArea": f"{cell['area_mm2']:.2f}", "ConvCellSide": f"{cell['side_mm']:.2f}",
         "ConvCellJ": f"{cell['current_density_A_mm2']:.2f}",
         "ConvLossCell": f"{lo['total']:.2f}", "ConvCondCell": f"{lo['conduction']:.2f}",
         "ConvSwCell": f"{lo['switching']:.2f}",
         "ConvCapEsrCell": f"{lo['split']['P_cap_ESR'] * 1e3:.0f}",
         "ConvLossSys": f"{prod['loss_25C_system_W']:.1f}",
         "ConvLossSysLegacy": f"{legacy['loss_25C_system_W']:.1f}",
         "ConvLossSysDelta": f"{prod['loss_25C_system_W'] - legacy['loss_25C_system_W']:.1f}",
         "ConvCapEsrLegacy": f"{legacy['flying_capacitors']['ESR_at_fsw_mohm']:.1f}"}
    if ce.get("C1") is not None:
        m["ConvCapCeffOne"] = f"{ce['C1']:.2f}"
    if ce.get("C2") is not None:
        m["ConvCapCeffTwo"] = f"{ce['C2']:.2f}"
    cb = cf.get("C_bias_25C_uF") or {}
    if cb.get("C1") is not None:
        m["ConvCapCbiasOne"] = f"{cb['C1']:.2f}"
    if cb.get("C2") is not None:
        m["ConvCapCbiasTwo"] = f"{cb['C2']:.2f}"
    if cf.get("height_um"):
        m["ConvCapHeight"] = f"{cf['height_um'] / 1e3:.1f}"
    return m


def main():
    import electrical as EL
    import replay_production as RPX
    prod = record()
    with EL.pinned_rules(EL.LEGACY_RULES):
        RPX._DESIGN_CACHE.clear()
        legacy = record()
    RPX._DESIGN_CACHE.clear()
    out = {"what": __doc__.split("\n\n")[0], "production": prod, "legacy_lineage": legacy,
           "macros": macros(prod, legacy)}
    OUT.write_text(json.dumps(out, indent=1, default=float) + "\n")
    print(json.dumps(out["macros"], indent=1))
    return out


if __name__ == "__main__":
    main()
