"""Run ONLY the structural step of a finished case on its converged temperature field.

Used when the E-T fixed point of a case is converged but its thermoelastic solve is
missing or failed: the direct solver crashed on a larger mesh, or a mesh level was run
thermal-only first because its structural solve takes hours. The temperature field is
read back from the last converged thermal result -- asserted equal to the case file's
T_max -- so the E-T state is unchanged; the structural solver used is recorded.

    python final_closure_remech.py ARCH SCEN H [rXZ] [SOLVER] [THREADS]
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import final_closure_physical_etm as E                              # noqa: E402


def main():
    arch, scen, h = sys.argv[1], sys.argv[2], float(sys.argv[3])
    refine = (int(sys.argv[4][1]), int(sys.argv[4][2])) if len(sys.argv) > 4 else (1, 1)
    solver = sys.argv[5] if len(sys.argv) > 5 else "ITERATIVE CHOLESKY"
    threads = int(sys.argv[6]) if len(sys.argv) > 6 else None
    f = E.case_path(arch, scen, h, refine)
    wd = E.WD / f"{arch}_{scen}_h{h}{E.refine_tag(refine)}"
    E._raise_stack_limit()
    m, mats, st, tiles, _ = E.build(arch, h, refine)    # slow on fine levels: build first,
    while not f.exists():                               # then wait for the converged case
        time.sleep(30)
    time.sleep(5)
    res = json.loads(f.read_text())
    last_it = sorted(wd.glob("et*"), key=lambda p: int(p.name[2:]))[-1]
    frd = sorted(last_it.glob("th_*.frd"), key=lambda p: int(p.stem.split("_")[1]))[-1]
    import production_et as PE
    Tn = PE.ccxio.read_frd(frd)["NDTEMP"][1:m.n_nodes + 1, 0]
    assert abs(float(np.nanmax(Tn)) - res["thermal"]["T_max_C"]) < 1e-6, "not the converged field"
    t0 = time.time()
    res["mechanics"] = E.mechanics(m, mats, st, Tn, wd, arch, tiles,
                                   "" if solver == "SPOOLES" else solver, threads)
    res["mechanics"]["note"] = "structural step run separately on the converged field"
    res.pop("mechanics_error", None)
    f.write_text(json.dumps(res, indent=1, default=float))
    print("re-mech", arch, scen, h, refine, res["mechanics"]["die_warpage_pv_um"],
          res["mechanics"]["joint_search"]["critical"]["du_um"],
          f"{time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
