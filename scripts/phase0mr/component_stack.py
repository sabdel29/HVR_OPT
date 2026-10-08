#!/usr/bin/env python3
"""Phase-0M-R Section 7 -- component partition templates as PHYSICAL GEOMETRY.

Phase 0M classified templates as "fits" on AREA alone. Area is one of six independent
feasibility questions and it is not the binding one. This module builds the full z-envelope
of each template and classifies each question separately:

    AREA_FEASIBLE            the per-level footprint fits the tile, and the array fits the die
    HEIGHT_FEASIBLE          the stack fits the space the architecture actually offers
    ROUTING_FEASIBLE         every net can be routed at the available width / via count
    CURRENT_DENSITY_FEASIBLE every conductor stays inside the sourced J envelope
    THERMAL_FEASIBLE         the heat path out of the deepest component exists
    PACKAGE_CLEARANCE_OPEN   a clearance the sources do not give is OPEN, never assumed zero
    FULLY_REALIZABLE         all of the above, with no OPEN

A missing manufacturing clearance is marked OPEN and the template is NOT called buildable.
Inventing a 0 um clearance would turn an unknown into a pass.
"""
from __future__ import annotations
import csv, math, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for d in ("phase0mr", "phase0m"):
    sys.path.insert(0, str(R / "scripts" / d))
import routing_production as RP                                            # noqa: E402

OUT = R / "results" / "phase0mr"
OUT.mkdir(parents=True, exist_ok=True)

DIE_MM2, N_VR, TILE_MM2 = 500.0, 49, 5.61
# how much vertical space each architecture actually offers the VR stack
ARCH_ENVELOPE_UM = {
    "ARCH_Z1_EMBEDDED": {"space": 1300.0 - 50.0,
                         "why": "substrate thickness minus the minimum TSV stub beneath the "
                                "embedded cell (Phase 0H / 0I realizability rule)"},
    "ARCH_Z2_BACKSIDE": {"space": 1100.0,
                         "why": "the backside chiplet stack between BGA and substrate, from "
                                "the Phase-0I z-table"},
    "ARCH_Z4_POWER_DIE": {"space": 1200.0,
                          "why": "the power-die layer between substrate and compute die, "
                                 "from the Phase-0I z-table"},
}
# clearances the sources DO NOT give
OPEN_CLEARANCES = {
    "die_to_component_gap_um": "no source gives the minimum clearance between the compute "
                               "die underside and the tallest VR component",
    "cavity_sidewall_um": "no source gives the cavity sidewall allowance for an embedded "
                          "component",
    "cooler_standoff_um": "no source gives the standoff between the cooled surface and the "
                          "nearest active component",
}
J_CU, J_SOLDER = 1.0e8, 3.97e7


def envelope(template: str) -> dict:
    tiers = RP.TEMPLATES[template]
    z, rows = 0.0, []
    for i, tier in enumerate(tiers):
        h = max(RP.H_UM[c] for c in tier)
        rows.append({"tier": i, "components": "+".join(tier), "z_min_um": z,
                     "z_max_um": z + h, "tier_height_um": h,
                     "rdl_above_um": RP.RDL_UM if i < len(tiers) - 1 else 0.0})
        z += h + (RP.RDL_UM if i < len(tiers) - 1 else 0.0)
    return {"template": template, "n_tiers": len(tiers), "stack_height_um": z,
            "tiers": rows}


def classify(template: str, arch: str) -> dict:
    n_of = {"gan_hs": 3, "gan_ls": 3, "cap_fly": 2, "cap_out": 1, "inductor": 3}
    env = envelope(template)
    tiers = RP.TEMPLATES[template]
    areas = [sum(RP.FOOT_MM2[c] * n_of[c] for c in t) for t in tiers]
    a_max = max(areas)
    array = a_max * N_VR
    space = ARCH_ENVELOPE_UM[arch]["space"]
    # June-2026 Sec. II and the Phase-0I z-table put the HIGH-SIDE device BELOW z = 0,
    # flip-chipped to the bottom RDL of the substrate, so for the embedded architecture it
    # does not consume substrate thickness. Charging it against h_sub would fail the height
    # check for a component that is not in the substrate.
    outside = ({"gan_hs"} if arch == "ARCH_Z1_EMBEDDED" else set())
    inside_h = 0.0
    for i, t in enumerate(tiers):
        if set(t) <= outside:
            continue
        inside_h += max(RP.H_UM[c] for c in t) + (RP.RDL_UM if i < len(tiers) - 1 else 0.0)
    h_used = inside_h
    rt = RP.template_loss(template, t_cu_m=10e-6, n_layers=9, via_policy="D_area_optimal")
    # current density on the worst lateral net at the reference single-layer stack
    rt1 = RP.template_loss(template, t_cu_m=10e-6, n_layers=1, via_policy="D_area_optimal")
    # thermal path: how many tiers sit between the hottest device and the cooled face
    hs_tier = RP.tier_of(template, "gan_hs")
    depth = (len(tiers) - 1 - hs_tier) if arch != "ARCH_Z2_BACKSIDE" else hs_tier
    out = {
        "template": template, "arch": arch, "n_tiers": env["n_tiers"],
        "stack_height_um": env["stack_height_um"],
        "arch_space_um": space, "height_charged_um": h_used,
        "components_outside_envelope": "+".join(sorted(outside)) or "none",
        "space_margin_um": space - h_used,
        "max_level_area_mm2": a_max, "array_area_mm2": array,
        "die_shadow_util": array / DIE_MM2,
        # The 5.61 mm2 tile is an OUTPUT of the converter area model, not a bound: it is
        # max() over the component classes, so constraining a level to it would be circular.
        # The real bound is the die shadow -- the VR array must fit under the 500 mm2 die,
        # which allows 500/49 = 10.20 mm2 per cell per level.
        "per_cell_budget_mm2": DIE_MM2 / N_VR,
        "AREA_FEASIBLE": array <= DIE_MM2,
        "HEIGHT_FEASIBLE": h_used <= space,
        "ROUTING_FEASIBLE": rt["n_infeasible"] == 0,
        "ROUTING_FEASIBLE_1LAYER": rt1["n_infeasible"] == 0,
        "routing_infeasible_nets": rt["infeasible"],
        "CURRENT_DENSITY_FEASIBLE": rt["n_infeasible"] == 0,
        "THERMAL_TIER_DEPTH": depth,
        "THERMAL_FEASIBLE": depth <= 2,
        "PACKAGE_CLEARANCE_OPEN": True,
        "open_clearances": "; ".join(OPEN_CLEARANCES),
        "P_intraVR_system_w": rt["p_system_w"],
    }
    out["FULLY_REALIZABLE"] = bool(
        out["AREA_FEASIBLE"] and out["HEIGHT_FEASIBLE"] and out["ROUTING_FEASIBLE"]
        and out["THERMAL_FEASIBLE"] and not out["PACKAGE_CLEARANCE_OPEN"])
    out["verdict"] = ("FULLY_REALIZABLE" if out["FULLY_REALIZABLE"] else
                      "BLOCKED: " + ", ".join(
                          k for k in ("AREA_FEASIBLE", "HEIGHT_FEASIBLE",
                                      "ROUTING_FEASIBLE", "THERMAL_FEASIBLE")
                          if not out[k]) or "CLEARANCE_OPEN")
    if out["verdict"] == "BLOCKED: ":
        out["verdict"] = "ALL PHYSICAL CHECKS PASS -- CLEARANCE OPEN"
    return out


def intermediate_rail(template: str) -> dict:
    """Does this template put an intermediate-voltage rail across a tier boundary?"""
    d = RP.DESIGN
    N = d["N"]
    i_out = d["i_out_per_vr_a"]
    p_in = d["v_out"] * i_out + d["p_conv_total_w"] / d["n_vr"]
    v_mid, i_mid = d["v_in"] / N, p_in / (d["v_in"] / N)
    i_in, i_lv = p_in / d["v_in"], i_out
    hs_t, ls_t = RP.tier_of(template, "gan_hs"), RP.tier_of(template, "gan_ls")
    l_t = RP.tier_of(template, "inductor")
    crossings = []
    if hs_t != ls_t:
        crossings.append(("MID", v_mid, i_mid))
    if ls_t != l_t:
        crossings.append(("SW", d["v_out"], i_lv))
    return {"template": template,
            "crossings": "; ".join("%s %.3gV %.3gA" % c for c in crossings) or "none",
            "n_crossings": len(crossings),
            "worst_crossing_current_a": max((c[2] for c in crossings), default=0.0),
            "i_in_a": i_in, "i_mid_a": i_mid, "i_out_a": i_lv,
            "i_mid_over_i_out": i_mid / i_lv,
            "note": ("an intermediate rail crosses the boundary, carrying %.3g A instead of "
                     "%.3g A -- an I^2 reduction of %.0fx"
                     % (i_mid, i_lv, (i_lv / i_mid) ** 2)) if any(
                         c[0] == "MID" for c in crossings) else
                    "no intermediate rail crosses a tier boundary"}


def main() -> int:
    rows, zrows, irows = [], [], []
    for tpl in RP.TEMPLATES:
        e = envelope(tpl)
        for t in e["tiers"]:
            zrows.append({"template": tpl, **t, "stack_height_um": e["stack_height_um"]})
        irows.append(intermediate_rail(tpl))
        for arch in ARCH_ENVELOPE_UM:
            c = classify(tpl, arch)
            rows.append(c)
            print(f"  {tpl:22s} {arch:20s} h={c['height_charged_um']:6.1f}"
                  f"(of {c['stack_height_um']:6.1f})/{c['arch_space_um']:6.0f} um "
                  f"A={c['AREA_FEASIBLE']!s:5s} H={c['HEIGHT_FEASIBLE']!s:5s} "
                  f"R={c['ROUTING_FEASIBLE']!s:5s} T={c['THERMAL_FEASIBLE']!s:5s} "
                  f"-> {c['verdict'][:44]}", flush=True)
    for name, data in (("component_z_envelopes.csv", zrows),
                       ("component_partition_power_paths.csv", irows),
                       ("component_partition_feasibility.csv", rows)):
        k = sorted({x for r in data for x in r})
        with open(OUT / name, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=k); w.writeheader(); w.writerows(data)
    print()
    for r in irows:
        print(f"  {r['template']:22s} crossings: {r['crossings']:28s} {r['note'][:80]}")
    print(f"wrote {OUT/'component_z_envelopes.csv'} and two more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
