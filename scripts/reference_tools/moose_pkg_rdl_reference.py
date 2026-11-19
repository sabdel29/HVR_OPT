"""Matched reference for the package HV RDL network: production FV sheet vs MOOSE FEM.

Q3D and Maxwell DC conduction are unlicensed on this host, so the independent
numerical reference is MOOSE (heat_transfer-opt) solving the exact analogue
div(sigma grad V) = -J as div(k grad T) = -q on an unstructured gmsh mesh.

ONE FORMULATION, BOTH SOLVERS. To make the comparison model-to-model exact:
  sheet   sigma_s = 1 / R_sq over the 30 x 30 mm substrate (Neumann edges)
  balls   each 400 um disc couples to the rail (V = 0) through an areal
          conductance g_a = 1 / (rho_c + R_ball * A_ball)   [S/mm^2]
  pads    each 0.2 mm VIN pad draws I_cell uniformly over its area
The production network lumps the ball resistance in a ball node; the distributed
form used here differs from it only by the ball-internal current redistribution,
which is reported separately as a model-form difference, not hidden in the error.

Observables: total dissipation P at 1 A (= R_eff) from the exact identity
P = sum_pads I_pad |<V>_pad|, and the largest pad drop.
The problem is linear: MOOSE takes one Newton step whose linear solve is converged
to a relative residual of 1e-12, so the solver tolerance is far below the
mesh error that the m1/m2/m3 sequence measures.
"""
from __future__ import annotations

import json
import math
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
for _p in ("scripts/phase0nw", "scripts/phase0m", "scripts/phase0mr", "scripts"):
    sys.path.insert(0, str(R / _p))
import pkg_rdl_network as K                                          # noqa: E402
import pkg_rdl_refined as RF                                         # noqa: E402
import physical_coords as PCO                                        # noqa: E402
import pad_interface as PI                                           # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hvr_scratch import path as scratch                             # noqa: E402

MOOSE = Path("/home/beams0/LPOPRYHO/projects/moose/modules/heat_transfer/heat_transfer-opt")
OUT = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "final_closure"   # campaign hook
EVID = Path(os.environ.get("ETM_RESULTS_ROOT") or R) / "presentation" / "prelim_hvr" / "tool_evidence" / "pkg_rdl_moose"
WD = scratch("moose_rdl")
REPEATS = 3


def timed(fn, *a):
    """One untimed warm-up call, then REPEATS timed calls on the same machine.
    The problem is linear, so the warm-up result equals the timed ones; the last
    result is returned with the median and range of the timed walls."""
    fn(*a)
    walls, out = [], None
    for _ in range(REPEATS):
        out = fn(*a)
        walls.append(out["wall_s"])
    out["timing"] = {"median_s": statistics.median(walls), "min_s": min(walls),
                     "max_s": max(walls), "repeats": REPEATS, "walls_s": walls}
    return out


def set_wd(arch):
    global WD
    WD = scratch(f"moose_rdl_{arch}")
    WD.mkdir(parents=True, exist_ok=True)


def problem(arch="Z2", rail="supply", N=54):
    cells = PCO.physical_cell_coordinates()
    cand = PCO.bga_lattice_sites(K.architecture_cutout_mm(arch))
    balls = PCO.select_power_sites(cand, cells, N, N, "nearest_symmetric")[rail]
    pads = RF.cell_terminals(cells, rail, "VIN_PAD")
    rsq = K.sheet_resistance_ohm_sq(5e-3, 0.30)
    rho_c = K.RHO_C_CASES["CONTACT_N"]
    a_ball = math.pi * 0.2 ** 2
    g_a = 1.0 / (rho_c + PI.bga_ball_resistance_ohm(20.0) * a_ball)      # S/mm^2
    return {"arch": arch, "rail": rail, "N": N, "balls": balls, "pads": pads,
            "sigma_s": 1.0 / rsq, "g_a": g_a, "i_total": 1.0}


def production(pb, level=2):
    t0 = time.time()
    fx, fy = RF.build_grid_general(pb["balls"], pb["pads"], level)
    sh = RF.RefinedSheet(fx, fy, 1.0 / pb["sigma_s"])
    G = sh.laplacian().tolil()
    rhs = np.zeros(sh.n)
    react = np.zeros(sh.n)
    for x, y in pb["balls"]:
        nd, ar = sh.overlap(x, y, 0.400, "disc")
        react[nd] += pb["g_a"] * ar
    pad_nodes = []
    i_pad = pb["i_total"] / len(pb["pads"])
    for x, y, c in pb["pads"]:
        nd, ar = sh.overlap(x, y, c, "square")
        rhs[nd] -= i_pad * ar / ar.sum()
        pad_nodes.append((nd, ar))
    G = G.tocsr() + __import__("scipy.sparse", fromlist=["diags"]).diags(react)
    import scipy.sparse.linalg as spla
    V = spla.spsolve(G.tocsc(), rhs)
    vbar = np.array([np.sum(V[nd] * ar) / ar.sum() for nd, ar in pad_nodes])
    P = float(np.sum(i_pad * np.abs(vbar)))
    return {"P_W_at_1A": P, "R_eff_ohm": P / pb["i_total"] ** 2,
            "max_pad_drop_V": float(np.max(np.abs(vbar))),
            "n_cv": sh.n, "wall_s": time.time() - t0}


def gmsh_mesh(pb, h_fine=0.02, h_coarse=0.35, path=None):
    path = path or WD / "rdl.msh"
    import gmsh
    WD.mkdir(parents=True, exist_ok=True)
    gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add("rdl")
    occ = gmsh.model.occ
    sheet = occ.addRectangle(-15, -15, 0, 30, 30)
    discs = [occ.addDisk(x, y, 0, 0.2, 0.2) for x, y in pb["balls"]]
    squares = [occ.addRectangle(x - c / 2, y - c / 2, 0, c, c) for x, y, c in pb["pads"]]
    out, omap = occ.fragment([(2, sheet)], [(2, t) for t in discs + squares])
    occ.synchronize()
    ball_tags = [omap[1 + i][0][1] for i in range(len(discs))]
    pad_tags = [omap[1 + len(discs) + i][0][1] for i in range(len(squares))]
    used = set(ball_tags) | set(pad_tags)
    rest = [t for d, t in gmsh.model.getEntities(2) if t not in used]
    for i, t in enumerate(ball_tags):
        gmsh.model.addPhysicalGroup(2, [t], name=f"ball{i}")
    for i, t in enumerate(pad_tags):
        gmsh.model.addPhysicalGroup(2, [t], name=f"pad{i}")
    gmsh.model.addPhysicalGroup(2, rest, name="sheet")
    f = gmsh.model.mesh.field
    bnd = gmsh.model.getBoundary([(2, t) for t in ball_tags + pad_tags], oriented=False)
    f.add("Distance", 1); f.setNumbers(1, "CurvesList", [abs(c[1]) for c in bnd])
    f.add("Threshold", 2); f.setNumber(2, "InField", 1)
    f.setNumber(2, "SizeMin", h_fine); f.setNumber(2, "SizeMax", h_coarse)
    f.setNumber(2, "DistMin", 0.05); f.setNumber(2, "DistMax", 1.5)
    f.setAsBackgroundMesh(2)
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    gmsh.model.mesh.generate(2)
    n_el = sum(len(e) for e in gmsh.model.mesh.getElements(2)[1])
    gmsh.write(str(path))
    gmsh.finalize()
    return path, n_el


def moose(pb, msh):
    npad = len(pb["pads"])
    i_pad = pb["i_total"] / npad
    a_pad = pb["pads"][0][2] ** 2
    balls = " ".join(f"ball{i}" for i in range(len(pb["balls"])))
    pads = " ".join(f"pad{i}" for i in range(npad))
    pps = "\n".join(f"""  [v{i}]
    type = ElementAverageValue
    variable = V
    block = pad{i}
  []""" for i in range(npad))
    inp = f"""
[Mesh]
  [f]
    type = FileMeshGenerator
    file = {msh}
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
  [contact]
    type = Reaction
    variable = V
    rate = {pb['g_a']:.12e}
    block = '{balls}'
  []
  [draw]
    type = BodyForce
    variable = V
    value = {-i_pad / a_pad:.12e}
    block = '{pads}'
  []
[]
[Materials]
  [k]
    type = GenericConstantMaterial
    prop_names = 'thermal_conductivity'
    prop_values = '{pb['sigma_s']:.12e}'
  []
[]
[Executioner]
  type = Steady
  solve_type = NEWTON
  line_search = none
  petsc_options_iname = '-pc_type -pc_hypre_type'
  petsc_options_value = 'hypre boomeramg'
  l_tol = 1e-12
  l_max_its = 300
  nl_rel_tol = 1e-9
  nl_abs_tol = 1e-30
  nl_max_its = 5
[]
[Postprocessors]
{pps}
[]
[Outputs]
  csv = true
  exodus = true
[]
"""
    p = WD / "rdl.i"
    p.write_text(inp)
    t0 = time.time()
    r = subprocess.run([str(MOOSE), "-i", p.name], cwd=WD, capture_output=True, text=True)
    wall = time.time() - t0
    csvs = sorted(WD.glob("rdl_out*.csv"))
    if r.returncode != 0 or not csvs:
        raise RuntimeError(r.stdout[-1500:] + r.stderr[-800:])
    import csv
    rows = list(csv.DictReader(csvs[-1].open()))
    last = rows[-1]
    vbar = np.array([float(last[f"v{i}"]) for i in range(npad)])
    P = float(np.sum(i_pad * np.abs(vbar)))
    (WD / "moose_log_tail.txt").write_text(r.stdout[-4000:])
    return {"P_W_at_1A": P, "R_eff_ohm": P / pb["i_total"] ** 2,
            "max_pad_drop_V": float(np.max(np.abs(vbar))), "wall_s": wall}


def main():
    arch = sys.argv[1] if len(sys.argv) > 1 else "Z2"
    set_wd(arch)
    pb = problem(arch)
    load0 = [round(x, 1) for x in os.getloadavg()]
    prod = production(pb, 2)
    prod3 = timed(production, pb, 3)
    res = {"stage": f"pkg_rdl_{arch}", "formulation": "distributed-ball, uniform pad draw",
           "production_L2": prod, "production_L3": prod3, "moose": {}}
    for tag, hf in (("m1", 0.04), ("m2", 0.02), ("m3", 0.01)):
        msh, n_el = gmsh_mesh(pb, h_fine=hf, h_coarse=hf * 15,
                              path=WD / f"rdl_{tag}.msh")
        mo = timed(moose, pb, msh) if tag == "m3" else moose(pb, msh)
        mo["n_elements"] = n_el
        mo["h_fine_mm"] = hf
        res["moose"][tag] = mo
        print(tag, json.dumps(mo), flush=True)
    ref = res["moose"]["m3"]
    res["rel_err_R_eff"] = (prod3["R_eff_ohm"] - ref["R_eff_ohm"]) / ref["R_eff_ohm"]
    res["rel_err_max_drop"] = ((prod3["max_pad_drop_V"] - ref["max_pad_drop_V"])
                               / ref["max_pad_drop_V"])
    # Aitken extrapolation of the reference's own mesh sequence (diagnostic only)
    r1, r2, r3 = (res["moose"][t]["R_eff_ohm"] for t in ("m1", "m2", "m3"))
    d1, d2 = r2 - r1, r3 - r2
    if abs(d1 - d2) > 0 and d1 * d2 > 0:
        r_inf = r3 + d2 * d2 / (d1 - d2)
        res["moose_R_eff_extrapolated_ohm"] = r_inf
        res["rel_err_R_eff_vs_extrapolated"] = (prod3["R_eff_ohm"] - r_inf) / r_inf
    res["speedup_L3_vs_moose_m3"] = (ref["timing"]["median_s"]
                                     / prod3["timing"]["median_s"])
    res["cores"] = {"production": 1, "moose_mpi_ranks": 1}
    res["load_average"] = {"before": load0,
                           "after": [round(x, 1) for x in os.getloadavg()]}
    res["timing_method"] = f"1 warm-up + {REPEATS} timed repeats, median and range"
    ev = EVID.parent / f"pkg_rdl_moose_{arch}"
    ev.mkdir(parents=True, exist_ok=True)
    for f in ("rdl.i", "moose_log_tail.txt"):
        if (WD / f).exists():
            (ev / f).write_text((WD / f).read_text())
    (OUT / f"reference_pkg_rdl_moose_{arch}.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ("rel_err_R_eff", "rel_err_max_drop",
                                          "speedup_L3_vs_moose_m3")}))


if __name__ == "__main__":
    main()
