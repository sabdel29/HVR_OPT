#!/usr/bin/env python3
"""Phase-0I -- architecture-aware realizability and rail-aware power paths.

DEFECT #33, found in this phase
-------------------------------
`kw1.design_1kw()` takes no architecture argument. The embedded realizability rule
`t_cell + h_tsv <= h_sub` was therefore applied to EVERY architecture, including ARCH_B
(converter below the substrate, 1 V rail up through the TSVs) and ARCH_C (2.5D lateral) --
neither of which puts the converter inside the substrate at all. At h_sub = 0.30 mm the
code returns "no inductor fits h_sub=300 um (budget 30 um)" for all three, which is the
right answer for one of them.

The electrical model has varied the converter's vertical position since Phase 0D-R. The
geometric and mechanical models never did. Every "unbuildable" verdict Phase 0H issued
against a thin substrate is therefore EMBEDDED-SPECIFIC.

Architecture-specific minima
----------------------------
EMBEDDED   h_sub >= t_cell + h_tsv_min, with t_cell the summed component stack (Phase 0H).
OTHERS     the converter is not in the substrate, so the substrate only has to carry a TSV
           field. The binding constraint is TSV manufacturability. June-2026 Table III gives
           d = 30 um and h = 300 um for the power-layer TSVs, i.e. a demonstrated aspect
           ratio of 10:1 at a 300 um layer. 300 um is therefore adopted as the SOURCE-BACKED
           minimum for non-embedded architectures, and any thinner value would be an
           extrapolation below the source's own demonstrated geometry rather than above it.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
for p in ("phase0h", "phase0f", "phase0e", "phase0dr"):
    sys.path.insert(0, str(REPO / "scripts" / p))

from geometry import (GAN_H_UM, H_TSV_MIN_UM, INTERLAYER_RDL_H_UM, MLCC_H_UM,  # noqa: E402
                      inductor_library)
from scope import Q, Scope, ScopeError, total, watts_per_regulator, watts_system  # noqa: E402

CFG = REPO / "configs" / "phase0i" / "z_architectures.yaml"

# SOURCED in Phase 0H from the manufacturer datasheets. These replace the invented
# GAN_H_UM envelope for every architecture that actually embeds the device.
GAN_HS_UM = 685.0        # EPC2212 datasheet Side View, nominal (815 max)
GAN_LS_UM = 606.0        # EPC2090 datasheet: 518 +/- 25 die + 50 Cu + 3 Ni + 35 solder

# June-2026 Table III: power-layer TSV d = 30 um, h = 300 um -> demonstrated AR 10:1.
TSV_D_UM = 30.0
TSV_DEMONSTRATED_H_UM = 300.0
TSV_DEMONSTRATED_AR = TSV_DEMONSTRATED_H_UM / TSV_D_UM


def load_cfg() -> dict:
    return yaml.safe_load(CFG.read_text())


@dataclass
class ZRealizability:
    arch: str
    h_sub_mm: float
    feasible: bool
    reason: str
    rule: str
    h_sub_min_um: float
    t_cell_um: float | None
    components_in_substrate: list = field(default_factory=list)
    tsv_aspect_ratio: float | None = None


def embedded_cell_um(mlcc_bound: str = "nominal", inductor_h_um: float = 500.0) -> float:
    """Height of the substrate power-layer stack for the EMBEDDED architecture.

    June-2026 Sec. II: the LOW-SIDE switch, the flying capacitors and the inductors are
    embedded in the substrate power layers; the HIGH-SIDE device is flip-chipped to the RDL
    of the bottom substrate and is therefore BELOW z = 0.
    """
    return inductor_h_um + GAN_LS_UM + MLCC_H_UM[mlcc_bound] + 2 * INTERLAYER_RDL_H_UM


def realizable(arch: str, h_sub_mm: float, mlcc_bound: str = "nominal",
               inductor_h_um: float = 500.0) -> ZRealizability:
    """Architecture-aware realizability. This is the DEFECT #33 fix."""
    h_um = h_sub_mm * 1e3
    if arch in ("ARCH_Z1_EMBEDDED", "ARCH_A"):
        t_cell = embedded_cell_um(mlcc_bound, inductor_h_um)
        h_min = t_cell + H_TSV_MIN_UM
        ok = h_um >= h_min
        return ZRealizability(
            arch, h_sub_mm, ok,
            "realizable" if ok else
            f"embedded cell is {t_cell:.0f} um and needs {H_TSV_MIN_UM:.0f} um of TSV "
            f"beneath it, so h_sub must be >= {h_min:.0f} um; got {h_um:.0f} um",
            rule="t_cell + h_tsv_min <= h_sub  (components embedded in the substrate)",
            h_sub_min_um=h_min, t_cell_um=t_cell,
            components_in_substrate=["gan_ls", "mlcc", "inductor", "interlayer_rdl"],
            tsv_aspect_ratio=(h_um - t_cell) / TSV_D_UM if h_um > t_cell else None)

    # every other architecture: the substrate carries a TSV field and nothing else
    h_min = TSV_DEMONSTRATED_H_UM
    ok = h_um >= h_min
    ar = h_um / TSV_D_UM
    return ZRealizability(
        arch, h_sub_mm, ok,
        "realizable" if ok else
        f"substrate {h_um:.0f} um is below the source-demonstrated power-layer thickness "
        f"of {h_min:.0f} um (June-2026 Table III, d = 30 um TSV at h = 300 um)",
        rule="h_sub >= source-demonstrated TSV layer thickness (converter NOT embedded)",
        h_sub_min_um=h_min, t_cell_um=None,
        components_in_substrate=[], tsv_aspect_ratio=ar)


# ------------------------------------------------------------------ rail-aware power paths
@dataclass
class Segment:
    seg: str
    tier: str
    rail: str
    v_volt: float
    i_a: float
    i_rms_a: float
    location: str
    scope: str


def rail_currents(load_w: float = 1000.0, v_out: float = 1.0, v_in: float = 48.0,
                  eta: float = 0.889) -> dict:
    """System-level rail currents. eta is the Phase-0F converter efficiency at 1 kW."""
    i_out = load_w / v_out
    p_in = load_w / eta
    i_in = p_in / v_in
    return {"I_out_a": i_out, "I_in_a": i_in, "P_in_w": p_in}


def path_for(arch: str, load_w: float = 1000.0) -> list[Segment]:
    """The ordered segment chain, with the rail each segment actually carries.

    'TSV = 48 V' and 'TSV = 1 V' are BOTH wrong as global statements. Which rail crosses the
    substrate is set by where the conversion happens relative to the substrate.
    """
    rc = rail_currents(load_w)
    hv, lv = rc["I_in_a"], rc["I_out_a"]
    S = Segment
    if arch == "ARCH_Z1_EMBEDDED":
        return [
            S("board -> substrate underside", "bga", "HV", 48.0, hv, hv, "z < 0", "SYSTEM"),
            S("underside -> embedded cell", "tsv", "HV", 48.0, hv, hv,
              "through h_sub - t_cell", "SYSTEM"),
            S("conversion in the power layers", "converter", "CONV", 48.0, hv, hv,
              "inside the substrate", "SYSTEM"),
            S("cell -> die POL", "microbump", "LV", 1.0, lv, lv, "10 um pads", "SYSTEM"),
            S("lateral spreading under the die", "rdl", "LV", 1.0, lv, lv,
              "package RDL", "SYSTEM"),
        ]
    if arch == "ARCH_Z2_BACKSIDE":
        return [
            S("board -> backside VR", "bga", "HV", 48.0, hv, hv, "z < 0, short", "SYSTEM"),
            S("conversion on the backside chiplet", "converter", "CONV", 48.0, hv, hv,
              "below the substrate", "SYSTEM"),
            S("backside VR -> die, through the substrate", "tsv", "LV", 1.0, lv, lv,
              "through the FULL h_sub", "SYSTEM"),
            S("substrate top -> die POL", "microbump", "LV", 1.0, lv, lv, "10 um pads",
              "SYSTEM"),
            S("lateral spreading under the die", "rdl", "LV", 1.0, lv, lv, "package RDL",
              "SYSTEM"),
        ]
    if arch == "ARCH_Z4_POWER_DIE":
        return [
            S("board -> substrate underside", "bga", "HV", 48.0, hv, hv, "z < 0", "SYSTEM"),
            S("underside -> power die", "tsv", "HV", 48.0, hv, hv,
              "through the FULL h_sub", "SYSTEM"),
            S("conversion on the power die", "converter", "CONV", 48.0, hv, hv,
              "above the substrate, below the compute die", "SYSTEM"),
            S("power die -> compute die", "microbump", "LV", 1.0, lv, lv,
              "10 um hybrid pads, the SHORTEST possible 1 V path", "SYSTEM"),
            S("lateral spreading on the power die", "rdl", "LV", 1.0, lv, lv,
              "power-die RDL", "SYSTEM"),
        ]
    if arch == "ARCH_Z5_2P5D_LATERAL":
        return [
            S("board -> substrate underside", "bga", "HV", 48.0, hv, hv, "z < 0", "SYSTEM"),
            S("underside -> lateral VR field", "tsv", "HV", 48.0, hv, hv,
              "through the FULL h_sub", "SYSTEM"),
            S("conversion beside the die", "converter", "CONV", 48.0, hv, hv,
              "lateral, on the interposer", "SYSTEM"),
            S("VR field -> die, ACROSS the interposer", "rdl", "LV", 1.0, lv, lv,
              "long lateral interposer RDL", "SYSTEM"),
            S("interposer -> die POL", "microbump", "LV", 1.0, lv, lv, "10 um pads",
              "SYSTEM"),
        ]
    raise ValueError(f"no power path defined for {arch}")


def tsv_rail(arch: str) -> str:
    return next(s.rail for s in path_for(arch) if s.tier == "tsv")


def tsv_current(arch: str, load_w: float = 1000.0) -> float:
    return next(s.i_a for s in path_for(arch) if s.tier == "tsv")
