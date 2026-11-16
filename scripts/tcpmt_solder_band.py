"""Task 3 -- sensitivity of the response to the averaging-band definition.

The corner-exclusion band of amendment 5 is a fixed physical width b = side/6 = 59.1 um.
Here b = side/8 (44.3 um), side/6 (production) and side/4 (88.6 um) at the Z1 and Z2 cooling-A
critical joints (= production S0), at L0 and L2. Only joint.BAND_FRAC changes (read by
build_joint at call time); joint, card, steps and extraction are the production ones, and the
mesh keeps breakpoints at the band edge, so every level averages the same core for a given b.

    python tcpmt_solder_band.py --run | --summarize
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcpmt_solder_common as C                                     # noqa: E402

STUDY = "band"
BANDS = {"side/8": 1.0 / 8.0, "side/6": 1.0 / 6.0, "side/4": 1.0 / 4.0}
LEVELS = ("L2", "L0")                                         # long runs first
CASES = {"Z1": "Z1_S0", "Z2": "Z2_S0"}


def tasks():
    t = []
    for lev in LEVELS:
        for lab, f in BANDS.items():
            for arch, case in CASES.items():
                c = C.critical(case)
                t.append(dict(study=STUDY, tag=f"A_{arch}_{lev}_b{lab.replace('/', '')}",
                              du_um=c["du_um"], T_C=c["T_C"], level=lev, band_frac=f,
                              meta={"arch": arch, "case": case, "band": lab}))
    return t


def summarize():
    recs = C.load_records(STUDY)
    prod = C.production_uncertainty()
    out = {"what": "averaging-band sensitivity at the cooling-A Z1 and Z2 critical joints "
                   "(task 3)",
           "settings": {"levels": list(LEVELS), "first_increment_s": C.INC0,
                        "split_steps": True, "n_cycles": 4},
           "bands": {}, "production_reference": {
               k: {"L0": prod[f"{k}_HV_S0"]["L0"],
                   "L2": None} for k in CASES}}
    ms = json.loads(C.MESH_STUDY.read_text())["cases"]
    for k in CASES:
        out["production_reference"][k]["L2"] = ms[f"{k}_HV_S0"]["levels"]["L2"][
            "d_peeq_per_cycle"]
    for lab, f in BANDS.items():
        row = {"band_frac": f, "band_um": f * C.JOINT.SOLDER_SIDE_UM,
               "core_side_um": (1 - 2 * f) * C.JOINT.SOLDER_SIDE_UM}
        for lev in LEVELS:
            v = {}
            for arch in CASES:
                r = recs.get(f"A_{arch}_{lev}_b{lab.replace('/', '')}") or {}
                v[arch] = {"d_eps": r.get("d_peeq_per_cycle"), "n_core": r.get("n_core"),
                           "error": r.get("error")}
            z1, z2 = v["Z1"]["d_eps"], v["Z2"]["d_eps"]
            v["Z1_lt_Z2"] = (z1 < z2) if (z1 and z2) else None
            v["gap_rel"] = (abs(z2 - z1) / max(z1, z2)) if (z1 and z2) else None
            v["ratio_Z2_over_Z1"] = (z2 / z1) if (z1 and z2) else None
            row[lev] = v
        out["bands"][lab] = row
    base = out["bands"]["side/6"]
    for lab, row in out["bands"].items():
        for lev in LEVELS:
            for arch in CASES:
                b0, x = base[lev][arch]["d_eps"], row[lev][arch]["d_eps"]
                row[lev][arch]["change_vs_production_band"] = ((x - b0) / b0
                                                              if (b0 and x) else None)
            for arch in CASES:
                a0, a2 = row["L0"][arch]["d_eps"], row["L2"][arch]["d_eps"]
                row.setdefault("L0_to_L2_change", {})[arch] = ((a2 - a0) / a0
                                                              if (a0 and a2) else None)
    flags = [row[lev]["Z1_lt_Z2"] for row in out["bands"].values() for lev in LEVELS]
    out["ranking_Z1_lt_Z2_holds_everywhere"] = all(flags) if None not in flags else None
    return out


def main():
    if "--run" in sys.argv:
        C.run_tasks(tasks())
    if "--summarize" in sys.argv:
        from tcpmt_solder_collect import merge
        s = summarize()
        merge("averaging_band", s)
        for lab, row in s["bands"].items():
            print(lab, {lev: (row[lev]["Z1"]["d_eps"], row[lev]["Z2"]["d_eps"],
                              row[lev]["Z1_lt_Z2"]) for lev in LEVELS})


if __name__ == "__main__":
    main()
