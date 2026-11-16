"""TCPMT revision -- the flying capacitors: rating, capacitance, physical height, ESR.

FACTS FROM THE FRAMEWORK
  topology   manuscript Fig. 2 (fig_converter.py): S1, S3 conduct in phase A, S2 in phase B;
             C1 (n1 -> Vx1) holds 32 V, C2 (Vx2 -> n2) holds 16 V.
               phase A  48 V -> S1 -> C1 -> L1          C1 charges with i_L1
                        S6 -> C2 -> S3 -> L3            C2 discharges with i_L3
               phase B  S5 -> C1 -> S2 -> C2 -> L2      C1 discharges, C2 charges, with i_L2
             so in each on-interval each capacitor carries exactly one branch current
             (I_L = 20.41/3 = 6.80 A, ramping by the 4.6 A branch ripple), twice per period;
             charge balance forces i_L1 = i_L2 = i_L3.
  synthesis  HVR_FULL_OPT_EPC_V2.filter_candidate_capacitors admits v_max > V_in/N = 16 V; it
             selected 'Murata GCM21BR71E106KA73' (0805 10 uF 25 V X7R, ESR 2.5 mOhm, ~1.25 mm):
             under-rated for C1's 32 V.
  stack      configs/phase0nx/z1_physical.yaml: flying_caps tier 100 um (BOUNDED, from the
             reference stack); the HS-to-LS connection crosses it as a 120 um build-up via
             (aspect ratio t_Cf / 120 um = 0.83 at 100 um).
  loss model only the capacitors' ESR enters (P_cap_ESR = V_out/V_in I_out,rms^2 2(1-1/N) R_C),
             soft-charged through the inductors; the capacitance sets only the ripple.

    python tcpmt_decap_flying_caps.py    writes research/tcpmt_revision/flying_caps.json
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
import tcpmt_decap_parts as PA                                      # noqa: E402

OUT = R / "research" / "tcpmt_revision" / "flying_caps.json"
V_C = {"C1": 32.0, "C2": 16.0}
RIPPLE_FRAC = (0.05, 0.10)
TIER_AREA_MM2 = 5.61                  # the cell's capacitor-tier footprint, two capacitors
SPACING_MM = 0.20                     # placement spacing around each part
ATTACH_UM = 30.0                      # solder + pad stack under a part
VIA_D_UM = 120.0                      # HS-to-LS build-up via diameter (the AR = t/120 rule)
LIBRARY_ESR_MOHM = 2.5
RATING_MIN = {"C1": 50.0, "C2": 25.0}
RATING_PREF = {"C1": 50.0, "C2": 35.0}
#: X7S/X7T temperature factor at the tier temperature where Murata has no curve: the 0402
#: X7S hot DC-bias curve (GRM155C71H104JE19, 105 C) and the X7T class limit (-33 %)
CLASS_T_FACTOR = {"X7R": (0.89, 0.85), "X7S": (0.89, 0.78), "X7T": (0.89, 0.67)}


def s0_tier_temperature():
    return CI.s0_temperatures()["caps"]


def cap_current_waveform(n=2 ** 14):
    """One period of one flying capacitor's current: +i_L over phase A, -i_L over phase B
    (C1; C2 has the opposite sign), each on-interval D_eff T with the branch ramp."""
    d = CI.design()
    T = 1.0 / d["f_sw_hz"]
    t = np.arange(n) * T / n
    ton = d["D_eff"] * T
    di = d["v_out"] * (1.0 - d["D_eff"]) * T / d["L_H"]
    ramp = lambda tt: d["I_L_a"] - di / 2 + di * tt / ton
    i = np.zeros(n)
    a = t < ton
    i[a] = ramp(t[a])
    b = (t >= T / 2) & (t < T / 2 + ton)
    i[b] = -ramp(t[b] - T / 2)
    return t, i, {"I_L_A": d["I_L_a"], "branch_ripple_pp_A": di, "t_on_ns": ton * 1e9,
                  "D_eff": d["D_eff"]}


def requirement():
    d = CI.design()
    t, i, w = cap_current_waveform()
    dt = t[1] - t[0]
    q = np.cumsum(i) * dt
    qpp = float(q.max() - q.min())
    out = {"waveform": w, "charge_per_interval_C": qpp,
           "charge_at_nominal_D_C": d["I_L_a"] * d["D"] / d["f_sw_hz"],
           "I_rms_per_cap_A": float(np.sqrt(np.mean(i ** 2))),
           "I_rms_loss_model_A": math.sqrt(2 * d["D"]) * 20.573030604962867 / 3,
           "C_required_uF": {}}
    for cap, v in V_C.items():
        out["C_required_uF"][cap] = {f"{int(fr * 100)}pct": qpp / (fr * v) * 1e6
                                     for fr in RIPPLE_FRAC}
    out["note"] = ("effective capacitance at the capacitor's DC voltage and tier temperature; "
                   "peak-to-peak ripple; D_eff (loss-lengthened on-interval) is conservative "
                   "against the nominal D = 0.0625 (charge x 0.874)")
    return out


def footprint(L, W, n):
    return n * (L + SPACING_MM) * (W + SPACING_MM)


CELL_SIDE_MM = 2.3685


def fits_cell(parts, side=CELL_SIDE_MM, gap=SPACING_MM):
    """Exact small-n check that the rectangles fit the cell square: shelf packing over every
    order and orientation (n <= 7), parts separated by `gap`."""
    import itertools
    n = len(parts)
    if n == 0:
        return True, []
    if sum(L * W for L, W in parts) > side * side:
        return False, None
    for order in itertools.permutations(range(n)):
        for flips in itertools.product((False, True), repeat=n):
            x = y = row_h = 0.0
            ok, layout = True, []
            for k, f in zip(order, flips):
                w, h = (parts[k][1], parts[k][0]) if f else parts[k]
                if w > side or h > side:
                    ok = False
                    break
                if x > 0 and x + w > side + 1e-9:
                    y += row_h + gap
                    x, row_h = 0.0, 0.0
                if y + h > side + 1e-9:
                    ok = False
                    break
                layout.append((k, round(x, 3), round(y, 3), w, h))
                x += w + gap
                row_h = max(row_h, h)
            if ok:
                return True, layout
    return False, None


def candidates(req, t_c):
    data = PA.load()
    rows = {"C1": [], "C2": []}
    for key, rec in data["parts"].items():
        roles = rec.get("roles", [])
        for cap, role in (("C1", "flying_C1_32V"), ("C2", "flying_C2_16V")):
            if role not in roles:
                continue
            v = V_C[cap]
            L, W, T, Tm = PA.dims_mm(rec)
            c25 = PA.c_at_bias(rec, v)
            tf, how = PA.temp_factor(rec, v, t_c)
            diel = rec["spec"]["dielectric"]
            if tf is None:
                tf, how = CLASS_T_FACTOR[diel][0], f"{diel} class estimate (0402 X7S curve)"
            c_eff = c25 * tf
            esr = float(PA.esr_at(rec, 805e3, bias=v))
            row = {"part": key, "url": rec["url"], "dielectric": diel,
                   "V_rated": PA.rated_v(rec), "T_max_C": PA.t_max_c(rec),
                   "C_nom_uF": PA.c_nominal_uf(rec), "C_at_bias_25C_uF": c25,
                   "temp_factor": tf, "temp_factor_source": how, "C_eff_uF": c_eff,
                   "L_mm": L, "W_mm": W, "T_nom_mm": T, "T_max_mm": Tm,
                   "ESR_805kHz_mohm": esr * 1e3,
                   "ESR_1.61MHz_mohm": float(PA.esr_at(rec, 1.61e6, bias=v)) * 1e3,
                   "rating_ok": PA.rated_v(rec) >= RATING_MIN[cap],
                   "rating_preferred": PA.rated_v(rec) >= RATING_PREF[cap],
                   "temp_ok": PA.t_max_c(rec) >= 125.0}
            for fr in RIPPLE_FRAC:
                need = req["C_required_uF"][cap][f"{int(fr * 100)}pct"]
                n = int(math.ceil(need / c_eff - 1e-9))
                a = footprint(L, W, n)
                row[f"n_for_{int(fr * 100)}pct"] = n
                row[f"area_for_{int(fr * 100)}pct_mm2"] = a
                row[f"fits_half_tier_{int(fr * 100)}pct"] = a <= TIER_AREA_MM2 / 2 + 1e-9
                row[f"ESR_parallel_{int(fr * 100)}pct_mohm"] = esr * 1e3 / n
            rows[cap].append(row)
    return rows


def thin_options(req):
    """Every catalogue part <= 150 um thick that is rated for the capacitor: Murata silicon
    capacitors (all voltage-stable) and Murata ultra-thin MLCCs."""
    data = PA.load()
    si = []
    for s in data["silicon_catalogue"]:
        t = PA._num(s["thickness"])
        if not (t <= 150.0):
            continue
        v = PA._num(s["rated_voltage"])
        c = PA._num(s["capacitance"])
        unit = s["capacitance"]
        c_uf = c * (1e-6 if "pF" in unit else 1e-3 if "nF" in unit else 1.0)
        if "x" in unit.lower():
            continue
        L, W = (float(x) for x in s["LxW_mm"].replace("mm", "").split("×"))
        si.append({"part": s["part"], "series": s["series"], "V": v, "C_uF": c_uf,
                   "LxW_mm": [L, W], "t_um": t, "density_uF_per_mm2": c_uf / (L * W)})
    out = {}
    for cap in ("C1", "C2"):
        ok = [x for x in si if x["V"] >= RATING_MIN[cap]]
        best = max(ok, key=lambda x: x["density_uF_per_mm2"]) if ok else None
        need10 = req["C_required_uF"][cap]["10pct"]
        res = {"rating_min_V": RATING_MIN[cap]}
        if best:
            a_need = need10 / best["density_uF_per_mm2"]
            res.update({"best_silicon": best, "area_for_10pct_mm2": a_need,
                        "C_in_half_tier_uF": best["density_uF_per_mm2"] * TIER_AREA_MM2 / 2,
                        "C_in_full_tier_uF": best["density_uF_per_mm2"] * TIER_AREA_MM2,
                        "meets_10pct_in_half_tier": a_need <= TIER_AREA_MM2 / 2})
        out[cap] = res
    out["ultra_thin_mlcc"] = ("Murata catalogue: <= 0.15 mm only for 2.5-4 V 0201 parts "
                              "(GRM031, 0.095 mm); 0.2 mm parts are <= 10 V; the thinnest "
                              ">= 25 V part is 0.5 mm (0603 X5R, 85 C) -- none qualifies")
    out["any_thin_option_meets_C1_at_32V"] = bool(out["C1"].get("meets_10pct_in_half_tier"))
    out["any_thin_option_meets_C2_at_16V"] = bool(out["C2"].get("meets_10pct_in_half_tier"))
    return out


def esr_loss(choice, t_conv):
    """P_cap_ESR of the converter model with the chosen parts' ESR (model form: one R_C for
    both capacitors -> their mean), and the spectrum-weighted ESR loss of the actual
    capacitor current with the datasheet R(f)."""
    import final_closure_ledger as FL
    base = FL.converter_terms(t_conv)["P_conv_cap_esr"]
    t, i, _w = cap_current_waveform()
    I = CI.harmonics(i)
    d = CI.design()
    f = np.arange(1, 257) * d["f_sw_hz"]
    data = PA.load()
    per = {}
    for cap, (key, n) in choice.items():
        rec = data["parts"][key]
        esr_f = PA.esr_at(rec, f, bias=V_C[cap]) / n
        per[cap] = {"part": key, "n": n,
                    "ESR_805kHz_mohm": float(PA.esr_at(rec, 805e3, bias=V_C[cap])) * 1e3 / n,
                    "P_spectrum_per_cell_W": float(np.sum(np.abs(I[1:257]) ** 2 / 2 * esr_f))}
    r_mean = 0.5 * (per["C1"]["ESR_805kHz_mohm"] + per["C2"]["ESR_805kHz_mohm"])
    p_model = base * r_mean / LIBRARY_ESR_MOHM
    p_spec = 49 * (per["C1"]["P_spectrum_per_cell_W"] + per["C2"]["P_spectrum_per_cell_W"])
    return {"parts": per, "P_cap_ESR_library_2p5mohm_W": base,
            "R_C_effective_mohm": r_mean, "P_cap_ESR_model_W": p_model,
            "delta_model_W": p_model - base, "P_cap_ESR_spectrum_W": p_spec,
            "delta_spectrum_W": p_spec - base,
            "note": "P_conv_cap_esr is temperature-independent in the converter model; the "
                    "ledger's S0 value at the converged temperatures is 1.4402 W"}


def tier_height(choice):
    data = PA.load()
    t_nom = max(PA.dims_mm(data["parts"][k])[2] for k, _n in choice.values())
    t_max = max(PA.dims_mm(data["parts"][k])[3] for k, _n in choice.values())
    out = {}
    for lab, t in (("nominal", t_nom), ("max_tolerance", t_max)):
        h = t * 1e3 + ATTACH_UM
        out[lab] = {"part_height_mm": t, "tier_um": h, "via_AR_at_120um": h / VIA_D_UM,
                    "post_diameter_for_AR3_um": h / 3.0, "post_diameter_for_AR5_um": h / 5.0}
    out["current_tier_um"] = 100.0
    out["current_AR"] = 100.0 / VIA_D_UM * 1.0
    out["build_up_microvia_AR_limit"] = ("~1:1 (laser-drilled, filled build-up microvias; "
                                         "typical industry practice, not sourced here)")
    out["through_mold_post_AR"] = ("plated Cu posts / through-mold or through-InFO vias: "
                                   "typically ~2-3:1, up to ~5:1 reported (typical literature "
                                   "range, not sourced here)")
    out["verdict"] = ("the HS-to-LS connection across a %.0f-%.0f um tier needs AR %.1f-%.1f at "
                      "120 um: beyond build-up vias; through-mold copper posts of ~%.0f-%.0f um "
                      "diameter (AR 3) are needed instead"
                      % (out["nominal"]["tier_um"], out["max_tolerance"]["tier_um"],
                         out["nominal"]["via_AR_at_120um"],
                         out["max_tolerance"]["via_AR_at_120um"],
                         out["nominal"]["post_diameter_for_AR3_um"],
                         out["max_tolerance"]["post_diameter_for_AR3_um"]))
    return out


def main():
    t_caps = s0_tier_temperature()
    t_conv = CI.s0_temperatures()["conv"]
    req = requirement()
    cand = candidates(req, t_caps)
    thin = thin_options(req)

    def combos(frac):
        """Every (C1 part, C2 part) pair, each at the count its ripple target needs, that is
        rated, >= 125 C, and fits the cell square together; best = thinnest, then rating
        preference, then lowest ESR."""
        out = []
        for a in cand["C1"]:
            for b in cand["C2"]:
                if not (a["rating_ok"] and b["rating_ok"] and a["temp_ok"] and b["temp_ok"]):
                    continue
                n1, n2 = a[f"n_for_{frac}pct"], b[f"n_for_{frac}pct"]
                if n1 + n2 > 7:
                    continue
                ok, lay = fits_cell([(a["L_mm"], a["W_mm"])] * n1
                                    + [(b["L_mm"], b["W_mm"])] * n2)
                if ok:
                    out.append((max(a["T_nom_mm"], b["T_nom_mm"]),
                                -(b["rating_preferred"]),
                                a[f"ESR_parallel_{frac}pct_mohm"]
                                + b[f"ESR_parallel_{frac}pct_mohm"], a, b, lay))
        # ties: one part type for both capacitors, then the lower rating (smaller BOM)
        out.sort(key=lambda z: z[:3] + (z[3]["part"] != z[4]["part"], z[3]["V_rated"]))
        return out
    rec, feasibility = {}, {}
    for frac in (5, 10):
        cc = combos(frac)
        feasibility[f"{frac}pct"] = {"n_feasible_pairs": len(cc),
                                     "pairs": [f"{z[3]['part']} x{z[3][f'n_for_{frac}pct']} + "
                                               f"{z[4]['part']} x{z[4][f'n_for_{frac}pct']}"
                                               for z in cc[:8]]}
        if not cc:
            rec[f"{frac}pct"] = {"feasible": False,
                                 "reason": "no rated (C1 >= 50 V, C2 >= 25 V), >= 125 C pair "
                                           "meets the ripple target inside the 2.37 mm cell "
                                           "square at one tier"}
            continue
        c1, c2 = cc[0][3], cc[0][4]
        choice = {"C1": (c1["part"], c1[f"n_for_{frac}pct"]),
                  "C2": (c2["part"], c2[f"n_for_{frac}pct"])}
        keys = ("part", "url", "dielectric", "V_rated", "C_at_bias_25C_uF", "temp_factor",
                "temp_factor_source", "C_eff_uF", "L_mm", "W_mm", "T_nom_mm", "T_max_mm",
                "ESR_805kHz_mohm")
        rec[f"{frac}pct"] = {"feasible": True,
                             "C1": {k: c1[k] for k in keys} | {"n": choice["C1"][1]},
                             "C2": {k: c2[k] for k in keys} | {"n": choice["C2"][1]},
                             "ripple_pct": {
                                 "C1": 100 * req["charge_per_interval_C"] / (
                                     choice["C1"][1] * c1["C_eff_uF"] * 1e-6) / V_C["C1"],
                                 "C2": 100 * req["charge_per_interval_C"] / (
                                     choice["C2"][1] * c2["C_eff_uF"] * 1e-6) / V_C["C2"]},
                             "ripple_pct_at_class_limit_temp_factor": {
                                 cap: 100 * req["charge_per_interval_C"] / (
                                     choice[cap][1] * x["C_at_bias_25C_uF"] * 1e-6
                                     * CLASS_T_FACTOR[x["dielectric"]][1]) / V_C[cap]
                                 for cap, x in (("C1", c1), ("C2", c2))},
                             "cell_layout_mm": cc[0][5],
                             "tier_height": tier_height(choice),
                             "esr_loss": esr_loss(choice, t_conv)}
    # 5 % at one tier is infeasible: what two stacked capacitor tiers (C1 and C2 each on the
    # full cell footprint) would take
    two = {}
    for cap in ("C1", "C2"):
        best = None
        for a in cand[cap]:
            if not (a["rating_ok"] and a["temp_ok"]):
                continue
            n = a["n_for_5pct"]
            if n <= 7 and fits_cell([(a["L_mm"], a["W_mm"])] * n)[0]:
                key = (a["T_max_mm"], a["ESR_parallel_5pct_mohm"])
                if best is None or key < best[0]:
                    best = (key, a, n)
        if best:
            two[cap] = {"part": best[1]["part"], "n": best[2], "T_nom_mm": best[1]["T_nom_mm"],
                        "T_max_mm": best[1]["T_max_mm"]}
    if len(two) == 2:
        h_nom = sum(v["T_nom_mm"] * 1e3 + ATTACH_UM + 10.0 for v in two.values())
        h_max = sum(v["T_max_mm"] * 1e3 + ATTACH_UM + 10.0 for v in two.values())
        two["stack_um"] = [h_nom, h_max]
        two["via_AR_at_120um"] = [h_nom / VIA_D_UM, h_max / VIA_D_UM]
        two["note"] = "two capacitor tiers, each part height + 30 um attach + 10 um RDL"
    rec["5pct_two_tiers"] = two
    data = PA.load()
    syn = data["parts"].get("GRM21BC71E106KE01")
    out = {"topology_check": {
               "source": "manuscript_v2/fig_scripts/fig_converter.py (Fig. 2)",
               "phase_A": "C1 charges with i_L1 (48 V -> S1 -> C1 -> L1); C2 discharges with "
                          "i_L3 (S6 -> C2 -> S3 -> L3)",
               "phase_B": "C1 discharges and C2 charges with i_L2 (S5 -> C1 -> S2 -> C2 -> L2)",
               "per_interval_current": "one branch current, I_L = 6.80 A ramping 4.5 -> 9.1 A",
               "agrees_with_loss_model": "P_cap_ESR = 2 D (I/N)^2 R_C per capacitor: two "
                                         "on-intervals per period at the branch current"},
           "T_caps_tier_S0_C": t_caps, "requirement": req,
           "synthesis_selection": {
               "part": PA.SYNTHESIS_PART, "rating_V": 25.0, "C1_voltage_V": 32.0,
               "under_rated_for_C1": True,
               "found_in_current_murata_catalogue": data["synthesis_part"][
                   "found_in_murata_catalogue"],
               "same_class_part_used_for_data": "GRM21BC71E106KE01 (0805 10 uF 25 V X7S)",
               "same_class_C_at_16V_uF": PA.c_at_bias(syn, 16.0) if syn else None,
               "thickness_mm": 1.25, "fits_100um_tier": False,
               "library_ESR_mohm": LIBRARY_ESR_MOHM,
               "datasheet_ESR_805kHz_at_16V_mohm": float(PA.esr_at(syn, 805e3)) * 1e3
               if syn else None},
           "candidates": cand, "thin_options": thin, "feasibility": feasibility,
           "recommended": rec, "summary": {}}
    r10 = rec["10pct"]
    out["summary"] = {
        "C_required_uF": req["C_required_uF"],
        "thin_option_meets_requirement": thin["any_thin_option_meets_C1_at_32V"],
        "one_tier_5pct_feasible": rec["5pct"]["feasible"],
        "5pct_two_tiers": rec["5pct_two_tiers"],
        "recommended_10pct": f"C1 {r10['C1']['n']} x {r10['C1']['part']}, "
                             f"C2 {r10['C2']['n']} x {r10['C2']['part']}",
        "ripple_pct_10pct_choice": r10["ripple_pct"],
        "min_tier_um_10pct": [r10["tier_height"]["nominal"]["tier_um"],
                              r10["tier_height"]["max_tolerance"]["tier_um"]],
        "via_AR_10pct": [r10["tier_height"]["nominal"]["via_AR_at_120um"],
                         r10["tier_height"]["max_tolerance"]["via_AR_at_120um"]],
        "P_cap_ESR_W": {"library_2p5mohm": r10["esr_loss"]["P_cap_ESR_library_2p5mohm_W"],
                        "10pct_model": r10["esr_loss"]["P_cap_ESR_model_W"],
                        "10pct_spectrum": r10["esr_loss"]["P_cap_ESR_spectrum_W"]}}
    OUT.write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out["summary"], indent=1, default=float))
    print(json.dumps(out["recommended"], indent=1, default=float)[:6000])


if __name__ == "__main__":
    main()
