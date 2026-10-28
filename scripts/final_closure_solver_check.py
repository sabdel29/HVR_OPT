"""Structural-solver verification on a converged case (never edits the case file).

This CalculiX build's SPOOLES solves 36k and 38.6k C3D8I elements but segfaults at
43k, single- or multi-threaded, and ITERATIVE CHOLESKY was once measured 35 % off the
direct solver on package warpage. So before any structural number from a non-default
solver is used, it is
re-solved here on the SAME mesh and the SAME converged temperature field as a reference
solve, and the observables are compared. Usage:

    python final_closure_solver_check.py ARCH SCEN H SOLVER THREADS
    SOLVER: SPOOLES | "ITERATIVE CHOLESKY" | "ITERATIVE SCALING"
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import final_closure_physical_etm as E                              # noqa: E402


def converged_field(m, arch, scen, h):
    import production_et as PE
    wd = Path(f"/tmp/fc_etm/{arch}_{scen}_h{h}")
    last_it = sorted(wd.glob("et*"), key=lambda p: int(p.name[2:]))[-1]
    frd = sorted(last_it.glob("th_*.frd"), key=lambda p: int(p.stem.split("_")[1]))[-1]
    return PE.ccxio.read_frd(frd)["NDTEMP"][1:m.n_nodes + 1, 0]


def solve(m, mats, st, Tn, arch, tiles, wd, solver, threads):
    import production_et as PE
    wd.mkdir(parents=True, exist_ok=True)
    si = wd / "structural.inp"
    PE.ccxio.write_structural(m, mats, Tn, st, "BC_BOARD", si,
                              solver="" if solver == "SPOOLES" else solver)
    t0 = time.time()
    PE.ccxio.run_ccx(si, threads=threads)
    wall = time.time() - t0
    sres = PE.ccxio.read_frd(si.with_suffix(".frd"))
    sm = PE.metrics.structural_metrics(m, sres["DISP"], sres["STRESS"], st)
    js = E.joint_search(m, sres["DISP"], Tn, arch, tiles)
    return {"die_warpage_pv_um": sm["die_warpage_pv_um"],
            "pkg_warpage_pv_um": sm.get("pkg_warpage_pv_um"),
            "du_c_um": js["critical"]["du_um"],
            "critical_xy_mm": [js["critical"]["x_mm"], js["critical"]["y_mm"]],
            "wall_s": wall}


def main():
    arch, scen, h, solver, threads = (sys.argv[1], sys.argv[2], float(sys.argv[3]),
                                      sys.argv[4], int(sys.argv[5]))
    E._raise_stack_limit()
    m, mats, st, tiles, _ = E.build(arch, h)
    Tn = converged_field(m, arch, scen, h)
    case = json.loads((R / "research" / "final_closure" /
                       f"etm_{arch}_{scen}_h{h}.json").read_text())
    assert abs(float(np.nanmax(Tn)) - case["thermal"]["T_max_C"]) < 1e-6
    tag = f"{solver.replace(' ', '_')}_t{threads}"
    out = {"arch": arch, "scenario": scen, "h_xy_mm": h, "n_elems": int(m.n_elems),
           "solver": solver, "threads": threads}
    try:
        out.update(solve(m, mats, st, Tn, arch, tiles,
                         Path(f"/tmp/fc_solver/{arch}_{scen}_h{h}_{tag}"), solver, threads))
        out["ok"] = True
    except Exception as e:                                # a crash IS the finding
        out["ok"] = False
        out["error"] = str(e)[-400:]
    f = R / "research" / "final_closure" / "solver_check" / f"{arch}_{scen}_h{h}_{tag}.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(out, indent=1, default=float))
    print("SOLVERCHECK", json.dumps(out, default=float), flush=True)


if __name__ == "__main__":
    main()
