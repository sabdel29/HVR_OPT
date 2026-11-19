"""PHASE 0N-W --- Z1/Z2 converter inventory and volume equality (brief section 18).

The comparison the paper rests on is only meaningful if both architectures contain the
SAME converter. Not "a converter of the same nominal rating" -- the same component counts
and the same active silicon, magnetics and capacitor volume. Otherwise a warpage or
temperature difference could simply be a difference in how much hardware got meshed.

Volumes are measured from the MESHES, not computed from the specification, so this audit
catches an implementation that silently dropped or duplicated a tier.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts/phase0nw"))
import z1_package as Z1P                                                  # noqa: E402
import z2_converter as Z2C                                               # noqa: E402
from physical_package import (build_physical_package, build_physical_z1,  # noqa: E402
                              load_physical_package_config,
                              load_z1_package_config)

CFG = R / "configs/phase0nt/z2_2p4mm_cutout.yaml"

import design_record as DR                                               # noqa: E402

#: the record's class -> the audit's component key
COMPONENT = {"gan_hs": "hs", "gan_ls": "ls", "inductor": "inductor", "cap_fly": "flying_cap"}


def per_cell() -> dict:
    """Per-cell component counts of the design in force (THE design record: N high-side and
    K low-side dies, K inductors, N - 1 flying capacitors; 3/3/3/2 for N3K3K_A2)."""
    return {COMPONENT[c]: n for c, n in DR.part_counts().items()}


#: kept for importers; the counts of the design in force
PER_CELL = per_cell()


def _tier_volumes(mesh, layer_names) -> dict:
    """In-cell volume per tier, in mm^3, measured from the mesh."""
    vol = mesh.elem_volumes()
    lay = np.array(mesh.elem_layer)
    tile = np.array(mesh.elem_tile)
    out = {}
    for nm in layer_names:
        sel = (lay == nm) & (tile >= 0)
        out[nm] = float(vol[sel].sum())
    return out


def audit() -> dict:
    """TCPMT round 3: the converter tiers are the design record's MIXED tiers, identical in
    Z1 and Z2 (same contents, heights and cells). The audit measures every tier's in-cell
    volume on both meshes and requires equality tier by tier; a component class is equal when
    every tier holding it is."""
    cfg = load_physical_package_config(CFG)
    m2 = build_physical_package(cfg)[0]
    z1cfg = load_z1_package_config()
    m1 = build_physical_z1(z1cfg)[0]
    z2_names = [t[0] for t in Z2C.converter_layers(cfg)]
    z1_names = [t[0] for t in Z1P.mid_layers(z1cfg) if t[0].startswith("z1conv_")]
    v2, v1 = _tier_volumes(m2, z2_names), _tier_volumes(m1, z1_names)
    parts = DR.tier_parts()

    def by_tier(vols):
        act, rdl = {}, 0.0
        for nm, v in vols.items():
            key = nm.split("_", 2)[2]
            if key in parts:
                act[key] = act.get(key, 0.0) + v
            else:
                rdl += v
        return act, rdl

    a2, rdl2 = by_tier(v2)
    a1, rdl1 = by_tier(v1)
    tiers = []
    for t in parts:
        d = a1.get(t, 0.0) - a2.get(t, 0.0)
        rel = abs(d) / max(a1.get(t, 0.0), a2.get(t, 0.0), 1e-30)
        tiers.append({"tier": t, "parts": parts[t], "z1_volume_mm3": a1.get(t, 0.0),
                      "z2_volume_mm3": a2.get(t, 0.0), "rel_delta": rel,
                      "equal": rel < 1e-9})
    eq = {r["tier"]: r["equal"] for r in tiers}
    pc = per_cell()
    comps = []
    for c, key in COMPONENT.items():
        holding = [t for t in parts if parts[t].get(c)]
        comps.append({"component": key, "count_per_cell": pc[key],
                      "count_total": pc[key] * cfg.cells, "tiers": holding,
                      "z1_volume_mm3": sum(a1.get(t, 0.0) for t in holding),
                      "z2_volume_mm3": sum(a2.get(t, 0.0) for t in holding),
                      "rel_delta": max((r["rel_delta"] for r in tiers if r["tier"] in holding),
                                       default=0.0),
                      "equal": all(eq[t] for t in holding)})
    active1, active2 = sum(a1.values()), sum(a2.values())
    n_rdl1 = sum(1 for n in z1_names if n.endswith("_rdl"))
    n_rdl2 = sum(1 for n in z2_names if n.endswith("_rdl"))
    return {
        "design": DR.name(),
        "cells_z1": int((np.array(m1.elem_tile) >= 0).any() and z1cfg.cells),
        "cells_z2": cfg.cells,
        "tiers": tiers,
        "components": comps,
        "active_volume_z1_mm3": active1,
        "active_volume_z2_mm3": active2,
        "active_equal": abs(active1 - active2) / max(active1, active2) < 1e-9,
        "rdl_volume_z1_mm3": rdl1,
        "rdl_volume_z2_mm3": rdl2,
        "rdl_justified_difference": {
            "z1_rdl_count": n_rdl1, "z2_rdl_count": n_rdl2,
            "reason": ("Z1's converter is sandwiched -- it lands on the bottom-substrate "
                       "RDL below and must present an output RDL to the microbumps above, "
                       "so it carries a landing RDL at BOTH ends. Z2 attaches only at the "
                       "substrate side; its far end descends into the cutout and "
                       "terminates free. The 10 um / one-RDL difference is interconnect, "
                       "not active converter content."),
        },
        "z1_total_converter_um": Z1P.Z1_CONV_UM,
        "z2_total_converter_um": cfg.conv_total_um,
    }


def main():
    a = audit()
    print(f"cells: Z1 {a['cells_z1']}  Z2 {a['cells_z2']}")
    print(f"{'component':12s} {'per cell':>8s} {'total':>6s} "
          f"{'Z1 mm3':>10s} {'Z2 mm3':>10s} {'rel delta':>10s}")
    for c in a["components"]:
        print(f"{c['component']:12s} {c['count_per_cell']:8d} {c['count_total']:6d} "
              f"{c['z1_volume_mm3']:10.4f} {c['z2_volume_mm3']:10.4f} "
              f"{c['rel_delta']:10.2e} {'OK' if c['equal'] else 'DIFFERS'}")
    print(f"\nactive converter volume  Z1 {a['active_volume_z1_mm3']:.4f} mm3   "
          f"Z2 {a['active_volume_z2_mm3']:.4f} mm3   equal={a['active_equal']}")
    print(f"converter RDL volume     Z1 {a['rdl_volume_z1_mm3']:.4f} mm3   "
          f"Z2 {a['rdl_volume_z2_mm3']:.4f} mm3   "
          f"(5 vs 4 RDLs, justified)")
    print(f"total converter height   Z1 {a['z1_total_converter_um']:.0f} um   "
          f"Z2 {a['z2_total_converter_um']:.0f} um")
    out = R / "research" / "phase0nw"
    out.mkdir(parents=True, exist_ok=True)
    json.dump(a, (out / "inventory_audit.json").open("w"), indent=1)


if __name__ == "__main__":
    main()
