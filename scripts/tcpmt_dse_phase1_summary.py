"""Regulator-count screen, TCPMT revision phase 1: switch-voltage rule, corrected output-
capacitance (C_OSS) term and tier packing, against the corrected-capacitor run.

Runs (case D, research/tcpmt_revision/dse_j35/data/), written by scripts/tcpmt_dse_phase1_runs.sh
with the sweep driver of the published runs (research/tcpmt_revision/dse_j35/sweep_etm.py). The
engine defaults are the authors' decisions: corrected capacitor rule, switch derating 0.9,
corrected C_OSS, packing with a 50-um keep-out.
  etm35_p1_legacycheck   all four legacy flags                  must equal etm35 (published)
  etm35_p1_swlegacy      capacitor corrected, other three legacy must equal etm35_caprule_full
  etm35_p1a_sw90         (a)  capacitor + switch rule (derating 0.9)
  etm35_p1a_sw95         (a') the same with derating 0.95 (sensitivity)
  etm35_p1b_coss         (b)  (a) + corrected C_OSS term
  etm35_p1c_full         (c)  (b) + tier packing = the full set (engine defaults)
  etm35_p1c_full_sw95    the full set with derating 0.95 (sensitivity)
  <tag>_m81              the same runs at M = 81 (9 x 9, not one of the 17 counts)

    python tcpmt_dse_phase1_summary.py -> research/tcpmt_revision/dse_phase1_summary.json
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
TR = R / "research" / "tcpmt_revision"
D = TR / "dse_j35" / "data"
SIVR = R / "Scalable_Integrated_VR"
sys.path.insert(0, str(SIVR / "src"))
import HVR_FULL_OPT_EPC_V2 as H  # noqa: E402

V_IN, V_OUT, P_LOAD, J = 48.0, 1.0, 1000.0, 3.5
BASE = "etm35_caprule_full"
RUNS = {   # tag: (label, what, environment, previous step)
    "etm35_p1a_sw90": ("a", "corrected capacitor rule + switch rule (derating 0.9)",
                       "HVR_CAP_RULE=stress HVR_SW_RULE=stress HVR_SW_DERATING=0.9 "
                       "HVR_COSS_RULE=legacy HVR_PACK_RULE=off", BASE),
    "etm35_p1a_sw95": ("a'", "corrected capacitor rule + switch rule (derating 0.95)",
                       "HVR_CAP_RULE=stress HVR_SW_RULE=stress HVR_SW_DERATING=0.95 "
                       "HVR_COSS_RULE=legacy HVR_PACK_RULE=off", "etm35_p1a_sw90"),
    "etm35_p1b_coss": ("b", "(a) + corrected C_OSS term",
                       "HVR_CAP_RULE=stress HVR_SW_RULE=stress HVR_SW_DERATING=0.9 "
                       "HVR_COSS_RULE=corrected HVR_PACK_RULE=off", "etm35_p1a_sw90"),
    "etm35_p1c_full": ("c", "(b) + tier packing (keep-out 50 um): the full set, engine defaults",
                       "HVR_CAP_RULE=stress HVR_SW_RULE=stress HVR_SW_DERATING=0.9 "
                       "HVR_COSS_RULE=corrected HVR_PACK_RULE=on HVR_PACK_KEEPOUT_UM=50",
                       "etm35_p1b_coss"),
    "etm35_p1c_full_sw95": ("c'", "the full set with switch derating 0.95",
                            "HVR_CAP_RULE=stress HVR_SW_RULE=stress HVR_SW_DERATING=0.95 "
                            "HVR_COSS_RULE=corrected HVR_PACK_RULE=on HVR_PACK_KEEPOUT_UM=50",
                            "etm35_p1c_full"),
}
FINAL = "etm35_p1c_full"
CHECKS = {"etm35_p1_legacycheck": ("etm35", "HVR_CAP_RULE=legacy HVR_SW_RULE=legacy "
                                            "HVR_COSS_RULE=legacy HVR_PACK_RULE=off"),
          "etm35_p1_swlegacy": (BASE, "HVR_CAP_RULE=stress HVR_SW_RULE=legacy "
                                      "HVR_COSS_RULE=legacy HVR_PACK_RULE=off")}
ENGINE = Path("/home/beams0/SABDELZAHER/ETM_project/scratch/dse_engine_phase1")


def load(tag):
    p = D / f"case_D_{tag}.csv"
    return {int(float(r["M"])): r for r in csv.DictReader(p.open())} if p.exists() else {}


def sel(r):
    if r is None or r.get("feasible") != "True":
        return None
    return {"arch": r["arch"], "hs": r["hs"], "ls": r["ls"],
            "f_sw_kHz": round(float(r["f_sw_Hz"]) / 1e3, 2),
            "conv_per_cell_W": round(float(r["conv_loss_per_vr_W"]), 5),
            "conv_total_W": round(float(r["conv_loss_total_W"]), 3),
            "routing_W": round(float(r["routing_loss_W"]), 3),
            "P_total_W": round(float(r["total_loss_W"]), 3),
            "area_mm2": round(float(r["area_mm2"]), 4),
            "area_budget_mm2": round(float(r["area_budget_mm2"]), 4),
            "component_count": int(float(r["component_count"])),
            **({"inductor": r["inductor"], "capacitor": r["capacitor"]}
               if r.get("inductor") else {})}


def key(s):
    return None if s is None else (s["arch"], s["hs"], s["ls"], s["f_sw_kHz"])


def identical(tag, ref):
    """Per output file: every row equal on all of the reference's columns. (The driver gained
    two columns, the selected inductor and capacitor, after the reference runs were written, so
    the files are compared on the reference's columns rather than byte for byte.)"""
    out = {}
    for stem in ("case_A", "case_B", "case_C", "case_D", "all_architectures"):
        a, b = D / f"{stem}_{tag}.csv", D / f"{stem}_{ref}.csv"
        if not (a.exists() and b.exists()):
            out[stem] = None
            continue
        ra, rb = list(csv.DictReader(a.open())), list(csv.DictReader(b.open()))
        cols = list(rb[0].keys()) if rb else []
        out[stem] = {"rows_equal_on_reference_columns":
                     len(ra) == len(rb) and all(x.get(c) == y[c] for x, y in zip(ra, rb)
                                                for c in cols),
                     "byte_identical": a.read_bytes() == b.read_bytes(),
                     "extra_columns": sorted(set(ra[0]) - set(cols)) if ra else []}
    return out


def arch_of(label):
    n, k, ka = (int(x.split("=")[1]) for x in label.split(","))
    return H.VRArchitecture(N=n, K=k, K_A=ka, B_array=H.generate_B_array(n, k, ka),
                            D=n * V_OUT / V_IN, component_count=0)


DEV = {r["PartNumber"]: H.row_to_device(r) for _, r in
       H.load_epc_devices(str(SIVR / "EPC-Product-Table.csv"), V_gs_op=5.0).iterrows()}


def coss(arch, hs, ls, f, m):
    """C_OSS power of one design under both rules: per cell and for m cells (W)."""
    e = H.coss_energy_per_period(arch, DEV[hs], DEV[ls], V_IN)
    legacy = (f / 2) * (arch.N * DEV[hs].C_OSS * (V_IN / arch.N - V_OUT) ** 2
                        + arch.K * DEV[ls].C_OSS * V_OUT ** 2)
    return {"legacy_per_cell_W": legacy, "legacy_total_W": legacy * m,
            "corrected_per_cell_W": f * e["total"], "corrected_total_W": f * e["total"] * m,
            "corrected_split_total_W": {k: f * v * m for k, v in e.items() if k != "total"}}


def coss_digitized_49():
    """The same transitions with the digitized datasheet curves of research/tcpmt_revision/
    omitted_losses_inputs.json (EPC2014C C_OSS-derived Q/E, EPC2057 Q_OSS), interpolated as
    scripts/tcpmt_omitted_losses.py does; reproduces that script's 'datasheet_hard_turn_on_w'
    (no stacked term) and adds the stacked-switch charge."""
    dig = json.loads((TR / "omitted_losses_inputs.json").read_text())
    c14, q57 = dig["EPC2014C_coss"], dig["EPC2057_qoss"]

    def q14(v):
        return float(np.interp(v, [0] + c14["V_DS_V"], [0] + c14["Q_OSS_nC"])) * 1e-9

    def e14(v):
        return float(np.interp(v, [0] + c14["V_DS_V"], [0] + c14["E_OSS_nJ"])) * 1e-9

    vv = [0.0] + [x for x, q in zip(q57["V_DS_V"], q57["Q_OSS_nC"]) if q is not None]
    qq = [0.0] + [q for q in q57["Q_OSS_nC"] if q is not None]

    def q57f(v):
        return float(np.interp(v, vv, qq)) * 1e-9

    def e57(v):
        vg = np.linspace(0, v, 400)
        qg = np.interp(vg, vv, qq)
        return float(np.sum(0.5 * (vg[1:] + vg[:-1]) * np.diff(qg))) * 1e-9

    f, m, v1, v2 = 805170.3343770516, 49, 16.0, 32.0
    e_hs, e_node = 3 * e14(v1), 3 * (q57f(v1) * v1 - e57(v1))
    e_stk = 2 * (v2 * (q14(v2) - q14(v1)) - (e14(v2) - e14(v1)))
    return {"hs_turn_on_W": e_hs * f * m, "switch_node_W": e_node * f * m,
            "stacked_W": e_stk * f * m, "total_W": (e_hs + e_node + e_stk) * f * m,
            "without_stacked_W": (e_hs + e_node) * f * m,
            "sqrt_law_vs_curves": {"Q_EPC2057_16V_nC": [H.q_oss_at(DEV["EPC2057"], 16) * 1e9,
                                                        q57f(16) * 1e9],
                                   "E_EPC2057_16V_nJ": [H.e_oss_at(DEV["EPC2057"], 16) * 1e9,
                                                        e57(16) * 1e9],
                                   "E_EPC2014C_16V_nJ": [H.e_oss_at(DEV["EPC2014C"], 16) * 1e9,
                                                         e14(16) * 1e9]}}


def min_side(n, part, keep_mm=0.05):
    """Smallest square side (mm, 1-um resolution) holding n copies of part."""
    x, y = H.part_dims_mm(part)
    lo, hi = 0.0, 20.0
    while hi - lo > 1e-3:
        mid = 0.5 * (lo + hi)
        lo, hi = (lo, mid) if H.pack_identical(n, x, y, mid, keep_mm) else (mid, hi)
    return round(hi, 3)


def packing_49():
    a = arch_of("N=3,K=3,K_A=2")
    hs, ls = DEV["EPC2014C"], DEV["EPC2057"]
    ind = [i for i in H.INDUCTOR_LIBRARY if i.name == "Shared_Core_UIC_250_nH"][0]
    caps = {c.name: c for c in H.default_capacitor_library("stress")}
    cells = {"production_cell_5.61mm2": math.sqrt(5.61),
             "area_budget_5.83mm2": math.sqrt(P_LOAD / 49 / J)}
    out = {"design": "M=49 N3K3K_A2 EPC2014C/EPC2057 805 kHz, inductor Shared_Core_UIC_250_nH",
           "part_dims_mm": {"EPC2014C": H.part_dims_mm(hs), "EPC2057": H.part_dims_mm(ls),
                            "inductor": H.part_dims_mm(ind),
                            "C_f published (GCM21 0805)": H.CAP_DIMS_MM["Murata-GCM21-10uF-25V"],
                            "C_f rated (GRM188 0603)":
                                H.CAP_DIMS_MM["Murata-GRM188D72A105KE01-1uF-100V"]},
           "summed_tier_area_mm2": {"gan_hs": 3 * hs.footprint_mm2, "gan_ls": 3 * ls.footprint_mm2,
                                    "inductor": 3 * ind.footprint_mm2},
           "verdicts": {}}
    for cname in ("Murata-GCM21-10uF-25V", "Murata-GRM188D72A105KE01-1uF-100V"):
        for cell, side in cells.items():
            for k_um in (0.0, 50.0):
                out["verdicts"][f"{cname} | {cell} (side {side:.4f} mm) | keep-out {k_um:g} um"] = \
                    H.tier_report(a, hs, ls, ind, caps[cname], side, k_um)
    out["min_square_side_mm_keepout_50um"] = {
        "3 x EPC2014C": min_side(3, hs), "3 x EPC2057": min_side(3, ls),
        "3 x inductor": min_side(3, ind),
        "2 x 0603": min_side(2, caps["Murata-GRM188D72A105KE01-1uF-100V"]),
        "2 x 0805": min_side(2, caps["Murata-GCM21-10uF-25V"])}
    s = max(out["min_square_side_mm_keepout_50um"]["3 x EPC2014C"],
            out["min_square_side_mm_keepout_50um"]["3 x EPC2057"])
    out["parts_placeable_up_to"] = {"cell_side_mm": s, "cell_area_mm2": round(s * s, 3),
                                    "max_M_at_J3.5": int(P_LOAD / (J * s * s))}
    return out


def cc_candidates(area_budget_mm2):
    """The sweep driver's component-count candidates (sweep_etm.cc_candidates, copied here so
    the summary does not import the driver, which changes directory on import)."""
    implied = area_budget_mm2 / 0.48
    cands = {10, 15} | {c for c in (22, 30) if implied > c * 0.75}
    return sorted(c for c in cands if c <= 30)


def undecided_scan(counts):
    """Every placement question run (c) asks at these counts -- the tiers of every enumerated
    architecture with the parts that pass the device, inductor and capacitor screens -- and how
    many of them exhaust the exact-search budget (counted as not placeable)."""
    df = H.load_epc_devices(str(SIVR / "EPC-Product-Table.csv"), V_gs_op=5.0)
    H.PACK_STATS.update(exact_searches=0, undecided=0)
    H._PACK_CACHE.clear()                       # count every question afresh
    H._GUIL_CACHE.clear()
    lib = H.default_capacitor_library("stress")
    n_q = 0
    for m in counts:
        i_vr = P_LOAD / m
        side = math.sqrt(i_vr / J)
        for cc in cc_candidates(i_vr / J):
            for a in H.generate_architectures(1, 1, 1, 1, cc, V_OUT, V_IN):
                hs, ls = H.filter_candidate_devices(df, a, V_IN, V_OUT, 5.0, i_vr,
                                                    max(a.B_array), rule="stress")
                inds = H.filter_candidate_inductors(H.INDUCTOR_LIBRARY, a, i_vr)
                caps = H.filter_candidate_capacitors(lib, a, V_IN, rule="stress")
                for n, parts in ((a.N, hs), (a.K, ls), (a.K, inds), (a.N - 1, caps)):
                    for p in parts:
                        H.tier_packs(n, p, side, 50.0)
                        n_q += 1
    return {"questions": n_q, **H.PACK_STATS}


def packing_requirements_49():
    """What the 49-cell design's parts would need to be placed, and which parts would place."""
    side = math.sqrt(P_LOAD / 49 / J)
    i_vr = P_LOAD / 49
    out = {"cell_side_mm": side, "keepout_um": 50.0}
    for name, n, part in (("gan_hs", 3, DEV["EPC2014C"]), ("gan_ls", 3, DEV["EPC2057"])):
        x, y = H.part_dims_mm(part)
        n_max = max([k for k in range(0, 4) if H.pack_identical(k, x, y, side, 0.05)])
        s_min = min_side(n, part)
        out[name] = {"part": part.part_number, "per_tier_in_49_cell": n_max,
                     "tiers_needed": (math.ceil(n / n_max) if n_max else None),
                     "min_cell_side_mm": s_min, "min_cell_area_mm2": round(s_min ** 2, 3),
                     "J_needed_A_per_mm2": round(i_vr / s_min ** 2, 3),
                     "max_M_at_J3.5": int(P_LOAD / (J * s_min ** 2))}
    # parts that pass the screens of N3K3K_A2 at M = 49 and place three to a tier
    df = H.load_epc_devices(str(SIVR / "EPC-Product-Table.csv"), V_gs_op=5.0)
    a = arch_of("N=3,K=3,K_A=2")
    for d_ in (0.9, 0.95):
        old = H.SW_V_DERATING
        try:
            H.SW_V_DERATING = d_
            hs, ls = H.filter_candidate_devices(df, a, V_IN, V_OUT, 5.0, i_vr, max(a.B_array),
                                                rule="stress")
        finally:
            H.SW_V_DERATING = old
        out[f"placeable_three_per_tier_derating_{d_}"] = {
            "hs": [d.part_number for d in hs if H.tier_packs(3, d, side, 50.0)],
            "ls": [d.part_number for d in ls if H.tier_packs(3, d, side, 50.0)]}
    return out


def tiers_needed(s, m, keep_um=50.0):
    """Tiers one selected design would need with the packing rule: per class, the most copies
    that place in the square cell of the area budget and the resulting tier count (the area
    rule assumes one tier per class)."""
    side = math.sqrt(P_LOAD / m / J)
    a = arch_of(s["arch"])
    ind = {i.name: i for i in H.INDUCTOR_LIBRARY}.get(s.get("inductor"))
    cap = {c.name: c for c in H.default_capacitor_library("stress")}.get(s.get("capacitor"))
    out, total = {"cell_side_mm": round(side, 4)}, 0
    for cls, n, part in (("gan_hs", a.N, DEV[s["hs"]]), ("gan_ls", a.K, DEV[s["ls"]]),
                         ("inductor", a.K, ind), ("cap_fly", a.N - 1, cap)):
        if part is None:
            out[cls] = None
            continue
        x, y = H.part_dims_mm(part)
        per = max([k for k in range(0, n + 1) if H.pack_identical(k, x, y, side, keep_um * 1e-3)])
        t = math.ceil(n / per) if per else None
        out[cls] = {"count": n, "per_tier": per, "tiers": t}
        total = None if (t is None or total is None) else total + t
    out["total_tiers"] = total
    return out


def richer_budgets(counts=(49, 64), ccs=(22, 30)):
    """Full rule set at component budgets the sweep does not enumerate at these counts (its
    candidates there are 10 and 15): is any architecture feasible?"""
    old = (H.CAP_RULE, H.SW_RULE, H.SW_V_DERATING, H.COSS_RULE, H.PACK_RULE, H.PACK_KEEPOUT_UM)
    out = {}
    try:
        H.CAP_RULE, H.SW_RULE, H.SW_V_DERATING = "stress", "stress", 0.9
        H.COSS_RULE, H.PACK_RULE, H.PACK_KEEPOUT_UM = "corrected", "on", 50.0
        for m in counts:
            for cc in ccs:
                cwd = os.getcwd()
                os.chdir(SIVR)
                try:
                    rr = H.run_hvr_optimization(target_component_count=cc, V_in=V_IN, V_out=V_OUT,
                                                I_out=P_LOAD / m, V_gs_drive=5.0,
                                                ripple_factor=0.5, v_ripple_frac=0.25,
                                                I_target_density=J, verbose=False)
                finally:
                    os.chdir(cwd)
                feas = [f"N={r.architecture.N},K={r.architecture.K},K_A={r.architecture.K_A}"
                        for r in rr if np.isfinite(r.optimized_loss) and r.ripple_satisfied
                        and r.area_feasible]
                out[f"M{m}_cc{cc}"] = {"architectures": len(rr), "feasible": feas}
    finally:
        (H.CAP_RULE, H.SW_RULE, H.SW_V_DERATING, H.COSS_RULE, H.PACK_RULE,
         H.PACK_KEEPOUT_UM) = old
    return out


def run_summary(tag, base_rows, prev_rows):
    rows = load(tag)
    m81 = load(tag + "_m81").get(81)
    per = {m: sel(rows[m]) for m in sorted(rows)}
    feas = {m: s for m, s in per.items() if s}
    opt_m = min(feas, key=lambda m: feas[m]["P_total_W"]) if feas else None
    sq = {m: (feas[m]["P_total_W"] if m in feas else None) for m in (36, 49, 64)}
    sq_ok = {m: v for m, v in sq.items() if v is not None}
    s49, b49 = per.get(49), sel(base_rows.get(49))
    return {
        "optimum": None if opt_m is None else {"M": opt_m, **feas[opt_m]},
        "square_grid": {"P_total_W": sq,
                        "best_of_36_49_64": (None if not sq_ok else
                                             min(sq_ok, key=sq_ok.get)),
                        "M81_feasible": bool(m81 and m81["feasible"] == "True"),
                        "M81": sel(m81),
                        "M100_feasible": bool(per.get(100))},
        "feasible_counts": sorted(feas),
        "M49": s49, "M49_differs_from_caprule_full": key(s49) != key(b49),
        "M49_caprule_full": b49,
        "N2_designs": {m: f"{s['hs']}/{s['ls']} {s['f_sw_kHz']} kHz" for m, s in feas.items()
                       if s["arch"].startswith("N=2,")},
        "selection_changed_vs_caprule_full_at_M": [m for m in per if key(per[m]) !=
                                                   key(sel(base_rows.get(m)))],
        "selection_changed_vs_previous_step_at_M": (None if prev_rows is None else
                                                   [m for m in per if key(per[m]) !=
                                                    key(sel(prev_rows.get(m)))]),
        "per_count": per,
    }


def main():
    base = load(BASE)
    checks = {}
    for tag, (ref, env) in CHECKS.items():
        same = identical(tag, ref)
        a, b = load(tag), load(ref)
        checks[tag] = {"env": env, "reference": ref, "files": same,
                       "reproduces_reference": all(v and v["rows_equal_on_reference_columns"]
                                                   for v in same.values()),
                       "case_D_selection_equal": bool(a) and all(
                           key(sel(a.get(m))) == key(sel(b.get(m))) for m in b),
                       "M81": sel(load(tag + "_m81").get(81))}
    out = {"what": __doc__.split("\n\n")[0], "driver": "research/tcpmt_revision/dse_j35/sweep_etm.py",
           "launcher": "scripts/tcpmt_dse_phase1_runs.sh",
           "engine_snapshot": {"path": str(ENGINE), "md5": {
               f.name: hashlib.md5(f.read_bytes()).hexdigest()
               for f in sorted(ENGINE.glob("*")) if f.is_file()} if ENGINE.exists() else None},
           "rules": {
               "switch": {"rule": "V_DS,max * SW_V_DERATING >= stress (relative tolerance 1e-9)",
                          "S1": "V_in/N", "stacked_S2_SN": "max(N-1, 2) V_in/N (authors' rule)",
                          "low_side": "V_in/N", "one_hs_type": "covers the stacked stress",
                          "stress_V_per_N": {n: H.switch_stresses(n, V_IN) for n in (2, 3, 4, 5)},
                          "ladder_node_analysis": "stacked switches block 2 V_in/N at every N "
                                                  "(equal to the rule at N = 2, 3; below it for "
                                                  "N >= 4)",
                          "legacy": "HS V_DS,max >= V_in/N, LS V_DS,max >= V_out"},
               "coss": {"corrected": "per period: N E_OSS,HS(V_in/N) + K [Q_OSS,LS(V_in/N) V_in/N "
                                     "- E_OSS,LS(V_in/N)] + (N-1) [V2 dQ_OSS,HS - dE_OSS,HS], "
                                     "V2 = 2 V_in/N, from V_in/N",
                        "Q_OSS_V": "Q_OSS,table sqrt(V / V_test), V_test = V_DS,max/2; E = Q V/3",
                        "V_test_evidence": {"EPC2014C": "Q_OSS 4 nC typ at V_DS = 20 V",
                                            "EPC2057": "Q_OSS 7.9 nC typ at V_DS = 25 V",
                                            "EPC2090": "Q_OSS 27 nC typ at V_DS = 50 V"},
                        "legacy": "f/2 [N (Q_OSS/V_DSmax) (V_in/N - V_out)^2 + K (Q_OSS/V_DSmax)"
                                  " V_out^2]"},
               "packing": {"cell": "square of the area budget, side sqrt(I_out/J)",
                           "keepout": "50 um between parts, 25 um to the cell edge",
                           "tiers": "N HS dies | K LS dies | K inductors | N-1 flying caps",
                           "dims": "EPC Package(mm); 0603 1.6 x 0.8, 0805 2.0 x 1.25, 1206 3.2 x "
                                   "1.6, 0402 1.0 x 0.5; inductors square of library footprint"}},
           "legacy_reproduction": checks,
           "baseline_caprule_full": {"optimum": None, "per_count": {m: sel(r) for m, r in
                                                                    sorted(base.items())}},
           "runs": {}}
    bf = {m: s for m, s in out["baseline_caprule_full"]["per_count"].items() if s}
    bm = min(bf, key=lambda m: bf[m]["P_total_W"])
    out["baseline_caprule_full"]["optimum"] = {"M": bm, **bf[bm]}
    out["baseline_caprule_full"]["M81"] = sel(load("etm35_p1_swlegacy_m81").get(81))
    for tag, (label, what, env, prev) in RUNS.items():
        out["runs"][tag] = {"label": label, "what": what, "env": env, "previous_step": prev,
                            **run_summary(tag, base, load(prev))}
    # C_OSS magnitude at M = 49
    a49 = arch_of("N=3,K=3,K_A=2")
    f49 = 805170.3343770516
    ref = json.loads((TR / "omitted_losses.json").read_text())["out_of_scope_coss_check"]
    ref49 = [x for x in ref["per_count"] if x["M"] == 49][0]
    cm = {"design_49_cell": {"design": "N3K3K_A2 EPC2014C/EPC2057 805.17 kHz",
                             **coss(a49, "EPC2014C", "EPC2057", f49, 49)},
          "digitized_curves_same_transitions": coss_digitized_49(),
          "omitted_losses_json_M49": ref49}
    for tag in ("etm35_p1b_coss", FINAL):
        s = out["runs"][tag]["M49"]
        if s:
            cm[f"{tag}_M49_selection"] = {"design": f"{s['arch']} {s['hs']}/{s['ls']} "
                                                    f"{s['f_sw_kHz']} kHz",
                                          **coss(arch_of(s["arch"]), s["hs"], s["ls"],
                                                 s["f_sw_kHz"] * 1e3, 49)}
        o = out["runs"][tag]["optimum"]
        if o:
            cm[f"{tag}_optimum"] = {"design": f"M={o['M']} {o['arch']} {o['hs']}/{o['ls']} "
                                              f"{o['f_sw_kHz']} kHz",
                                    **coss(arch_of(o["arch"]), o["hs"], o["ls"],
                                           o["f_sw_kHz"] * 1e3, o["M"])}
    out["coss_M49"] = cm
    out["packing_49_cell"] = packing_49()
    out["packing_49_requirements"] = packing_requirements_49()
    f = out["runs"][FINAL]
    out["tiers_needed_for_b_selections"] = {
        "note": "run (b) (no packing) selections; the area rule assumes 4 tiers (one per class)",
        **{m: tiers_needed(sel_, m) for m, sel_ in out["runs"]["etm35_p1b_coss"]["per_count"].items()
           if sel_}}
    out["final_full_set"] = {
        "tag": FINAL, "env": f["env"], "optimum": f["optimum"],
        "square_grid": f["square_grid"], "M49": f["M49"],
        "M49_feasible_with_packing": f["M49"] is not None,
        "richer_component_budgets": richer_budgets(),
        "M49_stack_changed_vs_caprule_full": f["M49_differs_from_caprule_full"],
        "feasible_counts": f["feasible_counts"]}
    out["packing_undecided_scan"] = undecided_scan(
        [36, 40, 42, 45, 48, 49, 50, 52, 56, 60, 64, 70, 76, 81, 84, 92, 100, 120])
    out["model_issues"] = [
        "C_OSS (legacy): C = Q_OSS/V_DS,max although the table Q_OSS is specified at V_DS,max/2,"
        " and the low side is charged to V_out instead of the switch-node swing V_in/N; at the "
        "49-cell design the term is 1.34 W against 11.2 W (sqrt law) / 10.1 W (digitized curves)"
        " for the hard-switched transitions",
        "area rule: tier sums with zero keep-out; the 49-cell design's two GaN tiers (3 x "
        "EPC2014C, 3 x EPC2057) cannot be placed in its 5.61-5.83 mm2 cell, and the published "
        "0805 flying-capacitor pair (2 x 2.0 x 1.25 mm) does not fit either",
        "capacitor library footprints below the body: GCM21 0805 2.0 mm2 (body 2.5), GRM31 1206 "
        "4.5 mm2 (body 5.12); the area rule then under-counts",
        "switching (overlap) term: R_g,int = 6e-4 Ohm is the continuous model's per-unit-width "
        "value (HVR_FULL_OPT_sizing.R_g_o) used as an absolute gate resistance; the datasheets "
        "give 0.4 Ohm (EPC2014C, EPC2090) and 0.8 Ohm (EPC2057); V_gs_drive is hard-coded 5 V "
        "inside compute_total_loss",
        "authors' stacked-switch stress max(N-1, 2) V_in/N exceeds the ladder's 2 V_in/N for "
        "N >= 4 (36 vs 24 V at N = 4): conservative (with derating 0.9 the 40-V parts sit "
        "exactly at the N = 4 limit)",
    ]
    (TR / "dse_phase1_summary.json").write_text(json.dumps(out, indent=1, default=float))
    brief = {t: {"opt": (v["optimum"]["M"], v["optimum"]["P_total_W"]) if v["optimum"] else None,
                 "sq": v["square_grid"]["P_total_W"], "M81": v["square_grid"]["M81_feasible"],
                 "M49": key(v["M49"]), "M49_P": v["M49"] and v["M49"]["P_total_W"],
                 "N2": v["N2_designs"]} for t, v in out["runs"].items()}
    print(json.dumps({"legacy": {t: c["reproduces_reference"] for t, c in checks.items()},
                      "baseline_opt": out["baseline_caprule_full"]["optimum"]["M"],
                      "runs": brief}, indent=1, default=str))


if __name__ == "__main__":
    main()
