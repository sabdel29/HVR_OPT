#!/usr/bin/env python3
"""Phase-0M-R3C Section 4 --- bounded repartition search over EXISTING components.

Enumerates every ordered assignment of the five existing component classes into tiers,
subject to the cell-area budget, and scores by the dielectric depth each high-current net
must cross. Nothing new is introduced: no device, no dimension change, no relaxed spec.

The objective is the brief's hierarchy: fewest vertical levels for the 20.408 A ls_to_L
net, then the other vertical nets.
"""
from __future__ import annotations
import csv, itertools, sys
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


def net_depth(tiers, ext, src, dst):
    """Total dielectric depth the net must cross, and how many via levels."""
    ta = next(i for i, t in enumerate(tiers) if src in t)
    tb = next(i for i, t in enumerate(tiers) if dst in t)
    if ta == tb:
        return 0.0, 0, "same tier -- lateral"
    lo, hi = min(ta, tb), max(ta, tb)
    depths = [max(RP.H_UM[c] for c in tiers[t]) for t in range(lo + 1, hi)]
    if not depths:
        return 0.0, 0, "adjacent tiers -- RDL-level transition, no build-up via"
    return sum(depths), len(depths), " + ".join(f"{d:.0f}" for d in depths)


def main() -> int:
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
