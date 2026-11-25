#!/usr/bin/env python3
"""Si-IF backside VR study -- results from the sweeps.

Reads sweep_<tag>_best.json (sif_sweep.py) for 48 V and 12 V and writes
  results_summary.json   per V_in and packing mode/keep-out: the efficiency-vs-density curve
                         (grid J_t and Pareto front on the achieved density), the maximum
                         density and its design, the maximum efficiency and its design, the
                         design at 1 A/mm^2, TWV/routing loss and system efficiency, BOM cost
  curve_<vin>.csv        minimum-loss design per J_t (every mode and keep-out)
  pareto_<vin>.csv       non-dominated designs on (achieved density, efficiency)
  designs_<vin>.csv      the reported designs with loss breakdown, parts and cost

    python sif_report.py [--tags v48,v12]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import twv_routing as T  # noqa: E402

def open_text(path):
    """Open a result file, or its gzip copy (path + ".gz") when only that is present."""
    import gzip
    if os.path.isfile(path):
        return open(path)
    return gzip.open(path + ".gz", "rt")


P_OUT = 1000.0
BASE = ("power", 100.0)
TWV_T_UM = (100.0, 300.0, 700.0)
TWV_BASE_T_UM = 300.0
I_VIA = 0.75
T_CU_UM = 20.0
N_SQ = 1.0 / 3.0


# ------------------------------------------------------------------ prices
def load_prices():
    """Volume unit prices (USD): EPC parts from the product table (= Digi-Key's largest
    tape-and-reel break) completed by the largest break for commercial parts the table lacks;
    MLCCs at the largest reel break; inductors from inductor_library.json; the uP1966E driver at
    its largest reel break; 0402 bootstrap capacitors at $0.01 (assumed)."""
    import sif_core as S
    P = {"epc": {}, "epc_src": {}, "ind": {}, "mlcc": {}, "driver": None, "boot": 0.01,
         "proxies": {}}
    P["epc"], P["epc_src"] = S.device_prices()
    pr = json.load(open(os.path.join(HERE, "prices_raw.json")))
    for e in pr.get("mlcc", []):
        v = e.get("price_10k_or_reel") or e.get("price_1k")
        if v:
            P["mlcc"][e["part"]] = float(v)
    # Murata in-production parts Digi-Key does not stock: nearest stocked equivalent
    for miss, proxy in (("GRM188C81E106ME01", "GRM188C81C106MA73"),
                        ("GRM155D71E105KE11", "GRM188C71E225KE11")):
        if miss not in P["mlcc"] and proxy in P["mlcc"]:
            P["mlcc"][miss] = P["mlcc"][proxy]
            P["proxies"][miss] = proxy
    drv = [e for e in pr.get("drivers", []) if str(e.get("part", "")).lower().startswith("up1966")]
    if drv:
        tr = (drv[0].get("price_breaks") or {}).get("tape_reel") or []
        P["driver"] = float(tr[-1][1]) if tr else float(drv[0]["price"])
    lib = os.path.join(HERE, "inductor_library.json")
    if os.path.isfile(lib):
        for p in json.load(open(lib))["parts"]:
            if p.get("price_usd"):
                P["ind"][f"{p['vendor']}-{p['part_number']}"] = float(p["price_usd"])
    return P


def _vendor_part(cap_name):
    return cap_name.split("-")[1] if cap_name and cap_name.startswith("Murata-") else None


def bom(rec, P):
    """Parts per cell x cells, USD per 1 kA (I_total = 1 kA)."""
    N, K, M = rec["N"], rec["K"], rec["M"]
    rows = [("HS GaN FET", rec["hs"], N, P["epc"].get(rec["hs"])),
            ("LS GaN FET", rec["ls"], K, P["epc"].get(rec["ls"])),
            ("inductor", rec["inductor"], K, P["ind"].get(rec["inductor"]))]
    if N > 1:
        rows.append(("flying MLCC", rec["capacitor"], N - 1,
                     P["mlcc"].get(_vendor_part(rec["capacitor"]))))
    cell = sum(n * (p or 0.0) for _, _, n, p in rows)
    missing = [pn for _, pn, n, p in rows if n > 0 and p is None]
    ovh_rows = [("half-bridge driver (uP1966E)", "uP1966E", math.ceil((N + K) / 2), P["driver"]),
                ("bootstrap MLCC 0402", "0402", N, P["boot"]),
                ("input MLCC 0805", "GRM21BD72A225KE01" if rec["V_in"] > 24 else "GRM21BC71E106KE01",
                 2, P["mlcc"].get("GRM21BD72A225KE01" if rec["V_in"] > 24 else "GRM21BC71E106KE01"))]
    ovh = sum(n * (p or 0.0) for _, _, n, p in ovh_rows)
    return {"per_cell_usd": cell, "per_kA_usd": M * cell, "per_kA_with_drivers_usd": M * (cell + ovh),
            "lines": [{"item": a, "part": b, "per_cell": n, "unit_usd": p, "total_usd":
                       (M * n * p if p is not None else None)} for a, b, n, p in rows],
            "overhead_lines": [{"item": a, "part": b, "per_cell": n, "unit_usd": p} for a, b, n, p
                               in ovh_rows],
            "missing_prices": missing}


# ------------------------------------------------------------------ system loss
def system(rec):
    P_conv = rec["loss_total_W"]
    route = T.routing_loss_w(P_OUT, rec["I_cell_A"], T_CU_UM, N_SQ)["P_route_W"]
    out = {"P_route_W": route, "routing_assumption": f"{T_CU_UM:g}-um Cu, {N_SQ:.3f} sq/polarity"}
    for t in TWV_T_UM:
        tw = T.twv_loss_w(P_OUT, t, 50.0, I_VIA)
        out[f"P_TWV_{int(t)}um_W"] = tw["P_TWV_W"]
        out[f"eta_sys_{int(t)}um"] = T.system_efficiency(P_OUT, P_conv, tw["P_TWV_W"], route)
    out["n_vias_total"] = T.twv_loss_w(P_OUT, 300.0, 50.0, I_VIA)["n_vias_total"]
    return out


# ------------------------------------------------------------------ summary
def j_eff(r):
    """Achieved density of a record: the bisection's minimum cell (a constructive, slightly
    non-monotone test) or, for a grid record, at least the J_t at which it was placed."""
    j = r["J_achieved"]
    if r.get("kind") == "grid":
        j = max(j, r["J_target"])
    return j


def pareto(records):
    """Non-dominated records on (achieved density up, loss down)."""
    out, best = [], float("inf")
    for r in sorted(records, key=lambda r: (-j_eff(r), r["loss_total_W"])):
        if r["loss_total_W"] < best - 1e-12:
            out.append(r)
            best = r["loss_total_W"]
    return sorted(out, key=j_eff)


def hot_efficiency(r, k_fet=1.5, k_cu=1.3):
    """Rough efficiency at ~100 C: GaN R_DS(on) x1.5 and copper (inductor DCR) x1.3 on the
    conduction terms; the other terms unchanged."""
    b = r["breakdown_total_W"]
    extra = ((k_fet - 1) * (b["cond_hs_W"] + b["cond_ls_W"]) + (k_cu - 1) * b["cond_ind_dcr_W"])
    return P_OUT / (P_OUT + r["loss_total_W"] + extra)


def design_brief(r, P=None):
    d = {k: r.get(k) for k in (
        "V_in", "mode", "keepout_um", "J_target", "J_achieved", "cell_shape", "cell_min_WH_mm",
        "M", "I_cell_A", "topology", "N", "K", "K_A", "hs", "ls", "inductor", "ind_L_nH",
        "ind_DCR_mohm", "ind_Isat_A", "ind_Irms_A", "ind_dims_mm", "capacitor", "f_sw_Hz",
        "cell_area_mm2", "cell_min_area_mm2", "loss_cell_W", "loss_total_W", "efficiency",
        "dI_L_pp_A", "I_L_pk_A", "I_L_rms_A", "t_on_ns", "flying_cap_ripple_frac",
        "parts_per_cell", "breakdown_total_W")}
    d["J_effective"] = j_eff(r)
    d["backside_area_mm2"] = P_OUT / j_eff(r)
    d["heat_flux_W_per_cm2"] = r["loss_total_W"] / (P_OUT / j_eff(r)) * 100.0
    d["efficiency_hot_estimate"] = hot_efficiency(r)
    d["inductor_height_mm"] = (r.get("ind_dims_mm") or [None, None, None])[2]
    d["system"] = system(r)
    if P is not None:
        d["bom"] = bom(r, P)
    return d


def summarize(tag, P):
    d = json.load(open_text(os.path.join(HERE, f"sweep_{tag}_best.json")))
    meta, best, jmax, par = d["meta"], d["best"], d["jmax"], d["pareto_candidates"]
    vin = meta["V_in"]
    combos = sorted({(r["mode"], r["keepout_um"]) for r in best})
    out = {"meta": meta, "by_mode": {}}
    for mode, ko in combos:
        grid = sorted((r for r in best if (r["mode"], r["keepout_um"]) == (mode, ko)),
                      key=lambda r: r["J_target"])
        jm = [r for r in jmax if (r["mode"], r["keepout_um"]) == (mode, ko)]
        pc = pareto([r for r in par + best + jmax if (r["mode"], r["keepout_um"]) == (mode, ko)])
        rec = {"curve": [{"J_target": r["J_target"], "efficiency": r["efficiency"],
                          "J_achieved": j_eff(r), "topology": r["topology"], "M": r["M"],
                          "inductor": r["inductor"], "f_sw_Hz": r["f_sw_Hz"]} for r in grid],
               "pareto": [{"J_achieved": j_eff(r), "efficiency": r["efficiency"],
                           "topology": r["topology"], "M": r["M"], "inductor": r["inductor"],
                           "hs": r["hs"], "ls": r["ls"], "f_sw_Hz": r["f_sw_Hz"]} for r in pc]}
        if jm:
            jbest = max(r["J_target"] for r in jm)
            top = min((r for r in jm if r["J_target"] >= jbest * (1 - 1e-6)),
                      key=lambda r: r["loss_total_W"])
            rec["max_density"] = design_brief(top, P)
            # ranking of the topologies by their own maximum density
            per_topo = {}
            for r in jm:
                t = r["topology"]
                if t not in per_topo or r["J_target"] > per_topo[t]["J_max"]:
                    per_topo[t] = {"J_max": r["J_target"], "M": r["M"],
                                   "efficiency_at_J_max": r["efficiency"]}
            rec["max_density_by_topology"] = dict(sorted(per_topo.items(),
                                                         key=lambda kv: -kv[1]["J_max"]))
        if grid:
            eff = min(grid, key=lambda r: r["loss_total_W"])
            rec["max_efficiency"] = design_brief(eff, P)
            prac = [r for r in pc if j_eff(r) >= 0.1 - 1e-9]
            if prac:
                rec["max_efficiency_at_J_ge_0p1"] = design_brief(
                    min(prac, key=lambda r: r["loss_total_W"]), P)
            rec["efficiency_at_J"] = {f"{r['J_target']:g}": r["efficiency"] for r in grid}
            # highest density reached within 0.1 / 0.5 points of the best efficiency
            for tol in (0.001, 0.005):
                ok = [r for r in pc if r["efficiency"] >= eff["efficiency"] - tol]
                if ok:
                    rec[f"J_within_{tol*100:g}pt_of_max_eff"] = max(r["J_achieved"] for r in ok)
            at1 = [r for r in grid if abs(r["J_target"] - 1.0) < 1e-9]
            rec["at_1A_per_mm2"] = design_brief(at1[0], P) if at1 else None
            if not at1:
                rec["at_1A_per_mm2_note"] = "infeasible at 1 A/mm^2"
        out["by_mode"][f"{mode}_ko{int(ko)}"] = rec
    return vin, out


def system_curve(tag, mode="power", ko=100.0, t_cu_um=T_CU_UM, t_w_um=TWV_BASE_T_UM):
    """System-optimal design per J_t: over every (M, topology) of the sweep (sweep_<tag>_cells.csv),
    the minimum of conversion + TWV + backside-routing loss (routing grows with the cell
    current, so smaller cells than the conversion-only optimum can win)."""
    p_twv = T.twv_loss_w(P_OUT, t_w_um, 50.0, I_VIA)["P_TWV_W"]
    best = {}
    for r in csv.DictReader(open_text(os.path.join(HERE, f"sweep_{tag}_cells.csv"))):
        if r["kind"] != "grid" or r["mode"] != mode or float(r["keepout_um"]) != ko:
            continue
        J = float(r["J_target"])
        conv = float(r["loss_total_W"])
        route = T.routing_loss_w(P_OUT, float(r["I_cell_A"]), t_cu_um, N_SQ)["P_route_W"]
        tot = conv + p_twv + route
        if J not in best or tot < best[J]["P_total_W"]:
            best[J] = {"J_target": J, "M": int(r["M"]), "I_cell_A": float(r["I_cell_A"]),
                       "topology": r["topology"], "hs": r["hs"], "ls": r["ls"],
                       "inductor": r["inductor"], "f_sw_Hz": float(r["f_sw_Hz"]),
                       "P_conv_W": conv, "P_TWV_W": p_twv, "P_route_W": route, "P_total_W": tot,
                       "eta_conv": float(r["efficiency"]), "eta_sys": P_OUT / (P_OUT + tot)}
    return [best[J] for J in sorted(best)]


FLAT = ["V_in", "role", "mode", "keepout_um", "J_target", "J_achieved", "M", "I_cell_A",
        "topology", "hs", "ls", "inductor", "capacitor", "f_sw_Hz", "efficiency", "loss_total_W"]
BRK = ["cond_hs_W", "cond_ls_W", "cond_ind_dcr_W", "cond_cap_esr_W", "sw_overlap_W", "gate_W",
       "coss_W", "ind_core_W"]


def write_sources(P):
    """sources.json: where every library value and price comes from."""
    import sif_core as S
    lib = json.load(open(os.path.join(HERE, "inductor_library.json")))
    mlcc = json.load(open(os.path.join(HERE, "mlcc_vendor_data.json")))
    pr = json.load(open(os.path.join(HERE, "prices_raw.json")))
    out = {
        "devices": {
            "library": "EPC product table (Scalable_Integrated_VR/EPC-Product-Table.csv) through "
                       "the engine loader; datasheet R_G, Q_OSS test voltage and heights from "
                       "Scalable_Integrated_VR/src/HVR_epc_device_data.json",
            "excluded": S.DEVICE_FILTER_NOTE.get("dropped") or
                        "rad-hard EPC Space parts (EPC7xxx) and parts without a commercial price",
            "prices": "EPC product-table price column; matches Digi-Key's largest tape-and-reel "
                      "break (prices_raw.json epc_check: median ratio 1.00)",
            "price_check": pr.get("epc_check")},
        "capacitors": {
            "library": "Murata catalog MLCCs (in production), rated per the engine's corrected "
                       "rule; DC bias, C(T) at bias and ESR(f) from Murata's product-information "
                       "API (mlcc_fetch.py -> mlcc_vendor_data.json)",
            "fetched": mlcc.get("fetched"),
            "parts": {pn: {"url": r["url"], "rated_V": r["rated_voltage_V"],
                           "dielectric": r["dielectric"], "size": r["size_inch"],
                           "temp_factor_basis": r["temp_factor_basis"],
                           "price_usd": P["mlcc"].get(pn),
                           "price_proxy": P["proxies"].get(pn)}
                      for pn, r in mlcc["parts"].items()},
            "prices": "Digi-Key largest reel break (prices_raw.json)"},
        "inductors": {
            "library": "catalog power inductors from manufacturer datasheets "
                       "(inductor_catalog_raw.json -> build_inductor_library.py -> "
                       "inductor_library.json); per-part sources in inductor_sources.json",
            "calibration": {k: v for k, v in lib["meta"].items() if k != "notes"},
            "core_loss_methods": sorted({p["core_loss_method"] for p in lib["parts"]}),
            "excluded": "research, integrated and in-house inductors (e.g. Shared_Core_UIC_250_nH, "
                        "the UIC/literature entries of the engine library)"},
        "gate_driver": {"part": "uP1966E (12-WLCSP 1.6 x 1.6 mm)", "price_usd": P["driver"],
                        "source": "Digi-Key largest reel break (prices_raw.json)"},
        "prices_retrieved": pr.get("retrieved"),
    }
    json.dump(out, open(os.path.join(HERE, "sources.json"), "w"), indent=1, default=str)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", default="v48,v12")
    ap.add_argument("--out", default="results_summary.json")
    args = ap.parse_args()
    P = load_prices()
    summary = {"assumptions": {
        "efficiency": "converter: P_out / (P_out + conversion loss), P_out = 1 kW",
        "twv": f"Cu, 50 um, {I_VIA} A/via, rho {T.RHO_CU} Ohm m, rail + return, t_w {TWV_T_UM} um",
        "routing": f"backside Cu {T_CU_UM} um, {N_SQ:.3f} squares per polarity per cell",
        "bom": "EPC product-table 2.5k price (missing parts from distributors), catalog inductor "
               "and MLCC prices at ~1k (inductor_library.json, prices_raw.json)"}, "results": {}}
    for tag in args.tags.split(","):
        vin, s = summarize(tag, P)
        summary["results"][f"{vin:g}V"] = s
        with open(os.path.join(HERE, f"curve_{int(vin)}V.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["mode_ko", "J_target", "efficiency", "J_achieved", "topology", "M",
                        "inductor", "f_sw_Hz"])
            for key, rec in s["by_mode"].items():
                for c in rec["curve"]:
                    w.writerow([key, c["J_target"], c["efficiency"], c["J_achieved"],
                                c["topology"], c["M"], c["inductor"], c["f_sw_Hz"]])
        with open(os.path.join(HERE, f"pareto_{int(vin)}V.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["mode_ko", "J_achieved", "efficiency", "topology", "M", "hs", "ls",
                        "inductor", "f_sw_Hz"])
            for key, rec in s["by_mode"].items():
                for c in rec["pareto"]:
                    w.writerow([key, c["J_achieved"], c["efficiency"], c["topology"], c["M"],
                                c["hs"], c["ls"], c["inductor"], c["f_sw_Hz"]])
        with open(os.path.join(HERE, f"designs_{int(vin)}V.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(FLAT + BRK + ["J_effective", "heat_flux_W_per_cm2", "eta_hot_estimate",
                                     "P_TWV_300um_W", "P_route_W", "eta_sys_300um",
                                     "bom_per_kA_usd", "bom_with_drivers_usd"])
            for key, rec in s["by_mode"].items():
                for role in ("max_density", "max_efficiency", "max_efficiency_at_J_ge_0p1",
                             "at_1A_per_mm2"):
                    r = rec.get(role)
                    if not r:
                        continue
                    w.writerow([r.get(k) if k != "role" else role for k in FLAT]
                               + [r["breakdown_total_W"][k] for k in BRK]
                               + [r["J_effective"], r["heat_flux_W_per_cm2"],
                                  r["efficiency_hot_estimate"]]
                               + [r["system"]["P_TWV_300um_W"], r["system"]["P_route_W"],
                                  r["system"]["eta_sys_300um"], r["bom"]["per_kA_usd"],
                                  r["bom"]["per_kA_with_drivers_usd"]])
    for tag in args.tags.split(","):
        vin = json.load(open_text(os.path.join(HERE, f"sweep_{tag}_best.json")))["meta"]["V_in"]
        sc = {}
        for tcu in (20.0, 50.0):
            cur = system_curve(tag, t_cu_um=tcu)
            sc[f"cu{int(tcu)}um"] = cur
            with open(os.path.join(HERE, f"curve_system_{int(vin)}V_cu{int(tcu)}um.csv"), "w",
                      newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(cur[0].keys()))
                w.writeheader()
                w.writerows(cur)
        summary["results"][f"{vin:g}V"]["system_optimal_power_ko100"] = {
            "assumptions": f"TWV {TWV_BASE_T_UM:g} um, {I_VIA} A/via; routing {N_SQ:.3f} sq per "
                           "polarity per cell, Cu thickness as keyed",
            **sc}
    json.dump(summary, open(os.path.join(HERE, args.out), "w"), indent=1, default=float)
    write_sources(P)
    for v, s in summary["results"].items():
        for key, rec in s["by_mode"].items():
            md, me, a1 = rec.get("max_density"), rec.get("max_efficiency"), rec.get("at_1A_per_mm2")
            mp = rec.get("max_efficiency_at_J_ge_0p1")
            print(f"   (J>=0.1: eta {100*mp['efficiency']:.2f}% at J {mp['J_effective']:.3f}, "
                  f"{mp['topology']} M={mp['M']})" if mp else "")
            print(f"{v} {key:14s} Jmax={md['J_target'] if md else float('nan'):.3f} "
                  f"(eta {100*md['efficiency'] if md else float('nan'):.2f}%, {md and md['topology']}, M={md and md['M']}) | "
                  f"eta_max={100*me['efficiency']:.2f}% at J_ach={me['J_achieved']:.3f} ({me['topology']}, M={me['M']}) | "
                  f"1A/mm2: {('%.2f%% ' % (100*a1['efficiency']) + a1['topology']) if a1 else 'infeasible'}")


if __name__ == "__main__":
    main()
