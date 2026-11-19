#!/usr/bin/env python3
"""Phase-0M-R3C Section 4 --- bounded repartition search over EXISTING components.

Enumerates every ORDERED PARTITION of the five existing component classes (high-side GaN,
low-side GaN, flying capacitors, output capacitor, inductor) into k = 2..5 non-empty,
bottom-to-top ordered tiers -- k! S(5, k) candidates: 30 + 150 + 240 + 120 = 540 -- keeps
those whose every tier fits the cell area (144 of the 540), and scores them by the
dielectric depth each high-current net must cross. Nothing new is introduced: no device, no
dimension change, no relaxed spec. (TCPMT round 3, finding 10: the 144 are NOT "the
permutations of the four component tiers"; there are 4! = 24 of those. The correct
statement and counts are written by --bookkeeping.)

The objective is the brief's hierarchy: fewest vertical levels for the 20.408 A ls_to_L
net, then the other vertical nets.

Terminal assumption. The production rule takes the device dies to have terminals on BOTH
faces, so a die connects up and down through the capture planes on either side of its tier.
net_depth(..., terminals="single") instead takes every die face-down with terminals on its
bottom face only (flip-chip on the RDL beneath its tier): a net leaving a die tier upward
must then cross that tier itself. Capacitors keep wrap-around terminations (both faces).

    python repartition_search.py                 the candidate CSV (production)
    python repartition_search.py --bookkeeping   counts, statement and the terminal
                                                 sensitivity -> research/tcpmt_revision/
                                                 tier_order_bookkeeping.json
"""
from __future__ import annotations
import csv, itertools, os, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0mr", "scripts/phase0m", "scripts"):
    sys.path.insert(0, str(R / p))
import routing_production as RP                                          # noqa: E402

OUT = R / "results" / "phase0mr3c"
D = RP.DESIGN
N, K = D["N"], D["K"]
N_OF = {"gan_hs": N, "gan_ls": K, "cap_fly": N - 1, "cap_out": 1, "inductor": K}
COMPS = ["gan_hs", "gan_ls", "cap_fly", "cap_out", "inductor"]
CELL_MM2 = D["tile_side_mm"] ** 2
# the vertical nets and the current each carries, from build_edges
NETS = [("ls_to_L", "gan_ls", "inductor", D["i_out_per_vr_a"]),
        ("hs_to_cf", "gan_hs", "cap_fly", None),
        ("hs_to_ls", "gan_hs", "gan_ls", None)]
# architecture height budgets, um (substrate space available to the converter cell)
BUDGET = {"ARCH_Z1_EMBEDDED": 1300.0, "ARCH_Z2_BACKSIDE": 1300.0}


def partitions(items, k):
    """Every ordered assignment of `items` into exactly k non-empty tiers."""
    for assign in itertools.product(range(k), repeat=len(items)):
        if len(set(assign)) != k:
            continue
        tiers = [[c for c, a in zip(items, assign) if a == t] for t in range(k)]
        yield tiers


def geometry(tiers):
    z, ext, areas = 0.0, [], []
    for tier in tiers:
        h = max(RP.H_UM[c] for c in tier)
        ext.append((z, z + h))
        areas.append(sum(RP.FOOT_MM2[c] * N_OF[c] for c in tier))
        z += h + RP.RDL_UM
    return ext, areas, z - RP.RDL_UM


#: device dies (the single-face option applies to these; capacitors have wrap-around ends)
DIES = ("gan_hs", "gan_ls")


def net_levels(tiers, src, dst, terminals="both", heights=None):
    """Depth of every via level the net crosses (one per tier between capture planes).

    terminals='both'   (production) a component connects from either face of its tier, so
                       only the tiers strictly between the two ends are crossed;
    terminals='single' every die is face-down with terminals on its bottom face: when the
                       LOWER end of the net is a die, its own tier is crossed as well (the
                       upper end, face-down, is reached on the plane beneath its tier)."""
    h = heights or RP.H_UM
    ta = next(i for i, t in enumerate(tiers) if src in t)
    tb = next(i for i, t in enumerate(tiers) if dst in t)
    if ta == tb:
        return []
    lo, hi = min(ta, tb), max(ta, tb)
    lower = src if ta < tb else dst
    first = lo if (terminals == "single" and lower in DIES) else lo + 1
    return [max(h[c] for c in tiers[t]) for t in range(first, hi)]


def net_depth(tiers, ext, src, dst, terminals="both"):
    """Total dielectric depth the net must cross, and how many via levels."""
    ta = next(i for i, t in enumerate(tiers) if src in t)
    tb = next(i for i, t in enumerate(tiers) if dst in t)
    if ta == tb:
        return 0.0, 0, "same tier -- lateral"
    depths = net_levels(tiers, src, dst, terminals)
    if not depths:
        return 0.0, 0, "adjacent tiers -- RDL-level transition, no build-up via"
    return sum(depths), len(depths), " + ".join(f"{d:.0f}" for d in depths)


def stirling2(n, k):
    from math import comb
    return sum((-1) ** j * comb(k, j) * (k - j) ** n for j in range(k + 1)) // \
        __import__("math").factorial(k)


def bookkeeping():
    """Finding 10: the correct count and statement, and the worst via aspect ratio of the
    reference and repartitioned orders under both terminal options (heights from the Z1
    config, capacitor cases A0 / A1 and via diameter from flying_caps.json as the
    realizability figure uses them)."""
    import json
    import math
    import yaml
    counts = {}
    n_all = n_pass = 0
    for k in (2, 3, 4, 5):
        n_k = sum(1 for _ in partitions(COMPS, k))
        assert n_k == math.factorial(k) * stirling2(len(COMPS), k)
        p_k = sum(1 for t in partitions(COMPS, k) if max(geometry(t)[1]) <= CELL_MM2 + 1e-9)
        counts[k] = {"ordered_partitions": n_k, "pass_area_budget": p_k}
        n_all += n_k
        n_pass += p_k
    # which groupings survive: every passing k-tier partition is an order of ONE grouping?
    groupings = {}
    for k in (2, 3, 4, 5):
        g = {frozenset(frozenset(x) for x in t) for t in partitions(COMPS, k)
             if max(geometry(t)[1]) <= CELL_MM2 + 1e-9}
        groupings[k] = sorted(sorted(",".join(sorted(x)) for x in G) for G in g)
        counts[k]["distinct_groupings"] = groupings[k]
    cfg = yaml.safe_load((R / "configs" / "phase0nx" / "z1_physical.yaml").read_text())
    tiers = cfg["converter"]["tiers_from_substrate_upward"]
    um = lambda p: next(float(t["um"]) for t in tiers if t["name"].startswith(p))  # noqa: E731
    fc = json.loads((Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision" / "flying_caps.json").read_text())["summary"]
    d_via = float(fc["min_tier_um_10pct"][-1]) / float(fc["via_AR_10pct"][-1])
    base_h = {"gan_hs": um("gan_hs"), "gan_ls": um("gan_ls"), "cap_fly": um("flying_caps"),
              "cap_out": um("inductor_plus_cout"), "inductor": um("inductor_plus_cout")}
    cases = {"A0": dict(base_h), "A1": dict(base_h, cap_fly=float(fc["min_tier_um_10pct"][-1]))}
    orders = {"reference": [["gan_hs"], ["gan_ls"], ["cap_fly"], ["cap_out", "inductor"]],
              "repartitioned": [["gan_hs"], ["cap_fly"], ["gan_ls"], ["cap_out", "inductor"]]}
    nets = [("hs_to_cf", "gan_hs", "cap_fly"), ("hs_to_ls", "gan_hs", "gan_ls"),
            ("ls_to_L", "gan_ls", "inductor")]
    ar = {}
    for cname, h in cases.items():
        for oname, t in orders.items():
            for term in ("both", "single"):
                per = {}
                for nm, a, b in nets:
                    lv = net_levels(t, a, b, term, h)
                    per[nm] = {"levels_um": lv, "worst_AR": (max(lv) / d_via) if lv else 0.0}
                ar[f"{cname}/{oname}/{term}"] = {
                    "nets": per, "worst_AR": max(v["worst_AR"] for v in per.values()),
                    "worst_net": max(per, key=lambda n: per[n]["worst_AR"])}
    # the best passing candidate under each option (same ranking rule as main())
    best = {}
    for term in ("both", "single"):
        rows = []
        for k in (2, 3, 4, 5):
            for t in partitions(COMPS, k):
                if max(geometry(t)[1]) > CELL_MM2 + 1e-9:
                    continue
                worst = max((max(net_levels(t, a, b, term) or [0.0]) for _, a, b in nets))
                src_ok = "gan_hs" in t[0] and "inductor" in t[-1]
                rows.append((not src_ok, worst, k, " | ".join(",".join(x) for x in t)))
        rows.sort()
        best[term] = {"partition": rows[0][3], "worst_level_um": rows[0][1],
                      "worst_AR_RP_heights": rows[0][1] / d_via,
                      "source_order_compatible": not rows[0][0]}
    out = {"what": "tier-order bookkeeping (TCPMT round 3, finding 10)",
           "generator": "scripts/phase0mr3c/repartition_search.py --bookkeeping",
           "enumeration": "ordered partitions of the 5 component classes (gan_hs, gan_ls, "
                          "cap_fly, cap_out, inductor) into k = 2..5 non-empty tiers ordered "
                          "bottom to top: k! S(5,k) per k",
           "counts_by_k": counts, "n_ordered_partitions": n_all,
           "n_pass_area_budget": n_pass, "cell_area_mm2": CELL_MM2,
           "statement_for_paper": (
               f"The {n_pass} assignments are the ordered partitions of the five component "
               "classes (high-side and low-side devices, flying and output capacitors, "
               f"inductor) into two to five tiers whose every tier fits the cell area, out of "
               f"{n_all}: " + "; ".join(
                   f"{counts[k]['pass_area_budget']} with {k} tiers"
                   + (f" (the {math.factorial(k)} orders of "
                      + " / ".join("{" + g + "}" for g in groupings[k][0]) + ")"
                      if len(groupings[k]) == 1 else "")
                   for k in (2, 3, 4, 5) if counts[k]["pass_area_budget"]) +
               "; no partition into two or three tiers fits."),
           "wrong_statement": "the permutations of the four component tiers (there are 24)",
           "via_diameter_um": d_via, "tier_heights_um": cases,
           "terminal_options": {"both": "production: dies connect from either face",
                                "single": "dies face-down, terminals on the bottom face only; "
                                          "a net leaving a die tier upward crosses it"},
           "worst_aspect_ratio": ar, "best_candidate_by_option": best}
    f = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision" / "tier_order_bookkeeping.json"   # campaign hook
    f.write_text(json.dumps(out, indent=1) + "\n")
    return out


def main() -> int:
    if "--bookkeeping" in sys.argv:
        b = bookkeeping()
        print(b["statement_for_paper"])
        print({k: v["worst_AR"] for k, v in b["worst_aspect_ratio"].items()})
        print(b["best_candidate_by_option"])
        return 0
    rows = []
    for k in (2, 3, 4, 5):
        for tiers in partitions(COMPS, k):
            ext, areas, stack = geometry(tiers)
            if max(areas) > CELL_MM2 + 1e-9:
                continue                                   # area budget violated
            r = {"n_tiers": k,
                 "partition": " | ".join(",".join(t) for t in tiers),
                 "max_tier_area_mm2": round(max(areas), 3),
                 "stack_height_um": round(stack, 1),
                 "height_ok_Z1": stack <= BUDGET["ARCH_Z1_EMBEDDED"]}
            worst = 0.0
            for name, src, dst, _i in NETS:
                d, lv, desc = net_depth(tiers, ext, src, dst)
                r[f"{name}_depth_um"] = round(d, 1)
                r[f"{name}_via_levels"] = lv
                r[f"{name}_detail"] = desc
                worst = max(worst, d)
            r["worst_vertical_depth_um"] = round(worst, 1)
            # the free area in the deepest layer ls_to_L crosses bounds the via field
            ta = next(i for i, t in enumerate(tiers) if "gan_ls" in t)
            tb = next(i for i, t in enumerate(tiers) if "inductor" in t)
            lo, hi = min(ta, tb), max(ta, tb)
            crossed = list(range(lo + 1, hi))
            r["ls_to_L_free_area_mm2"] = round(
                min((CELL_MM2 - areas[t] for t in crossed), default=CELL_MM2), 3)
            # June-2026 Sec. II fixes two ends of the stack: the high-side GaN is
            # flip-chipped to the RDL of the BOTTOM substrate, and the inductors sit in
            # the TOP layer near the POLs. A candidate that keeps both is a reordering
            # WITHIN the sourced architecture; one that does not is a departure from it.
            r["gan_hs_at_bottom"] = "gan_hs" in tiers[0]
            r["inductor_at_top"] = "inductor" in tiers[-1]
            r["source_order_compatible"] = bool(r["gan_hs_at_bottom"]
                                                and r["inductor_at_top"])
            r["is_baseline_T1"] = (
                r["partition"] == "gan_hs | gan_ls | cap_fly | cap_out,inductor")
            rows.append(r)

    rows.sort(key=lambda r: (not r["source_order_compatible"],
                             r["ls_to_L_via_levels"], r["ls_to_L_depth_um"],
                             r["worst_vertical_depth_um"], r["n_tiers"],
                             -r["ls_to_L_free_area_mm2"]))
    with (OUT / "repartition_candidates.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    print(f"cell area {CELL_MM2:.2f} mm2, total component area "
          f"{sum(RP.FOOT_MM2[c]*N_OF[c] for c in COMPS):.2f} mm2 "
          f"-> at least {sum(RP.FOOT_MM2[c]*N_OF[c] for c in COMPS)/CELL_MM2:.2f} tiers\n")
    print(f"{len(rows)} partitions satisfy the per-tier area budget\n")
    n_src = sum(1 for r in rows if r["source_order_compatible"])
    print(f"of those, {n_src} keep the sourced stack ends "
          f"(gan_hs flip-chipped at the bottom, inductor at the top near the POL)\n")
    print(f"{'partition':46s} {'tr':>3} {'ls_lv':>5} {'ls_um':>6} {'worst':>6} "
          f"{'maxA':>6} {'stack':>7} {'src':>4}")
    for r in rows[:10]:
        print(f"{r['partition']:46s} {r['n_tiers']:3d} {r['ls_to_L_via_levels']:5d} "
              f"{r['ls_to_L_depth_um']:6.0f} {r['worst_vertical_depth_um']:6.0f} "
              f"{r['max_tier_area_mm2']:6.2f} {r['stack_height_um']:7.1f} "
              f"{'yes' if r['source_order_compatible'] else 'NO':>4}")
    base = [r for r in rows if r["partition"] ==
            "gan_hs | gan_ls | cap_fly | cap_out,inductor"]
    if base:
        b = base[0]
        print(f"\nfor reference, the Phase-0M-R3 baseline T1_EMBEDDED_4LAYER:")
        print(f"  ls_to_L {b['ls_to_L_via_levels']} level(s), "
              f"{b['ls_to_L_depth_um']:.0f} um; worst vertical "
              f"{b['worst_vertical_depth_um']:.0f} um; stack {b['stack_height_um']:.1f} um")
    return 0


if __name__ == "__main__":
    sys.exit(main())
