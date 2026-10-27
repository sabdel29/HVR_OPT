#!/usr/bin/env python3
"""Phase-0M Parts 10-13 -- routing scope audit and the intra-VR routing model.

THREE LEVELS, AND ONLY TWO OF THEM EXIST TODAY
  LEVEL 1  INTRA-CONVERTER: input pads -> GaN switches <-> flying caps -> intermediate
           rail -> buck switches -> inductors -> output caps -> output pads.
           **ABSENT from the current framework.**
  LEVEL 2  VR-TO-PACKAGE: VR terminal -> TSV field / RDL / bump array / die terminal.
           Present: the vertical tiers in zpower.evaluate_z.
  LEVEL 3  PACKAGE-TO-POL: VR outputs -> load regions.
           Present: rdl_network_solve, a multilayer resistive sheet.

NOT DOUBLE-COUNTED. The upstream converter loss model
(`Scalable_Integrated_VR/src/HVR_FULL_OPT_*::compute_total_loss`) already contains
`hs.R_DS_ON`, `ls.R_DS_ON`, the inductor DCR `R_L_ESR` and the capacitor `R_C_ESR`, plus
hard-switching, gate-drive and C_OSS losses. It contains NO metallization between the
components. This module adds only that metallization.

FIDELITY LADDER (Part 12)
  R0  Manhattan length between terminal centres, width from the current-density rule
  R1  obstacle-aware Manhattan: components are blockages, routes detour around them
  R2  2-D resistive sheet over the tile with FINITE terminal footprints
  R3  3-D extraction of one critical transition (the crowding module, Part 8)
The cheapest level that reproduces R2 is what the eventual optimizer should use.
"""
from __future__ import annotations
import csv, itertools, math, sys
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parents[2]
for d in ("phase0m", "phase0e", "phase0dr"):
    sys.path.insert(0, str(R / "scripts" / d))
from interconnect import rho_cu                                            # noqa: E402
from stack import multilayer_sheet_solve                                   # noqa: E402

OUT = R / "results" / "phase0m"
OUT.mkdir(parents=True, exist_ok=True)

# ---- the compiled 1 kW design (scripts/phase0f/kw1.py::design_1kw) ----------------------
DESIGN = dict(label="N3K3KA2_J3.5", N=3, K=3, K_A=2, f_sw_hz=805170.3343770515,
              i_out_per_vr_a=1000.0 / 49, v_in=48.0, v_out=1.0, n_vr=49,
              tile_side_mm=2.3685438564654024, p_conv_total_w=125.26443889730017,
              hs_part="EPC2014C", hs_footprint_mm2=1.87, hs_rdson_ohm=0.016,
              ind_l_nh=250, ind_dcr_mohm=1.6, ind_footprint_mm2=1.0, ind_h_um=500,
              cap_uf=10.0, cap_esr_mohm=2.5, cap_esl_ph=400.0, cap_footprint_mm2=2.0)

T_C = 85.0
J_RDL_A_PER_M2 = 1.0e10     # 10 kA/mm^2 -- see note in ROUTING_SCOPE_AUDIT.md


@dataclass
class Comp:
    name: str
    x_mm: float
    y_mm: float
    z_um: float
    w_mm: float
    h_mm: float
    layer: str
    kind: str
    column: int = -1

    def blocks(self, layer: str) -> bool:
        return layer == self.layer


@dataclass
class Net:
    name: str
    src: str
    dst: str
    i_dc_a: float
    i_rms_a: float
    rail: str
    geom: str            # "lateral" or "vertical"
    layer: str = ""
    note: str = ""


# Layer z-positions for the Z1 EMBEDDED assignment (June-2026 Sec. II, heights sourced in
# Phase 0H). z = 0 is the substrate underside; the HS device is flip-chipped BELOW it.
LAYER_Z_UM = {"HS_RDL": -685.0 / 2, "PL1": 606.0 / 2, "PL2": 616.0 + 125.0,
              "PL3": 616.0 + 250.0 + 10.0 + 250.0}
INTERLAYER_RDL_UM = 10.0


def tile_layout(side_mm: float, d: dict = DESIGN) -> list[Comp]:
    """PER-PHASE STACKED COLUMNS, not a planar grid.

    The first version of this layout put every component side by side inside its own layer
    and routed laterally between them. That is the wrong topology for a vertically
    integrated VR and it returned 61 % of the load in intra-VR routing, because it forced
    a 6.8 A phase current down a 0.8 mm lateral trace that does not exist in the real
    device. In the embedded architecture the low-side switch, its flying capacitor and its
    inductor sit in DIFFERENT power layers at the SAME footprint, so the phase connection
    is a via stack a few hundred micrometres long, not a millimetre of trace.

    The footprint arithmetic confirms the column reading: the compiled design reports
    total_area = 5.61 mm^2 = 3 x 1.87 mm^2 = K x (one HS footprint), and the tile is
    2.3685 mm square = 5.61 mm^2. The area budget is ONE column per phase, and the
    passives are stacked inside that column's shadow -- they cannot be beside it.
    """
    K, N = d["K"], d["N"]
    s = side_mm
    col_w = s / K
    a_hs = math.sqrt(d["hs_footprint_mm2"])
    a_ind = math.sqrt(d["ind_footprint_mm2"])
    a_cap = math.sqrt(d["cap_footprint_mm2"])
    out: list[Comp] = []
    for k in range(K):
        x = (k + 0.5) * col_w - s / 2
        out.append(Comp(f"HS{k}", x, 0.0, LAYER_Z_UM["HS_RDL"], min(a_hs, col_w),
                        a_hs, "HS_RDL", "gan_hs", k))
        out.append(Comp(f"LS{k}", x, 0.0, LAYER_Z_UM["PL1"], min(a_hs, col_w),
                        a_hs, "PL1", "gan_ls", k))
        out.append(Comp(f"L{k}", x, 0.0, LAYER_Z_UM["PL3"], min(a_ind, col_w),
                        a_ind, "PL3", "inductor", k))
    for j in range(N - 1):
        x = (j + 0.5) * s / (N - 1) - s / 2
        out.append(Comp(f"CF{j}", x, 0.0, LAYER_Z_UM["PL2"], min(a_cap, s / (N - 1)),
                        a_cap, "PL2", "cap_fly", -1))
    out.append(Comp("COUT", 0.0, 0.35 * s, LAYER_Z_UM["PL2"], a_cap, a_cap,
                    "PL2", "cap_out", -1))
    out.append(Comp("VIN", -0.45 * s, -0.45 * s, LAYER_Z_UM["HS_RDL"], 0.2, 0.2,
                    "HS_RDL", "pad_in", -1))
    out.append(Comp("VOUT", 0.0, 0.0, LAYER_Z_UM["PL3"] + 250.0, s, s,
                    "PL3", "pad_out", -1))
    return out


def nets(d: dict = DESIGN) -> list[Net]:
    """Every metallization edge, with the current it carries and whether it is a lateral
    run in one layer or a vertical via stack between layers.

    Rail currents: V_mid = V_in / N (the SC ratio). I_in = P_in / V_in with
    P_in = V_out I_out + P_conv per cell. Each of the K phases carries I_out / K.
    """
    N, K = d["N"], d["K"]
    i_out = d["i_out_per_vr_a"]
    p_conv = d["p_conv_total_w"] / d["n_vr"]
    p_in = d["v_out"] * i_out + p_conv
    i_in = p_in / d["v_in"]
    v_mid = d["v_in"] / N
    i_mid = p_in / v_mid
    i_ph = i_out / K
    i_cap_rms = i_mid / math.sqrt(2)
    out = [Net(f"vin_to_hs{k}", "VIN", f"HS{k}", i_in / N, i_in / N, "HV",
               "lateral", "HS_RDL") for k in range(N)]
    out += [Net(f"hs{k}_to_cf", f"HS{k}", f"CF{min(k, N - 2)}", 0.0, i_cap_rms, "SC",
                "lateral", "PL2", "flying-capacitor loop: AC only, no DC term")
            for k in range(N)]
    out += [Net(f"hs{k}_to_ls{k}", f"HS{k}", f"LS{k}", i_mid / N, i_mid / N, "MID",
                "vertical") for k in range(N)]
    out += [Net(f"ls{k}_to_L{k}", f"LS{k}", f"L{k}", i_ph, i_ph, "SW", "vertical")
            for k in range(K)]
    out += [Net(f"L{k}_to_vout", f"L{k}", "VOUT", i_ph, i_ph, "LV", "vertical")
            for k in range(K)]
    out += [Net("vout_plane", "VOUT", "VOUT", i_out, i_out, "LV", "lateral", "PL3",
                "output plane spreading across the tile")]
    return out


def manhattan(a: Comp, b: Comp) -> float:
    return abs(a.x_mm - b.x_mm) + abs(a.y_mm - b.y_mm)


def obstacle_manhattan(a: Comp, b: Comp, comps: list[Comp], layer: str,
                       margin_mm: float = 0.02) -> float:
    """Obstacle-aware Manhattan length (level R1).

    THE DEFECT THIS REPLACES. The previous implementation tested blockage with
    each component's EXTENT but then sized the detour by looking for blocking
    components whose CENTRE fell inside the route bounding box. A component can
    straddle a route without its centre lying inside that box, so the function
    could detect that both L-corners were blocked and still return the plain
    Manhattan length. Across all 28 parameter combinations every one of the 16
    nets came out numerically identical to R0, so R1 supplied no fidelity
    evidence at all while being advertised as a distinct level.

    The replacement uses ONE geometric test for both decisions. If either
    L-shaped route is clear the length is Manhattan. Otherwise a Z-route with a
    single offset leg is tried, with candidate offsets taken from the blockers'
    own edges, and the shortest clear one is returned. A Z-route through an
    offset that lies between the endpoints costs exactly Manhattan; one that
    overshoots costs Manhattan + 2 * overshoot, which is where a real detour
    penalty comes from.
    """
    p, q = (a.x_mm, a.y_mm), (b.x_mm, b.y_mm)
    base = manhattan(a, b)

    def contains(c, pt):
        return (abs(pt[0] - c.x_mm) <= c.w_mm / 2
                and abs(pt[1] - c.y_mm) <= c.h_mm / 2)

    # A component that CONTAINS a terminal is not an obstruction to that route:
    # the route starts inside it. Counting it blocked every segment leaving the
    # terminal and made the net look enclosed. Likewise a self-net (src == dst)
    # is a plane, not a routed segment, and has no Manhattan length to detour.
    blocks = [c for c in comps
              if c.blocks(layer) and c.name not in (a.name, b.name)
              and not contains(c, p) and not contains(c, q)]
    if a.name == b.name or base == 0.0:
        return base

    def seg_clear(p0, p1) -> bool:
        x0, x1 = sorted((p0[0], p1[0]))
        y0, y1 = sorted((p0[1], p1[1]))
        for c in blocks:
            if (x0 - margin_mm <= c.x_mm + c.w_mm / 2
                    and x1 + margin_mm >= c.x_mm - c.w_mm / 2
                    and y0 - margin_mm <= c.y_mm + c.h_mm / 2
                    and y1 + margin_mm >= c.y_mm - c.h_mm / 2):
                return False
        return True

    def path_clear(pts) -> bool:
        return all(seg_clear(pts[i], pts[i + 1]) for i in range(len(pts) - 1))

    for corner in ((q[0], p[1]), (p[0], q[1])):
        if path_clear((p, corner, q)):
            return base

    # Z-routes: offsets drawn from the blockers' edges, same geometry as the test
    best = None
    # 2 * margin, not 1: seg_clear() also relaxes the segment by margin_mm, so
    # an offset placed at exactly edge + margin still tests as touching and no
    # Z-route could ever be found. Verified on a synthetic blocker.
    off = 2.0 * margin_mm
    ys = [c.y_mm + c.h_mm / 2 + off for c in blocks] + \
         [c.y_mm - c.h_mm / 2 - off for c in blocks]
    xs = [c.x_mm + c.w_mm / 2 + off for c in blocks] + \
         [c.x_mm - c.w_mm / 2 - off for c in blocks]
    for y in ys:
        pts = (p, (p[0], y), (q[0], y), q)
        if path_clear(pts):
            L = abs(y - p[1]) + abs(q[0] - p[0]) + abs(q[1] - y)
            best = L if best is None else min(best, L)
    for x in xs:
        pts = (p, (x, p[1]), (x, q[1]), q)
        if path_clear(pts):
            L = abs(x - p[0]) + abs(q[1] - p[1]) + abs(x - q[0])
            best = L if best is None else min(best, L)
    if best is not None:
        return max(best, base)
    # No clear single-offset route. Report the plain Manhattan length rather
    # than infinity -- an unroutable flag belongs in the routability audit, not
    # in a resistance that would poison every downstream loss sum.
    return base


# ---------------------------------------------------------------------------
# segment resistance, derived from geometry under a stated allocation policy
# ---------------------------------------------------------------------------
def lateral_segment(i_rms_a: float, length_mm: float, t_cu_m: float, j_max: float,
                    avail_width_m: float, n_layers: int = 1) -> dict:
    """Width DERIVED from the current-density rule; feasibility reported, never clipped."""
    w_req = i_rms_a / max(j_max * t_cu_m * n_layers, 1e-30)
    w = min(w_req, avail_width_m)
    r = rho_cu(T_C) * (length_mm * 1e-3) / max(n_layers * w * t_cu_m, 1e-30)
    return {"w_required_m": w_req, "w_used_m": w,
            "feasible": w_req <= avail_width_m + 1e-15,
            "width_shortfall_x": w_req / avail_width_m,
            "R_ohm": r, "J_actual": i_rms_a / max(n_layers * w * t_cu_m, 1e-30)}


def vertical_segment(i_rms_a: float, height_um: float, j_max: float,
                     footprint_mm2: float, policy: str, r_via_m: float = 15e-6,
                     pitch_m: float = 60e-6, pg_ratio: float = 0.5,
                     t_liner_m: float = 0.5e-6) -> dict:
    """A via stack between two layers, allocated by an explicit POLICY (Part 3).

    Policy A gives R = rho h J / I exactly -- independent of the via cross-section -- and
    therefore a loss LINEAR in current and in height. Policy D fills the component's own
    footprint with vias and is far cheaper. Which policy the intra-VR links use is a real
    design decision that the current framework never states, because it has no intra-VR
    links at all.
    """
    rho = rho_cu(T_C)
    h = height_um * 1e-6
    a_c = math.pi * max(r_via_m - t_liner_m, 1e-12) ** 2
    n_req = max(1, math.ceil(i_rms_a / (j_max * a_c)))
    n_avail = max(1, int(footprint_mm2 * 1e-6 * pg_ratio / pitch_m ** 2))
    n = n_req if policy == "A_min_capability" else min(max(n_avail, n_req), n_avail)
    r = rho * h / (a_c * n)
    return {"n_required": n_req, "n_available": n_avail, "n_allocated": n,
            "feasible": n_req <= n_avail, "R_ohm": r, "height_um": height_um,
            "policy": policy}


def route_loss(level: str = "R1", t_cu_m: float = 10e-6, j_max: float = 1.0e8,
               via_policy: str = "D_area_optimal", n_layers: int = 1,
               d: dict = DESIGN) -> dict:
    comps = {c.name: c for c in tile_layout(d["tile_side_mm"], d)}
    s_m = d["tile_side_mm"] * 1e-3
    rows, p_tot, p_dc, infeas = [], 0.0, 0.0, []
    for n in nets(d):
        a, b = comps[n.src], comps[n.dst]
        if n.geom == "vertical":
            fp = min(a.w_mm * a.h_mm, b.w_mm * b.h_mm)
            hgt = abs(b.z_um - a.z_um)
            seg = vertical_segment(max(n.i_rms_a, 1e-9), hgt, j_max, fp, via_policy)
            L, wid = hgt * 1e-3, float("nan")
        else:
            L = (manhattan(a, b) if level == "R0"
                 else obstacle_manhattan(a, b, list(comps.values()), n.layer))
            if n.name == "vout_plane":
                L = d["tile_side_mm"] / 3.0        # mean spreading path on the tile
            seg = lateral_segment(max(n.i_rms_a, 1e-9), L, t_cu_m, j_max, s_m, n_layers)
            wid = seg["w_used_m"] * 1e6
        r = seg["R_ohm"]
        p = n.i_rms_a ** 2 * r
        p_tot += p
        p_dc += n.i_dc_a ** 2 * r
        if not seg["feasible"]:
            infeas.append(f"{n.name}: " + (
                f"needs {seg['width_shortfall_x']:.1f}x the available width"
                if n.geom == "lateral" else
                f"needs {seg['n_required']} vias, {seg['n_available']} sites"))
        rows.append({"net": n.name, "src": n.src, "dst": n.dst, "rail": n.rail,
                     "geom": n.geom, "layer": n.layer, "i_dc_a": n.i_dc_a,
                     "i_rms_a": n.i_rms_a, "length_mm": L, "width_um": wid,
                     "R_mohm": r * 1e3, "P_w_per_vr": p, "feasible": seg["feasible"],
                     "level": level, "j_max": j_max, "via_policy": via_policy,
                     "t_cu_um": t_cu_m * 1e6, "n_layers": n_layers, "note": n.note})
    return {"level": level, "t_cu_um": t_cu_m * 1e6, "j_max": j_max,
            "via_policy": via_policy, "n_layers": n_layers,
            "p_intra_vr_w": p_tot, "p_intra_vr_dc_w": p_dc,
            "p_system_w": p_tot * d["n_vr"], "p_system_dc_w": p_dc * d["n_vr"],
            "pct_of_load": 100 * p_tot * d["n_vr"] / 1000.0,
            "pct_of_converter_loss": 100 * p_tot * d["n_vr"] / d["p_conv_total_w"],
            "n_infeasible": len(infeas), "infeasible": "; ".join(infeas),
            "nets": rows}


def r2_sheet(d: dict = DESIGN, t_cu_m: float = 10e-6, n_layers: int = 1,
             grid_n: int = 121) -> dict:
    """R2 -- the output net solved as a 2-D resistive sheet over the tile, with the K
    inductor terminals injecting over their real footprints and the VOUT pad extracting."""
    comps = {c.name: c for c in tile_layout(d["tile_side_mm"], d)}
    s = d["tile_side_mm"]
    i_out, K = d["i_out_per_vr_a"], d["K"]
    sigma_s = n_layers * t_cu_m / rho_cu(T_C)          # a PLANE: occupancy 1
    src = [(comps[f"L{k}"].x_mm, comps[f"L{k}"].y_mm) for k in range(K)]
    out = multilayer_sheet_solve([sigma_s], src, [i_out / K] * K,
                                 [(0.0, 0.45 * s)], [i_out], span_mm=s, n=grid_n,
                                 src_size_mm=math.sqrt(d["ind_footprint_mm2"]),
                                 load_size_mm=0.4 * s,
                                 ground_xy=(0.0, 0.45 * s), ground_size_mm=0.4 * s)
    return {"level": "R2", "t_cu_um": t_cu_m * 1e6, "n_layers": n_layers,
            "sigma_s_S": sigma_s, "p_output_net_w_per_vr": out["p_w"],
            "p_system_w": out["p_w"] * d["n_vr"],
            "pct_of_load": 100 * out["p_w"] * d["n_vr"] / 1000.0,
            "balance_err_pct": out["balance_err_pct"], "grid_n": grid_n}


# ---------------------------------------------------------------------------
# Part 10/11 -- the sweep, the scope audit and the ranking question
# ---------------------------------------------------------------------------
def sweep() -> tuple[list[dict], list[dict]]:
    summ, nets_rows = [], []
    for level in ("R0", "R1"):
        for j in (1.0e8, 4.0e8):
            for pol in ("A_min_capability", "D_area_optimal"):
                for t_um, nl in ((10.0, 1), (10.0, 2), (10.0, 4), (10.0, 9),
                                 (20.0, 1), (40.0, 1), (5.0, 1)):
                    r = route_loss(level, t_cu_m=t_um * 1e-6, j_max=j,
                                   via_policy=pol, n_layers=nl)
                    nets_rows += r.pop("nets")
                    summ.append(r)
    for nl in (1, 2, 4, 9):
        for t_um in (5.0, 10.0, 20.0, 40.0):
            summ.append(r2_sheet(t_cu_m=t_um * 1e-6, n_layers=nl))
    return summ, nets_rows


def ranking_effect(d: dict = DESIGN) -> dict:
    """Does intra-VR routing change the Z1 / Z2 / Z4 ranking?

    The converter CELL is identical in all three architectures -- the same compiled
    N3K3KA2 design with the same component heights -- so the intra-VR metallization is the
    same absolute loss in each. It shifts every architecture's total by the same amount and
    cannot reorder them. What it CAN do is change the temperature, which feeds the
    mechanics; that second-order path is quantified here rather than dismissed.
    """
    base = route_loss("R1", j_max=1.0e8, via_policy="D_area_optimal", n_layers=9)
    p_extra = base["p_system_w"]
    # Phase-0I system totals at h_sub = 0.30 mm (Z2, Z4) and 1.30 mm (Z1)
    tot = {"Z1": 126.089845025657, "Z2": 127.77795736640536, "Z4": 126.4}
    out = {"p_intra_vr_system_w": p_extra}
    for k, v in tot.items():
        out[f"{k}_before_w"] = v
        out[f"{k}_after_w"] = v + p_extra
    out["delta_gap_Z2_minus_Z1_before_w"] = tot["Z2"] - tot["Z1"]
    out["delta_gap_Z2_minus_Z1_after_w"] = tot["Z2"] - tot["Z1"]
    out["ordering_changed"] = False
    out["reason"] = ("the converter cell is identical across Z1, Z2 and Z4, so the "
                     "intra-VR metallization is a common additive term; it moves every "
                     "total by the same watts and the electrical ordering is unchanged")
    # thermal second-order path
    out["extra_heat_frac_of_load"] = p_extra / 1000.0
    out["extra_heat_frac_of_existing_loss"] = p_extra / d["p_conv_total_w"]
    return out


def main() -> int:
    summ, nets_rows = sweep()
    keys = sorted({k for r in summ for k in r})
    with open(OUT / "intra_vr_routing_model.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(summ)
    keys2 = sorted({k for r in nets_rows for k in r})
    with open(OUT / "intra_vr_routing_nets.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys2); w.writeheader(); w.writerows(nets_rows)
    re_ = ranking_effect()
    with open(OUT / "intra_vr_ranking_effect.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(re_)); w.writeheader(); w.writerow(re_)
    r1 = [r for r in summ if r.get("level") == "R1"]
    print(f"{len(summ)} configurations")
    print(f"intra-VR system loss spans {min(r['p_system_w'] for r in r1):.2f} to "
          f"{max(r['p_system_w'] for r in r1):.2f} W "
          f"({min(r['pct_of_load'] for r in r1):.2f} to "
          f"{max(r['pct_of_load'] for r in r1):.2f} % of load)")
    print(f"ranking changed: {re_['ordering_changed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
