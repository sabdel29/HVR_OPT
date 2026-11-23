"""Material variants of the mechanics revision, from configs/tcpmt_mech (findings 7, 11).

  encapsulant (finding 7)  the out-of-cell converter fill (underfill_homog of the physical
                           builders) as a capillary underfill or a low-CTE mold compound WITH
                           its glass transition: E(T) logistic between the glassy and rubbery
                           moduli, the instantaneous CTE switching from alpha1 to alpha2 over
                           the same width, written as the SECANT CTE about the stress-free
                           temperature (*EXPANSION, ZERO=). Conductivity is untouched, so the
                           variants run on the converged fields (mechanics only).
  bga_card_local (11a)     the homogenised BGA layer from the LOCAL solder card -- E(T), nu
                           and CTE of tcpmt_mech_laws -- smeared by the ball area fraction,
                           instead of board.py's STAMP-2.5D values (E 20 GPa, 20.5 ppm/K).

Every number comes from the config or from the stack the builder assembled, so a tier card
merged into the stack flows through unchanged. The hooks are BUILD_HOOKS of
final_closure_physical_etm (applied after the builders' own material assignment).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import tcpmt_mech_laws as LAW                                       # noqa: E402


def _rows(a, b, s):
    n = int(round((b - a) / s)) + 1
    return [round(a + s * k, 6) for k in range(n)]


def encap_tables(v: dict, t_ref: float = 25.0, rows=None):
    """[(T, E)], [(T, alpha_secant)] of one encapsulant variant."""
    rows = rows or _rows(*LAW.cfg()["encapsulant"]["T_rows_C"])
    Eg, Er = float(v["E_g_MPa"]), float(v["E_r_MPa"])
    a1, a2 = float(v["alpha1_per_K"]), float(v["alpha2_per_K"])
    Tg, w = float(v["Tg_C"]), float(v["width_K"])

    def E(T):
        return Er + (Eg - Er) / (1.0 + math.exp((T - Tg) / w))

    def strain(T):                       # integral of the logistic instantaneous CTE
        sp = lambda t: w * math.log1p(math.exp((t - Tg) / w))      # noqa: E731
        return a1 * (T - t_ref) + (a2 - a1) * (sp(T) - sp(t_ref))

    def inst(T):
        return a1 + (a2 - a1) / (1.0 + math.exp(-(T - Tg) / w))
    sec = [(T, strain(T) / (T - t_ref) if abs(T - t_ref) > 1e-9 else inst(T)) for T in rows]
    return [(T, E(T)) for T in rows], sec


def encap_card(name: str, base: dict, t_ref: float = 25.0) -> dict:
    v = LAW.cfg()["encapsulant"]["variants"][name]
    E_T, cte_T = encap_tables(v, t_ref)
    c = dict(base)
    c.update({"status": "ASSUMPTION", "elastic_type": "iso",
              "E": {"value": dict(E_T)[min(dict(E_T), key=lambda T: abs(T - t_ref))],
                    "status": "ASSUMPTION"},
              "nu": {"value": float(v["nu"]), "status": "ASSUMPTION"},
              "cte": {"value": float(v["alpha1_per_K"]), "status": "ASSUMPTION"},
              "E_T": E_T, "cte_T": cte_T,
              "note": f"encapsulant variant {name}: {v['what']} ({v['source']})"})
    return c


def encap_hook(name: str):
    mat = LAW.cfg()["encapsulant"]["material"]

    def hook(m, st, tiles, _n=name):
        t_ref = st["structural_bc"]["t_ref"]["value"]
        st["materials"][mat] = encap_card(_n, st["materials"][mat], t_ref)
        n_el = int(sum(1 for x in m.elem_material if x == mat))
        return {"encapsulant_variant": _n, "encapsulant_material": mat,
                "encapsulant_elements": n_el}
    return hook


def bga_local_card(base: dict, t_ref: float = 25.0) -> dict:
    import board as BRD
    f = BRD.AREA_FRACTION
    rows = LAW.rows_C()
    c = dict(base)
    c.update({"status": "DERIVED", "elastic_type": "iso",
              "E": {"value": f * LAW.E_of_T(t_ref), "status": "DERIVED"},
              "nu": {"value": LAW.nu(), "status": "ASSUMPTION"},
              "cte": {"value": LAW.cte(), "status": "ASSUMPTION"},
              "E_T": [(T, f * LAW.E_of_T(T)) for T in rows],
              "note": "BGA layer from the local solder card (tcpmt_mech_laws), smeared by "
                      f"the ball area fraction {f:.5f}"})
    return c


def bga_local_hook():
    def hook(m, st, tiles):
        t_ref = st["structural_bc"]["t_ref"]["value"]
        old = st["materials"]["bga_homog"]
        st["materials"]["bga_homog"] = bga_local_card(old, t_ref)
        v = lambda x: x["value"] if isinstance(x, dict) else x       # noqa: E731
        return {"bga_card": "local solder card", "bga_E_25C_MPa":
                st["materials"]["bga_homog"]["E"]["value"], "bga_E_prod_MPa": v(old["E"]),
                "bga_cte": LAW.cte(), "bga_cte_prod": v(old["cte"])}
    return hook


def coarse_check(arch, names, scen="HV_S0"):
    """Mechanics-only check of material variants on the COARSE mesh (r11) against the
    coarse production case, on its stored converged field (the mesh-study work tree):
    a cheap reading of each variant's effect before the production-mesh campaign."""
    import json
    import os
    import numpy as np
    import final_closure_physical_etm as E
    import production_et as PE
    from hvr_scratch import path as scratch
    d = Path(os.environ.get("HVR_FC_WORK", "/home/beams0/SABDELZAHER/ETM_project/scratch/fc_etm")) \
        / f"{arch}_{scen}_h1.1"
    its = sorted(d.glob("et*"), key=lambda p: int(p.name[2:]))
    th = sorted(its[-1].glob("th_*.frd"), key=lambda p: int(p.stem.split("_")[1]))[-1]
    base = json.loads(E.case_path(arch, scen, 1.1, (1, 1)).read_text())
    out = {}
    for name in ["production"] + list(names):
        E.BUILD_HOOKS.clear()
        if name in LAW.cfg()["encapsulant"]["variants"]:
            E.BUILD_HOOKS.append(encap_hook(name))
        elif name == LAW.cfg()["bga_global"]["reconciled_variant"]:
            E.BUILD_HOOKS.append(bga_local_hook())
        m, mats, st, tiles, info = E.build(arch, 1.1, (1, 1))
        T = PE.ccxio.read_frd(th)["NDTEMP"][1:m.n_nodes + 1, 0]
        if abs(float(np.nanmax(T)) - base["thermal"]["T_max_C"]) > 1e-6:
            raise RuntimeError(f"{th} is not the converged coarse field of {arch}")
        me = E.mechanics(m, mats, st, T, scratch("mech_coarse", f"{arch}_{name}"), arch,
                         tiles, "", int(os.environ.get("FC_THREADS", "2")))
        c = me["joint_search"]["critical"]
        k = (me.get("interconnects") or {}).get("bga", {}).get("critical", {})
        out[name] = {"die_warpage_pv_um": me["die_warpage_pv_um"], "du_c_um": c["du_um"],
                     "site_mm": [c["x_mm"], c["y_mm"]], "du_def_xy_um": k.get("du_def_xy_um"),
                     "du_z_um": k.get("du_z_um"),
                     "interconnect_gamma": {n: v.get("gamma_max") for n, v in
                                            (me.get("interconnects") or {}).items()},
                     "decomposition_share": (me.get("decomposition_bga_critical") or {})
                     .get("share_along_du"), "materials": info, "wall_s": me["wall_s"]}
        print(arch, name, {kk: out[name][kk] for kk in ("die_warpage_pv_um", "du_c_um",
                                                          "du_def_xy_um")}, flush=True)
    E.BUILD_HOOKS.clear()
    f = LAW.TR / "coarse_variant_checks.json"
    d0 = json.loads(f.read_text()) if f.exists() else {}
    d0[arch] = out
    f.write_text(json.dumps(d0, indent=1, default=float) + "\n")
    return out


def judge_B():
    """Finding 8: the cooling-B rows of the robustness map. For every mechanics-only variant
    run on the cooling-B fields (final_closure_sensitivity NAME@B -> ..__NAME__B.json), the
    change of each mechanical output against the cooling-B base case, and whether every
    pairwise cooling-B ordering keeps its direction and stays resolved under THE comparison
    rule of the revision (TCPMT round 3, tcpmt_resolution: |D + beta| > U95(D)); the cooling-B
    cases have no ladder of their own, so the laddered reference pair's beta and U are
    transferred provisionally when the case passes the transfer check (identical mesh), else the
    verdict is pending."""
    import itertools
    import json
    import final_closure_sensitivity as S
    import tcpmt_uncertainty as TU
    sens = S.OUT
    pairs = TU.reference_pairs()
    archs = ("Z1", "Z2", "Z3")
    mesh = {}
    base = {}
    for a in archs:
        try:
            b, _frd, name = S.thermal_base(a, "B")
        except Exception as e:                    # recorded, never silent
            base[a] = {"error": str(e)[-200:]}
            continue
        me = b.get("mechanics") or {}
        k = ((me.get("interconnects") or {}).get("bga") or {}).get("critical") or {}
        mesh[("__base__", a)] = TU.mesh_signature(b)
        base[a] = {"case": name, "warp": me.get("die_warpage_pv_um"),
                   "du": (me.get("joint_search") or {}).get("critical", {}).get("du_um"),
                   "du_def": k.get("du_def_xy_um"),
                   "eps": (b.get("local") or {}).get("d_peeq_per_cycle")}
    rows = {}
    for f in sorted(sens.glob("etm_*_HV_S0__*__B.json")):
        c = json.loads(f.read_text())
        a, name = c["arch"], c["variant"]["name"].split("@")[0]
        me = c.get("mechanics") or {}
        k = ((me.get("interconnects") or {}).get("bga") or {}).get("critical") or {}
        mesh[(name, a)] = TU.mesh_signature(c)
        rows.setdefault(name, {})[a] = {
            "warp": me.get("die_warpage_pv_um"),
            "du": (me.get("joint_search") or {}).get("critical", {}).get("du_um"),
            "du_def": k.get("du_def_xy_um"), "eps": (c.get("local") or {}).get("d_peeq_per_cycle")}
    # an architecture the variant does not touch (registered for others only, e.g. the attach
    # cards of Z2) keeps its cooling-B base: unchanged by definition, as the reference map does
    for name, per in rows.items():
        for a in archs:
            if a not in per and a not in S.VARIANTS[name]["archs"] and "error" not in base.get(a, {}):
                per[a] = {y: base[a].get(y) for y in ("warp", "du", "du_def", "eps")}
                mesh[(name, a)] = mesh.get(("__base__", a))
    out = {"what": "cooling-B robustness of the mechanical orderings (finding 8)",
           "base": base, "variants": {}}
    for name, per in rows.items():
        res = {"values": per, "change_rel": {}, "orderings": {}}
        for a, v in per.items():
            res["change_rel"][a] = {y: (v[y] / base[a][y] - 1) if (v.get(y) and (base.get(a) or {})
                                                                    .get(y)) else None
                                    for y in ("warp", "du", "du_def", "eps")}
        for y, uy in (("warp", "warp"), ("du", "du"), ("du_def", "du"), ("eps", None)):
            for a, b in itertools.combinations(archs, 2):
                va, vb = (per.get(a) or {}).get(y), (per.get(b) or {}).get(y)
                ba, bb = (base.get(a) or {}).get(y), (base.get(b) or {}).get(y)
                if None in (va, vb, ba, bb):
                    continue
                gap = abs(va - vb) / max(abs(va), abs(vb))
                j = (TU.variant_judgement(a, b, uy, va, vb, mesh.get((name, a)),
                                          mesh.get((name, b)), pairs) if uy else None)
                # the cooling-B base itself under the same transferred U: the row's baseline
                jb = (TU.variant_judgement(a, b, uy, ba, bb, mesh.get(("__base__", a)),
                                           mesh.get(("__base__", b)), pairs) if uy else None)
                res["orderings"][f"{y}:{a}/{b}"] = {
                    "base_lower": a if ba < bb else b, "variant_lower": a if va < vb else b,
                    "same_direction": (ba < bb) == (va < vb), "gap_rel": gap,
                    "verdict": j["verdict"] if j else None,
                    "base_verdict": jb["verdict"] if jb else None,
                    "resolved": j.get("resolved") if j else None,
                    "U95": j.get("U95") if j else None,
                    "provisional": j.get("provisional") if j else None}
        out["variants"][name] = res
    out["rule"] = TU.RULE.RULE
    import tcpmt_mech_production as MP
    out["inputs_sha1"] = MP.inputs_sha1(
        sorted(sens.glob("etm_*_HV_S0__*__B.json"))
        + [S.case_file(a, LAW.cfg()["cooling_B_base"][a]) for a in archs]
        + [LAW.TR / "uncertainty.json"])
    f = LAW.TR / "robustness_B.json"
    f.write_text(json.dumps(out, indent=1, default=float) + "\n")
    return out


def _mech_values(c):
    """warp, du (all-site search), du_def (deforming BGA du) and the local response of a
    case or a mechanics-only variant."""
    me = (c or {}).get("mechanics") or {}
    k = ((me.get("interconnects") or {}).get("bga") or {}).get("critical") or {}
    return {"warp": me.get("die_warpage_pv_um"),
            "du": (me.get("joint_search") or {}).get("critical", {}).get("du_um"),
            "du_def": k.get("du_def_xy_um"),
            "eps": ((c or {}).get("local") or {}).get("d_peeq_per_cycle")}


def judge_state(state="SDEC"):
    """TCPMT round 3: the mechanics-only variants run on the compared cases of a state
    (final_closure_sensitivity --state: NAME on the cooling-A case, NAME@B on the cooling-B
    case), each against ITS OWN base case: the change of every mechanical output, and whether
    every pairwise ordering of that cooling keeps its direction and stays resolved under THE
    rule (|D + beta| > U95), with the beta and U95 of the state's own laddered comparison
    (uncertainty.json, the production state's ladders) transferred provisionally when the
    variant's mesh is the base case's. -> tcpmt_revision/robustness_mech_<state>.json"""
    import itertools
    import json
    import final_closure_sensitivity as S
    import tcpmt_cases as TC
    import tcpmt_uncertainty as TU
    import tcpmt_mech_production as MP
    scen = TC.SCEN[state]
    unc = json.loads((LAW.TR / "uncertainty.json").read_text()) \
        if (LAW.TR / "uncertainty.json").is_file() else {}
    cmp_ = {(r["tier"], r["a"], r["b"], r["output"]): r for r in unc.get("comparisons") or []}
    base, bmesh, ins = {}, {}, {}
    for t in TC.TIERS:
        for a in TC.ARCHS:
            p = TC.case_path(state, t, a)
            if p is None:
                continue
            c = json.loads(p.read_text())
            base.setdefault(t, {})[a] = dict(_mech_values(c), case=p.name)
            bmesh[(t, a)] = TU.mesh_signature(c)
            ins.update(MP.inputs_sha1([p]))
    rows = {}
    for f in sorted(S.OUT.glob(f"etm_*_{scen}__*.json")):
        c = json.loads(f.read_text())
        v = c.get("variant") or {}
        if v.get("kind") != "mech" or not c.get("state"):
            continue
        name, t = S.split_tier(v["name"])
        rows.setdefault(name, {}).setdefault(t, {})[c["arch"]] = dict(
            _mech_values(c), mesh=TU.mesh_signature(c), file=f.name)
        ins.update(MP.inputs_sha1([f]))
    ins.update(MP.inputs_sha1([LAW.TR / "uncertainty.json"]))   # the pairs' beta and U95
    out = {"what": "mechanics-only variants on the compared cases of the state, against their "
                   "own base cases (findings 6-8, 11a)", "state": state, "base": base,
           "variants": {}, "rule": TU.RULE.RULE, "inputs_sha1": ins,
           "u_source": "uncertainty.json comparisons of the state (own ladders), transferred "
                       "provisionally on the identical mesh"}

    def ref(t, a, b, y):
        r = cmp_.get((t, a, b, y))
        if r:
            return r.get("bias") or 0.0, r.get("U95"), r.get("verdict"), r.get("lower")
        r = cmp_.get((t, b, a, y))
        if r:
            return -(r.get("bias") or 0.0), r.get("U95"), r.get("verdict"), r.get("lower")
        return None
    for name, per_t in rows.items():
        res = {}
        for t, per in per_t.items():
            bt = base.get(t) or {}
            r = {"values": per, "change_rel": {}, "orderings": {}}
            for a, vv in per.items():
                r["change_rel"][a] = {y: (vv[y] / bt[a][y] - 1) if (vv.get(y) is not None and
                                                                    (bt.get(a) or {}).get(y))
                                      else None for y in ("warp", "du", "du_def", "eps")}
            for y in ("warp", "du", "du_def", "eps"):
                for a, b in itertools.combinations(TC.ARCHS, 2):
                    va, vb = (per.get(a) or {}).get(y), (per.get(b) or {}).get(y)
                    ba, bb = (bt.get(a) or {}).get(y), (bt.get(b) or {}).get(y)
                    if None in (va, vb, ba, bb):
                        continue
                    rec = {"base_lower": a if ba < bb else b, "variant_lower": a if va < vb else b,
                           "same_direction": (ba < bb) == (va < vb),
                           "gap_rel": abs(va - vb) / max(abs(va), abs(vb)),
                           "base": [ba, bb], "variant": [va, vb]}
                    rf = ref(t, a, b, y) if y in ("warp", "du") else None
                    same_mesh = (per[a].get("mesh") == bmesh.get((t, a))
                                 and per[b].get("mesh") == bmesh.get((t, b)))
                    if rf and rf[1] is not None and same_mesh:
                        j = TU.RULE.judge(vb - va, rf[0], rf[1])
                        rec.update({"verdict": TU.RULE.verdict_label(j["resolved"],
                                                                     j["D_corrected"], a, b),
                                    "resolved": j["resolved"], "U95": rf[1], "bias": rf[0],
                                    "base_verdict": (f"{rf[3]} lower" if rf[2] == "resolved"
                                                     and rf[3] else "unresolved"),
                                    "provisional": True})
                    elif rf:
                        rec.update({"verdict": "pending", "resolved": None,
                                    "note": "variant mesh differs from the base case's"})
                    r["orderings"][f"{y}:{a}/{b}"] = rec
            res[t] = r
        out["variants"][name] = res
    f = LAW.TR / f"robustness_mech_{state}.json"
    f.write_text(json.dumps(out, indent=1, default=float) + "\n")
    return out


def register(VARIANTS: dict, apply_hook):
    """Add the round-3 variants to final_closure_sensitivity.VARIANTS. apply_hook(fn)
    appends a BUILD_HOOK in the variant's process."""
    cfg = LAW.cfg()
    for name, v in cfg["encapsulant"]["variants"].items():
        VARIANTS[name] = dict(kind="mech", archs=("Z1", "Z2", "Z3"),
                              apply=(lambda n=name: apply_hook(encap_hook(n))),
                              gates=["mat.encapsulant_card"],
                              nature="declared range (encapsulant class, finding 7)",
                              what=f"out-of-cell encapsulant: {v['what']}")
    VARIANTS[cfg["bga_global"]["reconciled_variant"]] = dict(
        kind="mech", archs=("Z1", "Z2", "Z3"), apply=lambda: apply_hook(bga_local_hook()),
        gates=["mat.bga_card_consistency"], nature="model-form check (finding 11a)",
        what="homogenised BGA layer from the local solder card E(T), nu, CTE")


if __name__ == "__main__":
    # python tcpmt_mech_variants.py coarse ARCH VARIANT [...]
    if sys.argv[1:2] == ["coarse"]:
        coarse_check(sys.argv[2], sys.argv[3:])
    elif sys.argv[1:2] == ["judgeB"]:            # python tcpmt_mech_variants.py judgeB
        import json
        print(json.dumps({k: v["orderings"] for k, v in judge_B()["variants"].items()},
                         indent=1, default=float)[:3000])
    elif sys.argv[1:2] == ["judge-state"]:       # python tcpmt_mech_variants.py judge-state [SDEC]
        import json
        d = judge_state(sys.argv[2] if len(sys.argv) > 2 else "SDEC")
        print(json.dumps({k: {t: {o: (x.get("verdict"), x.get("base_verdict"))
                                  for o, x in r["orderings"].items()}
                              for t, r in v.items()} for k, v in d["variants"].items()},
                         indent=1, default=float)[:4000])
