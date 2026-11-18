"""Static 1-V drop per rail, MAXIMUM over the rail (TCPMT review round 2).

Table V used to report the 1-V conductor loss divided by the load current -- a mean drop over
both rails, which hides the drop that matters at the die. This module reports, per rail
(VDD supply, GND return), the MAXIMUM static drop between the converter output and the die at
the DC load current I = P_load / V_out:

  lumped conductors   every 1-V ledger row of that rail (VR attach, board vias, 1-V BGA balls,
                      TSV field, source pads): I x R_rail, R_rail the row's system resistance
                      per rail at its converged temperature (equal sharing, the ledger's own
                      assumption, so the maximum equals the mean)
  sheets              Z3's land-side redistribution and board planes: the FV static spread
                      (max - min of the rail plane potential) kappa_V I R_s at the converged
                      temperature (the case's z3_land block); the cell's own output plane (R2
                      sheet of the ledger, VDD): max - min of its FV potential per ampere, scaled
                      by the cell DC current and rho_Cu at the converter temperature
The sum over the series conductors is an upper bound of the rail's maximum drop (the maxima of
different conductors need not coincide in plane). The loop drop is VDD + GND. 48-V conductors
are not part of the 1-V drop.
"""
from __future__ import annotations

import math
from functools import lru_cache

LIMIT_MV_PER_RAIL = 30.0          # DECLARED (feasibility): 3 % of the 1-V rail, per rail
P_LOAD_W, V_OUT = 1000.0, 1.0


def _rail(term):
    t = term.upper()
    if t.endswith(("_VDD", "_SUPPLY")):
        return "VDD"
    if t.endswith(("_GND", "_RETURN")):
        return "GND"
    return None


@lru_cache(maxsize=2)
def vout_plane_drop_per_amp(level=2):
    """Max - min potential (V) of the cell's output plane per ampere of cell current at 20 C:
    the R2 sheet of final_closure_ledger.vout_plane_r2 (K inductor footprints inject, the pad
    field extracts uniformly), same grid, same sheet resistance."""
    import numpy as np
    import scipy.sparse.linalg as spla
    import final_closure_ledger as FL
    import routing as RT
    import pkg_rdl_refined as RF
    from interconnect import rho_cu
    d = FL.routing_design()
    s = d["tile_side_mm"]
    comps = {c.name: c for c in RT.tile_layout(s, d)}
    legs = [comps[f"L{k}"] for k in range(d["K"])]
    h_fine, h_coarse = RF.LEVELS[level]
    tx = sorted({round(c.x_mm + k * c.w_mm / 2, 9) for c in legs for k in (-1, 1)})
    ty = sorted({round(c.y_mm + k * c.h_mm / 2, 9) for c in legs for k in (-1, 1)})
    fx = RF.axis_faces(-s / 2, s / 2, tx, [], h_fine / 4, h_coarse / 4)
    fy = RF.axis_faces(-s / 2, s / 2, ty, [], h_fine / 4, h_coarse / 4)
    rsq = rho_cu(20.0) / (FL.INTRA_T_CU_M * FL.VOUT_PLANE_OCCUPANCY)
    sh = RF.RefinedSheet(fx, fy, rsq)
    G = sh.laplacian().tolil()
    area = np.outer(sh.dx, sh.dy).ravel()
    rhs = -area / area.sum()
    for c in legs:
        ar = np.zeros(sh.n)
        for i in range(sh.nx):
            ox = min(sh.fx[i + 1], c.x_mm + c.w_mm / 2) - max(sh.fx[i], c.x_mm - c.w_mm / 2)
            if ox <= 0:
                continue
            for j in range(sh.ny):
                oy = (min(sh.fy[j + 1], c.y_mm + c.h_mm / 2)
                      - max(sh.fy[j], c.y_mm - c.h_mm / 2))
                if oy > 0:
                    ar[sh.node(i, j)] = ox * oy
        rhs += (1.0 / len(legs)) * ar / ar.sum()
    ref = int(np.argmin(np.abs(sh.cx - 0)[:, None] + np.abs(sh.cy - s / 2)[None, :]))
    G[ref, :] = 0.0
    G[ref, ref] = 1.0
    rhs[ref] = 0.0
    V = spla.spsolve(G.tocsr(), rhs)
    return float(V.max() - V.min())


def static_drop(case, n_vr=None, with_cell_plane=True):
    """{'VDD_mV', 'GND_mV', 'max_mV', 'loop_mV', 'terms', 'mean_loss_over_I_mV', 'basis'}."""
    i_dc = P_LOAD_W / V_OUT
    rows = case.get("ledger_rows") or []
    terms = {"VDD": {}, "GND": {}}
    p_1v = 0.0
    for r in rows:
        if r.get("rail") == "1V":
            p_1v += r.get("P_w") or 0.0
        if r.get("rail") != "1V" or not r.get("R_ohm"):
            continue
        rail = _rail(r["term"])
        if rail is None:
            continue
        terms[rail][r["term"]] = 1e3 * i_dc * float(r["R_ohm"])
    zl = case.get("z3_land") or {}
    if zl:
        land = zl.get("land") or {}
        if land.get("dV_static_one_rail_mV") is not None:
            for rail in ("VDD", "GND"):
                terms[rail]["land_side_sheet"] = float(land["dV_static_one_rail_mV"])
        board = zl.get("board") or {}
        for rail in ("VDD", "GND"):
            v = board.get(f"dV_static_{rail}_mV")
            if v is not None:
                terms[rail]["board_plane_sheet"] = float(v)
    elif any(r["term"] == "P_sub_land_1V_spreading" and (r.get("P_w") or 0) > 0 for r in rows):
        raise ValueError("coupled Z3 case without its z3_land block: the sheet drops are unknown")
    if with_cell_plane:
        import final_closure_ledger as FL
        n = n_vr or FL.N_VR
        h = (case.get("et_history") or [{}])[-1]
        t_conv = h.get("T_conv_C", 85.0)
        terms["VDD"]["cell_output_plane"] = (1e3 * vout_plane_drop_per_amp() * (i_dc / n)
                                             * FL.rho_ratio_cu(t_conv))
    vdd, gnd = sum(terms["VDD"].values()), sum(terms["GND"].values())
    return {"VDD_mV": vdd, "GND_mV": gnd, "max_mV": max(vdd, gnd), "loop_mV": vdd + gnd,
            "terms": terms, "I_dc_A": i_dc,
            "mean_loss_over_I_mV": 1e3 * p_1v / i_dc,
            "limit_mV_per_rail": LIMIT_MV_PER_RAIL,
            "basis": "per-rail sum of series maxima: lumped rows I_dc R_rail (equal sharing); "
                     "Z3 land side and board planes FV max-min spread; cell output plane FV "
                     "max-min (VDD)"}
