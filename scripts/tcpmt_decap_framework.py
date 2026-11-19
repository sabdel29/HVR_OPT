"""TCPMT revision -- what Z1's physically realised input decoupling does to the framework.

1. LEDGER. final_closure_ledger.self_consistent at the converged S0 temperatures (the input
   temperatures of the final S0 E-T iteration, which reproduce the recorded 144.31 W), with a
   new scenario key whose k is the package network's loss-equivalent k_eq from the 49-cell
   port model (tcpmt_decap_placement). Two terms are treated physically rather than by the
   scenario convention:
     - the cell-internal VIN -> high-side runs (P_intraVR_metal, HV nets) sit INSIDE the
       hot loop whatever is placed outside the cell, so they carry the cell's own pulse
       (k_open = 3.80), not k_eq;
     - the ring capacitors' ESR loss is package-internal and is added as its own row.
2. COUPLED RUN. The same as a variant of final_closure_sensitivity (registered from here, run
   through S.run_full at the production mesh): FL.SCEN_RATIO gets the new scenario key, the
   sensitivity driver runs that scenario, the intra-VR HV nets use k_open, and the capacitor
   ESR row enters the ledger (deposited in the high-side tier inside the cells: conservative,
   the ring is cooler).

    python tcpmt_decap_framework.py ledger     ledger consequence -> input_decoupling.json
    python tcpmt_decap_framework.py run        the coupled Z1 case (E-T + mechanics)
    python tcpmt_decap_framework.py collect    summarise the coupled case into the JSON
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import tcpmt_decap_circuit as CI                                    # noqa: E402

VARIANT = "z1_input_decoupling"
SCEN_KEY = "HV_SDEC"
SCEN_HOTLOOP = "HV_SDEC_HOTLOOP"
#: TCPMT round 3: the recommended option is the placement's (its declared rule: the
#: interleaving + ring option of least nominal k_eq on the grid of the design in force);
#: "i_latin7+c_ring" was the 49-cell (7 x 7) choice of review round 2
RECOMMENDED_49 = "i_latin7+c_ring"


def placement():
    return json.loads(CI.JSON_OUT.read_text())["placement"]


def recommended_option():
    return placement().get("recommended") or RECOMMENDED_49


class _Rec(str):
    """The recommended option name, resolved from input_decoupling.json when used."""


def __getattr__(name):                     # module attribute RECOMMENDED (PEP 562)
    if name == "RECOMMENDED":
        return recommended_option()
    raise AttributeError(name)


def recommended_k():
    pl = placement()
    RECOMMENDED = recommended_option()
    o = pl["options"][RECOMMENDED]
    return {"option": RECOMMENDED, "k_eq": o["k_eq_nominal"], "k_eq_band": o["k_eq_band"],
            "P_ring_esr_W": o[f"L{pl['loop_inductance_pH_evaluated'][1]:.0f}pH"].get(
                "P_ring_esr_W", 0.0)}


def k_open():
    _t, i = CI.phase_a_current("ramp_deff")
    return CI.k_of(CI.harmonics(i))


def _register(k_eq, k_hot, p_esr, key=SCEN_KEY):
    """Scenario `key`: package 48 V network at k_eq, intra-VR HV nets at k_hot (their own
    key), capacitor ESR as a ledger row inside the self-consistent fixed point."""
    import final_closure_ledger as FL
    FL.SCEN_RATIO[key] = float(k_eq)
    FL.SCEN_RATIO[key + "_HOTLOOP"] = float(k_hot)
    if not hasattr(FL, "_decap_esr"):
        FL._decap_esr = {}
    FL._decap_esr[key] = float(p_esr)
    if getattr(FL, "_decap_patched", False):
        return FL
    o_intra, o_ledger = FL.intra_vr, FL.ledger

    def intra_vr(t_conv_c, scen, arch="Z1"):
        return o_intra(t_conv_c, scen + "_HOTLOOP" if scen in FL._decap_esr else scen, arch)

    def ledger(arch, scen, temps, i_hv_avg_a, pad_case=FL.PAD_PRODUCTION):
        L = o_ledger(arch, scen, temps, i_hv_avg_a, pad_case)
        p_esr = FL._decap_esr.get(scen, 0.0)
        if scen in FL._decap_esr and arch == "Z1" and p_esr > 0:
            hs = FL.LAYERS["Z1"]["hs"]
            L["rows"].append({"arch": arch, "scenario": scen, "term": "P_Cin_ring_ESR",
                              "conductor": "input capacitors (ring, 1206 100 V X7S) ESR",
                              "rail": "48V", "P_w": float(p_esr), "R_ohm": None, "I_a": None,
                              "current_type": "harmonic currents of the port model",
                              "model": "datasheet R(f) at 48 V x port-model currents",
                              "deposit_layer": ",".join(hs) if isinstance(hs, list) else hs,
                              "evidence": "DATASHEET_PORT_MODEL", "maturity": "BOUNDED",
                              "note": "tcpmt_decap_placement; deposited in-cell (conservative)"})
            L["P_loss_w"] += float(p_esr)
        return L
    FL.intra_vr, FL.ledger = intra_vr, ledger
    FL._decap_patched = True
    return FL


def ledger_consequence():
    import final_closure_ledger as FL
    temps = CI.s0_temperatures()
    s0 = json.loads(CI.CASE_S0.read_text())
    L0 = FL.self_consistent("Z1", "HV_S0", temps)
    rk = recommended_k()
    kh = k_open()
    out = {"temperatures_C": temps,
           "S0_reproduced_W": L0["P_loss_w"], "S0_recorded_W": s0["P_loss_w"],
           "S0_reproduction_rel": L0["P_loss_w"] / s0["P_loss_w"] - 1.0,
           "k_open_cell": kh, "recommended": rk, "cases": {}}
    pl = placement()
    RECOMMENDED = recommended_option()
    lkey = f"L{pl['loop_inductance_pH_evaluated'][1]:.0f}pH"
    ph = pl.get("recommended_phase") or "latin7"
    spread = next((k for k in pl["options"] if k.startswith("i_spread") and
                   k.endswith("+c_ring")), None)
    names = [RECOMMENDED, "c_ring_1206_X7S", f"i_{ph}", spread, "b_gap_0402_X7R", "none_sync"]
    for j, name in enumerate(n for n in names if n and n in pl["options"]):
        o = pl["options"][name]
        k = o["k_eq_nominal"]
        p_esr = o[lkey].get("P_ring_esr_W", 0.0) + o[lkey].get("P_local_esr_W", 0.0)
        # convention check: everything at k (the scenario factor on every 48 V term)
        FL.SCEN_RATIO["HV_TMP"] = k
        Lc = FL.self_consistent("Z1", "HV_TMP", temps)
        FL.SCEN_RATIO.pop("HV_TMP")
        # physical: package network at k_eq, cell-internal VIN->HS runs at k_open (the hot
        # loop), capacitor ESR as a row -- all inside the self-consistent fixed point
        key = f"HV_DEC{j}"
        _register(k, kh, p_esr, key=key)
        Lk = FL.self_consistent("Z1", key, temps)
        rows = {r["term"]: r["P_w"] for r in Lk["rows"]}
        rows_c = {r["term"]: r["P_w"] for r in Lc["rows"]}
        pkg48 = sum(rows[t] for t in ("P_pkg_RDL_HV_supply", "P_pkg_RDL_HV_return",
                                      "P_BGA_supply", "P_BGA_return", "P_TSV_VDD",
                                      "P_TSV_GND"))
        out["cases"][name] = {
            "k_eq": k, "k_eq_band": o["k_eq_band"],
            "P_loss_all_terms_at_k_W": Lc["P_loss_w"],
            "P_package_internal_W": Lk["P_loss_w"],
            "delta_vs_S0_W": Lk["P_loss_w"] - L0["P_loss_w"],
            "P_pkg_48V_terms_W": pkg48, "P_intraVR_metal_W": rows["P_intraVR_metal"],
            "hotloop_correction_W": rows["P_intraVR_metal"] - rows_c["P_intraVR_metal"],
            "P_cap_esr_W": p_esr, "I_48_avg_A": Lk["i_hv_avg_a"]}
    # the recommended design across its loop-inductance band (k_eq and ring ESR at each end)
    o = pl["options"][RECOMMENDED]
    out["recommended_option"] = RECOMMENDED
    band = {}
    for j, lp in enumerate(pl["loop_inductance_pH_evaluated"]):
        ev = o[f"L{lp:.0f}pH"]
        key = f"HV_DECB{j}"
        _register(ev["k_eq"], kh, ev.get("P_ring_esr_W", 0.0), key=key)
        band[f"{lp:.0f}pH"] = {"k_eq": ev["k_eq"],
                               "P_package_internal_W": FL.self_consistent(
                                   "Z1", key, temps)["P_loss_w"]}
    out["recommended_band"] = band
    rows0 = {r["term"]: r["P_w"] for r in L0["rows"]}
    out["S0_pkg_48V_terms_W"] = sum(rows0[t] for t in (
        "P_pkg_RDL_HV_supply", "P_pkg_RDL_HV_return", "P_BGA_supply", "P_BGA_return",
        "P_TSV_VDD", "P_TSV_GND"))
    out["note"] = ("fixed temperatures (no thermal feedback): the coupled case below adds the "
                   "feedback. Package 48 V terms scale with k_eq^2; the TSV fields carry each "
                   "cell's own current (k_open) but are 0.4 mW at S0, so the scenario factor "
                   "is kept for them")
    return out


def backside_note(p_z1_w):
    """Direct-fed Z2/Z3: the external 48 V feed carries the cells' residual pulsed current,
    so the crossover loop resistance R* = (P_Z1 - P_int,Z2) / (k_feed^2 I^2) scales as
    1/k_feed^2. Uses the S0 crossover file's Z2 internal loss and current."""
    import final_closure_ledger as FL
    cx = json.loads((CI.CASE_S0.parent / "direct_feed_crossover.json").read_text())
    s = cx["scenarios"]["HV_S0"]
    # the same cell's VIN -> HS runs sit in the hot loop in Z2 too: same correction
    FL.SCEN_RATIO["HV_TMP_HOT"] = k_open()
    t2 = s["temps_C"]["conv"]
    hot2 = (FL.intra_vr(t2, "HV_TMP_HOT", "Z2")["P_intraVR_metal"]
            - FL.intra_vr(t2, "HV_S0", "Z2")["P_intraVR_metal"])
    FL.SCEN_RATIO.pop("HV_TMP_HOT")
    p2 = s["P_Z2_internal_recomputed_w"] + hot2
    adv = p_z1_w - p2
    out = {"P_Z1_W": p_z1_w, "P_Z2_internal_S0_W": s["P_Z2_internal_recomputed_w"],
           "Z2_hotloop_correction_W": hot2, "P_Z2_internal_with_hotloop_W": p2,
           "advantage_Z2_at_zero_feed_W": adv, "R_star_mohm": {}}
    i = s["I_48_rms_a"]
    for lab, k in (("k_feed=1", 1.0), ("k_feed=k_eq", recommended_k()["k_eq"]),
                   ("k_feed=k_open", k_open())):
        out["R_star_mohm"][lab] = max(adv, 0.0) / (k * k * i * i) * 1e3
    out["note"] = ("approximate (Z2 at its converged S0 temperatures, no thermal feedback, "
                   "linearised): the hot-loop correction is common to every integration (same "
                   "cell), so only Z1's package 48 V network and ring ESR separate them. R* > 0 "
                   "only if the decoupled Z1 loses more than Z2 internally; the direct feed "
                   "carries the cells' residual pulse, so its own k (decoupling/interleaving at "
                   "the backside) divides R* by k_feed^2")
    return out


# ------------------------------------------------------------------ the coupled variant
def apply_variant():
    """Variant hook for final_closure_sensitivity: the new scenario key, the hot-loop
    intra-VR treatment, the ESR row, and the sensitivity driver pointed at the new key."""
    import final_closure_sensitivity as S
    rk = recommended_k()
    _register(rk["k_eq"], k_open(), rk["P_ring_esr_W"])
    S.SCEN = SCEN_KEY
    S.case_file = lambda arch, variant, scen=SCEN_KEY: S.OUT / f"etm_{arch}_{scen}__{variant}.json"


def register():
    import final_closure_sensitivity as S
    rk = recommended_k()
    S.VARIANTS[VARIANT] = dict(
        kind="full", archs=("Z1",), apply=apply_variant, gates=[],
        nature="PHYSICAL_DESIGN (input decoupling made physical)",
        what=(f"Z1 with the physically realisable input decoupling ({recommended_option()}): package "
              f"48 V network at k_eq = {rk['k_eq']:.3f} ({len(CI.NW_cells()) if hasattr(CI, 'NW_cells') else CI.N_CELL}-cell port model), cell-internal "
              f"VIN->HS runs at k_open = {k_open():.3f}, ring-capacitor ESR "
              f"{rk['P_ring_esr_W']:.3f} W as a ledger row"))
    return S


def run():
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    S = register()
    S.OUT.mkdir(parents=True, exist_ok=True)
    print(S._task(("Z1", VARIANT)), flush=True)


def collect():
    import final_closure_sensitivity as S
    f = S.OUT / f"etm_Z1_{SCEN_KEY}__{VARIANT}.json"
    c = json.loads(f.read_text())
    s0 = json.loads(CI.CASE_S0.read_text())
    s1 = json.loads(CI.CASE_S0.with_name("etm_Z1_HV_S1_h1.1_r21.json").read_text())
    crit = (c.get("mechanics") or {}).get("joint_search", {}).get("critical")

    def summ(x):
        cr = x["mechanics"]["joint_search"]["critical"]
        return {"P_loss_W": x["P_loss_w"], "T_max_C": x["thermal"]["T_max_C"],
                "T_joint_C": cr["T_C"], "du_um": cr["du_um"],
                "die_warpage_um": x["mechanics"]["die_warpage_pv_um"]}
    out = {"file": str(f.relative_to(R)), "et_converged": c["et_converged"],
           "P_loss_W": c["P_loss_w"], "T_max_C": c["thermal"]["T_max_C"],
           "T_joint_C": crit["T_C"] if crit else None, "du_um": crit["du_um"] if crit else None,
           "die_warpage_um": c.get("mechanics", {}).get("die_warpage_pv_um"),
           "mechanics_error": c.get("mechanics_error"),
           "S0": summ(s0), "S1": summ(s1),
           "within_125C_calibration": (crit["T_C"] <= 125.0) if crit else None,
           "rows": {r["term"]: r["P_w"] for r in c["ledger_rows"]},
           "et_history_last": c["et_history"][-1]}
    out["backside"] = backside_note(c["P_loss_w"])
    doc = json.loads(CI.JSON_OUT.read_text())
    # the other options, ESTIMATED (not run) by this run's own thermal amplification
    # (coupled / fixed-temperature loss rise) and its joint-temperature slope
    led = doc["framework"]["ledger_at_S0_temperatures"]
    rise_fix = led["cases"][recommended_option()]["delta_vs_S0_W"]
    amp = (c["P_loss_w"] - s0["P_loss_w"]) / rise_fix
    slope = ((crit["T_C"] - out["S0"]["T_joint_C"]) / (c["P_loss_w"] - s0["P_loss_w"])
             if crit else None)
    out["other_options_estimated"] = {
        "method": "coupled loss rise = fixed-T rise x %.3f (this run); joint slope %s K/W "
                  "(this run vs S0); linear, not run" % (amp, f"{slope:.3f}" if slope else "n/a"),
        "cases": {n: {"k_eq": v["k_eq"],
                      "P_loss_W": s0["P_loss_w"] + amp * v["delta_vs_S0_W"],
                      "T_joint_C": (out["S0"]["T_joint_C"] + slope * amp * v["delta_vs_S0_W"])
                      if slope else None}
                  for n, v in led["cases"].items()}}
    doc.setdefault("framework", {})["coupled_case"] = out
    CI.JSON_OUT.write_text(json.dumps(doc, indent=1, default=float))
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1, default=float))


def _row(rows, lp, c):
    rr = [r for r in rows if r["L_loop_pH"] == lp]
    return min(rr, key=lambda r: abs(r["C_uF_per_cell"] - c) / c)


def summary():
    """Headline numbers, recommended implementation, manuscript text, specification-table row
    and caption, all formatted from the computed sections."""
    import tcpmt_decap_parts as PA
    import tcpmt_decap_placement as PL
    doc = json.loads(CI.JSON_OUT.read_text())
    doc["placement"]["connection_inductance"] = PL.connection_inductance()
    doc["placement"]["robustness_recommended"] = PL.robustness()
    ci, pl, fw = doc["circuit"], doc["placement"], doc["framework"]
    cb = ci["charge_balance"]["ramp_deff"]
    lnom = ci["loop_inductance_estimate"]["nominal_pH"]
    rows = ci["sweep"]["rows"]
    k_at = {f"{c:g}uF": {f"{lp:g}pH": _row(rows, lp, c)["k_net"] for lp in (10, 30, 100, 300,
                                                                          1000)}
            for c in (0.1, 0.3, 0.56, 1.0, 3.0, 10.0)}
    rip_at = {f"{c:g}uF": _row(rows, 100, c)["ripple_sw_pp_V"] for c in (0.1, 0.3, 0.56, 1.0,
                                                                         3.0, 10.0)}
    opt = pl["options"]
    RECOMMENDED = recommended_option()
    rec = opt[RECOMMENDED]
    n_cells = CI.N_CELL
    ph = pl.get("recommended_phase") or "latin7"
    n_ph = int("".join(ch for ch in ph.split("_")[0] if ch.isdigit()) or 7)
    lkey = f"L{pl['loop_inductance_pH_evaluated'][1]:.0f}pH"
    ring = rec["parts"]
    led = fw["ledger_at_S0_temperatures"]
    cc = fw.get("coupled_case")
    s = {
        "requirement_charge_balance_uF_per_cell": cb["C_req_uF"],
        "requirement_charge_balance_uF_total": cb["C_req_total_uF"],
        "k_open_cell_waveform": ci["waveform"]["ramp_deff"]["k_open"],
        "loop_inductance_nominal_pH": lnom,
        "loop_inductance_band_pH": ci["loop_inductance_estimate"]["plausible_band_pH"],
        "network_R_loop_hot_mohm": ci["network_resistance"]["loop_hot_ohm"] * 1e3,
        "k_vs_C_per_cell_1cell_model": k_at,
        "switching_ripple_pp_V_at_100pH": rip_at,
        "C_for_k_le_1p2_uF_per_cell": ci["C_required_uF_per_cell"]["k<=1.2"],
        "C_for_k_le_1p1_uF_per_cell": ci["C_required_uF_per_cell"]["k<=1.1"],
        "fd_td_agreement_rel": {"k": ci["verification"]["rel_diff_k"],
                                "ripple": ci["verification"]["rel_diff_ripple"],
                                "I_cap": ci["verification"]["rel_diff_Icap"]},
        "placement_k_eq": {n: {"nominal": o["k_eq_nominal"], "band": o["k_eq_band"]}
                           for n, o in opt.items()},
        "recommended": {
            "option": RECOMMENDED,
            "interleaving": (f"{n_ph} clock phases, pattern {ph} over the {pl.get('grid', '')} "
                             f"cells ({360.0 / n_ph:.1f} deg apart)"
                             + (": a Latin square, every row and column holds all "
                                f"{n_ph}" if ph.startswith("latin") else "")),
            "part": "Murata GRM31CC72A475KE11", "url": ring["url"],
            "count": ring["n_ring"], "count_per_cell": ring["n_ring"] / n_cells,
            "C_each_48V_25C_uF": ring["C_part_48V_25C_uF"],
            "C_each_48V_105C_uF": ring["C_total_uF"],
            "C_total_48V_105C_uF": ring["C_ring_total_uF"],
            "ESR_805kHz_mohm": ring["ESR_part_805kHz_mohm"], "ESL_pH": ring["ESL_part_pH"],
            "size_mm": [3.2, 1.6], "height_mm": [1.6, 1.9], "rating": "100 V, X7S, -55..125 C",
            "k_eq": rec["k_eq_nominal"], "k_eq_band": rec["k_eq_band"],
            "ring_cap_rms_A_max": rec[lkey]["I_ring_rms_A_max"],
            "ring_cap_self_heating_K": PA.self_heating_K(
                PA.load()["parts"]["GRM31CC72A475KE11"], rec[lkey]["I_ring_rms_A_max"]),
            "P_ring_esr_W": rec[lkey]["P_ring_esr_W"],
            "input_ripple_pp_V_max_cell": rec[lkey]["ripple_pp_V_max_cell"]},
        "ledger_at_S0_temperatures": led["cases"][RECOMMENDED],
        "coupled_case": cc and {k: cc[k] for k in ("P_loss_W", "T_max_C", "T_joint_C", "du_um",
                                                  "die_warpage_um", "within_125C_calibration",
                                                  "et_converged")},
    }
    s["backside_integrations"] = cc.get("backside") if cc else None
    s["other_options_coupled_estimate"] = cc.get("other_options_estimated") if cc else None
    s["robustness_recommended"] = doc["placement"]["robustness_recommended"]
    s["connection_inductance_nH"] = doc["placement"]["connection_inductance"]
    data = PA.load()
    s["parts_table_input_48V"] = [
        {k: x[k] for k in x if k not in ("roles",)} | {"url": data["parts"][x["part"]]["url"]}
        for x in PA.summary() if "input_48V" in x.get("roles", [])]
    s["silicon_100V_best"] = [p for p in data["silicon_catalogue"]
                              if p["rated_voltage"] == "100Vdc" and p["capacitance"] == "10nF"
                              and p["thickness"] == "100μm"]
    r = s["recommended"]
    lc = s["ledger_at_S0_temperatures"]
    k12 = s["C_for_k_le_1p2_uF_per_cell"]
    if cc and cc.get("T_joint_C") is not None:
        tail = (f"the coupled Z1 case at that k loses {cc['P_loss_W']:.1f} W in the package with "
                f"its critical joint at {cc['T_joint_C']:.0f} C (S0: {cc['S0']['P_loss_W']:.1f} W, "
                f"{cc['S0']['T_joint_C']:.0f} C)")
    elif cc:
        tail = (f"the coupled Z1 case at that k loses {cc['P_loss_W']:.1f} W in the package "
                f"(S0: {cc['S0']['P_loss_W']:.1f} W)")
    else:
        tail = (f"at the converged S0 temperatures the package-internal loss rises to "
                f"{lc['P_package_internal_W']:.1f} W")
    s["manuscript_text"] = (
        f"Z1 is admissible only if the 48-V current in its package network is smooth. Charge "
        f"balance asks for {cb['C_req_uF']['1V']:.2f} uF per cell for 1 V of ripple, but a "
        f"circuit model of the cells' phase-A pulse against the {s['network_R_loop_hot_mohm']:.1f}-"
        f"mOhm package network leaves k = {k_at['0.56uF']['100pH']:.1f} at that value; k <= 1.2 "
        f"needs about {k12['100']:.1f} uF per cell at 48 V, and the Z1 stack has no room for it "
        f"(the cell tiers and the 0.8-mm gaps hold only nanofarads of 100-V, 125-C capacitance, "
        f"which resonate with the package inductance and raise k). The decoupling is "
        f"therefore made physical as {n_ph} interleaved clock phases over the "
        f"{pl.get('grid', '')} cells and a "
        f"ring of {r['count']} 1206 100-V X7S capacitors ({r['C_total_48V_105C_uF']:.0f} uF at "
        f"48 V and 105 C) outside the cell grid: a {n_cells}-cell model of the package sheets gives "
        f"k = {r['k_eq']:.2f} ({r['k_eq_band'][0]:.2f}-{r['k_eq_band'][1]:.2f} over the loop-"
        f"inductance band), and {tail}.")
    s["spec_table_row"] = {
        "item": "Input decoupling (Z1)",
        "part": "Murata GRM31CC72A475KE11, 1206, 4.7 uF, 100 V, X7S (-55 to 125 C)",
        "count_per_cell": f"{r['count']} per package ({r['count_per_cell']:.2f} per cell), "
                          "none inside a cell",
        "effective_uF_at_48V": f"{r['C_each_48V_25C_uF']:.2f} uF each at 25 C, "
                               f"{r['C_each_48V_105C_uF']:.2f} at 105 C; "
                               f"{r['C_total_48V_105C_uF']:.0f} uF total "
                               f"({r['C_total_48V_105C_uF'] / n_cells:.2f} per cell)",
        "footprint": "3.2 x 1.6 mm",
        "height": "1.6 mm (1.9 mm max) < the converter layer",
        "placement": ("two rows in the ring between the cell grid (21.36 mm) and the package "
                      f"edge (30 mm); cell clocks in {n_ph} interleaved phases ({ph})")}
    s["figure_caption"] = (
        f"C_in is the package input capacitance ({r['count']} x 1206 100-V X7S, "
        f"{r['C_total_48V_105C_uF']:.0f} uF at 48 V) in the ring outside the cell grid, since a "
        f"cell has room for only nanofarads of 100-V capacitance; the phase-A input pulse (S1) "
        f"is smoothed in the package network by interleaving the cells' clocks in {n_ph} phases, "
        f"which with C_in holds k = {r['k_eq']:.2f} (bare pulse: "
        f"{s['k_open_cell_waveform']:.1f}).")
    doc["summary"] = s
    CI.JSON_OUT.write_text(json.dumps(doc, indent=1, default=float))
    print(json.dumps({k: s[k] for k in ("recommended", "ledger_at_S0_temperatures",
                                        "coupled_case", "manuscript_text", "spec_table_row",
                                        "figure_caption")}, indent=1, default=float))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "ledger"
    if cmd == "summary":
        return summary()
    if cmd == "ledger":
        out = ledger_consequence()
        doc = json.loads(CI.JSON_OUT.read_text())
        doc.setdefault("framework", {})["ledger_at_S0_temperatures"] = out
        CI.JSON_OUT.write_text(json.dumps(doc, indent=1, default=float))
        print(json.dumps(out, indent=1, default=float))
    elif cmd == "run":
        run()
    elif cmd == "collect":
        collect()
    else:
        raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    main()
