"""TCPMT revision -- where Z1's input capacitance can physically go, and the k it achieves.

Placement options (configs/phase0nx/z1_physical.yaml; cell 2.3685 mm square at 3.165 mm pitch,
gaps 0.797 mm, converter layer 1973 um, substrate 30 mm, cell grid 21.36 mm):

  a1  flying-cap tier (100 um): area left beside the two flying capacitors, heights <= 100 um
      -> only silicon capacitors (Murata 100 V parts: 10 nF in 0.8 x 0.8 mm)
  a2  inductor + C_out tier (500 um): area left beside three 1.0 mm^2 inductors and the
      2.0 mm^2 C_out (routing.tile_layout footprints); parts <= ~480 um tall
  b   inter-cell gaps (0.797 mm wide, 1973 um tall): parts <= 0.6 mm wide, i.e. 0402; two
      usable levels (beside the HS tier, 685 um, and the LS tier, 638 um; the 100 um flying-cap
      and 500 um inductor tiers are too thin for a 0.55 mm-max 0402); two per shared side
      segment per level -> 8 per interior cell
  c   ring outside the grid (30 mm package, 21.36 mm grid): 1206 parts, 1.9 mm max < 1973 um,
      packed by tcpmt_decap_network.ring_layout; fed to the cells through the package sheets
  i   inter-cell interleaving of the 49 cells' switching phase (a clock assignment, no part),
      alone and with (c)

Each option is solved on the 49-cell port model (tcpmt_decap_network) at the nominal loop
inductance and across its plausible band; capacitances are the manufacturer's DC-bias value
at 48 V times the temperature factor at the converter-tier temperature.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import tcpmt_decap_circuit as CI                                    # noqa: E402
import tcpmt_decap_network as NW                                    # noqa: E402
import tcpmt_decap_parts as PA                                      # noqa: E402

T_PARTS_C = 105.0           # converter-tier temperature at S0 (T_conv 107.7 C; ring cooler)
#: X7S temperature factor at 105 C under bias where Murata has no curve for the part: the
#: 0402 X7S (GRM155C71H104JE19) hot DC-bias curve gives 0.89; the X7S class limit is 0.78
X7S_T_FACTOR = (0.89, 0.78)
GAP_MM = 3.1652 - 2.3685
CELL_MM, CELL_AREA = 2.3685, 5.61
L_CONN_NH = {"a1": 0.10, "b_level1": 0.45, "b_level2": 0.85, "c": 0.15}
ESR_SILICON_OHM = 0.10      # ASSUMPTION (no published ESR in the cached data); immaterial at 20 nF


def connection_inductance():
    """Where the L_CONN_NH values come from (all per capacitor):

      b level 1  0.7 mm of coplanar strips in the single 10-um bottom RDL (w = 0.3 mm,
                 s = 0.05 mm): L' = mu0 K(k)/K(k'), k = s/(s + 2w)  (conformal mapping),
                 plus ~0.1 nH of pads/terminations
      b level 2  level 1 + a 0.8 mm through-mold via pair (r = 60 um, 0.3 mm apart):
                 L = mu0 l/pi ln(s/r)
      c          ten 30-um TSV pairs (60 um pitch) through the 300-um substrate in parallel
                 plus ~0.13 nH of pads/terminations; the sheet path from the ring to the cells
                 is in the port model
      a1         a short via stack inside the cell (~0.1 nH)
    """
    from scipy.special import ellipk
    mu0 = 4e-7 * math.pi
    w, s = 0.3e-3, 0.05e-3
    k = s / (s + 2 * w)
    lp = mu0 * ellipk(k ** 2) / ellipk(1 - k ** 2)            # H/m (scipy uses m = k^2)
    b1 = 0.7e-3 * lp + 0.1e-9
    via = mu0 * 0.8e-3 / math.pi * math.log(0.3e-3 / 60e-6)
    tsv = mu0 * 0.3e-3 / math.pi * math.log(60e-6 / 15e-6) / 10
    out = {"cps_nH_per_mm": lp * 1e6, "b_level1_nH": b1 * 1e9,
           "b_level2_nH": (b1 + via) * 1e9, "c_nH": (tsv + 0.13e-9) * 1e9,
           "used_nH": dict(L_CONN_NH)}
    for key in ("b_level1", "b_level2", "c"):
        if abs(out[f"{key}_nH"] / L_CONN_NH[key] - 1.0) > 0.2:
            raise RuntimeError(f"L_conn {key}: derived {out[f'{key}_nH']:.3f} nH vs used "
                               f"{L_CONN_NH[key]} nH")
    return out


def part_branch_params(key, n, l_conn_nh, t_c=T_PARTS_C, bias=48.0, t_fac=None):
    """Lumped C, ESR(f), L of n parallel parts of one type (each with its own connection)."""
    data = PA.load()
    rec = data["parts"][key]
    c1 = PA.c_at_bias(rec, bias)
    if t_fac is None:
        t_fac, how = PA.temp_factor(rec, bias, t_c)
        if t_fac is None:
            t_fac, how = X7S_T_FACTOR[0], "X7S factor at 105 C from GRM155C71H104JE19"
    else:
        how = "given"
    _f0, esl, _ = PA.srf_esl(rec)
    c = n * c1 * t_fac * 1e-6
    br = NW.Branch(c, lambda f, rec=rec, n=n: PA.esr_at(rec, np.maximum(f, 1e3)) / n,
                   (esl + l_conn_nh * 1e-9) / n)
    info = {"part": key, "n": n, "C_part_48V_25C_uF": c1, "temp_factor": t_fac,
            "temp_factor_source": how, "C_total_uF": c * 1e6, "ESL_part_pH": esl * 1e12,
            "L_conn_nH": l_conn_nh, "ESR_part_805kHz_mohm": float(PA.esr_at(rec, 805e3)) * 1e3,
            "url": rec["url"]}
    return br, info


def silicon_branch(n, l_conn_nh):
    c = n * 10e-9
    return (NW.Branch(c, lambda f: np.full_like(np.asarray(f, float), ESR_SILICON_OHM / n),
                      (20e-12 + l_conn_nh * 1e-9) / n),
            {"part": "935154050510-T3T (UWSC 100 V 10 nF, 0.8 x 0.8 x 0.1 mm)", "n": n,
             "C_total_uF": c * 1e6, "ESR_assumed_ohm": ESR_SILICON_OHM,
             "url": PA.PRODUCT_URL.format(pn="935154050510-T3T"),
             "note": "Murata: 'high stability of capacitance over temperature, voltage'"})


def tier_budget():
    """Area and height left in the converter tiers of one cell."""
    import routing as RT
    d = RT.DESIGN
    a_hs, a_ls = 3 * 1.87, 3 * 1.80
    a_cf = 2 * d["cap_footprint_mm2"]
    a_ind = 3 * d["ind_footprint_mm2"]
    a_cout = d["cap_footprint_mm2"]
    return {"cell_area_mm2": CELL_AREA,
            "gan_hs_685um": {"used_mm2": a_hs, "left_mm2": CELL_AREA - a_hs},
            "flying_caps_100um": {"used_mm2": a_cf, "left_mm2": CELL_AREA - a_cf,
                                  "max_part_height_um": 100.0},
            "gan_ls_638um": {"used_mm2": a_ls, "left_mm2": CELL_AREA - a_ls},
            "inductor_cout_500um": {"used_mm2": a_ind + a_cout,
                                    "left_mm2": CELL_AREA - a_ind - a_cout,
                                    "max_part_height_um": 480.0,
                                    "note": "C_out footprint = routing.tile_layout COUT"}}


def gap_count():
    """0402 parts in the gaps: per level, two per cell side segment (2.3685 mm long: 2 x 1.0
    mm + spacing), four segments per cell each shared by two cells -> 4 per cell per level."""
    per_seg = int(math.floor((CELL_MM + 0.2) / (1.0 + 0.2)))
    return {"gap_width_mm": GAP_MM, "part_width_mm": 0.5, "side_clearance_mm":
            (GAP_MM - 0.5) / 2, "per_segment": per_seg, "per_cell_per_level": 2 * per_seg,
            "levels": 2, "per_cell": 4 * per_seg,
            "levels_note": "beside the HS tier (685 um) and the LS tier (638 um); the "
                           "flying-cap (100 um) and inductor (500 um) tiers are thinner than "
                           "a 0402's 0.55 mm maximum"}


def run():
    d = CI.design()
    f = d["f_sw_hz"]
    _t, i = CI.phase_a_current("ramp_deff")
    I = CI.harmonics(i)
    lest = CI.loop_inductance_estimate()
    l_nom = lest["nominal_pH"] * 1e-12
    l_band = [lest["plausible_band_pH"][0] * 1e-12, l_nom, 300e-12,
              lest["plausible_band_pH"][1] * 1e-12]
    nr = CI.network_resistance()
    r_scale = nr["loop_hot_ohm"] / NW.self_check()["R_loop_reduced_ohm"]
    ring_xy, ring_info = NW.ring_layout()
    gc = gap_count()
    opts = {}

    def add(name, desc, local=None, ring=None, phase="sync", info=None):
        res = {"description": desc, "parts": info or {}, "phase": phase}
        for lh in l_band:
            ev = NW.evaluate(I, f, lh, ring_branch=ring, local_branch=local, phase=phase,
                             ring_xy=ring_xy if ring is not None else [], r_scale=r_scale)
            res[f"L{lh * 1e12:.0f}pH"] = ev
        res["k_eq_nominal"] = res[f"L{l_nom * 1e12:.0f}pH"]["k_eq"]
        res["k_eq_band"] = [min(res[f"L{x * 1e12:.0f}pH"]["k_eq"] for x in l_band),
                            max(res[f"L{x * 1e12:.0f}pH"]["k_eq"] for x in l_band)]
        opts[name] = res
        print(f"{name:28s} k_eq nominal {res['k_eq_nominal']:.3f} band "
              f"{res['k_eq_band'][0]:.3f}-{res['k_eq_band'][1]:.3f}", flush=True)

    add("none_sync", "no input capacitance, cells in phase (scenario S1 physics)")
    br, inf = silicon_branch(2, L_CONN_NH["a1"])
    add("a1_cf_tier_silicon", "2 x 100 V silicon 10 nF per cell in the flying-cap tier",
        local=br, info=inf)
    n_gap = gc["per_cell"]
    br, inf = part_branch_params("GRM155R72A472KA01", n_gap,
                                 0.5 * (L_CONN_NH["b_level1"] + L_CONN_NH["b_level2"]))
    add("b_gap_0402_X7R", f"{n_gap} x 0402 100 V X7R 4.7 nF per cell in the gaps (largest "
        "0402 100 V part rated to 125 C)", local=br, info=inf)
    br, inf = part_branch_params("GRM155R62A104KE14", n_gap,
                                 0.5 * (L_CONN_NH["b_level1"] + L_CONN_NH["b_level2"]),
                                 t_fac=1.0)
    inf["qualification"] = "X5R, 85 C maximum: NOT admissible at the 105-112 C converter tier"
    add("b_gap_0402_X5R_unqualified", f"{n_gap} x 0402 100 V X5R 0.1 uF per cell (reference "
        "only: 85 C part)", local=br, info=inf)
    br_r, inf_r = part_branch_params("GRM31CC72A475KE11", 1, L_CONN_NH["c"])
    inf_r.update({"n_ring": ring_info["n_caps"], "ring": ring_info,
                  "C_ring_total_uF": ring_info["n_caps"] * inf_r["C_total_uF"]})
    add("c_ring_1206_X7S", f"{ring_info['n_caps']} x 1206 100 V X7S 4.7 uF in the ring",
        ring=br_r, info=inf_r)
    for ph in ("rows7", "latin7", "spread49"):
        add(f"i_{ph}", f"interleaved cells ({ph}), no capacitors", phase=ph)
        add(f"i_{ph}+c_ring", f"interleaved cells ({ph}) + ring capacitors", ring=br_r,
            phase=ph, info=inf_r)
    # what the S0 premise would need, locally (not placeable: reference)
    for c_need in (1.0, 2.9):
        n_eq = c_need / (PA.c_at_bias(PA.load()["parts"]["GRM31CC72A475KE11"], 48.0)
                         * X7S_T_FACTOR[0])
        br, inf = part_branch_params("GRM31CC72A475KE11", n_eq, 0.3)
        add(f"ref_local_{c_need:g}uF", f"reference: {c_need:g} uF per cell AT each cell "
            "(1206-class density; does not fit the Z1 stack)", local=br, info=inf)
    return {"tier_budget": tier_budget(), "gap_count": gc, "ring": ring_info,
            "loop_inductance_pH_evaluated": [x * 1e12 for x in l_band],
            "r_scale_hot": r_scale, "temperature_C": T_PARTS_C, "options": opts}


def main():
    out = run()
    doc = json.loads(CI.JSON_OUT.read_text()) if CI.JSON_OUT.exists() else {}
    doc["placement"] = out
    CI.JSON_OUT.write_text(json.dumps(doc, indent=1, default=float))


if __name__ == "__main__":
    main()
