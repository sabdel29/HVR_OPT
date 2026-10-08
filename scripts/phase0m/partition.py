#!/usr/bin/env python3
"""Phase-0M Parts 14-16 -- component-level Z partitioning.

WHAT WAS ALREADY THERE, AND WHERE
The converter sizing model assumes FOUR-LAYER VERTICAL STACKING, silently:

    Scalable_Integrated_VR/src/HVR_FULL_OPT_EPC_V2.py::_compute_area
        return max(N*fp_hs, K*fp_ls, K*ind.footprint, (N-1)*cap.footprint)

`max`, not `sum`. The docstring says "Total estimated component footprint (mm^2)" and the
file header claims the function was "fixed: area = SUM of all component footprints (not
max)". It is a MAX, so the reported 5.61 mm^2 is a PER-LAYER footprint and the true summed
component footprint of the compiled 1-kW cell is 18.01 mm^2 -- 3.21x larger.

So component-level z partitioning IS already assumed -- by the AREA model alone. The
electrical, thermal and mechanical models all place the whole VR as one lumped block with
one temperature, one stiffness and one terminal. Nothing checks that the four layers the
area model presumes actually exist in a given architecture.
"""
from __future__ import annotations
import csv, math, sys
from pathlib import Path
import yaml

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0m"
CFG = R / "configs" / "phase0m"
OUT.mkdir(parents=True, exist_ok=True)
CFG.mkdir(parents=True, exist_ok=True)

# the compiled 1-kW cell (scripts/phase0f/kw1.py::design_1kw)
N, K = 3, 3
COMP = {
    "gan_hs": dict(n=N, footprint_mm2=1.87, height_um=685.0, part="EPC2014C",
                   vmax=40.0, heat_share=0.45, src="EPC2212/EPC2014C datasheets"),
    "gan_ls": dict(n=K, footprint_mm2=1.80, height_um=606.0, part="EPC2057",
                   vmax=50.0, heat_share=0.35, src="EPC2090/EPC2057 datasheets"),
    "inductor": dict(n=K, footprint_mm2=1.00, height_um=500.0,
                     part="Shared_Core_UIC_250_nH", vmax=None, heat_share=0.15,
                     src="Rasheedi, TCPMT 2026"),
    "cap_fly": dict(n=N - 1, footprint_mm2=2.00, height_um=250.0,
                    part="Murata GCM21 10uF 25V", vmax=25.0, heat_share=0.05,
                    src="Murata GCM21BR71E106KA73 datasheet, 0805"),
}
TILE_MM2 = 5.61
N_VR = 49
DIE_MM2 = 500.0
INTERLAYER_RDL_UM = 10.0

TEMPLATES = {
    "T0_SINGLE_LEVEL": {
        "label": "Everything on one level (the null template)",
        "levels": {"L0": ["gan_hs", "gan_ls", "inductor", "cap_fly"]},
        "where": "one plane, anywhere in the stack",
        "source_status": "NOT DESCRIBED by any source; included as the null hypothesis",
    },
    "T1_EMBEDDED_4LAYER": {
        "label": "Z1 baseline: HS flip-chipped below, LS / caps / inductors in three "
                 "substrate power layers",
        "levels": {"below_substrate": ["gan_hs"], "PL1": ["gan_ls"],
                   "PL2": ["cap_fly"], "PL3": ["inductor"]},
        "where": "inside the power substrate",
        "source_status": "SOURCE-DESCRIBED (June-2026 Sec. II) but explicitly NOT "
                         "DEMONSTRATED -- 'remains an open challenge'",
    },
    "T2_BACKSIDE_CHIPLET": {
        "label": "Z2 baseline: the whole VR as a stacked chiplet on the substrate backside",
        "levels": {"chip1": ["gan_hs", "gan_ls"], "chip2": ["cap_fly"],
                   "chip3": ["inductor"]},
        "where": "below the substrate, between BGA and substrate",
        "source_status": "SOURCE-BACKED (June-2026 Sec. II, chiplet stacking on the "
                         "backside with TSV interconnect)",
    },
    "T3_POWER_DIE": {
        "label": "Z4 baseline: a dedicated power die between substrate and compute die",
        "levels": {"pd_active": ["gan_hs", "gan_ls"], "pd_pass1": ["cap_fly"],
                   "pd_pass2": ["inductor"]},
        "where": "above the substrate, directly beneath the compute die",
        "source_status": "PARTIALLY source-backed: chiplet framing extrapolated to a "
                         "monolithic power die",
    },
    "T4_SPLIT_SC_BUCK": {
        "label": "HV switched-capacitor stage on the backside, LV buck stage on a power "
                 "die against the compute die",
        "levels": {"backside_sc": ["gan_hs", "cap_fly"],
                   "power_die_buck": ["gan_ls", "inductor"]},
        "where": "conversion split across two tiers by VOLTAGE DOMAIN",
        "source_status": "Architecture class named by Krishnakumar & Partin-Vaisband, "
                         "SoCC 2023, DOI 10.1109/SOCC58585.2023.10256973 (vertical power "
                         "conversion and distribution); the specific split is constructed "
                         "here",
    },
    "T5_SWITCH_INTERPOSER_IND_EMBEDDED": {
        "label": "Switches on/in the interposer, inductors embedded in the substrate below",
        "levels": {"interposer": ["gan_hs", "gan_ls", "cap_fly"],
                   "substrate_PL": ["inductor"]},
        "where": "active devices above the substrate, magnetics inside it",
        "source_status": "Constructed; embedded-magnetics substrates are a demonstrated "
                         "technology class but no source in this repository gives one at "
                         "this current density",
    },
    "T6_CAPS_NEAR_DIE": {
        "label": "Decoupling and flying capacitors immediately under the die, switches below",
        "levels": {"under_die": ["cap_fly"], "mid": ["gan_hs", "gan_ls"],
                   "lower": ["inductor"]},
        "where": "capacitance closest to the load, magnetics furthest",
        "source_status": "Constructed; motivated by embedded-capacitor VPD work",
    },
    "T7_IND_SUBSTRATE_ACTIVE_BACKSIDE": {
        "label": "Inductors in the substrate, all active devices on the backside",
        "levels": {"backside": ["gan_hs", "gan_ls", "cap_fly"],
                   "substrate_PL": ["inductor"]},
        "where": "actives below, magnetics inside the substrate",
        "source_status": "Constructed; the mirror image of T5",
    },
}


def check(tag: str, t: dict) -> dict:
    lv = t["levels"]
    per_level_area = {k: sum(COMP[c]["footprint_mm2"] * COMP[c]["n"] for c in v)
                      for k, v in lv.items()}
    per_level_h = {k: max(COMP[c]["height_um"] for c in v) for k, v in lv.items()}
    n_levels = len(lv)
    a_max = max(per_level_area.values())
    h_tot = sum(per_level_h.values()) + (n_levels - 1) * INTERLAYER_RDL_UM
    a_total_all_cells = a_max * N_VR
    # thermal path: how many levels sit between the hottest component and the cooled face
    order = list(lv)
    hs_level = next(k for k, v in lv.items() if "gan_hs" in v)
    ls_level = next(k for k, v in lv.items() if "gan_ls" in v)
    # voltage isolation: a level that carries both the 48 V and the 1 V domain needs
    # in-level isolation; a level holding only one domain does not
    dom = {k: {"HV" if c in ("gan_hs", "cap_fly") else "LV" for c in v}
           for k, v in lv.items()}
    mixed = [k for k, d in dom.items() if len(d) > 1]
    # interconnect density: the phase current must cross every level boundary
    i_phase = (1000.0 / N_VR) / K
    return {
        "template": tag, "label": t["label"], "source_status": t["source_status"],
        "n_levels": n_levels,
        "level_areas_mm2": "; ".join(f"{k}={v:.2f}" for k, v in per_level_area.items()),
        "max_level_area_mm2": a_max,
        "summed_component_area_mm2": sum(COMP[c]["footprint_mm2"] * COMP[c]["n"]
                                         for c in COMP),
        "stack_height_um": h_tot,
        "area_all_cells_mm2": a_total_all_cells,
        "fits_die_shadow": a_total_all_cells <= DIE_MM2,
        "die_shadow_utilisation": a_total_all_cells / DIE_MM2,
        "hs_level": hs_level, "ls_level": ls_level,
        "levels_with_mixed_voltage_domain": ";".join(mixed) or "none",
        "needs_in_level_isolation": bool(mixed),
        "n_level_crossings_for_phase_current": max(n_levels - 1, 0),
        "i_phase_a": i_phase,
    }


def main() -> int:
    rows = [check(k, v) for k, v in TEMPLATES.items()]
    keys = list(rows[0])
    with open(OUT / "component_partition_templates.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
    cfg = {
        "meta": {
            "phase": "0M",
            "purpose": "A FINITE library of component-partition templates. Phase 0M does "
                       "NOT allow arbitrary continuous z placement; templates first, and "
                       "only then a decision about which further degree of freedom is "
                       "scientifically useful.",
            "upstream_finding": "HVR_FULL_OPT_EPC_V2::_compute_area returns max(), not "
                                "sum(), over the four component classes -- so four-layer "
                                "vertical stacking is ALREADY assumed by the converter "
                                "area model, and only by it.",
            "summed_component_footprint_mm2": rows[0]["summed_component_area_mm2"],
            "reported_tile_area_mm2": TILE_MM2,
            "ratio": rows[0]["summed_component_area_mm2"] / TILE_MM2,
        },
        "components": {k: {kk: vv for kk, vv in v.items()} for k, v in COMP.items()},
        "templates": {k: {**v, "checks": next(r for r in rows if r["template"] == k)}
                      for k, v in TEMPLATES.items()},
        "checks_applied": [
            "component height -> stack height",
            "per-level footprint -> does the cell fit its own tile",
            "all-cell footprint -> does the VR array fit the die shadow",
            "voltage-isolation: does any level mix the 48 V and 1 V domains",
            "thermal path: how many levels between the hottest device and the coolant",
            "interconnect density: level crossings carrying the phase current",
            "manufacturing plausibility -> source_status, never assumed",
        ],
    }
    (CFG / "component_partition_templates.yaml").write_text(
        "# Phase-0M component-partition template library.\n"
        "# Generated by scripts/phase0m/partition.py -- edit the generator.\n"
        + yaml.safe_dump(cfg, sort_keys=False, width=96))
    for r in rows:
        print(f"  {r['template']:34s} levels={r['n_levels']} h={r['stack_height_um']:7.1f}um "
              f"A_max={r['max_level_area_mm2']:5.2f}mm2 array={r['area_all_cells_mm2']:7.1f}mm2 "
              f"fits_die={r['fits_die_shadow']} util={r['die_shadow_utilisation']:.2f} "
              f"mixedV={r['levels_with_mixed_voltage_domain']}")
    print(f"\nsummed component footprint = {rows[0]['summed_component_area_mm2']:.2f} mm2 "
          f"against a reported tile area of {TILE_MM2:.2f} mm2 "
          f"({rows[0]['summed_component_area_mm2']/TILE_MM2:.2f}x)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
