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
    m, _mats, st, tiles = PE.build_global(
        "ARCH_Z2_BACKSIDE", 0.30, board_case="fr4_2p4mm", cutout_mm=cut)
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
# PHASE 0N-T: CENTRED lattice. The previous expression -Lx/2 + (i+0.5)*p ran
# -14.6 .. +14.2 for n = 37, p = 0.8 -- off-centre by 0.2 mm, so the outer ring
# existed only on the W and S edges and no symmetric allocation was possible.
off = (n - 1) * p / 2.0
sites = [(-off + i*p, -off + j*p) for i in range(n) for j in range(n)]
surv = [s for s in sites if not (abs(s[0]) < CUT/2 and abs(s[1]) < CUT/2)]
print(f"\nBGA lattice {p} mm: {len(sites)} sites, {len(surv)} survive the "
      f"{CUT} mm cutout, {len(sites)-len(surv)} removed")

# PHASE 0N-T item 10. The previous allocation sorted all surviving sites by
# outer-ring distance and took the first 16 -- which put essentially every supply
# ball on the x = -14.6 mm edge. Replaced with a four-fold symmetric allocation:
# equal counts per side, alternating supply/ground, first moments ~ 0.
import math
I_IN, I_BALL = 23.4344, 1.5
need = math.ceil(I_IN / I_BALL)                 # per rail
per_side = math.ceil(need / 4)
Rout = max(max(abs(a_), abs(b_)) for a_, b_ in surv)


def side_of(x, y):
    if abs(x) >= abs(y):
        return "E" if x > 0 else "W"
    return "N" if y > 0 else "S"


outer = [p_ for p_ in surv if max(abs(p_[0]), abs(p_[1])) >= Rout - 1e-9]
supply, ret = [], []
for sd in ("N", "S", "E", "W"):
    cand = [p_ for p_ in outer if side_of(*p_) == sd]
    # the coordinate that runs ALONG this side
    key = (lambda p_: p_[0]) if sd in "NS" else (lambda p_: p_[1])
    # build mirror-symmetric pairs (+c, -c) so each rail's first moment cancels exactly
    pos = sorted((p_ for p_ in cand if key(p_) > 0), key=key)
    pairs = []
    for q in pos:
        mate = next((r for r in cand if abs(key(r) + key(q)) < 1e-9), None)
        if mate is not None:
            pairs.append((q, mate))
    # alternate whole PAIRS between supply and return, innermost first
    for k, pr in enumerate(pairs[:per_side]):
        (supply if k % 2 == 0 else ret).extend(pr)
supply, ret = supply[:need], ret[:need]

mx_s = sum(p_[0] for p_ in supply) / len(supply)
my_s = sum(p_[1] for p_ in supply) / len(supply)
mx_r = sum(p_[0] for p_ in ret) / len(ret)
my_r = sum(p_[1] for p_ in ret) / len(ret)
from collections import Counter
print(f"\n48 V supply {len(supply)} balls, return {len(ret)}, "
      f"{len(surv)-len(supply)-len(ret)} unallocated")
print(f"  supply per side {dict(Counter(side_of(*p_) for p_ in supply))}")
print(f"  return per side {dict(Counter(side_of(*p_) for p_ in ret))}")
print(f"  supply first moment  ({mx_s:+.4f}, {my_s:+.4f}) mm")
print(f"  return first moment  ({mx_r:+.4f}, {my_r:+.4f}) mm")

json.dump({"cutout_mm": CUT, "board_case": "fr4_2p4mm",
           "board_um": 2400.0, "elements_full": full, "elements_annular": ann,
           "bga_sites_full": len(sites), "bga_sites_surviving": len(surv),
           "bga_sites_removed": len(sites) - len(surv),
           "i_in_a": I_IN, "i_per_ball_a": I_BALL,
           "n_supply_balls": len(supply), "n_return_balls": len(ret),
           "n_unallocated": len(surv) - len(supply) - len(ret),
           "supply_first_moment_mm": [mx_s, my_s],
           "return_first_moment_mm": [mx_r, my_r],
           "per_side_supply": dict(Counter(side_of(*p_) for p_ in supply)),
           "per_side_return": dict(Counter(side_of(*p_) for p_ in ret)),
           "supply_xy_mm": supply, "return_xy_mm": ret},
          (OUT / "annular_pcb.json").open("w"), indent=1)
print(f"\nwrote {OUT/'annular_pcb.json'}")
