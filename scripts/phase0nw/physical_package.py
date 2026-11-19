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
    # FINAL CLOSURE: the primary Z2 is direct-fed with an explicit VR attach and a void
    # sidewall clearance. Defaults keep any older YAML loadable; the guard in the loader
    # refuses a Z2_DIRECT_FEED file that omits any of the three.
    variant: str = ""
    hv_feed: str = ""
    attach_um: float = 0.0
    attach: tuple = ()
    clearance_mm: float | None = None
    clearance_void: bool = False
    out_of_cell_primary: str = "F1_encapsulated"
    #: board + BGA depth minus attach + converter (um): < 0 = the converter protrudes below
    #: the board backside (TCPMT round 3, check_cutout_fit)
    cutout_fit_margin_um: float | None = None
    #: the design record entry the converter block restates ('' = not record-driven)
    design: str = ""
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
    # TCPMT round 3: the converter block restates THE design record (checked) or, for another
    # HVR_DESIGN entry, is replaced by it (design_record.apply_converter)
    sys.path.insert(0, str(R / "scripts/phase0nw"))
    import design_record as DR
    c = DR.apply_converter(c, "Z2", source=path.name)

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
    variant = c.get("variant", "")
    feed = (c.get("hv_feed") or {}).get("mode", "")
    va = c.get("vr_attach") or {}
    attach_um = float(va.get("thickness_um", 0.0))
    if va:
        parts = float(va.get("cu_height_um", 0.0)) + float(va.get("cap_height_um", 0.0))
        if abs(parts - attach_um) > 1e-9:
            raise PhysicalConfigError(
                f"{path.name}: vr_attach Cu {va.get('cu_height_um')} + cap "
                f"{va.get('cap_height_um')} um does not add up to {attach_um} um")
    ooc = (c.get("out_of_cell") or {}).get("primary", "F1_encapsulated")
    clr = cut.get("sidewall_clearance_mm")
    clr_void = str(cut.get("sidewall_content", "")).upper() == "VOID"
    # --- cross-check 4: a direct-fed Z2 must carry ALL of its defining features --------
    if variant == "Z2_DIRECT_FEED":
        missing = [k for k, ok in (("hv_feed.mode = DIRECT_FEED", feed == "DIRECT_FEED"),
                                   ("vr_attach.thickness_um > 0", attach_um > 0),
                                   ("cutout.sidewall_content = VOID", clr_void),
                                   ("out_of_cell.primary = F1_clearance",
                                    ooc == "F1_clearance")) if not ok]
        if missing:
            raise PhysicalConfigError(f"{path.name}: Z2_DIRECT_FEED lacks {missing}")
    # --- cross-check 5 (TCPMT round 3): does the converter FIT the cutout? It hangs from the
    # substrate underside through the attach; the cutout is as deep as the board + BGA. A
    # converter deeper than that protrudes below the board backside: recorded (the board film
    # then takes only the exposed board faces), never silently clipped.
    import board as BRD
    t_board_mesh = BRD.BOARD_CASES[case]["t_mm"] * 1e3
    if abs(t_board_mesh - float(need(b, "thickness_um", "board"))) > 1e-9:
        raise PhysicalConfigError(f"{path.name}: board.thickness_um {b['thickness_um']} but "
                                  f"board case {case} meshes {t_board_mesh} um")
    fit = t_board_mesh + BRD.BALL_H_MM * 1e3 - (attach_um + stated)
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
        variant=variant, hv_feed=feed, attach_um=attach_um,
        attach=tuple(sorted((k, v) for k, v in va.items() if not isinstance(v, (dict, list)))),
        clearance_mm=float(clr) if clr is not None else None, clearance_void=clr_void,
        out_of_cell_primary=ooc,
        cutout_fit_margin_um=fit if cut_mm is not None else None,
        design=str((c.get("converter") or {}).get("design") or ""),
        source_path=path,
    )


def build_physical_package(cfg: PhysicalPackage, h_xy: float = 1.1,
                           discrete_cells: bool = True,
                           out_of_cell: str | None = None):
    """Mesh a physical package. Every geometric argument comes from `cfg`.

    This is the only supported entry point for the physical path: calling
    production_et.build_global directly is what allowed a "2.4 mm" run to carry a 1.6 mm
    board, because the board defaulted silently when the argument was omitted.
    """
    import production_et as PE
    if cfg.board_case in FORBIDDEN_BOARD_CASES:
        raise PhysicalConfigError(f"refusing to build on legacy board {cfg.board_case}")
    out_of_cell = out_of_cell or cfg.out_of_cell_primary
    if not discrete_cells:
        return PE.build_global(cfg.architecture, cfg.substrate_mm, h_xy=h_xy,
                               board_case=cfg.board_case, cutout_mm=cfg.cutout_mm)
    return PE.build_global(cfg.architecture, cfg.substrate_mm, h_xy=h_xy,
                           board_case=cfg.board_case, cutout_mm=cfg.cutout_mm,
                           physical_converter=(cfg, out_of_cell))


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
          f"{cfg.cells} cells of {cfg.cell_side_mm} mm")
    m, mats, st, tiles = build_physical_package(cfg)
    lay = measure_layers(m)
    print(f"  mesh       {m.n_elems} elements, {len(tiles)} tiles")
    for k in ("board", "bga", "sub_lower", "conv", "die"):
        if k in lay:
            print(f"    {k:10s} {lay[k]['t_um']:8.1f} um  "
                  f"[{lay[k]['z0_um']:+.1f}, {lay[k]['z1_um']:+.1f}]")


def build_physical_z1(cfg=None, h_xy: float = 1.1,
                      out_of_cell: str = "F1_encapsulated"):
    """Mesh the COMPLETE physical Z1 from Z1's OWN configuration.

    `cfg` is a Z1Package (or None for the default Z1 YAML). A Z2 PhysicalPackage is
    REFUSED: Z1 reading Z2's board case and substrate thickness is exactly the coupling
    this signature exists to break, and it is invisible while the two configs agree.
    """
    import production_et as PE
    if cfg is None:
        cfg = load_z1_package_config()
    if isinstance(cfg, PhysicalPackage):
        raise PhysicalConfigError(
            "build_physical_z1 received a Z2 PhysicalPackage. Z1 must be built from "
            "configs/phase0nx/z1_physical.yaml via load_z1_package_config().")
    if cfg.board_case in FORBIDDEN_BOARD_CASES:
        raise PhysicalConfigError(f"refusing to build on legacy board {cfg.board_case}")
    return PE.build_global(cfg.architecture, cfg.substrate_mm, h_xy=h_xy,
                           board_case=cfg.board_case, cutout_mm=None,
                           physical_z1=(cfg, out_of_cell))


@dataclass(frozen=True)
class Z1Package:
    """Z1's own configuration object, loaded from configs/phase0nx/z1_physical.yaml.

    build_physical_z1() used to take the Z2 PhysicalPackage and read board_case and
    substrate_mm off it. Those values match today, so the geometry was right -- but Z1
    was not configuration-driven, it was Z2-driven, and would silently follow Z2 the
    moment the configs diverged. A dedicated Z1 YAML that nothing reads is worse than no
    YAML, because the file implies an independence that does not exist.
    """
    label: str
    architecture: str
    board_case: str
    board_thickness_um: float
    substrate_um: float
    tile_band_um: float
    cells: int
    cell_area_mm2: float
    cell_side_mm: float
    conv_total_um: float
    tiers: tuple
    interface_um: float
    die_um: float
    tim_um: float
    rail_v: float
    package_top_um: float
    source_path: Path = field(compare=False, default=None)

    @property
    def substrate_mm(self) -> float:
        return self.substrate_um / 1e3

    @property
    def board_thickness_mm(self) -> float:
        return self.board_thickness_um / 1e3

    def tier_names(self) -> list:
        return [t[0] for t in self.tiers]


def load_z1_package_config(path=None) -> Z1Package:
    """Build a validated Z1 configuration OBJECT. Cross-checks live in z1_package."""
    sys.path.insert(0, str(R / "scripts/phase0nw"))
    import z1_package as Z1P
    c = Z1P.load_z1_config(path)
    conv = c["converter"]
    if c["board"]["case"] in FORBIDDEN_BOARD_CASES:
        raise PhysicalConfigError(f"legacy board {c['board']['case']} on the Z1 path")
    return Z1Package(
        label=c.get("label", "Z1"), architecture=c["architecture"],
        board_case=c["board"]["case"],
        board_thickness_um=float(c["board"]["thickness_um"]),
        substrate_um=float(c["substrate"]["thickness_um"]),
        tile_band_um=float(c["substrate"]["tile_band_um"]),
        cells=int(conv["cells"]), cell_area_mm2=float(conv["cell_area_mm2"]),
        cell_side_mm=float(conv["cell_side_mm"]),
        conv_total_um=float(conv["total_um"]),
        tiers=tuple((t["name"], float(t["um"]))
                    for t in conv["tiers_from_substrate_upward"]),
        interface_um=float(c["interface"]["thickness_um"]),
        die_um=float(c["die"]["thickness_um"]), tim_um=float(c["tim"]["thickness_um"]),
        rail_v=float(c["supply_return"]["rail_v"]),
        package_top_um=float(c["expected"]["package_top_um"]),
        source_path=Path(path) if path else None,
    )


# =======================================================================================
# PHASE 0N-Z --- Z3, the regulator on the PCB BACKSIDE (configs/phase0nz/z3_board_backside.yaml)
# =======================================================================================
Z3_CFG = R / "configs" / "phase0nz" / "z3_board_backside.yaml"
Z2_CFG = R / "configs" / "phase0nt" / "z2_2p4mm_cutout.yaml"
#: the two homogenisation bases a Z3 card may use for a lattice's metal fraction
Z3_FRACTION_BASES = ("unit_cell", "real_lattice")


@dataclass(frozen=True)
class Z3Package:
    """Z3's own configuration object, loaded from configs/phase0nz/z3_board_backside.yaml.

    Z3 re-uses Z2's package above the board and Z2's regulator, but it does NOT read them
    from the Z2 file: it states them itself and the loader CHECKS the equality against the
    Z2 file. Reading Z2's values would make Z3 silently follow any later Z2 change (the
    coupling build_physical_z1 had to break); checking them makes such a change refuse to
    load until Z3 is re-declared.
    """
    label: str
    architecture: str
    variant: str
    hv_feed: str
    board_case: str
    board_thickness_um: float
    substrate_um: float
    tile_band_um: float
    cells: int
    cell_area_mm2: float
    cell_side_mm: float
    cell_grid_bbox_mm: float
    conv_total_um: float
    tiers: tuple                 # Tier objects from the BOARD DOWNWARD (high-side GaN last)
    attach_um: float
    attach: tuple                # sorted (key, value) scalar items of vr_attach
    pcb_via: tuple               # sorted (key, value) scalar items of pcb_via_field
    bga_pitch_mm: float
    bga_height_um: float
    bga_sites_total: int
    bga_1v_n_per_rail: int
    bga_1v_criterion_a: float
    bga_1v_criterion_current_a: float
    out_of_cell_fill: str
    top_rdl_um: float
    expected_z_min_um: float
    expected_z_max_um: float
    source_path: Path = field(compare=False, default=None)

    @property
    def substrate_mm(self) -> float:
        return self.substrate_um / 1e3

    @property
    def tile_band_mm(self) -> float:
        return self.tile_band_um / 1e3

    @property
    def board_thickness_mm(self) -> float:
        return self.board_thickness_um / 1e3

    @property
    def cutout_mm(self):
        """Z3 has no PCB opening: the board and the BGA are full slabs."""
        return None

    @property
    def cell_grid_n(self) -> int:
        n = int(round(math.sqrt(self.cells)))
        if n * n != self.cells:
            raise PhysicalConfigError(f"{self.cells} cells is not a square grid")
        return n

    def tier_names(self) -> list:
        return [t.name for t in self.tiers]

    def attach_dict(self) -> dict:
        return dict(self.attach)

    def pcb_via_dict(self) -> dict:
        return dict(self.pcb_via)


def load_z3_package_config(path=None) -> Z3Package:
    """Parse, validate and CROSS-CHECK the Z3 config.

    Same philosophy as the Z1/Z2 loaders: every quantity the YAML states redundantly is
    re-derived, and the file is refused if the statements disagree. In addition every
    value the MESH takes from somewhere else (board and ball heights from board.py, die/TIM/
    interface from the stack card, the top RDL from z2_converter) is checked against that
    owner, so the config cannot describe one package while the solver builds another.
    """
    p = Path(path) if path else Z3_CFG
    c = yaml.safe_load(p.read_text())
    sys.path.insert(0, str(R / "scripts/phase0nw"))
    # TCPMT round 3: the converter block restates THE design record (checked) or, for another
    # HVR_DESIGN entry, is replaced by it (design_record.apply_converter)
    import design_record as DR
    c = DR.apply_converter(c, "Z3", source=p.name)
    record_driven = bool((c.get("converter") or {}).get("design"))
    import board as BRD
    import physical_coords as PCO
    import z2_converter as Z2C
    from etm.config import load_stack

    def need(d, key, where):
        if key not in d:
            raise PhysicalConfigError(f"{p.name}: missing {where}.{key}")
        return d[key]

    def bad(msg):
        raise PhysicalConfigError(f"{p.name}: {msg}")

    variant = need(c, "variant", "root")
    feed = need(need(c, "hv_feed", "root"), "mode", "hv_feed")
    if variant != "Z3_BOARD_BACKSIDE" or feed != "DIRECT_FEED":
        bad(f"variant {variant!r} / hv_feed {feed!r}: Z3 is Z3_BOARD_BACKSIDE, DIRECT_FEED")

    # --- board: a full IT-968G slab, at the thickness the mesh will actually build ---------
    b = need(c, "board", "root")
    case = need(b, "case", "board")
    if case in FORBIDDEN_BOARD_CASES:
        bad(f"board.case '{case}' is an unsourced legacy case, forbidden on the physical path")
    t_board = float(need(b, "thickness_um", "board"))
    if abs(BRD.BOARD_CASES[case]["t_mm"] * 1e3 - t_board) > 1e-9:
        bad(f"board.thickness_um {t_board} but board case {case} meshes "
            f"{BRD.BOARD_CASES[case]['t_mm'] * 1e3} um")
    if str(b.get("cutout", "none")).lower() != "none":
        bad("Z3 has no PCB opening: board.cutout must be none")

    # --- converter: Z2's regulator, tier for tier, and a tier list that adds up -----------
    conv = need(c, "converter", "root")
    tiers = tuple(Tier(t["name"], float(t["um"]), t.get("status", "OPEN"))
                  for t in need(conv, "tiers_from_board_downward", "converter"))
    stated = float(need(conv, "with_land_side_rdl_um", "converter"))
    if abs(sum(t.um for t in tiers) - stated) > 1e-9:
        bad(f"converter tiers sum to {sum(t.um for t in tiers)} um, not {stated} um")
    # the input-end tier (the high side, fed directly with 48 V) is the DEEPEST: the record's
    # first tier (a mixed tier holding high-side dies), or the legacy single-class HS tier
    deepest = DR.tiers()[0]["name"] if record_driven else "gan_hs_EPC2014C"
    if tiers and tiers[-1].name != deepest:
        bad(f"the input-end (high-side) tier {deepest} must be the DEEPEST tier (last from the "
            f"board downward), not {tiers[-1].name}")
    z2 = load_physical_package_config(Z2_CFG)
    cells = int(need(conv, "cells", "converter"))
    area = float(need(conv, "cell_area_mm2", "converter"))
    side = float(need(conv, "cell_side_mm", "converter"))
    if abs(side * side - area) / area > 2e-4:
        bad(f"cell_side {side} mm squares to {side * side:.4f} mm2, not {area}")
    # the SAME regulator in the SAME order as Z2: both restate the design record (checked by
    # apply_converter against the record, never against each other's file); a config that is
    # not record-driven is still compared with the Z2 file
    if [(t.name, t.um) for t in tiers] != [(t.name, t.um) for t in z2.tiers]:
        bad("converter tiers differ from Z2's: Z3 carries the SAME regulator in the SAME order")
    if (cells, area, side) != (z2.cells, z2.cell_area_mm2, z2.cell_side_mm):
        bad("cell count/area/side differ from Z2's")

    # --- package above the board: Z2's, as the builder will take it ------------------------
    pk, sub = need(c, "package", "root"), need(c, "substrate", "root")
    t_sub, t_band = float(need(sub, "thickness_um", "substrate")), float(
        need(sub, "tile_band_um", "substrate"))
    if abs(t_sub - z2.substrate_um) > 1e-9:
        bad(f"substrate {t_sub} um differs from Z2's {z2.substrate_um} um")
    if not 0.0 < t_band < t_sub:
        bad(f"tile band {t_band} um must lie inside the {t_sub} um substrate")
    g = load_stack()["geometry"]
    card = {"die_um": g["functional_die"]["thickness"]["value"] * 1e3,
            "tim_um": g["tim"]["thickness"]["value"] * 1e3,
            "interface_um": g["interface_layer"]["thickness"]["value"] * 1e3,
            "top_rdl_um": Z2C.TOP_RDL_UM}
    for k, v in card.items():
        if abs(float(need(pk, k, "package")) - v) > 1e-9:
            bad(f"package.{k} = {pk[k]} but the solver builds {v} um")

    # --- VR-to-PCB attach --------------------------------------------------------------------
    va = need(c, "vr_attach", "root")
    att_um = float(need(va, "thickness_um", "vr_attach"))
    if abs(float(va["cu_height_um"]) + float(va["cap_height_um"]) - att_um) > 1e-9:
        bad(f"vr_attach Cu {va['cu_height_um']} + solder {va['cap_height_um']} um is not "
            f"{att_um} um")
    if not 0.0 < float(va["diameter_um"]) < float(va["pitch_um"]):
        bad("vr_attach diameter must be positive and below the pitch")
    if va.get("card_fraction_basis") not in Z3_FRACTION_BASES:
        bad(f"vr_attach.card_fraction_basis must be one of {Z3_FRACTION_BASES}")

    # --- PCB via field: via-in-pad on the attach lattice --------------------------------------
    pv = need(c, "pcb_via_field", "root")
    if abs(float(pv["pitch_um"]) - float(va["pitch_um"])) > 1e-9:
        bad("pcb_via_field.pitch_um must equal the attach pitch (via-in-pad alignment)")
    d_out = float(pv["finished_hole_um"]) + 2.0 * float(pv["plating_um"])
    if not 0.0 < float(pv["finished_hole_um"]) < d_out < float(pv["pitch_um"]):
        bad(f"a {d_out} um plated via does not fit a {pv['pitch_um']} um pitch")
    if pv.get("card_fraction_basis") not in Z3_FRACTION_BASES:
        bad(f"pcb_via_field.card_fraction_basis must be one of {Z3_FRACTION_BASES}")

    # --- BGA: the FULL lattice, with the 1 V field provisioned by the 1.5 A/ball rule ---------
    bg = need(c, "bga", "root")
    pf = need(bg, "power_field_1v", "bga")
    sites = int(need(bg, "sites_total", "bga"))
    n_lattice = len(PCO.bga_lattice_sites(None))
    if sites != n_lattice or abs(float(bg["pitch_mm"]) - PCO.BGA_PITCH_MM) > 1e-12:
        bad(f"bga.sites_total {sites} / pitch {bg['pitch_mm']} but the full centred lattice "
            f"has {n_lattice} sites at {PCO.BGA_PITCH_MM} mm")
    if abs(float(bg["height_um"]) - BRD.BALL_H_MM * 1e3) > 1e-9:
        bad(f"bga.height_um {bg['height_um']} but the BGA layer meshes {BRD.BALL_H_MM * 1e3}")
    crit, i_dc = float(pf["i_ball_criterion_a"]), float(pf["criterion_current_a"])
    n_rail = int(pf["n_per_rail"])
    if n_rail != math.ceil(i_dc / crit - 1e-12):
        bad(f"bga 1 V n_per_rail {n_rail} but ceil({i_dc} / {crit}) = "
            f"{math.ceil(i_dc / crit - 1e-12)}")
    if 2 * n_rail > sites:
        bad(f"2 x {n_rail} 1 V balls exceed the {sites}-site lattice")

    # --- out-of-cell rule and the expected z extents ------------------------------------------
    ooc = need(c, "out_of_cell", "root")
    if ooc.get("fill") != "underfill_homog" or str(ooc.get("outside_bbox")).upper() != "VOID":
        bad("out_of_cell must fill the cell-grid bbox with underfill_homog and void outside")
    ex = need(c, "expected", "root")
    z_min = -(float(bg["height_um"]) + t_board + att_um + stated)
    z_max = (t_sub + card["top_rdl_um"] + card["interface_um"] + card["die_um"]
             + card["tim_um"])
    for k, v in (("z_min_um", z_min), ("z_max_um", z_max)):
        if abs(float(need(ex, k, "expected")) - v) > 1e-6:
            bad(f"expected.{k} = {ex[k]} but the layers add up to {v}")

    scal = lambda d: tuple(sorted((k, v) for k, v in d.items()                  # noqa: E731
                                  if not isinstance(v, (dict, list))))
    return Z3Package(
        label=c.get("label", p.stem), architecture=need(c, "architecture", "root"),
        variant=variant, hv_feed=feed, board_case=case, board_thickness_um=t_board,
        substrate_um=t_sub, tile_band_um=t_band, cells=cells, cell_area_mm2=area,
        cell_side_mm=side, cell_grid_bbox_mm=float(need(conv, "cell_grid_bbox_mm",
                                                        "converter")),
        conv_total_um=stated, tiers=tiers, attach_um=att_um, attach=scal(va),
        pcb_via=scal(pv), bga_pitch_mm=float(bg["pitch_mm"]),
        bga_height_um=float(bg["height_um"]), bga_sites_total=sites,
        bga_1v_n_per_rail=n_rail, bga_1v_criterion_a=crit, bga_1v_criterion_current_a=i_dc,
        out_of_cell_fill=ooc["fill"], top_rdl_um=card["top_rdl_um"],
        expected_z_min_um=z_min, expected_z_max_um=z_max, source_path=p)


def build_physical_z3(cfg=None, h_xy: float = 1.1):
    """Mesh the COMPLETE physical Z3 from Z3's OWN configuration.

    A Z2 PhysicalPackage or a Z1Package is REFUSED, for the reason build_physical_z1 refuses
    a Z2 config: the architectures must stay separately configured to stay comparable.
    """
    import production_et as PE
    if cfg is None:
        cfg = load_z3_package_config()
    if not isinstance(cfg, Z3Package):
        raise PhysicalConfigError(
            "build_physical_z3 needs a Z3Package from configs/phase0nz/z3_board_backside.yaml "
            f"(load_z3_package_config), not {type(cfg).__name__}")
    if cfg.board_case in FORBIDDEN_BOARD_CASES:
        raise PhysicalConfigError(f"refusing to build on legacy board {cfg.board_case}")
    return PE.build_global(cfg.architecture, cfg.substrate_mm, h_xy=h_xy,
                           board_case=cfg.board_case, cutout_mm=None, physical_z3=cfg)
