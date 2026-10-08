#!/usr/bin/env python3
"""Phase-0M-R3C Section 3 --- the conductor-plane sequence, not the layer count.

Phase 0M-R3B counted three MATERIAL layers across the 120 um gap and concluded three
microvia levels. That conflates material layers with conductor planes. `RDL_UM = 10 um` is
an interlayer REDISTRIBUTION LAYER -- a patterned copper plane, which is exactly what a
microvia lands on. A via level is needed per DIELECTRIC region between conductor planes,
not per material layer.
"""
from __future__ import annotations
import csv, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0mr", "scripts/phase0m", "scripts"):
    sys.path.insert(0, str(R / p))
import routing_production as RP                                          # noqa: E402

OUT = R / "results" / "phase0mr3c"


def planes(template: str, net_src: str, net_dst: str) -> list[dict]:
    """The ordered z-structure between two components' facing terminal planes."""
    ext, z = [], 0.0
    for tier in RP.TEMPLATES[template]:
        h = max(RP.H_UM[c] for c in tier)
        ext.append((z, z + h)); z += h + RP.RDL_UM
    ta = RP.tier_of(template, net_src)
    tb = RP.tier_of(template, net_dst)
    if ta == tb:
        return [{"i": 0, "kind": "SAME TIER", "role": "lateral route on the tier's own "
                 "conductor plane", "z_start_um": ext[ta][0], "z_end_um": ext[ta][1],
                 "thickness_um": 0.0, "needs_via": False,
                 "capture_land": "n/a", "via_type": "none", "source_status": "n/a"}]
    lo, hi = min(ta, tb), max(ta, tb)
    seq, z = [], ext[lo][1]
    seq.append({"i": 0, "kind": "TERMINAL PLANE", "role": f"{net_src} terminal face",
                "z_start_um": z, "z_end_um": z, "thickness_um": 0.0, "needs_via": False,
                "capture_land": "device land", "via_type": "none",
                "source_status": "SOURCE_BACKED (component height)"})
    i = 1
    for t in range(lo, hi):
        seq.append({"i": i, "kind": "CONDUCTOR PLANE", "role": f"interlayer RDL above tier {t}",
                    "z_start_um": z, "z_end_um": z + RP.RDL_UM,
                    "thickness_um": RP.RDL_UM, "needs_via": False,
                    "capture_land": "patterned Cu; a microvia can land here",
                    "via_type": "none", "source_status": "SOURCE_BACKED (ECTC-2024 Tab. I)"})
        z += RP.RDL_UM
        i += 1
        if t + 1 < hi:                       # a component tier lies in between
            tier = RP.TEMPLATES[template][t + 1]
            h = max(RP.H_UM[c] for c in tier)
            seq.append({"i": i, "kind": "DIELECTRIC REGION",
                        "role": f"tier {t+1} power layer ({','.join(tier)}) -- build-up "
                                f"with embedded components, no conductor plane inside it",
                        "z_start_um": z, "z_end_um": z + h, "thickness_um": h,
                        "needs_via": True, "capture_land": "none available inside",
                        "via_type": "build-up via, full tier depth",
                        "source_status": "OPEN (depth/diameter rule unsourced)"})
            z += h
            i += 1
    seq.append({"i": i, "kind": "TERMINAL PLANE", "role": f"{net_dst} terminal face",
                "z_start_um": z, "z_end_um": z, "thickness_um": 0.0, "needs_via": False,
                "capture_land": "device land", "via_type": "none",
                "source_status": "SOURCE_BACKED (component height)"})
    return seq


def main() -> int:
    rows = []
    for tpl in ("T1_EMBEDDED_4LAYER", "T4_SPLIT_SC_BUCK", "T2_BACKSIDE_CHIPLET",
                "T0_SINGLE_LEVEL"):
        for src, dst, net in (("gan_ls", "inductor", "ls_to_L"),
                              ("gan_hs", "gan_ls", "hs_to_ls"),
                              ("gan_hs", "cap_fly", "hs_to_cf")):
            try:
                seq = planes(tpl, src, dst)
            except KeyError:
                continue
            nv = sum(1 for s in seq if s["needs_via"])
            for s in seq:
                rows.append({"template": tpl, "net": net, "via_levels_total": nv, **s})
    with (OUT / "conductor_plane_topology.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    print("VIA LEVELS, derived from conductor planes (not material layers):\n")
    print(f"{'template':22s} {'net':10s} {'levels':>7s}  via depths")
    for tpl in ("T1_EMBEDDED_4LAYER", "T4_SPLIT_SC_BUCK", "T2_BACKSIDE_CHIPLET",
                "T0_SINGLE_LEVEL"):
        for net in ("ls_to_L", "hs_to_ls", "hs_to_cf"):
            g = [r for r in rows if r["template"] == tpl and r["net"] == net]
            if not g:
                continue
            d = [f"{r['thickness_um']:.0f} um" for r in g if r["needs_via"]]
            print(f"{tpl:22s} {net:10s} {g[0]['via_levels_total']:7d}  "
                  f"{', '.join(d) if d else 'same tier -- lateral'}")
    print("\nDetail for T1 ls_to_L, the Phase-0M-R3B case:")
    for r in [x for x in rows if x["template"] == "T1_EMBEDDED_4LAYER"
              and x["net"] == "ls_to_L"]:
        v = " <-- VIA" if r["needs_via"] else ""
        print(f"  {r['i']}  {r['kind']:18s} {r['z_start_um']:7.1f}-{r['z_end_um']:7.1f} um "
              f"({r['thickness_um']:5.1f}){v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
