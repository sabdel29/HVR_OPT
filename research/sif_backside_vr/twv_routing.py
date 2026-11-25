"""Si-IF backside VR study -- through-wafer-via (TWV) and backside-routing loss estimate.

Rough first-order estimate for I_total at V_out delivered from backside converter cells through
the wafer to the top side. Assumptions (all arguments, baseline in brackets):

  TWV        solid Cu, diameter d_via [50 um], length = wafer thickness t_w [100-700 um],
             resistivity rho [2.2e-8 Ohm m: electroplated Cu at ~85 C; bulk Cu is 1.72e-8 at
             20 C], each via loaded to I_via [0.75 A; 0.5-1 A range]; vias for the 1-V rail AND
             its ground return (2 x I_total / I_via vias in total); barrier/liner and contact
             resistance neglected
                 R_via = rho t_w / (pi d^2 / 4),   P_TWV = 2 I_total I_via R_via
  routing    backside plated-Cu redistribution of thickness t_cu [20 um; 10-50 um], sheet
             resistance R_s = rho / t_cu; in every cell the output current enters from one side
             (the inductor terminal) and leaves through vias spread uniformly under the cell, so
             the lateral path is n_sq [1/3: uniform extraction along a square, current from one
             edge] squares per polarity, for the rail and the ground plane:
                 P_route = 2 n_sq R_s M I_cell^2 = 2 n_sq R_s I_total I_cell
  not included: top-side lateral distribution (vias assumed to land under the load's power
             bumps, i.e. the converter array lies under the load), the input-side (12/48 V)
             distribution (I_in = 21-85 A, small next to 1 kA), contact/interface resistances.
"""
from __future__ import annotations

import math

RHO_CU = 2.2e-8


def twv_loss_w(I_total=1000.0, t_w_um=300.0, d_via_um=50.0, I_via=0.75, rho=RHO_CU):
    a = math.pi * (d_via_um * 1e-6) ** 2 / 4.0
    r_via = rho * t_w_um * 1e-6 / a
    n_per_pol = math.ceil(I_total / I_via)
    p = 2.0 * n_per_pol * (I_total / n_per_pol) ** 2 * r_via
    return {"R_via_mohm": r_via * 1e3, "n_vias_total": 2 * n_per_pol, "P_TWV_W": p}


def routing_loss_w(I_total=1000.0, I_cell=25.0, t_cu_um=20.0, n_sq=1.0 / 3.0, rho=RHO_CU):
    r_s = rho / (t_cu_um * 1e-6)
    return {"R_sheet_mohm_sq": r_s * 1e3, "P_route_W": 2.0 * n_sq * r_s * I_total * I_cell}


def system_efficiency(P_out, P_conv, P_twv, P_route):
    return P_out / (P_out + P_conv + P_twv + P_route)


def table(I_total=1000.0, I_cell=25.0):
    """TWV loss over wafer thickness and via current, routing loss over Cu thickness."""
    out = {"twv": [], "routing": []}
    for t in (100.0, 300.0, 500.0, 700.0):
        for iv in (0.5, 0.75, 1.0):
            r = twv_loss_w(I_total, t, 50.0, iv)
            out["twv"].append({"t_w_um": t, "I_via_A": iv, **r})
    for tc in (10.0, 20.0, 50.0):
        for nsq in (1.0 / 6.0, 1.0 / 3.0, 2.0 / 3.0):
            out["routing"].append({"t_cu_um": tc, "n_sq": nsq,
                                   **routing_loss_w(I_total, I_cell, tc, nsq)})
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(table(), indent=1))
