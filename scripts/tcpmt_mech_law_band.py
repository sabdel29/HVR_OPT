"""Finding 1 -- a self-consistent production law and the joint response as a law band.

For every law of solder.band_laws (configs/tcpmt_mech/mechanics_revision.yaml) the six tier
joints (cooling A and B, Z1 / Z2 / Z3) are solved with the v2 local model (global cut-boundary
kinematics, 3-s ramps, 300-s dwells; tcpmt_mech_submodel). For a Garofalo law the Norton
surrogate's stress window is then re-read from those solves (5-95 % of the core von Mises
stress, weighted where the cycle's inelastic strain is deposited) and the card refitted, until
the window endpoints move by less than 10 % and the responses by less than 1 % -- the card is
then accurate where the response is produced. A measured-Norton law has no window to iterate
(its card is the per-temperature fit of the data); its visited window is recorded.

Outputs
  research/tcpmt_revision/solder_law_cards.json   converged window and card hash per law (the
                                                  production harness reads the production
                                                  law's window from here)
  research/tcpmt_revision/solder_law_band.json    per joint: the response under every law, the
                                                  band (min..max), its spread relative to the
                                                  production law, and the ranking per law --
                                                  read by tcpmt_uncertainty.py

    python tcpmt_mech_law_band.py --run [--laws a,b] [--joints A_Z1,...]
    python tcpmt_mech_law_band.py --summarize
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcpmt_mech_laws as LAW                                       # noqa: E402
import tcpmt_mech_submodel as SUB                                   # noqa: E402
import tcpmt_mech_kinematics as KIN                                 # noqa: E402

import tcpmt_mech_production as MP                                 # noqa: E402

#: TCPMT round 3 (campaign): the joints are the critical joints of the COMPARED cases of the
#: local model's state -- the production state (implemented decoupling, HV_SDEC) of the design
#: in force, Z1/Z2/Z3 x cooling A/B (tcpmt_cases; site kinematics from the case files,
#: tcpmt_mech_production). TCPMT_LOCAL_STATE=S0|S1 solves a reference state's cases instead
#: (own study, own output names), =round2 the round-2 field cases of the merged branch.
STATE = MP.LOCAL_STATE
_SFX = "" if STATE == "SDEC" else f"_{STATE}"
STUDY = "lawband" + _SFX
TR = LAW.TR
BAND = TR / f"solder_law_band{_SFX}.json"
CRIT = TR / f"solder_critical_v2{_SFX}.json"
#: the converged windows: the production card's file for the production state only (the
#: production harness reads it); another state records its own and never moves the card
CARDS_OUT = LAW.CARDS if STATE == "SDEC" else TR / f"solder_law_cards{_SFX}.json"
#: tier -> arch -> kinematics case; the coupled land-side Z3 cases when their kinematics exist
ROUND2_TIERS = {"A": {"Z1": "Z1_S0", "Z2": "Z2_S0", "Z3": ("A_Z3land", "A_Z3")},
                "B": {"Z1": "B_Z1", "Z2": "B_Z2", "Z3": ("B_Z3land", "B_Z3")}}
TIERS = ROUND2_TIERS if STATE == "round2" else {
    t: {a: MP.label(STATE, t, a) for a in ("Z1", "Z2", "Z3")} for t in ("A", "B")}


def joint_case(tier, arch):
    c = TIERS[tier][arch]
    for k in (c if isinstance(c, tuple) else (c,)):
        if KIN.load_kinematics(k):
            return k
    return None


def joint_site(case):
    """The joint to solve: the critical site of the v2 critical-joint check when that study
    has confirmed one for this case, else the maximum-|du_xy| BGA site."""
    kin = KIN.load_kinematics(case)
    crit = (json.loads(CRIT.read_text()).get("cases", {}).get(case, {})
            .get("max_response_site") if CRIT.is_file() else None)
    cand = KIN.expand_sites(kin["interconnects"]["bga"]["candidates"])
    if crit:
        for k in cand:
            if abs(k["x_mm"] - crit["x_mm"]) < 1e-6 and abs(k["y_mm"] - crit["y_mm"]) < 1e-6:
                return k, "v2 critical-joint check"
    return max(cand, key=lambda k: k["du_xy_um"]), "maximum |du_xy|"


def joints(only=None):
    out = []
    for t in ("A", "B"):
        for a in ("Z1", "Z2", "Z3"):
            lab = f"{t}_{a}"
            if only and lab not in only:
                continue
            case = joint_case(t, a)
            if case is None:
                print(f"  {lab}: no kinematics, skipped", flush=True)
                continue
            k, basis = joint_site(case)
            out.append((lab, case, k, basis))
    return out


def tasks_for(law, win, label, js, **kw):
    return [dict(study=STUDY, tag=f"{lab}_{label}", kin=k, law=law, window=win,
                 meta={"joint": lab, "case": case, "site_basis": basis, "law": law,
                       "label": label}, **kw) for lab, case, k, basis in js]


def iterate(law, js, execute=True):
    """Window iteration of one law; returns the iteration log."""
    lc = LAW.law_cfg(law)
    w = LAW.solder_cfg()["window"]
    win, status = LAW.stored_window(law)
    its, prev = [], None
    n_it = int(w["max_iterations"]) if lc["form"] == "garofalo" else 1
    for k in range(n_it):
        lab = f"{law}_it{k}"
        tasks = tasks_for(law, win, lab, js)
        recs = SUB.run_tasks(tasks) if execute else {
            t["tag"]: r for t in tasks if (r := SUB.load_records(STUDY).get(t["tag"]))}
        vals = {t["meta"]["joint"]: (recs.get(t["tag"]) or {}).get("d_peeq_per_cycle")
                for t in tasks}
        obs = LAW.window_from_records([recs[t["tag"]] for t in tasks if t["tag"] in recs])
        ok = None not in vals.values() and set(obs) == {"hot", "cold"}
        dw = (max(abs(math.log(obs[p][i] / win[p][i])) for p in ("hot", "cold")
                  for i in (0, 1)) if ok else None)
        dv = (max(abs(vals[j] / prev[j] - 1) for j in vals) if ok and prev else None)
        its.append({"iteration": k, "label": lab, "window_fit_MPa": win,
                    "window_observed_MPa": obs, "window_change_max_log": dw,
                    "response_change_max_rel": dv, "responses": vals,
                    "errors": {t["meta"]["joint"]: (recs.get(t["tag"]) or {}).get("error")
                               for t in tasks},
                    "card_sha": LAW.card_sha(LAW.card(law, win)[0])})
        if not ok or lc["form"] != "garofalo":
            break
        if dw < math.log(1 + float(w["tol_window_rel"])) and dv is not None \
                and dv < float(w["tol_response_rel"]):
            break
        prev, win = vals, {p: list(v) for p, v in obs.items()}
    return its


def store_cards(logs, js):
    d = json.loads(CARDS_OUT.read_text()) if CARDS_OUT.is_file() else {}
    d["what"] = ("converged Norton-surrogate windows of the local solder laws (v2 model: "
                 "global cut-boundary kinematics, ramped loading); written by "
                 "scripts/tcpmt_mech_law_band.py")
    d.setdefault("laws", {})
    w = LAW.solder_cfg()["window"]
    for law, its in logs.items():
        last = its[-1]
        conv = (LAW.law_cfg(law)["form"] != "garofalo") or (
            last["window_change_max_log"] is not None
            and last["window_change_max_log"] < math.log(1 + float(w["tol_window_rel"]))
            and (last["response_change_max_rel"] or 1.0) < float(w["tol_response_rel"]))
        d["laws"][law] = {"window_MPa": last["window_fit_MPa"], "converged": bool(conv),
                          "n_iterations": len(its), "card_sha": last["card_sha"],
                          "visited_window_last_MPa": last["window_observed_MPa"],
                          "visited_T_C": sorted(round(SUB.site_temperature(k), 2)
                                                for _, _, k, _ in js),
                          "weighting": w["weighting"], "quantiles": w["quantiles"],
                          "joints": [lab for lab, *_ in js],
                          "joint_cases": {lab: case for lab, case, *_ in js},
                          "state": STATE}
    CARDS_OUT.write_text(json.dumps(d, indent=1, default=float) + "\n")


def ranking(v):
    if None in v.values():
        return None
    return " < ".join(sorted(v, key=v.get))


def _kin_meta(case):
    k = KIN.load_kinematics(case) or {}
    return {"case_file": k.get("case_file"), "case_sha1": k.get("case_sha1"),
            "inputs_sha1": k.get("inputs_sha1") or {}}


def critical_check(js):
    """The v2 critical-joint check behind the joints, when it covers every joint's case:
    {file, per joint: moved off the maximum-du site?}; None otherwise."""
    if not CRIT.is_file():
        return None
    cases = json.loads(CRIT.read_text()).get("cases", {})
    if not all((cases.get(case) or {}).get("max_response_site") for _l, case, *_ in js):
        return None
    return {"file": MP.rel(CRIT), "moved_off_max_du": {
        lab: basis == "v2 critical-joint check" and not cases[case].get("critical_is_max_du")
        for lab, case, _k, basis in js}}


def summarize(logs, js):
    prod = LAW.solder_cfg()["production_law"]
    final = {law: its[-1]["responses"] for law, its in logs.items()}
    meta = {case: _kin_meta(case) for _l, case, *_ in js}
    out = {"what": "local joint response as a band over the configured solder laws "
                   "(finding 1); v2 local model",
           "state": STATE,
           "production_law": prod, "band_laws": list(logs),
           "model": {k: SUB.lcfg()[k] for k in ("bc_mode", "ramp_s", "dwell_s", "n_cycles",
                                                 "element", "level")},
           "joints": {lab: {"case": case, "x_mm": k["x_mm"], "y_mm": k["y_mm"],
                            "T_C": SUB.site_temperature(k), "du_xy_um": k["du_xy_um"],
                            "du_z_um": k["du_z_um"], "du_def_xy_um": k.get("du_def_xy_um"),
                            "site_basis": basis, "case_file": meta[case]["case_file"],
                            "case_sha1": meta[case]["case_sha1"]}
                      for lab, case, k, basis in js},
           "inputs_sha1": {p: h for m in meta.values() for p, h in m["inputs_sha1"].items()},
           "iterations": logs, "responses": final, "band": {}, "rankings": {}}
    cc = critical_check(js)
    if cc is not None:                 # pass 2: the joints the critical-joint check confirmed
        out["critical_check"] = cc
        out["inputs_sha1"][str(CRIT.resolve())] = MP.sha1(CRIT)
    for lab, *_ in js:
        v = {law: final[law].get(lab) for law in final}
        if None in v.values() or not v.get(prod):
            out["band"][lab] = {"values": v, "complete": False}
            continue
        lo, hi = min(v.values()), max(v.values())
        out["band"][lab] = {"values": v, "min": lo, "max": hi, "production": v[prod],
                            "spread_rel_to_production": (hi - lo) / v[prod],
                            "U_law_rel": max(hi - v[prod], v[prod] - lo) / v[prod],
                            "ratio_to_production": {k: x / v[prod] for k, x in v.items()},
                            "law_of_min": min(v, key=v.get), "law_of_max": max(v, key=v.get),
                            "complete": True}
    for law, v in final.items():
        out["rankings"][law] = {t: ranking({a: v.get(f"{t}_{a}") for a in ("Z1", "Z2", "Z3")
                                            if f"{t}_{a}" in v}) for t in ("A", "B")}
    r0 = out["rankings"].get(prod, {})
    out["rankings_hold_across_laws"] = all(r == r0 for r in out["rankings"].values())
    out["note"] = ("model-form band: not added to the numerical U; a resolved comparison whose "
                   "ranking differs between laws is CONDITIONAL on the law "
                   "(tcpmt_uncertainty.py)")
    BAND.write_text(json.dumps(out, indent=1, default=float) + "\n")
    return out


def main():
    laws = LAW.solder_cfg()["band_laws"]
    only = None
    if "--laws" in sys.argv:
        laws = sys.argv[sys.argv.index("--laws") + 1].split(",")
    if "--joints" in sys.argv:
        only = sys.argv[sys.argv.index("--joints") + 1].split(",")
    js = joints(only)
    execute = "--run" in sys.argv
    logs = {law: iterate(law, js, execute) for law in laws}
    store_cards(logs, js)
    s = summarize(logs, js)
    print(json.dumps({"responses": s["responses"], "rankings": s["rankings"],
                      "hold": s["rankings_hold_across_laws"]}, indent=1, default=float))
    for law, its in logs.items():
        for it in its:
            print(law, it["iteration"], it["window_fit_MPa"], it["window_observed_MPa"],
                  it["response_change_max_rel"])


if __name__ == "__main__":
    main()
