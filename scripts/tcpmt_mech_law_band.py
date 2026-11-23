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
import tcpmt_mech_critical as CR                                   # noqa: E402

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


def crit_file(law=None):
    """The critical-joint check of a law (tcpmt_mech_critical: the maximum over the lattice
    under that law at its stored window); the production law's file by default."""
    law = law or LAW.solder_cfg()["production_law"]
    f = CR.out_for(law)
    return f if STATE != "round2" or law == LAW.solder_cfg()["production_law"] else CRIT


def _find_site(case, x, y):
    """The kinematics of site (x, y) of a case: a stored candidate, else a lattice site."""
    kin = KIN.load_kinematics(case)
    pool = KIN.expand_sites(kin["interconnects"]["bga"]["candidates"])
    pool += (MP.load_lattice(case) or []) if STATE != "round2" else []
    for k in pool:
        if abs(k["x_mm"] - x) < 1e-6 and abs(k["y_mm"] - y) < 1e-6:
            return k
    return None


def joint_site(case, law=None):
    """The joint to solve under a law: the maximum-response site of THAT law's critical-joint
    check when it covers this case, else the production law's, else the maximum-|du_xy| BGA
    site (TCPMT round 3: the reported response is the maximum over the lattice under every
    law of the band, not the production law's site re-solved)."""
    kin = KIN.load_kinematics(case)
    prod = LAW.solder_cfg()["production_law"]
    for lw, basis in ((law or prod, "v2 critical-joint check"),
                      (prod, "v2 critical-joint check (production law's site)")):
        f = crit_file(lw)
        crit = (json.loads(f.read_text()).get("cases", {}).get(case, {})
                .get("max_response_site") if f.is_file() else None)
        if crit:
            k = _find_site(case, crit["x_mm"], crit["y_mm"])
            if k is not None:
                return k, basis
    cand = KIN.expand_sites(kin["interconnects"]["bga"]["candidates"])
    return max(cand, key=lambda k: k["du_xy_um"]), "maximum |du_xy|"


def joints(only=None, law=None):
    """[(label, case, kinematics, basis)] of the six joints under a law (production default)."""
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
            k, basis = joint_site(case, law)
            out.append((lab, case, k, basis))
    return out


def _same_sites(js, sites):
    return all((sites.get(lab) or {}).get("case") == case
               and abs((sites.get(lab) or {}).get("x_mm", 1e9) - k["x_mm"]) < 1e-6
               and abs((sites.get(lab) or {}).get("y_mm", 1e9) - k["y_mm"]) < 1e-6
               for lab, case, k, _b in js)


def previous_final(law, js):
    """The previous pass's last iteration of this law when it solved these very sites (the
    band file as it is): its card and responses let an unchanged law converge at once instead
    of moving its window again (a re-run of the band is then idempotent)."""
    if not BAND.is_file():
        return None
    b = json.loads(BAND.read_text())
    its = (b.get("iterations") or {}).get(law) or []
    sites = (b.get("joints_by_law") or {}).get(law) or b.get("joints") or {}
    if not its or not _same_sites(js, sites):
        return None
    return its[-1]


def critical_responses(law, js, sha):
    """{joint: response} of the law's critical-joint check at these sites when it was solved
    with card `sha`; None otherwise."""
    f = crit_file(law)
    if not f.is_file():
        return None
    c = json.loads(f.read_text())
    if c.get("card_sha") != sha:
        return None
    out = {}
    for lab, case, k, _b in js:
        rows = ((c.get("cases") or {}).get(case) or {}).get("candidates") or []
        hit = next((r for r in rows if r.get("d_eps") is not None
                    and abs(r["x_mm"] - k["x_mm"]) < 1e-6 and abs(r["y_mm"] - k["y_mm"]) < 1e-6
                    and abs(r["du_xy_um"] - k["du_xy_um"]) < 1e-6), None)
        if hit is None:
            return None
        out[lab] = hit["d_eps"]
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
    # an unchanged card: the responses already solved at it at these very sites -- the law's
    # critical-joint check (same card, same kinematics: the same deck) or the previous pass --
    # are this iteration's comparison, so a law whose fitted window reproduces the window its
    # joints visit (within tol_window_rel) converges at once instead of moving its card again
    sha0 = LAW.card_sha(LAW.card(law, win)[0])
    prev = critical_responses(law, js, sha0)
    last = previous_final(law, js)
    if prev is None and last and last.get("card_sha") == sha0:
        prev = last.get("responses")
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
        # the next fit window: the one the joints visited; from the third fit on under-relaxed
        # (geometric mean with the window just fitted), which damps the two-cycle oscillation a
        # Garofalo law with a strongly stress-dependent exponent shows (Xiao and Armstrong:
        # the cold window alternated by ~10 % and the responses by ~3 % for six fits)
        relax = float(w.get("relaxation", 0.5)) if k >= 1 else 1.0
        prev = vals
        win = {p: [math.exp(relax * math.log(obs[p][i]) + (1 - relax) * math.log(win[p][i]))
                   for i in (0, 1)] for p in obs}
    return its


def store_cards(logs, jsd):
    """jsd: {law: joints of that law}."""
    d = json.loads(CARDS_OUT.read_text()) if CARDS_OUT.is_file() else {}
    d["what"] = ("converged Norton-surrogate windows of the local solder laws (v2 model: "
                 "global cut-boundary kinematics, ramped loading); written by "
                 "scripts/tcpmt_mech_law_band.py")
    d.setdefault("laws", {})
    w = LAW.solder_cfg()["window"]
    for law, its in logs.items():
        js = jsd[law]
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
                          "joint_sites_mm": {lab: [k["x_mm"], k["y_mm"]]
                                             for lab, _c, k, _b in js},
                          "state": STATE}
    CARDS_OUT.write_text(json.dumps(d, indent=1, default=float) + "\n")


def verify(law, its, js):
    """The maximum at the law's FINAL card. The critical-joint check of the law solved its
    sites at the window stored when it ran; when the window iteration has moved the card since,
    every site of the check within local.critical.verify_near_rel of the case's maximum is
    re-solved at the final card (a farther site cannot overtake: a window move within the
    iteration's tolerances changes a response by about 1 %). Returns ({joint: record},
    joints to use, all confirmed)."""
    f = crit_file(law)
    crit = json.loads(f.read_text()) if f.is_file() else {}
    last = its[-1]
    out, new_js, ok = {}, [], True
    near = float(SUB.lcfg()["critical"]["verify_near_rel"])
    for lab, case, k, basis in js:
        cc = (crit.get("cases") or {}).get(case) or {}
        rows = [r for r in cc.get("candidates") or [] if r.get("d_eps") is not None]
        rec = {"critical_card_sha": crit.get("card_sha"), "final_card_sha": last["card_sha"],
               "near_rel": near}
        if not rows:
            rec.update({"status": "no critical-joint check of this law", "confirmed": None})
            out[lab] = rec
            new_js.append((lab, case, k, basis))
            continue
        if crit.get("card_sha") == last["card_sha"]:
            rec.update({"status": "the check was solved at the final card", "n_resolved": 0,
                        "confirmed": True})
            out[lab] = rec
            new_js.append((lab, case, k, basis))
            continue
        rmax = max(r["d_eps"] for r in rows)
        pool = [r for r in rows if r["d_eps"] >= (1.0 - near) * rmax]
        ks = [x for x in (_find_site(case, r["x_mm"], r["y_mm"]) for r in pool) if x]
        ts = [dict(study=STUDY, tag=f"verify_{law}_{CR.tag(case, x)}", kin=x, law=law,
                   window=last["window_fit_MPa"],
                   meta={"joint": lab, "case": case, "law": law, "label": "verify"})
              for x in ks]
        recs = SUB.run_tasks(ts)
        vals = [(x, (recs.get(t["tag"]) or {}).get("d_peeq_per_cycle")) for x, t in zip(ks, ts)]
        vals = [(x, v) for x, v in vals if v is not None]
        if not vals:
            rec.update({"status": "re-solve failed", "confirmed": None})
            ok = False
            out[lab] = rec
            new_js.append((lab, case, k, basis))
            continue
        bx, bv = max(vals, key=lambda xv: xv[1])
        same = abs(bx["x_mm"] - k["x_mm"]) < 1e-6 and abs(bx["y_mm"] - k["y_mm"]) < 1e-6
        rec.update({"status": "re-solved at the final card", "n_resolved": len(vals),
                    "max_site_mm": [bx["x_mm"], bx["y_mm"]], "max_d_eps": bv,
                    "joint_site_mm": [k["x_mm"], k["y_mm"]], "confirmed": same})
        out[lab] = rec
        if same:
            new_js.append((lab, case, k, basis))
        else:
            ok = False
            new_js.append((lab, case, bx, "v2 critical-joint check, re-verified at the "
                                          "final card"))
    return out, new_js, ok


def ranking(v):
    if None in v.values():
        return None
    return " < ".join(sorted(v, key=v.get))


def _kin_meta(case):
    k = KIN.load_kinematics(case) or {}
    return {"case_file": k.get("case_file"), "case_sha1": k.get("case_sha1"),
            "inputs_sha1": k.get("inputs_sha1") or {}}


def critical_check(jsd):
    """The critical-joint checks behind the joints, when they cover every joint's case:
    {files, per law and joint: moved off the maximum-du site?}; None otherwise."""
    prod = LAW.solder_cfg()["production_law"]
    out = {"files": {}, "moved_off_max_du": {}, "moved_off_max_du_by_law": {}}
    for law, js in jsd.items():
        f = crit_file(law)
        if not f.is_file():
            if law == prod:
                return None
            continue
        cases = json.loads(f.read_text()).get("cases", {})
        if not all((cases.get(case) or {}).get("max_response_site") for _l, case, *_ in js):
            if law == prod:
                return None
            continue
        out["files"][law] = MP.rel(f)
        mv = {lab: basis.startswith("v2 critical-joint check")
              and not (abs(k["x_mm"] - cases[case]["max_du_site"]["x_mm"]) < 1e-6
                       and abs(k["y_mm"] - cases[case]["max_du_site"]["y_mm"]) < 1e-6)
              for lab, case, k, basis in js}
        out["moved_off_max_du_by_law"][law] = mv
        if law == prod:
            out["file"] = MP.rel(f)
            out["moved_off_max_du"] = mv
    return out


def _site(case, k, basis, meta):
    return {"case": case, "x_mm": k["x_mm"], "y_mm": k["y_mm"],
            "T_C": SUB.site_temperature(k), "du_xy_um": k["du_xy_um"],
            "du_z_um": k["du_z_um"], "du_def_xy_um": k.get("du_def_xy_um"),
            "site_basis": basis, "case_file": meta[case]["case_file"],
            "case_sha1": meta[case]["case_sha1"]}


def summarize(logs, jsd, verif=None):
    prod = LAW.solder_cfg()["production_law"]
    final = {law: its[-1]["responses"] for law, its in logs.items()}
    meta = {case: _kin_meta(case) for js in jsd.values() for _l, case, *_ in js}
    js0 = jsd[prod] if prod in jsd else next(iter(jsd.values()))
    out = {"what": "local joint response as a band over the configured solder laws "
                   "(finding 1); v2 local model; under every law the maximum over the BGA "
                   "lattice (tcpmt_mech_critical)",
           "state": STATE,
           "production_law": prod, "band_laws": list(logs),
           "model": {k: SUB.lcfg()[k] for k in ("bc_mode", "ramp_s", "dwell_s", "n_cycles",
                                                 "element", "level")},
           "joints": {lab: _site(case, k, basis, meta) for lab, case, k, basis in js0},
           "joints_by_law": {law: {lab: _site(case, k, basis, meta)
                                   for lab, case, k, basis in js}
                             for law, js in jsd.items()},
           "verification": verif or {},
           "inputs_sha1": {p: h for m in meta.values() for p, h in m["inputs_sha1"].items()},
           "iterations": logs, "responses": final, "band": {}, "rankings": {}}
    cc = critical_check(jsd)
    if cc is not None:                 # the joints the critical-joint checks confirmed
        out["critical_check"] = cc
        for law in cc["files"]:
            f = crit_file(law)
            out["inputs_sha1"][str(f.resolve())] = MP.sha1(f)
    for lab, *_ in js0:
        v = {law: final[law].get(lab) for law in final}
        sites = {law: [out["joints_by_law"][law][lab]["x_mm"],
                       out["joints_by_law"][law][lab]["y_mm"]]
                 for law in final if lab in out["joints_by_law"].get(law, {})}
        same = len({tuple(x) for x in sites.values()}) == 1
        if None in v.values() or not v.get(prod):
            out["band"][lab] = {"values": v, "sites_mm": sites, "same_site_all_laws": same,
                                "complete": False}
            continue
        lo, hi = min(v.values()), max(v.values())
        out["band"][lab] = {"values": v, "min": lo, "max": hi, "production": v[prod],
                            "sites_mm": sites, "same_site_all_laws": same,
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
    out["same_site_all_laws"] = all(b.get("same_site_all_laws") for b in out["band"].values())
    out["all_verified"] = all(r.get("confirmed") is not False
                              for per in (verif or {}).values() for r in per.values())
    out["note"] = ("model-form band: not added to the numerical U; a resolved comparison whose "
                   "ranking differs between laws is CONDITIONAL on the law "
                   "(tcpmt_uncertainty.py). Each law's value is its own maximum over the "
                   "lattice (its critical-joint check, re-verified at its final card)")
    BAND.write_text(json.dumps(out, indent=1, default=float) + "\n")
    return out


def main():
    laws = LAW.solder_cfg()["band_laws"]
    only = None
    if "--laws" in sys.argv:
        laws = sys.argv[sys.argv.index("--laws") + 1].split(",")
    if "--joints" in sys.argv:
        only = sys.argv[sys.argv.index("--joints") + 1].split(",")
    execute = "--run" in sys.argv
    logs, jsd, verif = {}, {}, {}
    for law in laws:
        js = joints(only, law)
        for outer in range(3):
            its = iterate(law, js, execute)
            ver, js2, ok = verify(law, its, js) if execute else ({}, js, True)
            if ok or outer == 2 or _same_sites(
                    js2, {lab: {"case": c, "x_mm": k["x_mm"], "y_mm": k["y_mm"]}
                          for lab, c, k, _b in js}):
                break                      # (an unconfirmed maximum stays flagged in verif)
            js = js2                       # a site overtook at the final card: iterate there
        logs[law], jsd[law], verif[law] = its, js, ver
    store_cards(logs, jsd)
    s = summarize(logs, jsd, verif)
    print(json.dumps({"responses": s["responses"], "rankings": s["rankings"],
                      "hold": s["rankings_hold_across_laws"],
                      "same_site_all_laws": s["same_site_all_laws"],
                      "all_verified": s["all_verified"]}, indent=1, default=float))
    for law, its in logs.items():
        for it in its:
            print(law, it["iteration"], it["window_fit_MPa"], it["window_observed_MPa"],
                  it["response_change_max_rel"])


if __name__ == "__main__":
    main()
