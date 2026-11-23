"""Findings 2, 3 and 11b -- checks of the v2 local model at the six tier joints.

  chain    attribution from the round-2 model to v2, one change at a time:
             R2      legacy card, legacy BC, STEP loading          (round-2 production)
             ramp    legacy card, legacy BC, 3-s ramps
             law     production law, legacy BC, 3-s ramps
             uz      production law, u_z released to the global du_z
             v2      production law, full global kinematics        (v2 production)
           plus 'v2_step' (v2 with STEP loading) to isolate the ramp under the new law
  dwell    v2 at dwell 60 / 900 s (300 s is v2), and ramp 30 s
  element  C3D8 (v2) against C3D8I and C3D8R at the cooling-A Z1 joint
  mesh     L1 / L2 / L3 against L0 at the cooling-A Z1 and Z3 joints
  cycles   8 cycles against 4 (the zero-yield laws carry no hardening drift)
  layers   finding 4: the critical fine-pitch joint of each architecture (Z1 die-converter
           microbump, Z2 Cu pillar, Z3 100-um bump) with the v2 model and its own geometry

    python tcpmt_mech_local_checks.py --run [GROUP ...]
    python tcpmt_mech_local_checks.py --summarize  -> research/tcpmt_revision/solder_local_checks.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcpmt_mech_law_band as LB                                    # noqa: E402
import tcpmt_mech_submodel as SUB                                   # noqa: E402
import tcpmt_mech_kinematics as KIN                                 # noqa: E402
import tcpmt_mech_laws as LAW                                       # noqa: E402

import tcpmt_mech_production as MP                                 # noqa: E402

#: TCPMT round 3 (campaign): the joints of the local model's state (tcpmt_mech_law_band.joints:
#: the production state's compared cases by default)
STATE = MP.LOCAL_STATE
_SFX = "" if STATE == "SDEC" else f"_{STATE}"
STUDY = "checks" + _SFX
OUT = LAW.TR / f"solder_local_checks{_SFX}.json"
CHAIN = {"R2": dict(law="legacy", bc="legacy", ramp_s=0.0),
         "ramp": dict(law="legacy", bc="legacy"),
         "law": dict(bc="legacy"),
         "uz": dict(bc="uz"),
         "v2": dict(),
         # a STEP load on a zero-yield card meets the full elastic spike: the first increment
         # must start at 1e-9 s (round-2 constitutive study: 1e-6 s fails, 1e-8 s runs)
         "v2_step": dict(ramp_s=0.0, legacy_inc0=1e-9)}
DWELL = {f"dwell{d:g}": dict(dwell_s=d) for d in LAW.cfg()["local"]["dwell_sensitivity_s"]
         if abs(d - LAW.cfg()["local"]["dwell_s"]) > 1e-9}
DWELL.update({f"ramp{r:g}": dict(ramp_s=r) for r in LAW.cfg()["local"]["ramp_sensitivity_s"]
              if abs(r - LAW.cfg()["local"]["ramp_s"]) > 1e-9})
ELEMENT = {"C3D8I": dict(element="C3D8I"), "C3D8R": dict(element="C3D8R")}
MESH = {"L1": dict(level="L1"), "L2": dict(level="L2"), "L3": dict(level="L3")}
CYCLES = {"N8": dict(n_cyc=8)}
#: the mesh check at every compared joint (each joint's own L0 -> L3 change is its numerical U,
#: tcpmt_uncertainty.local_u_v2); round 2 checked the cooling-A Z1 and Z3 joints only
GROUPS = {"chain": (CHAIN, None), "dwell": (DWELL, None), "element": (ELEMENT, ("A_Z1",)),
          "mesh": (MESH, ("A_Z1", "A_Z3") if STATE == "round2" else None),
          "cycles": (CYCLES, None)}
#: finding 4: the fine-pitch layer and its geometry per architecture, at the cooling-A case
#: (and, for a campaign state, at the cooling-B case: key 'B_<arch>')
_FINE = {"Z1": ("interface", "microbump"), "Z2": ("conv_attach_vr_substrate", "z2_pillar"),
         "Z3": ("z3_attach_vr_pcb", "z3_bump")}
if STATE == "round2":
    LAYERS = {"Z1": ("Z1_S0", "interface", "microbump"),
              "Z2": ("Z2_S0", "conv_attach_vr_substrate", "z2_pillar"),
              "Z3": (("A_Z3land", "A_Z3"), "z3_attach_vr_pcb", "z3_bump")}
else:
    LAYERS = {(a if t == "A" else f"B_{a}"): (MP.label(STATE, t, a), *_FINE[a])
              for t in ("A", "B") for a in ("Z1", "Z2", "Z3")}


def tasks(groups):
    js = LB.joints()
    out = []
    for g in groups:
        if g == "layers":
            out += layer_tasks()
            continue
        variants, only = GROUPS[g]
        for lab, case, k, basis in js:
            if only and lab not in only:
                continue
            for v, kw in variants.items():
                out.append(dict(study=STUDY, tag=f"{lab}_{v}", kin=k,
                                meta={"group": g, "joint": lab, "case": case, "variant": v},
                                **kw))
    return out


def layer_tasks():
    out = []
    for arch, (cases, layer, geom) in LAYERS.items():
        case = next((c for c in (cases if isinstance(cases, tuple) else (cases,))
                     if KIN.load_kinematics(c)), None)
        if not case:
            continue
        ic = KIN.load_kinematics(case)["interconnects"].get(layer) or {}
        crit = ic.get("critical")
        if not crit:
            continue
        out.append(dict(study=STUDY, tag=f"{arch}_{layer}_crit", kin=crit, geometry=geom,
                        meta={"group": "layers", "arch": arch, "case": case, "layer": layer,
                              "label": ic.get("label"), "gamma": crit["gamma"]}))
        # the same joint driven by the BGA-style legacy transfer, for the BC effect at scale
        out.append(dict(study=STUDY, tag=f"{arch}_{layer}_crit_uz", kin=crit, geometry=geom,
                        bc="uz", meta={"group": "layers", "arch": arch, "case": case,
                                       "layer": layer, "variant": "uz"}))
        # the joint at the layer's maximum shear-strain site when that is another site
        cs = ic.get("critical_by_shear_strain")
        if cs and (abs(cs["x_mm"] - crit["x_mm"]) > 1e-9 or abs(cs["y_mm"] - crit["y_mm"]) > 1e-9):
            out.append(dict(study=STUDY, tag=f"{arch}_{layer}_critdef", kin=cs, geometry=geom,
                            meta={"group": "layers", "arch": arch, "case": case,
                                  "layer": layer, "variant": "max shear strain",
                                  "gamma_def": cs.get("gamma_def")}))
    return out


def summarize():
    recs = SUB.load_records(STUDY)
    band = SUB.load_records(LB.STUDY)
    prod = LAW.solder_cfg()["production_law"]
    out = {"what": "v2 local-model checks (findings 2, 3, 4, 11b)",
           "production_law": prod, "groups": {}}
    # the v2 baseline of every joint is the law band's last production-law iteration
    cards = json.loads(LAW.CARDS.read_text()) if LAW.CARDS.is_file() else {}
    n_it = (cards.get("laws", {}).get(prod) or {}).get("n_iterations")
    base = {}
    for lab, case, k, basis in LB.joints():
        r = recs.get(f"{lab}_v2") or (band.get(f"{lab}_{prod}_it{n_it - 1}") if n_it else None)
        base[lab] = (r or {}).get("d_peeq_per_cycle")
    out["v2_baseline"] = base
    for g, (variants, only) in GROUPS.items():
        rows = {}
        for lab, b in base.items():
            if only and lab not in only:
                continue
            rows[lab] = {}
            for v in variants:
                r = recs.get(f"{lab}_{v}") or {}
                d = r.get("d_peeq_per_cycle")
                rows[lab][v] = {"d_eps": d, "rel_to_v2": (d / b - 1) if (d and b) else None,
                                "per_cycle": r.get("per_cycle"), "error": r.get("error"),
                                "wall_s": r.get("wall_s"),
                                "peak_vm_MPa": max((r.get("stress") or {}).get(p, {})
                                                   .get("peak_vm_MPa", 0) for p in ("hot", "cold"))
                                if r.get("stress") else None}
        out["groups"][g] = rows
    # the round-2 published values for reference
    out["round2_L0"] = {f"{t}_{a}": v for t, d in {"A": {"Z1": 5.80, "Z2": 8.03, "Z3": 13.47},
                                                    "B": {"Z1": 2.08, "Z2": 4.15, "Z3": 2.52}}
                        .items() for a, v in d.items()}
    lay = {}
    for arch, (cases, layer, geom) in LAYERS.items():
        r = recs.get(f"{arch}_{layer}_crit") or {}
        ru = recs.get(f"{arch}_{layer}_crit_uz") or {}
        rd = recs.get(f"{arch}_{layer}_critdef") or {}
        case = cases if isinstance(cases, str) else next(
            (c for c in cases if KIN.load_kinematics(c)), None)
        kin = KIN.load_kinematics(case) if case else None
        ic = ((kin or {}).get("interconnects") or {}).get(layer) or {}
        lay[arch] = {"layer": layer, "geometry": geom, "case": case,
                     "label": ic.get("label"), "h_um": ic.get("h_um"),
                     "gamma": (ic.get("critical") or {}).get("gamma"),
                     "gamma_def": (ic.get("critical") or {}).get("gamma_def"),
                     "d_eps": r.get("d_peeq_per_cycle"),
                     "d_eps_uz": ru.get("d_peeq_per_cycle"),
                     "d_eps_max_shear_strain_site": rd.get("d_peeq_per_cycle"),
                     "kin": r.get("kin"),
                     "T_C": r.get("T_hot_C"), "error": r.get("error"),
                     "n_elem": r.get("n_elem"), "unit": r.get("unit"),
                     "per_cycle": r.get("per_cycle")}
    out["fine_pitch_joints"] = lay
    out["inputs_sha1"] = {}
    for lab, case, *_ in LB.joints():
        out["inputs_sha1"].update((KIN.load_kinematics(case) or {}).get("inputs_sha1") or {})
    if LAW.CARDS.is_file():
        out["inputs_sha1"][str(LAW.CARDS.resolve())] = MP.sha1(LAW.CARDS)
    OUT.write_text(json.dumps(out, indent=1, default=float) + "\n")
    return out


def main():
    groups = [a for a in sys.argv[1:] if a in GROUPS or a == "layers"] or (
        list(GROUPS) + ["layers"])
    if "--run" in sys.argv:
        SUB.run_tasks(tasks(groups))
    if "--summarize" in sys.argv:
        s = summarize()
        print(json.dumps({g: {j: {v: (round(x["d_eps"], 7) if x["d_eps"] else None)
                                  for v, x in r.items()} for j, r in rows.items()}
                          for g, rows in s["groups"].items()}, indent=1))
        print(json.dumps(s["fine_pitch_joints"], indent=1, default=float)[:2000])


if __name__ == "__main__":
    main()
