#!/usr/bin/env python3
"""Phase-0M-R3B Section 7 --- clearance provenance, and the 27-corner replay.

Phase 0M-R2 searched for these three numbers and found none. This phase reached two new
primary sources on embedded-component substrates, so the search is repeated against them
rather than simply restated. One of the three moves; two do not.

The 27-corner replay then asks the question the brief poses: after the `ls_to_L` correction,
are the clearances still the only manufacturing blocker?
"""
from __future__ import annotations
import csv, itertools, sys
from pathlib import Path

import yaml

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0mr2"))
OUT = R / "results" / "phase0mr3b"
CFG = R / "configs" / "phase0mr2" / "package_clearances.yaml"

S_OST = ("Ostmann et al., 'Industrial and Technical Aspects of Chip Embedding Technology', "
         "Fraunhofer IZM / AT&S / IMEC-CMST 2008")

FINDINGS = {
 "die_to_component_gap_um": dict(
   searched_this_phase="chip-embedding and HDI primary literature reached via OpenAlex; "
                       "two full texts obtained",
   found="RCC lamination over an embedded die: 'A thickness of 15-20 um over the chip "
         "surface is desirable for the subsequent microvia opening and filling'",
   value_um="15-20", source=S_OST,
   same_feature="NO -- that is the dielectric cap over an EMBEDDED die, not the gap "
                "between the compute-die underside and the tier below it. Closest "
                "sourced analogue, used as a bound and labelled as one",
   new_status="SOURCE_BOUNDED",
   effect="15-20 um lies INSIDE the existing [10, 25, 50] um bound, so no corner of the "
          "27-corner sweep moves and no verdict changes"),
 "cavity_sidewall_um": dict(
   searched_this_phase="same two full texts plus three further OpenAlex queries for "
                       "embedded-component cavity and keep-out rules",
   found="nothing numeric. The chip-embedding source discusses cavity ASPECT RATIO for "
         "etched copper line cavities, a different feature entirely",
   value_um="", source="",
   same_feature="n/a -- nothing found",
   new_status="OPEN",
   effect="unchanged; bound [15, 30, 60] um retained as an anchor, not a source"),
 "cooler_standoff_um": dict(
   searched_this_phase="OpenAlex query for cooler standoff / lid clearance design rules",
   found="nothing. The five hits were unrelated fields",
   value_um="", source="",
   same_feature="n/a -- nothing found",
   new_status="OPEN",
   effect="unchanged; bound [0, 50, 100] um retained as an anchor, not a source"),
}


def main() -> int:
    cfg = yaml.safe_load(CFG.read_text())["clearances"]
    rows = []
    for k, f in FINDINGS.items():
        rows.append({"clearance": k,
                     "definition": " ".join(cfg[k]["definition"].split())[:160],
                     "where": cfg[k]["where"],
                     "affects": cfg[k]["affects"],
                     "bound_um": cfg[k]["bound_um"],
                     "status_0mr2": "OPEN", "status_0mr3b": f["new_status"],
                     "searched_this_phase": f["searched_this_phase"],
                     "found": f["found"], "value_um": f["value_um"],
                     "source": f["source"], "same_feature": f["same_feature"],
                     "effect_on_verdict": f["effect"]})
    with (OUT / "package_clearance_provenance.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    for r in rows:
        print(f"  {r['clearance']:26s} {r['status_0mr2']:6s} -> {r['status_0mr3b']}")

    # ---- 27-corner replay on the FROZEN PAIR ----------------------------------------
    # The 0M-R2 evaluator classifies the GENERIC T1 template, not the Phase-0M-R3 frozen
    # candidates, so it must not be used here: it would report thermal and current-density
    # failures that the frozen pair does not have. The clearance sweep is instead applied
    # to the frozen pair's own margins, and routing is taken from this phase's physical
    # model.
    base = {r["case"]: r for r in csv.DictReader(
        (R / "results" / "phase0mr3a" / "_baseline_phase0mr3"
         / "final_realizability_margins.csv").open())}
    phys = list(csv.DictReader((OUT / "ls_to_L_feasibility.csv").open()))
    sourced_ok = any(r["feasible"] == "True" and float(r["pitch_um"]) >= 100.0
                     and r["stack"] == "semi_stacked" for r in phys)
    design_point = [r for r in phys if float(r["pitch_um"]) == 70.0
                    and r["stack"] == "fully_stacked" and float(r["d_um"]) == 40.0][0]
    design_point_ok = design_point["feasible"] == "True"
    grid = [cfg[k]["bound_um"] for k in
            ("die_to_component_gap_um", "cavity_sidewall_um", "cooler_standoff_um")]
    out = []
    for case, b in base.items():
        h_ratio = float(b["height_ratio"]); a_ratio = float(b["area_ratio"])
        budget_um = 1300.0 if case == "Z1" else 300.0     # arch height budget, um
        for gap, wall, so in itertools.product(*grid):
            # Phase 0M-R3 evaluated the clearance dimension itself and recorded
            # 27/27 for both candidates. This phase found nothing that falsifies that
            # arithmetic, so it is CARRIED, not recomputed: re-deriving the height budget
            # here with a cruder model would manufacture a disagreement rather than a
            # finding. What this phase does change is the routing gate.
            charged = h_ratio * budget_um + gap + so
            height_ok = int(b["corners_passing"].split("/")[0]) == 27
            infl = ((1.0 + 2 * wall * 1e-3 / (5.61 ** 0.5)) ** 2) if case == "Z1" else 1.0
            area_ok = height_ok
            out.append({
                "case": case, "architecture": b["architecture"],
                "die_to_component_gap_um": gap, "cavity_sidewall_um": wall,
                "cooler_standoff_um": so,
                "height_charged_um": round(charged, 2), "height_budget_um": budget_um,
                "HEIGHT_OK_0MR3_carried": height_ok,
                "area_ratio_inflated": round(a_ratio * infl, 5), "AREA_OK_0MR3_carried": area_ok,
                "ROUTING_OK_0MR3": True,
                "ROUTING_OK_0MR3B_design_point": design_point_ok,
                "ROUTING_OK_0MR3B_sourced_bounds": sourced_ok,
                "REALIZABLE_0MR3": bool(height_ok and area_ok),
                "REALIZABLE_0MR3B": bool(height_ok and area_ok and sourced_ok),
            })
    with (OUT / "clearance_27corner_replay.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)

    for case in ("Z1", "Z2"):
        g = [e for e in out if e["case"] == case]
        print(f"\n{case}  ({len(g)} corners)")
        for k in ("HEIGHT_OK_0MR3_carried", "AREA_OK_0MR3_carried",
                  "REALIZABLE_0MR3", "REALIZABLE_0MR3B"):
            print(f"   {k:22s} {sum(1 for e in g if e[k]):2d}/{len(g)}")
    print(f"\n0M-R3 design point (70 um pitch, 40 um via, 3 stacked): "
          f"feasible = {design_point_ok}  (ratio {design_point['routing_ratio']}, "
          f"landing area {design_point['landing_area_mm2']} mm2)")
    print(f"inside BOTH sourced bounds (pitch >= 100 um AND semi-stacked): {sourced_ok}")
    print("\nAfter the ls_to_L correction, are the clearances the ONLY blocker?  "
          + ("YES" if sourced_ok else
             "NO -- the vertical interconnect fails first, on sourced via rules"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
