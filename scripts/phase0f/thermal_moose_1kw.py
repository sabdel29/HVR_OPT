#!/usr/bin/env python3
"""Phase-0F Sec.13: 1-kW full 3-D package thermal cross-check in MOOSE.

Phase 0D-R validated the conduction OPERATOR on a 2-D sheet. This rebuilds the COMPLETE
package -- substrate, embedded HVR tiles, interface, die, TIM -- in an independent code with
its own mesher, element formulation and linear solver, and asks the only question that
matters for a design framework: **does the independent solver preserve candidate ordering?**

The Icepak attempt is reported separately in thermal_validation.md: it converged but the
external cooling boundary did not take effect (every object returned exactly 5000 K, a solver
clamp), so it produced no usable temperature.
"""
from __future__ import annotations
import csv, json, math, subprocess, sys, tempfile, time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0b"))
sys.path.insert(0, str(R / "scripts" / "phase0d"))
from etm.config import load_stack, load_doe, build_materials
from etm.placement import generate
from electrical import compile_hvr

MOOSE = Path("/home/beams0/LPOPRYHO/projects/moose/modules/heat_transfer/heat_transfer-opt")
OUT = R / "results" / "phase0f"
SUB, DIE = 30.0, 22.36
DZ = 0.01                     # z cell size: every layer boundary is a multiple of 10 um
NXY = 60                      # 0.5 mm lateral cells
T_AMB, H_BOT = 25.0, 10.0


def tiles_for(place, side, stack, doe, n_vr=None):
    """Phase-0F lattice; n_vr and the tile height come from the 1-kW design point."""
    import sys as _s
    _s.path.insert(0, str(R / "scripts" / "phase0f"))
    from placement0f import build as build0f
    g, rules = stack["geometry"], doe["placement_rules"]
    tiles, _ = build0f(place, n_vr or globals().get("_N_VR", 49), side,
                       g["functional_die"]["size_x"]["value"],
                       rules["edge_keepout_mm"]["value"], rules["min_gap_mm"]["value"])
    return [(t.cx, t.cy) for t in tiles]


def build_input(place, side, h_sub, p_conv, p_die, h_top, stack, doe, tag):
    mats = build_materials(stack)
    g = stack["geometry"]
    t_tile = globals().get("_T_TILE", g["hvr_tile"]["thickness"]["value"])
    t_if = g["interface_layer"]["thickness"]["value"]
    t_die = g["functional_die"]["thickness"]["value"]
    t_tim = g["tim"]["thickness"]["value"]
    z_if, z_die, z_tim, z_top = h_sub, h_sub + t_if, h_sub + t_if + t_die, h_sub + t_if + t_die + t_tim
    nz = int(round(z_top / DZ))
    tiles = tiles_for(place, side, stack, doe)

    # blocks: 1 substrate, 2 hvr tile, 3 interface, 4 die, 5 tim, 9 to-delete
    gens = [f"""  [gen]
    type = GeneratedMeshGenerator
    dim = 3
    nx = {NXY}
    ny = {NXY}
    nz = {nz}
    xmin = {-SUB/2} xmax = {SUB/2}
    ymin = {-SUB/2} ymax = {SUB/2}
    zmin = 0 zmax = {z_top}
  []"""]
    prev = "gen"
    def bb(name, lo, hi, blk, inp):
        gens.append(f"""  [{name}]
    type = SubdomainBoundingBoxGenerator
    input = {inp}
    block_id = {blk}
    bottom_left = '{lo[0]} {lo[1]} {lo[2]}'
    top_right = '{hi[0]} {hi[1]} {hi[2]}'
  []""")
        return name
    # everything above the substrate that is OUTSIDE the die footprint is not package
    prev = bb("dead", (-SUB/2, -SUB/2, h_sub), (SUB/2, SUB/2, z_top), 9, prev)
    prev = bb("b_if", (-DIE/2, -DIE/2, z_if), (DIE/2, DIE/2, z_die), 3, prev)
    prev = bb("b_die", (-DIE/2, -DIE/2, z_die), (DIE/2, DIE/2, z_tim), 4, prev)
    prev = bb("b_tim", (-DIE/2, -DIE/2, z_tim), (DIE/2, DIE/2, z_top), 5, prev)
    for k, (cx, cy) in enumerate(tiles):
        prev = bb(f"b_tile{k}", (cx - side/2, cy - side/2, h_sub - t_tile),
                  (cx + side/2, cy + side/2, h_sub), 2, prev)
    gens.append(f"""  [kill]
    type = BlockDeletionGenerator
    input = {prev}
    block = '9'
    new_boundary = 'cut'
  []""")
    gens.append(f"""  [top_ss]
    type = ParsedGenerateSideset
    input = kill
    combinatorial_geometry = 'z > {z_top - DZ/2}'
    included_subdomains = '5'
    normal = '0 0 1'
    new_sideset_name = 'cool_top'
  []""")
    gens.append(f"""  [bot_ss]
    type = ParsedGenerateSideset
    input = top_ss
    combinatorial_geometry = 'z < {DZ/2}'
    normal = '0 0 -1'
    new_sideset_name = 'cool_bot'
  []""")

    # SubdomainBoundingBoxGenerator assigns whole elements by centroid, so every block's
    # MESHED volume and area are quantised (22.36 mm on a 0.5 mm grid becomes 22.0 mm). Using
    # nominal values leaves 3.2 % of the heat unaccounted for. Both are computed exactly here:
    # source densities from the meshed volume, and the film coefficients scaled so the TOTAL
    # cooling conductance h*A matches the CalculiX model -- which is what makes this a
    # like-for-like cross-check rather than a different boundary-value problem.
    dxy, dzc = SUB / NXY, z_top / nz

    def ncells(lo, hi, origin, d, n):
        return sum(1 for i in range(n) if lo <= origin + (i + 0.5) * d <= hi)

    def meshed_volume(x0, x1, y0, y1, z0, z1):
        return (ncells(x0, x1, -SUB / 2, dxy, NXY) * dxy
                * ncells(y0, y1, -SUB / 2, dxy, NXY) * dxy
                * ncells(z0, z1, 0.0, dzc, nz) * dzc)

    v_die = meshed_volume(-DIE / 2, DIE / 2, -DIE / 2, DIE / 2, z_die, z_tim)
    v_tile = sum(meshed_volume(cx - side / 2, cx + side / 2, cy - side / 2, cy + side / 2,
                               h_sub - t_tile, h_sub) for cx, cy in tiles)
    q_tile = p_conv / v_tile
    q_die = p_die / v_die

    a_top_meshed = (ncells(-DIE / 2, DIE / 2, -SUB / 2, dxy, NXY) * dxy) ** 2
    a_bot_meshed = (ncells(-SUB / 2, SUB / 2, -SUB / 2, dxy, NXY) * dxy) ** 2
    h_top_eff = h_top * (DIE * DIE) / a_top_meshed
    h_bot_eff = H_BOT * (SUB * SUB) / a_bot_meshed

    def k_of(m):   # W/(mm K)
        return mats[m].k * 1e-3

    inp = f"""
[Mesh]
{chr(10).join(gens)}
[]
[Variables]
  [T]
    initial_condition = {T_AMB}
  []
[]
[Materials]
  [m_sub]
    type = GenericConstantMaterial
    block = '0'
    prop_names = 'thermal_conductivity'
    prop_values = '{k_of("silicon"):.8e}'
  []
  [m_tile]
    type = GenericConstantMaterial
    block = '2'
    prop_names = 'thermal_conductivity'
    prop_values = '{k_of("hvr_effective"):.8e}'
  []
  [m_if]
    type = GenericConstantMaterial
    block = '3'
    prop_names = 'thermal_conductivity'
    prop_values = '{k_of("underfill_homog"):.8e}'
  []
  [m_die]
    type = GenericConstantMaterial
    block = '4'
    prop_names = 'thermal_conductivity'
    prop_values = '{k_of("silicon"):.8e}'
  []
  [m_tim]
    type = GenericConstantMaterial
    block = '5'
    prop_names = 'thermal_conductivity'
    prop_values = '{k_of("tim"):.8e}'
  []
[]
[Kernels]
  [cond]
    type = HeatConduction
    variable = T
  []
  [q_die]
    type = BodyForce
    variable = T
    value = {q_die:.8e}
    block = '4'
  []
  [q_tile]
    type = BodyForce
    variable = T
    value = {q_tile:.8e}
    block = '2'
  []
[]
[BCs]
  [top]
    type = ConvectiveHeatFluxBC
    variable = T
    boundary = 'cool_top'
    T_infinity = {T_AMB}
    heat_transfer_coefficient = {h_top_eff*1e-6:.8e}
  []
  [bot]
    type = ConvectiveHeatFluxBC
    variable = T
    boundary = 'cool_bot'
    T_infinity = {T_AMB}
    heat_transfer_coefficient = {h_bot_eff*1e-6:.8e}
  []
[]
[Postprocessors]
  [Tmax]
    type = NodalExtremeValue
    variable = T
    value_type = max
  []
  [Tmax_die]
    type = NodalExtremeValue
    variable = T
    value_type = max
    block = '4'
  []
  [Tmean_die]
    type = ElementAverageValue
    variable = T
    block = '4'
  []
  [Tmean_tile]
    type = ElementAverageValue
    variable = T
    block = '2'
  []
  [Qtop]
    type = ConvectiveHeatTransferSideIntegral
    T_solid = T
    T_fluid = {T_AMB}
    htc = {h_top_eff*1e-6:.8e}
    boundary = 'cool_top'
  []
  [Qbot]
    type = ConvectiveHeatTransferSideIntegral
    T_solid = T
    T_fluid = {T_AMB}
    htc = {h_bot_eff*1e-6:.8e}
    boundary = 'cool_bot'
  []
[]
[Executioner]
  type = Steady
  solve_type = NEWTON
  petsc_options_iname = '-pc_type -pc_hypre_type'
  petsc_options_value = 'hypre boomeramg'
  nl_rel_tol = 1e-9
[]
[Outputs]
  csv = true
  file_base = {tag}
[]
"""
    return inp, p_die + p_conv


# 1-kW cases: the two thickness extremes, which is where the Phase-0F decision lives.
CASES = [("KW1_thin_h800",  "uniform", 3.5, 0.8),
         ("KW1_thick_h1500", "uniform", 3.5, 1.5)]


def main():
    import sys as _s
    _s.path.insert(0, str(R / "scripts" / "phase0f"))
    import kw1
    from geometry import cell_stack
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((R / "results/phase0f/cooling_1kw_calibration.json").read_text())["h_top_W_m2K"]
    rows = []
    for tag, place, j, h in CASES:
        des, g, why = kw1.design_1kw(kw1.M_VR, j, h)
        if des is None:
            print(f"  {tag}: {why}"); continue
        side = math.sqrt(des.area_mm2)
        p_conv = kw1.M_VR * des.loss_at(84.0)["p_conv_w"]
        globals()["_T_TILE"] = cell_stack(des, "nominal").t_cell_mm
        globals()["_N_VR"] = kw1.M_VR
        inp, p_tot = build_input(place, side, h, p_conv, 1000.0, h_top, stack, doe, tag)
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "in.i"; f.write_text(inp)
            t0 = time.time()
            pr = subprocess.run([str(MOOSE), "-i", str(f)], capture_output=True, text=True,
                                cwd=td, timeout=5400)
            csvf = Path(td) / f"{tag}.csv"
            if not csvf.exists():
                print(f"  {tag}: FAILED"); print(pr.stdout[-2500:]); continue
            r = list(csv.reader(open(csvf)))
            d = {k.strip(): float(v) for k, v in zip(r[0], r[-1])}
        bal = 100 * (d["Qtop"] + d["Qbot"] - p_tot) / p_tot
        rows.append({"case": tag, "placement": place, "j": j, "h_sub_mm": h,
                     "tile_side_mm": side, "P_conv_w": p_conv, "P_total_w": p_tot,
                     "Tmax_C": d["Tmax"], "Tmax_die_C": d["Tmax_die"],
                     "Tmean_die_C": d["Tmean_die"], "Tmean_tile_C": d["Tmean_tile"],
                     "Q_out_w": d["Qtop"] + d["Qbot"], "energy_residual_pct": bal,
                     "solve_s": time.time() - t0})
        print(f"  {tag:24s} Tmax={d['Tmax']:7.3f} C  Tdie={d['Tmax_die']:7.3f}  "
              f"Ttile={d['Tmean_tile']:7.3f}  Ebal={bal:+.3f}%  ({time.time()-t0:.0f}s)",
              flush=True)
    with open(OUT / "thermal_moose_1kw.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"\nwrote {OUT/'thermal_moose_1kw.csv'}")


if __name__ == "__main__":
    main()
