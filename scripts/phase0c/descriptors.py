"""Geometric descriptors of the HVR inclusion field.

Phase 0B proposed that C05 ~ C13 because subdividing a symmetric fixed-area inclusion
leaves the relevant mechanical moments unchanged. These descriptors let that explanation
be tested quantitatively rather than asserted.

All moments are taken about the DIE CENTRE (0,0), which is also the package centre and
the symmetry point of the thermal and support boundary conditions.
"""
from __future__ import annotations

import math

import numpy as np


def descriptors(tiles, tile_thickness_mm: float) -> dict:
    a = np.array([t.area for t in tiles])                 # mm^2
    x = np.array([t.cx for t in tiles])
    y = np.array([t.cy for t in tiles])
    q = np.array([t.power_w for t in tiles])              # W
    ax = np.array([t.ax for t in tiles])
    ay = np.array([t.ay for t in tiles])

    A = a.sum()
    # area-weighted (stiffness) centroid and heat centroid
    cx_a, cy_a = float((a * x).sum() / A), float((a * y).sum() / A)
    Q = q.sum()
    cx_q, cy_q = float((q * x).sum() / Q), float((q * y).sum() / Q)

    # first moment magnitude about the die centre
    m1_area = math.hypot((a * x).sum(), (a * y).sum())     # mm^3
    m1_heat = math.hypot((q * x).sum(), (q * y).sum())     # W.mm

    # second moments about the die centre: parallel-axis (own inertia + A d^2)
    Ixx = float((a * y ** 2 + a * ay ** 2 / 12.0).sum())   # about x-axis, mm^4
    Iyy = float((a * x ** 2 + a * ax ** 2 / 12.0).sum())   # about y-axis, mm^4
    Ipol = Ixx + Iyy
    Rg = math.sqrt(Ipol / A) if A else float("nan")

    # in-plane anisotropy of the inclusion field (>0 => stiffer/more spread along x)
    aniso = float((Iyy - Ixx) / (Iyy + Ixx)) if Ipol else 0.0

    # own-shape anisotropy only (aspect-ratio signature, placement removed)
    own_Ixx = float((a * ay ** 2 / 12.0).sum())
    own_Iyy = float((a * ax ** 2 / 12.0).sum())
    aniso_shape = float((own_Iyy - own_Ixx) / (own_Iyy + own_Ixx)) if (own_Ixx + own_Iyy) else 0.0

    # heat second moment
    Ixx_q = float((q * y ** 2).sum())
    Iyy_q = float((q * x ** 2).sum())

    return {
        "n_tiles": len(tiles),
        "A_total_mm2": float(A),
        "V_incl_mm3": float(A * tile_thickness_mm),
        "centroid_area_x_mm": cx_a, "centroid_area_y_mm": cy_a,
        "centroid_area_offset_mm": float(math.hypot(cx_a, cy_a)),
        "centroid_heat_x_mm": cx_q, "centroid_heat_y_mm": cy_q,
        "centroid_heat_offset_mm": float(math.hypot(cx_q, cy_q)),
        "first_moment_area_mm3": float(m1_area),
        "first_moment_heat_Wmm": float(m1_heat),
        "Ixx_mm4": Ixx, "Iyy_mm4": Iyy, "I_polar_mm4": Ipol,
        "radius_gyration_mm": Rg,
        "anisotropy": aniso, "anisotropy_shape_only": aniso_shape,
        "Ixx_heat_Wmm2": Ixx_q, "Iyy_heat_Wmm2": Iyy_q,
        "mean_tile_area_mm2": float(a.mean()),
        "tile_aspect_ratio": float((ax / ay).mean()),
    }
