#!/usr/bin/env python3
"""Generate configs/design_points.yaml -- THE design record (TCPMT round 3).

For every design below: synthesize it (kw1.design_1kw under the production converter rules,
packing ON, plus the design's own overrides), take the engine's minimum-tier stack plan with
the part placement in the square cell of side sqrt(I_cell / J_t) (the DSE convention), split
the 25-C converter loss per part, run the tier-order analysis (scripts/tcpmt_tier_order.py)
and write the entry with its tiers in the PRODUCTION ORDER (input end first). The screen
numbers come from the DSE record (research/tcpmt_revision/dse_phase2_summary.json).

    python scripts/tcpmt_design_record.py        writes the record + tier_order.json

Designs (authors' decision, round-3 worklog 2026-11-19):
  m36      PRODUCTION. M = 36, N3K3K_A2, EPC2014C / EPC2055, 805 kHz, rated 0603 flying
           capacitors, at most 4 mixed tiers (2.99 mm)
  m36t5    co-design comparison: the 5-tier optimum at M = 36 (N4K4K_A2, 957 kHz, 3.73 mm)
  m36thin  sensitivity (former case A0): m36 with the flying-capacitor height set to 100 um
  m25      count neighbour: the 4-tier screen pick at M = 25
  m49      count neighbour: the 4-tier screen pick at M = 49
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
for _p in ("scripts/phase0nw", "scripts/phase0mr", "scripts/phase0f", "scripts/phase0d",
           "scripts/phase0dr", "scripts/phase0e", "scripts/phase0b", "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))

RECORD = R / "configs" / "design_points.yaml"
DSE = R / "research" / "tcpmt_revision" / "dse_phase2_summary.json"
J_T = 3.5
PRODUCTION = "m36"
DESIGNS = {
    "m36": dict(role="production", n_vr=36, topology=(3, 3, 2), rules={}, dse_run="etm35_p2_t4",
                label="N3K3K_A2 at M = 36 (6 x 6), EPC2014C / EPC2055, 805 kHz, rated 0603 "
                      "flying capacitors, 4 mixed tiers (production)"),
    "m36t5": dict(role="co-design comparison", n_vr=36, topology=(4, 4, 2),
                  rules={"MAX_TIERS": 5}, dse_run="etm35_p2_t5",
                  label="N4K4K_A2 at M = 36, EPC2014C / EPC2055, 957 kHz, 5 mixed tiers "
                        "(co-design comparison)"),
    "m36thin": dict(role="sensitivity", base="m36", cap_height_um=100.0, dse_run="etm35_p2_t4",
                    label="m36 with the flying-capacitor height set to 100 um (thin-capacitor "
                          "sensitivity, former case A0)"),
    "m25": dict(role="count neighbour", n_vr=25, topology=None, rules={}, dse_run="etm35_p2_t4",
                label="4-tier screen pick at M = 25 (count neighbour)"),
    "m49": dict(role="count neighbour", n_vr=49, topology=None, rules={}, dse_run="etm35_p2_t4",
                label="4-tier screen pick at M = 49 (count neighbour)"),
}
CLASSES = ("gan_hs", "gan_ls", "inductor", "cap_fly")
#: the committed production k of each design's implemented decoupling (the package network is
#: closed at it; the campaign's decoupling chain re-derives it and tcpmt_design_comparison.py
#: kcheck records the difference). Filled from the decoupling chain run on the design
#: (scripts/tcpmt_decap_{circuit,placement,framework}.py); a design without its own value
#: takes the production design's and says so.
DECOUPLING = {}
DECOUPLING_FILE = R / "research" / "tcpmt_revision" / "decoupling_by_design.json"


def per_part_25c(des):
    """25-C per-part loss of a compiled design (the ledger's per-device split)."""
    from ledger import converter_decomposition, device_split
    from HVR_FULL_OPT_EPC_V2 import LossModelInputs, compute_total_loss
    import HVR_FULL_OPT_EPC_V2 as H
    import electrical as EL
    prev = EL.pin_loss_rules(H, des)
    try:
        lr = compute_total_loss(des.arch, LossModelInputs(
            hs_device=des.hs, ls_device=des.ls, inductor=des.inductor, capacitor=des.capacitor,
            I_out=des.i_out_a, V_out=des.v_out, V_in=des.v_in, f_sw=des.f_sw_hz))
        dec = converter_decomposition(des.arch, des.hs, des.ls, des.inductor, des.capacitor,
                                      des.i_out_a, des.v_out, des.v_in, des.f_sw_hz, lr)
        dec.update(device_split(des, des.hs, des.ls, dec))
    finally:
        EL._restore_rules(H, prev)
    return dec, lr


def compile_design(spec):
    import kw1
    import electrical as EL
    rules = {**EL.LEGACY_RULES, **EL.production_rules(), **spec.get("rules", {})}
    with EL.pinned_rules(rules):
        des, _g, why = kw1.design_1kw(m_vr=spec["n_vr"], j=J_T, topology=spec["topology"])
    if des is None:
        raise SystemExit(f"no design at M = {spec['n_vr']}: {why}")
    return des, rules


def stack(des, side, rules, cap_h=None):
    import HVR_FULL_OPT_EPC_V2 as H
    import electrical as EL
    from dataclasses import replace
    cap = des.capacitor if cap_h is None else replace(des.capacitor, height_um=float(cap_h))
    with EL.pinned_rules(rules):
        prev = EL._pin_production_rules(H)
        try:
            sp = H.stack_plan(des.arch, des.hs, des.ls, des.inductor, cap, side,
                              placement=True)
            dims = {c: list(H.part_dims_mm(p)) for c, p in
                    (("gan_hs", des.hs), ("gan_ls", des.ls), ("inductor", des.inductor),
                     ("cap_fly", cap))}
            hts = {c: H.part_height_um(p)[0] for c, p in
                   (("gan_hs", des.hs), ("gan_ls", des.ls), ("inductor", des.inductor),
                    ("cap_fly", cap))}
            known = all(H.part_height_um(p)[1] for p in (des.hs, des.ls, des.inductor, cap))
            ko = float(H.PACK_KEEPOUT_UM)
        finally:
            EL._restore_rules(H, prev)
    return sp, dims, hts, known, ko


def entry_for(key, spec, dse):
    base = DESIGNS.get(spec.get("base", ""), None)
    s = dict(base or {}, **{k: v for k, v in spec.items() if k != "base"}) if base else spec
    des, rules = compile_design(s)
    a = des.arch
    n = s["n_vr"]
    budget = 1000.0 / n / J_T
    side = math.sqrt(budget)
    sp, dims, hts, known, ko = stack(des, side, rules, s.get("cap_height_um"))
    dec, lr = per_part_25c(des)
    # the cell output RMS of the converter model's ripple (rms_currents' L1 formula)
    L = des.inductor.l_nh * 1e-9
    boost = 1.0 + des.inductor.coupling_k * max(a.K - 1, 0)
    di = ((a.D / (des.f_sw_hz * L)) * (des.v_in / a.N * a.K_A - des.v_out * a.K)) / boost
    i_rms = math.sqrt(des.i_out_a ** 2 + di ** 2 / 12.0)
    run = dse["runs"][s["dse_run"]]["per_count"][str(n)]
    if base:
        # a sensitivity of a base design keeps the base's DECIDED tier contents and placement;
        # only the heights follow the changed part (tallest part in each tier)
        b_sp = stack(des, side, rules)[0]
        plan = [dict(t, height_um=max(hts[c] for c in CLASSES if t.get(c)))
                for t in b_sp["plan"]]
    else:
        plan = sp["plan"]
    tiers = [{"parts": {c: int(t[c]) for c in CLASSES if t.get(c)},
              "height_um": float(t["height_um"]),
              "placement_mm": [[round(float(x), 6) for x in r[:4]] + [r[4]]
                               for r in (t.get("placement_mm") or [])]} for t in plan]
    e = {"role": s["role"], "label": s["label"],
         "tag": f"M{n}N{a.N}K{a.K}KA{a.K_A}" + ("T5" if rules.get("MAX_TIERS") == 5 else "")
                + ("THIN" if s.get("cap_height_um") else ""),
         "n_vr": n, "j_target_A_mm2": J_T, "rules": dict(s.get("rules", {})),
         "topology": {"N": a.N, "K": a.K, "K_A": a.K_A}, "B_array": list(a.B_array),
         "hs_part": des.hs.part_number, "ls_part": des.ls.part_number,
         "inductor": des.inductor.name, "capacitor": des.capacitor.name,
         "inductor_data": {"l_nh": float(des.inductor.l_nh),
                           "dcr_mohm": float(des.inductor.r_dcr_mohm),
                           "footprint_mm2": float(des.inductor.footprint_mm2),
                           "coupling_k": float(des.inductor.coupling_k)},
         "f_sw_hz": float(des.f_sw_hz), "synthesized_area_mm2": float(des.area_mm2),
         "conversion_25C_W": float(des.loss_25c_w) * n,
         "cell_area_mm2": budget, "cell_side_mm": side,
         "cap_height_um": float(s.get("cap_height_um") or hts["cap_fly"]),
         "keepout_um": ko, "part_dims_mm": dims, "part_heights_um": hts,
         "heights_known": bool(known), "i_cell_out_rms_A": i_rms,
         "per_part_25C_W": dec["per_part"],
         "screen": {"source": f"{DSE.relative_to(R)} runs.{s['dse_run']}.per_count.{n}",
                    "P_total_W": run["P_total_W"], "conv_total_W": run["conv_total_W"],
                    "routing_W": run["routing_W"], "tiers": run["tiers"],
                    "stack_height_um": run["stack_height_um"]},
         "tiers": tiers}
    return e, sp


def order_entry(key, e, sp, chosen_order=None):
    """Put the tiers in the production order (input end first) and name them."""
    import tcpmt_tier_order as TO
    import design_record as DR
    decided = [t["parts"] for t in e["tiers"]]
    rec = TO.analyse(e, decided, int(e["rules"].get("MAX_TIERS", 4)) if e["rules"] else 4,
                     full_search=len(decided) <= 4)
    order = chosen_order or rec["chosen"]["tiers"]
    pool = list(e["tiers"])
    out = []
    for i, v in enumerate(order, start=1):
        vec = {c: int(n) for c, n in zip(CLASSES, v) if n}
        j = next(j for j, t in enumerate(pool) if t["parts"] == vec)
        t = pool.pop(j)
        t = {"name": DR.tier_name(i, t["parts"]), **t}
        out.append(t)
    e["tiers"] = out
    c = rec["chosen"]
    if chosen_order is not None:            # the forced order's own evaluation
        c = next(r for r in rec["decided_orders"]
                 if [list(map(int, v)) for v in r["tiers"]] == [list(map(int, v))
                                                               for v in chosen_order])
        rec["chosen"] = c
    rank = rec["rule_ranking"]
    # the runner-up: the best order other than the production one under the rule (for a
    # forced order, the best of the others on the design's own numbers)
    ru = next((r for r in rank if r["order"] != c["order"]), None)
    sf = rec["single_face"]["rule_choice"]
    e["tier_order"] = {"rule": rec["rule"], "basis": rec["chosen_basis"],
                       "order_input_to_output": c["order"],
                       "worst_via_ar_both_faces": c["worst_ar_both"],
                       "worst_net_both_faces": c["worst_net_both"],
                       "worst_via_ar_single_face": c["worst_ar_single"],
                       "heat_path_K": c["heat_path_K"],
                       "heat_path_two_sided_K": c["heat_path_two_sided_K"],
                       "assignment": c["assignment"],
                       "rank_by_rule": next(r["rank"] for r in rank if r["order"] == c["order"]),
                       "n_orders": rec["n_decided_orders"],
                       "runner_up": None if ru is None else {
                           "order_input_to_output": ru["order"],
                           "heat_path_K": ru["heat_path_K"],
                           "heat_path_above_chosen_K": ru["heat_path_K"] - c["heat_path_K"],
                           "worst_via_ar_both_faces": ru["worst_ar_both"],
                           "worst_via_ar_single_face": ru["worst_ar_single"]},
                       "single_face_sensitivity": {
                           "chosen_order_worst_via_ar": c["worst_ar_single"],
                           "chosen_order_worst_net": c["worst_net_single"],
                           "rule_choice_single_face": sf["order"],
                           "rule_choice_worst_via_ar": sf["worst_ar_single"],
                           "rule_choice_heat_path_K": sf["heat_path_K"],
                           "same_order": sf["order"] == c["order"]},
                       "best_heat_path_order": rec["best_heat_path_order"]["order"],
                       "best_heat_path_K": rec["best_heat_path_order"]["heat_path_K"],
                       "best_heat_path_worst_via_ar": rec["best_heat_path_order"]["worst_ar_both"],
                       "source": "research/tcpmt_revision/tier_order.json (rule_ranking: every "
                                 "order with its heat path and worst via aspect ratios)"}
    e["converter_stack_um"] = sum(t["height_um"] for t in out) + (len(out) - 1) * 10.0
    return e, rec


NAME = {"gan_hs": "HS", "gan_ls": "LS", "inductor": "L", "cap_fly": "CF"}


def routing_block(e, des):
    """The routing dict of the design (z1_design.design_dict: the fields routing.nets and the
    ledger's intra-VR model read, at the record's cell) plus the B-vector and the part-level
    cell layout: every part's tier and placement rectangle, indexed by the tier-order
    assignment."""
    import routing as RT
    import z1_design as Z1D
    d = Z1D.design_dict(des, int(e["n_vr"]), RT.DESIGN_49_LEGACY,
                        tile_side_mm=float(e["cell_side_mm"]))
    d["B_array"] = list(e["B_array"])
    ko = float(e["keepout_um"]) * 1e-3
    asg = e["tier_order"]["assignment"]
    layout = []
    for t_i, t in enumerate(e["tiers"], start=1):
        for c in CLASSES:
            idx = sorted(int(k[len(c):]) for k, v in asg.items()
                         if k.startswith(c) and k[len(c):].isdigit() and int(v) == t_i)
            rects = [r for r in t["placement_mm"] if r[4] == c]
            if len(idx) != len(rects):
                raise SystemExit(f"tier {t['name']}: {len(idx)} {c} indices for "
                                 f"{len(rects)} placed parts")
            for k, (x, y, w, h, _c) in zip(idx, rects):
                layout.append({"name": f"{NAME[c]}{k}", "kind": c, "index": k, "tier": t_i,
                               "tier_name": t["name"], "x_mm": x, "y_mm": y, "w_mm": w,
                               "h_mm": h, "part_w_mm": w - ko, "part_h_mm": h - ko})
    d["layout"] = layout
    d["layout_cell_side_mm"] = float(e["cell_side_mm"])
    orient_layout(d)
    return d


#: the eight symmetries of the square cell (corner coordinates, side s)
SYM = {"id": lambda x, y, s: (x, y), "r90": lambda x, y, s: (s - y, x),
       "r180": lambda x, y, s: (s - x, s - y), "r270": lambda x, y, s: (y, s - x),
       "mx": lambda x, y, s: (s - x, y), "my": lambda x, y, s: (x, s - y),
       "tr": lambda x, y, s: (y, x), "atr": lambda x, y, s: (s - y, s - x)}


def _transform(p, f, s):
    xs, ys = zip(*(f(x, y, s) for x, y in ((p["x_mm"], p["y_mm"]),
                                           (p["x_mm"] + p["w_mm"], p["y_mm"] + p["h_mm"]))))
    w, h = abs(xs[1] - xs[0]), abs(ys[1] - ys[0])
    rot = abs(w - p["w_mm"]) > 1e-9
    return dict(p, x_mm=min(xs), y_mm=min(ys), w_mm=w, h_mm=h,
                part_w_mm=p["part_h_mm"] if rot else p["part_w_mm"],
                part_h_mm=p["part_w_mm"] if rot else p["part_h_mm"])


def orient_layout(d):
    """LAYOUT RULE (declared). Each tier keeps the DSE's packing (contents and order are the
    record's), placed in the cell up to the eight symmetries of the square. Lateral nets
    inside one tier are isometry-invariant, so the choice matters only BETWEEN tiers: the
    tiers holding inductors take the combination of symmetries (the first fixed) of least
    output-plane spreading resistance (the R2 sheet the ledger charges, routing.
    output_plane_r2: injection at the inductors, uniform extraction), the input-end tier the
    symmetry of least current-weighted VIN run (sum I_rms^2 x Manhattan from the corner VIN
    pad). Recorded per tier."""
    import itertools
    import routing as RT
    s = float(d["layout_cell_side_mm"])
    by = {p["name"]: p for p in d["layout"]}
    tiers = sorted({p["tier"] for p in d["layout"]})
    ind_tiers = [t for t in tiers if any(p["kind"] == "inductor" and p["tier"] == t
                                         for p in d["layout"])]
    chosen = {str(t): "id" for t in tiers}
    r2_id = RT.output_plane_r2(d)[0]
    best = (r2_id, ("id",) * len(ind_tiers))
    for combo in itertools.product(SYM, repeat=max(len(ind_tiers) - 1, 0)):
        keys = ("id",) + combo
        q = dict(by)
        for t, k in zip(ind_tiers, keys):
            for n, p in by.items():
                if p["tier"] == t:
                    q[n] = _transform(p, SYM[k], s)
        r2 = RT.output_plane_r2(dict(d, layout=[q[p["name"]] for p in d["layout"]]))[0]
        if r2 < best[0] - 1e-15:
            best = (r2, keys)
    for t, k in zip(ind_tiers, best[1]):
        chosen[str(t)] = k
        for n, p in list(by.items()):
            if p["tier"] == t:
                by[n] = _transform(p, SYM[k], s)
    t1 = tiers[0]
    if t1 not in ind_tiers:
        nets = RT.nets(d)
        vin = (0.05 * s, 0.05 * s)

        def cost(k):
            c = 0.0
            for n in nets:
                p = by.get(n.dst)
                if n.src == "VIN" and p and p["tier"] == t1:
                    q = _transform(p, SYM[k], s)
                    c += n.i_rms_a ** 2 * (abs(q["x_mm"] + q["w_mm"] / 2 - vin[0])
                                           + abs(q["y_mm"] + q["h_mm"] / 2 - vin[1]))
            return c
        k1 = min(SYM, key=lambda k: (round(cost(k), 12), list(SYM).index(k)))
        chosen[str(t1)] = k1
        for n, p in list(by.items()):
            if p["tier"] == t1:
                by[n] = _transform(p, SYM[k1], s)
    d["layout"] = [by[p["name"]] for p in d["layout"]]
    d["layout_rule"] = ("DSE packing per tier up to the 8 square symmetries: the inductor tiers "
                        "minimise the output-plane R2 resistance, the input-end tier the "
                        "current-weighted VIN run")
    d["layout_symmetry"] = chosen
    d["output_plane_r2_mohm"] = {"dse_placement": r2_id * 1e3, "adopted": best[0] * 1e3}


def _decoupling(key):
    """The committed production k of a design (decoupling_by_design.json, written from the
    decoupling chain runs), the production design's when the design has none of its own."""
    if not DECOUPLING_FILE.is_file():
        return None
    d = json.loads(DECOUPLING_FILE.read_text())
    own = (d.get("designs") or {}).get(key)
    if own:
        return dict(own, own=True)
    prod = (d.get("designs") or {}).get(PRODUCTION)
    if prod:
        return dict(prod, own=False, note=f"the production design's ({PRODUCTION}) k: this "
                                          f"design's own decoupling chain runs in the campaign")
    return None


def main():
    import yaml
    dse = json.loads(DSE.read_text())
    entries, recs = {}, {}
    for key, spec in DESIGNS.items():
        e, sp = entry_for(key, spec, dse)
        entries[key] = (e, sp)
        print(f"{key}: {e['tag']} {e['hs_part']}/{e['ls_part']} {e['f_sw_hz'] / 1e3:.2f} kHz "
              f"{e['conversion_25C_W']:.3f} W, {len(e['tiers'])} tiers", flush=True)
    out = {}
    for key, (e, sp) in entries.items():
        chosen = None
        if DESIGNS[key].get("base"):          # a sensitivity keeps its base design's order
            b = out[DESIGNS[key]["base"]]
            chosen = [[t["parts"].get(c, 0) for c in CLASSES] for t in b["tiers"]]
        e, rec = order_entry(key, e, sp, chosen)
        if DESIGNS[key].get("base"):
            e["tier_order"]["basis"] = (f"the order of {DESIGNS[key]['base']} (a sensitivity "
                                        "changes the capacitor height only)")
        e["routing"] = routing_block(e, compile_design(
            dict(DESIGNS.get(DESIGNS[key].get("base", ""), {}),
                 **{k: v for k, v in DESIGNS[key].items() if k != "base"}))[0])
        dec = _decoupling(key)
        if dec:
            e["decoupling"] = dec
        out[key] = e
        recs[key] = rec
        c = e["tier_order"]
        print(f"{key}: {c['order_input_to_output']}  AR {c['worst_via_ar_both_faces']:.2f} / "
              f"{c['worst_via_ar_single_face']:.2f}  H {c['heat_path_K']:.3f} K", flush=True)
    doc = {"schema": 1, "production": PRODUCTION, "selector": "HVR_DESIGN",
           "what": "THE design record of the TCPMT chain (round 3): regulator count, converter, "
                   "cell and mixed tiers (input end first, production order) of every design "
                   "the chain runs",
           "generator": "scripts/tcpmt_design_record.py", "designs": out}
    hdr = ("# GENERATED by scripts/tcpmt_design_record.py -- edit the generator, not this file.\n"
           "# THE design record (scripts/phase0nw/design_record.py reads and verifies it).\n")
    RECORD.write_text(hdr + yaml.safe_dump(doc, sort_keys=False, width=100,
                                           default_flow_style=None))
    import tcpmt_tier_order as TO
    TO.OUT.write_text(json.dumps({"what": TO.__doc__.split("\n\n")[0], "rule": TO.RULE,
                                  "designs": recs}, indent=1, default=float) + "\n")
    print("wrote", RECORD, "and", TO.OUT)


if __name__ == "__main__":
    main()
