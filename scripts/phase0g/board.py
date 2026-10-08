"""Phase-0G Sec.5/7: an EXPLICIT package + BGA + board assembly.

The compact BC-B foundation has two problems that only became visible in Phase 0G:

  1. it fixes ALL THREE DOF on the underside plane, so the package is clamped in-plane --
     a BGA field is compliant in shear and does not do that;
  2. at low foundation modulus it is numerically degenerate against silicon (a stiffness
     ratio of ~1e8), so its k -> 0 limit never reaches the free-package answer: 0.739 um
     against 8.287 um for BC_A on the identical mesh.

This module replaces it with real layers whose moduli are in a well-conditioned range: a
homogenised BGA field with the SOURCE-BACKED ball geometry, and an FR-4 board. The assembly
is restrained only by 3-2-1, so nothing is clamped and the free limit is recovered by
construction when the board is made compliant.
"""
from __future__ import annotations
import json
import math

# --- BGA field, homogenised over the ball pitch (June-2026 Table III geometry) -----------
BALL_D_MM, BALL_H_MM, BALL_P_MM = 0.400, 0.300, 0.800
AREA_FRACTION = math.pi * BALL_D_MM ** 2 / 4 / BALL_P_MM ** 2      # 0.19635
E_SOLDER_MPA = 20000.0        # STAMP-2.5D material table (SOURCE_BACKED)
NU_SOLDER = 0.35              # ASSUMPTION
CTE_SOLDER = 20.5e-6          # STAMP-2.5D (SOURCE_BACKED)
K_SOLDER = 50.0               # W/mK, ASSUMPTION

# --- board envelope. No board data exists for this vehicle, so a source-backed envelope --
BOARD_CASES = {
    "fr4_1p6mm":   {"t_mm": 1.6, "E_MPa": 20000.0, "nu": 0.20, "cte": 17.0e-6, "k": 0.30},
    "fr4_2p4mm":   {"t_mm": 2.4, "E_MPa": 22000.0, "nu": 0.20, "cte": 16.0e-6, "k": 0.30},
    "fr4_3p2mm":   {"t_mm": 3.2, "E_MPa": 24000.0, "nu": 0.20, "cte": 15.0e-6, "k": 0.35},
    "compliant":   {"t_mm": 0.8, "E_MPa": 12000.0, "nu": 0.20, "cte": 18.0e-6, "k": 0.30},
    "stiff_metal_backed": {"t_mm": 3.2, "E_MPa": 120000.0, "nu": 0.30, "cte": 12.0e-6,
                           "k": 100.0},
}


def bga_material():
    """Homogenised ball array: normal stiffness E*f, giving k_z = E*f/h = 13 090 N/mm^3."""
    return {"status": "DERIVED", "elastic_type": "iso",
            "E": {"value": E_SOLDER_MPA * AREA_FRACTION, "status": "DERIVED"},
            "nu": {"value": NU_SOLDER, "status": "ASSUMPTION"},
            "cte": {"value": CTE_SOLDER, "status": "SOURCE_BACKED"},
            "k": {"value": K_SOLDER * AREA_FRACTION, "status": "DERIVED"}}


def board_material(case):
    c = BOARD_CASES[case]
    return {"status": "ASSUMPTION", "elastic_type": "iso",
            "E": {"value": c["E_MPa"], "status": "ASSUMPTION"},
            "nu": {"value": c["nu"], "status": "ASSUMPTION"},
            "cte": {"value": c["cte"], "status": "ASSUMPTION"},
            "k": {"value": c["k"], "status": "ASSUMPTION"}}


def stack_with_board(stack, t_tile_mm, case="fr4_1p6mm"):
    """Deep copy of the package stack with BGA and board materials injected."""
    st = json.loads(json.dumps(stack))
    st["geometry"]["hvr_tile"]["thickness"]["value"] = t_tile_mm
    st["materials"]["bga_homog"] = bga_material()
    st["materials"]["board_fr4"] = board_material(case)
    return st


def bottom_layers(case="fr4_1p6mm", nz_board=2, nz_bga=2):
    """(name, thickness, material, n_elements) laid down below z = 0, deepest first."""
    return [("board", BOARD_CASES[case]["t_mm"], "board_fr4", nz_board),
            ("bga", BALL_H_MM, "bga_homog", nz_bga)]


def k_z_equivalent():
    """Normal foundation stiffness of the ball array alone, for comparison with BC-B."""
    return E_SOLDER_MPA * AREA_FRACTION / BALL_H_MM
