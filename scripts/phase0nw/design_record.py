"""TCPMT round 3 --- THE design record: regulator count, converter design and stack, one place.

Every count- or design-dependent number of the electrothermal-mechanical chain (Z1, Z2 and Z3
alike) comes from configs/design_points.yaml through this module: the regulator count M, the
synthesized converter (topology, parts, f_sw), the cell (area budget I_cell / J_t, side), the
mixed converter tiers (contents, heights, placement, ORDER) and the screen it was picked by.
Nothing downstream may restate them as literals (the 49-cell constants the chain carried --
N_VR = 49, routing.DESIGN, 5.61 mm2, 1444 TSVs, the S1 duty 1/16, gan_hs_EPC2014C layer
names -- are derived from here).

SELECTION. explicit key > environment variable HVR_DESIGN > the record's `production` key.
The production design is the authors' decided point (round-3 worklog, 2026-11-19): M = 36,
N3K3K_A2, EPC2014C / EPC2055, 805 kHz, rated Murata 0603 flying capacitors, four mixed tiers.
The other entries are the co-design comparison (5 tiers), the thin-capacitor sensitivity and
the count neighbours M = 25 and 49.

VERIFICATION. compiled() re-synthesizes the design with kw1.design_1kw under the production
converter rules (electrical.production_rules, packing ON) plus the entry's own overrides and
refuses unless it reproduces every recorded part, f_sw, area and 25-C conversion loss; the
recorded tier contents are checked against the engine's stack plan by the generator
(scripts/tcpmt_design_record.py) and by the tests.

TIER ORDER. `tiers` are listed from the converter's INPUT end (48 V, the high-side end) to its
OUTPUT end (1 V, the side facing the die): Z1 stacks them upward from the bottom substrate,
Z2/Z3 hang them downward from the substrate/board with the output end against the attach.
The order is the production order of the tier-order analysis (scripts/tcpmt_tier_order.py).
"""
from __future__ import annotations

import copy
import math
import os
import sys
from functools import lru_cache
from pathlib import Path

R = Path(__file__).resolve().parents[2]
RECORD = R / "configs" / "design_points.yaml"
ENV = "HVR_DESIGN"
P_LOAD_W, V_IN, V_OUT = 1000.0, 48.0, 1.0
#: component classes of a converter cell, in the order the record lists a tier's contents
CLASSES = ("gan_hs", "gan_ls", "inductor", "cap_fly")
ABBR = {"gan_hs": "hs", "gan_ls": "ls", "inductor": "l", "cap_fly": "cf"}
#: interlayer RDL between two converter tiers, and the landing RDLs (um)
RDL_UM = 10.0
#: the TSV fabric's reference point for the current-scaled count: the 49-cell field of
#: 38 x 38 = 1444 vias carried 1000/49 A per cell; the count scales with the cell current at
#: the same current per via (TCPMT round 3), never beyond the geometric maximum of the cell
TSV_REF_SIDE, TSV_REF_I_CELL_A = 38, 1000.0 / 49.0


class DesignRecordError(ValueError):
    """The design record is missing, inconsistent, or does not reproduce its synthesis."""


# --------------------------------------------------------------------------- the record
@lru_cache(maxsize=4)
def _load(path: str) -> dict:
    import yaml
    p = Path(path)
    if not p.is_file():
        raise DesignRecordError(f"no design record at {p}")
    rec = yaml.safe_load(p.read_text())
    if rec.get("production") not in rec.get("designs", {}):
        raise DesignRecordError(f"{p.name}: production design {rec.get('production')!r} is not "
                                f"in designs")
    return rec


def record(path=None) -> dict:
    return _load(str(Path(path or RECORD).resolve()))


def name(key=None) -> str:
    """The key of the design in force."""
    rec = record()
    k = key or os.environ.get(ENV) or rec["production"]
    if k not in rec["designs"]:
        raise DesignRecordError(f"{ENV}={k!r}: not a design of {RECORD.name} "
                                f"({sorted(rec['designs'])})")
    return k


def production_key() -> str:
    return record()["production"]


def is_production(key=None) -> bool:
    return name(key) == production_key()


def get(key=None) -> dict:
    """A copy of the record entry of the design in force."""
    return copy.deepcopy(record()["designs"][name(key)])


def keys() -> list:
    return list(record()["designs"])


# --------------------------------------------------------------------------- scalars
def n_vr(key=None) -> int:
    return int(get(key)["n_vr"])


def tag(key=None) -> str:
    return str(get(key)["tag"])


def topology(key=None) -> tuple:
    t = get(key)["topology"]
    return int(t["N"]), int(t["K"]), int(t["K_A"])


def j_target(key=None) -> float:
    return float(get(key)["j_target_A_mm2"])


def i_cell_a(key=None) -> float:
    """DC output current of one cell."""
    return P_LOAD_W / V_OUT / n_vr(key)


def cell_area_mm2(key=None) -> float:
    return float(get(key)["cell_area_mm2"])


def cell_side_mm(key=None) -> float:
    return float(get(key)["cell_side_mm"])


def grid_n(key=None) -> int:
    n = int(round(math.sqrt(n_vr(key))))
    if n * n != n_vr(key):
        raise DesignRecordError(f"{n_vr(key)} cells is not a square grid")
    return n


def buck_duty(key=None) -> float:
    """D = N V_out / V_in, the converter model's buck duty (VRArchitecture.D)."""
    return topology(key)[0] * V_OUT / V_IN


def part_counts(key=None) -> dict:
    """Parts of one cell per class: N high-side, K low-side, K inductors, N-1 flying caps."""
    N, K, _ = topology(key)
    return {"gan_hs": N, "gan_ls": K, "inductor": K, "cap_fly": N - 1}


def rule_overrides(key=None) -> dict:
    """The entry's own converter-rule overrides on top of the production rules."""
    return dict(get(key).get("rules") or {})


def rules(key=None) -> dict:
    """Engine rules of the design: the production rules of this process with the entry's
    overrides (e.g. MAX_TIERS 5 for the co-design comparison)."""
    _paths()
    import electrical as EL
    return {**EL.LEGACY_RULES, **EL.production_rules(), **rule_overrides(key)}


# --------------------------------------------------------------------------- tiers
def tiers(key=None) -> list:
    """[{'name', 'height_um', 'parts': {class: n}, 'placement_mm'}] from the input end to the
    output end (the production order)."""
    t = get(key)["tiers"]
    counts = {c: 0 for c in CLASSES}
    for x in t:
        for c, n in x["parts"].items():
            if c not in CLASSES:
                raise DesignRecordError(f"tier {x['name']}: unknown class {c}")
            counts[c] += int(n)
    if counts != part_counts(key):
        raise DesignRecordError(f"{name(key)}: tiers hold {counts}, the topology needs "
                                f"{part_counts(key)}")
    return t


def tier_name(index: int, parts: dict) -> str:
    """tier<i>_<contents>, e.g. tier1_hs2cf2 (i counts from the input end)."""
    return f"tier{index}_" + "".join(f"{ABBR[c]}{int(parts[c])}" for c in CLASSES
                                     if parts.get(c))


def tier_parts(key=None) -> dict:
    """tier name -> {class: n}."""
    return {t["name"]: dict(t["parts"]) for t in tiers(key)}


def converter_stack_um(key=None) -> float:
    """Tiers plus the interlayer RDLs between them (the DSE stack height)."""
    t = tiers(key)
    return sum(float(x["height_um"]) for x in t) + (len(t) - 1) * RDL_UM


def converter_tiers(arch: str, key=None) -> list:
    """The converter tier list an integration's config states, [(name, um)]:

      Z1   from the bottom substrate UPWARD: landing RDL, tiers (input end first) separated
           by interlayer RDLs, output RDL (towards the die)
      Z2   from the substrate DOWNWARD: land-side attach RDL, tiers (output end first),
           interlayer RDLs; the input end is deepest
      Z3   from the board DOWNWARD: as Z2
    """
    t = [(x["name"], float(x["height_um"])) for x in tiers(key)]
    if arch == "Z1":
        out = [("bottom_substrate_rdl", RDL_UM)]
        for i, x in enumerate(t):
            if i:
                out.append(("interlayer_rdl", RDL_UM))
            out.append(x)
        out.append(("output_rdl", RDL_UM))
        return out
    if arch in ("Z2", "Z2BF", "Z3"):
        out = [("land_side_attach_rdl", RDL_UM)]
        for i, x in enumerate(reversed(t)):
            if i:
                out.append(("interlayer_rdl", RDL_UM))
            out.append(x)
        return out
    raise DesignRecordError(f"no converter tier convention for {arch}")


def tier_classes(tier_name_: str, key=None) -> dict:
    """{class: n} of one converter tier name (a tier of the record), {} for an RDL."""
    return dict(tier_parts(key).get(tier_name_, {}))


#: the tier-list key of each integration's config
TIER_KEY = {"Z1": "tiers_from_substrate_upward", "Z2": "tiers_from_substrate_downward",
            "Z3": "tiers_from_board_downward"}


def apply_converter(c: dict, arch: str, key=None, source: str = "") -> dict:
    """Bring an integration config's converter block (parsed YAML `c`) in line with the design
    record. A config that restates a record entry declares it (converter.design):

      the design in force IS that entry   every restated value (cells, cell area and side, the
                                          tier list) must equal the record's; a difference is
                                          refused (the config cannot drift from the record)
      another entry (HVR_DESIGN)          the converter block is REPLACED by the record's and
                                          the totals and expected extents the loaders check
                                          are shifted by the change of converter height

    A config without converter.design (a count-study candidate) is returned unchanged."""
    conv = c.get("converter") or {}
    declared = conv.get("design")
    if not declared:
        return c
    k = name(key)
    tk = TIER_KEY["Z2" if arch == "Z2BF" else arch]
    want = [(n, float(um)) for n, um in converter_tiers(arch, k)]
    have = [(t["name"], float(t["um"])) for t in conv.get(tk, [])]
    scal = {"cells": n_vr(k), "cell_area_mm2": cell_area_mm2(k), "cell_side_mm": cell_side_mm(k)}
    if declared == k:
        bad = {kk: (conv.get(kk), v) for kk, v in scal.items()
               if conv.get(kk) is None or abs(float(conv[kk]) - float(v)) > 1e-9 * max(1.0, v)}
        if have != want:
            bad["tiers"] = (have, want)
        if bad:
            raise DesignRecordError(f"{source or arch}: the converter block restating design "
                                    f"{k} differs from the record: {bad}")
        return c
    old_tot, new_tot = sum(u for _n, u in have), sum(u for _n, u in want)
    d = new_tot - old_tot
    conv = dict(conv)
    conv[tk] = [{"name": n, "um": u, "status": "SOURCE_BACKED" if n.endswith("_rdl")
                 else "DESIGN_CHOICE"} for n, u in want]
    conv.update(scal)
    conv["design"] = k
    if arch == "Z1":
        conv["total_um"] = new_tot
        ex = dict(c.get("expected") or {})
        if "package_top_um" in ex:
            ex["package_top_um"] = float(ex["package_top_um"]) + d
        if "converter_span_um" in ex:
            ex["converter_span_um"] = [ex["converter_span_um"][0],
                                       float(ex["converter_span_um"][1]) + d]
        c = dict(c, expected=ex)
    else:
        conv["with_land_side_rdl_um"] = new_tot
        if "four_tier_um" in conv:
            conv["four_tier_um"] = new_tot - RDL_UM
        if arch == "Z3":
            ex = dict(c.get("expected") or {})
            if "z_min_um" in ex:
                ex["z_min_um"] = float(ex["z_min_um"]) - d
            if "converter_span_um" in ex:
                ex["converter_span_um"] = [float(ex["converter_span_um"][0]) - d,
                                           ex["converter_span_um"][1]]
            c = dict(c, expected=ex)
    return dict(c, converter=conv)


# --------------------------------------------------------------------------- converter
def _paths():
    for p in ("scripts/phase0f", "scripts/phase0d", "scripts/phase0dr", "scripts/phase0e",
              "scripts/phase0b", "scripts/phase0nw", "scripts/phase0mr", "scripts"):
        if str(R / p) not in sys.path:
            sys.path.insert(0, str(R / p))


_COMPILED: dict = {}


def compiled(key=None):
    """The converter of the design, re-synthesized (kw1.design_1kw at the recorded count,
    current density and topology) under rules(key) and checked against the record. Cached by
    (design, rules)."""
    k = name(key)
    rl = rules(k)
    sig = (k, tuple(sorted(rl.items())))
    if sig not in _COMPILED:
        _paths()
        import kw1
        import electrical as EL
        d = get(k)
        with EL.pinned_rules(rl):
            des, _g, why = kw1.design_1kw(m_vr=int(d["n_vr"]), j=float(d["j_target_A_mm2"]),
                                          topology=topology(k))
        if des is None:
            raise DesignRecordError(f"{k}: kw1 compiles no {d['topology']} design at "
                                    f"M = {d['n_vr']}: {why}")
        check(k, des)
        _COMPILED[sig] = des
    return _COMPILED[sig]


def check(key, des) -> None:
    """Refuse a compiled design that does not reproduce the record entry."""
    d = get(key)
    a = des.arch
    got = {"topology": (a.N, a.K, a.K_A), "hs_part": des.hs.part_number,
           "ls_part": des.ls.part_number, "inductor": des.inductor.name,
           "capacitor": des.capacitor.name}
    want = {"topology": topology(key), "hs_part": d["hs_part"], "ls_part": d["ls_part"],
            "inductor": d["inductor"], "capacitor": d["capacitor"]}
    bad = {kk: (got[kk], want[kk]) for kk in got if got[kk] != want[kk]}
    if abs(float(des.f_sw_hz) - float(d["f_sw_hz"])) > 1e-6 * float(d["f_sw_hz"]):
        bad["f_sw_hz"] = (float(des.f_sw_hz), float(d["f_sw_hz"]))
    if abs(float(des.area_mm2) - float(d["synthesized_area_mm2"])) > 1e-9:
        bad["synthesized_area_mm2"] = (float(des.area_mm2), float(d["synthesized_area_mm2"]))
    conv = float(des.loss_25c_w) * int(d["n_vr"])
    if abs(conv - float(d["conversion_25C_W"])) > 1e-7 * conv:
        bad["conversion_25C_W"] = (conv, float(d["conversion_25C_W"]))
    if bad:
        raise DesignRecordError(f"the compiled design does not reproduce {key}: {bad}")


def design_identity(key=None) -> dict:
    d = get(key)
    return {"design": name(key), "tag": d["tag"], "n_vr": int(d["n_vr"]),
            "topology": list(topology(key)), "hs": d["hs_part"], "ls": d["ls_part"],
            "inductor": d["inductor"], "capacitor": d["capacitor"],
            "f_sw_hz": float(d["f_sw_hz"]), "cell_side_mm": cell_side_mm(key),
            "tiers": [t["name"] for t in tiers(key)]}


# --------------------------------------------------------------------------- geometry
def tsv_n_side(key=None, cell_side=None, i_cell=None) -> int:
    """Side of the 30-um / 60-um checkerboard TSV lattice of one cell, scaled with the cell
    current at the 49-cell field's current per via (38 x 38 at 1000/49 A), capped at the
    cell's geometric maximum (tsv_fields._lattice). `cell_side` / `i_cell` give another cell
    (a count-study candidate) the same rule."""
    _paths()
    import tsv_fields as TF
    side = float(cell_side if cell_side is not None else cell_side_mm(key))
    i = float(i_cell if i_cell is not None else i_cell_a(key))
    n_max = TF._lattice(side, TF.P_TSV_MM)[0]
    n = int(math.ceil(TSV_REF_SIDE * math.sqrt(i / TSV_REF_I_CELL_A) - 1e-9))
    return min(n_max, max(2, n))


def tsv_n_per_cell(key=None) -> int:
    return tsv_n_side(key) ** 2


def pkg_cutout_mm(clearance_mm: float = 1.0) -> float:
    """The PCB opening of a backside converter: the cell-grid bbox (die minus the edge
    keep-out, independent of the count for the uniform placement) + 2 x the clearance."""
    return grid_bbox_mm() + 2.0 * clearance_mm


def grid_bbox_mm() -> float:
    """The uniform placement's cell-grid bbox: die (22.36 mm) minus 2 x the edge keep-out
    (placement0f.square_lattice; the same for every count)."""
    _paths()
    from etm.config import load_doe, load_stack
    die = load_stack()["geometry"]["functional_die"]["size_x"]["value"]
    ko = load_doe()["placement_rules"]["edge_keepout_mm"]["value"]
    return die - 2.0 * ko


def cell_centres(key=None) -> list:
    """Cell centres of the uniform placement (the FE tiles), [(x, y)] mm."""
    _paths()
    import kw1
    from etm.config import load_doe, load_stack
    return [tuple(map(float, xy)) for xy in
            kw1.tiles_for("uniform", cell_side_mm(key), load_stack(), load_doe(), n_vr(key))]


def summary(key=None) -> dict:
    d = get(key)
    return {"design": name(key), "production": is_production(key), "tag": d["tag"],
            "label": d.get("label", ""), "n_vr": int(d["n_vr"]),
            "topology": dict(d["topology"]), "hs_part": d["hs_part"], "ls_part": d["ls_part"],
            "inductor": d["inductor"], "capacitor": d["capacitor"],
            "f_sw_hz": float(d["f_sw_hz"]), "cell_area_mm2": cell_area_mm2(key),
            "cell_side_mm": cell_side_mm(key), "conversion_25C_W": float(d["conversion_25C_W"]),
            "tiers": [(t["name"], float(t["height_um"])) for t in tiers(key)],
            "converter_stack_um": converter_stack_um(key), "record": str(RECORD.relative_to(R))}
