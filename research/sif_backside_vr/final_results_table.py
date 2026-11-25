#!/usr/bin/env python3
"""Si-IF backside VR study -- final results table (HVR_OPT designs and off-the-shelf routes, 1 kA).

Reads results_summary.json and commercial_compare.json; writes final_results_table.csv and
final_results_table.html (a <table> fragment for the summary page).

Cost basis
  HVR_OPT rows: switches, inductors, flying and input capacitors, gate drivers and bootstrap parts
    (sif_report.bom, volume prices); the controller is not included (a hybrid converter needs a
    programmable or custom controller).
  Catalog rows: modules + multiphase controllers ($3.50-7.32 per 12 phases: Infineon XDPE192C3B,
    TI TPS536C7) + local capacitors ($5-15 per kA). Unit prices: MPC22165-170 $24.31-28.03
    (6.4k-800 pcs), NBM2317 $84.84 (100+), VTM48EF012T130C01 $102, PRM48BF480T600A00 $141 (100+),
    LTM4664A $91.58-140 (1k list - 84 pcs). Counts per kA are continuous (large array).
"""
from __future__ import annotations

import csv
import gzip
import html
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "results_summary.json")))["results"]
C = json.load(open(os.path.join(HERE, "commercial_compare.json")))
DES = {}
for v in ("48V", "12V"):
    for row in csv.DictReader(open(os.path.join(HERE, f"designs_{v}.csv"))):
        DES[(v, row["role"], row["mode"], float(row["keepout_um"]))] = row



def ceiling(v, J):
    """Best design with gate drivers (overhead mode, 100 um) at density target J, from the sweep."""
    sys.path.insert(0, HERE)
    import sif_report as SR
    tag = "v48" if v == "48V" else "v12"
    p = os.path.join(HERE, f"sweep_{tag}_best.json")
    d = json.load(open(p)) if os.path.exists(p) else json.load(gzip.open(p + ".gz"))
    recs = d["records"] if isinstance(d, dict) and "records" in d else d
    if isinstance(recs, dict):
        recs = [r for x in recs.values() for r in (x if isinstance(x, list) else [x])]
    cand = [r for r in recs if isinstance(r, dict) and r.get("mode") == "overhead"
            and float(r.get("keepout_um", 0)) == 100.0 and r.get("kind", "grid") == "grid"
            and abs(float(r["J_target"]) - J) < 2e-3]
    r = min(cand, key=lambda r: r["loss_total_W"])
    P = SR.load_prices()
    brief = SR.design_brief(r, P)
    return {"rec": brief, "bom_drv": SR.bom(r, P)["per_kA_with_drivers_usd"],
            "heat": brief["heat_flux_W_per_cm2"]}


MPC = (24.31, 28.03)
NBM, VTM, PRM, LTM = 84.84, 102.0, 141.0, (91.58, 140.0)
CTRL = (3.50, 7.32)        # per 12 phases
CAPS = (5.0, 15.0)


def mlcc(name):
    tbl = {"GRM32EC72A106KE05": "10 µF 100 V 1210", "GRM21BC71H475KE11": "4.7 µF 50 V 0805",
           "GRM188D71H105KE01": "1 µF 50 V 0603", "GRM32ER71E226KE15": "22 µF 25 V 1210",
           "GRM21BC81E226ME44": "22 µF 25 V 0805"}
    pn = name.split("-")[1] if name else ""
    return f"Murata {pn} ({tbl.get(pn, '')})" if pn else ""


def ind(name):
    tbl = {"TDK-CLT32-17N": "TDK CLT32-17N (17 nH)",
           "Bourns-TLVR1005T-R15K": "Bourns TLVR1005T-R15K (150 nH)"}
    return tbl.get(name, name)


def topo(t):
    if t == "buck":
        return "Buck"
    n, k = t[1:].split("K")[0], t.split("K")[1]
    return f"Hybrid SC-buck: {n}:1 switched-capacitor stage + {k} inductors ({t})"


def hvr_row(v, label, rec, cost, note="", drivers_on_layer=True):
    n, k = rec["N"], rec["K"]
    drv = math.ceil((n + k) / 2)
    comp = (f"per cell: {n}× {rec['hs']} (HS), {k}× {rec['ls']} (LS), {k}× {ind(rec['inductor'])}, "
            f"{n - 1}× {mlcc(rec['capacitor'])} flying, {drv}× uPI uP1966E driver"
            + ("" if drivers_on_layer else " (placed elsewhere)"))
    return {
        "conversion": f"{v[:-1]} V → 1 V",
        "approach": "HVR_OPT (proposed framework), discrete catalog parts",
        "point": label,
        "topology": topo(rec["topology"]),
        "distribution": f"Distributed: {rec['M']} cells × {rec['I_cell_A']:.0f} A ({rec['M'] * k} phases)",
        "components": comp,
        "f_sw": f"{rec['f_sw_Hz'] / 1e6:.2f} MHz",
        "J": rec["J_effective"],
        "eta": 100 * rec["efficiency"],
        "eta_hot": 100 * rec["efficiency_hot_estimate"],
        "cost": cost,
        "note": note,
    }


def money(lo, hi=None):
    if hi is None or abs(hi - lo) < 1:
        return f"${lo:,.0f}"
    return f"${lo:,.0f}–{hi:,.0f}"


rows = []
for v in ("48V", "12V"):
    bm = R[v]["by_mode"]
    o = bm["overhead_ko100"]
    d = lambda role, mode="overhead", ko=100.0: float(DES[(v, role, mode, ko)]["bom_with_drivers_usd"])
    ceil_J = 1.3 if v == "48V" else 1.2
    rows.append(hvr_row(v, "Highest efficiency (≥ 0.1 A/mm²)", o["max_efficiency_at_J_ge_0p1"],
                        money(d("max_efficiency_at_J_ge_0p1")),
                        "11.7 mm tall inductors; ≈0.3–0.4 W/cm² of heat"))
    rows.append(hvr_row(v, "1 A/mm² (1 kA per 1000 mm²)", o["at_1A_per_mm2"], money(d("at_1A_per_mm2")),
                        f"parts ≤ 3 mm tall; {o['at_1A_per_mm2']['heat_flux_W_per_cm2']:.0f} W/cm²"))
    cj = ceiling(v, ceil_J)
    rows.append(hvr_row(v, "Practical ceiling (knee of the curve)", cj["rec"], money(cj["bom_drv"]),
                        f"{cj['heat']:.0f} W/cm²; efficiency falls steeply beyond this"))
    rows.append(hvr_row(v, "Maximum density", o["max_density"], money(d("max_density")),
                        f"bound, not a design: {o['max_density']['heat_flux_W_per_cm2']:.0f} W/cm², "
                        "parts at their limits"))
    p = bm["power_ko100"]["max_density"]
    rows.append(hvr_row(v, "Maximum density, power stage only", p,
                        money(float(DES[(v, 'max_density', 'power', 100.0)]["bom_with_drivers_usd"])),
                        f"gate drivers not on the backside layer; {p['heat_flux_W_per_cm2']:.0f} W/cm²",
                        drivers_on_layer=False))

    if v == "48V":
        bpm = C["v48"]["bus_plus_modules"]
        for q, label in ((bpm[2], "Equal-efficiency point"), (bpm[5], "Modules at 168 A (near the 170 A rating)")):
            n_mod = 1000.0 / q["I_module_A"]
            n_bus = (1000.0 / (q["eta"] / 0.956)) / 1000.0
            ctrl = math.ceil(2 * n_mod / 12)
            lo = n_mod * MPC[0] + n_bus * NBM + ctrl * CTRL[0] + CAPS[0]
            hi = n_mod * MPC[1] + n_bus * NBM + ctrl * CTRL[1] + CAPS[1]
            rows.append({
                "conversion": "48 V → 1 V", "approach": "Off-the-shelf, two-stage (catalog)", "point": label,
                "topology": "48→12 V fixed-ratio bus converter (K = 1/4) + 2-phase buck modules with integrated inductors",
                "distribution": f"Distributed: ≈{n_bus:.1f} bus converters + ≈{n_mod:.1f} modules × {q['I_module_A']} A per kA",
                "components": "Vicor NBM2317S60D1580T0R; MPS MPC22165-170; multiphase controller",
                "f_sw": "0.5 MHz (modules)", "J": q["J"], "eta": 100 * q["eta"], "eta_hot": None,
                "cost": money(lo, hi), "note": "datasheet efficiencies; bus converter takes 30–45% of the area"})
        vic = C["v48"]["vicor_prm_vtm"]
        n_vtm, n_prm = 1000 / 130, (1000 / 0.904) / 600
        rows.append({
            "conversion": "48 V → 1 V", "approach": "Off-the-shelf, factorized power (catalog)", "point": "At rating",
            "topology": "ZVS buck-boost regulator (PRM) + 40:1 sine-amplitude current multiplier (VTM)",
            "distribution": f"Distributed: ≈{n_prm:.1f} PRM + ≈{n_vtm:.1f} VTM × 130 A per kA",
            "components": "Vicor PRM48BF480T600A00 + VTM48EF012T130C01",
            "f_sw": "≈1 MHz", "J": vic["J"], "eta": 100 * vic["eta"], "eta_hot": None,
            "cost": money(n_vtm * VTM + n_prm * PRM), "note": "52-week lead time; denser ChiP VTM is end of life"})
        lt = C["v48"]["ltm4664"]
        rows.append({
            "conversion": "48 V → 1 V", "approach": "Off-the-shelf, single module (catalog)", "point": "At rating",
            "topology": "4:1 switched-capacitor divider + dual-phase buck in one module",
            "distribution": "Distributed: 20 modules × 50 A per kA",
            "components": "ADI LTM4664 (16 × 16 × 7.7 mm µModule)",
            "f_sw": "0.1 / 0.2 MHz (stage 1 / 2)", "J": lt["J"], "eta": 100 * lt["eta"], "eta_hot": None,
            "cost": money(20 * LTM[0], 20 * LTM[1]), "note": "price of the 60 A LTM4664A used"})
        fe = C["v48"]["ferric_two_stage"]
        rows.append({
            "conversion": "48 V → 1 V", "approach": "Off-the-shelf, advanced IVR (estimate)", "point": "Estimate",
            "topology": "48→12 V bus converter + 12→1.8 V buck modules + 16-phase integrated VR",
            "distribution": "Distributed: ≈1.2 bus converters + ≈6 modules + ≈6.3 IVRs × 160 A per kA",
            "components": "Vicor NBM2317; MPS MPC22165-170; Ferric Fe1766",
            "f_sw": "15 MHz (IVR)", "J": fe["J"], "eta": 100 * fe["eta"], "eta_hot": None,
            "cost": "not public (Ferric) + ≈$250", "note": "IVR alone 4.5 A/mm²; needs a 1.8 V bus"})
        rows.append({
            "conversion": "48 V → 1 V", "approach": "Vendor claim, not catalog", "point": "Claimed",
            "topology": "Vertical power: current multiplier under the load, regulator elsewhere",
            "distribution": "Distributed multipliers",
            "components": "Vicor MCM / GCM (VPD)", "f_sw": "—", "J": None, "J_text": "2–5 (multiplier only)",
            "eta": None, "eta_text": "≈94% claimed", "eta_hot": None, "cost": "not public",
            "note": "sold to strategic customers"})
    else:
        mods = C["v12"]["modules_MPC22165"]
        # the 1 A/mm2 point (interpolated) and the rating point
        a, b = mods[2], mods[3]
        t = (1.0 - a["J"]) / (b["J"] - a["J"])
        eta1 = a["eta"] + t * (b["eta"] - a["eta"])
        i1 = a["I_module_A"] + t * (b["I_module_A"] - a["I_module_A"])
        for (J, eta, i_mod, label) in ((1.0, eta1, i1, "1 A/mm²"),
                                       (mods[5]["J"], mods[5]["eta"], mods[5]["I_module_A"],
                                        "Modules at 168 A (near the 170 A rating)")):
            n_mod = 1000.0 / i_mod
            ctrl = math.ceil(2 * n_mod / 12)
            lo = n_mod * MPC[0] + ctrl * CTRL[0] + CAPS[0]
            hi = n_mod * MPC[1] + ctrl * CTRL[1] + CAPS[1]
            rows.append({
                "conversion": "12 V → 1 V", "approach": "Off-the-shelf, integrated-inductor modules (catalog)",
                "point": label, "topology": "2-phase buck, smart power stages + inductors in one module",
                "distribution": f"Distributed: ≈{n_mod:.1f} modules × {i_mod:.0f} A per kA ({2 * n_mod:.0f} phases)",
                "components": "MPS MPC22165-170 (9 × 9.9 × 9.65 mm); multiphase controller",
                "f_sw": "0.5 MHz", "J": J, "eta": 100 * eta, "eta_hot": None, "cost": money(lo, hi),
                "note": ("measured vendor curve moved to 1 V; Infineon TDM22545D similar size at $15–18"
                         if label == "1 A/mm²" else "43 W per module; needs a cold plate")})
        rows.append({
            "conversion": "12 V → 1 V", "approach": "Off-the-shelf, discrete multiphase (catalog)", "point": "Typical",
            "topology": "Multiphase buck: one smart power stage + one inductor per phase",
            "distribution": "Distributed: 18–20 phases × 50–55 A per kA",
            "components": "Infineon TDA21590 (or MPS MP87190, TI CSD95410RRB); Coilcraft SLC1049-101 (100 nH); Infineon XDPE192C3B controller",
            "f_sw": "0.4–0.8 MHz", "J": None, "J_text": "0.2–0.35", "eta": None, "eta_text": "not evaluated",
            "eta_hot": None, "cost": "$85–155", "note": "standard server VR layout"})
        fe = C["v12"]["ferric_two_stage"]
        n1 = (1000.0 / 0.89 / 1.8) / 105.0
        rows.append({
            "conversion": "12 V → 1 V", "approach": "Off-the-shelf, advanced IVR (estimate)", "point": "Estimate",
            "topology": "12→1.8 V buck modules + 16-phase integrated VR",
            "distribution": f"Distributed: ≈{n1:.1f} modules + ≈6.3 IVRs × 160 A per kA",
            "components": "MPS MPC22165-170; Ferric Fe1766",
            "f_sw": "15 MHz (IVR)", "J": fe["J"], "eta": 100 * fe["eta"], "eta_hot": None,
            "cost": "not public (Ferric) + ≈$150–175",
            "note": "gains transient response, not area; Empower 3.3 V-input IVRs similar"})

# ---- write CSV
cols = ["conversion", "approach", "point", "topology", "distribution", "components", "f_sw",
        "current_density_A_per_mm2", "efficiency_pct_25C", "efficiency_pct_hot", "cost_per_kA_usd", "note"]
with open(os.path.join(HERE, "final_results_table.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(cols)
    for r in rows:
        w.writerow([r["conversion"], r["approach"], r["point"], r["topology"], r["distribution"],
                    r["components"], r["f_sw"],
                    f"{r['J']:.2f}" if r.get("J") is not None else r.get("J_text", ""),
                    f"{r['eta']:.1f}" if r.get("eta") is not None else r.get("eta_text", ""),
                    f"{r['eta_hot']:.1f}" if r.get("eta_hot") is not None else "",
                    r["cost"], r["note"]])

# ---- write HTML fragment
e = html.escape
out = ['<table class="final">',
       '<thead><tr><th scope="col">Approach</th><th scope="col">Operating point</th>'
       '<th scope="col">Topology</th><th scope="col">Single or distributed</th>'
       '<th scope="col">Components</th><th scope="col" class="r">f<sub>sw</sub></th>'
       '<th scope="col" class="r">A/mm²</th><th scope="col" class="r">Efficiency</th>'
       '<th scope="col" class="r">Cost per kA</th></tr></thead><tbody>']
cur = None
for r in rows:
    if r["conversion"] != cur:
        cur = r["conversion"]
        out.append(f'<tr class="group"><th colspan="9" scope="colgroup">{e(cur)}</th></tr>')
    J = f"{r['J']:.2f}" if r.get("J") is not None else e(r.get("J_text", ""))
    if r.get("eta") is not None:
        eta = f"{r['eta']:.1f}%" + (f"<br><small>{r['eta_hot']:.1f}% hot</small>" if r.get("eta_hot") else "")
    else:
        eta = e(r.get("eta_text", ""))
    cls = ' class="this-study"' if r["approach"].startswith("HVR_OPT") else ""
    out.append(f'<tr{cls}><td>{e(r["approach"])}</td><td>{e(r["point"])}</td><td>{e(r["topology"])}</td>'
               f'<td>{e(r["distribution"])}</td><td>{e(r["components"])}<br><small>{e(r["note"])}</small></td>'
               f'<td class="r">{e(r["f_sw"])}</td><td class="r">{J}</td><td class="r">{eta}</td>'
               f'<td class="r">{e(r["cost"])}</td></tr>')
out.append("</tbody></table>")
open(os.path.join(HERE, "final_results_table.html"), "w").write("\n".join(out) + "\n")
for r in rows:
    J = f"{r['J']:.2f}" if r.get("J") is not None else r.get("J_text", "")
    eta = f"{r['eta']:.1f}" if r.get("eta") is not None else r.get("eta_text", "")
    print(f"{r['conversion']} | {r['approach'][:34]:34s} | {r['point'][:28]:28s} | {r['distribution'][:58]:58s} | {J:>6} | {eta:>6} | {r['cost']}")
