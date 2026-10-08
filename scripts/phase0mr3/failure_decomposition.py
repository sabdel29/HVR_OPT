#!/usr/bin/env python3
"""Phase-0M-R3 Section 3 --- why each of the 12 combinations fails, QUANTIFIED.

"Fails area" is not actionable. A ratio is: area_required / area_available = 1.0383 says
the deficit is 3.8 % and may be reachable from the existing library, while
routing_required / routing_available = 8.6 says no repackaging will ever close it.
Every condition is therefore reported as a distance-to-feasibility ratio, and the
constraints are ranked by that distance.
"""
from __future__ import annotations

import csv
import itertools
import math
import sys
from pathlib import Path

import yaml

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0mr3", "scripts/phase0mr2", "scripts/phase0mr", "scripts/phase0i",
          "scripts/phase0m", "scripts"):
    sys.path.insert(0, str(R / p))

import arch_geometry as AG                                               # noqa: E402
import component_stack as CS                                             # noqa: E402
import routing_production as RP                                          # noqa: E402

OUT = R / "results" / "phase0mr3"
ARCHES = ["ARCH_Z1_EMBEDDED", "ARCH_Z2_BACKSIDE", "ARCH_Z4_POWER_DIE"]
CLEAR = yaml.safe_load(
    (R / "configs" / "phase0mr2" / "package_clearances.yaml").read_text())["clearances"]


def ratios(template: str, arch: str, gap: float, wall: float, stand: float) -> dict:
    """Every hard condition as required/available. >1 means infeasible."""
    c = CS.classify(template, arch)
    rl = RP.template_loss(template)

    # --- A area, with the cavity sidewall charged for the embedded architecture
    side = math.sqrt(max(c["max_level_area_mm2"], 1e-12))
    infl = ((side + 2 * wall * 1e-3) / side) ** 2 if arch == "ARCH_Z1_EMBEDDED" else 1.0
    area_req = c["max_level_area_mm2"] * infl
    area_av = c["per_cell_budget_mm2"]

    # --- B/C height, gap and standoff charged together
    h_req = c["height_charged_um"] + gap + stand
    h_av = c["arch_space_um"]

    # --- D routing: EVERY net, lateral and vertical. Filtering to lateral missed
    # `ls_to_L`, a vertical via stack carrying 20.4 A at 1.236x the vias available --
    # the actual binding routing constraint.
    worst, worst_net, worst_geom = 0.0, "", ""
    for e in RP.build_edges(template):
        s = RP.edge_loss(e, 10e-6, 9, 1.0e8, RP.DESIGN["tile_side_mm"], 85.0,
                         "D_area_optimal")
        if s["shortfall_x"] > worst:
            worst, worst_net, worst_geom = s["shortfall_x"], e.name, e.geom

    # --- F/G TSV
    sp = AG.span(arch)
    i_tsv = 1000.0 if sp.rail == "LV" else 1000.0 / 0.889 / 48.0
    fld = AG.field(arch, i_tsv)

    return {
        "template": template, "arch": arch,
        "gap_um": gap, "wall_um": wall, "standoff_um": stand,
        "area_required_mm2": area_req, "area_available_mm2": area_av,
        "area_ratio": area_req / area_av,
        "height_required_um": h_req, "height_available_um": h_av,
        "height_ratio": h_req / h_av,
        "routing_worst_net": worst_net, "routing_worst_geom": worst_geom,
        "routing_ratio": worst,
        "J_design": fld["J_design"], "J_process_max": fld["J_process_max"],
        "current_density_ratio": fld["J_actual"] / fld["J_design"],
        "n_tsv_required": fld["n_required"], "n_tsv_available": fld["n_available"],
        "tsv_count_ratio": fld["n_required"] / max(fld["n_available"], 1),
        "tsv_AR": sp.aspect_ratio, "tsv_AR_max": sp.aspect_ratio_max,
        "tsv_AR_ratio": sp.aspect_ratio / sp.aspect_ratio_max,
        "tsv_AR_margin": sp.aspect_ratio_max / sp.aspect_ratio,
        "thermal_feasible": bool(c["THERMAL_FEASIBLE"]),
        "n_routing_infeasible": rl["n_infeasible"],
        "clearance_sourcing": "OPEN",
    }


def main() -> int:
    gaps = CLEAR["die_to_component_gap_um"]["bound_um"]
    walls = CLEAR["cavity_sidewall_um"]["bound_um"]
    stands = CLEAR["cooler_standoff_um"]["bound_um"]
    best_corner = (min(gaps), min(walls), min(stands))

    rows = []
    for tpl, arch in itertools.product(RP.TEMPLATES, ARCHES):
        for g, w, s in itertools.product(gaps, walls, stands):
            r = ratios(tpl, arch, g, w, s)
            r["corner"] = ("BEST" if (g, w, s) == best_corner else "swept")
            rows.append(r)

    with open(OUT / "realizability_failure_matrix.csv", "w", newline="") as fh:
        k = sorted({x for r in rows for x in r})
        wr = csv.DictWriter(fh, fieldnames=k); wr.writeheader(); wr.writerows(rows)

    # rank constraints at the MOST FAVOURABLE clearance corner
    best = [r for r in rows if r["corner"] == "BEST"]
    RATIOS = [("area", "area_ratio"), ("height", "height_ratio"),
              ("routing", "routing_ratio"), ("current density", "current_density_ratio"),
              ("TSV count", "tsv_count_ratio"), ("TSV AR", "tsv_AR_ratio")]
    print("  at the MOST FAVOURABLE clearance corner "
          f"(gap {best_corner[0]}, wall {best_corner[1]}, standoff {best_corner[2]} um):\n")
    print("  %-22s %-14s %s" % ("template", "arch", "  ".join(f"{n:>10s}" for n, _ in RATIOS)))
    for r in best:
        print("  %-22s %-14s %s" % (
            r["template"], r["arch"].replace("ARCH_", ""),
            "  ".join(f"{r[k]:10.4f}" for _, k in RATIOS)))
    print("\n  distance to feasibility, worst case over the 12 combinations:")
    for n, k in RATIOS:
        v = [r[k] for r in best]
        worst = max(v)
        n_fail = sum(1 for x in v if x > 1.0 + 1e-9)
        print(f"    {n:16s} worst = {worst:8.4f}   fails {n_fail:2d}/12   "
              f"{'REPAIRABLE-SCALE' if worst < 1.5 else 'STRUCTURAL' if worst > 3 else 'HARD'}")
    print(f"\nwrote {OUT/'realizability_failure_matrix.csv'} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
