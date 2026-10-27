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


#: lattice coordinates are SNAPPED to this many decimals (mm). 1e-9 mm is a
#: picometre -- far below any physical scale -- but it is what makes the set
#: closed under negation, which the mirror-symmetric placement rule requires.
LATTICE_DECIMALS = 9


def _snap(v: float) -> float:
    """Round to the canonical lattice grid, and never return -0.0."""
    return round(v, LATTICE_DECIMALS) + 0.0


def bga_lattice_sites(cutout_mm: float | None = None) -> list:
    """Every legal centred-lattice site, optionally excluding the cutout interior.

    COORDINATES ARE SNAPPED, AND THAT IS NOT COSMETIC. `-14.4 + i * 0.8`
    accumulates floating-point error, so the lattice was not closed under
    negation: site (14.4, 12.8) existed as (14.4, 12.800000000000002), differing
    from the exact mirror of (-14.4, -12.8) by 1.78e-15. select_power_sites()
    tests `mirror not in cand` with exact tuple equality, so it silently
    discarded every site whose partner had drifted -- 1080 of 1369 on the full
    lattice, and 408 of 528 on the Z2 annulus. Roughly 79 % of physically legal
    sites were invisible to the placement rule, and every BGA selection, every
    package-RDL resistance and every controlled cutout experiment was drawn from
    an arbitrary ~21 % subset determined by floating-point luck rather than by
    geometry. Snapping makes the set exactly closed under negation.
    """
    n = int(round(2 * BGA_HALF_SPAN_MM / BGA_PITCH_MM)) + 1
    out = []
    for i in range(n):
        for j in range(n):
            x = _snap(-BGA_HALF_SPAN_MM + i * BGA_PITCH_MM)
            y = _snap(-BGA_HALF_SPAN_MM + j * BGA_PITCH_MM)
            if cutout_mm and abs(x) < cutout_mm / 2 and abs(y) < cutout_mm / 2:
                continue
            out.append((x, y))
    return out


def annulus_supply_return() -> tuple:
    """The Phase-0N-T allocation, as actually recorded."""
    j = json.loads((R / "research/phase0nt/annular_pcb.json").read_text())
    return ([tuple(p) for p in j["supply_xy_mm"]],
            [tuple(p) for p in j["return_xy_mm"]])


def select_power_sites(candidate_sites, cells, n_supply: int, n_return: int,
                       allocation_rule: str = "nearest_symmetric") -> dict:
    """Select EXACTLY n_supply supply and n_return return sites from one candidate set.

    THE ARGUMENT IS A COUNT OF SITES, NOT A COUNT OF PAIRS. The previous API took
    `n_pairs` and the caller passed len(annulus_supply)//2 = 8, so Z1 received eight
    supply balls against Z2's sixteen. That silently replaced one uncontrolled
    comparison with another: the resulting 0.55 ratio measured the ball count, not the
    architecture.

    `allocation_rule` is applied identically to whichever candidate set it is given, so
    the ONLY difference between a Z1 and a Z2 run is which sites exist -- which is what
    isolating the cutout requires.

      nearest_symmetric  mirror-symmetric pairs closest to the load centroid
      outer_perimeter    mirror-symmetric pairs furthest from the centroid
      inner_edge         mirror-symmetric pairs closest to the cutout boundary
    """
    import math
    if n_supply % 2 or n_return % 2:
        raise ValueError("mirror symmetry needs even counts; got "
                         f"{n_supply} supply and {n_return} return")
    cx = sum(x for x, _ in cells) / len(cells)
    cy = sum(y for _, y in cells) / len(cells)
    cand = {(_snap(x), _snap(y)) for x, y in candidate_sites}

    def dist(p):
        return math.hypot(p[0] - cx, p[1] - cy)

    if allocation_rule == "nearest_symmetric":
        ranked = sorted(candidate_sites, key=dist)
    elif allocation_rule == "outer_perimeter":
        ranked = sorted(candidate_sites, key=dist, reverse=True)
    elif allocation_rule == "inner_edge":
        # WITHDRAWN. This branch ran `sorted(candidate_sites, key=dist)` -- the exact
        # expression used by nearest_symmetric -- so it returned the identical 16+16
        # sites on the full lattice AND on the Z2 annulus, verified directly. Its
        # comment claimed the annulus case would differ; it does not, because nothing
        # in the ranking refers to the cutout. Counting it as a third allocation rule
        # overstated how much placement sensitivity had been explored: two of the
        # three "rules" were one rule. A genuine inner-edge rule needs the cutout
        # radius passed in, which this signature does not carry.
        raise NotImplementedError(
            "allocation_rule='inner_edge' was an alias of 'nearest_symmetric' "
            "(identical ranking expression, identical sites on both candidate "
            "sets). It is withdrawn rather than silently duplicated; pass "
            "'nearest_symmetric' or 'outer_perimeter'.")
    else:
        raise ValueError(f"unknown allocation_rule {allocation_rule!r}")

    sup, ret, used = [], [], set()
    for p in ranked:
        if len(sup) >= n_supply and len(ret) >= n_return:
            break
        mirror = (_snap(-p[0]), _snap(-p[1]))
        if p in used or mirror in used or mirror not in cand or mirror == p:
            continue
        if len(sup) < n_supply:
            sup += [p, mirror]
            used |= {p, mirror}
        elif len(ret) < n_return:
            ret += [p, mirror]
            used |= {p, mirror}
    if len(sup) < n_supply or len(ret) < n_return:
        raise ValueError(f"only {len(sup)}/{n_supply} supply and {len(ret)}/{n_return} "
                         f"return sites could be placed symmetrically")
    return {"supply": sup[:n_supply], "return": ret[:n_return],
            "allocation_rule": allocation_rule,
            "n_candidates": len(candidate_sites)}
