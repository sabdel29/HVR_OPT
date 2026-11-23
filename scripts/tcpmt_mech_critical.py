"""Finding 2 -- the critical joint with the v2 local model: the MAXIMUM response over the BGA
lattice, per case and per law of the band.

With the full cut-boundary transfer the joint response is no longer a function of (|du_xy|,
T) alone: du_z, the relative tilt of the two faces and their in-plane stretch enter too, so
the Pareto argument of round 2 does not cover the sites any more (campaign_v3: 7801 of 16107
dominance pairs in (|du_xy|, T) reversed, by up to 6x; Z2's critical joint is not the
maximum-du joint). The response IS monotone, within a few %, in the deforming (rotation-free)
in-plane du, |du_z| and T: over every dominance pair of the solved sites the largest reversal
is 5.6 % (configs/tcpmt_mech local.critical). That is the screening rule:

  * solve the base candidates (tcpmt_mech_kinematics.candidate_sites: top N by |du_xy|, by
    |relative tilt|, by |eps_z| and by the deforming du, the (|du_xy|, T) Pareto front, the
    four corners) and the Pareto front of the WHOLE lattice in the three screening features
    (site kinematics of every lattice site: tcpmt_mech_production.lattice_record);
  * a lattice site s dominated in the three features by a solved site c responds at most
    (1 + margin) R(c), margin = max(margin_min_rel, margin_factor x the largest reversal over
    the law's solved dominance pairs); solve every site whose bound min_c (1 + margin) R(c)
    exceeds the maximum found (a site no solved site dominates is unbounded), and repeat --
    re-validating the margin on the new pairs -- until no bound does.

The maximum over the solved sites then bounds every lattice site: the case's critical joint
and its response under that law. Each law of solder.band_laws is screened with its own
responses at its own stored (converged) window; the law band re-checks the maximum at the
law's final card when the window moves afterwards (tcpmt_mech_law_band.verify).

    python tcpmt_mech_critical.py --run [--law NAME] [CASE ...]
    python tcpmt_mech_critical.py --summarize [--law NAME]
        -> research/tcpmt_revision/solder_critical_v2.json (production law),
           solder_critical_v2_<law>.json (the other laws of the band)
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcpmt_mech_kinematics as KIN                                 # noqa: E402
import tcpmt_mech_submodel as SUB                                   # noqa: E402
import tcpmt_mech_laws as LAW                                       # noqa: E402

import tcpmt_mech_production as MP                                 # noqa: E402

#: TCPMT round 3 (campaign): the compared cases of the local model's state -- the production
#: state of the design in force by default (tcpmt_mech_production.LOCAL_STATE)
STATE = MP.LOCAL_STATE
_SFX = "" if STATE == "SDEC" else f"_{STATE}"
STUDY = "critical_v2" + _SFX
OUT = LAW.TR / f"solder_critical_v2{_SFX}.json"
ROUND2_ORDER = ["Z1_S0", "Z2_S0", "Z3_S0", "Z1_S1", "Z2_S1", "A_Z3", "B_Z1", "B_Z2", "B_Z3",
                "A_Z3land", "B_Z3land"]
CASE_ORDER = ROUND2_ORDER if STATE == "round2" else MP.labels(STATE)


#: relative response difference below which two solves of one site (or of its mirror image)
#: are the same within the local model's own noise (CETOL 0.05 increment control)
NOISE_REL = 0.01


def ccfg():
    return SUB.lcfg()["critical"]


def production_law():
    return LAW.solder_cfg()["production_law"]


def study_for(law):
    return STUDY if law == production_law() else f"{STUDY}_{law}"


def out_for(law):
    return OUT if law == production_law() else OUT.with_name(f"{OUT.stem}_{law}.json")


def card_for(law):
    """(window, status, card sha) of a law at its stored window: the card the check solves."""
    win, status = LAW.stored_window(law)
    return win, status, LAW.card_sha(LAW.card(law, win)[0])


def key(k):
    return (round(k["x_mm"], 6), round(k["y_mm"], 6))


def feat(k):
    """The screening features: deforming (rotation-free) in-plane du, |du_z| (um), T (C)."""
    return (k["du_def_xy_um"], abs(k["du_z_um"]), SUB.site_temperature(k))


def dominates(a, b):
    return all(p >= q for p, q in zip(a, b))


def mirror_of(a, b, tol=1e-6):
    """Site a is a mirror image of site b (|x| and |y| swapped or reflected)."""
    sa = sorted((abs(a["x_mm"]), abs(a["y_mm"])))
    sb = sorted((abs(b["x_mm"]), abs(b["y_mm"])))
    return abs(sa[0] - sb[0]) < tol and abs(sa[1] - sb[1]) < tol


def pareto_front(rows):
    """Strict Pareto front in (|du_xy|, T): no other site is larger in both."""
    return [r for r in rows if not any(o["du_xy_um"] > r["du_xy_um"] and o["T_C"] > r["T_C"]
                                       for o in rows)]


def lattice_front(lat):
    """The lattice sites no other lattice site dominates in the screening features."""
    F = [(feat(k), k) for k in lat]
    return [k for f, k in F if not any(g != f and dominates(g, f) for g, _o in F)]


def _pairs(rows, fkey):
    """Every ordered pair (a, b) of solved rows with a dominating b (>= in all, > in one)."""
    done = [r for r in rows if r.get("d_eps") is not None]
    for a in done:
        fa = fkey(a)
        for b in done:
            if a is b:
                continue
            fb = fkey(b)
            if dominates(fa, fb) and fa != fb:
                yield a, b


def monotonicity(rows, fkey=None, rule=None):
    """Monotonicity of the response over every dominance pair of the solved sites in the
    features fkey (default the round-2 argument, (|du_xy|, T)): the number of pairs whose
    responses are ordered the other way, those beyond the noise, and the largest excess."""
    fkey = fkey or (lambda r: (r["du_xy_um"], r["T_C"]))
    n = nv = nv1 = 0
    worst = None
    for a, b in _pairs(rows, fkey):
        n += 1
        if b["d_eps"] > a["d_eps"]:
            nv += 1
            x = b["d_eps"] / a["d_eps"] - 1.0
            nv1 += x > NOISE_REL
            if worst is None or x > worst["excess_rel"]:
                worst = {"excess_rel": x, "dominating": [a["x_mm"], a["y_mm"]],
                         "dominated": [b["x_mm"], b["y_mm"]]}
    done = [r for r in rows if r.get("d_eps") is not None]
    front = pareto_front(done)
    best = max(done, key=lambda r: r["d_eps"]) if done else None
    return {"n_ordered_pairs": n, "n_violations": nv, "n_violations_over_1pct": nv1,
            "worst_violation": worst,
            "n_pareto_solved": len(front),
            "max_response_on_pareto_front": (best in front) if best else None,
            "rule": rule or ("a site at least as large in both |du_xy| and T must respond at "
                             "least as much (pairs over every solved site); excesses below 1 % "
                             "are within the local model's noise")}


def _screen_key(r):
    return (r["du_def_xy_um"], abs(r["du_z_um"]), r["T_C"])


def margin_of(rows):
    """The bound's margin: max(margin_min_rel, margin_factor x the largest reversal over the
    solved dominance pairs in the screening features)."""
    c = ccfg()
    w = max([b["d_eps"] / a["d_eps"] - 1.0 for a, b in _pairs(rows, _screen_key)
             if b["d_eps"] > a["d_eps"]] or [0.0])
    return max(float(c["margin_min_rel"]), float(c["margin_factor"]) * w), w


def screen(lat, solved, margin):
    """The closure test: {need: lattice sites to solve (unbounded, or bound > the maximum),
    max_bound, n_unbounded} given solved {key: (features, d_eps)}."""
    rmax = max(v for _f, v in solved.values())
    S = list(solved.values())
    need, maxb, unb = [], 0.0, 0
    for k in lat:
        s = key(k)
        if s in solved:
            continue
        f = feat(k)
        b = min((v for g, v in S if dominates(g, f)), default=None)
        if b is None:
            unb += 1
            need.append(k)
            maxb = math.inf
            continue
        b *= 1.0 + margin
        maxb = max(maxb, b)
        if b > rmax:
            need.append(k)
    return {"need": need, "max_bound": maxb, "max_solved": rmax, "n_unbounded": unb}


def candidates(case, n_top):
    """The base candidates of a case (the global search's candidate set)."""
    kin = KIN.load_kinematics(case)
    if not kin:
        return None
    allc = KIN.expand_sites(kin["interconnects"]["bga"]["candidates"])
    for k in allc:
        Gb, Gt = k["G_bot"], k["G_top"]
        k["tilt_rel"] = [Gt[2][0] - Gb[2][0], Gt[2][1] - Gb[2][1]]
    return KIN.candidate_sites(allc, n_top)


def tag(case, k):
    return f"{case}_x{k['x_mm']:+06.2f}_y{k['y_mm']:+06.2f}"


def _fresh(r, k, sha):
    """A record solved with this card and these kinematics."""
    return bool(r) and r.get("card_sha") == sha and abs(
        ((r.get("kin") or {}).get("du_xy_um") or -1.0) - k["du_xy_um"]) < 1e-9


def site_set(case, n_top, law, recs=None):
    """(sites of the check, lattice or None, base candidate keys, lattice-front keys): the base
    candidates, the lattice's Pareto front in the screening features and every lattice site
    already solved by this check with this card (the closure's additions)."""
    base = candidates(case, n_top) or []
    lat = MP.load_lattice(case) if STATE != "round2" else None
    pick = {key(k): k for k in base}
    fr = []
    if lat:
        fr = lattice_front(lat)
        for k in fr:
            pick.setdefault(key(k), k)
        recs = SUB.load_records(study_for(law)) if recs is None else recs
        sha = card_for(law)[2]
        for k in lat:
            if key(k) not in pick and _fresh(recs.get(tag(case, k)), k, sha):
                pick[key(k)] = k
    for k in pick.values():
        k.setdefault("tilt_rel", [k["G_top"][2][0] - k["G_bot"][2][0],
                                  k["G_top"][2][1] - k["G_bot"][2][1]])
    return list(pick.values()), lat, {key(k) for k in base}, {key(k) for k in fr}


def task(case, k, law, top=False):
    return dict(study=study_for(law), tag=tag(case, k), kin=k, law=law,
                meta={"case": case, "x_mm": k["x_mm"], "y_mm": k["y_mm"], "max_du": top,
                      "law": law})


def run(cases, n_top, law):
    """Solve the check's sites, screen the lattice, add what the bound cannot exclude, repeat."""
    extra = {c: [] for c in cases}
    for rnd in range(int(ccfg()["max_rounds"])):
        ts = []
        for case in cases:
            sites, _lat, _b, _f = site_set(case, n_top, law)
            seen = {key(k) for k in sites}
            sites += [k for k in extra[case] if key(k) not in seen]
            top = max(sites, key=lambda k: k["du_xy_um"]) if sites else None
            ts += [task(case, k, law, k is top) for k in sites]
        print(f"round {rnd}: {len(ts)} sites ({law})", flush=True)
        SUB.run_tasks(ts)
        recs = SUB.load_records(study_for(law))
        sha = card_for(law)[2]
        n_add = 0
        for case in cases:
            sites, lat, _b, _f = site_set(case, n_top, law, recs)
            if not lat:
                continue
            rows = [_row(k, recs.get(tag(case, k)), sha) for k in sites]
            solved = {key(r): (_screen_key(r), r["d_eps"]) for r in rows
                      if r["d_eps"] is not None}
            if not solved:
                print(f"  {case}: nothing solved", flush=True)
                return False
            m, _w = margin_of(rows)
            sc = screen(lat, solved, m)
            extra[case] = sc["need"]
            n_add += len(sc["need"])
            print(f"  {case}: {len(solved)} solved, margin {m:.3f}, max {sc['max_solved']:.4e}, "
                  f"max bound {sc['max_bound']:.4e}, {len(sc['need'])} to add", flush=True)
        if not n_add:
            return True
    return False


def _row(k, r, sha):
    fresh = _fresh(r, k, sha)
    return {"x_mm": k["x_mm"], "y_mm": k["y_mm"], "du_xy_um": k["du_xy_um"],
            "du_z_um": k["du_z_um"], "T_C": SUB.site_temperature(k),
            "du_def_xy_um": k.get("du_def_xy_um"), "tilt_rel": k.get("tilt_rel"),
            "d_eps": r.get("d_peeq_per_cycle") if fresh else None,
            "error": (r.get("error") if fresh else
                      ("stale record (other card or kinematics)" if r else "not solved"))}


def summarize(n_top, law=None):
    law = law or production_law()
    recs = SUB.load_records(study_for(law))
    win, wstat, sha = card_for(law)
    c = ccfg()
    out = {"what": "critical joint, v2 local model (finding 2): the maximum response over the "
                   "BGA lattice under one law",
           "state": STATE,
           "model": {k: SUB.lcfg()[k] for k in ("bc_mode", "ramp_s", "dwell_s", "n_cycles",
                                                 "element", "level")},
           "law": law, "production_law": production_law(),
           "window_status": wstat, "window_MPa": win, "card_sha": sha,
           "candidate_rule": f"base: top {n_top} by |du_xy|, by |relative tilt|, by |eps_z| and "
                             "by the deforming du, the strict Pareto front in (|du_xy|, T) and "
                             "the four corners, over every evaluated lattice site; plus the "
                             "lattice's Pareto front in the screening features and every "
                             "lattice site the dominance bound could not exclude",
           "screen": {"features": list(c["screen_features"]),
                      "margin_min_rel": float(c["margin_min_rel"]),
                      "margin_factor": float(c["margin_factor"]),
                      "rule": "a lattice site dominated in (deforming du, |du_z|, T) by a solved "
                              "site c responds at most (1 + margin) R(c); margin = max(min, "
                              "factor x the largest reversal over the solved dominance pairs). "
                              "Closed when every unsolved lattice site's bound is at most the "
                              "maximum solved response."},
           "inputs_sha1": {}, "cases": {}}
    # the card it was solved with is recorded by its hash (card_sha): the law band re-stores
    # the window afterwards by design (and re-checks the maximum at its final card)
    n_tot = n_ok = 0
    for case in CASE_ORDER:
        sites, lat, base, fr = site_set(case, n_top, law, recs)
        if not sites:
            continue
        rows = [_row(k, recs.get(tag(case, k)), sha) for k in sites]
        for r, k in zip(rows, sites):
            r["origin"] = ("base" if key(k) in base else
                           "lattice front" if key(k) in fr else "bound")
        rows.sort(key=lambda r: -r["du_xy_um"])
        done = [r for r in rows if r["d_eps"] is not None]
        if not done:
            continue
        top = max(rows, key=lambda r: r["du_xy_um"])
        best = max(done, key=lambda r: r["d_eps"])
        # a mirror image of the maximum-du site responding more by less than the local model's
        # own noise (NOISE_REL: CETOL-controlled creep increments) is that site; a larger excess
        # is physical (the streamwise coolant breaks the mirror symmetry) and moves the joint
        twin = (best is not top and mirror_of(best, top) and top["d_eps"] is not None
                and best["d_eps"] / top["d_eps"] - 1.0 < NOISE_REL)
        if twin:
            best = top
        others = [r for r in done if r is not top]
        second = max(others, key=lambda r: r["d_eps"]) if others else None
        n_tot += 1
        is_max = top["d_eps"] is not None and best is top
        n_ok += bool(is_max)
        kin = KIN.load_kinematics(case) or {}
        out["inputs_sha1"].update(kin.get("inputs_sha1") or {})
        if lat:
            out["inputs_sha1"].update(MP.inputs_sha1([MP.lattice_path(case)]))
        stale = [r["error"] for r in rows if r.get("error")]
        scr = None
        if lat:
            m, w = margin_of(rows)
            sc = screen(lat, {key(r): (_screen_key(r), r["d_eps"]) for r in done}, m)
            scr = {"n_lattice": len(lat), "n_base": len(base), "n_lattice_front": len(fr),
                   "n_solved": len(done), "largest_reversal_rel": w, "margin_rel": m,
                   "max_solved": sc["max_solved"], "max_bound_unsolved": sc["max_bound"],
                   "n_unbounded": sc["n_unbounded"], "n_to_add": len(sc["need"]),
                   "closed": not sc["need"],
                   "max_is_base_candidate": key(best) in base}
        out["cases"][case] = {
            "case_file": kin.get("case_file"), "case_sha1": kin.get("case_sha1"),
            "site_coverage": kin.get("site_coverage"),
            "n_candidates": len(rows), "n_solved": len(done), "n_failed": len(stale),
            "monotonicity": monotonicity(rows),
            "monotonicity_screen": monotonicity(
                rows, _screen_key, "the same over (deforming du, |du_z|, T): the screening "
                                   "features"),
            "screen": scr,
            "max_du_site": top, "max_response_site": best,
            "mirror_twin_of_max_du_responded_more": bool(twin),
            "critical_is_max_du": is_max if top["d_eps"] is not None else None,
            "margin_rel": ((top["d_eps"] - second["d_eps"]) / top["d_eps"]
                           if (second and top["d_eps"]) else None),
            "max_response_over_max_du": (best["d_eps"] / top["d_eps"]
                                         if top["d_eps"] else None),
            "candidates": rows}
    out["all_max_du"] = (n_ok == n_tot) if n_tot else None
    out["n_cases"] = n_tot
    out["all_closed"] = (len(out["cases"]) == len(CASE_ORDER) and all(
        (c.get("screen") or {}).get("closed") for c in out["cases"].values())) \
        if STATE != "round2" else None
    out_for(law).write_text(json.dumps(out, indent=1, default=float) + "\n")
    return out


def main():
    a = sys.argv[1:]
    n_top = int(a[a.index("--top") + 1]) if "--top" in a else int(ccfg()["n_top"])
    law = a[a.index("--law") + 1] if "--law" in a else production_law()
    cases = [x for x in a if x in KIN.CASES] or CASE_ORDER
    if "--run" in a:
        closed = run(cases, n_top, law)
        print("closed:", closed, flush=True)
    if "--summarize" in a:
        s = summarize(n_top, law)
        for k, c in s["cases"].items():
            b, sc = c["max_response_site"], c.get("screen") or {}
            print(f"{k}: {c['n_solved']}/{c['n_candidates']}; max d_eps at ({b['x_mm']}, "
                  f"{b['y_mm']}) = {b['d_eps']:.4e}; is max-du: {c['critical_is_max_du']}; "
                  f"ratio {c['max_response_over_max_du']}; closed {sc.get('closed')} "
                  f"(margin {sc.get('margin_rel')}, bound {sc.get('max_bound_unsolved')})")
        print("all max-du:", s["all_max_du"], "all closed:", s["all_closed"])


if __name__ == "__main__":
    main()
