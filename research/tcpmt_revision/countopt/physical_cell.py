#!/usr/bin/env python3
"""Physical cell of a count-optimal candidate: cell side, tier heights and a realizable order.

Inputs are the DSE pick (candidate_dse.json) and the parts' own dimensions; nothing is fitted.

  cell side    sqrt of the synthesized cell area. The optimizer's area is the largest
               per-tier footprint, max(N A_hs, K A_ls, K A_L, (N-1) A_Cf), i.e. one component
               class per tier in the cell's shadow -- the same convention as the 49-cell
               production cell (5.61 mm2 = 3 x EPC2014C).
  heights      the selected parts are the production cell's parts, so the heights are the
               production config's (configs/phase0nx/z1_physical.yaml), whose GaN values are
               the datasheet mounted heights (research/DEVICE_GEOMETRY_AUDIT.md) and whose
               inductor value is the library part's height_um; the MLCC keeps the production
               BOUNDED 100-um nominal. The script refuses if a part differs.
  footprints   EPC Package(mm) column (EPC-Product-Table.csv), inductor and capacitor library
               footprints; the output capacitor is one capacitor of the selected part, as the
               production cell (routing.tile_layout: COUT has the capacitor footprint).
  order        every ordered assignment of the five classes (HS, LS, C_f, C_out, L) to tiers
               that meets the per-tier area budget (phase0mr3c/repartition_search.py) is checked
               against the realizability rule of fig_realizability.py: a vertical net that has
               to cross a whole tier needs a build-up microvia whose aspect ratio, crossed
               dielectric depth / 120 um, must not exceed 1; a net between adjacent tiers
               steps through one 10-um RDL (AR 10/120); components in one tier connect
               laterally. Validated on the 49-cell cell: 144 area-feasible assignments, worst
               AR 5.32 for the reference order and 0.83 for the repartitioned one (the paper's
               numbers).

Writes research/tcpmt_revision/countopt/physical_cell.json.
"""
from __future__ import annotations

import csv
import itertools
import json
import math
import re
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
R = HERE.parents[2]
OUT = HERE / "physical_cell.json"
D_VIA_UM, RDL_UM = 120.0, 10.0
CLASSES = ("gan_hs", "cap_fly", "gan_ls", "inductor", "cap_out")
#: vertical nets of one cell: the 48 V input enters from the bottom landing RDL, the 1 V
#: output leaves through the output RDL at the top (routing.nets plus the C_out terminal)
NETS = (("vin", "gan_hs", "VIN -> HS"), ("gan_hs", "cap_fly", "HS -> C_f"),
        ("gan_hs", "gan_ls", "HS -> LS"), ("gan_ls", "inductor", "SW -> L"),
        ("inductor", "out", "L -> out"), ("cap_out", "out", "C_out -> out"))


def epc_dims(part):
    for r in csv.DictReader((R / "Scalable_Integrated_VR" / "EPC-Product-Table.csv")
                            .open(encoding="utf-8-sig")):
        if r["PartNumber"].strip() == part:
            a, b = [float(x) for x in re.findall(r"\d+\.?\d*", r["Package(mm)"])[:2]]
            return {"package": r["Package(mm)"].strip(), "x_mm": a, "y_mm": b,
                    "area_mm2": a * b}
    raise KeyError(part)


def production_heights():
    """Tier heights of the production cell, keyed by component class, with the part each
    tier names (the config tier names carry the GaN part numbers)."""
    c = yaml.safe_load((R / "configs" / "phase0nx" / "z1_physical.yaml").read_text())
    h = {}
    for t in c["converter"]["tiers_from_substrate_upward"]:
        n = t["name"]
        if n.startswith("gan_hs_"):
            h["gan_hs"] = (float(t["um"]), n[len("gan_hs_"):], t.get("status"))
        elif n.startswith("gan_ls_"):
            h["gan_ls"] = (float(t["um"]), n[len("gan_ls_"):], t.get("status"))
        elif n == "flying_caps":
            h["cap_fly"] = (float(t["um"]), None, t.get("status"))
        elif n.startswith("inductor"):
            h["inductor"] = (float(t["um"]), None, t.get("status"))
    return h


def partitions(items, k):
    for assign in itertools.product(range(k), repeat=len(items)):
        if len(set(assign)) == k:
            yield [[c for c, a in zip(items, assign) if a == t] for t in range(k)]


def evaluate(tiers, H, A, n_of, cell_mm2):
    """Per-tier areas and heights, and the via AR of every net (planes 0..k: 0 the bottom
    landing RDL, k the output RDL; tier t sits between planes t-1 and t)."""
    areas = [sum(A[c] * n_of[c] for c in t) for t in tiers]
    hts = [max(H[c] for c in t) for t in tiers]
    k = len(tiers)
    tier_of = {c: i + 1 for i, t in enumerate(tiers) for c in t}
    nets = {}
    for a, b, label in NETS:
        if b == "out":
            t = tier_of[a]
            crossed = list(range(t + 1, k + 1))
        elif a == "vin":
            t = tier_of[b]
            crossed = list(range(1, t))
        else:
            ta, tb = sorted((tier_of[a], tier_of[b]))
            if ta == tb:
                nets[label] = {"kind": "lateral (same tier)", "depth_um": 0.0, "ar": 0.0}
                continue
            crossed = list(range(ta + 1, tb))
        if not crossed:
            nets[label] = {"kind": "adjacent tiers: one 10-um RDL step", "depth_um": 0.0,
                           "ar": RDL_UM / D_VIA_UM}
            continue
        depth = sum(hts[t - 1] for t in crossed) + (len(crossed) - 1) * RDL_UM
        nets[label] = {"kind": "build-up via across " + " + ".join(
            "/".join(tiers[t - 1]) for t in crossed), "depth_um": depth,
            "ar": depth / D_VIA_UM}
    worst = max(nets.items(), key=lambda kv: kv[1]["ar"])
    stack = sum(hts) + (k + 1) * RDL_UM            # bottom landing + interlayers + output
    return {"partition": " | ".join("+".join(t) for t in tiers), "n_tiers": k,
            "tier_area_mm2": [round(a, 6) for a in areas], "tier_um": hts,
            "area_ok": max(areas) <= cell_mm2 + 1e-9, "nets": nets,
            "worst_net": worst[0], "worst_ar": worst[1]["ar"],
            "realizable": worst[1]["ar"] <= 1.0 + 1e-12, "stack_um": stack,
            "hs_at_bottom": tiers[0] == ["gan_hs"] or "gan_hs" in tiers[0],
            "output_end_on_top": bool({"inductor", "cap_out"} & set(tiers[-1]))}


def study(rec, label):
    a = rec["topology"]
    N, K = a["N"], a["K"]
    hs, ls = rec["hs_device"], rec["ls_device"]
    ind, cap = rec["inductor"], rec["capacitor"]
    ph = production_heights()
    if (ph["gan_hs"][1], ph["gan_ls"][1]) != (hs["part_number"], ls["part_number"]):
        raise RuntimeError(f"{label}: GaN parts {hs['part_number']}/{ls['part_number']} are "
                           f"not the production parts; their heights must be sourced anew")
    if abs(ph["inductor"][0] - float(ind["height_um"])) > 1e-9:
        raise RuntimeError(f"{label}: inductor height {ind['height_um']} um is not the "
                           f"production tier's {ph['inductor'][0]} um")
    H = {"gan_hs": ph["gan_hs"][0], "gan_ls": ph["gan_ls"][0], "cap_fly": ph["cap_fly"][0],
         "cap_out": ph["cap_fly"][0], "inductor": float(ind["height_um"])}
    A = {"gan_hs": float(hs["footprint_mm2"]), "gan_ls": float(ls["footprint_mm2"]),
         "cap_fly": float(cap["footprint_mm2"]), "cap_out": float(cap["footprint_mm2"]),
         "inductor": float(ind["footprint_mm2"])}
    n_of = {"gan_hs": N, "gan_ls": K, "cap_fly": N - 1, "cap_out": 1, "inductor": K}
    cell = float(rec["area_mm2"])
    rows = []
    for k in range(1, 6):
        for tiers in partitions(list(CLASSES), k):
            r = evaluate(tiers, H, A, n_of, cell)
            if r["area_ok"]:
                rows.append(r)
    ok = [r for r in rows if r["realizable"]]
    cand = sorted([r for r in ok if r["hs_at_bottom"]],
                  key=lambda r: (r["worst_ar"], r["stack_um"], r["n_tiers"],
                                 sum(v["depth_um"] for v in r["nets"].values())))
    hs_d, ls_d = epc_dims(hs["part_number"]), epc_dims(ls["part_number"])
    return {
        "label": label, "M": rec["M"], "topology": a["label"],
        "cell_area_mm2": cell, "cell_side_mm": math.sqrt(cell),
        "parts": {"gan_hs": {**hs_d, "part": hs["part_number"], "per_cell": N,
                             "height_um": H["gan_hs"], "height_source":
                             "EPC2014C datasheet mounted height (DEVICE_GEOMETRY_AUDIT.md)"},
                  "gan_ls": {**ls_d, "part": ls["part_number"], "per_cell": K,
                             "height_um": H["gan_ls"], "height_source":
                             "EPC2057 datasheet: 518 die + 120 bump (DEVICE_GEOMETRY_AUDIT.md)"},
                  "inductor": {"part": ind["name"], "per_cell": K,
                               "area_mm2": A["inductor"], "height_um": H["inductor"],
                               "height_source": "library height_um (HVR_FULL_OPT_EPC_V2 "
                                                "INDUCTOR_LIBRARY; not in Ind_and_Cap_data.py)"},
                  "cap_fly": {"part": cap["name"], "per_cell": N - 1,
                              "area_mm2": A["cap_fly"], "height_um": H["cap_fly"],
                              "height_source": "production BOUNDED nominal (100 um); the "
                                               "catalogue 0805 body is 1.25 mm thick"},
                  "cap_out": {"part": cap["name"], "per_cell": 1, "area_mm2": A["cap_out"],
                              "height_um": H["cap_out"],
                              "height_source": "as the flying capacitor (production COUT "
                                               "convention: one capacitor footprint)"}},
        "tier_area_mm2_by_class": {c: A[c] * n_of[c] for c in CLASSES},
        "n_area_feasible_assignments": len(rows),
        "n_realizable": len(ok),
        "n_realizable_hs_at_bottom": len(cand),
        "chosen": cand[0] if cand else None,
        "runner_up": cand[1] if len(cand) > 1 else None,
        "realizable_hs_at_bottom": [{k: r[k] for k in ("partition", "worst_ar", "worst_net",
                                                       "stack_um")} for r in cand],
        "assignments": rows,
    }


def main():
    d = json.loads((HERE / "candidate_dse.json").read_text())["counts"]
    res = {"rule": {"via_diameter_um": D_VIA_UM, "rdl_um": RDL_UM, "max_ar": 1.0,
                    "source": "manuscript_v2/fig_scripts/fig_realizability.py, "
                              "scripts/phase0mr3c/repartition_search.py"},
           "cells": {}}
    for m in ("49", "64"):
        res["cells"][m] = study(d[m], f"M{m}")
    # the production checks the method must reproduce before it is trusted on M = 64
    p = {r["partition"]: r for r in res["cells"]["49"]["assignments"]}
    ref = p["gan_hs | gan_ls | cap_fly | inductor+cap_out"]
    rep = p["gan_hs | cap_fly | gan_ls | inductor+cap_out"]
    res["validation_49"] = {
        "n_area_feasible": res["cells"]["49"]["n_area_feasible_assignments"],
        "paper_n_area_feasible": 144,
        "reference_order_worst_ar": ref["worst_ar"], "paper_reference": 5.32,
        "repartitioned_worst_ar": rep["worst_ar"], "paper_repartitioned": 0.83,
        "repartitioned_stack_um": rep["stack_um"], "config_total_um": 1973.0}
    v = res["validation_49"]
    assert v["n_area_feasible"] == 144, v
    assert round(v["reference_order_worst_ar"], 2) == 5.32, v
    assert round(v["repartitioned_worst_ar"], 2) == 0.83, v
    assert abs(v["repartitioned_stack_um"] - 1973.0) < 1e-9, v
    OUT.write_text(json.dumps(res, indent=1))
    c = res["cells"]["64"]
    print(f"M64: side {c['cell_side_mm']:.4f} mm, {c['n_area_feasible_assignments']} "
          f"area-feasible, {c['n_realizable']} realizable, chosen "
          f"{c['chosen']['partition']} worst AR {c['chosen']['worst_ar']:.3f} "
          f"({c['chosen']['worst_net']}), stack {c['chosen']['stack_um']} um")
    for r in c["realizable_hs_at_bottom"]:
        print("   ", r)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
