"""PHASE 0N-AG --- ONE source of physical x-y coordinates for every electrical model.

Three models were each deriving the 49 cell centres their own way. The RDL solver
hard-coded a 3.0 mm pitch; the actual FE placement puts them at 3.165243 mm with centres
spanning +-9.495728 mm. Every RDL result computed against the wrong grid.

Likewise Z1's BGA "sites" were synthesised by adding (+0.4, +0.4) mm to cell centres,
which are not lattice positions at all. The real lattice is centred at 0.8 mm pitch:
x, y in {-14.4 + 0.8 n}.

This module is the single source. Tests assert the FE tiles, the RDL cell loads, the TSV
fields and the pad fields all use the same centres.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for _p in ("scripts/phase0nw", "scripts/phase0mr", "scripts/phase0i", "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))

BGA_PITCH_MM = 0.800
BGA_HALF_SPAN_MM = 14.4            # centred lattice: -14.4 + 0.8 n


def physical_cell_coordinates(cfg=None) -> list:
    """The 49 cell centres FROM THE FE PLACEMENT GENERATOR. Never hard-coded."""
    from physical_package import (build_physical_package,
                                  load_physical_package_config)
    cfg = cfg or load_physical_package_config(
        R / "configs/phase0nt/z2_2p4mm_cutout.yaml")
    _m, _mats, _st, tiles = build_physical_package(cfg)
    return [(float(t.cx), float(t.cy)) for t in tiles]


def cell_pitch_mm(coords=None) -> float:
    c = coords or physical_cell_coordinates()
    xs = sorted({round(x, 6) for x, _ in c})
    return xs[1] - xs[0]


def is_on_bga_lattice(x: float, y: float, tol: float = 1e-6) -> bool:
    """A legal site satisfies (v + 14.4) / 0.8 == integer."""
    for v in (x, y):
        k = (v + BGA_HALF_SPAN_MM) / BGA_PITCH_MM
        if abs(k - round(k)) > tol:
            return False
    return True


def bga_lattice_sites(cutout_mm: float | None = None) -> list:
    """Every legal centred-lattice site, optionally excluding the cutout interior."""
    n = int(round(2 * BGA_HALF_SPAN_MM / BGA_PITCH_MM)) + 1
    out = []
    for i in range(n):
        for j in range(n):
            x = -BGA_HALF_SPAN_MM + i * BGA_PITCH_MM
            y = -BGA_HALF_SPAN_MM + j * BGA_PITCH_MM
            if cutout_mm and abs(x) < cutout_mm / 2 and abs(y) < cutout_mm / 2:
                continue
            out.append((x, y))
    return out


def annulus_supply_return() -> tuple:
    """The Phase-0N-T allocation, as actually recorded."""
    j = json.loads((R / "research/phase0nt/annular_pcb.json").read_text())
    return ([tuple(p) for p in j["supply_xy_mm"]],
            [tuple(p) for p in j["return_xy_mm"]])


def select_sites(candidates, cells, n_pairs: int) -> tuple:
    """Pick n_pairs supply + n_pairs return sites nearest the cell grid, mirror-symmetric.

    A DESIGN CHOICE, not a sourced placement: the rule is "closest legal lattice sites to
    the load centroid, in mirror-symmetric pairs". It is applied identically to Z1 and Z2
    so the architectures are compared under one allocation rule rather than two.
    """
    import math
    cx = sum(x for x, _ in cells) / len(cells)
    cy = sum(y for _, y in cells) / len(cells)
    ranked = sorted(candidates, key=lambda p: math.hypot(p[0] - cx, p[1] - cy))
    sup, ret, used = [], [], set()
    for p in ranked:
        if len(sup) >= n_pairs and len(ret) >= n_pairs:
            break
        mirror = (-p[0], -p[1])
        if p in used or mirror in used or mirror not in set(candidates):
            continue
        if len(sup) < n_pairs:
            sup += [p, mirror]
            used |= {p, mirror}
        elif len(ret) < n_pairs:
            ret += [p, mirror]
            used |= {p, mirror}
    return sup[:n_pairs], ret[:n_pairs]
