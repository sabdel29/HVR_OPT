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
    # PHASE 0N-V. The source-backed IT-968G cases are NOT literals here -- they are
    # inserted below by _add_it968g_cases() from the generator's single nominal_tensor
    # block, because a copy of a derived value is a second source that goes stale alone.
    # The fr4_* entries above are UNSOURCED and are kept only for reproducibility.
}


def bga_material():
    """Homogenised ball array: normal stiffness E*f, giving k_z = E*f/h = 13 090 N/mm^3."""
    return {"status": "DERIVED", "elastic_type": "iso",
            "E": {"value": E_SOLDER_MPA * AREA_FRACTION, "status": "DERIVED"},
            "nu": {"value": NU_SOLDER, "status": "ASSUMPTION"},
            "cte": {"value": CTE_SOLDER, "status": "SOURCE_BACKED"},
            "k": {"value": K_SOLDER * AREA_FRACTION, "status": "DERIVED"}}


def board_material(case):
    """Board card. The it968g_* cases are DERIVED from a datasheet; the fr4_* are not.

    ELASTIC ANISOTROPY IS DELIBERATELY NOT MODELLED. Two independent reasons:
      1. etm/config.py's ``*ELASTIC, TYPE=ORTHO`` emitter writes D1111 = D2222 = D3333
         from a single C11, i.e. CUBIC symmetry. It cannot express E_xy != E_z at all.
      2. Even with a general emitter, three of the five transversely-isotropic constants
         (E_z, G_xz, nu_xz) are OPEN -- absent from the IT-968G datasheet and not
         derivable from E_warp/E_fill. Supplying them would be fabrication.
    So E is the in-plane homogenised modulus and the through-thickness compliance is
    UNMODELLED, not modelled-as-equal. research/PCB_IT968G_HOMOGENIZATION.md Sec.5
    quantifies what that omission is worth and records it as OPEN.

    THERMAL anisotropy IS modelled: k_ortho is a first-class CalculiX card.
    """
    c = BOARD_CASES[case]
    derived = case.startswith("it968g_")
    st = "DERIVED" if derived else "ASSUMPTION"
    m = {"status": st, "elastic_type": "iso",
         "E": {"value": c["E_MPa"], "status": st},
         "nu": {"value": c["nu"], "status": "ASSUMPTION"},   # OPEN for IT-968G
         "cte": {"value": c["cte"], "status": st},
         "k": {"value": c["k"], "status": st}}
    if c.get("k_ortho"):
        m["k_ortho"] = {"value": list(c["k_ortho"]), "status": "DERIVED"}
    return m


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


# ---------------------------------------------------------------------------------- 0N-V
def _add_it968g_cases():
    """Derive the source-backed board cases from the ONE nominal tensor.

    `scripts/phase0nv_pcb_homogenization.py` owns the reduction (nominal copper coverage,
    midpoint of each bounded bracket) and writes it to research/phase0nv/. Re-picking a
    value out of the sweep here would make this file a second source, and two sources of a
    derived number drift apart without anything going red.

    The two cases share ONE material dict and differ ONLY in thickness, so a 2.4 -> 3.2 mm
    comparison isolates geometric stiffness. The fr4_* pair changes E/CTE/k with thickness
    and is unsourced; it is kept for reproducibility and must not be used for that study.

    Conductivity is orthotropic (k_xy >> k_z, ~148x) and reaches CalculiX as a real
    *CONDUCTIVITY, TYPE=ORTHO card. Elasticity is isotropic at the in-plane modulus: the
    solver's ORTHO elastic card is cubic-only, AND E_z/G_xz/nu_xz are OPEN. See
    research/PCB_IT968G_HOMOGENIZATION.md Sec.5 for what that omission is worth.
    """
    import pathlib
    j = pathlib.Path(__file__).resolve().parents[2] / "research" / "phase0nv" / "pcb_homogenization.json"
    n = json.loads(j.read_text())["nominal_tensor"]
    mat = {"E_MPa": n["E_MPa"], "nu": n["nu"], "cte": n["cte"] * 1e-6, "k": n["k_z"],
           "k_ortho": [n["k_xy"], n["k_xy"], n["k_z"]]}
    for key, t in (("it968g_2p4mm", 2.4), ("it968g_3p2mm", 3.2)):
        BOARD_CASES[key] = dict(mat, t_mm=t)


_add_it968g_cases()
