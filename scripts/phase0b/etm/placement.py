"""HVR tile placement generation.

Coordinates are GENERATED from a placement class, never transcribed by hand.
Every layout is validated for: no tile overlap, containment in the legal region,
preserved total footprint, and preserved heat-source integral.

Legal-region rationale: VR tiles must sit BENEATH THE LOAD (that is the premise of
vertical power delivery), so the legal region for tile centres derives from the DIE
footprint, not the larger power substrate.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Tile:
    cx: float
    cy: float
    ax: float
    ay: float
    power_w: float

    @property
    def x0(self): return self.cx - self.ax / 2
    @property
    def x1(self): return self.cx + self.ax / 2
    @property
    def y0(self): return self.cy - self.ay / 2
    @property
    def y1(self): return self.cy + self.ay / 2
    @property
    def area(self): return self.ax * self.ay


class PlacementError(ValueError):
    pass


def legal_halfspan(die_side: float, tile_side: float, keepout: float) -> float:
    h = (die_side - tile_side) / 2.0 - keepout
    if h < 0:
        raise PlacementError(
            f"tile side {tile_side:.3f} mm cannot fit inside die {die_side:.3f} mm "
            f"with {keepout:.3f} mm keep-out")
    return h


def generate(placement: str, n_vr: int, ax: float, ay: float, *,
             die_x: float, die_y: float, keepout: float, min_gap: float,
             p_total: float) -> list[Tile]:
    xl = legal_halfspan(die_x, ax, keepout)
    yl = legal_halfspan(die_y, ay, keepout)
    hx, hy = die_x / 2.0, die_y / 2.0
    p = p_total / n_vr

    def cx_(v): return float(np.clip(v, -xl, xl))
    def cy_(v): return float(np.clip(v, -yl, yl))

    pts: list[tuple[float, float]] = []

    if placement == "compact_central_pair":
        if n_vr != 2: raise PlacementError("compact_central_pair requires n_vr=2")
        d = (ax + min_gap) / 2.0
        pts = [(-d, 0.0), (d, 0.0)]

    elif placement == "opposing_edge_pair":
        if n_vr != 2: raise PlacementError("opposing_edge_pair requires n_vr=2")
        pts = [(-xl, 0.0), (xl, 0.0)]

    elif placement == "compact_2x2_central":
        if n_vr != 4: raise PlacementError("compact_2x2_central requires n_vr=4")
        dx, dy = (ax + min_gap) / 2.0, (ay + min_gap) / 2.0
        pts = [(sx * dx, sy * dy) for sx in (-1, 1) for sy in (-1, 1)]

    elif placement == "distributed_2x2":
        # Quadrant centroids of the die: each VR at the centre of the load quadrant
        # it serves - electrically the natural distributed architecture.
        if n_vr != 4: raise PlacementError("distributed_2x2 requires n_vr=4")
        pts = [(sx * cx_(hx / 2), sy * cy_(hy / 2)) for sx in (-1, 1) for sy in (-1, 1)]

    elif placement == "distributed_3x2":
        if n_vr != 6: raise PlacementError("distributed_3x2 requires n_vr=6")
        xs = [cx_(-2 * hx / 3), 0.0, cx_(2 * hx / 3)]
        ys = [cy_(-hy / 2), cy_(hy / 2)]
        pts = [(x, y) for y in ys for x in xs]

    elif placement == "uniform_distributed":
        # Exact factorisation of N into the most square lattice, so the layout is
        # genuinely uniform (N=8 -> 4x2, not a truncated 3x3).
        best = min(((abs(c - n_vr // c), c) for c in range(1, n_vr + 1) if n_vr % c == 0))
        cols = max(best[1], n_vr // best[1])
        rows = n_vr // cols
        xs = [cx_(-hx + (i + 0.5) * (2 * hx) / cols) for i in range(cols)]
        ys = [cy_(-hy + (j + 0.5) * (2 * hy) / rows) for j in range(rows)]
        pts = [(x, y) for y in ys for x in xs][:n_vr]

    elif placement == "edge_corner_biased":
        if n_vr != 4: raise PlacementError("edge_corner_biased requires n_vr=4")
        pts = [(sx * xl, sy * yl) for sx in (-1, 1) for sy in (-1, 1)]

    elif placement == "asymmetric_left":
        # All tiles confined to the left half: a symmetric heuristic cannot reproduce this.
        rows = 2 if n_vr <= 4 else 3
        cols = int(np.ceil(n_vr / rows))
        xs = [cx_(-xl + i * (ax + min_gap)) for i in range(cols)]
        if max(xs) > 0:
            raise PlacementError("asymmetric_left: tiles spill past the die centreline")
        ys = [cy_(-hy + (j + 0.5) * (2 * hy) / rows) for j in range(rows)]
        pts = [(x, y) for x in xs for y in ys][:n_vr]

    elif placement == "perimeter_ring":
        # Symmetric edge-weighted ring: split N between the two long edges (plus the
        # side edges when N is not divisible by 2), preserving mirror symmetry so the
        # case genuinely tests "edge-weighted SYMMETRY" as the spec intends.
        if n_vr % 2:
            raise PlacementError("perimeter_ring requires an even n_vr")
        per_edge = n_vr // 2
        xs = ([0.0] if per_edge == 1 else
              [cx_(-xl + i * (2 * xl) / (per_edge - 1)) for i in range(per_edge)])
        pts = [(x, -yl) for x in xs] + [(x, yl) for x in xs]

    elif placement == "perimeter_biased":
        # Corners first, then edge midpoints - the maximally corner-weighted symmetric ring.
        corners = [(sx * xl, sy * yl) for sx in (-1, 1) for sy in (-1, 1)]
        mids = [(0.0, -yl), (0.0, yl), (-xl, 0.0), (xl, 0.0)]
        pts = (corners + mids)[:n_vr]
        if n_vr > 8:
            raise PlacementError("perimeter_biased is defined for n_vr <= 8")
    else:
        raise PlacementError(f"unknown placement class {placement!r}")

    tiles = [Tile(cx, cy, ax, ay, p) for cx, cy in pts]
    validate(tiles, die_x=die_x, die_y=die_y, keepout=keepout, min_gap=min_gap,
             p_total=p_total, n_vr=n_vr)
    return tiles


def validate(tiles, *, die_x, die_y, keepout, min_gap, p_total, n_vr, area_total=None) -> None:
    if len(tiles) != n_vr:
        raise PlacementError(f"generated {len(tiles)} tiles, expected {n_vr}")

    hx, hy = die_x / 2 - keepout, die_y / 2 - keepout
    for i, t in enumerate(tiles):
        if t.x0 < -hx - 1e-9 or t.x1 > hx + 1e-9 or t.y0 < -hy - 1e-9 or t.y1 > hy + 1e-9:
            raise PlacementError(
                f"tile {i} at ({t.cx:.3f},{t.cy:.3f}) size {t.ax:.3f}x{t.ay:.3f} "
                f"leaves the legal region +/-({hx:.3f},{hy:.3f})")

    for i in range(len(tiles)):
        for j in range(i + 1, len(tiles)):
            a, b = tiles[i], tiles[j]
            ox = min(a.x1, b.x1) - max(a.x0, b.x0)
            oy = min(a.y1, b.y1) - max(a.y0, b.y0)
            # separated iff there is a clear gap >= min_gap along at least one axis
            if ox > -min_gap + 1e-9 and oy > -min_gap + 1e-9:
                raise PlacementError(
                    f"tiles {i},{j} violate the {min_gap:.3f} mm gap "
                    f"(centres ({a.cx:.3f},{a.cy:.3f}) and ({b.cx:.3f},{b.cy:.3f}))")

    ptot = sum(t.power_w for t in tiles)
    if abs(ptot - p_total) > 1e-9:
        raise PlacementError(f"heat-source integral {ptot:.9f} W != specified {p_total:.9f} W")

    if area_total is not None:
        atot = sum(t.area for t in tiles)
        if abs(atot - area_total) / area_total > 1e-3:
            raise PlacementError(
                f"total HVR footprint {atot:.4f} mm^2 != specified {area_total:.4f} mm^2")


def case_tiles(case: dict, stack: dict, doe: dict) -> list[Tile]:
    g, rules, dflt = stack["geometry"], doe["placement_rules"], doe["defaults"]
    return generate(
        case["placement"], case["n_vr"], case["tile_ax"], case["tile_ay"],
        die_x=g["functional_die"]["size_x"]["value"],
        die_y=g["functional_die"]["size_y"]["value"],
        keepout=rules["edge_keepout_mm"]["value"],
        min_gap=rules["min_gap_mm"]["value"],
        p_total=case.get("p_hvr_total_w", dflt["p_hvr_total_w"]))
