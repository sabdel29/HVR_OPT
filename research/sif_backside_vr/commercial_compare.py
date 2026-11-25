#!/usr/bin/env python3
"""Si-IF backside VR study -- catalog-module reference points for the efficiency-vs-density plot.

Places the catalog alternatives on the same axes as the HVR_OPT sweep: conversion efficiency at
V_out = 1.0 V versus current density over the backside area the converter occupies (output bulk
capacitance and the controller excluded, as in the sweep). Every input is a datasheet value; the
area allowances and the 0.8 V -> 1.0 V conversion are stated assumptions.

Assumptions
  * Module area = footprint x 1.30 for point-of-load modules (tiling gaps ~15 % plus external
    input MLCCs ~15 %); bus converters and other modules x 1.15 (tiling gaps).
  * MPS MPC22165-170 (12 V -> 0.8 V, 500 kHz, datasheet Fig. "Efficiency vs. Load Current",
    read from the plot) is moved to 1.0 V out at equal power loss: the switching and conduction
    losses depend on V_in and current, not on V_out, to first order. The duty-cycle shift adds
    a little high-side conduction, so the 1.0 V values are slightly optimistic.
  * 48 V two-stage: Vicor NBM2317S60D1580T0R (K = 1/4, 1 kW, 95.6 % at full load) feeding the
    same 12 V modules; bus-converter area scales continuously with the power it passes.
  * Ferric Fe1766 two-stage: 12 V -> 1.8 V on the same modules at 105 A each, then Fe1766
    (160 A, 35.5 mm^2, 89 % at 160 A, 1.8 V -> 0.75 V) -- an estimate, no published system data.

    python commercial_compare.py   ->  commercial_compare.json
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
GAP_POL, GAP_BUS = 1.30, 1.15

# MPC22165-170 datasheet curve, V_in = 12 V, V_out = 0.8 V (load current A, efficiency %)
MPC_CURVE_08V = [(30, 91.0), (60, 90.2), (90, 87.2), (120, 84.1), (150, 80.1), (168, 76.1)]
MPC_AREA = 9.0 * 9.9                                   # mm^2, LGA-72
NBM_W_PER_UNIT, NBM_AREA, NBM_ETA = 1000.0, 22.8 * 17.3, 0.956
PRM_ETA, VTM_ETA = 0.976, 0.904                        # PRM48BF480T600A00, VTM48EF012T130C01
VTM_I, VTM_AREA, PRM_W, PRM_AREA = 130.0, 32.5 * 22.0, 600.0, 32.5 * 22.0
LTM_I, LTM_AREA, LTM_ETA = 50.0, 16.0 * 16.0, 0.88    # LTM4664, 48 V -> 1 V at 50 A
FE_I, FE_AREA, FE_ETA = 160.0, 35.5, 0.89             # Ferric Fe1766


def loss_w(i_a, eta_pct, v_out=0.8):
    return i_a * v_out * (100.0 / eta_pct - 1.0)


def mpc_points():
    pts = []
    for i, e in MPC_CURVE_08V:
        p = loss_w(i, e)
        pts.append({"I_module_A": i, "loss_W": p, "eta": i / (i + p),
                    "J": i / (MPC_AREA * GAP_POL)})
    return pts


def interp_loss(i):
    c = [(q["I_module_A"], q["loss_W"]) for q in mpc_points()]
    for (i0, p0), (i1, p1) in zip(c, c[1:]):
        if i0 <= i <= i1:
            return p0 + (p1 - p0) * (i - i0) / (i1 - i0)
    raise ValueError(i)


def two_stage_48(pts12):
    out = []
    for q in pts12:
        a2 = 1000.0 / q["J"]                            # mm^2 per kA, second stage
        p_in2 = 1000.0 / q["eta"]                       # W into the second stage per kA
        a_bus = p_in2 / NBM_W_PER_UNIT * NBM_AREA * GAP_BUS
        out.append({"I_module_A": q["I_module_A"], "J": 1000.0 / (a2 + a_bus),
                    "eta": NBM_ETA * q["eta"], "area_bus_mm2": a_bus, "area_pol_mm2": a2})
    return out


def ferric(i_first=105.0, with_bus=False):
    p1 = interp_loss(i_first)
    eta1 = 1.8 * i_first / (1.8 * i_first + p1)        # 12 V -> 1.8 V, equal-loss estimate
    p_in_fe = 1000.0 / FE_ETA
    i_bus18 = p_in_fe / 1.8
    a_first = i_bus18 / i_first * MPC_AREA * GAP_POL
    a_fe = 1000.0 / FE_I * FE_AREA * GAP_BUS
    area, eta = a_first + a_fe, FE_ETA * eta1
    if with_bus:
        area += (p_in_fe / eta1) / NBM_W_PER_UNIT * NBM_AREA * GAP_BUS
        eta *= NBM_ETA
    return {"J": 1000.0 / area, "eta": eta, "eta_first_stage": eta1,
            "area_first_mm2": a_first, "area_ferric_mm2": a_fe}


def main():
    m = mpc_points()
    vicor_area = (1000.0 / VTM_I * VTM_AREA
                  + (1000.0 / VTM_ETA) / PRM_W * PRM_AREA) * GAP_BUS
    res = {
        "assumptions": __doc__,
        "v12": {
            "modules_MPC22165": m,
            "ferric_two_stage": ferric(),
        },
        "v48": {
            "bus_plus_modules": two_stage_48(m),
            "vicor_prm_vtm": {"J": 1000.0 / vicor_area, "eta": PRM_ETA * VTM_ETA},
            "ltm4664": {"J": LTM_I / (LTM_AREA * GAP_BUS), "eta": LTM_ETA},
            "ferric_two_stage": ferric(with_bus=True),
        },
    }
    json.dump(res, open(os.path.join(HERE, "commercial_compare.json"), "w"), indent=1)
    for v, d in res.items():
        if v == "assumptions":
            continue
        for k, x in d.items():
            rows = x if isinstance(x, list) else [x]
            for r in rows:
                print(f"{v:4s} {k:18s} J={r['J']:.3f} A/mm2  eta={100 * r['eta']:.1f} %")


if __name__ == "__main__":
    main()
