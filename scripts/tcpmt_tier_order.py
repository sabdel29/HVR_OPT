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

ROUTING LOSS (review round 3: the framework's objective is loss). The intra-VR routing loss
of an order with a part assignment is final_closure_ledger.intra_vr's model on the oriented
cell layout (RoutingModel: R0 lateral runs within a tier, R0 via stacks across the span between
tiers, the output-plane R2 sheet), copper at 25 C, the 48-V nets at the hot-loop factor of the
design's decoupling record; every order takes its part assignment of least routing loss among
the assignments of its best worst-via aspect ratio.

RULE (the coordinator's decision, superseding the heat-path tie-break): among the orders of
the decided tiers meeting the via rule (both-face terminals) -- or, when none meets it, among
those of the best worst-via aspect ratio -- the order of least routing loss; orders within
0.1 W of it are separated by the heat path. Recorded for the paper: every decided order ranked
by the rule (rule_ranking: routing loss with its range over assignments, heat path, worst via
aspect ratio with both- and single-face terminals, the assignment), the runner-up, the least
routing-loss and best heat-path orders, and the rule applied to the single-face aspect ratios
(single_face: the order it picks and the chosen order's single-face worst via).

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
#: REVIEW ROUND 3 (the coordinator's decision: the framework's objective is loss). Each order
#: takes the part assignment of least intra-VR ROUTING LOSS among the assignments of its best
#: worst-via aspect ratio; among the orders meeting the via rule -- or, when none does, among
#: those tied on the best worst-via aspect ratio -- the production order is the one of least
#: routing loss, the heat path deciding only between orders within LOSS_TIE_W of it.
RULE = ("production order = among the orders of the decided tiers meeting the via rule (AR <= 1 "
        "on every via level, die terminals on both faces) -- or, if none meets it, among those "
        "of the best worst-via aspect ratio -- the order of least intra-VR routing loss (the "
        "ledger's model at 25 C, the 48-V nets at the hot-loop factor; each order with its "
        "part assignment of least routing loss among those of its best worst-via aspect "
        "ratio); orders within 0.1 W of the least loss are separated by the heat path")
#: the routing-loss criterion: final_closure_ledger.intra_vr's model (R0 lateral runs on the
#: oriented cell layout, R0 via stacks across the face-to-face span between tiers, the
#: output-plane R2 sheet), copper at this temperature
ROUTING_T_C = 25.0
#: orders whose routing losses differ by at most this are separated by the heat path
LOSS_TIE_W = 0.1


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


def assignment_ar(order, cls, nets, d_via, combo, terminals="both"):
    """(worst AR, worst net, per-net AR, total crossed depth) of ONE part assignment `combo`
    (per class, the tier position of each part index)."""
    hts = tier_heights(order, cls)
    T = len(order)
    step = RDL_UM / d_via

    def levels(ta, tb, lower_is_die):
        lo, hi = min(ta, tb), max(ta, tb)
        first = lo if (terminals == "single" and lower_is_die) else lo + 1
        return list(range(first, hi))
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
    return w, wn, pern, depth


def asg_dict(combo, cls):
    """{class<index>: tier (1-based)} of a part assignment."""
    return {f"{cls[i][0]}{k}": combo[i][k] + 1 for i in range(len(cls))
            for k in range(len(combo[i]))}


def worst_ar(order, cls, nets, d_via, terminals="both"):
    """(worst AR, worst net, per-net AR, assignment) minimised over the part indices: the
    smallest worst aspect ratio, then the smallest total crossed depth over all nets. Kept
    for the repartition search (context); the production assignment of an order is chosen by
    routing loss (RoutingModel, analyse)."""
    best = None
    for combo in itertools.product(*_assignments(order, cls)):
        w, wn, pern, depth = assignment_ar(order, cls, nets, d_via, combo, terminals)
        key = (round(w, 9), depth)
        if best is None or key < best[0]:
            best = (key, (w, wn, dict(pern), asg_dict(combo, cls)))
    return best[1]


class RoutingModel:
    """The intra-VR routing loss of one design for any (tier order, part assignment), with
    final_closure_ledger.intra_vr's model (review round 3): every part on the oriented cell
    layout of the design record's rule (tcpmt_design_record.routing_block: the DSE packing of
    each tier, placed by the output-plane R2 / VIN-run symmetries), a link within one tier --
    or between a part and the plane its tier lands on -- an R0 lateral run, a link between
    tiers an R0 via stack across the face-to-face span, plus the output-plane R2 sheet; copper
    at ROUTING_T_C; the 48-V nets at the hot-loop factor k_hot (the production state). The
    layout orientation does not depend on the part indices (equal currents per class), so it
    is built once per order; the R2 sheet depends only on the inductor footprints, so its
    solves are shared by every order."""

    def __init__(self, entry, des, k_hot):
        import routing as RT
        import z1_design as Z1D
        import final_closure_ledger as FL
        import tcpmt_design_record as G
        self.RT, self.FL, self.G = RT, FL, G
        self.entry, self.des, self.k_hot = entry, des, float(k_hot)
        self.side = float(entry["cell_side_mm"])
        d0 = Z1D.design_dict(des, int(entry["n_vr"]), RT.DESIGN_49_LEGACY,
                             tile_side_mm=self.side)
        d0["B_array"] = list(entry["B_array"])
        self.nets = [n for n in RT.nets(d0) if n.name != "vout_plane"]
        self.n_vr = int(entry["n_vr"])
        self.i_out_rms = float(entry["i_cell_out_rms_A"])
        self.k_t = FL.rho_ratio_cu(ROUTING_T_C, RT.T_C)
        self._order = {}
        self._r2 = {}

    def _r2_cached(self, d, *a, **kw):
        key = (round(float(d["tile_side_mm"]), 9), a, tuple(sorted(kw.items())),
               tuple(sorted((round(p["x_mm"], 9), round(p["y_mm"], 9), round(p["w_mm"], 9),
                             round(p["h_mm"], 9)) for p in d["layout"]
                            if p["kind"] == "inductor")))
        if key not in self._r2:
            self._r2[key] = self._r2_raw(d, *a, **kw)
        return self._r2[key]

    def oriented(self, tiers):
        """(slots, P_plane per cell, layout dict) of an order: slots[(tier, class)] = the
        oriented layout entries of that tier and class, in placement (= index) order."""
        key = tuple(tuple(sorted(t["parts"].items())) for t in tiers)
        if key in self._order:
            return self._order[key]
        import design_record as DR
        asg, cnt = {}, {c: 0 for c in CLASSES}
        for ti, t in enumerate(tiers, start=1):
            for c in CLASSES:
                for _ in range(int(t["parts"].get(c, 0))):
                    asg[f"{c}{cnt[c]}"] = ti
                    cnt[c] += 1
        e2 = dict(self.entry, tiers=[dict(t, name=DR.tier_name(i, t["parts"]))
                                     for i, t in enumerate(tiers, start=1)],
                  tier_order={"assignment": asg})
        RT = self.RT
        self._r2_raw, RT.output_plane_r2 = RT.output_plane_r2, self._r2_cached
        try:
            d = self.G.routing_block(e2, self.des)
            r2 = RT.output_plane_r2(d, self.FL.VOUT_PLANE_OCCUPANCY, 2,
                                    self.FL.INTRA_T_CU_M)[0]
        finally:
            RT.output_plane_r2 = self._r2_raw
        slots = {}
        for p in d["layout"]:
            slots.setdefault((int(p["tier"]), p["kind"]), []).append(p)
        for v in slots.values():
            v.sort(key=lambda p: int(p["index"]))
        p_plane = self.i_out_rms ** 2 * r2 * self.FL.rho_ratio_cu(ROUTING_T_C)
        self._order[key] = (slots, p_plane, d)
        return self._order[key]

    def loss(self, tiers, combo, cls, detail=False):
        """Routing loss (W, all cells) of the order `tiers` with the part assignment `combo`
        (per class of `cls`, the 0-based tier of each part index)."""
        RT, FL = self.RT, self.FL
        slots, p_plane, d = self.oriented(tiers)
        s = self.side
        sc = s / float(d["layout_cell_side_mm"])
        T = len(tiers)
        hts = [10.0]                                # Z1 cell: landing RDL, tiers, RDLs, output
        for i, t in enumerate(tiers):
            if i:
                hts.append(RDL_UM)
            hts.append(float(t["height_um"]))
        hts.append(10.0)
        name = {"gan_hs": "HS", "gan_ls": "LS", "inductor": "L", "cap_fly": "CF"}
        comp, idx = {}, {}
        for i, (c, _n, _ab, _h) in enumerate(cls):
            labels = combo[i]
            for k, t0 in enumerate(labels):
                rank = sum(1 for kk in range(k) if labels[kk] == t0)
                p = slots[(t0 + 1, c)][rank]
                nm = f"{name[c]}{k}"
                comp[nm] = ((p["x_mm"] + p["w_mm"] / 2) * sc - s / 2,
                            (p["y_mm"] + p["h_mm"] / 2) * sc - s / 2,
                            p["part_w_mm"], p["part_h_mm"])
                idx[nm] = 2 * t0 + 1
        comp["VIN"], idx["VIN"] = (-0.45 * s, -0.45 * s, 0.2, 0.2), 0
        comp["VOUT"], idx["VOUT"] = (0.0, 0.0, s, s), 2 * T
        s_m = s * 1e-3
        p_lat = p_vert = 0.0
        rows = []
        for n in self.nets:
            a, b = comp[n.src], comp[n.dst]
            ia, ib = idx[n.src], idx[n.dst]
            hgt = 0.0
            if ia != ib:
                lo, hi = sorted((ia, ib))
                hgt = sum(hts[max(lo + 1, 0):hi])
                if hgt <= 0.0 and n.dst == "VOUT":
                    hgt = hts[ib]
            if hgt > 0.0:
                seg = RT.vertical_segment(max(n.i_rms_a, 1e-9), hgt, FL.INTRA_J_MAX,
                                          min(a[2] * a[3], b[2] * b[3]), "D_area_optimal")
            else:
                seg = RT.lateral_segment(max(n.i_rms_a, 1e-9),
                                         abs(a[0] - b[0]) + abs(a[1] - b[1]),
                                         FL.INTRA_T_CU_M, FL.INTRA_J_MAX, s_m, FL.INTRA_N_LAYERS)
            scale = self.k_hot ** 2 if n.rail == "HV" else 1.0
            p = n.i_rms_a ** 2 * seg["R_ohm"] * self.k_t * scale
            if hgt > 0.0:
                p_vert += p
            else:
                p_lat += p
            if detail:
                rows.append({"net": n.name, "geom": "vertical" if hgt > 0 else "lateral",
                             "P_W": p * self.n_vr})
        tot = (p_lat + p_vert + p_plane) * self.n_vr
        if detail:
            return {"P_routing_W": tot, "P_lateral_W": p_lat * self.n_vr,
                    "P_vertical_W": p_vert * self.n_vr, "P_plane_W": p_plane * self.n_vr,
                    "nets": rows}
        return tot


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


def pick(rows, terminals="both"):
    """The order RULE picks among evaluated orders: those meeting the via rule, else those of
    the best worst-via aspect ratio; among them the least routing loss, the heat path deciding
    between orders within LOSS_TIE_W of it. `terminals` 'single' applies the rule with the
    single-face aspect ratios (each order's assignment chosen on them)."""
    ar = f"worst_ar_{terminals}"
    loss = "routing_loss_W" if terminals == "both" else "routing_loss_single_W"
    pool = [r for r in rows if r[ar] <= AR_MAX + 1e-12]
    if not pool:
        best = min(round(r[ar], 9) for r in rows)
        pool = [r for r in rows if round(r[ar], 9) == best]
    lmin = min(r[loss] for r in pool)
    near = [r for r in pool if r[loss] <= lmin + LOSS_TIE_W + 1e-12]
    return min(near, key=lambda r: (r["heat_path_K"], r[loss], r["order"]))


def rank(rows, terminals="both"):
    """Every order in RULE's order of preference (pick, repeatedly)."""
    rest, out = list(rows), []
    while rest:
        r = pick(rest, terminals)
        out.append(r)
        rest.remove(r)
    return out


def order_row(r):
    """The paper's row of one evaluated order."""
    return {"order": r["order"], "routing_loss_W": r["routing_loss_W"],
            "heat_path_K": r["heat_path_K"],
            "heat_path_two_sided_K": r["heat_path_two_sided_K"],
            "worst_ar_both": r["worst_ar_both"], "worst_net_both": r["worst_net_both"],
            "worst_ar_single": r["worst_ar_single"], "worst_net_single": r["worst_net_single"],
            "via_rule_met": r["via_rule_met"], "assignment": r["assignment"],
            "routing_loss_range_W": r["routing_loss_range_W"]}


def analyse(entry, decided, max_tiers, full_search=True, des=None, k_hot=None):
    """The tier-order record of one design entry. `decided`: the decided tiers (record tier
    dicts with parts, height_um and placement_mm; any order). `des`: the compiled design
    (default: design_record.compiled of the entry's design), `k_hot`: the hot-loop factor of
    the 48-V nets (default: the entry's decoupling k_open, else 1/sqrt(D)). Returns the record
    with 'chosen' (production order) and its part assignment."""
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
    if k_hot is None:
        k_hot = ((entry.get("decoupling") or {}).get("k_open")
                 or 1.0 / math.sqrt(N * 1.0 / 48.0))
    if des is None:
        import design_record as DR
        des = DR.compiled(next(k for k in DR.keys() if DR.get(k)["tag"] == entry["tag"]))
    RM = RoutingModel(entry, des, k_hot)

    @lru_cache(maxsize=None)
    def kz_vec(v, h):
        parts = {c: v[i] for i, c in enumerate(CLASSES) if v[i]}
        return CC.mixed_tier(mc, "tierX_probe", parts, h)["k_ortho"]["value"][2]

    def kz_of(v, h):
        return kz_vec(tuple(v), float(h))

    tier_of_vec = {}
    for t in decided:
        tier_of_vec.setdefault(tuple(int(t["parts"].get(c, 0)) for c in CLASSES), t)
    vecs_dec = [tuple(int(t["parts"].get(c, 0)) for c in CLASSES) for t in decided]
    cls = None

    def evaluate(order):
        r = {"order": label(order, cls), "tiers": [list(v) for v in order],
             "tier_um": tier_heights(order, cls)}
        r["stack_um"] = sum(r["tier_um"]) + (len(order) - 1) * RDL_UM
        tiers = [tier_of_vec[tuple(v)] for v in order]
        rows = []
        for combo in itertools.product(*_assignments(order, cls)):
            wb, nb, pb, _db = assignment_ar(order, cls, nets, d_via, combo, "both")
            ws, ns, _ps, _ds = assignment_ar(order, cls, nets, d_via, combo, "single")
            rows.append((round(wb, 9), round(ws, 9), RM.loss(tiers, combo, cls), combo, wb, nb,
                         pb, ws, ns))
        losses = [x[2] for x in rows]
        # the order's assignment: least routing loss among those of its best worst-via AR
        bb = min(x[0] for x in rows)
        c = min((x for x in rows if x[0] == bb), key=lambda x: (x[2], x[3]))
        r["worst_ar_both"], r["worst_net_both"], r["net_ar_both"] = c[4], c[5], c[6]
        r["worst_ar_single"], r["worst_net_single"] = c[7], c[8]
        r["routing_loss_W"], r["assignment"] = c[2], asg_dict(c[3], cls)
        r["routing_loss_range_W"] = [min(losses), max(losses)]
        r["n_assignments"] = len(rows)
        bs = min(x[1] for x in rows)                   # the single-face sensitivity
        cs = min((x for x in rows if x[1] == bs), key=lambda x: (x[2], x[3]))
        r["worst_ar_single_best"], r["routing_loss_single_W"] = cs[7], cs[2]
        r["assignment_single"] = asg_dict(cs[3], cls)
        r["worst_ar_single_rule"] = cs[7]
        r["via_rule_met"] = r["worst_ar_both"] <= AR_MAX + 1e-12
        r["heat_path_K"], r["heat_path_two_sided_K"] = heat_path(
            order, cls, kz_of, p_part, float(entry["cell_side_mm"]) ** 2, k_rdl)
        return r

    import HVR_FULL_OPT_EPC_V2 as H
    cls = classes_of(entry, H)
    # 1. the decided tiers, every order, each with its least-loss assignment
    dec_orders = sorted(set(itertools.permutations(vecs_dec)))
    dec = [evaluate(o) for o in dec_orders]
    meets = [r for r in dec if r["via_rule_met"]]
    ranking = rank(dec)
    chosen = ranking[0]
    basis = (("least routing loss among the orders meeting the via rule" if meets else
              "no order of the decided tiers meets the via rule: least routing loss among the "
              "orders of the best worst-via aspect ratio")
             + f" (heat path between orders within {LOSS_TIE_W:g} W)")
    best_heat = min(dec, key=lambda r: (r["heat_path_K"], r["worst_ar_both"]))
    best_loss = min(dec, key=lambda r: (r["routing_loss_W"], r["heat_path_K"]))
    sf = {r["order"]: dict(r, worst_ar_single=r["worst_ar_single_best"],
                           routing_loss_W=r["routing_loss_single_W"],
                           assignment=r["assignment_single"]) for r in dec}
    single = pick(list(sf.values()), "single")
    rec = {"design": entry["tag"], "rule": RULE, "via_diameter_um": d_via,
           "ar_limit": AR_MAX, "rdl_um": RDL_UM, "k_z_rdl_W_mK": k_rdl,
           "routing": {"model": "final_closure_ledger.intra_vr (R0 lateral, R0 via stacks, "
                                "output-plane R2), all cells", "T_C": ROUTING_T_C,
                       "k_hot_48V_nets": float(k_hot), "tie_W": LOSS_TIE_W},
           "per_part_25C_W": p_part, "nets": [n for n, _a, _b in nets],
           "terminal_assumption": {"both": "production (authors' stated assumption): a die "
                                           "connects through the capture planes on both "
                                           "faces of its tier",
                                   "single": "sensitivity: dies face the input end, terminals "
                                             "on that face only"},
           "decided_tiers": [list(v) for v in vecs_dec],
           "decided_orders": ranking,
           "n_decided_orders": len(dec), "n_meeting_via_rule": len(meets),
           "chosen": chosen, "chosen_basis": basis, "best_heat_path_order": best_heat,
           "least_routing_loss_order": order_row(best_loss),
           "rule_ranking": [dict(order_row(r), rank=i + 1) for i, r in enumerate(ranking)],
           "runner_up": order_row(ranking[1]) if len(ranking) > 1 else None,
           "single_face": {
               "rule_choice": dict(order_row(single), worst_ar_single=single["worst_ar_single"],
                                   routing_loss_W=single["routing_loss_W"],
                                   assignment=single["assignment"]),
               "same_as_chosen": single["order"] == chosen["order"],
               "chosen_order_worst_ar_single": chosen["worst_ar_single"],
               "what": "RULE applied with single-face terminals (dies face the input end; "
                       "each order's assignment chosen on its single-face aspect ratio): the "
                       "order it picks, and the chosen order's single-face worst via"}}
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
        rec = analyse(e, e["tiers"], int(DR.rules(k)["MAX_TIERS"]),
                      full_search=len(e["tiers"]) <= 4, des=DR.compiled(k),
                      k_hot=(e.get("decoupling") or {}).get("k_open"))
        out["designs"][k] = rec
        c = rec["chosen"]
        print(f"{k}: chosen {c['order']}  routing {c['routing_loss_W']:.3f} W  AR both "
              f"{c['worst_ar_both']:.2f} single {c['worst_ar_single']:.2f}  H "
              f"{c['heat_path_K']:.3f} K  ({rec['chosen_basis']})")
    OUT.write_text(json.dumps(out, indent=1, default=float) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
