"""FINAL CLOSURE --- the nonlinear local solder response at the NEW critical joint.

The validated Phase-0I/0I-R local family is run unchanged (mesh, exclusion band,
Norton/EPC constitutive card, procedure, cycle schedule, extraction); only the two
inputs the architecture supplies change, and they now come from the physical
lineage's ALL-SITE joint search instead of an assumed corner joint:

    du_c     in-plane relative displacement across the critical joint
    T_joint  temperature at that joint

response != damage != life. This returns the inelastic strain increment per
stabilised cycle, the strain range and the inelastic work density. No cycles to
failure are computed: the available life correlations are calibrated to other
simulation procedures (Darveaux, 10.1115/1.1413764), so an absolute life from
these numbers would not be admissible.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts" / "phase0mr3c"))
sys.path.insert(0, str(R / "scripts" / "phase0ir"))
sys.path.insert(0, str(R / "scripts" / "phase0i"))
import run_final_local_response as LR                                # noqa: E402

OUT = R / "research" / "final_closure"
LR.WD = Path("/tmp/fc_local")
LR.WD.mkdir(parents=True, exist_ok=True)
#: the Norton/EPC card's calibrated temperature span. A joint temperature above it
#: is an extrapolation and is FLAGGED, not hidden.
NORTON_T_RANGE_C = (-40.0, 125.0)


def critical(arch, scen):
    """Critical joint of the PRODUCTION-mesh case (final_closure_physical_etm.case_path)."""
    sys.path.insert(0, str(R / "scripts"))
    import final_closure_physical_etm as E
    f = E.case_path(arch, scen)
    r = json.loads(f.read_text())
    c = dict(r["mechanics"]["joint_search"]["critical"], source=f.name)
    return c["du_um"], c["T_C"], c


def main():
    scen = sys.argv[1] if len(sys.argv) > 1 else "HV_S0"
    LR.WD = Path(f"/tmp/fc_local_{scen}")
    LR.WD.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    dev = LR.run_control()
    res = {"scenario": scen, "control_deviation_pct": dev,
           "control_tolerance_pct": LR.CONTROL_TOL_PCT, "cetol": LR.CETOL,
           "local_family": {"n_xy": LR.N_XY, "n_z_solder": LR.N_Z_SOL,
                            "n_cycles": LR.N_CYC, "dwell_s": LR.DWELL,
                            "T_off_C": LR.T_OFF, "procedure": LR.PROCEDURE,
                            "material": LR.MATKIND},
           "norton_T_range_C": NORTON_T_RANGE_C, "cases": {}}
    for arch in ("Z1", "Z2"):
        du, tj, crit = critical(arch, scen)
        r = LR.run_case(f"{arch}_{scen}", du, tj)
        extrap = not (NORTON_T_RANGE_C[0] <= tj <= NORTON_T_RANGE_C[1])
        res["cases"][arch] = {"critical_joint": crit, "du_c_um": du, "T_joint_C": tj,
                              "T_outside_norton_calibration": extrap,
                              "response": r}
        print(f"  {arch}: du_c={du:.4f} um T={tj:.2f} C -> "
              f"d_eps_in={r['d_peeq_per_cycle'] if r else None}", flush=True)
    # one finer local mesh for the convergence of THIS operating point
    keep = (LR.N_XY, LR.N_Z_SOL)
    LR.N_XY, LR.N_Z_SOL = 8, 10
    for arch in ("Z1", "Z2"):
        du, tj, _ = critical(arch, scen)
        rf = LR.run_case(f"{arch}_{scen}_fine", du, tj)
        base = res["cases"][arch]["response"]
        res["cases"][arch]["fine_mesh"] = {"n_xy": 8, "n_z_solder": 10, "response": rf}
        if rf and base:
            res["cases"][arch]["mesh_change_pct"] = (
                100 * abs(rf["d_peeq_per_cycle"] - base["d_peeq_per_cycle"])
                / base["d_peeq_per_cycle"])
    LR.N_XY, LR.N_Z_SOL = keep
    res["wall_s"] = round(time.time() - t0, 1)
    (OUT / f"local_solder_{scen}.json").write_text(json.dumps(res, indent=1, default=float))
    print("wrote local_solder", scen, "in", res["wall_s"], "s")


if __name__ == "__main__":
    main()
