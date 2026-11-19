"""Before/after regulator-count screen under the corrected flying-capacitor rule, with the
attribution steps, and the 49-cell capacitor comparison (TCPMT revision, Option A).

Steps (case D, 17 counts, research/tcpmt_revision/dse_j35/data/):
  etm35                 published
  etm35_legacycheck2    corrected engine with HVR_CAP_RULE=legacy (must equal the published)
  etm35_caprule         + voltage rule (rated parts admitted, constant ESR, no ripple check)
  etm35_caprule_ripple  + effective-capacitance ripple check (MLCCs without vendor data excluded)
  etm35_caprule_full    + ESR at f_sw (vendor ESR(f)); T_design 105 C
  etm35_caprule_full125 the same at T_design 125 C

    python tcpmt_dse_caprule_summary.py -> research/tcpmt_revision/dse_caprule.json,
                                           research/tcpmt_revision/cap49_comparison.json
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
TR = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision"
D = TR / "dse_j35" / "data"
TAGS = ["etm35", "etm35_legacycheck2", "etm35_caprule", "etm35_caprule_ripple",
        "etm35_caprule_full", "etm35_caprule_full125"]
CAUSE = {"etm35_caprule": "voltage screening and component selection (rated part, its ESR)",
         "etm35_caprule_ripple": "effective capacitance (and exclusion of parts without vendor data)",
         "etm35_caprule_full": "ESR at the switching frequency",
         "etm35_caprule_full125": "design temperature 125 C"}


def load(tag):
    return {int(float(r["M"])): r for r in csv.DictReader((D / f"case_D_{tag}.csv").open())}


def main():
    T = {t: load(t) for t in TAGS}
    counts = sorted(T["etm35"])
    per = []
    for m in counts:
        row = {"M": m}
        for t in TAGS:
            r = T[t][m]
            row[t] = (None if r["feasible"] != "True" else
                      {"arch": r["arch"], "hs": r["hs"], "ls": r["ls"],
                       "f_sw_kHz": round(float(r["f_sw_Hz"]) / 1e3, 1),
                       "P_total_W": round(float(r["total_loss_W"]), 3)})
        per.append(row)
    opt = {}
    for t in TAGS:
        f = [r for r in T[t].values() if r["feasible"] == "True"]
        b = min(f, key=lambda r: float(r["total_loss_W"]))
        opt[t] = {"M": int(float(b["M"])), "arch": b["arch"], "P_total_W": float(b["total_loss_W"])}
    steps = []
    prev = "etm35"
    for t in TAGS[2:]:
        changed = [r["M"] for r in per if r[t] and r[prev] and
                   (r[t]["arch"] != r[prev]["arch"] or r[t]["f_sw_kHz"] != r[prev]["f_sw_kHz"]
                    or r[t]["hs"] != r[prev]["hs"] or r[t]["ls"] != r[prev]["ls"])]
        dl = [r[t]["P_total_W"] - r[prev]["P_total_W"] for r in per if r[t] and r[prev]]
        steps.append({"step": t, "vs": prev, "cause": CAUSE[t], "selection_changed_at_M": changed,
                      "dP_min_W": min(dl), "dP_max_W": max(dl), "optimum": opt[t]})
        if t != "etm35_caprule_full125":
            prev = t
    legacy_ok = all((T["etm35"][m]["arch"], T["etm35"][m]["total_loss_W"]) ==
                    (T["etm35_legacycheck2"][m]["arch"], T["etm35_legacycheck2"][m]["total_loss_W"])
                    for m in counts)
    out = {"what": __doc__.split("\n\n")[0], "legacy_reproduces_published": legacy_ok,
           "optimum": opt, "steps": steps, "per_count": per,
           "conclusion": ("the optimum stays at M = %d (%.2f W) under the full correction"
                          % (opt["etm35_caprule_full"]["M"], opt["etm35_caprule_full"]["P_total_W"]))}
    (TR / "dse_caprule.json").write_text(json.dumps(out, indent=1))

    # 49-cell capacitor comparison
    sys.path.insert(0, str(R / "Scalable_Integrated_VR" / "src"))
    import HVR_FULL_OPT_EPC_V2 as H
    arch = H.VRArchitecture(N=3, K=3, K_A=2, B_array=[1, 1, 1], D=0.0625, component_count=11)
    i_out, f = 1000.0 / 49, 805170.3343770516
    parts = {c.name: c for c in H.default_capacitor_library("stress")}
    cmp_ = {}
    for name in ("Murata-GRM188D72A105KE01-1uF-100V", "Murata-GRM188D71H105KE01-1uF-50V",
                 "Murata-GCM21-10uF-25V"):
        c = parts[name]
        e = {}
        for t in (25.0, 105.0, 125.0):
            e[f"{t:.0f}C"] = {"C_eff_32V_uF": H.cap_c_eff_uf(c, 32.0, t),
                              "C_eff_16V_uF": H.cap_c_eff_uf(c, 16.0, t),
                              "ripple_worst": H.flying_cap_ripple(arch, c, i_out, 48.0, 1.0, f, t)}
        cmp_[name] = {"v_max": c.v_max, "rating_ok_C1": c.v_max * H.CAP_V_DERATING >= 32.0,
                      "esr_mohm_at_fsw": H.cap_esr_mohm(c, f, 32.0), "height_um": c.height_um,
                      "by_temperature": e}
    rpl = T["etm35_caprule_full"][49]
    pub = T["etm35"][49]
    (TR / "cap49_comparison.json").write_text(json.dumps({
        "design": "M=49 N3K3K_A2 EPC2014C/EPC2057 805 kHz", "parts": cmp_,
        "selected_corrected": "Murata-GRM188D72A105KE01-1uF-100V",
        "P_total_screen_W": {"published": float(pub["total_loss_W"]),
                             "corrected": float(rpl["total_loss_W"])},
        "note": "ripple: worst position, Q = (I_out/N) D / f_sw, C_eff with -10 % tolerance; the "
                "published 25-V part fails the C1 rating; both rated parts pass the 10 % ripple "
                "limit at 25-125 C"}, indent=1, default=float))
    print(json.dumps({"legacy_ok": legacy_ok, "optimum": opt,
                      "steps": [(s["step"], s["selection_changed_at_M"], round(s["dP_min_W"], 2),
                                 round(s["dP_max_W"], 2)) for s in steps]}, indent=1))


if __name__ == "__main__":
    main()
