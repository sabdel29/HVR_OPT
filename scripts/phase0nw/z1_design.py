"""TCPMT REVISION --- the converter design a Z1 evaluation runs with.

The production chain was written around one regulator: the 49-cell N3K3K_A2 design of
kw1.design_1kw(). Its count, topology and cell geometry reached the chain through constants
in several modules (final_closure_ledger.N_VR, routing.DESIGN, production_et.N_VR /
HVR_AREA_MM2, replay_production.N_VR, final_closure_physical_etm.TSV_N_PER_CELL, the Z1
layer map, the package 48 V network file). This module is the ONE place a different design
enters, so a count-optimal candidate can be carried through the complete Z1 chain.

SELECTION. explicit path > environment variable HVR_Z1_CONFIG > the production config
(configs/phase0nx/z1_physical.yaml). A non-default config must declare a `design:` block;
the design is COMPILED here (kw1.design_1kw at the declared count and topology) and refused
unless it reproduces every declared part, f_sw, area and 25 C conversion loss.

THE DEFAULT PATH DOES NOT CHANGE. On the production config every consumer keeps its own
production constant (they test is_default() and only then read the derived values), so the
49-cell results stay byte-identical; research/tcpmt_revision/countopt/fingerprint_49.py
proves it (mesh, materials, ledgers, deposits, thermal and structural decks).

SCOPE. A non-default design applies to Z1 only: Z2/Z3 carry the production regulator in
their own configs, and require_z1() refuses them in a process whose Z1 design is not the
production one, so no other architecture can silently pick up the candidate's constants.
"""
from __future__ import annotations

import math
import os
import sys
from functools import lru_cache
from pathlib import Path

R = Path(__file__).resolve().parents[2]
ENV = "HVR_Z1_CONFIG"
DEFAULT_CFG = R / "configs" / "phase0nx" / "z1_physical.yaml"
DEFAULT_PACKAGE_NETWORK = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "final_closure" / "package_network.json"
#: the production regulator count (final_closure_ledger.N_VR, production_et.N_VR)
PRODUCTION_N_VR = 49
P_LOAD_W, V_IN, V_OUT = 1000.0, 48.0, 1.0


class DesignError(ValueError):
    """A non-default Z1 config is inconsistent with the design it declares."""


def config_path(path=None) -> Path:
    """The Z1 config in force. Relative paths resolve against the repository root."""
    p = Path(path if path is not None else (os.environ.get(ENV) or DEFAULT_CFG))
    return p if p.is_absolute() else R / p


def is_default(path=None) -> bool:
    return config_path(path).resolve() == DEFAULT_CFG.resolve()


@lru_cache(maxsize=None)
def _yaml(p: str) -> dict:
    import yaml
    return yaml.safe_load(Path(p).read_text())


def raw(path=None) -> dict:
    return _yaml(str(config_path(path).resolve()))


def declared(path=None):
    """The `design:` block of a non-default config, cross-checked against its converter
    block; None on the production config."""
    if is_default(path):
        return None
    c = raw(path)
    d = c.get("design")
    if not d:
        raise DesignError(f"{config_path(path)} is not the production Z1 config and declares "
                          f"no design: block")
    conv = c["converter"]
    if int(d["n_vr"]) != int(conv["cells"]):
        raise DesignError(f"design.n_vr {d['n_vr']} != converter.cells {conv['cells']}")
    # the physical cell is the synthesized footprint, or larger but never beyond the DSE's
    # area budget I_vr / J_t (a cell enlarged so that two component classes share a tier)
    a_syn, a_cell = float(d["area_mm2"]), float(conv["cell_area_mm2"])
    budget = P_LOAD_W / V_OUT / int(d["n_vr"]) / float(d["j_target_A_mm2"])
    if not (a_syn - 1e-9 <= a_cell <= budget + 1e-9):
        raise DesignError(f"converter.cell_area_mm2 {a_cell} must lie between the synthesized "
                          f"{a_syn} mm2 and the {budget:.4f} mm2 area budget")
    n = int(round(math.sqrt(int(d["n_vr"]))))
    if n * n != int(d["n_vr"]):
        raise DesignError(f"{d['n_vr']} cells is not a square grid (the package builder "
                          f"meshes square grids only)")
    return d


def n_vr(path=None) -> int:
    d = declared(path)
    return PRODUCTION_N_VR if d is None else int(d["n_vr"])


def tag(path=None) -> str:
    d = declared(path)
    return "" if d is None else str(d["tag"])


def topology(path=None):
    """(N, K, K_A) of a non-default design; None on the production config."""
    d = declared(path)
    if d is None:
        return None
    t = d["topology"]
    return int(t["N"]), int(t["K"]), int(t["K_A"])


def buck_duty(path=None) -> float:
    """D = V_out N / V_in, the converter model's buck duty (VRArchitecture.D)."""
    return (V_OUT * topology(path)[0]) / V_IN


def cell_area_mm2(path=None) -> float:
    return float(raw(path)["converter"]["cell_area_mm2"])


def cell_side_mm(path=None) -> float:
    """The FE / routing tile side of a non-default design: sqrt of the synthesized area
    (the production tile is sqrt(274.89 / 49), kept by its consumers)."""
    return math.sqrt(cell_area_mm2(path))


def results_dir(path=None):
    if is_default(path):
        return None
    return _results_path(raw(path)["results"]["dir"])


def package_network_file(path=None) -> Path:
    if is_default(path):
        return DEFAULT_PACKAGE_NETWORK
    return _results_path(raw(path)["package_network"]["file"])


def _results_path(rel: str) -> Path:
    """A config's research/... result path; under $ETM_RESULTS_ROOT for a campaign (hook)."""
    root = os.environ.get("ETM_RESULTS_ROOT")
    if root and Path(rel).parts[:1] == ("research",):
        return Path(root).joinpath(*Path(rel).parts[1:])
    return R / rel


def require_z1(arch: str, what: str = "") -> None:
    """Refuse a non-Z1 architecture in a process whose Z1 design is not the production one."""
    if arch != "Z1" and not is_default():
        raise RuntimeError(
            f"{what or 'this step'} for {arch}: {ENV}={os.environ.get(ENV)} selects a "
            f"non-production Z1 design ({tag()}); Z2/Z3 carry the production regulator and "
            f"must run in a process without {ENV}")


# --------------------------------------------------------------------------- the converter
@lru_cache(maxsize=None)
def _compiled(p: str):
    for _p in ("scripts/phase0f", "scripts/phase0d", "scripts/phase0dr", "scripts/phase0e",
               "scripts/phase0b"):
        if str(R / _p) not in sys.path:
            sys.path.insert(0, str(R / _p))
    import kw1
    d = declared(p)
    des, _g, why = kw1.design_1kw(m_vr=int(d["n_vr"]), j=float(d["j_target_A_mm2"]),
                                  topology=topology(p))
    if des is None:
        raise DesignError(f"kw1 compiles no {d['topology']} design at M = {d['n_vr']}: {why}")
    a = des.arch
    got = {"topology": (a.N, a.K, a.K_A), "hs_part": des.hs.part_number,
           "ls_part": des.ls.part_number, "inductor": des.inductor.name,
           "capacitor": des.capacitor.name}
    want = {"topology": topology(p), "hs_part": d["hs_part"], "ls_part": d["ls_part"],
            "inductor": d["inductor"], "capacitor": d["capacitor"]}
    bad = {k: (got[k], want[k]) for k in got if got[k] != want[k]}
    if abs(float(des.f_sw_hz) - float(d["f_sw_hz"])) > 1e-6 * float(d["f_sw_hz"]):
        bad["f_sw_hz"] = (float(des.f_sw_hz), float(d["f_sw_hz"]))
    if abs(float(des.area_mm2) - float(d["area_mm2"])) > 1e-9:
        bad["area_mm2"] = (float(des.area_mm2), float(d["area_mm2"]))
    conv = float(des.loss_25c_w) * int(d["n_vr"])
    if abs(conv - float(d["conversion_25C_W"])) > 1e-9 * conv:
        bad["conversion_25C_W"] = (conv, float(d["conversion_25C_W"]))
    if bad:
        raise DesignError(f"the compiled design does not reproduce {config_path(p).name}: {bad}")
    return des


def compiled(path=None):
    """The compiled HVRDesign of a non-default config (the production design is compiled by
    replay_production.compiled_design, unchanged)."""
    if is_default(path):
        raise DesignError("the production design is compiled by its own callers")
    return _compiled(str(config_path(path).resolve()))


# --------------------------------------------------------------------------- design point
# TCPMT review round 2: the regulator count and topology of the converter a run uses come from
# the Z1 config in force -- the production config's converter block, or a candidate's design:
# block -- never from a literal, so the campaign can run the 49-cell point or another one (e.g.
# M = 36, N4K4K_A2) by pointing HVR_Z1_CONFIG at that design's config.
def design_point(path=None) -> dict:
    """{'n_vr', 'topology' (None = the synthesis's free pick, the production behaviour), 'tag',
    'production', 'config'} of the design in force."""
    p = config_path(path)
    if is_default(path):
        return {"n_vr": int(raw(path)["converter"]["cells"]), "topology": None, "tag": "",
                "production": True, "config": str(p)}
    d = declared(path)
    return {"n_vr": int(d["n_vr"]), "topology": topology(path), "tag": str(d["tag"]),
            "production": False, "config": str(p)}


def routing_design(base: dict, path=None) -> dict:
    """routing.DESIGN for the design in force: `base` itself on the production config, else
    rebuilt from the compiled design by the rule that produced the production dict
    (p_conv_total_w = loss_at(85 C) x n_vr, tile side = sqrt(synthesized area))."""
    if is_default(path):
        return base
    return _routing_design(str(config_path(path).resolve()), tuple(sorted(base.items())))


@lru_cache(maxsize=None)
def _routing_design(p: str, base_items: tuple) -> dict:
    return design_dict(compiled(p), n_vr(p), dict(base_items), tile_side_mm=cell_side_mm(p))


def design_dict(des, n: int, base: dict, tile_side_mm: float | None = None) -> dict:
    """The routing.DESIGN fields of a compiled HVRDesign at n regulators. Applied to the
    production design (kw1.design_1kw(), n = 49) it reproduces routing.DESIGN (tested).
    The tile is the physical cell (default: the synthesized footprint, sqrt(area))."""
    a = des.arch
    out = dict(base)
    tile = math.sqrt(des.area_mm2) if tile_side_mm is None else float(tile_side_mm)
    out.update(label=des.label, N=a.N, K=a.K, K_A=a.K_A, f_sw_hz=float(des.f_sw_hz),
               i_out_per_vr_a=P_LOAD_W / V_OUT / n, v_in=float(des.v_in),
               v_out=float(des.v_out), n_vr=n, tile_side_mm=tile,
               p_conv_total_w=float(des.loss_at(85.0)["p_conv_w"]) * n,
               hs_part=des.hs.part_number, hs_footprint_mm2=float(des.hs.footprint_mm2),
               hs_rdson_ohm=float(des.hs.R_DS_ON), ind_l_nh=des.inductor.l_nh,
               ind_dcr_mohm=des.inductor.r_dcr_mohm,
               ind_footprint_mm2=float(des.inductor.footprint_mm2),
               ind_h_um=des.inductor.height_um, cap_uf=des.capacitor.c_uf,
               cap_esr_mohm=des.capacitor.esr_mohm, cap_esl_ph=float(des.capacitor.esl_ph),
               cap_footprint_mm2=float(des.capacitor.footprint_mm2))
    return out


# --------------------------------------------------------------------------- geometry
def tsv_n_per_cell(path=None) -> int:
    """The production TSV rule (30 um / 60 um checkerboard at maximum density,
    tsv_fields._lattice) on the cell side of the design in force."""
    if str(R / "scripts/phase0nw") not in sys.path:
        sys.path.insert(0, str(R / "scripts/phase0nw"))
    import tsv_fields as TF
    side = (float(raw(path)["converter"]["cell_side_mm"]) if is_default(path)
            else cell_side_mm(path))
    return TF._lattice(side, TF.P_TSV_MM)[0] ** 2


#: component class of a Z1 tier name -> the final_closure_ledger.LAYERS key
_LAYER_KEY = (("gan_hs", "hs"), ("gan_ls", "ls"), ("flying_caps", "caps"),
              ("inductor", "ind"), ("output_caps", "cout"))


def z1_layers(path=None) -> dict:
    """final_closure_ledger.LAYERS['Z1'] derived from the config's tier list (layer names are
    z1conv_<index>_<tier name>, z1_package.mid_layers). On the production config this
    reproduces the ledger's literal map exactly (tests/phase0nz/test_count_generalization)."""
    tiers = raw(path)["converter"]["tiers_from_substrate_upward"]
    names = [f"z1conv_{i}_{t['name']}" for i, t in enumerate(tiers)]
    lay = {}
    for prefix, key in _LAYER_KEY:
        hits = [n for n, t in zip(names, tiers) if t["name"].startswith(prefix)]
        if key == "cout" and not hits:
            continue
        if len(hits) != 1:
            raise DesignError(f"{config_path(path).name}: {len(hits)} tiers named {prefix}*")
        lay[key] = hits[0]
    if not tiers[-1]["name"] == "output_rdl":
        raise DesignError("the last Z1 tier must be the output RDL")
    out = {k: lay[k] for k in ("hs", "ls", "caps", "ind")}
    out["rdl"] = [n for n, t in zip(names, tiers) if t["name"].endswith("_rdl")]
    out.update({"lv": names[-1], "tsv": "sub_lower", "pads": "interface", "bga": "bga",
                "pkg_hv": "bga", "die": "die"})
    if "cout" in lay:
        out["cout"] = lay["cout"]
    return out


def cell_coordinates(path=None) -> list:
    """The Z1 cell centres FROM THE FE PLACEMENT GENERATOR, as physical_coords does for Z2."""
    if str(R / "scripts/phase0nw") not in sys.path:
        sys.path.insert(0, str(R / "scripts/phase0nw"))
    import physical_package as PP
    _m, _mats, _st, tiles = PP.build_physical_z1(
        cfg=PP.load_z1_package_config(config_path(path)))
    return [(float(t.cx), float(t.cy)) for t in tiles]


def summary(path=None) -> dict:
    """What a case file records about the design it was computed with."""
    if is_default(path):
        return {"config": str(DEFAULT_CFG.relative_to(R)), "tag": "", "n_vr": PRODUCTION_N_VR,
                "production": True}
    des = compiled(path)
    d = declared(path)
    rd = routing_design({}, path)
    p = config_path(path)
    return {"config": str(p.relative_to(R)) if p.is_relative_to(R) else str(p),
            "tag": tag(path), "production": False, "n_vr": n_vr(path),
            "topology": d["topology"], "label": des.label,
            "hs_part": des.hs.part_number, "ls_part": des.ls.part_number,
            "inductor": des.inductor.name, "capacitor": des.capacitor.name,
            "f_sw_hz": float(des.f_sw_hz), "cell_area_mm2": cell_area_mm2(path),
            "synthesized_area_mm2": float(des.area_mm2),
            "cell_side_mm": cell_side_mm(path), "conversion_25C_W": float(des.loss_25c_w)
            * n_vr(path), "p_conv_85C_legacy_alpha_W": rd["p_conv_total_w"],
            "tsv_per_cell": tsv_n_per_cell(path),
            "tiers": [(t["name"], float(t["um"])) for t in
                      raw(path)["converter"]["tiers_from_substrate_upward"]],
            "package_network": str(package_network_file(path).relative_to(R))}
