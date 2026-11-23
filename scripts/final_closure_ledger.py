"""FINAL CLOSURE --- the physical electrical ledger, one owner per conductor.

Every conductor in the Z1/Z2 power path appears exactly once, with its geometry,
current type, scenario, resistance model, resistance at its own temperature, loss,
the FE tier its heat is deposited in, and its evidence class. Nothing is silently
zero: a term the production geometry does not contain is recorded as
STRUCTURALLY_ABSENT with the reason and the alternative quantified.

The 48 V side is SCENARIO-CONDITIONED (HV-S0/S1/S2 are named scenarios, never a
bracket). The 48 V average current is SELF-CONSISTENT: it is the current that
carries the load plus the losses this ledger itself computes, iterated to a fixed
point, because the package losses depend on the very current they help set.
"""
from __future__ import annotations

import json
import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
for _p in ("scripts/phase0nw", "scripts/phase0m", "scripts/phase0mr", "scripts/phase0e",
           "scripts/phase0dr", "scripts/phase0i", "scripts/phase0g", "scripts/phase0b",
           "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))

#: TCPMT round 3: the regulator count, topology, cell and converter tiers come from THE design
#: record (configs/design_points.yaml via scripts/phase0nw/design_record.py; HVR_DESIGN selects
#: an entry, default the production M = 36 point) for EVERY integration; a count-study candidate
#: config (HVR_Z1_CONFIG) still overrides Z1 alone (z1_design). No count, cell or tier name is a
#: literal here any more.
import z1_design as Z1D                                              # noqa: E402
import design_record as DR                                           # noqa: E402

P_LOAD_W, V_IN, V_OUT = 1000.0, 48.0, 1.0
N_VR = Z1D.n_vr()
SCENARIOS = ("HV_S0", "HV_S1", "HV_S2")
#: HV RMS / HV average for each named scenario -- the rms_currents definitions
#: (S0 continuous; S1 square pulse at the buck duty D = N V_out / V_in of the design in force;
#: S2 square pulse at 1/48).
SCEN_RATIO = {"HV_S0": 1.0, "HV_S1": 1.0 / math.sqrt(Z1D.buck_duty()),
              "HV_S2": math.sqrt(V_IN / V_OUT)}

#: component class of a converter tier: a mixed tier of the design record holds several
#: (design_record.tier_classes); a single-class tier (count-study candidates) is named by its
#: class prefix
_TIER_CLASS = (("gan_hs", "gan_hs"), ("gan_ls", "gan_ls"), ("flying_caps", "cap_fly"),
               ("inductor", "inductor"), ("output_caps", "cap_out"))
#: ledger key of each class (the LAYERS map, the temperature regions, the deposits)
CLASS_KEY = {"gan_hs": "hs", "gan_ls": "ls", "inductor": "ind", "cap_fly": "caps",
             "cap_out": "cout"}
#: layer-name prefix of the converter tiers of each integration
TIER_PREFIX = {"Z1": "z1conv_", "Z2": "conv_", "Z2BF": "conv_", "Z3": "z3conv_"}
Z2_CFG = R / "configs" / "phase0nt" / "z2_2p4mm_cutout.yaml"
Z3_CFG = R / "configs" / "phase0nz" / "z3_board_backside.yaml"


def config_tiers(arch):
    """The converter tier list [(name, um)] of an integration's config IN FORCE, in config
    order (Z1 upward from the substrate; Z2/Z3 downward), after the design record is applied
    (design_record.apply_converter)."""
    import yaml
    if arch == "Z1":
        p = Z1D.config_path()
        c = DR.apply_converter(yaml.safe_load(p.read_text()), "Z1", source=p.name)
        raw = c["converter"]["tiers_from_substrate_upward"]
    elif arch == "Z3":
        c = DR.apply_converter(yaml.safe_load(Z3_CFG.read_text()), "Z3", source=Z3_CFG.name)
        raw = c["converter"]["tiers_from_board_downward"]
    else:
        c = DR.apply_converter(yaml.safe_load(Z2_CFG.read_text()), "Z2", source=Z2_CFG.name)
        raw = c["converter"]["tiers_from_substrate_downward"]
    return [(t["name"], float(t["um"])) for t in raw]


def tier_contents(name, counts=None):
    """{class: n} of one converter tier name: a mixed tier of the design record, a
    single-class tier (all parts of its class), {} for an RDL."""
    mixed = DR.tier_classes(name) if name.startswith("tier") else {}
    if mixed:
        return mixed
    cls = next((c for key, c in _TIER_CLASS if name.startswith(key)), None)
    if cls is None:
        return {}
    if counts is None:
        N, K, _ = Z1D.topology() or DR.topology()
        counts = {"gan_hs": N, "gan_ls": K, "inductor": K, "cap_fly": N - 1, "cap_out": 1}
    if name.startswith("inductor_plus_cout"):
        return {"inductor": counts["inductor"], "cap_out": 1}
    return {cls: counts[cls]}


def layers_for(arch):
    """final_closure_ledger.LAYERS[arch] of the design in force: every converter tier holding
    each class (lists: a class may sit in several mixed tiers), the tier contents, the RDL
    tiers and the fixed package layers."""
    tiers = config_tiers(arch)
    pre = TIER_PREFIX[arch]
    names = [f"{pre}{i}_{n}" for i, (n, _um) in enumerate(tiers)]
    parts = {}
    for ln, (n, _um) in zip(names, tiers):
        c = tier_contents(n)
        if c:
            parts[ln] = c
    lay = {CLASS_KEY[c]: [ln for ln, pc in parts.items() if pc.get(c)]
           for c in ("gan_hs", "gan_ls", "inductor", "cap_fly")}
    if any(pc.get("cap_out") for pc in parts.values()):
        lay["cout"] = [ln for ln, pc in parts.items() if pc.get("cap_out")]
    lay["parts"] = parts
    lay["converter"] = list(parts)
    lay["rdl"] = [ln for ln, (n, _um) in zip(names, tiers) if n.endswith("_rdl")]
    lay.update({"tsv": "sub_lower", "pads": "interface", "bga": "bga", "die": "die"})
    if arch == "Z1":
        lay.update({"lv": names[-1], "pkg_hv": "bga"})
    elif arch in ("Z2", "Z2BF"):
        lay.update({"attach": "conv_attach_vr_substrate", "lv": "z2_top_rdl", "pkg_hv": "bga"})
    else:
        lay.update({"attach": "z3_attach_vr_pcb", "pcb_via": "board", "lv": "z2_top_rdl"})
    return lay


LAYERS = {a: layers_for(a) for a in ("Z1", "Z2", "Z2BF")}


def input_end_layer(arch):
    """The converter layer of the INPUT-end tier (the high side, 48 V): the record's first
    tier (Z1: next to the bottom substrate; Z2/Z3: the deepest tier)."""
    lay = LAYERS[arch]
    first = DR.tiers()[0]["name"]
    hits = [ln for ln in lay["converter"] if ln.endswith("_" + first)]
    if hits:
        return hits[0]
    return lay["hs"][0] if isinstance(lay["hs"], list) else lay["hs"]

#: architecture identity, carried into every artifact so the two Z2s can never be confused
VARIANT = {"Z1": "Z1_EMBEDDED", "Z2": "Z2_DIRECT_FEED", "Z2BF": "Z2_BGA_FED_CONTROL"}
HV_FEED = {"Z1": "BGA_FED", "Z2": "DIRECT_FEED", "Z2BF": "BGA_FED"}
#: the package-level 48 V network of a BGA-fed architecture; package_network.json keys its
#: BGA-fed Z2 network as "Z2"
NETWORK_KEY = {"Z1": "Z1", "Z2BF": "Z2"}
#: terms a direct-fed architecture can NEVER carry: its 48 V never enters the package
FORBIDDEN_DIRECT_FEED_TERMS = ("P_pkg_RDL_HV_supply", "P_pkg_RDL_HV_return",
                               "P_BGA_supply", "P_BGA_return")
ARCH_SPEC = R / "research" / "final_closure" / "z2_direct_feed_architecture.json"

#: Z3 -- the SAME regulator and tier order as Z2, hung from the PCB BACKSIDE
#: (configs/phase0nz/z3_board_backside.yaml). Direct-fed like Z2, so no package 48 V term;
#: its 1 V output crosses a VR-to-PCB solder attach, the board's plated through-holes and the
#: full BGA before the substrate TSVs. `pcb_via` is the board, whose elements under the cells
#: hold the via fields (final_closure_physical_etm.in_tile_keys confines that loss to them).
LAYERS["Z3"] = layers_for("Z3")
VARIANT["Z3"] = "Z3_BOARD_BACKSIDE"
HV_FEED["Z3"] = "DIRECT_FEED"

#: the intra-VR fidelity policy, declared before the R0/R2/reference differences
#: were read: point-to-point traces -> R0 width rule; via stacks -> R0 via model;
#: the distributed output plane -> R2 sheet. R1 is retired (no net obstructed).
FIDELITY_POLICY = {"lateral": "R0", "vertical": "R0_VIA", "plane": "R2"}
#: production construction of every intra-VR tier: one 10 um copper layer, as the
#: physical stacks carry it. The historical 9-layer routing assumption matched no
#: physical stack (Z1 has five RDL tiers, Z2 four).
INTRA_T_CU_M, INTRA_N_LAYERS, INTRA_J_MAX = 10e-6, 1, 1.0e8
VOUT_PLANE_OCCUPANCY = 0.80          # DECLARED, swept in the sensitivity

PAD_CASES = {
    "COMPACT": "pad field confined to a quarter of the tile",
    "SOURCE_ANCHORED": "DVPD Table III: 200,000 VICs over 20 mm^2, split evenly "
                       "between the two 1 V rails",
    "DISTRIBUTED": "geometric maximum over the full tile at the 0.30 keepout",
}
PAD_PRODUCTION = "SOURCE_ANCHORED"


def rho_ratio_cu(t_c, t_ref=20.0):
    from interconnect import rho_cu
    return rho_cu(t_c) / rho_cu(t_ref)


# ---------------------------------------------------------------------------
# converter intrinsic losses
# ---------------------------------------------------------------------------
def converter_terms(t_conv_c):
    """System converter loss per component class at one temperature (W): each class's
    conduction and switching on its own devices (the per-device split, ledger.device_split:
    gate drive and C_oss to the high- or low-side die that dissipates them)."""
    import replay_production as RPX
    dec = RPX.converter_terms(t_conv_c)
    sysw = lambda k: dec[k] * N_VR                                    # noqa: E731
    return {
        "P_conv_hs": sysw("P_hs_total"),
        "P_conv_ls": sysw("P_ls_total"),
        "P_conv_inductor_dcr": sysw("P_inductor_DCR"),
        "P_conv_cap_esr": sysw("P_cap_ESR"),
        "_per_part": dec["per_part"],
        "_check_total_w": dec["p_conv_total_w"],
    }


#: the class each converter ledger row owns
ROW_CLASS = (("P_conv_hs", "gan_hs", "hs", "high-side GaN (cond+sw+gate+Coss)"),
             ("P_conv_ls", "gan_ls", "ls", "low-side GaN (cond+gate+Coss)"),
             ("P_conv_inductor_dcr", "inductor", "ind", "inductor DCR"),
             ("P_conv_cap_esr", "cap_fly", "caps", "capacitor ESR"))


def _part_indices(layer, cls, n):
    """Part indices of class `cls` in a converter tier (the design record's tier-order
    assignment; the first n indices for a single-class tier)."""
    name = layer.split("_", 2)[-1] if layer.count("_") >= 2 else layer
    tname = name[name.index("tier"):] if "tier" in name else name
    asg = (DR.get().get("tier_order") or {}).get("assignment") or {}
    try:
        t_i = next(i for i, t in enumerate(DR.tiers(), start=1) if t["name"] == tname)
    except StopIteration:
        return list(range(n))
    idx = sorted(int(k[len(cls):]) for k, v in asg.items()
                 if k.startswith(cls) and k[len(cls):].isdigit() and int(v) == t_i)
    return idx if len(idx) == n else list(range(n))


def converter_rows_split(arch, temps, t_conv, ct_at):
    """{row term: (P_w, [deposit split])}: every converter part's loss evaluated at the
    in-cell temperature of the tier HOLDING it and deposited in that tier -- per die (equal
    share of its class's conduction and switching), per inductor (DCR by B_k^2), per flying
    capacitor (ESR, equal share). A tier temperature key is 'tier:<layer>'; without it the
    class key (an older caller), then the converter mean."""
    lay = LAYERS[arch]
    N, K, _ = Z1D.topology() or DR.topology()
    n_of = {"gan_hs": N, "gan_ls": K, "inductor": K, "cap_fly": max(N - 1, 1)}
    out = {}
    for term, cls, key, _label in ROW_CLASS:
        split = []
        for layer, pc in lay["parts"].items():
            n = int(pc.get(cls, 0))
            if not n:
                continue
            t_k = float(temps.get(f"tier:{layer}", temps.get(key, t_conv)))
            ct = ct_at(t_k)
            if cls == "inductor":
                per = ct["_per_part"]["inductor"]
                w = sum(per[j] for j in _part_indices(layer, cls, n)) / sum(per) \
                    if sum(per) > 0 else n / n_of[cls]
            else:
                w = n / n_of[cls]
            split.append({"layer": layer, "parts": n, "T_C": t_k, "P_w": w * ct[term]})
        out[term] = (sum(x["P_w"] for x in split), split)
    return out


# ---------------------------------------------------------------------------
# intra-VR: R0 traces and via stacks, R2 output plane
# ---------------------------------------------------------------------------
def routing_design() -> dict:
    """The routing dict of the design in force: the design record's (routing.design_in_force:
    the compiled converter's fields at the record's cell, the B-vector and the part-level
    layout of the mixed tiers), a candidate config's rebuilt by z1_design.design_dict. The
    49-cell literal (routing.DESIGN_49_LEGACY) is never the production design."""
    import routing as RT
    key = (DR.name(), str(Z1D.config_path()))
    if key not in _ROUTING_CACHE:
        _ROUTING_CACHE[key] = Z1D.routing_design(RT.DESIGN_49_LEGACY)
    return dict(_ROUTING_CACHE[key])


_ROUTING_CACHE: dict = {}


@lru_cache(maxsize=4)
def vout_plane_r2(occupancy=VOUT_PLANE_OCCUPANCY, level=2):
    """Output plane on the tile: the K inductor footprints inject I/K each (where the design
    record's layout puts them), the pad field over the tile extracts uniformly. Returns R_eff
    (Ohm) at 20 C and the control-volume count (routing.output_plane_r2)."""
    import routing as RT
    return RT.output_plane_r2(routing_design(), occupancy, level, INTRA_T_CU_M)


def cell_tiers(arch):
    """The tiers of ONE regulator cell, from the input (high-side) end to the output end, as
    [(name, thickness_um, {class: n})] ({} for an RDL), read from the architecture's own config
    in force so the electrical routing and the meshed stack can never disagree on the tier
    order. The output plane is beyond the last entry; the input landing plane is the first
    entry for Z1 (its bottom-substrate RDL) and the free face beyond the input-end tier for
    Z2/Z3 (direct feed from below)."""
    t = config_tiers(arch)
    if arch != "Z1":
        t = list(reversed(t))           # Z2/Z3: deepest (input end) first, attach RDL last
    return [(n, um, tier_contents(n)) for n, um in t]


def _component_index(arch):
    """Index of every routed component in cell_tiers(arch): parts by their tier (the design
    record's part-level layout, or the class of a single-class tier), VIN on the input
    landing plane, VOUT on the output plane."""
    tiers = cell_tiers(arch)
    names = [n for n, _um, _c in tiers]
    out = {}
    d = routing_design()
    if d.get("layout"):
        for p in d["layout"]:
            out[p["name"]] = names.index(p["tier_name"])
    else:
        import routing as RT
        for c in RT.tile_layout(d["tile_side_mm"], d):
            cls = {"gan_hs": "gan_hs", "gan_ls": "gan_ls", "inductor": "inductor",
                   "cap_fly": "cap_fly", "cap_out": "cap_out"}.get(c.kind)
            if cls is None:
                continue
            hit = [i for i, (_n, _um, pc) in enumerate(tiers) if pc.get(cls)]
            if not hit and cls == "cap_out":
                hit = [i for i, (_n, _um, pc) in enumerate(tiers) if pc.get("inductor")]
            if hit:
                out[c.name] = hit[0]
    # VIN: Z1's bottom landing RDL (entry 0); Z2/Z3 feed the free face below the input-end
    # tier (index -1, before entry 0). VOUT: the output RDL / land-side attach RDL (last entry)
    out["VIN"] = 0 if arch == "Z1" else -1
    out["VOUT"] = len(tiers) - 1
    return out, tiers


def face_span_um(tiers, i, j, plane=None):
    """Depth a vertical net must cross between the components at cell_tiers indices i and j:
    every entry strictly between them (tiers and interlayer RDLs). `plane` marks an end that
    is a plane rather than a component (VIN / VOUT): the plane itself is not crossed."""
    lo, hi = sorted((i, j))
    return sum(um for _n, um, _c in tiers[max(lo + 1, 0):hi])


def intra_vr(t_conv_c, scen, arch="Z1"):
    """Per-system intra-VR metal and vertical losses under the fidelity policy.

    Same R0 trace and via models as before; the GEOMETRY follows the cell's actual tier
    order AT PART LEVEL (TCPMT round 3): every component sits in the tier the design record's
    tier-order assignment puts it in, a link between components in different tiers is a via
    stack across the face-to-face span between them (Phase-0M-R3B DEFECT #62 convention), and
    a link within one tier -- or between a component and the plane its tier lands on -- is a
    lateral R0 run on the cell layout."""
    import routing as RT
    d = routing_design()
    comps = {c.name: c for c in RT.tile_layout(d["tile_side_mm"], d)}
    idx, tiers = _component_index(arch)
    s_m = d["tile_side_mm"] * 1e-3
    k_t = rho_ratio_cu(t_conv_c, RT.T_C)
    p_lat = p_vert = 0.0
    nets = []
    for n in RT.nets(d):
        if n.name == "vout_plane":
            continue
        a, b = comps[n.src], comps[n.dst]
        ia, ib = idx.get(n.src), idx.get(n.dst)
        hgt = 0.0
        if ia is not None and ib is not None and ia != ib:
            hgt = face_span_um(tiers, ia, ib)
            if hgt <= 0.0 and b.kind == "pad_out":
                # a component on the output plane's own face reaches it through that RDL
                # (the legacy 'terminal -> the output RDL plane above it' step); the plane's
                # spreading is the R2 vout_plane term
                hgt = float(tiers[ib][1])
        if hgt > 0.0:
            fp = min(a.w_mm * a.h_mm, b.w_mm * b.h_mm)
            seg = RT.vertical_segment(max(n.i_rms_a, 1e-9), hgt, INTRA_J_MAX, fp,
                                      "D_area_optimal")
            geom, length_mm = "vertical", hgt * 1e-3
        else:
            length_mm = RT.manhattan(a, b)
            seg = RT.lateral_segment(max(n.i_rms_a, 1e-9), length_mm, INTRA_T_CU_M,
                                     INTRA_J_MAX, s_m, INTRA_N_LAYERS)
            geom = "lateral"
        scale = SCEN_RATIO[scen] ** 2 if n.rail == "HV" else 1.0
        p = n.i_rms_a ** 2 * seg["R_ohm"] * k_t * scale
        if geom == "vertical":
            p_vert += p
        else:
            p_lat += p
        nets.append({"net": n.name, "geom": geom, "rail": n.rail,
                     "model": FIDELITY_POLICY[geom], "length_mm": length_mm,
                     "R_ohm": seg["R_ohm"] * k_t, "P_w_per_vr": p})
    r_plane_20, n_cv = vout_plane_r2()
    i_out = d["i_out_per_vr_a"]
    import rms_currents as RMS
    i_out_rms = RMS.cell_currents()["i_cell_out_rms_a"]
    p_plane = i_out_rms ** 2 * r_plane_20 * rho_ratio_cu(t_conv_c)
    nets.append({"net": "vout_plane", "geom": "plane", "rail": "LV", "model": "R2",
                 "R_ohm": r_plane_20 * rho_ratio_cu(t_conv_c), "P_w_per_vr": p_plane,
                 "n_cv": n_cv, "i_rms_a": i_out_rms, "i_avg_a": i_out})
    return {"P_intraVR_metal": (p_lat + p_plane) * N_VR,
            "P_intraVR_vertical": p_vert * N_VR, "nets": nets}


# ---------------------------------------------------------------------------
# package HV network, BGA, TSV, pads
# ---------------------------------------------------------------------------
#: REVIEW ROUND 3 (the authors' decision of 2026-11-22): the 48-V BGA carries the re-closure's
#: ADOPTED count (final_closure_pkg_network.ADOPT_RULE: per architecture the smallest legal
#: count meeting the per-ball target, within the site budget), solved by the re-closure into
#: this file beside the network build's package_network.json (whose count, the modelled
#: arrangement, is the network the decoupling chain derives k_eq on). Only which lattice sites
#: carry 48 V changes; the ball layer and the joint search do not.
ADOPTED_NETWORK_NAME = "package_network_adopted.json"


def _same_design(a, b):
    ka = ((a.get("meta") or {}).get("design") or {})
    kb = ((b.get("meta") or {}).get("design") or {})
    return all(ka.get(k) == kb.get(k) for k in ("design", "tag", "n_vr"))


def merge_adopted(pn, adopted):
    """The network build's record with the adopted network's loop and per-ball split (per
    architecture key, at its own count) in place of the modelled arrangement's, when the
    adopted network is of the same design; otherwise the network build's record unchanged."""
    if not adopted or not _same_design(pn, adopted):
        return pn
    out = dict(pn)
    out["loop"] = {**pn.get("loop", {}), **adopted.get("loop", {})}
    out["convergence"] = {**pn.get("convergence", {}), **adopted.get("convergence", {})}
    out["adopted_count"] = dict(adopted.get("adopted_count") or {})
    out["modelled_count"] = pn.get("matched_count")
    return out


@lru_cache(maxsize=1)
def package_network():
    """The package 48 V network (research/final_closure/package_network.json; a non-default
    Z1 design names its own, solved on its own cell grid), at the re-closure's adopted count
    when the re-closure has written one for the same design beside it (ADOPTED_NETWORK_NAME)."""
    f = Z1D.package_network_file()
    pn = json.loads(f.read_text())
    fa = f.with_name(ADOPTED_NETWORK_NAME)
    return merge_adopted(pn, json.loads(fa.read_text())) if fa.is_file() else pn


def package_hv_terms(pn, nk, i_hv_rms, t_bga):
    """The package-level 48-V terms of a BGA-fed architecture as the ledger rows carry them:
    the package HV RDL sheet of each rail (the network's 20-C loop resistance x rho_Cu(T) /
    rho_Cu(20 C)) and the BGA balls of each rail (Table III rho_solder h / A x sum f^2 of the
    solved per-ball split), at the BGA temperature t_bga and the 48-V RMS current i_hv_rms, on
    network record `pn` (key nk). {term: {P_w, R_ohm, n_per_rail}}; the re-closure evaluates
    the same terms on the adopted and the modelled networks (its coupled-effect check)."""
    import pad_interface as PAD
    from interconnect import rho_solder
    loop = pn["loop"][nk]
    kt_bga = rho_ratio_cu(t_bga)
    kt_sol = rho_solder(t_bga) / rho_solder(20.0)
    out = {}
    for rail in ("supply", "return"):
        r20 = loop[f"r_{rail}_ohm"]
        out[f"P_pkg_RDL_HV_{rail}"] = {"P_w": i_hv_rms ** 2 * r20 * kt_bga,
                                       "R_ohm": r20 * kt_bga,
                                       "n_per_rail": int(loop["n_per_rail"])}
        f = np.asarray(pn["convergence"][f"{nk}_{rail}"]["i_ball_frac"])
        r_ball = PAD.bga_ball_resistance_ohm(20.0) * kt_sol
        out[f"P_BGA_{rail}"] = {"P_w": r_ball * i_hv_rms ** 2 * float(np.sum(f ** 2)),
                                "R_ohm": r_ball / max(1e-30, 1.0 / float(np.sum(f ** 2))),
                                "n_per_rail": len(f)}
    return out


def pad_count(case):
    import pad_interface as PAD
    import rms_currents as RMS
    i = RMS.cell_currents()["i_cell_out_rms_a"]
    a_cell = Z1D.cell_area_mm2()                    # the design record's cell
    base = PAD.size_for_cell(i, a_cell)
    if case == "DISTRIBUTED":
        return base["PAD_GEOM_MAX"]["n_per_rail"]
    if case == "COMPACT":
        return PAD.geometric_capacity(a_cell / 4.0, 0.30)["n_vdd"]
    if case == "SOURCE_ANCHORED":
        return int(200_000 / N_VR / 2)
    raise ValueError(case)


@lru_cache(maxsize=1)
def attach_spec():
    """The VR-attach spec of the direct-fed architecture (hand-written, frozen before results)
    on the cell of the design in force: TCPMT round 3 replaces the spec's 49-cell side
    (2.3685 mm) by the design record's, so the bump count follows the cell."""
    sp = dict(json.loads(ARCH_SPEC.read_text())["vr_attach"])
    sp["cell_side_mm"] = Z1D.cell_side_mm()
    sp.pop("bumps_per_rail_per_cell", None)
    return sp


def vr_attach_r_per_rail_cell(t_c, spec=None):
    """Resistance of ONE rail of ONE cell's VR attach: n Cu-pillar + solder-cap bumps in
    parallel, R_bump = (rho_Cu h_Cu + rho_solder h_cap) / A at the attach temperature.
    Contact and IMC resistance are not resolved (the all-solder class-B bound brackets
    them). Returns (R_ohm, n_bumps, R_bump_ohm)."""
    from interconnect import rho_cu, rho_solder
    sp = dict(spec or attach_spec())
    a = math.pi * (sp["d_um"] * 1e-6 / 2.0) ** 2
    r_b = (rho_cu(t_c) * sp["h_cu_um"] * 1e-6 + rho_solder(t_c) * sp["h_cap_um"] * 1e-6) / a
    n = int(math.floor(sp["cell_side_mm"] / (sp["pitch_um"] * 1e-3)) ** 2 // 2)
    return r_b / n, n, r_b


def vr_attach_rails(t_c, spec=None):
    """Per rail: (R_rail_per_cell_ohm, n_bumps, R_bump_ohm). A spec from
    final_closure_vr_attach.ledger_spec (the attach-density study) carries the REAL lattice's
    VDD and GND counts (a checkerboard can be odd) and the two-sided constriction into each
    bump, which lives in Cu and scales with its resistivity. The production spec carries
    neither and keeps the legacy model (equal rails, no constriction) -- for the production
    geometry the two agree to the study's stated difference."""
    sp = dict(spec or attach_spec())
    r1, n_leg, r_b = vr_attach_r_per_rail_cell(t_c, sp)
    if "n_vdd" not in sp:
        return {"VDD": (r1, n_leg, r_b), "GND": (r1, n_leg, r_b)}
    r_b = r_b + float(sp.get("r_constriction_20c_ohm", 0.0)) * rho_ratio_cu(t_c)
    return {rail: (r_b / int(sp[k]), int(sp[k]), r_b)
            for rail, k in (("VDD", "n_vdd"), ("GND", "n_gnd"))}


@lru_cache(maxsize=1)
def z3_spec():
    """Z3's board-level 1 V path, from its OWN config (configs/phase0nz/z3_board_backside.yaml):

      attach  the attach-density study's machinery (final_closure_vr_attach): bumps on the
              REAL legal lattice of each cell (edge clearance >= (p - d)/2, VDD/GND
              checkerboard), the series column -- all solder here -- and the two-sided
              constriction of the output-plane current into each bump; the spec form
              vr_attach_rails reads
      via     one plated through-hole under every bump (via-in-pad), so the via field's
              VDD/GND counts ARE the attach lattice's; R = rho_Cu(T) L / A_annulus
      bga     the 1 V ball count of the per-ball target on the DC rail current (review round
              3: 2 A, the feasibility stage's target, as for the 48-V balls; 500 per rail),
              equal sharing (a lower bound on the BGA loss)
    """
    import final_closure_vr_attach as VA
    import physical_package as PPK
    import z3_package as Z3P
    cfg = PPK.load_z3_package_config(Z3_CFG)
    if abs(cfg.bga_1v_criterion_current_a - P_LOAD_W / V_OUT) > 1e-9:
        raise RuntimeError(f"the Z3 BGA count is provisioned for {cfg.bga_1v_criterion_current_a}"
                           f" A but the ledger's 1 V rail carries {P_LOAD_W / V_OUT} A DC")
    a = cfg.attach_dict()
    lat = Z3P.attach_lattice(cfg)
    c_fv = VA.constriction_fv(float(a["pitch_um"]), float(a["diameter_um"]))
    attach = {"h_cu_um": float(a["cu_height_um"]), "h_cap_um": float(a["cap_height_um"]),
              "d_um": float(a["diameter_um"]), "pitch_um": float(a["pitch_um"]),
              "cell_side_mm": Z3P.cell_side_um(cfg) / 1e3,
              "n_vdd": int(lat["n_vdd"]), "n_gnd": int(lat["n_gnd"]),
              "r_constriction_20c_ohm": 2.0 * c_fv * VA.sheet_resistance(20.0),
              "model": "real lattice + all-solder column + two-sided constriction"}
    return {"cfg": cfg, "attach": attach,
            "attach_lattice": {k: lat[k] for k in ("n_per_axis", "n_total", "n_vdd", "n_gnd",
                                                   "edge_clearance_um", "edge_rule_um",
                                                   "area_fraction",
                                                   "area_fraction_infinite_lattice")},
            "via": Z3P.via_field(cfg),
            "bga": {"n_per_rail": cfg.bga_1v_n_per_rail, "sites_total": cfg.bga_sites_total,
                    "criterion_a": cfg.bga_1v_criterion_a,
                    "criterion_current_a": cfg.bga_1v_criterion_current_a}}


def z3_rows(add, lay, temps, t_sub, t_bga, i_cell_rms):
    """The Z3 1 V rows between the converter and the substrate TSVs, in power-path order.
    Each conductor is deposited in its own FE region: the attach tier, the board elements
    under the cells (the via fields), the BGA layer (equal sharing over the whole field).
    The two lateral-spreading conductors the geometry needs but the model does not carry are
    RECORDED as NOT_MODELLED zero rows, never silently absent: each makes the Z3 1 V loss a
    lower bound."""
    import pad_interface as PAD
    from interconnect import rho_cu, rho_solder
    z3 = z3_spec()
    t_att = temps.get("attach", t_sub)
    sp_att = z3["attach"]
    a_bump = math.pi * (sp_att["d_um"] * 1e-6 / 2.0) ** 2
    for rail, (r_rc, n_b, r_b) in vr_attach_rails(t_att, sp_att).items():
        add(f"P_VR_PCB_attach_{rail}", f"VR-to-PCB attach {rail}: {n_b} SAC305 bumps/cell",
            "1V", N_VR * i_cell_rms ** 2 * r_rc, r_rc / N_VR, i_cell_rms, "cell output RMS",
            "rho_solder h / A per bump (all-solder column) + two-sided constriction (real "
            "lattice), n in parallel", lay["attach"], "GEOMETRY_DESIGN_CHOICE", "BOUNDED",
            "d %g um / pitch %g um / standoff %g um; R_bump = %.4g mOhm at %.1f C; %.3f A and "
            "%.0f A/cm2 per bump (OUTPUT only, no allowable claimed)"
            % (sp_att["d_um"], sp_att["pitch_um"], sp_att["h_cap_um"] + sp_att["h_cu_um"],
               r_b * 1e3, t_att, i_cell_rms / n_b, i_cell_rms / n_b / a_bump * 1e-4))
    via = z3["via"]
    t_via = temps.get("pcb_via", t_bga)
    r_via = rho_cu(t_via) * via["L_um"] * 1e-6 / (via["A_annulus_um2"] * 1e-12)
    for rail in ("VDD", "GND"):
        n = via[f"n_{rail.lower()}"]
        add(f"P_PCB_via_{rail}", f"PCB 1 V plated through-holes {rail}: {n}/cell", "1V",
            N_VR * i_cell_rms ** 2 * r_via / n, r_via / n / N_VR, i_cell_rms,
            "cell output RMS", "rho_Cu(T) L / A_annulus per via, n in parallel per rail per "
            "cell", lay["pcb_via"], "CLOSED_FORM_GEOMETRY_DESIGN_CHOICE", "BOUNDED",
            "finished hole %g um, plating %g um (drill %g um), pitch %g um, L %g um, via-in-pad "
            "under the attach bumps; R_via = %.4g mOhm at %.1f C"
            % (via["d_finished_um"], (via["d_drill_um"] - via["d_finished_um"]) / 2.0,
               via["d_drill_um"], via["pitch_um"], via["L_um"], r_via * 1e3, t_via))
    i_rail = i_cell_rms * N_VR
    add("P_PCB_plane_1V_spreading", "PCB 1 V copper planes: via fields -> BGA balls", "1V",
        0.0, None, i_rail, f"1 V output RMS of the {N_VR} cells", "none -- NOT MODELLED",
        lay["pcb_via"], "STRUCTURAL", "NOT_MODELLED",
        f"the via fields sit only under the {N_VR} cells while the 1 V balls cover the whole "
        "lattice, so the PCB planes must spread ~1 kA laterally between them; that loss is "
        "NOT modelled and the Z3 1 V loss is a LOWER BOUND")
    bga = z3["bga"]
    r_ball = PAD.bga_ball_resistance_ohm(20.0) * rho_solder(t_bga) / rho_solder(20.0)
    n = bga["n_per_rail"]
    for rail in ("VDD", "GND"):
        add(f"P_BGA_1V_{rail}", f"BGA 1 V {rail} balls (N={n}, equal sharing)", "1V",
            i_rail ** 2 * r_ball / n, r_ball / n, i_rail, f"1 V output RMS of the {N_VR} cells",
            "Table III rho_solder h / A per ball, equal sharing", lay["bga"],
            "SOURCE_REPRODUCTION", "LOWER_BOUND",
            "%d per rail by the %.1f A/ball ENGINEERING criterion on %.0f A DC (%d of %d sites, "
            "%.1f %%); equal sharing is a lower bound; %.3f A RMS per ball"
            % (n, bga["criterion_a"], bga["criterion_current_a"], 2 * n, bga["sites_total"],
               100.0 * 2 * n / bga["sites_total"], i_rail / n))
    add("P_sub_land_1V_spreading", "package land-side 1 V redistribution: BGA balls -> TSV "
        "fields", "1V", 0.0, None, i_rail, f"1 V output RMS of the {N_VR} cells",
        "none -- NOT MODELLED", lay["tsv"], "STRUCTURAL", "NOT_MODELLED",
        f"the balls cover the whole lattice while the TSV fields sit only under the {N_VR} cells, "
        "and the Z2 package adopted above the board has no land-side 1 V RDL to carry that "
        "redistribution; NOT modelled, so the Z3 1 V loss is a LOWER BOUND")


def z3_design(rows, temps, i_cell_rms):
    """The Z3 design numbers a reader needs next to the ledger: counts, per-bump and per-ball
    currents (outputs, no allowable claimed) and the fraction of the BGA field the 1 V rails
    consume."""
    z3 = z3_spec()
    p = {r["term"]: r["P_w"] for r in rows}
    att, lat, via, bga = z3["attach"], z3["attach_lattice"], z3["via"], z3["bga"]
    a_bump = math.pi * (att["d_um"] * 1e-6 / 2.0) ** 2
    i_rail = i_cell_rms * N_VR
    n = bga["n_per_rail"]
    return {
        "vr_attach": {
            "technology": "SAC305 solder bumps + underfill", "d_um": att["d_um"],
            "pitch_um": att["pitch_um"], "standoff_um": att["h_cu_um"] + att["h_cap_um"],
            **lat, "bumps_per_rail_per_cell": {"VDD": att["n_vdd"], "GND": att["n_gnd"]},
            "I_per_bump_A": {r: i_cell_rms / att[f"n_{r.lower()}"] for r in ("VDD", "GND")},
            "J_per_bump_A_cm2": {r: i_cell_rms / att[f"n_{r.lower()}"] / a_bump * 1e-4
                                 for r in ("VDD", "GND")},
            "T_attach_C": temps.get("attach"),
            "P_attach_w": p["P_VR_PCB_attach_VDD"] + p["P_VR_PCB_attach_GND"],
            "note": "per-bump current is an OUTPUT; no solder electromigration allowable is "
                    "claimed"},
        "pcb_via_field": {**via, "T_via_C": temps.get("pcb_via"),
                          "P_via_w": p["P_PCB_via_VDD"] + p["P_PCB_via_GND"]},
        "bga_1v": {"n_per_rail": n, "n_total": 2 * n, "sites_total": bga["sites_total"],
                   "fraction_of_field": 2 * n / bga["sites_total"],
                   "sites_left_for_signals_and_other_rails": bga["sites_total"] - 2 * n,
                   "criterion_A_per_ball": bga["criterion_a"],
                   "criterion_current_A_dc": bga["criterion_current_a"],
                   "I_per_ball_A_dc_equal_sharing": bga["criterion_current_a"] / n,
                   "I_per_ball_A_rms_equal_sharing": i_rail / n,
                   "n_per_rail_if_provisioned_on_rms": math.ceil(i_rail / bga["criterion_a"]),
                   "T_bga_C": temps.get("bga"),
                   "P_bga_1v_w": p["P_BGA_1V_VDD"] + p["P_BGA_1V_GND"],
                   "sharing": "EQUAL (lower bound)"},
        "not_modelled": [r["term"] for r in rows if r["maturity"] == "NOT_MODELLED"],
        "lower_bound_statement": ("the Z3 1 V loss is a LOWER BOUND: equal BGA sharing, and "
                                  "neither the PCB plane spreading nor the package land-side "
                                  "redistribution is modelled"),
    }


def ledger(arch, scen, temps, i_hv_avg_a, pad_case=PAD_PRODUCTION):
    """All terms for one architecture and scenario at the given temperatures."""
    import pad_interface as PAD
    import rms_currents as RMS
    import tsv_fields as TF
    import physical_package as PPK
    if arch not in VARIANT:
        raise KeyError(f"unknown architecture {arch!r}; known {sorted(VARIANT)}")
    Z1D.require_z1(arch, "the ledger")
    t_conv, t_bga, t_sub, t_if = (temps["conv"], temps["bga"], temps["sub"],
                                  temps["interface"])
    lay = LAYERS[arch]
    i_hv_rms = i_hv_avg_a * SCEN_RATIO[scen]
    i_cell_rms = RMS.cell_currents()["i_cell_out_rms_a"]
    rows = []

    def add(term, conductor, rail, value, R_ohm, I_a, current_type, model, layer,
            evidence, maturity, note=""):
        rows.append({"arch": arch, "scenario": scen, "term": term,
                     "conductor": conductor, "rail": rail, "P_w": value,
                     "R_ohm": R_ohm, "I_a": I_a, "current_type": current_type,
                     "model": model, "deposit_layer": layer, "evidence": evidence,
                     "maturity": maturity, "note": note})

    # each device term at the in-cell temperature of its OWN tier, the region its loss is
    # deposited in (final_closure_physical_etm.temperature_regions; DEFECT #68). Without
    # per-tier keys (an older caller) every term falls back to the converter mean.
    ct_at = lru_cache(maxsize=16)(converter_terms)
    import replay_production as _RPX
    ident = _RPX.design_identity()      # review round 2: the converter lineage, on every row
    ident["design"] = DR.design_identity() if Z1D.is_default() else Z1D.summary()
    split = converter_rows_split(arch, temps, t_conv, ct_at)
    for k, _cls, _key, comp in ROW_CLASS:
        p_k, sp = split[k]
        ts = ", ".join(f"{x['parts']} in {x['layer']} at {x['T_C']:.2f} C" for x in sp)
        add(k, comp, "converter", p_k, None, None, "converter model RMS",
            f"HVR_FULL_OPT_EPC_V2 closed form, each part at the in-cell temperature of the "
            f"tier holding it ({ts})", ",".join(x["layer"] for x in sp),
            "CONSERVATION_VERIFICATION", "CLOSED")
        rows[-1]["converter"] = ident
        rows[-1]["deposit_split"] = sp

    iv = intra_vr(t_conv, scen, arch)
    add("P_intraVR_metal", "cell traces (R0) + output plane (R2)", "mixed",
        iv["P_intraVR_metal"], None, None, "converter-model RMS; HV nets per scenario",
        "R0 width rule + R2 refined FV sheet", ",".join(lay["rdl"]),
        "MODEL_CONSISTENCY", "SCENARIO" if scen != "HV_S0" else "CLOSED")
    add("P_intraVR_vertical", "cell via stacks", "mixed", iv["P_intraVR_vertical"],
        None, None, "converter-model RMS", "R0 via stack, footprint-filling policy",
        ",".join(lay["rdl"]), "CLOSED_FORM_VERIFICATION", "CLOSED")

    if HV_FEED[arch] == "BGA_FED":
        # the package-level 48 V network: BGA balls + package 48 V RDL sheet (Z1, and the
        # Z2_BGA_FED_CONTROL). A direct-fed architecture has no such network.
        # Review round 3: at the re-closure's adopted count when it exists (package_network).
        pn = package_network()
        nk = NETWORK_KEY[arch]
        terms = package_hv_terms(pn, nk, i_hv_rms, t_bga)
        src = ("48-V balls at the re-closure's adopted count (%s)" % ADOPTED_NETWORK_NAME
               if nk in (pn.get("adopted_count") or {}) else "")
        for rail in ("supply", "return"):
            t = terms[f"P_pkg_RDL_HV_{rail}"]
            add(f"P_pkg_RDL_HV_{rail}", f"package HV RDL {rail} sheet", "48V",
                t["P_w"], t["R_ohm"], i_hv_rms, f"HV RMS, {scen}",
                "voltage-fed refined FV sheet, N=%d/rail" % t["n_per_rail"],
                lay["pkg_hv"], "MESH_CONVERGENCE",
                "SCENARIO" if scen != "HV_S0" else "CLOSED", src)
            b = terms[f"P_BGA_{rail}"]
            add(f"P_BGA_{rail}", f"BGA {rail} balls (N=%d)" % b["n_per_rail"], "48V",
                b["P_w"], b["R_ohm"], i_hv_rms,
                f"HV RMS, {scen}, solved per-ball split", "Table III rho_solder h / A",
                lay["bga"], "SOURCE_REPRODUCTION",
                "SCENARIO" if scen != "HV_S0" else "CLOSED", src)

    if arch == "Z3":
        # Z3: VR-to-PCB attach, PCB plated through-holes, 1 V BGA (z3_rows); the TSV field,
        # top RDL and pads below are Z2's
        z3_rows(add, lay, temps, t_sub, t_bga, i_cell_rms)
    elif "attach" in lay:
        # the explicit VR-to-substrate attach: Cu pillar + solder cap per bump, one
        # VDD/GND checkerboard over each cell, carrying only the 1 V output current
        t_att = temps.get("attach", t_sub)
        sp_att = attach_spec()
        for rail, (r_rc, n_b, r_b) in vr_attach_rails(t_att, sp_att).items():
            add(f"P_VR_attach_{rail}", f"VR attach {rail}: {n_b} Cu-pillar bumps/cell",
                "1V", N_VR * i_cell_rms ** 2 * r_rc, r_rc / N_VR, i_cell_rms,
                "cell output RMS", "(rho_Cu h_Cu + rho_solder h_cap) / A per bump, "
                "n in parallel" + (" + two-sided constriction (real lattice)"
                                   if "n_vdd" in sp_att else ""),
                lay["attach"], "GEOMETRY_CLOSE_ANALOG", "BOUNDED",
                ("d %g um / pitch %g um, %s; R_bump = %.4g mOhm at %.1f C"
                 % (sp_att["d_um"], sp_att["pitch_um"], sp_att["model"], r_b * 1e3, t_att))
                if "n_vdd" in sp_att else
                ("Au et al. ECTC 2016 geometry (CLOSE_ANALOG); R_bump = %.4g mOhm at %.1f C"
                 % (r_b * 1e3, t_att)))

    # Z3's TSV field is Z2's, but its cells and substrate come from Z3's own config; a
    # non-default Z1 design takes its cells from its own Z1 config (the production Z1 cell
    # count and side equal Z2's, which this has always read)
    cfg = (z3_spec()["cfg"] if arch == "Z3" else
           PPK.load_z1_package_config(Z1D.config_path()) if arch == "Z1" else
           PPK.load_physical_package_config(Z2_CFG))
    h_tsv = cfg.substrate_mm if arch == "Z3" else 0.300
    # TCPMT round 3: the TSV lattice of the FE card (final_closure_physical_etm.
    # TSV_N_PER_CELL), sized for the cell current of the design in force
    n_side = int(round(math.sqrt(Z1D.tsv_n_per_cell())))
    if arch == "Z1":
        rep = TF.system_report(cfg.cells, cfg.cell_side_mm, 0.300,
                               i_hv_rms, T_C=t_sub, n_side=n_side)
        rail_v, cur = "48V", f"HV RMS, {scen}"
    else:
        rep = TF.system_report(cfg.cells, cfg.cell_side_mm, h_tsv,
                               i_cell_rms * N_VR, T_C=t_sub, n_side=n_side)
        rail_v, cur = "1V", "cell output RMS"
    for rail, key in (("VDD", "p_vdd_total_w"), ("GND", "p_gnd_total_w")):
        pc = rep["per_cell"]
        r_cell = pc[f"r_{rail.lower()}_ohm"] + pc[f"r_spread_{rail.lower()}_ohm"]
        add(f"P_TSV_{rail}", f"TSV field {rail}, {pc[f'n_{rail.lower()}']}/cell, "
            f"incl. two-end spreading", rail_v, rep[key], r_cell / N_VR,
            pc["i_cell_a"] * N_VR, cur, "rho L/A per via + compact spreading",
            lay["tsv"], "INDEPENDENT_NUMERICAL_VALIDATION",
            "CLOSED" if (arch in ("Z2", "Z3") or scen == "HV_S0") else "SCENARIO")

    n_pad = pad_count(pad_case)
    r_pad = PAD.pad_bulk_resistance_ohm(t_if)
    for rail in ("VDD", "GND"):
        add(f"P_pad_{rail}", f"source Cu pads, {n_pad}/rail/cell ({pad_case})", "1V",
            N_VR * i_cell_rms ** 2 * r_pad / n_pad, r_pad / n_pad / N_VR, i_cell_rms,
            "cell output RMS", "Table III rho_Cu h / A", lay["pads"],
            "SOURCE_REPRODUCTION", "SENSITIVITY_BOUNDED", PAD_CASES[pad_case])

    p_lv_alt = lv_alternative_loss_w(t_if) / 2.0          # per rail
    for rail in ("supply", "return"):
        add(f"P_pkg_RDL_LV_{rail}", "package LV lateral spreading", "1V", 0.0, 0.0,
            i_cell_rms, "cell output RMS", "none -- see note", lay["lv"],
            "STRUCTURAL", "STRUCTURALLY_ABSENT",
            "the source-pad field sits over the tile footprint (the pad model's own "
            "geometric capacity), so 1 V leaves the package directly above each cell; "
            "the in-tile collection is owned by P_intraVR_metal (R2 output plane) and "
            "the lateral spreading beyond the tile happens in the die's power grid, "
            "outside package scope. ALTERNATIVE, quantified: if the pad field were "
            "spread over the whole cell pitch, a 10 um / 80 %% plane would carry the "
            "spreading at %.4f W per rail (lv_alternative_r_ohm, periodic unit cell)"
            % p_lv_alt)
        rows[-1]["alternative_P_w"] = p_lv_alt
    check_direct_feed(arch, rows)
    total = sum(r["P_w"] for r in rows)
    out = {"rows": rows, "P_loss_w": total, "intra_vr_nets": iv["nets"],
           "n_pad": n_pad, "i_hv_avg_a": i_hv_avg_a, "i_hv_rms_a": i_hv_rms,
           "architecture_variant": VARIANT[arch], "hv_feed": HV_FEED[arch]}
    if HV_FEED[arch] == "DIRECT_FEED":
        # OUTSIDE the package-internal boundary: the external feed is a swept parameter
        # (R_Z2_direct_feed_loop; Z3's own loop to the board backside for Z3), so only its
        # scaling is recorded here
        out["external_feed"] = {"parameter": ("R_Z3_direct_feed_loop" if arch == "Z3" else
                                              "R_Z2_direct_feed_loop"),
                                "i_48_avg_a": i_hv_avg_a, "i_48_rms_a": i_hv_rms,
                                "P_feed_per_mohm_w": i_hv_rms ** 2 * 1e-3,
                                "in_package_internal_total": False}
    if arch == "Z3":
        out["z3_design"] = z3_design(rows, temps, i_cell_rms)
    return out


def check_direct_feed(arch, rows):
    """A direct-fed architecture's 48 V never enters the package: refuse any package 48 V
    BGA or RDL term in its ledger (Z2_DIRECT_FEED_ARCHITECTURE.md section 2)."""
    if HV_FEED.get(arch) != "DIRECT_FEED":
        return
    bad = sorted({r["term"] for r in rows if r["term"] in FORBIDDEN_DIRECT_FEED_TERMS})
    if bad:
        raise RuntimeError(f"{VARIANT[arch]} acquired package 48 V terms {bad}: its 48 V "
                           "never enters the package")


def self_consistent(arch, scen, temps, tol_w=1e-6, max_iter=50, **kw):
    """Fixed point: I_48 = (P_load + P_loss(I_48)) / 48."""
    i = (P_LOAD_W + 130.0) / V_IN
    hist = []
    for k in range(max_iter):
        L = ledger(arch, scen, temps, i, **kw)
        i_new = (P_LOAD_W + L["P_loss_w"]) / V_IN
        hist.append({"iter": k, "i_hv_avg_a": i, "P_loss_w": L["P_loss_w"]})
        if abs(i_new - i) * V_IN < tol_w:
            L["i_hv_avg_a"] = i_new
            break
        i = i_new
    p_in = V_IN * L["i_hv_avg_a"]
    L["energy"] = {"P_input_w": p_in, "P_load_w": P_LOAD_W, "P_loss_w": L["P_loss_w"],
                   "residual_w": p_in - P_LOAD_W - L["P_loss_w"],
                   "residual_rel": (p_in - P_LOAD_W - L["P_loss_w"]) / p_in}
    L["fixed_point_history"] = hist
    return L


# ---------------------------------------------------------------------------
# the ALTERNATIVE LV geometry, quantified rather than asserted
# ---------------------------------------------------------------------------
LV_ALT_T_CU_M, LV_ALT_OCC = 10e-6, 0.80     # a 10 um power plane, declared


@lru_cache(maxsize=2)
def lv_alternative_r_ohm(level=2):
    """If the 1 V pad field were spread over the WHOLE cell pitch instead of the tile,
    the package would have to carry each cell's current laterally from the VOUT tile
    to the pitch boundary. Periodic unit cell (Neumann edges = symmetry), tile held
    through rho_c, uniform areal draw. Returns R per cell at 20 C."""
    import pkg_rdl_refined as RF
    import physical_coords as PCO
    import routing as RT
    from interconnect import rho_cu
    import scipy.sparse as sp
    import scipy.sparse.linalg as spla
    cells = (PCO.physical_cell_coordinates() if Z1D.is_default()
             else Z1D.cell_coordinates())
    xs = sorted({round(x, 6) for x, _ in cells})
    p = xs[1] - xs[0]
    s = routing_design()["tile_side_mm"]
    h_fine, h_coarse = RF.LEVELS[level]
    fx = RF.axis_faces(-p / 2, p / 2, [-s / 2, s / 2], [], h_fine / 2, h_coarse / 2)
    sh = RF.RefinedSheet(fx, fx, rho_cu(20.0) / (LV_ALT_T_CU_M * LV_ALT_OCC))
    G = sh.laplacian().tolil()
    area = np.outer(sh.dx, sh.dy).ravel()
    rhs = -area / area.sum()                         # 1 A drawn uniformly
    tile = np.array([abs(sh.cx[i]) < s / 2 and abs(sh.cy[j]) < s / 2
                     for i in range(sh.nx) for j in range(sh.ny)])
    rho_c = 1e-5
    g_t = np.where(tile, area / rho_c, 0.0)          # tile -> source node at V = 0
    A = G.tocsr() + sp.diags(g_t)
    V = spla.spsolve(A.tocsc(), rhs)
    Lp = sh.laplacian().tocoo()
    up = Lp.row < Lp.col
    p_sheet = float(np.sum(-Lp.data[up] * (V[Lp.row[up]] - V[Lp.col[up]]) ** 2))
    p_cont = float(np.sum(g_t * V ** 2))
    return p_sheet + p_cont


def lv_alternative_loss_w(t_c):
    import rms_currents as RMS
    i = RMS.cell_currents()["i_cell_out_rms_a"]
    return 2 * N_VR * i ** 2 * lv_alternative_r_ohm() * rho_ratio_cu(t_c)
