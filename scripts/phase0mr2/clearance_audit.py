#!/usr/bin/env python3
"""Phase-0M-R2 Section 4 --- the three open clearances, bounded and swept.

Phase 0M-R said every partition template fails FULLY_REALIZABLE "because three package
clearances are OPEN". That is only part of the truth, and this module separates the six
feasibility dimensions so the real causes are visible rather than collapsed into one
Boolean.

No clearance is given a single "reasonable" value. Each is swept over the bounded
envelope declared in configs/phase0mr2/package_clearances.yaml, and each template is
reported as realizable over the WHOLE bound, infeasible over the whole bound, or
bound-dependent.
"""
from __future__ import annotations

import csv
import itertools
import sys
from pathlib import Path

import yaml

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0mr", "scripts/phase0i", "scripts/phase0m", "scripts"):
    sys.path.insert(0, str(R / p))

import component_stack as CS                                            # noqa: E402
import routing_production as RP                                         # noqa: E402

CFG = R / "configs" / "phase0mr2" / "package_clearances.yaml"
OUT = R / "results" / "phase0mr2"

ARCHES = ["ARCH_Z1_EMBEDDED", "ARCH_Z2_BACKSIDE", "ARCH_Z4_POWER_DIE"]

DIMENSIONS = ["AREA_FEASIBLE", "HEIGHT_FEASIBLE", "THERMAL_FEASIBLE",
              "ROUTING_FEASIBLE", "CURRENT_DENSITY_FEASIBLE",
              "PACKAGE_CLEARANCE_SATISFIED"]


def cfg() -> dict:
    return yaml.safe_load(CFG.read_text())


def evaluate(template: str, arch: str, gap_um: float, wall_um: float,
             standoff_um: float) -> dict:
    """Six independent questions at one corner of the clearance bound."""
    c = CS.classify(template, arch)

    # HEIGHT: the die-to-component gap and the cooler standoff both consume the same
    # vertical budget, so they are charged TOGETHER (they are declared coupled).
    charged = c["height_charged_um"] + gap_um + standoff_um
    height_ok = charged <= c["arch_space_um"]

    # AREA: the cavity sidewall inflates each embedded component's in-plane footprint.
    # It applies to ARCH_Z1 only, which is the architecture that embeds components.
    if arch == "ARCH_Z1_EMBEDDED":
        # a square component of side s grows to s + 2*wall
        import math
        side = math.sqrt(max(c["max_level_area_mm2"], 1e-12))
        area_infl = ((side + 2 * wall_um * 1e-3) / side) ** 2
    else:
        area_infl = 1.0
    area_mm2 = c["max_level_area_mm2"] * area_infl
    area_ok = area_mm2 <= c["per_cell_budget_mm2"]

    return {
        "template": template, "arch": arch,
        "die_to_component_gap_um": gap_um, "cavity_sidewall_um": wall_um,
        "cooler_standoff_um": standoff_um,
        "height_charged_um": charged, "height_budget_um": c["arch_space_um"],
        "height_margin_um": c["arch_space_um"] - charged,
        "area_per_cell_mm2": area_mm2, "area_budget_mm2": c["per_cell_budget_mm2"],
        "area_margin_pct": 100.0 * (c["per_cell_budget_mm2"] - area_mm2)
        / c["per_cell_budget_mm2"],
        "AREA_FEASIBLE": bool(area_ok),
        "HEIGHT_FEASIBLE": bool(height_ok),
        "THERMAL_FEASIBLE": bool(c["THERMAL_FEASIBLE"]),
        "ROUTING_FEASIBLE": bool(c["ROUTING_FEASIBLE"]),
        "CURRENT_DENSITY_FEASIBLE": bool(c["CURRENT_DENSITY_FEASIBLE"]),
        # at a stated clearance corner the clearance question IS answered; what remains
        # open is the SOURCING, which is reported separately and never as feasibility
        "PACKAGE_CLEARANCE_SATISFIED": bool(height_ok and area_ok),
        "clearance_sourcing": "OPEN",
        "FULLY_REALIZABLE": bool(
            area_ok and height_ok and c["THERMAL_FEASIBLE"]
            and c["ROUTING_FEASIBLE"] and c["CURRENT_DENSITY_FEASIBLE"]),
    }


def main() -> int:
    c = cfg()["clearances"]
    gaps = c["die_to_component_gap_um"]["bound_um"]
    walls = c["cavity_sidewall_um"]["bound_um"]
    stands = c["cooler_standoff_um"]["bound_um"]

    rows = []
    for tpl, arch in itertools.product(RP.TEMPLATES, ARCHES):
        for g, w, s in itertools.product(gaps, walls, stands):
            rows.append(evaluate(tpl, arch, g, w, s))

    # per template/arch: does the verdict depend on the bound?
    summary = []
    for tpl, arch in itertools.product(RP.TEMPLATES, ARCHES):
        sub = [r for r in rows if r["template"] == tpl and r["arch"] == arch]
        rec = {"template": tpl, "arch": arch, "n_corners": len(sub)}
        for d in DIMENSIONS + ["FULLY_REALIZABLE"]:
            vals = {r[d] for r in sub}
            rec[d] = ("ALWAYS" if vals == {True} else
                      "NEVER" if vals == {False} else "BOUND_DEPENDENT")
        # the causes of failure, preserved rather than collapsed
        always_fail = [d for d in DIMENSIONS if rec[d] == "NEVER"]
        rec["blocking_dimensions"] = "; ".join(always_fail) or "none"
        rec["n_blocking"] = len(always_fail)
        summary.append(rec)
        print(f"  {tpl:22s} {arch.replace('ARCH_',''):14s} "
              f"FULLY_REALIZABLE={rec['FULLY_REALIZABLE']:16s} "
              f"blocked by: {rec['blocking_dimensions']}", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "component_partition_feasibility_r2.csv", "w", newline="") as fh:
        k = sorted({x for r in rows for x in r})
        w_ = csv.DictWriter(fh, fieldnames=k); w_.writeheader(); w_.writerows(rows)
    with open(OUT / "clearance_provenance.csv", "w", newline="") as fh:
        pr = []
        for name, v in cfg()["clearances"].items():
            pr.append({"clearance": name, "definition": v["definition"],
                       "where": v["where"], "sourcing_status": v["sourcing"],
                       "current_default": v["current_default"],
                       "bound_um": str(v["bound_um"]), "bound_anchor": v["bound_anchor"],
                       "why_it_matters": v["why_it_matters"], "affects": v["affects"],
                       "coupled_to": v["coupled_to"] or "independent"})
        w_ = csv.DictWriter(fh, fieldnames=list(pr[0])); w_.writeheader(); w_.writerows(pr)
    n_real = sum(1 for s in summary if s["FULLY_REALIZABLE"] != "NEVER")
    print(f"\n{len(summary)} template x architecture combinations, "
          f"{n_real} not-always-infeasible")
    print(f"wrote {OUT/'component_partition_feasibility_r2.csv'} "
          f"({len(rows)} bound corners) and clearance_provenance.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
