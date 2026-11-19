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
import os
import sys
import time
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts" / "phase0mr3c"))
sys.path.insert(0, str(R / "scripts" / "phase0ir"))
sys.path.insert(0, str(R / "scripts" / "phase0i"))
import run_final_local_response as LR                                # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hvr_scratch import path as scratch                             # noqa: E402
import final_closure_local_extract as X                             # noqa: E402

OUT = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "final_closure"   # campaign hook
LR.WD = scratch("fc_local")
LR.WD.mkdir(parents=True, exist_ok=True)
#: the Norton/EPC card's calibrated temperature span. A joint temperature above it
#: is an extrapolation and is FLAGGED, not hidden.
NORTON_T_RANGE_C = (-40.0, 125.0)
#: SAC305 melting onset (final_closure_results.SAC305_SOLIDUS_C): at or above it the joint
#: is not solid solder and a missing response is an outcome, not a failure
SOLIDUS_C = 217.0
INCOMPLETE = {}


def _complete_case(case, du_um, t_hot, _run=LR.run_case):
    """LR.run_case refused unless the solve reached the end of its schedule (DEFECT #69).
    Old outputs of the same name are removed first, so a previous .dat can never stand in
    for a solve that did not run."""
    for ext in (".dat", ".frd", ".sta", ".cvg"):
        (LR.WD / f"{case}{ext}").unlink(missing_ok=True)
    r = _run(case, du_um, t_hot)
    t_end = 2 * LR.N_CYC * LR.DWELL
    dat = LR.WD / f"{case}.dat"
    if X.complete(dat, t_end):
        return r
    t = X.end_time(dat) if dat.exists() else None
    INCOMPLETE[case] = {"t_last_s": t, "t_end_s": t_end}
    print(f"  {case}: INCOMPLETE solve -- the .dat ends at t = {t} s of {t_end:g} s; "
          "no response is reported", flush=True)
    return None


def install():
    """Route the harness (run_control included) through the completeness check."""
    if LR.run_case is not _complete_case:
        LR.run_case = _complete_case


def lost_responses(cases):
    """Solves without a response at a solid-solder joint. There an incomplete solve is a
    failed run to repeat, never a 'no response' result."""
    return [f"{a}{tag}" for a, c in cases.items() if c["T_joint_C"] < SOLIDUS_C
            for tag, rr in (("", c["response"]),
                            ("_fine", (c.get("fine_mesh") or {}).get("response")))
            if rr is None]


def critical(arch, scen):
    """Critical joint of the PRODUCTION-mesh case (final_closure_physical_etm.case_path; Z3:
    the coupled land-side case, reference_case_path)."""
    sys.path.insert(0, str(R / "scripts"))
    f = reference_case_path(arch, scen)
    r = json.loads(f.read_text())
    c = dict(r["mechanics"]["joint_search"]["critical"], source=f.name)
    return c["du_um"], c["T_C"], c


def reference_case_path(arch, scen):
    """TCPMT round 3: the case a local study takes for (arch, scen). Z3 is ALWAYS the coupled
    land-side case (cooling A base, tcpmt_cases.Z3_LAND), never the superseded uncoupled
    production-boundary Z3 file; the other integrations keep their production-mesh case."""
    import final_closure_physical_etm as E
    if arch == "Z3":
        import tcpmt_cases as TC
        import final_closure_sensitivity as S
        return S.OUT / f"etm_Z3_{scen}__{TC.Z3_LAND['A']}.json"
    return E.case_path(arch, scen)


def main():
    scen = sys.argv[1] if len(sys.argv) > 1 else "HV_S0"
    LR.WD = scratch(f"fc_local_{scen}")
    LR.WD.mkdir(parents=True, exist_ok=True)
    install()
    t0 = time.time()
    dev = LR.run_control()
    res = {"scenario": scen, "control_deviation_pct": dev,
           "control_tolerance_pct": LR.CONTROL_TOL_PCT, "cetol": LR.CETOL,
           "local_family": {"n_xy": LR.N_XY, "n_z_solder": LR.N_Z_SOL,
                            "n_cycles": LR.N_CYC, "dwell_s": LR.DWELL,
                            "T_off_C": LR.T_OFF, "procedure": LR.PROCEDURE,
                            "material": LR.MATKIND},
           "norton_T_range_C": NORTON_T_RANGE_C, "cases": {}}
    sys.path.insert(0, str(R / "scripts"))
    import final_closure_physical_etm as E
    # TCPMT revision: every integration with a production case (Z3: its coupled case)
    archs = [a for a in ("Z1", "Z2", "Z3") if reference_case_path(a, scen).exists()]
    for arch in archs:
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
    for arch in archs:
        du, tj, _ = critical(arch, scen)
        rf = LR.run_case(f"{arch}_{scen}_fine", du, tj)
        base = res["cases"][arch]["response"]
        res["cases"][arch]["fine_mesh"] = {"n_xy": 8, "n_z_solder": 10, "response": rf}
        if rf and base:
            res["cases"][arch]["mesh_change_pct"] = (
                100 * abs(rf["d_peeq_per_cycle"] - base["d_peeq_per_cycle"])
                / base["d_peeq_per_cycle"])
    LR.N_XY, LR.N_Z_SOL = keep
    lost = lost_responses(res["cases"])
    if lost:
        raise SystemExit(f"  {scen}: no response at an admissible joint for {lost} "
                         f"({INCOMPLETE}) -- nothing written; rerun")
    res["incomplete_solves"] = INCOMPLETE
    res["wall_s"] = round(time.time() - t0, 1)
    (OUT / f"local_solder_{scen}.json").write_text(json.dumps(res, indent=1, default=float))
    print("wrote local_solder", scen, "in", res["wall_s"], "s")


if __name__ == "__main__":
    main()
