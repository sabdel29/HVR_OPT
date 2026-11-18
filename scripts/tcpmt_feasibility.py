"""Component- and material-temperature feasibility of every compared case (TCPMT review MC5).

For each case, from its CONVERGED nodal field on the production mesh (scratch/fields), the
maximum and mean temperature of every tier and material region, inside the cell footprints
where the region holds devices. The power-device junction is bounded from the tier maximum
by the device's own junction-to-case resistance at its dissipated power (conservative: the
homogenised tier temperature is a die-average, the junction sits on one face).

Limits (declared, with sources):
  GaN FETs EPC2014C / EPC2057   T_J <= 150 C (datasheets, Maximum Ratings); the R_DS(on)
                                temperature coefficients are fitted over 25-125 C
  solder law (SAC305)           calibrated <= 125 C; solidus 217 C
  MLCC flying / output caps     X7R/X7S class <= 125 C (declared class of the library parts)
  build-up dielectric (RDL)     Tg ~ 150 C (ABF-class film, declared)
  encapsulant / underfill       Tg ~ 150 C (declared)
  board laminate (high-Tg FR-4) Tg ~ 170 C (declared)

    python tcpmt_feasibility.py      -> research/tcpmt_revision/feasibility.json
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np  # noqa: E402

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import final_closure_physical_etm as E                              # noqa: E402
import final_closure_ledger as FL                                   # noqa: E402

FIELDS = Path(os.environ.get("HVR_FIELDS",
                             "/home/beams0/SABDELZAHER/ETM_project/scratch/fields"))
SENS = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "final_closure" / "sensitivity"
OUT = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision" / "feasibility.json"

CASES = {  # label -> (arch, field dir, case file)
    "A_Z1": ("Z1", "etm_Z1_HV_S0_r21", E.case_path("Z1", "HV_S0")),
    "A_Z2": ("Z2", "etm_Z2_HV_S0_r21", E.case_path("Z2", "HV_S0")),
    "A_Z3": ("Z3", "etm_Z3_HV_S0__z3_top_only", SENS / "etm_Z3_HV_S0__z3_top_only.json"),
    "B_Z1": ("Z1", "etm_Z1_HV_S0__z1_bottom_plate_tim",
             SENS / "etm_Z1_HV_S0__z1_bottom_plate_tim.json"),
    "B_Z2": ("Z2", "etm_Z2_HV_S0__z2_cooled_tim", SENS / "etm_Z2_HV_S0__z2_cooled_tim.json"),
    "B_Z3": ("Z3", "etm_Z3_HV_S0__z3_plate_tim", SENS / "etm_Z3_HV_S0__z3_plate_tim.json"),
    "I_Z3": ("Z3", "etm_Z3_HV_S0_r21", E.case_path("Z3", "HV_S0")),
    "S1_Z1": ("Z1", "etm_Z1_HV_S1_r21", E.case_path("Z1", "HV_S1")),
    "S1_Z2": ("Z2", "etm_Z2_HV_S1_r21", E.case_path("Z2", "HV_S1")),
}
#: datasheet values (review_work/dl_epc): T_J max, R_thetaJC (K/W), die (mm)
DEVICES = {"hs": {"part": "EPC2014C", "Tj_max_C": 150.0, "R_jc_K_W": 3.6,
                  "R_jb_K_W": 9.3, "die_mm": [1.7, 1.1], "V_DS_V": 40.0, "I_D_A": 10.0,
                  "per_cell": 3},
           "ls": {"part": "EPC2057", "Tj_max_C": 150.0, "R_jc_K_W": 2.3,
                  "R_jb_K_W": 7.0, "die_mm": [1.5, 1.2], "V_DS_V": 50.0, "I_D_A": 9.6,
                  "per_cell": 3}}
LIMITS = {"gan_Tj_C": 150.0, "ron_fit_max_C": 125.0, "solder_cal_C": 125.0,
          "solder_solidus_C": 217.0, "mlcc_C": 125.0, "inductor_C": 125.0,
          "buildup_Tg_C": 150.0, "encapsulant_Tg_C": 150.0, "board_Tg_C": 170.0}


def node_stats(m, Tn, ids):
    if len(ids) == 0:
        return None
    nodes = np.unique(m.elems[ids - 1].ravel())
    t = Tn[nodes - 1]
    return {"max_C": float(np.nanmax(t)), "mean_C": float(np.nanmean(t)),
            "n_elems": int(len(ids))}


def device_power(case, key):
    """Tier loss of one device kind (sum of ledger rows deposited in that tier)."""
    lay = FL.LAYERS[case["arch"]][key]
    p = sum(r["P_w"] for r in case["ledger_rows"] if r["deposit_layer"] == lay)
    return p


def evaluate(label, arch, field, case_file):
    import production_et as PE
    case = json.loads(Path(case_file).read_text())
    m, mats, st, tiles, info = E.build(arch, E.PRODUCTION_H_XY, E.PRODUCTION_REFINE)
    Tn = PE.ccxio.read_frd(FIELDS / field / "thermal_converged.frd")["NDTEMP"][
        1:m.n_nodes + 1, 0]
    if abs(float(np.nanmax(Tn)) - case["thermal"]["T_max_C"]) > 1e-3:
        raise RuntimeError(f"{field} is not the converged field of {case_file}")
    lay = FL.LAYERS[arch]
    out = {"arch": arch, "field": field, "case": Path(case_file).name,
           "T_max_C": case["thermal"]["T_max_C"], "regions": {}}
    names = [L.name for L in m.layers]
    for key in ("hs", "ls", "caps", "ind", "attach", "lv", "die", "bga", "pads", "tsv"):
        if key not in lay:
            continue
        layers = lay[key] if isinstance(lay[key], list) else [lay[key]]
        ids_all = np.concatenate([PE._layer_elems(m, x) for x in layers])
        ids_in = E._region_elems(m, layers, True, tiles)
        out["regions"][key] = {"layers": layers, "all": node_stats(m, Tn, ids_all),
                               "in_cells": node_stats(m, Tn, ids_in)}
    rdl = lay["rdl"]
    out["regions"]["rdl"] = {"layers": rdl, "all": node_stats(
        m, Tn, np.concatenate([PE._layer_elems(m, x) for x in rdl]))}
    # encapsulant: converter-tier elements outside the cell footprints
    conv = [lay[k] for k in ("hs", "ls", "caps", "ind")]
    ids_c = np.concatenate([PE._layer_elems(m, x) for x in conv])
    ids_in = E._region_elems(m, conv, True, tiles)
    enc = np.setdiff1d(ids_c, ids_in)
    out["regions"]["encapsulant"] = {"layers": conv, "all": node_stats(m, Tn, enc)}
    board = [n for n in names if n.startswith("board") or n.startswith("pcb")]
    if board:
        ids_b = np.concatenate([PE._layer_elems(m, x) for x in board])
        out["regions"]["board"] = {"layers": board, "all": node_stats(m, Tn, ids_b)}
    # junction bound per device kind
    for key, dev in DEVICES.items():
        p_tier = device_power(case, key)
        p_dev = p_tier / (FL.N_VR * dev["per_cell"])
        t_tier = out["regions"][key]["in_cells"]["max_C"]
        out["regions"][key]["device"] = {
            **dev, "P_tier_W": p_tier, "P_device_W": p_dev,
            "Tj_bound_C": t_tier + p_dev * dev["R_jc_K_W"],
            "margin_K": dev["Tj_max_C"] - (t_tier + p_dev * dev["R_jc_K_W"])}
    crit = case.get("mechanics", {}).get("joint_search", {})
    ranked = crit.get("ranked") or []
    out["joints"] = {"T_critical_C": crit.get("critical", {}).get("T_C") if crit else None,
                     "T_hottest_C": max((r["T_C"] for r in ranked), default=None)}
    out["checks"] = checks(out)
    print(label, {k: round(v["device"]["Tj_bound_C"], 1) for k, v in out["regions"].items()
                  if "device" in v}, flush=True)
    return out


def checks(o):
    rg = o["regions"]
    c = {}
    tj = max(rg["hs"]["device"]["Tj_bound_C"], rg["ls"]["device"]["Tj_bound_C"])
    c["gan_Tj"] = {"value_C": tj, "limit_C": LIMITS["gan_Tj_C"], "ok": tj <= LIMITS["gan_Tj_C"]}
    c["ron_fit"] = {"value_C": max(rg["hs"]["in_cells"]["max_C"], rg["ls"]["in_cells"]["max_C"]),
                    "limit_C": LIMITS["ron_fit_max_C"]}
    c["ron_fit"]["ok"] = c["ron_fit"]["value_C"] <= LIMITS["ron_fit_max_C"]
    t_cap = rg["caps"]["in_cells"]["max_C"]
    t_ind = rg["ind"]["in_cells"]["max_C"]
    c["mlcc"] = {"value_C": max(t_cap, t_ind), "limit_C": LIMITS["mlcc_C"],
                 "ok": max(t_cap, t_ind) <= LIMITS["mlcc_C"]}
    c["inductor"] = {"value_C": t_ind, "limit_C": LIMITS["inductor_C"],
                     "ok": t_ind <= LIMITS["inductor_C"]}
    tj_s = o["joints"]["T_hottest_C"]
    c["solder_cal"] = {"value_C": o["joints"]["T_critical_C"], "limit_C": LIMITS["solder_cal_C"]}
    c["solder_cal"]["ok"] = (o["joints"]["T_critical_C"] or 0) <= LIMITS["solder_cal_C"]
    c["solder_solidus"] = {"value_C": tj_s, "limit_C": LIMITS["solder_solidus_C"],
                           "ok": (tj_s or 0) <= LIMITS["solder_solidus_C"]}
    c["buildup"] = {"value_C": rg["rdl"]["all"]["max_C"], "limit_C": LIMITS["buildup_Tg_C"]}
    c["buildup"]["ok"] = c["buildup"]["value_C"] <= LIMITS["buildup_Tg_C"]
    c["encapsulant"] = {"value_C": rg["encapsulant"]["all"]["max_C"],
                        "limit_C": LIMITS["encapsulant_Tg_C"]}
    c["encapsulant"]["ok"] = c["encapsulant"]["value_C"] <= LIMITS["encapsulant_Tg_C"]
    if "board" in rg:
        c["board"] = {"value_C": rg["board"]["all"]["max_C"], "limit_C": LIMITS["board_Tg_C"]}
        c["board"]["ok"] = c["board"]["value_C"] <= LIMITS["board_Tg_C"]
    c["all_ok"] = all(v["ok"] for v in c.values() if isinstance(v, dict))
    return c


def main(labels=None):
    res = json.loads(OUT.read_text()) if OUT.is_file() else {}
    res.setdefault("limits", LIMITS)
    res.setdefault("devices", DEVICES)
    res.setdefault("cases", {})
    for label, (arch, field, cf) in CASES.items():
        if labels and label not in labels:
            continue
        res["cases"][label] = evaluate(label, arch, field, cf)
        OUT.write_text(json.dumps(res, indent=1, default=float))
    return res


if __name__ == "__main__":
    main(sys.argv[1:] or None)
