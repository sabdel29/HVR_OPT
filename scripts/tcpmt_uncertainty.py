"""Uncertainty of every compared output, per case, and the comparison rule (TCPMT review MC13;
round 3: ONE rule for every comparison, scripts/tcpmt_resolution.py).

RULE: a difference D = y_b - y_a between two cases is RESOLVED when its bias-corrected value
exceeds the uncertainty of the difference at about 95 % coverage, |D + beta_D| > U95(D).
  beta_D, U_mesh(D)  GCI-type estimate on D's own nested ladder (r11 / r21 / r31): the observed
                     order where the ladder is asymptotic (Fs = 1.25), otherwise Fs = 3 with the
                     order limited to [0.5, 2] (tcpmt_resolution.gci); the signed bias moves the
                     production-mesh difference to its extrapolated value
  U_tt(D)            the through-thickness split r11 -> r12 of D (two rungs, Fs = 3)
  U_et               the E-T stop of each case (0.1 % of the loss, 0.25 K)
  U_ref(D)           the matched-reference agreement of the solver on the difference (0.13 % of
                     a temperature difference, 0.43 % of a displacement difference)
  U95(D) = sqrt(U_mesh^2 + U_tt^2 + U_et,a^2 + U_et,b^2 + U_ref^2)
The local joint response: U95(D) = sqrt(U_loc,a^2 + U_loc,b^2) (each joint's numerical U: local
mesh L0 -> L3 and cycle count, in quadrature), evaluated under EVERY law of the solder-law band:
resolved only when resolved with one sign under all laws, law-conditional when only under the
production law.
NO TRANSFER WITHOUT A CHECK: a compared case without a ladder of its own is marked; its
comparisons use the laddered reference pair (the S0 cooling-A production ladders of the same
integrations) only as a PROVISIONAL estimate when both cases pass the transfer check (identical
production mesh; the r11 step check once their r11 rung exists), else they are PENDING; the
ladder runs the campaign must add are listed (ladder_runs_needed). MODEL-FORM uncertainty
(material cards, boundaries, omitted physics) is not added to U: both integrations are rerun under
each declared alternative (the robustness map); a resolved ranking that a declared alternative
reverses is CONDITIONAL on that decision.

Per-case values (Table IV): the production value, its signed bias beta and its U95 (the same GCI
on the case's own ladder, relative to the value -- to the rise above the inlet for temperatures --
when transferred from the reference ladder of the same integration).

    python tcpmt_uncertainty.py   -> research/tcpmt_revision/uncertainty.json,
                                     manuscript_v2/tab_uncertainty.tex
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import tcpmt_resolution as RULE                                     # noqa: E402

FC = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "final_closure"
SENS = FC / "sensitivity"
TR = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision"
OUT = TR / "uncertainty.json"
TAB = Path(os.environ.get("ETM_RESULTS_ROOT") or R) / "manuscript_v2" / "tab_uncertainty.tex"
ATAG = {"Z1": "Zone", "Z2": "Ztwo", "Z3": "Zthree"}
YTAG = {"P": "Ploss", "T": "Tmax", "warp": "Warp", "du": "Du", "eps": "Eps"}
OBS = ("P", "T", "warp", "du")
ARCHS = ("Z1", "Z2", "Z3")
U_ET = {"P_rel": 1e-3, "T_K": 0.25}
U_REF = {"T_rel": 0.0013, "mech_rel": 0.0043}
T_IN = 25.0
RUNGS = ("r11", "r21", "r31", "r12")
PRODUCTION_RUNG = "r21"
#: the laddered reference lineage: the S0 production cases of each integration (cooling A)
REF_SCEN = "HV_S0"
PAIRS = [("A", "Z1", "Z2"), ("A", "Z1", "Z3"), ("B", "Z2", "Z1"), ("B", "Z3", "Z1"),
         ("B", "Z2", "Z3")]


def J(p):
    p = Path(p) if p else None
    return json.loads(p.read_text()) if p and p.is_file() else None


def obs(c):
    if not c:
        return None
    me = c.get("mechanics") or {}
    cr = (me.get("joint_search") or {}).get("critical") or {}
    return {"P": c["P_loss_w"], "T": c["thermal"]["T_max_C"],
            "warp": me.get("die_warpage_pv_um"), "du": cr.get("du_um"), "Tj": cr.get("T_C")}


def mesh_signature(c):
    """(n_elems, n_nodes, h_xy, refine) of a solved case (the transfer check's mesh)."""
    if not c:
        return None
    th = c.get("thermal") or {}
    return (th.get("n_elems"), th.get("n_nodes"), c.get("h_xy_mm"),
            tuple(c.get("refine") or (2, 1)))


# ------------------------------------------------------------------ ladders
def ladder_files(path):
    """{rung: Path} of a production-mesh case file: the production lineage keeps its rungs
    beside it (etm_<arch>_<scen>_h1.1[_rXZ].json), a variant case under sensitivity/ladder
    (<stem>_rXZ.json, final_closure_sensitivity.variant_file)."""
    p = Path(path)
    if "__" not in p.stem:
        m = re.match(r"^(etm_.+_h[0-9.]+?)(_r\d\d)?$", p.stem)
        stem = m.group(1) if m else p.stem
        return {r: p.parent / f"{stem}{'' if r == 'r11' else '_' + r}.json" for r in RUNGS}
    return {r: (p if r == PRODUCTION_RUNG else p.parent / "ladder" / f"{p.stem}_{r}.json")
            for r in RUNGS}


def ladder_values(path):
    """{rung: obs or None} and whether the case has its own three-rung ladder. A compared case
    resolved to a fallback file (tcpmt_cases: the first implemented-decoupling run of Z1-A)
    takes its other rungs from the name the campaign writes (the expected file)."""
    files = ladder_files(path)
    alt = _EXPECTED.get(Path(path).name)
    if alt is not None:
        files = {**ladder_files(alt), PRODUCTION_RUNG: Path(path)}
    vals = {r: obs(J(f)) for r, f in files.items()}
    own = all(vals[r] is not None for r in ("r11", "r21", "r31"))
    return vals, own, files


def reference_path(arch):
    """The laddered reference case of an integration: its S0 case under cooling A
    (tcpmt_cases: the production-boundary file etm_<arch>_HV_S0_h1.1_r21.json for Z1/Z2; Z3
    ALWAYS the coupled land-side case, never the superseded uncoupled Z3 file)."""
    return _TC.expected_path("S0", "A", arch)


def _base(y, v):
    return (v - T_IN) if y == "T" else v


def _u_et(y, v):
    return U_ET["P_rel"] * abs(v) if y == "P" else (U_ET["T_K"] if y == "T" else 0.0)


def _u_ref_rel(y):
    return U_REF["T_rel"] if y == "T" else (U_REF["mech_rel"] if y in ("warp", "du") else 0.0)


# ------------------------------------------------------------------ per case
def ladder_estimate(vals, y):
    """GCI and through-thickness estimate of output y from a ladder's values."""
    g = RULE.gci(*(None if vals.get(r) is None else vals[r].get(y)
                   for r in ("r11", "r21", "r31")))
    v11, v12 = ((vals.get(r) or {}).get(y) for r in ("r11", "r12"))
    tt = RULE.gci_two_rung(v11, v12)
    return g, tt


def case_estimate(path, arch):
    """Per-output bias and U95 of one compared case: its own ladder, or -- PROVISIONAL -- the
    relative estimate of its integration's reference ladder when the transfer check passes."""
    c = J(path)
    vals, own, files = ladder_values(path)
    me = obs(c)
    ref_p = reference_path(arch)
    ref_vals, ref_own, _ = ladder_values(ref_p)
    chk = None
    if not own:
        chk = RULE.transfer_check(mesh_signature(c), mesh_signature(J(ref_p)))
    out = {"file": Path(path).name, "own_ladder": own,
           "missing_rungs": [r for r in ("r11", "r31", "r12") if vals.get(r) is None],
           "ladder_files": {r: f.name for r, f in files.items()},
           "transfer": None if own else {"reference": ref_p.name, **chk}, "outputs": {}}
    for y in OBS:
        v = (me or {}).get(y)
        if v is None:
            continue
        base = abs(_base(y, v))
        u_et, u_ref = _u_et(y, v), _u_ref_rel(y) * base
        if own:
            g, tt = ladder_estimate(vals, y)
            basis = "own ladder"
            beta, u_mesh = g["beta"], g["U"]
            beta_tt, u_tt = (tt["beta"], tt["U"]) if tt else (0.0, None)
            cls, p_obs, fs = g["class"], g["p_obs"], g["Fs"]
            prov = False
        elif chk["ok"] and ref_own:
            g, tt = ladder_estimate(ref_vals, y)
            rb = abs(_base(y, ref_vals["r21"][y])) or 1.0
            scale = base / rb                      # relative transfer
            beta, u_mesh = g["beta"] * scale, g["U"] * scale
            beta_tt, u_tt = ((tt["beta"] * scale, tt["U"] * scale) if tt else (0.0, None))
            cls, p_obs, fs = g["class"], g["p_obs"], g["Fs"]
            basis, prov = f"transferred from {ref_p.name} ({chk['status']})", True
        else:
            out["outputs"][y] = {"value": v, "bias": None, "U95": None, "verdict_basis":
                                 "pending: no ladder of its own and no checked transfer"}
            continue
        u95 = RULE.quad(u_mesh, u_tt, u_et, u_ref)
        out["outputs"][y] = {
            "value": v, "bias": beta + beta_tt, "bias_mesh": beta, "bias_tt": beta_tt,
            "value_corrected": v + beta + beta_tt, "U_mesh": u_mesh, "U_tt": u_tt,
            "U_et": u_et, "U_ref": u_ref, "U95": u95, "class": cls, "p_obs": p_obs, "Fs": fs,
            "U95_rel": u95 / base if base else None, "basis": basis, "provisional": prov}
    return out


# ------------------------------------------------------------------ differences
def pair_estimate(pa, pb, a, b, y):
    """beta_D and the discretization terms of D = y_b - y_a: the paired ladder when both cases
    have their own; else the reference pair's estimate (PROVISIONAL, checked transfer)."""
    va, own_a, _ = ladder_values(pa)
    vb, own_b, _ = ladder_values(pb)
    def both(xa, xb, r):
        return (xa.get(r) or {}).get(y) is not None and (xb.get(r) or {}).get(y) is not None
    if own_a and own_b and all(both(va, vb, r) for r in ("r11", "r21", "r31")):
        dv = {r: ({y: vb[r][y] - va[r][y]} if both(va, vb, r) else None) for r in RUNGS}
        g, tt = ladder_estimate(dv, y)
        return {"basis": "own ladders", "provisional": False, "gci": g, "tt": tt,
                "tt_basis": "own r12" if tt else "no r12 rung", "reference": None}
    ra, rb = reference_path(a), reference_path(b)
    rva, rown_a, _ = ladder_values(ra)
    rvb, rown_b, _ = ladder_values(rb)
    ca = (RULE.transfer_check(mesh_signature(J(pa)), mesh_signature(J(ra))) if not own_a
          else {"ok": True, "status": "own ladder"})
    cb = (RULE.transfer_check(mesh_signature(J(pb)), mesh_signature(J(rb))) if not own_b
          else {"ok": True, "status": "own ladder"})
    ref = f"{rb.name} - {ra.name}"
    if not (rown_a and rown_b and ca["ok"] and cb["ok"]):
        return {"basis": "pending", "provisional": None, "gci": None, "tt": None,
                "reference": ref, "checks": {a: ca["status"], b: cb["status"]}}
    dv = {r: ({y: rvb[r][y] - rva[r][y]} if both(rva, rvb, r) else None) for r in RUNGS}
    g, tt = ladder_estimate(dv, y)
    tt_basis = "reference r12"
    if tt is None:                         # an integration without r12 (Z3): the largest
        alt = []                           # through-thickness term of the laddered pairs
        for x, z in (("Z1", "Z2"), ("Z1", "Z3"), ("Z2", "Z3")):
            xa, _o, _ = ladder_values(reference_path(x))
            xb, _o2, _ = ladder_values(reference_path(z))
            if all((xa.get(r) or {}).get(y) is not None and (xb.get(r) or {}).get(y) is not None
                   for r in ("r11", "r12")):
                alt.append(RULE.gci_two_rung(xb["r11"][y] - xa["r11"][y],
                                             xb["r12"][y] - xa["r12"][y]))
        tt = max(alt, key=lambda t: t["U"]) if alt else None
        tt_basis = "no r12 rung for this pair: largest laddered pair's (provisional)"
    return {"basis": f"transferred from the reference pair {ref}", "provisional": True,
            "gci": g, "tt": tt, "tt_basis": tt_basis, "reference": ref,
            "checks": {a: ca["status"], b: cb["status"]}}


def compare(t, a, b, y, pa, pb, ya, yb):
    """One comparison under the rule (global outputs)."""
    d = yb - ya
    est = pair_estimate(pa, pb, a, b, y)
    row = {"tier": t, "a": a, "b": b, "output": y, "y_a": ya, "y_b": yb, "D": d,
           "basis": est["basis"], "provisional": est["provisional"],
           "reference": est.get("reference"), "transfer_checks": est.get("checks")}
    if est["gci"] is None:
        row.update({"bias": None, "D_corrected": None, "U95": None, "U_D": None,
                    "verdict": RULE.PENDING, "resolved": None, "lower": None, "ratio": None})
        return row
    g, tt = est["gci"], est["tt"]
    beta = g["beta"] + (tt["beta"] if tt else 0.0)
    u_mesh, u_tt = g["U"], (tt["U"] if tt else None)
    u_et_a, u_et_b = _u_et(y, ya), _u_et(y, yb)
    u_ref = _u_ref_rel(y) * abs(d)
    u95 = RULE.quad(u_mesh, u_tt, u_et_a, u_et_b, u_ref)
    j = RULE.judge(d, beta, u95)
    row.update({"bias": beta, "bias_mesh": g["beta"], "bias_tt": tt["beta"] if tt else 0.0,
                "D_corrected": j["D_corrected"], "U95": u95, "U_D": u95,
                "components": {"mesh": u_mesh, "tt": u_tt, "et_a": u_et_a, "et_b": u_et_b,
                               "ref": u_ref},
                "ladder_class": g["class"], "p_obs": g["p_obs"], "p": g["p"], "Fs": g["Fs"],
                "tt_basis": est.get("tt_basis"), "ratio": j["ratio"],
                "resolved": j["resolved"],
                "verdict": RULE.RESOLVED if j["resolved"] else RULE.NOT_RESOLVED,
                "lower": RULE.lower_of(a, b, j["D_corrected"])})
    return row


#: review round 2: the compared cases of each cooling from tcpmt_cases -- the production state
#: (implemented decoupling) by default, TCPMT_UNC_STATE=S0 for the reference
import tcpmt_cases as _TC                                           # noqa: E402
UNC_STATE = os.environ.get("TCPMT_UNC_STATE", _TC.PRODUCTION_STATE)
TIERS = {t: {a: p for a, p in row.items() if p is not None}
         for t, row in _TC.table(UNC_STATE).items()}
#: resolved file name -> the expected (campaign) file, where they differ (ladder_values)
_EXPECTED = {p.name: _TC.expected_path(UNC_STATE, t, a)
             for t, row in TIERS.items() for a, p in row.items()
             if p.name != _TC.expected_path(UNC_STATE, t, a).name}
#: the local solder responses were solved on the S0 tier cases: they enter the comparisons of the
#: S0 state only, until the study is rerun on the production cases
EPS_STATE = "S0"
#: TCPMT round 3: the local responses are ONLY those of the design in force, from the results
#: root (the v2 law band, else the campaign's solder studies); the round-2 (49-cell) tier L0
#: values once used as a fallback here (EPS_L0) never stand in -- a joint without a response
#: of its own is pending


def local_u_v2():
    """TCPMT round 3: the v2 local model. Value = the production law in solder_law_band.json;
    numerical U of each joint = its own L0 -> L3 change (else the largest over the checked
    joints: provisional) and its 4 -> 8 cycle change, in quadrature; the law band is part of
    the joint-response resolution (tcpmt_resolution.law_band)."""
    band = J(TR / "solder_law_band.json")
    if not band or not band.get("band"):
        return None
    chk = (J(TR / "solder_local_checks.json") or {}).get("groups", {})
    mesh_own = {lab: abs(r["L3"]["rel_to_v2"]) for lab, r in (chk.get("mesh") or {}).items()
                if (r.get("L3") or {}).get("rel_to_v2") is not None}
    u_mesh_max = max(mesh_own.values()) if mesh_own else None
    eps, u_t, law, own = {"A": {}, "B": {}}, {}, {}, {}
    for lab, b in band["band"].items():
        t, a = lab.split("_")
        if not b.get("complete"):
            continue
        eps[t][a] = 1e3 * b["production"]
        cyc = ((chk.get("cycles") or {}).get(lab) or {}).get("N8", {}).get("rel_to_v2")
        um = mesh_own.get(lab, u_mesh_max)
        u_t[(t, a)] = RULE.quad(um, cyc)
        own[(t, a)] = lab in mesh_own
        law[(t, a)] = {"U_law_rel": b["U_law_rel"], "values_x1e3": {
            k: (1e3 * v if v is not None else None) for k, v in b["values"].items()}}
    basis = ("v2 local model, production law " + band["production_law"] + " (4-cycle L0; U = "
             "own L0->L3 mesh change, else the largest checked joint's, and the 4->8 cycle "
             "change, in quadrature; law band in the resolution)")
    return eps, u_t, law, basis, band, own


def local_u_solder_studies():
    """The campaign's local solder studies (tcpmt_solder_*: the critical joints of the S0 tier
    cases, 48-cycle stabilized L0 responses, solder_studies.json; Z3 at the coupled land side,
    solder_z3land.json): value = the stabilized response, U = mesh + time + cycle + card grid
    (U_stab_num); own = the joint's own pass-5 mesh study. None when the studies have not run."""
    ss = J(TR / "solder_studies.json")
    st = ((ss or {}).get("stabilization") or {}).get("cases") or {}
    if not st:
        return None
    eps, u_t, own = {"A": {}, "B": {}}, {}, {}
    for lab, v in st.items():
        t, a = lab.split("_")
        if v.get("stabilised") is None:
            continue
        eps.setdefault(t, {})[a] = 1e3 * v["stabilised"]
        u_t[(t, a)] = v.get("U_stab_num")
        own[(t, a)] = str(v.get("U_basis") or "").startswith("own")
    zl = J(TR / "solder_z3land.json")              # Z3 with the coupled land side
    for t, v in ((zl or {}).get("cases") or {}).items():
        if v.get("stabilised") is not None:
            eps.setdefault(t, {})["Z3"] = 1e3 * v["stabilised"]
            if v.get("U_stab_num") is not None:
                u_t[(t, "Z3")] = v["U_stab_num"]
    return eps, u_t, own, "stabilized L0 (48 cycles; U = mesh + time + cycle + card grid)"


def local_u():
    """(eps, U_rel per (tier, arch), own-mesh flags, basis, band or None): the v2 law band of
    the results root, else the campaign's solder studies, else none (every joint pending)."""
    v2 = local_u_v2()
    if v2 is not None:                        # a joint the band has not solved stays pending
        eps, u_t, law, basis, band, own = v2
        return eps, u_t, own, basis, band
    ss = local_u_solder_studies()
    if ss is not None:
        eps, u_t, own, basis = ss
        return eps, u_t, own, basis, None
    return ({"A": {}, "B": {}}, {}, {},
            "none: no local responses of the design in force in the results root (neither "
            "solder_law_band.json nor solder_studies.json)", None)


def compare_eps(t, a, b, eps, u_t, own, band):
    """The joint response under the rule and the law band."""
    ya, yb = eps.get(t, {}).get(a), eps.get(t, {}).get(b)
    if ya is None or yb is None:
        return None
    ua, ub = u_t.get((t, a)), u_t.get((t, b))
    row = {"tier": t, "a": a, "b": b, "output": "eps", "y_a": ya, "y_b": yb, "D": yb - ya,
           "bias": 0.0, "D_corrected": yb - ya,
           "basis": ("own local mesh ladders" if own.get((t, a)) and own.get((t, b)) else
                     "local mesh U of the checked joints (provisional for a joint without "
                     "its own L0->L3)"),
           "provisional": not (own.get((t, a)) and own.get((t, b)))}
    if ua is None or ub is None:
        row.update({"U95": None, "U_D": None, "verdict": RULE.PENDING, "resolved": None,
                    "lower": None, "ratio": None})
        return row
    u95 = RULE.quad(ua * ya, ub * yb)
    j = RULE.judge(yb - ya, 0.0, u95)
    row.update({"U95": u95, "U_D": u95, "ratio": j["ratio"], "lower": RULE.lower_of(a, b, yb - ya)})
    if band:
        per = {}
        for law_name, v in band["responses"].items():
            la, lb = v.get(f"{t}_{a}"), v.get(f"{t}_{b}")
            if la is None or lb is None:
                continue
            la, lb = 1e3 * la, 1e3 * lb
            per[law_name] = (lb - la, RULE.quad(ua * la, ub * lb))
        lb_ = RULE.law_band(per, band["production_law"])
        row["law_band"] = {k: {kk: lb_["per_law"][k][kk] for kk in ("D", "U95", "resolved")}
                           for k in lb_["per_law"]}
        row["verdict"] = lb_["verdict"]
        row["resolved"] = lb_["verdict"] == RULE.RESOLVED
        row["conditional_on_law"] = lb_["verdict"] == RULE.LAW_CONDITIONAL
    else:
        row["verdict"] = RULE.RESOLVED if j["resolved"] else RULE.NOT_RESOLVED
        row["resolved"] = j["resolved"]
    return row


# ------------------------------------------------------------------ reference pairs
def reference_pairs():
    """The laddered reference pairs (S0 production, cooling A): beta_D and the discretization
    U of every output of every pair of integrations (b - a), the basis of every provisional
    transfer -- also read by final_closure_classB and tcpmt_mech_variants.judge_B."""
    out = {}
    for a, b in (("Z1", "Z2"), ("Z1", "Z3"), ("Z2", "Z3")):
        pa, pb = reference_path(a), reference_path(b)
        va, oa, _ = ladder_values(pa)
        vb, ob, _ = ladder_values(pb)
        rec = {"a": a, "b": b, "files": [pa.name, pb.name], "own_ladders": oa and ob,
               "mesh": {a: mesh_signature(J(pa)), b: mesh_signature(J(pb))}, "outputs": {}}
        for y in OBS:
            est = pair_estimate(pa, pb, a, b, y)
            if est["gci"] is None:
                continue
            g, tt = est["gci"], est["tt"]
            rec["outputs"][y] = {"D": vb["r21"][y] - va["r21"][y],
                                 "D_rungs": {r: (vb[r][y] - va[r][y]) if (va.get(r) and vb.get(r)
                                             and va[r].get(y) is not None and vb[r].get(y)
                                             is not None) else None for r in RUNGS},
                                 "class": g["class"], "p_obs": g["p_obs"], "p": g["p"],
                                 "Fs": g["Fs"], "beta_mesh": g["beta"], "U_mesh": g["U"],
                                 "beta_tt": tt["beta"] if tt else 0.0,
                                 "U_tt": tt["U"] if tt else None,
                                 "tt_basis": est.get("tt_basis")}
        out[f"{a}/{b}"] = rec
    return out


def reference_pair(a, b, y, pairs=None):
    """beta and discretization U of y_b - y_a from the laddered reference pairs (sign-oriented),
    or None."""
    pairs = pairs if pairs is not None else reference_pairs()
    key, sgn = (f"{a}/{b}", 1.0) if f"{a}/{b}" in pairs else (f"{b}/{a}", -1.0)
    rec = ((pairs.get(key) or {}).get("outputs") or {}).get(y)
    if not rec:
        return None
    return {"beta": sgn * (rec["beta_mesh"] + rec["beta_tt"]), "U_mesh": rec["U_mesh"],
            "U_tt": rec["U_tt"], "class": rec["class"], "reference": key}


def variant_judgement(a, b, y, ya, yb, mesh_a, mesh_b, pairs=None, rung_a=None, rung_b=None):
    """A robustness variant pair (no ladder of its own) under the rule: the reference pair's
    beta / U_mesh / U_tt (absolute) transferred provisionally when both cases pass the transfer
    check, the variant's own E-T stop and reference terms. Returns the judge record with
    'verdict' in the robustness-map vocabulary ('Z1 lower', 'unresolved', 'pending')."""
    ref = reference_pair(a, b, y, pairs)

    def check(mesh, arch):
        if mesh == "reference":            # the laddered reference case itself (unchanged)
            return {"ok": True, "status": "the reference case itself (own ladder)"}
        return RULE.transfer_check(mesh, mesh_signature(J(reference_path(arch))))
    ra, rb = check(mesh_a, a), check(mesh_b, b)
    rec = {"transfer_checks": {a: ra["status"], b: rb["status"]},
           "reference": ref["reference"] if ref else None}
    if ref is None or not (ra["ok"] and rb["ok"]) or ya is None or yb is None:
        rec.update({"verdict": RULE.PENDING, "resolved": None, "provisional": None,
                    "U95": None, "D_corrected": None})
        return rec
    d = yb - ya
    u95 = RULE.quad(ref["U_mesh"], ref["U_tt"], _u_et(y, ya), _u_et(y, yb),
                    _u_ref_rel(y) * abs(d))
    j = RULE.judge(d, ref["beta"], u95)
    rec.update(j)
    rec.update({"provisional": True,
                "verdict": RULE.verdict_label(j["resolved"], j["D_corrected"], a, b)})
    return rec


# ------------------------------------------------------------------ campaign list
def run_command(state, tier, arch, rung):
    """The command that produces rung `rung` of the compared case (state, tier, arch)."""
    scen = _TC.SCEN[state]
    base = _TC.COOLING_BASE[(arch, tier)]
    if state == _TC.PRODUCTION_STATE:
        return f"python scripts/tcpmt_review_variants.py sdec {arch} {tier} {rung}"
    if base is None:
        return (f"python scripts/final_closure_physical_etm.py "
                f"'{arch}:{scen}:1.1:{rung}:ITERATIVE CHOLESKY:2'")
    if base.startswith("z3_land"):
        return f"python scripts/tcpmt_z3land_variants.py run {base} {rung}"
    return f"python scripts/tcpmt_review_variants.py state {arch} {tier} {scen} {rung}"


def ladder_runs_needed(state=None):
    """Every rung the campaign must add so that each compared case of `state` has a ladder of
    its own (r11, r31: the in-plane ladder; r12: the through-thickness split)."""
    state = state or UNC_STATE
    out = []
    for t in _TC.TIERS:
        for a in ARCHS:
            p = _TC.expected_path(state, t, a)
            files = ladder_files(p)
            for r in ("r11", "r31", "r12"):
                if not files[r].is_file():
                    out.append({"state": state, "tier": t, "arch": a, "rung": r,
                                "file": _TC.rel(files[r]),
                                "command": run_command(state, t, a, r)})
    return out


# ------------------------------------------------------------------ assembly
def assemble():
    cases = {t: {a: case_estimate(p, a) for a, p in v.items()} for t, v in TIERS.items()}
    refs = {a: case_estimate(reference_path(a), a) for a in ARCHS
            if reference_path(a).is_file()}
    return cases, refs


def comparisons(cases):
    eps, u_t, own, eps_basis, band = local_u()
    vals = {t: {a: obs(J(f)) for a, f in v.items()} for t, v in TIERS.items()}
    res = []
    for t, a, b in PAIRS:
        pa, pb = TIERS.get(t, {}).get(a), TIERS.get(t, {}).get(b)
        for y in OBS:
            if not (pa and pb):
                continue
            ya, yb = (vals[t][a] or {}).get(y), (vals[t][b] or {}).get(y)
            if ya is None or yb is None:
                continue
            res.append(compare(t, a, b, y, pa, pb, ya, yb))
        if UNC_STATE == EPS_STATE:
            r = compare_eps(t, a, b, eps, u_t, own, band)
            if r:
                res.append(r)
    return res, eps, u_t, eps_basis, band


CODE = {RULE.RESOLVED: "R", RULE.NOT_RESOLVED: "--", RULE.LAW_CONDITIONAL: "L",
        RULE.PENDING: "P"}


def _cell(o):
    if not o or o.get("U95") is None:
        return "--"
    u, b = o["U95"], o["bias"]
    f = (lambda x: f"{x:+.2f}") if abs(u) < 10 else (lambda x: f"{x:+.1f}")
    g = (lambda x: f"{x:.2f}") if abs(u) < 10 else (lambda x: f"{x:.1f}")
    return f"{f(b)}/{g(u)}" + (r"$^\dagger$" if o.get("provisional") else "")


def latex(cases, res, eps, u_t):
    names = {"P": "Loss (W)", "T": "Peak temp.\\ (K)", "warp": "Die warpage (\\textmu m)",
             "du": "$\\du$ (\\textmu m)", "eps": "$\\deps$ ($10^{-3}$/cycle)"}
    L = [r"% GENERATED by scripts/tcpmt_uncertainty.py -- do not edit",
         r"\begin{table}[!t]",
         r"\caption{Signed production-mesh bias $\beta$ and numerical uncertainty $U_{95}$ of each "
         r"compared output (" + {"S0": "S0", "SDEC": "implemented decoupling"}.get(
             UNC_STATE, UNC_STATE) + r", production mesh), and the comparisons they resolve: a "
         r"difference is resolved when $|D+\beta_D| > U_{95}(D)$.}",
         r"\label{tab:uncertainty}", r"\centering", r"\footnotesize",
         r"\setlength{\tabcolsep}{2.0pt}",
         r"\begin{tabular}{@{}lrrrrrr@{}}", r"\toprule",
         r" & \multicolumn{3}{c}{Cooling A: $\beta/U_{95}$} & "
         r"\multicolumn{3}{c}{Cooling B: $\beta/U_{95}$}\\",
         r"\cmidrule(lr){2-4}\cmidrule(l){5-7}",
         r"Output & Z1 & Z2 & Z3 & Z1 & Z2 & Z3 \\", r"\midrule"]
    for y in OBS:
        cells = [_cell((cases.get(t, {}).get(a) or {}).get("outputs", {}).get(y))
                 for t in ("A", "B") for a in ARCHS]
        L.append(f"{names[y]} & " + " & ".join(cells) + r" \\")
    if UNC_STATE == EPS_STATE:
        cells = []
        for t in ("A", "B"):
            for a in ARCHS:
                e, u = eps.get(t, {}).get(a), u_t.get((t, a))
                cells.append("--" if e is None or u is None else f"0/{u * e:.2f}")
        L.append(f"{names['eps']} & " + " & ".join(cells) + r" \\")
    L += [r"\midrule", r"\multicolumn{7}{@{}p{0.95\columnwidth}@{}}{\emph{Comparisons (lower "
          r"first). R: $|D+\beta_D|>U_{95}(D)$, $U_{95}$ of the difference ($\approx$95\,\%: GCI "
          r"with $F_s$ = 1.25 asymptotic, 3 otherwise; other terms in quadrature); L: resolved "
          r"under the production solder law only; --: not resolved; P: pending (no ladder); "
          r"$\dagger$: provisional, $U$ of the laddered S0 reference (own ladder pending).}}\\"]
    seen = {}
    for r in res:
        seen.setdefault((r["tier"], r["a"], r["b"]), []).append(r)
    for (t, a, b), rows in seen.items():
        s = "; ".join(f"{names[r['output']].split(' (')[0]} "
                      f"{r['lower'] or ''} {CODE[r['verdict']]}"
                      + (r"$^\dagger$" if r.get("provisional") else "") for r in rows)
        L.append(f"\\multicolumn{{7}}{{@{{}}p{{0.95\\columnwidth}}@{{}}}}{{{t}, {a}/{b}: {s}}}\\\\")
    L += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    return L


def relative_block(refs):
    """Per integration, the relative U95 components of its laddered reference (the old
    'relative' block's keys: mesh, tt, et, ref, total; read by the supplement, judge_B and the
    board study)."""
    rel = {}
    for a, c in refs.items():
        rel[a] = {}
        for y, o in c["outputs"].items():
            if o.get("U95") is None:
                continue
            base = abs(_base(y, o["value"])) or 1.0
            rel[a][y] = {"mesh": o["U_mesh"] / base, "tt": (o["U_tt"] or 0.0) / base,
                         "et": o["U_et"] / base, "ref": o["U_ref"] / base,
                         "total": o["U95"] / base, "bias_rel": o["bias"] / base,
                         "class": o["class"], "p_obs": o["p_obs"], "Fs": o["Fs"]}
    return rel


def main():
    cases, refs = assemble()
    res, eps, u_t, eps_basis, band = comparisons(cases)
    rel = relative_block(refs)
    U = {}
    for t, v in cases.items():
        for a, c in v.items():
            for y, o in c["outputs"].items():
                if o.get("U95") is not None:
                    U[f"{t}.{a}.{y}"] = o["U95"]
    if UNC_STATE == EPS_STATE:
        for t in ("A", "B"):
            for a in ARCHS:
                e, u = eps.get(t, {}).get(a), u_t.get((t, a))
                if e is not None and u is not None:
                    U[f"{t}.{a}.eps"] = u * e
    mac = {}
    for k, u in U.items():
        t, a, y = k.split(".")
        mac[f"U{t}{ATAG[a]}{YTAG[y]}"] = f"{u:.2f}"
    for t, v in cases.items():
        for a, c in v.items():
            for y, o in c["outputs"].items():
                if o.get("bias") is not None:
                    mac[f"Bias{t}{ATAG[a]}{YTAG[y]}"] = f"{o['bias']:+.2f}"
    for a in ARCHS:
        for y in OBS:
            if y in rel.get(a, {}):
                mac[f"Urel{ATAG[a]}{YTAG[y]}"] = f"{100 * rel[a][y]['total']:.2f}"
    for r in res:
        k = f"Res{r['tier']}{ATAG[r['a']]}{ATAG[r['b']]}{YTAG[r['output']]}"
        mac[k] = r["verdict"]
        mac[k + "Ratio"] = f"{r['ratio']:.1f}" if r.get("ratio") is not None else "--"
        mac[k + "Basis"] = ("provisional" if r.get("provisional") else
                            "pending" if r["verdict"] == RULE.PENDING else "own ladder")
    pairs = reference_pairs()
    out = {"rule": RULE.RULE, "rule_doc": RULE.__doc__.split("RULE:")[1].strip(),
           "coverage": RULE.COVERAGE, "state": UNC_STATE,
           "cases": cases, "reference_cases": refs, "reference_pairs": pairs,
           "relative": rel, "U": U, "eps_basis": eps_basis, "eps": eps,
           "eps_U_rel": {f"{t}.{a}": u for (t, a), u in u_t.items()},
           "comparisons": res, "ladder_runs_needed": ladder_runs_needed(),
           "macros": mac, "latex_supplement": latex(cases, res, eps, u_t)}
    if band is not None and UNC_STATE == EPS_STATE:
        out["eps_law_band"] = {k: v for k, v in band.get("band", {}).items()}
        out["eps_law_rankings"] = band.get("rankings")
        out["eps_law_rankings_hold"] = band.get("rankings_hold_across_laws")
    dst = OUT if UNC_STATE == _TC.PRODUCTION_STATE else OUT.with_name(f"uncertainty_{UNC_STATE}.json")
    dst.write_text(json.dumps(out, indent=1, default=float))
    TAB.write_text("\n".join(latex(cases, res, eps, u_t)) + "\n")
    for r in res:
        print(f"{r['tier']} {r['a']}/{r['b']} {r['output']:5s} D={r['D']:+8.3f} "
              f"bias={(r.get('bias') or 0):+7.3f} U95={(r.get('U95') or float('nan')):7.3f} "
              f"{r['verdict']}{' (provisional)' if r.get('provisional') else ''}")
    print(f"ladder runs needed: {len(out['ladder_runs_needed'])}")
    return out


if __name__ == "__main__":
    main()
