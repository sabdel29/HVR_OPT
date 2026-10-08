#!/usr/bin/env python3
"""Phase-0M-R3C Sections 2 and 5 --- the feasibility contract.

Two questions are kept apart throughout, as Section 2 requires:

  FRAMEWORK PROVISIONING   n_req = ceil(I / (J_design * A_via)) -- a conservative
                           design-side allocation using the framework's own J_design.
  MANUFACTURING            a sourced allowable current for THIS microvia technology.
                           Still OPEN. Nothing here is a manufacturing qualification.

New inputs this phase, both from primary sources obtained in full text:
  * EPC2057 datasheet: the part is a bare die with FOUR solder bars (pad 1 gate,
    pads 2 and 4 source, pad 3 drain), 1500 x 1200 um. The switch node is ONE bar, so
    the landing area on the die is at most a quarter of its footprint.
  * the ls_to_L edge is an AGGREGATE over K phases. Per device the switch node carries
    i_out/K, and there are K low-side dies, each with its own drain bar.
"""
from __future__ import annotations
import csv, math, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0mr", "scripts/phase0m", "scripts"):
    sys.path.insert(0, str(R / p))
import routing_production as RP                                          # noqa: E402

OUT = R / "results" / "phase0mr3c"
D = RP.DESIGN
K = D["K"]
I_AGG = D["i_out_per_vr_a"]
I_PHASE = I_AGG / K
J_DESIGN = 1.0e8
T_LINER_UM, S_MIN_UM, PACKING = 0.5, 30.0, 0.5
CELL_MM2 = D["tile_side_mm"] ** 2
RHO_85 = 1.72e-8 * (1 + 0.00393 * (85.0 - 20.0))
SPREAD = 1.163                      # 3-D land-spreading penalty, Phase 0M-R3B, measured

# EPC2057 datasheet, "Die Outline / Solder Bump View": A x B = 1500 x 1200 um, four
# solder bars. Pad 3 is the drain, i.e. the switch node of the low-side device. Four
# non-overlapping bars on that footprint bound one bar at A*B/4.
EPC_DIE_MM2 = 1.500 * 1.200
DRAIN_BAR_MAX_MM2 = EPC_DIE_MM2 / 4.0

PITCH_CASES = [(70.0, "0M-R3 design point", "UNSOURCED"),
               (100.0, "Ostmann 2008 prototype", "SOURCE_BOUNDED"),
               (150.0, "Ostmann 2008 production", "SOURCE_BOUNDED")]

CANDIDATES = {
    "baseline_T1": ["gan_hs", "gan_ls", "cap_fly", "cap_out,inductor"],
    "repartition_C1": ["gan_hs", "cap_fly", "gan_ls", "cap_out,inductor"],
}


def tiers_of(spec):
    return [t.split(",") for t in spec]


def geom(tiers):
    z, ext, areas = 0.0, [], []
    n_of = {"gan_hs": D["N"], "gan_ls": K, "cap_fly": D["N"] - 1,
            "cap_out": 1, "inductor": K}
    for t in tiers:
        h = max(RP.H_UM[c] for c in t)
        ext.append((z, z + h))
        areas.append(sum(RP.FOOT_MM2[c] * n_of[c] for c in t))
        z += h + RP.RDL_UM
    return ext, areas, z - RP.RDL_UM


def crossing(tiers, src, dst):
    ta = next(i for i, t in enumerate(tiers) if src in t)
    tb = next(i for i, t in enumerate(tiers) if dst in t)
    lo, hi = min(ta, tb), max(ta, tb)
    return [max(RP.H_UM[c] for c in tiers[t]) for t in range(lo + 1, hi)], (lo, hi)


def n_req(i_a, d_um):
    return max(1, math.ceil(i_a / (J_DESIGN * math.pi *
                                   ((d_um / 2 - T_LINER_UM) * 1e-6) ** 2)))


def main() -> int:
    rows = []
    for name, spec in CANDIDATES.items():
        tiers = tiers_of(spec)
        ext, areas, stack = geom(tiers)
        for net, src, dst, i_agg in (("ls_to_L", "gan_ls", "inductor", I_AGG),
                                     ("hs_to_ls", "gan_hs", "gan_ls", 1.435),
                                     ("hs_to_cf", "gan_hs", "cap_fly", 1.015)):
            depths, (lo, hi) = crossing(tiers, src, dst)
            i_per = i_agg / K if net == "ls_to_L" else i_agg
            if not depths:
                # Adjacent tiers. There is no component tier to cross, but the two device
                # faces are still separated by the interlayer RDL dielectric, so the
                # transition is a via of RDL_UM depth -- the shallowest one the stack
                # allows. Calling it "no via" would be wrong. The landing area is the
                # device land, not free cell area: EPC2057 has four solder bars, so the
                # switch node is at most a quarter of the die, times the K devices.
                depths = [RP.RDL_UM]
                land_mm2 = (DRAIN_BAR_MAX_MM2 * K if net == "ls_to_L"
                            else RP.FOOT_MM2["gan_hs"] / 4.0 * D["N"])
                for pitch, plabel, pprov in PITCH_CASES:
                    d_um = min(40.0, pitch - S_MIN_UM) if pitch == 70.0 else pitch - S_MIN_UM
                    nr = n_req(i_agg, d_um)
                    na = max(1, int(land_mm2 * 1e-6 * PACKING / (pitch * 1e-6) ** 2))
                    a_cu = math.pi * ((d_um / 2 - T_LINER_UM) * 1e-6) ** 2
                    rows.append({
                        "candidate": name, "net": net,
                        "route": "RDL via (adjacent tiers)",
                        "via_levels": 1, "dielectric_depth_um": RP.RDL_UM,
                        "i_aggregate_a": round(i_agg, 4),
                        "i_per_device_a": round(i_per, 4),
                        "free_area_mm2": round(land_mm2, 3), "d_um": round(d_um, 1),
                        "pitch_um": pitch,
                        "n_required_framework": nr, "n_available": na,
                        "routing_ratio": round(nr / na, 4),
                        "conductor_width_required_um": "",
                        "conductor_width_available_um": "", "width_margin_pct": "",
                        "AR_worst": round(RP.RDL_UM / d_um, 3),
                        "feasible_framework": nr <= na,
                        "manufacturing_status": "OPEN -- microvia current allowable and "
                                                "capture pad unsourced; landing area "
                                                "bounded from the EPC2057 datasheet",
                        "pitch_provenance": pprov})
                continue
            for pitch, plabel, pprov in PITCH_CASES:
                d_um = min(40.0, pitch - S_MIN_UM) if pitch == 70.0 else pitch - S_MIN_UM
                free = min(CELL_MM2 - areas[t] for t in range(lo + 1, hi))
                nr = n_req(i_agg, d_um)
                na = max(1, int(free * 1e-6 * PACKING / (pitch * 1e-6) ** 2))
                a_cu = math.pi * ((d_um / 2 - T_LINER_UM) * 1e-6) ** 2
                rser = sum(RHO_85 * (dp * 1e-6) / (a_cu * min(nr, na)) for dp in depths)
                rows.append({
                    "candidate": name, "net": net,
                    "route": f"build-up via x{len(depths)}",
                    "via_levels": len(depths),
                    "dielectric_depth_um": round(sum(depths), 1),
                    "i_aggregate_a": round(i_agg, 4), "i_per_device_a": round(i_per, 4),
                    "free_area_mm2": round(free, 3), "d_um": round(d_um, 1),
                    "pitch_um": pitch,
                    "n_required_framework": nr, "n_available": na,
                    "routing_ratio": round(nr / na, 4),
                    "conductor_width_required_um": "", "conductor_width_available_um": "",
                    "width_margin_pct": "",
                    "AR_worst": round(max(depths) / d_um, 3),
                    "feasible_framework": nr <= na,
                    "manufacturing_status": "OPEN -- microvia current allowable, capture "
                                            "pad and vendor rule unsourced",
                    "pitch_provenance": pprov})
    with (OUT / "routing_feasibility.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    print(f"per-phase decomposition: ls_to_L aggregate {I_AGG:.3f} A over K={K} phases "
          f"= {I_PHASE:.3f} A per device (EPC2057 rated 9.6 A continuous)")
    print(f"EPC2057 land pattern: 4 solder bars on {EPC_DIE_MM2:.2f} mm2; the drain bar "
          f"(switch node) is at most {DRAIN_BAR_MAX_MM2:.3f} mm2\n")
    for name in CANDIDATES:
        print(f"--- {name}")
        for r in [x for x in rows if x["candidate"] == name]:
            if True:
                print(f"   {r['net']:9s} {r['route']:12s} {r['dielectric_depth_um']:5.0f} um  "
                      f"p{r['pitch_um']:.0f} d{r['d_um']:.0f}  AR {r['AR_worst']:5.2f}  "
                      f"n {r['n_required_framework']:>4}/{r['n_available']:<4} "
                      f"ratio {r['routing_ratio']:6.3f}  "
                      f"{'OK' if r['feasible_framework'] else 'FAIL':4s} [{r['pitch_provenance']}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
