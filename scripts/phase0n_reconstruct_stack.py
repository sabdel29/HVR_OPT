#!/usr/bin/env python3
"""PHASE 0N SECTION A -- reconstruct what the code ACTUALLY builds for Z1 and Z2.

Builds the real production mesh for each architecture and reports the z-stack as
measured from the mesh, not as described in any document.
"""
from __future__ import annotations
import json, math, os, sys
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parent.parent
for p in ("phase0b", "phase0g", "phase0i", "phase0mr"):
    sys.path.insert(0, str(R / "scripts" / p))
sys.path.insert(0, str(R / "scripts" / "phase0b" / "etm"))

import production_et as PE                                             # noqa: E402
import zglobal as ZG                                                   # noqa: E402
import zarch as ZA                                                     # noqa: E402
import board as BRD                                                    # noqa: E402

OUT = R / "research" / "phase0n"
OUT.mkdir(parents=True, exist_ok=True)

CASES = {"Z1": ("ARCH_Z1_EMBEDDED", 1.30), "Z2": ("ARCH_Z2_BACKSIDE", 0.30)}


def layer_table(m, tiles):
    """Per (layer, material): z extent and meshed volume."""
    zc = m.nodes[:, 2]
    rows = {}
    for e, lay, mat in zip(m.elems, m.elem_layer, m.elem_material):
        z = zc[e - 1]
        z0, z1 = float(z.min()), float(z.max())
        xs = m.nodes[e - 1, 0]; ys = m.nodes[e - 1, 1]
        vol = (xs.max() - xs.min()) * (ys.max() - ys.min()) * (z1 - z0)
        k = (lay, mat)
        if k not in rows:
            rows[k] = {"z0": z0, "z1": z1, "vol": 0.0, "n": 0}
        rows[k]["z0"] = min(rows[k]["z0"], z0)
        rows[k]["z1"] = max(rows[k]["z1"], z1)
        rows[k]["vol"] += vol
        rows[k]["n"] += 1
    return rows


def main():
    # This file records the FROZEN baseline geometry. Running it with the Phase-0N
    # correction enabled would silently overwrite that baseline with a variant.
    if os.environ.get("PHASE0N_Z2_CONV_FILL"):
        raise SystemExit("refusing to run: PHASE0N_Z2_CONV_FILL is set, which would "
                         "overwrite the frozen baseline in stack_reconstruction.json. "
                         "Unset it, or use phase0n_conv_extent_experiment.py instead.")
    report = {}
    for tag, (arch, h_sub) in CASES.items():
        m, mats, st, tiles = PE.build_global(arch, h_sub)
        rows = layer_table(m, tiles)
        g = st["geometry"]
        Lx = g["power_substrate"]["size_x"]["value"]
        Ly = g["power_substrate"]["size_y"]["value"]
        tile_area = sum(t.ax * t.ay for t in tiles)
        ordered = sorted(rows.items(), key=lambda kv: (kv[1]["z0"], kv[0][0]))
        report[tag] = {
            "arch": arch, "h_sub_mm": h_sub,
            "substrate_mm": [Lx, Ly], "substrate_area_mm2": Lx * Ly,
            "n_tiles": len(tiles), "tile_area_mm2": tile_area,
            "tile_coverage_pct": 100 * tile_area / (Lx * Ly),
            "conv_cell_mm": ZG.CONV_CELL_MM,
            "tile_band_is_converter": ZG.CONV_PLACE[arch] == "in",
            "n_elem": len(m.elems),
            "z_min_mm": float(m.nodes[:, 2].min()),
            "z_max_mm": float(m.nodes[:, 2].max()),
            "layers": [{"layer": k[0], "material": k[1],
                        "z0_mm": round(v["z0"], 6), "z1_mm": round(v["z1"], 6),
                        "t_um": round((v["z1"] - v["z0"]) * 1e3, 2),
                        "vol_mm3": round(v["vol"], 4), "n_elem": v["n"]}
                       for k, v in ordered],
        }
        print(f"\n{'='*86}\n{tag}  {arch}   h_sub = {h_sub} mm   "
              f"{len(m.elems)} elements   z = [{m.nodes[:,2].min():.3f}, "
              f"{m.nodes[:,2].max():.3f}] mm\n{'='*86}")
        print(f"{'layer':<18}{'material':<20}{'z0 mm':>10}{'z1 mm':>10}"
              f"{'t um':>9}{'vol mm3':>11}{'elems':>8}")
        for L in report[tag]["layers"]:
            print(f"{L['layer']:<18}{L['material']:<20}{L['z0_mm']:>10.4f}"
                  f"{L['z1_mm']:>10.4f}{L['t_um']:>9.1f}{L['vol_mm3']:>11.2f}"
                  f"{L['n_elem']:>8}")
        print(f"  substrate {Lx}x{Ly} mm = {Lx*Ly:.0f} mm2; "
              f"{len(tiles)} tiles = {tile_area:.1f} mm2 "
              f"({100*tile_area/(Lx*Ly):.1f} % coverage)")
    (OUT / "stack_reconstruction.json").write_text(json.dumps(report, indent=1))
    print(f"\nwrote {OUT/'stack_reconstruction.json'}")


if __name__ == "__main__":
    main()
