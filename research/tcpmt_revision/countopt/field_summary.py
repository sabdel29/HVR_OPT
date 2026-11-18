#!/usr/bin/env python3
"""Where the heat sits: per-layer temperature of a converged Z1 case, from its own field.

Reads the LAST thermal result of the case's final E-T iteration (the field the case file's
T_max came from; asserted equal), on the mesh the case was solved on, and reports for every
layer the node max / mean and, for the converter tiers, the in-cell mean (inside the cell
footprints, where the device losses are deposited). Run once per design: the Z1 config in
force (HVR_Z1_CONFIG) selects the design, --wd the case's scratch directory.

    python -B field_summary.py --wd <scratch>/fc_etm/Z1_HV_S0_h1.1_r21 --out OUT.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[3]
for _p in ("scripts", "scripts/phase0nw", "scripts/phase0mr", "scripts/phase0m",
           "scripts/phase0i", "scripts/phase0g", "scripts/phase0b"):
    sys.path.insert(0, str(R / _p))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wd", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--refine", default="21")
    a = ap.parse_args()
    import final_closure_physical_etm as E
    import production_et as PE
    import z1_design as Z1D
    refine = (int(a.refine[0]), int(a.refine[1]))
    case = json.loads(E.case_path("Z1", "HV_S0", 1.1, refine).read_text())
    m, _mats, _st, tiles, _ = E.build("Z1", 1.1, refine)
    wd = Path(a.wd)
    last_it = sorted(wd.glob("et*"), key=lambda p: int(p.name[2:]))[-1]
    frd = sorted(last_it.glob("th_*.frd"), key=lambda p: int(p.stem.split("_")[1]))[-1]
    Tn = PE.ccxio.read_frd(frd)["NDTEMP"][1:m.n_nodes + 1, 0]
    assert abs(float(np.nanmax(Tn)) - case["thermal"]["T_max_C"]) < 1e-6, "not the case field"
    i = int(np.nanargmax(Tn))
    hot = m.nodes[i]
    lay_of_hot = [L.name for L in m.layers if L.z0 - 1e-9 <= hot[2] <= L.z1 + 1e-9]
    rows = {}
    for L in m.layers:
        ids = PE._layer_elems(m, L.name)
        nd = np.unique(m.elems[ids - 1].ravel())
        r = {"z0_um": L.z0 * 1e3, "z1_um": L.z1 * 1e3, "T_max_C": float(np.nanmax(Tn[nd - 1])),
             "T_mean_C": float(np.nanmean(Tn[nd - 1]))}
        if L.name.startswith("z1conv_"):
            nin = E.region_nodes(m, tiles, [L.name], True)
            r["T_in_cell_mean_C"] = float(np.nanmean(Tn[nin - 1]))
        rows[L.name] = r
    out = {"design": Z1D.summary(), "frd": str(frd), "T_max_C": float(Tn[i]),
           "T_max_at_mm": [float(x) for x in hot], "T_max_layers": lay_of_hot,
           "n_cells": len(tiles), "layers": rows}
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(f"T_max {Tn[i]:.2f} C at {np.round(hot, 3).tolist()} in {lay_of_hot}")
    for k, v in rows.items():
        print(f"  {k:32s} max {v['T_max_C']:7.2f} mean {v['T_mean_C']:7.2f}"
              + (f" in-cell {v['T_in_cell_mean_C']:7.2f}" if "T_in_cell_mean_C" in v else ""))


if __name__ == "__main__":
    main()
