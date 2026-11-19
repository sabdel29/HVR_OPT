#!/usr/bin/env python3
"""TCPMT round 3 --- tier order of a converter cell with MIXED tiers.

The decided design point (configs/design_points.yaml) stacks the parts of one cell in at most
four tiers that may mix classes (the DSE's packing with a 50-um keep-out, engine
HVR_FULL_OPT_EPC_V2.stack_plan). This module redoes the tier-order analysis of
scripts/phase0mr3c/repartition_search.py for such a stack.

SEARCH (with packing). Every grouping of the cell's parts (N high-side and K low-side dies, K
inductors, N-1 flying capacitors) into at most T tiers whose every tier PLACES in the cell
(engine _multiset_fits, keep-out as the DSE), and every order of those tiers from the input
(48 V) end to the output (1 V) end. The decided tiers' orders are the candidates the
production order is chosen from; the full search is reported beside them.

NETS. The cell's part-level netlist of the intra-VR ledger (routing.nets): VIN -> every
high-side die, high side k -> flying capacitor min(k, N-2), high side k -> the low side of the
inductor branch it drives (the B-vector allocation), low side j -> inductor j, inductor j ->
output plane. VIN is the landing plane under the input-end tier, the output plane the one
above the output-end tier. Which part of a class sits in which tier (the part indices) is
searched for each order and the best assignment kept.

VIA RULE (as fig_realizability / repartition_search --bookkeeping). An interlayer RDL is a
copper capture plane, so a net crossing tiers is one via level per crossed tier; the aspect
ratio of a level is the crossed tier height over the build-up via diameter (120 um, from
flying_caps.json), and a net between adjacent tiers steps through one 10-um RDL. The rule is
AR <= 1 on every level of every net.
Terminals: BOTH faces (the authors' stated assumption, production): a die connects through
the capture planes on either side of its tier, so only the tiers strictly between the two
ends are crossed. SINGLE face (sensitivity): dies face the input end with terminals on that
face only, so a net whose input-side end is a die crosses that die's own tier as well.

HEAT-PATH METRIC. The loss-weighted one-dimensional conduction rise from each tier to the
converter's output-end face (the face towards the die and the top cold plate in every
integration), per cell:  H = sum_t (P_t / A_cell) R''_t,  R''_t = h_t / (2 k_z,t) + the
tiers and RDLs between tier t and that face (k_z of the homogenized tier cards,
tcpmt_converter_cards.mixed_tier; P_t the 25-C per-part loss split of the converter model).
The two-sided value (each tier also cooled through the input-end face, parallel paths) is
recorded beside it.

RULE (declared before the result): the production order is the order of the decided tiers
with the best heat path among those meeting the via rule (both-face terminals); when none
meets it, the order with the best worst-via aspect ratio, ties broken by the heat path. Both
the chosen order and the best heat-path order are recorded for the paper.

    python tcpmt_tier_order.py [design ...]   -> research/tcpmt_revision/tier_order.json
"""
from __future__ import annotations

import itertools
import json
import math
import os
import sys
from functools import lru_cache
from pathlib import Path

R = Path(__file__).resolve().parents[1]
for _p in ("scripts/phase0nw", "scripts/phase0mr", "scripts/phase0m", "scripts/phase0f",
           "scripts/phase0d", "scripts/phase0dr", "scripts/phase0e", "scripts/phase0b",
           "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))

OUT = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision" / \
    "tier_order.json"                                                       # campaign hook
CLASSES = ("gan_hs", "gan_ls", "inductor", "cap_fly")
DIES = ("gan_hs", "gan_ls")
RDL_UM = 10.0
AR_MAX = 1.0
RULE = ("production order = the order of the decided tiers with the best heat path among the "
        "orders meeting the via rule (AR <= 1 on every via level, die terminals on both faces); "
        "if none meets it, the order with the best worst-via aspect ratio, ties broken by the "
        "heat path")


def via_diameter_um():
    """Build-up via diameter of the realizability rule (flying_caps.json summary: tier / AR)."""
    f = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision" / \
        "flying_caps.json"
    try:
        fc = json.loads(f.read_text())["summary"]
        return float(fc["min_tier_um_10pct"][-1]) / float(fc["via_AR_10pct"][-1])
    except (FileNotFoundError, KeyError):
        return 120.0


def rdl_kz():
    """k_z of one 10-um RDL tier: the production tensor (the explicit RVE of
    final_closure_physical_etm.rdl_tier_laminate, read from reference_rve.json)."""
    f = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "final_closure" / \
        "reference_rve.json"
    try:
        return float(json.loads(f.read_text())["rdl_tier_kz"]["reference_value"])
    except (FileNotFoundError, KeyError, TypeError):
        return 0.620


# --------------------------------------------------------------------------- netlist
def branch_inductor(N, K, B):
    """Inductor index driven by high-side branch k (B-vector allocation, in branch order)."""
    out, k = [], 0
    for j, b in enumerate(B):
        out += [j] * int(b)
        k += int(b)
    if len(out) != N:
        raise ValueError(f"B {B} does not allocate {N} branches")
    return out


def netlist(N, K, B):
    """[(net, (class_a, index_a) or 'vin', (class_b, index_b) or 'out')]."""
    bi = branch_inductor(N, K, B)
    nets = [(f"vin_to_hs{k}", "vin", ("gan_hs", k)) for k in range(N)]
    nets += [(f"hs{k}_to_cf{min(k, N - 2)}", ("gan_hs", k), ("cap_fly", min(k, N - 2)))
             for k in range(N) if N >= 2]
    nets += [(f"hs{k}_to_ls{bi[k]}", ("gan_hs", k), ("gan_ls", bi[k])) for k in range(N)]
    nets += [(f"ls{j}_to_L{j}", ("gan_ls", j), ("inductor", j)) for j in range(K)]
    nets += [(f"L{j}_to_vout", ("inductor", j), "out") for j in range(K)]
    return nets


# --------------------------------------------------------------------------- packing
def classes_of(entry, H):
    """Engine class descriptors of a design entry: (name, count, (a, b) grown, height)."""
    N, K = entry["topology"]["N"], entry["topology"]["K"]
    ko = float(entry.get("keepout_um", H.PACK_KEEPOUT_UM)) * 1e-3
    out = []
    for c, n in (("gan_hs", N), ("gan_ls", K), ("inductor", K), ("cap_fly", N - 1)):
        x, y = entry["part_dims_mm"][c]
        out.append((c, n, (round(max(x, y) + ko, 9), round(min(x, y) + ko, 9)),
                    float(entry["part_heights_um"][c])))
    return out


def packable_vectors(entry):
    """Every class-count vector (n_hs, n_ls, n_ind, n_cf) whose parts place in the cell."""
    import HVR_FULL_OPT_EPC_V2 as H
    cls = classes_of(entry, H)
    side = round(float(entry["cell_side_mm"]), 9)
    counts = [c[1] for c in cls]
    ok = {}
    for v in sorted((v for v in itertools.product(*[range(n + 1) for n in counts]) if any(v)),
                    key=sum):
        if any(v[i] and not ok.get(v[:i] + (v[i] - 1,) + v[i + 1:], True)
               for i in range(len(v))):
            ok[v] = False
            continue
        ok[v] = H._multiset_fits(tuple(sorted((cls[i][2], v[i]) for i in range(len(v))
                                              if v[i])), side)
    return [v for v, good in ok.items() if good], cls


def groupings(entry, max_tiers):
    """Every multiset of <= max_tiers packable vectors that sums to the part counts."""
    vecs, cls = packable_vectors(entry)
    total = tuple(c[1] for c in cls)
    vecs = sorted(vecs, reverse=True)
    out = []

    def rec(rem, start, acc):
        if not any(rem):
            out.append(tuple(acc))
            return
        if len(acc) >= max_tiers:
            return
        for i in range(start, len(vecs)):
            v = vecs[i]
            if all(a <= b for a, b in zip(v, rem)):
                rec(tuple(b - a for a, b in zip(v, rem)), i, acc + [v])
    rec(total, 0, [])
    return out, cls


# --------------------------------------------------------------------------- evaluation
def tier_heights(order, cls):
    return [max(cls[i][3] for i in range(len(cls)) if v[i]) for v in order]


def _assignments(order, cls):
    """Distinct assignments of part indices to tiers: for each class, the multiset of tier
    positions permuted (parts in one tier are interchangeable)."""
    per = []
    for i, c in enumerate(cls):
        labels = [t for t, v in enumerate(order) for _ in range(v[i])]
        per.append(sorted(set(itertools.permutations(labels))))
    return per


def worst_ar(order, cls, nets, d_via, terminals="both"):
    """(worst AR, worst net, per-net AR, assignment) minimised over the part indices: the
    smallest worst aspect ratio, then the smallest total crossed depth over all nets (so the
    assignment also keeps the via stacks the ledger charges short)."""
    hts = tier_heights(order, cls)
    T = len(order)
    per = _assignments(order, cls)
    step = RDL_UM / d_via

    def levels(ta, tb, lower_is_die):
        lo, hi = min(ta, tb), max(ta, tb)
        first = lo if (terminals == "single" and lower_is_die) else lo + 1
        return list(range(first, hi))

    best = None
    for combo in itertools.product(*per):
        tier_of = {(cls[i][0], k): combo[i][k] for i in range(len(cls))
                   for k in range(len(combo[i]))}
        w, wn, pern, depth = 0.0, None, {}, 0.0
        for name_, a, b in nets:
            if a == "vin":
                crossed = list(range(0, tier_of[b]))
            elif b == "out":
                ta = tier_of[a]
                crossed = list(range(ta if (terminals == "single" and a[0] in DIES)
                                     else ta + 1, T))
            else:
                ta, tb = tier_of[a], tier_of[b]
                if ta == tb:
                    pern[name_] = 0.0
                    continue
                lower = a if ta <= tb else b
                crossed = levels(ta, tb, lower[0] in DIES)
            ar = max(hts[t] for t in crossed) / d_via if crossed else step
            depth += sum(hts[t] for t in crossed)
            pern[name_] = ar
            if ar > w:
                w, wn = ar, name_
        key = (round(w, 9), depth)
        if best is None or key < best[0]:
            best = (key, (w, wn, dict(pern),
                          {f"{c}{k}": t + 1 for (c, k), t in tier_of.items()}))
    return best[1]


def heat_path(order, cls, kz_of, p_part, a_cell_mm2, k_rdl):
    """(one-sided H to the output-end face, two-sided H), K, per cell."""
    hts = tier_heights(order, cls)
    T = len(order)
    a = a_cell_mm2 * 1e-6
    r_t = [h * 1e-6 / kz_of(v, h) for v, h in zip(order, hts)]          # m^2 K / W, full tier
    r_rdl = RDL_UM * 1e-6 / k_rdl
    h1 = h2 = 0.0
    for t, v in enumerate(order):
        p = sum(v[i] * p_part[cls[i][0]] for i in range(len(cls)))
        up = r_t[t] / 2 + sum(r_t[t + 1:]) + (T - t) * r_rdl            # to the output face
        dn = r_t[t] / 2 + sum(r_t[:t]) + (t + 1) * r_rdl                 # to the input face
        h1 += p / a * up
        h2 += p / a * (up * dn / (up + dn))
    return h1, h2


def label(order, cls):
    return " | ".join("+".join(f"{v[i]}{cls[i][0]}" for i in range(len(cls)) if v[i])
                      for v in order)


def analyse(entry, decided, max_tiers, full_search=True):
    """The tier-order record of one design entry. `decided`: the decided tiers as
    [{class: n}] (any order). Returns the record with 'chosen' (production order)."""
    import tcpmt_converter_cards as CC
    N, K = entry["topology"]["N"], entry["topology"]["K"]
    B = list(entry["B_array"])
    nets = netlist(N, K, B)
    d_via = via_diameter_um()
    p_part = dict(entry["per_part_25C_W"])
    p_part["inductor"] = sum(p_part["inductor"]) / len(p_part["inductor"])
    mc = CC.MixedContents(label=entry["tag"], n_cells=int(entry["n_vr"]),
                          cell_side_mm=float(entry["cell_side_mm"]),
                          i_out_rms_a=float(entry["i_cell_out_rms_A"]),
                          hs_part=entry["hs_part"], ls_part=entry["ls_part"],
                          ind_footprint_mm2=float(entry["part_dims_mm"]["inductor"][0]
                                                  * entry["part_dims_mm"]["inductor"][1]),
                          ind_um=float(entry["part_heights_um"]["inductor"]),
                          cf_um=float(entry["part_heights_um"]["cap_fly"]), n_ind_total=K)
    k_rdl = rdl_kz()

    @lru_cache(maxsize=None)
    def kz_vec(v, h):
        parts = {c: v[i] for i, c in enumerate(CLASSES) if v[i]}
        return CC.mixed_tier(mc, "tierX_probe", parts, h)["k_ortho"]["value"][2]

    def kz_of(v, h):
        return kz_vec(tuple(v), float(h))

    vecs_dec = [tuple(int(t.get(c, 0)) for c in CLASSES) for t in decided]
    cls = None

    def evaluate(order):
        r = {"order": label(order, cls), "tiers": [list(v) for v in order],
             "tier_um": tier_heights(order, cls)}
        r["stack_um"] = sum(r["tier_um"]) + (len(order) - 1) * RDL_UM
        for term in ("both", "single"):
            w, wn, pern, asg = worst_ar(order, cls, nets, d_via, term)
            r[f"worst_ar_{term}"], r[f"worst_net_{term}"] = w, wn
            if term == "both":
                r["net_ar_both"], r["assignment"] = pern, asg
        r["via_rule_met"] = r["worst_ar_both"] <= AR_MAX + 1e-12
        r["heat_path_K"], r["heat_path_two_sided_K"] = heat_path(
            order, cls, kz_of, p_part, float(entry["cell_side_mm"]) ** 2, k_rdl)
        return r

    import HVR_FULL_OPT_EPC_V2 as H
    cls = classes_of(entry, H)
    # 1. the decided tiers, every order
    dec_orders = sorted(set(itertools.permutations(vecs_dec)))
    dec = [evaluate(o) for o in dec_orders]
    meets = [r for r in dec if r["via_rule_met"]]
    if meets:
        chosen = min(meets, key=lambda r: (r["heat_path_K"], r["worst_ar_both"]))
        basis = "best heat path among the orders meeting the via rule"
    else:
        chosen = min(dec, key=lambda r: (round(r["worst_ar_both"], 9), r["heat_path_K"]))
        basis = ("no order of the decided tiers meets the via rule: best worst-via aspect "
                 "ratio, ties broken by the heat path")
    best_heat = min(dec, key=lambda r: (r["heat_path_K"], r["worst_ar_both"]))
    rec = {"design": entry["tag"], "rule": RULE, "via_diameter_um": d_via,
           "ar_limit": AR_MAX, "rdl_um": RDL_UM, "k_z_rdl_W_mK": k_rdl,
           "per_part_25C_W": p_part, "nets": [n for n, _a, _b in nets],
           "terminal_assumption": {"both": "production (authors' stated assumption): a die "
                                           "connects through the capture planes on both "
                                           "faces of its tier",
                                   "single": "sensitivity: dies face the input end, terminals "
                                             "on that face only"},
           "decided_tiers": [list(v) for v in vecs_dec],
           "decided_orders": sorted(dec, key=lambda r: (r["worst_ar_both"], r["heat_path_K"])),
           "n_decided_orders": len(dec), "n_meeting_via_rule": len(meets),
           "chosen": chosen, "chosen_basis": basis, "best_heat_path_order": best_heat}
    # 2. the full repartition search with packing (context)
    if full_search:
        gs, _ = groupings(entry, max_tiers)
        n_orders, best_ar, best_ar_heat, best_hp, n_meet = 0, None, None, None, 0
        for g in gs:
            for o in sorted(set(itertools.permutations(g))):
                n_orders += 1
                w, wn, _p, _a = worst_ar(o, cls, nets, d_via, "both")
                hp = heat_path(o, cls, kz_of, p_part, float(entry["cell_side_mm"]) ** 2,
                               k_rdl)[0]
                n_meet += w <= AR_MAX + 1e-12
                if best_ar is None or (round(w, 9), hp) < (round(best_ar[0], 9), best_ar[2]):
                    best_ar = (w, label(o, cls), hp, wn, tier_heights(o, cls))
                if best_hp is None or (hp, w) < (best_hp[0], best_hp[1]):
                    best_hp = (hp, w, label(o, cls), tier_heights(o, cls))
        rec["repartition_search"] = {
            "max_tiers": max_tiers, "n_groupings": len(gs), "n_ordered": n_orders,
            "n_meeting_via_rule": int(n_meet),
            "best_worst_ar": {"worst_ar_both": best_ar[0], "order": best_ar[1],
                              "heat_path_K": best_ar[2], "worst_net": best_ar[3],
                              "tier_um": best_ar[4]},
            "best_heat_path": {"heat_path_K": best_hp[0], "worst_ar_both": best_hp[1],
                               "order": best_hp[2], "tier_um": best_hp[3]},
            "note": ("every packable grouping of the cell's parts into at most "
                     f"{max_tiers} tiers, every order; the production order is chosen among "
                     "the decided tiers' orders (the decided stack)")}
    return rec


def main():
    import design_record as DR
    keys = sys.argv[1:] or DR.keys()
    out = json.loads(OUT.read_text()) if OUT.exists() else {}
    out.setdefault("designs", {})
    out["what"] = __doc__.split("\n\n")[0]
    out["rule"] = RULE
    for k in keys:
        e = DR.get(k)
        rec = analyse(e, [t["parts"] for t in e["tiers"]], int(DR.rules(k)["MAX_TIERS"]),
                      full_search=len(e["tiers"]) <= 4)
        out["designs"][k] = rec
        c = rec["chosen"]
        print(f"{k}: chosen {c['order']}  AR both {c['worst_ar_both']:.2f} single "
              f"{c['worst_ar_single']:.2f}  H {c['heat_path_K']:.3f} K  ({rec['chosen_basis']})")
    OUT.write_text(json.dumps(out, indent=1, default=float) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
