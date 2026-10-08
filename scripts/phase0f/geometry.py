"""Phase-0F Sec.1: physically realizable HVR cell / package geometry.

WHY THIS EXISTS
Phase 0B fixed the mechanical HVR tile at 150 um "PROVISIONAL ... MUST be replaced by the
HVR compiler stack height". Phase 0E discovered that the converter the compiler actually
selects contains a 500 um inductor, and recorded the inconsistency with the remark that it
"does not affect trends". That remark was never established, and this module tests it.

THE PHYSICAL PICTURE (June-2026 Sec. II)
  "high-side GaN switches ... flip-chipped to the RDL of the bottom substrate, while
   low-side switches (bottom layer), flying capacitors (middle layer), and inductors
   (top layer near the POLs) are embedded within the subsequent substrate power layers"
  "the number of power layers is ultimately determined by the number and size of components
   in the chosen VR topology and constrained by the capabilities of advanced packaging"

So the VR cell is a STACK of substrate power layers, its height is set by its components,
and the TSV field runs beneath it from the substrate underside. The governing rule is

    t_cell + h_tsv  <=  h_sub          with  h_tsv >= H_TSV_MIN > 0

A combination violating it is GEOMETRICALLY INFEASIBLE and must not be simulated.

WHAT IS SOURCED AND WHAT IS NOT
  * inductor height  -- SOURCED, per part, in the upstream INDUCTOR_LIBRARY.
  * GaN device height -- NOT in the EPC product table (it gives `Package(mm)` as lateral
    dimensions only, e.g. "LGA 2.5 x 1.5"). OPEN.
  * MLCC height -- not in the capacitor library. OPEN.
Because only the inductor height is sourced, the primary constraint is stated on the
inductor alone, which makes it a NECESSARY (not sufficient) condition. Additional layer
heights can only make a combination less feasible, never more, so every INFEASIBLE verdict
reached here is robust to the two open values.
"""
from __future__ import annotations
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SIVR = REPO / "Scalable_Integrated_VR"

# Minimum through-substrate via length. The TSV field must physically exist between the
# substrate underside and the cell; zero length is degenerate (it is also unmeshable).
H_TSV_MIN_UM = 50.0          # ASSUMPTION
H_TSV_MIN_MM = H_TSV_MIN_UM * 1e-3

# Open layer heights, carried as an envelope rather than invented.
GAN_H_UM = {"optimistic": 0.0, "nominal": 100.0, "pessimistic": 250.0}   # OPEN
MLCC_H_UM = {"optimistic": 0.0, "nominal": 100.0, "pessimistic": 250.0}  # OPEN
INTERLAYER_RDL_H_UM = 10.0   # sourced RDL thickness, ECTC-2024 (2 x 10 um Cu + dielectric)


def inductor_library():
    cwd = os.getcwd()
    sys.path.insert(0, str(SIVR / "src"))
    os.chdir(SIVR)
    try:
        from HVR_FULL_OPT_EPC_V2 import INDUCTOR_LIBRARY
        return list(INDUCTOR_LIBRARY)
    finally:
        os.chdir(cwd)


@dataclass
class CellStack:
    """Physical height budget of one HVR cell."""
    inductor_h_um: float
    inductor_name: str
    inductor_category: str
    gan_h_um: float
    mlcc_h_um: float
    n_interlayer: int = 2
    bound: str = "nominal"

    @property
    def t_cell_um(self) -> float:
        """Layers stack vertically: the cell is as tall as the sum of its layers."""
        return (self.inductor_h_um + self.gan_h_um + self.mlcc_h_um
                + self.n_interlayer * INTERLAYER_RDL_H_UM)

    @property
    def t_cell_mm(self) -> float:
        return self.t_cell_um * 1e-3

    @property
    def h_sub_min_um(self) -> float:
        return self.t_cell_um + H_TSV_MIN_UM


def cell_stack(design, bound: str = "nominal") -> CellStack:
    ind = design.inductor
    return CellStack(inductor_h_um=float(ind.height_um), inductor_name=ind.name,
                     inductor_category=ind.category,
                     gan_h_um=GAN_H_UM[bound], mlcc_h_um=MLCC_H_UM[bound], bound=bound)


@dataclass
class Realizability:
    feasible: bool
    reason: str
    h_sub_um: float
    t_cell_um: float
    h_tsv_um: float
    h_sub_min_um: float
    bound: str
    inductor_name: str
    inductor_h_um: float
    inductor_category: str


def check(design, h_sub_mm: float, bound: str = "nominal") -> Realizability:
    """Is this (converter, substrate thickness) pair physically buildable?"""
    cs = cell_stack(design, bound)
    h_um = h_sub_mm * 1e3
    h_tsv = h_um - cs.t_cell_um
    ok = h_tsv >= H_TSV_MIN_UM
    if ok:
        why = "realizable"
    elif h_tsv <= 0:
        why = (f"cell is {cs.t_cell_um:.0f} um tall but the substrate is only {h_um:.0f} um: "
               f"the converter does not fit at all")
    else:
        why = (f"cell {cs.t_cell_um:.0f} um leaves only {h_tsv:.0f} um of TSV, below the "
               f"{H_TSV_MIN_UM:.0f} um minimum")
    return Realizability(ok, why, h_um, cs.t_cell_um, h_tsv, cs.h_sub_min_um, bound,
                         cs.inductor_name, cs.inductor_h_um, cs.inductor_category)


def fitting_inductors(h_sub_mm: float, bound: str = "nominal"):
    """The subset of the library whose parts leave room for a TSV field at this thickness."""
    budget = (h_sub_mm * 1e3 - H_TSV_MIN_UM - GAN_H_UM[bound] - MLCC_H_UM[bound]
              - 2 * INTERLAYER_RDL_H_UM)
    return [i for i in inductor_library() if i.height_um <= budget], budget
