#!/usr/bin/env python3
"""PHASE 0N-T Tasks 5/6 -- annular PCB and surviving BGA field.

Verifies that the through-cutout removes real elements (not relabelled ones) and
counts the surviving ball sites. Default (no env var) must reproduce the frozen
full-slab board exactly.
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parent.parent
for d in ("phase0mr", "phase0m", "phase0i", "phase0h", "phase0g", "phase0f",
          "phase0e", "phase0dr", "phase0b", "phase0d"):
    sys.path.insert(0, str(R / "scripts" / d))
import production_et as PE                                              # noqa: E402
import board as BRD                                                     # noqa: E402

OUT = R / "research" / "phase0nt"
OUT.mkdir(parents=True, exist_ok=True)
CUT = 23.36          # mm, 1.0 mm sidewall clearance on the 21.36 mm cell-grid bbox


def counts(cut):
    if cut:
        os.environ["PHASE0NT_CUTOUT_MM"] = str(cut)
    else:
        os.environ.pop("PHASE0NT_CUTOUT_MM", None)
    m, _mats, st, tiles = PE.build_global("ARCH_Z2_BACKSIDE", 0.30)
    cen = m.elem_centroids()
    out = {}
    for lay in ("board", "bga", "conv", "sub_lower", "die"):
        sel = np.array([l == lay for l in m.elem_layer])
        out[lay] = int(sel.sum())
        if cut and lay in ("board", "bga") and sel.any():
            inside = int((( np.abs(cen[sel, 0]) < cut / 2)
                        & (np.abs(cen[sel, 1]) < cut / 2)).sum())
            out[lay + "_inside_cutout"] = inside
    out["total"] = len(m.elems)
    os.environ.pop("PHASE0NT_CUTOUT_MM", None)
    return out, st, tiles


full, st, tiles = counts(None)
ann, _, _ = counts(CUT)
print(f"{'layer':12}{'full slab':>12}{'annular':>10}{'removed':>10}{'in cutout':>11}")
for lay in ("board", "bga", "conv", "sub_lower", "die"):
    rem = full[lay] - ann[lay]
    ins = ann.get(lay + "_inside_cutout", "-")
    print(f"{lay:12}{full[lay]:12d}{ann[lay]:10d}{rem:10d}{str(ins):>11}")
print(f"{'TOTAL':12}{full['total']:12d}{ann['total']:10d}{full['total']-ann['total']:10d}")

# surviving BGA ball SITES on the sourced lattice
p, Lx = BRD.BALL_P_MM, st["geometry"]["power_substrate"]["size_x"]["value"]
n = int(Lx / p)
sites = [(-Lx/2 + (i+.5)*p, -Lx/2 + (j+.5)*p) for i in range(n) for j in range(n)]
surv = [s for s in sites if not (abs(s[0]) < CUT/2 and abs(s[1]) < CUT/2)]
print(f"\nBGA lattice {p} mm: {len(sites)} sites, {len(surv)} survive the "
      f"{CUT} mm cutout, {len(sites)-len(surv)} removed")

# power / return allocation on the surviving ring, outermost first
import math
I_IN, I_BALL = 23.4344, 1.5
need = math.ceil(I_IN / I_BALL)
ring = sorted(surv, key=lambda s: -max(abs(s[0]), abs(s[1])))
supply = ring[:need]
ret = ring[need:2*need]
print(f"48 V supply balls {len(supply)} (outermost ring), return balls {len(ret)}, "
      f"{len(surv)-2*need} unallocated")
print(f"  supply |x|,|y| max {max(max(abs(a),abs(b)) for a,b in supply):.2f} mm")

json.dump({"cutout_mm": CUT, "elements_full": full, "elements_annular": ann,
           "bga_sites_full": len(sites), "bga_sites_surviving": len(surv),
           "bga_sites_removed": len(sites) - len(surv),
           "i_in_a": I_IN, "i_per_ball_a": I_BALL,
           "n_supply_balls": len(supply), "n_return_balls": len(ret),
           "n_unallocated": len(surv) - 2 * need,
           "supply_xy_mm": supply, "return_xy_mm": ret},
          (OUT / "annular_pcb.json").open("w"), indent=1)
print(f"\nwrote {OUT/'annular_pcb.json'}")
