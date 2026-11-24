"""Averaging-band study of the v2 local model at the critical joints of the production state.

The joint response is the inelastic strain per cycle averaged over the solder core: the
solder less a corner-exclusion band of fixed physical width b (local_mesh_policy amendment 5,
b = side/6 = 59.1 um, with mesh breakpoints at the band edge so that every mesh level averages
the same core). The band is a numerical device, so its width is varied here as in the round-2
study (tcpmt_solder_band.py: side/8, side/6, side/4 at L0 and L2 on the legacy model), now with
the PRODUCTION local model (tcpmt_mech_submodel: full cut-boundary kinematics of both pad
faces, ramped loads, the production law at its converged window) at the critical joint of
every compared case (the production law's maximum-response site over the BGA lattice,
tcpmt_mech_law_band.joints). Only band_frac changes; joint, card, schedule and extraction are
the production ones.

    python tcpmt_mech_band_study.py --run | --summarize
        -> research/tcpmt_revision/solder_band_study_v2.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcpmt_mech_law_band as LB                                    # noqa: E402
import tcpmt_mech_laws as LAW                                       # noqa: E402
import tcpmt_mech_production as MP                                  # noqa: E402
import tcpmt_mech_submodel as SUB                                   # noqa: E402

STUDY = "band_v2"
OUT = LAW.TR / "solder_band_study_v2.json"
BANDS = {"side/8": 1.0 / 8.0, "side/6": 1.0 / 6.0, "side/4": 1.0 / 4.0}
LEVELS = ("L2", "L0")                                      # long solves first
PRODUCTION_BAND = "side/6"


def _tag(lab, lev, band):
    return f"{lab}_{lev}_b{band.split('/')[1]}"


def tasks():
    law = LAW.solder_cfg()["production_law"]
    out = []
    for lev in LEVELS:
        for band, f in BANDS.items():
            for lab, case, k, basis in LB.joints(law=law):
                out.append(dict(study=STUDY, tag=_tag(lab, lev, band), kin=k, law=law,
                                level=lev, band_frac=f,
                                meta={"joint": lab, "case": case, "band": band, "level": lev,
                                      "site_basis": basis}))
    return out


def _order(v):
    if not v or None in v.values():
        return None
    return " < ".join(sorted(v, key=v.get))


def summarize():
    law = LAW.solder_cfg()["production_law"]
    recs = SUB.load_records(STUDY)
    js = LB.joints(law=law)
    side_um = float(SUB.geometry("bga")["solder_d"]) * (3.141592653589793 / 4) ** 0.5
    out = {"what": "averaging-band sensitivity of the v2 local model at the critical joints of "
                   "the production state (band widths of the round-2 study, production law at "
                   "its converged window)",
           "production_law": law, "production_band": PRODUCTION_BAND,
           "window": LAW.stored_window(law)[0], "levels": list(LEVELS),
           "solder_side_um": side_um, "bands": {}, "joints": {}}
    for band, f in BANDS.items():
        out["bands"][band] = {"band_frac": f, "band_um": f * side_um,
                              "core_side_um": (1 - 2 * f) * side_um}
    changes = []
    for lab, case, k, basis in js:
        row = {"case": case, "site_mm": [k["x_mm"], k["y_mm"]], "site_basis": basis,
               "T_C": SUB.site_temperature(k), "levels": {}}
        for lev in LEVELS:
            vals = {}
            for band in BANDS:
                r = recs.get(_tag(lab, lev, band)) or {}
                vals[band] = {"d_eps": r.get("d_peeq_per_cycle"), "error": r.get("error"),
                              "n_core": r.get("n_core"), "card_sha": r.get("card_sha"),
                              "wall_s": r.get("wall_s")}
            b0 = vals[PRODUCTION_BAND]["d_eps"]
            for band, v in vals.items():
                v["change_vs_production_band"] = ((v["d_eps"] - b0) / b0
                                                  if (v["d_eps"] and b0) else None)
                if band != PRODUCTION_BAND and v["change_vs_production_band"] is not None:
                    changes.append(v["change_vs_production_band"])
            row["levels"][lev] = vals
        out["joints"][lab] = row
    # the orderings of the compared integrations under every band and level, per cooling
    rk, same = {}, True
    for lev in LEVELS:
        for band in BANDS:
            for t in ("A", "B"):
                v = {a: ((out["joints"].get(f"{t}_{a}") or {}).get("levels", {}).get(lev, {})
                         .get(band, {}).get("d_eps")) for a in ("Z1", "Z2", "Z3")
                     if f"{t}_{a}" in out["joints"]}
                rk[f"{lev}:{band}:{t}"] = _order(v)
    for t in ("A", "B"):
        base = rk.get(f"L0:{PRODUCTION_BAND}:{t}")
        same &= all(r == base for k_, r in rk.items() if k_.endswith(f":{t}"))
    out["orderings"] = rk
    out["orderings_hold_everywhere"] = bool(same) and None not in rk.values()
    out["change_range_rel"] = [min(changes), max(changes)] if changes else None
    out["n_solves"] = sum(1 for lab in out["joints"] for lev in LEVELS for b in BANDS
                          if out["joints"][lab]["levels"][lev][b]["d_eps"] is not None)
    out["n_expected"] = len(js) * len(LEVELS) * len(BANDS)
    out["complete"] = out["n_solves"] == out["n_expected"]
    out["inputs_sha1"] = {}
    for lab, case, *_ in js:
        from tcpmt_mech_kinematics import load_kinematics
        out["inputs_sha1"].update((load_kinematics(case) or {}).get("inputs_sha1") or {})
    if LAW.CARDS.is_file():
        out["inputs_sha1"][str(LAW.CARDS.resolve())] = MP.sha1(LAW.CARDS)
    OUT.write_text(json.dumps(out, indent=1, default=float) + "\n")
    return out


def main():
    if "--run" in sys.argv:
        SUB.run_tasks(tasks())
    if "--summarize" in sys.argv:
        s = summarize()
        for lab, r in s["joints"].items():
            print(lab, {lev: {b: (round(v["d_eps"], 7) if v["d_eps"] else None,
                                  None if v["change_vs_production_band"] is None
                                  else round(100 * v["change_vs_production_band"], 2))
                              for b, v in d.items()} for lev, d in r["levels"].items()})
        print("orderings hold:", s["orderings_hold_everywhere"], "change range:",
              s["change_range_rel"], "complete:", s["complete"])


if __name__ == "__main__":
    main()
