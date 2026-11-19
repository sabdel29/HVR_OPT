"""TCPMT revision -- where Z1's input capacitance can physically go, and the k it achieves.

TCPMT ROUND 3: the cells, the tiers and the gaps are those of the design in force (the design
record: 36 cells of 2.817 mm on a 6 x 6 grid at 3.709 mm pitch in production, four mixed tiers
3011 um tall); the interleaving patterns are those of its n x n grid (tcpmt_decap_network.
phase_names: rows, Latin squares, two-group plans, raster, spread), and the RECOMMENDED design
is chosen by a declared rule: the implementable interleaving + ring option of least nominal k_eq
(RECOMMEND_RULE: one or two n-phase clock groups; m36: dual6, 12 phases). The option list below
describes the round-2 49-cell build; the geometry numbers now follow the record.

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
sys.path.insert(0, str(R / "scripts" / "phase0nw"))
import design_record as DR                                          # noqa: E402
#: the cell and the inter-cell gap of the design in force (uniform placement: the grid spans
#: the die minus the edge keep-out, design_record.grid_bbox_mm)
CELL_MM, CELL_AREA = DR.cell_side_mm(), DR.cell_area_mm2()
GAP_MM = (DR.grid_bbox_mm() - CELL_MM) / (DR.grid_n() - 1) - CELL_MM
#: interleaving + ring options are compared by this rule (declared before the results). The
#: candidates are the IMPLEMENTABLE clock plans of the n x n grid: those one n-phase clock
#: generates (one phase per row, or a Latin square) and those two interleaved n-phase clocks
#: generate (dual<n>: the second group offset by half a phase step, 2n phases; review round 3,
#: adopted by the authors for M = 36: i_dual6+c_ring, 12 phases). Plans of other group sizes
#: (blk9, dual9) are reported alternatives; a spread (one phase per cell, N = n^2 phases) is
#: the interleaving limit, reported but not a clock plan. On the round-2 7 x 7 grid (no dual
#: plan: 49 cells do not split into 14 equal phases) the rule returns i_latin7+c_ring (k_eq
#: 1.650; i_spread49+c_ring 1.617 is the limit), the round-2 recommendation.
RECOMMEND_RULE = ("the implementable interleaving + ring option of least nominal k_eq: clock "
                  "plans of one n-phase group (i_rows<n>+c_ring, i_latin<n>*+c_ring) or of two "
                  "interleaved n-phase groups (i_dual<n>+c_ring, 2n phases); other group sizes "
                  "(blk9, dual9) are alternatives and i_spread<n^2> is the limit, not "
                  "candidates")


def candidate(name, n):
    """True when RECOMMEND_RULE admits option `name` on the n x n grid."""
    return name.endswith("+c_ring") and (name.startswith(f"i_rows{n}+")
                                         or name.startswith(f"i_latin{n}")
                                         or name == f"i_dual{n}+c_ring")


def recommend(opts, n):
    """The option RECOMMEND_RULE selects among `opts` on the n x n grid."""
    cand = {k: v for k, v in opts.items() if candidate(k, n)}
    return min(cand, key=lambda k: (cand[k]["k_eq_nominal"], k))
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
    """Area and height left in the converter tiers of one cell (the design record's tiers:
    each part at its body footprint)."""
    d = DR.get()
    fp = {c: float(d["part_dims_mm"][c][0]) * float(d["part_dims_mm"][c][1])
          for c in DR.CLASSES}
    out = {"cell_area_mm2": CELL_AREA, "tiers": {}}
    for t in DR.tiers():
        used = sum(fp[c] * n for c, n in t["parts"].items())
        out["tiers"][t["name"]] = {"height_um": float(t["height_um"]), "used_mm2": used,
                                   "left_mm2": CELL_AREA - used,
                                   "parts": dict(t["parts"])}
    return out


def gap_count():
    """0402 parts in the gaps: per level, two per cell side segment (2 x 1.0 mm + spacing per
    cell side), four segments per cell each shared by two cells; one level per converter tier
    at least 0.55 mm (the 0402 maximum height) tall."""
    per_seg = int(math.floor((CELL_MM + 0.2) / (1.0 + 0.2)))
    levels = sum(1 for t in DR.tiers() if float(t["height_um"]) >= 550.0)
    return {"gap_width_mm": GAP_MM, "part_width_mm": 0.5, "side_clearance_mm":
            (GAP_MM - 0.5) / 2, "per_segment": per_seg, "per_cell_per_level": 2 * per_seg,
            "levels": levels, "per_cell": 2 * per_seg * levels,
            "levels_note": "one level beside each converter tier at least 0.55 mm tall"}


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
    for ph in [x for x in NW.phase_names() if x != "sync" and not x.startswith("raster")]:
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
    rec = recommend(opts, NW.grid_n())
    return {"tier_budget": tier_budget(), "gap_count": gc, "ring": ring_info,
            "loop_inductance_pH_evaluated": [x * 1e12 for x in l_band],
            "r_scale_hot": r_scale, "temperature_C": T_PARTS_C, "options": opts,
            "grid": f"{NW.grid_n()} x {NW.grid_n()}", "n_cells": len(NW.cells()),
            "recommended": rec, "recommended_phase": rec[2:-len("+c_ring")],
            "recommend_rule": RECOMMEND_RULE}


def recommended_phase():
    """The interleaving pattern of the recommended option (input_decoupling.json placement)."""
    import json as _json
    pl = _json.loads(CI.JSON_OUT.read_text())["placement"]
    return pl.get("recommended_phase") or "latin7"


def ball_currents(i_crit_a=1.5):
    """Per-ball RMS current (DC + harmonics, tcpmt_decap_network.ball_rms) on the network in
    force, for the recommended option and the limits, beside the count closure's production
    ball current (DC peak x k_eq): k_eq is loss-equivalent and, with the cells interleaved,
    mostly circulation between cells in the sheets, so k_eq x I overstates a ball's current.
    TCPMT round 3, diagnostic (the closure criterion is unchanged)."""
    ph0 = recommended_phase()
    f = CI.design()["f_sw_hz"]
    _t, i = CI.phase_a_current("ramp_deff")
    I = CI.harmonics(i)
    l_nom = CI.loop_inductance_estimate()["nominal_pH"] * 1e-12
    r_scale = CI.network_resistance()["loop_hot_ohm"] / NW.self_check()["R_loop_reduced_ohm"]
    xy, _ = NW.ring_layout()
    br, _ = part_branch_params("GRM31CC72A475KE11", 1, L_CONN_NH["c"])
    n = NW.grid_n()
    out = {"criterion_A": i_crit_a, "n_per_rail": len(NW.balls("supply")),
           "L_loop_pH": l_nom * 1e12, "options": {}}
    for name, phase, ring in ((f"i_{ph0}+c_ring", ph0, True), ("none_sync", "sync", False),
                              (f"i_spread{n * n}+c_ring", f"spread{n * n}", True)):
        ev = NW.evaluate(I, f, l_nom, ring_branch=br if ring else None, phase=phase,
                         ring_xy=xy if ring else None, r_scale=r_scale)
        b = NW.ball_rms(I, f, l_nom, ring_branch=br if ring else None, phase=phase,
                        ring_xy=xy if ring else None, r_scale=r_scale)
        dc_max = max(b[r]["I_dc_max_A"] for r in ("supply", "return"))
        out["options"][name] = {
            "k_eq": ev["k_eq"], "ball_rms": b,
            "I_ball_rms_max_A": b["I_rms_max_A"],
            "I_ball_closure_rule_A": dc_max * ev["k_eq"],
            "I_ball_dc_max_A": dc_max, "I_total_dc_A": b["I_total_dc_A"],
            "I_ball_A": max(b["I_rms_max_A"], dc_max * ev["k_eq"]),
            "passes_rms": b["I_rms_max_A"] <= i_crit_a,
            "passes_closure_rule": dc_max * ev["k_eq"] <= i_crit_a}
    out["note"] = ("I_ball_closure_rule_A = the DC peak ball current x k_eq, as the count "
                   "closure takes it; I_ball_rms_max_A = the largest ball RMS from the "
                   "harmonic port solution (level-%d reduction, hot network scale); I_ball_A = "
                   "the worse of the two (review round 3: the closure criterion); all at the "
                   "S0 case's 48-V current I_total_dc_A (they scale with it)" % NW.LEVEL)
    return out


def ball_rms_at_counts(counts, i_crit_a=1.5):
    """{n: worst-ball currents} of the RECOMMENDED plan + ring on Z1's package network with n
    balls per rail (review round 3: the per-ball check the BGA closure uses beside the DC peak
    x k_eq rule). The network's own count uses its balls; any other count the nearest-
    symmetric selection of the lattice (as `limits`). Values at the S0 case's 48-V current
    (I_total_dc_A); the caller scales to its own current."""
    ph0 = recommended_phase()
    f = CI.design()["f_sw_hz"]
    _t, i = CI.phase_a_current("ramp_deff")
    I = CI.harmonics(i)
    l_nom = CI.loop_inductance_estimate()["nominal_pH"] * 1e-12
    r_scale = CI.network_resistance()["loop_hot_ohm"] / NW.self_check()["R_loop_reduced_ohm"]
    xy, _ = NW.ring_layout()
    br, _ = part_branch_params("GRM31CC72A475KE11", 1, L_CONN_NH["c"])
    pn = json.loads(NW.NETWORK.read_text())
    out = {}
    try:
        for cnt in counts:
            if int(cnt) == int(pn["matched_count"]):
                NW.BALLS_OVERRIDE = None
            else:
                import physical_coords as PCO
                import pkg_rdl_network as K
                cand = PCO.bga_lattice_sites(K.architecture_cutout_mm("Z1"))
                s = PCO.select_power_sites(cand, PCO.physical_cell_coordinates(), int(cnt),
                                           int(cnt), "nearest_symmetric")
                NW.BALLS_OVERRIDE = (s["supply"], s["return"])
            ev = NW.evaluate(I, f, l_nom, ring_branch=br, phase=ph0, ring_xy=xy,
                             r_scale=r_scale)
            b = NW.ball_rms(I, f, l_nom, ring_branch=br, phase=ph0, ring_xy=xy,
                            r_scale=r_scale)
            dc_max = max(b[r]["I_dc_max_A"] for r in ("supply", "return"))
            out[int(cnt)] = {"option": f"i_{ph0}+c_ring", "k_eq": ev["k_eq"],
                             "I_ball_rms_max_A": b["I_rms_max_A"], "I_ball_dc_max_A": dc_max,
                             "I_ball_closure_rule_A": dc_max * ev["k_eq"],
                             "I_total_dc_A": b["I_total_dc_A"],
                             "passes_rms": b["I_rms_max_A"] <= i_crit_a,
                             "balls": "network" if NW.BALLS_OVERRIDE is None else
                                      "nearest_symmetric selection"}
    finally:
        NW.BALLS_OVERRIDE = None
    return out


def robustness(seed=1, trials=4):
    """The recommended option (its clock plan + ring) against (i) the X7S temperature
    factor at its class limit and (ii) random per-cell phase errors."""
    ph0 = recommended_phase()
    d = CI.design()
    f = d["f_sw_hz"]
    _t, i = CI.phase_a_current("ramp_deff")
    I = CI.harmonics(i)
    l_nom = CI.loop_inductance_estimate()["nominal_pH"] * 1e-12
    r_scale = CI.network_resistance()["loop_hot_ohm"] / NW.self_check()["R_loop_reduced_ohm"]
    xy, _ = NW.ring_layout()
    out = {"temperature_factor": {}, "phase_error": {}}
    for tf in X7S_T_FACTOR:
        br, inf = part_branch_params("GRM31CC72A475KE11", 1, L_CONN_NH["c"], t_fac=tf)
        ev = NW.evaluate(I, f, l_nom, ring_branch=br, phase=ph0, ring_xy=xy,
                         r_scale=r_scale)
        out["temperature_factor"][f"{tf:g}"] = {"C_ring_uF": len(xy) * inf["C_total_uF"],
                                                "k_eq": ev["k_eq"]}
    br, _ = part_branch_params("GRM31CC72A475KE11", 1, L_CONN_NH["c"])
    base = NW.phases(ph0)
    rng = np.random.default_rng(seed)
    orig = NW.phases
    try:
        for sig in (2.0, 5.0, 10.0):
            ks = []
            for _k in range(trials):
                pert = base + np.deg2rad(sig) * rng.standard_normal(len(base))
                NW.phases = lambda name, p=pert: p
                ks.append(NW.evaluate(I, f, l_nom, ring_branch=br, phase="perturbed",
                                      ring_xy=xy, r_scale=r_scale)["k_eq"])
            out["phase_error"][f"{sig:g}deg"] = {"timing_ns": sig / 360.0 / f * 1e9,
                                                 "k_eq_mean": float(np.mean(ks)),
                                                 "k_eq_range": [min(ks), max(ks)]}
    finally:
        NW.phases = orig
    # optional HF capacitance AT each cell (closes the switching loop locally): with the
    # cells interleaved it no longer resonates the package network up
    out["optional_local_hf"] = {}
    for lab, (loc, inf) in (("silicon_2x10nF_cf_tier", silicon_branch(2, L_CONN_NH["a1"])),
                            ("0402_X7R_8x4n7_gaps", part_branch_params(
                                "GRM155R72A472KA01", 8,
                                0.5 * (L_CONN_NH["b_level1"] + L_CONN_NH["b_level2"])))):
        ev = NW.evaluate(I, f, l_nom, ring_branch=br, local_branch=loc, phase=ph0,
                         ring_xy=xy, r_scale=r_scale)
        out["optional_local_hf"][lab] = {"part": inf["part"], "C_per_cell_uF": inf["C_total_uF"],
                                         "k_eq": ev["k_eq"], "P_local_esr_W": ev["P_local_esr_W"],
                                         "I_local_rms_A_max": ev["I_local_rms_A_max"]}
    # time-domain check of the port-model result (trapezoidal MNA, constant ESR, exact phase
    # shifts) against the frequency-domain port model at the same ESR and full harmonics
    _t7, i7 = CI.phase_a_current("ramp_deff", n=NW.phase_denominator(ph0) * 512)
    I7 = CI.harmonics(i7)
    rec_r = PA.load()["parts"]["GRM31CC72A475KE11"]
    esr_c = float(PA.esr_at(rec_r, 2 * f))
    brc = NW.Branch(br.c, lambda x: np.full_like(np.asarray(x, float), esr_c), br.l)
    k_fd = NW.evaluate(I7, f, l_nom, ring_branch=brc, phase=ph0, ring_xy=xy,
                       r_scale=r_scale, n_harm=len(I7) - 1)["k_eq"]
    td = NW.td_verify(i7, f, l_nom, br.c, esr_c, br.l, phase=ph0, periods=20,
                      r_scale=r_scale, ring_xy=xy)
    out["time_domain_port_model"] = {"ESR_const_mohm": esr_c * 1e3, "k_eq_frequency_domain": k_fd,
                                 "k_eq_time_domain": td["k_eq_td"],
                                 "rel_diff": td["k_eq_td"] / k_fd - 1.0, "dt_ns": td["dt_ns"],
                                 "periods": td["periods"]}
    # grid resolution of the port model: level 2 (h_fine 10 um) against the production level 1
    import json as _json
    pn = _json.loads(NW.NETWORK.read_text())["loop"]["Z1"]
    gs2, _ = NW.reduce_sheet("supply", xy, level=2)
    gr2, _ = NW.reduce_sheet("return", xy, level=2)
    nc = len(NW.cells())
    r2 = NW.solve_harmonic(gs2, gr2, np.full(nc, 1.0 / nc), 0.0, 1e-10)["P_sheets_W"]
    o_pm = NW.port_matrices
    try:
        NW.port_matrices = lambda ring_xy, refresh=False: (gs2, gr2)
        k2 = NW.evaluate(I, f, l_nom, ring_branch=br, phase=ph0, ring_xy=xy,
                         r_scale=CI.network_resistance()["loop_hot_ohm"] / r2)["k_eq"]
    finally:
        NW.port_matrices = o_pm
    out["port_model_level2"] = {"R_loop_ohm": r2, "R_loop_production_ohm": pn["r_loop_ohm"],
                                "k_eq": k2}
    # the cell waveform assumption: the scenario S1 flat pulse and the ramp at the nominal D
    out["waveform"] = {}
    for mode in ("ramp_deff", "ramp_D", "rect_D"):
        _t2, i2 = CI.phase_a_current(mode)
        I2 = CI.harmonics(i2)
        out["waveform"][mode] = {"k_open": CI.k_of(I2), "k_eq": NW.evaluate(
            I2, f, l_nom, ring_branch=br, phase=ph0, ring_xy=xy, r_scale=r_scale)["k_eq"]}
    out["note"] = ("random phase errors decorrelate the cells that share a clock phase, so they "
                   "lower k_eq slightly; the ring's capacitance hardly matters once interleaved; "
                   "a few nF at each cell for the switching loop costs < 0.02 in k; a flat or "
                   "nominal-D pulse raises k_eq by 0.06-0.09")
    return out


class IdealBranch:
    """A branch of negligible impedance (1 mF, 1 fH, 1 uOhm): the bound of any capacitor at
    its sites."""
    c, l = 1e-3, 1e-15

    def y(self, f):
        return 1.0 / (1e-6 + 1j * 2 * np.pi * f * self.l + 1.0 / (1j * 2 * np.pi * f * self.c))


def optimal_plan(Ms, Md, I, n_phase, seeds=3, sweeps=60):
    """The least-loss assignment of n_phase equally used clock phases to the cells (pairwise
    swaps from random starts, the best of `seeds`): the interleaving limit of that phase
    count on this network."""
    nc = Ms.shape[1]
    amp = np.array([0.5 * abs(I[h]) ** 2 for h in range(1, len(Ms) + 1)])

    def cost(lev):
        ph = 2 * np.pi * lev / n_phase
        return sum(a * float(np.real(np.conj(v) @ M @ v)) for h, (a, M) in
                   enumerate(zip(amp, Ms), start=1) for v in (np.exp(-1j * h * ph),))
    best = None
    for sd in range(seeds):
        rng = np.random.default_rng(sd)
        lev = np.repeat(np.arange(n_phase), nc // n_phase)
        rng.shuffle(lev)
        c0, improved, it = cost(lev), True, 0
        while improved and it < sweeps:
            improved, it = False, it + 1
            for i in range(nc):
                for j in range(i + 1, nc):
                    if lev[i] != lev[j]:
                        lev[i], lev[j] = lev[j], lev[i]
                        c = cost(lev)
                        if c < c0 - 1e-12:
                            c0, improved = c, True
                        else:
                            lev[i], lev[j] = lev[j], lev[i]
        if best is None or c0 < best[0]:
            best = (c0, lev.copy())
    return best


#: BGA counts of the count-dependence diagnostic (nearest-symmetric allocation)
LIMIT_COUNTS = (54, 68, 128, 154, 176, 220)


def limits():
    """REVIEW ROUND 3 -- what any clock plan or ring can do for Z1's package k_eq, on the
    network in force (the loss-matrix form of the port model, tcpmt_decap_network.
    loss_matrices): (1) every clock plan of the grid with the ring, and the per-ball current
    each implies at the closed BGA count (the closure rule: verified DC peak x k_eq); (2) the
    interleaving limit (optimal assignments of 6, 9, 12 and n^2 phases); (3) ring bounds (5x
    the capacitance, an ideal short at every ring site) and what would close (ideal
    capacitors at the interior street intersections, 2.9 uF at every cell); (4) k_eq against
    the BGA count, with the closure current pf(n) k_eq(n) I_avg of the level-1 screen."""
    import csv
    import time
    t0 = time.time()
    d = CI.design()
    f = d["f_sw_hz"]
    _t, i = CI.phase_a_current("ramp_deff")
    I = CI.harmonics(i)
    l_nom = CI.loop_inductance_estimate()["nominal_pH"] * 1e-12
    r_scale = CI.network_resistance()["loop_hot_ohm"] / NW.self_check()["R_loop_reduced_ohm"]
    xy, _ = NW.ring_layout()
    br, _ = part_branch_params("GRM31CC72A475KE11", 1, L_CONN_NH["c"])
    n = NW.grid_n()
    plans = [p for p in NW.phase_names() if not p.startswith("raster")]
    ph = {p: NW.phases(p) for p in plans}
    Ms, Md = NW.loss_matrices(f, l_nom, br, xy, r_scale)
    # the closure at the network's count (bga_count_production.json at this k, else the
    # network's own fallback record): per-ball current = verified peak x k / k_closed
    fc = NW.NETWORK.parent
    pn = json.loads(NW.NETWORK.read_text())
    bp = fc / "bga_count_production.json"
    clo = json.loads(bp.read_text()) if bp.is_file() else {}
    fb = clo.get("match_fallback") or pn.get("match_fallback") or {}
    k_closed = float(clo.get("k_eq") or pn["meta"].get("production_k_eq") or 1.0)
    peak = fb.get("verified_peak_A") or {}
    out = {"network_count_per_rail": pn["matched_count"], "criterion_A": 1.5,
           "k_closed": k_closed, "verified_peak_at_k_closed_A": peak, "plans": {}}
    for p in plans:
        k, pdc, pac, per = NW.k_eq_from(Ms, Md, I, ph[p])
        out["plans"][p] = {
            "n_phases": int(len(np.unique(np.round(ph[p], 9)))), "k_eq": k, "P_DC_W": pdc,
            "P_AC_W": pac, "largest_harmonics_W": [[int(h + 1), float(per[h])]
                                                   for h in np.argsort(per)[::-1][:4]],
            "I_ball_closure_rule_A": {a: v * k / k_closed for a, v in peak.items()}}
    # (2) interleaving limit
    out["interleaving_limit"] = {}
    for m in (6, 9, 12, n * n):
        if (n * n) % m:
            continue
        c, lev = optimal_plan(Ms, Md, I, m)
        pdc = out["plans"]["sync"]["P_DC_W"]
        out["interleaving_limit"][f"{m}_phases"] = {"k_eq": math.sqrt(1 + c / pdc),
                                                    "P_AC_W": c, "phase_index": lev.tolist()}
    # (3) ring bounds and what would close
    ref = [p for p in ("latin6z", f"latin{n}", "dual6", f"spread{n * n}") if p in ph]
    bounds = {"ring_C_x5": NW.Branch(5 * br.c, lambda x: br.esr_fn(x) / 5, br.l / 5),
              "ring_ideal_short": IdealBranch()}
    out["ring_bounds"] = {}
    for lab, b in bounds.items():
        M2, Md2 = NW.loss_matrices(f, l_nom, b, xy, r_scale)
        out["ring_bounds"][lab] = {p: NW.k_eq_from(M2, Md2, I, ph[p])[0] for p in ref}
    cl = np.array(NW.cells())
    mx = np.unique(np.round(cl[:, 0], 6))
    my = np.unique(np.round(cl[:, 1], 6))
    street = [(float(x), float(y)) for x in 0.5 * (mx[1:] + mx[:-1])
              for y in 0.5 * (my[1:] + my[:-1])]
    M2, Md2 = NW.loss_matrices(f, l_nom, IdealBranch(), street, r_scale)
    out["would_close"] = {"ideal_caps_at_street_intersections": {
        "sites": len(street), **{p: NW.k_eq_from(M2, Md2, I, ph[p])[0] for p in ref}}}
    rec = PA.load()["parts"]["GRM31CC72A475KE11"]
    n_loc = 2.9 / (PA.c_at_bias(rec, 48.0) * X7S_T_FACTOR[0])
    loc, _ = part_branch_params("GRM31CC72A475KE11", n_loc, 0.3)
    M2, Md2 = NW.loss_matrices(f, l_nom, br, xy, r_scale, local_branch=loc)
    out["would_close"]["local_2.9uF_per_cell_plus_ring"] = {
        p: NW.k_eq_from(M2, Md2, I, ph[p])[0] for p in ref}
    NW.port_matrices(xy)                                # the production cache in place
    # (4) k_eq against the BGA count
    import physical_coords as PCO
    import pkg_rdl_network as K
    cand = PCO.bga_lattice_sites(K.architecture_cutout_mm("Z1"))
    pf = {}
    with open(fc / "bga_count_screen.csv") as fh:
        for r in csv.DictReader(fh):
            pf[(r["arch"], int(r["n_per_rail"]))] = float(r["peak_fraction"])
    i_avg = {a: float(clo["currents_A"][a]["HV_SDEC"]) / k_closed
             for a in ("Z1", "Z2")} if clo.get("currents_A") else {}
    out["k_vs_count"] = {"allocation": "nearest_symmetric", "r_scale": r_scale,
                         "I_avg_A": i_avg, "counts": {}}
    try:
        for cnt in LIMIT_COUNTS:
            s = PCO.select_power_sites(cand, PCO.physical_cell_coordinates(), cnt, cnt,
                                       "nearest_symmetric")
            NW.BALLS_OVERRIDE = (s["supply"], s["return"])
            M2, Md2 = NW.loss_matrices(f, l_nom, br, xy, r_scale)
            row = {}
            for p in ref:
                k, pdc, pac, _per = NW.k_eq_from(M2, Md2, I, ph[p])
                row[p] = {"k_eq": k, "P_DC_W": pdc, "P_AC_W": pac,
                          "I_ball_closure_rule_A": {a: pf[(a, cnt)] * k * i_avg[a]
                                                    for a in i_avg if (a, cnt) in pf}}
            out["k_vs_count"]["counts"][str(cnt)] = row
            print(f"count {cnt}: " + ", ".join(f"{p} {v['k_eq']:.3f}" for p, v in row.items()),
                  flush=True)
    finally:
        NW.BALLS_OVERRIDE = None
    out["wall_s"] = time.time() - t0
    out["note"] = ("loss-matrix port model at the nominal loop inductance; k_vs_count keeps the "
                   "network's hot/cold scale (r_scale) at every count; the closure currents use "
                   "the level-1 screen peak fractions")
    return out


#: the limits study's own record (review round 3: written apart from input_decoupling.json,
#: which production jobs read while the study runs)
LIMITS_OUT = CI.JSON_OUT.with_name("decoupling_limits.json")


def main():
    if sys.argv[1:2] == ["limits"]:
        out = limits()
        pl = json.loads(CI.JSON_OUT.read_text()).get("placement") or {}
        LIMITS_OUT.write_text(json.dumps({
            "what": "what any clock plan or ring can do for Z1's package k_eq on the network in "
                    "force (tcpmt_decap_placement.limits)", "design": CI.design(),
            "recommended": pl.get("recommended"), "recommend_rule": pl.get("recommend_rule"),
            "placement_limits": out}, indent=1, default=float))
        print(json.dumps({k: out[k] for k in ("interleaving_limit", "ring_bounds",
                                              "would_close")}, indent=1, default=float))
        return
    out = run()
    doc = json.loads(CI.JSON_OUT.read_text()) if CI.JSON_OUT.exists() else {}
    doc["placement"] = out
    CI.JSON_OUT.write_text(json.dumps(doc, indent=1, default=float))


if __name__ == "__main__":
    main()
