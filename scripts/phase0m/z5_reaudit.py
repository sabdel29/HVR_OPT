#!/usr/bin/env python3
"""Phase-0M Parts 17-19 -- Z5 re-audit from first principles, and the Z5 FAMILY.

Phase 0I reported ~768 W of RDL loss for ARCH_Z5_2P5D_LATERAL and read it as pricing 2.5D.
Phase 0I-R narrowed that to the tested LOW-VOLTAGE-LATERAL topology. Phase 0M neither
preserves nor withdraws the number: it traces the code path that produces it, states the
implied equivalent loop resistance, checks every parameter against interposer rather than
PCB geometry, and then evaluates a family of lateral architectures at different rail
voltages to locate the crossover.
"""
from __future__ import annotations
import csv, json, math, sys
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parents[2]
for d in ("phase0m", "phase0i", "phase0f", "phase0e", "phase0dr", "phase0b", "phase0d"):
    sys.path.insert(0, str(R / "scripts" / d))
from stack import stacks_from_cfg, rdl_network_solve, rho_cu               # noqa: E402
from architecture0e import pol_grid                                        # noqa: E402

OUT = R / "results" / "phase0m"
OUT.mkdir(parents=True, exist_ok=True)

DIE_MM = 22.36
NPOL = 10
GRID_N = 161
T_C = 85.0
LOAD_W = 1000.0
HVR_AREA_MM2 = 274.89
N_SRC = 49
GAP_MM = 2.0


def z5_geometry(lateral_gap_mm: float = GAP_MM, hvr_area_mm2: float = HVR_AREA_MM2,
                n_src: int = N_SRC):
    """Reproduce zpower.evaluate_z's Z5 source placement exactly."""
    tile = math.sqrt(hvr_area_mm2 / n_src)
    span = DIE_MM + 2 * (lateral_gap_mm + tile * 3.5)
    xs = -(DIE_MM / 2 + lateral_gap_mm + tile / 2)
    src = [(xs, (k + .5) / n_src * DIE_MM - DIE_MM / 2) for k in range(n_src)]
    return src, span, tile, xs


def trace_z5(stack_name: str = "ectc2024_primary", i_lat_a: float = 1000.0,
             lateral_gap_mm: float = GAP_MM, t_c: float = T_C,
             grid_n: int = GRID_N) -> dict:
    """The full chain: rail current -> geometry -> sheet conductance -> R_eq -> P."""
    stack = stacks_from_cfg()[stack_name]
    src, span, tile, xs = z5_geometry(lateral_gap_mm)
    pol = pol_grid()
    sol = rdl_network_solve(stack, src, [i_lat_a / len(src)] * len(src), pol,
                            [i_lat_a / len(pol)] * len(pol), span_mm=span, T_c=t_c,
                            n=grid_n, src_size_mm=tile, load_size_mm=DIE_MM / NPOL,
                            ground_xy=pol[len(pol) // 2], ground_size_mm=DIE_MM / NPOL)
    p = sol["p_loop_w"]
    r_eq = p / i_lat_a ** 2
    rs_v = stack.r_sheet_net("vdd", t_c)
    rs_g = stack.r_sheet_net("gnd", t_c)
    rs_loop = rs_v + rs_g
    return {"stack": stack_name, "i_lateral_a": i_lat_a, "T_c": t_c,
            "t_cu_um": stack.t_cu_m * 1e6, "width_um": (stack.width_m or 0) * 1e6,
            "space_um": (stack.space_m or 0) * 1e6, "occupancy": stack.occupancy,
            "n_vdd": stack.n_vdd, "n_gnd": stack.n_gnd,
            "rho_at_T_ohm_m": rho_cu(t_c),
            "sheet_R_vdd_mohm_sq": rs_v * 1e3, "sheet_R_gnd_mohm_sq": rs_g * 1e3,
            "sheet_R_loop_mohm_sq": rs_loop * 1e3,
            "source_x_mm": xs, "source_to_die_edge_mm": abs(xs) - DIE_MM / 2,
            "span_mm": span, "tile_side_mm": tile, "n_sources": len(src),
            "P_vdd_w": sol["p_vdd_w"], "P_gnd_w": sol["p_gnd_w"], "P_loop_w": p,
            "R_eq_mohm": r_eq * 1e3,
            "loop_squares": r_eq / rs_loop,
            "IR_drop_v": i_lat_a * r_eq,
            "grid_n": grid_n, "balance_err_pct": sol["vdd"]["balance_err_pct"]}


# ---------------------------------------------------------------------------
# Part 18 -- PCB versus interposer/RDL, parameter by parameter
# ---------------------------------------------------------------------------
PCB_ROW = {"source": "ECTC-2024 Table I, PCB row", "t_cu_um": 152.0, "width_um": 32.0,
           "space_um": 32.0, "n_per_net": 1, "rho_20c": 17.0e-9,
           "route_mm": "board-scale, tens of mm"}
RDL_ROW = {"source": "ECTC-2024 Table I, RDL row", "t_cu_um": 10.0, "width_um": 10.0,
           "space_um": 2.0, "n_per_net": 2, "rho_20c": 17.0e-9,
           "route_mm": "package-scale, a few mm"}


def pcb_vs_rdl(t_c: float = T_C) -> list[dict]:
    rows = []
    for tag, d in (("PCB", PCB_ROW), ("RDL", RDL_ROW)):
        occ = d["width_um"] / (d["width_um"] + d["space_um"])
        sig = d["n_per_net"] * d["t_cu_um"] * 1e-6 * occ / rho_cu(t_c)
        rows.append({"path": tag, **d, "occupancy": occ,
                     "sheet_conductance_S_per_sq": sig,
                     "sheet_R_mohm_per_sq": 1e3 / sig,
                     "loop_R_mohm_per_sq": 2e3 / sig})
    return rows


# ---------------------------------------------------------------------------
# Part 19 -- the Z5 architecture FAMILY
# ---------------------------------------------------------------------------
def stage_loss(v_in: float, v_out: float, i_out_total_a: float, n_cells: int = 49) -> dict:
    """Loss of ONE conversion stage, from the SAME upstream loss model the rest of the
    project uses -- never an assumed efficiency."""
    sys.path.insert(0, str(R / "scripts" / "phase0f"))
    from electrical import compile_hvr
    import kw1
    if abs(v_in - v_out) < 1e-9:
        return {"v_in": v_in, "v_out": v_out, "status": "NO STAGE NEEDED",
                "p_conv_total_w": 0.0}
    fit, _ = kw1.fitting_inductors(1.5, "nominal")
    d = compile_hvr(i_out_total_a / n_cells, 3.5, v_in=v_in, v_out=v_out,
                    inductor_library=fit)
    if d is None:
        return {"v_in": v_in, "v_out": v_out, "status": "NO FEASIBLE CONVERTER",
                "p_conv_total_w": None}
    p = d.loss_at(85.0)["p_conv_w"] * n_cells
    return {"v_in": v_in, "v_out": v_out, "status": "OK", "label": d.label,
            "p_conv_total_w": p, "efficiency_pct": 100 * (v_out * i_out_total_a)
            / (v_out * i_out_total_a + p),
            "f_sw_mhz": d.f_sw_hz / 1e6, "area_mm2_total": d.area_mm2 * n_cells}


def second_stage_efficiency(v_in: float, v_out: float = 1.0) -> dict:
    return stage_loss(v_in, v_out, LOAD_W / 1.0)


def trace_z5_clustered(n_edges: int, i_lat_a: float, lateral_gap_mm: float = GAP_MM,
                       stack_name: str = "ectc2024_primary", t_c: float = T_C,
                       grid_n: int = GRID_N) -> dict:
    """Z5-DISTRIBUTED solved directly, not scaled.

    A first version scaled the clustered loss as I^2 R / nc^1.5 on the argument that the
    lateral path shortens as 1/sqrt(nc). For a monolithic die that argument is wrong twice:
    a converter cannot sit inside the die, so clusters can only be placed around the
    PERIMETER; and the source-to-die gap is fixed by the VR footprint, so it does NOT shrink
    with the cluster count and the number of squares actually RISES. The clustered cases are
    therefore solved on the same resistive sheet as the baseline, with the VR tiles
    distributed over 1, 2 or 4 edges of the die.
    """
    stack = stacks_from_cfg()[stack_name]
    _, span, tile, xs = z5_geometry(lateral_gap_mm)
    off = DIE_MM / 2 + lateral_gap_mm + tile / 2
    per = max(N_SRC // n_edges, 1)
    src = []
    edges = [(-1, 0), (1, 0), (0, -1), (0, 1)][:n_edges]
    for ex, ey in edges:
        for k in range(per):
            t = (k + .5) / per * DIE_MM - DIE_MM / 2
            src.append((ex * off if ex else t, ey * off if ey else t))
    pol = pol_grid()
    sol = rdl_network_solve(stack, src, [i_lat_a / len(src)] * len(src), pol,
                            [i_lat_a / len(pol)] * len(pol), span_mm=span, T_c=t_c,
                            n=grid_n, src_size_mm=tile, load_size_mm=DIE_MM / NPOL,
                            ground_xy=pol[len(pol) // 2], ground_size_mm=DIE_MM / NPOL)
    rs_loop = stack.r_sheet_net("vdd", t_c) + stack.r_sheet_net("gnd", t_c)
    return {"n_edges": n_edges, "n_sources": len(src), "P_loop_w": sol["p_loop_w"],
            "R_eq_mohm": sol["p_loop_w"] / i_lat_a ** 2 * 1e3,
            "loop_squares": sol["p_loop_w"] / i_lat_a ** 2 / rs_loop,
            "i_lateral_a": i_lat_a}


def z5_family(v_lateral_list=(1.0, 3.3, 5.0, 12.0, 24.0, 48.0),
              n_clusters=(1, 2, 4), stage1: dict | None = None,
              stage2: dict | None = None) -> list[dict]:
    """Z5-LV / MV / HV / DISTRIBUTED on two axes: the lateral rail VOLTAGE and the number
    of lateral clusters.

    Lateral loss scales as (P/V)^2 R. BOTH conversion stages are charged at their real
    modelled cost from the same upstream loss model: stage 1 converts 48 V to the lateral
    rail beside the die, stage 2 converts the lateral rail to 1 V at the load. At
    V_lateral = 48 V stage 1 vanishes and the topology degenerates into vertical delivery
    with a lateral 48 V feed; at V_lateral = 1 V stage 2 vanishes and it is the tested
    Z5-LV. The family therefore spans the whole space between the two, which is exactly
    what Phase 0I never did.
    """
    # one solve per edge count, reused across rail voltages because P ~ I^2 R_eq exactly
    req = {}
    for nc in n_clusters:
        c = trace_z5_clustered(nc, 1000.0)
        req[nc] = c["R_eq_mohm"] * 1e-3
        print(f"  clustered Z5: {nc} edge(s), {c['n_sources']} sources -> "
              f"R_eq = {c['R_eq_mohm']:.5f} mOhm ({c['loop_squares']:.4f} squares)",
              flush=True)
    rows = []
    for v in v_lateral_list:
        i_lat = LOAD_W / v
        s1 = (stage1 or {}).get(v, {})
        s2 = (stage2 or {}).get(v, {})
        p1 = s1.get("p_conv_total_w")
        p2 = s2.get("p_conv_total_w")
        for nc in n_clusters:
            r_c = req[nc]
            p_lat = i_lat ** 2 * r_c
            # A stage the upstream optimizer cannot compile is NOT worth zero watts.
            # Those rows are marked LOWER BOUND and two explicitly-labelled SC-stage
            # efficiency sensitivities are carried alongside, never folded into the total.
            modelled = (p1 is not None) and (p2 is not None)
            tot = (p_lat + (p1 or 0.0) + (p2 or 0.0))
            miss = (p1 is None) or (p2 is None)
            rows.append({
                "topology": ("Z5-LV" if v <= 1.0 else "Z5-MV" if v <= 12.0 else "Z5-HV"),
                "v_lateral": v, "n_die_edges_fed": nc, "i_lateral_a": i_lat,
                "R_eq_mohm": r_c * 1e3,
                "P_lateral_w": p_lat,
                "P_stage1_w": p1, "stage1_status": s1.get("status", "none"),
                "P_stage2_w": p2, "stage2_status": s2.get("status", "none"),
                "P_total_w": tot,
                "total_is": "LOWER BOUND -- a stage could not be compiled" if miss
                            else "COMPLETE",
                "P_total_stage1_at_97pct_w": tot + (0.0 if p1 is not None
                                                    else LOAD_W / 0.97 - LOAD_W),
                "P_total_stage1_at_99pct_w": tot + (0.0 if p1 is not None
                                                    else LOAD_W / 0.99 - LOAD_W),
                "efficiency_pct": 100 * LOAD_W / (LOAD_W + tot),
                "vs_Z1_126p1W": tot - 126.089845025657,
            })
    return rows


def main() -> int:
    rows = [trace_z5()]
    for stack in ("ectc2024_one_per_net", "iscas2024_variant"):
        rows.append(trace_z5(stack))
    for gap in (0.5, 1.0, 2.0, 4.0):
        r = trace_z5(lateral_gap_mm=gap); r["stack"] = f"ectc2024_primary_gap{gap:g}"
        rows.append(r)
    for n in (121, 161, 201):
        r = trace_z5(grid_n=n); r["stack"] = f"ectc2024_primary_grid{n}"
        rows.append(r)
    keys = sorted({k for r in rows for k in r})
    with open(OUT / "z5_path_decomposition.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
    b = rows[0]
    print(f"Z5-LV baseline: P_loop = {b['P_loop_w']:.3f} W, R_eq = {b['R_eq_mohm']:.5f} mOhm,"
          f" {b['loop_squares']:.4f} loop squares on {b['sheet_R_loop_mohm_sq']:.4f} mOhm/sq,"
          f" IR = {b['IR_drop_v']:.4f} V", flush=True)
    for r in rows[1:]:
        print(f"  {r['stack']:34s} P={r['P_loop_w']:9.3f} W  R_eq={r['R_eq_mohm']:.5f} mOhm"
              f"  squares={r['loop_squares']:.4f}")

    cmp_rows = pcb_vs_rdl()
    with open(OUT / "z5_pcb_vs_rdl.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cmp_rows[0])); w.writeheader()
        w.writerows(cmp_rows)
    for c in cmp_rows:
        print(f"  {c['path']:4s} t={c['t_cu_um']:6.1f}um W/S={c['width_um']:.0f}/"
              f"{c['space_um']:.0f} n={c['n_per_net']} occ={c['occupancy']:.3f} "
              f"loop R = {c['loop_R_mohm_per_sq']:.4f} mOhm/sq")

    s1, s2 = {}, {}
    for v in (1.0, 3.3, 5.0, 12.0, 24.0, 48.0):
        s2[v] = stage_loss(v, 1.0, LOAD_W) if v > 1.0 else {"status": "none",
                                                            "p_conv_total_w": 0.0}
        s1[v] = stage_loss(48.0, v, LOAD_W / v * 1.0) if v < 48.0 else {
            "status": "none", "p_conv_total_w": 0.0}
        print(f"  V_lat={v:5.1f}: stage1 48->{v:g} {s1[v]['status']:20s} "
              f"P={s1[v].get('p_conv_total_w')}   stage2 {v:g}->1 "
              f"{s2[v]['status']:20s} P={s2[v].get('p_conv_total_w')}", flush=True)
    with open(OUT / "z5_stage_losses.csv", "w", newline="") as fh:
        allr = [{**r, "stage": 1, "v_lateral": v} for v, r in s1.items()] + \
               [{**r, "stage": 2, "v_lateral": v} for v, r in s2.items()]
        k = sorted({x for r in allr for x in r})
        w = csv.DictWriter(fh, fieldnames=k); w.writeheader(); w.writerows(allr)

    fam = z5_family(stage1=s1, stage2=s2)
    with open(OUT / "z5_architecture_comparison.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(fam[0])); w.writeheader(); w.writerows(fam)
    print("\n  V_lat  nc   P_lat    P_stage1  P_stage2   P_total  +97% SC  status")
    for r in fam:
        if r["n_die_edges_fed"] in (1, 4):
            print(f"  {r['v_lateral']:5.1f} {r['n_die_edges_fed']:3d} {r['P_lateral_w']:9.3f} "
                  f"{(r['P_stage1_w'] if r['P_stage1_w'] is not None else float('nan')):9.3f} "
                  f"{(r['P_stage2_w'] or 0):9.3f} "
                  f"{r['P_total_w']:9.3f} {r['P_total_stage1_at_97pct_w']:8.1f}  "
                  f"{r['total_is']}")
    print(f"\nwrote {OUT/'z5_architecture_comparison.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
