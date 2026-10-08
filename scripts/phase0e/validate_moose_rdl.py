#!/usr/bin/env python3
"""Phase-0E Sec.10: validate the multilayer RDL compact solver against MOOSE FE.

PREDECLARED AGREEMENT TARGET (fixed before any run):
    |dP_RDL| <= 2.0 %   and   |dV_span| <= 4.0 %   for EVERY placement,
    using ONE model with ONE calibration. No per-placement fitting is permitted.

DC conduction is solved through the exact analogy div(sigma grad V) = -J  <->
div(k grad T) = -q, which is why the MOOSE heat_transfer application is the correct
independent solver here rather than a full-wave EM code.
"""
from __future__ import annotations
import json, subprocess, sys, tempfile
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
OUTD = REPO / "results" / "phase0e"
MOOSE = Path("/home/beams0/LPOPRYHO/projects/moose/modules/heat_transfer/heat_transfer-opt")
sys.path.insert(0, str(REPO / "scripts" / "phase0e"))
from stack import stacks_from_cfg, rdl_network_solve, multilayer_sheet_solve

DIE = 22.36
TILE = 4.9
NPOL = 10

TARGET_P_PCT = 2.0
TARGET_V_PCT = 4.0


def pols():
    q = (np.arange(NPOL) + .5) / NPOL * DIE - DIE / 2
    return [(float(x), float(y)) for x in q for y in q]


# A tile must lie ON the substrate: |centre| + TILE/2 <= DIE/2, i.e. |centre| <= 8.73 mm.
# The earlier edge-biased set used +-9.0, which overhangs the die by 0.27 mm. The compact
# model renormalises a clipped footprint (injecting the full current), MOOSE injects only
# the in-domain part, and the two then disagree by ~25 % for reasons that have nothing to
# do with either solver. Placements are now kept physical, and asserted so.
EDGE_MAX = DIE / 2 - TILE / 2

PLACEMENTS = {
    "distributed": [(-5.59, -5.59), (5.59, -5.59), (-5.59, 5.59), (5.59, 5.59)],
    "edge_biased": [(-8.7, 0.0), (8.7, 0.0), (0.0, -8.7), (0.0, 8.7)],
    "asymmetric":  [(-8.0, -8.0), (-8.0, -3.0), (-3.0, -8.0), (8.0, 8.0)],
}
for _n, _t in PLACEMENTS.items():
    for _x, _y in _t:
        assert max(abs(_x), abs(_y)) <= EDGE_MAX + 1e-9, (
            f"{_n}: tile at ({_x},{_y}) overhangs the die (max centre {EDGE_MAX:.2f} mm)")


def _boxcar(cx, cy, half, amp):
    return (f"if(abs(x-({cx}))<{half}&abs(y-({cy}))<{half},{amp:.10e},0)")


def moose_solve(sigma_s: float, srcs, i_src, lds, i_ld, nx=200, tag="c",
                pin_xy=(0.0, 0.0), pin_size=0.0) -> dict:
    """2-D sheet conduction on an nx x nx FE mesh, finite-area injection (same footprints
    as the compact model). Power is integrated as sigma|grad V|^2 over the sheet."""
    # The 100 equal POL footprints tile the die exactly, so the load is a UNIFORM current
    # density -- one term instead of 100. This matters: a 104-term ParsedFunction silently
    # loses terms (measured injection was 195 A instead of 240 A, an 18 % error), whereas
    # 5 terms integrate cleanly. High-order Gauss then resolves the tile boxcar edges,
    # which are not commensurate with the mesh (4.9 mm / 0.1118 mm = 43.8 cells).
    hs = TILE / 2
    i_load_total = float(sum(i_ld))
    terms = [f"{-i_load_total / (DIE * DIE):.10e}"]
    terms += [_boxcar(x, y, hs, i / (TILE * TILE)) for (x, y), i in zip(srcs, i_src)]
    fexpr = "+".join(terms)

    inp = f"""
[Mesh]
  [gen]
    type = GeneratedMeshGenerator
    dim = 2
    nx = {nx}
    ny = {nx}
    xmin = {-DIE/2}
    xmax = {DIE/2}
    ymin = {-DIE/2}
    ymax = {DIE/2}
  []
  # Ground a SINGLE node, at exactly the point the compact solver grounds.
  # A Dirichlet condition on a whole edge is a different problem: it lets current
  # enter and leave through that edge, which is why an edge-pinned comparison
  # disagreed by +25 % (edge-biased) and +55 % (asymmetric).
  [pinset]
    type = BoundingBoxNodeSetGenerator
    input = gen
    new_boundary = 'pinpt'
    bottom_left = '{pin_xy[0]-pin_size/2} {pin_xy[1]-pin_size/2} 0'
    top_right = '{pin_xy[0]+pin_size/2} {pin_xy[1]+pin_size/2} 0'
  []
[]
[Variables]
  [V]
  []
[]
[Kernels]
  [cond]
    type = HeatConduction
    variable = V
  []
  [src]
    type = BodyForce
    variable = V
    function = jsrc
  []
[]
[Functions]
  [jsrc]
    type = ParsedFunction
    expression = '{fexpr}'
  []
  [jabs]
    type = ParsedFunction
    expression = 'abs({fexpr})'
  []
[]
[Materials]
  [k]
    type = GenericConstantMaterial
    prop_names = 'thermal_conductivity'
    prop_values = '{sigma_s:.10e}'
  []
[]
[BCs]
  [pin]
    type = DirichletBC
    variable = V
    boundary = 'pinpt'
    value = 0
  []
[]
[AuxVariables]
  # DiffusionFluxAux evaluates a gradient, so these must be ELEMENTAL
  # (constant monomial); nodal aux variables have no gradient at nodes.
  [fx]
    order = CONSTANT
    family = MONOMIAL
  []
  [fy]
    order = CONSTANT
    family = MONOMIAL
  []
  [pdens]
    order = CONSTANT
    family = MONOMIAL
  []
[]
[AuxKernels]
  [fxk]
    type = DiffusionFluxAux
    variable = fx
    diffusion_variable = V
    component = x
    diffusivity = thermal_conductivity
  []
  [fyk]
    type = DiffusionFluxAux
    variable = fy
    diffusion_variable = V
    component = y
    diffusivity = thermal_conductivity
  []
  [pk]
    type = ParsedAux
    variable = pdens
    coupled_variables = 'fx fy'
    expression = '(fx*fx+fy*fy)/{sigma_s:.10e}'
  []
[]
[Postprocessors]
  [P]
    type = ElementIntegralVariablePostprocessor
    variable = pdens
  []
  [Vmax]
    type = NodalExtremeValue
    variable = V
    value_type = max
  []
  [Vmin]
    type = NodalExtremeValue
    variable = V
    value_type = min
  []
  # Net injected current: MUST be ~0. The tile footprints are not commensurate with the
  # mesh (4.9 mm / 0.1118 mm = 43.8 cells), so Gauss quadrature of a boxcar source can
  # mis-integrate the injected current, and P scales as I^2.
  [Inet]
    type = FunctionElementIntegral
    function = jsrc
  []
  [Iabs]
    type = FunctionElementIntegral
    function = jabs
  []
[]
[Executioner]
  type = Steady
  [Quadrature]
    order = ELEVENTH
    type = GAUSS
  []
  solve_type = NEWTON
  petsc_options_iname = '-pc_type -pc_hypre_type'
  petsc_options_value = 'hypre boomeramg'
  nl_rel_tol = 1e-10
[]
[Outputs]
  csv = true
  file_base = {tag}
[]
"""
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "in.i"
        f.write_text(inp)
        r = subprocess.run([str(MOOSE), "-i", str(f)], capture_output=True, text=True,
                           cwd=td, timeout=1800)
        csv = Path(td) / f"{tag}.csv"
        if not csv.exists():
            print(r.stdout[-3000:]); print(r.stderr[-2000:])
            raise RuntimeError("MOOSE produced no csv")
        rows = csv.read_text().strip().split("\n")
        hdr = rows[0].split(","); last = rows[-1].split(",")
        d = {h.strip(): float(v) for h, v in zip(hdr, last)}
    return {"P_w": d["P"], "Vmax": d["Vmax"], "Vmin": d["Vmin"],
            "dv_span_v": d["Vmax"] - d["Vmin"], "mesh": f"{nx}x{nx}",
            "I_net_a": d.get("Inet"), "I_abs_a": d.get("Iabs")}


def run(i_total=240.0, T_c=20.0, nx=300, grid_n=161):
    st = stacks_from_cfg()["ectc2024_primary"]
    sigma_net = st.sigma_s_net("vdd", T_c)      # ONE calibration, used for every placement
    P = pols()
    i_pol = i_total / len(P)
    rows, ok_all = [], True
    print(f"stack={st.name}  sigma_net={sigma_net:.2f} S  (n_vdd={st.n_vdd}, t={st.t_cu_m*1e6:.0f} um,"
          f" occ={st.occupancy:.4f})")
    print(f"PREDECLARED TARGET: |dP| <= {TARGET_P_PCT} %, |dV| <= {TARGET_V_PCT} %\n")
    print(f"{'placement':14s} {'P_compact(W)':>13s} {'P_MOOSE(W)':>11s} {'dP%':>7s}"
          f" {'dV_cmp(mV)':>11s} {'dV_MOOSE(mV)':>13s} {'dV%':>7s}  verdict")
    for name, tiles in PLACEMENTS.items():
        i_vr = i_total / len(tiles)
        pin = P[len(P) // 2]
        cmp_ = multilayer_sheet_solve([sigma_net], tiles, [i_vr] * len(tiles),
                                      P, [i_pol] * len(P), span_mm=DIE, n=grid_n,
                                      src_size_mm=TILE, load_size_mm=DIE / NPOL,
                                      ground_xy=pin, ground_size_mm=DIE / NPOL)
        mo = moose_solve(sigma_net, tiles, [i_vr] * len(tiles), P, [i_pol] * len(P),
                         nx=nx, tag=f"m_{name}", pin_xy=pin, pin_size=DIE / NPOL)
        dp = 100 * (cmp_["p_w"] - mo["P_w"]) / mo["P_w"]
        dv = 100 * (cmp_["dv_span_v"] - mo["dv_span_v"]) / mo["dv_span_v"]
        good = bool(abs(dp) <= TARGET_P_PCT and abs(dv) <= TARGET_V_PCT)
        ok_all = bool(ok_all and good)
        print(f"{name:14s} {cmp_['p_w']:13.5f} {mo['P_w']:11.5f} {dp:+7.2f}"
              f" {cmp_['dv_span_v']*1e3:11.4f} {mo['dv_span_v']*1e3:13.4f} {dv:+7.2f}"
              f"  {'PASS' if good else 'FAIL'}")
        rows.append({"placement": name, "P_compact_w": float(cmp_["p_w"]), "P_moose_w": float(mo["P_w"]),
                     "dP_pct": float(dp), "dv_compact_v": float(cmp_["dv_span_v"]),
                     "dv_moose_v": float(mo["dv_span_v"]), "dV_pct": float(dv), "pass": good,
                     "moose_mesh": mo["mesh"], "compact_grid": grid_n})
    out = {"stack": st.name, "sigma_s_net": float(sigma_net), "i_total_a": i_total,
           "target_P_pct": TARGET_P_PCT, "target_V_pct": TARGET_V_PCT,
           "one_calibration_for_all_placements": True, "all_pass": ok_all, "cases": rows}
    (OUTD / "multilayer_rdl_validation.json").write_text(json.dumps(out, indent=2))
    import csv as _c
    with open(OUTD / "multilayer_rdl_validation.csv", "w", newline="") as fh:
        w = _c.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f"\nALL PLACEMENTS {'PASS' if ok_all else 'FAIL'} against the predeclared target")
    print(f"compact grid n={grid_n} (h={DIE/(grid_n-1)*1e3:.0f} um), MOOSE {nx}x{nx} "
          f"(h={DIE/nx*1e3:.0f} um); ONE grid for every placement, chosen by the convergence "
          f"study in results/phase0e/rdl_grid_convergence.csv")
    return out


if __name__ == "__main__":
    run()
