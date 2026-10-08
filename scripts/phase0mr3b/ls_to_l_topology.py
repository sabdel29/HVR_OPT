#!/usr/bin/env python3
"""Phase-0M-R3B Sections 2 and 4 --- what `ls_to_L` physically is, layer by layer.

Phase 0M-R3A recorded a 673 um span and asked what technology spans it. The span itself
turns out to be the artifact: build_edges() addresses components at their tier MID-PLANES,
so `ls_to_L` was measured from the geometric centre of the low-side GaN die to the
geometric centre of the inductor -- straight through 303 um of GaN body and 250 um of
inductor body. No interconnect does that; components are contacted at their terminal
faces. The build-up a via chain must actually cross is the gap between them (DEFECT #62).

Everything here is derived from the framework's own H_UM / RDL_UM / TEMPLATES. No new
geometry is invented.
"""
from __future__ import annotations
import csv, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0mr"))
sys.path.insert(0, str(R / "scripts" / "phase0m"))
sys.path.insert(0, str(R / "scripts"))
import routing_production as RP                                          # noqa: E402

OUT = R / "results" / "phase0mr3b"
T = "T1_EMBEDDED_4LAYER"


def tier_extents(template: str = T) -> list[tuple[float, float]]:
    """(z_bottom, z_top) of every component tier, um, bottom-to-top."""
    z, ext = 0.0, []
    for tier in RP.TEMPLATES[template]:
        h = max(RP.H_UM[c] for c in tier)
        ext.append((z, z + h))
        z += h + RP.RDL_UM
    return ext


def physical_span(e, ext) -> float:
    """Top face of the lower component to the bottom face of the upper one."""
    lo, hi = min(e.tiers), max(e.tiers)
    return ext[hi][0] - ext[lo][1]


def layer_stack(template: str = T) -> list[dict]:
    """The dielectric layers `ls_to_L` crosses, in order, with what each one is."""
    ext = tier_extents(template)
    segs = []
    # from the top face of gan_ls (tier 1) to the bottom face of the inductor (tier 3)
    z = ext[1][1]
    segs.append({"i": 1, "layer": "RDL above gan_ls", "kind": "build-up dielectric",
                 "z_bot_um": z, "z_top_um": z + RP.RDL_UM,
                 "thickness_um": RP.RDL_UM,
                 "obstruction": "none", "source": "ECTC-2024 Table I interlayer RDL"})
    z += RP.RDL_UM
    h_cap = max(RP.H_UM[c] for c in RP.TEMPLATES[template][2])
    segs.append({"i": 2, "layer": "flying-capacitor power layer", "kind": "embedded-component build-up",
                 "z_bot_um": z, "z_top_um": z + h_cap, "thickness_um": h_cap,
                 "obstruction": "embedded MLCC bodies; the via must route beside them",
                 "source": "June-2026 Sec. II: flying capacitors embedded in the middle power layer"})
    z += h_cap
    segs.append({"i": 3, "layer": "RDL below inductor", "kind": "build-up dielectric",
                 "z_bot_um": z, "z_top_um": z + RP.RDL_UM, "thickness_um": RP.RDL_UM,
                 "obstruction": "none", "source": "ECTC-2024 Table I interlayer RDL"})
    return segs


def main() -> int:
    ext = tier_extents()
    E = {e.name: e for e in RP.build_edges(T)}
    rows = []
    for name, e in E.items():
        if e.geom != "vertical":
            continue
        rows.append({
            "edge": name, "src": e.src, "dst": e.dst, "rail": e.rail,
            "tier_src": e.tiers[0], "tier_dst": e.tiers[1],
            "i_rms_a": round(e.i_rms, 6),
            "modelled_span_um": round(e.length_mm * 1000, 1),
            "physical_span_um": round(physical_span(e, ext), 1),
            "overstatement_x": round(e.length_mm * 1000 / physical_span(e, ext), 2),
            "basis_modelled": "tier mid-plane to tier mid-plane",
            "basis_physical": "top face of lower component to bottom face of upper",
        })
    (OUT / "ls_to_L_layer_by_layer_geometry.csv").write_text("")
    with (OUT / "vertical_span_correction.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    segs = layer_stack()
    with (OUT / "ls_to_L_layer_by_layer_geometry.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(segs[0])); w.writeheader(); w.writerows(segs)

    print(f"{'edge':10s} {'I_rms':>8s} {'modelled':>9s} {'physical':>9s} {'x':>6s}")
    for r in rows:
        print(f"{r['edge']:10s} {r['i_rms_a']:8.3f} {r['modelled_span_um']:9.1f} "
              f"{r['physical_span_um']:9.1f} {r['overstatement_x']:6.2f}")
    print(f"\nls_to_L crosses {len(segs)} dielectric layers, "
          f"{sum(s['thickness_um'] for s in segs):.0f} um total:")
    for s in segs:
        print(f"  {s['i']}  {s['layer']:34s} {s['thickness_um']:6.1f} um   {s['kind']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
