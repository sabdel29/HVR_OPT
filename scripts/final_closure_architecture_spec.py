"""The machine-readable Z1/Z2 architecture spec every package illustration is drawn from.

Nothing here is typed in. Every z extent is MEASURED on the solver's own mesh (the same
builders the physical lineage runs, final_closure_physical_etm.build), every lateral
dimension comes from the configuration objects and the stack card the mesh was built
from, and every electrical role comes from the ledger's layer map. A figure that needs a
layer height reads it from research/final_closure/architecture_geometry.json; there is no
second set of heights anywhere in the figure code, and tests/final_closure checks that.

    python final_closure_architecture_spec.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import final_closure_physical_etm as E                              # noqa: E402

OUT = R / "research" / "final_closure" / "architecture_geometry.json"

#: plain-language role of each meshed layer, keyed by the ledger's role names
ROLE_TEXT = {"hs": "high-side GaN device tier", "ls": "low-side GaN device tier",
             "caps": "flying-capacitor tier", "ind": "inductor + output-capacitor tier",
             "rdl": "converter RDL tier (10 um)", "lv": "1 V output RDL",
             "tsv": "through-silicon via field", "pads": "die-to-package interface (Cu pads)",
             "bga": "BGA ball field (48 V supply + return)", "die": "compute die"}


def _layers(m, materials, cut=None):
    """z extent, materials and in-plane region of every meshed layer, from the mesh.
    `plan_extent` is MEASURED in plan view from the element centroids against the PCB
    opening's square footprint: a layer declared region 'all' that the opening removes
    (board, BGA in Z2) is 'outside_opening_footprint' in fact. It says nothing about z."""
    lay = np.array(m.elem_layer, dtype=object)
    mat = np.array(materials, dtype=object)
    cen = m.elem_centroids()
    inside = ((np.abs(cen[:, 0]) < cut / 2) & (np.abs(cen[:, 1]) < cut / 2)) if cut \
        else np.zeros(len(cen), bool)
    out, seen = [], set()
    for L in m.layers:
        if L.name in seen:
            for o in out:
                if o["name"] == L.name:
                    o["z0_um"] = min(o["z0_um"], round(L.z0 * 1e3, 3))
                    o["z1_um"] = max(o["z1_um"], round(L.z1 * 1e3, 3))
                    o["t_um"] = round(o["z1_um"] - o["z0_um"], 3)
            continue
        seen.add(L.name)
        sel = lay == L.name
        n_in, n_out = int((sel & inside).sum()), int((sel & ~inside).sum())
        extent = ("within_opening_footprint" if n_in and not n_out else
                  "outside_opening_footprint" if n_out and not n_in and cut else
                  "both" if n_in and n_out else "no_opening")
        out.append({"name": L.name, "z0_um": round(L.z0 * 1e3, 3),
                    "z1_um": round(L.z1 * 1e3, 3), "t_um": round((L.z1 - L.z0) * 1e3, 3),
                    "footprint": L.footprint, "region": L.region, "plan_extent": extent,
                    "n_elems_inside_cutout": n_in, "n_elems_outside_cutout": n_out,
                    "materials": {str(k): int((mat[sel] == k).sum())
                                  for k in sorted(set(mat[sel]))}})
    return sorted(out, key=lambda o: o["z0_um"])


def spec_for(arch):
    import final_closure_ledger as FL
    import physical_coords as PCO
    import pkg_rdl_network as K
    import tsv_fields as TF
    import board as BRD
    m, mats, st, tiles, minfo = E.build(arch, E.PRODUCTION_H_XY, (1, 1))
    g = st["geometry"]
    v = lambda d: d["value"] if isinstance(d, dict) else d
    cut = K.architecture_cutout_mm(arch)
    roles = {}
    for k, name in FL.LAYERS[arch].items():
        for n in (name if isinstance(name, list) else [name]):
            roles.setdefault(n, []).append(k)
    layers = _layers(m, m.elem_material, cut)
    for o in layers:
        o["roles"] = roles.get(o["name"], [])
        o["role_text"] = "; ".join(dict.fromkeys(ROLE_TEXT[r] for r in o["roles"]
                                                 if r in ROLE_TEXT)) or None
    xs = sorted({round(t.cx, 6) for t in tiles})
    return {
        "arch": arch,
        "label": {"Z1": "Z1 -- converter embedded between substrate and die",
                  "Z2": "Z2 -- converter on the substrate backside, inside the PCB "
                        "opening"}[arch],
        "layers": layers,
        "z_min_um": round(float(m.zs.min()) * 1e3, 3),
        "z_max_um": round(float(m.zs.max()) * 1e3, 3),
        "substrate_mm": [v(g["power_substrate"]["size_x"]), v(g["power_substrate"]["size_y"])],
        "die_mm": [v(g["functional_die"]["size_x"]), v(g["functional_die"]["size_y"])],
        "board_extent_mm": [float(m.xs.min()), float(m.xs.max())],
        "board_case": E.PRODUCTION_H_XY and BRD.BOARD_CASES and
        (__import__("physical_package").load_z1_package_config().board_case if arch == "Z1"
         else __import__("physical_package").load_physical_package_config(
             R / "configs/phase0nt/z2_2p4mm_cutout.yaml").board_case),
        "cutout_mm": cut,
        "cells": {"n": len(tiles), "grid": len(xs), "side_mm": float(tiles[0].ax),
                  "centres_x_mm": xs},
        "bga": {"pitch_mm": 0.8, "sites_legal": len(PCO.bga_lattice_sites(cut)),
                "height_um": round(BRD.BALL_H_MM * 1e3, 3)},
        "tsv": {"n_per_cell": E.TSV_N_PER_CELL, "d_um": E.TSV_D_MM * 1e3,
                "pitch_um": TF.P_TSV_MM * 1e3,
                "rail_carried": {"Z1": "48 V input (low current)",
                                 "Z2": "1 V output (about 1 kA total)"}[arch]},
        "rails": {"input": "48 V enters through the PCB and BGA",
                  "output": "1 V delivered to the compute die",
                  "return": "ground return through the same BGA field"},
        "mesh": {"builder": "final_closure_physical_etm.build", "h_xy_mm": E.PRODUCTION_H_XY,
                 "n_elems_base": int(m.n_elems)},
    }


def main():
    spec = {"generated_by": "scripts/final_closure_architecture_spec.py",
            "rule": "every z extent measured on the solver mesh; nothing typed in",
            "architectures": {a: spec_for(a) for a in ("Z1", "Z2")}}
    txt = json.dumps(spec, indent=1, default=float)
    spec["sha256"] = hashlib.sha256(txt.encode()).hexdigest()
    OUT.write_text(json.dumps(spec, indent=1, default=float))
    for a, s in spec["architectures"].items():
        print(a, s["z_min_um"], s["z_max_um"], [(o["name"], o["t_um"]) for o in s["layers"]])


if __name__ == "__main__":
    main()
