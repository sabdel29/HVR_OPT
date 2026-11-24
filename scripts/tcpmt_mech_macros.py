"""Macros of the mechanics revision in the production state (TCPMT round 3) for
results_macros.tex: the v2 joint response with its law band, the critical-joint check, the
local-model checks, the interconnect layers, reflow / bonding warpage, board / mounting / clamp
and the mechanics-only variants. Every macro starts with "Mv"; a missing artifact gives no
macro (the manuscript prints the undefined name, never a stale number).

Read from the results root ($ETM_RESULTS_ROOT): tcpmt_revision/solder_law_band.json,
solder_law_cards.json, solder_law_record.json, solder_critical_v2.json, solder_local_checks.json,
interconnect_drivers.json, interconnect_mesh_ladder.json, reflow_warpage.json,
board_study_SDEC.json, robustness_mech_SDEC.json, robustness_B.json, uncertainty.json.

    python tcpmt_mech_macros.py          prints every macro
"""
from __future__ import annotations

import json
import os
from pathlib import Path

R = Path(__file__).resolve().parents[1]
TR = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision"   # hook
NA = "--"
ATAG = {"Z1": "Zone", "Z2": "Ztwo", "Z3": "Zthree"}
LTAG = {"schubert2003": "Schub", "xiao_armstrong2005": "Xiao", "xa_measured_norton": "Meas"}
TIERS = ("A", "B")
ARCHS = ("Z1", "Z2", "Z3")


def J(name):
    p = TR / name
    try:
        return json.loads(p.read_text()) if p.is_file() else None
    except json.JSONDecodeError:
        return None


def fx(v, n=1):
    try:
        return NA if v is None else f"{float(v):.{n}f}"
    except (TypeError, ValueError):
        return NA


def pct(v, n=1):
    return NA if v is None else fx(100.0 * v, n)


def spct(v, n=1):
    """signed percent with a typographic minus"""
    if v is None:
        return NA
    s = f"{100.0 * v:+.{n}f}"
    return s.replace("-", r"\textminus{}")


def xy(x, y):
    """a site '(x, y)' in mm with typographic minus signs"""
    return f"({x:g}, {y:g})".replace("-", r"\textminus{}")


def rng(vals, f=pct, n=1):
    v = [x for x in vals if x is not None]
    return (f(min(v), n), f(max(v), n)) if v else (NA, NA)


def yn(b):
    return NA if b is None else ("yes" if b else "no")


# ------------------------------------------------------------------ joint response, law band
def joint():
    b = J("solder_law_band.json")
    if not b or not b.get("band"):
        return {}
    m = {}
    prod = b["production_law"]
    m["MvLawProd"] = {"schubert2003": "Schubert et al.", "xiao_armstrong2005":
                      "Xiao and Armstrong", "xa_measured_norton": "measured Norton"}.get(prod, prod)
    m["MvLawN"] = str(len(b.get("band_laws") or []))
    m["MvEpsState"] = {"SDEC": "production state", "S0": "ideal-decoupling reference"}.get(
        b.get("state") or "S0", b.get("state") or "")
    ratios = {law: [] for law in b.get("band_laws") or []}
    spread = []
    for lab, v in b["band"].items():
        t, a = lab.split("_")
        k = f"{t}{ATAG[a]}"
        if not v.get("complete"):
            continue
        m[f"MvEps{k}"] = fx(1e3 * v["production"], 2)
        m[f"MvEpsLo{k}"] = fx(1e3 * v["min"], 2)
        m[f"MvEpsHi{k}"] = fx(1e3 * v["max"], 2)
        for law, x in v["values"].items():
            if law in LTAG and x is not None:
                m[f"MvEps{LTAG[law]}{k}"] = fx(1e3 * x, 2)
                ratios.setdefault(law, []).append(x / v["production"])
        spread.append(v["spread_rel_to_production"])
        for law, p in (v.get("sites_mm") or {}).items():
            if law in LTAG and p:
                m[f"MvEpsSite{LTAG[law]}{k}"] = xy(*p)
        jt = (b.get("joints") or {}).get(lab) or {}
        m[f"MvTsj{k}"] = fx(jt.get("T_C"), 1)
        m[f"MvDuxy{k}"] = fx(jt.get("du_xy_um"), 2)
        m[f"MvDuz{k}"] = fx(jt.get("du_z_um"), 2)
        m[f"MvDudef{k}"] = fx(jt.get("du_def_xy_um"), 2)
        if jt.get("x_mm") is not None:
            m[f"MvSite{k}"] = xy(jt['x_mm'], jt['y_mm'])
    for law, r in ratios.items():
        if law != prod and r and law in LTAG:
            m[f"MvRatio{LTAG[law]}Lo"], m[f"MvRatio{LTAG[law]}Hi"] = fx(min(r), 2), fx(max(r), 2)
    m["MvLawSpreadMax"] = pct(max(spread), 0) if spread else NA
    rk = (b.get("rankings") or {}).get(prod) or {}
    for t in TIERS:
        if rk.get(t):
            m[f"MvEpsOrder{t}"] = rk[t].replace("<", "$<$")
            m[f"MvEpsLow{t}"] = rk[t].split("<")[0].strip()
    m["MvEpsOrderHold"] = ("hold" if b.get("rankings_hold_across_laws") else
                           "do not all hold") if b.get("rankings_hold_across_laws") is not None \
        else NA
    for law, rr in (b.get("rankings") or {}).items():
        for t in TIERS:
            if law in LTAG and rr.get(t):
                m[f"MvEpsOrder{t}{LTAG[law]}"] = rr[t].replace("<", "$<$")
    # TCPMT round 3: under every law its own maximum over the lattice -- is it the same site?
    if b.get("same_site_all_laws") is not None:
        m["MvEpsSameSite"] = yn(b["same_site_all_laws"])
        diff = {}
        for lab, v in b["band"].items():
            sites = v.get("sites_mm") or {}
            ps = sites.get(prod)
            for law, q in sites.items():
                if law != prod and ps and q and tuple(q) != tuple(ps):
                    t, a = lab.split("_")
                    diff.setdefault((a, t), []).append(law)
        names = {"schubert2003": "Schubert et al.", "xiao_armstrong2005": "Xiao and Armstrong",
                 "xa_measured_norton": "measured Norton"}
        m["MvEpsSiteDiffN"] = str(len(diff))
        m["MvEpsSiteDiff"] = "; ".join(
            f"{a} under cooling~{t} ({', '.join(names.get(x, x) for x in laws)})"
            for (a, t), laws in sorted(diff.items())) or "none"
    if b.get("all_verified") is not None:
        m["MvBandVerified"] = yn(b["all_verified"])
    cc = b.get("critical_check") or {}
    m["MvBandAtCritical"] = yn(bool(cc))
    m["MvBandMoved"] = str(sum(1 for x in (cc.get("moved_off_max_du") or {}).values() if x)) \
        if cc else NA
    # numerical U and the resolution under the band, from the uncertainty record
    u = J("uncertainty.json") or {}
    for lab, v in (u.get("eps_reported") or {}).items():
        t, a = lab.split("_")
        m[f"MvEpsU{t}{ATAG[a]}"] = fx(v.get("U95_num_x1e3"), 2)
        val = v.get("value_x1e3")
        if val:
            m[f"MvEpsUrel{t}{ATAG[a]}"] = fx(100 * (v.get("U95_num_x1e3") or 0) / val, 1)
    rows = [r for r in u.get("comparisons") or [] if r.get("output") == "eps"] \
        if u.get("eps_state") == b.get("state") else []
    if not rows:                    # the local checks' own resolution (same rule, same U)
        jr = (J("solder_local_checks.json") or {}).get("joint_resolution") or {}
        for key, r in (jr.get("pairs") or {}).items():
            t, ab = key.split(":")
            a, bb = ab.split("/")
            rows.append(dict(r, tier=t, a=a, b=bb))
        for lab, ur in (jr.get("U_rel") or {}).items():
            t, a = lab.split("_")
            v = (b["band"].get(lab) or {}).get("production")
            if v and ur is not None:
                m.setdefault(f"MvEpsU{t}{ATAG[a]}", fx(1e3 * v * ur, 2))
                m.setdefault(f"MvEpsUrel{t}{ATAG[a]}", fx(100 * ur, 1))
    for r in rows:
        k = f"MvEpsRes{r['tier']}{ATAG[r['a']]}{ATAG[r['b']]}"
        m[k] = r.get("verdict") or NA
        k2 = f"MvEpsRes{r['tier']}{ATAG[r['b']]}{ATAG[r['a']]}"
        m.setdefault(k2, m[k])
    res = [r.get("verdict") for r in rows]
    if res:
        m["MvEpsResN"] = str(len(res))
        m["MvEpsResResolved"] = str(sum(1 for v in res if v == "resolved"))
        m["MvEpsResLaw"] = str(sum(1 for v in res if v == "law-conditional"))
    return m


def window():
    c = J("solder_law_cards.json")
    if not c:
        return {}
    b = J("solder_law_band.json") or {}
    prod = b.get("production_law") or "schubert2003"
    m = {}
    for law, e in (c.get("laws") or {}).items():
        tag = "" if law == prod else LTAG.get(law, "")
        if law != prod and not tag:
            continue
        w, vis = e.get("window_MPa") or {}, e.get("visited_window_last_MPa") or {}
        for ph, P in (("hot", "Hot"), ("cold", "Cold")):
            if w.get(ph):
                m[f"Mv{tag}Win{P}Lo"], m[f"Mv{tag}Win{P}Hi"] = fx(w[ph][0], 0), fx(w[ph][1], 0)
            if vis.get(ph):
                m[f"Mv{tag}Vis{P}Lo"], m[f"Mv{tag}Vis{P}Hi"] = fx(vis[ph][0], 0), \
                    fx(vis[ph][1], 0)
        m[f"Mv{tag}WinIters"] = str(e.get("n_iterations", NA))
        m[f"Mv{tag}WinConv"] = yn(e.get("converged"))
    rec = J("solder_law_record.json") or {}
    pl = (rec.get("laws") or {}).get(prod) or {}
    m["MvSurrErrHot"] = pct(pl.get("surrogate_max_rate_err_rel_hot"), 0)
    m["MvSurrErrCold"] = pct(pl.get("surrogate_max_rate_err_rel_cold"), 0)
    rv = pl.get("rate_vs_measured_Sn3.9Ag0.6Cu") or {}
    m["MvRateVsDataLo"], m["MvRateVsDataHi"] = fx(rv.get("ratio_min"), 0), fx(rv.get("ratio_max"),
                                                                           0)
    return m


# ------------------------------------------------------------------ critical-joint check
def critical():
    c = J("solder_critical_v2.json")
    if not c or not c.get("cases"):
        return {}
    m = {}
    cs = c["cases"]
    m["MvCritCases"] = str(len(cs))
    m["MvCritCand"] = str(sum(v.get("n_candidates", 0) for v in cs.values()))
    m["MvCritSites"] = str(sum(v.get("n_solved", 0) for v in cs.values()))
    mono = [v.get("monotonicity") or {} for v in cs.values()]
    m["MvCritPairs"] = f"{sum(x.get('n_ordered_pairs', 0) for x in mono):,}".replace(",", "{,}")
    m["MvCritViol"] = str(sum(x.get("n_violations", 0) for x in mono))
    worst = [(x.get("worst_violation") or {}).get("excess_rel") for x in mono]
    worst = [w for w in worst if w is not None]
    m["MvCritViolMax"] = pct(max(worst), 1) if worst else "0"
    m["MvCritAllMaxDu"] = yn(c.get("all_max_du"))
    m["MvCritMoved"] = str(sum(1 for v in cs.values() if v.get("critical_is_max_du") is False))
    moved = {}
    for lab, v in cs.items():
        if v.get("critical_is_max_du") is False:
            _s, t, a = lab.split("_")
            moved.setdefault(a, []).append(t)
    if moved:
        parts = [f"{a} under cooling~{' and '.join(ts)}" for a, ts in sorted(moved.items())]
        m["MvCritMovedCases"] = "; ".join(parts)
    m["MvCritOnPareto"] = str(sum(1 for x in mono if x.get("max_response_on_pareto_front")))
    rat = [v.get("max_response_over_max_du") for v in cs.values()
           if v.get("max_response_over_max_du")]
    m["MvCritRatioMax"] = pct(max(rat) - 1.0, 1) if rat else NA
    cov = [((v.get("site_coverage") or {}).get("full")) for v in cs.values()]
    m["MvCritCoverage"] = yn(all(cov)) if cov else NA
    # the screening rule that makes the maximum a bound over the whole lattice (TCPMT round 3)
    scr = [v.get("screen") for v in cs.values() if v.get("screen")]
    if scr:
        m["MvCritLattice"] = f"{sum(x['n_lattice'] for x in scr):,}".replace(",", "{,}")
        m["MvCritBase"] = str(sum(x["n_base"] for x in scr))
        m["MvCritFront"] = str(sum(x["n_lattice_front"] for x in scr))
        m["MvCritMargin"] = pct(max(x["margin_rel"] for x in scr), 0)
        m["MvCritMarginMin"] = pct(min(x["margin_rel"] for x in scr), 0)
        m["MvCritRevF"] = pct(max(x["largest_reversal_rel"] for x in scr), 1)
        m["MvCritClosed"] = yn(c.get("all_closed"))
        m["MvCritMaxInBase"] = str(sum(1 for x in scr if x.get("max_is_base_candidate")))
        mf = [v.get("monotonicity_screen") or {} for v in cs.values()]
        m["MvCritPairsF"] = f"{sum(x.get('n_ordered_pairs', 0) for x in mf):,}".replace(",",
                                                                                       "{,}")
        m["MvCritViolF"] = str(sum(x.get("n_violations_over_1pct", 0) for x in mf))
        sp = (c.get("screen") or {})
        m["MvCritMarginFactor"] = fx(sp.get("margin_factor"), 0)
    # every law of the band: its own check (sites solved, closed, moved joints)
    for law, tag in LTAG.items():
        cl = c if law == c.get("law") else J(f"solder_critical_v2_{law}.json")
        if not cl or not cl.get("cases"):
            continue
        cl_cs = cl["cases"]
        m[f"MvCrit{tag}Solved"] = f"{sum(v.get('n_solved', 0) for v in cl_cs.values()):,}" \
            .replace(",", "{,}")
        m[f"MvCrit{tag}Closed"] = yn(cl.get("all_closed"))
        m[f"MvCrit{tag}Moved"] = str(sum(1 for v in cl_cs.values()
                                         if v.get("critical_is_max_du") is False))
        for lab, v in cl_cs.items():
            _s, t, a = lab.split("_")
            mr = v.get("max_response_site") or {}
            if mr:
                m[f"MvCritSite{tag}{t}{ATAG[a]}"] = xy(mr['x_mm'], mr['y_mm'])
    allc = [J("solder_critical_v2_" + law + ".json") if law != c.get("law") else c
            for law in LTAG]
    allc = [x for x in allc if x and x.get("cases")]
    if allc:
        m["MvCritSolvedAll"] = f"{sum(v.get('n_solved', 0) for x in allc for v in x['cases'].values()):,}" \
            .replace(",", "{,}")
        m["MvCritClosedAll"] = yn(all(x.get("all_closed") for x in allc))
    for lab, v in cs.items():
        st, t, a = lab.split("_")
        k = f"{t}{ATAG[a]}"
        sc = v.get("site_coverage") or {}
        m[f"MvLatticeSites{ATAG[a]}"] = str(sc.get("lattice_sites", NA))
        m[f"MvCritN{k}"] = str(v.get("n_solved", NA))
        m[f"MvCritIsMaxDu{k}"] = yn(v.get("critical_is_max_du"))
        m[f"MvCritRatio{k}"] = fx(v.get("max_response_over_max_du"), 3)
        mr = v.get("max_response_site") or {}
        if mr:
            m[f"MvCritSite{k}"] = xy(mr['x_mm'], mr['y_mm'])
    return m


# ------------------------------------------------------------------ local-model checks
def checks():
    c = J("solder_local_checks.json")
    if not c or not c.get("groups"):
        return {}
    g = c["groups"]
    m = {}

    def rel(group, var):
        return {lab: (r.get(var) or {}).get("rel_to_v2") for lab, r in (g.get(group) or {}).items()}
    for var, tag in (("L3", "Mesh"), ("N8", "Cyc")):
        grp = "mesh" if var == "L3" else "cycles"
        vals = rel(grp, var)
        for lab, x in vals.items():
            t, a = lab.split("_")
            m[f"Mv{tag}U{t}{ATAG[a]}"] = pct(abs(x) if x is not None else None, 1)
        v = [abs(x) for x in vals.values() if x is not None]
        m[f"Mv{tag}Umax"] = pct(max(v), 1) if v else NA
    for var, tag in (("dwell60", "DwellSixty"), ("dwell900", "DwellNineHundred"),
                     ("ramp30", "RampThirty")):
        v = [x for x in rel("dwell", var).values() if x is not None]
        m[f"Mv{tag}Lo"], m[f"Mv{tag}Hi"] = rng(v, spct, 1)
    for var, tag in (("C3D8I", "ElemI"), ("C3D8R", "ElemR")):
        v = [x for x in rel("element", var).values() if x is not None]
        m[f"Mv{tag}"] = spct(v[0], 1) if v else NA
    # the attribution chain round 2 -> v2, one change at a time
    ch = g.get("chain") or {}
    steps = ("R2", "ramp", "law", "uz", "v2")
    for lab, r in ch.items():
        t, a = lab.split("_")
        k = f"{t}{ATAG[a]}"
        d = {s: (r.get(s) or {}).get("d_eps") for s in steps}
        m[f"MvChainRtwo{k}"] = fx(1e3 * d["R2"], 2) if d["R2"] else NA
        if d["R2"] and d["v2"]:
            m[f"MvChainRatio{k}"] = fx(d["v2"] / d["R2"], 2)
    for s, tag in zip(steps[1:], ("Ramp", "Law", "Uz", "Global")):
        prev = steps[steps.index(s) - 1]
        v = [((r.get(s) or {}).get("d_eps") / (r.get(prev) or {}).get("d_eps") - 1.0)
             for r in ch.values() if (r.get(s) or {}).get("d_eps") and
             (r.get(prev) or {}).get("d_eps")]
        m[f"MvChain{tag}Lo"], m[f"MvChain{tag}Hi"] = rng(v, spct, 0)
    rat = [((r.get("v2") or {}).get("d_eps") / (r.get("R2") or {}).get("d_eps"))
           for r in ch.values() if (r.get("v2") or {}).get("d_eps") and
           (r.get("R2") or {}).get("d_eps")]
    m["MvChainRatioLo"], m["MvChainRatioHi"] = rng(rat, fx, 2)
    # finding 4: the critical fine-pitch joints with their own geometry
    for key, v in (c.get("fine_pitch_joints") or {}).items():
        t, a = ("B", key[2:]) if key.startswith("B_") else ("A", key)
        k = f"{t}{ATAG[a]}"
        m[f"MvFineEps{k}"] = fx(1e3 * v["d_eps"], 2) if v.get("d_eps") else NA
        m[f"MvFineEpsUz{k}"] = fx(1e3 * v["d_eps_uz"], 2) if v.get("d_eps_uz") else NA
        m[f"MvFineT{k}"] = fx(v.get("T_C"), 1)
        m[f"MvFineGam{k}"] = fx(1e3 * v["gamma"], 1) if v.get("gamma") else NA
        m[f"MvFineGamDef{k}"] = fx(1e3 * v["gamma_def"], 1) if v.get("gamma_def") else NA
        if t == "A":
            m[f"MvFineH{ATAG[a]}"] = fx(v.get("h_um"), 0)
    return m


# ------------------------------------------------------------------ interconnect layers
FINE = {"Z1": "interface", "Z2": "conv_attach_vr_substrate", "Z3": "z3_attach_vr_pcb"}
LAYER_WORD = {"bga": "BGA", "interface": "die microbumps",
              "conv_attach_vr_substrate": "Cu-pillar attach", "z3_attach_vr_pcb": "SAC attach"}


def interconnects():
    d = J("interconnect_drivers.json")
    if not d or not d.get("cases"):
        return {}
    m = {}
    for lab, c in d["cases"].items():
        st, t, a = lab.split("_")
        k = f"{t}{ATAG[a]}"
        L = c.get("layers") or {}
        for name, tag in (("bga", "Bga"), ("interface", "If"), (FINE[a], "Att")):
            if a == "Z1" and tag == "Att":
                continue
            r = L.get(name)
            if not r:
                continue
            cr = r["critical"]
            m[f"MvGam{tag}{k}"] = fx(1e3 * r["gamma_max"], 2)
            m[f"MvGamDef{tag}{k}"] = fx(1e3 * r["gamma_def_max"], 2) \
                if r.get("gamma_def_max") is not None else NA
            m[f"MvT{tag}{k}"] = fx(cr.get("T_C"), 1)
            m[f"MvH{tag}{ATAG[a]}"] = fx(r.get("h_um"), 0)
        gl = c.get("governing_layer_by_shear_strain")
        m[f"MvGovLayer{k}"] = LAYER_WORD.get(gl, gl or NA)
        gg = c.get("governing_layer_by_gamma")
        m[f"MvGovLayerGam{k}"] = LAYER_WORD.get(gg, gg or NA)
        sp = c.get("bga_split") or {}
        sh = sp.get("share_along_du") or {}
        m[f"MvMemShare{k}"] = spct(sh.get("membrane"), 0)
        m[f"MvBendShare{k}"] = spct(sh.get("bending"), 0)
        m[f"MvMemUm{k}"] = fx(sp.get("membrane_um"), 2)
        m[f"MvBendUm{k}"] = fx(sp.get("bending_um"), 2)
        m[f"MvRigidRot{k}"] = fx(sp.get("rigid_rotation_um"), 3)
        m[f"MvDuDefBga{k}"] = fx(sp.get("deforming_xy_um"), 2)
    lad = J("interconnect_mesh_ladder.json") or {}
    for lab, c in (lad.get("cases") or {}).items():
        st, t, a = lab.split("_")
        k = f"{t}{ATAG[a]}"
        for name, tag in (("bga", "Bga"), ("interface", "If"), (FINE[a], "Att")):
            v = (c.get("layers") or {}).get(name) or {}
            if v.get("r31_over_r21") is not None and not (a == "Z1" and tag == "Att"):
                m[f"MvLad{tag}{k}"] = fx(v["r31_over_r21"], 2)
    return m


# ------------------------------------------------------------------ reflow / bonding
def reflow():
    d = J("reflow_warpage.json")
    if not d or not d.get("cases"):
        return {}
    m = {}
    lim = d.get("limits") or {}

    def lv(k):
        x = lim.get(k) or {}
        return x.get("value") if isinstance(x, dict) else x
    m["MvCoplLim"] = fx(lv("bga_coplanarity_room_um"), 0)
    rl = lv("bga_reflow_warpage_um") or [None, None]
    m["MvRfLimLo"], m["MvRfLimHi"] = fx(rl[0], 0), fx(rl[1], 0)
    m["MvTcbLim"] = fx(lv("tcb_coplanarity_um"), 0)
    m["MvAttLimZthree"] = fx(lv("z3_attach_coplanarity_um"), 0)
    for key, c in d["cases"].items():
        parts = key.split("_r21")
        a, sfx = parts[0], (parts[1] if len(parts) > 1 else None)
        if sfx is None or a not in ATAG:
            continue
        tag = {"": "", "_encap_uf_tg": "Uf", "_encap_emc_lowcte": "Emc"}.get(sfx)
        if tag is None:
            continue
        ch = c.get("checks") or {}
        b = (ch.get("bga@bga_reflow") or {})
        w = b.get("warpage") or {}
        m[f"MvRfBga{tag}{ATAG[a]}"] = fx(w.get("pv_plane_removed_um"), 0)
        m[f"MvRfBow{tag}{ATAG[a]}"] = fx(w.get("bow_corner_minus_centre_um"), 0)
        m[f"MvRfCopl{tag}{ATAG[a]}"] = fx(b.get("pv_over_room_coplanarity"), 2)
        m[f"MvRfWithin{tag}{ATAG[a]}"] = yn(b.get("within_reflow_limit_magnitude"))
        s = (ch.get("bga@bga_solidus") or {}).get("warpage") or {}
        m[f"MvRfSol{tag}{ATAG[a]}"] = fx(s.get("pv_plane_removed_um"), 0)
        cure = (ch.get("bga@bga_reflow") or {}).get("cure_reference_150C") or {}
        if cure:
            m[f"MvRfCure{tag}{ATAG[a]}"] = fx(cure.get("pv_plane_removed_um"), 0)
        tc = ch.get("tcb") or {}
        g = tc.get("gap_nonuniformity") or {}
        m[f"MvRfTcb{tag}{ATAG[a]}"] = fx(g.get("pv_plane_removed_um"), 1)
        m[f"MvRfTcbOk{tag}{ATAG[a]}"] = yn(tc.get("within_limit"))
        m[f"MvRfTcbT{tag}{ATAG[a]}"] = fx(tc.get("T_C"), 0)
    return m


# ------------------------------------------------------------------ board / mounting / clamp
BVAR = {"screws": "Screws", "screws_pinned": "Pinned", "edge": "Edge",
        "clamp_screws": "Clamp", "clamp_only": "ClampOnly", "clamp_backplate": "Backplate",
        "free_ring_hot": "LargeHot", "free_ring_cold": "LargeCold",
        "screws_ring_hot": "LargeScrews", "clamp_screws_ring_hot": "LargeClamp"}


def board():
    d = J("board_study_SDEC.json")
    if not d or not d.get("cases"):
        return {}
    m = {}
    acc = {}
    free_dev, clamp_eff = [], []
    for lab, c in d["cases"].items():
        st, t, a = lab.split("_")
        k = f"{t}{ATAG[a]}"
        for var, tag in BVAR.items():
            r = (c.get("mechanics") or {}).get(var) or {}
            if "warp_rel_vs_case" not in r:
                continue
            m[f"MvBd{tag}Warp{k}"] = spct(r["warp_rel_vs_case"], 1)
            m[f"MvBd{tag}Du{k}"] = spct(r["du_rel_vs_case"], 1)
            acc.setdefault(tag, {"w": [], "d": []})
            acc[tag]["w"].append(r["warp_rel_vs_case"])
            acc[tag]["d"].append(r["du_rel_vs_case"])
        fr = c.get("free_reproduces_case") or {}
        if fr:
            free_dev.append(max(abs(fr.get("warp_rel", 0)), abs(fr.get("du_rel", 0))))
        cl = c.get("clamp_local") or {}
        if cl.get("clamp_effect_rel") is not None:
            m[f"MvClampEps{k}"] = spct(cl["clamp_effect_rel"], 1)
            clamp_eff.append(cl["clamp_effect_rel"])
        if c.get("clamp"):
            m["MvClampForce"] = fx(c["clamp"].get("force_N"), 0)
            m["MvClampMPa"] = fx(c["clamp"].get("pressure_MPa"), 2)
        if c.get("board_side_mm"):
            m["MvBoardSide"] = fx(c["board_side_mm"], 0)
        own = c.get("larger_board_own_field") or {}
        if own.get("warp_rel") is not None:
            # the 3x board's own E-T field (coarse rung) against the case's coupon rung
            m[f"MvBdOwnWarp{k}"] = spct(own["warp_rel"], 1)
            m[f"MvBdOwnDu{k}"] = spct(own["du_rel"], 1)
            t_k = own.get("T_max_K")
            m[f"MvBdOwnT{k}"] = NA if t_k is None else f"{t_k:+.1f}".replace("-", r"\textminus{}")
            m[f"MvBdOwnP{k}"] = spct(own.get("P_loss_rel"), 1)
            acc.setdefault("Own", {"w": [], "d": []})
            acc["Own"]["w"].append(own["warp_rel"])
            acc["Own"]["d"].append(own["du_rel"])
    for tag, v in acc.items():
        m[f"MvBd{tag}WarpLo"], m[f"MvBd{tag}WarpHi"] = rng(v["w"], spct, 1)
        m[f"MvBd{tag}DuLo"], m[f"MvBd{tag}DuHi"] = rng(v["d"], spct, 1)
        m[f"MvBd{tag}AbsMax"] = pct(max(abs(x) for x in v["w"] + v["d"]), 1)
    m["MvBdFreeDev"] = fx(100 * max(free_dev), 3) if free_dev else NA
    m["MvClampEpsLo"], m["MvClampEpsHi"] = rng(clamp_eff, spct, 1)
    return m


# ------------------------------------------------------------------ mechanics-only variants
EVAR = {"encap_uf_tg": "Uf", "encap_emc_lowcte": "Emc", "encap_emc_lowcte_const": "EmcConst",
        "bga_card_local": "BgaLocal"}


def _orderings(rows):
    """(n orderings judged, n same direction, n reversed resolved, list of flips)."""
    n = same = rev = 0
    flips = []
    for name, per in rows:
        for o, x in per.items():
            n += 1
            same += bool(x.get("same_direction"))
            if not x.get("same_direction"):
                flips.append(f"{name}:{o}")
            v, bv = x.get("verdict"), x.get("base_verdict")
            if v and bv and v.endswith("lower") and bv.endswith("lower") and v != bv:
                rev += 1
    return n, same, rev, flips


def variants():
    m = {}
    d = J("robustness_mech_SDEC.json")
    if d and d.get("variants"):
        acc, rows = {}, []
        for name, per_t in d["variants"].items():
            tag = EVAR.get(name)
            if not tag:
                continue
            for t, r in per_t.items():
                for a, ch in (r.get("change_rel") or {}).items():
                    k = f"{t}{ATAG[a]}"
                    for y, Y in (("warp", "Warp"), ("du", "Du"), ("eps", "Eps")):
                        if ch.get(y) is not None:
                            m[f"MvEnc{tag}{Y}{k}"] = spct(ch[y], 1)
                            acc.setdefault((tag, Y), []).append(ch[y])
                rows.append((f"{name}@{t}", r.get("orderings") or {}))
        for (tag, Y), v in acc.items():
            m[f"MvEnc{tag}{Y}Lo"], m[f"MvEnc{tag}{Y}Hi"] = rng(v, spct, 1)
        n, same, rev, flips = _orderings(rows)
        m["MvEncOrderN"], m["MvEncOrderSame"] = str(n), str(same)
        m["MvEncOrderRev"] = str(rev)
        m["MvEncFlips"] = str(len(flips))
    b = J("robustness_B.json")
    if b and b.get("variants"):
        rows = [(name, r.get("orderings") or {}) for name, r in b["variants"].items()]
        n, same, rev, flips = _orderings(rows)
        m["MvCoolBVariants"] = str(len(b["variants"]))
        m["MvCoolBOrderN"], m["MvCoolBOrderSame"] = str(n), str(same)
        m["MvCoolBOrderRev"] = str(rev)
        m["MvCoolBFlips"] = str(len(flips))
        mx = []
        for name, r in b["variants"].items():
            for a, ch in (r.get("change_rel") or {}).items():
                mx += [abs(ch[y]) for y in ("warp", "du") if ch.get(y) is not None]
        m["MvCoolBChangeMax"] = pct(max(mx), 1) if mx else NA
    return m


# ------------------------------------------------------------------ joint-response screen
#: groups of tcpmt_mech_joint_screen -> macro tag
SGROUP = {"S0_A": "Map", "SDEC_new_A": "New", "S0_B": "CoolB", "SDEC_mech_A": "Enc",
          "SDEC_mech_B": "Enc", "board_A": "Bd", "board_B": "Bd"}


def _eps_orderings(groups, keys, pairs=None):
    """(n judged, n same direction, n resolved reversals, n withdrawn, n pending) over the
    joint-response orderings of the named groups."""
    n = same = rev = wd = pend = 0
    for g in keys:
        for name, r in (groups.get(g) or {}).items():
            for o, x in (r.get("orderings") or {}).items():
                if pairs and o not in pairs:
                    continue
                n += 1
                same += bool(x.get("same_direction"))
                v, bv = x.get("verdict"), x.get("base_verdict")
                if v == "pending":
                    pend += 1
                elif v == "unresolved" and bv and bv.endswith("lower"):
                    wd += 1
                elif v and bv and v.endswith("lower") and bv.endswith("lower") and v != bv:
                    rev += 1
    return n, same, rev, wd, pend


def screen():
    """The joint response of the mechanical robustness variants (robustness_joint.json):
    screen size, validation, and per group the changes and the orderings under the rule."""
    d = J("robustness_joint.json")
    if not d or not d.get("variants"):
        return {}
    m = {"MvScrK": str(d["K"]), "MvScrNvar": str(d["n_variants"]),
         "MvScrNcomplete": str(d["n_complete"]), "MvScrMaxRank": str(d["max_rank_used"]),
         "MvScrNatLast": str(d["n_at_last_rank"])}
    m["MvScrNsolves"] = str(sum(v.get("n_sites") or 0 for v in d["variants"].values()))
    val = d.get("validation") or {}
    if val:
        m["MvScrValN"] = str(len(val))
        m["MvScrValInTopK"] = str(sum(1 for v in val.values() if v.get("max_in_top_k")))
        m["MvScrValAll"] = yn(d.get("validation_all_in_top_k"))
        rk = [v.get("max_rank_in_reference") for v in val.values()
              if v.get("max_rank_in_reference")]
        m["MvScrValRankMax"] = str(max(rk)) if rk else NA
        m["MvScrValSolved"] = str(sum(v.get("n_solved") or 0 for v in val.values()))
        m["MvScrValClosed"] = yn(all(v.get("closed") for v in val.values()))
        rat = [v.get("screen_over_full") for v in val.values() if v.get("screen_over_full")]
        m["MvScrValRatioMin"] = fx(min(rat), 3) if rat else NA
        lat = [v.get("n_lattice") for v in val.values() if v.get("n_lattice")]
        m["MvScrValLatticeLo"], m["MvScrValLatticeHi"] = (str(min(lat)), str(max(lat))) \
            if lat else (NA, NA)
    # changes against each variant's reference, per group (in %)
    acc = {}
    for key, v in d["variants"].items():
        if v.get("change_rel") is None:
            continue
        acc.setdefault(SGROUP.get(v["group"], v["group"]), []).append(v["change_rel"])
        if v["group"].startswith("board"):
            tag = BVAR.get(v["name"])
            if tag:
                k = f"{v['tier']}{ATAG[v['arch']]}"
                m[f"MvBd{tag}Eps{k}"] = spct(v["change_rel"], 1)
                acc.setdefault(f"Bd{tag}", []).append(v["change_rel"])
        if v["group"].startswith("SDEC_mech"):
            tag = EVAR.get(v["name"])
            if tag:
                k = f"{v['tier']}{ATAG[v['arch']]}"
                m[f"MvEncScr{tag}Eps{k}"] = spct(v["change_rel"], 1)
                acc.setdefault(f"EncScr{tag}", []).append(v["change_rel"])
    for tag, vals in acc.items():
        m[f"MvScr{tag}EpsLo"], m[f"MvScr{tag}EpsHi"] = rng(vals, spct, 1)
        m[f"MvScr{tag}EpsAbsMax"] = pct(max(abs(x) for x in vals), 1)
    g = d.get("groups") or {}
    for keys, tag in ((("board_A", "board_B"), "Bd"), (("SDEC_mech_A", "SDEC_mech_B"), "Enc"),
                      (("S0_B",), "CoolB"), (("S0_A",), "Map"), (("SDEC_new_A",), "New")):
        n, same, rev, wd, pend = _eps_orderings(g, keys)
        m[f"MvScr{tag}OrderN"], m[f"MvScr{tag}OrderSame"] = str(n), str(same)
        m[f"MvScr{tag}OrderRev"], m[f"MvScr{tag}OrderWd"] = str(rev), str(wd)
        m[f"MvScr{tag}OrderPend"] = str(pend)
        n2, same2, rev2, wd2, pend2 = _eps_orderings(g, keys, ("eps:Z1/Z2",))
        m[f"MvScr{tag}ZoneZtwoN"], m[f"MvScr{tag}ZoneZtwoSame"] = str(n2), str(same2)
        m[f"MvScr{tag}ZoneZtwoRev"], m[f"MvScr{tag}ZoneZtwoWd"] = str(rev2), str(wd2)
    # the verdict of every mapped decision's Z1/Z2 joint ordering against its group's baseline
    # (preserved / withdrawn / reversed / pending), e.g. MvScrVNewDieHotspotA
    digit = {str(i): w for i, w in enumerate(("Zero", "One", "Two", "Three", "Four", "Five",
                                               "Six", "Seven", "Eight", "Nine"))}

    def ctag(name):
        out = ""
        for part in name.replace("@", "_").split("_"):
            part = "".join(digit.get(ch, ch) for ch in part)
            out += part[:1].upper() + part[1:]
        return out
    for gk, gt in (("S0_A", "Map"), ("SDEC_new_A", "New"), ("S0_B", "CoolB"),
                   ("SDEC_mech_A", "EncA"), ("SDEC_mech_B", "EncB")):
        for name, r in (g.get(gk) or {}).items():
            o = (r.get("orderings") or {}).get("eps:Z1/Z2")
            if not o:
                continue
            v, bv = o.get("verdict"), o.get("base_verdict")
            m[f"MvScrV{gt}{ctag(name)}"] = ("pending" if v == "pending" else "preserved"
                                            if v == bv else "withdrawn" if v == "unresolved"
                                            else "reversed")
            m[f"MvScrG{gt}{ctag(name)}"] = fx(1e3 * (o["variant"][1] - o["variant"][0]), 2)
    # the clamp held through the cycle against the same screws without it (each case)
    eff = []
    for t in TIERS:
        for a in ARCHS:
            c = (d["variants"].get(f"SDEC_{t}_{a}__board_clamp_screws") or {}).get("d_eps")
            s_ = (d["variants"].get(f"SDEC_{t}_{a}__board_screws") or {}).get("d_eps")
            if c and s_:
                m[f"MvScrClampEff{t}{ATAG[a]}"] = spct(c / s_ - 1, 1)
                eff.append(c / s_ - 1)
    m["MvScrClampEffLo"], m["MvScrClampEffHi"] = rng(eff, spct, 1)
    return m


def macros():
    m = {}
    for f in (joint, window, critical, checks, interconnects, reflow, board, variants, screen):
        try:
            m.update(f())
        except Exception as e:                        # noqa: BLE001 -- keep building
            print(f"  WARNING mech macros {f.__name__}: {e}")
    return m


if __name__ == "__main__":
    for k, v in macros().items():
        print(k, v)
