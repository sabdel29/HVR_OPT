#!/usr/bin/env python3
"""Phase-0M-R Section 6/7 -- intra-VR routing, TEMPLATE-AWARE, in the production total.

PHASE-0M CLAIM UNDER TEST
    "intra-VR routing is common-mode across Z1, Z2 and Z4"
That was true only because all three architectures instantiated the SAME component-level
layout. Once components are split across tiers by a partition template, the via-stack
heights, the lateral runs and the rail that crosses each tier boundary all change. The claim
is therefore RE-TESTED per template here rather than carried forward.

NO DOUBLE COUNTING. The upstream converter model owns `R_DS(on)`, the inductor DCR, the
capacitor ESR and all switching loss. This module owns ONLY the metal between components,
and every edge it produces is registered in the ledger under `P_intraVR_metal` or
`P_intraVR_vertical`, each of which has exactly one writer.
"""
from __future__ import annotations
import csv, math, sys
from dataclasses import dataclass
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for d in ("phase0mr", "phase0m", "phase0e", "phase0dr"):
    sys.path.insert(0, str(R / "scripts" / d))
from interconnect import rho_cu                                            # noqa: E402
import routing as RT0                                                      # noqa: E402

OUT = R / "results" / "phase0mr"
OUT.mkdir(parents=True, exist_ok=True)

# sourced component heights (Phase 0H datasheets; Phase-0I inductor library)
# Heights: GaN from the Phase-0H datasheets, inductor from the Phase-0I library, MLCC at
# the project's own NOMINAL (100 um). Phase 0H's embedded cell of 1226 um is
# 500 + 606 + 100 + 2x10, which only reproduces with the nominal; 250 um is the upper bound
# of the sourced envelope and is carried as a sensitivity, not as the default.
H_UM = {"gan_hs": 685.0, "gan_ls": 606.0, "cap_fly": 100.0, "cap_out": 100.0,
        "inductor": 500.0}
H_UM_MLCC_UPPER = 250.0
FOOT_MM2 = {"gan_hs": 1.87, "gan_ls": 1.80, "cap_fly": 2.00, "cap_out": 2.00,
            "inductor": 1.00}
RDL_UM = 10.0                       # interlayer RDL, ECTC-2024 Table I
DESIGN = RT0.DESIGN

# Templates as ORDERED TIERS. Each tier is a list of component classes sharing a level; the
# tier order is bottom-to-top and the z-gap between tiers is set by the tallest component in
# the lower tier plus one interlayer RDL.
TEMPLATES = {
    # The output capacitor belongs with the OUTPUT, not with the flying capacitors. Phase 0M
    # grouped them, which alone pushed the capacitor tier to 6.00 mm2 against a 5.61 mm2
    # tile and would have failed the area check for a reason that is a bookkeeping choice.
    "T1_EMBEDDED_4LAYER": [["gan_hs"], ["gan_ls"], ["cap_fly"], ["inductor", "cap_out"]],
    "T4_SPLIT_SC_BUCK": [["gan_hs", "cap_fly"], ["gan_ls", "inductor", "cap_out"]],
    "T2_BACKSIDE_CHIPLET": [["gan_hs", "gan_ls"], ["cap_fly"], ["inductor", "cap_out"]],
    "T0_SINGLE_LEVEL": [["gan_hs", "gan_ls", "cap_fly", "cap_out", "inductor"]],
    # PHASE 0M-R3C. A pure REORDERING of T1_EMBEDDED_4LAYER: the same five component
    # classes, the same per-tier areas, the same 1921 um stack. Only gan_ls and cap_fly
    # swap tiers, which puts the low-side switch adjacent to the inductor so the 20.408 A
    # switch node no longer crosses a component tier. It keeps both ends the June-2026
    # source fixes: gan_hs flip-chipped at the bottom, inductors at the top near the POL.
    "T1C_REORDERED": [["gan_hs"], ["cap_fly"], ["gan_ls"], ["inductor", "cap_out"]],
}


def tier_of(template: str, comp: str) -> int:
    for i, tier in enumerate(TEMPLATES[template]):
        if comp in tier:
            return i
    raise KeyError(f"{comp} not placed in {template}")


def tier_z(template: str) -> list[float]:
    """Mid-plane z of each tier, in um, bottom-to-top."""
    z, out = 0.0, []
    for tier in TEMPLATES[template]:
        h = max(H_UM[c] for c in tier)
        out.append(z + h / 2.0)
        z += h + RDL_UM
    return out


def tier_footprint_mm2(template: str, tier: int, n_of: dict) -> float:
    return sum(FOOT_MM2[c] * n_of[c] for c in TEMPLATES[template][tier])


@dataclass
class Edge:
    name: str
    src: str
    dst: str
    rail: str
    i_dc: float
    i_rms: float
    geom: str            # "lateral" | "vertical"
    length_mm: float
    tiers: tuple


def build_edges(template: str, d: dict = DESIGN) -> list[Edge]:
    """Component-terminal graph for one VR cell under one partition template."""
    N, K = d["N"], d["K"]
    i_out = d["i_out_per_vr_a"]
    p_conv = d["p_conv_total_w"] / d["n_vr"]
    p_in = d["v_out"] * i_out + p_conv
    i_in = p_in / d["v_in"]
    v_mid = d["v_in"] / N
    i_mid = p_in / v_mid
    i_ph = i_out / K
    i_cap = i_mid / math.sqrt(2)
    n_of = {"gan_hs": N, "gan_ls": K, "cap_fly": N - 1, "cap_out": 1, "inductor": K}
    zs = tier_z(template)
    side = d["tile_side_mm"]

    def z_of(c):
        return zs[tier_of(template, c)]

    # PHASE 0M-R3B, DEFECT #62. z_of() returns a tier MID-PLANE, so a vertical link was
    # measured centre-of-component to centre-of-component -- straight through the body of
    # the GaN die at one end and the inductor at the other. Components are contacted at
    # their terminal faces, so the build-up a via chain actually crosses is the gap
    # BETWEEN them. Opt-in, because turning it on changes every prior vertical loss:
    # PHASE0MR3B_PHYSICAL_SPANS=1.
    import os as _os2
    _phys_spans = _os2.environ.get("PHASE0MR3B_PHYSICAL_SPANS", "0") == "1"
    _ext, _z = [], 0.0
    for _tier in TEMPLATES[template]:
        _h = max(H_UM[c] for c in _tier)
        _ext.append((_z, _z + _h)); _z += _h + RDL_UM

    def link(name, a, b, rail, idc, irms):
        ta, tb = tier_of(template, a), tier_of(template, b)
        if ta == tb:
            # same level: a lateral run of order one third of the tile, obstacle-aware
            return Edge(name, a, b, rail, idc, irms, "lateral", side / 3.0, (ta, tb))
        if _phys_spans:
            lo, hi = min(ta, tb), max(ta, tb)
            span_um = _ext[hi][0] - _ext[lo][1]       # top face of lower -> bottom of upper
        else:
            span_um = abs(z_of(b) - z_of(a))
        return Edge(name, a, b, rail, idc, irms, "vertical", span_um * 1e-3, (ta, tb))

    E = [Edge("vin_bus", "pad_in", "gan_hs", "HV", i_in, i_in, "lateral",
              side * 0.7, (tier_of(template, "gan_hs"),) * 2)]
    E.append(link("hs_to_cf", "gan_hs", "cap_fly", "SC", 0.0, i_cap))
    E.append(link("hs_to_ls", "gan_hs", "gan_ls", "MID", i_mid, i_mid))
    E.append(link("ls_to_L", "gan_ls", "inductor", "SW", i_out, i_out))
    E.append(link("L_to_cout", "inductor", "cap_out", "LV", i_out, i_out))
    E.append(Edge("vout_plane", "cap_out", "pad_out", "LV", i_out, i_out, "lateral",
                  side / 3.0, (tier_of(template, "cap_out"),) * 2))
    return E


def edge_loss(e: Edge, t_cu_m: float, n_layers: int, j_max: float, tile_side_mm: float,
              t_c: float, via_policy: str, r_via_m: float | None = None,
              pitch_m: float | None = None, t_liner_m: float = 0.5e-6,
              footprint_mm2: float = 1.8) -> dict:
    # PHASE 0M-R3. The intra-VR via geometry is the one repair the realizability search
    # applied: r = 20 um at the framework's own legal pitch, inside the sourced range
    # design_variables.tsv.radius_m = {lo 2.5, nominal 15, hi 50} um. Defaults stay at the
    # Phase-0M values so nothing changes unless the repair is explicitly requested.
    import os as _os
    if r_via_m is None:
        r_via_m = float(_os.environ.get("PHASE0MR3_R_VIA_UM", 15.0)) * 1e-6
    if pitch_m is None:
        pitch_m = float(_os.environ.get("PHASE0MR3_VIA_PITCH_UM", 60.0)) * 1e-6
    rho = rho_cu(t_c)
    if e.geom == "lateral":
        avail = tile_side_mm * 1e-3
        w_req = e.i_rms / max(j_max * t_cu_m * n_layers, 1e-30)
        w = min(w_req, avail)
        r = rho * (e.length_mm * 1e-3) / max(n_layers * w * t_cu_m, 1e-30)
        return {"R_ohm": r, "width_um": w * 1e6, "w_required_um": w_req * 1e6,
                "feasible": w_req <= avail, "shortfall_x": w_req / avail,
                "n_via": None}
    a_c = math.pi * max(r_via_m - t_liner_m, 1e-12) ** 2
    n_req = max(1, math.ceil(e.i_rms / (j_max * a_c)))
    n_av = max(1, int(footprint_mm2 * 1e-6 * 0.5 / pitch_m ** 2))
    n = n_req if via_policy == "A_min_capability" else min(max(n_av, n_req), n_av)
    r = rho * (e.length_mm * 1e-3) / (a_c * n)
    return {"R_ohm": r, "width_um": float("nan"), "w_required_um": float("nan"),
            "feasible": n_req <= n_av, "shortfall_x": n_req / max(n_av, 1), "n_via": n}


def template_loss(template: str, t_cu_m: float = 10e-6, n_layers: int = 9,
                  j_max: float = 1.0e8, via_policy: str = "D_area_optimal",
                  t_c: float = 85.0, d: dict = DESIGN) -> dict:
    edges = build_edges(template, d)
    rows, p_lat, p_vert, infeas = [], 0.0, 0.0, []
    for e in edges:
        s = edge_loss(e, t_cu_m, n_layers, j_max, d["tile_side_mm"], t_c, via_policy)
        p = e.i_rms ** 2 * s["R_ohm"]
        if e.geom == "lateral":
            p_lat += p
        else:
            p_vert += p
        if not s["feasible"]:
            infeas.append(f"{e.name} x{s['shortfall_x']:.1f}")
        rows.append({"template": template, "edge": e.name, "rail": e.rail,
                     "geom": e.geom, "tier_from": e.tiers[0], "tier_to": e.tiers[-1],
                     "length_mm": e.length_mm, "i_rms_a": e.i_rms, "i_dc_a": e.i_dc,
                     "R_mohm": s["R_ohm"] * 1e3, "P_w_per_vr": p,
                     "width_um": s["width_um"], "n_via": s["n_via"],
                     "feasible": s["feasible"], "t_cu_um": t_cu_m * 1e6,
                     "n_layers": n_layers, "j_max": j_max, "via_policy": via_policy})
    n_vr = d["n_vr"]
    return {"template": template, "n_tiers": len(TEMPLATES[template]),
            "stack_height_um": sum(max(H_UM[c] for c in t) for t in TEMPLATES[template])
                               + RDL_UM * (len(TEMPLATES[template]) - 1),
            "p_lateral_per_vr_w": p_lat, "p_vertical_per_vr_w": p_vert,
            "p_intra_vr_per_vr_w": p_lat + p_vert,
            "P_intraVR_metal_system_w": p_lat * n_vr,
            "P_intraVR_vertical_system_w": p_vert * n_vr,
            "p_system_w": (p_lat + p_vert) * n_vr,
            "pct_of_load": 100 * (p_lat + p_vert) * n_vr / 1000.0,
            "n_infeasible": len(infeas), "infeasible": "; ".join(infeas),
            "t_cu_um": t_cu_m * 1e6, "n_layers": n_layers, "via_policy": via_policy,
            "edges": rows}


def main() -> int:
    summ, alled = [], []
    for tpl in TEMPLATES:
        for nl, t in ((1, 10e-6), (2, 10e-6), (9, 10e-6), (1, 20e-6), (1, 40e-6)):
            for pol in ("A_min_capability", "D_area_optimal"):
                r = template_loss(tpl, t_cu_m=t, n_layers=nl, via_policy=pol)
                alled += r.pop("edges")
                summ.append(r)
    with open(OUT / "intravr_routing_by_template.csv", "w", newline="") as fh:
        k = sorted({x for r in summ for x in r})
        w = csv.DictWriter(fh, fieldnames=k); w.writeheader(); w.writerows(summ)
    with open(OUT / "intravr_routing_edges.csv", "w", newline="") as fh:
        k = sorted({x for r in alled for x in r})
        w = csv.DictWriter(fh, fieldnames=k); w.writeheader(); w.writerows(alled)
    ref = [r for r in summ if r["n_layers"] == 9 and r["t_cu_um"] == 10.0
           and r["via_policy"] == "D_area_optimal"]
    print("  reference stack (10 um x 9 layers, area-optimal vias):")
    for r in sorted(ref, key=lambda r: r["template"]):
        print(f"    {r['template']:22s} tiers={r['n_tiers']} h={r['stack_height_um']:7.1f}um "
              f"lat={r['p_lateral_per_vr_w']:.5f} vert={r['p_vertical_per_vr_w']:.5f} "
              f"sys={r['p_system_w']:7.3f} W ({r['pct_of_load']:.2f} %) "
              f"infeas={r['n_infeasible']}")
    p = [r["p_system_w"] for r in ref]
    print(f"\n  spread across templates at the same stack: "
          f"{min(p):.3f} to {max(p):.3f} W, {100*(max(p)-min(p))/min(p):.1f} %")
    print(f"wrote {OUT/'intravr_routing_by_template.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
