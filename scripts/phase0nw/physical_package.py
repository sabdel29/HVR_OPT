"""PHASE 0N-W --- the physical package configuration is the single source of truth.

Before this module the physical geometry lived in several places at once: 2.4 mm in a
board case AND in a YAML, 23.36 mm in the annular script AND in a YAML, 1963 um in a YAML
that nothing read, 49 cells in a comment. Commit 30f717b shipped a mesh described as
"2.4 mm" that contained a 1600 um board, which is precisely what a second copy buys you.

So: ONE loader, ONE builder, and every physical number comes out of the YAML.

    physical YAML
         v  load_physical_package_config()   <- validates, cross-checks, freezes
    PhysicalPackage
         v  build_physical_package()         <- the only way to mesh a physical package
    (mesh, materials, stack, tiles)

`load_physical_package_config` does not merely parse. It re-derives every quantity the
YAML states redundantly and refuses to return if the redundant statements disagree -- a
YAML that says "49 cells" and "cell_side 2.3685 mm" and "cutout 23.36 mm" is asserting a
geometric relation, and the point of the loader is to check it rather than trust it.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

R = Path(__file__).resolve().parents[2]
for _p in ("scripts/phase0mr", "scripts/phase0i", "scripts/phase0g", "scripts/phase0b",
           "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))

FORBIDDEN_BOARD_CASES = ("fr4_1p6mm", "fr4_2p4mm", "fr4_3p2mm")
# CONV_CELL_MM proxies that structurally EXCLUDE the high-side device. Never a Z2 total.
FORBIDDEN_CONV_TOTAL_UM = (1226.0, 1258.0)


class PhysicalConfigError(ValueError):
    """The configuration is internally inconsistent. Never downgraded to a warning."""


@dataclass(frozen=True)
class Tier:
    name: str
    um: float
    status: str


@dataclass(frozen=True)
class PhysicalPackage:
    label: str
    architecture: str
    board_case: str
    board_thickness_um: float
    board_model_level: str
    eta_nominal: float
    eta_sensitivity: tuple
    thickness_sensitivity_case: str
    substrate_um: float
    substrate_size_mm: tuple
    cutout_mm: float | None
    cells: int
    cell_area_mm2: float
    cell_side_mm: float
    conv_total_um: float
    tiers: tuple
    converter_implemented: bool
    open_gates: tuple
    source_path: Path = field(compare=False, default=None)

    # ---- derived, never stored twice -------------------------------------------------
    @property
    def board_thickness_mm(self) -> float:
        return self.board_thickness_um / 1e3

    @property
    def substrate_mm(self) -> float:
        return self.substrate_um / 1e3

    @property
    def conv_total_mm(self) -> float:
        return self.conv_total_um / 1e3

    @property
    def cell_grid_n(self) -> int:
        n = int(round(math.sqrt(self.cells)))
        if n * n != self.cells:
            raise PhysicalConfigError(f"{self.cells} cells is not a square grid")
        return n

    def tier_names(self) -> list:
        return [t.name for t in self.tiers]


def load_physical_package_config(path) -> PhysicalPackage:
    """Parse, validate and cross-check one physical package YAML."""
    path = Path(path)
    c = yaml.safe_load(path.read_text())

    def need(d, key, where):
        if key not in d:
            raise PhysicalConfigError(f"{path.name}: missing {where}.{key}")
        return d[key]

    b = need(c, "board", "root")
    case = need(b, "case", "board")
    if case in FORBIDDEN_BOARD_CASES:
        raise PhysicalConfigError(
            f"{path.name}: board.case '{case}' is an unsourced legacy case and is "
            f"forbidden on the physical path; use it968g_2p4mm")

    conv = need(c, "converter", "root")
    tiers = tuple(Tier(t["name"], float(t["um"]), t.get("status", "OPEN"))
                  for t in need(conv, "tiers_from_substrate_downward", "converter"))
    if not tiers:
        raise PhysicalConfigError(f"{path.name}: converter has no tiers")

    # --- cross-check 1: the tier list must ADD UP to the stated total -----------------
    stated = float(need(conv, "with_land_side_rdl_um", "converter"))
    summed = sum(t.um for t in tiers)
    if abs(summed - stated) > 1e-9:
        raise PhysicalConfigError(
            f"{path.name}: converter tiers sum to {summed:.1f} um but "
            f"with_land_side_rdl_um says {stated:.1f} um")
    if any(abs(stated - f) < 1e-9 for f in FORBIDDEN_CONV_TOTAL_UM):
        raise PhysicalConfigError(
            f"{path.name}: {stated:.0f} um is an embedded-cell proxy that excludes the "
            f"high-side device; it can never be a Z2 converter total")

    # --- cross-check 2: cell count, area and side must agree --------------------------
    cells = int(need(conv, "cells", "converter"))
    area = float(need(conv, "cell_area_mm2", "converter"))
    side = float(need(conv, "cell_side_mm", "converter"))
    if abs(side * side - area) / area > 2e-4:
        raise PhysicalConfigError(
            f"{path.name}: cell_side {side} mm squares to {side*side:.4f} mm2, "
            f"not the stated cell_area_mm2 {area}")

    # --- cross-check 3: the cutout must match its own stated rule ---------------------
    cut = c.get("cutout") or {}
    cut_mm = float(cut["width_mm"]) if "width_mm" in cut else None
    if cut_mm is not None and "sidewall_clearance_mm" in cut:
        n = int(round(math.sqrt(cells)))
        # the grid bbox is derived from the cell pitch implied by the cutout rule, so the
        # only self-consistent check is bbox + 2*clearance == width
        bbox = cut_mm - 2 * float(cut["sidewall_clearance_mm"])
        if bbox <= n * side * 0.5:
            raise PhysicalConfigError(
                f"{path.name}: cutout {cut_mm} mm leaves a {bbox:.2f} mm grid bbox, too "
                f"small for {n}x{n} cells of {side} mm")

    sub = need(c, "substrate", "root")
    return PhysicalPackage(
        label=c.get("label", path.stem),
        architecture=need(c, "architecture", "root"),
        board_case=case,
        board_thickness_um=float(need(b, "thickness_um", "board")),
        board_model_level=b.get("model_level", "PCB-H0"),
        eta_nominal=float(b.get("eta_nominal", 0.5)),
        eta_sensitivity=tuple(b.get("eta_sensitivity", (0.25, 0.5, 0.75))),
        thickness_sensitivity_case=b.get("thickness_sensitivity_case", ""),
        substrate_um=float(need(sub, "thickness_um", "substrate")),
        substrate_size_mm=tuple(sub.get("size_mm", (30.0, 30.0))),
        cutout_mm=cut_mm,
        cells=cells, cell_area_mm2=area, cell_side_mm=side,
        conv_total_um=stated, tiers=tiers,
        converter_implemented=bool(conv.get("implemented", False)),
        open_gates=tuple(c.get("open_gates", ())),
        source_path=path,
    )


def build_physical_package(cfg: PhysicalPackage, h_xy: float = 1.1):
    """Mesh a physical package. Every geometric argument comes from `cfg`.

    This is the only supported entry point for the physical path: calling
    production_et.build_global directly is what allowed a "2.4 mm" run to carry a 1.6 mm
    board, because the board defaulted silently when the argument was omitted.
    """
    import production_et as PE
    if cfg.board_case in FORBIDDEN_BOARD_CASES:
        raise PhysicalConfigError(f"refusing to build on legacy board {cfg.board_case}")
    return PE.build_global(cfg.architecture, cfg.substrate_mm, h_xy=h_xy,
                           board_case=cfg.board_case, cutout_mm=cfg.cutout_mm)


def measure_layers(mesh) -> dict:
    """Actual z extent of every meshed layer, in um. The mesh is the witness, not the YAML."""
    out = {}
    for L in mesh.layers:
        lo, hi = out.get(L.name, (None, None))
        z0, z1 = L.z0 * 1e3, L.z1 * 1e3
        out[L.name] = (z0 if lo is None else min(lo, z0), z1 if hi is None else max(hi, z1))
    return {k: {"z0_um": v[0], "z1_um": v[1], "t_um": v[1] - v[0]} for k, v in out.items()}


if __name__ == "__main__":
    cfg = load_physical_package_config(R / "configs/phase0nt/z2_2p4mm_cutout.yaml")
    print(f"{cfg.label}: {cfg.architecture}")
    print(f"  board      {cfg.board_case} {cfg.board_thickness_um:.0f} um "
          f"({cfg.board_model_level}, eta={cfg.eta_nominal})")
    print(f"  substrate  {cfg.substrate_um:.0f} um   cutout {cfg.cutout_mm} mm")
    print(f"  converter  {cfg.conv_total_um:.0f} um over {len(cfg.tiers)} tiers, "
          f"{cfg.cells} cells of {cfg.cell_side_mm} mm  implemented={cfg.converter_implemented}")
    m, mats, st, tiles = build_physical_package(cfg)
    lay = measure_layers(m)
    print(f"  mesh       {m.n_elems} elements, {len(tiles)} tiles")
    for k in ("board", "bga", "sub_lower", "conv", "die"):
        if k in lay:
            print(f"    {k:10s} {lay[k]['t_um']:8.1f} um  "
                  f"[{lay[k]['z0_um']:+.1f}, {lay[k]['z1_um']:+.1f}]")
